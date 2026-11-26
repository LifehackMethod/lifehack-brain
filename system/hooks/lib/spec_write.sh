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
PAYLOAD="$1"; SID="$2"; WD="${3:-}"   # B2: the run folder is captured at LAUNCH (arg 3); it is never re-read after the model call
_SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUG="$(cd "$_SELF_DIR/../../.." && pwd -P)"
case "$SID" in ''|*[!A-Za-z0-9_-]*) exit 0;; esac
export CLAUDE_CODE_SESSION_ID="$SID"
OD="$HOME/.claude/run/observe"; mkdir -p "$OD"
trap 'rm -f "$OD/spec-write-$SID.pid"; rmdir "$OD/spec-launch-$SID.lock" 2>/dev/null' EXIT   # the launch lock (S2) goes with the writer
PY="$_SELF_DIR/sb_spec.py"
[ -n "$WD" ] || WD="$(python3 "$PY" flag-wd "$SID")"   # only a direct call without arg 3
FAILF="$OD/spec-fail-$SID.txt"; EVID="$WD/spec-evidence.md"
PROMPT="$OD/spec-prompt-$SID.md"; REPLY="$OD/spec-reply-$SID.txt"
TS() { date '+%Y-%m-%d %H:%M:%S'; }
fail() {   # fail <reason> — a loud gate line (marker), the fail file, the log, and spec-evidence.md when the folder exists. Never into the cwd.
  printf '%s\n' "$1" > "$FAILF"
  printf 'FAILED: could not save: %s\n' "$1" > "$OD/spec-saved-$SID.txt"
  printf '[%s] spec_write.sh: %s\n' "$(TS)" "$1" >> "$OD/spec-errors.log"
  if [ -n "$WD" ] && [ -d "$WD" ]; then printf -- '- [%s] WRITER FAILED: %s\n' "$(TS)" "$1" >> "$EVID"; fi
  rm -f "$PROMPT" "$REPLY"
  exit 0
}
[ -n "$WD" ] && [ -d "$WD" ] || fail "no run folder to write into (${WD:-empty}); nothing was written"
sleep "${SPEC_WAIT:-2}"
python3 "$PY" active "$SID" || exit 0            # the run finished or was dropped while we waited: nothing to do (the flag is cleared)
[ -r "$PAYLOAD" ] || fail "the end-of-turn payload was unreadable"
INFO_LINE="$(python3 "$PY" build-prompt "$PAYLOAD" "$PROMPT" "$SID" "$WD" 2>/dev/null | head -1)"
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
RES="$(python3 "$PY" apply "$REPLY" "$SID" "$NEW_OFF" "$WD" 2>&1 | head -1)"
# B4: APPLIED (saved N or nothing to save) / FAILED (rejected, aborted, unparseable: the offset did not advance, the next run retries)
case "$RES" in APPLIED*) rm -f "$FAILF";; FAILED:*) fail "${RES#FAILED: }";; *) fail "could not apply the reply: ${RES:-no reason}";; esac
SPN="$(printf '%s' "$RES" | sed -n 's/.*spec=\([0-9][0-9]*\).*/\1/p')"; SPN="${SPN:-0}"
PKT="$(printf '%s' "$RES" | sed -n 's/.*packet=\([0-9][0-9]*\).*/\1/p')"; PKT="${PKT:-0}"
REJ="$(printf '%s' "$RES" | sed -n 's/.*rejected=\([0-9][0-9]*\).*/\1/p')"; REJ="${REJ:-0}"
REJNOTE=""; [ "$REJ" -gt 0 ] && REJNOTE=" ($REJ record(s) rejected, see spec-evidence.md)"
# The DONE-MARKER, then the questioner chained at once: marker present => the fresh read is already running.
if [ "$SPN" -gt 0 ] || [ "$PKT" -gt 0 ]; then
  printf 'saved %s spec lines · %s packet lines%s\n' "$SPN" "$PKT" "$REJNOTE" > "$OD/spec-saved-$SID.txt"
else
  printf 'nothing to save\n' > "$OD/spec-saved-$SID.txt"
fi
rm -f "$OD/spec-questions-$SID.txt" "$OD/spec-questions-$SID.txt.shown"   # the last round's questions never linger
nohup bash "$_SELF_DIR/spec_questions.sh" "$SID" </dev/null >/dev/null 2>&1 &
echo $! > "$OD/spec-questions-$SID.pid"; disown
rm -f "$PROMPT" "$REPLY"
exit 0
