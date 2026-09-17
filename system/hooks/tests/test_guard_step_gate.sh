#!/bin/bash
# test_guard_step_gate.sh — proof of guard_step_gate.sh's own mechanism: generic, register-driven,
# both PreToolUse and UserPromptExpansion legs, fail-closed on garbage, benign controls untouched.
#
# WHAT THIS SUITE DOES NOT DO, ON PURPOSE. guard_step_gate.sh is deliberately UNREGISTERED in K6 v1
# (see that script's own "v1 SCOPE" note) — no row in the real system/register/register.jsonl wires
# it to checkin, save, or any other real skill, precisely so an advisory-only seam (checkin->save,
# R9/R34) can never be silently turned into a hard block by this mechanism. So this suite NEVER reads
# the repo's real register.jsonl and NEVER uses "checkin"/"save" as a skill name anywhere below — it
# builds its own throwaway register.jsonl with SYNTHETIC skill rows and points the script at it via
# LHB_STEP_GATE_REGISTER. That fixture carries THREE rows (a gated skill, an ungated skill, and a
# skill with a DIFFERENT declared need), not one row compared with itself — the discriminating case
# this suite exists to prove is "the gate reads the INVOKED skill's own needs, not just any row's."
#
# Run: bash system/hooks/tests/test_guard_step_gate.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
G="$HOOKS/guard_step_gate.sh"
[ -f "$G" ] || { echo "CANNOT RUN: no hook at $G"; exit 1; }

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
check() { [ "$3" = "$2" ] && ok || bad "$1" "expected exit $2, got $3"; }

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/step-gate.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
mkdir -p "$SANDBOX/home"
export LHB_STEP_GATE_FIRELOG="$SANDBOX/firelog.jsonl"

# ── synthetic, multi-row register fixture — never a one-row vacuous compare ─────────────────────
REGISTER="$SANDBOX/register.jsonl"
python3 -c "
import json
rows = [
  {'type': 'skill', 'name': 'gated-widget-skill',   'needs': ['widget_prepped'], 'returns': []},
  {'type': 'skill', 'name': 'ungated-freebie-skill','needs': [],                 'returns': []},
  {'type': 'skill', 'name': 'other-gated-skill',     'needs': ['other_thing'],    'returns': []},
]
with open('$REGISTER', 'w', encoding='utf-8') as f:
    for r in rows:
        f.write(json.dumps(r) + '\n')
"
export LHB_STEP_GATE_REGISTER="$REGISTER"

# ── input builders — same shapes guard_checkin_needs_project.sh's own suite uses ────────────────
pretooluse_payload() { # pretooluse_payload <skill-name>
  python3 -c "
import json,sys
print(json.dumps({
  'hook_event_name': 'PreToolUse',
  'tool_name': 'Skill',
  'tool_input': {'skill': sys.argv[1]},
}))" "$1"
}
upe_payload() { # upe_payload <command_name>
  python3 -c "
import json,sys
print(json.dumps({
  'hook_event_name': 'UserPromptExpansion',
  'expansion_type': 'slash_command',
  'command_name': sys.argv[1],
  'command_args': '',
  'command_source': 'user',
  'prompt': '/' + sys.argv[1],
}))" "$1"
}

write_receipt() { # write_receipt <need-name> <session-id>  — mirrors what a future producer would
                   # write; the session id MUST match the one `run` will later check with, since
                   # flag.sh keys the flag file by CLAUDE_CODE_SESSION_ID (flag.sh:flag_init).
  CLAUDE_CODE_SESSION_ID="$2" HOME="$SANDBOX/home" bash -c '
    . "'"$HOOKS"'/lib/flag.sh"
    flag_init step-receipts "'"$1"'"
    flag_write "producer=test" "armed_at=$NOW"
  '
}

run() { # run <label> <exp-rc> <sess> <payload-json>
  local label="$1" exp="$2" sess="$3" payload="$4"
  printf '%s' "$payload" | CLAUDE_CODE_SESSION_ID="$sess" HOME="$SANDBOX/home" \
    LHB_STEP_GATE_REGISTER="$REGISTER" LHB_STEP_GATE_FIRELOG="$LHB_STEP_GATE_FIRELOG" \
    bash "$G" >"$SANDBOX/out.txt" 2>"$SANDBOX/err.txt"
  check "$label" "$exp" "$?"
}

echo "── PreToolUse leg ──"

echo "case 1: PreToolUse, a gated skill, no receipt -> DENY rc 2, names the missing need"
run "pretooluse gated no-receipt" 2 "sess-1" "$(pretooluse_payload gated-widget-skill)"
grep -q "BLOCKED: /gated-widget-skill" "$SANDBOX/err.txt" && ok || bad "message" "deny text not found"
grep -q "widget_prepped" "$SANDBOX/err.txt" && ok || bad "message need" "deny did not name the missing need"

echo "case 2: PreToolUse, the SAME gated skill, receipt now written -> allow rc 0"
write_receipt widget_prepped sess-1
run "pretooluse gated with-receipt" 0 "sess-1" "$(pretooluse_payload gated-widget-skill)"

echo "case 3: PreToolUse, the UNGATED skill (needs=[]), no receipt anywhere -> allow rc 0"
run "pretooluse ungated" 0 "sess-1" "$(pretooluse_payload ungated-freebie-skill)"

echo "case 4: PreToolUse, a DIFFERENT gated skill with a DIFFERENT need, only widget_prepped satisfied -> DENY (proves it reads THIS skill's own needs, not just any satisfied receipt)"
run "pretooluse other-gated cross-check" 2 "sess-1" "$(pretooluse_payload other-gated-skill)"
grep -q "other_thing" "$SANDBOX/err.txt" && ok || bad "message need" "deny did not name other-gated-skill's own need (other_thing) — may be reading the wrong row"

echo "case 5: PreToolUse, a skill with NO register row at all -> allow rc 0 (nothing declared, nothing to gate)"
run "pretooluse unknown skill" 0 "sess-1" "$(pretooluse_payload totally-unregistered-skill)"

echo
echo "── UserPromptExpansion leg ──"

echo "case 6: UserPromptExpansion, a gated skill, no receipt -> DENY rc 2"
run "upe gated no-receipt" 2 "sess-2" "$(upe_payload gated-widget-skill)"
grep -q "widget_prepped" "$SANDBOX/err.txt" && ok || bad "message" "deny text missing the need name"

echo "case 7: UserPromptExpansion, same gated skill, receipt present -> allow rc 0"
write_receipt widget_prepped sess-2
run "upe gated with-receipt" 0 "sess-2" "$(upe_payload gated-widget-skill)"

echo "case 8: UserPromptExpansion, ungated skill -> allow rc 0"
run "upe ungated" 0 "sess-2" "$(upe_payload ungated-freebie-skill)"

echo
echo "── expiry: an EXPIRED receipt is treated as absent ──"

echo "case 9: gated skill, receipt exists but TTL=0 forces expiry -> DENY rc 2"
printf '%s' "$(pretooluse_payload gated-widget-skill)" | CLAUDE_CODE_SESSION_ID="sess-1" HOME="$SANDBOX/home" \
  LHB_STEP_GATE_REGISTER="$REGISTER" LHB_STEP_GATE_TTL_HOURS=0 bash "$G" >"$SANDBOX/out.txt" 2>"$SANDBOX/err.txt"
check "expired receipt denies" 2 "$?"

echo
echo "── fail-closed on garbage / unparseable input ──"

echo "case 10: garbage input, not JSON at all -> REFUSE rc 2 (fail closed, not open)"
run "garbage input" 2 "sess-3" "not json at all"
grep -qi "fail" "$SANDBOX/err.txt" && ok || bad "message" "fail-closed branch did not identify itself"

echo "case 11: a real, unrelated hook_event_name (e.g. PostToolUse) this gate doesn't evaluate -> allow rc 0 (there is nothing for THIS gate to check on that event, not a failure)"
run "unrelated event" 0 "sess-4" '{"hook_event_name": "PostToolUse"}'

echo
echo "── benign control: an unrelated skill invoked many times never trips the gate ──"

echo "case 12: 20 calls for the ungated skill, alternating legs -> 0 false denies"
DENIES=0
for i in $(seq 1 20); do
  if [ $((i % 2)) -eq 0 ]; then P="$(pretooluse_payload ungated-freebie-skill)"; else P="$(upe_payload ungated-freebie-skill)"; fi
  printf '%s' "$P" | CLAUDE_CODE_SESSION_ID="sess-benign-$i" HOME="$SANDBOX/home" \
    LHB_STEP_GATE_REGISTER="$REGISTER" bash "$G" >/dev/null 2>/dev/null
  [ "$?" -ne 0 ] && DENIES=$((DENIES+1))
done
[ "$DENIES" -eq 0 ] && ok || bad "benign sweep" "$DENIES false denies out of 20 benign calls"

echo
echo "── fire-log: unconditional, appends ──"

echo "case 13: fire-log accumulated at least one line per invocation above"
[ -s "$LHB_STEP_GATE_FIRELOG" ] && ok || bad "firelog" "fire-log file was not written"
LINES="$(wc -l < "$LHB_STEP_GATE_FIRELOG" | tr -d ' ')"
[ "$LINES" -ge 13 ] && ok || bad "firelog lines" "expected >=13 appended lines, got $LINES"

echo
echo "RESULT: $pass passed, $fail failed."
[ "$fail" -eq 0 ] && echo "STEP GATE GREEN" || echo "STEP GATE RED"
exit $([ "$fail" -eq 0 ] && echo 0 || echo 1)
