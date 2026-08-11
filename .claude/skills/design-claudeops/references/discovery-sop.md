# Design Discovery Protocol SOP — the lead-driven path

*The process the design lead runs a stakeholder THROUGH — for a new build (DISCOVER) and as the backbone the
detective checks against (DIAGNOSE). The lead drives the steps; the stakeholder supplies the raw material. The
stakeholder is a beginner (small-business owner, AI-curious novice, smart pro with no design background) — keep
it KISS, cap it at foundational. ⛔ The two research write-ups this was built from are records in the
author's own notes and do not ship; their conclusions are the protocol below.*

The shape: **DISCOVER (elicit) → INFORMATION-HIERARCHY PASS (assign purpose + rank) → BUILD (lay out) → verify.**

---

## Part A — DISCOVER: the six-stage interview (the lead drives)

0. **Anchor to the project, THEN frame it (Gate A — the placement prerequisite).** Before anything else: *"which project does this design serve?"* → resolve the slug in `<notes>/system/project-registry.md`, place the cartridge inside that project (`<notes>/state/projects/{slug}/design/`), set the binder's `project:` slug, and inherit its `governing_contracts:` from the project's `canon.md` (read those docs before any build — Gate B), and **arm project-manager** for it — `bash "$ROOT/system/hooks/pm_flag.sh" arm "<absolute path to the project brief>" "<slug>" "<subject>"` (resolve the brief via `<notes>/system/project-registry.md`) — so `/save` and `/read` route to the project, not off to the side. If it's genuinely **standalone** (no parent project), make the stakeholder **confirm that explicitly** — an orphan cartridge that can't see its project's rules of construction must be a conscious choice, never an accident. THEN **frame it:** state the boundary (what's locked vs blank-page); define terms in plain language before using them.

**0.5 — The altitude primer (teach the stacking BEFORE you interrogate).** A non-designer stakeholder cannot rank what they cannot see the structure of. Before any heavy questioning, ground them in how a dashboard nests, in plain language — pointing at THEIR actual rendered screen if one exists (label the boxes A/B/C):

> A dashboard stacks in layers, like Russian dolls:
> - **The page** — the whole screen.
> - **Cards** — the big boxes sitting *on* the page.
> - **Elements** — the smaller things *inside* a box (a number, a row, a label).
>
> **You rank one altitude at a time:** first rank the *cards* against each other; then drop inside the winning card and rank its *elements*. Never mix levels in one breath.

Deliver it as a ~20-second primer and confirm they can see the levels before ranking anything. This pre-empts the #1 stall in the Hierarchy Pass — the stakeholder silently lost on which level a question is about ("is that the cards, or the things inside the hero?"). That confusion is a signal the primer was skipped, not stakeholder ignorance.

1. **The 5 questions** (one short round): (a) what does your business do + the ONE job this page does; (b) who's the visitor + what they should do; (c) what content do you already have; (d) the one must-have + the one must-NOT.
2. **Visual preference** *(the move for a non-verbal stakeholder)*: "show me 3–5 sites/dashboards you like" → interrogate each ("what specifically — color? layout? photos? the feel? what would you change?") → ask 1–2 **dislikes** (hard constraints) → reflect the *feel* back → confirm. References are an ingredient list, not a blueprint — extract elements, never "make it look like this."
3. **Priority rank — confirmed DIRECTLY with the stakeholder** *(the #1 rework-preventer)*: "what's the ONE thing this answers instantly? rank #1–4." Never inherit a relayed brief's framing.
4. **Tile-tiering gate** (constraint-kit A1): size = priority, never content volume.
4.5. **Seed the GRAMMAR (not just tokens).** The design system needs *grammar* — usage rules · composition contracts · **negative rules ("must NOT…")** · closed-value sets — or the build agent improvises and wobbles (*tokens give vocabulary, not grammar*). Inherit the generic grammar from `constraint-kit.md` (don't re-derive it); **capture this project's negative rules + closed-value sets into the binder / `decision-log.md` as decisions are made** (start from the stakeholder's must-NOT in Q1d). Grammar is mostly *imposed + captured over the build*, not interviewed cold from a beginner — but it must end up written down, not left in the agent's head.
5. **ASCII wireframe gut-check** (`references/ascii-layout-preview.md`): cheap layout → react → revise, before any pixels. Rough-first gets you *structure* feedback; finished-looking mockups get pixel-bikeshedding. **The gut-check isn't done until the stakeholder can SEE it** — ASCII is placement-only, narrow (≤~44 cols), pasted INLINE in the reply. If a preview doesn't reach them (collapses/wraps) or can't carry the judgment (density/fidelity), **switch medium immediately to a real render** — never burn turns re-running a preview they can't read.
   **PERSIST IT (required):** the approved wireframe is a MANDATORY section of the cartridge `<name>-brief.md`
   (`## Wireframe (ASCII)`) — write it in before lock/handoff. A cartridge with no saved wireframe is
   INCOMPLETE (the 2026-06-28 Cal miss: locked-on-Lanes but only stale pre-redesign renders existed). Draw to
   the view's REAL aspect ratio — the ≤44-col guidance is terminal-FIT only and must never distort a wide
   layout's proportions; when proportion is load-bearing, also register a 1440px render as the `golden_image:`.
6. **Build in the live app** — render→read→react loop; revert snapshots; log every locked decision.

**Two-round interview cap.** Stages 1–2 are the interview; once you can answer *what the visitor should DO · what content exists · what looks right to them*, **stop asking and show something.**

**Training-wheels cap — DROP for this stakeholder:** personas · journey maps · SMART goals/KPIs · competitor grids · brand mission / 5-year vision · requirements docs · digital wireframe tools (pen/ASCII wins) · anything past ~5 questions or 2 rounds.

The output of DISCOVER **is the binder** (`<name>-brief.md` — the desired-outcome tree).

---

## Part B — THE INFORMATION-HIERARCHY PASS (the missing middle step)

*Most views that feel "nice but wrong" have visual polish and no information hierarchy — every element was
styled, none was assigned a job or a rank. This pass fixes that. It LEADS with settled design canon, not
stakeholder framing. Citations verified against the real publications 2026-06-16.*

### The principles it enforces (the canon)

1. **One primary job per view — Jobs-to-Be-Done.** A view answers one question / supports one task; the rest is secondary. *Tony Ulwick (originator, Outcome-Driven Innovation; "What Customers Want," 2005) — popularized by Clayton Christensen ("The Innovator's Solution," 2003).*
2. **Glanceability — the primary answer lands at a glance,** on one screen, without navigation or recall. *Stephen Few, "Information Dashboard Design" (O'Reilly / Perceptual Edge, 2006).* Verify with the **5-second test** *(Christine Perfetti, 2007).*
3. **Purpose at every altitude.** Whole view → section → card → element — each owes ONE stated job (JTBD down the tree). A node with no job is a candidate to cut.
4. **Visual hierarchy — size, weight, position encode importance; the most important is the most dominant.** Grounded in the **Gestalt grouping laws** *(Wertheimer 1923; Koffka 1935; Köhler 1929).* Sanity-check with the **squint test** *(practitioner heuristic — no canonical author).*
5. **Overview first, then drill — progressive disclosure.** *"Overview first, zoom and filter, then details-on-demand"* — *Ben Shneiderman, "The Eyes Have It," IEEE Symp. on Visual Languages, 1996.* UX technique: progressive disclosure — *Jakob Nielsen / NN/g, 2006.*
6. **Inverted pyramid — most important first, detail tapering down.** *Jakob Nielsen, "Inverted Pyramids in Cyberspace," NN/g, 1996.*
7. **Strip non-data ink — maximize the data-ink ratio; kill chartjunk.** *Edward Tufte, "The Visual Display of Quantitative Information" (Graphics Press, 1983).*
8. **Critique backbone — cross-walk findings to the 10 usability heuristics.** *Jakob Nielsen, CHI '94 / "Usability Inspection Methods," 1994.*

### The procedure (run top-down: view → each section → each card → each key element)

1. **State the one job** (purpose). Can't name it? → candidate to cut. *(JTBD; Tufte)*
2. **Rank the contents** — what leads, what's secondary, what's reference-only. *(inverted pyramid)*
3. **Make the rank visible** — most important = most dominant; secondary recedes; reference-only drops to a lower tier or behind a drill. *(visual hierarchy; progressive disclosure)*
4. **Verify** — squint test + 5-second test: does the one job land at a glance, does one thing lead?
5. **Strip** — anything serving no job comes out. *(data-ink)*

A node with no recorded job isn't skipped — **assigning it is the move**, then it's stored in the brief's outcome tree. Output = a marked-up tree (every altitude → its job + rank) the build pipeline lays out via tile-tiering (size = priority).

---

## Part C — THE SOP-COMPLIANCE CONTRACT (stay on the path)

*The process twin of the vocabulary rule: structural mechanisms that keep the skill (and the stakeholder) from
skipping steps or wandering off on a side-quest. Grounded in the skill-building playbook §3 — binary visible
gates, escalation ladder, blind-the-arc. The core gates live in SKILL.md (adjacent to the action); the detail
is here.*

1. **The Prerequisite Ledger — the gate against skipped work.** The binder carries a visible checklist of each node's required early work (purpose stated? rank assigned? references gathered? cognitive-load bar set?). A **binary visible gate**: present = pass, missing = honest FAIL. **You cannot do downstream work on a node whose upstream prerequisite is blank** — can't polish a card whose job was never defined; can't lay out what you haven't tiered. When blocked, don't loop — state the gap and route back: *"Can't resolve this card — its purpose was never defined (Discovery skipped). Going back to do that first."* **Hard stop, not a label:** an `open prerequisite` named in the Path Beat blocks ALL downstream-stage work until it is resolved or the stakeholder explicitly waives it (logged); listed-UNSET-then-silently-passed is a contract violation. **Understand before you cut:** never propose removing or merging an element whose purpose you have not first stated.

2. **The Path Beat — belt-and-suspenders for the SOP.** Every substantive turn carries a one-line banner re-anchoring to the path:
   > `SOP · Stage 4/6 (Hierarchy Pass) · doing: ranking the System cards · open prerequisites: [System hero purpose UNSET] · next: squint check`
   A reply without it is malformed. The required format drags the skill back to the path each turn — the structural cure for side-quest drift (playbook: *distance decays compliance; blind the arc*).

3. **The Convergence Loop — the tight final-20% iteration, with an alarm.** Polish runs **bounded + monotonic**: cap the passes (~3), accept a change only if it **measurably improves** against a named criterion (squint / 5-second / the node's cognitive-load bar) — never loop-until-happy. **If the loop fails to converge within the cap, that is the alarm, not a reason to try harder** → it trips the Prerequisite Ledger: *"3 passes, no real improvement → the cause is upstream → which early step is unfilled?"* → route back.

4. **The Build-Conformance gate — the back-end twin of the Prerequisite Ledger.** The Prerequisite Ledger gates that upstream work is FILLED before you start; this gates that the BUILD actually DELIVERED it before you call it done. Before showing or saving a build, derive a checklist from the locked binder (wireframe + `decision-log.md`) — every agreed screen / card / element — and mark each **built / placeholder / MISSING** against the render. A **MISSING locked element blocks "done"** (it is a build gap, never an "aspirational" note; a locked element whose data isn't wired renders as a placeholder, never omitted). Record status by **SUB-SCOPE** — *partial — N of M built* — so a partial build never reads as full; and a unanimous Critical critic/stakeholder finding blocks "done" until fixed or overridden (logged). (Detail: SKILL.md Pre-output gates.)

**The unifying reflex — stuck at the end → suspect the beginning.** A polish loop that won't converge is evidence a foundational step (purpose, rank, the references) was skipped. The skill stops the spin and routes back to the missing work, rather than letting stakeholder + LLM bikeshed cosmetics together.

---

## Resumability

The binder carries a **stage marker** that names **sub-scope, not just a number** ("Stage 6/6 — BUILD: Overview
built · Flow/Archivist/Security STUB · 1 of 4 screens") — a bare "Stage X done" hides a partial build.
`/design-claudeops <name>` reads it and resumes there (jump back on request). Decision-log + dated snapshots
already exist. **Never rename binder files mid-project** — that's a documented continuity bug.
