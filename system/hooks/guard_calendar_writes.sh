#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: left to itself, a session writes calendar events to whatever calendar the account opens on —
#      which is the one your actual life is in. Agent-created entries then sit among real events,
#      and nobody notices until something important is buried. So this system writes to ONE calendar
#      that you made for it, and this hook is what makes that true rather than intended.
# GUARDS: ANY `gws calendar` command that is not a recognised READ, unless your agent calendar's id
#      is named explicitly in the command. DEFAULT-DENY — see the inversion note below, which is the
#      most important thing on this page.
# REDIRECT: name your agent calendar's id in the command. It is the `agent_calendar` line in
#      `<notes>/config/cal.md`; `python3 shared/cal_config.py` prints what is on file.
# SIGNPOST: which calendar is writable is YOUR setting, not this repo's — `<notes>/config/cal.md`,
#      documented in `INSTALL.md` under the Google sit-down. Change it there. Never loosen this
#      guard to match a command; change the config to match the calendar you meant.
# FAIL_POSTURE: closed — an unreadable payload denies, and an unknown verb denies.
# UPDATED: 2026-08-11 (ported; the one hardcoded calendar id became the reader's own config, and
#      the guard now refuses rather than passing when no calendar is configured at all)
#
# ⚠ INVERTED FROM AN ALLOWLIST-OF-ATTACKS TO DEFAULT-DENY on 2026-08-01, and this is the lesson to
#   keep. The previous version matched only `calendar events (insert|update|patch|quickAdd|import|
#   move)` and ended that test with `|| exit 0` — an allowlist of attack SPELLINGS that failed OPEN
#   on every spelling not in it. Fire-tested:
#       gws calendar events insert --calendar primary   -> rc=2  BLOCKED (correct)
#       gws calendar +insert       --calendar primary   -> rc=0  WALKED STRAIGHT THROUGH
#   `+insert` is not an exotic evasion — it is gws's OWN documented shorthand, listed in
#   `gws calendar --help`, and it is what a session reaches for. Also unlisted and therefore also
#   open at the time: `events delete`, `calendars clear` (which empties an entire calendar),
#   `acl insert`, `calendarList delete`, and any verb gws adds in future.
#   The fix inverts the test: recognise READS, and require the configured calendar for everything
#   else. An unknown verb is now UNKNOWN-therefore-DENIED.
# ─────────────────────────────────────────────────────────────────────────────
# PreToolUse hook (matcher: Bash).
#
# SELFTEST_DENY: {"tool_input":{"command":"gws calendar events insert --calendar primary --params '{}'"}}
# SELFTEST_DENY: {"tool_input":{"command":"gws calendar +insert --calendar primary --params '{}'"}}
# SELFTEST_DENY: {"tool_input":{"command":"gws calendar events delete --calendar primary --id abc"}}
# SELFTEST_DENY: {"tool_input":{"command":"gws calendar calendars clear --calendar primary"}}
# SELFTEST_ALLOW: {"tool_input":{"command":"gws calendar events list --params '{\"calendarId\":\"primary\"}'"}}
# SELFTEST_ALLOW: {"tool_input":{"command":"echo not a calendar command at all"}}

_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd -P)"
REPO="${_HOOKDIR%/system/hooks}"

deny() {
  printf 'BLOCKED (calendar guard): %s\n' "$1" >&2
  printf '%s\n' "WHY: this system writes to ONE calendar — the empty one you made for it — so that agent-created entries never end up among the real events in the calendar your life is in. This guard is DEFAULT-DENY, because the version before it listed the write verbs it knew about and let every other spelling through, including gws's own \`+insert\` shorthand." >&2
  printf '%s\n' "$2" >&2
  printf '%s\n' "RULE: which calendar is writable is your setting, at <notes>/config/cal.md (INSTALL.md → the Google sit-down). Change it there. Do not loosen this guard to fit a command; if a genuine READ was caught, add its verb to the read list in this file deliberately." >&2
  exit 2
}

INPUT=$(cat 2>/dev/null)
COMMAND=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try: print(json.load(sys.stdin).get('tool_input', {}).get('command', ''))
except Exception: print('__ERR__')" 2>/dev/null)

# An unreadable payload names no calendar. This hook sits in front of every Bash command, so
# denying here would wall the session off from the shell over a malformed message — the failure the
# sheet guards shipped with. Fail-CLOSED applies below, once a calendar command is actually in hand.
[ "$COMMAND" = "__ERR__" ] && exit 0
[ -n "$COMMAND" ] || exit 0

# Not a calendar command at all — pass through. This hook only speaks calendar.
printf '%s' "$COMMAND" | grep -qE "(^|[/[:space:]])gws([[:space:]]|$).*calendar" 2>/dev/null || exit 0

# Match the verb on the command HEAD only. Everything from the first flag or quote onward is
# PAYLOAD — a --params JSON body containing the words "events list" must never be able to talk this
# guard into treating a write as a read.
HEAD=$(printf '%s' "$COMMAND" | sed -e "s/[[:space:]]--.*//" -e "s/['\"].*//")

# Recognised READS — the only things that pass without the configured calendar. Derived from
# `gws calendar --help` (nouns: acl calendarList calendars channels colors events freebusy settings,
# plus the +insert/+agenda helpers) intersected with the verbs anything here actually uses.
# ADD TO THIS LIST DELIBERATELY; never widen it with a catch-all, never replace the default-deny.
READ_RE="calendar[[:space:]]+(events[[:space:]]+(list|get|instances)|calendarList[[:space:]]+(list|get)|calendars[[:space:]]+get|acl[[:space:]]+(list|get)|freebusy[[:space:]]+query|colors[[:space:]]+get|settings[[:space:]]+(list|get)|\+agenda|help)([[:space:]]|$)"
printf '%s' "$HEAD" | grep -qE "$READ_RE" 2>/dev/null && exit 0

# A bare `gws calendar` with no verb (--help is stripped into HEAD) is harmless — pass.
printf '%s' "$HEAD" | grep -qE "calendar[[:space:]]*$" 2>/dev/null && exit 0

# ── Everything left is a WRITE or a verb this guard does not know. Both need the calendar you
# configured, named explicitly anywhere in the FULL command.
CALID="$(python3 -c "
import sys
sys.path.insert(0, '$REPO/shared')
try:
    import cal_config
    print(cal_config.load().get('agent_calendar', ''))
except Exception:
    print('')" 2>/dev/null)"

if [ -z "$CALID" ]; then
  deny "a calendar write, and no writable calendar has been configured." \
"REDIRECT: nothing here knows which calendar is yours to write to, so there is no safe destination and this cannot be waved through. Make a NEW, EMPTY calendar in Google Calendar, then put its id in <notes>/config/cal.md:
    agent_calendar: <the id, from Settings → that calendar → \"Integrate calendar\">
Run \`python3 shared/cal_config.py\` to see what is currently on file."
fi

printf '%s' "$COMMAND" | grep -qF "$CALID" 2>/dev/null && exit 0

# DEFAULT DENY. Do NOT add an `|| exit 0` after this line — that is the bug the inversion fixed.
deny "this calendar command is write-shaped, or uses a verb this guard does not recognise, and it does not name your agent calendar." \
"REDIRECT: name your agent calendar's id in the command — it is on file as:
    $CALID
If this was a genuine READ that got caught, add its verb to the read list in this file, deliberately."
