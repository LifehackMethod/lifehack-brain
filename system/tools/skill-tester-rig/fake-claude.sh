#!/bin/bash
# from orchestrator-v2/rig/stress/fake-claude.sh @ 2026-10-28
#   (kept: the stand-in-for-`claude -p` shape plugged in through CLAUDE_BIN, --version, the -p prompt scan, the
#    first-line [kind=.. step=..] header, FAKE_MODE / FAKE_MODE_STEP, and the empty|garbage|hang|exit127 behaviours;
#    rewritten for the canary (TR1.4): `good` replies with `expected.py next` (the previous step file + the token
#    from the rendered prompt, i.e. exactly what a real model is given, never the seed), wrapped in claude's
#    --output-format json shape; `almost` drops ONLY the token key; `lossy` drops ONLY the last fact; `garbage` is
#    a well-formed JSON envelope whose result is not a step (so it is a CHECK-FAIL, never a MODEL-FAIL);
#    new: the seed-leak assertion, the FAKE_WAIT handshake, FAKE_MODEL_ID, and a refusal of
#    --dangerously-skip-permissions. TR1.8: FAKE_DELAY, a clock, was removed; F-09 uses FAKE_WAIT_FILE now.)
#
# fake-claude.sh : no network, no tokens, no clock. CONTRACT.md §5.
# Env: FAKE_MODE        good|empty|almost|garbage|hang|exit127|lossy   (default good)
#      FAKE_MODE_STEP   misbehave only when the prompt's step=sN has N == this (default: every call)
#      FAKE_WAIT_FILE / FAKE_WAIT_STEP   a HANDSHAKE, not a clock (run_selftest s1/s2, bite sentinel controls,
#                     F-09): at that step, before reading the input, wait until FAKE_WAIT_FILE exists (wait.lib.sh);
#                     bounded by FAKE_WAIT_SECS (default 30), then stderr `WAIT-TIMEOUT fake actor s<N>: <file>`
#                     and exit 4 (the run fails loudly as MODEL-FAIL, never silently)
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
settings=""
while [ $# -gt 0 ]; do
  [ "$1" = "-p" ] && { prompt="$2"; shift; }
  [ "$1" = "--settings" ] && { settings="$2"; shift; }
  shift
done
head1="$(printf '%s\n' "$prompt" | head -1)"
step="$(printf '%s' "$head1" | sed -n 's/.*step=s\([0-9]*\).*/\1/p')"
input="$(printf '%s' "$head1" | sed -n 's/.*input=\([^] ]*\).*/\1/p')"
mode="${FAKE_MODE:-good}"
if [ -n "${FAKE_MODE_STEP:-}" ] && [ "${FAKE_MODE_STEP#s}" != "$step" ]; then mode=good; fi
RIG="$(cd "$(dirname "$0")" && pwd)"
# TR2.0b F-M5: a prompt carrying `PRIOR-TRANSCRIPT: <path>` makes the fake "attempt" that Read, as a nudged model
# would. Like Claude Code, it is refused only if the --settings deny list has a Read(...) rule matching the path
# (`//abs/**` and `~/...` forms; ~ = this process's HOME, the throwaway one). A refusal goes into the envelope's
# permission_denials; an allowed read changes nothing in the reply (so only the deny can catch it, by name).
DENIALS="[]"
tpath="$(printf '%s\n' "$prompt" | sed -n 's/^PRIOR-TRANSCRIPT: //p' | head -1)"
if [ -n "$tpath" ]; then
  DENIALS="$(python3 -I -c '
import fnmatch, json, os, sys
path, settings = sys.argv[1], sys.argv[2]
try:
    deny = json.load(open(settings))["permissions"]["deny"]
except (OSError, ValueError, KeyError, TypeError):
    deny = []
hit = False
for r in deny:
    if not (isinstance(r, str) and r.startswith("Read(") and r.endswith(")")):
        continue
    pat = r[5:-1]
    if pat.startswith("//"): pat = pat[1:]
    elif pat.startswith("~/"): pat = os.path.join(os.environ.get("HOME", "/nonexistent"), pat[2:])
    else: continue
    if fnmatch.fnmatchcase(path, pat.replace("**", "*")): hit = True; break
print(json.dumps([{"tool_name": "Read", "tool_use_id": "fake-1", "tool_input": {"file_path": path}}] if hit else []))
' "$tpath" "$settings")" || DENIALS="[]"
fi
out() {  # out <result-text> : claude's --output-format json envelope (+ permission_denials, TR2.0b)
  python3 -I -c 'import json,sys; print(json.dumps({"type":"result","subtype":"success","is_error":False,"result":sys.argv[1],"total_cost_usd":0,"num_turns":1,"model":sys.argv[2],"permission_denials":json.loads(sys.argv[3])}))' \
    "$1" "${FAKE_MODEL_ID:-fake-model}" "$DENIALS"
}
case "$mode" in
  empty) exit 0 ;;
  garbage) out '<<<not json at all {{{ result:'; exit 0 ;;
  hang) exec sleep 3600 ;;   # pacing: the hang stand-in; the watchdog under test must kill it
  exit127) exit 127 ;;
  good|almost|lossy) ;;
  *) echo "FAKE: unknown FAKE_MODE '$mode'" >&2; exit 2 ;;
esac
if [ -n "${FAKE_WAIT_FILE:-}" ] && [ "${FAKE_WAIT_STEP#s}" = "$step" ]; then
  . "$RIG/wait.lib.sh" || exit 4
  wait_until "${FAKE_WAIT_SECS:-30}" "fake actor s$step: $FAKE_WAIT_FILE" test -e "$FAKE_WAIT_FILE" || exit 4
fi
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
