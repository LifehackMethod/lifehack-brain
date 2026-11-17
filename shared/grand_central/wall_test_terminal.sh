#!/bin/bash
# wall_test_terminal.sh — plan step 1.2, the part the owner runs once in Terminal.
# Needs GC_OWNER_EMAIL (the address of the account under test; the test mail goes to it).
#
# From a Claude window, YOLO's guards block these attempts before they reach Google, so they can't prove what
# GOOGLE refuses. Run here, they go to Google with the rig login only. Every one of them MUST be refused.
# They are written to be harmless even if the wall failed: a mail to yourself, removing a label the message
# doesn't have, an event in 2099, a task titled "rig wall test". If anything comes back "ALLOWED", stop and
# tell the coordinator window.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
unset GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE GOOGLE_WORKSPACE_CLI_TOKEN
export GOOGLE_WORKSPACE_CLI_CONFIG_DIR="$HOME/.config/gws-rig"
export GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND=file
DATA_ROOT="$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import gc_settings; print(gc_settings.data_root())' "$HERE")" || exit 1
OUT="$DATA_ROOT/state/wall-terminal.txt"
mkdir -p "$(dirname "$OUT")"
: > "$OUT"

try() {  # $1 = name, rest = command
  local name="$1"; shift
  if out="$("$@" 2>&1)"; then
    echo "ALLOWED   $name   <-- WALL FAILED, tell the coordinator" | tee -a "$OUT"
  else
    # Google's JSON error: keep the numeric code and the human message, so a refusal for the RIGHT reason
    # (insufficient permission, 403) can be told apart from a malformed request (400) or a not-found (404).
    reason="$(printf '%s' "$out" | python3 -c 'import json,sys
t=sys.stdin.read()
try:
    e=json.loads(t[t.find("{"):]).get("error",{})
    print(str(e.get("code","?"))+" "+str(e.get("message",""))[:150])
except Exception:
    print(t.strip().splitlines()[-1][:150] if t.strip() else "no output")')"
    echo "REFUSED   $name   ($reason)" | tee -a "$OUT"
  fi
}

ME="${GC_OWNER_EMAIL:?set GC_OWNER_EMAIL to the address of the account under test}"
RAW="$(printf 'To: %s\r\nSubject: rig wall test - should never arrive\r\n\r\nIf you see this, the wall failed.\r\n' "$ME" | base64 | tr '+/' '-_' | tr -d '=\n')"
MSG_ID="$(python3 "$HERE/first_message_id.py" 2>/dev/null)"

echo "rig wall test (Terminal) — $(date)" | tee -a "$OUT"
try "gmail send"            gws gmail users messages send --params '{"userId":"me"}' --json "{\"raw\":\"$RAW\"}"
try "gmail label change"    gws gmail users messages modify --params "{\"userId\":\"me\",\"id\":\"${MSG_ID:-none}\"}" --json '{"removeLabelIds":["TRASH"]}'
try "gmail trash"           gws gmail users messages trash --params "{\"userId\":\"me\",\"id\":\"${MSG_ID:-none}\"}"
try "gmail filter create"   gws gmail users settings filters create --params '{"userId":"me"}' --json '{"criteria":{"from":"rig-wall-test@example.invalid"},"action":{"addLabelIds":["TRASH"]}}'
try "calendar create event" gws calendar events insert --params '{"calendarId":"primary"}' --json '{"summary":"rig wall test","start":{"date":"2099-01-01"},"end":{"date":"2099-01-02"}}'
try "tasks create task"     gws tasks tasks insert --params '{"tasklist":"@default"}' --json '{"title":"rig wall test"}'
try "contacts create"       gws people people createContact --json '{"names":[{"givenName":"rig wall test"}],"emailAddresses":[{"value":"rig-wall-test@example.invalid"}]}'
echo "message id used: ${MSG_ID:-none (could not read one)}" | tee -a "$OUT"
echo "saved to $OUT"
