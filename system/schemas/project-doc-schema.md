# Project Doc Schema

> Canonical shape for a **project doc** (a.k.a. the brief) — the episodic-memory
> "home base" for one project (one slug). Sandbox-proven 2026-06-02 (cold-pickup
> test passed 4/4). Organic shape + a REQUIRED spine; not a rigid template.
> Source of truth that `/save`, `/read`, `/checkin`, and `project-manager` all cite.
>
> **v2 (2026-06-06): a project is now a FOLDER.** See "## v2 — Folder Model" at the
> bottom. v2 changed only WHERE the brief lives (in its project folder, as `brief.md`)
> and that each folder carries a tiny `canon.md` loaded lazily along the path.
> Backward-compatible: flat `state/briefs/{slug}.md` still resolves via the registry.
>
> **v3 (2026-07-13): the history consolidation.** The brief SPINE was redesigned — the
> scattered history sections (DEAD ENDS, ESTABLISHED/WHAT WORKS, DURABLE LOG) collapse into
> ONE append-only **STORY LOG** *(2026-07-17: the standalone ⛔ DON'T-RETRY folded IN; its one-line
> scan now lives in the §2 DECISION BOARD's ⛔ RULED-OUT bucket)*, so a fresh
> session reads the whole arc — tried → outcome → status — in one place instead of
> re-litigating settled work. Backward-compatible + migrate-on-touch (see the Migration note
> at the end of the spine).

## What a project doc IS

- **One per slug, for the project's whole life.** `state/briefs/{slug}.md`
  (desk: `state/projects/{slug}/state/briefs/{slug}.md`). Updated IN PLACE, every save,
  every session. NEVER dated/numbered/duplicated.
- **The distilled "current" face** of the project. The journal is the append-only
  history; this doc is the always-current synthesis that points at everything else.
- **One read = full rehydration.** A cold session opens this one file and knows
  what was tried, what failed, what's established, and what's next.

## Memory-tier vocabulary (industry-aligned)

- **Working** = the live session (volatile) — not a file.
- **Procedural** = skills + CLAUDE.md (how Claude behaves).
- **Episodic** = THIS doc + the journal slice (timeline of what happened/was tried).
- **Semantic** = `canon/` (durable, generalizable observations — human-vetted reliable beliefs), fed upward by `/save`.

Dead-ends live HERE (project-local). Durable, generalizable insights elevate OUT to
semantic (`canon/`) via `/save`.

## Safety model (why one mutable file is safe)

- The brief is overwritten in place. Safety comes from UNDERNEATH, not from copies:
  the **journal** (append-only) is the PRIMARY, actionable backstop + reconstruction
  source. (Google Drive also keeps file revision history, but that is recoverable only
  through the Drive web UI by the human — NOT restorable from within the tool plane,
  so do not rely on it as an automated backstop. The journal is the one a session can act on.)
- **HARD RULE — precious info must hit the journal, never live ONLY in the brief.**
  Anything whose loss would hurt (a dead-end, a decision, a key number) must be in
  an append-only home before/as the brief is rewritten.

## Frontmatter

```yaml
---
id: {desk}-{slug}
slug: {slug}
title: {Display Name}
record_type: project-doc
memory_tier: episodic
desk: {desk}
parent: {parent-slug or —}      # nesting via tag, not folders (optional)
status: active | paused | complete
created_at: {YYYY-MM-DD}
updated_at: {YYYY-MM-DD}
authority: user
---
```

## ⭐ SECTION KINDS — every section is a GAUGE or a LOG (2026-08-06)

> **THE LAW: A GAUGE IS OVERWRITTEN. A LOG IS APPENDED. Writing a gauge like a log is the defect this
> schema exists to prevent.**

| § | section | kind | what that means here |
|---|---|---|---|
| §0 | 🛑 LLM NOTICE | **GAUGE** | fixed text; replaced only if the notice itself changes |
| §1 | FRAME | **GAUGE** ⛔ human-only | one desired outcome. Never machine-edited, never accumulated |
| §2 | CURRENT STATE | **GAUGE** | ONE answer to "where do things stand." See the two verbs in §2 below |
| §4 | STORY LOG | **LOG** | append-only, grows forever, and that is CORRECT. Superseded entries are TAGGED in place, never removed |
| §5 | OPEN LOOPS | **GAUGE** | the live list. A resolved loop LEAVES; it is not annotated in place |
| §6 | KEY RESOURCES | **GAUGE** | current handles only. A dead pointer is deleted, not struck through |
| §7 | SCRATCHPAD | **GAUGE-with-lifecycle** | dumb capture → graduate → CLEAR. The only section with a clearing mechanism (`pad_archive.py`) — and the only one that has never bloated |
| §8 | ARTIFACTS | **LOG** | a record of what was produced; append |

**Why this table exists, measured 2026-08-06.** `<notes>/state/projects/<slug>/brief.md` was found holding
**NINE competing status surfaces** inside §2 — eight hand-written `WHERE WE ARE` blocks plus the three-rung
altitude block — **FOUR of them each declaring "SUPERSEDES EVERY BLOCK ABOVE. READ THIS ONE,"** in
scrambled date order. §2 had reached **762 lines: 45.3% the size of the append-only STORY LOG and 23.4% of
the entire 3,251-line brief.** A blind session — the audience every brief is written for — got nine answers
to one question.

⭐ **THE ROOT CAUSE IS NOT DISCIPLINE.** Every gauge in this system with a **MECHANISM** stayed sharp;
every gauge with only **PROSE** went dull. §7 has `pad_archive.py` and runs 2 lines. §2 had one sentence of
instruction and ran 762. The `/save` handoff had three successive prose word-caps and **failed all three**
until the prose was replaced by a form. **Same failure, three surfaces, one variable: whether anything
counts.**

## REQUIRED spine (in this order — read-first sections up top; the history is ONE chronological log)

### 0. 🛑 LLM NOTICE  *(the VERY FIRST lines of every brief — verbatim, immediately below the frontmatter, above FRAME)*
Every brief opens with this notice — the "fine china" guard (2026-07-17). It is written into every new brief (project-manager create template) and backfilled into all existing briefs:
> 🛑 **LLM NOTICE — READ FIRST.** This brief is high-value, human-in-the-loop, VERIFIED knowledge — the *fine china* of the system. Operate with extreme care: prefer append over rewrite, never condense or "improve" settled content, and treat the DESIRED OUTCOME (§1) as read-only. When unsure, ASK the human — do not edit.

### 1. FRAME  *(why this exists / definition of done — the stable anchor)*
> ⚠ **HUMAN-IN-THE-LOOP APPROVAL REQUIRED TO CHANGE.** Human-authored, human-only. Do NOT override, rewrite, condense, or "improve" this desired outcome without EXPLICIT human approval in-session. LLMs treat this section as READ-ONLY.

Desired outcome, success criteria, constraints, scope edges. Each labeled
`CONFIRMED` / `WAIVED` / `INFERRED`. **Human-only — confirmed with the user, never guessed, never
machine-edited** (in the brief OR the plan).
> **THE DESIRED OUTCOME *IS* THIS PROJECT'S 10,000-FOOT VIEW** (`system/work-altitude-doctrine.md`). That
> doctrine reads the top rung off this line — so write it as a destination, not a task list. ⚠ It is the
> project's 10k, not always the *session's*: a standing goal can sit ABOVE every brief (*"we're fixing this
> skill because we want a machine that builds better skills"*), and that outranks this line when it applies.
> **This FRAME *is* the project's declared INTENT** (⏳ **UNRULED** — the parent law
> `system/intent-doctrine.md` is on no ship list; the rule it supplies is the next clause): a project is a BOUNDED
> object, so its intent is a **DESIRED OUTCOME** (a definition-of-done), not a standing PURPOSE. A brief with no
> confirmed desired outcome is an object missing its intent — the archivist flags it (check O / check P).

### 2. CURRENT STATE — the DECISION BOARD  *(the live status of every granular decision)*
The scoreboard a fresh session reads to know where each decision stands RIGHT NOW — so it never re-suggests
something already settled or killed.

**OPENS WITH THE THREE-ALTITUDE READ (REQUIRED, 2026-08-05 — replaces the old "1–3 lines of live status +
the very next action").** Same three rungs as `system/work-altitude-doctrine.md`, but ⭐ **▲10,000 is not
re-derived here — it is a faithful restatement of §1's desired outcome, human-authored and human-only. A
session may print it or flag it stale against §1; it may never rewrite it, append to it, or dress it in
position/status language.** Position, status and measurement live at the two rungs beneath it, zoomed two
ways:

    ▲ 10,000 — §1's desired outcome, restated (human-authored; a session prints or flags-stale, never rewrites)
    ▲  5,000 — the Phase ▸ Feature / seam / learning we are inside right now
    ▲ ground — what was last worked on, dated, with an explicit "re-verify before acting on this" note — never phrased as an instruction, since the next reader may arrive after it has gone stale

> ## ⭐⭐ §2 HAS TWO VERBS AND THEY MUST NEVER BE CONFUSED (the operator, 2026-08-06)
>
> ### VERB A — ▲5,000 AND ▲GROUND ARE **OVERWRITTEN**. THE OLD READING IS **DELETED**.
> The session re-derives ▲5,000 and ▲ground at pickup and **replaces** the previous text outright.
> ⛔ **▲10,000 is exempt from Verb A.** It is human-authored, not derived — a session prints it as-is and
> may flag it stale against §1, but never re-derives, rewrites or replaces it.
> **NOT archived. NOT graduated to the STORY LOG. NOT compacted. NOT an input to compaction.**
> ⛔ **NEVER WIRE COMPACTION TO THIS BLOCK.**
>
> **Why that would actively harm, not merely waste effort:** compaction's verb is *graduate-then-delete* —
> it PRESERVES content by moving it. Pointed at a gauge, **every superseded altitude reading would be
> pumped into the append-only STORY LOG, making the record duller with each pickup** — the exact inverse
> of what this schema is for. **A stale gauge reading has no archival value.** A speedometer does not keep
> a log of every speed you have driven. There is nothing to lose here, so there is nothing to protect:
> **no archive, no receipt, no gate.**
>
> ### VERB B — EVERYTHING ELSE IN §2 IS **UPDATE → AUDIT → COMPACT**, IN THAT ORDER.
> The decision boards (✅ LOCKED / ⛔ RULED-OUT / ❓ OPEN) and any cumulative prose:
> 1. **UPDATE** — bring each item current against what this session actually did.
> 2. **AUDIT** — check the updated board against itself and against the STORY LOG: a ✅ LOCKED item that a
>    ⛔ RULED-OUT line contradicts · an ❓ OPEN item the Story Log says is closed · a number corrected
>    elsewhere and stale here.
> 3. **COMPACT** — only now graduate what is settled out to the STORY LOG / OPEN LOOPS / KEY RESOURCES,
>    through the existing archive-first receipt gate (see "BRIEF COMPACTION" below — that routing table is
>    referenced, never duplicated).
>
> ⚠ **THE ORDER IS LOAD-BEARING. Compacting FIRST graduates STALE content into an append-only log you
> then cannot correct** — the STORY LOG is append-only by design, so a wrong entry graduated there is
> permanent. **Update makes it true, audit proves it, compaction moves it. Never reorder these.**
>
> ⛔ **NEITHER VERB IS A NEW ENGINE.** The compaction machinery already exists and is proven
> (`pad_archive.py` + the routing table below). Verb B AIMS it at a second section; **it does not rebuild
> it.** ⛔ **And the code has no judgment:** `pad_archive.py` calls itself *"the deterministic safety
> core"* — it copies, reads back, prints a receipt. **The session does all the sorting, in both verbs.**
> The mechanism is not a smarter sorter — **it is a rule the session cannot skip without leaving
> evidence.**
>
> ## ⛔ §2 HOLDS ONLY NAMED SLOTS. FREE PROSE IS OVERFLOW, BY DEFINITION. (2026-08-06)
>
> **The complete legal contents of §2 — nothing else belongs:**
> 1. **The three-rung altitude block** (`▲ 10,000` · `▲ 5,000` · `▲ ground`) — ▲5,000/▲ground overwritten
>    by verb A; ▲10,000 printed or flagged stale only, never overwritten.
> 2. **The three decision-board buckets** — `✅ LOCKED` · `⛔ RULED-OUT` · `❓ OPEN` — verb B.
>
> **Anything else in §2 is OVERFLOW and routes out** per verb B's compaction — to the STORY LOG, OPEN
> LOOPS, or KEY RESOURCES. Not "should probably route out." **Is overflow, definitionally.**
>
> ⭐ **This rule exists to make the question mechanically answerable.** *"Does this paragraph belong in
> §2?"* is a judgment call, and a judgment call cannot be enforced — it can only be asked nicely, which is
> what produced 762 lines. **"Is this one of the named slots?"* is a lookup.** That is the difference
> between a rule a tool can check and a rule that decays. Without this line, `gauge_check.py` would have
> to decide what a block MEANS, which is exactly the judgment the code must never hold.
>
> **Size ceiling (the thing neither verb imposes on its own):** §2 ≤ **120 lines** AND ≤ **25%** of that
> brief's STORY LOG. *(Measured 2026-08-06: a healthy §2 is 35 lines; the pathological one was 762 lines
> = 45.3% of its Story Log. 120 leaves ~3.4× headroom over healthy.)* Verb A stops the gauge going stale
> and verb B stops content accumulating — **but only the ceiling stops §2 growing without bound.**
>
> ## ⛔ EXACTLY ONE STATUS SURFACE. REPLACE IT. NEVER APPEND A SECOND. (2026-08-05)
>
> **This three-rung block is a GAUGE, not a LOG.** A gauge has one current value and you overwrite it.
> A log accretes. **You UPDATE this block in place. You NEVER add a second status block, under any
> heading, anywhere in §2** — not `WHERE WE ARE`, not `STATUS`, not "the previous one might still be
> useful." If the block is stale, FIX IT. If you cannot tell whether it's stale, say so IN the block.
>
> **Measured 2026-08-06 in `<notes>/state/projects/<slug>/brief.md`:** §2 had grown to **741 lines of a
> 3,177-line brief (23%)** holding **NINE competing status surfaces** — eight hand-written `WHERE WE ARE`
> blocks plus this one. **FOUR of them each declared "SUPERSEDES EVERY BLOCK ABOVE. READ THIS ONE,"** and
> they sat in scrambled date order (08-05, 08-04, 08-04, 07-29, 08-01, 08-01, 08-02, 08-03). **The
> audience for a brief is a blind session with zero context, and that reader got nine answers to one
> question.** Nothing wrote them mechanically — eight sessions each added one by hand, which is why the
> rule has to be stated: appending felt safer than overwriting, every single time.
>
> **A second status surface is a DEFECT — clean it up on touch, graduate-then-delete:** for each extra
> block, oldest first, append anything not already in the STORY LOG / OPEN LOOPS to the STORY LOG
> (append-only) and journal-first anything precious — **only then remove it. NEVER delete first**; those
> blocks may hold the sole copy of a measured number or a ruling.

> ## ⭐ RUNG SHAPE — ONE TO TWO SENTENCES EACH. HARD CAP. (the operator, 2026-08-06)
>
> **A rung is a READING, not a paragraph.** One to two sentences, per rung, always.
> - **▲ 10,000** — §1's desired outcome, restated. Human-authored; a session prints it or flags it stale,
>   never composes it.
> - **▲ 5,000** — which part of the plan this sits inside.
> - **▲ ground** — what was last worked on and when, plus anything NOT built — dated, carrying its own
>   re-verify instruction, never phrased as a next action.
>
> **Still blind-reader legible** — every proper noun gets a clause explaining what it is, full
> sentences, no fragments. **Short is not terse.**
>
> **Anything longer belongs in the decision boards or the STORY LOG** — which is what verb B's
> graduation is for. ⚠ **Measured 2026-08-06, on the brief of the project that built this rule:** a
> paragraph-per-rung block ran §2 to **50% of its Story Log**, and **the altitude block was most of
> it.** Normalising to this shape took §2 from **55 → 25 lines** in one edit. **A bloated gauge is
> the disease this schema exists to cure; writing one inside the fix is how it survives.**

**Rules:** a. **▲10,000 is a restatement, never a position** — it is a faithful copy of §1's desired
outcome, human-authored and human-only. A session may PRINT it and may FLAG it as looking stale against
§1; it may never rewrite it, append to it, or dress it in position/status/measurement language. Position,
status and measurement belong at ▲5,000 and ▲ground only. b. **Read, don't compose** — the 5,000 comes
from the live plan, quoted; a rung written from memory is not a rung. c. **A rung with no honest answer
says so** (`no larger frame` / `no plan armed`) — never invent one to fill the space; the doctrine's
`NO-FRAME` is a correct answer, and a fabricated rung reads exactly like a real one, which trains the
reader to skim the block. d. **▲5,000 and ▲ground are machine-maintained** — rewritten every compaction,
the only two rungs a session may write without asking. ▲10,000 is not machine-maintained: it is human
territory, present in this block only to be printed or flagged, exactly like §1.

Then three buckets, **maintained by compaction off the STORY LOG (§4)**:
- **✅ LOCKED** — decided + in force now (the current approach).
- **⛔ RULED-OUT** — tried/considered → killed. A one-line `⛔ {what} → {why}` + a pointer to its STORY LOG entry.
  *(This bucket is the fast "do-NOT-retry" scan — it replaces the old standalone §3 Don't-Retry section.)*
- **❓ OPEN** — still under discussion / unresolved (a fresh session must NOT treat these as settled).

**"Promoted"** = an item moves INTO ✅ LOCKED; **"demoted"** = it moves to ⛔ RULED-OUT or back to ❓ OPEN.
**3 states only** — promoted/demoted are transitions, not extra buckets. The board is the scoreboard; the
STORY LOG (§4) is the play-by-play. This is the END of the STORY LOG, made scannable. **Why it exists:** LLMs
hold the broad strokes but lose which *version* is locked / killed / still-open across a long back-and-forth —
the board pins that granular status so it can't be lost.

### 3. ⛔ DON'T-RETRY — RETIRED (folded 2026-07-17)
> **This standalone section is retired.** Its two jobs are now split cleaner: the **fast "do-NOT-retry" scan**
> lives in the **§2 DECISION BOARD → ⛔ RULED-OUT bucket**, and the **full dead-end story (with its why)** lives
> in the **§4 STORY LOG**. Reason (from the project-system audit): a separate hand-maintained rail *rots* when
> nothing keeps it current, and a bare "⛔ don't do X" invites re-litigation — the *why* is what actually stops a
> re-tread, and the why lives in the Story Log. New briefs do NOT carry a §3; existing briefs drop it on their
> next normalization (dead-ends → STORY LOG + the RULED-OUT bucket, nothing lost).

### 4. STORY LOG  *(REQUIRED — the chronological, APPEND-ONLY history of the build)*
> **The seam (SETTLED → here):** a decision a future session must NEVER re-litigate is **SETTLED** — it
> belongs in the STORY LOG. A live thought / a maybe is **WORKING** — it stays in the SCRATCHPAD (§7).
> Everything starts in the scratchpad and **GRADUATES** to the Story Log the moment it's confirmed.

The one place the whole arc lives, in order: *first we tried X → it failed; then Y → worked; then Z →
partial; now here.* A fresh session reads this top-to-bottom and knows the project's history — low
resolution, but complete. **This is now the SINGLE chronological home** — it holds decisions, **wins**, twists,
AND every dead-end / demoted / stale path, each WITH its why (the retired §3 Don't-Retry folded IN here; the
§2 ⛔ RULED-OUT bucket keeps only the one-line scan of them). **PRESERVE EVERY DEAD-END** — a missing dead-end
is exactly what makes a fresh session re-suggest a killed idea (keep-everything bias). Each entry's STATUS is
what the §2 DECISION BOARD reads to place it (`locked` → ✅, `superseded/killed` → ⛔, `open` → ❓).
- **One entry per real move (a decision, an attempt, a pivot), OLDEST-first, newest appended at the bottom:**
  `{when} — {tried / decided X} → {outcome: worked | failed | partial} → STATUS: {locked | superseded-by:<entry> | open} → {why / lesson}`
- **APPEND-ONLY — never drop or rewrite an entry.** A decision that gets overtaken is marked
  `superseded-by:<later entry>`, NOT deleted — the supersession chain is the whole point (it's what stops
  re-litigation and shows HOW you got here). You may compress an entry's PROSE, never remove the entry.
- **Low-resolution on purpose** — the arc and the outcome, not every detail; the journal holds full receipts.
- **STATUS vocabulary:** `locked` (decided + still holds) · `superseded-by:<entry>` (overtaken — the newer
  entry wins, both stay visible) · `open` (raised but never actually resolved — a fresh session must NOT
  treat it as settled). Getting STATUS right is the anti-re-litigation feature; when unsure, mark `open`.
- **★ AN EVENT THAT CORRECTS A STALE NUMBER DOES NOT CLOSE THE WORK.** "Nine promote blocks" corrected to
  "three" still left the three unapplied; "86 uncommitted files" corrected to "73" still left the 73
  uncommitted. A correction FEELS like a resolution — striking a wrong figure produces the same
  satisfaction as completing the task — so the label reads as *handled* and nobody re-opens it. **How to
  apply:** when correcting a count, state the WORK STATUS separately and explicitly in the same edit —
  *"nine → three, and all three remain unapplied"* is a status; *"nine → three"* alone is just a number.
  Never let the corrected figure stand in for the status.

### 5. OPEN LOOPS / NEXT ACTIONS
Live unresolved items + concrete next moves. **Each item carries a definition-of-done** (what "resolved"
looks like) — not just a label. For an `UNKNOWN`, state **what would resolve it** (the check to run, the
file to read). ("TODO: backfill Credits from confirmed-booking rows in [sheet] — done when each booking has
a Credits row" — not bare "TODO Credits backfill".)

### 6. KEY RESOURCES / IDS  *(REQUIRED — the live handles to ACT)*
The live handles a session needs to *act*, not just understand: Sheet IDs / URLs, DB tables, label IDs,
tool paths, calendar IDs, key file paths. A doc can explain a project perfectly yet be useless if the
session can't find the actual ledger.

### 7. SCRATCHPAD  *(the fixed working-notes surface — a dumb capture dump; graduated + cleared automatically at each compaction)*
> **The seam (WORKING lives here):** the scratchpad holds **WORKING** material — live thoughts, maybes,
> in-progress reasoning. The moment something is **SETTLED** (a decision a future session must never
> re-litigate) it **GRADUATES** to the STORY LOG (§4). Start everything here; graduate the keepers.

The session's live working notes: in-progress reasoning, intermediate outputs, half-formed ideas, and the
pointer to the active plan-mode plan. **Fixed section so any session — even stale/compacted — finds it by
"check the scratchpad": the brief auto-injects every turn (via `pm_persist.sh`), so the user never has to
remember a scratch-file name.** For big content that won't fit inline, store a POINTER (name + path),
never the content.
**DUMB CAPTURE surface — GRADUATE-then-CLEAR (2026-07-17; supersedes the 2026-07-15 "never-wiped" model).**
The scratchpad is where notes land as work happens — a dumb dump, no classifying at capture time. At each
**COMPACTION** (fired by `/save` alone, at session close — see "BRIEF COMPACTION" below; `/checkin` no longer
compacts, 2026-08-03), its NEW content is sorted into
the durable sections (a decision → STORY LOG + the §2 board; a dead-end/demoted/stale item → STORY LOG + the
§2 ⛔ RULED-OUT bucket; a resource → KEY RESOURCES; an open thread → OPEN LOOPS), and the graduated items are
then **CLEARED from the pad** — AUTOMATICALLY (no approval gate, no skip), the only precondition being that the
WHOLE pad was first appended to the append-only `{brief}.pad-archive.md` AND read-back-verified (via
`pad_archive.py`), so **nothing is ever lost silently** — a clear without a fresh archive receipt is forbidden
(fail-closed). Unresolved / very recent items stay on the pad.
The compaction is **incremental** — it only processes the NEW delta, so it's cheap when little was added.
*(This reverses the old "never wipe / duplicate-up-leave-intact" rule AND the 2026-07-17 approval gate — 2026-07-19: an approval that defaulted to skip meant the pad never compacted; the verbatim backup + append-only Story Log + untouched FRAME make automatic clearing safe.)*

### 8. ARTIFACTS
Key records (`records/{type}/...`) and important files, by path.

### + CHRONICLE POINTER  *(footer — one line, not a numbered section)*
The append-only substrate is `system/journal.md`, entries tagged `| {slug} |` — the full receipts under
the distilled STORY LOG. Pointed to, never copied. **Journal-first stays HARD:** precious info (a decision,
a dead-end, a key number) hits the journal before/as the brief is overwritten.

## ⭐ WHO DOES WHAT: `/checkin` DETECTS · `/save` CORRECTS (2026-08-06)

> **`/checkin` = THE AUDIT.** Diffs plan vs brief vs session, runs `gauge_check.py`, REPORTS the counts,
> and OVERWRITES the altitude block (verb A — no archive needed, nothing to lose). It proposes; the human
> approves once.
>
> **`/save` = PERSISTENCE.** Copy, verify, file. It keeps verb B's compaction with its receipt gate. **It
> makes no judgment about whether the filing was any good.**
>
> ⛔ **DO NOT MOVE THE COMPACTION ENGINE INTO `/checkin`, AND DO NOT BUILD A SECOND ONE.** *(the operator,
> 2026-08-06: "I just want to make sure we're not double building a compaction that we already built.")*
> An earlier draft of this rule read *"trigger at `/checkin`, not `/save`"*, which reads as relocating the
> engine. **It was wrong. The engine stays exactly where it is.**
>
> **The real gap was never LOCATION — it was SEQUENCE.** Compaction was deliberately removed from
> `/checkin` on 2026-08-03 because a cold pickup could fire it at session **launch** and clear the pad
> before the operator had read it — a correct fix for a real bug. But the consequence is that in the order
> the operator actually works (**`/checkin` … then `/save`**), **nothing inspects §2 at the FRONT.** It is
> only ever touched at the end, when context is exhausted and expensive steps get dropped — measured
> 2026-08-02: a session at ~719k skipped compaction entirely and stamped the ledger as if it had run.
> ⇒ **Detection at the front, where the operator actually is. Correction at the back, where the safe
> machinery already lives.**

## BRIEF COMPACTION — the `/save` procedure (2026-07-20 · AUTOMATIC + LOSSLESS + SELF-HEALING; `/checkin` compaction removed 2026-08-03)
> The SINGLE source of truth for how a brief is compacted. **`/save` (session-close) runs this, and only `/save`.**
> `/checkin` used to also run this same procedure on every re-orient (the 2026-07-20 model below) — that
> co-ownership is RETIRED (2026-08-03, the operator's ruling: "take compaction out of `/checkin` completely").
> Check-in had no session-close gate on its copy, so it could fire at session **launch** on a cold pickup and
> clear the pad before the operator had read his own orientation material — a real, live failure. Compaction now
> lives ENTIRELY in `/save`, gated on session-close mode; `/checkin` only harvests to the scratchpad and
> appends confirmed decisions (its own Step 3.6) — compaction itself is defined HERE and nowhere else.
> **AUTOMATIC:** it ALWAYS runs when a brief with real
> `## SCRATCHPAD` content is active — NO skip, NO "let it ride," NO approval gate. (The 2026-07-17 approval gate
> defaulted to skip, so the pad never compacted and grew unbounded — the silent-deferral this feature exists to
> kill.) **LOSSLESS by construction:** nothing leaves the pad except through an APPEND-ONLY archive that is
> written and READ-BACK-VERIFIED *before* anything is cleared, so a mis-sort can never lose data. **SELF-HEALING:**
> a completeness pass re-checks that durable knowledge actually landed in the STORY LOG and WRITES IN anything
> that didn't. **Twice-a-session + crown-jewel payload → COST IS IRRELEVANT; buy certainty, not speed**
> (the operator 2026-07-20). Design converged with the architecture council (2026-07-20). The heavy whole-brief re-sort,
> when built, folds into THIS same automatic path — NEVER a separate manual button ("everything is built into the save").

**Steps (strict order — the safety steps GATE the destructive ones):**

1. **COPY-EVERYTHING-FIRST → the append-only archive (the mechanical net).** Call the deterministic safety core:
   `python3 <this repo>/system/tools/save/pad_archive.py archive "<abs_brief_path>"`. It appends the ENTIRE
   current `## SCRATCHPAD` verbatim (everything — NO choreography carve-out) to `<brief>.pad-archive.md`
   (append-only, chained, self-describing: `compaction #N · ISO-ts · host · prev-hash · hash`), reads it back to
   prove it landed, and prints `RECEIPT <hash>` on **exit 0**. Idempotent (unchanged pad → no duplicate block).
   **Then run `pad_archive.py verify "<abs_brief_path>"`** (chain + counter integrity). Exit 0 = intact; a NONZERO
   exit means a broken prev-hash chain or a missing compaction (# gap) = tamper or a lost block → surface a loud
   `⚠ ARCHIVE INTEGRITY` note to the user. This does NOT block the current compaction (this run's block is safe) —
   it flags HISTORICAL corruption to investigate.
2. **RECEIPT-GATE (fail-closed).** The clear in step 5 is FORBIDDEN unless step 1 returned **exit 0 + a RECEIPT
   this run**. If the script is not called, errors, or exits non-zero → **DO NOT CLEAR**; write a loud
   `> ⚠ COMPACTION ABORTED {ts} — archive not confirmed; pad left intact` line at the TOP of `## SCRATCHPAD` and
   surface it to the user. "Not archived = not cleared" — silent-loss is structurally impossible.
3. **CLASSIFY + GRADUATE each item** into the durable sections (this is the model-judgment step; it is now
   *decoupled* from safety — a wrong call is caught in step 6, never lost):
   - settled decision / **win** → STORY LOG (`STATUS: locked`) + board **✅ LOCKED**; refresh the live-status line.
   - dead-end / demoted / stale (incl. an item the new note supersedes) → STORY LOG (`STATUS: superseded/killed`,
     WITH the why) + board **⛔ RULED-OUT** (one-line + pointer). **PRESERVE every dead-end.**
   - open thread → OPEN LOOPS (§5) + board **❓ OPEN**.  · new resource / path / ID → KEY RESOURCES (§6).
   - pure choreography with no lasting lesson → drop (it is safe in the archive from step 1).
4. **Journal-first** for precious keepers (decision / dead-end / number) → `system/journal.md` before/as the brief
   is rewritten.
5. **CLEAR (only with a fresh receipt).** Remove the graduated items from `## SCRATCHPAD` (leave unresolved/recent).
   **NEVER touch §0 / §1 FRAME content.**
6. **SELF-HEALING completeness diff (the "nothing buried" layer).** For each item just cleared: first a mechanical
   pre-filter (does its text appear in the STORY LOG?) to skip the obvious hits cheaply; then, for the residual,
   judge **BY MEANING** whether its durable substance actually landed (reworded ≠ missing). **If a durable item did
   NOT land → WRITE IT INTO the STORY LOG now** (self-heal — do not merely flag). Anything you do flag lands in
   OPEN LOOPS (§5), never a silent log line.
7. **INDEPENDENT SECOND-PASS audit (option B — the second mind).** Spawn ONE isolated **sonnet** subagent (read-only)
   that compares THIS compaction's archive block (`<brief>.pad-archive.md`, newest block) against the durable
   sections and returns any durable item not represented. The main session WRITES any confirmed miss into the
   STORY LOG. Once-a-session, cheap insurance for crown-jewel knowledge.
8. **Print the receipt:** `📝 Compaction: Story Log +{S} · board ✅{L}/⛔{K}/❓{J} · dropped {D} · self-healed {H} ·
   2nd-pass recovered {R} · archive #{N}`. Restore path (one line): *open `<brief>.pad-archive.md`, find the block
   for the date / highest `compaction #N`, copy notes back.*

**Guardrails (HARD):**
- **Archive-then-verify is mandatory before ANY clear; approval is NOT** (2026-07-20). No `RECEIPT`/exit-0 from
  `pad_archive.py` = no clear (hard stop, fail-closed). The append-only verified archive + append-only Story Log +
  untouched FRAME + the self-healing diff are the fine-china guarantee that replaces the old approval gate.
- **STORY LOG is append-only** — never rewrite/delete an existing entry (a superseded one is marked in place).
- **FRAME (§1) content is human-only** — compaction never edits it.
- **The archive (`<brief>.pad-archive.md`) is append-only + chained** — never rewrite/truncate it; a `prev`-hash
  gap or counter gap means a compaction was lost or the file was tampered → surface it.

## Migration (old 10-section briefs → this v3 shape)
Backward-compatible + **migrate-on-touch**. An un-migrated brief (with DEAD ENDS / ESTABLISHED / DURABLE
LOG / a standalone §3 DON'T-RETRY) still parses and resolves — nothing breaks. The NEXT time a session
materially writes that brief (`/save` compaction, `project-manager` maintenance, or a backfill), it converts:
**DEAD ENDS / DON'T-RETRY → STORY LOG** (the failure narrative, WITH each why) **+ the §2 ⛔ RULED-OUT bucket**
(the one-line scan); **ESTABLISHED/WHAT-WORKS + DURABLE LOG → STORY LOG** entries; **CURRENT STATE → the §2
DECISION BOARD**. No entry is lost in the conversion; when unsure of an entry's STATUS, mark it `open`, never
guess `locked`.

## Confidence labels
`CONFIRMED` · `INFERRED` · `HYPOTHESIS` · `UNKNOWN` · `DEPRECATED` · `ACTIVE` · `TODO`

## The cold-pickup test (the bar this schema must clear)
A fresh session given ONLY this doc can state, unprompted, by reading the **STORY LOG** as a
chronological arc: what was tried, what failed and why, what worked, and where we landed — with the
dead-ends genuinely present in the STORY LOG (not just milestone headlines) + scannable in the §2 ⛔ RULED-OUT
bucket, and every superseded decision still visible with its supersession, so nothing settled gets re-litigated.

---

# v2 — Folder Model (2026-06-06)

> A project is a FOLDER. Knowledge is organized as a SHALLOW folder hierarchy, with a
> tiny `canon.md` at each level loaded LAZILY along the path you touch. This solves the
> two pains the flat-slug system couldn't: (a) "where does this save go?" (the folder
> answers it) and (b) "a desk's whole canon floods every session" (only the canon on
> your branch loads). Design + evidence: `state/briefs/knowledge-architecture/`.

## The structure

```
state/projects/{slug}/
  canon/                      ← desk-wide canon (existing; injected by default)
  state/                      ← desk state (existing)
  records/{type}/             ← desk-wide records (existing; backward-compat home)
  sources/inbox/              ← intake (existing)
  projects/                   ← NEW: container for this desk's project folders
    {slug}/
      brief.md                ← the project doc (schema spine above). MOVED here from state/briefs/{slug}.md
      canon.md                ← NEW: tiny, always-true-at-this-level facts. PROPOSED not auto-written.
      records/                ← this project's records (optional; type-subfolders allowed)
      {work files}            ← loose
      {sub-project}/          ← OPTIONAL deeper level (e.g. state/projects/coaching/a-client/)
                                only where a real practice→client structure exists. DEPTH CAP: 3 below desk.
```

Root-level projects (no desk) live at `state/projects/{slug}/` with the same shape.

## The rules (KISS)

1. **Project = folder.** One folder per registered slug. Its `brief.md` is the project doc.
2. **Depth cap (the one hard rule):** `desk → practice → client`, files below. 2 folder
   levels below the desk's `projects/`, 3 absolute max. **Phases live in the brief, never
   as folders.** An archivist check flags depth > cap.
3. **`canon.md` per folder = always-true-HERE facts, each SELF-EXPLANATORY.** Every line must pass the standalone test (a cold, zero-context session fully understands it alone); always-on canon is also efficient, scoped canon may be richer. Canon is
   **PROPOSED, never auto-written** — a human approves each line. Bloat is the existential
   risk; the path-load tax + densify-in-place + the promotion test are the forcing functions.
4. **Canon loads LAZILY by path.** When `/read` loads a file at
   `desks/d/projects/practice/client/X.md`, it ALSO loads `client/canon.md` +
   `practice/canon.md` + the desk's `canon/` — the canon ALONG THE BRANCH — and SKIPS
   everything off-branch. Mechanical step in `/read`, NOT a frontmatter instruction, NOT
   eager-full-chain-on-every-read.
5. **Slug = identity; the registry maps slug → folder path.** Folders can move; slug
   references don't break. The registry is the resolver and the controlled vocabulary.
6. **`scope:` frontmatter = the cross-cutting JOIN layer.** For the minority of notes
   true in two branches at once: `scope: [other-slug]`. Value MUST be a registered slug.
   One canonical home + findable from each scope. Folders divide; tags join.
7. **Promotion = a lesson graduates UP the canon ladder** (`client → practice → desk`) to
   the level where it reliably holds. Gate: "would this hold for a future DIFFERENT case
   as a generalizable observation, without the backstory?" If not → it stays a record.

## Frontmatter additions (v2)

```yaml
parent: {parent-slug or —}     # the containing project, if nested (was already optional)
scope: [slug, ...]             # cross-cutting: other registered slugs this note also serves
path: state/projects/{slug}/projects/{slug}    # OPTIONAL cache of the registry path; registry is source of truth
```
Backward-compat: these are additive. A doc without them still validates.

## canon.md shape (precise + self-explanatory by design)

```yaml
---
canon_level: {desk|practice|client}
slug: {slug}
updated_at: {YYYY-MM-DD}
authority: user        # canon is human-approved; never machine-written
---
# {Name} — Canon (always true here)
- {one durable observation or fact, one line}
```
If a project has no durable always-true facts yet, `canon.md` may be a header-only stub.
Empty canon is fine; bloated canon is the failure.

## Backward-compatibility contract (the safety invariant)

Until a project is migrated, its brief stays at `state/briefs/{slug}.md` (or
`state/projects/{slug}/state/briefs/{slug}.md`). `/read`, `/save`, `/checkin` resolve a slug
via the **registry path** if present, else fall back to the legacy `state/briefs/`
location. This means a partial migration NEVER breaks the live system — both shapes
resolve. Hard rules (auth, calendar, write-gates) remain in HOOKS, not canon.
