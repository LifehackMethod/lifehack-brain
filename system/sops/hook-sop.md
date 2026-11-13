---
id: system-playbook-hook-sop
title: "Hook SOP — when & how to reach for a hook (the decision layer)"
record_type: playbook
created_at: 2026-06-17
updated_at: 2026-10-31
status: active
authority: user
reader_note: "The DECISION layer for hooks (WHEN + WHICH kind). Mechanics live in system/hook-contract.md — where this page restates a mechanic, the copies agree with hook-contract.md. The single front door: it POINTS, it does not duplicate. Keep it concise."
history: "system/sops/hook-sop.history.md (retired and moved text; never read in normal use)"
route_format: "[section, line_in_this_file, purpose]; find a section by grep -n on its heading text; generated last, regenerate after any edit"
route:
  - ["§1", 28, "when a hook is worth building at all: the two reasons, the smallest tool, what not to hook"]
  - ["§2", 35, "which of the three kinds: BLOCK, INJECT, OBSERVE"]
  - ["§3", 41, "the three build principles the mechanics doc omits: the channel, fail-closed, lean injection"]
  - ["§3.2", 43, "fail postures: closed, degrade-safe, or open with its reason"]
  - ["§4", 46, "prove it fires: read the message, test through the registered entry point, deploy and restart"]
  - ["DO NOT BUILD", 73, "what was tried and failed, grouped by the failure it teaches (read by deadend_check.py)"]
  - ["§5", 195, "the front door: pointers to the mechanics and the other files"]
---

# Hook SOP — when & how to reach for a hook

> **This doc owns WHEN to build a hook and WHICH kind. `system/hook-contract.md` owns the mechanics; where this doc restates one, the copies agree with `hook-contract.md`.** It is the single **front door** for hooks: it POINTS at the canonical files, never copies them. Keep it concise — if it grows into a second mechanics manual, it has failed. (Council-ratified 2026-06-17; diverge→argue→converge.)

> **Shared tools:** `system/organism/elements/shared-layer.md` — common tools exist once in `shared/` (list: `system/register/toolbox.md`); use them, never copy them.

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
- **Deploying it:** both halves are files in this repo — the script at `system/hooks/`, the registration, a row in `system/register/register.jsonl` (`system/register/generate.py` generates `hooks/hooks.json` and `.claude/settings.json` from it) — so both travel by `git pull` and neither is re-done by hand. ⛔ **Then RESTART.** The harness reads `settings.json` at session start, so a newly registered hook does nothing at all in the window that registered it, and the only symptom is silence. That is the single commonest reason a correct hook appears not to work. (→ `system/hook-contract.md`, Deploy & Verify.)

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
  redirect to `/websearch`. **UNIVERSAL** — a structural fact about the harness, not this hook.

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
  checklist**) → ✅ `system/hook-contract.md`
- **Injector arm/clear/TTL lifecycle + WHEN a skill arms its anchor** → `system/sops/skill-building-sop.md`, Build steps 9 and 14 (the skills SOP was written fresh 2026-11-10; the older detail, §IV.3 and §IV.7, is in `system/_retired-2026-11-10/skill-building-sop.ARCHIVE-2026-11-10.md`)
- **Is-this-hook-well-built conformance check** (the LLM-CONTEXT block audit) → the LLM Context Block section of `system/hook-contract.md` (the old pointer, the skill conformance checklist, was archived 2026-11-10 to `system/_retired-2026-11-10/`)
- **The catalog of coded friction points / fitness functions** → the live list is `hooks/hooks.json` (generated from `system/register/register.jsonl`); each guard's own header says what it blocks and why
