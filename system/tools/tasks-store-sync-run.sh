#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# tasks-store-sync-run.sh — CT-3 Google Tasks → durable item-store WRITE-cadence (Pulse). Off the jig.
#
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: refreshes state/item-store/tasks/ by running tasks_store_sync.py --sync (MECHANICAL — pulls via
#      safe_tasks.py --redact, one durable record per task, delta-only, never-delete lifecycle; NO LLM,
#      no claude -p). Without a cadence the tasks store goes stale and the item-store dead-man trips.
# GUARDS: single-instance lock. gws auth is KEYCHAIN-FREE + isolated so a headless run can NEVER touch
#      the interactive login keychain. NO claude token. Writes ONLY the tasks item-store (via the
#      CT-1-guarded writer) + a machine-local proof. A write ERROR (e.g. dead auth) buzzes the phone
#      IMMEDIATELY (critical).
# REDIRECT: item store state/item-store/tasks/ (written by the python, behind the CT-1 HARD guard);
#      machine-local proof $OUT_DIR/last-run.json (trap) + $OUT_DIR/last-write.log (the run's output).
# ⚖ PORT NOTE: donor's PRIMARY-machine gate (state/primary-machine marker election between two machines)
#      is DELETED, not translated — a student has one computer. ⚠ CORRECTED 2026-08-15 (T9.7d):
#      this used to deny that DEST had any scheduler or cron scaffold, and to say this runner had
#      no caller. Both are
#      false — `system/pulse-config.md` carries a real `tasks-store-sync` row (86400s) invoking
#      this file.
# ─────────────────────────────────────────────────────────────────────────────
set -eo pipefail

SUBSYSTEM_NAME="tasks-store-sync"
STALE_AFTER_HOURS="30"                             # own absence horizon (writers run ~daily)
WATCHDOG_SECS="600"                                # a --sync pulls Google Tasks + writes records; budget generously
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# The ONE headless-gws credential preflight (require_gws_credentials) — shared with the ten other
# runners that reach Google, so the rc=75 stand-down contract cannot drift between copies again.
# A missing library is a REAL defect (exit 1), never a stand-down.
. "$CODE_ROOT/system/tools/gws-auth.lib.sh" || {
  echo "[$SUBSYSTEM_NAME] FATAL: cannot source $CODE_ROOT/system/tools/gws-auth.lib.sh"; exit 1; }

DRIVE="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
if [ -z "$DRIVE" ]; then
  echo "[$SUBSYSTEM_NAME] no data root set — nothing to sync into. Set one: python3 shared/brain_root.py --set <folder>"
  exit 2
fi

OUT_DIR="$HOME/.local/share/lifehack/${SUBSYSTEM_NAME}"
STATUS_ARTIFACT="$OUT_DIR/last-run.json"
WORKLOG="$OUT_DIR/last-write.log"
mkdir -p "$OUT_DIR" 2>/dev/null || true

LOCKDIR="/tmp/lifehack-${SUBSYSTEM_NAME}.lock"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  if [ -d "$LOCKDIR" ] && [ "$(( $(date +%s) - $(stat -c %Y "$LOCKDIR" 2>/dev/null || stat -f %m "$LOCKDIR" 2>/dev/null || echo 0) ))" -gt 1200 ]; then
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
  # future dispatch until credentials are configured. Paging on it — even once — would just move
  # the noise from "every tick" to "every day forever," which is worse than the red tile this fix
  # replaces. DEFAULT TO SILENCE, matching the established convention: planning-health.py /
  # backlog-health.py's own "not configured" branch pages nobody, and pulse.sh's own rc=75 handling
  # counts it `skipped` with no notify-send call of its own. Genuine failures (anything else
  # non-zero) still page below, unchanged.
  if [ "$RC" -ne 0 ] && [ "$RC" -ne 75 ]; then
    bash "$CODE_ROOT/shared/notify/notify-send.sh" --source "$SUBSYSTEM_NAME" --tags warning --priority critical \
      --title "⚠️ tasks-store sync failed" \
      --message "tasks_store_sync --sync errored (rc=$RC) — tasks store not refreshing. See $STATUS_ARTIFACT." 2>/dev/null || true
  fi
  rm -rf "$LOCKDIR" 2>/dev/null || true
}
trap _on_exit EXIT INT TERM

# ── GWS (GOOGLE) HEADLESS AUTH — keychain-free, isolated. NO claude token: the write path is
#    MECHANICAL (safe_tasks --redact + a deterministic writer). One-time per machine:
#      gws auth export --unmasked > ~/.config/lifehack/gws-credentials.json && chmod 600 "$_"
#      mkdir -p ~/.config/lifehack/gws-cron
#    A student with no Google account / no gws binary fails here with a clear FATAL line.
# No creds file is true on day one of every install, and PERMANENTLY true for a student with no
# Google account — not a runner fault. rc=75 = "this job's own preflight declined to run this
# tick" (system/pulse-config.md's exit-code contract; matches planning-health.py / backlog-health.py's
# identical "not configured yet" convention) — Pulse counts it as `skipped`, never toward the
# 3-strike circuit breaker, so a permanently-unconfigured install never renders DOWN/error forever.
# ⚖ 2026-08-15: the check itself now lives in ONE place (gws-auth.lib.sh, sourced at the top) —
# eleven runners hand-rolled it, and the `exit 3` version of this same branch survived in three
# copies after being "fixed." The helper also catches what every hand-rolled copy missed: `[ -s ]`
# passes a whitespace-only or corrupt file, which exported garbage and failed downstream instead of
# standing down. `RC=75` FIRST so the EXIT trap records the stand-down, THEN exit — the helper
# deliberately does not terminate on our behalf, for exactly this reason. ⛔ Do not re-inline it.
require_gws_credentials "$SUBSYSTEM_NAME" || { RC=75; exit 75; }

# ── PRE-FLIGHT: confirm gws auth is healthy via the isolated creds (RETRY 3×4s for a transient blip). ──
GWS_BIN="$(command -v gws 2>/dev/null || echo /opt/homebrew/bin/gws)"
PREFLIGHT_OK=0
for _attempt in 1 2 3; do
  if "$GWS_BIN" gmail users getProfile --params '{"userId":"me"}' >/dev/null 2>&1; then PREFLIGHT_OK=1; break; fi
  [ "$_attempt" -lt 3 ] && { echo "[$SUBSYSTEM_NAME] gws pre-flight attempt $_attempt failed — retry in 4s…"; sleep 4; }
done
if [ "$PREFLIGHT_OK" -ne 1 ]; then
  echo "[$SUBSYSTEM_NAME] FATAL: gws pre-flight failed 3× — Google auth not healthy via isolated creds, or gws is not installed."
  RC=2; exit 2
fi

# ── THE WORK: refresh the tasks store (mechanical, delta-only). Watchdog kill-9s a hung pull. Output →
#    WORKLOG. Exit 0 = success; non-zero ONLY when the writer itself broke (→ trap buzzes). ──
do_work() {
  python3 "$CODE_ROOT/shared/tools/tasks_store_sync.py" --sync --verbose > "$WORKLOG" 2>&1
}
do_work & WORK_PID=$!
( sleep "$WATCHDOG_SECS"; kill -9 "$WORK_PID" 2>/dev/null ) & WD_PID=$!
if wait "$WORK_PID" 2>/dev/null; then RC=0; else RC=$?; fi
kill "$WD_PID" 2>/dev/null || true
wait "$WD_PID" 2>/dev/null || true
[ -f "$WORKLOG" ] && cat "$WORKLOG"

echo "[$SUBSYSTEM_NAME] done (rc=$RC)."
exit "$RC"
