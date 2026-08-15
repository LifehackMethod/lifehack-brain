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
# ⚖ PORT NOTE: donor's PRIMARY-machine gate (state/primary-machine marker election between two Macs)
#      is DELETED, not translated — a student has one computer. This runner has no caller yet — DEST
#      has no scheduler/cron scaffold (that lands separately); ported so it is correct and callable
#      the moment one exists.
# ─────────────────────────────────────────────────────────────────────────────
set -eo pipefail

SUBSYSTEM_NAME="tasks-store-sync"
STALE_AFTER_HOURS="30"                             # own absence horizon (writers run ~daily)
WATCHDOG_SECS="600"                                # a --sync pulls Google Tasks + writes records; budget generously
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

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
  if [ -d "$LOCKDIR" ] && [ "$(( $(date +%s) - $(stat -f %m "$LOCKDIR" 2>/dev/null || echo 0) ))" -gt 1200 ]; then
    echo "[$SUBSYSTEM_NAME] stale lock (>20m) — stealing."; rm -rf "$LOCKDIR"; mkdir "$LOCKDIR" 2>/dev/null || exit 0
  else
    echo "[$SUBSYSTEM_NAME] another run in progress — skip this tick."; exit 0
  fi
fi

RC=1
_on_exit() {
  printf '{"subsystem":"%s","rc":%s,"ts":"%s","stale_after_h":%s}\n' \
    "$SUBSYSTEM_NAME" "$RC" "$(date -u +%FT%TZ)" "$STALE_AFTER_HOURS" > "$STATUS_ARTIFACT" 2>/dev/null || true
  if [ "$RC" -ne 0 ]; then
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
GWS_CREDS="$HOME/.config/lifehack/gws-credentials.json"
if [ -s "$GWS_CREDS" ]; then
  export GOOGLE_WORKSPACE_CLI_CONFIG_DIR="$HOME/.config/lifehack/gws-cron"
  export GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE="$GWS_CREDS"
  export GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND=file
else
  # No creds file is true on day one of every install, and PERMANENTLY true for a student with no
  # Google account — not a runner fault. rc=75 = "this job's own preflight declined to run this
  # tick" (system/pulse-config.md's exit-code contract; matches cal-health.py / backlog-health.py's
  # identical "not configured yet" convention) — Pulse counts it as `skipped`, never toward the
  # 3-strike circuit breaker, so a permanently-unconfigured install never renders DOWN/error forever.
  echo "[$SUBSYSTEM_NAME] STOOD DOWN: no gws creds at $GWS_CREDS — export them (chmod 600) from an interactive session to enable this job. See INSTALL.md."
  RC=75; exit 75
fi

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
