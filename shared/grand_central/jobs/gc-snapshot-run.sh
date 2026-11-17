#!/usr/bin/env bash
# not-wired-yet: its row lands in system/jobs.md through the V2 window when feat/gc-planning-weekly merges (plan 4P.0b / 4P.8)
# gc-snapshot-run.sh — the plugin's thin runner for the Grand Central nightly snapshot (daily).
# Plan 4P.0b (engine plumbing), generalised from the owner's personal wrapper: backup.py local, then
# snapshot (to the notes folder's backups directory, engine-retention), then verify on that snapshot.
# Everything resolves from $LIFEHACK_CODE_ROOT and the engine's settings loader — no hard-coded home
# path, no one person's names. Pure code: no AI, no model call, no network of its own.
# The engine writes no receipt for this job, so the runner writes the proof line ONLY on full success
# (after verify passes); any failure exits non-zero and leaves no fresh proof.
# After the receipt, the setup copy (backup.py settings + verify-settings) runs: a failure there is
# reported loudly and fails the run (the alarm fires), but it can never block or un-prove the database
# snapshot above it.
# Env passthrough for tests: GC_DATA_ROOT, GC_STATE_ROOT, GC_SETUP_DIR, GC_PYTHON.
# Exit codes (cron SOP section 4): 0 receipt written, 75 stood down (engine not set up), 1 failed.
set -euo pipefail
: "${LIFEHACK_CODE_ROOT:?run me through job-run.sh (it exports LIFEHACK_CODE_ROOT)}"
ENG="$LIFEHACK_CODE_ROOT/shared/grand_central"
[ -f "$ENG/backup.py" ] || { echo "[gc-snapshot] FATAL: the engine is missing: $ENG/backup.py" >&2; exit 1; }
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
PY="${GC_PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || { echo "[gc-snapshot] FATAL: no python interpreter: $PY" >&2; exit 1; }
# Not set up -> stand down (75), never a fault: no Grand Central setup folder, or no gc.json in it.
if ! GC_ENG="$ENG" "$PY" - <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["GC_ENG"])
import gc_settings
gc_settings.setup_path("gc.json")
PYEOF
then
  echo "[gc-snapshot] stood down: the Grand Central engine is not set up (no setup folder or no gc.json)" >&2
  exit 75
fi
# The receipt folder is the engine's own state root (GC_STATE_ROOT, else <data root>/state) + /gc-snapshot.
STATE="$(GC_ENG="$ENG" "$PY" - <<'PYEOF'
import os, sys
sys.path.insert(0, os.environ["GC_ENG"])
import gc_settings
print(os.path.join(gc_settings.state_dir(), "gc-snapshot"))
PYEOF
)"
[ -n "$STATE" ] || { echo "[gc-snapshot] FAIL: could not resolve the engine's state folder" >&2; exit 1; }
mkdir -p "$STATE"
PROOF="$STATE/last-run.txt"
cd "$ENG"
"$PY" backup.py local
SNAP="$("$PY" backup.py snapshot | tail -n 1)"
[ -n "$SNAP" ] && [ -f "$SNAP" ] || { echo "[gc-snapshot] FAIL: snapshot path not a file: '$SNAP'" >&2; exit 1; }
VOUT="$("$PY" backup.py verify "$SNAP")" || { echo "$VOUT" >&2; echo "[gc-snapshot] FAIL: verify rejected $SNAP" >&2; exit 1; }
echo "$VOUT"
ROWS="$(printf '%s\n' "$VOUT" | sed -n '1s/.* \([0-9][0-9]*\) rows$/\1/p')"
case "$ROWS" in ''|*[!0-9]*) echo "[gc-snapshot] FAIL: could not read row count from verify output" >&2; exit 1;; esac
LINE="gc-snapshot ok date=$(date +%F) snapshot=$(basename "$SNAP") rows=$ROWS at=$(date -u +%FT%TZ)"
printf '%s\n' "$LINE" > "$PROOF.tmp" && mv "$PROOF.tmp" "$PROOF"
echo "$LINE"
# Settings copy (setup/*.json beside the db snapshots, engine retention) + check, AFTER the receipt.
if SET_COPY="$("$PY" backup.py settings)" && SET_OUT="$("$PY" backup.py verify-settings)"; then
  echo "$SET_COPY"
  echo "$SET_OUT"
  echo "settings-check ok at=$(date -u +%FT%TZ)" > "$STATE/settings-check.txt"
else
  echo "settings-check FAILED at=$(date -u +%FT%TZ)" > "$STATE/settings-check.txt"
  echo "[gc-snapshot] SETTINGS CHECK FAILED (the database snapshot above is fine): ${SET_OUT:-the settings copy raised an error}" >&2
  exit 1
fi
