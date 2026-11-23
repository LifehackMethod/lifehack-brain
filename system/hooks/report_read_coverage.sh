#!/bin/bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "report_read_coverage.sh" "SubagentStop" "" 2>/dev/null || true' EXIT
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: helpers skim whole documents and say they read them — debt ledger §9 item 41 (reading
#      verification for every helper) and §9 item 42 (the reading harness: code drives the
#      reading), carried into canon as proposed failure mode 22, "the read nobody saw". A model
#      is structurally worst at noticing what it skipped, so its own word proves nothing. When
#      a helper STOPS, its record (agent_transcript_path) shows exactly which lines of which
#      files it opened with the Read tool; shared/tools/read_coverage.py counts that. Code, not
#      a session's judgment, runs this check on EVERY helper stop — the counter is the layer
#      that catches what the sign (the chart at first launch) missed.
# GUARDS: Nothing. OBSERVE-shaped (SubagentStop cannot block). It reports only when a DOCUMENT
#      (.md/.txt — a builder opening part of a code file is normal) was read only PARTIALLY, or
#      a document was read through the shell (not countable), or the record itself could not be
#      counted. Exit 0 always.
# ⚠ DELIVERY: a message printed on the SubagentStop event is NOT shown to the model. The status
#      tile IS the delivery — it lands on Enver's status screen (<brain_root>/status/),
#      written through system/tools/emit_status.py (its own envelope; never a hand-written tile),
#      plus one dated line in the plugin's state folder. No stdout is needed for this event.
# REDIRECT: the counter's tool is shared/tools/read_coverage.py (card 6.3). The structural fix
#      for a partial read is the reading tool, shared/tools/read_harness.py --whole (cards 5-6):
#      send the reading there instead of into a helper.
# SIGNPOST: the RULE is canon's proposed failure mode 22 "the read nobody saw" (debt ledger §9
#      items 41/42) and the chart in canon/helpers-and-model-routing-sop.md. A change to what is
#      reported, or the reporting threshold, goes there and to the person — never to this hook.
# FAIL_POSTURE: degrade-safe — any error (unreadable stdin, missing tool, unwritable state)
#      exits 0 silently; a missed count costs a tile, never a wrong action or a stopped turn.
# UPDATED: 2026-11-19 (built as reading-harness plan card 7.1(b); patch kit, applied by hand)
# ─────────────────────────────────────────────────────────────────────────────
set +e

PR="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
. "$PR/system/hooks/lib/roundb.sh" 2>/dev/null || roundb_on() { return 0; }
roundb_on read_coverage_report || exit 0

STATE_DIR="${LIFEHACK_STATE_DIR:-$HOME/.claude/run}"
LOGDIR="$STATE_DIR/reading-harness"
LOG="$LOGDIR/coverage.log"

INPUT=$(cat 2>/dev/null)
TPATH=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    print(json.load(sys.stdin).get("agent_transcript_path", "") or "")
except Exception:
    print("")
' 2>/dev/null)
SESSION_ID=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    print(json.load(sys.stdin).get("session_id", "") or "")
except Exception:
    print("")
' 2>/dev/null)

[ -n "$TPATH" ] || exit 0          # no record handed over: nothing to count
[ -f "$TPATH" ] || exit 0          # missing record: degrade-safe, count nothing

COVERAGE=$(python3 "$PR/shared/tools/read_coverage.py" "$TPATH" --documents-only 2>/dev/null)
RC=$?

# exit 0: every document full, nothing uncountable — say nothing anywhere.
[ "$RC" = 0 ] && exit 0
# rc 1 = something partial or not countable; rc 4 = the record could not be read. Both report.

# The dated line in the plugin's state folder (never inside any repo).
mkdir -p "$LOGDIR" 2>/dev/null
STAMP=$(date '+%Y-%m-%d %H:%M:%S')
REASON="partial-or-uncountable"; [ "$RC" = 4 ] && REASON="record-unreadable"
{ printf '%s | session=%s | rc=%s | %s | %s\n' "$STAMP" "${SESSION_ID:-unknown}" "$RC" "$REASON" "$(printf '%s' "$COVERAGE" | tr '\n' ' § ' | cut -c1-2000)"; } >> "$LOG" 2>/dev/null

# The status tile, through emit_status.py's own envelope (never a hand-written tile).
TPATH="$TPATH" COVERAGE="$COVERAGE" RC="$RC" SESSION_ID="$SESSION_ID" PR="$PR" python3 - "$PR" <<'PYEOF' 2>/dev/null
import json, os, subprocess, sys

pr = os.environ["PR"]
rc = int(os.environ["RC"])
coverage = os.environ["COVERAGE"]
session = os.environ.get("SESSION_ID", "unknown")

sys.path.insert(0, os.path.join(pr, "shared"))
try:
    import brain_root
    source, root = brain_root.resolve_brain_root()
except Exception:
    root = None
if not root:
    sys.exit(0)   # no brain root: no tile; the dated line above is the remaining record

sys.path.insert(0, os.path.join(pr, "system", "tools"))
try:
    from emit_status import emit_status
except Exception:
    sys.exit(0)   # no tile writer on this install: degrade-safe; the log line stands

files = [ln for ln in coverage.splitlines() if ln and not ln.startswith(("EXAMINED", "WARNING", "COULD"))]
tile = os.path.join(root, "status", "reading-harness-coverage.json")
try:
    emit_status(
        tile,
        desk="reading-harness",
        pulse_job="read-coverage-counter",
        stale_after_s=21600,
        status="ERROR" if rc == 4 else "NEEDS_REVIEW",
        rc=rc,
        summary=("a helper's record could not be counted" if rc == 4
                 else f"{len(files)} document(s) read partially or not countable by a helper"),
        payload={"files_report": files, "session_id": session,
                 "note": "a message on SubagentStop is not shown to the model; this tile is the delivery"},
        required_payload=("files_report", "session_id"),
        emit_mode="pulse",
    )
except Exception:
    sys.exit(0)   # contract refused it: degrade-safe, never crash the hook
PYEOF

exit 0
