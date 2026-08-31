---
element: council-engine
title: "council-engine — element detail (ground/base altitude)"
subsystem: decision-support
altitude: base
record_type: organism-element
maturity_label: LIVE·gap
gap_disposition: by-design
gap_disposition_note: "ruled 2026-07-28 at class level — C2 honor-caller throughout; the model-pin guard was deliberately parked as over-build for a single-operator system"
generated_from:
  - skills/advisory-council/SKILL.md
  - skills/advisory-council/SCOPE.md
  - skills/council/SKILL.md
  - skills/planning-weekly/prompts/04-council.md
  - skills/planning-weekly/prompts/council/_member-format.md
  - skills/marc-checkin/SKILL.md (lines 79–87)
  - system/sops/architecture-planning-sop.md (lines 59–104, 139)
  - system/hooks/plan_flag.sh (lines 94–96)
  - $DRIVE/councils/registry.md
created_at: 2026-07-24
updated_at: 2026-07-24
status: draft
authority: user
---

# council-engine — element detail

> **Altitude = BASE (ground / street view).** Full mechanics of the advisory-council + council pair —
> every trigger, every protocol step, the fixed advisor schema, the model-selection exception, the
> roster-library structure, and every interop seam. The MIDDLE index (`system/organism/manual.md`)
> carries only a pointer here; the TIP shows only a box + arrows; the **skills themselves**
> (`skills/advisory-council/SKILL.md`, `skills/council/SKILL.md`) are the executable ground truth.
> This entry is the UNDERSTANDING layer.
>
> **One-line:** two skills sharing one blind-diverge → argue → converge protocol — `/advisory-council`
> runs a swappable roster cartridge (any subject, any desk), `/council` runs the five named desk lenses
> (cross-life decisions only). The engine is fixed; the advisors are the cartridge.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory script) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause)

> **LADDER: ELEMENT (full mechanics). up → manual#council-engine ; ground truth → the live artifacts
> (skills/advisory-council/SKILL.md · skills/council/SKILL.md)**

> **CITATIONS — what the paths below resolve to here.** This element describes the donor system truthfully; the two lines below record what happened to each named file at THIS destination, and they cover every mention of them in the body.
>
> ⛔ `state/current.md` — runtime-generated, created on first run, never committed. It is the reader's own where-things-stand file, written by /save into their notes folder (docs/data-layout.md line 237). Absent from a fresh checkout is CORRECT.
>
> ⛔ `councils/*/council.md` — never ships: a roster cartridge is the reader's own, written by the /advisory-council Builder into `<notes>/councils/<slug>/council.md` (.claude/skills/advisory-council/SKILL.md line 192: *"⛔ never ships — they are yours to write"*); the shipped seed is .claude/skills/advisory-council/example-council.md.
> ⛔ `councils/market-analysis/council.md` — same reason: never ships. The market-analysis cartridge additionally belonged to marc-checkin, which is ⛔ excluded from the migration — desk.

---

## AUTHORED   (human-only)

---

### THE TWO SKILLS — WHEN TO USE WHICH

The most load-bearing seam in the whole element:

| | `/advisory-council` | `/council` |
|---|---|---|
| **Roster** | User-built cartridge (`councils/<slug>/council.md`) — any subject, swappable | Dynamic — the subject folders discovered under `$NOTES/desks/` at runtime, each folder's `canon/purpose.md` supplying its lens; no fixed roster ships |
| **When** | A decision with a known subject area where you have (or want) a saved council; OR building a new one | A cross-desk life decision touching money, career, time, location — 2+ life domains |
| **Trigger phrase** | `/advisory-council`, "convene my X council", "advisory board", "what would my advisors say" | `/council [question]`, "convene the council", "debate this across desks" |
| **Protocol** | Full 4-stage chaired session (Frame → Diverge → Argue → Converge/Land); human chairs every transition; loops freely | 4-step dispatch (Desk Selection → Parallel Dispatch → Collect Positions → Synthesis); orchestrator drives; synthesis is the product |
| **Model** | Advisors: **opus** (sanctioned exception) unless the council's own charter pins otherwise (market-analysis = sonnet on cost) | Subagents: **sonnet** (hard pin, no exceptions — SKILL.md "R-1") |
| **Subagent source** | Each advisor block from the council cartridge | Each subagent loads only its own desk canon + `state/current.md` |
| **Library** | `$DRIVE/councils/<slug>/council.md`; central registry at `$DRIVE/councils/registry.md` | No library — desk structure IS the roster |
| **Persistence** | Output → `/save` → Archivist routes; council file never written with session findings | Output → analysis only; read-only; actions route to owning desk |
| **Chaired?** | YES — nothing auto-advances; chair holds the gavel at every seam | NO — orchestrator drives; no interactive gate per round |

**The rule of thumb (from SCOPE.md §1 and SKILL.md):** `/advisory-council` is the **generalization** of `/council` — it
lifts `/council`'s pattern from the fixed desk roster to an arbitrary, user-built roster on any subject.
Use `/council` for the known five desks; use `/advisory-council` for everything else.

---

### TRIGGERS

**`/advisory-council`** fires on:
- Explicit `/advisory-council`
- "convene my X council" / "advisory board" / "what would my advisors say"
- Any invocation from `architecture-planning-sop.md` Stages 1, 4, and 6
- `marc-checkin` Stage 2 when the operator says yes (SKILL.md line 83)
- `planning-weekly` Phase 4 (`04-council.md` — built ON the advisory-council engine)

**`/council`** fires on:
- Explicit `/council [question]`
- "convene the council" / "debate this across desks" / "what would the desks say about"
- Any cross-desk life question touching 2+ of: money · career · time · location · revenue

---

### `/advisory-council` — FULL PROTOCOL

#### Front door (NO GUESSING — hard binary)

`skill → $DRIVE/councils/registry.md → confident match OR builder [honor]`

On invoke, the skill must:
1. If the user names a council → registry lookup. Confident match → LOAD → chaired session. No confident match → surface close names or offer "build new." **Never silently load a different council.**
2. If "build a new council" → Builder (see below).
3. If unspecific → read registry, present list: "Which council? You have: {names}. Or build new." Library empty / nothing fits → "We don't have a council for this yet — let's build one." → Builder.

**No auto-picking; no improvising a council from scratch.** (SCOPE.md §3)

#### Auto-context from a live project

**Before Stage 0**, check for an armed project:

```bash
bash "$HOME/lifehack-brain/system/hooks/pm_flag.sh" status  # → brief path or "none"
bash "$HOME/lifehack-brain/system/hooks/plan_flag.sh" path   # → plan file path or "none"
```

*(plan_flag.sh `path` sub-command was added 2026-07-21 explicitly for this use — SKILL.md lines 47–48)*

If a brief returns, build the **settled-ground card** from its §1 FRAME + §2 DECISION BOARD:
- Desired outcome (one line) + hard constraints / non-negotiables
- ✅ LOCKED decisions (each with one-line why) — settled ground
- ⛔ RULED-OUT options (each with why it died) — the load-bearing bucket
- **EXCLUDE** ❓ OPEN questions (those are the debate), peer positions, story-log

State to advisors verbatim: *"The brief items are SETTLED GROUND — work within them, do not re-propose
or re-open them. If you see a MAJOR problem with one, surface it as an explicit CHALLENGE-QUESTION for
the chair; do not simply re-suggest it. The plan is our current best thinking, not locked — push on it freely."*

Present a chair-confirmation banner before advancing:
`📎 Live project context — framing on {slug}: {outcome} · {N} locked · {N} ruled-out · plan: {name}. Adjust · dismiss · or go.`

**Degrade silently** if both checks return `none` or files are unreadable — no error, no empty banner;
ask the chair to state the frame.

**Known gap (debt-ledger `[ADVISORY-COUNCIL]`, 2026-07-21):** the settled-ground card has NOT yet been
validated on a real council run. Whether advisors actually honor "don't re-propose ruled-out" is
UNVERIFIED — wording may need sharpening after the first real run. `state:monitoring`

#### The chaired session — 4 stages, nothing auto-advances

**Stage 0 · FRAME**
Pull live project context (above); offer settled-ground card as pre-filled frame; confirm the question;
state who you'd convene and why (routing); let the chair adjust the room.

**Stage 1 · DIVERGE**
Dispatch each chosen advisor as an **isolated, parallel, blind** subagent (model: opus). Each returns:
`position · risks caught · grade A–F · the A+ move · what it refuses/flags`
Present compact, in-voice. Gate: *"argue, or another divergent pass?"* (loops freely — extra diverge
rounds are strictly safe; each is independent samples, no cross-contamination).

**Stage 2 · ARGUE (red-team)**
Re-run advisors as isolated subagents over a **static, anonymized snapshot** of Stage-1 positions
(labeled "Position A/B/C" — judge the argument, not the source). Mandate: "attack from your lens; you're
rewarded for the flaw, not agreement." Each returns: same schema + which peer claim challenged + why.
Gate: *"done, or keep hashing it out?"* (loops; skill flags diminishing returns: "no new conflict this
round — converge?").

**Loop safety note (SCOPE.md §4):** looping Stage 2 is multi-round debate (the documented sycophancy
failure mode). Protected by: (1) advisors critique the *current* positions only — the orchestrator holds
the running conflict ledger; (2) the chair steers each loop purposefully; (3) the diminishing-returns
signal fires. The loop is safe when these three hold.

The chair can **backtrack** at any seam (converge → argue more; argue → add a lens).

**Stage 3 · CONVERGE (chair-invoked moves, this order)**
1. **Floor ("center of the Venn")** — what survived every lens + the assumption the agreement rests on
   (a one-model council can share a blind spot — name it). Answers *"what's safe?"*
2. **Steelman the dissent** — argue the loudest unresolved objection at full strength: the antidote to
   false/shared consensus. Answers *"what if the agreement is the mistake?"*
3. **Integrated plan ("lock them in a room")** — the ORCHESTRATOR (not agents negotiating) drafts the one
   plan satisfying each advisor's non-negotiables with explicit tradeoffs. Then a **veto-check
   ratification**: each advisor (isolated) checks only "does this cross a hard line in my domain?" —
   a veto, NOT an agreement vote ("can you live with it?" resists sycophancy; "do you agree?" invites it).
   Answers *"what do I do?"*

"Press a specific conflict" is NOT a convergence move — it's more arguing; it stays in the Stage-2 loop.

**Stage 4 · LAND**
Artifact: plan/floor · surviving tensions · A–F grades · human-expert flags.

#### Synthesis output contract (SKILL.md §10)

1. Who convened + why
2. Floor (+ blind-spot flag)
3. Surviving conflicts (flag which held through red-team)
4. Grades (each A–F + A+ move; orchestrator overall read)
5. Integrated plan (+ veto-check results)
6. High-stakes flag: "sharpens questions; does not replace {engineer/inspector/licensed pro} sign-off"

**Synthesis guard:** weigh substance, never the most vivid/confident phrasing. A persuasive-but-wrong
critique reaching an uncalibrated judge is how structured critique backfires (Wynn et al. 2025 — cited
SCOPE.md §10); rank by evidence/domain-fit.

#### Sub-agent contract

`skill → Agent tool → isolated context per advisor → model: opus [honor]`

- Each advisor: its own isolated, parallel subagent
- **Blind in Diverge** (no peer context)
- **Static anonymized snapshot in Argue** (Position A/B/C)
- Loads only: its own advisor block + shared context (settled-ground card if live project; never peers)
- **model: opus** — the sole sanctioned exception to Lifehack Subagent Model Selection (SKILL.md
  line 100; SCOPE.md §9; CLAUDE.md Subagent Model Selection). Advisors' reasoning IS the deliverable;
  grunt-work rationale does not apply. Exception is scoped to small rosters (the routed 2–4 advisors).
- **Exception to the exception:** a council's own locked charter may pin otherwise. The
  `market-analysis` council (7 lenses) is locked to **sonnet** on cost — stated in SKILL.md line 103
  and in the council's Convening Contract. This is the only known override.
- No raw dumps. Chair (main session) synthesizes. Weigh substance, never vivid phrasing.

**HARD RULE: the chaired loop runs in the MAIN session** — never delegated to a subagent (Lifehack:
human-in-the-loop execution stays in the main loop). Subagents ARE the advisors, not the chair.

#### The Builder — create or localize a council

`skill → charter frame → proposed lenses → chair curates → flesh cores + voices → save to library + registry [honor]`

From scratch:
1. FRAME — "What's this council for, and what calls will it chew on?"
2. PROPOSE — 6–10 *distinct* candidate lenses covering the angles that matter; actively dedupes ("these two overlap — merge?")
3. CURATE — chair keeps / cuts / merges / adds / adjusts
4. FLESH — per kept lens: draft reasoning core (Domain/Catches/Refuses/Bias); then voice (name + character for human legibility, fenced off from analysis)
5. CHARTER — grading rubric + high-stakes policy + co-convene hints + `Routing home (hint): {desk}` field
6. SAVE+REG — write to `$DRIVE/councils/<slug>/council.md`; add row to `$DRIVE/councils/registry.md`

From a template: ingest template roster, run localization Q&A, fill `{{placeholders}}`, save as a concrete council.
Clone & modify and grow/edit paths also supported.

#### Roster file schema

```
## Charter
(grading rubric · "advisors disagree freely" · high-stakes policy · co-convene hints ·
 Routing home (hint): {desk/project})

### {Name "Nickname" Surname} — {Lens title}
Domain:  {what they cover}
Catches: {the specific failures/risks they reliably spot}
Refuses: {what they won't do / won't call something}
Bias:    {their decision tilt}
--- voice (delivery only — does NOT drive the analysis) ---
{5–6 lines: cadence, signature phrases, quirks — for human legibility only}
Convene for: {keyword} · {keyword}
```

The `Domain/Catches/Refuses/Bias` block is the **reasoning core** (clean, instruction-like).
The `voice` block is fenced off; persona drives delivery, not analysis. `Convene for:` is the router.

#### Library + registry

- **Library:** `$DRIVE/councils/<slug>/council.md` — all councils, one home each, fully centralized
  (callable from any desk, any conversation)
- **Registry:** `$DRIVE/councils/registry.md` — index: `name · slug/path · scope · created`
- The Builder writes registry entries on create/edit; the registry is the front door's source of truth

#### Persistence boundary

Two kinds of content; two destinations; **never mixed** `[honor]`:
- **The council** (who the advisors are) → library cartridge. Read-mostly. Only the Builder writes to it.
- **Session output** (plans, decisions, findings) → `/save` → Archivist routes to the relevant desk's
  `records/` · `state/` · canon. The `Routing home` charter field is a hint, not a bypass.
- **Never write session output back into the council file** — this would corrupt a reusable tool.
- The skill does NOT auto-persist. Stage 4 yields the artifact; the user `/save`s it (manual save-back).

---

### `/council` — PROTOCOL

#### Scope

Cross-desk life decisions only — questions touching 2+ of: money · career · time · location · revenue.
Single-desk questions route to the desk directly. Not a fact-checker; read-only throughout.

#### Step 1 — Subject selection (dynamic discovery — NO shipped roster)

`skill → folder scan of $NOTES/desks/ → read each canon/purpose.md → 2–5 relevant subjects [honor]`

**A deliberate architecture change: the roster is discovered, never declared.** The earlier design
hardcoded five named desk lenses in the skill file itself. That shipped one person's career, money,
calendar, clients and investments as *everyone's* council — convening a room about somebody else's
life for every reader, and staying silent about theirs. The current skill file states the rule
outright: it **ships with no roster, on purpose.**

The discovery mechanism:
1. Resolve the notes root (`shared/brain_root.py`), then enumerate subject folders with
   `find "$NOTES/desks" -mindepth 1 -maxdepth 1 -type d` — `find`, not a `ls -d …/*/` glob, because
   under zsh an unmatched glob is a **shell** error raised during argument expansion, before `ls`
   runs, so `ls`'s own `2>/dev/null` never suppresses it. That fires on every brain with no subjects
   yet — i.e. everyone's first `/council`.
2. For each candidate folder, read its `canon/purpose.md` — one or two lines saying what that folder
   is for. **That is the lens.** Nothing needs configuring: a subject that exists in the notes is a
   voice that can be in the room; a subject that does not, is not.
3. **Optional hand-written override:** if a purpose file is thin or missing, or a lens matters that
   has no folder yet, the user can write lenses at `<notes>/config/desks.md` — one row per subject,
   `name | what it sees` — and those override what is read from the folders. Most users never need it.

State selection + one-line reason per subject before dispatching. Do not force all of them if only
two are relevant; do not under-select either — if a lens would change the answer, it belongs in the
room. **If nothing resolves** (no notes root set, or no subject folders yet) — say so plainly and
STOP. Never invent lenses to fill the room; an invented council is a single voice wearing hats.

#### Step 2 — Parallel dispatch (REAL subagents, not personas)

`skill → Agent tool → one subagent per selected desk, IN PARALLEL [skill · honor on model pin]`

Why real subagents (SKILL.md §Step 2): loading all 5 desks' canon into one context is ~2,800 lines;
a single context collapses independent voices into one blurred lens. Real subagents each load ONLY
their own desk and answer from a clean lens. The independence is structural, not performative.

**Model — HARD (SKILL.md "R-1"):** pin `model: sonnet` on EVERY dispatch. A dispatch with no `model:`
silently inherits the (possibly opus) main session's tier. Set explicitly. No exceptions.

Each subagent: loads own desk canon + `state/current.md`; returns:
`POSITION · KEY DRIVERS (2–4) · RISKS THIS DESK SEES (1–3) · WHAT WOULD CHANGE THIS (1–2 conditions)`
Read-only. No writes, no executes.

#### Step 3 — Collect positions

Present each desk's position verbatim-ish, compact, before synthesis. No editorializing.

#### Step 4 — Synthesis (CONFLICTS ARE THE POINT)

`skill → orchestrator judgment → AGREEMENTS + CONFLICTS/TRADEOFFS + DECISION (conditional) [honor]`

The synthesis MUST surface conflict, not paper over it. Three labeled parts:
- **(a) AGREEMENTS** — where desks converge
- **(b) CONFLICTS / TRADEOFFS** — the genuine tension; name which desks pull which way and why; do NOT average into mush
- **(c) THE DECISION (conditional)** — "GO if X AND Y AND Z. DON'T if any one fails." Conditions drawn from the desks' own drivers. The conditional structure IS the synthesis.

A consensus-only output is a failure. The council ends by naming the next move + the desk that owns it.

#### `/council` bounds

Read-only throughout (no calendar writes, no ledger edits, no task creates, no file moves — not by
orchestrator, not by any subagent). Analyzes; does not execute. Actions route to the owning desk for
approval-first execution there.

---

### STORES TOUCHED (complete list)

| Store | Access | Element |
|---|---|---|
| `$DRIVE/councils/<slug>/council.md` | READ (run) · WRITE (Builder only) | advisory-council |
| `$DRIVE/councils/registry.md` | READ (front door) · WRITE (Builder on create/edit) | advisory-council |
| `$DRIVE/councils/_templates/` | READ (localization path) | advisory-council |
| `pm_flag.sh` output (in-memory) | READ (auto-context check) | advisory-council |
| `plan_flag.sh path` output (in-memory) | READ (auto-context check) | advisory-council |
| Active project brief (read-only) | READ (settled-ground card) | advisory-council |
| `$DRIVE/desks/{desk}/canon/*.md` | READ (desk subagent loads own only) | council |
| `$DRIVE/desks/{desk}/state/current.md` | READ (desk subagent loads own only) | council |
| Session output | via `/save` → Archivist; never stays in council file | both |

---

### GATES AND ENFORCEMENT (the honest map)

**No hooks registered for either skill (confirmed: `grep` of settings.json returned no council entries).**

All behavioral contracts are **honor-system** or **skill-logic** (prose instructions + model compliance).

| Contract | Tag | Notes |
|---|---|---|
| Front door: load named or build (no guessing) | `[honor]` | No hook intercepts a "wrong" council pick |
| Settled-ground card exclude open-questions | `[honor]` | Model judgment; no verification |
| Nothing auto-advances (chair gates every seam) | `[honor]` | Model discipline; no hook blocks auto-advance |
| Advisors blind in Diverge | `[honor]` | Structural (isolated subagent context) — but no hook verifies the context was actually isolated |
| Static snapshot in Argue (not live debate) | `[honor]` | Model disciplines the snapshot; no hook prevents feeding live context |
| model: opus for advisory-council advisors | `[honor]` | Prose instruction only; the model-drift debt item (debt-ledger `[COUNCIL-MODEL-DRIFT-GUARD]` 2026-07-20, `state:parked`) flags this. No hook asserts dispatch=opus / all-others=sonnet. The operator deferred building a guard as over-build for a one-person system |
| model: sonnet for /council desks (R-1) | `[honor]` | Hard prose rule; no hook enforces; same drift risk |
| Session output never written to council file | `[honor]` | No guard prevents a write to the cartridge |
| Chaired loop stays in main session | `[honor]` | No hook detects delegation to a subagent |
| `/save` before close (manual) | `[human]` | User-invoked; skill does not auto-persist |

**Maturity label: LIVE·gap** — the skill fires and its core chaired-session logic runs; but:
- The opus pin is honor-system with a documented drift risk (no blocking guard)
- The settled-ground card is unvalidated in production (monitoring, per debt-ledger)
- No hook plane at all — the entire behavioral surface is model-discipline `[honor]`

The `·gap` is warranted: a tip-only reader seeing `LIVE` would over-trust enforcement posture when the
ENTIRE contract is prose-only. The gap prose in this GAPS section is the discriminator.

---

### GAPS (documented fail-open conditions)

**G-1 — No hook enforces model selection (the sonnet/opus split is prose-only across ~20 files)**
`debt-ledger: [COUNCIL-MODEL-DRIFT-GUARD] state:parked`
The opus pin for advisory-council advisors and the sonnet hard pin for /council desks are documented in
~20 files but no blocking guard asserts it at dispatch time. A future caller that copies the wrong
model pin would produce a silent wrong-model run. The operator deferred building a guard as over-build for a
single-person system — revisit if pins drift again. `done_when: a guard asserts dispatch=opus (advisory-council) / sonnet (council), OR drift proves unnecessary.`

**G-2 — Settled-ground card unvalidated in production**
`debt-ledger: [ADVISORY-COUNCIL] state:monitoring`
The auto-context settled-ground card (LOCKED + RULED-OUT with why) was designed and built but has NOT
been exercised on a real council run as of 2026-07-24. Whether advisors actually honor
"don't re-propose ruled-out" is UNVERIFIED. Card wording may need sharpening after the first real use.

**G-3 — Advisor isolation is structural but not hook-verified**
Each advisor runs in an isolated subagent context (structural wall). There is no hook that verifies the
context contained only the advisor's block + shared boundary context (never a peer's position). A
prompt construction error could leak peer context into Diverge; the model is the only check.

**G-4 — Council cartridge has no write-guard**
No hook prevents writing session output back into a council cartridge file. The prohibition is honor-
system. A confused `/save` route to `councils/<slug>/council.md` would corrupt the cartridge.

---

### INTEROP SEAMS

**1. `architecture-planning-sop` TRIGGERS `/advisory-council` at Stages 1, 4, and 6.**
(architecture-planning-sop.md lines 69–104)
The SOP calls `/advisory-council` three times over a single project council, using the same roster
cartridge across all three stages: Stage 1 for independent review; Stage 4 for pre-mortem
("assume the build derailed — what did we miss?"); Stage 6 for re-review ("did the revision close
each condition?"). The SOP's own exploration/drafting subagents stay **sonnet** — only the
`/advisory-council` engine's advisors run **opus** (the SOP explicitly states this exception at
line 139). Loop exit: READY verdict from the council AND stakeholder confirms no overrides outstanding.

**2. `planning-weekly` Phase 4 IS the advisory-council engine.**
(skills/planning-weekly/prompts/04-council.md)
The weekly planning skill's pressure-testing phase dispatches 6 fresh-context member files from
`skills/planning-weekly/prompts/council/*.md` as the advisory-council's advisor roster, running the
blind-diverge → argue → converge protocol. Members run **opus** (the designed exception, as stated in
`04-council.md` and `_member-format.md`). Cost note in `04-council.md`: "6 opus advisors/run is heavier
than the rule's 'small roster 2–4' — the operator can down-scope to sonnet if cost bites." The Phase 4 output
is a set of numbered tensions + the operator's per-item disposition (fold in / loop back / hold) — the operator keeps
the pen; the council never re-ranks.

**3. `marc-checkin` Stage 2 optionally invokes `/advisory-council` on the market-analysis council.**
(skills/marc-checkin/SKILL.md line 83)
Marc-checkin asks the operator at Stage 2 whether to convene the advisory council on the market-analysis
cartridge (7 lenses). If yes: runs `/advisory-council` on `councils/market-analysis/council.md`
per its locked Convening Contract — **sonnet** (cost-locked exception to the opus exception). Marc
chairs. Never auto-summoned.

**4. `pm_flag.sh` + `plan_flag.sh` FEED `/advisory-council`'s auto-context.**
(system/hooks/plan_flag.sh lines 13, 94–96)
The `path` sub-command of `plan_flag.sh` was added 2026-07-21 explicitly for `/advisory-council`'s
auto-context check. The skill reads both flags at Stage 0 to build the settled-ground card. Changes
to `pm_flag.sh` TTL or `plan_flag.sh path` API propagate directly to the auto-context flow.

**5. `/save` is the ONLY persistence path for session output.**
Session findings (plans, decisions, floor/integrated-plan artifacts) must go through `/save` → Archivist
routing. The charter's `Routing home (hint): {desk}` field tells the Archivist where outputs usually
belong — a hint, not a bypass. The Archivist adjudicates. Council file is never written with findings.

**6. `/council` isolation depends on the same desk canon that desk sessions read.**
Each `/council` subagent loads its desk's `canon/*.md` + `state/current.md`. Any drift or staleness
in those files directly affects council output quality. The independence is structural; the signal quality
depends on canon maintenance.

**7. `/council` vs. `/advisory-council` routing.**
These two are NOT redundant alternatives — they are non-overlapping by scope. `/council` is for the five
named desks (cross-life questions); `/advisory-council` is for any user-built roster cartridge (any
subject). The SCOPE.md explicitly names `/council` as the architectural parent that `/advisory-council`
generalizes. A session that convenes the wrong one wastes rounds (wrong lens set). The discriminator is:
does the question map to the five desk lenses, or to a subject-specific roster?

---

### INTENT / CURRENT-VS-TARGET

**BY DESIGN:** both skills are honor-system by intent — a council is a reasoning aid, not a guard.
The chaired session's value is in the human steering every seam; mechanical enforcement would undermine
that. The maturity label `LIVE·gap` is honest: the protocols run; the behavioral surface is skill-prose
with no hook backstop.

**Current → LIVE·gap:**
The chaired session protocol, the convergence moves, the roster loading, and the sub-agent dispatch all
work. The gaps (model-drift, card validation, isolation verification, cartridge write-guard) are real
but deferred (parked / monitoring) — not blocking daily use.

**TARGET:**
1. Validate the settled-ground card on the first real council in a live project (G-2 → close or sharpen wording)
2. Model-drift guard if the opus/sonnet pins drift again (`[COUNCIL-MODEL-DRIFT-GUARD]` — build only if needed)
3. Cartridge write-guard — a simple `guard_canon_write`-style hook blocking writes to `councils/*/council.md`
   without authority:builder (low priority; single-user system)

---

## AUTO-COMPUTED   (machine-only — hand-set at authoring; the F1.5 checker will own this once built)

- **maturity_label:** LIVE·gap
- **check_detail:** No hooks registered for either skill (settings.json grep returned zero council entries
  — confirmed 2026-07-24). All behavioral contracts are honor-system (`[honor]`) or structural (isolated
  subagent context). LIVE: both skills fire and the core protocols run in production (advisory-council
  engine in planning-weekly Phase 4 and architecture-planning-sop Stages 1/4/6; /council in cross-desk
  sessions). `·gap`: (1) opus/sonnet pins are prose-only with documented drift risk (debt-ledger
  `[COUNCIL-MODEL-DRIFT-GUARD]`, parked); (2) settled-ground card unvalidated in production (monitoring);
  (3) advisor isolation structural but not hook-verified; (4) no cartridge write-guard. A tip-only
  reader seeing `LIVE` without `·gap` would over-trust enforcement posture. Gap disclosure required. →
  **LIVE·gap**. Not PARTIAL (skill runs end-to-end; no missing capability); not TARGET (it works today).
