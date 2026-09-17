#!/bin/bash
# test_brief_truncation_guard.sh — deny-coverage suite for system/hooks/guard_brief_truncation.sh
# (B6.0 — this guard had NO test anywhere before this file.)
#
# ⚠ ALLOW CASES FIRST — see hook-contract.md.
#
# Invocation form matches the registered one:
#   bash "${CLAUDE_PROJECT_DIR}/system/hooks/guard_brief_truncation.sh"  (matcher: Write|Edit|MultiEdit|Bash)
#
# Covers BOTH doors this guard's header claims: the typed-tool door (Write/Edit, sized exactly)
# and the Bash door (an overwrite-shaped shell write, gated on a fresh snapshot receipt instead of
# size, via lib/bash_write_door.sh).

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/guard_brief_truncation.sh"

if [ ! -r "$GUARD" ]; then
  echo "MISSING: $GUARD — nothing to test. FAILING CLOSED."
  exit 1
fi

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/brief_truncation_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
ERRF="$SCRATCH/stderr.txt"
PASSED=0
FAILED=0

PROJDIR="$SCRATCH/projects/demo"
mkdir -p "$PROJDIR"
BRIEF="$PROJDIR/brief.md"
python3 -c '
import sys
print("x" * 40000)
' > "$BRIEF"
BRIEF_SIZE=$(wc -c < "$BRIEF" | tr -d ' ')

mkjson_write() {  # mkjson_write <path> <content>
  T_PATH="$1" T_CONTENT="$2" python3 -c 'import os, json; print(json.dumps({"tool_name": "Write", "tool_input": {"file_path": os.environ["T_PATH"], "content": os.environ["T_CONTENT"]}}))'
}
mkjson_edit() {
  T_PATH="$1" T_OLD="$2" T_NEW="$3" python3 -c 'import os, json; print(json.dumps({"tool_name": "Edit", "tool_input": {"file_path": os.environ["T_PATH"], "old_string": os.environ["T_OLD"], "new_string": os.environ["T_NEW"]}}))'
}
mkjson_bash() {
  T_CMD="$1" python3 -c 'import os, json; print(json.dumps({"tool_name": "Bash", "tool_input": {"command": os.environ["T_CMD"]}}))'
}

SCRATCH_TMPDIR="$SCRATCH/tmp"; mkdir -p "$SCRATCH_TMPDIR"
run_guard() {
  cat | HOME="$SCRATCH/home" CLAUDE_PROJECT_DIR="$REPO" TMPDIR="$SCRATCH_TMPDIR" bash "$GUARD" 2>"$ERRF"
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

echo "=== guard_brief_truncation.sh — ALLOW cases first ==="

allow "a Write to an unrelated file"           "$(mkjson_write "$SCRATCH/notes.md" 'x')"
SMALL_NEW=$(python3 -c 'print("x" * 39000)')
allow "a small trim under both thresholds (ordinary compaction)" \
  "$(mkjson_write "$BRIEF" "$SMALL_NEW")"
allow "a Write that GROWS the brief"           "$(mkjson_write "$BRIEF" "$(python3 -c 'print("x"*50000)')")"
allow "a Bash APPEND (>>) mentioning the brief -- cannot truncate" \
  "$(mkjson_bash "echo more >> $BRIEF")"
allow "a Bash READ of the brief via python (open().read())" \
  "$(mkjson_bash "python3 -c \"print(len(open('$BRIEF').read()))\"")"
allow "an unrelated Bash command"              "$(mkjson_bash 'ls -la')"

echo
echo "=== DENY cases — every door this guard's header claims to gate ==="

BIG_SHRINK=$(python3 -c 'print("x" * 100)')
deny "typed Write shrinks the brief past BOTH thresholds (>15% AND >5000 bytes)" \
  "$(mkjson_write "$BRIEF" "$BIG_SHRINK")" "would remove"

deny "typed Edit whose old/new delta shrinks the brief past both thresholds" \
  "$(mkjson_edit "$BRIEF" "$(python3 -c 'print("x"*20000)')" "y")" "would remove"

deny "Bash overwrite-shaped write to the brief, no fresh snapshot" \
  "$(mkjson_bash "python3 -c \"open('$BRIEF','w').write('short')\"")" "OVERWRITE-shaped Bash write"

echo
echo "=== the snapshot receipt path — a fresh .pre-shrink.bak lifts the Bash-door block ==="

cp "$BRIEF" "$BRIEF.pre-shrink.bak"
out=$(printf '%s' "$(mkjson_bash "python3 -c \"open('$BRIEF','w').write('short')\"")" | run_guard); rc=$?
if [ "$rc" -eq 0 ]; then
  printf "  PASS  allow  a fresh snapshot beside the brief lifts the Bash-door block\n"
  PASSED=$((PASSED + 1))
else
  printf "  FAIL  allow  snapshot-lifts-block shape (rc=%s)\n" "$rc"
  printf "        stderr: %.300s\n" "$(cat "$ERRF")"
  FAILED=$((FAILED + 1))
fi
rm -f "$BRIEF.pre-shrink.bak"

echo
echo "=== unresolved-var scope narrowing (lead review, 2026-09-17) ==="
# An unresolved variable is NOT, on its own, evidence a Bash write lands in a project brief --
# false-block regression a lead review caught in the first cut of the var-resolve fix.
# NOTE: these use a single ">" (overwrite), never ">>" -- this guard SCRUBS ">>" before analysis
# (appends cannot truncate, so they are never its business, unrelated to this fix).

allow "an ordinary \$TMPDIR write, unrelated to any brief" \
  "$(mkjson_bash "echo x > \"\$TMPDIR/foo.txt\"; cat \"$BRIEF\" > /dev/null")"

allow "unresolved var write elsewhere, brief only READ in the same command" \
  "$(mkjson_bash "printf 'x' > \"\$UNSET_BRIEF_VAR/scratch/notes.md\"; python3 -c \"print(len(open('$BRIEF').read()))\"")"

deny "unresolved var whose remainder looks like a project brief -- names the var" \
  "$(mkjson_bash "cat > \"\$UNSET_BRIEF_VAR/projects/demo/brief.md\"")" "UNSET_BRIEF_VAR"

deny "a bare unresolved var with no remainder, brief mentioned elsewhere -- could be anything" \
  "$(mkjson_bash "cat > \"\$UNSET_BRIEF_VAR\"; cat \"$BRIEF\" > /dev/null")" "UNSET_BRIEF_VAR"

echo
echo "  $PASSED passed, $FAILED failed"
if [ "$FAILED" -eq 0 ]; then
  echo "--- RESULT: GREEN ---"
  exit 0
fi
echo "--- RESULT: RED ---"
exit 1
