#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# email-summary-write-run.sh — CT-2 v2 email WRITE-cadence (Pulse). Off the subsystem jig.
#
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: nothing else refreshes the v2 faithful-thread store — the old email-summary-sync cron is
#      the v1 path and is gated OFF. Without a write cadence the store goes stale and the S-1
#      read-side dead-man trips DEGRADED (→ phone buzz) in ~36h. This runner pulls new mail into
#      threads-v2/ via `email_summary_sync.py --write-v2` (MECHANICAL — no LLM, no claude -p) and,
#      on success, stamps the shared health tile so write-health is legible.
# GUARDS: single-instance lock (a second overlapping tick must not double-pull). gws auth is
#      KEYCHAIN-FREE + isolated so a headless run can NEVER touch the interactive `gws` keychain.
#      NO claude token (the write path is mechanical). Writes ONLY: the v2 store (via the janitor's
#      own HARD-guarded writer), the health tile (via the janitor), a machine-local {rc,ts} proof.
#      A write ERROR (e.g. dead auth) buzzes the phone IMMEDIATELY.
# REDIRECT: v2 store threads-v2/ + tile state/status/email-summary.json (both written by the python);
#      machine-local proof $OUT_DIR/last-run.json (trap) + $OUT_DIR/last-write.log (the run's output).
# ⚖ PORT NOTE: donor's PRIMARY-machine gate (state/primary-machine marker election between two Macs)
#      is DELETED, not translated — a student has one computer, so there is nothing to elect between.
#      The single-instance LOCK below is unrelated and is kept (it guards against two overlapping
#      ticks on the SAME machine, which is still possible with one computer). This runner has no
#      caller yet — DEST has no scheduler/cron scaffold (that lands separately); it is ported so it
#      is correct and callable the moment one exists. A student with no `gws` binary / no Google
#      account gets a clear FATAL line below, never a stack trace or a silent no-op success.
# ─────────────────────────────────────────────────────────────────────────────
set -eo pipefail

# ── Identity + residency ──
SUBSYSTEM_NAME="email-summary-write"
STALE_AFTER_HOURS="4"                              # own absence horizon — just over one 3h cadence, so a SINGLE
                                                   #   missed run surfaces on the next tick (not after 4 misses)
WATCHDOG_SECS="900"                                # a full --write-v2 touches Gmail per label; budget generously
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"  # residency: code from clone

# The data root, through the ONE resolver — never a hardcoded personal Drive path. A student with
# no data root set gets a clear, explicit message and a clean non-zero exit, never a stack trace.
DRIVE="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
if [ -z "$DRIVE" ]; then
  echo "[$SUBSYSTEM_NAME] no data root set — nothing to sync into. Set one: python3 shared/brain_root.py --set <folder>"
  exit 2
fi

OUT_DIR="$HOME/.local/share/lifehack/${SUBSYSTEM_NAME}"        # machine-local, OUTSIDE the indexed vault
STATUS_ARTIFACT="$OUT_DIR/last-run.json"                        # {rc, ts} proof — written by the trap
mkdir -p "$OUT_DIR" 2>/dev/null || true

# ── Single-instance lock (a write run can take minutes; a second Pulse tick must not double-pull). ──
LOCKDIR="/tmp/lifehack-${SUBSYSTEM_NAME}.lock"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  if [ -d "$LOCKDIR" ] && [ "$(( $(date +%s) - $(stat -f %m "$LOCKDIR" 2>/dev/null || echo 0) ))" -gt 1200 ]; then
    echo "[$SUBSYSTEM_NAME] stale lock (>20m) — stealing."; rm -rf "$LOCKDIR"; mkdir "$LOCKDIR" 2>/dev/null || exit 0
  else
    echo "[$SUBSYSTEM_NAME] another run in progress — skip this tick."; exit 0
  fi
fi

# ── ONE exit handler: write the {rc,ts} proof, buzz the phone on a real FAILURE, clear the lock — on ANY
#    exit (success, set -e death, watchdog kill). A write ERROR (RC≠0) pages critical IMMEDIATELY so a
#    broken-auth runner reaches the person's phone this tick, not after 3 Pulse-breaker strikes. ──
RC=1
_on_exit() {
  printf '{"subsystem":"%s","rc":%s,"ts":"%s","stale_after_h":%s}\n' \
    "$SUBSYSTEM_NAME" "$RC" "$(date -u +%FT%TZ)" "$STALE_AFTER_HOURS" > "$STATUS_ARTIFACT" 2>/dev/null || true
  # rc=75 = STOOD DOWN (no gws creds configured yet) — the job's own preflight declined to run,
  # not a failure; PERMANENT-BY-DESIGN for a student with no Google account, so it fires on every
  # future dispatch until credentials are configured. Paging on it — even once — would just move
  # the noise from "every tick" to "every day forever," which is worse than the red tile this fix
  # replaces. DEFAULT TO SILENCE, matching the established convention: cal-health.py /
  # backlog-health.py's own "not configured" branch pages nobody, and pulse.sh's own rc=75 handling
  # counts it `skipped` with no notify-send call of its own. Genuine failures (anything else
  # non-zero) still page below, unchanged.
  if [ "$RC" -ne 0 ] && [ "$RC" -ne 75 ]; then
    bash "$CODE_ROOT/shared/notify/notify-send.sh" --source "$SUBSYSTEM_NAME" --tags warning --priority critical \
      --title "⚠️ email write-cadence failed" \
      --message "email_summary_sync --write-v2 errored (rc=$RC) — v2 store not refreshing. See $STATUS_ARTIFACT." 2>/dev/null || true
  fi
  rm -rf "$LOCKDIR" 2>/dev/null || true
}
trap _on_exit EXIT INT TERM

# ── GWS (GOOGLE) HEADLESS AUTH — keychain-free, isolated. NO claude token: the v2 write path is
#    MECHANICAL (email_convert quote/sig strip), it never spawns claude -p. A headless/cron session
#    cannot unlock the interactive login keychain gws normally uses, so this points gws at an
#    isolated file-backed config instead. ONE-TIME setup per machine (from an interactive session):
#      gws auth export --unmasked > ~/.config/lifehack/gws-credentials.json && chmod 600 "$_"
#      mkdir -p ~/.config/lifehack/gws-cron
#    A student with no Google account / no gws binary at all fails here with a clear FATAL line,
#    never a stack trace or a silent success.
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
  echo "[$SUBSYSTEM_NAME] STOOD DOWN: no gws creds at $GWS_CREDS — this needs Google Workspace CLI (gws) set up first. Run 'gws auth export --unmasked > $GWS_CREDS' (chmod 600) from an interactive session, then 'mkdir -p ~/.config/lifehack/gws-cron' to enable this job. See INSTALL.md."
  RC=75; exit 75
fi

# ── PRE-FLIGHT: confirm gws auth is HEALTHY via the isolated creds before pulling. RETRY 3×4s so a
#    transient token-refresh blip becomes a brief wait, not a hard failure. A real dead-auth still buzzes
#    (RC=2 → the trap pages). SAFE: the isolated config never touches the interactive login keychain. ──
GWS_BIN="$(command -v gws 2>/dev/null || echo /opt/homebrew/bin/gws)"
PREFLIGHT_OK=0
for _attempt in 1 2 3; do
  if "$GWS_BIN" gmail users getProfile --params '{"userId":"me"}' >/dev/null 2>&1; then
    PREFLIGHT_OK=1; break
  fi
  [ "$_attempt" -lt 3 ] && { echo "[$SUBSYSTEM_NAME] gws pre-flight attempt $_attempt failed — retrying in 4s…"; sleep 4; }
done
if [ "$PREFLIGHT_OK" -ne 1 ]; then
  echo "[$SUBSYSTEM_NAME] FATAL: gws pre-flight failed 3× — Google auth not healthy via isolated creds ($GWS_CREDS), or gws is not installed. See INSTALL.md."
  RC=2; exit 2
fi

# ── THE WORK: refresh the v2 store (mechanical, delta-only — write_v2 skips unchanged threads). Wrapped in a
#    watchdog: a hung network pull is kill-9'd so the runner can't wedge the lock. Output → WORKLOG (machine-
#    local) so we can read the run's error count after. Exit 0 = a successful pull (found-result); non-zero
#    ONLY when the janitor itself broke (→ the trap buzzes + Pulse breaker counts). NOTE: stdout is REDIRECTED
#    (not piped) so `wait` returns the python exit code, never a pipe's tail. ──
WORKLOG="$OUT_DIR/last-write.log"
do_work() {
  python3 "$CODE_ROOT/shared/tools/email_summary_sync.py" --write-v2 --verbose > "$WORKLOG" 2>&1
}

do_work & WORK_PID=$!
( sleep "$WATCHDOG_SECS"; kill -9 "$WORK_PID" 2>/dev/null ) & WD_PID=$!
if wait "$WORK_PID" 2>/dev/null; then RC=0; else RC=$?; fi
kill "$WD_PID" 2>/dev/null || true
wait "$WD_PID" 2>/dev/null || true
[ -f "$WORKLOG" ] && cat "$WORKLOG"   # surface the work output to the Pulse log

# ── On SUCCESS → stamp write-health into the shared tile (a durable last_write_run; PRESERVES any DEGRADED
#    the S-1 dead-man set — a good write never masks a stale/zeroed store). Best-effort: a tile-stamp hiccup
#    must not fail an otherwise-successful write. ──
if [ "$RC" -eq 0 ]; then
  # write_v2 exits 0 even if SOME threads errored — its summary line carries "errors=N". Read it once,
  # feed it to the tile stamp AND use it for the partial-failure buzz below.
  _ERRS="$(grep -oE 'errors=[0-9]+' "$WORKLOG" 2>/dev/null | tail -1 | grep -oE '[0-9]+' || echo 0)"
  python3 "$CODE_ROOT/shared/tools/email_summary_sync.py" --stamp-write-ok --write-errors "${_ERRS:-0}" 2>/dev/null || \
    echo "[$SUBSYSTEM_NAME] WARNING: write succeeded but tile-stamp failed (non-fatal)."

  # ── H2.1 PARTIAL-failure visibility: N>0 → the store is only partially refreshed → a WARNING-priority
  #    buzz (NOT critical: a transient per-thread hiccup must never trip Pulse's breaker or wake anyone at
  #    3am; the S-1 dead-man still backstops a real stall). ──
  if [ "${_ERRS:-0}" -gt 0 ]; then
    bash "$CODE_ROOT/shared/notify/notify-send.sh" --source "$SUBSYSTEM_NAME" --tags mailbox,warning \
      --title "📭 email write PARTIAL" \
      --message "v2 write finished with ${_ERRS} thread error(s) — store only partially refreshed. See $WORKLOG." 2>/dev/null || true
    echo "[$SUBSYSTEM_NAME] partial refresh: ${_ERRS} thread error(s) → warning buzz sent."
  fi
fi

echo "[$SUBSYSTEM_NAME] done (rc=$RC)."
exit "$RC"
