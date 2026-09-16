#!/bin/bash
# test_disable_model_invocation_guard.sh — deny-coverage suite for
# system/hooks/guard_disable_model_invocation.sh (B6.0 — this guard had NO test anywhere before
# this file.)
#
# ⚠ ALLOW CASES FIRST — see hook-contract.md.
#
# Invocation form matches the registered one:
#   bash "${CLAUDE_PROJECT_DIR}/system/hooks/guard_disable_model_invocation.sh"  (matcher: Write|Edit|MultiEdit)

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/guard_disable_model_invocation.sh"

if [ ! -r "$GUARD" ]; then
  echo "MISSING: $GUARD — nothing to test. FAILING CLOSED."
  exit 1
fi

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/disable_model_invocation_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
ERRF="$SCRATCH/stderr.txt"
PASSED=0
FAILED=0

mkjson_write() {
  T_PATH="$1" T_CONTENT="$2" python3 -c 'import os, json; print(json.dumps({"tool_name": "Write", "tool_input": {"file_path": os.environ["T_PATH"], "content": os.environ["T_CONTENT"]}}))'
}
mkjson_edit() {
  T_PATH="$1" T_OLD="$2" T_NEW="$3" python3 -c 'import os, json; print(json.dumps({"tool_name": "Edit", "tool_input": {"file_path": os.environ["T_PATH"], "old_string": os.environ["T_OLD"], "new_string": os.environ["T_NEW"]}}))'
}
mkjson_multiedit() {  # mkjson_multiedit <path> <new1> <new2>
  T_PATH="$1" T_N1="$2" T_N2="$3" python3 -c '
import os, json
print(json.dumps({"tool_name": "MultiEdit", "tool_input": {"file_path": os.environ["T_PATH"], "edits": [
    {"old_string": "a", "new_string": os.environ["T_N1"]},
    {"old_string": "b", "new_string": os.environ["T_N2"]},
]}}))
'
}

run_guard() {
  cat | HOME="$SCRATCH/home" CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" 2>"$ERRF"
}

allow() {
  local desc="$1" payload="$2"
  out=$(printf '%s' "$payload" | run_guard); rc=$?
  if [ "$rc" -eq 0 ]; then
    printf "  PASS  allow  %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  allow  %s  (rc=%s) OVER-BLOCK\n" "$desc" "$rc"
    printf "        stderr: %.200s\n" "$(cat "$ERRF")"
    FAILED=$((FAILED + 1))
  fi
}

deny() {
  local desc="$1" payload="$2" must="$3"
  out=$(printf '%s' "$payload" | run_guard); rc=$?
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

echo "=== guard_disable_model_invocation.sh — ALLOW cases first ==="

allow "a normal SKILL.md write, no flag"       "$(mkjson_write "$SCRATCH/SKILL.md" '---
description: does a thing
---
body')"
allow "a Write to a non-SKILL.md file"         "$(mkjson_write "$SCRATCH/notes.md" 'disable-model-invocation: true')"
allow "a bare MENTION in prose, discussing the retired flag" \
  "$(mkjson_write "$SCRATCH/SKILL.md" 'This skill historically carried `disable-model-invocation: true` before it was retired fleet-wide.')"
allow "an Edit unrelated to the flag"          "$(mkjson_edit "$SCRATCH/SKILL.md" 'old text' 'new text')"

echo
echo "=== DENY cases — every tool shape this guard's header claims to cover ==="

deny "Write installs the frontmatter key"      "$(mkjson_write "$SCRATCH/SKILL.md" '---
description: x
disable-model-invocation: true
---
body')" "disable-model-invocation"

deny "Edit installs the frontmatter key"       "$(mkjson_edit "$SCRATCH/SKILL.md" 'description: x' 'description: x
disable-model-invocation: true')" "disable-model-invocation"

deny "MultiEdit installs the frontmatter key in one of several edits" \
  "$(mkjson_multiedit "$SCRATCH/SKILL.md" 'harmless' 'disable-model-invocation: true')" "disable-model-invocation"

echo
echo "  $PASSED passed, $FAILED failed"
if [ "$FAILED" -eq 0 ]; then
  echo "--- RESULT: GREEN ---"
  exit 0
fi
echo "--- RESULT: RED ---"
exit 1
