#!/bin/bash
# test_organism_map_guard.sh — the write-guard over the map this system keeps of itself.
#
# ⭐ THE CASE THIS SUITE EXISTS FOR. The guard was DROPPED during the port on one stated reason:
# `system/tools/organism/label_manifest.yaml` recorded that "system/organism/ does not exist in this
# repo at all (confirmed absent)". Phase 9 landed the whole tree on 2026-08-15 — manual.md,
# map-format-specs.md and 42 elements/ files. The premise died and nothing replaced it, leaving the
# worst of the three states: several SHIPPED documents describe the organism tree as write-guarded
# while nothing guarded it. A protection that is documented but absent is the defect class the house
# rule T9.11b (`system/build-rules-index.md`) is named after.
#
# ⚠ ALLOW CASES COME FIRST, on purpose. A guard that blocks ordinary work gets unregistered, and
# then it guards nothing. The whole authoring path for these files is the surgical Edit, and every
# one of those must pass.
#
# ⚠ AND THE EXIT CODE IS NOT THE TEST. Measured during this guard's own port: the deny message
# wrapped a command in backticks, the escaping emitted an invalid JSON escape, and the deny was
# unparseable — exit 2 fired, an exit-code-only suite scored it PASS, and the message a human reads
# would have rendered on neither channel. So the last block below re-parses every deny path and
# asserts WHY / REDIRECT / RULE are present in the text. (`canon/hook-sop.md` §4.)
#
# Deny = exit 2 + JSON on stderr. Allow = exit 0.
# Run: bash system/hooks/tests/test_organism_map_guard.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$HOOKS/../.." && pwd)"
GUARD="$HOOKS/guard_organism_map.sh"
[ -f "$GUARD" ] || { echo "CANNOT RUN: no hook at $GUARD"; exit 1; }

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

# fire <label> <expected-rc> <tool> <path> [with-content:1|0]
fire() {
  local label="$1" exp="$2" tool="$3" path="$4" body="${5:-1}" got repo="${6:-$REPO}"
  python3 -c "
import json, sys
tool, path, body = sys.argv[1], sys.argv[2], sys.argv[3]
ti = {}
if path: ti['file_path'] = path
if body == '1': ti['content'] = '# a whole new file\n'
else: ti.update({'old_string': 'a', 'new_string': 'b'})
print(json.dumps({'tool_name': tool, 'tool_input': ti}))" "$tool" "$path" "$body" 2>/dev/null \
    | env CLAUDE_PROJECT_DIR="$repo" bash "$GUARD" >/dev/null 2>&1
  got=$?
  [ "$got" = "$exp" ] && ok || bad "$label" "expected exit $exp, got $got"
}

echo "── ALLOW FIRST: the surgical Edit is the normal authoring path ───────────"
fire "Edit the manual"            0 Edit  "$REPO/canon/manual.md"                0
fire "Edit the format specs"      0 Edit  "$REPO/canon/map-format-specs.md"      0
fire "Edit an element"            0 Edit  "$REPO/system/organism/elements/canon.md"        0
fire "Edit a NEW element"         0 Edit  "$REPO/system/organism/elements/invented.md"     0

echo "── ALLOW: it does not over-block anything outside its own subject ────────"
fire "Write the README"           0 Write "$REPO/README.md"
fire "Write a skill file"         0 Write "$REPO/.claude/skills/save/SKILL.md"
fire "Write outside the repo"     0 Write "/tmp/scratch-note.md"
fire "Write a non-.md in elements/" 0 Write "$REPO/system/organism/elements/notes.txt"
fire "Write system/organism/ sibling" 0 Write "$REPO/system/organism-notes.md"
fire "another checkout's organism" 0 Write "/tmp/some-other-repo/canon/manual.md"
fire "a Write carrying no path"   0 Write ""

echo "── DENY: a wholesale Write of a protected map file ───────────────────────"
fire "Write the manual"           2 Write "$REPO/canon/manual.md"
fire "Write the format specs"     2 Write "$REPO/canon/map-format-specs.md"
fire "Write an element"           2 Write "$REPO/system/organism/elements/canon.md"
fire "Write a NEW element"        2 Write "$REPO/system/organism/elements/invented.md"

echo "── ⭐ DENY: the same targets, spelled so a raw string match would miss ────"
# The donor matched a glob against the raw file_path. Every spelling below resolves to a protected
# file and every one of them walked past that version.
fire "relative to the repo"       2 Write "canon/manual.md"
fire "via a .. traversal"         2 Write "$REPO/system/tools/../../canon/manual.md"
fire "via a doubled slash"        2 Write "$REPO/canon//manual.md"
fire "via a . segment"            2 Write "$REPO/system/organism/./elements/brain.md"
fire "relative element path"      2 Write "system/organism/elements/hook-plane.md"

echo "── DENY: fail closed on anything it cannot inspect ───────────────────────"
for label in "unparseable stdin" "empty stdin"; do
  case "$label" in
    "unparseable stdin") payload='not json at all' ;;
    *)                   payload='' ;;
  esac
  printf '%s' "$payload" | env CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" >/dev/null 2>&1
  got=$?
  [ "$got" = 2 ] && ok || bad "$label" "expected exit 2 (fail closed), got $got"
done

echo "── ⭐ THE DENY TEXT ITSELF — a message that cannot render is a dark guard ─"
# Every deny path: JSON must re-parse, and must carry WHY + REDIRECT + RULE. An exit code alone
# scored the invalid-escape bug in this very file a PASS.
check_text() {
  local label="$1"; shift
  "$@" 2>/tmp/.org_deny.$$ >/dev/null
  python3 -c "
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception as e:
    print('UNPARSEABLE: %s' % e); raise SystemExit(1)
r = d.get('reason', '')
missing = [k for k in ('WHY:', 'REDIRECT:', 'RULE:') if k not in r]
if d.get('decision') != 'block': print('not a block decision'); raise SystemExit(1)
if missing: print('deny text missing %s' % ', '.join(missing)); raise SystemExit(1)
" /tmp/.org_deny.$$ && ok || bad "$label" "$(cat /tmp/.org_deny.$$ | head -c 120)"
  rm -f /tmp/.org_deny.$$
}
_payload() { python3 -c "
import json,sys; print(json.dumps({'tool_name':'Write','tool_input':{'file_path':sys.argv[1],'content':'x'}}))" "$1"; }

check_text "deny text: manual"   bash -c "_p=\$(python3 -c \"import json;print(json.dumps({'tool_name':'Write','tool_input':{'file_path':'$REPO/canon/manual.md','content':'x'}}))\"); printf '%s' \"\$_p\" | env CLAUDE_PROJECT_DIR='$REPO' bash '$GUARD'"
check_text "deny text: element"  bash -c "_p=\$(python3 -c \"import json;print(json.dumps({'tool_name':'Write','tool_input':{'file_path':'$REPO/system/organism/elements/canon.md','content':'x'}}))\"); printf '%s' \"\$_p\" | env CLAUDE_PROJECT_DIR='$REPO' bash '$GUARD'"
check_text "deny text: unparseable" bash -c "printf 'not json' | env CLAUDE_PROJECT_DIR='$REPO' bash '$GUARD'"

echo
echo "── COMPONENT PAGES (2026-11-16): a SIGN, not a hard block ────────────────"
# A component page carries two machine-only fenced blocks (AS-BUILT / STATUS) regenerated by
# component_page.py. A whole-file Write is signed; an Edit/MultiEdit is signed only when its
# strings reach into the fenced content; an Edit confined to the human parts passes.

# fixture: one component page with both fences, in the repo the suite fires against
COMPDIR="$REPO/canon/components"
FIXTURE="$COMPDIR/test-fixture.md"
mkdir -p "$COMPDIR"
cat > "$COMPDIR/test-fixture.md" <<'FIX'
---
component: test-fixture
title: "Test fixture"
---
# Test fixture

## Directory/file location
<!-- AS-BUILT:BEGIN -->
| file | system/tools/a.sh |
<!-- AS-BUILT:END -->

## Status
<!-- STATUS:BEGIN -->
Status: unproven (receipt missing)
<!-- STATUS:END -->
FIX
trap 'rm -f "$REPO/canon/components/test-fixture.md"; rmdir "$REPO/canon/components" 2>/dev/null' EXIT

fire_edit() { # label expected tool path old_string new_string [repo]
  local label="$1" exp="$2" tool="$3" path="$4" old="$5" new="$6" got repo="${7:-$REPO}"
  python3 -c "
import json, sys
tool, path, old, new = sys.argv[1:5]
print(json.dumps({'tool_name': tool, 'tool_input': {'file_path': path, 'old_string': old, 'new_string': new}}))" \
      "$tool" "$path" "$old" "$new" 2>/dev/null \
    | env CLAUDE_PROJECT_DIR="$repo" bash "$GUARD" >/dev/null 2>&1
  got=$?
  [ "$got" = "$exp" ] && ok || bad "$label" "expected exit $exp, got $got"
}
fire_multi() { # label expected path old1 new1 old2 new2
  local label="$1" exp="$2" path="$3" o1="$4" n1="$5" o2="$6" n2="$7" got
  python3 -c "
import json, sys
path, o1, n1, o2, n2 = sys.argv[1:6]
print(json.dumps({'tool_name': 'MultiEdit', 'tool_input': {'file_path': path,
  'edits': [{'old_string': o1, 'new_string': n1}, {'old_string': o2, 'new_string': n2}]}}))" \
      "$path" "$o1" "$n1" "$o2" "$n2" 2>/dev/null \
    | env CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" >/dev/null 2>&1
  got=$?
  [ "$got" = "$exp" ] && ok || bad "$label" "expected exit $exp, got $got"
}

echo "── COMPONENT ALLOW: an Edit confined to the human parts passes ───────────"
fire_edit "Edit a component, human parts only"   0 Edit "$FIXTURE" "## Directory/file location" "## Directory / file location"
fire_edit "Edit a component, empty strings"      0 Edit "$FIXTURE" "" ""
fire_edit "Edit an unrelated file"               0 Edit "$REPO/README.md" "a" "b"
fire_edit "Edit a non-.md in components/"        0 Edit "$COMPDIR/notes.txt" "AS-BUILT:BEGIN" "x"
fire_multi "MultiEdit a component, human parts"  0 "$FIXTURE" "## Status" "## Status " "# Test fixture" "# Test fixture v2"

echo "── COMPONENT SIGN: a Write, or an Edit reaching into a fence ─────────────"
fire     "Write a component page"                2 Write "$FIXTURE"
fire     "Write a NEW component page"            2 Write "$COMPDIR/invented.md"
fire_edit "Edit a component, fence marker"       2 Edit "$FIXTURE" "<!-- AS-BUILT:BEGIN -->" "<!-- AS-BUILT:BEGIN -->x"
fire_edit "Edit a component, fenced table line"  2 Edit "$FIXTURE" "| file | system/tools/a.sh |" "| file | system/tools/a.sh | HAND-EDITED |"
fire_edit "Edit a component, fenced status line" 2 Edit "$FIXTURE" "Status: unproven (receipt missing)" "Status: LIVE forged"
fire_edit "Edit a component, STATUS marker"      2 Edit "$FIXTURE" "STATUS:END" "STATUS:END"
fire_multi "MultiEdit a component, fence in edit 2" 2 "$FIXTURE" "## Purpose" "## Purpose " "AS-BUILT:END" "AS-BUILT:END x"

echo "── COMPONENT SIGN TEXT: the deny JSON must re-parse ──────────────────────"
check_text "deny text: component Write" bash -c "_p=\$(python3 -c \"import json;print(json.dumps({'tool_name':'Write','tool_input':{'file_path':'$FIXTURE','content':'x'}}))\"); printf '%s' \"\$_p\" | env CLAUDE_PROJECT_DIR='$REPO' bash '$GUARD'"
check_text "deny text: component Edit in fence" bash -c "_p=\$(python3 -c \"import json;print(json.dumps({'tool_name':'Edit','tool_input':{'file_path':'$FIXTURE','old_string':'AS-BUILT:BEGIN','new_string':'x'}}))\"); printf '%s' \"\$_p\" | env CLAUDE_PROJECT_DIR='$REPO' bash '$GUARD'"

echo "── ROUND 2 FIX 8: a fence edit covering only part of a line must sign ────"
fire_edit "Substring of a fenced status line signs" 2 Edit "$FIXTURE" "Status: unproven" "Status: LIVE forged"
fire_edit "Substring of a fenced table row signs"   2 Edit "$FIXTURE" "system/tools/a.sh" "system/tools/b.sh"
fire_edit "old_string absent from the page signs (fail closed)" 2 Edit "$FIXTURE" "text that appears nowhere in this page" "x"
fire_edit "Heading above the fences still passes"   0 Edit "$FIXTURE" "# Test fixture" "# Test fixture v2"

echo "── ROUND 2 FIX 9: a repo path containing a space ─────────────────────────"
SPACE_BASE="$(mktemp -d)"
SPACE_REPO="$SPACE_BASE/with space/repo"
mkdir -p "$SPACE_REPO/canon/components" "$SPACE_REPO/system/organism/elements"
printf 'x\n' > "$SPACE_REPO/canon/manual.md"
cp "$FIXTURE" "$SPACE_REPO/canon/components/test-fixture.md"
trap 'rm -rf "$SPACE_BASE"; rm -f "$REPO/canon/components/test-fixture.md"; rmdir "$REPO/canon/components" 2>/dev/null' EXIT
fire  "Space path: Write the manual is denied"  2 Write "$SPACE_REPO/canon/manual.md" 1 "$SPACE_REPO"
fire  "Space path: Write a component is signed" 2 Write "$SPACE_REPO/canon/components/test-fixture.md" 1 "$SPACE_REPO"
fire_edit "Space path: a fence edit is signed"  2 Edit "$SPACE_REPO/canon/components/test-fixture.md" "Status: unproven (receipt missing)" "Status: LIVE forged" "$SPACE_REPO"
fire_edit "Space path: outside-fence edit passes" 0 Edit "$SPACE_REPO/canon/components/test-fixture.md" "# Test fixture" "# Test fixture v2" "$SPACE_REPO"

echo "── ROUND 2 FIX 10: deny JSON survives quote and backslash in the path ────"
check_text "deny text: double-quote in filename" bash -c "_p=\$(python3 -c \"import json;print(json.dumps({'tool_name':'Write','tool_input':{'file_path':'$COMPDIR/a\\\"b.md','content':'x'}}))\"); printf '%s' \"\$_p\" | env CLAUDE_PROJECT_DIR='$REPO' bash '$GUARD'"
check_text "deny text: backslash in filename"    bash -c "_p=\$(python3 -c \"import json;print(json.dumps({'tool_name':'Write','tool_input':{'file_path':'$COMPDIR/a'+chr(92)+'q.md','content':'x'}}))\"); printf '%s' \"\$_p\" | env CLAUDE_PROJECT_DIR='$REPO' bash '$GUARD'"

echo "── ROUND 2 FIX 11 (darwin only): case-folded path matching ───────────────"
case "$(uname -s)" in
  Darwin)
    fire     "Case variant: Write a component is signed"  2 Write "$REPO/canon/COMPONENTS/test-fixture.md"
    fire     "Case variant: Write an element is denied"   2 Write "$REPO/system/organism/ELEMENTS/canon.md"
    fire_edit "Case variant: fence edit is signed"        2 Edit "$REPO/canon/COMPONENTS/test-fixture.md" "Status: unproven (receipt missing)" "Status: LIVE forged"
    ;;
esac

echo

echo "passed: $pass   failed: $fail"
[ "$fail" -eq 0 ] || exit 1
exit 0
