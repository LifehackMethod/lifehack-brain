#!/bin/bash
# test_gh_account_switch_guard.sh — deny-coverage suite for system/hooks/guard_gh_account_switch.sh
# (B6.0 — this guard had NO test anywhere before this file.)
#
# ⚠ ALLOW CASES FIRST — see hook-contract.md.
#
# Zone: this guard only fires when the session's `cwd` is inside the ClaudeOps clone, the Drive
# spine, THIS declaring repo (resolved $0-relative — i.e. this worktree, since the guard script
# lives under it), or CLAUDE_PROJECT_DIR. We set the payload's "cwd" to this worktree's own root so
# the guard's zone check passes the same way it would for a real session working here, and also
# test the OUT-OF-ZONE case explicitly (a real near-miss the header itself documents).
#
# Invocation form matches the registered one: bash "${CLAUDE_PROJECT_DIR}/system/hooks/guard_gh_account_switch.sh"

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/guard_gh_account_switch.sh"

if [ ! -r "$GUARD" ]; then
  echo "MISSING: $GUARD — nothing to test. FAILING CLOSED."
  exit 1
fi

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/gh_account_switch_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
ERRF="$SCRATCH/stderr.txt"
PASSED=0
FAILED=0

mkjson() {  # mkjson <command> <cwd>
  T_CMD="$1" T_CWD="$2" python3 -c '
import os, json
print(json.dumps({"tool_name": "Bash", "tool_input": {"command": os.environ["T_CMD"]}, "cwd": os.environ["T_CWD"]}))
'
}

run_guard() {  # run_guard <command> <cwd> [owner-env-value]
  local cmd="$1" cwd="$2" owner="${3:-}"
  mkjson "$cmd" "$cwd" | HOME="$SCRATCH/home" CLAUDE_PROJECT_DIR="$REPO" LIFEHACK_OWNER_GH_USER="$owner" bash "$GUARD" 2>"$ERRF"
}

allow() {
  local desc="$1" cmd="$2" cwd="${3:-$REPO}" owner="${4:-}"
  out=$(run_guard "$cmd" "$cwd" "$owner"); rc=$?
  if [ "$rc" -eq 0 ]; then
    printf "  PASS  allow  %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  allow  %s  (rc=%s) OVER-BLOCK\n" "$desc" "$rc"
    printf "        stderr: %.200s\n" "$(cat "$ERRF")"
    FAILED=$((FAILED + 1))
  fi
}

deny() {  # deny <desc> <cmd> <must-contain> [cwd]
  local desc="$1" cmd="$2" must="$3" cwd="${4:-$REPO}"
  out=$(run_guard "$cmd" "$cwd"); rc=$?
  problems=""
  [ "$rc" -eq 2 ] || problems="${problems}rc=$rc(want 2);"
  [ -z "$out" ] || problems="${problems}stdout-not-empty;"
  errtxt="$(cat "$ERRF")"
  case "$errtxt" in *"$must"*) ;; *) problems="${problems}missing(${must});" ;; esac
  case "$errtxt" in *WHY*) ;; *) problems="${problems}no-WHY;" ;; esac
  case "$errtxt" in *REDIRECT*) ;; *) problems="${problems}no-REDIRECT;" ;; esac
  if [ -z "$problems" ]; then
    printf "  PASS  deny   %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  deny   %s  ->%s\n" "$desc" "$problems"
    printf "        stderr: %.300s\n" "$errtxt"
    FAILED=$((FAILED + 1))
  fi
}

echo "=== guard_gh_account_switch.sh — ALLOW cases first ==="

allow "read-only gh auth status"              "gh auth status"
allow "unrelated gh command"                  "gh repo view LifehackMethod/lifehack-brain"
allow "the repair direction: switch back to the owner account" \
                                               "gh auth switch --user realowner" "$REPO" "realowner"
allow "out-of-zone session never matched at all" \
                                               "gh auth login" "/tmp/definitely-not-a-guarded-zone-$$"

echo
echo "=== DENY cases — every distinct verb this guard's header claims to mutate global gh state ==="

deny "gh auth login"                          "gh auth login" "MUTATES GLOBAL"
deny "gh auth logout"                         "gh auth logout" "MUTATES GLOBAL"
deny "gh auth refresh"                        "gh auth refresh" "MUTATES GLOBAL"
deny "gh auth switch to a non-owner account"  "gh auth switch --user someoneelse" "MUTATES GLOBAL"

echo
echo "  $PASSED passed, $FAILED failed"
if [ "$FAILED" -eq 0 ]; then
  echo "--- RESULT: GREEN ---"
  exit 0
fi
echo "--- RESULT: RED ---"
exit 1
