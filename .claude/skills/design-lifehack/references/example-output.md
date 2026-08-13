# Example Output — The Golden Turn

This is the **teach-back shape**: what a great skill turn looks like when the user reaches for a concept  
in lay language. Use this as the template when translating lay words into design terms.

**Demand-driven only.** Fire this shape when lay or imprecise language appears.  
If the user already uses correct design terms, skip the teach-back and go straight to the critique or fix.

---

## The Teach-Back Shape

```
**You said:** (mirror the user's exact lay words)
**What that's called:** (industry term + one plain sentence from design-glossary.md)
**What most [dashboards/pages/applets] do:** (the standard approach + the common failure)
**The critique, translated:** (the blind-critique findings, rendered in design language)
**Boil-down:** you said X → it's really Y → the critique was Z → my suggestion going forward is W.
```

---

## The Golden Example

This is a real exchange where the skill performed well. It models the right voice and depth.

---

**Context:** The user was reviewing a system status dashboard. They had seen a critique that said "the hero card should have one thing on it" and were confused — they also said the dashboard felt like "a wall of numbers" and floated an idea about "nested TLDRs" for how to handle the data density.

---

**You said:**  
*"The critique said the hero card should 'have one thing on it' — but that confused me. And the dashboard is a wall of numbers. I had an idea about nested TLDRs."*

**What that's called:**

- **"A wall of numbers"** → **no visual hierarchy / failed squint test.** The squint test means: blur your eyes and look at the view. If nothing jumps out as more important, the hierarchy has failed. Every element is the same weight — the eye has no anchor and scans randomly.

- **"Have one thing on it"** → **squint-test dominance** (not literal item count). The critique didn't mean only one data point can appear on the hero tile. It meant ONE element must visually DOMINATE — like a newspaper front page: there are many headlines, but there's one lead story you see first at a glance. The hero tile's job is to answer the dashboard's one 5-second question, so one element must lead visually. A number, a trend, a status — one of them needs to be 2× the visual weight of everything else on that card.

- **"Nested TLDRs"** → **progressive disclosure** — Shneiderman's mantra: *overview → zoom → details-on-demand.* The idea you're describing already has an industry name and a proven pattern: the card shows the KPI (the TLDR), and the detail lives one interaction deeper (the nested layer). Two levels max. This is the right instinct — it's literally the standard solution to data density on dashboards.

**What most dashboards do:**  
The standard: a hero tile shows ONE dominant metric (large number, bold, ~36px+) with one supporting label and one comparison value (e.g., vs. last week). The common failure: four equal-size cards, same font size, same color — no anchor. The squint test fails instantly.

**The critique, translated:**  
The blind critics converged on: the primary KPI competes with three equal-weight supporting figures — there's no visual lead. The fix is not to remove figures; it's to make ONE figure visually dominant (larger type scale, higher contrast, more whitespace around it) so the squint test passes, even if three or four numbers still appear on the card.

**Boil-down:**  
You said "wall of numbers" → it's really a failed squint test (no element visually leads). You said "one thing on it" → it means one element *dominates*, not one item *exists*. You said "nested TLDRs" → that's progressive disclosure, which is exactly right. My suggestion going forward: keep all the figures, but make the primary KPI ~2× the type scale of everything else on the hero card. Then run the squint test: blur your eyes — if the primary number jumps out first, the hierarchy passes.

---

## Voice Notes

- **Warm, not clinical.** The user is learning vocabulary, not reading a textbook.
- **Lead with what they said, then translate.** Never open with the industry term — that's answering a question they didn't ask.
- **The boil-down is mandatory.** X → Y → Z → W. The user needs to hear it once in plain terms before moving on.
- **One teach-back per turn.** Don't pile three vocabulary lessons into one response — it defeats the purpose of teaching one term at a time.
- **After the teach-back, check in.** "Does that land? Or should I show the fix?" — then wait before building.
