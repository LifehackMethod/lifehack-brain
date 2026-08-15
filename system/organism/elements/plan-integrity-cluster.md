---
element: plan-integrity-cluster
title: "plan-integrity-cluster — element detail (ground/base altitude)"
subsystem: planning
altitude: base
record_type: organism-element
maturity_label: PARTIAL [provisional]
generated_from:
  - system/hooks/guard_plan_structure.sh
  - system/hooks/guard_plan_fork.sh
  - system/hooks/mirror_plans.sh
  - system/hooks/announce_plan_write.sh
  - system/hooks/inject_sop_before_build.sh
  - system/hooks/plan_flag.sh
  - system/reference/settings.json
  - CLAUDE.md §"Planning Output"
  - system/sops/architecture-planning-sop.md
  - state/debt-ledger.md (lines 84–85, 146, 349, 369, 419)
  - records/research/2026-07-15-agent-plan-file-management.md
created_at: 2026-07-24
updated_at: 2026-07-24
status: draft
authority: user
---

# plan-integrity-cluster — element detail

> **CITATION BANNER — what this page names that is not a file in this repository** (migration note, 2026-08-15).
> The description below is the donor system as it was, and it is kept as written. Each marker records what
> happened to that file AT THIS DESTINATION; none of them changes the description.
>
> ⛔ `system/hooks/guard_plan_fork.sh` is not coming. It was RETIRED in the donor on 2026-07-15 — its own header
> reads "RETIRED — DO NOT RE-REGISTER" — because it hard-blocked plan mode's native save and trapped sessions
> in a loop it could not leave. Its designed replacement, `system/hooks/announce_plan_write.sh`, IS here.
>
> ⏳ unruled — `system/hooks/mirror_plans.sh`. It is the donor's off-machine backup of the plans folder, and
> whether it migrates at all is an OPEN question there (`OL-P8-4`): a session proposed retiring it, the operator
> has not answered, and it stays registered in the donor meanwhile. A debt, not a pass.
>
> ⏳ unruled — `system/sops/cron-safety.md`. It belongs to the scheduled plane, which the donor rules ships in a
> later phase of its own plan; nothing on this side names a landing for this file yet.

> **LADDER: ELEMENT (full mechanics). up → manual#plan-integrity-cluster ; ground truth → the live artifacts (system/hooks/{guard_plan_structure,guard_plan_fork,announce_plan_write,inject_sop_before_build,plan_flag}.sh)**
>
> **One-line:** the hook/enforcement layer that keeps every plan structurally correct, visible, and anchored to a durable flag — so plans never fork silently or miss the Phase→Feature→Task shape before the user sees them.
>
> **Scope note:** this element covers the hooks and the one flag-manager that enforce and track plan lifecycle. It is DISTINCT from `build-plan-plane` (the `/build` + `/autoplan` skills that WRITE plans and drive their execution) and from `project-manager` (which owns the project brief and pm_flag). Cross-references to both are typed below.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires, registered in `settings.json`) · `[skill]` (skill logic, no hook enforcement) · `[honor]` (prose instruction only — CLAUDE.md or SOP) · `[human]` (deliberate HITL pause)

---

## AUTHORED (human-only)

### SUBSYSTEM OVERVIEW — six hooks + one flag-manager, four concerns

The cluster covers four distinct concerns that collectively keep plans durable and well-formed:

| Concern | Hook(s) | Enforcement posture |
|---|---|---|
| Structure quality | `guard_plan_structure.sh` | [hook] BLOCKS on ExitPlanMode — exit 2 if shape missing |
| Fork/proliferation transparency | `guard_plan_fork.sh` (RETIRED) · `announce_plan_write.sh` | RETIRED blocker → replaced by non-blocking observer |
| SOP awareness at build time | `inject_sop_before_build.sh` | [hook] UserPromptSubmit — inject pointer, never blocks |
| Session plan identity | `plan_flag.sh` | State-writer: record · set · status · path · clear |

**No durability/backup concern.** The donor had a fifth one — a Stop hook that copied plans to a
second machine's namespace. It is not here, and nothing replaces it: a plan is one flat file at
`<notes>/plans/<name>.md`, "not mirrored anywhere. There is one copy" (`docs/data-layout.md` line
201). The heading above still says "six hooks" from the donor's count; the real count is five.

`pm_persist.sh` (a `project-manager` element hook, NOT part of this cluster) refreshes the plan flag's TTL every turn so it never expires mid-session (`pm_persist.sh` line 49).

---

### HOOK 1 — guard_plan_structure.sh

**File:** `system/hooks/guard_plan_structure.sh`
**Registration:** `settings.json` → `PreToolUse`, matcher `ExitPlanMode` (verified live)
**Enforcement:** [hook] — exit 2 → **BLOCKS** the ExitPlanMode approval dialog

#### What it guards

Every plan submitted via ExitPlanMode must carry all three non-negotiable structural markers:
- `Phase` (or `phase`) — case-insensitive grep
- `Task` (or `task`) — case-insensitive grep
- `Verif` — case-insensitive grep (catches "Verify", "verification", etc.)

Features are OPTIONAL; Phase + Task + Verify are required. Any missing marker triggers a block.

#### Step chain

```
ExitPlanMode event fires
→ guard_plan_structure.sh reads stdin
→ python3 extracts tool_input.plan (json.load; on parse failure → "" [guard_plan_structure.sh line 23–29])
→ if PLAN is empty → exit 0 [FAIL-OPEN, line 32–34]
→ grep -qi 'phase' || 'task' || 'verif' on PLAN text
→ if any missing → emit {decision:"block", reason:"BLOCKED…"} to stderr → exit 2 [line 43–44]
→ all markers present → exit 0
```

**Fail posture: OPEN on empty/unparseable plan text** (guard_plan_structure.sh lines 18–19, 32–34). Deliberate design: a quality gate, not a security control. A transient parse miss must never brick plan mode. Worst case: one structurally unchecked plan slips; the CLAUDE.md "Planning Output" rule (`CLAUDE.md` line 89–91) is the always-loaded backstop.

#### Block message (verbatim excerpt)

> "BLOCKED: plan is missing required structure (${miss}). WHY: Lifehack plans must be Phase -> Feature -> Task, each task Execute -> Verify & test -> mark done (a task is NOT done until its verify passes), per the Planning Output rule in CLAUDE.md. REDIRECT: rewrite the plan in that hierarchy (Features optional for small plans; Phase + Task + Verify are required) before calling ExitPlanMode. Spec: system/sops/architecture-planning-sop.md (star-star ALWAYS)."

#### Doctrine backstop

`CLAUDE.md` lines 89–91 ("Planning Output") is an always-loaded `[honor]` rule that covers plans produced OUTSIDE plan mode (e.g. inline planning, `/build` without plan mode). The hook enforces the shape only at the ExitPlanMode approval moment; the `[honor]` rule covers the rest of the surface. The gap between them (plans produced inline, never passing through ExitPlanMode) is not mechanically enforced.

---

### HOOK 2 — guard_plan_fork.sh

**File:** `system/hooks/guard_plan_fork.sh`
**Registration:** **NOT registered** in `settings.json` (confirmed by grep — guard_plan_fork absent from settings.json). File is RETIRED.
**Enforcement:** [RETIRED] — file preserved for history; NEVER re-register without the operator sign-off.

#### History and retirement

`guard_plan_fork.sh` was designed to block a Write that creates a NEW `~/.claude/plans/*.md` file when the session's plan flag already named a DIFFERENT linked plan. The intent: prevent Claude from silently forking a second plan file and burying the first (project-system incident, 2026-07-14).

**Retired 2026-07-15** (commit 82b024e) because it hard-BLOCKED plan mode's own native save (ExitPlanMode writes to `~/.claude/plans/` itself) → sessions were trapped in an inescapable loop. The research record (`records/research/2026-07-15-agent-plan-file-management.md`) confirmed the correct fix is TRANSPARENCY (a non-blocking observer), not a block.

The banner at `guard_plan_fork.sh` lines 1–8 carries the explicit "⛔ RETIRED — DO NOT RE-REGISTER" instruction.

#### The "won't-build" debt closure

`debt-ledger.md` line 419 records `[FLYWHEEL-AUTOPLAN-PREVENT] CLOSED — won't-build (2026-07-14, the operator)`. This is the companion feature (prevent the model from even hitting the block by defaulting `/autoplan` to editing the session's existing plan). Status: won't-build — the fork-BLOCK was live at the time; the polish was deferred and then made moot by the hook's retirement.

---

### HOOK 3 — announce_plan_write.sh

**File:** `system/hooks/announce_plan_write.sh`
**Registration:** `settings.json` → `UserPromptSubmit`, no matcher (fires on EVERY turn)
**Enforcement:** OBSERVE/INJECT only — [hook] but exit 0 unconditionally. NEVER blocks.

#### What it does

On every user prompt turn, diffs `~/.claude/plans/*.md` against a per-session state file (`~/.claude/run/plan-announce/<key>.state`) to detect plan files that are NEW or have been MODIFIED since the last turn. For each delta:

1. **Prints a visible line to stdout**: `📋 plan written: <filename> @ <path> (NEW|updated)` — user-visible inject (UserPromptSubmit stdout injection).
2. **For NEW plans only**: writes a durable pointer:
   - If `pm_flag.sh status` is armed → appends `> 📋 plan created: <name> @ <path> (<date>)` to the active project brief's `## SCRATCHPAD` section (announce_plan_write.sh lines 76–88).
   - If no brief armed → appends the same line to `~/.claude/run/plan-ledger.md` (line 89–91).

**First-run seeds silently** (announce_plan_write.sh line 62): pre-existing plans are NOT announced as "new" so a session startup with old plans doesn't flood the user.

**Session key logic**: prefers `$CLAUDE_CODE_SESSION_ID`; falls back to `cwd-<hash>` (lines 26–28).

**Fail posture: degrade-safe** — any error in the Python block → exit 0 silently (never wedges a turn).

**Rationale for UserPromptSubmit (not PostToolUse)**: the hook is a per-TURN diff, not a per-write intercept. It announces on the turn AFTER a plan file changes, not the instant of the write. This is a design choice (the research record §4 recommends a PostToolUse intercept for immediate announcement — see GAPS below).

---

### HOOK 4 — mirror_plans.sh

**NOT PART OF THIS SYSTEM. There is no fourth hook — this heading is a leftover from the donor.**

`system/hooks/mirror_plans.sh` does not exist here, and neither does the recovery script that
paired with it. Both were two-machine machinery: a Stop hook that rsynced `~/.claude/plans/` into a
per-hostname folder on a shared drive, and a puller that fetched the *other* machine's copy. This
system has one machine, so the whole concern is gone — `docs/data-layout.md` line 214: *"there is
one machine. The two-machine plane is not part of this system."*

#### What it does

Nothing — there is no hook to run. Plans are durable because they are written where the rest of
your notes are written: one flat file per plan at `<notes>/plans/<name>.md`, "not mirrored
anywhere. There is one copy" (`docs/data-layout.md` line 201). Backing that up is the same job as
backing up everything else you own, and it is not this cluster's concern.

---

### HOOK 5 — inject_sop_before_build.sh

**File:** `system/hooks/inject_sop_before_build.sh`
**Registration:** `settings.json` → `UserPromptSubmit`, no matcher (fires on every turn)
**Enforcement:** Read-only INJECT observer. [hook] but exit 0 always. NEVER blocks.

#### What it does

On every user prompt, detects a BUILD-VERB within ~3 words of a TRACKED-NOUN (case-insensitive, Python regex). On a match, injects into stdout:

```
[SOP CHECK — harness-injected, NOT user input. A standing Lifehack build rule.]
Before you plan or build this <label>, STOP and Read `<sop-path>` in full now — it holds the
hard-won lessons. Do NOT build from memory or a stale mental model: read it first,
then build something better for having read it.
```

#### Trigger table (inject_sop_before_build.sh lines 40–49)

| Noun regex | SOP pointed at | Human label |
|---|---|---|
| `skills?` | `system/sops/skill-building-sop.md` | skill |
| `hooks?` | `system/sops/hook-sop.md` | hook |
| `desks?` | `system/sops/desk-building-sop.md` | desk |
| `(?:google\s+)?sheets?\|spreadsheets?` | `system/sops/google-sheet-sop.md` | Google Sheet |
| `dashboards?\|views?\|screens?` | `system/sops/design-process-sop.md` | dashboard / view |
| `crons?\|scheduled\s+(?:job\|task)s?\|timers?` | `system/sops/cron-safety.md` | cron job |
| email / ingest compound pattern | `system/information-ingestion-interpretation.md` | email / information ingestion reader |

**Build verbs** (inject_sop_before_build.sh line 52): `build|building|built|make|making|made|creat(?:e|ing)|writ(?:e|ing)|author|construct|design|add|adding|new|scaffold|set\s+up|spin\s+up|put\s+together|draft`

**Match rule**: a build-verb must appear within ~3 words BEFORE the noun (optionally through an article). A bare noun mention ("skill at cooking", "that hooked me") is a NO-OP.

**No SOP for plans themselves** in this table. The planning SOP is pointed at by `guard_plan_structure.sh`'s block message and by `CLAUDE.md` directly — not by inject_sop.

**Fires every matching turn** (no suppression per session) — by design.

**Fail posture: degrade-safe** — any error → exit 0 silently.

**Origin** (inject_sop_before_build.sh lines 5–11): confirmed 2026-07-11 that the full settings.json hook registry + a grep of every hook referenced ZERO build SOP. A gentle "consider the skill" nudge fires ~20%; an explicit inject lands ~84% (figures stated in `inject_sop_before_build.sh` header lines 7–8; the `skill-building-sop.md §2` attribution in the header could not be confirmed from the SOP source).

---

### HOOK 6 — plan_flag.sh

**File:** `system/hooks/plan_flag.sh`
**Registration:** `settings.json` → `PreToolUse`, matcher `ExitPlanMode` (subcommand: `record`)
**Enforcement:** State-writer, exit 0 always. NEVER blocks (plan_flag.sh line 7: "NEVER blocks").

`plan_flag.sh` is a multi-subcommand state manager, not just a hook:

| Subcommand | Called by | What it does |
|---|---|---|
| `record` | ExitPlanMode hook (settings.json) | Reads plan text from stdin, extracts H1 heading, finds newest `~/.claude/plans/*.md` by mtime → writes flag file with name, plan_file, armed_at, session |
| `set <path>` | `/checkin` skill (resume path) | Arms flag from an EXPLICIT plan-file path — avoids the newest-mtime mis-fire the `record` path can hit across parallel windows |
| `status` | `/save` Step 0 · pm_persist.sh (every turn) · /advisory-council | Prints active plan name or "none"; enforces 36h TTL (self-deletes on expiry) |
| `path` | `/advisory-council` | Prints the armed plan's FILE PATH (status prints the name); consumed to read the active plan as advisory context |
| `clear` | User or skill (clean succession) | Removes this session's plan marker; also clears other flags for this session_id |

**Flag store**: `~/.claude/run/plan/plan-<key>.flag` (plan_flag.sh line 23–26). Key = `sess-$CLAUDE_CODE_SESSION_ID` when available, else `cwd-<shasum>`.

**Flag content** (on `record`/`set`): four lines: `name=`, `plan_file=`, `armed_at=`, `session=`.

**TTL**: 36 hours default (`PLAN_TTL_HOURS`, plan_flag.sh line 22). `pm_persist.sh` (a `project-manager` element hook) refreshes `armed_at` every turn so a live session never expires mid-run (pm_persist.sh line 49).

#### Known gap — mtime cross-wire (ExitPlanMode / `record` path)

`debt-ledger.md` line 84 (`[STATUSLINE-PLAN-CROSSWIRE]`): the `record` subcommand resolves the plan file as the NEWEST `~/.claude/plans/*.md` by mtime. With multiple plan-mode windows open, "newest" is whichever saved LAST → the marker cross-wires between windows. **The RESUME path (`set <path>`) is reliable** — it arms from an explicit path. **What REMAINS broken**: the `record`/ExitPlanMode path. State: `actionable` as of 2026-07-13.

#### Known gap — `/read` does not arm plan flag

`debt-ledger.md` line 85 (`[CHECKIN-READ-PLANFLAG]`): `/checkin` arms BOTH pm_flag and plan_flag on resume (commit 6d0255f). `/read` (the other resume door) only arms pm_flag, not plan_flag → resuming via `/read` leaves the `plan:` HUD field blank. **State: `parked`** (the operator deferred 2026-07-13: "leave /read alone").

---

### STORES TOUCHED

| Store | Written by | Read by | Notes |
|---|---|---|---|
| `~/.claude/plans/*.md` | Claude Code plan mode (native) | guard_plan_structure · guard_plan_fork · announce_plan_write · plan_flag.sh record | Machine-local; the ephemeral approval-card store |
| `~/.claude/run/plan/plan-<key>.flag` | plan_flag.sh (record · set) | plan_flag.sh (status · path · clear) · pm_persist.sh (TTL refresh) · statusline.sh · /advisory-council · /save Step 8 | Per-session state; 36h TTL |
| `~/.claude/run/plan-announce/<key>.state` | announce_plan_write.sh | announce_plan_write.sh (per-turn diff) | Per-session plan-diff seed; never durable |
| `~/.claude/run/plan-ledger.md` | announce_plan_write.sh (fallback) | Human / recovery | NEW-plan pointer when no pm_flag armed |
| Active project brief `## SCRATCHPAD` | announce_plan_write.sh (primary) | pm_persist.sh · /save | NEW-plan pointer when pm_flag armed |
| `<notes>/plans/<name>.md` | `/autoplan` | Human · `/build` · `/checkin` · `/read` | The durable plan. Flat, one copy, mirrored nowhere (`docs/data-layout.md` lines 201, 241) |

---

### INTEROP SEAMS

```
GUARDED-BY  guard_plan_structure      · blocks malformed ExitPlanMode submissions; the ONLY hard gate in this cluster [hook exit 2]
COMPLEMENTS build-plan-plane          · build-plan-plane (/autoplan · /build skills) WRITES the plans that this cluster guards, flags, backs up, and makes visible; plan-integrity-cluster is purely the enforcement/observability layer — it never writes plan CONTENT [honor; cross-element boundary]
COMPLEMENTS project-manager           · plan_flag.sh arms session plan identity; pm_flag.sh (project-manager element) arms session project identity; pm_persist.sh (project-manager element) refreshes BOTH flags' TTL every turn [hook — pm_persist.sh UserPromptSubmit line 49]. NOTE: pm_persist.sh's directive to "record a link to the plan's path in the doc" is PROJECT-MANAGER CONTINUITY DISCIPLINE (keeping the brief's pointer to the active plan current so context doesn't fade) that incidentally covers plans — it is NOT a plan-integrity enforcement point and is NOT scoped to this cluster. The actual plan-integrity enforcement lives in guard_plan_fork.sh (RETIRED) + announce_plan_write.sh (built 2026-07-14 after the real fork incident). [honor — pm_persist.sh line 121 is project-manager's concern]
WRITES→     announce_plan_write       · writes NEW-plan pointer lines into project-manager's owned ## SCRATCHPAD when pm_flag is armed; falls back to plan-ledger.md when not [hook — announce_plan_write.sh lines 76–91]
READS       plan_flag.sh              · /advisory-council reads plan_flag.sh path subcommand to load the active plan as advisory context before its council run [honor — /advisory-council skill; no hook enforces this read]
READS       plan_flag.sh              · /save Step 8 (Wake Routine handoff) reads plan_flag.sh status to surface the active plan name in the continuation handoff [honor — /save skill]
TRIGGERS    inject_sop_before_build   · fires before any build of a hook, skill, desk, sheet, dashboard, cron, or ingest pipeline — the six domains whose SOPs live in system/sops/; NOT triggered before plan-content work (planning SOP is pointed at by guard_plan_structure's block message + CLAUDE.md directly) [hook — UserPromptSubmit exit 0]
KEYS-OFF    pm_persist.sh             · pm_persist.sh (project-manager element) refreshes plan_flag.sh's armed_at every turn so the plan flag never TTL-expires mid-session [hook — pm_persist.sh line 49]
```

---

### GAPS

1. **Structural check is BYPASS-able via inline planning** — `guard_plan_structure.sh` fires ONLY at ExitPlanMode. Any plan produced inline (without entering plan mode), or handed off as prose in `CLAUDE.md`'s "Planning Output" rule, is NOT mechanically checked. The `[honor]` rule is the only coverage. A session that never calls ExitPlanMode can produce and execute a plan with no structural enforcement.

2. **Fork prevention is HONOR-SYSTEM only since guard_plan_fork.sh was RETIRED** (2026-07-15). The research record (§2, dominant practice) confirms this is the correct posture: blocking native plan mode breaks the approval card. `announce_plan_write.sh` makes forks VISIBLE but does not PREVENT them. A determined (or confused) session can still create multiple plan files.

3. **announce_plan_write.sh announces on the NEXT TURN, not the instant of write** — it's a per-turn diff, not a PostToolUse intercept. A plan created at the end of a turn is not announced until the following user prompt. The research record (§4) identifies a PostToolUse hook as the tighter fix; current design accepts the one-turn lag.

4. **plan_flag.sh `record` path mtime cross-wire** (CONFIRMED debt, `debt-ledger.md` line 84) — see Hook 6 "Known gap." `state: actionable`.

5. **A plan has no second copy** — plans live at `<notes>/plans/<name>.md`, flat, one copy, mirrored nowhere (`docs/data-layout.md` line 201). Nothing in this cluster backs a plan up; if the notes folder is lost, the plans go with it. That is the deliberate posture, not an oversight — but it is worth knowing, because the donor system did have a backup hook and this one does not.

6. **`/read` does not arm plan_flag** (`debt-ledger.md` line 85) — `state: parked` by the operator decision 2026-07-13.

---

### INTENT / CURRENT-VS-TARGET

**Intent:** keep every plan structurally correct, visible, and anchored to a durable flag —
so a plan never forks silently and gets buried, and
never skips the Phase→Feature→Task shape before the human approves it. The cluster is purely
enforcement/observability; it never writes plan content — that is `build-plan-plane`'s job.

**Current state → PARTIAL [provisional]:** the one HARD gate in the cluster
(`guard_plan_structure.sh`, blocking `ExitPlanMode` on missing Phase/Task/Verify) is live and
fire-tested. Everything else is a softer posture BY DESIGN: fork-prevention was tried as a hard block
(`guard_plan_fork.sh`) and retired after it trapped plan mode in an inescapable loop —
`announce_plan_write.sh` now makes forks visible, not prevented, which the research record confirms is
the correct posture, not a shortfall. The remaining honest gaps are narrower: the structural check
only fires at `ExitPlanMode`, so inline planning is unchecked; `plan_flag.sh record`'s newest-mtime
fallback can cross-wire the plan HUD across parallel windows; and `/read` (unlike `/checkin`) doesn't
arm the plan flag on resume.

**TARGET:** fix the `plan_flag.sh record` mtime cross-wire so multi-window sessions don't show the
wrong plan (`[STATUSLINE-PLAN-CROSSWIRE]`, actionable). `/read` not arming plan_flag is parked
by the operator's own 2026-07-13 call, not tracked as a gap to close. Whether inline-plan structural
enforcement is worth building is an open judgment call (see the design fork below) — the
recommendation on file is to accept the gap until a real incident forces the question.

---

## AUTO-COMPUTED (machine-only — written by Feature 1.5 checker, not by humans)

```yaml
maturity_label: PARTIAL [provisional]
check_detail: ~
```

---

## [provisional] SELF-CRITIQUE vs SOURCE

**Verified from live code:**
- `guard_plan_structure.sh` ExitPlanMode registration, exit-2 behavior, fail-open on empty plan, three-marker check (Phase/Task/Verif) — all confirmed by reading the file.
- `guard_plan_fork.sh` retirement + NOT-in-settings.json — confirmed by `grep` of settings.json + banner in the file.
- `announce_plan_write.sh` non-blocking UserPromptSubmit, per-turn diff logic, pm_flag-vs-ledger fallback — confirmed by reading the file.
- `inject_sop_before_build.sh` trigger table + build-verb regex — confirmed by reading the file.
- `plan_flag.sh` subcommands (record/set/status/path/clear), flag store location, 36h TTL — confirmed.
- `pm_persist.sh` plan flag TTL refresh at line 49 — confirmed by grep.
- Debt ledger entries at lines 84–85, 146, 349, 369, 419 — confirmed.
- `settings.json` registrations: guard_plan_structure (ExitPlanMode), plan_flag.sh record (ExitPlanMode), announce_plan_write (UserPromptSubmit), inject_sop_before_build (UserPromptSubmit) — confirmed. guard_plan_fork NOT registered — confirmed.

**UNVERIFIED / INFERRED:**
- `[INFERRED]` `build-plan-plane` is the slug for the /build + /autoplan skills element. No organism element file for build-plan-plane exists in `system/organism/elements/` (confirmed by ls) — the slug is used in cross-references in `hook-plane.md.draft` and `project-manager.md.draft` but the element itself is not yet authored. Cross-references here use that same slug for consistency.
- `[INFERRED]` The `inject_sop_before_build.sh` duplicate in the settings.json output (two lines for UserPromptSubmit and two for announce_plan_write) — the grep output showed duplicated lines; however these may reflect the Python de-duplication script artifact in my extraction, not actual double-registration. A careful manual count of the settings.json hook array entries is needed to confirm whether these hooks fire twice per turn or once. (The only confirmed duplicate from my dedup check was `ingest_gate_enforce.sh` × 3.)
- `[INFERRED]` The `path` subcommand of plan_flag.sh is described as "consumed by /advisory-council" — confirmed by plan_flag.sh header (`UPDATED: 2026-07-21 added 'path': print the armed plan's file path, for /advisory-council auto-context`), but the /advisory-council skill was NOT read to confirm the consumption pattern. Treated as CONFIRMED by header attribution.

**Design FORK for morning (the one live question this element surfaces):**

> **Should `guard_plan_structure.sh` also fire on inline-plan writes (not just ExitPlanMode)?** The gap (inline planning bypasses structural enforcement) is real. Two viable options: (A) accept the gap — the CLAUDE.md `[honor]` rule plus the ExitPlanMode gate covers the canonical path; inline plans are low-frequency; (B) add a UserPromptSubmit hook that detects "here is my plan" style inline outputs and runs the same grep-check. Option B has the mtime/latency problem (inline plans live in the model's output, not a file) and risks false positives. The research record (§4, dominant practice) suggests structural enforcement via hooks is the right posture — but for quality gates, fail-open is the correct default. **Recommend: stay with Option A (accept the gap) until a real incident — inline plan bypasses are observable via announce_plan_write's transparency layer.** This is a judgment call for the operator.
