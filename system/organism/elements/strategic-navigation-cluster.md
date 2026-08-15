---
element: strategic-navigation-cluster
title: "strategic-navigation-cluster — /first-principles + /telos + /throughline (ground/base altitude)"
subsystem: strategic-navigation
altitude: base
record_type: organism-element
maturity_label: PARTIAL [provisional]
generated_from:
  - skills/first-principles/SKILL.md (v1.0.0)
  - skills/telos/SKILL.md (v1.0)
  - skills/throughline/SKILL.md (v1.1)
  - system/hooks/throughline_flag.sh (UPDATED 2026-06-22)
  - system/hooks/guard_throughline_write_scope.sh (UPDATED 2026-06-22)
  - ~/.claude/settings.json (lines 175-179 PreToolUse Write/Edit; line 206 ExitPlanMode; line 342 UserPromptSubmit)
  - state/debt-ledger.md (SKILL-SOP-FIXES)
created_at: 2026-07-24
updated_at: 2026-07-24
status: draft
authority: user
---

# strategic-navigation-cluster — element detail

> **LADDER: ELEMENT (full mechanics). up → manual#strategic-navigation-cluster ; ground truth → the three live skill artifacts (generated_from)**
>
> **Altitude = BASE (ground / street view).** The in-the-weeds mechanics of the three strategic-navigation
> skills that operate ABOVE the task plane: `/first-principles` (find the real problem before building),
> `/telos` (steward the year-long brief), and `/throughline` (plot-tension investigator, read-only by
> enforced guard). They share no runtime machinery with each other, but form a logical cluster: they all
> answer "are we doing the right thing, in the right direction, in the right place?" before or between
> execution. `/checkin` was previously listed here; it is homed in the memory-read element (read.md) —
> see pointer below.
>
> **One-line:** three orienting skills — diagnose → year-anchor → tension-surface —
> none of which writes code or executes work, two of which are structurally read-only.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory script) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause).

> **CITATIONS — what the paths below resolve to here.** This element describes the donor system; the line below records what happened to each named file at THIS destination, and it covers every mention of them in the body.
>
> ⛔ `state/telos.md` — runtime-generated, created on first run, never committed. It is the reader's OWN year-long brief and lives in their notes folder (`.claude/skills/telos/SKILL.md` line 23: *"inside your own notes folder — never in this repo"*); `system/templates/telos-starter.md` is the shipped seed the skill writes it from. Absent from a fresh checkout is CORRECT, not missing.

---

## AUTHORED   (human-only)

### /checkin — pointer (homed in memory-read)

`/checkin` → full step-chain, triggers, stores, enforcement, and interop live in the **memory-read element** (`elements/read.md.draft`). It is memory+state machinery (session re-orientation + pm/plan flag arming), not direction-questioning — primary home is memory-read, not this cluster.

---

### THE THREE SKILLS — ROLE SUMMARY

These three skills share the strategic-navigation subsystem by **operating at altitude** — they are
invoked to question, orient, or surface tension BEFORE or BETWEEN execution, never during it.

---

#### /first-principles — Interrogative Intelligence Coach

**Role:** intercepts any request before execution and drives the user toward the real goal through
a structured coaching conversation. It never answers the stated request; it improves the question.

**Trigger:** explicit `/first-principles` · "am I even asking the right question" · "what should I build
first?" Invoked by the user at the START of a project or when lost.

**Shape:** `interactive-workflow` (SKILL.md v1.0.0). Only tool allowed: `AskUserQuestion`.

**Five phases (fixed sequence, no reordering):**
1. **INTAKE** — receives the raw request without judgment; opens with the stated coaching frame.
2. **SURFACE** (Round 1 — max 3 questions) — surfaces what sits behind the stated ask. Three questions
   chosen for relevance, always paired with a mandatory starters block (never ask without the starters).
3. **PROBE** (Round 2 — max 3 questions, branch-routed) — routes to the branch that fits:
   - **Branch A — Goal is fuzzy:** questions target what was tried + who benefits + what comes next.
   - **Branch B — Goal is clear, scope may be wrong:** tests for smallest viable move + prerequisites.
   - **Branch C — Scope is right, structure is missing:** tests for intelligence types + failure modes.
   All branches: mandatory questions + starters block together, every time.
4. **CONVERGE** — names three things: stated ask / actual goal / the gap. Then picks one of three
   output types: (A) better-formed question (rewritten prompt, ready to use); (B) build this first
   (smallest prerequisite named, not a full plan); (C) advisory structure (roles + one specific
   question per role).
5. **HANDOFF** — delivers the artifact + two clean exits: act on it now / go one level deeper.
   Never loops back into more questions after the artifact unless the user explicitly chooses Option 2.

**Hard rules:**
- Maximum 3 questions per round. Hard cap.
- Every question round paired with a starters block. Never ask without it.
- Session ends only when a concrete artifact is delivered (reframed question / "build this first" /
  advisory structure). Never loop forever.
- Never answer the stated request directly. Never produce a plan instead of an artifact.
- Never tell the user their goal is wrong — surface it and let them decide.

**Enforcement:** ALL honor. No hooks, no write guards. The skill is stateless and produces no writes.
A session that skips phases or delivers the stated request directly has no mechanical backstop — the
contract is the skill prose only.

**Write authority:** none. `/first-principles` does not write any store.

---

#### /telos — Year-Brief Steward

**Role:** reads the current year-long TELOS strategic brief (`$DRIVE/state/telos.md`), asks four
structured questions, proposes a full draft showing exactly what changes, and waits. Writes ONLY on
explicit user approval. If the current version is still accurate, it does nothing.

**Trigger:** explicit `/telos` · "what am I optimizing for?" · "re-anchor priorities."

**Shape:** `interactive-workflow` (SKILL.md v1.0).

**Content root:** Drive only. `$DRIVE` =
`$LIFEHACK_ROOT`.
`state/telos.md` lives there, never in the code clone.

**Four-phase execution:**
1. **READ CURRENT** — reads `$DRIVE/state/telos.md`, displays it.
2. **LIFE MAP** — fetches Google Tasks via `safe_tasks.py` (Monthly Win + Yearly Win only; daily/weekly
   are tactical — ignored). Free-text is isolated: `safe_tasks.py` returns structured fields on stdout
   with a `_reader_scratch` path instead of raw title/notes; a spawned `ingest-reader` subagent (haiku)
   reads the scratch. (SKILL.md lines 44-55; `system/ingestion-reader-contract.md`)
3. **FOUR QUESTIONS** — asks: (1) what are you optimizing for over the next year; (2) hard constraints;
   (3) what does a good month look like; (4) in an ideal world, what are you NOT doing.
4. **PROPOSE DRAFT** — shows a full proposed update as a complete draft (not a diff). User edits inline
   if needed, then approves.

**Write:** on explicit approval (`"yes"` / `"write it"` / `"looks good"`) only — overwrites
`$DRIVE/state/telos.md` and updates `updated_at` in frontmatter. Appends a one-line changelog to the
`## Changelog` section on every write (the non-fakeable write trace). Never touches `created_at` or
`review_by` unless user asks. (SKILL.md lines 36-40, 72)

**Hard rules:**
- Never write without explicit approval. NEVER auto-update.
- Never pull from desk-specific records, thought experiments, or living-abroad scenarios — Life Map +
  user answers only.
- Keep it outcome-focused: no tactical plans in the TELOS. Every sentence states a desired STATE, not
  a method ("maintain a daily writing habit" ✗ → "be a working writer whose output compounds" ✓).

**Enforcement:** write is honor-gated (explicit-yes rule is skill-prose, not a blocking hook). The
`ingest-reader` pattern is the reader-actor security wall for the Life Map free-text.

**Stores touched:**
- READ: `$DRIVE/state/telos.md` · Google Tasks (Life Map) via `safe_tasks.py`.
- WRITE: `$DRIVE/state/telos.md` (on approval only).

**GAPS:** The write gate is honor-only — a session that writes `telos.md` without an explicit yes has
no hook to stop it. There is also no `guard_telos_write.sh` in the hook plane. The sole enforcement is
the skill prose. (INFERRED from absence of a hook registration for telos writes in settings.json.)

---


#### /throughline — Plot Tension-Surfacer (read-only, hook-enforced)

**Role:** a read-only, context-blind investigator. Given a plot (pre-assembled or assembled live from
the Cal diary) and a `--context` string, it runs four beats and writes findings to a scratchpad ONLY.
Never writes back to source files, never concludes, never produces a task list. Surfaces; human disposes.

**Trigger:** `/throughline` · `/throughline --context "..."` · "evaluate this" · "run the throughline on"
· "surface the tension in this plot / project."

**Shape:** `interactive-workflow` (SKILL.md v1.1). Runs in the MAIN session (NOT a subagent).

**Write-scope guard — arm at start, clear at end (do not skip):**
`/throughline` MUST arm `throughline_flag.sh` BEFORE reading the plot, and MUST clear it after writing
the scratchpad (or on abort):
```bash
bash ~/lifehack-brain/system/hooks/throughline_flag.sh arm    # at start
bash ~/lifehack-brain/system/hooks/throughline_flag.sh clear  # at end or abort
```
Flag location: `~/.claude/run/eval/eval-sess-<CLAUDE_CODE_SESSION_ID>.flag`. TTL: 30 minutes
(configurable via `$EVAL_TTL_MIN`; self-expires so a forgotten `clear` is harmless). A cwd-hash
fallback fires when `$CLAUDE_CODE_SESSION_ID` is empty. (throughline_flag.sh lines 17-36)

`guard_throughline_write_scope.sh` (settings.json:175-179, PreToolUse Write|Edit matcher) — WHILE the
flag is armed, any write/edit outside the scratchpad dir is hard-blocked. Fails CLOSED on
unparseable input during an armed run. Pure NO-OP for all other sessions (flag not present → exit 0).
Scratchpad dir: `$DRIVE/state/projects/infrastructure/evaluator/scratchpads/`.

**Invocation:**
```
/throughline --context "<plain-language caller context>" [<plot-path>]
```
`--context` is required (orientation, not a filter). `<plot-path>` is optional — if omitted AND caller
names a **target** (slug / desk / `whole-system`) + **grain** (week/month/quarter/year), the skill
assembles the plot from the Cal diary.

**Staleness handling:** never refuse on age. A stale/cold/dormant plot is a FINDING, not a stop.
Surface it in REFLECT. If the producer looks dead (newest rollup's `generated_at` far past cadence):
fall back to the single read-only sonnet sub-agent (the only place `/throughline` may spawn an agent).

**Plot input format (feed order is load-bearing):**
`origin` → `dead_ends` → `intended` → `now` (NOW is read LAST, to avoid anchoring on current state).
Thin-plot degradation (no `dead_ends`): PROVOKE degrades from "X was tried and failed" to "you don't
have evidence this is working" — name the degradation when it occurs. (SKILL.md lines 86-112)

**Assembling the plot from the Cal diary (when no plot-path given):**
- `intended` by scope: project slug → brief `## DESIRED OUTCOME`; desk → `desks/{desk}/canon/purpose.md`;
  whole-system → `records/canon/purpose.md` + `state/telos.md`.
- `origin → now` (the dots): last 2–3 diary rollups at the chosen grain
  (`desks/cal/diary/{YYYY}/{MM}/review-{week|month}-{period}.md`).
  Whole-system → each rollup's `## What happened` + `## Activity by desk`.
  Single-project → each rollup's `## Activity by project → ### {slug}` block.
  Oldest rollup seeds `origin`; newest is `now` (fed last).
- `dead_ends`: target brief `## DEAD ENDS` + journal rows tagged `failed:` / `DEAD END` / `PIVOT`.
- Confidence: `HIGH` only if a `## Human Delta` block is present in the rollup; otherwise `LOW`.
  (SKILL.md lines 115-144)

**The four beats (run in EXACT sequence — no reordering):**
1. **REFLECT** — render the plot clearly and without judgment. The cognitive-load release. NO
   editorialising, NO problem-flagging, NO praise. A mirror, not a review.
2. **PROVOKE** — surface the question the owner is NOT asking (the unknown-unknown). Every provocation
   must cite a REAL dead-end or goal-gap. Then apply the "so what" filter: would the owner DO anything
   differently if they accepted this point? If no → discard (technically-grounded irrelevance is noise).
3. **IDEATE** — offer 2–3 AREAS TO INVESTIGATE, not solutions. "It might be worth asking whether X."
   Stay at altitude — no in-the-weeds implementation nitpicks.
4. **DIVERGE** — surface the gap between stated intent and actual trajectory in both directions:
   where work moved away from intent AND whether intent itself is misaligned. Does NOT assign a verdict,
   score, or conclusion. Healthy-target rail: if there is no real gap, say so — refusing to surface
   a finding on a healthy target is a false positive. (SKILL.md lines 159-228)

**Write target — scratchpad ONLY:**
Path: `{DRIVE_ROOT}/state/projects/infrastructure/evaluator/scratchpads/{target-slug}-{YYYY-MM-DD}.md`.
After writing, tells the human: findings written to `{full path}` · `status: draft` · next step: review
and set `status: human-reviewed` before any downstream consumer (cal-review, etc.) can gate on it.

**Stance rails (woven through all four beats; non-negotiable):**
1. Investigate and surface — do not conclude. No score, grade, or prosecution.
2. Every PROVOKE/DIVERGE finding must cite a real dead-end or stated-goal gap.
3. Pop altitude — forest not trees. No in-the-weeds nitpicks.
4. Surface-never-execute — never write back to source files. Never suggest a task list.
5. No swarm — no sub-agent fan-out, no websearch. ONLY exception: the single read-only sonnet
   fallback when the diary-plot is thin/dead.
6. Context-blind — evaluates the plot on its own terms.

**Hard rules:**
- NEVER mutate the plot source.
- Writes ONLY to the scratchpad path above.
- Staleness surfaced, never refused.
- No subagent fan-out. The one sub-agent exception (sonnet, read-only) is the diary fallback only.
- Subagents that invoke `/throughline` must be sonnet (doctrine standard).

**Enforcement:**
- `guard_throughline_write_scope.sh` (settings.json:175-179) — PreToolUse Write|Edit hook, fires only
  while `throughline_flag.sh` is armed. Hard-blocks any write outside the scratchpad dir. Fails CLOSED
  on unparseable input. (guard_throughline_write_scope.sh lines 1-42)
- `throughline_flag.sh` — the session-scoped on/off switch. File-based (env vars don't survive tool
  calls; same proven pattern as `pm_flag.sh`). TTL: 30 min. (throughline_flag.sh lines 16-36)

**GAPS:** The guard fires only when the flag is armed AND the tool is Write|Edit. A session that forgets
to run `throughline_flag.sh arm` (or runs `clear` prematurely) has no guard protection at all — the
arm/clear step is skill-prose mandatory but mechanically unenforced. The skill is also the caller's
responsibility to arm; no hook pre-arms it automatically. (INFERRED from hook code: throughline_flag.sh
line 16, guard_throughline_write_scope.sh lines 28-30)

**Stores touched:**
- READ: plot file (or Cal diary rollups + brief + journal for assembly) · `state/telos.md`
  (whole-system scope) · `desks/cal/diary/…`.
- WRITE: `$DRIVE/state/projects/infrastructure/evaluator/scratchpads/{slug}-{date}.md` ONLY.

**Known debt:**
- **[SKILL-SOP-FIXES]** `/throughline` needs a per-turn anchor added (wave-2 of the 2026-07-12
  skill-audit; `debt-ledger.md` line 214, `state:actionable`).

---

### INTEROP SEAMS (cluster-level)

The three skills do not call each other, but they share a coherent operating posture. `/checkin`
interop seams live in the memory-read element (`elements/read.md.draft`).

**`/telos` → `memory-read` / `/checkin` (FEEDS):** the TELOS (`$DRIVE/state/telos.md`) is the
year-long desired-state brief that `/checkin` (memory-read element) uses as the "whole-system desired
outcome" when scope is root-level. `/telos` updates it; the memory-read element reads it.

**`/throughline` → `project-manager` / `memory-read` (READS):** `/throughline` reads the brief's
`## DESIRED OUTCOME` + `## DEAD ENDS` blocks when assembling the plot from the Cal diary (single-project
scope). It reads; it never writes the brief.

**`/throughline` → Cal diary (READS):** `desks/cal/diary/…` rollups are the primary `origin→now` data
source for diary-assembled plots. The diary is written by the `cal-weekly` / pulse-cron pipeline;
`/throughline` reads it read-only.

**`/first-principles` → (any execution skill) (FEEDS):** `/first-principles` produces a sharpened
question / "build this first" / advisory structure that the user then carries into the execution layer.
No runtime handoff — the artifact is verbal, passed by the user. `/first-principles` itself writes nothing.

**`/throughline` ← `guard_throughline_write_scope.sh` (GUARDED-BY):** the hook enforces the read-only
contract while the flag is armed.

**`/telos` ← safe_tasks.py + ingest-reader (CHAINS):** the Life Map free-text is reader-actor isolated;
`/telos` chains through `safe_tasks.py` (structured fields) → ingest-reader subagent (free-text) before
consuming task notes. (security-canon.md; ingestion-reader-contract.md)

---

### PORTS TOUCHED

| Skill | Reads | Writes | Arms |
|-------|-------|--------|------|
| `/first-principles` | user input only | nothing | nothing |
| `/telos` | `$DRIVE/state/telos.md` · Google Tasks (Life Map) | `$DRIVE/state/telos.md` (on approval) | nothing |
| `/throughline` | plot file or Cal diary rollups · brief (dead_ends/desired outcome) · `state/telos.md` | scratchpad ONLY (`…/evaluator/scratchpads/`) | `throughline_flag.sh` (self-clears) |
| `/checkin` | → see memory-read element (`elements/read.md.draft`) | | |

---

### ENFORCEMENT POINTS

| Guard | Type | Scope | What it catches |
|-------|------|-------|-----------------|
| `guard_throughline_write_scope.sh` | `[hook]` PreToolUse Write/Edit | Fires ONLY while `throughline_flag.sh` is armed | Blocks any write outside scratchpad dir during a `/throughline` run |
| `throughline_flag.sh arm/clear` | `[skill]` Bash | Self-arming (no auto-trigger) | Session-scoped on/off state for the write guard; 30-min TTL backstop |
| Telos write gate (explicit-yes) | `[honor]` | `/telos` skill prose | Prevents write without "yes" / "write it" / "looks good" |
| `/first-principles` 3Q cap | `[honor]` | Skill prose | Max 3 questions per round |

---

### GAPS (documented fail-open conditions)

1. **`/throughline` — guard is OFF unless armed.** If the skill forgets `throughline_flag.sh arm`
   (or runs `clear` prematurely), `guard_throughline_write_scope.sh` is a pure NO-OP — nothing blocks
   a `/throughline` session from writing source files. The arm step is mandatory skill prose, not a
   pre-arming hook. **Blast radius:** a rogue write to a plot/brief/canon file with no guard. Medium.

2. **`/telos` — no write hook.** A session that writes `state/telos.md` without an explicit-yes has no
   mechanical block. Sole enforcement is the skill's explicit-yes prose rule. **Blast radius:** telos
   overwritten without approval. Medium (recoverable from git; Drive recycle bin).

3. **`/first-principles` — entirely honor.** No writes, no hooks; if the session skips phases or
   answers the stated request directly, nothing prevents it. Low blast radius (no writes).

4. **`/checkin` gaps** → documented in the memory-read element (`elements/read.md.draft`).

---

### INTENT / CURRENT-VS-TARGET

**Intent:** provide the three altitude tools that let a practitioner question, anchor, and surface
tension BEFORE or BETWEEN execution — so the system optimizes for the right outcomes, not just
efficient execution of the wrong ones. (`/checkin` re-orientation is served by the memory-read element.)

**Current:** all three skills are operative. `/throughline`'s read-only contract is hook-enforced
(the strongest enforcement in this cluster). `/telos` writes are honor-gated. No mechanical per-run
skill auditor exists. Per-turn anchors are PRESENT in `/telos` (L14), `/throughline` (L17), and
`/first-principles` (L20). SKILL-SOP-FIXES wave-2 is complete for these three skills (debt-ledger
entry at L214 is stale for them — gap is now only `/checkin`, tracked in the memory-read element).

**Target:** (a) resolve SKILL-SOP-FIXES for `/checkin` (memory-read element, not here); (b) consider
a telos write-hook analogous to `guard_throughline_write_scope.sh` if the honor-gate fails in practice.

---

## AUTO-COMPUTED   (machine-only — written by Feature 1.5 checker; DO NOT EDIT)

```
maturity_label : PARTIAL [provisional]
check_detail   : n/a
```
