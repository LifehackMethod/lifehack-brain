#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# planning-health-run.sh — READ-ONLY calendar health check WRITE-cadence (Pulse). Off the jig.
#
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: refreshes state/status/planning.json by running planning-health.py (READ-ONLY — flags
#      timed-event conflicts + unconfirmed invites over a 7-day forward window via safe_calendar.py;
#      NO LLM, no claude -p, no writes to any item store). Without a cadence the tile goes stale and
#      the health dead-man trips.
# GUARDS: single-instance lock. gws auth is KEYCHAIN-FREE + isolated so a headless run can NEVER
#      touch the interactive login keychain. NO claude token. Writes ONLY state/status/planning.json
#      (via planning-health.py's own atomic tile writer) + a machine-local proof.
# REDIRECT: state/status/planning.json (written by the python); machine-local proof
#      $OUT_DIR/last-run.json (trap) + $OUT_DIR/last-write.log (the run's output).
# ⚖ PORT NOTE: this wrapper did not exist before 2026-08-24. `system/pulse-config.md` was invoking
#      planning-health.py DIRECTLY, with no `require_gws_credentials` preflight, so the job inherited
#      the bare scheduler environment and every gws call inside safe_calendar.py failed with
#      `error[auth]: Access denied. No credentials provided.` — NOT an expired credential; the same
#      creds file worked fine from an interactive shell with the three GOOGLE_WORKSPACE_CLI_* vars
#      exported. `pulse-config.md`'s own comment at the old invocation line already named this gap
#      ("No *-run.sh wrapper exists yet for this job... a future lane can add
#      system/tools/planning-health-run.sh"). This file is that lane, built by copying
#      calendar-store-sync-run.sh's credential-export shape rather than inventing a new one.
# ─────────────────────────────────────────────────────────────────────────────
set -eo pipefail

SUBSYSTEM_NAME="planning-health"
STALE_AFTER_HOURS="8"                              # own absence horizon (6h cadence; buffer above it)
WATCHDOG_SECS="120"                                # a 7-day-window read-only pull; budget generously
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# The ONE headless-gws credential preflight (require_gws_credentials) — same shared function
# calendar-store-sync-run.sh and tasks-store-sync-run.sh use, so the rc=75 stand-down contract
# cannot drift between copies. A missing library is a REAL defect (exit 1), never a stand-down.
. "$CODE_ROOT/system/tools/gws-auth.lib.sh" || {
  echo "[$SUBSYSTEM_NAME] FATAL: cannot source $CODE_ROOT/system/tools/gws-auth.lib.sh"; exit 1; }

DRIVE="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
if [ -z "$DRIVE" ]; then
  echo "[$SUBSYSTEM_NAME] no data root set — nothing to check into. Set one: python3 shared/brain_root.py --set <folder>"
  exit 2
fi

OUT_DIR="$HOME/.local/share/lifehack/${SUBSYSTEM_NAME}"
STATUS_ARTIFACT="$OUT_DIR/last-run.json"
WORKLOG="$OUT_DIR/last-write.log"
mkdir -p "$OUT_DIR" 2>/dev/null || true

LOCKDIR="/tmp/claudeops-${SUBSYSTEM_NAME}.lock"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  _lock_mtime="$(stat -c %Y "$LOCKDIR" 2>/dev/null || stat -f %m "$LOCKDIR" 2>/dev/null || echo 0)"
  case "$_lock_mtime" in ''|*[!0-9]*) _lock_mtime=0 ;; esac
  if [ -d "$LOCKDIR" ] && [ "$(( $(date +%s) - _lock_mtime ))" -gt 1200 ]; then
    echo "[$SUBSYSTEM_NAME] stale lock (>20m) — stealing."; rm -rf "$LOCKDIR"; mkdir "$LOCKDIR" 2>/dev/null || exit 0
  else
    echo "[$SUBSYSTEM_NAME] another run in progress — skip this tick."; exit 0
  fi
fi

RC=1
_on_exit() {
  printf '{"subsystem":"%s","rc":%s,"ts":"%s","stale_after_h":%s}\n' \
    "$SUBSYSTEM_NAME" "$RC" "$(date -u +%FT%TZ)" "$STALE_AFTER_HOURS" > "$STATUS_ARTIFACT" 2>/dev/null || true
  # rc=75 = STOOD DOWN (no gws creds configured yet) — the job's own preflight declined to run,
  # not a failure; PERMANENT-BY-DESIGN for a student with no Google account, so it fires on every
  # future dispatch until credentials are configured. Paging on it would just move the noise from
  # "every tick" to "every day forever," which is worse than the red tile this fix replaces.
  # DEFAULT TO SILENCE, matching calendar-store-sync-run.sh / tasks-store-sync-run.sh's identical
  # convention. Genuine failures (anything else non-zero) still page below, unchanged.
  if [ "$RC" -ne 0 ] && [ "$RC" -ne 75 ]; then
    bash "$CODE_ROOT/shared/notify/notify-send.sh" --source "$SUBSYSTEM_NAME" --tags warning --priority critical \
      --title "⚠️ planning-health check failed" \
      --message "planning-health.py errored (rc=$RC) — calendar health tile not refreshing. See $STATUS_ARTIFACT." 2>/dev/null || true
  fi
  rm -rf "$LOCKDIR" 2>/dev/null || true
}
trap _on_exit EXIT INT TERM

# ── GWS (GOOGLE) HEADLESS AUTH — keychain-free, isolated. NO claude token: the read path is
#    MECHANICAL (safe_calendar --redact + a deterministic tile writer). One-time per machine:
#      gws auth export --unmasked > ~/.config/lifehack/gws-credentials.json && chmod 600 "$_"
#      mkdir -p ~/.config/lifehack/gws-cron
#    A student with no Google account / no gws binary stands down here (rc=75), same as the store
#    syncs — this job legitimately cannot do its Google-backed work without it, and planning-health.py
#    treats "gws never reaches it" the same as any other real read failure once cal ids ARE
#    configured, so it belongs on the REQUIRED (not optional) side of gws-auth.lib.sh's contract.
# No creds file is true on day one of every install, and PERMANENTLY true for a student with no
# Google account — not a runner fault. rc=75 = "this job's own preflight declined to run this tick"
# (system/pulse-config.md's exit-code contract) — Pulse counts it as `skipped`, never toward the
# 3-strike circuit breaker. `RC=75` FIRST so the EXIT trap records the stand-down, THEN exit — the
# helper deliberately does not terminate on our behalf. ⛔ Do not re-inline it.
require_gws_credentials "$SUBSYSTEM_NAME" || { RC=75; exit 75; }

# ── THE WORK: run the read-only calendar health check. Watchdog kill-9s a hung pull. Output →
#    WORKLOG. Exit 0 = success (including "checked, clean" and "not configured"); non-zero ONLY
#    when the checker itself hit a real read failure (→ trap buzzes). ──
do_work() {
  python3 "$CODE_ROOT/system/tools/planning-health.py" > "$WORKLOG" 2>&1
}
do_work & WORK_PID=$!
( sleep "$WATCHDOG_SECS"; kill -9 "$WORK_PID" 2>/dev/null ) & WD_PID=$!
if wait "$WORK_PID" 2>/dev/null; then RC=0; else RC=$?; fi
kill "$WD_PID" 2>/dev/null || true
wait "$WD_PID" 2>/dev/null || true
[ -f "$WORKLOG" ] && cat "$WORKLOG"

echo "[$SUBSYSTEM_NAME] done (rc=$RC)."
exit "$RC"
