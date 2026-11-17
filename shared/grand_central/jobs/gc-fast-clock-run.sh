#!/usr/bin/env bash
# not-wired-yet: its row lands in system/jobs.md through the V2 window when feat/gc-planning-weekly merges (plan 4P.0b / 4P.8)
# gc-fast-clock-run.sh — the plugin's thin runner for the Grand Central fast clock (every 600 s).
# Plan 4P.0b (engine plumbing): a job every installer would want ships a runner in the plugin, written
# fresh and generic — everything resolves from $LIFEHACK_CODE_ROOT (job-run.sh exports it) and the
# engine's own settings loader; no hard-coded home path, no one person's names.
# Thin on purpose: all the work is grand_central/gcjobs.py fast-clock (front-room filing, the
# calendar+tasks source pull through pull.py, alarm candidates, the morning launch check). This file
# does no outside read of its own and makes no model call of its own.
# Exit codes pass straight through (cron SOP section 4): 0 receipt written, 75 stood down
# (engine not set up / nothing configured / lock held), 2 transient, 1 failed.
# The receipt is written by gcjobs.py AFTER it verifies the artifact; this runner writes none itself.
set -euo pipefail
: "${LIFEHACK_CODE_ROOT:?run me through job-run.sh (it exports LIFEHACK_CODE_ROOT)}"
ENG="$LIFEHACK_CODE_ROOT/shared/grand_central"
[ -f "$ENG/gcjobs.py" ] || { echo "[gc-fast-clock] FATAL: the engine is missing: $ENG/gcjobs.py" >&2; exit 1; }
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
PY="${GC_PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || { echo "[gc-fast-clock] FATAL: no python interpreter: $PY" >&2; exit 1; }
# Not set up -> stand down (75), never a fault: no Grand Central setup folder, or no gc.json in it
# (gc_settings raises SettingsError; the engine itself must not be started half-configured).
if ! GC_ENG="$ENG" "$PY" - <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["GC_ENG"])
import gc_settings
gc_settings.setup_path("gc.json")
PYEOF
then
  echo "[gc-fast-clock] stood down: the Grand Central engine is not set up (no setup folder or no gc.json)" >&2
  exit 75
fi
cd "$ENG"
exec "$PY" "$ENG/gcjobs.py" fast-clock "$@"
