# Training Wheels — Safe-Default Presets by Complexity Tier

Pick your tier. Use the presets. You will not fail.

Every number here is grounded in `constraint-kit.md` — no invented values.  
These are blessed safe choices for a non-designer, not a complete design system.

---

## The Four Tiers

| Tier | What it is | Principles that apply | Reference files that load |
|---|---|---|---|
| **Applet** | A single-purpose tool: one screen, one job (calculator, timer, form, widget) | Foundation only: type scale, 8pt spacing, 1 accent, squint test | glossary, training-wheels |
| **Static page** | Read-only display: a report, a bio, a landing tile, a simple summary card | Foundation + IA basics: hierarchy, labels, contrast | glossary, training-wheels |
| **Functional page** | Interactive: a settings page, a form flow, a detail view with actions | Foundation + interaction: affordances, loading/error states, IA | glossary, training-wheels, constraint-kit §B–C |
| **Dashboard** | Data-dense, read-or-act: multiple cards, multiple metrics, decision support | Full treatment: tile-tiering, all 7 lenses, full constraint-kit | all references |

> **The tier also gates the skill's depth.** An applet gets the foundations and the training-wheel preset — no 7-lens pass, no FRESH-EYES, no tile-tiering. A dashboard earns the full treatment. Declare or infer the tier at the start of every run.

---

## Tier 1 — Applet

**Blessed type scale (pick one, use it consistently):**
- Body: 14px / Regular
- Label: 12px / Medium
- Heading: 22px / Semibold
- Heading:body ratio: 22/14 = 1.57× ✓

**Spacing steps to use:** 8px · 16px · 24px (three steps is enough for one screen)

**Color rule:** 1 neutral background + 1 surface color + 1 accent. No more.

**Layout:** single column or two columns max. No grid complexity needed.

**Must-do:**
- Squint test before done: does the primary action or primary value visually lead?
- Labels in plain English: no acronyms, no abbreviations.
- One accent color. State its one job (CTA / primary action / brand mark).

**Must-not:**
- Don't use a chart for ≤3 data points. Use a number.
- Don't add a second accent color "for variety."
- Don't nest more than 2 levels of information.

---

## Tier 2 — Static Page

**Blessed type scale:**
- Body: 16px / Regular
- Label / caption: 12px / Medium
- Subheading: 20px / Semibold
- Heading: 28px / Bold
- Heading:body ratio: 28/16 = 1.75× ✓

**Spacing steps to use:** 8px · 16px · 24px · 32px

**Color rule:** 1 neutral background + 1–2 surface levels + 1 accent. Alternate surface levels to break monotony (constraint-kit B2 — never two identical surface levels in consecutive bands).

**Layout skeleton options (pick one):**
- Single column, max 680px content width (readable long-form)
- Two-column: 2/3 main + 1/3 sidebar (classic editorial split)

**Must-do:**
- Visual hierarchy: heading → subheading → body, each a distinct size jump.
- Contrast: check text-to-background ≥4.5:1 for body text.
- One section / one job: each block answers one question.

**Must-not:**
- Don't use more than 2 type weights (Regular + Semibold or Bold).
- Don't ship default gray text on white without checking contrast.
- Don't put two things side-by-side that the reader needs to compare — show both in the same flow.

---

## Tier 3 — Functional Page (interactive)

**Blessed type scale:** same as Tier 2 + one size for form labels (14px / Medium).

**Spacing steps to use:** 8px · 16px · 24px · 32px · 48px

**Color rule:** same as Tier 2 + one functional state color (error = red; success = green). Each state color: icon + label + color — never color alone.

**Layout skeletons (pick one):**
- Form: single column, 480–600px max width, left-aligned labels
- Settings: two-column with nav sidebar (nav = 240px; content = fluid)
- Detail view: hero zone (full width) + content sections below

**Must-do:**
- Every interactive element looks interactive: buttons have visible bounds; links are distinguishable from body text.
- Every state defined: loading (spinner or skeleton), empty (message), error (plain-English message + what to do).
- Group related fields: label-to-value spacing = 1 unit; group-to-group spacing = 2 units (constraint-kit A4).

**Must-not:**
- Don't use flat unstyled rectangles as buttons.
- Don't leave an error state as just a red border — add a text message.
- Don't use tabs when the user needs to see two sections simultaneously to complete a task.

---

## Tier 4 — Dashboard

Use the full `constraint-kit.md` — all sections A through F.

**Baseline safe choices (in addition to the kit):**

**Type scale:**
- KPI number: 32–40px / Bold
- KPI label: 12px / Medium, uppercase or sentence case (pick one — never mix)
- Card title: 16px / Semibold
- Body / secondary text: 14px / Regular
- Caption / timestamp: 12px / Regular

**Spacing:** 8pt grid throughout. Card internal padding: 1×1 tile = 16px; 2×1 tile = 24px; 2×2 tile = 32px (constraint-kit A4).

**Grid:** 12 columns, 16px gutters, 24px container padding (constraint-kit A2).

**Tile-class layout skeleton (constraint-kit A1):**
```
[ Hero  ·  Hero      ] [ Feature  ] [ Feature  ]
[ Metric ] [ Metric ] [ Metric ] [ Metric ]
[ Accent ] [ Accent ] [ Accent ] [ Accent ] [ Accent ]
```
- Hero: max 2 per view, 4–6 cols × 2 rows
- Feature: 3–4 cols × 1–2 rows
- Metric: 2–3 cols × 1 row
- Accent: 1–2 cols × 1 row

**Must-do:**
- Tier tiles BEFORE laying out (size = priority, not content volume).
- Run the squint test: blur the render — does ONE element lead?
- Snap every dimension to 8pt scale.
- Walk constraint-kit §E (Don'ts) as a checklist before done.

**Must-not (constraint-kit §E):**
- Don't size a tile to its content — size to priority.
- Don't pad an orphan box with filler — resize or center it.
- Don't use border AND shadow at the same elevation.
- Don't bury scannable numbers behind tabs.
- Don't ship default chart styles or pies >3 slices.
- Don't introduce a second accent color.
