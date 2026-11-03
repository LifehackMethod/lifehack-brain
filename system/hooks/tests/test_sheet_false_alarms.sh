#!/bin/bash
# test_sheet_false_alarms.sh -- two false alarms found 2026-11-02 (plan fix 23(c)), both directions.
#   A. guard_sheet_writes.sh refused a local sed + grep because the words appeared in the command text.
#   B. inject_sop_before_build.sh put the Google Sheet SOP in front of messages not about building a Sheet.
# Every guard runs through its registered .sh entry point (hook SOP section 4, trap 1). Strings only: gws here is a
# stub that records any call into $S/gws-called, and the test fails if it ever runs.
# SHEET_FA_HOOKS points the file at another checkout's hooks, to show the failures on the old code.
# Run: bash system/hooks/tests/test_sheet_false_alarms.sh   (exit 0 = all pass)
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/pin_roundb_off.sh"
HOOKS="${SHEET_FA_HOOKS:-$(cd "$HERE/.." && pwd)}"
WRITES="$HOOKS/guard_sheet_writes.sh"; FORMULA="$HOOKS/guard_sheet_formula_writes.sh"; SOP="$HOOKS/inject_sop_before_build.sh"
for h in "$WRITES" "$FORMULA" "$SOP"; do [ -f "$h" ] || { echo "CANNOT RUN: no hook at $h"; exit 1; }; done
S="$(mktemp -d "${TMPDIR:-/tmp}/sheetfa.XXXXXX")"; trap 'rm -rf "$S"' EXIT  # guaranteed cleanup: leaked test temp dirs filled a disk, 2026-11-01
mkdir -p "$S/bin" "$S/home" "$S/marks"
printf '%s\n' '#!/bin/bash' "echo \"\$*\" >> \"$S/gws-called\"" 'exit 1' > "$S/bin/gws"; chmod +x "$S/bin/gws"
export PATH="$S/bin:$PATH" HOME="$S/home" SHEET_LLM_MARKDIR="$S/marks" LHB_JOURNAL_DISABLE=1
P=0; F=0
ok() { P=$((P+1)); }
bad() { F=$((F+1)); echo "  FAIL: $1"; }
bashjson() { T="$1" python3 -c 'import os,json; print(json.dumps({"tool_name":"Bash","tool_input":{"command":os.environ["T"]}}))'; }
# quiet <label> <command>: BOTH sheet guards say nothing at all
quiet() {
  local h rc
  for h in "$WRITES" "$FORMULA"; do
    bash "$h" <<<"$(bashjson "$2")" >"$S/out" 2>"$S/err"; rc=$?
    if [ $rc -eq 0 ] && [ ! -s "$S/out" ] && [ ! -s "$S/err" ]; then ok; else bad "$1 :: $(basename "$h") rc=$rc $(head -c 120 "$S/err")$(head -c 120 "$S/out")"; fi
  done
}
# guarded <label> <command>: guard_sheet_writes refuses with the guide message or a destructive/unknown one
guarded() {
  local rc
  bash "$WRITES" <<<"$(bashjson "$2")" >"$S/out" 2>"$S/err"; rc=$?
  if [ $rc -eq 2 ] && grep -q "BLOCKED (sheet guard)" "$S/err"; then ok; else bad "$1 :: no longer guarded, rc=$rc $(head -c 160 "$S/out")"; fi
}
SID="1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789AbCdEf"
UPD="gws sheets spreadsheets values update --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!A2\"}'"
APP="gws sheets spreadsheets values append --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!A:C\"}'"
CLR="gws sheets spreadsheets values clear --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!A:Z\"}'"
BAT="gws sheets spreadsheets batchUpdate --params '{\"spreadsheetId\":\"$SID\"}'"
LST="['gws','sheets','spreadsheets','values','update','--params','{\"spreadsheetId\":\"$SID\"}']"

echo "-- A1. the exact commands that were refused stay silent"
quiet "the 2026-11-02 sed + grep" "sed -i '' -e 's|, home/gws.log, notes/ (the cwd)|, notes/ (the cwd)|' score.py && grep -n \"sheets\\|gws\\|SHEET\" score.py; sed -n '1,20p' test_kinds.py | grep -n sheets"
quiet "this fix's own deadend query" "cd /tmp/wt
python3 system/tools/deadend_check.py \"fix false alarms in guard_sheet_writes and sheet SOP prompt hook: match real gws sheets write commands not words in sed/grep patterns\"
echo ----; grep -n -i \"sheet\" system/register/toolbox.md | head -30
echo ----; grep -rIl -i \"sheet\" system/hooks hooks 2>/dev/null | head -60
echo ----; ls system/hooks | grep -i -E \"sheet|fine_china\"; find . -name \"test_*sheet*\" -not -path \"./archive/*\""

echo "-- A2. sed, grep, cat and friends over files that mention gws or sheets stay silent"
quiet "grep for the full write shape"   "grep -n 'gws sheets spreadsheets values update' system/gws-contract.md"
quiet "rg, pipe into head"              "rg 'gws sheets spreadsheets values clear' docs | head -5"
quiet "cat a path, then grep"           "cat home/gws.log sheets | grep -c update"
quiet "sed print of a guard's text"     "sed -n '1,20p' gws/sheets.txt"
quiet "sed replacing the write shape"   "sed -i '' 's/gws sheets spreadsheets values update/gws sheets spreadsheets values append/' notes.md"
quiet "head and tail of named files"    "head -3 gws.log; tail -3 sheets"
quiet "cd first, then grep"             "cd /tmp/gws && grep -rn sheets ."
quiet "grep inside a for loop"          "for f in a b; do grep -n 'gws sheets' \$f; done"
quiet "an echo of the words"            "echo 'gws sheets spreadsheets values clear is guarded'"
quiet "a commit message"                "git commit --only a.sh -m 'stop gws sheets spreadsheets values update firing on sed'"
quiet "a heredoc written to a file"     "cat > notes.md <<'EOF'
gws sheets spreadsheets values clear is refused
EOF"
quiet "a script given prose as its argument" "python3 tool.py \"why does gws sheets write fire on a grep\""
quiet "the sed, then a test run"        "sed -i '' 's|home/gws.log, ||' score.py && python3 test_kinds.py sheets"
quiet "if grep, then echo"              "if grep -q gws sheets; then echo found; fi"
quiet "another gws service beside a grep" "gws drive files list --params '{\"q\":\"x\"}' | grep -n sheets"

echo "-- A3. real writes are still refused, in every shape"
guarded "plain update"                  "$UPD"
guarded "plain append"                  "$APP"
guarded "plain clear"                   "$CLR"
guarded "plain batchUpdate"             "$BAT"
guarded "helper verb"                   "gws sheets +append --spreadsheet $SID --values a,b"
guarded "absolute binary"               "/opt/homebrew/bin/$UPD"
guarded "cd first"                      "cd /tmp/x && $UPD"
guarded "chained after a grep"          "grep -n sheets notes.md; $UPD"
guarded "chained before a grep"         "$UPD && grep -n gws out.log"
guarded "piped into a grep"             "$UPD | grep -n sheets"
guarded "assignment prefix"             "ID=$SID $UPD"
guarded "wrapper word"                  "command $UPD"
guarded "timeout wrapper"               "timeout 30 $UPD"
guarded "find -exec"                    "find . -name x -exec $UPD \\;"
guarded "xargs"                         "cat ids | xargs -I{} $UPD"
guarded "stdin words to xargs"          "echo spreadsheets values clear | xargs gws sheets"
guarded "ssh"                           "ssh box \"$UPD\""
guarded "subshell"                      "($UPD)"
guarded "for loop"                      "for i in a b; do $UPD; done"
guarded "bash -c"                       "bash -c \"$UPD\""
guarded "eval"                          "eval \"$UPD\""
guarded "command substitution"          "echo \$($UPD)"
guarded "substitution inside a grep"    "grep \$($UPD) notes.md"
guarded "binary in a variable"          "V=gws; \$V sheets spreadsheets values update --params '{\"spreadsheetId\":\"$SID\"}'"
guarded "whole command in a variable"   "C=\"$UPD\"; \$C"
guarded "words in a variable"           "A=\"gws sheets\"; \$A \"\$@\""
guarded "verb in a variable"            "OP=update; gws sheets spreadsheets values \$OP --params '{\"spreadsheetId\":\"$SID\"}'"
guarded "python -c list"                "python3 -c \"import subprocess; subprocess.run($LST)\""
guarded "python heredoc list"           "python3 - <<'E'
import subprocess
subprocess.run($LST)
E"
guarded "python heredoc after cd"       "cd /tmp/x && python3 -I - <<'E'
import subprocess
subprocess.run($LST)
E"
guarded "python heredoc, shell string"  "python3 - <<'E'
import subprocess
subprocess.run(\"$(printf '%s' "$UPD" | sed 's/"/\\"/g')\", shell=True)
E"
guarded "python body, words split up"   "python3 - <<'E'
import subprocess
parts = 'gws sheets'.split()
subprocess.run(parts + rest)
E"
guarded "node -e"                       "node -e \"require('child_process').execFileSync('gws',['sheets','spreadsheets','values','update'])\""
guarded "heredoc run by a shell"        "bash <<'E'
$UPD
E"
guarded "piped into a shell"            "echo \"$UPD\" | bash"
guarded "grep's output piped to a shell" "grep -h 'gws sheets spreadsheets values update' cmds.txt | sh"
guarded "written, then run"             "cat > run.sh <<'E'
$UPD
E
bash run.sh"
guarded "echoed to a file, then run"    "echo \"$UPD\" > run.sh; bash run.sh"
guarded "written by tee, then run"      "echo \"$UPD\" | tee run.sh; sh run.sh"
guarded "GNU sed e command"             "sed '1e gws sheets spreadsheets values clear' notes.md"
guarded "GNU sed s///e flag"            "sed 's|x|gws sheets spreadsheets values clear|e' notes.md"
guarded "rg --pre runs a program"       "rg --pre 'gws sheets spreadsheets values clear' x ."
guarded "awk system()"                  "awk 'BEGIN{system(\"gws sheets spreadsheets values clear\")}'"
guarded "git alias"                     "git -c alias.x='!gws sheets spreadsheets values clear' x"
guarded "git grep runs a pager"         "git grep -O'gws sheets spreadsheets values clear' x"
guarded "heredoc piped into python"     "cat <<'E' | python3 -
import subprocess
parts = 'gws sheets'.split()
subprocess.run(parts + rest)
E"
guarded "unquoted heredoc substitution" "cat > notes.md <<E
\$($UPD)
E"
guarded "heredoc to a script's stdin"   "python3 runner.py <<'E'
$UPD
E"
guarded "here-string to a script"       "python3 runner.py <<< \"$UPD\""
guarded "written, then run by path"     "echo \"$UPD\" > run.sh && chmod +x run.sh && ./run.sh"
guarded "written by sed, then run"      "sed -n 's/x/gws sheets spreadsheets values clear/w run.sh' a; ./run.sh"
guarded "sed -i into a script, then run" "sed -i '' 's/x/gws sheets spreadsheets values clear/' run.sh; ./run.sh"
guarded "python flags clustered"       "python3 -Ic \"import subprocess; subprocess.run('gws sheets'.split() + rest)\""
guarded "bash flags clustered"          "bash -lc 'A=\"gws sheets\"; \$A \$B'"
guarded "service in a variable, beside a grep" "gws \$S \"\$@\"; grep -n sheets a"
guarded "printf into a variable"        "printf -v C 'gws sheets %s' x; \$C"
guarded "a function"                    "f() { gws sheets spreadsheets values clear; }; f"
guarded "an alias"                      "alias x='gws sheets spreadsheets values clear'; x"
guarded "after an if"                   "if grep -q gws a; then gws sheets spreadsheets values clear; fi"
echo "   and a real write next to a mention gets the formula guard's check too"
PATH="$S/bin:$PATH" bash "$FORMULA" <<<"$(bashjson "grep -n sheets a; gws sheets spreadsheets values update --params '{\"range\":\"Data!B2\"}'")" >"$S/out" 2>"$S/err"
[ $? -eq 2 ] && ok || bad "formula guard no longer refuses a write it cannot check"
echo "   reads still earn the mark, and the mark still unlocks an append"
bash "$WRITES" <<<"$(bashjson "gws sheets spreadsheets values get --params '{\"spreadsheetId\":\"$SID\",\"range\":\"_LLM_GUIDE!A:Z\"}'")" >/dev/null 2>&1
[ $? -eq 0 ] && [ -f "$S/marks/$SID" ] && ok || bad "reading the guide no longer records the mark"
bash "$WRITES" <<<"$(bashjson "$APP")" >/dev/null 2>&1; [ $? -eq 0 ] && ok || bad "append after the guide refused"
bash "$WRITES" <<<"$(bashjson "$CLR")" >/dev/null 2>"$S/err"; [ $? -eq 2 ] && grep -q "destructive" "$S/err" && ok || bad "clear after the guide no longer gets the destructive answer"
rm -f "$S/marks/$SID"

echo "-- A4. with fc_ask_not_token on, the person is still asked"
bash_ask() { ROUNDB_FC_ASK_NOT_TOKEN=on bash "$WRITES" <<<"$(bashjson "$2")" 2>/dev/null | grep -q '"permissionDecision": "ask"' && ok || bad "$1 no longer asks"; }
bash_ask "destructive"                 "$CLR"
bash_ask "destructive beside a grep"   "grep -n sheets a; $CLR"
bash_ask "destructive after cd"        "cd /tmp/x && $CLR"
ROUNDB_FC_ASK_NOT_TOKEN=on bash "$WRITES" <<<"$(bashjson "grep -n 'gws sheets spreadsheets values clear' a")" >"$S/out" 2>&1; [ $? -eq 0 ] && [ ! -s "$S/out" ] && ok || bad "a grep asks when the switch is on"

echo "-- B. the Google Sheet SOP is injected only for a message about building or writing a Sheet"
sopcheck() { # sopcheck fires|quiet <message>
  local got=quiet
  P_MSG="$2" python3 -c 'import os,json; print(json.dumps({"prompt":os.environ["P_MSG"]}))' | bash "$SOP" 2>/dev/null | grep -q 'google-sheet-sop' && got=fires
  [ "$got" = "$1" ] && ok || bad "SOP $got, wanted $1: $2"
}
for m in \
  "write a cheat sheet for the git commands" \
  "make me a call sheet for tomorrow's audition" \
  "add the balance sheet total to the tax note" \
  "draft a one-sheet for the pitch" \
  "new sign-in sheet at the front desk" \
  "add a note saying the sheet guard fired on a sed" \
  "write up why the sheet guard blocked me" \
  "the new sheet SOP reminder fired again, why?" \
  "make sure the sheet is not mentioned in the report" \
  "build the test, the sheet guard must still protect" \
  "I added it yesterday. The sheet looks fine" \
  "write about the spreadsheet in the report" \
  "add the sheet-word match to the list" \
  "the sheet is out of date"; do sopcheck quiet "$m"; done
for m in \
  "build me a google sheet for the budget" \
  "create a new spreadsheet for invoices" \
  "design a sheet to track auditions" \
  "make a spreadsheet of my receipts" \
  "write these rows to the sheet" \
  "set up a new sheet for 2027" \
  "put together a sheet of the rates" \
  "draft a budget sheet" \
  "make that sheet" \
  "build the sheet tomorrow" \
  "Build a Sheet." \
  "add a row to the sheet please" \
  "make a sheet tracking receipts" \
  "build a sheet my accountant can use"; do sopcheck fires "$m"; done
echo "   the other SOP rows are untouched"
sopfires() { P_MSG="$2" python3 -c 'import os,json; print(json.dumps({"prompt":os.environ["P_MSG"]}))' | bash "$SOP" 2>/dev/null | grep -q "$1" && ok || bad "$1 no longer fires on: $2"; }
sopfires hook-sop.md "build a hook guard"
sopfires skill-building-sop.md "write a new skill"
sopfires cron-jobs-sop.md "add a cron"

[ ! -e "$S/gws-called" ] && ok || bad "the gws stub was actually called: $(cat "$S/gws-called")"
echo
echo "sheet false alarms: $P passed, $F failed"
[ "$F" -eq 0 ]
