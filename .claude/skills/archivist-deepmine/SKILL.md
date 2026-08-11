---
skill: archivist-deepmine
description: "Monthly deep pass over a desk's records back-catalog — surfaces promotable insight + stale-bulk deletes. Use on \"/archivist-deepmine desk=<name>\". Propose-only; never writes canon or deletes."
shape: interactive-workflow
status: active
topic: [archivist]
summary: Mine a desk's records back-catalog for buried promotable insight + stale-bulk delete candidates.
---

## Intent (§0.5)
**User outcome:** A desk's records back-catalog accumulates over months — findings that should have been promoted but weren't, clusters of raw-scrape/superseded/duplicate files that should be deleted. The weekly audit doesn't read record bodies; deepmine does. One pass surfaces the buried promotable insight and the stale-bulk delete candidates as a synthesis proposal for the supervised review session. **Bar:** "the buried gold is on the table — I don't need to re-read a year of records to find what's worth keeping."
**Role:** the periodic deep-pass miner — monthly (heavier than the weekly audit). It fans out via the Agent tool (not Workflow — the proven headless-safe path), reads every record body through read-only sonnet agents (waves of 2–3, never 6+), and synthesizes a structured result grouped by destination (desk canon / project canon / other / stale-bulk). It ends firmly at the proposal — never writes canon, never deletes. Expected shape is mostly-delete; a near-empty result on a young desk is valid.

# archivist-deepmine

> **Content root (Drive).** Every relative `state/…`, `records/…`, `canon/…`, `desks/…` path in this
> skill is **content** — it resolves under the Drive root
> `<notes>/`, never the code
> clone. Sessions launch from the clone now, so resolve these against that absolute Drive root.


Mine a desk's **records back-catalog** for buried, promotable insight + stale-bulk delete
candidates. This is the standing Archivist's **reach** — the periodic deep pass the weekly
structural audit doesn't do. **READ-ONLY / PROPOSE-ONLY:** it produces a synthesis proposal
sheet; it NEVER writes canon and NEVER deletes. (Part of `archivist-rebuild` — P2.)

## When it runs

- **Manually:** `/archivist-deepmine desk=<name>` (one-off / to prove it).
- **Standing:** monthly is the cadence it was built for, fired by whatever schedules things on
  your machine. ⛔ **Nothing here schedules it** — no scheduler ships, so today it is a skill you
  run. The procedure is
  identical — only the invocation differs. The structural audit (checks A–O) is weekly and
  separate; this deep pass is monthly because it's heavier and the back-catalog moves slowly.

## Architecture (LOCKED — archivist-rebuild huddle 2026-06-09)

- Fan out via the **Agent tool** (sonnet, read-only) — NOT the Workflow tool (unverified under
  headless `claude -p`). Agent-tool fan-out IS proven to work headless.
- **Batch 2–3 concurrent agents, never 6+** — above 2 parallel headless subagents is the proven
  ceiling; more risks flakiness. Run units in waves of 2–3.
- **Sonnet only, never opus** (subagent model rule). No API key — runs on the session/OAuth context.

## Procedure

1. **Resolve the target.** `desk=<name>` → records root `<notes>/desks/<name>/records/`. (Or `path=<root>`.)
   If neither is given, ask which desk — never guess.
2. **Discover record bodies.** List the non-empty type-subfolders under the records root
   (`context/ briefing/ decision/ summary/ log/ insight/ daily/ …`). **Skip `backups/`.** Each
   substantive body = one mining unit; group thin bodies together so every unit is worth an agent.
3. **Fan out (batched 2–3).** For each unit, spawn ONE **read-only sonnet** Agent:
   - Task: "Read every record under «body paths». Return (a) **promotable insights** — durable,
     generalizable lessons worth elevating to canon, each with a proposed home + confidence + why;
     and (b) **stale-bulk groups** — clusters of superseded / raw-scrape / consumed / duplicate
     files that are delete candidates. READ-ONLY: propose only, touch nothing."
   - Force the schema (StructuredOutput):
     `{ promotable_insights: [{insight, proposed_home, confidence:"H"|"M"|"L", why}],
        stale_bulk_groups: [{pattern, count, example_paths:[…]}] }`
   - Launch in waves of 2–3; collect all results before synthesis.
4. **Synthesize** (you, the orchestrator). Merge + dedupe across agents; reconcile cross-agent
   conflicts. Group by destination:
   - **A. Promote → DESK canon** (always-on) — the rule, not the data.
   - **B. Promote → PROJECT canon** (scoped) — name the slug.
   - **C. Other destinations** — another project's records, or route-to-`{desk}/CLAUDE.md`.
   - **D. STALE-BULK delete candidates** — snapshot-first; needs approval. Note count + caveats.
   - **E. Reconciliations** the mine confirmed (superseded projects, misplacements).
5. **Write the synthesis proposal** to `<notes>/system/logs/archivist_{YYYY-MM-DD}_deepmine-<desk>.md`
   (frontmatter `record_type: proposal`). Header line: desk · #bodies · #agents · #raw insights →
   #after dedupe. This file IS the queue a person works through in a supervised session.
6. **STOP.** Every line is a PROPOSAL. Write nothing to canon. Delete nothing. The promote/delete
   decisions belong to the supervised review session (P3), snapshot-first.

## Rails

- **READ-ONLY / PROPOSE-ONLY.** The fan-out agents get NO Edit/Write/Bash-mutation. Sonnet only.
- **Expect MOSTLY-DELETE:** a handful of real promotions, a large stale-bulk. That's the normal
  shape (one measured run: 25 insights → ~12 promotions + 366 delete candidates). A near-empty synthesis on a
  small/young desk is a VALID result — "clean, nothing to promote" is a correct output.
- **Snapshot-before-delete is the executor's job,** not this skill's.
- This skill **ends at the proposal** — it never loops into execution.

## Reference
- ⛔ The one prior hand-run's output is a record in the author's own notes and does not ship. Its SHAPE is described above, which is the part that transfers.
- ⛔ The plan-of-record and the spec this was built against are both in the author's own notes and do not ship. The procedure above is the whole of what transfers.

---

## Where the queue goes, and who acts on it

This skill **proposes and never executes.** Its output is a queue, and the queue lands at:

```
<notes>/records/proposals/archivist-{YYYY-MM-DD}-{what}.md
```

`records/proposals/` is one of the six record types, and it means exactly this: *something proposed,
waiting on a person to rule on it.*

⛔ **There is no `/archivist-review`.** The system this came from had one, and retired it on
2026-07-11 as a dead approve-then-file model — its own scheduled runner records the replacement in
one line: **the scanner just FLAGS, and the next `/save` picks it up.** So nothing here waits for a
review command that does not exist. Write the queue, say where it is, and stop. When you next run
`/save`, the open proposals are there to be dealt with.

## What this skill needs OUTSIDE its own folder

**Nothing in this repo.** It reads your notes and writes a proposal queue into them
(`<notes>/records/proposals/`), which the next `/save` picks up.

⛔ **Its scheduled runner does NOT ship** — it needed a scheduler, a cloud folder id and a
notification topic that do not exist here. The skill IS the interactive path; nothing is
missing from it.
