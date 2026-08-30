---
topic: [system-architecture]
skill: architect
description: "Read ONE subject at three altitudes — what is actually broken (ground), which seam in its chain is the broken one (5,000), and whether one root cause up top is generating the mess below — including the answer that there is none (10,000). Then says what decision that changes. Use on \"/architect\", \"give me the altitudes\", \"what would a professional build\", \"architect this\", \"is this the right architecture\", \"what are we missing\", \"is there a root cause\", \"explain that\", \"what just happened\", \"I'm confused\", \"explain this technically\". A bare \"/architect\" right after any turn, with no subject, is a legitimate invocation — the subject is implicit (the last turn). DEFAULT is SURVEY — one reasoner, conversational, grounded from source, and it must say it was not a council run. The 7-lens architecture COUNCIL is an optional mode the operator invokes by hand. Propose-only: it never applies anything, and it may legally return that nothing needs changing."
shape: interactive-workflow
desk: root
status: active
version: 0.1
created_at: 2026-08-06
updated_at: 2026-08-06
---

## Intent (§0.5)

**User outcome.** the operator names one subject and gets back what a professional systems architect would build
instead — **at this system's real size**, with every claim carrying a source fetched this session. Not a
list of tidy improvements: the delta between his best thinking as a self-taught builder and what someone
who does this for a living would do. **Bar:** *"I asked what I was missing, and I got an answer I couldn't
have written myself — or an honest 'you're fine,' which I also believe."*

**Role.** The third and highest rung of Efficiency's ladder — **FIXER** (one broken thing) · **ENGINEER**
(parts that fight each other) · **ARCHITECT** (what should exist instead). It is **human-in-the-loop and
propose-only by construction**: it convenes the room, holds the frame against the room's own gravity, and
hands the operator a decision. **It never applies anything.** The judgment is genuinely the deliverable, so the
advisors run `opus` — the sanctioned exception, scoped to the routed advisors only.

**Per-turn anchor.** `/architect · step N/6 · <subject> · next → <next>`

> ⚠ **PORT NOTE (T3.6, lifehack-migration, 2026-08-20) — SURVEY MODE ONLY, verified this session.**
> The donor's own recorded deferral reason ("blocked on missing tools") does not hold up: of the six
> tools/files this skill cites, only ONE (the advisory-council engine itself) is actually invoked as a
> live dependency by SURVEY mode, and it isn't even SURVEY's — it's COUNCIL's. The rest are
> **cited as context sources to read, not imported/executed** — this skill is prose a reasoning agent
> follows, not a program with hard imports, so an absent citation degrades the read rather than
> crashing it (the skill already says as much: "if there are ZERO findings, say so in the packet in
> those words").
>
> **Checked this session, present vs absent at this destination:**
> | dependency | mode | status |
> |---|---|---|
> | `system/organism/elements/<slug>.md`, `system/organism/manual.md` (step 2a, "WHAT IT IS") | SURVEY | ⛔ **not shipped** — only a single one-idea extract ships here (`system/organism-manual-extract.md`), which says explicitly "None of that ships here." Step 2a has no per-subject element file to read at this destination. |
> | `system/tools/findings_reader.py` (step 2b, "HOW IT ACTUALLY FAILS" — Hospital's findings) | SURVEY | ⛔ **not shipped** — Hospital itself hasn't migrated here (donor-only concept). Every SURVEY run should say "no failure history available" per the skill's own instruction, not silently skip the rung. |
> | `system/tools/architecture_reason.py` (the human-ruling filter, step 2) | SURVEY | ⛔ **not shipped** — the "did the operator already rule on this" pre-check cannot run; a SURVEY here cannot detect and stop on a prior ruling. Real degradation, not a blocker. |
> | `advisory-council` (the engine, step 3) | COUNCIL | **present** (`.claude/skills/advisory-council/`) — but the specific `claudeops-architecture` cartridge/roster it needs does not exist anywhere in this repo or notes root. |
> | `system/council-framings.md` (step 3) | COUNCIL | ✅ **here** — corrected from the donor's `_ClaudeOps/councils/framings.md` (a personal-notes path there); at this destination the framing text is a repo-tracked engine file, same as `advisory-council` already reads it. Not what blocks COUNCIL mode — the cartridge/roster row above is. |
> | `system/tools/emit_recommendation.py`, `fault_proposer.py`'s threshold (steps 5-6) | COUNCIL | ⛔ **not shipped**. |
>
> **Verdict: COUNCIL mode is still blocked, but on a narrower basis than first found — its framing
> file turned out to be a citation error, not a real gap** (see the corrected row above: `advisory-council`
> reads `system/council-framings.md` here, same as it always did; the donor's `_ClaudeOps/councils/
> framings.md` path was ported over unchanged, which was wrong). What actually blocks it is the missing
> `claudeops-architecture` cartridge/roster and `emit_recommendation.py`. **SURVEY mode is portable and
> will run** — steps 1, 2c, "The read," and the Rails/Verification framing all work as written — but 2a
> and 2b's context is honestly thinner here than on the donor (no organism element files, no Hospital
> findings, no prior-ruling filter). This skill should keep saying so on every run, exactly as its own
> text already requires for a zero-findings case — the absence is a fact about the packet, not a blank
> to silently skip.

# architect

## Purpose

**One command that puts ONE subject in front of the architecture council with the system's real shape
attached, and returns exactly one of five outcomes — one of which is "nothing needs changing."**

⚠ **It is a FRONT DOOR over machinery that already exists.** `/advisory-council` is the engine, the
`claudeops-architecture` cartridge is the roster, `architecture-library.md` is the canvas, and
`emit_recommendation.py` is the writer. **This skill invents none of them.** If you find yourself building
a second council, a second writer, or a second altitude vocabulary — stop, you are off the path.

## The outcome set — a closed vocabulary; code checks membership

Every run returns **exactly one**:

| outcome | meaning |
|---|---|
| `REINVENTED-WHEEL` | this system built something that already exists as a standard, well-understood thing |
| `MISSING-PIECE` | something a professional would consider structural is simply absent |
| `OVERBUILT` | this is more machinery than the problem needs |
| **`NO-UPGRADE-FOUND`** | **I looked, and you're fine.** The NO-OUTCOME member. |
| `INCONCLUSIVE` | **I could not tell.** |

⛔ **`NO-UPGRADE-FOUND` and `INCONCLUSIVE` are DISTINCT and never collapse.** *"I looked and you're fine"*
≠ *"I could not tell."* A council that always finds something is not an architect, it is a generator.

⛔ **`unreachable · timed-out · rate-limited · malformed · empty` ALL map to `INCONCLUSIVE`, NEVER to
`NO-UPGRADE-FOUND`** (`skill-building-sop.md` LAW 1b). *"I could not look"* must never be spelled the same
way as *"I looked and it was fine."*

## Steps / Flow

### 1 · Take the subject, and refuse a sweep

the operator names ONE subject — a subsystem, a seam, a capability, or a question ("do we need X?"). If they name
several or none, **ask for one; do not pick.** Write it into the anchor and carry it every turn.

⭐ **EXCEPTION — bare invocation right after a turn.** `/architect` with NO arguments, called right after any
turn, is a legitimate and expected invocation: it means "re-explain what just happened, at the three
altitudes." The subject is **implicit** — whatever the session was just doing — not absent. **Do not refuse
it, do not demand a named subject, and do not say "this isn't a council run."** Run SURVEY mode on the
current context and answer. This does not weaken the sweep refusal above: a bare invocation still has
exactly one bounded subject (the last turn); it is only typed versus implicit.

### 2 · Build the packet — three parts, and the middle one is the point

**(a) WHAT IT IS.** The subject's own description from `system/organism/elements/<slug>.md` if one exists,
plus `system/organism/manual.md` where it explains how the part sits against its neighbours.

**(b) HOW IT ACTUALLY FAILS.** ⭐ **The half that makes the run worth doing.** Read Hospital's real findings
for this subject through `system/tools/findings_reader.py` — the union reader over the live store. **Not
how it might fail: the recorded evidence of how it has.**
⚠ **If there are ZERO findings, say so in the packet in those words.** An absent failure history is a fact
about the subject, not a blank to skip — and it changes what a competent architect would recommend.

**(c) WHAT IT COSTS.** Context pasted per run, scheduled jobs, attention. **Compute it, never estimate it.**

**⛔ THE FILTER, BEFORE THE PACKET GOES OUT.** Run the subject past `system/tools/architecture_reason.py`'s
`_strip_agent_authored()` and `human_ruling_for()` — `T20.6`'s human-decision matcher. **If the operator already
ruled on this, the run STOPS and says so.**
★ **This exists because of a real defect:** a lane once read a brief's SCRATCHPAD as a human ruling and
cited a note written eleven minutes earlier — so any session could have suppressed any recommendation by
writing itself a note. **A scratchpad is never a ruling.**

## The read

> **Take ONE subject. Read it at three altitudes. Answer a different question at each — never the same answer three sizes.**
>
> **▲ Ground — what is actually broken.** The specific things, named. Not categories. If you cannot name the file, the row, the count, you have not been to ground yet.
>
> **▲ 5,000 — the chain this sits inside.** What subsystem is it part of, what feeds it, what reads it, and **which seam is the broken one**. Say which stages are healthy — a chain where four of five stages work is a different problem from one broken throughout.
> ⭐ **Also look for a CODE↔LLM interface boundary in that chain** — code handing off TO a model, a model handing back TO code, or a chain of both (code → model generates → response returns to code). If one exists, name it and state the governing rule inline, from `records/insight/2026-08-05-the-code-llm-seam.md` (Drive): **code hands the model a bounded set of outcomes; the set must contain one member meaning NO OUTCOME WAS REACHED; code checks membership on every path in.** If the subsystem has NO model in it at runtime, **say so plainly — the seam doctrine does not bind a code-only product.** (Proven live 2026-08-07: a Hospital analysis assumed an LLM was producing unreadable output; all 12 producers were pure code, and the real failure was code-to-code — a raw `json.dump` bypassing a validator.) Checking whether a model is even present is part of this rung.
>
> **▲ 10,000 — is there ONE cause above everything below?**
> ⚖ **the operator's definition, 2026-08-05, `authority: user`:** *"5,000 is fixing stuff that IS in the system… if I had my own programmer, he would tell me that."*
> ★ **The test: if the fix is editing an existing file, it is 5,000 ft.**
>
> **Then answer the question the altitudes exist to answer: is there a root cause up top generating the mess below?** If yes, name it and say what it changes. **If no, say so plainly** — *"these are three separate ground-level bugs, there is no architecture behind them"* is a correct and valuable answer. Do not manufacture a 10,000-ft cause to fill the slot.
>
> **Close with: does this change a decision already on the table?** An altitude read that changes nothing was not worth running. Name the decision and how the read moves it.

⛔ **VERIFY FROM SOURCE BEFORE YOU ASSERT.** Every altitude claim gets grounded THIS session — a grep, a file read, a count. The strongest finding in the first real run was *"`emit_finding.py` has zero references to the self-model"* — a grep that returned nothing. **A confident architecture claim with no command behind it is the failure mode this skill exists to avoid.**

⛔ **A RUN WITHOUT A COUNCIL IS NOT A COUNCIL VERDICT — SAY SO IN THE FIRST LINE.** This is this skill's recorded DEFECT 1: on its first real run the lead skipped the council and presented its own analysis in the shape of an architect finding, and nothing objected. **Open every run by naming which mode it was.** One reasoner's read is legitimate and often correct; passing it off as a room's verdict is not.

## Modes

**`SURVEY` (DEFAULT) — one reasoner, three altitudes, grounded from source.** Cheap, fast, what you almost
always want. **Must self-label as not-a-council-run.** SURVEY is **conversational** — it answers "The read"
above and stops there. It does not have to emit into the findings store; steps 5 (the gate) and 6 (emit)
below apply to COUNCIL runs, not to a SURVEY.

**`COUNCIL` — the 7-lens advisory council on top.** the operator invokes it BY HAND when a genuine fork exists
(two viable architectures competing). ⚠ ~68,000 tokens of setup before any reasoning. Wasteful when the
answer is a grep. **At this destination: NOT AVAILABLE** — see the PORT NOTE at the top of this file;
every one of steps 3-6's own dependencies is absent here. Stay in SURVEY.

### 3 · Dispatch the council — the framing, verbatim (COUNCIL mode)

Invoke `/advisory-council` on the **`claudeops-architecture`** cartridge. It already pastes
`architecture-library.md` inline every round; **do not paste it again.**

**Load the ARCHITECT framing from `system/council-framings.md`** — the single engine-level source
(✅ here, same file `advisory-council` reads; COUNCIL mode is still blocked at this destination by the
missing cartridge/roster, not by this file — see PORT NOTE above).
⛔ **Paste it verbatim.** Never retype, paraphrase, or write a "close enough" version inline: two copies of
one decision drift, and a reworded framing is an agent's approximation standing in for the operator's ruling.

**Advisors run `opus`** — the sanctioned exception (`~/.claude/CLAUDE.md` → Subagent Model Selection §1a),
scoped to the routed advisors only. Everything else here stays at the default tier.

⛔ **Advisors SEE the system.** Blinding them was **overruled by the operator 2026-08-06**: without the shape they
propose at the wrong scale. The reader/actor split survives only for the web-fetch step.

### 4 · The citation bar — read the trace, not the claim (COUNCIL mode)

**Every finding carries an external citation verified from the FETCH TRACE**, never from a URL an advisor
typed. Web work goes through `system/tools/safe_fetch.py` / `bash system/tools/safe_search_api.sh
'<query>'`. **Read what those tools actually returned.** A URL in prose is a claim about a fetch, not a
fetch — `§V.4b`: *"if the only thing it reads is something the actor can type, it is theater."*

⚠ **A finding with no verifiable citation does not become weaker. It becomes `INCONCLUSIVE`.**

### 5 · The gate — split honestly between code and human (COUNCIL mode, before emit)

**This is the one place the skill is deliberately NOT automated,** and the reason is stated rather than
hidden. `§III.10`'s human-in-the-loop test has three legs and **the substance of a causal claim fails all
three**: a computer sees a claim was made but not whether it is true (1) · the proof arrives only if the
fix is built (2) · judging whether a cause explains its symptoms is taste (3).

**CODE CHECKS SHAPE** — mechanical, fail-closed, no judgment:
- the finding names **one cause** and **at least two symptoms**
- each symptom resolves to a **real fingerprint** in the findings store (membership — code's own job)

⚠ **The threshold already exists; do not mint a second number.**
`fault_proposer.ORGANISM_DISTINCT_KEYS = 2` — *"two distinct recurring keys is the floor at which 'these
share a cause' becomes a question worth a human's time."*

**HUMAN CHECKS SUBSTANCE** — tagged `human_in_the_loop`, **never hard-gated**: is the causal claim true?
does fixing the cause really dissolve the symptoms?
⛔ **A false gate on a judgment rule is worse than no gate** — it stops anyone looking.

### 6 · Emit — propose-only, at the ORGANISM altitude (COUNCIL mode)

Write through **`system/tools/emit_recommendation.py`**, the validated writer, which requires evidence.

**`--altitude ORGANISM`.** ⚠ **Read this before "fixing" it to `ARCHITECT`:** the human-facing rung names
are FIXER / ENGINEER / ARCHITECT; the code's vocabulary is `INSTANCE / SUBSYSTEM / ORGANISM / DECISION`.
**Two namings of one ladder — and `ORGANISM` already means exactly this rung** (`fault_proposer.py:58`:
*"several DIFFERENT faults share a shape. The model is wrong."*). Adding a fifth member would touch two
hand-copied constants and break a deliberate anti-drift selftest, to rename something that exists.
*(`§22.8` anticipated adding `ARCHITECT`; on inspection `ORGANISM` was already the thing — recorded so the
next session doesn't re-open it.)*

**Then say what it cost and what it produced, plainly.** ⛔ **If the council found nothing worth changing,
that is a RESULT** — not padded, not re-run until it produces something.

## Rails (what this skill will NEVER do)

- **NEVER applies a proposal.** No applier at any rung. `grep` for one at the close of any change here; if
  one appears, that is the defect.
- **NEVER runs unattended.** `MODEL REACH = SESSION ONLY` — `/advisory-council` is skill prose, and **skill
  prose does not exist in cron** (LAW 1b). Written here so a future scheduled path cannot silently skip the
  model step and report success.
- **NEVER sweeps.** One subject per sitting.
- **NEVER re-raises something the operator already ruled** (step 2's filter).
- **NEVER accepts a typed URL as a citation** (step 4).
- **NEVER blinds the advisors** — overruled 2026-08-06.

## Verification — how you know this works

Per `skill-building-sop.md` PART V. **Prove the failure paths, not just the happy one.**

1. `/architect` resolves from a cold window — as `/architect` **and** from prose intent.
2. ⭐ **WATCH `NO-UPGRADE-FOUND` FIRE.** Run it on a subject with nothing wrong and confirm the no-outcome
   member returns. **A check never seen to fail is not a check** (`§V.4c`).
3. **A synthetic single-symptom finding is REJECTED by the shape gate** — prove it FAILS, not that a good
   finding passes.
4. **A citation that is a typed URL with no fetch trace returns `INCONCLUSIVE`**, not a finding.
5. **`grep` finds no applier** in this skill or anything it calls.
6. **The framing text appears in exactly ONE file** — `system/council-framings.md`. Grep an *unwrapped* fragment
   and run a positive control; markdown line-wrapping already produced one false zero on this project.

## Routing eval

`references/routing-eval.md` — prompts that SHOULD fire this plus near-misses that should NOT, each run
**3+ times** (`LAW 4.3`: single samples lie). Re-run whenever the `description:` changes.

## What this deliberately does NOT do

- No applier, at any rung. the operator acts; the system proposes.
- No cron path.
- No second council, no second writer, no fifth altitude.
- No glossary maintenance — the first run's terminology output feeds the library's glossary by a separate,
  human-approved step.
