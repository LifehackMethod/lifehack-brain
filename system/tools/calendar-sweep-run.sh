#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: WEEKLY calendar duplicate sweep ahead of the Sunday-evening Win-the-Week ritual — same-day
#      duplicate titles, near-identical titles at the same start, new writes to legacy calendars,
#      Society events missing the [CS] Cedars-credit tag. Ported 2026-08-29 from the Cowork
#      scheduled task `calendar-weekly-sweep` (MZ ruling that day: move it under Pulse so a missed
#      Sunday is CAUGHT by system-health instead of passing silently — the Cowork copy missed
#      2026-08-23 and nothing noticed). The v1 spec is section 7 of the v1 routing rules
#      (AI-Brain-Z/80-integrations/calendar-email-docs/calendar-routing-rules.md, read-only
#      archive); the detector calendar_sweep.py is a verbatim port and mirrors those rules.
# PIPELINE (all code, NO LLM): roster (<notes>/config/calendar-sweep-roster.tsv) →
#      calendar_sweep_pull.py (per-calendar `gws calendar events list` through safe_calendar.py
#      --redact — sanitizer store-path, titles with flagged spans neutralized) → calendar_sweep.py
#      (report-only detector) → report in <notes>/desks/cal/state/sweep-reports/ + tile + one
#      normal buzz. REPORT ONLY: no write path to any calendar exists anywhere in this pipeline;
#      every finding is a proposal for the owner to rule on.
# SCHEDULING: registered as `calendar-sweep` in system/pulse-config.md ticking DAILY (86400); this
#      script self-gates ONCE PER WEEK keyed to the MOST RECENT SUNDAY (Sunday is Win-the-Week
#      eve). On Sunday's first tick it runs; a machine asleep all Sunday catches up on the next
#      tick — the stamp records which Sunday was served. Sleep-proof, never clock-pinned.
# EXIT CODES (pulse-config.md's contract): 0 ran (incl. found-findings — that is success) ·
#      75 stood down (no/unusable gws creds, or roster not configured yet) · 1 real failure
#      (pull/detector broke) — counted by Pulse's breaker · 2 no data root.
# ─────────────────────────────────────────────────────────────────────────────
set -u
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CS_LABEL="calendar-sweep"

_clog() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${CS_LABEL}: $*"; }

# The ONE shared gws preflight — never hand-rolled (see gws-auth.lib.sh's eleven-copy history).
. "$CODE_ROOT/system/tools/gws-auth.lib.sh" || {
  echo "[$CS_LABEL] FATAL: cannot source $CODE_ROOT/system/tools/gws-auth.lib.sh"; exit 1; }
require_gws_credentials "$CS_LABEL" _clog || exit 75

DATA="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
if [ -z "$DATA" ]; then
  _clog "no data root set — nothing to sweep. Set one: python3 shared/brain_root.py --set <folder>"
  exit 2
fi

ROSTER="$DATA/config/calendar-sweep-roster.tsv"
if [ ! -s "$ROSTER" ]; then
  _clog "stood down: no roster at $ROSTER — config not set up yet (seed it per INSTALL/the cal sit-down)."
  exit 75
fi

# Tile staleness: 9 days = 777600s (7*86400 weekly + 2*86400 catch-up slack).
CS_STALE_AFTER_S=777600
CS_SPAN_DAYS="${CS_SPAN_DAYS:-60}"
CS_WINDOW_DAYS="${CS_WINDOW_DAYS:-8}"

FORCE=0; DRY_RUN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --force)   FORCE=1;   shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "calendar-sweep-run: unknown arg '$1'" >&2; exit 2 ;;
  esac
done

# ─────────────────────────────────────────────────────────────────────────────
# PERIOD-IDEMPOTENT WEEKLY GATE — keyed to the MOST RECENT SUNDAY (today, if Sunday).
# Runs when that Sunday is not yet stamped; a sleep through Sunday catches up next tick.
# Stamp ONLY after success so a failed sweep retries next tick.
# ─────────────────────────────────────────────────────────────────────────────
PERIOD_STATE_DIR="$HOME/.local/share/lifehack/calendar-sweep-periods"
mkdir -p "$PERIOD_STATE_DIR" 2>/dev/null || true
PERIOD_STATE_FILE="$PERIOD_STATE_DIR/weekly"

_target_sunday() {
  python3 - "$1" <<'PYEOF'
import sys, datetime
today = datetime.date.fromisoformat(sys.argv[1])
print((today - datetime.timedelta(days=today.isoweekday() % 7)).isoformat())
PYEOF
}

TODAY="$(date +%F)"
TARGET_SUNDAY="$(_target_sunday "$TODAY")" || {
  _clog "ERROR: could not compute target Sunday — aborting."; exit 1; }
LAST_DONE=""; [ -f "$PERIOD_STATE_FILE" ] && LAST_DONE="$(tr -d '[:space:]' < "$PERIOD_STATE_FILE" 2>/dev/null)"

if [ "$DRY_RUN" -eq 1 ]; then
  echo "[$CS_LABEL] --dry-run report:"
  echo "  today         = $TODAY"
  echo "  target_sunday = $TARGET_SUNDAY (most recent Sunday, incl. today)"
  echo "  last_done     = ${LAST_DONE:-(never)}"
  echo "  roster        = $ROSTER ($(grep -cv '^\s*#' "$ROSTER" 2>/dev/null || echo '?') non-comment line(s))"
  if [ "$FORCE" -eq 1 ]; then
    echo "  --force set: GATE BYPASSED → would run"
  elif [ -z "$LAST_DONE" ] || [[ "$LAST_DONE" < "$TARGET_SUNDAY" ]]; then
    echo "  GATE: PASS → would run (Sunday $TARGET_SUNDAY not yet served)"
  else
    echo "  GATE: SKIP (Sunday $TARGET_SUNDAY already served)"
  fi
  exit 0
fi

if [ "$FORCE" -eq 1 ]; then
  _clog "--force: bypassing period gate (target=$TARGET_SUNDAY, last_done=${LAST_DONE:-(never)})."
else
  if [ -n "$LAST_DONE" ] && ! [[ "$LAST_DONE" < "$TARGET_SUNDAY" ]]; then
    _clog "Sunday $TARGET_SUNDAY already served (last_done=$LAST_DONE) — skip."
    exit 0
  fi
  _clog "gate PASS: target Sunday=$TARGET_SUNDAY, last_done=${LAST_DONE:-(never)} → running."
fi

# ── SINGLE-INSTANCE LOCK (mkdir atomic; stale-steal after 30 min — pull is bounded at 90s/cal) ──
LOCKDIR="/tmp/lifehack-${CS_LABEL}.lock"
STEAL=1800
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  if [ -d "$LOCKDIR" ] && [ "$(( $(date +%s) - $(stat -f %m "$LOCKDIR" 2>/dev/null || echo 0) ))" -gt "$STEAL" ]; then
    _clog "stale lock (>${STEAL}s) — stealing."; rm -rf "$LOCKDIR"
    mkdir "$LOCKDIR" 2>/dev/null || { _clog "lock race — skip."; exit 0; }
  else
    _clog "another run in progress — skip this tick."; exit 0
  fi
fi
trap "rm -rf '$LOCKDIR' 2>/dev/null" EXIT

DATESTAMP="$(date +%F)"
DATESTAMP_DOTS="$(date +%Y.%m.%d)"
# Topic-first filename, date trailing (house convention).
CS_REPORT_FILE="$DATA/desks/cal/state/sweep-reports/calendar-sweep_${DATESTAMP_DOTS}.md"
CS_EVENTS_TSV="$DATA/system/logs/calendar-sweep_${DATESTAMP}.events.tsv"
mkdir -p "$(dirname "$CS_REPORT_FILE")" "$(dirname "$CS_EVENTS_TSV")" 2>/dev/null || true

# tile writer — args: status high_count summary
_write_tile() {
  local status="${1:-ERROR}" count="${2:-0}" summary="${3:-}"
  python3 -c 'import json,sys; print(json.dumps({"high_findings": int(sys.argv[1]), "headline": sys.argv[2]}))' \
    "${count:-0}" "$summary" 2>/dev/null | \
    python3 "$CODE_ROOT/system/tools/emit_status.py" \
      --out "$DATA/state/status/calendar-sweep.json" --desk cal --pulse-job calendar-sweep \
      --stale-after-s "$CS_STALE_AFTER_S" --status "$status" --rc 0 --summary "$summary" --json - 2>/dev/null || \
    _clog "WARN: tile write failed (non-fatal)"
}

# ── PULL (code; sanitized reads via safe_calendar --redact) ──
N_CALS="$(grep -cv '^\s*#' "$ROSTER" 2>/dev/null || echo 0)"
_clog "pulling $N_CALS calendar(s), ${CS_SPAN_DAYS}d span…"
python3 "$CODE_ROOT/system/tools/calendar_sweep_pull.py" \
  --roster "$ROSTER" --span-days "$CS_SPAN_DAYS" --out "$CS_EVENTS_TSV"
PULL_RC=$?
if [ "$PULL_RC" -eq 2 ]; then
  _write_tile "ERROR" 0 "event pull setup error — tool broke"
  _clog "pull setup error — real failure. No stamp."; exit 1
fi
N_ROWS="$(( $(wc -l < "$CS_EVENTS_TSV" 2>/dev/null || echo 1) - 1 ))"
if [ "$PULL_RC" -eq 1 ] && [ "$N_ROWS" -le 0 ]; then
  # every calendar failed → "I could not look" must never read as "I looked and it was fine"
  _write_tile "ERROR" 0 "all calendar pulls failed — no data, not a clean calendar"
  _clog "all pulls failed — real failure. No stamp."; exit 1
fi

# ── DETECT (verbatim-ported v1 detector; report-only) ──
if ! python3 "$CODE_ROOT/system/tools/calendar_sweep.py" "$CS_EVENTS_TSV" \
      --window-days "$CS_WINDOW_DAYS" --span-days "$CS_SPAN_DAYS" \
      --calendars-queried "$N_CALS" > "$CS_REPORT_FILE"; then
  _write_tile "ERROR" 0 "detector failed — tool broke"
  _clog "detector failed — real failure. No stamp."; rm -f "$CS_REPORT_FILE"; exit 1
fi
N_HIGH="$(grep -c 'HIGH' "$CS_REPORT_FILE" 2>/dev/null || echo 0)"

PARTIAL_NOTE=""
if [ "$PULL_RC" -eq 1 ]; then
  PARTIAL_NOTE=" (PARTIAL — some calendars failed to pull; see pulse log)"
fi

echo "$TARGET_SUNDAY" > "$PERIOD_STATE_FILE"
_clog "stamped Sunday $TARGET_SUNDAY → $PERIOD_STATE_FILE"

SUMMARY="$N_ROWS event(s) swept across $N_CALS calendar(s); $N_HIGH HIGH line(s)${PARTIAL_NOTE}"
if [ "$N_HIGH" -gt 0 ] || [ -n "$PARTIAL_NOTE" ]; then
  _write_tile "NEEDS_REVIEW" "$N_HIGH" "$SUMMARY"
  bash "$CODE_ROOT/shared/notify/notify-send.sh" --source "$CS_LABEL" --tags "calendar" \
    --title "📅 Calendar sweep ready" \
    --message "calendar sweep ready — $SUMMARY. See $(basename "$CS_REPORT_FILE") before Win-the-Week." \
    2>/dev/null || true
else
  _write_tile "OK" 0 "$SUMMARY"
fi

_clog "done — $SUMMARY → $CS_REPORT_FILE (exit 0: found-findings is success)"
exit 0
