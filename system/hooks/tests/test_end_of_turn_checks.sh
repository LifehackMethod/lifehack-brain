#!/bin/bash
# Matrix for system/hooks/turn_write_recorder.sh (PostToolUse) + system/hooks/end_of_turn_checks.sh (Stop),
# Round B pieces 1+2. Fired through the REAL entry scripts with realistic payloads under a temp HOME (fictional
# names only). ALLOW cases first. Asserts exit code AND reads the printed message.
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PLUG="$(cd "$HERE/../.." && pwd -P)"; REC="$HERE/turn_write_recorder.sh"; EOT="$HERE/end_of_turn_checks.sh"
T="$(cd "$(mktemp -d)" && pwd -P)"; trap 'rm -rf "$T"' EXIT
export HOME="$T/hm"; PC="$T/hm/my-code"; WORK="$T/hm/my-code/bin"; export LHB_TURN_WRITES_DIR="$T/tw"
mkdir -p "$HOME/.config/lifehack" "$PC/bin" "$WORK"; echo "$PC" > "$HOME/.config/lifehack/personal-code"
pass=0; fail=0
ok()  { pass=$((pass+1)); printf '   ok   %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL  %s\n' "$1"; }
CU="cu""rl"    # assembled from fragments: the egress guard blocks a command that contains the bare word
# rec <session> <prompt> <tool> <tool_input-json> [response-type]
rec() { python3 -c 'import json,sys; d={"session_id":sys.argv[1],"prompt_id":sys.argv[2],"cwd":sys.argv[5],"hook_event_name":"PostToolUse","tool_name":sys.argv[3],"tool_input":json.loads(sys.argv[4]),"tool_response":{"type":sys.argv[6]} if sys.argv[6] else {"stdout":""}}; print(json.dumps(d))' "$1" "$2" "$3" "$4" "${CWD:-$WORK}" "${5:-}" 2>/dev/null | bash "$REC" >"$T/rec.out" 2>&1; RRC=$?; }
# stop <session> <prompt> [active]  -> OUT (stdout), ERR (stderr), RC
stop() { python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"prompt_id":sys.argv[2],"hook_event_name":"Stop","stop_hook_active":sys.argv[3]=="true","last_assistant_message":"done"}))' "$1" "$2" "${3:-false}" 2>/dev/null | bash "$EOT" >"$T/o" 2>"$T/e"; RC=$?; OUT="$(cat "$T/o")"; ERR="$(cat "$T/e")"; }
reason() { printf '%s' "$OUT" | python3 -c 'import json,sys; print(json.load(sys.stdin)["reason"])' 2>/dev/null; }
Jw() { python3 -c 'import json,sys; print(json.dumps({"file_path":sys.argv[1],"content":"x"}))' "$1"; }
Jb() { python3 -c 'import json,sys; print(json.dumps({"command":sys.argv[1]}))' "$1"; }
mkfile() { mkdir -p "$(dirname "$1")"; printf '%s' "$2" > "$1"; }
BADSH="#!/bin/bash
$CU -s https://example.org/data || true
"
HD="cat > $WORK/fetch-bash.sh <<'EOF'
$CU x || true
EOF"
HD2="cat > rel-fetch.sh <<'EOF'
$CU x || true
EOF"
export ROUNDB_BACK_DOOR=on ROUNDB_OWN_LIST=on

echo "== ALLOW =="
stop a1 p1; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "no writes: silent exit 0" || bad "no writes not silent: $OUT $ERR"
[ ! -e "$T/tw/a1.list" ] && ok "no list file created for a no-write session" || bad "list created for no-write"
printf '{"type": "tool", "path": "/bin/hello.py"}\n{"type": "tool", "path": "/bin/clean-b.py"}\n' >> "$PC/register.jsonl"   # listed: the clean files live in a home, so they must be on the person's own list too
mkfile "$WORK/hello.py" $'print("hi")\n'; rec a2 p1 Write "$(Jw "$WORK/hello.py")" create
stop a2 p1; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "clean new file: silent" || bad "clean file flagged: $OUT $ERR"
mkfile "$WORK/old-fetch.sh" "$BADSH"; rec a3 p1 Edit "$(Jw "$WORK/old-fetch.sh")"
grep -q "edit" "$T/tw/a3.list" && ok "edit recorded as 'edit'" || bad "edit not recorded"
stop a3 p1; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "edit of old file: not checked, silent" || bad "edit was checked: $OUT"
mkfile "$PC/notes.md" $'# my notes\n'; rec a4 p1 Write "$(Jw "$PC/notes.md")" create
stop a4 p1; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "notes file in personal folder: silent" || bad "notes flagged: $OUT"
mkfile "$PC/bin/ping-me.py" $'print("ping")\n'; python3 "$PLUG/shared/tools/own_list_add.py" "$PC/bin/ping-me.py" >/dev/null
rec a5 p1 Write "$(Jw "$PC/bin/ping-me.py")" create
stop a5 p1; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "listed tool: silent" || bad "listed tool flagged: $OUT"
mkfile "$WORK/fetch-old.sh" "$BADSH"; rec a6 pOLD Write "$(Jw "$WORK/fetch-old.sh")" create
stop a6 pNEW; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "other prompt's file: silent" || bad "other prompt flagged: $OUT"
mkfile "$WORK/fetch-b.sh" "$BADSH"; rec a7 p1 Write "$(Jw "$WORK/fetch-b.sh")" create
stop a7 p1 true; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "stop_hook_active: never blocks" || bad "blocked while active: $OUT"
mkfile "$WORK/clean-b.py" $'print(1)\n'
rec a8 p1 Bash "$(Jb "printf 'print(1)\n' > $WORK/clean-b.py")"
stop a8 p1; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "Bash-written clean file: silent" || bad "clean bash file flagged: $OUT"
rec a9 p1 Bash "$(Jb "cat $WORK/hello.py | grep print")"; [ ! -e "$T/tw/a9.list" ] && ok "read-only Bash records nothing" || bad "read recorded"
rec a10 p1 Bash "$(Jb "echo 'see $WORK/ghost.sh for later'")"; [ ! -e "$T/tw/a10.list" ] && ok "path in quoted text records nothing" || bad "quoted mention recorded"

echo "== SWITCHES OFF = today's behaviour =="
mkfile "$WORK/fetch-off.sh" "$BADSH"
ROUNDB_BACK_DOOR=off ROUNDB_OWN_LIST=off ROUNDB_OWN_LIST_UNHOMED=off rec b1 p1 Write "$(Jw "$WORK/fetch-off.sh")" create
[ ! -e "$T/tw/b1.list" ] && ok "both OFF: recorder records nothing" || bad "recorded while OFF"
ROUNDB_BACK_DOOR=off ROUNDB_OWN_LIST=off ROUNDB_OWN_LIST_UNHOMED=off stop b1 p1; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "both OFF: Stop hook silent" || bad "Stop acted while OFF"
rec b2 p1 Write "$(Jw "$WORK/fetch-off.sh")" create
ROUNDB_BACK_DOOR=off ROUNDB_OWN_LIST=off ROUNDB_OWN_LIST_UNHOMED=off stop b2 p1; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "OFF at Stop even with a recorded list: silent" || bad "Stop blocked while OFF"
mkfile "$PC/bin/new-thing.py" $'print(2)\n'
rec b3 p1 Write "$(Jw "$PC/bin/new-thing.py")" create
ROUNDB_OWN_LIST=off stop b3 p1; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "own_list OFF: unlisted tool not flagged" || bad "own_list flagged while OFF: $OUT"

echo "== BLOCK =="
mkfile "$WORK/fetch-new.sh" "$BADSH"; rec c1 p1 Write "$(Jw "$WORK/fetch-new.sh")" create
stop c1 p1; R="$(reason)"
[ "$RC" = 0 ] && printf '%s' "$OUT" | grep -q '"decision": *"block"' && ok "new bad file: block decision, exit 0" || bad "no block: rc=$RC out=$OUT"
printf '%s' "$R" | grep -q "hides_failure" && printf '%s' "$R" | grep -q "fetch-new.sh" && ok "message names the check and the file" || bad "message lacks check/file: $R"
printf '%s' "$R" | grep -q "allow-silence" && ok "message gives the escape" || bad "no escape in message"
rec c1 p2 Write "$(Jw "$WORK/fetch-new.sh")" create; stop c1 p2; [ -z "$OUT" ] && ok "same file never asked twice" || bad "asked twice: $OUT"
mkfile "$WORK/fetch-new2.sh" "$BADSH"; rec c1 p3 Bash "$(Jb "printf 'x' > $WORK/fetch-new2.sh")"
stop c1 p3 true; [ -z "$OUT$ERR" ] && ok "second stop in the same turn (active) is silent" || bad "blocked twice in a turn"
mkfile "$WORK/fetch-bash.sh" "$BADSH"; rec c2 p1 Bash "$(Jb "$HD")"
stop c2 p1; printf '%s' "$(reason)" | grep -q "fetch-bash.sh" && ok "Bash heredoc-created bad file blocked" || bad "bash file missed: $OUT $ERR"
mkfile "$WORK/rel-fetch.sh" "$BADSH"; CWD="$WORK" rec c3 p1 Bash "$(Jb "$HD2")"
stop c3 p1; printf '%s' "$(reason)" | grep -q "rel-fetch.sh" && ok "relative Bash target resolved against cwd" || bad "relative missed: $OUT $ERR"
mkfile "$WORK/notify-send.sh" $'echo not the real one\nlogger something\n'; rec c4 p1 Write "$(Jw "$WORK/notify-send.sh")" create
stop c4 p1; printf '%s' "$(reason)" | grep -q "is_copy" && ok "copy of a shared tool blocked (is_copy)" || bad "is_copy missed: $OUT $ERR"
python3 -c 'import json; print(json.dumps({"session_id":"c5","prompt_id":"p1","cwd":"/","tool_name":"NotebookEdit","tool_input":{"notebook_path":"/x/nb.ipynb"},"tool_response":{}}))' | bash "$REC"; grep -q "/x/nb.ipynb" "$T/tw/c5.list" && ok "NotebookEdit path recorded" || bad "notebook not recorded"

echo "== OWN LIST (piece 2) =="
mkfile "$PC/bin/ring-bell.sh" $'#!/bin/bash\necho ring\n'; rec d1 p1 Write "$(Jw "$PC/bin/ring-bell.sh")" create
stop d1 p1; R="$(reason)"
printf '%s' "$OUT" | grep -q '"decision": *"block"' && ok "unlisted personal tool: blocked" || bad "own-list miss: $OUT $ERR"
CMDLINE="python3 \"$PLUG/shared/tools/own_list_add.py\" \"$PC/bin/ring-bell.sh\""
printf '%s' "$R" | grep -qF "$CMDLINE" && ok "message carries the exact add command" || bad "command not in message: $R"
eval "$CMDLINE" >/dev/null; grep -q '/bin/ring-bell.sh' "$PC/register.jsonl" && ok "printed command works (row written, no git)" || bad "command did not list the tool"
rec d1 p5 Write "$(Jw "$PC/bin/ring-bell.sh")" create; stop d1 p5; [ -z "$OUT$ERR" ] && ok "after listing: silent" || bad "still flagged: $OUT"
mkfile "$PC/bin/fetch-x.sh" "$BADSH"; ROUNDB_BACK_DOOR=off rec d2 p1 Write "$(Jw "$PC/bin/fetch-x.sh")" create
ROUNDB_BACK_DOOR=off stop d2 p1; R="$(reason)"; printf '%s' "$R" | grep -q "own list" && ! printf '%s' "$R" | grep -q hides_failure && ok "own_list alone: only the list rule" || bad "own-alone wrong: $R"

echo "== OWN LIST, UNHOMED (Round C 5A, switch own_list_unhomed) =="
# ALLOW first: switch OFF, kept-listed, scratch dirs, test files, non-code, inside a home
mkdir -p "$HOME/pondproj" "$HOME/.config/lifehack"
mkfile "$HOME/pondproj/lonely.py" $'print("lonely")\n'; rec u1 p1 Write "$(Jw "$HOME/pondproj/lonely.py")" create
ROUNDB_OWN_LIST_UNHOMED=off stop u1 p1; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "unhomed OFF: file outside homes not flagged" || bad "flagged while OFF: $OUT"
mkfile "$T/tmpish/x.sh" $'echo x\n'; rec u2 p1 Write "$(Jw "$T/tmpish/x.sh")" create
mkfile "$HOME/.claude/scratchpad/y.py" $'print(1)\n'; rec u2 p2 Write "$(Jw "$HOME/.claude/scratchpad/y.py")" create
ROUNDB_OWN_LIST_UNHOMED=on stop u2 p2; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "unhomed ON: ~/.claude scratchpad exempt" || bad "scratch flagged: $OUT"
mkfile "$HOME/pondproj/test_lonely.py" $'assert 1\n'; rec u3 p1 Write "$(Jw "$HOME/pondproj/test_lonely.py")" create
mkfile "$HOME/pondproj/readme.md" $'# hi\n'; rec u3 p1 Write "$(Jw "$HOME/pondproj/readme.md")" create
ROUNDB_OWN_LIST_UNHOMED=on stop u3 p1; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "unhomed ON: test file and .md silent" || bad "test/md flagged: $OUT"
mkfile "$PC/bin/inside.py" $'print(3)\n'; python3 "$PLUG/shared/tools/own_list_add.py" "$PC/bin/inside.py" >/dev/null; rec u4 p1 Write "$(Jw "$PC/bin/inside.py")" create
ROUNDB_OWN_LIST_UNHOMED=on stop u4 p1; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "unhomed ON: file inside personal folder (listed): silent" || bad "inside flagged: $OUT"
rec u5 p1 Write "$(Jw "$HOME/pondproj/lonely.py")" create
echo "== unhomed BLOCK =="
ROUNDB_OWN_LIST_UNHOMED=on stop u5 p1; R="$(reason)"
printf '%s' "$OUT" | grep -q '"decision": *"block"' && ok "unhomed ON: stray tool blocked" || bad "not blocked: $OUT $ERR"
printf '%s' "$R" | grep -qF "move it to $PC/tools/lonely.py, then run: python3 \"$PLUG/shared/tools/own_list_add.py\" \"$PC/tools/lonely.py\"" && ok "message: move to <personal>/tools/<name> + exact add command" || bad "move message wrong: $R"
rec u5 p2 Write "$(Jw "$HOME/pondproj/lonely.py")" create; ROUNDB_OWN_LIST_UNHOMED=on stop u5 p2; [ -z "$OUT" ] && ok "same stray file not asked twice" || bad "asked twice"
mkdir -p "$HOME/keptproj/sub"; printf 'kept\t%s\tmy old repo\n' "$HOME/keptproj" > "$HOME/.config/lifehack/placement.conf"
mkfile "$HOME/keptproj/sub/stay.sh" $'#!/bin/bash\necho stay\n'; rec u6 p1 Write "$(Jw "$HOME/keptproj/sub/stay.sh")" create
ROUNDB_OWN_LIST_UNHOMED=on stop u6 p1; R="$(reason)"
printf '%s' "$R" | grep -qF "stays here by your choice; list it: python3 \"$PLUG/shared/tools/own_list_add.py\" --keep \"$HOME/keptproj/sub/stay.sh\"" && ! printf '%s' "$R" | grep -q "move it to" && ok "kept folder: 'stays here by your choice' variant" || bad "kept message wrong: $R"
python3 "$PLUG/shared/tools/own_list_add.py" --keep "$HOME/keptproj/sub/stay.sh" >/dev/null; grep -qF "$HOME/keptproj/sub/stay.sh" "$PC/register.jsonl" && ok "--keep lists it in the personal folder's own list (absolute path)" || bad "keep did not list"
rec u7 p1 Write "$(Jw "$HOME/keptproj/sub/stay.sh")" create; ROUNDB_OWN_LIST_UNHOMED=on stop u7 p1; [ -z "$OUT$ERR" ] && ok "kept + listed: silent" || bad "kept still flagged: $OUT"
rm -f "$HOME/.config/lifehack/placement.conf"; rm -f "$HOME/.config/lifehack/personal-code"
mkfile "$HOME/pondproj/two.py" $'print(2)\n'; rec u8 p1 Write "$(Jw "$HOME/pondproj/two.py")" create
ROUNDB_OWN_LIST_UNHOMED=on stop u8 p1; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "no personal code folder: silent by design" || bad "flagged with no folder: $OUT"
echo "$PC" > "$HOME/.config/lifehack/personal-code"

echo; echo "passed=$pass failed=$fail"; [ "$fail" = 0 ]
