---
skill: planning-weekly
title: Planning Weekly
shape: interactive-workflow
status: draft
description: Use when planning the week ahead with the person — "plan my week", "weekly review", "set my week", "what's my week". Walks eight interview stages from a morning machine picture to a confirmed, written-back week. Not for daily planning ("plan my day" does not fire this).
triggers: [plan my week, weekly review, set my week, what's my week]
created_at: 2026-11-20
updated_at: 2026-11-20
---

# Planning Weekly
### Turns the morning run's blurry machine picture into a confirmed, written-back week — the person keeps the pen throughout.

## Desired outcome

> **When I sit down to plan my week, most of the work has already happened.** The machine has read
> everything (maximalist intake) and arrives with a good but blurry picture of my life. In a very short
> time it takes that picture from low definition to 4K. It asks me only what lives in my head and nowhere
> else, round by round, never anything it could have looked up. The data is only dots; the picture — the
> threads, the judgment, the shadow information — is mine to give.
>
> **Then I commit ruthlessly little (minimalist commitment).** The machine can read far more than I ever
> could, but my week never gets any longer: it has 168 hours (24 hours × 7 days), and nothing the machine
> does adds one. *(Demir calls this "the 168-hour constraint": AI lifts the limit on how much can be read
> and tracked, never the limit on how many hours a person has to live and work in.)* So every choice runs
> through one question: *which outcome, if achieved, makes all other efforts easier, more impactful, or
> unnecessary?* I leave with a ranked list — if I can only do one thing, it's number one; if two, numbers
> one and two — planned for a body, not a machine (rest and recovery go in first), and a calendar I'd
> stand up and clap for.
>
> **I keep the pen.** The machine does all the work it can, surfaces problems honestly with a proposed fix,
> and never decides for me — sometimes the choosing is the point. Putting my life into words gives me
> clarity too.
>
> **Everything I confirm sharpens the machine.** My confirmed week becomes what every morning starts
> from, and the session's lessons — new filters, urgency changes, fixes to the diary — make next week's
> guess closer, so each session starts further ahead.
>
> **The bar:** *"It's all in one place I trust — I can turn my head off and glide the week."* And a fresh AI
> session could read my confirmed week and treat it as ground truth.

*(Locked by the person 2026-11-19, spec section 1, verbatim. No duration is promised — the person's ruling: "we shouldn't say how long it will take.")*

## Musts

- **Writes only through the doors:** every durable write goes through `gc answer` / `gc decide` / `gc backup` and the guarded calendar writes — never a raw file drop into the engine's state.
- **No Gmail draft or send.** Reply drafts are written only as markdown files (scratchpad § Write list rows); the person sends them themself.
- **Arithmetic by code, never in the model's head** — every number a decision rests on (capacity, fit check, read-back totals) is computed by a script and shown with its expression.
- **The planning desk is found through `shared/desk_list.py`, never a literal folder name.** The one place a desk path may exist is `scripts/desk.sh`.
- **A tier is named on every sub-agent spawn** (helpers SOP; tiers, never model ids). Exception, the person's explicit ruling 2026-11-20: the six Council advisors run on **Opus**.
- **No running on yesterday:** if no morning snapshot exists for today when the session starts, the session forces a fresh morning read rather than proceeding on the previous day's (coordinator's rule, 2026-11-20).
- **Nothing is written until the one "go".** Step 8.5's "go" is read by code; only then does the alone clerk stage submit the write list through the doors.
- **This spec is for everyone.** Roles, never one person's values: calendars, lanes, closing voice and desk names are read from the person's own layer at run time (spec §G, locked 2026-11-20).

## The zones (settled 2026-11-20 by the coordinator, from the old skill's own logic)

One definition only — every prompt and reference that names a zone points here or to `references/zones.md` (slice B), never redefines:

| Zone | Leverage | Urgency | What it means for the week |
|---|---|---|---|
| **Win-zone** | high | LOW | protect it — it goes in first, with a block, before anything urgent can eat it |
| **Must-deliver** | high | high | scheduled and delivered this week |
| **Shallow-trap** | low | high | feels urgent, isn't important — batch, delegate or cut |
| **Kill-or-push** | low | low | kill it, or push it out of the week |

Source: `_legacy/references/triage-guide.md` lines 30–41 and `_legacy/prompts/03-prioritization.md` line 28. The producer spec's lines 154 and 525 ("and urgent" for Win-zone) are drafting errors; this table is the single authority.

## Procedure

The runner owns the order, the record and the gates — this file describes the work inside each stage, never the order. Read `card.json` for the machine-readable stage list; run through `system/parts/stage_runner.py` (the plugin's own part, consumed, never copied).

Eight talk stages, then one alone stage:

1. **step-1 — Check the compass.** Email placement by the engine's own choices (junk · notification · needs me · can't tell · belongs in this week's picture); the look-back drafter starts at 1.0 before any input; the email reader starts when step 1 locks.
2. **step-2 — Confirm the week that was.** Rounds of correction; § Confirmed week written at lock. Hard gate: step-4 cannot open until this stage passes confirmed.
3. **step-3 — Mine the brain.** Question rounds (≤10); the next round waits for the world-model sharpener — its failure is shown, never skipped.
4. **step-4 — Rank.** Opens only when the draft ranker's finished file exists; the person reorders the ranked list.
5. **step-5 — Leverage × urgency.** Zones assigned (definitions above); on lock, spins off the persist drafter (⟶ step 7) and the Council.
6. **step-6 — The Council.** Six advisors on Opus; tensions shown as each finishes; the person rules on each (RULING lines).
7. **step-7 — Persist the plan.** Calendar draft as rows (day · start · end · label · zone), fit check by code, write list saved at 7.7. Nothing is written yet.
8. **step-8 — Close.** The read-back, every number computed by code; "go" (or a step number 1–8) read by code.
9. **clerk — alone.** Works the write list row by row through the doors, resumable, showing each completed row; backup last, reported plainly if it failed.

## Where the runner waits

The runner waits for the person at every talk stage's move-on; the details:

- **steps 1–3:** on the person's rounds; step 3's next round waits for the sharpener.
- **step-4:** hard gate — opens only when step-2's week is confirmed AND the draft ranker's file is done.
- **step-5:** opens when the zone sorter's draft is done; on lock, fans out to the persist drafter and Council.
- **step-6:** tensions arrive per advisor; the person rules while slower advisors finish.
- **step-7:** rounds until the clap test; the write list is saved at 7.7.
- **step-8:** on the person's "go" (code-read: "go", or a step number 1–8; anything else is asked again).
- **clerk:** alone, resumable; advances on a verified pass.

## The scratchpad — one file, one section table

Home: one file per session in the planning desk's records (exact sub-folder set by the desk's shape, e.g. `records/weekly/<YYYY>-W<NN>/scratchpad.md`; W<NN> = the ISO week of the session's Monday). Created at move 1.0 with the section skeleton below plus § Confirmed week and § Unplaced emails. Write rights: the main window and the named subagents only.

**One table — every section, its writer and its readers** (prompts read and write these exact names; a section not here does not exist):

| Section | Written by | Read by |
|---|---|---|
| § Look-back draft | 1.4a look-back drafter | 2.2 |
| § Belongs in this week's picture | step 1 (email placement) | 3.2 |
| § Filter candidates | step 1 | 7.2 |
| § Confirmed week | 2.2 lock | 5.2, 6.2, 7.3, 8.2 |
| § Energy baseline | 2.7 (full week · lighter · much lighter — code turns it into hours) | 5.3 |
| § Tags | 3.6 | 4.2 / 4.4 |
| § Still open | 3.9 | 7.2 |
| § Ranked list | 4.6 | 5.2, 6.2, 7.3, 8.3 |
| § Zones | 5.6 | 6.2, 7.3, 8.3 |
| § Persist draft | 5.8 persist drafter | 7.2 |
| § Council rulings | 6.7 | 7.2, 8.2 |
| § Write list | 7.7 | 8.6 clerk |
| § Unplaced emails | step 1 (skipped emails are carried, never lost) | 7.2 |
| § Questions | the morning run (background) | 3.2 |
| § Council-<advisor> | each advisor (tensions only, never a new plan) | 6.7 |
| § Read-back draft | read-back stager (during step 7) | step 8 |

Long-handoff arrows mark both ends (spec §F/H1): the sending move names "⟶ for step N: scratchpad § …", the receiving move names "⟵ incoming from …". Going back to an earlier step marks every later section **stale** (spec I8).

## Conventions

- **Orientation:** every screen opens with an I2 orientation line — where we are, what is next, in plain language.
- **Strike-through marker:** `~~line~~` (the one default, stated once here).
- **Diary:** no single midnight writer; the diary CAN be rewritten; machine writes are low confidence; a high-confidence line is never overwritten by the machine alone (spec §J, the person's correction 2026-11-20).
- **Spawns:** a tier named on every spawn (helpers SOP); Council advisors on Opus per the person's ruling 2026-11-20. The principle, not a rule: a sub-agent should earn its place.
- **Records:** IDs carried only as the records already carry them, never invented.
- **Answer door:** reads go through `gc answer`/`gc decide`/`gc backup` per the planning interface (engine-owned command names — read at wiring time, never guessed).

## What this does NOT do

- **No daily planning** — "plan my day" is not this skill.
- **No email drafting or sending** — reply drafts are markdown files only.
- **No write before "go"** — and no diary write outside the clerk's high-confidence corrections.
- **No outcome path:** a week with no drafts stops on screen — it is never reported as "a quiet week". The stop is shown plainly and the session ends with nothing written.
- **No engine work:** the world model, lens reports, Questions list, capacity block are engine output (on the GC coordinator's list); the capacity fallback computes in-session and SAYS SO, never a silent zero.

## Check before use

- `skill:` matches the folder; `shape:` is interactive-workflow; the outcome is in the first lines; every write path is named (the doors above, the scratchpad table, the calendar rows); the early-stop/no-outcome path is written down. Runner and card: see `card.json`; the runner validates the card before anything is written.
