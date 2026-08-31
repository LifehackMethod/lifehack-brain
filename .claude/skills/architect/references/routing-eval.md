# /architect — routing eval

> **What this is.** The prompts that SHOULD fire `/architect`, and the near-misses that should NOT.
> **Triggering is the one place a skill's correctness is decided before the skill ever runs**, and it is
> invisible from inside — this file is the only thing that catches a silent under-trigger.
>
> **⛔ RUN EACH CASE 3+ TIMES** (`skill-building-sop.md` LAW 4.3 — *single samples lie*). Trigger behaviour
> is stable on some prompts and not on others, so one green sample is not evidence the description
> improved. Record every result, including the disagreements.
>
> **Re-run this whole file whenever the `description:` frontmatter changes.** Nothing else in the skill
> can tell you the description got worse.
>
> ⚠ **Expected baseline: auto-trigger runs roughly 20–50% even with a good description**, and descriptions
> truncate at ~250 characters. A case that fires 2-of-3 is not automatically a defect; a case that fires
> 0-of-3 is.

## How to run one case

Open a **cold window** (no prior context about this project — prior context contaminates the trigger
decision), paste the prompt as the whole message, and record whether `/architect` fired.
**Do not paste the prompt mid-conversation** — that measures something else.

---

## SHOULD FIRE

| # | prompt | why it must fire | run 1 | run 2 | run 3 |
|---|---|---|---|---|---|
| S1 | `/architect` | the literal command | | | |
| S2 | `/architect grand-central` | literal command + a subject | | | |
| S3 | "what would a professional systems architect build instead of this?" | the skill's own framing, near-verbatim | | | |
| S4 | "is this the right architecture for the ingestion pipeline?" | the core question, named subsystem | | | |
| S5 | "what are we missing architecturally?" | absence-shaped — `MISSING-PIECE` | | | |
| S6 | "did we reinvent something that already exists here?" | `REINVENTED-WHEEL` | | | |
| S7 | "is the hospital subsystem overbuilt?" | `OVERBUILT` | | | |
| S8 | "architect this" | terse idiom | | | |
| S9 | "I want a professional's read on how the memory system is designed" | prose intent, no keyword | | | |
| S10 | "step back — what would someone who does this for a living do differently?" | the altitude question with zero vocabulary overlap. **The hardest case, and the most important one.** | | | |

## SHOULD **NOT** FIRE — the near-misses

> Each of these belongs to a **neighbouring** skill. A false fire here is as much a defect as a silent
> miss, because it burns an opus council on the wrong question.

| # | prompt | who should get it instead | why NOT architect | run 1 | run 2 | run 3 |
|---|---|---|---|---|---|---|
| N1 | "fix this bug in `emit_recommendation.py`" | ordinary build | FIXER rung — one broken thing | | | |
| N2 | "why is the health tile red?" | Hospital / diagnosis | a symptom, not an architecture question | | | |
| N3 | "make a plan for the next phase" | `/autoplan` | planning, not architecture | | | |
| N4 | "what did we decide about the calendar guard?" | `/read` | recall, not design | | | |
| N5 | "convene my advisory council on whether to buy the house" | `/advisory-council` | a council, but the **wrong cartridge** — not a ClaudeOps-architecture question | | | |
| N6 | "these two subsystems are fighting each other" | ENGINEER rung | seam-level, one rung below | | | |
| N7 | "review this code" | ordinary review | implementation, not architecture | | | |
| N8 | "what's the best way to do X in Python?" | `/research` | an external-practice question with no ClaudeOps subject | | | |

⚠ **N5 and N6 are the two that matter.** N5 shares almost all of this skill's vocabulary and differs only
in **domain**; N6 shares the domain and differs only in **altitude**. If either fires, the description is
too broad — and N6 firing is the more expensive mistake, because the answer will look plausible.

---

## Results log

> Append a dated block per run. **Never overwrite a prior result** — the point is the trend across
> description changes, and a rewritten history cannot show one.

### 2026-08-06 — baseline, NOT YET RUN
**Status: ⏸ the file exists; no case has been executed.** Created alongside the skill at `T22.6`.
⛔ **Do not record this skill's routing as verified until this table has real numbers in it** — an empty
eval file is `§V.9`'s *validator-exists-but-nothing-calls-it*, and it would be this project's own named
failure committed inside the document that names it.
