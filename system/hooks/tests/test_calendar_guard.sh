#!/bin/bash
# test_calendar_guard.sh — the wall around which calendar gets written to.
#
# ⭐ THE CASE THIS SUITE EXISTS FOR is `gws calendar +insert`. The version this guard came from
# listed the write verbs it knew about (`insert|update|patch|quickAdd|import|move`) and ended with
# `|| exit 0` — so every spelling NOT on that list walked straight through to the person's real
# calendar. `+insert` is not an exotic evasion: it is gws's own documented shorthand, listed in
# `gws calendar --help`, and it is what a session reaches for. Also open at the time: `events
# delete`, `calendars clear` (which empties a whole calendar), and every verb gws has added since.
# The guard was inverted to recognise READS and deny everything else. These cases hold that line.
#
# Deny = exit 2. Allow = exit 0.
# Run: bash system/hooks/tests/test_calendar_guard.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
GUARD="$HOOKS/guard_calendar_writes.sh"
[ -f "$GUARD" ] || { echo "CANNOT RUN: no hook at $GUARD"; exit 1; }

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/calguard.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
NOTES="$SANDBOX/notes"; mkdir -p "$NOTES/config"
MINE="abc123def456@group.calendar.google.com"
printf 'agent_calendar: %s\npersonal_calendar: someone@example.com\n' "$MINE" > "$NOTES/config/cal.md"

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

# run <label> <expected-rc> <command> [notes-root-override]
run() {
  local label="$1" exp="$2" cmd="$3" root="${4-$NOTES}" got
  python3 -c "
import json,sys
print(json.dumps({'tool_name':'Bash','tool_input':{'command':sys.argv[1]}}))" "$cmd" 2>/dev/null \
    | env HOME="$SANDBOX" LIFEHACK_ROOT="$root" bash "$GUARD" >/dev/null 2>&1
  got=$?
  [ "$got" = "$exp" ] && ok || bad "$label" "expected exit $exp, got $got"
}

echo "── not a calendar command: invisible ────────────────────────────────────"
for c in "ls -la" "git push origin main" "gws gmail messages list" "gws sheets spreadsheets get" "echo calendar"; do
  run "$c" 0 "$c"
done
run "unreadable payload" 0 "" ""
printf 'not json' | env HOME="$SANDBOX" bash "$GUARD" >/dev/null 2>&1
[ "$?" = 0 ] && ok || bad "unparseable stdin" "a guard in front of every Bash command must not deny here"

echo "── reads always pass, including of the personal calendar ────────────────"
run "events list"        0 "gws calendar events list --params '{\"calendarId\":\"primary\"}'"
run "events get"         0 "gws calendar events get --calendar primary --id abc"
run "events instances"   0 "gws calendar events instances --calendar primary --id abc"
run "calendarList list"  0 "gws calendar calendarList list"
run "freebusy query"     0 "gws calendar freebusy query --params '{}'"
run "+agenda"            0 "gws calendar +agenda"
run "bare gws calendar"  0 "gws calendar --help"

echo "── ⭐ writes to the wrong calendar — every spelling, not just the known ──"
run "events insert"      2 "gws calendar events insert --calendar primary --params '{}'"
run "+insert (the bypass)" 2 "gws calendar +insert --calendar primary --params '{}'"
run "events delete"      2 "gws calendar events delete --calendar primary --id abc"
run "calendars clear"    2 "gws calendar calendars clear --calendar primary"
run "events update"      2 "gws calendar events update --calendar primary --id abc"
run "events patch"       2 "gws calendar events patch --calendar primary --id abc"
run "acl insert"         2 "gws calendar acl insert --calendar primary"
run "quickAdd"           2 "gws calendar events quickAdd --calendar primary --text 'lunch'"
echo "   ...and a verb that does not exist yet is UNKNOWN, therefore denied"
run "a verb from the future" 2 "gws calendar events teleport --calendar primary"
run "a nonsense verb"        2 "gws calendar wibble --calendar primary"

echo "── writes naming YOUR calendar pass ─────────────────────────────────────"
run "insert, named"      0 "gws calendar events insert --params '{\"calendarId\":\"$MINE\"}'"
run "+insert, named"     0 "gws calendar +insert --params '{\"calendarId\":\"$MINE\"}'"
run "delete, named"      0 "gws calendar events delete --calendar $MINE --id abc"

echo "── the payload must not be able to talk the guard into a read ───────────"
# A --params body containing the words "events list" is DATA. The verb is matched on the command
# head only, so this stays a write.
run "a write whose body says 'events list'" 2 \
  "gws calendar events insert --calendar primary --params '{\"summary\":\"gws calendar events list\"}'"

echo "── no calendar configured: refuse, and say how to fix it ────────────────"
# There is no safe default. `primary` is the one calendar a stranger's agent must never touch, so
# an unconfigured install cannot be allowed to write anywhere at all.
EMPTY="$SANDBOX/empty-notes"; mkdir -p "$EMPTY"
run "unconfigured write"  2 "gws calendar events insert --calendar primary --params '{}'" "$EMPTY"
run "unconfigured read"   0 "gws calendar events list --params '{}'" "$EMPTY"
MSG="$(python3 -c "
import json; print(json.dumps({'tool_input':{'command':'gws calendar events insert --calendar primary'}}))" \
  | env HOME="$SANDBOX" LIFEHACK_ROOT="$EMPTY" bash "$GUARD" 2>&1 >/dev/null)"
printf '%s' "$MSG" | grep -q "config/cal.md" && ok || bad "deny names the config file" "$MSG"
printf '%s' "$MSG" | grep -q "agent_calendar" && ok || bad "deny names the key" "$MSG"
printf '%s' "$MSG" | grep -qi "new, empty" && ok || bad "deny says to make a NEW calendar" "$MSG"

echo
if [ "$fail" = 0 ]; then echo "RESULT: $pass passed, 0 failed."; echo "CALENDAR GUARD GREEN"; exit 0
else echo "RESULT: $pass passed, $fail failed."; exit 1; fi
