---
skill: build
title: "Build — execute the plan, and close honestly"
shape: interactive-workflow
status: active
description: "Use when planning is done and it's time to execute — steps back, builds autonomously, verifies every task before ticking it. Fires on \"build\", \"execute the plan\", \"just do it\"."
triggers: ["/build", "build", "execute the plan", "just do it", "run the plan"]
created_at: 2026-06-01
updated_at: 2026-10-28
---

# Build

You are in autonomous build mode. The conversation is over; execute the plan.

## Enver's three locked rules

1. **Delegate by default.** Use as many parallel background sub-agents as the plan's independent cards
   allow. The main window keeps its context for high-order thinking only. Every helper gets an explicit
   model (sonnet; haiku for pure read-only; never opus), a done-criterion, and its context in the prompt.
   Helpers return verdicts, not file bodies: cite file:line, and put evidence in a file. Work runs
   sequentially only when one card writes a file another card reads.
2. **Don't stop to ask.** Keep going unless something is broken or blocked. The only planned stops are a
   checkpoint card and an irreversible external act (push, deploy, send, delete), which the runner
   records as `waiting`. Never defer an in-scope card silently: build it, or mark it ✗ loudly and carry on.
3. **Breadcrumbs for a human reading along.** After each card, and at least once mid-task when
   heads-down, write the fixed prefix `Phase N · card X of Y —` then 1–3 plain sentences: what finished,
   what is next. No tables, never a question. Breadcrumbs are read once and gone, so anything that
   changes the plan also goes into the plan file.

## Start-up

- Stand up the task queue from the plan's open cards. It is a display for Enver, fed from the runner's
  record, never a second source of truth.
- Arm the status bar by what was handed over: plan only, arm the plan; working from a project, arm the
  project AND its plan; a project with no current plan, the project only.

## Job 2: what you build must conform to skills SOP v2

Whatever the plan builds has to come out conforming. `system/tools/conform.py` checks it; this file does
not restate the rules. Three doors:

- **Door 1, design.** Before the first card, make the scope call: is this a card job or a normal skill?
  This is a checkpoint for Enver. Do not decide it alone.
- **Door 2, each card.** After a card's Verify passes, run conform.py on that card's Where.
- **Door 3, the whole artifact.** Run conform.py on the finished artifact. The build is not done unless
  it passes or every failure is a declared exception.

Scope: ALWAYS applies to anything that runs code. ORDERED applies on top when step order must hold,
decided by the card-or-not rule. NOT APPLICABLE is said out loud with a reason; a silent pass is a fail.

Exceptions are declared as `exception: <RULE-ID> because <reason>` in the plan or in `conform.decl`. An
undeclared exception fails. `JUDGE` items (ORD-6, ORD-7) go to a reviewer or Enver and are never auto-passed.

## How to run it

The runner walks the plan's open cards. Run it as:

```bash
bash "$HOME/lifehack-v2/.claude/skills/build/scripts/build_run.sh" <plan.md>
```

- The runner, not the AI, runs every Verify and writes the record (`BUILD_RUN_HOME`, default
  `~/.claude/run/build/<run-id>/record.tsv`). You never tick anything and never touch the record.
- `plan_queue.py` runs first. Report any WEAK Verify warnings to Enver before building on them.
- Exit `0`: done. Exit `1`: a card, door, or step failed or was refused; read the loud line, fix, rerun.
- Exit `70`: waiting at a checkpoint or Door 1. Ask Enver. Only after he answers, rerun the same command
  with `--answer yes` or `--answer no`. Never answer for him.
- Exit `4`: the record or the plan could not be read, or the record is truncated. Stop and tell Enver;
  do not repair the record by hand.

## Close honestly

- A partial card is ✗. The close names every ✗ at the top; silence is not completion.
- Discoveries that change the plan go into the plan file, not only into chat.
- If a capability is missing, say so in one line and carry on; do not go quiet.
- Research plan (no code, no artifact): the deliverable is the finding. Never manufacture an artifact to
  look done; Door 3 is NOT APPLICABLE, said with that reason.

Excuses for skipping a step: see `system/sops/build-conductor-sop.md`.
