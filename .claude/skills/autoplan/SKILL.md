---
skill: autoplan
title: "Autoplan — plan against what the system actually is"
shape: interactive-workflow
status: active
description: "Fires on \"/autoplan\", \"make a plan\", \"update the plan\", \"add this to the plan\", \"plan this\". Use it for ANY plan: it explores the real system, writes into the project's ONE living plan file, and has six reviewers attack the plan before you see it."
summary: |
  The surveyor. It maps the ground before it draws the map — never planning from memory and never from
  the conversation alone — then amends the one plan file that project has always used. It reserves the
  person for the things only they can supply: a real fork between viable approaches, a contradiction
  between what they asked for and what the system is, a scope cut. It plans; it never executes.
triggers: ["/autoplan", "make a plan", "update the plan", "add this to the plan", "plan this"]
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Task, Agent]
created_at: 2026-07-28
updated_at: 2026-09-04
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

## Why this exists

The harness's plan mode mints **a new plan file per session**, named from the prompt — measured once:
63 plan files, 47 belonging to no project. Every one was someone asking to *update* the plan and getting
a new file. So this skill owns the plan file itself. **Never enter plan mode to hold a living plan**; it
will mint a new file and your amendment lands there. Edit the plan file directly.

## Paths (set once)

```bash
ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)"
DATA="$(python3 "$ROOT/shared/brain_root.py" --quiet)" || {
  echo "STOP: nobody has said where their notes live yet."
  echo "Ask them, then: python3 $ROOT/shared/brain_root.py --set \"<that folder>\" --create"; exit 1; }
```

Plans live at `$DATA/plans/` — they are something the person wrote, so they live with what they wrote,
never in this repo, never mirrored. One copy.

## The naming rule

- **A live plan is `$DATA/plans/<slug>.plan.md`** — one predictable name per project, forever; the
  check-in, the save handoff and the status bar all resolve against it.
- **A retired plan is `<slug>.plan.<YYYY-MM-DD>-retired.md`**, renamed once at the end of its life.
  Retirement is the only renaming operation; versioning on the way out is a one-way door, on the way
  in it is a fork. A date sorts itself; a `v2` needs you to know the sequence.
- **A standalone plan is `standalone-<name>.plan.md`**, same retirement rule — the prefix is what tells a
  deliberate standalone from an accidental orphan.
- **Deleting a plan file is forbidden.** Retirement renames; it never removes.
- **Never a prompt-derived filename** — it hides which project owns the plan.

## Step 0 — Resolve where the plan lands

Run first, every time. Getting this wrong is the failure this skill prevents.

```bash
bash "$ROOT/system/hooks/pm_flag.sh"  status    # the armed project's brief, or none
bash "$ROOT/system/hooks/plan_flag.sh" path     # the armed plan file, or none
```

Three branches, no fourth:

**(a) A project is armed and its brief carries `plan:`.** That file is the plan. Read it and the brief
in full — the scratchpad holds the freshest decisions. You are amending, not starting over.

**(b) Armed, no `plan:` field.** Look before creating: list `$DATA/plans/`, read the H1 of anything
plausible, check for forked duplicates. Found one → adopt it and write its path into the brief's `plan:`
at the write step. Found several → **STOP and surface them**, say which you believe is real and why —
never merge, never pick silently. Found none → create `$DATA/plans/<slug>.plan.md`.

**(c) No project armed. Ask — never guess.** Offer three answers: *(1) an existing project's plan — name
it, (2) a new project to stand up, (3) a standalone plan with no project.* Standalone is legitimate, and
the safety property is that it is **chosen, never defaulted into** — the orphans were created by default.
On (3), make the same look-before-create check as (b), including existing `standalone-*.plan.md`. On
creation stamp: *`**STANDALONE PLAN** — deliberately not attached to a project (<date>). This is NOT an
orphan.`* It is promotable: rename to `<slug>.plan.md` and set the brief's `plan:` — one-way, additive.
No project means no brief, and that is fine: the check-in and save handoff report the `plan:` step as N/A
in one line. Never warn, never treat the absence as an error.

## Step 0.1 — Boot guards. Code first, before any judgment.

```bash
python3 "$ROOT/system/tools/plan_lint.py" --self || { echo "STOP: boot guard failed — read the line above"; exit 1; }
```

Two checks, both mechanical: the known-bad fixture (`fixtures/broken.plan.md`) must still **fail** the
linter — a checker that passes a broken plan is dead, and nothing else would notice; and `SKILL.md` must
not exceed the size recorded in `fixtures/.budget` — the ratchet, because instruction files regrow
silently and nobody remembers why a line exists well enough to cut it. Nonzero → stop and say which.

## Step 0.2 — Read the map. Every run.

The operator's `~/.claude/CLAUDE.md` carries the repo map — which folder is which repo, public or
private, and the routing rule for where a change lands. It is already in context: **cite it, do not
reload it.** From it, every task's `Repo:` is *derived* from the task's `Where:` path — never typed
from memory, never guessed. Three outcomes:

- **The map names folders.** For each one: `test -d <folder>` — a named folder that is not there means
  the map has drifted; **STOP and ask**, do not route around it.
- **No map, or no repo section** (a student, most days). Every task gets `Repo: none — not git`, and
  the receipt says so in one line. That is a correct answer, not an error.
- **A task's `Where:` matches no row and is not under the notes root → STOP and ask.**

**Never discover repos** with `git rev-parse` or `git remote -v` — measured 2026-09-04: discovery fails
to see the second repo and reports "no access" that is not true. The map is the authority; `test -d`
only checks the map still describes the disk.

## Step 0.5 — Load the world model

Step 0 was filing. This decides what you already know, and it runs in all three branches — skipping it
is how a plan gets written against a picture three sessions stale.

Nothing enforces a read. So every read this skill makes ends in a one-line **orientation receipt**
naming what was read and what was absent — a skipped read and a read that found nothing look identical
unless the read announces itself. *(src: system/sops/plan-sharpening-sop.md:231-243)*

**Five blocks, in order:**
1. **FRAME first, deliberately** — whatever you read first becomes the lens; anchoring runs 22–61% and
   awareness does not remove it.
2. **The ⛔ RULED-OUT bucket** — the anti-re-proposal duty never turns off.
3. **CURRENT STATE.**
4. **OPEN LOOPS / NEXT ACTIONS.**
5. **The scratchpad in full — standing block and every dated entry.** The dated entries hold the
   current cycle's decisions (measured once at 89% of the pad); the cost is bounded because the pad
   clears at session close, and an unexpectedly large pad is evidence the last save skipped compaction.

**The story log is a gate, never a wholesale skip.** It can be 70% of the file, so a full read stays
wrong — read every entry whose status is `open`, plus the last few regardless. Only the settled middle
is skipped, because it is already distilled into CURRENT STATE and RULED-OUT. A bare "SKIPPED" is never
acceptable: **name the slice you read**.

Then one receipt line — the blocks read and anything absent, e.g. *"world model: FRAME · RULED-OUT ·
CURRENT STATE · OPEN LOOPS · pad in full · story log (open + last 3); missing: none."*

## Step 1 — Explore. Write nothing yet.

Thoroughness comes from this beat only. **Read first, from source, this session** — the brief, the
plan, and the files the work will touch. Never from a summary, a memory, or a prior session's account.

**Any claim the plan rests on — "X is broken", "Y never fires", "there are ~N files" — goes to
`Skill(audit)`, once, carrying every claim as a list.** It spawns the three refuters this system already
trusts (the map, the project story, the journals) and returns one verdict per claim. One invocation per
plan-write, never one per claim: each spawn costs ~8,100 tokens to exist. (Enver, 2026-09-04: *"default
to my audit skill — that's what I end up doing to reorient the system, and it works."*)

**For what `/audit` does not cover** — a count, a file's real shape, whether something is wired — fan
out read-only explorers when scope is uncertain or spans areas you have not read:
- **Always in the background.** A foreground spawn freezes the session; a background spawn costs the
  same and returns the same. Launch, keep working, fold the findings in when they land. This is about
  this skill's own explorers, not only the delegated tasks it writes into a plan.
- **A read-only helper** (`.claude/agents/worker.md` — Read, Grep, Glob). Never one that can write.
- **Name the model on every one** — a bare spawn inherits the session's tier, the most expensive outcome.
- **One explorer carrying all the questions.** A spawn costs ~8,100 tokens to exist; six one-question
  explorers burn six times that. Split only when the areas are genuinely different.
- Launch them in a single message so they run concurrently.

**Run the number the plan rests on.** When the justification is a figure — a count, a saving, "roughly N
files" — get it now, from source. Three plans in a row once rested on a count nobody had run; each
collapsed the moment someone ran it. If you cannot get it, write the benefit as **UNVERIFIED**.

**And verify the claim, whatever shape it has.** A plan's reason for existing is just as often a defect
claim — *"X is broken", "Y never fires"*. Reasoning from the spec tells you what should happen; only the
artifact tells you what did. **Go and find the last real artifact it would have damaged — a preserved
run, a committed output, a log — and look.** If none exists, write `UNVERIFIED — no artifact checked`
beside the claim. Never state it flat.

You are hunting for: what already exists that you would otherwise rebuild · the real current state
(counts, paths, whether the thing you assume is wired actually is) · anything that contradicts the
premise of the request. **Verify, don't assert:** replace every *"probably"* with a fact you read this
session. An unresolvable unknown is a **stop**, not a hedge.

## Step 2 — Design from what you found

Design from the exploration results **and from what this session established** — the discussion is
usually where the new understanding formed, and it is already in context. Carry the concrete material
forward: real filenames, real paths, the functions that already do half the job.

**Mine the session** for four things: a number that got measured (and what it replaced) · a claim that
got disproved, including your own · an approach ruled out, and why · a correction they made to your
read. **Route every finding** — into CONTEXT, into a task, or into `DEFERRED` as a `DEAD-END`. A finding
mentioned and not routed is indistinguishable, three sessions later, from never found. This catches
dropped *knowledge*; the scope check in Step 3 catches dropped *requests*.

### The seam declaration — you are almost certainly in a hybrid build

Hybrid means **the running thing has a model in it** — editing one rule inside a skill, hook or tool a
session invokes is a hybrid build, because the seam belongs to the thing you are editing. The default
answer is yes; say no only for a pure script or migration with no model at runtime.

**The code/LLM seam** — binds any hybrid build (classify the product, not the change). Code hands the
model a bounded set of outcomes; the middle is unbounded; what comes back is one of those outcomes, and
the set must contain one meaning NO OUTCOME WAS REACHED. Code checks membership on every path in;
anything off-list is surfaced, never absorbed. **The no-outcome member is for the model, not the
human** — with no legal way to say "nothing was decided" the model manufactures a decision code cannot
tell from a real one. Name the slot, never the words. Perimeter only: it governs the shape that crosses
the boundary, never how the model reasons inside it. *(src: system/build-rules-index.md:66-80)*

Then, in the plan: **name each handoff's bounded outcome set and its no-outcome member.** For a
headless handoff, name the reach and confirm both of its fixes are in place.

### When the plan is an experiment — three rules

A plan that ends in *"then run it and see"* is an experiment.

1. **One variable, or the run resolves nothing.** Two changes → two comparisons that each isolate one,
   or one moves to a follow-on phase. An arm that changes one uncontrolled thing beside its treatment
   is refused however good it looks.
2. **Find the control before designing the treatment.** Look on disk first — a preserved prior run
   predates every change under test. Name it with its real numbers. None → say so and price generating
   one as its own task; never let *"we'll compare it to something"* stand in for a named file.
3. **Put the parallelism at the right layer.** Ask what is shared between the arms and what differs. If
   the difference is downstream of the expensive shared step, run that step once and fork after it —
   cheaper and more rigorous at once, because the arms then have zero input variance.

Two constraints any multi-arm plan states: the arms **write to separate paths**, and the results table
carries an **ARM column** — a finding present in one arm and absent in the other is a named result,
never averaged away.

**Two viable approaches with different reversibility → do not pick silently; that is a stop.** At a
load-bearing fork where neither option rests on something you verified, offer `/research` rather than
answering from training.

## Step 3 — Review before you show it

Re-read your draft against the frame's desired outcome. Five checks; the fourth runs backward.

1. **Does every success criterion map to a task?** If not, add it or move it to `⚠ CUT` — never let it
   silently vanish.
2. **Reconcile scope.** Everything named "to build" in this conversation maps to a `Phase ▸ Feature ▸
   Task` or lands in `⚠ CUT`. Nothing disappears.
3. **Do the named files exist?** A plan naming a file that isn't there is a plan built from memory.
4. **The return loop — does every open task still serve the outcome?** Derive from the rungs and
   CURRENT STATE what the plan *should* hold and diff it against what it *does* hold; a diff catches
   missing work and obsolete work, a walk catches only the second. Each open task → **still serves** ·
   **done another way** (✅ + what did it) · **superseded** (✗ + what replaced it) · **❓ can't tell**
   (→ them). Additive only — a marker beside the task, never a removal. Receipt it as counts.
5. **A task may cite a ruling only where that ruling states its verdict, its date and its author.**
   "See §X" is not a citation if §X still asks the question — that asserts a decision never given and
   spends the human's authority. When you record a ruling, write those three at the site.
   *(src: system/sops/architecture-planning-sop.md:59-72)*

## Step 4 — Stop, when stopping is the right answer

You are allowed and expected to stop rather than commit. **Stop when:** exploration contradicts the
premise · two approaches are viable and differ in reversibility (their call) · the real system is
materially different from what the request assumed · you would otherwise guess at something a wrong
guess makes the plan useless. **Do not stop for:** naming, structure or ordering · anything you can
verify yourself · a phase boundary · permission to keep going.

**How:** name the fork, give your recommendation and why, and ask. The plan file lands on one
recommended approach — the stop is about reaching it honestly, not handing over a menu. **End a turn
only two ways:** a real question, or the plan for approval.

## Step 4.5 — Propose what's done, with evidence

Walk the plan's tasks and mark what this session actually finished. **Evidence, not recall:** *can the
model produce this evidence by generating it rather than by causing it? Then it is not evidence.* A task
is proposed done only against something that exists — a commit hash, a command's real output you read
this session, a number you measured. Never against a memory of having done it. Append the evidence
inline beside the task — a finished job left unrecorded gets re-done. **Say so even when nothing
qualifies:** *"completion pass: nothing to tick."* This step proposes; the monitoring window's retire
decides.

## Step 5 — Write the plan

**Amend the project's plan file in place.** New work appends as a new Phase; sharpening edits the
section where it lives. Then **write the pointer**: if the brief's `plan:` is empty, set it — that one
line is what lights up the check-in, the save handoff and the status bar.

~~*"Finished phases stay — mark them done, never prune, never compact. Long plans grown over time are
the ones that survived."*~~ **Struck 2026-09-04.** This was the accumulator: agents cite stale text and
act on it (Bekim's two-tracker finding, 2026-09-01). Finished cards are preserved in `<slug>.plan.done.md`
by the retire step, never in the live plan.

### What it must contain, in this order

1. **`CONTEXT`** — why this change is being made and the intended outcome; the reason, not the request.
2. **`FRAME`** — desired outcome · success criteria · constraints · out of scope. Approved once, up
   front; that is what lets execution run without nagging. **And one `Desired outcome:` line directly
   under the H1** — the first thing a cold build window reads, before any task.
3. **`⚠ CUT FROM THIS BUILD`**, directly under the frame, if anything they named is not in the body:
   what it is · why defer · what they lose · **needs an explicit OK**. Plan approval is not cut
   approval; the default is keep-it-in. An approved cut files to the brief's open loops.
4. **`Phase → Feature → Task`**, never a flat list. **Every phase is written in full detail** — never
   an outline to be filled in later; the plan may run unattended, and drift is caught at the phase
   gate, not by coming back to plan again. **A phase with any `Owner: BUILD` task opens with one
   `Desired outcome:` line** — the nav window reads it before the task list; a nav-only phase omits it
   rather than carrying decoration. **Every task is a card** — the same slots in the
   same order, so a blind session that reads one card and nothing else can act. The card *is* the
   sub-agent brief: a delegated task receives it verbatim, and nothing is relayed by memory.
   - `Owner:` — see below.
   - `Where:` — the path(s) the task touches. A path, not a description.
   - `Repo:` — **derived, never typed**: `Where:` → the map row it falls under → `public · <branch>` /
     `private · <branch>` / `none — not git`. The linter re-derives it and refuses a mismatch.
   - `Do:` — the work, atomic. **Never an enumeration of items tracked somewhere else** — no issue
     or PR numbers. If the work is a tracked list, the card carries `Query:` instead (below).
   - `Verify:` — typed `SHAPE` (a command on the artifact, with a `before` value that must fail and an
     `after` that must pass) · `RUN` (invoke it on a fixture; a broken fixture must be caught) · `JUDGE`
     (a window that did not write it reads it, told "find where this fails"). Self-report is not a
     type; the window that built a task never ticks it.
   - `Done:` — never a checkbox. What re-derives the truth: the Verify re-run by `plan_retire.py`, a
     commit whose subject starts `<id>:`, or a `Query:` returning empty **and proven well-formed**.
   - `Commit:` — `<id>: <what>`, local only, explicit paths; absent when `Repo: none`. No push in a plan.
   - `Query:` + `Proof:` — for tracked work only: the `gh` command that returns the live list, and the
     command that proves the query is well-formed (the label exists, the repo answers). **A zero result
     is UNKNOWN until proven** — a typo'd query returns nothing and exit 0, and reads as "all clear".
   - gear + model, when delegated.
   **The cycle is Execute → Verify & Test → Commit → Retire.** No further slots (rules tax each other).
   **A plan never holds what something else can tell you.** Brain files: nothing else can, so the
   card holds list and state. Git work: git knows what shipped, so `Done:` derives it. GitHub issues:
   GitHub knows the list and the state, so the card holds the decision and the `Query:`, nothing more. ⛔ Binds only when the work is tracked in a repo: system work outside one has no tracker, so it carries `Done:` and no `Query:`.
   **Every task carries an owner line** (Enver, 2026-09-04) — a task is build work only when it has
   been diagnosed and its fix is known, **atomised so a cold build window executes it without
   re-deriving anything**; anything still needing diagnosis, a judgment call, or the human in the loop
   does not go in as a build task at all: `**Owner: BUILD**` — diagnosed, mechanical; the spec is the
   work · `**Owner: NAV**` — needs diagnosis, judgment, or the human · `**Owner: NAV to specify, BUILD
   to implement**` — mixed; name which half is which. **The test is not difficulty — it is whether the
   answer is already known.** A build window is not equipped to hold an open question; it closes one
   rather than leave it open, and the wrong answer then carries the authority of something written
   down. If you cannot fully specify a task, it is NAV's — write it so, diagnose, re-write it as BUILD.
   *(src: system/sops/build-nav-window-remit-sop.md:184-215)*
5. **`PARALLEL LANES` per phase** — which tasks are independent and which are gated, and by what.
   Without it the build walks the phase one task at a time and the plan silently costs wall-clock.
6. **The critical files named.** Where a change repeats across many files, describe the pattern once.
7. **Existing code to reuse, with paths.** This is exploration's payoff; a plan without it means the
   explore step did not really happen.
8. **`SAFE-HALT`** — a checkable list: every destructive step and every plan-changing decision.
9. **`DEFERRED`** — each item **TODO** (still viable → open loops) or **DEAD-END** (ruled out → story log).
10. **`VERIFICATION`** — how to test the whole thing end to end. Runnable.

**Only the recommended approach goes in the file.** Rejected alternatives belong in `DEFERRED` as
dead ends, never in the body as a menu.

**Every plan carries a `Review:` line** at the top, written by this skill in both branches — `six-lens
<date> · <n> findings · <accepted>/<rejected>/<to them>` after the swarm, or `SKIPPED <date> <reason>`
when `--no-review` was used. An unreviewed plan must look unreviewed a year later.

### Lanes — when each task runs

Gears say *how* a task runs; lanes say *when*. Write both, or the plan executes in single file.
**The gate rule — the only thing that makes two tasks sequential:** one writes a file the other reads
or writes, or one consumes the other's output. Nothing else. Independence is the assumption; a gate is
what you must justify — name the reason beside every gate, and if you cannot, the tasks are independent.

**Lock the data contracts before parallel writes** — agree the shape each lane reads and emits first;
skipping this is the #1 regret of parallel builds. *(src: system/sops/build-conductor-sop.md:193-194)*

Draw it plainly, per phase, and **name the file each task writes** — that is what makes the gate
checkable by whoever executes it:

```
Phase 1  ── Lane A: Task 1.1 (system/tools/foo.py)           ┐ independent — different files,
         └─ Lane B: Task 1.2 (.claude/skills/build/SKILL.md) ┘ launch together
Phase 2  ── Lane C: Task 2.2 (.claude/skills/build/SKILL.md) ← GATED on 1.2 (same file)
```

### Gear tags

Tag each task **gear-1** (single thread) · **gear-2** (background helper) · **gear-3** (team wave) ·
**gear-4** (scripted fan-out). The tag is a hint — the build re-decides per task, so write each task to
read as standalone.
- **gear-2 is the default** for decided, self-contained work, launched in the background so the
  foreground stays open. **Say it in the task, don't just tag it** — *"run this as a background
  helper"* in the task's own text; deciding is where delegation dies.
- **Name the model on every delegated task.** Blank is not neutral: a bare spawn inherits the session's
  tier, the most expensive outcome.
- **Batch: one helper carrying many jobs.** A spawn costs ~8,100 tokens fixed; bundling six jobs into
  one helper measured 4.6× cheaper. Savings from bigger batches are durable; savings from a weaker
  judgment model are not.
- **gear-3** is a team wave: several independent surfaces that must coordinate — ~7× tokens, only on
  "use agent teams". **gear-4** is a scripted fan-out: dozens-to-hundreds of independent items, or a
  repeatable cross-checked pass worth codifying as a rerunnable script — up to ~16 concurrent / 1,000
  total, only on "use a workflow". *(src: system/sops/build-conductor-sop.md:70-71)*
- **gear-4's three guardrails:** every `agent()` call sets `model: 'sonnet'` (haiku for pure read-only)
  or it burns opus at fleet scale · read-only, no mid-run sign-off — anything needing approval, or any
  human-domain / Google write, stays gear-1; the pattern is *workflow does the read-only legwork → lead
  surfaces it → human approves → write happens in the main loop*, and for staged sign-off run each stage
  as its own workflow · opt-in only. *(src: system/sops/build-conductor-sop.md:162-169)*
- If the shape fits gear-3/4 but nobody opted in, **name it in the frame** — *"this is fan-out-shaped;
  say the word"* — and plan it as gear-2s.

## Step 5.5 — The swarm: six lenses, blind, one table

The plan is written and has passed lint — run `python3 "$ROOT/system/tools/plan_lint.py" "<plan>"`;
nonzero exit means the plan is not reviewed and is not shown. Only a plan that already passes goes to
the six readers below.

**Launch all six lenses in one message, in the background.** Each receives exactly two things: the
plan's **file path**, and its lens file from `.claude/skills/autoplan/lenses/` — `tokens`, `steps`,
`gating`, `github` run on sonnet; `value`, `postmortem` run on opus. The model is named inside each
lens file — pin it on the spawn regardless, since a bare spawn inherits the session's own tier. All six
read the shared rules at `lenses/_contract.md`. Where a lens names `<notes>/...`, substitute `$DATA` on the spawn — a lens file never carries a personal path, because this folder ships to students. **The lenses are blind to each other** — nothing is
relayed between them by chat, before or after — a lens that saw another's finding would anchor on it
instead of finding its own; independence is the entire point of running six.

**Collect, then build one table** — finding · lens · severity · accept / reject / ask-them — before
anything in the plan is touched. Aggregating first is what makes six independent reads worth more than
one careful one; folding a finding in as it lands loses the count of how many lenses agreed on it.

Apply every `accept` to the plan file. Every `reject` goes to `DEFERRED` as a `DEAD-END`, carrying the
lens's reason. **Two lenses disagreeing on the same task is not adjudicated here** — it goes to the
operator, in the four-part decision format: the decision in one line · the context · why it could not
be settled without them · your recommendation.

**Save the table** to `<notes>/state/<plan-slug>/<name>-<date>.<ext>` (a claim beside nothing is the
thing, SOP §V.4d), add that path to `Review:` as `· artifact: \`<path>\`` — `plan_lint.py` requires it.

**`--no-review` skips the swarm** — write `Review: SKIPPED <date> <reason>`, no artifact needed.
Either branch, the plan says which: an unreviewed plan must look unreviewed a year later, never carry a
line implying six lenses looked at it when none did.

Six lenses cost roughly `6 × 8,100 = 48,600` tokens fixed, before any reasoning runs — worth it on a
plan other plans will fork from or follow; the `steps` lens's own time budget is what tells you when a
plan is small enough to skip the swarm entirely.

## Step 6 — The efficiency pass

The plan is written. **Now, and only now, look at cost** — an efficiency worry raised mid-design
quietly shrinks the plan's ambition; a plan written without this step overspends by accident. One
question of the finished thing: **where does this get the same result for fewer tokens?**

Read the whole plan again for the three things a per-task rule cannot see:
1. **Work of the same shape scattered across phases** — four "read these files and report" tasks in
   three phases are one helper's job. Bundle them and say so.
2. **A delegated task with no model named.** Fill it in.
3. **A fan-out that is one-helper-per-item.** Rewrite it as one helper carrying the list — the single
   biggest lever, because the spawn cost is fixed.

**The hard fence — this pass may never lower the quality bar.** Never downgrade the model on judgment
work to save tokens (that trade was run at ~8× cheaper and "lost the intuition"). Never delete a task,
merge two distinct verifies, or thin a `SAFE-HALT` — if the pass wants to cut scope, that is a `⚠ CUT`
needing an OK. Never trade away the thing that goes unmeasured: a helper that came back thin and got
believed shows up nowhere; when a bundle would make an answer harder to check, keep it split.

**Then write one line at the top of the plan naming what the pass changed** — and if it changed
nothing, say that. A pass with no recorded outcome is indistinguishable from a pass that never ran.

## The rules that hold across all of it

- **One project, one plan.** A second plan file for the same project is the failure.
- **Never plan from memory.** Re-anchor to the live brief and the live plan first, every run.
- **Verify, don't assert.** Replace every *"probably"* with a fact you read this session; an
  unresolvable unknown is a stop.
- **Say what you found, even when it is nothing.** Every step that comes up empty says so in one line.
- ~~**Finished work stays.** Mark it done; never prune, never compact.~~ Struck 2026-09-04 — see Step 5.

## What this skill needs outside its own folder

| Needed | Why | Status |
|---|---|---|
| `shared/brain_root.py` · `shared/registry.py` | where the notes are, and which project this is | ✅ here |
| `system/hooks/pm_flag.sh` · `plan_flag.sh` | which project and plan are armed | ✅ here |
| `.claude/agents/worker.md` | the read-only explorer | ✅ here |
