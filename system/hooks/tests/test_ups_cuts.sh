#!/bin/bash
# test_ups_cuts.sh: the injection cuts of sop-cleanup Phase 2 ruling 4 (12-token-audit). Sandbox HOME, no model calls.
#   4.1 project-manager line: once per arming, again after the reset hook, READER_NOTE still conditional
#   4.4 save-routing: imperative save only ("keep it simple" is silent)
#   4.5 NUMBERS: real money/arithmetic only (dates, versions, bare percentages are silent)
#   4.2 the delegation hook is no longer registered in the plugin wiring
# Run: bash system/hooks/tests/test_ups_cuts.sh   (exit 0 = all pass)
HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$HOOKS/../.." && pwd)"
PMF="$HOOKS/pm_flag.sh"; PMP="$HOOKS/pm_persist.sh"; RST="$HOOKS/pm_announce_reset.sh"
SRH="$HOOKS/save_routing_hint.sh"; ICM="$HOOKS/inject_compute_mechanically.sh"
SB="$(mktemp -d "${TMPDIR:-/tmp}/upscuts.XXXXXX")"; trap 'rm -rf "$SB"' EXIT
mkdir -p "$SB/hm" "$SB/notes" "$SB/proj"
pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
SESS="upscuts-$$"
jprompt() { python3 -c 'import json,sys; print(json.dumps({"prompt": sys.argv[1], "cwd": sys.argv[2]}))' "$1" "$SB/proj"; }
runh() { # runh <script> <prompt>
  jprompt "$2" | env HOME="$SB/hm" LIFEHACK_ROOT="$SB/notes" CLAUDE_CODE_SESSION_ID="$SESS" bash "$1" 2>/dev/null
}

echo "-- 4.1 project-manager line: once per arming"
DOC="$SB/proj/brief.md"; printf '# Brief\n\n## 1. CURRENT STATE\nthe state line\n' > "$DOC"
( cd "$SB/proj" && env HOME="$SB/hm" CLAUDE_CODE_SESSION_ID="$SESS" bash "$PMF" arm "$DOC" alpha root >/dev/null 2>&1 )
O1="$(runh "$PMP" "first message")"
O2="$(runh "$PMP" "second message")"
O3="$(runh "$PMP" "third message")"
case "$O1" in *"[project-manager ACTIVE]"*) ok;; *) bad "first message after arming announces the project" "got: $O1";; esac
[ -z "$O2" ] && ok || bad "second message is silent" "got: $O2"
[ -z "$O3" ] && ok || bad "third message is silent" "got: $O3"
jprompt "" | env HOME="$SB/hm" CLAUDE_CODE_SESSION_ID="$SESS" bash "$RST" >/dev/null 2>&1; RC=$?
[ "$RC" = 0 ] && ok || bad "reset hook exits 0" "rc=$RC"
O4="$(runh "$PMP" "after compaction")"
case "$O4" in *"[project-manager ACTIVE]"*) ok;; *) bad "after the reset hook the line fires again" "got: $O4";; esac
O5="$(runh "$PMP" "next")"
[ -z "$O5" ] && ok || bad "and is silent again afterwards" "got: $O5"
# armed MID-session (flag appears after earlier silent turns) still announces: covered above because the stamp is
# per doc path. Re-arm to a different doc must announce again.
# READER_NOTE: still conditional per message while the blind reader is unstamped
mkdir -p "$SB/hm/.claude/run/save-ledger"
printf '{"verdicts":{}}' > "$SB/hm/.claude/run/save-ledger/save-checkin-$SESS.json"
O6="$(runh "$PMP" "while reader unstamped")"
case "$O6" in *"BLIND READER"*) ok;; *) bad "READER_NOTE still prints while unstamped, without the long line" "got: $O6";; esac
case "$O6" in *"Source of truth"*) bad "READER_NOTE line must not repeat the full project line" "got: $O6";; *) ok;; esac

echo "-- 4.4 save-routing"
fires() { [ -n "$(runh "$SRH" "$1")" ]; }
for s in "keep it simple" "keep it short" "hold it 10 seconds" "I can't remember. This doesn't seem right" "note that the file moved" "Keep it scannable"; do
  fires "$s" && bad "silent on: $s" "it fired" || ok
done
for s in "save this" "Save it." "/save" "okay, save all this to my document" "remember this for later" "jot that down" "no canon. save" "write it to the scratch pad"; do
  fires "$s" && ok || bad "fires on: $s" "it was silent"
done

echo "-- 4.5 NUMBERS (arm 3 only)"
numfires() { [ -n "$(runh "$ICM" "$1")" ]; }
for s in "Today's Deliveries: 10/06/2026" "Version 2.524 Updated : 2026/09/22" "we are 50-56% full here" "50 messages" "tests pass 20/20" "it is 40% of session starts" "a 35×43 painting"; do
  numfires "$s" && bad "silent on: $s" "it fired" || ok
done
for s in "Yeah, let's do \$210" "what is 1,250 * 6?" "\$400 to \$450 is still pretty expensive" "calculate 15% of \$2,000"; do
  numfires "$s" && ok || bad "fires on: $s" "it was silent"
done
# arms 1 and 2 untouched: /calculate armed fires on any prompt
env HOME="$SB/hm" CLAUDE_CODE_SESSION_ID="$SESS" bash "$HOOKS/numbers_flag.sh" arm >/dev/null 2>&1
numfires "hello there" && ok || bad "numbers-mode armed still fires on any prompt" "silent"
env HOME="$SB/hm" CLAUDE_CODE_SESSION_ID="$SESS" bash "$HOOKS/numbers_flag.sh" clear >/dev/null 2>&1

echo "-- 4.2 delegation hook no longer shipped to students"
grep -q inject_delegation_standing "$REPO/hooks/hooks.json" && bad "plugin hooks.json" "still registers it" || ok
grep -q inject_delegation_standing "$REPO/.claude/settings.json" && bad "V2 settings.json" "still registers it" || ok
python3 -c "import json,sys; json.load(open(sys.argv[1])); json.load(open(sys.argv[2]))" "$REPO/hooks/hooks.json" "$REPO/.claude/settings.json" && ok || bad "wiring files parse" ""
grep -q pm_announce_reset "$REPO/hooks/hooks.json" && ok || bad "reset hook is wired (SessionStart compact|clear)" "missing"

echo; echo "passed $pass, failed $fail"; [ "$fail" = 0 ]
