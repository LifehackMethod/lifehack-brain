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
#  MEASURED ON THIS FILE, 2026-08-14. The first version of this guard passed its own
#  39-case suite and 13 adversarial cases. An independent agent, charged to REFUTE it
#  and to default to BYPASSABLE on thin evidence, then broke its central promise
#  three separate ways in one pass — using a semicolon, adjacent quotes, and xargs.
#  Nothing exotic: no eval, no unicode, no ${var@P}. All nine of its cases were
#  reproduced before a line was changed, and all nine are now in the fire-test.
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
# GUARDS: any `gws tasks` command that touches the list on file as `goals_tasklist` and is
#      not a recognised READ. ONE carve-out: the day's plan may be written as SUBTASKS under
#      the task on file as `daily_parent_task` — a single-statement insert/update/patch/move
#      naming that task in a PARENT position. delete and clear are NEVER permitted on the
#      goals list, carve-out or not. Reads (list/get) on any list pass untouched, and writes
#      to any other list pass untouched.
# REDIRECT: write the day's plan as subtasks under `daily_parent_task`; read the goals list
#      with a tasks list/get; write any other task to a different list. Both ids are lines in
#      <notes>/config/cal.md — `python3 shared/cal_config.py` prints what is on file.
# SIGNPOST: which list is protected is YOUR setting, not this repo's — <notes>/config/cal.md,
#      documented in INSTALL.md under the Google sit-down. Change it there. Never loosen this
#      guard to fit a command; change the config to match the list you meant.
# FAIL_POSTURE: closed — DEFAULT-DENY on anything aimed at the goals list that is not a
#      recognised read or the one carve-out. An unknown verb, an unresolvable target, or a
#      multi-statement command is denied, never waved through.
# UPDATED: 2026-08-14 (ported, then INVERTED to default-deny after an adversarial pass)
# ─────────────────────────────────────────────────────────────────────────────
# PreToolUse hook (matcher: Bash).
#
# ⚠⚠ INVERTED FROM AN ALLOWLIST-OF-WRITE-VERBS TO DEFAULT-DENY, 2026-08-14. This is the whole
# lesson of the file, and this repo had already learned it once — `guard_calendar_writes.sh`
# carries the same warning after the same mistake, and its header was sitting three files away
# while this one was written the wrong way round.
#
# The first version listed the verbs it considered writes (insert/update/patch/delete/move/clear)
# and ended that test with `|| exit 0`. That is an allowlist of attack SPELLINGS, and it fails OPEN
# on every spelling not in it. Measured:
#     printf 'delete' | xargs -I{} gws tasks tasks {} --params '{"tasklist":"<goals>"...}'
#         -> rc 0, ALLOWED. The literal text at the verb position is `{}`, so no write was
#            recognised at all and the command never reached a single protection below.
# Two more, same pass, same file:
#     · the carve-out matched its two patterns anywhere in the WHOLE command and then exited 0
#       for the WHOLE command — so `echo <decoy> ; gws tasks tasks delete ...` was allowed, as was
#       the same decoy hidden in a trailing `#` comment. It sat BEFORE every other check, so
#       tripping it disabled all of them at once.
#     · `grep -qF "$GOALS"` needs the id contiguous, and bash concatenates adjacent quoted
#       strings, so `'MDAwbGlzdG''dvYWxz'` is the real id at runtime and invisible to the match.
#
# The shape below fixes the CLASS, not the three instances: recognise READS, decide the TARGET on
# a quote-normalised copy of the command, and deny everything else aimed at the goals list.

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

# An unreadable payload names no task list. This hook sits in front of every Bash command, so
# denying here would wall the session off from the shell over a malformed message. Fail-CLOSED
# applies below, once a command aimed at the goals list is actually in hand.
[ "$COMMAND" = "__ERR__" ] && exit 0
[ -n "$COMMAND" ] || exit 0

# The shell removes a backslash-newline before running, so the wrapped and joined forms execute
# identically. Every match below is on text, so it must see the joined form.
COMMAND=$(printf '%s' "$COMMAND" | perl -0pe 's/\\\n/ /g' 2>/dev/null || printf '%s' "$COMMAND")

# ── IS THIS A TASKS COMMAND AT ALL? Two loose gates, deliberately not one tight one. ─────────
# ⚠ THE BINARY IS MATCHED AS A TOKEN ANYWHERE, NOT AS THE WORD DIRECTLY BEFORE `tasks`. Two
# earlier drafts were each measurably blind, in opposite directions:
#   · `gws[[:space:]]*.*tasks` — in `gws tasks tasklists delete` the only space-delimited `tasks`
#     is the one right after `gws`, already consumed, so the command went unrecognised entirely
#     and fell through to exit 0. That is the verb that destroys an entire list.
#   · `gws[[:space:]]+tasks` — correct for that, still blind to `V=gws; $V tasks tasks delete`,
#     where no literal `gws` sits beside the service word. Fire-tested: ALLOWED, rc 0. The same
#     shape is a confirmed live hole in the sheet guards of BOTH repos.
# Both gates are loose on purpose. A mere mention costs nothing: a command that touches no
# protected list exits 0 a few lines below anyway.
printf '%s' "$COMMAND" | grep -qE "(^|[^A-Za-z0-9_.-])gws([^A-Za-z0-9_-]|$)|bin/gws" 2>/dev/null || exit 0
printf '%s' "$COMMAND" | grep -qE "(^|[[:space:]])tasks(lists)?([[:space:]]|$)" 2>/dev/null || exit 0

# ── THE NORMALISED HAYSTACK ───────────────────────────────────────────────────────────────────
# Quotes removed, because bash CONCATENATES adjacent quoted strings and a literal match does not.
# `'MDAwbGlzdG''dvYWxz'` is one id to the shell and two fragments to grep -F; stripping the quote
# characters puts the two back together, which is what the shell would have done. This copy is used
# ONLY to decide what the command touches — never to decide what it does.
HAY=$(printf '%s' "$COMMAND" | tr -d "\"'")

# Does this command carry more than one statement? If so, no single verb can be attributed to the
# target, and a decoy in one statement must never license an operation in another — which is
# precisely how the first version was broken. Aimed at the goals list, that is UNKNOWN, and unknown
# is denied. A `#` comment counts: a decoy hidden after one was a working bypass.
MULTI=0
printf '%s' "$COMMAND" | grep -qE '[;&|]|#' 2>/dev/null && MULTI=1
# ⛔ A NEWLINE IS A STATEMENT SEPARATOR AND grep CANNOT SEE ONE. grep works a line at a time, so the
# test above is blind to the most ordinary separator there is, and every check below that greps the
# command is likewise per-line: `grep -q` succeeds if ANY line matches. Together that meant one
# innocuous read line anywhere in a multi-line command handed exit 0 to every other line in it,
# including `tasklists delete`. That is the decoy bug the semicolon fix closed, inverted to `\n`.
# Found by the SECOND adversarial pass, after the first pass's three holes were closed. Counted with
# wc -l because printf adds no trailing newline, so any count above zero is an embedded one.
[ "$(printf '%s' "$COMMAND" | wc -l | tr -d ' ')" != "0" ] && MULTI=1

# ── RECOGNISED READS PASS, ALWAYS ─────────────────────────────────────────────────────────────
# Matched on the command HEAD — everything from the first flag or quote onward is PAYLOAD, and a
# --params body containing the words "tasks list" must never talk this guard into reading a write
# as a read. A read is only trusted when it stands alone; a read chained to something else is not
# a read, it is one statement of several.
HEAD=$(printf '%s' "$COMMAND" | sed -e "s/[[:space:]]--.*//" -e "s/['\"].*//")
if [ "$MULTI" = 0 ]; then
  printf '%s' "$HEAD" | grep -qE "tasks[[:space:]]+(tasks|tasklists)[[:space:]]+(list|get)([[:space:]]|$)" 2>/dev/null && exit 0
  printf '%s' "$HEAD" | grep -qE "tasks[[:space:]]*(--help)?[[:space:]]*$" 2>/dev/null && exit 0
fi

# ── EVERYTHING LEFT IS A WRITE OR A VERB THIS GUARD DOES NOT KNOW. ────────────────────────────
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

# Does it touch the goals list? TWO spellings count, and missing the second one was a real hole:
# the id written out, OR a substitution that names the config key holding it. A delete whose target
# reads `$(cal_config.py --get goals_tasklist)` carries no literal id at all.
TOUCHES_GOALS=0
printf '%s' "$HAY" | grep -qF "$GOALS" 2>/dev/null && TOUCHES_GOALS=1
printf '%s' "$HAY" | grep -qE "\-\-get[[:space:]]+goals_tasklist" 2>/dev/null && TOUCHES_GOALS=1

# ── AIMED AT SOME OTHER LIST — probably yours to write. But "we did not see the goals id" and
# "we could not see the target at all" are different answers, and only the first is an allow.
# ⚠ THIS CHECK MUST SIT HERE, AFTER the goals test, not before it. The shipped day's-plan write
# resolves BOTH ids through a substitution, so an indirection catch placed earlier denies the one
# command this system is supposed to make — measured, and it was the first version's worst defect.
# By this line a self-describing substitution has already been recognised and handled above; what
# is left is genuinely opaque.
if [ "$TOUCHES_GOALS" = 0 ]; then
  LIB="$_HOOKDIR/lib/gws_guard.py"
  if [ ! -r "$LIB" ]; then
    deny "this guard's shared command parser is missing, so it cannot tell what this command would do." \
"REDIRECT: restore system/hooks/lib/gws_guard.py — without it there is no safe verdict, so nothing is waved through."
  fi
  printf '%s' "$COMMAND" | python3 "$LIB" --service tasks \
    --destructive '' \
    --write-verbs insert,update,patch,delete,move,clear 2>/dev/null
  if [ $? -eq 7 ]; then
    deny "a Google Tasks write whose target is hidden behind a shell variable or a command substitution, so this guard cannot tell which list it would change." \
"REDIRECT: write the task list out literally so the guard can see it — or, if this is the day's plan, name the parent with a \"parent\" field so it is recognisable as the one sanctioned write. An unknown target is refused rather than assumed safe: the list it might be is the one with no undo."
  fi
  exit 0
fi

# ── AIMED AT THE GOALS LIST. From here, only the day's-plan carve-out survives. ───────────────
if [ "$MULTI" = 1 ]; then
  deny "a command aimed at your goals list that carries more than one statement, so this guard cannot tell which part does what." \
"REDIRECT: run the goals-list operation on its own, as a single command with nothing chained before or after it. A separator or a comment in the same line was a working way to smuggle a delete past this guard, so it is refused rather than parsed."
fi

# The verb must be POSITIVELY one of the four that may add or amend a subtask. Anything else —
# delete, clear, a verb supplied by xargs, a verb this guard has never heard of — lands on the
# deny at the bottom. This is the inversion: the guard no longer lists what it forbids.
if printf '%s' "$HEAD" | grep -qE "tasks[[:space:]]+tasks[[:space:]]+(insert|update|patch|move)([[:space:]]|$)" 2>/dev/null; then
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

  # The parent must sit in a PARENT POSITION — a "parent" field or a --parent flag — not merely
  # appear somewhere in the text. Matching it anywhere means any string carrying that id, a task
  # title or a notes body included, unlocks a write to any goal in the list.
  # Two spellings of the id are accepted, because the shipped skill uses the second: the literal
  # id, or a substitution that NAMES the config key. That indirection is self-describing — it says
  # in plain text which key it resolves — so it can be read without being resolved. A substitution
  # naming any other key does not match.
  # ⛔ THE KEY'S QUOTES ARE REQUIRED, and leaving them optional was a live bypass. The first version
  # accepted `"?parent"?[[:space:]]*:` — which matches the bare text `parent:` anywhere, including
  # inside an unrelated field. Measured: `--json '{"notes":"parent:<id>"}'` on an `update` aimed at a
  # real goal was ALLOWED, rc 0, as a single statement with no separator trick at all. A decorative
  # sentence in a notes body is not a parent slot. Requiring `"parent"` as a properly closed JSON key
  # rejects it, while the shipped command — `"parent":"$(… --get daily_parent_task)"` — still matches.
  if printf '%s' "$COMMAND" | grep -qE "\"parent\"[[:space:]]*:[[:space:]]*\"(${PARENT}|\\\$\([^)]*--get[[:space:]]+daily_parent_task[^)]*\))\"" 2>/dev/null \
     || printf '%s' "$COMMAND" | grep -qE "(^|[[:space:]])--parent[[:space:]=]+\"?(${PARENT}|\\\$\([^)]*--get[[:space:]]+daily_parent_task[^)]*\))\"?([[:space:]]|$)" 2>/dev/null; then
    exit 0   # the day's plan, hung from its parent — the one sanctioned write
  fi

  deny "a write to your goals list that does not hang from the day's parent task." \
"REDIRECT: the only permitted write here is a subtask of the parent on file as daily_parent_task:
    $PARENT
Name it as the parent — a \"parent\" field in the params body, or --parent $PARENT — so this
guard can see this is the day's plan and not an edit to one of your goals."
fi

# DEFAULT DENY. Do NOT add an `|| exit 0` after this line — that is the bug the inversion fixed.
deny "an operation aimed at your goals list that is not a recognised read and not the day's plan." \
"REDIRECT: reads (a tasks list or get) always pass. The only write that passes is a subtask under
the task on file as daily_parent_task. Nothing may delete or clear anything in this list, including
the day's plan, which may only ADD subtasks — remove goals yourself, in Google Tasks.
If a genuine READ was caught here, add its verb to the read list in this file, deliberately."
