#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: guard_pm_flag_store.sh denied READS of the project-arming store, not just writes.
#      Measured 2026-08-08: it fired 3x in one session on reads, including the one that
#      /checkin Step 1.8's GATE 2 explicitly instructs. That step was UNRUNNABLE AS WRITTEN.
#      W12.1 split the matcher into two tiers; this script is the proof it works BOTH ways.
# GUARDS: nothing. It is a TEST, not a hook. It never writes to the arming store.
# REDIRECT: if a case fails, fix system/hooks/guard_pm_flag_store.sh — never edit this file
#      to match the guard's current behaviour. The expectations here are the specification.
# SIGNPOST: system/hooks/guard_pm_flag_store.sh (the guard) · system/sops/hook-sop.md §4
#      ("a hook you haven't watched block/allow in a live attempt is not a control", and
#      Trap 2: "a command-string guard blocks its own documentation" — which is exactly why
#      these cases live in a FILE instead of an inline shell command; the guard denied the
#      inline version of this very test).
# UPDATED: 2026-08-13 (THE SUITE HAD NEVER RUN THE GUARD — see the block below)
# ─────────────────────────────────────────────────────────────────────────────
# Usage:  bash system/hooks/tests/verify-pm-guard.sh      (exit 0 = every case behaved)
#
# ⛔⛔ WHY THIS FILE NOW CHECKS THAT THE GUARD EXISTS BEFORE IT TESTS IT.
# Measured 2026-08-13: this suite reported "FAIL — 7 cases behaved wrong" and had been read as
# "the guard denies reads." It was not testing the guard at all. This script used to live at
# `system/tools/`, where `../..` correctly reached the repo root. The migration moved it one level
# deeper to `system/hooks/tests/` and did not update that path, so REPO resolved to `<root>/system`
# and GUARD pointed at `<root>/system/system/hooks/…`, which does not exist. `bash` on a missing
# file exits **127**, run() read any non-zero as DENY, and so EVERY case denied.
# ⭐ THE PART THAT MATTERS: the 8 cases that "PASSED" passed for the same wrong reason — 127 is not
# 0. A suite that cannot reach the thing it tests reports its DENY half GREEN. The red half is what
# got noticed; the green half was equally meaningless and would not have been.
# ⇒ Two fixes, and the second is the load-bearing one: the path is corrected, AND 127 is now mapped
# to NOT-RUN and aborts loudly instead of being absorbed as a real verdict. An unreachable subject
# is not a clean result — it is no result, and it must never be allowed to look like one.

# Resolved from this script, never a hardcoded home directory.
# tests -> hooks -> system -> repo root: THREE levels. Counted, not guessed.
REPO="$(cd "$(dirname "$0")/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/guard_pm_flag_store.sh"
STORE="$HOME/.claude/run/pm/pm-probe.flag"
FAILS=0

# ⛔ PRECONDITION — fail LOUD, never silently. Without this the whole suite is theatre.
if [ ! -f "$GUARD" ]; then
  echo "⛔ ABORT — the guard under test does not exist at:"
  echo "     $GUARD"
  echo "   Nothing was tested. This is NOT a pass and NOT a failure of the guard —"
  echo "   it is this script being unable to find its subject. Fix the path above."
  exit 2
fi

# Payload is generated with json.dumps, never echo — an echo'd \n becomes a real newline and
# the hook's json parse throws, so the test "passes" via fail-open instead of via validation
# (build-sop.md, 2026-06-19).
run() {  # $1 label · $2 expected ALLOW|DENY · $3 command string
  python3 -c "import json,sys; sys.stdout.write(json.dumps({'tool_name':'Bash','tool_input':{'command':sys.argv[1]}}))" "$3" \
    | bash "$GUARD" >/dev/null 2>&1
  local rc=$? got
  # ⛔ 127 is NOT-RUN, never DENY. The guard exits 0 (allow) or 2 (block); anything else means it
  # did not run — not found, not executable, killed. Absorbing that as a verdict is exactly how this
  # suite spent its life reporting a guard it never reached.
  if [ "$rc" != "0" ] && [ "$rc" != "2" ]; then
    printf "  [NOT-RUN] %-41s guard exited %s — no verdict, not a deny\n" "$1" "$rc"
    FAILS=$((FAILS + 1))
    return
  fi
  [ "$rc" = "0" ] && got=ALLOW || got=DENY
  if [ "$got" = "$2" ]; then
    printf "  [PASS] %-44s %s\n" "$1" "$got"
  else
    printf "  [FAIL] %-44s expected %s, got %s\n" "$1" "$2" "$got"
    FAILS=$((FAILS + 1))
  fi
}

echo "=== ALLOW — reads of the arming store (the W12.1 fix) ==="
run "Gate-2 style python read"      ALLOW "python3 -c \"print(open('$STORE').read())\""
run "python heredoc read"           ALLOW "python3 - <<'PY'
d = open('$STORE').read()
PY"
run "grep the store"                ALLOW "grep pad_sha_at_arm $STORE"
run "cat the store"                 ALLOW "cat $STORE"
run "ls the store dir"              ALLOW "ls -l \$HOME/.claude/run/pm/"

echo "=== DENY — writes must STILL be blocked (a guard not seen to deny is not a guard) ==="
run "python open(...,'w')"          DENY  "python3 -c \"open('$STORE','w').write('slug=evil')\""
run "python os.replace onto store"  DENY  "python3 -c \"import os; os.replace('/tmp/a','$STORE')\""
run "python Path().write_text"      DENY  "python3 -c \"from pathlib import Path; Path('$STORE').write_text('x')\""
run "shell redirect into store"     DENY  "echo slug=evil > $STORE"
run "rm the store"                  DENY  "rm $STORE"
run "sed -i the store"              DENY  "sed -i s/a/b/ $STORE"
run "tee into the store"            DENY  "echo x | tee $STORE"
run "mv onto the store"             DENY  "mv /tmp/a $STORE"

echo "=== ALLOW — unrelated work is untouched ==="
run "python writing somewhere else" ALLOW "python3 -c \"open('/tmp/z','w').write('hi')\""
run "sibling store run/pm-ack"      ALLOW "echo x > \$HOME/.claude/run/pm-ack/z"

echo
if [ "$FAILS" -eq 0 ]; then
  echo "PASS — reads allowed, writes denied, siblings untouched."
  exit 0
fi
echo "FAIL — $FAILS case(s) behaved wrong. Fix the GUARD, not this file."
exit 1
