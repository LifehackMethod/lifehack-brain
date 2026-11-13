# Hook Contract

Canonical reference for hook creation. Read this before writing any hook. The DECISION layer —
whether a hook is the right tool at all, and which of the three kinds — is `system/sops/hook-sop.md`;
this page is the mechanics.

---

## The LLM Context Block (on every hook)

Every hook opens with this block immediately after the shebang:

```bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: [the incident or failure that created this hook — specific, not generic]
# GUARDS: [what behavior it blocks and why that behavior was wrong]
# REDIRECT: [exactly where Claude should go instead — path, calendarId, desk name]
# SIGNPOST: [the canonical rule doc/file behind this hook — where the RULE lives + what to do instead to comply; a change to this rule goes to the person]
# UPDATED: [YYYY-MM-DD]
# ─────────────────────────────────────────────────────────────────────────────
```

**REDIRECT is specific.** "See Lifehack architecture" is not a redirect.
Give Claude the exact path, ID, or command it needs to recover.

**SIGNPOST — on every hook.** A hook's purpose is not just to BLOCK — it is to
**RE-TEACH the boundary so a fresh session LEARNS the rule instead of hitting a silent wall.** Every
hook therefore carries a SIGNPOST: the deny message (and the LLM-context block) names **where the
rule is codified** (the canonical doc / contract file) and **what to do instead to comply** (a change
to this rule goes to the person), so the blocked session is pointed straight at the source of truth — not merely told "no."
A block without a signpost is a wall; a block with a signpost is a teacher.

**Deny messages include WHY + REDIRECT + SIGNPOST inline:**
```bash
echo '{"decision":"block","reason":"BLOCKED: [what]. WHY: [why]. REDIRECT: [where]. RULE: [the canonical doc/file + what to do instead to comply; a change to this rule goes to the person]."}'
```

---

## Hook Types

### PreToolUse
Runs BEFORE tool execution. Can block (deny) or allow (exit 0).
Registered under `"PreToolUse"` in settings.json (generated from `system/register/register.jsonl`).

**Input:** stdin — JSON with `tool_input` containing the tool's parameters.
**Output to block (house standard, proven live):** deny text → **stderr + `exit 2`** (the honored block signal — what the live guard fleet uses). The `{"decision":"block",...}` JSON → **stdout** form is also honored. NEVER put the JSON on stderr with `exit 1` — neither channel is read, so the guard goes silently DARK.
**Output to allow:** exit 0 (no stdout needed)

Common matchers: `Bash`, `Write|Edit`, `Write`, `Edit`

### PostToolUse
Runs AFTER tool execution. Cannot block. Always exits 0.
Registered under `"PostToolUse"` in settings.json (generated from `system/register/register.jsonl`).

**Input:** stdin — JSON string (not `$ARGUMENTS`, not `$1`).
**Output:** advisory only — write to stderr, never exit non-zero to block.

---

## Input Parsing Patterns

### PreToolUse — extract command (Bash matcher)
```bash
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('command', ''))
except:
    print('')
")
```

### PreToolUse — extract file path (Write|Edit matcher)
```bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    path = data.get('tool_input', {}).get('file_path', '')
    if not path:
        path = data.get('tool_input', {}).get('path', '')
    print(path)
except:
    print('')
")
```

### PostToolUse — extract file path from stdin
```bash
ARGS="$(cat)"
FILE_PATH=$(echo "$ARGS" | grep -o '"file_path":"[^"]*"' | cut -d'"' -f4 | head -1)
```

---

## Canonical Deny Format

House standard across the live fleet — deny text to **stderr**, then **`exit 2`** (the honored PreToolUse block signal). Verified live (council audit 2026-06-16/17):

```bash
DENY='{"decision":"block","reason":"BLOCKED: [what]. WHY: [the incident or rule]. REDIRECT: [specific path or action]. RULE: [canonical doc/file + what to do instead to comply; a change to this rule goes to the person]."}'
deny() { printf '%s\n' "$DENY" >&2; exit 2; }
```

Both work: `exit 2` + stderr (house standard) AND the `{"decision":"block"}` JSON on **stdout**. The ONE dark trap: JSON on **stderr with `exit 1`** → neither channel is read → the guard is silently DARK. Do NOT use the `hookSpecificOutput` / `permissionDecision` format.

---

## Exit Code Semantics

| Exit | PreToolUse | PostToolUse |
|------|-----------|-------------|
| 0 | Allow — tool runs | Complete — no action |
| 2 | **Block — exit 2 is the block signal; deny text on stderr is shown to the model (house standard)** | n/a |
| 1 | Block via `{"decision":"block"}` JSON on **stdout** only (also works) | Invalid — do not use |

PostToolUse hooks always exit 0. Use stderr for warnings. **Fail-closed:** a guard that can't parse its input DENIES (`exit 2`), never `exit 0`.

---

## Registration: a register row, fed through generate.py

A hook is registered as one row in `system/register/register.jsonl`, the source. `system/register/generate.py`
reads the register and writes `hooks/hooks.json` and `.claude/settings.json` from it; neither file is
edited by hand. A real row, as it stands in the register:

```json
{"args": "", "cost_bytes": null, "cost_ms": null, "event": "PreToolUse", "exists": true, "expiry": null, "group": null, "id": "hook:public:/system/hooks/guard_canon_write.sh@PreToolUse:Bash|Write|Edit", "if": null, "launch_mode": "both", "matcher": "Bash|Write|Edit", "needs": [], "path": "/system/hooks/guard_canon_write.sh", "protects_permissions": [], "repo": "public", "returns": [], "sha": "5ae2d114", "state": "active", "status": "Checking what is going into the always-loaded layer...", "status_conflicts": [], "surfaces": ["plugin", "settings"], "type": "hook"}
```

**The generated command in `.claude/settings.json` starts from `${CLAUDE_PROJECT_DIR}`, which expands to
the repo root** (the plugin's `hooks/hooks.json` uses `${CLAUDE_PLUGIN_ROOT}`). That is what makes a
registration portable: it travels with `git pull` and needs no editing on any machine. An absolute
path baked into either file works on exactly one computer.

⚠ **`.claude/settings.json` is in this repo's own deny-list** (`Edit(.claude/settings.json)`), so a
session cannot quietly re-wire its own guards. Editing it is a deliberate act by a person.

---

## Permission Model

- Hook scripts live at `system/hooks/` in this repo and are ordinary tracked files, mode `755`.
- `system/hooks/**` is in the deny-list for the Edit tool, so a session cannot rewrite a guard as a
  side effect of doing something else. Editing one is a deliberate act.
- ⚠ **Do not `chmod 444` them.** The system this came from did, because its hooks were symlinked out
  of a clone into a home directory and read-only was the only protection available. Here git tracks
  the executable bit and nothing else, so a `444` file is just a file you cannot edit without a
  `chmod` first — friction with no guarantee behind it. The deny-list is one layer of friction.
  ⛔ **CORRECTED 2026-09-16 (R2 Part B):** this `Edit(system/hooks/**)` deny entry is now
  REGISTER-GOVERNED, not a fixed constant — `system/register/register.jsonl`'s
  `guard_hook_sop_read.sh` row carries it in `protects_permissions`, and
  `generate.py`'s `install_into_repo()` REMOVES it from `.claude/settings.json` for the
  duration of a declared, expiring `state=suspended` suspension on that row (and APPENDS
  it back the moment the suspension expires or is lifted — the self-heal is the expiry).
  "The deny-list is one layer of friction" above still holds in the everyday case; it is no
  longer a claim that this specific line can never move.

---

## Testing a Hook Locally

```bash
# PreToolUse, Bash matcher
echo '{"tool_input":{"command":"ls -la"}}' | bash system/hooks/enforce_egress_allowlist.sh; echo "rc=$?"

# PreToolUse, Write|Edit matcher
echo '{"tool_input":{"file_path":"/tmp/test.md"}}' | bash system/hooks/guard_canon_write.sh; echo "rc=$?"
```

⚠ **A pipe test proves the script did not crash. It does not prove the hook is a control** — for that
you have to watch it fire through the real harness and READ the message it prints. See
`system/sops/hook-sop.md` §4, and the suites in `system/hooks/tests/`, which are the worked examples
worth copying: every one of them tests the ALLOW cases first, because a guard that blocks ordinary
work gets unregistered and then guards nothing.

⚠ **A guard that matches on the command STRING will block the commands that document it.** Writing a
test whose payload contains the tokens the guard looks for trips the guard on the way in. Assemble
those tokens from fragments, or put the work in a file and run the file.

---

## Deploy & Verify — after every hook change

Both halves are files in this repo, so both travel by `git pull` and neither is re-done by hand:

1. **The script** — `system/hooks/{name}.sh`. Commit it.
2. **The registration** — a row in `system/register/register.jsonl`, the source; `system/register/generate.py` writes `hooks/hooks.json` and `.claude/settings.json` from it. Same change. A script with no
   registration is a file nobody runs; a registration with no script is a hook that fails on every
   turn. `system/tools/citation_lint.py` checks both directions on every commit and refuses one
   without the other, so this is not a rule anyone has to remember.
3. **⛔ RESTART.** The harness reads `settings.json` at session start. A newly registered hook does
   nothing at all in the window that registered it, and the only symptom is silence. This is the
   single most common reason a correct hook appears not to work.
4. **Watch it fire.** Attempt the guarded action for real and read what it prints. Not the exit code
   — the message, which is the half a human acts on.

⚠ **A hook not registered on the machine you are sitting at is silently dark there.** Nothing reports
it. `citation_lint.py` catches the file-vs-registration mismatch; it cannot tell you the session was
never restarted.

---

## Worked examples in this repo

Read the LLM CONTEXT block at the top of any of these. It is the fastest way to see what a good one
looks like, and each states WHY it exists in terms of something that actually went wrong.

| Hook | Type | Matcher | What it guards |
|------|------|---------|---------------|
| `system/hooks/ingest_gate_enforce.sh` | PreToolUse | Bash\|WebFetch\|WebSearch\|Read | forces every external read through the sanitizers — the widest one here |
| `system/hooks/enforce_egress_allowlist.sh` | PreToolUse | Bash | where an outbound call is allowed to go |
| `system/hooks/guard_canon_write.sh` | PreToolUse | Write\|Edit | what is allowed into the always-loaded layer |
| `system/hooks/guard_throughline_write_scope.sh` | PreToolUse | Write\|Edit | a session-scoped guard that is a pure no-op unless armed |
| `system/hooks/pm_persist.sh` | UserPromptSubmit | — | the INJECT shape: prints, never blocks |
| `system/hooks/session_context_loader.sh` | SessionStart | — | loading standing context once, with a real failure path |

The `system/hooks/tests/` suites beside them are the other half of the example: what a hook test has
to cover before the hook counts as a control.

---

## Hook Creation Checklist

- [ ] Read this document before writing
- [ ] ⛔ There is no `system/templates/hook-template.sh` here — copy the closest SHIPPED hook instead.
      A real one carries a real WHY, which is the field a blank template cannot fill and the one
      that decides whether the hook should exist at all.
- [ ] Fill in all 5 LLM context fields (WHY · GUARDS · REDIRECT · SIGNPOST · UPDATED) — no blanks
- [ ] REDIRECT is specific (path / calendarId / desk name), not generic
- [ ] SIGNPOST names the canonical rule doc/file + what to do instead to comply; a change to this rule goes to the person (re-teach, don't just wall)
- [ ] Deny message includes WHY + REDIRECT + SIGNPOST (the RULE) inline
- [ ] Tested locally with an echo pipe — necessary, and nowhere near sufficient
- [ ] A suite in `system/hooks/tests/`, whose ALLOW cases come first
- [ ] Registered as a row in `system/register/register.jsonl`, run through `system/register/generate.py`, which writes the plugin's `hooks/hooks.json` (and `.claude/settings.json`), in the SAME commit
- [ ] Restarted, then watched it fire for real and READ the message
- [ ] Committed + pushed; `git pull` on the other machine, ~~confirm its settings.json symlink~~, then **watched it fire on both**
  > **⚠ CORRECTED 2026-08-24:** `~/.claude/settings.json` is not a symlink into the repo (measured
  > directly this session: regular file, 15,516 bytes, content differs from the repo's tracked copy —
  > `system/tools/gws-audit.sh` documents this was a deliberate conversion away from a symlink). A
  > `git pull` does not update it. The real checklist step is: confirm the new/changed registration
  > reached the other machine by the register-and-generate route (its row in
  > `system/register/register.jsonl`, run through `system/register/generate.py`), not "confirm its symlink."  ⛔ not shipped to the public subset — private-clone only.
