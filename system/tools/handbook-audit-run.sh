#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: QUARTERLY drift audit of the Owner's Handbook (the harness-handbook project's chapters)
#      against the live system — pulse schedule, guard registry, desks+projects tree, skill
#      roster. Fires a read-only headless `claude -p` that files a drift report (an explicit
#      "no drift" report when clean) into the handbook project's records/, writes a JSON
#      summary sidecar, then THIS runner writes the status tile and sends ONE normal-priority
#      buzz. Added 2026-08-25.
# GUARDS: PROPOSE-ONLY, forever — the claude session may write ONLY the two output files named
#      in its own prompt. It NEVER edits chapters; the owner reviews the report and rules.
#      Exit 0 EVEN when drift is found (found-drift is success; non-zero = tool broke → Pulse's
#      3-strike breaker). Lock + watchdog-bounded.
# SCHEDULING: registered as `handbook-audit` in system/pulse-config.md ticking DAILY (86400);
#      this script self-gates period-idempotently ONCE PER QUARTER — the planning-diary-run.sh
#      gate pattern (stamp file, on-or-after target date, catch-up on wake, --force, --dry-run).
#      ⚠ Same MECHANICS, different period SEMANTICS, on purpose: planning-diary's quarterly key
#      is the JUST-ENDED quarter (a rollup summarizes the past); an audit checks the PRESENT, so
#      the key here is the CURRENT quarter with target = the quarter's first day. Consequence:
#      the first tick after install/merge runs immediately (the current quarter is unstamped),
#      then once per quarter after — sleep-proof, never clock-pinned.
# EXIT CODES (system/pulse-config.md's contract): 0 ran (incl. clean AND found-drift) ·
#      75 stood down (no claude token yet — claude-auth.lib.sh emits the named line) ·
#      2 no data root · anything else = real failure, counted by the breaker. claude's own
#      exit 75/2 are remapped to 1 so a broken tool is never laundered into "skipped"/"held"
#      (same remap, same reason, as archivist-run.lib.sh).
# ─────────────────────────────────────────────────────────────────────────────
set -u
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# The ONE headless-claude credential preflight — shared, never hand-rolled (see
# claude-auth.lib.sh's own header for the five-copy history that rule comes from).
# A missing library is a REAL defect (exit 1), never a stand-down.
. "$CODE_ROOT/system/tools/claude-auth.lib.sh" || {
  echo "[handbook-audit] FATAL: cannot source $CODE_ROOT/system/tools/claude-auth.lib.sh"; exit 1; }

# The data root, through the ONE resolver — never a hardcoded personal Drive path.
DATA="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
if [ -z "$DATA" ]; then
  echo "[handbook-audit] no data root set — no handbook to audit. Set one: python3 shared/brain_root.py --set <folder>"
  exit 2
fi

# Reach `claude` at runtime, never a hardcoded personal path (house standard).
CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude 2>/dev/null)}"
if [ -z "$CLAUDE_BIN" ]; then
  for _cb in "$HOME/.local/bin/claude" /opt/homebrew/bin/claude /usr/local/bin/claude; do
    [ -x "$_cb" ] && CLAUDE_BIN="$_cb" && break
  done
fi
CLAUDE_BIN="${CLAUDE_BIN:-claude}"

HB_LABEL="handbook-audit"
# sonnet: reads trusted repo/Brain content and produces judgment the owner relies on → mid-tier per the
# house subagent rule; same default as the archivist runners.
HB_MODEL="${HB_MODEL:-claude-sonnet-4-6}"
HB_WATCHDOG="${HB_WATCHDOG:-1800}"
# Tile staleness: 100 days = 8640000s (computed 100*86400) — longer than the longest quarter
# (92 days = 7948800s) plus catch-up slack, so a healthy quarterly tile never renders stale.
HB_STALE_AFTER_S=8640000

_hlog() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${HB_LABEL}: $*"; }

FORCE=0; DRY_RUN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --force)   FORCE=1;   shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "handbook-audit-run: unknown arg '$1'" >&2; exit 2 ;;
  esac
done

# ─────────────────────────────────────────────────────────────────────────────
# PERIOD-IDEMPOTENT QUARTERLY GATE — the planning-diary-run.sh pattern.
# State file: ~/.local/share/lifehack/handbook-audit-periods/quarterly
#   Contents: the last COMPLETED quarter key (e.g. "2026-Q3"); empty/absent = never run.
# GATE PASSES if: today >= target_date (the current quarter's first day — always true except
# never, kept for pattern fidelity + explicitness in --dry-run) AND last_done < current_quarter
# (or --force). Stamp happens ONLY after a successful run, so a failed audit retries next tick.
# ─────────────────────────────────────────────────────────────────────────────
PERIOD_STATE_DIR="$HOME/.local/share/lifehack/handbook-audit-periods"
mkdir -p "$PERIOD_STATE_DIR" 2>/dev/null || true
PERIOD_STATE_FILE="$PERIOD_STATE_DIR/quarterly"

# Prints two lines: current quarter key, target date (the quarter's first day).
_period_key_and_target() {
  local today="$1"
  python3 - "$today" <<'PYEOF'
import sys, datetime
today = datetime.date.fromisoformat(sys.argv[1])
q = (today.month - 1) // 3 + 1
q_start_months = {1: 1, 2: 4, 3: 7, 4: 10}
print(f"{today.year}-Q{q}")
print(today.replace(month=q_start_months[q], day=1).isoformat())
PYEOF
}

TODAY="$(date +%F)"
PERIOD_INFO="$(_period_key_and_target "$TODAY")" || {
  _hlog "ERROR: could not compute current quarter — aborting."; exit 1; }
CURRENT_PERIOD="$(echo "$PERIOD_INFO" | head -1)"
TARGET_DATE="$(echo "$PERIOD_INFO" | tail -1)"
LAST_DONE=""; [ -f "$PERIOD_STATE_FILE" ] && LAST_DONE="$(tr -d '[:space:]' < "$PERIOD_STATE_FILE" 2>/dev/null)"

if [ "$DRY_RUN" -eq 1 ]; then
  echo "[handbook-audit] --dry-run report:"
  echo "  today          = $TODAY"
  echo "  current_period = $CURRENT_PERIOD"
  echo "  target_date    = $TARGET_DATE"
  echo "  last_done      = ${LAST_DONE:-(never)}"
  _gte() { [[ "$1" > "$2" || "$1" == "$2" ]]; }
  echo "  today >= target_date?  $( _gte "$TODAY" "$TARGET_DATE" && echo YES || echo NO )"
  echo "  last_done < current?   $( [ -z "$LAST_DONE" ] || [[ "$LAST_DONE" < "$CURRENT_PERIOD" ]] && echo YES || echo NO )"
  if [ "$FORCE" -eq 1 ]; then
    echo "  --force set: GATE BYPASSED → would run"
  elif _gte "$TODAY" "$TARGET_DATE" && { [ -z "$LAST_DONE" ] || [[ "$LAST_DONE" < "$CURRENT_PERIOD" ]]; }; then
    echo "  GATE: PASS → would run"
  else
    echo "  GATE: SKIP (already done this quarter)"
  fi
  exit 0
fi

if [ "$FORCE" -eq 1 ]; then
  _hlog "--force: bypassing period gate (period=$CURRENT_PERIOD, last_done=${LAST_DONE:-(never)})."
else
  if [[ "$TODAY" < "$TARGET_DATE" ]]; then
    _hlog "not yet due (target=$TARGET_DATE, today=$TODAY, period=$CURRENT_PERIOD) — skip."
    exit 0
  fi
  if [ -n "$LAST_DONE" ] && { [[ "$LAST_DONE" > "$CURRENT_PERIOD" ]] || [[ "$LAST_DONE" == "$CURRENT_PERIOD" ]]; }; then
    _hlog "already completed period $CURRENT_PERIOD (last_done=$LAST_DONE) — skip."
    exit 0
  fi
  _hlog "gate PASS: period=$CURRENT_PERIOD, last_done=${LAST_DONE:-(never)} → running."
fi

# ── HEADLESS AUTH — claude OAuth token (cron can't read the login keychain). STOOD DOWN (75),
#    not a fault, when absent: true on day one of every install until `claude setup-token`.
require_claude_token "$HB_LABEL" _hlog || exit 75

# ── SINGLE-INSTANCE LOCK (mkdir atomic; stale-steal after watchdog+buffer) ──
LOCKDIR="/tmp/lifehack-${HB_LABEL}.lock"
STEAL=$(( HB_WATCHDOG + 300 ))
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  if [ -d "$LOCKDIR" ] && [ "$(( $(date +%s) - $(stat -f %m "$LOCKDIR" 2>/dev/null || echo 0) ))" -gt "$STEAL" ]; then
    _hlog "stale lock (>${STEAL}s) — stealing."; rm -rf "$LOCKDIR"
    mkdir "$LOCKDIR" 2>/dev/null || { _hlog "lock race — skip."; exit 0; }
  else
    _hlog "another run in progress — skip this tick."; exit 0
  fi
fi
trap "rm -rf '$LOCKDIR' 2>/dev/null" EXIT

DATESTAMP="$(date +%F)"
DATESTAMP_DOTS="$(date +%Y.%m.%d)"
# Topic-first filename, date trailing (house convention — never date-first).
HB_REPORT_FILE="$DATA/state/projects/harness-handbook/records/handbook-audit_${DATESTAMP_DOTS}.md"
HB_SUMMARY_FILE="$DATA/system/logs/handbook-audit_${DATESTAMP}.summary.json"
mkdir -p "$(dirname "$HB_REPORT_FILE")" "$(dirname "$HB_SUMMARY_FILE")" 2>/dev/null || true
rm -f "$HB_SUMMARY_FILE" 2>/dev/null  # never read a prior run's stale sidecar

HB_PROMPT="Your notes root is: $DATA
The harness code root is: $CODE_ROOT
You are the QUARTERLY HANDBOOK AUDITOR, running HEADLESS and UNATTENDED. You are PROPOSE-ONLY: you NEVER edit, move, rename, or delete the handbook chapters or anything else. Your ONLY writes are the two output files named below. The live system is the truth; the handbook is what drifts.

1) FIND the Owner's Handbook chapters. Try in order:
   a. $DATA/state/projects/harness-handbook/drafts/handbook-ch*.md
   b. If that folder is empty or gone (a final-home move was pending when this job was built), read $DATA/state/projects/harness-handbook/brief.md — its §2 decision board / §8 artifacts name the chapters' current home — and audit them there.
   If you cannot locate any chapters, that IS the finding: write both output files saying so (sidecar: status NEEDS_REVIEW, finding_count 1, headline 'handbook chapters not found').

2) AUDIT every factual claim the chapters make against the LIVE system:
   - Pulse schedule: the \`\`\`jobs block in $CODE_ROOT/system/pulse-config.md — cadence/rhythm claims (especially the rhythms chapter).
   - Guard registry: the hooks registered in $CODE_ROOT/.claude/settings.json — protection/wall claims (especially the protections chapter).
   - Desks + projects: the live tree under $DATA (desks with canon/+records/, state/projects/) — where-things-live claims and any counts.
   - Skill roster: $CODE_ROOT/.claude/skills/ — command-list claims (especially the commands chapter).
   Flag ONLY real contradictions a reader would act on wrongly — a chapter naming a command that no longer exists, a cadence that changed, a guard added/removed, a desk or project the maps don't show. Do not nitpick tone or wording.

3) WRITE the drift report (markdown) → $HB_REPORT_FILE
   Frontmatter: topic: [harness-handbook], record_type: report, status: active, created_at: $DATESTAMP.
   Lead with a one-line summary (drift count). One block per drift: chapter file · what the chapter says · what the live system says (cite the live file) · proposed correction. If there is NO drift, the report still gets written and says so explicitly — 'audited on $DATESTAMP against pulse schedule, guard registry, Brain tree, skill roster: no drift found' — never silence.

4) WRITE a machine-readable summary sidecar (JSON, one object) → $HB_SUMMARY_FILE
   EXACTLY: {\"status\":\"OK\"|\"NEEDS_REVIEW\",\"finding_count\":<integer>,\"headline\":\"<=8 word teaser\"}
   status OK with finding_count 0 ONLY if genuinely no drift; otherwise NEEDS_REVIEW with the true count.

Do NOT send any notification — the runner buzzes deterministically from the sidecar. Do not touch any file outside the two named above."

# ── RUN the propose-only audit headless, hard-bounded by the watchdog ──
cd "$DATA" || { _hlog "FATAL: cannot cd to $DATA"; exit 1; }
_hlog "launching headless claude ($HB_MODEL, watchdog ${HB_WATCHDOG}s)…"
"$CLAUDE_BIN" -p "$HB_PROMPT" --model "$HB_MODEL" --dangerously-skip-permissions </dev/null &
CPID=$!
( sleep "$HB_WATCHDOG"; kill -9 "$CPID" 2>/dev/null ) & WPID=$!
wait "$CPID" 2>/dev/null; RC=$?
kill "$WPID" 2>/dev/null; wait "$WPID" 2>/dev/null
_hlog "claude exit: $RC"

# tile writer — args: status count summary  (argv into python, never string-interpolated)
_write_tile() {
  local status="${1:-ERROR}" count="${2:-0}" summary="${3:-}"
  python3 -c 'import json,sys; print(json.dumps({"finding_count": int(sys.argv[1]), "headline": sys.argv[2]}))' \
    "${count:-0}" "$summary" 2>/dev/null | \
    python3 "$CODE_ROOT/system/tools/emit_status.py" \
      --out "$DATA/state/status/handbook-audit.json" --desk handbook --pulse-job handbook-audit \
      --stale-after-s "$HB_STALE_AFTER_S" --status "$status" --rc 0 --summary "$summary" --json - 2>/dev/null || \
    _hlog "WARN: tile write failed (non-fatal)"
}

# ── TOOL BROKE (non-zero / watchdog kill) → tile=ERROR, no stamp (retries next tick), rc to the
#    breaker. NOT a found-drift. claude's own 75/2 are remapped to 1 — a broken tool must never
#    be laundered into Pulse's "skipped"/"held" buckets (same remap as archivist-run.lib.sh).
if [ "$RC" -ne 0 ]; then
  _write_tile "ERROR" 0 "claude exited $RC — tool broke, not drift"
  _hlog "non-zero exit — tool broke (NOT drift). No stamp; Pulse breaker handles repeats."
  if [ "$RC" -eq 75 ] || [ "$RC" -eq 2 ]; then
    _hlog "claude's own exit $RC collides with a Pulse not-a-fault code — reporting as 1 (real failure)."
    exit 1
  fi
  exit "$RC"
fi

# ── SUCCESS → read sidecar, stamp the quarter, write the tile, ONE normal-priority buzz.
#    Found-drift is SUCCESS (exit 0) — only a broken tool exits non-zero.
if [ -s "$HB_SUMMARY_FILE" ]; then
  STATUS="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("status","NEEDS_REVIEW"))' "$HB_SUMMARY_FILE" 2>/dev/null || echo NEEDS_REVIEW)"
  COUNT="$(python3 -c 'import json,sys; print(int(json.load(open(sys.argv[1])).get("finding_count",0)))' "$HB_SUMMARY_FILE" 2>/dev/null || echo 0)"
else
  _hlog "WARN: no summary sidecar — run completed but produced no machine-readable summary."
  STATUS="NEEDS_REVIEW"; COUNT="?"
fi

echo "$CURRENT_PERIOD" > "$PERIOD_STATE_FILE"
_hlog "stamped period $CURRENT_PERIOD → $PERIOD_STATE_FILE"

if [ "$STATUS" = "OK" ] && [ "$COUNT" = "0" ]; then
  _write_tile "OK" 0 "clean — no handbook drift found"
else
  # COUNT can be "?" (no sidecar) — the tile payload needs an integer; 0 + the summary carries it.
  TILE_COUNT="$COUNT"; case "$TILE_COUNT" in *[!0-9]*|"") TILE_COUNT=0 ;; esac
  _write_tile "NEEDS_REVIEW" "$TILE_COUNT" "handbook drift review ready (${COUNT} finding(s))"
fi

# ONE buzz, normal priority, clean or not: the report is filed either way; the owner's part
# is reading it and ruling on it.
# Teaser only; governor-gated; suppression is not a failure.
bash "$CODE_ROOT/shared/notify/notify-send.sh" --source "$HB_LABEL" --tags "books" \
  --title "📖 Handbook audit ready" \
  --message "handbook audit ready — ${COUNT} drift(s) found. See $(basename "$HB_REPORT_FILE") in your notes." \
  2>/dev/null || true

_hlog "done — status=$STATUS, findings=$COUNT. (exit 0: found-drift is success)"
exit 0
