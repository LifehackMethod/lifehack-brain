#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: the per-machine doctrine files (`CLAUDE.local.md` — the person's own standing instructions;
#      `.claude/settings.local.json` — the loader ceiling) are gitignored and outside the notes folder, so neither `git pull` nor Drive
#      carries an edit to the other machine. On 2026-08-21 the desktop edited one sentence, nobody
#      re-mirrored by hand, and the laptop ran an edit behind until a session noticed a day later.
# GUARDS: nothing — OBSERVE only (PostToolUse, always exit 0). After a Write/Edit lands on one of the two
#      mirrored files it runs `doctrine_sync.py push` so the shared mirror in the notes folder
#      (`state/doctrine-mirror/`, Drive-synced) carries the edit at edit time. Any other path: silent.
# REDIRECT: the check half rides the 5-minute `system-health` sweep (`system-health-run.sh`) and files a
#      Hospital finding when a machine is BEHIND or in CONFLICT; repair is the visible one-command act
#      `python3 system/tools/doctrine_sync.py pull` (diff shown, old local archived first).
# SIGNPOST: the rule + design live in `system/tools/doctrine_sync.py` (module docstring) and
#      `system/organism/elements/health-invariants.md` (the rider). Edits via Bash (`.claude/settings.json`
#      and `system/hooks/**` are on the Edit deny-list by design) — read `bash system/tools/read_sop.sh hook`
#      first, then edit, then RESTART: the harness reads settings.json at session start.
# FAIL_POSTURE: degrade-safe — a PostToolUse hook cannot block and must never try. Unparseable payload,
#      missing tool, push failure: a one-line note on stderr at most, always exit 0. The sweep's check is
#      the safety net for anything this misses (an edit made through Bash, for instance).
# UPDATED: 2026-08-22
# ─────────────────────────────────────────────────────────────────────────────
# PostToolUse hook (matcher: Write|Edit). Advisory only — always exits 0.
# Payload arrives on STDIN (house lesson: never `$1` alone) — `${1:-$(cat)}` mirrors validate_on_write.sh.

ARGS="${1:-$(cat)}"
[ -z "$ARGS" ] && exit 0

_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd -P)"
REPO="${CLAUDE_PROJECT_DIR:-${_HOOKDIR%/system/hooks}}"

FILE_PATH=$(printf '%s' "$ARGS" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', d) if isinstance(d, dict) else {}
    print(ti.get('file_path') or ti.get('path') or '')
except Exception:
    print('')
" 2>/dev/null)
[ -z "$FILE_PATH" ] && exit 0

# Resolve both sides to real paths so a relative path, a symlinked repo, or a trailing slash all compare.
# Tests point the match root at a scratch repo via DOCTRINE_SYNC_CODE_ROOT; unset in real use.
REPO_REAL="$(cd "${DOCTRINE_SYNC_CODE_ROOT:-$REPO}" 2>/dev/null && pwd -P)"
FILE_REAL="$(cd "$(dirname "$FILE_PATH")" 2>/dev/null && pwd -P)/$(basename "$FILE_PATH")"

case "$FILE_REAL" in
  "$REPO_REAL/CLAUDE.local.md")                NAME="CLAUDE.local.md" ;;
  "$REPO_REAL/.claude/settings.local.json")    NAME="settings.local.json" ;;
  *) exit 0 ;;
esac

# The tool is found next to THIS hook (system/hooks/../tools), never via the project dir — a hook
# that loses its tool when the project dir points elsewhere fails silently, which the first pipe
# test of this file caught (it matched the "tool missing" note and called it a pass).
TOOL="$_HOOKDIR/../tools/doctrine_sync.py"
[ -f "$TOOL" ] || { printf 'doctrine-mirror-push: %s edited but %s is missing — mirror NOT updated\n' "$NAME" "$TOOL" >&2; exit 0; }

# Tests point the tool at a scratch notes root / repo root through these two env vars; unset in real use.
EXTRA=()
[ -n "${DOCTRINE_SYNC_BRAIN_ROOT:-}" ] && EXTRA+=(--brain-root "$DOCTRINE_SYNC_BRAIN_ROOT")
[ -n "${DOCTRINE_SYNC_CODE_ROOT:-}" ]  && EXTRA+=(--code-root "$DOCTRINE_SYNC_CODE_ROOT")

OUT=$(python3 "$TOOL" push "$NAME" --reason "hook: edit on $(hostname -s 2>/dev/null || echo this-machine)" "${EXTRA[@]}" 2>&1)
rc=$?
if [ "$rc" = "0" ]; then
  printf 'doctrine-mirror-push: %s -> state/doctrine-mirror/ (the other machine will see it on its next 5-min sweep)\n' "$NAME" >&2
else
  printf 'doctrine-mirror-push (non-blocking): push of %s returned rc=%s — %s\n' "$NAME" "$rc" "$(printf '%s' "$OUT" | tail -1)" >&2
fi
exit 0
