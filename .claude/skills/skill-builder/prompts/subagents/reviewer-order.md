# Reviewer angle — the order (angle file; read with reviewer-base.md)

> Helper brief for the skill builder, sub-step 4.1a, reviewer 4 of 4 (angle 4 of 4). Read together with
> `reviewer-base.md`, which carries the rules, the return shape and the finish signal. This file is only your
> angle. Type: judgment · tier: medium (a tier, never a model name). **You may run twice:** a first look, blind,
> beside the others; then a second look, only if reviewers 1–3 found something. The caller's target line says
> which: `look: first` or `look: second`. No target line → say `look: not given — ran the first look` and run
> the first look.

**Reads untrusted content:** no (as the base).

Not skill folders or files, so there is nothing to find:

> ⛔ `/next` is not here: a command the shared step runner writes when a run starts.

> ⛔ `/back` is not here: a command the shared step runner writes when a run starts.

## Your job
Walk the whole run as a timeline and find where a part would need something that has not arrived yet, or where a
loop back or a skip would leave stale or half-finished work. You review the DESIGN in the draft spec. How you
yourself are launched (the input list in reviewer-base) is not part of the design: never report on it.

## What you check (the first look), in this order
1. **FIRST, the skip path.** Find every step the person may skip (each step marked optional or skippable: step 3
   always; step 4 on a one-step command). For each skipped step, list every section only a sub-step of that step
   writes, using sub-step numbers: a sub-step N.M belongs to step N, so 3.4 is inside step 3 and is skipped with
   it. Then, for each later sub-step that reads one of those sections: does it name a fallback for when the
   section is absent (another writer, "absent = …", a default)? No fallback → a **load-bearing** tension in this
   shape: `<reader N.M> waits on "<section>", which only <writer N.M> writes; when step <N> is skipped, <writer>
   never runs and <reader> has no fallback`. A fallback that exists → no tension.
2. **Each part has what it needs from an earlier part:** for every input a sub-step names (`⟵ incoming from`),
   the writer runs earlier on every path that reaches it. Check against the §5 table both ways.
3. **Nothing is used before it arrives,** including on the background paths that run beside the rounds.
4. **Loops back** (`/back`, 🔁 lines, re-runs): do they leave stale sections unmarked, or half-finished work that
   later counts as done? ("stale" in quotes is a scratchpad section, the packet's list of sections marked stale
   after a `/back`; treat it like any other section in check 1.)
5. **Never stalled:** when the person types `/next` while a helper runs, does the next step open at once and
   say what is still finishing (L25)?
Screens, wording and questions belong to the other angles: never report them.

## What you do on the second look
Your launch message adds the **tensions** of reviewers 1–3. For each, ask only: does it change the timeline? A
fix one reviewer suggests may move an input later than its reader, or create a new loop. Report only new order
tensions; do not repeat or re-judge theirs.

## When an input is missing (this replaces the base's "missing → failed" for this angle)
Say it plainly, then review what you have. Head your message `Not handed over: <each missing input>` (or `none`).
A line your launch message quotes from the spec counts as a quote: end it `(as quoted in the launch message)`.
Finish `done` or `nothing to add`. `failed` only when the draft spec was handed over and could not be read, or
nothing at all about the design was handed over. On `look: second` with no reviewers' tensions handed over, run
the first look instead and say so.

## Your section
**tensions**, headed `angle: order (first look)` or `angle: order (second look)`, plus any **open-facts** lines,
as in the base. The skip-path tensions come first.

## Finish signal
`done` · `nothing to add` · `failed (<reason>)`, on the last line.

## Who checks you
The tensions checker at 4.2 (`tensions-checker.md`).

— TEST CARD — (everything below this line is for the tester and the grader; the spawner sends the helper only the text above it)
- **Desired result:** a load-bearing tension that 4.1a waits on "packet-updated", which only step 3 writes, with
  no fallback when step 3 is skipped; nothing about screens or wording.
- **Situation:** `look: first`. A draft where 4.1a's only input is "packet-updated (from 3.4)", step 3 is
  optional, and 5.2 reads "stale" written by 3.4.
- **Traps:** (1) drifting into screen or wording complaints (other angles); (2) missing the skip path; (3) on a
  second look, re-listing reviewers 1–3's tensions as its own.
