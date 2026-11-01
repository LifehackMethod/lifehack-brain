#!/bin/bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "sanitize_connector_output.sh" "PostToolUse" "mcp__.*" 2>/dev/null || true' EXIT
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: PHASE 3b.7 item A.3, "guard the doors, trust the house" (locked by Enver 2026-11-01). A
#      connector (an MCP tool: Gmail, Slack, Drive, Calendar, any server added later) hands its
#      result straight to the model. An email body or a Slack message is text anyone can write, so
#      it is the cheapest place to plant an instruction. This is the connector DOOR: every connector
#      result goes through the existing sanitizer (system/tools/sanitize.py, document mode) and
#      injection scanner (system/tools/safe_input.py) on its way in, and the cleaned result is
#      swapped in. Local files are trusted once they are on the machine; this is where outside
#      text arrives, so this is where it is scanned.
# GUARDS: nothing is blocked. PostToolUse, matcher mcp__.* (a regex: every mcp__<server>__<tool>,
#      including mcp__claude_ai_Slack__*, mcp__claude_ai_Gmail__*, and plugin-bundled
#      mcp__plugin_<plugin>_<server>__*). Hidden characters (zero-width, bidi, controls) are
#      stripped; a flagged injection span becomes [REDACTED-FLAGGED: <label>] with a one-line note.
# HOW: hookSpecificOutput.updatedToolOutput (+ updatedMCPToolOutput, same value) — field names per
#      code.claude.com/docs/en/hooks, read 2026-11-01. NOT decision:block: on PostToolUse that only
#      adds a reason and "Claude still sees the original output". A clean result prints nothing.
# REDIRECT: n/a (nothing is refused). A withheld result says to retry the call.
# FAIL_POSTURE: closed. Any error — python3 missing, the lib missing, the sanitizer crashing,
#      timing out (alarm, default 20 s) or returning something that is not text, unparseable input,
#      the lib printing anything but the expected JSON — replaces the result with a "content
#      withheld" note. The raw text is never passed on from an error path. The one failure this
#      file cannot catch — not being started at all (file missing, no bash) — is covered by the
#      registration: the register row carries on_failure=block, emitted as "onFailure": "block"
#      (Claude Code v2.1.295+; 3b.7 A2). The hooks page does not say what "block" does on
#      PostToolUse, where the tool has already run; that is unverified live.
# LEDGER: findings also go to the existing Sentinel ledger (safe_input.route_findings, source
#      connector:<server>), the same gate safe_read.py uses; it never changes what is emitted.
# SIGNPOST: plan <notes>/plans/v2.plan.md PHASE 3b.7 A; logic system/hooks/lib/connector_sanitize.py;
#      tests system/hooks/tests/test_sanitize_connector_output.sh.
# ─────────────────────────────────────────────────────────────────────────────

_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd -P)"
_WITHHELD='{"hookSpecificOutput":{"hookEventName":"PostToolUse","updatedToolOutput":"[content withheld: the Lifehack connector sanitizer could not run on this connector result, so the raw text was not passed on (fail closed). Nothing changed at the source. Retry the call; if it keeps happening, report it and read the item another way.]","updatedMCPToolOutput":"[content withheld: the Lifehack connector sanitizer could not run on this connector result, so the raw text was not passed on (fail closed). Nothing changed at the source. Retry the call; if it keeps happening, report it and read the item another way.]"}}'
withhold() { printf '%s\n' "$_WITHHELD"; exit 0; }

INPUT="$(cat 2>/dev/null)" || withhold
command -v python3 >/dev/null 2>&1 || withhold
[ -n "$_HOOKDIR" ] && [ -f "$_HOOKDIR/lib/connector_sanitize.py" ] || withhold

OUT="$(printf '%s' "$INPUT" | python3 "$_HOOKDIR/lib/connector_sanitize.py" 2>/dev/null)" || withhold
case "$OUT" in
  "__PASS__") exit 0 ;;
  '{"hookSpecificOutput": {"hookEventName": "PostToolUse", "updatedToolOutput": '*) printf '%s\n' "$OUT"; exit 0 ;;
  *) withhold ;;
esac
