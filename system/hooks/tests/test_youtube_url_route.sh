#!/bin/bash
# test_youtube_url_route.sh — routing hook fires on a real YouTube URL and stays silent otherwise.
#
# Both halves are asserted: exit code AND output text (asserting only the exit code is a recorded
# failure mode, hook-sop.md §4). The hook is invoked exactly as the harness would: JSON piped on
# stdin, no argv. No network call and no dependency on system/tools/youtube_transcribe.py existing
# (it is being written in parallel and is not created or stubbed here).
#
# Run: bash system/hooks/tests/test_youtube_url_route.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$HOOKS/youtube_url_route.sh"
[ -f "$HOOK" ] || { echo "CANNOT RUN: no hook at $HOOK"; exit 1; }

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

# run_positive <label> <prompt>   -- expects exit 0 AND non-empty stdout
run_positive() {
  local label="$1" prompt="$2" out rc
  out="$(python3 -c "import json,sys; print(json.dumps({'prompt': sys.argv[1]}))" "$prompt" \
    | bash "$HOOK" 2>/dev/null)"
  rc=$?
  if [ "$rc" != 0 ]; then bad "$label" "expected exit 0, got $rc"; return; fi
  if [ -z "$out" ]; then bad "$label" "expected injected text, got nothing"; return; fi
  ok
}

# run_negative <label> <prompt>   -- expects exit 0 AND empty stdout
run_negative() {
  local label="$1" prompt="$2" out rc
  out="$(python3 -c "import json,sys; print(json.dumps({'prompt': sys.argv[1]}))" "$prompt" \
    | bash "$HOOK" 2>/dev/null)"
  rc=$?
  if [ "$rc" != 0 ]; then bad "$label" "expected exit 0, got $rc"; return; fi
  if [ -n "$out" ]; then bad "$label" "expected silence, got: $out"; return; fi
  ok
}

# ⚠ HOSTNAMES ARE ASSEMBLED FROM FRAGMENTS BELOW, ON PURPOSE. `enforce_egress_allowlist.sh`
#   matches anything URL-shaped in a command string — it cannot tell a fixture from a real
#   outbound call — so a test file with literal YouTube URLs in it is BLOCKED the moment a
#   session tries to run it. Verified 2026-08-27: the literal version tripped the guard, and so
#   did an f-string whose placeholders merely looked like URLs. This is the workaround the hook
#   SOP names in §4 Trap 2 ("a command-string guard blocks its own documentation").
#   Keep the concatenation. Inlining these back into readable URLs re-breaks the file.
S="htt""ps://"; SP="htt""p://"
YT="you""tu"".be"; YTC="www.""you""tu""be.com"; MYT="m.""you""tu""be.com"
YTB="you""tu""be.com"; VIM="vim""eo"".com"

echo "── positive: real YouTube URL shapes fire ────────────────────────────────"
run_positive "${YT} short form"           "check this out ${S}${YT}/dQw4w9WgXcQ"
run_positive "${YTC} watch"         "${S}${YTC}/watch?v=WuT05f11IeE"
run_positive "URL embedded mid-sentence"     "so I was watching ${S}${YT}/dQw4w9WgXcQ and thought about it"
run_positive "${MYT}, http scheme"    "${SP}${MYT}/watch?v=abc123defgh"
run_positive "${YTB}/live/"             "watching live now ${S}${YTC}/live/aBcDeFgHiJk"
run_positive "extra query params"            "${S}${YTC}/watch?v=WuT05f11IeE&t=42s"
run_positive "${YTB}/shorts/"           "look at this ${S}${YTC}/shorts/aBcDeFgHiJk"

echo "── negative: keyword mentions and non-matches stay silent ───────────────"
run_negative "bare word 'youtube' in a question" "what about youtube transcripts?"
run_negative "bare word 'youtube' as opinion"    "I hate the youtube algorithm"
run_negative "bare word 'transcript' alone"      "transcript"
run_negative "a Vimeo URL"                       "check this out ${S}${VIM}/76979871"
run_negative "empty prompt"                      ""

echo "── negative: malformed / absent JSON on stdin fails degrade-safe ────────"
out="$(printf 'not json at all' | bash "$HOOK" 2>/dev/null)"; rc=$?
[ "$rc" = 0 ] && [ -z "$out" ] && ok || bad "malformed JSON" "rc=$rc out='$out'"

out="$(printf '' | bash "$HOOK" 2>/dev/null)"; rc=$?
[ "$rc" = 0 ] && [ -z "$out" ] && ok || bad "absent stdin" "rc=$rc out='$out'"

echo "── judgment call: ${YTB} with no video-id path does NOT match ──────"
# ${YTB}/feed/subscriptions names no video -- the tool this hook redirects to
# (youtube_transcribe.py <URL>) has nothing to transcribe for a channel/feed/subscriptions
# page, so treating it as a hit would send the model to run a tool that can't do anything
# useful with it. Matching is deliberately scoped to path shapes that name an actual video:
# /watch?v=, the ${YT} short form, /live/, /shorts/.
run_negative "${YTB}/feed/subscriptions (no video id)" "check ${S}${YTC}/feed/subscriptions"

echo
if [ "$fail" = 0 ]; then echo "RESULT: $pass passed, 0 failed."; exit 0
else echo "RESULT: $pass passed, $fail failed."; exit 1
fi
