#!/bin/bash
# test_spec_write_chain.sh -- brief 2f §6 test 5: THE CHAIN, with LIFEHACK_MODEL_STUB (no real model call).
# The writer (lib/spec_write.sh, small tier) writes the done-marker with the EXACT counts and only then chains the
# questioner (lib/spec_questions.sh, medium tier), which writes the questions file; the gate (sb_spec.py gate) reads
# both. A failed writer leaves no new marker, and the stale marker is removed at the next launch (end_of_turn_checks.sh).
# Run: bash system/hooks/tests/test_spec_write_chain.sh
PLUG="${SPEC_PLUG:-$(cd "$(dirname "$0")/../../.." && pwd -P)}"
T="$(cd "$(mktemp -d)" && pwd -P)"; trap '[ -n "${KEEP:-}" ] || rm -rf "$T"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); printf '   ok   %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL  %s\n' "$1"; }
chk() { if eval "$2"; then ok "$1"; else bad "$1  <<$2>>"; fi; }

HM="$T/home"; mkdir -p "$HM/.claude/run/observe" "$HM/brain/drafts/builds/demo-skill"
export HOME="$HM" LIFEHACK_ROOT="$HM/brain" SPEC_WAIT=0
OD="$HM/.claude/run/observe"; SID="chain-sess-1"; WD="$HM/brain/drafts/builds/demo-skill"
H="$PLUG/system/hooks"
export CLAUDE_CODE_SESSION_ID="$SID"

cat > "$T/stub.sh" <<'EOF'
#!/bin/bash
echo "$1" >> "$STUB_LOG"
[ "${STUB_FAIL:-0}" = 1 ] && exit 1
# the stub branches on TIER (ids passed in env): the writer's small call gets the writer reply, the questioner's medium call gets questions
if [ "$1" = "$STUB_SMALL_ID" ]; then
  cat "$STUB_REPLY" > "$3"
else
  printf '1. what does the skill read first?\nQUESTIONS-END\n' > "$3"
fi
EOF
export LIFEHACK_MODEL_STUB="$T/stub.sh" STUB_LOG="$HM/stub.log"
export STUB_SMALL_ID="$(bash -c ". \"$PLUG/system/tools/model.lib.sh\"; model_id_for_tier small")"
cat > "$T/reply.txt" <<'EOF'
SAID: the person said a receipt sorter
---
END-WRITE
EOF
export STUB_REPLY="$T/reply.txt"

# a live run (stage_runner) so `active` passes, and the spec shell
python3 "$PLUG/system/parts/stage_runner.py" start --card "$PLUG/.claude/skills/skill-builder/card.json" --workdir "$WD" >/dev/null 2>&1
printf 'wd=%s\n' "$WD" > "$OD/spec-sess-$SID.flag"
python3 "$PLUG/system/hooks/lib/sb_spec.py" activate2 >/dev/null 2>&1 || true
cp "$PLUG/system/templates/skill-spec-form/skill-spec-form-v2.md" "$WD/draft-spec.md"
python3 - "$WD" <<'PY'
import sys
p = sys.argv[1] + "/draft-spec.md"
t = open(p).read()
open(p, "w").write("> Saved by code's gated writer.\n\n" + t)
PY

echo "== the chain =="
printf '%s\n' '{"session_id":"'"$SID"'","prompt_id":"p1","last_assistant_message":"ok","cwd":"/x","transcript_path":"'$T'/t.jsonl"}' > "$T/stop.json"
: > "$T/t.jsonl"
rm -f "$HM/stub.log"
HOME="$HM" CLAUDE_CODE_SESSION_ID="$SID" bash "$H/lib/spec_write.sh" "$T/stop.json" "$SID"
chk "[C1] the writer wrote the done-marker with the EXACT counts (1 packet line, 0 spec lines)" '[ "$(cat "$OD/spec-saved-$SID.txt")" = "saved 0 spec lines · 1 packet lines" ]'
chk "[C2] the marker exists => the questioner was already launched (its pid file)" '[ -f "$OD/spec-questions-'$SID'.pid" ] || [ -f "$OD/spec-questions-'$SID'.txt" ]'
i=0; while [ ! -s "$OD/spec-questions-$SID.txt" ] && [ $i -lt 50 ]; do sleep 0.2; i=$((i+1)); done
chk "[C3] the questioner ran at the MEDIUM tier, after the writer's small call" '[ "$(wc -l < "$HM/stub.log" | tr -d " ")" -ge 2 ] && [ "$(sed -n 1p "$HM/stub.log")" = "$(bash -c ". \"$PLUG/system/tools/model.lib.sh\"; model_id_for_tier small")" ] && [ "$(sed -n 2p "$HM/stub.log")" = "$(bash -c ". \"$PLUG/system/tools/model.lib.sh\"; model_id_for_tier medium")" ]'
chk "[C4] the questions file holds the questioner's reply" 'grep -q "what does the skill read first" "$OD/spec-questions-'$SID'.txt"'
# the gate reads the pair
OUT="$(HOME="$HM" python3 "$H/lib/sb_spec.py" gate "$SID")"
chk "[C5] gate: SAVED + QUESTIONS (from code) with the questions TEXT in the line (2g B1)" 'printf "%s" "$OUT" | grep -q "GATE: SAVED — saved 0 spec lines · 1 packet lines." && printf "%s" "$OUT" | grep -q "QUESTIONS (from code)" && printf "%s" "$OUT" | grep -q "what does the skill read first"'
chk "[C6] gate consumed: the second read shows neither line" '[ "$(HOME="$HM" python3 "$H/lib/sb_spec.py" gate "$SID" | head -1)" = "-" ]'

echo "== the writer's failure =="
rm -f "$OD/spec-saved-$SID.txt" "$OD/spec-saved-$SID.txt.shown" "$OD/spec-questions-$SID.txt" "$OD/spec-questions-$SID.txt.shown"
export STUB_FAIL=1
HOME="$HM" CLAUDE_CODE_SESSION_ID="$SID" bash "$H/lib/spec_write.sh" "$T/stop.json" "$SID"; unset STUB_FAIL
chk "[C7] a writer failure writes the fail line and a FAILED gate marker (2g), and starts NO questioner" '[ -s "$OD/spec-fail-'$SID'.txt" ] && grep -q "^FAILED: could not save" "$OD/spec-saved-'$SID'.txt" && [ ! -e "$OD/spec-questions-'$SID'.pid" ]'

echo "== the stale marker is removed at the next launch (end_of_turn_checks.sh) =="
printf 'stale counts\n' > "$OD/spec-saved-$SID.txt"
python3 - "$T" "$SID" <<'PY' > "$T/stop2.json"
import json, sys
json.dump({"session_id": sys.argv[2], "prompt_id": "p2", "hook_event_name": "Stop", "stop_hook_active": False,
           "last_assistant_message": "ok", "cwd": "/x", "transcript_path": sys.argv[1] + "/t.jsonl"}, sys.stdout)
PY
HOME="$HM" bash "$H/end_of_turn_checks.sh" < "$T/stop2.json" >/dev/null 2>&1
chk "[C8] a new launch removed the stale done-marker before the writer ran" '[ ! -f "$OD/spec-saved-'$SID'.txt" ] || ! grep -q stale "$OD/spec-saved-'$SID'.txt"'
i=0; while [ -f "$OD/spec-write-$SID.pid" ] && kill -0 "$(cat "$OD/spec-write-$SID.pid" 2>/dev/null)" 2>/dev/null && [ $i -lt 50 ]; do sleep 0.2; i=$((i+1)); done
chk "[C9] the relaunched writer produced a fresh marker" '[ -s "$OD/spec-saved-'$SID'.txt" ] && grep -qE "saved [0-9]+ spec lines · [0-9]+ packet lines|nothing to save" "$OD/spec-saved-'$SID'.txt"'

echo "== 2g: B2 no write into the cwd, B4 a failure is loud and keeps the offset, S2 a stale questioner is harmless =="
CW="$T/cwd"; rm -rf "$CW"; mkdir -p "$CW"
rm -f "$OD/spec-saved-$SID.txt" "$OD/spec-saved-$SID.txt.shown" "$OD/spec-fail-$SID.txt"
rm -f "$OD/spec-sess-$SID.flag"    # the run flag has vanished (the audit's B2 case): no run folder to write into
( cd "$CW" && HOME="$HM" bash "$H/lib/spec_write.sh" "$T/stop.json" "$SID" "" )
chk "[C10] B2: an empty run folder writes NOTHING into the cwd, and leaves a FAILED gate marker" '[ -z "$(ls -A "$CW")" ] && grep -q "^FAILED: could not save: no run folder" "$OD/spec-saved-'$SID'.txt"'
printf 'wd=%s\n' "$WD" > "$OD/spec-sess-$SID.flag"
rm -f "$OD/spec-saved-$SID.txt" "$OD/spec-offset-$SID" "$OD/spec-questions-$SID.pid"
printf 'REPLACE: A line that exists nowhere in this spec\nNEW: nope\nEVIDENCE: nope\n---\nEND-WRITE\n' > "$T/reply-rej.txt"
STUB_REPLY="$T/reply-rej.txt" HOME="$HM" bash "$H/lib/spec_write.sh" "$T/stop.json" "$SID" "$WD"
chk "[C11] B4: rejected-only writes FAILED (not 'nothing to save'), the offset does not advance, no questioner starts" 'grep -q "^FAILED: could not save: .*rejected" "$OD/spec-saved-'$SID'.txt" && [ ! -e "$OD/spec-offset-'$SID'" ] && [ ! -e "$OD/spec-questions-'$SID'.pid" ]'
chk "[C11b] B4: the FAILED marker shows loudly on screen and the model line tells the model" 'GOUT="$(HOME="$HM" python3 "$H/lib/sb_spec.py" gate "$SID")"; printf "%s" "$GOUT" | grep -q "COULD NOT SAVE" && printf "%s" "$GOUT" | sed -n 2p | grep -q "COULD NOT SAVE"'
rm -f "$OD/spec-questions-$SID.txt" "$OD/spec-questions-$SID.txt.shown"
echo 99999999 > "$OD/spec-questions-$SID.pid"    # the pid file now belongs to a newer questioner
HOME="$HM" SPEC_Q_PIDWAIT=0 bash "$H/lib/spec_questions.sh" "$SID"
chk "[C12] S2: a stale questioner writes no questions and leaves the newer pid file alone" '[ ! -e "$OD/spec-questions-'$SID'.txt" ] && [ "$(cat "$OD/spec-questions-'$SID'.pid")" = "99999999" ]'
rm -f "$OD/spec-questions-$SID.pid"
rm -f "$OD/spec-sess-$SID.flag"

echo "passed=$pass failed=$fail"
REAL_FAIL=$fail
if [ -n "${SPEC_PLUG:-}" ]; then echo "passed=$pass failed=$fail"; [ "$REAL_FAIL" = 0 ]; exit; fi  # a broken copy never recurses
echo "== BROKEN COPIES: each check must FAIL on a copy with one edit =="
broken() {  # broken <name> <file-under-test> <old> <new> <check-that-must-fail>
  local C="$T/copy"; rm -rf "$C"; mkdir -p "$C"
  cp -R "$PLUG/system" "$C/system"
  mkdir -p "$C/.claude/skills"
  cp -R "$PLUG/.claude/skills/skill-builder" "$C/.claude/skills/skill-builder"
  python3 - "$C/$2" "$3" "$4" <<'PYB'
import sys
p, old, new = sys.argv[1:4]
t = open(p).read()
assert t.count(old) == 1, (p, t.count(old))
open(p, "w").write(t.replace(old, new))
PYB
  local OUT; OUT="$(SPEC_PLUG="$C" timeout 300 bash "$0" 2>&1 | tail -1)"
  if printf '%s' "$OUT" | grep -q "failed=0"; then bad "[broken $1] $5 did NOT fail on the broken copy"; else ok "[broken $1] the copy fails $5"; fi
}
broken marker-counts system/hooks/lib/spec_write.sh 'printf '"'"'saved %s spec lines · %s packet lines%s\n'"'"' "$SPN" "$PKT" "$REJNOTE"' 'printf '"'"'saved 99 spec lines · 99 packet lines%s\n'"'"' "$SPN" "$PKT" "$REJNOTE"' C1
broken no-chain system/hooks/lib/spec_write.sh 'nohup bash "$_SELF_DIR/spec_questions.sh" "$SID" </dev/null >/dev/null 2>&1 &' ':' C2
broken gate-questions system/hooks/lib/sb_spec.py 'QUESTIONS (from code): show these' 'QUESTIONS: show these' C5
echo "passed=$pass failed=$fail"
[ "$REAL_FAIL" = 0 ]
