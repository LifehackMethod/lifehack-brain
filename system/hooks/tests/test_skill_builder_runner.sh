#!/bin/bash
# test_skill_builder_runner.sh -- round 2b (B1 no runner, no run; B5 honest catch-up). ALLOW cases first.
# The /skill-builder prompt starts or resumes the skill builder's step run by CODE (run_step_hook.sh + lib/sb_start.py).
# Run: bash system/hooks/tests/test_skill_builder_runner.sh   (exit 0 = all pass)
# SB_HOOKS=<hooks dir> points the suite at a copy (used to show each check failing against a broken copy first).
HERE="$(cd "$(dirname "$0")" && pwd)"
HOOKS="${SB_HOOKS:-$(cd "$HERE/.." && pwd)}"
HOOK="$HOOKS/run_step_hook.sh"
[ -f "$HOOK" ] || { echo "CANNOT RUN: no mover at $HOOK"; exit 1; }
FIX="$HERE/fixtures"
SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/sbrun.XXXXXX" | sed "s#//#/#g")"
trap 'rm -rf "$SANDBOX"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
has() { case "$1" in *"$2"*) return 0;; *) return 1;; esac; }

export HOME="$SANDBOX/home"; mkdir -p "$HOME"
export LIFEHACK_ROOT="$SANDBOX/brain"; mkdir -p "$LIFEHACK_ROOT"
unset CLAUDE_CODE_SESSION_ID
SID="sess-sb-test-0001"
OUTSIDE="$SANDBOX/elsewhere"; mkdir -p "$OUTSIDE"
RUNPTR="$HOOKS/../tools/run_pointer.sh"
n=0
payload() { # $1 prompt  $2 cwd  [$3 session id]  -> JSON
  python3 - "$1" "$2" "${3:-$SID}" <<'PY'
import json, sys, uuid
print(json.dumps({"session_id": sys.argv[3], "prompt_id": str(uuid.uuid4()), "cwd": sys.argv[2], "prompt": sys.argv[1],
                  "hook_event_name": "UserPromptSubmit", "transcript_path": "/tmp/x.jsonl"}))
PY
}
fire() { # $1 hook  $2 prompt  $3 cwd  [$4 sid] -> OUT
  OUT=$(payload "$2" "$3" "$4" | sh "$1" 2>&1); RC=$?
}
pointer() { CLAUDE_CODE_SESSION_ID="${1:-$SID}" bash "$RUNPTR" get; }
runs_in() { ls "$1/runs" 2>/dev/null | wc -l | tr -d ' '; }

echo "B1: starting the skill builder starts its runner"
BUILDS="$LIFEHACK_ROOT/drafts/builds"
# 1. a fresh /skill-builder <name> with no run: a run starts, the RUN line is injected, the pointer is set
fire "$HOOK" "/skill-builder monthly-budget" "$OUTSIDE"
WD="$BUILDS/monthly-budget"
has "$OUT" "RUN: step 1 of 6 (step-1), folder ($WD)" && ok || bad 1a "no RUN line for a fresh start: $OUT"
[ "$(runs_in "$WD")" = 1 ] && ok || bad 1b "no run started in $WD"
[ "$(pointer)" = "$WD" ] && ok || bad 1c "the run pointer is not set to $WD (got '$(pointer)')"
has "$OUT" "code word: RUN-" && ok || bad 1d "the step-1 code word was not handed over"
RID1="$(ls "$WD/runs")"
# 2. a plain /skill-builder with no name: a session-scoped holding folder, said so
fire "$HOOK" "/skill-builder" "$OUTSIDE" "sess-sb-test-0002"
has "$OUT" "RUN: step 1 of 6 (step-1), folder ($BUILDS/_holding-sess-sb-" && ok || bad 2a "no holding-folder run: $OUT"
has "$OUT" "HOLDING FOLDER" && ok || bad 2b "the holding folder was not announced"
# 3. an active run exists: resume, never start (the run id is unchanged), and the run line says so
sleep 1
fire "$HOOK" "/skill-builder monthly-budget" "$OUTSIDE"
has "$OUT" "RUN: step 1 of 6 (step-1), folder ($WD)" && ok || bad 3a "no RUN line on resume: $OUT"
[ "$(runs_in "$WD")" = 1 ] && [ "$(ls "$WD/runs")" = "$RID1" ] && ok || bad 3b "a second run was started (or the id changed)"
grep -q '"event": "reissue"' "$WD/runs/$RID1/record.jsonl" && ok || bad 3c "resume left no reissue line"
# 4. mid-sentence, and the plugin-prefixed spelling
sleep 1
fire "$HOOK" "ok let's go, please run /lifehack-brain:skill-builder monthly-budget for me" "$OUTSIDE"
has "$OUT" "RUN: step 1 of 6 (step-1), folder ($WD)" && ok || bad 4a "mid-sentence prefixed command not recognised: $OUT"
# 5. /next works from a cwd outside the run folder, through the pointer
CODE="$(printf '%s' "$OUT" | grep -o 'RUN-[0-9A-Z]\{6\}' | head -1)"
python3 - "$WD/runs/$RID1/out/step-1.md" "$CODE" <<'PY'
import sys
words = " ".join(["word"] * 70)
open(sys.argv[1], "w").write("## Outcome\n%s\n\n## Harness check\nchecked.\n\n## Size sense\none skill.\n\nCode word: %s\n" % (words, sys.argv[2]))
PY
fire "$HOOK" "/next" "$OUTSIDE"
grep -q '"event": "person"' "$WD/runs/$RID1/record.jsonl" && ok || bad 5a "/next from outside the run folder wrote no person line: $OUT"
has "$OUT" "stage/02.prompt.md" && ok || bad 5b "/next from outside did not move to step 2: $OUT"
# 6. the per-turn line while the run is live
fire "$HOOK" "what do you think about the second question?" "$OUTSIDE"
has "$OUT" "RUN: step 2 of 6 (step-2), folder ($WD)" && ok || bad 6a "no per-turn RUN line on plain chat during a live run: $OUT"
# 7. observe / note / wrap are not this code's: nothing from it, with or without a run
for P in "/skill-builder observe monthly-budget" "/skill-builder note a thought" "/skill-builder wrap" "please /skill-builder note remember this"; do
  fire "$HOOK" "$P" "$OUTSIDE"
  [ -z "$OUT" ] && ok || bad 7 "mode prompt '$P' produced output: $OUT"
done
# 8. plain chat with no run anywhere: nothing
fire "$HOOK" "how is the weather" "$OUTSIDE" "sess-sb-test-0099"
[ -z "$OUT" ] && ok || bad 8a "plain chat with no run produced output: $OUT"
fire "$HOOK" "tell me about the \`/skill-builder\` skill" "$OUTSIDE" "sess-sb-test-0099"
[ -z "$OUT" ] && ok || bad 8b "a command shown in backticks started a run: $OUT"
[ "$(ls "$BUILDS" | wc -l | tr -d ' ')" = 2 ] && ok || bad 8c "plain chat created a design folder: $(ls "$BUILDS")"
# 9. an ordinary word after the command is speech, not a skill name (holding folder, no folder named 'to')
fire "$HOOK" "/skill-builder to plan my week" "$OUTSIDE" "sess-sb-test-0003"
[ ! -d "$BUILDS/to" ] && has "$OUT" "HOLDING FOLDER" && ok || bad 9 "speech after the command was taken as a skill name: $OUT"

echo "B1: the runner cannot start -> one NO RUN line, nothing else"
TREE="$SANDBOX/tree"; mkdir -p "$TREE/system" "$TREE/.claude/skills"
mkdir -p "$TREE/system/hooks" "$TREE/system/parts"; cp -R "$HOOKS/." "$TREE/system/hooks/"; cp -R "$HOOKS/../parts/." "$TREE/system/parts/"
ln -s "$(cd "$HOOKS/../tools" && pwd)" "$TREE/system/tools"; ln -s "$(cd "$HOOKS/../../shared" && pwd)" "$TREE/shared"
ln -s "$(cd "$HOOKS/../../.claude/skills/skill-builder" && pwd)" "$TREE/.claude/skills/skill-builder"
printf 'import sys\nsys.exit(9)\n' > "$TREE/system/parts/stage_runner.py"
export LIFEHACK_ROOT="$SANDBOX/brain2"; mkdir -p "$LIFEHACK_ROOT"
fire "$TREE/system/hooks/run_step_hook.sh" "/skill-builder broken-one" "$OUTSIDE" "sess-sb-test-0004"
LINES=$(printf '%s\n' "$OUT" | grep -c .)
has "$OUT" "NO RUN:" && has "$OUT" "Stop. Tell the person this one line and do nothing else." && ok || bad 10a "no NO RUN line when the runner is broken: $OUT"
[ "$LINES" = 1 ] && ok || bad 10b "more than one line came with NO RUN ($LINES): $OUT"
[ ! -d "$LIFEHACK_ROOT/drafts/builds/broken-one/runs" ] && [ -z "$(CLAUDE_CODE_SESSION_ID=sess-sb-test-0004 bash "$RUNPTR" get)" ] && ok || bad 10c "a run or pointer exists although the runner could not start"
# the card missing: also NO RUN
rm -f "$TREE/.claude/skills/skill-builder"; mkdir -p "$TREE/.claude/skills/skill-builder"
printf '{"skill":"x","stages":[]}' > "$TREE/.claude/skills/skill-builder/card.json"
fire "$TREE/system/hooks/run_step_hook.sh" "/skill-builder broken-card" "$OUTSIDE" "sess-sb-test-0010"
has "$OUT" "NO RUN:" && ok || bad 10f "no NO RUN line when the runner refuses the card: $OUT"
rm -f "$TREE/.claude/skills/skill-builder/card.json"
fire "$TREE/system/hooks/run_step_hook.sh" "/skill-builder broken-two" "$OUTSIDE" "sess-sb-test-0005"
has "$OUT" "NO RUN:" && ok || bad 10d "no NO RUN line when the card is missing: $OUT"
# the starter module itself missing: still NO RUN (never silent)
rm -f "$TREE/system/hooks/lib/sb_start.py"
fire "$TREE/system/hooks/run_step_hook.sh" "/skill-builder broken-three" "$OUTSIDE" "sess-sb-test-0006"
has "$OUT" "NO RUN:" && ok || bad 10e "no NO RUN line when the run starter is missing: $OUT"
export LIFEHACK_ROOT="$SANDBOX/brain"

echo "B5: the honest catch-up (a synthetic design folder; the real one is never touched)"
CU="$SANDBOX/design"; mkdir -p "$CU/out"
python3 - "$CU" <<'PY'
import os, sys
w = " ".join(["word"] * 90)
d = sys.argv[1]
open(os.path.join(d, "out/step-1.md"), "w").write("## Outcome\n%s\n\n## Harness check\nok\n\n## Size sense\nsmall\n\nCode word: (no runner in this window)\n" % w)
open(os.path.join(d, "out/step-2.md"), "w").write("## Steps draft\n%s\n\n## Step count\n6, a skill.\n" % w)
open(os.path.join(d, "out/step-3.md"), "w").write("## Walked steps\n%s\n\n## Step count\n6, a skill.\n" % w)
PY
find "$CU" -type f | sort | xargs shasum > "$SANDBOX/cu-before.sum"
CSID="sess-sb-test-0007"
fire "$HOOK" "/skill-builder catch-up 3 $CU" "$OUTSIDE" "$CSID"
has "$OUT" "CATCH-UP READY" && ok || bad 11a "catch-up did not report READY: $OUT"
has "$OUT" "RUN: step 1 of 6" && ok || bad 11b "no RUN line from catch-up: $OUT"
CRID="$(ls "$CU/runs")"
[ -f "$CU/runs/$CRID/out/step-1.md" ] && ok || bad 11c "step 1's file was not staged"
! grep -q '"event": "person"\|"event": "pass"\|"event": "handover"' "$CU/runs/$CRID/record.jsonl" && ok || bad 11d "catch-up wrote a person/pass/handover line itself"
for k in 1 2 3; do fire "$HOOK" "/next" "$OUTSIDE" "$CSID"; done
CST=$(python3 "$HOOKS/../parts/stage_runner.py" status --json --workdir "$CU" 2>&1)
has "$CST" '"stage": "step-4"' && ok || bad 11e "three typed /next did not land in step 4: $CST"
python3 "$HOOKS/../parts/stage_runner.py" verify --workdir "$CU" > "$SANDBOX/verify.out" 2>&1; VRC=$?
[ "$VRC" = 0 ] && ok || bad 11f "verify did not pass (exit $VRC): $(cat "$SANDBOX/verify.out")"
find "$CU" -type f -not -path "$CU/runs/*" -not -path "$CU/.claude/*" -not -name '.stage-runner.json' | sort | xargs shasum > "$SANDBOX/cu-after.sum"
grep -v "/runs/\|/\.claude/\|stage-runner" "$SANDBOX/cu-before.sum" | diff -q - "$SANDBOX/cu-after.sum" >/dev/null && ok || bad 11g "catch-up changed the design folder's own files"
# a missing step file: stops before starting anything
CU2="$SANDBOX/design2"; mkdir -p "$CU2/out"; cp "$CU/out/step-1.md" "$CU2/out/"
fire "$HOOK" "/skill-builder catch-up 2 $CU2" "$OUTSIDE" "sess-sb-test-0008"
has "$OUT" "NO RUN:" && [ ! -d "$CU2/runs" ] && ok || bad 12 "a missing step file did not stop the catch-up cleanly: $OUT"
# a run already active there: refused, nothing changed
fire "$HOOK" "/skill-builder catch-up 3 $CU" "$OUTSIDE" "$CSID"
has "$OUT" "NO RUN:" && [ "$(runs_in "$CU")" = 1 ] && ok || bad 13 "catch-up over a live run was not refused: $OUT"

echo "suite: $pass passed, $fail failed"
[ "$fail" = 0 ]
