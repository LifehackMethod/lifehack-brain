#!/bin/bash
# test_sheet_guards.sh — the two guards on a spreadsheet used as a database.
#
#   guard_sheet_writes.sh           read the sheet's own instructions before writing to it;
#                                   destructive and structural operations need saying so out loud
#   guard_sheet_formula_writes.sh   an owner-credentialled write must not land on a formula
#
# ⭐ THE FIRST BLOCK BELOW IS THE REASON THIS FILE EXISTS. Both guards sit in front of EVERY Bash
# command in every session. The versions this repo inherited parsed their input with `jq` and ended
# each parse in `|| deny`, so on a machine without jq they exited 2 — a hard block — on `ls -la`, with
# a refusal message about destructive spreadsheet operations. Measured 2026-08-11: with jq removed
# from PATH and nothing else changed, both guards blocked a plain directory listing. jq only reached
# macOS's own /usr/bin recently; it is absent on older macOS, on a plain Linux box, and in Git Bash on
# Windows, which is this project's documented Windows floor. The cases below run each guard with a
# PATH that has no jq on it, and they are the ones to keep if you keep nothing else.
#
# Deny = exit 2. Allow = exit 0.
# Run: bash system/hooks/tests/test_sheet_guards.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
WRITES="$HOOKS/guard_sheet_writes.sh"
FORMULA="$HOOKS/guard_sheet_formula_writes.sh"
for h in "$WRITES" "$FORMULA"; do
  [ -f "$h" ] || { echo "CANNOT RUN: no hook at $h"; exit 1; }
done

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/sheetguard.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
MARKDIR="$SANDBOX/marks"

# Two PATHs identical to the real one, each missing exactly ONE tool. Emptying the whole PATH
# instead would test nothing but the absence of `cat`, which is not a situation anybody is in.
shim_without() {   # shim_without <dir> <tool-to-omit>
  mkdir -p "$1"
  for d in /bin /usr/bin /usr/local/bin /opt/homebrew/bin; do
    [ -d "$d" ] || continue
    for f in "$d"/*; do
      b="$(basename "$f")"
      [ "$b" = "$2" ] && continue
      [ -e "$1/$b" ] || ln -s "$f" "$1/$b" 2>/dev/null
    done
  done
  if PATH="$1" command -v "$2" >/dev/null 2>&1; then
    echo "CANNOT RUN: could not build a PATH without $2"; exit 1
  fi
}
NOJQ="$SANDBOX/nojq";   shim_without "$NOJQ" jq
NOGWS="$SANDBOX/nogws"; shim_without "$NOGWS" gws

# A spreadsheet id has to be at least 40 characters for the guards to see it.
SID="1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789AbCdEf"

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

# run <label> <expected-rc> <hook> <command> [extra env...]
run() {
  local label="$1" exp="$2" hook="$3" cmd="$4"; shift 4
  local got
  python3 -c "
import json,sys
print(json.dumps({'tool_name':'Bash','tool_input':{'command':sys.argv[1]}}))" "$cmd" 2>/dev/null \
    | env HOME="$SANDBOX" SHEET_LLM_MARKDIR="$MARKDIR" "$@" bash "$hook" >/dev/null 2>&1
  got=$?
  [ "$got" = "$exp" ] && ok || bad "$label" "expected exit $exp, got $got"
}

echo "── ⭐ WITH NO jq ON PATH: ordinary commands must be untouched ────────────"
for c in "ls -la" "git status" "python3 -c 'print(1)'" "echo hello" "cd /tmp && pwd"; do
  run "no-jq: $c" 0 "$WRITES"  "$c" PATH="$NOJQ"
  run "no-jq: $c" 0 "$FORMULA" "$c" PATH="$NOJQ"
done
echo "   ...and the guards still GUARD without jq — they must not fail open either"
run "no-jq: blind write still blocked" 2 "$WRITES" \
  "gws sheets spreadsheets values update --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!A2\"}'" PATH="$NOJQ"
run "no-jq: destructive still blocked" 2 "$WRITES" \
  "gws sheets spreadsheets values clear --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!A:Z\"}'" PATH="$NOJQ"

echo "── an unreadable payload does not wall off the shell ────────────────────"
# This is the same failure by a second route: a guard in front of every Bash command that denies on a
# parse error takes the whole session down with it. It names no sheet, so there is nothing to protect.
printf 'not json at all' | env HOME="$SANDBOX" bash "$WRITES"  >/dev/null 2>&1; [ "$?" = 0 ] && ok || bad "writes: unparseable" "expected allow"
printf 'not json at all' | env HOME="$SANDBOX" bash "$FORMULA" >/dev/null 2>&1; [ "$?" = 0 ] && ok || bad "formula: unparseable" "expected allow"
printf '' | env HOME="$SANDBOX" bash "$WRITES" >/dev/null 2>&1; [ "$?" = 0 ] && ok || bad "writes: empty stdin" "expected allow"

echo "── ordinary work is untouched — the half that decides if this survives ──"
for c in "git push origin main" "ls -la" "gws gmail messages list --maxResults 5" "gws calendar events list" "python3 script.py" "grep -rn sheets ."; do
  run "$c" 0 "$WRITES" "$c"
  run "$c" 0 "$FORMULA" "$c"
done
echo "   including a command that merely MENTIONS the word sheets"
run "a message about sheets" 0 "$WRITES" "echo 'remember to update the sheets later'"
run "a path containing gws" 0 "$WRITES" "cat /tmp/mygws/sheets-notes.txt"

echo "── guard_sheet_writes: reads always pass, and a guide read earns the mark ─"
run "reading anything"        0 "$WRITES" "gws sheets spreadsheets values get --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!A1:Z1\"}'"
echo "   a write BEFORE the guide has been read is refused"
run "blind write"             2 "$WRITES" "gws sheets spreadsheets values update --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!A2\"}'"
run "blind append"            2 "$WRITES" "gws sheets spreadsheets values append --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!A:C\"}'"
echo "   read the guide, and the same write goes through"
run "read the guide"          0 "$WRITES" "gws sheets spreadsheets values get --params '{\"spreadsheetId\":\"$SID\",\"range\":\"_LLM_GUIDE!A:Z\"}'"
run "append after the guide"  0 "$WRITES" "gws sheets spreadsheets values append --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!A:C\"}'"
echo "   ...but the mark is PER SHEET — reading one guide does not unlock another"
OTHER="1ZzYyXxWwVvUuTtSsRrQqPpOoNnMmLlKkJjIiHhGg"
run "a different sheet"       2 "$WRITES" "gws sheets spreadsheets values update --params '{\"spreadsheetId\":\"$OTHER\",\"range\":\"Data!A2\"}'"

echo "   and reading the guide never unlocks a DESTRUCTIVE op by itself"
run "clear"                   2 "$WRITES" "gws sheets spreadsheets values clear --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!A:Z\"}'"
run "batchClear"              2 "$WRITES" "gws sheets spreadsheets values batchClear --params '{\"spreadsheetId\":\"$SID\"}'"
run "a whole-column update"   2 "$WRITES" "gws sheets spreadsheets values update --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!A:Z\"}'"
run "structural batchUpdate"  2 "$WRITES" "gws sheets spreadsheets batchUpdate --params '{\"spreadsheetId\":\"$SID\"}'"
echo "   the confirmation marker is the only way past, and it must be the NEW name"
run "with the confirm marker" 0 "$WRITES" "LIFEHACK_SHEET_CONFIRM=1 gws sheets spreadsheets values clear --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!A:Z\"}'"
# The donor's marker was LIFEHACK_SHEET_CONFIRM. If both were honoured, a stale command copied from
# old notes would silently keep its bypass and nobody would learn the name had changed.
run "the retired marker"      2 "$WRITES" "LIFEHACK_SHEET_CONFIRM=1 gws sheets spreadsheets values clear --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!A:Z\"}'"
echo "   creating a NEW sheet has no guide to read and nothing to destroy"
run "create"                  0 "$WRITES" "gws sheets spreadsheets create --params '{\"title\":\"new\"}'"

echo "── guard_sheet_formula_writes: appends pass, unverifiable writes do not ──"
run "an append"               0 "$FORMULA" "gws sheets spreadsheets values append --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!A:C\"}'"
run "a read"                  0 "$FORMULA" "gws sheets spreadsheets values get --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!A1\"}'"
run "the confirm marker"      0 "$FORMULA" "LIFEHACK_SHEET_CONFIRM=1 gws sheets spreadsheets values update --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!B2\"}'"
echo "   an update it cannot check is refused, not waved through — fail CLOSED"
# With gws absent from PATH there is no way to read back what the write would land on. A guard that
# allows an unverifiable write is not a guard; it is a comment.
run "no gws to check with"    2 "$FORMULA" "gws sheets spreadsheets values update --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!B2\"}'" PATH="$NOGWS"
run "no range in the command" 2 "$FORMULA" "gws sheets spreadsheets values update --params '{\"spreadsheetId\":\"$SID\"}'"
run "no sheet id"             2 "$FORMULA" "gws sheets spreadsheets values update --params '{\"range\":\"Data!B2\"}'"

echo "── the deny TEXT, not just the exit code ────────────────────────────────"
MSG="$(python3 -c "
import json; print(json.dumps({'tool_input':{'command':'gws sheets spreadsheets values update --params \'{\"spreadsheetId\":\"$SID\",\"range\":\"Data!A2\"}\''}}))" \
  | env HOME="$SANDBOX" SHEET_LLM_MARKDIR="$SANDBOX/empty-marks" bash "$WRITES" 2>&1 >/dev/null)"
printf '%s' "$MSG" | grep -q "_LLM_GUIDE" && ok || bad "deny names the tab to read" "$MSG"
printf '%s' "$MSG" | grep -q "LIFEHACK_SHEET_CONFIRM" && ok || bad "deny names the current marker" "$MSG"
printf '%s' "$MSG" | grep -q "google-sheet-sop.md" && ok || bad "deny names the rule" "$MSG"
printf '%s' "$MSG" | grep -qv "LIFEHACK_SHEET_CONFIRM" && ok || bad "deny still names the retired marker" "$MSG"

echo
if [ "$fail" = 0 ]; then echo "RESULT: $pass passed, 0 failed."; echo "SHEET GUARDS GREEN"; exit 0
else echo "RESULT: $pass passed, $fail failed."; exit 1; fi
