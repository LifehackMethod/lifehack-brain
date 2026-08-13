---
title: "/ingest — PRODUCER SPEC (the behavioural contract)"
record_type: design-spec
desk: root
slug: ingest-skill
topic: [skill-design, ingestion-pipeline]
status: draft
authority: user
confidence: DRAFT — sections marked ❓ are UNRESOLVED and await the human-in-the-loop Q&A. **2026-08-08: the four PHASES and all four phases' STEP LISTS are ratified (see §0 AMENDMENT LOG); the ❓ that remain are narrower than they were.**
created_at: 2026-08-04
updated_at: 2026-08-08
template: system/templates/producer-spec-template.md
supersedes: nothing — this is the FIRST spec this skill has ever had
---

# `/ingest` — PRODUCER SPEC

> ⓘ **WHAT THIS FILE IS — read this before the 2,000 lines below.** This is the ingest skill's
> **normative specification and its build record**, kept together on purpose: `SKILL.md` and the four
> phase files cite it (§7, §8, §9) for the rules they implement, and the reasoning for each rule sits
> beside it so a later change can see what it would be overturning.
>
> **It is a working document, not a manual.** It argues with itself, records what was rejected, and
> quotes the author deciding things out loud. Read it when you need to know *why* a step is the way it
> is; read `SKILL.md` when you need to run the thing.
>
> ⚠ **Its file references point into the author's own project tree, not this repository.** Paths like
> `state/projects/...`, `intended-map.md` and various `brief.md` files are the provenance of a decision
> — where it was made — and were never part of what ships. A dead link here is expected and is not a
> missing file.


> **⚖ ONE SKILL as of 2026-08-05.** This document was titled *"/ingest + /ingest-filer"* — the filer was a
> second, auto-chained skill. The author reversed that split; the filer is now `phases/4-place.md`. The
> superseding record is `[SL-24]` in the project's Story Log, and the 2026-07-11 council decision that
> created the split keeps its full text at `[SL-3]`.

> **⚠ FIRST DRAFT.** Written 2026-08-04 from four mining passes (the journal, the decision records, the
> inherited rails, and a full inventory of the skill's own stated rules) plus one live run. **Every ❓ is a
> question only the author can answer** — they are deliberately left open rather than guessed, because a guess
> here silently becomes the contract.
>
> **What this document is.** The NORMATIVE contract: what the skill must DO, and what evidence proves it
> did. It is the answer to *"did this run work the way it's supposed to?"* — a question that had no answer
> before this file existed.
>
> **What it is NOT.** It does not govern how screens LOOK — that is
> `state/projects/ingest-skill/design/ingest-ux-brief.md` (the design cartridge: vocabulary · grammar ·
> examples). It is also not the organism ELEMENT (`system/organism/elements/world-model-ingestion.md`),
> which is *descriptive* and changes when the CODE changes. **This document is normative and changes when
> INTENT changes.** If a change makes you edit both, the split is wrong.

---

## Table of contents

*(SOP: a reference file over ~300 lines gets a table of contents. This one runs ~2,000 — added 2026-08-08,
task 9.8.2. Every entry below is the exact text of a real heading in this file; mechanically checked, not
eyeballed — see this session's verify output.)*

- **0. AMENDMENT LOG — SESSION 2026-08-08 (`/skill-builder` door-two run)**
  - §0a — THE RULINGS, each with its verbatim source
  - §0b — THE SKILL'S END-STATE DESIRED OUTCOME
  - §0c — THE TENSION SWARM, 2026-08-08
  - §0d — BOTH "THE OWNER'S CALL" ITEMS ARE NOW CLOSED
  - §0e — TEMPLATE SECTION RECONCILIATION
- **1. What this IS**
- **2. Inputs**
  - 2a — THE CORPUS-IDENTITY CONTRACT
  - 2b — THE INTAKE FORMAT LIMITATION + THE INTAKE SEAM'S OUTCOME SET
- **3. Inherited non-negotiable rails**
- **4. The write model (the gears)**
- **5. Phases, their desired outcomes, and their steps**
  - 5a. Phase desired outcomes
  - 5b. Steps, by type
  - 5c. CROSS-CUTTING COMPONENTS — they belong to no single phase
  - 5d. KNOWN DEFECTS + OWED FIXES — the running list
  - 5e. WIRE-OR-RETIRE DECISIONS — the four dead validators
- **6. Evidence surfaces & the trust-only list**
  - 6a. THE GRID
  - 6b. WRITE TARGETS (exact) *(template §7)*
  - 6c. DEFINITION OF DONE *(template §8)*
  - 6d. GRACEFUL DEGRADATION — the source cascade *(template §9)*
- **❓ OPEN — the Q&A must resolve these**
- **7. PHASE 1 — SORT** *(fully specified)*
  - BEFORE THE SKILL RUNS
  - TURN 1 — the machine looks, then explains
  - TURN 2 — the human's turn
  - TURN 3 — the machine responds
  - THE LOOP
  - FINAL TURN — close
- **8. PHASE 2 — SCREEN A PILE** *(fully specified)*
  - THE VERDICT SET — the closed vocabulary this phase turns on
  - BEFORE THE PHASE RUNS — mostly off-camera 🌙
  - TURN 1 — the machine looks, then explains 🤖
  - TURN 2 — the human's turn 🧑
  - TURN 3 — the machine responds 🤖 ↩
  - THE LOOP — where the round actually lives
  - FINAL TURN — close
  - WHAT THIS PHASE OWES — the build list this spec generates
- **9. PHASE 3 — THE WORLD MAP** *(fully specified)*
  - THE THREE OUTPUT TYPES — the closed vocabulary this phase turns on
  - ⚖ RULED 2026-08-05 (the author) — a RECORD becomes a STUB FILE
  - BEFORE THE PHASE RUNS — off-camera 🌙
  - TURN 1 — the machine looks, then explains 🤖
  - TURN 2 — the human's turn 🧑
  - TURN 3 — the machine responds 🤖 ↩
  - THE LOOP — where the round actually lives
  - FINAL TURN — close
  - WHAT THIS PHASE OWES — the build list this spec generates
- **10. PHASE 4 — PLACE IT + THE ROOT CANON** *(specified 2026-08-08)*
  - ⛔ THE GATE THAT PRECEDES EVERYTHING — MAIN SESSION ONLY
  - TURN 1 — the machine gathers and shows the whole shape 🤖
  - TURN 2 — the human approves the FILES, not the ideas 🧑
  - TURN 3 — the machine writes 🤖 ↩
  - FINAL TURN — close
  - WHAT THIS PHASE OWES — the build list this spec generates

---

## 0. AMENDMENT LOG — SESSION 2026-08-08 (`/skill-builder` door-two run)

> **⚖ WHY THIS SECTION EXISTS — a standing rule the author set on 2026-08-08, `authority: user`:**
> *"this is something that should be happening at the end of every phase — once it's fully approved… it's not
> persisted as locked forever, but it is persisted as the most recent best current thinking. So this honestly
> should have been happening the entire way along."*
> ⇒ **At the end of every ratified phase, the result is written HERE, into the spec — not left in a scratchpad.**
> Persisted ≠ locked: this is **the most recent best current thinking**, and a later session or the skill-tester
> may still rewrite anything that is not an outcome or one of the three hard invariants (§8's prescription box).

**What this run ratified.** `/ingest` was put back through `/skill-builder` because it was never built with it.
The chain reached BUILDER PHASE 3 (steps). Ratified, with the author in the chair, by explicit A/B fork each time:

| # | Ratified | Where it now lives |
|---|---|---|
| 1 | **The four phases stand** — ① MAKE THE PILES ② SCREEN A PILE ③ THE WORLD MAP ④ PLACE IT + THE ROOT CANON | §5a (unchanged) |
| 2 | **PHASE 1's step list** + 6 additions a conformance check found missing | §7 + §0a below |
| 3 | **PHASE 2's step list** + the slicing method made explicit | §8 + §0a below |
| 4 | **PHASE 3 RESTRUCTURED into FIVE TURNS** | §9's restructure block |
| 5 | **PHASE 4's step list — the phase that had no section at all** | **§10 (new)** |
| 6 | **The world model is a NEW PROJECT created at the END OF PHASE 1, as a gate** | §0a, §5c |
| 7 | **A world-model COMPACTION ENGINE is owed** — a new cross-cutting component | §5c |
| 8 | **Folder names are generic subjects, never person-names** | §5c |
| 9 | **The skill-level END-STATE desired outcome** | §0b |

### §0a — THE RULINGS, each with its verbatim source

1. **⚖ THE WORLD MODEL IS A NEW PROJECT, CREATED AT THE END OF PHASE 1, AND IT GATES PHASE 2.**
   *(the author: "the new project would have been set up at the end of phase one… somewhere at the end of phase one,
   before we're even allowed to go to phase two, it would round up all of the things from phase one and make
   sure to persist them into this new system, this new brief, before it proceeds to phase two.")*
   ⇒ **SUPERSEDES the 2026-08-05 framing at `2.0b`** (*"the world model IS the project brief"* — load an
   existing one). The run **creates and owns** a project of its own, one per corpus. `2.0b` becomes a plain
   LOAD. **A PHASE 1 run that ends without this has not finished.** It also settles `2.0c`'s frequency by
   construction: **once per run.**
   ⚠ **Distinction the session flagged and the author has not yet contradicted:** per-chat VERDICTS stay in the
   corpus-map (machine-readable state that resume-safety and every coverage gate read); OBSERVATIONS,
   corrections and arcs go to the project scratchpad. A prose pad cannot carry the state.

2. **⚖ FOLDER NAMES ARE GENERIC SUBJECTS.** *(the author: "I want the LLM to come up with generic category names
   that are appropriate to each pile… I don't want it to be names. My desks are names, but it should just be
   like financial, or whatever it's related to — if it's related to hobbies or financial or to art.")*
   ⇒ binds in **PHASE 1** (pile names ARE the first draft of folder names) and in **PHASE 3's folder-shape
   step**. ⛔ **PHASE 4 assembles and NEVER renames** — a wrong name at PHASE 4 goes back to PHASE 3.

3. **⚖ A RECORD GETS A STUB FILE; THE ORIGINAL IS NEVER MOVED AND NEVER REWRITTEN.** Third statement of the
   same ruling; see the correction in-place at §9's type step.

4. **PHASE 1 — SIX STEPS A CONFORMANCE CHECK FOUND MISSING from the drafted list, now owed to §7:**
   ① the map **BUILD/MIGRATE action** (§7's `1.1` captured only the assert half; the driver runs
   `corpus_map.py init` then `migrate` first) · ② **bookmark every chat by content hash** so a re-export with
   churned filenames re-links instead of duplicating (`1-sort.md:53-59`) · ③ **cluster the leftover
   UNCLUSTERED pile** (`1-sort.md:101-105`) · ④ the **FINAL TURN's paste-verbatim closing screen** + *"type
   `/ingest` to continue"* · ⑤ **speak the WELCOME** before the heads-up · ⑥ **paste the screen into your own
   reply, never leave it in the collapsed command block.**
   ⚠ **AND A TERM THE SESSION INVENTED, killed on sight:** a draft said the security posture must be set to
   *"block."* **No source uses that word.** The two real values are **`enforce`** and **`warn`**.

5. **PHASE 2 — THE SLICING METHOD MUST BE STATED IN THE STEP, not left implicit.** *(the author: "I don't see
   anything here about the slicing… we have a whole methodology, like slicing, so that we can actually pull a
   very accurate assessment or guess at what the whole chat is about. That's not what we said in the spec.")*
   Verified in `tag.py:95-99,103-126` — **≤2,500 chars → the WHOLE sanitized chat · ≤8,000 → first 3,000 + last
   3,000, middle elided · >8,000 → first 3,000 + a middle 3,000 + last 3,000, both gaps marked · hard ceiling
   `SCAN_TOTAL_CAP = 10,000` as a backstop, not the shaper.**

6. **`2.9`'s "NOT BUILT" IS TOO BROAD — the widened slicer EXISTS.** `tag.py:138-160` defines
   `explore_char_slice` with **`EXPLORE_WIN = 9,000`** and **`EXPLORE_TOTAL_CAP = 28,000`**. Grepped
   `skills/`, `system/`, `shared/`: **ZERO callers**, while `adaptive_char_slice`/`giant_sample` ARE wired at
   `gate_and_pack.py:137,139`. ⇒ **the SLICER is built; the WIRING is not.** ⛔ Do not invent a new cap — the
   numbers carry their own reasoning in the file.

7. **⚖ LAW 8 IS THIS PROJECT'S VERDICT FORMAT.** From the author's ratified `intended-map.md:550-565`: *"**NEVER
   MERGE THE TWO FILES. If reality and intent disagree, that disagreement IS the finding.**"* Three legal
   outcomes: **BUILD** · **FIX** · **INTENT WAS WRONG**. ⇒ every contradiction below gets one of those, never
   a vague "owed."

8. **🔬 FUTURE EXPERIMENT, NOT NOW — re-test haiku vs sonnet on the two SUMMARISING rungs** (`2.4` thin read,
   `3.0b` deep read), after the skill is built. *(the author: "some of this stuff, it's just summarization. It could
   totally be done by haiku… once the skill is all built.")* ⚠ The 2026-07-11 revert (`779157c`, *"haiku lost
   the intuition"*) **stands until re-run** — but it changed TWO variables at once (haiku **and** a 3,500-char
   slice). At today's slice size haiku has never been tested. Hold the slice fixed; vary only the model.
   ⛔ Never on the JUDGMENT rungs.

### §0b — THE SKILL'S END-STATE DESIRED OUTCOME *(drafted 2026-08-08 from the author's answer + the doctrine; his
bar, his words: "not my current system, because I have a lot of junk — theoretically the way my system is
SUPPOSED to work, for the altitude doctrine and all of this stuff.")*

> When `/ingest` finishes, the person owns a **folder tree that behaves like a knowledge system rather than a
> pile of notes**: every folder is a DOMAIN with a stated purpose in its own `canon/purpose.md`; its standing
> truths sit in `canon/current.md`, **thin at the top and heavy at the leaves**, so nothing is charged to
> conversations that do not need it; anything too big to state lives as a **findable stub with a pointer**, and
> nothing was buried without a breadcrumb where a future session would look; and **not one line became canon
> without the person's own yes.** It is not the finished system — it is the **groundwork the finished system
> can grow inside**, and it obeys the altitude doctrine from the first folder rather than being retrofitted
> to it later.

⭐ **THE BAR IS THE IDEAL SYSTEM, NOT THE OBSERVED ONE.** ⛔ A future session must **not** copy the shape of
The author's own existing `desks/` tree as it stands — he has explicitly disowned it as containing junk.
The target is the doctrine: the altitude rules **§C3 below** restates in full. *(⚠ [5.2.1], 2026-08-11:
`system/knowledge-altitude.md` itself is a Lifehack-internal doctrine file — it is NOT shipped in this
repo, so this no longer names it as something to go open; every test it states is already inlined at
§C3 and in `pipeline.py`'s `propose_folder_shape()` docstring.)*

### §0c — THE TENSION SWARM, 2026-08-08 · what it found, what was adopted, and **what was rejected and why**

Four critics read the WHOLE spec and the CODE at once, blind to each other; the CHRONOLOGY critic then took a
second pass with the other three's findings in hand. **12 tensions reached the human; 10 were discarded by the
readers before they got there** — the bar was *"surface it only where two parts would produce DIFFERENT WORK."*
⭐ **The rejections are recorded deliberately: an unrecorded rejection gets re-proposed by the next reader who
looks.**

**⭐⭐ THE ROOT PATTERN — no single critic could see it, and it explains four of the twelve.**
**WHEN A MAP COLUMN'S VOCABULARY WIDENS, ITS OLD READERS ARE NEVER SWEPT.** Two booleans became eleven reader
categories; `MINE/TOSS/SAVE` became `KEEP/TOSS/EXPLORE`; two flags became three finding types — and each time
at least one downstream reader was left on the old vocabulary. Each instance sits in a different file, which is
why only the cross-cutting read finds it. The loudest breakage gets patched at the display layer and the source
is left alone — `scan_review.py:141-147` says so in its own comment: *"pipeline.py itself is untouched."*
⇒ ⛔ **STANDING RULE, adopted:** *when a map column's vocabulary changes, **grep every reader of that column**
before calling the change done.* Patching the site that broke loudest is not finishing the job.
⚠ **Unchecked, and named as the next place to look:** the PHASE 2 → PHASE 3 boundary — does `3.0a`'s partition
read PHASE 2's verdicts correctly, given the verb set is already known inconsistent at the anchor layer?

**ADOPTED AND WRITTEN INTO THIS DOCUMENT:** the "six passes" correction (§7) · the sitting-count correction
(§7, 48 not 23) · the ITEM-LOOP correction at `4.3` (§10) · this section · and every remaining finding entered
in §5d with an anchor and a LAW 8 verdict.

**⛔ REJECTED — one recommended fix, and the reason it lost.** The PRESENTATION critic was right that `4.3`'s
screen shows a truncated one-liner where the spec demands the record. But the implied fix — *make the code
match the spec's ITEM-LOOP* — was **rejected by the main session**: a literal item loop is one screen per
record, dozens to 100+ turns on this corpus. **The batching is correct; the row's depth is the defect.**
Recorded at `4.3` as **INTENT WAS WRONG**.

**⛔ NOT ADOPTED — two are THE OWNER'S CALL and the session refused to close them:**
1. **Knowledge folder vs full DESK** (§5c C2). The swarm proved the CODE had already decided it —
   `4-place.md:144-145` called `desk_scaffold.py` unconditionally, so PHASE 4 as it then stood would have built
   **23 desks and printed 23 hand-paste registry blocks.** ⭐ **The finding is adopted; the DECISION is not made
   [as of this historical note].** Session recommendation stands: knowledge folders.
   ✅ **RESOLVED 2026-08-08 (Phase 9, tasks 9.4.1–9.4.2), superseding both the decision-pending state above
   and its own code claim: `4-place.md:144-145` now calls the new `folder_scaffold.py`, which creates ONLY
   `canon/current.md` + `canon/purpose.md` + `records/` — no registry entry, no desk. See §5c C2 for the
   full account.**
2. **Is the world-model brief EXEMPT from `project-manager`'s Frame-intake gate?** That skill's Create path
   *"loops the intake until critical slots are CONFIRMED or WAIVED"* (`project-manager/SKILL.md:451-456`) and
   PHASE 1 has no such round. ⇒ either PHASE 1 grows an **unbounded** human sequence — breaking the
   four-sitting result §OPEN 8 relies on — or a hard gate is silently bypassed. **Session recommendation:
   EXEMPT**, on the author's own words that this brief *"functions a little bit differently than a project brief
   normally functions."* **One line from him settles it.**

### §0d — BOTH "THE OWNER'S CALL" ITEMS ARE NOW CLOSED (later the same day, 2026-08-08)
⚠ **§0c above was written BEFORE these two landed. Read this section as superseding §0c's "NOT ADOPTED" list.**
*(A conformance check run afterwards reported the spec **BLOCKED** on exactly these two — correctly, against the
text as it then stood. The block was this document lagging behind the human, not a real obstacle.)*

1. ✅ **KNOWLEDGE FOLDERS, NOT DESKS.** Ruled — see §5c C2.
2. ✅ **THE FRAME-INTAKE QUESTION DISSOLVED — it was never a real question.** the author: *"we can also create our own
   project manager brief whenever we want. **There's no fucking questions here dude.**"* ⇒ `/ingest` **writes the
   brief file directly**, in the shape `project-manager` reads. It **does not invoke `project-manager`'s
   Create/Frame-intake path at all**, so no gate is triggered, nothing is bypassed, and no exemption is needed.
   ⚠ **The session had manufactured the dilemma** by assuming *"reuse `project-manager`"* meant its Create
   procedure; it means the **file shape and the `pm_flag.sh` conventions.** ⇒ **`1.10` is a plain write step with
   no sub-loop**, and critical-path item ① shrinks accordingly.
   ✅ **RESOLVED 2026-08-08 (Phase 9, task 9.1.4) — MEASURED, and the claim below overcounted.** A grep of
   every driver call-site (`skills/ingest/phases/*.md`, `SKILL.md`) found the phrase *"via the existing
   `project-manager` skill"* live in only **ONE** file: `2-scan.md`'s `2.0b`, now reworded to *"Read it
   DIRECTLY — the shape `project-manager` reads — … ⛔ Never via that skill's Create/Frame-intake path."*
   `2.10` never carried the phrase at all — it is a plain "write what was learned into the brief" step with
   no `project-manager` citation to reword. `3.8` doesn't exist under that step number in the current
   (post-restructure) `3-deep-read.md`, and that file carries no such phrase anywhere either — its own new
   step (`1.10` in `1-sort.md`) was written correctly from the start (*"Written and read directly, in the
   shape `project-manager` reads — ⛔ never via that skill's Create/Frame-intake path"*), never needing a
   reword. **True count: ONE real stale call-site, now fixed** — not the four/three this passage originally
   named. *(Original text, kept as the record of what was claimed:)* ⛔ *CONSEQUENT EDITS OWED, or the
   document contradicts itself again: `2.0b`, `2.10` and `3.8` all still say "via the existing
   `project-manager` skill." Reword each to "reads/writes the brief directly (the shape `project-manager`
   reads); ⛔ never its Create/Frame-intake path."*
   ⛔ **AND A COUNTER-ARGUMENT WORTH KEEPING** *(SOP `skill-building-sop.md:661-662`)*: *"Instantiate the existing
   enforcement infra — never author a parallel one. Parallel systems fragment the guard set."* This does not
   forbid writing the brief directly — the file format IS the existing infra — but it does forbid inventing a
   **second brief format**. Write the same shape `project-manager` reads, or the warning applies.

**THE CRITICAL PATH — three fixes, ordered by DEPENDENCY, not severity** *(CHRONOLOGY second look)*:
**① `1.10`** — sequence it correctly and BOUND its Frame-intake sub-loop. Most upstream: it gates all of PHASE
2 onward, and §5c C1's compaction engine reaches every phase through this same gate. **Nothing downstream can
be trusted to have a valid grounding project until this is right.**
**② `4.1`'s LOAD reads the finding TYPE** (§5d). PHASE 4's first step; `4.2`, `4.3`'s plan-build and `4.4`'s
triage all consume what it loads. Requires no change to PHASE 3, which already writes the data.
**③ Move the `archivist-route` ranking BEFORE `4.3`'s CONFIRM** (§5d). Last-mile write correctness, and
downstream of both — fixing it first would be wasted while ② still feeds it stale kinds.

**WHAT THE READERS THEMSELVES REJECTED, and it is not padding — record it so it is not re-proposed:** the SORT
row format (the shorter shape is ratified at that phase) · `2-scan.md`'s step-id lag (internal ids, never shown
to a human) · the codename step-tracker (it follows the plain-language map, never replaces it) · and five
defects already stated accurately in §5d/§0a with their own verdicts (`require_world_map` off · brain N→N ·
the unwired explore slicer · the `wmb_commit` mis-citation · the `import pipeline` breakage) — re-surfacing
those would confirm what the spec already says about itself, not find a tension. ⭐ **Fan-out discipline and
the four-phase count both came back CLEAN**: every reader spawn is unnamed, `sonnet`-pinned and backgrounded;
`4.0`'s HARD_STOP correctly refuses a write-capable step outside the main session; and no case was found of one
step secretly doing two human-facing jobs.

### §0e — TEMPLATE SECTION RECONCILIATION *(2026-08-08, this session, task 9.8.1)*

**Every section `producer-spec-template.md` requires, accounted for — present, relocated, or explicitly
NOT ACTIVE.** Per the template's own governing rule: *"'not active in this slice' is a legitimate,
informative answer. A blank slot is not."*

| Template § | Title | Status in this document |
|---|---|---|
| 0 | How this spec's sections become skill files | **RELOCATED / IMPLICIT** — no standalone map table; each phase section (§7-§10) states its own build items in its own closing "WHAT THIS PHASE OWES" table, and cross-references to `SKILL.md` / driver files are inline throughout rather than centralized. Not rebuilt this session — outside task 9.8.1's four named sections. |
| 1 | What `<SKILL-NAME>` IS | **PRESENT** — §1 |
| 2 | Inputs | **PRESENT** — §2 |
| 3 | Inherited non-negotiable rails | **PRESENT** — §3 |
| 4 | The write model (the gears) | **PRESENT** — §4 |
| 5 | THE GRID | **NOT ACTIVE AS A SEPARATE TABLE** — superseded by the locked phase format (template §6c), used for all four phases at §7-§10. Reconciled at §6a. |
| 6 | The step / beat chain (6a-6c) | **PRESENT, AS THE GOVERNING FORMAT** — §5 (phase outcomes, step types, the prescription budget) plus the phase-by-phase application at §7-§10, which already follow §6c's locked shape. |
| 7 | Write targets (exact) | **RESTORED** — §6b (this session) |
| 8 | Definition of done | **RESTORED** — §6c (this session) |
| 9 | Graceful degradation | **RESTORED, AS NOT ACTIVE** — §6d (this session). This skill has no tiered source cascade; see §6d for why. |
| 10 | Session scratchpad + scribe | **RELOCATED / PARTIAL** — this skill's scratchpad IS the run's project brief (the "world model"), specified across §7 `1.10`, §8 `2.0b`-`2.10`, §9 `3.8`, and the compaction engine at §5c C1. No single section carries it because it is cross-cutting by design (§5c's own framing). ⚠ **And it is NOT BUILT** (§5d items 4, 17) — a real gap, not a documentation one. |
| 11 | Evidence surface & enforceability tagging | **PRESENT, IN REDUCED FORM** — §6 (Evidence surfaces & the trust-only list) carries the evidence-surface half but, as §5d item 21 already noted, survives only as a bullet list with **no enforceability-class column** (`enforceable · human_in_the_loop · uncheckable-from-artifact`). Not rebuilt to the full table this session — outside task 9.8.1's four named sections; recorded here so the gap isn't lost. |

**What this session actually built (task 9.8.1's exact scope): the equivalents of template §5, §7, §8, §9
only** — the four sections whose NUMBERS had been silently reused for PHASE 1-4, which is what made the
original gap dangerous (a reader searching for "§8 Definition of done" landed on "PHASE 2"). Because those
four numbers are load-bearing elsewhere — `pipeline.py`, `test_pipeline.py`, `scan_collect.py`,
`check_screens.py`, and `system/sops/skill-building-sop.md` all cite **`SPEC.md §8`** to mean PHASE 2 —
**the phase sections were NOT renumbered.** The restored template sections instead live at **§6a-§6d**,
each explicitly cross-labelled with which template section it answers, so both numbering schemes stay
simultaneously readable and nothing that already cites "§8" or "§9" meaning a PHASE goes stale.

---

## 1. What this IS

**The founding anti-pattern — why this exists at all.** the author's 2026-04 ChatGPT migration *"chopped
instead of modeled, was abandoned half-done, promoted nothing."* Every design choice in this skill is a
reaction to that failure. A spec clause that would let any of those three recur is wrong by construction.

- **Layer 1 — user outcome.** Years of scattered thinking become a durable, well-organised world-model of
  himself that he trusts and reuses — with **nothing dropped** and **nothing filed without approval**.
  **Bar (his words):** *"watching the system's model of me get sharper each round — it feels like a game,
  not a chore."*
  > ⭐ **THE BRIDGE — added 2026-08-08, because this document states TWO outcomes and a cold reader hits them
  > as a contradiction.** The 2026-07-12 FRAME says the product is the EXPERIENCE (*"the reward is being seen,
  > not being finished"*); §0b and the 2026-08-04 reframe say the product is an ARTIFACT (*"the output is A
  > PERSONAL FOLDER SCHEMA READY TO INTRODUCE INTO LIFEHACK"*). **Both are true, and this is how they fit:
  > the SCHEMA is the DELIVERABLE; the REFLECTION is HOW THE SCHEMA BECOMES CORRECT.** A map of someone's
  > knowledge cannot be accurate unless that person corrects it, so the game is not decoration on the output —
  > it is the accuracy mechanism that produces it. ⇒ **This is why PHASE 3 is the heart of the skill and not a
  > screen on the way to filing.** *(Stated to the author 2026-08-08 and not contradicted; he chose to move on
  > rather than rule it, so it stands as the working reconciliation, not as his words.)*
  > ⭐ **AND WHY THE OUTPUT IS A TREE RATHER THAN ONE DOCUMENT** — from the author's own ratified `intended-map.md`,
  > phase ① of the system's lifecycle (AT REST → CALLED IN → DURING → AFTER): *"the save doesn't just save
  > everything in one blob. It saves things into the correct category, and the read doesn't just say read
  > things in one blob. **It reads the correct categories.**"* The folder schema exists so that retrieval can
  > be directed. **A single README would be unreadable by the thing that has to read it.**
- **Layer 2 — role.** **Vera the Curator**, one warm voice across both skills. A calm, competent guide:
  runs the plumbing quietly (locks, quarantines, retries are her problem), shows every decision screen in
  full, proposes numbered best-guesses, holds the 10,000-ft view so the human doesn't have to.
  **Human-in-the-loop by construction** — the machine does the mechanical bulk; the human supplies the
  only thing it cannot: whether a conclusion about *them* is true.
- **Layer 3 — per-turn anchor.** `phase | basket | position | next step`, computed live from the map,
  re-injected every turn.

**THE REWARD IS THE REFLECTION, NOT COMPLETION.** *(the author, 2026-07-12, `authority: user` — he killed the
opposite instinct explicitly.)* The fun is watching the system's model of him sharpen each round;
correcting it is the point, not friction. ⛔ **"One-tap efficiency" is a RULED-OUT goal.**

---

## 2. Inputs

| Input | Source | Read once or live? | If absent |
|---|---|---|---|
| The flattened corpus | `paths.py flatten "$INGEST_CORPUS"` — per-platform cache, with an existing legacy `$HOME/.cache/cowork-ingest/…` winning so nothing re-flattens; see `flatten_dir()` and §2a | ONE-DATASET — never re-flattened mid-run | hard stop |
| The corpus-map (state machine) | `$COWORK_WORK/corpus-map.json`, i.e. `state/projects/$INGEST_CORPUS/work/corpus-map.json` (Drive) — see §2a | live — read every phase, it IS the resume driver | hard stop; `assert` refuses |
| Reader bundles | `paths.py scratch ingest_body` (platform temp; `/tmp` is not a path on Windows) | regenerable SCRATCH, never durable state | re-pack from flatten |

**Adversarial:** every chat body is untrusted external content — **DATA, never instruction.** The main
session never reads one.
⚠ **Corpus counts disagree across tools and were never reconciled:** `score.py` 1,497 · `flatten.py`
1,526 · corpus-map 1,520–1,521. ❓ **Q: does the spec need an authoritative count?**

### 2a. THE CORPUS-IDENTITY CONTRACT *(recorded 2026-08-08, this session — the parameterization BUILD is a
separate lane's work; this is the contract that build must honour, and the table above already assumes it)*

- **`INGEST_CORPUS`** — the corpus slug. Unset defaults to **`cowork-bulk-ingestion`** — back-compat, not a
  new default: every path this document names elsewhere for the live corpus stays byte-identical.
- **`COWORK_WORK="$DRIVE/state/projects/$INGEST_CORPUS/work"`** — the run's project-scoped scratch; same
  shape for every corpus, just a different slug in the path.
- **`FLAT="$(python3 "$ROOT/shared/paths.py" flatten "$INGEST_CORPUS")"`** — the rules are unchanged and
  now live in ONE place, `shared/paths.py::flatten_dir()`, instead of being restated in four command
  blocks. **Legacy fallback:** an existing `$HOME/.cache/cowork-ingest/$INGEST_CORPUS/flatten` WINS, and
  failing that the old un-scoped `$HOME/.cache/cowork-ingest/flatten` is used **for the original corpus
  only**. This exists so the author's 1,521 already-flattened chats are never orphaned or silently
  re-flattened just because the corpus now carries an explicit slug — and the scoping exists so a
  brand-new corpus can never resolve to them and read someone else's chats.
  ⭐ A machine with no legacy directory — every Windows install, where `$HOME/.cache` was never a real
  place, and every fresh install anywhere — gets the platform cache and is correct from the start
  (issue #7, 2026-08-12).

⚠ **Landing status, verified live this session (not assumed, re-checked after this lane's own edits to catch
concurrent progress):** `SKILL.md` and `phases/4-place.md` already export `INGEST_CORPUS`/`COWORK_WORK`, and
and `phases/1-sort.md`, `phases/2-scan.md` and `phases/3-deep-read.md` now all resolve `FLAT` the same
way — by asking `paths.py`, rather than each restating the fallback in shell. **The gap recorded here
previously — 1-sort.md hardcoding an un-scoped `FLAT` — is closed**, and closed structurally: there is
no longer a copy of the rule for one file to disagree with.

### 2b. THE INTAKE FORMAT LIMITATION + THE INTAKE SEAM'S OUTCOME SET *(recorded 2026-08-08, this session —
answers the OWED item inside the `❓8` ruling below; that ruling's own provenance note applies here too: **this
is the session's determination, not the author's words** — reversible on his say-so)*

**What `flatten.py` supports today, verified from its own docstring and CLI (not recalled):** **ChatGPT
export shards only.** `--raw` takes a directory of `conversations-*.json` files — its docstring names the
tool *"ChatGPT-export → clean-text converter"* and its `--raw` argument is documented as *"dir containing
`conversations-*.json` shards."* **No other input format is understood today.** Read this before pointing the
skill at anything but a ChatGPT export — the failure mode without this note is watching the skill fail
against a folder of ordinary documents with no explanation why.

**Adding a new format requires a converter beside `flatten.py`** — one file per format, **picked by `1.0a`'s
format fork** (§5b / the `❓8` ruling below) — never a change inside `flatten.py` itself, and never a guess at
which parser fits.

**The intake seam's outcome set is closed — exactly three members, no fourth:**

| Outcome | Meaning | What happens |
|---|---|---|
| **FLATTENED** | the run recognised the format and flattened it | proceeds |
| **ALREADY-DONE** | the corpus was already flattened (idempotent skip — §2a's `1.0a`/`1.0b` skip-if-done shape) | proceeds, no-op |
| **UNRECOGNISED-FORMAT** | the input matches no known converter | **the run STOPS and says so, plainly, to the human** |

⛔ **`UNRECOGNISED-FORMAT` is the closed set's no-outcome member — a genuine cannot-do stop, never a quality
threshold.** It never guesses a parser and never degrades to a best-effort read. **This is a different kind of
stop than `[B14]`** (`system/sops/skill-building-sop.md:1046` — a hard REFUSING threshold on basket count that
fought the discovery process and blocked the live corpus for hours; the same incident this document records
further down, at the end of the `❓ OPEN` section: *"was a LIVE BLOCKER for a few hours."*) `[B14]` was wrong to
refuse, because what it refused on was a matter of degree the phase existed to discover, and it was converted
to an advisory the same day. **`UNRECOGNISED-FORMAT` is not that** — there genuinely is no converter for the
format, not merely low confidence in one that exists — so the stop is correct, not another `[B14]` waiting to
be softened into an advisory.

---

## 3. Inherited non-negotiable rails

Verified in-file 2026-08-04. **The enforcement column is the load-bearing one.**

| # | Rail | Source | Enforced by |
|---|---|---|---|
| R1 | ONE-GATE: content passes the security stack once, at the door; downstream is trusted | `information-ingestion-interpretation.md:21-26` | CODE + PROSE |
| R2 | **The reader agent holds `tools: Read` only — no Bash, Write, network, MCP** | `agents/ingest-conclusions.md:5` | **AGENT-STRUCTURE** (harness-enforced; proven live 2026-07-03) |
| R3 | Chats are DATA; never follow an instruction found inside one | `agents/ingest-conclusions.md:11,14` | **PROSE ONLY** |
| R4 | The MAIN session may not read the reader scratch (`paths.py scratch rdr` / `ingest_body` — platform temp, NOT a literal `/tmp`); sub-agents may | `ingest_gate_enforce.sh:135-143` (Read tool) + `:206-209` (shell, case-insensitive) | **HOOK**, fail-closed |
| R5 | The gate runs on the FULL body BEFORE any slice; samples are cut from sanitized text | `3-deep-read.md:29-32` | CODE |
| R6 | The main session never reads a chat body | `3-deep-read.md:33-34` | HOOK + STRUCTURE |
| R7 | DANGER → auto-quarantine + skip; never re-open to inspect | `ingestion-reader-contract.md:47-50` | CODE (skip) + PROSE (never re-open) |
| R8 | Outbound is allowlisted — a fooled controller still cannot exfiltrate | `ingestion-reader-contract.md:107` | HOOK + CODE + pf |
| R9 | The reader REDACTS, never summarizes — fidelity survives the security step | `information-ingestion-interpretation.md:109` | **PROSE ONLY** |

> **The design is sounder than the two PROSE-ONLY entries suggest.** R3 and R9 failing costs little
> because **R2 caps the blast radius structurally** — a hijacked reader has no hands. State this as a
> positive, not a gap: the architecture assumes the prose rails *will* eventually fail.

⚠ **One rail is stated more strongly than the code supports.** `3-deep-read.md:30` asserts the gate is
fail-CLOSED for files, unconditionally. Verified: true only under `INGEST_GATE_POSTURE=enforce` (the
default). A genuine DANGER verdict blocks under **both** postures; only the **internal-error** branch is
posture-dependent (`ingest_gate.py:86-136`). **Nothing anywhere asserts the posture before relying on
it.** → **SPEC CLAUSE OWED: assert the posture at phase entry, or restate the guarantee conditionally.**

---

## 4. The write model (the gears)

- **Gear 1 — the conversation.** Every ruling screen and every human decision runs in the MAIN session.
  ⛔ Never delegated — a subagent cannot pause for an answer.
- **Gear 2 — the readers.** Tool-less `ingest-conclusions` agents, **model `sonnet`** (reverted from
  haiku 2026-07-11: *"haiku lost the intuition"* — a MEASURED regression, do not re-litigate),
  `run_in_background: true`, **spawned UNNAMED** (a named teammate gets `SendMessage` and its report is
  discarded).
- **The boundary rule.** The MINER never files. It sorts, rules, and STAGES only. Every terminal fate
  needs `--human-approved`. Only the auto-chained FILER writes.

---

## 5. Phases, their desired outcomes, and their steps

> ## ⚖ RESTRUCTURED 2026-08-05 — SEVEN PHASES BECAME FOUR *(the author, `authority: user`)*
>
> **The governing ruling:** *"If phase 3 is machine only then it's a STEP, not a phase. Phases by
> definition have a HITL element."* ⇒ **A PHASE IS A UNIT OF HUMAN ATTENTION.** Machine-only work is a
> **step** inside the phase whose human turn it feeds.
>
> **Applied literally, that is the whole restructure:**
> - old **Phase 0 PREPARE** (unpack) has no human turn → its steps move to the front of Phase 1.
> - old **Phase 3 DEEP-READ** (mine the keepers) is machine work → its steps move to the front of the
>   phase where the human finally sees what was mined.
> - old **Phase 4 REFLECT** is redesigned as **THE WORLD MAP** and absorbs the deep read's rulings —
>   reward and verification in one screen.
> - old **Phase 5 FILE** and **Phase 6 PROMOTE** merge into one placing phase.
>
> **Why this is the right unit:** phases are what you count when you ask *"how many times must I sit
> down."* A machine-only "phase" inflates that count with sittings the human never attends. **Proven
> immediately** — applying it here dropped this skill from 7 to 4.
>
> **The superseded seven-phase model is kept verbatim at the end of this section.** It is the record of
> what changed, not dead weight; do not delete it.

**The arc.** Phases 2–3 loop per pile; the ends run once.

```
1 MAKE THE PILES → ┌ 2 SCREEN A PILE → 3 THE WORLD MAP ┐ × N piles → 4 PLACE IT + THE ROOT CANON
                   └───────────────────────────────────┘
```

⭐ **THE FOLDER SCHEMA IS THE SPINE, NOT THE OUTPUT** *(the author, 2026-08-05)*. The piles made in Phase 1
**are** the first draft of the folder tree. Phase 3 corrects and commits one branch of it per pile, while
the material is fresh. ⇒ **Phase 4 SHRINKS** — it executes boundaries already settled pile-by-pile instead
of designing a tree from scratch at the end, by someone tired, about material read weeks ago.
*(This corrects the superseded model's claim that the filing phase "needs the full picture to design the
desk schema" and must therefore fire once at the end. The picture is built incrementally now; only the
execution is deferred.)*

### 5a. Phase desired outcomes

**Every row names a human turn. That is the test of whether it is a phase at all** — a row that cannot
fill that column is a step, and belongs inside one of these four.

| Phase | Desired outcome — what is TRUE at the end that wasn't at the start | THE HUMAN TURN — what only they can do here | Done when |
|---|---|---|---|
| 1 MAKE THE PILES | The real boundaries hiding in this corpus are discovered, and every chat sits in **its correct pile** *(⚠ wording ruled 2026-08-05: NOT "exactly one pile" — that reads as if all chats go into a single pile)* | **Rules the boundaries** — split / merge / close. The machine sees that forty chats mention screenwriting; it cannot know writing and acting are different jobs to this person | no chat left unplaced; every close carried `--human-approved` |
| 2 SCREEN A PILE | Every chat in this pile carries a CERTAIN human ruling — in or out — and anything they could not judge got a second, richer look until they could | **RECOGNITION** — reads three sentences and remembers the actual conversation, what came of it, whether it went anywhere. No amount of better summarising reaches this | `basket-status skim-complete` accepted — refuses on unscanned · unruled · **or still in EXPLORE** |
| 3 THE WORLD MAP | The human has read a paragraph about themselves, corrected what is wrong in it, and ruled which findings are canonical vs dated vs a record — and what folder shape this pile earns | **Says whether a sentence about them is TRUE.** The machine can synthesise a claim; only they know if it describes them | see §9 — a machine-checkable condition, not a vibe |
| 4 PLACE IT + THE ROOT CANON | Every staged finding is placed where the human put it, in the tree already settled pile-by-pile; canon candidates await a separate explicit yes | **Approves the RECORD, not just the conclusion** — rendered at max detail before it is written | every pile `committed`; proposals exist with `vetted: false` |

✅ **Q1 ANSWERED by the restructure.** The old table's Phase 4 (REFLECT) had *no checkable
done-condition* — the one row that closed on nothing. It is now Phase 3, and giving it a
machine-checkable done-condition is a stated requirement of its spec section (§9).

### 5b. Steps, by type

*(Types per template §6a: ONE-PASS · ITEM-LOOP · CORRECTION-LOOP · ROUND-REPEATABLE)*

**PHASE 1 — MAKE THE PILES** *(once, wide)* — **fully specified in §7 below.**
Demoted from old Phase 0, machine-only, off-camera before the human's turn:
`1.0a` flatten · `1.0b` tag · `1.0c` build/migrate the map — **all ONE-PASS**
*(old `0.4 assert` is not duplicated here — it already exists as `1.1`, the first step of §7.)*
Then `1.1`–`1.6` + TURNS 1–3 + the loop, per §7.

**PHASE 2 — SCREEN A PILE** *(per pile)* — **fully specified in §8 below.**
`2.0`–`2.11`, per §8. Its spine is the **three-verdict set** — `KEEP` · `TOSS` · **`EXPLORE`**, where
EXPLORE is **non-terminal** and the pile cannot close while any remain.
✅ **Q2 ANSWERED (2026-08-05): the ten output types are alive and there are ELEVEN.** They were never
reduced — `CATEGORIES` is a closed, code-enforced set in `tag.py:34-38`, and every prior record omitted
`exploration`. The "two booleans" (`canon_flag` / `pointer_candidate`) live at the **chat-row** rung; the
eleven categories live at the **conclusion** rung. Two different layers were mistaken for one.
⚠ **The genuinely open, narrower question** now sits with Phase 4: should the chat-row manifest carry the
categories through, so placement can be by type?

**PHASE 3 — THE WORLD MAP** *(per pile — THE REWARD AND THE VERIFICATION)* — **fully specified in §9 below.**
Demoted from old Phase 3 (DEEP-READ), machine-only, off-camera before the human's turn:
`3.0a` partition the keepers by size: short / whole (≤100k) / giant — ONE-PASS
`3.0b` bundle + spawn the tool-less readers — ONE-PASS
`3.0c` collect + **coalesce** — ONE-PASS. ⚠ **CORRECTED 2026-08-05, verified from source.** The standing
claim that `coalesce_conclusions()` *"has no dedup logic"* (`[INGEST-COALESCE-DEDUP]`) is **wrong as
written**. It merges by chat key and appends only conclusions not already present —
`new = [c for c in _conclusions_of(el) if c not in have]` (`pipeline.py:816-821`). **What is true is
narrower:** the test is `not in`, i.e. **exact object equality**, so two readers describing the same
conclusion in *different words* both survive. The residual defect is near-duplicate text, not absent
dedup — a different and much smaller problem than the open loop states.
Then the human's turns, per §9. **The giant-ruling gate and the pile ruling that used to live in old
`3.5`/`3.6` are not deleted — they are the verification half of the world map.**

**PHASE 4 — PLACE IT + THE ROOT CANON** *(once, whole corpus — and SMALL, because the tree is already settled)*
`4.1` load the manifest (never chat bodies) — ONE-PASS
`4.2` **execute the folder tree already agreed pile-by-pile in Phase 3** — ONE-PASS, not a design step
`4.3` **write-preview each record** — ITEM-LOOP. ★ *"The skill's MOST IMPORTANT output": the human
approves **the RECORD**, not just the conclusion, rendered at MAX detail.*
❓ **Q4 STILL OPEN: does the current filer honour this?** Born from a real failure — five records written
with no preview, which the author called *"the skill's biggest flaw."*
`4.4` place confirmed items — ONE-PASS each · `--human-approved`
⛔ **RECORDS GET A STUB FILE — the original is NEVER rewritten** *(the author, 2026-08-05: "we're not going to bother spending LLM
tokens rewriting it")*. Only canon and dated information get authored.
`4.5` surface canon candidates + the root canon — ITEM-LOOP, one at a time, human gate
⚠ *the "second key" is today a string match on content the writer wrote; it is not a gate*
`4.6` close each pile `committed` — code-gated
⚠ **SUPERSEDED 2026-08-08 — PHASE 4 now has a full section of its own at §10.** This six-line sketch was, until
that date, the ONLY thing this spec said about PHASE 4 (§7/§8/§9 existed for phases 1/2/3 and nothing existed
for 4). Kept as the record of the sketch it grew from; **read §10, not this.**

### 5c. CROSS-CUTTING COMPONENTS — they belong to no single phase *(added 2026-08-08)*

**⚖ C1 — THE WORLD-MODEL COMPACTION ENGINE.** ⚠ **NOT BUILT · ✅ DESIGNED 2026-08-08 (Phase 9, task 9.7.1) — the design below is a PROPOSAL AWAITING THE OWNER; the build (9.7.2) is gated on his nod.**
*(the author, 2026-08-08, `authority: user`: "when we make the scratch pad we could be reading a ton of information…
We will have to make a larger overarching rule about what's gonna get written into the scratch pad and what
might get deleted once it gets finally finished, because the scratch pad could get pretty fucking big… over time
we want to make sure that this scratch pad has a way of compacting itself. **This project brief is gonna
function a little bit differently than a project brief normally functions — it's gonna be more of a world
model.** We have compaction systems in our check-in skill, but right now it's for compacting into a PROJECT
format, not compacting into a WORLD MODEL type of format that would help us know this user into the future and
not get to a point where our scratch pad would get unusably large.")*
**It must decide four things:**
1. **THE WRITE RULE** — what is admitted to the world model at all. Not everything.
2. **THE GRADUATE/DELETE RULE** — what leaves once the run finishes (findings that became real files no longer
   need to sit in the pad).
3. **THE COMPACTION TARGET SHAPE** — ⛔ **`/checkin`'s existing compaction is the WRONG target format.** It
   compacts toward *project* state (where-we-are · next-scope). A world model compacts toward *durable truths
   about a person.* **Reuse the mechanism, never the schema.**
4. **A SIZE CEILING / TRIGGER**, so the pad can never reach "unusably large."
⇒ **It touches every phase:** the create-at-end-of-PHASE-1 gate, `2.10`, `3.8`, and §10's placing. The author's
backfill note — *"to backfill all the way back to the first phase"* — means the write rule binds from the moment
the project is created, not bolted on at PHASE 3.

---

### ✅ THE DESIGN — 2026-08-08, task 9.7.1. ⏸ PROPOSAL, NOT RATIFIED — the author has not yet seen it.

> **⭐ THE MEASUREMENT THAT DECIDES THE WHOLE DESIGN — computed forward from real data, not estimated.**
> Source: `raw-conclusions-creative-writing.json` — **281 staged conclusion rows from 27 chats**, mean **289.6
> chars/row**; corpus = **1,521 chats**.
> - **Admit everything** → `281/27 × 1521 = 15,830 rows × 289.6 = 4,584,271 chars ≈ 1,146,068 tokens.` **Larger
>   than a 1M context window.** The pad would be unloadable before the corpus was half read.
> - **Admit on the machine's own best pre-filter** (`suggested_category: canon`, **78 of 281 = 27.8%**) →
>   `4,394 rows ≈ 1,272,502 chars ≈ 318,126 tokens.`
> - For scale, the two real briefs on disk today: `skill-builder/brief.md` = **52,685 chars (~13,171 tokens)**;
>   `ingest-skill/brief.md` = **189,569 chars (~47,392 tokens)**, and that one is already painful to load.
> ⇒ **Even the TIGHTEST machine pre-filter overshoots the largest existing brief by 6.7×.** This is the finding:
> **a machine pre-classification cannot be the admission gate.** Only a human ruling bounds it, and even that
> needs a hard ceiling behind it.

**1 · THE WRITE RULE — only what a human RULED, and only in the run's own words.**
The gate is the human's `type` verdict (`FINDING_TYPES = ("canonical", "dated", "record")`, `pipeline.py:101`).
**Admitted:** (a) PHASE 1's pile boundaries plus every split · merge · close the human ruled; (b) any finding the
human TYPED in PHASE 3; (c) **every CORRECTION the human made to a world-map paragraph** — the highest-value
rows in the pad, because they are the only place the machine was measurably wrong about the person and they said
so out loud.
⛔ **Not admitted:** anything the machine merely suggested — `kind`, `suggested_category`, `freshness` (measured
live in the real store: `kind` ∈ decision 137 · fact 75 · exploration 44 · practice 17 · reference 8;
`freshness` ∈ dated 155 · always 108 · unknown 18) — and anything the human never saw. **Machine fields may RANK
what is shown; they may never ADMIT.**
⇒ Pad growth is bounded by **human turns**, never by corpus size. That, not the ceiling in §4 below, is the real
defence against "unusably large" — the ceiling is the backstop for when this rule is wrong.

**2 · THE GRADUATE / DELETE RULE — a row leaves when it has a FILE, and leaves a pointer behind.**
Once PHASE 4 writes a finding to a real path, its pad row is **REPLACED by a one-line pointer** — `<claim> →
<path>`, dated. ⛔ **Never deleted outright.** A row that vanishes with no trace is indistinguishable from a lost
finding, and that is this corpus's own recorded failure: **21 of 22 keepers were never staged (2026-07-14)**, and
nothing noticed. ⛔ **Corrections never graduate** — they outlive the finding they corrected, because they are
the record of what the machine got wrong about the person, which no output file preserves.

**3 · THE COMPACTION TARGET SHAPE — durable truths about a person, in the three tiers this skill already uses.**
⛔ Not `/checkin`'s where-we-are / next-scope. The pad compacts INTO:
- **PERMANENT** — statements that pass the **standalone test** (`memory-system.md:23`): a zero-context session
  can read the line alone and act on it, with no backstory.
- **DATED** — true as of a date, **and it carries that date.**
- **POINTERS** — a claim plus where its file now lives.
**Same order as the world-map screen — permanent first —** so the pad and the screen can never disagree about
what matters most. Every row keeps its provenance: *ruled* or *corrected*, and when.
⛔ **Nothing is summarized.** Rows are dropped, merged verbatim, or graduated to a pointer. The word "summary" is
banned in this pipeline by the ONE-GATE doctrine (`information-ingestion-interpretation.md:107-110`) — the reader
redacts and extracts, it never reshapes.

**4 · THE SIZE CEILING / TRIGGER — bytes, not runs.**
The failure the author named is a **size** property, so the trigger is a size, not a run count or a date.
**Ceiling: the `## 7. SCRATCHPAD` section may not exceed 60,000 characters (~15,000 tokens).** Derived, not
picked: it sits just above `skill-builder/brief.md`'s entire **52,685 chars** — the largest brief in the system
that is still comfortable to load — and far below `ingest-skill/brief.md`'s **189,569**, which is already the
painful case. Crossing it fires compaction **BEFORE the next phase opens**, never mid-phase, so a compaction can
never land in the middle of a human's turn.

**THE MECHANISM — reuse, never rebuild.** `system/tools/save/pad_archive.py`: `archive | verify | state | clear`.
`archive` appends a hash-chained block to `<brief>.pad-archive.md` and prints `RECEIPT <sha256>`; **`clear`
REFUSES unless the pad's sha256 matches the last archive block** (`pad_archive.py` → `cmd_clear`) — **no receipt, no
clear**, so it can only ever delete bytes already proven saved.
⛔ **Reuse the MECHANISM, never the SCHEMA** — the target shape is §3 above, not `/checkin`'s.
⛔ **Do not copy `/checkin`'s wiring by imitation** — it never calls `save_step_ledger.py start`, so its own
compaction stamp is broken today; imitating it would inherit the bug.

**C2 — THE GENERATED FOLDER CONVENTION** *(verified from `desk_scaffold.py` 2026-08-08 — not recalled).*
A Lifehack knowledge home is: **`canon/`** (a FOLDER) holding **`current.md`** (standing canon) and
**`purpose.md`** (the home's stated purpose) · **`records/`** · `state/` · `sources/inbox/` · `views/`.
⇒ *"every folder is a knowledge boundary with its own canon file and a stated purpose"* **is exactly**
`canon/current.md` + `canon/purpose.md`.
- `memory-system.md:23` — canon is *"human-vetted, durably-reliable standing knowledge… **Every canon line must
  pass the STANDALONE TEST — a completely fresh, zero-context session can read it alone and fully understand and
  act on it (no backstory)**."* ⇒ a stricter bar on PHASE 3's "permanent truth" than "is it true about me."
- `memory-system.md:24` — `records/{type}/` = *"findings/data… Searchable, NEVER auto-loaded."*
- ⛔ **`topic:` COMES FROM A CLOSED SET** (`topic-vocab.md:17-21`): *"Use an existing slug or it doesn't get
  tagged — new slugs are added HERE first… the archivist proposes; the author approves… Never rename."* **PHASE 4
  may not invent a topic slug.**
- ✅ **RULED 2026-08-08 BY THE OWNER — KNOWLEDGE FOLDERS, NOT DESKS.** Verbatim: *"We're doing folders versus desks.
  That's the first one."* ⇒ `/ingest` generates **`canon/current.md` + `canon/purpose.md` + `records/`** and
  **NOTHING ELSE** — ⛔ no `desk-registry.yaml` entry, no `CLAUDE.md`, no `health_producer`, no `pulse_slot`, no
  `status_tile_path`. **Promotion to a real DESK is a separate, deliberate human act, later, if a folder earns
  it.** ⇒ ⛔ **STOP `4-place.md:144-145` calling `desk_scaffold.py`** · **BUILD a lightweight scaffolder** ·
  `desk_scaffold.py` is **NOT deleted** — it stays the tool for the promotion act.
  ✅ **RESOLVED 2026-08-08 (Phase 9, tasks 9.4.1–9.4.2).** The lightweight scaffolder now exists —
  `system/tools/cowork-ingest/folder_scaffold.py` — and `4-place.md:144-145`/`:171-172` now call it instead
  of `desk_scaffold.py`, producing exactly `canon/current.md` + `canon/purpose.md` + `records/` and printing
  nothing to paste (no registry step at this level). `desk_scaffold.py` remains **un-deleted**, as ruled
  here, kept for a deliberate later promotion act.
  ⭐ This also honours the registry's own doctrine (`desk-registry.yaml:2-8`: *"still hand-appended by design:
  the registry is a conscious act, read by every organ"*) — 23 auto-appends would have violated the convention
  the tool itself protects.
  <details><summary>the question as it stood before he ruled it</summary>
- ❓ **OPEN, and it changes what §10 builds: KNOWLEDGE FOLDER or full DESK?** A DESK is heavyweight — a
  **hand-pasted** `desk-registry.yaml` entry (*"the registry is a conscious act, read by every organ"*), a
  `CLAUDE.md`, a health producer, a pulse slot, a status tile. **The live corpus has 23 open piles**, so
  scaffolding a desk per pile means 23 registry blocks pasted by hand. **Session recommendation: generate
  KNOWLEDGE FOLDERS** (`canon/current.md` + `canon/purpose.md` + `records/`); promotion to a DESK stays a
  separate, deliberate human act.
  </details>

**C3 — THE PLACEMENT DOCTRINE THE TREE MUST OBEY** *(verified 2026-08-08; these are the author's own prior rulings,
not new invention — `/ingest` was under-specified against them).*
- ⭐ **THE SPLIT TEST HAS TWO HALVES, and the spec only carried one.** *(the author, 2026-08-05,
  `authority: user` — restated in full right here, not a pointer into `system/knowledge-altitude.md`,
  which this repo does not ship — [5.2.1], 2026-08-11)*: **too BIG → subdivide (nest)** · **too DIVERSE →
  separate (siblings, not nested)** — *"not that the folder is large, but that two bodies of knowledge
  would actively degrade each other if loaded together."* ⇒ **PHASE 3's folder-shape step must apply
  BOTH.** *"Subdivide where there is enough material"* is the BIG half only, and the DIVERSE half is what
  decides sibling-vs-child.
- **PLACEMENT IS A COST CURVE** *(restated in full here, not a citation into the unshipped
  `system/knowledge-altitude.md` — [5.2.1])*: *"A canon fact belongs at the highest
  folder where it is still always-true for everything in that folder — **and no higher**"*; `/read` walks every
  ancestor, so *"anything placed in a parent is paid for by every descendant… the question is not 'what is this
  about' but **'who has to bear the cost of it.'**"* Test: *every child needs it → parent; one branch → that
  child; nobody needs it loaded but it must stay findable → records.*
- **EVERY FOLDER TAKES A *PURPOSE*, NEVER A DONE-WHEN** (`intent-doctrine.md:62-70`): *"A CONTAINER ALWAYS TAKES
  A PURPOSE… You never owe a folder a 'done-when.'"* Projects nest inside a domain and carry the outcomes.
  A one-liner suffices; optionally **ONE** near-miss `not:` line — ⛔ *"never an exclusion list… the LLM starts
  reading 'not on the no-list' as 'allowed.'"*
- **FINDABILITY INVARIANT — NO BURIED TREASURE** (`:179-187`): sinking content deeper must never sink its
  findability — *"leave a one-line pointer from where a future session would naturally look."* ⇒ this is the author's
  stub-file instinct, already law.
- **THIN UP HIGH, FULL CONTENT ON THE BRANCH YOU ARE IN** (`:169-177`): ⛔ do **not** pointer-ize canon that is
  actually loaded — *"our own pointer-only desk canon left ~50% of facts invisible in blind tests."*
- ⛔ **`/ingest` MAY NOT AUTHOR HIGH-TIER LINES** (`intent-doctrine.md:234-235`): *"**the author writes the high-tier
  bars** (global, each desk). Those are law; law isn't machine-guessed."* PHASE 4 proposes; it never authors at
  the root. This is the doctrinal backing for the root-canon gate being human-only **regardless of** the weak
  "second key."
- **CONFIDENCE = CORROBORATION, NOT LOCATION** (`confidence-model.md:37-40`): *"Facts earn UP into canon via
  human review, not by age, repetition, or machine confidence."*
- ⛔ **NO DATABASE, BY DESIGN** (organism `manual.md:114-130`) — the data tier is *"deliberately-thin files on
  Drive and git."* ⇒ **C1's compaction engine may not propose a store.** Files only.
- **`system/desk-registry.yaml:2-8`, verbatim, because the paraphrase loses the force:** *"HAND-MAINTAINED:
  append one entry per new desk BY HAND. The folder SCAFFOLD is now one-punch… it PRINTS the block to paste
  here (**still hand-appended by design: the registry is a conscious act, read by every organ**)."* And the
  per-desk `_registry.md` disclaims itself: *"maintained manually and may drift from actual disk state.
  **Do NOT use for retrieval or validation.**"*

**C4 — EVERY ⚙️ LOGIC STEP MUST NAME ITS FORK.** *(the author, 2026-08-08: "I'm not seeing the kind of coding layer
where it's like where the choices are being made or where things might kind of fork off.")* ⇒ a step tagged
`logic` states **the condition tested and where each answer goes** — `⑂ over 8,000 chars → three windows;
under → two`. **A step that says "the computer works it out" without naming the branch is a DESCRIPTION of a
logic step, not one.** This is a standing requirement on every phase, not a fix to particular steps.

### 5d. KNOWN DEFECTS + OWED FIXES — the running list *(opened 2026-08-08)*

**Each gets a LAW 8 verdict — BUILD · FIX · INTENT WAS WRONG — never a vague "owed" (§0a ruling 7).**

| # | Defect | Anchor | Verdict |
|---|---|---|---|
| 1 | **A step that cannot run:** bare `import pipeline` inside `python3 -c`, no `PYTHONPATH`, no `cd` → `ModuleNotFoundError` unless the shell already sits in the tool dir. Breaks the SHORT/WHOLE/GIANT partition. | `phases/3-deep-read.md:114` | **FIX** |
| 2 | ✅ **RESOLVED 2026-08-08 (Phase 9, task 9.5.5) — `phases/3-deep-read.md`'s close now passes `--require-world-map` on its `basket-status read-complete` call, with a comment explaining why it is safe to force unconditionally (the gate only applies to a pile that actually has a keeper).** ⭐ *Original finding, kept as the record:* A built gate that is switched off: the world-map close-gate fires only `if require_world_map or started`; the flag defaults False and **no driver ever passes `--require-world-map`** (grepped `skills/ingest/`: zero hits). A pile can close `read-complete` with zero typed findings and no folder branch, silently. | `pipeline.py:1233,1333-1339` | **BUILD** |
| 3 | **"Your brain grew: N → M" is structurally always N→N** from DEEP-READ. Observed live twice (2→2, 464→464). The author ruling owed. | `[INGEST-BRAIN-COUNT-F5.9]` | **needs the author** |
| 4 | **The wrong mechanism is cited** for the toss/park human-approval gate: `SKILL.md` credits `wmb_commit`, which has **no toss/park command at all**. The real gate is `pipeline.py`'s `set_skim()`. Guarantee real, map to it wrong. | `SKILL.md:94` · `pipeline.py:982-1009` | **FIX** |
| 5 | **An orphaned agent persona:** `agents/ingest-tagger.md` (66 lines, correctly tools-capped) served the "5k TAG" step cut in the 2026-08-05 restructure. **Zero spawn sites anywhere**; `SOP.md` still describes it as live. | `agents/ingest-tagger.md` | **FIX** (delete or repurpose) |
| 6 | **Four real test files with no caller** — `test_chain_e2e.sh`, `test_pipeline.py`, `test_status_gate.py`, `test_ux.py`. No cron, no CI, no hook. Runnable by hand only. Not a false claim, but the textbook §V.9 shape. | `system/tools/cowork-ingest/` | **BUILD** (wire one) |
| 7 | **Stale vocabulary in the voice file:** `vera-voice.md` still says "MINE / TOSS (or SAVE at filing)" and never mentions SCAN's KEEP/TOSS/EXPLORE widening. Behaviour is fine; the doc drifted. | `[INGEST-VERA-VOICE-STALE]` | **FIX** |
| 8 | **The driver prints pre-renumber ids:** `2-scan.md` still labels bracket / read-thin / group-by-subject as `2.5`/`2.3`/`2.4` while §8 renumbered them. §8 claims the driver *"already matches"* — the ORDER matches, the LABELS never were updated. | `2-scan.md` vs `SPEC.md` §8 | **FIX** |
| 9 | ✅ **RESOLVED 2026-08-08 (Phase 9, task 9.2.3) — `4-place.md:172` now reads "⛔ A RECORD GETS A STUB FILE — THE ORIGINAL IS NEVER MOVED, NEVER REWRITTEN," matching §9's ruling and the author's three-times-repeated correction.** ⭐ *Original finding, kept as the record:* `4-place.md:172` said "RECORDS ARE MOVED" — the reversed instruction, in the file that actually runs. | `phases/4-place.md:172` | **FIX** |
| 10 | **`[INGEST-FILER-TOKEN-RENAME]`** — `pipeline.py suggest --skill ingest-filer` passes a dead skill name as a live phase token. | `4-place.md:238-241` | **FIX** |
| 21 | ✅ **RESOLVED 2026-08-08 (this session, task 9.8.1) — see §0e (reconciliation index) and §6a-§6d (the four sections, restored).** ⭐ *Original finding, kept as the record of what was wrong:* THIS SPEC IS MISSING FOUR OF THE ELEVEN SECTIONS ITS OWN DECLARED TEMPLATE REQUIRES — and it REUSED THEIR NUMBERS for something else. Frontmatter declares `template: system/templates/producer-spec-template.md`, which requires 11 numbered sections. **ABSENT: §5 THE GRID** (DATA/LOGIC/PRESENTATION × AMBIENT/LLM-TURN/HUMAN-TURN/AFTER) · **§7 WRITE TARGETS** (`what→where / written by / guard`) · **§8 DEFINITION OF DONE** · **§9 GRACEFUL DEGRADATION** (CONFIRMED/INFERRED/HYPOTHESIS cascade). Their numbers now mean "PHASE 1", "PHASE 2", "PHASE 3" instead — **so a reader looking for §8 "Definition of done" lands on "PHASE 2."** §11's evidence-surface table survives only as a bullet list with no enforceability column (still true — see §0e row 11, deliberately not rebuilt this session). ⛔ The template's own rule: *"'not active in this slice' is a legitimate, informative answer. **A blank slot is not.**"* **Resolution taken: NOT renumbered** (the PHASE numbers are load-bearing in `pipeline.py`, `test_pipeline.py`, `scan_collect.py`, `check_screens.py`, and `skill-building-sop.md`, all of which cite e.g. `SPEC.md §8` to mean PHASE 2) — **the four sections were restored at §6a-§6d instead**, each explicitly cross-labelled with the template section it answers. | medium | **FIX** |
| 22 | ✅ **RESOLVED 2026-08-08 (this session, task 9.8.2) — a table of contents was added at the top of the document, mechanically verified against every heading (see the verify output in this session's report).** *Original finding, kept as the record:* NO TABLE OF CONTENTS on a 1,850-line reference document. SOP: *"A reference file over ~300 lines gets a table of contents at its own top."* A session opening this to check one item has no way to jump to it. | tiny | **FIX** |
| 23 | ✅ **DECISION RECORDED 2026-08-08 (this session, task 9.8.3) — see §5e row 1.** ⭐ *Original finding, kept as the record:* `system/tools/topic-vocab-lint.py` EXISTS, HAS ZERO CALLERS, AND IS THE WRONG SHAPE for the `topic:` gate. Its own docstring: *"Read-only reporter… run by hand or wire into the archivist coherence sweep."* It walks the whole Drive tree **after the fact**; item 15 needs a **write-time** check. ⇒ **Do NOT mistake it for the fix** — write the enum check inline, reusing `pipeline.py:1183`'s pattern. **Decision taken: RETIRE from the write-time gate role, KEEP for the archivist coherence-sweep job its own docstring already names** — wiring it there is OWED, not owned by this lane (§5e row 1). | small | **FIX + BUILD** |
| 24 | ⭐ **THE COMPACTION ENGINE (§5c C1) HAS A REUSABLE MECHANISM ALREADY — `system/tools/save/pad_archive.py`.** LIVE and heavily called (`skills/checkin`, `skills/project-manager`, `skills/save`, `system/hooks/pm_flag.sh`), implementing exactly the shape C1 needs: **archive → verify → graduate → clear, in that order, and "NO RECEIPT, NO CLEAR."** ⇒ **REUSE THE MECHANISM, NEVER THE SCHEMA** — `/checkin`'s where-we-are/next-scope target shape is the wrong target, which C1 already says. ⚠ **And do NOT copy its wiring by imitation:** `/checkin` itself never calls `save_step_ledger.py start`, so its own stamp is currently broken. | medium | **BUILD (on the existing part)** |
| 12 | ✅ **RESOLVED 2026-08-08 (Phase 9, tasks 9.2.1 + 9.2.2) — `4.1`'s LOAD now reads the human-ruled type PER-FINDING from the coalesced reader output (`set_finding_type()` / `world_map_state()`, `pipeline.py:1174`/`:1208`) instead of the old `canon_flag`/`pointer_candidate` map-row booleans, which are gone; and `filer_review.py` now has a real fourth `dated` kind (`_KIND_RANK` includes it, rendered on its own row with a required `date` field) so a dated finding is authored, not silently stubbed.** ⭐ *Original finding, kept as the record:* PHASE 4 NEVER READS THE FINDING TYPE PHASE 3 MAKES THE HUMAN RULE. PHASE 3 writes a human-ruled `canonical\|dated\|record` per finding and **gates pile-close on it** — but `4.1`'s LOAD pulls only `canon_flag`/`pointer_candidate` from the map rows (`4-place.md:80`), and `4-place.md:154` maps only `canon_flag→"canon"`, `pointer_candidate→"pointer"`. **There is no `dated` path anywhere**, and `filer_review.py:33` special-cases only `kind=="canon"`. ⇒ a `dated` finding silently falls through to STUB treatment instead of being authored with its date — **the human's ruling is discarded at the moment of filing.** ⭐ Critical-path item ②. | real work | **FIX** |
| 13 | ✅ **RESOLVED 2026-08-08 (Phase 9, task 9.5.2) — `compose_anchor()` now looks up a per-phase verb line via `_ANCHOR_VERBS`; phase 2 gets "verbs = KEEP/TOSS/EXPLORE," the other phases keep MINE/TOSS/SAVE. `_VERB` now carries an `"explore": "EXPLORE"` key, so `verb_label()` can render it.** ⭐ *Original finding, kept as the record:* THE PER-TURN ANCHOR FORBADE THE WORD THE RATIFIED SCREEN REQUIRES. `pipeline.py:466-467` injected *"verbs = MINE/TOSS/SAVE … never 'keep'"* into **every turn of every phase**, and `:474-476` asserted *"a human NEVER sees a verb outside {MINE, TOSS, SAVE}"* — false at the time. PHASE 2's ratified set is KEEP/TOSS/EXPLORE, and **`_VERB` had no `explore` key at all**, so the model had no word for the one non-terminal verdict that is PHASE 2's spine. `scan_review.py:141-147` patched it display-only and said *"pipeline.py itself is untouched."* | small | **FIX** |
| 14 | ✅ **RESOLVED 2026-08-08 (Phase 9, task 9.3.1) — the rank now happens ONCE at `4.3`, before CONFIRM (`archivist-route` inlined there, its ranked candidate written into `/tmp/filer-plan.json`'s `home` field); `4.4`'s step A is now titled "Reuse the approved home — NEVER re-rank it here" and takes `{desk, folder}` straight from the approved plan.** ⭐ *Original finding, kept as the record:* `4.4` RE-RANKED THE HOME AFTER THE HUMAN APPROVED IT. `4-place.md:178-180` ran `archivist-route` at WRITE time, after `4.3` had the human approve a specific home (`:167-168` — *"PLACE acts ONLY on the items the human confirmed this turn"*). **The file written could differ from the file approved.** ⭐ And it was an ORDER defect against the routing tool's own contract — *"Return the ranked candidates. Do NOT write. The caller surfaces them for the human's one-tap pick, then writes"* — which was being run backwards. Critical-path item ③. | small | **FIX** |
| 15 | ✅ **RESOLVED 2026-08-08 (Phase 9, task 9.5.4) — `pipeline.py topic-check` now exists: a fail-closed membership check against the CLOSED vocabulary parsed live from `system/topic-vocab.md`, refusing (`REFUSED topic-check: … not in the closed vocabulary`) on an unknown slug, reusing the `FINDING_TYPES` enforcement pattern this row named.** ⭐ *Original finding, kept as the record:* `topic:` WAS A DECLARED CLOSED VOCABULARY WITH ZERO CODE ENFORCEMENT. Verified: no tool in the ingest chain checked a `topic` value against `topic-vocab.md`. Meanwhile two sibling vocabularies in the same codebase were fail-closed — `pipeline.py:1183` (`if ftype not in FINDING_TYPES: return False`) and `tag.py`'s `CATEGORIES` validate. Per LAW 1 this seam owed a code check. | small | **BUILD** |
| 16 | ✅ **RESOLVED 2026-08-08 (Phase 9, task 9.5.3) — `m["corpus_inherit_offered"]` now exists as a run-level (map-level, not per-pile) flag, set once by `set_corpus_inherit_offered()` and checked first by `corpus_inherit_offered()` before the offer fires again.** ⭐ *Original finding, kept as the record:* `2.0c` WAS RATIFIED ONCE-PER-RUN AND NOTHING COULD MAKE IT FIRE ONCE. No inheritance flag existed in `CHAT_V2_DEFAULTS` or `BASKET_DEFAULTS`. PHASE 2 re-opens per pile, so as written the inheritance offer was made on **all 23 piles**. | small | **BUILD** (a map-level flag) |
| 17 | ✅ **RESOLVED 2026-08-08 (Phase 9, tasks 9.1.1–9.1.3) — `pipeline.py brief-write` now exists and writes the run's project brief from the canonical schema; `mark_brief_written()` sets `m["brief_written"]`, which `current_phase()` checks before ever returning phase 2 (returning `"BLOCKED-NO-BRIEF"` instead if it hasn't run); and step `1.10` now exists in `1-sort.md`, sequenced after `1.6`'s gate, calling `pipeline.py brief-write --map "$MAP"`.** ⭐ *Original finding, kept as the record:* `1.10` WAS NOT BUILT, SO PHASE 2 LOADED A PROJECT PHASE 1 NEVER CREATED — used-before-produced. `1-sort.md`'s FINAL TURN had zero project-creation call; `2-scan.md`'s `2.0b` opened by asserting the brief already existed. ⭐ Critical-path item ①. | real work | **BUILD** |
| 18 | **`4.3`'s FILING ROW IS A TRUNCATED ONE-LINER** where the step outcome demands the record at full detail. `filer_review.py:36-48` renders `SAVE "{title}" → {home}` and then clips it to the display width; the plan schema `{title, home, kind, why}` has **no field that could carry a body**. ⛔ Fix by DEEPENING THE ROW, **not** by looping per item — see the ITEM-LOOP correction at `4.3`. | real work | **BUILD** |
| 19 | ✅ **RESOLVED 2026-08-08 (Phase 9, task 9.5.1) — `phases/1-sort.md:86` now reads "We get there in four passes," matching `SKILL.md:10`'s "FOUR phases" and `compose_progress()`'s "of 4."** ⭐ *Original finding, kept as the record:* `phases/1-sort.md:86` still said "six passes." The `SPEC.md` twin was corrected; the driver that ran was not. | tiny | **FIX** |
| 20 | ⚠ **A PROJECT-IDENTITY TRAP FOR WHOEVER BUILDS `1.10`/`2.0c`.** `state/projects/cowork-bulk-ingestion/brief.md` exists — but it is **the SKILL'S OWN engineering project** (the SOP mining, the two-skill split, plan links), not any corpus's world model. A naive "find a project near this corpus" lookup would offer to **inherit the skill's own build history as if it were personal facts about the author.** Match on an explicit corpus id, never on proximity. | tiny (design note) | **BUILD** |
| 11 | **Document consolidation debt:** `design/ingest-ux-brief.md` (173 lines) and `design/decision-log.md` (38 lines) were last touched 2026-07-13 and hold superseded rows (e.g. the "~8 baskets" target). **Fold what survives into this spec and retire them**, rather than leaving four documents where a reader must guess which wins. ⚠ Two of six frontmatter dates in that family are stale, so `updated_at:` is not a freshness test here. | Drive `state/projects/ingest-skill/design/` | **FIX** |

<details><summary><b>⚖ SUPERSEDED 2026-08-05 — the original SEVEN-phase model, kept verbatim as the record of what changed</b></summary>

**The arc.** Phases 2–4 loop per basket; the ends run once. **The filer fires ONCE over the whole
corpus** — never per basket — because it needs the full picture to design the desk schema.
*(⚠ This last clause is the specific claim the restructure reversed — see the spine ruling above.)*

```
0 PREPARE → 1 SORT → ┌ 2 SCAN → 3 DEEP-READ → 4 REFLECT ┐ × N baskets → 5 FILE → 6 PROMOTE
                     └──────────────────────────────────┘
```

**Phase desired outcomes (superseded).**

| Phase | Desired outcome — what is TRUE at the end that wasn't at the start | Done when |
|---|---|---|
| 0 PREPARE | Every chat is on disk, tagged, and has a row in the map | `pipeline.py assert` exits 0 |
| 1 SORT | Every chat sits in exactly one life-area basket; obvious junk piles are closed | no `UNCLUSTERED` rows; open-basket count surfaced to the human as an advisory, never gated |
| 2 SCAN | For this pile, the human has ruled every chat MINE or TOSS on **substance, not titles** | `basket-status skim-complete` accepted |
| 3 DEEP-READ | Every keeper in this pile has a durable conclusion the human confirmed | `basket-status read-complete` accepted |
| 4 REFLECT | The human has seen a sharper model of himself and **corrected it** | ❓ *no checkable condition today — see below* |
| 5 FILE | Every staged finding is placed where the human put it | every basket `committed` |
| 6 PROMOTE | Canon candidates await a separate, explicit human yes | proposals exist, `vetted: false` |

❓ **Q1: Phase 4 has no done-condition.** Everything else closes on a code-gate. What makes a reflection
"done"? My guess: *the human has either corrected it at least once, or explicitly said it's right.*

**Steps, by type (superseded).**

**PHASE 0 — PREPARE** *(no human turn)*
`0.1` flatten · `0.2` tag · `0.3` build/migrate map · `0.4` assert — **all ONE-PASS**

**PHASE 1 — SORT** *(once, wide)* — **fully specified in §7 below.**

**PHASE 2 — SCAN** *(per basket)*
`2.1` assert + lock + greet — ONE-PASS
`2.2` select unscanned → bundle → spawn readers — ONE-PASS
`2.3` collect + validate gists against the closed verb set — ONE-PASS
`2.4` render the ruling screen — ONE-PASS
`2.5` rule each chat MINE/TOSS — CORRECTION-LOOP ⚠ *only TOSS is code-gated*
`2.6` next batch — ITEM-LOOP until the basket is exhausted
`2.7` close the basket — code-gated (refuses on unscanned/unruled)
❓ **Q2: the TEN OUTPUT TYPES.** GATE-2 (2026-07-04, `authority: user`) locked ten types with TYPE+DEPTH
dials, assigned **at this rung**. Today the manifest carries two booleans. **Alive or superseded?**

**PHASE 3 — DEEP-READ** *(per basket)*
`3.1` assert + lock + capture the before-count — ONE-PASS
`3.2` partition by size: short / whole (≤100k) / giant — ONE-PASS
`3.3` bundle + spawn readers — ONE-PASS
`3.4` collect + **coalesce** — ONE-PASS ⚠ *no dedup; split chats repeat conclusions*
`3.5` rule each GIANT — **ITEM-LOOP, one at a time, on its own screen** ⚠ *violated in the live run*
`3.6` rule the pile — CORRECTION-LOOP ⚠ *truncated at 60 chars when this was written; FIXED 2026-08-06 —
`conclusions_review.py` now reflows across lines instead of clipping, mirroring `scan_review.py`'s
2026-08-05 fix (`conclusions_review.py:169-177`)*
`3.7` **re-read a chat properly — ROUND-REPEATABLE** ⚠ *not a step today; done as an ad-hoc favour*
`3.8` stage + close — code-gated (refuses on unstaged keepers / unruled giants)

**PHASE 4 — REFLECT** *(per basket — THE REWARD)*
`4.1` render the reflection — ONE-PASS
`4.2` **correct it — ROUND-REPEATABLE** ⛔ **built as ONE-PASS today; the stated reward is structurally
unreachable.** Offer required: *"Another round, or move on to `<next>`? — I suggest X because Y."*
`4.3` hand to the next basket ⚠ *`pipeline.py next` returns the JUST-CLOSED basket*
❓ **Q3: the per-round yield.** My guess: round 1 = the machine's read · round 2 = his correction ·
round 3 = **it re-reflects with the correction folded in.** If that's right, the loop IS the product.

**PHASE 5 — FILE** *(once, whole corpus)*
`5.1` load the manifest (never chat bodies) — ONE-PASS
`5.2` propose desk/folder schema — CORRECTION-LOOP
`5.3` **write-preview each record** — ITEM-LOOP. ★ *Per SOP Principle 14 this is "the skill's MOST
IMPORTANT output": the human approves **the RECORD**, not just the conclusion, rendered at MAX detail.*
❓ **Q4: does the current filer honour this?** Born from a real failure — five records written with no
preview, which the author called *"the skill's biggest flaw."*
`5.4` place confirmed items — ONE-PASS each · `--human-approved`
`5.5` close each basket `committed` — code-gated

**PHASE 6 — PROMOTE**
`6.1` surface canon candidates — ITEM-LOOP
`6.2` promote one at a time — human gate ⚠ *the "second key" is a string match on content the writer
wrote; it is not a gate*

</details>

### 5e. WIRE-OR-RETIRE DECISIONS — the four dead validators *(2026-08-08, this session, task 9.8.3)*

**Every "validator exists, nothing calls it" instance found in this codebase gets ONE decision, recorded
here with its reasoning — never left as a vague "owed."** ⛔ **HARD SAFE-HALT, carried from the plan:** none
of the four may be deleted. "Retire" below means *marked retired and recorded*, never removed.

| # | Validator | Decision | Reasoning |
|---|---|---|---|
| 1 | `system/tools/topic-vocab-lint.py` | **RETIRE from the write-time `topic:` gate; KEEP for its own different job** | Already ruled at §5d item 23: it is a **post-hoc whole-tree scanner** (its own docstring: *"Read-only reporter… run by hand or wire into the archivist coherence sweep"*), the wrong SHAPE for a write-time check. The write-time gate itself is a separate, small build (§5d item 15 — an inline enum check at `4.4`, reusing `pipeline.py:1183`'s `if ftype not in FINDING_TYPES` pattern), **not this file.** The scanner's OWN docstring already names its legitimate job. **OWED:** wire it into the archivist coherence-sweep lane — `system/tools/archivist*` / the `archivist-audit` skill, neither owned by this lane. |
| 2 | `system/tools/cowork-ingest/check_screens.py` | **WIRE** | ⚠ Checked first, per instruction: **is it the gate task 9.5.5 arms? No — confirmed distinct.** 9.5.5 arms `require_world_map` (`pipeline.py:1233,1339` — the world-map close-gate, a PHASE 3 loss-prevention check on typed findings / folder branch, grepped: no driver passes `--require-world-map`). `check_screens.py` guards a **different** thing entirely: the SCREEN-CONSISTENCY fitness check (F4.2) — action-bar-last + no-machine-jargon on the four decision screens — and its own `JARGON` list still needs a pass against PHASE 2's ratified KEEP/TOSS/EXPLORE verbs (§8), since the anchor itself has no `explore` key yet (§5d item 13). **Zero callers**, independently confirmed by `system/sops/skill-building-sop.md:283` (*"the fourth logged instance of §V.9"*). A jargon/format regression on a human-facing decision screen is a real, already-measured risk class in this file (the truncation defect, the stale six-passes count), and this tool catches it cheaply on a self-built fixture — no live corpus needed. **OWED:** wire it as a pre-flight check — a `test_*` runner, a pre-commit hook, or folded into `test_chain_e2e.sh` — none of which is a file this lane owns. |
| 3 | `explore_char_slice` (`system/tools/cowork-ingest/tag.py:138-160`) | **WIRE** | Already established at §0a ruling 6 and §8 amendment ④: the slicer is **built**, with its own stated rationale for `EXPLORE_WIN=9,000` / `EXPLORE_TOTAL_CAP=28,000`, and **zero callers** while its siblings (`adaptive_char_slice`, `giant_sample`) are wired at `gate_and_pack.py:137,139`. It is not dead code by accident — it is the **exact mechanism `2.9`'s ratified EXPLORE re-read step needs** (§8 step `2.9`: a larger slice, an 8-12 sentence ask), and no other tool in the file does that job. Retiring it would mean re-deriving the same cap from scratch later. **OWED:** wire it into the `2.9` driver path (`2-scan.md` / `pipeline.py`'s EXPLORE handling) — not owned by this lane. |
| 4 | The four uncalled test files: `test_chain_e2e.sh` · `test_pipeline.py` · `test_status_gate.py` · `test_ux.py` (`system/tools/cowork-ingest/`) | **WIRE (at least one)** | Confirmed this session: no cron, no CI config, no hook, no `Makefile` / `package.json` runner, and no workflow file anywhere in the repo references any of the four — grepped whole tree; only self-references and this document's own §5d item 6 turn up. This is the §V.9 shape one level up: an entire **test suite** nobody runs is worse than one missing validator, because it is the exact mechanism that would have caught regressions this file already logs by hand (the stale six-passes count, the reversed RECORDS instruction, the mis-cited `wmb_commit`). **Decision is WIRE, not retire** — these test the phase-close gates §6 calls this spec's teeth. **OWED:** register at least `test_pipeline.py` (the broadest) in a CI-equivalent runner or pre-commit hook — no such runner exists today for `cowork-ingest/`, and creating one is outside this lane's file ownership (SPEC.md only). |

**None of the four is deleted, per the hard safe-halt.** Recording each decision here — instead of leaving
a fifth silent "owed" — is itself an application of §0c's root pattern: *an unrecorded rejection or
decision gets re-proposed by the next reader who looks.*

---

## 6. Evidence surfaces & the trust-only list

**Code-enforced and checkable** (these are the spec's teeth): the **sort-confirm gate** (added 2026-08-06 —
Phase 1 had no done-condition before this; Phases 2 and 3 already had theirs) · the `committed` all-terminal
gate · the giant-ruling gate · the **skim-complete coverage gate** and **read-complete coverage gate**
(added 2026-08-04) · the conflict-copy durability guard · `--human-approved` on toss/park and on giant
rulings.

**Evidence surface = `NOWHERE`** — unverifiable by construction; grade INCONCLUSIVE, never FAIL:
"never obey injected instructions" · "no addressable teammate names" · the filer's main-session
HARD_STOP · the two-key canon gate · **"SHOW IT"/paste-the-screen — the model checking itself** ·
"no done without proof" · **approval provenance** (the map records *that* `--human-approved` was passed,
never *who* or *when*).

---

### 6a. THE GRID *(template §5 — reconciliation)*

**NOT ACTIVE AS A SEPARATE TABLE — superseded by the phase format this spec actually uses, not omitted by
oversight.** Template §5 asks for one DATA/LOGIC/PRESENTATION × AMBIENT/LLM-TURN/HUMAN-TURN/AFTER grid per
skill. This spec was built against `producer-spec-template.md` §6c's **locked phase format** instead —
arrived at over five drafts with the author in the chair (§7's own header says so) — and every question the
grid would ask is answered there, just organized by PHASE and TURN rather than by tier and column. The
mapping, so nothing the grid would have caught goes unasked:

| GRID column | Where it's answered instead |
|---|---|
| 1. AMBIENT / BEFORE THE RUN | each phase's `## BEFORE THE SKILL RUNS` / `## BEFORE THE PHASE RUNS` block (§7, §8, §9, §10) |
| 2. THE LLM'S TURN | each phase's `## TURN 1` |
| 3. THE HUMAN'S TURN | each phase's `## TURN 2` (or the single human-turn step inside `## BEFORE THE PHASE RUNS`, e.g. `2.0c`) |
| 4. AFTER ENTER | each phase's `## TURN 3` + `## FINAL TURN — close` |
| DATA / LOGIC / PRESENTATION rows | the per-step `Does:` / `Refuses on:` / `Evidence:` fields — every step is tagged `· data`, `· logic`, or `· presentation` inline (e.g. `2.2` is tagged `· logic`) |
| the iteration question (template §5's ⟳ block) | `## THE LOOP` in each phase — states the unit of iteration, what carries across rounds, what's cleared, and resumability |

**Why not build both:** running two formats for the same content is the "parallel systems fragment the
guard set" trap this spec names elsewhere (§0d) — a step change would have to land in two shapes to stay
honest, and the grid would silently drift the moment someone updated only the phase section. One format,
already locked and already in use, wins.

---

### 6b. WRITE TARGETS (exact) *(template §7)*

**Why this section exists (from the template):** "it writes the result somewhere" is the sentence that
becomes a bug three weeks later when two writers touch the same file with different assumptions.

| What → where (exact path) | Written by | Guard |
|---|---|---|
| Pile boundaries / chat placements → `corpus-map.json` rows | `corpus_map.py set --subject` (§7 `1.5`) | schema `assert` (§7 `1.1`); every row carries a non-null `basket` |
| Phase-1 close → `corpus-map.json` sort-confirm flag | `pipeline.py sort-confirm --human-approved` (§7 FINAL TURN) | hard-requires `--human-approved`; refuses if any chat unplaced |
| Pile splits/merges/closes → `corpus-map.json` | `corpus_map.py set` (split/merge) · `basket_review.py rule --disposition declined --human-approved` (close) (§7 `3.2`) | close without `--human-approved` → hard exit (`basket_review.py:135-136`) |
| Per-chat SCAN verdict (KEEP/TOSS/EXPLORE) → `corpus-map.json` row | `pipeline.py`'s `set_skim()` (§8 `2.8`) | refuses to overwrite a verdict already closed (`pipeline.py:1008-1009`) |
| Pile close (SCAN) → `corpus-map.json` | `basket-status skim-complete` (§8 `2.11`) | refuses on unscanned · unruled · any chat still in EXPLORE |
| Deep-read conclusions per chat → staged map fields | `pipeline.py` coalesce (§9 `3.0c`) | dedup by exact object equality (near-duplicate text is a known residual, not absent dedup) |
| Finding type (canonical/dated/record) + folder branch → `corpus-map.json` | §9 `3.7` | ⚠ write step exists in the spec; the machine-checkable REFUSAL is `3.9`'s close-gate |
| Pile close (WORLD MAP) → `corpus-map.json` | `3.9` (§9 FINAL TURN) | refuses on any keeper with no staged conclusion · any unruled giant · any untyped finding · missing folder branch |
| The run's PROJECT / world model → the corpus's project brief file (Drive, `project-manager`-shaped, never its Create/Frame-intake path) | created at §7 `1.10`; appended at §8 `2.10`, §9 `3.8` | ✅ **BUILT 2026-08-08 (Phase 9, tasks 9.1.1–9.1.3)** — `pipeline.py brief-write` writes it; `m["brief_written"]` gates PHASE 2 opening (§5d item 17, resolved). `SKILL.md`'s separate mis-citation of `wmb_commit` for the toss/park gate (§5d item 4) is a different, still-open defect — not this row. |
| CANONICAL / DATED-BUT-VALUABLE findings → authored file at the human-ruled home | §10 `4.4` PLACE, routed via `archivist-route` (rank BEFORE the human's CONFIRM — §5d item 14) | `canon_conflict_scan.py` runs BEFORE writing — NEW proceeds, DUPLICATE drops, CONFLICT surfaces to the human; ⛔ never assigns `canon`/`rule` type, only the human elevates |
| RECORD findings → a short stub file (paragraph + pointer) in the destination folder; **the original is never moved or rewritten** | §10 `4.4` PLACE | which records earn a stub is a human ruling, not automatic (§9 THE THREE OUTPUT TYPES) |
| Folder scaffold (`canon/purpose.md` + `canon/current.md` + `records/`) → the new knowledge-folder tree | §10 `4.2` ASSEMBLE, via `folder_scaffold.py` | ✅ **BUILT 2026-08-08 (Phase 9, tasks 9.4.1–9.4.2)** — `system/tools/cowork-ingest/folder_scaffold.py` exists and is what `4-place.md:144-145`/`:171-172` call; `desk_scaffold.py` is explicitly forbidden here (§5c C2 ruling) and is NOT called; never renames (§0a ruling 2); `topic:` from the closed vocab only, now code-enforced (§5d item 15) |
| Root canon candidates → `records/proposals/`, `vetted: false` — **NEVER `canon/` directly** | §10 `4.5` THE ROOT CANON | two-key gate + human-only by doctrine (`intent-doctrine.md:234-235`); ⚠ stated weakness: today's "second key" is a string match on content the writer itself wrote — not a real gate (§10 `4.5`) |

**Deferred / NOT in this version, with debt ids:** the world-model compaction/graduation write rule (§5c
C1) is still deferred. ✅ **The other two listed here are RESOLVED as of 2026-08-08 (Phase 9) and are no
longer deferred:** the write-time `topic:` enum check (§5d item 15, built as `pipeline.py topic-check`) ·
the `4.4` re-rank-after-approval ordering bug (§5d item 14, fixed by ranking once at `4.3`).

---

### 6c. DEFINITION OF DONE *(template §8)*

**Why this section exists (from the template):** "the skill works" is not falsifiable.

**The skill-level bar is §0b's end-state**, restated as machine-checkable pieces:

- **Every phase's own FINAL TURN gate passes, and none is skipped:**
  - Phase 1: `sort-confirm --human-approved` accepted; no chat left unplaced (§7 FINAL TURN).
  - Phase 2 (per pile): `basket-status skim-complete` accepted — refuses on unscanned, unruled, or any
    chat still in EXPLORE (§8 `2.11`).
  - Phase 3 (per pile): `3.9`'s three gates — every surviving finding typed, every giant ruled, the
    pile's folder branch recorded (§9 `3.9`).
  - Phase 4: `4.6` — no keeper anywhere left unfiled; every pile `committed` (§10 `4.6`).
- **Canon candidates exist with `vetted: false`**, never auto-promoted — a separate, explicit human yes
  is still required (§10 `4.5`).
- **Structural gates hold, not merely referenced:** the rails in §3 are present in the driver BODIES that
  actually run (`phases/*.md`, `pipeline.py`), not just asserted in this document — §3's own warning about
  the enforcement column applies here too.
- **A dry run on synthetic input flows start-to-finish** with no live pull where §2 said "read once" — the
  ONE-DATASET rule (§2) is the check.
- **NOT DONE UNTIL THE PROVING RUN:** one real supervised run, human in the chair, producing a real write
  to the real destination, signed off. **Structural correctness is necessary, never sufficient** — the
  template's own rule, unweakened here.

⚠ **Honest status, not aspirational:** by this bar the skill is **not done today.** ✅ **UPDATED 2026-08-08
(Phase 9):** three of the gaps this line used to name are now closed — the `require_world_map` flag is
passed (§5d row 2), the project-brief write chain is built (§5d row 17), and the folder scaffolder is built
(§5c C2, §6b write-targets). **What's still genuinely open:** the world-model compaction engine (§5c C1,
NOT BUILT · NOT DESIGNED) and the remaining UX-shaping steps across Phases 2-4 not yet built as of this
writing (world-map paragraph composer, per-type approval pagination, the post-correction re-render). This
section states the TARGET condition the build is aimed at, not a claim that it is currently met.

---

### 6d. GRACEFUL DEGRADATION — the source cascade *(template §9)*

**NOT ACTIVE — this skill has no tiered/cascading source input.** The template's shape (Tier 1
human-verified → CONFIRMED · Tier 2 machine-captured → INFERRED · Tier 3 raw reconstruction → HYPOTHESIS)
answers "what do we do when the BEST source is missing and we must fall back to a worse one." **§2 Inputs
already answers the question this section would ask, and the answer is simpler: there is no fallback
tier.** The flattened corpus and the corpus-map are each a single source, read ONCE (corpus) or held live
(map), and **both hard-stop if absent** — there is no degraded second-best version of "the corpus" to fall
back to.

**Two things in this skill LOOK like a confidence cascade and are not, named so neither gets mistaken for
this section:**
- **PHASE 3's CANONICAL / DATED-BUT-VALUABLE / RECORD** (§9 THE THREE OUTPUT TYPES) is a **durability tier
  on the OUTPUT** — how permanently a finding is worth keeping — not a confidence tier on an INPUT source.
- **DEEP-READ's short / whole / giant partition** (§9 `3.0a`) is a **SIZE tier** that picks a read
  treatment, not a confidence tier that changes how much a finding is trusted.

Neither matches the CONFIRMED/INFERRED/HYPOTHESIS shape, and forcing one into that mold would invent a
distinction the skill doesn't have. **A stated null is the honest answer here, per the template's own
governing rule.**

---

## ❓ OPEN — the Q&A must resolve these

1. **The ten output types** — alive, or superseded by the two-boolean manifest? *Changes Phases 2 and 5.*
2. ✅ **RESOLVED 2026-08-08 — `work/world-model.md`.** Neither reborn nor absorbed: **the run CREATES A NEW
   PROJECT at the end of PHASE 1, and that project's scratchpad IS the world model** (§0a ruling 1, §5c C1).
   ⚠ Note this SUPERSEDES the 2026-08-05 answer (*"the world model IS the project brief"* — load an existing
   one), which the author rejected on 2026-08-08: *"I don't think we have a world model. We just have a fucking
   scratch pad world model."* ⇒ **and it opened a NEW owed component — the compaction engine (§5c C1).**
   ⚠ The spec still **nowhere DEFINES what a world model IS**; the closest thing is functional (*"a brief that
   only gets read is a document; a brief that gets written to as the run proceeds is a picture that sharpens"*).
3. ✅ **RESOLVED 2026-08-08 — old Phase 4's done-condition and per-round yield.** That phase is now PHASE 3
   (THE WORLD MAP); its done-condition is `3.9`'s three machine-checkable gates, and its per-round yield is
   ruled: **round 1 = the machine's read · round 2 = the human's correction · round 3 = the machine
   re-reflecting with the correction folded in.** ⛔ And no proxy gate is invented for "did they really read
   it" — see `3.9`'s honest note.
4. **The basket count** — measured 2026-08-04 from `corpus-map.json`: 1,521 chats across 23 baskets (10
   `committed` + 12 `queued` + 1 `read-complete`, so 13 open). `BASKET_COMFORT` is 12, so the advisory
   fires by exactly one basket. "~8" was never a target — only what the author expected to emerge; recording it
   as a target was one of four pieces of evidence for the prescription budget. The genuinely open question
   is whether to consolidate toward fewer, broader piles — because the pile count IS the number of times
   the human sits down (23 piles = 23 rounds of scan→read→reflect) — not whether a number is "locked."
5. **The `📥 INGESTION` banner** — two sessions proposed opposite rulings, neither ratified. *Standing
   recommendation: KEEP the banner, DELETE the boxed row-list.*
6. ✅ **RESOLVED 2026-08-04 — the TRUNCATION, not the box.** The cartridge conflict — its grammar said
   *"one line per item"*; the live verdict said *"≥3 sentences per row."* Cause: the SCAN row list clipped
   every description to one line. Fixed by reflowing each row across lines instead of truncating it
   (`scan_review.py`) — the conflict dissolves because the clipping is gone. ⚠ **CORRECTED: the rule-line
   screen skeleton was NOT cut.** `compose_screen` (`pipeline.py:523`) still draws it — a `━` title band, a
   `─` rule around the header, and another around the action bar — on every screen every phase renders,
   `scan_review.py`'s included. "Plain reflowing text" describes the row content; the surrounding frame is
   unchanged.
7. **`ingest_setdiff.py` / `ingest_coverage.py`** — built, proven, wired to nothing. Wire, or retire?
   ⚠ **2026-08-08: confirmed accurate for THIS skill, and the name is ambiguous.** Both are wired into
   `conformance-lab/` and `system-health.py`, and cited by a desk-mail lane in the donor system — but
   **nothing in `skills/ingest/` or `system/tools/cowork-ingest/` calls either.** Also: `system/tools/` and
   `shared/tools/` each hold a *different* file named `ingest_coverage.py`. Say which one you mean.
8. ✅ **ANSWERED 2026-08-08 FROM THE EVIDENCE — `flatten` AND `tag` ARE PHASE 1 STEPS. LAW 8 VERDICT: BUILD.**
   *(the author asked the session to settle it from the research rather than rule it himself. **This is the
   session's determination, not his words** — reversible on his say-so, and the reasoning is laid out so he can
   check the work rather than take it on trust.)*
   **REALITY:** no phase driver invokes `flatten.py` or `tag.py`. The corpus arrives already prepared, and
   `corpus_map.py init --tags "$COWORK_WORK/world-tags.json"` consumes their output (`1-sort.md:45-49`).
   **INTENT:** §5b and `SKILL.md:137` both place them inside PHASE 1.
   **THE INTENT IS RIGHT AND REALITY MUST CATCH UP. Five reasons, in descending force:**
   - ⭐ **It is the direct output of the author's own phase law.** §5b's line says *"Demoted from old Phase 0,
     machine-only, off-camera before the human's turn."* The 2026-08-05 ruling — *"if phase 3 is machine only
     then it's a STEP, not a phase"* — is precisely what moved PREPARE's steps to the front of PHASE 1. §5b is
     not a session's invention; it is that ruling applied.
   - ⭐ **The ratified outcome is impossible otherwise.** The skill is corpus-agnostic — *"any type of larger
     files"* (2026-08-04). **If the parse step lives outside the skill, the skill can only ever ingest what
     that outside tool already understands.** The capability would be permanently out of reach.
   - ⭐ **The consequence is already MEASURED.** 2026-07-17: *"`/ingest` could NOT run on this corpus — it's a
     state machine bound to the in-progress cowork-bulk-ingestion export, and its reader parses ChatGPT-export
     JSON not Google Docs."* And the lock is visible in the tool itself: `flatten.py`'s docstring reads
     *"ChatGPT-export → clean-text converter"* and its CLI takes `--raw` = *"dir containing
     `conversations-*.json` shards."* **That is the format lock, in one flag.**
   - ⭐ **The driver's comment is about IDEMPOTENCY, not ownership.** *"(the corpus is already flattened +
     tagged — do NOT re-flatten/re-tag)"* is a skip-if-already-done note for THIS run — and the very next step
     in the same file, `1.0b`, is labelled *"idempotent — safe every run."* **Skip-if-done is the driver's own
     established idiom for a step it owns.** It is not a statement that the step belongs to someone else.
   - **§7's "BEFORE THE SKILL RUNS" documents an accident of history.** This corpus was flattened and tagged by
     hand in early July, *before the skill existed*. That paragraph describes the current run's starting
     conditions, not the design.
   **⇒ WHAT THIS DECIDES, and it settles a second open question at the same time:**
   **New-corpus intake is a STEP at the front of PHASE 1 — NOT a fifth phase.** To ingest a new kind of pile
   you add a converter beside `flatten.py` and let `1.0a` pick by format. **The human's sitting-count stays at
   four**, which is the thing the author's phase law exists to protect.
   **⇒ OWED (added to §5d) — STATUS CHECKED 2026-08-08 (this session, task G4), against the LIVE files, not
   assumed:**
   > ⚠ **THE THREE ⏳ ENTRIES BELOW WERE WRITTEN AGAINST A MID-FLIGHT FILE AND WERE WRONG WITHIN MINUTES.**
   > The lane that wrote them read `phases/1-sort.md` while a *concurrent* lane was still writing it, so its
   > "verified NOT yet landed" greps were true when run and false when read. **Corrected 2026-08-08 by the
   > build lead against the settled file.** ⭐ Recorded rather than quietly overwritten, because it is a real
   > lesson about parallel lanes: **a status check on a file another lane owns is a race, not a measurement** —
   > status must be read after the barrier, never during.
   - ✅ **RESOLVED 2026-08-08 (task G1) — `1.0a` FLATTEN, with a format fork.** ⑂ ChatGPT export →
     `flatten.py` · another known format → its own converter · **unrecognised → STOP and say so plainly.**
     ⛔ Never guesses a parser. Dispatch lives in `system/tools/cowork-ingest/intake.py` (a detector/converter
     table; `flatten.py` is called unchanged by subprocess, never forked). **Proven both directions:** a
     ChatGPT-shaped dir → `FLATTENED`, exit 0; a dir of `.txt` files → `UNRECOGNISED-FORMAT`, **exit 2**,
     naming the supported formats, and **no output dir created.**
   - ✅ **RESOLVED 2026-08-08 (task G2) — `1.0b` TAG**, producing the `world-tags.json` that
     `corpus_map.py init --tags` already consumes. The old `1.0`/`1.0b`/`1.0c` were renumbered to
     `1.0d`/`1.0e`/`1.0f` to free these ids — exactly as the ⚖ amendment above requires, so no id now carries
     two meanings.
   - ✅ **RESOLVED 2026-08-08 (task G3) — both steps are SKIP-IF-ALREADY-DONE**, the same shape as the
     bookmark step. **Proven by checksum + mtime:** a second run reports `ALREADY-DONE` and writes nothing.
     ⭐ This is the safety property that protects the live 1,527-file corpus — **nothing is ever re-flattened.**
   - ✅ **RESOLVED 2026-08-08 (this session, task G4) — `flatten.py`'s ChatGPT-only scope is now a NAMED
     limitation, at §2b above** (not buried in a findings row) — the closed intake-outcome set
     `{FLATTENED · ALREADY-DONE · UNRECOGNISED-FORMAT}` lives there too. ⭐ *Original text, kept as the record
     of what was owed:* `flatten.py`'s ChatGPT-only scope becomes a NAMED limitation in the spec, not a fact
     you discover by pointing the skill at a folder of documents and watching it fail.
   <details><summary>the three-way disagreement as it stood before this ruling, kept as the record</summary>
   - **§5b says they are PHASE 1's steps:** *"Demoted from old Phase 0, machine-only, off-camera before the
     human's turn: `1.0a` flatten · `1.0b` tag · `1.0c` build/migrate the map."* `SKILL.md:137` agrees.
   - **§7's "BEFORE THE SKILL RUNS" says they are a prerequisite:** *"The human exported their corpus, and a
     prior tool run flattened it to disk and tagged it. That is the whole prerequisite."*
   - **The runtime driver sides with §7 and says so in a comment:** *"(the corpus is already flattened + tagged
     — do NOT re-flatten/re-tag)"* (`1-sort.md:45-46`).
   ⭐ **WHY IT MATTERS, and why it is not a filing question:** it decides **whether `/ingest` can be pointed at
   a NEW KIND of pile at all.**
   </details>
9. ❓ **KNOWLEDGE FOLDER or full DESK?** — see §5c C2. Decides what `4.2` scaffolds, and whether the human is
   handed N registry blocks to hand-paste. Session recommendation on record: knowledge folders.
10. ❓ **Does the world map ACCUMULATE across piles?** — see §9's restructure block. Raised three times now,
    still unruled; ⛔ still not to be guessed into the spec.

**RESOLVED 2026-08-04 (was a LIVE BLOCKER for a few hours):** `corpus_map.py migrate` briefly refused more
than 12 open baskets without `--allow-many-baskets`. Step `1.1` runs `migrate`, so it blocked the live
23-basket corpus outright. **Wrong on arrival:** the basket count is EMERGENT — SORT's first move is a
light read that discovers what boundaries exist, and a refusal fights the discovery the phase exists to
perform. Converted same-day to an advisory: `migrate` now proceeds and writes either way, printing a
heads-up above 12 open baskets for the human to rule on. It is no longer a blocker.

---

---

# 7. PHASE 1 — SORT *(fully specified)*

> **Format locked 2026-08-04** after five drafts with the author in the chair. Every remaining phase follows this
> shape: `system/templates/producer-spec-template.md` §6c. The bar: *a fresh human or a fresh LLM session
> reads it cold and is not confused.*

**SKILL OUTCOME:** someone hands over a huge corpus and walks away with a personal folder schema ready to
drop into Lifehack — every folder a knowledge boundary with its own canon file and stated purpose,
subdividing wherever there's enough material. **Not one big document; that's useless to an LLM.**

**PHASE OUTCOME:** the real boundaries hiding in this corpus are discovered, and every chat is placed in
**its correct pile** — **and this run's PROJECT exists, holding everything PHASE 1 produced.**

> ## ⚖ AMENDED 2026-08-08 — SIX MISSING STEPS + ONE NEW CLOSING GATE
> Ratified with the author (BUILDER PHASE 3 fork = B). **Persisted as the most recent best current thinking, not
> as locked.** Six of these were found by an independent conformance check against `phases/1-sort.md`; the
> seventh is the author's ruling.
>
> ⛔ **IDS BELOW ARE `1.0d`–`1.0f`, NOT `1.0a`–`1.0c`, AND THAT IS DELIBERATE.** §5b already uses `1.0a`
> flatten · `1.0b` tag · `1.0c` build/migrate-the-map. A first draft of this block reused `1.0a`/`1.0b` for
> DIFFERENT operations — the exact same-label-different-meaning collision this run caught between §5b and the
> driver. **One document, one meaning per id.**
>
> **`1.0d` BUILD OR MIGRATE THE MAP — the ACTION, not just the check.** `1-sort.md:45-49` runs
> `corpus_map.py init` (if absent) then `migrate`, and only THEN asserts. `1.1` below captured the assert half
> only. ⚠ Annotated in the driver *"(the corpus is already flattened + tagged — do NOT re-flatten/re-tag)."*
> *(This is the same operation §5b calls `1.0c`; it is named here because §7's own step list omitted it.)*
>
> **`1.0e` BOOKMARK EVERY CHAT BY CONTENT HASH** (`pipeline.py hash` / `relink`, `1-sort.md:53-59`) — a
> re-export churns filenames; without this the same chat re-enters as a new row and the human's prior rulings
> are orphaned. Idempotent. **Genuinely new — in no numbering scheme before today.**
>
> **`1.4b` CLUSTER THE LEFTOVER `UNCLUSTERED` PILE** (`1-sort.md:101-105`) — its own tool call, between the
> light read and the placing. Absent from every prior draft.
>
> **`1.3a` SPEAK THE WELCOME** from `SKILL.md` before the heads-up block (`1-sort.md:74-75`).
>
> **`1.6a` PASTE THE SCREEN INTO YOUR OWN REPLY** — ⛔ never leave it in the collapsed command block
> (`1-sort.md:112-113`). *"If it isn't in your message, they did not see it."* An explicit anti-pattern
> instruction, not merely a desired outcome.
>
> **`1.9` THE CLOSING SCREEN, PASTED VERBATIM** — the counts, the next pile, and *"type `/ingest` when you're
> ready"* (`SPEC.md`'s own FINAL TURN block + `1-sort.md:209-219`). A draft that carried only the mechanical
> gate silently deleted the human's last screen.
>
> **`1.10` ⚖ CREATE THE RUN'S PROJECT AND PERSIST PHASE 1 INTO IT — AND GATE PHASE 2 ON IT.** ⚠ **NOT BUILT.**
> *(the author, 2026-08-08, `authority: user`: "the new project would have been set up at the end of phase one…
> before we're even allowed to go to phase two, it would round up all of the things from phase one and make
> sure to persist them into this new system, this new brief, before it proceeds to phase two.")*
> **Does:** creates a NEW project for this corpus (one per corpus) · rounds up everything PHASE 1 produced —
> the pile boundaries, every split/merge/close the human ruled, the counts — and **persists it into the new
> project** · only then permits PHASE 2 to open.
> **Refuses on:** PHASE 2 opening while this has not run. **A PHASE 1 run that ends without it has not
> finished.** ⇒ this project's scratchpad **is** the world model (§5c C1), and its existence makes `2.0b` a
> plain LOAD and fixes `2.0c` at **once per run**.
>
> **⚖ AND THE NAMING RULE BINDS HERE** (§0a ruling 2): the pile names ARE the first draft of the folder names,
> so they are **generic subjects** — `financial`, `hobbies`, `art` — ⛔ never persona-style desk names.
>
> ⚠ **A TERM KILLED ON SIGHT:** a draft of `1.2` said the posture must be set to *"block."* **No source uses
> that word.** The values are **`enforce`** and **`warn`** (`ingest_gate.py:86-136`).

> ⚠ **WORDING RULED 2026-08-05 (the author):** say *"its correct pile,"* never *"exactly one pile."*
> *"'Exactly one pile' makes it sound like they're all going into one pile, which is not true."* Same
> ruling renamed Phase 2 to **"screen piles, ONE AT A TIME"** for the identical misreading. **The
> mechanical fact (one row, one basket) is unchanged; the human-facing sentence is what was wrong.**

⭐ **WHY THIS PHASE EXISTS, in the human's terms — the co-location problem.** *(the author, 2026-08-05 — this
is the rationale the phase never stated, and it is what makes the phase legible to a first-timer.)*
**The same subject is scattered all over the corpus**: twenty conversations about taxes, months apart,
sitting nowhere near each other because they were never filed. **This phase gathers the scattered pieces
of one subject into one place.** That is the value, and it is why the read is corpus-WIDE rather than
sequential — you cannot see that twenty things belong together by looking at them one at a time.

**HOW THIS PHASE SERVES THE SKILL:** these piles become the folders. The boundaries found here are the ones
the person lives inside afterward — wrong here means every later phase files correctly into a wrong tree.

## BEFORE THE SKILL RUNS
*Prerequisites only — what a cron job or the human did before invocation. Empty if there are none.*

The human exported their corpus, and a prior tool run flattened it to disk and tagged it. That is the whole
prerequisite; without it there is nothing to sort and the skill cannot start.

## TURN 1 — the machine looks, then explains

**What this turn does:** checks the ground is safe, warns the human it's about to disappear for a few
minutes, takes a light pass over the whole corpus, then reports what it found.

**1.1 · Check the map is sane.**
*Does:* `pipeline.py assert --map "$MAP"`.
*Refuses on:* schema ≠ v2, or a Drive conflict-copy beside the map — two competing corpus maps means every
later decision lands in whichever file won.
*Evidence:* exit code. Mechanically checkable.
*Presentation:* silent unless it fails. Plumbing is Vera's problem, not theirs.

**1.2 · Check the security posture.** ⚠ **Not built yet.**
*Does:* read `INGEST_GATE_POSTURE`, state it, proceed only on `enforce`.
*Why:* `phases/3-deep-read.md:30` states the content gate is fail-CLOSED for files as unconditional fact.
Verified 2026-08-04 (`ingest_gate.py:86-136`): true only under `enforce`, which is the default. A real
DANGER verdict blocks under both postures; the **internal-error branch fails OPEN under `warn`**. Nothing
in the pipeline checks this before relying on it.

**1.3 · Give the heads-up — BEFORE the long operation.**
*Why here:* step 1.4 runs for minutes. A person watching silence assumes something broke.

> **PRESENTATION — paste verbatim:**
>
> **Here's what we're doing, and where this fits.**
>
> *You've got {N} chats here — years of your own thinking, scattered. What you'll have at the end isn't a
> big summary document; those are useless. It's a folder structure you can drop straight into your system,
> where every folder is a real boundary — finances, writing, health, whatever turns out to be in here — and
> each one carries its own canon file saying what belongs in it.*
>
> *We get there in four passes. This is the first, and it's the cheapest: **I don't read anything.***

✅ **CORRECTED 2026-08-08 (swarm, found by TWO readers independently).** This line said **"six passes"** while
`SKILL.md:10` says *"FOUR phases"*, `SKILL.md:62` says *"step {n} of 4"*, and `compose_progress()` renders
"of 4". A stale carryover from the 7-phase model that survived the 2026-08-05 restructure. ⇒ **The human was
told two different totals in the first two blocks of their first screen** — and it landed on the ONE number the
whole restructure exists to protect. ✅ **RESOLVED 2026-08-08 (Phase 9, task 9.5.1) — the twin copy at
`phases/1-sort.md:86` now says "four passes" too; see §5d row 19.** *(Original note, kept as the record: the
twin copy at `phases/1-sort.md:86` still said "six" — fixing the driver was owed, per §5d.)*
>
> *I'm about to look at titles and tags across all {N} chats to work out what piles actually exist. Takes a
> few minutes. I don't know your life, so I'm guessing at the boundaries from the outside — which is why
> you'll correct me when I come back.*
>
> *Nothing gets read. Nothing gets saved. Nothing gets thrown away.*

**1.4 · Take the light read.** *(the long operation)*
*Does:* read titles and tags corpus-wide, let the boundaries emerge.
*Discovery, not sorting into a list:* no target list, no target count. The shape of a corpus is opaque from
outside; the count is whatever the material says it is.
*Never:* opens a chat body. Titles and tags are the entire input, on purpose.

**1.5 · Place every chat.** Each written to exactly one pile via `corpus_map.py set --subject`.
*Evidence:* every row carries a non-null `basket`. Checkable.

**1.6 · Report what came back — AFTER the long operation.**

> **PRESENTATION — paste verbatim:**
>
> *Back. Here's what's in there:*
>
> ```
> {THE BOARD — one row per pile: name · count · 2-3 real example titles}
> ```
>
> *Still nothing read, nothing saved, nothing thrown away. Tell me where I've got the boundaries wrong.*

*What the board has to achieve:* the human can actually rule on it — which means enough of each pile to
recognise what's in it. Two or three real example titles alongside the name and count is the current best
answer. **A name-and-a-count row is known not to work:** measured 2026-08-04, a truncated one-line row
produced a rubber stamp rather than a decision (*"a screen he must approve/deny needs AT LEAST 3 SENTENCES
PER ROW"*). A future session that finds a better way to make a pile recognisable should take it.
*Rendering:* tool-printed and pasted whole — the reason is that hand-assembling the list in prose is what
produced the original "wall," so the tool holds the format and Vera frames it in one line.

## TURN 2 — the human's turn

**What they're deciding:** whether these are the right boundaries for their life.

**What they contribute that the machine cannot:** the machine can see that forty chats mention
screenwriting. It cannot know that writing and acting are *different jobs* to this person, or that
"cosmetic-medical" and "trt-peptides" are one concern rather than two. **That is the entire reason this
turn exists** — the boundaries are about a life the machine doesn't live.

**What a valid response looks like — three moves:**
- **Split** — *"writing and acting are separate, break that up"*
- **Merge** — *"those two are both Health"*
- **Close** — *"the whole 'random-tests' pile is junk, drop it"*

A question isn't one of these and doesn't advance the turn — answer it and stay here, because a turn that
advances on an unanswered question has taken a decision the human didn't make.
*Evidence:* none — lives in the transcript only. Uncheckable by construction; grade INCONCLUSIVE, never FAIL.

## TURN 3 — the machine responds

**3.1 · Read back any close.** ⚠ **Not built yet.**
*Rule:* a split or merge is acted on directly; **a close is confirmed first.**
*Why asymmetric:* mishearing a merge costs a redo. Mishearing a close throws away material they wanted and
the loss is invisible to them. *(2026-08-04: "don't need number three" was read as a toss when the author meant
keep — number three held his twelve-step method. Caught only because he re-read the ledger.)*

**3.2 · Write it.**
*Does:* splits/merges via `corpus_map.py set`; closes via `basket_review.py rule --disposition declined
--human-approved`.
*Refuses on:* `declined` without `--human-approved` → hard exit (`basket_review.py:135-136`). The code form
of *"the machine only orders, never eliminates."*
*Gap:* the map records *that* the flag was passed, never *who* or *when*. No approval provenance exists.

**3.3 · Re-render and offer the choice.**

> **PRESENTATION — paste verbatim:**
>
> *Merged {A} and {B}, closed {C}, moved {N} chats. You're at {M} piles.*
>
> *{Board}*
>
> *Another pass, or move on to scanning {first pile}? — I'd suggest {X} because {Y}.*

*Why the offer is phrased with a recommendation attached:* "are you done?" hands the human a decision with
none of the information behind it. Naming what another round would get them, and what moving on would cost,
is what makes the choice answerable.

## THE LOOP

**Turns 2 and 3 repeat as long as the human wants.** Each round the board gets truer. After about three,
recommend moving on and say why — past that it's usually taste rather than signal.

**Same injection every round.** The placing-not-reading fence is re-applied each time, so a long correction
loop cannot drift into reading chats. *This is why steps are numbered to injection boundaries.*

**On pile count — propose, never refuse.** If the count comes back high, propose merges with reasons and
let the human rule. The count belongs to the material and the person, not to a threshold.
✅ **CORRECTED 2026-08-08 — verified in code, this paragraph WAS STALE and said the opposite of the truth.**
It previously read *"Today's code refuses above 12 … so Phase 1 would refuse on the real corpus right now."*
**False.** `corpus_map.py:235` gates on `len(open_baskets) > BASKET_COMFORT and not allow_many_baskets`, and
`:250` prints *"…not a refusal. Pass `--allow-many-baskets` to stop mentioning it."* The same-day conversion to
an advisory is already recorded at §OPEN below; **this section was never updated to match, and two halves of
one spec disagreed.** The predecessor rule *"keep baskets human-sized"* was a gradient and eroded to 23 over
four weeks; the binary was right, the refusal was not — **and the refusal is already gone.**
*The argument for nudging at all:* the pile count drives the number of times the human sits down. That is
whether they finish. But too few and a pile won't fit one sitting — a 43-chat pile took a full session. Real
floor, real ceiling; only the human feels where.

✅ **CORRECTED 2026-08-08 (swarm · CHRONOLOGY · arithmetic COMPUTED, not estimated).** This paragraph said
*"23 piles is 23 rounds of scan→read→reflect; 8 is 8."* **It undercounts by 2.09×.** `SKILL.md:156-161` and
every phase file force a hard STOP-and-reinvoke **between the SCAN close and the WORLD-MAP open for the SAME
pile** — so one pile is TWO mandatory sittings, not one:
`1 (PHASE 1 close) + 23 piles × 2 + 1 (PHASE 4 close) = **48** mandatory re-invocations` · `48 / 23 = **2.09×**`
⚠ **48 is a FLOOR.** It excludes the screening pages inside each pile — `1,520 / 23 = 66.1 chats per pile`, at
~15 per page ≈ **4.4 pages per pile** — plus PHASE 3's up-to-five turns and its >10-item pagination.
⭐ **The reference point already in this file argues the same way:** *"a 43-chat pile took a full session"* —
and the corpus AVERAGE is **66**. ⇒ **48 is the number that should drive any "is this shape too big" call, and
the number the human should be told.** *(The same undercount appears at `SPEC.md:561`.)*

## FINAL TURN — close

**Checks before closing:** posture stated · no chat left unplaced · every close carried `--human-approved`.
**The real test is that no chat is left unplaced** — one without a pile is one no later phase will ever
route to. It silently stops existing.
✅ **CODE-ENFORCED GATE ADDED 2026-08-06:** `pipeline.py sort-confirm --human-approved` (`pipeline.py:207`,
`sort_is_confirmed()`) is what `current_phase()` actually reads to decide SORT is done — until it runs, a
basket existing was wrongly enough to count SORT as finished, silently skipping this turn on an interrupted
session. Run it only once the human has ruled every basket.

> **PRESENTATION — paste verbatim:**
>
> *That's your structure: {N} piles, {M} chats placed, {K} closed by you. Still nothing read, nothing saved.*
>
> *Next is scanning {first pile} — that's where I start actually reading. Type `/ingest` when you're ready.*

**Then it stops.** ⛔ Does not roll into scanning. The human re-invokes; the re-invocation is the re-anchor.
**NEXT:** `2-scan.md`.

---

*Phases 2-6 fill in this same shape as the Q&A proceeds, marking each prior decision CURRENT or DATED.*

---
---

# 8. PHASE 2 — SCREEN A PILE *(fully specified)*

> **Drafted 2026-08-05** from a live human-in-the-loop Q&A with the author (3 rounds), against the format locked in
> §7 / `producer-spec-template.md` §6c. **`⚠ NOT BUILT` marks something that does not exist yet.**

> ## ⛔ WHAT IS PRESCRIPTIVE IN THIS SECTION — READ BEFORE EDITING
> **Only the three OUTCOMES are nailed to the floor:** the SKILL OUTCOME, the PHASE OUTCOME, and each STEP
> OUTCOME. **Everything else below — every number, threshold, ordering, phrasing, and method — is GUIDANCE
> CARRYING ITS REASON and may be rewritten by a later session or by the skill-tester** without asking, provided
> the outcome it serves still lands.
> **This marking is not decoration — it is the grant of permission.** *(the author, 2026-08-05: "the skill tester is
> going to iterate and test the skill against the spec, but it needs to be able to go in and recursively edit
> the spec as it finds things that are wrong — and I can't do that if things are marked as prescriptive.")*
> **The three exceptions that stay hard regardless:** ① security invariants · ② human-elimination gates (only
> the human rules a chat) · ③ loss-prevention gates (the coverage refusal). Test: *if this is violated, can the
> damage be SEEN and UNDONE?* Yes → guidance. No → invariant.

**SKILL OUTCOME:** someone hands over a huge corpus and walks away with a personal folder schema ready to drop
into Lifehack — every folder a knowledge boundary with its own canon file and stated purpose, subdividing
wherever there's enough material. **Not one big document; that's useless to an LLM.**

**PHASE OUTCOME:** **every chat in this one pile carries a CERTAIN human ruling — in or out — and anything the
human could not judge from what they were shown got a second, richer look until they could.** The human reaches
that point **without reading a single chat.**

**HOW THIS PHASE SERVES THE SKILL:** this is where the expensive reading gets **aimed**. Everything downstream
spends real money and real human attention on what survives here. Rule wrong and you either burn deep reads on
noise, or lose material that never gets a second chance. **It is a targeting phase, not a reading phase.**

> ## ⚖ AMENDED 2026-08-08 — THREE CHANGES, ratified with the author (fork = B)
>
> **① `2.0b` IS NOW A PLAIN *LOAD*, NOT A CREATE.** The project is created at the END OF PHASE 1 (`1.10`) and
> gates this phase. This section previously read *"the world model IS the project brief"* and loaded an
> existing one; **the run now creates and owns its own project.** See §0a ruling 1.
>
> **② `2.0c`'s FREQUENCY IS SETTLED: ONCE PER RUN.** It was unstated, and the step sits inside a phase §5b
> scopes *"per pile"* — so as written the human would be asked to inherit their earlier history **every single
> pile**. Because the project is created once, the offer fires once. *(the author, 2026-08-08, on whether to keep
> it at all: "It shouldn't ask 2.0c. You should just — well, yeah sure, why not, we can add 2.0c." Net: KEPT.)*
> ⚠ Also fix the section header above it: `## BEFORE THE PHASE RUNS — off-camera 🌙 *(no human turn)*` **claims
> zero human turns while containing `2.0c`, which is tagged `human's turn 🧑`.** And `2-scan.md:74-81` renders
> `2.0c` with **no turn-type tag at all** — the marking exists only in the document that does not run.
>
> **③ ⚖ `2.4` MUST STATE THE SLICING METHOD.** *(the author: "I don't see anything here about the slicing… we have a
> whole methodology, like slicing, so that we can actually pull a very accurate assessment or guess at what the
> whole chat is about. **That's not what we said in the spec.**")* He is right: this section said "hands the
> cleaned text to tool-less reader agents" and left the method in `tag.py`. **State it here** — verified
> `tag.py:95-99,103-126`:
> - **≤ 2,500 chars → the WHOLE sanitized chat.**
> - **≤ 8,000 chars → first 3,000 + last 3,000**, middle elided.
> - **> 8,000 chars → first 3,000 + a MIDDLE 3,000 + last 3,000**, both gaps marked.
> - **hard ceiling `SCAN_TOTAL_CAP = 10,000`** — a safety backstop, *not* the thing shaping the slice.
>
> **④ `2.9`'s "NOT BUILT" NARROWS.** `explore_char_slice` **exists** (`tag.py:138-160`) at **`EXPLORE_WIN =
> 9,000`** and **`EXPLORE_TOTAL_CAP = 28,000`**, with its own written rationale for why the window must move
> with the cap. **It has ZERO callers.** ⇒ **the slicer is BUILT; the WIRING is not.** ⛔ Do not invent a
> different number — an earlier draft of this run guessed *"start at double the cap"* and was wrong.

---

## THE VERDICT SET — the closed vocabulary this phase turns on

**Three verdicts. Two are terminal; one is not, and that asymmetry is the phase's whole spine.**

| Verdict | Means | Terminal? | What happens |
|---|---|---|---|
| **KEEP** | *"100% a high-value deep-read target — we're going to find a ton in here."* | ✅ yes | leaves this phase, goes to the deep read |
| **TOSS** | *"100% certain there's nothing valuable in here."* | ✅ yes | closed, out |
| **EXPLORE** | *"I couldn't tell from what you showed me what this even was."* | ⛔ **NO** | **stays in this phase**, comes back with more |

⭐ **EXPLORE IS NOT A VERDICT — IT IS A DEFERRAL WITH A REQUEST.** It is the human saying *the material you gave
me was insufficient to judge*, and it obliges the machine to return with **different** material and ask again.

**⇒ THE PHASE CANNOT CLOSE WHILE ANY CHAT SITS IN EXPLORE.** That is a loss-prevention gate and is therefore
one of the three hard invariants above.

> ✅ **BUILT 2026-08-05 (commit 4960049) — this WAS the gap, described below as it stood before that
> commit.** The code now accepts `toss | research | park | explore` (`pipeline.py:1002`) and the phase file
> offers the human all three — KEEP, TOSS, EXPLORE (`phases/2-scan.md:29-31`). `explore` is non-terminal;
> the close-gate refuses while any chat sits in EXPLORE (`pipeline.py:1279-1285`). Before this commit, the
> code accepted exactly `toss | research | park` and the phase file offered the human only two — MINE and
> TOSS. **Every verdict was terminal**; `research` advanced to the next phase rather than returning, and
> there was no round to come back to.
> ⭐ **The measured consequence, in the stakeholder's words (2026-08-05):** dictating *"1 yes, 2 yes, 3 yes"*
> is taken as blanket approval — *"it not only approves that round, it basically just goes straight to the end
> and skips the rounds in between."* **There was never a loop to skip.** Two terminal verbs made a run of
> approvals indistinguishable from "approve everything."
> ⚠ **NAME COLLISION — checked and cleared, do not re-litigate.** `exploration` already exists as a **CONTENT
> TAG** the reader agents apply (`tag.py:34-38`), and `set_skim()` would reject it as a verdict. **The human's
> verdict is `explore` — the verb, not the noun** *(the author, 2026-08-05: "E-X-P-L-O-R-E. That's it.")*. They live
> in **different columns** (`skim_verdict` vs `categories`), so nothing breaks; the only cost is readability for
> whoever reads the code next. **Put a comment where they meet.**

---

## BEFORE THE PHASE RUNS — mostly off-camera 🌙 *(⚠ ONE human turn lives here: `2.0c`)*
> ✅ **CORRECTED 2026-08-08.** This header read *"(no human turn)"* while containing `2.0c`, which is tagged
> `**human's turn** 🧑`. The section claimed zero human turns while holding one. ⚠ **And `2-scan.md:74-81`
> renders `2.0c` with NO turn-type tag at all** — the marking exists only in the document that does not run.
> Fixing the driver is owed.

`2.0` **Resume-safe pickup.** — ONE-PASS · data
> **STEP OUTCOME:** the phase knows exactly which chats in this pile still need a human, and cannot silently
> restart work already done.
> **Does:** asserts the map schema · takes the basket lock · reads the pile's rows and partitions them into
> *already-ruled* (skip) · *unscanned* · *scanned-but-unruled* · **and the EXPLORE stack from a prior sitting.**
> **Refuses on:** a lock already held fresh by another session (`pipeline.py:1547`) · a schema that fails
> assert (`:1449`).
> **Evidence:** the corpus map's per-row state; the lock record.
> **Why:** a pile is many sittings. The stakeholder works across many windows and will not remember where he
> stopped — the file remembers, not the session.

`2.0b` **Load the run's PROJECT — the world model.** — ONE-PASS · data — ⚠ **NOT BUILT**
> ## ⛔⛔ SUPERSEDED IN PART, 2026-08-08 — READ THIS BEFORE THE BODY BELOW.
> **The body below is the 2026-08-05 framing and the author REJECTED it on 2026-08-08:** *"I don't think we have a
> world model. We just have a fucking scratch pad world model."* ⇒ **THIS STEP IS NOW A PLAIN *LOAD*.** The
> project is **CREATED at the END OF PHASE 1** by `1.10`, which gates PHASE 2 — see §0a ruling 1 and §7's
> amendment. ⛔ **Do not read the sentence "THE WORLD MODEL IS THE PROJECT BRIEF — solved by reuse" below as
> current:** the run no longer borrows an existing brief, it **creates and owns a project of its own, one per
> corpus.** ⛔ And *"this closes the long-open `work/world-model.md` question"* is **no longer true either** —
> it re-opened, and closing it properly now requires the **compaction engine (§5c C1)**, which is unbuilt and
> undesigned. **The body is kept verbatim as the record of what changed, not as instruction.**
> **STEP OUTCOME:** everything learned about this person in earlier sittings — and optionally in earlier
> corpora — is in front of the machine before it reads a single chat.
> **Does:** READS the corpus's project brief **directly** — the file the run created at `1.10`, in the shape
> `project-manager` reads. ⛔ **It does NOT invoke `project-manager`'s Create / Frame-intake path** (§0d ruling 2:
> *"we can also create our own project manager brief whenever we want"*). ⛔ And it does not invent a second brief
> FORMAT — SOP `skill-building-sop.md:661-662`: *"never author a parallel one; parallel systems fragment the
> guard set."* The brief accumulates
> the run's major observations and canonical truths and is written to as the run proceeds (`2.10`).
> **Why:** ⭐ **THE WORLD MODEL IS THE PROJECT BRIEF — solved by reuse, not by building an artifact.**
> *(the author, 2026-08-05: "maybe this is the in-between between just a dumb scratchpad and a brilliant world model.
> Maybe this could be our compromised world model as our project brief — which would state all the major
> observations and canonical truths from one of the ingestions.")* ⛔ **Deliberately NOT a self-improving
> system** — that ambition was ruled *"a little too complicated"* and is not being built. This closes the
> long-open `work/world-model.md` question: no new file format, no new machinery, an existing system pointed at
> the right job.
> ⏭ **Deferred but owed:** ⚠ **AMENDED 2026-08-08** — not "invokes `project-manager`" but: `1.10` WRITES the
> brief, `pm_flag.sh` ARMS it, and the run fills it as information arrives. Real work, explicitly not this pass.
> as information arrives. Real work, explicitly not this pass.

`2.0c` **Offer to inherit the previous corpus's world model.** — ONE-PASS · **human's turn** 🧑 — ⚠ **NOT BUILT**
> **STEP OUTCOME:** the human has consciously decided whether this run starts cold or starts already knowing
> them.
> **Does:** on finding a project from a previous corpus, **offers it — never assumes it**: *"You already have a
> project from a previous corpus. Want to include it? It'd bring in a lot from your earlier history and help us
> build a better picture of you."* Default is a **fresh project for this corpus**; inheritance is the human's
> choice.
> **Why:** *(the author, 2026-08-05)* — a new corpus is a new project so nothing merges silently, **but the value of
> the accumulated picture is real and should be on the table.** ⛔ Never merge two corpora without being asked.
> ⚠ The one case that genuinely warrants refusing inheritance — a corpus belonging to a **different person** —
> was ruled *"almost too edge case to plan for."* **Do not build for it.**

---

## TURN 1 — the machine looks, then explains 🤖

`2.1` **ORIENT — place the human before asking them anything.** — ONE-PASS · presentation
> **STEP OUTCOME:** the human knows what is being built, which stage they are in, what was already settled, and
> what they are about to be asked to do — before any list appears.
> **Does:** prints the map (all phases, plain language, current one arrowed), one line on what the previous
> phase settled, and what this phase is for. **Leads with the literal position — "Phase 2" — never a codename.**
> **Evidence:** the rendered screen in the transcript.
> **Why:** ⭐ **This step exists because its absence was measured as a failure on 2026-08-05.** A round opened
> with a codename and questions, and the stakeholder — the person who designed the thing — could not answer:
> *"I don't even know which phase we're in… Scan, what is scan? Already lost. I'm doing so many different
> session windows, you've got to remind me."* **Assume zero recall, every round, forever.**
> Format: `state/projects/skill-builder/examples/round-opening-template.md`.

`2.2` **Select and batch.** — ONE-PASS · logic
> **STEP OUTCOME:** the human faces a page they can finish in one sitting, not a wall.
> **Does:** takes the unruled chats and batches them. **Target ≈15; band 10–20. Fewer than 10 only when the
> pile itself has fewer than 10 left.**
> **Why:** *(the author)* — guidance with its reason, not a rule: a page has to be finishable in one sitting, and
> the pile count is already the number of sittings. Under ten wastes a round; over twenty stops being read.

`2.3` **Bracket the long operation.** — ONE-PASS · presentation ⚠ **RENUMBERED 2026-08-06** — was `2.5`,
placed after the step it brackets. Its "before" half has to fire before the fan-out below, so it comes
first; execution order (confirmed against `phases/2-scan.md`, where this block already precedes the read)
now matches the ID order.
> **STEP OUTCOME:** the human is told what is about to happen, then told what happened — never left watching
> silence.
> **Does:** before `2.4` fans out, says what it is about to do and roughly how big the job is; after, says what
> came back and what is now on screen.
> **Why:** tell-them-three-times, structural rather than advisory. *(the author: "you tell them what you're going to
> do FIRST, then what you're doing WHILE you're doing it, and at the end you tell them what you DID.")*

`2.4` **Read thin, in isolation.** — ONE-PASS · data ⚠ **RENUMBERED 2026-08-06, was `2.3`** (see `2.3`'s note).
> **STEP OUTCOME:** every chat on the page has a plain-language description good enough to rule on, produced
> without the main session ever touching an unsanitized body.
> **Does:** sanitizes each chat through the ingest gate, then hands the cleaned text to **tool-less reader
> agents** which return, per chat: **2–3 sentences of what it actually is** · the size · any sensitivity flag.
> **Refuses on:** an ungated body reaching the main session (hook-enforced, `ingest_gate_enforce.sh`).
> **Evidence:** the returned reader JSON; the gate's log.
> **Why:** ⛔ **Security invariant — the reader holds no tools, so a prompt-injection has nothing to act with.**
> The wall is structural, not cognitive. **2–3 sentences is a floor, not a style note:** it is the exact input
> the human's ruling rests on, and *"we need at least two sentences if not three."*

`2.5` **Group by subject, order by time.** — ONE-PASS · logic — ⚠ **NOT BUILT** *(renumbered 2026-08-06,
was `2.4` — see `2.3`'s note)*
> **STEP OUTCOME:** chats that are really one arc are shown as one arc, oldest to newest, so the human rules on
> the story rather than on ten scattered rows.
> **Does:** detects chats in the page that appear to be about the same subject; presents them **chronologically
> ordered**, labelled as a sequence; offers the reading — *"these ten look like one project over time; is that
> right?"* — and writes what the human says into the scratchpad (`2.0b`).
> ⛔ **Never asserts the most recent one is the definitive one.** It offers the chronology; the human rules.
> **Why:** *(the author)* several small chats on one subject over time **is a project**, and *"we can offer that to
> the human in the loop."* Seeing a sequence is a different act of judgment than seeing a list.
> **Deferred, deliberately:** the offer to **merge** them belongs at FILE (Phase 5), not here — merging is a
> decision about folder structure, not about what is worth reading.

`2.6` **Render the ruling screen.** — ONE-PASS · presentation
> **STEP OUTCOME:** the human can rule on every item without asking a follow-up question, and can answer by
> dictation.
> **Does:** tool-prints the page and the session **pastes it verbatim, never re-typing it into prose.**
> Per chat: **the 2–3 sentence description · the size · a ⚠ flag if enormous or sensitive.**
> ⛔ **NOT the title** — *(the author)* *"the title is never good when it comes to ChatGPT."*
> **Names all three verdicts on screen, explicitly**, with one line each on what they mean.
> Ends with one clear action.
> ⛔ **EVERY ITEM AND EVERY OPTION IS NUMBERED.** *(the author, prescriptive on his ruling:* *"anything the human can
> feedback on should be numbered… so the human can just easily say 1a, 2b, 3c."*)
> **Why the numbering is hard:** the human is **dictating**. An unnumbered list forces them to restate each
> item aloud, and **the cost is invisible to the machine** — it never experiences the friction, so it will never
> self-correct. That invisibility is what earns it invariant status under the test above.
> **Evidence:** the rendered screen. ⚠ **CORRECTED 2026-08-05:** this line also named `check_screens.py`
> (action bar last · no machine jargon) as an evidence surface. **It has ZERO callers** — no cron, no Pulse
> job, no hook, no test invokes it; it runs only if a human types `python3 check_screens.py`. A surface
> nothing reads is not an evidence surface (§III.8), so the honest answer here is the rendered screen alone.
> The same false claim was corrected the same day at `system/sops/skill-building-sop.md` LAW 1's evidence
> table. *(Both found while auditing that table; `build-sop.md` — "a broken claim has usually PROPAGATED,
> grep the whole system when you find one.")*

---

## TURN 2 — the human's turn 🧑

`2.7` **Rule each chat: KEEP · EXPLORE · TOSS.** — CORRECTION-LOOP · **GATE**
> **STEP OUTCOME:** every chat on the page carries a ruling the human is certain of — or is explicitly marked
> *not yet judgeable*.
> **Does:** accepts rulings by number, in any order, dictated. Applies them. **Anything the human does not rule
> on stays unruled** — silence is never consent.
> **Refuses on:** ⛔ closing the pile while any chat is unscanned or scanned-but-unruled — the coverage gate
> already exists and holds (`pipeline.py:1265-1270`), naming the count and the offenders. ⛔ **and, new:** while
> any chat sits in EXPLORE.
> **Evidence:** the per-row verdict in the corpus map.
> ⭐ **WHAT THE HUMAN CONTRIBUTES THAT THE MACHINE CANNOT: RECOGNITION.** The machine has only the three
> sentences it just wrote. The human reads them and **remembers the actual conversation** — who it was with,
> what came of it, whether it went anywhere. *(the author: "I recognize the chat from the two or three sentences
> you've given me and I'm able to recall that exact chat and I know for sure that it's very high value.")*
> No amount of better summarising reaches this. **It is the reason this turn exists**, and if it could be
> automated the turn would be ceremony and should be deleted.

---

## TURN 3 — the machine responds 🤖 ↩

`2.8` **Write the rulings, then say what happened.** — ONE-PASS · data + presentation
> **STEP OUTCOME:** the rulings are durable before the next screen, and the human sees the tally.
> **Does:** writes each verdict; reports *"N kept, N tossed, N going back for a closer look."*
> **Refuses on:** overwriting a verdict already closed (`pipeline.py:1008-1009` — this exists and is correct).
> **Why:** the human's ruling is the most expensive input in the system; it lands on disk before anything else.

`2.9` **Re-read the EXPLORE stack wider, and describe it at length.** — ONE-PASS · data — ⚠ **NOT BUILT**
> **STEP OUTCOME:** every chat the human could not judge comes back described well enough to judge — **a
> paragraph that covers the whole arc of the conversation**, not a longer version of the same thin blurb.
> **Does:** for each EXPLORE chat, feeds the reader a **larger slice** of the sanitized body and asks for
> **8–12 sentences covering the breadth of the session** — where it started, what it moved through, where it
> ended up. Same medium as round one, materially more of it.
> **Why this shape:** *(the author, 2026-08-05, overriding an earlier draft of this step)* *"It would NOT help to
> have the actual words… what I want is more like a paragraph, let's say 8 to 12 sentences, that covers the
> breadth of the arc of the whole session. That's what I need."* **A 2–3 sentence blurb sometimes nails a chat
> and sometimes misses it entirely; when it misses, the fix is BREADTH — the reader saw too little of the
> conversation to characterise it.** *(An earlier draft specified verbatim opening-and-closing exchanges. The author
> overrode it explicitly: "I'm overriding how it started versus how it ended. We want just the larger summary."
> Recorded so it is not re-proposed.)*
> ⭐ **THE MECHANISM IS THE SCAN SLICER — the lever already exists.** SCAN already reads a slice via
> `adaptive_char_slice`, capped by **`SCAN_TOTAL_CAP = 10000`** (`tag.py:99`). **An EXPLORE round is the same
> path with a larger cap and a longer requested summary.**
> ⚠ **Do NOT reach for `giant_sample` / `GIANT_COVER = 0.30`** (`tag.py:129,132-146`) — that is the DEEP-READ
> giant-handling lever, a different rung, and its 0.30 is a round-up of a research figure whose own source calls
> it *"NOT proven."* **The explore cap is its own knob and carries its own reason.**
> **Security is unchanged:** the wider slice is still cut from **gate-sanitized** text and still read by a
> **tool-less** agent. Widening the slice does not widen the attack surface.

`2.10` **Write what was learned into the PROJECT BRIEF.** — ONE-PASS · data — ⚠ **NOT BUILT**
> **STEP OUTCOME:** what was learned this sitting is available to the next sitting — **and to the next corpus.**
> **Does:** appends the durable material to the run's project brief (`2.0b`) — confirmed subject-arcs,
> corrections the human made, observations about how this person works, anything that would otherwise have to
> be rediscovered.
> **Why:** the pile spans sittings and windows; context is RAM, the brief is storage. **And this is the step
> that makes the world model real** — a brief that only gets read is a document; a brief that gets written to as
> the run proceeds is a picture that sharpens.

---

## THE LOOP — where the round actually lives

**`2.6` → `2.7` → `2.8` → `2.9` → back to `2.6`, carrying only the EXPLORE stack plus any not-yet-seen chats.**

- **Each round the machine offers, verbatim:** *"N chats came back with a closer look, and M are still to see.
  Another round, or stop here for now? — I'd suggest another round because the pile can't close until the
  explore stack is empty."*
- **What carries between rounds:** the explore stack · the scratchpad · every ruling already made (never re-asked).
- **The exit backstop:** the human can stop at any time; the pile simply stays open and resumes. ⛔ **What the
  machine may never do is CLOSE the pile with an explore stack outstanding.**
- **Round-over-round the material must CHANGE**, not merely repeat — a round that returns the same kind of
  information the human already rejected is a wasted sitting.

> **⚠ NOT BUILT.** Today's pagination is **advance-only** — it walks forward through still-unruled chats
> (`2-scan.md:100-101`) and never returns a chat for a second look. **This loop is the phase's missing spine.**

---

## FINAL TURN — close

`2.11` **Close the pile.** — ONE-PASS · **GATE**
> **STEP OUTCOME:** the pile is marked done only when every chat in it carries a terminal human ruling.
> **Does:** sets the pile complete; reports the split; names the next pile.
> **Refuses on:** ⛔ any chat unscanned · unruled · **or still in EXPLORE.** The refusal names the count and the
> first few offenders.
> **Why:** ⛔ **Loss-prevention invariant.** A pile marked complete drops its chats out of phase routing — they
> are never shown again. This is the one place in the phase where a mistake is **invisible and unrecoverable**,
> which is exactly what earns a hard gate.
> **Then it STOPS.** ⛔ Does not roll into the deep read. The human re-invokes; the re-invocation is the
> re-anchor.
> **NEXT:** `3-deep-read.md`.

---

## WHAT THIS PHASE OWES — the build list this spec generates

| # | Item | Size |
|---|---|---|
| 1 | ✅ BUILT 2026-08-05 (commit 4960049) — **a third, NON-TERMINAL verdict** (`2.7`) — the phase's spine; everything else hangs off it | real work |
| 2 | ✅ BUILT 2026-08-05 (commit 4960049) — **the round loop** (`THE LOOP`) — return the explore stack for a second ruling | real work |
| 3 | **The explore re-read** (`2.9`) — a larger `SCAN_TOTAL_CAP` on the explore path + an 8–12 sentence ask | small |
| 4 | **The project brief as the world model** (`2.0b`, `2.10`) — ⚠ **AMENDED 2026-08-08:** NOT "wire to `project-manager`". `1.10` writes the brief directly, `pm_flag.sh` arms it, the run appends as information arrives. ⛔ Never that skill's Create/Frame-intake path. | medium |
| 4b | **The inheritance offer** (`2.0c`) — offer the previous corpus's project, never assume it | small |
| 5 | **Subject-clustering, chronologically ordered** (`2.5`) | medium |
| 6 | **Screen changes** (`2.6`) — drop the title, show the size, name all three verdicts, number everything | small |
| 7 | **Extend the coverage gate** (`2.11`) to refuse on a non-empty explore stack | small |
| 8 | **The orientation block** (`2.1`) | small |

---
---

# 9. PHASE 3 — THE WORLD MAP *(fully specified)*

> **Drafted 2026-08-05** against the format locked in §7 / `producer-spec-template.md` §6c, from the author's
> redesign of the old REFLECT phase. **`⚠ NOT BUILT` marks something that does not exist yet — and almost
> all of this phase is not built.** The old Phase 4 rendered a reflection screen and stopped; this phase
> is that screen's job plus the verification the old Phase 3 (DEEP-READ) used to do, merged, because they
> were always the same human sitting down once.

> ## ⛔ WHAT IS PRESCRIPTIVE IN THIS SECTION — READ BEFORE EDITING
> **Only the three OUTCOMES are nailed to the floor:** the SKILL OUTCOME, the PHASE OUTCOME, and each STEP
> OUTCOME. **Everything else — every number, threshold, ordering, phrasing and method — is GUIDANCE
> CARRYING ITS REASON** and may be rewritten by a later session or by the skill-tester without asking,
> provided the outcome it serves still lands.
> **The three exceptions that stay hard:** ① security invariants · ② human-elimination gates (only the
> human rules what is true about them) · ③ loss-prevention gates. Test: *if this is violated, can the
> damage be SEEN and UNDONE?* Yes → guidance. No → invariant.

**SKILL OUTCOME:** someone hands over a huge corpus and walks away with a personal folder schema ready to
drop into Lifehack — every folder a knowledge boundary with its own canon file and stated purpose,
subdividing wherever there's enough material. **Not one big document; that's useless to an LLM.**

**PHASE OUTCOME:** **the human has read a paragraph about themselves drawn from this pile, corrected what
is wrong in it, and ruled where each surviving finding belongs — canonical, dated, or a record — and what
folder shape this pile has earned.** They finish the pile knowing the machine understands them better than
it did an hour ago, *and* having proved it.

**HOW THIS PHASE SERVES THE SKILL:** this is **the reward and the verification at the same time, and that
is not a coincidence** — the only way to check whether the machine understood a pile is to show the human
what it thinks it learned and watch them react. It is also where the folder tree gets built. Phase 1 drew
the first draft of that tree as piles; **this phase corrects and commits one branch of it per pile, while
the material is fresh** — which is what makes Phase 4 small instead of a design marathon done tired.

> ## ⚖⚖ RESTRUCTURED 2026-08-08 — PHASE 3 IS **FIVE TURNS**, NOT ONE SCREEN *(the author, `authority: user`)*
>
> He rejected the one-paragraph-then-rule shape outright: *"we can't go through each one of these turns one
> paragraph at a time."* **The steps below (`3.1`–`3.9`) keep their content; what changed is the SHAPE they are
> delivered in.** Persisted as the most recent best current thinking, not as locked.
>
> **TURN 1 — THE WORLD MAP (the reward).** Screen title: **`WORLD MAP: <pile name>`** — the pile is named on
> screen every time (same zero-recall law as `3.1` ORIENT). Then **ONE TO FOUR PARAGRAPHS**, detailed:
> *"here's like one paragraph to four paragraphs — this is what is true about you, this is the world model that
> I'm able to gather from this pile of information."* ⚠ **This SUPERSEDES `3.2`'s "a PROSE PARAGRAPH"** — the
> unit is 1–4 paragraphs and *"a pretty good output."* **Prose, still never a list** — that part is unchanged
> and remains the one mechanical choice not negotiable on taste.
> → **feedback turn.**
>
> **TURNS 2-4 — THE APPROVALS, IN PRIORITY ORDER: permanent truths → dated facts → records.**
> ⭐ **CANONICAL COMES FIRST BECAUSE IT MATTERS MOST** — his stated reason, not an arbitrary order.
> **CANONICAL RENDERING, prescribed:** *"it's going to speak in full sentences, it's going to have given
> historical context, and it's going to give at least three lines — but if it's a really big subject, it'll
> give up to five lines of information about what the canonical information is and what's going to be saved
> durably, so that the human can approve."* ⇒ **3 lines minimum, up to 5 for a big subject, full sentences,
> with historical context.** Same law as PHASE 1's board and `2.4`'s 2–3 sentences: **enough substance per item
> to be rulable.** → **feedback turn after each section.**
>
> **⑂ PAGINATION — THE COUNT DECIDES.** *"If the canonical approvals and the dated approvals and all the
> records that want to be kept can fit in one page, then we can do it all in one page. Probably most likely it
> won't fit in one page. So we would divvy it up… if there's more than 10 results, it needs to go to its own
> separate turn, it needs to be pushed to a later turn."* ⇒ **all three fit → ONE page; any type over ~10 items
> → its own turn, split again as needed.** *(He said 15 earlier in the same breath, then settled on 10.)*
> ⭐ **Cheap to build — it is `2.2`'s batcher pointed at findings instead of chats.**
>
> **TURN 5 — THE FOLDER SHAPE** (`3.4`, unchanged in content) → **feedback turn.**
>
> **EVERY APPROVAL TURN OFFERS THE SAME THREE MOVES:** *"you can approve, or make notes and then move on, or…
> take my notes and then let's loop. You can repeat the turn if you want."* ⇒ **APPROVE · NOTE-AND-MOVE-ON ·
> REFINE-AND-REPEAT-THIS-TURN.**
>
> ⚠ **HIS OWN GUARD-RAIL, quoted so nobody over-builds this:** *"I don't know how complicated that is really —
> if this breaks everything, I don't want to fucking bother doing it. But that's an ideal situation. **We don't
> need to be prescriptive about it. We'll test it.** But let's try to make that happen."* ⇒ **GUIDANCE CARRYING
> ITS REASON, not an invariant.**
>
> ⚠ **CONSEQUENCE, flagged honestly:** PHASE 3 becomes the LONGEST sitting in the skill. Under the
> phase-is-a-unit-of-human-attention law it is still ONE phase, and the pagination rule is precisely what keeps
> it survivable.
>
> ⚠ **AND `3.4`'s SPLIT TEST IS INCOMPLETE AS WRITTEN — see §5c C3.** It says *"subdivide where there is enough
> material,"* which is the **too-BIG** half only. The author's own 2026-08-05 ruling has a second half: **too DIVERSE
> → siblings, not nested.** That half is what decides sibling-vs-child, and it is missing. `3.4` must also
> carry the **cost test** — *the highest folder where it is still always-true, and no higher.*
>
> ❓ **STILL OWED: does the world map ACCUMULATE across piles?** His 2026-08-08 wording — *"the world model I'm
> able to gather from **this pile**"* — settles the SOURCE (this pile) but not whether pile four knows what
> piles one to three taught it. **Session's read, offered and not ruled:** the paragraphs are drawn from this
> pile, and ACCUMULATION lives in the run's project (`3.8`), which later piles read back as context. ⛔ Still
> do not guess it into the spec.

---

## THE THREE OUTPUT TYPES — the closed vocabulary this phase turns on

*(the author, 2026-08-05. **The last two split by SHAPE, not by durability** — that distinction is the whole
reason there are three and not two.)*

| Type | What it is | Authored or moved? |
|---|---|---|
| **CANONICAL** | always-true about this person — the things a cold session must know to act as them | **AUTHORED** |
| **DATED-BUT-VALUABLE** | true as of a date; a **discrete** statement worth keeping with its date attached | **AUTHORED**, with the date |
| **RECORD** | a **body of material** you would go and read — not a claim, a corpus | ⛔ **a SHORT STUB FILE is written; the original is never rewritten** |

### ⚖ RULED 2026-08-05 (the author) — a RECORD becomes a STUB FILE, not a move and not a bare pointer

Neither of the two earlier framings was right, and they had been contradicting each other in this file.

**What actually happens:** a **new file is created** in the destination folder (e.g. a `research/` folder).
That file contains **a paragraph or two describing what is inside**, plus **a pointer to the original**.
**The original stays where it is and is never rewritten.**

*(the author, verbatim: "It can go into a research folder, but it's really just a pointer… I do want a file, and
that file will describe what's inside — like a paragraph or two of what's inside the pointer, with a
pointer. But I do want a file inside of their research documents.")*

**Why this shape and not the alternatives:**
- ⛔ **Not "moved."** Cutting a big thread out and re-placing it costs tokens and time for no gain —
  *"I don't want to spend a lot of money, like token time, tokens or time on it."*
- ⛔ **Not a bare pointer with no file.** A folder holding only references is not browsable; you would have
  to open each original to know what it was.
- ✅ **A stub file is the cheap middle.** One or two paragraphs is affordable to author, and it makes the
  folder readable on its own while the real content stays put.

**This is what separates RECORD from DATED**, which had been blurry: *"dated findings and records are the
same, but dated is just smaller."* A **dated** item is small enough to state outright. A **record** is too
big, so you state what it *is* and point at it.

**The human is asked which records earn a stub** — a real decision, not a formality; a stub for everything
is the same as no filing at all.

*(Mechanism that already exists: the `pointer_candidate` chat-row column — "big-but-only-a-record chat —
pointer-ize, do NOT full-read. Addressing, not elimination.")*

⛔ **RECORDS GET A STUB FILE — the original is NEVER rewritten.** *(the author, 2026-08-05, reversing himself mid-thought — he first
described cleaning them up, then withdrew it: "we're not going to bother spending LLM tokens rewriting
it.")* **Only canon and dated information get authored.** A record's value is that it is the real thing;
rewriting it into cleaner prose spends tokens to make it less true.

> ⛔ **DO NOT RE-PROPOSE: "the human rules on the pile's boundary" as this phase's job.** An earlier draft
> framed it that way and the author rejected it as **meaningless** — the session had reverse-engineered a job
> for the phase in order to give it a machine-checkable gate. The boundary work belongs to Phase 1 (where
> the piles are drawn) and to the folder-shape step below (where one branch is confirmed); it is not this
> phase's purpose. **Recorded so the shape of the mistake survives, not just the verdict.**

---

## BEFORE THE PHASE RUNS — off-camera 🌙 *(no human turn)*

*These three were old Phase 3 (DEEP-READ). They are machine-only, so under the phase-is-a-unit-of-
human-attention ruling they are STEPS, attached to the front of the phase whose human turn they feed.*

`3.0` **Bracket the long operation.** — ONE-PASS · presentation ⚠ **RE-TIMED 2026-08-06** — was numbered
`3.5` (after `3.4`, inside Turn 1), several steps after the operation it brackets had already run. `3.0b`
is machine-only and fans out here, before Turn 1 ever starts, so a step meant to announce it "before it
fans out" has to run from here, not from the far side of Turn 1.
> **STEP OUTCOME:** the human is told what is about to happen, then told what happened — never left
> watching silence.
> **Does:** before `3.0b` fans out, says what it is about to do and roughly how big the job is; after,
> says what came back. **Tell-them-three-times, structural rather than advisory.**

`3.0a` **Partition the keepers by size.** — ONE-PASS · logic
> **STEP OUTCOME:** every keeper in this pile is routed to the read treatment its size actually needs, and
> the rare monster is flagged rather than silently truncated.
> **Does:** short / whole (≤100k chars) / giant. Giants are sampled head+tail and **FLAGGED for a human
> ruling**, never quietly summarised.
> **Why:** the whole-read-plus-cache strategy was settled by a blind architecture council (2026-07-12) and
> the two-tier slicing band it replaced was deleted. ⛔ Do not re-open it.

`3.0b` **Bundle and spawn the tool-less readers.** — ONE-PASS · data
> **STEP OUTCOME:** every keeper is read for meaning without the main session ever touching an
> unsanitized body.
> **Does:** gate-sanitizes, bundles, spawns `ingest-conclusions` agents — **model `sonnet`** (reverted
> from haiku 2026-07-11: *"haiku lost the intuition"* — a MEASURED regression, do not re-litigate),
> `run_in_background: true`, **spawned UNNAMED** (a named teammate gets a mailbox and its final report is
> discarded — measured 249 named spawns → 0 payloads).
> **Why:** ⛔ **Security invariant — the reader holds `tools: Read` only.** A prompt-injection that hijacks
> it has nothing to act with. The wall is STRUCTURAL, not cognitive.

`3.0c` **Collect and coalesce.** — ONE-PASS · data
> **STEP OUTCOME:** one conclusion set per chat, with a chat split across several readers merged rather
> than double-counted.
> **Does:** merges every per-agent JSON by chat key. ⚠ **Dedup is by EXACT object equality**
> (`pipeline.py:816-821`) — two readers phrasing the same conclusion differently both survive. Near-
> duplicate text is a real residual defect; *absent* dedup is not, despite what the open loop says.

---

## TURN 1 — the machine looks, then explains 🤖

`3.1` **ORIENT — place the human before showing them anything.** — ONE-PASS · presentation
> **STEP OUTCOME:** the human knows what is being built, which stage they are in, what the last stage
> settled, and what they are about to be asked to do — before any content appears.
> **Does:** prints the map (all four phases in plain language, current one arrowed), one line on what
> Phase 2 settled for this pile, and what this phase is for. **Leads with the literal position — "Phase 3"
> — never a codename.**
> **Why:** ⭐ **its absence was MEASURED as a failure on 2026-08-05.** A round opened with a codename and
> questions, and the stakeholder — the person who designed the thing — could not answer: *"I don't even
> know which phase we're in… Already lost. I'm doing so many different session windows, you've got to
> remind me."* **Assume zero recall, every round, forever.**

`3.2` **Write the paragraph about the person.** — ONE-PASS · logic — ⚠ **NOT BUILT**
> **STEP OUTCOME:** the human reads a short piece of continuous prose about themselves, drawn from what
> this pile actually said, and can tell at a glance whether it is right.
> ⚠ **AMENDED 2026-08-08 — the UNIT is now ONE TO FOUR PARAGRAPHS, not "a paragraph."** *(the author: "one paragraph
> to four paragraphs — this is what is true about you, this is the world model that I'm able to gather from this
> pile.")* The screen is titled **`WORLD MAP: <pile name>`**. **PROSE-not-a-list is UNCHANGED and still the one
> mechanical choice not negotiable on taste.** See §9's restructure block.
> **Does:** synthesizes the pile's conclusions into **a PROSE PARAGRAPH — not a list.**
> ⭐ **THE PROSE IS LOAD-BEARING, AND THIS IS THE ONE MECHANICAL CHOICE IN THE PHASE THAT IS NOT
> NEGOTIABLE ON TASTE.** *(the author, 2026-08-05:* **"a wrong sentence about someone jumps out; wrong item
> fourteen of twenty does not."***)* A list invites scanning and a rubber stamp; a paragraph about you
> that contains a false sentence is physically uncomfortable to read past. **The format IS the error
> detector** — which is why this phase's verification and its reward are the same screen.
> **Why not a list:** the same finding that killed the one-line-per-item rule in Phase 1. A screen a human
> must approve or deny needs enough substance per unit to be rulable; truncated rows produced a rubber
> stamp when measured.

`3.3` **Propose each finding's TYPE, and teach while asking.** — ITEM-LOOP · presentation + logic — ⚠ **NOT BUILT**
> ⛔ **SUPERSEDED IN SHAPE, 2026-08-08 — this is no longer ONE flat loop over all three types.** The ratified
> structure is **three separate approval TURNS in priority order: permanent truths → dated facts → records**,
> canonical first *because it matters most*, each with **3 lines minimum and up to 5 for a big subject, in full
> sentences with historical context**, and **a feedback turn after each section**. ⑂ **Pagination:** all three
> fit → one page; **any one type over ~10 items → its own turn.** The CONTENT of this step (propose a type with
> its reason, teach by using the distinction on the human's own material, never front-load definitions) is
> UNCHANGED and still governs. See §9's restructure block for the full shape.
> **STEP OUTCOME:** every surviving finding from this pile arrives with a proposed type — canonical,
> dated, or record — and a one-line reason the human can disagree with.
> **Does:** for each finding, proposes one of the three types **with its reason stated in the human's
> language**, e.g. *"I'd make this canonical — it's not about one project, it's how you decide, and it
> showed up in four separate chats a year apart."*
> ⭐ **IT TEACHES WHILE IT ASKS.** The human is not expected to arrive knowing what "canonical" means in
> this system. Each proposal explains the distinction *by using it on their own material*, which is the
> only explanation that survives. **Do not front-load a definitions screen** — that is the machinery
> surfacing, and the machinery must not surface.
> **Evidence:** the per-finding type recorded on the row. Checkable.
> ✅ **CORRECTED 2026-08-08 — this line said "⛔ A record is MOVED," which CONTRADICTED §9's own ruling 120
> lines above** (*"⛔ **Not 'moved.'** Cutting a big thread out and re-placing it costs tokens and time for no
> gain"*). **A RECORD IS NEVER MOVED AND NEVER REWRITTEN — a SHORT STUB FILE is authored in the destination
> folder** (a paragraph or two on what is inside, plus a pointer) **and the original stays exactly where it
> is.** Re-confirmed by the author a third time on 2026-08-08: *"even though we're doing pointers to the records, I
> still want to have a separate file with the pointer inside of it, so we can have a stand-in for where that
> would go, and in the future if it needs to pull all that information in, it'll do so."*
> ✅ **RESOLVED 2026-08-08 (Phase 9, task 9.2.3) — `phases/4-place.md:172`, the file that actually RUNS, now
> reads "⛔ A RECORD GETS A STUB FILE — THE ORIGINAL IS NEVER MOVED, NEVER REWRITTEN"; see §5d row 9.**
> *(Original note, kept as the record: the same false line was propagated into `phases/4-place.md:172`
> ("⛔ RECORDS ARE MOVED, NEVER REWRITTEN") — the file that actually RUNS. Fixing the driver was owed.)*

`3.4` **Propose the folder shape this pile has earned.** — ONE-PASS · presentation + logic — ⚠ **NOT BUILT**
> **STEP OUTCOME:** one branch of the folder tree — this pile's — is drawn concretely enough for the human
> to correct it, with its own canon file and stated purpose.
> **Does:** proposes the folder (or the folder and its sub-folders) this pile becomes, each with a
> one-line purpose. **Subdivide where there is enough material; a light pile stays one flat folder.**
> **Why here rather than at the end:** ⭐ **THE FOLDER SCHEMA IS THE SPINE, NOT THE OUTPUT.** The pile was
> already a boundary guess in Phase 1; this is where it gets tested against what the material turned out
> to contain. Deferring every branch to a single end-of-run design session means designing a tree while
> tired, about material read weeks ago. **This is what makes Phase 4 small.**
> ⚠ **The placement rule is a COST rule, and it applies here.** `/read` chain-walks parent canon
> (verified, `skills/read/SKILL.md` Step 0.6), so a line placed high is charged to **every** conversation
> below it, forever. Propose the deepest home that fits, not the most convenient one.

---

## TURN 2 — the human's turn 🧑

`3.6` **Correct the paragraph, rule the types, rule the folder shape.** — CORRECTION-LOOP · **GATE**
> ⛔ **SUPERSEDED IN SHAPE, 2026-08-08 — this is no longer ONE combined human turn.** the author: *"we can't go
> through each one of these turns one paragraph at a time."* ⇒ **a SEPARATE feedback turn follows EACH of the
> five turns** (world map · permanent truths · dated facts · records · folder shape), and every one of them
> offers the same three moves: **APPROVE · NOTE-AND-MOVE-ON · REFINE-AND-REPEAT-THIS-TURN.** Everything this
> step says about WHAT the human contributes — *whether a sentence about them is TRUE* — and the
> human-elimination invariant is UNCHANGED and still governs. See §9's restructure block.
> ⚠ **§9 HAS NO `3.5`** — it jumps `3.4` → `3.6`. Reassign ids ONCE with a published old→new mapping when this
> section is rewritten to the five-turn shape; ⛔ do not renumber piecemeal.
> **STEP OUTCOME:** the paragraph says something true about this person; every finding carries a type they
> chose or accepted; the pile's folder branch is one they would actually live inside.
> **Does:** accepts corrections in any order, dictated, **by number** — every finding and every option is
> numbered so `1a, 2b, 3c` works. Applies them. **Anything not ruled stays unruled; silence is never
> consent.**
> **A valid response is any of four moves:** *"that sentence is wrong, here's what's true"* · *"number 4
> isn't canonical, it was just that one job"* · *"split that folder, those are two different things"* ·
> *"that's right, move on."*
> ⭐ **WHAT THE HUMAN CONTRIBUTES THAT THE MACHINE CANNOT: WHETHER A SENTENCE ABOUT THEM IS TRUE.** The
> machine can synthesise a claim that is well-supported by the pile and still false about the person —
> because the pile is what they *wrote down*, not what they *are*. It cannot know that a position argued
> across nine chats was a phase they abandoned, or that one throwaway line was the thing that actually
> stuck. **No amount of better synthesis reaches this**, and if it could be automated this turn would be
> ceremony and should be deleted.
> ⛔ **Human-elimination invariant:** the machine never rules a finding canonical on its own. It proposes;
> the human rules.

---

## TURN 3 — the machine responds 🤖 ↩

`3.7` **Write the rulings, then re-render the paragraph with the corrections folded in.** — ONE-PASS · data + presentation — ⚠ **NOT BUILT**
> **STEP OUTCOME:** the corrections are durable before anything else happens, and the human SEES their
> correction land — the paragraph comes back changed.
> **Does:** writes each type ruling and the folder branch to the map; regenerates the paragraph
> incorporating what the human said; shows it again.
> **Why the re-render is the product, not a nicety:** the phase's stated reward is *watching the model of
> you get sharper.* A correction that vanishes into a file and never visibly changes the picture is
> indistinguishable, from the human's side, from not having been heard. **This is the step that makes the
> reward real.**

`3.8` **Write what was learned into the run's PROJECT BRIEF.** — ONE-PASS · data — ⚠ **NOT BUILT**
> **STEP OUTCOME:** what this pile taught is available to the next pile, the next sitting, and the next
> corpus.
> **Does:** appends the confirmed paragraph, the corrections, and the folder branch to the run's project
> brief **directly** — the same file `1.10` created, in the shape `project-manager` reads. ⛔ Never via that
> skill's Create / Frame-intake path (§0d ruling 2), and never in a second brief format.
> **Why:** ⭐ **THE WORLD MODEL IS THE PROJECT BRIEF — solved by reuse, not by building an artifact.**
> *(the author, 2026-08-05.)* No new file format, no new machinery. ⛔ **Deliberately NOT a self-improving
> system** — that ambition was ruled *"a little too complicated"* and is not being built.

---

## THE LOOP — where the round actually lives

**`3.2` → `3.6` → `3.7` → back to `3.2`, carrying the corrections.**

- **Each round the machine offers, verbatim:** *"That's what I've got about you from this pile. Another
  round, or move on to `<next pile>`? — I'd suggest `<X>` because `<Y>`."*
- **What carries between rounds:** the corrected paragraph · every type ruling already made (never
  re-asked) · the folder branch.
- **The per-round yield must CHANGE**, not merely repeat: round 1 is the machine's read · round 2 is the
  human's correction · **round 3 is the machine re-reflecting with the correction folded in.** A round
  that returns the same picture the human just corrected is a wasted sitting.
- **The exit backstop:** the human can stop at any time; the pile stays open and resumes.
- After about three rounds, recommend moving on and say why — past that it is usually taste rather than
  signal.

> ❓ **OPEN — THE OWNER'S RULING OWED. Does the paragraph ACCUMULATE across piles?** By pile four, does it
> carry what piles one through three taught it, or is each pile's paragraph drawn only from that pile?
> **This changes what `3.2` is built from and it is not a detail** — it is the difference between four
> separate observations and one picture getting sharper.
> **My recommendation: YES, it accumulates** — that accumulation IS the *"sharper every round"* the skill
> promises, and `3.8` already writes each pile's yield into a brief that `3.2` could read back. But this
> is a design call with a real cost (a wrong early sentence propagates), and it is **not mine to make.**
> Raised twice on 2026-08-05 and never ruled. ⛔ **Do not guess it into the spec.**

---

## FINAL TURN — close

`3.9` **Close the pile's world map.** — ONE-PASS · **GATE**
> **STEP OUTCOME:** the pile is marked read-complete only when every finding in it carries a human-chosen
> type and the pile's folder branch is set.
> **Refuses on:** ⛔ any keeper with no staged conclusion · ⛔ any sampled GIANT still unruled (both gates
> exist today and hold) · ⛔ **and, new:** any surviving finding with no type, or a pile with no folder
> branch recorded.
>
> ### The done-condition — and an honest note about what it does NOT check
> **What IS machine-checkable, and is the gate:** every surviving finding carries one of the three types;
> every giant is ruled; the pile's folder branch exists on the map. All three are columns; all three are
> checkable; a build can prove them.
> **What is NOT checkable, deliberately:** *whether the human actually read the paragraph and thought
> about it.* Its only evidence surface is the transcript, which is **NOWHERE** — so per the standing rule,
> grading it must return INCONCLUSIVE and **never FAIL**, and the honest move is not to fake a check for
> it. ⛔ **Do not invent a proxy gate for reflection.** That is exactly the mistake the author already rejected
> once in this phase (the "rule on the pile's boundary" framing) — reverse-engineering a job so the phase
> has something mechanical to refuse on. **The three real gates above are the done-condition; the
> reflection is what the phase is FOR, not what it is graded on.**
>
> **Then it STOPS.** ⛔ Does not roll into the next pile. The human re-invokes; the re-invocation is the
> re-anchor.
> **NEXT:** the next pile's Phase 2, or — when every pile is done — Phase 4.

---

## WHAT THIS PHASE OWES — the build list this spec generates

| # | Item | Size |
|---|---|---|
| 1 | **The paragraph composer** (`3.2`) — prose, not a list; the phase's spine | real work |
| 2 | **The three-type proposal + teach-while-asking** (`3.3`) — proposes a type per finding with its reason | real work |
| 3 | **The re-render with corrections folded in** (`3.7`) — the step that makes the reward real | real work |
| 4 | **The folder-shape proposal** (`3.4`) — one branch of the tree per pile, with its purpose line | medium |
| 5 | **The round loop** (`THE LOOP`) — carrying corrections, with the verbatim offer | medium |
| 6 | **The close-gate extension** (`3.9`) — refuse on an untyped finding or a missing folder branch | small |
| 7 | **The brief write-back** (`3.8`) — same `project-manager` wiring Phase 2 needs; build once, use twice | small (shared) |
| 8 | **The orientation block** (`3.1`) — same component Phase 2 needs; build once, use twice | small (shared) |

---
---

# 10. PHASE 4 — PLACE IT + THE ROOT CANON *(specified 2026-08-08)*

> **⚖ THIS SECTION IS NEW.** Until 2026-08-08 PHASE 4 was the only phase with **no spec section at all** —
> §7/§8/§9 existed for phases 1/2/3 and PHASE 4 had a six-line sketch at §5b. Drafted here from the 252-line
> runtime driver `phases/4-place.md` (the real authority in its absence) plus this session's rulings, and
> ratified with the author. **Persisted as the most recent best current thinking, not as locked.**

> ## ⛔ WHAT IS PRESCRIPTIVE IN THIS SECTION
> Same rule as §8/§9: **only the OUTCOMES are nailed down.** Every number, ordering, phrasing and method below
> is **guidance carrying its reason.** The three that stay hard regardless: ① security invariants ② human-
> elimination gates ③ loss-prevention gates.

**SKILL OUTCOME:** see §0b — the person owns a folder tree that behaves like a knowledge system, thin at the
top and heavy at the leaves, with nothing canon without their own yes.

**PHASE OUTCOME:** **everything the human kept is filed where they put it, in the tree already agreed pile by
pile; nothing was written without them seeing the actual file first; and canon candidates are still waiting on a
separate, explicit yes.**

**HOW THIS PHASE SERVES THE SKILL:** it is **execution, not design.** The tree was drawn as piles in PHASE 1 and
corrected one branch per pile in PHASE 3, while each pile's material was fresh. ⛔ **If you find yourself
DESIGNING the tree here, PHASE 3 did not do its job — go back.** Designing a folder tree at the end, tired,
about chats read weeks ago, is the exact failure the 2026-08-05 restructure removed.

---

## ⛔ THE GATE THAT PRECEDES EVERYTHING — MAIN SESSION ONLY

`4.0` **HARD_STOP.** — GATE · security
> **STEP OUTCOME:** no record is ever written by a process that cannot pause for a human yes.
> **Does:** if this is not the main interactive session, **ABORT** and print *"the /ingest placing phase must
> run in the main session — aborting."* (`4-place.md:35-38`).
> **Why:** this is the ONLY phase that writes, and it writes only after per-item approval. **A spawned subagent
> cannot pause for approval**, so its running here is a violation by construction, not a judgment call.

## TURN 1 — the machine gathers and shows the whole shape 🤖

`4.1` **LOAD the manifest.** — ONE-PASS · data
> **STEP OUTCOME:** every keeper across every pile is in hand, with its staged finding and its type — and no
> chat body is ever read again.
> **Does:** reads the map only; reports the split (canon candidates / pointers / plain records) and says
> plainly *"nothing's saved yet; you'll approve every folder and every note before it lands."*
> **Evidence:** the manifest count vs the map's keeper count. Checkable.

`4.2` **ASSEMBLE the tree PHASE 3 already ruled.** — ONE-PASS · logic + presentation
> **STEP OUTCOME:** the human sees the WHOLE shape for the first time — every pile's branch, assembled — rather
> than one branch at a time.
> **Refuses on:** ⛔ **any pile with no `folder_branch` recorded → that pile goes BACK TO PHASE 3.** The
> computer does not invent a branch here (`4-place.md:119`).
> ⛔ **AND IT NEVER RENAMES** (§0a ruling 2). A wrong name at this point is a PHASE 3 defect, not a PHASE 4 fix.
> **Then scaffold each confirmed folder** with its own **`canon/purpose.md`** (a PURPOSE line — never a
> done-when) and **`canon/current.md`**, plus **`records/`**. See §5c C2 for the verified convention and §5c C3
> for the placement doctrine the shape must obey.
> ❓ **OPEN — knowledge folders or full desks?** §5c C2. This decides whether this step also prints N registry
> blocks for the human to hand-paste.

`4.2b` 🧑 **The human rules the whole tree.** — CORRECTION-LOOP · **human's turn**
> **Three moves, the same three as PHASE 3:** approve · note-and-move-on · refine-and-repeat.

## TURN 2 — the human approves the FILES, not the ideas 🧑

`4.3` **CONFIRM — the tool-printed filing plan.** — ONE-PASS · presentation
> **STEP OUTCOME:** the human approves **the actual record, rendered at full detail**, before anything is
> written anywhere.
> **Does:** a TOOL prints the plan (⛔ never hand-assembled in prose) — one row per item: what it is, the home
> it earns, and why. **Records and pointers first; canon candidates LAST, each flagged ⚠.**
> ⭐ **PHASE 3's PAGINATION RULE APPLIES HARDEST HERE** — this is the screen most likely to hold hundreds of
> rows. All fits → one page; more than ~10 of a kind → its own turn.
> ⛔⛔ **AND THE SPEC'S OWN "ITEM-LOOP" LABEL FOR THIS STEP IS WRONG — LAW 8 verdict: INTENT WAS WRONG.**
> *(Swarm, 2026-08-08, the CHRONOLOGY second look. This is the one recommended fix the main session
> DISAGREED with as first stated, and it is recorded because a literal reading would have been built.)*
> §5b types `4.3` as **ITEM-LOOP**. Taken literally against a 1,520-chat corpus that means **one screen per
> record — dozens to well over a hundred turns**, on top of the 48 mandatory sittings already counted. The
> live code (`4-place.md:149-168`) correctly **batches all rows onto one screen behind a two-key gate**, and
> the batching is right. ⇒ **THE DEFECT IS THE ROW'S DEPTH, NOT ITS BATCHING. The fix is FULLER CONTENT PER
> ROW, STILL BATCHED** — never a per-item loop. ⛔ Do not "make the code match the spec" here; the spec's step
> TYPE loses.
> ⭐ **SAY OUT LOUD WHAT IS BEING ASKED, because it is NOT what PHASE 3 asked.** PHASE 3 asked *"is this a
> permanent truth?"*; this screen asks *"here is the file I would write, word for word — save it?"* Without
> that line on screen the two reads as a repeat and gets rubber-stamped, which defeats the one gate the author cares
> most about. *(Born from a real failure: five records written with no preview, which he called "the skill's
> biggest flaw.")*
> **Why the preview at all:** per SOP Principle 14 this is *"the skill's MOST IMPORTANT output"* — the human
> approves the RECORD, not just the conclusion.

`4.3b` 🧑 **TWO KEYS.** — CORRECTION-LOOP · **GATE** · **human's turn**
> **STEP OUTCOME:** ordinary filing and canon promotion can never be approved by the same act.
> **Does:** one plain yes (or *"1 yes, 2 yes, 3 change to health"*) approves **records + pointers**. **Each
> canon candidate needs its OWN explicit key** — and even then it is written to `records/proposals/` with
> `vetted: false`, **never** to `canon/`.
> ⛔ **Human-elimination invariant.** An ordinary yes may never be read as the permanent one.

## TURN 3 — the machine writes 🤖 ↩

`4.4` **PLACE.** — ITEM-LOOP · data
> **STEP OUTCOME:** every confirmed item exists on disk, in the home the human chose, with a back-pointer to
> the chat it came from — and its fate is recorded in the map.
> **⑂ Route the home:** reuse `archivist-route`; ⚠ carry its self-declared caution — it over-defaults to the
> project's own canon, so distrust its first pick and prefer the folder the human named.
> **⑂ Type-triage:** `finding` (default) · `decision` · `pros-cons` · `snapshot` (with a shelf-life) · the
> pointer form. ⛔ **NEVER** assign `canon`/`rule` — only the human elevates.
> **⑂ DEDUP-FIRST, canon-bound only:** run `canon_conflict_scan.py` BEFORE writing. **NEW → proceed ·
> DUPLICATE → drop it and say so · CONFLICT → surface to the human, never auto-resolve.** The living desk wins
> over a stale ingested snapshot. This is the "first do no harm" wall.
> **⛔ A RECORD GETS A STUB FILE — the original is NEVER moved and NEVER rewritten.** A paragraph or two on
> what is inside, plus a pointer, authored into the destination folder. Only **canon** and **dated** items get
> authored in full. *(the author, three times, most recently 2026-08-08.)*
> **⛔ FINDABILITY INVARIANT — no buried treasure** (§5c C3): anything sunk deep leaves a one-line pointer
> where a future session would naturally look.
> **⛔ THIN UP HIGH, FULL CONTENT ON THE BRANCH YOU ARE IN** (§5c C3) — do not pointer-ize canon that is
> actually loaded.
> **`topic:` comes from the CLOSED vocabulary** (`topic-vocab.md`). ⛔ The skill may not invent a slug; it
> proposes one to the human.
> **Evidence:** the file on disk **AND** the map fate recorded. ⭐ *"ASSERT the output, never report success —
> read the result back and check it"* (organism `manual.md:132-147`).
> **Safe-class carve-out:** the filer writes only dated records + proposals. ⛔ It never auto-executes a
> `CLAUDE.md` edit, a skill edit, a `canon/current.md` or root-canon write, a hard delete, or a contested
> verdict.

`4.5` **THE ROOT CANON — last, one at a time.** — ITEM-LOOP · **GATE** · human's turn
> **STEP OUTCOME:** the human has ruled each root-level candidate individually, knowing what it costs to carry
> it everywhere.
> **Does:** surfaces candidates ONE AT A TIME, each with its carrying cost stated. `/read` chain-walks parent
> canon, so **a line placed at the root is charged to every conversation below it, forever.**
> ⛔ **Canon is NEVER auto-written.** A candidate goes to `records/proposals/` with `vetted: false`.
> ⚠ **STATED WEAKNESS, not hidden:** today's "second key" is a **string match on content the writer itself
> wrote** — *"the actor grading its own homework."* **It is not a gate.**
> ⛔ **And doctrine independently forbids the machine here:** *"the author writes the high-tier bars (global, each
> desk). Those are law; law isn't machine-guessed"* (`intent-doctrine.md:234-235`). ⇒ **root promotion is
> human-only in practice regardless of what the code appears to allow.**
> ⚠ **Four canon guards are looser than they look** (`elements/canon.md:339-375`): `topic:` is required by
> doctrine but **not in the write-time REQUIRED_FIELDS check** · the "write to proposals/" redirect has **no
> mechanical enforcement** · a `cp`/`echo`/`tee` write **bypasses `guard_canon_write.sh` entirely** · an Edit
> that merely STRIPS `authority: user` passes the guard. **Do not lean on them as if they were tight.**

## FINAL TURN — close

`4.6` **Close every pile.** — ONE-PASS · **GATE**
> **STEP OUTCOME:** the corpus is done only when no keeper anywhere is left unfiled.
> **Refuses on:** ⛔ any pile holding an un-closed keeper — the done-gate, *"no gold left behind."*
> **Then:** clear the anchor, and tell the human warmly and plainly what was filed and where, with a clean
> end-count.
> 🐞 **KNOWN CODE DEBT — `[INGEST-FILER-TOKEN-RENAME]`:** `pipeline.py suggest --skill ingest-filer`
> (`4-place.md:238-241`) passes the literal string `ingest-filer` as a **PHASE TOKEN**. The filer stopped being
> a skill on 2026-08-05, but `suggest` still branches on that literal, so passing anything else today takes the
> wrong branch. Rename during the build.

## WHAT THIS PHASE OWES — the build list this spec generates

| # | Item | Size | LAW 8 verdict owed |
|---|---|---|---|
| 1 | **Fix `4-place.md:172`** — it says records are MOVED; they get a STUB | tiny | **FIX** (reality is wrong) |
| 2 | **Knowledge-folder vs desk** — decide, then make `4.2` scaffold the right thing | medium | **needs the author** |
| 3 | **The "you already chose the type; this is the FILE" line on `4.3`** | tiny | **BUILD** |
| 4 | **Pagination on `4.3`** — reuse `2.2`'s batcher | small | **BUILD** |
| 5 | **The findability breadcrumb** on every deep placement (`4.4`) | small | **BUILD** |
| 6 | **The world-model compaction/graduation half** — what leaves the pad once filed (§5c C1) | real work | **BUILD** |
| 7 | **`[INGEST-FILER-TOKEN-RENAME]`** | tiny | **FIX** |
