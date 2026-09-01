#!/usr/bin/env bash
# system-health-run.sh — Pulse runner for the missed-run sweeper (state/status/_system-health.json).
#
# PORTED (2026-08-14) from claudeops-config's system/tools/system-health-run.sh. The donor version
# was machine-gated (only one of two machines should write the single shared feed) and set
# INGEST_COVERAGE_FLAG=on for a desk-registry-driven coverage check — neither applies here: this is
# a single-machine install (nothing to gate between), and system-health.py in this repo does not
# carry that desk-registry coverage check at all (see that file's own header for what was cut and
# why). What's left is the part that still matters: single-instance locking (so two overlapping
# Pulse ticks can't race on the same tile write) and running the sweeper itself.
#
# READ-ONLY (reads pulse-config + the heartbeat + every tile; writes only its own feed).
set -uo pipefail
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$CODE_ROOT/system/tools/ingest-run.lib.sh"

JOB="system-health"

ingest_acquire_lock "$JOB"

# NOT `exec`: exec replaces this shell, so the EXIT trap ingest_acquire_lock() registered never
# fires and the lock dir outlives every run — the next ticks then skip on "another run in
# progress" until the 25-minute stale-steal, turning a 300s job into a ~30-minute one. A plain
# call lets bash wait, clean the lock, and still exit with python's status (it is the last command).
python3 "$CODE_ROOT/system/tools/system-health.py"
