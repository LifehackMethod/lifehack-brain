#!/usr/bin/env python3
"""
registry.py — resolve a project slug to the files that belong to it.

Every skill that touches a project asks the same question — *where does `<slug>` live?* — and the
answer has two shapes, because a project is a folder now and used to be a single flat file. Four
skills were each about to carry their own prose copy of that rule. This is the one copy.

    from registry import resolve
    p = resolve("widget")          # or resolve("widget", root="/path/to/notes")
    p.brief                        # .../state/projects/widget/brief.md
    p.records                      # .../state/projects/widget/records
    p.canon                        # .../state/projects/widget/canon/current.md
    p.layout                       # "folder" | "flat" | None

## The row format

One line per project in `<notes>/system/project-registry.md`, five pipe-separated fields:

    {desk} | {slug} | {display name} | {status} | {path}

`status` is `active` · `paused` · `complete` · `split → [a, b]`. `path` is the project's FOLDER,
relative to the notes root. `desk` is `root` unless someone uses subject desks. A four-field row —
no path — is still valid and still parses; that is what an un-migrated project looks like.

## The two shapes, and why both are read

1. **The row has a path** → the folder shape. The brief is `<path>/brief.md`, and the project's own
   records and canon sit beside it.
2. **No path** → the flat shape. The brief is `state/briefs/<slug>.md`, and there is nowhere for the
   project's own records, so they go to the shared `records/` tree.

**Both are read. Only the folder shape is ever created.** That is the safety invariant: a set of
notes that is half-migrated must never break lookup. `create_row()` below writes the five-field form
and nothing else.

⛔ It does not guess. An unknown slug returns a `Project` with `layout=None` and the paths it WOULD
have used, so a caller can say "no such project, did you mean to start one?" rather than inventing a
folder. `resolve()` never creates anything.
"""

import os
import re
import sys

REGISTRY_REL = os.path.join("system", "project-registry.md")
_HERE = os.path.dirname(os.path.abspath(__file__))

STATUSES = ("active", "paused", "complete")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class Project(object):
    """Where one project's files are. Paths are absolute and may not exist yet."""

    def __init__(self, slug, root, path=None, desk="root", display=None, status=None):
        self.slug = slug
        self.root = root
        self.desk = desk
        self.display = display or slug
        self.status = status
        self.path = path                      # folder, relative to root; None = flat shape

    @property
    def layout(self):
        if self.status is None and self.path is None:
            return None                       # not in the registry at all
        return "folder" if self.path else "flat"

    @property
    def folder(self):
        """The project's folder. For a flat project there isn't one — returns None."""
        return os.path.join(self.root, self.path) if self.path else None

    @property
    def brief(self):
        if self.path:
            return os.path.join(self.root, self.path, "brief.md")
        return os.path.join(self.root, "state", "briefs", self.slug + ".md")

    @property
    def records(self):
        """Where this project's own findings go. A flat project has no folder of its own, so its
        records land in the shared tree — visibility is the point, and there is nowhere else."""
        if self.path:
            return os.path.join(self.root, self.path, "records")
        return os.path.join(self.root, "records")

    @property
    def canon(self):
        """A folder's canon is a DIRECTORY holding current.md — the same shape /ingest builds for a
        subject, so a person learns one shape rather than two."""
        if self.path:
            return os.path.join(self.root, self.path, "canon", "current.md")
        return os.path.join(self.root, "canon.md")

    @property
    def leaf_matches_slug(self):
        """The folder's last segment must equal the slug, or the project cannot be found by its own
        name. A flat project has no folder, so the question does not arise."""
        if not self.path:
            return True
        return os.path.basename(self.path.rstrip("/")) == self.slug

    def __repr__(self):
        return "Project(%r, layout=%r, brief=%r)" % (self.slug, self.layout, self.brief)


def notes_root(explicit=None):
    """The person's notes folder, via the one resolver. Returns None when it is not set — never a
    guess, and never the current directory."""
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))
    sys.path.insert(0, _HERE)
    try:
        import brain_root
    except ImportError:
        return None
    return brain_root.resolve_brain_root()[1]


def parse_row(line):
    """A registry row → dict, or None if the line is not a row.

    ⚠ The slug must START with a letter or digit, not merely be built from the slug alphabet. `-` is
    in that alphabet, so a markdown table separator (`|---|---|---|---|---|`) otherwise parses as a
    project whose slug and folder are both '---' — it matches itself, raises no alarm, and inflates
    every count taken over the registry."""
    if line.count("|") < 3:
        return None
    f = [x.strip() for x in line.split("|")]
    if len(f) < 4 or not SLUG_RE.match(f[1]):
        return None
    return {"desk": f[0] or "root", "slug": f[1], "display": f[2], "status": f[3],
            "path": (f[4] if len(f) > 4 and f[4] else None)}


def rows(root=None, registry=None):
    """Every parseable row, in file order. Missing or unreadable registry → an empty list, because
    'no projects yet' and 'I could not read the registry' are both answered the same way by every
    caller here: there is nothing to resolve."""
    path = registry or (os.path.join(root, REGISTRY_REL) if root else None)
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except Exception:
        return []
    return [r for r in (parse_row(l) for l in text.splitlines()) if r]


def resolve(slug, root=None, registry=None):
    """slug → Project. Never creates anything, never guesses a folder.

    An unknown slug still returns a Project — with `layout` None and the paths the FLAT shape would
    have used — so a caller can say "there is no project called that" and show where it looked,
    instead of silently inventing a home."""
    root = notes_root(root)
    if root is None:
        raise RuntimeError("no notes folder is set — resolve it first, never guess one")
    for r in rows(root, registry):
        if r["slug"] == slug:
            return Project(slug, root, path=r["path"], desk=r["desk"],
                           display=r["display"], status=r["status"])
    return Project(slug, root)


def find_brief(slug, root=None, registry=None):
    """The brief that actually EXISTS on disk, trying both shapes in order, or None.

    This is the dual-resolution rule itself: the registry's answer first, the flat shape second. A
    half-migrated set of notes never breaks lookup."""
    p = resolve(slug, root, registry)
    if p.path and os.path.isfile(p.brief):
        return p.brief
    flat = os.path.join(p.root, "state", "briefs", slug + ".md")
    if os.path.isfile(flat):
        return flat
    return None


def format_row(slug, display, path, desk="root", status="active"):
    """The five-field row, in the one format. Refuses a folder whose leaf is not the slug — a
    project nobody can find by its own name is a project they have lost."""
    if not SLUG_RE.match(slug):
        raise ValueError("slug %r must be lowercase letters, digits and hyphens, "
                         "starting with a letter or digit" % slug)
    if path and os.path.basename(path.rstrip("/")) != slug:
        raise ValueError("the folder's last segment must equal the slug: %r ends in %r"
                         % (path, os.path.basename(path.rstrip("/"))))
    return "%s | %s | %s | %s | %s" % (desk, slug, display, status, path)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: registry.py <slug> [--root <notes folder>]\n"
              "       registry.py --list [--root <notes folder>]", file=sys.stderr)
        return 2
    root = None
    if "--root" in argv:
        i = argv.index("--root")
        root = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    try:
        if argv and argv[0] == "--list":
            for r in rows(notes_root(root)):
                print("%(slug)s  %(status)s  %(path)s" % r)
            return 0
        p = resolve(argv[0], root)
    except RuntimeError as e:
        print("REFUSED: %s" % e, file=sys.stderr)
        return 1
    if p.layout is None:
        print("NOT-REGISTERED %s" % p.slug)
        print("  no row in %s" % os.path.join(p.root, REGISTRY_REL))
        return 3
    print("%s  layout=%s" % (p.slug, p.layout))
    for label in ("brief", "records", "canon"):
        target = getattr(p, label)
        print("  %-8s %s%s" % (label, target, "" if os.path.exists(target) else "   (not created yet)"))
    if not p.leaf_matches_slug:
        print("  ⚠ the folder's last segment is not the slug — this project cannot be found by name")
    return 0


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    sys.exit(main())
