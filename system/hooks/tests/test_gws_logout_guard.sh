#!/bin/bash
# test_gws_logout_guard.sh — deny-coverage suite for system/hooks/guard_gws_logout.sh
# (B6.0 — this guard had NO test anywhere before this file.)
#
# ⚠ ALLOW CASES FIRST — see hook-contract.md.
#
# NOTE ON NEAR-MISS: this guard's own header says it is DELIBERATELY INVERTED from the house
# "match the action, never the bare keyword" rule -- it fires on a MENTION too, because the
# protected action (gws auth logout) has NO UNDO. So the benign near-miss case here is a command
# that shares NEITHER the verb nor the phrase, never a quoted mention of "gws auth logout" (which
# this guard, correctly, still blocks).
#
# Invocation form matches the registered one: bash "${CLAUDE_PROJECT_DIR}/system/hooks/guard_gws_logout.sh"
# No real gws call is ever made.

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/guard_gws_logout.sh"

if [ ! -r "$GUARD" ]; then
  echo "MISSING: $GUARD — nothing to test. FAILING CLOSED."
  exit 1
fi

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/gws_logout_test.XXXXXX")"
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

deny() {
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

echo "=== guard_gws_logout.sh — ALLOW cases first ==="

allow "unrelated command"                    "ls -la"
allow "a different gws auth verb"            "gws auth login"
allow "gws auth status (read-only)"          "gws auth status"
allow "a lookalike word, not the phrase"     "gws auth logouts --help"
allow "a different binary entirely"          "mygws auth logout"

echo
echo "=== DENY cases — every shape this guard's header claims to catch ==="

deny "bare invocation"                        "gws auth logout" "no undo"
deny "chained after a semicolon (the donor bug this guard fixed)" \
                                               "gws auth logout;echo done" "no undo"
deny "chained with &&"                        "gws auth logout&&echo done" "no undo"
deny "piped"                                  "gws auth logout|tee /tmp/x" "no undo"
deny "preceded by another command"            "echo x; gws auth logout; echo y" "no undo"
deny "via a full path"                        "/usr/local/bin/gws auth logout" "no undo"
deny "a mere MENTION inside quotes — deliberately still blocked (see header)" \
                                               'echo "never run gws auth logout"' "no undo"

echo
echo "  $PASSED passed, $FAILED failed"
if [ "$FAILED" -eq 0 ]; then
  echo "--- RESULT: GREEN ---"
  exit 0
fi
echo "--- RESULT: RED ---"
exit 1
