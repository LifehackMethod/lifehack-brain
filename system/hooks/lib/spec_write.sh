#!/usr/bin/env bash
# ⛔ SWITCHED OFF (2026-11-25, Enver's "just enough" ruling): end_of_turn_checks.sh no longer launches this
# background writer; the skill-builder itself writes <run folder>/draft-spec.md at the end of every round. The file
# is kept, not wired: removing the launch was the switch, and nothing in this script changed.
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: SPEC WRITER (round 2b, brief Y/B3). While a skill-builder run is live, after each turn ONE medium-tier model call reads
#      that turn plus the current draft spec and fills ONLY the blanks the turn gives evidence for. Before this, the draft spec
#      never existed in the live run (2026-11-24) and nothing showed whether it moved. It runs DETACHED (launched by
#      end_of_turn_checks.sh) because a model call takes ~15 s and a Stop hook must not wait.
# GUARDS: none — a background worker. Never blocks a turn. One job per session at a time (the launcher's pid file). SOLE WRITER of
#      <run folder>/draft-spec.md during a run and of spec-evidence.md beside it. The model gets Read only (run_model); every
#      edit is applied by CODE (lib/sb_spec.py apply): blanks and unconfirmed lines only, each new line marked [inferred] unless
#      the person's own words are quoted, confirmed lines checked intact before the one atomic rename.
# REDIRECT: the quoted evidence is <run folder>/spec-evidence.md; on any failure ONE line goes to ~/.claude/run/observe/spec-fail-<sid>.txt
#      (shown once on the next spec line) and a WRITER FAILED line to spec-evidence.md.
# SIGNPOST: model tier = `medium` via system/tools/model.lib.sh (never a model id). Mechanics = system/hooks/lib/sb_spec.py. The
#      reporter that counts the result = same file (report), counter = skill-builder scripts/completion.py.
# FAIL_POSTURE: degrade-safe — every failure is reported through the fail file and spec-evidence.md, never as a crash.
# UPDATED: 2026-11-25 (new, 2b-Y)
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
if ! RMSG="$(run_model medium "$PROMPT" "$REPLY" 2>&1)"; then
  reason="$(printf '%s\n' "$RMSG" | grep -F '[run_model] FAILED:' | head -1 | sed 's/.*FAILED: //' | cut -c1-200)"
  fail "${reason:-the model call failed}"
fi
RES="$(python3 "$PY" apply "$REPLY" "$SID" "$NEW_OFF" 2>&1 | head -1)"
case "$RES" in APPLIED*) rm -f "$FAILF";; *) fail "could not apply the reply: ${RES:-no reason}";; esac
rm -f "$PROMPT" "$REPLY"
exit 0
