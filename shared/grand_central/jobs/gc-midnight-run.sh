#!/usr/bin/env bash
# not-wired-yet: its row lands in system/jobs.md through the V2 window when feat/gc-planning-weekly merges (plan 4P.0b / 4P.8)
# gc-midnight-run.sh — the plugin's thin runner for the Grand Central daily diary job (daily, 00:00).
# Plan 4P.0b (engine plumbing): the DEFAULT daily diary job (ruling 7) — a person's own row of the same
# name wins over this one on purpose; this runner is the generic one every installer gets.
# Thin on purpose: all the work is grand_central/gcjobs.py midnight (morning.midnight_entry for every
# recent staged day; no model, no network). A night with nothing staged is a GOOD run with a receipt
# (staged_days=0), never a stand-down, so no "paused" text is ever sent for an empty window (4P.0b).
# This file does no outside read of its own. Exit codes pass straight through (cron SOP section 4):
# 0 receipt written, 75 stood down (engine not set up / lock held), 2 transient, 1 failed.
# The receipt is written by gcjobs.py AFTER it verifies the artifact; this runner writes none itself.
set -euo pipefail
: "${LIFEHACK_CODE_ROOT:?run me through job-run.sh (it exports LIFEHACK_CODE_ROOT)}"
ENG="$LIFEHACK_CODE_ROOT/shared/grand_central"
[ -f "$ENG/gcjobs.py" ] || { echo "[gc-midnight] FATAL: the engine is missing: $ENG/gcjobs.py" >&2; exit 1; }
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
PY="${GC_PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || { echo "[gc-midnight] FATAL: no python interpreter: $PY" >&2; exit 1; }
# Not set up -> stand down (75), never a fault: no Grand Central setup folder, or no gc.json in it.
if ! GC_ENG="$ENG" "$PY" - <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["GC_ENG"])
import gc_settings
gc_settings.setup_path("gc.json")
PYEOF
then
  echo "[gc-midnight] stood down: the Grand Central engine is not set up (no setup folder or no gc.json)" >&2
  exit 75
fi
cd "$ENG"
exec "$PY" "$ENG/gcjobs.py" midnight "$@"
