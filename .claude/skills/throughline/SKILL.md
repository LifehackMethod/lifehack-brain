---
topic: [system-architecture]
skill: throughline
description: "Read-only plot tension-surfacer: four beats (Reflect → Provoke → Ideate → Diverge). Use on \"/throughline\" or \"surface the tension in this plot / project\"."
shape: interactive-workflow
title: Throughline — Plot Tension-Surfacer
version: 1.2
created_at: 2026-06-22
updated_at: 2026-08-11
status: active
authority: user
---

## Intent (§0.5)
**User outcome:** Every project has a gap between what it set out to do and what it's actually doing — throughline makes that gap visible before it compounds. Drop in a project slug and a grain (week/month/quarter) and four beats later the divergence is named, cited, and written down ready for review — nothing asserted, nothing concluded. **Bar:** "I can see the gap — I didn't know that's what I was looking at until now."
**Role:** the read-only investigator, context-blind by design (it judges the plot on its own terms, not what the caller hopes to find). It arms a write-scope guard hook before reading (hard-blocking every write but its own findings file), assembles the plot from what has accreted if none is given, and runs REFLECT → PROVOKE → IDEATE → DIVERGE in exact sequence. It produces only a draft-status finding; a person must set `status: human-reviewed` before any downstream consumer can act. It surfaces; the human disposes.
**Per-turn anchor:** Beat N/4 · {REFLECT | PROVOKE | IDEATE | DIVERGE} · reading the plot, not concluding · next → {next beat or the findings write}

# throughline — Plot Tension-Surfacer

A read-only, context-blind investigator. Given a pre-assembled PLOT and a caller-provided `--context` string,
it runs the four-beat sequence and writes the output to one findings file. It never writes back to
source files. It never executes anything. It surfaces; the human concludes.

Triggered by: `/throughline`, `/throughline --context "..."`, "evaluate this", "run the throughline on",
"surface the tension in this plot".

**NOT a subagent.** Runs in the main session — the caller provides context, the investigator produces the output.

---

## Write-scope guard — ARM at start, CLEAR at end (do not skip)

`/throughline` is read-only; a guard hook enforces that it writes ONLY its findings file.
The guard is OFF until you arm it, so:

```bash
ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" && pwd)"
```

1. **At the very START of a run**, before reading the plot:
   ```bash
   bash "$ROOT/system/hooks/throughline_flag.sh" arm
   ```
2. **At the END** (after the findings are written, OR if you abort):
   ```bash
   bash "$ROOT/system/hooks/throughline_flag.sh" clear
   ```

While armed, ANY write outside `<notes>/records/insights/throughline/` is hard-blocked. The flag is
session-scoped and self-expires after 30 min, so a forgotten `clear` is harmless.

---

## Invocation

```
/throughline --context "<plain-language caller context>" <plot-path>
```

- `--context` — required. A plain-language string from the caller: what this evaluation is for, who
  is asking, and what question they most want answered. Passed verbatim. The investigator uses it to orient
  but does not let it narrow what tensions it surfaces.
- `<plot-path>` — optional. Absolute path to a pre-assembled plot file. If omitted AND the caller names
  a **target** (a project slug, a subject folder, or `whole-system`) + a **grain** (week/month/quarter/year),
  the skill ASSEMBLES the plot — see "Assembling the plot" below.
  If the caller pastes a plot inline, use that. Never fetch a file plot from multiple sources.

**Context-blind design:** there is no horizon/caller branching inside this skill. The investigator evaluates
the plot on its own terms. The `--context` string is orientation, not a filter.

---

## Before Running — Staleness is a SIGNAL, not a refusal

Check the plot's `plot_assembled` / `updated_at` (or, for an assembled plot, the newest rollup's
`generated_at`). **Do NOT refuse on age** — surface staleness as part of the investigation:

- If the freshest dot is old *relative to its cadence* (weekly >~10 days · monthly >~40 · quarter
  >~100): note it in REFLECT ("the trajectory goes cold after {date}; what follows is read from a
  stale plot") — a thing that went dark IS a finding worth surfacing.
- If the producing job looks **dead** (the newest rollup's `generated_at` is far past its cadence
  window): say so — "PRODUCER STALE — the diary stopped updating on {date}; pulling the heavy-search
  fallback rather than trusting cold dots" (see the fallback section).
- A genuinely dormant project rendering as **"Quiet this period"** is itself signal — surface it; it
  is not missing data.

---

## Plot Input Format

The investigator is fed a pre-assembled plot. The expected shape:

```
plot_assembled: YYYY-MM-DD

origin:      [one paragraph — why this was started, what problem it was solving]

dead_ends:   [bulleted list — what was tried and abandoned, with the real reason it failed]

intended:    [the stated purpose / desired-outcome / goal — what success looks like]

now:         [one paragraph — where things actually are today — fed LAST]
```

**Feed order is load-bearing.** The investigator reads: origin → dead_ends → intended → now (LAST).
The investigator must understand where things were going before seeing where they are, to avoid
anchoring on the current state.

**Thin-plot degradation note** (measured 2026-06-22): if the plot has no formal `dead_ends`
section, the PROVOKE beat degrades from "X was tried and failed, and you're doing it again" to
"you don't have evidence this is working." This is honest and still useful, but structurally thinner.
Name the degradation when it occurs: "NOTE: no dead_ends in this plot — PROVOKE is working from
absence, not from specific failures."

---

## Assembling the plot (when no plot file is given)

The plot is a **READ, not a stored file** — assemble it at call time from what already accretes. You
need three inputs; pick the **grain** (the caller's altitude) and the **scope** (what the plot is about).

**1 — `intended` (the fixed destination), by scope:**
- a single project (slug) → that project's `brief.md` `## DESIRED OUTCOME` block (resolve the slug's
  folder via `<notes>/system/project-registry.md`).
- a subject folder → `<notes>/desks/{subject}/canon/purpose.md`.
- whole-system → `<notes>/canon.md` — the few things true across everything.

**2 — `origin → now` (the dots): read the last 2–3 diary rollups at the chosen grain**, if a diary
exists — `<notes>/desks/cal/diary/{YYYY}/{MM}/review-{week|month}-{period}.md` (quarter/year live one
folder up). ⏳ **The diary is written by `cal-daily` / `cal-weekly`, which land later in phase 3.**
Until they do, this branch finds nothing — which is not an error. Say the diary is absent and take the
heavy-search fallback below, which reads what already exists.
- whole-system scope → each rollup's `## What happened` + `## Activity by subject`.
- single-project scope → each rollup's `## Activity by project` → the `### {slug}` block; a rollup
  that lists the slug under **"Quiet this period"** is a real `now = dormant` dot — record it.
- **oldest** rollup seeds `origin`, **newest** is `now` (fed LAST). Target 2–3 dots.

**3 — `dead_ends`:** pull from the target's `brief.md` `## DEAD ENDS` section + journal rows tagged
`failed:` / `DEAD END` / `PIVOT` for the slug (`<notes>/system/journal.md` and its rotated segments).

**Altitude is information, not just resolution — say which you read + what it answers:**
- **monthly = theme** ("is the trajectory pointed the right way?").
- **weekly = cadence** ("is the work pattern sustainable — bursty, where are the gaps?").
State the grain in REFLECT so the reader knows which lens produced the investigation.

**Confidence:** a rollup's dots are machine-deterministic → **LOW** confidence until a person's
check-in verified that period (a `## Human Delta` block present = verified/**HIGH**). A
backfilled/reconstructed dot is always LOW. If the investigation rests mostly on LOW-confidence dots,
label it so.

Set `plot_assembled` = today when assembled live, then run the four beats on the assembled plot.

---

## Heavy-search fallback (when the plot is thin, absent, or dead)

If the assembled plot is too thin (no rollups for the target, or a single dot), OR the producer looks
**stale/dead** (newest `generated_at` far past its cadence window), do NOT surface findings from cold dots. Fall back
to **one** sonnet sub-agent that reads the target's `brief.md` + its `canon` + the last ~10 journal
entries for the slug, and returns a freshly-assembled `origin → dead_ends → intended → now`. Say you
used the fallback. **This is the ONLY place `/throughline` spawns an agent** — one sub-agent, sonnet,
read-only, reading pre-distilled docs (never a fan-out grinding raw journals — the no-swarm rail holds).

---

## The Four Beats (run in this exact sequence — no reordering)

### BEAT 1 — REFLECT

Render the plot clearly and without judgment. This is the cognitive-load release: the reader
should finish REFLECT thinking "oh right, that's what this whole thing has been about."

**Do not editorialise. Do not flag problems yet.** Give the plot back, beautifully.

No criticism in REFLECT. No hedging. No praise either — this is a mirror, not a review.

---

### BEAT 2 — PROVOKE

Surface the question the owner is NOT asking — the unknown-unknown. One or two sharp questions
that the plot data justifies but that don't appear anywhere in the stated intent or dead-end list.

**Citation rail:** every provocation must cite a real dead-end or a real stated-goal gap.
No generic challenge ("have you thought about scaling?") that would apply to any project.
If you cannot cite a specific dead-end or gap, the provocation is not earned — do not surface it.

**"So what" filter** (measured fix, 2026-06-22): after drafting each provocation, apply this filter
before surfacing it:

> "Even if this is factually grounded and cited to a real dead-end — would it actually change a
> decision? If the owner accepted this point, would they do anything differently, or investigate
> anything differently?"

If the answer is no — if the observation is true but irrelevant to any choice the owner faces —
discard it. A technically-grounded irrelevance is noise, not a finding. This filter closes a gap the
earlier 5-point bar left open: it protected against factually wrong claims but not against
"right evidence, wrong conclusion" observations.

---

### BEAT 3 — IDEATE

Offer two or three *areas to investigate* — not solutions, not recommendations.
Direction-of-investigation only.

Format: "It might be worth asking whether X" or "You could investigate if Y."

**Altitude rail:** stay at altitude. No in-the-weeds implementation nitpicks.
Forest-not-trees. The investigator is irreplaceable at the system-and-purpose level,
not as a code reviewer or task-list generator.

Leave every decision to the human. Do not suggest what to do — suggest what to look at.

---

### BEAT 4 — DIVERGE

Surface the gap between stated intent and actual trajectory in BOTH directions:

- **Drifted from purpose:** where has the work moved away from the stated intent? Show the gap explicitly.
- **Purpose itself misaligned:** does the stated intent describe the right goal, regardless of execution? Surface the tension if not.

This beat shows the divergence — it does NOT assign a verdict, a score, or a conclusion.
The investigator names the gap; the human decides what to do about it.

**Healthy-target rail:** if there is no real gap between intent and trajectory, say so plainly.
Refusing to surface a finding when the target is healthy is a false positive — it is just as much
a failure mode as manufacturing tension where none exists.

**Citation rail applies here too:** every DIVERGE point must cite a real dead-end or goal-gap.
A DIVERGE finding that doesn't cite the plot is generic and doesn't count.

---

## Stance Rails (non-negotiable, woven through all four beats)

1. **Investigate and surface — do not conclude.** Show the gap between stated intent and actual
   trajectory. The investigator's job is to make the divergence visible; the human draws the verdict.
   Do not assign a score, a grade, or a prosecution outcome.

2. **Every finding in PROVOKE/DIVERGE must cite a real dead-end or a real stated-goal gap.**
   The anti-cry-wolf guard. Generic observations are not findings; they are noise.

3. **Pop altitude.** Forest-not-trees. No in-the-weeds implementation nitpicks. The investigator
   should be irreplaceable at the system-and-purpose level.

4. **Surface-never-execute.** Surfaces; human disposes. Never write back to source files.
   Never suggest a specific task list. Stay in the investigative register.

5. **No swarm, no deep-research mobilization.** Reads the pre-assembled or assembled plot.
   The ONLY agent it may spawn is the single read-only **sonnet** fallback (one sub-agent, when the
   plot is thin/dead — see "Heavy-search fallback"). Never a fan-out grinding raw journals.

6. **Context-blind.** Does not know who is asking or why (beyond the `--context` orientation).
   Evaluates the plot on its own terms.

---

## Write Target — ONE findings file, and nothing else

After running the four beats, write the findings to **one** file. **Never to the plot file,
the source brief, the canon, or any other record.**

```
<notes>/records/insights/throughline/{target-slug}-{YYYY-MM-DD}.md
```

`<notes>` is the folder `shared/brain_root.py` resolves — never the repo, never the current
directory. `{target-slug}` is derived from the plot's title or the `--context` string (slugified,
max 40 chars, lowercase, dashes).

**The file's shape.** Frontmatter first, then the four beats in order under `##` headings:

```markdown
---
topic: [<a slug from your own vocabulary>]
record_type: insight
status: draft            # a PERSON changes this to human-reviewed. Nothing else may.
target: <slug | subject | whole-system>
grain: <week | month | quarter | year | n/a — a file plot was supplied>
plot_assembled: YYYY-MM-DD
confidence: <LOW | HIGH>  # LOW unless a person's check-in verified the period the dots came from
created_at: YYYY-MM-DD
---

## REFLECT
## PROVOKE
## IDEATE
## DIVERGE
```

⚠ **`status: draft` is the whole contract.** Downstream consumers gate on `human-reviewed`, and this
skill may never write that value — it is the one word that says a person read this. A run that
writes `human-reviewed` has forged the review it exists to require.

**After writing, tell them:**

> Findings written to: {full path}
> Status: draft
> Next step: read it and set `status: human-reviewed` before anything downstream acts on it.

---

## Self-Check After Writing (optional, for calibration)

If the caller asks for a self-check, apply the 5-point bar + the "so what" filter:

| # | Bar point | Result | Note |
|---|---|---|---|
| a | Factually grounded | pass/weak/fail | |
| b | Cites dead-end/goal-gap per finding | pass/weak/fail | |
| c | Surfaces ≥1 genuinely useful tension | pass/weak/fail | |
| d | No cry-wolf on healthy target | pass/weak/fail | |
| e | Pops altitude | pass/weak/fail | |
| f | "So what" filter applied (PROVOKE points change decisions) | pass/weak/fail | |

A gate-pass output: (a)–(f) all at pass or weak, no fails.

---

## Hard Rules

- **Never mutate the plot source.** Any write to a plot file, brief, canon, record, or source
  is a violation. The write-scope guard hook (`system/hooks/guard_throughline_write_scope.sh`)
  enforces this — by code, while armed.
- **Writes ONLY to the findings path** defined above.
- **Staleness is surfaced, never refused.** A stale/cold/dormant plot is a *finding*, not a stop.
- **No swarm.** No subagent fan-out, no websearch. The ONE exception: the single read-only sonnet
  fallback sub-agent when the plot is thin/dead. Otherwise read the plot; surface the findings.
- **Surfaces-never-concludes.** Do not produce a task list, a sprint, a verdict, or a score.
  The output is an investigation, not a plan and not a judgment.
- A subagent that invokes `/throughline` must be **sonnet**.

---

## What this skill needs outside its own folder

| what | where | status |
|---|---|---|
| the arm/clear switch | `system/hooks/throughline_flag.sh` | ✅ here |
| the write-scope guard it arms | `system/hooks/guard_throughline_write_scope.sh` | ✅ here |
| the notes-folder resolver | `shared/brain_root.py` | ✅ here |
| where the findings land | `docs/data-layout.md` | ✅ here |
| the diary the plot is assembled from | `cal-daily` / `cal-weekly` | ⏳ lands later in phase 3 — until then the heavy-search fallback is the path |
| a project's brief, canon and journal | under your own notes folder | ⛔ never ships — it is your material |
