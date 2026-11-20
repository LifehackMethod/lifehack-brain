#!/bin/bash
# test_inject_helper_chart.sh: card 7.1(a) — the chart at first launch (PreToolUse, matcher Agent).
# ALLOW cases first: the hook NEVER blocks (exit 0 on every input, including garbage).
# Fed the real payloads from the launch-message-channels / reader-hard-block experiments,
# SCRUBBED: every /Users/<name> path and email replaced with placeholders.
# Run: bash system/hooks/tests/test_inject_helper_chart.sh   (exit 0 = all pass)
HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN="$(cd "$HOOKS/../.." && pwd)"
HOOK="$HOOKS/inject_helper_chart.sh"
SB="$(mktemp -d "${TMPDIR:-/tmp}/chart7a.XXXXXX")"; trap 'rm -rf "$SB"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

mkdir -p "$SB/system/hooks/lib" "$SB/canon"
cp "$PLUGIN/system/hooks/lib/roundb.sh" "$SB/system/hooks/lib/roundb.sh"
# the switch line is absent from the sandbox's roundB.conf, so every ON case passes the env
# override the switch reader honors (ROUNDB_<NAME>=on); the OFF case passes =off.
export ROUNDB_HELPER_CHART=on
CHSW=on
CH() { env -i PATH="$PATH" HOME="$SB/home" LIFEHACK_STATE_DIR="$SB/state" CLAUDE_PLUGIN_ROOT="$SB" ROUNDB_HELPER_CHART="$CHSW" bash "$HOOK"; }

canon_fixtures() {  # canon copy with or without the markers
  mkdir -p "$SB/canon"
  if [ "$1" = with ]; then
    { echo "intro"; echo "<!-- helper-chart:start -->"; echo "CHARTCODE-A: if someone will rely on a whole document, the reading tool reads it."; echo "<!-- helper-chart:end -->"; echo "outro"; } > "$SB/canon/helpers-and-model-routing-sop.md"
  else
    echo "intro only, no markers" > "$SB/canon/helpers-and-model-routing-sop.md"
  fi
}

# real-shaped payload (from experiments/reader-hard-block/ log.jsonl), scrubbed
PAYLOAD='{"session_id":"SESS-ABC-123","tool_input":{"description":"Reader plan check","prompt":"Check the plan /Users/<name>/Notes/drafts/grand-central/planning-weekly-phase.md and reply yes or no. Contact <email-redacted> if unclear."}}'
NOPAYLOAD='{"session_id":"SESS-ABC-123","tool_input":{"command":"ls -la"}}'

echo "-- ALLOW: never blocks, any input"
printf '%s' '{"tool_input":{"command":"rm -rf /"}}' | env -i PATH="$PATH" HOME="$SB/home" CLAUDE_PLUGIN_ROOT="$PLUGIN" bash "$HOOK" >/dev/null 2>&1
[ $? = 0 ] && ok || bad "garbage input" "nonzero exit"
printf '%s' 'not json at all' | env -i PATH="$PATH" HOME="$SB/home" CLAUDE_PLUGIN_ROOT="$PLUGIN" bash "$HOOK" >/dev/null 2>&1
[ $? = 0 ] && ok || bad "non-JSON stdin" "nonzero exit"
printf '%s' '' | env -i PATH="$PATH" HOME="$SB/home" CLAUDE_PLUGIN_ROOT="$PLUGIN" bash "$HOOK" >/dev/null 2>&1
[ $? = 0 ] && ok || bad "empty stdin" "nonzero exit"

echo "-- first launch: chart delivered as additionalContext, exit 0"
canon_fixtures with
OUT=$(printf '%s' "$PAYLOAD" | CH 2>/dev/null); RC=$?
[ "$RC" = 0 ] && ok || bad "first launch rc" "rc=$RC"
printf '%s' "$OUT" | python3 -c '
import json, sys
d = json.load(sys.stdin)
hs = d["hookSpecificOutput"]
assert hs["hookEventName"] == "PreToolUse", hs
assert "additionalContext" in hs, hs
assert "CHARTCODE-A" in hs["additionalContext"], hs["additionalContext"][:120]
' && ok || bad "envelope" "expected hookSpecificOutput.additionalContext carrying the chart; got: $(printf '%s' "$OUT" | head -c 200)"

echo "-- the canon copy itself is untouched (hook holds no copy of the chart)"
grep -q "CHARTCODE-A" "$HOOK" && bad "chart copy" "hook embeds chart text" || ok

echo "-- second launch, same session: silence, exit 0"
OUT2=$(printf '%s' '{"session_id":"SESS-ABC-123","tool_input":{}}' | CH 2>/dev/null); RC2=$?
[ "$RC2" = 0 ] && ok || bad "second launch rc" "rc=$RC2"
[ -z "$OUT2" ] && ok || bad "second launch silent" "got: $(printf '%s' "$OUT2" | head -c 120)"
[ -f "$SB/state/helper-chart-shown/SESS-ABC-123" ] && ok || bad "marker file" "marker not written under LIFEHACK_STATE_DIR"

echo "-- different session: chart fires again"
OUT3=$(printf '%s' '{"session_id":"SESS-OTHER-9","tool_input":{}}' | CH 2>/dev/null)
printf '%s' "$OUT3" | grep -q "CHARTCODE-A" && ok || bad "second session fires" "silent for a fresh session"

echo "-- no session_id in payload: still fires, exit 0, never blocks"
OUT4=$(printf '%s' '{"tool_input":{}}' | CH 2>/dev/null); RC4=$?
[ "$RC4" = 0 ] && ok || bad "no-session rc" "rc=$RC4"
printf '%s' "$OUT4" | grep -q "CHARTCODE-A" && ok || bad "no-session fires" "silent"

echo "-- markers missing: one-line fallback naming the canon file, stderr note, exit 0"
canon_fixtures without
OUT5=$(printf '%s' '{"session_id":"SESS-NOMARK","tool_input":{}}' | CH 2>"$SB/err.txt"); RC5=$?
[ "$RC5" = 0 ] && ok || bad "missing-markers rc" "rc=$RC5"
printf '%s' "$OUT5" | grep -q "canon/helpers-and-model-routing-sop.md" && ok || bad "fallback names canon file" "got: $(printf '%s' "$OUT5" | head -c 160)"
[ -s "$SB/err.txt" ] && ok || bad "stderr note" "stderr empty"

echo "-- switch OFF: silence (exactly the old behaviour = nothing at all)"
canon_fixtures with
CHSW=off
OUT6=$(printf '%s' '{"session_id":"SESS-OFF","tool_input":{}}' | CH 2>/dev/null); RC6=$?
CHSW=on
[ "$RC6" = 0 ] && [ -z "$OUT6" ] && ok || bad "switch off" "rc=$RC6 out=$(printf '%s' "$OUT6" | head -c 80)"

echo; echo "passed $pass, failed $fail"; [ "$fail" = 0 ]
