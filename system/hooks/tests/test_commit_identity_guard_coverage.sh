#!/bin/bash
# test_commit_identity_guard.sh — deny-coverage suite for system/hooks/guard_commit_identity.sh
# (B6.0 — this guard had NO test anywhere before this file.)
#
# ⚠ ALLOW CASES COME FIRST, DELIBERATELY (see hook-contract.md: "every one of them tests the ALLOW
#   cases first, because a guard that blocks ordinary work gets unregistered and then guards nothing").
#
# ⚠ GIT-WORD HYGIENE: this guard's own job is to intercept `git commit`/`rebase`/`cherry-pick`, and
#   THIS SUITE ITSELF runs inside a live Claude Code session where the real guard_commit_identity.sh
#   (and guard_no_upstream_commit_signpost.sh) are registered on the session's own Bash tool calls.
#   To make sure the test AUTHOR's own shell commands never hand a live guard a literal "git commit"
#   / "git push" / "git rebase" / "git cherry-pick" token to match on, every payload command string
#   below is assembled by CONCATENATING separate word fragments **in Python** (mkcmd()), never typed
#   as one contiguous literal in this file. The words also never appear pre-joined in a raw shell
#   command this file itself runs directly (git init/config are unguarded verbs and are safe as-is).
#
# Invocation form matches the REGISTERED one: bash "${CLAUDE_PROJECT_DIR}/system/hooks/guard_commit_identity.sh"
# (matcher: Bash), with CLAUDE_PROJECT_DIR set to this worktree and HOME set to a throwaway scratch
# dir so the guard's brain-root/identity-file resolution never touches real state.
#
# Run:  bash system/hooks/tests/test_commit_identity_guard.sh   ·   exit 0 = all green.

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/guard_commit_identity.sh"

if [ ! -r "$GUARD" ]; then
  echo "MISSING: $GUARD — nothing to test. FAILING CLOSED."
  exit 1
fi

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/commit_identity_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
ERRF="$SCRATCH/stderr.txt"

PASSED=0
FAILED=0

# ── fixtures: two target repos (matching / mismatched identity), one brain root ──────────────────
BRAIN="$SCRATCH/brain"
mkdir -p "$BRAIN/config"
cat > "$BRAIN/config/ship-identity.md" <<'EOF'
# ship identity allow-list (test fixture)
allowed@example.com
EOF

mk_target() {  # mk_target <dir-name> [email]
  local d="$SCRATCH/$1"
  mkdir -p "$d/shared"
  git init -q "$d"
  # stub brain_root.py: ignores its args, always resolves to our scratch brain — this is the
  # TARGET repo's own shared/brain_root.py, resolved relative to the target, never to this repo's.
  cat > "$d/shared/brain_root.py" <<BRAINPY
import sys
print("$BRAIN")
BRAINPY
  if [ -n "${2:-}" ]; then
    git -C "$d" config user.email "$2"
  fi
  printf '%s' "$d"
}

TARGET_OK="$(mk_target target_ok allowed@example.com)"
TARGET_BAD="$(mk_target target_bad wrong@example.com)"
TARGET_NOEMAIL="$(mk_target target_noemail)"

# ── payload construction: fragments joined IN PYTHON, never as one literal in this file ──────────
mkcmd() {  # mkcmd word1 word2 ... -> prints them space-joined (join happens in python, not bash)
  python3 -c '
import sys
print(" ".join(sys.argv[1:]))
' "$@"
}

mkjson() {
  T_CMD="$1" python3 -c 'import os, json; print(json.dumps({"tool_name": "Bash", "tool_input": {"command": os.environ["T_CMD"]}}))'
}

run_guard() {
  local cmd="$1"
  mkjson "$cmd" | HOME="$SCRATCH/home" CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" 2>"$ERRF"
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

deny() {  # deny <desc> <cmd> <substring the message must contain>
  local desc="$1" cmd="$2" must="$3"
  out=$(run_guard "$cmd"); rc=$?
  problems=""
  [ "$rc" -eq 2 ] || problems="${problems}rc=$rc(want 2);"
  [ -z "$out" ] || problems="${problems}stdout-not-empty;"
  errtxt="$(cat "$ERRF")"
  [ -n "$errtxt" ] || problems="${problems}stderr-empty(guard-cannot-speak);"
  case "$errtxt" in
    *"$must"*) ;;
    *) problems="${problems}message-missing-expected-substring(${must});" ;;
  esac
  case "$errtxt" in
    *WHY*) ;;
    *) problems="${problems}no-WHY;" ;;
  esac
  case "$errtxt" in
    *REDIRECT*) ;;
    *) problems="${problems}no-REDIRECT;" ;;
  esac
  if [ -z "$problems" ]; then
    printf "  PASS  deny   %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  deny   %s  ->%s\n" "$desc" "$problems"
    printf "        stderr: %.300s\n" "$errtxt"
    FAILED=$((FAILED + 1))
  fi
}

echo "=== guard_commit_identity.sh — ALLOW cases first ==="

allow "unrelated command"                    "$(mkcmd ls -la)"
allow "git status (not a write verb)"        "$(mkcmd git status)"
allow "the words git commit only as a MENTION, not a command" \
                                              "$(mkcmd echo run git commit later)"
CMT="$(mkcmd git -C "$TARGET_OK" commit -m ok)"
allow "matching identity commit"             "$CMT"

echo
echo "=== DENY cases — every distinct protection this guard's header claims ==="

D1="$(mkcmd git -C "$TARGET_BAD" commit -m x)"
deny "commit under mismatched identity"      "$D1" "not in the allow-list"

D2="$(mkcmd git -C "$TARGET_BAD" commit --amend -m x)"
deny "commit --amend under mismatched identity" "$D2" "not in the allow-list"

D3="$(mkcmd git -C "$TARGET_BAD" rebase -i HEAD~1)"
deny "rebase under mismatched identity"      "$D3" "not in the allow-list"

D4="$(mkcmd git -C "$TARGET_BAD" cherry-pick abc123)"
deny "cherry-pick under mismatched identity" "$D4" "not in the allow-list"

D5="$(mkcmd git -C "$TARGET_NOEMAIL" commit -m x)"
deny "no user.email configured at all"       "$D5" "no git config user.email set"

rm -f "$BRAIN/config/ship-identity.md"
D6="$(mkcmd git -C "$TARGET_BAD" commit -m x)"
deny "identity file itself missing"          "$D6" "does not exist"

echo
echo "  $PASSED passed, $FAILED failed"
if [ "$FAILED" -eq 0 ]; then
  echo "--- RESULT: GREEN ---"
  exit 0
fi
echo "--- RESULT: RED ---"
exit 1
