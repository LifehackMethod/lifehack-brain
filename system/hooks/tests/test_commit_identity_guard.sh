#!/bin/bash
# test_commit_identity_guard.sh — guard_commit_identity.sh's brain_root.py resolution.
#
# ⭐ THE BUG THIS SUITE EXISTS FOR (2026-09-15, #O5). The guard resolved
# `shared/brain_root.py` from the TARGET repo being committed to
# (`$_target/shared/brain_root.py`) and denied outright when that file was not there. That is
# every repo which is not a Harness clone — e.g. a private personal repo with no `shared/`
# folder at all. Because this guard fails CLOSED by design, EVERY `git commit` from a session
# working in such a repo was blocked, identity correct or not. Same class of bug as
# guard_findings_write.sh's winpath_fold.py lookup (PR #165, fixed 2026-09-09): a resolver
# path derived from the TARGET/cwd instead of from this script's own location/plugin root.
#
# THE FIX: prefer the target repo's own copy (the common case — committing inside the Harness
# clone itself), and when the target lacks one, fall back to this script's own plugin install
# (`$CLAUDE_PLUGIN_ROOT/shared/brain_root.py`, or this script's own directory when that env var
# is unset) — so a non-Harness repo is still CHECKED, never silently skipped, and a real
# identity violation there is still denied.
#
# Nothing real is touched: HOME, CLAUDE_PLUGIN_ROOT and LIFEHACK_ROOT all point into a throwaway
# sandbox, so the real AI Brain / ship-identity.md / git config on this machine are never read.
#
# Deny = exit 2. Allow = exit 0.
# Run: bash system/hooks/tests/test_commit_identity_guard.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$HOOKS/../.." && pwd)"
GUARD="$HOOKS/guard_commit_identity.sh"
[ -f "$GUARD" ] || { echo "CANNOT RUN: no hook at $GUARD"; exit 1; }

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/commitid.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT

ALLOWED="allowed@example.com"
WRONG="wrong@example.com"

# ── Fixtures ─────────────────────────────────────────────────────────────────────────────────
# The Brain: a real AI Brain has to look like this only as far as this guard cares —
# config/ship-identity.md with at least one "@" line.
BRAIN="$SANDBOX/brain"
mkdir -p "$BRAIN/config"
printf '# scratch allow-list\n%s\n' "$ALLOWED" > "$BRAIN/config/ship-identity.md"

git_repo() {  # git_repo <path> <email>
  mkdir -p "$1" && (cd "$1" && git init -q && git config user.email "$2" && git config user.name "Test")
}

# A "harness-style" repo: carries its OWN shared/brain_root.py (+ the system/tools/utf8_stdio.py
# sibling it imports as __main__) at its root, same as a real Harness clone.
HARNESS_REPO="$SANDBOX/harness-repo"
git_repo "$HARNESS_REPO" "$ALLOWED"
mkdir -p "$HARNESS_REPO/shared" "$HARNESS_REPO/system/tools"
cp "$REPO_ROOT/shared/brain_root.py" "$HARNESS_REPO/shared/brain_root.py"
cp "$REPO_ROOT/system/tools/utf8_stdio.py" "$HARNESS_REPO/system/tools/utf8_stdio.py"

HARNESS_REPO_BADID="$SANDBOX/harness-repo-badid"
git_repo "$HARNESS_REPO_BADID" "$WRONG"
mkdir -p "$HARNESS_REPO_BADID/shared" "$HARNESS_REPO_BADID/system/tools"
cp "$REPO_ROOT/shared/brain_root.py" "$HARNESS_REPO_BADID/shared/brain_root.py"
cp "$REPO_ROOT/system/tools/utf8_stdio.py" "$HARNESS_REPO_BADID/system/tools/utf8_stdio.py"

# A "non-harness" repo — the bug's own reproduction case: no shared/ folder at all, e.g. a
# private personal repo like ~/.claude/skills/ClaudeOps.
PLAIN_REPO="$SANDBOX/plain-repo"
git_repo "$PLAIN_REPO" "$ALLOWED"

PLAIN_REPO_BADID="$SANDBOX/plain-repo-badid"
git_repo "$PLAIN_REPO_BADID" "$WRONG"

PLAIN_REPO_NOEMAIL="$SANDBOX/plain-repo-noemail"
mkdir -p "$PLAIN_REPO_NOEMAIL" && (cd "$PLAIN_REPO_NOEMAIL" && git init -q)

# A fake "plugin install" with NO shared/ at all — for the truly-unresolvable case: the target
# lacks brain_root.py AND the plugin-root fallback does too.
NO_BRAIN_PLUGIN="$SANDBOX/no-brain-plugin"
mkdir -p "$NO_BRAIN_PLUGIN/system/hooks"
cp "$GUARD" "$NO_BRAIN_PLUGIN/system/hooks/guard_commit_identity.sh"

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

# run <label> <expected-rc> <command> <plugin-root>
# LIFEHACK_ROOT always points at the scratch Brain — CLAUDE_PLUGIN_ROOT is the variable under
# test, since it is what the fix's fallback route reads (falling back further to this script's
# own directory only when unset, which the REAL registered form never leaves unset).
run() {
  local label="$1" exp="$2" cmd="$3" plugin_root="$4" got out
  out=$(python3 -c "
import json,sys
print(json.dumps({'tool_name':'Bash','tool_input':{'command':sys.argv[1]}}))" "$cmd" 2>/dev/null \
    | env -i HOME="$SANDBOX" PATH="$PATH" LIFEHACK_ROOT="$BRAIN" CLAUDE_PLUGIN_ROOT="$plugin_root" \
        bash "$plugin_root/system/hooks/guard_commit_identity.sh" 2>&1 >/dev/null)
  got=$?
  if [ "$got" = "$exp" ]; then ok; else bad "$label" "expected exit $exp, got $got — $out"; fi
}

echo "── not ours: no write verb, never even reaches identity resolution ──────"
run "git status"     0 "git -C $PLAIN_REPO status"          "$REPO_ROOT"
run "git log"        0 "git -C $PLAIN_REPO log -1"          "$REPO_ROOT"
run "unrelated cmd"  0 "ls -la"                              "$REPO_ROOT"

echo "── ⭐ THE BUG: a non-Harness repo (no shared/brain_root.py) must still be CHECKED, and correct identity must be ALLOWED — not skipped, not denied ──"
run "plain repo, correct identity"   0 "git -C $PLAIN_REPO commit -m x"   "$REPO_ROOT"
run "plain repo, --amend, correct"   0 "git -C $PLAIN_REPO commit --amend -m x" "$REPO_ROOT"

echo "── a real identity violation must still be denied — in EITHER repo shape ──"
run "harness-style repo, wrong identity"  2 "git -C $HARNESS_REPO_BADID commit -m x"  "$REPO_ROOT"
run "plain repo, wrong identity"          2 "git -C $PLAIN_REPO_BADID commit -m x"    "$REPO_ROOT"
run "plain repo, no user.email set"       2 "git -C $PLAIN_REPO_NOEMAIL commit -m x"  "$REPO_ROOT"

echo "── harness-style repo, correct identity: unchanged prior behavior ───────"
run "harness-style repo, correct identity" 0 "git -C $HARNESS_REPO commit -m x"       "$REPO_ROOT"

echo "── truly unresolvable (target AND plugin fallback both lack brain_root.py): fail CLOSED, not silently skipped ──"
run "no brain_root.py anywhere"  2 "git -C $PLAIN_REPO commit -m x"  "$NO_BRAIN_PLUGIN"

echo "── the CLOSED-not-skipped case names the FAIL_POSTURE, so it teaches rather than just walls ──"
MSG=$(python3 -c "
import json; print(json.dumps({'tool_input':{'command':'git -C $PLAIN_REPO commit -m x'}}))" \
  | env -i HOME="$SANDBOX" PATH="$PATH" LIFEHACK_ROOT="$BRAIN" CLAUDE_PLUGIN_ROOT="$NO_BRAIN_PLUGIN" \
      bash "$NO_BRAIN_PLUGIN/system/hooks/guard_commit_identity.sh" 2>&1 >/dev/null)
printf '%s' "$MSG" | grep -q "FAIL_POSTURE: closed" && ok || bad "unresolvable names FAIL_POSTURE" "$MSG"
printf '%s' "$MSG" | grep -q "$PLAIN_REPO" && ok || bad "unresolvable names the target checked" "$MSG"
printf '%s' "$MSG" | grep -q "$NO_BRAIN_PLUGIN" && ok || bad "unresolvable names the plugin fallback checked" "$MSG"

echo
if [ "$fail" = 0 ]; then echo "RESULT: $pass passed, 0 failed."; echo "COMMIT IDENTITY GUARD GREEN"; exit 0
else echo "RESULT: $pass passed, $fail failed."; exit 1; fi
