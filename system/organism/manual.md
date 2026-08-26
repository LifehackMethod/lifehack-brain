---
topic: [system-architecture]
title: "Lifehack Manual — how the whole system works together (middle altitude)"
record_type: reference
desk: root
created_at: 2026-07-21
updated_at: 2026-07-24
status: active
authority: user
---

# Lifehack Manual — the middle-altitude how-to guide

> LADDER: MANUAL (how it works together). up → the map ; full mechanics → `elements/<slug>.md`

> **What this is (the MIDDLE altitude of the self-schematic — renamed from `flow-registry.md` 2026-07-22).**
> A **manual**: a medium-density, ~5,000-ft description of how the whole Lifehack system works and
> operates **together** — how the parts combine into outcomes. It is DESCRIPTIVE, not a dumb index and
> not the weeds. It does **NOT** get into how each individual part works step-by-step — that lives one
> level down.
>
> **The three altitudes (the operator, locked 2026-07-22):**
> - **TIP = a MAP** — a bare schematic (boxes · arrows · pointers) in the global + per-desk `CLAUDE.md`. Loads every session.
> - **MIDDLE = this MANUAL** — how the system works together at 5,000 ft. One medium file. On-disk, on-demand.
> - **BASE = an ENCYCLOPEDIA** — `system/organism/elements/<name>.md`, one deep entry per load-bearing element (the in-the-weeds detail + every interaction/overlap). On-disk, on-demand.
>
> **Scope = the WHOLE architecture** (the operator 2026-07-19): skills · hooks · tools · system files · memory ·
> desks · Pulse (cron) · the security plane — and how they combine. Not a skill-map; skills are one slice.
>
> **★ AUTHORED 2026-07-24 (N5):** the middle "how it all works together" layer is now filled — a ranked
> INDEX of all 50 live parts + a TYPED INTEROP SEAM entry per non-trivial element (42 entries; 8 dormant
> parts carry an index line only), derived from each element's own INTEROP SEAMS. The map (tip) is a
> regenerated slice of this manual + the element STORES tables (N6).

## How this manual + the encyclopedia are maintained (the human/machine split — LOCKED)

The organism principle: **meaning is human-authored; facts are machine-computed.** Enforced *in the
format itself*, so it is testable, not conventional:

- **`## AUTHORED` (human-only).** The meaning of an element — its trigger, hand-off narrative, ports,
  intent, current-vs-target, interop seams. **Only a human edits this.** No script, and no auto-downgrade,
  ever writes inside an AUTHORED block. When a cited source file changes, the system **NUDGES** a human to
  re-author; it never rewrites the meaning itself.
- **`## AUTO-COMPUTED` (machine-only).** The *facts about enforcement* — the maturity label + when it was
  last checked. Written ONLY by the Feature 1.5 enforcement-label checker (`label_checker.py`, which
  fire-tests the named guards). A human does not hand-edit these.

Kept live by **detect-and-nudge**, redundant channels (split by blast radius): the in-session PostToolUse
nudge (`nudge_flow_drift.sh`, Feature 1.4) · the Archivist weekly drift-check (Feature 2.1) · the Helm
freshness tile (Feature 2.2) · the skill `flow:` frontmatter field (Feature 2.3).

**Format:** the base encyclopedia-entry format (the `## AUTHORED` / `## AUTO-COMPUTED` skeleton) is locked
in `system/organism/map-format-specs.md`; each entry lives at `system/organism/elements/<name>.md`.
✅ `system/organism/map-format-specs.md` is here — verified on disk 2026-08-15. It landed alongside the manual
and the element entries it governs, so the format lock above is checkable, not just asserted.

## THE HONESTY-LABEL CRITERIA (system-wide — a label must be fire-tested, never assumed)

> The whole point is to stop the system lying about what it enforces (the `validate_on_write`-was-inert
> lesson). A label is a *claim about enforcement*; every LIVE claim must be proven by firing the real guard
> against a synthetic violation — registration is NOT proof.

### THE LABEL GRAMMAR — LOCKED 2026-07-28 (the operator's ruling, S1.1 T1.3 / D-1)

```
maturity_label: <BASE>[·gap][ [provisional]][ (honor)]
                  ^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                machine   HUMAN-OWNED annotations
```

- **`<BASE>` — MACHINE-OWNED, one of `LIVE` · `PARTIAL` · `DORMANT`.** Computed by
  `label_checker.py` from a real fire test and written by `write-labels`. **Never hand-set.** A
  hand-edit that disagrees with the fire test is caught as `LABEL-DRIFT` and ambers the gauge.
- **The suffixes — HUMAN-OWNED, never touched by the machine.** `·gap` = a documented fail-open
  exists alongside a working guard · `[provisional]` = authored but not yet independently reviewed ·
  `(honor)` = prose-only rule, no hook behind it.

**Why the split:** it makes both lies structurally impossible. The machine cannot overwrite a
human's judgement about a known hole, and a human cannot type a green the fire test did not earn.

**Why NOT one flat controlled vocabulary:** collapsing suffixes into the base would either destroy
the human annotations or force the machine to reason about them. Two fields with two owners is the
smaller, honest move.

**When several guards back ONE element (D-2, LOCKED): the WEAKEST result wins.** One dark guard
drags the element down rather than being outvoted by healthy siblings — the conservative direction,
because this map exists to prevent false greens. Implemented in `write-labels`.

**All 49 elements were normalised to this grammar on 2026-07-28** (4 were malformed: a trailing `#`
comment, a `[TO BE COMPUTED]` placeholder, a `PENDING`, and a leading double-space). Anything the
writer cannot govern is REPORTED, never silently skipped.

- **LIVE** — every enforcement point is **hook-enforced AND fire-tested**: `label_checker.py` fired the
  named guard against a synthetic violation and confirmed it BLOCKS (`exit 2` / `decision:block`), and the
  guard is **git-tracked** (travels to every machine). A guard that isn't git-tracked cannot be LIVE.
- **PARTIAL** — the element runs and produces its outcome, but ≥1 claimed enforcement point is
  **honor-system** (prose-only, not hook-backed), OR not git-tracked, OR the fire-test does not pass, OR it
  depends on a human step that may not happen. Honest "works, but not everywhere/always guaranteed."
- **TARGET** — aspirational: the element, or the enforcement it should have, **does not exist yet**. Named
  so the gap is visible, not hidden.

**Auto-downgrade (fail-closed):** the moment a cited `generated_from` file is missing, or a fire-test that
previously passed now fails, the checker rewrites `maturity_label` DOWN (never up silently) and pings —
writing ONLY inside `## AUTO-COMPUTED`. Upgrading to LIVE requires the fire-test to pass again.

---

## THE THREE COMPROMISES — what this system deliberately is NOT (a feature, not a bug)

> Written into the map 2026-07-28 (organism-audit S1.3 T3.2). A reader — especially a second
> person being handed this system — will notice these and assume they are oversights. They are
> not. Each is a deliberate trade, and each has a **compensating rule** that makes the trade safe.
> Naming them here is the point: an unstated compromise reads as a defect, and a second person
> would "fix" it.

### 1. The three tiers, named for what they actually are here

Most systems this shape have a presentation layer, a business-logic layer and a database. This
one has all three — they just do not look like the textbook.

- **Presentation** = **Helm** (the dashboard), the **status bar**, and **notify** (phone pushes).
  That is the whole of it. There is no UI framework and no web app.
- **Business logic** = **skills · hooks · `system/tools/`** *plus the LLM session itself*. This is
  the answer to "where is the code layer": a skill is executable procedure written in prose, a
  hook is executable policy written in bash, and the running session is the interpreter. The
  logic is not all in files, and that is intentional — it is what makes the system adaptable
  without a deploy.
  ⚠ **That sentence — "the running session is the interpreter" — is developed further, and its tension with `skill-building-sop.md:199` (LAW 1) named, in THE CODE/LLM SEAM below.**
- **Data** = **deliberately-thin files** on Drive (content) and git (code). **There is NO
  database, BY DESIGN.** Markdown and JSONL that a human can open, diff, and correct beat a
  schema no human will ever query — for a single operator whose data is measured in megabytes,
  a database would add migrations, a daemon, and a second source of truth, to solve a scale
  problem that does not exist.

**The lifecycle that follows from the git/Drive split:** `git pull` replaces the git side wholesale —
every tracked file, this manual and the map in `CLAUDE.md` included — and never comes near the Drive
side, because the AI Brain was never inside the folder a pull writes into. **A person's own machinery
(a skill, agent, hook, script) never sits in either of those two paths at all** — it lives outside the
repo, in `~/.claude/` or the AI Brain, precisely so a pull has nothing of theirs to touch. `~/.claude/`
itself is the one home that rides neither side cleanly: required there so the harness can FIND a
skill/agent/command/hook, it survives a pull because nothing there is git-tracked — but it is not on
the Drive side either, so it is backed up nowhere. Full account, including the discovery test and the
`~/.claude/` gap: `system/organism/elements/where-things-live.md`.

### 2. The compensating rule: ASSERT the output, never report success

The cost of the choices above is that nothing is type-checked and nothing fails loudly on its
own. So the system's central discipline is: **every automated thing must ASSERT its own output,
never merely report that it ran.** "Pushed 2 files", "sweep complete", "exit 0" are the tool
describing its intent, not the world. Read the result back and check it.

**The standard door is `emit_status.py` → `state/status/*.json` → sweeper / Helm / the gauge.**
Self-tests, fire-tests and receipts all report THROUGH the tile plane. Anything that does not
report there is nonconforming — it can fail invisibly, and something eventually will.
⛔ `state/status/*.json` is runtime-generated — status tiles written by a run, under your own notes root,
created on first run and never committed. There is no version of them to ship (migration note, 2026-08-15).

This is not theory. Every green-illusion this project has found came from a component that
reported success while producing nothing observable: a dashboard tile "going amber" rendered in
black ink · a token table reading 0.0% · a watchdog dead 11 days behind a green board · a fire-test
script that had been RED for 16 days with nobody reading it · a status gate whose "NOT READY"
string contained the word "READY" and so never fired, for a month, costing a real overbill.

### 3. Single-rider by design — and the git rule that follows from it

Lifehack assumes **one operator**. No multi-user auth, no roles, no locking beyond a lock dir,
no on-call. That is correct for what this is, and it is why a circuit breaker that "disables
until a human resets it" silently means *off forever* here — there is no rota to catch it.
(Fixed 2026-07-28: breaker trips are now a doubling backoff with a half-open retry, never a
tombstone.)

The one place single-rider is NOT true is the **git clone**, where the operator runs ~7 concurrent
Claude windows against one working tree. So: **stage by explicit path, always.** `git add -A`,
`git add .`, `git commit -a` and the rest of the everything-add class are hook-blocked
(`guard_git_add_class.sh`) because in this clone "add everything" is never your own work — it is
everyone's. A scoped directory add stays allowed; it is deliberate. And in a shared tree,
`git status` is not a record of what YOU changed: diff against the commit you expect, not HEAD.

---

## THE CODE/LLM SEAM — how this system is actually made

> ⚠ **PROVISIONAL. NOT PRESCRIPTIVE. THIS IS BEST-CURRENT-THINKING, NOT DOCTRINE.**
> Written 2026-08-09 from one long session plus a six-reader sweep of two projects. It is filed here so
> the thinking survives the window that produced it — **not because it has been validated.** Everything
> below describes what we have observed so far, offered for testing. **Where it disagrees with a LAW in
> `skill-building-sop.md`, the LAW remains the operative rule until the operator says otherwise.**
> ⛔ **Do not cite this chapter as authority. Do not gate anything on it.** It exists to be argued with.
> **This is a new area and we are early in it.**
>
> **What a reader would otherwise misread:** you will assume the code in this system is the system. It
> isn't — and the manual already says so, one chapter up: *"the running session is the interpreter."*
> This chapter develops that sentence. ⚠ **It also sits in tension with `skill-building-sop.md:199`
> (LAW 1), which says code owns the perimeter and the model works inside it. Both statements are
> currently live. That tension is real, it is named here on purpose, and resolving it is the operator's call.**
>
> **Evidence:** `state/projects/project-system/records/2026-08-09-code-llm-spiral-candidates.md` ·
> `…/2026-08-09-code-spiral-audit-ledger.md`
> ⛔ `state/projects/project-system/records/2026-08-09-code-llm-spiral-candidates.md` and the audit ledger
> beside it live in the author's own notes, not in this repository — the working evidence behind the chapter,
> kept where the author's writing is kept and never committed here (migration note, 2026-08-15). The chapter
> stands on its own; you cannot open its footnotes.

### ▲ 10,000 ft — a shift being staffed, rather than a machine being built

The session behaves like an employee working a long shift. **Extremely capable** — fast, good judgment,
handles the unfamiliar. **Also forgetful by the hour, and eager to please whoever is standing in front of
them.**

On this reading, code is not the shop. **Code is what you put in the shop to help that employee**, and
there seem to be only four such things:

**Signs on the wall** — prose in a file. Only work if someone looks up.
**A supervisor who taps their shoulder** — the per-turn injector. Happens *to* them rather than waiting.
**A locked door** — the hook. They cannot walk through it whether they remember it or not.
**A timecard** — the artifact. Evidence they were there, after the fact.

#### The spiral, in this frame

**The pattern looks like trying to automate a shop that is actually staffed.**

The employee misses something. A machine gets installed to catch it. **But the machine does not run itself
— the employee has to switch it on.** They forget. So a machine gets installed to check the machines.

Meanwhile, measured across three projects on 2026-08-09: **fifteen machines in the back room nobody
switches on** · **thirteen with a green light wired to nothing** · **nine signs in the storeroom.**
Including one on a shelf a session actually opened — it read the first eighty lines and the sign starts
at eighty-two.

#### Why it has felt correct each time

**When the employee fails, you see it. When a machine fails, it hums and the light stays green.**

**13 of 36 code failures reported success while producing nothing.** `emit_status.py` printed `✓ PASSED`,
exit 0, and wrote no tile — **live since 2026-06-25.** `verify-hooks.sh` sat **red for 16 days.** A guard
printed its denial on the wrong channel: **blocked nothing, scored PASS.**

So each comparison between "unreliable model" and "reliable code" weighs **all** of the model's failures
against **a third** of code's. ⇒ **This looks like a measurement problem rather than a discipline
problem — the evidence in front of you genuinely supports building another machine.**

#### The inversion this suggests

**The session appears to be the host. Code appears to be the guest.**

`skill-building-sop.md:199` says *"code owns the mechanical perimeter, the LLM owns judgment inside it"* —
the model inside code's wall. **In this system it may be the reverse:** the session is what runs, and code
sits inside it waiting to be picked up.

That rule is sound engineering **from systems where code is the host.** In that world delivery is free — a
function call always arrives — so the only leg worth guarding is the return. **The rule came over; the
reason it worked may not have.** `skill-system/brief.md:2608` had already named this shape: *"when you
reuse a rule, re-derive its justification against the new subject."*

#### Where the metaphor breaks — stated rather than sold

**It makes the employee sound duller than they are.** They are excellent and forgetful, which is a
different problem needing different help.
**And it undersells code in three places where code plainly wins: the till, the lock, and the timecard** —
arithmetic, refusal, and proof. A person should not be doing any of those.

### ▲ 5,000 ft — the landmarks

#### 1. Three tiers, by who has to remember

**Fires on its own** — hooks and per-turn injectors.
**The model must call it** — every tool. Its reliability tracks the model's memory, which is what rots.
**The model must call it *and* type it exactly** — two ways to fail.

**Measured 2026-08-09: 49 hooks registered and firing** (29 PreToolUse · 10 UserPromptSubmit ·
5 PostToolUse · 4 Stop · 1 SessionStart) **against 15 tools with no caller.** So far, everything that
fires by itself works and everything that waits does not. ⇒ **A tool has behaved more like a suggestion
than a control.**

#### 2. Two handoff legs, and only one currently has a rule

**Outbound — code produces, the model must pick it up. 37 of 57 failures (65%).** The open question is
*what makes the model look?* Three answers appear available: **it's on screen every turn · it fires on the
act · the model remembers.** The third is hope, and it accounts for most of the 65%.

**Return — the model hands something back. 14 of 57 (25%).** Closed set, a member meaning *no outcome was
reached*, membership checked on the way in.

⚠ **Every enforceable clause of the current seam rule sits on the leg carrying 25% of failures.** The
outbound leg has no rule at all.

#### 3. Payload and delivery look like different axes

**The payload has been the same thing throughout: plain English, written for a model, landing when it is
needed.** There is no ladder here. A hook's deny message and a sign on the wall are the same substance.

**Only delivery has tiers.** A hook is not better prose — it is the same prose with better timing, and the
only one that can also refuse.

⛔ **The artifact does not sit on that ladder at all.** It is evidence after the fact, on its own axis.

#### 4. Liberal at the door, strict in the record

The pattern that has held: **accept anything that clearly means one of the legal values; store only a
legal value.**

**Measured 2026-08-09:** a verdict interface built that same night rejected **five of six plausible
phrasings** — `can proceed`, `can-proceed`, `CanProceed`, `proceed`, `ok`. Only the exact underscored
string passed. **This was a repeat**: `fork.py` did it first, and the recorded reaction was *"that's dumb
as fuck."*

**Why strictness may be backwards here:** strict code rejects what it does not recognise, and what it does
not recognise tends to be **a degraded session** — the moment the step most needed to land. **It has been
solid when nothing was wrong and unhelpful when something was.**

#### 5. The trade looks like error *shape*, not error *rate*

The operator, 2026-08-09: ***"if the LLM gets off course you can put it back; if the code breaks we're fucked."***

A model's error has been **visible, bounded, and non-breeding.** Code's error on the same question has
been **invisible, unbounded, and compounding** — each patch adding surface. ⇒ The trade appears to be a
higher rate of cheap visible errors against a lower rate of silent multiplying ones.

#### 6. What each side has been good at

**Code:** arithmetic · refusing an irreversible act · membership in a closed set · verifying an artifact
or hash · timing.
**The model:** meaning · anything containing a soft word · normalizing messy input · judging whether a
stranger would be confused — **which code has not been able to do at all.**

#### 7. Patterns that have tended to go wrong

A tool with no named caller · code deciding what a soft word means (*meaningful · stale · right ·
proper*) · **code that checks whether other code ran** · asking the model to self-report compliance · a
strict door stacked on a remembered call · trusting a search that returned nothing without a positive
control.

⭐ **One signal that has marked the shift from hybrid toward application: writing code whose job is to make
sure other code ran.** One layer has stayed manageable. Two layers has meant babysitting the machinery.

### ▲ Ground — dated specifics, both directions

#### What has worked, repeatedly

**A blind second instance — 8+ recorded uses across two projects, never previously named as a pattern.**
Eight sealed agents into the elements: **8/8 arrived, zero fabrications.** **55 sealed agents** settling a
map bake-off by measurement rather than debate. **Eight blind auditors over 795 files** — of 84 deletion
candidates, 67 were one concluded lab experiment, so real dead wood was **2.3%, not 11%** (*"the wrong verb
destroys working machinery"*). An adversarial audit **2-for-4 on day one**, finding a fire-test silently
dead. A skeptic pass killing a claim of **476 broken edges** — none real, a path bug. LAW 3, which two
teams stripped everything else down to and kept.

⭐ **Why it seems to work:** the instrument is **structurally incapable of the failure it is testing for** —
a blind reader cannot fake understanding because it has no context to fake with. Same principle as the
tool-less `ingest-reader`: **the wall is structural, not cognitive.**
⭐ **What made the asking work:** ⛔ **no checklist** (a checklist finds only what its author already
imagined) · **asking it to DO the job rather than evaluate the artifact** · **treating the assumptions it
must state as the measurement.**
**Cost:** haiku, two files, one job — **53,243 tokens / 68s**, beating a 110,226-token sonnet baseline.
⚠ **In the one case measured, a second confirming pass cost 110,354 tokens / ~4.3 min and bought nothing.**

**Derive it rather than hand-keep it.** `buried_command_hint.sh` reads frontmatter — *"stopped flagging
`/autoplan` the instant the flag left, with zero edits."* The capability census regenerates every run and
refuses hand edits: *"a hand-kept index rots and then LIES, which is worse than having none."* A producer
roster read from live `crontab` after a curated dict *"enumerated it as NOTHING, which is WHY an 87%
failure rate was invisible."*

**Grepping the live caller rather than reasoning from lineage** — recorded twice; *"both times the one
reasoning from LINEAGE was wrong."*

**An artifact only the real work could produce.** `pad_archive`'s receipt — three projects, never shown to
lose data. `skill-builder` independently replacing self-declared phase completion with a required
artifact, **explicitly borrowing `save_step_ledger.py`.**

**And three smaller ones:** stating the denominator · **admitting the gap out loud — a gap-admission note
measurably outperformed silence in blind probe testing** · stating the fraction rather than the adjective ·
testing on a scratch copy, *"nothing ships in order to test it, and a failure costs nothing."*

#### What has failed before — the record so far

⚠ **These are dated instances, not prohibitions.** They are recorded so a future session can weigh them,
not so it is forbidden from trying something similar with better reasons.

`emit_status.py` — green light, no tile, **since 2026-06-25** · `verify-hooks.sh` — **red 16 days**,
unread · a guard denying on the wrong channel, **blocking nothing, scoring PASS** · `except: continue`
swallowing **1,300 rows** and reporting `0 examined` · `age_s None` becoming 0 so a silent producer could
never escalate · a DECISION gate comparing sha256 to job names, **vacuous by construction**.

`_derive_reader` inferring *"did real work happen"* from a file timestamp — **five bypasses in six
minutes**, two of them things a careful session does by accident · a second `start` call wiping stamps and
pushing the clock forward · **a strict door rejecting five of six phrasings, twice** · a guard matching a
literal path string that **a shell variable walked straight past** (*"cannot be completed by adding an
eighth regex"*) · a skip-filter matching macOS temp roots · a 40-char truncation turning *"30 active
DANGER"* into *"30 ac"* — **a redaction, not a summary.**

`inject_sop_before_build` keyed on the user's words, **firing at session start hours before the edit** · a
rule persisted in **four files and reaching zero of them** · **reading lines 1–80 of a file whose rule
begins at 82** · a clone-only grep returning **0 hits against 21 real references** · a fabricated **"141
sealed agents"** written into an always-loaded banner · a lane reading an **11-minute-old scratchpad note**
as a human ruling.

### What is NOT settled — read this before leaning on any of the above

**The whether/what boundary.** `pad_archive` checks whether a hash matches. Is that code deciding
*whether*, or code deciding *what*? **It is the one piece never shown to lose data, so any rule that
cannot account for it is wrong.** Unresolved.

**Is the no-outcome member mandatory or advisory?** The operator's own question,
`state/projects/ingest-skill/design/skill-maker-note-the-seam-slot.md:82`. **Unanswered.**
⛔ `state/projects/ingest-skill/design/skill-maker-note-the-seam-slot.md` lives in the author's own notes, not
in this repository, and is never committed here (migration note, 2026-08-15). The question above is quoted in
full; the note itself is not openable from here.

**Is a reminder enough, or is a hook needed?** The per-turn line shipped 2026-08-09 is **live and
untested.** What has been observed is that *blocks* worked at boundaries — three fired that night and each
changed the build. **Reminders for mid-work steps remain an experiment in progress, not a finding.**

**And the honest caution about this whole chapter:** the unifying lens fits **57 of 57** instances, which
is exactly the shape of a theory built on its own evidence. **The useful test is what it forbids, not what
it explains.** It cleanly forbids the 111-line scorecard built that night. Whether it forbids anything else
useful is unknown.

## THE RANKED ELEMENT LIST — the index (all 51 live parts, rank-ordered; each links DOWN to its encyclopedia entry)

> The load-bearing components in rank order. Each: **slug** *(scope)* — machine-computed maturity label → its base file. A `↓ #slug` means a full middle-altitude entry exists below; DORMANT/trivial parts get this index line only (per `map-format-specs.md §8.5`). Slug = map box = manual header = filename stem (2 gloss exceptions: `save`→save.md, `memory-read`→read.md).

> **⛔ TEN OF THE 51 DID NOT MIGRATE — read this before following a pointer** (migration note, 2026-08-15).
> This index, and the element entries below it, are the donor's list of 51 and are kept whole on purpose: a
> list that quietly drops what was left behind teaches you the system is smaller than it is. **41 of the 51
> ship here** *(counted mechanically 2026-08-15 against `elements/` — the earlier figure of 42 was a
> file-count taken before a second authored-here element existed; see the ADDENDUM below)*. **These ten do
> not, and their `elements/<slug>.md` files are absent by decision, not by accident:**
>
> - `elements/emily-desk.md` · `elements/marc-desk.md` · `elements/clair-desk.md` · `elements/deryl-desk.md` ·
>   `elements/dobby-desk.md` · `elements/cal-pipeline.md` — ⛔ excluded from the migration: **personal.** They
>   are one person's own desks (auditions, markets, consulting, money, calendar), not general-purpose parts.
> - `elements/helm.md` — ⛔ excluded from the migration: **named.** The operator ruled Helm out by name; it is
>   the one thing on the closed exclusion list that is infrastructure rather than personal.
> - `elements/overmyshoulder.md` — ⛔ excluded from the migration: **browser-bound.** It reads a live Chrome
>   tab, and the whole Chrome path was ruled out of this system (see the two corrections further down).
> - `elements/two-machine-residency.md` · `elements/git-autopush.md` — ⛔ excluded from the migration:
>   **two-machine.** Both exist to keep one person's two machines in step. Whether they migrate is formally
>   **unruled** on the donor's side (`OL-P8-4`); until that is answered they are not here.
>
> Every other numbered line below resolves. If a pointer in this index or a `## <slug>` entry further down
> names one of the ten, that is this banner's subject — the entry describes a part of the donor system that
> stayed there.

> ⭐ **ADDENDUM — TWO ELEMENTS WERE AUTHORED HERE AND TAKE NO NUMBER.** The numbered list above is the
> **donor's** list of 51 and is frozen at 51 on purpose; a 52nd line would quietly turn a preserved
> artifact into a living one, and then nobody could tell which entries were inherited and which were
> written here. So these two sit outside the numbering rather than extending it. **Both files exist on
> disk and both ship** *(43 files in `elements/` = 41 donor + these 2, counted mechanically 2026-08-15)*:
>
> - **planning** *[GLOBAL]* — PARTIAL·gap [provisional] (honor) → `elements/planning.md` · ↓ `#planning`
>   The daily + weekly cadence layer. It is **not** a rename of the donor's `cal-pipeline` (#44, which
>   stayed) — that file described one person's own calendar desk; this one describes the generic
>   capability that shipped. Do not reconcile the two.
> - **brain** *[GLOBAL]* — PARTIAL [provisional] (honor) → `elements/brain.md` · ⏳ no `## brain` entry
>   below yet. The system's self-description layer — this manual, the map above it, and the element
>   corpus below it. Its middle-altitude entry is **owed, not present**; the base file is complete.

1. **ingest-gate** *[GLOBAL]* — LIVE·gap → `elements/ingest-gate.md`  · ↓ `#ingest-gate`
2. **security-ingest-gate** *[GLOBAL]* — LIVE → `elements/security-ingest-gate.md`  · ↓ `#security-ingest-gate`
3. **egress-allowlist-wall** *[GLOBAL]* — LIVE·gap → `elements/egress-allowlist-wall.md`  · ↓ `#egress-allowlist-wall`
4. **hook-plane** *[GLOBAL]* — PARTIAL → `elements/hook-plane.md`  · ↓ `#hook-plane`
5. **canon** *[GLOBAL]* — PARTIAL·gap → `elements/canon.md`  · ↓ `#canon`
6. **save** *[GLOBAL]* — PARTIAL → `elements/save.md`  · ↓ `#save`
7. **memory-read** *[GLOBAL]* — PARTIAL (honor) → `elements/read.md`  · ↓ `#memory-read`
8. **journal** *[GLOBAL]* — PARTIAL (honor) → `elements/journal.md`  · ↓ `#journal`
9. **claude-md-pyramid** *[GLOBAL]* — PARTIAL·gap → `elements/claude-md-pyramid.md`  · ↓ `#claude-md-pyramid`
10. **pm-flag** *[GLOBAL]* — PARTIAL·gap → `elements/pm-flag.md`  · ↓ `#pm-flag`
11. **gws-plane** *[GLOBAL]* — LIVE·gap → `elements/gws-plane.md`  · ↓ `#gws-plane`
12. **pulse-cron** *[GLOBAL]* — LIVE·gap → `elements/pulse-cron.md`  · ↓ `#pulse-cron`
13. **grand-central** *[GLOBAL]* — PARTIAL·gap → `elements/grand-central.md`  · ↓ `#grand-central`
14. **safe-reader-plane** *[GLOBAL]* — LIVE·gap → `elements/safe-reader-plane.md`  · ↓ `#safe-reader-plane`
15. **sentinel** *[GLOBAL]* — LIVE·gap → `elements/sentinel.md`  · ↓ `#sentinel`
16. **email-service** *[GLOBAL]* — PARTIAL [provisional] → `elements/email-service.md`  · ↓ `#email-service`
17. **item-store** *[GLOBAL]* — LIVE·gap → `elements/item-store.md`  · ↓ `#item-store`
18. **skill-system** *[GLOBAL]* — PARTIAL → `elements/skill-system.md`  · ↓ `#skill-system`
19. **project-manager** *[GLOBAL]* — PARTIAL (honor) → `elements/project-manager.md`  · ↓ `#project-manager`
20. **scratch-capture-gate** *[GLOBAL]* — LIVE·gap → `elements/scratch-capture-gate.md`  · ↓ `#scratch-capture-gate`
21. **helm** *[GLOBAL]* — LIVE·gap → `elements/helm.md`  · ↓ `#helm`
22. **health-invariants** *[GLOBAL]* — LIVE·gap [provisional] → `elements/health-invariants.md`  · ↓ `#health-invariants`
23. **archivist** *[GLOBAL]* — PARTIAL·gap → `elements/archivist.md`  · ↓ `#archivist`
24. **two-machine-residency** *[GLOBAL]* — PARTIAL [provisional] → `elements/two-machine-residency.md`  · ↓ `#two-machine-residency`
25. **notify-plane** *[GLOBAL]* — LIVE [provisional] → `elements/notify-plane.md`  · ↓ `#notify-plane`
26. **backlog-authority** *[GLOBAL]* — PARTIAL → `elements/backlog-authority.md`  · ↓ `#backlog-authority`
27. **label-checker** *[GLOBAL]* — LIVE·gap → `elements/label-checker.md`  · ↓ `#label-checker`
28. **build-plan-plane** *[GLOBAL]* — LIVE (honor) → `elements/build-plan-plane.md`  · ↓ `#build-plan-plane`
29. **plan-integrity-cluster** *[GLOBAL]* — PARTIAL [provisional] → `elements/plan-integrity-cluster.md`  · ↓ `#plan-integrity-cluster`
30. **research-web-plane** *[GLOBAL]* — PARTIAL [provisional] → `elements/research-web-plane.md`  · ↓ `#research-web-plane`
31. **ingest-run-lib** *[SHARED: emily/deryl/cron]* — DORMANT → `elements/ingest-run-lib.md`  *(index only — dormant)*
32. **git-autopush** *[GLOBAL]* — LIVE·gap → `elements/git-autopush.md`  · ↓ `#git-autopush`
33. **strategic-navigation-cluster** *[GLOBAL]* — PARTIAL [provisional] → `elements/strategic-navigation-cluster.md`  · ↓ `#strategic-navigation-cluster`
34. **statusline-hud** *[GLOBAL]* — LIVE·gap [provisional] → `elements/statusline-hud.md`  · ↓ `#statusline-hud`
35. **council-engine** *[GLOBAL]* — LIVE·gap → `elements/council-engine.md`  · ↓ `#council-engine`
36. **translator-cluster** *[GLOBAL]* — PARTIAL [provisional] → `elements/translator-cluster.md`  · ↓ `#translator-cluster`
37. **red-team** *[GLOBAL]* — LIVE [provisional] → `elements/red-team.md`  · ↓ `#red-team`
38. **topic-vocab-lint** *[GLOBAL]* — DORMANT → `elements/topic-vocab-lint.md`  *(index only — dormant)*
39. **compute-mechanically-gate** *[SHARED: deryl/clair/finance]* — DORMANT → `elements/compute-mechanically-gate.md`  *(index only — dormant)*
40. **emily-desk** *[DESK: emily]* — LIVE·gap [provisional] → `elements/emily-desk.md`  · ↓ `#emily-desk`
41. **marc-desk** *[DESK: marc]* — PARTIAL [provisional] → `elements/marc-desk.md`  · ↓ `#marc-desk`
42. **clair-desk** *[DESK: clair]* — PARTIAL·gap [provisional] → `elements/clair-desk.md`  · ↓ `#clair-desk`
43. **deryl-desk** *[DESK: deryl]* — PARTIAL [provisional] → `elements/deryl-desk.md`  · ↓ `#deryl-desk`
44. **cal-pipeline** *[DESK: cal]* — PARTIAL → `elements/cal-pipeline.md`  · ↓ `#cal-pipeline`
45. **dobby-desk** *[DESK: dobby]* — DORMANT → `elements/dobby-desk.md`  *(index only — dormant)*
46. **world-model-ingestion** *[GLOBAL]* — ~~DORMANT~~ **LIVE** → `elements/world-model-ingestion.md`  ~~*(index only — dormant)*~~ *(index line only — LIVE)*  ⚠ **CORRECTED 2026-08-15.** The element file carries `maturity_label: LIVE` plus its own note — *"no longer inactive as of 2026-08-06 (the skill is built and running on a live corpus)"* — so this manual line's DORMANT was stale. Both read this session; the element is authoritative on its own maturity. The struck text stays visible because this manual asserted it.
47. **overmyshoulder** *[GLOBAL·optional]* — DORMANT → `elements/overmyshoulder.md`  *(index only — dormant)*
48. **calculate** *[SHARED: deryl/clair/manual]* — DORMANT → `elements/calculate.md`  *(index only — dormant)*
49. **google-sheet** *[GLOBAL·optional]* — DORMANT → `elements/google-sheet.md`  *(index only — dormant)*
50. **hospital** *[GLOBAL]* — PARTIAL·gap [provisional] → `elements/hospital.md`  · ↓ `#hospital`
51. **efficiency** *[GLOBAL]* — PARTIAL·gap [provisional — not fire-tested] → `elements/efficiency.md`  · ↓ `#efficiency`

---

## ELEMENT ENTRIES — the "how it works together" narratives (per `map-format-specs.md §8.5`)

> Each non-trivial element: a `## <slug>` entry — one-line purpose + a TYPED INTEROP SEAM LIST (compress words, never seams). Seam-verbs = the closed set in §8.3. Derived from each element's own INTEROP SEAMS (2026-07-24 fan-out).

## ingest-gate · every safe_* tool call   [LIVE·gap]   → elements/ingest-gate.md
Python gate inside the door — sanitize → injection-scan → Sentinel-verdict pipeline called by every safe_* tool after the hook allows entry. Distinct from security-ingest-gate (the hook wall); these two compose.

INTEROP:
  CHAINS     security-ingest-gate   · hook plane fires first; redirects to safe_* tools which call gate()
  READS      sanitize               · L0 scrub (system/tools/sanitize.py); gate imports it directly
  READS      safe_input             · injection scanner (system/tools/safe_input.py); gate imports it directly
  TRIGGERS   sentinel               · sentinel_response.py called on any findings (non-empty scan result)
  WRITES→    ingest-provenance      · breadcrumb ledger ($DRIVE/state/status/ingest-provenance.jsonl) on every gate call
  FEEDS      ingest-reader          · on FLAG/CLEAN, safe_* tools write cleared content to /tmp/rdr for the tool-less reader subagent
  SHARES     email_convert          · email_convert.py calls gate(source_type="email") → enforces FLAG-floor invariant
  SHARES     safe_calendar/tasks    · safe_calendar.py and safe_tasks.py call gate(source_type="calendar"/"api") — same pipeline
  COMPLEMENTS sentinel              · sentinel_response.py is the verdict arbiter; gate is the pipeline; hook is the wall — three layers
  SYNCS      ingest-gate-signature  · frozen contract v1.0 in system/schemas/ingest-gate-signature.md; any change requires schema bump + Window-3 sign-off
  GUARDED-BY security-ingest-gate   · ingest_gate_enforce.sh forces callers through safe_* tools, which causes gate() to be called

## security-ingest-gate · ingest_gate_enforce.sh   [LIVE]   → elements/security-ingest-gate.md
Sanitize/gate every external-read channel so no unsanitized, attacker-authorable content ever reaches the model's context. One hook subsumed six scattered per-channel deny hooks — a REDIRECT gate, not a wall.

INTEROP:
  COMPLEMENTS  safe-reader-plane     · gate = the wall (blocks + redirects); safe tools = the clean door (L0-sanitize + injection-scan); the pair is the full control
  CHAINS       ingest-reader         · denies tool-holding main session any scratch read; lets tool-less subagent (agent_id set) through — reader has nothing to act with
  FEEDS        sentinel              · downstream of safe tools; the danger gate that refuses flagged content; provenance_route breadcrumbs flow from every read
  WRITES→      state/email-summary/threads-v2/   · enforces single-writer invariant on the email-summary store (non-janitor writes blocked)
  WRITES→      state/item-store/     · enforces single-writer invariant on the item-store (non-writer writes blocked)
  GUARDED-BY   ingest_gate_enforce.sh   · PreToolUse on Bash/WebFetch/WebSearch/Read — the hook itself IS this element; fail-closed on unparseable input

## egress-allowlist-wall · always-on   [LIVE·gap]   → elements/egress-allowlist-wall.md
Block every outbound network call to a host not on the allowlist — so a hijacked session cannot exfiltrate data. ~~Three independent hook layers (L1 credential-exfil, L2 domain name-check, L3 raw-tool block) plus an OS-layer LuLu backstop~~; ·gap because dynamic-URL and env-var-credential paths are fail-open.
⚠ **CORRECTED 2026-08-15 — the in-process domain seal was ARMED. It still ships OFF.** There is now a FOURTH mechanism beside the three hook layers: the in-process seal inside `system/tools/safe_fetch.py`. The operator ruled it (`authority: user` — *"APPROVED — ARM IT"*). A persistent switch file `system/safe-fetch-allowlist.md` (same ALLOWLIST-START/END markers as `system/egress-allowlist.md`), a `l2_state()` resolving every read to **three named outcomes and no quiet fourth** — **OFF** (allowed, and it says so on stderr once per process) · **ON** (off-list host refused *before the socket opens*) · **AMBIGUOUS** (**refused**) — with the `SAFE_FETCH_ALLOWLIST` env var as the **per-run** seal outranking the file, which is the **persistent** switch a human sets by hand. `--l2-status` reports the switch position without fetching. `system/tools/test_egress_level2.py` holds 12 tests, passing inside `system/tools/run-all-tests.sh`.
⛔ **DO NOT READ THIS AS "THE EGRESS WALL IS NOW ENFORCED."** It ships `off` with an empty domain block and no caller arms it, so **by default it seals nothing.** The honest claim — do not exceed it — is **armed and switchable, ships OFF, refuses loudly when half-configured.** Never "enforced," never "protected." What changed is that the level you are actually at is now knowable and stated out loud; not that a wall went up.
⚠ **Two things did NOT change.** (1) The Bash-command domain hook still **fails OPEN, deliberately** — it sits in front of *every* Bash command, where a false positive stops ordinary work and somebody unregisters the guard; the in-process seal sits in front of web reads only and is off unless deliberately armed. (2) The OS firewall (LuLu) remains the only HARD wall of the three, and is still not carried here.
⚠⚠ **A NUMBERING COLLISION — carry it or you will state something false.** This map and `system/organism/elements/egress-allowlist-wall.md` number the layers **L1 = `guard_egress.sh`** (credential-exfil) · **L2 = `enforce_egress_allowlist.sh`** (the Bash-command domain hook) · **L3 = `ingest_gate_enforce.sh`** (raw WebFetch/WebSearch deny). The shipped code and `docs/OUTSIDE-SERVICES.md` number a *different* ladder: **Level 1 = the Bash-command domain hook** (this map's L2) · **Level 2 = the in-process `safe_fetch.py` seal** · **Level 3 = the OS firewall**. So *"Level 2 is now armed"* means **the in-process seal, NOT the Bash hook.** Neither numbering is wrong; they count different things. Full statement: `system/organism/elements/egress-allowlist-wall.md`.

INTEROP:
  COMPLEMENTS  security-ingest-gate   · ingest-gate redirects inbound raw WebFetch/WebSearch to safe tools; this wall gates those tools' outbound Bash calls — together they close the adversarial loop
  FEEDS        sentinel               · enforce_egress_allowlist.py appends a structured block record to sentinel-events.jsonl on every off-allowlist denial; sentinel-health.py rolls that into the dashboard tile
  READS        helm                   · health_invariants.py names guard_egress.sh as a CRITICAL invariant; absence triggers a CRITICAL health failure — the wall is wired into system liveness monitoring
  COMPLEMENTS  research-web-plane     · safe_search_api.sh + safe_fetch.py are the ONLY permitted outbound tools; this wall is what structurally forces them to be the sole path (L3 blocks raw WebFetch/WebSearch)
  FEEDS        research-web-plane     · /tmp/serper_calls_YYYYMMDD.log (written by safe_search_api.sh) is the shared daily call-cap counter across all callers
  SYNCS        notify-plane           · ntfy.sh is an approved domain in egress-allowlist.md; removing it would sever push notifications
  SYNCS        gws-plane              · googleapis.com / google.com / gstatic.com / googleusercontent.com are all in egress-allowlist.md; the allowlist entries are what structurally permit gws-plane traffic
  COMPLEMENTS  two-machine-residency  · egress-allowlist.md and egress-allowlist.hosts are git-tracked and travel to both machines via git push/pull; LuLu sync remains manual
  READS        label-checker          · conformance-lab fire-tests guard_egress.sh + enforce_egress_allowlist.sh with synthetic probes to produce the LIVE/PARTIAL verdict; the checker makes LIVE a meaningful claim
  GUARDED-BY   guard_egress.sh · enforce_egress_allowlist.sh · ingest_gate_enforce.sh   · the walls that fire here

## hook-plane · system/hooks/ + settings.json   [PARTIAL]   → elements/hook-plane.md
The system's immune layer — the registered guard fleet across the hook event categories that intercept every Claude tool call at runtime to enforce behavioral invariants autonomously, without asking the human. PARTIAL because not all doctrine rules are hook-backed.

INTEROP:
  GUARDED-BY  save               · guard_write_paths · guard_canon_write · guard_ledger_discipline wall every write /save performs
  GUARDED-BY  canon              · guard_canon_write enforces authority:user + no stale content on every write to any **/canon/** file
  GUARDED-BY  project-manager    · guard_ledger_discipline protects state/debt-ledger.md; guard_throughline_write_scope gates /throughline scratchpad writes
  GUARDED-BY  skill-system       · enforce_skill_frontmatter blocks a malformed SKILL.md at birth; guard_write_paths blocks Write/Edit to ~/.claude/skills/
  GUARDED-BY  organism-map       · guard_organism_map blocks full-content Write to system/organism/manual.md and map-format-specs.md
  GUARDED-BY  gws-plane          · block_primary_calendar · guard_tasks_writes · guard_sheet_writes · guard_sheet_formula_writes · guard_gws_logout wall every gws write
  GUARDED-BY  security-ingest-gate · ingest_gate_enforce.sh IS the security-ingest-gate element's physical body; hook-plane is the enforcement carrier
  READS       egress-allowlist-wall · enforce_egress_allowlist.sh/py reads system/egress-allowlist.md on every Bash call
  WRITES→     sentinel           · enforce_egress_allowlist.py appends blocked-host events to system/logs/sentinel-events.jsonl on every deny
  FEEDS       skill-system       · auto_register_skill writes ~/.claude/commands/<name>.md stub after a desk SKILL.md write
  FEEDS       organism-map       · nudge_flow_drift reads system/organism/elements/*/generated_from and emits advisory when an edited file is cited there
  FEEDS       helm               · observability_logger (all tools) appends to /tmp buffer; session_flight_recorder flushes to system/observability/YYYY-MM-DD.jsonl at Stop
  FEEDS       validate           · validate_on_write reads each written file via validate_frontmatter.py; advisory today, TARGET is blocking
  FEEDS       claude-md-pyramid  · session_context_loader reads desks/{desk}/canon/*.md + state/telos.md and injects into session context at SessionStart
  SHARES      pm-flag            · pm_persist.sh reads ~/.claude/run/pm/pm-sess-<id>.flag (written by pm_flag.sh) every turn
  SHARES      project-manager    · pm_persist.sh injects the active brief's SCRATCHPAD section every turn; brief is the shared file
  SHARES      skill-system       · skill_anchor_inject.sh reads ~/.claude/run/anchor/anchor-<key>.flag (written by skill_anchor.sh) every turn
  SHARES      build-plan-plane   · announce_plan_write monitors ~/.claude/plans/ and injects pointer to new plans; plan file store is shared
  FEEDS       save               · save_routing_hint injects routing context on save-phrase; reads pm_flag status to route correctly
  GUARDED-BY  build-plan-plane   · guard_plan_structure blocks malformed ExitPlanMode; plan_flag.sh record arms the plan flag; both fire on ExitPlanMode
  FEEDS       helm               · plan_flag.sh (armed by ExitPlanMode hook) writes ~/.claude/run/plan/plan-<key>.flag; statusline.sh reads it for the HUD
  WRITES→     helm               · session_flight_recorder flushes observability buffer → system/observability/YYYY-MM-DD.jsonl + system/flight-log.jsonl
  FEEDS       save               · session_flight_recorder nudges /save at Stop when it was not called
  WRITES→     two-machine-residency · mirror_plans.sh rsyncs ~/.claude/plans/ → Drive/plans/<hostname>/ at every Stop
  READS       project-manager    · scratch_capture_gate.sh reads pm_flag status at Stop to resolve the active brief's SCRATCHPAD; bounces turn on token bucket overflow
  KEYS-OFF    two-machine-residency · settings.json IS the hook-plane's own registration store; travels to both machines via git symlink; broken symlink silently darkens every hook
  FEEDS       label-checker      · hook-plane's settings.json + guard scripts are the input source label_checker.py reads and fire-tests
  FEEDS       sentinel           · hook scripts + settings.json registration are artifacts sentinel's health checkers read for the Security tile
  GUARDED-BY  egress-allowlist-wall · guard_egress + enforce_egress_allowlist gate all raw outbound Bash calls; the egress-allowlist-wall element is the downstream policy store these hooks enforce
  FEEDS       claude-md-pyramid  [deprecated-in-place] · translator_gate.sh was the voice-compliance grading gate (Stop); the Haiku grader was RETIRED per [TRANSLATOR-GATE-RIP] 2026-07-14; hook remains registered but does not enforce
  FEEDS       rating-capture     · rating_capture.sh (UserPromptSubmit) writes system/learnings-signals.jsonl + system/learnings/ failure files; quality-signal store downstream of hook-plane

## canon · canon/   [PARTIAL·gap]   → elements/canon.md
Human-vetted top trust tier — always-loaded floor of durable memory; `guard_canon_write.sh` mechanically enforces `authority: user` as the human-promotion signal. The manual /save gate IS the feature (Divergence-1), not a gap.

INTEROP:
  GUARDED-BY  guard_canon_write.sh      · primary canon write wall — blocks non-authority:user Writes and wrong-authority Edits to any /canon/ path (PreToolUse, exit 2)
  GUARDED-BY  guard_write_paths.sh      · residency wall fires first — confirms canon path is inside $DRIVE before guard_canon_write runs
  READS       session-context-loader    · SessionStart hook injects desk canon branch (or root canon) into every session — the always-on floor
  READS       read                      · /read Step 0.6 lazy-canon walk loads canon most-specific-first on demand; scope must stay in lockstep with canon_conflict_scan.py
  READS       canon-audit               · deep-reads entire desk canon tree on seven dimensions; read-only, never writes
  READS       save                      · Step 4.6 runs canon_conflict_scan.py against target tree before any canon-bound write; fail-closed
  PROPOSES    save                      · /save Step 6b routes confirmed canon candidates → records/proposals/ (vetted:false); guard does not fire on proposals/ path
  PROPOSES    ingest-filer              · routes canon-candidates to records/proposals/ with separate confirmation key; same store, independently enforced
  READS       archivist                 · archivist reads records/proposals/ as inbound promotion queue; proposes placement via archivist-route; never writes canon/ directly
  WRITES→     archivist-audit           · weekly headless run regenerates system/canon-purpose-map.md — the territory-map cache; sole managed archivist write in the clone
  READS       archivist-route           · reads system/canon-purpose-map.md (not live canon tree) to rank correct canon home; cache staleness between archivist runs is a known correctness risk
  READS       council                   · spawns per-desk subagents each loading only their own desk canon tree — enforces structural desk isolation
  SYNCS       canon_conflict_scan.py    · conflict scan and /read lazy-canon must walk the same ladder scope; a drift silently admits duplicates at save-time
  COMPLEMENTS validate_on_write.sh      · PostToolUse advisory; fires after any Write/Edit; non-blocking frontmatter nudge (topic: gap not caught here)

## save · /save   [PARTIAL]   → elements/save.md
Turn what happened in a session into durable, correctly-filed memory — with a human gate on anything permanent. Canon WRITE is hook-walled; the residual honor surface is the model's routing choice and journal-first discipline.

INTEROP:
  SHARES       checkin              · both write the same brief.md ## SCRATCHPAD (checkin harvests notes in; /save alone runs the 8-step pad_archive.py compaction against {brief}.pad-archive.md); canonical definition in project-doc-schema.md
  SHARES       project-manager      · all three read/write ## SCRATCHPAD / ## STORY LOG / ## CURRENT STATE; FRAME is human-only across all
  WRITES->     archivist            · canon candidates land in records/proposals/ (vetted:false) as the Archivist's inbound promotion queue
  WRITES->     journal              · system/journal.md is the append-only backstop and mandatory transit point for the Cal pipeline; journal-first is a precondition
  COMPLEMENTS  scratch-capture-gate · scratch_capture_gate.sh pushes interim captures autonomously; SC-4 F5.6 sweeps the final delta at session-close; complementary not redundant
  FEEDS        backlog              · Steps 7c.5/7c.6 stamp type: + state: on every debt entry; the backlog groomer consumes those stamps ~0-LLM
  CHAINS       plan-flag            · plan_flag.sh arms the plan; pm_persist.sh injects it every turn; Step 8 Wake Routine emits the /checkin copy-paste line using the absolute path
  READS        project-registry     · Step 0.5 resolves slug→folder via system/project-registry.md; all project-aware skills share this identity source
  SYNCS        read                 · canon_conflict_scan.py (Step 4.6) scope must match /read's lazy-canon ladder; a conflict visible to /read must be visible at save time
  GUARDED-BY   guard_canon_write.sh · blocks Write/Edit to **/canon/** lacking authority:user — canon can't be silently written
  GUARDED-BY   guard_write_paths.sh · residency wall on ALL /save stores; fails CLOSED on unparseable input
  GUARDED-BY   guard_ledger_discipline.sh · blocks adding RESOLVED/✅/DONE lines to ## Open; forces deletion-not-annotation
  GUARDED-BY   scratch_capture_gate.sh · Stop hook; fires once per ~100k-token bucket when an active pad exists; emits decision:block
  GUARDED-BY   pm_persist.sh        · UserPromptSubmit; injects active brief + flag reminders every turn
  GUARDED-BY   save_routing_hint.sh · UserPromptSubmit; intercepts "save this" natural-language triggers; routes to scratchpad or forces ASK

## memory-read · /read | /checkin | /project-manager invocation   [PARTIAL (honor)]   → elements/read.md
Rehydrate the right slice of durable memory into a session so context is never rebuilt from scratch. Manual/directed by design — the session floor is auto-loaded; /read is the directed top-up.

INTEROP:
  READS      save                   · /save WRITES-> the records/journal/canon/briefs /read consumes; /save alone runs the compaction engine (pad_archive.py on the pad-archive file)
  KEYS-OFF   pm-flag                · pm_flag.sh is the project-routing identity hub; every project-aware skill (save, read, checkin, pm) keys off it; break → silent degraded room-scan
  READS      canon                  · $DRIVE/{desk}/canon/**/*.md loaded by session_context_loader (floor) + /read Step 0.6 (lazy walk); read is ungated
  GUARDED-BY guard-canon-write      · guard_canon_write.sh walls the WRITE side; /read reads canon freely — correct by design
  READS      journal                · /read Step 2b reads last-20 journal slice for desk/slug; /checkin + project-manager WRITE-> same journal (journal-first rule)
  WRITES→    journal                · /checkin Step 3.6 + project-manager append to journal BEFORE overwriting the brief (journal-first; honor-system ordering)
  SHARES     save                   · both read/write $DRIVE/{project_path}/brief.md; FRAME is human-only; ## SCRATCHPAD + ## STORY LOG are the mutable sections
  SHARES     project-manager        · all three (save/read/pm) read/write brief.md; pm creates; /checkin updates; /save compacts
  READS      project-registry       · $DRIVE/system/project-registry.md is the slug→path resolver; /read Step 0.6 + /checkin Step 0 key off it; /save + pm WRITE-> new rows
  SYNCS      session-context-loader · session_context_loader.sh pre-loads desk canon at SessionStart; /read Step 0.6 must skip same-desk canon already loaded (honor-system dedup)
  COMPLEMENTS archivist             · archivist WRITES-> and PROPOSES to records + canon; /read surfaces what archivist filed — full curation cycle
  READS      huddle-board           · /checkin Step 1.5 reads huddle channel via huddle.py mine; flag files + message data at $DRIVE/state/huddle/
  FEEDS      planning               · /checkin journal-first writes (Step 3.6) feed planning-diary-capture.py; skip = starves the planning pipeline silently
  READS      telos                  · $DRIVE/state/telos.md pre-loaded by session_context_loader; /read deduplicates (honor-system)
  GUARDED-BY ingest_gate_enforce    · PreToolUse Read/Bash — BLOCKS external reads; passes all internal trusted-zone .md reads freely (correct by design)
  GUARDED-BY guard_write_paths      · PreToolUse Write|Edit — /checkin brief + journal writes stay in approved Drive paths
  COMPLEMENTS scratch-capture-gate  · scratch_capture_gate.sh (Stop hook) bounces the turn at 100k-token boundaries when pad capture is due; reads the pm-flag-armed brief path as its scratchpad target

## journal · system/journal.md   [PARTIAL (honor)]   → elements/journal.md
The single append-only event log — the common backstop all write paths must hit before touching any mutable file, and the sole source the Cal pipeline reads for its daily diary. Journal-first ordering is [honor]-only; residency wall is hook-enforced.

INTEROP:
  WRITES→  save              · /save Steps 7, 7d, SC-5 each append ledger rows or SESSION CONTEXT blocks; mandatory transit before any brief or canon write
  WRITES→  checkin           · Step 3.6b append-only journal-first write before/as the brief Story Log is updated
  WRITES→  project-manager   · journal-first hard rule: dead-end, decision, or key number written to brief must hit journal first (same Edit, never deferred)
  WRITES→  marc-desk         · marc-sensor appends one TRIP row per VIX regime escalation; marc-pulse-journal appends one market-pulse line per slot/day — both via Python file I/O outside the hook plane
  FEEDS    planning-diary-capture  · planning-diary-capture.py reads journal.md as the only cross-desk narrative source for each day's Machine Recap (ONLY transit point, by design)
  FEEDS    planning-diary-rollup   · planning-diary-rollup.py reads journal.md for period-range aggregations (weekly/monthly/quarterly/yearly) by desk + by slug
  READS    read               · /read Step 0 loads a journal slice filtered by desk or slug; surfaces gap-since-last-entry staleness signal; mandates coverage disclaimer
  READS    distill            · pulls last 30 journal rows for the target desk as one of its named source streams
  READS    throughline        · reads last ~10 journal rows for a slug tagged failed:/DEAD END/PIVOT as the storyline-and-failure source for its sub-agent
  READS    marc-checkin       · reads recent marc-desk journal rows as the session-orient source (market trips and weekly wraps)
  READS    archivist-audit    · uses journal-newer-than-brief as a staleness check (N. stale-brief rule)
  GUARDED-BY   guard_write_paths   · PreToolUse: allows Write/Edit to Drive path; blocks Write/Edit to the clone-side copy — residency enforcement

## claude-md-pyramid · session-init   [PARTIAL·gap]   → elements/claude-md-pyramid.md
Always-loaded system-prompt stack (global cap + root doctrine + per-desk doctrine) plus the SessionStart hook that injects Drive-side canon, TELOS, and the pulse brief. ·gap because Bash writes bypass the write-guard and a failed hook silently drops the entire Drive-side floor.

INTEROP:
  COMPLEMENTS  read                   · /read's Step 0.6 explicitly skips loading desk canon when session_context_loader.sh already injected it at SessionStart — the pyramid injects the floor; /read builds on top without double-loading
  GUARDED-BY   guard-write-paths      · guard_write_paths.sh (PreToolUse Write|Edit) explicitly allows writes to ~/.claude/CLAUDE.md and clone CLAUDE.md paths (exit 0) — it does NOT block CLAUDE.md writes but does block restricted content paths
  GUARDED-BY   guard-canon-write      · guard_canon_write.sh (PreToolUse Write|Edit) protects the Drive-side canon stores that session_context_loader.sh injects as the session floor; a poisoned canon write would corrupt every future session
  GUARDED-BY   guard-organism-map     · guard_organism_map.sh (PreToolUse Write) blocks wholesale Write overwrites of system/organism/manual.md and map-format-specs.md — the host files that reference this element's entry
  READS        save                   · /save Step 6 WRITES behavioral rules back into CLAUDE.md files via Edit; the pyramid is the always-on reader of those rules; /save is the authorized writer
  READS        canon                  · session_context_loader.sh reads desks/{desk}/canon/*.md and records/canon/*.md on every SessionStart; the pyramid is the intake point for the canon store into the session
  KEYS-OFF     hook-plane             · the SessionStart hook registration in system/reference/settings.json is what makes session_context_loader.sh fire; a corrupted entry silently disables Layer 2
  SYNCS        two-machine-residency  · ~/.claude/CLAUDE.md is tracked by parity-check.sh as a PARITY_FILE; the symlink target travels by git pull; settings.json carrying the SessionStart registration is also parity-tracked
  READS        telos                  · session_context_loader.sh reads state/telos.md at every SessionStart; /telos is the sole documented writer; the pyramid is the always-on injection path
  READS        pulse-cron             · session_context_loader.sh reads state/pulse-brief.md on every SessionStart; the pyramid is the sole consumer; the writer is currently UNKNOWN (open loop OL-4)
  READS        archivist              · Archivist proposes placements to desks/{desk}/canon/*.md and records/canon/*.md — the exact stores the pyramid loads; approved proposals (via /save) directly alter what the next session sees

## pm-flag · pm_flag.sh arm/status/clear   [PARTIAL·gap]   → elements/pm-flag.md
The singleton on/off switch that tells the whole organism which project brief is currently active — armed by skills, re-injected every turn, read by every hook that routes saves, HUD tiles, plan announces, and session-close captures. Hub, not wall: pm-flag does not block anything on its own; it is a routing-state source read by the gates and skills that do the actual work.

INTEROP:
  TRIGGERS    project-manager    · /project-manager calls pm_flag.sh arm after intake/interview identifies doc path/slug/desk — NOT as the first step; intake comes first [honor]
  TRIGGERS    checkin            · /checkin has two paths: front-door args → arm immediately; no args → status check first then arm after resolution; /read re-arms on rehydrate [honor]
  TRIGGERS    design-lifehack   · /design-lifehack discovery SOP references pm_flag.sh arm for project activation [honor]
  READS       save               · /save Step 0 calls pm_flag.sh status to route the write; Step 0.4 calls pm_flag_recover.py to recover a dropped flag from arm-events.log; re-arms on success to refresh TTL [honor]
  READS       scratch-capture-gate · scratch_capture_gate.sh calls pm_flag.sh status as fallback pad resolver when no scratch_flag is armed; pm brief becomes Stop-gate scratchpad target [hook]
  READS       hook-plane         · announce_plan_write.sh calls pm_flag.sh status unconditionally each turn; save_routing_hint.sh calls it only when prompt matches a save-request phrase; scratch_sweep_nudge.sh calls it only when scratch_flag is not armed [hook]
  SYNCS       plan-flag          · pm_persist.sh refreshes plan-<KEY>.flag armed_at every turn via _refresh_armed_at; /advisory-council reads plan_flag.sh path alongside pm_flag.sh status to build the settled-ground card [honor]
  SYNCS       scratch-flag       · pm_persist.sh refreshes scratch-<KEY>.flag armed_at every turn via _refresh_armed_at [hook]
  READS       huddle-flag        · pm_persist.sh reads huddle-<KEY>.flag each turn to inject BUILD CLOSE-OUT nudge for active huddle sessions; huddle TTL applied is PM_TTL_HOURS [hook]
  READS       huddle             · /huddle and /huddle-board call pm_flag.sh status to locate the active project brief before posting or cross-referencing [honor]
  READS       advisory-council   · /advisory-council calls pm_flag.sh status AND plan_flag.sh path before convening advisors to build the settled-ground card from active brief and plan [honor]
  READS       helm               · statusline.sh reads the pm flag to compose the proj: HUD tile (slug + freshness color) and desk: bottom-bar field (TRUTH CONTRACT: desk field shows desk, never slug) [honor for read]
  GUARDED-BY  guard_statusline_lock.sh · PreToolUse Bash hook blocks Bash commands that destroy or repoint the statusline script that reads the pm flag; flag store itself (~/.claude/run/pm/) has no PreToolUse write guard [hook]

## gws-plane · gws   [LIVE·gap]   → elements/gws-plane.md
Single, locked, Bash-only conduit for all Google Workspace reads and writes — binary, auth, capability tiers, write-guard stack, and per-channel ingest wrappers that sanitize untrusted content before it enters context. MCP calendar write bypass is the live gap.

INTEROP:
  GUARDED-BY  guard_gws_logout.sh             · blocks auth destruction (`gws auth logout`) from any session — root backstop (PreToolUse Bash, exit 2)
  GUARDED-BY  block_primary_calendar.sh       · all calendar writes must target Agent Ops calendar; fires on gws Bash only — MCP calendar calls bypass entirely (·gap)
  GUARDED-BY  guard_sheet_writes.sh           · Sheets write requires LLM_GUIDE tab read first; destructive ops need LIFEHACK_SHEET_CONFIRM=1
  GUARDED-BY  guard_sheet_formula_writes.sh   · blocks formula injection in Sheets cell values
  GUARDED-BY  guard_tasks_writes.sh           · protects Life Map from agent writes; Daily Win subtask carve-out only
  TRIGGERS    ingest-gate                     · ingest_gate_enforce.sh fires on every gws Gmail/calendar/tasks/drive-export Bash call — unified on-path enforcement arm
  READS       google-capability-registry.yaml · tiers + risk classes + per-desk access model
  READS       gws-contract.md                 · canonical invocation patterns, auth rules, zsh quoting rules
  READS       google-policy.md                · prohibitions, admin exception, guarded capability list
  WRITES→     planning                        · calendar events read/write through this plane
  WRITES→     email-ingest                    · Gmail reads through this plane via email_convert.py / email_service_read.py
  WRITES→     sheets-desks                    · Sheets reads/writes (deryl DFM, clair billing, reconcile) through this plane
  FEEDS       safe_calendar.py                · gws-plane invokes; wrapper sanitizes calendar event free-text before it enters context
  FEEDS       safe_tasks.py                   · gws-plane invokes; wrapper sanitizes task title/notes
  FEEDS       email_convert.py                · gws Gmail body goes through email_convert.py / email_service_read.py before reaching model context
  KEYS-OFF    settings.json permissions.deny  · `gws auth logout`, auth login, ~/.config/gws/ all deny-listed at the permission layer
  SYNCS       grand-central                   · Google-touching skills route through desks that invoke this plane
  COMPLEMENTS security-ingest-gate            · ingest_gate_enforce.sh overlaps — the ingest gate IS the on-path enforcement arm of this plane for read channels

## pulse-cron · crontab */5   [LIVE·gap]   → elements/pulse-cron.md
One crontab line ticks pulse.sh every 5 minutes; it reads the jobs block in pulse-config.md and fires any job whose interval has elapsed, with machine-local circuit-breaker safety, single-writer machine-gating, and a Drive-mirrored heartbeat feed. The Bash-write bypass gap (guard_write_paths.sh matches Write/Edit only) is accepted.

INTEROP:
  TRIGGERS     system-health        · dispatches system-health-run.sh → reads _pulse-*.json + pulse-config.md to detect missed runs
  TRIGGERS     archivist            · fires archivist-audit/deepmine-run.sh on their respective intervals
  TRIGGERS     emily-breakdown      · fires emily-breakdown-run.sh; ingest runner contract via ingest-run.lib.sh
  TRIGGERS     clair-ingest         · fires clair-ingest-run.sh; ingest runner contract via ingest-run.lib.sh
  TRIGGERS     deryl-ingest         · fires deryl-ingest-run.sh; ingest runner contract via ingest-run.lib.sh
  TRIGGERS     marc-pipeline        · fires marc-weekly/wednesday/deadman-run.sh; marc-research-lib.sh contract
  TRIGGERS     email-service        · fires email-summary-write-run.sh + email-summary-freshness-run.sh
  TRIGGERS     grand-central        · fires tasks-store-sync-run.sh + calendar-store-sync-run.sh
  TRIGGERS     sentinel             · fires sentinel-health-run.sh → reads sentinel-events.jsonl → tile
  TRIGGERS     git-sync             · fires git-autopush + git-autopull (keeps both machines' clone in sync)
  READS        two-machine-residency · reads state/primary-machine on every writer-runner tick via require_primary
  READS        pulse-config.md      · reads the ```jobs block every tick for the job schedule manifest
  WRITES->     durable-status-plane · writes state/status/_pulse-{machine}.json + _pulse.json heartbeat mirrors after every cycle
  WRITES->     durable-status-plane · runner jobs write state/status/{desk}.json tiles via emit_status.py
  WRITES->     learnings-store      · Pulse trims system/learnings.md sections older than 90d; /save appends
  WRITES->     observability        · observability-trim job deletes system/observability/*.jsonl older than 30d
  WRITES->     maintenance-log      · hook-doc-lint job is the sole writer of system/logs/maintenance-due.md (honor-system pickup by sessions)
  FEEDS        helm                 · _pulse-*.json glob drives dashboard freshness + per-job heartbeat tiles
  FEEDS        helm                 · state/status/*.json tiles drive per-desk health cards
  FEEDS        marc-pipeline        · marc_research_run + marc_material_change_scan stamp desks/marc/organism/heartbeat/last-run.json; marc-deadman reads it
  FEEDS        planning             · planning-vault-weekly-run.sh writes desks/cal/state/weekly-vault/ → planning-weekly-analyze-run.sh consumes (⚠ desks/cal/ is DELIBERATE — code/jobs/tiles renamed to planning, the records directory was NOT)
  FEEDS        email-service        · email-summary-write-run.sh → state/email-summary/threads-v2/ (faithful thread store)
  FEEDS        grand-central        · item-store jobs → state/item-store/tasks/ + state/item-store/calendar/ (sole writers)
  SYNCS        two-machine-residency · git-autopush/pull keep pulse-config.md in sync; NOTE: git-autopull does not call install-schedulers.sh — manual install required after pull
  FEEDS        security-posture-scan · pulse-config.md is read by security-posture-scan.sh to verify supabase jobs stay disabled + emily stays enabled
  COMPLEMENTS  notify-plane         · pulse.sh calls notify-send.sh directly for circuit-breaker trips + no-lead nag; all *-run.sh runners channel alerts through notify-send.sh
  COMPLEMENTS  health-deadman-check · launchd watcher (BY DESIGN outside Pulse) watches system-health tile mtime; catches a dead Pulse+health chain that no Pulse job could detect
  GUARDED-BY   require_primary      · single-writer safety on all Drive-writing jobs (ingest-run.lib.sh + primary-gate.sh + inline copies)
  GUARDED-BY   ingest_acquire_lock  · prevents stacked runs per job; single-instance enforcement in every claude-invoking runner
  GUARDED-BY   circuit breaker (pulse.sh) · auto-disables a job after 3 consecutive non-transient failures; rc=2 never trips it
  GUARDED-BY   ingest_check_paused  · Sentinel danger verdict → human-gated source pause; no auto-resume
  GUARDED-BY   guard_write_paths.sh [hook] · blocks Write/Edit tool calls to status stores from a session (NOT from the pulse subprocess; Bash-write bypass gap accepted 2026-07-14)
  GUARDED-BY   ingest_gate_enforce.sh [hook] · fires inside claude -p sessions launched by runners; blocks raw external reads + gws body reads

## grand-central · Pulse-dispatched email/tasks/cal writers   [PARTIAL·gap]   → elements/grand-central.md
Pulse-dispatched headless runners pull Gmail threads, Google Tasks, and Calendar events and write faithful, schema-validated, injection-scanned records to Drive-backed v2 stores — the single authoritative write path for all three channels.

INTEROP:
  FEEDS      email-service          · state/email-summary/threads-v2/ is the exclusive store email_service_read.py serves to the 4 ingest desks; grand-central is sole Pulse writer
  FEEDS      planning               · item_store_read.read_item("calendar") reads state/item-store/calendar/ for event payloads; grand-central (calendar_store_sync.py) is sole Pulse writer
  FEEDS      planning               · item_store_read.read_item("task") reads state/item-store/tasks/ for task payloads; grand-central (tasks_store_sync.py) is sole Pulse writer
  WRITES→    helm                   · state/status/email-summary.json written by email_summary_sync.py via stamp_write_success() after RC=0; read by freshness runner for local DEGRADED notification
  FEEDS      item-store-freshness-runner  · grand-central's output stores (item-store/tasks/, item-store/calendar/) are the input item_store_read.py --freshness-check reads; that runner writes state/status/item-store.json
  TRIGGERS   notify-plane           · write-runners and freshness-runners call notify-send.sh on ERROR/DEGRADED; grand-central is a direct trigger source on every write failure
  GUARDED-BY security-ingest-gate   · ingest_gate_enforce.sh blocks direct Read of threads-v2/ and item-store/, and blocks non-janitor Write to those paths; session boundary only (not headless cron)
  KEYS-OFF   pulse-cron             · all three writers and both freshness runners registered in pulse-config.md; Pulse is the sole trigger source for the write paths
  SHARES     security-ingest-gate   · email_convert.py, ingest_gate.py, safe_input.py (in-degree 17), and intake_reader.py are shared library components used by grand-central's Python writers AND by security-ingest-gate's redirect targets

## safe-reader-plane · safe_*/email_convert cluster   [LIVE·gap]   → elements/safe-reader-plane.md
Every byte of external content — web, email, calendar, tasks, documents, search results — passes through a two-layer filter (L0 deterministic scrub + heuristic injection scan) before the model reads it, and a hook plane blocks every raw-read bypass. ~~Egress allowlist is structurally present but functionally unarmed [EGRESS-WALL-FAILOPEN].~~
⚠ **CORRECTED 2026-08-15.** "Functionally unarmed" is no longer true of the in-process seal in `system/tools/safe_fetch.py` — it was built out and made switchable (the operator, `authority: user`). The honest claim, and do not exceed it: **armed and switchable, ships OFF, refuses loudly when half-configured** — never "enforced," never "protected," because it ships `off` with an empty domain block and no caller arms it. ⚠ *"Level 2 is armed"* means **that in-process seal**, NOT the Bash-command hook this map calls L2 — the two ladders are numbered oppositely; see the collision note under `## egress-allowlist-wall` above. The `[EGRESS-WALL-FAILOPEN]` gap itself is UNCHANGED and still stands: the Bash-command domain hook still fails OPEN, deliberately.

INTEROP:
  GUARDED-BY   ingest_gate_enforce.sh   · PreToolUse hook plane on Bash/WebFetch/WebSearch/Read that forces all external reads through the safe-reader cluster
  READS        sanitize.py / safe_input.py   · L0 deterministic scrub + heuristic injection scan — the shared core every channel tool runs
  FEEDS        security-ingest-gate     · provenance_route breadcrumbs from every read flow to the on-path Sentinel gate
  CHAINS       ingest-reader            · tool-less reader consumes /tmp/rdr/* scratch files written by safe_calendar.py / safe_tasks.py (reader-actor split)
  COMPLEMENTS  egress-allowlist-wall    · safe_fetch.py's _enforce_egress_allowlist is one layer; OS-layer LuLu firewall is a parallel backstop
  WRITES→      state/email-summary/threads-v2/   · email_convert.py (via janitor) writes the faithful-thread store
  WRITES→      state/item-store/        · calendar/tasks store syncs write; item_store_read.py adapts reads
  READS        email_service_read.py    · the read adapter for the v2 faithful-thread store (wraps re-scan + refuse-flagged + tool-less-reader routing)
  KEYS-OFF     system/security-canon.md · reader-actor split contract + channel classification lives there
  COMPLEMENTS  websearch               · /websearch skill wraps safe_search_api.sh ~~(primary) + safe_search.sh (Chrome fallback)~~ for interactive sessions
                                        ⚠ **CORRECTED 2026-08-15.** safe_search_api.sh is not "primary" — it is the ONLY search path. There is no Chrome fallback: `safe_search.sh` and the whole dev-browser path were DELETED by ruling (the operator, authority: user — *"Research should never go into Chrome… that's an old leftover thing"*). The file is gone from the tree; verified absent this session. The struck text is left visible because it was true of the donor.

## sentinel · ingest-path   [LIVE·gap]   → elements/sentinel.md
Classify every inbound scan finding as CLEAN / FLAG / DANGER; on DANGER pause the source, push a phone alert, and reversibly quarantine the Gmail message — then write to an append-only event ledger and refresh the security dashboard tile. ·gap because NTFY push and Gmail quarantine are fail-open via env-var test-disable flags, and the email FLAG-floor is caller-convention not hook-enforced.

INTEROP:
  FEEDS        pulse-cron             · sentinel-events.jsonl is the source for sentinel-health.py (a Pulse job); Pulse polls every ~1800s and rewrites the tile with stale_after_s=86400 — sentinel produces the event record; Pulse produces the tile refresh
  TRIGGERS     notify-plane           · on DANGER: sentinel_response.notify_danger() calls notify-send.sh (critical NTFY push); suppressed if reader_verdict=="BENIGN" (honor-only suppression)
  WRITES->     helm                   · sentinel_response.write_tile() + sentinel-health.py write state/status/sentinel.json; security-health.py composes that into state/status/_security.json; Helm's Security tab reads both tiles
  WRITES->     email-service          · on DANGER with a Gmail message-id: sentinel_quarantine.py applies the Sentinel/Quarantine Gmail label (reversible; non-Gmail items have no wiring — gap)
  SHARES       egress-allowlist-wall  · sentinel-events.jsonl is the shared append-only event ledger; egress-allowlist-wall writes block events there (enforce_egress_allowlist.py appends on every off-allowlist denial); sentinel-health.py reads it — sentinel is the shared event store for both inbound-injection and outbound-block classes
  FEEDS        ingest-coverage        · sentinel-events.jsonl is the fallback coverage source when ingest-provenance.jsonl is absent; ingest_coverage.py switches automatically
  SYNCS        helm                   · sentinel_ack.py refreshes sentinel.json immediately on each ack; Helm's dismiss overlay (sentinel-dismissed.json) must stay in sync with the tile's event ids — a stale tile produces stale dismiss state
  GUARDED-BY   hook-plane             · security-ingest-gate (ingest_gate_enforce.sh, PreToolUse Bash/WebFetch/WebSearch/Read) routes every external read through the sanitizer stack before sentinel sees findings; enforce_egress_allowlist.sh + guard_egress.sh fire on every Bash invocation in the ingest harness

## email-service · email_service_read.py / read_thread()   [PARTIAL [provisional]]   → elements/email-service.md
The sanctioned, security-layered READ path for the per-thread faithful store — every desk reads email through read_thread(), never directly from the store files. Distinct from grand-central (the WRITE side): grand-central is the Pulse-dispatched janitor that writes faithful records; this element is only the read adapter.

INTEROP:
  READS       grand-central      · grand-central writes threads-v2/{thread_id}.json that read_thread() reads; ONE-WAY: janitor writes, adapter reads; schema changes require co-ordination via shared email_thread_schema
  FEEDS       deryl-desk         · deryl-ingest uses read_thread() as store-first read path; body-via-scratch for tooled sessions, body-inline for read-only; live wiring per-desk status UNVERIFIED
  FEEDS       emily-desk         · Emily ingest uses read_thread() as store-first read path; Cal and Emily are tooled (isolate=True by default) — body lands in /tmp/rdr, must spawn ingest-reader
  FEEDS       clair-desk         · Clair ingest uses read_thread() as store-first read path
  FEEDS       planning           · Cal ingest uses read_thread() as store-first read path; the planning desk is tooled, body isolation applies
  CHAINS      ingest-reader      · for any tooled desk or flagged thread, read_thread() writes body to /tmp/rdr/ and sets reader_required=True; controller MUST spawn tool-less ingest-reader on scratch_path
  GUARDED-BY  ingest_gate_enforce.sh · Ra-2 scratch-dir lock blocks main/controller session Read of /tmp/rdr/*; sub-agent (has agent_id) is allowed — the sanctioned reader-actor path; HOOK UNVERIFIED on the second machine
  READS       email_service_contract.py · janitor imports SUMMARY_MODEL · MAX_WORKERS · entrypoint pins at startup; validate_contract() greps tree for single-writer invariant; import fail → hard-stop
  KEYS-OFF    email-summary health tile · reads state/status/email-summary.json in _store_is_stale() to classify a miss as MISS-NEW vs MISS-SYNCLAG
  FEEDS       email-fallback-events.jsonl · every store miss that routes to raw fallback appended to state/status/email-fallback-events.jsonl via _log_fallback()
  SYNCS       email_thread_schema.py · both the janitor's write path and read_thread() Step 3 import email_thread_schema; load-bearing assertion: message_count == len(messages)
  SYNCS       ingestion-reader-contract.md · adapter's _write_scratch() must stay in sync with the contract's scratch-dir path format, MARKER prefix, and scan-verdict semantics

## item-store · item-store   [LIVE·gap]   → elements/item-store.md
Drive-backed flat-file mirror of Google Tasks and Calendar events — read exclusively through a security adapter that routes structured fields inline and isolates third-party free-text to /tmp/rdr scratch; hook wall enforces single-writer access. Python callers passing isolate=False are the accepted design gap.

INTEROP:
  READS       grand-central           · READS safe_tasks.py + safe_calendar.py (via subprocess, --redact flag) — raw gws output never lands in the store; grand-central owns the write-side sync runners that populate the store
  WRITES→     grand-central           · grand-central's tasks_store_sync.py + calendar_store_sync.py are the sole writers; item-store is the read side — complementary halves of the same mirror
  WRITES→     state/item-store/       · tasks_store_sync + calendar_store_sync write one .json per record atomically
  WRITES→     state/status/item-store.json · freshness dead-man emits hourly tile via emit_status.py (Pulse slot item-store-freshness)
  WRITES→     /tmp/rdr/               · read adapter writes isolated free-text scratch for the tool-less ingest-reader on every isolate=True read
  FEEDS       item_store_window.py    · time-window sweep calls iter_item_dates() + read_item(); composes tasks + calendar + email into one read_window() call
  FEEDS       email-service           · item_store_window.py composes both adapters — email-service is the sibling adapter for the email store
  FEEDS       planning                · planning-daily + planning-weekly call item_store_window.py instead of hitting Google live; the store is the query layer
  FEEDS       hitl_note_store.py      · bundle mode checks HITL note store per item; a matching note may replace the raw item body before bundling
  KEYS-OFF    ingest-gate             · ingest_gate_enforce.sh hook wall (PreToolUse Bash + Read) makes the adapter the only read path in; without it the security model is advisory
  GUARDED-BY  ingest_gate_enforce.sh  · direct Read of state/item-store/ BLOCKED; un-wrapped Bash reads BLOCKED; non-writer Bash writes BLOCKED — all three rules live inside this hook
  SYNCS       item_schema.py          · both sync writers AND the read adapter import from item_schema.py; a schema change propagates to all four modules
  COMPLEMENTS email-service           · email store and item store share doctrine (verbatim mirror, single writer, adversarial free-text, lifecycle states) but are independent stores with independent adapters

## skill-system · new-skill.sh / SKILL.md write   [PARTIAL·gap]   → elements/skill-system.md
Full lifecycle of a Lifehack skill — from scaffolded birth, through frontmatter enforcement and slash-command registration, to every-turn anchor re-injection that keeps a leading skill on-frame across a long session. Birth conformance is hook-enforced; behavioral quality and shape compliance are honor-system.

INTEROP:
  SHARES       project-manager      · skill_anchor.sh + skill_anchor_inject.sh are a direct architectural mirror of pm_flag.sh + pm_persist.sh (flag state manager + UserPromptSubmit injector); same session-key scheme, TTL, degrade-safe posture
  FEEDS        save                 · /save's Step 7b (machine-log) and Step 7c (learnings) record skill-related events when a session runs a skill and then saves
  FEEDS        label-checker        · conformance-lab's multi-phase driver contracts (## Output contract + ✅ phase N complete) are the machine-readable seam conformance.py reads; new-skill.sh --multiphase creates this seam at birth
  TRIGGERS     auto_register_skill.sh · a Write or Edit to desks/{desk}/skills/{name}/SKILL.md automatically triggers stub creation; /save may trigger this if it writes a SKILL.md
  CHAINS       skill_anchor.sh → skill_anchor_inject.sh · anchor state manager arms a flag; injector reads it every turn; useless without each other
  READS        system/sops/skill-building-sop.md · canonical doctrine for all skill authoring; the hook's deny message names it explicitly
  SYNCS        docs/skill-conformance.md · frontmatter schema (shape:, emit_diary:, etc.) canonicalized here; changes must land in conformance doc first; hook and scaffolder updated in same commit
  READS        system/templates/skill-template/SKILL.md · canonical template new-skill.sh was designed from; scaffolder's stamp IS the template's required structure
  GUARDED-BY   enforce_skill_frontmatter.sh · PreToolUse Write — exit-2 BLOCKS non-conformant SKILL.md writes (description + YAML + 500-line cap); Write-only (not Edit)
  GUARDED-BY   skill_anchor_inject.sh · UserPromptSubmit — re-injects lean anchor body every turn when armed; DEGRADE-SAFE
  GUARDED-BY   auto_register_skill.sh · PostToolUse Write|Edit — creates desk command stubs automatically; non-blocking (stderr only)

## project-manager · /project-manager | "track this" | build invocation   [PARTIAL (honor)]   → elements/project-manager.md
Arm a session-scoped flag → re-inject the active brief on every turn → run HITL Frame intake on create → compact the scratchpad losslessly at close → block the Stop event until capture is confirmed. Primary behavioral contract is honor-system; only the Stop-capture gate is a real blocker.

INTEROP:
  SHARES     save                   · /save runs the BRIEF COMPACTION (pad_archive.py → pad-archive → CLEAR) — sole authorized compactor, at session-close
  SHARES     checkin                · /checkin appends harvested notes to the same ## SCRATCHPAD (and confirmed decisions to the Story Log) but never compacts; only /save fires the compaction engine (pad_archive.py), at session-close
  WRITES→    journal                · project-manager writes system/journal.md JOURNAL-FIRST before overwriting the brief on any direct update — journal is the only append-only backstop
  READS      pm-flag                · pm_persist.sh reads the armed doc_path from the flag to inject the Current-State excerpt into every turn
  COMPLEMENTS announce_plan_write   · announce_plan_write.sh (UserPromptSubmit) writes a plan pointer line into ## SCRATCHPAD when a NEW plan file appears and pm-flag is armed; falls back to plan-ledger.md when no brief active
  FEEDS      read                   · /read resolves slug via project-registry.md, loads {path}/brief.md as primary rehydration source, re-arms pm-flag — the brief is the memory chunk /read delivers
  WRITES→    project-registry       · project-manager writes a new slug→path row into system/project-registry.md on first project creation; /save + /checkin + /read all resolve the brief path from that row
  COMPLEMENTS scratch-capture-gate  · scratch_capture_gate.sh reads the pm-flag-armed brief path as its fallback scratchpad target at Stop; brief's ## SCRATCHPAD is what the gate inspects
  FEEDS      archivist              · archivist-audit reads brief.md ## FRAME and ## STORY LOG, compares brief.md updated_at against newest journal line for the slug (staleness signal)
  FEEDS      council-engine         · /advisory-council calls pm_flag.sh status to locate the active brief and builds the settled-ground card from FRAME / desired-outcome + DECISION BOARD
  FEEDS      build-plan-plane       · project-manager records a Current plan pointer in ## SCRATCHPAD and links the plan path; build-plan-plane likely picks up the linked plan via pm_persist injection
  GUARDED-BY guard_write_paths      · guard_write_paths.sh (PreToolUse Write|Edit) gates all Write/Edit to the brief path; allows Drive-root paths, blocks everything else; does NOT check section content or archive status

## scratch-capture-gate · scratch_capture_gate.sh   [LIVE·gap]   → elements/scratch-capture-gate.md
Prevent session-memory loss by blocking every turn-end (once per ~100k-token bucket) when the active scratchpad has un-captured work — forcing the model to surface an ADDED-lines receipt before the turn can complete. Receipt content is model-executed, not mechanically verified [honor].

INTEROP:
  COMPLEMENTS  save              · both target the same ## SCRATCHPAD section; gate captures continuously (~100k-tok bucket); /save SC-4 F5.6 does the final delta-capture at session-close — not redundant, they interlock (gate populates, F5.6 closes)
  READS        pm-flag           · reads pm_flag.sh status → brief path (secondary pad resolver; fires when scratch_flag = none or empty PAD)
  READS        scratch-flag      · reads scratch_flag.sh status → armed state + scratch_path (primary pad override; armed externally, 30m TTL)
  SHARES       project-manager   · the active brief's ## SCRATCHPAD is this gate's target pad; pm_persist.sh injects the brief + flag every turn, refreshing pm_flag for this gate; pm_flag_recover.py repairs a dropped pm_flag this gate depends on
  KEYS-OFF     hook-plane        · Stop-event registration in settings.json is what arms this gate at all; deregistering it silently disables all continuous capture for the session

## helm · localhost:8080   [LIVE·gap]   → elements/helm.md
Local web dashboard that renders every desk's live status tile — the read-only face of the system, always showing what Pulse last emitted, never inventing data. ·gap because the server has five write-back POST endpoints that persist to Drive (dismiss overlays, location, emily re-emit) — a tip-only reader treating Helm as purely read-only misjudges the blast radius.

INTEROP:
  FEEDS        every desk emitter     · every desk's *-health.py calls emit_status() to write its tile; Helm reads it — the tile contract is the seam
  READS        pulse mirror           · Helm reads _pulse*.json to derive STALE and circuit-breaker ERROR; Aliveness writes these mirrors
  FEEDS        system-health sweeper  · system-health.py emits _system-health.json which Helm surfaces as the System tab passthrough via build_state()
  TRIGGERS     sentinel-health.py · archivist-placements.py · archivist-lean.py   · the sweeper calls these as child processes on each run (graceful, non-blocking)
  READS        desk-registry.yaml     · system-health.py derives DESKS and drift-cop checks from the registry; load_registry() is graceful (returns [] on failure)
  FEEDS        health_invariants.py   · invoked by system-health.py; checks substrate integrity and appends to state/health.jsonl
  KEYS-OFF     pulse-config.md        · system-health.py loads job intervals from the same config Aliveness dispatches from (CODE_ROOT, not Drive — avoids stale job-list drift)
  CHAINS       emily-emit.py          · POST /api/emily/dismiss calls _reemit_emily() which runs emily-emit.py to rebuild emily.json from the store; the next /api/state poll reflects it
  COMPLEMENTS  verify-connections.py  · the readiness scorecard is the emit→served audit tool; Helm's render-pixel check is the complementary half

## health-invariants · system-health.py + health_invariants.py   [LIVE·gap [provisional]]   → elements/health-invariants.md
Assert five structural invariants and sweep every Pulse job for missed runs — on any breach, push a phone alert and surface a BROKEN tile on the Helm dashboard; the out-of-band dead-man's-switch watches the sweeper itself from outside Pulse so silence is never mistaken for health. Gap: Invariant 4 fires BROKEN on legitimate machine-offline (no lead-aware suppression); FRESH_TILES is a residual hand-maintained shadow list.

INTEROP:
  TRIGGERS    pulse-cron         · Pulse dispatches system-health-run.sh every 300s — the sweeper IS a Pulse job, living inside the thing it watches (out-of-band launchd watcher is the escape hatch)
  READS       pulse-cron         · _pulse-*.json heartbeat files — the raw evidence the sweeper assesses for missed-run detection
  WRITES→     helm               · _system-health.json feed (schema_version:2) — Helm's Cron tab and front page render this; shape is frozen
  WRITES→     (ground-truth log) · state/health.jsonl — append-only invariant record; survives tile lies; not consumed by any UI today
  READS       egress-allowlist-wall · guard_egress.sh presence is one of the four CRITICAL_HOOKS asserted by Invariant 1; tampering detected by Invariant 2
  READS       hook-plane         · all guard hook files in system/hooks/guard_*.sh — Invariant 1 checks presence; Invariant 2 checks git-committed (untampered) state
  READS       sentinel           · state/status/sentinel.json tile consumed by sentinel_fold() in the sweeper; Sentinel DANGER escalated to need_attention[]
  READS       security-ingest-gate · desk-registry.yaml reads_external field — Invariant 5 / drift-cop coverage check (when INGEST_COVERAGE_FLAG=on)
  COMPLEMENTS sentinel           · Sentinel detects INBOUND injection; health-invariants detects SUBSTRATE failure — parallel, non-redundant
  CHAINS      archivist          · sweeper spawns archivist-placements.py + archivist-lean.py as side-effects post-sweep (decoupled + graceful; failure never blocks sweep)
  READS       grand-central      · state/primary-machine — lead-machine detection in system-health-run.sh and _current_lead()
  SYNCS       (desk-health producers) · FRESH_TILES and assess_registry() must stay in sync with desk-registry.yaml when new desks are added

## archivist · /archivist-*   [PARTIAL·gap]   → elements/archivist.md
Read-only knowledge-health scanner and placement oracle — detects structural drift + misplacements, proposes corrections, routes placement candidates; never writes durable content except its own territory-map index and controlled log outputs. Cron jobs currently in ERROR; Bash-write bypass is the primary gap.

INTEROP:
  FEEDS       save                    · archivist log files (audit/deepmine/declutter queues in $DRIVE/system/logs/) feed /save — next /save picks up FLAGS; archivist-review intermediary is RETIRED
  FEEDS       archivist-route         · audit WRITES→ system/canon-purpose-map.md; archivist-route READS it as primary territory index (Step 1 of routing)
  READS       save                    · /save Step 7e drops AMBIGUOUS content pointers into $DRIVE/system/archivist/insight-inbox/; NOTE: inbox is currently undrainable — archivist-inbox skill retired 2026-07-11, items accumulate with no downstream consumer
  READS       archivist-declutter     · declutter reads $DRIVE/system/archivist/home-intents.md for per-home admission bars before each line-level pass
  WRITES→     helm                    · archivist-run.lib.sh _write_tile() writes $DRIVE/state/status/archivist.json after each run; archivist-lean.py + archivist-placements.py also write sub-keys; Helm reads the tile
  FEEDS       helm                    · archivist-placements.py reads autoplace-ledger.md to populate recent_placements[] in archivist.json (data stale — autoplace retired)
  TRIGGERS    pulse-cron              · pulse-cron (*/5) fires archivist-audit-run.sh + archivist-deepmine-run.sh on their registered intervals via pulse-config.md
  KEYS-OFF    two-machine-residency   · archivist-run.lib.sh reads $DRIVE/state/primary-machine on every tick; stands down if not the lead machine (single-writer safety; [ARCHIVIST-AUDIT-DEAD] known wrong design)
  CHAINS      archivist-route         · deepmine synthesis chains into archivist-route to rank homes for each promotable insight; route reads territory map only — not home-intents.md
  COMPLEMENTS save                    · archivist is the scanner (DETECT + PROPOSE); /save is the writer (EXECUTE + GATE) — two halves of the knowledge-health loop
  GUARDED-BY  guard_write_paths.sh    · PreToolUse Write|Edit blocks out-of-bounds writes; Bash bypass documented (accepted 2026-07-14)
  GUARDED-BY  guard_canon_write.sh    · PreToolUse Write|Edit blocks any /canon/ write missing authority:user; enforces propose-only boundary on canon paths; same Bash bypass
  SYNCS       ingest-filer            · ingest-filer calls archivist-route inline (Step A of its routing procedure), which reads system/canon-purpose-map.md; territory map freshness gates ingest-filer routing quality
  READS       notify-plane            · archivist-run.lib.sh _ping() calls notify-send.sh → ntfy on each NEEDS_REVIEW result; notify-plane handles rate/dedup/quiet-hours gating

## two-machine-residency · Write/Edit tool call / git commit / Pulse 15 min   [PARTIAL [provisional]]   → elements/two-machine-residency.md
Code lives on GitHub and travels by git; content lives on Drive and travels by Drive sync; the two are kept separate by residency rules, a write-gate hook, and a pre-commit content-gate — and a primary-machine marker prevents two machines writing the same shared Drive state at the same time. Primary-gate is inlined in 6 runners rather than sourced (dedup debt).

INTEROP:
  TRIGGERS     guard_write_paths.sh · any Write|Edit tool call triggers the residency path-check hook
  TRIGGERS     check-content-paths.py · git commit in ~/lifehack-brain/ triggers gitleaks + content-gate pre-commit check
  TRIGGERS     pulse-cron           · Pulse tick (every 15 min) fires git-autopush.sh or git-autopull.sh
  TRIGGERS     mirror_plans.sh      · session end (Stop hook) triggers rsync of ~/.claude/plans/ → $DRIVE/plans/<hostname>/
  TRIGGERS     lifehack-lead.sh    · a human command flips the primary-machine marker between the primary and the second machine
  TRIGGERS     bootstrap-machine.sh · human runs bootstrap-machine.sh to wire all symlinks on a new machine
  READS        pulse-cron           · git-autopush/pull are registered Pulse slots (pulse-config.md); two-machine-residency owns their purpose in the sync model
  WRITES->     pulse-cron           · git-autopush/pull keep pulse-config.md in sync across machines; NOTE: git-autopull does not call install-schedulers.sh — manual install required
  FEEDS        notify-plane         · autopush circuit breaker fires a critical ntfy on 3+ consecutive push failures (P10)
  SYNCS        skill-system         · bootstrap-machine.sh creates all skill/agent/command symlinks; ~/.claude/skills/<name> symlinks point INTO the clone (correct direction)
  GUARDED-BY   guard_write_paths.sh · PreToolUse Write|Edit — BLOCKS content writes to clone, wrong-zone paths, orphan ~/.claude/skills/ writes; fails CLOSED on unparseable input
  GUARDED-BY   check-content-paths.py · pre-commit git hook — BLOCKS secrets (gitleaks) and content-class files in staging area; backstop for Bash-redirect writes that bypass guard_write_paths.sh
  GUARDED-BY   primary-gate.sh      · require_primary sourced by headless Pulse runners; return 1/exit 0 if not lead; fail-closed for scheduler conflicts
  GUARDED-BY   mirror_plans.sh      · Stop hook; rsyncs plans to Drive per-machine; always exits 0 (never blocks close)

## notify-plane · any component calling notify-send.sh   [LIVE [provisional]]   → elements/notify-plane.md
The single, governor-gated outbound push channel — every Lifehack alarm that reaches the user's phone passes through here and nowhere else. No hooks; structural enforcement by convention (all callers call the script; governor is called unconditionally inside it).

INTEROP:
  CHAINS     pulse                  · pulse.sh is the primary scheduler caller; notifies on no-lead + circuit-breaker trip
  CHAINS     system-health          · system-health.py calls notify-plane on newly-degraded jobs; critical on error-severity
  CHAINS     health-deadman         · health-deadman-check.sh calls notify-plane if system-health itself goes silent
  CHAINS     sentinel               · sentinel_response.py calls notify-plane (critical) on any scan hit; disableable via env
  CHAINS     pulse-circuit-breaker  · the breaker trip in pulse.sh fires notify-plane as its only outbound signal
  CHAINS     marc-sensor            · marc-sensor.py calls notify-plane on marc alert conditions
  CHAINS     marc-deadman           · marc-deadman.py calls notify-plane (critical) if marc-sensor goes silent
  CHAINS     archivist              · archivist-run.lib.sh calls notify-plane on archivist completion
  CHAINS     ingest-lib             · ingest-run.lib.sh calls notify-plane (critical) on no-lead-machine abort
  SHARES     notify-governor        · governor is a sub-component of notify-plane, not a separate interop peer

## backlog-authority · backlog_groom.py + backlog-health.py   [PARTIAL]   → elements/backlog-authority.md
Reads the typed system backlog (~0-LLM in steady state) and emits an honest DECOMPOSED count — actionable_debt (type:debt AND state:actionable) — to the Backlog dashboard tile; proposes grooming actions but never executes them. Supervised drain path is unbuilt (GAP-1).

INTEROP:
  READS    save              · triages off the type:/state: stamps /save writes onto debt-ledger rows; /save Steps 7c.5 and 7c.6 are the SOLE structured writer for debt-ledger ## Open
  FEEDS    helm              · backlog-health.py emits state/status/backlog.json; Helm Backlog tab reads it; work_count/work_noun (= actionable_debt) drive the KPI strip
  READS    open-loops        · groomer reads every desk's open-loops.md enumerated from system/desk-registry.yaml; _dupes() enforces one-home-per-item by detecting cross-file slug conflicts
  COMPLEMENTS  health-authority  · Health Authority answers "is the system RUNNING right?" (runtime); Backlog Authority answers "is the system TRACKING ITSELF right?" (backlog hygiene) — symmetric sibling organs, two tabs, no overlap
  COMPLEMENTS  archivist     · Archivist curates KNOWLEDGE; Backlog Authority curates WORK TRACKING — different data, different question; must not be conflated
  KEYS-OFF     desk-registry · groomer reads system/desk-registry.yaml for open_loops_path + backlog_mode; a desk missing from the registry is silently excluded
  KEYS-OFF     pulse-cron    · Pulse fires backlog-health-run.sh on a 6h interval; require_primary gate ensures single Drive writer
  GUARDED-BY   guard_ledger_discipline   · PreToolUse Write|Edit: blocks adding ✅/RESOLVED/CLEARED/FIXED annotation to ## Open — enforces deletion-not-annotation discipline structurally

## label-checker · manual CLI   [LIVE·gap]   → elements/label-checker.md
Fire-test every guard the self-schematic map claims is enforced against a synthetic violation and compute LIVE/PARTIAL/TARGET from the result; then stamp the computed label into the element file. ·gap because label_manifest.yaml is unguarded (Feature 1.6 not yet built) and the weekly cron that turns a downgrade into a phone-ping is not yet wired.

INTEROP:
  READS        hook-plane             · system/reference/settings.json is the canonical registration source; hook-plane owns this store; label-checker reads it to verify every claimed LIVE registration (two-machine truth by git-canonical path)
  READS        hook-plane             · system/hooks/*.sh — label-checker fires each guard script directly via bash stdin to assert it blocks (exit 2); hook-plane owns and maintains the hook fleet that label-checker fire-tests
  WRITES->     security-ingest-gate   · write-labels stamps maturity_label: + last_checked: into system/organism/elements/security-ingest-gate.md ## AUTO-COMPUTED from fire-test results (the reference LIVE element; the only element file stamped by write-labels today)
  GUARDED-BY   hook-plane             · guard_organism_map.sh (PreToolUse matcher=Write) blocks wholesale Write-tool overwrites of system/organism/manual.md and map-format-specs.md — the two files that carry the label criteria + format specs; Edit calls bypass by scope (matcher=Write only)
  FEEDS        archivist              · system/organism/elements/*.md are the shared store — label-checker stamps computed labels into element files; Archivist's weekly drift-check reads those same files to detect stale entries
  FEEDS        notify-plane           · label-checker exits non-zero (exit 1) on any downgrade; the weekly Archivist cron (TARGET — not yet wired) is the declared caller that turns that non-zero into a phone-ping via notify-plane
  COMPLEMENTS  conformance-lab        · conformance-lab (system/tools/conformance-lab/) also fires hook scripts against payloads via bash stdin; label-checker runs manifest-declared probes for map-honesty; conformance-lab runs adversarial bake-off suites for enforcement-tournament selection; neither reads the other's ground-truth file; neither subsumes the other

## build-plan-plane · /autoplan + /build   [LIVE (honor)]   → elements/build-plan-plane.md
The planning + execution contract — /autoplan structures the plan and /build executes it autonomously; together they enforce Phase → Feature → Task discipline with verified ✅ on every task. Primary behavioral contracts (continuation check, No-Silent-Demotion, Execute→Verify→✅, gear selection, honest close) are [honor]-only skill prose; plan-shape hooks are LIVE but enforce structure only at ExitPlanMode, not execution time.

INTEROP:
  READS       build-rules-index  · /build Step 0 reads system/build-rules-index.md to resolve which docs bind the build type
  READS       architecture-planning-sop · /autoplan prose directives; /build Step 0 ALWAYS doc — scoping front-end that produces the vetted handoff prompt
  READS       build-sop          · /build Step 0 ALWAYS doc; appended to when a build teaches a durable lesson (living doc)
  READS       build-conductor-sop · /build Step 0 for orchestrated/parallel builds; defines the four gears + worker loop
  FEEDS       project-manager    · /build files unbuilt tasks to OPEN LOOPS via project-manager at honest close
  CHAINS      project-manager    · /autoplan re-anchors via pm_flag.sh; plan's FRAME feeds the project brief
  FEEDS       plan-integrity-cluster · guard_plan_structure + plan_flag are the plan-integrity seam hooks — full per-hook mechanics cross-referenced there
  READS       pm-flag            · /autoplan Step 0 reads pm_flag.sh status to re-anchor; announce_plan_write reads pm_flag.sh status for brief path to write NEW plan pointer to brief's SCRATCHPAD
  WRITES→     durable memory (/save) · build lessons append to build-sop.md (skill's own living memory); plan mirrors to Drive via mirror_plans.sh
  GUARDED-BY  guard_plan_structure.sh · blocks ExitPlanMode if Phase/Task/Verify absent
  GUARDED-BY  inject_sop_before_build.sh · injects SOP pointer (advisory, non-blocking) at UserPromptSubmit on build-verb + tracked noun
  COMPLEMENTS advisory-council   · architecture-planning-sop.md Stages 1/4/6 invokes /advisory-council for blind review; /build does not invoke it directly
  COMPLEMENTS checkin            · /checkin re-arms plan_flag.sh via plan_flag.sh set <path> so a resumed window shows its plan
  COMPLEMENTS read               · /read arms plan_flag.sh on resume (same set call as /checkin)

## plan-integrity-cluster · ExitPlanMode/Stop/UserPromptSubmit   [PARTIAL [provisional]]   → elements/plan-integrity-cluster.md
Hook/enforcement layer that keeps every plan structurally correct, visible, backed up, and anchored to a durable flag — plans never vanish, fork silently, or miss Phase→Feature→Task shape before the user sees them. Fork prevention is honor-system only since guard_plan_fork.sh was retired 2026-07-15.

INTEROP:
  GUARDED-BY  guard_plan_structure.sh   · blocks malformed ExitPlanMode submissions — the ONLY hard gate in this cluster; exit 2 on missing Phase/Task/Verif markers; fail-open on empty plan
  COMPLEMENTS build-plan-plane          · build-plan-plane (/autoplan · /build skills) WRITES the plans this cluster guards, flags, backs up, and makes visible; plan-integrity-cluster is purely the enforcement/observability layer — never writes plan content
  COMPLEMENTS project-manager          · plan_flag.sh arms session plan identity; pm_flag.sh (project-manager) arms session project identity; pm_persist.sh refreshes BOTH flags' TTL every turn
  WRITES→     announce_plan_write.sh   · writes NEW-plan pointer lines into project-manager's owned ## SCRATCHPAD when pm_flag is armed; falls back to plan-ledger.md when not
  READS       plan_flag.sh             · /advisory-council reads plan_flag.sh path subcommand to load the active plan as advisory context before its council run
  READS       plan_flag.sh             · /save Step 8 (Wake Routine handoff) reads plan_flag.sh status to surface the active plan name in the continuation handoff
  SYNCS       mirror_plans.sh          · must stay in lockstep with the plan-recovery script on the pull side; both assume per-machine hostname namespacing under $DRIVE/plans/
  TRIGGERS    inject_sop_before_build.sh · fires before any build of a hook, skill, desk, sheet, dashboard, cron, or ingest pipeline — six domains whose SOPs live in system/sops/; NOT triggered before plan-content work
  KEYS-OFF    pm_persist.sh            · pm_persist.sh (project-manager element) refreshes plan_flag.sh's armed_at every turn so the plan flag never TTL-expires mid-session

## research-web-plane · /research / /websearch   [PARTIAL [provisional]]   → elements/research-web-plane.md
The sanitized web-research stack — two skills (/research, /websearch) that route all external web access through safe_search_api.sh / safe_fetch.py, with blind isolated subagents (the web-searcher agent type) STRUCTURALLY forced through the safe stack by tool restriction, so web content reaches context only after L0 + heuristic sanitization. Bias-control disciplines (blindness, isolation, distilled-verdict-only) are honor-system.

INTEROP:
  FEEDS        safe-reader-plane    · safe_search_api.sh, ~~safe_search.sh,~~ safe_fetch.py are shared primitives; safe-reader-plane OWNS the security model; research-web-plane USES them as its only network path; a change to safe_input.py or sanitize.py propagates to both
                                     ⚠ **CORRECTED 2026-08-15.** `safe_search.sh` is struck because it no longer exists: it and the whole Chrome/dev-browser path were DELETED by ruling (the operator, authority: user — *"Research should never go into Chrome… that's an old leftover thing"*). Verified absent from the tree this session. The shared primitives are safe_search_api.sh and safe_fetch.py; the struck name is kept visible rather than silently removed.
  GUARDED-BY   egress-allowlist-wall · guard_egress.sh (L1 credential-exfil) + enforce_egress_allowlist.sh (L2 domain allowlist) + ingest_gate_enforce.sh (L3 CLOSED WebFetch/WebSearch block) own the egress hooks; EGRESS-WALL-FAILOPEN gaps apply to both elements
  GUARDED-BY   ingest-gate          · ingest_gate_enforce.sh (PreToolUse WebFetch · WebSearch) is an ingest-gate mechanism; unconditional CLOSED deny on raw web tools for all sessions
  WRITES->     save                 · /research Step 7 writes an autonomous tier:dated-record research record to records/research/; /save's Step 4 dedup and Step 8 canon pipeline apply to it; complementary (research captures the map immediately; /save handles canon at session close)
  SYNCS        web-searcher         · /research Step 3 prompt skeleton, effort-tier rules, and tool constraints are tightly coupled to agents/web-searcher.md; the agent's tools:Bash,Read restriction is what makes the structural safe-stack claim true; must stay in sync
  COMPLEMENTS  security-ingest-gate · security-ingest-gate handles inbound external content (email, files); research-web-plane handles outbound-then-inbound web content; both feed into safe_input.py / sanitize.py shared primitives
  READS        CLAUDE.md            · global "Subagent Model Selection" rule mandates model:sonnet for all spawned agents; /research SKILL.md Hard rule 3 echoes this; CLAUDE.md is authoritative, SKILL.md is the runtime implementation

## git-autopush · Pulse every 900s (both machines)   [LIVE·gap]   → elements/git-autopush.md
Backstop auto-sync of ~/lifehack-brain between the two machines — push side sends new commits to GitHub; pull side fast-forwards the other machine — so a git commit propagates without ever asking the user to push. Conservative: handles clean fast-forward only; bails on anything requiring human judgment.

INTEROP:
  TRIGGERS   pulse-cron             · pulse.sh dispatches both jobs every 900s via cron
  READS      two-machine-residency  · ADR-010 git topology + the code/content split determines what these scripts own
  WRITES→    GitHub origin/main     · autopush sends local commits to the shared origin
  READS      GitHub origin/main     · autopull fetches + merges from origin
  FEEDS      hook-plane             · the git clone contains hooks registered in settings.json; a fast-forward lands updated hooks live on the receiving machine
  FEEDS      pulse-cron             · pulse.sh is itself stored in the clone; a pull updates pulse's own code on the next tick
  COMPLEMENTS bootstrap-sync        · bootstrap-machine.sh handles a full machine setup; this pair handles the delta-continuous sync
  GUARDED-BY pulse.sh circuit-breaker · 3 consecutive exit 1 → auto-disable + notify-send.sh buzz

## strategic-navigation-cluster · /first-principles + /telos + /throughline   [PARTIAL [provisional]]   → elements/strategic-navigation-cluster.md
Three orienting skills — diagnose → year-anchor → tension-surface — none of which writes code or executes work, two of which are structurally read-only. /checkin is homed in memory-read, not this cluster.

INTEROP:
  FEEDS        memory-read      · /telos updates state/telos.md; the memory-read element (/checkin) reads it as the whole-system desired-outcome anchor at root scope
  READS        project-manager  · /throughline reads the brief's ## DESIRED OUTCOME + ## DEAD ENDS when assembling the plot from the Cal diary (single-project scope) — reads only, never writes the brief
  READS        planning-diary   · /throughline reads desks/cal/diary/… rollups as the primary origin→now data source for diary-assembled plots (⚠ desks/cal/ is DELIBERATE — code/jobs/tiles renamed to planning, the records directory was NOT)
  FEEDS        execution-layer  · /first-principles produces a sharpened question / "build this first" / advisory structure the user carries into any execution skill; no runtime handoff — the artifact is verbal
  CHAINS       safe-reader-plane · /telos Life Map free-text is reader-actor isolated; /telos chains through safe_tasks.py (structured fields) → ingest-reader subagent (free-text) before consuming task notes
  GUARDED-BY   guard_throughline_write_scope   · PreToolUse Write|Edit: fires only while throughline_flag.sh is armed; hard-blocks any write outside the scratchpad dir during a /throughline run

## statusline-hud · every-turn   [LIVE·gap [provisional]]   → elements/statusline-hud.md
Always-on terminal status bar rendering model, context usage, session cost, active desk, armed project, active plan, and scratch state on every Claude Code turn. ·gap because the plan crosswire (mtime fallback picks wrong plan in multi-window sessions) is unresolved and the command-text guard cannot mechanically distinguish all Bash write patterns.

INTEROP:
  READS        pm_flag.sh flag store      · slug= and desk= fields → proj: HUD + desk: bar
  READS        plan_flag.sh flag store    · plan_file= basename → plan: HUD
  READS        scratch_flag.sh flag store · armed/not (30-min TTL) → scratch: on
  READS        skill_hud.sh hud store     · ~/.claude/hud/$SID.txt (6-h freshness) → top skill line
  KEYS-OFF     CLAUDE_CODE_SESSION_ID     · session key for all flag lookups; SHA(PWD) fallback when absent
  FEEDS        user terminal display      · rendered two-layer bar on every turn
  SYNCS        plan_flag.sh               · pm_persist.sh refreshes plan TTL every turn to prevent TTL expiry
  COMPLEMENTS  project-manager            · project-manager WRITES the pm_flag; this element READS it for display
  COMPLEMENTS  plan-integrity-cluster     · plan-integrity-cluster writes plan_flag via plan_flag.sh; this reads it for the HUD
  COMPLEMENTS  save                       · /save reads pm_flag.sh status for project routing (Step 0); statusline reads for display only
  GUARDED-BY   guard_statusline_lock.sh · statusline-truth-test.sh   · the walls that fire here

## council-engine · /advisory-council + /council   [LIVE·gap]   → elements/council-engine.md
Two skills sharing one blind-diverge → argue → converge protocol — /advisory-council runs a swappable roster cartridge (any subject, any desk) with advisors on opus; /council runs the five named desk lenses (cross-life decisions only) on sonnet. The engine is fixed; the advisors are the cartridge. No hooks registered for either skill — entire behavioral surface is honor-system.

INTEROP:
  TRIGGERS    architecture-planning-sop · SOP calls /advisory-council at Stages 1, 4, and 6 using the same roster cartridge; SOP's own subagents stay sonnet, only the advisors run opus
  TRIGGERS    planning-weekly    · planning-weekly Phase 4 IS the advisory-council engine — dispatches 6 member files as the advisor roster, running blind-diverge → argue → converge; members run opus
  TRIGGERS    marc-checkin       · marc-checkin Stage 2 optionally invokes /advisory-council on the market-analysis council (sonnet-locked, cost exception); never auto-summoned
  READS       pm-flag            · /advisory-council reads pm_flag.sh status + plan_flag.sh path at Stage 0 to build the settled-ground card from active brief and plan
  READS       pm-flag   · plan_flag.sh path sub-command (added 2026-07-21 for /advisory-council) returns plan file path for the settled-ground card
  FEEDS       save               · session output (plans, decisions, floor/integrated-plan artifacts) must go through /save → Archivist routing; council file is never written with findings
  READS       (desk canon)       · each /council subagent loads ONLY its own desks/{desk}/canon/*.md + state/current.md; independence is structural, signal quality depends on canon maintenance
  READS       councils/registry.md · front-door registry lookup on every /advisory-council invoke; Builder writes registry entries on create/edit

## translator-cluster · /condense · /explain · /summarize   [PARTIAL [provisional]]   → elements/translator-cluster.md
Three-skill cluster + two hooks that continuously re-assert a shared voice contract, keeping every reply readable on first pass for a low-recall reader juggling windows. The Stop-grade layer (translator_gate.sh) is dormant by default — grader parked 2026-07-14; inject hook is always-on.

INTEROP:
  COMPLEMENTS all-response-outputs      · ⛔ simplify_anchor_inject.sh was DELETED 2026-08-05 (failed experiment — fired EVERY turn, not 1-in-10). The per-turn voice re-anchor NO LONGER EXISTS; translator_gate.sh (Stop) still grades finished replies. This line claimed a live control for 9 days after it was switched off — §19's founding specimen. Was: fires before EVERY turn across every desk, skill, and agent — the voice contract for the entire system
  CHAINS      save                      · /save Step 8 continuation handoff specifies a two-pass DRAFT → /explain re-render as its voice-seed; the only place a translator skill is a REQUIRED intermediate step in another skill's flow
  KEYS-OFF    system/translator-rubric.md · all five cluster components (3 skills + 2 hooks) key off this file as the authority on translator voice; rubric edit must propagate to all five — propagation is honor-system
  SYNCS       output-styles/simplify.md · session-startup voice baseline; simplify_anchor_inject.sh is the per-turn re-anchor; both implement the same rubric criteria — out-of-sync means baseline and injection diverge mid-session
  COMPLEMENTS distill                   · /summarize explicitly routes full-thread or multi-turn distillations to /distill; complementary non-redundant tools for different scopes

## red-team · /red-team   [LIVE [provisional]]   → elements/red-team.md
Surface the glaring errors in a plan before they get expensive — no nitpicking, no perfection loops — ranked worst-first, with suggested fixes, then stop. Fully honor-system by design; a stateless one-shot needs no state, no hooks, no stores.

INTEROP:
  COMPLEMENTS  advisory-council     · advisory-council's Argue stage runs its own structured red-team round (advisor-vs-advisor over anonymized snapshot) — it does NOT call /red-team the skill; the two are distinct mechanisms for the same impulse
  COMPLEMENTS  research-web-plane   · /research maps convergence (what experts do); /red-team attacks the plan (does ours survive); run /research first, /red-team second when both are needed
  CHAINS       architecture-planning-sop · the SOP uses /advisory-council in pre-mortem mode at Stage 4 rather than /red-team directly; /red-team is the available utility for an ad-hoc pre-mortem outside the SOP formal gate — INFERRED
  COMPLEMENTS  council              · /council (convergence) and /red-team (critique) are orthogonal; run council to generate options, /red-team to punch holes in the winning option — UNVERIFIED

## emily-desk · new Emily-Ingest mail | /emily-* skills   [LIVE·gap [provisional]]   → elements/emily-desk.md
The audition/casting operating desk — ingest to breakdown to emit spine; the Relationship Ledger (Hollywood data layer); the cron/headless runner; and the Helm tile (HITL note store: planned/unverified). Contained subsystem with its own Google Sheets data layer, cron trigger, and Helm tile.

INTEROP:
  READS      email-service          · durable thread store (state/email-summary/threads-v2/) for Phase 0 body pull; store-first before raw gws
  FEEDS      helm                   · tile at state/status/emily.json via emily-emit.py; rich pending_auditions[] shape drives renderEmily() in app.js; required_payload contract enforced in emitter
  READS      gws-plane              · Gmail label list/modify, Sheets batchGet/batchUpdate, calendar events insert, Drive files update, docs create — full gws surface
  WRITES→    durable-memory         · breakdown Google Doc lands in "2026 Breakdowns" Drive folder; session.md + breakdowns markdown in desks/emily/state/; Relationship Ledger rows in the Sheet
  GUARDED-BY ingest-gate            · ingest_gate_enforce.sh blocks raw gws format:full body reads; forces email_convert.py path [hook]
  GUARDED-BY calendar-guard         · calendar write hook blocks any event write to primary or non-Agent-Ops calendar [hook]
  GUARDED-BY primary-gate.sh        · Drive writes on lead machine only [script]
  CHAINS     safe-reader-plane      · script-reader subagent uses safe_pdf.py; researcher uses safe_search_api.sh (Serper primary, Chrome fallback); calendar + email free-text isolated via safe_calendar.py / reader-actor subagent
  FEEDS      notify-plane           · buzz via notify-send.sh after successful breakdown (Phase 6)
  READS      pulse-cron             · emily-breakdown-run.sh is a Pulse-managed cron job; Pulse owns cadence + circuit-breaker (3 non-zero → auto-disable + buzz)
  CHAINS     emily-2-interrogate    · quick kill-filter + calendar gate on current session materials; reads session.md seeded by today's ingest; live interactive skill
  CHAINS     emily-ledger-write     · forensic ledger-write guard called by emily-1-ingest Step 6; 5 hard stops before any Sheet write; live interactive skill
  COMPLEMENTS hollywood-db          · shared/skills/hollywood-db is a distinct project (industry player database, Supabase-backed) sharing the Emily desk context; researcher reads the Relationship Ledger, not Hollywood DB directly during breakdown

## marc-desk · sensor→gather→narrative→checkin spine   [PARTIAL [provisional]]   → elements/marc-desk.md
Marc is a self-running market-intelligence organism — a daily data + tripwire plane, two weekly LLM-research rhythms, a falsifiable-projection/grade loop, a narrative registry, and a human HITL check-in (/marc-checkin) that is the only path that writes HIGH-confidence output. Machine writes LOW; human check-in writes HIGH.

INTEROP:
  WRITES→  journal           · every deep read (weekly + Wednesday) appends ONE LOW-confidence row; marc-sensor appends ONE row on a TRIP (new threshold cross)
  WRITES→  cal-diary         · /marc-checkin Stage 5 appends HIGH-confidence ## Human Delta — verified to desks/cal/diary/YYYY/MM/DD.md (the ONE high-confidence path)
  FEEDS    advisory-council  · /marc-checkin Stage 2 optionally convenes the 7-lens market council (sonnet seats, Marc chairs; never auto-summoned)
  READS    safe-reader-plane · 8 blind researchers call safe_search_api.sh (Serper) — the ONLY web path; no raw WebFetch/WebSearch/curl
  CHAINS   marc-grade.py     · Stage 0 of every deep read grades due projections before new ones are made (pure code, 0 LLM)
  COMPLEMENTS  marc-diary-write  · assembles the plain-text diary from already-existing data (no new LLM call); phone notifications link to this file
  KEYS-OFF     state/primary-machine · all gather runners + narrative-writer gate on this value (single Drive writer)
  SYNCS    emit_status()     · every runner writes a Pulse tile so the status bar reflects organism health
  TRIGGERS notify-send.sh    · sensor on CRITICAL cross · deadman on > 28h silence · weekly gather on success
  GUARDED-BY   guard_marc_narrative   · PostToolUse advisory lint on narrative/scenario file writes via marc-narrative-check.py (advisory, not blocking)

## clair-desk · /ingest + /clair-session-close   [PARTIAL·gap [provisional]]   → elements/clair-desk.md
Consulting-ops desk — reads every Consulting Gmail thread through a safety-isolated reader agent, surfaces what needs the operator in needs-me.json, closes sessions with Drive-doc ingest + an append-only billing write to Tracker v3, and keeps a cadence-nudge cron that fires a phone push exactly once per new due-state. ·gap because Drive-side billing scripts are not git-tracked and the concern-bar classification is LLM-judgment with no deterministic enforcement.

INTEROP:
  READS        email-service          · store-first path (email_service_read.py --desk clair) is the primary body-read source
  CHAINS       safe-reader-plane      · ingest-reader (haiku, tool-less) reads email_convert.py output on the raw fallback path
  READS        grand-central          · reads the v2 store that email_summary_sync.py writes; clair-desk is a consumer, not a writer of that store
  WRITES->     needs-me.json          · consumed by the Helm clair.json tile via clair-health.py
  WRITES->     ledger.md              · append-only Clair session-close journal (distinct from system/journal.md)
  WRITES->     Billing Tracker v3     · the billing sheet; the only external-service write clair makes
  FEEDS        pulse-cron             · clair-billing-run.sh + clair-ingest-run.sh + clair-health-run.sh are all Pulse-dispatched runners
  COMPLEMENTS  save                   · /save routes clair records to records/ + ledger to state/debt-ledger.md; clair's own ledger.md is separate and append-only
  KEYS-OFF     gws-plane              · all Gmail / Drive / Sheets / Tasks reads and writes go through gws CLI (/opt/homebrew/bin/gws)
  CHAINS       notify-send.sh         · cadence push + health-failure alerts fire via notify-send.sh (ntfy phone push)
  GUARDED-BY   guard_ledger_discipline.sh · guard_sheet_writes.sh · guard_sheet_formula_writes.sh · ingest_gate_enforce.sh   · the walls that fire here

## deryl-desk · /deryl-ingest + /reconcile + /deryl-rocketmoney   [PARTIAL [provisional]]   → elements/deryl-desk.md
The personal-finance operator — ingests email, transactions, and utility data; maintains the live ledger (Deryl Financial Master); runs a nightly health check that feeds the Helm dashboard; and provides a human-gated reconcile session for periodic tax bookkeeping. Multiple documented honor-system failure modes (stale-number recitation, mental arithmetic, email-scope breach).

INTEROP:
  CHAINS      ingest-run.lib.sh  · deryl-ingest-run.sh is built on the shared ingest-run.lib.sh scaffold (primary-machine gate, new-mail gate, bounded work-list, single-instance lock, watchdog, marker-advance); a change to the lib propagates to all ingest runners
  FEEDS       helm               · deryl-ingest writes state/status/deryl-ingest.json (LOCKED schema decision #38) — Helm d.ingest card; deryl-books-health.py emits state/status/deryl.json — Helm finances/property/tax tiles
  WRITES→     Gmail Deryl-Archive   · deryl-ingest routes True Submeter emails to Deryl-Archive (Label_32) as pipeline hand-off to true_submeter_ingest.py; all other processed threads move to Deryl-Processed
  FEEDS       deryl open-loops   · deryl-ingest appends HIGH items with gmail links to desks/deryl/state/open-loops.md; Deryl session reads on launch; /save can relocate resolved loops
  READS       email-service      · daily ingest tries read_thread() store-first before re-fetching from Gmail; falls back to raw sanitization on MISS-*/DISABLED; never writes the store
  CHAINS      cp_utilities_ingest · cp_utilities_ingest → true_submeter_ingest are chained inside cp-utilities-run.sh; true_submeter must not run if cp_utilities fails
  SYNCS       reconcile marker   · /reconcile writes last-reconciled marker to Tax Workbook _REVIEW_STORE!H1; deryl-books-health.py reads and parses this same cell for dashboard signals — format must stay parseable
  GUARDED-BY  guard_sheet_writes.sh · DFM and CP sheets flagged BRITTLE; destructive ops confirm before executing
  GUARDED-BY  guard_ledger_discipline.sh · blocks adding ✅/RESOLVED/CLEARED/FIXED annotation to ## Open in state/debt-ledger.md; deletion-only discipline
  GUARDED-BY  guard_canon_write.sh · blocks Write/Edit to **/canon/** lacking authority:user; prevents silent promotion of financial findings
  GUARDED-BY  ingest_gate_enforce.sh · enforces reader-actor split; blocks un-wrapped raw email body reads by the controller context
  GUARDED-BY  guard_write_paths.sh · residency wall; blocks writes outside Drive spine or approved ~/.claude/ paths

## cal-pipeline · /cal-daily · /cal-weekly   [PARTIAL]   → elements/cal-pipeline.md
Pre-builds the day/week from raw Google data overnight, then mines the human once and writes nothing until confirmed — the interrogative cognitive-load layer on top of the raw calendar store. cal-weekly is mid-build/unverified; diary parser is hard-broken for rich journal content.

INTEROP:
  READS       item-store              · weekly vault filled via item_store_window / item_store_read; the store is the query layer instead of live Google calls
  READS       grand-central           · email bodies via email_service_read (store-first path in vault-pull)
  READS       system/journal.md       · cal-diary-capture.py reads pipe rows + SESSION CONTEXT blocks for per-day diary (parser broken for rich formats — CAL-DIARY-FORMAT-DRIFT)
  READS       journal                 · cal-diary-capture.py reads system/journal.md as the sole transit point for the diary
  WRITES→     desks/cal/diary/        · diary-capture + diary-rollup write the diary tree (lookback surface)
  WRITES→     desks/cal/state/raw-vault/  · overnight vault (daily); cal-daily reads only here
  WRITES→     desks/cal/state/weekly-vault/ · weekly deep vault; cal-weekly reads here
  CHAINS      cal-analyze-run.sh      · chained from cal-vault-run.sh on RC=0 (Stage 2 daily analysis — 3-lens Opus panel + synthesizer)
  CHAINS      cal-weekly-analyze-run.sh · chained from cal-vault-weekly-run.sh on RC=0 (Stage 2 weekly mine — one Sonnet call, 3 angles)
  WRITES→     Agent Ops calendar      · Phase 5 / Pass 5 clerk → guarded by block_primary_calendar.sh
  WRITES→     Google Tasks            · Life Map Daily Win subtasks only → guarded by guard_tasks_writes.sh
  READS       desks/cal/skill-refs/user-canon.md · life lanes, rails, Agent Ops calendar id
  READS       state/status/*.json     · diary-capture reads desk status snapshots for machine recap
  GUARDED-BY  block_primary_calendar.sh · all calendar writes; fires on gws Bash only (MCP bypass gap)
  GUARDED-BY  guard_tasks_writes.sh   · Life Map writes; Daily Win subtasks only; [CAL-WEEKLY-LIFEMAP-GUARD] conflict with weekly coach routing unresolved
  GUARDED-BY  scratch_capture_gate.sh · weekly session scratchpad; Stop hook; fires per ~100k-token bucket
  TRIGGERS    advisory-council        · Phase 4 council IS the /advisory-council engine (6 opus members — the sole named opus exception in CLAUDE.md)
  COMPLEMENTS pulse-cron              · Pulse dispatches Stage 1 + Stage 2 cron jobs; cal-pipeline owns the skill/human layer
---

## hospital · emit_finding.py + findings_reader.py + fault_proposer.py   [PARTIAL·gap [provisional]]   → elements/hospital.md
Every problem the system detects about itself becomes ONE comparable record, so "what is wrong?" can be asked once — at ground, subsystem or whole-system altitude — and answered with a ranked, evidence-cited list instead of a pile of incompatible notes. It DETECTS and RANKS; it never REMEDIATES (council: auto-fix CUT 7/7). Four producers emit through it today; ~8 known failure producers still do not (GAP-1), and nothing guards the store against a hand-authored write (GAP-3).

INTEROP:
  READS        health-invariants   · one of its four converted producers; health_invariants.py emits per-invariant findings through emit_finding (T15.19, `fe56626`) — its old state/health.jsonl append was DELETED in that same commit
  COMPLEMENTS  health-invariants   · Health Authority answers "is the SUBSTRATE intact?" (runtime); Hospital answers "what has any DETECTOR found, and how bad is it?" — and health_invariants is now BOTH a substrate-checker AND a Hospital producer, which is exactly why the two must never be merged
  WRITES→      helm                · findings land at state/findings/<producer>.<machine>.jsonl on the Drive spine — machine token in the PATH, never only the payload (an internally-tagged shared file still forked 9 ways and stranded 1,169 rows)
  FEEDS        health-line         · health_line.py at SESSION START is the CONSUMER — chosen because it speaks whether or not anyone chooses to look; "a human sees the dashboard" is the consumer that already failed twice (a forked tile unnoticed; 57 findings unread for 7 days)
  TRIGGERS-BY  pulse-cron          · fault-proposer runs daily (86400s); findings_deadman enumerates producers from pulse-config AND live `crontab -l`, which is what finally makes the crontab-only health-deadman visible at all
  KEYS-OFF     two-machine-residency · one writer per PATH, per machine; the union reader NAMES any shard it could not read rather than silently returning a shorter list
  GUARDED-BY   — NOTHING, as of this write · no Hospital hook exists or is registered (GAP-3); emit_finding's contract is structural (no id= parameter, scanned_n required, zero-scan-OK refused) but a direct append into state/findings/ bypasses it entirely

## efficiency · recommend.py + emit_recommendation.py + fault_proposer.py   [PARTIAL·gap [provisional — not fire-tested]]   → elements/efficiency.md
Efficiency exists so the system gets SHARPER with use instead of duller. Entropy is the default — junk accumulates, parts rot, seams fray. Efficiency is the counter-force: it reads what is wrong, reasons ACROSS findings rather than one at a time, and proposes how the organism should evolve. Where Hospital DETECTS and RANKS one problem at a time, Efficiency reasons across them at three altitudes — the broken part, the broken chain, the wrong architecture. **It SUGGESTS and never APPLIES** (⚖ RULED 2026-08-04 by the operator; auto-fix CUT 7/7 by council), and there is no applier anywhere in it. ⚠ **Only the GROUND altitude is built, and it has never run in production** — `recommend.py` has no caller and `state/recommendations/` does not exist on disk (measured 2026-08-05), deliberately, pending one supervised live run. **There is no LLM in this subsystem today** — it is deterministic code end to end, so no code/LLM seam binds it as built.

INTEROP:
  READS        hospital            · consumes the findings union via findings_reader.py — Hospital's contract change is Efficiency's outage; the tightest coupling in the pair
  SHARES-STORE hospital            · ONE hook (guard_findings_write.sh, mode 444, settings.json) guards BOTH state/findings/ and state/recommendations/ incl. dispositions/ — hardening it helps both, breaking it blinds both
  FEEDS        health-line         · the session-start RECOMMENDATIONS: line is the ONLY surface where Efficiency reaches a human — ranked DECISION > ORGANISM > SUBSYSTEM > INSTANCE, capped at 3, each with an 8-char fingerprint the disposition CLI accepts directly
  TRIGGERS-BY  pulse-cron          · ONLY fault-proposer is scheduled (daily, 86400s); the ground reasoner is NOT — that is GAP-1, not an oversight (CUT-E)
  KEYS-OFF     two-machine-residency · machine token in the PATH, never only the payload; one writer per path per machine
  COMPLEMENTS  backlog             · ⚖ RULED 2026-08-05 by the operator — the debt ledger is Efficiency's INPUT, not its exile; it may DEMOTE and ARCHIVE ledger items on POSITIVE EVIDENCE ONLY (§18.5a carve-out). NOT YET BUILT
  GUARDED-BY   guard_findings_write.sh · blocks any Bash/Write/Edit into the store that bypasses emit_recommendation.py; resolves shell variables before matching (the T15.32 bypass). Watched firing on the PRIMARY machine only — the second machine is dark since 2026-07-04

---

> ⭐ **AUTHORED HERE — the entries below take no donor number** (see the ADDENDUM under the ranked index).
> They are `## <slug>` narratives in the same format as every entry above; they are simply not part of the
> donor's frozen list of 51.

## planning · planning daily · planning weekly   [PARTIAL·gap [provisional] (honor)]   → elements/planning.md
Two interrogative cadence skills — a daily trust-fall and a weekly helmsman — that mine the reader for the judgment a machine cannot pull from data, batch every write to a ledger, and flush it only behind a gate the reader confirms by hand. It is the ONE place this system asks instead of reasoning over material that already exists: a day does not exist yet. **Not the donor's `cal-pipeline` (#44)** — that described one person's calendar desk; this describes the generic capability that shipped. Two real hook guards wall the write path; the interrogative discipline itself is prose.

INTEROP:
  CHAINS       council-engine        · planning-weekly Phase 4 IS the advisory-council engine — six member briefs dispatched as the advisor roster (blind-diverge → argue → converge); the ONLY opus subagents in this element
  FEEDS        item-store            · both skills read the faithful de-duplicated library via shared/tools/item_store_window.py (--mode bundle); metadata-only and index-only reads are REJECTED — the store is the query layer, not Google
  KEYS-OFF     gws-plane             · every calendar and task read/write exits through the gws CLI; the four identifiers come from the reader's own `<notes>/config/cal.md` via shared/cal_config.py, never a constant in a tool (`cal` there means CALENDAR, not the renamed desk)
  GUARDED-BY   hook-plane            · guard_calendar_writes.sh (agent calendar only, default-deny) + guard_tasks_writes.sh with lib/tasks_guard.py (goals list read-only, one carve-out, delete/clear never); both registered PreToolUse/Bash and both fire-tested LIVE
  TRIGGERS-BY  pulse-cron            · planning-weekly-prime (daily tick, weekly work), planning-diary (one row driving five cadences), planning-health; planning-vault / planning-vault-weekly / planning-analyze have NO row — the daily compensates by pulling live
  WRITES→      journal               · the diary under the reader's notes root is written by planning-diary-capture.py, which preserves the Human Delta block and completes with gws entirely absent from PATH
  SHARES-STORE memory-read           · /checkin's journal-first writes feed planning-diary-capture.py; a skipped checkin starves the diary silently and the failure is invisible at the planning end
  SHARES       statusline-hud        · skill_hud.sh paints the per-phase HUD, scratch_flag.sh the scratchpad indicator — rendering, never enforcement
  SHARES       scratch-capture-gate  · scratch_flag.sh arms the gate on the resolved scratchpad path; the weekly raises SCRATCH_TTL_MIN to 180 because its run is long
  READS        safe-reader-plane     · email bodies, invites and task text from anyone are ADVERSARIAL DATA — facts extracted, embedded instructions never obeyed; the priming cron restates this verbatim in every lens prompt
  COMPLEMENTS  email-service         · the daily's email surface routes through shared/tools/email_convert.py, which ships but has never run against a real mailbox — the inbox slice is EMPTY BY BREAKAGE and says so
  COMPLEMENTS  build-plan-plane      · a different sense of "plan": that element structures and executes PROJECT plans (Phase/Feature/Task); this one plans a DAY and a WEEK. No shared code, no shared store — named so nobody merges them
  PROPOSES     backlog-authority     · the weekly's ranked output and the daily's open-loop pass surface work the reader then decides on; neither writes a backlog itself

## where-things-live · a new skill/agent/hook/file needs a home   [PARTIAL·gap (honor)]   → elements/where-things-live.md
Answers "where does this go" for anything a person builds or writes themselves — sorted by ONE question they already know the answer to, who is this for. For me: outside this repo entirely, in `~/.claude/<kind>/<name>/` if the harness must DISCOVER it, or the AI Brain if something merely CALLS it by path. For everyone: inside this repo, on a branch, offered back as a PR — ordinary open source. For a whole separate system: copy it out and run it as a fork, which will not receive Harness updates. States plainly that `~/.claude/` itself is backed up nowhere.

INTEROP:
  READS        brain                 · shares brain.md's git/Drive vocabulary (repo = machinery, AI Brain = content) and extends it with the third surface, `~/.claude/`, that brain.md does not cover
  READS        skill-system          · the discovery mechanism this element generalizes is skill-system's own registration chain (`~/.claude/skills/` symlink discovery); this element states the rule skill-system only demonstrates for one kind
  READS        hook-plane            · hook registration is the one kind this element found to have NO confirmed personal home — the tracked `.claude/settings.json` is the only documented registration surface, and it travels by wholesale `git pull` replacement like every other tracked file
  COMPLEMENTS  two-machine-residency · that element's parity model is for THIS repo's own tracked files across two machines; this element is about material that is deliberately NOT tracked at all — adjacent problem, opposite mechanism
  GUARDED-BY   guard_write_paths.sh  · PreToolUse Write|Edit blocks a *new* file written directly under `~/.claude/skills/` or `~/.claude/commands/` with a redirect message that names a different repo's clone path — a real, live inconsistency with the no-symlink rule this element documents rather than resolves

## Delivery (Feature 1.6 — after the elements are authored)
One pointer line in global `CLAUDE.md` + one line per desk naming the elements that touch it. A PreToolUse
write-guard (`guard_organism_map.sh`) protects this manual + the label-criteria (it is the system's own
attack-surface map); the Feature 1.5 checker asserts that guard is itself git-tracked + LIVE.
