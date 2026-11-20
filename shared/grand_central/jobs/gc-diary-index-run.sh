#!/usr/bin/env bash
# not-wired-yet: its row lands in system/jobs.md through the V2 window when feat/gc-planning-weekly merges (plan 4P.3 item 10)
# gc-diary-index-run.sh — the plugin's thin runner for the Grand Central diary-index refresher (daily, interval 86400).
# Plan 4P.3 item 10: the one gc-midnight duty that must stay on a schedule when midnight retires (midnight
# inventory duty 5, 2026-11-20) — without it the diary_index table goes stale and `gc person`'s DIARY lines
# go dark. Thin on purpose: all the work is grand_central/diary_index_job.py (code only — refresh_index once
# per diary under the store's write lock; no model, no network, no email). This file does no outside read of
# its own. Exit codes pass straight through (cron SOP section 4): 0 receipt written, 75 stood down
# (engine not set up / no database file), 1 failed (a diary failed; the others still ran; no receipt).
# The receipt is written by the job AFTER the refresh, LAST, atomically; this runner writes none itself.
set -euo pipefail
: "${LIFEHACK_CODE_ROOT:?run me through job-run.sh (it exports LIFEHACK_CODE_ROOT)}"
ENG="$LIFEHACK_CODE_ROOT/shared/grand_central"
[ -f "$ENG/diary_index_job.py" ] || { echo "[gc-diary-index] FATAL: the engine is missing: $ENG/diary_index_job.py" >&2; exit 1; }
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
PY="${GC_PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || { echo "[gc-diary-index] FATAL: no python interpreter: $PY" >&2; exit 1; }
# Not set up -> stand down (75), never a fault: no Grand Central setup folder, or no gc.json in it
# (gc_settings raises SettingsError; the engine itself must not be started half-configured).
if ! GC_ENG="$ENG" "$PY" - <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["GC_ENG"])
import gc_settings
gc_settings.setup_path("gc.json")
PYEOF
then
  echo "[gc-diary-index] stood down: the Grand Central engine is not set up (no setup folder or no gc.json)" >&2
  exit 75
fi
cd "$ENG"
exec "$PY" "$ENG/diary_index_job.py" "$@"
