#!/bin/bash
# test_plan_structure_guard.sh — deny-coverage suite for system/hooks/guard_plan_structure.sh
# (B6.0 — this guard had NO test anywhere before this file.)
#
# ⚠ ALLOW CASES FIRST — see hook-contract.md. This guard is a QUALITY gate, not a security
#   boundary: its own header states it fails OPEN on empty/unparseable plan text, so an empty-plan
#   case is tested as an ALLOW, not a parse-error edge case.
#
# Invocation form matches the registered one: bash "${CLAUDE_PROJECT_DIR}/system/hooks/guard_plan_structure.sh"
# (matcher: ExitPlanMode)

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/guard_plan_structure.sh"

if [ ! -r "$GUARD" ]; then
  echo "MISSING: $GUARD — nothing to test. FAILING CLOSED."
  exit 1
fi

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/plan_structure_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
ERRF="$SCRATCH/stderr.txt"
PASSED=0
FAILED=0

mkjson() {
  T_PLAN="$1" python3 -c 'import os, json; print(json.dumps({"tool_name": "ExitPlanMode", "tool_input": {"plan": os.environ["T_PLAN"]}}))'
}

run_guard() {
  mkjson "$1" | HOME="$SCRATCH/home" CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" 2>"$ERRF"
}

allow() {
  local desc="$1" plan="$2"
  out=$(run_guard "$plan"); rc=$?
  if [ "$rc" -eq 0 ]; then
    printf "  PASS  allow  %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  allow  %s  (rc=%s) OVER-BLOCK\n" "$desc" "$rc"
    printf "        stderr: %.200s\n" "$(cat "$ERRF")"
    FAILED=$((FAILED + 1))
  fi
}

deny() {
  local desc="$1" plan="$2" must="$3"
  out=$(run_guard "$plan"); rc=$?
  problems=""
  [ "$rc" -eq 2 ] || problems="${problems}rc=$rc(want 2);"
  [ -z "$out" ] || problems="${problems}stdout-not-empty;"
  errtxt="$(cat "$ERRF")"
  verdict=$(T_ERRF="$ERRF" python3 -c '
import os, json, sys
raw = open(os.environ["T_ERRF"]).read().strip()
try:
    d = json.loads(raw)
except Exception as e:
    print("stderr-not-json(%s);" % type(e).__name__); sys.exit(0)
if d.get("decision") != "block":
    print("decision!=block;")
')
  problems="$problems$verdict"
  case "$errtxt" in *"$must"*) ;; *) problems="${problems}missing(${must});" ;; esac
  if [ -z "$problems" ]; then
    printf "  PASS  deny   %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  deny   %s  ->%s\n" "$desc" "$problems"
    printf "        stderr: %.300s\n" "$errtxt"
    FAILED=$((FAILED + 1))
  fi
}

echo "=== guard_plan_structure.sh — ALLOW cases first ==="

allow "a fully-structured plan" "## Phase 1: setup
### Task A
Execute: do the thing
Verify: run the test and confirm it passes
mark done"

allow "empty plan text fails OPEN by design (quality gate, not a boundary)" ""

echo
echo "=== DENY cases — each missing structural marker the header claims to require ==="

deny "missing all three markers"    "just write some code and ship it" "Phase"
deny "has Phase+Task but no Verify" "## Phase 1
### Task: build the thing" "Verify"
deny "has Phase+Verify but no Task" "## Phase 1
we will verify this works at the end" "Task"
deny "has Task+Verify but no Phase" "### Task: build the thing
Verify: run tests" "Phase"

echo
echo "  $PASSED passed, $FAILED failed"
if [ "$FAILED" -eq 0 ]; then
  echo "--- RESULT: GREEN ---"
  exit 0
fi
echo "--- RESULT: RED ---"
exit 1
