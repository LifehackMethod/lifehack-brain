#!/bin/bash
# Regression coverage for `system/hooks/guard_git_push_signpost.sh`'s signpost marker.
#
# THE BUG (fixed 2026-09-15): this guard is registered TWICE for the same PreToolUse
# Bash event -- hooks/hooks.json loads it via ${CLAUDE_PLUGIN_ROOT} and
# .claude/settings.json loads the identical script via ${CLAUDE_PROJECT_DIR} -- so
# both copies run in PARALLEL on every push attempt. The marker used to be keyed on
# session id ALONE and DELETED itself on the allow branch: one copy created it and
# denied, the other found it, deleted it, and allowed -- so every attempt denied,
# forever (see this file's git history for the empirical reproduction).
#
# THE FIX: key the marker on session id + a hash of the normalized command + the
# resolved target dir, created via `mkdir` (atomic on POSIX filesystems) and NEVER
# deleted. This file exercises exactly the shapes the fix promises:
#   A. single registration      -- first sighting denies, every repeat allows
#   B. a DIFFERENT push command in the same session -- gets its OWN first-sight deny
#   C. double registration (the real bug) -- two copies invoked in TRUE parallel for
#      the identical payload, three rounds: round 1 must show exactly one deny of
#      the two; rounds 2-3 must show zero denies.
#   D. unrelated behavior (unresolvable -C target, a non-push git verb, a mere
#      mention in a commit message) is untouched by this fix.
#
# Invokes the guard through the REGISTERED invocation form (the literal command
# templates from hooks/hooks.json and .claude/settings.json), with a scratch $HOME
# so the real ~/.claude markers are never touched.

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)" || exit 1
GUARD_REL="system/hooks/guard_git_push_signpost.sh"

pass=0; fail=0
TMP_HOMES=()
cleanup() { for d in "${TMP_HOMES[@]}"; do rm -rf "$d"; done; }
trap cleanup EXIT

new_home() {
  local d
  d=$(mktemp -d "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX") || exit 1
  mkdir -p "$d/.claude"
  printf '%s' "$d"
}

payload() { # payload <command-string>
  python3 -c 'import json, sys; print(json.dumps({"tool_input": {"command": sys.argv[1]}}))' "$1"
}

# invoke_plugin/invoke_project mirror the two REGISTERED command templates exactly.
invoke_plugin() { # invoke_plugin <payload-json> <home> <session>
  printf '%s' "$1" | CLAUDE_PLUGIN_ROOT="$REPO_ROOT" HOME="$2" CLAUDE_CODE_SESSION_ID="$3" \
    bash -c 'bash "${CLAUDE_PLUGIN_ROOT}/'"$GUARD_REL"'"'
}
invoke_project() { # invoke_project <payload-json> <home> <session>
  printf '%s' "$1" | CLAUDE_PROJECT_DIR="$REPO_ROOT" HOME="$2" CLAUDE_CODE_SESSION_ID="$3" \
    bash -c 'bash "${CLAUDE_PROJECT_DIR}/'"$GUARD_REL"'"'
}

want_deny() { # want_deny <exit_code> <label>
  if [ "$1" -eq 2 ]; then pass=$((pass+1)); printf '   ok   %s (denied)\n' "$2"
  else fail=$((fail+1)); printf '  FAIL  %s (expected deny/exit 2, got %s)\n' "$2" "$1"; fi
}
want_allow() { # want_allow <exit_code> <label>
  if [ "$1" -eq 0 ]; then pass=$((pass+1)); printf '   ok   %s (allowed)\n' "$2"
  else fail=$((fail+1)); printf '  FAIL  %s (expected allow/exit 0, got %s)\n' "$2" "$1"; fi
}
want_count() { # want_count <expected> <actual> <label>
  if [ "$1" -eq "$2" ]; then pass=$((pass+1)); printf '   ok   %s\n' "$3"
  else fail=$((fail+1)); printf '  FAIL  %s (expected %s, got %s)\n' "$3" "$1" "$2"; fi
}

echo "── A. single registration: first sighting denies, repeats allow ──────────"
HOME_A=$(new_home); TMP_HOMES+=("$HOME_A")
PAY_A=$(payload "git push origin main")
ERR_A1=$(mktemp "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX")
invoke_project "$PAY_A" "$HOME_A" "sess-A" >/dev/null 2>"$ERR_A1"; c=$?
want_deny "$c" "first sighting"
if [ -s "$ERR_A1" ] && grep -q "PUSH" "$ERR_A1"; then
  pass=$((pass+1)); printf '   ok   deny text carries the PUSH signpost\n'
else
  fail=$((fail+1)); printf '  FAIL  deny text missing the PUSH signpost\n'
fi
rm -f "$ERR_A1"
invoke_project "$PAY_A" "$HOME_A" "sess-A" >/dev/null 2>&1; c=$?
want_allow "$c" "repeat #1 of the identical push"
invoke_project "$PAY_A" "$HOME_A" "sess-A" >/dev/null 2>&1; c=$?
want_allow "$c" "repeat #2 -- marker was never deleted"

echo
echo "── B. a DIFFERENT push command in the same session gets its own signpost ──"
HOME_B=$(new_home); TMP_HOMES+=("$HOME_B")
PAY_B1=$(payload "git push origin main")
PAY_B2=$(payload "git push origin V2")
invoke_project "$PAY_B1" "$HOME_B" "sess-B" >/dev/null 2>&1; c=$?
want_deny "$c" "push #1, first sighting"
invoke_project "$PAY_B1" "$HOME_B" "sess-B" >/dev/null 2>&1; c=$?
want_allow "$c" "push #1, repeat"
invoke_project "$PAY_B2" "$HOME_B" "sess-B" >/dev/null 2>&1; c=$?
want_deny "$c" "push #2 (different command), its own first sighting"
invoke_project "$PAY_B2" "$HOME_B" "sess-B" >/dev/null 2>&1; c=$?
want_allow "$c" "push #2, repeat"

echo
echo "── C. double registration (the actual historical bug) -- TRUE parallel ──"
HOME_C=$(new_home); TMP_HOMES+=("$HOME_C")
PAY_C=$(payload "git push origin main")
for round in 1 2 3; do
  invoke_plugin "$PAY_C" "$HOME_C" "sess-C" >/dev/null 2>&1 &
  pid1=$!
  invoke_project "$PAY_C" "$HOME_C" "sess-C" >/dev/null 2>&1 &
  pid2=$!
  wait "$pid1"; code1=$?
  wait "$pid2"; code2=$?
  denycount=0
  [ "$code1" -eq 2 ] && denycount=$((denycount+1))
  [ "$code2" -eq 2 ] && denycount=$((denycount+1))
  if [ "$round" -eq 1 ]; then
    want_count 1 "$denycount" "round 1: exactly one of the two parallel copies denies"
  else
    want_count 0 "$denycount" "round $round: identical repeat -- neither parallel copy denies"
  fi
done

echo
echo "── D. unrelated behavior is untouched by this fix ─────────────────────────"
HOME_D=$(new_home); TMP_HOMES+=("$HOME_D")
PAY_UNRES=$(payload "git -C /this/path/does/not/exist push origin main")
ERR_D1=$(mktemp "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX")
invoke_project "$PAY_UNRES" "$HOME_D" "sess-D" >/dev/null 2>"$ERR_D1"; c=$?
if [ "$c" -eq 2 ] && grep -q "cannot determine the target repo" "$ERR_D1"; then
  pass=$((pass+1)); printf '   ok   unresolvable -C target still refuses, un-signposted, unchanged\n'
else
  fail=$((fail+1)); printf '  FAIL  unresolvable -C target behavior changed (exit=%s)\n' "$c"
fi
rm -f "$ERR_D1"

PAY_STATUS=$(payload "git status")
invoke_project "$PAY_STATUS" "$HOME_D" "sess-D" >/dev/null 2>&1; c=$?
want_allow "$c" "a genuinely different git verb (status) is silently allowed"

PAY_MENTION=$(payload "git commit -m 'about to git push later'")
invoke_project "$PAY_MENTION" "$HOME_D" "sess-D" >/dev/null 2>&1; c=$?
want_allow "$c" "a mere mention of 'git push' inside a quoted commit message is not tripped"

echo
echo "── E. refspec-summary fix (A1.9): summarises the NAMED ref, never the checkout ──"
# A1.9 bug (observed live 2026-09-15): `git -C <repo> push origin <named-branch>`,
# run while the checkout was on a DIFFERENT branch, signposted the CHECKOUT's
# commits/files instead of the named branch's. This section builds a real scratch
# git fixture (bare remote + local clone) and drives the guard through it via
# `-C`, covering: the exact bug shape, src:dst, HEAD, no refspec, --tags, and an
# unresolvable refspec.
FIX_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/push-signpost-fixture.XXXXXX") || exit 1
TMP_HOMES+=("$FIX_ROOT")
FIX_BARE="$FIX_ROOT/remote.git"
FIX_LOCAL="$FIX_ROOT/local"
git init --bare -q "$FIX_BARE"
git init -q "$FIX_LOCAL"
export GIT_AUTHOR_NAME="A19 Test" GIT_AUTHOR_EMAIL="a19@example.invalid"
export GIT_COMMITTER_NAME="A19 Test" GIT_COMMITTER_EMAIL="a19@example.invalid"
git -C "$FIX_LOCAL" checkout -q -b main
git -C "$FIX_LOCAL" remote add origin "$FIX_BARE"
printf 'root\n' > "$FIX_LOCAL/root.txt"; git -C "$FIX_LOCAL" add root.txt; git -C "$FIX_LOCAL" commit -q -m "root commit"
git -C "$FIX_LOCAL" push -q -u origin main
git -C "$FIX_LOCAL" symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main

git -C "$FIX_LOCAL" checkout -q -b branchA main
printf 'a\n' > "$FIX_LOCAL/a_only.txt"; git -C "$FIX_LOCAL" add a_only.txt; git -C "$FIX_LOCAL" commit -q -m "branchA-only commit"
git -C "$FIX_LOCAL" push -q -u origin branchA

git -C "$FIX_LOCAL" checkout -q -b branchB main
git -C "$FIX_LOCAL" push -q -u origin branchB
printf 'b\n' > "$FIX_LOCAL/b_new_file.txt"; git -C "$FIX_LOCAL" add b_new_file.txt; git -C "$FIX_LOCAL" commit -q -m "branchB ahead-by-one commit"

git -C "$FIX_LOCAL" checkout -q -b newbranch main
printf 'n\n' > "$FIX_LOCAL/new_file.txt"; git -C "$FIX_LOCAL" add new_file.txt; git -C "$FIX_LOCAL" commit -q -m "newbranch commit"

git -C "$FIX_LOCAL" tag v1.0 main

# leave the checkout on branchA -- this IS the reported bug shape: checked out on
# one branch while the push command NAMES a different one.
git -C "$FIX_LOCAL" checkout -q branchA
unset GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL

HOME_E=$(new_home); TMP_HOMES+=("$HOME_E")

# E1 -- THE EXACT REPORTED BUG: checked out on branchA, push NAMES branchB.
PAY_E1=$(payload "git -C $FIX_LOCAL push origin branchB")
ERR_E1=$(mktemp "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX")
invoke_project "$PAY_E1" "$HOME_E" "sess-E1" >/dev/null 2>"$ERR_E1"; c=$?
want_deny "$c" "E1: push names branchB while checked out on branchA"
if grep -q "branchB -> origin/branchB" "$ERR_E1" && grep -q "b_new_file.txt" "$ERR_E1" && ! grep -q "a_only" "$ERR_E1"; then
  pass=$((pass+1)); printf '   ok   E1: manifest names the PUSHED branch (branchB), not the checkout (branchA)\n'
else
  fail=$((fail+1)); printf '  FAIL  E1: manifest did not correctly summarise the named refspec\n'; cat "$ERR_E1"
fi
rm -f "$ERR_E1"

# E2 -- src:dst refspec (local newbranch -> remote name renamed)
PAY_E2=$(payload "git -C $FIX_LOCAL push origin newbranch:renamed")
ERR_E2=$(mktemp "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX")
invoke_project "$PAY_E2" "$HOME_E" "sess-E2" >/dev/null 2>"$ERR_E2"; c=$?
want_deny "$c" "E2: src:dst refspec"
if grep -q "newbranch -> origin/renamed" "$ERR_E2" && grep -q "NEW BRANCH" "$ERR_E2" && grep -q "new_file.txt" "$ERR_E2"; then
  pass=$((pass+1)); printf '   ok   E2: src:dst resolved to the correct dst name, flagged as a new branch\n'
else
  fail=$((fail+1)); printf '  FAIL  E2: src:dst refspec not resolved correctly\n'; cat "$ERR_E2"
fi
rm -f "$ERR_E2"

# E3 -- literal HEAD, checked out on branchB
git -C "$FIX_LOCAL" checkout -q branchB
PAY_E3=$(payload "git -C $FIX_LOCAL push origin HEAD")
ERR_E3=$(mktemp "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX")
invoke_project "$PAY_E3" "$HOME_E" "sess-E3" >/dev/null 2>"$ERR_E3"; c=$?
want_deny "$c" "E3: literal HEAD refspec"
if grep -q "HEAD (branchB)" "$ERR_E3" && grep -q "origin/branchB" "$ERR_E3" && grep -q "b_new_file.txt" "$ERR_E3"; then
  pass=$((pass+1)); printf '   ok   E3: HEAD resolved to the checked-out branch (branchB) by name\n'
else
  fail=$((fail+1)); printf '  FAIL  E3: HEAD refspec not resolved correctly\n'; cat "$ERR_E3"
fi
rm -f "$ERR_E3"

# E4 -- no refspec at all; current branch (branchB) has an upstream
PAY_E4=$(payload "git -C $FIX_LOCAL push")
ERR_E4=$(mktemp "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX")
invoke_project "$PAY_E4" "$HOME_E" "sess-E4" >/dev/null 2>"$ERR_E4"; c=$?
want_deny "$c" "E4: bare push, no refspec"
if grep -q "branchB (current branch, no refspec)" "$ERR_E4" && grep -q "origin/branchB" "$ERR_E4"; then
  pass=$((pass+1)); printf '   ok   E4: no-refspec push resolved via the current branch + its upstream\n'
else
  fail=$((fail+1)); printf '  FAIL  E4: no-refspec push not resolved correctly\n'; cat "$ERR_E4"
fi
rm -f "$ERR_E4"

# E5 -- --tags
PAY_E5=$(payload "git -C $FIX_LOCAL push origin --tags")
ERR_E5=$(mktemp "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX")
invoke_project "$PAY_E5" "$HOME_E" "sess-E5" >/dev/null 2>"$ERR_E5"; c=$?
want_deny "$c" "E5: --tags"
if grep -q "v1.0 -> origin/v1.0" "$ERR_E5"; then
  pass=$((pass+1)); printf '   ok   E5: --tags lists the local tag\n'
else
  fail=$((fail+1)); printf '  FAIL  E5: --tags did not list the local tag\n'; cat "$ERR_E5"
fi
rm -f "$ERR_E5"

# E6 -- unresolvable refspec must say UNRESOLVED loudly, never a silent allow
PAY_E6=$(payload "git -C $FIX_LOCAL push origin does-not-exist-anywhere")
ERR_E6=$(mktemp "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX")
invoke_project "$PAY_E6" "$HOME_E" "sess-E6" >/dev/null 2>"$ERR_E6"; c=$?
want_deny "$c" "E6: unresolvable refspec still signposts (never silently allows)"
if grep -q "UNRESOLVED" "$ERR_E6"; then
  pass=$((pass+1)); printf '   ok   E6: unresolvable refspec says UNRESOLVED rather than guessing\n'
else
  fail=$((fail+1)); printf '  FAIL  E6: unresolvable refspec did not say UNRESOLVED\n'; cat "$ERR_E6"
fi
rm -f "$ERR_E6"

echo
echo "── F. a shell redirection never masquerades as a refspec (2>&1 case) ──────"
# Observed live 2026-09-16, against the re-applied 0R.12 resolver port:
# `git -C <path> push -u origin <branch> 2>&1 | tail -3` printed a manifest row
# for a phantom refspec literally named "2>&1" (UNRESOLVED 2>&1 -> origin/2>&1).
# A redirection is consumed by the SHELL before git ever sees it -- it must
# never reach the refspec parser as if it were a positional git argument.
git -C "$FIX_LOCAL" checkout -q branchB
HOME_F=$(new_home); TMP_HOMES+=("$HOME_F")
PAY_F=$(payload "git -C $FIX_LOCAL push -u origin branchB 2>&1 | tail -3")
ERR_F=$(mktemp "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX")
invoke_project "$PAY_F" "$HOME_F" "sess-F" >/dev/null 2>"$ERR_F"; c=$?
want_deny "$c" "F: -u origin <branch> 2>&1 | tail -3"
if ! grep -qF "2>&1" "$ERR_F" && ! grep -q "UNRESOLVED" "$ERR_F" && grep -q "branchB -> origin/branchB" "$ERR_F"; then
  pass=$((pass+1)); printf ' ok F: the redirection (2>&1) never surfaces as a phantom refspec\n'
else
  fail=$((fail+1)); printf ' FAIL F: a shell redirection token leaked into the refspec manifest\n'; cat "$ERR_F"
fi
rm -f "$ERR_F"

echo
printf 'RESULT: %d passed, %d failed.\n' "$pass" "$fail"
if [ "$fail" -eq 0 ]; then echo "PUSH SIGNPOST GUARD GREEN"; exit 0; fi
echo "PUSH SIGNPOST GUARD RED"; exit 1
