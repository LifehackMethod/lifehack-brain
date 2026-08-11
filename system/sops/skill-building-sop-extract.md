# A model cannot report on its own compliance

> **This is an extract, and it says so.** The document it comes from is roughly 2,300 lines and belongs
> to the skill-building work, which is not part of this release. **The core skills cite it for exactly
> one idea**, and that idea is below in full. Landing the whole thing here to carry one paragraph would
> ship 2,300 lines nobody reads to hold a rule everybody needs.
>
> Source: `system/sops/skill-building-sop.md` → **LAW 4, item 2**. The full document travels with the
> skill-building work.

---

## The rule

**A model accurately restates a rule it is simultaneously violating, between 8% and 99% of the time.**

So a **self-report**, a **restated banner**, a **"gate cleared" marker** — every one of them is
**orientation only, and never a gate.**

## Why it matters more than it sounds

It is easy to read that as "models are sometimes careless" and move on. It is stronger than that: the
restatement and the violation are **not in tension** from the inside. A session can write *"rungs:
present and current"* in complete good faith, having just not looked. There is no internal signal that
separates the two, which is exactly why an external one is required.

**The consequence for anything you build:** if a step matters, the evidence it ran has to be something
the step **caused**, not something a model **generated**.

> **The test:** *can the model produce this evidence by GENERATING it, rather than by CAUSING it? If
> yes, it is not evidence.*

A file that exists only because the work happened · a hash that matches only because the bytes were
written · a command's exit code · a receipt read back off disk. Those are evidence. A sentence saying
the step ran is not, however sincerely it is meant.

## What this looks like in practice, here

Three places in this repo are shaped by exactly this rule, and each one is worth seeing as the same
move rather than three separate designs:

- **The rungs are printed by code, not recited.** `checkin_open.py` reads the lines off disk and prints
  them. Four earlier attempts to fix this with better wording all failed.
- **A step's stamp is refused unless its artifact verifies.** The coverage ledger will not record that
  the scratchpad was compacted unless the archive chain checks out **and** its newest block postdates
  the run. The stamp is *caused* by the archive, not asserted alongside it.
- **The reader with no hands.** Where a model must read something hostile, the wall is its **tool
  list** — `Read` and nothing else — rather than an instruction telling it to behave. Measured, and
  this is the part that surprises people: **a cheaper model matched a more expensive one on
  correctness, and caught an injection a mechanical scan had already cleared.** Upgrading the model
  buys nothing, because the model was never what was holding the line.

## The whole model, in one line

> **Code owns the definite · the model owns the undecidable · structure owns the unverifiable.**

The handoff between the first two is a closed vocabulary: code hands the model a bounded set of
outcomes, the set contains one meaning *no outcome was reached*, and code checks membership on the way
back. The third is the one people forget — some properties cannot be checked by either, and the answer
there is to build a situation where the failure is impossible rather than detected.
