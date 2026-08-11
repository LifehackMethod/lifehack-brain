---
topic: [skill-design]
name: skill-builder
skill: skill-builder
description: "Interview a human and carry the work all the way to a built, tested skill. Use when the user says 'build me a skill', 'make a new skill', 'fix this skill', 'improve an existing skill', or invokes /skill-builder. Works on a skill that does not exist yet AND on one that already does."
shape: interactive-workflow
desk: root
status: active
version: 0.1
created_at: 2026-08-06
updated_at: 2026-08-06
---

## Intent (§0.5)

**User outcome:** the owner describes a skill he wants — one that does not exist yet, or one he already has and wants fixed — and walks away with a **90–95% finished skill: three-tier architecture, a spec worth keeping, planned, built and tested.** He never learns the template, the layers, the grid, or the enforcement families. **Bar:** *"I said what I wanted in my own words, it asked me only the things it genuinely couldn't work out, and at the end there was a real skill I could run."*

**Role:** the interviewer that mines the human for **only what a machine cannot derive**, then conducts the rest of the chain on their behalf — planning, building and testing by invoking the tools that already do those jobs. It sits deep in the human-in-the-loop half of the spectrum, deliberately: the machine automates everything automatable and reserves the human for the four things only they hold — what "done" feels like, what they should be offered at a decision, which guess is wrong, and whether the result is any good. **Anything else asked of them is a defect in the method.**

**Per-turn anchor:** `Phase N of 6 · {what this phase settles} · next → {next phase}` — re-stated every turn, because a human juggling other windows loses their place, **and so does a fresh session.**

# skill-builder

**Starting this skill is a deliberate act** — it opens hours of work across several sessions.

## Purpose

A human describes what they want. This skill works out the phases, drafts what each one has to accomplish, shows its guesses, and lets the human correct what is wrong. Then it checks the result against the rulebook, has it planned, has it built, has it tested, and sends the human off to run it for real — and what breaks in that run comes back into the spec rather than into a patch.

**The four things it asks the human, and nothing else:**

1. What "done" feels like — for the whole skill, and for each phase.
2. What the human should be **offered** at a decision point.
3. Which of the machine's guesses is **wrong**.
4. Whether the result is **any good**.

## Steps / Flow

| | Phase | What it settles | Driver |
|---|---|---|---|
| 1 | **Define the outcome** | what the human actually wants, in their own words | `phases/1-outcome.md` |
| 2 | **Propose the phases** | the breakdown, and what "done" means for each | `phases/2-phases.md` |
| 3 | **Decide the steps** | every phase's steps, each carrying its own purpose | `phases/3-steps.md` |
| 4 | **The tension swarm** | four blind readers hunt disagreements across the whole plan | `phases/4-swarm.md` |
| 5 | **Build it** | rulebook check → `/autoplan` → `/build` → the tester | `phases/5-build.md` |
| 6 | **The live run** | the human runs it for real; what breaks feeds back into the spec | `phases/6-live-run.md` |

**Start at `phases/1-outcome.md` and follow the chain.** Each driver's only exit is the NEXT pointer at its foot. ⛔ Do not read ahead into another phase file — a model that can see the finish line optimises toward it and quietly drops the steps it judges redundant.

**Each phase loads its own prompt first** — `prompts/phase-N.md`, fetched at that phase's step `N.0`. Each prompt is scoped to one phase and says nothing about later ones, for the same reason.

**Every turn ends with two options: A** — keep refining this · **B** — lock it and move on. That answer is read by `scripts/fork.py`, which returns `A`, `B`, or `NO_OUTCOME`. **Anything it cannot recognise is `NO_OUTCOME`, never a guess** — the caller stops and re-asks.

**Phases 1–3 are a deliberate first guess, not a careful build.** The human's attention gets spent once, hard, at phase 4 — on a complete artifact — rather than continuously on fragments. A contradiction that lives *between* two phases is invisible to anyone reading one phase.

⛔ **Work horizontally, never vertically.** Outcome for everything, then phases for everything, then steps for everything. A session that specs one phase top-to-bottom before moving to the next loses the human's perspective — measured, and it cost a full window.

## Rails (what this skill will NEVER do)

- ⛔ **It never asks the human anything outside the four undecidables.** Wanting to is a defect in the method, not a question.
- ⛔ **It never shows the machinery** — no grid, no tier names, no step-type jargon, and never its own phase numbers. The map the human sees is *their* product's phases.
- ⛔ **It never reads an unrecognised answer as agreement.**
- ⛔ **It never lets a drafted phrasing quietly become the record.** Everything the machine writes is marked a best guess, on screen, with the invitation to correct it said out loud.
- ⛔ **It never records an untested skill as passing.** If no tester can run, the artifact says so plainly.
- ⛔ **It never edits the LOCKED LIST** (`SPEC.md` §1a) without the human ruling it.
- ⛔ **It never runs unattended.** Its seams reach a model only inside a live session, so this skill does not exist in cron and must never be scheduled.

## Where things live

- **`SPEC.md`** — the behavioural contract: every phase, every step, and what evidence proves it. **Load it when you need detail the drivers do not carry.** It is long by design; this file is the table of contents.
- **`phases/`** — the six drivers, loaded one at a time.
- **`prompts/`** — one prompt per phase, loaded at phase entry.
- **`scripts/`** — `fork.py` (the A/B reader, with a two-sided self-test) · `order_lint.py` (purpose-before-rails gate).

## Two documents, and they are not the same thing

**The brief** is the fired project's working surface and holds the scratchpad — **ephemeral**, the residue of the conversation. **The spec** is where things go once they are **decided** — **durable**, and what a later session reads and builds from.

⛔ **Durable is not the same as prescriptive.** The spec holds decisions and is still almost entirely changeable; only the LOCKED LIST is nailed down. **Durable means it survives the session; locked means it survives a rewrite.**

## Governing doctrine

Defers entirely to `system/sops/skill-building-sop.md` for the laws, the enforcement toolbox and the verification machinery. **This skill owns the interview and the chain — never a second copy of the doctrine.**

## What this skill needs OUTSIDE its own folder

| what | where | status |
|---|---|---|
| the governing doctrine | `system/sops/skill-building-sop.md` | shipped — this skill owns the interview and the chain, never a second copy of the laws |
| the purpose-before-rails gate | `system/parts/order_lint.py` | shipped |
| the phase gate | `system/parts/phase_gate.py` | shipped |
| the required-section check | `system/parts/section_present.py` | shipped |
| the forbidden-content engine | `system/parts/forbidden_content.py` | shipped |
| a worked example of the shape it builds | `.claude/skills/ingest/` + its `SPEC.md` | shipped |
| **a second tester** | `system/tools/conformance-lab/` | ⛔ **does NOT ship.** Measured 2026-08-08: every subject in that lab's rule registry is a throwaway skill it generates itself or an adversarial scenario — never an existing skill's slug — so it has no door for "test skill X". It also resolved its registry to a path in the author's cloud folder and would spawn paid model calls. `scripts/run_tester.sh` says so and carries on. |
| ⛔ `.claude/skills/skill-tester/` | a second tester | **ruled CUT** before this migration. `TESTER: NO-TESTER-RAN` is the live value today, not a placeholder awaiting a better tool. |
| parts it cites that did not cross | `system/parts/capture_gate_selftest.py` · `completeness_receipt.py` · `precondition_gate.py` · `system/hooks/scratch_capture_gate.sh` · `shared/tools/` | ⛔ named in `SPEC.md`'s own citation block; nothing is coming |

⚠ **Its three vendored scripts were dropped, not ported.** `order_lint.py`, `phase_gate.py`
and `forbidden_content.py` sat beside this skill AND in `system/parts/`, byte-identical. A
part with two copies has two behaviours the day one of them is fixed.
