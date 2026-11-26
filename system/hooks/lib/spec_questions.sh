#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: THE FRESH QUESTIONER (brief 2f, 2026-11-25). After the gated writer saves a round's answers, the NEXT round's
# questions must come from a FRESH read of the saved spec, never from the long conversation. This detached job is
# chained by spec_write.sh immediately after it writes the done-marker (marker present => questioner already launched).
# It reads nothing but the saved spec (and, at 4.3, the checked findings file), builds its prompt in code
# (sb_spec.py build-questions), calls ONE medium-tier model (Sonnet via model.lib.sh — the tier is named here, the
# model id never is), and writes the questions to $OD/spec-questions-<sid>.txt for `sb_spec.py gate` to hand over.
# GUARDS: none — a background worker. Never blocks a turn. One per session at a time (its pid file); killed with the
# writer's own kill order (this script's trap). Never the conversation: the prompt is built from the saved spec only.
# REDIRECT: the questions file is $OD/spec-questions-<sid>.txt (consumed to .shown by sb_spec.py gate); on any failure
# it holds the single line "NONE (the fresh read failed)".
# SIGNPOST: prompt mechanics = system/hooks/lib/sb_spec.py (build-questions / questions-out); tier = `medium` via
# system/tools/model.lib.sh (never a model id). The writer that chains this = system/hooks/lib/spec_write.sh.
# FAIL_POSTURE: degrade-safe — every failure becomes the failure line in the questions file, never a crash; the gate
# says "the fresh read failed" and the model asks no new numbered questions that round.
# UPDATED: 2026-11-25 (new, brief 2f)
# ─────────────────────────────────────────────────────────────────────────────
# spec_questions.sh <session-id>
# Env: SPEC_Q_MODEL_TIMEOUT (default 240), LIFEHACK_MODEL_STUB (tests only, see model.lib.sh).
set +e
SID="$1"
_SELF_DIR="$(cd "$(dirname "$0")" && pwd -P)"
case "$SID" in ''|*[!A-Za-z0-9_-]*) exit 0;; esac
export CLAUDE_CODE_SESSION_ID="$SID"
OD="$HOME/.claude/run/observe"; mkdir -p "$OD"
trap 'rm -f "$OD/spec-questions-$SID.pid"' EXIT
PY="$_SELF_DIR/sb_spec.py"

python3 "$PY" active "$SID" || exit 0 # the run finished or was dropped while we waited: nothing to ask
WD="$(python3 "$PY" flag-wd "$SID")"
[ -n "$WD" ] && [ -d "$WD" ] || exit 0
QOUT="$OD/spec-questions-$SID.txt"
failq() { printf 'NONE (the fresh read failed)\n' > "$QOUT"; exit 0; }
PROMPT="$OD/spec-qprompt-$SID.md"; REPLY="$OD/spec-qreply-$SID.txt"
INFO="$(python3 "$PY" build-questions "$SID" "$PROMPT" "${SPEC_Q_FINDINGS:-}" 2>/dev/null | head -1)"
case "$INFO" in OK*) ;; *) failq;; esac

. "$_SELF_DIR/../../tools/model.lib.sh" 2>/dev/null || failq
export MODEL_TIMEOUT="${SPEC_Q_MODEL_TIMEOUT:-240}"
export SPEC_WRITER_RUNNING=1 # the nested model session inherits this: its hooks never start or flag a run
RMSG="$(run_model medium "$PROMPT" "$REPLY" 2>&1)"
if [ $? -ne 0 ]; then
  printf '%s\n' "the questioner's model call failed: $(printf '%s\n' "$RMSG" | grep -F '[run_model] FAILED:' | head -1 | sed 's/.*FAILED: //' | cut -c1-160)" >> "$WD/spec-evidence.md" 2>/dev/null # allow-silence: evidence-log write is best effort; the questions file already says NONE
  failq
fi
python3 "$PY" questions-out "$REPLY" "$QOUT" >/dev/null 2>&1 || failq
rm -f "$PROMPT" "$REPLY"
exit 0
