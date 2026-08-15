---
element: memory-write-save
title: "memory-write (/save) — element detail (ground/base altitude)"
subsystem: memory
altitude: base
record_type: organism-element
maturity_label: PARTIAL
generated_from:
  - skills/save/SKILL.md (v3.3)
  - skills/save/WRITE-FORMATS.md
  - system/schemas/project-doc-schema.md (BRIEF COMPACTION)
  - system/hooks/pm_flag.sh
  - system/hooks/pm_persist.sh
  - system/hooks/save_routing_hint.sh
  - system/hooks/scratch_capture_gate.sh
  - system/hooks/validate_on_write.sh
  - system/hooks/guard_write_paths.sh
  - system/hooks/guard_canon_write.sh
  - system/hooks/guard_ledger_discipline.sh
  - system/tools/pm_flag_recover.py
  - system/tools/canon_conflict_scan.py
  - system/tools/pad_archive.py
  - system/memory-system.md
  - system/organism/map-format-specs.md §0–§1
created_at: 2026-07-22
updated_at: 2026-07-22
status: active
authority: user
---

# memory-write (`/save`) — element detail

> **CITATION BANNER — what this page names that is not a file in this repository** (migration note, 2026-08-15).
> The description below is the donor system as it was, and it is kept as written. Each marker records what
> happened to that file AT THIS DESTINATION; none of them changes the description.
>
> ⛔ `system/topic-vocab.md` is not shipped, by ruling (the operator, 2026-08-11): no vocabulary ships with the
> system, because the vocabulary is the person's own. Here it lives at `<notes>/memory/topic-vocab.md` and is
> written by them. Read every "pick a slug from the controlled vocabulary" instruction below against that file.
>
> ⛔ `state/debt-ledger.md` is the person's own notes, not a repo file. Here it is
> `<notes>/state/debt-ledger.md`, written by `/save` and `/build` (`docs/data-layout.md`) — created by use,
> never committed.

> **Altitude = BASE (ground / street view).** The in-the-weeds detail of how `/save` actually works —
> every trigger, every mode, every step and sub-step, every store it touches, every gate and its real
> enforcement, and its overlaps with the rest of the system. The MIDDLE index (`system/organism/manual.md`)
> carries only a one-line pointer here; the TIP (`CLAUDE.md` schematic) shows only its box + arrows;
> the **skill itself** (`skills/save/SKILL.md`) is the fourth level — the executable runtime ground truth.
> This entry is the UNDERSTANDING layer: exhaustive description of what the skill does + why + how it connects.
>
> **One-line:** turn what happened in a session into durable, correctly-filed memory — with a human gate
> on anything permanent.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory script) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause).

---

## AUTHORED   (human-only)

### MODES

`/save` operates in four distinct modes. Mode is determined from the invocation argument before any step runs.

**1. Default / mid-session (single-artifact)**
Triggered by a bare `/save` WITH a specific argument naming what to save, or any invocation where neither session-close keywords nor "deep"/"ingestion" keywords appear. Runs the full step chain (Steps 0 → 0.4 → 0.5 → 1 → 2 → 2.5 → 2.7 → 3 → 4 → [4.6 if canon-bound] → [4.5 ONLY if canon candidate] → 5/5b/6/6b → 7 → 7c → 7c.5 → 7c.6 → 7d → 7e → 8 → 9). The CONFIRM-GATE (Step 4.5) fires ONLY if the artifact is a `tier: canon-proposal`; all other writes are autonomous with a one-line post-write receipt. The SC-1..SC-5 session-close curation flow does NOT run.

**2. Session-close (SC-1..SC-5)**
Triggered when: `/save` is called with no argument; OR the argument contains "session" / "close" / "end" / "wrap"; OR a noticeable number of session findings have accrued. Full curation runs (SC-1..SC-5) BEFORE the standard steps 7–9. SC produces all the items to write; the standard pipeline then writes them. Session-close mode has a single mandatory closer: the Step 8 continuation handoff absorbs both the write receipt AND the Step 9 coverage note; no standalone receipt is printed.

**3. Review mode**
Triggered when the argument contains "review". Same as v2.4 behavior: show everything before writing; wait for explicit approval at EVERY step (including normally-autonomous record writes). The CONFIRM-GATE becomes universal, not canon-gated.

**4. Deep / ingestion mode**
Triggered when the argument contains "deep" or "ingestion", OR when `/save` is invoked by the `world-model-builder` skill. Before writing ANY record (not just canon), render a detailed plain-language OUTLINE of every record about to be written and its exact destination, then WAIT for approval. The outline is EXPAND-not-compress: each record gets a full paragraph or several, not a one-liner. Render it via a BACKGROUND AGENT in the `/simplify` voice — but here "simplify" means plainer WORDS, never fewer: the outline is EXPAND-not-compress (SKILL.md lines 42/72 specify /simplify for the deep-mode outline; this is DISTINCT from Step 8's handoff, which correctly uses /explain). The style target is `skills/world-model-builder/PREVIEW-EXEMPLAR.md` exactly: (a) one-line origin, (b) full content point by point, (c) explicit KEEPER-vs-DATED split, (d) destination + do-no-harm action. The canon conflict/dedup scan (Step 4.6) still fires for every canon-bound item and its verdict appears in the same outline. The CANON-GATED PAUSE still applies; the "no abbreviated preview" hard rule means even the deep outline may not be reduced to one-liners. Batch all of a round's outlines in one panel; human approves/edits/kills per item; only then write.

---

### TRIGGERS

Every trigger that causes `/save` to run, and what it resolves to:

1. **Explicit `/save` (no argument)** — session-close mode; full curation (SC-1..SC-5).
2. **`/save <session-close keyword>`** — argument contains "session" / "close" / "end" / "wrap" → session-close mode.
3. **`/save <specific artifact>`** — default mid-session mode for that artifact.
4. **`/save review`** — review mode.
5. **`/save deep` or `/save ingestion`** — deep mode.
6. **`/save` invoked by `world-model-builder`** — deep mode automatically.
7. **Noticeable volume of session findings** — the skill may self-trigger session-close mode without an explicit command when findings have clearly accumulated.
8. **Natural-language "save this" / "remember this" / "capture this"** — intercepted upstream by `save_routing_hint.sh` (UserPromptSubmit hook); see "Trigger Disambiguation" below.

**Trigger Disambiguation — the routing-hint decision (critical):**
- **Bare "save this" / "remember this" WITH a project armed** → DUMB CAPTURE only. `save_routing_hint.sh` intercepts this BEFORE `/save` runs and routes it to append to the active brief's `## SCRATCHPAD` directly — the full extract-tier-route flow does NOT run. This is not `/save`; it is a scratchpad append.
- **Bare "save" / "save this" with NO project armed** → does not silently guess a home. `save_routing_hint.sh` forces an **ASK**: *"No project's active — save to a standalone scratchpad, or which project's brief?"* `[human]` `[hook]`. The CLAUDE.md save-routing rule is the always-loaded backstop for this behavior.
- **Explicit `/save`** (the slash command) WITH no project → runs the FULL curation flow to a standalone destination (the full step chain still runs, Step 7d fires only if a brief happens to exist).
- **`scratch_capture_gate.sh` (Stop hook)** fires independently — once per ~100k-token bucket when an active pad exists, emitting a `decision:block` that forces the model to surface a captured-lines diff. This is complementary to, not a replacement for, SC-4 F5.6 delta-capture.

---

### FULL STEP CHAIN

The complete ordered step chain, with every sub-step and its enforcement tag.

---

#### Step 0 — Project-manager check

`skill → pm_flag.sh status → session PM-flag → route destination [skill]`

Run: `bash "$HOME/lifehack-brain/system/hooks/pm_flag.sh" status`

- **Output = a doc path** → project is armed. The active project brief is the primary destination: Step 7d is promoted to primary write (use the returned doc path — do NOT re-infer the slug). After saving, re-arm the flag to refresh its TTL.
- **Output = `none`** → first run Step 0.4 (PM-flag drop recovery). If 0.4 recovers a project, use it; if nothing is recovered, proceed as a normal `/save` (Step 7d fires only if a brief happens to exist at the end).
- **If `pm_flag.sh` errors for any reason** → ignore silently and proceed with normal `/save`. The flag must never block a save.

---

#### Step 0.4 — PM-flag drop recovery (fires ONLY when Step 0 returned `none`)

`skill → pm_flag_recover.py + arm-events.log → recover silently-expired flag [skill]`

**Why it exists:** the flag has a 36-hour TTL and self-deletes on `status` past expiry. On a long session the flag can silently self-destruct, after which `/save` sees `none` and skips the brief sync. This step is the safety net.

**Source of truth = the durable logbook, not the chat transcript.** Every real `pm_flag.sh arm`/`clear` appends a TSV line to `~/.claude/run/pm/arm-events.log` (format: `<ts>⇥<arm|clear>⇥<doc>⇥<slug>⇥<desk>⇥<session>`). Recovery keys off that logbook — only genuinely-executed arms can be recovered; example/test/documented arm commands cannot trip a false recovery.

Run: `python3 "$HOME/lifehack-brain/system/tools/pm_flag_recover.py"`

Outputs exactly one of:
- **`NONE`** → no arm/clear event for this session → nothing to recover → proceed as normal `none` save.
- **`CLEAR`** → last event was an intentional `clear` → do nothing; respect the stop; proceed as `none`. Never resurrect a deliberately-cleared flag.
- **`ARM<TAB>doc_path<TAB>slug<TAB>desk`** → flag dropped by accident (TTL/loss), but this session WAS tracking that project. Surface for a one-tap confirm (never silent, ASK-DON'T-GUESS):
  > *"The project flag reads `none`, but this session armed `<slug>` earlier (brief at `<doc_path>`) and never cleared it — the flag likely expired (36h TTL). Sync its brief and re-arm tracking? [y/n]"*
  - On **`y`**: treat `<slug>` as the resolved project for the WHOLE save (Steps 3, 5, 7d); re-arm the flag.
  - On **`n`**: proceed as a normal `none` save.
  If the save ends with no brief synced (NONE outcome), surface a visible one-liner (NOT a blocking prompt): *"ℹ Brief sync skipped — no armed project found for this session. If you WERE working a project, re-arm it and re-run /save."*

**Guardrails:** deterministic (keys off the recorded `arm` in the durable logbook, not vibes); session-scoped (only THIS session's events); confirmed before acting; intent-respecting (a `clear` is never overridden).

---

#### Step 0.5 — Slug routing (ASK-DON'T-GUESS — the confidence ladder)

`skill → slug confidence-ladder → system/project-registry.md → which project owns this; ASK-DON'T-GUESS [human on low confidence]`

**First: is this even project work?** The slug is a FILING LABEL, not a save-precondition — a save NEVER blocks on it.

- **System / root / governance work** (CLAUDE.md, SOPs, hooks, skills, system docs — no desk, no project) → file to root `$DRIVE/records/{type}/` with a title-derived label. Skip the ladder.
- **Clear desk record** (desk obvious + type clear, no specific project) → file to `$DRIVE/desks/{desk}/records/{type}/`. Skip the ladder.
- **Genuine project work** → run the confidence ladder:
  1. Declared and consistent flag → proceed silently.
  2. Flag set but session looks inconsistent (mid-session switch) → ASK: "The active project is X, but this session looks like Y — route to Y, split, or stay on X?"
  3. No flag + one clear registry match → propose + one-tap confirm. Never a silent commit on a guess.
  4. No flag + ambiguous / multiple / no match → ASK; present registry candidates + "new project".
  5. New project → confirm + register. Add to `$DRIVE/system/project-registry.md` BEFORE the first save. This is IDENTITY only — NOT the frame (see Step 7d CREATE vs UPDATE).
  6. Multi-project session → segment + route each, or ask which. Don't force one slug.

The resolved slug from this step is authoritative for the WHOLE save — Steps 3, 5, and 7 use it and must NOT re-infer a different one. `<doc_path>` passed to arm must be ABSOLUTE. After resolving, arm/refresh the flag for the chosen slug.

---

#### SC-1 — Extract-with-reasoning (session-close only)

`skill → transcript ($CLAUDE_CODE_SESSION_ID) → /tmp temp file → extract findings-with-reasoning [skill]`

**Fires in session-close mode only.** Job: mechanically pull discrete, addressable items from the raw session record — each anchored to the transcript, each carrying its question and WHY. Structures the extraction; does NOT summarize.

**(a) Raw transcript pull — locate the session record first.**

Transcripts are `.jsonl` files. Resolution (confirmed 2026-06-28):
```bash
TRANSCRIPT=$(ls "$HOME/.claude/projects/"*"/${CLAUDE_CODE_SESSION_ID}.jsonl" 2>/dev/null | head -1)
```
- Env var is `$CLAUDE_CODE_SESSION_ID` (NOT `$CLAUDE_SESSION_ID`, which is empty).
- Transcripts live DIRECTLY in the project dir — there is **no** `conversations/` subdir.
- The project-slug dir is the working directory path with `/` replaced by `-` (e.g., `-Users-<you>-lifehack-brain`).
- If `$TRANSCRIPT` is empty → fall back to context-window pull AND note the fallback in the journal entry so the lossy pass is visible.

Write extracted content to a working temp file (e.g., `/tmp/save-extract-<date>.md`) so it survives context compaction and can be re-read in subsequent passes.

**(b) Six targeted passes — extract by category, not one "summarize it all" sweep:**
1. Decisions — anything explicitly committed/confirmed by the human
2. Dead-ends — anything tried and ruled out (the WHY is required)
3. Key numbers / snapshots — any dollar amount, count, date, or fast-stale value
4. Open questions — anything unresolved at session close
5. Suggestions / leanings — any recommendation or direction not yet committed
6. Reasoning / WHY — the reasoning chain behind each item found above

**(c) Anchor every item to evidence — cite the turn / quote the line.** An item that cannot be anchored to something said or done in the transcript does NOT get written. "I think we discussed X" is NOT an anchor.

**(d) Completeness pass.** After the targeted passes, one final sweep: what was tried, pivoted on, or surfaced that none of the above passes caught? These often fall between categories and are the most valuable.

**For trivial sessions** (a single quick lookup, no decisions, no dead-ends): skip the transcript pull; surface explicitly that nothing warrants persisting; skip the rest of session-close flow.

**Output:** a flat list of `{question, why, conclusion}` triples, one per finding, each anchored to evidence. Internal working material — NOT shown to the user yet (they see them in SC-4's pre-fill).

---

#### SC-2 — Tier-by-durability (session-close only)

`skill → durability decision-tree → — → tier each item {ephemeral · record · state · canon} [skill]`

Apply the if/else ladder from `system/confidence-model.md §3` exactly — no improvisation:

```
human-vetted?
  → tier: canon-proposal  (machine never sets vetted:true — becomes a proposal in records/proposals/)

fast-stale value? (a number, live tally, this-week datum — expires within days/weeks)
  → tier: snapshot
  → REQUIRE shelf-life field

has at least one explicit source_ref?
  → tier: dated-record
  → confidence: CONFIRMED (authoritative + direct source)
                INFERRED (indirect or requires interpretation)
                HYPOTHESIS (plausible but circumstantial)

no source_ref, no vetted flag, no expiry date
  → tier: snapshot
  → confidence: INFERRED or UNKNOWN
```

Output: each item from SC-1 carries `{tier, confidence, type, shelf-life?}`.

---

#### SC-3 — Assign register (session-close only)

`skill → register taxonomy → — → tag type; a possibility is NEVER machine-promoted to decision/canon [skill]`

**The nine-type taxonomy (from `system/confidence-model.md §2a`):**

| Test | Type |
|---|---|
| Human explicitly decided/committed? | `decision` |
| Still open — direction, hypothesis, possibility? | `possibility` |
| Recommendation or leaning, not committed? | `suggestion` |
| Trade-off analysis? | `pros-cons` (preserved AS THE WHOLE WEIGHING — never collapsed) |
| Tried-and-ruled-out path? | `dead-end` (WHY required) |
| Unresolved thread? | `open-question` |
| Derived fact or synthesis? (default) | `finding` |
| Live number / fast-stale datum? | `snapshot` |
| Prescriptive always-on directive? | `rule` — **STOP. Never auto-assign. Human-only elevation.** |

**DEFAULT = the softest register that fits.** The model NEVER auto-assigns `decision` or `rule`.

**Register-preservation rule (critical):** once assigned, a register MUST survive through all downstream steps. A `possibility` stays a possibility through SC-4's pre-fill, the confirm-gate, and SC-5's write. It cannot be promoted to decision or canon-proposal by the machine. Two `possibility` items on the same topic are a CONFLICT to surface (not merge) — let the Archivist handle it.

Output: each item has a final `type:` that reflects its actual epistemic state.

---

#### SC-4 — Pre-fill + confirm-gate + brief compaction (session-close only)

`skill → pre-fill panel (canon LIFTED OUT) → — → CONFIRM-GATE: WAIT for explicit yes [human] — fires ONLY if canon candidate present; otherwise autonomous`

**Job:** Present each item with a best-guess placement so the human confirms, corrects, or cuts. The human is never asked to author cold — they react to a pre-filled proposal.

##### F5.6 — FINAL DELTA-CAPTURE FIRST (HARD — runs before any promotion or compaction)

`skill → Edit → active brief ## SCRATCHPAD → append any missing session decisions before compaction [skill]`

The background capture-gate (`scratch_capture_gate.sh`) may not have caught the most recent chunk. So FIRST: scan this session for any decision / outcome / dead-end settled since the last auto-capture that is NOT yet in the `## SCRATCHPAD`, and APPEND it to the `## SCRATCHPAD` via Edit — so the pad is complete — THEN proceed. This closes the gap between the last gate-capture and the save. This runs BEFORE the compaction, and BEFORE the pre-fill panel.

##### The panel style (WHERE-FIRST, two tiers — HARD)

Imitate `skills/save/SAVE-PANEL-EXEMPLAR.md` exactly. Items are grouped by DESTINATION, not by type.

**TIER 1 — the placement glance (what SC-4 shows FIRST):**
1. Group by destination bucket; the bucket is a HEADER, printed once.
2. Order buckets by permanence: CANON first, then RECORDS, CURRENT, then rarer buckets only when something lands there. Bucket meanings: CANON (permanent core truth) · RECORDS (dated note) · CURRENT/STATE (live project state) · JOURNAL (system diary) · DEBT-LOG (loose ends / deferred) · LESSONS (system learnings) · TO-DO (open loop).
2b. NAME THE CANON ALTITUDE — never the bare word "CANON" when something lands there. Canon lives at several altitudes (`system/knowledge-altitude.md §3`): label as `CANON · global` / `CANON · desk ({desk})` / `CANON · sub-folder ({area})` / `CANON · project ({name})` / `CANON · deep` — the human-readable LEVEL, NOT the file path (the exact path waits for Tier 2). If canon items span more than one altitude, sub-group them by altitude under the CANON header.
3. ALWAYS show CANON even when empty — print "— nothing going here this time." so "nothing touches your permanent truths" is stated out loud, never silent. Hide the other empty buckets.
4. Each item = a GLOBAL number (1..N across the whole panel, in bucket order) + a short bold name + ONE plain sentence. One line; NO path on this glance.
5. Flag sensitive items with a small `· private` marker on the name line.
6. End by asking the human to approve / correct / cut by number.

**TIER 2 — the pre-write detail (shown on the human's OK, right before writing):** for each approved item, show the EXACT destination path + create/update + the full content outline. For DEEP/ingestion mode, Tier 2 IS the expand-not-compress outline. Items in Tier 2 are grouped by register section (DECISIONS / SUGGESTIONS / POSSIBILITIES / PROS-CONS / FINDINGS / OPEN-QUESTIONS / DEAD-ENDS / SNAPSHOTS / [RULE — only if human-elevated]).

Format per item in Tier 2:
```
=== DECISIONS ===
[N] {title}
    tier:       dated-record
    confidence: CONFIRMED
    type:       decision
    → route:    {destination path}
    → action:   create | update
    excerpt:    "{1–2 sentence version}"
```

For any `type: rule` item (only after human elevation), display the RULE WARNING before writing: rules are always-on, generalize to cases they weren't written for, accrete silently, and are rarely revisited. Even on confirm, writes as a canon-PROPOSAL (`vetted: false`), never `vetted: true`.

##### Debt-clear check (inside SC-4, not a separate hook)

Immediately after the pre-fill list, surface:
> Any technical debt from this session to clear? (press enter to skip)

A skip is accepted and is logged in the journal entry so the gap is visible. A skip in autonomous/non-interactive mode is also accepted, but must be logged.

##### Brief compaction (session-close — the scratchpad roll-up)

Runs RIGHT AFTER the debt-clear check. Fires automatically when ALL three conditions hold: (a) session-close mode, (b) Step 0 / 0.4 resolved an active project brief, AND (c) that brief's `## SCRATCHPAD` holds real content. Else skip silently. **AUTOMATIC — it ALWAYS runs when those three conditions hold; NO skip, NO "let it ride," NO approval gate.**

Source of truth for the procedure: `system/schemas/project-doc-schema.md` → "BRIEF COMPACTION" (follow its 8 steps exactly). The steps, in order:

**Step 13a — Copy-everything-first + receipt-gate (fail-closed):**
`skill [Bash exception] → pad_archive.py archive → {brief}.pad-archive.md → append WHOLE pad verbatim + readback → emits RECEIPT on exit 0 [skill]`
Call `python3 $HOME/lifehack-brain/system/tools/pad_archive.py archive "<abs_brief_path>"`. It appends the ENTIRE `## SCRATCHPAD` verbatim (everything — NO choreography carve-out) to the append-only `{brief}.pad-archive.md`, reads it back, and prints `RECEIPT <hash>` on exit 0. The archive file is chained + self-describing: `compaction #N · ISO-ts · host · prev-hash · hash`. Idempotent (unchanged pad → no duplicate block).

**Step 13a-verify — Chain integrity check:**
`skill → pad_archive.py verify → {brief}.pad-archive.md → chain + counter integrity [skill]`
Then run `python3 $HOME/lifehack-brain/system/tools/pad_archive.py verify "<abs_brief_path>"`. Exit 0 = intact; a NONZERO exit means a broken prev-hash chain or a missing compaction → surface a `⚠ ARCHIVE INTEGRITY` note (historical tamper/gap to investigate; does NOT block this run's clear — this run's block is safe).

**Step 13b — Receipt-gate (fail-closed):**
`skill → receipt check → — → ABORT if no fresh receipt [skill]`
**RECEIPT-GATE:** the clear in step 13e is FORBIDDEN unless step 13a returned exit 0 WITH a fresh RECEIPT. If the script is not called, errors, or exits non-zero → **ABORT: do NOT clear anything; prepend a loud `> ⚠ COMPACTION ABORTED {ts} — archive not confirmed; pad left intact` line to `## SCRATCHPAD` and surface to the user.** No receipt = no clear (silent-loss is structurally impossible).

**Step 13c — Classify + graduate:**
`skill → model judgment → ## Story Log + ## Current State board + ## Open Loops + ## Key Resources → GRADUATE durable items [honor]`
Classify each scratchpad item (model judgment; safety already banked in 13a–13b, so a wrong call is caught in 13f, never lost):
- Settled decision / win → STORY LOG (`STATUS: locked`) + board **✅ LOCKED**; refresh the live-status line.
- Dead-end / demoted / stale → STORY LOG (`STATUS: superseded/killed`, WITH the why) + board **⛔ RULED-OUT** (one-line + pointer). **PRESERVE every dead-end.**
- Open thread → OPEN LOOPS + board **❓ OPEN**.
- Resource / ID / path → KEY RESOURCES.
- Pure choreography with no lasting lesson → drop (safe in the archive from 13a).
NEVER touch §0 / §1 FRAME content — ever.

**Step 13d — Journal-first for precious keepers:**
`skill → Write → system/journal.md → journal-first for precious keepers before/as the brief is rewritten [honor]`
Every precious keeper (decision / dead-end / number) hits the journal before/as it lands in the brief.

**Step 13e — Clear graduated items:**
`skill → Edit → ## SCRATCHPAD → CLEAR only the graduated items; unresolved/recent stay [skill]`
Only now that step 13b returned a receipt: remove the graduated items from `## SCRATCHPAD`. Leave unresolved/recent items.

**Step 13f — Self-healing completeness diff:**
`skill → self-healing diff (mechanical pre-filter → judge-by-meaning) → ## Story Log → write in any confirmed miss [honor]`
For each item just cleared: first a mechanical pre-filter (does its text appear in the STORY LOG?) to skip obvious hits cheaply; then judge BY MEANING for the residual (reworded ≠ missing). **If a durable item did NOT land → WRITE IT INTO the STORY LOG now (self-heal — do not merely flag).** {H} = count healed.

**Step 13g — Independent second-pass:**
`skill → spawn 1 isolated read-only sonnet subagent → newest {brief}.pad-archive.md block vs durable sections → return any durable item not represented; main session writes confirmed misses [honor]`
(Mandatory skill step but model-executed; no hook forces the spawn. This is a structural note: a `spawn subagent` instruction inside a skill is advisory, not mechanically enforced — the main session can execute the audit itself as a fallback.)

**Step 13h — Print receipt:**
`skill → stdout → — → print compaction receipt [honor]`
> 📝 **Compaction done** — `## SCRATCHPAD` had {N} items → **Story Log +{S}** · **board** ✅{L}/⛔{K}/❓{J} · **dropped {D}** · **self-healed {H}** · **2nd-pass recovered {R}** · **archive #{compaction-N}**. Restore: open `{brief}.pad-archive.md`, find the block for today, copy notes back.

This receipt is a REPORT, not an approval prompt.

##### CANON-GATED PAUSE (governs whether SC-4 waits)

Check the survivors for a `tier: canon-proposal` item:
- **NO canon candidate** → do NOT wait. Go straight to SC-5, write every survivor, then close through the single Step 8 continuation handoff (which absorbs the receipt + tucks the coverage note at its foot — see Step 8's SINGLE CLOSER rule); no panel-wait, no banner, no separate standalone receipt.
- **≥1 canon candidate** → render the pre-fill panel (canon lifted out per rule 3c above) + the pending-approval banner (`🟨🟨🟨 NOT SAVED YET — WAITING FOR YOUR APPROVAL`) and WAIT for an explicit human yes. Nothing canonical writes until this response is received. SC-5 fires only on confirmed items.

**Execute on confirm — show the panel ONCE, then write.** The pre-fill panel is rendered a single time. On any blanket approval ("save it" / "just /save" / "go" / approve-all) → proceed STRAIGHT to SC-5 and WRITE the survivors. Do NOT re-render the panel. A blanket approval confirms every pre-filled item at its pre-filled placement.

**Mixed batch (canon + reversible items):** the presence of a canon candidate pauses the WHOLE panel — do not split into a partial auto-write plus a separate canon gate.

---

#### SC-5 — Write-only-survivors (session-close only)

`skill → Write/Edit → records/ · state/ · records/proposals/ (canon candidates land here vetted:false — NOT a direct canon write) → write survivors [hook: validate_on_write nudges frontmatter · hook: guard_canon_write BLOCKS any direct canon write lacking authority:user]`

**Job:** Write exactly the items the human confirmed in SC-4. Nothing more. Cut items are silently dropped — no stub, no placeholder.

Write per tier, using the named section of `skills/save/WRITE-FORMATS.md`:

- **`tier: dated-record`** → write per **`WRITE-FORMATS.md` § "Dated record"** (frontmatter: `id`, `title`, `record_type: insight`, `desk`, `topic`, `created_at`, `updated_at`, `status: active`, `authority: skill`, `confidence`, `tier: dated-record`, `type`, `source_refs` REQUIRED).
- **`tier: canon-proposal`** → write to `records/proposals/` with `vetted: false` per **`WRITE-FORMATS.md` § "Canon-proposal"** (frontmatter: `id`, `title`, `record_type: proposals`, `status: draft`, `authority: skill`, `vetted: false`, `confidence: INFERRED`). NEVER `vetted: true`.
- **`tier: snapshot`** → write per **`WRITE-FORMATS.md` § "Snapshot"** (frontmatter includes `tier: snapshot`, `shelf-life: {ISO date}` — REQUIRED, never omit). Never promote to canon.
- **Journal SESSION CONTEXT entry** → append to `$DRIVE/system/journal.md` under a new heading per **`WRITE-FORMATS.md` § "Journal SESSION CONTEXT entry"** (fields: Session / Follows / Failed-changed / Key findings / End state / Missteps). If the SC-4 debt-clear was skipped, append: `**Debt-check:** skipped at close — debt items from this session may be uncaptured.`

---

#### Step 1 — Identify what to save (standard path)

If an argument was provided, use it as the description of what to save. If no argument, inspect the most recent output in the conversation. If genuinely unclear, surface a one-line candidate: "I'll save: [X]. Correct?" — but default to acting, not asking.

---

#### Step 2 — Identify the desk

Check the current working directory. If it contains `desks/{desk}`, the desk is clear. If ambiguous, infer from content. If genuinely ambiguous, ask once.

---

#### Step 2.5 — Resolve the project folder (v2 registry or legacy)

`skill → registry lookup → {path}/records vs legacy desks/{desk}/records → resolve the project folder [skill]`

Using the slug from Step 0.5, look it up in `$DRIVE/system/project-registry.md`:
- **Row has a 5th `{path}` field** → migrated project. Folder is `{path}`; brief is `{path}/brief.md`; records go in `{path}/records/`; canon is `{path}/canon.md`.
- **No `{path}` field** → legacy layout: records → `$DRIVE/desks/{desk}/records/{type}/`; brief → `$DRIVE/desks/{desk}/state/briefs/{slug}.md` or `$DRIVE/state/briefs/{slug}.md`.

Dual-resolution is the safety invariant: a save works whether or not the project has been migrated. When in doubt, legacy paths always work.

---

#### Step 2.7 — Confident-place vs DUMP-to-inbox (P13 — the friction gate)

`skill → home-clarity check → archivist inbox if unclear → confident-place vs DUMP-to-inbox (P13 friction gate) [skill]`

Before routing, classify by HOW CLEAR the home is:
- **CONFIDENT** — exactly ONE obvious, codified home → place it (proceed to Steps 3–7). The standard set: the journal, learnings, the debt ledger, the active project's brief + plan + state, a clearly-typed desk record where BOTH the desk AND the type are unambiguous.
- **AMBIGUOUS** — placing it would require a DECISION → do NOT decide in the moment. Preserve the content durably, then drop an inbox NOTE (Step 7e, `kind:content`) and STOP. The judgment set: a NEW project, research output / synthesized map, a new standalone file/doc with no obvious home, genuinely cross-cutting content, a record whose desk or type is truly unclear.

**Test:** "Is there exactly ONE obvious home, or does this need a decision?" One home → place. A decision → preserve + defer to the archivist. NEVER run the old "suggest a home and make the operator pick" step.

**Content is sacred — deferring placement NEVER loses content.** Save the ACTUAL content durably FIRST, THEN drop the pointer-note. Durable spot: if a project is ACTIVE and could use it → into THAT project's folder (`{path}/records/`); else → the inbox holding spot itself (`$DRIVE/system/archivist/insight-inbox/`).

---

#### Step 3 — Route using the three-question tree

`skill → three-question routing tree → choose the output port → facts/findings→records/ · phase/blockers→state/ · behavioral rule→CLAUDE.md [skill]`

Ask in order; stop at the first YES:

**Q1:** Does this contain facts, findings, dollar amounts, entity names, dates, analysis outputs, or professional/financial information? → YES: destination depends on Step 2.5 (migrated: `{path}/records/`; legacy: `$DRIVE/desks/{desk}/records/{type}/`). Choose type: `context` / `briefing` / `decision` / `summary` / `log` / `insight`. Then go to Step 4.

**Q2:** Is this about current phase, active blockers, open items, or next move? → YES: blocker/open item → `$DRIVE/state/open-loops.md`; phase/posture/orientation → `$DRIVE/desks/{desk}/state/current.md`. Then go to Step 5b.

**Q3:** Is this a behavioral rule about how Claude should operate? → YES: desk-specific rule → `~/lifehack-brain/desks/{desk}/CLAUDE.md`; cross-desk rule → `Lifehack/CLAUDE.md`. Then go to Step 6.

**None apply:** Ask one clarifying question. Do not default to auto-memory.

---

#### Step 4 — Deduplication check

`skill → glob the destination dir for a same-slug file → records/ → dedup: update-in-place vs new file [skill]`

Glob the destination directory for files whose name contains the slug. If a match is found: in review mode, show and ask. In default mode, update the existing file if it's a clear match, or write a new file if the content is distinct. If no match: continue.

---

#### Step 4.6 — Canon conflict/dedup scan (HARD — fires before ANY write into a canon file)

`skill → canon_conflict_scan.py → existing canon → NEW/DUPLICATE/CONFLICT, existing canon wins [skill]`

**Fires before writing OR proposing anything whose destination is a `canon.md` / `canon/…` file.** This reads canon CONTENT, not just filenames — in addition to Step 4's filename glob.

Run (NOT optional, NOT narrated):
```bash
python3 "$HOME/lifehack-brain/system/tools/canon_conflict_scan.py" \
  --canon-root <target desk/project canon dir> \
  --terms "<3-6 key terms of the incoming item>" \
  --title "<title>"
```
Exits non-zero if canon is unreadable (fail-closed — no scan, no write).

**Classify the incoming item:**
- **NEW** — nothing in canon covers this → safe to propose.
- **DUPLICATE** — canon already states this → do NOT write; point at the existing line.
- **CONFLICT** — the incoming fact contradicts or supersedes an existing canon line → **STOP.** Surface BOTH (existing vs incoming) to the human. Let them choose: keep-existing / replace / merge / keep-both. **Existing canon WINS by default** — never auto-overwrite, never silently resolve.

Surface the verdict in the confirm panel (Step 4.5) or the SC-4 / deep-mode outline, tagged NEW / DUPLICATE / CONFLICT with the exact file (+ line where known).

Also scan the siblings up the canon ladder for that desk/project (per `/read` Step 0.6 lazy-canon). The scope of this scan must match `/read`'s lazy-canon ladder — a conflict visible to `/read` must be visible here too.

**The feature, not a byproduct:** surfacing every conflict / tension / redundancy back to the HUMAN — and NEVER auto-resolving one — is the entire reason this gate exists. Canonical example: an ingest concluded the operator was repositioning AWAY from warm-authority TOWARD rough-edged; the scan surfaced the conflict → human corrected it: warm authority STAYS primary; rough-edged is ADDITIVE secondary. Auto-resolving would have written the WRONG primary type into canon.

---

#### Step 4.5 — Confirm-gate (mid-session single-artifact)

`skill → pre-fill panel (canon LIFTED OUT) → — → CANON-GATED: WAIT for explicit yes ONLY if canon candidate [human on canon]`

**CANON-GATED — this gate fires ONLY for a canon candidate.** If the item is NOT a `tier: canon-proposal`, do NOT wait: write it and show a one-line post-write receipt + the coverage note. If the item IS a canon candidate, show its lifted-out CANON CANDIDATE block (rule 3c format) + the pending-approval banner and wait for the explicit yes. A state edit or rule append is reversible and also writes without waiting.

For a canon candidate, show WHERE-FIRST (same format as SC-4, imitate `SAVE-PANEL-EXEMPLAR.md`): lead with the destination bucket + the altitude label (never bare "CANON") + a short name + one plain sentence. No path on the glance; show exact path + create/update on the human's OK, right before writing.

Nothing canonical writes until the human confirms.

---

#### Steps 5 / 5b / 6 / 6b — Write survivors (standard path)

**Step 5 — Write record:**
`skill → Write → records/ → [hook: validate_on_write nudges frontmatter · hook: guard_write_paths blocks wrong-location writes]`
Filename + frontmatter format: **`WRITE-FORMATS.md` § "Mid-session record frontmatter"** (filename `YYYY-MM-DD-{slug}.md`, slug 2–5 kebab words; fields: `id`, `title`, `record_type`, `desk`, `topic`, `created_at`, `updated_at`, `status: active`, `authority: user`, `confidence`, `tier`, `type`).
`topic:` — pick 1–3 slugs from `system/topic-vocab.md`. Use ONLY slugs that already exist there — NEVER invent one. If nothing fits, OMIT `topic:` and drop a Step 7e `flag` note.

**Step 5b — Edit state:**
`skill → Edit → state/current.md or state/open-loops.md [hook: guard_write_paths]`
Update `updated_at` in frontmatter to today.

**Step 6 — Append behavioral rule:**
`skill → Edit → CLAUDE.md files → [hook: guard_write_paths]`
Distill the rule using the exact `statement / **Why:** / **How to apply:**` structure per **`WRITE-FORMATS.md` § "Behavioral rule structure"**. Do not omit any part.

**Step 6b — Propose canon (v2 — PROPOSE, never auto-write):**
`skill → Write → records/proposals/ → vetted:false → [hook: guard_canon_write BLOCKS direct canon write]`
If this session produced a durable, generalizable lesson about a migrated project, apply two tests before proposing: (1) **Generalization test** — "Would this hold for a future DIFFERENT case as a generalizable observation, without the backstory?"; (2) **Standalone test** — "Can a completely fresh, ZERO-CONTEXT session read this line ALONE and fully understand and act on it?" Both must pass; if either fails → it is a record, not canon.

If YES → identify the RIGHT LEVEL on the canon ladder → RUN Step 4.6 (canon conflict/dedup scan) FIRST → PROPOSE to the user for a one-tap yes. Do NOT auto-write canon even in autonomous mode.

On approval: append the canon line to the target `canon.md`, and densify in place — if it makes an older line redundant or stale, merge/prune. Hard rules (auth, calendar, write-gates) are NEVER canon — they belong in hooks.

Note: the `insight-harvest` path from earlier `/save` versions is DEPRECATED. Durable lessons are now captured as TIERED, REGISTERED records by SC-1→SC-5, or as a normal Step 5 record carrying a `type:` from the register vocabulary. A generalizable rule is a canon-PROPOSAL (Step 6b) — never an inbox dump with `kind: insight`.

---

#### Step 7 — Journal entry

`skill → Write → system/journal.md → journal-FIRST (precondition that gates the brief write) [honor]`

**Always journal:** record writes (Step 5). **Never journal:** behavioral rule appends (Step 6). **Judgment call:** state edits (Step 5b) — journal only if it materially changes project chronology.

If the session-close flow ran (SC-1..SC-5), the journal SESSION CONTEXT entry was already written in SC-5 — do NOT write a second one here. The ledger row still fires.

Journal entry format (the ledger row):
- Use the slug resolved in Step 0.5 — do NOT re-infer. Never fall back to `{desk}-general` silently.
- date, desk, slug, event (one sentence — what changed AND why; not a filename echo), supersedes (path of prior artifact, or `—`, or `[partial: ...]`), → artifact-path or decision.
- Append the entry to `$DRIVE/system/journal.md` below the last line in the `## Log` section.

**SESSION CONTEXT block:** write one autonomously if any of these signals are present: multiple failed attempts, a model or architecture decision, a pivot in approach, a session spanning more than one significant phase.

---

#### Step 7b — Machine-local file log

**THIS STEP NO LONGER APPLIES — do not run it, and do not write anything for it.**

The donor logged every machine-local file change to `<notes>/state/machine-log.md` so a *second*
machine could learn what the first one had touched. Here there is one machine, and that file is
gone: `docs/data-layout.md` line 215 lists `<notes>/state/machine-log.md` against **"gone"**, for
the reason given on line 214 — *"there is one machine. The two-machine plane is not part of this
system."* The shipped `/save` skill has no Step 7b either; there is nothing to write and nowhere
to write it. A run goes straight from Step 7 to Step 7c.

Genuine unfinished work on local files is still captured — it lands in the debt ledger at
Step 7c.5, which is where it was always actionable.

---

#### Step 7c — System self-assessment

`skill → Write → system/learnings.md → log what the SYSTEM learned about ITSELF [skill]`

NOT about what the user wants to save — about how Lifehack performed. Three questions:
1. What did I miss or fail to find?
2. What did I get wrong that the user had to correct?
3. What should I do differently next time?

Categories: FRICTION / CORRECTION / PREFERENCE / WORKED.

Rules: do NOT echo what was saved in Steps 1–7 (that's content; this is system performance). Every entry must answer: "How could Lifehack improve or be better?" If nothing meaningful happened (trivial session), skip silently. Keep entries to one line each.

Append a dated block to `$DRIVE/system/learnings.md`:
```
## YYYY-MM-DD

### What did I miss?
- FRICTION: [one-liner]

### What did I get wrong?
- CORRECTION: [one-liner]

### What should I do differently?
- PREFERENCE: [one-liner]
- WORKED: [one-liner]
```

---

#### Step 7c.5 — Technical-debt sweep IN

`skill → Write → state/debt-ledger.md ## Open → sweep new debt IN [skill · hook: guard_ledger_discipline BLOCKS adding a RESOLVED/✅/DONE line to ## Open]`

Scan this session for technical debt — anything left unfinished, deferred, or working-but-not-clean. What counts: deferred work, half-done migrations, workarounds and band-aids, stubbed/broken/untested pieces, stale references after a move, anything said "we should fix / clean up later."

**One home — route UP to root.** ALL technical debt goes to `$DRIVE/state/debt-ledger.md`, even when working inside a desk. Debt is about the system working, not a desk.

For each item: append a tight one-liner with `[AREA]` tag to `$DRIVE/state/debt-ledger.md` under `## Open` (the themed section that fits) **AND STAMP the two-axis tags**: `` `type:` `` + `` `state:` `` on it.
- `type:` = `debt` · `project` · `decision` · `blocked` (or `chore` / `idea` for desk files).
- `state:` = `actionable` (default) · `waiting-external` / `waiting-date` (each REQUIRES an `` `unblock:…` `` tag) · `monitoring` · `parked`.
- Format: `- **[AREA] description** \`type:debt\` \`state:actionable\``

Dedup first (grep the file for the same item — update, don't duplicate). `guard_ledger_discipline.sh` rejects any edit that ADDS a `RESOLVED`/`✅`/`DONE` line to `## Open` — when done, DELETE the line (see 7c.6), never annotate in place. Never silently drop deferred work.

---

#### Step 7c.6 — Archive-on-close: sweep resolved items OUT

`skill → Edit/Delete → state/debt-ledger.md ## Open → DELETE resolved lines; state/open-loops.md → relocate to ## Resolved [skill · hook: guard_ledger_discipline enforces deletion-not-annotation]`

For every tracked loop / debt item THIS session demonstrably resolved:
- `$DRIVE/state/debt-ledger.md`: **DELETE the line from `## Open`**. Move a ONE-LINE dated entry to `## Cleared` only if it's history-worthy; routine closes just delete.
- `$DRIVE/state/open-loops.md`: relocate the resolved block to its `## Resolved` section.

**Do NOT just mark `✅` in place — DELETE (ledger) or relocate (open-loops).** Scope = only what THIS session confidently closed. Do NOT triage or re-verify the whole backlog. If unsure an item is fully done, leave it active.

---

#### Step 7d — Project doc sync

`skill → Edit → active project brief (## SCRATCHPAD · ## STORY LOG · ## CURRENT STATE · ## OPEN LOOPS) → brief sync; FRAME is human-only; CREATE needs the Frame-intake gate [human on CREATE]`

**JOURNAL-FIRST GATE (HARD — runs BEFORE the brief is touched):** if this save adds ANY dead-end, decision, or key number to the brief, the journal SESSION CONTEXT entry (Step 7) capturing it MUST be written FIRST. The brief is overwritten in place; the journal is the only append-only backstop. Never overwrite the brief with new precious info that isn't yet in the journal.

**v2 brief location:** resolve via Step 2.5 — `{path}/brief.md` for migrated project, else legacy path.

**CREATE vs UPDATE — the Frame-intake gate (HARD):** if the brief does NOT exist yet, you are CREATING it. The FRAME section (desired outcome · success criteria · constraints · scope edges) is HUMAN-ONLY. On CREATE: either (a) hand off to `project-manager`'s Frame-intake gate, OR (b) stub the FRAME with each slot labeled `INFERRED`, mark the brief's frame `UNCONFIRMED`, and surface the slots to the user in ONE round for confirm / correct / waive. Never write FRAME slots as if settled, and never omit the `CONFIRMED` / `INFERRED` / `WAIVED` labels. The slug-routing ASK (Step 0.5) confirms the project's IDENTITY, not its FRAME — confirming the name is not confirming the definition-of-done.

Populate the EXTRACTABLE spine autonomously (§0 LLM notice, CURRENT STATE / DECISION BOARD, STORY LOG, KEY RESOURCES, OPEN LOOPS) using the FB.1 canonical header skeleton.

**Updating an existing brief:**
- Refresh CURRENT STATE to where the work now stands.
- Move completed items future → present → past; record new decisions, results, and lessons; update next-actions and open questions; bump `updated_at`.
- COMPACTION GUARD: if this has been a long session OR compaction may have occurred, explicitly ASK: "Long session — any dead-ends or failed attempts from earlier that I should make sure are captured?"
- CONTINUOUS DEAD-END CAPTURE: scan the WHOLE session for everything tried and ruled out, and land each one in the STORY LOG + a one-line ⛔ RULED-OUT entry on the §2 DECISION BOARD.
- JOURNAL-FIRST for precious info: brief is overwritten in place, so anything whose loss would hurt — a dead-end, a decision, a key number — must ALSO be in the append-only journal.

**SECTION-CONFORMANCE (FB.2 — normalize drifted headers):** after the sync, check the brief's section HEADERS against the canonical skeleton (schema §0→§8: `## 0. 🛑 LLM NOTICE` · `## 1. FRAME` · `## 2. CURRENT STATE — the DECISION BOARD` · `## 4. STORY LOG` · `## 5. OPEN LOOPS` · `## 6. KEY RESOURCES` · `## 7. SCRATCHPAD` · `## 8. ARTIFACTS`; no §3 — Don't-Retry is retired). For any drifted header, propose a NORMALIZATION and apply it in this same brief write:
- Identify sections BY MEANING, not a brittle regex.
- HEADER + STRUCTURE ONLY — NEVER rewrite section CONTENT. The FRAME text is human-only, left byte-for-byte untouched.
- Show the proposed header changes (before→after) for the human's OK; write the `{brief}.pre-compact.bak` backup FIRST. An already-canonical brief is a SILENT no-op.

---

#### Step 7e — Deferred-placement capture (content pointers + flags ONLY)

`skill → Write → system/archivist/insight-inbox/ → deferred content/flag pointer ONLY (kind:insight is DEPRECATED) [skill]`

Handles ONLY two placement-deferral kinds (about WHERE a thing lives, not about laundering insights into rules):
- **`content`** — a POINTER to the durably-saved file for anything Step 2.7 marked AMBIGUOUS.
- **`flag`** — a note about a gap to fix later. In particular MISSING-INTENT — if this save created a NEW project / file / folder and no intent was saved for it, drop a `flag` note.

Do NOT capture `kind: insight` here, ever (DEPRECATED model). Durable lessons are captured as TIERED, REGISTERED records by SC-1→SC-5 or Step 5. A generalizable rule is a canon-PROPOSAL (Step 6b).

For each item, write ONE markdown file into `$DRIVE/system/archivist/insight-inbox/`, named `YYYY-MM-DD-<source>-<short-slug>.md`:
```yaml
---
kind: content | flag
captured: <today YYYY-MM-DD>
source_desk: <desk, or - >
source_project: <slug from Step 0.5, or - >
placement_hint: <best-guess home — a GUESS, not a decision>  # optional
pointer: <path to the durable file>                           # for kind:content
---
<one plain line — what-it-is (content) / the gap (flag) — readable by a FRESH no-context session>
```

Show the operator what was captured (lettered list, each kind noted), then move on. Default is DONE. If nothing needs deferred placement, skip silently.

---

#### Step 8 — Continuation handoff

`skill → two-pass voice-seed (DRAFT → /explain re-render) → — → continuation handoff + Wake Routine arm-first; in session-close it is the SINGLE CLOSER, absorbing the receipt + the Step 9 coverage note [skill]`

**THE HANDOFF IS THE SINGLE CLOSER in session-close mode.** The session-close ending had three overlapping artifacts — post-write receipt, this handoff, and the Step 9 coverage note — and the model historically satisfied itself with the two CHEAP ones (terse receipt + coverage boilerplate) and crushed this handoff to a thin bullet list. Fix:
- **It ABSORBS the receipt.** Its DURABLE POINTERS section IS the receipt. Do NOT also print a separate past-tense "Saved: X, Y, Z" receipt.
- **The coverage note (Step 9) is tucked at the FOOT of this handoff**, not emitted as a standalone line.
- **Never substitute the terse receipt for the full handoff.** A bullet-list "Saved: X → path" is a FAILED session-close.

(For a MID-SESSION single-artifact `/save`: the one-line receipt is still correct and sufficient. The single-closer rule is SESSION-CLOSE mode only.)

**Voice-seed — the TWO-STEP inline process (critical, not a "write it nicely" pass):**
1. **DRAFT** the handoff with every load-bearing item (dense/rough is fine; this draft is not emitted).
2. **RE-RENDER your own draft through the `/explain` lens** as a distinct second pass: keep ALL the detail, translate into plain conversational prose, re-anchor every named file/tool in a few words, lead with the answer, reorder freely for a fresh reader, drop the labeled-section scaffolding. **Emit ONLY this re-rendered version.**

The lens is `/explain`, **never `/simplify`** — a handoff's whole job is completeness; `/simplify` condenses and would cut load-bearing items. The two-step is what actually forces the voice (vs. the always-on "talk nicely" that decays).

**Open the handoff with the WAKE ROUTINE — the resuming instance's first actions:**
1. **FIRST ACTION — ARM BEFORE ANYTHING ELSE (mandatory; never offered as a choice, never deferred).** Run `/checkin <project> <plan>` as the literal FIRST move — before orienting, summarizing, planning, or building. Emit it as a copy-paste line with the real slug + the linked plan's absolute path. Arming is always correct and fully reversible. Do NOT present as an option, do NOT defer, do NOT let a `/build`, workflow, or `ultracode` launch go first. An unarmed session silently loses the plan HUD AND its scratchpad captures go nowhere.
2. **Read any huddle group(s) or scratchpad associated with this project.**
3. **PLAN STALENESS glance** — look at the linked plan; if a step is now done / obsolete / overtaken by this session, annotate the brief `⚠ stale: <step> needs update` — do NOT enter plan mode, do NOT rewrite the plan. Just flag it.
Then pick up from THE VERY NEXT ACTION.

**9-item completeness checklist** (the DRAFT must cover each; the EMITTED handoff folds them into flowing prose, NOT printed as labeled sections):
- WHERE WE ARE — desk/project + one line on the arc.
- DESIRED END-STATE (user's words) — the north star.
- WHAT JUST HAPPENED — the last loop: what was tried and the result.
- THE VERY NEXT ACTION — concrete and specific.
- WORKING THEORY / LIVE REASONING — the in-flight thinking not yet written to any file.
- RAILS — constraints + decisions locked THIS session that must hold.
- DON'T RE-TRY — dead-ends hit this session.
- PENDING ON THE HUMAN — what you're waiting on them for.
- DURABLE POINTERS — where the saved material lives for going deeper.

**End the handoff with the VOICE BLOCK — verbatim:**
> **How to talk to the operator:** he's sharp but juggling a lot of other windows and didn't watch this work happen — so write for *his* attention, not your own cover. Lead with the answer, keep it plain and conversational (not a wall of report-sections), and add a few words on what each file or tool *is* the first time you name it. Close by numbering anything that needs him, each with your own recommendation ("My call"), and don't hand him a question that's really just "can I proceed?" or one he'd have to go digging to answer. Picture a smart college freshman who hasn't been paying full attention: never dumb it down, just make it land on the first read.

---

#### Step 9 — Coverage note (mandatory, every time)

`skill → stdout → — → print coverage note verbatim [skill]`

After every `/save` completion — whether or not a journal entry was written — print this note verbatim. No shortening. No skipping. **Placement:** in SESSION-CLOSE mode it is tucked at the FOOT of the Step 8 handoff (not a standalone line after it); in mid-session mode it follows the one-line receipt. Either way it always appears.

> Journal reflects saves via /save and explicitly logged decisions only.
> In-session pivots, verbal agreements, and file changes outside /save are
> not captured. A clean-looking journal is not a complete journal.

---

### STORES TOUCHED (complete list)

Every store `/save` writes to or reads from:

| Store | Step(s) | Access |
|---|---|---|
| `$DRIVE/records/{type}/` | SC-5, Step 5 | WRITE (dated records) |
| `$DRIVE/desks/{desk}/records/{type}/` | SC-5, Step 5 (legacy) | WRITE (legacy dated records) |
| `{project-path}/records/` | SC-5, Step 5 (migrated) | WRITE (project records) |
| `$DRIVE/records/proposals/` | SC-5, Step 6b | WRITE (canon-proposals, vetted:false) |
| `$DRIVE/state/current.md` | Step 5b | EDIT |
| `$DRIVE/desks/{desk}/state/current.md` | Step 5b | EDIT |
| `$DRIVE/state/open-loops.md` | Steps 3, 5b, 7c.6 | EDIT |
| `$DRIVE/system/journal.md` | SC-5, Steps 7, 7d | APPEND (journal-first precondition) |
| `$DRIVE/system/learnings.md` | Step 7c | APPEND |
| `$DRIVE/state/debt-ledger.md` | Steps 7c.5, 7c.6 | EDIT (## Open only; deletion-only for resolved) |
| `~/lifehack-brain/desks/{desk}/CLAUDE.md` | Step 6 | EDIT (behavioral rules) |
| `Lifehack/CLAUDE.md` (Drive copy) | Step 6 (cross-desk rules) | EDIT |
| Active project brief (`brief.md` or `state/briefs/{slug}.md`) | SC-4, Step 7d | EDIT (## SCRATCHPAD, ## STORY LOG, ## CURRENT STATE, ## OPEN LOOPS; FRAME is read-only) |
| `{brief}.pad-archive.md` | Step 13a (compaction) | APPEND (archive-only, never truncated) |
| `{brief}.pre-compact.bak` | Step 7d FB.2 | WRITE (header-normalization backup) |
| `$DRIVE/system/archivist/insight-inbox/` | Step 7e | WRITE (content/flag pointers only) |
| `$DRIVE/system/project-registry.md` | Step 0.5 | READ (slug→path resolution); WRITE on new project registration |
| `~/.claude/run/pm/arm-events.log` | Step 0.4 | READ (recovery logbook) |
| Canon files (`{path}/canon.md`) | Step 6b (read); Step 4.6 (read); NEVER direct write — guard-blocked | READ for scan; WRITE only via a confirmed proposal path |
| `/tmp/save-extract-<date>.md` | SC-1 | WRITE (temp working file; survives context compaction) |

---

### GATES AND ENFORCEMENT (the honest map)

Every gate `/save` operates, with its real enforcement strength.

**Four hard hook-enforced walls:**

1. **`guard_write_paths.sh`** (PreToolUse Write|Edit) `[hook]` — the residency wall: blocks any write outside the Drive spine / approved `~/.claude/` paths; fails CLOSED on unparseable input. Fires on ALL of `/save`'s stores — the reason a `/save` write can't silently land in `/tmp` or the clone.

2. **`guard_canon_write.sh`** (PreToolUse) `[hook]` — blocks any Write/Edit to `**/canon/**` lacking `authority:user` (or fast-stale). Canon can't be silently written. This is a live wall — the proposed-then-write flow exists because the WRITE is already walled.

3. **`guard_ledger_discipline.sh`** (PreToolUse) `[hook]` — blocks adding a RESOLVED/✅/DONE line to a ledger's `## Open`. Forces deletion-not-annotation discipline on the debt ledger.

4. **`scratch_capture_gate.sh`** (Stop hook) `[hook]` — fires ONCE per ~100k-token bucket when an active pad exists, emitting a single `decision:block` with the captured-lines diff; forces the model to surface a receipt. The PROMPT is hook-enforced; the CAPTURE CONTENT itself is honor-system (the hook can't verify what was actually written to the pad).

**Two UserPromptSubmit hooks (ambient, fire every turn):**

5. **`pm_persist.sh`** (UserPromptSubmit) `[hook]` — refreshes TTLs and injects the active brief and flag reminders into every turn. This is what makes the brief "auto-load every turn."

6. **`save_routing_hint.sh`** (UserPromptSubmit) `[hook]` — intercepts "save this" / "remember this" natural-language triggers and routes them to the scratchpad or forces an ASK. Also injects the CLAUDE.md save-routing rule as an always-loaded backstop.

**One PostToolUse advisory pair:**

7. **`validate_on_write.sh`** (PostToolUse) `[hook]` — advisory nudge on frontmatter completeness; non-blocking, surfaces to the human.

8. `nudge_flow_drift.sh` — PostToolUse Write|Edit advisory: fires after any Write/Edit and checks whether the written file appears in an organism element's generated_from; if so, prints a one-line stderr nudge to re-check that element. NEVER fires on Bash — does NOT trigger on pad_archive.py; its match is CONTENT-dependent (a mapped file), not /save-specific. `observability_logger.sh` — PostToolUse * (all tools): fires on EVERY tool call unconditionally, logging one JSON line per call to /tmp/lifehack-observability-buffer.jsonl. It logs pad_archive.py only because it logs everything — NO /save-specific relationship. Neither hook targets /save; their presence is incidental/universal.

**Mandatory scripts (skill-level, not hooks):**

9. **`pm_flag_recover.py`** (Step 0.4) `[skill]` — mandatory run when Step 0 returns `none`; deterministic; never optional.

10. **`canon_conflict_scan.py`** (Step 4.6) `[skill]` — mandatory run before any canon-bound write or proposal; exits non-zero if canon is unreadable (fail-closed).

11. **`pad_archive.py archive + verify`** (Step 13a) `[skill]` — mandatory call before any scratchpad clear; fail-closed receipt-gate.

**Honor-system (prose instruction only; no hook enforces the choice):**

- **Journal-first** (Steps 7, 7d, 13d) `[honor]` — the instruction to write to `system/journal.md` before/as the brief is rewritten. No hook verifies the write actually happened first.
- **Propose-then-pause CHOICE** `[honor]` — the model choosing to route a canon candidate to `records/proposals/` and wait, rather than attempt a write (which would be hook-blocked anyway). The WRITE is already walled; the residual honor component is the model's routing choice. This is the "PARTIAL" in the maturity label.
- **Brief compaction GRADUATE + self-healing diff** (Steps 13c, 13f) `[honor]` — model judgment for classification; the safety is already banked in the archive receipt.
- **FRAME-untouched** (compaction, Step 7d) `[honor]` — backed by the always-injected LLM NOTICE in the brief (§0), no mechanical wall.
- **Register-preservation** (SC-3 → SC-5) `[honor]` — no hook tracks that a `possibility` wasn't promoted to `decision` downstream.
- **Transcript-anchor** (SC-1c) `[honor]` — no hook verifies items are actually sourced from the transcript.
- **Snapshot shelf-life respect** (SC-2, SC-3) `[honor]` — no hook blocks use of an expired snapshot.
- **Step 8 two-pass voice-seed** `[honor]` — no hook verifies the DRAFT→re-render actually happened as two passes.
- **Independent 2nd-pass subagent** (Step 13g) `[honor]` — model-executed; no hook forces the spawn or verifies a subagent ran vs. the main session doing it inline.

---

### EDGE CASES

Every known edge case and how `/save` handles it:

1. **PM-flag drop recovery — the three branches:** NONE output → visible one-liner at close (not a blocking prompt); CLEAR → respect the stop, proceed as `none`; ARM with dropped flag → surface for one-tap confirm before re-arming. Never auto-resurrect a deliberately-cleared flag.

2. **No project armed + "save this" natural language** → `save_routing_hint.sh` forces an ASK before any `/save` flow runs. The question: "standalone scratchpad, or which project's brief?" Never guess.

3. **No project armed + explicit `/save`** → runs the full curation to a standalone destination. Step 7d fires only if a brief happens to exist; if not, a visible one-liner surfaces at close.

4. **Mixed canon batch (canon candidate + reversible items)** → the presence of a canon candidate pauses the WHOLE panel. Do not split into partial auto-write plus a separate canon gate. On blanket approval ("save it" / "go"), all items confirmed at their pre-filled placement.

5. **Blanket approval** ("save it" / "just /save" / "go" / approve-all) → confirms every pre-filled item at its placement, including canon. Do NOT re-render the panel or re-ask per-item confirmation you already hold.

6. **Trivial session** (a single quick lookup, no decisions, no dead-ends) → skip SC-1's transcript pull; surface explicitly that nothing warrants persisting; skip the rest of the session-close flow.

7. **Compaction ABORT (no receipt = no clear)** → prepend `> ⚠ COMPACTION ABORTED {ts} — archive not confirmed; pad left intact` to `## SCRATCHPAD`, surface to the user. Never clear the pad without a fresh RECEIPT from `pad_archive.py`.

8. **Transcript not found** (empty `$TRANSCRIPT`) → fall back to context-window pull AND note the fallback in the journal entry so the lossy pass is visible.

9. **`pm_flag.sh` error on Step 0** → ignore silently and proceed with normal `/save`. The flag must never block a save.

10. **Mid-session flag inconsistency** (flag set but session content looks inconsistent with it) → ASK: "The active project is X, but this session looks like Y — route to Y, split, or stay on X?" Never silently route to the wrong project.

11. **Multi-project session** → segment + route each, or ask which. Never force one slug on multi-project work.

12. **`topic:` nothing-fits** → OMIT `topic:` and drop a Step 7e `flag` note. Never invent a topic slug not in `system/topic-vocab.md`.

13. **`type: rule` auto-assign block** → the model NEVER assigns this register; only the human elevates to rule at the review gate. Even after human elevation it writes as a canon-PROPOSAL (`vetted: false`).

14. **Snapshot past shelf-life** → after expiry the value is UNKNOWN; re-pull, never carry forward. No auto-promoting a snapshot past its shelf-life.

15. **New project: identity vs frame distinction** → Step 0.5 registering a new slug is IDENTITY only, not the FRAME. A new brief's FRAME must go through the Frame-intake gate (Step 7d CREATE block). Never write FRAME slots as settled fact on a guess; label each `CONFIRMED` / `INFERRED` / `WAIVED`.

16. **CANON CANDIDATE in SC-4 with no-canon path all resolved** → go straight to SC-5; emit the single Step 8 closer (absorbs the receipt + coverage note at its foot). Do NOT print a separate standalone receipt.

17. **History-worthy close vs routine close on debt-ledger** → routine close = delete the line from `## Open` (no `## Cleared` entry). History-worthy close = move a ONE-LINE dated entry to `## Cleared`. Decide per item; bias toward delete.

18. **Session-close compaction with a long session** → the COMPACTION GUARD in Step 7d fires: explicitly ASK the user whether any dead-ends or failed attempts from earlier should be captured. Do not assume the scan is complete.

---

### HARD PROHIBITIONS

What `/save` never does, under any circumstances (from SKILL.md "What never happens"):

- No write to `~/.claude/projects/*/memory/` — never, under any circumstances.
- No silent slug commit — never write under `{desk}-general` (or any guessed slug) unless Step 0.5 resolved it or the user explicitly chose it.
- No `vetted: true` on any record — machine proposes, human approves only.
- No overwriting a brief with new dead-ends/decisions before the journal entry is written (journal-first gate, Step 7d).
- No guessing when desk or type is genuinely unclear.
- No pasting full prose essays into CLAUDE.md.
- No writing a behavioral rule without `Why:` and `How to apply:` lines.
- No writing a record without checking for an existing file at the destination first (dedup check).
- No journal entry for behavioral rule appends.
- No skipping or shortening the coverage note.
- No system self-assessment entries that just duplicate what was saved — it must be about system performance.
- No silently dropping deferred work — technical debt created or discovered this session must land in `$DRIVE/state/debt-ledger.md`.
- No autonomously authored FRAME on a NEW brief — brief CREATE runs the Frame-intake gate; FRAME slots are written `CONFIRMED`/`INFERRED`/`WAIVED`, never as settled fact on a guess.
- No routing directly to Cal — `/save` feeds the journal; `cal-diary-capture.py` reads the journal.
- No register collapse — a `possibility` stays a possibility, a `suggestion` stays a suggestion, a `pros-cons` is preserved as the full weighing (never collapsed to the winning side); registers are never promoted by the machine.
- No auto-assigning `type: rule` — only the human elevates to rule; the machine NEVER assigns this register; even after human elevation it writes as a canon-PROPOSAL (`vetted: false`), never `vetted: true`; `decision` ≠ `rule`.
- No writing an item without a transcript anchor — items from SC-1 that cannot be anchored to something said or done in the transcript are not written (Step SC-1c).
- No auto-promoting a snapshot past its shelf-life — after expiry the value is UNKNOWN; re-pull, never carry forward.
- No writing a CANON candidate before the confirm-gate response is received.
- No skipping the journal when a session had real findings — the journal is the mandatory transit point for the Cal pipeline.
- No `kind: insight` capture in Step 7e (DEPRECATED model — durable lessons go through SC-1→SC-5 or Step 5/6b).
- No abbreviated deep-mode outline — even in deep mode, per-record outlines are EXPAND-not-compress; never a one-liner.

---

### INTENT / CURRENT-VS-TARGET

**BY DESIGN (the audit's biggest correction — `identity.md` Divergence-1):** manual `/save` IS the human-judgment gate for memory (invoke → review → judge what enters). The canon pause is a deliberate HITL seam, NOT a gap. Non-canon saves are already fully autonomous.

**Current state → PARTIAL, for a precise reason:**
- The canon WRITE is already a live wall: `guard_canon_write.sh` PreToolUse BLOCKS any Write/Edit to `**/canon/**` lacking `authority:user` — canon can't be silently written.
- The debt-ledger IS hook-disciplined (`guard_ledger_discipline.sh`).
- What remains `[honor]` is: **journal-first** (Step 7) + the **propose-then-pause CHOICE** (the model routing a canon candidate to `records/proposals/` and waiting, rather than attempting a blocked write). Mixed → **PARTIAL** (not "canon unprotected" — the canon write is walled; the residual is behavioral).

**TARGET:**
1. **Harden the propose-then-pause CHOICE** — the WRITE is already walled; the residual question is whether the model reliably PROPOSES vs. never-attempts (Phase-5 verify/strengthen, not build).
2. **Harden the `pad_archive.py` receipt-gate** — add a hook (a PostToolUse on `pad_archive.py` calls, or a PreToolUse on an Edit that clears a brief's `## SCRATCHPAD`) that verifies a FRESH receipt exists before the pad can be cleared. Today the receipt-gate is fail-closed *inside* `pad_archive.py` (Step 13a), but nothing outside it stops a clear that never called the tool. ⚠ **RE-HOMED HERE 2026-08-03 (T11.14):** this target lived in `elements/read.md`, which owns `/checkin`. When compaction moved to `/save`-only, an agent DELETED it there as out-of-element rather than moving it — correct diagnosis, wrong action. It is restored here because `/save` now solely owns the surface it describes. *(Caught by the T11.14 verification pass, not by the agent's own report — a target removed for a good reason is still a silent demotion if nothing catches it.)*
3. **`save_classify.py`** (D-2) — ~16 of 22 steps are deterministic and could be pre-classified in code; LLM/human confirm ONLY at the judgment boundary. The human confirm-gate STAYS. KISS: never automate the human out.

**Known SKILL.md defects (tracked separately):**
- `allowed-tools` omits Bash, though steps call it (the `pad_archive.py` call needs it — pinned narrow exception).
- `WRITE-FORMATS.md § Canon-proposal` frontmatter shows `tier: dated-record` — should read `tier: canon-proposal` to match the tier name used everywhere else (a WRITE-FORMATS.md defect).
- "spawn subagent" instruction in Step 13g is structurally advisory (a skill can't mechanically force a spawn; the main session executes the audit inline as a fallback; no hook verifies a subagent ran).
- CANON-GATED PAUSE is restated approximately 3× across SKILL.md (rule accretion — lightly confusing on a cold read).
- `type` + `state` stamps on debt-ledger entries are not mechanically enforced (honor-system; `guard_ledger_discipline.sh` guards against `RESOLVED` lines, not against missing stamps).

**pm_flag blast-radius note:** `pm_flag.sh` is an in-degree-17 hub — it is cited or called by pm_persist.sh, save_routing_hint.sh, pm_flag_recover.py, `/checkin`, `/save`, `project-manager`, and others. Changes to its API or TTL behavior propagate to all of them. Review impact across that surface before touching it.

---

### INTEROP SEAMS (shared-state edges to other elements — the organism view)

**1. Brief compaction engine — `/save`'s exclusive subroutine (formerly shared with `/checkin`).**
The 8-step brief compaction procedure (Steps 13a..13h) is invoked SOLELY by `/save` (SC-4 sub-step), at session-close, running `pad_archive.py` against `{brief}.pad-archive.md`. Compaction was removed from `/checkin` entirely (it was firing on every reorient, including a cold-pickup session launch, and clearing a brief's orientation material before the operator had read it) — `/checkin` now only harvests notes into the same `## SCRATCHPAD` and appends confirmed decisions to the Story Log. Canonical definition: `system/schemas/project-doc-schema.md` → "BRIEF COMPACTION"; a change there now changes only `/save`.

**2. Brief ⇄ `project-manager` + `/checkin`.**
All three read/write the active brief's `## SCRATCHPAD` / `## STORY LOG` / `## CURRENT STATE`. `pm_persist.sh` injects the brief every turn. The FRAME is human-only across all of them.

**3. `records/proposals/` ⇄ the Archivist.**
Canon candidates `/save` writes here (`vetted:false`) are the Archivist's inbound queue for later human-gated promotion. The Archivist reads and acts on them; `/save` only writes them.

**4. `system/journal.md` ⇄ every write element.**
The append-only journal is the shared backstop; journal-first is a precondition across `/save`, `/checkin`, and `project-manager`. Additionally: `cal-diary-capture.py` reads `system/journal.md` to populate the Cal pipeline — this is WHY `/save` must never write to Cal directly (no direct-Cal prohibition). The journal is the ONLY transit point for the Cal pipeline.

**5. `scratch_capture_gate.sh` ⇄ SC-4 F5.6 (complementary capture pipeline).**
`scratch_capture_gate.sh` fires autonomously on the Stop hook (once per ~100k-token bucket) and pushes interim captures to the active pad. SC-4 F5.6 then runs the FINAL DELTA-CAPTURE at session-close, picking up anything the gate missed since its last fire. They are complementary, not redundant: the gate is continuous; F5.6 is the closing sweep.

**6. `state/debt-ledger.md` ⇄ Backlog groomer.**
`/save` Steps 7c.5 and 7c.6 write the `type:` + `state:` stamps onto every debt entry. The Backlog organ's groomer runs ~0-LLM in steady state by reading those stamps — it can classify and triage entries without invoking an LLM. The stamps are the interface; `/save` is the writer; the groomer is the consumer. Correctness of the stamps is honor-system.

**7. `plan_flag.sh` ⇄ pm_persist ⇄ `/save` Step 8 handoff.**
`plan_flag.sh` arms the linked plan for a project; `pm_persist.sh` injects both the brief and the plan path every turn; Step 8's Wake Routine emits the `/checkin <project> <plan>` copy-paste line using the plan's absolute path. The three compose to ensure the next session arms both flags in one paste. If `plan_flag.sh` is broken or the plan path is stale, the Step 8 handoff emits a stale path — the PLAN STALENESS glance in the Wake Routine is the catch.

**8. `system/project-registry.md` ⇄ all project-aware skills.**
`/save` (Step 0.5) reads the registry to resolve slug→folder path (the `{path}` field in each row). Every project-aware skill (`/read`, `/checkin`, `project-manager`, the Archivist) also keys off the same registry. A slug registered here is the identity that all skills share. A slug NOT registered causes Step 0.5 to ASK and register before the first save.

**9. `canon_conflict_scan.py` scope must match `/read`'s lazy-canon ladder.**
Step 4.6 scans the canon ALONG THE BRANCH (target canon + siblings up the ladder). `/read`'s lazy-canon loads canon along the same branch when opening a file. If the scan scope is narrower than `/read`'s load scope, a conflict visible in a `/read` session won't be caught at save time. These two must stay in sync — tighten the scan's `--canon-root` to cover the full ladder the target file sits in.

**10. Compaction cadence — single-trigger now (the former /checkin trigger-asymmetry is retired).**
`/save` is the only path that fires compaction, once per session-close. A session that runs `/save` more than once (e.g., two mid-session artifact saves plus a final session-close) will compact repeatedly — each time appending to `{brief}.pad-archive.md` and incrementing the compaction counter. This is correct and expected (idempotent for unchanged pads); the `pad_archive.py verify` step catches any chain breaks.

---

## AUTO-COMPUTED   (machine-only — hand-set at authoring; the F1.5 checker will own this once built)

- **maturity_label:** PARTIAL
- **check_detail:** LIVE hooks fire on this element — `guard_canon_write` (blocks non-`authority:user` canon writes, PreToolUse) · `guard_write_paths` (residency wall, PreToolUse, all stores) · `guard_ledger_discipline` (debt-ledger deletion discipline, PreToolUse) · `scratch_capture_gate` Stop (hard-bounce, ~100k-token bucket) · `pm_persist` + `save_routing_hint` (UserPromptSubmit, every turn) · `validate_on_write` (advisory, PostToolUse) · `nudge_flow_drift` (PostToolUse Write|Edit; fires only when the written file is in an element's generated_from — NOT on Bash) + `observability_logger` (PostToolUse *, logs every tool call; no /save-specific relationship) — plus mandatory scripts (`pm_flag_recover.py`, `canon_conflict_scan.py`, `pad_archive.py archive + verify`). What is honor-system: **journal-first** (Steps 7 / 7d / 13d) + the **propose-then-pause CHOICE** (model routing canon candidate to `records/proposals/` and waiting — the write is already walled, the choice is behavioral) + register-preservation + transcript-anchor + snapshot-shelf-life + Step 8 two-pass voice-seed + Step 13g independent 2nd-pass subagent. Mixed (significant honor-system surface alongside strong hook coverage) ⇒ **PARTIAL**. Not "canon unprotected" — the canon write is hook-walled; the residual is behavioral routing. Honest.
