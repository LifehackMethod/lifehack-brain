#!/bin/bash
# test_doctrine_mirror_push.sh — pipe test for system/hooks/doctrine_mirror_push.sh (PostToolUse Write|Edit).
# Proves: fires on the two mirrored paths (mirror updated), silent on any other path, always rc=0.
# ⚠ A pipe test proves the script did not crash and did what it says — NOT that the harness honours it.
#   That needs a live fire after a restart (hook-sop.md §4).
set -u
HERE="$(cd "$(dirname "$0")" && pwd -P)"; REPO="$(cd "$HERE/../../.." && pwd -P)"
HOOK="$REPO/system/hooks/doctrine_mirror_push.sh"
T="$(mktemp -d "${TMPDIR:-/tmp}/dmp-test.XXXXXX")"; trap 'rm -rf "$T"' EXIT
mkdir -p "$T/repo/.claude" "$T/brain"
printf '# rules\n' > "$T/repo/CLAUDE.local.md"; printf '{"env":{}}\n' > "$T/repo/.claude/settings.local.json"
export CLAUDE_PROJECT_DIR="$T/repo" DOCTRINE_SYNC_BRAIN_ROOT="$T/brain" DOCTRINE_SYNC_CODE_ROOT="$T/repo"
pass=0; fail=0
chk() { if [ "$1" = "$2" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL: $3 (got '$1', want '$2')"; fi; }
# 1. CLAUDE.local.md via stdin payload -> mirror appears, rc 0
ERR=$(printf '{"tool_input":{"file_path":"%s"}}' "$T/repo/CLAUDE.local.md" | bash "$HOOK" 2>&1 >/dev/null); rc=$?
chk "$rc" "0" "rc on CLAUDE.local.md"
chk "$([ -f "$T/brain/state/doctrine-mirror/CLAUDE.local.md" ] && echo yes || echo no)" "yes" "mirror written for CLAUDE.local.md"
chk "$(printf '%s' "$ERR" | grep -c 'doctrine-mirror-push: CLAUDE.local.md -> state/doctrine-mirror/')" "1" "stderr note is the SUCCESS note (not the tool-missing note)"
# 2. settings.local.json via $1 payload (the other delivery shape) -> mirror appears
bash "$HOOK" "$(printf '{"tool_input":{"file_path":"%s"}}' "$T/repo/.claude/settings.local.json")" 2>/dev/null; rc=$?
chk "$rc" "0" "rc on settings.local.json"
chk "$([ -f "$T/brain/state/doctrine-mirror/settings.local.json" ] && echo yes || echo no)" "yes" "mirror written for settings.local.json"
# 3. an unrelated file -> silent, nothing new in the mirror
before=$(ls "$T/brain/state/doctrine-mirror" | wc -l | tr -d ' ')
ERR=$(printf '{"tool_input":{"file_path":"%s"}}' "$T/repo/README.md" | bash "$HOOK" 2>&1 >/dev/null); rc=$?
chk "$rc" "0" "rc on unrelated path"; chk "$ERR" "" "silent on unrelated path"
chk "$(ls "$T/brain/state/doctrine-mirror" | wc -l | tr -d ' ')" "$before" "mirror untouched by unrelated path"
# 4. garbage payload -> rc 0, silent
ERR=$(printf 'not json' | bash "$HOOK" 2>&1 >/dev/null); rc=$?
chk "$rc" "0" "rc on garbage"; chk "$ERR" "" "silent on garbage"
# 5. a same-named file OUTSIDE the repo -> silent (path is resolved, not basename-matched)
mkdir -p "$T/elsewhere"; printf 'x' > "$T/elsewhere/CLAUDE.local.md"
ERR=$(printf '{"tool_input":{"file_path":"%s"}}' "$T/elsewhere/CLAUDE.local.md" | bash "$HOOK" 2>&1 >/dev/null); rc=$?
chk "$rc" "0" "rc on same-named outside file"; chk "$ERR" "" "silent on same-named outside file"
echo "doctrine_mirror_push pipe test: $pass passed, $fail failed"; [ "$fail" = "0" ]
