#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# cal-vault-run.sh — headless runner for the Cal overnight VERBATIM raw-vault pull.
# Exports the keychain-free gws-cron env (so email_convert.py / safe_calendar.py / gws all auth
# headlessly), pre-flights gws, then runs cal-vault-pull.py. READ-ONLY against Google; the only
# writes are the local vault files. Fail-soft (a source failure → marked in _manifest, exit 0).
#
# Cron (Stage 1): 0 4 * * *  bash cal-vault-run.sh   (today's material, ready by morning)
# Test by hand:   bash cal-vault-run.sh [--date YYYY-MM-DD]
#
# ⚖ PORT NOTE: donor's LEAD-MACHINE gate (state/primary-machine marker election between two machines)
# is DELETED, not translated — a student has one computer, so there is nothing to elect between.
# ⚠ CORRECTED 2026-08-15 (T9.7d): this used to deny that DEST had any scheduler or cron scaffold.
# That's false — `system/tools/pulse.sh` is the live daemon, `system/tools/install-schedulers.sh`
# installs its entry (cron or Windows Task Scheduler), and several sibling runners have rows in
# `system/pulse-config.md`. What's still true: this runner specifically has no row there yet
# (the cron comment above is the intended shape, not yet wired into pulse-config.md) — ported so
# it is correct and callable the moment one is added. A student with no `gws` binary / no
# Google account is fine here: this runner is fail-soft by design (a source failure marks it in
# the manifest and still exits 0), matching cal-vault-pull.py's own already-ported honest-degrade
# behavior (it explicitly refuses to fake the email surface when email_convert.py isn't present).
# ─────────────────────────────────────────────────────────────────────────────
set -u
# Execution-residency: DRIVE = CONTENT root (vault/state WRITTEN here); CODE_ROOT = where this
# script + its .py tools live (derived from $0 → the git clone when cron calls the clone).
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# The ONE headless-gws credential preflight — shared with the ten other runners that reach Google.
# A missing library is a REAL defect (exit 1), never a stand-down.
. "$CODE_ROOT/system/tools/gws-auth.lib.sh" || {
  echo "[cal-vault] FATAL: cannot source $CODE_ROOT/system/tools/gws-auth.lib.sh"; exit 1; }

# The data root, through the ONE resolver — never a hardcoded personal Drive path.
DRIVE="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
if [ -z "$DRIVE" ]; then
  echo "[cal-vault] no data root set — nothing to pull into. Set one: python3 shared/brain_root.py --set <folder>"
  exit 2
fi

GWS_BIN="$(command -v gws 2>/dev/null || echo /opt/homebrew/bin/gws)"

# ── GWS HEADLESS AUTH (keychain-free isolated config) ──
# (No abort if creds absent — interactive runs use the normal gws login; the pull is fail-soft
#  regardless, and a student with no gws/Google account at all still gets a completed, if empty,
#  vault rather than a crash — cal-vault-pull.py marks each unavailable source in its manifest.)
#  That is why this calls the _optional entry point and not require_gws_credentials.
# ⚖ 2026-08-15: was a hand-rolled `[ -s "$GWS_CREDS" ]` block, one of eleven identical copies —
# now the shared helper (gws-auth.lib.sh, sourced at the top). Two things change: `[ -s ]` passed a
# whitespace-only or corrupt file and exported it anyway, and the absence was SILENT. The helper
# validates, and names the absence in one non-fatal line. ⛔ Do not re-inline it.
load_gws_credentials_optional cal-vault

# ── PRE-FLIGHT (warn-only; the pull degrades gracefully + marks sources failed) ──
# RETRY the gws pre-flight (3x/4s) before declaring failure — a single getProfile can fail on a
# TRANSIENT blip (token mid-refresh, momentary API hiccup) rather than a real outage.
_GWS_PREFLIGHT_OK=0
for _gws_try in 1 2 3; do
  if "$GWS_BIN" gmail users getProfile --params '{"userId":"me"}' >/dev/null 2>&1; then _GWS_PREFLIGHT_OK=1; break; fi
  if [ "$_gws_try" -lt 3 ]; then echo "[gws] pre-flight attempt $_gws_try failed — retry in 4s…"; sleep 4; fi
done
if [ "$_GWS_PREFLIGHT_OK" -ne 1 ]; then
  echo "[cal-vault] WARN: gws pre-flight failed (or gws is not installed) — sources will be marked failed this run."
fi

python3 "$CODE_ROOT/system/tools/cal-vault-pull.py" "$@"; RC=$?

# ── STATUS TILE EMIT — cal-vault is a daily cron-scheduled job, not a Pulse job; stale_after_s=86400
#    (24h) for a health sweeper to watch this tile for staleness instead of tracking a heartbeat. ──
_NOW="$(date -u +"%Y-%m-%dT%H:%M:%S+00:00")"
_STATUS_DIR="$DRIVE/state/status"
_TILE="$_STATUS_DIR/cal-vault.json"
_STATUS_STR="$( [ "$RC" -eq 0 ] && echo "OK" || echo "ERROR" )"
_SUMMARY="$( [ "$RC" -eq 0 ] && echo "cal-vault pull ok" || echo "cal-vault pull failed (rc=$RC)" )"
python3 -c "
import json, os, sys
d={'schema_version':1,'emit_mode':'manual','last_run':'$_NOW','rc':$RC,'stale_after_s':86400,'status':'$_STATUS_STR','summary':'$_SUMMARY','no_pulse':True}
tmp='$_TILE.tmp'
os.makedirs(os.path.dirname('$_TILE'), exist_ok=True)
json.dump(d,open(tmp,'w'),indent=2)
os.replace(tmp,'$_TILE')
" 2>/dev/null || echo "[cal-vault] WARN: status tile write failed (non-fatal)"

# ── CHAIN → STAGE 2: the analysis panel runs the moment the pull lands a vault ──
# (cal-vault-pull exits 0 whenever the vault was written, even with partial sources — the
#  manifest records any failures; the panel reads the manifest and works with what's there.)
if [ "$RC" -eq 0 ]; then
  echo "[cal-vault] pull ok — chaining Stage 2 (analysis panel)…"
  bash "$CODE_ROOT/system/tools/cal-analyze-run.sh" "$@"
else
  echo "[cal-vault] pull rc=$RC — skipping Stage 2 (no/partial vault)."
fi
exit "$RC"
