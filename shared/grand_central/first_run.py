#!/usr/bin/env python3
"""first_run.py -- Grand Central step 4M.7(a): set up a person's own setup folder from the examples.

One-time, safe to re-run. The plugin ships EXAMPLE settings (shared/grand_central/templates/, `*.example.json`)
as placeholders. This script copies them into the person's OWN code folder, <personal code root>/
tools/grand-central/setup/ (the folder gc_settings.py reads), stripping `.example` from the name, and then
calls the plugin's EXISTING scaffold (shared/tools/personal_jobs_scaffold.py) to create the folders the
person's scheduled jobs need.

Rules it enforces by construction:
  - An existing file is NEVER overwritten: anything already there is skipped and reported, so a person who
    has edited their settings cannot lose an edit by running this again.
  - It prints every created / skipped path.
  - It never runs against a folder that is not the resolved personal code root, unless --root names one
    (which is how the tests run it against tmp folders only).

Usage:
  python3 shared/grand_central/first_run.py [--dry-run] [--root DIR]
    --dry-run  print what would happen, create nothing
    --root DIR run against DIR instead of the resolved personal code root (tests; real runs omit it)

Exit 0 ok (created and/or skipped), 1 when there is no personal code root to work in.
Python 3.9 compatible."""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = os.path.dirname(HERE)

SETUP_SUBDIR = os.path.join("tools", "grand-central", "setup")
TEMPLATE_SUFFIX = ".example"  # <name>.example.json -> <name>.json; .example.txt likewise

# files under templates/ copied as-is into the setup folder (names already final)
AS_IS = {"personal-values-allow.example.txt": "personal-values-allow.txt"}


def templates_dir():
    return os.path.join(HERE, "templates")


def _strip_example(fname):
    """<name>.example.<ext> -> <name>.<ext>, via the AS-IS table or the suffix rule; None = not a template."""
    if fname in AS_IS:
        return AS_IS[fname]
    base, ext = os.path.splitext(fname)
    if ext == ".json" and base.endswith(TEMPLATE_SUFFIX):
        return base[: -len(TEMPLATE_SUFFIX)] + ext
    return None


def plan(root, tdir=None):
    """-> (tdir, setup_dir, [(src, dst), ...]) for one run; dst paths under the person's setup folder.
    Raises RuntimeError when there is no personal code root and no --root."""
    tdir = tdir or templates_dir()
    setup = os.path.join(root, SETUP_SUBDIR)
    pairs = []
    for fname in sorted(os.listdir(tdir)):
        target = _strip_example(fname)
        if target:
            pairs.append((os.path.join(tdir, fname), os.path.join(setup, target)))
    return tdir, setup, pairs


def run(root=None, dry_run=False):
    """Do one first-run against root (default: person_roots' personal code root).
    Prints created/skipped lines. -> exit code."""
    if root is None:
        if SHARED not in sys.path:
            sys.path.insert(0, SHARED)
        try:
            import person_roots
            root = person_roots.personal_code_root()
        except ImportError:
            root = ""
        if not root:
            print("NO-ROOT: no personal code folder resolved. Fix: python3 system/tools/bootstrap.py", file=sys.stderr)
            return 1

    tdir, setup, pairs = plan(root)

    created, skipped = [], []
    for src, dst in pairs:
        if os.path.lexists(dst):
            skipped.append(dst)
            continue
        if dry_run:
            print("would create: %s" % dst)
            created.append(dst)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)  # copy contents only; destination is new by construction
        print("created: %s" % dst)
        created.append(dst)

    # the migrations folder ships only a README (an empty series is valid); make sure it exists
    mig = os.path.join(setup, "migrations")
    if not os.path.lexists(mig):
        if dry_run:
            print("would create: %s" % mig)
        else:
            os.makedirs(mig)
            print("created: %s" % mig)
    elif not dry_run:
        print("skipped (already there): %s" % mig)

    # the folders the person's jobs need: the plugin's OWN scaffold, called, never copied
    if dry_run:
        print("would run scaffold: shared/tools/personal_jobs_scaffold.py %s" % root)
    else:
        tools_dir = os.path.join(SHARED, "tools")
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        import personal_jobs_scaffold
        c2, s2 = personal_jobs_scaffold.scaffold(root)
        for rel in c2:
            print("created (scaffold): %s" % os.path.join(root, rel))
        for rel in s2:
            print("skipped (scaffold, already there): %s" % os.path.join(root, rel))

    print("done%s: %d created, %d skipped" % (" (dry-run)" if dry_run else "", len(created), len(skipped)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Set up a person's Grand Central setup folder from the shipped examples.")
    ap.add_argument("--dry-run", action="store_true", help="print what would happen; create nothing")
    ap.add_argument("--root", help="run against DIR instead of the resolved personal code root (tests)")
    args = ap.parse_args(argv)
    return run(root=args.root, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
