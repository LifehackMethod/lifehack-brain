---
title: "Skill Builder — PRODUCER SPEC (the behavioural contract)"
record_type: design-spec
desk: root
slug: skill-builder
topic: [skill-design]
status: draft
authority: user
created_at: 2026-08-05
updated_at: 2026-08-05
supersedes: nothing — this is the FIRST spec the skill-builder has ever had
---

> ## ⓘ WHAT THIS SPEC POINTS AT THAT IS NOT IN THIS REPOSITORY
>
> This is 2,000 lines of behavioural contract, and it earns its length by naming the exact record
> where each ruling was made. Most of those records belong to the system it came from and **do not
> ship here.** Named once, below, rather than discovered one dead link at a time.
>
> **⛔ Nothing in this block is coming.** Where a rule cites one of them, the rule's evidence is in
> the rule — the path was only ever the filing location of the original write-up.
>
> - ⛔ **Project records in the author's own notes** — `state/debt-ledger.md` · `state/projects/skill-builder/brief.md` · `state/projects/skill-builder/examples/round-opening-template.md` · `state/projects/ingest-skill/brief.md` · `state/projects/ingest-skill/brief.md.pad-archive.md`. These live under a personal notes folder, not in any repository.
> - ⛔ **Parts that did not cross** — `system/parts/capture_gate_selftest.py` · `system/parts/completeness_receipt.py` · `system/parts/precondition_gate.py` · `system/hooks/scratch_capture_gate.sh` · `shared/tools/`. Six of that library DID cross, because this skill needed them: `order_lint.py`, `phase_gate.py`, `section_present.py`, and the three the shipping lane brought. A part crosses when it has a caller.
> - ⛔ **`system/tools/conformance-lab/`** — held deliberately, and the reason is in this skill's own
>   `scripts/run_tester.sh`: measured on 2026-08-08, every subject in that lab's rule registry is
>   either a throwaway skill it builds itself or an adversarial scenario — **never an existing skill's
>   slug**, so it has no door for "test skill X" at all. It also resolves its registry to a path in the
>   author's cloud folder, hardcodes an absolute `claude` binary path and an OAuth token file, and
>   would spawn paid model calls. `run_tester.sh` reports its absence and carries on.
> - ⛔ **`.claude/skills/skill-tester/`** — ruled CUT before this migration. `TESTER: NO-TESTER-RAN` is
>   the live value this skill produces today, not a placeholder awaiting a better tool.
> - ⛔ **Donor line numbers** — `system/shipping-lane/scrub.py:110,368`. Both lane files ARE here, but
>   they were rewritten so their rules come from the reader's own identity file rather than the
>   author's name, so any line number cited against the donor's copy will not match.
>
> ⚠ **ATTRIBUTIONS READ "the owner", NOT A NAME.** Every ruling in this spec was made by one person in
> conversation, and the verbatim quotes are kept because they are the evidence for each decision. The
> name was removed; the rulings and the quotes are untouched.


# Skill Builder — PRODUCER SPEC

> **Why this file exists.** Until 2026-08-05 the skill-builder had **no spec file**. Its design lived
> scattered across another project's Story Log and scratchpad, and a session re-derived it wrongly three
> times in one evening. owner, verbatim: *"You have got to persist this knowledge into the skill builder as
> spec. It doesn't have to be this exact formatting, but you've got to save the goddamn knowledge."*
> **That is what this file is for. Anything learned about how the builder should behave lands HERE, not in
> a scratchpad.**

---

## 0a. HOW WE THINK ABOUT A SKILL — the layers, through time

> **Not a step, not a requirement, and nothing checks it.** This is the mental model the whole method rests
> on, written down so a cold session shares the picture. *(owner, 2026-08-06: "I wouldn't mind keeping it
> somewhere… it's the three-tier architecture through time.")*

**A skill is FOUR LAYERS moving through FOUR SLICES OF TIME.**

The layers (§8d): **data** — what is read and written · **business logic** — what gets worked out ·
**presentation** — what a human sees · **human-in-the-loop** — what the human does, and what is expected
back from them.

The slices: **before anyone is in the room** · **the machine's turn** · **the human's turn** · **after the
human answers.**

**Every layer exists in every slice, and the two blind spots are always the same two.** First: a skill that
never says what must already be true BEFORE the human arrives, so their turn opens on an unprepared page.
Second: a skill whose layers were each designed correctly on their own and quietly disagree with each
other — **the seams, which is where this system's real bugs have always been.**

**And a skill that loops owes four more answers:** what is the unit that repeats · what carries across from
one pass to the next · ⭐ **what must be CLEARED between passes** · and can the loop resume halfway.
⚠ **The clearing question is the one everybody skips.** Measured 2026-08-04: 33 stale files from earlier
passes accumulated in a collection directory and hard-failed a live run — **because nothing owned clearing
them, since nobody had ever asked who did.**

⇒ **BUILDER PHASE 4's four readers ARE this model, running as agents instead of as a table** — three of them
are the layers, and the chronology reader walks the time slices. That is why the grid is not also a step.

---

## 0. THE NAMING RULE — never write "phase N" bare

Two skills are always in play: the **builder** and whatever skill it is being used to build. Saying
"phase 2" without naming the skill made an entire session unreadable on 2026-08-05.

**Always write `BUILDER PHASE 2` or `<SUBJECT> PHASE 2`.** Never a bare number, in files or out loud.
Steps too: `INGEST PHASE 2 step 2.7`.

### ⛔ THE VOCABULARY IS EXACTLY TWO WORDS: **PHASES** and **STEPS**

*(owner, 2026-08-05: "Why are you saying stage in these? It should say step. We refer to things as phases,
and steps to each phase.")*

**A skill has PHASES. A phase has STEPS. That is the entire vocabulary.**

⛔ **NEVER introduce a third word** — no "stage," no "section," no "part," no "beat." A session started
saying "stage" to avoid confusing `/ingest`'s phases with the builder's phases. **That is solving the
ambiguity with a synonym, which makes it worse** — now there are three words for two things. The ambiguity
is solved by the NAMING RULE above (always say *which skill's* phase), never by inventing new nouns.

---

## 1. What this IS

> **⚖ AMENDED 2026-08-06.** The old outcome line said the human *"walks away with a filled-in spec."* the owner
> overruled it the same day: **the builder does not stop at a document — it carries the work to a built,
> tested skill, and then keeps going.** The superseded line is kept at the bottom of this section because
> the correction is the valuable part.

**Desired outcome (the whole skill).** A human who wants a skill — **one that does not exist yet, or one
that already does** — describes it in plain language and walks away with a **90–95% finished skill: three-
tier architecture, a spec worth keeping, planned, built and tested.** They never learn the template, the
grid, the tiers, or the enforcement families. The machine mines them for only what a machine cannot derive
and infers everything downstream.

*(owner, 2026-08-06: "So it goes all the way through to the end… it will hand off, let's say a 90 to 95%
completed skill that has good three tier architecture and a spec that we can work from.")*

*(owner, 2026-08-05: "how could we use the LLM intuition to mine only the most important information from
the user and infer all of the downstream information.")*

**THE CHAIN, in order — and the ORDER IS THE RULING** *(owner, 2026-08-06)*:

> **spec → CHECK THE SOP → `/autoplan` makes the plan → `/build` executes it → the tester runs → the human
> runs it live → what breaks feeds back UP into the spec → the chain fires again.**

⭐ **THE SOP IS CHECKED BEFORE THE PLAN IS MADE, NOT AFTER.** *(owner, verbatim: "before it goes into auto
plan, it goes, checks the SOP the first time to make the plan. Then the build executes the plan. And then we
test it. **There's no point in wasting the tokens to build something that's not in accordance with SOP.**")*
⇒ The SOP is a constraint on the PLAN, never a source of code. A plan that violates it is caught before a
single file is written.

<details><summary>the superseded outcome line, kept — this is what a builder read as ground truth until 2026-08-06</summary>

*"A human who wants a skill describes what they want in plain language and walks away with a filled-in spec
— without ever learning the template, the grid, the tiers, or the enforcement families."*
**Why it stopped holding:** it described the interview and stopped there, so a builder following this file
alone would hand over a document and call the job done. The spec was always meant to be the INPUT to the
rest of the chain, not the output of the skill.

</details>

**The four undecidables — the only things asked of the human:**
1. What "done" feels like (skill / phase / step)
2. What the human should be **offered** at a decision point — the optionality
3. Which of the machine's guesses is **wrong**
4. Whether the result is **any good**

Everything else — the grid, step types, evidence surfaces, gates, vocabularies — is derivable. **Anything
else asked of the human is a defect in the method.**

---

## 1d. HOW THIS SKILL GETS TRIGGERED — the human fires it (owner, 2026-08-06)

> **`skill-building-sop.md` III.3 calls the `description:` frontmatter "the #1 failure mode" — get it wrong
> and nothing downstream matters, because the skill never fires. This spec said NOTHING about triggering
> anywhere in 1,700+ lines.** A conformance check found the silence; a reader could not tell a deliberate
> choice from an oversight.

**THE HUMAN INVOKES THIS SKILL. It does not auto-trigger.** *(owner: "it just gets triggered by the human
in the loop.")* That is a choice, not a gap: this skill opens a long, expensive, multi-session build, so
**firing it is the human's act.** At the time this was written, that rested on the same mechanism as every
other side-effect skill in this system — `disable-model-invocation: true`, because a skill that writes,
spends or commits the human to hours of work must not start on a model's hunch.

> **⚠ AMENDED 2026-08-06 — mechanism retired, intent unchanged.** `disable-model-invocation` was retired
> fleet-wide the same day (owner, `authority: user` — *"I want all of my skills to be able to invoke each
> other. It's a guard that I don't feel that I need."*; doctrine at `system/sops/skill-building-sop.md:605-622`)
> and removed from this skill's frontmatter in commit `a93df23`. **The paragraph above's INTENT still
> holds** — starting `/skill-builder` is deliberately a human act, not a model hunch — but it no longer
> rests on a frontmatter flag. It now rests on the skill's own deliberate-act properties: no auto-trigger
> tuning, a `description:` written to be found only on an explicit ask, and (per the replacement doctrine)
> confirm-gates / safe-halts on the skill's own destructive steps rather than a gate on who may start it.

⇒ **The `description:` still has to be sharp** — it is what makes `/skill-builder` findable and what stops a
neighbouring skill answering in its place — but no routing-eval file and no auto-trigger tuning is owed,
because auto-triggering is deliberately off.

---

## 1c. ★★ TWO DOCUMENTS, AND THEY ARE NOT THE SAME THING (owner, 2026-08-06)

> **A swarm reader found that six save-steps write to "the brief" while three later steps read "the spec",
> and no step anywhere produced a file by that name. A session then guessed the two were one document.
> They are not.** *(owner: "The spec document and the brief are not the same thing. They are not the same
> thing at all.")*

| | **THE BRIEF** | **THE SPEC DOCUMENT** |
|---|---|---|
| what it is | the fired project's own brief, and it **holds the scratchpad** | the official record of what has been DECIDED |
| what lives there | working notes, the conversation's residue, things in flight | durable content — outcomes, phases, steps as ratified |
| how long it lasts | **ephemeral** — it is a working surface | **durable** — it is what a later session reads and builds from |
| who reads it later | this run | `/autoplan`, `/build`, the next loop, a stranger |

⛔ **BEING DURABLE IS NOT THE SAME AS BEING PRESCRIPTIVE.** *(owner, same ruling.)* The spec document holds
what was decided **and is still almost entirely changeable** — only the LOCKED LIST (§1a) is nailed down,
and even that changes when the human says so. **Durable means it survives the session; locked means it
survives a rewrite.** Confusing the two is what makes a later pass afraid to touch anything.

⇒ **The scratchpad feeds the brief; the brief's settled content is written into the spec.** Every save-step
in this file that ratifies something writes to **the spec**; working residue stays in the brief.

---

## 1a. ★★ THE LOCKED LIST — what is prescriptive, and what it takes to change it

> **the owner's ruling, 2026-08-06.** *"We'll have a list of things that are prescriptive and locked… I want
> things to be numbered… things that are locked and considered prescriptive are going to be a section
> inside of the spec document. And it's something that we could add to or change."*
>
> **The whole rest of this file is guidance carrying its reason and is EXPECTED TO CHANGE under contact.**
> That is the PRESCRIPTION BUDGET. What follows is the exception list — and it is the ONLY exception list.

**⛔ NOTHING IS UNTOUCHABLE JUST BECAUSE IT WAS DECIDED ONCE.** *(owner, 2026-08-06: "this can be a
recursive system, so we don't want it reading something and assuming that it's untouchable just because we
made that decision once.")* Every item below is changeable. What each item states is **who may change it**.

> **📎 SOURCING, 2026-08-06 — which rows are HIS, and which are a session's compilation.**
> **the owner named exactly ONE item for this mechanism: the design style (L4)** — *"we're locking the design
> style… this would need to be a specific human in the loop approval to change the design style."* He also
> ruled that the LIST ITSELF should exist, be numbered, live in this spec, and be changeable only by him.
> **L1, L2, L3, L5 and L6 are real prior rulings that a SESSION promoted into this tier — he did not put
> them here.** The line calling this *"the ONLY exception list"* is the session's too.
> ⇒ **Ratify or strike each row.** Caught by an adversarial fidelity check the same day it was written.
> ⚠ **This table also overrides the project brief's FRAME**, which says *"only outcomes get prescriptive
> language."* That override is legitimate — the owner built this mechanism deliberately — **but the FRAME has
> not been amended, so two files currently disagree.** Only the human may amend a FRAME. **OPEN.**

| # | LOCKED | Tier | Who may change it |
|---|---|---|---|
| **L1** | **The desired outcome** (§1) — the chain, both doors, the 90–95% finished skill. | **HARD** | The human, explicitly. A session may never amend it. |
| **L2** | **The order of the chain** (§1) — spec → SOP check → plan → build → test → live run → back to spec. | **HARD** | The human, explicitly. |
| **L3** | **The naming rule** (§0) — PHASES and STEPS, never a third word, never a bare "phase N". | **HARD** | The human, explicitly. |
| **L4** | **The visual/design style** (§8, §8a, §8b, §8c) — the four approved screens. | **MOSTLY LOCKED** | **A specific human-in-the-loop approval, per change.** ⛔ **The system must never change the design style on its own.** *(owner: "we don't want the system to go in and start changing the design style of the skill.")* |
| **L5** | **The four undecidables** (§1) — the only things asked of the human. | **HARD** | The human, explicitly. |
| **L6** | **The machinery never surfaces** (§8) — no grid, no tiers, no step-type jargon, not the builder's own phase numbers. | **HARD** | The human, explicitly. |
| **L7** | **BUILDER PHASE 1's step list** (§3) — the eight-line ladder, the fork structure, and its three rulings. **Ruled locked by the owner 2026-08-06** *("lock this into the spec document as locked for phase one")*, after three drafts in one sitting. | **HARD** | The human, explicitly. |
| **L8** | **The three-tier markers on every step line** (§8d) — data · business logic · presentation, in that order. | **MOSTLY LOCKED** | A specific human-in-the-loop change. |
| **L9** | **⭐ THE STAKEHOLDER IS A TECH-FRIGHTENED BEGINNER, AND THE SKILL TEACHES THEM** — it does not merely inform. Every phase, phase 1 included. | **MOSTLY LOCKED** | A specific human-in-the-loop change. |
| **L10** | **⭐ ORIENT THE READER ON EVERY TURN** — where they are, how many turns remain, how close the finished thing is. Not once a phase; every turn. | **MOSTLY LOCKED** | A specific human-in-the-loop change. |
| **L11** | **The process is INTERROGATIVE** — it brainstorms with the human and never solves for them. | **MOSTLY LOCKED** | A specific human-in-the-loop change. |
| **L12** | **⭐ EVERYTHING THE MACHINE WRITES IS A BEST GUESS, AND SAYS SO ON SCREEN** — never presented as settled. | **MOSTLY LOCKED** | A specific human-in-the-loop change. |
| **L13** | **ONLY DESIRED OUTCOMES ARE WRITTEN AS DEFINITIVE** — the skill's, and each phase's. Everything else (steps, methods, wording) is explicitly provisional. **And even the outcomes are changeable by the human.** | **MOSTLY LOCKED** | A specific human-in-the-loop change. |
| **L14** | **BUILDER PHASE 2's step list** (§4) — ~~nine steps~~ **ten steps (2.0–2.9) — corrected 2026-08-08 [F3.6]: counted directly against both this spec's own locked list and `phases/2-phases.md`, both run 2.0 through 2.9. A 2026-08-06 backfill added step 2.0 (fetching the phase's own prompt, §8g) after this row was first written, and the row's count was never updated to match.** The A/B fork at 2.6 with both destinations named. **Ruled locked by the owner 2026-08-06** *("This is fully approved. I love it.")* | **HARD** | The human, explicitly. |
| **L15** | **Every turn ends on the A/B fork** (§8f) — *keep refining* or *lock it and move on* — and any step offering it names BOTH destinations by number. | **MOSTLY LOCKED** | A specific human-in-the-loop change. |
| **L16** | **A desired outcome shown to a human is written in the FUTURE TENSE** (§8e) — a promise about what is coming, never phrased as though it already happened. Back-propagated to every phase, 2026-08-06. | **MOSTLY LOCKED** | A specific human-in-the-loop change. ⚠ **Cited at :1542 since 2026-08-06 but never registered in this table until now — added here 2026-08-08 [F3.6].** |

**How to change an item:** the human says so, in session, and the change is written here with its date. A
session that wants to change a locked item **surfaces the conflict and stops** — §9b rule 1.
**How to ADD an item:** same. This list grows by ruling, never by a session deciding something felt important.

⚠ **An L4 change is NOT a style preference a session can absorb.** Eight iterations in one sitting produced
those screens. A session that "improves" them is undoing measured work — get the approval or leave them.

---

## 1b. ★ THE TWO DOORS — the builder is not only for skills that do not exist yet

> **owner, 2026-08-06:** *"The skill builder shouldn't just be for building from scratch. You should be able
> to point the skill builder at an already written skill. And it will go through and help us to analyze the
> skill, its weaknesses, its strengths. It will create a spec from that skill… **so this is not just for
> building from scratch, it's for modifying skills.**"*

**DOOR ONE — a skill that does not exist yet.** The full interview: BUILDER PHASE 1 asks for the outcome
cold, because nothing is on disk to mine.

**DOOR TWO — a skill that already exists.** The same phases, entered with most answers already available.

> **📎 SOURCING, 2026-08-06 — read this before treating the five steps below as settled.** the owner ruled that
> **DOOR TWO EXISTS** *("this is not just for building from scratch, it's for modifying skills")* and, when
> asked to rule on it in a numbered list, answered *"Number six. Okay."* **The five-step procedure below is
> a SESSION'S DRAFT** built from that framing plus standing doctrine — **he has not seen or ruled on the
> steps.** Caught by an adversarial fidelity check the same day. Treat as a strong starting point, not a
> decision; it is BUILDER PHASE 3 work and belongs to the human to correct.

1. **The builder reads the skill first** — its `SKILL.md`, its phase files, its code, its spec if it has
   one, and its project history. This is §9a's *mine, don't ask cold* rule with far more to mine.
2. **It writes the spec that skill ALREADY IMPLIES** — derived from what is shipped, not from the human.
3. **It reports strengths, weaknesses, and — the sharpest one — CLAIMS WITH NO ENFORCEMENT BEHIND THEM.**
   The two richest seams are `skill-building-sop.md` §V.4d (a claim written next to a thing is read as the
   thing) and §V.9 (a validator that exists and nothing calls it).
4. **Then the normal interview runs ONLY on the gaps** — the human is asked only what the files cannot
   answer. That is the whole speed advantage of this door.
5. ## ⚖ RULED BY THE OWNER 2026-08-08 — **IT RUNS THE WHOLE CHAIN. IT DOES NOT REJOIN AT THE SWARM.**
   > **His words:** *"Basically what happened is I didn't build a skill properly because I didn't build it
   > with my skill builder. So it's going to put it back through a rigorous pipeline… The critique is not
   > really an important part. Really, we're going to put it through a more rigorous pipeline that makes
   > sure that it contains all the parts that it needs to function correctly."*
   >
   > ⇒ **DOOR TWO IS A REMEDIAL PIPELINE, NOT A REVIEWER.** A skill built without the builder is missing
   > parts; the chain's job is to find which and put them in. The critique output (step 3 above) is a
   > BY-PRODUCT, never the deliverable.
   >
   > ⭐ **POSTURE, and it is the whole difference from door one:** the chain runs in full, but at every
   > stage **what the skill ALREADY HAS is the draft**, and the question is *"what is missing here?"* —
   > never *"what should this be?"* Blank-page work on a skill that already exists is the failure mode.
   >
   > **This RESOLVES the fork that sat unruled from 2026-08-06 to 2026-08-08** and that two sessions
   > declined to pick. `phases/1-outcome.md` — which runs the whole chain — was ALREADY CORRECT and is
   > unchanged. **This line was the wrong one**, and it was a session's draft the owner had never seen (§1b's
   > five steps are labelled as such), never a ruling. ⛔ Do not re-introduce a swarm-rejoin shortcut.
   ~~It rejoins the chain AT BUILDER PHASE 4 — the tension swarm — and runs from there.~~
   **It rejoins at `1.4` and runs the FULL chain from there:** the rest of BUILDER PHASE 1 -> phases ->
   steps -> swarm -> SOP check -> `/autoplan` -> `/build` -> tester -> live run.
   **AMENDED 2026-08-06.** This step used to send a derived spec straight to the SOP check and the build,
   **skipping the swarm entirely** — while §2 states, as a HARD rule with a dated cost, *"DO NOT BUILD
   BEFORE THE SWARM."* A spec DERIVED from an existing skill needs the readers MORE than one the human
   dictated, because every line of it is the machine's inference about someone else's intent.

⛔ **A derived spec is a GUESS until the human rules on it.** Reading a skill tells you what it DOES; only
the human can say what it was SUPPOSED to do. Every derived outcome is presented as a guess, per §3's rule.

---

## 2. THE SIX BUILDER PHASES

> **⚖ WAS FIVE UNTIL 2026-08-06.** the owner added the sixth — the live run that feeds back into the spec —
> and rewrote what phase 5 does. The old phase-5 row read *"Reads the skills SOP + the library of parts"*
> and named none of the chain.

| | BUILDER PHASE | What happens |
|---|---|---|
| 1 | **Define the desired outcome** | The human states what the whole skill is for. Q&A, as many rounds as needed. |
| 2 | **Propose the phases + each phase's desired outcome** | The **builder suggests** them. The human corrects. |
| 3 | **Decide the steps** | Each step gets its own outcome, each tagged LLM or HUMAN. |
| 4 | **The tension swarm** | Sub-agents per architectural tier hunt TENSIONS across the whole spec. |
| 5 | **Build it — the CHAIN** | Check the SOP → `/autoplan` (pointed at the SOP by an injected prompt) → `/build` → the tester. |
| 6 | **The live run — and the loop back** | The human runs the finished skill for real, in a fresh session. What breaks feeds back UP into the spec, and the chain fires again. |

**The cheap-draft principle — the reason phase 4 exists at all** *(owner)*: *"The first spec we make, we
know it's not going to be perfect. Instead of trying to get the human to catch all the things by showing
them every single phase, we just use the first three phases to GUESS at it. Then phase four goes and really
surfaces all the tensions and really tries to shake the tree."*

⇒ **BUILDER PHASES 1–3 are a deliberate first guess, not a careful build.** The human's attention is spent
ONCE, on a hard critique of a COMPLETE artifact — not continuously, on fragments. **This inverts the
intuitive design** (review each phase as you go) and it is better, because a cross-phase tension is
invisible to anyone reading one phase.

⛔ **DO NOT BUILD BEFORE THE SWARM.** On 2026-08-05 a session took `INGEST PHASE 2`'s spec alone and built
its code while `INGEST PHASE 3` was still being written and `INGEST PHASE 4` had no spec. That is working
**vertically, phase-by-phase** — the exact thing this method forbids — and it cost a full window.

⛔ **WORK HORIZONTALLY BY ALTITUDE, NEVER VERTICALLY.** Outcome for everything → phases for everything →
steps for everything. Proven by getting it wrong: a session specced `INGEST PHASE 1` top-to-bottom then
`INGEST PHASE 2` top-to-bottom, and the owner reported *"I'm losing perspective"* — he had never seen all the
phases side by side.

---

## 3. BUILDER PHASE 1 — DEFINE THE DESIRED OUTCOME

**PHASE OUTCOME:** the whole skill's desired outcome exists **in the human's own words**, as a felt result,
and the builder understands it well enough to propose a phase breakdown.

**How it runs.** A conversation. The human says what they want the skill to do. The builder asks, listens,
plays it back, asks again — **as many rounds as it takes.** There is no fixed round count.

**Rules:**
- The outcome is **human-authored, human alone.** The builder may offer a first phrasing **but must flag it
  explicitly as a guess and ask for the human's own words back.** ⛔ Never let a drafted phrasing quietly
  become the record.
- Check it reads as a **felt result** — *"I know this landed when ___"* — not a mechanism — *"it runs a
  script that ___."*
- ⛔ **Do NOT open by showing the human the spec template.** *(owner: "I actually don't want you to start by
  showing me the full spec template.")* Ask for the outcome in their words FIRST.
- **Mine before you ask.** Pull everything already on disk that bears on this skill — prior journal
  entries, records, canon, and the shipped files if code exists — *before* opening any question.

### ✅ THE LOCKED STEP LIST — BUILDER PHASE 1 (owner, 2026-08-06: *"lock this into the spec document as locked for phase one"*)

> **Produced by running BUILDER PHASE 3 on the builder itself, 2026-08-06, with the owner in the chair.**
> Three drafts: the first put the disk-pull first (*"how could the computer pull everything on disk about
> the skill — you don't even know what the fuck the skill is"*), the second split the fork question from the
> ask, the third is this. **Reproduce the step numbering and the fork structure; the wording is the record.**

> **⚖ BACKFILLED 2026-08-06, on the owner's approval,** after BUILDER PHASE 3's own drafting produced rules this
> list predates: the four layers (§8d), the `→ LLM / → CODE` seam notation, the turn-closing fork (L15,
> §8f), the prompt library (§8g), and L13 (only outcomes are definitive). **Renumbered — the old 1.1–1.6
> became 1.1–1.7 with a new 1.0 at the front.** ⛔ Nothing was removed; the fork at the old 1.1 and the
> brief-at-the-end rule at the old 1.6 are intact.

```
├ 🤖💾 1.0  The computer fetches THIS phase's own prompt from the prompt library and injects it, so the
            phase runs scoped to itself and the model never sees where the work is going (§8g).
├ 🙋🤝 1.1  ⑂ THE FORK.  `→ CODE (A|B)`
            The human answers the opening screen, which asks two things at once: are we building a NEW
            skill, or fixing one that ALREADY EXISTS — and then, depending on that answer, either "what do
            you want this skill to do for you" (with the reframings under it), or "point me at the skill you
            want to improve." One screen, because the second question is meaningless without the first.
            · A = a NEW skill → SKIP TO 1.4.
            · B = it ALREADY EXISTS → CONTINUE TO 1.2.
            ⭐ HALF-BUILT AND SHIPPED ARE THE SAME ANSWER. Both mean "something is on disk, go read it";
              HOW MUCH exists is something the computer discovers by looking, never a question the human is
              asked. *(Ruled 2026-08-06 after a session proposed a third branch and the owner rejected it.)*
            ⛔ An answer that is neither A nor B breaks loudly and re-asks. It is never guessed at.

  ↳ if the skill ALREADY EXISTS
├ 🤖💾 1.2  The computer pulls everything on disk about that skill — its files, its code, its spec if it has
            one, its project history — so the human is never asked for what the system already knows.
├ 🤖⚙️ 1.3  The computer drafts the desired outcome that skill ALREADY IMPLIES from what it read, so the
            human corrects a draft instead of composing from a blank page.

  ↳ both paths
├ 🔁 1.4   The computer brainstorms WITH the human. For a new skill it asks what they want it to do and
            why. For an existing one it asks what went wrong — what did you want it to do that it wasn't
            doing — debugging in plain language. It TEACHES as it goes (L9) and says where they are (L10).
            ⛔ It never invokes the `brainstorming` skill; it just brainstorms. EVERY ROUND ENDS WITH THE
            TWO OPTIONS: A — keep going. B — I've said enough, move on.
├ 🙋🤝 1.5  ⑂ THE FORK.  `→ CODE (A|B)`  · A → back to 1.4, the loop continues.  · B → CONTINUE TO 1.6.
            ⛔ Neither answer breaks loudly and re-asks. The human always knows the door is there.
├ 🤖⚙️ 1.6  The computer works out from the conversation how big this thing actually is: how many steps, how
            much the human is involved, how much information has to be gathered and processed.
├ 🤖💾 1.7  At the end of the phase — not before — the computer creates the project brief, plus a plan if
            the work warrants one, and FILLS IN AS MUCH OF THE BRIEF AS IT CAN from everything phase 1
            produced, writing the rest into that brief's scratchpad. ⭐ Every field the machine filled is
            MARKED AS THE MACHINE'S BEST GUESS, never as settled — it is guessing at a human's intent and
            must say so. ⭐ AND ONLY THE DESIRED OUTCOME IS WRITTEN AS DEFINITIVE (L13); everything else it
            drafts — steps, methods, wording — is recorded as version one and expected to change.
            **The brief IS the scratchpad**; there is no second place. A one-step skill gets neither brief
            nor plan. Waiting until the end means someone who walks away mid-conversation leaves no orphan.
└ ✅ Done when the human's own words are on the page as a felt result, the computer can say how it would
     break the work into phases, and — if the skill is big enough to warrant it — a brief exists holding
     everything gathered, with every machine-filled field marked as a guess.
```

**Three rulings inside that list, each earned in the sitting that produced it:**
- ⛔ **NOTHING IS PULLED, READ OR ASKED BEFORE 1.1.** The fork question comes first because the two paths
  need completely different first moves, and because there is nothing on disk to mine for a skill that does
  not exist yet.
- ⛔ **THERE IS NO SEPARATE SCRATCHPAD — THE BRIEF IS THE SCRATCHPAD.** *(owner: "there is no scratch pad.
  The brief is the scratch pad. There's a scratch pad in each project… you're doing two things at once.")*
  A draft that created both was doing the thing that lost `/ingest`'s world-model file: two homes for one
  artifact.
- ⛔ **PHASE 1 DOES NOT PROPOSE THE PHASES.** the owner raised it, then reversed himself in the same breath:
  *"the phases can be the second step… the next step is the phases."* Phase 1 scopes HOW BIG (1.5); BUILDER
  PHASE 2 proposes the list.

⭐ **AND A SHARPENING OF THE PHASE TEST, from the same sitting — carry it into BUILDER PHASE 2:** *"The
computer does something, then the human responds — that's a phase. Looping and ideating on one thing isn't a
new phase."* ⇒ **If the human's next turn is THE SAME TURN AGAIN, BETTER, it is a LOOP, not a phase.** This
tightens "a phase is a unit of human attention" into a test that can actually be applied while proposing.

**DONE WHEN:** the human's own words are on the page as a felt result, the builder can state how it would
break the work into phases, and — where the work warrants it — the brief exists with every machine-filled
field marked as a guess.

---

## 4. BUILDER PHASE 2 — PROPOSE THE PHASES + EACH PHASE'S DESIRED OUTCOME

> **★ THIS SECTION IS THE ONE THAT KEPT GETTING LOST. Written from the owner's own description, 2026-08-05.**

**PHASE OUTCOME:** the human has seen a proposed breakdown of their skill into phases, seen how those
phases add up to the outcome they gave in BUILDER PHASE 1, seen a suggested "done" statement for every
single phase, and corrected whatever was wrong.

### ⭐ THE BUILDER SUGGESTS. THE HUMAN CORRECTS. THIS IS THE WHOLE SHAPE.

*(owner, verbatim, 2026-08-05: "in phase one you're telling me what it is — it SUGGESTS what they are.
So: 'I think you want four phases, and each phase is going to be…' and then, how does that get me to the
desired outcome? And then we do a Q&A where **it guesses the desired outcome for each phase** — here's my
suggested desired outcome, second phase suggested desired outcome — and then there would be questions at
the end.")*

⛔ **DO NOT ASK THE HUMAN TO AUTHOR THE PHASE OUTCOMES ONE AT A TIME.** A session did exactly that on
2026-08-05 and it was wrong. The builder **drafts all of them and presents them together**; the human rules
by exception. Asking someone to compose four "done" statements from nothing is the cognitive load this
whole method exists to remove.

*(This refines the earlier `[SL-3]` shaping — "the human gives the PHASE outcome, the LLM drafts the STEP
outcomes." the owner's 2026-08-05 description moves the phase outcome to propose-and-correct as well. The
human still OWNS it; they just don't compose it from blank.)*

### What BUILDER PHASE 2 puts on screen, in this order

1. **The proposed phase list.** Numbered, plain language, one line each. *"I think you want four phases."*
2. **How those phases get you to the desired outcome.** An explicit walk from the phase list back to what
   the human said in BUILDER PHASE 1. **This is not decoration** — it is the argument that the breakdown is
   correct, and it is the thing the human is really ruling on.
3. **A suggested desired outcome for EVERY phase.** *"Here's my suggested desired outcome for phase one.
   Here's my suggested desired outcome for phase two."* All of them, together, so the human sees the whole
   shape at once. Each stated as a felt result.
4. **Then the questions, at the end.** Few, numbered, each carrying the builder's best guess.

### The phase test — apply it while proposing

**A PHASE IS A UNIT OF HUMAN ATTENTION.** *(owner, `authority: user`: "If phase 3 is machine only then it's
a STEP, not a phase. Phases by definition have a HITL element.")* Machine-only work is a **step inside the
phase it feeds**, never a phase of its own.

**Why it is the right unit:** phases are what you count when you ask *"how many times must I sit down."* A
machine-only "phase" inflates that count with sittings the human never attends. **Proven immediately:
applying it dropped `/ingest` from 7 phases to 4.**

### ✅ THE LOCKED STEP LIST — BUILDER PHASE 2 (owner, 2026-08-06: *"This is fully approved. I love it."*)

> **Produced by running BUILDER PHASE 3 on the builder itself, 2026-08-06, over three drafts.** The
> correction that mattered: the A/B question originally sat AFTER the human had already corrected the board,
> which made it impossible to simply approve the first draft. It now rides at the bottom of **every** screen,
> including the first.

> **⚖ BACKFILLED 2026-08-06:** added 2.0 (the phase's own prompt, §8g) and the `→ CODE (A|B)` seam notation
> plus the 🤝 layer marker on the human's fork at 2.6. Nothing else moved.

```
├ 🤖💾 2.0  The computer fetches THIS phase's own prompt from the prompt library and injects it, so the
            phase runs scoped to itself and the model never sees where the work is going (§8g).
├ 🤖💾 2.1  The computer re-reads the brief and everything phase 1 gathered, so that it proposes from the
            written record rather than from whatever it happens to remember of the conversation.
├ 🤖⚙️ 2.2  The computer drafts the phase list, applying one test to every candidate: A PHASE IS ONE
            DISTINCT DESIRED OUTCOME. Many exchanges between the computer and the human can live inside a
            single phase, because refining one idea takes several passes. But when a stretch of work is
            chasing a DIFFERENT outcome, that stretch is a new phase — and when the computer counts roughly
            three genuinely distinct human decisions inside one phase, that phase should almost certainly
            be split into two phases.
├ 🤖⚙️ 2.3  The computer drafts a suggested "done" for EVERY phase, all of them in one pass, so that the
            human never has to compose a finish line from a blank page.
├ 🤖⚙️ 2.4  The computer writes the argument for the breakdown: how these phases, in this order, add up to
            the outcome the human gave in phase 1. The argument is the thing the human is actually ruling
            on; the list alone is not.
├ 🤖🖥 2.5  The computer shows the whole thing on one screen, in one order — the phase list, then the
            argument, then every phase's suggested "done" — and it TEACHES WHILE IT SHOWS: what a phase is,
            why the outcome has to be settled before any step is written, and why the human is being asked
            to do this at all (because once the phases exist, the computer can reach into what it already
            knows and fill in the rest, so the human never has to write a specification themselves). Every
            line is labelled a best guess and the invitation to edit is said out loud.
            THE SCREEN ENDS WITH TWO OPTIONS: A — keep refining this. B — lock it and move to the next phase.
├ 🙋🤝 2.6  ⑂ THE FORK.  `→ CODE (A|B)` — this answer gates the phase, so it must be one of the two, and an
            answer that is neither breaks loudly and re-asks. The human answers A or B.
            · B → the human is accepting the board as it stands → SKIP TO 2.9.
            · A → the human says what is wrong (reorder, merge, split, rename, rewrite a "done", or name
                  where the argument does not hold) → CONTINUE TO 2.7.
├ 🤖⚙️ 2.7  The computer takes those corrections and re-drafts the board: a new phase list, new outcomes
            where they changed, and a re-written argument, because a changed list makes the old argument
            false.
├ 🔁 2.8   The computer shows the new version on the same screen, ending with the same two options, and
            this cycle repeats for as long as the human keeps choosing A. THE PHASE CANNOT CLOSE WHILE A
            CORRECTION IS OUTSTANDING.
├ 🤖💾 2.9  Only after the human chooses B, the computer writes the ratified phase list into THE SPEC
            DOCUMENT — the durable one — and the working notes into the brief.
            ONLY THE DESIRED OUTCOMES ARE WRITTEN AS DEFINITIVE — the steps, the methods and the wording are
            recorded as provisional, because this is version one of something that will loop. The computer
            also records, for each phase, whether its "done" is the human's own words or a machine draft the
            human accepted.
└ ✅ Done when every phase carries a "done" the human has accepted or rewritten, the human has seen all of
     them side by side, and the record says which ones are theirs.
```

⭐ **2.6 IS A FORK AND THE SPEC SAYS SO EXPLICITLY** *(owner, 2026-08-06: "2.6 is kind of like a fork —
if they answer B then really they would skip to 2.9. I just want this to be very clear when we're building
the skill for the flow.")* **A branch that lives only in a reader's head is a branch the build will get
wrong.** Any step offering the A/B fork names both destinations by number.

**DONE WHEN:** the phase list is ratified AND every phase carries a desired outcome the human has either
accepted or rewritten. ⛔ **A builder-drafted outcome the human has never seen does NOT count** — it is a
guess wearing a locked outcome's clothes. Track which is which.

---

## 5. BUILDER PHASE 3 — DECIDE THE STEPS

**PHASE OUTCOME:** every phase has a step list, each step carries its own desired outcome, and each step is
tagged **LLM** or **HUMAN**.

- The builder proposes the steps using the SOP library and the parts library; the human corrects.
- **Each step gets its own desired outcome.**
- **Each step is tagged LLM or HUMAN.** Steps interleave: *"the LLM does steps 1, 2, 3 → the human decides
  X → the LLM does step 4 → the human does step 5."*
- ⛔ **Never start step work before that phase's desired outcome is locked.** Steps are DERIVED from the
  outcome. Draft them first and you are inventing steps and working backwards to justify them.

### 📝 THE STEP LIST — BUILDER PHASE 3 · **PROVISIONAL BEST THINKING, 2026-08-06** (not yet locked)

> **owner, 2026-08-06:** *"Yes, this is awesome… push it to the spec document as our provisional best
> thinking."* ⇒ **This is NOT on the LOCKED LIST (§1a).** It is the current best draft and is expected to
> change — which is exactly what L13 says about everything that is not a desired outcome.

**WHAT THIS PHASE IS REALLY DOING — the framing the human is given, in their own terms.** Every skill this
system builds runs on four layers: it fetches or stores **data**, it **works things out**, it **shows**
something to a person, and the **person answers**. This phase reverse-engineers the human's phases into
steps that walk those four in order — often several of each in sequence, because processing usually happens
in stages before anything is worth showing. ⭐ **The human is never asked to know any of that.** The computer
conforms the steps to the architecture; the human only ever rules on whether the steps reach what they said
they wanted. *(owner: "this step is really, without bothering the human-in-the-loop to understand three-tier
architecture, making sure that all the steps conform to it.")*

```
├ 🤖💾 3.0   The computer fetches THIS phase's own prompt from the prompt library and injects it, so the
             phase runs scoped to itself and the model never sees where the work is going (§8g).
├ 🤖💾 3.1   The computer re-reads the ratified phase list and every phase's "done" from the brief, because
             steps are derived from those outcomes and from nothing else.
├ 🤖⚙️ 3.2   The computer takes ONE PHASE AT A TIME and drafts its steps by walking the four layers in
             order — what has to be fetched or already known, what has to be worked out and in what
             sequence, what gets shown, and what the human must decide — reaching into the skills SOP and
             the library of parts for shapes that already exist rather than inventing new ones. SEVERAL
             STEPS OF THE SAME LAYER IN A ROW IS NORMAL: two rounds of processing before anything is shown
             is a sequence, not a mistake.
├ 🤖💾 3.2b  The FIRST step the computer drafts for every phase is always the same one: the prompt for that
             phase is fetched from the prompt library and injected, so that each phase runs on a fresh
             prompt scoped to itself and the model never sees where the work is going. (What that prompt
             SAYS is not decided here — §8g.)
├ 🤖⚙️ 3.3   The computer gives every step its own purpose, folded into the sentence as a "so that…" clause,
             because a step whose purpose cannot be said in the same breath is usually two steps or none.
├ 🤖⚙️ 3.4   The computer marks every step with who acts — computer, human, or loop — and which layer it
             touches. A STEP NEEDING TWO LAYER MARKERS IS DOING TWO JOBS, and the computer splits it before
             the human ever sees it.
├ 🤖⚙️ 3.5   For every human step, the computer marks WHO RECEIVES THE ANSWER: `→ LLM (open)` when the human
             is thinking out loud and anything they say is usable, or `→ CODE (A|B)` when their answer is
             read by code that gates something. EVERY `→ CODE` STEP ALSO GETS ITS NAMED SET OF VALID ANSWERS
             AND A FAILURE MODE — what happens when the human says something outside the set. It must break
             loudly and re-ask, never guess which one they meant.
├ 🤖🖥 3.6   The computer shows one phase's steps on screen, led by that phase's number and its "done"
             restated in full, so the human answers "do these steps get me to THAT?" rather than "do these
             look alright?" It teaches as it shows, marks every line a best guess, says that corrections
             flow backward if a phase's purpose changes, and explains that it paces one phase per round
             because twenty steps at once cannot be read.
             THE SCREEN ENDS WITH: A — keep refining this phase's steps. B — lock them and move to the next.
├ 🙋🤝 3.7   ⑂ THE FORK. `→ CODE (A|B)` — this answer gates the phase, so it must be one of the two.
             · B → the human accepts these steps → SKIP TO 3.10.
             · A → the human says what is wrong (a step missing, one that does not belong, one in the wrong
                   order, or one whose purpose is not what they meant) → CONTINUE TO 3.8.
├ 🤖⚙️ 3.8   The computer re-drafts that phase's steps from the corrections, and IF A CORRECTION CHANGED
             WHAT THE PHASE IS FOR, it says so out loud and reopens that phase's "done" back in BUILDER
             PHASE 2 rather than fitting steps to an outcome that no longer describes the work.
├ 🔁 3.9    The computer shows the new version on the same screen, ending with the same two options, and
             this repeats for as long as the human keeps choosing A.
├ 🤖💾 3.10  The computer writes that phase's ratified steps into THE SPEC DOCUMENT as PROVISIONAL, and
             the working notes into the brief — only the
             desired outcomes stay definitive — and records which steps are the human's own and which are
             machine drafts they accepted.
├ 🔁 3.11   The computer moves to the next phase and runs 3.2 through 3.10 again, saying each time how many
             phases remain, until every phase has a step list.
└ ✅ Done when every phase has a step list the human has accepted or corrected, every step carries its
     purpose, its actor and its layer, every human step names whether its answer goes to the LLM or to code,
     and the record says which steps are the human's.
```

**DONE WHEN:** every phase has a step list the human accepted or corrected, every step carries its purpose,
actor and layer, and every human step declares `→ LLM` or `→ CODE`.

---

## 6. BUILDER PHASE 4 — THE TENSION SWARM

**PHASE OUTCOME:** the human is handed every tension in the complete spec, each with a recommended
resolution, and rules by exception.

Sub-agents, one per architectural tier, each reading **the whole proposed spec** through one lens:

- **PRESENTATION** — *"how are we representing this information to the stakeholder, which we're pretending
  is a boomer with not a lot of technical experience? How are we teaching them, supporting them through
  each step?"*
- **BUSINESS LOGIC** — *"how are we integrating code and LLM knowledge, and what are the SEAMS between
  them? Are we abiding by the SOP for integrating LLM and coding?"*
- **DATA** — *"are we persisting knowledge to a scratchpad correctly? Is all the knowledge being persisted
  to the correct place at each moment?"*
- **PLUS ONE CHRONOLOGY AGENT** — *"not a subagent for each of the four chronological slices, but ONE
  subagent responsible for ordering — keeping track of what happens at each chronological step."*

⭐ **THE POSTURE IS THE POINT:** *"it's not making a decision, it's actually looking for TENSIONS."*
**A critic, never an author.**

**It returns tensions AND suggestions** — *"it would run the swarm and then bring back to the human the
tensions it found, and then suggestions based on its best knowledge."* Not a bare list of problems.

**Run the swarm over the WHOLE spec, ONCE.**

### ⚖ RULED 2026-08-05 BY THE FIRST REAL RUN — the mechanics, settled with evidence

**All four readers run BLIND from each other, in PARALLEL, in ONE pass — then CHRONOLOGY gets a cheap
SECOND look with the other three's findings in hand.** Not a re-run: it inherits their inventories and
sweeps for what it structurally could not reach alone.

**The evidence, unprompted, from the chronology reader itself:** *"Running blind cost me some
completeness, not correctness."* Its ordering findings were self-contained and unaffected by not seeing
the others — but it found a missing-schema-field tension by grepping the schema **itself**, and said a
DATA reader who had already built a field inventory *"would have handed it that directly, and I can't
rule out 1-2 more of that same shape."*

**Also settled by that run:**
- **They read the SPEC *and* the CODE.** The most valuable findings were spec-versus-reality.
- **The bar: only surface a tension where two parts would produce DIFFERENT WORK**, and say plainly when
  nothing clears it. **Measured: 13 surfaced, 13 rejected — exactly half.** Without that bar, four readers
  over a long spec bury the real finding under twenty trivial ones.
- **Sonnet, read-only, UNNAMED.** A named agent's final report is discarded (249 named spawns → 0
  payloads; 1,714 unnamed → 1,714).
- **Advisory, never blocking.** The human always overrides.
- ⚠ **A READER CAN BE CONFIDENTLY WRONG.** One quoted a stale docstring to claim a field could never
  render, when it had been added and demoed that same evening. **Verify every finding against the source
  before acting on it.**

**Measured yield, first outing:** 12 unique findings on a spec its author would have sworn was complete —
**seven of them drift that author had created hours earlier in the same window.**

### ✅ THE LOCKED STEP LIST — BUILDER PHASE 4 (owner, 2026-08-06: *"let's lock this"*)

```
├ 🤖💾 4.0  The computer fetches THIS phase's own prompt from the prompt library and injects it (§8g).
├ 🤖💾 4.1  The computer assembles the COMPLETE spec — every phase, every step, the outcomes, and the
            skill's own files if any exist — because a reader given fragments finds fragment-sized problems.
├ 🤖⚙️ 4.2  The computer sends out four readers AT ONCE, BLIND to each other, each with one lens and no
            authority to decide anything. Their charges are specified in §6a.
├ 🤖⚙️ 4.3  The readers read the SPEC and the CODE, because the most valuable findings are the ones where
            the two disagree.
├ 🤖⚙️ 4.4  After the first three report, the CHRONOLOGY reader gets a second, cheap look with their
            findings in hand — not a re-run, but a sweep for the ordering problems it could not reach blind.
├ 🤖⚙️ 4.5  The computer RANKS every finding rather than discarding any of it (owner, 2026-08-06). The ones
            TWO OR MORE READERS FOUND go at the top, then the single-reader findings that would change real
            work, then the rest. ⛔ NOTHING IS THROWN AWAY: the tokens are already spent, the main session
            reads them all, and a finding one reader saw alone can still be the real one.
            *(This replaces a filter that DISCARDED the low-ranked findings — on 2026-08-06 it dropped 25 of
            42 before the human saw anything, and the filter runs in the session that AUTHORED the spec,
            which the spec's own rule says cannot review its own work.)*
├ 🤖⚙️ 4.6  The computer checks every surviving finding against the source before the human sees it, because
            A READER CAN BE CONFIDENTLY WRONG — one quoted a stale docstring to claim a field could never
            render, hours after it had been demonstrated rendering.
├ 🤖🖥 4.7  The computer shows the tensions, each with ITS OWN RECOMMENDED FIX, so the human rules by
            exception instead of solving problems. It says how many were found and how many rejected, and
            teaches what a tension is — a place where two parts of the plan disagree, not a bug.
            THE SCREEN ENDS WITH: A — work through these. B — none of these change anything, move on.
├ 🙋🤝 4.8  ⑂ THE FORK.  `→ CODE (A|B)`
            · A → the human rules on each tension (accept the fix, reject it, or decide it differently)
                  → CONTINUE TO 4.9.
            · B → nothing is adopted, the phase closes → SKIP TO 4.10.
            ⛔ An answer that is neither breaks loudly and re-asks.
├ 🤖⚙️ 4.9  The computer applies the accepted fixes, and WHERE A FIX CHANGES WHAT A PHASE IS FOR, it says so
            and reopens that phase's "done" back in BUILDER PHASE 2 rather than quietly editing around it.
├ 🤖💾 4.10 The computer writes the outcome into the brief: what was found, what was adopted, and WHAT WAS
            REJECTED AND WHY. The rejections matter as much as the fixes — an unrecorded rejection gets
            re-proposed by the next reader who looks.
└ ✅ Done when every surviving tension has been ruled on by the human, the adopted fixes are in the spec,
     and the rejected ones are on the record with their reasons.
```

## 6a. ★★ THE FOUR READERS — their charges, one lens each

> **owner, 2026-08-06.** The lenses map to the four layers (§8d) plus one that cuts across all of them.
> ⭐ **THE POSTURE, unchanged and load-bearing: a critic, never an author.** *"It's not making a decision,
> it's actually looking for TENSIONS."*

**🖥 THE PRESENTATION READER** — *"how are we representing this information to the stakeholder, which we're
pretending is a boomer with not a lot of technical experience? How are we teaching them, supporting them
through each step?"* Asks whether a frightened beginner is **taught, guided AND ORIENTED at every single
screen** *(orientation added 2026-08-06 — L10)*: do they know where they are, how much is left, why they
are being asked this, and that they are allowed to edit what they are shown.

> ⭐ **AND IT CHECKS SUBJECT–VERB–OBJECT AGREEMENT IN EVERY SENTENCE SHOWN TO A HUMAN** *(owner, 2026-08-06,
> and he names it as a MAJOR failure mode):* *"Often the failure mode in the LLM is it starts to assume that
> the human knows what the subject or the object is, and it'll cut it out. This is a major failure mode,
> especially for an immature or unsophisticated user."*
> ⇒ **Every sentence names its actor and its object.** ⛔ No title-then-dash-then-fragment. ⛔ No dangling
> reference — *"it's really two"* leaves a reader asking *two what?* **The writer always knows what was
> meant; the beginner never does, and the beginner is the one being written for.**

**⚙️ THE BUSINESS-LOGIC READER — it owns ALL PROCESSING OF INFORMATION, and the seam is only one part.**
*"How are we integrating code and LLM knowledge, and what are the SEAMS between them? Are we abiding by the
SOP for integrating LLM and coding?"* **Expanded by the owner 2026-08-06 — the layer's real definition:**
**the data layer brings information IN; the business-logic layer is HOW THAT INFORMATION GETS ALTERED OR
TRANSFORMED.** It therefore also checks:

- ⭐ **SKILL-TO-SKILL HANDOFFS.** *"When one skill calls another skill as a sub-process, how is the handoff
  going to happen between those two — or is the handoff even possible between the two?"* This is a first-
  class check, not an afterthought: this whole skill's BUILDER PHASE 5 is one long chain of skills calling
  skills, and the handoffs are where such chains fail.
- ⭐ **ANY MATH IS DONE BY PYTHON, NEVER BY THE MODEL.** If a calculation exists anywhere in the skill, the
  reader confirms code performs it. *(a standing law of this system: the model silently miscomputes, and a wrong
  number contaminates every decision built on it.)*
- **Every transformation of information** — what shape goes in, what shape comes out, and what happens to
  anything that does not fit either.

**💾 THE DATA READER — information IN, information OUT, and the prompts.** *"Are we persisting knowledge to
a scratchpad correctly? Is all the knowledge being persisted to the correct place at each moment?"*
**Expanded by the owner 2026-08-06 into the simple form that catches the most:**

- **COMING IN:** the skill brings data from somewhere. **Does that place exist?** **Is the data in the
  format the skill needs in order to bring it in?** *(A source that does not exist, or exists in the wrong
  shape, is the cheapest catastrophic failure there is — and it is invisible until runtime.)*
- **GOING OUT:** after the business-logic layer and the human have transformed it — **where does it go?
  Where is it persisted to?** A skill that produces something with nowhere to put it has no output.
- **THE PROMPTS (§8g), added 2026-08-06:** does each phase have one, where is it stored, **is it scoped to
  that phase alone with no leak about later ones**, and is it tuned to that phase's desired outcome.

### ⏱ THE CHRONOLOGY READER — sharpened 2026-08-06, and it is the most demanding of the four

> **owner, verbatim:** *"The chronological reader is like the biological human. They're experiencing it in
> biological human chronological time. A human sits down, they type in slash whatever the name of the skill
> is, push enter — then what happens, then what happens, then what happens?"*

**It is not a fourth tier. It is the human's stopwatch walking the whole thing end to end**, double-checking
that the other three readers' territory actually happens **in a correct and optimal order in real time.**
What it asks:

1. **Is anything in the wrong order?** Is something used before it is produced — or merely *later than it
   optimally could be*? Both are findings; only the first is a bug.
2. **Could any of this run in PARALLEL to make it shorter?** Sequential work that has no dependency between
   its parts is wasted wall-clock.
3. **How long is this going to take the human?** Not machine time — **the human's felt duration**, which is
   the number they actually experience.
4. **Are sub-agents, background agents and parallel fan-out used the way `/build`'s own doctrine says?**
   A phase that runs everything inline when it could have fanned out is a finding.
5. ⭐ **THE TOUGH QUESTIONS NOBODY ELSE IS CHARGED TO ASK:** *could two phases be consolidated into one?*
   *Are there ten phases where the same desired outcomes could be reached in fewer?* *Are steps repetitive,
   such that they should be merged?* *Is a single step actually doing more than one thing?*
   **This reader is the only one with a mandate to say the whole shape is too big** — the other three grade
   what exists; this one asks whether it should exist at all.

⭐ **AND THIS IS WHY IT GETS THE SECOND LOOK (4.4).** Its findings are structural, so it can reach them
blind — but its *completeness* improves with the others' inventories in hand. Measured, unprompted, from the
reader itself on the first run: *"Running blind cost me some completeness, not correctness."*

---

## 7. BUILDER PHASE 5 — BUILD IT (the chain)

**PHASE OUTCOME:** the skill exists on disk, planned against the SOP, built to the plan, and tested — a
90–95% finished skill with three-tier architecture and a spec worth keeping, handed to the human to run.

**The four steps, in this order** *(owner, 2026-08-06 — the order is L2, locked)*:

1. **CHECK THE SOP — before anything is planned.** *"There's no point in wasting the tokens to build
   something that's not in accordance with SOP."* The spec is read against `system/sops/skill-building-sop.md`
   and anything it forbids is caught HERE, at zero cost, not after a build.
2. **INVOKE `/autoplan`, WITH AN INJECTED PROMPT THAT POINTS IT AT THE SOP.** *(owner: "we're going to inject
   a specific prompt when it hits auto plan with a pointer to the SOP — so that's going to be a specific
   prompt to point auto plan at the correct source. That'll be specific to this skill.")* ⛔ Not a hope that
   `/autoplan` remembers the SOP — an explicit pointer, passed at invocation.
3. **INVOKE `/build`.** It executes the plan under the existing build doctrine (Phase→Feature→Task, Execute →
   Verify → ✅, the honest close). ⛔ The builder does not re-implement any of it.
4. **INVOKE THE TESTER.** ⚠ **`/skill-tester` DOES NOT EXIST — ⛔ ruled CUT, and none ships here:** no `.claude/skills/*test*` ⛔
   directory, nothing registered, and `~/.claude/plans/skill-tester.plan.md` (2026-08-04) is a plan to
   CONSOLIDATE three existing labs, not a shipped skill. What exists today:
   `system/tools/conformance-lab/` and per-skill `verify-*.sh`. **Point the seam at those, and name the
   swap-in point.** ⛔ Do not report a tester ran when nothing ran — an unreachable tester maps onto the
   NO-OUTCOME member, never onto "clean" (`skill-building-sop.md` LAW 1b).

**ONE JOB PER TOOL.** The builder INVOKES; it never re-implements planning, building or testing.

### ✅ THE LOCKED STEP LIST — BUILDER PHASE 5 (owner, 2026-08-06: *"approve this and push to the spec"*)

```
├ 🤖💾 5.0  The computer fetches THIS phase's own prompt from the prompt library and injects it (§8g).
├ 🤖💾 5.1  The computer reads the complete spec — every phase, every step, every outcome — because the
            whole thing is about to be handed to another tool, and a gap here becomes a gap in the build.
├ 🤖⚙️ 5.2  The computer checks the spec against the skills SOP BEFORE ANYTHING IS PLANNED: what the SOP
            requires, and — the cheaper half — WHAT THE DO-NOT-BUILD SECTION SAYS WAS ALREADY TRIED AND
            FAILED. There is no point spending tokens building something the rules already rule out.
├ 🤖🖥 5.3  The computer shows what the check found, each item with a recommended fix, or says plainly that
            the spec is clean.  THE SCREEN ENDS WITH: A — fix these first. B — proceed as it stands.
├ 🙋🤝 5.4  ⑂ THE FORK.  `→ CODE (A|B)`
            · A → the computer amends the spec and re-checks → BACK TO 5.2.
            · B → proceed → CONTINUE TO 5.5.      ⛔ Neither breaks loudly and re-asks.
├ 🤖⚙️ 5.5  The computer invokes `/autoplan`, PASSING AN INJECTED PROMPT THAT POINTS IT AT THE SOP BY PATH,
            so the plan is built against the rules rather than against whatever the planner remembers.
├ 🤖⚙️ 5.6  The computer confirms the returned plan ACTUALLY CITES the SOP. A plan that cites nothing did
            not check anything, and the invocation is repeated rather than accepted.
├ 🤖🖥 5.7  The computer shows the plan in plain language — what will be built, in what order, and where the
            human will be stopped.  THE SCREEN ENDS WITH: A — change something. B — build it.
├ 🙋🤝 5.8  ⑂ THE FORK.  `→ CODE (A|B)`
            · A → the human says what to change, the plan is redone → BACK TO 5.5.
            · B → CONTINUE TO 5.9.     ⛔ Neither breaks loudly and re-asks.
├ 🤖⚙️ 5.9  The computer invokes `/build`, which executes the plan under the existing build rules and closes
            honestly — naming every task it did NOT complete, out loud, at the top.
├ 🤖⚙️ 5.10 The computer invokes the tester. ⚠ `/skill-tester` DOES NOT EXIST YET, so today this runs the
            conformance lab and the skill's own verifier instead. IF NOTHING TESTABLE RUNS, THE ARTIFACT
            SAYS SO PLAINLY — an untested skill is never recorded as a passing one.
├ 🤖🖥 5.11 The computer shows what happened: what was built, what the tester found, and WHAT WAS NOT BUILT
            AND WHY — the unfinished parts first, not buried.
├ 🤖💾 5.12 The computer writes all of it into the brief: the plan, the build's honest close, the tester's
            verdict or its absence, and anything left owed.
└ ✅ Done when the skill exists on disk, the plan it was built from cites the SOP, the build's close is
     recorded with every gap named, and the tester's verdict — or the fact that no tester ran — is written.
```

**DONE WHEN:** the skill is on disk, the plan cites the SOP, `/build` closed honestly, and the tester's
verdict — or its explicit absence — is recorded in the artifact.

<details><summary>the older, vaguer 2026-08-05 framing this replaced — kept because the lean it records was right</summary>

*(owner, 2026-08-05: "before it builds the actual skill there's going to be a phase where it looks at the
skills SOP. And also — I don't know if we built it yet — we wanted a **library of parts**, not fully built,
just tools it can use, with the SOP rules." His own lean: "maybe that's going to be in the SOP, maybe they
should be one and the same — they probably should.")* **That lean became the 2026-08-06 ruling: ONE SOP
file, no separate registers.**

</details>

⭐ **CRITICAL, his emphasis: the builder must know *what NOT to do*, not only what to do.** *"It wants to
know what to do and CRITICALLY what not to do. We may need to add this into our skills SOP."*

⚠ **MEASURED STATE — SUPERSEDED, kept for the record; do not act on it.** ~~`skill-building-sop.md` §II.4
lists 5 primitives and **exactly ONE is marked `(exists)`** — the capture gate. **The catalogue exists; the
shelf does not.** What the shelf should hold: closed vocabularies and the validators that enforce them (a
verb set · a status ladder · a coverage gate · a tool-less reader).~~

> ⚖ **CORRECTED 2026-08-08 [F3.6] — this reading was BACKWARDS, re-measured independently this session.**
> `skill-building-sop.md` §II.4 itself now carries a 2026-08-07 "HEADLINE INVERSION" (independently
> re-verified the same day): checked against the filesystem, **5 of 5 named primitives resolve to a real
> file on disk** — `system/parts/phase_gate.py`, `system/parts/order_lint.py`,
> `system/parts/precondition_gate.py`, `system/parts/section_present.py`, and the capture gate
> (`system/hooks/scratch_capture_gate.sh`, self-tested by `system/parts/capture_gate_selftest.py`) — all six
> paths confirmed present this session. **The library holds 19 built primitives in `system/parts/`**
> (`ls system/parts/*.py | wc -l` → `19`, re-confirmed this session), not the near-empty shelf the stale
> marker implied. **The catalogue exists AND the shelf is well-stocked.** This is the same [SL-4] → [SL-21]
> inversion recorded in the project brief. **Why it matters:** BUILDER PHASE 5 step 5.2 reads this section
> before a build is planned — a stale "the shelf is nearly empty" framing invites REBUILDING parts that
> already exist, which is the exact waste `skill-building-sop.md`'s own toolbox section exists to prevent.

### ⚖ RULED 2026-08-06 — THE SOP IS **ONE FILE**, WITH THREE NAMED SECTIONS INSIDE IT

*(owner, verbatim: "Yes, we're going to keep the SOP as one file. I don't want three different lists. We're
not going to duplicate. It's going to have some good front matter so that it'll be navigable by an LLM."
And again, unprompted: "I want it all as one SOP.")*

**The three sections the builder reads — all inside `system/sops/skill-building-sop.md`:**

1. **BEST PRACTICES** — what to do. **Already there** (the laws, the toolbox, the procedure). Nothing moves;
   it needs an INDEX, not a rewrite.
2. **⭐ DO NOT BUILD** — what has been tried and did NOT work. **Does not exist today, and the owner named it the
   most important of the three:** *"most importantly, we should have a do not build section of things that
   didn't work… It might not be populated at the moment, but we'll make that section."* Today that knowledge
   is scattered across LAW 1's fence, §II.2's failure modes, §V.9's anti-patterns, and every project's own
   DON'T-RETRY list — a builder would have to read 1,300+ lines and assemble it. **Each entry carries what
   was tried · why it failed, with a date and a file · what replaced it.**
3. **THE PARTS LIBRARY** — the tools already built, in one findable place, so the builder reaches for what
   exists instead of rebuilding it. **Each part carries its real path, whether anything actually CALLS it,
   and a "do not use this for X" line.**

⛔ **RULED OUT, 2026-08-06 — three separate register files.** A session proposed splitting these into their
own documents beside the SOP. the owner killed it: one file, no duplication. **The answer to "1,597 lines is too
long to read" is NAVIGABLE FRONTMATTER, not a split.** Recorded here so it is not re-proposed.

---

## 7a. BUILDER PHASE 6 — THE LIVE RUN, AND THE LOOP BACK

> **★ NEW 2026-08-06, the owner's own design. This is what makes the builder a RECURSIVE system rather than a
> one-shot factory.** *(Verbatim: "There may even be a recursive system where the user has a final phase
> where they actually launch the skill from a new session — but with the project fired for that new skill in
> question — and then they run it, and then those observations from that first run and the notes and the
> failings will feed back upwards directly into the spec document. And then the whole chain will fire again:
> the spec document will get updated, the autoplan will load, the build will build, the skill tester will
> fire.")*

**PHASE OUTCOME:** the skill has been run for real, by the human, on real work — and what it got wrong is
written back into the spec, so the next pass through the chain fixes it at the source rather than patching
the symptom.

**How it runs:**

1. **The human launches the new skill FROM A FRESH SESSION, with that skill's own project armed.** ⛔ Not a
   dry-run inside the building session — that session is contaminated by everything it just decided, and a
   long dry-run is itself a session that rots ([SL-6], `skill-building-sop.md` §III.9).
2. **They run it on real work.** `skill-building-sop.md` §V.8: *one real supervised run with the human in
   the chair beats ten sandbox arcs.*
3. **The observations, the notes and the failings feed back UP into the SPEC — not into a patch.** This is
   the load-bearing half. A fix applied to the built files and not to the spec is lost the next time the
   chain runs, and the spec quietly becomes a lie about the skill.
4. **The chain fires again:** spec updated → SOP check → `/autoplan` → `/build` → tester → live run.

⭐ **WHY THIS CHANGES THE WHOLE DOCUMENT'S POSTURE.** Because the chain re-fires, **no decision in this file
is permanently sealed** — that is exactly why §1a's LOCKED LIST exists and why everything outside it is
expected to change. *(owner: "we don't want it reading something and assuming that it's untouchable just
because we made that decision once.")*

### ✅ THE LOCKED STEP LIST — BUILDER PHASE 6 (owner, 2026-08-06: *"Yes, this is good. Let's push it to the spec document. It's now complete."*)

> **TWO WINDOWS AT ONCE.** Session **A** is the builder and STAYS OPEN, waiting. Session **B** is a
> disposable window where the skill actually gets run. The human moves between them; **nothing is copied
> across by hand**, because B writes its findings into the project's own brief and A reads them from there.

```
├ 🤖💾 6.0  The computer fetches THIS phase's own prompt from the prompt library and injects it (§8g).
├ 🤖🖥 6.1  The computer explains what is about to happen and WHY THE TEST RUNS SOMEWHERE ELSE: this session
            helped decide how the skill should work, so it already knows what everything was MEANT to do. A
            window that knows nothing is the only honest test. It teaches what the human is looking for —
            the moments they felt lost, had to guess, or had to say something twice.
├ 🤖💾 6.2  The computer writes the FULL HANDOFF into the brief, containing, in order:
            (a) ⭐ LOCKED — an instruction telling the new window to load the project-manager skill BY NAME,
                IN PLAIN LANGUAGE, NEVER AS A SLASH COMMAND, so the new session reads the project's brief
                without firing the command;  (b) the instruction to then type the skill's own command by
                hand;  (c) what to do during the run;  (d) THE ROLL-UP PROMPT to paste when the run ends;
                (e) the instruction to come back to session A and say "go".
├ 🤖🖥 6.3  The computer hands over the instructions and says plainly: LEAVE THIS WINDOW OPEN. This session
            is not finished — it is waiting for session B to write its findings into the brief.
├ 🙋🤝 6.4  The human opens session B, loads the project by name, and runs the skill ON REAL WORK. They
            observe and they say what they don't like — ⛔ BUT THEY DO NOT FIX ANYTHING AND THEY DO NOT
            BUILD. ("I didn't like that, but let's keep going.") They get as far through the skill as they
            can and notice everything along the way.
├ 🙋🤝 6.5  When the run ends — finished or as far as it got — the human pastes THE ROLL-UP PROMPT into
            session B. That prompt tells B exactly what to capture and to write it DURABLY into the
            project's scratchpad: everything the human disliked, everything they said, and — ⭐ the part
            only that window can see — EVERYTHING THE HUMAN NEVER SAW, including the background work that
            happened off-screen.
├ 🙋🤝 6.6  The human returns to session A and says "go".  `→ CODE (go)`
            ⛔ Anything other than "go" breaks loudly and re-asks. The computer NEVER reads an ambiguous
            reply as permission to proceed — this answer is attached to code, so the human makes the choice
            and the choice is confirmed (owner, 2026-08-06).
├ 🤖💾 6.7  Session A reads the project brief and its scratchpad. NOTHING IS COPIED ACROSS BY HAND — session
            B already wrote it down, which is the whole reason the handoff was built that way.
├ 🤖⚙️ 6.8  The computer decides ONE thing first: IS ANYTHING CRITICAL MISSING FROM THAT TEST RUN? It is
            deciding whether it can proceed, not whether the skill was any good.
├ 🤖🖥 6.9  The computer says which it is. If something is missing, IT WRITES A SECOND PROMPT for the human
            to paste into the still-open session B, naming exactly what to find and to write to the
            scratchpad. If nothing is missing, it says session B can be closed.
            THE SCREEN ENDS WITH: A — go fetch what's missing. B — we have everything.
├ 🙋🤝 6.10 ⑂ THE FORK.  `→ CODE (A|B)`
            · A → the human pastes the new prompt into session B and returns → BACK TO 6.7.
            · B → session B is closed → CONTINUE TO 6.11.     ⛔ Neither breaks loudly and re-asks.
├ 🤖⚙️ 6.11 The computer proposes changes TO THE SPEC. ⭐ IT MAY ONLY CHANGE WHAT THE SPEC MARKS PROVISIONAL;
            THE LOCKED LIST (§1a) IS WHAT IT MUST NOT TOUCH WITHOUT A RULING. This is what that marking was
            for: a fresh session coming in cold can tell instantly what it is allowed to rewrite, instead of
            guessing at what was settled.
├ 🤖🖥 6.12 The computer shows the proposed spec changes in plain language, each with why the live run
            justifies it.  THE SCREEN ENDS WITH: A — change something. B — approve it.
├ 🙋🤝 6.13 ⑂ THE FORK.  `→ CODE (A|B)`  · A → redraft → BACK TO 6.11.  · B → CONTINUE TO 6.14.
├ 🔁 6.14  The chain fires again. WHERE IT RE-ENTERS DEPENDS ON WHAT 6.11 CHANGED (owner, 2026-08-06):
            · the spec changed MATERIALLY -> RE-ENTER AT BUILDER PHASE 4, the tension swarm. Step 6.11 had
              THIS session rewrite the spec, and a session cannot review its own fresh writing — measured:
              7 of the first swarm's 12 findings were drift that same session created hours earlier. Four
              cheap parallel readers are the price of not building on unreviewed self-edits.
            · the change was trivial (a wording fix) -> RE-ENTER AT BUILDER PHASE 5 and skip the swarm;
              four readers over a one-word change is waste.
            From there: check the SOP, plan it, build it, test it — each with its own approval before it
            moves. Nothing is re-specified here, because PHASE 5 already is that chain.
├ 🔁 6.15  The human opens a THIRD window and runs the sharpened skill again, from 6.4. THIS LOOP RUNS AS
            MANY TIMES AS IT TAKES, and each pass is smaller than the last because the spec keeps the gains.
└ ✅ Done when the human has run the skill for real, everything that run revealed has been written into the
     spec rather than only into the built files, and the human says it is good enough to stop.
```

⭐ **"EVERYTHING THE HUMAN NEVER SAW" IS A CATEGORY OF EVIDENCE NOTHING ELSE IN THIS SYSTEM COLLECTS.**
Every other feedback loop captures what the person noticed. The roll-up prompt captures what happened
off-screen — the background work, the steps that ran silently, the things that went right invisibly — and
**the only window that can see it is the one that just ran.**

**DONE WHEN:** a real run has happened, and every observation from it has landed in the spec — or been
explicitly ruled out of scope. ⛔ An observation that lives only in the transcript is lost.

---

## 8. PRESENTATION — how every round must look

> **★ HARD-WON 2026-08-05, over five rejected attempts in one sitting.** The content was right every time
> and the owner still could not use it. **Presentation is not polish here; it is the product.**

### The four moves that open EVERY round, in order

1. **THE MAP — "here is the whole thing, and here is where you are."** What is being built, in one plain
   sentence. Then the phases in order with a one-line plain description each and a status. Mark the current
   position. **Include the phases the human is NOT present for, marked as such** — knowing they exist is
   orientation too.
2. **WHAT CAME BEFORE — "here is what we already settled."** One short paragraph. The human has been in
   other windows; **assume zero recall, never make them ask.**
3. **WHAT WE ARE DOING NOW, AND WHY THIS FIRST.** State what you are about to ask for **and why it has to
   come first** — the reason, not just the request. Say explicitly what they are NOT being asked to do.
4. **THEN THE QUESTIONS.** Three is better than five. Each carries the builder's guess. Where there is no
   basis for a guess, **say so plainly** — *"I don't have enough information to suggest"* is legitimate and
   expected, never a filler guess.

### ★★ THE LOCKED VISUAL STYLE — approved verbatim by owner, 2026-08-05

> **This is THE house style for every screen the builder shows. It was approved after five rejected
> attempts in one sitting.** *(owner: "Thank you Christ — save this verbatim as the visual style.")*
> ⚠ **What is locked is the SHAPE, not the words.** The list's CONTENT in this specimen was corrected
> moments after it was approved (see §8a); the LAYOUT is what carries forward.

**What was rejected on the way here, so nobody re-proposes it:**
- ⛔ **A bordered ASCII screen** — title band, `━━━` rules, indented columns, a `▶` action bar.
  *"That's too much like a fucking 80s computer program."* **No boxes, no title bands, no code-block
  screens, no fixed-width layout.** *(This also matches the 2026-08-04 graphics cut on `/ingest`.)*
- ⛔ **Tables.** *"It was just a fucking list, man. It was just a list. It was much more conversational."*
- ⛔ **A wall of bold.** *"This is too hard to read, this is shitty user interface presentation level."*
- ⛔ **Stacked three-deep headers.**

**THE APPROVED SPECIMEN — reproduce this SHAPE:**

```
# 🛠 Skill Builder

Let's build you a skill.

You tell me what you want it to do, in your own words. I do the rest — work out
the phases, draft what each one has to accomplish, and show you my guesses so you
can tell me where I'm wrong. You never have to learn how any of it works underneath.

**<one bold lead-in line introducing the list>**

1. <short item, no bold inside>
2. <short item>
3. <short item>
4. <short item>

<one plain closing line>

---

**<one bold framing line for the ask.>** <one plain sentence of why it matters.>

### <THE QUESTION, as a heading>

<one plain line reframing it>

<examples in italics, and permission to be messy>
```

**The seven elements that make it work:**
1. **An H1 with one emoji and the skill's plain name.** The only emoji on the screen.
2. **Prose in short paragraphs**, 2–3 sentences each, no indentation. Ordinary text width.
3. **Exactly ONE bold lead-in line** above the list — the only bold in the top half.
4. **A short numbered list**, no bold inside the items, no sub-bullets.
5. **A single `---` rule**, and only one, dividing setup from the ask.
6. **The question as an `###` heading** — that heading IS the visual centre; nothing else competes.
7. **Italics for the examples**, plus an explicit "messy is fine."

**The governing principle: structure and whitespace carry the emphasis, not decoration.** If you find
yourself reaching for a border, a table, or a third bold phrase, the layout is already wrong.

### The format rules — violated repeatedly, so they are stated as absolutes

- ⛔ **NO TABLES for the human.** *"It was just a fucking list, man. It was just a list. It was much more
  conversational."* Use prose and a plain numbered list.
- ⛔ **NO wall of bold.** Bolding everything bolds nothing. **the owner, on a table-and-bold-heavy draft:
  *"this is too hard to read, this is shitty user interface presentation level."***
- ⛔ **NO section headers stacked three deep.** Talk, then list, then ask.
- ⛔ **NEVER lead with an internal codename.** *"You gave it a name called scan — the user has no fucking
  idea what the name means. So let's be literal."* ⇒ **"Phase 2, round 1"** first; the codename is optional
  colour.
- ⛔ **NEVER open a round with questions.** The map comes first, **every single round**, not just the first.
- ⛔ **THE MACHINERY NEVER SURFACES.** No "3×4 grid," no "tier," no "step type," no "evidence surface," and
  **not the builder's own phase numbers either.** The map the human sees is **THEIR product's** phases, not
  the builder's. *(A session showed the owner the builder's own five phases as the map. That is machinery. It
  was wrong.)*
- ✅ **State the order-of-operations reason.** *"I have to get the outcome before the steps, because
  otherwise I'm inventing steps and working backwards to justify them."*
- ✅ **Plain language, always.** **The human should not need to know the process to answer questions about
  their own product.** Write for a smart person who has not been paying attention.
- ✅ **Everything the human can respond to is NUMBERED** — they are dictating. An unnumbered list forces
  them to restate each item aloud, and **the cost is invisible to the machine**, so it will never
  self-correct for it.

### Why wrong guesses are the template WORKING

Two of the three guesses in the first approved round were wrong. **Kept deliberately.** A wrong guess the
human corrects in four words is far cheaper than an open question they must compose an answer to from
nothing. ⛔ Never hide a miss — a worked example that hides its own misses teaches the wrong lesson.

**Worked example of a full approved round:**
`state/projects/skill-builder/examples/round-opening-template.md` (Drive) — the owner on seeing it: *"Holy
crap, this was really really good. Put this into the skill builder."*

---

## 8a. BUILDER PHASE 1's OPENING SCREEN — the content, corrected

> **the owner corrected this immediately after approving the layout above, 2026-08-05.**

⛔ **THE LIST IS NOT "the four things I'll ever ask you."** That was wrong. **The list is a set of
DIFFERENT WAYS OF ASKING THE SAME QUESTION** — plain-language reframings of *"what's the desired
outcome?"*, offered because most people cannot answer that phrase cold.

*(owner, verbatim: "It's gonna ask you for what you want the desired outcome to look like. And you can
define it differently — you can say, in other words, another way of thinking of a desired outcome is:
what does it look like when it's done? What does it produce if it worked? What would happen now that
doesn't happen in your life right now? I mean, can have somebody just say in plain language.")*

**The reframings, from him:**
- What does it look like when it's done?
- What does it produce, if it worked?
- **What would happen in your life that doesn't happen now?**

**Why this is the right move and not padding:** "desired outcome" is jargon dressed as plain English. A
person asked for one either freezes or describes a mechanism. **Three concrete reframings give them a door
that fits** — and the third one in particular pulls the answer toward a felt result rather than a feature
list, which is exactly what BUILDER PHASE 1 needs.

**⇒ BUILDER PHASE 1's opening screen therefore carries:** the greeting · what the builder does and what
the human never has to learn · **the reframings as the numbered list** · then the single question.

⛔ **Do NOT open with the four undecidables.** They are the METHOD's input list (§1) — real, but they are
machinery, and §8 forbids machinery on screen.

### ✅ THE "WHY AM I DOING THIS AT ALL" TEXT — **WRITTEN AND APPROVED BY THE OWNER 2026-08-08**

> **owner, 2026-08-06:** *"The main bulk of what the explanation would be, it would be in the first official
> output. We'll create a little pin for us to go back and kind of lock that text in, because that's going to
> stay the same all the time. But phase two and all the appropriate phases can add a little nugget of how
> it's being refined — again, locating us within the process."*

**What is owed:** one fixed passage, written once and reused forever, that answers the question a beginner
is actually holding at the opening screen — **why am I being asked to do any of this?** The answer, in
substance: *once the phases exist, the computer can reach into what it already knows and fill in the rest,
so you never have to write a specification yourself.* **It belongs HERE, in BUILDER PHASE 1's opening
screen, because by the time someone reaches the phase list they have already committed.**

**Then every later phase carries a short nugget** — not the whole explanation again — saying how this phase
refines what came before, and where the human now sits in the process (L10).

✅ **WRITTEN AND APPROVED 2026-08-08 (owner: "1 yes").** It is FIXED TEXT — reproduce it verbatim, never
improvise it per-run, and treat it as L4-locked like the screen it sits in. The approved wording is in the
locked screen below.
⚠ **PLACEMENT IS PROVISIONAL, deliberately.** The spec said it belongs *"right after the human commits to
answering,"* so it sits at the FOOT of the screen. **the owner ruled 2026-08-08 that the presentation layer gets
fixed during the first real run, step by step** — so if it reads better higher up, move it then. That is a
LOOK change, not a FUNCTION change.

### ✅ THE LOCKED OPENING SCREEN — reproduce this verbatim (owner, 2026-08-05)

> Only the skill's name changes. **Everything else is fixed text** — this is the "script, not regenerated
> per run" doctrine: *"If it's non-prescriptive or generalizable, we could just make it into a script."*
> The reframings sit BELOW the question, because they are ways of answering it, not a preamble.

```markdown
# 🛠 Skill Builder

Let's build you a skill.

You tell me what you want it to do, in your own words. I do the rest — work out the
phases, draft what each one has to accomplish, and show you my guesses so you can tell
me where I'm wrong. You never have to learn how any of it works underneath.

**One question to start, and it's the only one that matters right now.**

### What do you want this skill to do for you?

If that's a hard way to think about it, any of these get at the same thing:

1. What does it look like when it's done?
2. What does it produce, if it worked?
3. What would happen in your life that doesn't happen now?

Not how it works — what it's like when it's working.

Say it however it comes out. *"I want to be able to…"* or *"right now I have to ___ and
I hate it."* Messy is fine. I'll say it back to you, we'll sharpen it over a round or
two, and then we move.

---

**Why I'm only asking you this one thing.** Once I know what you want out of it, I can work out the rest — how it breaks up, what each part has to do, which pieces already exist that I can reuse. What I can't work out is what you actually *want*, or whether I've guessed right.

So those are the only things I'll come back to you for. Everything else is mine, and I won't make you sit through it. That's the whole idea here — you shouldn't have to hold this in your head, or learn how any of it works, or write a single thing down properly. You talk, I draft, you tell me where I got it wrong.
```

---

## 8b. BUILDER PHASE 2's SCREEN — LOCKED VERBATIM (owner, 2026-08-05)

> **Approved after eight iterations in one sitting.** ⚠ **The SHAPE and the DENSITY are what is locked** —
> the `/ingest` specifics are the worked example. **Reproduce the emoji, the `├ └` outline markers, the
> 🤖/🙋 speaker labels, and above all the SENTENCE LENGTH.**
>
> **The two failure modes it is calibrated between**, both hit on the way here:
> ⛔ **Too spread out** — one fragment per line with vertical arrows. *"Almost unreadable because there's
> so many."*
> ⛔ **Too abbreviated** — terse phrases. *"The sentences are too abbreviated for the user to understand.
> We need more description because they don't understand what's going on."*
> ⇒ **CONDENSED STRUCTURE, FULL SENTENCES.** The outline is tight; each line is a real explanation that
> teaches. **The screen is a teaching surface, not a summary.**
>
> **Speaker labels:** 🤖 **LLM** and 🙋 **HUMAN** — ⛔ never "me"/"you" as the label.
>
> ⚖ **RECONCILED 2026-08-06.** This clause used to also read *"never 'the computer'"*, which read as a
> direct contradiction of §8c rule 3 (*"Say **the computer**… write `The computer …` as the subject of a
> real sentence"*). **A swarm reader surfaced it; the owner reconciled it: they are two different rules, not one
> contradiction.**
> · **THIS rule is about RENDERING** — the emoji-plus-label is how the line MARKS who is acting, in place of
>   "me" and "you", which were unclear.
> · **§8c rule 3 is about SENTENCE STYLE** — every sentence names its subject and its object in full,
>   because the model kept cutting them out.
> **Both apply at once.** The correct line carries the label AND a full sentence:
> `├ 🤖 **1.1** The computer flattens the export onto disk…` ⇒ the ban was always on *me/you as a label*,
> never on the word "computer" as a sentence's subject.
> **The 🔁 LOOP is its own step line**, placed where the loop actually happens — ⛔ never a badge on the
> phase title.

```markdown
# 🛠 Skill Builder

**Your target, in your words**
> [the human's desired outcome, played back verbatim in their own words]

That's the target. Everything below is my attempt to get you there.

**My plan — 4 phases.** 🤖 = the LLM works · 🙋 = the human's turn · 🔁 = a loop

**📚 1 · Make the piles**
├ 🤖 **LLM** — reads the title and tags of all 1,521 chats. Nothing gets opened, no bodies
  are read. It's looking for what subjects *naturally* exist in there, rather than sorting
  them into categories you had to invent up front. The reason this matters: the same subject
  is usually scattered all over the corpus — twenty conversations about your taxes, months
  apart, sitting nowhere near each other. This step gathers all those scattered pieces into
  one place.
├ 🙋 **HUMAN** — looks at the piles it made, each with a few real examples, and fixes the
  ones that are wrong. Three ways to fix a pile: **split** it, if the LLM lumped two
  different subjects together. **Merge** two, if it treated one subject as two. Or **drop** a
  whole pile, if it's genuinely junk and you never want to see those chats again.
└ ✅ **Done when** every chat sits in its correct pile, and the piles match how you actually
  think about your life.

**🔍 2 · Screen piles, one at a time**
├ 🤖 **LLM** — takes one pile and reads a slice of every chat in it, behind a safety filter,
  so raw text never reaches this conversation. How much it reads depends on length: a short
  chat is read whole, a medium one gets its beginning and its end, and a long one gets its
  beginning, a chunk from the middle, and its end. For each chat it writes two or three plain
  sentences on what it actually is, and tells you how big it is.
├ 🙋 **HUMAN** — reads those descriptions and gives every chat one of three answers. **Keep**
  means you're confident there's real value in there and it's worth reading properly. **Toss**
  means you're confident there's nothing. **Explore** means you honestly can't tell from what
  you were shown, and you want a better look before deciding.
├ 🤖 **LLM** — takes everything you marked **explore** and goes back for a much larger read of
  those chats, returning with a full paragraph on each that covers the whole arc of the
  conversation — where it started, what it moved through, where it ended up.
├ 🔁 **LOOP** — those come back to you, you rule on them again, and this keeps going until
  nothing is left sitting in **explore**. The pile cannot be closed while anything is still
  unresolved.
└ ✅ **Done when** every chat has a ruling you're confident in — and you never had to open a
  single one yourself.

**🪞 3 · The world map**
├ 🤖 **LLM** — now reads the keepers properly and whole, then writes you a paragraph about
  *yourself*, drawn from that pile. Prose, not a list of facts — because a wrong sentence
  about you jumps out, where a wrong bullet in a list of twenty doesn't.
├ 🤖 **LLM** — then sorts everything it found into three kinds and shows you its guesses.
  **Canonical** is what's permanently true about you and belongs in a canon file. **Dated** is
  a discrete finding that was true at a moment and is worth keeping with its date on it.
  **Records** are the bigger bodies of material — a whole research thread you'd want to go
  back and read. Those aren't rewritten or processed; it just keeps a pointer to the original.
├ 🙋 **HUMAN** — corrects the paragraph where it's got you wrong, moves anything it filed
  under the wrong kind, and says which records are actually worth keeping a pointer to.
├ 🤖 **LLM** — rewrites the paragraph with your corrections in it and shows you again, so you
  can see your fix actually landed. It also proposes what folder shape this pile has earned —
  one folder, or a folder with sub-folders under it.
├ 🔁 **LOOP** — you keep correcting and it keeps re-showing until the picture is right. Only
  then does this pile move on.
└ ✅ **Done when** you've read yourself back, fixed what was wrong, and what's on the screen
  perfectly reflects your understanding of your own life. It's a mirror held back to you.

**🗂 4 · File it**
├ 🤖 **LLM** — assembles the whole folder tree out of the branches you already approved pile
  by pile, and shows you the complete shape for the first time.
├ 🙋 **HUMAN** — corrects the overall shape, then approves each file before it's written.
  Nothing lands anywhere without your yes.
└ ✅ **Done when** everything you kept is where you said it goes, and every folder was born
  with its own canon file.

**Why this order.** [one paragraph arguing how these phases reach the desired outcome —
this is the real thing the human is ruling on, not decoration]

---

### ❓ Where did I get it wrong?

1. [question, carrying the builder's guess]
2. [question, carrying the builder's guess]
3. [question, carrying the builder's guess]
```

**Wording rulings inside that screen, each earned:**
- ⛔ *"every chat sits in exactly one pile"* → ✅ **"its correct pile."** *"Exactly one pile makes it sound
  like they're all going into one pile, which is not true."*
- ⛔ *"Screen a pile"* → ✅ **"Screen piles, one at a time."** Same misreading.
- ⛔ *"tell it where the boundaries are wrong"* → ✅ **name the three moves and explain each.** *"I have no
  idea what that means."* **Never use a word the human has to decode; spell out the action.**
- ⛔ Listing the verdicts as bare words → ✅ **bold them and give each a full sentence** saying what it means.

---

## 8c. BUILDER PHASE 3's SCREEN — LOCKED VERBATIM (owner, 2026-08-05: *"Perfect!"*)

> **The step-level screen.** Same visual family as §8b, with four rules this round earned.

**THE FOUR RULES THIS SCREEN LOCKS:**

1. **THE HEADER CARRIES THREE THINGS, IN THIS ORDER:**
   - **What the builder is DOING, in plain words** — `🛠 Skill Builder — Choose the steps`.
     ⛔⛔ **NEVER PUT THE BUILDER'S OWN PHASE NUMBER ON SCREEN.** *(owner, 2026-08-05: "Don't say phase
     three for the skill builder, because it's going to get confusing with the actual skill that we're
     building. So just do it: Skill Builder — choose the steps.")*
     **Two numbered ladders on one screen is the ambiguity that cost a whole session** — and the builder's
     ladder is the one the human never needs. **This is §8's machinery-never-surfaces rule applied to the
     title bar**, a rule this spec stated and then broke twice. ⛔ Also not a bare *"Skill Builder"* with
     no verb — the human still needs to know what this screen is for.
   - **Which SUBJECT PHASE is being worked, and WHAT IS BEING DONE TO IT RIGHT NOW** — e.g.
     `PHASE 1 — Choose the desired outcome for each step`.
     ⭐ **THE PHASE NUMBER LEADS, AND IT LEADS PROMINENTLY.** *(owner, 2026-08-06: "the next thing says
     skill builder again — that should just say PHASE ONE in a very prominent way, because visually that's
     the most important information: being able to see, oh we're in phase one, now we're in phase two, now
     we're in phase three.")* ⛔ **Do NOT repeat the skill's own name on this line** — the H1 directly above
     already said it, and repeating it spends the one line that tells the human WHERE THEY ARE. The phase
     number is the human's position in their own product, and position is the thing they lose first.
     ⛔⛔ **NOT the phase's own name.** *(owner, 2026-08-05: "It says ingest phase one dash CHOOSE THE
     DESIRED OUTCOME FOR EACH STEP. Why are you saying 'screen the piles one at a time'? No.")*
     **The phase's name says what that phase does when the finished skill RUNS. The human is not running
     it — they are BUILDING it, and this line has to say what they are being asked to do in this sitting.**
     Repeating the phase name here wastes the one line that could orient them. **This is the ONLY numbered
     ladder allowed on screen**, and it is the human's own product.
   - ⭐ **THAT PHASE'S DESIRED OUTCOME, restated in full.** **The load-bearing one.** Steps are DERIVED
     from the outcome, so the human cannot judge a step list without the outcome in front of them.
     **It turns "do these steps look OK?" into the answerable "do these steps get me to THAT?"**
     ⛔ Never make them scroll back or remember it.
   **Propagate this header to every builder screen that works below the phase level.**

   ⭐ **AND SAY WHAT IS BEING PRODUCED:** this screen is not only choosing steps, it is **giving each step
   its own desired outcome.** *(owner: "the whole point is we're creating the desired outcome for the steps
   in phase two.")* Each step's outcome rides in its sentence as the `so …` clause — that clause IS the
   step's desired outcome, not a flourish.
2. **SAY OUT LOUD THAT EVERYTHING IS A GUESS, and that corrections flow BACKWARD.** *"It needs to be clear
   that this is a suggestion, and we need to go back and backfill this into phase 2."* If correcting a step
   changes what a PHASE is FOR, that phase's finish line gets reopened. **Say that explicitly** — otherwise
   the human thinks the earlier phase is sealed and swallows the correction.
3. ⛔⛔ **EVERY LINE IS A FULL SENTENCE WITH AN EXPLICIT SUBJECT.** *"I really hate that you're using
   cut-off sentences… 'Unpack the corpus — flattens the export to disk' — who is the subject? Say **the
   computer**. **The computer flattens the export to disk and gives every chat a record so it can be
   tracked.**"*
   ⇒ **Write `The computer …` / `The human …` as the subject of a real sentence.** ⛔ **NEVER a
   title-then-dash-then-fragment.** ⛔ Never "me"/"you" as the actor.
4. ⭐ **EVERY STEP IS NUMBERED `<phase>.<step>`** — `1.1`, `1.2`, `2.7`. *(owner, 2026-08-05: "Now you
   just need to number every step.")* **Two reasons, both load-bearing:** the human is **dictating**, and
   an unnumbered list forces them to restate a whole sentence aloud to point at it — a cost the machine
   never feels, so it will never self-correct for it. And it makes the naming rule work end to end:
   `INGEST PHASE 2 step 2.7` is unambiguous in a way "the explore re-read bit" is not.
   **The 🔁 LOOP line is a step and gets a number. The ✅ line is the phase's outcome, not a step — no
   number.**
5. **FOLD THE STEP'S PURPOSE INTO THE SENTENCE WITH "so …"** — ⛔ not a separate `Achieves:` label. The
   step still carries its own outcome, as the method requires; it just reads as English. *"Make it a little
   bit simpler."*

**PACING:** ⭐ **one PHASE per round.** Twenty steps at once is unreadable. **This does NOT break
horizontal-by-altitude** — every phase's *finish line* was settled in BUILDER PHASE 2 before *any* step was
drafted. Going phase-by-phase *within* the step altitude is pacing, not verticality. **Say this to the
human**, because it looks like a contradiction otherwise.

```markdown
# 🛠 Skill Builder — Choose the steps

### 📚 Ingest phase 1 — Choose the desired outcome for each step

**Desired outcome —** every chat sits in its correct pile, and the piles match how you
actually think about your life.

**Everything below is a guess.** You told me what the four phases are and what "done" means for
each one. From that, I've worked out what I *think* the steps inside each phase should be. None
of it is decided. You correct whatever's wrong, and if a correction changes what a phase is
actually for, we go back and fix that phase's finish line in BUILDER PHASE 2.

I'm doing one phase per round, because twenty steps at once is unreadable.

├ 🤖 **1.1** The computer flattens the export onto disk and gives every chat its own record, so
  nothing can get lost track of later.
├ 🤖 **1.2** The computer checks that the safety filter is switched on, before anything at all gets read.
├ 🤖 **1.3** The computer tells the human it's about to go quiet for a few minutes, so the silence
  doesn't look like a crash.
├ 🤖 **1.4** The computer reads the title and tags of all 1,521 chats — never the bodies — and lets the
  real subjects surface on their own.
├ 🤖 **1.5** The computer puts every chat into a pile, so nothing is left floating with nowhere to go.
├ 🤖 **1.6** The computer shows the human the board: every pile, how many chats are in it, and two or
  three real examples from inside it.
├ 🙋 **1.7** The human fixes the piles — splits one that's really two subjects, merges two that are
  really one, or drops a pile that's junk.
├ 🤖 **1.8** The computer reads a drop back to the human before acting on it, because getting a split
  wrong costs a redo but getting a drop wrong throws material away invisibly.
├ 🔁 **1.9** The computer re-shows the board and the human keeps correcting, until the shape is right.
└ ✅ Done when every chat sits in its correct pile.

---

### ❓ Where did I get it wrong?

1. [question carrying the builder's guess]
2. [question carrying the builder's guess]
3. [question carrying the builder's guess]

---

**A** — Keep refining this phase's steps.
**B** — Lock them and move to the next phase.
```

> AMENDED 2026-08-06. The A/B ending was MISSING from this locked specimen, while step 3.6 requires the
> screen to end with it and step 3.7 reads that exact answer to decide whether to loop or advance.
> Reproduced verbatim as it stood, BUILDER PHASE 3 could never mechanically advance past its own worked
> example. Found by the presentation reader, corroborated by the chronology reader's second look.

---

## 8d. ★★ THE STEP-LINE TIER MARKERS — LOCKED 2026-08-06 (L8)

> **the owner's ask, and his own reason for it:** *"I want an emoji for each different layer of the three tier
> architecture… instead of it saying 'the computer shows the whole thing on screen', I would see that
> there's a presentation layer — okay, what is the readout for the purposes of the human?"* And on the
> jargon question: *"we don't need to teach the jargon and the tiers, but it really does help to see it. And
> it also helps the system itself to understand what it is that we're starting to draft."*

**Every step line carries the ACTOR first, then the LAYER.** The layers, in their canonical order:

| marker | layer | what it means on the line |
|---|---|---|
| 💾 | **DATA LAYER** | something is read from, or written to, a place that survives the session |
| ⚙️ | **BUSINESS LOGIC LAYER** | the machine works something out — decides, drafts, judges |
| 🖥 | **PRESENTATION LAYER** | something is rendered for a human to read |
| 🤝 | **HUMAN-IN-THE-LOOP LAYER** | the human acts, and something is expected back from them |

### ⭐⭐ THERE ARE FOUR LAYERS, NOT THREE — owner, 2026-08-06, `authority: user`

> *"It keeps in mind that this whole thing is a human-in-the-loop interaction. So it kind of keeps in mind
> that there's four layers really — in a weird way, we might want to persist this to the spec: there's the
> data layer, the business logic layer, the presentation layer, and the human-in-the-loop layer. In fact,
> absolutely, we need to persist that to the spec. 100%."*

**Why this is a real layer and not a courtesy.** The classic three-tier model describes a system that runs
by itself. **A skill does not.** The human's turn has its own contract — *what is expected back from them* —
and that contract is exactly what the other three layers cannot supply and cannot verify. **Naming it as a
layer is what makes it designable**: it gets a shape, an expected return, and a failure mode, instead of
being the gap between two machine steps. *(owner: "that's the difference between an LLM system and a normal
one." Filed to `state/debt-ledger.md` for system-wide adoption, 2026-08-06.)*

⛔ **A loop line (🔁) carries no layer marker** — a loop is a control shape, not a layer.
⛔ **The ✅ outcome line carries no number and no marker.**

### ⭐ AND EVERY HUMAN STEP NAMES WHO IT ANSWERS TO — `→ LLM` or `→ CODE`

> **owner, 2026-08-06 — the light version, deliberately:** *"All we're figuring out is, is the human
> returning a response to the LLM, or is it returning a response to code? … When it's ideating and looping,
> that's returning input to the LLM. But 'is the phase done, A or B' — we need to return that to code,
> because the code is preventing us from moving forward to the next phase."*

| tag | what it means | consequence |
|---|---|---|
| **`→ LLM (open)`** | the human is thinking out loud; anything they say is usable | no format, no gate, no failure mode |
| **`→ CODE (A\|B)`** | the human's answer is read by code that gates something | **the answer must be a member of a named set, and the code must refuse anything off it** |

**Why notate it now, before any code exists.** *(owner: "we don't need to code that machinery. We just need
to know that there may be two or more decisions that need to be made, or that code would be connected.")*
The seam is where this system's bugs live (`skill-building-sop.md` LAW 1). Marking which human answers are
destined for code — **while the steps are being written** — means the closed vocabulary is designed at the
same moment as the question, instead of retrofitted onto a question that was never shaped to be answered.

⛔ **A `→ CODE` step owes a failure mode.** When the human answers something outside the set, the step must
break loudly and re-ask — never guess which member they meant, and never let an unrecognised answer fall
through as agreement. *(This is LAW 1's NO-OUTCOME member, applied to the human's side of the seam.)*

**Two rules that fall out of this and are worth more than the decoration:**
- ⭐ **A STEP NEEDING TWO TIER MARKERS IS DOING TWO JOBS** — it is usually two steps wearing one number.
  This is the cheapest structural smell-test in the method, and it costs nothing to apply.
- **Reading the tier column top-to-bottom shows a phase's real SHAPE** — e.g. BUILDER PHASE 2 reads
  `💾 ⚙️ ⚙️ ⚙️ 🖥 · 💾`: read the record, think three times, show it once, write it back. A phase whose
  column is all ⚙️ has no human in it and is not a phase (§4's phase test).

⛔ **The jargon still never surfaces in the human's own words.** The MARKER is on screen; the phrase
*"presentation layer"* is not spoken to the human. A legend in plain language — *working it out · what
you'll see · written down* — is the most that appears.

---

## 8e. ★★ THE FOUR STANDING RULES OF EVERY SCREEN — LOCKED 2026-08-06 (L9–L13)

> the owner ruled all four in one sitting, 2026-08-06, and ruled them locked. They apply to **every phase,
> every turn** — BUILDER PHASE 1 included.

**1. ⭐ THE STAKEHOLDER IS A TECH-FRIGHTENED BEGINNER, AND YOU ARE TEACHING THEM.** *(L9)*
*"We're treating our human in the loop like a boomer… they don't just need to be informed, they need to be
guided and taught about the process. This is a learning process. You're teaching them, you're not just
building a skill — you're teaching them about the process of building a skill. They don't need just to know
what to do, they need to know WHY they're doing it."*
⇒ Every screen carries the **why**, not only the **what**. A screen that instructs without teaching has
failed even if the instruction is correct.

**2. ⭐ ORIENT THEM ON EVERY TURN — AND IT RE-ANCHORS THE SESSION TOO.** *(L10)*
*"They need to know where they are inside of the process every time… otherwise it looks to the human
psychologically like, oh my God, I've been doing this forever, when does this end? They need to know that
they're in step 2 out of 8. They need to know that this will end, otherwise they start to get discouraged."*
⭐ **AND THE SECOND REASON, WHICH IS THE ONE NOBODY WRITES DOWN:** *"guess what's also stupid is a fresh LLM
session. So by constantly reprinting it on the screen, we reduce the likelihood that the session goes off
the rails — because we're also re-anchoring not just for the human but for the LLM session."*
⇒ **The orientation banner is a DUAL-PURPOSE instrument: it holds the human's morale and the session's
frame at the same time.** This is `skill-building-sop.md` §IV.4's every-turn re-injection, arrived at
independently from the human's side.

**3. THE PROCESS IS INTERROGATIVE.** *(L11)* It brainstorms **with** the human and never solves **for**
them. ⛔ It never invokes the `brainstorming` skill.

**4. ⭐ EVERYTHING THE MACHINE WRITES IS A BEST GUESS, AND THE SCREEN SAYS SO.** *(L12)*
*"All things written are not written as definitive, they're written as best guesses and denoted as such —
'here's my best guess', or 'below are the best guesses that I have, please give your approval or edits.'
Otherwise our tech-illiterate person is not going to realise that they COULD actually make edits. They don't
understand."*
⇒ The denotation is not humility, it is **an affordance**: without it the beginner does not know editing is
allowed, and silently accepts everything.

**5. ⭐ A DESIRED OUTCOME SHOWN TO A HUMAN IS WRITTEN IN THE FUTURE TENSE.** *(L16, the owner 2026-08-06.)*
⛔ NOT *"four readers have gone at the plan and you've been handed every disagreement"* — that is written as
though it already happened, and to someone who has not done this before it reads as confusing at best and as
a false claim at worst. ✅ **"Four readers WILL GO at the complete plan, and you WILL BE HANDED every real
disagreement they find."** The outcome is a promise about what is coming, made before the work starts.
**Back-propagated to every phase, 2026-08-06.**

**AND THE COROLLARY ON WHAT GETS WRITTEN AS SETTLED** *(L13)*: **only DESIRED OUTCOMES** — the skill's and
each phase's — are recorded as definitive. Steps, methods and wording are recorded as provisional.
*"We know that this first version is just that — it's V1. There's going to be a V2 and a V3 and a V4. So all
we're really trying to lock definitively is the high-level desired outcomes."* ⇒ **Because the chain loops
(§7a), a later pass must never read a step list as sealed just because a session once wrote it down.**

---

## 8g. ★★ THE PROMPT LIBRARY — a fresh prompt per phase, and the DATA LAYER owns it

> **owner, 2026-08-06, `authority: user`.** *"Pretty much for sure there's going to be a new prompt that
> gets injected for each phase — a fresh one. Where is that stored, in a prompt library? What is that
> prompt? Is it tuned correctly for the desired outcome of that phase?"*

**Every phase loads its OWN prompt, fetched from a prompt library, at phase entry.** Some of it is common
to every phase (*you are an interrogative helper…*); most of it is specific to that phase and is **tuned to
that phase's desired outcome**.

⭐ **THE REASON IS CONTAINMENT, NOT ORGANISATION.** *(owner: "we never let the LLM get a whiff of where
we're going at the end, or of the next steps along the way, because then it tries to skip steps. So we're
re-injecting fresh prompts to limit what the LLM knows that it can do.")*
⇒ **The prompt is scoped to ONE phase and shows nothing beyond it.** A model that can see the finish line
optimises toward it and quietly drops the steps it judges redundant. *(Independently arrived at here, and
identical to `skill-building-sop.md` §IV.6's barn-sour rule and §II.2's blind-the-arc — a model shown the
whole sequence starts triaging across it. Two routes to the same law.)*

**WHO OWNS IT: THE DATA LAYER.** *(owner, deciding it in the same breath: "I don't know if it's the data
layer or the business layer, but we need something that's tracking what the prompt is that's being injected
in each phase… I think it would be the data layer.")* ⇒ **A prompt is stored state, fetched at a boundary —
that is the data layer's job.** The parallel is exact: **the business-logic reader owns the code/LLM seams;
the data reader owns the prompts** — where each one lives, whether it exists, and whether it is tuned to the
outcome of the phase that loads it.

**What BUILDER PHASE 4's DATA reader must therefore check, per phase:** does a prompt exist · where is it
stored · is it scoped to this phase only, leaking nothing about later ones · is it tuned to THIS phase's
desired outcome.

### 📍 WHERE THE PROMPT LIBRARY LIVES — decided 2026-08-06

**`.claude/skills/<skill-name>/prompts/`, one file per phase** (`phase-1.md` … `phase-N.md`).

**Why a fourth folder rather than one of the three conventional ones.** `skill-building-sop.md` §II.6 carries
Anthropic's shipped convention — **`scripts/` = run it · `references/` = read it into context when needed ·
`assets/` = files used in output** — and the folder itself is the signal, never an in-file tag. A per-phase
prompt fits none of the three cleanly: it is not documentation a session consults when it happens to need
it, and it is not an asset that appears in output. **It is an instruction set loaded at a fixed boundary,
every run, exactly once.** `.claude/skills/ingest/` already sets this precedent by giving `phases/` its own
first-class folder for the same reason.
⚠ **This EXTENDS the three-bucket convention rather than following it** — a real choice, recorded as one.

**What BUILDER PHASE 3 does about it TODAY — deliberately light** *(owner: "we don't have to say what it's
injecting, but it can just say: the first step is, this prompt is injected for this phase"):* **the first
step drafted for every phase is always the same line** — *the prompt for this phase is fetched from the
prompt library and injected.* ⛔ **The prompt's CONTENT is not specified yet, and inventing it now would be
guessing.**

---

## 8f. ★ THE TURN-CLOSING FORK — the two answers every turn ends on

> **owner, 2026-08-06:** *"At every turn when they're going through, it's going to ask at the end: is this
> good enough, or should we… it needs a fork decision A or B. Do we move forward, or do you want to repeat
> this and refine it more? That's the two options. **We need to think about this when we're creating the
> programming for this in the future — once we program the spec document, that's what the code is going to
> be looking for. That's the two inputs the code would be looking for.**"*

**Every turn ends by offering exactly two answers:**

```
A — Keep refining this.        (we stay here and sharpen it)
B — Lock it and move on.       (this is good enough; the next phase opens)
```

⭐ **THIS IS THE SEAM, AND IT IS ALREADY IN THE RIGHT SHAPE.** `skill-building-sop.md` LAW 1: code hands the
model a bounded set of outcomes, the model picks a member, code enforces membership fail-closed. `A | B` is
that closed vocabulary, and the owner named it as the thing future code will read. **What it still owes: a third
member meaning NO OUTCOME WAS REACHED** — the human answered something that is neither A nor B — so that
"they didn't decide" can never be spelled the same way as "they said move on."

---

## 8h. ★★ THE FOUR HANDOFFS — what crosses each seam, and what "nothing came back" looks like

> **`skill-building-sop.md` LAW 1 (line 199):** code hands the model a bounded set of outcomes; the
> middle is unbounded; what comes back is one of those outcomes, **and the set must contain a member
> meaning NO OUTCOME WAS REACHED.** **LAW 1b (line 369)** adds the second axis: a seam also has a
> **REACH**, and *"an unreachable model is not a clean result"* — `unreachable · errored · rate-limited ·
> timed-out · malformed · empty` map onto the no-outcome member, **NEVER onto the clean one.**

⛔ **THE WHOLE CHAIN IS SESSION-REACH. It must never be scheduled.** Every one of the four seams below
stops for a human, so none of them survives `claude -p` or cron. A background path would skip the human
step and report success — the exact failure LAW 1b names.

| # | seam | what is passed | the bounded set that may come back | the NO-OUTCOME member | reach |
|---|---|---|---|---|---|
| **S1** | builder → **`/autoplan`** (`5.5`/`5.6`) | the finished spec **plus an explicit path pointer** to `system/sops/skill-building-sop.md` | `PLAN-CITES-SOP` · `PLAN-NO-CITATION` | **`NO-PLAN`** — no file written, tool unreachable, or empty return | SESSION |
| **S2** | builder → **`/build`** (`5.9`) | the returned plan | `CLOSED-ALL-GREEN` · `CLOSED-WITH-GAPS-NAMED` | **`NO-CLOSE`** — the build never reported | SESSION |
| **S3** | builder → **the tester** (`5.10`) | the built skill | `TESTER: PASSED` · `TESTER: FAILED` | **`TESTER: NO-TESTER-RAN`** | see below |
| **S4** | builder → **the human** (BUILDER PHASE 6) | the handoff written into the brief | `A` · `B` | **`NO_OUTCOME`** | SESSION only, **by construction** |

### What is actually ENFORCED today — measured 2026-08-08, not assumed

**S4 is LIVE and is the only fully-closed seam.** `scripts/fork.py` enforces membership fail-closed
across **9 call sites** — one in each of the six drivers, two each in `5-build.md` and `6-live-run.md`.
Exit `2` = `NO_OUTCOME`; exit `3` = `DECIDED-BUT-NOT-RECORDED`, a distinct member added when `fork.py`
was made to persist the human's decision. A human cannot be reached headlessly at all, so **S4's reach
is NONE outside a session** — which is why the chain cannot be scheduled.

**S3 IS ALREADY WRITTEN AND IS NOT CALLED.** `scripts/phase-contract.json` phase `5` already encodes the
exact closed vocabulary — a `tester-verdict` row matching `TESTER:\s*(PASSED|FAILED|NO-TESTER-RAN)` and,
better, a `no-fake-pass` row that REFUSES hedge-words (`assumed|probably|likely|n/a`) posing as a
verdict. ⛔ **Nothing in the chain invokes `phase_gate.py`** — measured: zero hits for `phase_gate`
across all six drivers and `SKILL.md`. It is a built key with no lock turned. **`/skill-tester` is ruled
CUT (owner, 2026-08-07), so `NO-TESTER-RAN` is the LIVE value, not a fallback** — and the whole point of
naming it a member is that an untested skill can be recorded honestly instead of cleanly.

**S1 IS NOT ENFORCED, and the thing that looks like enforcement is not.** Step `5.6` says *"confirm the
returned plan ACTUALLY CITES the SOP"* — that is prose. `phase-contract.json`'s `sop-cited` row matches
`SOP-CITED:\s*(yes|true)`, **a token the model types about itself**; `phase_gate.py`'s own docstring
classes that shape as ⛔ `DECLARED UNCHECKABLE`. Nothing today reads the plan artifact and confirms a
literal citation is present. ⭐ **The fix needs no new primitive:** `system/parts/section_present.py`
takes a rules file and checks a required section/marker is present in an artifact — a bare presence rule
on the literal `skill-building-sop.md`, run against the returned plan file, closes S1. *(That part has
**zero callers** anywhere today — true of the part, not a reason to avoid it.)*

**S2 IS AN HONEST GAP AND IS RECORDED AS ONE.** `system/parts/completeness_receipt.py` can close the
**omission** half — set-diff the plan's own `Phase ▸ Feature ▸ Task` ids against the ids the close
mentions, catching the *"a task you simply don't mention"* failure `/build` names in its own honest-close
section. It **cannot** close the **false-✅** half: a task marked ✅ while incomplete still cites
cleanly. ⛔ **No part in the library closes that second half**, and this spec does not pretend otherwise —
per `skill-building-sop.md` §V.7, an honest *"this cannot be mechanically gated"* is a correct answer and
a phase forced into a fake artifact is worse than an ungated one. **Do not paper this over with a
self-reported field; that is exactly what makes S1 unenforced.**

⚠ **A STALE CALLER CLAIM IN THE RULEBOOK, found while measuring this.** `skill-building-sop.md:854`
names `ingest_coverage.py` as a caller of `completeness_receipt.py`. **Checked both candidate paths
(`shared/tools/` and `system/tools/`) — zero hits in each.** The rulebook is asserting an adoption it
does not have, which is §V.4d (a claim's proximity to a thing is not evidence about that thing) inside
the document that defines §V.4d. Left in place and dated here rather than silently corrected, because
the SOP is another project's surface.

---

## 9. WHAT THE HUMAN ANSWERS vs WHAT THE BUILDER DRAFTS

| Slot | Who | Why |
|---|---|---|
| The whole skill's desired outcome | **Human, alone.** Builder may propose a phrasing, flagged as a guess. | It is the felt result — only they hold it. |
| The phase list | **Builder drafts; human corrects.** | Cheap to guess, cheap to correct. |
| Each phase's desired outcome | **Builder drafts ALL of them together; human corrects.** | Composing four from blank is the load this method removes. |
| Each step's outcome + LLM/HUMAN tag | **Builder drafts; human corrects.** | Subtle, and the human should not learn the taxonomy. |
| The optionality — what the human is OFFERED at a decision point | **Human.** | the owner's keep/explore/toss is the worked example of why. |
| Any decision that was LOCKED once, then silently dropped or shrunk | **Leads the Q&A, first, never guessed.** | A guess here silently encodes a fiction as spec. |

---

## 9a. THE PROCEDURE — the question sequence that runs inside the phases

> **Rolled up 2026-08-05 from the `SOP DRAFT — CREATING A SKILL`** that had been parked in
> `state/projects/ingest-skill/brief.md`'s scratchpad. **That draft is now SUPERSEDED by this file.**
> It was the ancestor; this is the live document.

**Before anything — MINE, DON'T ASK COLD.** Pull everything already on disk that bears on this skill —
prior journal entries, records, canon, and the shipped files themselves if code exists — *before* opening
a single question. Asking a human what a system already knows is a defect.

**Step A — the whole skill's desired outcome** *(BUILDER PHASE 1)*. Human-authored, human alone. The
builder may offer a first phrasing but **must flag it explicitly as a guess and ask for their own words
back.** Check it reads as a felt result — *"I know this landed when ___"* — not a mechanism.

**Step B — the phases** *(BUILDER PHASE 2)*. The builder drafts a candidate list from mined sources plus
the shape of the work, numbered, each with a one-line reason. The human reorders, merges, splits, renames.

**Step C — ★ EACH PHASE GETS ITS OWN DESIRED OUTCOME.** Load-bearing, not optional. **Ask it even when the
phase looks self-evident — that is exactly when it gets skipped, and exactly when it bites later.**
*(the owner named skipping this as the step he most wished he hadn't.)* **A phase with no stated outcome
cannot be graded, and its steps get INVENTED rather than DERIVED.**

**Step D — the steps, tagged** *(BUILDER PHASE 3)*. The builder drafts the step list with a tentative type
per step; the human corrects. **This is where a correction-loop and a round-repeatable step get conflated
if nobody checks** — and this project MEASURED that bug living there. For any repeating step, confirm all
four parts exist: **the offer stated verbatim + a recommendation · the per-round yield · the exit backstop ·
what carries between rounds.** A missing one is how that loop dies later.

**Step E — ⚖ STRUCK 2026-08-06.** This step used to require filling `producer-spec-template.md` §5 (the
completeness grid) for every phase. **No locked step in §3–§7a ever performed it**, so the spec was claiming
compliance through a mechanism nothing could reach — the exact failure §V.4d names, committed by this file
about itself. **the owner's ruling:** the grid was his own way of THINKING about skills, never a step; and
**BUILDER PHASE 4's four readers already are the grid** — data, business logic and presentation are its
rows, and the chronology reader walks its columns. The mental model is kept as §0a; the requirement is gone.

**⭐ GATE THE PHASES AS YOU GO.** Do not show a phase's derived grid, or the next phase's candidate list,
before the current phase's desired outcome is locked. **Showing the finish line early pre-writes the
answer.**

### Interrogative style — every question this method asks
- **Numbered, answerable by number**, each carrying the builder's best guess in parens. ⛔ Never a bare
  open question when a guess is possible.
- **Batch 2–3 when genuinely independent; ONE at a time when the next question depends on this answer**,
  or when one phrase forks into readings that would flood a first-time answerer.
- **The plan is confirmed before producing** — the human sees and confirms the phase list before any step
  or grid work starts on it.

---

## 9b. THE FOUR RULES MINED FROM WHERE THE METHOD ITSELF BROKE

> **📎 SOURCING — added 2026-08-06 so nobody has to guess.** These rules are **DERIVED BY A SESSION** from
> real dated incidents. They are **NOT the owner rulings** — unlike §8/§8a/§8b/§8c, which carry his verbatim
> words and his approval. The incidents behind each are real and checkable; the *generalisation from
> incident to rule* is a session's work and has never been ratified.
> **Why this label exists:** in this system a line that reads like a ruling gets obeyed by every future
> session. `/ingest`'s PHASE 3 outcome sat in a spec looking locked when it was a session's guess, and it
> took a full audit to catch. **A rule stating its own provenance cannot do that.** Treat these as strong
> defaults, revisable by the human at any time (§1a: nothing is untouchable because it was decided once).

> Each is a real mistake made while running this method on `/ingest`, kept with its origin attached —
> **a rule with its origin attached doesn't get re-litigated.**

**1. NEVER SELF-AUTHORIZE A DESIGN CALL ON THE HUMAN'S BEHALF, even hedged as "he can veto."** A session
wrote *"two design calls I made on the owner's behalf"* — and a different session, working the same project,
had independently recommended the OPPOSITE. ⇒ **When a spec-authoring session notices a design question
nobody has ruled on, it SURFACES THE CONFLICT for the human to break. It does not pick a side and record
it as done.**

**2. STATE EVERY DROPPED OR SUPERSEDED RECOMMENDATION EXPLICITLY, IN THE TURN IT'S DROPPED.** A session
recommended wiring two tools into a seam; the build shipped different gates instead, and nobody said the
original had been dropped. A grep found them later still unwired — *"an unused promise."*
⇒ **A session that changes its own prior recommendation must say so in the same breath. Silence reads as
both having happened.**

**3. WHEN A LOCKED RULE TURNS OUT TO HAVE CAUSED THE FAILURE IT EXISTS TO PREVENT, AMEND THE ONE CLAUSE
THAT'S WRONG — dated, in place.** ⛔ Do not discard the whole rule; ⛔ do not leave it standing. The locked
*"one line per item, never a paragraph"* was meant to stop walls of text and **caused the exact truncation
defect it was credited with preventing**, because it conflated two concerns. ⇒ **Before ratifying a clause
pulled from an existing locked rule, ask whether the rule AS LITERALLY WRITTEN could itself be the cause
of a failure it's credited with preventing — and if so, isolate and amend only that clause.**

**4. CROSS-REFERENCE EVERY MINED DECISION AGAINST THE CURRENT SHIPPED ARTIFACT — history alone lies by
omission.** Two LOCKED decisions were quietly reduced across a restructure and nobody noticed for weeks:
a ten-type taxonomy read as flattened to two booleans, and the artifact the skill is NAMED for stopped
being mentioned at all. ⇒ **Before drafting phases or outcomes, run a DECISION-REGISTER PASS: every locked
decision touching this skill, diffed against what is actually shipped today. Every unresolved delta becomes
a LEADING Q&A question, never a silently inherited assumption.**

⭐ **THE FIFTH, EARNED 2026-08-05 BY THE FIRST REAL SWARM RUN:** **the builder cannot review its own spec.**
Four blind readers over a document written by one session in one night produced **12 unique findings, seven
of them drift that session had created hours earlier in the same window.** ⇒ **Writer ≠ verifier applies to
specs, not just code.** And: **a reader can be confidently WRONG** — one quoted a stale docstring to claim a
field could never render, when it had been added and demoed that evening. **Verify every finding against
the source before acting on it.**

---

## 9c. DEFINITION OF DONE — for ONE Q&A session

> **📎 SOURCING, added 2026-08-06:** this checklist is **DERIVED BY A SESSION** from the template's own
> requirements. **the owner has not reviewed it item by item.** Same reason as §9b's label — it reads as locked
> and is not. Revisable by the human at any time.

- ⚖ **STRUCK 2026-08-06** — this bullet required every `producer-spec-template.md` section to be filled or
  explicitly marked not-active. It depended on §9a Step E, which is struck for the same reason: no phase
  ever performed it. See §0a for what was kept.
- **Every phase carries its own one-line desired outcome, stated as a felt result** — not inferred from
  its steps.
- Every step carries its type tag, and every repeating step names all four required parts.
- **The decision-register pass (9b rule 4) RAN before drafting started**, and any unresolved
  locked-decision delta was asked as a LEADING question, not a trailing one.
- **The human has SEEN and signed off on the completed grid — never authored it from blank.**
- **Length check:** every clause traces to a stated need or a dated failure — not exhaustiveness for its
  own sake. **A stale 400-line grammar applied with confidence is worse than a short one someone reads.**

---

## 10. OPEN — not yet decided

> ⚠ **A resolved item left live in this list gets re-investigated and re-done from scratch — this repo's
> own doctrine names that the #1 time-waste.** Items 5 and 6 below were resolved elsewhere in this file;
> they are struck in place, dated, and pointed at where they were settled — never deleted, never left live.

1. ✅ **RESOLVED 2026-08-06 — where the method lives.** **THIS SPEC is the method's home**, and the skill is
   built from it. The SOP stays ONE file and gains the three named sections (§7). *(`[SB-HOME]` closed.)*
2. **The library of parts** — ~~4 of 5 catalogued primitives are unbuilt.~~ *(`[SB-PARTS-SHELF]`)* ~~**Still
   open: the section is ruled, the shelf is still empty.**~~
   > ⚖ **CORRECTED 2026-08-08 [F3.6]** — same measurement as §7's MEASURED STATE correction above: **5 of 5
   > named primitives resolve on disk, and the library holds 19 built primitives total** — the shelf is not
   > empty. **What is genuinely still open:** whether MORE primitives should be built beyond the 19, and
   > whether the SOP's own profile of the library (which still only writes up a subset of the 19) should be
   > expanded — the factual "shelf is empty" claim does not hold and should not drive that decision.
3. **A slot for the optionality** in the method draft — it has none today. *(`[SB-OPTIONALITY-SLOT]`)*
4. ✅ **RESOLVED 2026-08-06 — BUILDER PHASE 5 and the SOP are NOT the same thing.** Phase 5 is the CHAIN
   (SOP check → `/autoplan` → `/build` → tester); the SOP is what the chain checks the plan against. the owner's
   2026-08-05 lean that they "should probably be one and the same" resolved the other way once the chain was
   named.
5. ✅ **RESOLVED 2026-08-08 [F3.6] — the CUT ruling.** ~~The tester the chain ends in does not exist yet — the seam points at
   `system/tools/conformance-lab/` and per-skill `verify-*.sh` until `/skill-tester` ships. the owner's ruling
   owed on whether that stands.~~ **`/skill-tester` is ruled CUT (owner, 2026-08-07)** — `NO-TESTER-RAN` is
   the permanent LIVE value for seam S3, not a placeholder awaiting a future tester. See §8h ("What is
   actually ENFORCED today — measured 2026-08-08") at :1662. Struck 2026-08-08 [F3.6].
6. ✅ **RESOLVED 2026-08-08 [F3.6] — settled by §7a's own locked step list.** ~~BUILDER PHASE 6's own steps are not
   specified — the phase and its outcome are ruled (§7a); its turn-by-turn structure is BUILDER PHASE 3 work
   and has not been done.~~ **This was already stale when written:** §7a carries "THE LOCKED STEP LIST —
   BUILDER PHASE 6" (owner, 2026-08-06: *"Yes, this is good. Let's push it to the spec document. It's now
   complete."*) — 16 steps, 6.0 through 6.15, ratified the same day this item was drafted. Struck 2026-08-08
   [F3.6].
7. ❓ **A FIFTH READER FOR THE HUMAN-IN-THE-LOOP LAYER — proposed 2026-08-06, NOT RULED.** The swarm has one
   reader per architectural layer, but the fourth layer (🤝, §8d) was named the same day and **nothing in
   the swarm is charged to grade it.** The presentation reader asks *is the human taught*; no reader asks
   **what is expected back from the human, and is that expectation reachable** — is every human turn
   answerable by someone who was not in the room · does every fork name its valid answers · is any turn
   ceremony with no real decision in it · is the human asked anything outside the four undecidables.
   **The session's recommendation is YES** (the layer exists precisely because the other three could not
   supply or verify it, which is the same reason they cannot grade it). **the owner has not ruled. Do not build
   it until he does.**

---

## 11. LIVE STATE — the `/ingest` proving run

> **⚖ REWRITTEN 2026-08-08 (night) on the owner's approval.** The prior text of this section said *"BUILDER
> PHASE 2: IN PROGRESS, NOT FINISHED · BUILDER PHASES 3, 4, 5, 6: not started."* **That was three phases
> stale** — BUILDER PHASE 2 closed on 2026-08-08 by the owner's ruling and the run is at BUILDER PHASE 5.
> ⭐ **The section built to stop the method evaporating had itself gone stale.** Recorded, not hidden.

### Where the proving run actually is

**BUILDER PHASES 1–4: ✅ RUN.** `/ingest` was put through the chain on 2026-08-08 via **door two** (the
remedial pipeline): outcome → phases → steps → the four-reader tension swarm. **It produced a ratified
spec** (`.claude/skills/ingest/SPEC.md`) **and 24 named defects with `file:line` anchors.**

**BUILDER PHASE 5: ✅ COMPLETE 2026-08-09.** Steps 5.1–5.8 ran on 2026-08-08 (rulebook check · `/autoplan`
returned a plan · the S1 seam gate returned `PLAN-CITES-SOP`, exit 0). **Step `5.9` fired on 2026-08-09:
`/build` executed Phase 9 of `~/.claude/plans/ingest-skill.plan.md` — 25 of 26 tasks built and
independently verified, ~1,640 lines across 9 files plus two new tools** (`d0b4a18` · `b1dfde0` ·
`f370dd7`, plus a Phase 10 generalization).
⛔ **CORRECTED 2026-08-11. This section previously asserted "the chain has NOT changed one line of
`/ingest`" and cited a git check to prove it. That was true when written on 2026-08-08 and FALSE by the
next evening** — seven commits have landed since. ⚠ **This section was itself REWRITTEN on 2026-08-08
BECAUSE IT WAS STALE, and it went stale again within two days. Same file, same failure, third occurrence.**
⭐ **The lesson is not "update it more often" — it is that a LIVE-STATE section hand-maintained in a spec
will always lag the work it describes. If a future session wants to fix this properly, the fix is a
generated pointer, not a better paragraph.**

**BUILDER PHASE 6: ⬅ THE ONLY THING LEFT.** the owner opens a fresh window and runs `/ingest` on one pile.
No task precedes it and none is needed — `/build` has already run. **That single act is both the world
map's first real acceptance test (no human has yet seen it work) and BUILDER PHASE 6 itself.**

⇒ **the owner's bar for DONE — *"we've taken a pre-existing skill, we've run it through the skill-builder, and
the whole process ran"* — is ONE STEP from being met.** Five of six phases have run on a real
pre-existing skill. **The build is done; only his own run remains.**

---

### 11a. ⭐⭐ WHAT THE PROVING RUN TAUGHT — the four failure modes the METHOD committed ON ITSELF

> **Harvested 2026-08-08 from `state/projects/ingest-skill/brief.md` and its `.pad-archive.md` — 68 distinct
> method findings, of which these four are the ones that must change how the builder BEHAVES.**
> ⛔ **All four are UNRESOLVED — logged, never built into a rail.**
> ⭐ **THE ROOT CAUSE, named by the session that committed it:** *"the session had the answer available and
> put the load on the human anyway — the exact failure mode `/skill-builder` exists to prevent, committed by
> `/skill-builder`."*

**① PERFECTION LOOPING — THE OWNER'S OWN WORDS.**
> *"You're perfection looping. But we've run out of context window."*

**Measured:** the same decision screen re-rendered **five times**; rulings requested that the session could
have derived itself; **nothing built in ~700k tokens.** ⛔ **The A/B fork currently makes looping the
cheapest move and nothing pushes back.** **OWED: a build-forward bias** — once a screen has been corrected,
the next turn ADVANCES; it does not re-render for re-approval.

> ## ⭐⭐ RAIL ① IS NOW PROVEN, NOT OBSERVED — a controlled comparison, 2026-08-09
> **The plan that shipped 25 of 26 tasks was IDENTICAL to the plan that shipped nothing the day before.**
> **The only variable was the MODE: entering `/build` instead of re-rendering a screen.**
>
> | | 2026-08-08 | 2026-08-09 |
> |---|---|---|
> | the plan | Phase 9, 26 tasks | **the same Phase 9, unchanged** |
> | what the session did | re-rendered the decision screen five times; asked for rulings it could have derived | entered `/build` |
> | context spent | ~760k tokens | — |
> | `/ingest` files changed | **ZERO** | **9 files, ~1,640 lines, two new tools** |
> | tasks completed | **0 of 26** | **25 of 26, independently verified** |
>
> ⭐ **THIS IS THE STRONGEST EVIDENCE THIS PROJECT HAS PRODUCED, and it is why the rail is a RAIL.** Same
> plan, same skill, same operator, two modes, opposite outcomes. **The method was never broken — the MODE
> was.** A rail carrying a controlled comparison survives a rewrite; a rail carrying an anecdote gets
> deleted by the next session that finds it inconvenient.
> ⚠ **STATED BOUND, so nobody overclaims it:** n=1, two consecutive days, one operator, one plan. It is a
> natural experiment rather than a designed one — the confound (a different session, a fresher context)
> cannot be fully separated from the mode change. **It is strong because the PLAN was byte-identical, not
> because the trial was controlled.** Do not cite it as measured effect size; cite it as what it is.
> **Recorded 2026-08-11 from `state/projects/skill-builder/brief.md`'s own 10,000-ft rung, which had
> already flagged that it belonged here:** *"that is a `/skill-builder` finding, not a session mood, and it
> belongs in its SPEC."*

**② MANUFACTURING QUESTIONS — THE OWNER'S OWN WORDS, twice in three turns.**
> *"There's no fucking questions here dude, come on man."* · *"Don't make shit up for me. Don't make up busy work."*

**OWED: a rail that requires PROVING a question is undecidable by the machine before it reaches the human.**
The test, drafted at the time: *"can I settle this by reading one more file, or by choosing the cheaper path
and recording it? If yes — do that instead, and tell him what you did."*

**③ A QUESTION WITHOUT ITS CONTEXT — THE OWNER'S OWN WORDS.**
> *"It's just too abbreviated with no context and too short for me to understand and possibly make a decision on."*

**OWED: every question put to the human carries the situation, both options, and what each costs.**
⚠ **This is the same defect the swarm's PRESENTATION reader exists to catch — committed by the session while
it was reporting that swarm's results.**

**④ THE LOCKED VISUAL GRAMMAR GETS DROPPED BY REWRITES — THE OWNER'S OWN WORDS, TWICE.**
> *"You lost the presentation layer elements that we had locked in."* · *"We lost the thing where we're showing
> the emoji for the presentation, the data layer, the business logic layer… That's locked in our output style
> and it's not showing up."*

**OWED: a rewrite may never drop the locked look.** ⭐ **The standing instruction both times: FIX THE
TEMPLATE, NOT THE INSTANCE.**
⚠ **Correction attached, because the fix was itself wrong once:** there are **THREE layers, not four** —
💾 data · ⚙️ business logic · 🖥 presentation. **The human turn is an ACTOR (🙋), not a layer.** A session had
added it as a fourth; the owner corrected it.

> ⛔ **THE PROOF THAT THESE MUST BE RAILS AND NOT NOTES: ① and ② were committed AGAIN on the night of
> 2026-08-08, in a session that had already read them.** Third occurrence. A rule that is only written down
> is a rule that gets broken by the next window.

---

### 11b. THE FULL HARVEST — where the other 64 findings live

⛔ **DO NOT RE-DERIVE THESE. They are recorded and line-cited.** The raw record is deliberately NOT copied
here — the spec carries the LESSONS, the brief carries the TRANSCRIPT, and duplicating it would create two
sources that drift apart.

- **`state/projects/ingest-skill/brief.md`** (Drive) — 82 mentions of the builder / BUILDER PHASE.
- **`state/projects/ingest-skill/brief.md.pad-archive.md`** (Drive) — 31 mentions. ⭐ **Lines 843–1119 are
  the raw dry-run transcript** — rounds 1 through 5, **the owner's rulings verbatim with the builder's wrong
  guesses left visible and corrected.** That range is the single richest record of the method working.

**What the harvest confirmed as RATIFIED doctrine** (already in this spec, listed so the harvest's coverage
is checkable): a phase is a unit of human attention · the prescription budget — only desired outcomes are
prescriptive · everything the human can respond to is NUMBERED, because the human DICTATES · the builder
drafts all phase outcomes together and the human rules by exception · the swarm finds tensions and never
decides · `SPEC.md` is the ONE definitive home.

**Still UNRESOLVED beyond the four above, from the same harvest:** `order_lint.py` returned a green pass on
a check that had no applicable rule (*"a green light from a check that did not run is worse than no check"*)
· this spec is missing 4 of its own declared 11 template sections and reuses their numbers · no table of
contents at ~1,900 lines where the SOP asks for one over ~300 · **door two's BACKUP RAIL is ratified but
NOT BUILT** (owner: *"back up the original code and instructions"* → freeze to
`.claude/skills/_archive/<skill>-<date>-pre-<reason>/` with a `STALE.md`).
