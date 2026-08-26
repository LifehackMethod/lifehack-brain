---
element: build-plan-plane
title: "build-plan-plane — /build + /autoplan + the planning-execution contract"
subsystem: build-execution
altitude: base
record_type: organism-element
maturity_label: LIVE (honor)
generated_from:
  - skills/build/SKILL.md
  - commands/autoplan.md
  - system/sops/architecture-planning-sop.md
  - system/sops/build-sop.md
  - system/sops/build-conductor-sop.md
  - system/build-rules-index.md
  - system/hooks/guard_plan_structure.sh
  - system/hooks/inject_sop_before_build.sh
  - system/hooks/plan_flag.sh
  - system/hooks/guard_plan_fork.sh (RETIRED 2026-07-15)
  - system/hooks/announce_plan_write.sh
  - system/hooks/mirror_plans.sh
  - system/reference/settings.json (hook registrations)
  - $DRIVE/state/debt-ledger.md (AUTOPLAN-PLANMODE-SANDBOX · BUILD-PARKINGLOT · PLAN-DEMOTION-ENFORCE)
created_at: 2026-07-24
updated_at: 2026-07-24
status: draft
authority: user
---

# build-plan-plane — element detail

> **LADDER: ELEMENT (full mechanics). up → manual#build-plan-plane ; ground truth → the live artifacts (generated_from)**
>
> **One-line:** the planning + execution contract — `/autoplan` structures the plan and `/build` executes it
> autonomously; together they enforce Phase → Feature → Task discipline with verified ✅ on every task.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory script) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause).

---

## AUTHORED   (human-only)

### OVERVIEW

The **build-plan-plane** is the two-skill planning-and-execution harness: `/autoplan` (the planning front-end) and `/build` (the execution engine), bound by a shared contract: every plan is `Phase → Feature → Task` with a runnable `Verify` on every task, and no task is ✅ until its verify passes. Five hooks wire mechanical enforcement around the contract's entry and exit points; a parallel cluster of plan-management hooks keeps plans visible and durable. The two SOPs (`architecture-planning-sop.md`, `build-sop.md`) and the conductor (`build-conductor-sop.md`) are the runtime rule-books; the `build-rules-index.md` is the single routing table `/build` consults to know WHICH rules bind any given build.

**Upstream: `architecture-planning-sop.md`** is the scoping front-end that produces a vetted handoff prompt; that prompt is pasted into plan mode as `/autoplan`'s input. The SOP itself does NOT write a plan and does NOT build. This element covers what happens AFTER the handoff lands in `/autoplan`.

**Note on naming:** the `plan-integrity-cluster` element covers the hooks that enforce the plan's structural contract at `ExitPlanMode` (`guard_plan_structure.sh`, `plan_flag.sh`). This element describes those hooks as seams but does not duplicate their full mechanics — cross-reference `elements/plan-integrity-cluster.md` (UNVERIFIED — element not yet authored as of 2026-07-24).

---

### SKILL: `/autoplan` — the planning front-end

**Trigger:** the user types `/autoplan` (explicit slash-command invocation only). The command body is `commands/autoplan.md`. The phrases "plan this" / "make a plan" / "I need a plan" are NOT wired to auto-invoke it by any live mechanism.

**Step 0 — RE-ANCHOR + continuation check (runs BEFORE entering plan mode):**

1. **Re-anchor to live project state.** Run `bash system/hooks/pm_flag.sh status`. If a project brief is armed, read it in full (every section, especially `## SCRATCHPAD`). The plan MUST be built on current state, not a stale mental model. `[skill]`

2. **Continuation check.** Run `bash system/hooks/plan_flag.sh status`. If this session is already linked to a plan, DEFAULT to amending the existing plan — enter plan mode to edit it; do NOT mint a new file. Start a NEW plan only when the user explicitly says this is a separate effort. `[skill]` ⚠ **Caveat: this instruction is CONTRADICTED by the `[AUTOPLAN-PLANMODE-SANDBOX]` gap** — plan mode always mints a NEW plan file regardless of the continuation-check prose; the "amend in place" instruction does not hold in practice (see Gap 1 below).

   > Gap: `/autoplan` mints a NEW random-named plan file on every invocation; the continuation check is the skill's instruction to route into the existing file, but plan mode itself cannot be told which file to edit — it always saves to a new random path. This means the continuation rule is `[honor]`; `announce_plan_write.sh` makes forks VISIBLE after the fact. `guard_plan_fork.sh` was built to block this (2026-07-14) but was RETIRED 2026-07-15 because it trapped sessions in an inescapable loop (it blocked plan mode's own native save). The debt item `[AUTOPLAN-PLANMODE-SANDBOX]` tracks both the sandbox limitation and the mints-new-plan behavior. `(AUTOPLAN-PLANMODE-SANDBOX)`

3. **Enter plan mode.** Build the plan under Lifehack doctrine (reads the two ALWAYS SOPs implicitly through this skill's prose directives).

**Three standing directives the plan MUST honor:**

1. **Minimize main-session context rot.** Fan decided, self-contained work out to background sub-agents (gear-2) by default, launched async (`run_in_background`). Single-thread only genuinely coupled design. Gear-3 (Agent Teams) only on "use agent teams" / "team build". Gear-4 (dynamic workflow) only on `ultracode` / "use a workflow" AND read-only/autonomous work only. `[honor]`

2. **Spend human-in-the-loop efficiently — front-load and stage it.** Design the plan to run autonomously: each task `Execute → Verify & test → ✅`; executor stops only at (a) safe-halt conditions and (b) explicitly marked human checkpoints. Never stop at incidental phase boundaries. `[honor]`

3. **No Silent Demotion.** The plan may NOT quietly push in-scope work to "later." Requires: (a) enumerate every distinct thing the user named as "to build" and account for each one exactly once in the plan body OR in the `⚠ CUT FROM THIS BUILD` block; (b) cuts go LOUD and at the TOP (directly under the FRAME), not buried in the deferred list; (c) approving the plan ≠ approving the cuts (each cut is its own decision); (d) default is KEEP IT IN. `[honor]`

**Required plan shape (the output contract):**

Every plan `/autoplan` emits MUST carry:
- **FRAME block at the top** (one line each: desired outcome · success criteria · constraints · out-of-scope). Human-approved once, up front — gates the autonomous run. Satisfies `project-manager`'s Frame-intake gate so the brief is treated as authoritative. `[honor]`
- **`Phase → Feature → Task` hierarchy.** No flat task lists. `[hook]` — `guard_plan_structure.sh` blocks `ExitPlanMode` if Phase + Task + Verify markers are absent.
- **Every task = `Execute → Verify & test → mark-complete (- [ ])`**; the Verify must be a RUNNABLE check (a command / a rendered output to inspect), not "looks done." `[hook]`
- **Each task gear-tagged** (gear-1 / gear-2 / gear-3 / gear-4) — a HINT, not a command; `/build` re-decides per task from the work's actual shape. Default = gear-2. Gear-3 = opt-in only. Gear-4 = opt-in + read-only only. `[honor]`
- **A named safe-halt section** (checkable conditions, not a vibe). MUST explicitly list human-side Google writes (Sheets / Calendar / Gmail) — `/build` does NOT auto-pause for those. `[honor]`
- **`⚠ CUT FROM THIS BUILD` block** directly under the FRAME if anything the user named as "to build" is not in the executable body. `[honor]`
- **Deferred list** at the bottom — items tagged **TODO** (still viable → OPEN LOOPS) or **DEAD-END** (ruled out → DEAD ENDS). `[honor]`

---

### SKILL: `/build` — the execution engine

**Trigger:** "build", "execute the plan", "just do it", or the user stepping back after a plan is approved.

**Step 0 — Rules-of-Engagement gate (runs BEFORE any build action):**

1. **Name what you're building** from the `/build` argument. Ask the user ONE word if unclear (hook? skill? cron? memory/doc? gws? security? architecture? research/investigation? something else?). A build can be MULTIPLE types — match every type that applies. `[skill]`

2. **Read the index:** `$HOME/lifehack-brain/system/build-rules-index.md`. It maps build-type → binding docs. Paths relative to clone root `~/lifehack-brain/` — never Drive copies (legacy, being retired). `[skill]`

3. **FETCH the binding docs — read the actual files, do NOT rely on memory.** Always read the two ALWAYS docs (`build-sop.md` + `architecture-planning-sop.md`), then the docs for every matched row. A doc tagged `[UNVERIFIED]` may be stale — read it, but carry the caveat. `[skill]`

4. **Emit ONE `ORIENTATION:` block** before building: build type(s) detected · each doc fetched (with its trust tag) · the one-line binding constraint from each. One block, at the top only. `[skill]`

5. **Then build.** When a build teaches a durable reusable lesson, append it to `build-sop.md`; when it teaches a new binding rule or build-type, update `build-rules-index.md`. `[skill]`

> The Step-0 gate is **advisory** in v1 — an ORIENTATION block, not a code-gate. The hook `inject_sop_before_build.sh` (UserPromptSubmit, non-blocking) fires a pointer when a build-verb + tracked noun appears, landing ~84% coverage. The debt item `[BUILD-RULES-GATE]` tracks the escalation to a blocking gate if advisory proves skippable. `(BUILD-RULES-GATE)`

**Research-plan mode (non-construction plans):** if the plan is a research/investigation plan (not a software/artifact plan), "build" = run the research steps (search · fetch · cross-check · synthesize). "Verify" = sources checked & claims cross-validated, NOT "run the code." The construction docs in Step 0 do NOT bind a research plan.

**Execution discipline:**

Execute against a `Phase → Feature → Task` plan — never a flat task list. If no such plan exists yet, get one first (the Planning Output rule in `CLAUDE.md` + `architecture-planning-sop.md`).

Every task runs `Execute → Verify & test → mark ✅` — a task is NOT done until its verify passes. `[honor]` (The plan-structure hook fires at plan-creation time; the verify discipline during execution is honor.)

**Keep going through:**
- Routine implementation decisions (naming, structure, helpers)
- Creating, editing, deleting files within the working scope
- Running tests and fixing failures resolvable in this context
- Multiple sequential steps and commits
- **Crossing phase / feature boundaries** — a completed phase is NEVER by itself a reason to pause. Roll straight into the next phase unless the plan explicitly marked a stop.

**Stop and surface a checkpoint when:**
- A decision would change the plan's direction or scope
- A destructive or irreversible action is required (force push, drop table, delete data)
- A test failure cannot be resolved after genuine effort
- Credentials or secrets are needed that are unavailable
- About to write to an external system (push, deploy, send email)
- **The plan EXPLICITLY designates this step as a human-in-the-loop / Q&A checkpoint** — honor it; a phase boundary not marked this way is NOT a checkpoint
- The work reveals something material the user must weigh before proceeding correctly — not a routine status update
- **About to skip, defer, or "come back to later" an in-scope task** — surface it: "Task X is in-scope; I want to defer it because Y — OK, or build it now?" Default is build-it-now.

**Subagent model selection:** all subagents = **sonnet**, never opus. This is the global rule AND the `/build`-specific rule. Gear-4 workflow `agent()` calls inherit the session model (opus) by default — MUST pin `model: 'sonnet'` (haiku for pure read-only) on EVERY call or it silently burns opus at fleet scale. `[honor]`

**The four gears** (the conductor's routing table — `/build` re-decides gear per task):

| Gear | Fires when | What it is |
|---|---|---|
| **1 · Single-thread** | tightly-coupled design — shape / look-react-refine / anything needing show-react | you + the lead, one window. Never split coupled design — it diverges. |
| **2 · Sub-agent (fire-and-forget)** | decided, one-surface, self-verifiable chunk | lead fires a background Agent (sonnet), it works in fresh context, reports a summary. The workhorse. No tmux. |
| **3 · Agent-Team wave** (opt-in) | multiple independent surfaces that must coordinate — AND the user has said "use agent teams" / "team build" | ~7× tokens; requires tmux/iTerm2 from launch for long work (in-process teammates can't compact). |
| **4 · Dynamic workflow** (opt-in) | dozens-to-hundreds of independent items OR a repeatable cross-checked quality pass — AND user said `ultracode` / "use a workflow" | JS orchestration script, up to ~16 concurrent / 1,000 total sub-agents; read-only / autonomous ONLY (cannot pause mid-run). |

Gear-2 is the **automatic default** — reached for on own without a trigger phrase. Gear-3 opt-in gate: once open, COMMIT to the team (don't deflect back to gear-2 after the user requested it). Gear-4 opt-in gate: same; proactively SUGGEST when the shape fits (≫ ~20 independent items or a repeatable pass worth scripting), but fire only on unlock.

**No illusion of completion — the honest close:**

Before reporting a build complete, **reconcile against the plan** — walk every task and account for each as ✅ or ✗. Never report "done" while any in-scope task is ✗. The close is then "built X; did NOT build Y — here's why," with every unbuilt piece named LOUD at the TOP. A partial task is ✗, not ✅. Everything left ✗ files to the brief's OPEN LOOPS via `project-manager`. `[honor]` Debt item `[PLAN-DEMOTION-ENFORCE]` tracks the deferred hard enforcement (a hook that blocks a "done" report while in-scope tasks are ✗).

---

### SUPPORTING SOPs

**`build-sop.md`** (`system/sops/build-sop.md`) — Hard-won build doctrine, loaded on-demand by `/build` Step 0. Contains:
- General do's (apply to EVERY build): prove cheap integration BEFORE expensive run; prove live ONCE before automating; backup crown-jewel files before editing; no blanket-sed renaming refs across journal/diary/records (fix a wrong one by hand, visibly — only `canon/` is immutable, 2026-08-14 the operator ruling); SOP for bulk archive/drain/migration (loss-impossible protocol); batch LLM work (~10–15 items per call, NOT once-per-item); test hooks with faithful JSON not echo; no silent demotion carries into execution — the close must be honest.
- Domain sections: background/cron runners (Pulse `*-run.sh`) — machine-gate, exit codes, retry, emit modes, atomic writes, `verify-connections.py`.
- **Living doc pattern**: builds append new lessons here; it is how `/build` gets smarter over time.

**`architecture-planning-sop.md`** (`system/sops/architecture-planning-sop.md`) — Scoping front-end: fuzzy idea → vetted architecture doc-set (TRD/SAD) → Stage-8 handoff prompt. Three tiers by blast radius: Tier 1 (quick/reversible), Tier 2 (standard feature), Tier 3 (load-bearing multi-subsystem). Powers `/advisory-council` (Stages 1, 4, 6). Output is a handoff prompt, NOT a plan. **This SOP does NOT write a plan and does NOT build anything** — that is downstream in `/autoplan` → `/build`.

**`build-conductor-sop.md`** (`system/sops/build-conductor-sop.md`) — The operating mode `project-manager` arms for any orchestrated build. Defines the four gears in full, the two altitudes (Build Lead vs Observation Deck — conflating them is the swamp entry point), the large-build flow (plan-first → decompose by surface → lock data contracts BEFORE parallel writes → fan out → merge gate → worker loop), and coordinator discipline ("stay at altitude; lead from research/facts, not from the user's momentary mood"). The worker loop: execute → verify against ground truth (run it / render it / read the real output — NOT the code, NOT a self-report) → fix → repeat, ~5-iteration cap.

**`build-rules-index.md`** (`system/build-rules-index.md`) — The routing table `/build` consults in Step 0. Maps build-type → binding docs + trust tags (`[VERIFIED date]` / `[UNVERIFIED]` / `[PARTIAL §x]`). Two ALWAYS rows (build-sop + architecture-planning-sop) plus domain rows (hook, skill, desk, cron, memory/doc, gws, security, email-ingest, Google Sheet, architecture, orchestrated build, design/dashboard). The **single place to update** when docs move or get verified — `/build` never hardcodes paths.

---

### HOOKS (plan-shape enforcement)

Plan-shape enforcement hooks (`guard_plan_structure.sh`, `plan_flag.sh`, `announce_plan_write.sh`, `inject_sop_before_build.sh`, and the retired `guard_plan_fork.sh`) are the concern of the **`plan-integrity-cluster`** element — see `elements/plan-integrity-cluster.md.draft` for full per-hook mechanics, enforcement postures, registration details, and gaps. This element covers the `/autoplan` + `/build` skill capabilities and references those hooks only as seams.

---

### STORES + PATHS

| Store | Path | Written by | Read by |
|---|---|---|---|
| Plan files | `~/.claude/plans/*.md` | plan mode (ExitPlanMode) | `/build`, `/checkin`, `/read`, HUD |
| Plan-management flag | `~/.claude/run/plan/plan-<key>.flag` | `plan_flag.sh record / set` | `plan_flag.sh status/path`, `system/statusline.sh`, `/advisory-council` |
| Plan announce state | `~/.claude/run/plan-announce/<key>.state` | `announce_plan_write.sh` | `announce_plan_write.sh` (diff source) |
| Plan ledger (no active brief) | `~/.claude/run/plan-ledger.md` | `announce_plan_write.sh` | human / `/read` |
| Plans, the durable copy | `<notes>/plans/<name>.md` — flat, one copy, mirrored nowhere (`docs/data-layout.md` lines 201, 241) | `/autoplan` (a plan is written or sharpened) | `/build`, `/checkin`, `/read`, human |
| Build-rules index | `~/lifehack-brain/system/build-rules-index.md` | human (maintained by convention) | `/build` Step 0 |
| Build SOPs | `system/sops/build-sop.md` · `build-conductor-sop.md` · `architecture-planning-sop.md` | human + `/build` (build-sop.md append) | `/build` Step 0 |

---

### TRIGGERS (full map)

| Trigger | What fires | Effect |
|---|---|---|
| `/autoplan` (explicit slash-command only) | skill `commands/autoplan.md` | re-anchor → continuation check → plan mode |
| `ExitPlanMode` | `guard_plan_structure.sh` (PreToolUse) | BLOCK if Phase/Task/Verify absent |
| `ExitPlanMode` | `plan_flag.sh record` (PreToolUse) | write session plan flag (non-blocking) |
| Any user prompt (build-verb + tracked noun) | `inject_sop_before_build.sh` (UserPromptSubmit) | inject SOP pointer (non-blocking) |
| Any user prompt (every turn) | `announce_plan_write.sh` (UserPromptSubmit) | diff plans dir; announce NEW/updated plans |
| `/build` (or "build", "execute the plan") | skill `skills/build/SKILL.md` | Step-0 rules gate → execution loop |

---

### INTEROP SEAMS

```
READS       build-rules-index    · /build Step 0 reads it to resolve which docs bind the build
READS       architecture-planning-sop · /autoplan prose directives; /build Step 0 ALWAYS doc
READS       build-sop            · /build Step 0 ALWAYS doc; appended to when build teaches a lesson
READS       build-conductor-sop  · /build Step 0 (orchestrated/parallel builds); defines gears
FEEDS       project-manager      · /build files unbuilt tasks to OPEN LOOPS via project-manager at honest close
CHAINS      project-manager      · /autoplan re-anchors via pm_flag.sh; plan's FRAME feeds the project brief
FEEDS       plan-integrity-cluster · guard_plan_structure + plan_flag are the plan-integrity seam hooks (cross-reference)
READS       pm-flag              · /autoplan Step 0 reads pm_flag.sh status to re-anchor; announce_plan_write reads pm_flag.sh status for brief path (to write NEW plan pointer to brief's ## SCRATCHPAD)
WRITES→     durable memory (/save) · build lessons append to build-sop.md (the skill's own living memory)
GUARDED-BY  guard_plan_structure.sh · blocks ExitPlanMode if Phase/Task/Verify absent
GUARDED-BY  inject_sop_before_build.sh · injects SOP pointer (advisory, non-blocking) at UserPromptSubmit
COMPLEMENTS advisory-council     · architecture-planning-sop.md (Stages 1/4/6) invokes /advisory-council for blind review; /build does not invoke it directly
COMPLEMENTS checkin              · /checkin re-arms plan_flag.sh via `plan_flag.sh set <path>` so a resumed window shows its plan
COMPLEMENTS read                 · /read arms plan_flag.sh on resume (same set call as /checkin)
```

---

### GAPS

1. **`[AUTOPLAN-PLANMODE-SANDBOX]` — `/autoplan` mints a NEW random plan file on every invocation; the continuation-check rule (Step 0.2) is `[honor]` only.** Plan mode saves to a random new path in `~/.claude/plans/` regardless of which plan the session is tracking — there is no mechanism to route the write to an existing file. The `guard_plan_fork.sh` hook was built to block this and was RETIRED 2026-07-15 (it trapped plan mode). `announce_plan_write.sh` makes forks visible after the fact but cannot prevent them. A session following the continuation-check prose SHOULD amend the existing plan by copy-pasting or editing, but a model that enters plan mode will produce a new file. Real blast-radius: plan proliferation, lost continuity, user confusion about which plan is live (incident 2026-07-14). `done_when: plan mode edits persist OR fail loudly; /autoplan asks continue-vs-new`. ← **A tip-only reader sees `LIVE (honor)` and may trust the continuation-check rule is mechanically enforced — it is not.**

2. **`[PLAN-DEMOTION-ENFORCE]` — the No-Silent-Demotion guard at execution time is persuasive doctrine, not a code-gate.** The `/build` "No illusion of completion" close and the `/autoplan` `⚠ CUT FROM THIS BUILD` block are both `[honor]`. Two deferred enforcers: (a) a hook that blocks a "done" report or `ExitPlanMode` when in-scope `Phase ▸ Feature ▸ Task` items are unbuilt; (b) a `/save`-time reconciliation that catches an unbuilt-but-reported-done item before it settles into memory. `state:monitoring` — revisit if a silent demotion slips through after doctrine has run across several real plans/builds. *(Records: `records/decision/2026-07-10-no-silent-demotion-guard.md` — VERIFIED.)*

3. **`[BUILD-RULES-GATE]` — Step-0 rules-gate is advisory (v1).** The `inject_sop_before_build.sh` hook fires ~84% coverage (hook-internal claim; `skill-building-sop.md §2` states "~20–50%") but is non-blocking; a bare `/build` with a generic argument (no tracked noun) produces NO pointer. The escalation to a blocking UserPromptSubmit or in-skill produced-gate is tracked in `$DRIVE/state/debt-ledger.md` as `[BUILD-RULES-GATE]`. *(Committed 2026-06-20.)* The trust-tag lifecycle (`[UNVERIFIED]` → `[VERIFIED date]` flip in `build-rules-index.md` as the SAD rewrite lands) is also tracked there.

4. **`[BUILD-PARKINGLOT]` — /build's blocker handling is binary (keep-going / stop-the-whole-build).** A parked design: on hitting a blocker, shelve THAT phase, keep working the other independent phases, batch the human-questions, and hard-stop only when everything remaining is blocked or genuinely unsafe. Needs `/autoplan` to tag phase dependencies so deferral is possible. Deferred `state:parked` (user left it on the table 2026-06-24 after the phase-boundary fix). `done_when: /build defers a blocked phase, continues independent work, and batches the questions`.

---

### INTENT / CURRENT-VS-TARGET

**Intent:** every plan is `Phase → Feature → Task` with a runnable Verify on every task, and no task
is ✅ until its verify passes — so `/build` can run autonomously afterward, spending the human's
attention only at explicitly marked checkpoints, never at incidental phase boundaries. `/autoplan`
shapes the plan into this contract; `/build` executes it honestly, reconciling every task against
the plan before ever reporting "done."

**Current state → LIVE (honor):** the mechanical half is real — `guard_plan_structure.sh` blocks
`ExitPlanMode` if Phase/Task/Verify markers are missing, and `plan_flag.sh` / `announce_plan_write.sh`
/ `inject_sop_before_build.sh` are all registered and firing. But the PRIMARY
behavioral contracts of both skills are `[honor]`, not hook-enforced: the continuation check
(`/autoplan` Step 0.2 — contradicted in practice by `[AUTOPLAN-PLANMODE-SANDBOX]`, since plan mode
always mints a new file regardless of what the skill says), the No-Silent-Demotion rule, the
Execute→Verify→✅ execution discipline, gear selection, and the honest close are all skill prose a
session could skip. A tip-only reader seeing "LIVE" would over-trust enforcement of the continuation
and no-demotion rules — hence `(honor)` and the `·gap` candidate on the map gloss.

**TARGET:** (1) resolve the `/autoplan` continuation-check design fork — status quo / pre-mode prompt
/ post-mode auto-merge (the operator's call, see "DESIGN FORK FOR MORNING" below); (2) build the deferred
hard enforcer for No-Silent-Demotion (`[PLAN-DEMOTION-ENFORCE]`) — a hook that blocks a "done" report
while in-scope tasks are ✗; (3) escalate the Step-0 rules-gate from advisory to blocking if the ~84%
coverage proves skippable in practice (`[BUILD-RULES-GATE]`); (4) give `/build` graduated
blocker-handling (shelve-and-continue vs. stop-everything) per `[BUILD-PARKINGLOT]`.

---

## AUTO-COMPUTED   (machine-only — written by the Feature 1.5 checker)

```yaml
maturity_label: LIVE (honor)
check_detail: not yet run
```

---

## SELF-CRITIQUE vs SOURCE

**What this draft covers well:**
- Both skills' trigger-to-output flow from live source
- All five hooks with their `file:matcher` registration and enforcement posture
- All four debt items folded in with explicit labels
- Stores table, triggers table, interop seams in typed-verb vocabulary
- Honest GAPS section surfacing the three fail-open conditions with `·gap` candidates identified

**What is UNVERIFIED or provisional:**
- `records/decision/2026-07-10-no-silent-demotion-guard.md` — referenced in debt notes; confirmed to exist. Tagged `VERIFIED`.
- The `plan-integrity-cluster` element cross-reference: labeled UNVERIFIED because it does not yet exist as a live or draft element as of 2026-07-24.
- The `announce_plan_write.sh` BRIEF path resolution: the hook reads `pm_flag.sh status` expecting it to return the doc path, but `plan_flag.sh status` returns the PLAN NAME (not the doc path). The brief resolution uses `pm_flag.sh status` (which returns a doc path). Confirmed from reading both scripts — `pm_flag.sh status` returns `doc_path`, `plan_flag.sh status` returns plan `name`. The announce hook calls `pm_flag.sh status` (correct tool) not `plan_flag.sh status`. ✓ Confirmed consistent.
- `inject_sop_before_build.sh` fires on `matcher: ""` (all UserPromptSubmit). Confirmed from settings.json line 372–380. ✓

**Maturity label rationale:** `LIVE (honor)` — the mechanical hooks (`guard_plan_structure.sh`, `plan_flag.sh record`, `announce_plan_write.sh`, `inject_sop_before_build.sh`) are all LIVE and registered in settings.json. ⛔ CORRECTED 2026-08-25: `mirror_plans.sh` was dropped from this list — it does not exist in this repo (0 files, verified this session) and is not registered anywhere; see `system/organism/elements/hook-plane.md` §E2. The primary behavioral contracts of BOTH `/autoplan` and `/build` — the continuation check, the No-Silent-Demotion guard, the Execute→Verify→✅ discipline at execution time, the gear selection, the honest close — are `[honor]` only: skill prose, no blocking enforcement. A tip-only reader sees "LIVE" and may over-trust the enforcement posture. `·gap` is warranted on the map gloss. `(honor)` tip-tag is also warranted (primary contracts are skill-prose only).

---

## DESIGN FORK FOR MORNING

**The one open design question worth a morning decision:**

**Should the continuation check in `/autoplan` Step 0.2 be re-implemented as a pre-plan-mode PROMPT to the user (not a hook)?** The current implementation is honor-prose: the skill says "default to amending the existing plan," but plan mode will save to a new random file regardless. `announce_plan_write.sh` makes the fork visible after the fact. The retired `guard_plan_fork.sh` proved that a blocking approach traps plan mode.

Three viable paths:
1. **Status quo** (transparency-only via announce_plan_write): low friction, accepted UX, fork is visible but not prevented. Matches the 2026-07-15 decision. Close `[AUTOPLAN-PLANMODE-SANDBOX]` as "won't-fix" at the plan-mode layer.
2. **Pre-mode user prompt**: before entering plan mode, the skill asks "Continue plan `<name>` or start fresh?" — user chooses; skill either tells them to copy-paste from the existing plan or enters plan mode fresh. The new plan still gets a random name, but the user consented and can immediately copy the result back. Adds one round-trip; requires skill edit; no hook.
3. **Post-mode auto-merge**: after ExitPlanMode creates a new file, the skill's continuation logic detects the existing linked plan and proposes merging the new content into the old file (rename/move the new plan to the old path). Mechanically feasible; slightly weird UX; requires that the plan_flag record fires BEFORE the skill acts.

**The operator's call needed on which path to close the debt item.**
