# Reviewer angle — the screens (angle file; read with reviewer-base.md)

> Helper brief for the skill builder, sub-step 4.1a, reviewer 1 of 4 (angle 1 of 4, L23).
> Read together with `reviewer-base.md`, which carries the rules, the return shape and the finish signal. This
> file is only your angle. Type: judgment · tier: medium (a tier, never a model name).

**Reads untrusted content:** no (as the base).

Not skill folders or files, so there is nothing to find:

> ⛔ `/next` is not here: a command the shared step runner writes when a run starts.

> ⛔ `/back` is not here: a command the shared step runner writes when a run starts.

## Your job
Read every screen the draft spec describes as the person below would see it, and find where a screen would leave
them lost, anxious, doing busy work, or unsure what role they play.

## The audience, word for word (read every screen as this person)
Someone who has never built a skill, never used Lifehack, and has not seen this session; a bit anxious about not
knowing what's going on; wanting none of their time spent on busy work. In the designer's own words: "the lowest
common denominator user", unsophisticated, "having anxiety about not knowing what's going on in the process",
who wants their time "leveraged maximally ... not being asked to do any busy work everything that could be done
without them is being done without them". Every step reassures and orients them: in under two sentences,
what is happening now and where it sits in the whole run. Each step fully reorients them as if brand new: where
they are in the whole run, what this step is for, and what ROLE they play now (L23).

## What you ask of every screen
1. Does it say where you are in the whole run, in under two sentences?
2. Is it very clear what specific ROLE the person is supposed to play at this moment?
3. Is every sentence plain, naming who does what (never "it will be handled")?
4. At most four questions, each with a best guess (L16)? In step 5 (every sub-step 5.0–5.6), no question that is
   not really open: a question the design does not need, added to fill the space, is a tension.
   **Two confirmed exceptions, never a tension and never an open fact** (L16): step 2's
   walk-through (two or three questions under each walked step, so up to six on one screen) and step 4's findings
   (up to six at a time). Do not count those against four.
5. Does it ask the person something they cannot understand, or something the system decides? Model choice,
   model tiers and routing are always decided by the harness, never asked: a screen asking the person to
   pick one is a load-bearing tension.
6. Does it end with the status bar and the standing line, with `/next` and `/back` (L17, L24)?
7. Is anything asked that could have been found out instead (L12)?
8. While a helper is still working, does the screen say plainly what is still finishing (L25)?

## Tensions in your angle
A screen rule in one place that another place would break; a screen the person cannot act on; a question the
system could answer itself. Cite the screen's sub-step (for example 4.3) in your quote. Suggest the smallest fix
(cut a line, change a question); never a full rewrite of a screen.

## When an input is missing (this replaces the base's "missing → failed" for this angle)
Say it plainly, then review what you have. Head your message `Not handed over: <each missing input>` (or `none`).
A line your launch message quotes from the spec counts as a quote: end it `(as quoted in the launch message)`.
Finish `done` or `nothing to add`. `failed` only when the draft spec was handed over and could not be read, or
nothing at all about the design was handed over.

## Your section
**tensions**, headed `angle: screens`, plus any **open-facts** lines, as in the base.

## Finish signal
`done` · `nothing to add` · `failed (<reason>)`, on the last line.

## Who checks you
The tensions checker at 4.2 (`tensions-checker.md`).

— TEST CARD — (everything below this line is for the tester and the grader; the spawner sends the helper only the text above it)
- **Desired result:** a load-bearing tension on the screen that asks the person to pick a model tier, and one
  on a step-5 screen ending with a made-up question; no complaint about step 2 showing six questions.
- **Situation:** a draft spec where 4.0 says "choose: medium or large tier for the reviewers?", 5.3 ends with
  "Any thoughts on naming?", and step 2's walk-through shows two questions under each of three steps.
- **Traps:** (1) flagging step 2's six as a breach of "four"; (2) missing that the tier question asks the person
  something they do not understand and the harness decides; (3) suggesting a full rewrite of a screen.
