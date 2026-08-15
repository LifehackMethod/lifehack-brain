#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# item-store-freshness-run.sh — CT-3 item-store freshness DEAD-MAN (Pulse). Off the subsystem jig.
#
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: reads state/item-store/{tasks,calendar}/ (LOCAL files only — NO gws, NO auth) and emits the
#      item-store health tile via emit_status.py. ERROR (Helm-red + phone buzz) when a tracked item_type
#      has 0 ACTIVE records (a writer stopped producing / coverage hole) OR the store is stale/empty.
#      INDEPENDENT of the tasks/calendar writers so it fires even when a writer is down — the point of a dead-man.
# GUARDS: a producer — writes ONLY its status tile + a machine-local proof; no Gmail, no gws, no state mutation.
# REDIRECT: tile state/status/item-store.json (written by the python); machine-local proof below.
# ⚖ PORT NOTE: donor's marker-driven single tile-writer machine gate (state/primary-machine, two-Mac
#      election) is DELETED, not translated — a student has one computer. This runner has no caller
#      yet — DEST has no scheduler/cron scaffold (that lands separately); ported so it is correct and
#      callable the moment one exists.
# ─────────────────────────────────────────────────────────────────────────────
set -eo pipefail

SUBSYSTEM_NAME="item-store-freshness"
STALE_AFTER_HOURS="4"                              # own absence horizon (Pulse cadence ~ hourly)
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

DRIVE="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
if [ -z "$DRIVE" ]; then
  echo "[$SUBSYSTEM_NAME] no data root set — nothing to check. Set one: python3 shared/brain_root.py --set <folder>"
  exit 2
fi

OUT_DIR="$HOME/.local/share/lifehack/${SUBSYSTEM_NAME}"
STATUS_ARTIFACT="$OUT_DIR/last-run.json"
mkdir -p "$OUT_DIR" 2>/dev/null || true

LOCKDIR="/tmp/lifehack-${SUBSYSTEM_NAME}.lock"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  if [ -d "$LOCKDIR" ] && [ "$(( $(date +%s) - $(stat -f %m "$LOCKDIR" 2>/dev/null || echo 0) ))" -gt 900 ]; then
    rm -rf "$LOCKDIR"; mkdir "$LOCKDIR" 2>/dev/null || exit 0
  else
    echo "[$SUBSYSTEM_NAME] another run in progress — skip."; exit 0
  fi
fi

RC=1
_on_exit() {
  printf '{"subsystem":"%s","rc":%s,"ts":"%s","stale_after_h":%s}\n' \
    "$SUBSYSTEM_NAME" "$RC" "$(date -u +%FT%TZ)" "$STALE_AFTER_HOURS" > "$STATUS_ARTIFACT" 2>/dev/null || true
  rm -rf "$LOCKDIR" 2>/dev/null || true
}
trap _on_exit EXIT INT TERM

# ── THE WORK: emit the item-store tile. Exit 0 on OK AND ERROR (the TILE carries the signal, not the exit
#    code — Pulse's breaker never disables the watcher); non-zero ONLY if the check itself throws. ──
do_work() {
  python3 "$CODE_ROOT/shared/tools/item_store_read.py" --freshness-check
}
do_work && RC=0 || RC=$?

# ── ERROR tile → PHONE (NTFY). A zeroed/stale item-store must reach the person's phone. ERROR is exit 0
#    (a successful detection), so it needs its OWN push. Normal priority (respects quiet hours). ──
TILE="$DRIVE/state/status/item-store.json"
if [ "$RC" -eq 0 ] && [ -f "$TILE" ]; then
  _ST="$(python3 -c "import json;print(json.load(open('$TILE')).get('status',''))" 2>/dev/null || echo)"
  if [ "$_ST" = "ERROR" ]; then
    _RSN="$(python3 -c "import json;print(json.load(open('$TILE')).get('summary','')[:180])" 2>/dev/null || echo)"
    bash "$CODE_ROOT/shared/notify/notify-send.sh" --source "$SUBSYSTEM_NAME" --tags card_index,warning \
      --title "🗂️ Item store DEGRADED" --message "${_RSN:-a task/calendar type is zeroed or the store is stale}" 2>/dev/null || true
    echo "[$SUBSYSTEM_NAME] ERROR → phone push sent: ${_RSN}"
  fi
fi

# ── Active failure-buzz: the check itself broke → page critical. ──
if [ "$RC" -ne 0 ]; then
  bash "$CODE_ROOT/shared/notify/notify-send.sh" --source "$SUBSYSTEM_NAME" --tags warning --priority critical \
    --title "⚠️ ${SUBSYSTEM_NAME} failed" \
    --message "${SUBSYSTEM_NAME} check errored (rc=$RC). See $STATUS_ARTIFACT." 2>/dev/null || true
fi

echo "[$SUBSYSTEM_NAME] done (rc=$RC)."
exit "$RC"
