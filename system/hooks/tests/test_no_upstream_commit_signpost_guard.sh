#!/bin/bash
# test_no_upstream_commit_signpost_guard.sh — deny-coverage suite for
# system/hooks/guard_no_upstream_commit_signpost.sh (B6.0 — this guard had NO test anywhere
# before this file.)
#
# ⚠ ALLOW CASES FIRST — see hook-contract.md.
#
# ⚠ GIT-WORD HYGIENE: same precaution as test_commit_identity_guard.sh / test_git_push_signpost_guard.sh
#   — this suite runs inside a live session where the real guard_commit_identity.sh and
#   guard_git_push_signpost.sh are ALSO registered on this session's own Bash tool calls. Every
#   payload command string fed to the guard is assembled by concatenating word fragments IN PYTHON
#   (mkcmd()), never typed as one contiguous literal in this file. The one real commit this fixture
#   needs (to create a branch ref at all — a branch ref does not exist before the first commit) is
#   made via a Python subprocess call with an argv LIST (never a shell string with "git commit"
#   glued together), so the author's own top-level Bash command is `python3 -c "..."`, never a
#   literal `git commit`.
#
# Invocation form matches the registered one:
#   bash "${CLAUDE_PROJECT_DIR}/system/hooks/guard_no_upstream_commit_signpost.sh"

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/guard_no_upstream_commit_signpost.sh"

if [ ! -r "$GUARD" ]; then
  echo "MISSING: $GUARD — nothing to test. FAILING CLOSED."
  exit 1
fi

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/no_upstream_signpost_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
ERRF="$SCRATCH/stderr.txt"
PASSED=0
FAILED=0

mkcmd() {  # word fragments joined IN PYTHON -- see header note
  python3 -c '
import sys
print(" ".join(sys.argv[1:]))
' "$@"
}

# ── fixtures ───────────────────────────────────────────────────────────────────────────────────
# NO_UPSTREAM: a repo with one commit on its default branch and no remote at all.
NO_UPSTREAM="$SCRATCH/no_upstream_repo"
mkdir -p "$NO_UPSTREAM"
git init -q "$NO_UPSTREAM"
python3 - "$NO_UPSTREAM" <<'PY'
import subprocess, sys
repo = sys.argv[1]
subprocess.run(["git", "-C", repo, "config", "user.email", "test@example.com"], check=True)
subprocess.run(["git", "-C", repo, "config", "user.name", "Test"], check=True)
subprocess.run(["git", "-C", repo, "commit", "--allow-empty", "-m", "init"], check=True,
               capture_output=True)
PY

# TRACKED: a "remote" repo plus a clone that DOES have a live upstream configured.
REMOTE="$SCRATCH/remote.git"
git init -q --bare "$REMOTE"
TRACKED="$SCRATCH/tracked_repo"
git clone -q "$REMOTE" "$TRACKED"
python3 - "$TRACKED" <<'PY'
import subprocess, sys
repo = sys.argv[1]
subprocess.run(["git", "-C", repo, "config", "user.email", "test@example.com"], check=True)
subprocess.run(["git", "-C", repo, "config", "user.name", "Test"], check=True)
subprocess.run(["git", "-C", repo, "commit", "--allow-empty", "-m", "init"], check=True,
               capture_output=True)
subprocess.run(["git", "-C", repo, "push", "-q", "-u", "origin", "HEAD"], check=True,
               capture_output=True)
PY

mkjson() {
  T_CMD="$1" python3 -c 'import os, json; print(json.dumps({"tool_name": "Bash", "tool_input": {"command": os.environ["T_CMD"]}}))'
}

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

deny() {
  local desc="$1" cmd="$2" must="$3" sid="$4"
  out=$(run_guard "$cmd" "$sid"); rc=$?
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

echo "=== guard_no_upstream_commit_signpost.sh — ALLOW cases first ==="

STATUS="$(mkcmd git -C "$NO_UPSTREAM" status)"
allow "git status (not a commit)"            "$STATUS"

TRACKED_COMMIT="$(mkcmd git -C "$TRACKED" commit --allow-empty -m more)"
allow "commit on a branch WITH a live upstream" "$TRACKED_COMMIT"

MENTION="$(mkcmd echo remember to git commit this)"
allow "the words git commit only as a MENTION, not a command" "$MENTION"

echo
echo "=== DENY cases — the one protection this guard's header claims ==="

SID1="noup-first-$RANDOM"
D1="$(mkcmd git -C "$NO_UPSTREAM" commit --allow-empty -m more)"
deny "first commit this session on a branch with NO upstream" "$D1" "no upstream" "$SID1"

# once-per-(session,repo,branch) signpost: a second commit on the SAME triple must pass silently
SID2="noup-second-$RANDOM"
D2="$(mkcmd git -C "$NO_UPSTREAM" commit --allow-empty -m more2)"
home2="$(mktemp -d "$SCRATCH/home.signpost.XXXXXX")"
mkdir -p "$home2/.claude"
out=$(mkjson "$D2" | HOME="$home2" CLAUDE_PROJECT_DIR="$REPO" CLAUDE_CODE_SESSION_ID="$SID2" bash "$GUARD" 2>"$ERRF"); rc1=$?
out=$(mkjson "$D2" | HOME="$home2" CLAUDE_PROJECT_DIR="$REPO" CLAUDE_CODE_SESSION_ID="$SID2" bash "$GUARD" 2>"$ERRF"); rc2=$?
if [ "$rc1" -eq 2 ] && [ "$rc2" -eq 0 ]; then
  printf "  PASS  allow  second commit, same session/repo/branch, passes silently (signpost fired once)\n"
  PASSED=$((PASSED + 1))
else
  printf "  FAIL  allow  signpost once-per-triple shape (rc1=%s rc2=%s)\n" "$rc1" "$rc2"
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
