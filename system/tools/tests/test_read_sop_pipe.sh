#!/bin/bash
# read_sop.sh must stamp its receipt even when stdout is truncated by `| head -1` (SIGPIPE). v2 3b-n2.
HERE="$(cd "$(dirname "$0")/.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
export HOME="$T/home"; mkdir -p "$HOME"; export CLAUDE_CODE_SESSION_ID="pipe-test-$$"
OUT="$(bash "$HERE/read_sop.sh" hook 2>&1 | head -1)"
R="$HOME/.claude/run/sop/hook.$CLAUDE_CODE_SESSION_ID.receipt"
if [ -s "$R" ] && [ -n "$OUT" ]; then echo "   ok   receipt stamped despite | head -1"; echo "passed=1 failed=0"; exit 0; fi
echo "  FAIL  no receipt after | head -1"; echo "passed=0 failed=1"; exit 1
