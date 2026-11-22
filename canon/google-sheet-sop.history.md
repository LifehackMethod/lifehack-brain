# Google Sheet SOP — history

> **History file — archived text, not live guidance.** Created 2026-11-14 (fine-china edit pass, round three
> 'lowerbooks'). Each passage below was moved word for word out of `canon/google-sheet-sop.md` (Batch 4 item 3: retired and
> struck text goes to history, never deleted). Line numbers are those of the frozen copy
> `freeze-2026-11-14/google-sheet-sop.2026-11-14.md`. Read the live file for what is true today.

## G2-76 · moved 2026-11-14 · frozen L29-30

Reason: struck wording and the 2026-10-30 heading-rename note (Batch 4 item 3); the live line points at the harness brief's "Arithmetic is computed, never done in your head".

````
This is the sheets application of the cross-desk rule in `CLAUDE.md` → ~~*"Compute mechanically, never in
the model."*~~ *"Arithmetic is computed, never done in your head"* *(2026-10-30: heading renamed; see CLAUDE.md, "Arithmetic is computed, never done in your head")* (Narrow exception: a summary tier a person has explicitly approved for a specific sheet.)
````

## G2-83 · moved 2026-11-14 · frozen L182-183

Reason: the struck raw `values get` command and the 2026-10-30 open-gap note, fixed in code (guard_sheet_writes.sh L124-132, 0e7e214, 2026-11-03) (K26; Batch 4 item 3).

````
- Read: ~~`gws sheets spreadsheets values get --params '{"spreadsheetId":"<ID>","range":"_LLM_GUIDE!A:Z"}'`~~ *(2026-10-30: a raw `values get` is refused — `ingest_gate_enforce.sh` blocks it in a session and the job door blocks it in a runner, `cron-jobs-sop.md` §7.)* The allowed way: `python3 <repo>/system/tools/safe_sheets.py <spreadsheet-id> '_LLM_GUIDE!A:Z'` — it sanitizes every cell, scans for injection and fails closed; exit 1 means spans were flagged and neutralised, so read the stderr list.
  ⚠ *Open gap (2026-10-30, read from `guard_sheet_writes.sh:143-148`, not fire-tested):* that guard records its "this window read the guide" marker only from a command shaped like `gws sheets ... values get`, which the door refuses, so a write after a `safe_sheets.py` read may still be asked to read the guide first. Unresolved; it belongs to the guard, not this page.
````

## G2-84 · moved 2026-11-14 · frozen L186-187

Reason: struck `2>/dev/null` advice and its 2026-10-30 correction, restated plainly in the live file (Batch 4 item 3).

````
- ~~Always `2>/dev/null` when parsing gws JSON — it writes progress chatter there and it will corrupt
  your parse.~~ *(2026-10-30: never silence a fetch, write or push in a runner — `cron-jobs-sop.md` §7 refuses `2>/dev/null` there, and an error you cannot see reads as "nothing new". The allowed way: send stderr to a file, `2>"$TMP/gws.err"`, parse stdout only, and read the file if the call fails.)* `system/gws-contract.md` has the quoting and error-code patterns; see the Pointers section at the bottom.
````

## G2-88 · moved 2026-11-14 · frozen L234-234

Reason: struck 'does NOT ship' line and the version-pin note; the pin was dropped from gws-contract (G2-19) (Batch 4 item 3).

````
- ~~⛔ `system/gws-contract.md` does NOT ship.~~ *(2026-10-30: the file IS in this repo, `system/gws-contract.md`, frontmatter `gws_version: 0.22.3`.)* ⚠ It pins one `gws` version, which is the opposite of what these hooks now do (`command -v gws`, no version assumption), so read it for the quoting and error-code patterns, not for the install path or version.
````

## 2026-11-14 - reason: round three lowerbooks 2026-11-14, approved screen: G2-76 G2-77 G2-78 G2-79 G2-80 G2-81 G2-82 G2-83 G2-84 G2-85 G2-88 (see drafts/google-sheet-sop.applied.md)

~~~~
This is the sheets application of the cross-desk rule in `CLAUDE.md` → ~~*"Compute mechanically, never in
the model."*~~ *"Arithmetic is computed, never done in your head"* *(2026-10-30: heading renamed; see CLAUDE.md, "Arithmetic is computed, never done in your head")* (Narrow exception: a summary tier a person has explicitly approved for a specific sheet.)
~~~~

## 2026-11-14 - reason: round three lowerbooks 2026-11-14, approved screen: G2-76 G2-77 G2-78 G2-79 G2-80 G2-81 G2-82 G2-83 G2-84 G2-85 G2-88 (see drafts/google-sheet-sop.applied.md)

~~~~
applied to every workbook: *it can't be quietly wrong.* Two non-negotiables:
~~~~

## 2026-11-14 - reason: round three lowerbooks 2026-11-14, approved screen: G2-76 G2-77 G2-78 G2-79 G2-80 G2-81 G2-82 G2-83 G2-84 G2-85 G2-88 (see drafts/google-sheet-sop.applied.md)

~~~~
the next appended row comes up blank. **Rule: write ONLY the columns you actually changed** — a menu script
~~~~

## 2026-11-14 - reason: round three lowerbooks 2026-11-14, approved screen: G2-76 G2-77 G2-78 G2-79 G2-80 G2-81 G2-82 G2-83 G2-84 G2-85 G2-88 (see drafts/google-sheet-sop.applied.md)

~~~~
  stamp each transaction's owner from the card-last4→owner map — don't make a session join by last-4. But the
  rule is general: any sheet whose rows are typed/owned/classified from a lookup gets the computed column.)*
~~~~

## 2026-11-14 - reason: round three lowerbooks 2026-11-14, approved screen: G2-76 G2-77 G2-78 G2-79 G2-80 G2-81 G2-82 G2-83 G2-84 G2-85 G2-88 (see drafts/google-sheet-sop.applied.md)

~~~~
  **is a formula (`=…`) or carries `🔒`** — un-fakeable, works even on unlabeled formula cells.
- The two are complementary: 🔒 signals to a human; the formula-value check is the enforcement.
~~~~

## 2026-11-14 - reason: round three lowerbooks 2026-11-14, approved screen: G2-76 G2-77 G2-78 G2-79 G2-80 G2-81 G2-82 G2-83 G2-84 G2-85 G2-88 (see drafts/google-sheet-sop.applied.md)

~~~~
- **Prefer open-ended ranges over hardcoded ceilings (design rule).** Use `A4:A` / whole-column / dynamic
~~~~

## 2026-11-14 - reason: round three lowerbooks 2026-11-14, approved screen: G2-76 G2-77 G2-78 G2-79 G2-80 G2-81 G2-82 G2-83 G2-84 G2-85 G2-88 (see drafts/google-sheet-sop.applied.md)

~~~~
## The enforcement layer (the hooks — `system/hooks/`)
~~~~

## 2026-11-14 - reason: round three lowerbooks 2026-11-14, approved screen: G2-76 G2-77 G2-78 G2-79 G2-80 G2-81 G2-82 G2-83 G2-84 G2-85 G2-88 (see drafts/google-sheet-sop.applied.md)

~~~~
- Read: ~~`gws sheets spreadsheets values get --params '{"spreadsheetId":"<ID>","range":"_LLM_GUIDE!A:Z"}'`~~ *(2026-10-30: a raw `values get` is refused — `ingest_gate_enforce.sh` blocks it in a session and the job door blocks it in a runner, `cron-jobs-sop.md` §7.)* The allowed way: `python3 <repo>/system/tools/safe_sheets.py <spreadsheet-id> '_LLM_GUIDE!A:Z'` — it sanitizes every cell, scans for injection and fails closed; exit 1 means spans were flagged and neutralised, so read the stderr list.
  ⚠ *Open gap (2026-10-30, read from `guard_sheet_writes.sh:143-148`, not fire-tested):* that guard records its "this window read the guide" marker only from a command shaped like `gws sheets ... values get`, which the door refuses, so a write after a `safe_sheets.py` read may still be asked to read the guide first. Unresolved; it belongs to the guard, not this page.
~~~~

## 2026-11-14 - reason: round three lowerbooks 2026-11-14, approved screen: G2-76 G2-77 G2-78 G2-79 G2-80 G2-81 G2-82 G2-83 G2-84 G2-85 G2-88 (see drafts/google-sheet-sop.applied.md)

~~~~
- ~~Always `2>/dev/null` when parsing gws JSON — it writes progress chatter there and it will corrupt
  your parse.~~ *(2026-10-30: never silence a fetch, write or push in a runner — `cron-jobs-sop.md` §7 refuses `2>/dev/null` there, and an error you cannot see reads as "nothing new". The allowed way: send stderr to a file, `2>"$TMP/gws.err"`, parse stdout only, and read the file if the call fails.)* `system/gws-contract.md` has the quoting and error-code patterns; see the Pointers section at the bottom.
~~~~

## 2026-11-14 - reason: round three lowerbooks 2026-11-14, approved screen: G2-76 G2-77 G2-78 G2-79 G2-80 G2-81 G2-82 G2-83 G2-84 G2-85 G2-88 (see drafts/google-sheet-sop.applied.md)

~~~~
4. **Back up first** for any non-append change (build-sop *(retired 2026-10-31)*: crown-jewel backup before editing).
~~~~

## 2026-11-14 - reason: round three lowerbooks 2026-11-14, approved screen: G2-76 G2-77 G2-78 G2-79 G2-80 G2-81 G2-82 G2-83 G2-84 G2-85 G2-88 (see drafts/google-sheet-sop.applied.md)

~~~~
- The law this is one application of: compute mechanically, never in the model. `/calculate` arms it for a whole session.
~~~~

## 2026-11-14 - reason: round three lowerbooks 2026-11-14, approved screen: G2-76 G2-77 G2-78 G2-79 G2-80 G2-81 G2-82 G2-83 G2-84 G2-85 G2-88 (see drafts/google-sheet-sop.applied.md)

~~~~
- ~~⛔ `system/gws-contract.md` does NOT ship.~~ *(2026-10-30: the file IS in this repo, `system/gws-contract.md`, frontmatter `gws_version: 0.22.3`.)* ⚠ It pins one `gws` version, which is the opposite of what these hooks now do (`command -v gws`, no version assumption), so read it for the quoting and error-code patterns, not for the install path or version.
~~~~
