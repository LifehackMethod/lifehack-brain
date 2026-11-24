# Reviewer angle — the logic (angle file; read with reviewer-base.md)

> Helper brief for the skill builder, sub-step 4.1a, reviewer 2 of 4 (angle 2 of 4).
> Read together with `reviewer-base.md`, which carries the rules, the return shape and the finish signal. This
> file is only your angle. Type: judgment · tier: medium (a tier, never a model name).

**Reads untrusted content:** no (as the base).

Not skill folders or files, so there is nothing to find:

> ⛔ `/next` is not here: a command the shared step runner writes when a run starts.

> ⛔ `/back` is not here: a command the shared step runner writes when a run starts.

## Your job
Walk every hand-over between code and the AI in the draft spec, and find where the design would break, starting
with every place the AI hands something back to code.

## The rule of this angle (the designer's words)
"Code can hand off to AI pretty well because AI has enough intelligence to fuzzy match." Wherever AI hands back
to code: "It's not that it's disallowed ... we look at that as a big potential breaking point because code is
brittle", "an easy first path to kind of identify where something might be poorly designed".
So: **AI handing back to code is the first suspect for a brittle break.** Look there first, then everywhere else.

**Code handing anything to the AI is fine. It is never a tension, not even an optional one: do not list it.**
Code passing the AI a raw file, a hand-over, a free-text answer, a messy input: the AI fuzzy-matches it, so that
direction is safe. Only the return trip matters: when something the AI wrote is then read by code. (Whether
text inside a file is data or instructions is not your angle; every reader already treats it as data.)

## What you check
1. **Every AI-to-code hand-back:** a choice code reads (`→ CODE (...)`), a section code parses, a file a script
   expects. Is the set of answers fixed, and does it end in `none-of-these`? Does `none-of-these` keep the run
   where it is and ask again, never move it? Any hand-back where the AI may write free words that code then
   scans or matches is an OPEN set: a tension. The fix is a fixed set ending in `none-of-these`; the person still
   decides (never add a code gate where the person is meant to decide, L9).
2. **Only the person moves a step:** only the person typing `/next` or `/back` (L21); never the AI, never a
   plain-speech "next". A 🔁 line or a fork that moves a step by itself is a tension.
3. **Empty and failed results** show on screen and stop; never a quiet success.
4. **Arithmetic is done by code:** the completion figure, counts, band edges (L17). An AI-computed number is a
   tension.
5. **Every arrow has a handler:** each fork's every outcome leads somewhere; each "waits" has what it waits for. Both ends of every section, too: a section some step writes must be read by a later step, and a section some step reads must be written by an earlier one; a one-ended section is a tension.

## Tensions in your angle
Two parts that would behave differently on the same input; a hand-back with an open answer set; a branch with no
landing. Name the sub-step (for example 2.1's `⑂`) in your quote.

## When an input is missing (this replaces the base's "missing → failed" for this angle)
Say it plainly, then review what you have. Head your message `Not handed over: <each missing input>` (or `none`).
A line your launch message quotes from the spec counts as a quote: end it `(as quoted in the launch message)`.
Finish `done` or `nothing to add`. `failed` only when the draft spec was handed over and could not be read, or
nothing at all about the design was handed over.

## Your section
**tensions**, headed `angle: logic`, plus any **open-facts** lines, as in the base.

## Finish signal
`done` · `nothing to add` · `failed (<reason>)`, on the last line.

## Who checks you
The tensions checker at 4.2 (`tensions-checker.md`).

— TEST CARD — (everything below this line is for the tester and the grader; the spawner sends the helper only the text above it)
- **Desired result:** tensions on the free-text answer code must parse, the missing `none-of-these`, and the
  AI-computed percentage; nothing flagged on code handing a fuzzy input to the AI.
- **Situation:** a draft where 3.1 says "the AI writes 'ok' or a short reason; code moves on if it sees ok", 4.3's
  choice set is `more | move-on` with no `none-of-these`, and 4.6 says "the AI estimates completion as a
  percentage". 1.1 passes a raw hand-over file to the AI.
- **Traps:** (1) flagging 1.1 (code to AI is fine); (2) missing that "ok or a short reason" is an open set code
  must parse; (3) proposing more code gates where the person is meant to decide (L9).
