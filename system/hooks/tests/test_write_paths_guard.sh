#!/bin/bash
# test_write_paths_guard.sh — the guards protecting themselves.
#
# ⭐ THE CASE THIS SUITE EXISTS FOR was measured on 2026-08-14: an Edit aimed at
# system/hooks/guard_calendar_writes.sh was allowed by all five of this repo's Write/Edit-matched
# hooks, rc 0 across the board — while guard_statusline_lock.sh stated in its own header, twice,
# that this exact case was "already backstopped at the Write/Edit layer." It was not. An agent
# could edit or delete any guard here, and the repo said it couldn't.
#
# ⚠ SCOPE. This guard is a deliberate SUBSET of the donor's. It protects hooks, the settings file
# and .git — and allows everything else, ON PURPOSE. The donor's general write-containment wall
# (deny every write outside a set of approved zones) is NOT ported, because on a student's machine
# it would refuse to write to their own Desktop. That is a product decision, not a porting one. The
# "allows what it does not protect" cases below are therefore ASSERTIONS OF INTENT, not oversights.
#
# Deny = exit 2. Allow = exit 0.
# Run: bash system/hooks/tests/test_write_paths_guard.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$HOOKS/../.." && pwd)"
GUARD="$HOOKS/guard_write_paths.sh"
[ -f "$GUARD" ] || { echo "CANNOT RUN: no hook at $GUARD"; exit 1; }

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

# run <label> <expected-rc> <path> [tool]
run() {
  local label="$1" exp="$2" path="$3" tool="${4:-Edit}" got
  python3 -c "
import json,sys
print(json.dumps({'tool_name':sys.argv[2],'tool_input':{'file_path':sys.argv[1]}}))" "$path" "$tool" 2>/dev/null \
    | env CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" >/dev/null 2>&1
  got=$?
  [ "$got" = "$exp" ] && ok || bad "$label" "expected exit $exp, got $got"
}

echo "── the guards themselves are not editable by the Edit/Write tools ───────"
run "Edit a guard"              2 "$REPO/system/hooks/guard_calendar_writes.sh"
run "Write a guard"             2 "$REPO/system/hooks/guard_calendar_writes.sh" Write
run "Edit THIS guard"           2 "$REPO/system/hooks/guard_write_paths.sh"
run "a brand-new hook file"     2 "$REPO/system/hooks/guard_invented.sh"
run "the shared parser lib"     2 "$REPO/system/hooks/lib/gws_guard.py"

echo "── settings decides WHICH hooks run, so it is protected too ─────────────"
run "Edit settings.json"        2 "$REPO/.claude/settings.json"
run "Edit settings.local.json"  2 "$REPO/.claude/settings.local.json"

echo "── git internals are not hand-editable ──────────────────────────────────"
run "Edit .git/config"          2 "$REPO/.git/config"
run "Edit a git hook"           2 "$REPO/.git/hooks/pre-commit"

echo "── ⭐ the same targets, spelled so a string match would miss them ────────"
# A guard that compares raw strings can be walked around by naming the same file differently.
# Every one of these resolves to a protected file.
run "via a .. traversal"        2 "$REPO/system/tools/../hooks/guard_egress.sh"
run "via a doubled slash"       2 "$REPO/system/hooks//guard_egress.sh"
run "via a . segment"           2 "$REPO/system/hooks/./guard_egress.sh"
run "relative to the repo"      2 "system/hooks/guard_egress.sh"
run "relative with a traversal" 2 "./system/tools/../hooks/guard_egress.sh"

echo "── ordinary work is untouched ───────────────────────────────────────────"
run "a skill file"              0 "$REPO/.claude/skills/planning-daily/SKILL.md"
run "a tool"                    0 "$REPO/system/tools/smoke-check.sh"
run "a test"                    0 "$REPO/system/hooks/tests/test_calendar_guard.sh"
run "the README"                0 "$REPO/README.md"
run "a hook test, new"          0 "$REPO/system/hooks/tests/test_new_thing.sh"

echo "── what this guard deliberately does NOT do (see the scope note) ────────"
# These are ASSERTIONS, not gaps. Changing them is the product decision named at the top.
run "a file on the Desktop"     0 "$HOME/Desktop/notes.md"
run "a file in /tmp"            0 "/tmp/scratch.txt"

echo "── malformed input fails CLOSED; an absent path is not ours to judge ────"
printf 'not json' | env CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" >/dev/null 2>&1
[ "$?" = 2 ] && ok || bad "unparseable payload" "a Write/Edit guard must deny when it cannot read the target"
python3 -c "import json;print(json.dumps({'tool_name':'Edit','tool_input':{}}))" \
  | env CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" >/dev/null 2>&1
[ "$?" = 0 ] && ok || bad "no path in payload" "a payload carrying no path names nothing to protect"

echo "── the deny a person reads tells them the way through ───────────────────"
MSG="$(python3 -c "
import json,sys; print(json.dumps({'tool_name':'Edit','tool_input':{'file_path':sys.argv[1]}}))" \
  "$REPO/system/hooks/guard_egress.sh" \
  | env CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" 2>&1 >/dev/null)"
printf '%s' "$MSG" | grep -q "chmod 644"  && ok || bad "deny gives the edit path"   "$MSG"
printf '%s' "$MSG" | grep -q "chmod 755"  && ok || bad "deny restores 755, not 444" "$MSG"
printf '%s' "$MSG" | grep -q "RULE:"      && ok || bad "deny carries its signpost"  "$MSG"

echo
if [ "$fail" = 0 ]; then echo "RESULT: $pass passed, 0 failed."; echo "WRITE-PATHS GUARD GREEN"; exit 0
else echo "RESULT: $pass passed, $fail failed."; exit 1; fi
