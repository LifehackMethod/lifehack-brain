#!/bin/sh
# test_guard_run_commands.sh — the runner-command guard (spec run-pickup G3, invariant 3).
# ALLOW cases first; trigger strings are assembled from FRAGMENTS so the registered guard can
# never block this suite's own commands (hook SOP trap 2). Runs under sh.
# Run: sh system/hooks/tests/test_guard_run_commands.sh  (exit 0 = all pass)
HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$HOOKS/guard_run_commands.sh"
RUNNER="$HOOKS/../parts/stage_runner.py"
[ -f "$HOOK" ] || { echo "CANNOT RUN: no guard at $HOOK"; exit 1; }

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/guardrun.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

# fragments: the guarded subcommand names never appear whole in this file
PT1='person-'; PT2='turn'
ADV='ad''vance'; BCK='ba''ck'

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
json.dump({"skill": "guardspec", "stop_limit": 3, "stages": stages},
          io.open(os.path.join(td, "card.json"), "w", encoding="utf-8"))
PY
}

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
deny() { # $1 label $2 command $3 cwd: expect exit 2 + all four deny parts on stderr
  runguard "$2" "$3"
  if [ "$GRC" -ne 2 ]; then bad "$1 exit code" "expected 2, got $GRC"; return 1; fi
  case "$GERR" in
    *BLOCKED:*WHY:*REDIRECT:*RULE:*) ok ;;
    *) bad "$1 deny text" "$GERR" ;;
  esac
}
allow() { # $1 label $2 command $3 cwd
  runguard "$2" "$3"
  [ "$GRC" -eq 0 ] && ok || bad "$1 allowed but" "rc=$GRC err=$GERR"
}

gpayload() { # $1 command $2 cwd: writes JSON to $GPAY (python writes it; no shell redirect)
  python3 - "$1" "$2" "$GPAY" <<'PY'
import io, json, sys
io.open(sys.argv[3], "w", encoding="utf-8").write(json.dumps(
    {"tool_name": "Bash", "tool_input": {"command": sys.argv[1]}, "cwd": sys.argv[2]}))
PY
}

runguard() { # $1 command $2 cwd: sets GOUT (stdout), GERR (stderr), GRC
  GPAY="$SANDBOX/payload.json"
  gpayload "$1" "$2"
  GOUT=`sh "$HOOK" < "$GPAY" 2>/dev/null`; GRC=$?
  GERR=`sh "$HOOK" < "$GPAY" 2>&1 1>/dev/null`
}

card="$SANDBOX/card.json"
setup_card "$SANDBOX"

echo "ALLOW cases first: mentions, other commands, unparseable stdin"
WD="$SANDBOX/wd"; mkdir -p "$WD"
allow "grep mentioning the runner" "grep -n advance $RUNNER" "$WD"
allow "cat of the runner" "cat $RUNNER" "$WD"
allow "git commit -m quoting the trigger" "git commit -m \"run stage_runner.py $ADV on it\"" "$WD"
allow "echo of the path" "echo $RUNNER" "$WD"
allow "no runner token" "ls -la" "$WD"
allow "a command with no judgement needed" "true" "$WD"
JUNK_FILE="$SANDBOX/junk.txt"
printf 'not json at all' > "$JUNK_FILE"
JUNK_RC=`sh "$HOOK" < "$JUNK_FILE" 2>&1 1>/dev/null; echo $?`
[ "$JUNK_RC" -eq 0 ] && ok || bad "unparseable stdin allow" "rc=$JUNK_RC"

echo "a fresh talk-step run: the AI's plain hand moves are refused"
start_out=`python3 "$RUNNER" start --card "$card" --workdir "$WD" 2>&1`
case "$start_out" in *"code word"*) ok ;; *) bad "start run" "$start_out" ;; esac
deny "person-turn subcommand" "python3 $RUNNER $PT1$PT2 --turn t1 --cmd next --workdir $WD" "$WD"
deny "$ADV on a talk step" "python3 $RUNNER $ADV --turn t1 --workdir $WD" "$WD"
deny "$BCK on a talk step" "python3 $RUNNER $BCK --turn t1 --workdir $WD" "$WD"
deny "runner via bare relative path" "python3 system/parts/stage_runner.py $ADV --workdir $WD" "$SANDBOX"

echo "the same commands on an ALONE step: advance passes, back still needs the person"
code=`printf '%s' "$start_out" | grep -o 'RUN-[0-9A-Z]\{6\}' | head -1`
rid=`ls "$WD/runs" | head -1`
printf '## Gather\n\nThe gathered frame is here in full, complete and checked.\n\nCode word: %s\n' "$code" > "$WD/runs/$rid/out/01-gather.md"
python3 "$RUNNER" $PT1$PT2 --turn t1 --cmd next --workdir "$WD" > /dev/null 2>&1
adv_out=`python3 "$RUNNER" $ADV --turn t1 --workdir "$WD" 2>&1`
code2=`printf '%s' "$adv_out" | grep -o 'RUN-[0-9A-Z]\{6\}' | head -1`
printf '## Analyze\n\nThe analysis follows from the gathered frame, complete and checked throughout.\n\nCode word: %s\n' "$code2" > "$WD/runs/$rid/out/02-analyze.md"
python3 "$RUNNER" $PT1$PT2 --turn t2 --cmd next --workdir "$WD" > /dev/null 2>&1
python3 "$RUNNER" $ADV --turn t2 --workdir "$WD" > /dev/null 2>&1
mode=`python3 "$HOOKS/../parts/run_pickup.py" mode --workdir "$WD"`
[ "$mode" = "alone" ] && ok || bad "reached alone step" "mode=$mode"
allow "$ADV on an alone step" "python3 $RUNNER $ADV --workdir $WD" "$WD"
deny "$BCK on an alone step (back always needs the person)" "python3 $RUNNER $BCK --workdir $WD" "$WD"

echo "the read-only and closed-menu commands pass"
allow "check" "python3 $RUNNER check --workdir $WD" "$WD"
allow "status" "python3 $RUNNER status --workdir $WD" "$WD"
allow "verify" "python3 $RUNNER verify --workdir $WD" "$WD"
allow "statusline" "python3 $RUNNER statusline --workdir $WD" "$WD"
allow "recover" "python3 $RUNNER recover --workdir $WD" "$WD"

echo "the state-changing menu commands pass on a throwaway run"
WD2="$SANDBOX/wd2"; mkdir -p "$WD2"
python3 "$RUNNER" start --card "$card" --workdir "$WD2" > /dev/null 2>&1
allow "resume --choice continue" "python3 $RUNNER resume --choice continue --workdir $WD2" "$WD2"
allow "snooze --choice leave-it" "python3 $RUNNER snooze --choice leave-it --workdir $WD2" "$WD2"
allow "abandon --choice start-over" "python3 $RUNNER abandon --choice start-over --workdir $WD2" "$WD2"
allow "start (new run after abandon)" "python3 $RUNNER start --card $card --workdir $WD2" "$WD2"

echo "phase 4c: the plain side doors (failing-first plants)"
# the denies below judge the MODE, so they need a run whose open step is still a talk step
WD4C="$SANDBOX/wd4c"; mkdir -p "$WD4C"
python3 "$RUNNER" start --card "$card" --workdir "$WD4C" > /dev/null 2>&1
deny "person-turn after a global option" "python3 $RUNNER --workdir $WD4C $PT1$PT2 --turn t9 --cmd next" "$WD4C"
deny "status && advance on a talk step" "python3 $RUNNER status --workdir $WD4C && python3 $RUNNER $ADV --workdir $WD4C" "$WD4C"
deny "glob-built runner name" "python3 $SANDBOX/stage_r*.py $ADV --workdir $WD4C" "$SANDBOX"
deny "bash -c wrapping the runner" "bash -c 'python3 $RUNNER $ADV --workdir $WD'" "$WD"
deny "sh -c wrapping the runner" "sh -c 'python3 $RUNNER $BCK --workdir $WD'" "$WD"
deny "eval wrapping the runner" "eval python3 $RUNNER $ADV --workdir $WD" "$WD"
deny "xargs wrapping the runner" "echo x | xargs python3 $RUNNER $ADV --workdir $WD" "$WD"
deny "python3 -c importing the runner" "python3 -c \"import stage_runner; stage_runner.append('x','pass','g',{})\"" "$WD"
deny "runner path held in a variable" "R=$RUNNER; python3 \"\$R\" $ADV --workdir $WD" "$WD"
deny "-m stage_runner module person-turn" "python3 -m stage_runner $PT1$PT2 --turn t7 --cmd next --workdir $WD4C" "$WD4C"
deny "-m stage_runner module $ADV on a talk step" "python3 -m stage_runner $ADV --turn t7 --workdir $WD4C" "$WD4C"
allow "-m stage_runner module status" "python3 -m stage_runner status --workdir $WD4C" "$WD4C"
allow "status with the workdir option first" "python3 $RUNNER --workdir $WD status" "$WD"

# phase 4e A4: a global --workdir before the subcommand is honoured (regression: the
# argparse SUPPRESS change must not loosen the guard)
echo "phase 4e A4: global --workdir regression"
NOWHERE="$SANDBOX/nowhere"; mkdir -p "$NOWHERE"
deny "global --workdir advance on a talk step (cwd elsewhere)" "python3 $RUNNER --workdir $WD4C $ADV" "$NOWHERE"
allow "global --workdir status from another folder" "python3 $RUNNER --workdir $WD status" "$NOWHERE"

echo "guard suite: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
