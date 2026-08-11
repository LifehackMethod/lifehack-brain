#!/usr/bin/env python3
"""bootstrap.py — day one. Makes the four things nothing else makes, and nothing more.

Run once, after you have told the system where your notes live:

    python3 system/tools/bootstrap.py            # uses the folder you already chose
    python3 system/tools/bootstrap.py --root <path>
    python3 system/tools/bootstrap.py --dry-run  # say what it would do, touch nothing

⭐ WHY THIS EXISTS — measured, not assumed (2026-08-11).
/ingest builds every subject folder correctly: a canon file for what stays true, a records folder for
what happened on a date, a stated purpose. What it builds NOTHING of is the layer ABOVE those folders.
Its own phase file says so outright — "there is no registry step at this level" — and a grep across
the whole shipped skill finds zero code that creates a journal, a project registry, or a projects
folder. So a new person's day one is a set of subject folders sitting in an otherwise empty room.

It self-heals in use: /save writes a journal line and creates the journal if it is missing, and the
project tools create a brief when you start one. But nothing puts the shape there FIRST, so the first
session of a new install works against a directory that does not look like the system it is part of.

⭐ THE FOURTH THING — the root canon (added 2026-08-11, task 2.1.1). `docs/data-layout.md` and
`shared/registry.py`'s `Project.canon` property already agree on where it lives — `<notes>/canon.md`,
the plain top-level file, sibling of `desks/<subject>/canon/current.md` but not shaped like it (no
folder, no separate `purpose.md` — one file, one intent line). Nothing before this created it, so
`/read` Step 3.9's `$DATA/canon.md` line and `canon_conflict_scan.py`'s single-file mode had a path
with nothing at it. This ships the file EMPTY of canon lines, carrying only its own purpose — the
altitude bar for what belongs here — so PHASE 4.5 has a floor to write onto instead of open air.

⛔ AND NOTHING ELSE. It is very tempting to have this scaffold "a sensible starting structure" — some
subject folders, an example note, a template. Do not. Which subjects a person's life divides into is
theirs to discover, and handing them a guess teaches them that the guess is the answer. The same
reasoning that keeps a topic vocabulary out of this repo keeps starter folders out of this script.
The root canon is no exception: its FRAME ships (purpose + heading), its CONTENT does not — that is
earned, one line at a time, by a later human-confirmed act, never guessed here.

Never clobbers. Run it as often as you like; anything already there is left exactly as it is.
"""

import argparse
import os
import sys

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "shared"))

JOURNAL = "system/journal.md"
REGISTRY = "system/project-registry.md"
# The project folder. A project is a FOLDER named exactly its slug, holding brief.md +
# records/ + canon/ (docs/data-layout.md). The older flat shape, state/briefs/<slug>.md,
# stays READABLE forever but is never created — an empty folder nothing writes to teaches
# a shape that does not exist, which is the exact thing this file refuses to do elsewhere.
BRIEFS = "state/projects"
# The root canon — NOT under system/ or state/. `docs/data-layout.md`'s shape diagram and
# `shared/registry.py`'s `Project.canon` (`os.path.join(self.root, "canon.md")` for the rootless
# case) already agree: it sits directly at the notes root, beside `system/`, `state/`, `desks/` —
# the one file every one of those folders' canon defers up to. Picking a new path here would
# contradict two files that already point at this one; this just makes the pointer real.
ROOT_CANON = "canon.md"

# Deliberately thin. A one-line title so a human opening the file knows what it is, and NOT a schema —
# the row format belongs to the tools that write these, not to the thing that creates them empty.
JOURNAL_BODY = """# Journal

Appended to as you work — what happened, when, and why. Nothing here is written by hand; the tools
add to it. It is the backstop: if something was not filed anywhere else, it is in here.
"""

REGISTRY_BODY = """# Projects

One row per project, added when a project starts. This is what lets a cold session six weeks from now
find a project you have half-forgotten, by name, without searching the whole folder.
"""

# The admission bar, not a done-when — this is what a later phase (PHASE 4.5) reads before it writes
# a line here, and what a cold session reads before it reads anything else. ⛔ NO line count, NO size
# threshold, anywhere in this text — the bound the system enforces is ALTITUDE (does this fact hold
# for every conversation, on any subject?), never a number of lines. That was weighed and rejected:
# `knowledge-altitude.md` §7 bars "NO numeric scoring, NO thresholds" for exactly this kind of file.
ROOT_CANON_BODY = """# Canon

**intent:** only what must be true for EVERY conversation, on ANY subject — your name, how you want
to be spoken to, how this system itself should operate. A cold session loads this file before it
loads anything else, so a line placed here is carried into every conversation that follows, forever.
**not:** something true only within one subject — that belongs one level down, in that subject's own
`canon/current.md`, not here.

Nothing below this line is written by hand at creation. It is earned later, one confirmed line at a
time, off real conversations — never guessed, never pre-filled.

"""


def resolve_root(explicit=None):
    """(path, source) or (None, reason). Uses the one resolver — never guesses, never uses the cwd."""
    if explicit:
        p = os.path.abspath(os.path.expanduser(explicit))
        return (p, "--root") if os.path.isdir(p) else (None, "'%s' is not a directory" % p)
    try:
        import brain_root
    except ImportError as e:
        return None, "cannot import shared/brain_root.py (%s)" % e
    source, path = brain_root.resolve_brain_root()
    if path is None:
        return None, ("no data root set. Tell the system where your notes live first:\n"
                      "    python3 %s --set \"<that folder>\" [--create]"
                      % os.path.join(REPO, "shared", "brain_root.py"))
    return path, source


def bootstrap(root, dry_run=False):
    """Returns (created, existed) as lists of repo-relative paths. Creates nothing else, ever."""
    created, existed = [], []

    briefs = os.path.join(root, BRIEFS)
    if os.path.isdir(briefs):
        existed.append(BRIEFS + "/")
    else:
        created.append(BRIEFS + "/")
        if not dry_run:
            os.makedirs(briefs)

    for rel, body in ((JOURNAL, JOURNAL_BODY), (REGISTRY, REGISTRY_BODY), (ROOT_CANON, ROOT_CANON_BODY)):
        target = os.path.join(root, rel)
        if os.path.exists(target):
            existed.append(rel)
            continue
        created.append(rel)
        if not dry_run:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(body)
    return created, existed


def main(argv=None):
    ap = argparse.ArgumentParser(description="create the four top-level things nothing else creates")
    ap.add_argument("--root", help="the folder your notes live in (default: the one already chosen)")
    ap.add_argument("--dry-run", action="store_true", help="say what would happen; touch nothing")
    a = ap.parse_args(argv)

    root, source = resolve_root(a.root)
    if root is None:
        print("REFUSED: %s" % source)
        return 1

    created, existed = bootstrap(root, dry_run=a.dry_run)
    print("Your notes: %s  (from: %s)" % (root, source))
    verb = "would create" if a.dry_run else "created"
    if created:
        for p in created:
            print("  %s %s" % (verb, p))
    for p in existed:
        print("  already there, left alone: %s" % p)
    if not created:
        print("Nothing to do — the shape is already in place.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
