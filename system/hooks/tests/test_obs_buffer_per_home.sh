#!/bin/bash
# test_obs_buffer_per_home.sh — 3b.7 D: the observability buffer is per-HOME (with env override) and a
# throwaway HOME can neither read nor delete the old shared /tmp buffer or another HOME's buffer.
# Fully sandboxed: every HOME here is a mktemp dir; the real buffers are never touched.
HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
SB="$(mktemp -d "${TMPDIR:-/tmp}/lifehack-obsbuf.XXXXXX")" || exit 1
trap 'rm -rf "$SB"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
unset LIFEHACK_OBS_BUFFER
LOGIN='{"tool_name":"Read","session_id":"s","cwd":"/tmp","tool_input":{"file_path":"/tmp/x"}}'
STOP() { printf '{"session_id":"s","transcript_path":"%s/none","cwd":"/tmp"}' "$SB"; }

# 1. default path derives from $HOME
H1="$SB/home1"; mkdir -p "$H1"
printf '%s' "$LOGIN" | env HOME="$H1" LIFEHACK_ROOT="$SB/root1" bash "$HOOKS/observability_logger.sh" >/dev/null 2>&1
[ -s "$H1/.claude/run/lifehack-observability-buffer.jsonl" ] && ok || bad "default per-HOME path" "no line in \$HOME/.claude/run"

# 2. a second HOME writes to ITS OWN buffer, not the first
H2="$SB/home2"; mkdir -p "$H2"
printf '%s' "$LOGIN" | env HOME="$H2" bash "$HOOKS/observability_logger.sh" >/dev/null 2>&1
a=$(wc -l < "$H1/.claude/run/lifehack-observability-buffer.jsonl" | tr -d ' ')
b=$(wc -l < "$H2/.claude/run/lifehack-observability-buffer.jsonl" | tr -d ' ')
[ "$a" = 1 ] && [ "$b" = 1 ] && ok || bad "buffers isolated per HOME" "home1=$a home2=$b"

# 3. env override wins over HOME
OV="$SB/override/buf.jsonl"; mkdir -p "$SB/override"
printf '%s' "$LOGIN" | env HOME="$H1" LIFEHACK_OBS_BUFFER="$OV" bash "$HOOKS/observability_logger.sh" >/dev/null 2>&1
[ -s "$OV" ] && ok || bad "env override" "override file empty"
a2=$(wc -l < "$H1/.claude/run/lifehack-observability-buffer.jsonl" | tr -d ' ')
[ "$a2" = 1 ] && ok || bad "override does not also write the HOME buffer" "home1 now $a2 lines"

# 4. legacy shared /tmp buffer: a throwaway HOME must NOT read (flush) or delete it. The recorder is run
#    against a stand-in file at the legacy NAME inside a fake TMP-like dir is impossible (path is fixed),
#    so we assert on the code: the recorder and logger no longer reference the old path at all...
if grep -nE '^[[:space:]]*[A-Z_]*BUFFER=.*"/tmp/lifehack-observability-buffer' "$HOOKS/observability_logger.sh" "$HOOKS/session_flight_recorder.sh" >/dev/null; then
  bad "no hard-coded /tmp buffer assignment" "still assigned"; else ok; fi
#    ...and behaviourally: plant a canary at the real legacy path ONLY if absent (never clobber a real one), run
#    the recorder under a throwaway HOME with a notes root, and check the canary survived and was not flushed.
LEG=/tmp/lifehack-observability-buffer.jsonl
if [ -e "$LEG" ]; then
  before=$(cksum < "$LEG"); made=0
else
  echo '{"canary":"3b7D"}' > "$LEG"; before=$(cksum < "$LEG"); made=1
fi
H3="$SB/home3"; mkdir -p "$H3" "$SB/root3"
STOP | env HOME="$H3" LIFEHACK_ROOT="$SB/root3" bash "$HOOKS/session_flight_recorder.sh" >/dev/null 2>&1
[ -e "$LEG" ] && [ "$(cksum < "$LEG")" = "$before" ] && ok || bad "legacy /tmp buffer untouched by recorder (throwaway HOME)" "deleted or changed"
OBSF=$(ls "$SB/root3/system/observability" 2>/dev/null)
if [ "$made" = 1 ]; then
  [ -z "$OBSF" ] || ! grep -rq canary "$SB/root3/system/observability" 2>/dev/null && ok || bad "legacy buffer content not flushed into the throwaway root" "canary leaked"
fi
printf '%s' "$LOGIN" | env HOME="$H3" LIFEHACK_ROOT="$SB/root3" bash "$HOOKS/observability_logger.sh" >/dev/null 2>&1
[ "$(cksum < "$LEG")" = "$before" ] && ok || bad "legacy /tmp buffer untouched by logger" "changed"
[ "$made" = 1 ] && /bin/mv "$LEG" "$SB/canary.gone"   # cleanup of our own canary only

# 5. recorder under HOME2 flushes only HOME2's buffer and deletes only it; HOME1's survives
mkdir -p "$SB/root2"
STOP | env HOME="$H2" LIFEHACK_ROOT="$SB/root2" bash "$HOOKS/session_flight_recorder.sh" >/dev/null 2>&1
[ ! -e "$H2/.claude/run/lifehack-observability-buffer.jsonl" ] && ok || bad "own buffer flushed + removed" "still there"
[ -s "$H1/.claude/run/lifehack-observability-buffer.jsonl" ] && ok || bad "other HOME's buffer survives" "gone"
ls "$SB/root2/system/observability"/*.jsonl >/dev/null 2>&1 && ok || bad "flush landed in notes root" "none"

echo "RESULT: $pass passed, $fail failed."; [ "$fail" = 0 ]
