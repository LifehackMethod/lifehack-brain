#!/bin/bash
# Regression coverage for `system/hooks/guard_gmail_destructive.sh`'s parser-crash catch-all.
#
# THE BUG (A1.1, fixed 2026-09-16): the guard's bash wrapper only special-cased a
# gws_guard.py child exit of 7 (BLOCK). Any OTHER non-zero exit -- e.g. an uncaught
# Python exception, whose default exit code is 1, not 7 -- fell through to the
# unconditional `exit 0` at the end of the file, i.e. ALLOW, on a command the guard
# itself would otherwise recognise as destructive. Already flagged as a code-review
# "GAP (unexecuted)" in records/2026-09-12-research/guard-verification.md §1; this
# suite fires it live. Ported from
# records/2026-09-14-lane-triage/tests/test1_guard_gmail_destructive.sh (nav's
# triage), adapted to the REGISTERED invocation form against the repo's own copy
# (the triage script ran the installed plugin 0.3.20 cache copy instead).
#
# THE FIX: mirror guard_gmail_send.sh's existing RC/elif pattern -- capture RC=$?
# after the gws_guard.py call and add `elif [ "$RC" -ne 0 ]; then deny_parse; fi`
# (deny_parse()/$PARSE_DENY already existed in this file, unused, before the fix).
#
# Case C fault-injects gws_guard.py via a throwaway python3 shim placed first on
# PATH; every OTHER invocation (the guard's own JSON-field extraction) passes
# through to the real /usr/bin/python3 unchanged. Never executes a real Gmail call
# -- this is a PreToolUse hook; it only reads JSON on stdin and decides.
# Run: bash system/hooks/tests/test_gmail_destructive_guard.sh   (exit 0 = all pass)

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)" || exit 1
GUARD_REL="system/hooks/guard_gmail_destructive.sh"

pass=0; fail=0
FAKEBIN=$(mktemp -d "${TMPDIR:-/tmp}/gmail-destructive-test.XXXXXX") || exit 1
cleanup() { rm -rf "$FAKEBIN"; }
trap cleanup EXIT

cat > "$FAKEBIN/python3" <<'SHIM'
#!/bin/bash
# Test double for python3: fault-injects ONE specific child invocation (the shared
# gws_guard.py library call) so we can observe what the unmodified/fixed wrapper
# does when that child exits with a code it does not special-case. Every other
# invocation (e.g. the guard's own JSON-field extraction) is passed through to the
# real python3 unchanged.
REAL=/usr/bin/python3
for a in "$@"; do
  case "$a" in
    */gws_guard.py)
      # Simulate an uncaught exception inside gws_guard.py: no stdout, exit code
      # that is neither 0 (PASS) nor 7 (BLOCK) -- exactly what Python's default
      # unhandled-exception exit (1) looks like to a caller checking `-eq 7`.
      exit 42
      ;;
  esac
done
exec "$REAL" "$@"
SHIM
chmod +x "$FAKEBIN/python3"

payload() { python3 -c 'import json, sys; print(json.dumps({"tool_input": {"command": sys.argv[1]}}))' "$1"; }

invoke() { # invoke <payload-json> [extra-path]
  if [ -n "${2:-}" ]; then
    printf '%s' "$1" | PATH="$2:$PATH" CLAUDE_PROJECT_DIR="$REPO_ROOT" \
      bash -c 'bash "${CLAUDE_PROJECT_DIR}/'"$GUARD_REL"'"'
  else
    printf '%s' "$1" | CLAUDE_PROJECT_DIR="$REPO_ROOT" \
      bash -c 'bash "${CLAUDE_PROJECT_DIR}/'"$GUARD_REL"'"'
  fi
}

want_allow() { if [ "$1" -eq 0 ]; then pass=$((pass+1)); printf '   ok   %s (allowed)\n' "$2"; else fail=$((fail+1)); printf '  FAIL  %s (expected allow/exit 0, got %s)\n' "$2" "$1"; fi; }
want_deny()  { if [ "$1" -eq 2 ]; then pass=$((pass+1)); printf '   ok   %s (denied)\n' "$2"; else fail=$((fail+1)); printf '  FAIL  %s (expected deny/exit 2, got %s)\n' "$2" "$1"; fi; }

echo "── A. benign gmail command, real python3 -- must ALLOW ──────────────────"
PAY_A=$(payload "gws gmail users threads list --user-id me")
invoke "$PAY_A" >/dev/null 2>&1; want_allow "$?" "benign gmail list"

echo
echo "── B. real destructive command, real python3 -- must BLOCK ──────────────"
PAY_B=$(payload "gws gmail users threads trash --user-id me --id 18abc")
invoke "$PAY_B" >/dev/null 2>&1; want_deny "$?" "real destructive trash (real python3)"

echo
echo "── C. same destructive command, gws_guard.py fault-injected to exit 42 ──"
invoke "$PAY_B" "$FAKEBIN" >/dev/null 2>&1; want_deny "$?" "destructive trash, gws_guard.py exits 42 (parser-crash catch-all)"

echo
printf 'RESULT: %d passed, %d failed.\n' "$pass" "$fail"
if [ "$fail" -eq 0 ]; then echo "GMAIL DESTRUCTIVE GUARD GREEN"; exit 0; fi
echo "GMAIL DESTRUCTIVE GUARD RED"; exit 1
