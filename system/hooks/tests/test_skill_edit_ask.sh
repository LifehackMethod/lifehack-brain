#!/bin/bash
# test_skill_edit_ask.sh -- Round C lock-prep B, switch skill_edit_ask: a write/edit (Write, Edit, MultiEdit, Bash redirect/tee/cp/mv/sed -i)
# under ANY .claude/skills/ folder draws the harness ASK (permissionDecision "ask", exit 0, JSON on stdout). OFF = no ask.
# ALLOW cases first. Fictional names. Run: bash system/hooks/tests/test_skill_edit_ask.sh
HERE="$(cd "$(dirname "$0")/.." && pwd)"; HOOK="$HERE/guard_build_mode.sh"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
export HOME="$T/home"; CODE="$T/code"; NOTES="$T/notes"
mkdir -p "$HOME/.config/lifehack" "$CODE/shared" "$CODE/system/register" "$CODE/system/sops" "$CODE/system/hooks" "$CODE/hooks" "$NOTES/desks/pond/tools" "$T/proj/.claude/skills/old" "$HOME/.claude/skills/old"
echo "$CODE" > "$HOME/.config/lifehack/code-root"
cp "$HERE/../../shared/brain_root.py" "$HERE/../tools/utf8_stdio.py" "$CODE/shared/"; export LIFEHACK_ROOT="$NOTES"
cp "$HERE/build_mode_sops.conf" "$HERE/placement.conf" "$CODE/system/hooks/"; mkdir -p "$CODE/state" "$NOTES/system"
for s in skill-building jobs hook desk-building; do echo "# $s" > "$CODE/system/sops/$s-sop.md"; done
echo '{"hooks":{}}' > "$CODE/hooks/hooks.json"; printf '{"type":"tool","path":"/shared/paths.py"}\n' > "$CODE/system/register/register.jsonl"
echo "old" > "$HOME/.claude/skills/old/SKILL.md"; echo "old" > "$T/proj/.claude/skills/old/SKILL.md"
P=0; F=0
J() { python3 -c 'import json,sys; print(json.dumps(dict(zip(sys.argv[1::2],sys.argv[2::2]))))' "$@"; }
fire() { # fire <switch on|off> <session> <tool> <tool_input-json>
  python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"cwd":sys.argv[2],"tool_name":sys.argv[3],"tool_input":json.loads(sys.argv[4])}))' "$2" "$T/proj" "$3" "$4" \
    | ROUNDB_SKILL_EDIT_ASK="$1" bash "$HOOK" >"$T/out" 2>"$T/err"; RC=$?; }
asked() { grep -q '"permissionDecision": "ask"' "$T/out" && [ $RC -eq 0 ]; }
allow() { fire on "$2" "$3" "$4"; if ! asked; then P=$((P+1)); else F=$((F+1)); echo "FAIL allow $1 rc=$RC $(head -c 160 "$T/out")"; fi; }
ask() {   # ON asks (names the rule and the way through); OFF does not ask. The other checks still run first: a new-skill speed bump answers rc 2 once, the retry asks.
  fire on "$2" "$3" "$4"; [ $RC -eq 2 ] && fire on "$2" "$3" "$4"
  if asked && grep -q "WAY-THROUGH" "$T/out" && grep -q "WHO-COULD-THIS-BREAK" "$T/out" && grep -q "skill_edit_ask" "$T/out"; then P=$((P+1)); else F=$((F+1)); echo "FAIL ask $1 [on] rc=$RC $(head -c 160 "$T/out")"; fi
  fire off "$2" "$3" "$4"; if ! asked; then P=$((P+1)); else F=$((F+1)); echo "FAIL $1 [off] still asked"; fi; }
U="$HOME/.claude/skills"; PR="$T/proj/.claude/skills"
# ---- ALLOW
allow "Write a desk tool (not a skill)" a1 Write "$(J file_path "$NOTES/desks/pond/tools/note.txt" content hi)"
allow "Write under plugin-style skills/ with no dot-claude" a2 Write "$(J file_path "$T/proj/skills/pondkeeper/SKILL.md" content hi)"
allow "Write under .claude/skillsets (name prefix only)" a3 Write "$(J file_path "$T/proj/.claude/skillsets/x.md" content hi)"
allow "Bash cat READS a skill" a4 Bash "$(J command "cat $U/old/SKILL.md")"
allow "Bash ls a skill folder" a5 Bash "$(J command "ls $PR/old")"
allow "Bash redirect to a normal file" a6 Bash "$(J command "echo hi > $T/proj/notes.txt")"
allow "Bash grep in skills piped to /tmp" a7 Bash "$(J command "grep -r heron $U > $T/found.txt")"
# ---- ASK
ask "Write user-level skill" b1 Write "$(J file_path "$U/pond/SKILL.md" content hi)"
ask "Write project-level skill" b2 Write "$(J file_path "$PR/pond/SKILL.md" content hi)"
ask "Edit existing user skill" b3 Edit "$(J file_path "$U/old/SKILL.md" old_string old new_string new)"
ask "Edit existing project skill" b4 Edit "$(J file_path "$PR/old/SKILL.md" old_string old new_string new)"
ask "MultiEdit skill" b5 MultiEdit "$(python3 -c 'import json,sys; print(json.dumps({"file_path":sys.argv[1],"edits":[{"old_string":"old","new_string":"new"}]}))' "$PR/old/SKILL.md")"
ask "Write a helper script inside a skill folder" b6 Write "$(J file_path "$U/old/scripts/run.sh" content hi)"
ask "Bash redirect into a skill" b7 Bash "$(J command "echo hi > $PR/old/SKILL.md")"
ask "Bash heredoc into a skill" b8 Bash "$(J command "cat > $U/old/SKILL.md <<'EOF'
hello
EOF")"
ask "Bash append into a skill" b9 Bash "$(J command "echo more >> $U/old/SKILL.md")"
ask "Bash tee into a skill" b10 Bash "$(J command "echo hi | tee $PR/old/SKILL.md")"
ask "Bash cp into a skill" b11 Bash "$(J command "cp $T/proj/notes.txt $U/old/SKILL.md")"
ask "Bash sed -i on a skill" b12 Bash "$(J command "sed -i '' 's/old/new/' $PR/old/SKILL.md")"
ask "Bash mkdir a new skill folder" b13 Bash "$(J command "mkdir -p $U/newone")"
ask "Bash relative path from the project" b14 Bash "$(J command "echo hi > .claude/skills/old/SKILL.md")"
echo "skill-edit-ask: $P passed, $F failed"; [ $F -eq 0 ]
