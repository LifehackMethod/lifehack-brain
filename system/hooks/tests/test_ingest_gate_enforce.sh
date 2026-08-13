#!/bin/bash
# test_ingest_gate_enforce.sh — the matrix this gate is supposed to hold.
#
# WHY THIS IS WRITTEN FRESH RATHER THAN CARRIED OVER. The donor system had a fixture of the same
# name, and it was RETIRED on 2026-08-01 with a banner explaining that nothing ever ran it — no
# schedule, no CI, no habit. Three of its allow-cases had also gone stale: it still asserted that an
# external .txt, .md or extensionless file was ALLOWED, which stopped being true when the gate was
# tightened. Porting it would have shipped a suite that fails on arrival while asserting something
# false about the product. This one asserts what the gate does TODAY, and it runs.
#
# Deny = exit 2. Allow = exit 0.
# Run: bash system/hooks/tests/test_ingest_gate_enforce.sh   (exit 0 = all pass)

HOOKDIR="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$HOOKDIR/ingest_gate_enforce.sh"
REPO="${HOOKDIR%/system/hooks}"
[ -f "$HOOK" ] || { echo "CANNOT RUN: no hook at $HOOK"; exit 1; }

# A throwaway notes root, so the notes-root arms are exercised against a real directory that is
# nobody's actual notes. Cleaned up on the way out, whatever happens.
NOTES="$(mktemp -d "${TMPDIR:-/tmp}/gatetest.XXXXXX")"
trap 'rm -rf "$NOTES"' EXIT
mkdir -p "$NOTES/memory" "$NOTES/state" "$NOTES/corpus/_unpacked"

pass=0; fail=0

j() { python3 -c "import json,sys; print(json.dumps({'tool_name':sys.argv[1],'tool_input':json.loads(sys.argv[2])}))" "$1" "$2"; }
ja() { python3 -c "import json,sys; print(json.dumps({'tool_name':sys.argv[1],'tool_input':json.loads(sys.argv[2]),'agent_id':sys.argv[3]}))" "$1" "$2" "$3"; }

# label · expected exit · payload-json
run() {
  local label="$1" exp="$2" payload="$3"; shift 3
  local got
  printf '%s' "$payload" | env LIFEHACK_ROOT="$NOTES" "$@" bash "$HOOK" >/dev/null 2>&1
  got=$?
  if [ "$got" = "$exp" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL [$label]: expected exit $exp, got $got"; fi
}
check()  { run "$1" "$2" "$(j "$3" "$4")"; }
checka() { run "$1" "$2" "$(ja "$3" "$4" "$5")"; }

# The skip-variable NAME is built by concatenation so this fixture never contains the literal
# assignment pattern it is testing for — otherwise the file is its own tripwire.
SKV="LIFEHACK_SKIP_SAFE""_READ"

echo "-- WEB: never raw (expect 2) --"
check "WebFetch raw"            2 WebFetch  '{"url":"http://example.com"}'
check "WebSearch native"        2 WebSearch '{"query":"anything"}'

echo "-- DOCUMENTS: always through a reader, even inside the repo (expect 2) --"
check "Read .pdf"               2 Read "$(python3 -c "import json;print(json.dumps({'file_path':'/tmp/a.pdf'}))")"
check "Read .docx"              2 Read '{"file_path":"/tmp/a.docx"}'
check "Read .xlsx"              2 Read '{"file_path":"/tmp/a.xlsx"}'
check "Read .csv"               2 Read '{"file_path":"/tmp/a.csv"}'
check "Read .pdf inside repo"   2 Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]+'/docs/a.pdf'}))" "$REPO")"

echo "-- OUTSIDE THE TRUSTED ZONE: redirected, whatever the extension (expect 2) --"
check "external .txt"           2 Read '{"file_path":"/tmp/a.txt"}'
check "external .md"            2 Read '{"file_path":"/tmp/a.md"}'
check "external no extension"   2 Read '{"file_path":"/tmp/README"}'
check "external .html"          2 Read '{"file_path":"/tmp/a.html"}'
check "external .eml"           2 Read '{"file_path":"/tmp/a.eml"}'

echo "-- THE CARVE-OUTS: raw material inside a trusted folder (expect 2) --"
check "notes memory/"           2 Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]+'/memory/topic-vocab.md'}))" "$NOTES")"
check "repo memory/"            2 Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]+'/memory/export.md'}))" "$REPO")"
check "_unpacked/ anywhere"     2 Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]+'/corpus/_unpacked/chat.json'}))" "$NOTES")"

echo "-- THE SCRATCH LOCK: main session out, sub-agent in --"
check  "main reads scratch"     2 Read '{"file_path":"/tmp/ingest_body/bundle-1.md"}'
check  "main reads /tmp/rdr"    2 Read '{"file_path":"/tmp/rdr/note.txt"}'
checka "sub-agent reads it"     0 Read '{"file_path":"/tmp/ingest_body/bundle-1.md"}' "agent-xyz"
check  "main cats scratch"      2 Bash '{"command":"cat /tmp/ingest_body/bundle-1.md"}'
checka "sub-agent cats it"      0 Bash '{"command":"cat /tmp/ingest_body/bundle-1.md"}' "agent-xyz"

# -- THE SCRATCH LOCK MUST NOT DEPEND ON A LITERAL LEADING TEMP PATH (added 2026-08-13, S2.1).
# shared/paths.py honours TMPDIR on Unix and TEMP/TMP on Windows, so the scratch dir is already
# /var/folders/.../T/lifehack/... on a Mac and a drive-lettered backslash path on Windows. The
# old patterns matched only a literal leading temp prefix.
# THE FAILURE THAT MATTERS IS NOT A BYPASS -- IT IS THE SANCTIONED PATH BREAKING. The main
# session stayed blocked either way (the external-file arm caught it), but the SUB-AGENT -- the
# tool-less reader this whole split exists to route work to -- stopped being exempt, because the
# exemption lives INSIDE the scratch-lock arm and that arm never matched. Measured 2026-08-13
# against the pre-fix hook: a sub-agent read of a resolved scratch path returned exit 2.
# The contract is now the DIRECTORY NAME, which is stable across platforms.
check  "main reads resolved"      2 Read '{"file_path":"/var/folders/ab/T/lifehack/rdr/cal_1.txt"}'
checka "sub-agent reads resolved" 0 Read '{"file_path":"/var/folders/ab/T/lifehack/rdr/cal_1.txt"}' "agent-xyz"
checka "sub-agent resolved ibody" 0 Read '{"file_path":"/var/folders/ab/T/lifehack/ingest_body/b.md"}' "agent-xyz"
check  "main greps resolved"      2 Bash '{"command":"head /var/folders/ab/T/lifehack/rdr/cal_1.txt"}'
checka "sub-agent heads resolved" 0 Bash '{"command":"head /var/folders/ab/T/lifehack/rdr/cal_1.txt"}' "agent-xyz"
check  "main heads windows shape" 2 Bash '{"command":"head C:\\Users\\s\\AppData\\Local\\Temp\\lifehack\\c\\rdr\\cal_1.txt"}'
# NEGATIVE CONTROLS -- a dir-name match must not degrade into a keyword match. A dir called
# "reader" and a file merely NAMED rdr-something are not the scratch dir; blocking those is the
# false-positive disease this repo has logged four times.
check  "notes dir named reader"   0 Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]+'/state/reader/notes.md'}))" "$NOTES")"
check  "notes file rdr-log.md"    0 Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]+'/state/rdr-log.md'}))" "$NOTES")"

# ⛔ THE FALSE POSITIVE AN ADVERSARIAL AUDIT FOUND, 2026-08-13. The first cut of this fix matched a
# bare */rdr/* -- so ANY trusted folder literally named rdr or ingest_body (a client abbreviated "RDR", a
# renamed reader dir) was denied to the main session. The suite was 54/54 green and MISSED it,
# because the two negative controls tested "reader" and a FILENAME, never a DIRECTORY SEGMENT.
# paths.py always writes under a "lifehack" namespace, so the match is now qualified by it.
check  "trusted dir named rdr"    0 Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]+'/clients/rdr/status.md'}))" "$NOTES")"
check  "trusted dir ingest_body"  0 Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]+'/projects/ingest_body/plan.md'}))" "$NOTES")"
check  "shell reads trusted rdr"  0 Bash "{\"command\":\"grep x $NOTES/clients/rdr/status.md\"}"
# ⛔ AND THE CASE BYPASS, also the audit's: macOS APFS is case-INSENSITIVE, so an upper-cased
# segment reached the real file while never matching a case-sensitive pattern. PRE-EXISTING, not a
# regression -- open on the old literal pattern too. The shell arm is now -i.
check  "main heads UPPER scratch" 2 Bash '{"command":"head /var/folders/ab/T/lifehack/RDR/cal_1.txt"}'
check  "main heads MiXeD scratch" 2 Bash '{"command":"head /var/folders/ab/T/lifehack/Rdr/cal_1.txt"}'



echo "-- SHELL CHANNELS (expect 2) --"
check "skip-variable set"       2 Bash "{\"command\":\"export ${SKV}=1\"}"
check "gmail body read"         2 Bash '{"command":"gws gmail messages read 18abc"}'
check "gmail get full format"   2 Bash '{"command":"gws gmail messages get --params '"'"'{\"id\":\"18abc\",\"format\":\"full\"}'"'"'"}'
check "calendar raw list"       2 Bash '{"command":"gws calendar events list --max 10"}'
check "tasks raw list"          2 Bash '{"command":"gws tasks tasks list --params {}"}'
check "drive export raw"        2 Bash '{"command":"gws drive files export --params {} "}'

echo "-- INSIDE THE TRUSTED ZONE: ordinary work is untouched (expect 0) --"
check "repo .md"                0 Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]+'/README.md'}))" "$REPO")"
check "repo .py"                0 Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]+'/shared/brain_root.py'}))" "$REPO")"
check "repo .sh"                0 Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]+'/system/hooks/pm_flag.sh'}))" "$REPO")"
# A REAL file under a throwaway ~/.claude — deliberately not this machine's own, whose
# settings.json is a symlink pointing out of the tree. Since paths are canonicalised before they
# are compared, a symlink that leads outside the trusted zone resolves outside it, which is the
# safe direction and not what this case is about.
mkdir -p "$NOTES/fakehome/.claude"; printf 'x\n' > "$NOTES/fakehome/.claude/settings.json"
run "harness ~/.claude" 0 "$(j Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]+'/fakehome/.claude/settings.json'}))" "$NOTES")")" HOME="$NOTES/fakehome"
check "notes brief"             0 Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]+'/state/projects/x/brief.md'}))" "$NOTES")"
check "notes, no extension"     0 Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]+'/state/NOTES'}))" "$NOTES")"
check "benign ls"               0 Bash '{"command":"ls -la /tmp"}'
check "gmail LIST is fine"      0 Bash '{"command":"gws gmail messages list --maxResults 5"}'
check "calendar via safe"       0 Bash '{"command":"python3 system/tools/safe_calendar.py {}"}'
check "tasks via safe"          0 Bash '{"command":"python3 system/tools/safe_tasks.py {}"}'
check "drive export via safe"   0 Bash '{"command":"gws drive files export --params {} > /tmp/d.txt && python3 system/tools/safe_read.py /tmp/d.txt"}'
check "unmatched tool"          0 Glob '{"pattern":"**/*.md"}'

echo "-- ⭐ THE SHAPE OF THE ROOT MUST NOT DECIDE WHETHER YOU CAN READ YOUR OWN NOTES --"
# THE BUG THIS BLOCK EXISTS FOR, found on 2026-08-11 by running a real session rather than a
# fixture: the session could not read its own canon. The tool hands this hook the RESOLVED path —
# symlinks followed, doubled slashes collapsed — while the allowlist held whatever string had been
# configured. On macOS that alone is fatal: /tmp and /var ARE symlinks, so a notes folder anywhere
# under either arrives as /private/... and matches nothing.
#
# ⚠ AND HERE IS WHY THE SUITE ABOVE MISSED IT, which is the lesson worth keeping: every case above
# passes the SAME STRING to both sides. Of course it matches. A test that supplies both halves of a
# comparison can only ever prove the comparison is reflexive. These cases hand the hook one form and
# the payload another, which is what actually happens in the wild.
CANON_TARGET="$(python3 -c "import os,sys;print(os.path.realpath(sys.argv[1]+'/state/projects/x/brief.md'))" "$NOTES")"
CANON_PAYLOAD="$(j Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]}))" "$CANON_TARGET")")"

for shape in "trailing slash:$NOTES/" "doubled slash:$NOTES//" "trailing dot:$NOTES/." ; do
  label="${shape%%:*}"; root="${shape#*:}"
  printf '%s' "$CANON_PAYLOAD" | env LIFEHACK_ROOT="$root" bash "$HOOK" >/dev/null 2>&1
  if [ $? = 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL [root with a $label]: own notes were treated as somebody else's"; fi
done

# The symlink case, which is the one macOS creates for you whether you want it or not.
LINKED="$NOTES/linked-notes"
ln -s "$NOTES" "$LINKED" 2>/dev/null
printf '%s' "$CANON_PAYLOAD" | env LIFEHACK_ROOT="$LINKED" bash "$HOOK" >/dev/null 2>&1
if [ $? = 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL [root reached through a symlink]: own notes were treated as somebody else's"; fi

# And the carve-out has to survive the same treatment, or memory/ silently becomes trusted.
MEM_PAYLOAD="$(j Read "$(python3 -c "import json,os,sys;print(json.dumps({'file_path':os.path.realpath(sys.argv[1]+'/memory/topic-vocab.md')}))" "$NOTES")")"
printf '%s' "$MEM_PAYLOAD" | env LIFEHACK_ROOT="$LINKED" bash "$HOOK" >/dev/null 2>&1
if [ $? = 2 ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL [carve-out through a symlinked root]: memory/ became trusted"; fi

echo "-- FAIL-CLOSED: it cannot read its own input (expect 2) --"
printf 'not json at all' | bash "$HOOK" >/dev/null 2>&1
if [ $? = 2 ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL [unparseable]: expected deny"; fi

echo "-- SANITY: a notes root of \$HOME is refused, so it cannot swallow the allowlist --"
# With LIFEHACK_ROOT=$HOME the widening must NOT apply: a file directly in the home directory is
# still external. Without this rail one bad answer at install trusts the entire machine.
printf '%s' "$(j Read "$(python3 -c "import json,os;print(json.dumps({'file_path':os.path.expanduser('~/some-download.md')}))")")" \
  | LIFEHACK_ROOT="$HOME" bash "$HOOK" >/dev/null 2>&1
if [ $? = 2 ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL [\$HOME as notes root]: expected deny"; fi

echo "-- SANITY: NO notes root set at all — no widening, and no crash --"
printf '%s' "$(j Read '{"file_path":"/tmp/a.md"}')" | env -u LIFEHACK_ROOT HOME="$NOTES" bash "$HOOK" >/dev/null 2>&1
if [ $? = 2 ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL [no notes root]: expected deny"; fi

echo ""
echo "RESULT: $pass passed, $fail failed."
[ "$fail" = 0 ] && echo "INGEST GATE GREEN" || exit 1
