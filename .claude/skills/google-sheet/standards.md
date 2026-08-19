---
topic: [google-sheets]
type: skill-support
title: Google Sheet Standards
skill: google-sheet
version: 1.0
created_at: 2026-04-02
status: active
---

# Google Sheet Standards

This file is the authority on what is required versus recommended versus context-specific for any workbook designed or audited by the `/google-sheet` skill. Every rule is explicitly labeled. Nothing unlabeled should be treated as universal.

---

## Universal Principles

Three rules apply to every workbook, regardless of type, tier, complexity, or user. Violating any of them creates a correctness or usability problem.

**1. One source of truth per fact.**
Derived values derive. No fact is manually re-entered in a second location. If a value appears in two places, one derives from the other — or one is wrong.

**2. What to enter vs. what is calculated must be distinguishable.**
A user must be able to tell which cells accept input and which cells contain formulas. The exact treatment is a workbook-specific design choice (formatting, placement, protection, notes). The requirement to distinguish is not.

**3. Status and error states communicate with text, not color alone — when they exist.**
Color may supplement; it cannot be the only signal. A red cell with no text label is not a valid status indicator. A cell reading "✗ ERROR — [description]" with or without color is. This rule has no application to workbooks that have no status or error states.

---

## What Is Not Universal

These are frequently mistaken for universal rules. They are not. Each is labeled with what it actually is.

| Rule | Classification |
|---|---|
| Explicit tab map with declared roles | Tier-2 default. Required at Tier 3. Not applicable at Tier 1 (single-tab). |
| Tab-level purpose statement (A1) | Tier-2 default. Required at Tier 3. One sentence inserted as a new row 1 above all headers and data — why this tab exists, written for a user returning after months with no memory. Do not overwrite existing row 1; insert a row and push everything down. |
| README tab | Recommended at Tier 2. Required at Tier 3. Not expected at Tier 1. |
| Frozen header rows | Strong default at Tier 2+. Not always applicable (e.g., small static reference table with no scrolling need). |
| Internal visual consistency across tabs | Design goal. Its absence is a UX issue, not a correctness issue. Not a universal rule. |
| Named ranges | High-value default at Tier 2+ for frequently-referenced ranges. Not required. |
| 🔒 header prefix on formula columns | Tier-2 default. Required at Tier 3. Prefix any formula-only column header with `🔒` — e.g., `🔒 suggested_entity`. Absence of prefix means the column accepts input. This is the primary LLM write guard — co-located with the data, impossible to miss even if orientation docs aren't loaded. |
| Protected formula ranges | Tier-3 default when multiple users may edit. At Tier 3, combine with `🔒` headers: headers block LLMs, protection blocks humans in the UI. Two attack surfaces, two solutions. |
| Dedicated checks area | Required at Tier 3. Conditional at Tier 2 (see Internal Controls below). Not expected at Tier 1. |

---

## Complexity Tier Definitions

Score 1 point for each:
- More than one distinct data domain (multiple entity types tracked)
- More than one person uses or modifies the workbook
- An error in this workbook could cause a real downstream problem
- The workbook will be extended by others after initial build
- Known drift risk: stale data, manual updates that may be missed

**Tier 1 (0–1 points):** Lightweight. One user, low stakes, low complexity. Minimal controls. Output is a brief paragraph.

**Tier 2 (2–3 points):** Standard. Multi-domain or collaborative or meaningful stakes. Structured spec. Built-in controls where warranted.

**Tier 3 (4–5 points):** Governed. High complexity, high stakes, multi-user, or drift-prone. Full spec. Dedicated control layer. README required.

---

## Internal Control Requirements by Tier

**Tier 1:**
- Input validation: consider when invalid inputs would silently corrupt derived values. Not mandatory everywhere — apply the anti-overbuild test.
- No summary status area expected. No dedicated checks area expected.
- Anti-overbuild test: would a reasonably careful user notice this failure without the check? If yes, skip it.

**Tier 2:**
- Data validation on input fields with constrained valid values — required when invalid inputs silently corrupt derived values.
- Meaningful controls when the workbook has multi-step calculation chains, constrained inputs, or identified silent-failure risk. This is the trigger, not a blanket rule.
- If multi-step chains are present: inline status cells and at least one reconciliation check on the most critical path are the expected pattern. If the workbook is structurally simple enough that these add no real value, omit them.
- Summary status area when the number of active checks justifies one.
- Stale data check if the workbook has time-sensitive inputs.
- All check statuses: text-based, actionable.

**Tier 3:**
- Everything from Tier 2 (enforced, not conditional).
- Dedicated checks tab (default name: `_CHECKS`) as a first-class component. A tab is required rather than an in-tab area because a tab is structurally detectable during Audit; an in-tab control area is not.
- Checks organized by type: input validation / transformation verification / reconciliation / stale data / output reasonableness.
- Each check row: name, type, live formula status, what it checks, action guidance on failure.
- Reasonableness bounds on final outputs where those bounds can be defined.
- Multiple escalation levels: inline → summary area → dedicated checks tab.
- All status cells are live formulas. Nothing is manually updated.

**Anti-overbuild test (all tiers):**
A check is only worth adding if all three are true:
1. The failure mode is silent — it wouldn't be obvious without the check.
2. The failure mode would meaningfully affect reliability or a real decision.
3. The check can be implemented without formula complexity that creates its own maintenance risk.

**Failure visibility rule (all tiers where checks exist):**
Internal control formulas must fail visibly. IFERROR should handle only known-null states, never unexpected errors. A reconciliation check wrapped in IFERROR that returns "OK" on a broken formula is worse than no check — it provides false confidence. If a check formula cannot be written to fail visibly, it should not be added.

---

## Design Token Schema

Every workbook must resolve these visual decision categories at spec time. The schema names the categories — it does not specify values. Values are workbook-specific.

| Token Category | What It Governs |
|---|---|
| Header treatment | Background, text weight/color, border for header rows |
| Input cell treatment | Fill or indicator that distinguishes manual-entry cells |
| Formula cell treatment | Fill or formatting for calculated cells (often: no fill, or protected) |
| Status states | Visual treatment for OK / WARNING / ERROR states — must include text |
| Section divider | Visual pattern for separating logical sections within a tab |
| Number format | Consistent format for numeric values (commas, decimals) |
| Date format | Consistent format for dates |
| Currency format | Consistent format for currency values |

At Tier 1: resolve informally. At Tier 2: note the key choices in the spec. At Tier 3: document the token values in the README tab so future editors can stay consistent.

---

## Must-Not-Contain (this file)

This standards file must never contain:
- Color hex values or specific font names
- Tab naming conventions
- Domain-specific rules of any kind
- Any rule framed as "always" that is not one of the three universal principles
- Anything that could be described as a house style
