# Constraint Kit — what "good" looks like

The ground truth `design-claudeops` checks against (critique) and builds from (build).
The skill **applies** these rules — it does not re-derive them. Container format stolen
from the DESIGN.md spec (Google Stitch; ~70 shipped brand specs converged on it). The
**Layout & IA** cargo (section A) is ours — that section is empty in all 73 brand specs,
and it's the last mile nothing else closes.

**Two profiles.** DASHBOARD = data-dense, read-or-act (default for our work).
MARKETING = hero/landing. Where they differ, both values are given; otherwise the rule holds for both.

**Every rule below is falsifiable.** In critique, a violated rule is a finding. In build, an
unmet rule is a to-do. Don't soften them into vibes.

---

## The spec skeleton (the container — fill/check in this order)

`Overview · Colors · Typography · Layout & IA · Elevation · Shapes · Components · Do's & Don'ts · Responsive · Known Gaps`

- Carry values as named tokens (`spacing.md = 16px`, `color.accent = …`) and reference them everywhere — one source of truth, consistent by construction.
- **Known Gaps is mandatory:** end every spec/critique with what you did NOT cover or could not verify. Silence reads as false coverage.

---

## A. Layout & Information Architecture — the cargo (do this part first)

### A1. Tile-tiering — BEFORE any layout (the one decision nothing automates)
Tier every card by the **5-second question** the view answers. **Size = priority, never content volume** (sizing a tile to fit its content is the root cause of dead space).

| Tier | Span (12-col) | Count | Holds |
|---|---|---|---|
| Hero | 4–6 cols × 2 rows | **max 1–2** per screen | the headline metric / primary chart |
| Feature | 3–4 cols × 1–2 rows | a few | supporting charts, key groups |
| Metric | 2–3 cols × 1 row | several | single KPI + its comparison |
| Accent | 1–2 cols × 1 row | filler | small stat, status, link |

A 3rd hero cancels the others — the eye loses its anchor.

### A2. The grid
- **12 columns** (divisible by 2/3/4/6 → spans always tile evenly; no orphan fractional columns). Not 6.
- Gutters **16–24px** (default 16), container padding **24px**. Below ~8px tiles merge; above ~32px they read as scattered islands.

### A3. Kill dead space / orphan boxes
- **Cap 6–12 boxes** per view, **5–7 primary metrics** (working-memory limit). More → orphans + chaos become unavoidable.
- A literal orphan (lone last box): **make it bigger (span the remaining width) or center it — never pad it with filler.** Auto-stretching reads as "important"; if it isn't, center it instead.
- Variable/dynamic card counts → `grid-auto-flow: dense` (browser backfills gaps).
- Balance by **visual weight, not mirrored size** — one large light tile is counterbalanced by a cluster of small dense/dark ones.

### A4. Spacing
- **8-point scale** (8/16/24/32/48…); 4-pt allowed for dense dashboards. **No arbitrary 13px/17px.** Inconsistent spacing is the #1 "amateur" tell — above color, above fonts.
- **Tight within, double between:** label↔value = 1 unit; group↔group = 2× — clustering without borders.
- **Internal card padding scales with card size:** 1×1 = 16–20px · 2×1 = 20–24px · 2×2 = 24–32px. Bigger cards get breathing room, not more crammed content.

### A5. Density & progressive disclosure
- **Architecture:** overview → zoom/filter → details-on-demand (Shneiderman). Card shows the KPI; detail lives one interaction deeper.
- **Two levels max.** 3+ levels of nesting → regroup, don't nest.
- **Tabs:** 3–5 ideal, **hard max 6**. Beyond → sidebar / "More" / split into cards.
- **Comparison test:** if the user must see two sections at once to compare → **never tabs**; show both.
- **Control-by-shape:** tabs = few long parallel sections · accordions = many short items / mobile · segmented control = alternate VIEWS of the same data (list/grid, Today/Week) · wizard = sequential steps.
- For metric cards, **don't bury numbers behind tabs** — use expandable panels; reserve tabs for filtering by source.
- Tufte counterweight: most dashboards are too *sparse*. Fix clutter by removing non-data ink, **not** by removing data.

### A6. Self-balancing layout — so one card change doesn't break the whole grid
The goal: tweak / add / remove a card and the grid re-balances itself, **no per-card hand-tuning**.
- **Size by CLASS, not per-instance.** Three span classes only — `hero` / `feature` / `metric` (they map straight to the A1 tiers). Change a card's *class*, never a bespoke per-card span. Per-instance spans are the root cause of "I moved one card and the whole balance shifted."
- **Tokens are the single knob.** Carry `--card-min`, `--gap`, `--radius`, and the spacing steps as CSS custom properties at `:root`; every rule references them. One value change rebalances globally — one source of truth, consistent by construction.
- **Intrinsic outer grid:** `grid-template-columns: repeat(auto-fit, minmax(min(var(--card-min), 100%), 1fr))` — columns re-flow automatically as cards come and go. Use **`auto-fit`** (collapses empty tracks), never `auto-fill`. The `min(…, 100%)` wrapper prevents overflow on narrow screens.
- **Container queries for the INSIDE of a card.** `@container` (Baseline Aug 2025): a card adapts its own internal layout (row ↔ stack) to its rendered width, blind to the rest of the grid. Composes with the intrinsic outer grid — they aren't alternatives.
- **Fluid, not jumpy:** `clamp()` on `gap` / `padding` / `font-size` scales continuously (no breakpoint snap). Inside a container-query context use **`cqi`** units, not `vw` (`vw` ignores the card's actual slot width).
- **`subgrid`** (Baseline 2023) aligns title/body/footer across cards in a row; **`aspect-ratio`** holds card/image proportions through reflow.
- **Gotchas (falsifiable):** `grid-auto-flow: dense` backfills holes but **desyncs tab-order from visual order** — only use it when cards are equal semantic priority (a11y; ties to L7). Last-row orphan: **resize or center, never pad** (A3). For *designed* hierarchy (bento, Apple/Stripe style), prefer **fixed 12-col + explicit span-classes** over pure auto-placement — auto-placement is for user-configurable dashboards, not curated layouts.

---

## B. Universal craft rules (recur across ~70 shipped specs — guaranteed wins)

- **B1. Accent scarcity.** ONE accent. State its allowed roles (CTA / focus / link / brand mark) and a budget — "**appears here, nowhere else, max N per viewport.**" Accent-as-decoration is the violation.
- **B2. Surface-mode ladder + alternation.** Define 2–4 named surface levels (canvas → surface-1 → surface-2 …). **Never two of the same mode in consecutive bands/sections** — the alternation IS the pacing, and it's the cheapest anti-monotony / anti-dead-space rule.
- **B3. ONE elevation signal, named.** Depth = surface-color step **OR** border/hairline **OR** shadow — pick one doctrine and state it. High-craft systems (Linear, IBM/Carbon, Vercel) use surface-step + 1px hairlines, **not** drop shadows. Never border AND shadow at one elevation.
- **B4. Radius-as-hierarchy.** Each radius tier means something (structural / input / card / pill), not arbitrary softness. Document what each tier is for.

---

## C. Visual language minimums (the easy part — fast gates)

- Neutrals: one temperature family. Functional palette: **≤3 hue families.**
- Each color carries **one** meaning (interactive / warn / ok) — not decorative-and-redundant.
- Type: **≥3 sizes + 2 weights**, heading:body ratio **≥1.5×**.
- **Number formatting: pick a precision and commit** (`~73K`, not `72,563`, unless the exact figure is the point). Inconsistent number formatting across tiles is a loud amateur tell.
- Intentional-vs-generic: could this exact palette/spacing/radius ship with any SaaS template? If yes → under-differentiated.

---

## D. Charts

- **Strip chartjunk:** kill gridlines and the y-axis when data labels carry the value; label lines/bars directly instead of a legend. **No 3D, gradients, shadows, textures.**
- **Never ship default chart styles** (Excel/Power BI/Tableau defaults signal "no one thought about it").
- **Type matches relationship:** trend → line · category compare → bar · part-to-whole → stacked bar (NOT pie) · correlation → scatter · number-vs-target → bullet graph.
- Kill: pies > 3 slices, gauges, donuts-for-precision. Position beats angle/area.
- ≤3 data points → a number or a sentence, not a chart. Exact values needed → a table.

---

## E. Do's and Don'ts (the #1 accuracy lever — keep rule-anchored)

In both critique and build, **the Don'ts pull more weight than the Do's** (confirmed in research and across all 73 specs). Anchor each to a rule above.

**Do**
- Tier tiles by priority before laying anything out (A1).
- Snap every dimension to the 8-pt scale (A4).
- Reserve the accent for its stated roles only (B1).
- Carry hierarchy with size + space (A4, C), let one element clearly lead.
- Run the squint test before declaring done.

**Don't**
- Don't size a tile to its content (→ dead space). Size to priority.
- Don't pad an orphan with filler — resize or center it (A3).
- Don't use border AND shadow at one elevation (B3).
- Don't bury scannable numbers behind tabs (A5).
- Don't ship default chart styles or pies > 3 slices (D).
- Don't introduce a second accent color (B1).

---

## F. Critique backbone — Nielsen's 10 Heuristics (the evaluate layer)

The DESIGN.md format is build-only; this is the industry-standard *critique* checklist. Map findings to it for completeness + credibility.

1. Visibility of system status — *L3* 2. Match to the real world (labels/microcopy) — *L2*
3. User control & freedom (undo, exit) — *L3* 4. Consistency & standards — *L5/L6*
5. Error prevention — *L3* 6. Recognition over recall (don't make them remember) — *L2/L4*
7. Flexibility & efficiency (shortcuts, defaults) — *L3* 8. Aesthetic & minimalist (no clutter) — *L4/D*
9. Help users recover from errors (plain-language messages) — *L2/L3* 10. Help & documentation — *L1/L2*

---

## Known Gaps (what this kit does NOT cover)

- Brand/aesthetic *content* (specific palettes, fonts) — deliberately not here; that's matched from the user's reference, per-project.
- Animation/motion choreography beyond feedback timing.
- Domain-specific data-viz (maps, network graphs, financial candlesticks) — apply D's principles, but specifics are out of scope.
- It does not emit a filled token spec in v2 — it applies rules. (Spec emission is a later slice.)
