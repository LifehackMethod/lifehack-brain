#!/bin/bash
# mirror_line.sh — one line reporting how far the current git clone has drifted from its mirror
#
# REPORT ONLY, NEVER A GATE. GitHub SOP §9: "what branches contain, how far away they drift
# from main… Report those. Do not gate on them." This prints one line and always exits 0 — it
# blocks nothing, denies nothing, prompts nothing.
#
# FAIL SILENT. Not a git repo, git missing, any command errors, nothing to report — in every
# one of those cases this prints NOTHING and exits 0. It runs at every session start for every
# student; a session-start line that can throw is worse than the rot it reports.
#
# NO NETWORK. This reads only local refs — it never fetches. Its "ahead"/"behind" figures are
# only as fresh as the last fetch anyone ran; it does not go get a fresher one. (M14 is the
# scheduled fetch that keeps "behind" honest — this script never fetches on its own.)
#
# Run it: bash system/tools/mirror_line.sh
#
# Six measurements, each local-refs-only:
# 1. gone — local branches whose upstream was deleted. The track field format is
# "[origin/x: gone]", not "[gone]" — a bare `\[gone\]` pattern matches
# zero branches and silently under-reports. Tested via the substring
# "gone" inside %(upstream:track).
# 2. no-upstream — local branches with an empty %(upstream:short).
# 3. ahead-of-remote — for branches WITH a live upstream, `git rev-list --count up..branch`;
# counted when > 0, named "branch: +N" in the parenthetical (cap 5, "…").
# 4. behind-remote — for branches WITH a live upstream, `git rev-list --count branch..up`;
# counted when > 0, named "branch: -N" in the parenthetical (cap 5, "…"). Added M13 — M9's
# original four checks never looked backward, so the one drift actually present (`main`
# 12 behind `origin/main`, 2026-09-08) was invisible to this tool.
# 5. stray-remotes — any git remote other than `origin`, plus any remote-tracking ref not
# under `refs/remotes/origin/`. Added M13 — the public workbench carried a `claudeops`
# remote (5 refs) and 9 `origin-pr/*` refs with no configured remote at all; M10's other
# four checks never look at either, and `git remote prune origin` cannot see them because
# they are not origin's.
# 6. harness-overlap — ONLY in a two-remote clone, and only when exactly one of the two
# remotes' URL matches the same public-shaped pattern the push-gate uses
# (`github\.com[:/]LifehackMethod/`, see ClaudeOps system/shipping-lane/public-remotes.json).
# Counts paths from `git ls-tree -r --name-only HEAD` whose blob at that path is IDENTICAL
# (via `git rev-parse HEAD:<path>` vs `git rev-parse <public-remote>/<default-branch>:<path>`)
# — never `git log --find-object`, which produced a false positive on this project. Exists
# because `system/tools/resolution-census.sh` (ClaudeOps) counts symlinks only
# (`[ -L "$f" ] || continue`) — a real-directory copy is invisible to it, which is how 47 real
# directories hid in plain sight. That tool can prove the claim FALSE, never TRUE; this segment
# is the instrument that CAN prove it true. Students have single-remote clones and never see
# this. Silent whenever: not exactly 2 remotes, 0 or 2+ remotes match the public-shaped
# pattern, or the public remote's default-branch ref was never fetched locally — this section
# never fetches to find out.

set +e
set +u

# ── is this even a git repo? ────────────────────────────────────────────────────────
GIT_BIN="$(command -v git 2>/dev/null)"
if [ -z "$GIT_BIN" ]; then
  exit 0
fi

TOPLEVEL="$("$GIT_BIN" rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$TOPLEVEL" ]; then
  exit 0
fi

# ── walk every local branch once, classify it ───────────────────────────────────────
REFLINES="$("$GIT_BIN" for-each-ref --format='%(refname:short)|%(upstream:short)|%(upstream:track)' refs/heads/ 2>/dev/null)"
if [ -z "$REFLINES" ]; then
  exit 0
fi

GONE_COUNT=0
NOUP_COUNT=0
AHEAD_COUNT=0
AHEAD_LIST=""
AHEAD_SHOWN=0
AHEAD_TOTAL=0
BEHIND_COUNT=0
BEHIND_LIST=""
BEHIND_SHOWN=0
BEHIND_TOTAL=0

# read line-by-line without mapfile (bash 3.2 compatible)
OLDIFS="$IFS"
IFS='
'
for LINE in $REFLINES; do
  BRANCH="${LINE%%|*}"
  REST="${LINE#*|}"
  UPSTREAM="${REST%%|*}"
  TRACK="${REST#*|}"

  case "$TRACK" in
    *gone*)
      GONE_COUNT=$((GONE_COUNT + 1))
      continue
      ;;
  esac

  if [ -z "$UPSTREAM" ]; then
    NOUP_COUNT=$((NOUP_COUNT + 1))
    continue
  fi

  # live upstream — is this branch ahead of it? local refs only, no fetch.
  N="$("$GIT_BIN" rev-list --count "${UPSTREAM}..${BRANCH}" 2>/dev/null)"
  case "$N" in
    ''|*[!0-9]*) : ;; # not a clean integer — skip rather than guess
    *)
      if [ "$N" -gt 0 ] 2>/dev/null; then
        AHEAD_COUNT=$((AHEAD_COUNT + 1))
        AHEAD_TOTAL=$((AHEAD_TOTAL + 1))
        if [ "$AHEAD_SHOWN" -lt 5 ]; then
          if [ -z "$AHEAD_LIST" ]; then
            AHEAD_LIST="${BRANCH}: +${N}"
          else
            AHEAD_LIST="${AHEAD_LIST}, ${BRANCH}: +${N}"
          fi
          AHEAD_SHOWN=$((AHEAD_SHOWN + 1))
        fi
      fi
      ;;
  esac

  # same upstream — is this branch behind it? local refs only, no fetch, no pull.
  M="$("$GIT_BIN" rev-list --count "${BRANCH}..${UPSTREAM}" 2>/dev/null)"
  case "$M" in
    ''|*[!0-9]*) continue ;; # not a clean integer — skip rather than guess
  esac
  if [ "$M" -gt 0 ] 2>/dev/null; then
    BEHIND_COUNT=$((BEHIND_COUNT + 1))
    BEHIND_TOTAL=$((BEHIND_TOTAL + 1))
    if [ "$BEHIND_SHOWN" -lt 5 ]; then
      if [ -z "$BEHIND_LIST" ]; then
        BEHIND_LIST="${BRANCH}: -${M}"
      else
        BEHIND_LIST="${BEHIND_LIST}, ${BRANCH}: -${M}"
      fi
      BEHIND_SHOWN=$((BEHIND_SHOWN + 1))
    fi
  fi
done
IFS="$OLDIFS"

if [ "$AHEAD_TOTAL" -gt 5 ] 2>/dev/null; then
  AHEAD_LIST="${AHEAD_LIST}, …"
fi
if [ "$BEHIND_TOTAL" -gt 5 ] 2>/dev/null; then
  BEHIND_LIST="${BEHIND_LIST}, …"
fi

# ── stray remotes: any remote other than origin, plus any remote-tracking ref not under
#    refs/remotes/origin/. Local refs only — `git remote` and `git for-each-ref` never fetch.
STRAY_REMOTE_COUNT=0
REMOTE_EXTRA="$("$GIT_BIN" remote 2>/dev/null | grep -vc '^origin$' 2>/dev/null)"
case "$REMOTE_EXTRA" in
  ''|*[!0-9]*) REMOTE_EXTRA=0 ;;
esac
ORPHAN_REFS="$("$GIT_BIN" for-each-ref refs/remotes 2>/dev/null | grep -vc 'refs/remotes/origin/' 2>/dev/null)"
case "$ORPHAN_REFS" in
  ''|*[!0-9]*) ORPHAN_REFS=0 ;;
esac
STRAY_REMOTE_COUNT=$((REMOTE_EXTRA + ORPHAN_REFS))

# ── harness-overlap: paths in THIS clone whose blob is byte-identical to the same path
#    at the public remote's default branch. Two-remote clones only — see header note 6.
#    Local refs only: no fetch, ever. Missing/unfetched ref = silent, not an error.
OVERLAP_COUNT=0
REMOTE_NAMES="$("$GIT_BIN" remote 2>/dev/null)"
REMOTE_N=0
if [ -n "$REMOTE_NAMES" ]; then
  REMOTE_N="$(printf '%s\n' "$REMOTE_NAMES" | grep -c .)"
fi
case "$REMOTE_N" in
  ''|*[!0-9]*) REMOTE_N=0 ;;
esac

if [ "$REMOTE_N" -eq 2 ] 2>/dev/null; then
  PUBLIC_REMOTE=""
  PUBLIC_MATCHES=0
  OLDIFS4="$IFS"
  IFS='
'
  for RNAME in $REMOTE_NAMES; do
    RURL="$("$GIT_BIN" remote get-url "$RNAME" 2>/dev/null)"
    case "$RURL" in
      *github.com[:/]LifehackMethod/*)
        PUBLIC_REMOTE="$RNAME"
        PUBLIC_MATCHES=$((PUBLIC_MATCHES + 1))
        ;;
    esac
  done
  IFS="$OLDIFS4"

  if [ "$PUBLIC_MATCHES" -eq 1 ]; then
    PUBLIC_REF=""
    HEAD_SYM="$("$GIT_BIN" symbolic-ref -q "refs/remotes/${PUBLIC_REMOTE}/HEAD" 2>/dev/null)"
    if [ -n "$HEAD_SYM" ]; then
      PUBLIC_REF="$HEAD_SYM"
    elif "$GIT_BIN" show-ref --verify --quiet "refs/remotes/${PUBLIC_REMOTE}/main" 2>/dev/null; then
      PUBLIC_REF="refs/remotes/${PUBLIC_REMOTE}/main"
    elif "$GIT_BIN" show-ref --verify --quiet "refs/remotes/${PUBLIC_REMOTE}/master" 2>/dev/null; then
      PUBLIC_REF="refs/remotes/${PUBLIC_REMOTE}/master"
    fi

    if [ -n "$PUBLIC_REF" ]; then
      LOCAL_PATHS="$("$GIT_BIN" ls-tree -r --name-only HEAD 2>/dev/null)"
      if [ -n "$LOCAL_PATHS" ]; then
        OLDIFS5="$IFS"
        IFS='
'
        for P in $LOCAL_PATHS; do
          LHASH="$("$GIT_BIN" rev-parse "HEAD:${P}" 2>/dev/null)"
          RHASH="$("$GIT_BIN" rev-parse "${PUBLIC_REF}:${P}" 2>/dev/null)"
          if [ -n "$LHASH" ] && [ -n "$RHASH" ] && [ "$LHASH" = "$RHASH" ]; then
            OVERLAP_COUNT=$((OVERLAP_COUNT + 1))
          fi
        done
        IFS="$OLDIFS5"
      fi
    fi
  fi
fi

# ── nothing to report? print nothing. ───────────────────────────────────────────────
if [ "$GONE_COUNT" -eq 0 ] && [ "$NOUP_COUNT" -eq 0 ] && [ "$AHEAD_COUNT" -eq 0 ] && [ "$BEHIND_COUNT" -eq 0 ] && [ "$STRAY_REMOTE_COUNT" -eq 0 ] && [ "$OVERLAP_COUNT" -eq 0 ]; then
  exit 0
fi

# ── assemble the one line, omitting any zero component ──────────────────────────────
PARTS=""
if [ "$GONE_COUNT" -gt 0 ]; then
  PARTS="${GONE_COUNT} gone"
fi
if [ "$NOUP_COUNT" -gt 0 ]; then
  if [ -z "$PARTS" ]; then
    PARTS="${NOUP_COUNT} no-upstream (-> CLAUDE.md map: no-upstream)"
  else
    PARTS="${PARTS} · ${NOUP_COUNT} no-upstream (-> CLAUDE.md map: no-upstream)"
  fi
fi
if [ "$AHEAD_COUNT" -gt 0 ]; then
  if [ -z "$PARTS" ]; then
    PARTS="${AHEAD_COUNT} ahead-of-remote (${AHEAD_LIST})"
  else
    PARTS="${PARTS} · ${AHEAD_COUNT} ahead-of-remote (${AHEAD_LIST})"
  fi
fi
if [ "$BEHIND_COUNT" -gt 0 ]; then
  if [ -z "$PARTS" ]; then
    PARTS="${BEHIND_COUNT} behind-remote (${BEHIND_LIST})"
  else
    PARTS="${PARTS} · ${BEHIND_COUNT} behind-remote (${BEHIND_LIST})"
  fi
fi
if [ "$STRAY_REMOTE_COUNT" -gt 0 ]; then
  if [ -z "$PARTS" ]; then
    PARTS="${STRAY_REMOTE_COUNT} stray-remotes"
  else
    PARTS="${PARTS} · ${STRAY_REMOTE_COUNT} stray-remotes"
  fi
fi
if [ "$OVERLAP_COUNT" -gt 0 ]; then
  if [ -z "$PARTS" ]; then
    PARTS="harness-overlap: ${OVERLAP_COUNT}"
  else
    PARTS="${PARTS} · harness-overlap: ${OVERLAP_COUNT}"
  fi
fi

echo "MIRROR: ${PARTS}"
exit 0
