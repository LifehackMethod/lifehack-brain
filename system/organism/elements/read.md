---
element: memory-read
title: "memory-read (/read + /checkin + project-manager + project-registry) — element detail (ground/base altitude)"
subsystem: memory
altitude: base
record_type: organism-element
maturity_label: PARTIAL (honor)
generated_from:
  - skills/read/SKILL.md
  - skills/checkin/SKILL.md
  - skills/project-manager/SKILL.md
  - system/hooks/pm_flag.sh
  - system/hooks/pm_persist.sh
  - system/hooks/session_context_loader.sh
  - system/hooks/save_routing_hint.sh
  - system/hooks/ingest_gate_enforce.sh
  - system/hooks/guard_canon_write.sh
  - system/hooks/announce_plan_write.sh
  - system/hooks/scratch_sweep_nudge.sh
  - system/hooks/scratch_capture_gate.sh
  - system/hooks/skill_anchor.sh
  - system/reference/settings.json
  - system/organism/map-format-specs.md §0–§1
created_at: 2026-07-23
updated_at: 2026-07-23
status: draft
authority: user
---

# memory-read (`/read` + `/checkin` + `project-manager` + project-registry) — element detail

> **CITATION BANNER — what this page names that is not a file in this repository** (migration note, 2026-08-15).
> The description below is the donor system as it was, and it is kept as written. Each marker records what
> happened to that file AT THIS DESTINATION; none of them changes the description.
>
> ⛔ `state/debt-ledger.md` is the person's own notes, not a repo file. Here it is
> `<notes>/state/debt-ledger.md`, written by `/save` and `/build` (`docs/data-layout.md`) — created by use,
> never committed.
>
> ⛔ `state/projects/skill-system/brief.md/brief.md` is not a file anywhere, in either system. It is the
> DEFECTIVE path the registry-data finding below is reporting — the doubled suffix IS the finding — and it
> lives inside the person's own notes, not this repo. Left exactly as written, because rewriting it would
> delete the defect it exists to record.

> **LADDER: ELEMENT (full mechanics). up → manual#read ; ground truth → the live artifact (generated_from)**

> **Altitude = BASE (ground / street view).** The in-the-weeds detail of how session context is
> rehydrated — every trigger, every mode, every step, every store touched, every gate and its real
> enforcement, and every interop seam with the rest of the system. The MIDDLE index (`system/organism/manual.md`)
> carries only a one-line pointer here; the TIP (`CLAUDE.md` schematic) shows only the box + arrows;
> the **skills themselves** (`skills/read/SKILL.md`, `skills/checkin/SKILL.md`, `skills/project-manager/SKILL.md`)
> are the fourth level — the executable runtime ground truth.
> This entry is the UNDERSTANDING layer: exhaustive description of what the element does + why + how it connects.
>
> **One-line:** rehydrate the right slice of durable memory into a session so context is never rebuilt from scratch.
>
> **Broader framing (identity.md §Claim 1 correction):** session context recall is already fairly automated —
> open a window from the correct desk and the floor loads. The design-intent judgment was that this is
> INTENTIONALLY manual/directed (human chooses what to read and when), not a gap to close. The honor-system
> surface is deliberate, not an oversight; the `PARTIAL` label reflects incomplete TOOLING MATURITY on the
> mechanical surface (vocabulary enforcement at write-time, automated index health), not a broken retrieval path.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory script) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause).

---

## AUTHORED   (human-only)

### SCOPE OF THIS ELEMENT

This element covers four interleaved components that together form the memory-read layer:

1. **`/read` skill** — the directed session context load; functionally read-only except for re-arming the PM flag (pm_flag.sh arm) when a project is active — a write that `/read` performs to refresh the flag TTL (see Step 0).
2. **`/checkin` skill** — orientation pass that READS the project brief and then optionally WRITES to it (scratchpad, Story Log, plan link).
3. **`project-manager` skill** — project doc management (create + update brief, arm the PM flag on project pickup); the full lifecycle wrapper.
4. **Project registry** (`$DRIVE/system/project-registry.md`) — the slug→path resolver all three skills route through.

The surrounding hooks are NOT in the scope of the element but they form the always-on mechanical surface the element depends on: `pm_persist.sh` (per-turn re-injection), `session_context_loader.sh` (session-start floor), `save_routing_hint.sh` (save-phrase routing), `announce_plan_write.sh` (plan HUD), `scratch_sweep_nudge.sh` (context-switch warning).

---

### TRIGGERS

Every entry point into this element:

**1. `/read` skill (explicit or implicit)**
- Phrases: `/read`, "rehydrate", "load context", "remind me of", "what do we know about X", or any opener that implies needing context from the durable store.
- Also fires when opening a desk window where the session_context_loader (SessionStart hook) pre-seeded canon but the user needs project-level specifics too.
- No hook enforces invocation — model judgment. The skill is NOT a separate executable; it is injected skill-text that the LLM interprets.

**2. `/checkin` skill (explicit or gap-triggered; two invocation modes)**
- Phrases: `/checkin`, "where are we", "what should we scope today", "re-orient", "check in", or after a noticeable gap since last session on a project.
- Layered on top of `/read` — all of `/read`'s context load runs as a sub-procedure inside `/checkin`.
- **Front-door args mode — `/checkin <project> <plan>` (the `/save` handoff's paste-line).** When the invocation carries a project (slug or absolute brief path) and optionally a plan path, this is an EXPLICIT session-handoff entry point (distinct from the gap-triggered invocation): the brief and plan are already known, so Step 0's flag-lookup is skipped and BOTH flags are armed in one shot — `pm_flag.sh arm` + `plan_flag.sh set` — no guessing. This is the entry point `/save` routes to on session-close handoffs. The SKILL.md says: "treat those as the EXPLICIT target: resolve the brief (registry `{path}/brief.md` or the given path), then ARM BOTH flags in one shot." This invocation mode is ENTIRELY ABSENT from the normal Step 0 flow — it is a short-circuit that bypasses flag-status-check and goes directly to arm + proceed.

**3. `project-manager` skill (explicit or multi-session pickup)**
- Phrase: `/project-manager`, "track this project", "manage this project", or any multi-session project pickup where no brief exists yet.
- Reads context to orient itself (registry, canon, journal) then either creates a new brief or updates an existing one.
- Primary difference from `/checkin`: `project-manager` owns brief CREATION via the Frame-intake gate; `/checkin` owns ongoing reorientation on an EXISTING brief.

**4. Session-start floor (automatic — fires before any skill invocation)**
- `session_context_loader.sh` (SessionStart hook, non-blocking): pre-loads the active desk's canon files + `$DRIVE/state/telos.md` + `$DRIVE/state/pulse-brief.md` at every session start. This is the "always-loaded floor" — not the same as `/read` but the foundation that `/read` Step 0.6 deduplicates against.
- Not a skill trigger; a structural always-on precondition.

**5. Per-turn re-injection (automatic — fires every user prompt)**
- `pm_persist.sh` (UserPromptSubmit hook, non-blocking): when the PM flag is armed, injects a one-line "[project-manager ACTIVE]" reminder with an excerpt from the active brief into context every turn — keeping project state visible without a fresh `/read` invocation. This is NOT a read trigger; it is the mechanism that bridges between read invocations.

---

### FULL STEP CHAIN

#### Session-start floor (always-on; fires before any `/read` invocation)

```
session_context_loader.sh → Bash(cat + emit_dir) → $DRIVE/desks/{desk}/canon/*.md
                           + $DRIVE/state/telos.md
                           + $DRIVE/state/pulse-brief.md → stdout inject → none [hook, SessionStart, non-blocking, advisory]
```

- Matcher in settings.json: `SessionStart` entry — `command=session_context_loader.sh`, non-blocking.
- Always exit 0 (advisory; never blocks the session). Emits canon + TELOS + Pulse to context. No deny path.
- Root mode loads `$DRIVE/records/canon/*.md` instead of desk canon.
- This fires ONCE per session. `/read`'s lazy canon walk (Step 0.6 below) is supposed to SKIP re-loading same-desk canon already injected here — the dedup is honor-system only (no hook enforces it). This skip is ONE CASE of the general delta-load rule in Step 2a (a second load this session brings the delta, never a re-stuff); the floor is simply the first thing already in the window.

---

#### `/read` step chain

**Step 0 — PM flag check + re-arm (orientation routing)**

```
/read skill → Bash: pm_flag.sh status → ~/.claude/run/pm/pm-sess-{ID}.flag → none [honor]
```

- `pm_flag.sh` reads the flag file, checks TTL (36h), returns the absolute doc path or `"none"`.
- If a path is returned: `/read` leads with the active brief (Step 0.6 promotes the brief to first priority). **Additionally, `/read` RE-ARMS the flag to refresh its TTL:**
  ```
  /read skill → Bash: pm_flag.sh arm "<doc_path>" "<slug>" "<desk>"
  → ~/.claude/run/pm/pm-sess-{ID}.flag (overwrite) + arm-events.log (append) [honor]
  ```
  The SKILL.md says explicitly: "Re-arm to refresh the TTL (replace the three values)." This is a WRITE performed by `/read` — making `/read` not fully passive toward the PM flag. The re-arm overwrites the flag with fresh `armed_at`, ensuring the 36h TTL window extends from this `/read` invocation.
- If `"none"`: proceed with room-scan only (Step 1). The skill notes the user MAY BE OFFERED a re-arm if the read clearly rehydrates a project ("you may offer to re-arm PM — but do not auto-arm") — still honor-system and conditional.
- If `pm_flag.sh` errors: proceed silently (degrade-safe; the flag must never block a read).
- NO HOOK enforces that `/read` calls `pm_flag.sh` or performs the re-arm. Purely honor-system — the skill says to do both; nothing verifies.

**Step 0.6 — Slug resolution via registry + lazy canon walk**

```
/read skill → Read: $DRIVE/system/project-registry.md → extract {path} 5th-field or legacy slug location [honor]
/read skill → Read/Bash (while loop): $DRIVE/{branch}/canon.md files, most-specific-first → none [honor]
```

- The registry is read directly (no adapter). `ingest_gate_enforce.sh` fires on this Read call but the file is inside `$DRIVE/Lifehack/` (trusted zone) → always exit 0 — passes through freely.
- The registry format: `slug | desk | desc | status | {path}` (5th field = v2 folder-model). If the row has a `{path}`, brief lives at `{path}/brief.md`; if not, legacy fallback: `$DRIVE/desks/{desk}/state/briefs/{slug}.md` or `$DRIVE/state/briefs/{slug}.md`.
- **Known registry data error (source-audit finding):** the `skill-system` slug has `/brief.md` appended to its `{path}` field directly, making the `{path}/brief.md` resolution produce `state/projects/skill-system/brief.md/brief.md` (double suffix). Live data wins; this is a registry entry error that would cause resolution to fail for that slug. Flagged for the operator.
- Canon lazy walk: reads `canon.md` ancestors from the project folder upward, most-specific first. SKIP if same-desk canon was already injected by `session_context_loader.sh` — or by any earlier `/read` this session (Step 2a's delta-load rule, of which this canon skip is one instance). Honor-system dedup — no hook enforces the skip, and the skip must be STATED, never silent.
- No mechanical enforcement on the lazy walk order, the dedup, or whether the walk runs at all.

**Step 1 — Room-scan (intent extraction)**

```
/read skill → inspects conversation history + /read argument → extracts topic/desk/slug signals [in-context, no file I/O]
```

- Pure in-context reasoning. No file I/O. No gate.
- If a `/read <argument>` argument was passed, it constrains the search scope.

**Step 2 — Orient statement first (compaction-surviving anchor)**

```
/read skill → stdout (in-context emit, no file I/O) → none [honor]
```

- Before touching the filesystem, write one line at the top of the response:
  `Orienting around [topic] — loading from [desk].`
- This goes BEFORE any loaded content so it survives compaction even if content below it gets compressed. The SKILL.md calls this the compaction-surviving anchor: the session knows what it oriented around even if the loaded files are compressed away.
- Honor-system — no hook enforces that the line is written or that it precedes all file I/O. The skill is explicit: "before touching the filesystem."

**Step 2a — Delta-load on a second `/read` in the same session (the generalised dedup)**

```
/read skill → scans THIS session for every earlier `Orienting around …` line + every earlier close line
→ treats the paths they name as ALREADY IN THE WINDOW → skips them → says what was skipped and why [honor]
```

- **A second invocation loads the DELTA, never re-stuffs.** It brings in what is NEW and skips what is already in the window — additive but deduplicated, not a blind re-read and not a replacement of the earlier load. The failure mode being prevented is **over**-stuffing, so the tie-break is explicit: **when in doubt, skip rather than reload.**
- **No ledger is invented — the dedup reuses the channel that already exists.** Step 2's orient line and Step 6's closing anchor are both placed to survive compaction, which makes them a readable record of what this session already loaded. The four mechanics:
  1. Scan the session for every earlier `Orienting around …` line and every earlier close line; the paths they name are already loaded.
  2. Skip those paths — do not re-read them, do not re-print them.
  3. **Say what was skipped and why** — *"skipped 4 already loaded this session (see the earlier read)."* A SILENT skip is indistinguishable from a search that missed them, which is the exact failure this element exists to prevent.
  4. **Re-read anyway, deliberately, in exactly two cases:** the file is believed to have changed on disk this session (this session or a helper wrote to it), or the earlier read loaded one section and a different part is now needed. **Name the reason when you do.**
- **The SessionStart floor is ONE CASE of this rule, not a separate rule.** Step 0.6's canon skip (don't re-load same-desk canon the floor already injected) is this same delta-load logic applied to the always-loaded floor. Scope: the rule spans EVERY path a prior `/read` in this session loaded — records, briefs, state, journal slices — not just canon.
- Enforcement: `[honor]` throughout. Nothing verifies the transcript scan happened, that a skip was taken, that the skip was stated, or that a re-read carried a named reason.

**Step 2b — Journal load (chronological anchor)**

```
/read skill → Read: $DRIVE/system/journal.md (filtered on "| {desk} | {slug} |", last 20 matching lines)
→ gap signal (date-only if >7 days since last entry) → coverage disclaimer (mandatory verbatim) [honor]
```

- Ingest gate allows the journal read (trusted zone) — passes freely.
- The "last 20 lines" filter is LLM-executed (no shell grep; the model applies the filter judgment).
- The coverage disclaimer is HONOR-SYSTEM — no hook enforces it is printed verbatim. The skill says to always print it; nothing verifies.

**Step 3 — Candidate search (Tier 0 → Tier 1 ordering)**

*Tier 0 — Obsidian semantic search (try first):*

```
/read skill → Bash: npx -y obsidian-brain@1.7.24 search "<query>"
  (VAULT_PATH=$DRIVE, DATA_DIR=$HOME/.local/share/obsidian-brain)
→ ~/.local/share/obsidian-brain index → guard_egress.sh + enforce_egress_allowlist.sh [hook, blocking]
```

- The egress hooks fire on every Bash PreToolUse (settings.json PreToolUse Bash matchers). Whether `npx` hits an allowlisted host determines pass/block.
- On error/empty result: fail-safe pass-through to Tier 1. The staleness caveat (index may not reflect the latest files) is noted in skill prose; no hook checks index age.
- Tier ordering (try Tier 0 before Tier 1) is HONOR-SYSTEM — no hook enforces it.

*Tier 1 — Live filesystem search:*

```
/read skill → Read/Glob/Grep →
  $DRIVE/desks/{desk}/records/**
  $DRIVE/desks/{desk}/projects/**/*.md
  $DRIVE/state/projects/**/*.md
  $DRIVE/desks/{desk}/state/current.md
  $DRIVE/state/open-loops.md
  $DRIVE/desks/{desk}/canon/current.md + $DRIVE/desks/{desk}/canon/**/*.md
  $DRIVE/shared/**/*.md  (if cross-desk)
→ ingest_gate_enforce.sh [hook, PreToolUse Read, BLOCKING for deny cases — passes for all .md in trusted zone]
```

- `ingest_gate_enforce.sh` fires on every Read call. For `.md` files inside `$DRIVE/Lifehack/`: exit 0 (allow). External `.md`: BLOCK. `.pdf`/`.docx`/`.xlsx`/`.csv`: BLOCK always. For normal `/read` internal reads the hook is always a pass-through — it provides protection against external injection but never constrains the element's own reads. This is correct by design.

**Step 3.9 — Load the right ALTITUDE, not just the right topic**

```
/read skill → in-context depth selection over the candidate set → tip-first load, descend only on need
→ none [in-context, no file I/O] [honor]
```

- **The premise:** a read that returns the right *subject* at the wrong *depth* is still a bad read — it either buries the session in detail it cannot use, or hands it a summary when it needed specifics.
- **Start at the highest altitude that answers the question; descend only if it does not.** Canon and a brief's FRAME are the tip; `records/` are the base. Do not open the base when the tip answers it.
- **A pointer beats a paste.** When a file is large and only its existence or location matters to the task, load the pointer — path plus one line — not the body. **Say that the pointer was loaded instead of the body.**
- **Match depth to the ask.** *"Where does X live?"* is a tip question; *"why did X fail on the 14th?"* is a base question. Answering either at the wrong level costs the window twice: once loading it, once reasoning past it.
- **When you descend, say why** — *"canon answered the what; pulling the record for the when."*
- ⚠ **Altitude is NOT relevance, and this step is not Step 4.** Step 4 ranks *which* files; this ranks *how deep*. A perfectly relevant file loaded at the wrong depth still costs the session — which is why the two are separate steps rather than one ranking pass.
- Enforcement: `[honor]`. Nothing measures the depth chosen, and nothing verifies that a descent or a pointer-instead-of-body was declared.

**Step 4 — Prioritize candidates**

```
/read skill → in-context reasoning → ranked candidate list [in-context, no file I/O]
```

No file I/O. No gate. Pure in-context ranking of what was found (WHICH files — the depth question is Step 3.9's).

**Step 5 — Load and present files**

```
/read skill → Read tool → candidate files → ingest_gate_enforce.sh [hook, always passes for internal .md]
```

- Content loaded inline and presented to the user.
- `guard_canon_write.sh` (PreToolUse Write|Edit) does NOT fire on Read — canon is read without a gate (correct; reading canon is intentionally ungated; the guard only applies to writes).

**Step 5b — Skeptical envelope (trust labeling)**

```
/read skill → in-context label pass →
  Layer A: canon/ path OR vetted:true → load trusted, no label emitted (SKILL.md: "Load trusted, no label needed.")
  Layer B: records/ · state/ · non-canon → [source-of-record]
  Layer C: tier:snapshot OR shelf-life present → [snapshot / EXPIRED]
→ [honor]
```

- No hook enforces that the labels are applied. Entirely model-executed, honor-system. The label logic is defined in `system/confidence-model.md` and cited in the skill; nothing verifies the model applied it.

**Step 6 — Closing anchor**

```
/read skill → stdout → in-context synthesis [in-context, no file I/O]
```

Summary of what was loaded, what wasn't found, and the gap signal from Step 2b. Honor-system output.

---

#### `/checkin` additional step chain (layered on top of `/read`)

`/checkin` runs the full `/read` context load as its foundation, then adds the following steps:

**Step 0 (/checkin) — Front-door args OR PM flag resolve + mandatory arm**

*Front-door args path (the `/save` handoff's session-start entry point):*
```
/checkin <project> [<plan>] → resolve brief (registry {path}/brief.md or given path)
  → Bash: pm_flag.sh arm "<abs_brief_path>" "<slug>" "<desk>"  [honor]
  → Bash: plan_flag.sh set "<abs_plan_path>"  (if plan arg provided)  [honor]
  → skip pm_flag.sh status check; proceed directly to Step 1
```

- When `/checkin` is invoked with a project slug or absolute brief path (and optionally a plan path), the args are the EXPLICIT target — no guessing, no flag lookup. Both flags are armed in one shot. This is how `/save`'s session-close handoff paste-line resumes work in a fresh window. Honor-system — the model reads the invocation args.

*Normal invocation path (no args):*
```
/checkin skill → Bash: pm_flag.sh status → ~/.claude/run/pm/pm-sess-{ID}.flag → none [honor]
```

- If `"none"`: the skill says to ASK which project to check in on (never guess). The "ask-don't-guess" rule is honor-system — no hook enforces it.
- If a path is returned: resolve slug and brief; proceed to Step 1.

*Mandatory arm (fires on BOTH paths once the project is resolved — the RESUME fix):*
```
/checkin skill → Bash: pm_flag.sh arm "<abs_brief_path>" "<slug>" "<desk>"
→ writes ~/.claude/run/pm/pm-sess-{ID}.flag + appends ~/.claude/run/pm/arm-events.log [honor]
```

- The skill's Step 0 prose makes this mandatory: "ARM the project flag — don't just read it (RESUME fix). A window resumed on an old project usually has NO pm flag (or a stale/malformed one), so the status-bar `proj:` field and the `pm_persist` hook go blank or point at the wrong doc."
- `pm_flag.sh arm` writes: `doc_path`, `slug`, `desk`, `armed_at`, `cwd`, `session` to the flag file.
- Appends event to `arm-events.log` (prune-on-write at 500 lines; `PM_EVENTLOG_MAX=500`).
- No hook enforces correct arg order (`doc_path` must be first, `slug` second). A malformed arm (slug in path slot) produces broken `pm_persist.sh` injection on subsequent turns — known failure mode in the skill. Honor-system correctness.

**Step 1 (/checkin) — Scratchpad self-heal + Read brief in slot order**

*Scratchpad self-heal (do this FIRST, before reading anything else):*
```
/checkin skill → Read: {brief_path} (existence check only) → if ## SCRATCHPAD missing:
  Edit: {brief_path} — ADD empty ## SCRATCHPAD section (heading + standard sub-labels)
→ guard_write_paths.sh [hook, BLOCKING — brief path is approved] [honor for the "do this first" ordering]
```

- The SKILL.md Step 1 opens with: "Scratchpad self-heal (do this first). If the brief has no `## SCRATCHPAD` section (schema §7 — the fixed ephemeral working surface), ADD an empty one now (the heading + the standard sub-labels) before anything else — never run a check-in on a brief missing its scratchpad, since Step 3.6 harvests INTO it."
- This is an additive-first write: if the section exists, nothing happens; if absent, the heading is inserted. ADDITIVE ONLY — touch nothing else.
- The same self-heal requirement is in the `project-manager` skill ("Scratchpad self-heal (on touch)" — `Core mandate` item 2a), meaning any PM touch of a brief must also add the section if missing.
- `guard_write_paths.sh` fires on the conditional Edit (brief is in an approved Drive path → passes through). The "do-this-first" ordering before the read is honor-system.

*Then read the project doc in slot order:*
```
/checkin skill → Read: {brief_path} → sections: FRAME → STORY LOG → CURRENT STATE → KEY RESOURCES → linked plan
→ ingest_gate_enforce.sh [hook, passes for trusted-zone .md]
```

Reads the brief sequentially. The Frame-intake gate (brief FRAME is human-only, written `CONFIRMED`/`INFERRED`/`WAIVED`) is an always-honored constraint; no separate hook enforces it on the Read path.

**Step 1.5 (/checkin) — Huddle check**

```
/checkin skill → Bash: python3 $HOME/lifehack-brain/system/tools/huddle.py mine --session $CLAUDE_CODE_SESSION_ID
→ huddle channel store → none [honor]
```

Reads the active huddle channel for this session. Two separate locations: flag files at `~/.claude/run/huddle/huddle-{KEY}.flag`; message data at `$DRIVE/state/huddle/` (huddle.py HS_DIR). Honor-system — no hook enforces the call.

**Step 1.6 (/checkin) — Plan flag arm**

```
/checkin skill → Bash: plan_flag.sh set "<abs_plan_path>"
→ ~/.claude/run/plan/plan-{KEY}.flag [honor]
```

- Passively, the ExitPlanMode hook (`plan_flag.sh record`, settings.json PreToolUse Entry 5) records the most-recent plan file for the HUD — that is the passive arm path.
- The explicit arm here at Step 1.6 is fully honor-system: the skill says to do it; nothing forces it.

**Step 2 (/checkin) — Reconcile three time-horizons**

```
/checkin skill → in-context reasoning over brief + live session context → none [in-context, no file I/O]
```

- Compare three horizons:
  1. **Desired outcome** (stable — from FRAME; does not go stale).
  2. **Last-saved state** (from brief CURRENT STATE / STORY LOG — only as fresh as the last `/save`).
  3. **What's actually happened THIS session** (live, in-context — may be ahead of the doc).
- Name the deltas: what has been done since the last save? What plan steps are now stale (done, obsolete, or overtaken)? What dead-ends were hit this session that are not in the doc yet?
- This step is the core functional value of `/checkin` — the three-horizon reconciliation that gives the user the current picture across the gap between the doc and the live session. Honor-system; entirely in-context reasoning; no file I/O; no gate.

**Step 3 (/checkin) — Output the tight re-orientation block**

```
/checkin skill → stdout → in-context synthesis [honor]
```

- Output a scannable re-orientation block covering:
  - **Desired outcome:** one line (the stable anchor from FRAME).
  - **Where we are:** current state reconciled with this session.
  - **Don't re-try:** the relevant dead-ends / ruled-out paths.
  - **Stale in the plan:** plan steps that no longer apply.
  - **Scope for today:** the smallest viable next moves toward the outcome (Pareto-first).
- This is the user-facing deliverable of `/checkin` — the five-slot output that "replaces the manual check-in on the plan and the project manager prompt." Honor-system; no hook enforces format or that all five slots are present.

**Step 3.5 (/checkin) — Plan write (HUMAN-GATED)**

```
/checkin skill → [WAIT for explicit human confirmation] → Edit: linked plan file
→ guard_write_paths.sh + guard_ledger_discipline.sh + guard_throughline_write_scope.sh [hook, PreToolUse Write|Edit, BLOCKING]
→ validate_on_write.sh [hook, PostToolUse, advisory]
```

- **THE HUMAN-IN-THE-LOOP GATE IS HONOR-SYSTEM ONLY.** The skill says "WAIT for explicit confirmation. No silent writes." No hook enforces the pause. The PreToolUse Write|Edit hooks fire after the LLM calls Edit, not before the LLM decides to call Edit — a model could write the plan file without waiting and no hook stops the decision (the hooks would fire on the write but they guard path correctness / ledger discipline / scope, not "did the human say OK?"). The gate is ENTIRELY behavioral.
- `guard_write_paths.sh`: blocks writes outside approved Drive spine / `~/.claude/` paths. Plan files are in approved paths — passes through, but ensures the file doesn't land in the clone.
- `guard_ledger_discipline.sh`: scope is single file only (`state/debt-ledger.md`); blocks adding RESOLVED lines (not DONE — DONE is not in the forbidden pattern) to `## Open` sections there. Tangential here — plan files are not debt-ledger.md.
- `guard_throughline_write_scope.sh`: restricts writes to throughline-scoped files; plan file must be within scope.

**Step 3.6 (/checkin) — Scratchpad + Story Log + journal writes**

*Journal-first (the ordering constraint):*
```
/checkin skill → Edit: $DRIVE/system/journal.md → APPEND Story Log entry
→ guard_write_paths.sh [hook, BLOCKING] — journal.md is under $DRIVE_ROOT/*, which exits 0 unconditionally (blanket Drive pass-through, not an explicit per-file allowlist entry) [honor for ORDERING]
```

*Brief writes:*
```
/checkin skill → Edit: $DRIVE/{project_path}/brief.md (## SCRATCHPAD + ## STORY LOG appends)
→ guard_write_paths.sh + guard_ledger_discipline.sh + guard_throughline_write_scope.sh [hook, PreToolUse Write|Edit, BLOCKING]
→ guard_canon_write.sh [hook, PreToolUse Write|Edit — brief.md is NOT in a /canon/ path → PASSES THROUGH; brief writes are ungated by canon guard]
```

- Brief writes work: `brief.md` is not in a `/canon/` directory, so `guard_canon_write.sh` never fires on brief edits. By design — briefs are mutable project state, not canon.
- **JOURNAL-FIRST IS HONOR-SYSTEM.** No hook enforces that the journal write happens before (or as) the brief is edited. `guard_write_paths.sh` allows both paths; both writes are permitted independently. The ordering rule is skill prose only.

*Compaction — not run here:*

`/checkin` does not call `pad_archive.py` and does not clear or graduate `## SCRATCHPAD`. Compaction was removed from `/checkin` (it was firing on cold-pickup session launch and clearing a brief's orientation material before the operator had read it); `/save` is now the sole owner of the compaction engine, run once at session-close. `/checkin`'s role stops at the harvest-in append above (Step 3.6) — the pad is left intact for `/save` to compact. Canonical compaction procedure: `system/schemas/project-doc-schema.md → "BRIEF COMPACTION"`; see `elements/save.md`.

---

#### `project-manager` step chain (brief lifecycle)

`project-manager` wraps both `/read` and `/checkin` and adds:

**Slug routing and registry resolution**

```
project-manager skill → Read: $DRIVE/system/project-registry.md → slug routing → none [honor: ask-don't-guess on low confidence]
```

- The skill's core routing rule is **ask-don't-guess**: when the PM flag is absent or ambiguous, the skill asks which project to scope rather than silently committing to a slug. This applies at Frame-intake too — FRAME slots are never written as settled without user confirmation (CONFIRMED / INFERRED / THIN / MISSING / WAIVED rating on every slot).
- Routing branches: PM flag armed and consistent → proceed; PM flag armed but session looks inconsistent → ASK; no flag + one clear registry match → propose + one-tap confirm; no flag + ambiguous → ASK with candidates; new project → confirm name + register a new row; multi-project session → segment or ASK.
- On new project: add row to `$DRIVE/system/project-registry.md` (WRITE). This is one of the few registry-WRITE paths (the other is `/save` Step 0.5).

**Brief creation (Frame-intake gate)**

```
project-manager skill → [human confirms Frame] → Write: {project_path}/brief.md (FRAME slots rated CONFIRMED/INFERRED/THIN/MISSING; user declining a slot → WAIVED)
→ guard_write_paths.sh [hook, BLOCKING] + guard_canon_write.sh [hook, passes — brief is not in /canon/]
```

- The FRAME section (desired outcome · success criteria · constraints · scope edges) is HUMAN-ONLY. On CREATE: rate every frame slot `CONFIRMED / INFERRED / THIN / MISSING` (SKILL.md line 305); if the user declines a slot, mark it `WAIVED` (line 319). Never write FRAME as settled on a guess.
- The human-gate on FRAME is honor-system — the Write hooks don't distinguish FRAME content from other brief content. The gate is behavioral: the skill says not to write without confirmation; nothing blocks the write mechanically if the model decides to write without waiting.

**Build mode — `skill_anchor.sh` arm + four-gear conductor (a materially different operating mode)**

When the project is a BUILD (software, hook/skill/cron, dashboard — any make-a-thing work), `project-manager` additionally arms a second anchor:

```
project-manager skill (build) → Bash: skill_anchor.sh arm project-manager "$HOME/.claude/skills/project-manager/ANCHOR.md"
→ ~/.claude/run/anchor/ (anchor flag) [skill]
```

- `skill_anchor.sh arm` writes a session-scoped anchor flag at `~/.claude/run/anchor/` pointing to `ANCHOR.md`. A `UserPromptSubmit` hook picks this up and re-injects the build-conductor spine every turn (keeping the lead at 10,000 ft as the thread grows long).
- This stores are distinct from the pm_flag stores: `~/.claude/run/anchor/` is the build-conductor's own flag space.
- **ORIENTATION HANDSHAKE (do this FIRST, before any self-directed work):** when `project-manager` is invoked or re-invoked on a build, the first output is the four-beat handshake — (1) Identity + posture, (2) State of play ≤3 lines, (3) Recommended next move, (4) Hand over the wheel with the menu (Go / Scope Q&A / Full board / Redirect). Never bury the handshake under verification work; the user must feel oriented and in control in the first reply. Honor-system.
- **Scoping Q&A:** the lead interviews the user (batched 3–5 questions per round, each with a best-guess attached) to scope the work into surfaces/lanes, each tagged with a gear (gear-1 do-together / gear-2 background subagent / gear-3 Agent-Team wave / gear-4 dynamic workflow). Default is gear-2; gear-3 and gear-4 are opt-in. Output is a delegatable plan.
- **Four-gear delegation model:** gear-1 (coupled design, single-thread); gear-2 (decided one-surface chunk, background sonnet subagent); gear-3 (multiple coordinating surfaces, Agent-Team wave — opt-in); gear-4 (dozens-to-hundreds independent items, dynamic workflow — opt-in, read-only/autonomous). The build recipe is: Plan-first → decompose by surface → lock data contracts → fan out (gear-by-surface) → lead owns the merge gate.
- **READS ANCHOR.md, CHAINS to the build recipe.** The anchor file is the build-conductor's lean re-injection vehicle; the full doctrine is in `system/sops/build-conductor-sop.md`.
- **Off-switch:** `bash "$HOME/lifehack-brain/system/hooks/skill_anchor.sh" clear` (12h TTL backstops if forgotten).
- This operating mode is ENTIRELY ABSENT from the standard pm_flag step chain above. It adds a second flag store, a second arm step, the ANCHOR.md re-injection surface, and the conductor's step sequence. It fires only for builds; for planning/research/writing projects, the standard pm_flag path is the only mode.

**Journal-first write on project pickup**

```
project-manager skill → Edit: $DRIVE/system/journal.md (append) → guard_write_paths.sh [hook, passes] [honor for ordering]
```

Same journal-first constraint as `/checkin` Step 3.6 — honor-system ordering, no hook enforces precedence.

---

#### Per-turn ambient hooks (fire independently, not part of the skill step chains)

**`pm_persist.sh` — per-turn re-injection (UserPromptSubmit, every prompt):**

```
pm_persist.sh → reads ~/.claude/run/pm/pm-sess-{ID}.flag → awk-extracts CURRENT STATE/NEXT ACTION from brief (180-char limit)
→ injects "[project-manager ACTIVE] Source of truth: ..." to stdout [hook, UserPromptSubmit, advisory, non-blocking]
→ refreshes armed_at on pm/plan/scratch flags via sed in-place (shell write, bypasses all Write-tool hooks) [hook]
```

- Matcher: `UserPromptSubmit matcher=""` (all prompts). Always exit 0. Degrade-safe.
- Anti-injection scrub: bidi strip (perl) + C0–C1 control-char strip (tr) on the injected doc excerpt — live in code.
- TTL-refresh mechanism: `pm_persist.sh` calls `_refresh_armed_at` which writes the current timestamp to the flag file via `sed -i`. This is a shell-level file write — it BYPASSES all PreToolUse Write|Edit hooks. The flag can be refreshed without any guard seeing it. Intentional (the flag is machine-internal state, not Drive content), but a real hook-coverage gap for anyone auditing write coverage.
- ~~TTL discrepancy (doc vs code): `pm_flag.sh` uses `TTL_HOURS=36` for its stale check; `pm_persist.sh` has its own stale-check block at TTL_HOURS=12 (not updated when pm_flag.sh was bumped to 36h in 2026-07-11). In practice, `pm_persist.sh` refreshes `armed_at` every turn — so a live session's flag NEVER expires. The discrepancy matters only for crashed/dormant sessions: `pm_flag.sh status` would keep the flag alive 3x longer than `pm_persist.sh`'s own stale check. Both use the same session key (`CLAUDE_CODE_SESSION_ID`), so they target the same flag file. Benign in practice; real code drift.~~ ⛔ **CLOSED — corrected 2026-08-28 against the live source.** There is ONE definition (36h, `pm_flag.sh`); `pm_persist.sh` holds no independent literal and reads the number from the `ttl` verb. The duplicate was deleted 2026-08-14; the TTL was then *still* inert until 2026-08-15, because `_refresh_armed_at` re-stamped `armed_at` before the expiry check. ⚠ Note what this entry got wrong beyond the number: it called the per-turn refresh a *mitigation*, when that refresh was in fact the second bug — it is why the TTL could not fire at any value. Full account in `pm-flag.md` Edge Case 1.

**`save_routing_hint.sh` — save-phrase routing (UserPromptSubmit):**

```
save_routing_hint.sh → reads prompt text → regex-matches save verbs
→ pm_flag.sh status → emits "[save-routing] append to ## SCRATCHPAD of {brief}" or "ASK" [hook, advisory, non-blocking]
```

- Fires ONLY when a save-phrase regex matches the prompt.
- Handoff bail-out: if the prompt contains `"## SCRATCHPAD"` or `"/checkin"`, exits silent (2026-07-15 fix for false-fires on handoff paste).
- Relevant to `/checkin`'s scratchpad (routes "save this" to the active brief's `## SCRATCHPAD` during a `/checkin` session).

**`announce_plan_write.sh` — plan HUD (UserPromptSubmit):**

```
announce_plan_write.sh → diffs ~/.claude/plans/*.md vs per-session state
→ if new/modified: prints "📋 plan written: ..." [hook, advisory, non-blocking]
→ if NEW AND pm_flag armed: Python direct write to brief ## SCRATCHPAD (plan pointer) [HOOK-BYPASS GAP]
```

- The Python direct write (lines 77-86 of the hook script) uses `open(brief, "w").write()` — a direct Python file write that BYPASSES ALL PreToolUse Write|Edit hooks. `guard_write_paths.sh`, `guard_canon_write.sh`, `validate_on_write.sh`, `nudge_flow_drift.sh`, `auto_register_skill.sh` — none see this write. Confirmed gap.
- The write is to the brief's `## SCRATCHPAD` section (a plan pointer line), not to canon — the practical harm of the bypass is low, but the principle (that brief writes should route through the Write-tool hooks) is violated.

**`scratch_sweep_nudge.sh` — context-switch warning (UserPromptSubmit):**

```
scratch_sweep_nudge.sh → reads transcript_path from INPUT → opens that transcript file → scans for last usage block to extract token count
→ if >= 600k tokens AND new 100k-bucket AND (pm_flag OR scratch_flag armed): emits switch-session warning [hook, advisory, non-blocking]
```

- Matcher: `UserPromptSubmit`, no matcher key (match-all). Always exit 0.
- Fires at most once per 100k-token bucket past the 600k threshold.
- State tracked in `~/.claude/run/sweep/sweep-{KEY}.state`.

---

### STORES TOUCHED (complete list)

Every store this element reads or writes:

**READ:**

| Store | Access | Step |
|---|---|---|
| `~/.claude/run/pm/pm-sess-{ID}.flag` (or `pm-cwd-{hash}.flag`) | READ | /read Step 0, /checkin Step 0, pm_persist.sh, save_routing_hint.sh, announce_plan_write.sh, scratch_sweep_nudge.sh |
| `~/.claude/run/pm/arm-events.log` | READ | pm_flag_recover.py (external; referenced by /save Step 0.4, not /read) |
| `~/.claude/run/plan/plan-{KEY}.flag` | READ | pm_persist.sh (TTL-refresh each turn) |
| `~/.claude/run/scratch/scratch-{KEY}.flag` | READ | pm_persist.sh + scratch_sweep_nudge.sh |
| `~/.claude/run/sweep/sweep-{KEY}.state` | READ+WRITE | scratch_sweep_nudge.sh (token-bucket state) |
| `~/.claude/run/plan-announce/{KEY}.state` | READ+WRITE | announce_plan_write.sh (plan diff state) |
| `~/.claude/run/scratch-capture/cap-sess-{ID}.state` | READ+WRITE | scratch_capture_gate.sh (Stop hook — token-bucket checkpoint) |
| `~/.claude/run/scratch-capture/cap-sess-{ID}.pad` | READ+WRITE | scratch_capture_gate.sh (Stop hook — last-checkpoint pad sidecar for diff) |
| `~/.claude/run/anchor/` (anchor flag files) | WRITE (arm) / READ (re-inject) | project-manager build mode via skill_anchor.sh arm/clear |
| `~/.claude/plans/*.md` | READ | announce_plan_write.sh (diff) + /checkin Step 1.6 |
| `$DRIVE/system/project-registry.md` | READ | /read Step 0.6, /checkin Step 0, project-manager |
| `$DRIVE/system/journal.md` | READ | /read Step 2b (last-20 journal slice) |
| `$DRIVE/state/telos.md` | READ | session_context_loader.sh at SessionStart |
| `$DRIVE/state/pulse-brief.md` | READ | session_context_loader.sh at SessionStart |
| `$DRIVE/state/open-loops.md` | READ | /read Tier 1 Step 3 |
| `$DRIVE/desks/{desk}/canon/*.md` | READ | session_context_loader.sh (floor) + /read Step 0.6 (lazy walk) |
| `$DRIVE/records/canon/*.md` | READ | session_context_loader.sh (root mode) |
| `$DRIVE/desks/{desk}/state/current.md` | READ | /read Tier 1 |
| `$DRIVE/desks/{desk}/records/**/*.md` | READ | /read Tier 1 |
| `$DRIVE/desks/{desk}/projects/**/*.md` | READ | /read Tier 1 |
| `$DRIVE/state/projects/**/*.md` | READ | /read Tier 1 (v2 project folders) |
| `$DRIVE/{project_path}/brief.md` | READ | /checkin Step 1, project-manager, pm_persist.sh (excerpt) |
| `~/.local/share/obsidian-brain` | READ (index query) | /read Tier 0 via npx obsidian-brain |
| `$CLAUDE_CODE_SESSION_ID` (huddle.py session input) | READ | /checkin Step 1.5 |
| `$DRIVE/state/huddle/` (huddle message data — HS_DIR) | READ | /checkin Step 1.5 via huddle.py |

**WRITTEN (by /checkin + project-manager + ambient hooks only; /read is read-only):**

| Store | Written By | Step |
|---|---|---|
| `~/.claude/run/pm/pm-sess-{ID}.flag` | pm_flag.sh arm/clear (from /checkin Step 0, project-manager) | arm/clear |
| `~/.claude/run/pm/pm-sess-{ID}.flag` (armed_at refresh) | pm_persist.sh (sed in-place, bypasses Write-tool hooks) | every turn |
| `~/.claude/run/pm/arm-events.log` | pm_flag.sh arm/clear | append |
| `$DRIVE/{project_path}/brief.md` (## SCRATCHPAD + ## STORY LOG) | /checkin Step 3.6 (Edit, Write-tool path, hooks fire) | Step 3.6 |
| `$DRIVE/{project_path}/brief.md` (## SCRATCHPAD — plan pointer) | announce_plan_write.sh (direct Python write, Write-tool hooks BYPASS) | per-turn when new plan |
| `$DRIVE/system/journal.md` | /checkin Step 3.6 + project-manager (journal-first; honor-system ordering) | Step 3.6 |
| `$DRIVE/{project_path}/{brief}.pad-archive.md` | pad_archive.py (invoked from /save only, session-close) | compaction |
| `$DRIVE/system/project-registry.md` | project-manager on new project creation | slug registration |
| `~/.claude/plans/*.md` | plan mode (Claude built-in; announce_plan_write.sh watches) | plan write |
| `~/.claude/run/plan-ledger.md` | announce_plan_write.sh (fallback when no pm_flag) | per-turn |
| `~/.claude/run/plan/plan-{KEY}.flag` | plan_flag.sh set (/checkin Step 1.6) + ExitPlanMode hook | arm |
| `~/.claude/run/sweep/sweep-{KEY}.state` | scratch_sweep_nudge.sh | bucket counter |
| `~/.claude/run/plan-announce/{KEY}.state` | announce_plan_write.sh | plan diff state |

---

### GATES AND ENFORCEMENT (the honest map)

Every gate that fires on this element, with its real enforcement strength:

---

**1. `ingest_gate_enforce.sh` — REAL AND BLOCKING (fire-testable)**

Settings.json: PreToolUse matchers on Bash, WebFetch, WebSearch, Read (four separate registrations). Exit 2 + JSON on stderr = block (fail-closed). Exit 0 = allow.

What it does for this element:
- Blocks WebFetch (always) — `/read` never invokes WebFetch, so this never fires for this element's normal path.
- Blocks WebSearch (always) — same.
- Blocks Read on `.pdf`/`.docx`/`.xlsx`/`.csv` (always) — protects against a confused `/read` trying to load a non-.md file.
- Blocks Read of external `.md` outside the trusted zone (`~/lifehack-brain/`, `~/.claude/`, `$DRIVE/Lifehack/`).
- ALLOWS Read of all internal `Lifehack` `.md` — so every `/read` skill read of records, briefs, canon, state is a free pass-through.

Honest assessment: the gate is REAL and BLOCKING for its deny cases. For `/read`'s own internal reads, it is always a pass-through by design. It protects against EXTERNAL INJECTION, not against internal reads. The gate is correct and fire-testable; its protection doesn't constrain `/read`'s own operation.

---

**2. `guard_canon_write.sh` — REAL AND BLOCKING (fire-testable)**

Settings.json: PreToolUse matcher `Write|Edit`. Exit 2 = block.

What it does for this element:
- Blocks Write/Edit to any `**/canon/**` path lacking `authority:user` in frontmatter, or writes that would set `authority:skill` or `authority:archivist`.
- Does NOT fire on Read — `/read` reads canon freely (correct and intentional).
- Does NOT fire on brief writes — `brief.md` is not in a `/canon/` path.
- `/checkin`'s scratchpad/Story Log writes to `brief.md` pass through (correct; briefs are mutable).

Honest assessment: REAL AND BLOCKING for canon paths. Correct design — reading canon is ungated; writing canon requires human authority.

---

**3. `guard_write_paths.sh` — REAL AND BLOCKING (fire-testable)**

Settings.json: PreToolUse matcher `Write|Edit` (part of the Write|Edit block alongside `guard_ledger_discipline.sh` and `guard_throughline_write_scope.sh`).

What it does for this element:
- Blocks content writes into the git clone (content must go to Drive).
- Blocks writes to `~/.claude` auto-memory.
- Blocks writes outside approved zones.
- Allows `/checkin` Step 3.6 writes to the brief (under Drive, approved path).
- Allows journal appends (`$DRIVE/system/journal.md` passes through because all `$DRIVE_ROOT/*` paths exit 0 unconditionally — blanket Drive pass-through, not an explicit per-file allowlist entry).

Honest assessment: REAL AND BLOCKING. All of `/checkin`'s write paths pass through correctly (briefs + journal are approved paths).

---

**4. `pm_persist.sh` — REAL AND ADVISORY (fire-testable; non-blocking)**

Settings.json: UserPromptSubmit matcher="" (all prompts). Always exit 0.

What it does for this element:
- Re-injects `[project-manager ACTIVE]` reminder + brief excerpt into every turn when PM flag is armed. This is the mechanism that keeps project context visible between `/read` invocations — a passive continuous re-orientation.
- Refreshes TTL on pm/plan/scratch flags via shell sed (bypasses Write-tool hooks — intentional, machine-internal state).
- Anti-injection scrub (bidi + C0–C1 strip) on the injected excerpt — live in code.

Honest assessment: REAL, ADVISORY. The TTL-refresh shell write bypasses Write-tool hooks — a minor gap for hook-coverage auditing, but intentional (not malicious; the flag is machine state, not user content).

---

**5. `session_context_loader.sh` — REAL AND ADVISORY (fire-testable; non-blocking)**

Settings.json: SessionStart matcher="" (all sessions). Always exit 0.

What it does: pre-loads desk canon + TELOS + Pulse into context before any user prompt. The "always-loaded floor" that means `/read` in a well-launched session finds canon already present.

Honest assessment: REAL, ADVISORY. The canon-dedup between this hook and `/read` Step 0.6 is HONOR-SYSTEM (no hook verifies the skip).

---

**6. `save_routing_hint.sh` — REAL AND ADVISORY (fire-testable; non-blocking)**

Settings.json: UserPromptSubmit matcher="" (all prompts, but only fires when save-phrase regex matches). Always exit 0. Handoff bail-out (2026-07-15) prevents false-fires on `/checkin` paste.

Relevant to this element: routes "save this" during a `/checkin` session to the active brief's `## SCRATCHPAD`.

---

**7. `announce_plan_write.sh` (brief write path) — ADVISORY with HOOK-BYPASS GAP**

Settings.json: UserPromptSubmit matcher="" (all prompts). Advisory stdout inject + a direct Python file write to the brief.

The direct Python write (lines 77-86) bypasses ALL PreToolUse Write|Edit hooks. Not fire-testable as a guarded write — it is an unguarded write path. Confirmed gap.

---

**8. `scratch_capture_gate.sh` — REAL AND BLOCKING (Stop-event gate)**

Settings.json: `Stop` event — `command=bash ".../scratch_capture_gate.sh"`, `statusMessage="Scratchpad capture gate..."`. Blocking (can exit non-zero to bounce the turn).

What it does for this element:
- **EXECUTES on EVERY Stop event** (every turn-end). Resolves the active pad by precedence: (1) `scratch_flag` armed → its `scratch_path`; (2) else `pm_flag` → the brief's `## SCRATCHPAD` section; (3) else dormant (exit 0). On the common path — when no pad is armed, or when the token bucket has NOT advanced ≥100k since the last checkpoint — the hook exits 0 silently (no block, no user-visible output).
- **Only BLOCKS when capture is due:** when the token count HAS advanced ≥100k past the last checkpoint AND a pad is armed: exits non-zero with a `stop_hook_active` signal to bounce the turn, forcing the model to print a `📝 SCRATCHPAD CAPTURED` receipt. Mechanically diffs the pad vs the last checkpoint sidecar and hands the model the ADDED lines.
- Loop-safe: if `stop_hook_active` is already True in the input, exits 0 (prevents infinite bounce).
- Degrade-safe: any error → exit 0 (never wedges a turn).
- State: `~/.claude/run/scratch-capture/cap-sess-{ID}.state` (token-bucket checkpoint) + `cap-sess-{ID}.pad` sidecar (last-checkpoint pad snapshot for diffing).

**Enforcement picture change:** The draft originally classified pad compaction as honor-system only. The `scratch_capture_gate.sh` Stop-event hook changes this: **scratchpad CAPTURE at token-bucket boundaries is mechanically enforced** (the turn bounces until the receipt is printed). What remains honor-system is the `pad_archive.py` call specifically (the deep compaction + pad-clear flow, run solely by `/save` at session-close — `/checkin` no longer touches it) — that path is still honor-system. The Stop-gate enforces the lighter "acknowledge what was added to the pad" receipt; the full compaction procedure (archive → verify → clear → second-pass audit) is invoked by `/save` and has no hook interception. Two different levels of enforcement for two different capture operations.

---

**HONOR-SYSTEM (no hook enforces — the behavioral surface):**

| What | Why it matters |
|---|---|
| `/read` calls `pm_flag.sh status` (Step 0) | If skipped, /read won't lead with the brief when a project is armed. Silent mis-routing. |
| `/read` re-arms pm_flag when PM is active (Step 0) | If skipped, the TTL isn't refreshed and the flag ages toward stale on a resumed session. |
| Skeptical envelope labels (Step 5b) | Unlabeled canon vs records vs snapshots — the model can't calibrate confidence without them. |
| Journal coverage disclaimer (Step 2b) | Gap signal for last-read date; never seeing it means a stale read looks complete. |
| Delta-load dedup on a second `/read` this session (Step 2a) — of which the canon lazy-walk skip is one case | Duplicate context injection: re-stuffing the window with what it already holds. Wasteful, not incorrect — but an UNSTATED skip is indistinguishable from a search that missed the file, which is harmful. |
| Tier 0 → Tier 1 ordering | Semantic search tried first; if skipped, the semantic layer is effectively dead. |
| pad_archive.py full compaction before scratchpad clear | **Not this element's surface.** Compaction was removed from `/checkin`; `/save` alone now calls `pad_archive.py`, at session-close. The "no receipt = no clear" honor-system gap for that call belongs to `elements/save.md`, not memory-read. |
| PM flag arm after project resolution in /checkin Step 0 | If skipped, pm_persist.sh won't inject the brief on subsequent turns — the per-turn orientation goes dark. |
| Journal-first ordering in /checkin Step 3.6 | The brief is overwritten in place; if journal-first fails, precious info (decisions, dead-ends) that exists only in the brief can be lost if the brief write fails. |
| Human-in-the-loop gate for plan edits (Step 3.5) | No hook enforces the wait. The model must self-enforce; a runaway model could write the plan without human confirmation. |
| Frame-untouched on brief CREATE (project-manager) | No hook distinguishes FRAME content from other brief sections; the model must not write FRAME slots as settled without confirmation. |

---

### EDGE CASES

Known edge cases and how this element handles them:

1. **PM flag returns `"none"` during `/checkin`** → the skill says ASK which project to check in on (honor-system). A model could guess — no hook prevents it. The CLAUDE.md "ask-don't-guess" rule is the backstop (always-loaded).

2. **PM flag drops mid-session (36h TTL or crash)** → `/read` Step 0 sees `"none"` and falls back to room-scan. Unlike `/save`, `/read` has NO `pm_flag_recover.py` step — it just silently loses the project-aware routing. The brief won't be loaded first unless explicitly in the `/read` argument.

3. ~~**PM flag TTL discrepancy (pm_flag.sh 36h vs pm_persist.sh 12h)** → for live sessions: moot (pm_persist.sh refreshes armed_at every turn). For dormant/crashed sessions: pm_flag.sh keeps the flag alive 3x longer than pm_persist.sh's stale check. The 12h check in pm_persist.sh may delete a flag that pm_flag.sh considers still valid. Benign in practice; real code drift to track.~~ ⛔ **CLOSED 2026-08-28 — one definition (36h), read from `pm_flag.sh`'s `ttl` verb.** Duplicate literal deleted 2026-08-14; TTL made to actually fire 2026-08-15. Full account in `pm-flag.md` Edge Case 1.

4. **Registry `skill-system` slug double-suffix error** → the `{path}` field includes `/brief.md` already, making the standard `{path}/brief.md` resolver produce a doubled path. `/checkin` and `/read` resolution would fail to find this slug's brief. This is a live data error in the registry — not a code bug but a data bug. Flagged for the operator.

5. **Obsidian-brain index stale** → the index at `~/.local/share/obsidian-brain` may not reflect recent file writes (no guarantee of index freshness). The skill notes the staleness caveat; no hook checks index age. On stale miss, Tier 1 (live grep) will still find it — the Tier 0 miss is self-healing.

6. **npx obsidian-brain blocked by egress hooks** → the egress allowlist may block the npx call. Silent fail-through to Tier 1 (designed). But if the egress hooks are strict, this means Tier 0 is effectively dead in all sessions.

7. **`announce_plan_write.sh` direct Python write corrupts the brief** → the hook writes directly to `brief.md` via Python, bypassing all Write-tool hooks. If it gets the wrong path or an encoding issue, no PreToolUse hook would catch it. Post-write hooks (validate_on_write, nudge_flow_drift) don't fire either (they are PreToolUse or PostToolUse on TOOL calls, not shell writes).

8. **Long session — pad compaction fires multiple times per session** → N/A to this element now: `/checkin` no longer fires compaction (removed — it was clearing a brief's orientation material before a cold-pickup operator had read it). Only `/save`, at session-close, calls `pad_archive.py`; see `elements/save.md` for its idempotency behavior.

9. **Cross-desk read** → when the slug resolves to a different desk than the launch desk, `/read` includes `$DRIVE/shared/` in the Tier 1 search. The canon walk climbs to the root canon for the target desk. No hook distinguishes cross-desk reads.

10. **`pm_flag.sh arm` wrong arg order** → the skill warns about this; no hook validates. Malformed arm: pm_persist.sh would inject the bare slug (looks like a missing-path error) instead of the brief excerpt. The per-turn orientation injects garbage but doesn't error out.

---

### HARD PROHIBITIONS

What this element never does:

- **No READ from `~/.claude/projects/*/memory/` as a factual source — EVER.** This is the element's own primary hard rule (SKILL.md's first hard rule): "Auto-memory is behavioral-only. If the user believes something was saved there, tell them: 'Auto-memory is behavioral-only. If this was a finding or record, it belongs in `records/` — searching there instead.' Then proceed with Step 3." If a user believes something was saved to auto-memory, redirect them to `records/` and search there. The prohibition covers both reading auto-memory as content and presenting auto-memory content as factual. This is the READ-side prohibition; the write-side prohibition follows.
- No write to `~/.claude/projects/*/memory/` — never, under any circumstances (same prohibition as `/save`).
- No guessing which project is active when the PM flag is `"none"` — ASK-DON'T-GUESS is the invariant for both `/checkin` and `project-manager`.
- No silent slug commit when project is ambiguous.
- No writing to FRAME slots on a brief CREATE as settled fact — rate each slot `CONFIRMED`/`INFERRED`/`THIN`/`MISSING`; mark `WAIVED` only when the user explicitly declines a slot.
- No clearing the brief's `## SCRATCHPAD` before `pad_archive.py` confirms a successful archive (the receipt-gate rule — honor-system, but the prohibition is clear).
- No writing canon directly — `/read` never writes canon; `/checkin` and `project-manager` write briefs (not canon).
- No loading external `.md` files outside the trusted zone without going through `ingest_gate_enforce.sh` redirect.
- No re-reading same-desk canon already loaded by `session_context_loader.sh` (the dedup rule — honor-system but costs context budget).

---

### INTENT / CURRENT-VS-TARGET

**BY DESIGN (key audit correction — `identity.md` §Claim 1 + design-intent-brief §CORRECTION):**

The manual/directed nature of `/read` is INTENTIONAL. The earlier audit draft framed recall as "the flywheel only turns when the operator turns it" — a gap. The operator corrected this: "RECALL is already fairly automated — open a window from the correct desk, ask the question." The `session_context_loader.sh` floor pre-loads canon every session; `pm_persist.sh` re-injects project state every turn; `/read` is the directed top-up for specific context needs. The human-judgment gate on when to invoke `/read` is by design, not a defect.

The `/checkin` check in the checkin-conflicts-drift audit (conflicts-drift-A.md line 135) flagged `skills/checkin/SKILL.md` as "describes retirement of the core function" — a stale-path signal. The source audit confirms `/checkin` is live and used; the SKILL.md file may have prose describing an older framing that hasn't been fully updated. This is a doc-vs-code drift to investigate in the SKILL.md, not a functional defect.

**Current state → PARTIAL, for precise reasons:**

**What IS mechanically enforced (LIVE):**
- `ingest_gate_enforce.sh`: REAL AND BLOCKING for external reads (the gate that /read most benefits from, even if it never fires in the element's own trusted-zone reads).
- `guard_canon_write.sh`: REAL AND BLOCKING — canon cannot be accidentally written by /checkin.
- `guard_write_paths.sh`: REAL AND BLOCKING — /checkin's writes stay in correct Drive locations.
- `pm_persist.sh`: REAL (fires every turn, anti-injection scrubbed, TTL-refreshed).
- `session_context_loader.sh`: REAL (fires every session start).
- `scratch_capture_gate.sh`: REAL AND BLOCKING (Stop event) — bounces the turn at every 100k-token boundary when the pad is armed and capture is due; mechanically diffs pad vs sidecar checkpoint; forces receipt print. This is the enforcement layer for scratchpad CAPTURE (not full compaction).

**What is HONOR-SYSTEM (the PARTIAL gap):**
- The pm_flag.sh call in /read Step 0.
- Skeptical envelope labels (Step 5b).
- Journal coverage disclaimer (Step 2b).
- Delta-load dedup across `/read` invocations (Step 2a), including the canon lazy-walk skip when the floor already loaded it.
- Altitude-matching on load (Step 3.9) — tip-first, pointer-over-paste, and saying why on a descent.
- Tier ordering (Tier 0 before Tier 1).
- PM flag arm after project resolution in /checkin Step 0.
- Journal-first write ordering in /checkin Step 3.6.
- Human-in-the-loop gate for plan edits (Step 3.5).
- Frame-untouched on brief CREATE.

The honor-system surface is larger here than in the `/save` element. The `pad_archive.py` compaction gap is no longer part of this surface — compaction was removed from `/checkin`, so the risk now belongs solely to `/save` (see `elements/save.md`). The write-protection side (guard_write_paths + guard_canon_write) is strong; the read-routing side is largely behavioral. Hence PARTIAL (not LIVE).

**TARGET:**
1. **pm_flag.sh call in /read Step 0** — add to the `session_context_loader.sh` or a UserPromptSubmit hook so the flag check is automatic on every session rather than relying on the skill invoking it.
2. **TTL drift fix** — update `pm_persist.sh` TTL_HOURS from 12 to 36 to match `pm_flag.sh`. One-line fix; prevents the cross-script stale-check divergence.
3. **Registry `skill-system` double-suffix** — fix the `{path}` field in the registry. Data fix, not code.

---

### INTEROP SEAMS (shared-state edges to other elements — the organism view)

Seam verbs are from the closed vocabulary (§8.3): SHARES · WRITES-> · FEEDS · PROPOSES · KEYS-OFF · CHAINS · COMPLEMENTS · SYNCS · TRIGGERS · READS · GUARDED-BY.

---

**1. READS `save` (memory-write element) — the WRITE/READ halves of the same stores.**

`/save` WRITES-> the stores that `/read` READS: records, journal, canon, briefs, state/current, open-loops. The two elements are the write and read halves of the memory flywheel. No shared mutable file between them directly (they operate asynchronously — `/save` writes, `/read` reads what was written in prior sessions). `/save` alone runs the COMPACTION ENGINE (SC-4 invokes `pad_archive.py` on `{brief}.pad-archive.md`, at session-close); `/checkin` no longer shares it. A change to the compaction procedure (in `system/schemas/project-doc-schema.md`) changes only `/save`.

**2. KEYS-OFF `pm-flag` (pm_flag.sh routing hub).**

Every project-aware skill (save, read, checkin, project-manager, design-lifehack, huddle) routes through `pm_flag.sh`. The PM flag IS the project-routing identity for the session: which brief to read, where to write, which journal slug to use. If `pm_flag.sh` breaks, `/read` and `/checkin` lose project-aware routing silently (they degrade to room-scan, not error). The flag is a high-in-degree routing hub — the territory-map confirms it as the project-memory backbone.

**3. READS `canon` — GUARDED-BY `guard-canon-write`.**

This element READS the canon store (`$DRIVE/{desk}/canon/**/*.md`, `$DRIVE/records/canon/**/*.md`). The guard (`guard_canon_write.sh`) walls the WRITE side. The read is free and intentionally ungated. The element is a consumer of canon; the archivist and `/save` are the producers. Canon is read at two points: `session_context_loader.sh` (floor, always-on) and `/read` Step 0.6 (directed, lazy walk). These two must stay coordinated (no redundant load of same-desk canon).

**4. READS `journal` — WRITES-> it (`/checkin` + `project-manager`).**

`/read` Step 2b READS `$DRIVE/system/journal.md` (the last-20 slice for the desk/slug). `/checkin` Step 3.6 and `project-manager` WRITE-> the same journal (journal-first rule). The journal is the append-only chronological backstop shared by every write element — the FEEDS link: `planning-diary-capture.py` reads the journal to populate the Cal pipeline. If this element skips its journal write (honor-system failure), the Cal pipeline also silently loses the event.

**5. SHARES brief — with `save` + `project-manager`.**

All three read/write `$DRIVE/{project_path}/brief.md`. The FRAME section is human-only (never machine-written without CONFIRMED/INFERRED/THIN/MISSING labels; WAIVED if user declines a slot). The `## SCRATCHPAD` and `## STORY LOG` are the mutable working sections: `/checkin` appends; `/save` Step 7d syncs (session-close); `project-manager` creates and updates. `pm_persist.sh` injects an excerpt from `## CURRENT STATE / ## NEXT ACTION` every turn. The brief is the project's shared mutable operating state — the highest-churn file in the system.

**6. READS `project-registry` — shared identity hub with `save` + `project-manager`.**

`$DRIVE/system/project-registry.md` is the slug→path resolver all project-aware skills share. `/read` Step 0.6, `/checkin` Step 0, `/save` Step 0.5, and `project-manager` all key off this registry. `/save` and `project-manager` WRITE-> new rows on new project registration. A slug registered here is the identity shared across all skills. The registry has a known data error (`skill-system` double-suffix) that would break slug resolution for that project.

**7. SYNCS `session-context-loader` (→ `claude-md-pyramid`).**

`session_context_loader.sh` pre-loads the active desk canon at SessionStart. `/read` Step 0.6 is supposed to SKIP re-loading same-desk canon already loaded by the floor (dedup). These two must stay coordinated on what's already in context. The dedup is honor-system — no hook enforces it. Drift between them (the floor loads new canon files; `/read` still re-loads them) costs context budget but not correctness.

**8. COMPLEMENTS `archivist` (write/surface halves).**

The archivist (archivist-autoplace, archivist-route, archivist-deepmine) WRITES-> and PROPOSES to the records and canon stores. `/read` surfaces what the archivist filed. No direct shared mutable file between them — the archivist is the write-side intelligence; `/read` is the read-side retrieval. Together they form the full memory curation cycle: archivist places → `/read` retrieves.

**9. READS `huddle-board` (via `/checkin` Step 1.5).**

`/checkin` Step 1.5 reads the huddle channel via `huddle.py mine --session $CLAUDE_CODE_SESSION_ID`. Two separate locations: flag files at `~/.claude/run/huddle/huddle-{KEY}.flag`; message data (HS_DIR) at `$DRIVE/state/huddle/`. The huddle and huddle-board elements WRITE-> these channels; `/checkin` READS them. This is a read-only one-way seam for this element.

**10. FEEDS `planning` (via journal).**

`/checkin`'s journal-first writes (Step 3.6) are the upstream feed that `planning-diary-capture.py` reads to build the Cal pipeline. The pipeline keys off `$DRIVE/system/journal.md` — `/checkin` writes there; the planning pipeline reads it. Indirect but same store — a `/checkin` that skips the journal write also silently starves the planning pipeline.

**11. READS `telos` — pre-loaded by `session-context-loader`.**

`$DRIVE/state/telos.md` (the year-long strategic brief, read-only) is loaded by `session_context_loader.sh` at SessionStart. `/read` deduplicates against it (honor-system). Telos is consumed but never written by this element.

**12. FLAG: `obsidian-search-plane` is NOT in the ranked element list.**

`~/.local/share/obsidian-brain` (queried via `npx obsidian-brain@1.7.24`) is a distinct semantic search plane with its own index, staleness profile, and fail-safe path. It is a named tool in `/read` Tier 0 with its own operational characteristics (index freshness, egress-hook exposure, npx pinned version). It has no slug and no ranked-list entry. Candidate slug: `obsidian-search-plane`. Flagging for the operator as a new load-bearing candidate not in the inventory.

---

## AUTO-COMPUTED   (machine-only — hand-set at authoring; the F1.5 checker will own this once built)

- **maturity_label:** PARTIAL (honor)
- **check_detail:** pending label_checker.py — LIVE hooks fire on this element: `ingest_gate_enforce.sh` (PreToolUse Read/Bash — BLOCKS external reads; passes all internal trusted-zone reads freely; fire-tested via security-ingest-gate) · `guard_canon_write.sh` (PreToolUse Write|Edit — BLOCKS canon writes without authority:user; /checkin brief writes pass through correctly) · `guard_write_paths.sh` (PreToolUse Write|Edit — BLOCKS wrong-location writes; /checkin journal + brief paths are approved) · `pm_persist.sh` (UserPromptSubmit, every turn — advisory orient inject + TTL-refresh; anti-injection scrubbed; shell write bypasses Write-tool hooks) · `session_context_loader.sh` (SessionStart — advisory canon floor) · `save_routing_hint.sh` (UserPromptSubmit — advisory save-phrase routing) · `announce_plan_write.sh` (UserPromptSubmit — advisory plan HUD + direct Python brief write BYPASSING Write-tool hooks — confirmed gap) · `scratch_sweep_nudge.sh` (UserPromptSubmit — advisory context-switch warning) · **`scratch_capture_gate.sh` (Stop event — BLOCKING; bounces the turn when scratchpad capture is due at a 100k-token boundary; mechanically diffs pad vs sidecar and forces receipt print; state at `~/.claude/run/scratch-capture/`).** What is HONOR-SYSTEM: pm_flag.sh status + re-arm call at /read Step 0 · /read Step 2 orient statement first · /checkin Step 0 front-door-args mode · /checkin Steps 2+3 reconcile+re-orient · /checkin Step 1 scratchpad self-heal · project-manager build-mode skill_anchor.sh arm + handshake · skeptical envelope labels (Step 5b) · journal coverage disclaimer (Step 2b) · canon lazy-walk dedup · Tier 0→Tier 1 ordering · PM flag arm after project resolution · journal-first write ordering · human-gate on plan edits (Step 3.5) · Frame-untouched on brief CREATE. Significant honor-system surface on the read-routing side alongside strong write-protection hook coverage + `announce_plan_write.sh` Write-hook bypass gap + Stop-gate (enforces capture receipt, not full compaction — full compaction is `/save`'s alone now, at session-close) → **PARTIAL**. Not "reads unprotected" — the trusted-zone pass-through is correct design; the PARTIAL reflects behavioral routing gaps, not a compaction receipt-gate gap (that risk lives entirely in `elements/save.md` now).
