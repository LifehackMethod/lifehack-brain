#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: Passing name= to the Agent tool silently converts a sub-agent into an addressable
#      TEAMMATE with a mailbox, and a teammate final response text is DISCARDED when it
#      finishes. Measured on the donor system this hook was ported from, across that
#      machine's transcripts (2026-08-01): 249 named spawns returned a payload 0 times;
#      1,714 unnamed spawns returned one every time. Two real incidents there: six council
#      advisors spawned named, five reports lost; five research agents spawned named,
#      90,280 characters stranded plus a false root-cause filed to disk. Every signal
#      reads success while the deliverable is destroyed — this is a structural fact about
#      how the harness returns named-agent output, not something specific to that machine.
# GUARDS: An Agent spawn that passes a non-empty name= while its prompt states no delivery
#      contract. That combination silently destroys the helper work product.
# REDIRECT: Drop the name: parameter — an unnamed sub-agent returns its full report as the
#      tool result automatically. If the agent genuinely must be addressable (agent-team
#      coordination), keep name: AND instruct it in the prompt to return its FULL text via
#      SendMessage to main.
# SIGNPOST: The rule is codified in system/sops/build-sop.md (the subagent return-channel
#      lesson). Change it there and get sign-off; do not edit this guard to work around a block.
# FAIL_POSTURE: closed — per hook-sop.md 3.2 and hook-contract.md, a BLOCK guard that cannot
#      parse its input DENIES. An unknown is never read as permission.
# UPDATED: 2026-08-20 (jq replaced by python3 — see the ⛔ note below; FAIL_POSTURE unchanged)
# ────────────────────────────────────────────────────────────────────────────────
#
# ⛔ THIS FILE USED TO PARSE ITS INPUT WITH `jq`, AND THAT WAS A LOADED GUN. Both lines that read
# the payload ended in `|| deny`, so on a machine WITHOUT jq — Windows Git Bash, this project's
# documented floor, ships none — the command substitution failed and the hook denied EVERY Agent
# spawn, named or not, with a misleading "no delivery contract" message. Reported as GitHub #74
# item 1 / #77 D2. Same class already fixed in guard_sheet_writes.sh / guard_sheet_formula_writes.sh
# on 2026-08-11: jq replaced by python3, which every other hook here already requires, so there is
# one interpreter dependency instead of two and the missing-tool situation cannot arise again. The
# FAIL_POSTURE stays closed — a payload that IS present but fails to parse as JSON still denies;
# only the "parser itself is absent" failure mode is removed.
# guard_agent_return_channel.sh — PreToolUse hook (matcher: Agent)

DENY='{"decision":"block","reason":"BLOCKED: this Agent spawn passes name= but its prompt states no delivery contract. WHY: a NAMED agent is an addressable teammate with a mailbox, and its final response text is DISCARDED when it finishes. Measured on the donor system this hook was ported from: 249 named spawns returned a payload 0 times; 1,714 unnamed spawns returned one every time. Note that run_in_background:false does NOT help — name overrides it. REDIRECT: remove the name: parameter and the full report comes back automatically as the tool result. If the agent must be addressable for agent-team coordination, keep name: and add an explicit instruction to its prompt to return its FULL text via SendMessage to main. RULE: system/sops/build-sop.md (subagent return channel) — change the rule there with sign-off, never by editing this guard."}'

deny() { printf '%s\n' "$DENY" >&2; exit 2; }

INPUT=$(cat 2>/dev/null) || deny
[ -z "$INPUT" ] && deny

NAME=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    print((json.load(sys.stdin).get("tool_input", {}) or {}).get("name", "") or "")
except Exception:
    sys.exit(1)
' 2>/dev/null) || deny
PROMPT=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    print((json.load(sys.stdin).get("tool_input", {}) or {}).get("prompt", "") or "")
except Exception:
    sys.exit(1)
' 2>/dev/null) || deny

# No name — a plain background sub-agent. Its final text returns to the caller. Pass through.
if [ -z "$NAME" ]; then
  exit 0
fi

# Named AND the prompt names the delivery channel — a deliberate teammate. Pass through.
if printf '%s' "$PROMPT" | grep -qiF 'sendmessage' 2>/dev/null; then
  exit 0
fi

# Named with no delivery contract — the work would be silently destroyed.
deny
