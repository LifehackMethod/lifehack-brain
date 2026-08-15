#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# cal-diary-run.sh — headless runner for the Cal diary tee-ups. READ-ONLY against
# Google; the only writes are the local diary .md files (+ a "ready" ntfy buzz on
# weekly+). Dispatches by cadence:
#   daily (default) → cal-diary-capture.py  (writes diary/YYYY/MM/DD.md) — SILENT (no buzz)
#   weekly|monthly|quarterly|yearly → cal-diary-rollup.py (writes the period review draft)
#       → then fires ONE "your <cadence> check-in is ready" buzz via notify-send.sh
#
# SCHEDULING (period-idempotent catch-up conversion):
#   daily     → interval-based (86400s), catches up on wake.
#   weekly/monthly/quarterly/yearly → period-idempotent gate fires ONCE per period, on-or-after
#               target date. Designed to replace clock-pinned crons that MISS FOREVER if the
#               machine is asleep at the exact minute — this checks daily and runs the first time
#               the target date has passed and this period is not yet done.
#
# PERIOD IDEMPOTENCY (weekly|monthly|quarterly|yearly):
#   State: machine-local period stamp files at ~/.local/share/lifehack/cal-diary-periods/{cadence}
#   On each tick: if today >= target_date AND last_completed_period < current_period → run + stamp.
#   Safe to call daily; runs each period exactly once. --force bypasses the gate for manual/backfill.
#   --dry-run prints the gate decision and exits without doing any diary work.
#
# SAFETY: fail-soft (a source read failure → that section source-unavailable + exit 0, so a
# breaker never trips on a content gap); notify suppression by the governor is NOT a failure.
# Test without buzzing: NOTIFY_DRY_RUN=1 bash cal-diary-run.sh --cadence weekly
#
# ⚖ PORT NOTE: donor's LEAD-MACHINE gate (state/primary-machine marker election between two Macs)
# is DELETED, not translated — a student has one computer. This runner has no caller yet — DEST
# has no scheduler/cron scaffold (that lands separately); ported so it is correct and callable
# the moment one exists.
# ─────────────────────────────────────────────────────────────────────────────
set -u
# Execution-residency: DRIVE = CONTENT root (where diary/state/journal are WRITTEN). CODE_ROOT =
# where THIS script + its .py tools live (derived from $0 → the git clone when cron calls the
# clone copy). Code is invoked from CODE_ROOT; content is written under DRIVE.
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# The data root, through the ONE resolver — never a hardcoded personal Drive path.
DRIVE="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
if [ -z "$DRIVE" ]; then
  echo "[cal-diary] no data root set — nothing to write into. Set one: python3 shared/brain_root.py --set <folder>"
  exit 2
fi

GWS_BIN="$(command -v gws 2>/dev/null || echo /opt/homebrew/bin/gws)"

CADENCE="daily"; DATE_ARG=""; FORCE=0; DRY_RUN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --cadence)  CADENCE="${2:-daily}"; shift 2 ;;
    --date)     DATE_ARG="${2:-}";     shift 2 ;;
    --force)    FORCE=1;               shift   ;;
    --dry-run)  DRY_RUN=1;             shift   ;;
    *) echo "cal-diary-run: unknown arg '$1'" >&2; exit 2 ;;
  esac
done

# ── GWS HEADLESS AUTH (keychain-free isolated config) ──
GWS_CREDS="$HOME/.config/lifehack/gws-credentials.json"
if [ -s "$GWS_CREDS" ]; then
  export GOOGLE_WORKSPACE_CLI_CONFIG_DIR="$HOME/.config/lifehack/gws-cron"
  export GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE="$GWS_CREDS"
  export GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND=file
fi
# (No abort if creds absent — interactive sessions use the normal gws login; capture/rollup are
#  fail-soft, so a student with no gws/Google account still gets a diary entry from journal.md +
#  status tiles alone, with the Google sections marked source-unavailable.)

# Default the anchor to today when no --date was passed. This keeps the array non-empty so
# "${DATE_OPT[@]}" is safe under `set -u` on macOS bash 3.2 (empty-array expansion throws
# "unbound variable" there → the weekly rollup silently errored). --date=today == python's own
# no-arg default (anchor = today), so behaviour is unchanged for every cadence.
[ -z "$DATE_ARG" ] && DATE_ARG="$(date +%F)"
DATE_OPT=(--date "$DATE_ARG")

# ─────────────────────────────────────────────────────────────────────────────
# PERIOD-IDEMPOTENT GATE — weekly|monthly|quarterly|yearly only.
# Called AFTER DATE_ARG is resolved (so --date backfill still works correctly).
#
# State files: ~/.local/share/lifehack/cal-diary-periods/{cadence}
#   Contents: the last COMPLETED period key (e.g. "2026-W30", "2026-07", "2026-Q3", "2026")
#
# Logic:
#   current_period  = the ISO period key for today
#   target_date     = the date this period's rollup is due (on-or-after = run)
#   last_done       = the contents of the state file (empty = never run)
#   GATE PASSES if: today >= target_date AND last_done < current_period (or --force)
#   On success: stamp current_period into the state file.
# ─────────────────────────────────────────────────────────────────────────────
PERIOD_STATE_DIR="$HOME/.local/share/lifehack/cal-diary-periods"
mkdir -p "$PERIOD_STATE_DIR" 2>/dev/null || true

# period_key_and_target CADENCE TODAY_DATE
# Prints two lines: period_key, target_date (YYYY-MM-DD)
# "prior period" semantics for monthly/quarterly/yearly: the rollup is generated on the 1st of the NEW
# period to summarize the JUST-ENDED period, matching the old --date "$(date -v-1d)" cron behavior.
_period_key_and_target() {
  local cadence="$1" today="$2"
  python3 - "$cadence" "$today" <<'PYEOF'
import sys, datetime

cadence = sys.argv[1]
today = datetime.date.fromisoformat(sys.argv[2])

if cadence == "weekly":
    # ISO week key: YYYY-Www. Target date = Friday of that ISO week.
    iso = today.isocalendar()
    year, week = iso[0], iso[1]
    key = f"{year}-W{week:02d}"
    # Monday of iso week + 4 days = Friday
    monday = datetime.date.fromisocalendar(year, week, 1)
    target = monday + datetime.timedelta(days=4)  # Friday

elif cadence == "monthly":
    # Period = the JUST-ENDED month (same semantics as --date "$(date -v-1d)" on the 1st).
    # We roll up on the 1st of the current month to cover the prior month.
    # Period key = the prior month (YYYY-MM).
    # Target date = 1st of the current month (when today IS the 1st, run it).
    first_of_this_month = today.replace(day=1)
    prior = (first_of_this_month - datetime.timedelta(days=1))
    key = prior.strftime("%Y-%m")
    target = first_of_this_month

elif cadence == "quarterly":
    # Quarter boundaries: Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec.
    # Rollup runs on the 1st of the new quarter to cover the just-ended quarter.
    q_start_months = {1: 1, 2: 4, 3: 7, 4: 10}
    # Current quarter
    q = (today.month - 1) // 3 + 1
    q_start = today.replace(month=q_start_months[q], day=1)
    # Prior quarter (the one we're summarizing)
    prior_qstart = (q_start - datetime.timedelta(days=1)).replace(day=1)
    prior_q = (prior_qstart.month - 1) // 3 + 1
    key = f"{prior_qstart.year}-Q{prior_q}"
    target = q_start

elif cadence == "yearly":
    # Rollup on Jan 1 to cover the just-ended year.
    prior_year = today.year - 1
    key = str(prior_year)
    target = datetime.date(today.year, 1, 1)

else:
    sys.exit(1)

print(key)
print(target.isoformat())
PYEOF
}

_run_period_gate() {
  local cadence="$1"
  local today; today="$(date +%F)"
  local state_file="$PERIOD_STATE_DIR/$cadence"

  local period_info; period_info="$(_period_key_and_target "$cadence" "$today")" || {
    echo "[cal-diary] ERROR: could not compute period for cadence=$cadence — aborting." >&2; exit 1
  }
  local current_period; current_period="$(echo "$period_info" | head -1)"
  local target_date;    target_date="$(echo "$period_info" | tail -1)"
  local last_done="";   [ -f "$state_file" ] && last_done="$(cat "$state_file" 2>/dev/null | tr -d '[:space:]')"

  if [ "$DRY_RUN" -eq 1 ]; then
    echo "[cal-diary/$cadence] --dry-run report:"
    echo "  today          = $today"
    echo "  current_period = $current_period"
    echo "  target_date    = $target_date"
    echo "  last_done      = ${last_done:-(never)}"
    _gte() { [[ "$1" > "$2" || "$1" == "$2" ]]; }
    echo "  today >= target_date?  $( _gte "$today" "$target_date" && echo YES || echo NO )"
    echo "  last_done < current?   $( [ -z "$last_done" ] || [[ "$last_done" < "$current_period" ]] && echo YES || echo NO )"
    if [ "$FORCE" -eq 1 ]; then
      echo "  --force set: GATE BYPASSED → would run"
    elif _gte "$today" "$target_date" && { [ -z "$last_done" ] || [[ "$last_done" < "$current_period" ]]; }; then
      echo "  GATE: PASS → would run"
    else
      echo "  GATE: SKIP (already done or not yet due)"
    fi
    exit 0
  fi

  if [ "$FORCE" -eq 1 ]; then
    echo "[cal-diary/$cadence] --force: bypassing period gate (period=$current_period, last_done=${last_done:-(never)})."
    return 0  # proceed to actual work; caller stamps on success
  fi

  # Normal gate: run if today >= target AND this period not yet done
  # (bash [[ ]] has no >=; we negate < instead)
  if [[ "$today" < "$target_date" ]]; then
    echo "[cal-diary/$cadence] not yet due (target=$target_date, today=$today, period=$current_period) — skip."
    exit 0
  fi
  if [ -n "$last_done" ] && { [[ "$last_done" > "$current_period" ]] || [[ "$last_done" == "$current_period" ]]; }; then
    echo "[cal-diary/$cadence] already completed period $current_period (last_done=$last_done) — skip."
    exit 0
  fi

  echo "[cal-diary/$cadence] gate PASS: period=$current_period, target=$target_date, last_done=${last_done:-(never)} → running."
  return 0  # proceed; stamp happens after successful run below
}

_stamp_period() {
  local cadence="$1"
  local today; today="$(date +%F)"
  local period_info; period_info="$(_period_key_and_target "$cadence" "$today")"
  local current_period; current_period="$(echo "$period_info" | head -1)"
  local state_file="$PERIOD_STATE_DIR/$cadence"
  echo "$current_period" > "$state_file"
  echo "[cal-diary/$cadence] stamped period $current_period → $state_file"
}

# ── DAILY PATH — no period gate (an interval-based caller handles idempotency) ──
if [ "$CADENCE" = "daily" ]; then
  # ── PRE-FLIGHT (warn-only; the tee-up degrades gracefully without gws) ──
  # RETRY the gws pre-flight (3x/4s) before declaring failure — a single getProfile can fail on a
  # TRANSIENT blip (token mid-refresh, momentary API hiccup) rather than a real outage.
  _GWS_PREFLIGHT_OK=0
  for _gws_try in 1 2 3; do
    if "$GWS_BIN" gmail users getProfile --params '{"userId":"me"}' >/dev/null 2>&1; then _GWS_PREFLIGHT_OK=1; break; fi
    if [ "$_gws_try" -lt 3 ]; then echo "[gws] pre-flight attempt $_gws_try failed — retry in 4s…"; sleep 4; fi
  done
  if [ "$_GWS_PREFLIGHT_OK" -ne 1 ]; then
    echo "[cal-diary] WARN: gws pre-flight failed (or gws is not installed) — calendar/tasks/win will be source-unavailable this run."
  fi

  if [ "$DRY_RUN" -eq 1 ]; then
    echo "[cal-diary/daily] --dry-run: daily cadence has no period gate; would run cal-diary-capture.py --date $DATE_ARG."
    exit 0
  fi

  python3 "$CODE_ROOT/system/tools/cal-diary-capture.py" "${DATE_OPT[@]}"; RC=$?
  # ── STATUS TILE EMIT — a health sweeper watches this tile for the daily capture going stale/silent. ──
  _DIARY_NOW="$(date -u +"%Y-%m-%dT%H:%M:%S+00:00")"
  _DIARY_STATUS="$( [ "$RC" -eq 0 ] && echo "OK" || echo "ERROR" )"
  _DIARY_SUMMARY="$( [ "$RC" -eq 0 ] && echo "daily diary capture ok" || echo "daily diary capture failed (cal-diary-capture.py)" )"
  python3 -c "
import json, os
os.makedirs('$DRIVE/state/status', exist_ok=True)
d={'schema_version':1,'emit_mode':'manual','last_run':'$_DIARY_NOW','rc':$RC,'stale_after_s':93600,'status':'$_DIARY_STATUS','summary':'$_DIARY_SUMMARY','no_pulse':True}
tmp='$DRIVE/state/status/cal-diary.json.tmp'
json.dump(d,open(tmp,'w'),indent=2)
os.replace(tmp,'$DRIVE/state/status/cal-diary.json')
" 2>/dev/null || echo "[cal-diary] WARN: status tile write failed (non-fatal)"
  exit "$RC"   # daily is SILENT — no buzz
fi

# ── Periodic tee-up (weekly|monthly|quarterly|yearly) — period-idempotent gate ──
_run_period_gate "$CADENCE"   # exits 0 (skip) or returns 0 (proceed); exits with dry-run report

# PRE-FLIGHT for periodic cadences (same retry pattern as daily path)
_GWS_PREFLIGHT_OK=0
for _gws_try in 1 2 3; do
  if "$GWS_BIN" gmail users getProfile --params '{"userId":"me"}' >/dev/null 2>&1; then _GWS_PREFLIGHT_OK=1; break; fi
  if [ "$_gws_try" -lt 3 ]; then echo "[gws] pre-flight attempt $_gws_try failed — retry in 4s…"; sleep 4; fi
done
if [ "$_GWS_PREFLIGHT_OK" -ne 1 ]; then
  echo "[cal-diary] WARN: gws pre-flight failed (or gws is not installed) — calendar/tasks/win will be source-unavailable this run."
fi

python3 "$CODE_ROOT/system/tools/cal-diary-rollup.py" --cadence "$CADENCE" "${DATE_OPT[@]}"; RC=$?

# Stamp the completed period on success (so the next tick skips it).
if [ "$RC" -eq 0 ]; then
  _stamp_period "$CADENCE"
fi

# ── "Ready" buzz — only on a clean rollup (rc=0). Teaser only; governor-gated. ──
if [ "$RC" -eq 0 ]; then
  CAP="$(printf '%s' "${CADENCE:0:1}" | tr '[:lower:]' '[:upper:]')${CADENCE:1}"
  bash "$CODE_ROOT/shared/notify/notify-send.sh" \
    --source "cal-checkin" --tags "calendar,spiral_calendar" \
    --title "📋 ${CAP} check-in ready" \
    --message "Your ${CADENCE} review is teed up — open Cal to do the check-in." \
    2>/dev/null || true
fi
exit "$RC"
