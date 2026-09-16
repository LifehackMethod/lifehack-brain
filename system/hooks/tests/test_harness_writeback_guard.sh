#!/bin/bash
# test_harness_writeback_guard.sh — deny-coverage suite for system/hooks/guard_harness_writeback.sh
# (B6.0 — this guard had NO test anywhere before this file. It ships PLUGIN-ONLY: absent from this
#  repo's own .claude/settings.json per B6.1-static-prep.md §1's G2 finding, present only in
#  hooks/hooks.json under matcher Write|Edit with command "${CLAUDE_PLUGIN_ROOT}/system/hooks/guard_harness_writeback.sh".
#  This suite therefore invokes it via that exact registered form, with CLAUDE_PLUGIN_ROOT pointed
#  at this worktree — the guard resolves "its own repo" $0-relative anyway, so this also matches
#  what happens on a real install.)
#
# ⚠ ALLOW CASES FIRST — see hook-contract.md.
#
# Hermetic: LIFEHACK_BRAIN_ROOT is pointed at a throwaway scratch git repo standing in for the
# public lifehack-brain checkout — never the real ~/lifehack-brain, never a real remote.

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/guard_harness_writeback.sh"

if [ ! -r "$GUARD" ]; then
  echo "MISSING: $GUARD — nothing to test. FAILING CLOSED."
  exit 1
fi

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/harness_writeback_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
ERRF="$SCRATCH/stderr.txt"
PASSED=0
FAILED=0

# ── fixture "public repo" standing in for ~/lifehack-brain ───────────────────────────────────────
PUBLIC="$SCRATCH/public_lifehack_brain"
mkdir -p "$PUBLIC/system/hooks"
git init -q "$PUBLIC"
git -C "$PUBLIC" config user.email "test@example.com"
git -C "$PUBLIC" config user.name "Test"
echo 'harness content' > "$PUBLIC/system/hooks/guard_write_paths.sh"
git -C "$PUBLIC" add system/hooks/guard_write_paths.sh
python3 - "$PUBLIC" <<'PY'
import subprocess, sys
repo = sys.argv[1]
subprocess.run(["git", "-C", repo, "commit", "-m", "seed"], check=True, capture_output=True)
PY

mkjson_write() {  # mkjson_write <path> <content>
  T_PATH="$1" T_CONTENT="$2" python3 -c 'import os, json; print(json.dumps({"tool_name": "Write", "tool_input": {"file_path": os.environ["T_PATH"], "content": os.environ["T_CONTENT"]}}))'
}

run_guard() {  # pipes payload from stdin
  HOME="$SCRATCH/home" CLAUDE_PLUGIN_ROOT="$REPO" LIFEHACK_BRAIN_ROOT="$PUBLIC" bash "$GUARD" 2>"$ERRF"
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

echo "=== guard_harness_writeback.sh — ALLOW cases first ==="

allow "a write OUTSIDE this repo entirely"     "$(mkjson_write "$SCRATCH/somewhere/else/notes.md" 'hi')"
allow "a write inside this repo NOT tracked by the public repo" \
  "$(mkjson_write "$REPO/desks/enver/private-notes.md" 'personal material')"
allow "a Write payload with no file_path (not the Write/Edit shape)" \
  '{"tool_name":"Write","tool_input":{}}'

echo
echo "=== DENY cases — the one protection this guard's header claims ==="

deny "a write to a path TRACKED by the public lifehack-brain repo" \
  "$(mkjson_write "$REPO/system/hooks/guard_write_paths.sh" 'duplicated harness content')" \
  "tracked in the PUBLIC lifehack-brain repo"

echo
echo "=== CANNOT-DETERMINE — reported distinctly, never folded into a silent ALLOW ==="

out=$(printf '%s' "$(mkjson_write "$REPO/system/hooks/guard_write_paths.sh" 'x')" | \
  HOME="$SCRATCH/home" CLAUDE_PLUGIN_ROOT="$REPO" LIFEHACK_BRAIN_ROOT="$SCRATCH/no-such-public-repo" \
  bash "$GUARD" 2>"$ERRF"); rc=$?
if [ "$rc" -eq 2 ] && grep -q "CANNOT-DETERMINE" "$ERRF"; then
  printf "  PASS  deny   public repo absent -> CANNOT-DETERMINE, exit 2, never a silent allow\n"
  PASSED=$((PASSED + 1))
else
  printf "  FAIL  deny   public-repo-absent case (rc=%s)\n" "$rc"
  printf "        stderr: %.300s\n" "$(cat "$ERRF")"
  FAILED=$((FAILED + 1))
fi

echo
echo "  $PASSED passed, $FAILED failed"
if [ "$FAILED" -eq 0 ]; then
  echo "--- RESULT: GREEN ---"
  exit 0
fi
echo "--- RESULT: RED ---"
exit 1
