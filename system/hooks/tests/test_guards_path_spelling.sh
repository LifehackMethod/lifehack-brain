#!/bin/bash
# test_guards_path_spelling.sh — proves that every Write/Edit-matched guard in this plane gives the
# SAME VERDICT to the same logical file, no matter which of the two spellings Windows hands it in:
# native backslash-drive form (`C:\Users\name\Repo\...`) or the MSYS/Git-Bash POSIX form a guard's
# own `pwd -P` produces (`/c/users/name/repo/...`). This is the bug lib/winpath_fold.{sh,py} exists
# to close (see their headers, and GitHub #73 / #77 D1 / #92 item 3): a guard that classifies a
# path with a forward-slash-only test (`"/canon/" in path`, `case "$x" in "$root"/*)`, ...) silently
# enforces NOTHING on a backslash-native path, while the identical file spelled the other way is
# correctly caught. Two spellings of one file getting two different verdicts from the same guard is
# the exact defect class this file exists to catch, and it is what makes carrying a per-guard
# winpath_fold call safe going forward: if a future edit ever drops one, or a new guard ships
# without it, this file goes RED and names the guard.
#
# WHAT THIS PROVES: for a fixture path/content pair each guard demonstrably cares about, the same
# guard invoked twice -- once with the fixture spelled native-backslash, once spelled MSYS-POSIX --
# returns the SAME exit code and the SAME "did it say anything" (stdout+stderr non-empty) signal.
# LIFEHACK_WINFOLD_FORCE=1 is exported for BOTH runs, so the only variable between them is the
# spelling itself -- not whether autodetection thinks it is on Windows -- and the comparison is
# meaningful on a Linux CI runner too, where the fold would otherwise be a no-op.
#
# WHAT THIS CANNOT PROVE: that a guard's classification is CORRECT (only that it is CONSISTENT
# between spellings), and it cannot drive a guard that needs session/window state this harness has
# no way to fake convincingly -- those rows are marked SKIP, loudly, with a reason, and still count
# toward the completeness check below so a skipped guard can never quietly vanish from the table.
#
# COMPLETENESS: this file also parses .claude/settings.json itself and fails if any Write/Edit
# PreToolUse hook is not represented below by name -- a guard added to the plane without a row here
# is a guard this test cannot vouch for, and that must be loud, not a silent gap.
#
# Run: bash system/hooks/tests/test_guards_path_spelling.sh   (exit 0 = all pass, no fails)

set -u
HOOKDIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO="${HOOKDIR%/system/hooks}"
SETTINGS="$REPO/.claude/settings.json"
[ -d "$HOOKDIR" ]  || { echo "CANNOT RUN: no hook dir at $HOOKDIR"; exit 1; }
[ -f "$SETTINGS" ] || { echo "CANNOT RUN: no settings at $SETTINGS"; exit 1; }

# MSYS_NO_PATHCONV: see test_winpath_fold_parity.sh for the full explanation of the underlying Git
# Bash argv-conversion gotcha. ⛔ DELIBERATELY *NOT* EXPORTED GLOBALLY HERE, and that is the
# opposite of file 1 -- because guard_write_paths.sh and guard_organism_map.sh RESOLVE THEIR OWN
# REPO ROOT through a `python3 -c "...os.path.realpath(sys.argv[1])..." "$REPO"` call, where $REPO
# is itself a POSIX path handed to native python3.exe on argv. In REAL production use that call only
# resolves correctly BECAUSE Git Bash's automatic conversion rewrites it to a native path first --
# so disabling that conversion for the guard's own invocation would break the very thing being
# tested, and produce a mismatch that has nothing to do with the fold. It is scoped instead to just
# the one place THIS file needs it: `mkpayload`'s python3 call, below, where a POSIX fixture path
# must survive on argv WITHOUT being silently rewritten to native spelling first (that would erase
# the "posix spelling" half of every comparison before the guard ever saw it).

pass=0; fail=0; skip=0
SKIP_REASONS=()
eq() {  # label · expected · actual
  if [ "$2" = "$3" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL [$1]: expected [$2] got [$3]"; fi
}
note_skip() {  # label · reason
  skip=$((skip+1))
  SKIP_REASONS+=("$1 -- $2")
  echo "  SKIP [$1]: $2"
}

# ── sandbox HOME, so any guard that reads \$HOME (pm/plan/throughline flags, ack files) never
# touches the real one. Cleaned up on exit no matter how this script ends.
SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/guard-spelling-sandbox.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
export HOME="$SANDBOX/home"
mkdir -p "$HOME"

# ── to_native / to_fwd_drive: POSIX path -> Windows form, via `cygpath` -- NOT hand-rolled string
# surgery. A hand-rolled `/X/...` -> `X:\...` substitution only understands an actual DRIVE-LETTER
# mount (`/c/...`) and silently no-ops on anything else, INCLUDING a plain MSYS mount alias like
# `/tmp/...` (which is exactly what `mktemp -d "${TMPDIR:-/tmp}/..."` below produces) -- so a
# first draft of this file built its sandbox fixtures under /tmp, hand-converted them, got the
# SAME STRING BACK for both "native" and "posix" spellings, and every comparison trivially agreed
# regardless of whether the guard being tested had the fold or not. That is a FALSE PASS, the
# worktree's own opening warning by another name ("winpath_fold reconciles drive letters but not
# mount aliases"), and it would have shipped a suite that could not catch the bug it exists to
# catch. `cygpath` (part of the Git-for-Windows toolchain this whole plane already depends on)
# resolves the ACTUAL underlying path for ANY mount, alias included, which is why it replaces the
# hand-rolled version here rather than living beside it as a special case.
#   to_native "/tmp/x/y.md"        -> C:\Users\name\AppData\Local\Temp\x\y.md
#   to_fwd_drive "/tmp/x/y.md"     -> C:/Users/name/AppData/Local/Temp/x/y.md
# ⛔ DO NOT turn this back into a hard `exit 1`. This suite has TWO TIERS and only the second
# needs cygpath:
#   TIER 1, the completeness check -- reads .claude/settings.json only. Runs EVERYWHERE, and it
#           is the tier that stops this whole class of bug returning, because it fails the build
#           when a newly registered Write/Edit guard has no row in the table below.
#   TIER 2, the spelling comparisons -- needs a REAL native Windows path for each fixture, which
#           means cygpath, which means Windows. It cannot be faked: a hand-rolled converter
#           silently no-ops on mount aliases like /tmp, so both "spellings" come out identical
#           and every comparison passes against itself. That false pass is worse than no test.
# Off Windows, tier 2 SKIPS LOUDLY and the run exits 0. A CI that goes red on every commit gets
# added to a skip list and then ignored, which costs more than the coverage it was protecting.
HAVE_CYGPATH=1
[ -x "$(command -v cygpath 2>/dev/null)" ] || HAVE_CYGPATH=0
to_native()    { cygpath -w "$1"; }
to_fwd_drive() { cygpath -m "$1"; }

# ── mkpayload: build the JSON tool-call payload with python3 -c + json.dumps, ALWAYS -- a
# hand-written JSON string containing a native Windows path's backslashes will not parse and would
# hand this test a false pass (the whole payload silently becomes __PARSE_ERROR__ input, which most
# guards then fail closed on for BOTH spellings alike, masking the very asymmetry being tested for).
# Usage: mkpayload <tool_name> <key1> <val1> [<key2> <val2> ...]
mkpayload() {
  local tool="$1"; shift
  MSYS_NO_PATHCONV=1 python3 -c "
import json, sys
tool = sys.argv[1]
rest = sys.argv[2:]
d = {}
it = iter(rest)
for k in it:
    v = next(it)
    d[k] = v
sys.stdout.write(json.dumps({'tool_name': tool, 'tool_input': d}))
" "$tool" "$@"
}

# ── run_guard: invoke one guard with one JSON payload on stdin. Sets RC and OUT (stdout+stderr,
# combined -- the completeness assertion in the brief is "non-empty output", and several of these
# guards' deny messages land on stderr while a couple of allow-path notices land on stdout, so the
# two channels are merged rather than picking one and silently missing the other).
run_guard() {  # guard_script · payload
  OUT="$(printf '%s' "$2" | LIFEHACK_WINFOLD_FORCE=1 bash "$1" 2>&1)"
  RC=$?
}

# ── compare_spelling: the core assertion. Runs ONE guard against the SAME logical fixture spelled
# two ways and requires the SAME verdict: same exit code, same "said something or stayed silent".
# label · guard_relpath · payload_native · payload_posix
compare_spelling() {
  local label="$1" guard="$HOOKDIR/$2" payload_native="$3" payload_posix="$4"
  [ -f "$guard" ] || { fail=$((fail+1)); echo "  FAIL [$label]: guard script missing at $guard"; return; }

  run_guard "$guard" "$payload_native"
  local rc_native="$RC" nonempty_native="0"
  [ -n "$OUT" ] && nonempty_native="1"
  local out_native="$OUT"

  run_guard "$guard" "$payload_posix"
  local rc_posix="$RC" nonempty_posix="0"
  [ -n "$OUT" ] && nonempty_posix="1"
  local out_posix="$OUT"

  if [ "$rc_native" = "$rc_posix" ] && [ "$nonempty_native" = "$nonempty_posix" ]; then
    pass=$((pass+1))
  else
    fail=$((fail+1))
    echo "  FAIL [$label]: native-spelling -> exit $rc_native, output-nonempty=$nonempty_native"
    echo "                  posix-spelling  -> exit $rc_posix, output-nonempty=$nonempty_posix"
    echo "                  SAME FILE, TWO SPELLINGS, TWO VERDICTS -- a forward-slash-only path test."
    echo "                  native output: $(printf '%s' "$out_native" | head -c 300)"
    echo "                  posix  output: $(printf '%s' "$out_posix"  | head -c 300)"
  fi
}

echo "══════════════════════════════════════════════════════════════════════"
echo "COMPLETENESS CHECK — every Write/Edit PreToolUse hook must have a row below"
echo "══════════════════════════════════════════════════════════════════════"
# The ten names this file is REQUIRED to cover, independent of what settings.json says today --
# so that if a hook is ever REMOVED from settings.json without its row here being reconsidered,
# the mismatch is still visible (a name below with no matching hook is exactly as loud as the
# reverse). Cross-checked BOTH directions against the live registration.
REQUIRED_GUARDS=(
  guard_write_paths.sh
  enforce_skill_frontmatter.sh
  guard_canon_write.sh
  guard_cross_project_write.sh
  guard_throughline_write_scope.sh
  guard_ledger_discipline.sh
  guard_findings_write.sh
  guard_pm_flag_store.sh
  enforce_multiphase_contract.sh
  guard_organism_map.sh
)

# Content read into an env var, not handed to python3 as a path on argv or via a heredoc's stdin
# (which would collide with an actual `< file` redirect on the same command). With
# MSYS_NO_PATHCONV=1 set above, a POSIX absolute path like "$SETTINGS" would reach the native
# python3.exe UNCONVERTED and unopenable (Windows has no notion of an "/c/..." mount prefix) -- the
# same trap the parity test hit with the library path itself. A single-quoted heredoc ('PY') is
# used for the script itself so bash never touches the regex's backslashes or dollar signs --
# double-quoting that regex earlier corrupted `\$?` into a bare `$?`, which Python's re rejects
# ("nothing to repeat").
SETTINGS_JSON="$(cat "$SETTINGS")"
export SETTINGS_JSON
LIVE_GUARDS="$(python3 <<'PY'
import json, os, re
d = json.loads(os.environ["SETTINGS_JSON"])
names = []
for entry in d.get('hooks', {}).get('PreToolUse', []):
    matcher = entry.get('matcher', '') or ''
    if 'Write' not in matcher and 'Edit' not in matcher:
        continue
    for h in entry.get('hooks', []):
        cmd = h.get('command', '') or ''
        m = re.search(r'([A-Za-z0-9_.-]+\.sh)"?\s*$', cmd.strip())
        if m:
            names.append(m.group(1))
print('\n'.join(names))
PY
)"
# The native Windows python3.exe text-mode stdout translates each '\n' it writes to '\r\n', even
# through a pipe -- so every name above arrived with a trailing \r glued on, and ONLY the very last
# one (where command substitution's own trailing-newline strip happens to eat the final \r\n as a
# pair) would ever string-compare equal to its REQUIRED_GUARDS entry. Strip defensively rather than
# rely on Python-side newline settings that vary by version.
LIVE_GUARDS="$(printf '%s' "$LIVE_GUARDS" | tr -d '\r')"

# ⛔ AN EMPTY PARSE IS A BROKEN TEST, NOT A CLEAN REPO. Found while exercising this suite under a
# stripped PATH where python3 was present but non-functional: it wrote nothing, LIVE_GUARDS came
# back empty, and the two directions below then disagreed in the most misleading way available --
# "settings->table" passed VACUOUSLY (an empty list satisfies "every registered guard has a row"),
# while "table->settings" failed and blamed settings.json for having dropped all ten guards. A
# reader would go and look at settings.json, which is fine, and never suspect the parser. Refuse
# outright instead: if the repo genuinely registered zero Write/Edit guards, that is itself a thing
# this suite must shout about, so there is no case where continuing is correct.
if [ -z "$LIVE_GUARDS" ]; then
  fail=$((fail+1))
  echo "  FAIL [completeness]: parsed ZERO Write/Edit guards out of .claude/settings.json."
  echo "                  This is almost certainly a broken python3 or an unreadable settings file,"
  echo "                  NOT a repo with no guards. Both completeness directions are meaningless"
  echo "                  against an empty list -- one of them would pass vacuously -- so this"
  echo "                  refuses rather than reporting either."
  echo "                  CHECK: python3 -c 'import json' and that .claude/settings.json parses."
  echo
  echo "RESULT: $pass passed, $fail failed, $skip skipped."
  echo "GUARD PATH-SPELLING RED"
  exit 1
fi

MISSING_FROM_TABLE=""
while IFS= read -r g; do
  [ -n "$g" ] || continue
  found=0
  for r in "${REQUIRED_GUARDS[@]}"; do [ "$r" = "$g" ] && found=1 && break; done
  [ "$found" = "1" ] || MISSING_FROM_TABLE="$MISSING_FROM_TABLE $g"
done <<EOF
$LIVE_GUARDS
EOF

MISSING_FROM_SETTINGS=""
for r in "${REQUIRED_GUARDS[@]}"; do
  found=0
  while IFS= read -r g; do [ "$g" = "$r" ] && found=1 && break; done <<EOF
$LIVE_GUARDS
EOF
  [ "$found" = "1" ] || MISSING_FROM_SETTINGS="$MISSING_FROM_SETTINGS $r"
done

if [ -n "$MISSING_FROM_TABLE" ]; then
  fail=$((fail+1))
  echo "  FAIL [completeness]: .claude/settings.json registers a Write/Edit guard with NO fixture"
  echo "                        row in this file:$MISSING_FROM_TABLE"
  echo "                        A path-spelling row is required for each of these."
else
  pass=$((pass+1))
  echo "  PASS [completeness, settings->table]: every registered Write/Edit guard has a row here."
fi

if [ -n "$MISSING_FROM_SETTINGS" ]; then
  fail=$((fail+1))
  echo "  FAIL [completeness]: this file expects a guard no longer registered in settings.json:$MISSING_FROM_SETTINGS"
else
  pass=$((pass+1))
  echo "  PASS [completeness, table->settings]: every guard this file expects is still registered."
fi

# ── TIER 2 GATE ────────────────────────────────────────────────────────────────────────────────
# Everything below needs a real native Windows path per fixture. Where cygpath is absent we cannot
# build one honestly, so we say so and stop -- exit 0, because the completeness check above DID run
# and DID assert something real. The skip count is reported in the RESULT line like any other, so
# "skipped" can never be mistaken for "passed" by a human or by a log scraper.
if [ "$HAVE_CYGPATH" -eq 0 ]; then
  skip=$(( skip + ${#REQUIRED_GUARDS[@]} ))
  echo
  echo "══════════════════════════════════════════════════════════════════════"
  echo "SKIPPED — the path-spelling comparisons need cygpath, which is not on this host."
  echo "══════════════════════════════════════════════════════════════════════"
  echo "  WHAT RAN:     the completeness check above. Every Write/Edit guard registered in"
  echo "                .claude/settings.json has a fixture row here, and vice versa. That is the"
  echo "                assertion that keeps a newly added guard from shipping unprotected."
  echo "  WHAT SKIPPED: ${#REQUIRED_GUARDS[@]} per-guard spelling comparisons."
  echo "  WHY:          each fixture needs the SAME file spelled two ways, one of them a real native"
  echo "                Windows path. cygpath is the only thing here that produces one correctly for"
  echo "                any mount, alias included. A hand-rolled converter no-ops on /tmp, so both"
  echo "                spellings come out identical and every comparison passes against itself --"
  echo "                a false pass, and worse than skipping."
  echo "  TO RUN THEM:  run this suite on Windows with Git Bash."
  echo
  echo "RESULT: $pass passed, $fail failed, $skip skipped."
  [ "$fail" -eq 0 ] && echo "GUARD PATH-SPELLING GREEN (spelling tier skipped, completeness tier ran)" \
                    || echo "GUARD PATH-SPELLING RED"
  exit $([ "$fail" -eq 0 ] && echo 0 || echo 1)
fi

echo
echo "══════════════════════════════════════════════════════════════════════"
echo "guard_write_paths.sh — CONTROL: already folds. Own-hook-tree write must deny, both spellings."
echo "══════════════════════════════════════════════════════════════════════"
GWP_TARGET_POSIX="$REPO/system/hooks/fake_guard_for_spelling_test.sh"
GWP_TARGET_NATIVE="$(to_native "$GWP_TARGET_POSIX")"
GWP_TARGET_FWD="$(to_fwd_drive "$GWP_TARGET_NATIVE")"
compare_spelling "guard_write_paths.sh" "guard_write_paths.sh" \
  "$(mkpayload Write file_path "$GWP_TARGET_NATIVE" content "echo hi")" \
  "$(mkpayload Write file_path "$GWP_TARGET_FWD"     content "echo hi")"

echo
echo "══════════════════════════════════════════════════════════════════════"
echo "guard_organism_map.sh — CONTROL: already folds. Full-content Write of manual.md must deny."
echo "══════════════════════════════════════════════════════════════════════"
GOM_TARGET_POSIX="$REPO/system/organism/manual.md"
GOM_TARGET_NATIVE="$(to_native "$GOM_TARGET_POSIX")"
GOM_TARGET_FWD="$(to_fwd_drive "$GOM_TARGET_NATIVE")"
compare_spelling "guard_organism_map.sh" "guard_organism_map.sh" \
  "$(mkpayload Write file_path "$GOM_TARGET_NATIVE" content "# replaced whole file")" \
  "$(mkpayload Write file_path "$GOM_TARGET_FWD"     content "# replaced whole file")"

echo
echo "══════════════════════════════════════════════════════════════════════"
echo "enforce_skill_frontmatter.sh — SKILL.md with NO frontmatter must deny, both spellings."
echo "══════════════════════════════════════════════════════════════════════"
ESF_TARGET_POSIX="$REPO/.claude/skills/spelling-test-skill/SKILL.md"
ESF_TARGET_NATIVE="$(to_native "$ESF_TARGET_POSIX")"
ESF_CONTENT="no frontmatter block here at all, just prose"
compare_spelling "enforce_skill_frontmatter.sh" "enforce_skill_frontmatter.sh" \
  "$(mkpayload Write file_path "$ESF_TARGET_NATIVE" content "$ESF_CONTENT")" \
  "$(mkpayload Write file_path "$ESF_TARGET_POSIX"  content "$ESF_CONTENT")"

echo
echo "══════════════════════════════════════════════════════════════════════"
echo "enforce_multiphase_contract.sh — phase driver with NO Output contract must deny."
echo "══════════════════════════════════════════════════════════════════════"
EMC_TARGET_POSIX="$REPO/.claude/skills/spelling-test-skill/prompts/01-phase-one.md"
EMC_TARGET_NATIVE="$(to_native "$EMC_TARGET_POSIX")"
EMC_CONTENT="# Phase 1: Do The Thing
This driver declares a phase but has no Output contract section anywhere in it."
compare_spelling "enforce_multiphase_contract.sh" "enforce_multiphase_contract.sh" \
  "$(mkpayload Write file_path "$EMC_TARGET_NATIVE" content "$EMC_CONTENT")" \
  "$(mkpayload Write file_path "$EMC_TARGET_POSIX"  content "$EMC_CONTENT")"

echo
echo "══════════════════════════════════════════════════════════════════════"
echo "guard_canon_write.sh — canon write over the 3200-char size rail must deny."
echo "══════════════════════════════════════════════════════════════════════"
GCW_TARGET_POSIX="$SANDBOX/notes/state/projects/spelltest/canon/current.md"
GCW_TARGET_NATIVE="$(to_native "$GCW_TARGET_POSIX")"
GCW_CONTENT="$(python3 -c "print('x' * 3300)")"
compare_spelling "guard_canon_write.sh" "guard_canon_write.sh" \
  "$(mkpayload Write file_path "$GCW_TARGET_NATIVE" content "$GCW_CONTENT")" \
  "$(mkpayload Write file_path "$GCW_TARGET_POSIX"  content "$GCW_CONTENT")"

echo
echo "══════════════════════════════════════════════════════════════════════"
echo "guard_pm_flag_store.sh — direct write under ~/.claude/run/pm/ must deny."
echo "══════════════════════════════════════════════════════════════════════"
GPF_TARGET_POSIX="$HOME/.claude/run/pm/pm-spelltest.flag"
GPF_TARGET_NATIVE="$(to_native "$GPF_TARGET_POSIX")"
compare_spelling "guard_pm_flag_store.sh" "guard_pm_flag_store.sh" \
  "$(mkpayload Write file_path "$GPF_TARGET_NATIVE" content "doc_path=/tmp/x")" \
  "$(mkpayload Write file_path "$GPF_TARGET_POSIX"  content "doc_path=/tmp/x")"

echo
echo "══════════════════════════════════════════════════════════════════════"
echo "guard_ledger_discipline.sh — appending a status-annotation to ## Open must deny."
echo "══════════════════════════════════════════════════════════════════════"
GLD_TARGET_POSIX="$SANDBOX/notes/state/debt-ledger.md"
GLD_TARGET_NATIVE="$(to_native "$GLD_TARGET_POSIX")"
GLD_CONTENT="## Open
- some old debt item, now marked done ✅ RESOLVED in place
## Cleared
"
compare_spelling "guard_ledger_discipline.sh" "guard_ledger_discipline.sh" \
  "$(mkpayload Write file_path "$GLD_TARGET_NATIVE" content "$GLD_CONTENT")" \
  "$(mkpayload Write file_path "$GLD_TARGET_POSIX"  content "$GLD_CONTENT")"

echo
echo "══════════════════════════════════════════════════════════════════════"
echo "guard_findings_write.sh — a hand-authored write into state/findings/ must deny."
echo "══════════════════════════════════════════════════════════════════════"
GFW_TARGET_POSIX="$SANDBOX/notes/state/findings/hand-authored.jsonl"
GFW_TARGET_NATIVE="$(to_native "$GFW_TARGET_POSIX")"
compare_spelling "guard_findings_write.sh" "guard_findings_write.sh" \
  "$(mkpayload Write file_path "$GFW_TARGET_NATIVE" content "{\"fingerprint\":\"forged\"}")" \
  "$(mkpayload Write file_path "$GFW_TARGET_POSIX"  content "{\"fingerprint\":\"forged\"}")"

echo
echo "══════════════════════════════════════════════════════════════════════"
echo "guard_cross_project_write.sh — needs an ARMED PROJECT WINDOW. Driven via pm_flag.sh arm"
echo "inside the sandbox HOME (same mechanism a real /checkin uses), not hand-crafted state files."
echo "══════════════════════════════════════════════════════════════════════"
export CLAUDE_CODE_SESSION_ID="spelltest-cross-project-session"
GXP_ACTIVE_DOC="$SANDBOX/notes/state/projects/activeslug/brief.md"
ARM_OUT="$(HOME="$HOME" CLAUDE_CODE_SESSION_ID="$CLAUDE_CODE_SESSION_ID" bash "$HOOKDIR/pm_flag.sh" arm "$GXP_ACTIVE_DOC" activeslug spelltest-desk 2>&1)"
if printf '%s' "$ARM_OUT" | grep -q '^ARMED:'; then
  GXP_TARGET_POSIX="$SANDBOX/notes/state/projects/otherslug/brief.md"
  GXP_TARGET_NATIVE="$(to_native "$GXP_TARGET_POSIX")"
  compare_spelling "guard_cross_project_write.sh" "guard_cross_project_write.sh" \
    "$(mkpayload Write file_path "$GXP_TARGET_NATIVE" content "rewriting the wrong project's brief")" \
    "$(mkpayload Write file_path "$GXP_TARGET_POSIX"  content "rewriting the wrong project's brief")"
else
  note_skip "guard_cross_project_write.sh" "could not arm a project window via pm_flag.sh in the sandbox HOME (arm output: $(printf '%s' "$ARM_OUT" | head -c 200)) -- this guard needs an armed window to have anything to contradict, and without one it is a correct, silent no-op for both spellings alike, which would not exercise the fold at all."
fi
unset CLAUDE_CODE_SESSION_ID

echo
echo "══════════════════════════════════════════════════════════════════════"
echo "guard_throughline_write_scope.sh — needs an ARMED /throughline RUN. Driven by touching the"
echo "same flag file throughline_flag.sh itself writes, under the sandbox HOME, plus a resolvable"
echo "notes root via LIFEHACK_ROOT — not a guess at internal state."
echo "══════════════════════════════════════════════════════════════════════"
export CLAUDE_CODE_SESSION_ID="spelltest-throughline-session"
GTL_NOTES_ROOT="$SANDBOX/notes-root"
mkdir -p "$GTL_NOTES_ROOT/records/insights/throughline"
export LIFEHACK_ROOT="$GTL_NOTES_ROOT"
TL_FLAGDIR="$HOME/.claude/run/throughline"
mkdir -p "$TL_FLAGDIR"
touch "$TL_FLAGDIR/tl-sess-$CLAUDE_CODE_SESSION_ID.flag"
if [ -f "$TL_FLAGDIR/tl-sess-$CLAUDE_CODE_SESSION_ID.flag" ]; then
  # The ONE sanctioned destination itself, in both spellings -- this is the pair that actually
  # exercises the fix: canon()'s dirname/basename/cd need forward slashes just to split a
  # backslash-native path at all, so pre-fix this pair did NOT agree (see the revert-test in the
  # report). A target outside DEST would deny in both spellings even unfixed (canon() mangles a
  # backslash path into garbage that never matches DEST either way), which would not prove anything.
  GTL_TARGET_POSIX="$GTL_NOTES_ROOT/records/insights/throughline/spelltest-2026-08-25.md"
  GTL_TARGET_NATIVE="$(to_native "$GTL_TARGET_POSIX")"
  compare_spelling "guard_throughline_write_scope.sh" "guard_throughline_write_scope.sh" \
    "$(mkpayload Write file_path "$GTL_TARGET_NATIVE" content "throughline findings")" \
    "$(mkpayload Write file_path "$GTL_TARGET_POSIX"  content "throughline findings")"
else
  note_skip "guard_throughline_write_scope.sh" "could not create the armed-run flag file at $TL_FLAGDIR -- this guard is a pure no-op for every write when no /throughline run is armed, so without the flag file both spellings would trivially agree (exit 0, silent) without ever reaching the fold at all."
fi
unset CLAUDE_CODE_SESSION_ID LIFEHACK_ROOT

echo
echo "══════════════════════════════════════════════════════════════════════"
printf 'SKIPPED: %d guard(s).' "$skip"
if [ "$skip" -gt 0 ]; then
  echo " Reasons:"
  for r in "${SKIP_REASONS[@]}"; do echo "  - $r"; done
else
  echo
fi
echo "RESULT: $pass passed, $fail failed, $skip skipped."
[ "$fail" -eq 0 ] && echo "GUARD PATH-SPELLING GREEN" || echo "GUARD PATH-SPELLING RED"
exit $([ "$fail" -eq 0 ] && echo 0 || echo 1)
