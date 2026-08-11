---
topic: [google-sheets]
type: skill-support
title: Google Sheet Capabilities Directory
skill: google-sheet
version: 1.0
created_at: 2026-04-02
status: active
---

# Google Sheet Capabilities Directory

## Purpose and Use

This file is a recall aid and architecture pressure-test. It is consulted **after** a workbook architecture has been designed from first principles — never before. Its job is to surface better Sheets-native solutions for identified design problems, and to prevent satisficing (stopping at the first adequate approach).

**Core discipline rule:** Absence of a feature is not a defect unless its absence creates a meaningful quality gap. The question is never "what features are missing?" It is: "is anything missing that would meaningfully improve correctness, usability, or durability?"

This directory is intentionally small. Fewer high-signal entries are more useful than a broad list that becomes diffuse. Every entry passes the three-question test:
1. What problem does this feature solve?
2. When is it the right choice over simpler alternatives?
3. What are its key limitations or failure modes?

Entries that cannot answer all three clearly are not included.

---

## 1. Data Integrity

**Data validation**
- *Solves:* Prevents invalid inputs from entering the workbook and silently corrupting derived values.
- *Right choice when:* A field has a defined set of valid values (dropdown), a numeric range, or a pattern that, if violated, would propagate undetected into formulas. Also valuable for enforcing consistent spelling across a category column.
- *Limitations:* Does not catch logically invalid inputs that are syntactically valid (e.g., a date that is valid but before the project start). Custom formula validation is powerful but harder to maintain. Help text (available in validation settings) is underused and highly valuable — it explains to the user what is expected.

**Protected ranges**
- *Solves:* Prevents formula cells from being accidentally overwritten.
- *Right choice when:* Multiple users edit the workbook, or when the risk of accidentally typing into a formula cell would be costly. Also appropriate for reference data tabs that should not be edited casually.
- *Limitations:* Adds friction for legitimate edits. Best applied selectively to formula columns and reference tabs, not to the entire workbook. Overprotecting reduces usability.

---

## 2. Dynamic vs. Static Formulas

**ARRAYFORMULA**
- *Solves:* Eliminates row-by-row formula copying. One formula in the header row applies to the entire column, including new rows added later.
- *Right choice when:* A column applies the same transformation to every row. Without ARRAYFORMULA, the workbook requires manually extending formulas to new rows — a common source of drift.
- *Limitations:* Cannot be used with functions that do not support array input (some aggregation functions, some text functions). Debugging is harder. If the formula is complex, row-by-row may be more maintainable.

**FILTER / SORT / UNIQUE**
- *Solves:* Dynamic list generation without pivot tables or manual maintenance. FILTER extracts rows matching a condition. SORT returns a sorted array. UNIQUE returns deduplicated values.
- *Right choice when:* A summary or derived view needs to update automatically as source data changes. Replaces manual copy-paste workflows that create stale derived lists.
- *Limitations:* Results spill into adjacent cells — adjacent cells must be empty or the formula errors. Not compatible with manual formatting of individual result rows.

**QUERY**
- *Solves:* Complex multi-condition filtering and aggregation using SQL-like syntax. Can replace combinations of FILTER + SUMIF.
- *Right choice when:* The aggregation logic is complex enough that SUMIF/FILTER combinations become hard to read. Also useful for pulling a subset of columns from a data range.
- *Limitations:* SQL-like syntax has a learning curve and is harder for others to maintain. Column references use letter notation (Col1, Col2) which breaks if columns are reordered. Use when simplicity of the query logic justifies the syntax overhead.

---

## 3. Lookup and Reference

**VLOOKUP**
- *Solves:* Lookup a value in the leftmost column of a range and return a value from another column.
- *Right choice when:* The lookup column is the leftmost column and will stay that way. Legacy workbooks commonly use it.
- *Limitations:* Only works left-to-right. Fragile to column reordering. Returns the first match only. Superseded by XLOOKUP in most cases.

**INDEX / MATCH**
- *Solves:* Flexible lookup in any direction. MATCH finds the position; INDEX returns the value at that position.
- *Right choice when:* The lookup column is not leftmost, or when column order may change.
- *Limitations:* Two-function syntax is more verbose. Still requires knowing which column to return.

**XLOOKUP**
- *Solves:* Modern replacement for both VLOOKUP and INDEX/MATCH. Bidirectional, supports a fallback value for no-match cases, returns an array of columns if needed.
- *Right choice when:* Starting a new workbook. Handles all VLOOKUP use cases and most INDEX/MATCH use cases with simpler syntax.
- *Limitations:* Not available in older Excel versions (relevant only if the workbook may be used in Excel). No limitation within Google Sheets.

**Named ranges**
- *Solves:* Self-documenting references. A formula reading `=SUMIF(Category, "Food", Amount)` is clearer than `=SUMIF(D:D, "Food", F:F)`.
- *Right choice when:* A range is referenced from multiple formulas, or when the formula logic benefits from readable names. Particularly valuable in Tier 3 workbooks where future editors need to understand cross-tab dependencies.
- *Limitations:* Named ranges are global to the workbook — name conflicts can occur. Must be updated if the source range changes. Not worth adding for ranges referenced only once.

---

## 4. Aggregation and Summarization

**SUMIF / SUMIFS / COUNTIF / COUNTIFS**
- *Solves:* Conditional aggregation. Sum or count rows matching one or more criteria.
- *Right choice when:* Summary calculations depend on category, status, or date conditions. The workbook needs conditional totals without a pivot table.
- *Limitations:* Formula-per-condition — a summary with 10 categories requires 10 SUMIF formulas. SUMIFS handles multiple conditions in one formula.

**Pivot tables**
- *Solves:* Interactive cross-tabulation and summarization. Can aggregate the same data multiple ways without modifying the underlying data.
- *Right choice when:* The user needs to explore the data from multiple angles, or when the category structure is too variable to hard-code in SUMIF formulas. Also when the person maintaining the workbook is comfortable with pivot tables.
- *Limitations:* Must be manually refreshed (or configured to auto-refresh). Formatting can be lost on refresh. Do not use just to avoid writing SUMIF formulas — if the category structure is stable, SUMIF grids are more maintainable.

---

## 5. Internal Controls and Verification

**Inline status cells**
- *Solves:* Surfaces calculation problems at the point where they occur, in real time. A cell showing "✗ MISMATCH — Categories sum ($4,640) ≠ Summary total ($4,820). Diff: $180" is detected before the user relies on the wrong output.
- *Right choice when:* A key calculated value could silently be wrong due to a formula error, a broken reference, or a reconciliation failure. The status cell sits adjacent to the output it is checking.
- *Implementation:* `=IF(ABS(B12-SUM(Categories!D:D))>0.01, "✗ MISMATCH — " & TEXT(B12,"$#,##0") & " ≠ " & TEXT(SUM(Categories!D:D),"$#,##0"), "✓ OK")`. The formula must produce a meaningful text description of the failure, not just a flag.
- *Failure visibility rule:* Do not wrap in IFERROR unless handling a known-null state. An IFERROR that silently returns "OK" when the formula is broken provides false confidence. Let unexpected errors surface.

**Reconciliation checks**
- *Solves:* Catches the most dangerous silent failure: two independent paths that should agree but don't. A categories breakdown that sums to a different total than the summary view looks fine locally in both places.
- *Right choice when:* The workbook has two semi-independent calculation paths that should produce agreeing values. This is the most important check type — it catches errors that would otherwise require deliberate auditing to find.
- *Implementation:* Cross-tab reference comparing two computed values, with a tolerance for floating-point rounding. Surface as a status cell or check row with the difference amount.
- *Limitations:* Requires two independent paths to exist. If the "reconciliation" is just a value compared to itself through a chain, it is not a real reconciliation check.

**Stale data detection**
- *Solves:* Flags when time-sensitive inputs haven't been updated.
- *Right choice when:* The workbook has periodic manual inputs (monthly updates, weekly snapshots) where a missed update would cause the workbook to silently report stale data.
- *Implementation:* Compare a "last updated" date cell against `TODAY()`. Surface a WARNING if the gap exceeds the expected refresh interval. `=IF(TODAY()-B2>30, "⚠ STALE — Last updated " & TEXT(B2,"MMM D") & ". Update expected monthly.", "✓ Current")`

**IFERROR — correct vs. incorrect use**
- *Right use:* Handle known-null states gracefully. A lookup that returns #N/A for rows where no match exists yet can be wrapped in IFERROR to show blank or "—" instead.
- *Wrong use:* Suppressing unexpected errors. `=IFERROR(formula, "OK")` on a check cell defeats the purpose of the check. Use IFERROR only when #N/A or blank is a legitimate expected state, not as error suppression.

**Conditional formatting as anomaly detector**
- *Solves:* Makes data anomalies visible at a glance without requiring the user to look for them.
- *Right choice when:* A column has values where out-of-range is meaningful (negative values in a field that should always be positive, percentages above 100%, amounts far outside historical range). The formatting highlights the anomaly; the user decides what to do.
- *Limitations:* Color-only formatting violates the text-label rule for status states. Use conditional formatting to draw attention, but pair it with a status cell or note for anything actionable.

---

## What This Directory Does Not Contain

- Complete formula templates or copy-paste code. Brief illustrative fragments appear in some entries to clarify a pattern — these are decision aids, not implementations to copy verbatim.
- Aesthetic guidance (colors, fonts, spacing)
- "Always use X" rules
- Features that serve no purpose in workbook design (charts, scripts, add-ons, macros)
- Entries that cannot pass the three-question test
