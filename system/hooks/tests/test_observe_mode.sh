#!/bin/bash
# Matrix for OBSERVE MODE (round 2, brief 2.1): the Stop launcher step in system/hooks/end_of_turn_checks.sh, the detached
# reviewer system/tools/observe_review.sh, the switch system/tools/observe_flag.sh, and the prompt hook
# system/hooks/observe_ups.sh (arm / note / wrap / show findings). No real model call: LIFEHACK_MODEL_STUB.
# Each run uses a temp HOME and a temp notes root. UNARMED cases first. After the real tree passes, every check is shown
# FAILING on a deliberately broken copy (a symlink mirror of the plugin with ONE file edited), so no check is vacuous.
PLUG="$(cd "$(dirname "$0")/../../.." && pwd -P)"
T="$(cd "$(mktemp -d)" && pwd -P)"; trap 'rm -rf "$T"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); printf '   ok   %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL  %s\n' "$1"; }
chk() { if eval "$2"; then ok "$1"; else bad "$1  <<$2>>"; fi; }

# the model stub: sleeps STUB_SLEEP, logs the model id, keeps a copy of the prompt, then replies (or fails)
cat > "$T/stub.sh" <<'EOF'
#!/bin/bash
sleep "${STUB_SLEEP:-0}"
echo "$1" >> "$STUB_LOG"
cp "$2" "$STUB_PROMPT_COPY" 2>/dev/null
[ "${STUB_FAIL:-0}" = 1 ] && exit 1
if [ -n "${STUB_REPLY_FILE:-}" ]; then cat "$STUB_REPLY_FILE" > "$3"; else echo NOTHING > "$3"; fi
echo END-REVIEW >> "$3"
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
  export HOME="$HM" LIFEHACK_ROOT="$HM/brain"; mkdir -p "$HM/brain"
  local EOT="$R/system/hooks/end_of_turn_checks.sh" UPS="$R/system/hooks/observe_ups.sh" REV="$R/system/tools/observe_review.sh" FT="$R/system/tools/observe_flag.sh"
  export OBSERVE_WAIT=0 LIFEHACK_MODEL_STUB="$T/stub.sh" STUB_LOG="$HM/stub.log" STUB_PROMPT_COPY="$HM/prompt.seen"
  unset STUB_FAIL STUB_REPLY_FILE STUB_SLEEP
  local OD="$HM/.claude/run/observe" NB="$HM/brain/drafts/builds/audit"
  local MED; MED="$(bash -c ". '$R/system/tools/model.lib.sh'; model_id_for_tier medium")"
  arm() { CLAUDE_CODE_SESSION_ID="$1" bash "$FT" arm "$2"; }
  stopj() { python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"prompt_id":"p1","hook_event_name":"Stop","stop_hook_active":False,"last_assistant_message":"done","cwd":sys.argv[3],"transcript_path":sys.argv[2]}))' "$1" "$HM/t.jsonl" "${2:-$HM}" > "$HM/stop-$1.json"; }
  upsj() { python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"prompt_id":"p","cwd":"/x","hook_event_name":"UserPromptSubmit","prompt":sys.argv[2]}))' "$1" "$2"; }
  ups() { upsj "$1" "$2" | bash "$UPS"; }
  waitdone() { local i=0; while [ -f "$OD/review-$1.pid" ] && [ $i -lt 100 ]; do sleep 0.2; i=$((i+1)); done; sleep 0.3; }
  tline() { python3 -c 'import json,sys; print(json.dumps({"type":sys.argv[1],"message":{"role":sys.argv[1],"content":json.loads(sys.argv[2])}}))' "$1" "$2"; }
  { tline user '"OLD-TURN-TEXT before the watch"'; tline assistant '[{"type":"text","text":"old answer"}]'
    tline user '"I want a skill for my budget check"'; tline assistant '[{"type":"thinking","thinking":"HIDDEN-THOUGHT"},{"type":"text","text":"What changes in your week when it works?"}]'
    tline user '[{"type":"tool_result","content":"SECRET-TOOL-OUTPUT"}]'; } > "$HM/t.jsonl"
  local SKTITLE; SKTITLE="$(grep -m1 '^# ' "$R/.claude/skills/audit/SKILL.md")"

  echo "== UNARMED (nothing watched) =="
  stopj s0; read MS RC LEN < <(ms_of "$HM/stop-s0.json" "$EOT")
  for _i in 1 2 3; do read M2 R2_ L2_ < <(ms_of "$HM/stop-s0.json" "$EOT"); [ "$M2" -lt "$MS" ] && MS="$M2"; done   # best of 4: a loaded machine is noise
  chk "[U1] unarmed Stop: exit 0, no output" '[ "$RC" = 0 ] && [ "$LEN" = 0 ]'
  chk "[U1] unarmed Stop: no process launched, nothing written (no observe folder, no model call)" '[ ! -e "$OD" ] && [ ! -e "$STUB_LOG" ]'
  chk "[U2] unarmed Stop: whole hook ($MS ms) stays near its old cost (~100 ms before this step existed), under 250 ms" '[ "$MS" -lt 250 ]'
  TR="$(bash -x "$EOT" < "$HM/stop-s0.json" 2>&1 >/dev/null | grep -A3 "^+ OBSD=")"
  chk "[U2] unarmed Stop: after the switch path is built, the next command is ONE file test and the step is skipped (no find, kill, nohup, python)" '[ "$(printf "%s\n" "$TR" | sed -n 2p | grep -c -- "-f ")" = 1 ] && ! printf "%s" "$TR" | grep -qE "find|kill|nohup|python|mkdir"'
  chk "[U3] quiet prompt, nothing waiting: no output, nothing written" '[ -z "$(ups s0 "hello there")" ] && [ ! -e "$OD" ]'

  echo "== ARMED launcher =="
  chk "[A0] arm: prints OBSERVE ARMED with the notes folder" 'arm s1 audit | grep -q "^OBSERVE ARMED: audit|$NB$"'
  chk "[A0] arm: flag names skill file, notes folder, session" 'grep -q "^skill_file=.*/audit/SKILL.md$" "$OD/observe-sess-s1.flag" && grep -q "^notes_dir=$NB$" "$OD/observe-sess-s1.flag" && grep -q "^session=s1$" "$OD/observe-sess-s1.flag"'
  export STUB_SLEEP=2; stopj s1; read MS RC LEN < <(ms_of "$HM/stop-s1.json" "$EOT")
  chk "[A1] armed Stop: exit 0, no output, does not wait for the reviewer ($MS ms)" '[ "$RC" = 0 ] && [ "$LEN" = 0 ] && [ "$MS" -lt 1000 ]'
  chk "[A1] armed Stop: a reviewer is running (pid file, live process)" '[ -f "$OD/review-s1.pid" ] && kill -0 "$(cat "$OD/review-s1.pid")" 2>/dev/null'
  read MS RC LEN < <(ms_of "$HM/stop-s1.json" "$EOT"); waitdone s1
  chk "[A2] a second Stop while it runs is skipped: exactly one model call" '[ "$(grep -c . "$STUB_LOG")" = 1 ]'
  chk "[A3] the model call names the MEDIUM tier id ($MED)" 'grep -qx "$MED" "$STUB_LOG"'
  chk "[A3] prompt carries the skill design, the person words, the assistant text" 'grep -qF "$SKTITLE" "$STUB_PROMPT_COPY" && grep -q "I want a skill for my budget check" "$STUB_PROMPT_COPY" && grep -q "What changes in your week" "$STUB_PROMPT_COPY"'
  chk "[A3] prompt leaves out tool results, thoughts and the turns before the watch" '! grep -qE "SECRET-TOOL-OUTPUT|HIDDEN-THOUGHT|OLD-TURN-TEXT" "$STUB_PROMPT_COPY"'
  chk "[A4] pid file removed when the reviewer ends" '[ ! -f "$OD/review-s1.pid" ]'
  unset STUB_SLEEP

  echo "== REVIEWER (stub replies) =="
  local NR="$HM/reply.txt"
  printf '%s\n' "preamble the parser must ignore" "SHOW: SPEC GAP: first (evidence: \"a\")" "LOG: BETTER WAY: second" "SHOW: DIDN'T HAPPEN: third" "LOG: LIKELY CAUSE: fourth" "LOG: SPEC GAP: fifth" > "$NR"
  export STUB_REPLY_FILE="$NR"; rm -f "$NB/findings.md" "$OD/inbox-s1.txt"; arm s1 audit >/dev/null; stopj s1; bash "$REV" "$HM/stop-s1.json" s1
  chk "[R1] findings.md gets every line, timestamped, with its tag" '[ "$(grep -cE "^- \[20[0-9-]+ [0-9:]+\] (SHOW|LOG) " "$NB/findings.md")" = 5 ] && grep -q "LOG LIKELY CAUSE: fourth" "$NB/findings.md"'
  chk "[R1] inbox gets exactly the 2 SHOW lines, kind first, no tag" '[ "$(grep -c . "$OD/inbox-s1.txt")" = 2 ] && head -1 "$OD/inbox-s1.txt" | grep -q "^SPEC GAP: first" && ! grep -q "SHOW" "$OD/inbox-s1.txt"'
  printf 'SHOW: SPEC GAP: s%s\n' 1 2 3 4 5 6 7 > "$NR"; rm -f "$OD/inbox-s1.txt"; arm s1 audit >/dev/null; bash "$REV" "$HM/stop-s1.json" s1
  chk "[R2] seven SHOW lines: inbox holds at most 5" '[ "$(grep -c . "$OD/inbox-s1.txt")" = 5 ]'
  chk "[R2] ... and findings.md still keeps all seven" '[ "$(grep -c "SHOW SPEC GAP: s" "$NB/findings.md")" = 7 ]'
  echo NOTHING > "$NR"; rm -f "$OD/inbox-s1.txt"; B4="$(grep -c . "$NB/findings.md")"; arm s1 audit >/dev/null; bash "$REV" "$HM/stop-s1.json" s1
  chk "[R3] reply NOTHING: no new finding, no inbox" '[ "$(grep -c . "$NB/findings.md")" = "$B4" ] && [ ! -s "$OD/inbox-s1.txt" ]'
  export STUB_FAIL=1; rm -f "$OD/inbox-s1.txt" "$OD/failnotified-s1"; B4="$(grep -c "REVIEWER FAILED" "$NB/findings.md")"; arm s1 audit >/dev/null; bash "$REV" "$HM/stop-s1.json" s1
  chk "[R4] stub failure: the inbox gets ONE 'reviewer did not run: <reason>' line" '[ "$(grep -c . "$OD/inbox-s1.txt")" = 1 ] && grep -q "^reviewer did not run: .*rc=1" "$OD/inbox-s1.txt"'
  bash "$REV" "$HM/stop-s1.json" s1
  chk "[R4] a second failure in a row does not repeat it; findings.md records both" '[ "$(grep -c . "$OD/inbox-s1.txt")" = 1 ] && [ "$(grep -c "REVIEWER FAILED" "$NB/findings.md")" = $((B4+2)) ]'
  unset STUB_FAIL
  printf 'LOG: SPEC GAP: ok\n' > "$NR"; arm s1 audit >/dev/null; bash "$REV" "$HM/stop-s1.json" s1
  chk "[R4] after a success the failure line can be sent again" '[ ! -f "$OD/failnotified-s1" ]'
  # offset: first review reads from the last person message; the next reads only what is new
  rm -f "$OD/inbox-s1.txt"; arm s1 audit >/dev/null; bash "$REV" "$HM/stop-s1.json" s1; SZ="$(wc -c < "$HM/t.jsonl" | tr -d ' ')"
  chk "[R5] offset saved after a good review = transcript size" '[ "$(CLAUDE_CODE_SESSION_ID=s1 bash "$FT" get offset)" = "$SZ" ]'
  { tline user '"the second turn mentions ZEBRA"'; tline assistant '[{"type":"text","text":"answer about ZEBRA"}]'; } >> "$HM/t.jsonl"
  bash "$REV" "$HM/stop-s1.json" s1
  chk "[R5] the next review reads only the new text" 'grep -q "ZEBRA" "$STUB_PROMPT_COPY" && ! grep -q "I want a skill for my budget check" "$STUB_PROMPT_COPY"'
  chk "[R5] ... and moves the offset on" '[ "$(CLAUDE_CODE_SESSION_ID=s1 bash "$FT" get offset)" = "$(wc -c < "$HM/t.jsonl" | tr -d " ")" ]'
  # the person's notes and the step prompt
  printf '\n### 2026-11-25 10:00:00\nNOTE-WORDS-VERBATIM\n' > "$NB/notes.md"; bash "$REV" "$HM/stop-s1.json" s1
  chk "[R6] prompt carries the tail of the person's notes" 'grep -q "NOTE-WORDS-VERBATIM" "$STUB_PROMPT_COPY"'
  local WD="$HM/rundir"; mkdir -p "$WD/prompts"; echo 'STEPPROMPT-MARKER {{ID}} writes {{OUT}}' > "$WD/prompts/01-frame.md"
  printf '{"skill":"audit","stop_limit":3,"stages":[{"id":"frame","mode":"talk","prompt":"prompts/01-frame.md","out":"out/01-frame.md","checks":{"min_words":1}}]}' > "$WD/card.json"
  CLAUDE_CODE_SESSION_ID=s1 python3 "$R/system/parts/stage_runner.py" start --workdir "$WD" --card "$WD/card.json" >/dev/null 2>&1
  stopj s1 "$WD"; bash "$REV" "$HM/stop-s1.json" s1
  chk "[R7] an open run of THIS skill: its current step prompt is in the review prompt" 'grep -q "STEPPROMPT-MARKER frame" "$STUB_PROMPT_COPY" && grep -q "step 1 of 1" "$STUB_PROMPT_COPY"'
  rm -rf "$WD"; mkdir -p "$WD/prompts"; echo 'STEPPROMPT-MARKER {{ID}}' > "$WD/prompts/01-frame.md"
  printf '{"skill":"some-other-skill","stop_limit":3,"stages":[{"id":"frame","mode":"talk","prompt":"prompts/01-frame.md","out":"out/01-frame.md","checks":{"min_words":1}}]}' > "$WD/card.json"
  CLAUDE_CODE_SESSION_ID=s1 python3 "$R/system/parts/stage_runner.py" start --workdir "$WD" --card "$WD/card.json" >/dev/null 2>&1
  bash "$REV" "$HM/stop-s1.json" s1
  chk "[R7] an open run of ANOTHER skill: no step prompt" '! grep -q "STEPPROMPT-MARKER" "$STUB_PROMPT_COPY" && grep -q "no open run of this skill" "$STUB_PROMPT_COPY"'
  CLAUDE_CODE_SESSION_ID=s1 bash "$R/system/tools/run_pointer.sh" clear >/dev/null
  # cleared while waiting: nothing happens
  CLAUDE_CODE_SESSION_ID=s1 bash "$FT" clear >/dev/null; : > "$STUB_LOG"; bash "$REV" "$HM/stop-s1.json" s1
  chk "[R8] switch cleared: the reviewer makes no call" '[ ! -s "$STUB_LOG" ]'

  echo "== SHOWING findings (prompt hook) =="
  mkdir -p "$OD"; printf 'SPEC GAP: one (evidence: "x")\nBETTER WAY: two\n' > "$OD/inbox-s2.txt"
  OUT="$(ups s2 "next thing I type")"
  chk "[I1] inbox present: valid JSON with systemMessage AND additionalContext, headed" 'printf "%s" "$OUT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d[\"systemMessage\"].startswith(\"🛠 Skill builder here:\n1. SPEC GAP: one\"), d
h=d[\"hookSpecificOutput\"]
assert h[\"hookEventName\"]==\"UserPromptSubmit\" and h[\"additionalContext\"].startswith(\"[harness-injected, not user input] 🛠 Skill builder here:\"), h
"'
  chk "[I1] ... then the inbox is cleared (moved aside)" '[ ! -e "$OD/inbox-s2.txt" ]'
  chk "[I2] no inbox: no output" '[ -z "$(ups s2 "and another")" ]'
  python3 -c 'print("\n".join("BETTER WAY: " + ("long finding %d " % i) * 20 for i in range(8)))' > "$OD/inbox-s2.txt"; OUT="$(ups s2 "x")"
  chk "[I3] 8 long lines: at most 5 lines shown, about 1,200 characters" 'printf "%s" "$OUT" | python3 -c "
import json,sys
m=json.load(sys.stdin)[\"systemMessage\"].split(\"\n\")[1:]
assert 1<=len(m)<=5 and sum(len(x)+1 for x in m)<=1250, (len(m), sum(len(x)+1 for x in m))
"'
  python3 -c 'print("\n".join("SPEC GAP: short %d" % i for i in range(8)))' > "$OD/inbox-s2.txt"; OUT="$(ups s2 "x")"
  chk "[I3] 8 short lines: exactly 5 shown" '[ "$(printf "%s" "$OUT" | python3 -c "import json,sys; print(len(json.load(sys.stdin)[\"systemMessage\"].split(\"\n\"))-1)")" = 5 ]'
  chk "[I4] it is its own hook, never a member of the pilot-map-ups group (the dispatcher concatenates stdout)" '! grep -q "observe_ups" "$R/system/hooks/group_dispatch_pilot-map-ups.sh" && python3 -c "
import json
r=[json.loads(l) for l in open(\"$R/system/register/register.jsonl\")]
h=[x for x in r if x.get(\"path\")==\"/system/hooks/observe_ups.sh\" and x[\"type\"]==\"hook\"]
assert len(h)==1 and h[0][\"group\"] is None and h[0][\"event\"]==\"UserPromptSubmit\"
"'

  echo "== COMMANDS and NOTES =="
  OUT="$(ups s3 "/skill-builder observe audit")"
  chk "[C1] observe: ARMED line names the skill and the notes folder; flag exists" 'printf "%s" "$OUT" | grep -qF "OBSERVE ARMED: Observing audit; notes go to $NB; /skill-builder note to jot, /skill-builder wrap at the end" && [ -f "$OD/observe-sess-s3.flag" ]'
  OUT="$(ups s3 "/skill-builder observe no-such-skill")"
  chk "[C1] observe an unknown skill: NOT ARMED, says why" 'printf "%s" "$OUT" | grep -q "OBSERVE NOT ARMED: no skill named"'
  chk "[C2] skill-builder's notes go to the packet folder" 'ups s4 "/skill-builder observe skill-builder" | grep -qF "build-rebuild/16-skill-builder-packet"'
  rm -f "$NB/notes.md"
  N1='he said "hi" $HOME `ls` '"'"'q'"'"' 🎉 \n {braces} $(echo no) !bang'
  ups s3 "/skill-builder note $N1" > "$HM/note.out"
  chk "[N1] note: the text lands in notes.md byte for byte, after a timestamp heading" 'python3 - "$NB/notes.md" "$N1" <<"PY"
import re,sys
t=open(sys.argv[1],encoding="utf-8",newline="").read()
m=re.fullmatch(r"\n### \d{4}-\d\d-\d\d \d\d:\d\d:\d\d\n(.*)\n", t, re.S)
assert m and m.group(1)==sys.argv[2], repr(t)
PY'
  chk "[N1] note: the model is told it was filed" 'grep -q "OBSERVE NOTE FILED" "$HM/note.out"'
  NL=$'line one "q"\n\tline two $x `y`'
  ups s3 "/lifehack-brain:skill-builder note $NL" >/dev/null
  chk "[N2] plugin-prefixed command, multi-line text, second note appended exactly" 'python3 - "$NB/notes.md" "$N1" "$NL" <<"PY"
import re,sys
t=open(sys.argv[1],encoding="utf-8",newline="").read()
parts=re.split(r"\n### \d{4}-\d\d-\d\d \d\d:\d\d:\d\d\n", t)
assert parts[0]=="" and parts[1]==sys.argv[2]+"\n" and parts[2]==sys.argv[3]+"\n", parts
PY'
  OUT="$(ups s5 "/skill-builder note anything")"
  chk "[N3] nothing observed: ONE line, nothing written" '[ "$(printf "%s" "$OUT" | python3 -c "import json,sys; print(json.load(sys.stdin)[\"hookSpecificOutput\"][\"additionalContext\"].count(\"\n\")+1)")" = 1 ] && printf "%s" "$OUT" | grep -q "NOTE NOT FILED: no skill is being observed" && [ ! -e "$HM/brain/drafts/builds/s5" ]'
  B4="$(wc -c < "$NB/notes.md")"; OUT="$(ups s3 "/skill-builder note   ")"
  chk "[N4] empty note: not filed" 'printf "%s" "$OUT" | grep -q "NOTE NOT FILED: the note was empty" && [ "$(wc -c < "$NB/notes.md")" = "$B4" ]'
  chk "[N5] a prompt that only mentions the command in prose is not a note" 'B=$(wc -c < "$NB/notes.md"); [ -z "$(ups s3 "please explain what /skill-builder note does")" ] && [ "$(wc -c < "$NB/notes.md")" = "$B" ]'
  OUT="$(ups s3 "/skill-builder wrap")"
  chk "[W1] wrap: names the skill, the notes file and the findings file" 'printf "%s" "$OUT" | grep -qF "skill audit; notes file $NB/notes.md; findings file $NB/findings.md"'
  chk "[W1] wrap with nothing observed says so" 'ups s6 "/skill-builder wrap" | grep -q "no skill is being observed in this window"'
  ups s3 "/skill-builder observe off" >/dev/null
  chk "[C3] observe off: switch cleared, status says not observing" '[ ! -f "$OD/observe-sess-s3.flag" ] && [ "$(CLAUDE_CODE_SESSION_ID=s3 bash "$FT" status)" = "not observing" ]'
  arm s7 audit >/dev/null; CLAUDE_CODE_SESSION_ID=s7 bash "$FT" set armed_at 1
  chk "[C4] an old switch has expired (TTL): status says not observing" '[ "$(CLAUDE_CODE_SESSION_ID=s7 bash "$FT" status)" = "not observing" ]'
  chk "[C5] the three old command files are gone (one command to remember)" '[ ! -e "$R/commands/skill-builder-observe.md" ] && [ ! -e "$R/commands/skill-builder-note.md" ] && [ ! -e "$R/commands/skill-builder-wrap.md" ]'
  SB="$R/.claude/skills/skill-builder/SKILL.md"
  chk "[C6] SKILL.md has a Modes section before the normal job, naming observe, note, wrap and the hook line" 'python3 - "$SB" <<"PY"
import sys
s=open(sys.argv[1],encoding="utf-8").read()
i=s.index("**Modes.**"); k=s.index("**Normal job**")
m=s[i:k]
assert s.index("## Procedure")<i<k
for w in ("OBSERVE ARMED","SKILL TO START","OBSERVE NOTE FILED","Noted.","OBSERVE WRAP","hook did not run","do NOT start the normal interview"):
    assert w in m, w
assert "skill-builder observe <skill>" in s.split("---")[1]
PY'
  echo "== NO MODE WORD: the normal job is untouched =="
  B4="$(wc -c < "$NB/notes.md")"
  chk "[M1] plain /skill-builder: no output, nothing armed" '[ -z "$(ups s8 "/skill-builder")" ] && [ ! -f "$OD/observe-sess-s8.flag" ]'
  chk "[M2] /skill-builder monthly-budget: no output, nothing armed, nothing filed" '[ -z "$(ups s8 "/skill-builder monthly-budget")" ] && [ -z "$(ups s8 "/lifehack-brain:skill-builder monthly-budget")" ] && [ ! -f "$OD/observe-sess-s8.flag" ] && [ "$(wc -c < "$NB/notes.md")" = "$B4" ]'
  chk "[M2] near-miss words (noted-things, observer, wrapper) are not modes" '[ -z "$(ups s8 "/skill-builder noted-things")" ] && [ -z "$(ups s8 "/skill-builder observer")" ] && [ -z "$(ups s8 "/skill-builder wrapper my routine")" ]'
  chk "[M3] the old hyphen forms do nothing now (observe, note, wrap)" 'arm s9 audit >/dev/null; B=$(wc -c < "$NB/notes.md"); [ -z "$(ups s9 "/skill-builder-observe audit")" ] && [ -z "$(ups s9 "/skill-builder-note hello")" ] && [ -z "$(ups s9 "/skill-builder-wrap")" ] && [ "$(wc -c < "$NB/notes.md")" = "$B" ]'
  chk "[M4] the plugin-prefixed forms work: observe arms, wrap answers" 'ups s10 "/lifehack-brain:skill-builder observe audit" | grep -q "OBSERVE ARMED: Observing audit" && [ -f "$OD/observe-sess-s10.flag" ] && ups s10 "/lifehack-brain:skill-builder wrap" | grep -qF "findings file $NB/findings.md"'
  chk "[M4] ... and observe off with the prefix clears it" 'ups s10 "/lifehack-brain:skill-builder observe off" >/dev/null; [ ! -f "$OD/observe-sess-s10.flag" ]'
}

echo "######## the real tree ########"
suite "$PLUG"
REAL_FAIL=$fail

echo; echo "######## failing-first: each check must FAIL on a broken copy ########"
variant() {   # variant <label> <path-under-plugin> <old> <new> <check-id that must fail>
  local lab="$1" rel="$2" old="$3" new="$4" want="$5" M="$T/mir-$1"
  mkdir -p "$M/system/hooks" "$M/system/tools" "$M/commands"
  for f in "$PLUG"/system/hooks/* "$PLUG"/system/tools/*; do ln -s "$f" "$M/system/${f#$PLUG/system/}"; done
  ln -s "$PLUG/shared" "$M/shared"; ln -s "$PLUG/.claude" "$M/.claude"; ln -s "$PLUG/system/parts" "$M/system/parts"; ln -s "$PLUG/system/register" "$M/system/register"
  for f in "$PLUG"/commands/*; do ln -s "$f" "$M/commands/"; done
  case "$rel" in .claude/skills/*) python3 - "$PLUG" "$M" "$rel" <<'PYM'
import os, sys
plug, m, rel = sys.argv[1:4]
sk = rel.split("/")[2]
os.remove(m + "/.claude")
chain = [".claude", ".claude/skills", ".claude/skills/" + sk]
for n, d in enumerate(chain):
    os.makedirs(m + "/" + d, exist_ok=True)
    for e in os.listdir(plug + "/" + d):
        if n + 1 < len(chain) and d + "/" + e == chain[n + 1]: continue
        os.symlink(plug + "/" + d + "/" + e, m + "/" + d + "/" + e)
PYM
  ;; esac
  rm -f "$M/$rel"; python3 - "$PLUG/$rel" "$M/$rel" "$old" "$new" <<'PY'
import sys
s = open(sys.argv[1], encoding="utf-8").read()
assert s.count(sys.argv[3]) == 1, "variant text must occur exactly once: %r (%d)" % (sys.argv[3], s.count(sys.argv[3]))
open(sys.argv[2], "w", encoding="utf-8").write(s.replace(sys.argv[3], sys.argv[4]))
PY
  chmod 755 "$M/$rel"
  local out; out="$( ( suite "$M" ) 2>&1 )"
  if printf '%s\n' "$out" | grep -q "FAIL  \[$want\]"; then ok "broken copy '$lab' is caught by [$want]"; else bad "broken copy '$lab' was NOT caught by [$want]"; fi
}
variant eot-always-launch   system/hooks/end_of_turn_checks.sh 'if [ -f "$OBSD/observe-sess-$SID.flag" ]; then' 'if mkdir -p "$OBSD"; then' U1
variant eot-no-skip         system/hooks/end_of_turn_checks.sh 'if [ -z "$_obs_run" ]; then' 'if true; then' A2
variant eot-waits           system/hooks/end_of_turn_checks.sh '"$SID" </dev/null >/dev/null 2>&1 &' '"$SID" </dev/null >/dev/null 2>&1' A1
variant rev-no-cap          system/tools/observe_review.sh '[ "$SHOWN" -lt 5 ]' '[ "$SHOWN" -lt 500 ]' R2
variant rev-no-findings     system/tools/observe_review.sh "printf -- '- [%s] %s %s\\n' \"\$(TS)\" \"\$tag\" \"\$rest\" >> \"\$FINDINGS\"" ':' R1
variant rev-no-failline     system/tools/observe_review.sh "printf 'reviewer did not run: %s\\n' \"\$1\" >> \"\$INBOX\"" ':' R4
variant rev-failline-repeats system/tools/observe_review.sh 'if [ ! -f "$FAILMARK" ]; then' 'if true; then' R4
variant rev-no-offset       system/tools/observe_review.sh '[ -n "$NEW_OFF" ] && bash "$FLAGTOOL" set offset "$NEW_OFF"' ':' R5
variant rev-no-step         system/tools/observe_review.sh 'if j.get("skill") == skill and not j.get("complete"):' 'if False:' R7
variant rev-no-notes        system/tools/observe_review.sh 'notes = "".join(rd(notes_f).splitlines(True)[-30:]) or "(no notes yet)"' 'notes = "(no notes yet)"' R6
variant ups-no-clear        system/hooks/observe_ups.sh 'os.replace(inbox, os.path.join(od, "inbox-%s.shown" % sid))' 'pass' I1
variant ups-no-sysmsg       system/hooks/observe_ups.sh 'out["systemMessage"] = ' 'out["note"] = ' I1
variant ups-no-cap          system/hooks/observe_ups.sh 'for i, l in enumerate(lines[:5], 1):' 'for i, l in enumerate(lines, 1):' I3
variant ups-mangles-note    system/hooks/observe_ups.sh '(time.strftime("%Y-%m-%d %H:%M:%S"), rest))' '(time.strftime("%Y-%m-%d %H:%M:%S"), rest.replace(chr(96), "").replace("$", "")))' N1
variant ups-quiet-path-slow system/hooks/observe_ups.sh '[ -n "$CMD" ] || [ -s "$INBOX" ] || exit 0' 'python3 -c pass; mkdir -p "$OD"' U3

variant ups-mode-optional   system/hooks/observe_ups.sh 'skill-builder[ \t]+(observe|note|wrap)(?:' 'skill-builder(?:[ \t]+(observe|note|wrap))?(?:' M1
variant ups-mode-no-boundary system/hooks/observe_ups.sh '(observe|note|wrap)(?:[ \t\r\n]+|$)"' '(observe|note|wrap)"' M2
variant ups-old-form-kept   system/hooks/observe_ups.sh 'skill-builder[ \t]+(observe|note|wrap)(?:' 'skill-builder[ \t-]+(observe|note|wrap)(?:' M3
variant ups-no-prefix       system/hooks/observe_ups.sh '^/(?:[A-Za-z0-9_-]+:)?skill-builder' '^/skill-builder' M4
variant skill-no-modes      .claude/skills/skill-builder/SKILL.md '**Modes.**' '**Mode list.**' C6

echo
echo "passed=$pass failed=$fail"
[ "$fail" -eq 0 ]
