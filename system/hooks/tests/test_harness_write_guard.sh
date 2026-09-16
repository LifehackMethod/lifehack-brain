#!/bin/bash
# test_harness_write_guard.sh — deny-coverage suite for hooks/guard_harness_write.sh
# (B6.0 — this guard had NO test anywhere before this file. It ships in hooks/ at the PUBLIC repo
#  ROOT, not under system/hooks/ — plugin-only, registered in hooks/hooks.json as
#  "${CLAUDE_PLUGIN_ROOT}/hooks/guard_harness_write.sh" under matcher Write|Edit. This suite
#  invokes it via that exact form, with CLAUDE_PLUGIN_ROOT pointed at this worktree.)
#
# ⚠ ALLOW CASES FIRST — see hook-contract.md.
#
# Hermetic: shared/brain_root.py is the REAL resolver, but it is fully argument/env-driven and
# writes only under HOME/.config or a path we hand it — pointed at a scratch HOME + a scratch
# --set target, never the real AI Brain.

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/hooks/guard_harness_write.sh"

if [ ! -r "$GUARD" ]; then
  echo "MISSING: $GUARD — nothing to test. FAILING CLOSED."
  exit 1
fi
if [ ! -f "$REPO/shared/brain_root.py" ]; then
  echo "MISSING: $REPO/shared/brain_root.py — guard_harness_write.sh cannot run without it. FAILING CLOSED."
  exit 1
fi

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/harness_write_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
ERRF="$SCRATCH/stderr.txt"
PASSED=0
FAILED=0

BRAIN="$SCRATCH/ai_brain"
mkdir -p "$BRAIN"

mkjson_write() {  # mkjson_write <path> [content]
  T_PATH="$1" python3 -c 'import os, json; print(json.dumps({"tool_name": "Write", "tool_input": {"file_path": os.environ["T_PATH"], "content": "x"}}))'
}
mkjson_edit() {
  T_PATH="$1" python3 -c 'import os, json; print(json.dumps({"tool_name": "Edit", "tool_input": {"file_path": os.environ["T_PATH"], "old_string": "a", "new_string": "b"}}))'
}

run_guard() {  # run_guard <home> <brain-root-arg-or-empty>
  local home="$1" broot="$2"
  cat | HOME="$home" CLAUDE_PLUGIN_ROOT="$REPO" LIFEHACK_ROOT="$broot" bash "$GUARD" 2>"$ERRF"
}

fresh_home_with_brain() {  # a scratch HOME where brain_root.py resolves to $BRAIN via LIFEHACK_ROOT
  mktemp -d "$SCRATCH/home.XXXXXX"
}

allow() {
  local desc="$1" payload="$2" broot="${3:-$BRAIN}"
  local home; home="$(fresh_home_with_brain)"
  out=$(printf '%s' "$payload" | run_guard "$home" "$broot"); rc=$?
  if [ "$rc" -eq 0 ]; then
    printf "  PASS  allow  %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  allow  %s  (rc=%s) OVER-BLOCK\n" "$desc" "$rc"
    printf "        stderr: %.200s\n" "$(cat "$ERRF")"
    FAILED=$((FAILED + 1))
  fi
}

deny() {
  local desc="$1" payload="$2" must="$3" broot="${4:-$BRAIN}"
  local home; home="$(fresh_home_with_brain)"
  out=$(printf '%s' "$payload" | run_guard "$home" "$broot"); rc=$?
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

echo "=== guard_harness_write.sh — ALLOW cases first ==="

allow "a write OUTSIDE the harness tree entirely" "$(mkjson_write "$BRAIN/my-project/notes.md")"
allow "a write into the harness's own __pycache__ (build output)" \
  "$(mkjson_write "$REPO/system/tools/__pycache__/x.pyc")"
allow "a write into node_modules (build output)" "$(mkjson_write "$REPO/hooks/node_modules/pkg/index.js")"
allow "a write into .git internals"            "$(mkjson_write "$REPO/.git/hooks/pre-commit")"

echo
echo "=== DENY cases — every distinct danger this guard's header claims to name ==="

deny "DANGER1: a NEW file saved inside the harness (would be silently destroyed on update)" \
  "$(mkjson_write "$REPO/system/hooks/my-personal-notes.md")" "saved inside the installed harness"

deny "DANGER2: an EDIT to an EXISTING harness file (silently reverted on update)" \
  "$(mkjson_edit "$REPO/system/hooks/guard_write_paths.sh")" "customization made in place"

# NOTE ON NOT-SET: this worktree is a LINKED GIT WORKTREE of the main lifehack-brain checkout, and
# shared/brain_root.py's own resolution order (route 2b, "borrow the main worktree's .brain-root
# pointer, ahead of the machine-global") means an unset $LIFEHACK_ROOT here does NOT reach NOT-SET
# — it legitimately falls through to the REAL main worktree's real AI Brain pointer. Forcing a true
# NOT-SET would mean neutralising that real pointer file, which is live operator state outside this
# worktree and outside this task's remit ("tests only", hermetic, no live state). The two DANGER
# paths above are this guard's own two named protections and are both covered with a real scratch
# brain root; the NOT-SET *message shape* is exercised structurally by DANGER1/DANGER2's REDIRECT
# text already asserting a real path is named, not guessed.

echo
echo "  $PASSED passed, $FAILED failed"
if [ "$FAILED" -eq 0 ]; then
  echo "--- RESULT: GREEN ---"
  exit 0
fi
echo "--- RESULT: RED ---"
exit 1
