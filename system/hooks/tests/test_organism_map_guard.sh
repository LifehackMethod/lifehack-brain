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
# asserts WHY / REDIRECT / RULE are present in the text. (`system/sops/hook-sop.md` §4.)
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
  local label="$1" exp="$2" tool="$3" path="$4" body="${5:-1}" got
  python3 -c "
import json, sys
tool, path, body = sys.argv[1], sys.argv[2], sys.argv[3]
ti = {}
if path: ti['file_path'] = path
if body == '1': ti['content'] = '# a whole new file\n'
else: ti.update({'old_string': 'a', 'new_string': 'b'})
print(json.dumps({'tool_name': tool, 'tool_input': ti}))" "$tool" "$path" "$body" 2>/dev/null \
    | env CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" >/dev/null 2>&1
  got=$?
  [ "$got" = "$exp" ] && ok || bad "$label" "expected exit $exp, got $got"
}

echo "── ALLOW FIRST: the surgical Edit is the normal authoring path ───────────"
fire "Edit the manual"            0 Edit  "$REPO/system/organism/manual.md"                0
fire "Edit the format specs"      0 Edit  "$REPO/system/organism/map-format-specs.md"      0
fire "Edit an element"            0 Edit  "$REPO/system/organism/elements/canon.md"        0
fire "Edit a NEW element"         0 Edit  "$REPO/system/organism/elements/invented.md"     0

echo "── ALLOW: it does not over-block anything outside its own subject ────────"
fire "Write the README"           0 Write "$REPO/README.md"
fire "Write a skill file"         0 Write "$REPO/.claude/skills/save/SKILL.md"
fire "Write outside the repo"     0 Write "/tmp/scratch-note.md"
fire "Write a non-.md in elements/" 0 Write "$REPO/system/organism/elements/notes.txt"
fire "Write system/organism/ sibling" 0 Write "$REPO/system/organism-notes.md"
fire "another checkout's organism" 0 Write "/tmp/some-other-repo/system/organism/manual.md"
fire "a Write carrying no path"   0 Write ""

echo "── DENY: a wholesale Write of a protected map file ───────────────────────"
fire "Write the manual"           2 Write "$REPO/system/organism/manual.md"
fire "Write the format specs"     2 Write "$REPO/system/organism/map-format-specs.md"
fire "Write an element"           2 Write "$REPO/system/organism/elements/canon.md"
fire "Write a NEW element"        2 Write "$REPO/system/organism/elements/invented.md"

echo "── ⭐ DENY: the same targets, spelled so a raw string match would miss ────"
# The donor matched a glob against the raw file_path. Every spelling below resolves to a protected
# file and every one of them walked past that version.
fire "relative to the repo"       2 Write "system/organism/manual.md"
fire "via a .. traversal"         2 Write "$REPO/system/tools/../organism/manual.md"
fire "via a doubled slash"        2 Write "$REPO/system/organism//manual.md"
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

check_text "deny text: manual"   bash -c "_p=\$(python3 -c \"import json;print(json.dumps({'tool_name':'Write','tool_input':{'file_path':'$REPO/system/organism/manual.md','content':'x'}}))\"); printf '%s' \"\$_p\" | env CLAUDE_PROJECT_DIR='$REPO' bash '$GUARD'"
check_text "deny text: element"  bash -c "_p=\$(python3 -c \"import json;print(json.dumps({'tool_name':'Write','tool_input':{'file_path':'$REPO/system/organism/elements/canon.md','content':'x'}}))\"); printf '%s' \"\$_p\" | env CLAUDE_PROJECT_DIR='$REPO' bash '$GUARD'"
check_text "deny text: unparseable" bash -c "printf 'not json' | env CLAUDE_PROJECT_DIR='$REPO' bash '$GUARD'"

echo
echo "passed: $pass   failed: $fail"
[ "$fail" -eq 0 ] || exit 1
exit 0
