# Where things go inside your brain folder

> The map of what goes INSIDE your brain folder: the driver's logbook (knowledge layer: the brain
> folder, `shared/brain_root.py`). Every tool in this repo that writes something DURABLE
> writes it at one of the paths on this page, and gets the brain folder itself from one place:
> `shared/brain_root.py`. (Throwaway scratch is the stated exception — see the last section.)
> If you are adding a tool and the path you want is not here, the path is wrong or this page is
> incomplete — resolve that before writing code.

## Where the brain folder itself lives

**Where your brain folder lives and how it gets set up is covered in `INSTALL.md`, which is the
authority.** This page does not repeat it. This page is only the shape of what goes inside.

The brain folder is a local folder first; Google Drive backs it up. Beside the three folders (the
Lifehack Harness, personal code, and the brain folder) sits a fourth, local folder that is NOT
synced (for example `~/.local/share/<system>/`): live databases and other files that programs
rewrite constantly live there, because syncing a live database can corrupt it, and so does
sensitive raw content, like full email text. Finished backup copies may be placed in the brain
folder. There is no standing "no database" rule: files are the default for notes, diary, canon and
tiles, and a database is the right tool where many things must be connected and several jobs write.

Everywhere below, `<brain>/` is the path placeholder for your brain folder — whatever
`shared/brain_root.py` resolves, and not the current directory, not the repo, not a guess. When it
is not set, the honest answer is "not set" and the tool refuses.

## The shape

```
<brain>/                            the root has a desk's shape, plus a few root-only folders
├── canon/
│   ├── canon.md                    the few things that stay true. small on purpose.
│   └── purpose.md                  what this folder is for
├── records/<type>/                  everything found, decided or written down — see "Types" below
├── diary/YYYY/MM/DD.md              the dated tree: one entry per day. where things stand is read here.
├── open-loops.md                    started, not finished
├── debt-ledger.md                   root only. all known system technical debt: the deferred build list
├── projects/<slug>/                 one folder per project not started from a desk — see "A project" below
├── status/<producer>.json           root only. status tiles, one per producer
├── system/
│   ├── journal.md                  append-only. what happened, when, why.
│   ├── journal/YYYY-MM.md          older months, rotated out of the above
│   ├── project-registry.md         one row per project — the thing that makes a project findable
│   └── learnings.md                what the system learned about running itself
├── plans/<name>.md                  plans are yours, not the tool's
├── config/                          settings that are specific to you (IDs, accounts, rate cards)
├── councils/                        rosters of advisors, if you use them
├── memory/
│   └── topic-vocab.md               your subjects, in your words — written by you, never shipped
└── desks/<subject>/                 root only. one folder per subject, built by `/ingest` from your material
    ├── canon/current.md
    ├── canon/purpose.md
    └── records/
```

> **A note on the word `desks`.** That is the folder name `/ingest` writes, and it is kept because the
> code writes it. In anything you *say* to a person it is "a folder per subject" — `/ingest`'s own
> voice rules ban the jargon out loud while the path keeps it. Don't rename the folder to fix the
> vocabulary; the fix is in how you talk, and it is already made.

Four of those exist on day one and nothing else does: `system/journal.md`,
`system/project-registry.md`, the projects folder, and `canon/canon.md` — the last of these shipped **empty
of canon lines, carrying only its own purpose**, so a later step has a floor to write onto instead of
open air. `system/tools/bootstrap.py` makes exactly those and refuses to make more, for the reason
written at the top of that file: which subjects your life divides into is yours to discover, and a
starter folder is a guess that teaches itself as the answer.

## A project

A project is a **folder**, and the folder's name is the project's slug. A project started from inside a
desk keeps its folder, brief included, in that desk; any other project lives in the root `projects/`.
The shape is the same at both levels:

```
<brain>/projects/<slug>/
├── brief.md          the living document. one per project, for its whole life, updated in place.
├── records/          this project's own findings — kept here, where the project can see them
└── canon/canon.md    what this project has settled
```

**Three more files appear beside the brief, written by the tool and never by hand.** They are named
here because otherwise the first person to see one has to guess whether something went wrong:

| beside the brief | what it is |
|---|---|
| `<slug>/brief.md.pad-archive.md` | the append-only archive of every scratchpad, written before any pad is cleared. Nothing is ever deleted from it. It is the reason a compaction is safe: the clear will not run without a fresh receipt proving this file already holds the text. |
| `<slug>/brief.md.<section>-archive.md` | the same, for a named section — `## 2. CURRENT STATE` graduating at a check-in produces `brief.md.2-current-state-...-archive.md`. |
| `<slug>/brief.md.pre-section-archive-<date>.bak` | a whole-file backup taken before a *named-section* archive only, because the caller then deletes by hand. The pad's own clear is code-owned and hash-gated, so it needs no backup and takes none. |

You may delete an old `.bak`. Do not hand-edit the two archives, and never hand-clear a section that
has one: `pad_archive.py` matches a hash to prove what it is deleting, and an edit by hand breaks
that match — which is a refusal, not a loss, but it costs you the session's compaction.

**The folder's last path segment must equal the slug.** A category above it is fine
(`projects/infrastructure/<slug>/`); the leaf is not. This stops the drift where a project
called one thing lives in a folder called another and a cold session finds neither.
`system/tools/project-manager/check_slug_folder.py` audits it after the fact, and
`shared/registry.py`'s `format_row()` refuses to write such a row in the first place.

Its row in `<brain>/system/project-registry.md` is five fields, pipe-separated:

```
{desk} | {slug} | {display name} | {status} | {path}
```

`status` is `active` · `paused` · `complete` · `split → [slug-a, slug-b]`. `{path}` is the folder,
relative to `<brain>/`. `{desk}` is the desk the project was started from, or `root` for a project in
the root `projects/`.

### Where a brief lives

A brief lives in its project's folder, and nowhere else: the row's `{path}` → the brief is
`<path>/brief.md`. There is no separate `briefs/` folder.

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
> (`<brain>/memory/topic-vocab.md`), and why no package ships you a copy of somebody else's.

## Canon — two kinds, and they are different

- `<brain>/canon/canon.md` — the top-level file. The handful of things that are true across everything.
  Written only when a person says to. Keep it small; it is read often.
- `<subject>/canon/current.md` and `canon/purpose.md` — per folder. What `/ingest` builds for each
  subject it finds in your material, and what a project settles about itself. `purpose.md` says what
  the folder is *for*; `current.md` holds what it has established.

Every line in either has to survive being read cold, alone, months later, by someone with no memory of
the conversation that produced it. If it needs the backstory, it is a record, not canon.

## The journal

One file, appended to, never edited: `<brain>/system/journal.md`. When it gets long, older months
move to `<brain>/system/journal/YYYY-MM.md`.

**Anything reading the journal reads the current file AND the segments.** Reading only the current
file loses everything older than the last rotation, and it fails *quietly*: the result comes back
short and looks like a quiet stretch rather than a truncated search.

```bash
python3 system/tools/journal.py slice --slug "<slug>"     # segments + current, oldest first
python3 system/tools/journal.py rotate --dry-run          # what a rotation would move
```

`rotate` moves every entry from a **completed** month into its segment and leaves the current month
where it is — rotating a half-finished month would split it across two files and make every reader
join it back together. It reads each segment back before removing a line from the current file.

**Two entry shapes, and no others.**

A **ledger row** — one line, for every artifact saved:

```
{YYYY-MM-DD} | {desk} | {slug} | {event} | supersedes: {path or —} | → {artifact-path}
```

- `event` is what changed **and why**, readable with no other context. Not a filename echo. Bad:
  *"Updated state."* Good: *"Moved the venue to second choice after the quote came back double; the
  budget line changes."*
- `supersedes` is a path or `—`. **Never a concept.** `[partial: …]` when only part of the old file
  is invalidated; `[renamed]` when a file moved rather than being superseded; two comma-separated
  paths when two files became one.
- `slug` must exist in the registry before it is used.

A **session entry** — a block, written when the story matters more than the row: something failed and
shaped the outcome, an architectural decision was made, or the session pivoted.

```markdown
## SESSION — {YYYY-MM-DD} | {slug}

**Session:** {what was worked on — one sentence}
**Follows:** {what this picked up from — the cause-and-effect link, or "—" if it starts something}
**Failed / changed:** {what did not work, what pivoted, and why}
**Key findings:** {the two to four conclusions that matter}
**End state:** {where it stands — what is open, what is done}
**Missteps:** {anything that cost time or should not be repeated}
```

It is the backstop. A brief is overwritten in place all the time and that is safe **only** because the
journal kept what the brief used to say. Anything precious — a dead end, a decision, a number — goes
to the journal before the brief is rewritten over it.

Anything built from the journal carries this, unedited:

> This journal reflects saves via /save and explicitly logged decisions only. In-session pivots,
> verbal agreements, and file changes outside /save are not captured. A clean-looking journal is not a
> complete journal.

## Plans

`<brain>/plans/<name>.md`. Flat — no subfolders, and specifically **no folder per machine**. A plan is
a thing you wrote, so it lives with the rest of what you wrote, not in the repo, and it is not mirrored
anywhere. There is one copy.

## Deliberate differences from the system this came from

Named here because a difference nobody wrote down reads as a mistake later. Each was measured against
the author's live notes on 2026-08-11.

| the older system | here | why |
|---|---|---|
| `records/` types drifted into pairs — `decision/` **and** `decisions/`, `log/` **and** `logs/`, plus `reference/`, `snapshot/`, `briefing`, `summary` | six types, fixed above | the singular/plural fork happened because two documents disagreed and neither was binding. `reference` and `snapshot` fold into `context`; `briefing` folds into `insights`; `summary` folds into `logs`. |
| `records/canon/` held the root desk's canon (38 files) | no such folder | canon is either the one top-level file or a folder's own `canon/`. A third canon folder was a desk-era artifact. |
| `plans/` split into a folder per machine (five of them, named after their hosts, 359 files) | one flat `plans/` | there is one machine. The two-machine plane is not part of this system. |
| `<notes>/state/machine-log.md` recorded which machine changed what | gone | same reason. |
| a desk was a heavy thing — `state/`, `views/`, `sources/inbox/`, its own `CLAUDE.md`, a registry entry, a health producer | a desk is a domain of knowledge plus a short card, and nothing that runs; its shape is set by the in-force desk-building SOP (`system/sops/desk-building-sop.md`), not by this page | everything that runs a desk lives once in the car platform (platform layer: the plugin), and a desk's tools live in the car model (personal code layer: personal code). `/ingest` builds `canon/current.md`, `canon/purpose.md` and `records/` for each subject it finds; for the full shape of a desk, read the desk-building SOP. |
| the topic vocabulary shipped in the repo | never ships | see the note under Types. It is yours; the tools refuse and teach rather than invent one. |
| four record types existed for one desk each (`clients`, `billing`, `source-ingests`, `source-summaries`) | not here | they describe one person's work, not a general category. |

## Every path, written out

The diagram above is the shape; this is the list, so nothing has to be inferred from indentation.

| path | who writes it | when |
|---|---|---|
| `<brain>/canon/canon.md` | `/save` | only on an explicit go |
| `<brain>/system/journal.md` | `/save`, `bootstrap.py` | every save |
| `<brain>/system/journal/YYYY-MM.md` | whatever rotates it | when the journal gets long |
| `<brain>/system/project-registry.md` | `project-manager`, `bootstrap.py` | a project starts |
| `<brain>/system/learnings.md` | `/save` | when the system learns something about itself |
| `<brain>/projects/<slug>/brief.md` | `project-manager`, `/checkin`, `/save` | continuously, in place |
| `<brain>/projects/<slug>/records/` | `/save` | a finding belongs to one project |
| `<brain>/projects/<slug>/canon/canon.md` | `/save` | a project settles something |
| a desk's own `projects/<slug>/` (same three paths as above) | `project-manager`, `/checkin`, `/save` | a project is started from inside that desk |
| `<brain>/open-loops.md` | `/save` | something is started and not finished |
| `<brain>/diary/YYYY/MM/DD.md` | the diary cron job, at the end of the day | one entry per day, append-only |
| `<brain>/status/<producer>.json` | each producer, its own tile | overwritten on every run |
| `<brain>/debt-ledger.md` | `/save`, `/build` | a piece of system technical debt becomes known |
| `<brain>/records/<type>/` | `/save` | a finding belongs to no one project |
| `<brain>/records/research/` | `/research` | every run |
| `<brain>/records/insights/throughline/` | `/throughline` | once per run — and it is the ONLY thing that run may write |
| `<brain>/plans/<name>.md` | `/autoplan` | a plan is written or sharpened |
| `<brain>/config/` | a person, by hand | account IDs and the like, kept out of the repo |
| `<brain>/config/numbers-auto-arm` | a person, by hand | optional — subject folders that turn on `/calculate` by themselves |
| `<brain>/config/ship-identity.md` | the maintainer, by hand | ⛔ **MAINTAINER-ONLY — you do not need this.** The shipping lane exists to keep the maintainer's own private terms out of the public copy of this repo. Nobody else, contributor or not, ever needs to create this file |
| `<brain>/config/ship-rewrites.json` | a person, by hand | optional — `/ship`'s cosmetic substitutions, which get fixed and reported rather than blocking |
| `<brain>/councils/` | a person, by hand | if advisor rosters are used |
| `<brain>/memory/topic-vocab.md` | a person, by hand | your subjects, in your words |
| `<brain>/desks/<subject>/canon/` | `/ingest` | once per subject it finds |
| `<brain>/desks/<subject>/records/` | `/ingest` | a stub file per finding it places |
| `<brain>/desks/<subject>/records/proposals/` | `/ingest` | a canon candidate, awaiting your ruling |

## When you add something that writes

1. The path comes from `shared/brain_root.py`. There is no second way to find the brain folder.
   **The one exception is scratch** — `shared/paths.py`'s `scratch_dir()` answers from the machine's
   temp folder instead, on purpose: a regenerable working file does not belong in a brain folder,
   and the hardcoded `/tmp/...` it replaced does not exist on Windows. Durable state still comes from
   the resolver; if what you are writing survives the run, it is not scratch.
2. If your path is not on this page, add it here first — in the same change, not afterwards.
3. Never create a folder to be helpful. Everything above is created when something is actually put in
   it, except the three day-one files, which exist because nothing else would ever make them.
