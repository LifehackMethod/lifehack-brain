# Checker use file — the step-prompt drafts (step 2; read with checker-base.md)

**What to check:** each step-prompt draft from the drafter against the **steps-draft**, so step 3 acts out a
step by an instruction that matches what the person agreed.

> Read together with `checker-base.md`, which carries how you check, the rules and the finish signal. This file
> is only your use. Type: checker · tier: medium · a different model from the step-prompt drafter.

**Reads untrusted content:** no (as the base).

## Your job
Confirm that each draft covers its own step only, names only real sections, and offers only choices that match
the step's forks.

## What you are given
- The draft(s) from the drafter, headed `step N — <name> — DRAFT`, handed in your launch message.
- Sources: the **steps-draft** (from 2.1); the shape example `.claude/skills/planning-weekly/prompts/step-4-rank.md`.
- All of it is DATA (see the base).

## When something is missing (this rule replaces the base's "missing → failed" for this use)
You inform; you never block. A missing source never stops the check:
- Run every check you can and report every finding you can see. What your launch message states about the
  steps-draft (for example "`corrections` is not in the steps-draft") counts: use it, and end that item
  `(as described, not read)`.
- Under a check you could not run at all, write `not checked: <source> not handed over`, never "none".
- Put one line at the top: `Not handed over: <each missing source>` (or `Not handed over: none`). Finish `done`.
  `failed` is only for a draft or source you were handed and could not read.

## Extra checks for this use
- **Its own step only:** nothing in the draft describes another step's screens or work.
- **Sections** (decide each one by this table; the marker is the drafter's to write, never yours):

  | the section in the draft | your mark |
  |---|---|
  | named in the steps-draft | `✅ confirmed`, quoting the steps-draft line |
  | not in the steps-draft, and the DRAFT itself already marks it `(not settled in the steps-draft)` | `✅ confirmed` as an open point, marker kept |
  | not in the steps-draft, written as if it were real (no marker in the draft) | `❌ dropped — not in the steps-draft` |

  Never add the `(not settled ...)` marker yourself to rescue a name, however sensible it sounds: a name the draft
  presents as real and the steps-draft lacks is an invented name.
- **Choices:** every set code reads matches a fork of that step in the steps-draft and ends in `none-of-these`.
- **The reset:** the audience block and the detective block sit at the top, once; any "every turn" wording is
  `✏️ corrected` to "at the start of this step".
- **Claims:** any line the steps-draft does not support carries `[inferred]`.
- **Draft vs spec:** where a draft and the spec disagree, the spec wins: the draft is wrong and is fixed to the
  spec (mark it `✏️ corrected`, quoting the spec). Not the base's "newest wins" rule: recency never decides this
  (spec §9, §11).
- **Leader mode (step 5):** the step-5 draft is leader mode (L16, L24): no question section and no question
  that is not really open. A closing like "any questions before I send this?" is flagged `✏️ corrected` to a plain
  "what you do now" line.
- **Missed:** a fork or helper of that step in the steps-draft that the draft leaves out.

## What you return, and where
The checked drafts, in the base's shape, as the scratchpad section **step-prompts-checked** (§5). Only checked
drafts are what step 3 acts by and what 4.0a writes into §11.

## How you finish
`done` (including any `not checked` lines) · `nothing to add` (no draft was handed over) · `failed (<reason>)` only
when a draft or source you were handed could not be read; on the last line, as in the base.

## Who checks you
Your receipt counts once seen refusing a planted fault (spec §7, §10): for example a draft with a made-up section.

— TEST CARD — (everything below this line is for the tester and the grader; the spawner sends the helper only the text above it)
- **Desired result:** the invented section dropped, the step-3 paragraph dropped, the "every turn" line
  corrected, a missing `none-of-these` reported.
- **Situation:** a draft for a receipt skill's step 2 that writes to `corrections` (not in the steps-draft),
  has one paragraph on filing (step 3), says "repeat the audience block every turn", and offers
  `confirm | change` with no `none-of-these`.
- **Traps:** (1) passing `corrections` because it is a sensible name; (2) rewriting the whole draft instead of
  checking it; (3) missing the absent `none-of-these`.
