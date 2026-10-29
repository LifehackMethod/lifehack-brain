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
#      A write ERROR no longer texts from here (2.5c, 2026-10-27): job-run.sh is the one alarm.
# REDIRECT: v2 store threads-v2/ + tile state/status/email-summary.json (both written by the python);
#      machine-local proof $OUT_DIR/last-run.json (trap) + $OUT_DIR/last-write.log (the run's output).
# ⚖ PORT NOTE: donor's PRIMARY-machine gate (state/primary-machine marker election between two machines)
#      is DELETED, not translated — a student has one computer, so there is nothing to elect between.
#      The single-instance LOCK below is unrelated and is kept (it guards against two overlapping
#      ticks on the SAME machine, which is still possible with one computer). ⚠ CORRECTED
#      2026-08-15 (T9.7d): this used to deny that DEST had any scheduler or cron scaffold, and to
#      say this runner had no
#      caller. Both are false — `system/pulse-config.md` carries a real `email-summary-write`
#      row (10800s) invoking this file. A student with no `gws` binary / no Google
#      account gets a clear FATAL line below, never a stack trace or a silent no-op success.
# ─────────────────────────────────────────────────────────────────────────────
set -eo pipefail

# ── Identity + residency ──
SUBSYSTEM_NAME="email-summary-write"
STALE_AFTER_HOURS="4"                              # own absence horizon — just over one 3h cadence, so a SINGLE
                                                   #   missed run surfaces on the next tick (not after 4 misses)
WATCHDOG_SECS="${EMAIL_WRITE_WATCHDOG_SECS:-900}"                                # a full --write-v2 touches Gmail per label; budget generously
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"  # residency: code from clone

# The ONE headless-gws credential preflight (require_gws_credentials) — shared with the ten other
# runners that reach Google, so the rc=75 stand-down contract cannot drift between copies again.
# A missing library is a REAL defect (exit 1), never a stand-down.
. "$CODE_ROOT/system/tools/gws-auth.lib.sh" || {
  echo "[$SUBSYSTEM_NAME] FATAL: cannot source $CODE_ROOT/system/tools/gws-auth.lib.sh"; exit 1; }
. "$CODE_ROOT/system/tools/status-tile.lib.sh" || {
  echo "[$SUBSYSTEM_NAME] FATAL: cannot source $CODE_ROOT/system/tools/status-tile.lib.sh"; exit 1; }

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
LOCKDIR="${LIFEHACK_RUNNER_LOCK_ROOT:-/tmp}/claudeops-${SUBSYSTEM_NAME}.lock"   # LIFEHACK_RUNNER_LOCK_ROOT: TEST-ONLY seam (job-sim.sh)
. "$CODE_ROOT/system/tools/runner-lock.lib.sh" || { echo "FATAL: cannot source runner-lock.lib.sh" >&2; exit 1; }
# 5.9(h): the lock records its owner pid. A dead owner's lock is taken at once; a LIVE owner is a stand-down (75), never a 0;
# a lock that is present but unreadable is refused and named (1).
runner_lock_acquire "$LOCKDIR" 1200 "$SUBSYSTEM_NAME" || exit $?

# ── ONE exit handler: write the {rc,ts} proof, buzz the phone on a real FAILURE, clear the lock — on ANY
#    exit (success, set -e death, watchdog kill). No text from here (2.5c): job-run.sh is the one alarm. ──
RC=1
_on_exit() {
  printf '{"subsystem":"%s","rc":%s,"ts":"%s","stale_after_h":%s}\n' \
    "$SUBSYSTEM_NAME" "$RC" "$(date -u +%FT%TZ)" "$STALE_AFTER_HOURS" > "$STATUS_ARTIFACT" || echo "[$SUBSYSTEM_NAME] FAILED to write the status artifact $STATUS_ARTIFACT" >&2
  # 2026-10-27 (self-monitoring 2.5c): this runner no longer sends its own text. job-run.sh is now the ONE
  # alarm for this job (it pages on the 2nd consecutive miss and sends the recovery). The trap still writes
  # last-run.json and the Drive status tile, so the failure stays visible; rc=75 (no gws creds) is a stand-down.
  # Drive-visible status tile (state/status/email-summary-write.json) — emitted on EVERY outcome so
  # system-health never renders this job NO-TILE while it is silently dying (the 2026-08-27 failure).
  write_status_tile "$SUBSYSTEM_NAME" "$RC" $(( STALE_AFTER_HOURS * 3600 )) \
    "email v2 store write ok" "email v2 store write failed — store not refreshing" \
    "gws (Google) credentials not configured"
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
GWS_CREDS="$GWS_CREDS_FILE"   # path the helper actually looked at — quoted in the pre-flight FATAL below

# ── PRE-FLIGHT: confirm gws auth is HEALTHY via the isolated creds before pulling. RETRY 3×4s so a
#    transient token-refresh blip becomes a brief wait, not a hard failure. A real dead-auth still buzzes
#    (RC=2 → the trap pages). SAFE: the isolated config never touches the interactive login keychain. ──
# 5.4: the probe itself is the shared fetch's (--preflight = getProfile); this runner holds no raw Gmail call.
PREFLIGHT_OK=0
for _attempt in 1 2 3; do
  if python3 "$CODE_ROOT/shared/tools/email_fetch.py" --preflight >/dev/null; then
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
# EMAIL_WRITE_LIMIT (optional): cap a run at the first N threads. Set on the job's row in
# system/pulse-config.md. A capped run never cold-sweeps (email_summary_sync._should_cold_sweep).
do_work() {
  python3 "$CODE_ROOT/shared/tools/email_summary_sync.py" --write-v2 --verbose \
    ${EMAIL_WRITE_LIMIT:+--limit "$EMAIL_WRITE_LIMIT"} > "$WORKLOG" 2>&1
}

# 5.10(4): job control (set -m) puts the work in its OWN process group, so the watchdog kills the group (-PID), python included;
# killing only the subshell used to leave the python orphaned. Job control is switched off again straight after the launch.
set -m
do_work & WORK_PID=$!
( sleep "$WATCHDOG_SECS"; kill -9 -- "-$WORK_PID" 2>/dev/null || kill -9 "$WORK_PID" 2>/dev/null ) & WD_PID=$!
set +m
if wait "$WORK_PID" 2>/dev/null; then RC=0; else RC=$?; fi
pkill -P "$WD_PID" 2>/dev/null; kill "$WD_PID" 2>/dev/null || true   # the watchdog subshell AND its sleep (else a 900 s sleep leaks per run)
wait "$WD_PID" 2>/dev/null || true
[ -f "$WORKLOG" ] && cat "$WORKLOG"   # surface the work output to the Pulse log

# ── 5.9(c): the run's SUMMARY LINE decides success, not the janitor's exit code. write_v2 exits 0 even if SOME threads errored; its
#    summary line carries "errors=N". A missing summary line is a FAILURE (the run did not say how it went), never "zero errors";
#    errors=[1-9] fails the run. The tile stamp below still records the count either way. ──
if [ "$RC" -eq 0 ]; then
  if ! _SUMLINE="$(grep -E 'v2 write DONE' "$WORKLOG" | tail -1)"; then _SUMLINE=""; fi
  _ERRS=""
  if [ -n "$_SUMLINE" ]; then
    if ! _ERRS="$(printf '%s\n' "$_SUMLINE" | grep -oE 'errors=[0-9]+' | tail -1 | grep -oE '[0-9]+')"; then _ERRS=""; fi
  fi
  if [ -z "$_SUMLINE" ]; then
    echo "[$SUBSYSTEM_NAME] FAILED: no 'v2 write DONE' summary line in $WORKLOG — a missing summary is a failure, not zero errors." >&2
    RC=1
  elif [ -z "$_ERRS" ]; then
    echo "[$SUBSYSTEM_NAME] FAILED: the summary line has no errors=N field: $_SUMLINE" >&2
    RC=1
  elif [ "$_ERRS" -ge 1 ]; then
    echo "[$SUBSYSTEM_NAME] FAILED: the write finished with errors=$_ERRS — $_SUMLINE" >&2
    RC=1
  fi
  # Stamp write-health into the shared tile (a durable last_write_run; PRESERVES any DEGRADED the S-1 dead-man set). A tile-stamp hiccup is
  # named on stderr but does not by itself fail an otherwise-successful write.
  if [ -n "$_ERRS" ]; then
    python3 "$CODE_ROOT/shared/tools/email_summary_sync.py" --stamp-write-ok --write-errors "$_ERRS" || \
      echo "[$SUBSYSTEM_NAME] WARNING: the write finished but the tile-stamp failed (rc=$?)." >&2
  fi
  # 2026-10-27 (2.5c): job-run.sh is the one alarm; a partial refresh now FAILS the run above and is named in the log.
fi

echo "[$SUBSYSTEM_NAME] done (rc=$RC)."
exit "$RC"
