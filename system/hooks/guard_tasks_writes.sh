#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: your goals list is the one place in this system holding what YOU decided your life is for.
#      An agent that reorganises it, rewrites a goal, or deletes an item is not making a recoverable
#      mistake — Google Tasks keeps no version history, so a deleted task is simply gone. Until this
#      hook existed the read-only rule lived only in prose, in planning-daily's own skill file, which
#      said so plainly: "this one is a rule, not a wall." A rule an agent can reason past is a wish.
# GUARDS: any `gws tasks` command that touches the list on file as `goals_tasklist` and is not a
#      recognised read. ONE carve-out: the day's plan, as subtasks under `daily_parent_task`.
#      delete and clear NEVER pass there. Reads pass on any list; writes to other lists pass.
# REDIRECT: write the day's plan as subtasks under `daily_parent_task`; read the goals list with a
#      tasks list or get; write anything else to a different list. Both ids live in
#      <notes>/config/cal.md — `python3 shared/cal_config.py` prints what is on file.
# SIGNPOST: which list is protected is YOUR setting, not this repo's — <notes>/config/cal.md,
#      documented in INSTALL.md under the Google sit-down. Change it there, never here.
# FAIL_POSTURE: closed — an unresolvable target, an unreadable verb, or an unparseable command is
#      refused. An unknown is never read as permission.
# UPDATED: 2026-08-14 (the decision moved OUT of this file into a real parser — see below)
# ─────────────────────────────────────────────────────────────────────────────
# PreToolUse hook (matcher: Bash). This file is now a THIN WRAPPER. It reads the payload, loads the
# two ids from the reader's own config, and hands the command to `lib/tasks_guard.py`, which decides.
#
# ⚠⚠ WHY THE DECISION IS NOT IN THIS FILE ANY MORE — the most useful thing on this page.
# This guard used to match the command as TEXT. Three independent auditors, each charged to REFUTE
# it, found SEVENTEEN working bypasses across three passes. Not one needed anything exotic: a
# semicolon, a newline, two adjacent quotes, `xargs`, a duplicate JSON key, the word `@default`.
# Each round was patched, and the next round broke it somewhere new — and the patch for round two
# BROKE THE LEGITIMATE PATH, refusing a day's plan titled "Q3 R&D review" because a text matcher
# cannot tell an `&` inside a quoted string from a shell operator. It ended up simultaneously too
# weak and too strict, which is the signature of the wrong instrument rather than a bad rule.
#
# A shell command is a LANGUAGE — infinite spellings of the same act — so a matcher is always one
# spelling behind. The parser tokenizes with `shlex` (so quoting is understood), splits real
# statements, and reads JSON bodies with `json.loads` (so a duplicate key resolves to the same value
# the API will receive). It also refuses `@default` and an omitted list, because Google resolves
# both to a default that may BE the protected list and nothing here can know without asking.
#
# ⇒ THE GENERAL RULE THIS PAID FOR THREE TIMES: if a control must not be bypassed, do not express it
#   as a Bash-string match. Parse it, put it on a typed tool, or make the act structurally
#   impossible. This is still only a speed bump — it does not execute the shell, so text assembled
#   at run time is opaque to it and is refused rather than understood.

_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd -P)"
REPO="${_HOOKDIR%/system/hooks}"
GUARD_PY="$_HOOKDIR/lib/tasks_guard.py"

INPUT=$(cat 2>/dev/null)
COMMAND=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try: sys.stdout.write(json.load(sys.stdin).get('tool_input', {}).get('command', ''))
except Exception: sys.stdout.write('__ERR__')" 2>/dev/null)

# An unreadable payload names no task list. This hook sits in front of EVERY Bash command, so
# denying here would wall the session off from the shell over one malformed message. Fail-closed
# applies below, once a command aimed at the goals list is actually in hand.
[ "$COMMAND" = "__ERR__" ] && exit 0
[ -n "$COMMAND" ] || exit 0

# Cheap pre-filter: if the line names no gws binary at all, there is nothing here to judge and no
# reason to start a python process on every shell command the session runs.
printf '%s' "$COMMAND" | grep -qE "(^|[^A-Za-z0-9_.-])gws([^A-Za-z0-9_-]|$)|bin/gws" 2>/dev/null || exit 0

if [ ! -r "$GUARD_PY" ]; then
  printf 'BLOCKED (tasks guard): the parser this guard depends on is missing.\n' >&2
  printf 'WHY: without system/hooks/lib/tasks_guard.py there is no safe verdict, so nothing is waved through.\n' >&2
  printf 'REDIRECT: restore that file. RULE: system/hook-contract.md.\n' >&2
  exit 2
fi

IDS=$(python3 -c "
import sys
sys.path.insert(0, '$REPO/shared')
try:
    import cal_config
    c = cal_config.load()
    sys.stdout.write('%s\t%s' % (c.get('goals_tasklist',''), c.get('daily_parent_task','')))
except Exception:
    sys.stdout.write('\t')" 2>/dev/null)
GOALS="${IDS%%	*}"
PARENT="${IDS##*	}"

printf '%s' "$COMMAND" | env TASKS_GUARD_GOALS="$GOALS" TASKS_GUARD_PARENT="$PARENT" \
  python3 "$GUARD_PY"
exit $?
