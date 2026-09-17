#!/bin/bash
# Matrix for the SHARED repo-target resolver (system/hooks/lib/git_target_resolver.py)
# as exercised by guard_git_push_signpost.sh -- and, in the PRIVATE ClaudeOps repo
# this file was ported from, also by guard_git_commit_signpost.sh.
#
# PORTED 2026-09-10 from
# ~/.claude/skills/ClaudeOps/system/hooks/tests/test_git_signpost_resolver.sh into
# this public repo. Path resolution below is unchanged from the original -- it was
# already location-relative ($(dirname "$0")/..), never hardcoded to the private
# tree, so it needed no adjustment to resolve HOOKS_DIR correctly from here. This
# file reaches nothing under ~/.claude/skills/ClaudeOps.
#
# COMMIT-GUARD SECTION IS SKIPPED BELOW, NOT DELETED. The cases in that section
# were written against guard_git_commit_signpost.sh, which does not exist in this
# repo -- the registered commit-time hook here is guard_no_upstream_commit_signpost.sh
# (see .claude/settings.json / hooks/hooks.json). Investigated 2026-09-10 by reading
# it in full, not assuming from the name: it denies a `git commit` only when the
# CURRENT BRANCH has no upstream configured (or its upstream is gone) -- a
# mirror-rot warning -- and it NEVER computes or prints repo identity; there is no
# "PUBLIC"/"PRIVATE" text anywhere in its source or its output (confirmed by grep
# and by a live run against a fresh no-upstream repo). The cases below assert
# exactly that identity text, which this guard structurally cannot produce -- it is
# a different guard doing a different job, not a rename of the one under test here.
# Per the ruling governing this port: SKIPPED, LOUDLY (printed in the run output,
# one-line reason at each case), never deleted -- a deleted test and a passing test
# are indistinguishable afterwards, and that is the failure this port exists to
# avoid repeating.
#
# WHY THE PUSH-GUARD CASES EXIST: cards 2.20/2.23 found the (private) commit guard
# was -C-aware but not cd-aware (a live commit under `cd ~/lifehack-brain && ...`
# was mislabeled PRIVATE), and the push guard's `||` handling dropped
# `cd X || exit; ...` even though that idiom guarantees cwd once execution reaches
# past it. This file drives the REAL hook script end to end (not just a library
# function) against two throwaway git repos standing in for the public/private
# repos, so a guard never watched refusing is not a guard.
#
# ISOLATION ADDED IN THIS PORT: every run_guard call below now gets its OWN fresh
# $HOME (a throwaway dir under $WORK) -- never the real $HOME. The guard writes its
# one-shot marker under $HOME/.claude/.push-signpost.<hash>, and that hash key is
# NOT derived from the push target -- only from $CLAUDE_CODE_SESSION_ID (or $PWD).
# A shared HOME would let one case's fire silently disarm every later case's deny
# in the same run. The ORIGINAL private test did NOT isolate $HOME explicitly; it
# happened to dodge the collision only because it also varies
# CLAUDE_CODE_SESSION_ID per case (each case's hash came out distinct on its own,
# incidentally) -- true of today's guard, but not a structural guarantee, and not
# true for every marker-keying scheme a guard might use (guard_no_upstream_commit_
# signpost.sh, for one, keys on session|toplevel|branch, not session alone). This
# port makes the isolation explicit and guard-agnostic instead of relying on that
# coincidence.

set -u
HOOKS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"; rm -f "$HOME/.claude/.commit-signpost."* "$HOME/.claude/.push-signpost."* "$HOME/.claude/.no-upstream-commit-signpost."* 2>/dev/null' EXIT

PUB="$WORK/public-repo"
PRIV="$WORK/private-repo"
mkdir -p "$PUB" "$PRIV"
for d in "$PUB" "$PRIV"; do
  git -C "$d" init -q -b main
  git -C "$d" config user.email test@test.local
  git -C "$d" config user.name test
  echo hi > "$d/f.txt"
  git -C "$d" add f.txt
  git -C "$d" commit -q -m init
done
git -C "$PUB" remote add origin "git@github.com:LifehackMethod/lifehack-brain.git"
git -C "$PRIV" remote add origin "git@github.com:egjokaj/ClaudeOps.git"
# a second, uncommitted change so the push guard has something to act on
echo more >> "$PUB/f.txt"
echo more >> "$PRIV/f.txt"

pass=0; fail=0; skipped=0
sid=0

run_guard() { # run_guard <script> <command-string> -- caller must bump $sid BEFORE calling
  local script="$1" cmd="$2"
  local payload
  payload=$(python3 -c 'import json,sys; print(json.dumps({"tool_input":{"command":sys.argv[1]}}))' "$cmd")
  # Fresh isolated $HOME per case (see ISOLATION note above) -- never the real
  # $HOME, so a guard's real one-shot marker is never spent and never leaks
  # across cases regardless of what key the guard hashes on.
  local case_home="$WORK/home.$sid"
  mkdir -p "$case_home/.claude"
  printf '%s' "$payload" | \
    HOME="$case_home" CLAUDE_CODE_SESSION_ID="test-$$-$sid" bash "$HOOKS_DIR/$script" 2>"$WORK/stderr.$sid" 1>"$WORK/stdout.$sid"
  echo $?
}

want() { # want <label> <expected-exit> <exit-got> <grep-pattern-or-empty>
  local label="$1" want_exit="$2" got_exit="$3" pattern="$4"
  if [ "$got_exit" != "$want_exit" ]; then
    fail=$((fail+1)); printf '  FAIL  %-70s (wanted exit %s, got %s)\n' "$label" "$want_exit" "$got_exit"
    return
  fi
  if [ "$pattern" = "@nonempty" ]; then
    # Assert the PROPERTY -- it refused AND explained -- never the wording.
    # An earlier version of this test grepped the literal phrase "@nonempty";
    # the guard was later reworded and this test reported a regression that did not
    # exist. Assert what must be true, not how it happens to be said.
    if [ ! -s "$WORK/stderr.$sid" ]; then
      fail=$((fail+1)); printf '  FAIL  %-70s (exit ok, but refused SILENTLY -- no explanation on stderr)\n' "$label"
      return
    fi
  elif [ -n "$pattern" ] && ! grep -q "$pattern" "$WORK/stderr.$sid"; then
    fail=$((fail+1)); printf '  FAIL  %-70s (exit ok, but stderr missing: %s)\n' "$label" "$pattern"
    return
  fi
  pass=$((pass+1)); printf '   ok   %s\n' "$label"
}

not_want() { # not_want <label> <forbidden-egrep-pattern> -- asserts pattern is ABSENT from stderr
  local label="$1" pattern="$2"
  if grep -Eq "$pattern" "$WORK/stderr.$sid"; then
    fail=$((fail+1)); printf '  FAIL  %-70s (stderr should NOT contain: %s)\n' "$label" "$pattern"
    return
  fi
  pass=$((pass+1)); printf '   ok   %s\n' "$label"
}

skip() { # skip <label> <one-line-reason>
  local label="$1" reason="$2"
  skipped=$((skipped+1))
  printf '  SKIP  %-70s (%s)\n' "$label" "$reason"
}

echo "── guard_git_push_signpost.sh ────────────────────────────────────────────"

sid=$((sid+1)); e=$(run_guard guard_git_push_signpost.sh "git -C $PUB push origin main")
want "git -C <public> push -> names PUBLIC repo, denies" 2 "$e" "PUBLIC"

sid=$((sid+1)); e=$(run_guard guard_git_push_signpost.sh "cd $PUB && git push origin main")
want "cd <public> && git push -> names PUBLIC repo, denies" 2 "$e" "PUBLIC"

sid=$((sid+1)); e=$(run_guard guard_git_push_signpost.sh "cd $PUB || exit; git push origin main")
want "cd <public> || exit; git push -> names PUBLIC repo, denies (2.23 case)" 2 "$e" "PUBLIC"

sid=$((sid+1)); e=$(run_guard guard_git_push_signpost.sh "cd $PUB || exit 1; git push origin main")
want "cd <public> || exit 1; git push (unpadded ;) -> names PUBLIC, denies" 2 "$e" "PUBLIC"

sid=$((sid+1)); e=$(run_guard guard_git_push_signpost.sh "cd $PUB || exit 1 ; git push origin main")
want "cd <public> || exit 1 ; git push (padded ;) -> names PUBLIC, denies" 2 "$e" "PUBLIC"

sid=$((sid+1)); e=$(run_guard guard_git_push_signpost.sh "cd $PUB; git push origin main")
want "cd <public>; git push (bare semicolon, no exit guard) -> names PUBLIC, denies" 2 "$e" "PUBLIC"

sid=$((sid+1)); e=$(run_guard guard_git_push_signpost.sh "cd $PUB || echo nope; git push origin main")
want "cd <public> || echo nope; git push -> REFUSES (non-exit guard, unproven)" 2 "$e" "@nonempty"

sid=$((sid+1)); e=$(run_guard guard_git_push_signpost.sh "git -C $WORK/does-not-exist-xyz789 push origin main")
want "git -C <nonexistent dir> push -> genuinely unresolvable target, REFUSES" 2 "$e" "cannot determine"

cd "$PRIV" || exit 1
sid=$((sid+1)); e=$(run_guard guard_git_push_signpost.sh "git push origin main")
want "plain git push (cwd=private, no -C/cd) -> names repo of \$PWD" 2 "$e" "PRIVATE"
cd "$HOOKS_DIR" || exit 1

sid=$((sid+1)); e=$(run_guard guard_git_push_signpost.sh 'git commit -m "reminder: git push later, not now"')
want "outbound-shaped text INSIDE a quoted string -> does not false-fire" 0 "$e" ""

sid=$((sid+1)); e=$(run_guard guard_git_push_signpost.sh 'echo "git push origin main"')
want "bare echo of push-shaped text -> does NOT fire (regression guard)" 0 "$e" ""

# FALLBACK PATH EXERCISED HERE: the lone, unbalanced apostrophe in "guard's"
# below (ordinary English, never closed by a matching quote) makes shlex raise
# on this command, so the PRIMARY shlex match never runs at all -- only the
# character-class regex fallback (the shlex-ValueError branch the file's own
# header documents at line 31, "heredoc, unbalanced quote") ever inspects this
# text. This is the ONLY case in this suite that actually reaches that
# fallback; the "bare echo" case above tokenises cleanly and never does.
sid=$((sid+1)); e=$(run_guard guard_git_push_signpost.sh "cat <<'EOF'
The guard's fallback path only runs when shlex actually breaks.
EOF
cd $PUB || exit 1; git push origin main")
want "FALLBACK PATH: shlex-breaking apostrophe + push-shaped text -> REFUSES" 2 "$e" "cannot determine the target repo"
not_want "FALLBACK PATH refusal must never name a repository" "PUBLIC|PRIVATE"

# PRIMARY PATH CONTROL: the identical push-shaped words as the case just above
# (cd ... || exit 1; git push origin main), plus a contraction's apostrophe,
# but this time fully inside ONE balanced double-quoted argument to `echo` --
# shlex tokenises the whole thing as a single quoted token, so it never
# reaches the fallback. Pairs with the case above to prove the primary path is
# not over-firing on the very words that (left unbalanced) make it fall
# through above.
sid=$((sid+1)); e=$(run_guard guard_git_push_signpost.sh "echo \"note to self: cd $PUB || exit 1; git push origin main -- guard's fallback doesn't run when this parses cleanly\"")
want "PRIMARY PATH control: same push-shaped words, balanced quoting -> silent" 0 "$e" ""

sid=$((sid+1)); e=$(run_guard guard_git_push_signpost.sh "git -C $PUB push origin main --force")
want "a real outbound act (with extra flags) -> DOES fire" 2 "$e" "PUBLIC"

echo "── guard_git_commit_signpost.sh -- SKIPPED (7 cases) ──────────────────────"
printf 'SKIP REASON: these 7 cases assert repo-identity text (PUBLIC/PRIVATE) on a\n'
printf 'commit-time guard stderr, so they apply only to a guard that actually\n'
printf 'computes and prints that identity. guard_git_commit_signpost.sh, the guard\n'
printf 'they were written against, does not exist in this repo -- the registered\n'
printf 'commit-time hook here (see .claude/settings.json) is\n'
printf 'guard_no_upstream_commit_signpost.sh instead, a different guard for a\n'
printf 'different condition (missing/gone upstream tracking, not repo identity).\n'
printf 'FAILURE MODE this skip exists to prevent: silently asserting identity text\n'
printf 'against a guard that never emits it would report a false PASS, not catch a\n'
printf 'real regression. When read in full on 2026-09-10, that guard printed no\n'
printf 'PUBLIC/PRIVATE text at all (confirmed by grep and a live run) -- but a\n'
printf 'guard can change after this comment was written. Re-read\n'
printf 'system/hooks/guard_no_upstream_commit_signpost.sh yourself before trusting\n'
printf 'this skip; do not carry this reason forward on faith. Per the ruling\n'
printf 'governing this port: SKIPPED, LOUDLY -- never deleted.\n'

skip "git -C <public> commit -> names PUBLIC repo, denies" \
  "applies only to a guard that prints repo identity; this one did not as of 2026-09-10 -- re-read it before trusting this skip (see SKIP REASON above)"
skip "cd <public> && git commit -> names PUBLIC repo, denies (root-cause case)" \
  "applies only to a guard that prints repo identity; this one did not as of 2026-09-10 -- re-read it before trusting this skip (see SKIP REASON above)"
skip "cd <public> || exit; git commit -> names PUBLIC repo, denies (live-failed case)" \
  "applies only to a guard that prints repo identity; this one did not as of 2026-09-10 -- re-read it before trusting this skip (see SKIP REASON above)"
skip "cd <public> || echo nope; git commit -> REFUSES (non-exit guard, unproven)" \
  "guard_no_upstream_commit_signpost.sh's trigger is upstream-tracking, not cd-ambiguity -- not the same behaviour"
skip "plain git commit (cwd=private, no -C/cd) -> names repo of \$PWD" \
  "applies only to a guard that prints repo identity; this one did not as of 2026-09-10 -- re-read it before trusting this skip (see SKIP REASON above)"
skip "outbound-shaped text INSIDE a quoted string -> does not false-fire" \
  "would only exercise a shared matching-robustness property, not the identity behaviour this suite is chartered to verify -- not genuinely the same case"
skip "a real outbound act (with extra flags) -> DOES fire" \
  "applies only to a guard that prints repo identity; this one did not as of 2026-09-10 -- re-read it before trusting this skip (see SKIP REASON above)"

echo
echo "$pass passed, $fail failed, $skipped skipped"
[ "$fail" -eq 0 ]
