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

echo "-- ⭐ ISSUE #18: Grep/Glob read the same content Read does, and must hit the same gate --"
# The matcher fix that routes these tool calls here at all lives in .claude/settings.json
# (outside this hook's own file, ported/registered by whoever owns that file); these cases
# prove the SCRIPT'S side of the fix: once dispatched here as tool_name Grep/Glob, the gate
# must reason about their 'path' field exactly as it reasons about Read's 'file_path'.
# ⚠ dict(...) here, never a literal {'a':1,'b':2} — a two-key brace literal with a top-level
# comma is exactly the shape bash brace-expansion fires on even inside nested double quotes,
# and it silently split this into two separate one-arg python invocations the first time.
check "Grep on external .pdf"   2 Grep "$(python3 -c "import json;print(json.dumps(dict(pattern='secret',path='/tmp/quarantine-fixture.pdf')))")"
check "Grep on notes memory/"   2 Grep "$(python3 -c "import json,sys;print(json.dumps(dict(pattern='x',path=sys.argv[1]+'/memory/topic-vocab.md')))" "$NOTES")"
check "Glob path in memory/"    2 Glob "$(python3 -c "import json,sys;print(json.dumps(dict(pattern='*',path=sys.argv[1]+'/memory/topic-vocab.md')))" "$NOTES")"
check "Glob path in _unpacked/" 2 Glob "$(python3 -c "import json,sys;print(json.dumps(dict(pattern='*',path=sys.argv[1]+'/corpus/_unpacked/chat.json')))" "$NOTES")"
check "Grep, path in repo"      0 Grep "$(python3 -c "import json,sys;print(json.dumps(dict(pattern='def ',path=sys.argv[1]+'/shared')))" "$REPO")"
check "Glob, path in repo"      0 Glob "$(python3 -c "import json,sys;print(json.dumps(dict(pattern='*.py',path=sys.argv[1]+'/shared')))" "$REPO")"
check "Grep, path in notes"     0 Grep "$(python3 -c "import json,sys;print(json.dumps(dict(pattern='x',path=sys.argv[1]+'/state')))" "$NOTES")"

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
check "Glob, no path (cwd)"     0 Glob '{"pattern":"**/*.md"}'
check "Grep, no path (cwd)"     0 Grep '{"pattern":"TODO"}'

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

echo "-- ⭐ GITHUB #94/#96: notes_root() must fold a Windows path spelling BEFORE testing it --"
# THE BUG (found 2026-08-23): notes_root()'s case guard tested the RAW, UNFOLDED pointer. _winfold
# was only ever applied to NOTES_ROOT one line OUTSIDE the function, on the value the function had
# already returned. A native Windows-spelled pointer (backslash separators, e.g. a drive-letter root
# like D:\Google Drive\AI Brain) never starts with "/", so it fell straight into the `*) return 1`
# catch-all -- BEFORE any fold, and before the "-d" directory check ever ran. Every file under the
# user's own AI Brain then read as EXTERNAL.
#
# ⚠ Reproducing a literal drive-letter root (D:\...) end-to-end needs a real top-level single-letter
# directory, which this sandbox genuinely cannot create -- macOS's sealed system volume refuses new
# entries at "/" even as root (verified live: `mkdir /d` -> "Read-only file system", and
# `sudo -n true` -> a password is required, so root is not available either). This case proves the
# IDENTICAL mechanism -- the fold-before-test ordering inside notes_root() -- with a backslash-
# separated pointer anchored at a REAL directory instead of a synthetic drive letter. The
# drive-letter substring-folding itself is _winfold's own job and is already covered, correctly, by
# test_winpath_fold.sh; what was untested -- and what actually shipped the bug -- is THIS call site.
#
# `uname` is shadowed on PATH to report a Windows kernel, so `_winfold` autodetects real Windows
# behaviour exactly as it would on an actual Windows host, rather than being told to force it.
WINFAKEBIN="$(mktemp -d "${TMPDIR:-/tmp}/winfakebin.XXXXXX")"
trap 'rm -rf "$WINFAKEBIN"' RETURN 2>/dev/null
cat > "$WINFAKEBIN/uname" <<'UNAMEEOF'
#!/bin/sh
echo "MINGW64_NT-10.0"
UNAMEEOF
chmod +x "$WINFAKEBIN/uname"

# ⚠ FIXTURE CASE-SENSITIVITY NOTE. mktemp's XXXXXX draws from a mixed-case alphabet, so the
# directory this test creates can itself land on a MIXED-CASE suffix (e.g. "winroot.Ab3xY9").
# _winfold, once the fake Windows uname above is in effect, lowercases the WHOLE path -- not just
# a drive letter -- so the folded pointer this test feeds to the hook can differ in case from the
# real directory on disk. On a case-INSENSITIVE filesystem (default macOS) that mismatch is
# invisible: the OS resolves "winroot.ab3xy9" and "winroot.Ab3xY9" as the same entry, so
# `[ -d "$_nr" ]` still finds it. On a case-SENSITIVE filesystem (Linux, this project's CI) it is
# a different, nonexistent path, and the case fails for a reason that has nothing to do with the
# fold-ordering bug under test -- this is a fixture defect, not a product defect, and it is what
# made CI red while the same run stayed green on every macOS box (reproduced locally 2026-08-24 by
# running this exact fixture against a real case-sensitive APFS volume). FIX: force the
# directory's own name to be all-lowercase before anything is written under it, so the folded and
# unfolded spellings can never disagree on case regardless of filesystem.
WINDIR="$(mktemp -d "${TMPDIR:-/tmp}/winroot.XXXXXX")"
WINDIR_LOWER="$(dirname "$WINDIR")/$(basename "$WINDIR" | tr 'A-Z' 'a-z')"
if [ "$WINDIR_LOWER" != "$WINDIR" ]; then mv "$WINDIR" "$WINDIR_LOWER"; WINDIR="$WINDIR_LOWER"; fi
mkdir -p "$WINDIR/state"
printf 'hi\n' > "$WINDIR/state/brief.md"
WINDIR_REAL="$(cd "$WINDIR" && pwd -P)"
# Backslash-separated, exactly the shape a native Windows path arrives in -- no drive letter (see
# the note above for why a real one can't be filesystem-proven here), which is the part of the
# spelling that actually decided which branch of the old case statement fired.
WINRAW="$(python3 -c "import sys; print(sys.argv[1].replace('/', chr(92)))" "$WINDIR_REAL")"
WIN_PAYLOAD="$(j Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]}))" "$WINDIR_REAL/state/brief.md")")"
printf '%s' "$WIN_PAYLOAD" | env PATH="$WINFAKEBIN:$PATH" LIFEHACK_ROOT="$WINRAW" bash "$HOOK" >/dev/null 2>&1
if [ $? = 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL [Windows-spelled notes root]: own notes under a Windows-form root read as EXTERNAL"; fi
rm -rf "$WINDIR" "$WINFAKEBIN"

echo "-- ⭐ GITHUB #95: a LINKED WORKTREE with no .brain-root of its own borrows the MAIN worktree's --"
# THE BUG (fixed in commit 23b1797, which added main_worktree_pointer_file() below). `git worktree
# add` materialises only TRACKED files, and .brain-root is deliberately gitignored, so a LINKED
# WORKTREE never gets a pointer of its own -- git will never give it one. Before the fix,
# notes_root() then fell straight through past the repo-pointer route (it simply found nothing at
# $REPO/.brain-root) to the machine-global ~/.config/lifehack/brain-root, which belongs to no repo
# in particular and had gone stale. Reproduced live on 2026-08-21: a session running inside
# .claude/worktrees/<name>/ was DENIED its own brief as somebody else's content. The fix reads
# GIT'S OWN FILES to find the MAIN worktree and borrow ITS .brain-root: this worktree's `.git`
# FILE (a `gitdir:` line), then that gitdir's `commondir` file, which names the shared `.git`
# directory one level below the main worktree's root.
#
# ⚠ WHY THIS IS FABRICATED RATHER THAN A REAL `git worktree add` OF THIS REPO. This repo's own
# .brain-root already exists at the repo root and holds the operator's REAL AI Brain path -- exactly
# the file the task this test was written under says never to touch or read from. A real worktree of
# THIS repo would either (a) borrow that real pointer, so proving ALLOW would mean reading a live
# file out of the operator's actual brain, or (b) require overwriting the real .brain-root for the
# duration of the run, which risks leaving it clobbered if the test aborts partway. Neither is
# acceptable here. So this case builds the identical ON-DISK SHAPE main_worktree_pointer_file()
# actually reads -- and nothing more: a directory holding a `.git` FILE whose `gitdir:` line names a
# directory holding a `commondir` file whose first line names a directory that is literally called
# `.git`, one level above which sits a `.brain-root` this test owns end to end. That function never
# shells out to git (by design -- a gate must not depend on git being on PATH, or pay a subprocess on
# every tool call); it is two `head -n1`s, a suffix check and a `cd`. Faking the shape exercises the
# exact same lines a real linked worktree would drive, with no git porcelain involved on either side.
WTROOT="$(mktemp -d "${TMPDIR:-/tmp}/gatetest-wt.XXXXXX")"
MAINWT="$WTROOT/main"; LINKWT="$WTROOT/linked"; GITDIR="$WTROOT/linked-gitdir"; WTNOTES="$WTROOT/notes"
mkdir -p "$MAINWT/.git" "$LINKWT/system/hooks/lib" "$GITDIR" "$WTNOTES/state"
printf 'hi\n' > "$WTNOTES/state/brief.md"
printf '%s' "$WTNOTES" > "$MAINWT/.brain-root"           # the MAIN worktree's own declared brain
printf 'gitdir: %s\n' "$GITDIR" > "$LINKWT/.git"          # the linked worktree's pointer to its gitdir
printf '%s\n' "$MAINWT/.git" > "$GITDIR/commondir"        # that gitdir's pointer back to the shared .git
cp "$HOOK" "$LINKWT/system/hooks/ingest_gate_enforce.sh"
cp "$HOOKDIR/lib/winpath_fold.sh" "$LINKWT/system/hooks/lib/winpath_fold.sh"
WT_PAYLOAD="$(j Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]}))" "$WTNOTES/state/brief.md")")"
printf '%s' "$WT_PAYLOAD" | env -u LIFEHACK_ROOT bash "$LINKWT/system/hooks/ingest_gate_enforce.sh" >/dev/null 2>&1
if [ $? = 0 ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL [linked worktree borrows main's brain]: own notes read as EXTERNAL from inside a linked worktree"; fi
rm -rf "$WTROOT"

echo "-- ⭐ INGEST-GATE-WORKTREE-FIX-CARD: trust by the TARGET FILE's own git identity, never by \$0 --"
# THE BUG (INGEST-GATE-WORKTREE-FIX-CARD.md, 2026-09-16): \$REPO is derived from wherever *this
# script* happens to be invoked from (\$0), never from what repo the session is actually working in.
# A session running inside a linked worktree, with the plugin ALSO registering this same hook from
# the (non-git) plugin cache, gets denied its OWN repo's tracked files as somebody else's document --
# the plugin-cache copy's \$0 can never be the worktree, no matter how worktree-aware the logic
# inside the script becomes. This suite's own \$HOOK may or may not itself sit inside a git repo
# depending on which checkout runs it; every case below builds its OWN synthetic Harness checkout,
# deliberately separate from \$REPO/\$HOOKDIR, so a pass proves the NEW cross-repo route fired, not
# the ordinary \$REPO allow.
#
# Real, disposable \`git init\`/\`git worktree add\`, fully disconnected from this repo's own git
# history -- unlike the #95 fixture above (which fakes the .git-file SHAPE precisely to avoid a git
# subprocess on every call), the new route here only runs \`git\` on the deny path, so there is no
# reason to fake it and a real repo/worktree is more faithful to what is actually being proven.
WTFROOT="$(mktemp -d "${TMPDIR:-/tmp}/gatetest-wtfix.XXXXXX")"
CANON_ORIGIN="https://github.com/LifehackMethod/lifehack-brain.git"

# An outside target that exists BEFORE any symlink points at it, so realpath resolves cleanly.
OUTSIDE_TARGET="$WTFROOT/outside-file.md"
printf 'outside\n' > "$OUTSIDE_TARGET"

MAINCLONE="$WTFROOT/main-clone"
mkdir -p "$MAINCLONE/system/hooks" "$MAINCLONE/system/register" "$MAINCLONE/docs"
git -C "$MAINCLONE" init -q
git -C "$MAINCLONE" config user.email "test@example.com"
git -C "$MAINCLONE" config user.name "test"
# ⭐ LEAD REVIEW (2026-09-17): the canonical-remote check means every legitimate positive case below
# needs this origin configured -- worktrees share their main clone's config, so setting it once here
# covers the worktree created from this clone too.
git -C "$MAINCLONE" remote add origin "$CANON_ORIGIN"
cp "$HOOK" "$MAINCLONE/system/hooks/ingest_gate_enforce.sh"
printf '{}\n' > "$MAINCLONE/system/register/register.jsonl"
printf '# CLAUDE\n' > "$MAINCLONE/CLAUDE.md"
printf 'tracked note\n' > "$MAINCLONE/docs/note.md"
# A tracked symlink pointing to ANOTHER TRACKED FILE inside this same repo (relative target, same
# dir) -- proves a legitimate in-repo alias is not collateral damage from the new escape check.
ln -s note.md "$MAINCLONE/docs/alias-inside.md"
# A tracked symlink pointing OUTSIDE the repo entirely -- git only ever tracks the symlink's own
# path; nothing here validates where it leads, which is exactly what the new escape check must.
ln -s "$OUTSIDE_TARGET" "$MAINCLONE/docs/alias-outside.md"
git -C "$MAINCLONE" add -A
git -C "$MAINCLONE" commit -q -m "seed"

# A REAL linked worktree of MAINCLONE -- \`git worktree add\` materialises only TRACKED files.
HARNESSWT="$WTFROOT/harness-worktree"
git -C "$MAINCLONE" worktree add -q "$HARNESSWT" -b gatetest-wtfix-branch >/dev/null 2>&1
# An UNTRACKED file, dropped straight onto the worktree's disk -- never part of the repo's history.
printf 'untracked note\n' > "$HARNESSWT/docs/dropped-in.md"
# An UNTRACKED symlink pointing outside -- distinct from the TRACKED case below: this one is already
# caught by the tracked-files-only check alone, whatever the escape check does.
ln -s "$OUTSIDE_TARGET" "$HARNESSWT/docs/points-outside-untracked.md"

TRACKED_PAYLOAD="$(j Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]}))" "$HARNESSWT/docs/note.md")")"
UNTRACKED_PAYLOAD="$(j Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]}))" "$HARNESSWT/docs/dropped-in.md")")"
ALIAS_INSIDE_PAYLOAD="$(j Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]}))" "$HARNESSWT/docs/alias-inside.md")")"
ALIAS_OUTSIDE_PAYLOAD="$(j Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]}))" "$HARNESSWT/docs/alias-outside.md")")"
UNTRACKED_SYMLINK_PAYLOAD="$(j Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]}))" "$HARNESSWT/docs/points-outside-untracked.md")")"

run "worktree: tracked file, plugin-copy hook -> ALLOW"          0 "$TRACKED_PAYLOAD"
run "worktree: UNTRACKED file, same worktree -> gated"           2 "$UNTRACKED_PAYLOAD"
run "worktree: tracked symlink -> tracked file inside -> ALLOW"  0 "$ALIAS_INSIDE_PAYLOAD"
run "worktree: tracked symlink -> outside the repo -> gated"     2 "$ALIAS_OUTSIDE_PAYLOAD"
run "worktree: UNTRACKED symlink -> outside -> gated"            2 "$UNTRACKED_SYMLINK_PAYLOAD"

# A real git repo that is NOT a recognized Harness checkout (missing the 3 required files).
OTHERREPO="$WTFROOT/other-repo"
mkdir -p "$OTHERREPO/docs"
git -C "$OTHERREPO" init -q
git -C "$OTHERREPO" config user.email "test@example.com"
git -C "$OTHERREPO" config user.name "test"
git -C "$OTHERREPO" remote add origin "$CANON_ORIGIN"
printf 'hi\n' > "$OTHERREPO/docs/note.md"
git -C "$OTHERREPO" add -A
git -C "$OTHERREPO" commit -q -m "seed"
OTHER_PAYLOAD="$(j Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]}))" "$OTHERREPO/docs/note.md")")"
run "non-Harness git repo (tracked, wrong shape) -> gated" 2 "$OTHER_PAYLOAD"

# A path outside any repo whatsoever.
NOREPODIR="$WTFROOT/plain-dir"
mkdir -p "$NOREPODIR"
printf 'hi\n' > "$NOREPODIR/note.txt"
NOREPO_PAYLOAD="$(j Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]}))" "$NOREPODIR/note.txt")")"
run "path outside any repo -> gated"                        2 "$NOREPO_PAYLOAD"

echo "-- ⭐ LEAD REVIEW 2026-09-17: shape alone is spoofable -- the origin must be the canonical remote --"
# A hostile repo with the EXACT 3-file shape (a lookalike deliberately mimicking the layout) but an
# origin that is NOT the canonical Harness remote.
HOSTILE="$WTFROOT/hostile-lookalike"
mkdir -p "$HOSTILE/system/hooks" "$HOSTILE/system/register" "$HOSTILE/docs"
git -C "$HOSTILE" init -q
git -C "$HOSTILE" config user.email "test@example.com"
git -C "$HOSTILE" config user.name "test"
git -C "$HOSTILE" remote add origin "https://github.com/evil/lifehack-brain-lookalike.git"
cp "$HOOK" "$HOSTILE/system/hooks/ingest_gate_enforce.sh"
printf '{}\n' > "$HOSTILE/system/register/register.jsonl"
printf '# CLAUDE\n' > "$HOSTILE/CLAUDE.md"
printf 'hostile note\n' > "$HOSTILE/docs/note.md"
git -C "$HOSTILE" add -A
git -C "$HOSTILE" commit -q -m "seed"
HOSTILE_PAYLOAD="$(j Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]}))" "$HOSTILE/docs/note.md")")"
run "hostile lookalike (right shape, wrong origin) -> gated"      2 "$HOSTILE_PAYLOAD"

# Same shape, but NO remote configured at all -- must fall to gated, never trust by absence.
NOREMOTE="$WTFROOT/no-remote"
mkdir -p "$NOREMOTE/system/hooks" "$NOREMOTE/system/register" "$NOREMOTE/docs"
git -C "$NOREMOTE" init -q
git -C "$NOREMOTE" config user.email "test@example.com"
git -C "$NOREMOTE" config user.name "test"
cp "$HOOK" "$NOREMOTE/system/hooks/ingest_gate_enforce.sh"
printf '{}\n' > "$NOREMOTE/system/register/register.jsonl"
printf '# CLAUDE\n' > "$NOREMOTE/CLAUDE.md"
printf 'no-remote note\n' > "$NOREMOTE/docs/note.md"
git -C "$NOREMOTE" add -A
git -C "$NOREMOTE" commit -q -m "seed"
NOREMOTE_PAYLOAD="$(j Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]}))" "$NOREMOTE/docs/note.md")")"
run "right shape, NO remote at all -> gated"                      2 "$NOREMOTE_PAYLOAD"

# The ssh-form origin, which must be accepted exactly like the https form.
SSHREPO="$WTFROOT/ssh-origin-repo"
mkdir -p "$SSHREPO/system/hooks" "$SSHREPO/system/register" "$SSHREPO/docs"
git -C "$SSHREPO" init -q
git -C "$SSHREPO" config user.email "test@example.com"
git -C "$SSHREPO" config user.name "test"
git -C "$SSHREPO" remote add origin "git@github.com:LifehackMethod/lifehack-brain.git"
cp "$HOOK" "$SSHREPO/system/hooks/ingest_gate_enforce.sh"
printf '{}\n' > "$SSHREPO/system/register/register.jsonl"
printf '# CLAUDE\n' > "$SSHREPO/CLAUDE.md"
printf 'ssh note\n' > "$SSHREPO/docs/note.md"
git -C "$SSHREPO" add -A
git -C "$SSHREPO" commit -q -m "seed"
SSH_PAYLOAD="$(j Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]}))" "$SSHREPO/docs/note.md")")"
run "ssh-form canonical origin (git@github.com:...) -> ALLOW"    0 "$SSH_PAYLOAD"

git -C "$MAINCLONE" worktree remove --force "$HARNESSWT" >/dev/null 2>&1
rm -rf "$WTFROOT"
# The plugin cache's own files (no .git at all) must stay UNCHANGED by all of the above -- the
# existing "external .txt"/"external .md"/"external no extension" cases earlier in this suite
# already prove that end to end and are left unmodified; their tally is part of the RESULT below.

echo ""
echo "RESULT: $pass passed, $fail failed."
[ "$fail" = 0 ] && echo "INGEST GATE GREEN" || exit 1
