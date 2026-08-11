# Design Glossary — Lay-to-Industry Translation

The skill uses this to convert what you *said* into what it's *called*.  
Only fires when lay or imprecise language appears — if you already speak in correct terms, skip it.

Seeded from `constraint-kit.md` (the canonical ground truth) + foundational design knowledge.  
Foundational tier only — training wheels for non-designers, applets through dashboards.

---

## Visual Hierarchy & Dominance

**"it's a wall of numbers" / "everything looks the same" / "I don't know where to look"**  
**→ Failed squint test / no visual hierarchy**  
Blur your eyes and look at the page. If nothing jumps out as more important, hierarchy has failed.  
*Principle:* ONE element must visually lead (size, weight, or contrast). Everything else ranks below it.  
*Common failure:* four equal-size cards, same font size, same color — the eye has no anchor and scans randomly.

**"the big card" / "the main tile" / "the hero" / "the top thing"**  
**→ Hero tile / lead tile (constraint-kit A1)**  
The largest card on a view — above the fold, highest priority, answers the dashboard's one 5-second question.  
*Principle:* max 1–2 hero tiles per screen. A third hero cancels the others — the eye loses its anchor.  
*Common failure:* three or four "hero-sized" cards that all compete. None wins.

**"it has one thing on it" (misread) / "only one item on the hero"**  
**→ Squint-test dominance (not literal item count)**  
"One thing" means ONE element visually dominates — like a newspaper front page has many headlines but ONE lead story.  
*Principle:* the squint test asks "does one element LEAD?" not "does only one item appear?"  
*Common failure:* stripping a hero down to one metric when the problem was visual dominance, not item count.

**"the page feels heavy" / "too much going on" / "it feels cluttered"**  
**→ Visual clutter / low data-to-ink ratio (Tufte)**  
Too much non-data ink (borders, gridlines, shadows, decorations) relative to actual content.  
*Principle:* strip chartjunk; remove anything that doesn't carry meaning.  
*Common failure:* border AND shadow on the same card, decorative icons, busy background patterns.

**"it feels empty in some spots and crowded in others"**  
**→ Uneven density / orphan boxes (constraint-kit A3)**  
Some areas crammed; others have dead space that serves no purpose.  
*Principle:* balance by visual weight, not mirrored size. Orphan boxes get resized or centered — never padded with filler.  
*Common failure:* one lonely card left-aligned in a row with a huge gap beside it.

---

## Layout & Spacing

**"the spacing feels off" / "things aren't lined up" / "it looks inconsistent"**  
**→ Broken grid / off-scale spacing (constraint-kit A2, A4)**  
Spacing that doesn't follow a consistent system (e.g., 13px here, 17px there).  
*Principle:* 8-point scale (8/16/24/32/48px). 4pt allowed only for very dense dashboards.  
*Common failure:* arbitrary spacing chosen by feel — the #1 "amateur" tell, above color or fonts.

**"the cards feel squished" / "everything is too tight inside"**  
**→ Insufficient internal padding (constraint-kit A4)**  
Card content too close to the card's edges.  
*Principle:* padding scales with card size: 1×1 card = 16–20px; 2×2 card = 24–32px.  
*Common failure:* same 8px padding on every card regardless of size.

**"moving one card breaks the whole layout"**  
**→ Fragile bespoke layout / missing span classes (constraint-kit A6)**  
Layout built with per-card pixel values instead of reusable size classes.  
*Principle:* use three span classes (hero / feature / metric). Change the class, not the pixel count.  
*Common failure:* each card has a hardcoded `width: 340px` — one change breaks the whole row.

---

## Information Architecture & Disclosure

**"nested TLDRs" / "summary of summaries" / "show the summary then let me drill in"**  
**→ Progressive disclosure — Shneiderman's mantra: overview → zoom → details-on-demand**  
Show the summary first; let the user go deeper only when they need it.  
*Principle:* two levels max — card shows the KPI, detail lives one interaction deeper. Three-plus levels → regroup.  
*Common failure:* burying scannable numbers behind tabs; forcing three clicks to see a figure.

**"should this be tabs or should I show both?"**  
**→ Tab vs. side-by-side comparison (constraint-kit A5)**  
Tabs hide one section while showing another — wrong when the user must see both to compare.  
*Principle:* tabs = few long parallel sections. If users compare → show both simultaneously.  
*Common failure:* putting two sections users always compare into tabs, forcing back-and-forth switching.

**"the labels don't tell me what the number means"**  
**→ Self-explaining labels / recognition over recall (Nielsen #6, L2)**  
A label should make the value obvious without forcing the user to remember a convention.  
*Principle:* plain language; no unexplained acronyms; empty/error states in full sentences.  
*Common failure:* "MTD Rev ($K)" — requires knowing the abbreviation AND the unit convention to decode.

**"is that a card or the things inside it?" / "I'm lost on what level we're talking about"**  
**→ Altitude / nesting levels (page → cards → elements)**  
A dashboard nests: the page holds cards; cards hold elements. Rank one altitude at a time — cards against cards, then the elements within the winning card.  
*Principle:* never mix levels in one ranking pass; ground a non-designer in the stack before interrogating.  
*Common failure:* listing a card and an inside-the-card element as peers — the stakeholder can't tell which level the question is about and stalls.

---

## Color & Visual Language

**"the accent color is everywhere" / "everything is highlighted"**  
**→ Accent scarcity violation (constraint-kit B1)**  
When everything is accented, nothing is accented — the signal disappears.  
*Principle:* ONE accent color; defined roles only (CTA / link / brand mark); max budget per viewport.  
*Common failure:* accent used for hover, borders, icons, headings, AND buttons — all at once.

**"too many colors" / "it feels like a rainbow"**  
**→ Overloaded functional palette (constraint-kit C)**  
More hue families than needed, or colors used for decoration instead of meaning.  
*Principle:* ≤3 hue families; each color carries ONE meaning (interactive / warn / ok) — not decorative.  
*Common failure:* six chart colors that don't map to categories, used purely for visual variety.

**"I can't tell what's on top" / "everything reads as flat"**  
**→ Missing elevation signal (constraint-kit B2, B3)**  
No clear system for what surface level a card sits on.  
*Principle:* ONE elevation signal — surface-color step OR border/hairline OR shadow. Never two at the same elevation.  
*Common failure:* border AND drop shadow on the same card, plus a background tint — three signals, none dominant.

---

## Typography

**"the text is hard to read" / "everything is the same size"**  
**→ Flat typographic hierarchy (constraint-kit C, L5)**  
All text at similar sizes — nothing tells the eye what to read first.  
*Principle:* ≥3 sizes + 2 weights; heading:body ratio ≥1.5×.  
*Common failure:* body at 14px, labels at 12px, headings at 16px — a 14% spread reads as "all the same."

**"the numbers are formatted differently everywhere"**  
**→ Inconsistent number formatting (constraint-kit C)**  
Some tiles show "72,563", others "~73K" — reads as a mistake, not a choice.  
*Principle:* pick a precision and commit. Consistent across all tiles.  
*Common failure:* exact figures mixed with rounded ones on the same dashboard with no governing rule.

---

## Charts & Data

**"I can't read this pie chart" / "the chart is confusing"**  
**→ Wrong chart type for the relationship (constraint-kit D)**  
Trend → line; category compare → bar; part-to-whole → stacked bar (not pie).  
*Principle:* chart type matches the data relationship. Never pie >3 slices. No gauges or 3D.  
*Common failure:* a pie chart with 8 slices showing quarterly revenue by product — impossible to compare.

**"the chart has too many gridlines and borders"**  
**→ Chartjunk (Tufte)**  
Non-data ink — gridlines, legend boxes, shading, 3D effects — that doesn't help the reader extract meaning.  
*Principle:* kill gridlines and the y-axis when data labels carry the value. Label lines/bars directly.  
*Common failure:* a bar chart with a full grid, legend, border box, gradient fills, and shadow on each bar.

**"is three data points worth a chart?"**  
**→ Chart threshold (constraint-kit D)**  
≤3 data points → a number or a sentence, not a chart.  
*Principle:* chart only when the shape matters. Exact values needed → a table instead.  
*Common failure:* a line chart with two points; a donut with two segments.

---

## Interaction & Feedback

**"I didn't know I could click that" / "it doesn't feel like a button"**  
**→ Missing affordance (L3, Nielsen #4)**  
The element doesn't look like it does what it does.  
*Principle:* affordances match the type — buttons look clickable; hover states give feedback; cursor changes.  
*Common failure:* a flat rectangle with text that acts as a button — no border, no background, no cursor change.

**"I can't tell if it's loading or broken"**  
**→ Missing loading/error state (L3, Nielsen #1 — visibility of system status)**  
The view has no defined state for "working" or "failed."  
*Principle:* every interactive view defines loading, empty, and error states in plain language.  
*Common failure:* a data table that goes blank during a refresh with no spinner or message.

---

## Accessibility

**"the text is too light / hard to read against the background"**  
**→ Contrast failure (L7, WCAG)**  
Text-to-background contrast below the minimum readable threshold.  
*Principle:* contrast ≥4.5:1 for body text; ≥3:1 for large text (18px+ bold). Falsifiable — check with a tool.  
*Common failure:* light gray text on white that looks "clean" but measures 2.1:1 — fails WCAG AA.

**"the only way to see it's an error is the red color"**  
**→ Color as the only signal (L7)**  
Colorblind users can't distinguish the state.  
*Principle:* color never the only signal — pair with an icon, label, or pattern.  
*Common failure:* a red border on an error field with no icon, no text message, no asterisk.

---

## The Squint Test

**"the squint test" (industry shorthand for gestalt hierarchy check)**  
Blur your eyes (or squint) at the view. The most important element must be visually dominant even when blurry.  
*Principle:* if the leading element is unclear at blur distance, hierarchy has failed — needs a rebuild, not a nudge.  
*Common failure:* designing at 100% zoom on a big monitor — looks fine close up, nothing leads when you step back.

---

## The 5-Second Test

**"does this answer my question fast?" / "the view takes too long to parse"**  
**→ 5-second test / JTBD — Jobs To Be Done (L1)**  
A dashboard element should answer its one question in roughly five seconds — no reading, scrolling, or cross-referencing.  
*Principle:* each card/tile has ONE job. If you can't state it in one sentence, it's doing too much.  
*Common failure:* a "summary" card with nine metrics — it summarizes nothing because there's no single answer.

---

## What kind of design is this? (the umbrella — teach, don't prescribe)

The honest umbrella for this skill's work is **UI / visual design fundamentals** — making a screen *look and work right*. Name the distinction only when it helps; don't lecture it.

- **UI (user interface) design** — what the thing looks like and how you operate it: layout, type, color, buttons, spacing. The skill's home turf.
- **UX (user experience) design** — the *whole* experience incl. research and testing; UI is a part of UX. This skill does the UI/visual end, **not** user research or usability testing (that's intermediate).
- **Web design** — older, broader term; now reads as code-adjacent / dated.
- **Visual design** — the surface/aesthetic layer only (narrower than UI).
- **Dashboard vs. website** — a **dashboard** is *passive, read-at-a-glance* data (judge density, hierarchy, what to show); a **website / landing page** is more *presentational* (judge the hero, the flow, the message). The basics apply to both; the emphasis shifts. *(A "cockpit" is an interactive dashboard you act in.)*

---

## Phrases that FORK — they mean more than one thing (ask which; don't bolt to one)

These crude phrases map to several concepts at once. Offer the 2–3 candidates and ask which — proffer a suggestion, don't demand the stakeholder already know the word.

| Lay phrase | Candidate concepts (offer, then ask) |
|---|---|
| "Make it pop" | Contrast · visual hierarchy · emphasis/focal point · (sometimes) higher saturation |
| "Looks cheap / unprofessional" | Inconsistent type · weak/incoherent palette · poor spacing · generic default styling · stock-y tropes |
| "Too busy / cluttered" | Too little white space · broken hierarchy · no focal point · proximity failures |
| "Boring / plain / too safe" | Low contrast · flat hierarchy · weak type scale · uniform weight (no emphasis) |
| "Make it modern" | Flatter look · more white space · sans-serif · cleaner grid · current palette *(get a reference)* |
| "Hard to read" | Low contrast ratio · small size · tight leading · wrong body typeface |
| "Feels off / something's wrong" | Alignment · broken grid · proximity violation · imbalance *(look before naming)* |
| "Doesn't flow" | Weak hierarchy · missing reading path · poor scale/weight progression |

**The move:** validate what they noticed in their words → name the concept(s) from this file → if it forks, offer the candidates and ask which → teach ONE term, plainly. Name the principle **+ the specific element + the consequence**, never the bare word.

---

## The cap (what this dictionary deliberately does NOT cover)

Beginner / foundational tier only — applets through dashboards. **No** intermediate/advanced terms (Gestalt in depth, motion choreography, responsive-breakpoint strategy, type-scale systems, HSL/OKLCH, design tokens, data-viz, component libraries). Exact numbers live in `constraint-kit.md`; this file names the *concepts*. If a complaint maps to nothing here or in the kit, **say so plainly and offer the nearest concepts — never invent a term.**
