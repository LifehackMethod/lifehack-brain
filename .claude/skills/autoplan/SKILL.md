---
skill: autoplan
title: "Autoplan — plan against what the system actually is"
shape: interactive-workflow
status: active
description: "Build or amend a project's plan. Explores the real system before writing, then writes into that project's ONE living plan file — never a new one. Fires on \"/autoplan\", \"make a plan\", \"update the plan\", \"add this to the plan\", \"plan this\"."
summary: |
  The surveyor. It maps the ground before it draws the map — never planning from memory and never from
  the conversation alone — then amends the one plan file that project has always used. It reserves the
  person for the things only they can supply: a real fork between viable approaches, a contradiction
  between what they asked for and what the system is, a scope cut. It plans; it never executes.
triggers: ["/autoplan", "make a plan", "update the plan", "add this to the plan", "plan this"]
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Task]
created_at: 2026-07-28
updated_at: 2026-08-11
---

## Intent (§0.5)
**User outcome:** a plan built on what the system *actually looks like right now*, written into the ONE
plan file that project has always used — sharpened and grown, never forked into a new file they will
lose. **Bar:** *"it planned against reality, it went in the same place as last time, and it told me when
it hit something I needed to decide."*
**Role:** the surveyor. It maps the ground before it draws the map. **Human-in-the-loop by design** — it
reserves the person for a genuine fork, a contradiction, or a scope cut, and decides everything else
itself. Its fence: **surveyor, not builder.** It plans; it never executes.

# Autoplan

## Why this exists — read once

The harness's plan mode assigns **a new plan file per session**, named from the first few words of
whatever prompt triggered it. The slug is cached against the session id; a fresh window always mints a
fresh file. It is **by design**, and no setting points it at an existing plan.

Measured on one real system: **63 plan files, 41 of them prompt-named, 47 belonging to no project** —
`update-teh-plan-gleaming-liskov.md`, `add-to-the-plan-majestic-dove.md`. Every one of those is somebody
asking to *update the plan* and getting a new file instead.

**So this skill does not use plan mode to hold a living plan. It owns the file itself.**

⛔ **Never enter plan mode to hold a living plan.** It will mint a new file and your amendment lands
there instead of in the project's plan. Edit the plan file directly.

## Paths (set once)

```bash
ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)"
DATA="$(python3 "$ROOT/shared/brain_root.py" --quiet)" || {
  echo "STOP: nobody has said where their notes live yet."
  echo "Ask them, then: python3 $ROOT/shared/brain_root.py --set \"<that folder>\" --create"; exit 1; }
```

**Plans live at `$DATA/plans/`.** They are something the person wrote, so they live with the rest of
what they wrote — not in this repo, and not mirrored anywhere. There is one copy.

## The naming rule — the whole failure this skill prevents

- **A live plan is `$DATA/plans/<slug>.plan.md`.** One predictable name, every project, forever. That
  is what the check-in, the save handoff and the status bar all resolve against.
- **A retired plan is `<slug>.plan.<YYYY-MM-DD>-retired.md`** — renamed exactly once, at the end of its
  life. **Retirement is the only renaming operation there is.**
- **There is deliberately no way to mint a second live file.** A version slot at *creation*
  (`<slug>.v2.plan.md`) would be a fork button and would re-open *"which one is live?"* — the disease
  this cured. **Versioning on the way out is a one-way door; on the way in it is a fork.**
- **A date, not a `v2`.** A version number needs you to know the sequence; a date sorts itself and
  explains itself.
- **A standalone plan is `standalone-<name>.plan.md`**, same retirement rule. The prefix is what lets
  any future sweep tell a **deliberate** standalone from an **accidental** orphan at a glance.
- **Deleting a plan file is forbidden, absolutely.** Retirement renames; it never removes.

⛔ **Never a prompt-derived filename.** That is what produced the 47 orphans. A random name does not
disambiguate a plan from its project — **it hides which project owns it.**

## The steps

| phase | steps | what it does |
|---|---|---|
| `phases/1-resolve-and-explore.md` | 0 · 0.5 · 1 | resolve **where** the plan lands, load the world model, then explore the real system before writing anything |
| `phases/2-design.md` | 2 · 3 · 4 · 4.5 | design from what was found, declare the seam, review, stop if stopping is right, and tick what this session actually finished |
| `phases/3-write.md` | 5 · 6 | write the plan into the one file, then the efficiency pass |

## The rules that hold across all of them

- **One project, one plan.** A second plan file for the same project is the failure, not a convenience.
- **Never plan from memory.** Re-anchor to the live brief and the live plan first, every run.
- **Verify, don't assert.** Replace every *"probably"* and *"should be"* with a fact you read this
  session. An unresolvable unknown is a **stop**, not a hedge.
- **Say what you found, even when it is nothing.** Every step that comes up empty says so in one line.
  A silent pass and a pass that found nothing look identical unless the outcome is stated.
- **Finished work stays.** Mark it done; never prune, never compact. Long plans grown over time are the
  ones that survived — protect that shape.

## The three rules that bind a build, and where they live

**`system/build-rules-index.md` carries the code/LLM seam, the model-reach rule and the code-spiral
rule — once, and only there.** Read it at the design step. ⛔ **Do not paste a copy of any of them back
into this file.** They used to be inlined here *and* in `/build` *and* in the index, with two git hooks
comparing the copies byte for byte on every commit to stop them drifting. That is a mechanism for
keeping copies identical, not a reason to have copies.

## What this skill needs outside its own folder

| Needed | Why | Status |
|---|---|---|
| `shared/brain_root.py` · `shared/registry.py` | where the notes are, and which project this is | ✅ here |
| `system/hooks/pm_flag.sh` · `plan_flag.sh` | which project and plan are armed | ✅ here |
| `system/build-rules-index.md` | the three binding rule blocks, in one place | ✅ here |
| `.claude/agents/worker.md` | the read-only explorer | ✅ here |
| `system/sops/plan-sharpening-sop.md` | the shared world-model load and session mining | lands in T1.14 |
| `system/sops/architecture-planning-sop.md` | the plan's required shape | lands in T1.14 |
| `system/sops/build-conductor-sop.md` | the gear doctrine | lands in T1.14 |
| `docs/data-layout.md` | where plans and briefs live | ✅ here |
