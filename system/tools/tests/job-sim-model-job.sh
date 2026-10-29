#!/usr/bin/env bash
# job-sim-model-job.sh — TEST-ONLY job command for the 5.3 rig scenarios (job-sim.sh, model_scenarios).
# Calls run_model N times (N = $JOB_SIM_DIR/mode/<job>-calls, default 1) through LIFEHACK_MODEL_STUB.
# Deliberately SWALLOWS run_model's return code and exits 0, so the scenarios prove that job-run.sh
# fails the run itself (a job's exit 0 alone is never a success). Writes the row-check output file.
set -u
job="${1:?usage: job-sim-model-job.sh <job>}"
dir="${JOB_SIM_DIR:?JOB_SIM_DIR not set — this only runs under the rig}"
. "$LIFEHACK_CODE_ROOT/system/tools/model.lib.sh"
n="$(cat "$dir/mode/$job-calls" 2>/dev/null || echo 1)"
printf 'prompt\n' > "$dir/prompt-$job"
for i in $(seq 1 "$n"); do
  # swallows run_model's rc in a way the door's `|| true` rule cannot see: job-run.sh must still fail the run from the call record
  if ! run_model small "$dir/prompt-$job" "$dir/reply-$job" "MARK"; then :; fi
done
mkdir -p "$dir/out"
echo "ran $job at ${LIFEHACK_FAKE_NOW:-real-clock}" > "$dir/out/$job"
if [ -n "${LIFEHACK_FAKE_NOW:-}" ]; then
  touch -t "$(date -r "$LIFEHACK_FAKE_NOW" +%Y%m%d%H%M.%S 2>/dev/null || date -d "@$LIFEHACK_FAKE_NOW" +%Y%m%d%H%M.%S)" "$dir/out/$job"
fi
exit 0
