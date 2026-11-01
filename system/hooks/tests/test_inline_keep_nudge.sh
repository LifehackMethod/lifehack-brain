#!/bin/bash
# Matrix for switch inline_keep_nudge: system/hooks/end_of_turn_checks.sh + system/hooks/lib/inline_keep.py.
# Exam D-B03/D-B04 (2026-11-01): "keep it" said about a command run INLINE, no file written. Fired through the REAL Stop entry
# script with a synthetic transcript (fictional names only), under a temp HOME. CONF=<file> checks another conf (pre-landing).
HERE="$(cd "$(dirname "$0")/.." && pwd)"; EOT="$HERE/end_of_turn_checks.sh"; REC="$HERE/turn_write_recorder.sh"
T="$(cd "$(mktemp -d)" && pwd -P)"; trap 'rm -rf "$T"' EXIT
export HOME="$T/hm"; PC="$T/hm/my-code"; export LHB_TURN_WRITES_DIR="$T/tw"
mkdir -p "$HOME/.config/lifehack" "$PC" "$T/tw"; echo "$PC" > "$HOME/.config/lifehack/personal-code"
pass=0; fail=0
ok()  { pass=$((pass+1)); printf '   ok   %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL  %s\n' "$1"; }
CONF="${CONF:-$HERE/roundB.conf}"
# mk <file> <user-text> <bash-command|-> [prev-user-text] [injected-text] : a transcript of one turn (optionally a turn before)
mk() { python3 - "$@" <<'PY'
import json, sys
f, said, cmd = sys.argv[1], sys.argv[2], sys.argv[3]
prev = sys.argv[4] if len(sys.argv) > 4 else ""; inj = sys.argv[5] if len(sys.argv) > 5 else ""
L = []
def user(t, meta=False): L.append({"type": "user", "isMeta": meta, "message": {"role": "user", "content": t}})
if prev: user(prev); L.append({"type": "assistant", "message": {"content": [{"type": "text", "text": "ok"}]}})
if inj: user("<system-reminder>\n" + inj + "\n</system-reminder>", True)
user(said + (("\n<system-reminder>" + inj + "</system-reminder>") if inj else ""))
if cmd != "-":
    L.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": cmd}}]}})
    L.append({"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "keep it 12 lines"}]}})
L.append({"type": "assistant", "message": {"content": [{"type": "text", "text": "Here you go."}]}})
open(f, "w").write("\n".join(json.dumps(x) for x in L) + "\n")
PY
}
# stop <session> <prompt> <transcript>  -> OUT, RC
stop() { python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"prompt_id":sys.argv[2],"transcript_path":sys.argv[3],"hook_event_name":"Stop","stop_hook_active":False}))' "$1" "$2" "$3" | bash "$EOT" >"$T/o" 2>"$T/e"; RC=$?; OUT="$(cat "$T/o")"; ERR="$(cat "$T/e")"; }
blocked() { printf '%s' "$OUT" | grep -q '"decision": *"block"'; }
reason() { printf '%s' "$OUT" | python3 -c 'import json,sys; print(json.load(sys.stdin)["reason"])' 2>/dev/null; }
FIND='find ~/Recipes -type f -exec wc -l {} +'
PLAIN='wc -l ~/Recipes/*.txt'
LONG='cat ~/Recipes/*.txt | tr -s " " "\n" | sort | uniq -c | sort -rn | head -20'
export ROUNDB_INLINE_KEEP_NUDGE=on ROUNDB_BACK_DOOR=off ROUNDB_OWN_LIST=off ROUNDB_OWN_LIST_UNHOMED=off

echo "== the switch is a real line =="
[ "$(grep -cE '^inline_keep_nudge=(on|off)[[:space:]]*$' "$CONF")" = 1 ] && ok "roundB.conf has exactly one real inline_keep_nudge=on|off line" || bad "no real switch line in $CONF"
grep -qE '^inline_keep_nudge=off[[:space:]]*$' "$CONF" && ok "default is OFF" || bad "default is not off"
( unset ROUNDB_INLINE_KEEP_NUDGE; . "$HERE/lib/roundb.sh"; roundb_on inline_keep_nudge ) && bad "on with no env, conf default" || ok "roundb_on reads it as off by default"

echo "== BLOCK once =="
mk "$T/t1" "how many lines of text are in each file under my Recipes folder? quick answer. oh nice, keep it" "$FIND"
stop k1 p1 "$T/t1"; R="$(reason)"
[ "$RC" = 0 ] && blocked && ok "keep-intent + inline + no file: block, exit 0" || bad "no block: $OUT $ERR"
printf '%s' "$R" | grep -qF "$PC/tools/" && printf '%s' "$R" | grep -q "own_list_add.py" && printf '%s' "$R" | grep -q "restate the path and the list entry" && ok "message: personal folder from the pointer, own-list command, restate" || bad "message wrong: $R"
printf '%s' "$R" | grep -qF "wc -l" && ok "message carries the command" || bad "command missing"
stop k1 p1 "$T/t1"; [ -z "$OUT" ] && ok "same turn again: silent (blocks once)" || bad "blocked twice"
stop k1 p2 "$T/t1"; [ -z "$OUT" ] && ok "same command next turn: not asked again" || bad "asked again for same command"
mk "$T/t1b" "run the same count" "$FIND" "save that for later"
stop k1b p9 "$T/t1b"; blocked && ok "keep-intent in the turn just before counts" || bad "previous-turn intent missed: $OUT"
mk "$T/t1c" "keep it" "-" "count lines in my Recipes files"
python3 - "$T/t1c" <<'PY'
import json, sys
L = [json.loads(x) for x in open(sys.argv[1])]
a = {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t0", "name": "Bash", "input": {"command": "find ~/Docs -name '*.md' | xargs wc -w"}}]}}
L.insert(2, a); open(sys.argv[1], "w").write("\n".join(json.dumps(x) for x in L) + "\n")
PY
stop k1c p1 "$T/t1c"; blocked && ok "'keep it' said after the command ran (prior turn) still blocks" || bad "late keep missed: $OUT"

echo "== NO block =="
mk "$T/t2" "how many lines in each file under Recipes? keep it" "$FIND"
printf 'p3\tnew\t%s/tools/count.sh\n' "$PC" > "$T/tw/k2.list"
stop k2 p3 "$T/t2"; [ -z "$OUT$ERR" ] && ok "keep-intent + inline + file saved (recorder row): silent" || bad "blocked with a file saved: $OUT"
mk "$T/t2b" "keep it" "$FIND"
python3 - "$T/t2b" <<'PY'
import json, sys
L = [json.loads(x) for x in open(sys.argv[1])]
L.insert(2, {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "w", "name": "Write", "input": {"file_path": "/x/count.sh", "content": "x"}}]}})
open(sys.argv[1], "w").write("\n".join(json.dumps(x) for x in L) + "\n")
PY
stop k2b p1 "$T/t2b"; [ -z "$OUT$ERR" ] && ok "a Write in the turn counts as saved: silent" || bad "blocked after Write: $OUT"
mk "$T/t3" "how many lines in each file under Recipes?" "$PLAIN"
stop k3 p1 "$T/t3"; [ -z "$OUT$ERR" ] && ok "no keep-intent, short-ish command: silent" || bad "blocked without intent: $OUT"
mk "$T/t3b" "keep it" "-"
stop k3b p1 "$T/t3b"; [ -z "$OUT$ERR" ] && ok "keep-intent but no inline command: silent" || bad "blocked without a command: $OUT"
mk "$T/t3c" "please don't keep it, just tell me" "$PLAIN"
stop k3c p1 "$T/t3c"; [ -z "$OUT$ERR" ] && ok "negated ('don't keep it'): silent" || bad "negation missed: $OUT"
mk "$T/t3d" "ls" "ls"
stop k3d p1 "$T/t3d"; [ -z "$OUT$ERR" ] && ok "trivial command: silent" || bad "trivial blocked"
mk "$T/t4" "how many lines in each file under Recipes?" "$PLAIN" "" "standing brief: always keep it short; save that for the end; keep it tidy"
stop k4 p1 "$T/t4"; [ -z "$OUT$ERR" ] && ok "injected context containing 'keep it'/'save that': no false trigger" || bad "injected context triggered: $OUT"
mk "$T/t4b" "how many lines in each file under Recipes?" "$PLAIN" "" "keep it"
python3 - "$T/t4b" <<'PY'
import json, sys
L = [json.loads(x) for x in open(sys.argv[1])]
L.insert(1, {"type": "user", "isMeta": True, "message": {"role": "user", "content": "keep it, save that, I'll reuse this"}})
open(sys.argv[1], "w").write("\n".join(json.dumps(x) for x in L) + "\n")
PY
stop k4b p1 "$T/t4b"; [ -z "$OUT$ERR" ] && ok "isMeta entry and a system-reminder span in the person's own message: ignored" || bad "meta triggered: $OUT"
stop k5 p1 "$T/nonexistent"; [ "$RC" = 0 ] && [ -z "$OUT" ] && ok "unreadable transcript: silent" || bad "unreadable transcript not silent"

echo "== long reusable command: at most ONE offer per session =="
mk "$T/t6" "which words show up most in my Recipes?" "$LONG"
stop o1 p1 "$T/t6"; R="$(reason)"
[ "$RC" = 0 ] && blocked && printf '%s' "$R" | grep -q "offer in ONE line" && ok "long pipeline, no keep-intent: one offer" || bad "no offer: $OUT $ERR"
mk "$T/t6b" "and the most common words in my Notes?" "$(printf '%s' "$LONG" | sed 's/Recipes/Notes/')"
stop o1 p2 "$T/t6b"; [ -z "$OUT$ERR" ] && ok "second long command, same session: no second offer" || bad "offered twice in a session"
stop o1 p3 "$T/t6b"; [ -z "$OUT$ERR" ] && ok "third turn: still none" || bad "offered on third turn"
stop o2 p1 "$T/t6b"; blocked && ok "a different session gets its own one offer" || bad "other session not offered"
mk "$T/t6c" "the loop" 'for f in ~/Recipes/*.txt; do wc -l "$f"; done'
stop o3 p1 "$T/t6c"; blocked && ok "a for-loop counts as reusable" || bad "loop not reusable"
mk "$T/t6d" "count" 'echo "hello there general kenobi" | wc -w'
stop o4 p1 "$T/t6d"; [ -z "$OUT$ERR" ] && ok "single short pipe: not offered" || bad "short pipe offered"
mk "$T/t6e" "keep it" "$LONG"
stop o5 p1 "$T/t6e"; printf '%s' "$(reason)" | grep -q "asked to keep" && ok "keep-intent wins over offer wording (block, not offer)" || bad "wrong wording"
stop o5 p2 "$T/t6e"; [ -z "$OUT" ] && ok "after a keep-block the same command is not offered either" || bad "offer after keep"

echo "== switch OFF = silent =="
mk "$T/t7" "keep it" "$FIND"
ROUNDB_INLINE_KEEP_NUDGE=off stop f1 p1 "$T/t7"; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "switch off: keep-intent case silent" || bad "acted while OFF: $OUT"
ROUNDB_INLINE_KEEP_NUDGE=off stop f2 p1 "$T/t6"; [ -z "$OUT$ERR" ] && ok "switch off: long-command case silent" || bad "offered while OFF"
[ ! -e "$T/tw/f1.inlinekeep" ] && ok "switch off: no state written" || bad "state written while OFF"

echo "== no personal code folder = silent =="
rm -f "$HOME/.config/lifehack/personal-code"
stop g1 p1 "$T/t7"; [ -z "$OUT$ERR" ] && ok "no folder resolves: silent, no guess" || bad "blocked with no folder: $OUT"

echo; echo "passed=$pass failed=$fail"; [ "$fail" = 0 ]
