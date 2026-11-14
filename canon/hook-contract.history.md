# History log for hook-contract.md

Text cut or moved out of the SOP, copied verbatim first. Append-only.

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-001, see drafts/hook-contract/applied.md

~~~~
## The LLM Context Block (mandatory on every hook)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-002, see drafts/hook-contract/applied.md

~~~~
Every hook must open with this block immediately after the shebang:
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-003, see drafts/hook-contract/applied.md

~~~~
# SIGNPOST: [the canonical rule doc/file this hook enforces — where the RULE lives + how to change it]
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-004, see drafts/hook-contract/applied.md

~~~~
**REDIRECT must be specific.** "See Lifehack architecture" is not a redirect.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-005, see drafts/hook-contract/applied.md

~~~~
**SIGNPOST — mandatory.** A hook's purpose is not just to BLOCK — it is to
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-006, see drafts/hook-contract/applied.md

~~~~
hook therefore carries a SIGNPOST: the deny message (and the LLM-context block) must name **where the
rule is codified** (the canonical doc / contract file) and **how to change it** (edit-there + get
sign-off), so the blocked session is pointed straight at the source of truth — not merely told "no."
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-007, see drafts/hook-contract/applied.md

~~~~
**Deny messages must include WHY + REDIRECT + SIGNPOST inline:**
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-008, see drafts/hook-contract/applied.md

~~~~
echo '{"decision":"block","reason":"BLOCKED: [what]. WHY: [why]. REDIRECT: [where]. RULE: [the canonical doc/file + how to change it]."}'
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-009, see drafts/hook-contract/applied.md

~~~~
Runs AFTER tool execution. Cannot block. Must always exit 0.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-010, see drafts/hook-contract/applied.md

~~~~
**Input:** `$ARGUMENTS` as first parameter ($1) — JSON string.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-011, see drafts/hook-contract/applied.md

~~~~
### PostToolUse — extract file path from $ARGUMENTS
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-012, see drafts/hook-contract/applied.md

~~~~
ARGS="$1"
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-013, see drafts/hook-contract/applied.md

~~~~
DENY='{"decision":"block","reason":"BLOCKED: [what]. WHY: [the incident or rule]. REDIRECT: [specific path or action]. RULE: [canonical doc/file + how to change it]."}'
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-014, see drafts/hook-contract/applied.md

~~~~
| 2 | **Block — deny text on stderr is shown to the model (house standard)** | n/a |
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-015, see drafts/hook-contract/applied.md

~~~~
PostToolUse hooks must always exit 0. Use stderr for warnings. **Fail-closed:** a guard that can't parse its input must DENY (`exit 2`), never `exit 0`.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-016, see drafts/hook-contract/applied.md

~~~~
## settings.json Registration
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-017, see drafts/hook-contract/applied.md

~~~~
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": "bash \"${CLAUDE_PROJECT_DIR}/system/hooks/{hook-name}.sh\"",
          "statusMessage": "Checking [what]..."
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "bash \"${CLAUDE_PROJECT_DIR}/system/hooks/{hook-name}.sh\" '$ARGUMENTS'",
          "statusMessage": "Validating [what]..."
        }]
      }
    ]
  }
}
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-018, see drafts/hook-contract/applied.md

~~~~
**The file is `.claude/settings.json`, in this repo, and `${CLAUDE_PROJECT_DIR}` expands to the repo
root.** That is what makes a registration portable: it travels with `git pull` and needs no editing on
any machine. An absolute path baked into this file works on exactly one computer.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-019, see drafts/hook-contract/applied.md

~~~~
  `chmod` first — friction with no guarantee behind it. The deny-list is the actual control.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-020, see drafts/hook-contract/applied.md

~~~~
  "The deny-list is the actual control" above still holds in the everyday case; it is no
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-021, see drafts/hook-contract/applied.md

~~~~
- [ ] SIGNPOST names the canonical rule doc/file + how to change it (re-teach, don't just wall)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-022, see drafts/hook-contract/applied.md

~~~~
- [ ] Registered in `.claude/settings.json`, using `${CLAUDE_PROJECT_DIR}`, in the SAME commit
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: hook-contract edit-pass hunk hunk-023, see drafts/hook-contract/applied.md

~~~~
  > `git pull` does not update it. The real checklist step is: confirm the new/changed registration was
  > separately installed into the other machine's own `~/.claude/settings.json` (e.g. via
  > `system/tools/install-guard-registrations.py`), not "confirm its symlink."  ⛔ not shipped to the public subset — private-clone only.
~~~~
