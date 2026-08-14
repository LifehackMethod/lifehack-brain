#!/bin/bash
#
# ══════════════════════════════════════════════════════════════════════════════
# ⚠  SPEED BUMP, NOT A BOUNDARY.  Read this before you trust this file.
#
#  This guard inspects a command as TEXT. A shell has infinite equivalent ways to
#  spell the same command, so a text matcher is always one phrasing behind. Treat
#  what follows as a speed bump that raises the cost of a mistake — never as a wall
#  that makes one impossible.
#
#  MEASURED, 2026-08-14, in the system this came from. Four guards of this shape were
#  fire-tested and then attacked by two independent auditors charged to break them:
#    · the first found 20 bypasses in ~20 minutes; 11 of 13 headline claims reproduced
#    · after a rewrite, the second found 13 more, all reproduced
#    · after three rounds of hardening, 1 of 27 tested attack forms still passes
#  Every one of those holes was in a guard reading a command STRING. Every guard that
#  fired correctly was on a typed tool.
#
#  PRIOR ART, same conclusion: CVE-2025-66032 — eight independent bypasses of Claude
#  Code's own regex blocklist, plus an independently reproduced substitution bypass.
#
#  ⇒ IF YOU ARE ADDING A CONTROL THAT MUST NOT BE BYPASSED, DO NOT ADD IT HERE.
#    Put it on a typed tool, or make the dangerous act structurally impossible.
# ══════════════════════════════════════════════════════════════════════════════
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: your goals list is the one place in this system holding what YOU decided your life
#      is for. An agent that reorganises it, rewrites a goal, or deletes an item is not
#      making a recoverable mistake — Google Tasks keeps no version history, so a deleted
#      task is simply gone. Until this hook existed the read-only rule lived only in prose,
#      in cal-daily's own skill file, which said so plainly: "this one is a rule, not a
#      wall." A rule an agent can reason past is a wish. This is the wall.
# GUARDS: any `gws tasks` WRITE verb (insert/update/patch/delete/move/clear on tasks or
#      tasklists) aimed at the list on file as `goals_tasklist`. ONE carve-out: the day's
#      plan may be written as SUBTASKS under the single task on file as `daily_parent_task`
#      — insert/update/patch/move that names that task in a PARENT position. delete and
#      clear are NEVER permitted on the goals list, carve-out or not. Reads (list/get) on
#      any list, the goals list included, pass untouched.
# REDIRECT: write the day's plan as subtasks under `daily_parent_task`; read the goals list
#      with `gws tasks tasks list`; write any other task to a different list. Both ids are
#      lines in <notes>/config/cal.md — `python3 shared/cal_config.py` prints what is on file.
# SIGNPOST: which list is protected is YOUR setting, not this repo's — <notes>/config/cal.md,
#      documented in INSTALL.md under the Google sit-down. Change it there. Never loosen this
#      guard to fit a command; change the config to match the list you meant.
# FAIL_POSTURE: closed — a write whose target this guard cannot resolve is denied, and a
#      write with no goals list configured is denied. An unknown is never read as permission.
# UPDATED: 2026-08-14 (ported; the two hardcoded task ids became the reader's own config, the
#      carve-out now requires the parent id in a PARENT position rather than anywhere in the
#      command text, and an unconfigured install refuses rather than passing)
# ─────────────────────────────────────────────────────────────────────────────
# PreToolUse hook (matcher: Bash).

_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd -P)"
REPO="${_HOOKDIR%/system/hooks}"

deny() {
  printf 'BLOCKED (tasks guard): %s\n' "$1" >&2
  printf '%s\n' "WHY: the list on file as goals_tasklist holds what you decided your life is for, and it is yours to edit, not your agent's. Google Tasks keeps no version history, so a deleted or overwritten task is gone for good. The one sanctioned write is the day's plan, as subtasks under the single parent task on file as daily_parent_task." >&2
  printf '%s\n' "$2" >&2
  printf '%s\n' "RULE: which list is protected is your setting, at <notes>/config/cal.md (INSTALL.md -> the Google sit-down). Change it there. Do not loosen this guard to fit a command." >&2
  exit 2
}

INPUT=$(cat 2>/dev/null)
COMMAND=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try: print(json.load(sys.stdin).get('tool_input', {}).get('command', ''))
except Exception: print('__ERR__')" 2>/dev/null)

# An unreadable payload names no task list. This hook sits in front of every Bash command,
# so denying here would wall the session off from the shell over a malformed message.
# Fail-CLOSED applies below, once a tasks WRITE is actually in hand.
[ "$COMMAND" = "__ERR__" ] && exit 0
[ -n "$COMMAND" ] || exit 0

# The shell removes a backslash-newline before running, so the wrapped and the joined forms
# execute identically. Every match below is on text, so it must see the joined form.
COMMAND=$(printf '%s' "$COMMAND" | perl -0pe 's/\\\n/ /g' 2>/dev/null || printf '%s' "$COMMAND")

# ── IS THIS A TASKS COMMAND AT ALL? Two loose gates, deliberately not one tight one. ─────────
# ⚠ THE BINARY IS MATCHED AS A TOKEN ANYWHERE, NOT AS THE WORD DIRECTLY BEFORE `tasks`. Two earlier
# drafts of this line were both measurably blind, in opposite directions:
#   · `gws[[:space:]]*.*tasks` — in `gws tasks tasklists delete` the only space-delimited `tasks`
#     is the one right after `gws`, already consumed, so the whole command went unrecognised and
#     fell through to exit 0. That is the verb that destroys an entire list.
#   · `gws[[:space:]]+tasks` — correct for that case, and still blind to `V=gws; $V tasks tasks
#     delete`, where no literal `gws` sits next to the service word. Fire-tested 2026-08-14:
#     ALLOWED, rc 0. The same shape is a confirmed live hole in the sheet guards of BOTH repos.
# So: gate 1 asks whether a gws binary is NAMED anywhere (a bare token, or a path ending in it);
# gate 2 asks whether the tasks service is named. Both are loose on purpose — a mere mention costs
# nothing, because a command with no write verb and no goals id exits 0 a few lines below anyway.
printf '%s' "$COMMAND" | grep -qE "(^|[^A-Za-z0-9_.-])gws([^A-Za-z0-9_-]|$)|bin/gws" 2>/dev/null || exit 0
printf '%s' "$COMMAND" | grep -qE "(^|[[:space:]])tasks(lists)?([[:space:]]|$)" 2>/dev/null || exit 0

# ── THE SANCTIONED WRITE, WHICH IS ITSELF AN INDIRECTION ─────────────────────
# ⛔ READ THIS BEFORE TIGHTENING THE INDIRECTION CATCH BELOW. The one write this system is
# supposed to make — the day's plan, from cal-daily's Pass 5 — does NOT name either id literally.
# It resolves both through the config reader at call time:
#     --params '{"tasklist":"$(… cal_config.py --get goals_tasklist)",
#                "parent":"$(… cal_config.py --get daily_parent_task)"}'
# The first version of this guard denied exactly that command. Its own 35-case unit suite passed
# green throughout, because every case in it spelled the ids out — the suite tested the shape the
# author imagined, not the shape the shipped skill emits. Fire-tested against the real invocation
# string on 2026-08-14: DENIED. A guard that blocks the only sanctioned path is not strict, it is
# broken, and it would have broken cal-daily on a student's first morning.
#
# The resolution: this indirection is SELF-DESCRIBING. The command does not hide its target behind
# an opaque variable — it names, in plain text, the config key it is about to resolve. So the guard
# can read the intent without resolving anything. A substitution that names `daily_parent_task` in
# a PARENT position, on an add-or-amend verb, is the day's plan. Nothing else gets this door:
# delete and clear are not in the verb list, and a substitution naming any other key does not match.
if printf '%s' "$COMMAND" | grep -qE "tasks[[:space:]]+tasks[[:space:]]+(insert|update|patch|move)([[:space:]]|$)" 2>/dev/null; then
  if printf '%s' "$COMMAND" | grep -qE "\"parent\"[[:space:]]*:[[:space:]]*\"?\\\$\([^)]*--get[[:space:]]+daily_parent_task" 2>/dev/null \
     || printf '%s' "$COMMAND" | grep -qE "(^|[[:space:]])--parent[[:space:]=]+\"?\\\$\([^)]*--get[[:space:]]+daily_parent_task" 2>/dev/null; then
    exit 0   # the day's plan, hung from the parent it names by key — the one sanctioned write
  fi
fi

# ── THE INDIRECTION CATCH ─────────────────────────────────────────────────────
# Everything below matches LITERAL text. When the text is not literal — a variable, a
# substitution — every literal matcher misses. In the system this came from, this guard was
# the worst of four for exactly that reason: it identified the protected list by a literal
# id, so ANY indirection made the match fail and the command fell through to the "write to
# an allowed list" tail. Measured: 3 of 4 indirect forms were live bypasses. An indirection
# we cannot resolve is UNKNOWN, and UNKNOWN FAILS CLOSED.
LIB="$_HOOKDIR/lib/gws_guard.py"
if [ ! -r "$LIB" ]; then
  deny "this guard's shared command parser is missing, so it cannot tell what this command would do." \
"REDIRECT: restore system/hooks/lib/gws_guard.py — without it there is no safe verdict, so nothing is waved through."
fi
printf '%s' "$COMMAND" | python3 "$LIB" --service tasks \
  --destructive '' \
  --write-verbs insert,update,patch,delete,move,clear 2>/dev/null
if [ $? -eq 7 ]; then
  deny "this gws tasks command hides its operation or its target behind a shell variable or a command substitution, so this guard cannot tell which list it would write to." \
"REDIRECT: re-run the command with the operation and the task list written out literally, so the guard can see them."
fi

# Not a write verb — pass through. Reads (list/get) on ANY list, the goals list included,
# are always fine; observing is the whole point.
printf '%s' "$COMMAND" | grep -qE "tasks[[:space:]]+(tasks|tasklists)[[:space:]]+(insert|update|patch|delete|move|clear)([[:space:]]|$)" 2>/dev/null || exit 0

# ── A WRITE IS IN HAND. From here the posture is closed. ──────────────────────
GOALS="$(python3 -c "
import sys
sys.path.insert(0, '$REPO/shared')
try:
    import cal_config
    print(cal_config.load().get('goals_tasklist', ''))
except Exception:
    print('')" 2>/dev/null)"

if [ -z "$GOALS" ]; then
  deny "a Google Tasks write, and no goals list is on file — so this guard cannot tell whether this command is about to rewrite the list holding your goals." \
"REDIRECT: put your goals list's id in <notes>/config/cal.md so this guard knows what to protect:
    goals_tasklist:    <the id of the task list holding your goals>
    daily_parent_task: <the id of the one task a day's plan hangs from>
Run: python3 shared/cal_config.py   to see what is currently on file. If you do not keep goals
in Google Tasks, point goals_tasklist at the list you most want protected — there is no safe
way for this guard to guess, and guessing wrong is silent."
fi

# Not aimed at the goals list — pass through. Any other list is yours to write.
printf '%s' "$COMMAND" | grep -qF "$GOALS" 2>/dev/null || exit 0

# ── Aimed at the goals list. Only the day's-plan carve-out survives. ──────────
# delete and clear never pass, carve-out or not: they are the two that cannot be undone.
printf '%s' "$COMMAND" | grep -qE "tasks[[:space:]]+(tasks|tasklists)[[:space:]]+(insert|update|patch|move)([[:space:]]|$)" 2>/dev/null || \
  deny "a delete or clear aimed at your goals list." \
"REDIRECT: nothing here may delete or clear anything in the goals list — not even the day's plan, which may only ADD subtasks. Remove goals yourself, in Google Tasks."

PARENT="$(python3 -c "
import sys
sys.path.insert(0, '$REPO/shared')
try:
    import cal_config
    print(cal_config.load().get('daily_parent_task', ''))
except Exception:
    print('')" 2>/dev/null)"

if [ -z "$PARENT" ]; then
  deny "a write to your goals list, and no daily parent task is on file — so there is no sanctioned slot for it to go in." \
"REDIRECT: the only permitted write to the goals list is a subtask under one specific parent. Put its id in <notes>/config/cal.md:
    daily_parent_task: <the id of the one task a day's plan hangs from>"
fi

# The parent id must appear in a PARENT POSITION — a JSON parent field or a --parent flag —
# not merely somewhere in the command text. Matching it anywhere (which is what the original
# did) means any string carrying that id, a task title or a notes body included, unlocks a
# write to any goal in the list. Both spellings below are accepted; an unrecognised spelling
# denies loudly rather than passing quietly, which is the direction a mistake here should fail.
if printf '%s' "$COMMAND" | grep -qE "\"parent\"[[:space:]]*:[[:space:]]*\"?${PARENT}\"?" 2>/dev/null \
   || printf '%s' "$COMMAND" | grep -qE "(^|[[:space:]])--parent[[:space:]=]+\"?${PARENT}\"?([[:space:]]|\"|$)" 2>/dev/null; then
  exit 0   # the day's plan, hung from its parent — the one sanctioned write
fi

deny "a write to your goals list that does not hang from the day's parent task." \
"REDIRECT: the only permitted write here is a subtask of the parent on file as daily_parent_task:
    $PARENT
Name it as the parent — a \"parent\" field in the params body, or --parent $PARENT — so this
guard can see this is the day's plan and not an edit to one of your goals."
