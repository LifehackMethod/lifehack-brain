#!/bin/bash
# B07 ruling (2026-10-31): a tool made for ONE desk goes to <personal code>/desks/<desk>/tools/; the loose personal code folder is for
# no-desk scripts; the notes folder is data only. Checks the text the placement hooks print. Personal code is resolved through the
# pointer file, never hard-coded.
HERE="$(cd "$(dirname "$0")/.." && pwd)"
. "$HERE/tests/pin_roundb_off.sh"
HOOK="$HERE/guard_build_mode.sh"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
export HOME="$T/home"; CODE="$T/code"; NOTES="$T/notes"
mkdir -p "$HOME/.config/lifehack" "$CODE/shared/tools" "$CODE/system/register" "$CODE/system/sops" "$CODE/system/hooks" "$CODE/hooks" "$NOTES/desks/marc/tools" "$NOTES/system" "$CODE/state"
echo "$CODE" > "$HOME/.config/lifehack/code-root"
cp "$HERE/../../shared/brain_root.py" "$HERE/../../shared/personal_code_root.py" "$HERE/../tools/utf8_stdio.py" "$CODE/shared/"; export LIFEHACK_ROOT="$NOTES"
cp "$HERE/build_mode_sops.conf" "$HERE/placement.conf" "$CODE/system/hooks/"
for s in skill-building jobs hook desk-building; do echo "# $s" > "$CODE/system/sops/$s-sop.md"; done
echo '{"hooks":{}}' > "$CODE/hooks/hooks.json"; : > "$CODE/system/register/register.jsonl"
PCODE="$T/pcode-elsewhere"; mkdir -p "$PCODE"; echo "$PCODE" > "$HOME/.config/lifehack/personal-code"; PCREAL="$(cd "$PCODE" && pwd -P)"
pass=0; fail=0
payload() { python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"cwd":sys.argv[2],"tool_name":sys.argv[3],"tool_input":json.loads(sys.argv[4])}))' "$1" "$NOTES" "$2" "$3"; }
J() { python3 -c 'import json,sys; print(json.dumps(dict(zip(sys.argv[1::2],sys.argv[2::2]))))' "$@"; }
fire() { ERR="$(payload "$1" "$2" "$3" | bash "$HOOK" 2>&1 >/dev/null)"; RC=$?; }
has() { printf '%s' "$ERR" | grep -Fq -- "$2" && { pass=$((pass+1)); echo "   ok   $1"; } || { fail=$((fail+1)); echo "  FAIL  $1 (text: $(printf '%.200s' "$ERR"))"; }; }
hasnt() { printf '%s' "$ERR" | grep -Fq -- "$2" && { fail=$((fail+1)); echo "  FAIL  $1"; } || { pass=$((pass+1)); echo "   ok   $1"; }; }

# 1. a new script in a desk's folder in the NOTES folder: the stop names <personal code>/desks/<desk>/tools/ and says notes are data only
fire a1 Write "$(J file_path "$NOTES/desks/marc/tools/mytool.py" content 'print(1)')"
[ "$RC" = 2 ] && { pass=$((pass+1)); echo "   ok   code in the notes folder is stopped"; } || { fail=$((fail+1)); echo "  FAIL  code in notes not stopped rc=$RC"; }
has "names the resolved <personal code>/desks/<desk>/tools/" "$PCREAL/desks/<desk>/tools/"
has "says the notes folder is data only" "data only"
hasnt "no hard-coded ClaudeOps path" "ClaudeOps"
hasnt "old wording (private repo's desks) is gone" "private repo's desks"
# 2. the personal-code pointer is missing: generic wording, still no hard-coded path
mv "$HOME/.config/lifehack/personal-code" "$HOME/.config/lifehack/personal-code.bak"
fire a2 Write "$(J file_path "$NOTES/desks/marc/tools/other.py" content 'print(2)')"
has "no pointer: points at desks/<desk>/tools/ inside the personal code folder" "desks/<desk>/tools/ folder inside your personal code folder"
hasnt "no pointer: still no ClaudeOps" "ClaudeOps"
mv "$HOME/.config/lifehack/personal-code.bak" "$HOME/.config/lifehack/personal-code"
# 3. the outside-homes stop names the personal code folder (the reason gate was removed 2026-11-01)
mkdir -p "$HOME/odd-widget"
export ROUNDB_PLACEMENT_OUTSIDE_HOMES=on ROUNDB_SKILLS_NATIVE_HOME=on
fire a3 Write "$(J file_path "$HOME/odd-widget/ping.py" content 'print(1)')"
has "stop: personal code folder named" "$PCREAL"
hasnt "stop: old 'only when the person said' wording is gone" "only when the person said"
echo "passed=$pass failed=$fail"; [ "$fail" -eq 0 ]
