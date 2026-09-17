#!/bin/bash
# test_hook_edit_switch.sh — K1/S1 guard runtime tests for the register-backed
# hook-edit protection switch.
#
# Verifies:
#   · default / missing register -> a hook-edit is BLOCKED (rc=2)
#   · state=suspended, expiry future -> ALLOWED with NOTICE (rc=0)
#   · state=suspended, expiry past  -> BLOCKED with ALARM (rc=2)
#
# Run: bash system/hooks/tests/test_hook_edit_switch.sh

set -u

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
REAL_GUARD="$REPO/system/hooks/guard_hook_sop_read.sh"

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/hook_edit_switch_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT

PASSED=0
FAILED=0

mkjson() {
  local cmd="$1" sid="${2:-test-$RANDOM}"
  T_CMD="$cmd" T_SID="$sid" python3 -c '
import os, json
print(json.dumps({"tool_name":"Bash","tool_input":{"command":os.environ["T_CMD"]},"session_id":os.environ["T_SID"]}))
'
}

run_guard() {
  local fixture="$1" today="$2" command_str="$3"
  local guard="$fixture/system/hooks/guard_hook_sop_read.sh"
  local errfile="$SCRATCH/stderr_$$.txt"
  rm -f "$errfile"
  local rc=0
  mkjson "$command_str" "test-$RANDOM" | HOME="$fixture" CLAUDE_CODE_SESSION_ID="test-session" \
    LHB_REGISTER_TODAY="$today" bash "$guard" 2>"$errfile" || rc=$?
  cat "$errfile" >"$SCRATCH/stderr.txt"
  return "$rc"
}

allow() {
  local desc="$1" fixture="$2" today="$3" command_str="$4"
  rc=0; run_guard "$fixture" "$today" "$command_str" >/dev/null || rc=$?
  if [ "$rc" -eq 0 ]; then
    printf "  PASS  allow  %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  allow  %s  (rc=%s, want 0) OVER-BLOCK\n" "$desc" "$rc"
    printf "        stderr: %.200s\n" "$(cat "$SCRATCH/stderr.txt")"
    FAILED=$((FAILED + 1))
  fi
}

deny() {
  local desc="$1" fixture="$2" today="$3" must="$4" command_str="$5"
  rc=0; run_guard "$fixture" "$today" "$command_str" >/dev/null || rc=$?
  problems=""
  [ "$rc" -eq 2 ] || problems="${problems}rc=$rc(want 2);"
  errtxt="$(cat "$SCRATCH/stderr.txt")"
  case "$errtxt" in *"$must"*) ;; *) problems="${problems}missing(${must});" ;; esac
  if [ -z "$problems" ]; then
    printf "  PASS  deny   %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  deny   %s  ->%s\n" "$desc" "$problems"
    printf "        stderr: %.300s\n" "$errtxt"
    FAILED=$((FAILED + 1))
  fi
}

make_fixture() {
  local state="$1" expiry="$2"
  local f="$SCRATCH/fixture_${state}_${expiry:-none}"
  mkdir -p "$f/system/hooks" "$f/system/register"
  cp "$REAL_GUARD" "$f/system/hooks/guard_hook_sop_read.sh"
  chmod +x "$f/system/hooks/guard_hook_sop_read.sh"
  python3 -c '
import json, sys
state, expiry = sys.argv[1], sys.argv[2]
row = {
  "id": "hook:public:/system/hooks/guard_hook_sop_read.sh@PreToolUse:Bash|Write|Edit",
  "type": "hook", "repo": "public",
  "path": "/system/hooks/guard_hook_sop_read.sh",
  "exists": True, "sha": "010a8c21",
  "needs": [], "returns": [],
  "cost_bytes": None, "cost_ms": None,
  "event": "PreToolUse", "matcher": "Bash|Write|Edit", "args": "",
  "status": "Checking the hook SOP was read first...",
  "surfaces": ["settings", "plugin"],
  "status_conflicts": [], "if": None,
  "launch_mode": "both", "group": None,
  "state": state, "expiry": expiry if expiry != "null" else None,
}
open(sys.argv[3], "w").write(json.dumps(row, sort_keys=True) + "\n")
' "$state" "$expiry" "$f/system/register/register.jsonl"
  echo "$f"
}

TODAY="2026-09-16"
FUTURE="2026-10-01"
PAST="2026-09-01"

ACTIVE_FIXTURE="$(make_fixture active null)"
SUSPENDED_FIXTURE="$(make_fixture suspended "$FUTURE")"
EXPIRED_FIXTURE="$(make_fixture suspended "$PAST")"
MISSING_FIXTURE="$SCRATCH/fixture_missing"
mkdir -p "$MISSING_FIXTURE/system/hooks"
cp "$REAL_GUARD" "$MISSING_FIXTURE/system/hooks/guard_hook_sop_read.sh"
chmod +x "$MISSING_FIXTURE/system/hooks/guard_hook_sop_read.sh"

printf "=== guard_hook_sop_read.sh — switch runtime tests ===\n"

# The command must mention the hook plane for the guard to inspect it.
deny   "default active (no receipt) blocks hook-edit"      "$ACTIVE_FIXTURE"    "$TODAY" "BLOCKED"       "chmod 644 $ACTIVE_FIXTURE/system/hooks/target.sh"
allow  "suspended-unexpired allows hook-edit with NOTICE"  "$SUSPENDED_FIXTURE" "$TODAY"                 "chmod 644 $SUSPENDED_FIXTURE/system/hooks/target.sh"
deny   "suspended-expired blocks hook-edit with ALARM"     "$EXPIRED_FIXTURE"   "$TODAY" "EXPIRY HAS PASSED" "chmod 644 $EXPIRED_FIXTURE/system/hooks/target.sh"
deny   "missing register fails safe (blocks)"              "$MISSING_FIXTURE"   "$TODAY" "BLOCKED"       "chmod 644 $MISSING_FIXTURE/system/hooks/target.sh"

echo ""
echo "$PASSED passed, $FAILED failed"
if [ "$FAILED" -eq 0 ]; then
  echo "--- RESULT: GREEN ---"
  exit 0
else
  echo "--- RESULT: RED ---"
  exit 1
fi
