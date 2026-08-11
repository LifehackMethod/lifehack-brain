# Phase 2 — design, review, stop, tick (steps 2 → 4.5)

---

## Step 2 — Design from what you found

Design **from the exploration results and from what THIS SESSION established** — never from the
conversation's *requests* alone. Carry the concrete material forward: real filenames, real paths, the
functions that already do half the job.

> 📖 **Mechanism: `system/sops/plan-sharpening-sop.md` §2 — read it.** Shared with `/checkin`, which
> runs the same beat. **Name the SOP in your receipt.**

**Mine this session for what changes the world model.** The old rule read *"design from the exploration
results, not from the conversation."* That intent stands — but taken flat it excludes the freshest
source in the room. **The discussion is usually where the new understanding actually formed**, and it
is already in your context, so reading it is free.

Four categories: **a number that got measured** (and what it replaced) · **a claim that got disproved**,
including one of your own · **an approach ruled out**, and why · **a correction they made** to your read
of the system.

**Route every finding** — into CONTEXT, into a task, or into `DEFERRED` as a `DEAD-END`. A finding
mentioned and not routed is indistinguishable, three sessions later, from never having been found.
**This is distinct from the scope reconciliation below**, which enumerates only what they named *to
build*: that catches dropped **requests**, this catches dropped **knowledge**, and nothing else here
does.

> *Worked example: a session measured a spawn rate at 0.6% against an 11.5% baseline, priced a spawn at
> ~8,100 fixed tokens, and disproved its own claim that the scratchpads were empty. **None of it was in
> any file.** A plan written from files alone would have been hours stale the moment it was written.*

### The seam declaration — required for any hybrid build

> ⛔ **You are almost certainly in a hybrid build. Read this before deciding you are not.**
> **Hybrid means the RUNNING THING has a model in it** — not that your task mentions the word. Editing
> one function, one rule or one check inside a skill, hook or tool that a session invokes **is a hybrid
> build**, because the seam it must survive belongs to the thing you are editing, not to your edit.
> ⚠ **Measured:** a blind reader skipped this entire section, reporting *"applies only to hybrid
> builds; situation does not specify one"* — while planning a fix to a live skill. **The default answer
> here is YES.** Say no only for a pure script or migration with no model at runtime.

**Read `system/build-rules-index.md` now** — it carries the code/LLM seam, the model-reach rule and the
code-spiral rule, once, and it is the only place any of them lives. ⛔ **Do not paste a copy back into
this file.**

Then, in the plan: **name each handoff's bounded outcome set and its no-outcome member.** For a
headless handoff, name the reach and confirm both of its fixes are in place.

### When the plan is an experiment — three rules

A plan that ends in *"then run it and see"* is an experiment.

**① ONE VARIABLE, or the run resolves nothing.** Every additional thing that changes between control
and treatment is a confound you cannot subtract afterwards. **If a plan wants to change two things, it
either runs two comparisons that each isolate one, or it cuts one to a follow-on phase.** *(Live
precedent: an arm measuring `44% cheaper · 1.79× findings` was formally refused because it ran one turn
where its control ran two — the best-looking result in that plan, killed by one uncontrolled
difference.)*

**② FIND THE CONTROL BEFORE DESIGNING THE TREATMENT.** A plan that generates its own baseline pays
twice and gets a baseline carrying the same unknowns as the run. **Look on disk first** — a preserved
prior run, gates green and artifacts intact, is worth more than a fresh one *because it predates every
change under test.* Name it with its real numbers. If no control exists, **say so and price generating
one as its own task** — never let *"we'll compare it to something"* stand in for a named file.

**③ ⭐⭐ PUT THE PARALLELISM AT THE RIGHT LAYER.** Ask: **what is shared between the arms, and what
actually differs?** If the difference is *downstream* of the expensive shared step, the arms do not each
need their own run of it — **do the expensive step once and fork after it.**

> **Worked case:** two arms differed only in how a map was assembled, and assembly happens after a
> four-agent fan-out. Two parallel *sessions* would have produced **different agent returns**, so any
> delta would be part-signal and part-noise against a 22% variance floor. **One fan-out with two
> assemblies off the byte-identical returns costs zero extra spend AND gives the comparison zero input
> variance.** ⭐ Splitting later is both cheaper and more rigorous — two properties that usually trade
> against each other.

⛔ **Two constraints any multi-arm plan must state:** the arms **write to separate paths** (a shared
filename silently overwrites one and the run reads as single-arm), and the results table carries an
**ARM column** — a finding present in one arm and absent in the other is a named result, **never
averaged away.**

**If exploration surfaced two genuinely viable approaches with different reversibility, do not pick
silently.** That is a stop. At a load-bearing fork where neither option rests on something you
verified, **offer `/research`** rather than answering from training.

## Step 3 — Review before you show it

> 📖 **Mechanism: `system/sops/plan-sharpening-sop.md` §3 — read it.** Shared with `/checkin`.

Re-read your own draft against the frame's desired outcome. **Four checks, and the fourth is the only
one that runs backward.**

1. **Does every success criterion map to a task?** If not, add the task or move it to `⚠ CUT` — never
   let it silently vanish.
2. **Reconcile scope.** Enumerate everything named as "to build" in this conversation. Each maps to a
   specific `Phase ▸ Feature ▸ Task`, or it lands in `⚠ CUT`. **Nothing disappears.**
3. **Do the named files exist?** Check. **A plan naming a file that isn't there is a plan built from
   memory.**
4. ⭐⭐ **The return loop — does every OPEN task still serve the outcome?** Derive from the rungs and
   CURRENT STATE what the plan *should* hold now, and **diff it against what the plan does hold.** A
   diff catches missing work **and** obsolete work; a task-by-task walk catches only the second. **It
   costs nothing** — both halves are already in context. Each open task → **still serves** · **done
   another way** (✅ + what did it) · **superseded** (✗ + what replaced it) · **❓ can't tell** (→ them).
   ⛔ **Additive only — a marker beside the task, never a removal.** *"Finished phases stay, no pruning,
   no compaction"* protects the record from destruction; it was never a rule against re-reading.
   **Measured:** one plan carried 75 open tasks, 58 from earlier sessions that nothing had revisited.
   **Receipt it as counts, every run.**

## Step 4 — Stop, when stopping is the right answer

You are **allowed and expected** to stop rather than commit.

> *"It should be allowed to stop if it finds something instead of being forced to commit to one
> approach, even if it finds something that contradicts."*

**Stop and put it in front of them when:** exploration found something that **contradicts the premise**
of what was asked · two approaches are genuinely viable and **differ in reversibility** (their call,
not yours) · the real system turns out to be materially different from what the request assumed · you
would otherwise **guess** at something a wrong guess makes the plan useless.

**Do NOT stop for:** routine naming, structure or ordering · anything you can verify yourself · a phase
boundary · permission to keep going.

**How to stop:** name the fork, give your recommendation and why, and ask. **The plan file eventually
lands on ONE recommended approach** — the stop is about reaching it honestly, not about handing over a
menu to sort.

> **End a turn only two ways:** with a real question, or by presenting the plan for approval. Never
> trail off into prose fishing for a go.

## Step 4.5 — Mark what's done

Step 2 mines the session for **knowledge**; step 3 reconciles **scope**. Neither asks the question this
exists for: **what in this plan is now DONE?** *"I wanted it to go read the session and figure out
what's been completed. It should be ticking things off on its own."* **It costs nothing** — the session
that did the work is already in context.

Walk the plan's existing tasks and mark what **this session actually finished**, with its evidence.

> ⚠ **EVIDENCE, NOT RECALL — this is the hard part.** A session once stamped ledger steps it had not
> run and the coverage report printed green. The governing rule: ***"can the model produce this evidence
> by GENERATING it, rather than by CAUSING it? If yes, it is not evidence."*** A task is ticked only
> against something that exists — a commit hash you can quote, a command's real output you read this
> session, a number you actually measured. **Never against a memory of having done it.**

**Record completed work IN THE PLAN, not only in commits.** A killed idea left lying gets obeyed; **a
finished job left unrecorded gets re-done.** Six of thirteen findings in one audit were already-fixed
work somebody redid because nothing in the plan said so. So for every task this session finished: tick
its checkbox **and append the evidence inline beside it** — not filed somewhere else.

**Say so even when nothing qualifies** — *"completion pass: nothing to tick; no plan task was finished
this session."* A silent pass and a pass that found nothing look identical unless the outcome is stated.
