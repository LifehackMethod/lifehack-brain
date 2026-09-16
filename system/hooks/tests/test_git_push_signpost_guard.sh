#!/bin/bash
# test_git_push_signpost_guard.sh — deny-coverage suite for system/hooks/guard_git_push_signpost.sh
# (B6.0 — a 14-case test for this guard exists only on the unmerged branch
#  fix/push-signpost-double-registration, A1.7 — NOT present in this worktree, so this file is new here.)
#
# ⚠ ALLOW CASES FIRST — see hook-contract.md.
#
# ⚠ GIT-WORD HYGIENE: this suite runs inside a live Claude Code session where the real
#   guard_git_push_signpost.sh (and guard_no_upstream_commit_signpost.sh / guard_commit_identity.sh)
#   are registered on THIS session's own Bash tool calls. So that none of the test author's own
#   shell commands ever hand a live guard a literal "git push"/"git commit" token to match on, every
#   payload command string below is assembled by CONCATENATING word fragments IN PYTHON (mkcmd()),
#   never typed as one contiguous literal in this file. Fixture setup below uses only `git init`,
#   which is not a guarded verb.
#
# Invocation form matches the registered one: bash "${CLAUDE_PROJECT_DIR}/system/hooks/guard_git_push_signpost.sh"
# No real network, no real remote is ever contacted — the guard itself never runs the push, it only
# inspects local git state (branch/remote URL/commit log) before the (never-executed) push would run.

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/guard_git_push_signpost.sh"

if [ ! -r "$GUARD" ]; then
  echo "MISSING: $GUARD — nothing to test. FAILING CLOSED."
  exit 1
fi

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/git_push_signpost_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
ERRF="$SCRATCH/stderr.txt"
PASSED=0
FAILED=0

TARGET="$SCRATCH/target_repo"
mkdir -p "$TARGET"
git init -q "$TARGET"
# a local-only "remote" -- never contacted, its URL is only ever read as text by the guard
git -C "$TARGET" remote add origin "file://$SCRATCH/nonexistent-remote.git"

PUBLIC_TARGET="$SCRATCH/public_target"
mkdir -p "$PUBLIC_TARGET"
git init -q "$PUBLIC_TARGET"
git -C "$PUBLIC_TARGET" remote add origin "https://github.com/LifehackMethod/lifehack-brain.git"

mkcmd() {  # word fragments joined IN PYTHON -- see header note
  python3 -c '
import sys
print(" ".join(sys.argv[1:]))
' "$@"
}

mkjson() {
  T_CMD="$1" python3 -c 'import os, json; print(json.dumps({"tool_name": "Bash", "tool_input": {"command": os.environ["T_CMD"]}}))'
}

# each case gets its OWN scratch HOME + its own CLAUDE_CODE_SESSION_ID so the "fires once per
# session" signpost bump file never leaks between cases in this suite.
run_guard() {  # run_guard <cmd> <session-id>
  local cmd="$1" sid="$2"
  local home; home="$(mktemp -d "$SCRATCH/home.XXXXXX")"
  mkdir -p "$home/.claude"
  mkjson "$cmd" | HOME="$home" CLAUDE_PROJECT_DIR="$REPO" CLAUDE_CODE_SESSION_ID="$sid" bash "$GUARD" 2>"$ERRF"
}

allow() {
  local desc="$1" cmd="$2" sid="${3:-allow-$RANDOM}"
  out=$(run_guard "$cmd" "$sid"); rc=$?
  if [ "$rc" -eq 0 ]; then
    printf "  PASS  allow  %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  allow  %s  (rc=%s) OVER-BLOCK\n" "$desc" "$rc"
    printf "        stderr: %.200s\n" "$(cat "$ERRF")"
    FAILED=$((FAILED + 1))
  fi
}

deny() {  # deny <desc> <cmd> <must-contain> <session-id>
  local desc="$1" cmd="$2" must="$3" sid="$4"
  out=$(run_guard "$cmd" "$sid"); rc=$?
  problems=""
  [ "$rc" -eq 2 ] || problems="${problems}rc=$rc(want 2);"
  [ -z "$out" ] || problems="${problems}stdout-not-empty;"
  errtxt="$(cat "$ERRF")"
  case "$errtxt" in *"$must"*) ;; *) problems="${problems}missing(${must});" ;; esac
  case "$errtxt" in *WHY*) ;; *) problems="${problems}no-WHY;" ;; esac
  if [ -z "$problems" ]; then
    printf "  PASS  deny   %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  deny   %s  ->%s\n" "$desc" "$problems"
    printf "        stderr: %.300s\n" "$errtxt"
    FAILED=$((FAILED + 1))
  fi
}

echo "=== guard_git_push_signpost.sh — ALLOW cases first ==="

FETCH="$(mkcmd git -C "$TARGET" fetch)"
allow "git fetch (not push)"                 "$FETCH"
LOG="$(mkcmd git -C "$TARGET" log --oneline)"
allow "git log (not push)"                   "$LOG"
MENTION="$(mkcmd echo do not forget to git push later)"
allow "the words git push only as a MENTION, not a command" "$MENTION"

SID2="signpost-second-$RANDOM"
PUSH1="$(mkcmd git -C "$TARGET" push origin main)"
SIGNPOST_HOME="$(mktemp -d "$SCRATCH/home.signpost.XXXXXX")"
mkdir -p "$SIGNPOST_HOME/.claude"
out=$(mkjson "$PUSH1" | HOME="$SIGNPOST_HOME" CLAUDE_PROJECT_DIR="$REPO" CLAUDE_CODE_SESSION_ID="$SID2" bash "$GUARD" 2>"$ERRF"); rc1=$?
out=$(mkjson "$PUSH1" | HOME="$SIGNPOST_HOME" CLAUDE_PROJECT_DIR="$REPO" CLAUDE_CODE_SESSION_ID="$SID2" bash "$GUARD" 2>"$ERRF"); rc2=$?
if [ "$rc1" -eq 2 ] && [ "$rc2" -eq 0 ]; then
  printf "  PASS  allow  second push attempt, same session, passes silently (signpost fired once)\n"
  PASSED=$((PASSED + 1))
else
  printf "  FAIL  allow  signpost once-per-session shape (rc1=%s rc2=%s)\n" "$rc1" "$rc2"
  FAILED=$((FAILED + 1))
fi

echo
echo "=== DENY cases — every distinct protection this guard's header claims ==="

D1="$(mkcmd git -C "$TARGET" push origin main)"
deny "first push of a session, private repo"   "$D1" "PUSH" "sess-private-$RANDOM"

D2="$(mkcmd git -C "$PUBLIC_TARGET" push origin main)"
deny "first push of a session, public repo (SHIPS TO STUDENTS)" "$D2" "PUBLIC" "sess-public-$RANDOM"

# -C target pointing at a path that does not exist -- refuses rather than guessing
D3="$(mkcmd git -C /this/path/does/not/exist push origin main)"
deny "a -C target that does not resolve"       "$D3" "cannot determine" "sess-badpath-$RANDOM"

echo
echo "  $PASSED passed, $FAILED failed"
if [ "$FAILED" -eq 0 ]; then
  echo "--- RESULT: GREEN ---"
  exit 0
fi
echo "--- RESULT: RED ---"
exit 1
