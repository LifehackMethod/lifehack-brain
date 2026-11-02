#!/bin/bash
# test_drive_destructive_guard.sh -- D-F11 (2026-11-02): guard_drive_destructive.sh + the shared gws parser must catch a
# Drive `files update` with trashed true in EVERY shape, including the exact command that trashed 899 real files.
#   switches: fc_drive_bulk_delete, fc_sheet_file_delete (drive guard), gws_exec_heredoc (shared parser, lib/gws_guard.py)
# Strings only: nothing is executed against Drive. gws is a stub on GWS_BIN that answers `files get` for the fictional ids.
# Run: bash system/hooks/tests/test_drive_destructive_guard.sh   (exit 0 = all pass)
HERE="$(cd "$(dirname "$0")" && pwd)"; HOOKS="$(cd "$HERE/.." && pwd)"
DRIVE="$HOOKS/guard_drive_destructive.sh"; LIB="$HOOKS/lib"
FIX="$HERE/fixtures/d-f11-exact-command.txt"
for f in "$DRIVE" "$FIX" "$LIB/gws_guard.py"; do [ -f "$f" ] || { echo "CANNOT RUN: $f"; exit 1; }; done
. "$HERE/pin_roundb_off.sh"
# Temp folder is left for the OS temp sweep (this test deletes nothing).
S="$(mktemp -d "${TMPDIR:-/tmp}/ddg.XXXXXX")"
P=0; F=0; OUTF="$S/out"; ERRF="$S/err"
mkdir -p "$S/bin" "$S/marks" "$S/home"
printf '%s\n' '#!/bin/bash' 'case "$*" in' \
  '  *pondSheet*) echo "{\"mimeType\":\"application/vnd.google-apps.spreadsheet\",\"name\":\"Pond Ledger\"}" ;;' \
  '  *pondNote*)  echo "{\"mimeType\":\"text/plain\",\"name\":\"scratch note\"}" ;;' \
  '  *) exit 1 ;;' 'esac' > "$S/bin/gws"
chmod +x "$S/bin/gws"
export GWS_BIN="$S/bin/gws" SHEET_LLM_MARKDIR="$S/marks"

bashjson() { T="$1" python3 -c 'import os,json; print(json.dumps({"tool_name":"Bash","tool_input":{"command":os.environ["T"]},"cwd":"/tmp"}))'; }
ok() { P=$((P+1)); }
bad() { F=$((F+1)); echo "FAIL: $1"; }
drive() { HOME="$S/home" bash "$DRIVE" <<<"$(bashjson "$1")" >"$OUTF" 2>"$ERRF"; RC=$?; }
d_allow() { drive "$2"; if [ $RC -eq 0 ] && ! grep -q '"ask"' "$OUTF"; then ok; else bad "ALLOW $1 (rc=$RC $(head -c 200 "$OUTF"))"; fi; }
d_ask() { drive "$2"; if [ $RC -eq 0 ] && grep -q '"permissionDecision": "ask"' "$OUTF" && grep -q "ASK FIRST" "$OUTF" && grep -q "WHY:" "$OUTF" && grep -q "WAY THROUGH:" "$OUTF" && grep -q "RULE:" "$OUTF"; then ok; else bad "ASK $1 (rc=$RC $(head -c 200 "$OUTF"))"; fi; }
d_bulk() { drive "$2"; if [ $RC -eq 0 ] && grep -q '"permissionDecision": "ask"' "$OUTF" && grep -q "more than one Drive file" "$OUTF"; then ok; else bad "BULK $1 (rc=$RC $(head -c 200 "$OUTF"))"; fi; }

# ── the shapes (fictional ids; every one sets trashed true) ─────────────────────────────────────────────────────────
DF11="$(cat "$FIX")"
PLAIN='gws drive files update --params '\''{"fileId":"mystery0001"}'\'' --json '\''{"trashed":true}'\'''
PLAIN_NOTE='gws drive files update --params '\''{"fileId":"pondNote0001"}'\'' --json '\''{"trashed":true}'\'''
PLAIN_SHEET='gws drive files update --params '\''{"fileId":"pondSheet0001"}'\'' --json '\''{"trashed": true}'\'''
DASH_C='python3 -c "import subprocess,json
for f in open(\"ids.txt\").read().split():
    subprocess.run([\"gws\",\"drive\",\"files\",\"update\",\"--params\",json.dumps({\"fileId\":f}),\"--json\",json.dumps({\"trashed\":True})])"'
QHD=$'cd /tmp && python3 -I - <<\'EOF\'\nimport subprocess, json\nfor fid in json.load(open("ids.json")):\n    subprocess.run(["gws","drive","files","update","--params",json.dumps({"fileId":fid}),"--json",json.dumps({"trashed":True})])\nEOF'
QHD_LIT=$'python3 - <<\'EOF\'\nimport subprocess\nfor fid in open("ids.txt").read().split():\n    subprocess.run(["gws","drive","files","update","--params",\'{"fileId":"%s"}\' % fid,"--json",\'{"trashed":true}\'])\nEOF'
QHD_SHELLSTR=$'python3 - <<\'EOF\'\nimport subprocess\nfor fid in open("ids.txt").read().split():\n    subprocess.run("gws drive files update --params \'{\\"fileId\\":\\"%s\\"}\' --json \'{\\"trashed\\":true}\'" % fid, shell=True)\nEOF'
UHD=$'cd /tmp && python3 -I - <<EOF\nimport subprocess, json\nfor fid in json.load(open("ids.json")):\n    subprocess.run(["gws","drive","files","update","--params",json.dumps({"fileId":fid}),"--json",json.dumps({"trashed":True})])\nEOF'
UHD_KW=$'node - <<EOF\nconst {execFileSync} = require("child_process");\nids.forEach(id => execFileSync("gws", ["drive","files","update","--params",JSON.stringify({fileId:id}),"--json",\'{"trashed":true}\']));\nEOF'
FORLOOP='for f in $(cat ids.txt); do gws drive files update --params "{\"fileId\":\"$f\"}" --json '\''{"trashed":true}'\''; done'
WHILELOOP='while read f; do gws drive files update --params "{\"fileId\":\"$f\"}" --json '\''{"trashed": true}'\''; done < ids.txt'
UNREADABLE='gws drive files update --params '\''{"fileId":"pondNote0001"}'\'' --json "$BODY"'
PY_UNREADABLE=$'python3 - <<\'EOF\'\nimport subprocess, json\nsubprocess.run(["gws","drive","files","update","--params",json.dumps({"fileId":"pondNote0001"}),"--json",json.dumps(body)])\nEOF'
# ── look-alikes that must pass ─────────────────────────────────────────────────────────────────────────────────────
LIST='gws drive files list --params '\''{"q":"trashed = true","pageSize":100}'\'''
GET='gws drive files get --params '\''{"fileId":"pondNote0001"}'\'''
RENAME='gws drive files update --params '\''{"fileId":"pondNote0001"}'\'' --json '\''{"name":"pond notes 2"}'\'''
PY_RENAME=$'python3 - <<\'EOF\'\nimport subprocess, json\nsubprocess.run(["gws","drive","files","update","--params",json.dumps({"fileId":"pondNote0001"}),"--json",json.dumps({"name":"x"})])\nEOF'
CAT_U=$'cat > notes.md <<EOF\nfor f in ids: gws drive files update --params x --json \'{"trashed":true}\'\nsubprocess.run(["gws","drive","files","delete","--params",p])\nEOF'
CAT_Q=$'cat > notes.md <<\'EOF\'\nsubprocess.run(["gws","drive","files","update","--json",json.dumps({"trashed":True})])\nEOF'
PY_LISTLOOP=$'cd /tmp && python3 -I - <<\'E\'\nimport json,subprocess\nfor f in files:\n    r=subprocess.run([\'gws\',\'drive\',\'files\',\'list\',\'--params\',json.dumps({\'q\':q,\'pageSize\':5})],capture_output=True,text=True).stdout\nE'
PRINT_ONLY=$'python3 - <<\'E\'\nprint("gws drive files update --json trashed:true is now guarded")\nE'

echo "-- 0. the fixture is the exact D-F11 command (sha256 pinned)"
# Byte-exact copy of the stream's command EXCEPT its one absolute home-folder prefix, written as ~/ (the commit-time
# no-internal-leakage gate refuses an account path; the cp destination plays no part in any verdict).
# Original (with the account path): 564 bytes, sha256 8b0636d4bdb74cd476e8c0f35b8c333a89e6e9633d207be3ed68a1647763bf44.
SUM=$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$FIX")
[ "$SUM" = "dd85fcbf635ef3ff1c85ae2f7ba7b79d3eaba6515ff035931eb6b7160b969e43" ] && ok || bad "fixture drifted: $SUM"

echo "-- 1. all switches ON"
export ROUNDB_FC_DRIVE_BULK_DELETE=on ROUNDB_FC_SHEET_FILE_DELETE=on ROUNDB_GWS_EXEC_HEREDOC=on
d_bulk "D-F11 EXACT command (899-file trash loop)"      "$DF11"
d_ask  "plain update trashed, unknown file"            "$PLAIN"
d_ask  "plain update trashed, a Sheet"                  "$PLAIN_SHEET"
d_bulk "python3 -c loop, json.dumps body"               "$DASH_C"
d_bulk "quoted heredoc, json.dumps body"                "$QHD"
d_bulk "quoted heredoc, '%s' % fid literal body"        "$QHD_LIT"
d_bulk "quoted heredoc, shell=True string"              "$QHD_SHELLSTR"
d_bulk "unquoted heredoc, json.dumps body"              "$UHD"
d_bulk "unquoted heredoc, node forEach"                 "$UHD_KW"
d_bulk "shell for-loop"                                 "$FORLOOP"
d_bulk "shell while-loop"                               "$WHILELOOP"
d_ask  "update with an unreadable --json body"          "$UNREADABLE"
d_ask  "python update, json.dumps(variable) body"       "$PY_UNREADABLE"
echo "-- 1b. ON: look-alikes pass silently"
d_allow "files list (query names trashed)"              "$LIST"
d_allow "files get"                                     "$GET"
d_allow "rename (update, no trashed)"                   "$RENAME"
d_allow "python rename, json.dumps literal body"        "$PY_RENAME"
d_allow "single non-Sheet trash (unchanged policy)"     "$PLAIN_NOTE"
d_allow "cat > f <<EOF holding gws text"                "$CAT_U"
d_allow "cat > f <<'EOF' holding gws text"              "$CAT_Q"
d_allow "python list loop (D-F11 reconnaissance)"       "$PY_LISTLOOP"
d_allow "print() of the words in executed code"         "$PRINT_ONLY"

echo "-- 2. gws_exec_heredoc OFF: executed quoted heredocs are blanked again (the old reader)"
export ROUNDB_GWS_EXEC_HEREDOC=off
d_allow "D-F11 exact, parser switch off = old behaviour" "$DF11"
d_allow "quoted heredoc, parser switch off"              "$QHD"
d_bulk  "shell for-loop still caught (loop regex fix is the drive guard's own)" "$FORLOOP"

echo "-- 3. drive switches OFF: nothing asks"
export ROUNDB_FC_DRIVE_BULK_DELETE=off ROUNDB_FC_SHEET_FILE_DELETE=off ROUNDB_GWS_EXEC_HEREDOC=on
for c in "$DF11" "$PLAIN" "$FORLOOP" "$QHD" "$UNREADABLE"; do d_allow "drive switches off" "$c"; done

echo "-- 4. shared parser self-test (switch-pinned inside)"
if python3 "$LIB/gws_guard.py" --selftest >"$OUTF" 2>&1; then ok; else bad "gws_guard --selftest: $(tail -3 "$OUTF")"; fi

echo "-- 5. the gws_exec_heredoc conf line is a REAL line that the readers see"
CONF="$HOOKS/roundB.conf"
N=$(grep -cE '^gws_exec_heredoc=(on|off)[[:space:]]*$' "$CONF")
[ "$N" = 1 ] && ok || bad "gws_exec_heredoc: expected exactly one real name=on|off line, found $N"
WANT=$(sed -nE 's/^gws_exec_heredoc=(on|off)[[:space:]]*$/\1/p' "$CONF" | tail -1)
GOT_SH=$( unset ROUNDB_GWS_EXEC_HEREDOC; . "$HOOKS/lib/roundb.sh"; roundb_on gws_exec_heredoc && echo on || echo off )
GOT_PY=$(env -u ROUNDB_GWS_EXEC_HEREDOC python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import roundb; print("on" if roundb.roundb_on("gws_exec_heredoc") else "off")' "$LIB")
[ "$GOT_SH" = "$WANT" ] && ok || bad "roundb.sh reads gws_exec_heredoc as $GOT_SH, line says $WANT"
[ "$GOT_PY" = "$WANT" ] && ok || bad "roundb.py reads gws_exec_heredoc as $GOT_PY, line says $WANT"
GOT_ENV=$(ROUNDB_GWS_EXEC_HEREDOC=off python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import gws_guard; print("on" if gws_guard.exec_heredoc_on() else "off")' "$LIB")
[ "$GOT_ENV" = off ] && ok || bad "env ROUNDB_GWS_EXEC_HEREDOC=off did not override the conf"

echo
echo "drive destructive guard (D-F11): $P passed, $F failed"
[ "$F" -eq 0 ]
