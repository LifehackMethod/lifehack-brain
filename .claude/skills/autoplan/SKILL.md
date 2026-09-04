---
skill: autoplan
title: "Autoplan — plan against what the system actually is"
shape: interactive-workflow
status: active
description: "Build or amend a project's plan. Explores the real system before writing, then writes into that project's ONE living plan file — never a new one. Fires on \"/autoplan\", \"make a plan\", \"update the plan\", \"add this to the plan\", \"plan this\"."
summary: |
  The surveyor. It maps the ground before it draws the map — never planning from memory and never from
  the conversation alone — then amends the one plan file that project has always used. It reserves the
  person for the things only they can supply: a real fork between viable approaches, a contradiction
  between what they asked for and what the system is, a scope cut. It plans; it never executes.
triggers: ["/autoplan", "make a plan", "update the plan", "add this to the plan", "plan this"]
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Task]
created_at: 2026-07-28
updated_at: 2026-08-11
---

## Intent (§0.5)
**User outcome:** a plan built on what the system *actually looks like right now*, written into the ONE
plan file that project has always used — sharpened and grown, never forked into a new file they will
lose. **Bar:** *"it planned against reality, it went in the same place as last time, and it told me when
it hit something I needed to decide."*
**Role:** the surveyor. It maps the ground before it draws the map. **Human-in-the-loop by design** — it
reserves the person for a genuine fork, a contradiction, or a scope cut, and decides everything else
itself. Its fence: **surveyor, not builder.** It plans; it never executes.

# Autoplan

## Why this exists — read once

The harness's plan mode assigns **a new plan file per session**, named from the first few words of
whatever prompt triggered it. The slug is cached against the session id; a fresh window always mints a
fresh file. It is **by design**, and no setting points it at an existing plan.

Measured on one real system: **63 plan files, 41 of them prompt-named, 47 belonging to no project** —
`update-teh-plan-gleaming-liskov.md`, `add-to-the-plan-majestic-dove.md`. Every one of those is somebody
asking to *update the plan* and getting a new file instead.

**So this skill does not use plan mode to hold a living plan. It owns the file itself.**

⛔ **Never enter plan mode to hold a living plan.** It will mint a new file and your amendment lands
there instead of in the project's plan. Edit the plan file directly.

## Paths (set once)

```bash
ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)"
DATA="$(python3 "$ROOT/shared/brain_root.py" --quiet)" || {
  echo "STOP: nobody has said where their notes live yet."
  echo "Ask them, then: python3 $ROOT/shared/brain_root.py --set \"<that folder>\" --create"; exit 1; }
```

**Plans live at `$DATA/plans/`.** They are something the person wrote, so they live with the rest of
what they wrote — not in this repo, and not mirrored anywhere. There is one copy.

## The naming rule — the whole failure this skill prevents

- **A live plan is `$DATA/plans/<slug>.plan.md`.** One predictable name, every project, forever. That
  is what the check-in, the save handoff and the status bar all resolve against.
- **A retired plan is `<slug>.plan.<YYYY-MM-DD>-retired.md`** — renamed exactly once, at the end of its
  life. **Retirement is the only renaming operation there is.**
- **There is deliberately no way to mint a second live file.** A version slot at *creation*
  (`<slug>.v2.plan.md`) would be a fork button and would re-open *"which one is live?"* — the disease
  this cured. **Versioning on the way out is a one-way door; on the way in it is a fork.**
- **A date, not a `v2`.** A version number needs you to know the sequence; a date sorts itself and
  explains itself.
- **A standalone plan is `standalone-<name>.plan.md`**, same retirement rule. The prefix is what lets
  any future sweep tell a **deliberate** standalone from an **accidental** orphan at a glance.
- **Deleting a plan file is forbidden, absolutely.** Retirement renames; it never removes.

⛔ **Never a prompt-derived filename.** That is what produced the 47 orphans. A random name does not
disambiguate a plan from its project — **it hides which project owns it.**

## The steps

## Steps 0 → 1 — resolve, load, explore

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

On answer (3), **look before you create — the same check branch (b) makes.** List `$DATA/plans/` and
read the H1 of anything plausible, including existing `standalone-*.plan.md` files. Found one covering
this effort → adopt and amend it. Found several → **STOP and surface them**; never merge or pick
silently. Found none → create it.

*(Branch (b) has always carried this and (c) never did. Deterministic naming has been covering the gap —
a re-run lands on the same filename — but preventing forked duplicate plans is this skill's whole job,
and it should not rest on a naming coincidence in one of its two paths.)*

On creation, stamp this header:

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

Nothing enforces a read. So every read this skill makes ends in a one-line **orientation receipt**
naming what was read and what was absent — a skipped read and a read that found nothing look identical
unless the read announces itself. *(src: system/sops/plan-sharpening-sop.md:231-243)*

**Five blocks, in order:**

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


## Steps 2 → 4.5 — design, review, stop, tick

---

## Step 2 — Design from what you found

Design **from the exploration results and from what THIS SESSION established** — never from the
conversation's *requests* alone. Carry the concrete material forward: real filenames, real paths, the
functions that already do half the job.

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

**The code/LLM seam** — binds any hybrid build (code and a model in one running product; classify the
product, not the change). Code hands the model a bounded set of outcomes; the middle is unbounded; what
comes back is one of those outcomes, and the set must contain one meaning NO OUTCOME WAS REACHED. Code
checks membership on every path in; anything off-list is surfaced, never absorbed. **The no-outcome
member is for the model, not the human** — with no legal way to say "nothing was decided" the model
manufactures a decision code cannot tell from a real one. Name the slot, never the words; perimeter
only. *(src: system/build-rules-index.md:66-80)*

Then, in the plan: **name each handoff's bounded outcome set and its no-outcome member.** For a
headless handoff, name the reach and confirm both of its fixes are in place.

### When the plan is an experiment — three rules

A plan that ends in *"then run it and see"* is an experiment.

**1. ONE VARIABLE, or the run resolves nothing.** Every additional thing that changes between control
and treatment is a confound you cannot subtract afterwards. **If a plan wants to change two things, it
either runs two comparisons that each isolate one, or it cuts one to a follow-on phase.** *(Live
precedent: an arm measuring `44% cheaper · 1.79× findings` was formally refused because it ran one turn
where its control ran two — the best-looking result in that plan, killed by one uncontrolled
difference.)*

**2. FIND THE CONTROL BEFORE DESIGNING THE TREATMENT.** A plan that generates its own baseline pays
twice and gets a baseline carrying the same unknowns as the run. **Look on disk first** — a preserved
prior run, gates green and artifacts intact, is worth more than a fresh one *because it predates every
change under test.* Name it with its real numbers. If no control exists, **say so and price generating
one as its own task** — never let *"we'll compare it to something"* stand in for a named file.

**3. ⭐⭐ PUT THE PARALLELISM AT THE RIGHT LAYER.** Ask: **what is shared between the arms, and what
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
5. **A task may cite a ruling only where that ruling states its verdict, its date and its author.**
   "See §X" is not a citation if §X still asks the question — that asserts a decision never given and
   spends the human's authority. When you record a ruling, write those three at the site.
   *(src: system/sops/architecture-planning-sop.md:59-72)*

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


## Steps 5 → 6 — write the plan, then price it

---

## Step 5 — Write the plan

### Where it goes

**Amend the project's plan file in place**, at `$DATA/plans/<slug>.plan.md`. New work appends as a
**new Phase section**. Sharpening edits the section where it already lives. **Finished phases stay** —
mark them done, never prune, never compact. Long plans grown over time are the ones that survived;
protect that shape.

**Then write the pointer.** If the brief's `plan:` frontmatter is empty or absent, set it to this
plan's path. That single line is what lights up the check-in (which arms the plan flag), the save
handoff, and the status bar — all three already read it, and most briefs have never had it filled.

### What it must contain

In this order:

1. **`CONTEXT` first** — why this change is being made, what prompted it, the intended outcome. Not a
   restatement of the request; the reason behind it.
2. **A `FRAME` block** — desired outcome · success criteria · constraints · out of scope. One line each
   is fine. **Approved once, up front** — that is what lets execution run without nagging.
3. **`⚠ CUT FROM THIS BUILD`**, directly under the frame, if anything they named is not in the
   executable body. Each cut states what it is · why you propose deferring · **what they lose** ·
   flagged **needs an explicit OK**. **Plan approval is NOT cut approval** — surface each as its own
   decision. **The default is keep-it-in.** An approved cut files to the brief's open loops, so a build
   that skips it structurally cannot report "done".
4. **`Phase → Feature → Task`** — never a flat list. Every task is `Execute → Verify & test → mark ✅`,
   and **the verify is runnable** — a command, or an output to look at. Never "looks done".
   **Every task carries an owner line** (Enver, 2026-09-04): `**Owner: BUILD**` — diagnosed, high
   confidence, mechanical; the spec is the work · `**Owner: NAV**` — still needs diagnosis, a judgment
   call, or the human in the loop · `**Owner: NAV to specify, BUILD to implement**` — mixed; name which
   half is which. **The test is not difficulty — it is whether the answer is already known.** A build
   window answers an undiagnosed question confidently and wrongly, and the wrong answer then carries the
   authority of something written down. If you cannot fully specify a task, that is the signal it is
   NAV's — write it so, diagnose, then re-write it as BUILD.
   *(src: system/sops/build-nav-window-remit-sop.md:184-215)*
5. **A `PARALLEL LANES` block per phase** — which tasks are **independent** (launch together) and which
   are **gated**, and by what. Without it the build walks the phase one task at a time even where
   nothing stops it running them at once, and the plan silently costs wall-clock it never needed to
   spend.
6. **The critical files named.** Where a change repeats across many files, describe the pattern once
   and list a few representative paths — do not enumerate every file.
7. **Existing code to reuse, with paths.** The functions, scripts and hooks already here that this
   build should stand on rather than rebuild. **This is exploration's payoff; a plan without it means
   the explore step did not really happen.**
8. **A `SAFE-HALT` section** — a checkable list, not a vibe. Name every genuinely destructive step and
   every plan-changing decision, explicitly.
9. **A `DEFERRED` list** — each item tagged **TODO** (still viable → files to open loops) or
   **DEAD-END** (ruled out → files to the story log).
10. **A `VERIFICATION` section** — how to test the whole thing end to end. Runnable.

**Only the recommended approach goes in the file.** Alternatives you considered and rejected belong in
`DEFERRED` as dead ends, **not in the body as a menu.**

### Lanes — WHEN each task runs

Gears answer *how* a task runs; lanes answer *when*. **Write both.** A plan with gear tags and no lanes
still executes in single file, which is the slow build people actually feel.

**The gate rule — the only thing that makes two tasks sequential:** one **writes a file the other reads
or writes**, or one **consumes the other's output**. Nothing else. Not "same phase", not "reads better
in order", not "I'd want to see the first one land". **Independence is the assumption; a gate is the
thing you must justify** — so state the reason beside every gate, and if you cannot name one, the tasks
are independent.

**Lock the data contracts before parallel writes** — agree the shape each lane reads and emits first;
skipping this is the #1 regret of parallel builds. *(src: system/sops/build-conductor-sop.md:193-194)*

Draw it plainly, per phase:

```
Phase 1  ── Lane A: Task 1.1 (system/tools/foo.py)            ┐ independent — different files,
         └─ Lane B: Task 1.2 (.claude/skills/build/SKILL.md) ┘ launch together
Phase 2  ── Lane C: Task 2.2 (.claude/skills/build/SKILL.md) ← GATED on 1.2 (same file)
```

**Name the file each task writes.** That is what makes the gate checkable by whoever executes it,
rather than a judgment call they have to redo.

### Gear tags

Tag each task **gear-1** (single thread) · **gear-2** (background helper) · **gear-3** (a team wave) ·
**gear-4** (a scripted fan-out). **The tag is a hint** — the build re-decides per task, so write each
task to read as standalone.

- **gear-2 is the default** for decided, self-contained work, launched **in the background** so the
  foreground stays open. Say so explicitly for any fan-out phase.
- **Say it in the task, don't just tag it.** A delegated task reads *"run this as a background helper"*
  in its own text — not merely `gear-2` in the margin. A task that **states** the delegation is not
  asking the builder to decide, and deciding is exactly where delegation dies.
- **Name the model on every delegated task — never blank.** Blank is not neutral: a bare spawn inherits
  the session's tier, so an unnamed model is **the most expensive outcome**, not the default one.
- ⭐ **Batch: one helper carrying many jobs, not one helper per job.** A spawn costs **~8,100 tokens
  fixed**, whatever the model and however small the work. Bundling 6 jobs into 1 helper measured
  **4.6× cheaper** than 6 spawns. So when a lane holds several small tasks of the same shape, the plan
  says **one helper, all of them.** ⚠ **This is the safe lever:** savings from bigger batches are
  durable; savings from a weaker judgment model are not.
- **gear-3 and gear-4 are opt-in only** — they need to have been asked for. gear-4 is read-only and
  autonomous, because a fan-out cannot pause for sign-off. If the shape fits gear-4 but nobody opted
  in, **name it in the frame** — *"this is fan-out-shaped; say the word to run it that way"* — and plan
  it as gear-2s.

- **gear-3** is a team wave: several independent surfaces that must coordinate — **~7× tokens**, only on
  "use agent teams". **gear-4** is a scripted fan-out: **dozens**-to-hundreds of independent items or a
  repeatable cross-checked pass, up to ~16 concurrent / 1,000 total, only on "use a workflow".
  *(src: system/sops/build-conductor-sop.md:70-71)*
- **gear-4's three guardrails:** every `agent()` call sets `model: 'sonnet'` (haiku for pure read-only)
  or it burns opus at fleet scale · read-only, no mid-run sign-off — anything needing approval or a
  human-domain write stays gear-1 · opt-in only. *(src: system/sops/build-conductor-sop.md:162-169)*

## Step 6 — The efficiency pass

The plan is written. **Now, and only now, look at cost.** The earlier steps decide whether the plan is
*right*; this asks one question of the finished thing: **where does this get the SAME result for fewer
tokens?**

**Keeping the two apart is the point.** An efficiency worry raised mid-design quietly shrinks the plan's
ambition; a plan written without this step overspends by accident.

Read the whole plan again and look for the three things a per-task rule cannot see:

1. **Work of the same shape scattered across phases.** Four tasks in three phases that are all *"read
   these files and report"* are one helper's job, not four. Each looks fine alone; **only the
   whole-plan view catches it.** Bundle them and say so.
2. **A delegated task with no model named.** Fill it in.
3. **A fan-out that is one-helper-per-item.** Rewrite it as one helper carrying the list. **This is the
   single biggest lever** — the spawn cost is fixed, so the win scales with how many spawns you
   removed.

**The hard fence — this pass may NEVER lower the quality bar.** It finds the same result cheaper; it
does not find a cheaper result.

- **Never downgrade the model on judgment work to save tokens.** That trade was run and reverted: a
  judgment step moved to the cheapest tier for roughly 8× and *"lost the intuition."* **Savings from
  bigger batches are durable; savings from a weaker judgment model are not.**
- **Never delete a task, merge two distinct verifies, or thin a `SAFE-HALT`** in the name of
  efficiency. If the pass wants to cut scope, that is a `⚠ CUT` item needing an OK — not an
  optimisation.
- **Never trade away the thing that goes unmeasured.** Tokens and wall-clock both show up somewhere; a
  helper that came back thin and got believed **shows up nowhere.** When a bundle would make an answer
  harder to check, keep it split.

**Then write one line at the top of the plan** naming what the pass changed — *"efficiency pass: folded
5 read-only tasks into 2 helpers; named the model on 3."* If it changed nothing, **say that.** A pass
with no recorded outcome is indistinguishable from a pass that never ran.


## The rules that hold across all of them

- **One project, one plan.** A second plan file for the same project is the failure, not a convenience.
- **Never plan from memory.** Re-anchor to the live brief and the live plan first, every run.
- **Verify, don't assert.** Replace every *"probably"* and *"should be"* with a fact you read this
  session. An unresolvable unknown is a **stop**, not a hedge.
- **Say what you found, even when it is nothing.** Every step that comes up empty says so in one line.
  A silent pass and a pass that found nothing look identical unless the outcome is stated.
- **Finished work stays.** Mark it done; never prune, never compact. Long plans grown over time are the
  ones that survived — protect that shape.


## What this skill needs outside its own folder

| Needed | Why | Status |
|---|---|---|
| `shared/brain_root.py` · `shared/registry.py` | where the notes are, and which project this is | ✅ here |
| `system/hooks/pm_flag.sh` · `plan_flag.sh` | which project and plan are armed | ✅ here |
| `.claude/agents/worker.md` | the read-only explorer | ✅ here |
