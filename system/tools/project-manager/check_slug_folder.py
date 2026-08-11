#!/usr/bin/env python3
"""
check_slug_folder.py — list projects whose FOLDER name is not their SLUG.

THE RULE: a project's folder — the last path segment of its registry `{path}` field — must equal
its slug. A category above it is fine (`state/projects/infrastructure/<slug>/`); only the leaf has
to match. A project a person can't find by its own name is a project they've lost, and the drift is
invisible until the day they go looking.

This lists violations. It never edits anything. Fixing one is a deliberate migration — rename the
folder, repoint the registry row and anything pointing at the old path — and that is a decision, not
a job for a detector.

Usage:
    check_slug_folder.py                       # the registry in your notes folder
    check_slug_folder.py <path/to/project-registry.md>

Exit 0 always, even with mismatches: a mismatch is a RESULT, not a failure of this tool. Exit 1 only
when there is nothing to check — no registry, or no notes folder chosen yet.
"""
import os
import re
import sys

_REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

# A row whose status or path says the project is over, or was split into others. Its folder is
# allowed to disagree with its slug — the project no longer exists to be found.
SKIP = ("dissolved", "merged", "superseded", "split", "complete", "→")


def default_registry():
    """The registry under the person's notes folder, via the one resolver. Never a guess."""
    sys.path.insert(0, os.path.join(_REPO, "shared"))
    try:
        import brain_root
    except ImportError as e:
        return None, "cannot import shared/brain_root.py (%s)" % e
    _source, root = brain_root.resolve_brain_root()
    if root is None:
        return None, ("no notes folder has been chosen yet. Set it with:\n"
                      "    python3 %s --set \"<that folder>\""
                      % os.path.join(_REPO, "shared", "brain_root.py"))
    return os.path.join(root, "system", "project-registry.md"), None


def check(lines):
    """(checked, mismatches) — mismatches are (slug, leaf, path, desk). Pure; no I/O."""
    mismatches, checked = [], 0
    for ln in lines:
        if ln.count("|") < 4:                       # need 5 fields: desk|slug|name|status|path
            continue
        parts = [p.strip() for p in ln.split("|")]
        desk, slug, _name, status, path = parts[0], parts[1], parts[2], parts[3], parts[4]
        if not path or any(s in status.lower() or s in path for s in SKIP):
            continue
        # ⚠ Must START with a letter or digit, not merely consist of the slug alphabet. `-` is in
        # that alphabet, so a markdown table separator row (`|---|---|---|---|---|`) parsed as a
        # project whose slug and folder were both "---" — it matched itself, raised no alarm, and
        # silently added one to the count of projects checked. A detector whose denominator is
        # inflated is reporting on a set that does not exist.
        if not re.match(r"^[a-z0-9][a-z0-9-]*$", slug):   # header rows, table decoration, garbage
            continue
        checked += 1
        segs = path.rstrip("/").split("/")
        if segs and segs[-1] == "brief.md":         # some rows give <folder>/brief.md, not the folder
            segs = segs[:-1]
        leaf = segs[-1] if segs else ""
        if leaf != slug:
            mismatches.append((slug, leaf, path, desk))
    return checked, mismatches


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        reg, err = argv[0], None
    else:
        reg, err = default_registry()
    if err:
        print("REFUSED: %s" % err)
        return 1
    try:
        with open(reg, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except Exception as e:                          # a cloud-synced folder can throw more than OSError
        print("cannot read the registry at %s: %s" % (reg, e))
        return 1

    checked, mismatches = check(lines)
    print("slug ↔ folder — %d project(s) with a path; %d mismatch(es)\n" % (checked, len(mismatches)))
    if mismatches:
        for slug, leaf, path, desk in mismatches:
            print("  ⚠ slug '%s'  ≠  folder '%s'   (%s · %s)" % (slug, leaf, desk, path))
        print("\n  Fixing one is a deliberate migration: rename the folder to match the slug, then "
              "repoint the registry row and anything else naming the old path.")
    else:
        print("  ✓ every project's folder matches its slug.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
