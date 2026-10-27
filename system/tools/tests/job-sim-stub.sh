#!/usr/bin/env bash
# job-sim-stub.sh — TEST-ONLY stub job for system/tools/tests/job-sim.sh (self-monitoring 2.0).
# job-run.sh runs it as the command of a "sim-*" manifest row. What it does this tick comes from a
# file the rig writes: $JOB_SIM_DIR/mode/<job>. Modes:
#   ok         writes $JOB_SIM_DIR/out/<job> (stamped with LIFEHACK_FAKE_NOW when set), exit 0
#   fail       exit 1, no output
#   silent     exit 0, no output          (the F2 shape: "ran" is not "succeeded")
#   hang       sleeps far past the (rig-shortened) watchdog
#   standdown  exit 75
#   transient  exit 2
# Never touches anything outside $JOB_SIM_DIR. No network.
set -u
job="${1:?usage: job-sim-stub.sh <job>}"
dir="${JOB_SIM_DIR:?JOB_SIM_DIR not set — this stub only runs under the rig}"
mode="$(cat "$dir/mode/$job" 2>/dev/null || echo missing)"
case "$mode" in
  ok)
    mkdir -p "$dir/out"
    echo "ran $job at ${LIFEHACK_FAKE_NOW:-real-clock}" > "$dir/out/$job"
    if [ -n "${LIFEHACK_FAKE_NOW:-}" ]; then
      ts="$(date -r "$LIFEHACK_FAKE_NOW" +%Y%m%d%H%M.%S 2>/dev/null || date -d "@$LIFEHACK_FAKE_NOW" +%Y%m%d%H%M.%S)"
      touch -t "$ts" "$dir/out/$job"
    fi
    exit 0 ;;
  fail)      echo "stub: failing on purpose" >&2; exit 1 ;;
  silent)    echo "stub: skipped quietly, exit 0, no output"; exit 0 ;;
  hang)      exec sleep 30 ;;
  standdown) exit 75 ;;
  transient) exit 2 ;;
  *)         echo "stub: unknown mode '$mode'" >&2; exit 64 ;;
esac
