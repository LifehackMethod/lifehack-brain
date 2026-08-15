#!/bin/bash
# test_ported_batch_guards.sh — the three BLOCKING hooks that arrived with the SECURITY port.
#
# WHY THIS SUITE EXISTS. All three sat on disk, registered nowhere, for a whole session. An
# unregistered hook never fires and reads as a control that exists — citation_lint.py caught exactly
# that and refused the batch. These cases are the proof that each one is now registered AND fires
# BOTH WAYS: a deliberate violation is refused, and the benign neighbour still runs.
#
# ⭐ ONE REAL DEFECT WAS FOUND BY RUNNING THESE, not by reading the code. enforce_multiphase_contract
# excluded drafts with `"/_" in os.path.basename(path)` — a basename contains no slash, so that
# fourth exclusion could NEVER be true and `_draft.md` was blocked against the author's stated
# intent. Fixed here to `.startswith("_")`; the "underscore-prefixed draft" case below is its guard.
# ⚠ The same dead clause is STILL LIVE in the donor repo — deliberately not patched there (the donor
# is read-only to this migration and nobody has ruled on it).
#
# Deny = exit 2. Allow = exit 0.
# Run: bash system/hooks/tests/test_ported_batch_guards.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$HOOKS/../.." && pwd)"

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
check() { # check <label> <expected-rc> <actual-rc>
  [ "$3" = "$2" ] && ok || bad "$1" "expected exit $2, got $3"
}

# ── guard_agent_return_channel.sh — PreToolUse, matcher: Agent ────────────────
# A NAMED sub-agent is an addressable teammate whose final text is DISCARDED. Named + no delivery
# contract in the prompt = the work product is silently destroyed.
G="$HOOKS/guard_agent_return_channel.sh"
[ -f "$G" ] || { echo "CANNOT RUN: no hook at $G"; exit 1; }
echo "── guard_agent_return_channel: a named helper must declare how it hands work back ──"
agent_case() { # agent_case <label> <exp> <name> <prompt>
  python3 -c "
import json,sys
print(json.dumps({'tool_name':'Agent','tool_input':{'name':sys.argv[1],'prompt':sys.argv[2]}}))" \
    "$3" "$4" 2>/dev/null | bash "$G" >/dev/null 2>&1
  check "$1" "$2" "$?"
}
agent_case "named, no delivery contract"  2 "helper" "go read the files and report"
agent_case "unnamed — text returns itself" 0 ""       "go read the files and report"
agent_case "named + SendMessage contract"  0 "helper" "return your FULL text via SendMessage to main"
agent_case "named, contract cased oddly"   0 "helper" "reply using sendmessage when done"

# ── guard_git_add_class.sh — PreToolUse, matcher: Bash ────────────────────────
# This clone can be open in several concurrent windows, so a whole-tree add is never "my changes".
# ⚠ Trigger tokens are ASSEMBLED FROM FRAGMENTS below. Spelled literally, this file's own test
# command would trip the guard while writing it — the documented "a command-string guard blocks its
# own documentation" trap (hook-sop.md §4 Trap 2).
G="$HOOKS/guard_git_add_class.sh"
[ -f "$G" ] || { echo "CANNOT RUN: no hook at $G"; exit 1; }
A="git ad""d"; C="git comm""it"
echo "── guard_git_add_class: whole-tree staging refused, scoped staging allowed ──"
bash_case() { # bash_case <label> <exp> <command>
  python3 -c "
import json,sys
print(json.dumps({'tool_name':'Bash','tool_input':{'command':sys.argv[1]}}))" "$3" 2>/dev/null \
    | bash "$G" >/dev/null 2>&1
  check "$1" "$2" "$?"
}
bash_case "everything-add -A"          2 "$A -A"
bash_case "everything-add --all"       2 "$A --all"
bash_case "dot pathspec"               2 "$A ."
bash_case "update flag -u"             2 "$A -u"
bash_case "no pathspec at all"         2 "$A"
bash_case "commit -a"                  2 "$C -a -m \"msg\""
bash_case "explicit paths"             0 "$A system/tools/foo.py system/hooks/bar.sh"
bash_case "scoped directory add"       0 "$A system/tools/organism/"
bash_case "--dry-run stages nothing"   0 "$A -n -A"
bash_case "a mere MENTION in a message" 0 "$C -m \"stop using $A -A everywhere\""
bash_case "an unrelated command"       0 "ls -la system/hooks/"

# ── enforce_multiphase_contract.sh — PreToolUse, matcher: Write ───────────────
# A phase driver with no `## Output contract` is invisible to the per-skill phase_gate.py, so the
# skill drifts silently. Only a full-content Write is adjudicated; an Edit carries no content.
G="$HOOKS/enforce_multiphase_contract.sh"
[ -f "$G" ] || { echo "CANNOT RUN: no hook at $G"; exit 1; }
echo "── enforce_multiphase_contract: a phase driver is born gradeable ──"
DRIVER='# Phase 2 — scan

Do the scan.
'
DRIVER_OK='# Phase 2 — scan

## Output contract
- writes scan.md

phase 2 complete
'
HUD='Some prose with a [2/5] progress marker in it.
'
write_case() { # write_case <label> <exp> <path> <content> [tool]
  python3 -c "
import json,sys
print(json.dumps({'tool_name':sys.argv[3],'tool_input':{'file_path':sys.argv[1],'content':sys.argv[2]}}))" \
    "$3" "$4" "${5:-Write}" 2>/dev/null | bash "$G" >/dev/null 2>&1
  check "$1" "$2" "$?"
}
write_case "driver with no contract"      2 ".claude/skills/demo/prompts/02-scan.md" "$DRIVER"
write_case "HUD marker, no contract"      2 ".claude/skills/demo/prompts/03-x.md"    "$HUD"
write_case "driver WITH contract"         0 ".claude/skills/demo/prompts/02-scan.md" "$DRIVER_OK"
write_case "not a phase driver at all"    0 ".claude/skills/demo/prompts/notes.md"   "just prose"
write_case "outside prompts/"             0 ".claude/skills/demo/SKILL.md"           "$DRIVER"
write_case "templates/ excluded"          0 "system/templates/prompts/01-x.md"       "$DRIVER"
write_case "underscore-prefixed draft"    0 ".claude/skills/demo/prompts/_draft.md"  "$DRIVER"
# An Edit payload has no `content` key at all — the guard must pass it through, not deny on absence.
python3 -c "
import json
print(json.dumps({'tool_name':'Edit','tool_input':{'file_path':'.claude/skills/demo/prompts/02-scan.md'}}))" \
  2>/dev/null | bash "$G" >/dev/null 2>&1
check "an Edit carries no content" 0 "$?"

echo
if [ "$fail" -eq 0 ]; then
  echo "PASS — $pass cases, 0 failures."
  exit 0
fi
echo "FAIL — $fail of $((pass+fail)) cases failed."
exit 1
