#!/bin/bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "inject_helper_chart.sh" "PreToolUse" "Agent" 2>/dev/null || true' EXIT
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: helpers skim whole documents and report the read as complete — debt ledger §9 item 42
#      ("the AI answers one section at a time"; 4 of 6 GLM readers skimmed long documents while
#      reporting "read in full: yes") and §9 item 41 (reading verification for every helper;
#      2 of 6 GLM readers silently skipped half a document, caught only by a code check). Canon
#      carries this as proposed failure mode 22, "the read nobody saw": a read is verified by
#      what the reader OPENED, never by its word. The fix's lightest layer is the SIGN: the
#      chart for choosing a helper, shown to the session the moment it first launches one, so
#      launch two onward is steered by the approved decision tree (Enver, approved 2026-11-19:
#      "if the main window likes it we can proceed"). Measured channel: additionalContext from a
#      PreToolUse hook on Agent was SEEN by the session 4 of 4 runs; plain stdout, stderr and
#      permissionDecisionReason were each NOT seen, 1 of 1 (experiments/launch-message-channels/).
# GUARDS: Nothing. This hook NEVER denies, NEVER asks, never outputs on a repeat launch. It is
#      pure injection, once per session, on the first Agent spawn only (a per-session_id marker
#      file under ${LIFEHACK_STATE_DIR:-$HOME/.claude/run}). The every-message one-liner (the
#      delegation standing line) covers the FIRST launch, which this hook cannot steer.
# REDIRECT: the chart text itself names the route for every branch; its ONE home is
#      canon/helpers-and-model-routing-sop.md between <!-- helper-chart:start --> and
#      <!-- helper-chart:end --> (Enver: "i don't want it in claude.md ... i also don't need it
#      every turn"). This hook holds NO COPY of the chart — it prints whatever canon carries.
# SIGNPOST: the RULE (the chart and when the reading tool takes over) is codified in
#      canon/helpers-and-model-routing-sop.md. A change to the chart or its delivery goes THERE
#      and to the person; never edit this hook to change what the chart says.
# FAIL_POSTURE: degrade-safe — any error (unreadable stdin, missing canon, missing markers,
#      unwritable marker file) exits 0 with no output or with the one-line fallback text. A
#      missing chart costs a sign, never a wrong action. A missing-marker session may see the
#      chart twice; a session is never blocked or slowed by this hook.
# UPDATED: 2026-11-19 (built as reading-harness plan card 7.1(a); patch kit, applied by hand)
# ─────────────────────────────────────────────────────────────────────────────
set +e

. "${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}/system/hooks/lib/roundb.sh" 2>/dev/null || roundb_on() { return 0; }
roundb_on helper_chart || exit 0

# Drain stdin; the only field we need is session_id.
INPUT=$(cat 2>/dev/null)
SESSION_ID=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    print(json.load(sys.stdin).get("session_id", "") or "")
except Exception:
    print("")
' 2>/dev/null)

STATE_DIR="${LIFEHACK_STATE_DIR:-$HOME/.claude/run}"
MARKER="$STATE_DIR/helper-chart-shown"
# No session id, or a marker we cannot write: fire the chart anyway (once now is better than never).
if [ -n "$SESSION_ID" ] && mkdir -p "$MARKER" 2>/dev/null && [ -f "$MARKER/$SESSION_ID" ]; then
  exit 0   # later launch in this session: silence, exit 0
fi

CANON="${CLAUDE_PLUGIN_ROOT:-}/canon/helpers-and-model-routing-sop.md"
CHART=""
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -r "$CANON" ]; then
  CHART=$(awk '/<!-- helper-chart:start -->/{f=1;next} /<!-- helper-chart:end -->/{f=0} f' "$CANON" 2>/dev/null)
  CHART=$(printf '%s' "$CHART" | sed -e 's/^[[:space:]]*$//' | cat -s)
fi

if [ -n "$CHART" ]; then
  TEXT="HELPER CHART (shown once, at your first helper launch — it steers launches from here on; the every-message line covers this first one): the chart for choosing a helper. $CHART"
else
  # Markers missing or canon unreadable: one line naming the file, plus a line on stderr.
  TEXT="HELPER CHART: the chart for choosing a helper lives in canon/helpers-and-model-routing-sop.md between the <!-- helper-chart:start --> and <!-- helper-chart:end --> markers, which are missing or unreadable on this install — read that file before choosing a helper or sending one a document someone will rely on."
  printf '%s\n' "inject_helper_chart.sh: helper-chart markers not found in canon/helpers-and-model-routing-sop.md (expected <!-- helper-chart:start --> / <!-- helper-chart:end -->); sent the one-line fallback instead" >&2
fi

printf '%s' "$TEXT" | python3 -c '
import sys, json
text = sys.stdin.read()
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": text}}))
' 2>/dev/null || exit 0

# Mark it shown only after the output was produced.
[ -n "$SESSION_ID" ] && mkdir -p "$MARKER" 2>/dev/null && : > "$MARKER/$SESSION_ID" 2>/dev/null
exit 0
