#!/usr/bin/env bash
# not-wired-yet: its row lands in system/jobs.md through the V2 window when feat/gc-planning-weekly merges (plan 4P.0b / 4P.8)
# gc-morning-run.sh — the plugin's thin runner for the Grand Central daily morning read.
# Plan 4P.0b (engine plumbing). Ships OFF by design: the fast clock starts the morning read when it is
# due (after 05:00 local); this row exists so the job is registered and its receipt is checked. gcjobs.py
# itself stands down (75) on a scheduled run before 05:00, and only runs on a forced test run.
# Thin on purpose: all the work is grand_central/gcjobs.py morning (morning.py hand_run — its one
# tool-less model call happens inside the engine; this runner makes none). No outside read here.
# Exit codes pass straight through (cron SOP section 4): 0 receipt written, 75 stood down
# (engine not set up / before 05:00 / lock held), 2 transient, 1 failed.
# The receipt is written by gcjobs.py AFTER it verifies the artifact; this runner writes none itself.
set -euo pipefail
: "${LIFEHACK_CODE_ROOT:?run me through job-run.sh (it exports LIFEHACK_CODE_ROOT)}"
ENG="$LIFEHACK_CODE_ROOT/shared/grand_central"
[ -f "$ENG/gcjobs.py" ] || { echo "[gc-morning] FATAL: the engine is missing: $ENG/gcjobs.py" >&2; exit 1; }
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
PY="${GC_PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || { echo "[gc-morning] FATAL: no python interpreter: $PY" >&2; exit 1; }
# Not set up -> stand down (75), never a fault: no Grand Central setup folder, or no gc.json in it.
if ! GC_ENG="$ENG" "$PY" - <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["GC_ENG"])
import gc_settings
gc_settings.setup_path("gc.json")
PYEOF
then
  echo "[gc-morning] stood down: the Grand Central engine is not set up (no setup folder or no gc.json)" >&2
  exit 75
fi
cd "$ENG"
exec "$PY" "$ENG/gcjobs.py" morning "$@"
