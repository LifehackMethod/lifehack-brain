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
# THE FIX: key the marker on session id + WHICH push this is (the resolved
# target dir + the push subcommand own argv -- remote + refspec(s); T3.2b,
# 2026-09-18, replacing the old raw-command-text hash, which denied the
# same push again whenever the command spelling changed, e.g. a different
# `tail` suffix), created via `mkdir` (atomic on POSIX filesystems) and
# NEVER deleted. This file exercises exactly the shapes the fix promises:
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
echo "── G. --delete/-d refspecs render as DELETE, never UNRESOLVED or a false 0/0 ──"
# Bug 1 (fix card 2026-09-16-round-4/FIXCARD-PUSH-SIGNPOST-DELETE-AND-BASE.md): the
# flag-parsing loop never recognized --delete/-d at all, so a remote branch deletion
# either printed UNRESOLVED (no same-named local branch) or a false-reassuring
# "0 commit(s), 0 file(s)" (a same-named local branch happened to exist) -- never
# what it actually is. The colon form (`git push origin :branch`) already worked;
# --delete/-d now shares the exact same render path and text.
HOME_G=$(new_home); TMP_HOMES+=("$HOME_G")

# G1 -- --delete of a branch with no same-named local ref: must say DELETE, never
# UNRESOLVED. Mutation-provable: reverting the fix reintroduces the literal string
# UNRESOLVED in this exact scenario.
PAY_G1=$(payload "git -C $FIX_LOCAL push origin --delete ghost-branch-xyz-never-existed")
ERR_G1=$(mktemp "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX")
invoke_project "$PAY_G1" "$HOME_G" "sess-G1" >/dev/null 2>"$ERR_G1"; c=$?
want_deny "$c" "G1: --delete, no same-named local branch"
if grep -q "DELETE origin/ghost-branch-xyz-never-existed" "$ERR_G1" && ! grep -q "UNRESOLVED" "$ERR_G1"; then
  pass=$((pass+1)); printf '   ok   G1: renders DELETE, never UNRESOLVED\n'
else
  fail=$((fail+1)); printf '  FAIL  G1: did not render as a clean DELETE\n'; cat "$ERR_G1"
fi
rm -f "$ERR_G1"

# G2 -- --delete of a branch that DOES exist locally (branchA, from section E): the
# worse failure mode -- a false "0 commit(s), 0 file(s)" that actively reassures
# nothing is happening. Mutation-provable: a fix that only guards the
# "local ref missing" path (partial fix) still fails this one.
PAY_G2=$(payload "git -C $FIX_LOCAL push origin --delete branchA")
ERR_G2=$(mktemp "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX")
invoke_project "$PAY_G2" "$HOME_G" "sess-G2" >/dev/null 2>"$ERR_G2"; c=$?
want_deny "$c" "G2: --delete of a branch that exists locally too"
if grep -q "DELETE origin/branchA" "$ERR_G2" && ! grep -q "0 commit(s), 0 file(s)" "$ERR_G2"; then
  pass=$((pass+1)); printf '   ok   G2: renders DELETE, never the false 0/0 summary\n'
else
  fail=$((fail+1)); printf '  FAIL  G2: still shows the false 0-commits reassurance\n'; cat "$ERR_G2"
fi
rm -f "$ERR_G2"

# G3 -- the -d short flag, and --delete with TWO branch names: proves the fix
# is not a single-refspec special case.
PAY_G3=$(payload "git -C $FIX_LOCAL push origin -d branchA branchB")
ERR_G3=$(mktemp "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX")
invoke_project "$PAY_G3" "$HOME_G" "sess-G3" >/dev/null 2>"$ERR_G3"; c=$?
want_deny "$c" "G3: -d with two branch names"
if grep -q "DELETE origin/branchA" "$ERR_G3" && grep -q "DELETE origin/branchB" "$ERR_G3"; then
  pass=$((pass+1)); printf '   ok   G3: both branches render as DELETE\n'
else
  fail=$((fail+1)); printf '  FAIL  G3: not both branches rendered as DELETE\n'; cat "$ERR_G3"
fi
rm -f "$ERR_G3"

# G4 -- the colon form is unaffected functionally, but now shares the SAME render
# text as --delete/-d (the old "[DELETE] ... (no local ref pushed)" text is gone).
PAY_G4=$(payload "git -C $FIX_LOCAL push origin :branchA")
ERR_G4=$(mktemp "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX")
invoke_project "$PAY_G4" "$HOME_G" "sess-G4" >/dev/null 2>"$ERR_G4"; c=$?
want_deny "$c" "G4: colon-form delete"
if grep -q "DELETE origin/branchA" "$ERR_G4" && grep -q "remote tip" "$ERR_G4" && ! grep -q "no local ref pushed" "$ERR_G4"; then
  pass=$((pass+1)); printf '   ok   G4: colon form uses the new shared DELETE (remote tip ...) format\n'
else
  fail=$((fail+1)); printf '  FAIL  G4: colon form did not use the new shared format\n'; cat "$ERR_G4"
fi
rm -f "$ERR_G4"

echo
echo "── H. NEW-BRANCH base: upstream, then nearest-by-merge-base (main vs V2) ──"
# Bug 2 (same fix card): a brand-new branch's manifest was ALWAYS diffed against
# origin/main via find_remote_default(), never the branch's real base. A branch
# built on V2 with 0-3 real commits showed 100+ phantom commits (everything V2 has
# ahead of main). Dedicated scratch fixture, mirroring the card's own test recipe:
# init, commit on main, branch V2 with N=2 extra commits, branch the test subject
# off V2 with M=1 more commit, no upstream set.
HFIX_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/push-signpost-basefixture.XXXXXX") || exit 1
TMP_HOMES+=("$HFIX_ROOT")
HFIX_BARE="$HFIX_ROOT/remote.git"
HFIX_LOCAL="$HFIX_ROOT/local"
git init --bare -q "$HFIX_BARE"
git init -q "$HFIX_LOCAL"
export GIT_AUTHOR_NAME="H Test" GIT_AUTHOR_EMAIL="h@example.invalid"
export GIT_COMMITTER_NAME="H Test" GIT_COMMITTER_EMAIL="h@example.invalid"
git -C "$HFIX_LOCAL" checkout -q -b main
git -C "$HFIX_LOCAL" remote add origin "$HFIX_BARE"
printf 'root\n' > "$HFIX_LOCAL/root.txt"; git -C "$HFIX_LOCAL" add root.txt; git -C "$HFIX_LOCAL" commit -q -m "root commit"
git -C "$HFIX_LOCAL" push -q -u origin main
git -C "$HFIX_LOCAL" symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main

# V2: the other long-lived integration branch, N=2 commits ahead of main.
git -C "$HFIX_LOCAL" checkout -q -b V2 main
printf 'v2-1\n' > "$HFIX_LOCAL/v2_1.txt"; git -C "$HFIX_LOCAL" add v2_1.txt; git -C "$HFIX_LOCAL" commit -q -m "V2 commit 1"
printf 'v2-2\n' > "$HFIX_LOCAL/v2_2.txt"; git -C "$HFIX_LOCAL" add v2_2.txt; git -C "$HFIX_LOCAL" commit -q -m "V2 commit 2"
git -C "$HFIX_LOCAL" push -q -u origin V2

# H1 subject: forked off V2, M=1 more commit, NO upstream set.
git -C "$HFIX_LOCAL" checkout -q -b v2-based-newbranch V2
printf 'feat\n' > "$HFIX_LOCAL/v2_feature.txt"; git -C "$HFIX_LOCAL" add v2_feature.txt; git -C "$HFIX_LOCAL" commit -q -m "feature on top of V2"

# Advance main independently (a main-only commit unrelated to V2) so the H3
# regression case has a clean, non-trivial count difference either way.
git -C "$HFIX_LOCAL" checkout -q main
printf 'main-2\n' > "$HFIX_LOCAL/main_2.txt"; git -C "$HFIX_LOCAL" add main_2.txt; git -C "$HFIX_LOCAL" commit -q -m "main-only commit"
git -C "$HFIX_LOCAL" push -q origin main

# H3 subject: forked directly off the (advanced) main, no V2 relation, no upstream.
git -C "$HFIX_LOCAL" checkout -q -b main-based-branch main
printf 'mfeat\n' > "$HFIX_LOCAL/main_feature.txt"; git -C "$HFIX_LOCAL" add main_feature.txt; git -C "$HFIX_LOCAL" commit -q -m "feature on top of main"

# H2 subject: forked off main (so the merge-base heuristic ALONE would pick main --
# 1 commit ahead of main vs 2 ahead of V2), but with branch.<name>.remote/.merge
# explicitly configured to V2. Proves the configured upstream short-circuits the
# heuristic rather than merely agreeing with it by coincidence.
git -C "$HFIX_LOCAL" checkout -q -b upstream-override main
printf 'ofeat\n' > "$HFIX_LOCAL/upstream_feature.txt"; git -C "$HFIX_LOCAL" add upstream_feature.txt; git -C "$HFIX_LOCAL" commit -q -m "feature, upstream forced to V2"
git -C "$HFIX_LOCAL" config branch.upstream-override.remote origin
git -C "$HFIX_LOCAL" config branch.upstream-override.merge refs/heads/V2
unset GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL

HOME_H=$(new_home); TMP_HOMES+=("$HOME_H")

# H1 -- V2-based branch, no upstream: must show "vs origin/V2" and exactly the
# M=1 real commit, never "vs origin/main" or the inflated M+N=3 count. Mutation-
# provable: reverting to find_remote_default()-only makes this assert vs main
# and the inflated count instead.
PAY_H1=$(payload "git -C $HFIX_LOCAL push origin v2-based-newbranch")
ERR_H1=$(mktemp "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX")
invoke_project "$PAY_H1" "$HOME_H" "sess-H1" >/dev/null 2>"$ERR_H1"; c=$?
want_deny "$c" "H1: NEW BRANCH forked off V2, no upstream"
if grep -q "\[NEW BRANCH vs origin/V2\]" "$ERR_H1" && grep -q "1 commit(s), 1 file(s):" "$ERR_H1" && ! grep -q "vs origin/main" "$ERR_H1"; then
  pass=$((pass+1)); printf '   ok   H1: based against origin/V2, exactly 1 commit, never main\n'
else
  fail=$((fail+1)); printf '  FAIL  H1: wrong NEW-BRANCH base or count\n'; cat "$ERR_H1"
fi
rm -f "$ERR_H1"

# H2 -- upstream set takes priority over the heuristic even when the heuristic
# alone would have picked a DIFFERENT (also real) candidate.
PAY_H2=$(payload "git -C $HFIX_LOCAL push origin upstream-override")
ERR_H2=$(mktemp "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX")
invoke_project "$PAY_H2" "$HOME_H" "sess-H2" >/dev/null 2>"$ERR_H2"; c=$?
want_deny "$c" "H2: NEW BRANCH with an explicit upstream configured"
if grep -q "\[NEW BRANCH vs origin/V2\]" "$ERR_H2" && ! grep -q "vs origin/main" "$ERR_H2"; then
  pass=$((pass+1)); printf '   ok   H2: configured upstream (V2) wins over the merge-base heuristic\n'
else
  fail=$((fail+1)); printf '  FAIL  H2: configured upstream did not win\n'; cat "$ERR_H2"
fi
rm -f "$ERR_H2"

# H3 -- regression: a branch built directly off main, unrelated to V2, must still
# land "vs origin/main" (non-trivial distinct counts: 1 vs main, 2 vs V2).
PAY_H3=$(payload "git -C $HFIX_LOCAL push origin main-based-branch")
ERR_H3=$(mktemp "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX")
invoke_project "$PAY_H3" "$HOME_H" "sess-H3" >/dev/null 2>"$ERR_H3"; c=$?
want_deny "$c" "H3: NEW BRANCH forked off main, no V2 relation"
if grep -q "\[NEW BRANCH vs origin/main\]" "$ERR_H3" && ! grep -q "vs origin/V2" "$ERR_H3"; then
  pass=$((pass+1)); printf '   ok   H3: main-based branch still lands vs origin/main\n'
else
  fail=$((fail+1)); printf '  FAIL  H3: main-based branch was wrongly attributed to V2\n'; cat "$ERR_H3"
fi
rm -f "$ERR_H3"

echo
echo "── I. T3.2a: a ~/ \$HOME \${HOME} cd/-C target RESOLVES — never a false cannot-determine ──"
# shlex-based target extraction performs NO shell expansion, so a cd/-C target
# written as "~", "~/repo", "\$HOME/repo" or "\${HOME}/repo" used to fail the
# existence check and refuse "cannot determine the target repo" on a real,
# resolvable push (observed live 2026-09-18) — the session was denied but told
# nothing useful. Fixed by expanding with THIS HOOK OWN \$HOME before the
# check, exactly as the twin guard_commit_identity.sh does (commit 3f03efcd).
# Fixture: a repo named lifehack-brain INSIDE a scratch HOME, so every
# ~/\$HOME form under that HOME lands on exactly this fixture. A tilde path
# that genuinely does not exist must STILL refuse (mutation control).
IFIX_HOME=$(mktemp -d "${TMPDIR:-/tmp}/push-signpost-tildehome.XXXXXX") || exit 1
TMP_HOMES+=("$IFIX_HOME")
mkdir -p "$IFIX_HOME/.claude"
IFIX_BARE="$IFIX_HOME/remote.git"
IFIX_LOCAL="$IFIX_HOME/lifehack-brain"
git init --bare -q "$IFIX_BARE"
git init -q "$IFIX_LOCAL"
export GIT_AUTHOR_NAME="T32 Test" GIT_AUTHOR_EMAIL="t32@example.invalid"
export GIT_COMMITTER_NAME="T32 Test" GIT_COMMITTER_EMAIL="t32@example.invalid"
git -C "$IFIX_LOCAL" checkout -q -b main
git -C "$IFIX_LOCAL" remote add origin "$IFIX_BARE"
printf 'root\n' > "$IFIX_LOCAL/root.txt"; git -C "$IFIX_LOCAL" add root.txt; git -C "$IFIX_LOCAL" commit -q -m "root commit"
unset GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL

tilde_case() { # tilde_case <label> <session> <expected-rc> <command> <must-contain> <must-not-contain>
  local label="$1" sess="$2" exprc="$3" cmd="$4" want_in="$5" want_out="$6"
  local err rc
  err=$(mktemp "${TMPDIR:-/tmp}/push-signpost-test.XXXXXX")
  payload "$cmd" | CLAUDE_PROJECT_DIR="$REPO_ROOT" HOME="$IFIX_HOME" CLAUDE_CODE_SESSION_ID="$sess" \
    bash -c 'bash "${CLAUDE_PROJECT_DIR}/'"$GUARD_REL"'"' >/dev/null 2>"$err"
  rc=$?
  if [ "$rc" -ne "$exprc" ]; then
    fail=$((fail+1)); printf ' FAIL %s (expected exit %s, got %s)\n' "$label" "$exprc" "$rc"; cat "$err"; rm -f "$err"; return
  fi
  pass=$((pass+1)); printf ' ok %s (exit %s)\n' "$label" "$rc"
  if [ -n "$want_in" ] && ! grep -qF "$want_in" "$err"; then
    fail=$((fail+1)); printf ' FAIL %s (output missing [%s])\n' "$label" "$want_in"; cat "$err"; rm -f "$err"; return
  fi
  if [ -n "$want_in" ]; then pass=$((pass+1)); fi
  if [ -n "$want_out" ] && grep -qF "$want_out" "$err"; then
    fail=$((fail+1)); printf ' FAIL %s (output must NOT contain [%s])\n' "$label" "$want_out"; cat "$err"; rm -f "$err"; return
  fi
  if [ -n "$want_out" ]; then pass=$((pass+1)); fi
  rm -f "$err"
}

tilde_case "I1: cd ~/repo resolves + signposts"   "sess-I1" 2 'cd ~/lifehack-brain && git push origin main' "📍 PUSH · lifehack-brain" "cannot determine the target repo"
tilde_case "I2: git -C ~/repo resolves"           "sess-I2" 2 'git -C ~/lifehack-brain push origin main' "📍 PUSH · lifehack-brain" "cannot determine the target repo"
tilde_case "I3: cd \$HOME/repo resolves"          "sess-I3" 2 'cd $HOME/lifehack-brain && git push origin main' "📍 PUSH · lifehack-brain" "cannot determine the target repo"
tilde_case "I4: cd \${HOME}/repo resolves"        "sess-I4" 2 'cd ${HOME}/lifehack-brain && git push origin main' "📍 PUSH · lifehack-brain" "cannot determine the target repo"
tilde_case "I5: missing tilde path STILL refuses" "sess-I5" 2 'git -C ~/no-such-repo-t32 push origin main' "cannot determine the target repo" "📍 PUSH · lifehack-brain"

echo
echo "── J. T3.2b: the marker keys on the PUSH (remote+refspecs), not the raw command ──"
# `git -C <repo> push origin branchB | tail -12` and `... | tail -8` are THE
# SAME push. The old marker key hashed the whole normalized command text, so
# each spelling denied separately (observed live 2026-09-18). Re-keyed on the
# resolved repo + the push subcommand own argv (remote + refspec(s)); a
# different remote or refspec still gets its own first-sight deny; a bare
# `git push` (empty argv) still falls back to the command text.
HOME_J=$(new_home); TMP_HOMES+=("$HOME_J")
PAY_J1=$(payload "git -C $FIX_LOCAL push origin branchB | tail -12")
invoke_project "$PAY_J1" "$HOME_J" "sess-J" >/dev/null 2>&1; c=$?
want_deny "$c" "J1: first sight of the push denies"
invoke_project "$PAY_J1" "$HOME_J" "sess-J" >/dev/null 2>&1; c=$?
want_allow "$c" "J2: byte-identical re-run yields"
PAY_J2=$(payload "git -C $FIX_LOCAL push origin branchB | tail -8")
invoke_project "$PAY_J2" "$HOME_J" "sess-J" >/dev/null 2>&1; c=$?
want_allow "$c" "J3: same push, different pipeline suffix -- NO second deny"
PAY_J3=$(payload "git -C $FIX_LOCAL push origin main | tail -12")
invoke_project "$PAY_J3" "$HOME_J" "sess-J" >/dev/null 2>&1; c=$?
want_deny "$c" "J4: different refspec (main, not branchB) denies once on its own"
invoke_project "$PAY_J3" "$HOME_J" "sess-J" >/dev/null 2>&1; c=$?
want_allow "$c" "J5: ...and its byte-identical re-run yields"
git init --bare -q "$FIX_ROOT/remote2.git"
git -C "$FIX_LOCAL" remote add upstream "$FIX_ROOT/remote2.git"
PAY_J4=$(payload "git -C $FIX_LOCAL push upstream branchB | tail -12")
invoke_project "$PAY_J4" "$HOME_J" "sess-J" >/dev/null 2>&1; c=$?
want_deny "$c" "J6: different REMOTE (upstream, not origin) denies once on its own"
invoke_project "$PAY_J4" "$HOME_J" "sess-J" >/dev/null 2>&1; c=$?
want_allow "$c" "J7: ...and its byte-identical re-run yields"

echo
printf 'RESULT: %d passed, %d failed.\n' "$pass" "$fail"
if [ "$fail" -eq 0 ]; then echo "PUSH SIGNPOST GUARD GREEN"; exit 0; fi
echo "PUSH SIGNPOST GUARD RED"; exit 1
