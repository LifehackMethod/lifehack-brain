#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: WEEKLY stale-record sweep — re-verifies every open claim in state/debt-ledger.md (## Open)
#      and state/open-loops.md (unstruck items) against live sources, and files a closure-PROPOSAL
#      report before the Sunday sitting. Born from 2026-08-26: 14 dead entries closed by hand, three
#      of them presented to the owner as live deadlines the same night. Spec:
#      <notes>/state/projects/harness-ops/records/stale-sweep-spec_2026.08.27.md
# SPLIT (LAW 1): stale_sweep.py extracts claims (structure-anchored) and validates dispositions
#      against a closed vocabulary fail-closed; the headless model ONLY judges "does live evidence
#      close this claim?". The tile's counts come from CODE validation, never the model's own
#      summary (LAW 3 — the actor never grades its own completion).
# GUARDS: PROPOSE-ONLY, forever — the claude session may write ONLY the two output files named in
#      its prompt. It NEVER edits the ledger or open-loops; the owner rules at the Sunday sitting
#      and the interactive session applies (ledger: delete + ## Cleared line; loops: strike + note).
#      Exit 0 EVEN when closures are proposed (found-stale is success). A model run whose EVERY
#      claim folds to NO-OUTCOME is a broken tool (tile ERROR, no stamp, exit 1) — "I could not
#      look" must never be spelled like "I looked and it was fine". Lock + watchdog-bounded.
# SCHEDULING: registered as `stale-sweep` in system/pulse-config.md ticking DAILY (86400); this
#      script self-gates ONCE PER ISO WEEK with target = that week's FRIDAY (handbook-audit-run.sh's
#      gate pattern, weekly semantics) so the report lands before Sunday; sleep-proof — a machine
#      asleep Friday runs on the next tick after wake, same week key.
# EXIT CODES (system/pulse-config.md's contract): 0 ran (incl. clean AND found-stale) · 75 stood
#      down (no claude token — claude-auth.lib.sh emits the named line) · 2 no data root · anything
#      else = real failure, counted by the breaker. claude's own exit 75/2 are remapped to 1 so a
#      broken tool is never laundered into "skipped"/"held" (same remap as handbook-audit-run.sh).
# ─────────────────────────────────────────────────────────────────────────────
set -u
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

. "$CODE_ROOT/system/tools/claude-auth.lib.sh" || {
  echo "[stale-sweep] FATAL: cannot source $CODE_ROOT/system/tools/claude-auth.lib.sh"; exit 1; }

DATA="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
if [ -z "$DATA" ]; then
  echo "[stale-sweep] no data root set — nothing to sweep. Set one: python3 shared/brain_root.py --set <folder>"
  exit 2
fi

CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude 2>/dev/null)}"
if [ -z "$CLAUDE_BIN" ]; then
  for _cb in "$HOME/.local/bin/claude" /opt/homebrew/bin/claude /usr/local/bin/claude; do
    [ -x "$_cb" ] && CLAUDE_BIN="$_cb" && break
  done
fi
CLAUDE_BIN="${CLAUDE_BIN:-claude}"

SS_LABEL="stale-sweep"
# sonnet: reads trusted repo/Brain content and produces judgment the owner relies on → mid-tier.
SS_MODEL="${SS_MODEL:-claude-sonnet-4-6}"
SS_WATCHDOG="${SS_WATCHDOG:-1800}"
# Tile staleness: 9 days = 777600s (7*86400 weekly + 2*86400 catch-up slack).
SS_STALE_AFTER_S=777600

LEDGER="$DATA/state/debt-ledger.md"
LOOPS="$DATA/state/open-loops.md"

_slog() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${SS_LABEL}: $*"; }

FORCE=0; DRY_RUN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --force)   FORCE=1;   shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "stale-sweep-run: unknown arg '$1'" >&2; exit 2 ;;
  esac
done

# ─────────────────────────────────────────────────────────────────────────────
# PERIOD-IDEMPOTENT WEEKLY GATE — handbook-audit-run.sh's pattern, weekly semantics.
# Key = current ISO week ("2026-W35"); target = that week's FRIDAY. Runs on-or-after Friday,
# once per ISO week; stamp ONLY after success so a failed sweep retries next tick.
# ─────────────────────────────────────────────────────────────────────────────
PERIOD_STATE_DIR="$HOME/.local/share/lifehack/stale-sweep-periods"
mkdir -p "$PERIOD_STATE_DIR" 2>/dev/null || true
PERIOD_STATE_FILE="$PERIOD_STATE_DIR/weekly"

_period_key_and_target() {
  local today="$1"
  python3 - "$today" <<'PYEOF'
import sys, datetime
today = datetime.date.fromisoformat(sys.argv[1])
iso = today.isocalendar()
print(f"{iso[0]}-W{iso[1]:02d}")
friday = today + datetime.timedelta(days=(5 - iso[2]))   # ISO weekday 5 = Friday
print(friday.isoformat())
PYEOF
}

TODAY="$(date +%F)"
PERIOD_INFO="$(_period_key_and_target "$TODAY")" || {
  _slog "ERROR: could not compute current ISO week — aborting."; exit 1; }
CURRENT_PERIOD="$(echo "$PERIOD_INFO" | head -1)"
TARGET_DATE="$(echo "$PERIOD_INFO" | tail -1)"
LAST_DONE=""; [ -f "$PERIOD_STATE_FILE" ] && LAST_DONE="$(tr -d '[:space:]' < "$PERIOD_STATE_FILE" 2>/dev/null)"

if [ "$DRY_RUN" -eq 1 ]; then
  echo "[stale-sweep] --dry-run report:"
  echo "  today          = $TODAY"
  echo "  current_period = $CURRENT_PERIOD"
  echo "  target_date    = $TARGET_DATE (this ISO week's Friday)"
  echo "  last_done      = ${LAST_DONE:-(never)}"
  _gte() { [[ "$1" > "$2" || "$1" == "$2" ]]; }
  echo "  today >= target_date?  $( _gte "$TODAY" "$TARGET_DATE" && echo YES || echo NO )"
  echo "  last_done < current?   $( [ -z "$LAST_DONE" ] || [[ "$LAST_DONE" < "$CURRENT_PERIOD" ]] && echo YES || echo NO )"
  if [ "$FORCE" -eq 1 ]; then
    echo "  --force set: GATE BYPASSED → would run"
  elif _gte "$TODAY" "$TARGET_DATE" && { [ -z "$LAST_DONE" ] || [[ "$LAST_DONE" < "$CURRENT_PERIOD" ]]; }; then
    echo "  GATE: PASS → would run"
  else
    echo "  GATE: SKIP (not yet Friday, or already done this week)"
  fi
  exit 0
fi

if [ "$FORCE" -eq 1 ]; then
  _slog "--force: bypassing period gate (period=$CURRENT_PERIOD, last_done=${LAST_DONE:-(never)})."
else
  if [[ "$TODAY" < "$TARGET_DATE" ]]; then
    _slog "not yet due (target=$TARGET_DATE Friday, today=$TODAY, week=$CURRENT_PERIOD) — skip."
    exit 0
  fi
  if [ -n "$LAST_DONE" ] && { [[ "$LAST_DONE" > "$CURRENT_PERIOD" ]] || [[ "$LAST_DONE" == "$CURRENT_PERIOD" ]]; }; then
    _slog "already completed week $CURRENT_PERIOD (last_done=$LAST_DONE) — skip."
    exit 0
  fi
  _slog "gate PASS: week=$CURRENT_PERIOD, last_done=${LAST_DONE:-(never)} → running."
fi

require_claude_token "$SS_LABEL" _slog || exit 75

# ── SINGLE-INSTANCE LOCK (mkdir atomic; stale-steal after watchdog+buffer) ──
LOCKDIR="/tmp/lifehack-${SS_LABEL}.lock"
STEAL=$(( SS_WATCHDOG + 300 ))
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  if [ -d "$LOCKDIR" ] && [ "$(( $(date +%s) - $(stat -f %m "$LOCKDIR" 2>/dev/null || echo 0) ))" -gt "$STEAL" ]; then
    _slog "stale lock (>${STEAL}s) — stealing."; rm -rf "$LOCKDIR"
    mkdir "$LOCKDIR" 2>/dev/null || { _slog "lock race — skip."; exit 0; }
  else
    _slog "another run in progress — skip this tick."; exit 0
  fi
fi
trap "rm -rf '$LOCKDIR' 2>/dev/null" EXIT

DATESTAMP="$(date +%F)"
DATESTAMP_DOTS="$(date +%Y.%m.%d)"
# Topic-first filename, date trailing (house convention).
SS_REPORT_FILE="$DATA/state/projects/harness-ops/records/stale-sweep_${DATESTAMP_DOTS}.md"
SS_CLAIMS_FILE="$DATA/system/logs/stale-sweep_${DATESTAMP}.claims.json"
SS_DISP_FILE="$DATA/system/logs/stale-sweep_${DATESTAMP}.dispositions.json"
SS_VALID_FILE="$DATA/system/logs/stale-sweep_${DATESTAMP}.validated.json"
mkdir -p "$(dirname "$SS_REPORT_FILE")" "$(dirname "$SS_CLAIMS_FILE")" 2>/dev/null || true
rm -f "$SS_DISP_FILE" "$SS_VALID_FILE" 2>/dev/null  # never read a prior run's stale sidecar

# tile writer — args: status count summary
_write_tile() {
  local status="${1:-ERROR}" count="${2:-0}" summary="${3:-}"
  python3 -c 'import json,sys; print(json.dumps({"proposal_count": int(sys.argv[1]), "headline": sys.argv[2]}))' \
    "${count:-0}" "$summary" 2>/dev/null | \
    python3 "$CODE_ROOT/system/tools/emit_status.py" \
      --out "$DATA/state/status/stale-sweep.json" --desk root --pulse-job stale-sweep \
      --stale-after-s "$SS_STALE_AFTER_S" --status "$status" --rc 0 --summary "$summary" --json - 2>/dev/null || \
    _slog "WARN: tile write failed (non-fatal)"
}

# ── EXTRACT (code, before any model) ──
if ! python3 "$CODE_ROOT/system/tools/stale_sweep.py" extract \
      --ledger "$LEDGER" --loops "$LOOPS" --out "$SS_CLAIMS_FILE"; then
  _write_tile "ERROR" 0 "claim extraction failed — tool broke"
  _slog "extraction failed — real failure."; exit 1
fi
CLAIM_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["claim_count"])' "$SS_CLAIMS_FILE" 2>/dev/null || echo 0)"
_slog "extracted $CLAIM_COUNT open claim(s)."

if [ "$CLAIM_COUNT" = "0" ]; then
  {
    echo "---"; echo "topic: [harness-ops]"; echo "record_type: report"; echo "status: active"
    echo "created_at: $DATESTAMP"; echo "---"; echo
    echo "# Weekly stale-record sweep — $DATESTAMP"
    echo
    echo "Zero open claims found in the ledger's ## Open section and open-loops — nothing to verify."
  } > "$SS_REPORT_FILE"
  echo "$CURRENT_PERIOD" > "$PERIOD_STATE_FILE"
  _write_tile "OK" 0 "zero open claims — nothing to sweep"
  _slog "zero claims — report filed, stamped $CURRENT_PERIOD. done."
  exit 0
fi

SS_PROMPT="Your notes root is: $DATA
The harness code root is: $CODE_ROOT
You are the WEEKLY STALE-RECORD SWEEPER, running HEADLESS and UNATTENDED. You are PROPOSE-ONLY: you NEVER edit, move, rename, or delete the debt ledger, open-loops, or anything else. Your ONLY writes are the two output files named below. READ-ONLY verification everywhere else; never run gws or anything that writes.

THE JOB: $SS_CLAIMS_FILE holds $CLAIM_COUNT open claims extracted tonight from $LEDGER and $LOOPS. Each was true when written and may have silently completed since — records here rot in one direction. For EACH claim, check its factual premise against live sources NOW: does the file/tool/config it names exist; does a status tile under $DATA/state/status/, a record, a log, or the repo's git log/show output prove it done; does the live file still carry the defect it describes?

For each claim pick EXACTLY ONE disposition from this closed vocabulary (any other value is discarded by the validator):
- STALE-CLOSE-PROPOSED — provably done/moot NOW; cite the proof (file:line or commit + a <=20-word decisive fragment).
- STILL-OPEN — the premise verifiably still holds; say what you checked.
- NEEDS-HUMAN — only the owner can confirm (a personal decision, an external party, physical-world state).
- UNVERIFIABLE — needs a source you cannot reach read-only/headless (e.g. a live Google read); say which.
Never guess a claim closed: no proof = STILL-OPEN or UNVERIFIABLE, never STALE-CLOSE-PROPOSED.

1) WRITE the dispositions sidecar (JSON, one object) -> $SS_DISP_FILE
   EXACTLY: {\"dispositions\":[{\"id\":\"<claim id verbatim from the claims file>\",\"disposition\":\"<vocab member>\",\"proof\":\"<cite, <=40 words>\"}, ...]}
   One entry per claim, ids copied verbatim. A claim you could not evaluate gets NO entry (the validator folds it to NO-OUTCOME).

2) WRITE the human report (markdown) -> $SS_REPORT_FILE
   Frontmatter: topic: [harness-ops], record_type: report, status: active, created_at: $DATESTAMP.
   Lead with one line: N claims checked, X closures proposed, Y need the owner. Then ONE section per disposition class (skip empty classes), one block per claim: the claim's source file:line, its one-line gist, your proof. Closures proposed are PROPOSALS for the Sunday sitting — the owner rules; the applying session uses each file's own convention (ledger: delete from ## Open + one dated line under ## Cleared; open-loops: strike + bold dated note). If nothing is stale, the report still gets written and says so explicitly — never silence.

Do NOT send any notification — the runner buzzes deterministically from the validated counts. Do not touch any file outside the two named above."

cd "$DATA" || { _slog "FATAL: cannot cd to $DATA"; exit 1; }
_slog "launching headless claude ($SS_MODEL, watchdog ${SS_WATCHDOG}s) over $CLAIM_COUNT claims…"
"$CLAUDE_BIN" -p "$SS_PROMPT" --model "$SS_MODEL" --dangerously-skip-permissions </dev/null &
CPID=$!
( sleep "$SS_WATCHDOG"; kill -9 "$CPID" 2>/dev/null ) & WPID=$!
wait "$CPID" 2>/dev/null; RC=$?
kill "$WPID" 2>/dev/null; wait "$WPID" 2>/dev/null
_slog "claude exit: $RC"

if [ "$RC" -ne 0 ]; then
  _write_tile "ERROR" 0 "claude exited $RC — tool broke, not a verdict"
  _slog "non-zero exit — tool broke (NOT a clean sweep). No stamp; Pulse breaker handles repeats."
  if [ "$RC" -eq 75 ] || [ "$RC" -eq 2 ]; then
    _slog "claude's own exit $RC collides with a Pulse not-a-fault code — reporting as 1."
    exit 1
  fi
  exit "$RC"
fi

# ── VALIDATE (code grades membership — never the model's own summary) ──
if ! python3 "$CODE_ROOT/system/tools/stale_sweep.py" validate \
      --claims "$SS_CLAIMS_FILE" --dispositions "$SS_DISP_FILE" > "$SS_VALID_FILE" 2>/dev/null; then
  _write_tile "ERROR" 0 "disposition validation failed — tool broke"
  _slog "validation failed — real failure. No stamp."; exit 1
fi
read -r N_CLOSE N_HUMAN N_NOOUT <<EOF2
$(python3 -c 'import json,sys; c=json.load(open(sys.argv[1]))["counts"]; print(c["STALE-CLOSE-PROPOSED"], c["NEEDS-HUMAN"], c["NO-OUTCOME"])' "$SS_VALID_FILE" 2>/dev/null || echo "0 0 999999")
EOF2

# Every claim NO-OUTCOME = the model produced nothing usable: a broken tool, never a clean sweep.
if [ "$N_NOOUT" -ge "$CLAIM_COUNT" ]; then
  _write_tile "ERROR" 0 "all $CLAIM_COUNT claims NO-OUTCOME — model produced nothing usable"
  _slog "all claims NO-OUTCOME — tool broke. No stamp."; exit 1
fi

echo "$CURRENT_PERIOD" > "$PERIOD_STATE_FILE"
_slog "stamped week $CURRENT_PERIOD → $PERIOD_STATE_FILE"

SUMMARY="$N_CLOSE closure(s) proposed, $N_HUMAN need the owner, $N_NOOUT no-outcome (of $CLAIM_COUNT)"
if [ "$N_CLOSE" = "0" ] && [ "$N_HUMAN" = "0" ] && [ "$N_NOOUT" = "0" ]; then
  _write_tile "OK" 0 "clean — all $CLAIM_COUNT open claims verified still open"
else
  _write_tile "NEEDS_REVIEW" "$N_CLOSE" "$SUMMARY"
fi

bash "$CODE_ROOT/shared/notify/notify-send.sh" --source "$SS_LABEL" --tags "broom" \
  --title "🧹 Stale-record sweep ready" \
  --message "stale sweep ready — $SUMMARY. See $(basename "$SS_REPORT_FILE") for Sunday." \
  2>/dev/null || true

_slog "done — $SUMMARY. (exit 0: found-stale is success)"
exit 0
