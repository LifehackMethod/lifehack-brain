#!/bin/bash
# Regression coverage for `system/hooks/guard_no_upstream_commit_signpost.sh`'s
# chained-branch resolution (first coverage this guard has ever had -- none existed
# before this file; git history shows it shipped in f7d146a with no test).
#
# THE BUG (shipped 0.3.21, reported 2026-09-16 by window 0-3-21-5c): the guard fires
# PreToolUse, before the inspected command runs. It already takes the REPO from the
# command text (an explicit -C, or a preceding `cd` in the same &&/; chain) but took
# the BRANCH from live `git rev-parse --abbrev-ref HEAD` + `for-each-ref`. In one
# Bash call `git -C <repo> checkout -b <new> && git -C <repo> commit ...`, HEAD is
# still the OLD branch at fire time (the checkout has not executed yet) -- so a
# brand-new, definitely-upstream-less branch never trips the guard. Hand-feeding the
# identical payload AFTER the branch already exists denies correctly, which is why a
# static hand-fed test would never have caught this -- only the CHAINED form does.
#
# THE FIX: parse a preceding `checkout -b/-B <name>` or `switch -c/-C <name>` in the
# same &&/; chain (dropped across |/||, exactly like the existing cwd/`cd` tracking)
# and let it override the branch used at commit time, scoped to the same resolved
# repo dir. A branch introduced this way does not exist as a ref yet at fire time, so
# the for-each-ref tracking probe is skipped for it -- absent an explicit --track,
# git's own `checkout -b`/`switch -c` never sets an upstream, so it is treated as
# upstream-less directly.
#
# This file exercises exactly the shapes the fix promises:
#   1. `-C` form, chained `checkout -b` + `commit` -- fires (RED on the unfixed guard).
#   2. same with `switch -c`, `checkout -B`, and a `;` separator.
#   3. the `cd <repo> && git checkout -b X && git commit` form (no -C anywhere).
#   4. controls: a plain commit on an already-tracked branch is silent; a chained
#      checkout of an EXISTING tracked branch (already checked out) is silent; a
#      `checkout -b` appearing only inside a quoted string (an echo) is not treated
#      as a real branch switch.
#   5. the once-per-(session,repo,branch) marker still holds for the chained case.
#
# Invokes the guard directly (its only registered form takes no arguments beyond
# stdin), against real throwaway git repos (a bare "origin" + a working clone with
# `main` pushed/tracked), with a scratch $HOME so the real ~/.claude markers are
# never touched.

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)" || exit 1
GUARD_REL="system/hooks/guard_no_upstream_commit_signpost.sh"
GUARD_PATH="$REPO_ROOT/$GUARD_REL"

pass=0; fail=0
TMP_DIRS=()
cleanup() { for d in "${TMP_DIRS[@]}"; do rm -rf "$d" 2>/dev/null; done; }
trap cleanup EXIT

new_home() {
  local d
  d=$(mktemp -d "${TMPDIR:-/tmp}/no-upstream-test.XXXXXX") || exit 1
  mkdir -p "$d/.claude"
  TMP_DIRS+=("$d")
  printf '%s' "$d"
}

# new_repo: a bare "origin" + a working clone with `main` committed, pushed and
# tracked (upstream = origin/main). Prints the working clone's absolute path.
new_repo() {
  local base bare work
  base=$(mktemp -d "${TMPDIR:-/tmp}/no-upstream-test.XXXXXX") || exit 1
  TMP_DIRS+=("$base")
  bare="$base/origin.git"
  work="$base/work"
  git init --quiet --bare "$bare" >/dev/null 2>&1
  git init --quiet "$work" >/dev/null 2>&1
  (
    cd "$work" || exit 1
    git checkout -b main --quiet >/dev/null 2>&1
    git config user.email test@example.com
    git config user.name "Test"
    git remote add origin "$bare"
    echo hello > f.txt
    git add f.txt
    git commit --quiet -m init >/dev/null 2>&1
    git push --quiet -u origin main >/dev/null 2>&1
  ) >/dev/null 2>&1
  printf '%s' "$work"
}

payload() { # payload <command-string>
  python3 -c 'import json, sys; print(json.dumps({"tool_input": {"command": sys.argv[1]}}))' "$1"
}

invoke() { # invoke <payload-json> <home> <session>
  printf '%s' "$1" | HOME="$2" CLAUDE_CODE_SESSION_ID="$3" bash "$GUARD_PATH"
}

want_deny() { # want_deny <exit_code> <label>
  if [ "$1" -eq 2 ]; then pass=$((pass+1)); printf '   ok   %s (denied)\n' "$2"
  else fail=$((fail+1)); printf '  FAIL  %s (expected deny/exit 2, got %s)\n' "$2" "$1"; fi
}
want_allow() { # want_allow <exit_code> <label>
  if [ "$1" -eq 0 ]; then pass=$((pass+1)); printf '   ok   %s (allowed)\n' "$2"
  else fail=$((fail+1)); printf '  FAIL  %s (expected allow/exit 0, got %s)\n' "$2" "$1"; fi
}

echo "── 1. chained 'checkout -b' + commit, -C form ──────────────────────────────"
REPO1=$(new_repo)
HOME1=$(new_home)
PAY1=$(payload "git -C $REPO1 checkout -b newb && git -C $REPO1 commit -m x")
ERR1=$(mktemp "${TMPDIR:-/tmp}/no-upstream-test.XXXXXX")
invoke "$PAY1" "$HOME1" "sess-1" >/dev/null 2>"$ERR1"; c=$?
want_deny "$c" "chained checkout -b + commit (-C form) fires"
if grep -q "newb" "$ERR1"; then pass=$((pass+1)); printf '   ok   deny text names the new branch (newb)\n'
else fail=$((fail+1)); printf '  FAIL  deny text does not name newb: %s\n' "$(cat "$ERR1")"; fi
rm -f "$ERR1"

echo
echo "── 2. switch -c / checkout -B / ';' separator ──────────────────────────────"
REPO2=$(new_repo)
HOME2=$(new_home)
PAY2A=$(payload "git -C $REPO2 switch -c newb2 && git -C $REPO2 commit -m x")
invoke "$PAY2A" "$HOME2" "sess-2a" >/dev/null 2>&1; c=$?
want_deny "$c" "chained 'switch -c' + commit fires"

PAY2B=$(payload "git -C $REPO2 checkout -B newb3 && git -C $REPO2 commit -m x")
invoke "$PAY2B" "$HOME2" "sess-2b" >/dev/null 2>&1; c=$?
want_deny "$c" "chained 'checkout -B' + commit fires"

PAY2C=$(payload "git -C $REPO2 checkout -b newb4 ; git -C $REPO2 commit -m x")
invoke "$PAY2C" "$HOME2" "sess-2c" >/dev/null 2>&1; c=$?
want_deny "$c" "chained checkout -b + commit joined by ';' fires"

echo
echo "── 3. 'cd <repo> && checkout -b && commit' (no -C anywhere) ────────────────"
REPO3=$(new_repo)
HOME3=$(new_home)
PAY3=$(payload "cd $REPO3 && git checkout -b newb5 && git commit")
invoke "$PAY3" "$HOME3" "sess-3" >/dev/null 2>&1; c=$?
want_deny "$c" "cd + checkout -b + bare commit fires"

echo
echo "── 4. controls ───────────────────────────────────────────────────────────"
REPO4=$(new_repo)
HOME4=$(new_home)

PAY4A=$(payload "git -C $REPO4 commit -m x")
invoke "$PAY4A" "$HOME4" "sess-4a" >/dev/null 2>&1; c=$?
want_allow "$c" "plain commit on a branch that HAS an upstream (main) is silent"

PAY4B=$(payload "git -C $REPO4 checkout main && git -C $REPO4 commit -m x")
invoke "$PAY4B" "$HOME4" "sess-4b" >/dev/null 2>&1; c=$?
want_allow "$c" "chained checkout of an EXISTING tracked branch uses its tracking, silent"

PAY4C=$(payload "echo \"note: git checkout -b sneaky\" && git -C $REPO4 commit -m x")
invoke "$PAY4C" "$HOME4" "sess-4c" >/dev/null 2>&1; c=$?
want_allow "$c" "'checkout -b' inside a quoted echo string is not treated as a branch switch"

echo
echo "── 5. once-per-(session,repo,branch) marker still holds ────────────────────"
PAY5=$(payload "git -C $REPO1 checkout -b newb && git -C $REPO1 commit -m x")
invoke "$PAY5" "$HOME1" "sess-1" >/dev/null 2>&1; c=$?
want_allow "$c" "identical chained payload, same session -- repeat is silent (marker held)"

PAY5B=$(payload "git -C $REPO1 checkout -b newb6 && git -C $REPO1 commit -m x")
invoke "$PAY5B" "$HOME1" "sess-1" >/dev/null 2>&1; c=$?
want_deny "$c" "a DIFFERENT chained branch, same session -- gets its own first sighting"

echo
printf 'RESULT: %d passed, %d failed.\n' "$pass" "$fail"
if [ "$fail" -eq 0 ]; then echo "NO-UPSTREAM SIGNPOST GUARD GREEN"; exit 0; fi
echo "NO-UPSTREAM SIGNPOST GUARD RED"; exit 1
