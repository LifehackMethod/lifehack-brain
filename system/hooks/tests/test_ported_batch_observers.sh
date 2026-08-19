#!/bin/bash
# test_ported_batch_observers.sh — the three NON-BLOCKING hooks from the SECURITY port.
#
# observability_logger (PostToolUse/*) · session_flight_recorder (Stop) · rating_capture
# (UserPromptSubmit). None of them can block; all three must ALWAYS exit 0. What they can do is
# WRITE — and two of them write into the person's notes root.
#
# ⛔⛔ READ THIS BEFORE EDITING. Twice on this migration a helper ran these hooks and created real
# files in the operator's actual notes root (~/AI Brain/data/system/: flight-log.jsonl,
# learnings-signals.jsonl, learnings.md). A prompt that forbids execution is not a sandbox.
#
# ⭐ AND THE OBVIOUS FIX IS NOT ENOUGH — MEASURED HERE, 2026-08-14. "Pass an isolated root inline"
# fails open on a typo: brain_root.py honours $LIFEHACK_ROOT only "if set AND a real directory", so
#   LIFEHACK_ROOT=/tmp/does-not-exist  ->  resolves to /Users/<person>/AI Brain/data
# — straight back to the live root, silently. Setting the variable is NOT the protection. The
# protection is ASKING brain_root.py what it actually resolved and REFUSING to continue if it is not
# the sandbox. That check is the first thing this file does, and it is the point of this file.
#
# Run: bash system/hooks/tests/test_ported_batch_observers.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$HOOKS/../.." && pwd)"

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/lifehack-hooktest.XXXXXX")" || exit 1
export LIFEHACK_ROOT="$SANDBOX"
BUFFER="/tmp/lifehack-observability-buffer.jsonl"

cleanup() { rm -rf "$SANDBOX"; }
trap cleanup EXIT

# ── THE FAIL-CLOSED ISOLATION GATE — never delete this ────────────────────────
RESOLVED="$(python3 "$REPO/shared/brain_root.py" --quiet 2>/dev/null)"
if [ "$RESOLVED" != "$SANDBOX" ]; then
  echo "REFUSING TO RUN: brain_root.py resolved to '$RESOLVED', not the sandbox '$SANDBOX'."
  echo "These hooks WRITE. Running now would create files in a real notes root — which has already"
  echo "happened twice on this migration. Fix the sandbox, do not weaken this check."
  exit 1
fi
echo "isolated notes root: $RESOLVED"

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
check()  { [ "$3" = "$2" ] && ok || bad "$1" "expected exit $2, got $3"; }
exists() { [ -e "$2" ] && ok || bad "$1" "expected file $2 to exist"; }
absent() { [ -e "$2" ] && bad "$1" "file $2 should NOT exist" || ok; }
lines()  { got=$(wc -l < "$2" 2>/dev/null | tr -d ' '); [ "$got" = "$3" ] && ok || bad "$1" "expected $3 lines in $2, got ${got:-0}"; }

# ── observability_logger.sh — PostToolUse, matcher: * ─────────────────────────
# One compact JSON line per tool call, to a /tmp buffer only — never the notes root on the hot path.
# ⚠ This hook is named in hook-sop.md's DO-NOT-BUILD list: it once read its payload from $1 instead
# of stdin and captured ZERO entries under 300+ daily calls while reporting success throughout. The
# "two real calls land" case below is what would have caught that.
G="$HOOKS/observability_logger.sh"
[ -f "$G" ] || { echo "CANNOT RUN: no hook at $G"; exit 1; }
rm -f "$BUFFER"
echo "── observability_logger: every tool call leaves a line, garbage leaves none ──"
printf '%s' '{"tool_name":"Bash","session_id":"s","cwd":"/tmp","tool_input":{"command":"gws calendar list"},"tool_response":{"exit_code":0}}' | bash "$G" >/dev/null 2>&1
check "a gws Bash call"        0 "$?"
printf '%s' '{"tool_name":"Read","session_id":"s","cwd":"/tmp","tool_input":{"file_path":"/tmp/x"}}' | bash "$G" >/dev/null 2>&1
check "an ordinary Read"       0 "$?"
printf '%s' 'GARBAGE NOT JSON' | bash "$G" >/dev/null 2>&1
check "malformed input"        0 "$?"
printf '%s' '' | bash "$G" >/dev/null 2>&1
check "empty input"            0 "$?"
lines "two real calls land, the two bad ones do not" "$BUFFER" 2
grep -q '"gws_command"' "$BUFFER" 2>/dev/null && ok || bad "gws audit string" "no gws_command captured"

# ── session_flight_recorder.sh — Stop ─────────────────────────────────────────
# Writes the flight-log line, flushes the observability buffer into the notes root, stubs
# learnings.md, and nudges on stderr when /save was never called.
G="$HOOKS/session_flight_recorder.sh"
[ -f "$G" ] || { echo "CANNOT RUN: no hook at $G"; exit 1; }
echo "── session_flight_recorder: the session leaves a trace and the buffer is flushed ──"
TRANSCRIPT="$SANDBOX/transcript.jsonl"
printf '%s\n' \
  '{"timestamp":"2026-08-14T19:00:00Z","type":"user"}' \
  '{"type":"tool_use","name":"Write"}' \
  '{"type":"tool_use","name":"Edit"}' \
  '{"type":"tool_use","name":"Bash"}' > "$TRANSCRIPT"
ERR=$(printf '{"session_id":"s","transcript_path":"%s","cwd":"/tmp"}' "$TRANSCRIPT" | bash "$G" 2>&1 >/dev/null)
check  "a Stop hook always exits 0"     0 "$?"
exists "flight-log written"             "$SANDBOX/system/flight-log.jsonl"
exists "observability flushed"          "$SANDBOX/system/observability/$(date +%Y-%m-%d).jsonl"
absent "buffer removed after flush"     "$BUFFER"
exists "learnings.md stubbed"           "$SANDBOX/system/learnings.md"
printf '%s' "$ERR" | grep -q '/save' && ok || bad "/save nudge" "no nudge on stderr when /save absent"
grep -q '"tool_calls":3' "$SANDBOX/system/flight-log.jsonl" 2>/dev/null && ok || bad "tool_calls" "expected 3"
grep -q '"files_written":2' "$SANDBOX/system/flight-log.jsonl" 2>/dev/null && ok || bad "files_written" "expected 2 (Write+Edit)"
# An existing learnings.md must never be overwritten — it is the person's file, not ours.
echo "MY REAL NOTES" > "$SANDBOX/system/learnings.md"
printf '{"session_id":"s","transcript_path":"%s","cwd":"/tmp"}' "$TRANSCRIPT" | bash "$G" >/dev/null 2>&1
grep -q 'MY REAL NOTES' "$SANDBOX/system/learnings.md" && ok || bad "learnings.md preserved" "the stub overwrote a real file"

# ── rating_capture.sh — UserPromptSubmit ──────────────────────────────────────
# Logs an explicit 1-10 rating; <=3 also writes a failure-capture file. Must never block a prompt.
G="$HOOKS/rating_capture.sh"
[ -f "$G" ] || { echo "CANNOT RUN: no hook at $G"; exit 1; }
echo "── rating_capture: a rating is logged, a sentence starting with a digit is not ──"
rate() { # rate <label> <exp-rc> <prompt>
  python3 -c "
import json,sys
print(json.dumps({'prompt':sys.argv[1],'session_id':'s','transcript_path':'/tmp/t.jsonl'}))" "$3" 2>/dev/null \
    | bash "$G" >/dev/null 2>&1
  check "$1" "$2" "$?"
}
SIG="$SANDBOX/system/learnings-signals.jsonl"
rate "N - comment"        0 "9 - great work"
rate "low rating"         0 "2 - completely wrong"
rate "N/10 form"          0 "10/10 nice"
rate "bare number"        0 "8"
rate "NOT a rating"       0 "3 items to fix today"
rate "not a rating either" 0 "5 minute break then continue"
lines "only the four real ratings logged" "$SIG" 4
ls "$SANDBOX/system/learnings/"*low-rating-2.md >/dev/null 2>&1 && ok || bad "failure capture" "no file for the <=3 rating"

# ── the whole point: nothing escaped the sandbox ──────────────────────────────
echo "── containment ──"
STRAY=$(find "$SANDBOX" -type f | wc -l | tr -d ' ')
[ "$STRAY" -gt 0 ] && ok || bad "sandbox" "these hooks wrote nothing at all — suspect the test"
FINAL="$(python3 "$REPO/shared/brain_root.py" --quiet 2>/dev/null)"
[ "$FINAL" = "$SANDBOX" ] && ok || bad "containment" "root drifted mid-run to '$FINAL'"

echo
if [ "$fail" -eq 0 ]; then
  echo "PASS — $pass cases, 0 failures. All writes contained in $SANDBOX"
  exit 0
fi
echo "FAIL — $fail of $((pass+fail)) cases failed."
exit 1
