# Desk-Building SOP — v2

⛔ `.claude/skills/deskname/` is a placeholder example path, not a file in this repo.

> **Status: IN FORCE** (promoted by Enver, 2026-11-11: "the new one has to go in"; drafted on his word of 2026-11-06: "I think it's about time for us to start a draft and lock this in").
> Written by the coordinator from Enver's rulings of 2026-11-06 (P-128 to P-132) and the desk-architecture
> discussion; restructured the same day around the subscriber's journey. This page is `system/sops/desk-building-sop.md`.
> It supersedes the v1 desk SOP, which is archived whole with a banner at
> `system/_retired-2026-11-13/desk-building-sop.ARCHIVE-2026-11-13.md`. Where this SOP and his words differ, the
> difference goes to him to settle; it is not settled by a precedence rule.

---

## 1. 10,000 ft — Why desks exist

**In the stack: a desk is the business logic layer's unit** — the tenant's domain of knowledge, run entirely by
platform machinery, served to delegated renderers. In the car picture, a desk is part of the car trim and options
(the configuration layer: desks, personal skills, settings); its folder sits in the brain folder (the driver's logbook: the
knowledge layer; `shared/brain_root.py` finds it), and its tools in personal code (the car model: the personal code
layer; `shared/personal_code_root.py` finds it). Layers are kinds of content; folders are where they sit. Everything
below follows from that.

**The audience is a blind reader with a finite context window.** Every decision below serves one reader: a stateless
LLM, future, with no background, that can only absorb so much at once and gets overloaded easily. Not what's tidy for
a human — what's absorbable by that reader. (Enver, 2026-11-06.)

**A desk is a domain of a person's life.** Wealth, auditions, health — each desk keeps canonical knowledge for one
subdomain so that a session in that domain doesn't carry the others. It is different for everybody; the
machinery serves any of them identically.

**Knowledge has three axes: place, date, trust.**
- **Place** — the altitude ladder: every fact lives at the broadest scope where it is always true, no higher, no
  lower. Canon is the pyramid tip: thin, durable truth, true for all subdomains below. It inherits vertically (a
  desk's canon is true for its subfolders) and never laterally (sibling canon is not true for each other).
- **Date** — the diary tree: the dated axis, separate from records and research. Its structure tells a reader not
  only that something is stale but exactly how stale. Throughlines and trajectories are assembled on demand, at
  whatever resolution the question needs.
- **Trust** — read by location: canon is canon because of where it sits; everywhere else starts from a default of
  doubt. Confidence accumulates as
  points of evidence, and a load-bearing decision needs a human sign-off. Written text carries no trust metadata;
  the machinery supplies it. (Canonical principles SOP §7.0.)

**The system is an organism, not a flat folder schema.** The closet of clothes works until it doesn't; V2 is the
point where organization became metabolism. Canon is DNA (rarely changed, human-gated, inherited vertically, thin).
The diary cron is metabolism — current state is produced by the system, not maintained by hand. The guards are the
immune system: layered, lightest first. Open loops are the repair ledger. A desk is a graft that takes because the
organism already has the organs. Organisms grow tumors — machinery accreting per desk — and the shared-code rule and
the doors are the anti-cancer. The skeleton stays boring: the schema is stable and dull while everything living flows
through it.

**We birth the healthiest possible baby.** The system gives a person the best option of growing healthy tissue; what
they choose to do once they're grown is their business. Friction protects against the dumb LLM and the accident —
it was never a warranty against choice. (P-132.)

---

## 2. What a desk is — the shape

**A desk is a domain of knowledge plus a three-line card, and nothing that runs.**

```
desks/<name>/
├── canon/          ← durably true; edited on the order of every six months, changed by big life events
│   ├── canon.md    ← the desk's canon
│   └── purpose.md  ← why this domain exists (2 lines)
├── records/        ← the file cabinet: raw, undated research, search results, big documents
├── diary/          ← the dated tree: YYYY/MM/DD.md, one entry per day
├── open-loops.md   ← the debt ledger: to improve, to build, broken, alerts fired
├── desk.yaml       ← the card: name, canon, diary — nothing else
└── CLAUDE.md       ← the desk's glasses, in its own file: the seventh item (section 8, point 4)
```

The card holds only facts no other machinery owns. Jobs are rows in the job list (the door checks them); access
grants live in the capability registry. One fact, one place. The card is read by code before the model wakes; the
model never sees it.

---

## 3. How a desk meets every layer

One pass over the whole stack, from the desk's point of view:

- **The car platform (the platform layer: shared code, the plugin):** everything that runs the desk — the loader, the diary pen, the guards, the doors,
  the job runner, the status writer — lives once, in the plugin, identical for everyone. It *consumes* the card and
  never modifies the desk. If it should behave the same for every desk, it is platform machinery and a desk never
  contains a copy of it.
- **The tenant (the car model: the personal code layer; the car trim and options: the configuration layer):** the
  desk's skills live in Claude's own folder, `~/.claude/skills/<name>/`
  (P-50); its standalone scripts and tools live in the personal code folder, one folder for the whole person, with
  `desks/<name>/tools/` only for code that truly serves one desk (P-51). Personal, update-safe, freely changeable;
  can never break the platform.
- **The interface (status emission):** the desk's producers emit status notes through the single writer
  (`emit_status.py`); notes self-register by existence in `status/` at the brain folder's root; the card never lists them. What
  compliance buys: visibility everywhere — dashboards, alerts, throughlines, every renderer that ever gets built.
  (Full spec: the Status Emission SOP. Not restated here.)
- **The clients (rendering):** delegated and unowned. Looking is free; touching goes through the door. How the
  desk's state is displayed is the person's business, not the desk's and not the plugin's.
- **The knowledge axes:** canon inherits vertically down the pyramid, never laterally; every artifact type carries
  its shelf-life (canon: years; diary: days; tiles: seconds); trust is read by location (canon by where it sits, a
  default of doubt everywhere else), confidence accumulates as points, and a load-bearing decision needs a human
  sign-off.

---

## 4. Two kinds of loading, two doors

- **The baseline:** the session-start hook reads the card, chain-loads the canon down the pyramid (root → desk →
  subfolder, never sideways), and injects the actual text. Deterministic, free, small. The one deliberate human act —
  opening the desk, by shortcut, folder, or `/deskname` (⛔ placeholder example path) command — is the trigger; everything after is code.
- **The pull (read-canon):** a subagent that searches the folders, does NOT trust the filing, and returns canonical
  passages VERBATIM — never summarized. On demand, from any window, any desk. Organization is a bonus, not a
  load-bearing assumption.

Both front doors — folder, shortcut, `/deskname` (⛔ placeholder example path) command — set the same fact, "this window is in this desk," and the
machinery acts on it identically. The command route is what makes desks work in the Anthropic app, where there is no
folder to open.

---

## 5. The desk door — build mode

Building a desk is build mode, not use mode — the invisible line where a user can really damage things. A desk is
born by writing knowledge and a card — never by building machinery. Building a desk also creates its `/deskname` (⛔ placeholder example path)
command invocation, working in the CLI and the Anthropic app both.

**The door's checks, the list a subscriber's desk must pass:**
1. The card parses and holds only its three facts — name, canon, diary. Anything else is rejected.
2. Every pointer on the card resolves to a real file.
3. Nothing duplicates a fact owned elsewhere (jobs belong to the job list; access grants to the capability registry;
   status notes to their producers).
4. Canon sits where the card says it does.
5. Any jobs the desk ships go through the job door (`--check-row` PASS).
6. No copied shared tools — a desk uses the platform's tools or its own: skills in `~/.claude/skills/<name>/`,
   scripts in the personal code folder (`desks/<name>/tools/` only for code that serves this one desk).

**Fine china protections.** Which of a desk's things get protection A or B is chosen by the person; protection C
covers every folder; what each protection does is fixed. All three are there "to prevent broad catastrophic events
from a misguided agent" (`system/sops/build-conformance-sop.md` §2 (the asks) and §5.11 (the friction levels)):
- **Fine china protection A** — "can't edit it without talking to the human first" (an ask before an edit).
- **Fine china protection B** — "can't delete it" (no delete). For canon and fine china outside git, protection B is
  a hard block with no override (P-136).
- **Fine china protection C** — a speed bump with a sign in front of a mass delete (a whole folder or hundreds of
  files), on any folder, to slow down a possible catastrophic event. It is never a hard block or a pop-up.

With nobody at the screen, protections A and B are denied with a sign and parked for the morning, and the run
carries on; protection C's sign is logged and the action waits for the morning rather than being blocked outright.

---

## 6. The diary economy

One entry per desk per day, written by a per-desk cron job at end of day: a spare boil-down of that day plus
pointers to the raw records. Size is controlled upstream, at generation — anything bigger was never diary material;
it's a record, and the entry points at it. Weekly/monthly/quarterly/annual roll-ups are built by cron as
low-confidence computer assumptions; they become high-confidence only when a human validates them. Unattended
summarization never touches hard-to-summarize work; the unattended step only handles what was already spare.

**The skeleton is three pieces:** the glasses (CLAUDE.md — plural: plugin, personal root, per desk, the per-desk one
in its own file as the desk's seventh item, with a total size budget across the three — carrying the two biases: lean toward the newer; read trust by location (canon by where it sits, a
default of doubt elsewhere)), the card, and the diary cron. Everything else exists or flows from these.

---

## 7. Ground — how it runs *(the first real desk's run corrects this section — per the house rule, a real proof beats a passing test, and no SOP keeps lessons it hasn't earned)*

**The birth sequence:**
1. Scaffold (or hand-write) the seven items: canon and purpose (both inside `canon/`), records, diary, open-loops,
   the card, and the desk's CLAUDE.md (the glasses).
2. Fill the card — three lines: name, canon, diary.
3. Write two lines of purpose, two lines of canon. The desk is born walking; everything else accretes.
4. The door checks it (section 5's list); fix what it names, re-run.
5. The `/deskname` (⛔ placeholder example path) command invocation is created — CLI and Anthropic app both.
6. The registry row is added: an index line that points the loader at the card and holds none of the card's facts
   (one fact, one place); the desk now exists for the loader.

**The launch sequence (every session, compressed):** the human chooses the desk — shortcut, folder, or command; the
one deliberate act. The glasses go on (the harness brief, plus the desk's CLAUDE.md, within the shared
budget). The hook reads the card, chain-loads the canon, injects the text — code, not model. The model wakes
situated. Work happens guarded (every tool call through the policy friction points). Raw output lands in records.
At midnight, the desk's diary cron writes the day's spare boil-down with pointers. Any future session can walk the
diary tree at whatever resolution a question needs, cheaply.

---

## 8. THE SEAM — what the interface taught the desk (2026-11-06)

*(These five sharpenings came out of the Helm archaeology; they are the two SOPs meeting in the middle of the
mountain. Confidence: high on 1, 2, 3, 5 — restatements of ruled things seen together; point 4 is settled: the
glasses are their own file.)*

**1. Two machine formats, everything else prose.** A desk contains exactly two machine-readable artifacts: the
manifest (`desk.yaml`, YAML) and whatever its producers emit as status tiles (JSON). All knowledge is unstructured
prose, because its consumer is an LLM and prose is an LLM's native food. A deliberate format-per-consumer
decision: structured data where a program parses, prose where a model reads. Prevents the over-structuring
mistake (formatting diaries for robots no robot reads).

**2. Tiles are the desk's pulse, and the card never mentions them.** A desk's jobs and skills emit status tiles
through the shared single writer (`emit_status.py`), as a byproduct of metabolism. Tiles self-register by
existence — **convention over configuration**: registration happens by being in `status/` at the brain folder's root, named for the
producer; no declaration lists. The manifest stays three lines because it holds only facts no other system owns.
The seam between the two SOPs is zero-declaration: the desk never lists its tiles; the status interface never
asks. (Organism capstone: the tile is the desk's pulse — literally the Pulse machinery.)

**3. Every artifact type carries its freshness horizon.** Canon: years (should not have to be edited more than every
six months; changed by life earthquakes). Diary: days (one append-only entry per day). Tiles: seconds
(`stale_after_s`, the producer's intended rhythm, set in the envelope). Each type has its own horizon — milk,
canned soup, whiskey: each aisle knows its own dates. The reader derives staleness by comparing last-verified time
against that rhythm (a TTL). The date axis made mechanical.

**4. The per-desk glasses — a second, tiny ID file for the model.** The manifest is read by CODE (the loader
hook, pre-injection; the model never sees it). But the model needs its own day-one note — who this desk is, how
to talk here, what matters — and that is the per-desk CLAUDE.md, the third layer of the plural CLAUDE.md stack
(plugin → personal root → desk), injected into the context window as system-prompt material. Two files, two
audiences, two delivery mechanisms. All three layers share a total token budget (P-131), because injected
context is paid for every turn — the guard against context bloat. It is its own file, the desk's seventh item, not
folded into purpose.md (purpose is knowledge and decays slowly; glasses are instructions and decay differently).

**5. Now, always, raw — the three tenses of a desk.** Tiles are NOW: current-state snapshots, whiteboard
semantics, last-write-wins, idempotent overwrite. The diary is ALWAYS: the append-only event log — event
sourcing, state derived never stored. Records are RAW: the undated archive. The tile's `detail` field is a
pointer from the snapshot layer into the event log or the archive — a cross-layer reference that keeps "now"
honest by always able to say "here's the history behind me." Three layers, three tenses, one pointer: the
complete data model of a desk, and the exact point where the two SOPs shake hands.

---

## 9. The dummy version — a primer for future readers

**A desk is a room in your life.** Marc is your money room. Emily is your auditions room. Each room keeps its own
stuff so a conversation about money doesn't drag your headshots into it.

**The room has seven shelves, and only three of them matter at first:**
- **What's true for years** (canon) — the whiskey. "I'm married. My agent is Formation." Changes only in a life
  earthquake, no more than every six months or so.
- **What happened today** (the diary) — the milk. One short page per day, written by a robot at midnight, never
  edited: what got done, in a few spare lines, with a pointer to where the full story lives.
- **The raw pile** (records) — the file cabinet. Every search result, every big document, unsorted and undated.
  It's fine that it's a mess; nobody reads it wholesale, they dig when pointed.
- Plus: **why the room exists** (purpose, two lines), **the to-fix list on the door** (open loops — broken things,
  ideas to build, alerts that fired), **the name tag** (the card), and **the glasses** (the desk's CLAUDE.md, below).

**The name tag (the card) is three lines: who I am, where my truth lives, where my diary goes.** A robot butler
reads it, in the split second before you even start talking, and quietly sets the room up for you: the right
truth on the desk, the right glasses on your face. You never see the name tag. It's not for you — it's for the
butler.

**The glasses (the desk's CLAUDE.md) are the note the new intern gets on day one:** how to talk in this room, what
matters here, what the boss likes. Three pairs of glasses get worn at once — the building's, yours, and this
room's — and together they can't be too heavy, because you pay for them every single minute you work.

**The room remembers on its own.** At midnight, a little robot comes in and writes the day's page in the diary —
not you, not the intern, nobody maintains it. Once a week another robot squints at the week's pages and drafts a
summary, marked "computer's guess — don't fully trust me" until a human glances at it and says "yes, that's
right." That's the confidence ratchet: the system proposes, your glance promotes.

**The room owns nothing that runs.** No machinery in the room — every machine belongs to the building (the
plugin) and serves every room identically. If your money room needs a special tool, it lives in your personal
workshop next door (personal code), not in the room. That's why a room can be born in an afternoon: write the
name tag, two lines of truth, two lines of purpose — the building already knows how to run rooms. Born walking,
like a deer.

**And the room never says how it looks.** If you want to *see* your rooms — a dashboard, an alert, anything —
that's looking, and looking is somebody else's job. The room just keeps honest labels on everything: when, who,
how it went. Anyone can look; nobody may touch without going through the door.

---

*Companion: the Status Emission SOP (the interface spec). The two meet in the middle of the mountain.*
