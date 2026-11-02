#!/bin/bash
# test_cloud_destructive_guard.sh -- guard_cloud_destructive.sh (D-F11, switch fc_cloud_destructive_ask): ASK before a
# destructive cloud action (gcloud, gsutil, rclone, aws s3, curl/wget DELETE to googleapis.com, gws permissions/
# emptyTrash/delete), in the command or in code it runs; ALLOW reads, listings, data heredocs and prose.
# Strings only: no cloud CLI is ever run (the hook reads the command text; nothing is executed).
# Run: bash system/hooks/tests/test_cloud_destructive_guard.sh   (exit 0 = all pass)
HERE="$(cd "$(dirname "$0")" && pwd)"; HOOKS="$(cd "$HERE/.." && pwd)"
G="$HOOKS/guard_cloud_destructive.sh"; LIB="$HOOKS/lib"
for f in "$G" "$LIB/cloud_guard.py"; do [ -f "$f" ] || { echo "CANNOT RUN: $f"; exit 1; }; done
. "$HERE/pin_roundb_off.sh"
# Temp folder is left for the OS temp sweep (this test deletes nothing).
S="$(mktemp -d "${TMPDIR:-/tmp}/cdg.XXXXXX")"; trap 'rm -rf "$S"' EXIT  # guaranteed cleanup: leaked test temp dirs filled a disk, 2026-11-01
mkdir -p "$S/home"
P=0; F=0; OUTF="$S/out"; ERRF="$S/err"

bashjson() { T="$1" python3 -c 'import os,json; print(json.dumps({"tool_name":"Bash","tool_input":{"command":os.environ["T"]},"cwd":"/tmp"}))'; }
ok() { P=$((P+1)); }
bad() { F=$((F+1)); echo "FAIL: $1"; }
hook() { HOME="$S/home" bash "$G" <<<"$1" >"$OUTF" 2>"$ERRF"; RC=$?; }
allow() { hook "$(bashjson "$2")"; if [ $RC -eq 0 ] && [ ! -s "$OUTF" ] && [ ! -s "$ERRF" ]; then ok; else bad "ALLOW $1 (rc=$RC out=$(head -c 220 "$OUTF") err=$(head -c 120 "$ERRF"))"; fi; }
ask() { hook "$(bashjson "$2")"; if [ $RC -eq 0 ] && grep -q '"permissionDecision": "ask"' "$OUTF" && grep -q '"hookEventName": "PreToolUse"' "$OUTF" && grep -q "ASK FIRST (cloud guard)" "$OUTF" && grep -q "WHY:" "$OUTF" && grep -q "WAY THROUGH:" "$OUTF" && grep -q "RULE: system/hooks/guard_cloud_destructive.sh" "$OUTF"; then ok; else bad "ASK $1 (rc=$RC out=$(head -c 220 "$OUTF") err=$(head -c 120 "$ERRF"))"; fi; }
ask_says() { ask "$1" "$2"; grep -q "$3" "$OUTF" || bad "ASK $1: reason lacks '$3' ($(head -c 300 "$OUTF"))"; }

# ── positives ──────────────────────────────────────────────────────────────────────────────────────────────────────
GC_RM='gcloud storage rm gs://pond-bucket/old.csv'
GC_RMR='gcloud storage rm -r gs://pond-bucket'
GC_BUCKET='gcloud storage buckets delete gs://pond-bucket'
GC_PROJ='gcloud projects delete pond-project-0001 --quiet'
GC_VM='gcloud compute instances delete pond-vm --zone us-east1-b'
GS_RM='gsutil rm gs://pond-bucket/old.csv'
GS_MRM='gsutil -m rm -r '\''gs://pond-bucket/**'\'''
GS_RB='gsutil rb gs://pond-bucket'
GS_RSYNC='gsutil rsync -d -r ./site gs://pond-bucket'
RC_DEL='rclone delete pondremote:archive'
RC_PURGE='rclone purge pondremote:archive'
RC_DELF='rclone deletefile pondremote:archive/a.txt'
RC_RMDIRS='rclone rmdirs pondremote:archive'
RC_MOVE='rclone move ./local pondremote:archive'
RC_SYNC='rclone sync ./local pondremote:archive'
AWS_RM='aws s3 rm s3://pond-bucket/old.csv'
AWS_RB='aws s3 rb s3://pond-bucket --force'
CURL_DEL='curl -s -X DELETE https://www.googleapis.com/drive/v3/files/pondFile0001 -H "Authorization: Bearer $TOKEN"'
CURL_REQ='curl --request DELETE "https://storage.googleapis.com/storage/v1/b/pond-bucket/o/old.csv"'
CURL_XDEL='curl -XDELETE https://www.googleapis.com/drive/v3/files/pondFile0001'
CURL_PATCH='curl -X PATCH https://www.googleapis.com/drive/v3/files/pondFile0001 -H "Content-Type: application/json" -d '\''{"trashed": true}'\'''
CURL_TRASHPATH='curl -X POST https://gmail.googleapis.com/gmail/v1/users/me/messages/m1/trash'
CURL_EMPTY='curl -X DELETE https://www.googleapis.com/drive/v3/files/trash'
WGET_DEL='wget --method=DELETE https://www.googleapis.com/drive/v3/files/pondFile0001'
GWS_PERM='gws drive permissions create --params '\''{"fileId":"pondFile0001"}'\'' --json '\''{"role":"writer","type":"anyone"}'\'''
GWS_EMPTY='gws drive files emptyTrash'
GWS_DDEL='gws drive files delete --params '\''{"fileId":"pondFile0001"}'\'''
GWS_GDEL='gws gmail users messages delete --params '\''{"userId":"me","id":"m1"}'\'''
GWS_CDEL='gws calendar events delete --params '\''{"calendarId":"primary","eventId":"e1"}'\'''
GWS_CCLEAR='gws calendar calendars clear --params '\''{"calendarId":"primary"}'\'''
GWS_SDEL='gws sheets spreadsheets developerMetadata delete --params '\''{"spreadsheetId":"s1"}'\'''
EMB_HD=$'cd /tmp && python3 -I - <<\'E\'\nimport subprocess\nfor r in ["pondremote:a", "pondremote:b"]:\n    subprocess.run(["rclone","purge",r])\nE'
EMB_C='python3 -c "import subprocess; subprocess.run([\"gsutil\",\"rm\",\"gs://pond-bucket/old.csv\"])"'
EMB_BASHC='bash -c '\''gcloud storage rm gs://pond-bucket/old.csv'\'''
EMB_SHELLSTR=$'python3 - <<\'E\'\nimport os\nos.system("rclone delete pondremote:old")\nE'
EMB_UHD=$'python3 - <<EOF\nimport subprocess\nsubprocess.run(["gcloud","storage","rm","gs://pond-bucket/x"])\nEOF'
EMB_BASHHD=$'bash <<\'E\'\naws s3 rm s3://pond-bucket/old.csv\nE'
EMB_GAPI=$'python3 - <<\'E\'\nfor f in ids:\n    service.files().delete(fileId=f).execute()\nE'
EMB_GAPI_TRASH=$'python3 - <<\'E\'\nfor f in ids:\n    service.files().update(fileId=f, body={"trashed": True}).execute()\nE'
EMB_GWS_PERM=$'python3 - <<\'E\'\nimport subprocess, json\nsubprocess.run(["gws","drive","permissions","delete","--params",json.dumps({"fileId":f,"permissionId":p})])\nE'
LOOP_GS='for b in pond-a pond-b; do gsutil rm gs://$b/old.csv; done'
NONLIT_RC='rclone $OP pondremote:archive'
CURL_DEL_VAR='curl -X DELETE "$API_URL"'

# ── negatives ──────────────────────────────────────────────────────────────────────────────────────────────────────
N_GWS_LIST='gws drive files list --params '\''{"q":"trashed = false","pageSize":100}'\'''
N_GWS_GET='gws drive files get --params '\''{"fileId":"pondFile0001"}'\'''
N_GC_LS='gcloud storage ls gs://pond-bucket'
N_GC_LIST='gcloud compute instances list --filter="name~pond"'
N_GS_LS='gsutil ls -l gs://pond-bucket'
N_RC_LS='rclone ls pondremote:archive'
N_RC_COPY='rclone copy ./local pondremote:archive'
N_AWS_LS='aws s3 ls s3://pond-bucket'
N_CAT_U=$'cat > notes.md <<EOF\ngws drive files delete --params x\nrclone purge pondremote:archive\ngcloud storage rm gs://pond-bucket\ncurl -X DELETE https://www.googleapis.com/drive/v3/files/x\nEOF'
N_CAT_Q=$'cat > notes.md <<\'EOF\'\nsubprocess.run(["rclone","purge","pondremote:archive"])\ngsutil rm gs://pond-bucket/x\nEOF'
N_TEE=$'tee runbook.md <<\'EOF\' >/dev/null\nrclone sync ./a pondremote:b deletes on the target\nEOF'
N_CURL_GET='curl -s https://www.googleapis.com/drive/v3/files -H "Authorization: Bearer $TOKEN"'
N_CURL_XGET='curl -X GET "https://www.googleapis.com/drive/v3/files?q=trashed%3Dtrue"'
N_CURL_LOCAL='curl -X DELETE http://localhost:8080/items/1'
N_ECHO='echo "rclone purge and gsutil rm now ask first"'
N_COMMIT='git commit -m "docs: gcloud storage rm, rclone purge and curl -X DELETE now ask"'
N_GREP='grep -rn "requests.delete\|rclone purge" .'
N_PRINT=$'python3 - <<\'E\'\nprint("gcloud storage rm is guarded")\nE'
N_DRIVE_TRASH1='gws drive files update --params '\''{"fileId":"pondFile0001"}'\'' --json '\''{"trashed":true}'\'''
N_LS='ls -la /tmp'

echo "-- 1. switch OFF (the pinned default): every positive passes silently"
export ROUNDB_FC_CLOUD_DESTRUCTIVE_ASK=off
for c in "$GC_RM" "$GS_MRM" "$RC_PURGE" "$CURL_DEL" "$GWS_PERM" "$EMB_HD" "$AWS_RM"; do allow "OFF: $c" "$c"; done

echo "-- 2. switch ON: ASK"
export ROUNDB_FC_CLOUD_DESTRUCTIVE_ASK=on
ask_says "gcloud storage rm"            "$GC_RM" "gcloud storage rm"
ask_says "gcloud storage rm -r"         "$GC_RMR" "whole tree or wildcard"
ask "gcloud storage buckets delete"     "$GC_BUCKET"
ask "gcloud projects delete"            "$GC_PROJ"
ask "gcloud compute instances delete"   "$GC_VM"
ask "gsutil rm"                         "$GS_RM"
ask_says "gsutil -m rm -r wildcard"     "$GS_MRM" "whole tree or wildcard"
ask "gsutil rb"                         "$GS_RB"
ask "gsutil rsync -d"                   "$GS_RSYNC"
ask "rclone delete"                     "$RC_DEL"
ask "rclone purge"                      "$RC_PURGE"
ask "rclone deletefile"                 "$RC_DELF"
ask "rclone rmdirs"                     "$RC_RMDIRS"
ask "rclone move"                       "$RC_MOVE"
ask_says "rclone sync"                  "$RC_SYNC" "deletes on the target side"
ask "aws s3 rm"                         "$AWS_RM"
ask "aws s3 rb"                         "$AWS_RB"
ask_says "curl -X DELETE googleapis"    "$CURL_DEL" "HTTP DELETE to a Google API"
ask "curl --request DELETE storage"     "$CURL_REQ"
ask "curl -XDELETE"                     "$CURL_XDEL"
ask_says "curl PATCH trashed:true"      "$CURL_PATCH" "sends a Google file to the trash"
ask "curl POST .../trash"               "$CURL_TRASHPATH"
ask "curl DELETE drive trash (empty)"   "$CURL_EMPTY"
ask "wget --method=DELETE"              "$WGET_DEL"
ask_says "gws drive permissions create" "$GWS_PERM" "sharing change"
ask "gws drive emptyTrash"              "$GWS_EMPTY"
ask "gws drive files delete"            "$GWS_DDEL"
ask "gws gmail messages delete"         "$GWS_GDEL"
ask "gws calendar events delete"        "$GWS_CDEL"
ask "gws calendar calendars clear"      "$GWS_CCLEAR"
ask "gws sheets ... delete"             "$GWS_SDEL"
ask_says "rclone purge in a python heredoc loop" "$EMB_HD" "in a loop"
ask "gsutil rm in python3 -c argv list" "$EMB_C"
ask "gcloud rm in bash -c"              "$EMB_BASHC"
ask "rclone delete via os.system"       "$EMB_SHELLSTR"
ask "gcloud rm in an unquoted python heredoc" "$EMB_UHD"
ask "aws s3 rm in a bash heredoc"       "$EMB_BASHHD"
ask_says "googleapiclient files().delete in a loop" "$EMB_GAPI" "in a loop"
ask "googleapiclient files().update trashed" "$EMB_GAPI_TRASH"
ask "gws permissions delete in python"  "$EMB_GWS_PERM"
ask_says "gsutil rm in a shell for-loop" "$LOOP_GS" "in a loop"
ask "rclone with an unreadable operation" "$NONLIT_RC"
ask "curl DELETE to an unreadable URL"  "$CURL_DEL_VAR"

echo "-- 3. switch ON: ALLOW (silent)"
allow "gws drive files list"            "$N_GWS_LIST"
allow "gws drive files get"             "$N_GWS_GET"
allow "gcloud storage ls"               "$N_GC_LS"
allow "gcloud compute instances list"   "$N_GC_LIST"
allow "gsutil ls"                       "$N_GS_LS"
allow "rclone ls"                       "$N_RC_LS"
allow "rclone copy"                     "$N_RC_COPY"
allow "aws s3 ls"                       "$N_AWS_LS"
allow "cat > f <<EOF holding cloud text" "$N_CAT_U"
allow "cat > f <<'EOF' holding cloud text" "$N_CAT_Q"
allow "tee f <<'EOF' holding cloud text" "$N_TEE"
allow "curl GET googleapis"             "$N_CURL_GET"
allow "curl -X GET googleapis"          "$N_CURL_XGET"
allow "curl DELETE to localhost"        "$N_CURL_LOCAL"
allow "echo prose"                      "$N_ECHO"
allow "git commit message"              "$N_COMMIT"
allow "grep for the words"              "$N_GREP"
allow "print() in executed code"        "$N_PRINT"
allow "single drive update trashed (drive guard owns it)" "$N_DRIVE_TRASH1"
allow "ls"                              "$N_LS"
allow "unrelated tool"                  '{"tool_name":"Read","tool_input":{"file_path":"/tmp/gcloud-notes.txt"}}'
allow "empty payload"                   ''

echo "-- 4. crash fails open with one stderr line"
hook 'not json, but it names gcloud'
if [ $RC -eq 0 ] && [ ! -s "$OUTF" ] && grep -q "guard_cloud_destructive: internal error" "$ERRF"; then ok; else bad "crash: rc=$RC out=$(cat "$OUTF") err=$(cat "$ERRF")"; fi

echo "-- 5. the fc_cloud_destructive_ask conf line is a REAL line that the readers see"
CONF="$HOOKS/roundB.conf"
N=$(grep -cE '^fc_cloud_destructive_ask=(on|off)[[:space:]]*$' "$CONF")
[ "$N" = 1 ] && ok || bad "fc_cloud_destructive_ask: expected exactly one real name=on|off line, found $N"
WANT=$(sed -nE 's/^fc_cloud_destructive_ask=(on|off)[[:space:]]*$/\1/p' "$CONF" | tail -1)
GOT_SH=$( unset ROUNDB_FC_CLOUD_DESTRUCTIVE_ASK; . "$LIB/roundb.sh"; roundb_on fc_cloud_destructive_ask && echo on || echo off )
GOT_PY=$(env -u ROUNDB_FC_CLOUD_DESTRUCTIVE_ASK python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import roundb; print("on" if roundb.roundb_on("fc_cloud_destructive_ask") else "off")' "$LIB")
[ "$GOT_SH" = "$WANT" ] && ok || bad "roundb.sh reads fc_cloud_destructive_ask as $GOT_SH, line says $WANT"
[ "$GOT_PY" = "$WANT" ] && ok || bad "roundb.py reads fc_cloud_destructive_ask as $GOT_PY, line says $WANT"

echo "-- 6. registered on PreToolUse Bash in the plugin manifest"
python3 - "$HOOKS/../../hooks/hooks.json" <<'PY' && ok || bad "guard_cloud_destructive.sh is not registered on PreToolUse Bash in hooks/hooks.json"
import json, sys
d = json.load(open(sys.argv[1]))
hit = any(e.get("matcher") == "Bash" and any("guard_cloud_destructive.sh" in h.get("command", "") for h in e.get("hooks", []))
          for e in d.get("hooks", {}).get("PreToolUse", []))
sys.exit(0 if hit else 1)
PY

echo
echo "cloud destructive guard: $P passed, $F failed"
[ "$F" -eq 0 ]
