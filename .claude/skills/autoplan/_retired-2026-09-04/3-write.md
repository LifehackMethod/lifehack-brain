# Phase 3 — write the plan, then price it (steps 5 → 6)

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

Draw it plainly, per phase:

```
Phase 1  ── Lane A: Task 1.1 (system/build-rules-index.md)  ┐ independent — different files,
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

Full gear doctrine: `system/sops/build-conductor-sop.md`. Plan shape:
`system/sops/architecture-planning-sop.md`. **Follow them; do not restate them.**

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
