#!/bin/bash
# run-all.sh - regression tests for the /build runner (scripts/build_run.sh), driven by a stub builder.
#
# LLM CONTEXT
# WHY: proves the runner's guarantees without a real AI: a clean plan finishes (Door 3 PASS); a planted
#   rule break is caught and stops the run (ALW-1); a run killed mid-card resumes without redoing passed
#   cards; a refused checkpoint stops the run. stub-ai.sh stands in for the builder (BUILD_AI_CMD).
# HOW TO RUN: bash run-all.sh   (needs python3; no network, no real AI). Then read $BUILD_TEST_OUT/toy.log:
#   expect 4 lines ending MATCH and none MISMATCH. Safe to repeat; each run gets fresh mktemp dirs.
# OUTPUT: bulk per-run output goes OFF the repo, to ${BUILD_TEST_OUT:-$HOME/lifehack-scratch/build-skill/toy-runs}
#   (one run-XXXXXX dir per case, runs.txt, toy.log). Plans are templates in plans/; @R@ = run dir, @P@ = card prefix.
# SIGNPOST: score.sh grades each case into toy.log; stub-ai.sh is the fake builder (STUB_PLANT=1 plants a
#   rule break, generated at run time); scripts/build_run.sh and scripts/plan_queue.py are found from this file.

HERE="$(cd "$(dirname "$0")" && pwd)"
T="${BUILD_TEST_OUT:-$HOME/lifehack-scratch/build-skill/toy-runs}"
BR="$HERE/../scripts/build_run.sh"
PQ="$HERE/../scripts/plan_queue.py"
export BUILD_AI_CMD="$HERE/stub-ai.sh"
export BUILD_TEST_OUT="$T"
mkdir -p "$T"
: > "$T/runs.txt"

mkplan() { # R prefix template
  local R="$1" p="$2" tpl="$HERE/plans/$3" f="$1/plan.md"
  sed -e "s|@R@|$R|g" -e "s|@P@|$p|g" "$tpl" > "$f"
  python3 "$PQ" "$f" > "$R/pq.txt" 2>&1; echo "plan_queue rc=$?" >> "$R/pq.txt"
}
newrun() { # case -> sets R and env
  R="$(mktemp -d "$T/run-XXXXXX")"
  export BUILD_RUN_HOME="$R/home" STUB_LOG="$R/invocations.log" STUB_PIDFILE="$R/stub.pid"
  unset STUB_PLANT STUB_PLANT_ON STUB_SLEEP_ON
  : > "$STUB_LOG"; REC="$R/record.tsv"; RC="$R/rc.txt"; : > "$RC"
  echo "$1 $R" >> "$T/runs.txt"
}
# last-line-complete guard: note (loudly, in out.txt) if the record's last byte is not a newline
chk_record() { [ ! -s "$REC" ] || [ "$(tail -c 1 "$REC" | od -An -c | tr -d ' ')" = '\n' ] || echo "TEST-NOTE: record truncated (no final newline)" >> "$R/out.txt"; }
run() { bash "$BR" "$R/plan.md" --run-id toy --record "$REC" "$@" >> "$R/out.txt" 2>&1; echo $? >> "$RC"; chk_record; }

# (a) clean
newrun clean; mkplan "$R" TA three-scripts.md
run; run --answer yes

# (b) planted
newrun planted; mkplan "$R" TB three-scripts.md
run; STUB_PLANT=1 STUB_PLANT_ON=TB2 run --answer yes

# (c) resume
newrun resume; mkplan "$R" TC three-scripts.md
run
STUB_SLEEP_ON=TC2 bash "$BR" "$R/plan.md" --run-id toy --record "$REC" --answer yes >> "$R/out.txt" 2>&1 &
BG=$!
for i in $(seq 1 60); do
  grep -q "TC1.*passed" "$REC" 2>/dev/null && grep -qx TC2 "$STUB_LOG" && break
  sleep 1
done
kill "$BG" 2>/dev/null
if [ -s "$R/stub.pid" ]; then sp="$(cat "$R/stub.pid")"; pkill -P "$sp" 2>/dev/null; kill "$sp" 2>/dev/null; fi
wait "$BG" 2>/dev/null; echo "killed" >> "$RC"
sleep 1
run

# (d) checkpoint-no
newrun checkpoint-no; mkplan "$R" TD three-with-checkpoint.md
run; run --answer yes; run --answer no

bash "$HERE/score.sh"
