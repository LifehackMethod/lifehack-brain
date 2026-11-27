#!/bin/bash
# test_waves.sh -- round 2c (replaces test_spec_write_chain.sh): CODE HANDS OVER THE LIST, THE AI RUNS THE WAVES IN THE TURN, CODE CHECKS
# THE RECEIPTS. Through the registered entry points only: the mover (run_step_hook.sh, UserPromptSubmit) hands the list over, the Stop
# hook (end_of_turn_checks.sh) checks the receipts, and `sb_spec.py apply` is the writer's one command. No model call at all: the
# tests play the AI's part by writing the output files the list names. ALLOW cases first; then every check is shown FAILING on a
# deliberately broken copy (a copy of the plugin pieces with ONE edit).
# Run: bash system/hooks/tests/test_waves.sh   (SPEC_PLUG=<plugin root> points it at a copy; WAVES_NOBROKEN=1 skips the broken copies)
PLUG="${SPEC_PLUG:-$(cd "$(dirname "$0")/../../.." && pwd -P)}"
T="$(cd "$(mktemp -d)" && pwd -P)"; trap 'rm -rf "$T"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); printf '   ok   %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL  %s\n' "$1"; }
chk() { if eval "$2"; then ok "$1"; else bad "$1  <<$2>>"; fi; }

suite() {   # suite <plugin root under test> [spaced]: spaced = the notes folder has a space in its path, like the owner's "My Drive"
  local R="$1" HM BR; HM="$(mktemp -d "$T/hm.XXXXXX")"; BR="$HM/brain"; [ "$2" = spaced ] && BR="$HM/My Drive/brain"
  export HOME="$HM" LIFEHACK_ROOT="$BR"; mkdir -p "$BR" "$HM/elsewhere"; unset CLAUDE_CODE_SESSION_ID
  local H="$R/system/hooks" SID="sess-waves-0001" OD="$HM/.claude/run/observe" OUTSIDE="$HM/elsewhere"
  local MOVER="$H/run_step_hook.sh" EOT="$H/end_of_turn_checks.sh" n=0
  mover() { n=$((n+1)); python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"prompt_id":sys.argv[3],"cwd":sys.argv[4],"hook_event_name":"UserPromptSubmit","prompt":sys.argv[2],"transcript_path":sys.argv[5]}))' "$1" "$2" "$3" "$4" "${5:-/x}" | sh "$MOVER" 2>&1; }
  stopj() { python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"prompt_id":sys.argv[2],"hook_event_name":"Stop","stop_hook_active":False,"last_assistant_message":"ok","cwd":"/x","transcript_path":sys.argv[3]}))' "$1" "$2" "${3:-/x}"; }
  stop() { stopj "$SID" "$1" "$2" | bash "$EOT" >/dev/null 2>&1; }
  # a transcript as the window would hold it: the person's prompt, then the tool calls the AI made (every job of the turn, except the ones named)
  tx() { python3 - "$1" "$2" "$3" <<'PY'
import json, os, sys
td, out, skip = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
notoken = os.environ.get("TXNOTOKEN", "")
rec = json.load(open(td + "/turn.json")); blocks = []
for j in rec["jobs"]:
    if j["id"] in skip: continue
    blocks.append({"type": "tool_use", "name": "Agent", "input": {"model": j["model"], "prompt": "Ask three questions of your own." if j["id"] == notoken else j["prompt"] + " (Context: a beginner.)"}} if j["kind"] == "agent"
                  else {"type": "tool_use", "name": "Bash", "input": {"command": j["cmd"]}})
with open(out, "w") as f:
    f.write(json.dumps({"type": "user", "message": {"role": "user", "content": "an answer"}}) + "\n")
    f.write(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": blocks}}) + "\n")
PY
  }
  jf() { python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(eval(sys.argv[2]))" "$1" "$2"; }
  local WD="$BR/drafts/builds/demo-skill"

  echo "== START: a fresh run, nothing to run on the first screen =="
  OUT="$(mover "$SID" "/skill-builder demo-skill" pstart "$OUTSIDE")"
  local RUN; RUN="$WD/runs/$(ls "$WD/runs" | head -1)"
  chk "[S1] the first screen of step 1 has no wave list and demands no writer" '! printf "%s" "$OUT" | grep -q "WAVES FOR THIS TURN" && ! printf "%s" "$OUT" | grep -q "saving your answers"'
  chk "[S2] the visit to step 1 is logged in the run folder" 'grep -q "^1	" "$RUN/waves/visits.log"'

  echo "== ANSWER: the person has just answered =="
  OUT="$(mover "$SID" "I want a skill that checks my monthly grocery spend against the Marigold-42 envelope" pans1 "$OUTSIDE")"
  local TD="$RUN/waves/pans1"
  chk "[A1] the list names the fixed first line the AI must print" 'printf "%s" "$OUT" | grep -qF "1. Your reply'"'"'s FIRST line, exactly: saving your answers and running checks…"'
  chk "[A2] wave 1 is the writer (haiku) beside the back-room helpers; the checkers and the questioner come in later waves, in order" 'a=$(printf "%s" "$OUT" | grep -n "^  • writer — " | head -1 | cut -d: -f1); b=$(printf "%s" "$OUT" | grep -n "^  • save-check — " | head -1 | cut -d: -f1); c=$(printf "%s" "$OUT" | grep -n "^  • questioner — " | head -1 | cut -d: -f1); [ -n "$a" ] && [ "$a" -lt "$b" ] && [ "$b" -lt "$c" ]'
  chk "[A3] each agent job names its model tier and its output file, the list is one line per helper, and the brief is a code-written file in the run folder" 'printf "%s" "$OUT" | grep -q "Agent, model haiku (small tier) — writes writer.md" && printf "%s" "$OUT" | grep -q "turn.s folder: $TD" && printf "%s" "$OUT" | grep -F "$TD/briefs/save-check.md" | grep -q "and do exactly what it says. \[" && grep -q "checker-save.md in full" "$TD/briefs/save-check.md"'
  chk "[A3b] the harness, research and size helpers wait for an outcome and the list says so loudly" '! printf "%s" "$OUT" | grep -q "^  • harness-search — " && printf "%s" "$OUT" | grep -q "NOT RUN YET: .outcome. is not written yet"'
  chk "[A4] the person's words reach the helpers by FILE, verbatim (code wrote it): the prompt carries no summary of them" '[ -f "$TD/person.md" ] && grep -q "Marigold-42 envelope" "$TD/person.md" && ! printf "%s" "$OUT" | grep -q "Marigold"'
  chk "[A5] the writer's whole input (brief, spec, packet, the person's words) was written by code" '[ -s "$TD/writer-input.md" ] && grep -q "Marigold-42" "$TD/writer-input.md" && ! grep -q "everything below this line is for the tester" "$TD/writer-input.md"'
  chk "[A6] questions come only from the questioner file" 'printf "%s" "$OUT" | grep -q "numbered questions come ONLY from questions.md in the turn.s folder"'
  chk "[A7] nothing was written into the folder of the window itself" '[ -z "$(ls -A "$OUTSIDE")" ]'
  chk "[A8] the receipt list for the turn and the Stop pointer exist" '[ -f "$TD/turn.json" ] && [ -f "$OD/spec-wave-$SID.json" ]'
  OUT2="$(mover "$SID" "/explain" pcmd1 "$OUTSIDE")"
  chk "[A9] a slash command that is not /next or /back gets no answer list" '! printf "%s" "$OUT2" | grep -q "WAVES FOR THIS TURN"'
  OUT2="$(mover "$SID" "/next" pnext0 "$OUTSIDE")"
  chk "[A10] a refused /next (step 1's file is not written) hands over no list" '! printf "%s" "$OUT2" | grep -q "WAVES FOR THIS TURN"'

  echo "== STOP: the receipt check =="
  stop pans1
  local WARN="$RUN/waves/receipt-warn.txt"
  chk "[R1] nothing was written for the turn: the Stop check names every missing job in a one-shot warning" '[ -s "$WARN" ] && grep -q "writer" "$WARN" && grep -q "save-check" "$WARN" && grep -q "questioner" "$WARN"'
  chk "[R2] the check is logged once, with the turn id" '[ "$(grep -c "^pans1	" "$RUN/waves/receipts.log")" = 1 ]'
  stop pans1
  chk "[R2b] a second Stop of the same turn does not log it again" '[ "$(grep -c "^pans1	" "$RUN/waves/receipts.log")" = 1 ]'
  OUT="$(mover "$SID" "the Kestrel card went over 310 once" pans2 "$OUTSIDE")"
  local L1 L2; L1="$(printf "%s\n" "$OUT" | grep -n "^1. Your reply's FIRST line" | head -1 | cut -d: -f1)"; L2="$(printf "%s\n" "$OUT" | grep -n "^2. RECEIPT CHECK FAILED LAST TURN" | head -1 | cut -d: -f1)"
  chk "[R3] the next turn says it loudly as the line right AFTER the fixed first line (explicit order)" '[ -n "$L1" ] && [ -n "$L2" ] && [ "$L2" = "$((L1+1))" ]'
  chk "[R4] and says it once: the warning is consumed" '[ ! -e "$WARN" ]'
  # the AI plays its part for turn pans2: every file the list names, fresh
  local TD2="$RUN/waves/pans2"
  printf 'SAID: the Kestrel card went over 310 once\nEND-WRITE\n' > "$TD2/writer.md"
  local CMD; CMD="$(sed -n 's/.*report the line it prints: \(python3 .*\) It applies your records.*/\1/p' "$RUN/waves/pans2/briefs/writer.md" | head -1)"
  chk "[R5] the writer's one command is in the list, with the run folder path" '[ -n "$CMD" ] && printf "%s" "$CMD" | grep -q "$TD2/writer.md" && printf "%s" "$CMD" | grep -q "$WD"'
  eval "$CMD" > "$HM/apply.out" 2>&1
  chk "[R6] running it applies the records by code and writes the receipt (only apply writes it; R9 shows a hand-written one is refused without the helper call)" 'grep -q "^APPLIED" "$HM/apply.out" && grep -q "^APPLIED" "$TD2/writer.md.applied" && grep -q "Kestrel card went over 310" "$WD/notes.md"'
  python3 - "$TD2" <<'PY'
import json, os, sys
td = sys.argv[1]; rec = json.load(open(os.path.join(td, "turn.json")))
for j in rec["jobs"]:
    p = os.path.join(td, j["receipt"])
    if not os.path.exists(p):
        open(p, "w").write("ok\n")
PY
  tx "$TD2" "$HM/tx2.jsonl" ""; stop pans2 "$HM/tx2.jsonl"
  chk "[R7] every receipt present: no warning is written" '[ ! -e "$WARN" ] && grep -q "ALL RECEIPTS PRESENT" "$RUN/waves/receipts.log"'
  OUT="$(mover "$SID" "one more thing" pans3 "$OUTSIDE")"
  # stale: the files of the turn before are in an earlier turn's folder; this turn's are old on disk
  local TD3="$RUN/waves/pans3"
  python3 - "$TD3" <<'PY'
import json, os, sys, time
td = sys.argv[1]; rec = json.load(open(os.path.join(td, "turn.json")))
for j in rec["jobs"]:
    p = os.path.join(td, j["receipt"])
    open(p, "w").write("APPLIED spec=0 packet=0\n" if p.endswith(".applied") else "ok\n")
    old = time.time() - 7200; os.utime(p, (old, old))
PY
  stop pans3
  chk "[R8] files that are older than the turn (stale) never pass: every job is named missing" '[ -s "$WARN" ] && [ "$(grep -o "no output file for this turn" "$WARN" | wc -l | tr -d " ")" -ge 3 ]'
  rm -f "$WARN"
  # proof that a helper ran: every file is fresh, but the AI wrote save-check.md itself (no Agent call for it in the transcript)
  OUT="$(mover "$SID" "one more answer" pans4 "$OUTSIDE")"; local TD4="$RUN/waves/pans4"
  python3 - "$TD4" <<'PY'
import json, os, sys
td = sys.argv[1]; rec = json.load(open(os.path.join(td, "turn.json")))
for j in rec["jobs"]:
    open(os.path.join(td, j["receipt"]), "w").write("APPLIED spec=3 packet=2 (skipped 0) rejected=0\n" if j["receipt"].endswith(".applied") else "ok\n")
PY
  tx "$TD4" "$HM/tx4.jsonl" "save-check"; stop pans4 "$HM/tx4.jsonl"
  chk "[R9] every file exists but save-check has no helper call in the transcript: the Stop check names it (a file the AI wrote is not a helper's)" '[ -s "$WARN" ] && grep -q "save-check" "$WARN" && grep -q "no helper call" "$WARN" && ! grep -q "wave 1, writer" "$WARN"'
  rm -f "$WARN"
  OUT="$(mover "$SID" "and a last one" pans5 "$OUTSIDE")"; local TD5="$RUN/waves/pans5"
  python3 - "$TD5" <<'PY'
import json, os, sys
td = sys.argv[1]; rec = json.load(open(os.path.join(td, "turn.json")))
for j in rec["jobs"]:
    open(os.path.join(td, j["receipt"]), "w").write("APPLIED spec=3 packet=2 (skipped 0) rejected=0\n" if j["receipt"].endswith(".applied") else "ok\n")
PY
  tx "$TD5" "$HM/tx5.jsonl" ""; stop pans5 "$HM/tx5.jsonl"
  chk "[R10] the same turn with every helper call in the transcript: all receipts present, no warning" '[ ! -e "$WARN" ] && tail -1 "$RUN/waves/receipts.log" | grep -q "ALL RECEIPTS PRESENT"'

  # a files-only check (transcript unreadable) is shown on the next turn; questions after a FAILED save are warned about; L25 line
  OUT="$(mover "$SID" "sixth answer" pans6 "$OUTSIDE")"; local TD6="$RUN/waves/pans6"
  chk "[L1] every list carries the one-line rule for a typed /next or /back" 'printf "%s" "$OUT" | grep -q "If the person types /next or /back, start no further waves; say in one line what is still running."'
  python3 - "$TD6" <<'PY'
import json, os, sys
td = sys.argv[1]; rec = json.load(open(os.path.join(td, "turn.json")))
for j in rec["jobs"]:
    open(os.path.join(td, j["receipt"]), "w").write("APPLIED spec=1 packet=1 (skipped 0) rejected=0\n" if j["receipt"].endswith(".applied") else "ok\n")
PY
  stop pans6 "$HM/no-such-transcript.jsonl"
  OUT="$(mover "$SID" "seventh answer" pans7 "$OUTSIDE")"
  chk "[R11] a files-only check (transcript unreadable) is SHOWN on the next turn as a RECEIPT NOTE, not only logged" 'printf "%s" "$OUT" | grep -q "RECEIPT NOTE: .*files only" && ! printf "%s" "$OUT" | grep -q "RECEIPT CHECK FAILED"'
  local TD7="$RUN/waves/pans7"
  python3 - "$TD7" <<'PY'
import json, os, sys
td = sys.argv[1]; rec = json.load(open(os.path.join(td, "turn.json")))
for j in rec["jobs"]:
    open(os.path.join(td, j["receipt"]), "w").write("FAILED: 2 record(s) rejected, none could be applied\n" if j["receipt"].endswith(".applied") else "ok\n")
PY
  tx "$TD7" "$HM/tx7.jsonl" ""; stop pans7 "$HM/tx7.jsonl"
  OUT="$(mover "$SID" "eighth answer" pans8 "$OUTSIDE")"
  chk "[R12] questions made after a FAILED save: the next turn warns loudly" 'printf "%s" "$OUT" | grep -q "questions were made although the save did not apply"'
  local TD8="$RUN/waves/pans8"
  python3 - "$TD8" <<'PY'
import json, os, sys, time
td = sys.argv[1]; rec = json.load(open(os.path.join(td, "turn.json")))
for j in rec["jobs"]:
    if j["id"] != "questioner":
        open(os.path.join(td, j["receipt"]), "w").write("APPLIED spec=1 packet=1 (skipped 0) rejected=0\n" if j["receipt"].endswith(".applied") else "ok\n")
time.sleep(0.05); open(os.path.join(td, "questions.md"), "w").write("1. q\nQUESTIONS-END\n")
PY
  # the questioner's call placed BEFORE the writer's in the transcript
  python3 - "$TD8" "$HM/tx8.jsonl" <<'PY'
import json, sys
td, out = sys.argv[1:3]; rec = json.load(open(td + "/turn.json")); jobs = {j["id"]: j for j in rec["jobs"]}
order = ["questioner", "writer"] + [i for i in jobs if i not in ("questioner", "writer")]
blocks = [{"type": "tool_use", "name": "Agent", "input": {"model": jobs[i]["model"], "prompt": jobs[i]["prompt"]}} if jobs[i]["kind"] == "agent"
          else {"type": "tool_use", "name": "Bash", "input": {"command": jobs[i]["cmd"]}} for i in order]
open(out, "w").write(json.dumps({"type": "user", "message": {"role": "user", "content": "an answer"}}) + "\n"
                     + json.dumps({"type": "assistant", "message": {"role": "assistant", "content": blocks}}) + "\n")
PY
  stop pans8 "$HM/tx8.jsonl"
  OUT="$(mover "$SID" "ninth answer" pans9 "$OUTSIDE")"
  chk "[R13] the questioner started before the writer (transcript order): the next turn warns" 'printf "%s" "$OUT" | grep -q "questioner was started before the writer"'
  rm -f "$RUN/waves/receipt-warn.txt"

  OUT="$(mover "$SID" "a call without the token" pans5b "$OUTSIDE")"; local TD5b="$RUN/waves/pans5b"
  python3 - "$TD5b" <<'PY'
import json, os, sys
td = sys.argv[1]; rec = json.load(open(os.path.join(td, "turn.json")))
for j in rec["jobs"]:
    open(os.path.join(td, j["receipt"]), "w").write("APPLIED spec=1 packet=1 (skipped 0) rejected=0\n" if j["receipt"].endswith(".applied") else "ok\n")
PY
  TXNOTOKEN=questioner tx "$TD5b" "$HM/tx5b.jsonl" ""; stop pans5b "$HM/tx5b.jsonl"
  chk "[R10b] an Agent call whose prompt lacks the job's token does not count (the AI wrote its own); extra context on the others is fine" '[ -s "$WARN" ] && grep -q "questioner" "$WARN" && grep -q "token" "$WARN" && ! grep -q "writer" "$WARN"'
  rm -f "$WARN"

  echo "== START moments: the /next handover =="
  local CU="$HM/design"; mkdir -p "$CU/out"
  python3 - "$CU" <<'PY'
import os, sys
w = " ".join(["word"] * 90); d = sys.argv[1]
open(os.path.join(d, "out/step-1.md"), "w").write("## Outcome\n%s\n\n## Harness check\nok\n\n## Size sense\nsmall\n\nCode word: x\n" % w)
open(os.path.join(d, "out/step-2.md"), "w").write("## Steps draft\n%s\n\n## Step count\n6, a skill.\n" % w)
open(os.path.join(d, "out/step-3.md"), "w").write("## Walked steps\n%s\n\n## Step count\n6, a skill.\n" % w)
PY
  mkdir -p "$CU/scratchpad"; printf '# steps\n1. read the receipts folder\n2. sort by date\n' > "$CU/scratchpad/steps-draft.md"
  local CS="sess-waves-0002"
  mover "$CS" "/skill-builder catch-up 3 $CU" pcu0 "$OUTSIDE" > /dev/null
  mover "$CS" "/next" pcu1 "$OUTSIDE" > /dev/null; mover "$CS" "/next" pcu2 "$OUTSIDE" > /dev/null
  OUT="$(mover "$CS" "/next" pcu3 "$OUTSIDE")"
  chk "[H1] /next into step 4: the handover is followed by the start list (a draft for every agreed step) with its own fixed first line" 'printf "%s" "$OUT" | grep -q "RUN-" && printf "%s" "$OUT" | grep -qF "1. Your reply'"'"'s FIRST line, exactly: running checks…" && printf "%s" "$OUT" | grep -q "^  • step-drafter — "'
  chk "[H2] a start list has no writer and no demand to save answers" '! printf "%s" "$OUT" | grep -q "^  • writer — " && ! printf "%s" "$OUT" | grep -q "saving your answers"'
  OUT="$(mover "$CS" "/next" pcu4 "$OUTSIDE")"
  chk "[H3] /next into step 5 (step 4 skipped by the person): the spec is brought up to date and checked before the questions, in that order" 'a=$(printf "%s" "$OUT" | grep -n "^  • spec-updater-a — " | cut -d: -f1); b=$(printf "%s" "$OUT" | grep -n "^  • spec-check-a — " | cut -d: -f1); c=$(printf "%s" "$OUT" | grep -n "^  • questioner — " | cut -d: -f1); [ -n "$a" ] && [ "$a" -lt "$b" ] && [ "$b" -lt "$c" ]'
  chk "[H4] each helper of the start list names its listed model (spec update and its check: sonnet)" 'printf "%s" "$OUT" | grep "^  • spec-updater-a — " | grep -q "model sonnet" && printf "%s" "$OUT" | grep "^  • spec-check-a — " | grep -q "model sonnet"'
  local CRUN="$CU/runs/$(ls "$CU/runs" | head -1)"
  chk "[H5] its files go to the run folder, named by the turn id" '[ -f "$CRUN/waves/pcu4/turn.json" ] && [ -f "$CRUN/waves/visits.log" ]'
  chk "[H5b] step 5's start list is a long chain: it tells the person to press Esc then /next" 'printf "%s" "$OUT" | grep -q "press Esc, then type /next, to move on now"'
  OUT="$(mover "$CS" "a plain answer in step 5" pcu5 "$OUTSIDE")"
  chk "[H6a] a step-5 answer carries the long-chain hint and, with no outcome written, the loud NOT RUN YET line" 'printf "%s" "$OUT" | grep -q "press Esc, then type /next" && printf "%s" "$OUT" | grep -q "NOT RUN YET: .outcome. is not written yet"'
  chk "[H6] before the 4.0a check has a file, the reviewers are held back by code, loudly" 'printf "%s" "$OUT" | grep -q "HELD BACK BY CODE: reviewer-screens" && ! printf "%s" "$OUT" | grep -q "^  • reviewer-screens — "'
  mkdir -p "$CRUN/waves/pcu4"; printf 'checked\n' > "$CRUN/waves/pcu4/spec-update-checked.md"
  OUT="$(mover "$CS" "decide now: keep it simple" pcu6 "$OUTSIDE")"
  chk "[H7] once it has a file, the five-angle check is handed over in order: reviewers, research pass, proposer, findings check" 'a=$(printf "%s" "$OUT" | grep -n "^  • reviewer-screens — " | cut -d: -f1); b=$(printf "%s" "$OUT" | grep -n "^  • research-pass — " | cut -d: -f1); c=$(printf "%s" "$OUT" | grep -n "^  • proposer — " | cut -d: -f1); d=$(printf "%s" "$OUT" | grep -n "^  • tensions-check — " | cut -d: -f1); [ -n "$a" ] && [ "$a" -lt "$b" ] && [ "$b" -lt "$c" ] && [ "$c" -lt "$d" ]'

  echo "== no run, no list; a failed table is one plain line =="
  OUT="$(mover "sess-nothing" "hello there" pnone "$OUTSIDE")"
  chk "[N1] no live run: a plain prompt prints nothing" '[ -z "$OUT" ]'
  mv "$R/.claude/skills/skill-builder/waves.json" "$R/.claude/skills/skill-builder/waves.json.off"
  OUT="$(mover "$CS" "an answer while the table is gone" pbroken "$OUTSIDE")"
  mv "$R/.claude/skills/skill-builder/waves.json.off" "$R/.claude/skills/skill-builder/waves.json"
  chk "[N2] a missing wave table is one plain WAVE LIST UNAVAILABLE line, never silence" 'printf "%s" "$OUT" | grep -q "WAVE LIST UNAVAILABLE" && printf "%s" "$OUT" | grep -q "RUN: step 5"'
}

echo "################ REAL TREE ($PLUG)"
suite "$PLUG"
echo "################ SPACED NOTES FOLDER (the owner's real one has 'My Drive' in it)"
suite "$PLUG" spaced
echo "passed=$pass failed=$fail"
REAL_FAIL=$fail
if [ -z "$WAVES_NOBROKEN" ] && [ -z "${SPEC_PLUG:-}" ]; then
  echo "== BROKEN COPIES: each check must FAIL on a copy with one edit =="
  broken() {   # broken <name> <file under plugin> <old> <new> <check id that must fail>
    local C="$T/br-$1"; mkdir -p "$C/.claude/skills"; rsync -a "$PLUG/system" "$PLUG/shared" "$C/"; rsync -a "$PLUG/.claude/skills/skill-builder" "$C/.claude/skills/"
    python3 - "$C/$2" "$3" "$4" <<'PY'
import sys
p, old, new = sys.argv[1:4]
s = open(p, encoding="utf-8").read()
assert old in s, "break marker missing: " + old
open(p, "w", encoding="utf-8").write(s.replace(old, new))
PY
    [ $? = 0 ] || { bad "[broken $1] could not break the copy"; return; }
    local o; o="$(WAVES_NOBROKEN=1 SPEC_PLUG="$C" bash "$0" 2>&1)"
    if printf '%s\n' "$o" | grep -q "FAIL  \[$5\]"; then ok "[broken $1] the copy fails $5"; else bad "[broken $1] $5 did NOT fail on the broken copy"; fi
  }
  broken no-first-line system/hooks/lib/sb_waves.py 'lines.append("1. Your reply'"'"'s FIRST line, exactly: %s" % (table.get("screen") or {}).get(moment, ""))' 'lines.append("1. Say something.")' A1
  broken no-receipt-check system/hooks/lib/sb_spec.py '        sb_waves.check(sid, tp)   # never raises' '        pass   # never raises' R1
  broken stale-passes system/hooks/lib/sb_waves.py 'os.path.getmtime(p) >= rec["t"] - SLACK' 'True' R8
  broken warn-not-said system/hooks/lib/sb_waves.py '        warn_line = ("RECEIPT CHECK FAILED LAST TURN' '        warn = ""; warn_line = ("RECEIPT CHECK FAILED LAST TURN' R3
  broken warn-not-after-first-line system/hooks/lib/sb_waves.py 'lines.append("2. " + warn_line + " Put it as the line right AFTER that first line.")' 'lines.insert(0, "2. " + warn_line)' R3
  broken no-start-list system/hooks/run_step_hook.sh 'if q.returncode == 0 and sb_start and sb_mode != "other":' 'if False:' H1
  broken no-answer-list system/hooks/lib/sb_start.py 'out += waves_lines(stage_runner, hooks, a[0], a[1], sid, pid, "answer", prompt, tp)' 'pass' A1
  broken writer-at-start .claude/skills/skill-builder/waves.json '"start": [],
      "answer": [
        {
          "label": "save, and start the back-room work"' '"start": [{"label": "save", "jobs": ["writer"]}],
      "answer": [
        {
          "label": "save, and start the back-room work"' S1
  broken no-reviewer-gate system/hooks/lib/sb_waves.py '                held.append((jid, "%s has no output yet" % d))' '                continue' H6
  broken no-proof system/hooks/lib/sb_waves.py '    if calls is not None:   # the file is not enough' '    if False:   # the file is not enough' R9
  broken unquoted-paths system/hooks/lib/sb_waves.py 'return (shlex.quote(v) if v is not None else m.group(0)) + tail' 'return (v if v is not None else m.group(0)) + tail' R6
  broken no-order-check system/hooks/lib/sb_waves.py '        op = _order_problem(td, rec, calls)' '        op = ""' R12
  broken note-hidden system/hooks/lib/sb_waves.py '        elif note:' '        elif False:' R11
  broken no-l25-line system/hooks/lib/sb_waves.py '        lines.append("If the person types /next or /back, start no further waves; say in one line what is still running.")' '        pass' L1
  broken no-token-check system/hooks/lib/sb_waves.py 'if n in ("Agent", "Task") and job.get("token") and job["token"] in str(i.get("prompt", ""))]' 'if n in ("Agent", "Task")]' R10b
  broken brief-not-written system/hooks/lib/sb_waves.py '    with open(bp, "w", encoding="utf-8") as f:
        f.write("# Brief for' '    with open(os.devnull, "w", encoding="utf-8") as f:
        f.write("# Brief for' A3
  broken forgeable-receipt system/hooks/lib/sb_spec.py '        _write_atomic(reply_file + ".applied", res + "\n")' '        pass' R6
  broken summary-allowed system/hooks/lib/sb_waves.py 'f.write("The person'"'"'s words this turn, verbatim:\n\n%s\n" % prompt)' 'f.write("The person'"'"'s words this turn, verbatim:\n\n%s\n" % "(summary)")' A4
  echo "passed=$pass failed=$fail"
  [ "$fail" = 0 ]
else
  [ "$REAL_FAIL" = 0 ]
fi
