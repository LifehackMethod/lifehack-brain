---
id: system-playbook-plan-sharpening-sop
title: Plan-Sharpening SOP — the shared thinking beats /autoplan and /checkin both read
record_type: playbook
created_at: 2026-08-01
updated_at: 2026-08-03
status: active
authority: user
---

# Plan-Sharpening SOP

> This SOP holds the **thinking beats** shared by `/autoplan` (STEP 0.5, STEP 2, STEP 3) and `/checkin`
> (Step 2) — the part of "sharpen the plan" that is cheap enough to run every time, not just on a full
> planning pass. It does **NOT** hold STEP 1's fan-out exploration (reading real files, spawning
> explorers, verifying the number a plan rests on) — that beat stays `/autoplan`-only, because it is
> genuinely expensive and `/checkin` runs far more often than `/autoplan` does. Two skills reading one
> document is how they stop drifting apart. *(Until 2026-08-04 `/autoplan` carried
> `disable-model-invocation: true` and literally **could not** be invoked by a model, which is why a shared
> SOP was the only option. **the operator removed that flag**, so one skill calling the other is now MECHANICALLY
> possible — but the shared-document design stands on its own merit: duplicating these beats into two
> skills is how they drift, and that was always the deeper reason.)*

---

## §1 — LOAD THE WORLD MODEL

Read these five blocks **in this order**, before designing or reconciling anything:

1. **`## FRAME`** — the desired outcome and definition of done. Read it **first, deliberately.**
   **Why first:** whatever you read first becomes the lens you judge everything else through —
   anchoring runs 22–61% and awareness does not remove it. Read the plan first and you read the notes
   as confirmation *of* the plan; read the goal first and you read both as evidence about whether you
   are still on track.
2. **The `⛔ RULED-OUT` bucket inside `## CURRENT STATE`** — what has already been tried and rejected.
   *(Older briefs carry this as a standalone `## DON'T-RETRY` section instead — read whichever this
   brief has.)* This is the densest anti-repetition content in the file and the least likely to already
   be in context, because it was learned weeks ago and written down, not discussed today.
3. **`## CURRENT STATE`** — the last-saved position.
4. **`## OPEN LOOPS / NEXT ACTIONS`** — what is outstanding.
5. **The `## SCRATCHPAD` in full — the standing block AND every dated entry below it.** Not the standing
   block alone. **Measured 2026-08-03** on the `organism-audit` brief: the standing block is 1,322
   tokens; the dated blocks are 11,062 — a standing-block-only read gets **11%** of the pad and skips the
   **89%** where the current session-cycle's decisions live. That day it skipped five the operator rulings,
   several self-corrections, and every measurement taken — a plan written without them is stale the
   moment it's written. **Why the cost is bounded:** the pad is CLEARED at session close by `/save`'s
   BRIEF COMPACTION, so in a healthy cycle the dated content is roughly one session's worth, not an
   unbounded accumulation. **★ This read doubles as a health check, for free:** if the dated pad is
   unexpectedly large, that is evidence the last `/save` skipped its compaction — exactly the bug found
   2026-08-03, where a session at ~719k context skipped the step and stamped the ledger as if it had run.
   A standing-block-only read would never have surfaced that.

### The `## STORY LOG` — narrowed to a gate, never a wholesale skip

The Story Log is not read in full by default — the cost below is real — but it is never hard-skipped
either. Measured 2026-08-01: the `skill-system` brief runs 147,470 chars total, and its `## STORY LOG`
alone is 104,547 chars ≈ 26k tokens — **70.9%** of the brief. The `project-system` brief runs 43,636
chars, Story Log 28,641 ≈ 7.2k tokens — **65.6%**. Both briefs spend roughly two-thirds to three-quarters
of their size on this section — reading it wholesale pays a large price to receive, in narrative form,
what the four blocks above already give you distilled.

**The floor both skills read, always:** every entry whose STATUS is `open`, plus the last few entries
regardless of status. Only the settled/`locked` historical middle may be skipped — genuinely redundant,
because it has already been promoted into CURRENT STATE and the `⛔ RULED-OUT` bucket. **Why a floor, not
zero:** CURRENT STATE records WHERE THINGS ARE; the Story Log is the only place that records WHY and WHAT
QUESTION WE STOPPED ON — an unresolved open fork there is exactly what a planning or re-orientation pass
most needs, and it does not age out of relevance just because it's mid-log. *(the operator, 2026-08-03, on why
even the settled parts aren't simply dropped: "the whole point is it wants to be getting smarter every
single time.")*

**`/checkin` promotes the floor to a full read on COLD pickup; `/autoplan` does not, and that is a real
difference, not an oversight.** `/checkin` can tell COLD (a fresh window, the first check-in of a
session, or a real gap since the last save) from MID-SESSION, and reads the Story Log **in full** on a
cold pickup, because the narrative arc is the point there. `/autoplan` has no such distinction to make —
every run is a deliberate, cold-start planning pass — so it always applies the floor above: open entries
+ last few, never full, **never zero.** *(`/autoplan` used to skip the Story Log unconditionally — worse
than `/checkin`'s pre-fix gate, which was at least COLD/WARM-gated. Fixed 2026-08-03; see
`skills/autoplan/SKILL.md` STEP 0.5.)*

**Either way**, read the `⛔ RULED-OUT` bucket regardless of Story Log gating — it carries the
anti-re-proposal duty (don't propose something already tried and rejected) and that duty doesn't turn off
mid-session.

### The receipt line

Emit **one line** naming the blocks you actually read, and any that were **absent** — e.g. *"world
model: FRAME · RULED-OUT (legacy DON'T-RETRY) · CURRENT STATE · OPEN LOOPS · pad-full (standing + dated)
· Story Log (open + last 3); missing: none."* **A bare `"SKIPPED"` on the Story Log is never
acceptable** — it reads identically to a legitimate skip of the settled middle, which is exactly what let
`/autoplan`'s old unconditional skip go unnoticed. Name the slice actually read, every time. A missing
block signals an **under-structured brief**, not a silent skip — say so rather than quietly moving on.

---

## §2 — MINE THE SESSION

Load the world model (§1) tells you what was already known. This step catches what changed **today**
that the saved state doesn't yet reflect — and it is separate work, not a restatement of §1.

**This costs nothing.** The material is already in your context from the conversation itself; reading
it for this purpose is free — there is no fan-out, no extra read.

### The four categories, and how to spot each

- **A measured number, and what it replaced.** Spot it by a figure appearing in the conversation that
  didn't come from a file — a count, a percentage, a cost, a rate someone actually ran.
- **A claim that got disproved — including one of your own.** Spot it by an assertion made earlier in
  the session (by you or by the operator) that a later check in the same session contradicted.
- **An approach ruled out, and why.** Spot it by a path that was seriously considered and then dropped
  — not just mentioned in passing.
- **A correction the operator made to your read of the system.** Spot it by the operator stating that something you
  said about the system's current state was wrong.

### Routing — nothing is noted and dropped

Each finding this step surfaces goes explicitly into one of three places: the plan's **CONTEXT**, a
**task**, or **DEFERRED** as a **DEAD-END**. A finding that gets mentioned and then not routed anywhere
is the exact failure this step exists to prevent — noting something without acting on it is
indistinguishable, three sessions later, from never having found it.

### The distinction from §3

§3 (below) catches dropped **requests** — things the operator explicitly asked to build that never made it
into the executable plan. §2 catches dropped **knowledge** — things learned this session that change
what the plan *should* say, whether or not anyone asked for them. **Nothing else in either `/autoplan`
or `/checkin` catches dropped knowledge** — if this step is skipped, it is gone.

### Why a tension-only filter misses this

`/checkin` Step 2 surfaces a **tension** — strictly, a case where acting on one source would mean doing
*different work* than acting on another. Most sharpening contradicts nothing; the plan simply never
mentioned it. No tension means nothing gets surfaced under a tension-only filter, and the report reads
"plan current — no changes," which is truthful and dulling at once. §2 exists because that gap is real.

### Worked examples

*(2026-07-28, carried from `/autoplan`.)* A session measured the sub-agent spawn rate at 0.6% against
an 11.5% baseline, priced a spawn at ~8,100 fixed tokens, and disproved its own claim that the
scratchpads were empty. None of it was in any file. A plan written from files alone would have been
hours stale at the moment it was written.

*(2026-08-01, new.)* A session measured `/checkin`'s own Story-Log read at 104,547 chars and discovered
that adopting `/autoplan`'s cheaper load made check-in **faster**, not slower — inverting the one
objection to the whole change. That fact contradicted nothing already in the plan, so a tension-only
filter would never have surfaced it — which is exactly why §2 exists as a separate step from tension
surfacing.

---

## §3 — REVIEW / RECONCILE SCOPE

**Four** checks, run against the plan (or the reconciliation, for `/checkin`) before it goes in front of
the operator:

1. **Does every success criterion map to a task?** If not, either add the task or move it to
   `⚠ CUT` — never let it silently vanish.
2. **Enumerate everything the operator named as "to build" in this conversation.** Each one maps to a specific
   `Phase ▸ Feature ▸ Task`, or it lands in `⚠ CUT`. Nothing disappears without being named as cut.
3. **Do the named files actually exist on disk?** Check. A plan naming a file that isn't there is a
   plan built from memory, not from the real system.

### ⭐⭐ 4 — THE RETURN LOOP: does every OPEN TASK still serve the desired outcome?

**Checks 1–3 all run ONE DIRECTION — from what the operator asked, TO tasks. Nothing has ever walked back the
other way.** Consequence, measured on `organism-audit` 2026-08-08: **75 open tasks across 15 sections,
58 of them written in earlier sessions that nothing had revisited since.** Some were done by another
route, some were superseded, some were dead. **Nothing in `/autoplan` or `/checkin` could say so, so
they all kept full standing purely by being written down.**

⭐ **THE 80/20, AND IT IS WHY THIS COSTS NOTHING: BOTH HALVES OF THE COMPARISON ARE ALREADY LOADED.**
§1 has just read the three altitude rungs, the whole `## CURRENT STATE`, `## OPEN LOOPS` and the full
scratchpad. `/autoplan` STEP 0 has read the plan in full. **The two sides have been sitting in context
on every run since this SOP existed and nobody ever put them side by side.** No new read, no fan-out,
no tool.

**DO IT AS A DIFF, NOT AS A WALK.** Derive from the rungs + CURRENT STATE what this plan *should* contain
now; hold that against what it *does* contain. ⭐ A diff surfaces **both** directions at once — work
that is missing AND work that is obsolete — where a task-by-task walk only ever asks *"is this one still
good?"* and never notices a hole. *(the operator's framing, 2026-08-08: "it figures out what the new plan
should be and then sharpens the plan.")*

**Every OPEN task lands in exactly one bucket — a closed set:**

| bucket | what you write | 
|---|---|
| **still serves** | nothing. Leave it untouched. |
| **done another way** | ✅ + **name what did it** (a commit, a tool, another task) |
| **superseded** | ✗ + **name what replaced it** |
| **❓ can't tell** | ❓ + one line on what would resolve it — **goes to the operator** |

⛔ **THE FOURTH BUCKET IS NOT OPTIONAL AND MUST NEVER BE ROUNDED AWAY.** Without a legal way to say
*"I cannot tell"*, a session forces a confident verdict onto a task it does not understand. **Measured
the same day: two independent auditors reached OPPOSITE confident conclusions on the same two files, and
in both cases the one reasoning from history was wrong and the one that opened the file and read the
live caller was right.** A forced verdict is worse than an honest `❓`.

⛔⛔ **THIS IS ADDITIVE. IT DOES NOT PRUNE, AND THAT IS NOT A SOFTENING — IT IS A STANDING RULING**
(2026-07-28, LOCKED): *"finished phases stay — no pruning, no compaction."* **Every bucket above writes a
marker BESIDE the task**, exactly as the completion pass already writes ✅ with a commit hash next to
finished work. **Nothing is removed, no history is lost, and the ruling survives intact.**
⭐ **The distinction that makes both true at once:** that ruling protects the record from DESTRUCTION. It
was never a rule against RE-READING. *"Never prune"* and *"never revisit"* are different things, and the
second one was never decided — it was inherited.

⚠ **AND `/checkin` GETS THIS TOO, WHICH IS THE POINT OF IT LIVING HERE.** `/checkin` runs far more often
than `/autoplan`, so the re-validation happens continuously instead of only when someone writes a plan.
Both skills read this one file, so they cannot drift apart on it — this SOP's own doctrine, applied.

**RECEIPT (§5 applies with full force here):** state the outcome as counts, every run —
e.g. *"return loop: 12 open · 9 still serve · 1 done-another-way · 1 superseded · 1 ❓ to the operator."*
**A run that reports nothing is indistinguishable from a run that never looked**, and this check's whole
reason for existing is 58 tasks that nobody could tell had gone unexamined.

---

## §4 — THE WRITE SPEC (pointer only — do not copy)

The shape a plan must come back in — the `FRAME` block, `Phase → Feature → Task`, runnable Verifies,
`PARALLEL LANES`, gear tags with a named model on every delegated task, `SAFE-HALT`, `DEFERRED`, and
`⚠ CUT` — is owned by two other documents, not this one:

- `system/sops/architecture-planning-sop.md` → `## ★★ ALWAYS — the plan spec the HANDOFF must carry`
- `skills/autoplan/SKILL.md` → STEP 5

**Read one of those when you need the write spec itself.** Duplicating it here would create the exact
drift this SOP exists to prevent — two documents each holding a slightly different account of what a
plan must contain, disagreeing quietly until someone notices.

---

## §5 — HOW TO READ THIS SOP (the loading contract)

SOP loading in this system is a **trusted-read convention with no hook enforcing it** — `/build`'s own
Step 0 says v1 is "advisory, a compass not a code-gate." The same is true here: nothing forces
`/autoplan` or `/checkin` to actually open this file.

**Therefore every skill that reads this SOP must emit an orientation receipt naming it** — the same
receipt-line discipline as §1's world-model read. A skipped read and a read that found nothing look
identical from the outside unless the read announces itself.

This mirrors the standing rule already in `/checkin` Step 2: *"Silence cannot be told apart from not
having looked. And a pass with no stated outcome is indistinguishable from a pass that never ran."*
That rule was written for tension-surfacing; it applies here with the same force, for the same reason.

---

## Doctrine this SOP holds

- **One shared document, not two skills drifting apart.** `/autoplan` and `/checkin` read the same
  thinking beats here; only the exploration beat (STEP 1, `/autoplan`-only) stays outside it.
- **The load is cheap; the exploration is not.** §1–§3 cost nothing beyond reading what's already
  there or already in context — that is why `/checkin` can afford to run them every time.
- **Nothing is noted and dropped.** Every §2 finding routes to CONTEXT, a task, or DEFERRED/DEAD-END.
  Every §3 check routes to a task or `⚠ CUT`.
- **Say what you read, or it didn't happen.** The receipt line (§1) and the orientation receipt (§5)
  exist for the same reason: silence and a skipped read are indistinguishable without one.
