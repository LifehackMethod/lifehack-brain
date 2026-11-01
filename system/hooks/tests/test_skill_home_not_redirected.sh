#!/bin/bash
# Regression (Round D overnight B01): the placement stop for a SKILL.md outside every home must say ~/.claude/skills/<name>/ (anchor ruling P-50),
# never "personal code folder"; a loose script still gets the personal-code message; a NEW skill (and its scripts/) under ~/.claude/skills is never redirected.
# Pins every Round B switch OFF, then turns on exactly the go-live switches that matter here.
HERE="$(cd "$(dirname "$0")/.." && pwd)"
. "$HERE/tests/pin_roundb_off.sh"
export ROUNDB_PLACEMENT_OUTSIDE_HOMES=on ROUNDB_SKILLS_NATIVE_HOME=on ROUNDB_SKILLS_NATIVE_WRITE=on ROUNDB_SKILL_EDIT_ASK=on ROUNDB_PLACEMENT_PROJECT_SKILLS=on
HOOK="$HERE/guard_build_mode.sh"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
CODE="$(cd "$HERE/../.." && pwd)"
export HOME="$T/home" LIFEHACK_ROOT="$T/notes"
mkdir -p "$HOME/.config/lifehack" "$HOME/personal-code" "$LIFEHACK_ROOT" "$HOME/work/skills"
echo "$CODE" > "$HOME/.config/lifehack/code-root"; echo "$HOME/personal-code" > "$HOME/.config/lifehack/personal-code"
pass=0; fail=0
fire() { ERR="$(python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"cwd":"/tmp","tool_name":"Write","tool_input":{"file_path":sys.argv[2],"content":sys.argv[3]}}))' "$1" "$2" "$3" | bash "$HOOK" 2>&1 >/dev/null)"; RC=$?; }
chk() { # chk <rc> <label> <must contain> <must NOT contain>
  if [ "$RC" = "$1" ] && { [ -z "$3" ] || printf '%s' "$ERR" | grep -Fq -- "$3"; } && { [ -z "$4" ] || ! printf '%s' "$ERR" | grep -Fq -- "$4"; }; then pass=$((pass+1)); echo "   ok   $2"
  else fail=$((fail+1)); printf '  FAIL  %s (rc=%s): %.200s\n' "$2" "$RC" "$ERR"; fi; }
SK=$'---\nname: friday-recap\n---\nx'
fire s1 "$HOME/work/skills/friday-recap/SKILL.md" "$SK"; chk 2 "SKILL.md outside homes: points to ~/.claude/skills" "~/.claude/skills/friday-recap/SKILL.md" "belongs in your personal code folder"
fire s2 "$HOME/work/ping.py" 'print(1)'; chk 2 "loose .py outside homes: still the personal code folder" "this belongs in your personal code folder"
fire s3 "$HOME/.claude/skills/friday-recap/SKILL.md" "$SK"; fire s3 "$HOME/.claude/skills/friday-recap/SKILL.md" "$SK"; chk 0 "new skill in ~/.claude/skills: not redirected, not asked" "" "Wrong home"
fire s4 "$HOME/.claude/skills/friday-recap/scripts/run.py" 'print(1)'; chk 0 "script inside a new skill: not redirected" "" "Wrong home"
# Decision 1 (Enver, 2026-11-01): a NEW skill under a PROJECT's .claude/skills is steered to ~/.claude/skills; the retry (the person said it is for this project) goes through
fire s6 "$HOME/work/proj/.claude/skills/friday-recap/SKILL.md" "$SK"; chk 2 "project .claude/skills SKILL.md: steered to ~/.claude/skills" "~/.claude/skills/friday-recap/SKILL.md" "belongs in your personal code folder"
chk 2 "  ... and says when the project folder is right" "ONLY if the person said this skill is for this project" ""
fire s6 "$HOME/work/proj/.claude/skills/friday-recap/SKILL.md" "$SK"; chk 0 "project .claude/skills: identical retry (confirmed for this project) passes" "" "Wrong home"
fire s7 "$HOME/.claude/skills/other/SKILL.md" "$SK"; fire s7 "$HOME/.claude/skills/other/SKILL.md" "$SK"; chk 0 "~/.claude/skills new skill unchanged: no stop" "" "Wrong home"
# Bash heredoc through a shell variable: the message must not print the literal $d as the folder name
CMD="d=$HOME/work/skills/meeting-decisions; mkdir -p \"\$d\"; cat > \"\$d/SKILL.md\" <<'EOF'
x
EOF"
ERR="$(python3 -c 'import json,sys; print(json.dumps({"session_id":"s5","cwd":sys.argv[2],"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$CMD" "$HOME/work" | bash "$HOOK" 2>&1 >/dev/null)"; RC=$?
chk 2 "Bash heredoc via \$d: stop says <name>, never the literal \$d" "~/.claude/skills/<name>/SKILL.md" '$d/SKILL.md'
echo "pass=$pass fail=$fail"; [ "$fail" = 0 ]
