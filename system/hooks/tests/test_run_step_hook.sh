#!/bin/sh
# test_run_step_hook.sh — the mover (spec run-pickup G2, invariants 1-3, 10).
# ALLOW/correct-move cases first, then the silent doors. Runs under sh.
# Run: sh system/hooks/tests/test_run_step_hook.sh  (exit 0 = all pass)
HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$HOOKS/run_step_hook.sh"
RUNNER="$HOOKS/../parts/stage_runner.py"
FIX="$HOOKS/tests/fixtures"
[ -f "$HOOK" ] || { echo "CANNOT RUN: no mover at $HOOK"; exit 1; }

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/mover.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

TAG='[RUN STEP — harness-injected, not user input]'

setup_card() {
  python3 - "$1" <<'PY'
import io, json, os, sys
td = sys.argv[1]
os.makedirs(os.path.join(td, "prompts"), exist_ok=True)
stages = []
for i, (sid, mode) in enumerate([("gather", "talk"), ("analyze", "talk"), ("finalize", "alone")], 1):
    io.open(os.path.join(td, "prompts", "%02d-%s.md" % (i, sid)), "w", encoding="utf-8").write(
        "Stage {{ID}} of {{TOTAL}} ({{MODE}}). Your code word: {{CODE}}. Write to {{OUT}}.\n")
    stages.append({"id": sid, "mode": mode,
                   "prompt": "prompts/%02d-%s.md" % (i, sid), "out": "out/%02d-%s.md" % (i, sid),
                   "checks": {"headings": ["## %s" % sid.title()], "min_words": 10, "code_word": True}})
json.dump({"skill": "moverspec", "stop_limit": 3, "stages": stages},
          io.open(os.path.join(td, "card.json"), "w", encoding="utf-8"))
PY
}

cnt=0
fresh_wd() { # a fresh run folder per test: a second start in an unfinished run's wd is refused
  cnt=`expr $cnt + 1`
  WD="$SANDBOX/w$cnt"; mkdir -p "$WD"
}
start_run() { # $1 wd: echoes "code rid"
  start_out=`python3 "$RUNNER" start --card "$SANDBOX/card.json" --workdir "$1" 2>&1`
  code=`printf '%s' "$start_out" | grep -o 'RUN-[0-9A-Z]\{6\}' | head -1`
  rid=`ls "$1/runs" | head -1`
  printf '%s %s' "$code" "$rid"
}

write_out() { # $1 rid $2 stage index (1-based) $3 stage id $4 code
  printf '## %s\n\nThe step work is written here in full, complete and checked.\n\nCode word: %s\n' "$3" "$4" \
    > "$WD/runs/$1/out/$(printf '%02d' "$2")-$3.md"
}

mkpayload() { # $1 fixture $2 cwd $3 prompt_id -> JSON on stdout
  python3 - "$1" "$2" "$3" <<'PY'
import io, json, sys
j = json.load(io.open(sys.argv[1], encoding="utf-8"))
j["cwd"] = sys.argv[2]
j["prompt_id"] = sys.argv[3]
sys.stdout.write(json.dumps(j))
PY
}

runhook() { # $1 payload -> sets HOUT and HRC
  HOUT=`printf '%s' "$1" | sh "$HOOK" 2>&1`; HRC=$?
}

persons() { # $1 rid: count of person events in its record
  grep -c '"event": "person"' "$WD/runs/$1/record.jsonl"
}

echo "correct moves (the person's typed /next and /back)"
setup_card "$SANDBOX"
fresh_wd; WD_RUN1="$WD"
set -- `start_run "$WD"`; CODE1="$1"; RID="$2"
# 1. /next on a finished step: TAG + move + mover.log
write_out "$RID" 1 Gather "$CODE1"
runhook "`mkpayload "$FIX/run_ups_next_live.json" "$WD" "mv-live-1"`"
[ "$HRC" -eq 0 ] && ok || bad "rc /next finished" "rc=$HRC"
case "$HOUT" in *"$TAG"*) ok ;; *) bad "tag /next finished" "$HOUT" ;; esac
grep -q '"person"' "$WD_RUN1/runs/$RID/record.jsonl" && ok || bad "person line" "none"
grep -q '"event": "pass"' "$WD_RUN1/runs/$RID/record.jsonl" && ok || bad "step actually advanced" "no pass event"
grep -q '^mv-live-1$' "$WD_RUN1/runs/$RID/mover.log" 2>/dev/null && ok || bad "mover.log" "$(cat "$WD_RUN1/runs/$RID/mover.log" 2>/dev/null)"
# 2. /back moves exactly one step back
fresh_wd; WD_BACK="$WD"
set -- `start_run "$WD"`; CODE2="$1"; RID2="$2"
write_out "$RID2" 1 Gather "$CODE2"
runhook "`mkpayload "$FIX/run_ups_next_live.json" "$WD" "mv-back-0"`"
CODEA=`printf '%s' "$HOUT" | grep -o 'RUN-[0-9A-Z]\{6\}' | head -1`
write_out "$RID2" 2 Analyze "$CODEA"
runhook "`mkpayload "$FIX/run_ups_back_live.json" "$WD" "mv-back-1"`"
[ "$HRC" -eq 0 ] && ok || bad "rc /back" "rc=$HRC out=$HOUT"
grep -q '"cmd": "back"' "$WD_BACK/runs/$RID2/record.jsonl" && ok || bad "back person line" "none"

echo "the handover is capped at 4000 characters"
fresh_wd
WD_CAP="$WD"
python3 - "$SANDBOX" <<'PY'
import io, json, os, sys
td = sys.argv[1]
os.makedirs(os.path.join(td, "prompts"), exist_ok=True)
body = "Filler line for the cap test. " * 400
# the MOVER prints the NEXT stage's prompt, so the long body belongs to stage 2
io.open(os.path.join(td, "prompts", "02-analyze.md"), "w", encoding="utf-8").write(
    "Stage {{ID}} of {{TOTAL}} ({{MODE}}). Your code word: {{CODE}}. Write to {{OUT}}.\n\n" + body)
for s in ("01-gather", "03-finalize"):
    io.open(os.path.join(td, "prompts", "%s.md" % s), "w", encoding="utf-8").write(
        "Stage {{ID}} of {{TOTAL}} ({{MODE}}). Your code word: {{CODE}}. Write to {{OUT}}.\n")
stages = []
for i, (sid, mode) in enumerate([("gather", "talk"), ("analyze", "talk"), ("finalize", "alone")], 1):
    stages.append({"id": sid, "mode": mode, "prompt": "prompts/%02d-%s.md" % (i, sid), "out": "out/%02d-%s.md" % (i, sid),
                   "checks": {"headings": ["## %s" % sid.title()], "min_words": 10, "code_word": True}})
json.dump({"skill": "capspec", "stop_limit": 3, "stages": stages}, io.open(os.path.join(td, "card2.json"), "w", encoding="utf-8"))
PY
start_out2=`python3 "$RUNNER" start --card "$SANDBOX/card2.json" --workdir "$WD_CAP" 2>&1`
code_cap2=`printf '%s' "$start_out2" | grep -o 'RUN-[0-9A-Z]\{6\}' | head -1`
rid_cap2=`ls "$WD_CAP/runs" | head -1`
printf '## Gather\n\nThe step work is written here in full, complete and checked.\n\nCode word: %s\n' "$code_cap2" > "$WD_CAP/runs/$rid_cap2/out/01-gather.md"
mkpayload "$FIX/run_ups_next_live.json" "$WD_CAP" "mv-cap-1" > "$SANDBOX/cap.json"
runhook "`cat "$SANDBOX/cap.json"`"
[ "$HRC" -eq 0 ] && ok || bad "rc capped handover" "rc=$HRC"
case "$HOUT" in
  *"full instructions in"*) ok ;;
  *) bad "cap note present" "output was ${#HOUT} chars, no cap note" ;;
esac
[ "${#HOUT}" -le 4200 ] && ok || bad "handover under cap" "${#HOUT} chars"

echo "runner failures still speak, exit 0"
# 3. /next on an UNFINISHED step: tagged line, exit 0
fresh_wd
set -- `start_run "$WD"`; RID3="$2"
runhook "`mkpayload "$FIX/run_ups_next_live.json" "$WD" "mv-nf-1"`"
[ "$HRC" -eq 0 ] && ok || bad "rc not-finished" "rc=$HRC"
case "$HOUT" in *"$TAG"*) ok ;; *) bad "tag not-finished" "$HOUT" ;; esac

echo "silent doors: not the person, not the command, no run"
# 4. peer /next: silent
runhook "`mkpayload "$FIX/run_ups_next_peer.json" "$WD" "mv-peer-1"`"
[ "$HRC" -eq 0 ] && [ -z "$HOUT" ] && ok || bad "peer /next silent" "rc=$HRC out=$HOUT"
# 5. task-notification /next: silent
runhook "`mkpayload "$FIX/run_ups_next_task_notification.json" "$WD" "mv-tn-1"`"
[ "$HRC" -eq 0 ] && [ -z "$HOUT" ] && ok || bad "notification /next silent" "rc=$HRC out=$HOUT"
# 6. '/next please': silent (exact match only)
mkpayload "$FIX/run_ups_next_live.json" "$WD" "x" | python3 -c 'import json,sys; j=json.load(sys.stdin); j["prompt"]="/next please"; sys.stdout.write(json.dumps(j))' > "$SANDBOX/p_please.json"
runhook "`cat "$SANDBOX/p_please.json"`"
[ "$HRC" -eq 0 ] && [ -z "$HOUT" ] && ok || bad "'/next please' silent" "rc=$HRC out=$HOUT"
# 7. no marker in cwd: silent
mkdir -p "$SANDBOX/empty"
runhook "`mkpayload "$FIX/run_ups_next_live.json" "$SANDBOX/empty" "mv-empty-1"`"
[ "$HRC" -eq 0 ] && [ -z "$HOUT" ] && ok || bad "no marker silent" "rc=$HRC out=$HOUT"
# 8. prompt without /next or /back: silent (sh prefilter)
mkpayload "$FIX/run_ups_next_live.json" "$WD" "x" | python3 -c 'import json,sys; j=json.load(sys.stdin); j["prompt"]="morning"; sys.stdout.write(json.dumps(j))' > "$SANDBOX/p_other.json"
runhook "`cat "$SANDBOX/p_other.json"`"
[ "$HRC" -eq 0 ] && [ -z "$HOUT" ] && ok || bad "no keyword silent" "rc=$HRC out=$HOUT"

echo "phase 4e fix 6: a payload missing prompt_id or cwd still speaks, exit 0"
mkpayload "$FIX/run_ups_next_live.json" "$WD" "mv-noid-1" > "$SANDBOX/p_noid.json"
python3 -c 'import json,sys; j=json.load(open(sys.argv[1])); j.pop("prompt_id", None); open(sys.argv[1],"w").write(json.dumps(j))' "$SANDBOX/p_noid.json"
runhook "`cat "$SANDBOX/p_noid.json"`"
[ "$HRC" -eq 0 ] && ok || bad "rc missing prompt_id" "rc=$HRC"
case "$HOUT" in
  *"$TAG"*) ok ;; *) bad "missing prompt_id tagged line" "rc=$HRC out=$HOUT" ;;
esac
mkpayload "$FIX/run_ups_next_live.json" "$WD" "mv-nocwd-1" > "$SANDBOX/p_nocwd.json"
python3 -c 'import json,sys; j=json.load(open(sys.argv[1])); j.pop("cwd", None); open(sys.argv[1],"w").write(json.dumps(j))' "$SANDBOX/p_nocwd.json"
runhook "`cat "$SANDBOX/p_nocwd.json"`"
[ "$HRC" -eq 0 ] && ok || bad "rc missing cwd" "rc=$HRC"
case "$HOUT" in
  *"$TAG"*) ok ;; *) bad "missing cwd tagged line" "rc=$HRC out=$HOUT" ;;
esac

echo "person lines only where the mover wrote them"
# 9. a peer /next must leave NO person line in the record
WD="$WD_RUN1"; cnt_before=`persons "$RID"`
runhook "`mkpayload "$FIX/run_ups_next_peer.json" "$WD" "mv-peer-2"`"
cnt_after=`persons "$RID"`
[ "$cnt_before" = "$cnt_after" ] && ok || bad "peer added a person line" "count was $cnt_before then $cnt_after"

echo "phase 4c fixes (failing-first plants)"
# 10. every person prompt is logged to person.log, even one that is not a step command
fresh_wd; WD_PLOG="$WD"
set -- `start_run "$WD"`; RID_P="$2"
n0=`persons "$RID_P"`
mkpayload "$FIX/run_ups_next_live.json" "$WD" "mv-morning-1" > "$SANDBOX/p_morning.json"
python3 -c 'import json,sys; j=json.load(open(sys.argv[1])); j["prompt"]="morning"; open(sys.argv[1],"w").write(json.dumps(j))' "$SANDBOX/p_morning.json"
runhook "`cat "$SANDBOX/p_morning.json"`"
[ "$HRC" -eq 0 ] && [ -z "$HOUT" ] && ok || bad "plain prompt silent" "rc=$HRC out=$HOUT"
case "`cat "$WD_PLOG/runs/$RID_P/person.log" 2>/dev/null`" in
  *"mv-morning-1"*) ok ;; *) bad "person.log written for a plain prompt" "$(cat "$WD_PLOG/runs/$RID_P/person.log" 2>/dev/null)" ;;
esac
[ "$n0" = "`persons "$RID_P"`" ] && ok || bad "plain prompt moved nothing" "record grew"
# 11. mover.log is written BEFORE person-turn: a repeat turn still leaves its line
mkpayload "$FIX/run_ups_next_live.json" "$WD" "mv-dup-1" > "$SANDBOX/p_dup.json"
runhook "`cat "$SANDBOX/p_dup.json"`"          # moves one step
mkpayload "$FIX/run_ups_next_live.json" "$WD" "mv-dup-1" > "$SANDBOX/p_dup.json"
runhook "`cat "$SANDBOX/p_dup.json"`"          # same turn again: person-turn refuses
c1=`grep -c '^mv-dup-1$' "$WD_PLOG/runs/$RID_P/mover.log" 2>/dev/null`
[ "$c1" = "2" ] && ok || bad "mover.log written before person-turn" "mover.log has $c1 mv-dup-1 lines"
# 12. a marker pointing outside its folder: the mover refuses and moves nothing
WD_OUT="$SANDBOX/wout"; mkdir -p "$WD_OUT"
OTHER="$SANDBOX/other-run"; mkdir -p "$OTHER"
printf '{"run_dir": "%s", "run_id": "x"}' "$OTHER" > "$WD_OUT/.stage-runner.json"
mkpayload "$FIX/run_ups_next_live.json" "$WD_OUT" "mv-out-1" > "$SANDBOX/p_out.json"
runhook "`cat "$SANDBOX/p_out.json"`"
case "$HOUT" in
  *"$TAG"*"outside"*) ok ;; *) bad "marker outside refused" "$HOUT" ;;
esac
# 13. an empty payload: one tagged line, nothing ran
HOUT=`printf '' | sh "$HOOK" 2>&1`; HRC=$?
case "$HOUT" in
  *"$TAG"*) ok ;; *) bad "empty payload tagged line" "rc=$HRC out=$HOUT" ;;
esac
# 14. the cap note names the stage prompt file
fresh_wd; WD_PFILE="$WD"
python3 - "$SANDBOX" <<'PY'
import io, json, os, sys
td = sys.argv[1]
os.makedirs(os.path.join(td, "prompts2"), exist_ok=True)
body = "Filler line for the cap test. " * 400
io.open(os.path.join(td, "prompts2", "02-analyze.md"), "w", encoding="utf-8").write(
    "Stage {{ID}} of {{TOTAL}} ({{MODE}}). Your code word: {{CODE}}. Write to {{OUT}}.\n\n" + body)
for s in ("01-gather", "03-finalize"):
    io.open(os.path.join(td, "prompts2", "%s.md" % s), "w", encoding="utf-8").write(
        "Stage {{ID}} of {{TOTAL}} ({{MODE}}). Your code word: {{CODE}}. Write to {{OUT}}.\n")
stages = []
for i, (sid, mode) in enumerate([("gather", "talk"), ("analyze", "talk"), ("finalize", "alone")], 1):
    stages.append({"id": sid, "mode": mode, "prompt": "prompts2/%02d-%s.md" % (i, sid),
                   "out": "out/%02d-%s.md" % (i, sid),
                   "checks": {"headings": ["## %s" % sid.title()], "min_words": 10, "code_word": True}})
json.dump({"skill": "pfilespec", "stop_limit": 3, "stages": stages},
          io.open(os.path.join(td, "card3.json"), "w", encoding="utf-8"))
PY
start_out3=`python3 "$RUNNER" start --card "$SANDBOX/card3.json" --workdir "$WD_PFILE" 2>&1`
code_p=`printf '%s' "$start_out3" | grep -o 'RUN-[0-9A-Z]\{6\}' | head -1`
rid_p=`ls "$WD_PFILE/runs" | head -1`
printf '## Gather\n\nThe step work is written here in full, complete and checked.\n\nCode word: %s\n' "$code_p" > "$WD_PFILE/runs/$rid_p/out/01-gather.md"
mkpayload "$FIX/run_ups_next_live.json" "$WD_PFILE" "mv-pfile-1" > "$SANDBOX/p_pfile.json"
runhook "`cat "$SANDBOX/p_pfile.json"`"
case "$HOUT" in
  *"02.prompt.md"*) ok ;; *) bad "cap note names the prompt file" "$HOUT" ;;
esac
# 15. the mover still works when lib/journal.sh is missing (A7: `.` must not end the script)
NOJ="$SANDBOX/nojournal"
mkdir -p "$NOJ/hooks"
cp "$HOOK" "$NOJ/hooks/"
cp -R "$HOOKS/lib" "$NOJ/hooks/lib"
rm -f "$NOJ/hooks/lib/journal.sh"
ln -s "$HOOKS/../parts" "$NOJ/parts"
WD_NOJ="$WD_PFILE"
mkpayload "$FIX/run_ups_next_live.json" "$WD_NOJ" "mv-nojournal-1" > "$SANDBOX/p_noj.json"
HOUT=`printf '%s' "$(cat "$SANDBOX/p_noj.json")" | sh "$NOJ/hooks/run_step_hook.sh" 2>&1`; HRC=$?
[ "$HRC" -eq 0 ] && ok || bad "no-journal rc" "rc=$HRC"
case "$HOUT" in *"$TAG"*) ok ;; *) bad "no-journal still moves" "$HOUT" ;; esac
grep -q '"event": "pass"' "$WD_NOJ/runs/$rid_p/record.jsonl" && ok || bad "no-journal moved the run" "no pass"

echo "code word survives a cut-off (long prompt + /back), first line carries path and word"
# Plant: stage 1's code word sits AFTER 4000 chars of filler, so a capped body can never show it.
fresh_wd
WD_CW="$WD"
python3 - "$SANDBOX" <<'PY'
import io, json, os, sys
td = sys.argv[1]; d = os.path.join(td, "cwcard"); os.makedirs(os.path.join(d, "prompts"), exist_ok=True)
filler = "Filler line for the code-word cut-off test. " * 150
for i, sid in enumerate(("gather", "analyze"), 1):
    io.open(os.path.join(d, "prompts", "%02d-%s.md" % (i, sid)), "w", encoding="utf-8").write(
        "Stage {{ID}}. Write to {{OUT}}.\n\n" + filler + "\nYour code word: {{CODE}}\n")
stages = [{"id": s, "mode": "talk", "prompt": "prompts/%02d-%s.md" % (i, s), "out": "out/%02d-%s.md" % (i, s),
           "checks": {"headings": ["## %s" % s.title()], "min_words": 10, "code_word": True}}
          for i, s in enumerate(("gather", "analyze"), 1)]
json.dump({"skill": "cwspec", "stop_limit": 3, "stages": stages}, io.open(os.path.join(d, "card.json"), "w", encoding="utf-8"))
PY
cw_start=`python3 "$RUNNER" start --card "$SANDBOX/cwcard/card.json" --workdir "$WD_CW" 2>&1`
cw1=`printf '%s' "$cw_start" | grep -o 'RUN-[0-9A-Z]\{6\}' | head -1`
cw_rid=`ls "$WD_CW/runs" | head -1`
printf '## Gather\n\nThe step work is written here in full, complete and checked.\n\nCode word: %s\n' "$cw1" > "$WD_CW/runs/$cw_rid/out/01-gather.md"
runhook "`mkpayload "$FIX/run_ups_next_live.json" "$WD_CW" "mv-cw-next"`"
runhook "`mkpayload "$FIX/run_ups_back_live.json" "$WD_CW" "mv-cw-back"`"
cw_first=`printf '%s\n' "$HOUT" | sed -n 2p`
cw_new=`printf '%s' "$cw_first" | grep -o 'RUN-[0-9A-Z]\{6\}' | head -1`
case "$cw_first" in "full prompt: "*"/stage/01.prompt.md; code word: RUN-"*) ok ;; *) bad "first line has path + word after /back" "$cw_first" ;; esac
[ -n "$cw_new" ] && [ "$cw_new" != "$cw1" ] && ok || bad "a FRESH word survives the cut" "new=$cw_new old=$cw1"
printf '## Gather\n\nThe step work is written here in full, complete and checked.\n\nCode word: %s\n' "$cw_new" > "$WD_CW/runs/$cw_rid/out/01-gather.md"
python3 "$RUNNER" check --workdir "$WD_CW" >/dev/null 2>&1 && ok || bad "the surfaced word is the one the runner accepts" "check refused $cw_new"
# FAILING FIRST: the pre-fix mover (capped body only) loses the word on the same plant.
if [ -f "$HOOKS/run_step_hook.sh.bak-20261124-cap" ]; then
  fresh_wd; WD_OLD="$WD"
  o_start=`python3 "$RUNNER" start --card "$SANDBOX/cwcard/card.json" --workdir "$WD_OLD" 2>&1`
  o1=`printf '%s' "$o_start" | grep -o 'RUN-[0-9A-Z]\{6\}' | head -1`; o_rid=`ls "$WD_OLD/runs" | head -1`
  printf '## Gather\n\nThe step work is written here in full, complete and checked.\n\nCode word: %s\n' "$o1" > "$WD_OLD/runs/$o_rid/out/01-gather.md"
  mkpayload "$FIX/run_ups_next_live.json" "$WD_OLD" "mv-old-next" | sh "$HOOKS/run_step_hook.sh.bak-20261124-cap" >/dev/null 2>&1
  OOUT=`mkpayload "$FIX/run_ups_back_live.json" "$WD_OLD" "mv-old-back" | sh "$HOOKS/run_step_hook.sh.bak-20261124-cap" 2>&1`
  printf '%s' "$OOUT" | grep -q 'RUN-[0-9A-Z]\{6\}' && bad "failing-first: old mover should LOSE the word" "it kept it" || ok
else
  echo "  NOTE: failing-first part skipped (no pre-fix copy beside the hook; it was seen failing on 2026-11-24)"
fi

echo "mover suite: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
