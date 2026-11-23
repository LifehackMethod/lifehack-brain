#!/bin/bash
# test_report_read_coverage.sh: card 7.1(b) — the counter when a helper stops (SubagentStop).
# ALLOW cases first: the hook NEVER blocks (exit 0 on every input, including garbage) and
# reports NOTHING when every document was read in full.
# Transcript fixtures are small records shaped like the real ones saved under
# state/code-plus-reading-harness/experiments/ (SubagentStop hands over agent_transcript_path);
# every real /Users/<name> path and email is scrubbed to placeholders.
# Run: bash system/hooks/tests/test_report_read_coverage.sh   (exit 0 = all pass)
HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
PLUGIN="$(cd "$HOOKS/../.." && pwd)"
HOOK="$HOOKS/report_read_coverage.sh"
SB="$(mktemp -d "${TMPDIR:-/tmp}/cov7b.XXXXXX")"; trap 'rm -rf "$SB"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

mkdir -p "$SB/docs" "$SB/home" "$SB/state"
DOC="$SB/docs/plan-note.md"
printf 'line one\nline two\nline three\nline four\nline five\n' > "$DOC"

# a transcript fixture: JSONL, one Read tool_use + its tool_result per line-shape below
mkrecord() { # mkrecord <out.jsonl> <file_path> <offset> <limit> [shell_cmd]
  local out="$1" fp="$2" off="$3" lim="$4" cmd="${5:-}" rid="t$RANDOM"
  {
    printf '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"%s","name":"Read","input":{"file_path":"%s","offset":%s,"limit":%s}}]}}\n' "$rid" "$fp" "$off" "$lim"
    printf '{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"%s","content":"lines"}]}}\n' "$rid"
    [ -n "$cmd" ] && printf '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"t%s","name":"Bash","input":{"command":"%s"}}]}}\n' "$RANDOM" "$cmd"
  } > "$out"
}

STOPP() { printf '{"session_id":"%s","agent_transcript_path":"%s"}' "$1" "$2"; }
# the switch line is absent from the worktree's roundB.conf, so every ON case passes the env
# override the switch reader honors (ROUNDB_READ_COVERAGE_REPORT=on); the OFF case passes =off.
runhook() { env -i PATH="$PATH" HOME="$SB/home" LIFEHACK_STATE_DIR="$SB/state" LIFEHACK_ROOT="$SB/brain" CLAUDE_PLUGIN_ROOT="$PLUGIN" ROUNDB_READ_COVERAGE_REPORT=on bash "$HOOK"; }
# brain root: the hook resolves the tile path through brain_root.py; point it at the sandbox
mkdir -p "$SB/brain/status"

echo "-- ALLOW: never blocks, any input"
printf '%s' '{"garbage":true}' | runhook >/dev/null 2>&1; [ $? = 0 ] && ok || bad "garbage payload" "nonzero exit"
printf '%s' 'not json' | runhook >/dev/null 2>&1; [ $? = 0 ] && ok || bad "non-JSON stdin" "nonzero exit"
printf '%s' '' | runhook >/dev/null 2>&1; [ $? = 0 ] && ok || bad "empty stdin" "nonzero exit"
printf '%s' '{"session_id":"s1","agent_transcript_path":"/nonexistent/x.jsonl"}' | runhook >/dev/null 2>&1; [ $? = 0 ] && ok || bad "missing transcript" "nonzero exit"

echo "-- full read of every document: nothing reported (exit 0, no tile, no log line)"
mkrecord "$SB/full.jsonl" "$DOC" 1 2000
BEFORE=$(cat "$SB/brain/status/reading-harness-coverage.json" 2>/dev/null | wc -c)
printf '%s' "$(STOPP sess-full "$SB/full.jsonl")" | runhook >/dev/null 2>&1; RC=$?
[ "$RC" = 0 ] && ok || bad "full read rc" "rc=$RC"
AFTER=$(cat "$SB/brain/status/reading-harness-coverage.json" 2>/dev/null | wc -c)
[ "$BEFORE" = "$AFTER" ] && ok || bad "full read tile" "tile written on a full read"
[ ! -s "$SB/state/reading-harness/coverage.log" ] && ok || bad "full read log" "log line written on a full read"

echo "-- partial read: exit 0 ALWAYS, tile through emit_status's envelope, dated log line"
mkrecord "$SB/partial.jsonl" "$DOC" 1 2
printf '%s' "$(STOPP sess-partial "$SB/partial.jsonl")" | runhook >/dev/null 2>&1; RC=$?
[ "$RC" = 0 ] && ok || bad "partial rc" "rc=$RC (SubagentStop never exits nonzero)"
python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
for k in ("desk","schema_version","pulse_job","emit_mode","stale_after_s","last_run","rc","status","summary"):
    assert k in d, k
assert d["desk"] == "reading-harness", d["desk"]
assert d["pulse_job"] == "read-coverage-counter", d["pulse_job"]
assert d["status"] in ("NEEDS_REVIEW", "ERROR"), d["status"]
assert d["rc"] == 1, d["rc"]
assert any("plan-note.md" in f for f in d["files_report"]), d["files_report"]
assert "tile is the delivery" in d["note"], d["note"]
' "$SB/brain/status/reading-harness-coverage.json" && ok || bad "tile envelope" "tile missing envelope fields or wrong shape"
grep -q "sess-partial" "$SB/state/reading-harness/coverage.log" && grep -q "plan-note.md" "$SB/state/reading-harness/coverage.log" && ok || bad "dated log line" "log lacks session/file"

echo "-- shell read (not counted): reported"
mkrecord "$SB/shell.jsonl" "$DOC" 1 2000 "cat $DOC"
rm -f "$SB/brain/status/reading-harness-coverage.json"
printf '%s' "$(STOPP sess-shell "$SB/shell.jsonl")" | runhook >/dev/null 2>&1
[ -f "$SB/brain/status/reading-harness-coverage.json" ] && ok || bad "shell read tile" "no tile on a shell read"

echo "-- broken transcript (no valid JSON lines, rc 4): reported, exit 0"
printf 'this is not json\nnor is this\n' > "$SB/broken.jsonl"
rm -f "$SB/brain/status/reading-harness-coverage.json"
printf '%s' "$(STOPP sess-broken "$SB/broken.jsonl")" | runhook >/dev/null 2>&1; RC=$?
[ "$RC" = 0 ] && ok || bad "broken rc" "rc=$RC"
python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
assert d["rc"] == 4 and d["status"] == "ERROR", (d["rc"], d["status"])
' "$SB/brain/status/reading-harness-coverage.json" && ok || bad "broken tile" "expected rc=4 ERROR"

echo "-- switch OFF: exactly the old behaviour (nothing at all)"
rm -f "$SB/brain/status/reading-harness-coverage.json"
printf '%s' "$(STOPP sess-off "$SB/partial.jsonl")" | env -i PATH="$PATH" HOME="$SB/home" LIFEHACK_STATE_DIR="$SB/state" LIFEHACK_ROOT="$SB/brain" CLAUDE_PLUGIN_ROOT="$PLUGIN" ROUNDB_READ_COVERAGE_REPORT=off bash "$HOOK" >/dev/null 2>&1; RC=$?
[ "$RC" = 0 ] && ok || bad "switch off rc" "rc=$RC"
[ ! -f "$SB/brain/status/reading-harness-coverage.json" ] && ok || bad "switch off tile" "tile written while off"

echo; echo "passed $pass, failed $fail"; [ "$fail" = 0 ]
