# /audit — routing eval

> **What this is.** The prompts that SHOULD fire `/audit`, and the near-misses that should NOT.
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
decision), paste the prompt as the whole message, and record whether `/audit` fired.
**Do not paste the prompt mid-conversation** — that measures something else.

---

## SHOULD FIRE

| # | prompt | why it must fire | run 1 | run 2 | run 3 |
|---|---|---|---|---|---|
| S1 | `/audit` | the literal command | | | |
| S2 | `/audit we should build a caching layer for the ingest gate` | literal command + a claim | | | |
| S3 | "has this actually been tried before?" | the skill's own framing, near-verbatim | | | |
| S4 | "sanity-check this plan before I build it" | pre-flight framing, no keyword | | | |
| S5 | "am I about to rebuild something that already failed?" | the DO-NOT-BUILD refutation shape | | | |
| S6 | "is this claim actually true, or am I about to believe something wrong?" | the REFUTES member's own framing | | | |
| S7 | "check this against what we already know before I commit to it" | prose intent, no keyword | | | |
| S8 | "poke holes in this before I take it to a builder" | the refutation mandate, idiomatic phrasing | | | |
| S9 | "is this really broken, or does the system already handle it?" | the hardest case — zero vocabulary overlap with "audit" | | | |
| S10 | "three-way check this against the map, the brief, and the journal" | names the mechanism directly | | | |

## SHOULD **NOT** FIRE — the near-misses

> Each of these belongs to a **neighbouring** skill. A false fire here is as much a defect as a silent
> miss, because it burns three subagent spawns on the wrong question.

| # | prompt | who should get it instead | why NOT audit | run 1 | run 2 | run 3 |
|---|---|---|---|---|---|---|
| N1 | "what would a professional architect build instead of this?" | `/architect` | reads ONE subject at three altitudes — a design question, not a claim-check | | | |
| N2 | "load everything relevant on the ingest gate" | `/read` | context loading, not a claim to refute | | | |
| N3 | "where are we on the organism audit project" | `/checkin` | re-orienting on a project, not checking a specific claim | | | |
| N4 | "what's the best way to rate-limit an API in Python?" | `/research` | external-practice question, no ClaudeOps subject | | | |
| N5 | "convene my advisors on whether to take this consulting client" | `/advisory-council` | a decision needing expert judgment, not a fact-check against memory | | | |
| N6 | "these two subsystems keep fighting each other" | `/architect` (ENGINEER rung) | a seam-level design problem, not a single claim to refute | | | |
| N7 | "what did we decide about the calendar guard?" | `/read` | recall of a decision, not a refutation pass on a new claim | | | |
| N8 | "audit the desk canon for staleness" | `canon-audit` / `archivist-audit` | a structural/staleness sweep over a whole tree, not one claim checked against three sources | | | |

⚠ **N1, N6, and N8 are the ones that matter.** N1/N6 share almost all of this skill's vocabulary
("architect", "check", "broken") and differ only in **shape** — one subject at three altitudes vs. one
claim through three refutation lanes. N8 shares the literal word "audit" and differs only in **scope** —
a whole-tree structural sweep vs. one bounded claim. If any of these three fire, the description is too
broad, and N8 firing is the most likely mistake given the shared name.

---

## Results log

> Append a dated block per run. **Never overwrite a prior result** — the point is the trend across
> description changes, and a rewritten history cannot show one.

### 2026-08-20 — baseline, NOT YET RUN
**Status: ⏸ the file exists; no case has been executed.** Created alongside the skill.
⛔ **Do not record this skill's routing as verified until this table has real numbers in it** — an empty
eval file is `skill-building-sop.md §V.9`'s *validator-exists-but-nothing-calls-it*, and it would be this
project's own named failure committed inside the document that names it.
