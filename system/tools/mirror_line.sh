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
# NO NETWORK. This reads only local refs — it never fetches. Its "ahead" figure is only as
# fresh as the last fetch anyone ran; it does not go get a fresher one.
#
# Run it:   bash system/tools/mirror_line.sh
#
# Three measurements, each local-refs-only:
#   1. gone         — local branches whose upstream was deleted. The track field format is
#                      "[origin/x: gone]", not "[gone]" — a bare `\[gone\]` pattern matches
#                      zero branches and silently under-reports. Tested via the substring
#                      "gone" inside %(upstream:track).
#   2. no-upstream   — local branches with an empty %(upstream:short).
#   3. ahead-of-remote — for branches WITH a live upstream, `git rev-list --count up..branch`;
#                      counted when > 0, named "branch: +N" in the parenthetical (cap 5, "…").

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
    ''|*[!0-9]*) continue ;;  # not a clean integer — skip rather than guess
  esac
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
done
IFS="$OLDIFS"

if [ "$AHEAD_TOTAL" -gt 5 ] 2>/dev/null; then
  AHEAD_LIST="${AHEAD_LIST}, …"
fi

# ── nothing to report? print nothing. ───────────────────────────────────────────────
if [ "$GONE_COUNT" -eq 0 ] && [ "$NOUP_COUNT" -eq 0 ] && [ "$AHEAD_COUNT" -eq 0 ]; then
  exit 0
fi

# ── assemble the one line, omitting any zero component ──────────────────────────────
PARTS=""
if [ "$GONE_COUNT" -gt 0 ]; then
  PARTS="${GONE_COUNT} gone"
fi
if [ "$NOUP_COUNT" -gt 0 ]; then
  if [ -z "$PARTS" ]; then
    PARTS="${NOUP_COUNT} no-upstream"
  else
    PARTS="${PARTS} · ${NOUP_COUNT} no-upstream"
  fi
fi
if [ "$AHEAD_COUNT" -gt 0 ]; then
  if [ -z "$PARTS" ]; then
    PARTS="${AHEAD_COUNT} ahead-of-remote (${AHEAD_LIST})"
  else
    PARTS="${PARTS} · ${AHEAD_COUNT} ahead-of-remote (${AHEAD_LIST})"
  fi
fi

echo "MIRROR: ${PARTS}"
exit 0
