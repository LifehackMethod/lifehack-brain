#!/bin/bash
# Matrix for switch record_failed_writes (turn_write_recorder.sh on PostToolUseFailure + end_of_turn_checks.sh), exam case D-B06.
# A Bash command that ends non-zero fires PostToolUseFailure, never PostToolUse, so what it wrote was invisible to the end-of-turn check.
# Fired the way the harness fires it: every command registered in hooks/hooks.json under the event, with the matcher applied, never the
# script by hand (a hand-fed script would "pass" on code the harness never calls). Payloads copy a real one captured from Claude Code 2.1.317
# (no tool_response; error, is_interrupt, duration_ms, prompt_id). Commands really run, so their files and exit codes are real. ALLOW cases first.
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PLUG="$(cd "$HERE/../.." && pwd -P)"; EOT="$HERE/end_of_turn_checks.sh"
T="$(cd "$(mktemp -d)" && pwd -P)"; trap 'rm -rf "$T"' EXIT
export HOME="$T/hm"; PC="$T/hm/my-code"; PROJ="$T/hm/pondproj"; export LHB_TURN_WRITES_DIR="$T/tw"
mkdir -p "$HOME/.config/lifehack" "$PC/bin" "$PROJ"; echo "$PC" > "$HOME/.config/lifehack/personal-code"
export ROUNDB_BACK_DOOR=on ROUNDB_OWN_LIST=on ROUNDB_OWN_LIST_UNHOMED=on ROUNDB_INLINE_KEEP_NUDGE=off ROUNDB_RECORD_FAILED_WRITES=on
pass=0; fail=0
ok()  { pass=$((pass+1)); printf '   ok   %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL  %s\n' "$1"; }

# fire <event> <session> <prompt> <tool> <tool_input-json> <duration_ms or ""> -> FRC, FOUT (what the registered hooks returned)
fire() {
  python3 - "$PLUG" "$@" >"$T/fire.out" 2>&1 <<'PY'
import json, os, re, subprocess, sys
plug, event, sid, pid, tool, ti, dur = sys.argv[1:8]
d = {"session_id": sid, "transcript_path": "", "cwd": os.environ.get("FIRE_CWD", ""), "prompt_id": pid, "permission_mode": "default",
     "hook_event_name": event, "tool_name": tool, "tool_input": json.loads(ti), "tool_use_id": "toolu_x"}
if event == "PostToolUseFailure":
    d.update({"error": "Exit code 1", "is_interrupt": False})
    if dur:
        d["duration_ms"] = int(dur)
else:
    d["tool_response"] = {"type": "create"}
reg = json.load(open(os.path.join(plug, "hooks", "hooks.json")))
reg = reg.get("hooks", reg)
env = dict(os.environ, CLAUDE_PLUGIN_ROOT=plug)
rc = 0
for group in reg.get(event, []):
    for h in group["hooks"]:
        if "turn_write_recorder" not in h["command"] or not re.fullmatch(group.get("matcher") or ".*", tool):
            continue
        p = subprocess.run(h["command"], shell=True, input=json.dumps(d), text=True, capture_output=True, env=env)
        rc = rc or p.returncode
        sys.stdout.write(p.stdout + p.stderr)
sys.exit(rc)
PY
  FRC=$?; FOUT="$(cat "$T/fire.out")"
}
stop() { python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"prompt_id":sys.argv[2],"hook_event_name":"Stop","stop_hook_active":False,"last_assistant_message":"done"}))' "$1" "$2" | bash "$EOT" >"$T/o" 2>"$T/e"; RC=$?; OUT="$(cat "$T/o")"; }
reason() { printf '%s' "$OUT" | python3 -c 'import json,sys; print(json.load(sys.stdin)["reason"])' 2>/dev/null; }
Jb() { python3 -c 'import json,sys; print(json.dumps({"command":sys.argv[1]}))' "$1"; }
Jw() { python3 -c 'import json,sys; print(json.dumps({"file_path":sys.argv[1],"content":"x"}))' "$1"; }
Je() { python3 -c 'import json,sys; print(json.dumps({"file_path":sys.argv[1],"old_string":"NOPE","new_string":"Y"}))' "$1"; }
# age <seconds> <file...>: back-date a file, so it plainly was not written by the command under test
age() { local s="$1"; shift; python3 -c 'import os,sys,time; t=time.time()-int(sys.argv[1]); [os.utime(f,(t,t)) for f in sys.argv[2:]]' "$s" "$@"; }
# runreal <session> <prompt> <command> [dur]: really run the command in $PROJ (it must end non-zero), then fire the failure event
runreal() { ( cd "$PROJ" && bash -c "$3" ) >/dev/null 2>&1; RUNRC=$?; FIRE_CWD="$PROJ" fire PostToolUseFailure "$1" "$2" Bash "$(Jb "$3")" "${4-500}"; }

# D-B06, the real command's shape: a heredoc writes a tool, then the last command ends non-zero.
b06() { printf '%s' "mkdir -p $1 && cat > $1/$1.py <<'EOF'
#!/usr/bin/env python3
print('combine')
EOF
chmod +x $1/$1.py
python3 -I $1/$1.py nope.md -o /no/such/dir/out.md && false; false"; }

echo "== ALLOW: a failed command that wrote nothing must not trigger the check =="
runreal n1 p1 "cat > /no/such/dir/tool.py <<'EOF'
print(1)
EOF"
[ "$RUNRC" != 0 ] && [ "$FRC" = 0 ] && [ -z "$FOUT" ] && ok "redirect into a missing folder: exit 0, no output" || bad "n1 rc=$RUNRC frc=$FRC out=$FOUT"
[ ! -s "$T/tw/n1.list" ] && ok "redirect into a missing folder: no row" || bad "n1 recorded: $(cat "$T/tw/n1.list")"
stop n1 p1; [ "$RC" = 0 ] && [ -z "$OUT" ] && ok "redirect into a missing folder: Stop silent" || bad "n1 Stop: $OUT"
runreal n2 p1 "ls -la nope-nope && head -c 600 jobs.md 2>/dev/null"
[ ! -s "$T/tw/n2.list" ] && ok "D-B06's own read-only failed command: no row" || bad "n2 recorded: $(cat "$T/tw/n2.list")"
printf 'print(1)\n' > "$PROJ/old-tool.py"; age 86400 "$PROJ/old-tool.py"
runreal n3 p1 "false && cp /etc/hosts old-tool.py"
[ ! -s "$T/tw/n3.list" ] && ok "named an old file, never reached it: no row" || bad "n3 recorded: $(cat "$T/tw/n3.list")"
printf 'print(2)\n' > "$PROJ/fresh-other.py"; age 30 "$PROJ/fresh-other.py"
runreal n4 p1 "cp /no/such/source fresh-other.py"
[ ! -s "$T/tw/n4.list" ] && ok "named a file made 30 s ago by someone else, wrote nothing to it: no row" || bad "n4 recorded: $(cat "$T/tw/n4.list")"
stop n4 p1; [ -z "$OUT" ] && ok "same: Stop silent" || bad "n4 Stop: $OUT"
fire PostToolUseFailure n5 p1 Write "$(Jw /no-such-root-folder/x.py)" 6
[ "$FRC" = 0 ] && [ ! -s "$T/tw/n5.list" ] && ok "failed Write, no file: no row" || bad "n5 frc=$FRC $(cat "$T/tw/n5.list" 2>/dev/null)"
printf 'print(3)\n' > "$PROJ/old-edit.py"; age 86400 "$PROJ/old-edit.py"
fire PostToolUseFailure n6 p1 Edit "$(Je "$PROJ/old-edit.py")" 6
[ ! -s "$T/tw/n6.list" ] && ok "failed Edit of an old file, unchanged: no row" || bad "n6 recorded: $(cat "$T/tw/n6.list")"
printf 'print(4)\n' > "$PROJ/noduration.py"; age 300 "$PROJ/noduration.py"
runreal n7 p1 "cp /no/such/source noduration.py" ""
[ ! -s "$T/tw/n7.list" ] && ok "payload without duration_ms, file 5 min old: no row" || bad "n7 recorded: $(cat "$T/tw/n7.list")"
printf '{not json' | bash "$HERE/turn_write_recorder.sh" >"$T/j.out" 2>&1; JRC=$?
[ "$JRC" = 0 ] && [ ! -s "$T/j.out" ] && ok "unreadable payload: exit 0, no output" || bad "bad payload rc=$JRC $(cat "$T/j.out")"

echo "== SWITCH OFF = the old behaviour =="
mkdir -p "$PROJ/off"; ( cd "$PROJ/off" && ROUNDB_RECORD_FAILED_WRITES=off FIRE_CWD="$PROJ/off" bash -c "$(b06 offtool)" ) >/dev/null 2>&1
ROUNDB_RECORD_FAILED_WRITES=off FIRE_CWD="$PROJ/off" fire PostToolUseFailure off1 p1 Bash "$(Jb "$(b06 offtool)")" 500
[ -f "$PROJ/off/offtool/offtool.py" ] && ok "OFF: the command really left its file" || bad "off file missing"
[ "$FRC" = 0 ] && [ -z "$FOUT" ] && [ ! -s "$T/tw/off1.list" ] && ok "OFF: failed Bash records nothing, no output" || bad "OFF recorded: $(cat "$T/tw/off1.list" 2>/dev/null) $FOUT"
ROUNDB_RECORD_FAILED_WRITES=off stop off1 p1; [ "$RC" = 0 ] && [ -z "$OUT" ] && ok "OFF: Stop silent, the old miss" || bad "OFF Stop: $OUT"
printf 'x\n' > "$PROJ/off/w.py"
ROUNDB_RECORD_FAILED_WRITES=off fire PostToolUseFailure off2 p1 Write "$(Jw "$PROJ/off/w.py")" 6
[ ! -s "$T/tw/off2.list" ] && ok "OFF: failed Write records nothing" || bad "OFF failed Write recorded"
printf 'x\n' > "$PROJ/off/s.py"
ROUNDB_RECORD_FAILED_WRITES=off fire PostToolUse off3 p1 Write "$(Jw "$PROJ/off/s.py")" ""
grep -qF "$PROJ/off/s.py" "$T/tw/off3.list" 2>/dev/null && ok "OFF: a successful Write is still recorded" || bad "OFF: success not recorded"
fire PostToolUse off4 p1 Write "$(Jw "$PROJ/off/s.py")" ""
grep -q "new" "$T/tw/off4.list" 2>/dev/null && ok "ON: a successful Write records exactly as before" || bad "ON: success changed"

echo "== REGISTERED: the harness has to call it =="
python3 - "$PLUG" > "$T/reg.out" <<'PY'
import json, os, sys
plug = sys.argv[1]
want = "Write|Edit|MultiEdit|NotebookEdit|Bash"
for rel in ("hooks/hooks.json", ".claude/settings.json"):
    doc = json.load(open(os.path.join(plug, rel)))
    groups = doc.get("hooks", doc).get("PostToolUseFailure", [])
    print(rel, "yes" if any(g.get("matcher") == want and any("turn_write_recorder.sh" in h["command"] for h in g["hooks"]) for g in groups) else "no")
PY
grep -q "hooks/hooks.json yes" "$T/reg.out" && ok "hooks/hooks.json has PostToolUseFailure -> the recorder" || bad "not in hooks/hooks.json"
grep -q ".claude/settings.json yes" "$T/reg.out" && ok ".claude/settings.json has PostToolUseFailure -> the recorder" || bad "not in .claude/settings.json"
grep -qE '^record_failed_writes=on$' "$HERE/roundB.conf" && ok "roundB.conf: record_failed_writes=on" || bad "switch missing from roundB.conf"

echo "== D-B06: a tool written by a command that ended non-zero =="
runreal b1 p1 "$(b06 mdcombine)"
[ "$RUNRC" != 0 ] && [ -f "$PROJ/mdcombine/mdcombine.py" ] && ok "the command really wrote the file and really failed (rc $RUNRC)" || bad "shape wrong: rc=$RUNRC"
[ "$FRC" = 0 ] && [ -z "$FOUT" ] && ok "observer: exit 0, no output" || bad "observer spoke: rc=$FRC $FOUT"
grep -qF "p1	new	$PROJ/mdcombine/mdcombine.py" "$T/tw/b1.list" 2>/dev/null && ok "recorded as new, under this prompt" || bad "not recorded: $(cat "$T/tw/b1.list" 2>/dev/null)"
stop b1 p1; R="$(reason)"
printf '%s' "$OUT" | grep -q '"decision": *"block"' && ok "end-of-turn check fires" || bad "end-of-turn stayed silent: $OUT"
printf '%s' "$R" | grep -q "mdcombine.py" && printf '%s' "$R" | grep -q "$PC/" && ok "message names the file and the personal code folder" || bad "message wrong: $R"
printf 'print(5)\n' > "$PROJ/half.py"
fire PostToolUseFailure b2 p1 Write "$(Jw "$PROJ/half.py")" 6
grep -qF "p1	new	$PROJ/half.py" "$T/tw/b2.list" 2>/dev/null && ok "failed Write that left a new file: recorded as new" || bad "b2: $(cat "$T/tw/b2.list" 2>/dev/null)"
printf 'print(6)\n' > "$PROJ/old-then-hit.py"; age 86400 "$PROJ/old-then-hit.py"
runreal b3 p1 "printf 'print(7)\n' > old-then-hit.py; exit 1"
grep -qF "p1	edit	$PROJ/old-then-hit.py" "$T/tw/b3.list" 2>/dev/null && ok "failed Bash that rewrote an old file: edit, like a success" || bad "b3: $(cat "$T/tw/b3.list" 2>/dev/null)"
stop b3 p1; [ -z "$OUT" ] && ok "an edit is not checked at Stop, like a success" || bad "b3 Stop: $OUT"
runreal b4 p1 "printf 'print(8)\n' > noduration-new.py; exit 1" ""
grep -qF "p1	new	$PROJ/noduration-new.py" "$T/tw/b4.list" 2>/dev/null && ok "no duration_ms: the 120 s window still catches a new file" || bad "b4: $(cat "$T/tw/b4.list" 2>/dev/null)"

echo
if [ "$fail" = 0 ]; then echo "RESULT: $pass passed, 0 failed."; exit 0; else echo "RESULT: $pass passed, $fail failed."; exit 1; fi
