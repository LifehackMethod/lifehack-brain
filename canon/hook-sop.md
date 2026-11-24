---
id: system-playbook-hook-sop
title: "Hook SOP — when & how to reach for a hook (the decision layer)"
record_type: playbook
created_at: 2026-06-17
updated_at: 2026-10-31
status: active
authority: user
reader_note: "The DECISION layer for hooks (WHEN + WHICH kind). Mechanics live in canon/hook-contract.md — where this page restates a mechanic, the copies agree with hook-contract.md. The single front door: it POINTS, it does not duplicate. Keep it concise."
history: "canon/hook-sop.history.md (retired and moved text; never read in normal use)"
route_format: "[section, line_in_this_file, purpose]; find a section by grep -n on its heading text; generated last, regenerate after any edit"
route:
  - ["§1", 107, "when a hook is worth building at all: the two reasons, the smallest tool, what not to hook"]
  - ["§2", 114, "which of the three kinds: BLOCK, INJECT, OBSERVE"]
  - ["§3", 120, "the three build principles the mechanics doc omits: the channel, fail-closed, lean injection"]
  - ["§3.2", 122, "fail postures: closed, degrade-safe, or open with its reason"]
  - ["§4", 125, "prove it fires: read the message, test through the registered entry point, deploy and restart"]
  - ["DO NOT BUILD", 152, "what was tried and failed, grouped by the failure it teaches (read by deadend_check.py)"]
  - ["§5", 274, "the front door: pointers to the mechanics and the other files"]
---

# Hook SOP — when & how to reach for a hook

> **This doc owns WHEN to build a hook and WHICH kind. `canon/hook-contract.md` owns the mechanics; where this doc restates one, the copies agree with `hook-contract.md`.** It is the single **front door** for hooks: it POINTS at the canonical files, never copies them. Keep it concise — if it grows into a second mechanics manual, it has failed. (Council-ratified 2026-06-17; diverge→argue→converge.)

> **Shared tools:** `system/organism/elements/shared-layer.md` — common tools exist once in `shared/` (list: `system/register/toolbox.md`); use them, never copy them. ⛔ archived 2026-11-22 (V1 element page, now in archive/organism-elements-v1-2026-11-22/; look for its V2 replacement)

# Doing hook work right means…

> **Words used here**
> - **hook** — a script the harness runs on an event (before a tool, after a tool, on the person's message, at session start).
> - **guard** — a hook that blocks an act.
> - **BLOCK / INJECT / OBSERVE** — the three kinds: stop the act (`PreToolUse`) / remind the model (`UserPromptSubmit`) / record or warn (`PostToolUse`).
> - **deny message** — the text a BLOCK prints when it stops something; the half a human actually reads.
> - **SIGNPOST** — the part of a hook that names where the rule is written and what to do instead.
> - **dark** — a hook that runs and reports nothing wrong, but whose block or message nobody receives.
> - **register row** — the one line in `system/register/register.jsonl` that registers a hook.
> - **fail posture** — what a hook does when it hits its own error: `closed`, `degrade-safe` or `open`.
> - **pipe test** — feeding a hook a fake payload through an echo pipe (full commands in Part 2); **live fire** — triggering it through the real harness.

## 1. Every time…

- Read `canon/hook-contract.md` before writing any hook; `canon/hook-sop.md` decides whether to build one and which kind. → hook-contract, top; hook-contract, Hook Creation Checklist
- A hook is built only for a hard invariant that has to survive model drift and compaction, justified by EITHER (a) a real past incident OR (b) a catastrophic, silent failure on an unrecoverable surface (auth/credentials · the wrong calendar · a destructive write · the wrong machine). "It would be nice to enforce" is not justification. → hook-sop §1
- Do not hook style or tone, anything needing judgment over conversation state (that goes to a skill gate or an Archivist sweep), or a speculative rule with no incident behind it. → hook-sop §1; DO NOT BUILD
- Pick the kind by asking "should this be STOPPED, or REMINDED?" BLOCK = `PreToolUse`, deny + non-zero exit, for an act that should not happen (destructive / irreversible / wrong-target). INJECT = `UserPromptSubmit`, plain stdout + `exit 0`, to re-ground without stopping. OBSERVE = `PostToolUse`, always `exit 0`, to record or warn; it cannot block. A mis-pick is a failure. → hook-sop §2
- The payload is read from STDIN (`INPUT=$(cat)`), never from `$1` or `$ARGUMENTS`. Reading `$1` fails silently: three hooks captured ZERO entries under 300+ daily calls and reported success throughout. → hook-contract, Hook Types; hook-sop DO NOT BUILD
- The hook opens, immediately after the shebang, with the LLM CONTEXT block, all 5 fields filled, no blanks: `# WHY:` (the specific incident) · `# GUARDS:` · `# REDIRECT:` · `# SIGNPOST:` · `# UPDATED: [YYYY-MM-DD]`. → hook-contract, The LLM Context Block; Hook Creation Checklist
- REDIRECT is specific: the exact path, ID, calendarId, desk name or command to recover. "See Lifehack architecture" is not a redirect. → hook-contract, The LLM Context Block
- SIGNPOST, on every hook: names the canonical rule doc/file and what to do instead to comply; a change to this rule goes to the person. A block without a signpost is a wall. → hook-contract, The LLM Context Block
- Start from a copy of the closest SHIPPED hook; there is no `system/templates/hook-template.sh` (⛔ none ships). → hook-contract, Hook Creation Checklist
- Both halves are files in the repo: the script at `system/hooks/{name}.sh`, and a register row in `system/register/register.jsonl`, run through `system/register/generate.py`, which writes `hooks/hooks.json` and `.claude/settings.json` — in the SAME commit. Neither generated file is edited by hand. → hook-contract, Registration; Deploy & Verify 1–2; Hook Creation Checklist; hook-sop §4
- A pipe test (echo pipe) was run — necessary, and nowhere near sufficient: it proves only that the script did not crash, not that the harness honored it. → hook-contract, Testing a Hook Locally; hook-sop §4
- A suite in `system/hooks/tests/`, with its ALLOW cases first (a guard that blocks ordinary work gets unregistered and then guards nothing). → hook-contract, Testing a Hook Locally; Hook Creation Checklist
- ⛔ RESTART after registering. The harness reads `settings.json` at session start, so a newly registered hook does nothing at all in the window that registered it, and the only symptom is silence — the single commonest reason a correct hook appears not to work. → hook-sop §4; hook-contract, Deploy & Verify 3
- After ANY hook change: trigger it for real through the real harness and READ the message it prints, not just the exit code. A hook not watched blocking/injecting in a live attempt is not a control. → hook-sop §4; hook-contract, Deploy & Verify 4
- Committed and pushed; then `git pull` on the other machine, confirm the registration reached it by the register-and-generate route (its row in `system/register/register.jsonl`, run through `system/register/generate.py`), and watch it fire on both. `~/.claude/settings.json` is a regular file, not a symlink into the repo; a `git pull` does not update it. (Private-clone only; not shipped to the public subset.) → hook-contract, Hook Creation Checklist (CORRECTED 2026-08-24)

## 2. In these situations…

- If it is a BLOCK → the deny text goes to stderr, then `exit 2` (the house standard): `DENY='{"decision":"block","reason":"BLOCKED: [what]. WHY: [the incident or rule]. REDIRECT: [specific path or action]. RULE: [canonical doc/file + what to do instead to comply; a change to this rule goes to the person]."}'` and `deny() { printf '%s\n' "$DENY" >&2; exit 2; }`. Mirror `guard_calendar_writes.sh`. → hook-contract, Canonical Deny Format; hook-sop §3.1
- If it is a BLOCK → the `{"decision":"block",...}` JSON on STDOUT is also honored (with `exit 1` per the exit table). → hook-contract, PreToolUse; Exit Code Semantics
- If it is a BLOCK → never `exit 0` on a deny path: exit 0 = ALLOW, silently. The block text prints and the act still runs; a calendar guard was non-functional this way from 2026-05-31 until fixed 2026-06-01. → hook-sop DO NOT BUILD
- If it is a BLOCK → NEVER put the JSON on stderr with `exit 1`: neither channel is read, and the guard goes silently DARK. → hook-contract, PreToolUse; Canonical Deny Format
- If it is a BLOCK → do not use the `hookSpecificOutput` / `permissionDecision` format. → hook-contract, Canonical Deny Format
- If it is a BLOCK → the deny message carries WHY + REDIRECT + SIGNPOST (the RULE) inline. A wrong redirect is worse than none: it actively misroutes (13 payload tests passed on a deny that named the wrong store). → hook-contract, The LLM Context Block; hook-sop §4
- After ANY hook change → trigger the block through the real harness, read the message it prints (not just the return code), and re-parse the deny JSON; a malformed deny goes silently DARK, honoured by neither channel. → hook-sop §4
- If you want only a warning before a tool runs → a `PreToolUse` hook that prints a caution and `exit 0`s is invisible to the model; that was replaced by a hard block (`exit 2`) with a redirect. → hook-sop DO NOT BUILD
- If it is an INJECT → deliver with plain `echo`/stdout + `exit 0`; NEVER the `systemMessage` JSON field — it is silently dropped: the hook reports success and nothing reaches the model. Mirror `pm_persist.sh`. → hook-sop §3.1
- If it is an INJECT → injected text ≤ ~150 tokens, active-recall (the model restates its frame, not re-reads an identical block), a hard char-ceiling, and an escape path; re-anchor hardest at post-compaction. A static per-turn block becomes wallpaper; what replaced it was a rotating anchor (5 variants, active recall). → hook-sop §3.3; DO NOT BUILD
- If it is an INJECT → it re-grounds as often as needed: every turn for a skill's lean anchor; once, and again after compaction, for the project-manager line. → hook-sop §2
- If it is an OBSERVE (`PostToolUse`) → always `exit 0`; warnings go to stderr; never exit non-zero to block (`exit 1` is invalid here). → hook-contract, PostToolUse; Exit Code Semantics
- If it is a narrow, single-target BLOCK → fail-closed: on ANY error (can't read stdin / parse fails) it DENIES (`exit 2`), never `exit 0`/allow-on-error. → hook-sop §3.2; hook-contract, Exit Code Semantics
- If its matcher is broad (`Bash`, `Write|Edit`) → degrade-safe instead: on an internal error it exits 0 and says so on stderr (else a malformed payload walls the session off from the shell). See `guard_build_mode.sh` `FAIL_POSTURE`. → hook-sop §3.2
- The posture follows the MATCHER, not how few commands you mean to block: a hook on a `Bash` or `Write|Edit` matcher is degrade-safe even when it guards only one script. → hook-sop §3.2
- If a hook should fail open → allowed, if it says why, as `enforce_egress_allowlist.sh` does. → hook-sop §3.2; hook-contract, Exit Code Semantics
- If you are writing the LLM CONTEXT block → declare one `# FAIL_POSTURE: closed|degrade-safe` line, or `open` with its reason (a declared intent, not a new checked field). → hook-sop §3.2
- If it is the in-process scan gate (`shared/gate/ingest_gate.py`) → by default it refuses a read it cannot check, except email (only ever flagged, never quarantined); `INGEST_GATE_POSTURE=warn` makes every read it cannot check fail open (the instant revert). → hook-sop §3.2
- If testing a hook that is a `.sh` wrapper around a `.py` → exercise it through its REGISTERED entry point, never the logic sibling; calling the sibling can fail OPEN (`rc=0`) and make a healthy guard look broken. When a healthy guard looks broken, suspect the test first. → hook-sop §4 Trap 1
- If testing locally → `echo '{"tool_input":{"command":"ls -la"}}' | bash system/hooks/enforce_egress_allowlist.sh; echo "rc=$?"` (Bash matcher) or `echo '{"tool_input":{"file_path":"/tmp/test.md"}}' | bash system/hooks/guard_canon_write.sh; echo "rc=$?"` (Write|Edit matcher). → hook-contract, Testing a Hook Locally
- If the guard matches the command STRING → it will block the commands that document or test it; assemble the trigger tokens from fragments so no literal appears, or put the work in a file and run the file. → hook-sop §4 Trap 2; hook-contract, Testing a Hook Locally
- If a guard looks for keywords in a command → match the write-TO-TARGET pattern, not the bare keyword (later hardened with shlex tokenization); a keyword guard false-fired on its own build's commit. → hook-sop DO NOT BUILD
- If you are tempted to put an LLM call inside a hook to gate a turn → don't: ~6.0–6.2s cold start per call (a Stop-hook judge measured 47–61s and flagged ZERO real violations in ~30–40 turns). → hook-sop DO NOT BUILD
- If the problem is a delivery problem → do not answer it by building detectors; add one line to an injection that already fires. → hook-sop DO NOT BUILD
- If an enforcement gate lives inside a skill → use an external mechanical check (`test -f GATE.ok || exit 1`), not prose; the AI reasons past prose gates. → hook-sop DO NOT BUILD
- If a job or session needs an outside fetch (Gmail, calendar, sheet values, curl, urllib, requests) → go through the shared fetch (`safe_fetch.py`, `safe_search_api.sh`, the email shared fetch), the only files allowed a raw call, listed in `system/tools/shared-fetch-allowlist.txt`; a raw call is refused (`system/tools/install-schedulers.sh --check-row`, `system/hooks/ingest_gate_enforce.sh` clause (h)). → hook-sop DO NOT BUILD
- If code names a model → by tier (`small|medium|large`) via `system/tools/model.lib.sh` (`MODEL_ID_SMALL/MEDIUM/LARGE`) or `shared/tools/model_ids.py` `model_id(tier)`, never a literal id; a literal id is refused and a retired one fails silently behind a fail-safe wrapper. → hook-sop DO NOT BUILD
- If a hook seems not to fire on this machine → it may not be registered here: a hook not registered on the machine you are at is silently dark, and nothing reports it. `system/register/check_drift.py` (on commit) and `register-drift.yml` (CI, every push and pull request) catch a script without a registration or the reverse; neither can tell you the session was never restarted. → hook-contract, Deploy & Verify
- If you need to change `.claude/settings.json` → it is on this repo's deny-list (`Edit(.claude/settings.json)`); editing it is a deliberate act by a person. → hook-contract, Registration
- If you need to edit a hook script → `system/hooks/**` is on the Edit tool's deny-list; editing one is a deliberate act. This entry is register-governed: `generate.py` removes it for the duration of a declared, expiring `state=suspended` on the `guard_hook_sop_read.sh` row and appends it back when the suspension ends. → hook-contract, Permission Model
- If you are editing the DO NOT BUILD section → do not "helpfully" de-duplicate it against the skills SOP; it is duplicated by design. → hook-sop DO NOT BUILD

## 3. Good practice

- Use the smallest tool that gets compliance — an instruction in CLAUDE.md, a gate inside a skill, the user-turn boundary, or a hook; don't open with the heaviest. → hook-sop §1
- A preference forced into a hook becomes wallpaper; style, tone and "usually do X" live in CLAUDE.md or a skill. → hook-sop §1
- A guard that reads a shell command as text is a speed bump; the controls that held were on typed tools (measured 2026-08-14). → hook-sop §1
- Before trusting a hook is working, look for the shape under every failure: something reported success while producing nothing observable. → hook-sop DO NOT BUILD
- Hook scripts are ordinary tracked files, mode `755`. ⚠ Do not `chmod 444` them — friction with no guarantee behind it. → hook-contract, Permission Model
- The generated command starts from `${CLAUDE_PROJECT_DIR}` (the plugin's `hooks/hooks.json` uses `${CLAUDE_PLUGIN_ROOT}`); an absolute path baked into either file works on exactly one computer. → hook-contract, Registration
- Read the LLM CONTEXT block of a worked example (`ingest_gate_enforce.sh`, `enforce_egress_allowlist.sh`, `guard_canon_write.sh`, `guard_throughline_write_scope.sh`, `pm_persist.sh`, `session_context_loader.sh`, all in `system/hooks/`) and copy the suites in `system/hooks/tests/`. → hook-contract, Worked examples; Testing a Hook Locally
- Use the input-parsing patterns in the contract (Bash command; Write|Edit `file_path` falling back to `path`; PostToolUse `file_path` via grep). → hook-contract, Input Parsing Patterns
- Arm/clear/TTL of a skill's anchor → `canon/skill-building-sop.md`, Build steps 9 and 14; the live hook catalog → `hooks/hooks.json`. → hook-sop §5

— end of checklist —

## §1 — When to reach for a hook at all
- A hook is for a **hard invariant that has to survive model drift + compaction** — justified by EITHER **(a)** a real past incident, OR **(b)** a catastrophic-**silent** failure on an unrecoverable surface (auth/credentials · the wrong calendar · a destructive write · the wrong machine). *"It would be nice to enforce"* is **not** justification.
- **Use the smallest tool that gets the compliance** — an instruction in CLAUDE.md, a gate inside a skill, the user-turn boundary, or a hook. A hook is the strongest, so it has to earn its place (the two reasons above). Don't open with the heaviest tool.
- **A rule that isn't a hook is a wish** — but the inverse holds: a *preference* forced into a hook becomes wallpaper. Style/tone/"usually do X" live in CLAUDE.md or a skill.
- **A guard that reads a shell command as text is a speed bump; the controls that held were on typed tools** (measured 2026-08-14).
- **DO NOT hook:** style/tone; anything needing judgment over conversation *state* (→ a skill gate or an Archivist sweep, a stateless hook can't do it); a speculative rule with no incident behind it.

## §2 — Which of the three kinds
- **BLOCK** — `PreToolUse`, deny + non-zero exit. Use when **the act itself should not happen** (destructive / irreversible / wrong-target).
- **INJECT** — `UserPromptSubmit`, plain stdout + exit 0. Use to **re-ground the model as often as it is needed (every turn for a skill's lean anchor; once, and again after compaction, for the project-manager line) without stopping it** (the anchor / project-manager pattern).
- **OBSERVE** — `PostToolUse`, always exit 0. Use to **record or warn** — it structurally *cannot* block.
- **Mis-pick = failure:** a BLOCK used for guidance stops with no way forward; an INJECT used for a hard rule is a wish dressed as a guard. Decide by: *should this be STOPPED, or REMINDED?*

## §3 — The three build principles the mechanics doc omits
1. **The channel (the landmine):** an INJECT hook delivers via **plain `echo`/stdout + `exit 0`** — **NEVER** the `systemMessage` JSON field (silently dropped: the hook reports success and nothing reaches the model). A BLOCK denies via the **working** channel — deny text + `exit 2` (the honored block signal). Mirror `pm_persist.sh` (inject) and `guard_calendar_writes.sh` (block).
2. **Fail-closed:** on ANY error (can't read stdin / parse fails) a **narrow, single-target** BLOCK hook **denies** — never `exit 0`/allow-on-error. *(Scope, 2026-10-30: fail-closed applies to what a guard is FOR — `canonical-principles-sop.md` "Fail-closed applies to what a guard is FOR". A broad matcher (`Bash`, `Write|Edit`) is **degrade-safe** instead: on an internal error it exits 0 and says so on stderr, or a malformed payload walls the session off from the shell; see `guard_build_mode.sh` `FAIL_POSTURE`. The in-process scan gate (`shared/gate/ingest_gate.py`) is a third case: by default it refuses a read it cannot check, except email, which stays open because it is only ever flagged, never quarantined; setting `INGEST_GATE_POSTURE=warn` makes every read it cannot check fail open (the instant revert).)* Declare it as one `# FAIL_POSTURE: closed|degrade-safe` line, or `open` with its reason, as `enforce_egress_allowlist.sh` does, in the LLM-CONTEXT block (a declared intent, not a new checked field).
3. **Lean / anti-wallpaper (inject only):** injected text ≤ ~150 tokens, **active-recall** (make the model RESTATE its frame, not re-read an identical block that becomes wallpaper), a hard char-ceiling, and an escape path. Re-anchor hardest at **post-compaction**.

## §4 — Prove it fires

> **★ WATCHING IT FIRE CATCHES WHAT PAYLOAD TESTS CANNOT — AND A WRONG REDIRECT IS WORSE THAN NO
> REDIRECT.** (2026-08-05, T18.6b; the full story is in the history log.) A guard extended to a second store passed **13 synthetic
> payloads**, then fired for real, and its **deny message named only the ORIGINAL store and redirected to the
> wrong writer**. Every payload test passed because they only ever asserted the **exit code**, and the deny TEXT is the
> half a human actually reads. **A hook's job is to RE-TEACH the boundary, not merely block it** (see the
> SIGNPOST rule in `hook-contract.md`) — so a wrong redirect actively misroutes, where a missing one at
> least fails obviously. **How to apply:** after any hook change, trigger the block **through the real
> harness** and *read the message it prints*, not just its return code. **And re-parse the deny JSON
> afterwards — a malformed deny goes silently DARK**, honoured by neither channel.
>
> **⚠ TWO TRAPS THAT MAKE A HEALTHY GUARD LOOK BROKEN — both hit on 2026-08-05.**
> **(1) EXERCISE A HOOK THROUGH ITS REGISTERED ENTRY POINT, NEVER ITS LOGIC SIBLING.** Several guards are
> a `.sh` wrapper around a `.py`. In the original system, the `.sh` wrapper exported `ALLOWLIST_FILE`, which
> the `.py` read; invoking the `.py` directly left it unset, so it opened `''`, threw, and **failed OPEN
> (`rc=0`)**. For several minutes the evidence read *"the egress wall allows a real off-allowlist host."*
> It does not. *(In this repository the `.py` finds its own list, so this exact trap is gone; the lesson
> stands.)* ⇒ *suspect the test first* — now paid out **ten** times on this project (as counted by
> 2026-08-11, not re-checked).
> **(2) A COMMAND-STRING GUARD BLOCKS ITS OWN DOCUMENTATION.** The same guard blocked the very commands
> writing its fix, because the docstring **quoted** the attack it defends against. Same class as the
> 2026-07-13 status-bar guard that blocked its own build's commit (`build-sop.md` *(retired 2026-10-31)*). Workaround when
> authoring: assemble the trigger tokens from fragments so no literal appears in the command.
- A hook you haven't **watched block/inject in a live attempt is not a control** — an echo-pipe test proves only that the script didn't crash, not that the harness honored it.
- **Deploying it:** both halves are files in this repo — the script at `system/hooks/`, the registration, a row in `system/register/register.jsonl` (`system/register/generate.py` generates `hooks/hooks.json` and `.claude/settings.json` from it) — so both travel by `git pull` and neither is re-done by hand. ⛔ **Then RESTART.** The harness reads `settings.json` at session start, so a newly registered hook does nothing at all in the window that registered it, and the only symptom is silence. That is the single commonest reason a correct hook appears not to work. (→ `canon/hook-contract.md`, Deploy & Verify.)

## DO NOT BUILD — what was tried and failed

> **This section is DUPLICATED BY DESIGN across `hook-sop.md` and the skills SOP**
> (the operator's ruling, 2026-08-07, verbatim: *"I would rather have duplication than miss something."*) — a
> retired rule got re-installed TWICE in one day because no session could ask "has this already been
> tried?" **Do not "helpfully" de-duplicate this across the two SOPs** — each copy is scoped to that
> SOP's own domain and the copies are not required to stay identical. This copy carries the **hook-domain**
> entries only, harvested from a 2026-08-07 dead-end harvest
> (80 entries; this SOP owns the subset below).
>
> **The pattern underneath every entry:** something reported success while producing nothing observable —
> a hook whose deny path exited 0, a logger that captured zero entries under 300+ daily calls, a warning
> the model could not see, a judge that flagged nothing across 40 turns. That is the shape to look for
> before trusting a hook is working.

**Grouped by the failure they teach, not by date. Where §1–§5 above already state the rule, these are its
dated INCIDENTS — evidence, not a restatement.**

### exit 0 on a BLOCK hook is a silent ALLOW (§3 principle 1, "The channel" — already stated; these are its incidents)
- **Tried:** `block_primary_calendar.sh`'s `deny()` written to `exit 0` on both its failure paths → **failed:**
  exit 0 = ALLOW — calendar-write protection was silently non-functional the whole time it was in this
  state. `2026-05-31` (found) / `2026-06-01` (fixed) · an audit record →
  replaced by `deny()` corrected to `exit 2`. **UNIVERSAL** (this is the script §3 cited by name as
  the canonical BLOCK example until 2026-10-30 — it did not start out correct).
- **Tried:** a PreToolUse-style hook's `deny()` using `exit 0` → **failed:** fails OPEN — the block JSON
  prints but the write still executes. `2026-06-17` · a project brief
  → replaced by `exit 2`. **UNIVERSAL**
- **Tried:** a WARNING-ONLY PreToolUse hook (`guard_web_search.sh`) that printed a caution before an
  unsanctioned WebSearch, then `exit 0`'d → **failed:** "exit 0 hooks are invisible to the model" — the
  warning was security theater the model never saw. `2026-05-30` · a log record → replaced by a hard block (`exit 2`) with a
  redirect to `/websearch`. **UNIVERSAL** — a structural fact about the harness, not this hook. Measured narrowly: `additionalContext` from a `PreToolUse` hook on the Agent tool was seen by the session, 4 of 4 (2026-11-19, `experiments/launch-message-channels/`); this does not claim other channels or events.

### a hook's payload comes in on STDIN, never `$1` / `$ARGUMENTS` (mechanics live in `hook-contract.md` per §5 below; these are the incidents that taught it)
- **Tried:** `observability_logger.sh`, `validate_on_write.sh`, `auto_register_skill.sh` reading their
  PostToolUse payload from `$1` → **failed:** the harness delivers payload via STDIN — ZERO real entries
  captured despite 300+ daily calls, and all three hooks reported success throughout. `2026-05-31` (found)
  / `2026-06-01` (fixed) · an audit record → replaced by reading stdin via
  `$(cat)`. **UNIVERSAL**
- **Tried:** using the `$ARGUMENTS` token in `settings.json` to pass stdin content into a hook → **failed:**
  Claude Code delivers hook input via STDIN, not as `$1`. `2026-05-30` ·
  a project brief → replaced by `INPUT=$(cat)`. **UNIVERSAL**

### a guard that matches a keyword/string, not the real target (§4 Trap 2 — already stated in brief; this is that same incident, with the fix it taught)
- **Tried:** a guard hook grepping a Bash command STRING for keywords (`settings.json` + `statusLine`) →
  **failed:** false-positived on any command merely MENTIONING both words — including its own build's git
  commit message (this is the "2026-07-13 status-bar guard" §4 already references by name). `2026-07-13` ·
  `system/sops/build-sop.md` ⛔ (retired 2026-10-31); a debt-ledger entry → replaced by
  matching the write-TO-TARGET pattern, not the bare keyword; later hardened with shlex tokenization so a
  literal-in-a-string can't trip it. **UNIVERSAL**

### a static per-turn INJECT anchor becomes wallpaper (§3 principle 3, anti-wallpaper — already stated; these are its incidents, plus the upstream cause)
- **Tried:** state the desired response voice ONCE in always-loaded CLAUDE.md → **failed:** the rule faded
  — models skip preambles by default and guidance decayed over a long/resumed session (CLAUDE.md loads
  only at session start). `2026-06-08` · a debug-history record → replaced
  by a firmer rewrite + a dedicated SOP, later a per-turn reinforcement. **UNIVERSAL**
- **Tried:** an always-on Output Style as the session-start voice baseline → **failed:** "loads once at
  start -> same decay" — didn't hold across a resumed session. `2026-06-27` ·
  a debug-history record → replaced by a rotating per-turn anchor hook.
  **UNIVERSAL**
- **Tried:** a STATIC per-turn anchor hook re-asserting the same voice-rule block every turn → **failed:**
  "became wallpaper" — the model tuned it out. `2026-06-28` ·
  a debug-history record → replaced by a rotating anchor (5 variants,
  active recall). **UNIVERSAL**

### an LLM-in-the-loop hook is too slow or too unreliable to gate a turn on (not yet stated elsewhere in this SOP)
- **Tried:** a per-turn LLM classifier (`claude -p --model haiku`) on every UserPromptSubmit to decide "does
  this need math?" → **failed:** ~6.0–6.2s COLD-START latency (CLI boot, not inference) — unacceptable in a
  synchronous per-turn hook; no API key available for a sub-second call instead. `2026-06-27` ·
  a decision record → replaced by a declare-intent model
  (finance desks auto-arm, `/calculate` elsewhere, regex only as backstop). **LOCAL**
- **Tried:** a Stop-hook LLM "bounce judge" that regenerates a reply failing a quality check → **failed:**
  killed three ways — self-critique degrades the output it's judging; latency measured 6s → 47–61s per call
  (CLI boot); and across ~30–40 live turns the grader flagged ZERO real violations (a rubber stamp —
  cheap-judge true-negative rate was under 30% in one study, Jain et al. NeurIPS 2025). `2026-07-12/13` and
  recorded again from the project brief · a debug-history record and
  a project brief → replaced by a 3-layer plan (output-style + examples,
  a parked grader, a planned local classifier) — the Stop-hook judge itself was killed outright.
  **UNIVERSAL**

### a hook can't do judgment over conversation state — don't hook it (§1's "DO NOT hook" line — already stated; these are its incidents)
- **Tried:** a Stop/block gate halting on ungrounded arithmetic → **failed:** a hook cannot distinguish a
  number the model COMPUTED from one it READ — provenance is invisible in text, so it would false-fire
  constantly. `2026-06-27` · a decision record → replaced by
  no blocking gate at all. **LOCAL**
- **Tried:** a status-bar write-GUARD hook on `statusline.sh` blocking python/bash writes to it → **failed:**
  false-positived on legitimate work. `NO-DATE` · a project brief → replaced
  by editing `statusline.sh` with the Edit tool only, plus an inline warning comment — no hook at all.
  **LOCAL**

### prose is not a guard — the reason a hook exists at all (adjacent to §1's "a rule that isn't a hook is a wish"; recorded here because it is the harvest entry that most directly evidences it)
- **Tried:** polite prompt instructions used as an enforcement gate inside a skill → **failed:** "the AI
  reasons past prose gates." `NO-DATE` (LOG-04) · a project brief →
  replaced by an external mechanical check (`test -f GATE.ok || exit 1`), not skill prose — the same
  logic that makes a hard invariant a hook's job, never a paragraph's. **UNIVERSAL**

### building a detector answers a delivery problem, not a detection problem (not yet stated elsewhere in this SOP)
- **Tried:** answering a DELIVERY problem by building DETECTORS. **Failed:** 863 lines shipped in one day,
  **ZERO with a caller**, while 10 existing per-turn injectors sat unused; the shared module built to end
  the recurring class was adopted by 3 of 15 tools (as counted on 2026-08-08, not re-checked). `2026-08-08` · a project brief
  → replaced by one line in an injection that already fires. **8th recorded instance (as counted on 2026-08-08, not re-checked) of build-with-no-caller
  in this system** (prior: `compose_reflection` · `judge.py`/`push_gate.py` — *"I built the lock and never
  built the key"* · `check_screens.py` · 4 unused shared primitives). See **THE CODE SPIRAL**,
  `system/build-rules-index.md`. **UNIVERSAL**

### a raw fetch outside the shared fetch is refused, in a job and in a session (self-monitoring 5.2 — the door)
- **Tried:** a job runner or a session making its own raw Gmail, calendar, sheet-values, curl, urllib or requests
  call instead of going through the shared fetch → **failed:** the text arrives unsanitised, unscanned and
  unrecorded, and a desk that holds its own credential can bypass every lock the shared layer carries; this is
  a dead end, met by a door, not advised against. `2026-10-27` · `system/tools/install-schedulers.sh --check-row`
  (jobs: refused at install, no plist) and `system/hooks/ingest_gate_enforce.sh` clause (h) (sessions) →
  replaced by the shared fetch (`safe_fetch.py`, `safe_search_api.sh`, the email shared fetch), the only files
  allowed a raw call, listed in `system/tools/shared-fetch-allowlist.txt`. **UNIVERSAL**

### a hard-coded model id outside the one table is refused (self-monitoring 5.4 — the door)
- **Tried:** a runner, reader or library naming a model by its literal id (`claude-haiku-4-5...`) instead of a tier
  (`small|medium|large`) → **failed:** the id retires, the call exits 1, and a fail-safe wrapper swallows it. The
  email reader named a retired id, so the danger path had NEVER worked headless and nothing said so; `2026-10-28`
  · `shared/tools/intake_reader.py` · met by a door, `system/tools/install-schedulers.sh --check-row`
  rule (d) (no plist) and `system/tools/tests/test_no_hardcoded_model_ids.sh` (new ids fail the suite) →
  replaced by the tier table `system/tools/model.lib.sh` (`MODEL_ID_SMALL/MEDIUM/LARGE`; Python reads it via
  `shared/tools/model_ids.py` `model_id(tier)`), the only files allowed an id. **UNIVERSAL**

## §5 — The front door (pointers — one file each; where restated, the copies agree with `hook-contract.md`)
- **Mechanics** (exit codes · stdin parsing · deny format · registration · the **Deploy & Verify
  checklist**) → ✅ `canon/hook-contract.md`
- **Injector arm/clear/TTL lifecycle + WHEN a skill arms its anchor** → `canon/skill-building-sop.md`, Build steps 9 and 14 (the skills SOP was written fresh 2026-11-10; the older detail, §IV.3 and §IV.7, is in `system/_retired-2026-11-10/skill-building-sop.ARCHIVE-2026-11-10.md`)
- **Is-this-hook-well-built conformance check** (the LLM-CONTEXT block audit) → the LLM Context Block section of `canon/hook-contract.md` (the old pointer, the skill conformance checklist, was archived 2026-11-10 to `system/_retired-2026-11-10/`)
- **The catalog of coded friction points / fitness functions** → the live list is `hooks/hooks.json` (generated from `system/register/register.jsonl`); each guard's own header says what it blocks and why
