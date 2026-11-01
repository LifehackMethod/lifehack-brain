#!/bin/bash
# Matrix for the one-off-script nudge (plan PHASE 3b.6, B05 / P-51): switch `oneoff_script_nudge` in roundB.conf,
# read by system/hooks/end_of_turn_checks.sh (Stop) and recorded by system/hooks/turn_write_recorder.sh (PostToolUse).
# Fired through the REAL entry scripts under a temp HOME. Asserts exit code AND reads the printed message.
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PLUG="$(cd "$HERE/../.." && pwd -P)"; REC="$HERE/turn_write_recorder.sh"; EOT="$HERE/end_of_turn_checks.sh"
T="$(cd "$(mktemp -d)" && pwd -P)"; trap 'rm -rf "$T"' EXIT
export HOME="$T/hm"; PC="$T/hm/my-code"; WORK="$T/work"; export LHB_TURN_WRITES_DIR="$T/tw"
mkdir -p "$HOME/.config/lifehack" "$PC/tools" "$WORK" "$T/work/scratch"; echo "$PC" > "$HOME/.config/lifehack/personal-code"
unset ROUNDB_BACK_DOOR ROUNDB_OWN_LIST ROUNDB_OWN_LIST_UNHOMED ROUNDB_ONEOFF_SCRIPT_NUDGE
pass=0; fail=0
ok()  { pass=$((pass+1)); printf '   ok   %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL  %s\n' "$1"; }
# rec <session> <prompt> <file>   (a Write that created the file)
rec() { python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"prompt_id":sys.argv[2],"cwd":sys.argv[4],"hook_event_name":"PostToolUse","tool_name":"Write","tool_input":{"file_path":sys.argv[3],"content":"x"},"tool_response":{"type":"create"}}))' "$1" "$2" "$3" "$WORK" | bash "$REC" >"$T/rec.out" 2>&1; }
# transcript <name> <user text> [assistant text] -> path in TP
transcript() { TP="$T/$1.jsonl"; python3 -c 'import json,sys; f=open(sys.argv[1],"w"); f.write(json.dumps({"type":"user","message":{"role":"user","content":sys.argv[2]}})+"\n"); f.write(json.dumps({"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":sys.argv[3]},{"type":"tool_use","name":"Write","input":{"file_path":"/x/keep-me.py"}}]}})+"\n"); f.write(json.dumps({"type":"user","message":{"role":"user","content":[{"type":"tool_result","content":"please keep this in mind: reuse everything"}]}})+"\n")' "$TP" "$2" "${3:-Done, here is the script.}"; }
# stop <session> <prompt> <transcript path> [active] -> OUT RC
stop() { python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"prompt_id":sys.argv[2],"cwd":sys.argv[5],"transcript_path":sys.argv[3],"hook_event_name":"Stop","stop_hook_active":sys.argv[4]=="true","last_assistant_message":"done"}))' "$1" "$2" "$3" "${4:-false}" "$WORK" | bash "$EOT" >"$T/o" 2>"$T/e"; RC=$?; OUT="$(cat "$T/o")"; ERR="$(cat "$T/e")"; }
reason() { printf '%s' "$OUT" | python3 -c 'import json,sys; print(json.load(sys.stdin)["reason"])' 2>/dev/null; }
mkfile() { mkdir -p "$(dirname "$1")"; printf '%s' "$2" > "$1"; }
silent() { [ "$RC" = 0 ] && [ -z "$OUT$ERR" ]; }

echo "== SWITCH IS A REAL LINE =="
grep -qE '^oneoff_script_nudge=off$' "$HERE/roundB.conf" && ok "roundB.conf has a real line oneoff_script_nudge=off" || bad "no real line oneoff_script_nudge=off"
[ "$(grep -cE '^[[:space:]]*#.*oneoff_script_nudge=' "$HERE/roundB.conf")" -le 1 ] && ok "mentioned in at most one comment, never only inside one" || bad "switch text only in comments?"
( . "$HERE/lib/roundb.sh"; roundb_on oneoff_script_nudge ) && bad "default is ON" || ok "default (no env) reads OFF through roundb_on"
( . "$HERE/lib/roundb.sh"; ROUNDB_ONEOFF_SCRIPT_NUDGE=on roundb_on oneoff_script_nudge ) && ok "env ROUNDB_ONEOFF_SCRIPT_NUDGE=on reads ON" || bad "env override not honoured"

echo "== SILENT CASES =="
transcript t0 "write me a quick script that counts words"
mkfile "$WORK/count.py" $'print(1)\n'
ROUNDB_ONEOFF_SCRIPT_NUDGE=off rec s1 p1 "$WORK/count.py"; [ ! -e "$T/tw/s1.list" ] && ok "switch OFF: recorder records nothing" || bad "recorded while OFF"
ROUNDB_ONEOFF_SCRIPT_NUDGE=on rec s1 p1 "$WORK/count.py"
ROUNDB_ONEOFF_SCRIPT_NUDGE=off stop s1 p1 "$TP"; silent && ok "switch OFF at Stop: silent exit 0" || bad "acted while OFF: $OUT $ERR"
rec s1b p1 "$WORK/count.py"; stop s1b p1 "$TP"; silent && ok "no env, conf default: silent" || bad "acted with the default: $OUT"
export ROUNDB_ONEOFF_SCRIPT_NUDGE=on
transcript t1 "write me a script, and keep it for next time"
rec s2 p1 "$WORK/count.py"; stop s2 p1 "$TP"; silent && ok "person said keep: silent" || bad "nudged after 'keep': $OUT"
transcript t1b "write me a script" "I wrote it; I can also save it in your personal code folder if you like."
rec s2b p1 "$WORK/count.py"; stop s2b p1 "$TP"; silent && ok "assistant already offered (personal code): silent" || bad "nudged after an offer: $OUT"
transcript t2 "write me notes"
mkfile "$WORK/notes.md" $'# n\n'; mkfile "$WORK/data.txt" $'x\n'; mkfile "$WORK/out.json" $'{}\n'
rec s3 p1 "$WORK/notes.md"; rec s3 p1 "$WORK/data.txt"; rec s3 p1 "$WORK/out.json"; stop s3 p1 "$TP"; silent && ok "non-script files (.md .txt .json): silent" || bad "nudged for non-script: $OUT"
rec s4 p1 "$WORK/count.py"; stop s4 p1 "$TP" true; silent && ok "stop_hook_active: silent" || bad "nudged while active: $OUT"
mkfile "$PC/tools/mine.py" $'print(2)\n'; rec s5 p1 "$PC/tools/mine.py"; transcript t3 "write me a script"; stop s5 p1 "$TP"; silent && ok "script already in the personal code folder: silent" || bad "nudged for a homed script: $OUT"
rec s6 p1 "$WORK/count.py"; stop s6 p1 "$T/does-not-exist.jsonl"; silent && ok "unreadable transcript: silent (no guessing)" || bad "nudged blind: $OUT"
mkfile "$WORK/test_count.py" $'assert 1\n'; rec s7 p1 "$WORK/test_count.py"; transcript t3 "write me a script"; stop s7 p1 "$TP"; silent && ok "test_*.py: silent" || bad "nudged for a test file: $OUT"

echo "== FIRES =="
transcript t4 "write me a quick script that counts words in my file"
# a real transcript also holds injected context (api-request-blob / <system-reminder> text) full of the word "keep": it must NOT count as the person saying keep
python3 -c 'import json,sys; f=open(sys.argv[1],"a"); f.write(json.dumps({"type":"api-request-blob","message":{"role":"user","content":[{"type":"text","text":"Keep the personal code folder tidy; reuse shared tools"}]}})+"\n"); f.write(json.dumps({"type":"user","message":{"role":"user","content":"<system-reminder> keep going, personal code </system-reminder>"}})+"\n")' "$TP"
rec f1 p1 "$WORK/count.py"; stop f1 p1 "$TP"; R="$(reason)"
[ "$RC" = 0 ] && printf '%s' "$OUT" | grep -q '"decision": *"block"' && ok "new .py in the working folder: one note, exit 0, JSON well-formed" || bad "no note: rc=$RC out=$OUT err=$ERR"
printf '%s' "$R" | grep -q "count.py" && printf '%s' "$R" | grep -q "keep it" && ok "message names the file and offers to keep it" || bad "message lacks file/offer: $R"
printf '%s' "$R" | grep -qF "python3 $PLUG/shared/tools/own_list_add.py $PC/tools/count.py" && ok "message carries the own-list command for <personal>/tools/" || bad "no own-list command: $R"
printf '%s' "$R" | grep -q "nothing to fix" && ok "message says nothing is to be fixed" || bad "not marked as non-blocking note"
transcript t5 "write me a shell helper"
mkfile "$WORK/scratch/helper.sh" $'#!/bin/bash\necho hi\n'; rec f2 p1 "$WORK/scratch/helper.sh"; stop f2 p1 "$TP"; R="$(reason)"
[ "$RC" = 0 ] && printf '%s' "$R" | grep -q "helper.sh" && ok "new .sh in a scratch folder: note" || bad "scratch .sh missed: $OUT"
mkfile "$T/aaa-temp/probe.sh" $'echo p\n'; rec f3 p1 "$T/aaa-temp/probe.sh"; stop f3 p1 "$TP"; printf '%s' "$(reason)" | grep -q "probe.sh" && ok "new .sh in a temp folder: note" || bad "temp .sh missed: $OUT"

echo "== ONCE ONLY =="
mkfile "$WORK/second.py" $'print(9)\n'; rec f1 p2 "$WORK/second.py"; stop f1 p2 "$TP"; silent && ok "second new script, same session: silent" || bad "nagged twice: $OUT"
rec f1 p3 "$WORK/count.py"; stop f1 p3 "$TP"; silent && ok "same file again, next turn: silent" || bad "same file re-flagged: $OUT"
[ -e "$T/tw/f1.oneoff" ] && ok "once-marker present for the session" || bad "no marker"
rec f4 p1 "$WORK/second.py"; stop f4 p1 "$TP"; printf '%s' "$(reason)" | grep -q "second.py" && ok "a different session is still offered once" || bad "other session silenced: $OUT"
rec f4 p2 "$WORK/count.py"; stop f4 p2 "$TP"; silent && ok "...and then not again" || bad "f4 nagged"

echo "== DOES NOT STACK ON ANOTHER FINDING =="
BADSH=$'#!/bin/bash\n'"cu""rl -s https://example.org/data || true"$'\n'
mkfile "$WORK/fetch-bad.sh" "$BADSH"
ROUNDB_BACK_DOOR=on rec g1 p1 "$WORK/fetch-bad.sh"; ROUNDB_BACK_DOOR=on stop g1 p1 "$TP"; R="$(reason)"
printf '%s' "$R" | grep -q "hides_failure" && ! printf '%s' "$R" | grep -q "one-off script" && ok "another finding present: only that finding is raised (no stacked nudge)" || bad "stacked: $R"

echo; echo "passed $pass, failed $fail"; [ "$fail" = 0 ]
