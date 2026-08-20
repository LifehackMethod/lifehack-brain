#!/bin/bash
# test_winpath_fold.sh — proves the Windows path-form bridge (system/hooks/lib/winpath_fold.sh)
# actually closes the mismatch reported in GitHub #73 / #77 D1 / #92 item 3, and that it does so
# WITHOUT loosening the trusted-zone boundary. Written on a Mac, which cannot itself run a native
# Windows Python or Git-Bash MSYS shell -- see the file-level note below for exactly what that
# means for what each section can and cannot prove.
#
# Run: bash system/hooks/tests/test_winpath_fold.sh   (exit 0 = all pass)

HOOKDIR="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$HOOKDIR/ingest_gate_enforce.sh"
LIB="$HOOKDIR/lib/winpath_fold.sh"
REPO="${HOOKDIR%/system/hooks}"
[ -f "$LIB" ]  || { echo "CANNOT RUN: no lib at $LIB"; exit 1; }
[ -f "$HOOK" ] || { echo "CANNOT RUN: no hook at $HOOK"; exit 1; }
. "$LIB"

pass=0; fail=0
eq() {  # label · expected · actual
  if [ "$2" = "$3" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL [$1]: expected [$2] got [$3]"; fi
}
match() {  # label · pattern · value  (value must match pattern as a case glob)
  case "$3" in
    $2) pass=$((pass+1)) ;;
    *)  fail=$((fail+1)); echo "  FAIL [$1]: [$3] does not match glob [$2]" ;;
  esac
}
nomatch() {  # label · pattern · value  (value must NOT match pattern)
  case "$3" in
    $2) fail=$((fail+1)); echo "  FAIL [$1]: [$3] WRONGLY matches glob [$2] -- this must stay external" ;;
    *)  pass=$((pass+1)) ;;
  esac
}

echo "-- OFF WINDOWS (force=0): identity, byte for byte -- this is the entire macOS/Linux guarantee --"
eq "posix passthrough"      "/Users/name/Repo"              "$(_winfold "/Users/name/Repo" 0)"
eq "mixed-case passthrough" "/Users/Name/Repo"               "$(_winfold "/Users/Name/Repo" 0)"
eq "backslash left alone"   'C:\Users\name\Repo'             "$(_winfold 'C:\Users\name\Repo' 0)"
eq "empty stays empty"      ""                               "$(_winfold "" 0)"
eq "sentinel untouched"     "/dev/null/no-repo-resolved"     "$(_winfold "/dev/null/no-repo-resolved" 0)"

echo "-- ON WINDOWS (force=1): the exact GitHub #77 D1 repro -- two spellings, one directory --"
# From the issue verbatim:  REPO = /c/AI-Engine (pwd -P)   FP = C:\AI-Engine\...\SKILL.md (Python realpath)
REPO_POSIX='/c/AI-Engine'
FP_NATIVE='C:\AI-Engine\.claude\skills\ingest\SKILL.md'
FOLDED_REPO="$(_winfold "$REPO_POSIX" 1)"
FOLDED_FP="$(_winfold "$FP_NATIVE" 1)"
eq "folded MSYS repo root"   "/c/ai-engine" "$FOLDED_REPO"
eq "folded native file path" "/c/ai-engine/.claude/skills/ingest/skill.md" "$FOLDED_FP"
match "the fixed comparison: FP now falls inside REPO/*" "$FOLDED_REPO/*" "$FOLDED_FP"

echo "-- ON WINDOWS: the boundary guard the fold must NOT weaken --"
# A sibling directory that merely SHARES A PREFIX with the repo root must stay external. This is
# what stops "AI-Engine" matching "AI-Engine-evil" -- the trailing "/*" in every real caller's
# glob is what enforces it; folding case/separators must not create a false positive here.
nomatch "prefix-sibling stays external" "$FOLDED_REPO/*" "$(_winfold '/c/AI-Engine-evil/secrets.md' 1)"
# A path on a DIFFERENT drive must stay external -- folding never invents a match across drives.
nomatch "different drive stays external" "$FOLDED_REPO/*" "$(_winfold 'D:\Somewhere\Else\file.md' 1)"
# A path that is a case-different NON-descendant (not under the root at all) must stay external.
nomatch "unrelated path stays external" "$FOLDED_REPO/*" "$(_winfold 'C:\Users\other\Documents\notes.md' 1)"

echo "-- ON WINDOWS: an in-zone descendant, several path shapes deep, still resolves inside --"
match "nested MSYS-form descendant"   "$FOLDED_REPO/*" "$(_winfold '/c/AI-Engine/system/hooks/ingest_gate_enforce.sh' 1)"
match "nested native-form descendant" "$FOLDED_REPO/*" "$(_winfold 'C:\AI-Engine\system\hooks\ingest_gate_enforce.sh' 1)"

echo "-- INTEGRATION: the real hook, forced into Windows-autodetect via a stubbed uname --"
# This cannot fabricate a genuine native Windows path (there is no Windows Python on this
# machine), so it proves the WIRING instead: once _gate_is_windows() reports true, the hook must
# still ALLOW a real in-repo file and still DENY a real external one, on the paths this machine
# actually has. That is the regression the "extend a test that fails if the gate loosens" ask is
# really after -- confirming the fold, once switched on, does not accidentally open the gate for
# paths it was already denying, or close it for paths it was already allowing.
STUBDIR="$(mktemp -d "${TMPDIR:-/tmp}/winpathfold-stub.XXXXXX")"
trap 'rm -rf "$STUBDIR"' EXIT
cat > "$STUBDIR/uname" << 'EOS'
#!/bin/bash
echo "MINGW64_NT-10.0-19045"
EOS
chmod +x "$STUBDIR/uname"

j() { python3 -c "import json,sys; print(json.dumps({'tool_name':sys.argv[1],'tool_input':json.loads(sys.argv[2])}))" "$1" "$2"; }
irun() {  # label · expected exit · tool · json-input
  local label="$1" exp="$2" got
  printf '%s' "$(j "$3" "$4")" | env PATH="$STUBDIR:$PATH" bash "$HOOK" >/dev/null 2>&1
  got=$?
  if [ "$got" = "$exp" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL [$label]: expected exit $exp, got $got (forced-Windows run)"; fi
}
irun "forced-Windows: in-repo .py still ALLOWED" 0 Read "$(python3 -c "import json,sys;print(json.dumps({'file_path':sys.argv[1]+'/system/hooks/lib/winpath_fold.sh'}))" "$REPO")"
irun "forced-Windows: /tmp external .md still DENIED" 2 Read '{"file_path":"/tmp/a.md"}'
irun "forced-Windows: /tmp external .py (no ext branch) still DENIED" 2 Read '{"file_path":"/tmp/README"}'

echo
echo "RESULT: $pass passed, $fail failed."
[ "$fail" -eq 0 ] && echo "WINPATH FOLD GREEN" || echo "WINPATH FOLD RED"
exit $([ "$fail" -eq 0 ] && echo 0 || echo 1)
