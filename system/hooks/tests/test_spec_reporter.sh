#!/bin/bash
# test_spec_reporter.sh -- round 2b-Y: the spec REPORTER (B2), the spec WRITER (B3) and the BARS from code (B4);
# 2c (2026-11-25): the background writer is SWITCHED OFF (Stop starts no spec_write), the B2 line checks decision
# words (DECISION_RE) and warns when the person decided and the spec did not change; the writer cases below still
# exercise lib/spec_write.sh directly (the file is kept, not wired).
# Files under test: system/hooks/lib/sb_spec.py, lib/spec_write.sh, lib/sb_start.py (activate + per-turn bars), observe_ups.sh
# (the merged systemMessage), end_of_turn_checks.sh (the Stop launch + bar check), scripts/completion.py (counts).
# No real model call: LIFEHACK_MODEL_STUB. NO-RUN / UNARMED cases first. After the real tree passes, each check is shown
# FAILING on a deliberately broken copy (a copy of the plugin pieces with ONE edit).
# Run: bash system/hooks/tests/test_spec_reporter.sh   (SPEC_PLUG=<plugin root> points it at a copy)
PLUG="${SPEC_PLUG:-$(cd "$(dirname "$0")/../../.." && pwd -P)}"
T="$(cd "$(mktemp -d)" && pwd -P)"; trap '[ -n "$KEEP" ] || rm -rf "$T"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); printf '   ok   %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL  %s\n' "$1"; }
chk() { if eval "$2"; then ok "$1"; else bad "$1  <<$2>>"; fi; }

cat > "$T/stub.sh" <<'EOF'
#!/bin/bash
sleep "${STUB_SLEEP:-0}"
echo "$1" >> "$STUB_LOG"
cp "$2" "$STUB_PROMPT_COPY" 2>/dev/null
[ "${STUB_FAIL:-0}" = 1 ] && exit 1
if [ -n "${STUB_REPLY_FILE:-}" ]; then cat "$STUB_REPLY_FILE" > "$3"; else echo NOTHING > "$3"; fi
if [ "${STUB_NO_MARKER:-0}" = 1 ]; then :; elif [ "${STUB_INLINE:-0}" = 1 ]; then printf 'END-WRITE' >> "$3"; else echo END-WRITE >> "$3"; fi
EOF

ms_of() { python3 - "$@" <<'PY'
import subprocess, sys, time
payload, args = sys.argv[1], sys.argv[2:]
t = time.perf_counter()
r = subprocess.run(["bash"] + args, input=open(payload, "rb").read(), capture_output=True)
print(round((time.perf_counter() - t) * 1000), r.returncode, len(r.stdout) + len(r.stderr))
PY
}

suite() {   # suite <plugin-root-under-test>
  local R="$1" HM; HM="$(mktemp -d "$T/hm.XXXXXX")"
  export HOME="$HM" LIFEHACK_ROOT="$HM/brain"; mkdir -p "$HM/brain" "$HM/elsewhere"
  unset CLAUDE_CODE_SESSION_ID
  local H="$R/system/hooks" EOT UPS MOVER SC
  EOT="$H/end_of_turn_checks.sh"; UPS="$H/observe_ups.sh"; MOVER="$H/run_step_hook.sh"; SC="$R/.claude/skills/skill-builder/scripts"
  export LIFEHACK_MODEL_STUB="$T/stub.sh" STUB_LOG="$HM/stub.log" STUB_PROMPT_COPY="$HM/prompt.seen" SPEC_WAIT=0
  unset STUB_FAIL STUB_REPLY_FILE STUB_SLEEP
  local OD="$HM/.claude/run/observe" SID="sess-spec-0001" S0="sess-spec-none"
  jq_() { python3 -c "import json,sys; d=json.load(sys.stdin); print(eval(sys.argv[1]))" "$1"; }
  upsj() { python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"prompt_id":"p"+sys.argv[3],"cwd":sys.argv[4],"hook_event_name":"UserPromptSubmit","prompt":sys.argv[2],"transcript_path":"/x"}))' "$1" "$2" "${3:-1}" "${4:-/x}"; }
  ups() { upsj "$1" "$2" "$3" "$4" | bash "$UPS" 2>/dev/null; }
  mover() { upsj "$1" "$2" "$3" "$HM/elsewhere" | sh "$MOVER" 2>&1; }
  stopj() { python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"prompt_id":"p1","hook_event_name":"Stop","stop_hook_active":False,"last_assistant_message":sys.argv[2],"cwd":"/x","transcript_path":sys.argv[3]}))' "$1" "$2" "$3"; }
  waitdone() { local i=0; while [ -f "$OD/spec-write-$1.pid" ] && kill -0 "$(cat "$OD/spec-write-$1.pid" 2>/dev/null)" 2>/dev/null && [ $i -lt 100 ]; do sleep 0.2; i=$((i+1)); done; sleep 0.3; }
  tline() { python3 -c 'import json,sys; print(json.dumps({"type":sys.argv[1],"message":{"role":sys.argv[1],"content":json.loads(sys.argv[2])}}))' "$1" "$2"; }

  echo "== NO RUN =="
  OUT="$(ups "$S0" "hello there" 1)"
  chk "[N1] no run: a plain prompt prints nothing" '[ -z "$OUT" ]'
  stopj "$S0" "done" "$HM/none.jsonl" > "$HM/stop0.json"
  read MS RC LEN < <(ms_of "$HM/stop0.json" "$EOT")
  for _i in 1 2 3; do read M2 R2_ L2_ < <(ms_of "$HM/stop0.json" "$EOT"); [ "$M2" -lt "$MS" ] && MS="$M2"; done
  chk "[N2] no run: Stop exits 0 with no output, nothing launched or written" '[ "$RC" = 0 ] && [ "$LEN" = 0 ] && [ ! -e "$OD" ] && [ ! -e "$STUB_LOG" ]'
  chk "[N3] no run: the whole Stop hook ($MS ms) stays under 250 ms (the check itself is one file test)" '[ "$MS" -lt 250 ]'

  echo "== START: the run starter makes the draft spec and flags the session =="
  OUT="$(mover "$SID" "/skill-builder demo-skill" 1)"
  local WD="$HM/brain/drafts/builds/demo-skill" SPEC="$HM/brain/drafts/builds/demo-skill/draft-spec.md"
  chk "[S1] starting the skill builder creates draft-spec.md from the form, header says the skill-builder itself writes it (2c)" '[ -f "$SPEC" ] && grep -q "Written by the skill-builder itself" "$SPEC" && grep -q "^## 1. WHAT THIS SKILL IS FOR" "$SPEC"'
  chk "[S2] the session is flagged (spec-sess flag names the run folder)" '[ "$(python3 "$H/lib/sb_spec.py" flag-wd "$SID")" = "$WD" ]'
  chk "[S3] the fresh shell counts 0 filled, 0 confirmed" 'python3 "$SC/completion.py" --spec "$SPEC" --counts | grep -q "^[0-9]* 0 0$"'

  OUT="$(SPEC_WRITER_RUNNING=1 mover "sess-nested" "/skill-builder nested-x quoted from the person's words" 1)"
  chk "[X1] the writer's own nested model session (which quotes /skill-builder) never starts a run or flags a session (found live: it looped)" '[ -z "$OUT" ] && [ ! -d "$HM/brain/drafts/builds/nested-x" ] && [ ! -f "$OD/spec-sess-sess-nested.flag" ]'

  O1="$(mover "sess-twin" "/skill-builder twin-x" 77)"; O2="$(mover "sess-twin" "/skill-builder twin-x" 77)"
  chk "[D1] a twin copy of the hook (plugin AND repo settings both registered) on the same prompt starts no second run and prints nothing" '[ -n "$O1" ] && [ "$(ls "$HM/brain/drafts/builds/twin-x/runs" | wc -l | tr -d " ")" = 1 ] && [ -z "$(printf "%s" "$O2" | tr -d "[:space:]")" ]'
  U1="$(ups "sess-twin" "x" 78)"; U2="$(ups "sess-twin" "x" 78)"
  chk "[D2] a twin copy of the prompt hook prints no second spec line (one not-changed line, not two)" '[ -n "$U1" ] && [ -z "$U2" ]'

  echo "== B2: the spec line =="
  OUT="$(ups "$SID" "my first thought" 2 "$WD")"
  chk "[R1] no change: the screen line is exactly 'not changed this turn' (2d)" '[ "$(printf "%s" "$OUT" | jq_ "d[\"systemMessage\"]")" = "📋 Spec: not changed this turn" ]'
  chk "[R2] the same line goes to the model (additionalContext)" 'printf "%s" "$OUT" | jq_ "d[\"hookSpecificOutput\"][\"additionalContext\"]" | grep -q "📋 Spec: not changed this turn"'
  python3 - "$SPEC" <<'PY'
import re, sys
p = sys.argv[1]; t = open(p, encoding="utf-8").read()
# two blanks that are alone on their line: one filled inferred, one filled with a citation (confirmed)
a = re.search(r"<\[ask\] time, money or stress; say which>", t); b = re.search(r"<\[ask\] one or two sentences>", t)
if a.start() > b.start(): a, b = b, a
first_is_a = True
t = t[:b.start()] + "the person's own words (D1)" + t[b.end():]
t = t[:a.start()] + "saves an hour [inferred]" + t[a.end():]
open(p, "w", encoding="utf-8").write(t)
PY
OUT="$(ups "$SID" "next thought" 3 "$WD")"
chk "[R3] a change: the line is exactly 'changed this turn' (2d: no slot counts)" '[ "$(printf "%s" "$OUT" | jq_ "d[\"systemMessage\"]")" = "📋 Spec: changed this turn" ]'
OUT="$(ups "$SID" "and again" 4 "$WD")"
chk "[R4] no further change: back to not changed" '[ "$(printf "%s" "$OUT" | jq_ "d[\"systemMessage\"]")" = "📋 Spec: not changed this turn" ]'
printf '\nA plain prose line that fills no slot.\n' >> "$SPEC"
OUT="$(ups "$SID" "prose only" 40 "$WD")"
chk "[R4b] a change that fills no slot (a prose line, the merged-layout case) still reads 'changed this turn' (hash, not counts)" '[ "$(printf "%s" "$OUT" | jq_ "d[\"systemMessage\"]")" = "📋 Spec: changed this turn" ]'
OUT="$(ups "$SID" "and nothing more" 41 "$WD")"
chk "[R4c] the next turn, untouched: not changed" '[ "$(printf "%s" "$OUT" | jq_ "d[\"systemMessage\"]")" = "📋 Spec: not changed this turn" ]'
chk "[R5] the counter is scripts/completion.py (the figure line and the counts agree)" 'python3 "$SC/completion.py" --spec "$SPEC" | head -1 | grep -q "%"'
printf '%s\n' "LIKELY CAUSE: one (evidence: a)" "DIDN'T HAPPEN: two" "SPEC GAP: three" "BETTER WAY: four" "LIKELY CAUSE: five" > "$OD/inbox-$SID.txt"
python3 - "$SPEC" <<'PY'
import re, sys
p = sys.argv[1]; t = open(p, encoding="utf-8").read()
m = re.search(r"<\[ask\] one or two sentences; say which>|<\[ask\] their answer[^<>]*>", t)
open(p, "w", encoding="utf-8").write(t[:m.start()] + "another [inferred]" + t[m.end():])
PY
OUT="$(ups "$SID" "with reviewer lines" 5 "$WD")"
local SM; SM="$(printf "%s" "$OUT" | jq_ "d[\"systemMessage\"]")"
chk "[M1] spec line and the reviewer line are ONE systemMessage of at most 2 lines (2d)" '[ "$(printf "%s\n" "$SM" | grep -c .)" -le 2 ] && [ "$(printf "%s" "$OUT" | grep -o "systemMessage" | wc -l | tr -d " ")" = 1 ]'
chk "[M2] the spec line is first, then exactly ONE reviewer line (the first of the five)" 'case "$(printf "%s\n" "$SM" | head -1)" in "📋 Spec:"*) true;; *) false;; esac && [ "$(printf "%s\n" "$SM" | grep -c .)" = 2 ] && printf "%s" "$SM" | grep -q "one" && ! printf "%s" "$SM" | grep -q "two"'
chk "[M3] the model gets both" 'printf "%s" "$OUT" | jq_ "d[\"hookSpecificOutput\"][\"additionalContext\"]" | grep -q "📋 Spec" && printf "%s" "$OUT" | jq_ "d[\"hookSpecificOutput\"][\"additionalContext\"]" | grep -q "one (evidence"'

  echo "== B4: bars from code, the mismatch check, the read list =="
  python3 "$SC/page_bar.py" init --workdir "$WD" --section walk-through --label "Walk-through" --total 3 > /dev/null
  { tline user '"show me page 1"'; tline assistant '[{"type":"tool_use","name":"Read","input":{"file_path":"/x/handoff-in.md"}},{"type":"tool_use","name":"Bash","input":{"command":"cat /y/known.md"}}]'; } > "$HM/t.jsonl"
  local GOODBAR; GOODBAR="$(python3 "$SC/page_bar.py" bar --workdir "$WD" --section walk-through)"
  OUT="$(mover "$SID" "what is on page one?" 6)"
  chk "[B1] the injected line carries the page bar exactly as page_bar.py prints it" 'printf "%s" "$OUT" | grep -qF "$GOODBAR"'
  chk "[B2] the injected line carries the completion figure line from completion.py" 'printf "%s" "$OUT" | grep -qF "$(python3 "$SC/completion.py" --spec "$SPEC" | head -1)"'
  chk "[B3] the line tells the model to print the bars exactly as given" 'printf "%s" "$OUT" | grep -q "exactly as given"'
  stopj "$SID" "Here is page 1.
$GOODBAR
more" "$HM/t.jsonl" > "$HM/stopb.json"; bash "$EOT" < "$HM/stopb.json" >/dev/null 2>&1; waitdone "$SID"
OUT="$(mover "$SID" "ok" 7)"
chk "[B4] a reply bar that matches code: no mismatch said" '! printf "%s" "$OUT" | grep -q "BAR MISMATCH"'
chk "[B5] the per-turn line lists the files read last turn (Read tool call and a cat)" 'printf "%s" "$OUT" | grep -q "READ LAST TURN" && printf "%s" "$OUT" | grep -q "x/handoff-in.md" && printf "%s" "$OUT" | grep -q "y/known.md"'
stopj "$SID" "Here is page 1.
Walk-through · page 2 of 3   ✅ ▶ ⬜
more" "$HM/t.jsonl" > "$HM/stopc.json"; bash "$EOT" < "$HM/stopc.json" >/dev/null 2>&1; waitdone "$SID"
OUT="$(mover "$SID" "ok again" 8)"
chk "[B6] a hand-drawn bar that does not match code: the next line says BAR MISMATCH" 'printf "%s" "$OUT" | grep -q "BAR MISMATCH"'
OUT="$(mover "$SID" "ok once more" 9)"
chk "[B7] the mismatch is said once" '! printf "%s" "$OUT" | grep -q "BAR MISMATCH"'
stopj "$SID" "▰▰▰▰▰▰▰▰▰▰ 99% · *probably okay to move on*" "$HM/t.jsonl" > "$HM/stopd.json"; bash "$EOT" < "$HM/stopd.json" >/dev/null 2>&1; waitdone "$SID"
OUT="$(mover "$SID" "ok and again" 10)"
chk "[B8] a made-up figure bar is a mismatch too" 'printf "%s" "$OUT" | grep -q "BAR MISMATCH"'

  echo "== B3: the writer =="
  rm -f "$HM/stub.log" "$OD/spec-offset-$SID"
  python3 - "$SPEC" "$HM" <<'PY'
import re, sys
p, hm = sys.argv[1], sys.argv[2]; t = open(p, encoding="utf-8").read()
blanks = [m.group(0) for m in re.finditer(r"<\[ask\][^<>]*>", t)]
open(hm + "/blanks.txt", "w").write("\n".join(b.replace("\n", " ") for b in blanks))
PY
  local B1 B2 B3; B1="$(sed -n 1p "$HM/blanks.txt" | cut -c1-60)"; B2="$(sed -n 2p "$HM/blanks.txt" | cut -c1-60)"; B3="$(sed -n 3p "$HM/blanks.txt" | cut -c1-60)"
  cp "$SPEC" "$HM/spec.before"
  local CONF; CONF="$(grep -m1 'What it saves' "$SPEC")"
  { tline user '"I want something that sorts my weekly receipts. Yes, that is exactly it: one list per category."'
    tline assistant '[{"type":"text","text":"So a receipt sorter. Is that right?"}]'; } > "$HM/t2.jsonl"
  cat > "$HM/reply.txt" <<EOF
SLOT: $B1
VALUE: a weekly receipt sorter
BY: PERSON
EVIDENCE: I want something that sorts my weekly receipts
---
SLOT: $B2
VALUE: one list per category
BY: PERSON
EVIDENCE: the assistant said this and the person never did
---
SLOT: <[ask] this blank does not exist anywhere in the draft
VALUE: nope
BY: INFERRED
EVIDENCE: nope
---
SLOT: the person's own words (D1)
VALUE: should never overwrite a confirmed line
BY: INFERRED
EVIDENCE: Yes, that is exactly it
END-WRITE
EOF
  export STUB_REPLY_FILE="$HM/reply.txt"
  stopj "$SID" "ok" "$HM/t2.jsonl" > "$HM/stop2.json"
  CLAUDE_CODE_SESSION_ID="$SID" bash "$R/system/hooks/lib/spec_write.sh" "$HM/stop2.json" "$SID"
  chk "[W1] the writer ran the model once, at the medium tier" '[ "$(wc -l < "$STUB_LOG" | tr -d " ")" = 1 ] && grep -q "$(bash -c ". \"$R/system/tools/model.lib.sh\"; model_id_for_tier medium")" "$STUB_LOG"'
  chk "[W2] an evidenced PERSON line is written with a D-citation and a D line in DECISIONS" 'grep -q "a weekly receipt sorter (D2)" "$SPEC" && grep -q "^D2 · .* · a weekly receipt sorter · the person" "$SPEC"'
  chk "[W3] a PERSON claim whose quote is not the person's words is written [inferred], not confirmed" 'grep -q "one list per category \[inferred\]" "$SPEC"'
  chk "[W4] a made-up blank is rejected and logged; nothing else changed" 'grep -q "REJECTED" "$WD/spec-evidence.md" && ! grep -q "nope" "$SPEC"'
  chk "[W5] a confirmed line is never overwritten or deleted" '[ -n "$CONF" ] && grep -qxF -- "$CONF" "$SPEC" && ! grep -q "should never overwrite" "$SPEC"'
  chk "[W6] every added line has its quoted evidence in spec-evidence.md" 'grep -q "I want something that sorts my weekly receipts" "$WD/spec-evidence.md" && grep -q "FILLED \[inferred\]" "$WD/spec-evidence.md"'
  chk "[W7] the file is whole (no temp files left, header intact)" '[ -z "$(ls -a "$WD" | grep "^\.tmp-")" ] && grep -q "Written by the skill-builder itself" "$SPEC"'
  W8D="$(comm -23 <(sort "$HM/spec.before") <(sort "$SPEC"))"; W8N="$(printf "%s" "$W8D" | grep -c .)"; printf "W8 diff (%s lines):\n%s\n" "$W8N" "$W8D" > "$HM/w8diff.txt"
chk "[W8] the person never lost a line: every old line is still there except the two blanks replaced" '[ "$(comm -23 <(sort "$HM/spec.before") <(sort "$SPEC") | wc -l | tr -d " ")" -le 2 ]'
  # CONFIRM an [inferred] line
  { tline user '"yes, that is it: saves an hour is right"'; } > "$HM/t3.jsonl"
  printf 'CONFIRM: %s\nEVIDENCE: yes, that is it: saves an hour is right\nEND-WRITE\n' "$(grep -m1 'saves an hour \[inferred\]' "$SPEC" | cut -c1-60)" > "$HM/reply2.txt"
  export STUB_REPLY_FILE="$HM/reply2.txt"; stopj "$SID" ok "$HM/t3.jsonl" > "$HM/stop3.json"
  rm -f "$OD/spec-offset-$SID"
  CLAUDE_CODE_SESSION_ID="$SID" bash "$R/system/hooks/lib/spec_write.sh" "$HM/stop3.json" "$SID"
  chk "[W9] the person's yes confirms an [inferred] line: mark removed, D-citation added" '! grep -q "saves an hour \[inferred\]" "$SPEC" && grep -q "saves an hour (D[0-9]*)" "$SPEC"'
  OUT="$(ups "$SID" "after the writer" 11 "$WD")"
  chk "[W10] the spec line then reports the (dormant) writer's change as 'changed this turn'" '[ "$(printf "%s" "$OUT" | jq_ "d[\"systemMessage\"]")" = "📋 Spec: changed this turn" ]'
  # model failure
  export STUB_FAIL=1; stopj "$SID" ok "$HM/t3.jsonl" > "$HM/stop4.json"
  CLAUDE_CODE_SESSION_ID="$SID" bash "$R/system/hooks/lib/spec_write.sh" "$HM/stop4.json" "$SID"; unset STUB_FAIL
  chk "[W11] a failed model call leaves the spec as it was, says why in the evidence file and on the next spec line" 'grep -q "WRITER FAILED" "$WD/spec-evidence.md" && ups "$SID" "x" 12 "$WD" | jq_ "d[\"systemMessage\"]" | grep -q "the writer did not run"'

  # the marker (found live in Enver's window: "model output missing marker" on the NOTHING reply)
  rm -f "$OD/spec-offset-$SID" "$OD/spec-fail-$SID.txt"; printf 'NOTHING\n' > "$HM/reply3.txt"
  export STUB_REPLY_FILE="$HM/reply3.txt" STUB_NO_MARKER=1; stopj "$SID" ok "$HM/t2.jsonl" > "$HM/stop6.json"
  NF0="$(grep -c "WRITER FAILED" "$WD/spec-evidence.md")"
  CLAUDE_CODE_SESSION_ID="$SID" bash "$R/system/hooks/lib/spec_write.sh" "$HM/stop6.json" "$SID"; unset STUB_NO_MARKER
  chk "[K1] a NOTHING reply with no END-WRITE marker at all is not a failure (no fail file, no new WRITER FAILED, offset advanced)" '[ ! -f "$OD/spec-fail-$SID.txt" ] && [ "$(grep -c "WRITER FAILED" "$WD/spec-evidence.md")" = "$NF0" ] && [ -s "$OD/spec-offset-$SID" ]'
  rm -f "$OD/spec-offset-$SID"; BL="<[ask] the problem it solves and the result, in the person's"; grep -qF -- "$BL" "$SPEC" || BL=""
  printf 'SLOT: %s\nVALUE: when the receipt photo is blurry\nBY: INFERRED\nEVIDENCE: I want something that sorts my weekly receipts' "$BL" > "$HM/reply4.txt"
  export STUB_REPLY_FILE="$HM/reply4.txt" STUB_INLINE=1; stopj "$SID" ok "$HM/t2.jsonl" > "$HM/stop7.json"
  CLAUDE_CODE_SESSION_ID="$SID" bash "$R/system/hooks/lib/spec_write.sh" "$HM/stop7.json" "$SID"; unset STUB_INLINE
  chk "[K2] the marker glued onto the last line of a record is read as the marker: the record is applied, no marker text in the spec or the evidence" '[ -n "$BL" ] && grep -q "when the receipt photo is blurry \[inferred\]" "$SPEC" && ! grep -q "END-WRITE" "$SPEC" && ! grep -q "END-WRITE" "$WD/spec-evidence.md"'
  chk "[K3] the writer prompt tells the model to end every reply, NOTHING included, with END-WRITE" 'grep -q "ALWAYS end your reply with the line END-WRITE" "$HM/prompt.seen"'

# 2c task 4: the decision check. The warning reads the PREVIOUS prompt (the state stores that prompt's decision look):
OUT="$(ups "$SID" "catching the baseline up" 50 "$WD")" # sync the state to the spec as the writer runs left it
OUT="$(ups "$SID" "lock that in: keep that wording" 51 "$WD")"
chk "[R6a] decision words, spec unchanged: the line is still the plain not-changed line this turn" '[ "$(printf "%s" "$OUT" | jq_ "d[\"systemMessage\"]")" = "📋 Spec: not changed this turn" ]'
OUT="$(ups "$SID" "what was that?" 52 "$WD")"
chk "[R6b] the next report after a decision prompt with the spec still unchanged: the ⚠ warning, loudly" 'printf "%s" "$OUT" | jq_ "d[\"systemMessage\"]" | grep -q "⚠ You decided something this turn; the spec did not change."'
OUT="$(ups "$SID" "carry on" 53 "$WD")"
chk "[R6c] no decision words: back to the plain line, no ⚠" 'printf "%s" "$OUT" | jq_ "d[\"systemMessage\"]" | grep -q "not changed this turn" && ! printf "%s" "$OUT" | jq_ "d[\"systemMessage\"]" | grep -q "⚠"'
python3 - "$SPEC" <<'PY6'
import re, sys
p = sys.argv[1]; t = open(p, encoding="utf-8").read()
m = re.search(r"<\[ask\][^<>]*>", t)
open(p, "w", encoding="utf-8").write(t[:m.start()] + "decided by the person [inferred]" + t[m.end():])
PY6
OUT="$(ups "$SID" "yes, go with that order" 54 "$WD")"
chk "[R6d] decision words but the spec DID change: the normal 'changed this turn' line, no ⚠" '[ "$(printf "%s" "$OUT" | jq_ "d[\"systemMessage\"]")" = "📋 Spec: changed this turn" ] && ! printf "%s" "$OUT" | jq_ "d[\"systemMessage\"]" | grep -q "⚠"'
OUT="$(ups "$SID" "hmm" 55 "$WD")"
chk "[R6e] a later turn with the spec unchanged again warns (the decision at 54 was never written either)" 'printf "%s" "$OUT" | jq_ "d[\"systemMessage\"]" | grep -q "⚠ You decided something this turn"'
OUT="$(ups "$SID" "right" 56 "$WD")"
chk "[R6f] one plain prompt later the line is plain again (state reset for the tests below)" 'printf "%s" "$OUT" | jq_ "d[\"systemMessage\"]" = "📋 Spec: not changed this turn" 2>/dev/null || printf "%s" "$OUT" | jq_ "d[\"systemMessage\"]" | grep -q "not changed this turn"'
  echo "== one writer at a time; the Stop launch =="
  rm -f "$HM/stub.log"; export STUB_REPLY_FILE="$HM/reply2.txt" STUB_SLEEP=2
  stopj "$SID" ok "$HM/t3.jsonl" > "$HM/stop5.json"
  bash "$EOT" < "$HM/stop5.json" >/dev/null 2>&1; sleep 0.6
  local PIDF="$OD/spec-write-$SID.pid"
  chk "[L1] a live run: Stop starts NO spec writer (2c, switched off): no pid file, no detached process" '[ ! -e "$PIDF" ]'
  bash "$EOT" < "$HM/stop5.json" >/dev/null 2>&1
  chk "[L2] a second Stop still launches nothing" '[ ! -e "$PIDF" ] && [ ! -e "$STUB_LOG" ]'
  sleep 1.5; unset STUB_SLEEP
  chk "[L3] no model call at all for the two Stops (the writer is off; the direct spec_write runs above made the earlier calls)" '[ ! -e "$STUB_LOG" ] || [ "$(wc -l < "$STUB_LOG" | tr -d " ")" = 0 ]'
  # a finished run: flag cleared, nothing launched
  P="$(python3 "$R/system/parts/stage_runner.py" status --json --workdir "$WD" 2>/dev/null)"
  echo "$P" | grep -q '"skill"' && ok "[L4] (the runner reports the live run)" || bad "[L4] runner status unreadable"
  rm -f "$OD/spec-sess-$SID.flag"; rm -f "$HM/stub.log"; bash "$EOT" < "$HM/stop5.json" >/dev/null 2>&1; sleep 0.5
  chk "[L5] flag gone (run over or never started): Stop launches nothing" '[ ! -e "$STUB_LOG" ]'
  OUT="$(ups "$SID" "no flag now" 13 "$WD")"
  chk "[L6] flag gone: no spec line" '[ -z "$OUT" ]'
}

forced_error() {   # forced_error <plugin-root>: a broken completion.py makes the failure visible and logged, never silent
  local R="$1" HM; HM="$(mktemp -d "$T/fe.XXXXXX")"
  export HOME="$HM" LIFEHACK_ROOT="$HM/brain"; mkdir -p "$HM/brain" "$HM/elsewhere"
  local H="$R/system/hooks" SID="sess-spec-err" SC="$R/.claude/skills/skill-builder/scripts"
  local PJ; PJ() { python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"prompt_id":"p"+sys.argv[3],"cwd":sys.argv[4],"hook_event_name":"UserPromptSubmit","prompt":sys.argv[2],"transcript_path":"/x"}))' "$@"; }
  PJ "$SID" "/skill-builder err-skill" 1 "$HM/elsewhere" | sh "$H/run_step_hook.sh" >/dev/null 2>&1
  local WD="$HM/brain/drafts/builds/err-skill"
  cp "$SC/completion.py" "$HM/completion.good"; printf 'raise RuntimeError("forced for the test")\n' > "$SC/completion.py"
  printf '[1]' > "$HM/.claude/run/observe/spec-state-$SID.json"   # 2d: the line no longer uses the counter; a corrupt state file forces the error
  OUT="$(PJ "$SID" "hello" 2 "$WD" | bash "$H/observe_ups.sh" 2>/dev/null)"
  chk "[E1] a forced error in the reporter: the screen says 'Spec line unavailable', never nothing" 'printf "%s" "$OUT" | grep -q "Spec line unavailable"'
  chk "[E2] and it is logged to spec-errors.log, tagged with the script name" 'grep -q "sb_spec.py: spec report failed: AttributeError" "$HM/.claude/run/observe/spec-errors.log"'
  OUT="$(PJ "$SID" "plain chat" 3 "$WD" | sh "$H/run_step_hook.sh" 2>&1)"
  chk "[E3] the model's per-turn line says the figure is unavailable (show no bar)" 'printf "%s" "$OUT" | grep -q "FIGURE (from code): unavailable"'
  cp "$HM/completion.good" "$SC/completion.py"
}

echo "################ REAL TREE ($PLUG)"
suite "$PLUG"
FE="$T/fe-plug"; mkdir -p "$FE/.claude/skills"; rsync -a "$PLUG/system" "$PLUG/shared" "$FE/" ; rsync -a "$PLUG/.claude/skills/skill-builder" "$FE/.claude/skills/"
echo "== forced errors (a copy of the plugin) =="
forced_error "$FE"
echo "passed=$pass failed=$fail"
REAL_FAIL=$fail

if [ -z "$SPEC_NOBROKEN" ]; then
  echo "== BROKEN COPIES: each check must FAIL on a copy with one edit =="
  broken() {   # broken <name> <file under plugin> <old> <new> <check id that must fail> [<old2> <new2>]
    local C="$T/br-$1"; mkdir -p "$C/.claude/skills"; rsync -a "$PLUG/system" "$PLUG/shared" "$C/"; rsync -a "$PLUG/.claude/skills/skill-builder" "$C/.claude/skills/"
    python3 - "$C/$2" "$3" "$4" "${6:-}" "${7:-}" <<'PY'
import sys
p, old, new, old2, new2 = sys.argv[1:6]
s = open(p, encoding="utf-8").read()
assert old in s, "break marker missing: " + old
s = s.replace(old, new)
if old2:
    assert old2 in s, "second break marker missing: " + old2
    s = s.replace(old2, new2)
open(p, "w", encoding="utf-8").write(s)
PY
    [ $? = 0 ] || { bad "[broken $1] could not break the copy"; return; }
    local o; o="$(SPEC_NOBROKEN=1 SPEC_PLUG="$C" bash "$0" 2>&1)"
    if printf '%s\n' "$o" | grep -q "FAIL  \[$5\]"; then ok "[broken $1] the copy fails $5"; else bad "[broken $1] $5 did NOT fail on the broken copy"; fi
  }
  broken always-changed system/hooks/lib/sb_spec.py 'if not prev or prev.get("hash") == now["hash"]:' 'if False:' R1
  broken no-cap system/hooks/observe_ups.sh 'lines[:1]' 'lines[:5]' M2 '["🛠 " + x for x in show[:1]]' '["🛠 " + x for x in show]'
  broken never-changed system/hooks/lib/sb_spec.py 'return "📋 Spec: changed this turn" + extra' 'return "📋 Spec: not changed this turn" + extra' R3
  broken mismatch-blind system/hooks/lib/sb_spec.py '        if bad:
            is_page' '        if False:
            is_page' B6
  broken person-unchecked system/hooks/lib/sb_spec.py 'who = "person" if by == "PERSON" and qn in persons else "inferred"' 'who = "person" if by == "PERSON" else "inferred"' W3
  broken no-inferred-mark system/hooks/lib/sb_spec.py 'rep = value + " [inferred]"' 'rep = value' W3
  broken writer-relaunched system/hooks/end_of_turn_checks.sh 'printf '"'"'%s'"'"' "$P" | python3 "$_lhb_dir/lib/sb_spec.py" stop "$SID"' 'printf '"'"'%s'"'"' "$P" > "$OBSD/spec-stop-$SID.json"; nohup bash "$_lhb_dir/lib/spec_write.sh" "$OBSD/spec-stop-$SID.json" "$SID" </dev/null >>"$OBSD/spec-writer.log" 2>&1 & echo $! > "$OBSD/spec-write-$SID.pid"; disown; printf '"'"'%s'"'"' "$P" | python3 "$_lhb_dir/lib/sb_spec.py" stop "$SID"' L1
  broken no-decision system/hooks/lib/sb_spec.py 'state["decided"] = bool(DECISION_RE.search(prompt)) if prompt else False' 'state["decided"] = False' R6b
  broken no-bars system/hooks/lib/sb_start.py 'out += sb_spec.turn_lines(hooks, a[0], sid)' 'pass' B1
  broken silent-error system/hooks/lib/sb_spec.py 'return "📋 Spec line unavailable: %s" % _log("spec report", e)[:160]' 'return None' E1
  broken no-spec-shell system/hooks/lib/sb_spec.py '        ensure_spec(plug, wd)
        _write_atomic(flag_path' '        _write_atomic(flag_path' S1
  broken twin-begin system/hooks/lib/sb_start.py 'if not sb_spec.claim("begin", sid, pid):' 'if False:' D1
  broken twin-report system/hooks/lib/sb_spec.py 'if not claim("report", sid, pid):' 'if False:' D2
  broken marker-demanded system/hooks/lib/spec_write.sh 'run_model medium "$PROMPT" "$REPLY" 2>&1' 'run_model medium "$PROMPT" "$REPLY" END-WRITE 2>&1' K1
  broken marker-inline system/hooks/lib/sb_spec.py 'if line.endswith("END-WRITE"):' 'if line == "END-WRITE":' K2
  broken nested-loop system/hooks/lib/sb_start.py 'if os.environ.get("SPEC_WRITER_RUNNING"):' 'if False:' X1
  echo "passed=$pass failed=$fail"
  [ "$fail" = 0 ]
else
  [ "$REAL_FAIL" = 0 ]
fi
