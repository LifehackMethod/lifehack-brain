#!/bin/bash
# test_hook_sop_read_guard_deny_no_substitution.sh — regression test for R25: the guard's own
# DENY message must never itself perform the action it exists to gate.
#
# THE BUG (2026-09-16 R25-DENY-SUBSTITUTION-FINDING.md): guard_hook_sop_read.sh's final
# `deny "BLOCKED: ..."` call (line ~352) is a bash DOUBLE-quoted string containing two
# unescaped backtick spans — `` `bash $_REPO/system/tools/read_sop.sh hook` `` and
# `` `authority: user` ``. Building that string to pass to deny() RUNS command substitution,
# so span 1 actually EXECUTES read_sop.sh FOR REAL as a side effect of being denied — printing
# the SOP docs into the denial's own text and silently stamping the session's receipt. The very
# next identical retry then finds that self-planted receipt and is ALLOWED: the deny message
# substitutes for the compliance it exists to require, and the guard defeats itself.
#
# What this proves, against the UNFIXED guard (must go RED here — captured at authoring time):
#   (a) PASS — a blocked hook-plane write still denies (exit 2); the bug is not "always allow".
#   (b) FAIL — a receipt DOES appear after that single deny, though nothing was ever read.
#   (c) FAIL — the identical retry is ALLOWED (exit 0), not denied — the actual bypass.
#   (d) FAIL — the deny text does not contain the literal redirect phrase; it contains
#       read_sop.sh's own printed SOP banner instead, because span 1 executed rather than
#       stayed prose.
#   (e) PASS — a genuine read_sop.sh run (the legitimate path) still unblocks normally; the
#       fix must not touch this.
# After the fix (escaped/restructured backticks so the string is inert prose), all five pass.
#
# Uses a fully scratch HOME (mktemp -d, isolated $HOME/.claude/run/sop receipt store) so this
# test can assert the receipt store's exact contents without touching the real one or any
# other test's state.
#
# Deny = exit 2. Allow = exit 0. Run: bash system/hooks/tests/test_hook_sop_read_guard_deny_no_substitution.sh

set -uo pipefail

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$HOOKS/../.." && pwd)"
GUARD="$HOOKS/guard_hook_sop_read.sh"
READ_SOP="$REPO/system/tools/read_sop.sh"
[ -f "$GUARD" ] || { echo "CANNOT RUN: no hook at $GUARD"; exit 1; }
[ -f "$READ_SOP" ] || { echo "CANNOT RUN: no tool at $READ_SOP"; exit 1; }

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

# A fresh, never-seen session_id per invocation -- guarantees no stale SOP receipt exists for
# it, so a DENY case reliably hits the real deny (exit 2), never the CANNOT-DETERMINE path.
_sid() { python3 -c "import uuid; print(uuid.uuid4())"; }

# Fully isolated HOME for this test's whole run -- a scratch receipt store, never the real one.
SCRATCH_HOME="$(mktemp -d)"
trap 'rm -rf "$SCRATCH_HOME"' EXIT
RUN_DIR="$SCRATCH_HOME/.claude/run/sop"

TARGET="$REPO/system/hooks/guard_invented_by_test.sh"  # need not exist -- only its path matters

payload() {
  # tool_name Edit, file_path in the hook plane (not tests/) -- IS_WRITE=1, receipt required.
  python3 -c "
import json, sys
print(json.dumps({'tool_name': 'Edit', 'tool_input': {'file_path': sys.argv[1]}, 'session_id': sys.argv[2]}))" \
    "$TARGET" "$1"
}

run_guard() {
  # $1 = session id to use in the payload
  printf '%s' "$(payload "$1")" | env -i HOME="$SCRATCH_HOME" PATH="$PATH" bash "$GUARD"
}

SID="$(_sid)"
RECEIPT_SESSION="$RUN_DIR/hook.$SID.receipt"

echo "── (a) first blocked hook-plane write → deny (exit 2) ─────────────────────────────────"
OUT_A="$(run_guard "$SID" 2>&1)"
RC_A=$?
[ "$RC_A" = 2 ] && ok || bad "a-deny" "expected exit 2, got $RC_A"

echo "── (b) NO SOP receipt file was created anywhere by that single deny ───────────────────"
CREATED_ANY=0
if [ -d "$RUN_DIR" ]; then
  for f in "$RUN_DIR"/*.receipt; do
    [ -e "$f" ] || continue
    CREATED_ANY=1
    echo "    found receipt: $f -> $(cat "$f" 2>/dev/null)"
  done
fi
[ "$CREATED_ANY" = 0 ] && ok || bad "b-no-receipt" "a DENY created a receipt in $RUN_DIR (this is the R25 self-certification bug)"

echo "── (c) retry the identical payload → still denied (exit 2), not silently allowed ──────"
OUT_C="$(run_guard "$SID" 2>&1)"
RC_C=$?
[ "$RC_C" = 2 ] && ok || bad "c-deny-retry" "expected exit 2 on identical retry, got $RC_C (the R25 bypass: a prior deny self-planted a receipt that now ALLOWS the same blocked write)"

echo "── (d) deny message shows the redirect as TEXT, and never executes it ─────────────────"
case "$OUT_A" in
  *bash*read_sop.sh\ hook*)
    ok ;;
  *)
    bad "d-literal-text" "deny message did not contain the literal, unexecuted phrase 'bash ... read_sop.sh hook'" ;;
esac
case "$OUT_A" in
  *'════'*)
    bad "d-no-execution" "deny message contains read_sop.sh's OWN printed SOP banner (════) -- span 1 executed instead of staying prose" ;;
  *)
    ok ;;
esac

echo "── (e) negative control: a LEGITIMATE read_sop.sh run still unblocks the write ────────"
LEGIT_SID="$(_sid)"
env -i HOME="$SCRATCH_HOME" PATH="$PATH" CLAUDE_CODE_SESSION_ID="$LEGIT_SID" bash "$READ_SOP" hook >/dev/null 2>&1
run_guard "$LEGIT_SID" >/dev/null 2>&1
RC_E=$?
[ "$RC_E" = 0 ] && ok || bad "e-legit-allow" "expected exit 0 after a real read_sop.sh run, got $RC_E"

echo
if [ "$fail" = 0 ]; then
  echo "RESULT: $pass passed, 0 failed."
  echo "HOOK-SOP-READ GUARD DENY-NO-SUBSTITUTION GREEN"
  exit 0
else
  echo "RESULT: $pass passed, $fail failed."
  exit 1
fi
