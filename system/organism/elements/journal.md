---
element: journal
title: "journal — element detail (ground/base altitude)"
subsystem: memory
altitude: base
record_type: organism-element
maturity_label: PARTIAL (honor)
generated_from:
  - Lifehack/system/journal.md (header + format spec + ## Log section)
  - skills/save/SKILL.md (v3.3) Steps 7 · 7d · SC-4(iv-journal-first) · SC-5 · Step 9 coverage-note
  - skills/checkin/SKILL.md (v1.3) Step 3.6b journal-first rule
  - skills/project-manager/SKILL.md "Ongoing update rule" + "JOURNAL-FIRST" block (~lines 278–390)
  - system/tools/planning-diary-capture.py (read_journal() · JOURNAL constant · build())
  - system/tools/planning-diary-rollup.py (journal_range() · JOURNAL constant)
  - system/tools/marc-sensor.py (TRIP journal-append block lines 113–130)
  - system/tools/marc-pulse-journal.py (full file — slot-level daily append)
  - system/hooks/guard_write_paths.sh (line ~270, not 130 [corrected 2026-08-27, claim 78] — journal.md in clone block-list; live effective behavior for this path did not match "blocked" when fire-tested, claim 77 — see STORE section)
  - system/reference/settings.json (hook registrations PreToolUse Write|Edit)
  - skills/read/SKILL.md Step 0 journal-slice + gap-signal + coverage-disclaimer
  - skills/throughline/SKILL.md (journal failure-rows subagent input)
  - skills/marc-checkin/SKILL.md (marc journal-row read)
  - skills/archivist-audit/SKILL.md (journal-newer-than-brief staleness check)
created_at: 2026-07-23
updated_at: 2026-07-23
status: active
authority: user
---

# journal — element detail

> **CITATION BANNER — what this page names that is not a file in this repository** (migration note, 2026-08-15).
> The description below is the donor system as it was, and it is kept as written. Each marker records what
> happened to that file AT THIS DESTINATION; none of them changes the description.
>
> ⛔ `system/journal/YYYY-MM.md` is not a repo file and never was. It is a rotated journal segment in the
> person's own notes, created by the rotate subcommand when a month completes. The rotation section further
> down claims ✅ — that claim is TRUE about the tool, which is here; it is not true about the segment file the
> tool writes, and this banner is what corrects it.
>
> ⛔ `state/current.md` is the person's own notes too — here it is `<notes>/state/current.md`, written by
> `/save` when where-things-stand changes (`docs/data-layout.md`). Never committed to this repo.

> **Altitude = BASE (ground / street view).** The in-the-weeds detail of `system/journal.md` —
> every write trigger, every format, every step chain, every reader, every gate and its real
> enforcement, and its overlaps with the rest of the system. The MIDDLE index (`system/organism/manual.md`)
> carries only a one-line pointer here; the TIP (`CLAUDE.md` schematic) shows only its box + arrows.
>
> **LADDER: ELEMENT (full mechanics). up → manual#journal ; ground truth → the live artifact (generated_from)**
>
> **One-line:** the single append-only event log — the common backstop all write paths must hit
> before touching any mutable file, and the sole source the Cal pipeline reads for its daily diary.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory script) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause).

---

## AUTHORED   (human-only)

### STORE

**One file, two parts.**

- **Store:** `$DRIVE/system/journal.md` (the Drive spine copy — the only writable home).
- **Clone copy:** `~/lifehack-brain/system/journal.md` — **does not exist as a real file**; any
  Write/Edit tool call targeting that path is ~~BLOCKED~~ by `guard_write_paths.sh` (see GATES below).
  > **⚠ CORRECTED 2026-08-27, lb2-ops-comms.md claims 77/78 — live-tested, not blocked.** An `Edit`
  > targeting `~/lifehack-brain/system/journal.md` through `guard_write_paths.sh` returned rc=0
  > (ALLOWED), contradicting this line. `system/journal.md` IS present in the guard's block-list
  > case-statement, but at a different line than previously cited (~270, not ~130) — the pattern is in
  > the source, but the live effective behavior for this exact clone-copy path did not match "blocked"
  > when fire-tested. Treat the "does not exist as a real file" half as still true; the enforcement half
  > needs re-verification against the guard's actual match logic before relying on it.
- **The ## Log section** is the append-only event ledger. New entries are always appended below the
  last line; existing entries are NEVER edited or deleted.
- **The file header** (above `## Log`) declares the three entry types and the field rules. It is
  human-owned metadata; agent writes land only in `## Log`.

### ENTRY TYPES AND FORMAT

Three formats. No others are valid (per the file's own header).

**1. Artifact save (ledger row)**
```
{YYYY-MM-DD} | {desk} | {slug} | {event} | supersedes: {path or —} | → {artifact-path}
```
- `event` — what changed AND why; not a filename echo; readable with no other context.
- `supersedes` — path of prior artifact, `—` (new), `[partial: ...]` (part invalidated, annotation
  required), `[renamed]`, or two comma-separated paths (merge). NEVER a concept.
- `slug` — must exist in `system/project-registry.md` before use; `{desk}-general` is valid without
  a registry entry.
- The pipe characters are the parse delimiter planning-diary-capture.py keys off (`| {date} |` prefix).
  Malformed rows that don't start with the date-pipe token are silently skipped by the parser.

**2. Decision (ledger row variant)**
```
{YYYY-MM-DD} | {desk} | {slug} | {event} | supersedes: {path or —} | decision: {what was decided}
```
Same field rules as artifact save; the trailing field starts with `decision:` instead of `→`.

**3. SESSION CONTEXT block**
```
--- SESSION CONTEXT | YYYY-MM-DD | {desk} | {slug} ---
session: [what this session was trying to do — one line]
follows: [cause/effect link to the prior context, or "—" if first entry]
failed: [what was attempted and didn't work, and why — or "none"]
changed: [the delta: what's different now vs. start of session]
why: [the reasoning behind key decisions made]
state: [where things stand; what's blocked; what's next]
---
```
Write a SESSION CONTEXT entry when: something failed and shaped the outcome, an architectural
decision was made, a multi-hour session where ledger rows alone won't tell the story, or a pivot
occurred mid-session. Not for routine saves — the ledger row is sufficient for those.

The header `--- SESSION CONTEXT | {date} | {desk} | {slug} ---` is the parse token
planning-diary-capture.py uses to identify blocks: it reads the `session:` field as a one-line
description and groups the block by desk, the same way it groups ledger rows.

**Machine-appended rows (not authored by skill prose):**
- `marc-sensor.py` appends a TRIP row under the `marc` desk when a VIX regime escalates or a
  tripwire fires, using direct Python file I/O (`open(JOURNAL, "a")`). Format follows the pipe-row
  convention but delineates with `| supersedes: -` (single dash, not em-dash). LOW-confidence flag
  is embedded in the event text: `TRIP{slot}: ... (machine, LOW — run /marc-checkin to verify)`.
- `marc-pulse-journal.py` appends one compact market-level line per slot/day (open/close) under the
  `marc` desk. Write-once-per-slot-per-day dedup: it checks for an existing row for that date +
  slot before writing. Failure is non-fatal (exception caught; does not break the health run).

---

### TRIGGERS AND WRITE PATHS

Five write paths trigger journal appends. The first four are agent-authored (LLM + tool plane); the
fifth is mechanical (Python file I/O outside the tool plane entirely).

---

#### PATH A — /save Step 7 (mid-session, standard record write)

`save-skill → [Step 7 logic: "Always journal: record writes"] → Edit → $DRIVE/system/journal.md → [hook: guard_write_paths fires PreToolUse; allows Drive path] [skill]`

**When it fires:** after every record write (Step 5), and after state edits (Step 5b) when the edit
materially changes project chronology (model judgment). Never fires after a behavioral-rule append
(Step 6).

**Format:** a ledger row (artifact save or decision type). Uses the slug resolved at Step 0.5 — does
NOT re-infer. Falls back to a visible one-liner (not a blocking prompt) if no armed project exists.

**Journal-first gate (honor):** the skill states the journal entry must be written BEFORE/AS the
brief is touched (Step 7d JOURNAL-FIRST GATE). No PreToolUse hook enforces the ordering — if the
skill skips the journal write, the brief write proceeds. The gate is `[honor]` only.

**In review mode:** the entry is shown to the human and awaits explicit approval before being
written. In default mode: autonomous append (one-line post-write receipt).

**SESSION CONTEXT auto-trigger:** the skill autonomously writes a SESSION CONTEXT block (not just a
ledger row) when any of these signals are present: multiple failed attempts, a model or architecture
decision, a pivot in approach, or a session spanning more than one significant phase.

---

#### PATH B — /save SC-5 (session-close write-only-survivors)

`save-skill → [SC-1..SC-4 curation] → [SC-4 CANON-GATED confirm-gate (wait only if canon candidate)] → SC-5 Edit → $DRIVE/system/journal.md → SESSION CONTEXT entry appended under ## Log [skill · hook: guard_write_paths fires PreToolUse]`

**When it fires:** session-close mode only (bare `/save`, or argument contains "session" / "close" /
"end" / "wrap", or noticeable volume of session findings). The full SC-1..SC-5 curation flow runs
BEFORE the standard Steps 7–9.

**SC-1 transcript pull:** the session transcript (`.jsonl` file at
`~/.claude/projects/*/$CLAUDE_CODE_SESSION_ID.jsonl`) is extracted into a working temp file
(`/tmp/save-extract-<date>.md`) so it survives context compaction. If `$TRANSCRIPT` is empty, falls
back to the context-window pull and notes the fallback in the journal entry so the lossy pass is
visible.

**SC-4 confirm gate:** the write is autonomous unless a `tier: canon-proposal` item is present in
the survivors. On canon candidate: render the pre-fill panel + pending-approval banner and WAIT for
an explicit human yes before SC-5 runs.

**SC-5 journal write:** appends a SESSION CONTEXT block. **Format divergence — load-bearing gap:**
`WRITE-FORMATS.md § "Journal SESSION CONTEXT entry"` specifies `## SESSION CONTEXT — {YYYY-MM-DD} |
{desk or project slug}` (a markdown heading) with fields `Session / Follows / Failed-changed / Key
findings / End state / Missteps`. But `journal.md`'s own canonical format (the source of truth and
the parse target) uses `--- SESSION CONTEXT | YYYY-MM-DD | {desk} | {slug} ---` (a pipe-delimited
fence) with fields `session / follows / failed / changed / why / state`. These are two distinct
formats. `planning-diary-capture.py` keys its block parser off the `--- SESSION CONTEXT |` token — a
`## SESSION CONTEXT —` heading would be silently invisible to the Cal pipeline (the parser's
`startswith("--- SESSION CONTEXT |")` check fails on the markdown heading form). Any SC-5 entry
written in the WRITE-FORMATS.md style is a pipeline miss: it lands in the journal file but
contributes nothing to the diary's Machine Recap. The field names also differ (`why` and `state`
exist in the journal's canonical format; they have no equivalents in WRITE-FORMATS.md's template).
**✅ THIS DISCREPANCY IS RESOLVED — 2026-08-02, commit `f414643`; the ledger entry `[CAL-DIARY-FORMAT-DRIFT]` is CLEARED.** The fix was made in the CONSUMER, deliberately: `planning-diary-capture.py` now accepts the `## SESSION CONTEXT — {date}` heading form alongside the original `--- SESSION CONTEXT |` delimiter, plus dashed `- {date} |` entry rows and the bold `**DECISION|BUILD**` lines. **The journal was NOT changed** — it is append-only history and the reader adapts to the data, never the reverse; and only the reader could repair the ~2 months of entries already written. Measured old-vs-new across all 108 journal dates: reach **385 → 1,263 records**, zero regressions; the existing diary was then backfilled (Jul 1 → Aug 2, 28 days, 72 → 352 records). Locked by `system/tools/test_planning_diary_capture.py` (25 cases, watched failing before trusted green). *(The field-name divergence noted above — `why` / `state` having no WRITE-FORMATS.md equivalent — is a SEPARATE and still-open point; the format-drift fix did not address it.)* If the SC-4 debt-clear was skipped, the entry
appends: `**Debt-check:** skipped at close — debt items from this session may be uncaptured.`

**Ordering note (no double-write):** if the session-close flow ran (SC-1..SC-5), the journal SESSION
CONTEXT entry was already written in SC-5. The standard Step 7 does NOT write a second one; the
ledger row still fires.

---

#### PATH C — /checkin Step 3.6b (confirmed decision / outcome)

`checkin-skill → [Step 3.6b "Journal-first (HARD)"] → Edit → $DRIVE/system/journal.md (append ledger row) → Edit → brief ## STORY LOG (append Story Log entry) [skill · honor for ordering · hook: guard_write_paths fires on both writes]`

**When it fires:** invoked by the user ("/checkin", "where are we", "re-orient", etc.) when a
confirmed decision, settled outcome, or ruled-out path is captured mid-session.

**Ordering rule:** the skill prose states the journal write comes "before/as" the brief write. The
HARD label in the SKILL.md text means the skill treats this as non-negotiable. No PreToolUse hook
enforces the ordering — if the skill skips the journal write first, the brief write goes through.
Ordering is `[honor]`.

**What gets written:** a ledger row (artifact save or decision type). The brief then receives an
append to `## STORY LOG` in the same update.

**Compaction interaction:** checkin's Step 3.6 does NOT fire compaction — that was removed from
`/checkin` (it was clearing a brief's orientation material before a cold-pickup operator had read
it). Only `/save`'s SC-4 fires the AUTOMATIC + LOSSLESS COMPACTION (pad_archive.py → graduate →
clear → self-healing diff), at session-close, when the scratchpad has real content. That procedure's
step (iv) states "Journal-first: every precious keeper hits the journal (SC-5) before/as it lands in
the brief." Precious items (decision / dead-end / number) hit the journal before/as they land in the
brief. This is `[honor]`.

---

#### PATH D — project-manager direct brief update

`pm-skill → [JOURNAL-FIRST hard rule in "Ongoing update rule"] → Edit → $DRIVE/system/journal.md (SESSION CONTEXT or ledger row) → Edit → brief [skill · honor for ordering · hook: guard_write_paths fires on both writes]`

**When it fires:** any time the project-manager skill updates the brief directly (not through `/save`)
— new dead-ends, decisions, or key numbers discovered during a PM doc sync.

**Rule text (exact, from pm-skill "Ongoing update rule"):** "Before you overwrite the brief with any
NEW dead-end, decision, or key number, that item must ALSO be written to `$DRIVE/system/journal.md`
(a SESSION CONTEXT entry or ledger row). Never let a piece of precious info live ONLY in the mutable
brief. If you are updating the doc directly (not through `/save`), write the journal entry as part
of the same update — do not defer it."

**Ordering rule:** same as PATH C — the skill prose mandates journal-first but no PreToolUse hook
verifies it. `[honor]`.

**What gets written:** a ledger row or SESSION CONTEXT block, depending on the significance of what
changed.

---

#### PATH E — mechanical writes (marc-sensor.py + marc-pulse-journal.py)

`marc-health-run.sh (Pulse cron) → python3 marc-sensor.py / marc-pulse-journal.py → open($DRIVE/system/journal.md, "a") → append one row [tool · outside Claude tool plane entirely]`

**When it fires:**
- `marc-sensor.py`: on a TRIP event (VIX regime escalation or a tripwire newly fired). Silent on
  QUIET (no journal write). Fires ~every 2h on Pulse cron via `marc-health-run.sh`.
- `marc-pulse-journal.py`: once per slot/day (market open, market close) — fires on any day
  `marc-health-run.sh` runs (no weekday/weekend guard in marc-pulse-journal.py; the weekend skip
  exists only in marc-sensor.py, not in this script).

**Mechanism:** pure Python file I/O (`open(path, "a")`). The Claude tool plane (Write/Edit tools)
is NOT involved; therefore `guard_write_paths.sh` does NOT fire. This path is entirely outside the
hook enforcement plane.

**Dedup (marc-pulse-journal.py only):** before appending, the script checks whether a row for the
same date + slot already exists in the file. If found, it skips the write (idempotent). No such
dedup exists in marc-sensor.py (each TRIP is always written).

**Failure mode:** both scripts catch `open()` exceptions and fail non-fatally: marc-sensor.py
writes to stderr and continues; marc-pulse-journal.py is explicitly "Non-fatal — a failure here
must not break the health run."

---

### READ PATHS (downstream consumers)

Four elements read journal.md directly. None of them write to it.

#### READ 1 — planning-diary-capture.py (primary Cal pipeline consumer)

`planning-diary-run.sh (Pulse interval ~86400s, any machine) → python3 planning-diary-capture.py → open($DRIVE/system/journal.md, "r") → parse pipe rows + SESSION CONTEXT blocks matching the target date → compose → atomic write (tmp + os.replace) → $DRIVE/desks/cal/diary/YYYY/MM/DD.md [tool · outside Claude tool plane]`

**Parsing logic (from `read_journal()` in planning-diary-capture.py):**
- Ledger rows: match lines where `line.startswith(f"| {date_str} |")`. Split on `|`, extract
  desk (parts[2]), slug (parts[3]), event (parts[4], truncated at 200 chars). Group by desk.
- SESSION CONTEXT blocks: match lines starting with `--- SESSION CONTEXT |`. Extract date from
  parts[1], desk from parts[2]. Scan forward to the closing `---`, extract the `session:` field
  value. Group the one-line session summary by desk.
- Output: `{desk: [entry, ...]}` dict — one per desk seen on the date.

**Fail-soft:** any `open()` exception returns `({}, "source-unavailable")`, exits 0. The diary
section for journal is then marked `_source-unavailable (journal read failed this run)_`. This
ensures the Pulse circuit breaker never trips on a content gap.

**Atomic write:** the diary file is written to a temp file first, then `os.replace()` to the
final path. Idempotent: regenerates the machine portion but PRESERVES any `## Human Delta —
verified` section verbatim (never overwrites human gray-matter).

**The Cal pipeline prohibition (save SKILL.md "Hard Prohibitions"):** `/save` must NEVER write
directly to a Cal diary file. The journal is the ONLY transit point for the Cal pipeline. An agent
writing directly to Cal would bypass the append-only backstop and violate the single-writer
invariant. `[honor]` — no hook blocks a rogue direct-Cal write.

#### READ 2 — planning-diary-rollup.py (periodic roll-up)

`planning-diary-run.sh (Pulse cron, at period boundaries) → python3 planning-diary-rollup.py → open($DRIVE/system/journal.md, "r") → journal_range(start, end) → aggregate by desk + by slug → write period review draft [tool · outside Claude tool plane]`

**Parsing logic (from `journal_range()` in planning-diary-rollup.py):** similar to planning-diary-capture.py
but spans a date range (weekly / monthly / quarterly / yearly). Aggregates `{desk: [events]}` AND
`{slug: [events]}` — the second dict powers the per-project activity summary in rollup reports.

**Fail-soft:** same as planning-diary-capture.py — source failure marks the section unavailable, exits 0.

**Output:** period review draft — path varies by cadence: weekly/monthly use
`desks/cal/diary/YYYY/MM/review-{cadence}-{label}.md`; quarterly/yearly omit the `MM` subdirectory
and write to `desks/cal/diary/YYYY/review-{cadence}-{label}.md`. The
`## Human Delta — verified` section is preserved across re-runs.

⚠ **`desks/cal/` is deliberate, not stale.** The desk was renamed `cal` → `planning` on 2026-08-15 in
code, jobs and tiles; **the records directory was NOT** — moving the operator's live records is his
decision and has not been taken. Known, intentional split — do not "complete" it without his word.

#### READ 3 — /read skill (Step 0 journal slice + gap signal)

`read-skill → Step 0: Read $DRIVE/system/journal.md → filter lines matching slug or desk → journal slice [skill]`

**What it does:** before searching the filesystem for project context, `/read` loads a project or
desk journal slice. Filters by slug (project-slice) or desk name (desk-slice). Extracts the gap
signal: "last journal entry for [{slug}] was [{date}]" — surfaces how stale the record is.

**Coverage disclaimer (mandatory, printed verbatim after every journal output):**
> Journal reflects saves via /save and explicitly logged decisions only. In-session pivots,
> verbal agreements, and file changes outside /save are not captured. A clean-looking journal is
> not a complete journal.

No shortening, no skipping.

#### READ 4 — /distill skill (last-30 journal rows)

`distill-skill → Read $DRIVE/system/journal.md → filter to | {desk} | → last 30 entries → one of four source streams [skill]`

The distill skill pulls the last 30 journal rows for the target desk as one of its named source
streams (alongside `state/current.md`, `canon/current.md`, and `telos.md`). The journal stream
is the "what happened recently" input. (Note: the brief is not a named source stream in distill/SKILL.md;
the relevant records directories are the primary scan target.)

#### READ 5 — /throughline skill (failure rows)

`throughline-skill → spawn 0 or 1 sonnet subagent (0 on the normal in-session path; 1 only when the diary-plot is thin/dead) → subagent reads brief.md + canon + last ~10 journal rows tagged failed:/DEAD END/PIVOT for the slug [skill]`

The throughline skill spawns 0 or 1 sonnet subagent: on the normal in-session path no subagent is
spawned; one is spawned only when the diary-plot is thin or dead. The subagent reads a narrow slice
of the journal: the last ~10 rows for a slug that carry failure/pivot signals. These rows are the
storyline-and-failure source for the throughline narrative — what was tried, ruled out, and why.
Read-only, never a fan-out.

#### READ 6 — /marc-checkin skill (marc journal rows)

`marc-checkin-skill → Step 0: read recent | … | marc | … | rows from $DRIVE/system/journal.md → session orient (market trips + weekly wraps) [skill]`

The marc-checkin skill reads recent `marc`-desk journal rows as its session-orient source. This is
the mechanism by which manually-checked marc events (which marc-sensor wrote as TRIP rows) inform
the next human market-review session.

#### READ 7 — archivist-audit (journal-newer-than-brief staleness check)

`archivist-audit → Read $DRIVE/system/journal.md → compare newest journal line for slug vs brief updated_at → staleness signal [agent]`

The archivist-audit uses the journal as a staleness probe: if the journal has an entry for a slug
that is newer than the brief's `updated_at`, the brief is flagged as stale (N. stale-brief rule).
This is the same signal the archivist uses during drift detection. Read-only.

---

### STORES READ OR WRITTEN

| Store | Path | Access | By |
|---|---|---|---|
| Journal (the store itself) | `$DRIVE/system/journal.md` | APPEND (## Log only) | /save, /checkin, project-manager, marc-sensor.py, marc-pulse-journal.py |
| Journal (read) | `$DRIVE/system/journal.md` | READ | planning-diary-capture.py, planning-diary-rollup.py, /read, /distill, /throughline, /marc-checkin, archivist-audit |
| Cal daily diary | `$DRIVE/desks/cal/diary/YYYY/MM/DD.md` | WRITE (atomic, machine sections only) | planning-diary-capture.py |
| Cal period review draft | `$DRIVE/desks/cal/diary/YYYY/[MM/]review-{cadence}-{label}.md` (MM present for weekly/monthly; absent for quarterly/yearly) | WRITE | planning-diary-rollup.py |
| Session transcript | `~/.claude/projects/*/$CLAUDE_CODE_SESSION_ID.jsonl` | READ | /save SC-1 (resolves the session to extract) |
| Cal diary status tile | `$DRIVE/state/status/planning-diary.json` | WRITE | planning-diary-run.sh (inline Python after capture) |

---

### GATES AND ENFORCEMENT (the honest map)

**What IS enforced (hook-level):**

1. **`guard_write_paths.sh`** (PreToolUse Write|Edit) `[hook]` — the residency wall. Fires on every
   Edit/Write tool call. For the journal specifically: ~~line 130~~ (actually ~line 270, corrected
   2026-08-27, claim 78) of the hook lists `system/journal.md`
   inside the **clone-content block-list** case statement. ~~Meaning: any Write/Edit to the CLONE path
   (`~/lifehack-brain/system/journal.md`) is HARD-BLOCKED (exit 1, with a REDIRECT message).~~
   **⚠ CORRECTED 2026-08-27, lb2-ops-comms.md claim 77 — live test contradicts this.** An `Edit`
   targeting `~/lifehack-brain/system/journal.md` through `guard_write_paths.sh` returned rc=0
   (ALLOWED), not blocked. The path is present in the block-list case statement (mechanism exists in
   source) but the live effective behavior did not match "hard-blocked" when fire-tested — needs
   re-verification against the guard's actual match/resolution logic before relying on this as an
   active control.
   A Write/Edit to the DRIVE path (`$DRIVE/system/journal.md`) hits the "Allow within Drive spine"
   branch (line 71-73) and exits 0 — ALLOWED. This half is unaffected by the correction above.

   Note: this hook covers the Claude tool plane (Write and Edit tools) only. Python `open(path, "a")`
   by marc-sensor.py and marc-pulse-journal.py is NOT a tool call — it bypasses this hook entirely.
   This is a KNOWN-GAP in guard_write_paths.sh (documented in the hook header, lines 14-15): "Bash
   file-writes (echo >, tee, cp, heredoc) BYPASS it entirely." The Python I/O path is the same class
   of bypass. Accepted and documented, not a surprise.

2. **`guard_canon_write.sh`** (PreToolUse Write|Edit) `[hook]` — NO-OP for journal writes. This hook
   checks if `/canon/` appears in `file_path`. The journal path (`system/journal.md`) contains no
   `/canon/` segment. Does not affect journal writes.

3. **`guard_ledger_discipline.sh`** (PreToolUse Write|Edit) `[hook]` — NO-OP for journal writes.
   Concerns `debt-ledger.md` discipline only. Zero references to "journal" in this hook.

4. **`validate_on_write.sh`** (PostToolUse Write|Edit) `[hook]` — advisory, non-blocking. Fires
   after every journal Edit; has no journal-specific logic found. Likely validates YAML frontmatter
   on other files. Runs on journal writes by coincidence, not by design.

5. **`observability_logger.sh`** (PostToolUse *) `[hook]` — logs every tool call. Fires on journal
   writes as on all other writes; records-only, no enforcement.

6. **`nudge_flow_drift.sh`** (PostToolUse Write|Edit) `[hook]` — advisory. Checks if the written
   file appears in an organism element's `generated_from`. journal.md is not in an element's
   `generated_from` (it is a data store, not a skill). Likely a NO-OP on journal writes in practice.

**What is honor-system (prose instruction only; no hook enforces):**

- **Journal-first ordering** — the rule that the journal MUST be written BEFORE/AS the brief is
  rewritten. Stated as "HARD" in /save Step 7d, /checkin Step 3.6b, and pm-skill "Ongoing update
  rule." No PreToolUse hook blocks a brief edit when the journal entry hasn't been written yet. If
  the skill skips the journal write, the brief write goes through. The word "HARD" in the doc
  overstates the enforcement posture — the gate is `[honor]` only.

- **Entry format discipline** — the field rules (event must say what changed AND why, `supersedes`
  must be a path or `—`, slug must exist in project-registry.md). No hook validates journal content.
  Any conforming or non-conforming text can be appended.

- **No-routing-directly-to-Cal** — the prohibition against agents writing diary files directly (they
  must route through the journal so planning-diary-capture.py picks it up). No hook blocks a direct Cal
  diary write from a non-/save path. `[honor]`.

- **Coverage disclaimer** — the mandatory print after any journal-derived synthesis (Step 9 of /save;
  `/read` Step 0). The disclaimer text itself is tracked in the journal.md file header. No hook
  enforces that it is printed.

- **marc-sensor.py / marc-pulse-journal.py dedup** — the write-once-per-slot dedup in
  marc-pulse-journal.py is code logic (not a hook). If the code fails or is bypassed, double rows
  can accumulate. The planning-diary-capture.py parser tolerates duplicates (it groups by desk, so two
  rows for the same slot just mean two bullets in the diary section).

---

### EDGE CASES

1. **Ledger row missing the date-pipe prefix** (e.g., written via Bash heredoc with wrong format)
   → planning-diary-capture.py's `read_journal()` silently skips it (the `startswith(f"| {date_str} |")`
   check fails). The row is in the journal file but invisible to the Cal pipeline. No hook catches
   malformed rows.

2. **SESSION CONTEXT block with malformed header** (fewer than 4 pipe-separated parts) → the
   planning-diary-capture.py parser skips the block silently (`if len(hdr) >= 4 and hdr[1] == date_str:`
   fails). Again invisible to the Cal pipeline.

3. **Transcript not found** (empty `$CLAUDE_CODE_SESSION_ID` or no matching `.jsonl`) → /save SC-1
   falls back to context-window pull AND notes the fallback in the journal entry (so the lossy pass
   is visible). The SESSION CONTEXT block is still written; it just isn't anchored to the full
   transcript.

4. **TRIP on a weekend (marc-sensor.py)** → the sensor exits silently at the weekend guard; no
   journal row is written. The guard (`if utc_now().weekday() >= 5: … return 0` at lines 77–80)
   fires BEFORE the `if tripped:` block — the journal-write code is never reached on weekends
   regardless of trip status. The weekend guard is unconditional on trip status, not conditional
   on QUIET.

5. **marc-pulse-journal.py slot dedup race** (two concurrent runs before either finishes) → both
   could append, producing a duplicate row for the same date + slot. The dedup check is a read-then-
   write (not atomic); no file lock. Tolerated: the Cal pipeline produces two bullets for the same
   slot in the diary, which is cosmetically redundant but not incorrect.

6. **Journal grows unbounded** — the file had no rotation, archival, or truncation mechanism and
   grew indefinitely, while the planning-diary-capture.py and planning-diary-rollup.py parsers scanned the
   whole file on every run (`lines = f.readlines()`) with no hard cap or warning.
   **✅ THIS IS RESOLVED — `system/tools/journal.py` carries a `rotate` subcommand
   (`journal.py rotate [--dry-run]`).** It moves every entry from a *completed* month out of
   `journal.md` into a segment file `system/journal/YYYY-MM.md`, and leaves the current month in
   place (rotating the current month would split a month across two files). Rotation is
   **move-and-verify: it never deletes and never rewrites** — it moves whole lines between files and
   refuses, raising before anything is removed, if the segment did not receive every row. This also
   bounds the full-file `readlines()` scan cost the gap flagged, since only the current month
   remains in `journal.md`. ⛔ **The corollary a reader must carry: anything reading the journal
   must read the segments too.** A reader that opens only `journal.md` loses everything before the
   last rotation, and it fails *quietly* — the slice comes back short and reads as a quiet stretch
   rather than a truncated search. `journal.py slice` spans the segments correctly; a skill grepping
   by hand must include `system/journal/*.md`.

7. **/save Step 7 — journal entry for a state edit** — whether a state edit (Step 5b) warrants a
   journal entry is explicitly a model judgment call ("journal only if it materially changes project
   chronology"). No hook verifies the judgment. A state edit that SHOULD have a journal entry but
   doesn't is silently undetected.

8. **Two skills write to the journal in the same agent turn** (e.g., a /checkin that also triggers
   /save) — both will attempt Edit tool calls to append to the same file. Since Edit is append-to-
   end and the journal is an append-only log, this is safe — the two appends land sequentially and
   both are valid rows. No concurrency hazard in the single-threaded Claude tool plane.

---

### HARD PROHIBITIONS

What the journal element never does (from the file header + skill hard rules):

- No edits or deletions to existing entries in `## Log` — the journal is append-only by definition.
- No direct write to a Cal diary file as a substitute for the journal → Cal path (`[honor]`).
- No write of a journal entry that lacks the slug in `system/project-registry.md` — except
  `{desk}-general`, which is always valid (`[honor]`).
- No write to the clone-side copy of journal.md (`~/lifehack-brain/system/journal.md`) — this is
  `[hook]`-enforced by `guard_write_paths.sh`.
- No synthesis of journal output without the coverage disclaimer (`[honor]`).
- No machine-promoted `type: rule` or `vetted: true` entries — the journal records what happened,
  not what should always happen.

---

### INTENT / CURRENT-VS-TARGET

**Purpose:** the journal is the one place that is NEVER overwritten. Briefs are overwritten
(compaction clears the scratchpad, CURRENT STATE is refreshed, STORY LOG grows). Records are
updated. The journal grows only. That makes it the safety net: any precious info (decision,
dead-end, key number) that appears in the journal cannot be lost by a subsequent brief rewrite or
record update. The journal-first rule exists because of this property — the brief is the live
working surface, the journal is the indestructible ledger.

**Second role:** the journal is the Cal pipeline's only cross-desk narrative source. It is
deliberately the ONLY input to planning-diary-capture.py's "Machine Recap" section. This means the
agent's work becomes visible to the Cal pipeline if and only if it routes through the journal — an
intentional bottleneck that keeps the Cal pipeline from being wired to every individual store.

**Current state → PARTIAL, for a precise reason:**
- The RESIDENCY wall (Drive path allowed, clone path blocked) is `[hook]`-enforced and fire-testable.
  This is the strong part.
- The JOURNAL-FIRST ORDERING rule (journal before the brief) is the most critical behavioral
  property of the journal — and it is `[honor]`-only. The word "HARD" in the skills' prose overstates
  the enforcement posture. A skill that skips the journal write and goes straight to a brief edit
  will pass all hooks without complaint. This is the gap that makes the label PARTIAL rather than
  LIVE.
- The ENTRY FORMAT discipline (field rules, slug-must-exist, event-must-say-why) is entirely
  `[honor]`. No hook validates what is appended.
- The Cal pipeline prohibition (no direct-Cal write) is `[honor]`.
- The mechanical write paths (marc-sensor.py, marc-pulse-journal.py) bypass the hook plane entirely
  via Python file I/O. This is a known-gap class documented in guard_write_paths.sh. Accepted.

**TARGET:**
1. **Harden journal-first ordering** — a PreToolUse hook that detects when an Edit to a known
   `brief.md` path fires before an Edit to `journal.md` has fired in the same turn could catch
   ordering violations. This is architecturally complex (requires session-scoped state in the hook).
   Tracked as a potential Phase-5 hardening task.
2. **Journal entry format validation** — a PostToolUse advisory hook that checks the appended
   content starts with `| YYYY-MM-DD |` or `--- SESSION CONTEXT |` and emits a nudge if not.
   Would catch the malformed-row edge case that currently makes entries invisible to the Cal
   pipeline.
3. **File-size monitoring** — ✅ the rotation half of this is DONE (see Edge Case 6):
   `journal.py rotate` segments completed months into `system/journal/YYYY-MM.md`, so the full-file
   scan on each planning-diary-capture.py run is bounded to the current month. What remains open is the
   indexed-format question and any automatic scheduling of `rotate` — today it is a CLI subcommand
   a human or a job invokes, not a cadence.

---

### INTEROP SEAMS (shared-state edges — the organism view)

All interop seams typed with the closed vocabulary from §8.3.

**Callers that WRITE to journal.md:**

- `WRITES->   save` · /save Steps 7, 7d, SC-4(iv journal-first), SC-5 each append ledger rows or
  SESSION CONTEXT blocks; the mandatory transit point before any brief or canon write lands anywhere
  `[skill]`

- `WRITES->   checkin` · Step 3.6b append-only journal-first write before/as the brief Story Log
  is updated; treats the brief as overwrite-safe ONLY because the journal is the append-only
  backstop `[skill · honor on ordering]`

- `WRITES->   project-manager` · journal-first hard rule: any dead-end, decision, or key number
  written to the brief must hit journal.md first (same Edit, never deferred) `[skill · honor on ordering]`

- `WRITES->   marc-sensor` · (tool, not a ranked element) appends one mechanical TRIP row per VIX
  regime escalation / tripwire fire — zero LLM, Pulse-cron, Python file I/O outside the hook plane
  `[tool]`

- `WRITES->   marc-pulse-journal` · (tool, not a ranked element) appends one market-pulse line per
  slot/day (open/close); consumed by planning-diary-capture via the same pipe-row format `[tool]`

**Consumers that READ from journal.md:**

- `FEEDS      planning-diary-capture` · planning-diary-capture.py reads journal.md as the primary input for
  each day's Machine Recap — the only cross-desk narrative source the Cal pipeline ingests; ONLY
  transit point, by design `[tool · pulse-cron]`

- `FEEDS      planning-diary-rollup` · planning-diary-rollup.py reads journal.md for period-range
  aggregations (weekly/monthly/quarterly/yearly) by desk + by slug `[tool · pulse-cron]`

- `READS      read` · /read Step 0 loads a journal slice filtered by desk or slug; surfaces the
  gap-since-last-entry staleness signal; mandates the coverage disclaimer on every journal output
  `[skill]`

- `READS      distill` · pulls the last 30 journal rows for the target desk as one of its named
  source streams (alongside state/current.md, canon/current.md, telos.md) `[skill]`

- `READS      throughline` · reads the last ~10 journal rows for a slug tagged `failed:` / `DEAD END` /
  `PIVOT` as the storyline-and-failure source for its sub-agent `[skill]`

- `READS      marc-checkin` · reads recent `| … | marc | … |` rows as the session orient — market
  trips and weekly wraps `[skill]`

- `READS      archivist-audit` · uses journal-newer-than-brief as a staleness check (N. stale-brief
  rule) — compares brief `updated_at` against newest journal line for the same slug `[agent]`

**The wall that governs writes:**

- `GUARDED-BY   guard_write_paths` · PreToolUse: allows Write/Edit to the Drive path; blocks any
  Write/Edit to the clone-side copy — residency enforcement `[hook]`

---

## AUTO-COMPUTED   (machine-only — hand-set at authoring; the F1.5 checker will own this once built)

- **maturity_label:** PARTIAL (honor)
- **check_detail:** pending label_checker.py. Proposed basis: PARTIAL — one hook-enforced wall fires
  (`guard_write_paths.sh` BLOCKS clone-path Write/Edit to journal.md; Drive path ALLOWED). What
  remains honor-system: journal-first ordering (the most load-bearing rule, stated "HARD" in three
  skills, no PreToolUse hook enforces it) · entry format discipline (pipe-row + SESSION CONTEXT
  structure, field rules, slug-must-exist) · Cal-pipeline prohibition (no direct-Cal write) ·
  coverage disclaimer print · mechanical write paths (marc-sensor.py + marc-pulse-journal.py) bypass
  the hook plane entirely via Python file I/O (documented known-gap class). Mixed: one strong
  residency wall + significant honor-system surface across the most important behavioral property
  (ordering) ⇒ PARTIAL. Not LIVE because the journal-first ordering, which is the element's core
  safety property, is not mechanically enforced.
