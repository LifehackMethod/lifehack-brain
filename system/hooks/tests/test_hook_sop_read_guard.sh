#!/bin/bash
# test_hook_sop_read_guard.sh — deny-coverage suite for system/hooks/guard_hook_sop_read.sh
# (B6.0 — this guard had NO test anywhere before this file.)
#
# ⚠ ALLOW CASES FIRST — see hook-contract.md.
#
# SCOPE NOTE: in THIS repo's own .claude/settings.json (the registered form actually in force
# here), this hook is registered on matcher `Bash` ONLY -- not `Bash|Write|Edit` as its own header
# banner describes (that is the plugin hooks.json's registration; see B6.1-static-prep.md §1's
# "Event : Matcher" column vs the settings.json dump, which shows plain `Bash`). This suite tests
# the Bash-shaped path, which is what actually reaches this guard under the current registration —
# the Write/Edit branch in the script is real code but currently unreachable via this repo's own
# wiring. That gap is reported as a FINDING in the B6.0 report, not silently worked around here.
#
# Invocation form matches the registered one: bash "${CLAUDE_PROJECT_DIR}/system/hooks/guard_hook_sop_read.sh"

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/guard_hook_sop_read.sh"

if [ ! -r "$GUARD" ]; then
  echo "MISSING: $GUARD — nothing to test. FAILING CLOSED."
  exit 1
fi

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/hook_sop_read_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
ERRF="$SCRATCH/stderr.txt"
PASSED=0
FAILED=0

mkjson() {  # mkjson <command> <session-id>
  T_CMD="$1" T_SID="$2" python3 -c '
import os, json
print(json.dumps({"tool_name": "Bash", "tool_input": {"command": os.environ["T_CMD"]}, "session_id": os.environ["T_SID"]}))
'
}

run_guard() {  # run_guard <cmd> <session-id> <home>
  local cmd="$1" sid="$2" home="$3"
  mkjson "$cmd" "$sid" | HOME="$home" CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" 2>"$ERRF"
}

fresh_home() { mktemp -d "$SCRATCH/home.XXXXXX"; }

allow() {
  local desc="$1" cmd="$2" sid="${3:-allow-$RANDOM}" home="${4:-$(fresh_home)}"
  out=$(run_guard "$cmd" "$sid" "$home"); rc=$?
  if [ "$rc" -eq 0 ]; then
    printf "  PASS  allow  %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  allow  %s  (rc=%s) OVER-BLOCK\n" "$desc" "$rc"
    printf "        stderr: %.200s\n" "$(cat "$ERRF")"
    FAILED=$((FAILED + 1))
  fi
}

deny() {
  local desc="$1" cmd="$2" must="$3" sid="${4:-deny-$RANDOM}" home="${5:-$(fresh_home)}"
  out=$(run_guard "$cmd" "$sid" "$home"); rc=$?
  problems=""
  [ "$rc" -eq 2 ] || problems="${problems}rc=$rc(want 2);"
  [ -z "$out" ] || problems="${problems}stdout-not-empty;"
  errtxt="$(cat "$ERRF")"
  case "$errtxt" in *"$must"*) ;; *) problems="${problems}missing(${must});" ;; esac
  if [ -z "$problems" ]; then
    printf "  PASS  deny   %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  deny   %s  ->%s\n" "$desc" "$problems"
    printf "        stderr: %.300s\n" "$errtxt"
    FAILED=$((FAILED + 1))
  fi
}

echo "=== guard_hook_sop_read.sh — ALLOW cases first ==="

allow "an unrelated command"                        "ls -la"
allow "reading a hook (grep)"                        "grep -n WHY $REPO/system/hooks/guard_write_paths.sh"
allow "reading a hook (cat)"                         "cat $REPO/system/hooks/guard_write_paths.sh"
allow "running a hook (the fire-test fleet's own shape)" "bash $REPO/system/hooks/guard_write_paths.sh"
allow "git checkout of a hook (the emergency repair path)" "git checkout -- $REPO/system/hooks/guard_write_paths.sh"
allow "a mention of system/hooks/ with no write verb"  "echo talking about system/hooks/ here"

echo
echo "=== DENY cases — write-shaped Bash into the hook plane, SOP unread ==="

deny "chmod on a hook"        "chmod 644 $REPO/system/hooks/guard_write_paths.sh" "hook SOP has not been read"
deny "sed -i on a hook"       "sed -i s/x/y/ $REPO/system/hooks/guard_write_paths.sh" "hook SOP has not been read"
deny "redirect (>) into a hook" "echo bad > $REPO/system/hooks/guard_write_paths.sh" "hook SOP has not been read"
deny "cp into the hook plane" "cp /etc/hosts $REPO/system/hooks/guard_write_paths.sh" "hook SOP has not been read"

echo
echo "=== the receipt path — a real SOP read unlocks the write, once, per session ==="

SID_R="receipt-$RANDOM"
HOME_R="$(fresh_home)"
CMD_CHMOD="chmod 644 $REPO/system/hooks/guard_write_paths.sh"
out=$(run_guard "$CMD_CHMOD" "$SID_R" "$HOME_R"); rc1=$?
mkdir -p "$HOME_R/.claude/run/sop"
touch "$HOME_R/.claude/run/sop/hook.$SID_R.receipt"
out=$(run_guard "$CMD_CHMOD" "$SID_R" "$HOME_R"); rc2=$?
if [ "$rc1" -eq 2 ] && [ "$rc2" -eq 0 ]; then
  printf "  PASS  allow  a stamped receipt for this exact session unlocks the write\n"
  PASSED=$((PASSED + 1))
else
  printf "  FAIL  allow  receipt-unlocks-write shape (rc1=%s rc2=%s)\n" "$rc1" "$rc2"
  FAILED=$((FAILED + 1))
fi

# a STALE receipt (older than the 12h TTL) must not unlock the write
SID_S="stale-$RANDOM"
HOME_S="$(fresh_home)"
mkdir -p "$HOME_S/.claude/run/sop"
STALE_RECEIPT="$HOME_S/.claude/run/sop/hook.$SID_S.receipt"
touch "$STALE_RECEIPT"
STALE_RECEIPT="$STALE_RECEIPT" python3 -c "
import os
p = os.environ['STALE_RECEIPT']
old = 13 * 3600
t = os.path.getmtime(p) - old
os.utime(p, (t, t))
"
deny "a receipt older than 12h does not unlock the write" "$CMD_CHMOD" "hook SOP has not been read" "$SID_S" "$HOME_S"

echo
echo "  $PASSED passed, $FAILED failed"
if [ "$FAILED" -eq 0 ]; then
  echo "--- RESULT: GREEN ---"
  exit 0
fi
echo "--- RESULT: RED ---"
exit 1
