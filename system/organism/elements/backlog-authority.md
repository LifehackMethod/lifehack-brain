---
element: backlog-authority
title: "backlog-authority — element detail (ground/base altitude)"
subsystem: backlog
altitude: base
record_type: organism-element
maturity_label: PARTIAL·gap [provisional]
gap_disposition: by-design
gap_disposition_note: "ruled 2026-07-28 at class level — the supervised drain half is UNBUILT rather than failing open; stamp correctness is C2 honor-caller, accepted"
generated_from:
  - system/schemas/backlog-entry-schema.md (v1.0)
  - system/tools/backlog_groom.py
  - system/tools/backlog-health.py
  - system/tools/backlog-health-run.sh
  - system/hooks/guard_ledger_discipline.sh
  - system/reference/settings.json (line 171 — guard_ledger_discipline PreToolUse registration)
  - system/pulse-config.md (line 299 — backlog-health Pulse slot)
  - state/projects/infrastructure/backlog-authority/brief.md
  - system/schemas/backlog-entry-schema.md
  - state/status/backlog.json (live tile, last_run 2026-07-23T19:19:29)
created_at: 2026-07-24
updated_at: 2026-07-24
status: draft
authority: user
---

# backlog-authority — element detail

> **Altitude = BASE (ground / street view).** Full mechanics + honest enforcement map + all interop seams.
> The MIDDLE index (`system/organism/manual.md`) carries only a one-line pointer here; the TIP
> (`CLAUDE.md` schematic) shows only its box + arrows; the **live artifacts** (`system/tools/backlog_groom.py`,
> `system/tools/backlog-health.py`) are the fourth level — the
> executable runtime ground truth. This entry is the UNDERSTANDING layer.
>
> **LADDER: ELEMENT (full mechanics). up → manual#backlog-authority ; ground truth → system/tools/backlog_groom.py + backlog-health.py**
>
> **One-line:** reads the typed system backlog (~0-LLM in steady state) and emits an honest DECOMPOSED
> count — `actionable_debt` (type:debt AND state:actionable) — to the Backlog dashboard tile; proposes
> grooming actions but never executes them.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[script]` (mandatory script) · `[honor]` (prose
> instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause).
>
> **⛔ NOT HERE — the donor paths this element names that do not exist in this repository, and are not
> owed.** `state/debt-ledger.md` and `state/open-loops.md` are the reader's own files under their
> gitignored notes root, never committed to this repository. `state/status/backlog.json` is the tile
> `backlog-health.py` writes under that same notes root — runtime-generated, created on first run,
> never committed. A later line in this element quotes the literal annotation strings the ledger guard
> blocks; that is the guard's vocabulary being described, not a claim that any of these files are here.

---

## AUTHORED   (human-only)

### THE TWO-AXIS MODEL (the conceptual foundation)

`state/debt-ledger.md` and every desk `open-loops.md` carry backlog items. The
Backlog Authority makes these machine-readable by imposing TWO orthogonal axes —
**`type`** and **`state`** — as inline backtick tags appended to each bullet.

**The two axes (schema_version: "1.0", frozen 2026-06-19):**

| Axis | Field | Enum | Source |
|------|-------|------|--------|
| type | `type:` | `debt` · `project` · `decision` · `blocked` · `chore` · `idea` | `backlog-entry-schema.md` §Fields |
| state | `state:` | `actionable` · `waiting-external` · `waiting-date` · `monitoring` · `parked` · `done` | `backlog-entry-schema.md` §state enum |

**Why two axes kills the "95-scare" (the founding problem):** an undifferentiated
aggregate of all bullets in all open-loops files read as "95 broken things." With
the two-axis stamp, the query `type:debt AND state:actionable` returns the honest
"what's actually broken" number. Everything else (projects, blocked items, chore
backlogs, parked ideas) decomposes separately and is explicitly NOT counted as broken.
The headline number is `actionable_debt` — never the aggregate.

**`parked` is a STATE not a type.** Items in the ledger's `## Parked` section carry
`type:project` (or `type:decision`) with `state:parked`. This is enforced by the
schema; the groomer's section map handles it.

**`done` is transient.** Used by the groomer's done-detection pass, then the line is
DELETED (ledger discipline). A `done` line that persists is itself a grooming defect.

**Optional fields** (stamp when known):
- `unblock:<condition>` — REQUIRED when `state:waiting-external` or `state:waiting-date`
- `last_touched:YYYY-MM-DD` — the groomer's staleness signal for queue desks
- `done_when:<condition>` — enables deterministic done-detection without LLM re-classification
- `owner:<desk-id or user>` — which session absorbs this item in-context

---

### SOURCES (what the groomer reads)

Three distinct input sources, all read-only:

1. **`$DRIVE/state/debt-ledger.md`** — the root typed ledger. Section membership IS the
   default `type` discriminator (the groomer's `SECTION_MAP` at `backlog_groom.py` lines
   31–38 maps each `## ` header to a `(type, default-state)` pair). Inline `type:`/`state:`
   tags override section defaults. Skip sections: "Discipline", "type model", "Routed to
   desks", "Cleared" — never counted as backlog items.

2. **`$DRIVE/desks/{desk}/state/open-loops.md`** — each desk's chore/idea backlog,
   enumerated from `system/desk-registry.yaml` via `backlog_mode` field, NOT a hardcoded
   list (`backlog_groom.py` line 234). Path comes from the registry's `open_loops_path`
   field verbatim (never derived from `desk_id`). Two desk modes:
   - **`register`** (cal, deryl/books) — waiting items are NOT flagged stale (externally-blocked
     by design; staleness is normal in these desks).
   - **`queue`** (clair, emily, marc, sentinel, dobby) — waiting items ARE flagged as
     stale-suspects if `last_touched` exceeds threshold.

3. **`$DRIVE/state/open-loops.md`** — the legacy "swamp." Counted SEPARATELY as
   `swamp_pending`; deliberately NOT folded into `actionable_debt` (conflating it is
   exactly the disease the two-axis model cures). Reported as "pending drain."

**Graceful degradation:** any parse or registry failure degrades that source to empty
and never crashes — `backlog_groom.py` lines 62–72, 103–133.

---

### THE GROOMER ENGINE (`backlog_groom.py`)

**READ-ONLY propose-never-execute.** The engine reads all three sources, builds one
report dict, and returns grooming PROPOSALS. It NEVER writes to any backlog file.
Destructive grooming (delete a done line, stamp a tag, drain the swamp) is a
SUPERVISED main-session pass that consumes the proposals.

**Entry parsing** (`_entry()`, `backlog_groom.py` lines 83–99):
- Parses one bullet line into a typed struct: `slug` · `title` · `type` · `state` ·
  `done_when` · `unblock` · `last_touched` · `tagged` (bool: has explicit inline tags?)
  · `done_marker` (body contains ✅/DONE/RESOLVED/CLEARED/COMPLETE/SHIPPED/BUILT).
- `type`/`state` from inline tags override section defaults.
- Ledger entries: section membership supplies defaults. Desk entries: default to
  `chore/actionable` (desk chores). Swamp entries: rough parse (header-level items).

**`build_report()` returns** (`backlog_groom.py` lines 225–276):
```python
{
  "generated_at": ...,
  "counts": {
      "actionable_debt": int,   # ⭐ THE headline — type:debt AND state:actionable
      "debt_total":      int,   # all debt lines (any state)
      "projects":        int,   # type:project NOT parked
      "decisions":       int,   # type:decision (any state)
      "blocked":         int,   # type:blocked
      "parked":          int,   # type:project AND state:parked
      "needs_verify":    int,   # synthetic "verify" bucket
      "desk_loops_total": int,  # sum of all desk open-loops items
      "by_desk":         dict,  # {desk_id: {count, mode, waiting}}
      "swamp_pending":   int,   # legacy open-loops items above ## Resolved
  },
  "proposals": {
      "done":    list,  # done-never-archived candidates (desk/swamp only — ledger ## Open is guard-clean)
      "dupes":   list,  # same slug in two different files (root ledger wins)
      "stale":   list,  # queue-desk waiting items flagged as stale-suspect
      "untyped": list,  # ledger entries without explicit inline type/state tags
  }
}
```

**Duplicate detection** (`_dupes()`, `backlog_groom.py` lines 200–221):
Same slug appearing across DIFFERENT FILES is the "one home per item" violation (root
ledger wins). Two distinct items in the SAME file sharing an `[AREA]` prefix are NOT
dupes. Strictly cross-file only.

**Done-never-archived:** the groomer detects `done_marker` (body says finished) in
DESK and SWAMP files. It does NOT fire on the ledger's `## Open` section because the
`guard_ledger_discipline.sh` hook structurally prevents annotated-done lines from
accumulating there — the guard makes that class of defect impossible in the ledger.

---

### THE TILE PRODUCER (`backlog-health.py`)

`backlog-health.py` calls `backlog_groom.build_report()` and emits
`$DRIVE/state/status/backlog.json` via `emit_status` (the one write-time validator).
It mutates NO backlog source file.

**Tile status logic** (`backlog-health.py` lines 53–54):
```python
needs = actionable > 0 or swamp > 0 or done_n or dupe_n
env_status = "NEEDS_REVIEW" if needs else "OK"
```
The board is `OK` only when: `actionable_debt == 0` AND `swamp_pending == 0` AND no
done-never-archived candidates AND no duplicate slugs. In practice the board is always
`NEEDS_REVIEW` until the system has zero broken items AND the swamp is drained.

**Live tile snapshot (2026-07-23T19:19:29):**
- `actionable_debt: 82` · `projects: 42` · `decisions: 24` · `blocked: 14` · `parked: 17`
- `swamp_pending: 2` · `groom: {done_candidates: 10, dupe_candidates: 6, stale_suspects: 7}`
- `desk_loops_total: 212` across 7 desks (cal/clair/deryl/dobby/emily/marc/sentinel)

**Tile schema** (emitted to `state/status/backlog.json`, schema_version 2):
`work_count` · `work_noun` · `actionable_debt` · `debt_total` · `projects` · `decisions`
· `blocked` · `parked` · `needs_verify` · `desk_loops_total` · `by_desk` · `swamp_pending`
· `groom{}` · `kpis[]` · `items[]` + standard emit_status envelope.

---

### THE RUNNER (`backlog-health-run.sh`)

**There is no wrapper runner here.** Pulse invokes the tile producer directly; no
`backlog-health-run.sh` exists in `system/tools/`, and nothing needs one — the donor's wrapper
existed to carry a lead-machine gate, and this system has one machine (`docs/data-layout.md`
line 214: *"there is one machine. The two-machine plane is not part of this system"*). There is
no machine gate, no `require_primary`, and no `state/primary-machine` marker; the tile has a
single writer because there is only ever one writer.

**Pulse slot** (`system/pulse-config.md` line 115):
```
backlog-health   | yes | 21600 | python3 "$LIFEHACK_CODE_ROOT/system/tools/backlog-health.py"
```
6-hour cadence; `stale_after_s: 43200` (12h).

---

### `guard_ledger_discipline.sh` — THE WRITE WALL

**Registered:** PreToolUse Write|Edit · `settings.json` line 171 (alongside `guard_write_paths.sh` at line 166).
**Fires on:** ALL Write/Edit tool calls; checks ONLY `state/debt-ledger.md` (non-ledger targets
exit 0 — a bug here must never block the whole edit surface).

**What it guards:** ADDING a status-annotation line (`✅` · `RESOLVED` · `CLEARED` · `FIXED`)
to the `## Open` section. Pattern: `re.compile(r"✅|\b(RESOLVED|CLEARED|FIXED)\b")` (guard
script lines 41, 55–57).

**The discipline rule:** the `## Open` section is DELETION-ONLY. To close an item:
DELETE its line. If a history note is warranted: add ONE dated line to `## Cleared`.
Never annotate in place. **Why it exists:** the debt list grew +29 items over 4 days
(2026-06-14..18) because closing annotated ✅ IN PLACE — so the list only accumulated.
The drain made `## Open` deletion-only; this guard enforces it structurally so the
growth pattern cannot recur.

**Exit-2 semantics:** the guard exits 2 (deny) and prints a JSON `{"decision":"block","reason":...}`
to stderr. The Claude Code harness interprets exit-2 as a hard block. (`guard_ledger_discipline.sh`
lines 58–65.)

**What the guard does NOT cover:**
- It does NOT parse inline `type:`/`state:` tags — adding a backtick tag to a bullet is
  new content on an existing line, which the guard passes (schema compatibility, confirmed
  `backlog-entry-schema.md` line 121–126).
- It does NOT enforce the presence of `type:`/`state:` stamps on new entries — that is
  honor-system (`/save` Step 7c.5 is the writer; stamp correctness is prose instruction only).
- It does NOT block Bash file-writes — Bash bypasses the Write|Edit hook plane (system-class
  gap, accepted by design per `guard_write_paths.sh` header 2026-07-14; NOT specific to this
  guard).

---

### HOW `/save` STAMPS ENTRIES (the write path)

The Backlog Authority is a READ-ONLY engine — it never writes. The writer is `/save`.

**`/save` Step 7c.5 — sweep IN** (`save.md` line 552–565, `elements/save.md` §Step 7c.5):
`skill → Write → state/debt-ledger.md ## Open → sweep new debt IN`
- Scans the session for technical debt: deferred work, half-done migrations, workarounds,
  stubbed/broken/untested pieces, stale references, anything deferred with "fix later."
- ALL debt goes to `$DRIVE/state/debt-ledger.md`, even when working inside a desk.
- For each item: appends a tight one-liner with `[AREA]` tag to `## Open` under the themed
  section AND STAMPS the two-axis tags: `` `type:` `` + `` `state:` ``.
- Format: `- **[AREA] description** \`type:debt\` \`state:actionable\``
- Dedup first (grep the file for the same item — update, don't duplicate).
- `guard_ledger_discipline.sh` BLOCKS any edit that adds a RESOLVED/✅/DONE line to `## Open`.

**`/save` Step 7c.6 — sweep OUT** (`elements/save.md` §Step 7c.6):
`skill → Edit/Delete → state/debt-ledger.md ## Open → DELETE resolved lines`
- For every tracked loop THIS session demonstrably resolved: DELETE the line from `## Open`.
- Move a ONE-LINE dated entry to `## Cleared` only if history-worthy; routine closes just delete.
- Do NOT mark ✅ in place — DELETE. The guard blocks annotation; deletion is the only path.
- `guard_ledger_discipline.sh` enforces the deletion-not-annotation discipline.

**Stamp correctness is honor-system.** `/save` is instructed to stamp `type:` + `state:` on
every new entry, but no hook verifies the stamps are present or correctly chosen. The groomer
treats untagged entries as `untyped` proposals (shown as forward-stamp targets in the groom
report). This is the groomer's catch for any miss.

---

### STORES TOUCHED

| Store | Access | Tool | Gate |
|-------|--------|------|------|
| `$DRIVE/state/debt-ledger.md` | READ (groomer) | `backlog_groom.py` | none (read-only) |
| `$DRIVE/state/open-loops.md` (swamp) | READ (groomer) | `backlog_groom.py` | none (read-only) |
| `$DRIVE/desks/*/state/open-loops.md` | READ (groomer) | `backlog_groom.py` | none (read-only) |
| `system/desk-registry.yaml` | READ (desk enumeration) | `backlog_groom.py` | none (read-only) |
| `$DRIVE/state/status/backlog.json` | WRITE (tile) | `backlog-health.py` via `emit_status` | none (single writer) |
| `$DRIVE/state/debt-ledger.md ## Open` | WRITE (entries) | `/save` Steps 7c.5, 7c.6 | `guard_ledger_discipline.sh` [hook] |
| `$DRIVE/state/debt-ledger.md ## Cleared` | WRITE (history notes) | `/save` Step 7c.6 | `guard_ledger_discipline.sh` [hook] |

---

### GATES AND ENFORCEMENT (the honest map)

**One hard hook-enforced wall:**

1. **`guard_ledger_discipline.sh`** (PreToolUse Write|Edit) `[hook]` — blocks ADDING a
   `✅`/`RESOLVED`/`CLEARED`/`FIXED` annotation line to `## Open` in `state/debt-ledger.md`.
   Exit-2 deny. Registered at `settings.json` line 171. Makes the "annotate-in-place growth"
   failure mode structurally impossible. (`guard_ledger_discipline.sh` lines 1–67.)

**Honor-system (prose instruction only; no hook enforces these):**

2. **Stamp correctness** `[honor]` — `/save` Step 7c.5 is instructed to stamp `type:` +
   `state:` on every new ledger entry. No hook verifies stamps are present or correctly chosen.
   Groomer's `untyped` proposal list is the catch.

3. **One-home discipline** `[honor]` — the schema declares "one home per item; root ledger
   wins over desk copies." No hook enforces cross-file dedup. The groomer's `dupes` proposals
   surface violations; a supervised session acts on them.

4. **Grooming writes (supervised drain)** `[honor]` — the groomer proposes; a human-in-the-loop
   main session executes deletions, stamp additions, and swamp drains. No autonomous execution path
   is built. The supervised drain is NOT a built tool — it is a described procedure (brief.md §6).

5. **`unblock:` field presence on waiting items** `[honor]` — the schema requires `unblock:`
   when `state:waiting-external` or `state:waiting-date`. No hook enforces this. The groomer
   flags stale queue-desk waiting items but does not validate field completeness.

6. **Desk `backlog_mode` routing** `[honor]` — the decision to NOT flag `register` desks as stale
   is enforced by the groomer's logic reading `desk-registry.yaml`, but the `backlog_mode` field
   itself is human-maintained in the registry. An incorrect `backlog_mode` silently changes staleness
   behavior.

---

### GAPS (documented fail-open conditions)

**GAP-1 — No supervised drain tool (the build's missing half).**
The brief (`backlog-authority/brief.md` §6) describes two components: (1) the groomer (BUILT) and
(2) a supervised DRAIN pass where a human reviews proposals and applies deletions/stamps. Component 2
has no built tool or structured skill — grooming proposals exist in the tile and `--propose` output,
but consuming them requires an ad-hoc main-session pass. The groomer's `done`, `dupes`, and `untyped`
proposals sit in the tile and never self-resolve. The "backlog-authority" project `status: SCOPED (not
yet built)` (brief.md line 6) reflects this: the tile is live but the drain workflow is unbuilt.
**Posture impact:** a session reading only the tile (`backlog.json`) would see 10 done-candidates and
6 dupe-candidates and have no structured path to clear them.

**GAP-2 — Stamp correctness is fully honor-system.**
`type:` + `state:` stamps on new ledger entries depend entirely on `/save`'s Step 7c.5 prose
instruction. No hook verifies stamps exist or are correctly chosen. The groomer's `untyped` count
(items without explicit tags) is the only signal. A session that skips or mis-stamps an entry silently
degrades the groomer's accuracy — the groomer falls back to section-default types, which may be wrong
if an item is in the wrong section.

**GAP-3 — Swamp drain has no built path.**
The legacy `state/open-loops.md` (the "swamp") is counted separately as `swamp_pending` and flagged
in the tile. The drain procedure (Window-4 Phase 5 per `backlog-health.py` tile summary field) has no
built skill or scheduled job. It requires a full supervised session.

**GAP-4 — `backlog_mode` in desk-registry is human-maintained with no validation.**
The groomer's staleness logic pivots on `backlog_mode: register | queue` from `system/desk-registry.yaml`.
If a new desk is added without the correct `backlog_mode`, it defaults to `queue` (the Python fallback
at `backlog_groom.py` line 234: `mode = d.get("backlog_mode") or "queue"`), which may generate false
stale-suspects for a register-mode desk.

---

### INTEROP SEAMS (organism view)

**1. `save` WRITES→ `backlog-authority`** — the primary write path.
`/save` Steps 7c.5 and 7c.6 are the SOLE structured writer for the ledger's `## Open` section.
They stamp `type:` + `state:` on every entry they write. The groomer reads these stamps to classify
~0-LLM in steady state. The stamps are the interface contract between `/save` and `backlog-authority`.
A change to the stamp format or the `type`/`state` enum requires updating BOTH. (`elements/save.md`
INTEROP seam 6; `backlog-entry-schema.md` §Groomer invariants.)

**2. `backlog-authority` FEEDS `Helm`** — the tile is the dashboard data source.
`backlog-health.py` emits to `state/status/backlog.json`; the Helm Backlog tab reads it. The tile's
`work_count`/`work_noun` (= `actionable_debt` / `"actionable debt"`) drive the Helm KPI strip.
The Helm demo (`helm/demo/fixtures/state/status/backlog.json`) carries a separate fixture copy that
can silently drift from the live tile shape. (Known gap: `[HELM-DEMO-DRIFT]` in the ledger.)

**3. `backlog-authority` READS `open-loops`** — desk open-loops as secondary backlog.
The groomer reads every desk's `open-loops.md` enumerated from `system/desk-registry.yaml`.
`open-loops` is the desk-level chore/idea backlog; the root ledger is the system-level backlog.
The groomer's `_dupes()` function enforces the "one home per item" rule by detecting cross-file
slug conflicts and proposing that the root ledger copy wins.

**4. `guard_ledger_discipline` GUARDED-BY → `save` write path.**
The guard fires on every Write/Edit tool call that targets `state/debt-ledger.md`. This means
it guards both `/save` Step 7c.5 (new entries) and Step 7c.6 (resolutions). It enforces
deletion-not-annotation on `## Open`. Registered alongside `guard_write_paths.sh` in the same
PreToolUse hook block (settings.json lines 158–175).

**5. `desk-registry` KEYS-OFF → `backlog-authority`.**
The groomer's desk enumeration reads `system/desk-registry.yaml` for `open_loops_path` and
`backlog_mode`. The registry is code-resident (not Drive). Adding a desk without the correct
registry entry silently excludes that desk's loops from the tile.

**6. `backlog-authority` COMPLEMENTS `health-authority`.**
The Health Authority (`system-health.py` + tile) answers "is the system RUNNING right?" (runtime:
jobs · hooks · guards). The Backlog Authority answers "is the system TRACKING
ITSELF right?" (backlog: typed · stale flagged · done-never-archived · cross-file dupes). Symmetric
sibling organs, two tabs, no overlap. (brief.md §3 framing.)

**7. `backlog-authority` COMPLEMENTS `archivist`.**
The Archivist curates KNOWLEDGE (insights, canon placement, knowledge drift). Backlog Authority
curates WORK TRACKING (backlog hygiene). Different data, different question. They must not be
conflated: the Archivist must not be stretched to work-hygiene, and Backlog Authority must not
touch knowledge/canon placement. (brief.md §4 explicit boundary.)

**8. `pulse-cron` TRIGGERS → `backlog-authority` tile.**
Pulse invokes `backlog-health.py` on a 6h interval (`pulse-config.md` line 115). Nothing gates
that call — one machine, one writer of the tile.

---

### INTENT / CURRENT-VS-TARGET

**BY DESIGN — propose-never-execute is the primary contract.**
The groomer surfaces defects; a supervised human-in-the-loop session acts on them. Auto-deletion
of ledger entries is deliberately out of scope (brief.md §9: "Not auto-fixing or auto-deleting
debt — it surfaces and proposes; a supervised session acts"). This is the same posture as the
Archivist: propose-never-execute.

**BY DESIGN — `~0-LLM` in steady state.**
When `/save` stamps entries correctly, the groomer classifies purely from section membership
and inline tags — no LLM call. LLM grooming (best-effort classification of legacy untagged
entries) fires only on the `untyped` residue from the pre-stamp era. This is the design
target and is currently met for all newly-written entries.

**Current state → PARTIAL, for a precise reason:**

The READ side is LIVE: the groomer (`backlog_groom.py`) + tile producer (`backlog-health.py`)
+ Pulse slot are all built, Pulse-scheduled, and the tile is
actively updating (last_run 2026-07-23T19:19:29, rc:0). `guard_ledger_discipline.sh` is live
and hook-enforced.

What keeps it PARTIAL:

1. **The supervised drain path is unbuilt** (GAP-1). The groomer proposes; there is no built
   tool or skill to consume the proposals. 10 done-candidates and 6 dupe-candidates sit in the
   live tile with no structured resolution path.

2. **Stamp correctness is fully honor-system** (GAP-2). The groomer's accuracy in steady state
   depends on `/save` stamping entries correctly, and no hook verifies this.

3. **Project status: `SCOPED (not yet built)`** (brief.md line 6) — this reflects the original
   2026-06-19 framing before the groomer was built. The groomer IS now built; the brief status
   is stale. The missing piece is the drain workflow. [UNVERIFIED — brief status was not updated
   post-build; this assessment is inferred from the live code + tile.]

**TARGET:**
1. **Build a supervised drain skill or structured session SOP** that consumes the groomer's
   `done`, `dupes`, `stale`, and `untyped` proposals and guides a human through the deletions,
   stamp additions, and home-consolidation in a single session.
2. **Close the stamp correctness gap** — either a lightweight PostToolUse advisory hook that
   checks new ledger entries for `type:`/`state:` tags, or a `save_classify.py` pre-stamp step
   in `/save` that machines the tags before writing.
3. **Drain the swamp** (`state/open-loops.md`) in a supervised session, converting items to
   typed ledger entries or archiving them.
4. **Update brief.md status** from `SCOPED (not yet built)` to reflect that the groomer and
   tile are live.

---

### EDGE CASES

1. **Registry missing `open_loops_path`** — the groomer silently skips that desk (no crash,
   no false count). `backlog_groom.py` line 235: `if not olp: continue`.

2. **PyYAML absent** — `load_registry()` catches the ImportError and returns `[]`; the groomer
   degrades to ledger-only. No crash. (`backlog_groom.py` lines 62–72.)

3. **Ledger unreadable** — `parse_ledger()` returns `[]` on any I/O failure. The tile still
   emits with zeroed counts (not a silent error). (`backlog_groom.py` lines 103–133.)

4. **Same-file duplicate slugs** — NOT flagged as dupes. The `_dupes()` function skips items
   whose `file` matches the first-seen file for that slug. Rationale: two `[DOCS]` bullets in
   the ledger are different items sharing only a prefix, not a duplicate home.

5. **`done` state in `## Open`** — the schema says `done` is transient; `guard_ledger_discipline.sh`
   blocks adding a `✅` annotation but does NOT specifically block adding `` `state:done` `` (the
   guard's regex targets `✅|\b(RESOLVED|CLEARED|FIXED)\b`, not the backtick-tag syntax). A
   `` `state:done` `` entry in `## Open` would pass the guard and then appear as a grooming
   defect in the tile's `done-never-archived` proposals.

6. **A missed run is silent until the tile goes stale** — if the Pulse tick does not fire (machine
   asleep, scheduler down), nothing writes and the old tile persists. The `stale_after_s: 43200`
   threshold is the only signal: >12h without a write and the tile reads stale on the dashboard.
   (No machine gate is involved — there is one machine.)

7. **`guard_ledger_discipline` parse failure on non-ledger targets** — the guard exits 0
   (allow) on any parse failure or non-ledger path target. A bug in the guard itself can only
   ever MISS a ledger check, never block the whole edit surface. (`guard_ledger_discipline.sh`
   header "SCOPING NOTE".)

---

### HARD PROHIBITIONS (what backlog-authority never does)

- No autonomous deletion or modification of backlog entries — propose-never-execute at all times.
- No LLM classification of already-stamped entries in steady state.
- No write to any source other than `state/status/backlog.json` (tile) from the automated path.
- No swamp drain without a supervised session — the swamp is counted separately, never auto-consumed.
- No overriding `guard_ledger_discipline.sh` — the guard is the structural backstop for the
  deletion-only discipline.
- No conflation with the Health Authority (runtime health) or the Archivist (knowledge curation).

---

## AUTO-COMPUTED   (machine-only — hand-set at authoring; the F1.5 checker will own this once built)

- **maturity_label:** PARTIAL·gap [provisional]
- **why `·gap`:** the runner is NOT in `settings.json` hooks and no supervised-drain path is built.
  *(Reason relocated here 2026-07-28 — it had been living ONLY in a trailing `#` comment on the
  frontmatter line, where any label normalisation would have silently deleted it.)*
- **check_detail:** LIVE components: `guard_ledger_discipline.sh` (PreToolUse Write|Edit, exit-2
  deny, registered `settings.json` line 171) · `backlog_groom.py` (read-only groomer, produces
  decomposed counts + proposals, ~0-LLM in steady state) · `backlog-health.py` (tile producer,
  emits `state/status/backlog.json` via `emit_status`) · `backlog-health-run.sh` (Pulse runner,
  6h cadence, primary-machine-gated) · `system/pulse-config.md` line 299 (Pulse slot registered,
  `enabled:yes`). Tile confirmed live (last_run 2026-07-23T19:19:29, rc:0). What is honor-system:
  stamp correctness on new ledger entries (`/save` Step 7c.5 prose instruction, no hook verifies
  `type:`/`state:` presence or correctness) · one-home discipline (groomer proposes, human acts) ·
  supervised drain workflow (unbuilt — GAP-1 · GAP-3). What is missing: the drain skill/SOP
  (GAP-1) + stamp-verification hook (GAP-2 target). The guard (`guard_ledger_discipline.sh`) is
  LIVE on the primary vector (annotation-in-place) with one documented bypass (GAP-5: `state:done`
  backtick-tag passes the guard's regex — no `·gap` added because the posture question is
  "does annotating ✅ in place get blocked?" and the answer is YES for that pattern; the
  `state:done` bypass is a minor edge case, not a main-path enforcement hole). Mixed (live
  guard + live tile pipeline + significant honor-system surface) ⇒ **PARTIAL**. Honest.
