#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: THE GATED WRITER (brief 2f, 2026-11-25; replaced cbde479d's "the main AI writes draft-spec.md at the end of every
#      round"). While a skill-builder run is live, after each round's turn ONE small-tier model call — the writer, brief
#      prompts/subagents/spec-writer.md — reads that round's turns plus the current draft spec and the packet, and
#      returns records. It is NOT a sub-agent and NOT the main AI: it is the detached-job pattern (observe machinery);
#      the Stop hook (end_of_turn_checks.sh) launches it, and it never blocks a turn. On success it writes the
#      DONE-MARKER ($OD/spec-saved-<sid>.txt: "saved <n> spec lines · <m> packet lines" or "nothing to save") and then
#      CHAINS THE QUESTIONER (spec_questions.sh) — so marker present always means the fresh read is already running.
#      The GATE (sb_spec.py gate) turns the markers into the WAIT / SAVED lines on screen and to the model.
# GUARDS: none — a background worker. Never blocks a turn. One job per session at a time (the launcher's pid file). SOLE WRITER of
#      <run folder>/draft-spec.md and the packet during a run, and of spec-evidence.md beside it. The model gets Read only
#      (run_model); every edit is applied by CODE (lib/sb_spec.py apply): blanks and unconfirmed lines only, the packet
#      append-only, [inferred] added by code (the writer never types marks), a replaced line kept beneath marked
#      (superseded <date>), confirmed lines checked intact before the one atomic rename.
# REDIRECT: the quoted evidence is <run folder>/spec-evidence.md; on any failure ONE line goes to ~/.claude/run/observe/spec-fail-<sid>.txt
#      (shown once on the next spec line) and a WRITER FAILED line to spec-evidence.md. The stale done-marker is removed
#      by end_of_turn_checks.sh at the start of each new launch.
# SIGNPOST: model tier = `small` via system/tools/model.lib.sh (never a model id; a GLM override happens THERE). Mechanics =
#      system/hooks/lib/sb_spec.py. The questioner = system/hooks/lib/spec_questions.sh (tier medium). The reporter that
#      reads the markers = sb_spec.py (report / gate), counter = skill-builder scripts/completion.py.
# FAIL_POSTURE: degrade-safe — every failure is reported through the fail file and spec-evidence.md, never as a crash.
# UPDATED: 2026-11-25 (2f: small tier, packet records, done-marker, chains the questioner; new 2b-Y)
# ─────────────────────────────────────────────────────────────────────────────
#   spec_write.sh <stop-payload-file> <session-id>
# Env: SPEC_WAIT (seconds before reading, default 2), SPEC_MODEL_TIMEOUT (default 240), SPEC_TRANSCRIPT_CAP (chars, default 20000),
#      LIFEHACK_MODEL_STUB (tests only, see model.lib.sh).
set +e
PAYLOAD="$1"; SID="$2"
_SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUG="$(cd "$_SELF_DIR/../../.." && pwd -P)"
case "$SID" in ''|*[!A-Za-z0-9_-]*) exit 0;; esac
export CLAUDE_CODE_SESSION_ID="$SID"
OD="$HOME/.claude/run/observe"; mkdir -p "$OD"
trap 'rm -f "$OD/spec-write-$SID.pid"' EXIT
sleep "${SPEC_WAIT:-2}"
PY="$_SELF_DIR/sb_spec.py"

python3 "$PY" active "$SID" || exit 0            # the run finished or was dropped while we waited: nothing to do (the flag is cleared)
WD="$(python3 "$PY" flag-wd "$SID")"
[ -n "$WD" ] && [ -d "$WD" ] || exit 0
FAILF="$OD/spec-fail-$SID.txt"; EVID="$WD/spec-evidence.md"
TS() { date '+%Y-%m-%d %H:%M:%S'; }
fail() {   # fail <reason> — one line in spec-evidence.md, one line for the next spec line
  printf -- '- [%s] WRITER FAILED: %s\n' "$(TS)" "$1" >> "$EVID"
  printf '%s\n' "$1" > "$FAILF"
  exit 0
}
[ -r "$PAYLOAD" ] || fail "the end-of-turn payload was unreadable"
PROMPT="$OD/spec-prompt-$SID.md"; REPLY="$OD/spec-reply-$SID.txt"
INFO_LINE="$(python3 "$PY" build-prompt "$PAYLOAD" "$PROMPT" "$SID" 2>/dev/null | head -1)"
case "$INFO_LINE" in OK*) ;; *) fail "could not build the prompt: ${INFO_LINE:-no reason}";; esac
NEW_OFF="${INFO_LINE#OK}"; NEW_OFF="${NEW_OFF# }"

. "$_SELF_DIR/../../tools/model.lib.sh" 2>/dev/null || fail "cannot load model.lib.sh"
export MODEL_TIMEOUT="${SPEC_MODEL_TIMEOUT:-240}"
# no marker is demanded of run_model: a reply that lacks END-WRITE (found live: the NOTHING case) is still parsed; a cut-off record is rejected by apply
export SPEC_WRITER_RUNNING=1     # the nested model session inherits this: its hooks never start or flag a run (found live: it looped)
if ! RMSG="$(run_model small "$PROMPT" "$REPLY" 2>&1)"; then
  reason="$(printf '%s\n' "$RMSG" | grep -F '[run_model] FAILED:' | head -1 | sed 's/.*FAILED: //' | cut -c1-200)"
  fail "${reason:-the model call failed}"
fi
RES="$(python3 "$PY" apply "$REPLY" "$SID" "$NEW_OFF" 2>&1 | head -1)"
case "$RES" in APPLIED*) rm -f "$FAILF";; *) fail "could not apply the reply: ${RES:-no reason}";; esac
SPN="$(printf '%s' "$RES" | sed -n 's/.*spec=\([0-9][0-9]*\).*/\1/p')"; SPN="${SPN:-0}"
PKT="$(printf '%s' "$RES" | sed -n 's/.*packet=\([0-9][0-9]*\).*/\1/p')"; PKT="${PKT:-0}"
# The DONE-MARKER, then the questioner chained at once: marker present => the fresh read is already running.
if [ "$SPN" -gt 0 ] || [ "$PKT" -gt 0 ]; then
  printf 'saved %s spec lines · %s packet lines\n' "$SPN" "$PKT" > "$OD/spec-saved-$SID.txt"
else
  printf 'nothing to save\n' > "$OD/spec-saved-$SID.txt"
fi
rm -f "$OD/spec-questions-$SID.txt" "$OD/spec-questions-$SID.txt.shown"   # the last round's questions never linger
nohup bash "$_SELF_DIR/spec_questions.sh" "$SID" </dev/null >/dev/null 2>&1 &
echo $! > "$OD/spec-questions-$SID.pid"; disown
rm -f "$PROMPT" "$REPLY"
exit 0
