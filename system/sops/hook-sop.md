---
id: system-playbook-hook-sop
title: "Hook SOP — when & how to reach for a hook (the decision layer)"
record_type: playbook
created_at: 2026-06-17
updated_at: 2026-06-17
status: active
authority: user
sources:
  - system/research/2026-06-17-skill-anchoring-hooks-consensus.md
  - system/research/2026-06-17-agent-procedure-enforcement-consensus.md
  - "an architecture council, 2026-06-17"
reader_note: "The DECISION layer for hooks (WHEN + WHICH kind). Mechanics live in system/hook-contract.md — this never repeats them. The single front door: it POINTS, it does not duplicate. Keep it ONE page."
---

# Hook SOP — when & how to reach for a hook

> **This doc owns WHEN to build a hook and WHICH kind. It does NOT repeat the mechanics — `system/hook-contract.md` owns those.** It is the single **front door** for hooks: it POINTS at the canonical homes, never copies them. Keep it short — if it grows into a second mechanics manual, it has failed. (Council-ratified 2026-06-17; diverge→argue→converge.)

> ⓘ **WHAT THIS PAGE POINTS AT THAT IS NOT IN THIS REPOSITORY.** A front door is only as good as the
> rooms behind it, so the missing rooms are named here rather than discovered by a reader who goes
> looking. This block is the whole list.
>
> - ⏳ **UNRULED — `system/hook-contract.md`.** The mechanics half of this page: exit codes, stdin
>   parsing, the deny format, registration, `chmod`. **It is on no ship list, and this page is the
>   decision half of a pair.** Until it crosses, §5's first pointer leads nowhere and the mechanics you
>   need are in the shipped hooks themselves — `system/hooks/pm_flag.sh` is the fullest worked example.
> - ✅ **`/calculate` has arrived**, with the two scripts the §3 story is about:
>   `system/hooks/numbers_flag.sh` (the switch) and `system/hooks/inject_compute_mechanically.sh`
>   (the per-turn half). (`/websearch` arrived before it.)
> **Not shipped — where a §3 story cites one of these, the story's evidence is in the story; the
> pointer was only ever the filing location of the original write-up:**
>
> - ⛔ `docs/architecture.md` — the author's own map of their whole system.
> - ⛔ `docs/skill-conformance.md` — their conformance checker's rulebook.
> - ⛔ `system/reference/settings.json` — one machine's symlink source, which the single-machine
>   model here made meaningless. Registration lives in `.claude/settings.json` and travels by `git pull`.
> - ⛔ `system/sops/build-sop.md` — see the same entry under `system/build-rules-index.md`.

## §1 — When to reach for a hook at all
- A hook is for a **hard invariant that must survive model drift + compaction** — justified by EITHER **(a)** a real past incident, OR **(b)** a catastrophic-**silent** failure on an unrecoverable surface (auth/credentials · the wrong calendar · a destructive write · the wrong machine). *"It would be nice to enforce"* is **not** justification.
- **Climb the escalation ladder first — a hook is the LAST rung:** instruction (CLAUDE.md) → a binary gate inside a skill → the user-turn boundary → a hook. Don't open with the heaviest tool.
- **A rule that isn't a hook is a wish** — but the inverse holds: a *preference* forced into a hook becomes wallpaper. Style/tone/"usually do X" live in CLAUDE.md or a skill.
- **DO NOT hook:** style/tone; anything needing judgment over conversation *state* (→ a skill gate or an Archivist sweep, a stateless hook can't do it); a speculative rule with no incident behind it.

## §2 — Which of the three kinds
- **BLOCK** — `PreToolUse`, deny + non-zero exit. Use when **the act itself must not happen** (destructive / irreversible / wrong-target).
- **INJECT** — `UserPromptSubmit`, plain stdout + exit 0. Use to **re-ground the model every turn without stopping it** (the anchor / project-manager pattern).
- **OBSERVE** — `PostToolUse`, always exit 0. Use to **record or warn** — it structurally *cannot* block.
- **Mis-pick = failure:** a BLOCK used for guidance is a wall with no door; an INJECT used for a hard rule is a wish dressed as enforcement. Decide by: *must this be STOPPED, or REMINDED?*

## §3 — The three build rules the mechanics doc omits
1. **Channel law (the landmine):** an INJECT hook delivers via **plain `echo`/stdout + `exit 0`** — **NEVER** the `systemMessage` JSON field (silently dropped: the hook reports success and nothing reaches the model). A BLOCK denies via the **working** channel — deny text + `exit 2` (the honored block signal). Mirror `pm_persist.sh` (inject) and `block_primary_calendar.sh` (block).
2. **Fail-closed:** on ANY error (can't read stdin / parse fails) a BLOCK hook **denies** — never `exit 0`/allow-on-error. Declare it as one `# FAIL_POSTURE: closed|degrade-safe` line in the LLM-CONTEXT block (a declared intent, not a new enforced field).
3. **Lean / anti-wallpaper (inject only):** injected text ≤ ~150 tokens, **active-recall** (make the model RESTATE its frame, not re-read an identical block that becomes wallpaper), a hard char-ceiling, and an escape path. Re-anchor hardest at **post-compaction**.

## §4 — Prove it fires (not optional)

> **★ WATCHING IT FIRE CATCHES WHAT PAYLOAD TESTS CANNOT — AND A WRONG REDIRECT IS WORSE THAN NO
> REDIRECT.** (2026-08-05, T18.6b.) A guard was extended to a second store and passed **13 synthetic
> payloads** — both stores blocked, reads untouched, three false-positive cases correctly ignored. Then
> it was fired for real, and the **deny message named only the ORIGINAL store and redirected to the wrong
> writer**: a session blocked while writing to the NEW store would have been sent to fix the wrong thing.
> Every payload test passed because they only ever asserted the **exit code**, and the deny TEXT is the
> half a human actually reads. **A hook's job is to RE-TEACH the boundary, not merely wall it** (see the
> SIGNPOST rule in `hook-contract.md`) — so a wrong redirect actively misroutes, where a missing one at
> least fails obviously. **How to apply:** after any hook change, trigger the block **through the real
> harness** and *read the message it prints*, not just its return code. **And re-parse the deny JSON
> afterwards — a malformed deny goes silently DARK**, honoured by neither channel.
>
> **⚠ TWO TRAPS THAT MAKE A HEALTHY GUARD LOOK BROKEN — both hit on 2026-08-05.**
> **(1) EXERCISE A HOOK THROUGH ITS REGISTERED ENTRY POINT, NEVER ITS LOGIC SIBLING.** Several guards are
> a `.sh` wrapper around a `.py`. `enforce_egress_allowlist.sh:19` **exports `ALLOWLIST_FILE`**, which the
> `.py` reads; invoking the `.py` directly leaves it unset, so it opens `''`, throws, and **fails OPEN
> (`rc=0`)**. For several minutes the evidence read *"the egress wall allows a real off-allowlist host."*
> It does not. ⇒ *suspect the test first* — now paid out **ten** times on this project.
> **(2) A COMMAND-STRING GUARD BLOCKS ITS OWN DOCUMENTATION.** The same guard blocked the very commands
> writing its fix, because the docstring **quoted** the attack it defends against. Same class as the
> 2026-07-13 status-bar guard that blocked its own build's commit (`build-sop.md`). Workaround when
> authoring: assemble the trigger tokens from fragments so no literal appears in the command.
- A hook you haven't **watched block/inject in a live attempt is not a control** — an echo-pipe test proves only that the script didn't crash, not that the harness honored it.
- **Two machines:** the script travels via `git pull` — AND so does the `settings.json` REGISTRATION, because `~/.claude/settings.json` is symlinked from the clone (`system/reference/settings.json`). You do NOT re-add the entry by hand. What's machine-local is the *symlink itself* (+ `~/.claude/skills/*`, `~/.claude/output-styles/*`), so on both Studio and Air: confirm the symlink exists and **watch it fire** — a broken/missing symlink leaves the hook silently dark. (→ `hook-contract.md` Deploy & Verify checklist.)

## DO NOT BUILD — what was tried and failed

> **This section is DUPLICATED BY DESIGN across `hook-sop.md` and the build/skill SOPs**
> (the operator's ruling, 2026-08-07, verbatim: *"I would rather have duplication than miss something."*) — a
> retired rule got re-installed TWICE in one day because no session could ask "has this already been
> tried?" **Do not "helpfully" de-duplicate this across the three SOPs** — each copy is scoped to that
> SOP's own domain and the copies are not required to stay identical. This copy carries the **hook-domain**
> entries only, harvested from `state/projects/skill-builder/records/2026-08-07-dead-end-harvest.md`
> (80 entries; this SOP owns the subset below).
>
> **The pattern underneath every entry:** something reported success while producing nothing observable —
> a hook whose deny path exited 0, a logger that captured zero entries under 300+ daily calls, a warning
> the model could not see, a judge that flagged nothing across 40 turns. That is the shape to look for
> before trusting a hook is working.

**Grouped by the failure they teach, not by date. Where §1–§5 above already state the rule, these are its
dated INCIDENTS — evidence, not a restatement.**

### exit 0 on a BLOCK hook is a silent ALLOW (§3 rule 1, "Channel law" — already stated; these are its incidents)
- **Tried:** `block_primary_calendar.sh`'s `deny()` written to `exit 0` on both its failure paths → **failed:**
  exit 0 = ALLOW — calendar-write protection was silently non-functional the whole time it was in this
  state. `2026-05-31` (found) / `2026-06-01` (fixed) · an audit record →
  replaced by `deny()` corrected to `exit 2`. **UNIVERSAL** (this is the same script §3 cites by name as
  the canonical BLOCK example — it did not start out correct).
- **Tried:** a PreToolUse-style hook's `deny()` using `exit 0` → **failed:** fails OPEN — the block JSON
  prints but the write still executes. `2026-06-17` · `state/projects/security/security-hardening/brief.md:44-77`
  → replaced by `exit 2`. **UNIVERSAL**
- **Tried:** a WARNING-ONLY PreToolUse hook (`guard_web_search.sh`) that printed a caution before an
  unsanctioned WebSearch, then `exit 0`'d → **failed:** "exit 0 hooks are invisible to the model" — the
  warning was security theater the model never saw. `2026-05-30` ·
  `records/log/2026-05-30-datagate-websearch-automation.md` → replaced by a hard block (`exit 2`) with a
  redirect to `/websearch`. **UNIVERSAL** — a structural fact about the harness, not this hook.

### a hook's payload comes in on STDIN, never `$1` / `$ARGUMENTS` (mechanics live in `hook-contract.md` per §5 below; these are the incidents that taught it)
- **Tried:** `observability_logger.sh`, `validate_on_write.sh`, `auto_register_skill.sh` reading their
  PostToolUse payload from `$1` → **failed:** the harness delivers payload via STDIN — ZERO real entries
  captured despite 300+ daily calls, and all three hooks reported success throughout. `2026-05-31` (found)
  / `2026-06-01` (fixed) · an audit record → replaced by reading stdin via
  `$(cat)`. **UNIVERSAL**
- **Tried:** using the `$ARGUMENTS` token in `settings.json` to pass stdin content into a hook → **failed:**
  Claude Code delivers hook input via STDIN, not as `$1`. `2026-05-30` ·
  `state/projects/security/security-hardening/brief.md:44-77` → replaced by `INPUT=$(cat)`. **UNIVERSAL**

### a guard that matches a keyword/string, not the real target (§4 Trap 2 — already stated in brief; this is that same incident, with the fix it taught)
- **Tried:** a guard hook grepping a Bash command STRING for keywords (`settings.json` + `statusLine`) →
  **failed:** false-positived on any command merely MENTIONING both words — including its own build's git
  commit message (this is the "2026-07-13 status-bar guard" §4 already references by name). `2026-07-13` ·
  `system/sops/build-sop.md`; `state/debt-ledger.md` `[GUARD-HOOKSOP-FALSE-POSITIVE]` → replaced by
  matching the write-TO-TARGET pattern, not the bare keyword; later hardened with shlex tokenization so a
  literal-in-a-string can't trip it. **UNIVERSAL**

### a static per-turn INJECT anchor becomes wallpaper (§3 rule 3, anti-wallpaper — already stated; these are its incidents, plus the upstream cause)
- **Tried:** state the desired response voice ONCE in always-loaded CLAUDE.md → **failed:** the rule faded
  — models skip preambles by default and guidance decayed over a long/resumed session (CLAUDE.md loads
  only at session start). `2026-06-08` · `records/2026-07-13-translator-voice-debug-history.md` → replaced
  by a firmer rewrite + a dedicated SOP, later a per-turn reinforcement. **UNIVERSAL**
- **Tried:** an always-on Output Style as the session-start voice baseline → **failed:** "loads once at
  start -> same decay" — didn't hold across a resumed session. `2026-06-27` ·
  `records/2026-07-13-translator-voice-debug-history.md` → replaced by a rotating per-turn anchor hook.
  **UNIVERSAL**
- **Tried:** a STATIC per-turn anchor hook re-asserting the same voice-rule block every turn → **failed:**
  "became wallpaper" — the model tuned it out. `2026-06-28` ·
  `records/2026-07-13-translator-voice-debug-history.md` → replaced by a rotating anchor (5 variants,
  active recall). **UNIVERSAL**

### an LLM-in-the-loop hook is too slow or too unreliable to gate a turn on (not yet stated elsewhere in this SOP)
- **Tried:** a per-turn LLM classifier (`claude -p --model haiku`) on every UserPromptSubmit to decide "does
  this need math?" → **failed:** ~6.0–6.2s COLD-START latency (CLI boot, not inference) — unacceptable in a
  synchronous per-turn hook; no API key available for a sub-second call instead. `2026-06-27` ·
  `records/decision/2026-06-27-numbers-integrity-enforcement.md` → replaced by a declare-intent model
  (finance desks auto-arm, `/calculate` elsewhere, regex only as backstop). **LOCAL**
- **Tried:** a Stop-hook LLM "bounce judge" that regenerates a reply failing a quality check → **failed:**
  killed three ways — self-critique degrades the output it's judging; latency measured 6s → 47–61s per call
  (CLI boot); and across ~30–40 live turns the grader flagged ZERO real violations (a rubber stamp —
  cheap-judge true-negative rate is structurally under 30%, Jain et al. NeurIPS 2025). `2026-07-12/13` and
  recorded again from the project brief · `records/2026-07-13-translator-voice-debug-history.md` and
  `state/projects/translator-voice/brief.md:97-122` → replaced by a 3-layer plan (output-style + examples,
  a parked grader, a planned local classifier) — the Stop-hook judge itself was killed outright.
  **UNIVERSAL**

### a hook can't do judgment over conversation state — don't hook it (§1's "DO NOT hook" line — already stated; these are its incidents)
- **Tried:** a Stop/block gate halting on ungrounded arithmetic → **failed:** a hook cannot distinguish a
  number the model COMPUTED from one it READ — provenance is invisible in text, so it would false-fire
  constantly. `2026-06-27` · `records/decision/2026-06-27-numbers-integrity-enforcement.md` → replaced by
  no blocking gate at all. **LOCAL**
- **Tried:** a status-bar write-GUARD hook on `statusline.sh` blocking python/bash writes to it → **failed:**
  false-positived on legitimate work. `NO-DATE` · `state/projects/project-system/brief.md:170` → replaced
  by editing `statusline.sh` with the Edit tool only, plus an inline warning comment — no hook at all.
  **LOCAL**

### prose is not enforcement — the reason a hook exists at all (adjacent to §1's "a rule that isn't a hook is a wish"; recorded here because it is the harvest entry that most directly evidences it)
- **Tried:** polite prompt instructions used as an enforcement gate inside a skill → **failed:** "the AI
  reasons past prose gates." `NO-DATE` (LOG-04) · a project brief →
  replaced by an external mechanical check (`test -f GATE.ok || exit 1`), not skill prose — the same
  logic that makes a hard invariant a hook's job, never a paragraph's. **UNIVERSAL**

### building a detector answers a delivery problem, not a detection problem (not yet stated elsewhere in this SOP)
- **Tried:** answering a DELIVERY problem by building DETECTORS. **Failed:** 863 lines shipped in one day,
  **ZERO with a caller**, while 10 existing per-turn injectors sat unused; the shared module built to end
  the recurring class was adopted by 3 of 15 tools. `2026-08-08` · `state/projects/project-system/brief.md`
  → replaced by one line in an injection that already fires. **8th recorded instance of build-with-no-caller
  in this system** (prior: `compose_reflection` · `judge.py`/`push_gate.py` — *"I built the lock and never
  built the key"* · `check_screens.py` · 4 unused shared primitives). See **THE CODE SPIRAL**,
  `system/build-rules-index.md`. **UNIVERSAL**

## §5 — The front door (pointers — one home each, zero duplication)
- **Mechanics** (exit codes · stdin parsing · deny format · registration · chmod · the two-machine **Deploy & Verify checklist**) → `system/hook-contract.md`
- **Injector arm/clear/TTL lifecycle + WHEN a skill arms its anchor** → the skill-building SOP §4
- **Is-this-hook-well-built conformance check** (the LLM-CONTEXT block audit) → `docs/skill-conformance.md`
- **The catalog of enforced rules / fitness functions** → `docs/architecture.md`
