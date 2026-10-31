#!/bin/bash
# test_fine_china_ask.sh -- Round D: guard_fine_china_ask.sh (fc_db_delete_ask, fc_folder_delete_ask, fc_user_sop_ask, fc_placement_conf_ask),
# the user's placement off-switch (placement_user_off), skills_native_home, and watch-only mode (mode=watch / LIFEHACK_WATCH=1).
# ALLOW cases first, each switch ON and OFF. Isolated HOME and code root; the real ~/.config/lifehack is never touched.
# Run: bash system/hooks/tests/test_fine_china_ask.sh      (VERBOSE=1 prints every case with the hook's answer)
HERE="$(cd "$(dirname "$0")/.." && pwd)"; FC="$HERE/guard_fine_china_ask.sh"; BM="$HERE/guard_build_mode.sh"
T="$(cd "$(mktemp -d)" && pwd -P)"; trap 'rm -rf "$T"' EXIT
export HOME="$T/home"; CODE="$T/code"; NOTES="$T/notes"; PC="$T/pc"
unset LIFEHACK_WATCH LIFEHACK_WATCH_SHADOW LHB_WATCH_CHILD; for v in $(env | sed -n 's/^\(ROUNDB_[A-Z0-9_]*\)=.*/\1/p'); do unset "$v"; done
mkdir -p "$HOME/.config/lifehack" "$HOME/.claude/skills" "$CODE/shared" "$CODE/system/register" "$CODE/system/sops" "$CODE/system/hooks" "$CODE/hooks" "$NOTES/desks/pond/tools" "$PC" "$HOME/proj/node_modules/x" "$HOME/proj/build" "$HOME/proj/data-folder/sub" "$HOME/proj/emptydir" "$HOME/proj/sops" "$HOME/proj/__pycache__"
echo "$CODE" > "$HOME/.config/lifehack/code-root"; echo "$PC" > "$HOME/.config/lifehack/personal-code"
cp "$HERE/../../shared/brain_root.py" "$HERE/../../shared/personal_code_root.py" "$HERE/../tools/utf8_stdio.py" "$CODE/shared/" 2>/dev/null; export LIFEHACK_ROOT="$NOTES"
mkdir -p "$CODE/shared/tools" "$CODE/system/hooks/lib"; cp "$HERE/../../shared/tools/own_list_add.py" "$CODE/shared/tools/"; cp "$HERE/lib/roundb.py" "$CODE/system/hooks/lib/"; cp "$HERE/roundB.conf" "$CODE/system/hooks/"
cp "$HERE/build_mode_sops.conf" "$HERE/placement.conf" "$CODE/system/hooks/"; mkdir -p "$CODE/state" "$NOTES/system"
for s in skill-building jobs hook desk-building; do echo "# $s" > "$CODE/system/sops/$s-sop.md"; done
echo '{"hooks":{}}' > "$CODE/hooks/hooks.json"; printf '{"type":"tool","path":"/shared/paths.py"}\n' > "$CODE/system/register/register.jsonl"
echo "keep" > "$HOME/proj/data-folder/sub/a.txt"; echo "x" > "$HOME/proj/build/o.js"; echo "x" > "$HOME/proj/node_modules/x/i.js"
echo "rows" > "$HOME/proj/notes.db"; echo "rows" > "$HOME/proj/app.sqlite"; echo "# my sop" > "$HOME/proj/sops/team-sop.md"; echo "# my sop" > "$HOME/proj/onboarding-sop.md"; echo "doc" > "$HOME/proj/readme.md"
mkdir -p "$T/scratch/box"; echo "t" > "$T/scratch/box/t.db"
P=0; F=0; V="${VERBOSE:-}"
J() { python3 -c 'import json,sys; print(json.dumps(dict(zip(sys.argv[1::2],sys.argv[2::2]))))' "$@"; }
run() { # run <hook> <session> <tool> <tool_input-json> [VAR=val ...]  -> RC, OUT, ERR in $T/out $T/err
  local hook="$1" sid="$2" tool="$3" ti="$4"; shift 4
  python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"cwd":sys.argv[2],"tool_name":sys.argv[3],"tool_input":json.loads(sys.argv[4])}))' "$sid" "$HOME/proj" "$tool" "$ti" | env "$@" bash "$hook" >"$T/out" 2>"$T/err"; RC=$?; }
asked() { grep -q '"permissionDecision": "ask"' "$T/out" && [ $RC -eq 0 ]; }
say() { [ -n "$V" ] && echo "  $1 -> rc=$RC out=$(head -c ${3:-150} "$T/out" | tr '\n' ' ') err=$(head -c 100 "$T/err" | tr '\n' ' ')"; }
ok() { P=$((P+1)); [ -n "$V" ] && echo "PASS $1"; return 0; }
bad() { F=$((F+1)); echo "FAIL $1 :: rc=$RC $(head -c 200 "$T/out") $(head -c 120 "$T/err")"; }
ALL="ROUNDB_FC_DB_DELETE_ASK=on ROUNDB_FC_FOLDER_DELETE_ASK=on ROUNDB_FC_USER_SOP_ASK=on ROUNDB_FC_PLACEMENT_CONF_ASK=on"
allow() { run "$FC" s "$3" "$4" $ALL; if ! asked && [ $RC -eq 0 ]; then ok "ALLOW $1"; else bad "ALLOW $1"; fi; say "$1"; }
ask() { # ask <name> <tool> <input> : ON asks (and names the rule), all four OFF does not
  run "$FC" s "$2" "$3" $ALL; if asked && grep -q "WAY-THROUGH" "$T/out"; then ok "ASK $1 [on]"; else bad "ASK $1 [on]"; fi; say "$1"
  run "$FC" s "$2" "$3"; if ! asked && [ $RC -eq 0 ]; then ok "ASK $1 [off = silent]"; else bad "ASK $1 [off]"; fi; }
D="$HOME/proj"
# ---------------- ALLOW (false-alarm guard): throwaway folders, non-folders, reads, new/append, other files
allow "rm -rf node_modules" "" Bash "$(J command "rm -rf $D/node_modules")"
allow "rm -rf build" "" Bash "$(J command "cd $D && rm -rf build")"
allow "rm -rf __pycache__" "" Bash "$(J command "rm -rf $D/__pycache__")"
allow "rm -rf a temp-folder scratch dir outside home" "" Bash "$(J command "rm -rf $T/scratch/box")"
allow "rm -rf a folder that does not exist" "" Bash "$(J command "rm -rf $D/nothing-here")"
allow "rm -rf an empty folder" "" Bash "$(J command "rm -rf $D/emptydir")"
allow "rm -f one plain file (not a db, not an SOP)" "" Bash "$(J command "rm -f $D/readme.md")"
allow "rm a database in a temp scratch dir" "" Bash "$(J command "rm $T/scratch/box/t.db")"
allow "rm -rf a folder named by an unresolved \$VAR (limit)" "" Bash "$(J command 'rm -rf "$SOMEDIR"/x')"
allow "sqlite3 SELECT" "" Bash "$(J command "sqlite3 $D/notes.db 'select * from t'")"
allow "echo mentions drop table into a text file" "" Bash "$(J command "echo 'drop table t' > $D/notes.txt")"
allow "Write a NEW sop file" "" Write "$(J file_path "$D/sops/new-sop.md" content hi)"
allow "append (>>) to an existing sop" "" Bash "$(J command "echo more >> $D/sops/team-sop.md")"
allow "Edit an ordinary markdown file" "" Edit "$(J file_path "$D/readme.md" old_string doc new_string docs)"
allow "cat placement.conf (read)" "" Bash "$(J command "cat $HOME/.config/lifehack/placement.conf")"
allow "grep placement.conf (read)" "" Bash "$(J command "grep kept $HOME/.config/lifehack/placement.conf")"
allow "Edit a plugin-tree SOP (the harness guards own it, not this one)" "" Edit "$(J file_path "$CODE/system/sops/hook-sop.md" old_string '# hook' new_string '# hooks')"
# ---------------- ASK
ask "rm -rf a real data folder" Bash "$(J command "rm -rf $D/data-folder")"
ask "rm -r a real data folder (no f)" Bash "$(J command "rm -r $D/data-folder")"
ask "rm -rf inside bash -c" Bash "$(J command "bash -c 'rm -rf $D/data-folder'")"
ask "rm -rf after cd with &&" Bash "$(J command "cd $D && ls && rm -rf data-folder")"
ask "rm a sqlite database file" Bash "$(J command "rm $D/app.sqlite")"
ask "rm -f a .db file" Bash "$(J command "rm -f $D/notes.db")"
ask "truncate a database by redirect" Bash "$(J command ": > $D/notes.db")"
ask "sqlite3 DROP TABLE" Bash "$(J command "sqlite3 $D/notes.db 'DROP TABLE t;'")"
ask "psql DELETE FROM with no WHERE" Bash "$(J command "psql -c 'DELETE FROM clients;' mydb")"
ask "dropdb via psql -c DROP DATABASE" Bash "$(J command "psql -c 'DROP DATABASE crm'")"
ask "Edit the person's own SOP (sops/ folder)" Edit "$(J file_path "$D/sops/team-sop.md" old_string must new_string should)"
ask "Write over the person's own SOP" Write "$(J file_path "$D/onboarding-sop.md" content new)"
ask "sed -i on the person's own SOP (Round C F11)" Bash "$(J command "sed -i '' 's/must/should/' $D/sops/team-sop.md")"
ask "rm the person's own SOP" Bash "$(J command "rm $D/onboarding-sop.md")"
ask "mv the person's own SOP away" Bash "$(J command "mv $D/onboarding-sop.md $D/old.md")"
ask "redirect overwrite of an SOP" Bash "$(J command "echo x > $D/sops/team-sop.md")"
ask "Write a NEW placement.conf" Write "$(J file_path "$HOME/.config/lifehack/placement.conf" content "off	code-in-notes")"
ask "append an off line to placement.conf" Bash "$(J command "printf 'off\tcode-in-notes\n' >> $HOME/.config/lifehack/placement.conf")"
ask "echo >> placement.conf" Bash "$(J command "echo 'off	own-list' >> ~/.config/lifehack/placement.conf")"
ask "sed -i placement.conf" Bash "$(J command "sed -i '' 's/a/b/' $HOME/.config/lifehack/placement.conf")"
ask "tee placement.conf" Bash "$(J command "echo x | tee $HOME/.config/lifehack/placement.conf")"
ask "python writes placement.conf" Bash "$(J command "python3 -c \"open('$HOME/.config/lifehack/placement.conf','a').write('off\tx')\"")"
ask "Edit placement.conf" Edit "$(J file_path "$HOME/.config/lifehack/placement.conf" old_string a new_string b)"
# each switch is independent: only its own piece asks
run "$FC" s Bash "$(J command "rm -rf $D/data-folder")" ROUNDB_FC_DB_DELETE_ASK=on; if ! asked; then ok "folder delete is silent when only the db switch is on"; else bad "switch independence"; fi
run "$FC" s Bash "$(J command "rm $D/notes.db")" ROUNDB_FC_FOLDER_DELETE_ASK=on; if ! asked; then ok "db delete is silent when only the folder switch is on"; else bad "switch independence 2"; fi
# ---------------- fine china has NO user off-switch: a placement.conf full of off lines changes nothing
printf 'off\tfc_user_sop_ask\noff\tfc_db_delete_ask\noff\tfc_folder_delete_ask\noff\tfc_placement_conf_ask\nfc_user_sop_ask\toff\n' > "$HOME/.config/lifehack/placement.conf"
for pair in "Bash|rm $D/app.sqlite" "Bash|rm -rf $D/data-folder" "Bash|rm $D/onboarding-sop.md" "Bash|echo x >> $HOME/.config/lifehack/placement.conf"; do
  run "$FC" s "${pair%%|*}" "$(J command "${pair#*|}")" $ALL ROUNDB_PLACEMENT_USER_OFF=on; if asked; then ok "off lines in placement.conf do not silence: ${pair#*|}"; else bad "fine china off-switch leaked: ${pair#*|}"; fi
done
rm -f "$HOME/.config/lifehack/placement.conf"
# ---------------- placement off-switch (A.6) on guard_build_mode
BMR() { run "$BM" "$@"; }   # BMR <sid> <tool> <json> [env...]
WN="$NOTES/newtool.sh"
BMR sess1 Write "$(J file_path "$WN" content 'echo hi')"; if [ $RC -eq 2 ]; then ok "placement stop fires (code-in-notes) with no off line"; else bad "placement stop baseline"; fi; say "baseline" 0
printf 'off\tcode-in-notes\n' > "$HOME/.config/lifehack/placement.conf"
BMR sess2 Write "$(J file_path "$WN" content 'echo hi')" ROUNDB_PLACEMENT_USER_OFF=on; if [ $RC -eq 0 ]; then ok "off<TAB>code-in-notes switches that check off"; else bad "off line ignored"; fi
BMR sess3 Write "$(J file_path "$WN" content 'echo hi')"; if [ $RC -eq 2 ]; then ok "switch placement_user_off OFF: the off line does nothing"; else bad "off line honoured with the switch off"; fi
rm -f "$HOME/.config/lifehack/placement.conf"; rm -f "$HOME/.config/lifehack/placement-stops.json"
for i in 1 2 3; do BMR "cnt$i" Write "$(J file_path "$WN" content 'echo hi')" ROUNDB_PLACEMENT_USER_OFF=on; if [ $i -lt 3 ]; then grep -q "turning this off may break" "$T/err" && bad "hint too early at stop $i" || ok "no off-switch hint at stop $i"; else grep -q "off.*code-in-notes" "$T/err" && grep -q "Lifehack is built to work this way; turning this off may break" "$T/err" && ok "3rd stop adds how to switch off + warning" || bad "3rd-stop hint missing: $(head -c 300 "$T/err")"; fi; done
say "3rd stop" 0
# skills native home (A.2)
SK="$PC/skills/pondkeeper/SKILL.md"
BMR sk1 Write "$(J file_path "$SK" content hi)" ROUNDB_SKILLS_NATIVE_HOME=on; if [ $RC -eq 2 ] && grep -q "~/.claude/skills" "$T/err"; then ok "a SKILL.md under <personal code>/skills gets the 'not loaded' stop"; else bad "skill-not-loaded stop: $(head -c 200 "$T/err")"; fi
BMR sk2 Write "$(J file_path "$SK" content hi)"; [ $RC -eq 2 ] && grep -q "skill-not-loaded" "$T/err" && bad "skill-not-loaded fired with its switch off" || ok "skills_native_home OFF: no skill-not-loaded stop"
NS="$HOME/.claude/skills/newskill/SKILL.md"
BMR sk3 Write "$(J file_path "$NS" content hi)" ROUNDB_SKILL_EDIT_ASK=on ROUNDB_SKILLS_NATIVE_HOME=on; [ $RC -eq 2 ] && BMR sk3 Write "$(J file_path "$NS" content hi)" ROUNDB_SKILL_EDIT_ASK=on ROUNDB_SKILLS_NATIVE_HOME=on
if ! asked; then ok "building a NEW personal skill in ~/.claude/skills draws no ask (skills_native_home ON)"; else bad "new skill asked"; fi
mkdir -p "$HOME/.claude/skills/oldskill"; echo old > "$HOME/.claude/skills/oldskill/SKILL.md"
BMR sk4 Edit "$(J file_path "$HOME/.claude/skills/oldskill/SKILL.md" old_string old new_string new)" ROUNDB_SKILL_EDIT_ASK=on ROUNDB_SKILLS_NATIVE_HOME=on; if asked; then ok "editing an EXISTING skill still asks"; else bad "existing skill edit lost its ask"; fi
BMR sk5 Write "$(J file_path "$T/home/Desktop/foo/SKILL.md" content hi)" ROUNDB_PLACEMENT_OUTSIDE_HOMES=on ROUNDB_REASON_GATE=on ROUNDB_SKILLS_NATIVE_HOME=on; if [ $RC -eq 2 ] && grep -q "WHERE IT BELONGS: ~/.claude/skills/foo/SKILL.md" "$T/err"; then ok "outside-homes stop sends a SKILL.md to ~/.claude/skills/<name>/"; else bad "outside-homes skill message: $(head -c 300 "$T/err")"; fi
BMR sc1 Write "$(J file_path "$T/home/Desktop/foo/tool.py" content 'print(1)')" ROUNDB_PLACEMENT_OUTSIDE_HOMES=on ROUNDB_REASON_GATE=on ROUNDB_SKILLS_NATIVE_HOME=on; if [ $RC -eq 2 ] && grep -q "ONE folder for all your standalone scripts" "$T/err"; then ok "a standalone script is sent to the ONE personal code folder"; else bad "script message"; fi
# own_list_add suggestion (A.2)
mkdir -p "$T/home/Desktop/bar"; echo hi > "$T/home/Desktop/bar/SKILL.md"
OUT1="$(ROUNDB_SKILLS_NATIVE_HOME=on python3 "$HERE/../../shared/tools/own_list_add.py" --unhomed "$T/home/Desktop/bar/SKILL.md" 2>&1)"
echo "$OUT1" | grep -q ".claude/skills/bar/SKILL.md" && ! echo "$OUT1" | grep -q "pc/skills" && ok "own_list_add --unhomed points a skill at ~/.claude/skills/<name>/" || bad "own_list_add suggestion: $OUT1"
OUT2="$(python3 "$HERE/../../shared/tools/own_list_add.py" --unhomed "$T/home/Desktop/bar/SKILL.md" 2>&1)"
echo "$OUT2" | grep -q "pc/skills/bar" && ok "own_list_add switch OFF = old suggestion" || bad "own_list_add old behaviour: $OUT2"
# ---------------- WATCH-ONLY mode (B.5)
WL="$HOME/.claude/run/watch/watch-log.jsonl"; rm -f "$WL"
run "$FC" w1 Bash "$(J command "rm -rf $D/data-folder")" ROUNDB_FC_FOLDER_DELETE_ASK=on LIFEHACK_WATCH=1
if [ ! -s "$T/out" ] && [ $RC -eq 0 ] && grep -q '"switch": \["fc_folder_delete_ask"\]' "$WL" && grep -q '"would_decision": "ask"' "$WL"; then ok "watch: the ask is logged (switch, would_decision) and NOT given"; else bad "watch log: $(cat "$WL" 2>/dev/null | head -c 300)"; fi
run "$FC" w2 Bash "$(J command "rm -rf $D/data-folder")" ROUNDB_FC_FOLDER_DELETE_ASK=on LIFEHACK_WATCH=0; if asked; then ok "LIFEHACK_WATCH=0 = enforce"; else bad "watch=0 enforce"; fi
run "$FC" w3 Bash "$(J command "ls $D")" ROUNDB_FC_FOLDER_DELETE_ASK=on LIFEHACK_WATCH=1; [ $(wc -l < "$WL") -eq 1 ] && ok "watch: a harmless command logs nothing" || bad "watch logged a harmless command"
mkdir -p "$CODE/system/sops"; echo "# s" > "$CODE/system/sops/skill-building-sop.md"
run "$BM" w4 Bash "$(J command "echo x > $CODE/system/sops/skill-building-sop.md")" ROUNDB_FC_SHELL_OVERWRITE=on LIFEHACK_WATCH=1
if [ $RC -eq 0 ] && grep -q '"switch": \["fc_shell_overwrite"\]' "$WL" && grep -q '"would_decision": "block"' "$WL"; then ok "watch: a would-be BLOCK (shell overwrite of an SOP) is logged, exit 0, nothing blocked"; else bad "watch block: rc=$RC $(tail -1 "$WL" | head -c 300)"; fi
run "$BM" w5 Bash "$(J command "echo x > $CODE/system/sops/skill-building-sop.md")" ROUNDB_FC_SHELL_OVERWRITE=on; [ $RC -eq 2 ] && ok "same call without watch is blocked (exit 2)" || bad "enforce baseline for watch"
# conf-driven watch (no env): copy the hooks to a scratch plugin tree whose roundB.conf has mode=watch + one switch on
cp -R "$HERE" "$T/hooks-copy"; sed -i.bak 's/^fc_folder_delete_ask=off/fc_folder_delete_ask=on/' "$T/hooks-copy/roundB.conf"; grep -q '^mode=watch' "$T/hooks-copy/roundB.conf" || echo 'mode=watch' >> "$T/hooks-copy/roundB.conf"
rm -f "$WL"; run "$T/hooks-copy/guard_fine_china_ask.sh" w6 Bash "$(J command "rm -rf $D/data-folder")"
if [ ! -s "$T/out" ] && grep -q fc_folder_delete_ask "$WL" 2>/dev/null; then ok "watch from roundB.conf alone (mode=watch + switch on, no env, no settings.json)"; else bad "conf-driven watch: rc=$RC $(cat "$WL" 2>/dev/null | head -c 200)"; fi
sed -i.bak 's/^mode=watch/mode=enforce/' "$T/hooks-copy/roundB.conf"; run "$T/hooks-copy/guard_fine_china_ask.sh" w7 Bash "$(J command "rm -rf $D/data-folder")"; asked && ok "mode=enforce: the ask is given" || bad "mode=enforce"
# FAIL-OPEN CHECK (Round D integrator): the WATCHER crashing must never skip the real guard. Four ways it can die; each time the real guard still asks / blocks.
for kind in raise syntax silent-exit0 missing; do
  rm -rf "$T/hooks-crash"; cp -R "$HERE" "$T/hooks-crash"
  case "$kind" in
    raise) printf 'import not_a_real_module_xyz\n' > "$T/hooks-crash/lib/watch_run.py" ;;
    syntax) printf 'def (:\n' > "$T/hooks-crash/lib/watch_run.py" ;;
    silent-exit0) printf 'import sys\nsys.stdin.buffer.read()\nsys.exit(0)\n' > "$T/hooks-crash/lib/watch_run.py" ;;
    missing) printf 'import os,sys\nos.kill(os.getpid(), 9)\n' > "$T/hooks-crash/lib/watch_run.py" ;;
  esac
  run "$T/hooks-crash/guard_fine_china_ask.sh" fo1 Bash "$(J command "rm -rf $D/data-folder")" ROUNDB_FC_FOLDER_DELETE_ASK=on LIFEHACK_WATCH=1
  if asked; then ok "watcher crash [$kind]: the real fine-china guard still ASKS"; else bad "watcher crash [$kind]: guard skipped (rc=$RC)"; fi
  run "$T/hooks-crash/guard_build_mode.sh" fo2 Bash "$(J command "echo x > $CODE/system/sops/skill-building-sop.md")" ROUNDB_FC_SHELL_OVERWRITE=on LIFEHACK_WATCH=1
  if [ $RC -eq 2 ]; then ok "watcher crash [$kind]: the real build-mode guard still BLOCKS (exit 2)"; else bad "watcher crash [$kind]: block skipped (rc=$RC)"; fi
done
echo "test_fine_china_ask: $P passed, $F failed"; [ "$F" -eq 0 ]
