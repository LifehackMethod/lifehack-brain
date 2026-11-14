# History log for data-layout.md

Text cut or moved out of the SOP, copied verbatim first. Append-only.

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 001

~~~~
# Where things go inside your AI Brain
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 002

~~~~
> The map of what goes INSIDE your AI Brain. Every tool in this repo that writes something DURABLE
> writes it at one of the paths on this page, and gets the AI Brain itself from one place:
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 003

~~~~
## Where the AI Brain itself lives
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 004

~~~~
**Where your AI Brain lives and how it gets set up is covered in `INSTALL.md`, which is the
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 005

~~~~
Everywhere below, `<notes>/` is the path placeholder for your AI Brain — whatever
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 006

~~~~
<notes>/
├── canon.md                        the few things that stay true. small on purpose.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 007

~~~~
├── state/
│   ├── projects/<slug>/            one folder per project — see "A project" below
│   ├── briefs/<slug>.md            older flat briefs. read, never written. see "Two brief shapes".
│   ├── open-loops.md               started, not finished
│   ├── debt-ledger.md              known-imperfect, deliberately deferred
│   └── current.md                  where things stand right now
├── records/<type>/                  everything found, decided or written down — see "Types" below
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 008

~~~~
└── desks/<subject>/                 one folder per subject, built by `/ingest` from your material
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 009

~~~~
`system/project-registry.md`, the projects folder, and `canon.md` — the last of these shipped **empty
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 010

~~~~
A project is a **folder**, and the folder's name is the project's slug:
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 011

~~~~
<notes>/state/projects/<slug>/
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 012

~~~~
└── canon/current.md  what this project has settled
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 013

~~~~
(`state/projects/infrastructure/<slug>/`); the leaf is not. This stops the drift where a project
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 014

~~~~
Its row in `<notes>/system/project-registry.md` is five fields, pipe-separated:
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 015

~~~~
relative to `<notes>/`. `{desk}` stays in the format because rows written by the author's older system
carry one; on a fresh install it is `root` and means nothing else.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 016

~~~~
### Two brief shapes, one resolver
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 017

~~~~
Anything new gets the folder above. But a brief may also exist as a single flat file, because that is
what this system used to make, and the author's own notes still hold seventeen of them. So resolution
tries both, in order:

1. The row has a `{path}` → the brief is `<path>/brief.md`.
2. No `{path}` → `<notes>/state/briefs/<slug>.md`.

Both are readable. **Only the first is ever created.** A half-migrated set of notes must never break
lookup — that is the whole point of carrying two.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 018

~~~~
> (`<notes>/memory/topic-vocab.md`), and why no package ships you a copy of somebody else's.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 019

~~~~
- `<notes>/canon.md` — the top-level file. The handful of things that are true across everything.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 020

~~~~
One file, appended to, never edited: `<notes>/system/journal.md`. When it gets long, older months
move to `<notes>/system/journal/YYYY-MM.md`.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 021

~~~~
`<notes>/plans/<name>.md`. Flat — no subfolders, and specifically **no folder per machine**. A plan is
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 022

~~~~
| `records/canon/` held the root desk's canon (38 files) | no such folder | canon is either the one top-level file or a folder's own `canon/`. A third home was a desk-era artifact. |
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 023

~~~~
| a desk was a heavy thing — `state/`, `views/`, `sources/inbox/`, its own `CLAUDE.md`, a registry entry, a health producer | `desks/<subject>/` here is the light subset only: `canon/current.md`, `canon/purpose.md`, `records/` | `/ingest` builds the subset and nothing more, on purpose. Promotion to the heavy shape is a deliberate human act, later, if a folder earns it — and that machinery is not in this release. |
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 024

~~~~
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
| `<notes>/records/insights/throughline/` | `/throughline` | once per run — and it is the ONLY thing that run may write |
| `<notes>/plans/<name>.md` | `/autoplan` | a plan is written or sharpened |
| `<notes>/config/` | a person, by hand | account IDs and the like, kept out of the repo |
| `<notes>/config/numbers-auto-arm` | a person, by hand | optional — subject folders that turn on `/calculate` by themselves |
| `<notes>/config/ship-identity.md` | the maintainer, by hand | ⛔ **MAINTAINER-ONLY — you do not need this.** The shipping lane exists to keep the maintainer's own private terms out of the public copy of this repo. Nobody else, contributor or not, ever needs to create this file |
| `<notes>/config/ship-rewrites.json` | a person, by hand | optional — `/ship`'s cosmetic substitutions, which get fixed and reported rather than blocking |
| `<notes>/councils/` | a person, by hand | if advisor rosters are used |
| `<notes>/memory/topic-vocab.md` | a person, by hand | your subjects, in your words |
| `<notes>/desks/<subject>/canon/` | `/ingest` | once per subject it finds |
| `<notes>/desks/<subject>/records/` | `/ingest` | a stub file per finding it places |
| `<notes>/desks/<subject>/records/proposals/` | `/ingest` | a canon candidate, awaiting your ruling |
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 025

~~~~
1. The path comes from `shared/brain_root.py`. There is no second way to find the AI Brain.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: data-layout hunk 026

~~~~
   temp folder instead, on purpose: a regenerable working file does not belong in an AI Brain,
~~~~
