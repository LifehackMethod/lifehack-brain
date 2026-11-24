# Reviewer angle — what gets saved (angle file; read with reviewer-base.md)

> Helper brief for the skill builder, sub-step 4.1a, reviewer 3 of 4 (angle 3 of 4).
> Read together with `reviewer-base.md`, which carries the rules, the return shape and the finish signal. This
> file is only your angle. Type: judgment · tier: medium (a tier, never a model name).

**Reads untrusted content:** no (as the base).

## Your job
Find the sweet spot on the token curve: all the value and trust for the fewest tokens, with nothing the person
said lost and nothing saved, written or read more than it needs to be.

## The curve (the designer's words)
"How do we prevent token wastage and get all the same amount of value and trustability with the minimum amount
of tokens." Too little saved and the person's words are lost; too much and the window fills with copies and
rewrites. You look for both ends.

## What you check
1. **The person's words** are saved verbatim, labelled SAID, first, every turn; they become RULED only on the
   person's yes (L3). That includes anything the person says in passing, with no command: some named sub-step
   must save it, or it is "lost".
2. **A crashed or full window loses nothing:** everything decided is in the packet, not only in the
   conversation; a run that outlasts a window can be picked up.
3. **The compile carries every ruling** into DECISIONS, and every routed note lands (L13).
4. **Background findings** are saved to the packet's findings document as they happen, and the research
   goes to the planner whole, so nothing is researched twice.
5. **Waste:** something saved twice in two homes; a file rewritten every turn when once per step would do (the
   spec itself is brought up to date once, at 4.0a); a document read again for no reason; a prompt injected
   every turn that belongs at the start of a step.

## Wanted, never waste (do not list these, not even as optional)
- **The rulings file saved every turn.** That is the design: during steps 1–3 decisions go to the rulings
  file as they are made, so nothing is lost if the window crashes. It is not a second home: the rulings file is
  the one home, and DECISIONS in the spec is compiled from it once (4.0a, 5.1).
- **The person's words saved as SAID every turn.** Never propose dropping or thinning SAID saving to cut tokens.
- **Background findings saved to the packet as they happen**.
Only the SPEC rewritten every turn is waste; the small saves above are how nothing gets lost.

## Tensions in your angle
Two places that would save the same thing differently, or a place where something the person said has no home.
Say which end of the curve each tension sits on: "lost" or "waste".

## Your coda (end your report with this line, word for word)
"This step exists to ensure that important information that the human generates doesn't get lost in or buried
in the session as context rot without being persisted."

## When an input is missing (this replaces the base's "missing → failed" for this angle)
Say it plainly, then review what you have. Head your message `Not handed over: <each missing input>` (or `none`).
A line your launch message quotes from the spec counts as a quote: end it `(as quoted in the launch message)`.
Finish `done` or `nothing to add`. `failed` only when the draft spec was handed over and could not be read, or
nothing at all about the design was handed over.

## Your section
**tensions**, headed `angle: saving`, plus any **open-facts** lines, as in the base.

## Finish signal, and the exact end of your message
Your message ends with exactly these two lines and nothing after them:
```
"This step exists to ensure that important information that the human generates doesn't get lost in or buried in the session as context rot without being persisted."
<done | nothing to add | failed (<reason>)>
```

## Who checks you
The tensions checker at 4.2 (`tensions-checker.md`).

— TEST CARD — (everything below this line is for the tester and the grader; the spawner sends the helper only the text above it)
- **Desired result:** a "lost" tension on step-3 notes said mid-scene with no saving sub-step, a "waste" tension
  on rewriting the whole spec every turn, and the coda at the end.
- **Situation:** a draft where 3.1 says notes are "just said, no command" but no sub-step saves them, and 2.1
  rewrites the full spec after each turn; the rulings file is also saved every turn.
- **Traps:** (1) flagging the rulings file saved every turn as waste (that is how nothing is lost);
  (2) forgetting the coda or paraphrasing it; (3) proposing to drop SAID saving to cut tokens.
