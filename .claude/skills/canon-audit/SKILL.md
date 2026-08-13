---
skill: canon-audit
description: "Deep seven-dimension audit of one desk's full canon tree — grades staleness/altitude/misplacement into a proposal for /archivist-review. Use on \"/canon-audit desk=<name>\". Propose-only."
shape: interactive-workflow
status: active
topic: [archivist]
version: 0.3
summary: Propose-only deep audit of a desk's FULL canon tree — altitude, crowding, cohesion, missing-spine, source-integrity, purpose-fit, and temporal-home (durable vs live vs time-bound) — emitting a graded change-list into the /archivist-review queue.
triggers:
  - "/canon-audit"
  - "audit the canon"
  - "audit a desk's canon"
  - "is this canon crowded"
  - "this canon is a dumping ground"
  - "canon getting messy / bloated"
  - "split this canon"
  - "canon altitude check"
  - "is this fact stale / time-bound / belongs in the diary"
---

## Intent (§0.5)
**User outcome:** A desk's canon tree drifts — facts at the wrong altitude, time-bound snapshots sitting as if permanent, files fusing disjoint topics, figures frozen stale. canon-audit does the thorough desk-by-desk pass the weekly structural audit defers: it grades the full canon tree on seven dimensions and emits a prioritized, actionable change-list for the supervised review session. **Bar:** "I know exactly what's wrong with this desk's canon and where each thing belongs — not a vague 'it needs cleanup'."
**Role:** the rigorous on-demand inspector — judgment-heavy, calibration-driven (a living version + calibration log that grows each run). It fills the gap between archivist-audit (weekly structural) and archivist-declutter (line-level, always-loaded): folder/file depth across one desk's whole canon tree, judged against the authored intent bars. It fans out sonnet agents (waves of 2–3, never 6+), forces a structured schema, merges + grades, and stops at the proposal — never loops into execution.

# canon-audit

> **Where things resolve.** Every `desks/…`, `system/…`, `state/…` path below is under `<notes>` — the folder `shared/brain_root.py` returns — unless it starts with `$ROOT` (this repo). This skill READS content and WRITES exactly one proposal log; it never edits canon.

The **deep, on-demand auditor of a single desk's entire canon tree** — `desks/{desk}/canon/current.md` + every sub-folder canon + `desks/{desk}/projects/**/canon.md`. It grades the tree on seven dimensions and emits a prioritized change-list **into the `/archivist-review` queue**. It is the reusable engine for the by-hand "canon-currency" cleanup (a subject, 2026-06-25), generalized to any desk.

**It fills a real gap, between two existing skills — do NOT duplicate them:**
- `archivist-audit` (weekly, whole-filesystem) only trip-wires canon crowding lightly (check J = "one judgment while reading"). canon-audit does the *thorough* desk-canon pass that J defers.
- `archivist-declutter` audits **lines**, but only in the **always-loaded layers** (global/root/desk `CLAUDE.md` + `canon/current.md`) and **excludes** sub-folder/project canons. canon-audit works at **folder/file depth across the whole desk tree** — explicitly NOT line-level always-loaded work.

**This skill is judgment-heavy and iterative.** It is not specified perfect up front — it ships rough and sharpens across real reps (observe-then-codify). See **§ Calibration log** at the bottom: after each run, fold a miss back and bump `version:`.

---

## Invocation

```
/canon-audit                      # all desks, processed one desk at a time (sequence)
/canon-audit scope=desk:<subject>   # one subject folder's full canon tree
```

`scope=desk:{name}` mirrors `archivist-audit`'s syntax (colon, lowercase desk). Bare invocation = sweep every desk in `desks/*/`, **one desk at a time** (never all at once).

---

## Hard rules

- **READ-ONLY / PROPOSE-ONLY.** Never edit, move, or delete a canon file. The ONLY write is the proposal log on Drive. Execution is `/archivist-review`'s job — this skill ends at the proposal.
- **Subagents sonnet-only, waves of 2–3, never 6+** (the proven headless ceiling; per `archivist-deepmine`). Fan out via the **Agent tool**, not Workflow.
- **Read the bars, never regenerate them.** Read `<notes>/system/archivist/home-intents.md` (the authored `intent:`/`not:` bar per home) + `<notes>/system/canon-purpose-map.md` (the Territory Map: `accepts:` + STATED|INFERRED). Regenerating the map is `archivist-audit`'s job — never this skill's.
- **Stay in the fence.** No line-level always-loaded-layer audit (that's `archivist-declutter`). No whole-filesystem structural audit (that's `archivist-audit`). One desk's canon tree, at folder/file depth.
- **A clean desk is a valid result.** "Tidy — little to propose" is a correct output (like deepmine on a young desk). Do not manufacture findings.

---

## What it audits — the full canon tree

For the target desk, the audit covers:
- `desks/{desk}/canon/current.md` — the always-loaded floor.
- `desks/{desk}/canon/**/` — every sub-area canon (e.g. `income/`, `assets/`, `tax/`) + its `README.md` intent bar.
- `desks/{desk}/projects/**/canon.md` — every scoped project canon.

---

## The seven dimensions (plus corroboration — below-canon only)

Each fact / file / folder is judged on:

1. **Altitude-fit** — does it earn its level, or should it **sink** to a sub-area canon, a record, or a playbook? (Per `knowledge-altitude.md`: the admission question for the level it lives at.)
2. **Crowding** — is a canon file a dumping ground? Signals: (a) a line that FAILS the **standalone test** — a cold, zero-context session can't fully interpret it alone (the PRIMARY signal); (b) reads as a junk drawer; (c) for ALWAYS-LOADED canon only, over ~25 lines (a heuristic, NOT a hard rule — scoped/on-demand canon may be richer if every line is self-interpretable). Include a **chars/4 token estimate** of the always-loaded floor vs the ~20K context-rot budget.
3. **Cohesion / split** — does a canon hold **≥2 clusters with disjoint session-relevance** (things that'd never load in the same session)? If yes → name the clusters, propose a split. **Judgment, not math** — propose only; a split is a human call.
4. **Missing-spine** — is the desk's core situation a first-class floor fact, or absent? Absent = high-priority.
5. **Source-integrity** — do figures carry a source pointer / as-of, or are live-pullable numbers **frozen as stale snapshots**? Flag frozen figures.
6. **Purpose-fit** — does each file still serve the desk's purpose, or is it superseded / prescribing a dead action?
7. **Temporal-home (the new axis)** — classify each load-bearing FACT by its relationship to time, and route accordingly:

**Corroboration (below-canon only — does NOT apply to canon):** for any fact that sits BELOW the canon tier (a
`records/` finding, a dated-record insight, a snapshot), note whether it is **corroborated** (≥2 independent sources
agree) or **lone** (single-signal only). This is an **informational flag**, not a demotion trigger — the finding just
surfaces it so the human knows the confidence weight. Do NOT apply this dimension to canon: canon earns its trust
through the human-vetting gate (`vetted: true`), not corroboration count (confidence-model.md Layer A). Propose-only.

   Corroboration finding format: `corroboration: corroborated | lone_signal` + a one-line note on the source count.
   - **durable** — true for any session on this desk → **stays in canon** (this is canon's job).
   - **live** — a current-state number (net worth now, a balance) → **should be a pointer to the live source**, never a frozen value. Flag if frozen (the verify-don't-guess rule).
   - **time-bound / half-life** — true for a moment, then historical (a figure that was true in one year, a valuation "as of" a date, "represented by X in 2023") → **propose routing it to its dated home**, where staleness is structural (the date is in the path). **The dated home is the desk's OWN dated record/diary when the fact is desk-local** (e.g. `desks/<subject>/records/diary/2026-04-snapshot.md`), **OR the shared diary's period summary when it's a cross-desk/life fact** (e.g. `desks/cal/diary/2024/review-year-2024.md`) — choose by judgment, don't default to Cal. Each time-bound proposal carries a **confidence (H/L)**.

> Routing today is by type + altitude only. Temporal-home is the missing axis — durable→canon, live→sheet-pointer, time-bound→a **dated home** (desk-local record/diary, or the Cal diary for cross-desk/life facts).

---

## Procedure

**1. Resolve scope.** From the arg: one desk, or all desks in `desks/*/` processed in sequence. For each desk:

**2. Load the bars (read-only).** Read this desk's lines in `home-intents.md` + its homes in `canon-purpose-map.md`. These are what each canon home is judged against. If the map is missing/stale, NOTE it in the output — do not regenerate it.

**3. Slice + fan out (sonnet, waves of 2–3).** Spawn ONE read-only **sonnet** Agent per canon sub-area:
   - one auditor for the floor (`canon/current.md`),
   - one per sub-folder canon (`canon/income/`, `canon/assets/`, …),
   - one for the project canons (`projects/**/canon.md`).
   Launch in waves of 2–3; never 6+ concurrent. Each auditor is READ-ONLY (no Edit/Write/Bash-mutation).

   Each auditor's task: *"Audit «these canon paths» against «the home's intent bar». Return findings across the seven dimensions. For every load-bearing fact, classify temporal-home (durable|live|time-bound); for time-bound, propose its dated diary period home + confidence. READ-ONLY — propose only, touch nothing."*

   Force this StructuredOutput schema:
   ```
   {
     home: "<canon path audited>",
     token_estimate: <int, chars/4 of this home if always-loaded else null>,
     findings: [
       {
         dimension: "altitude|crowding|cohesion|missing-spine|source-integrity|purpose-fit|temporal",
         detail: "<the line/file/fact + why it misses>",
         proposed_action: "<sink to X | split into A,B | add spine line | repoint to source | DIARY-ROUTE to <dated home>>",
         temporal_class: "durable|live|time-bound|n-a",
         diary_target: "<dated diary path | n-a>",
         confidence: "H|L|n-a",
         severity: "P1|P2|P3",
         dep_gate: "clear|KEEP",      // KEEP = hook-paired rule, never sink
         reversible: "y|n"
       }
     ]
   }
   ```

**4. Merge + grade (you, the orchestrator).** Dedupe across auditors; reconcile conflicts. **When a file is oversized BECAUSE it holds disjoint clusters, crowding (D) and cohesion (J) share one root — emit ONE merged split proposal (`source-check: canon-audit/D+J`), not two overlapping findings.** Assign a **grade + one-paragraph rationale** (cite the specific files/facts that set it). Sum the floor token estimate and flag if over ~20K.

**5. Write the proposal** (the one write) → `<notes>/system/logs/archivist_{YYYY-MM-DD}_canon-audit-{desk}.md`, `record_type: proposal`. See the output format below.

**6. Hand off.** End here. Point them at the queue file to work through and act on. **Never loop into execution.**

---

## Output format (the queue shape)

Lead with a one-screen summary: the **grade**, floor token count (vs ~20K), and N findings by group. Then the grouped queue. **If the change-list contains any move/sink, the header MUST carry the reindex warning:**

> ⚠️ **File moves invalidate the obsidian-brain index — reindex before declaring the restructure done; a stale index misdirects to dead paths.**

Group findings under the review labels:
- **SCOPE-FIX** — oversized canon (densify), cohesion split-candidate (propose split), missing-purpose/spine.
- **ROUTE-REFILE-RELOCATE-SINK** — a fact/file that should sink to a lower canon home or a record + a pointer left behind.
- **DIARY-ROUTE** — a time-bound fact → its dated home (the desk's own dated record/diary, or the shared diary's period summary for cross-desk/life facts — by judgment); `confidence` is **mandatory** on these.

Each item carries all ten fields:
```
id · source-check(canon-audit/{D|J|R|spine|source|fit|time}) · detail · proposed-action · confidence(H|L|n-a) · risk(low|med|high) · reversible(y/n) · dep-gate(n/a|clear|BLOCKED) · vet(n-a) · disposition(pending)
```
(`vet` is always `n-a` here — vetting happens when a person works the queue, not in this skill.)

---

## Self-improvement (observe-then-codify)

This skill is expected to be imperfect at first and to sharpen across real reps. **After each real run**, if it missed or misclassified something, append a dated line to **§ Calibration log** below and bump `version:` in the frontmatter. Mirror `build-sop.md`'s self-extending pattern — the calibration log is the living memory of what this skill learned from real desks.

## Calibration log

Format: `- {YYYY-MM-DD} · v{x} · desk:{d} · MISS: <what it missed/misclassified> → FIX: <the one-line skill change applied>`

- 2026-06-26 · v0.2 · MISS: temporal-home defaulted time-bound facts to the **diary** specifically, but a real subject-local fact (a dated career snapshot, a dated history of who represented you) wants the **desk's OWN dated record/diary**, not a cross-desk write into Cal. → FIX: generalized the DIARY-ROUTE target to "desk-local dated record/diary OR the Cal diary (cross-desk/life facts only), by judgment — don't default to Cal."
- 2026-06-26 · v0.3 · MISS: crowding (D) and cohesion (J) fired as two separate findings for the SAME root (an oversize file that's oversize *because* it fuses disjoint clusters) → duplicate items in the queue. → FIX: merge step now emits ONE split proposal (`source-check: canon-audit/D+J`) when D and J share a root. (v0.2 fix confirmed working this rep: Cal's time-bound note correctly routed to the Cal diary while a subject's routed to a subject-local records.)

---

## Reference

- Consumes: `<notes>/system/archivist/home-intents.md` · `<notes>/system/canon-purpose-map.md` · the target desk's canon tree.
- Produces: `<notes>/records/proposals/archivist-{YYYY-MM-DD}-canon-audit-{subject}.md` (see the handoff note at the foot; formerly fed `/archivist-review`).
- Related: `/archivist-declutter` (line-level, always-loaded only) · `/archivist-audit` (weekly, whole-system) · `/archivist-deepmine` (the fan-out pattern this copies).

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

| what | where | status |
|---|---|---|
| the notes-root resolver | `shared/brain_root.py` | shipped |

Everything else it reads is your own canon, in your notes.
