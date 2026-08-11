# Phase 1 — resolve, load, explore (steps 0 → 1)

Decide **where** the plan lands, load what you already know, then go and look at the real system.
**Nothing is written in this phase.**

---

## Step 0 — Resolve the plan before you plan anything

Run this first, every time. It decides where the work lands, and getting it wrong is the whole failure
this skill exists to prevent.

```bash
bash "$ROOT/system/hooks/pm_flag.sh"  status    # the armed project's brief, or none
bash "$ROOT/system/hooks/plan_flag.sh" path     # the armed plan file, or none
```

**Three branches. There is no fourth.**

**(a) A project is armed and its brief carries a `plan:` field.** That file is the plan. **Read it in
full**, plus the brief in full — every section, especially the scratchpad, which holds the freshest
captured decisions. **You are amending. You are not starting over.**

**(b) A project is armed with no `plan:` field.** Before creating anything, **look for its existing
plan**: list `$DATA/plans/`, read the H1 of anything plausible, and check for **forked duplicates** —
several files covering one effort under different names.

- Found one → adopt it, and write its path into the brief's `plan:` frontmatter at the write step.
- Found several → **STOP and surface them.** Name each, say which you believe is the real one and why.
  **Never merge them yourself; never pick silently.**
- Found none → create `$DATA/plans/<slug>.plan.md`. The slug is what makes it findable and the status
  bar readable; the `.plan` marker is what keeps it unambiguous when a plan and its project share a
  name.

**(c) No project armed. ASK — never guess.** Offer **three** answers, not two:

> *"No project is active — is this (1) an existing project's plan (name it), (2) a new project I should
> stand up, or (3) a **standalone plan** with no project?"*

**Standalone is a legitimate answer** — *"sometimes I'm not working for my project, I'm just working
for my plan."* **The safety property is that standalone is CHOSEN, never defaulted into.** The orphan
plans were created *by default*, by plan mode minting a file because nothing stopped it. So: still ask,
always; **never fall through to standalone because resolution failed or the answer was vague.**

On answer (3), create `standalone-<name>.plan.md` and stamp this header at creation:

> **STANDALONE PLAN** — deliberately not attached to a project (`<date>`). This is NOT an orphan.

**Promotable, so the choice is never a trap:** if the work later becomes a project, rename it to
`<slug>.plan.md` and write the brief's `plan:` field. One-way, additive, no content touched.

**No project means no brief, and that is fine — not a defect.** The check-in and the save handoff both
resolve the brief's `plan:` field; with no brief that step is genuinely **N/A** and says so **in one
line.** Never warn, never nag, never treat the absence as an error.

## Step 0.5 — Load the world model

Step 0 decided *where the plan lands*. That is filing, not context. **This decides what you already
know**, and it runs in all three branches. **Skipping it is how a plan gets written against a picture
that went stale three sessions ago.**

> 📖 **The mechanism is `system/sops/plan-sharpening-sop.md` §1 — read it; do not work from this gist.**
> That SOP is shared with `/checkin`, which is what stops the two skills drifting apart. Nothing
> enforces the read, so **name the SOP in your receipt** or a skipped read is indistinguishable from
> one that found nothing.

**The gist, for orientation only.** Five blocks, in order:

1. **FRAME first, deliberately.** Whatever you read first becomes the lens. Anchoring runs 22–61% and
   awareness does not remove it.
2. **The ⛔ RULED-OUT bucket.** The anti-re-proposal duty does not turn off.
3. **CURRENT STATE.**
4. **OPEN LOOPS / NEXT ACTIONS.**
5. **The scratchpad IN FULL — the standing block *and* every dated entry**, not the standing block
   alone.

> **Why the whole pad.** Measured on one real brief: the standing block was 1,322 tokens and the dated
> blocks 11,062 — **a standing-block-only read gets 11% of the pad and skips the 89% where the current
> cycle's decisions live.** That day it would have missed five rulings, several self-corrections, and
> every measurement taken. **Why the cost is bounded:** the pad is cleared at session close, so in a
> healthy cycle the dated content is about one session's worth.
> ★ **And the read doubles as a free health check:** an unexpectedly large dated pad is evidence the
> last save skipped its compaction.

> **The story log is a gate, never a wholesale skip.** Measured: on one brief the story log was
> **104,547 characters ≈ 26k tokens = 70.9%** of the file; on another, 65.6%. That cost is real, so a
> wholesale read stays wrong — but the fix is a gate, not a skip. **Read every entry whose status is
> `open`, plus the last few regardless of status.** Only the settled middle is skipped, and only
> because it is already distilled into CURRENT STATE and RULED-OUT.
> ⚠ **This skill once carried the bug in a worse form than `/checkin` did** — an *unconditional* skip
> with no cold branch at all. Every run here is a deliberate cold planning pass, so the floor above
> always applies: **open plus recent, never full, never zero.**

**Then one receipt line** naming the SOP, the blocks you actually read, and anything **absent** — e.g.
*"world model (plan-sharpening §1): FRAME · RULED-OUT · CURRENT STATE · OPEN LOOPS · pad in full
(standing + dated) · story log (open + last 3); missing: none."*

⛔ **A bare "SKIPPED" on the story log is never acceptable.** It reads identically to a legitimate skip
of the settled middle, which is exactly what let the old unconditional skip go unnoticed. **Name the
slice you actually read, every time.**

## Step 1 — Explore. Write nothing yet.

Thoroughness comes from this beat and only this beat. **Skipping it is how you get a plan that reads
well and describes a system that does not exist.**

**Read first, from source, this session** — the brief in full, the plan in full, and the actual files
the work will touch. **Never plan from a summary, a memory, or a prior session's account.**

**Then fan out read-only explorers** when the scope is uncertain or spans areas you have not read:

- ⛔⛔ **ALWAYS in the background. NEVER spawn an explorer synchronously.** A foreground spawn **freezes
  the whole session** until it returns — the person is left staring at nothing, unable to redirect, and
  you cannot read the plan or the brief while it runs. **A background spawn costs the same tokens and
  returns the same payload; the only difference is whether the window stays usable.** Launch it, then
  **keep working** — read the plan, read the brief, mine the session — and fold the findings in when it
  lands. ⚠ **This is about *this skill's own* explorers**, not only the delegated tasks it writes into
  a plan. That gap is exactly how it went wrong.
- Use a **read-only** helper (`.claude/agents/worker.md` — `Read, Grep, Glob`). **Never an agent that
  can write.**
- **Name the model on every one.** A bare spawn inherits the session's tier, which is the most
  expensive outcome, not the neutral one.
- ⭐ **ONE explorer carrying ALL the questions — not one question each.** A spawn costs roughly
  **8,100 tokens just to exist**, so six explorers with one question each burn 48,600 in overhead
  against 8,100. Hand a single helper the whole list. Split into a second only when the areas are
  genuinely different — never to give each one a smaller job.
- Launch them in a single message so they run concurrently.

### Run the number the plan RESTS ON, before you write the plan

Verify-don't-assert guards the facts *inside* a plan. This guards its **reason for existing.** When the
justification is a figure — a count, a saving, a percentage, *"roughly N files"* — **go and get that
figure now, from source.**

> **Measured:** three consecutive plans promised a benefit resting on a count nobody had run, and each
> collapsed in seconds once someone ran it — *"~30 convertible files"* measured out at **3**, and all
> three were unconvertible. **The tell every time: nobody could say where the number came from.** If
> you cannot get it, **say so in the plan and mark the benefit UNVERIFIED** — never write around it.

⭐⭐ **And it is not only numbers — verify the CLAIM, whatever shape it has.** A plan's reason for
existing is just as often a **defect claim**: *"X is broken", "Y never fires", "nothing checks Z."*

> **Worked case, and it was this skill's own output.** A phase was written whose headline task claimed
> *"two of four agents run on nothing and the gate reports green."* It was reasoned carefully from
> source: the agent briefs said their data was *embedded in the dispatch*, the orchestrator's step
> never named the files it should paste, and the checker only asserted the boilerplate sentence.
> **Every step of that reasoning was correct and the conclusion was FALSE.** The next session opened
> the last real run's preserved dispatch and found the data sitting right there. **The operating
> session had been pasting it all along; the spec simply never said to.** The true finding was far
> weaker — *unenforced, not broken* — and the task was demoted out of the critical path.

⛔ **The rule: if a plan's justification is that something is broken, missing or unchecked, go and find
the last real ARTIFACT it would have damaged, and LOOK.** A preserved run, a committed output, a saved
dispatch, a log. ⭐ **Reasoning from the spec tells you what SHOULD happen; only the artifact tells you
what DID.** If no such artifact exists, the plan writes `UNVERIFIED — no artifact checked` beside the
claim. It never states it flat.

**What you are hunting for:** what already exists that you would otherwise rebuild · the real current
state (counts, paths, whether the thing you assume is wired actually is) · **anything that contradicts
the premise of the request.**

> **Verify, don't assert.** Replace every *"probably"* and *"should be"* with a fact you read this
> session. An unresolvable unknown is a **stop** — surface it. Never let an inferred value travel into
> the plan dressed as a fact.
