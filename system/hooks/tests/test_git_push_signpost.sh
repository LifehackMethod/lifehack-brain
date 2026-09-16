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
printf 'RESULT: %d passed, %d failed.\n' "$pass" "$fail"
if [ "$fail" -eq 0 ]; then echo "PUSH SIGNPOST GUARD GREEN"; exit 0; fi
echo "PUSH SIGNPOST GUARD RED"; exit 1
