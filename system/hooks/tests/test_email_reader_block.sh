#!/bin/bash
# test_email_reader_block.sh -- Round C lock-prep A, switch email_reader_block: no homemade readers of outside content.
#   ingest_gate_enforce.sh  Write/Edit/MultiEdit + Bash heredoc/redirect writes (lib/outside_reader_scan.py) and clause (h) inline python
#   enforce_egress_allowlist.py  python using a mail protocol, any host      guard_egress.sh  mail protocol + credential
# ALLOW cases first (false alarms matter), then DENY with the switch ON, each also run OFF (must allow). Fictional names only.
# Run: bash system/hooks/tests/test_email_reader_block.sh   (exit 0 = all pass)
HERE="$(cd "$(dirname "$0")/.." && pwd)"; GATE="$HERE/ingest_gate_enforce.sh"; EGR="$HERE/enforce_egress_allowlist.sh"; GE="$HERE/guard_egress.sh"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
CODE="$T/code"; mkdir -p "$CODE/system/tools" "$CODE/shared/tools" "$CODE/system/hooks" "$T/proj/tests" "$T/home" "$T/notes"
cp "$HERE/../tools/shared-fetch-allowlist.txt" "$CODE/system/tools/"
export HOME="$T/home" LIFEHACK_ROOT="$T/notes" OUTSIDE_READER_CODE_ROOT="$CODE"
P=0; F=0
json() { PROJ="$T/proj" python3 -c 'import json,sys,os
t=sys.argv[1]; a=sys.argv[2:]
if t=="Write": ti={"file_path":a[0],"content":a[1]}
elif t=="Edit": ti={"file_path":a[0],"old_string":"x","new_string":a[1]}
elif t=="MultiEdit": ti={"file_path":a[0],"edits":[{"old_string":"x","new_string":a[1]}]}
else: ti={"command":a[0]}
print(json.dumps({"tool_name":t,"tool_input":ti,"cwd":os.environ["PROJ"]}))' "$@"; }
runh() { # runh <hook> <switch> <payload>
  printf '%s' "$3" | ROUNDB_EMAIL_READER_BLOCK="$2" bash "$1" >"$T/o" 2>"$T/e"; RC=$?; }
allow() { runh "$1" on "$3"; if [ $RC -eq 0 ]; then P=$((P+1)); else F=$((F+1)); echo "FALSE ALARM $2: rc=$RC $(head -c 200 "$T/e")"; fi; }
deny() { # deny <hook> <label> <payload> <text that must appear>
  runh "$1" on "$3"
  if [ $RC -eq 2 ] && grep -q "WAY-THROUGH" "$T/e" && grep -q "$4" "$T/e" && grep -q "WHO-COULD-THIS-BREAK" "$T/e"; then P=$((P+1)); else F=$((F+1)); echo "FAIL deny $2 [on]: rc=$RC $(head -c 200 "$T/e")"; fi
  runh "$1" off "$3"; if [ $RC -eq 0 ]; then P=$((P+1)); else F=$((F+1)); echo "FAIL $2 [off] rc=$RC $(head -c 160 "$T/e")"; fi; }
PY="$T/proj/app.py"

# ------------------------------ ALLOW
allow "$GATE" "benign python" "$(json Write "$PY" 'import json
print(json.dumps({"a": 1}))')"
allow "$GATE" "docstring and comment mention imaplib" "$(json Write "$PY" '"""Never use imaplib or poplib here; call email_fetch.py."""
# imaplib is forbidden, so is requests.get
x = "import imaplib"
print(x)')"
allow "$GATE" "string mention of requests" "$(json Write "$PY" 'msg = "we do not use requests or urllib.request here"
print(msg)')"
allow "$GATE" "subprocess call to the shared email fetch" "$(json Write "$PY" 'import subprocess
subprocess.run(["python3", "shared/tools/email_fetch.py", "--consumer", "pond", "--query", "is:unread", "--cap", "5", "--since", "none"])')"
allow "$GATE" "subprocess call to safe_fetch" "$(json Write "$PY" 'import subprocess
out = subprocess.run(["python3", "system/tools/safe_fetch.py", "https://example.com"], capture_output=True)')"
allow "$GATE" "test file in a tests folder that uses imaplib" "$(json Write "$T/proj/tests/reader_check.py" 'import imaplib
def test_x(): pass')"
allow "$GATE" "test_ file name" "$(json Write "$T/proj/test_mail.py" 'import imaplib')"
allow "$GATE" "loopback-only requests" "$(json Write "$PY" 'import requests
r = requests.get("http://localhost:8080/health")')"
allow "$GATE" "markdown doc about imaplib" "$(json Write "$T/proj/notes.md" 'import imaplib is banned; use email_fetch.')"
allow "$GATE" "shell script without a fetch" "$(json Write "$T/proj/run.sh" '#!/bin/bash
# a fetch of https://example.com is not allowed here
echo hi')"
allow "$GATE" "the shared email_fetch.py itself (allowlisted) may hold mail code" "$(json Write "$CODE/shared/tools/email_fetch.py" 'import imaplib
import requests')"
allow "$GATE" "the shared safe_fetch.py itself (allowlisted)" "$(json Edit "$CODE/system/tools/safe_fetch.py" 'import urllib.request')"
allow "$GATE" "Bash running the shared email fetch" "$(json Bash 'python3 shared/tools/email_fetch.py --consumer pond --query is:unread --cap 3 --since none')"
allow "$GATE" "Bash heredoc of benign code to a file" "$(json Bash "cat > $T/proj/ok.py <<'EOF'
print('hello pond')
EOF")"
allow "$GATE" "Bash grep for imaplib" "$(json Bash "grep -rn imaplib $T/proj")"
allow "$GATE" "Bash echo imaplib to a text file" "$(json Bash "echo imaplib > $T/proj/notes.txt")"
allow "$EGR" "egress: benign python -c" "$(json Bash "python3 -c 'print(1)'")"
allow "$EGR" "egress: grep for imaplib (not python code)" "$(json Bash "grep -rn imaplib $T/proj")"
allow "$GE" "guard_egress: imaplib word, no credential" "$(json Bash "echo imaplib")"

# ------------------------------ DENY (ON), allow (OFF)
deny "$GATE" "Write imaplib reader" "$(json Write "$PY" 'import imaplib
m = imaplib.IMAP4_SSL("imap.gmail.com")')" "email_fetch.py"
deny "$GATE" "Write poplib reader" "$(json Write "$PY" 'import poplib
p = poplib.POP3_SSL("pop.example.net")')" "email_fetch.py"
deny "$GATE" "Write googleapiclient gmail" "$(json Write "$PY" 'from googleapiclient.discovery import build
svc = build("gmail", "v1", credentials=c)')" "email_fetch.py"
deny "$GATE" "Write import_module imaplib" "$(json Write "$PY" 'import importlib
m = importlib.import_module("imaplib")')" "email_fetch.py"
deny "$GATE" "Edit adds imaplib" "$(json Edit "$PY" 'import imaplib')" "email_fetch.py"
deny "$GATE" "MultiEdit adds poplib" "$(json MultiEdit "$PY" 'import poplib')" "email_fetch.py"
deny "$GATE" "Write raw Gmail REST in a script" "$(json Write "$T/proj/pull.sh" '#!/bin/bash
echo go
GET=https://gmail.googleapis.com/gmail/v1/users/me/messages')" "email_fetch.py"
deny "$GATE" "Write openssl s_client to IMAP" "$(json Write "$T/proj/pull.sh" 'openssl s_client -connect imap.example.net:993')" "email_fetch.py"
deny "$GATE" "Write requests web fetcher" "$(json Write "$PY" 'import requests
r = requests.get("https://api.example.com/data")')" "safe_fetch.py"
deny "$GATE" "Write urllib.request fetcher" "$(json Write "$PY" 'import urllib.request
urllib.request.urlopen("https://example.com")')" "safe_fetch.py"
deny "$GATE" "Write from urllib import request" "$(json Write "$PY" 'from urllib import request
request.urlopen(u)')" "safe_fetch.py"
deny "$GATE" "Write httpx fetcher" "$(json Write "$PY" 'import httpx
httpx.get(u)')" "safe_fetch.py"
deny "$GATE" "Write wget in a shell script" "$(json Write "$T/proj/alert.sh" 'wget https://ntfy.example.org/topic')" "safe_fetch.py"
deny "$GATE" "Write fetch() in js" "$(json Write "$T/proj/a.js" 'fetch("https://api.example.com/x").then(r => r.json())')" "safe_fetch.py"
deny "$GATE" "requests with a non-loopback URL among loopback ones" "$(json Write "$PY" 'import requests
requests.get("http://localhost:1/x"); requests.get("https://api.example.com/y")')" "safe_fetch.py"
deny "$GATE" "Bash heredoc writes an imaplib reader" "$(json Bash "cat > $T/proj/rd.py <<'EOF'
import imaplib
m = imaplib.IMAP4_SSL('imap.example.net')
EOF")" "email_fetch.py"
deny "$GATE" "Bash tee heredoc writes a requests fetcher" "$(json Bash "tee $T/proj/rd.py <<'EOF'
import requests
requests.get('https://example.com')
EOF")" "safe_fetch.py"
deny "$GATE" "Bash echo redirect writes imaplib code" "$(json Bash "echo 'import imaplib' > $T/proj/rd.py")" "email_fetch.py"
deny "$GATE" "Bash inline python3 - heredoc with imaplib (clause h)" "$(json Bash "python3 - <<'EOF'
import imaplib
imaplib.IMAP4_SSL('imap.gmail.com')
EOF")" "email_fetch.py"
deny "$GATE" "Bash python -c with poplib (clause h)" "$(json Bash "python3 -c 'import poplib; poplib.POP3_SSL(\"x.example.net\")'")" "email_fetch.py"
deny "$EGR" "egress: python imaplib to imap.gmail.com" "$(json Bash "python3 -c 'import imaplib; imaplib.IMAP4_SSL(\"imap.gmail.com\")'")" "email_fetch.py"
deny "$EGR" "egress: python smtplib" "$(json Bash "python3 -c 'import smtplib; smtplib.SMTP(\"smtp.gmail.com\")'")" "email_fetch.py"
# guard_egress: mail protocol + credential. Its text is the credential rule, so only the exit code is checked here.
runh "$GE" on "$(json Bash "python3 -c 'import imaplib; k=\"ANTHROPIC_API_KEY\"; imaplib.IMAP4_SSL(\"x.example.net\")'")"; [ $RC -eq 2 ] && P=$((P+1)) || { F=$((F+1)); echo "FAIL guard_egress imaplib+credential [on] rc=$RC"; }
runh "$GE" off "$(json Bash "python3 -c 'import imaplib; k=\"ANTHROPIC_API_KEY\"; imaplib.IMAP4_SSL(\"x.example.net\")'")"; [ $RC -eq 0 ] && P=$((P+1)) || { F=$((F+1)); echo "FAIL guard_egress imaplib+credential [off] rc=$RC"; }
echo "email-reader-block: $P passed, $F failed"; [ $F -eq 0 ]
