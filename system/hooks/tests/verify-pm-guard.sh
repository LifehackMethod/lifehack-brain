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
# UPDATED: 2026-08-08
# ─────────────────────────────────────────────────────────────────────────────
# Usage:  bash system/tools/verify-pm-guard.sh      (exit 0 = every case behaved)

# Resolved from this script, never a hardcoded home directory.
REPO="$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/guard_pm_flag_store.sh"
STORE="$HOME/.claude/run/pm/pm-probe.flag"
FAILS=0

# Payload is generated with json.dumps, never echo — an echo'd \n becomes a real newline and
# the hook's json parse throws, so the test "passes" via fail-open instead of via validation
# (build-sop.md, 2026-06-19).
run() {  # $1 label · $2 expected ALLOW|DENY · $3 command string
  python3 -c "import json,sys; sys.stdout.write(json.dumps({'tool_name':'Bash','tool_input':{'command':sys.argv[1]}}))" "$3" \
    | bash "$GUARD" >/dev/null 2>&1
  local rc=$? got
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
