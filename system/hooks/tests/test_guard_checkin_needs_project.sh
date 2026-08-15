#!/bin/bash
# test_guard_checkin_needs_project.sh — proof that /checkin is gated on BOTH the path Claude takes
# (calling the Skill tool) and the path a human types (/checkin expanding directly), not just one.
#
# WHY THIS SUITE EXISTS, AND WHY IT CHANGED 2026-08-14. The original guard registered only
# PreToolUse(matcher="Skill") — which fires ONLY when the model itself decides to call the Skill tool.
# Per the official hooks reference (code.claude.com/docs/en/hooks, fetched live 2026-08-14): "typing
# /skillname directly bypasses PreToolUse. UserPromptExpansion fires on that direct path." Since
# /checkin's own trigger list leads with the literal "/checkin", the guard's most common real
# invocation NEVER reached it. This suite now proves BOTH legs:
#   (1) PreToolUse  — matcher="Skill", narrowed by the handler-level `if: "Skill(checkin)"` field
#                      (code.claude.com/docs/en/skills: "Skill(name) for exact match").
#   (2) UserPromptExpansion — matcher="checkin" (that event matches on the `command_name` field).
# Both legs share one script, branching on the input's `hook_event_name` field, and both deny the same
# way: exit 2 + stderr text (confirmed equivalent to a JSON "deny"/"block" for BOTH events per the live
# docs — see the DENY SHAPE note at the top of guard_checkin_needs_project.sh).
#
# `Skill` and `UserPromptExpansion` had never been matched/used by any hook in this repo before this
# guard. An unproven matcher is a silently dark guard, so this suite proves the matcher-adjacent PARTS
# it actually CAN prove from a pipe (the script's own logic, and the fire-log the script writes on every
# call) and is explicit in its final section about the part it CANNOT prove outside a real harness.
#
# Run: bash system/hooks/tests/test_guard_checkin_needs_project.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$HOOKS/../.." && pwd)"
G="$HOOKS/guard_checkin_needs_project.sh"
[ -f "$G" ] || { echo "CANNOT RUN: no hook at $G"; exit 1; }

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
check() { [ "$3" = "$2" ] && ok || bad "$1" "expected exit $2, got $3"; }

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/checkin-guard.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
mkdir -p "$SANDBOX/home"
export LIFEHACK_HOOK_FIRELOG="$SANDBOX/firelog.jsonl"

# ── input builders — one JSON shape per event, matching the fields the live docs document ──────────
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

arm() { # arm <session-id>   — arms a fresh project for that session, isolated by HOME
  CLAUDE_CODE_SESSION_ID="$1" HOME="$SANDBOX/home" \
    bash "$REPO/system/hooks/pm_flag.sh" arm "$SANDBOX/fake-brief-$1.md" "guard-test-slug-$1" "test-desk" >/dev/null 2>&1
}

run() { # run <label> <exp-rc> <session-id-or-""> <payload-json>
  local label="$1" exp="$2" sess="$3" payload="$4"
  if [ -n "$sess" ]; then
    printf '%s' "$payload" | CLAUDE_CODE_SESSION_ID="$sess" HOME="$SANDBOX/home" PM_TTL_HOURS=36 \
      bash "$G" >"$SANDBOX/out.txt" 2>"$SANDBOX/err.txt"
  else
    printf '%s' "$payload" | HOME="$SANDBOX/home" PM_TTL_HOURS=36 \
      bash "$G" >"$SANDBOX/out.txt" 2>"$SANDBOX/err.txt"
  fi
  check "$label" "$exp" "$?"
}

echo "── PreToolUse leg (matcher=Skill, if=Skill(checkin) in settings.json) ──"

echo "case 1: PreToolUse, checkin, no project armed -> REFUSE rc 2, message readable"
run "pretooluse unarmed" 2 "sess-preToolUse-unarmed" "$(pretooluse_payload checkin)"
grep -q "BLOCKED: /checkin with NO PROJECT ARMED" "$SANDBOX/err.txt" && ok || bad "message" "refusal text not found"
grep -q "PreToolUse (Skill: checkin" "$SANDBOX/err.txt" && ok || bad "message path label" "deny message did not name the PreToolUse leg"

echo "case 2: PreToolUse, checkin, project armed -> allow rc 0"
arm "sess-preToolUse-armed"
run "pretooluse armed" 0 "sess-preToolUse-armed" "$(pretooluse_payload checkin)"

echo
echo "── UserPromptExpansion leg (matcher=checkin in settings.json; matches command_name) ──"

echo "case 3: UserPromptExpansion, checkin, no project armed -> REFUSE rc 2, message readable"
run "upe unarmed" 2 "sess-upe-unarmed" "$(upe_payload checkin)"
grep -q "BLOCKED: /checkin with NO PROJECT ARMED" "$SANDBOX/err.txt" && ok || bad "message" "refusal text not found"
grep -q "UserPromptExpansion (typed /checkin)" "$SANDBOX/err.txt" && ok || bad "message path label" "deny message did not name the UserPromptExpansion leg"

echo "case 4: UserPromptExpansion, checkin, project armed -> allow rc 0"
arm "sess-upe-armed"
run "upe armed" 0 "sess-upe-armed" "$(upe_payload checkin)"

echo "case 5: UserPromptExpansion, a DIFFERENT command_name, no project armed -> allow rc 0"
# Belt-and-braces: settings.json's matcher="checkin" should be the only thing that ever routes a
# non-checkin command_name here, but the script re-checks command_name itself, so prove that
# independently too.
run "upe other command unarmed" 0 "sess-upe-other" "$(upe_payload save)"

echo
echo "── fail-closed on an unparseable/unknown event ──"

echo "case 6: garbage input, no project armed -> REFUSE rc 2 (fail closed, not fail open)"
run "garbage unarmed" 2 "sess-garbage-unarmed" "not json at all"
grep -q "unrecognized/unparsed" "$SANDBOX/err.txt" && ok || bad "message" "fail-closed branch did not identify itself"

echo "case 7: garbage input, project armed -> allow rc 0 (fail-closed only bites when UNARMED)"
arm "sess-garbage-armed"
run "garbage armed" 0 "sess-garbage-armed" "not json at all"

echo
echo "── fire-log: unconditional, appends, never overwrites ──"

echo "case 8: fire-log exists and accumulated one line per invocation above (7 so far)"
[ -s "$LIFEHACK_HOOK_FIRELOG" ] && ok || bad "firelog" "fire-log file was not written"
LINES="$(wc -l < "$LIFEHACK_HOOK_FIRELOG" | tr -d ' ')"
[ "$LINES" -ge 7 ] && ok || bad "firelog lines" "expected >=7 appended lines, got $LINES (fire-log must APPEND, not overwrite)"
grep -q "hook_event_name" "$LIFEHACK_HOOK_FIRELOG" && ok || bad "firelog content" "fire-log did not carry the raw hook input"
grep -q "PreToolUse" "$LIFEHACK_HOOK_FIRELOG" && ok || bad "firelog PreToolUse" "fire-log missing a PreToolUse-shaped entry"
grep -q "UserPromptExpansion" "$LIFEHACK_HOOK_FIRELOG" && ok || bad "firelog UserPromptExpansion" "fire-log missing a UserPromptExpansion-shaped entry"
# every appended line starts with an ISO-8601-ish UTC timestamp, tab, then the payload
FIRSTLINE="$(head -1 "$LIFEHACK_HOOK_FIRELOG")"
printf '%s' "$FIRSTLINE" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z	' && ok || bad "firelog timestamp" "first field is not a UTC timestamp: $FIRSTLINE"

echo
echo "── settings.json registration — both legs present, PreToolUse leg correctly narrowed ──"

echo "case 9: settings.json parses and both hook legs are wired the way this suite assumes"
python3 -c "
import json, sys
path = '$REPO/.claude/settings.json'
d = json.load(open(path))
hooks = d.get('hooks', {})

def find_entries(event, matcher_wanted):
    out = []
    for group in hooks.get(event, []):
        if group.get('matcher') != matcher_wanted:
            continue
        for h in group.get('hooks', []):
            if 'guard_checkin_needs_project.sh' in h.get('command', ''):
                out.append(h)
    return out

pre = find_entries('PreToolUse', 'Skill')
upe = find_entries('UserPromptExpansion', 'checkin')

ok = True
if len(pre) != 1:
    print('FAIL: expected exactly 1 PreToolUse/Skill entry for this guard, found', len(pre)); ok = False
elif pre[0].get('if') != 'Skill(checkin)':
    print('FAIL: PreToolUse/Skill entry missing if=Skill(checkin), got', pre[0].get('if')); ok = False

if len(upe) != 1:
    print('FAIL: expected exactly 1 UserPromptExpansion/checkin entry for this guard, found', len(upe)); ok = False

sys.exit(0 if ok else 1)
" && ok || bad "settings.json wiring" "PreToolUse if-narrowing or UserPromptExpansion registration missing/wrong"

echo
echo "RESULT: $pass passed, $fail failed."
[ "$fail" -eq 0 ] && echo "CHECKIN GUARD GREEN" || echo "CHECKIN GUARD RED"
exit $([ "$fail" -eq 0 ] && echo 0 || echo 1)
