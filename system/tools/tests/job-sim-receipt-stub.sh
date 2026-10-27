#!/usr/bin/env bash
# job-sim-receipt-stub.sh — TEST-ONLY stub runner for system/tools/tests/job-sim.sh (5.7 *-contract scenarios).
# It stands in for a migrated job's runner (mirror-fetch-run.sh, guard-fire-test-run.sh) and writes the job's RECEIPT
# file, so the row's REAL `check` regex is exercised without fetching git or firing a guard.
#   usage: job-run.sh row command:  bash job-sim-receipt-stub.sh <job> <receipt-path>
# What it does comes from files the rig writes: $JOB_SIM_DIR/mode/<job> and $JOB_SIM_DIR/receipt/<job>.good|.bad
#   good     writes the .good line to <receipt-path>, stamped with LIFEHACK_FAKE_NOW, exit 0
#   bad      writes the .bad line (a run that did NOT succeed: wrong marker), fresh, exit 0
#   old      writes the .good line but leaves it OLDER than the run start (a previous run's receipt), exit 0
#   missing  writes nothing, exit 0 (the [F2] shape: ran, exited 0, produced no evidence)
# Never touches anything outside $JOB_SIM_DIR and <receipt-path> (which the rig puts under its throwaway HOME).
set -u
job="${1:?usage: job-sim-receipt-stub.sh <job> <receipt-path>}"; out="${2:?receipt path}"
dir="${JOB_SIM_DIR:?JOB_SIM_DIR not set — this stub only runs under the rig}"
mode="$(cat "$dir/mode/$job" 2>/dev/null || echo missing)"
stampto() { [ -n "${LIFEHACK_FAKE_NOW:-}" ] || return 0
  touch -t "$(date -r "$1" +%Y%m%d%H%M.%S 2>/dev/null || date -d "@$1" +%Y%m%d%H%M.%S)" "$out"; }
mkdir -p "$(dirname "$out")"
# A job whose row names a model tier (marc-health: small) makes its ONE model call per run through the shared run_model, like the real
# runner (job-run.sh exports JOB_RUN_MODEL and the budget/calls files); the rig's LIFEHACK_MODEL_STUB answers it. No-AI jobs skip this.
if [ "${JOB_RUN_MODEL:-none}" != none ]; then
  . "$LIFEHACK_CODE_ROOT/system/tools/model.lib.sh"
  printf 'prompt\n' > "$dir/prompt-$job"
  run_model "$JOB_RUN_MODEL" "$dir/prompt-$job" "$dir/reply-$job" "MARK" || true
fi
case "$mode" in
  good)    cp "$dir/receipt/$job.good" "$out"; stampto "${LIFEHACK_FAKE_NOW:-0}" ;;
  bad)     cp "$dir/receipt/$job.bad" "$out"; stampto "${LIFEHACK_FAKE_NOW:-0}" ;;
  old)     cp "$dir/receipt/$job.good" "$out"; stampto "$(( ${LIFEHACK_FAKE_NOW:-100000} - 86400 ))" ;;
  missing) ;;
  *) echo "stub: unknown mode '$mode'" >&2; exit 64 ;;
esac
exit 0
