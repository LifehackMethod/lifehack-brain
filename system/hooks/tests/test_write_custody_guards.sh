#!/bin/bash
# test_write_custody_guards.sh — the matrix for the three guards that watch WHAT gets written where.
#
#   guard_canon_write.sh          keeps the always-loaded layer true and small
#   guard_pm_flag_store.sh        keeps which-project-this-window-is-on from being rewritten by hand
#   guard_cross_project_write.sh  stops once when a write lands in a different project's files
#
# HALF THESE CASES ARE ALLOW-CASES, AND THAT IS THE POINT. Every one of these guards has a recorded
# history of firing on correct work, and each time the cost was the same: people stop trusting the
# stop and start routing around it. A guard that cannot prove it stays quiet during ordinary work is
# not finished. So the false-positive cases below are not padding — they are the regression tests for
# bugs that actually happened, and they are named after what went wrong.
#
# Nothing real is touched: HOME is redirected to a temp directory, so the arming store, the
# acknowledgement store and the notes root are all throwaway.
#
# Deny = exit 2. Allow = exit 0.
# Run: bash system/hooks/tests/test_write_custody_guards.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
CANON="$HOOKS/guard_canon_write.sh"
STORE="$HOOKS/guard_pm_flag_store.sh"
CROSS="$HOOKS/guard_cross_project_write.sh"
for h in "$CANON" "$STORE" "$CROSS"; do
  [ -f "$h" ] || { echo "CANNOT RUN: no hook at $h"; exit 1; }
done

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/custody.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
NOTES="$SANDBOX/notes"
mkdir -p "$NOTES/state/projects/alpha/canon" "$NOTES/state/projects/beta/canon" "$NOTES/state/briefs"

pass=0; fail=0

# label · hook · expected exit · payload on stdin · [extra env assignments...]
run() {
  local label="$1" hook="$2" exp="$3" payload="$4"; shift 4
  local got
  printf '%s' "$payload" | env HOME="$SANDBOX" "$@" bash "$hook" >/dev/null 2>&1
  got=$?
  if [ "$got" = "$exp" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL [$label]: expected exit $exp, got $got"; fi
}

# Build a Write payload with a file path and a body.
wpay() { python3 -c "
import json,sys
print(json.dumps({'tool_name':sys.argv[1],'tool_input':{'file_path':sys.argv[2],'content':sys.argv[3]}}))" "$1" "$2" "$3"; }
# An Edit payload — the guard reads new_string rather than content.
epay() { python3 -c "
import json,sys
print(json.dumps({'tool_name':'Edit','tool_input':{'file_path':sys.argv[1],'old_string':'x','new_string':sys.argv[2]}}))" "$1" "$2"; }
bpay() { python3 -c "
import json,sys
print(json.dumps({'tool_name':'Bash','tool_input':{'command':sys.argv[1]}}))" "$1"; }
# A payload for any tool that only carries a file path — used to prove the guards ignore reads.
rpay() { python3 -c "
import json,sys
print(json.dumps({'tool_name':sys.argv[1],'tool_input':{'file_path':sys.argv[2]}}))" "$1" "$2"; }

SMALL="- Sunset is computed before any hardware is chosen. Decided after the first prototype stalled."
BIG="$(python3 -c "print('x'*3201)")"
EXACT="$(python3 -c "print('x'*3200, end='')")"

echo "── guard_canon_write ─────────────────────────────────────────────────────"
run "ordinary file, not canon"        "$CANON" 0 "$(wpay Write "$NOTES/records/a.md" "$BIG")"
run "a canon line, no frontmatter"    "$CANON" 0 "$(wpay Write "$NOTES/state/projects/alpha/canon/current.md" "$SMALL")"
run "subject canon, small"            "$CANON" 0 "$(wpay Write "$NOTES/desks/lamps/canon/current.md" "$SMALL")"
run "root canon, small"               "$CANON" 0 "$(wpay Write "$NOTES/canon.md" "$SMALL")"
run "canon at exactly the rail"       "$CANON" 0 "$(wpay Write "$NOTES/canon.md" "$EXACT")"
run "canon one character over"        "$CANON" 2 "$(wpay Write "$NOTES/canon.md" "$BIG")"
run "subject canon, oversized"        "$CANON" 2 "$(wpay Write "$NOTES/desks/lamps/canon/current.md" "$BIG")"
run "canon with a shelf-life"         "$CANON" 2 "$(wpay Write "$NOTES/canon.md" "shelf-life: 30d")"
run "canon marked a snapshot"         "$CANON" 2 "$(wpay Write "$NOTES/canon.md" "tier: snapshot")"
run "an EDIT that adds an expiry"     "$CANON" 2 "$(epay "$NOTES/desks/lamps/canon/current.md" "expires: 2026-12-01")"
run "an EDIT of ordinary canon"       "$CANON" 0 "$(epay "$NOTES/desks/lamps/canon/current.md" "$SMALL")"
printf 'not json' | env HOME="$SANDBOX" bash "$CANON" >/dev/null 2>&1
[ $? = 2 ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "  FAIL [canon: unparseable]: expected deny"; }

echo "── guard_pm_flag_store ───────────────────────────────────────────────────"
PMDIR="\$HOME/.claude/run/pm"
run "Write into the store"            "$STORE" 2 "$(wpay Write "$SANDBOX/.claude/run/pm/pm-sess-x.flag" "slug=beta")"
run "Write anywhere else"             "$STORE" 0 "$(wpay Write "$NOTES/state/briefs/alpha.md" "hello")"
run "redirect into the store"         "$STORE" 2 "$(bpay "echo slug=beta > ~/.claude/run/pm/pm-sess-x.flag")"
run "rm aimed at the store"           "$STORE" 2 "$(bpay "rm -f ~/.claude/run/pm/pm-sess-x.flag")"
run "python writing to the store"     "$STORE" 2 "$(bpay "python3 -c \"open('/Users/x/.claude/run/pm/f','w').write('y')\"")"
run "cat the store (a read)"          "$STORE" 0 "$(bpay "cat ~/.claude/run/pm/pm-sess-x.flag")"
run "grep the store (a read)"         "$STORE" 0 "$(bpay "grep -l beta ~/.claude/run/pm/*.flag")"
run "python READING the store"        "$STORE" 0 "$(bpay "python3 -c \"print(open('/Users/x/.claude/run/pm/f').read())\"")"
# ⭐ THE REGRESSION THAT FIRED THREE TIMES IN ONE SESSION: a teardown aimed at /tmp, in a script that
# also happens to READ the store, was denied — twice while someone was verifying a documented step.
run "teardown beside a read"          "$STORE" 0 "$(bpay "grep pad_sha ~/.claude/run/pm/pm-sess-x.flag; rm -rf /tmp/checkin-fixture")"
# The sibling-folder bug: run/pm-ack is a DIFFERENT store and was being treated as the protected one.
run "a sibling store is not it"       "$STORE" 0 "$(bpay "rm -f ~/.claude/run/pm-ack/sess-x.ok")"
run "the sanctioned writer itself"    "$STORE" 0 "$(bpay "bash system/hooks/pm_flag.sh arm /tmp/b.md alpha root")"
printf 'not json' | env HOME="$SANDBOX" bash "$STORE" >/dev/null 2>&1
[ $? = 2 ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "  FAIL [store: unparseable]: expected deny"; }

echo "── guard_cross_project_write ─────────────────────────────────────────────"
A_BRIEF="$NOTES/state/projects/alpha/brief.md"
B_BRIEF="$NOTES/state/projects/beta/brief.md"
B_CANON="$NOTES/state/projects/beta/canon/current.md"
B_FLAT="$NOTES/state/briefs/beta.md"

# Nothing active yet: there is no contradiction to raise, so nothing is stopped.
run "no project active"               "$CROSS" 0 "$(wpay Write "$B_BRIEF" "x")" CLAUDE_CODE_SESSION_ID=none-yet

# Now put this window on alpha. Every case below shares that session id.
env HOME="$SANDBOX" CLAUDE_CODE_SESSION_ID=sess-alpha bash "$HOOKS/pm_flag.sh" arm "$A_BRIEF" alpha root >/dev/null 2>&1
run "alpha's own brief"               "$CROSS" 0 "$(wpay Write "$A_BRIEF" "x")"     CLAUDE_CODE_SESSION_ID=sess-alpha
run "alpha's own canon"               "$CROSS" 0 "$(wpay Write "$NOTES/state/projects/alpha/canon/current.md" "x")" CLAUDE_CODE_SESSION_ID=sess-alpha
run "an ordinary record"              "$CROSS" 0 "$(wpay Write "$NOTES/records/notes.md" "x")" CLAUDE_CODE_SESSION_ID=sess-alpha
run "beta's brief — STOP"             "$CROSS" 2 "$(wpay Write "$B_BRIEF" "x")"     CLAUDE_CODE_SESSION_ID=sess-alpha
run "beta's canon — STOP"             "$CROSS" 2 "$(wpay Write "$B_CANON" "x")"     CLAUDE_CODE_SESSION_ID=sess-alpha
run "beta's flat brief — STOP"        "$CROSS" 2 "$(wpay Write "$B_FLAT" "x")"      CLAUDE_CODE_SESSION_ID=sess-alpha
run "a Read is never its business"    "$CROSS" 0 "$(rpay Read "$B_BRIEF")" CLAUDE_CODE_SESSION_ID=sess-alpha

# One stop, not nagging: acknowledge the file and the same write goes through.
env HOME="$SANDBOX" CLAUDE_CODE_SESSION_ID=sess-alpha bash "$CROSS" ack "$B_BRIEF" >/dev/null 2>&1
run "after acknowledging it"          "$CROSS" 0 "$(wpay Write "$B_BRIEF" "x")"     CLAUDE_CODE_SESSION_ID=sess-alpha
run "a DIFFERENT file still stops"    "$CROSS" 2 "$(wpay Write "$B_CANON" "x")"     CLAUDE_CODE_SESSION_ID=sess-alpha
# The acknowledgement is per WINDOW. A SECOND window, also on alpha, has not seen it — the same
# write must still be stopped there. (A window with no project active is a separate case, covered
# above: it has nothing to contradict, so it is never stopped.)
env HOME="$SANDBOX" CLAUDE_CODE_SESSION_ID=sess-alpha-2 bash "$HOOKS/pm_flag.sh" arm "$A_BRIEF" alpha root >/dev/null 2>&1
run "a second window is not covered"  "$CROSS" 2 "$(wpay Write "$B_BRIEF" "x")"     CLAUDE_CODE_SESSION_ID=sess-alpha-2

printf 'not json' | env HOME="$SANDBOX" CLAUDE_CODE_SESSION_ID=sess-alpha bash "$CROSS" >/dev/null 2>&1
[ $? = 2 ] && pass=$((pass+1)) || { fail=$((fail+1)); echo "  FAIL [cross: unparseable]: expected deny"; }

echo ""
echo "RESULT: $pass passed, $fail failed."
[ "$fail" = 0 ] && echo "WRITE CUSTODY GREEN" || exit 1
