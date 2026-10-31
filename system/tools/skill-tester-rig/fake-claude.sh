#!/bin/bash
# from orchestrator-v2/rig/stress/fake-claude.sh @ 2026-10-28
#   (kept: the stand-in-for-`claude -p` shape plugged in through CLAUDE_BIN, --version, the -p prompt scan, the
#    first-line [kind=.. step=..] header, FAKE_MODE / FAKE_MODE_STEP, and the empty|garbage|hang|exit127 behaviours;
#    rewritten for the canary (TR1.4): `good` replies with `expected.py next` (the previous step file + the token
#    from the rendered prompt, i.e. exactly what a real model is given, never the seed), wrapped in claude's
#    --output-format json shape; `almost` drops ONLY the token key; `lossy` drops ONLY the last fact; `garbage` is
#    a well-formed JSON envelope whose result is not a step (so it is a CHECK-FAIL, never a MODEL-FAIL);
#    new: the seed-leak assertion, FAKE_DELAY, FAKE_MODEL_ID, and a refusal of --dangerously-skip-permissions.)
#
# fake-claude.sh : no network, no tokens, no clock. CONTRACT.md §5.
# Env: FAKE_MODE        good|empty|almost|garbage|hang|exit127|lossy   (default good)
#      FAKE_MODE_STEP   misbehave only when the prompt's step=sN has N == this (default: every call)
#      FAKE_DELAY / FAKE_DELAY_STEP   sleep FAKE_DELAY s BEFORE reading the input, at that step only (F-09)
#      FAKE_MODEL_ID    the reply's "model" field (default fake-model; the version-change injector sets it)
#      FAKE_VERSION     what --version reports (default 2.1.0)
# Exit 3 + stderr "FAKE: SEED-LEAK ..." if CANARY_SEED or SKILL_TESTER_SEED is in the environment: the actor
# must never inherit the answer key (CONTRACT §0). run.sh launches the actor through `env -u ... -u ...`.
if [ -n "${CANARY_SEED+x}" ] || [ -n "${SKILL_TESTER_SEED+x}" ]; then
  echo "FAKE: SEED-LEAK — CANARY_SEED/SKILL_TESTER_SEED is set in the actor's environment" >&2
  exit 3
fi
if [ "$1" = "--version" ]; then echo "${FAKE_VERSION:-2.1.0} (Claude Code)"; exit 0; fi
prompt=""
for a in "$@"; do
  [ "$a" = "--dangerously-skip-permissions" ] && { echo "FAKE: refused --dangerously-skip-permissions (ruling 8)" >&2; exit 2; }
done
while [ $# -gt 0 ]; do [ "$1" = "-p" ] && { prompt="$2"; shift; }; shift; done
head1="$(printf '%s\n' "$prompt" | head -1)"
step="$(printf '%s' "$head1" | sed -n 's/.*step=s\([0-9]*\).*/\1/p')"
input="$(printf '%s' "$head1" | sed -n 's/.*input=\([^] ]*\).*/\1/p')"
mode="${FAKE_MODE:-good}"
if [ -n "${FAKE_MODE_STEP:-}" ] && [ "${FAKE_MODE_STEP#s}" != "$step" ]; then mode=good; fi
RIG="$(cd "$(dirname "$0")" && pwd)"
out() {  # out <result-text> : claude's --output-format json envelope
  python3 -I -c 'import json,sys; print(json.dumps({"type":"result","subtype":"success","is_error":False,"result":sys.argv[1],"total_cost_usd":0,"num_turns":1,"model":sys.argv[2]}))' \
    "$1" "${FAKE_MODEL_ID:-fake-model}"
}
case "$mode" in
  empty) exit 0 ;;
  garbage) out '<<<not json at all {{{ result:'; exit 0 ;;
  hang) exec sleep 3600 ;;
  exit127) exit 127 ;;
  good|almost|lossy) ;;
  *) echo "FAKE: unknown FAKE_MODE '$mode'" >&2; exit 2 ;;
esac
if [ -n "${FAKE_DELAY:-}" ] && [ "${FAKE_DELAY_STEP#s}" = "$step" ]; then sleep "$FAKE_DELAY"; fi
tok="$(printf '%s' "$prompt" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p' | head -1)"
if [ -z "$step" ] || [ -z "$input" ] || [ -z "$tok" ]; then out "ERROR fake cannot parse the prompt"; exit 0; fi
reply="$(python3 -I "$RIG/canary/expected.py" next --step "$step" --prev "$input" --token "$tok" 2>/dev/null)"
if [ -z "$reply" ]; then out "ERROR cannot read $input"; exit 0; fi
case "$mode" in
  almost) reply="$(printf '%s' "$reply" | python3 -I -c 'import json,sys; r=json.load(sys.stdin); r.pop("token"); print(json.dumps(r,separators=(",",":")))')" ;;
  lossy)  reply="$(printf '%s' "$reply" | python3 -I -c 'import json,sys; r=json.load(sys.stdin); r["facts"]=r["facts"][:-1]; print(json.dumps(r,separators=(",",":")))')" ;;
esac
out "$reply"
exit 0
