#!/bin/bash
# test_claudemd_protect.sh -- plan PHASE 3b.8 item 5: CLAUDE.md protections inside guard_fine_china_ask.sh.
#   fc_claudemd_ask (5a), fc_claudemd_plugin_copy (5b), claudemd_len_advisory (5c). Each switch is a real line in roundB.conf.
# Both directions (asked / allowed), reads unaffected, every switch OFF = silent. Throwaway HOME and code root; no real CLAUDE.md is touched.
# Run: bash system/hooks/tests/test_claudemd_protect.sh      (VERBOSE=1 prints every case)
HERE="$(cd "$(dirname "$0")/.." && pwd)"; FC="$HERE/guard_fine_china_ask.sh"
T="$(cd "$(mktemp -d)" && pwd -P)"; trap 'rm -rf "$T"' EXIT
export HOME="$T/home"; CODE="$T/code"; CODE2="$T/code2"; NOTES="$T/notes"; PC="$T/pc"
unset LIFEHACK_WATCH LIFEHACK_WATCH_SHADOW LHB_WATCH_CHILD LIFEHACK_SANDBOX CLAUDE_PLUGIN_ROOT; for v in $(env | sed -n 's/^\(ROUNDB_[A-Z0-9_]*\)=.*/\1/p'); do unset "$v"; done
. "$(dirname "${BASH_SOURCE[0]}")/pin_roundb_off.sh"
mkdir -p "$HOME/.config/lifehack" "$HOME/.claude/plugins/cache/mk/lifehack-brain/1.0" "$HOME/proj/sub" "$CODE/shared" "$CODE/system/hooks/lib" "$CODE2/shared" "$CODE2/.git" "$NOTES" "$PC"
for c in "$CODE" "$CODE2"; do cp "$HERE/../../shared/brain_root.py" "$HERE/../../shared/personal_code_root.py" "$HERE/../../shared/person_roots.py" "$HERE/../tools/utf8_stdio.py" "$c/shared/" 2>/dev/null; done
cp "$HERE/lib/roundb.py" "$CODE/system/hooks/lib/"; cp "$HERE/roundB.conf" "$CODE/system/hooks/"; export LIFEHACK_ROOT="$NOTES"
echo "$PC" > "$HOME/.config/lifehack/personal-code"
setcode() { echo "$1" > "$HOME/.config/lifehack/code-root"; }
setcode "$CODE"
mkline() { python3 -c 'import sys; print("\n".join("line %d" % i for i in range(int(sys.argv[1]))))' "$1"; }
D="$HOME/proj"
echo "# rules" > "$D/CLAUDE.md"; echo "# sub" > "$D/sub/CLAUDE.md"; mkdir -p "$D/long" "$D/mid"; mkline 250 > "$D/long/CLAUDE.md"; mkline 150 > "$D/mid/CLAUDE.md"
echo "# user" > "$HOME/.claude/CLAUDE.md"; echo "# plugin" > "$CODE/CLAUDE.md"; echo "# plugin2" > "$CODE2/CLAUDE.md"; echo "# cache" > "$HOME/.claude/plugins/cache/mk/lifehack-brain/1.0/CLAUDE.md"
echo "x" > "$D/notes.md"; echo "x" > "$D/claude.md.txt"; echo "x" > "$D/MYCLAUDE.md"
P=0; F=0; V="${VERBOSE:-}"
J() { python3 -c 'import json,sys; print(json.dumps(dict(zip(sys.argv[1::2],sys.argv[2::2]))))' "$@"; }
run() { local hook="$1" sid="$2" tool="$3" ti="$4"; shift 4
  python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"cwd":sys.argv[2],"tool_name":sys.argv[3],"tool_input":json.loads(sys.argv[4])}))' "$sid" "$HOME/proj" "$tool" "$ti" | env "$@" bash "$hook" >"$T/out" 2>"$T/err"; RC=$?; }
asked() { grep -q '"permissionDecision": "ask"' "$T/out" && [ $RC -eq 0 ]; }
advised() { grep -q '"additionalContext"' "$T/out" && [ $RC -eq 0 ]; }
silent() { [ ! -s "$T/out" ] && [ $RC -eq 0 ]; }
ok() { P=$((P+1)); [ -n "$V" ] && echo "PASS $1"; return 0; }
bad() { F=$((F+1)); echo "FAIL $1 :: rc=$RC $(head -c 300 "$T/out") $(head -c 120 "$T/err")"; }
SA="ROUNDB_FC_CLAUDEMD_ASK=on"; SP="ROUNDB_FC_CLAUDEMD_PLUGIN_COPY=on"; SL="ROUNDB_CLAUDEMD_LEN_ADVISORY=on"
# ---- 5a: asks, and silent with the switch off
a_ask() { # a_ask <name> <tool> <input>
  run "$FC" s "$2" "$3" $SA; if asked && grep -q "WAY-THROUGH" "$T/out" && grep -q "fc_claudemd_ask" "$T/out"; then ok "ASK $1"; else bad "ASK $1"; fi
  run "$FC" s "$2" "$3"; if silent; then ok "ASK $1 [switch off = silent]"; else bad "ASK $1 [off]"; fi
  run "$FC" s "$2" "$3" $SP $SL; if ! asked; then ok "ASK $1 [other switches on, not this one = no ask]"; else bad "ASK $1 [independence]"; fi; }
a_allow() { run "$FC" s "$2" "$3" $SA $SP $SL; if ! asked && ! advised; then ok "ALLOW $1"; else bad "ALLOW $1"; fi; }
a_ask "Edit a project CLAUDE.md" Edit "$(J file_path "$D/CLAUDE.md" old_string rules new_string ruling)"
a_ask "Write over a project CLAUDE.md" Write "$(J file_path "$D/CLAUDE.md" content new)"
a_ask "Edit the user's ~/.claude/CLAUDE.md" Edit "$(J file_path "$HOME/.claude/CLAUDE.md" old_string user new_string me)"
a_ask "Edit a nested CLAUDE.md" Edit "$(J file_path "$D/sub/CLAUDE.md" old_string sub new_string deeper)"
a_ask "MultiEdit a CLAUDE.md" MultiEdit "$(python3 -c 'import json,sys; print(json.dumps({"file_path":sys.argv[1],"edits":[{"old_string":"rules","new_string":"r2"}]}))' "$D/CLAUDE.md")"
a_ask "redirect > CLAUDE.md" Bash "$(J command "echo x > $D/CLAUDE.md")"
a_ask "append >> CLAUDE.md" Bash "$(J command "echo x >> $D/CLAUDE.md")"
a_ask "tee CLAUDE.md" Bash "$(J command "echo x | tee $D/CLAUDE.md")"
a_ask "tee -a CLAUDE.md" Bash "$(J command "echo x | tee -a $D/CLAUDE.md")"
a_ask "sed -i CLAUDE.md (BSD form)" Bash "$(J command "sed -i '' 's/a/b/' $D/CLAUDE.md")"
a_ask "sed -i CLAUDE.md (GNU form)" Bash "$(J command "sed -i 's/a/b/' $D/CLAUDE.md")"
a_ask "cp over CLAUDE.md" Bash "$(J command "cp $D/notes.md $D/CLAUDE.md")"
a_ask "mv over CLAUDE.md" Bash "$(J command "mv $D/notes.md $D/CLAUDE.md")"
a_ask "relative path after cd" Bash "$(J command "cd $D && echo x > CLAUDE.md")"
a_ask "inside bash -c" Bash "$(J command "bash -c 'echo x > $D/CLAUDE.md'")"
a_ask "heredoc into CLAUDE.md" Bash "$(J command "cat > $D/CLAUDE.md <<'EOT'
hello
EOT")"
run "$FC" s Edit "$(J file_path "$D/CLAUDE.md" old_string rules new_string ruling)" $SA; if grep -q "DIFF" "$T/out" && grep -q "ruling" "$T/out"; then ok "the Edit ask carries a short diff"; else bad "diff missing"; fi
run "$FC" s Write "$(J file_path "$D/CLAUDE.md" content "# brand new text")" $SA; if grep -q "brand new text" "$T/out"; then ok "the Write ask carries a short diff"; else bad "write diff missing"; fi
# ---- allowed
a_allow "Edit a markdown file that is not CLAUDE.md" Edit "$(J file_path "$D/notes.md" old_string x new_string y)"
a_allow "Write a file whose name only contains claude.md" Write "$(J file_path "$D/MYCLAUDE.md" content y)"
a_allow "Write a NEW CLAUDE.md (nothing to lose)" Write "$(J file_path "$D/fresh/CLAUDE.md" content y)"
a_allow "redirect to a NEW CLAUDE.md" Bash "$(J command "echo x > $D/fresh2-CLAUDE.md")"
a_allow "redirect to claude.md.txt" Bash "$(J command "echo x > $D/claude.md.txt")"
a_allow "cat CLAUDE.md" Bash "$(J command "cat $D/CLAUDE.md")"
a_allow "grep CLAUDE.md" Bash "$(J command "grep rules $D/CLAUDE.md")"
a_allow "head/wc/sed -n CLAUDE.md" Bash "$(J command "head -5 $D/CLAUDE.md; wc -l $D/CLAUDE.md; sed -n 1,5p $D/CLAUDE.md")"
a_allow "diff/cp FROM CLAUDE.md" Bash "$(J command "cp $D/CLAUDE.md $D/notes.md")"
a_allow "git add / git diff CLAUDE.md" Bash "$(J command "git add $D/CLAUDE.md; git diff $D/CLAUDE.md")"
a_allow "echo mentions CLAUDE.md into another file" Bash "$(J command "echo 'see CLAUDE.md' > $D/notes.md")"
a_allow "cat CLAUDE.md piped to another file" Bash "$(J command "cat $D/CLAUDE.md > $D/notes.md")"
# ---- 5b: plugin copy message
b_ask() { run "$FC" s "$2" "$3" $SP; if asked && grep -q "replaced on the next update" "$T/out" && grep -q "~/.claude/CLAUDE.md" "$T/out" && grep -q "fc_claudemd_plugin_copy" "$T/out"; then ok "PLUGIN-COPY $1"; else bad "PLUGIN-COPY $1"; fi
  run "$FC" s "$2" "$3"; if silent; then ok "PLUGIN-COPY $1 [off = silent]"; else bad "PLUGIN-COPY $1 [off]"; fi
  run "$FC" s "$2" "$3" $SA; if asked && ! grep -q "replaced on the next update" "$T/out"; then ok "PLUGIN-COPY $1 [only 5a on: general ask, not the update message]"; else bad "PLUGIN-COPY $1 [5a only]"; fi
  run "$FC" s "$2" "$3" $SA $SP; if asked && grep -q "replaced on the next update" "$T/out" && ! grep -q "standing instructions" "$T/out"; then ok "PLUGIN-COPY $1 [both on: the update message wins]"; else bad "PLUGIN-COPY $1 [both]"; fi; }
b_ask "Edit <plugin root>/CLAUDE.md on a student install" Edit "$(J file_path "$CODE/CLAUDE.md" old_string plugin new_string mine)"
b_ask "Write the installed plugin cache copy" Write "$(J file_path "$HOME/.claude/plugins/cache/mk/lifehack-brain/1.0/CLAUDE.md" content y)"
b_ask "Bash redirect onto the plugin root copy" Bash "$(J command "echo x >> $CODE/CLAUDE.md")"
b_ask "sed -i the plugin root copy" Bash "$(J command "sed -i '' 's/a/b/' $CODE/CLAUDE.md")"
run "$FC" s Edit "$(J file_path "$D/CLAUDE.md" old_string rules new_string r2)" $SP; if silent; then ok "5b only: a normal project CLAUDE.md draws nothing"; else bad "5b leaked to a project CLAUDE.md"; fi
run "$FC" s Edit "$(J file_path "$HOME/.claude/CLAUDE.md" old_string user new_string me)" $SP $SA; if asked && ! grep -q "replaced on the next update" "$T/out"; then ok "the person's own ~/.claude/CLAUDE.md never gets the update message"; else bad "user CLAUDE.md got update message"; fi
run "$FC" s Bash "$(J command "cat $CODE/CLAUDE.md")" $SP $SA; if silent; then ok "reading the plugin CLAUDE.md is silent"; else bad "plugin read triggered"; fi
# maintainer self-repo: no update message (a .git work tree outside ~/.claude/plugins), only the general ask
setcode "$CODE2"
run "$FC" s Edit "$(J file_path "$CODE2/CLAUDE.md" old_string plugin2 new_string x)" $SP; if silent; then ok "maintainer self-repo (git work tree): no update message"; else bad "maintainer got update message"; fi
run "$FC" s Edit "$(J file_path "$CODE2/CLAUDE.md" old_string plugin2 new_string x)" $SP $SA; if asked && ! grep -q "replaced on the next update" "$T/out"; then ok "maintainer self-repo: still the general fine-china ask with 5a on"; else bad "maintainer + 5a"; fi
rmdir "$CODE2/.git" 2>/dev/null; mv "$CODE2/CLAUDE.md" "$CODE2/CLAUDE.md.keep"; setcode "$CODE"
# code-zones.txt route, and the sandbox tag
echo "$CODE" > "$PC/code-zones.txt"
run "$FC" s Edit "$(J file_path "$CODE/CLAUDE.md" old_string plugin new_string x)" $SP; if silent; then ok "maintainer self-repo (listed in code-zones.txt): no update message"; else bad "code-zones maintainer"; fi
rm -f "$PC/code-zones.txt"
run "$FC" s Edit "$(J file_path "$CODE/CLAUDE.md" old_string plugin new_string x)" $SP; if asked; then ok "code-zones.txt removed: the update message is back"; else bad "code-zones removal"; fi
run "$FC" s Edit "$(J file_path "$CODE/CLAUDE.md" old_string plugin new_string x)" $SP LIFEHACK_SANDBOX=V2; if silent; then ok "maintainer self-repo (V2 sandbox tag): no update message"; else bad "sandbox maintainer"; fi
# ---- 5c: advisory
l_adv() { run "$FC" s "$2" "$3" $SL; if advised && ! asked && grep -q "200 lines" "$T/out" && grep -q "claudemd_len_advisory" "$T/out"; then ok "ADVISORY $1"; else bad "ADVISORY $1"; fi
  run "$FC" s "$2" "$3"; if silent; then ok "ADVISORY $1 [off = silent]"; else bad "ADVISORY $1 [off]"; fi; }
l_none() { run "$FC" s "$2" "$3" $SL; if silent; then ok "NO ADVISORY $1"; else bad "NO ADVISORY $1"; fi; }
BIG="$(mkline 230)"
l_adv "Write a 230-line CLAUDE.md over an existing one" Write "$(J file_path "$D/CLAUDE.md" content "$BIG")"
l_adv "Edit that grows a 250-line CLAUDE.md" Edit "$(J file_path "$D/long/CLAUDE.md" old_string "line 3" new_string "line 3
extra a
extra b")"
l_adv "Edit that takes a 150-line CLAUDE.md past 200" Edit "$(J file_path "$D/mid/CLAUDE.md" old_string "line 3" new_string "$(mkline 60)")"
l_adv "Write a NEW 230-line CLAUDE.md" Write "$(J file_path "$D/fresh3/CLAUDE.md" content "$BIG")"
l_none "Write a 200-line CLAUDE.md (not past 200)" Write "$(J file_path "$D/CLAUDE.md" content "$(mkline 200)")"
l_none "Edit that keeps a 150-line file under 200" Edit "$(J file_path "$D/mid/CLAUDE.md" old_string "line 3" new_string "line three")"
l_none "Edit that shrinks a 250-line CLAUDE.md (progress, no nag)" Edit "$(J file_path "$D/long/CLAUDE.md" old_string "line 3
line 4" new_string "line 3")"
l_none "Write a 230-line file that is not named CLAUDE.md" Write "$(J file_path "$D/notes.md" content "$BIG")"
l_none "Edit whose old_string is not found (cannot measure)" Edit "$(J file_path "$D/mid/CLAUDE.md" old_string "no such text" new_string "$(mkline 90)")"
run "$FC" s Bash "$(J command "cat $D/long/CLAUDE.md; wc -l $D/long/CLAUDE.md; grep line $D/long/CLAUDE.md")" $SL $SA $SP; if silent; then ok "reading a long CLAUDE.md is silent"; else bad "read of a long CLAUDE.md triggered"; fi
run "$FC" s Write "$(J file_path "$D/CLAUDE.md" content "$BIG")" $SL $SA; if advised && asked; then ok "advisory and ask travel in one answer, ask still present"; else bad "advisory+ask combo"; fi
python3 - "$T/out" <<'PY' || bad "combined answer is not valid JSON"
import json,sys
d=json.load(open(sys.argv[1]))["hookSpecificOutput"]; assert d["permissionDecision"]=="ask" and d["additionalContext"] and d["hookEventName"]=="PreToolUse"
PY
run "$FC" s Edit "$(J file_path "$D/mid/CLAUDE.md" old_string "line 3" new_string "$(mkline 60)")" $SL; python3 - "$T/out" <<'PY' && ok "advisory-only answer has no permissionDecision (does not change permissions)" || bad "advisory carries a permission decision"
import json,sys
d=json.load(open(sys.argv[1]))["hookSpecificOutput"]; assert "permissionDecision" not in d
PY
# ---- every switch OFF: the whole battery is silent
for pair in "Edit|$(J file_path "$D/CLAUDE.md" old_string rules new_string r2)" "Write|$(J file_path "$D/CLAUDE.md" content "$BIG")" "Bash|$(J command "echo x >> $D/CLAUDE.md")" "Edit|$(J file_path "$CODE/CLAUDE.md" old_string plugin new_string x)"; do
  run "$FC" s "${pair%%|*}" "${pair#*|}"; if silent; then ok "all three switches off: silent (${pair%%|*})"; else bad "off but spoke (${pair%%|*})"; fi
done
# ---- the three switches are real lines in roundB.conf, committed OFF
for sw in fc_claudemd_ask fc_claudemd_plugin_copy claudemd_len_advisory; do
  if grep -qE "^${sw}=on\$" "$HERE/roundB.conf"; then ok "roundB.conf has a real committed ${sw}=on line"; else bad "no real ${sw}=on line in roundB.conf"; fi
done
# ---- watch mode: the ask is logged, not given
WL="$HOME/.claude/run/watch/watch-log.jsonl"; rm -f "$WL"
run "$FC" w1 Edit "$(J file_path "$D/CLAUDE.md" old_string rules new_string r2)" $SA LIFEHACK_WATCH=1
if [ ! -s "$T/out" ] && grep -q '"fc_claudemd_ask"' "$WL" 2>/dev/null; then ok "watch mode: logged, nothing given"; else bad "watch: $(head -c 200 "$WL" 2>/dev/null)"; fi
echo "test_claudemd_protect: $P passed, $F failed"; [ "$F" -eq 0 ]
