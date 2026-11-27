---
id: system-knowledge-altitude
title: Knowledge Altitude — where everything belongs (the archivist's placement doctrine)
record_type: doctrine
created_at: 2026-06-11
updated_at: 2026-11-16
status: active
authority: user
---

# Knowledge Altitude

'The operator' here is the person who maintains the plugin; 'the person' is you.

> The doctrine for WHERE a piece of knowledge belongs in this system's folders — across **every artifact type** (canon,
> skill, project/brief, record, SOP/playbook — or nothing at all). Read by the archivist, `/save`, `/read` (step 3.9), `/ingest`, `/canon-audit` and
> `/archivist-declutter`. Lives LOW on purpose — loaded only when
> this work is happening, never injected into every conversation. (It passes its own test by NOT sitting in the
> always-loaded layer: the root canon and the `CLAUDE.md` glasses.) Plain language by design: a cold session must be able to use it.
>
> This page is the **place** axis of the three (place, date, trust; `canon/desk-building-sop.md` §1). Date is the diary. Trust is read by location: canon is canon because of where it sits.
>
> **This is the INTENT DOCTRINE applied to knowledge:** every object declares its intent — a purpose for a
> standing thing, a desired outcome for a bounded one — and altitude is that same doctrine applied to one case,
> *where a piece of knowledge sits.*
> (Not the same as the Vision's INTENTION doctrine, which asks each significant choice to carry its why and
> its change condition. Intent says what a thing is for. An intention line says why a choice was made and
> what would change it.)
> The parent doctrine is `system/intent-doctrine.md`. The sentence above is the whole of it that this page needs; read the doctrine when you are deciding what KIND of intent a thing carries.

## What canon IS — durability × altitude (the definition)

Canon is a durable, generalizable **observation that reliably holds for the territory of knowledge it lives in,
filed at the thinnest altitude that still holds it.** (Sometimes that observation is a must the person has asserted, and a must enters only on the person's own yes. But canon is observation first.) Two tests, both required:

**1. Durability — is it canon at all?** Durably reliable standing knowledge (a generalizable observation, a
consistent pattern, a durable fact/trait/preference about the person or their world — observation first) → canon. A number, a finding, a document → a *record*. What happened on a day → the diary. A present status → a status tile or a project brief. None of these is canon. Plain check: would this still be true, and worth loading, on the order of years, so that the line should not need editing more than every six months or so?

**2. Altitude — which canon?** Canon is **not** "true everywhere" — that describes only the apex. A canon
fact belongs at the **highest (broadest) folder where it is still always-true for everything in that folder
— and no higher.** Scope narrows as you descend: a few things are true for *every* session (root, tiny by
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

**Refinement — the split test is an injection question, not just an always-loaded-cost one (the operator, 2026-08-05).** The real question behind "does this deserve its own territory" is: *what is a corpus of
canonical information that would be too large to inject into one conversation — such as one unified README
about a person — or too diverse to inject that way without confusing an LLM with contradictory or unnecessary
information?* This is a stronger frame than the context-rot/always-loaded-floor reasoning above (§ "What canon
IS") — that framing only bites on knowledge that loads by default (root/desk canon), while the injection
framing applies to **every** folder, including ones nothing preloads, because a `/read`, a branch-walk, or an
ingest pass can still pull a whole folder into one conversation at once.

**Too big and too diverse are different problems with different fixes (the operator, 2026-08-05).**
- **Too BIG → subdivide (nest).** Same territory, more shelves beneath it — the split above.
- **Too DIVERSE → separate (siblings, not nested).** Not that the folder is large, but that two bodies of
  knowledge would actively degrade each other if loaded together — mutually irrelevant at the point of use.
  (Worked case, same territory as above: within finance, tax knowledge and bookkeeping knowledge are each
  irrelevant to the other's questions — same thing the other way around.)

**Portability:** this governs any **nested-folder-schema knowledge system** (this system is the reference
instance) — canon is always relative to its territory and altitude, never absolute.

*(Added 2026-07-11. Refines the earlier implicit model and corrects a prior slip that framed canon as "true
across any folder" — that describes only the apex, not canon in general.)*

**The mechanism the ladder rests on — WHY placement has a cost, not just a category (the operator, 2026-08-05).** `/read`'s branch walk (`.claude/skills/read/SKILL.md` Step 0.6) loads the canon of every folder on the project's branch, most specific first, and the session loader has already loaded the root canon and the desk's canon — so a session working in `tax/` carries tax canon AND financial canon AND root canon, one *customized chain*, not one file. **Consequence: anything placed in a parent is paid for by every
descendant that ever walks past it** — a line in `desks/financial/canon/canon.md` loads into every tax conversation
AND every bookkeeping conversation, permanently. So the placement question is not "what is this about" but
**"who has to bear the cost of it."** The test: every child needs it → parent; only one branch needs it →
that child; nobody needs it *loaded*, but it must stay findable → records (the findability invariant, §3 below). Worked example (`desks/financial/`): shared-for-everything facts — *"he is married, rents an apartment
with his wife Marisol, and they keep separate bank accounts"* (invented example, ⚠ nobody real, in the
style of `system/shipping-lane/fixtures/identity-fixture.md`) — belong at the parent; tax-only detail
(filing deadlines, deduction history) sinks to `tax/`, because bookkeeping shouldn't be charged for it. **The
pyramid is a cost curve, not an aesthetic** — *"anything toward the top of the folder schema is THINNER in
canon than anything at the bottom … push all of our heavy canonical information to the bottom"*: the top is
thin because it's EXPENSIVE, and everything below it pays.

**Canon inherits down, never sideways.** A parent's canon is true for every folder below it. A sibling's canon is not true for its neighbour, so a fact two siblings both need belongs in their parent, or in one of them with a pointer from the other. It is never copied sideways.

## 1. The job — first the TYPE of folder, then the right spot inside it
The archivist's real job is bigger than canon: it decides **what KIND of thing a piece of information is, and
therefore which TYPE of folder it wants** — and only then where inside that folder it lands. Canon is the most
important destination for durable insights, but it is **one type among several.** A new item might really want
to be:

- **canon** — a durable, generalizable *observation* (a standing pattern or fact) (→ if so, apply the level ladder, §2–§3);
- **a skill** — a repeatable *how-to* the system should be able to run;
- **a project / brief** — something that belongs to one specific project's state, not the world;
- **a record** — evidence: a fact, number, finding or document, topic-named and searchable, never expiring, filed in one of the six closed record types (`canon/data-layout.md`) — NOT a rule, and not the story of a day;
- **the diary** — what happened on a day, as a short summary that points to its records. Each desk has its own (`<Desk>-Diary`, made with the desk; one page per desk per day, with two kinds of write: low-confidence machine entries and high-confidence human lines, where the high supersedes the low; `canon/desk-building-sop.md` §6). The archivist does not file into it. When an item is a day's story, it belongs to the diary, and the evidence behind it is a record;
- **an open loop** — started, not finished → that folder's `open-loops.md`;
- **a debt-ledger entry** — a known gap in the system itself → the root `debt-ledger.md`, never canon wording;
- **an SOP / playbook** — a repeatable *procedure*; if no playbook exists to hold it, **propose creating a NEW one**;
- **nothing** — drop it (an artifact that earns no folder anywhere).

**Records split by SHAPE, not just durability (the operator, 2026-08-05).** A record is either a
**discrete item** worth keeping on its own (invented example, ⚠ nobody real, same convention as
above: *"quick research done on a 2019 insurance claim," "notes kept while renovating a garage last
year"*) or **a larger corpus** — the same non-canon material,
but a body big enough that it's referenced/searched later rather than read whole. Both are records, not
canon; the split is size/shape, not durability, and neither graduates to canon just by accumulating.

**A folder can hold both canon and records at once — they are not competing types (the operator, 2026-08-05).** Every folder is born with a canon file and a stated purpose/intent (§4), but that doesn't make it
canon-only: the same folder routinely also holds `records/` for what matters but isn't durable/general (the
Durability test, § "What canon IS"). Canon and records are two different admission tests an item can pass, not
two folders competing for the same item — a single folder can and often does serve both doors.

The archivist is **responsible for knowing each type's definition** — what belongs in a canon vs a skill vs a
record vs an SOP — from the type list in §1 above (`canon/data-layout.md` distinguishes records, canon and the diary, and `/save`'s routing tree applies it; this doctrine + each folder's `intent` add the
admission bar). **Matching the item to the right *type* is the FIRST decision;** which level / which folder follows.

**Why this matters:** when a save's home is unclear, `/save` saves the content durably and drops a pointer for deferred placement (`.claude/skills/save/phases/standard-steps.md`, Step 7e); the archivist later proposes its home and the person picks. If this doctrine only knew canon, every non-canon save would have nowhere to go.

## 2. For canon — admission DIFFICULTY by level (the scarce-space idea)
Once an item is judged **canon-shaped**, this is how it finds its level:

**There's a range of admission DIFFICULTY across the levels of canon (each folder's `canon/canon.md`) in our folder schema: the higher up a
piece tries to live, the less space there is — so the harder it must fight to justify its place against
everything else competing for that canon.**

Global canon stays the *thinnest*, so competition for a slot there is fiercest; each level down has more room
and an easier bar. A piece never just "belongs" somewhere — it has to **earn its slot against everything else
crowding that canon**, and the crowding tightens as you climb. (Why the top is scarce: a higher file loads into
far more conversations, which is exactly what makes its space precious — *the air thins as you climb.*)

## 2b. Pointers up high, content down low (the C4 idea)

Our altitudes follow the four zoom levels of the C4 model of software: Context (the map, always loaded), Containers (the manual and the middle maps, opened when a whole area matters), Components (one page per part, `canon/components/`), Code (the live files). Each level stands alone at its own depth and points DOWN; it never copies what is below.

Why: the high levels are loaded into the most conversations, so every line there is paid for most often and has the least room. A copy of a detail up high is paid for every turn and goes stale the first time the detail changes below it. A pointer costs one line and cannot go stale in the same way. So the top holds the shape and the way down; the base holds the facts. A reader unpacks only as far as the question needs.

This is the same scarcity as §2, seen from the reader's side: §2 says the top has little room, so a piece must earn it; this says what earns it there, which is a pointer, not the content.

## 3. The canon admission test — difficulty by level, judged by a plain question (concrete)
A canon line belongs at the **highest** level where it can still win its fight for a slot. The difficulty rises
as you climb; judge each level by its concrete question:

| Level | Difficulty | Folder | The plain question it must pass |
|---|---|---|---|
| Root | **Hardest** | the brain folder's root canon, `<brain>/canon/canon.md` (loaded with every desk) | **Does this need to shape EVERY conversation, on ANY subject?** |
| Desk | **Hard** | the desk's canon, `desks/<name>/canon/canon.md` | **Needed in basically every conversation about THIS subject?** (a tax rule fails here — most talk about money is not about tax, so it belongs one level down) |
| Sub-folder | **Medium** | sub-area canon (e.g. tax within finance) | **Needed across this whole sub-area?** |
| Deep | **Easy** | sub-sub canon | **Is this even *about* this topic?** (If yes, let it in: it loads only when a session walks into this branch, so the bar is low. The too-big / too-diverse test above still applies.) |

The `CLAUDE.md` files (plugin, personal, desk) are not canon levels. They are the glasses: a separate pyramid, thin at the plugin and wider at the desk, which correct how a session reads and may point to where things live. Knowledge goes in canon. A line that wants to be in a `CLAUDE.md` is usually a pointer or a bias, not a fact.

Fails the question at a level → it can't win a slot there; **sink it to the next level down and ask again.**
There is **no numeric score** — the bar is just these plain questions plus the folder's stated intent (§4), and
the archivist reads and judges. Text + judgment is the whole engine.

**The wording gate — the STANDALONE TEST (applies at EVERY level, and matters most).** Beyond winning its
altitude slot, every admitted canon line must be worded so a **completely fresh, ZERO-CONTEXT session can read
it ALONE and fully understand and act on it** — no backstory, no reliance on the surrounding session. This is
the paramount canon gate: a durable, well-placed line worded in session-dependent shorthand still FAILS.
**Canon's virtue is precision and self-sufficiency, not size.** Always-on canon (root/desk) is also
*efficient* (it loads every session); scoped/on-demand canon (project/domain via `/read`) may be *richer* — but
both must pass the standalone test. Two failure modes: **cryptic** (fails the standalone test — the worse one)
and **bloat** (redundant/verbose). Precision beats brevity.

**Corollary — pointers up high, content down low.** This is also HOW a layer earns leanness. The higher (more
always-loaded) a canon sits, the more it should be a **directory** — the few load-bearing lines + **pointers** to
where the depth lives (`see records/insights/…`), NOT the full inline content. Deep canon (sea level, loaded only
when you walk into that branch) keeps the rich content **inline**, because its weight costs nothing elsewhere.
*Why:* a pointer adds a retrieval hop, so inline wins at the point of use — but up high, where every slot loads
into *everything*, the hop is worth paying. This is also what stops a `/read` branch-walk from crowding context:
it picks up light pointers on the way up and meets the heavy content only at the bottom, where you wanted it.

**Refinement — "thin up high," not "pointer up high" (2026-06-13 `/research`, preload-vs-pointer).** The corollary's
real lever is **altitude/leanness** — keep the always-loaded floor SMALL (outside research puts a context-rot threshold near ~20K tokens; a theory here, not measured, and not a cap),
where a wrong or bloated line pollutes every session — NOT "pointer-vs-content" per se. For a **SMALL, STABLE, authored
corpus like ours, do NOT pointer-ize the canon you actually load:** un-loaded knowledge is silently MISSED (our own
pointer-only desk canon left ~50% of facts invisible in blind tests until the SessionStart hook auto-injected content;
the research confirms silent-miss > context cost for small corpora). So: **THIN up high** (the few load-bearing lines +
**cross-branch** pointers to *other* domains you're not in), **full content on the branch you ARE in**, loaded
just-in-time by `/read`. Pointers are for cross-branch awareness, never for the spine of what a session needs. (RESEARCHED, 2026-06-13, preload-vs-pointer; the ~50% figure is OBSERVED in the author's own system, blind tests, before the SessionStart hook injected content.)

**Findability invariant — no buried treasure (the corollary's other half).** Moving content *down* must never
move its *findability* down with it. Whenever knowledge is placed into a deeper / specialist folder — sunk from a higher folder's canon, filed into a project's records, or parked in a playbook — **the domain that would reach for it must
be able to find it: leave a one-line pointer from where a future session would naturally look.** Leanness relocates
the *content*; the breadcrumb stays at the point of use. A note no one can locate from its domain is **lost, not
stored** — a pot of gold with no map. This is the standing answer to the *recall* problem (lean canon controls
what *loads*; it does nothing for how a cold session *finds* the right slice — retrieval is the hard part). The
pointer is **part of the placement, not optional cleanup** — see the archivist's findability gate in
`.claude/agents/archivist.md`.

## 4. How a folder declares its bar — the INTENT (every type, every folder)
Every folder — of **any** type (a canon, a skill folder, a project, a records area, a playbook) — carries its **intent**. For a standing folder that is its purpose (for a canon folder, `canon/purpose.md`; for a skill, its Intent section), written so it states the bar: what it takes to belong here. The router reads the same thing everywhere.

Optionally, a folder with a genuinely confusable neighbor adds **ONE near-miss redirect** — the single most
mistakable thing that does NOT belong, and where it goes instead:

```
intent:   <plain-English admission bar for this folder>
not:      <the one near-miss> → <its real folder>     # OPTIONAL, only where a real seam exists
```

Example (a subject's canon — note that the near-miss points DOWN at what sinks, never sideways at a sibling):
> **intent:** ONLY the high-level lines always true for any conversation about this subject — how it is
> structured + the standing conventions, plus pointers to the specialty detail.
> **not:** the deep detail of one area — full tax info, mortgage specifics, individual accounts → the sub-folder
> canons / records *below*.

**Guidance, each with its reason:**
- **One near-miss, NEVER an exclusion list.** Lists are infinite, they bloat, they rot, and worse — the LLM
  starts reading "not on the no-list" as "allowed." Name only the *one* boundary that's actually fuzzy.
- **For an always-on folder (root, a desk), the near-miss is usually the VERTICAL sink** — the specialty detail
  that should drop to a sub-folder *below* — NOT a sibling desk. An always-on canon loads every session, so its
  real bloat risk is holding depth only *some* sessions need; the bar is "high-level backbone + pointers, not depth."
- A folder with no confusable neighbor needs **no `not:` line** at all.
- The near-miss doubles as relocation guidance: it tells the archivist where to *send* a misfit.

## 5. The archivist's jobs under this doctrine (all PROPOSE-ONLY)
1. **Triage by type** — for each item it is handed (and each existing artifact under audit), FIRST decide which TYPE of
   folder it wants (§1). This includes **cull** (it's really a record → route to `records/`; or junk → propose
   dropping) and **propose a new SOP / skill / project** when a repeatable or self-contained thing has no folder yet.
2. **Place** — within the chosen type, land it in the right folder; for **canon**, run it up the levels to the
   highest where it can win a slot (§2–§3), against the folders' intents. (Uses the router, `.claude/skills/archivist-route`.)
3. **Audit, sink and raise** — periodically re-test EXISTING canon lines against their folder's purpose. Flag
   any that can **no longer win their slot** and should **sink lower**. Rarely, flag one that now holds for the
   whole parent and could **rise**. Rising is harder than sinking, by design (canon as gravity), but possible,
   and the person decides.
4. **Split** — flag a folder grown fat + broad enough to **split** into specialized children (which creates new
   lower shelves for sinkers). Pure judgment — **no size
   trigger, no math.**

The archivist **never moves anything.** It proposes; the human approves
(snapshot-first, dependency-gated). Applier, never legislator.

## 6. Authorship — who writes a folder's intent
- **The person writes the high-tier bars** (the root, each desk). Those are the person's own calls; they are never machine-guessed.
- **The archivist PROPOSES** the low / new / `[INFERRED]` intents for approval.

## 7. KISS — the complexity this keeps out, and why
- Plain-text intents and LLM judgment, with no numeric scoring, thresholds or "preponderance equations": placement is a judgment about meaning, and a score would look like precision while hiding the judgment (THE FRAME: a minimal harness).
  This exclusion is about filing (where a piece of knowledge sits); evidence points stay a judged weight, never a
  computed score.
- **One near-miss, never an exclusion list.**
- Type-routing adds **no machinery** — it's the same LLM reading §1's type list + each folder's `intent` and
  judging. Dumb core: a flat text inventory of folders + an LLM reading it. No engine beyond a cron + a read.

## 8. Self-application
This doctrine governs the archivist and `/save` — not every conversation — so it does **not** earn the always-loaded layer. Full text lives here (low, on-demand). At most a pointer in a `CLAUDE.md`. If we ever catch ourselves wanting to paste this into a `CLAUDE.md` or the root canon, that's the doctrine failing its own test — don't.
