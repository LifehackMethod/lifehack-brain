#!/bin/bash
# Regression coverage for `system/hooks/guard_git_push_signpost.sh`'s cwd-tracking
# defect behind a defensive `cd X || exit 1` idiom (A1.3, fixed 2026-09-16).
#
# A SEPARATE file from test_git_push_signpost.sh (A1.7's double-registration-marker
# suite, and A1.9's refspec-summary work, in progress on another branch) so this
# fix's own regression case does not collide with either.
#
# THE BUG (the 2026-09-08 incident, per the guard's own header): the cwd-tracking
# loop reset `cwd = ""` on ANY segment preceded by `|`/`||`, even when the cwd it
# was about to discard had been established by an earlier, unconditional `cd` that
# already ran and succeeded. For
#     cd <public repo> || exit 1 ; git push origin main
# -- the standard "cd-or-bail" idiom -- the `cd` IS the left side of the `||`; it
# ran and succeeded. But the following `exit 1` segment is itself preceded by
# `||`, and the old code read that as license to forget the cwd regardless of
# WHICH segment established it. The following `;`-separated push then fell back to
# bare $PWD and printed a confident, WRONG repo identity -- the dangerous
# direction, since a push actually going to the public, student-facing repo could
# be signposted "PRIVATE — students never see this."
#
# THE FIX: only refuse to ADOPT a `cd` target when the `cd` segment itself is
# preceded by `|`/`||` (its own effect on the parent shell's cwd is not
# trustworthy); a cwd already tracked from an earlier, trusted `cd` is left
# untouched by a LATER segment's preceding operator.
#
# Ported from records/2026-09-14-lane-triage/tests/test3_guard_git_push_signpost.sh
# (nav's triage), adapted to the REGISTERED invocation form against the repo's own
# copy and to a scratch $HOME per case (the original script wrote its one-shot
# cleanup marker directly under the real $HOME; this version never touches the real
# ~/.claude/.push-signpost.* for real). Runs `git -C <dir>
# rev-parse/remote/log/diff` read-only against two real, already-existing local
# repos; a real `git push` is never executed by this test.
# Run: bash system/hooks/tests/test_push_signpost_cwd_tracking.sh   (exit 0 = all pass)

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)" || exit 1
GUARD_REL="system/hooks/guard_git_push_signpost.sh"
PRIVATE_REPO="$HOME/.claude/skills/ClaudeOps"

pass=0; fail=0
WORK=$(mktemp -d "${TMPDIR:-/tmp}/push-signpost-cwd-test.XXXXXX") || exit 1
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

if [ ! -d "$PRIVATE_REPO/.git" ]; then
  echo "CANNOT RUN: $PRIVATE_REPO is not a git repo on this machine -- this suite needs a real"
  echo "second local repo (with a different, private-looking remote) to invoke from, to prove"
  echo "the fixed cwd-tracking overrides bare \$PWD. Skipping (not a guard failure)."
  exit 0
fi

payload() { python3 -c 'import json, sys; print(json.dumps({"tool_input": {"command": sys.argv[1]}, "session_id": sys.argv[2]}))' "$1" "$2"; }

run_case() { # run_case <label> <command-text> <invoking-cwd> <expect_substring>
  local label="$1" cmd="$2" cwd="$3" expect="$4"
  local home sid pay out rc
  home=$(mktemp -d "$WORK/home.XXXXXX"); mkdir -p "$home/.claude"
  sid="t3cwd-$RANDOM-$RANDOM"
  pay=$(payload "$cmd" "$sid")
  out=$(cd "$cwd" && printf '%s' "$pay" | HOME="$home" CLAUDE_CODE_SESSION_ID="$sid" CLAUDE_PROJECT_DIR="$REPO_ROOT" \
    bash -c 'bash "${CLAUDE_PROJECT_DIR}/'"$GUARD_REL"'"' 2>&1)
  rc=$?
  if printf '%s' "$out" | /usr/bin/grep -qF "$expect"; then
    pass=$((pass+1)); printf '   ok   %s\n' "$label"
  else
    fail=$((fail+1)); printf '  FAIL  %s -- did not find expected: %s\n       got (rc=%s): %s\n' "$label" "$expect" "$rc" "$out"
  fi
}

echo "── known-good: cd <public> && git push -- '&&' never reset cwd, stays PUBLIC ──"
run_case "cd PUBLIC && git push" \
  "cd $REPO_ROOT && git push origin main" \
  "$PRIVATE_REPO" \
  "PUBLIC -- SHIPS TO STUDENTS"

echo
echo "── bug case: cd <public> || exit 1 ; git push -- the defensive cd-or-bail idiom ──"
run_case "cd PUBLIC || exit 1 ; git push (invoked from PRIVATE repo cwd)" \
  "cd $REPO_ROOT || exit 1 ; git push origin main" \
  "$PRIVATE_REPO" \
  "PUBLIC -- SHIPS TO STUDENTS"

echo
printf 'RESULT: %d passed, %d failed.\n' "$pass" "$fail"
if [ "$fail" -eq 0 ]; then echo "PUSH SIGNPOST CWD-TRACKING GREEN"; exit 0; fi
echo "PUSH SIGNPOST CWD-TRACKING RED"; exit 1
