# The Map — shared output format (every map-agent returns THIS)

You are a fresh-context reader. You were handed a window of the person's real world (emails, tasks, calendar events for
the week) via the central store. Read it for YOUR one angle only (named in your angle brief) and return findings.

**Return, as markdown, nothing else:**
```
## <angle name>
### Findings (ordered biggest-signal first; OMIT NOTHING — low-signal ranks lower but stays)
- **<one-line headline>** — <the tension/theme/observation in one or two plain sentences>
  · pointer: <item id / thread / event so the session can reach it>
  · confidence: CONFIRMED | INFERRED | HYPOTHESIS
### Pre-drafted questions (for the session to ask the person — each a real question + your best-guess answer)
1. <question> — best guess: <guess>
### Marked deltas (only if your angle surfaces one; else omit)
- <what diverges + from what>
### Coverage ledger (REQUIRED — every item you were handed, accounted for, no exceptions)
SIGNAL — one line each, with its reason:
- `<item_id>` — SIGNAL: which finding above it feeds
NOISE — ONE block, ids only, NO per-item prose (these carry nothing for YOUR angle):
`<item_id>` `<item_id>` `<item_id>` … (every remaining id you were handed, space-separated)
```

> ## ⛔ THE COVERAGE LEDGER — why it exists and why the id must be in backticks
> **`OMIT NOTHING` was already this format's rule and had NO mechanism behind it.** On the real 2026-07-21
> run, 28 email threads were read and **5 real signals were lost** — including a lease-renewal deadline
> buried in a thread of routine building-maintenance notices, on the exact lane the week's locked Win said
> to protect. Nobody could tell, because a findings list orders what was *found* and is **silent about what
> was seen and dropped.**
> **The ledger is the fix: it makes your coverage a TRACE instead of a claim.** `fanout_completeness.py` runs
> at the return boundary (Phase 0 step 3b) and set-diffs the union of all four agents' cited ids against the
> exact id set the window handed you. **An uncited id reads as LOST and the run stops.**
> - **Write the id inside backticks — `` `19f822031dc6e583` ``.** That is the citation form the checker reads;
>   a bare id is invisible to it and your whole return grades as zero coverage.
> - **NOISE is a first-class, honest answer** — it is not a failure and it is not "dropping" the item. It is
>   how you say *"I saw this and it carries nothing for my angle."* That is exactly what the ledger is for.
> - ⭐ **NOISE GOES IN ONE BLOCK, IDS ONLY — do not write a reason per noise item (changed 2026-08-03).**
>   **Measured on the four real returns of 2026-08-03: the ledger was 73.9% of everything the agents wrote**
>   (86,726 of 117,400 bytes; ~140,438 of 190,110 output tokens), and that output volume is what drove each
>   agent to **20 turns**, re-reading its own context ~32×. **Compacting the noise half is a 54% smaller
>   ledger ≈ 40% of total output tokens — for free.** ⛔ **NOTHING ELSE CHANGES: same ids, same backticks,
>   same 242-item denominator, and you still READ every item in full.** The checker only ever reads
>   backticked ids, so your coverage is scored identically. **This is a change to BOOKKEEPING FORM, never
>   to what you absorb** — the person, 2026-08-03: *"we need to absorb all the content from the emails … that's
>   non-negotiable."*
> - ⚠ **KNOWN BOUND, stated rather than hidden:** a NOISE id is something you can TYPE without having read
>   the item — so this ledger proves COVERAGE ACCOUNTING, not attention. It always did; the per-item prose
>   never fixed that either. Do not treat a full ledger as proof anyone looked.
> - **Every id, including ones another agent will obviously claim.** You are blind to the other three; the
>   union is computed for you. Guessing that someone else has it covered is how the ER thread vanished.
> - ⛔ **Never invent an id to satisfy the ledger.** An id you did not receive is flagged as `alien` and fails
>   the run louder than a missing one. **The ledger is a record of what you actually read.**

**Rules for every map-agent:**
- **Delta-only read:** an item carrying a HITL note → read the NOTE, don't re-read the item. Only un-annotated items get a fresh deep read. *(The HITL note store is LIVE (Phase D) — `item_store_window` serves a fresh note in place of the raw body automatically; a changed item is re-mined, never served stale. You receive the note already substituted in the vault — trust it as the item's processed record.)*
- **Order, don't drop.** You RANK by likely relevance; you never delete. Only the human flags irrelevant.
- **Do NOT judge, conclude, or name a Win.** You surface and point-to. Mark inference; never fabricate.
- **Raw stays with you.** Return thin findings + pointers, never pasted raw bodies.
