#!/bin/bash
# test_heredoc_quiet_guards.sh -- heredoc-quiet-fix (2026-11-02). A python heredoc that only edits a notes file must be
# SILENT for every gws-family guard, even when its prose mentions gws and holds an apostrophe; a heredoc that really
# calls gws must still be judged. Live incident: guard_tasks_writes refused `cd <notes> && python3 - <<'EOF' ...` (a
# plan edit) as "could not be parsed" -- shlex choked on an apostrophe in the body. Measured: it did so before D-F11
# too (d00f672), with gws_exec_heredoc on or off.
# Every guard is exercised through its registered .sh entry point (hook SOP section 4, trap 1). Strings only.
# Run: bash system/hooks/tests/test_heredoc_quiet_guards.sh   (exit 0 = all pass)
HERE="$(cd "$(dirname "$0")" && pwd)"; HOOKS="$(cd "$HERE/.." && pwd)"
FIX="$HERE/fixtures/d-f11-exact-command.txt"
GUARDS="guard_tasks_writes guard_gmail_destructive guard_gmail_send guard_calendar_writes guard_sheet_writes
        guard_sheet_formula_writes guard_gws_logout guard_drive_destructive guard_cloud_destructive"
for g in $GUARDS; do [ -f "$HOOKS/$g.sh" ] || { echo "CANNOT RUN: $g.sh"; exit 1; }; done
. "$HERE/pin_roundb_off.sh"
# the shipped values of every switch these guards read
export ROUNDB_GWS_EXEC_HEREDOC=on ROUNDB_FC_DRIVE_BULK_DELETE=on ROUNDB_FC_SHEET_FILE_DELETE=on \
       ROUNDB_FC_CLOUD_DESTRUCTIVE_ASK=on ROUNDB_FC_ASK_NOT_TOKEN=on
S="$(mktemp -d "${TMPDIR:-/tmp}/hdq.XXXXXX")"; trap 'rm -rf "$S"' EXIT  # guaranteed cleanup: leaked test temp dirs filled a disk, 2026-11-01
mkdir -p "$S/home" "$S/bin"
printf '%s\n' '#!/bin/bash' 'exit 1' > "$S/bin/gws"; chmod +x "$S/bin/gws"
export GWS_BIN="$S/bin/gws" SHEET_LLM_MARKDIR="$S/marks"
# A configured notes root, so guard_tasks_writes has a protected list and is LIVE through its entry point
# (with no list on file it has nothing to protect and passes everything, which would make this test blind).
mkdir -p "$S/notes/config"
printf '%s\n' 'goals_tasklist: goalsListX' 'daily_parent_task: parentY' 'agent_calendar: pondCalendarX' > "$S/notes/config/cal.md"
export LIFEHACK_ROOT="$S/notes"
P=0; F=0
ok() { P=$((P+1)); }
bad() { F=$((F+1)); echo "FAIL: $1"; }
bashjson() { T="$1" python3 -c 'import os,json; print(json.dumps({"tool_name":"Bash","tool_input":{"command":os.environ["T"]},"cwd":"/tmp","session_id":"hdq"}))'; }
# run <guard> <command> -> RC, OUT, ERR
run() { HOME="$S/home" bash "$HOOKS/$1.sh" <<<"$(bashjson "$2")" >"$S/out" 2>"$S/err"; RC=$?; }
silent_all() {   # silent_all <label> <command>: every guard exits 0 with no ask
  for g in $GUARDS; do
    run "$g" "$2"
    if [ $RC -eq 0 ] && ! grep -q '"ask"' "$S/out"; then ok; else bad "$1 :: $g (rc=$RC $(head -c 160 "$S/err")$(head -c 160 "$S/out"))"; fi
  done
}

P1="cd ~/notes && python3 - <<'EOF'"
PLAN_EDIT="$P1"$'\np = "plans/v2.plan.md"\nt = open(p).read()\nt = t.replace("- [ ] step 4", "- [x] step 4")\nopen(p, "w").write(t)\nEOF'
PLAN_EDIT_PROSE="$P1"$'\np = "plans/v2.plan.md"\nt = open(p).read()\nt += "\\n- Enver\'s ruling: the gws guards read executed heredocs; gws drive files update with trashed asks.\\n"\nopen(p, "w").write(t)\nEOF'
PLAN_EDIT_TRIPLE="$P1"$'\np = "plans/v2.plan.md"\nt = open(p).read()\nt += """\n- it\'s landed: gws gmail users messages send stays blocked, gws tasks lists are guarded\n"""\nopen(p, "w").write(t)\nEOF'
# The shapes that really broke shlex: an apostrophe OUTSIDE any double-quoted string (a python comment, a
# '''-quoted block, an escaped \' in a '...' string), in a body whose prose names gws.
PLAN_EDIT_COMMENT="$P1"$'\n# don\'t touch step 5 -- the gws tasks list is the person\'s own\np = "plans/v2.plan.md"\nopen(p, "a").write("- noted\\n")\nEOF'
PLAN_EDIT_TRIPLE_SQ="$P1"$'\np = "plans/v2.plan.md"\nt = open(p).read()\nt += \'\'\'\n- Enver\'s ruling: gws drive files update with trashed asks first\n\'\'\'\nopen(p, "w").write(t)\nEOF'
PLAN_EDIT_ESC="$P1"$'\nopen("plans/v2.plan.md", "a").write(\'- it\\\'s done: gws guards read heredocs\\n\')\nEOF'
JSON_SUBPROC="$P1"$'\nimport json, subprocess\nr = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)\nprint(json.dumps({"changed": r.stdout.splitlines()}, indent=2))\nopen("state/status.json", "w").write(json.dumps({"ok": True}))\nEOF'
# (prose naming BOTH gws and the calendar service word is deliberately caught by guard_calendar_writes' loose
# text gate -- see that file's header; it predates D-F11 and does not use the shared parser -- so it is not used here)
UNQ_PLAN="cd ~/notes && python3 - <<EOF"$'\nopen("plans/v2.plan.md", "a").write("it\'s noted: the gws tasks guard is fine\\n")\nEOF'

echo "-- 1. ALLOW first: notes-editing python heredocs are silent for all 9 gws-family guards"
silent_all "plan edit (open/read/replace/write)"          "$PLAN_EDIT"
silent_all "plan edit, prose names gws + apostrophe"      "$PLAN_EDIT_PROSE"
silent_all "plan edit, triple-quoted prose, it's + gws"   "$PLAN_EDIT_TRIPLE"
silent_all "plan edit, comment with don't + gws"         "$PLAN_EDIT_COMMENT"
silent_all "plan edit, '''-block with Enver's + gws"      "$PLAN_EDIT_TRIPLE_SQ"
silent_all "plan edit, escaped \\' + gws"                 "$PLAN_EDIT_ESC"
silent_all "json.dumps + subprocess, no gws"              "$JSON_SUBPROC"
silent_all "unquoted heredoc, prose names gws + it's"     "$UNQ_PLAN"

echo "-- 2. still caught"
run guard_drive_destructive "$(cat "$FIX")"
if [ $RC -eq 0 ] && grep -q '"permissionDecision": "ask"' "$S/out" && grep -q "more than one Drive file" "$S/out"; then ok; else bad "D-F11 exact no longer ASKS (rc=$RC $(head -c 200 "$S/out"))"; fi
REAL_GMAIL="$P1"$'\nimport subprocess\nsubprocess.run(["gws","gmail","users","threads","trash","--params","{\\"id\\":\\"t1\\"}"])\nEOF'
run guard_gmail_destructive "$REAL_GMAIL"
[ $RC -eq 2 ] && ok || bad "a real gws gmail trash in a python heredoc is no longer blocked (rc=$RC)"
REAL_RCLONE="$P1"$'\nimport subprocess\nfor r in remotes:\n    subprocess.run(["rclone","purge",r])\nEOF'
run guard_cloud_destructive "$REAL_RCLONE"
grep -q '"permissionDecision": "ask"' "$S/out" && ok || bad "rclone purge in a python heredoc no longer asks ($(head -c 200 "$S/out"))"
# tasks: the wrapper takes the protected list from the person's config, so the decision engine is called with it set.
REAL_TASKS="$P1"$'\nimport subprocess\nsubprocess.run(["gws","tasks","tasks","delete","--params","{\\"tasklist\\":\\"goalsListX\\",\\"task\\":\\"t1\\"}"])\n# Enver\'s note\nEOF'
printf '%s' "$REAL_TASKS" | TASKS_GUARD_GOALS=goalsListX TASKS_GUARD_PARENT=parentY python3 "$HOOKS/lib/tasks_guard.py" >/dev/null 2>"$S/err"; RC=$?
[ $RC -eq 2 ] && ! grep -q "could not be parsed" "$S/err" && ok || bad "tasks: a real goals-list delete in a heredoc must block on its merits (rc=$RC $(head -c 160 "$S/err"))"
printf '%s' "$PLAN_EDIT_PROSE" | TASKS_GUARD_GOALS=goalsListX TASKS_GUARD_PARENT=parentY python3 "$HOOKS/lib/tasks_guard.py" >/dev/null 2>"$S/err"; RC=$?
[ $RC -eq 0 ] && ok || bad "tasks engine with a goals list set still refuses the plan edit (rc=$RC $(head -c 160 "$S/err"))"
# a heredoc a SHELL runs is shell text and is still read by the tasks guard
SHELL_HD=$'bash <<\'EOF\'\ngws tasks tasks delete --params \'{"tasklist":"goalsListX","task":"t1"}\'\nEOF'
printf '%s' "$SHELL_HD" | TASKS_GUARD_GOALS=goalsListX TASKS_GUARD_PARENT=parentY python3 "$HOOKS/lib/tasks_guard.py" >/dev/null 2>&1; RC=$?
[ $RC -eq 2 ] && ok || bad "tasks: a goals-list delete inside bash <<'EOF' is no longer blocked (rc=$RC)"

echo
echo "heredoc quiet (9 gws-family guards): $P passed, $F failed"
[ "$F" -eq 0 ]
