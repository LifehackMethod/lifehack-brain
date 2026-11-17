#!/usr/bin/env python3
"""cr9_notes_fixture.py -- builds a THROWAWAY notes root with the planning desk's real shape
(canon/desk-building-sop.md §2), for Grand Central's skill tests and the V2 plan's step 5.

A fixture BUILDER, not a committed folder tree: every run makes a fresh temp root and prints its
path. The desks inside are made by the real scaffold (system/tools/cowork-ingest/desk_scaffold.py,
run as a subprocess with --register no), so the fixture tests what step 5 will actually see -- never
a hand-copied shape that can drift from the scaffold.

What the root holds (both modes):
    <root>/desks/desk-registry.yaml  schema_version 2, two rows:
        - desk_id 'cal'      -> paths under desks/planning/  (mirrors the owner's post-move
                                state: the id is 'cal', the FOLDER is 'planning' -- the mismatch
                                is deliberate and is what desk resolvers must survive)
        - desk_id 'archive'  -> a generic second desk, no personal names anywhere
    <root>/desks/planning/   the SOP §2 shape, scaffolded: canon/canon.md, canon/purpose.md,
                             records/, diary/, open-loops.md, desk.yaml, CLAUDE.md, projects/
    <root>/desks/archive/    the same shape, generic

With --with-history (the default) the planning desk additionally carries day-one feeds:
    records/context/<YYYY-MM-DD>-cal.md      one dated draft, in the engine's naming
                                             (shared/grand_central/morning.py: records/context/
                                             <day>-<desk>.md)
    diary/YYYY/MM/DD.md                      two past dated Planning-Diary entries
With --empty: neither -- the no-feeds day-one state (the folders exist, they are empty).

Generic everywhere: no personal names, desks, emails or content (No Private Desks stays clean).

CLI:
    python3 shared/grand_central/tests/cr9_notes_fixture.py [--empty | --with-history]
Prints the temp root's path on the last line.
"""
import argparse
import datetime
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # tests -> grand_central -> shared -> repo
SCAFFOLD = os.path.join(ROOT, "system", "tools", "cowork-ingest", "desk_scaffold.py")

PLANNING_DESK = "planning"   # the FOLDER under desks/
PLANNING_ID = "cal"          # the desk_id in the registry row (owner's post-move state)
OTHER_DESK = "archive"       # the generic second desk (folder and id are the same slug)

REGISTRY_HEADER = "schema_version: 2\ndesks:\n"

DRAFT_BODY = (
    "---\ntitle: {day} — morning context ({desk})\nrecord_type: context\n"
    "desk: {desk}\ncreated_at: {day}\nstatus: active\n---\n\n"
    "# What changed first\n\n_(synthetic fixture text — no real content)_\n"
)

DIARY_BODY = (
    "# {name} — {day}\n\n"
    "_(synthetic fixture entry — one spare boil-down per day, never edited)_\n\n"
    "Sources: records/context/{day}-{desk}.md\n"
)


def _run_scaffold(notes_root, desk):
    """Scaffold one desk folder into the temp root; the desk-list row is NOT written by the
    scaffold (--register no) because the planning row's desk_id ('cal') differs from its folder
    ('planning') — the registry is written once below, by hand, with both rows."""
    r = subprocess.run(
        [sys.executable, SCAFFOLD, "--notes-root", notes_root, "--desk", desk,
         "--purpose", "synthetic fixture desk for tests", "--register", "no"],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("desk_scaffold failed for %r: %s %s" % (desk, r.stdout, r.stderr))


def _registry_text():
    """The two registry rows, in the simple shape shared/desk_list.py reads."""
    def row(desk_id, folder):
        return (
            " - desk_id: %s\n"
            "   open_loops_path: desks/%s/open-loops.md\n"
            "   purpose_path: desks/%s/canon/purpose.md\n"
            "   reads_external: no\n"
            "   backlog_mode: register\n"
            "   notes: synthetic fixture desk (no real content)\n" % (desk_id, folder, folder))
    return REGISTRY_HEADER + row(PLANNING_ID, PLANNING_DESK) + row(OTHER_DESK, OTHER_DESK)


def _past_days(n):
    """n distinct past dates, oldest first (the diary tree's natural order)."""
    days = []
    d = datetime.date.today()
    while len(days) < n:
        d -= datetime.timedelta(days=1)
        days.append(d)
    return list(reversed(days))


def build(mode="with-history"):
    """Build the fixture -> (notes_root, info dict). mode is 'with-history' (default) or 'empty'.
    Never touches anything outside the temp root it creates."""
    if mode not in ("with-history", "empty"):
        raise ValueError("mode must be 'with-history' or 'empty', got %r" % mode)
    notes = tempfile.mkdtemp(prefix="cr9-notes-fixture-")
    for desk in (PLANNING_DESK, OTHER_DESK):
        _run_scaffold(notes, desk)
    reg = os.path.join(notes, "desks", "desk-registry.yaml")
    with open(reg, "w", encoding="utf-8") as f:
        f.write(_registry_text())

    diary_name = "%s-Diary" % PLANNING_DESK.capitalize()  # via diary_names' {display}-Diary pattern
    diary_files = []
    if mode == "with-history":
        ctx = os.path.join(notes, "desks", PLANNING_DESK, "records", "context")
        os.makedirs(ctx, exist_ok=True)
        for day in _past_days(2):
            day_s = day.isoformat()
            # one dated draft in the engine's naming: records/context/<YYYY-MM-DD>-<desk>.md
            draft = os.path.join(ctx, "%s-%s.md" % (day_s, PLANNING_ID))
            with open(draft, "w", encoding="utf-8") as f:
                f.write(DRAFT_BODY.format(day=day_s, desk=PLANNING_ID))
            # one diary entry per day at YYYY/MM/DD.md, named by the <Desk>-Diary pattern
            entry = os.path.join(notes, "desks", PLANNING_DESK, "diary",
                                 "%04d" % day.year, "%02d" % day.month, "%02d.md" % day.day)
            os.makedirs(os.path.dirname(entry), exist_ok=True)
            with open(entry, "w", encoding="utf-8") as f:
                f.write(DIARY_BODY.format(name=diary_name, day=day_s, desk=PLANNING_ID))
            diary_files.append(entry)
    return notes, {"mode": mode, "registry": reg,
                   "planning_desk": os.path.join(notes, "desks", PLANNING_DESK),
                   "diary_entries": diary_files}


def main():
    ap = argparse.ArgumentParser(description="build a throwaway notes-root fixture (planning desk shape)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--empty", action="store_true",
                   help="no records, no diary entries: the no-feeds day-one state")
    g.add_argument("--with-history", action="store_true",
                   help="records/context draft + two past diary entries (the default)")
    a = ap.parse_args()
    mode = "empty" if a.empty else "with-history"
    notes, _info = build(mode)
    print("fixture mode: %s" % mode)
    print(notes)  # the root path, last line — for `root=$(... | tail -1)`


if __name__ == "__main__":
    main()
