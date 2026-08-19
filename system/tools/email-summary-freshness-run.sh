#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# email-summary-freshness-run.sh — S-1 per-scope freshness DEAD-MAN (Pulse). Off the subsystem jig.
#
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: reads the v2 faithful-thread store (LOCAL files only — NO gws, NO auth) and emits the
#      UP/DEGRADED health tile the read adapter's _store_is_stale() consults, so a store miss can tell a
#      real coverage gap from sync-lag. INDEPENDENT of the janitor so it fires even when the janitor is
#      down/disabled — the whole point of a dead-man.
# GUARDS: a producer — writes ONLY its status tile + a machine-local proof artifact; no Gmail, no state.
# REDIRECT: tile state/status/email-summary.json (written by the python); machine-local proof below.
# ⚖ PORT NOTE: donor's marker-driven single-writer machine gate (state/primary-machine, two-machine
#      election) is DELETED, not translated — a student has one computer. ⚠ CORRECTED 2026-08-15
#      (T9.7d): this used to deny that DEST had any scheduler or cron scaffold, and to say this
#      runner had no caller. Both are
#      false — `system/pulse-config.md` carries a real `email-summary-freshness` row (3600s)
#      invoking this file.
# ─────────────────────────────────────────────────────────────────────────────
set -eo pipefail

# ── Identity + residency ──
SUBSYSTEM_NAME="email-summary-freshness"
STALE_AFTER_HOURS="6"                              # the runner's own absence horizon (Pulse cadence ~ hourly)
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"  # residency: code from clone

# The data root, through the ONE resolver — never a hardcoded personal Drive path.
DRIVE="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
if [ -z "$DRIVE" ]; then
  echo "[$SUBSYSTEM_NAME] no data root set — nothing to check. Set one: python3 shared/brain_root.py --set <folder>"
  exit 2
fi

OUT_DIR="$HOME/.local/share/lifehack/${SUBSYSTEM_NAME}"        # machine-local, OUTSIDE the indexed vault
STATUS_ARTIFACT="$OUT_DIR/last-run.json"                        # {rc, ts} proof — written by the trap
mkdir -p "$OUT_DIR" 2>/dev/null || true

# ── Single-instance lock ──
LOCKDIR="/tmp/lifehack-${SUBSYSTEM_NAME}.lock"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  if [ -d "$LOCKDIR" ] && [ "$(( $(date +%s) - $(stat -f %m "$LOCKDIR" 2>/dev/null || echo 0) ))" -gt 900 ]; then
    rm -rf "$LOCKDIR"; mkdir "$LOCKDIR" 2>/dev/null || exit 0
  else
    echo "[$SUBSYSTEM_NAME] another run in progress — skip."; exit 0
  fi
fi

# ── ONE exit handler: write the {rc,ts} proof AND clear the lock on ANY exit (success, set -e death, kill). ──
RC=1
_on_exit() {
  printf '{"subsystem":"%s","rc":%s,"ts":"%s","stale_after_h":%s}\n' \
    "$SUBSYSTEM_NAME" "$RC" "$(date -u +%FT%TZ)" "$STALE_AFTER_HOURS" > "$STATUS_ARTIFACT" 2>/dev/null || true
  rm -rf "$LOCKDIR" 2>/dev/null || true
}
trap _on_exit EXIT INT TERM

# ── THE WORK: run the freshness dead-man (it emits the UP/DEGRADED tile itself). Exit 0 on UP AND
#    DEGRADED (the TILE carries the signal); non-zero ONLY if the check itself throws. ──
do_work() {
  python3 "$CODE_ROOT/shared/tools/email_summary_sync.py" --freshness-check
}

do_work && RC=0 || RC=$?

# ── (A) DEGRADED → PHONE (NTFY). This is the whole point: a stale / zeroed store must reach the
#    person's phone, not just the dashboard. DEGRADED is exit 0 (a successful detection), so it would NOT
#    hit the failure-buzz below — it needs its OWN push. notify-send.sh is governor-deduped, so an
#    hourly-repeating DEGRADED coalesces to one buzz, not a storm. Normal priority (respects quiet hours —
#    a stale store at 3am doesn't need to wake anyone; it's not an emergency). ──
TILE="$DRIVE/state/status/email-summary.json"
if [ "$RC" -eq 0 ] && [ -f "$TILE" ]; then
  _ST="$(python3 -c "import json;print(json.load(open('$TILE')).get('status',''))" 2>/dev/null || echo)"
  if [ "$_ST" = "ERROR" ] || [ "$_ST" = "DEGRADED" ]; then   # CT-4: tile now stores ERROR (emit_status enum)
    _RSN="$(python3 -c "import json;print(json.load(open('$TILE')).get('reason','')[:180])" 2>/dev/null || echo)"
    bash "$CODE_ROOT/shared/notify/notify-send.sh" --source "$SUBSYSTEM_NAME" --tags mailbox,warning \
      --title "📭 Email store DEGRADED" --message "${_RSN:-store is stale or a scope is empty}" 2>/dev/null || true
    echo "[$SUBSYSTEM_NAME] DEGRADED → phone push sent: ${_RSN}"
  fi
fi

# ── Active failure-buzz: a real check FAILURE (the tool itself broke) pages critical. ──
if [ "$RC" -ne 0 ]; then
  bash "$CODE_ROOT/shared/notify/notify-send.sh" --source "$SUBSYSTEM_NAME" --tags warning --priority critical \
    --title "⚠️ ${SUBSYSTEM_NAME} failed" \
    --message "${SUBSYSTEM_NAME} check errored (rc=$RC). See $STATUS_ARTIFACT." 2>/dev/null || true
fi

echo "[$SUBSYSTEM_NAME] done (rc=$RC)."
exit "$RC"
