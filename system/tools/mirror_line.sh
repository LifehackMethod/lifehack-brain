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
# Five measurements, each local-refs-only:
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

# ── nothing to report? print nothing. ───────────────────────────────────────────────
if [ "$GONE_COUNT" -eq 0 ] && [ "$NOUP_COUNT" -eq 0 ] && [ "$AHEAD_COUNT" -eq 0 ] && [ "$BEHIND_COUNT" -eq 0 ] && [ "$STRAY_REMOTE_COUNT" -eq 0 ]; then
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

echo "MIRROR: ${PARTS}"
exit 0
