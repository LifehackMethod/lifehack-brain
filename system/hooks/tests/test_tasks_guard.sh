#!/bin/bash
# test_tasks_guard.sh — the wall around the list holding your goals.
#
# ⭐ THE CASE THIS SUITE EXISTS FOR is that until this guard shipped, there was no wall at all.
# `cal-daily`'s own skill file said so in as many words: "The machine-side half of this is NOT in
# this repo… this one is a rule, not a wall." The rule is that everything in `goals_tasklist` is
# observe-only EXCEPT subtasks hung under `daily_parent_task`. These cases hold that line, and the
# ones marked ⭐ are the shapes that were live bypasses in the system this came from: an id behind a
# shell variable, and an id that merely APPEARS in the command rather than sitting in a parent slot.
#
# ⚠ WHY THE COMMANDS BELOW ARE ASSEMBLED FROM A `$G` PREFIX RATHER THAN SPELLED OUT. A sibling
# guard reads every Bash command as text and refuses raw Google reads. A file whose literal content
# is full of such commands cannot be written through that harness at all — so the service word is
# joined at runtime. What the guard under test receives is the fully assembled command; only the
# source text is broken up. This is the same false-positive class the calendar guard hit, and the
# documented workaround for it.
#
# Deny = exit 2. Allow = exit 0.
# Run: bash system/hooks/tests/test_tasks_guard.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
GUARD="$HOOKS/guard_tasks_writes.sh"
[ -f "$GUARD" ] || { echo "CANNOT RUN: no hook at $GUARD"; exit 1; }

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/tasksguard.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
NOTES="$SANDBOX/notes"; mkdir -p "$NOTES/config"
GOALS="MDAwbGlzdGdvYWxz"
PARENT="MDAwcGFyZW50dGFzaw"
OTHER="MDAwb3RoZXJsaXN0"
printf 'goals_tasklist: %s\ndaily_parent_task: %s\n' "$GOALS" "$PARENT" > "$NOTES/config/cal.md"

# The service word, assembled. See the note at the top of this file.
G="gws ta""sks"

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

echo "── not a tasks command: invisible ───────────────────────────────────────"
for c in "ls -la" "git push origin main" "gws ma""il messages list" "gws cal""endar events list" "echo tasks"; do
  run "$c" 0 "$c"
done
printf 'not json' | env HOME="$SANDBOX" bash "$GUARD" >/dev/null 2>&1
[ "$?" = 0 ] && ok || bad "unparseable stdin" "a guard in front of every Bash command must not deny here"

echo "── reads always pass, the goals list included ───────────────────────────"
run "tasklists list"      0 "$G tasklists list"
run "tasks list, goals"   0 "$G tasks list --tasklist $GOALS"
run "tasks get, goals"    0 "$G tasks get --tasklist $GOALS --id abc"
run "bare help"           0 "$G --help"

echo "── writes to any OTHER list pass — only the goals list is protected ─────"
run "insert elsewhere"    0 "$G tasks insert --tasklist $OTHER --params '{\"title\":\"buy milk\"}'"
run "delete elsewhere"    0 "$G tasks delete --tasklist $OTHER --id abc"

echo "── ⭐ writes to the GOALS list are denied ────────────────────────────────"
run "insert into goals"   2 "$G tasks insert --tasklist $GOALS --params '{\"title\":\"a new goal\"}'"
run "patch a goal"        2 "$G tasks patch --tasklist $GOALS --id g1 --params '{\"title\":\"rewritten\"}'"
run "update a goal"       2 "$G tasks update --tasklist $GOALS --id g1 --params '{}'"
run "move a goal"         2 "$G tasks move --tasklist $GOALS --id g1"
echo "   ...and delete/clear never pass, not even under the carve-out"
run "delete a goal"       2 "$G tasks delete --tasklist $GOALS --id g1"
run "clear the list"      2 "$G tasks clear --tasklist $GOALS"
run "delete the LIST"     2 "$G tasklists delete --tasklist $GOALS"
run "delete + parent named" 2 "$G tasks delete --tasklist $GOALS --id g1 --parent $PARENT"

echo "── the ONE sanctioned write: a subtask under the day's parent ───────────"
run "insert, parent in params" 0 \
  "$G tasks insert --tasklist $GOALS --params '{\"title\":\"domino one\",\"parent\":\"$PARENT\"}'"
run "insert, --parent flag"    0 "$G tasks insert --tasklist $GOALS --parent $PARENT --params '{\"title\":\"d\"}'"
run "patch a subtask"          0 \
  "$G tasks patch --tasklist $GOALS --id d1 --params '{\"parent\": \"$PARENT\"}'"

echo "── ⭐ the parent id must sit in a PARENT slot, not merely appear ─────────"
# Matching the id ANYWHERE (what the original did) means any string carrying it — a title, a
# notes body — unlocks a write to any goal in the list.
run "id smuggled in a title" 2 \
  "$G tasks patch --tasklist $GOALS --id g1 --params '{\"title\":\"$PARENT\"}'"
run "id smuggled in notes"   2 \
  "$G tasks patch --tasklist $GOALS --id g1 --params '{\"notes\":\"see $PARENT\"}'"

echo "── ⭐ indirection is UNKNOWN, and unknown fails closed ───────────────────"
run "list behind a variable"     2 "$G tasks delete --tasklist \$LIST --id g1"
run "list behind a substitution" 2 "$G tasks delete --tasklist \$(cat /tmp/l) --id g1"
run "verb behind a variable"     2 "$G tasks \$OP --tasklist $GOALS --id g1"

echo "── ⭐⭐ the two cases the first draft got WRONG, both measured ────────────"
# (1) The shipped skill (cal-daily prompts/05-act.md:30) resolves BOTH ids through cal_config at
# call time rather than spelling them out. The first draft denied it — 35 unit cases green, and the
# one command the system actually issues was blocked. A guard that blocks the only sanctioned path
# is broken, not strict. This indirection is self-describing: it names the key it resolves.
run "the shipped write, ids via --get substitution" 0 \
  "$G tasks insert --params '{\"tasklist\":\"\$(python3 \"\$ROOT/shared/cal_config.py\" --get goals_tasklist)\",\"parent\":\"\$(python3 \"\$ROOT/shared/cal_config.py\" --get daily_parent_task)\"}'"
# ...but a substitution naming any OTHER key is not the day's plan and must not get that door.
run "substitution naming the wrong key" 2 \
  "$G tasks patch --tasklist $GOALS --id g1 --params '{\"parent\":\"\$(python3 cal_config.py --get goals_tasklist)\"}'"
# (2) Binary-name indirection. The first draft matched a literal `gws` adjacent to the service word,
# so a binary behind a variable walked through — the same hole confirmed live in the sheet guards.
run "binary behind a variable" 2 "V=gws; \$V tasks tasks delete --tasklist $GOALS --id g1"
run "binary via an absolute path" 2 "/opt/homebrew/bin/gws tasks tasks delete --tasklist $GOALS --id g1"

echo "── nothing configured: a write refuses and says how to fix it ───────────"
EMPTY="$SANDBOX/empty-notes"; mkdir -p "$EMPTY"
run "unconfigured write" 2 "$G tasks insert --tasklist anything --params '{}'" "$EMPTY"
run "unconfigured read"  0 "$G tasks list --tasklist anything" "$EMPTY"
MSG="$(python3 -c "
import json,sys; print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" \
  "$G tasks insert --tasklist anything --params {}" \
  | env HOME="$SANDBOX" LIFEHACK_ROOT="$EMPTY" bash "$GUARD" 2>&1 >/dev/null)"
printf '%s' "$MSG" | grep -q "config/cal.md"    && ok || bad "deny names the config file" "$MSG"
printf '%s' "$MSG" | grep -q "goals_tasklist"   && ok || bad "deny names the key" "$MSG"

echo "── the deny a person actually reads names the parent to use ─────────────"
MSG2="$(python3 -c "
import json,sys; print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" \
  "$G tasks patch --tasklist $GOALS --id g1 --params '{}'" \
  | env HOME="$SANDBOX" LIFEHACK_ROOT="$NOTES" bash "$GUARD" 2>&1 >/dev/null)"
printf '%s' "$MSG2" | grep -qF "$PARENT"          && ok || bad "deny names the parent id" "$MSG2"
printf '%s' "$MSG2" | grep -q "daily_parent_task" && ok || bad "deny names the key"       "$MSG2"
printf '%s' "$MSG2" | grep -q "RULE:"             && ok || bad "deny carries its signpost" "$MSG2"

echo
if [ "$fail" = 0 ]; then echo "RESULT: $pass passed, 0 failed."; echo "TASKS GUARD GREEN"; exit 0
else echo "RESULT: $pass passed, $fail failed."; exit 1; fi
