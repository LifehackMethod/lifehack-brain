---
topic: [google-sheets]
id: system-playbook-google-sheet-sop
title: "Google Sheet SOP — the rules of engagement for any sheet build"
record_type: playbook
desk: root
created_at: 2026-06-20
updated_at: 2026-06-20
status: active
authority: user
---

# Google Sheet SOP

> The single **rules of engagement** for building, editing, or writing to ANY Google Sheet through this system.
> `/build` routes here (build-type "a Google Sheet"); the `google-sheet` skill applies it; the two sheet
> hooks enforce it. Craft detail (design tiers, internal-control layer, capabilities) lives in the
> `google-sheet` skill + its `standards.md`/`capabilities.md` — this doc owns the **rules**, not the craft.

# Doing Google Sheet work right means…
Every line traces to `canon/google-sheet-sop.md`.

> **Words used here**
> - **`_LLM_GUIDE`** — the tab in every sheet this system builds that holds the sheet's rules and structure for a fresh session.
> - **PURPOSE block** — the short orientation at the very top of `_LLM_GUIDE`.
> - **calculating sheet** — a sheet that computes anything; a **pure store** holds data with no math.
> - **error sweep** — one check flagging any broken cell anywhere in the sheet.
> - **`_CHECKS` tab** — the tab of formula checks that prove a calculating sheet's math.
> - **check-engine-light** — the one cell, at a fixed location, that says the sheet's health.
> - **`🔒`** — the mark at the start of a formula-only column header.
> - **fine china** — a billing/financial sheet, or one the person has named fine china.
> - **owner-API write** — a write sent through the API, authenticated as the file's owner.
> - **runner** — a scheduled run, with nobody at the screen.

## 1. Every time…

- The LLM never does math, calculation or analysis; it only reads what the sheet already computed and folds it in verbatim, never re-deriving a number at read time. → SOP Principle #1
- Computation goes, in order of preference: maximum in the Sheet (formulas, `ARRAYFORMULA`, `XLOOKUP`), then Apps Script (via `clasp`) when logic is too complex for a formula, minimum in the LLM. → SOP Principle #1
- Every check is a formula inside the sheet; a check a person has to run by hand is not a check. → SOP Principle #2
- Before any write, read the sheet's `_LLM_GUIDE` tab, with `python3 <repo>/system/tools/safe_sheets.py <spreadsheet-id> '_LLM_GUIDE!A:Z'`. A raw `values get` is refused. → SOP Convention 1; gws sheets syntax; Workflow 1
- If `safe_sheets.py` exits 1, spans were flagged and neutralised: read the stderr list. → SOP gws sheets syntax
- Normal sheet work appends rows (`gws sheets spreadsheets values append --params '{...}'`); it never edits formulas or rewrites computed cells. → SOP The append-only model; gws sheets syntax
- The sheet's own locks (dropdowns, protected ranges, "warn first") do NOT stop a write authenticated as the file owner; the only real guard is the hooks on this machine. → SOP The append-only model
- Write only the columns you changed. Never read a whole row/range and write it back (`getValues` → `setValues`, or a full-width `values.update` that spans computed columns) — that silently turns every formula in the range into a static value. → SOP Write narrow
- A full-row write fails without a sound: a script that has run for weeks with no visible problem may already have flattened its formulas, so new rows stopped calculating and nothing said so. "It ran fine" is not proof it did no harm. → SOP Write narrow (the measured 2026-07-06 example)
- Never touch a formula or `🔒` cell without explicit confirmation. → SOP Workflow 3
- Back up first for any non-append change. → SOP Workflow 4 (`canon/build-conformance-sop.md` §5 item 3)
- Every sheet has an error sweep, no exceptions, flagging `#REF!`/`#N/A`/`#ERROR!`/`#DIV/0!`/`#VALUE!`/`#NAME?` — even a pure data store. → SOP Principle #2; Convention 4
- Every sheet this system builds has a tab named `_LLM_GUIDE`, opening with a PURPOSE block. → SOP Convention 1, 1a
- The PURPOSE block fills the slots North star, What this is + who reads it, The one rule, Out of scope, and Live stakes (optional — only when something time-sensitive is load-bearing right now). → SOP Convention 1a
- The PURPOSE block ends with the one-line pointer `Recent changes → _LOG`. → SOP Convention 3
- There is no separate `purpose.md`; nothing load-bearing lives only in a longer doc. → SOP Convention 1a
- Every formula-only column header starts with `🔒` (e.g. `🔒 suggested_entity`); no `🔒` means the column accepts input. → SOP Convention 2
- Every sheet has a `_LOG` tab, newest on top: one line per session that CHANGED the sheet — `date · what changed · why/conclusion` — rolling ~10 entries. Pure-read sessions do not append. (Best-effort for now — no hook.) → SOP Convention 3

## 2. In these situations…

- If the sheet CALCULATES anything → it has a `_CHECKS` tab that proves its math, right-sized; the anti-overbuild test decides how MANY checks, never whether. A pure store with no math carries the error sweep only, no tab. → SOP Principle #2; Convention 4
- If the sheet calculates → it has one check-engine-light cell at a FIXED, predictable location (a named range, e.g. `sheet_status`), machine-readable (`OK` / `⚠ <n> FAILURES`). Turning a red light into a notification is the dashboard's job, not the sheet's. → SOP Principle #2; Convention 4
- If the sheet calculates → it has at least one COMPLETENESS check: for each row that SHOULD have an input, assert the input is non-blank. A blank passes every consistency check, and a blank counts as `0` in arithmetic. → SOP Principle #2a
- If you reconcile something by hand → make it a permanent `_CHECKS` row (encode-once). → SOP Principle #2
- If a formula must use a fixed row ceiling → add a capacity check that warns at ~85% full. → SOP Convention 4
- If a row's owner / category / classification comes from an authoritative reference (a map, glossary, registry) → a formula column must apply that map (e.g. `XLOOKUP(key → map.owner)`), paired with a check for zero unmapped / `UNKNOWN` rows. → SOP Convention 1b, G2a
- If the sheet is a backup, archive, prior-year or deprecated copy → the PURPOSE block's FIRST line says so, e.g. `⛔ BACKUP — not the live sheet; writes go to <where>`. → SOP Convention 1a
- If the tab is still named `LLM Instructions` or `README` → it is a legacy name being renamed to `_LLM_GUIDE`; the `guard_sheet_writes` hook accepts it during transition. → SOP Convention 1
- If the sheet is fine china (any billing/financial sheet) → read first, append only, never bulk-overwrite. → SOP The append-only model
- If the person has NAMED a sheet fine china → do not edit it without asking them first; with nobody at the screen (a scheduled run), park that edit for the morning. → SOP The append-only model
- If a fine-china edit is needed with nobody at the screen (a scheduled run) → park it for the morning. → SOP The append-only model (`canon/cron-jobs-sop.md` §7, `canon/build-conformance-sop.md` §2)
- If the operation is destructive (clear/delete/mass-overwrite) → it also needs an explicit confirmation. → SOP The friction layer
- If a formula change is deliberate → it needs `LIFEHACK_SHEET_CONFIRM=1`, after showing the person whose sheet it is the exact before and after. → SOP The friction layer
- If a write targets an `ARRAYFORMULA` spill cell → `guard_sheet_formula_writes` does not catch it (the hook's own header names that edge); every other formula (`=…`) or `🔒` cell is blocked, labelled or not. → SOP Convention 2
- If you need the tab list → `gws sheets spreadsheets get --params '{"spreadsheetId":"<ID>"}'`. → SOP gws sheets syntax
- If running in a runner → send stderr to a file (`2>"$TMP/gws.err"`), parse stdout only, read the file if the call fails; `2>/dev/null` is refused there. → SOP gws sheets syntax
- If building a new sheet → use the `google-sheet` skill (Kickoff mode), so it is born with `_LLM_GUIDE` (PURPOSE block + the body guidelines that apply), `🔒` headers, per-tab purpose lines, a `_LOG` tab, and the error sweep + `_CHECKS` layer. → SOP Workflow 5
- If writing, editing or deploying Apps Script, or setting a trigger → only on the person's named instruction. → SOP Apps Script via clasp
- If there is Apps Script source (`.gs` / `appsscript.json` / `.clasp.json`) → it lives in the repo, in a dedicated Apps Script folder, versioned and pushed — never under your notes folder. → SOP Apps Script via clasp
- If `clasp` is set up → `~/.clasprc.json` is a credential: machine-local, gitignored, never committed. → SOP Apps Script via clasp
- If the API must touch format → `spreadsheets.batchUpdate` + `repeatCell` / `updateBorders` with an EXPLICIT field mask; never `values.batchUpdate` for formatting (it overwrites); requests small, single-range, idempotent. → SOP Formatting 2
- If you need a format → format one cell by hand, read its `userEnteredFormat` via `spreadsheets.get`, reuse it verbatim; don't hand-author format JSON. → SOP Formatting 2
- If you need to SEE a private sheet → publish-to-web first, render the public URL with headless Chrome and `--virtual-time-budget` ~15s (`render_shot.sh` alone shoots blank), and un-publish when done. → SOP Formatting 3
- If reusing a styled tab across files with `sheets:copyTo` → re-apply row heights, protected ranges and named ranges separately; they do not come along. → SOP Formatting 4
- If the work is visual/layout precision → it goes to HTML, not the Sheet; `/design-lifehack` is built for HTML and not for Sheets. → SOP Formatting 5
- A summary tier a person has explicitly approved for a specific sheet is the one narrow exception to Principle #1. → SOP Principle #1

## 3. Good practice

- Style the LOOK once, by hand in the Sheets UI; never have the LLM rebuild a look from scratch via the API. → SOP Formatting 1
- Prefer open-ended ranges (`A4:A`, whole-column, dynamic) over hardcoded ceilings like `A4:A2000`. → SOP Convention 4; Principle #2a
- For the completeness check, you usually want both shapes: a `✗`-prefixed BLOCKING check on the current period, and a `⚠`-prefixed (NOT `✗`) WARNING check across all history. → SOP Principle #2a
- Keep the PURPOSE block to a target of ~80–120 words, 5–7 lines, scannable in ~15 seconds; cap the slots, not the word count. → SOP Convention 1a
- The PURPOSE block orients, it does not dictate: the why and the one load-bearing rule, no step-by-step procedure. Test: does it orient a smart stranger, or try to operate the sheet for them? → SOP Convention 1a
- Below the PURPOSE block, carry the guidelines G1–G6 a stranger would get wrong, scaled to the sheet (a simple sheet needs two, a multi-tab financial sheet all six): G1 computed vs. input (and who writes a pipeline tab), G2 who owns each fact, G3 write rules + append direction + entry order, G4 route new things to existing homes, G5 conventions a stranger can't guess (write numbers, not `"$1,234"` strings), G6 status in ONE known spot, newest-wins. → SOP Convention 1b
- Adding a tab requires justifying why a leaner build won't do — bias to consolidate. → SOP Convention 1b, G4
- Each tab carries a one-sentence purpose line in row 1 (the `google-sheet` skill's convention). → SOP Convention 1a; Workflow 5
- Reuse a look by copying a styled TAB (`sheets:copyTo`) or extracting a Style Kit — never hand-redo it. → SOP Formatting 4
- Avoid "paste format only" onto an existing populated range — it silently drops widths/heights/protections. → SOP Formatting 4
- Column width is whole-column, format state is additive, and there is NO live preview. → SOP Formatting 3
- Apps Script is optional; most sheets never need it. → SOP Apps Script via clasp
- Craft detail (check taxonomy, alert levels, right-sizing) lives in the `google-sheet` skill → *Internal Control Layer Design*; `/calculate` arms "arithmetic is computed" for a whole session. → SOP Principle #2; Pointers

— end of checklist —

## Principle #1 — the sheet computes; the LLM interprets (the law)
**The LLM NEVER does math, calculation, or analysis.** It fumbles arithmetic — so all computation lives in
deterministic code. The design ladder, in order of preference:

1. **Maximum in the Sheet** — formulas, `ARRAYFORMULA`, `XLOOKUP`. The sheet is the calculator.
2. **Then Apps Script** (via `clasp` — see below) when logic is too complex for a formula.
3. **Minimum in the LLM** — the LLM only **reads what the sheet already computed and folds it verbatim**.
   It never re-derives a number at read time.

This is the sheets application of the harness brief's "Arithmetic is computed, never done in your head".
(Narrow exception: a summary tier a person has explicitly approved for a specific sheet.)

## Principle #2 — the sheet checks itself; fail loud, never silent (the corollary)
If Principle #1 says the sheet does the math, this says **the sheet also proves its own math.** Anything you'd
ever verify by hand becomes a permanent live formula that re-checks on every open — double-entry bookkeeping
applied to every workbook: so it is much harder to be quietly wrong (Principle #2a shows the gap a
consistency check leaves). Two non-negotiables:
1. **Fail loud, never silent.** A broken or inconsistent cell must be impossible to miss — the enemy is a
   `#REF!` that renders like real data. Every sheet carries an **error sweep**; every sheet that CALCULATES
   also carries a right-sized **`_CHECKS` tab** that proves its math, rolling up to one **check-engine-light**
   cell at a fixed location — the single cell a dashboard reads to know the sheet's health (convention #4).
2. **The sheet checks itself — never the LLM/human.** Every check is a formula *inside* the sheet (Principle #1);
   a check a person has to run by hand isn't a check. **Encode-once:** the moment you reconcile something by
   hand, make it a permanent `_CHECKS` row — a manual check is a one-time cost, an encoded one is free forever.

Craft (the check taxonomy, alert levels, right-sizing): the `google-sheet` skill → *Internal Control Layer Design*.

## The append-only model
Normal sheet work **APPENDS rows** — it never edits formulas or rewrites computed cells. A Google Sheet's
own locks (dropdowns, protected ranges, "warn first") do **NOT** stop a write authenticated as the file
owner (proven live 2026-06-20) — so the only real guard is on our machine, before the command leaves
(the hooks below). Billing/financial sheets are **fine china**: read first, append only, never bulk-overwrite.
A Sheet the person has named fine china is not edited without asking them first; with nobody at the screen
(a scheduled run) that edit is parked for the morning (`canon/cron-jobs-sop.md` §7,
`canon/build-conformance-sop.md` §2).

## Write narrow — never rewrite a whole row over a formula
A script or API call that reads a whole row/range and writes it back (`getValues` → `setValues`, or a
full-width `values.update` that spans computed columns) **silently overwrites every formula in that range
with the static value it happened to be showing.** The formula is gone, the number still looks right, and
the next appended row comes up blank. **Write only the columns you changed** — a menu script
that stamps status/dates touches those columns alone, never the full row. This is the read-modify-write trap
generalized to any store: update the specific fields you changed, never blind-write a whole record back over
cells something else owns (a formula, another process, a downstream field).
*(Measured 2026-07-06 on a real billing tracker: a menu script wrote the full row back on every run,
flattening the rate and amount `ARRAYFORMULA` into static values — newly-added rows silently stopped
calculating, and nothing said so for weeks.)*

## The conventions every sheet this system builds carries

**1. The `_LLM_GUIDE` instruction tab (canonical name).**
Every sheet this system builds has a tab named **`_LLM_GUIDE`** holding its rules + structure for a fresh session.
Read it BEFORE any write. *(Legacy names `LLM Instructions` / `README` are being renamed to `_LLM_GUIDE`
in the backfill; the `guard_sheet_writes` hook accepts them during transition.)*

**1a. The PURPOSE block — opens `_LLM_GUIDE` (the one slot guaranteed read every window).**
The `guard_sheet_writes` hook forces a read of `_LLM_GUIDE` before any write, so the **top of that tab** is
the single thing a fresh session is guaranteed to see each window. It carries a **sheet-level PURPOSE block**:
the 15-second orientation that stops a session writing blind. **Size is the constraint, not a nicety** — it is
re-read on EVERY write, so a long block *is* the cognitive load it exists to kill. Target **~80–120 words,
5–7 lines, scannable in ~15 seconds** — fill the slots, don't write an essay. The five slots:
- **North star** — one line: why this sheet exists.
- **What this is + who reads it** — one line.
- **The one rule** — the single constraint that, violated, corrupts the sheet.
- **Out of scope** — what does NOT belong here, and where it goes instead.
- **Live stakes** (optional) — only when something time-sensitive is load-bearing right now.

Cap the **slots**, not the word count — the slot list travels across sheets of any complexity. This is the
WHOLE-SHEET "why," distinct from the **per-tab purpose line** (one sentence in row 1 of each tab — the
`google-sheet` skill's convention). There is **no separate `purpose.md`** — the block IS the complete
statement of purpose; nothing load-bearing may live only in a longer doc.

**Orient, don't dictate (the north-star test).** The block is a *north star*, not a rulebook. It conveys the
WHY and the single load-bearing rule, then **trusts the reading session's judgment for the how.** Resist the
pull to spell out step-by-step procedure or a wall of do's-and-don'ts — over-prescription blows the 15-second
budget AND ages badly as the sheet evolves (yesterday's rigid rule becomes tomorrow's wrong rule). Each slot
captures *intent*, not mechanics. Test before locking: *does this orient a smart stranger, or try to operate
the sheet for them?* If it reads as a procedure manual, cut it back to the why.

**Non-live sheets declare it in line one.** If the sheet is a backup, archive, prior-year, or deprecated
copy, the PURPOSE block's FIRST line says so — e.g. `⛔ BACKUP — not the live sheet; writes go to <where>`.
A guide that describes a dead sheet as operational is exactly how a fresh session silently writes to the
wrong place (seen live: a backup copy and a superseded tracker both reading as operational).

**1b. The `_LLM_GUIDE` body — what a fresh session must understand (scaled to the sheet).**
Below the PURPOSE block, the guide carries the handful of things a stranger would get WRONG. These are
GUIDELINES, not a mandatory template — a simple sheet needs two; a multi-tab financial sheet needs all six.
The same "orient, don't dictate" test applies: state what's true and where things live, never a procedure.
- **G1 — Computed vs. input.** Name the read-only tabs/columns (formula · `IMPORTRANGE` relay · machine/
  pipeline-written · web-published); `🔒` (#2) is the per-cell signal. *(The #1 trap — formula cells look
  hand-editable.)* For a pipeline-written tab, name the thing that writes it ("written by the import
  job — hand-edits get clobbered on the next run").
- **G2 — Who owns each fact.** If a fact could live in two places, say which tab owns it and which derive;
  state any precedence (e.g. "most-recent block wins," "`_RULES` beats this guide").
- **G2a — Resolve identity by a COMPUTED column, never a manual join.** If a row's owner / category /
  classification comes from an authoritative reference (a map, glossary, registry), a **formula column must
  apply that map** (e.g. `XLOOKUP(key → map.owner)`) so every row is pre-resolved at the data layer. **A
  documented map a reader has to apply by hand is a latent misattribution** — the careful session is fine,
  the careless one isn't. Pair it with a completeness check (zero unmapped / `UNKNOWN` rows). *(Finance ex:
  stamp each transaction's owner from the card-last4→owner map — don't make a session join by last-4. But this
  is general: any sheet whose rows are typed/owned/classified from a lookup gets the computed column.)*
- **G3 — Write rules + append direction.** What the session may write freely vs. what needs explicit
  sign-off; which way rows grow (top vs. bottom); and any mandatory entry order (out-of-order = orphan/stale rows).
- **G4 — Route new things to existing homes.** A new metric/insight/row goes to the tab that already owns
  it. Adding a tab requires justifying why a leaner build won't do — bias to consolidate. *(Lean by default.)*
- **G5 — Conventions a stranger can't guess.** Only the load-bearing few: sign/units/format (write numbers,
  not `"$1,234"` strings), naming collisions (same label, different owner → join on the key), intentionally-
  empty tabs, PII handling. Not an inventory.
- **G6 — Keep status current.** Volatile status lives in ONE known spot, newest-wins; a stale guide is a real
  failure mode (one that says "vacant" while the unit is rented mis-steers every session). Pairs with `_LOG` (#3).

**2. `🔒` on formula cells/headers — BOTH layers.**
- **Human layer:** prefix every formula-only column header with `🔒` (e.g. `🔒 suggested_entity`). Absence
  of `🔒` means the column accepts input. Co-located with the data, impossible to miss.
- **Machine layer:** the `guard_sheet_formula_writes` hook blocks any owner-API write whose target cell
  **is a formula (`=…`) or carries `🔒`** — it works even on unlabeled formula cells, except an
  `ARRAYFORMULA` spill cell (the hook's own header names that edge).
- The two are complementary: 🔒 signals to a human; the formula-value check is the friction that holds it.

**3. The `_LOG` tab — a light rolling history of what changed.**
A separate tab named **`_LOG`** carries an abbreviated, newest-on-top history so a fresh session can see what
recent sessions saw, concluded, and changed. Keep it LIGHT: one line per session that CHANGED the sheet —
`date · what changed · why/conclusion` — rolling **~10 entries** (Drive's own version history holds the full
past; the tab stays short on purpose). The PURPOSE block (#1a) ends with a one-line pointer (`Recent changes →
_LOG`) so the forced `_LLM_GUIDE` read tells every session the log exists. **Only changing sessions append;
pure-read sessions don't.** Best-effort for now — no hook; it rides the same write you were already making.

**4. The `_CHECKS` tab + the check-engine-light (Principle #2 made structural).**
- **Error sweep — every sheet, NO exceptions.** One check flagging any broken cell anywhere
  (`#REF!`/`#N/A`/`#ERROR!`/`#DIV/0!`/`#VALUE!`/`#NAME?`). Cheap, universal, catches the #1 silent killer — a
  snapped link or `IMPORTRANGE`. Even a pure data store gets this one.
- **`_CHECKS` tab — every sheet that CALCULATES anything.** Right-sized: a few checks for a simple sheet, more
  for a complex one. The skill's anti-overbuild test governs **how MANY** checks, **never whether** — a
  calculating sheet always proves its math. A pure store with no math carries the error sweep only, no tab.
- **One check-engine-light cell** at a FIXED, predictable location (a named range, e.g. `sheet_status`),
  machine-readable (`OK` / `⚠ <n> FAILURES`) — the single cell a dashboard or fresh session reads to know the
  sheet's health **without sweeping the whole workbook.** The sheet self-monitors; consumers just glance at the
  light. (Turning a red light into a notification is the dashboard's job, not the sheet's.)
- **Capacity / headroom check.** Where a formula must use a fixed row ceiling, add a check that warns at
  ~85% full — so the sheet flags *before* it silently stops counting new rows. (A hardcoded ceiling that
  fills up is a silent-corruption time-bomb: the numbers just quietly go stale with no error.)
- **Prefer open-ended ranges over hardcoded ceilings (design principle).** Use `A4:A` / whole-column / dynamic
  ranges, NOT `A4:A2000` — an open range can't be outgrown. Where a ceiling is genuinely unavoidable
  (perf), pair it with the capacity check above. This eliminates the trap rather than monitoring it.
- Full taxonomy / alert levels / right-sizing: the `google-sheet` skill → *Internal Control Layer Design*.

## Apps Script via clasp
**`clasp`** is Google's Apps Script CLI. Install and authenticate it once (`INSTALL.md` walks the step)
and Apps Script becomes something you write, version and push from the command line rather than hand-edit
in a browser tab.
- **Residency:** Apps Script source (`.gs` / `appsscript.json` / `.clasp.json`) is **code** → it lives in
  this repo, in a dedicated Apps Script folder, versioned and pushed. **Never under your notes folder** —
  it is not your material, it is a program.
- **Auth:** `~/.clasprc.json` is a credential → machine-local and gitignored, the same as the `gws` login.
  Never commit it.
- **Who writes it:** an agent writes, edits or deploys Apps Script, or sets a trigger, only on the
  person's named instruction (approved by Enver, 2026-11-13).
- ⚠ Apps Script is optional. Everything above it — formulas, `ARRAYFORMULA`, the check layer — works with
  no clasp installed at all, and most sheets never need it.

## The friction layer (the hooks — `system/hooks/`)
- **`system/hooks/guard_sheet_writes.sh`** — blocks any gws sheets WRITE until the sheet's `_LLM_GUIDE`
  tab has been READ this window; destructive ops (clear/delete/mass-overwrite) also need an explicit
  confirmation. Reads always pass, so reading the guide is never blocked.
- **`system/hooks/guard_sheet_formula_writes.sh`** — blocks owner-API writes onto formula and `🔒` cells
  (Principle #1 and append-only, enforced). A deliberate formula change needs `LIFEHACK_SHEET_CONFIRM=1`
  after showing the person whose sheet it is the exact before and after.

## gws sheets syntax (current — `/opt/homebrew/bin/gws`)
- Read: `python3 <repo>/system/tools/safe_sheets.py <spreadsheet-id> '_LLM_GUIDE!A:Z'` — a raw `values get` is refused (`ingest_gate_enforce.sh` in a session, the door in a runner, `canon/cron-jobs-sop.md` §7); safe_sheets sanitizes every cell, scans for injection and fails closed; exit 1 means spans were flagged and neutralised, so read the stderr list. A `safe_sheets.py` read of `_LLM_GUIDE` satisfies `guard_sheet_writes.sh`.
- Metadata (tab list): `gws sheets spreadsheets get --params '{"spreadsheetId":"<ID>"}'`
- Append (normal write): `gws sheets spreadsheets values append --params '{...}'`
- In a runner, send stderr to a file (`2>"$TMP/gws.err"`), parse stdout only, read the file if the call fails;
  `2>/dev/null` is refused there (`canon/cron-jobs-sop.md` §7). `system/gws-contract.md` has the quoting and
  error-code patterns; see the Pointers section at the bottom.

## The workflow (any sheet build)
1. **Identify the sheet + read its `_LLM_GUIDE`** (satisfies `guard_sheet_writes`).
2. **Design to Principle #1** — push math into formulas / Apps Script; the LLM only orchestrates + folds.
3. **Append, don't overwrite** — never touch a formula/`🔒` cell without explicit confirm.
4. **Back up first** for any non-append change (`canon/build-conformance-sop.md` §5 item 3: back up a hand-edited file before changing it).
5. New sheet → use the `google-sheet` skill (Kickoff mode) so it's born conformant (`_LLM_GUIDE` tab
   opening with its **PURPOSE block** (#1a) + the **body guidelines** that apply (#1b), `🔒` headers,
   per-tab purpose lines, a `_LOG` tab (#3), and the **error sweep + `_CHECKS` self-check layer** (#4)).

## Formatting / "design" in a Sheet — the rules (from a blind `/research` convergence run, 2026-06-27)

> A spreadsheet is a **data grid, not a design canvas.** The lesson is NOT "never format" — it's: split
> the work by what the medium does well. Hard-won on a real billing dashboard — roughly ten rounds of
> blind thrashing before this was understood.

1. **The LOOK is a human/UI job; the API does data + narrow patches.** Style headers / colors / widths /
   layout **once, by hand in the Sheets UI** (instant visual feedback, nothing breaks). NEVER have the LLM
   rebuild a *look* from scratch via the API — that is the blind-iteration swamp (no live preview → you're
   guessing colors and breaking neighbors).
2. **When the API must touch format:** `spreadsheets.batchUpdate` + `repeatCell` / `updateBorders` with an
   **EXPLICIT field mask** (touch only the named sub-property; leave all else untouched). NEVER
   `values.batchUpdate` for formatting — it overwrites. Keep requests **small, single-range, idempotent**.
   **Capture-by-readback:** format one cell by hand, read its `userEnteredFormat` via `spreadsheets.get`,
   reuse it verbatim — don't hand-author format JSON.
3. **Hard limits to respect:** column width is **whole-column** (no per-cell — the coupling that fattens a
   neighboring table when you resize); format state is **additive**; there is **NO live preview**. To SEE a
   private sheet you must **publish-to-web first**, then render the public URL (it's a JS page → headless
   Chrome with `--virtual-time-budget` ~15s; `render_shot.sh` alone shoots blank). Un-publish when done.
4. **Reuse a look = copy a styled TAB or extract a Style Kit — never hand-redo.**
   - Cross-file, cleanest: **`sheets:copyTo`** copies a whole styled TAB into your file, carrying
     colors/fonts/borders/merges/**widths**/number-formats/conditional-formatting in ONE call. *(Caveat:
     row heights, protected ranges, named ranges do NOT come along — re-apply separately.)*
   - Reusable *skin* across many sheets: extract a **Style Kit** (palette + type + header-bar treatments)
     from a reference's `userEnteredFormat`, then apply those exact tokens to new sheets (deterministic).
   - **AVOID** "paste format only" onto an existing populated range — silently drops widths/heights/
     protections (3–4 passes + cleanup).
5. **The line (the documented regret pattern):** data-driven formatting (conditional formatting, set-once
   header styles) is reliable. Visual/layout **precision** is not what a spreadsheet is for → that goes to
   **HTML**, which renders instantly and has a real layout engine. ✅ `/design-lifehack` is built for
   HTML and not for Sheets — don't run the design swamp inside a grid.

## Pointers
- Craft (design/audit/tiers/controls): the `google-sheet` skill + `standards.md` / `capabilities.md`.
- The harness brief's "Arithmetic is computed, never done in your head" is what this applies; `/calculate` arms it for a whole session.
- Enforcement mechanics: `canon/hook-contract.md` and `canon/hook-sop.md`.
- `system/gws-contract.md` — the quoting and error-code patterns.
  Connecting your own account is `INSTALL.md` → "THE GOOGLE-CONNECTED PARTS"; the quoting and
  error-code patterns are visible in the commands throughout this page.

### Principle #2a — a check must test PRESENCE, not only agreement (completeness ≠ consistency)

**Principle #2 says the sheet proves its own math. This says: a missing input passes every math proof.** The
Fernwood Commons `Checks` tab scored a statement that had overbilled the tenant by $50 as **"15 PASS / 1 WARNING /
0 FAIL"** — because the carriage submeter cell was BLANK, and:
- `TS: Electricity — Whole = Carriage + Front` → `198.42 = 0 + 198.42` is arithmetically TRUE.
- `SM: carriage ELECTRIC ≤ FC total — ALL periods` → `0 ≤ 2071` is TRUE.

**A missing input is perfectly consistent with itself**, so every consistency check certifies it. Sheets also
coerce a blank to `0` inside arithmetic, which is exactly what turned "no data" into "the tenant owes everything."

**So every calculating sheet needs at least one COMPLETENESS check alongside its consistency checks:** for each
row that SHOULD have an input, assert the input is non-blank. Two shapes, and you usually want both:
1. **A BLOCKING check on the current period** — `✗`-prefixed so it trips the sheet's own green-light gate, making
   a bill/output with a missing input impossible to produce.
2. **A WARNING check across all history** — `⚠`-prefixed, NOT `✗`. Historical gaps are often legitimate and
   explained (a meter installed mid-period, a month with no invoice); a hard fail there blocks the sheet forever.

Use **open-ended ranges** (`A4:A`, `4:50`) not a hardcoded ceiling — an all-periods check that stops at row 13
silently ignores rows 14+ (the exact trap in the same tab). *(2026-06-09, FC tenant-billing misbill — property,
tenant detail, and dollar figures in this example are invented for anonymity, not the real incident's actual
specifics; do not "restore" them. The generalised guard-testing lesson — "never test a status string by
substring" — is in `build-sop.md` *(retired 2026-10-31)*.)*
