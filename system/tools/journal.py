#!/usr/bin/env python3
"""
journal.py — append to the journal, read a slice of it, and rotate it when it gets long.

The journal is the append-only backstop. A brief is overwritten in place all the time, and that is
only safe because the journal kept what the brief used to say. So the three operations every skill
performs on it live here rather than as prose in four skill files:

    journal.py append --slug widget --event "..." [--to <artifact>] [--supersedes <path>]
    journal.py slice  --slug widget [--limit 20]
    journal.py rotate [--dry-run]

## Why `append` validates instead of trusting the caller

A ledger row is six pipe-separated fields, and two of them go wrong in the same way every time:

- **`event` must say what changed AND why**, and be readable with no other context. A filename echo
  ("Updated state.") is the failure. It is refused.
- **`supersedes` is a path or `—`. Never a concept.** "the old approach" is not a supersedes value;
  it makes the chain unfollowable, which is the one thing the chain is for.

These are write-time checks that fail loud. A journal line nobody can read six weeks later is
indistinguishable from a line that was never written.

## Why rotation exists, and why a reader must know about it

`journal.md` grows forever otherwise. When it does, `rotate` moves every entry from a *completed*
month into `journal/YYYY-MM.md` and leaves the current month in place.

⛔ **Anything reading the journal must read the segments too.** A reader that opens only `journal.md`
loses everything before the last rotation — and it fails *quietly*: the slice comes back short and
reads as a quiet stretch rather than a truncated search. `slice` below does it correctly; a skill
grepping by hand must include `system/journal/*.md`.

⛔ **Rotation never deletes and never rewrites.** It moves whole lines between files, and it refuses
if the move cannot be read back.
"""

import argparse
import datetime
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
# system/tools/ -> the repo root is TWO levels up, not one. It was one until 2026-08-11, which put
# `shared/` at system/shared -- a directory that does not exist -- so the import below always failed,
# notes_root() always returned None, and every call refused with "no notes folder is set". Silent,
# because the refusal is also the correct answer when nobody has set a root: the tool looked like it
# was working. `test_repo_root_actually_contains_shared_brain_root` fails if this drifts again.
_REPO = os.path.normpath(os.path.join(_HERE, "..", ".."))

JOURNAL_REL = os.path.join("system", "journal.md")
SEGMENT_DIR_REL = os.path.join("system", "journal")

ROW_RE = re.compile(r"^(\d{4})-(\d{2})-\d{2}\s*\|")
DASH = "—"

JOURNAL_HEADER = """# Journal

Appended to as you work — what happened, when, and why. Nothing here is written by hand; the tools
add to it. It is the backstop: if something was not filed anywhere else, it is in here.
"""


def notes_root(explicit=None):
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))
    sys.path.insert(0, os.path.join(_REPO, "shared"))
    try:
        import brain_root
    except ImportError:
        return None
    return brain_root.resolve_brain_root()[1]


# ⛔ FIELD REPORT #77, DEFECT D6 (2026-08-23). `append()` used to write the row with ZERO lookup
# against the project registry, so a typo'd or invented slug landed silently — unfindable later by
# the slug anyone would actually search for. `shared/registry.py` is the one place that already knows
# how to resolve a slug (`resolve()`), so this reuses it rather than re-deriving the same rule a
# second time.
#
# THE DECISION (refuse vs. mark, argued once, here): an unregistered slug REFUSES the write by
# default. `phases/standard-steps.md` Step 0.5 already requires a brand-new project to be registered
# ("add the row to `$DATA/system/project-registry.md` **before** the first save") before Step 7 ever
# calls `journal.py append` — so by the time this function runs, an unregistered slug is either a typo
# or a session that skipped its own precondition, and catching that at write time, before anything
# lands, is the cheapest possible moment to fix it. Nothing is lost by refusing: unlike a partial
# write, `validate()` already raises before touching disk, and this raises the same way — register the
# slug (or fix the typo) and re-run the identical `append` call.
#
# THE ESCAPE HATCH for a genuine legitimate first-write (a real project whose registration is
# deliberately deferred, or a caller that cannot register mid-flow): `allow_unregistered=True` /
# `--allow-unregistered` on the CLI. It does NOT silently accept — it still writes, but the `event`
# field carries a loud, unmissable `[UNREGISTERED SLUG]` marker so nobody downstream mistakes an
# unvetted slug for a filed project. This is deliberate, opt-in, and never the default.
def _check_registered(root, slug):
    """(ok, why-refused). `ok=True` for a registered slug OR when the registry itself could not be
    consulted for a repo-shape reason distinct from 'this slug is unknown' (fails CLOSED — see below,
    it never returns ok=True for a genuinely absent row)."""
    sys.path.insert(0, os.path.join(_REPO, "shared"))
    try:
        import registry as _registry
    except ImportError as e:
        # Fail CLOSED, not open: "the resolver is missing" must not read as "the slug is fine."
        return False, ("could not load shared/registry.py to check slug %r (%s) — refusing rather "
                        "than silently accepting an unverifiable slug" % (slug, e))
    try:
        p = _registry.resolve(slug, root=root)
    except Exception as e:
        return False, "registry.resolve(%r) raised %s — refusing rather than guessing" % (slug, e)
    if p.layout is None:
        return False, ("%r has no row in system/project-registry.md — register it first "
                        "(standard-steps.md Step 0.5: 'add the row ... before the first save'), or "
                        "pass allow_unregistered=True / --allow-unregistered for a deliberate "
                        "first-write ahead of registration." % slug)
    return True, None


def journal_path(root):
    return os.path.join(root, JOURNAL_REL)


def segment_paths(root):
    d = os.path.join(root, SEGMENT_DIR_REL)
    if not os.path.isdir(d):
        return []
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".md"))


def validate(event, supersedes):
    """(ok, why). The two fields that go wrong, checked at write time."""
    e = (event or "").strip()
    if len(e.split()) < 5:
        return False, ("event is too short to be readable without context: %r. Say what changed AND "
                       "why — 'Updated state.' is a filename echo, not an event." % e)
    if e.lower().rstrip(".") in ("updated state", "saved", "updated the brief", "made changes"):
        return False, "event %r says nothing. Say what changed and why." % e
    s = (supersedes or DASH).strip()
    if s == DASH or s.startswith("[partial:") or s == "[renamed]":
        return True, None
    for part in s.split(","):
        p = part.strip()
        if not (p.startswith(("/", "~", ".")) or "/" in p or p.endswith(".md")):
            return False, ("supersedes must be a PATH or %s, never a concept: %r. A concept makes the "
                           "chain unfollowable, which is the one thing it is for." % (DASH, p))
    return True, None


def format_row(slug, event, artifact=None, supersedes=None, desk="root", date=None):
    d = date or datetime.date.today().isoformat()
    tail = ("→ %s" % artifact) if artifact else ("decision: %s" % event)
    return "%s | %s | %s | %s | supersedes: %s | %s" % (
        d, desk, slug, event.strip(), (supersedes or DASH).strip(), tail)


def append(root, slug, event, artifact=None, supersedes=None, desk="root", date=None,
           allow_unregistered=False):
    ok, why = validate(event, supersedes)
    if not ok:
        raise ValueError(why)
    reg_ok, reg_why = _check_registered(root, slug)
    if not reg_ok:
        if not allow_unregistered:
            raise ValueError("unregistered slug — %s" % reg_why)
        # Deliberate first-write ahead of registration: write, but never quietly. The marker rides in
        # `event` so it survives `slice`, grep, and every other reader unchanged in format.
        event = "[UNREGISTERED SLUG] %s" % event.strip()
    p = journal_path(root)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8") as f:
            f.write(JOURNAL_HEADER)
    row = format_row(slug, event, artifact, supersedes, desk, date)
    with open(p, "a", encoding="utf-8") as f:
        f.write(row + "\n")
    # Read it back. A write that returned success is not evidence it landed.
    with open(p, encoding="utf-8") as f:
        if row not in f.read():
            raise IOError("journal append did not land at %s" % p)
    return row


def slice_(root, slug=None, limit=20):
    """Every matching row across the segments AND the current file, oldest first.

    ⛔ The segments come first and the current file last, so the arc reads forwards. A reader that
    opens only the current file loses everything before the last rotation, quietly."""
    rows = []
    for p in segment_paths(root) + [journal_path(root)]:
        if not os.path.isfile(p):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    if not ROW_RE.match(line):
                        continue
                    if slug and ("| %s |" % slug) not in line:
                        continue
                    rows.append(line.rstrip("\n"))
        except Exception:
            continue
    return rows[-limit:] if limit else rows


def rotate(root, dry_run=False, today=None):
    """Move every row from a COMPLETED month out of the current file into its segment.

    The current month stays put — rotating it would split a month across two files and make every
    reader join them back together. Returns {segment: n_moved}."""
    p = journal_path(root)
    if not os.path.isfile(p):
        return {}
    today = today or datetime.date.today()
    keep_key = "%04d-%02d" % (today.year, today.month)

    with open(p, encoding="utf-8") as f:
        lines = f.readlines()

    stay, by_month = [], {}
    for line in lines:
        m = ROW_RE.match(line)
        if not m:
            stay.append(line)
            continue
        key = "%s-%s" % (m.group(1), m.group(2))
        if key == keep_key:
            stay.append(line)
        else:
            by_month.setdefault(key, []).append(line)

    if not by_month or dry_run:
        return {k: len(v) for k, v in by_month.items()}

    segdir = os.path.join(root, SEGMENT_DIR_REL)
    os.makedirs(segdir, exist_ok=True)
    moved = {}
    for key, rows in sorted(by_month.items()):
        seg = os.path.join(segdir, key + ".md")
        with open(seg, "a", encoding="utf-8") as f:
            f.writelines(rows)
        # ⛔ Read back before removing anything from the current file. Nothing leaves without proof.
        with open(seg, encoding="utf-8") as f:
            landed = f.read()
        if not all(r in landed for r in rows):
            raise IOError("rotation aborted: %s did not receive every row — nothing was removed" % seg)
        moved[key] = len(rows)

    tmp = p + ".rotating"
    with open(tmp, "w", encoding="utf-8") as f:
        f.writelines(stay)
    os.replace(tmp, p)
    return moved


def main(argv=None):
    ap = argparse.ArgumentParser(prog="journal.py", description="append to, read, or rotate the journal")
    ap.add_argument("--root", help="the notes folder (default: the one already chosen)")
    sub = ap.add_subparsers(dest="cmd")

    a = sub.add_parser("append")
    a.add_argument("--slug", required=True)
    a.add_argument("--event", required=True)
    a.add_argument("--to", dest="artifact")
    a.add_argument("--supersedes")
    a.add_argument("--desk", default="root")
    a.add_argument("--allow-unregistered", action="store_true",
                   help="write even though --slug has no row in project-registry.md — for a "
                        "deliberate first-write ahead of registration. Marks the event loudly; "
                        "never the default. Omit this and an unregistered slug REFUSES the write.")

    s = sub.add_parser("slice")
    s.add_argument("--slug")
    s.add_argument("--limit", type=int, default=20)

    r = sub.add_parser("rotate")
    r.add_argument("--dry-run", action="store_true")

    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    if not args.cmd:
        ap.print_usage(sys.stderr)
        return 2

    root = notes_root(args.root)
    if root is None:
        print("REFUSED: no notes folder is set — set it first, never guess one", file=sys.stderr)
        return 1

    if args.cmd == "append":
        try:
            print(append(root, args.slug, args.event, args.artifact, args.supersedes, args.desk,
                          allow_unregistered=args.allow_unregistered))
        except ValueError as e:
            print("REFUSED: %s" % e, file=sys.stderr)
            return 2
        return 0

    if args.cmd == "slice":
        rows = slice_(root, args.slug, args.limit)
        if not rows:
            print("No journal entries for %s. Either nothing has been saved, or this is new."
                  % (args.slug or "anything"))
            return 0
        for row in rows:
            print(row)
        print("\nJournal reflects saves via /save and explicitly logged decisions only. In-session "
              "pivots, verbal agreements, and file changes outside /save are not captured. A "
              "clean-looking journal is not a complete journal.")
        return 0

    moved = rotate(root, args.dry_run)
    if not moved:
        print("Nothing to rotate — every entry is from the current month.")
        return 0
    verb = "would move" if args.dry_run else "moved"
    for key, n in sorted(moved.items()):
        print("%s %d entr%s → system/journal/%s.md" % (verb, n, "y" if n == 1 else "ies", key))
    return 0


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    sys.exit(main())
