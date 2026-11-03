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
( unset ROUNDB_INLINE_KEEP_NUDGE; . "$HERE/lib/roundb.sh"; V="$(sed -n 's/^inline_keep_nudge=//p' "$CONF" | tr -d '[:space:]')"; if roundb_on inline_keep_nudge; then [ "$V" = on ]; else [ "$V" = off ]; fi ) && ok "roundb_on agrees with the conf line" || bad "roundb_on disagrees with the conf line"

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

echo "== real-use false alarm (2026-11-01): a Bash redirect or heredoc that WRITES a file is a file saved =="
HD=$'cd /x/notes && cat > plans/launcher-lanes.plan.md <<\'EOF\'\n# plan\nstep one | step two | step three > done\nEOF'
mk "$T/t8" "write the launcher lanes plan, keep it" "$HD"
stop h1 p1 "$T/t8"; [ -z "$OUT$ERR" ] && ok "cd <notes> && cat > f <<EOF (the real command shape): silent" || bad "heredoc write flagged: $OUT"
mk "$T/t8b" "note it down, keep it" 'echo "remember the milk and the eggs" > /x/notes/todo.md'
stop h2 p1 "$T/t8b"; [ -z "$OUT$ERR" ] && ok "echo > file: silent" || bad "echo redirect flagged: $OUT"
mk "$T/t8c" "note it down, keep it" "printf 'remember the milk and eggs\\n' >> /x/notes/todo.md"
stop h3 p1 "$T/t8c"; [ -z "$OUT$ERR" ] && ok "printf >> file: silent" || bad "printf redirect flagged: $OUT"
LH=$'cat > /x/notes/big.md <<\'EOF\'\n'"$(python3 -c "print('alpha | beta | gamma | delta > epsilon\n' * 40)")"$'EOF'
mk "$T/t8d" "write the big doc" "$LH"
stop h4 p1 "$T/t8d"; [ -z "$OUT$ERR" ] && ok "long heredoc that writes a file: silent (no offer either)" || bad "long heredoc flagged: $OUT"
mk "$T/t8e" "show me the doc" $'cat <<\'EOF\'\n'"$(python3 -c "print('alpha | beta | gamma | delta\n' * 40)")"$'EOF'
stop h5 p1 "$T/t8e"; [ -z "$OUT$ERR" ] && ok "long heredoc BODY is not measured: no offer for a short command" || bad "heredoc body counted: $OUT"
mk "$T/t8f" "which lines" 'echo "a | b | c | d | e | f | g | h | i | j | k | l | m | n | o | p | q | r | s | t | u | v | w | x | y | z | aa | bb | cc"'
stop h6 p1 "$T/t8f"; [ -z "$OUT$ERR" ] && ok "quoted text payload is not measured" || bad "quoted payload counted: $OUT"
mk "$T/t8g" "keep it" "$FIND 2>/dev/null"
stop h7 p1 "$T/t8g"; blocked && ok "2>/dev/null is not a file write: keep-intent still fires" || bad "2>/dev/null treated as a write"
mk "$T/t8h" "keep it" "$FIND | sort -n | head -5 2>&1"
stop h8 p1 "$T/t8h"; blocked && ok "keep-intent + inline pipeline still fires" || bad "pipeline keep missed"

echo "== plan item 15 (2026-11-02): idioms, compaction summaries and rows the person did not type =="
# The real false alarm: Enver typed "keep this on track so just keep it on track" and the hook asked him to save a command.
# PLAIN is >= MIN_CHARS but not reusable, so a wrong keep-read is the ONLY way any of these silent cases can block.
N=0
mk "$T/i1" "keep this on track so just keep it on track" "$PLAIN"
stop i1 p1 "$T/i1"; [ -z "$OUT$ERR" ] && ok "Enver's exact 'keep this on track so just keep it on track': silent" || bad "idiom read as keep: $OUT"
mk "$T/i2" "keep it working" "$PLAIN"
stop i2 p1 "$T/i2"; [ -z "$OUT$ERR" ] && ok "'keep it working': silent" || bad "idiom read as keep: $OUT"
for IDI in "keep it going" "keep it up" "keep it short" "keep it simple" "ok keep it on track, then count the lines"; do
  mk "$T/i3" "$IDI" "$PLAIN"; N=$((N+1)); stop "i3n$N" p1 "$T/i3"; [ -z "$OUT$ERR" ] && ok "idiom '$IDI': silent" || bad "idiom '$IDI' read as keep: $OUT"
done
# rows <file> <spec>... : one transcript from row specs. h:<text> human-typed (real origin shape), n:<text> task notification
# (real shape: origin.kind task-notification, NO isMeta), c:<text> compaction summary (isCompactSummary + isVisibleInTranscriptOnly),
# v:<text> isVisibleInTranscriptOnly only, o:<kind>:<text> any other origin kind without isMeta, b:<cmd> a Bash run + its result.
rows() { python3 - "$@" <<'PY'
import json, sys
L = []
for s in sys.argv[2:]:
    k, _, t = s.partition(":")
    u = {"type": "user", "message": {"role": "user", "content": t}}
    if k == "h": u["origin"] = {"kind": "human"}; L.append(u)
    elif k == "n": u["origin"] = {"kind": "task-notification"}; u["message"]["content"] = "<task-notification>\n<status>completed</status>\n<result>" + t + "</result>\n</task-notification>"; L.append(u)
    elif k == "c": u["isCompactSummary"] = True; u["isVisibleInTranscriptOnly"] = True; L.append(u)
    elif k == "v": u["isVisibleInTranscriptOnly"] = True; L.append(u)
    elif k == "o": kind, _, t2 = t.partition(":"); u["origin"] = {"kind": kind}; u["message"]["content"] = t2; L.append(u)
    elif k == "b":
        L.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "b1", "name": "Bash", "input": {"command": t}}]}})
        L.append({"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "b1", "content": "12 lines"}]}})
    L.append({"type": "assistant", "message": {"content": [{"type": "text", "text": "ok"}]}})
open(sys.argv[1], "w").write("\n".join(json.dumps(x) for x in L) + "\n")
PY
}
rows "$T/i4" "h:how many lines in each file under Recipes?" "b:$PLAIN" "n:Agent finished. The person said keep it, so keep it."
stop i4 p1 "$T/i4"; [ -z "$OUT$ERR" ] && ok "task-notification row containing 'keep it': silent" || bad "task notification read as the person: $OUT"
rows "$T/i5" "c:This session is being continued. Summary: the person said keep it about the count command." "h:how many lines in each file under Recipes?" "b:$PLAIN"
stop i5 p1 "$T/i5"; [ -z "$OUT$ERR" ] && ok "compaction-summary row containing 'keep it': silent" || bad "compaction summary read as the person: $OUT"
rows "$T/i5b" "v:earlier the person said keep it" "h:how many lines in each file under Recipes?" "b:$PLAIN"
stop i5b p1 "$T/i5b"; [ -z "$OUT$ERR" ] && ok "isVisibleInTranscriptOnly row containing 'keep it': silent" || bad "transcript-only row read as the person: $OUT"
rows "$T/i5c" "h:how many lines in each file under Recipes?" "b:$PLAIN" "o:some-future-kind:keep it"
stop i5c p1 "$T/i5c"; [ -z "$OUT$ERR" ] && ok "any non-human origin kind without isMeta: silent" || bad "non-human origin read as the person: $OUT"
# still fires
mk "$T/i6" "how many lines of text are in each file under my Recipes folder? quick answer. oh nice, keep it" "$FIND"
stop i6 p1 "$T/i6"; printf '%s' "$(reason)" | grep -q "asked to keep" && ok "D-B04 exact prompt: still 'keep'" || bad "D-B04 lost: $OUT"
rows "$T/i7" "h:how many lines of text are in each file under my Recipes folder? quick answer" "b:$FIND" "h:keep it"
stop i7 p1 "$T/i7"; printf '%s' "$(reason)" | grep -q "asked to keep" && ok "D-B03 (prompt, inline run, then 'keep it'; real human origin): still 'keep'" || bad "D-B03 lost: $OUT"
rows "$T/i7b" "h:how many lines in each file under Recipes?" "b:$PLAIN" "n:Agent finished." "h:keep it"
stop i7b p1 "$T/i7b"; printf '%s' "$(reason)" | grep -q "asked to keep" && ok "'keep it' after a task notification: still 'keep' (notification skipped, not a barrier)" || bad "keep after notification lost: $OUT"
for KP in "keep it" "save that" "keep it please" "keep it as a script" "keep it for later" "Keep it!" "keep that command" "keep it, and run it again tomorrow"; do
  mk "$T/i8" "$KP" "$PLAIN"; N=$((N+1)); stop "i8n$N" p1 "$T/i8"; printf '%s' "$(reason)" | grep -q "asked to keep" && ok "'$KP': still 'keep'" || bad "'$KP' lost: $OUT"
done

echo "== fix 15b (2026-11-02): a capitalised next word starts a new sentence, so the keep phrase has ended =="
# The rig sends D-B04 as ONE -p prompt with BUILD_SUFFIX glued on with no punctuation: "...oh nice, keep it Do not edit ...".
RIGSUF=" Do not edit jobs.md, and do not push or send anything real. If a tool call is denied or blocked, read the message and do what it says, then continue."
grep -qF '" Do not edit jobs.md, and do not push or send anything real."' "$HERE/../tools/rig/rig_live_free.py" && grep -qF '" If a tool call is denied or blocked, read the message and do what it says, then continue."' "$HERE/../tools/rig/rig_live_free.py" && ok "RIGSUF matches rig_live_free.py BUILD_SUFFIX" || bad "RIGSUF drifted from rig_live_free.py BUILD_SUFFIX"
mk "$T/j1" "how many lines of text are in each file under my Recipes folder? quick answer. oh nice, keep it$RIGSUF" "$FIND"
stop j1 p1 "$T/j1"; printf '%s' "$(reason)" | grep -q "asked to keep" && ok "D-B04 exact prompt + rig suffix: 'keep'" || bad "D-B04 + rig suffix lost: $OUT"
for KP in "keep it I'll reuse it" "keep it i'll reuse it" "keep it Please" "keep it I might need it again"; do
  mk "$T/j2" "$KP" "$PLAIN"; N=$((N+1)); stop "j2n$N" p1 "$T/j2"; printf '%s' "$(reason)" | grep -q "asked to keep" && ok "'$KP': 'keep'" || bad "'$KP' lost: $OUT"
done
for IDI in "keep this on track so just keep it on track" "keep it working" "keep it going" "Keep it On track" "keep it short" "keep it brief" "Keep it Short" "Keep it Working"; do
  mk "$T/j3" "$IDI" "$PLAIN"; N=$((N+1)); stop "j3n$N" p1 "$T/j3"; [ -z "$OUT$ERR" ] && ok "idiom '$IDI': silent" || bad "idiom '$IDI' read as keep: $OUT"
done

echo "== plan fix 23(c) (2026-11-02): 'I'll use it to/for ...' about something else is not keep-intent =="
for IDI in "I'll use it to keep it on track" "I'll use it to count my recipes" "I'll use it for the report" "I'll use it in the report" "I'll use it To keep it on track" "I'll use that file" "I'll use this instead of the old one"; do
  mk "$T/u1" "$IDI" "$PLAIN"; N=$((N+1)); stop "u1n$N" p1 "$T/u1"; [ -z "$OUT$ERR" ] && ok "'$IDI': silent" || bad "'$IDI' read as keep: $OUT"
done
for KP in "I'll use it" "I'll use it." "I'll use it again" "I'll use it later" "i'll use it again next week" "I'll use it for later" "I'll use it as a script" "I'll use that one again" "I'll use this command" "I'll use it, thanks" "I'll reuse it to count my recipes"; do
  mk "$T/u2" "$KP" "$PLAIN"; N=$((N+1)); stop "u2n$N" p1 "$T/u2"; printf '%s' "$(reason)" | grep -q "asked to keep" && ok "'$KP': still 'keep'" || bad "'$KP' lost: $OUT"
done

echo "== curly apostrophes (phones and Mac smart punctuation) read the same as straight ones =="
mk "$T/c1" "I’ll use it" "$PLAIN"; stop c1 p1 "$T/c1"; printf '%s' "$(reason)" | grep -q "asked to keep" && ok "curly 'I’ll use it': 'keep'" || bad "curly I'll use it lost: $OUT"
mk "$T/c2" "don’t keep it" "$PLAIN"; stop c2 p1 "$T/c2"; [ -z "$OUT$ERR" ] && ok "curly 'don’t keep it': silent" || bad "curly negation missed: $OUT"

echo "== switch OFF = silent =="
mk "$T/t7" "keep it" "$FIND"
ROUNDB_INLINE_KEEP_NUDGE=off stop f1 p1 "$T/t7"; [ "$RC" = 0 ] && [ -z "$OUT$ERR" ] && ok "switch off: keep-intent case silent" || bad "acted while OFF: $OUT"
ROUNDB_INLINE_KEEP_NUDGE=off stop f2 p1 "$T/t6"; [ -z "$OUT$ERR" ] && ok "switch off: long-command case silent" || bad "offered while OFF"
[ ! -e "$T/tw/f1.inlinekeep" ] && ok "switch off: no state written" || bad "state written while OFF"

echo "== no personal code folder = silent =="
rm -f "$HOME/.config/lifehack/personal-code"
stop g1 p1 "$T/t7"; [ -z "$OUT$ERR" ] && ok "no folder resolves: silent, no guess" || bad "blocked with no folder: $OUT"

echo; echo "passed=$pass failed=$fail"; [ "$fail" = 0 ]
