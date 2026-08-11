---
id: system-knowledge-altitude
title: Knowledge Altitude — where everything belongs (the archivist's placement doctrine)
record_type: doctrine
created_at: 2026-06-11
updated_at: 2026-07-11
status: active
authority: user
---

# Knowledge Altitude

> The law for WHERE a piece of knowledge belongs in the this system tree — across **every artifact type** (canon,
> skill, project/brief, record, SOP/playbook — or nothing at all). Read by the **archivist** (when it routes
> inbox items, audits homes, or proposes a split) and by **`/save`**. Lives LOW on purpose — loaded only when
> this work is happening, never injected into every conversation. (It passes its own test by NOT sitting at the
> summit.) Plain language by design: a cold session must be able to use it.
>
> **This is the INTENT DOCTRINE applied to knowledge:** every object declares its intent — a purpose for a
> standing thing, a desired outcome for a bounded one — and altitude is that same law applied to one case,
> *where a piece of knowledge sits.*
> ⏳ **UNRULED** — the parent law itself, `system/intent-doctrine.md`, is on no ship list; the sentence
> above is the whole of it that this page needs.
>
> ⛔ **`/archivist-review` · `system/archivist/placement-trial-log.md` ·
> `system/research/2026-06-13-preload-vs-pointer-consensus.md` — not shipped.** The archivist's review
> command and its probation log belong to a family that stays with the author; §9's probation is
> therefore a description of how that judgment was earned, not a step you can run. The research record
> is one of their own findings — the conclusion it supports is stated where it is cited.

## What canon IS — durability × altitude (the definition)

Canon is a durable, generalizable **observation that reliably holds for the territory of knowledge it lives in,
filed at the thinnest altitude that still holds it.** (Sometimes that observation is even a rule — but canon is
observation first, never rules by definition.) Two tests, both required:

**1. Durability — is it canon at all?** Durably reliable standing knowledge (a generalizable observation, a
consistent pattern, a durable fact/trait/preference about the person or their world — sometimes a rule, but
observation first) → canon. A dated number, a one-off event, an expiring
status → a *record*, not canon. Plain check: would this still be true, and worth loading, well into the
future (the ~2-year test)?

**2. Altitude — which canon?** Canon is **not** "true everywhere" — that describes only the apex. A canon
fact belongs at the **highest (broadest) folder where it is still always-true for everything in that folder
— and no higher.** Scope narrows as you descend: a few things are true for *every* session (global, tiny by
necessity), more for *every* conversation in a domain (desk), more still for a sub-area (tax within finance).
Thin at top, heavy at bottom — because fewer truths hold across a wider scope, and the always-loaded apex
must stay under the context-rot floor.

**Finding the altitude — two directions, one ladder.** Top-down: start high, ask the level's question
("true for EVERY session?" → "every conversation in THIS domain?" → "across this whole sub-area?"); fails →
sink a level and ask again; it lands at the highest level it still passes. Bottom-up: start narrow, ask
"what's true *here* that wouldn't be true for the parent?" — isolating what belongs at this altitude vs. what
floats up.

**Sometimes the answer is a new territory.** When a folder fills with distinct always-true knowledge
(finance → tax · bookkeeping · budgeting), **split** it so each body gets its own shelf. Placement is two
questions: *which altitude* and *does this deserve its own territory.*

**Refinement — the split test is an injection question, not just an always-loaded-cost one (the operator, 2026-08-05,
authority: user).** The real question behind "does this deserve its own territory" is: *what is a corpus of
canonical information that would be too large to inject into one conversation — such as one unified README
about a person — or too diverse to inject that way without confusing an LLM with contradictory or unnecessary
information?* This is a stronger frame than the context-rot/always-loaded-floor reasoning above (§ "What canon
IS") — that framing only bites on knowledge that loads by default (global/desk canon), while the injection
framing applies to **every** folder, including ones nothing preloads, because a `/read`, a branch-walk, or an
ingest pass can still pull a whole folder into one conversation at once.

**Too big and too diverse are different problems with different fixes (the operator, 2026-08-05, authority: user).**
- **Too BIG → subdivide (nest).** Same territory, more shelves beneath it — the split above.
- **Too DIVERSE → separate (siblings, not nested).** Not that the folder is large, but that two bodies of
  knowledge would actively degrade each other if loaded together — mutually irrelevant at the point of use.
  (Worked case, same territory as above: within finance, tax knowledge and bookkeeping knowledge are each
  irrelevant to the other's questions — same thing the other way around.)

**Portability:** this governs any **nested-folder-schema knowledge system** (this system is the reference
instance) — canon is always relative to its territory and altitude, never absolute.

*(Added 2026-07-11. Refines the earlier implicit model and corrects a prior slip that framed canon as "true
across any folder" — that describes only the apex, not canon in general.)*

**The mechanism the ladder rests on — WHY placement has a cost, not just a category (the operator, 2026-08-05,
authority: user).** `/read`'s branch-walk (`skills/read/SKILL.md` Step 0.6) pulls canon from EVERY ancestor
folder on the way down — a read from `tax/` loads tax canon AND financial canon AND root canon, one
*customized chain*, not one file. **Consequence: anything placed in a parent is paid for by every
descendant that ever walks past it** — a line in `financial/canon.md` loads into every tax conversation
AND every bookkeeping conversation, permanently. So the placement question is not "what is this about" but
**"who has to bear the cost of it."** The test: every child needs it → parent; only one branch needs it →
that child; nobody needs it *loaded*, but it must stay findable → records (the findability invariant
above). Worked example (`financial/`): shared-for-everything facts — *"he is married, owns two homes with
his wife Ria, and they have joint bank accounts"* — belong at the parent; tax-only detail (filing
deadlines, deduction history) sinks to `tax/`, because bookkeeping shouldn't be charged for it. **The
pyramid is a cost curve, not an aesthetic** — *"anything toward the top of the folder schema is THINNER in
canon than anything at the bottom … push all of our heavy canonical information to the bottom"*: the top is
thin because it's EXPENSIVE, and everything below it pays.

## 1. The job — first the TYPE of home, then the right spot inside it
The archivist's real job is bigger than canon: it decides **what KIND of thing a piece of information is, and
therefore which TYPE of home it wants** — and only then where inside that home it lands. Canon is the most
important destination for durable insights, but it is **one type among several.** A new item might really want
to be:

- **canon** — a durable, generalizable *observation* (a standing pattern or fact; a rule only if it genuinely is one) (→ if so, apply the level ladder, §2–§3);
- **a skill** — a repeatable *how-to* the system should be able to run;
- **a project / brief** — something that belongs to one specific project's state, not the world;
- **a record** — a fact, number, finding, or event (dated, searchable — NOT a rule);
- **an SOP / playbook** — a repeatable *procedure*; if no playbook exists to hold it, **propose creating a NEW one**;
- **nothing** — drop it (an artifact that earns no home anywhere).

**Records split by SHAPE, not just durability (the operator, 2026-08-05, authority: user).** A record is either a
**discrete dated item** worth keeping on its own (his examples: *"quick research I did on my 2006 tax
filing," "research about a house I built last year"*) or **a larger corpus** — the same non-canon material,
but a body big enough that it's referenced/searched later rather than read whole. Both are records, not
canon; the split is size/shape, not durability, and neither graduates to canon just by accumulating.

**A home can hold both canon and records at once — they are not competing types (the operator, 2026-08-05, authority:
user).** Every home is born with a canon file and a stated purpose/intent (§4), but that doesn't make it
canon-only: the same folder routinely also holds `records/` for what matters but isn't durable/general (the
Durability test, § "What canon IS"). Canon and records are two different admission tests an item can pass, not
two homes competing for the same item — a single home can and often does serve both doors.

The archivist is **responsible for knowing each type's definition** — what belongs in a canon vs a skill vs a
record vs an SOP — from the architecture (`architecture.md` is the artifact-type inventory; `CLAUDE.md`'s Memory
/ Persistence-Routing rules distinguish record vs canon vs state; this doctrine + each home's `intent` add the
admission bar). **Matching the item to the right *type* is the FIRST decision;** which level / which home follows.

**Why this matters now:** the inbox is the **catch-all** — `/save` drops anything whose home is unclear straight
in, so it fills with mixed, ambiguous stuff *on purpose*. The archivist is the **disambiguator** that sorts it.
If this doctrine only knew canon, every non-canon save would have nowhere to go.

## 2. For canon — admission DIFFICULTY by level (the scarce-space idea)
Once an item is judged **canon-shaped**, this is how it finds its level:

**There's a range of admission DIFFICULTY across the levels of `canon.md` in our folder schema: the higher up a
piece tries to live, the less space there is — so the harder it must fight to justify its place against
everything else competing for that canon.**

Global canon stays the *thinnest*, so competition for a slot there is fiercest; each level down has more room
and an easier bar. A piece never just "belongs" somewhere — it has to **earn its slot against everything else
crowding that canon**, and the crowding tightens as you climb. (Why the top is scarce: a higher file loads into
far more conversations, which is exactly what makes its space precious — *the air thins as you climb.*)

## 3. The canon admission test — difficulty by level, judged by a plain question (concrete)
A canon line belongs at the **highest** level where it can still win its fight for a slot. The difficulty rises
as you climb; judge each level by its concrete question:

| Level | Difficulty | Home | The plain question it must pass |
|---|---|---|---|
| Global | **Hardest** | global `CLAUDE.md` | **Does this need to shape EVERY conversation, on ANY subject?** |
| Desk | **Hard** | desk `CLAUDE.md` / desk canon | **Needed in basically every conversation about THIS subject?** (a tax rule fails here — most talk about money is not about tax, so it belongs one level down)  (old: most talk isn't tax.) |
| Sub-folder | **Medium** | sub-area canon (e.g. a practice / finance) | **Needed across this whole sub-area?** |
| Deep | **Easy** | sub-sub canon | **Is this even *about* this topic?** (If yes, let it in — it barely loads, so overload is harmless.) |

Fails the question at a level → it can't win a slot there; **sink it to the next level down and ask again.**
There is **no numeric score** — the bar is just these plain questions plus the home's stated intent (§4), and
the archivist reads and judges. Text + judgment is the whole engine.

**The wording gate — the STANDALONE TEST (applies at EVERY level, and matters most).** Beyond winning its
altitude slot, every admitted canon line must be worded so a **completely fresh, ZERO-CONTEXT session can read
it ALONE and fully understand and act on it** — no backstory, no reliance on the surrounding session. This is
the paramount canon gate: a durable, well-placed line worded in session-dependent shorthand still FAILS.
**Canon's virtue is precision and self-sufficiency, not size.** Always-on canon (global/desk) is also
*efficient* (it loads every session); scoped/on-demand canon (project/domain via `/read`) may be *richer* — but
both must pass the standalone test. Two failure modes: **cryptic** (fails the standalone test — the worse one)
and **bloat** (redundant/verbose). Precision beats brevity.

**Corollary — pointers up high, content down low.** This is also HOW a layer earns leanness. The higher (more
always-loaded) a canon sits, the more it should be a **directory** — the few load-bearing rules + **pointers** to
where the depth lives (`see records/insights/…`), NOT the full inline content. Deep canon (sea level, loaded only
when you walk into that branch) keeps the rich content **inline**, because its weight costs nothing elsewhere.
*Why:* a pointer adds a retrieval hop, so inline wins at the point of use — but up high, where every slot loads
into *everything*, the hop is worth paying. This is also what stops a `/read` branch-walk from crowding context:
it picks up light pointers on the way up and meets the heavy content only at the bottom, where you wanted it.

**Refinement — "thin up high," not "pointer up high" (2026-06-13 `/research`, preload-vs-pointer).** The corollary's
real lever is **altitude/leanness** — keep the always-loaded floor SMALL (under the context-rot threshold ~20K tokens),
where a wrong or bloated line pollutes every session — NOT "pointer-vs-content" per se. For a **SMALL, STABLE, authored
corpus like ours, do NOT pointer-ize the canon you actually load:** un-loaded knowledge is silently MISSED (our own
pointer-only desk canon left ~50% of facts invisible in blind tests until the SessionStart hook auto-injected content;
the research confirms silent-miss > context cost for small corpora). So: **THIN up high** (the few load-bearing lines +
**cross-branch** pointers to *other* domains you're not in), **full content on the branch you ARE in**, loaded
just-in-time by `/read`. Pointers are for cross-branch awareness, never for the spine of what a session needs. (Map:
`system/research/2026-06-13-preload-vs-pointer-consensus.md` — captured 2026-06-13 in the archivist inbox.)

**Findability invariant — no buried treasure (the corollary's other half).** Moving content *down* must never
move its *findability* down with it. Whenever knowledge is placed into a deeper / specialist home — sunk from a
brain file, filed into a project's records, or parked in a playbook — **the domain that would reach for it must
be able to find it: leave a one-line pointer from where a future session would naturally look.** Leanness relocates
the *content*; the breadcrumb stays at the point of use. A note no one can locate from its domain is **lost, not
stored** — a pot of gold with no map. This is the standing answer to the *recall* problem (lean canon controls
what *loads*; it does nothing for how a cold session *finds* the right slice — retrieval is the hard part). The
pointer is **part of the placement, not optional cleanup** — see the archivist's findability gate in
`agents/archivist.md`.

## 4. How a home declares its bar — the INTENT (every type, every home)
Every home — of **any** type (a canon, a skill folder, a project, a records area, a playbook) — carries an
**`intent`**: one plain-English line stating its admission bar (what it takes to belong here). For canon this is
the P6 territory-map field `accepts:` **upgraded** from "what belongs" → "the *bar* to belong"; the same idea
extends to the other types so the router has one consistent thing to read everywhere.

Optionally, a home with a genuinely confusable neighbor adds **ONE near-miss redirect** — the single most
mistakable thing that does NOT belong, and where it goes instead:

```
intent:   <plain-English admission bar for this home>
not:      <the one near-miss> → <its real home>      # OPTIONAL, only where a real seam exists
```

Example (a subject's canon — note that the near-miss points DOWN at what sinks, never sideways at a sibling):
> **intent:** ONLY the high-level rules always true for any conversation about this subject — how it is
> structured + the standing conventions, plus pointers to the specialty detail.
> **not:** the deep detail of one area — full tax info, mortgage specifics, individual accounts → the sub-folder
> canons / records *below*.

**Rules:**
- **One near-miss, NEVER an exclusion list.** Lists are infinite, they bloat, they rot, and worse — the LLM
  starts reading "not on the no-list" as "allowed." Name only the *one* boundary that's actually fuzzy.
- **For an always-on home (global, a desk), the near-miss is usually the VERTICAL sink** — the specialty detail
  that should drop to a sub-folder *below* — NOT a sibling desk. An always-on canon loads every session, so its
  real bloat risk is holding depth only *some* sessions need; the bar is "high-level backbone + pointers, not depth."
- A home with no confusable neighbor needs **no `not:` line** at all.
- The near-miss doubles as relocation guidance: it tells the archivist where to *send* a misfit.

## 5. The archivist's jobs under this doctrine (all PROPOSE-ONLY)
1. **Triage by type** — for each inbox item (and each existing artifact under audit), FIRST decide which TYPE of
   home it wants (§1). This includes **cull** (it's really a record → route to `records/`; or junk → propose
   dropping) and **propose a new SOP / skill / project** when a repeatable or self-contained thing has no home yet.
2. **Place** — within the chosen type, land it in the right home; for **canon**, run it up the levels to the
   highest where it can win a slot (§2–§3), against the homes' intents. (Uses the router, `skills/archivist-route`.)
3. **Audit + sink** — periodically re-test EXISTING `CLAUDE.md`/canon lines against their home's intent; flag
   any that can **no longer win their slot at that level** and should **sink lower.**
4. **Split** — flag a home grown fat + broad enough to **split** into specialized children (which creates new
   lower shelves for sinkers). This is the cohesion check **J**, grown up. Pure judgment + J — **no size
   trigger, no math.**

The archivist **never moves anything.** It proposes; the human approves via `/archivist-review`
(snapshot-first, dependency-gated). Applier, never legislator.

## 6. Authorship — who writes a home's intent
- **the operator writes the high-tier bars** (global, each desk). Those are *law*; law isn't machine-guessed.
- **The archivist PROPOSES** the low / new / `[INFERRED]` intents for approval.

## 7. KISS — the hard lines (refuse this complexity)
- Plain-text intents + LLM judgment. **NO numeric scoring, NO thresholds, NO "preponderance equations."**
- **One near-miss, never an exclusion list.**
- Type-routing adds **no machinery** — it's the same LLM reading `architecture.md` + each home's `intent` and
  judging. Dumb core: a flat text inventory of homes + an LLM reading it. No engine beyond a cron + a read.

## 8. Self-application
This doctrine governs the archivist and `/save` — not every conversation — so it does **not** earn the summit.
Full text lives here (low, on-demand). At most a one-liner in `architecture.md`; a bare pointer (or nothing)
in global `CLAUDE.md`. If we ever catch ourselves wanting to paste this into `CLAUDE.md`, that's the doctrine
failing its own test — don't.

## 9. Probation — temporary scaffolding, built to be deleted
While we're still earning trust in the archivist's placement judgment, run a **monitoring period (~1–2 months)**:
for every triage / place / cull / sink / split it proposes, the archivist writes a **one-line plain-English
RATIONALE** (which type + level, which intent it matched or failed, what it rejected and why) to a single trial
log — `system/archivist/placement-trial-log.md`. the operator skims it, catches bad calls, and corrects the intents —
a real human-in-the-loop feedback signal *on top of* the normal `/archivist-review` approval.

This is **scaffolding, NOT law.** It is one file + one logging step, and **nothing else depends on it.** When
the operator is confident the judgment is good, the whole probation is deleted cleanly — remove the log and the
logging step; the doctrine and the engine are untouched. Designed from day one to be ripped out, never to
harden into a permanent layer.
