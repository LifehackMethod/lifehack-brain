# Desk-Building SOP — v2

⛔ `.claude/skills/deskname/` is a placeholder example path, not a file in this repo.

> **Status: IN FORCE** (promoted by Enver, 2026-11-11: "the new one has to go in"; drafted on his word of 2026-11-06: "I think it's about time for us to start a draft and lock this in").
> Written by the coordinator from Enver's rulings of 2026-11-06 (canon) and the desk-architecture
> discussion; restructured the same day around the subscriber's journey. This page is `canon/desk-building-sop.md`.
> It supersedes the v1 desk SOP, which is archived whole with a banner at
> `system/_retired-2026-11-13/desk-building-sop.ARCHIVE-2026-11-13.md`. Where this SOP and his words differ, the
> difference goes to him to settle; it is not settled by a precedence rule.

---

# A complete desk has…
Every line traces to `canon/desk-building-sop.md`.

> **Words used here**
> - **desk** — one domain of a person's life (wealth, auditions, health), kept in its own folder `desks/<name>/`.
> - **card** — the desk's `desk.yaml`: three lines read by code before the model wakes; the model never sees it.
> - **canon** — what is durably true; lives in the desk's `canon/` folder.
> - **diary** — the dated tree, `diary/YYYY/MM/DD.md`, one entry per day.
> - **records** — the file cabinet: raw, undated research, search results, big documents.
> - **open loops** — `open-loops.md`: started, not finished — to improve, to build, broken, alerts fired.
> - **glasses** — the desk's `CLAUDE.md`: the model's day-one note (who this desk is, how to talk here, what matters).
> - **platform** — the plugin and shared code: everything that runs a desk, once, identical for everyone.
> - **door** — the build-mode checks a desk must pass (§5, the six check lines).
> - **tile / status note** — a JSON status snapshot a desk's job or skill writes through `emit_status.py`.
> - **`/deskname`** — the SOP's placeholder example for a desk's command; `.claude/skills/deskname/` is a placeholder example path, not a file in the repo.

## 1. Every complete desk has…

- Eight items in `desks/<name>/`: `canon/canon.md` and `canon/purpose.md` (both inside `canon/`), `records/`, `diary/`, `open-loops.md`, `desk.yaml` (the card), `CLAUDE.md` (the glasses), and `projects/` (one `projects/<slug>/` folder per project started from this desk, holding its brief, same shape as the root `projects/`). → §2; §7 birth step 1
- A card holding only its three facts — name, canon, diary. Anything else is rejected. → §2; §5 check 1; §7 birth step 2
- Every pointer on the card resolving to a real file. → §5 check 2
- Canon sitting where the card says it does. → §5 check 4
- Nothing that duplicates a fact owned elsewhere: jobs belong to the job list, access grants to the capability registry, status notes to their producers. One fact, one place. → §2; §5 check 3
- Nothing that runs. The loader, the diary pen, the guards, the doors, the job runner and the status writer live once in the plugin; the desk never contains a copy. → §2; §3
- No copied shared tools: the desk uses the platform's tools or its own — skills in `~/.claude/skills/<name>/`, scripts in the personal code folder, with `desks/<name>/tools/` only for code that truly serves this one desk. → §3; §5 check 6
- Any jobs it ships passed through the job door (`--check-row` PASS). → §5 check 5
- A `purpose.md` of two lines saying why this domain exists. → §2; §7 birth step 3
- Glasses in their own file, the desk's seventh item — not folded into `purpose.md` (purpose is knowledge; glasses are instructions). → §6; §8 point 4
- Glasses that fit, with the plugin's and the personal root's `CLAUDE.md`, with their combined size tracked against the 200-line reference, not capped. → §6; §8 point 4
- A diary made when the desk was created, called `<Desk>-Diary` (the planning desk's is Planning-Diary); shared code knows only that pattern, never a desk's name. → §6
- One diary page per day: each machine read appends its own low-confidence entry, the person's sessions add high-confidence lines, and the machine never overwrites a high-confidence line; each entry a spare boil-down plus pointers to the raw records. → §6; §8 point 3
- Exactly two machine-readable artifacts: the card (`desk.yaml`, YAML) and whatever its producers emit as status tiles (JSON). All knowledge is prose. → §8 point 1
- A card that never lists its tiles: tiles are written through the single writer `emit_status.py` and register by existing in `status/` at the brain folder's root, named for the producer. → §3; §8 point 2
- A `/deskname` command (placeholder example) created with the desk, working in the CLI and the Anthropic app both. → §5; §7 birth step 5
- A registry row: an index line that points the loader at the card and holds none of the card's facts. → §7 birth step 6

## 2. In these situations…

- If building a desk → it is build mode, not use mode. The desk is born by writing knowledge and a card, never by building machinery. → §5
- If building a desk → the birth sequence is: (1) scaffold or hand-write the eight items; (2) fill the card's three lines; (3) write two lines of purpose and two lines of canon; (4) the door checks it; (5) the `/deskname` command invocation is created; (6) the registry row is added. The first real desk's run corrects this sequence. → §7
- If the door names a problem → fix what it names and re-run. → §7 birth step 4
- If it is the planning desk, or any desk that ships with the harness → same shape; everything that runs it lives in the platform. → §2
- If something should behave the same for every desk → it is platform machinery, and the desk never contains a copy. → §3
- If a desk needs a special tool → it lives in personal code, not in the desk (`desks/<name>/tools/` only for code that truly serves this one desk). → §3; §9
- If deciding where a fact goes → at the broadest scope where it is always true, no higher, no lower. → §1
- If canon is nested below a desk → it is true for that desk's subfolders (vertical), never for siblings (lateral); the loader flags nested canon as not loaded. → §1; §4
- If something is too big for a spare diary entry → it was never diary material; it is a record, and the entry points at it. → §6
- However a roll-up is assembled → it is a low-confidence computer assumption until a human validates it. → §6
- If summarizing unattended → never touch hard-to-summarize work; the unattended step only handles what was already spare. → §6
- If judging trust → canon is trusted because of where it sits; everywhere else starts from a default of doubt; confidence accumulates as points of evidence; a load-bearing decision needs a human sign-off. → §1; §3
- If a tile is written → its `stale_after_s` (the producer's rhythm) is set in the envelope; its `detail` field points into the diary or records. → §8 points 3, 5
- If opening a desk → folder, shortcut or the `/deskname` command all set the same fact, "this window is in this desk"; the command route is what makes desks work in the Anthropic app. → §4
- If a session starts in a desk → the session-start hook reads the card, loads the root canon and the one desk's canon (never sideways), and injects the actual text. → §4
- If pulling canon on demand → the read-canon subagent searches the folders, does not trust the filing, and returns canonical passages verbatim, never summarized. → §4
- If choosing protection for a desk's things → the person chooses which get fine china protection A (an ask before an edit) or B (no delete); protection C (a speed bump with a sign before a mass delete — a whole folder or hundreds of files) covers every folder. → §5
- If it is fine china outside git (canon always lives in git) → protection B is a hard block with no override. → §5
- If protection C applies → it is a speed bump with a sign, never a hard block or a pop-up. → §5
- If nobody is at the screen → protections A and B are denied with a sign and parked for the morning, and the run carries on; protection C's sign is logged and the action waits for the morning rather than being blocked outright. → §5
- If someone wants to see the desk (dashboard, alert) → that is the person's business, not the desk's or the plugin's; looking is free, touching goes through the door. → §3; §9
- If this SOP and Enver's words differ → the difference goes to him to settle; no precedence rule settles it. → the header at the top

## 3. Good practice

- Write for a blind reader with a finite context window: what is absorbable, not what is tidy. → §1
- Start small: the desk is born walking; everything else accretes. → §7 birth step 3; §9
- Canon is expected to change rarely — "edited on the order of every six months, changed by big life events". → §2; §8 point 3
- Structured data only where a program parses, prose where a model reads; do not format diaries for robots. → §8 point 1
- Treat organization as a bonus, not a load-bearing assumption. → §4
- Keep the skeleton boring: the schema stable and dull while everything living flows through it. → §1
- The glasses carry two biases: lean toward the newer; read trust by location. → §6

— end of checklist —

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
  only that something is stale but exactly how stale. Diary roll-ups and trajectories are assembled on demand, at
  whatever resolution the question needs.
- **Trust** — read by location: canon is canon because of where it sits; everywhere else starts from a default of
  doubt. Confidence accumulates as
  points of evidence, and a load-bearing decision needs a human sign-off. Written text carries no trust metadata;
  the machinery supplies it. (Canonical principles SOP §7.0.)

**The system is an organism, not a flat folder schema.** The closet of clothes works until it doesn't; V2 is the
point where organization became metabolism. Canon is DNA (rarely changed, human-gated, inherited vertically, thin).
The diary is metabolism (§6) — current state is produced by the system, not maintained by hand. The guards are the
immune system: layered, lightest first. Open loops are the repair ledger. A desk is a graft that takes because the
organism already has the organs. Organisms grow tumors — machinery accreting per desk — and the shared-code rule and
the doors are the anti-cancer. The skeleton stays boring: the schema is stable and dull while everything living flows
through it.

**We birth the healthiest possible baby.** The system gives a person the best option of growing healthy tissue; what
they choose to do once they're grown is their business. Friction protects against the dumb LLM and the accident —
it was never a warranty against choice. (canon.)

---

## 2. What a desk is — the shape

**A desk is a domain of knowledge plus a three-line card, and nothing that runs.**
A desk that ships with the harness (the planning desk; Enver's ruling, 2026-11-16) has the same shape: everything that runs it lives once in the platform, as for every desk.

```
desks/<name>/
├── canon/          ← durably true; edited on the order of every six months, changed by big life events
│   ├── canon.md    ← the desk's canon
│   └── purpose.md  ← why this domain exists (2 lines)
├── records/        ← the file cabinet: raw, undated research, search results, big documents
├── diary/          ← the dated tree: YYYY/MM/DD.md, one page per day
├── open-loops.md   ← started, not finished: to improve, to build, broken, alerts fired
├── desk.yaml       ← the card: name, canon, diary — nothing else
├── CLAUDE.md       ← the desk's glasses, in its own file: the seventh item (section 8, point 4)
└── projects/<slug>/  ← projects started from this desk: each folder holds its brief (same shape as the root `projects/`)
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
  (canon); its standalone scripts and tools live in the personal code folder, one folder for the whole person, with
  `desks/<name>/tools/` only for code that truly serves one desk (canon). Personal, update-safe, freely changeable;
  can never break the platform.
- **The interface (status emission):** the desk's producers emit status notes through the single writer
  (`emit_status.py`); notes self-register by existence in `status/` at the brain folder's root; the card never lists them. What
  compliance buys: visibility everywhere — dashboards, alerts, diary roll-ups, every renderer that ever gets built.
  (Full spec: the Status Emission SOP. Not restated here.)
- **The clients (rendering):** delegated and unowned. Looking is free; touching goes through the door. How the
  desk's state is displayed is the person's business, not the desk's and not the plugin's.
- **The knowledge axes:** canon inherits vertically down the pyramid, never laterally; every artifact type carries
  its shelf-life (canon: years; diary: days; tiles: seconds); trust is read by location (canon by where it sits, a
  default of doubt everywhere else), confidence accumulates as points, and a load-bearing decision needs a human
  sign-off.

---

## 4. Two kinds of loading, two doors

- **The baseline:** the session-start hook reads the card, loads the root canon and the one desk's canon (never
  sideways; canon nested below the desk is flagged as not loaded), and injects the actual text. Deterministic, free, small. The one deliberate human act —
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

The door is `shared/desk_door.py` (it exists and is tested). **Not built into the scaffold yet:** the desk scaffold script does not call it, so it is run by hand.

**Fine china protections.** Which of a desk's things get protection A or B is chosen by the person; protection C
covers every folder; what each protection does is fixed. All three are there "to prevent broad catastrophic events
from a misguided agent" (`canon/build-conformance-sop.md` §2 (the asks) and §5.11 (the friction levels)):
- **Fine china protection A** — "can't edit it without talking to the human first" (an ask before an edit).
- **Fine china protection B** — "can't delete it" (no delete). Canon always lives in git, so "outside git" means fine china only. For canon and fine china outside git, protection B is
  a hard block with no override (canon).
- **Fine china protection C** — a speed bump with a sign in front of a mass delete (a whole folder or hundreds of
  files), on any folder, to slow down a possible catastrophic event. It is never a hard block or a pop-up.

The guards are the hooks `system/hooks/guard_fine_china_ask.sh` and `system/hooks/guard_canon_write.sh`, with the helpers `system/hooks/lib/fine_china_ask.py` and `system/hooks/lib/fc_sign.py`.

With nobody at the screen, the ask of protection A becomes a refusal (the session stops and tells the person), and protection B stays a refusal; protection C's sign is logged and the action waits for the morning rather than being blocked outright.

---

## 6. The diary economy

Each desk's diary is made when the desk is created, and is called `<Desk>-Diary`: the planning desk's is Planning-Diary. Shared code knows only that pattern, not any desk's name.

One page per desk per day. There is no single midnight writer: each machine read appends its own low-confidence entry to that day's page; the person's sessions add high-confidence lines; the machine alone never overwrites a high-confidence line, so the page can be rewritten but never over the person's own words. Any desk appends through `append_entry` in `shared/diary_page.py`. Each entry is a spare boil-down plus
pointers to the raw records. Size is controlled upstream, at generation — anything bigger was never diary material;
it's a record, and the entry points at it. Weekly/monthly/quarterly/annual roll-ups are assembled on demand as
low-confidence computer assumptions; they become high-confidence only when a human validates them. Unattended
summarization never touches hard-to-summarize work; the unattended step only handles what was already spare.

**The skeleton is three pieces:** the glasses (CLAUDE.md — plural: plugin, personal root, per desk, the per-desk one
in its own file as the desk's seventh item, with a total size budget across the three — carrying the two biases: lean toward the newer; read trust by location (canon by where it sits, a
default of doubt elsewhere)), the card, and the diary (§6). Everything else exists or flows from these.

---

## 7. Ground — how it runs *(the first real desk's run corrects this section — per the house rule, a real proof beats a passing test, and no SOP keeps lessons it hasn't earned)*

**The birth sequence:**
1. Scaffold (or hand-write) the eight items: canon and purpose (both inside `canon/`), records, diary, open-loops,
   the card, the desk's CLAUDE.md (the glasses), and `projects/` (for projects started from this desk).
2. Fill the card — three lines: name, canon, diary.
3. Write two lines of purpose, two lines of canon. The desk is born walking; everything else accretes.
4. The door checks it (section 5's list); fix what it names, re-run.
5. The AI creates the `/deskname` command in the person's own skills folder (`~/.claude/skills/<desk>/`, never inside the plugin), CLI and Anthropic app both. (Nothing creates it today; adding it to the scaffold is open work.)
6. The desk scaffold script adds the registry row, through the shared desk-list tool: an index line that points the loader at the card and holds none of the card's facts
   (one fact, one place); the desk now exists for the loader.

**The launch sequence (every session, compressed):** the human chooses the desk — shortcut, folder, or command; the
one deliberate act. The glasses go on (the harness brief, plus the desk's CLAUDE.md, within the shared
budget). The hook reads the card, chain-loads the canon, injects the text — code, not model. The model wakes
situated. Work happens guarded (every tool call through the policy friction points). Raw output lands in records.
Machine reads append their spare boil-downs, with pointers, to the day's diary page (§6). Any future session can walk the
diary tree at whatever resolution a question needs, cheaply.

---

## 8. THE SEAM — what the interface taught the desk (2026-11-06)

*(These five sharpenings came out of an earlier desk project's archaeology; they are the two SOPs meeting in the middle of the
mountain. Confidence: high on 1, 2, 3, 5 — restatements of ruled things seen together; point 4 is settled: the
glasses are their own file.)*

**1. Two machine formats, everything else prose.** A desk contains exactly two machine-readable artifacts: the
manifest (`desk.yaml`, YAML) and whatever its producers emit as status tiles (JSON). All knowledge is unstructured
prose, because its consumer is an LLM and prose is an LLM's native food. A deliberate format-per-consumer
decision: structured data where a program parses, prose where a model reads. Prevents the over-structuring
mistake (formatting diaries for robots no robot reads).

**2. Tiles are the desk's pulse, and the card never mentions them.** A desk's jobs and skills emit status tiles
through the shared single writer (`emit_status.py`), as a byproduct of metabolism. Tiles self-register by
existence — **convention over configuration**: registration happens by being in `<brain>/status/` (the brain folder's root), named for the
producer; no declaration lists. The manifest stays three lines because it holds only facts no other system owns.
The seam between the two SOPs is zero-declaration: the desk never lists its tiles; the status interface never
asks. (Organism capstone: the tile is the desk's pulse — literally the Pulse machinery.)

**3. Every artifact type carries its freshness horizon.** Canon: years (should not have to be edited more than every
six months; changed by life earthquakes). Diary: days (one page per day, entries appended; §6). Tiles: seconds
(`stale_after_s`, the producer's intended rhythm, set in the envelope). Each type has its own horizon — milk,
canned soup, whiskey: each aisle knows its own dates. The reader derives staleness by comparing last-verified time
against that rhythm (a TTL). The date axis made mechanical.

**4. The per-desk glasses — a second, tiny ID file for the model.** The manifest is read by CODE (the loader
hook, pre-injection; the model never sees it). But the model needs its own day-one note — who this desk is, how
to talk here, what matters — and that is the per-desk CLAUDE.md, the third layer of the plural CLAUDE.md stack
(plugin → personal root → desk), injected into the context window as system-prompt material. Two files, two
audiences, two delivery mechanisms. The combined size of all three layers is tracked, not capped (no number is set; the vendor's 200-line reference is the yardstick), because injected
context is paid for every turn — the guard against context bloat. It is its own file, the desk's seventh item, not
folded into purpose.md (purpose is knowledge and decays slowly; glasses are instructions and decay differently).

**5. Now, always, raw — the three tenses of a desk.** Tiles are NOW: current-state snapshots, whiteboard
semantics, last-write-wins, idempotent overwrite. The diary is ALWAYS: the event log, one page per day, each machine read appending its own entry and never overwriting the person's high-confidence lines — event
sourcing, state derived never stored. Records are RAW: the undated archive. The tile's `detail` field is a
pointer from the snapshot layer into the event log or the archive — a cross-layer reference that keeps "now"
honest by always able to say "here's the history behind me." Three layers, three tenses, one pointer: the
complete data model of a desk, and the exact point where the two SOPs shake hands.

---

## 9. The dummy version — a primer for future readers

**A desk is a room in your life.** A finance desk is your money room. An auditions desk is your auditions room. Each room keeps its own
stuff so a conversation about money doesn't drag your headshots into it.

**The room has eight shelves, and only three of them matter at first:**
- **What's true for years** (canon) — the whiskey. "I'm married. My agent is <name>." Changes only in a life
  earthquake, no more than every six months or so.
- **What happened today** (the diary) — the milk. One short page per day, added to by machine reads and by you, never
  overwritten over your own high-confidence lines (§6): what got done, in a few spare lines, with a pointer to where the full story lives.
- **The raw pile** (records) — the file cabinet. Every search result, every big document, unsorted and undated.
  It's fine that it's a mess; nobody reads it wholesale, they dig when pointed.
- Plus: **why the room exists** (purpose, two lines), **the to-fix list on the door** (open loops — broken things,
  ideas to build, alerts that fired), **the name tag** (the card), **the glasses** (the desk's CLAUDE.md, below), and **the projects shelf** (one folder for each project started in this room).

**The name tag (the card) is three lines: who I am, where my truth lives, where my diary goes.** A robot butler
reads it, in the split second before you even start talking, and quietly sets the room up for you: the right
truth on the desk, the right glasses on your face. You never see the name tag. It's not for you — it's for the
butler.

**The glasses (the desk's CLAUDE.md) are the note the new intern gets on day one:** how to talk in this room, what
matters here, what the boss likes. Three pairs of glasses get worn at once — the building's, yours, and this
room's — and together they can't be too heavy, because you pay for them every single minute you work.

**The room remembers on its own.** Whenever a machine read happens, a little robot adds its own low-confidence entry to the day's page in the diary (§6) —
nobody maintains it by hand. When someone asks, another robot squints at the week's pages and drafts a
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
