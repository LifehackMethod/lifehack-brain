# Where things go in your notes folder

> The map of the **second** folder — the one that is yours. Every tool in this repo that writes
> something writes it at one of the paths on this page, and gets the folder itself from one place:
> `shared/brain_root.py`. If you are adding a tool and the path you want is not here, the path is
> wrong or this page is incomplete — resolve that before writing code.

## The one rule this all rests on

From `README.md`, verbatim:

> **The tool goes in one folder. Your notes go in a different one.**
>
> **One rule about where the tool folder goes: keep it out of your cloud folder.** Not inside Google
> Drive, not inside Dropbox, not inside OneDrive, not inside iCloud Drive. Anywhere else is fine —
> your home folder is perfect.
>
> **Your notes folder is the opposite: put it wherever you like, cloud included.**

Everywhere below, `<notes>/` means the folder that rule is about — whatever
`shared/brain_root.py` resolves. Not the current directory, not the repo, not a guess. When it is not
set, the honest answer is "not set" and the tool refuses.

## The shape

```
<notes>/
├── canon.md                        the few things that stay true. small on purpose.
├── system/
│   ├── journal.md                  append-only. what happened, when, why.
│   ├── journal/YYYY-MM.md          older months, rotated out of the above
│   ├── project-registry.md         one row per project — the thing that makes a project findable
│   └── learnings.md                what the system learned about running itself
├── state/
│   ├── projects/<slug>/            one folder per project — see "A project" below
│   ├── briefs/<slug>.md            older flat briefs. read, never written. see "Two brief shapes".
│   ├── open-loops.md               started, not finished
│   ├── debt-ledger.md              known-imperfect, deliberately deferred
│   └── current.md                  where things stand right now
├── records/<type>/                  everything found, decided or written down — see "Types" below
├── plans/<name>.md                  plans are yours, not the tool's
├── config/                          settings that are specific to you (IDs, accounts, rate cards)
├── councils/                        rosters of advisors, if you use them
├── memory/
│   └── topic-vocab.md               your subjects, in your words — written by you, never shipped
└── desks/<subject>/                 one folder per subject, built by `/ingest` from your material
    ├── canon/current.md
    ├── canon/purpose.md
    └── records/
```

> **A note on the word `desks`.** That is the folder name `/ingest` writes, and it is kept because the
> code writes it. In anything you *say* to a person it is "a folder per subject" — `/ingest`'s own
> voice rules ban the jargon out loud while the path keeps it. Don't rename the folder to fix the
> vocabulary; the fix is in how you talk, and it is already made.

Three of those exist on day one and nothing else does: `system/journal.md`,
`system/project-registry.md`, and the projects folder. `system/tools/bootstrap.py` makes exactly those
and refuses to make more, for the reason written at the top of that file — which subjects your life
divides into is yours to discover, and a starter folder is a guess that teaches itself as the answer.

## A project

A project is a **folder**, and the folder's name is the project's slug:

```
<notes>/state/projects/<slug>/
├── brief.md          the living document. one per project, for its whole life, updated in place.
├── records/          this project's own findings — kept here, where the project can see them
└── canon/current.md  what this project has settled
```

**The folder's last path segment must equal the slug.** A category above it is fine
(`state/projects/infrastructure/<slug>/`); the leaf is not. This stops the drift where a project
called one thing lives in a folder called another and a cold session finds neither.
`system/tools/check_slug_folder.py` audits it.

Its row in `<notes>/system/project-registry.md` is five fields, pipe-separated:

```
{desk} | {slug} | {display name} | {status} | {path}
```

`status` is `active` · `paused` · `complete` · `split → [slug-a, slug-b]`. `{path}` is the folder,
relative to `<notes>/`. `{desk}` stays in the format because rows written by the author's older system
carry one; on a fresh install it is `root` and means nothing else.

### Two brief shapes, one resolver

Anything new gets the folder above. But a brief may also exist as a single flat file, because that is
what this system used to make, and the author's own notes still hold seventeen of them. So resolution
tries both, in order:

1. The row has a `{path}` → the brief is `<path>/brief.md`.
2. No `{path}` → `<notes>/state/briefs/<slug>.md`.

Both are readable. **Only the first is ever created.** A half-migrated set of notes must never break
lookup — that is the whole point of carrying two.

## Types of record

`records/<type>/` — a closed set. Six:

| | |
|---|---|
| `context/` | reference material, baselines, "how this thing works" |
| `decisions/` | a choice that was made, and why |
| `insights/` | a pattern noticed; analysis worth keeping |
| `logs/` | a session, a pass, a phase — what was done |
| `proposals/` | something proposed, waiting on a person to rule on it |
| `research/` | what `/research` writes |

Closed means closed: a seventh type is a change to this page, not a judgment call at write time.

> **Why a closed set here, when the topic vocabulary is deliberately open?** They are not the same
> kind of list. A record type is the system's own filing category — the difference between a decision
> and a log is the same for everybody. A *topic* is a subject in someone's life, and those are not the
> same for anybody. That is why one is fixed here and the other one you write yourself
> (`<notes>/memory/topic-vocab.md`), and why no package ships you a copy of somebody else's.

## Canon — two kinds, and they are different

- `<notes>/canon.md` — the top-level file. The handful of things that are true across everything.
  Written only when a person says to. Keep it small; it is read often.
- `<subject>/canon/current.md` and `canon/purpose.md` — per folder. What `/ingest` builds for each
  subject it finds in your material, and what a project settles about itself. `purpose.md` says what
  the folder is *for*; `current.md` holds what it has established.

Every line in either has to survive being read cold, alone, months later, by someone with no memory of
the conversation that produced it. If it needs the backstory, it is a record, not canon.

## The journal

One file, appended to, never edited: `<notes>/system/journal.md`. When it gets long, older months
move to `<notes>/system/journal/YYYY-MM.md` and a reader searches the current file plus whichever
segment covers the dates it wants.

It is the backstop. A brief is overwritten in place all the time and that is safe **only** because the
journal kept what the brief used to say. Anything precious — a dead end, a decision, a number — goes
to the journal before the brief is rewritten over it.

Anything built from the journal carries this, unedited:

> This journal reflects saves via /save and explicitly logged decisions only. In-session pivots,
> verbal agreements, and file changes outside /save are not captured. A clean-looking journal is not a
> complete journal.

## Plans

`<notes>/plans/<name>.md`. Flat — no subfolders, and specifically **no folder per machine**. A plan is
a thing you wrote, so it lives with the rest of what you wrote, not in the repo, and it is not mirrored
anywhere. There is one copy.

## Deliberate differences from the system this came from

Named here because a difference nobody wrote down reads as a mistake later. Each was measured against
the author's live notes on 2026-08-11.

| the older system | here | why |
|---|---|---|
| `records/` types drifted into pairs — `decision/` **and** `decisions/`, `log/` **and** `logs/`, plus `reference/`, `snapshot/`, `briefing`, `summary` | six types, fixed above | the singular/plural fork happened because two documents disagreed and neither was binding. `reference` and `snapshot` fold into `context`; `briefing` folds into `insights`; `summary` folds into `logs`. |
| `records/canon/` held the root desk's canon (38 files) | no such folder | canon is either the one top-level file or a folder's own `canon/`. A third home was a desk-era artifact. |
| `plans/` split into a folder per machine (`Mac`, `Envers-Air`, …, five of them, 359 files) | one flat `plans/` | there is one machine. The two-machine plane is not part of this system. |
| `state/machine-log.md` recorded which machine changed what | gone | same reason. |
| a desk was a heavy thing — `state/`, `views/`, `sources/inbox/`, its own `CLAUDE.md`, a registry entry, a health producer | `desks/<subject>/` here is the light subset only: `canon/current.md`, `canon/purpose.md`, `records/` | `/ingest` builds the subset and nothing more, on purpose. Promotion to the heavy shape is a deliberate human act, later, if a folder earns it — and that machinery is not in this release. |
| the topic vocabulary shipped in the repo | never ships | see the note under Types. It is yours; the tools refuse and teach rather than invent one. |
| four record types existed for one desk each (`clients`, `billing`, `source-ingests`, `source-summaries`) | not here | they describe one person's work, not a general category. |

## Every path, written out

The diagram above is the shape; this is the list, so nothing has to be inferred from indentation.

| path | who writes it | when |
|---|---|---|
| `<notes>/canon.md` | `/save` | only on an explicit go |
| `<notes>/system/journal.md` | `/save`, `bootstrap.py` | every save |
| `<notes>/system/journal/YYYY-MM.md` | whatever rotates it | when the journal gets long |
| `<notes>/system/project-registry.md` | `project-manager`, `bootstrap.py` | a project starts |
| `<notes>/system/learnings.md` | `/save` | when the system learns something about itself |
| `<notes>/state/projects/<slug>/brief.md` | `project-manager`, `/checkin`, `/save` | continuously, in place |
| `<notes>/state/projects/<slug>/records/` | `/save` | a finding belongs to one project |
| `<notes>/state/projects/<slug>/canon/current.md` | `/save` | a project settles something |
| `<notes>/state/briefs/<slug>.md` | nothing — **read only** | older notes only |
| `<notes>/state/open-loops.md` | `/save` | something is started and not finished |
| `<notes>/state/debt-ledger.md` | `/save`, `/build` | something is knowingly left imperfect |
| `<notes>/state/current.md` | `/save` | where things stand changes |
| `<notes>/records/<type>/` | `/save` | a finding belongs to no one project |
| `<notes>/records/research/` | `/research` | every run |
| `<notes>/plans/<name>.md` | `/autoplan` | a plan is written or sharpened |
| `<notes>/config/` | a person, by hand | account IDs and the like, kept out of the repo |
| `<notes>/councils/` | a person, by hand | if advisor rosters are used |
| `<notes>/memory/topic-vocab.md` | a person, by hand | your subjects, in your words |
| `<notes>/desks/<subject>/canon/` | `/ingest` | once per subject it finds |
| `<notes>/desks/<subject>/records/` | `/ingest` | a stub file per finding it places |
| `<notes>/desks/<subject>/records/proposals/` | `/ingest` | a canon candidate, awaiting your ruling |

## When you add something that writes

1. The path comes from `shared/brain_root.py`. There is no second way to find the notes folder.
2. If your path is not on this page, add it here first — in the same change, not afterwards.
3. Never create a folder to be helpful. Everything above is created when something is actually put in
   it, except the three day-one files, which exist because nothing else would ever make them.
