#!/bin/bash
# test_gmail_destructive_guard.sh — deny-coverage suite for system/hooks/guard_gmail_destructive.sh
# (B6.0 — this guard had NO test anywhere before this file; sheets+send are covered elsewhere via
#  test_sheet_guards.sh / test_gmail_send_guard.sh, but the destructive-verb guard itself was not.)
#
# ⚠ ALLOW CASES FIRST — see hook-contract.md.
#
# Invocation form matches the registered one: bash "${CLAUDE_PROJECT_DIR}/system/hooks/guard_gmail_destructive.sh"
# No real gws/gmail call is ever made -- this guard is a pure text/argv parser and never executes
# the command it inspects.

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/guard_gmail_destructive.sh"

if [ ! -r "$GUARD" ]; then
  echo "MISSING: $GUARD — nothing to test. FAILING CLOSED."
  exit 1
fi

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/gmail_destructive_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
ERRF="$SCRATCH/stderr.txt"
PASSED=0
FAILED=0

mkjson() {
  T_CMD="$1" python3 -c 'import os, json; print(json.dumps({"tool_name": "Bash", "tool_input": {"command": os.environ["T_CMD"]}}))'
}

run_guard() {
  mkjson "$1" | HOME="$SCRATCH/home" CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" 2>"$ERRF"
}

allow() {
  local desc="$1" cmd="$2"
  out=$(run_guard "$cmd"); rc=$?
  if [ "$rc" -eq 0 ]; then
    printf "  PASS  allow  %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  allow  %s  (rc=%s) OVER-BLOCK\n" "$desc" "$rc"
    printf "        stderr: %.200s\n" "$(cat "$ERRF")"
    FAILED=$((FAILED + 1))
  fi
}

deny() {  # deny <desc> <cmd> <must-contain>
  local desc="$1" cmd="$2" must="$3"
  out=$(run_guard "$cmd"); rc=$?
  problems=""
  [ "$rc" -eq 2 ] || problems="${problems}rc=$rc(want 2);"
  [ -z "$out" ] || problems="${problems}stdout-not-empty;"
  errtxt="$(cat "$ERRF")"
  verdict=$(T_ERRF="$ERRF" python3 -c '
import os, json, sys
raw = open(os.environ["T_ERRF"]).read().strip()
if not raw:
    print("stderr-empty;"); sys.exit(0)
try:
    d = json.loads(raw)
except Exception as e:
    print("stderr-not-json(%s);" % type(e).__name__); sys.exit(0)
r = d.get("reason", "")
# NOTE: not every deny path on this guard carries a WHY label (UNRESOLVED_DENY does not) --
# REDIRECT and RULE are the two markers all three deny messages here share.
missing = [k for k in ("REDIRECT:", "RULE:") if k not in r]
if d.get("decision") != "block":
    missing.append("decision!=block")
print(("missing:" + ",".join(missing) + ";") if missing else "")
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

echo "=== guard_gmail_destructive.sh — ALLOW cases first ==="

allow "an unrelated command"                  "ls -la"
allow "another gws service entirely"          "gws calendar events list --params x"
allow "a label move (reversible)"             "gws gmail users threads modify --id 18abc --add-label-ids L1"
allow "untrash — recovery, must never be blocked" \
                                               "gws gmail users threads untrash --id 18abc"
allow "messages list (a read)"                "gws gmail users messages list --params x"
allow "a mention inside a commit message, never executed" \
                                               "echo 'guard blocks gws gmail users messages delete'"
allow "labels delete (a label is not mail)"   "gws gmail users labels delete --id L1"
allow "a payload body that merely CONTAINS the word delete" \
                                               'gws gmail users messages list --params {"q":"delete"}'

echo
echo "=== DENY cases — every destructive verb this guard's header claims to block ==="

deny "messages delete"                        "gws gmail users messages delete --id x" "BLOCKED: destructive Gmail verb"
deny "threads batchDelete"                    "gws gmail users threads batchDelete --params x" "BLOCKED: destructive Gmail verb"
deny "threads trash"                          "gws gmail users threads trash --id 18abc" "BLOCKED: destructive Gmail verb"
deny "binary held in a variable (indirection)" 'V=gws ; $V gmail users messages delete --id x' "BLOCKED"
deny "an operation hidden behind a variable (DEFAULT-DENY, unresolved)" 'gws gmail users messages $VERB --id x' "could not resolve this command"
deny_raw_unparseable() {
  out=$(printf 'not json at all' | HOME="$SCRATCH/home" CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" 2>"$ERRF"); rc=$?
  if [ "$rc" -eq 2 ]; then
    printf "  PASS  deny   unparseable stdin fails CLOSED\n"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  deny   unparseable stdin fails CLOSED (rc=%s)\n" "$rc"; FAILED=$((FAILED + 1))
  fi
}
deny_raw_unparseable

echo
echo "  $PASSED passed, $FAILED failed"
if [ "$FAILED" -eq 0 ]; then
  echo "--- RESULT: GREEN ---"
  exit 0
fi
echo "--- RESULT: RED ---"
exit 1
