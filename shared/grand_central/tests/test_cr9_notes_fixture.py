#!/usr/bin/env python3
"""test_cr9_notes_fixture.py -- the cr9 notes-root fixture builds what step 5 will see.

Run: python3 shared/grand_central/tests/test_cr9_notes_fixture.py

Builds the fixture BOTH ways and asserts:
  1. the desk door (shared/desk_door.py) PASSES on desks/planning — given the folder AND given the
     desk_id 'cal' through the desk-list seam (the post-move id/folder mismatch resolves);
  2. shared/desk_list.py resolves desk_id 'cal' to the folder 'planning' (desk_folder), and both
     rows are visible in the list;
  3. the diary entries sit under the card's diary folder at YYYY/MM/DD.md, and the desk's diary
     name derived through shared/grand_central/diary_names.py matches the <Desk>-Diary pattern
     ("Planning-Diary").

Nothing here touches the developer's real notes folder: the fixture builds into a temp root, and
the desk list is reached only through the LIFEHACK_DESK_LIST test seam.
"""
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = os.path.dirname(os.path.dirname(HERE))          # .../shared
REPO = os.path.dirname(SHARED)
sys.path.insert(0, SHARED)
sys.path.insert(0, os.path.join(SHARED, "grand_central"))

import desk_list        # noqa: E402
import diary_names      # noqa: E402

FIXTURE = os.path.join(HERE, "cr9_notes_fixture.py")
DOOR = os.path.join(SHARED, "desk_door.py")

DATE_RE = re.compile(r"\d{4}/\d{2}/\d{2}\.md$")


class Cr9NotesFixtureTests(unittest.TestCase):
    def setUp(self):
        self._tmp_roots = []

    def tearDown(self):
        for root in self._tmp_roots:
            shutil.rmtree(root, ignore_errors=True)

    def build(self, mode):
        root, info = __import__("cr9_notes_fixture").build(mode)
        self._tmp_roots.append(root)
        return root, info

    def seam(self, root):
        """The desk-list test seam pointing at THIS fixture's registry (never the real one)."""
        env = dict(os.environ)
        env["LIFEHACK_DESK_LIST"] = os.path.join(root, "desks", "desk-registry.yaml")
        return env

    # -- 1. the desk door --------------------------------------------------------------

    def test_door_passes_on_planning_folder_with_history(self):
        root, _ = self.build("with-history")
        desk = os.path.join(root, "desks", "planning")
        r = subprocess.run([sys.executable, DOOR, desk], capture_output=True, text=True,
                           env=self.seam(root))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS", r.stdout)

    def test_door_passes_on_planning_folder_empty(self):
        root, _ = self.build("empty")
        desk = os.path.join(root, "desks", "planning")
        r = subprocess.run([sys.executable, DOOR, desk], capture_output=True, text=True,
                           env=self.seam(root))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS", r.stdout)

    def test_door_resolves_planning_by_desk_id_cal(self):
        """The post-move mismatch: desk_id 'cal', folder desks/planning. Given the id, the door
        resolves through the desk list to the right folder and passes."""
        root, _ = self.build("with-history")
        r = subprocess.run([sys.executable, DOOR, "cal"], capture_output=True, text=True,
                           env=self.seam(root))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PASS", r.stdout)
        self.assertIn(os.path.join(root, "desks", "planning"), r.stdout)

    # -- 2. the desk list --------------------------------------------------------------

    def test_desk_list_resolves_cal_to_planning(self):
        root, _ = self.build("with-history")
        env = self.seam(root)
        self.assertEqual(desk_list.desk_ids(env), {"cal", "archive"})
        folder, err = desk_list.desk_folder("cal", env)
        self.assertIsNone(err)
        self.assertEqual(folder, "planning")
        folder, err = desk_list.desk_folder("archive", env)
        self.assertIsNone(err)
        self.assertEqual(folder, "archive")
        missing, err = desk_list.desk_folder("nobody", env)
        self.assertIsNone(missing)
        self.assertIsNone(err)

    # -- 3. the diary ------------------------------------------------------------------

    def test_diary_entries_match_pattern_and_folder(self):
        root, info = self.build("with-history")
        self.assertEqual(len(info["diary_entries"]), 2)
        # every entry sits under the desk's diary folder, named YYYY/MM/DD.md
        diary_dir = os.path.join(root, "desks", "planning", "diary")
        for entry in info["diary_entries"]:
            self.assertTrue(os.path.isfile(entry), entry)
            rel = os.path.relpath(entry, diary_dir)
            self.assertTrue(DATE_RE.search(rel.replace(os.sep, "/")), rel)
        on_disk = glob.glob(os.path.join(diary_dir, "*", "*", "*.md"))
        self.assertEqual(sorted(os.path.realpath(p) for p in on_disk),
                         sorted(os.path.realpath(p) for p in info["diary_entries"]))
        # the NAME comes from the ONE shared pattern: {display}-Diary -> Planning-Diary
        self.assertEqual(
            diary_names.diary_name("cal", {"desks": {"cal": {"display": "Planning"}}}),
            "Planning-Diary")
        self.assertEqual(
            diary_names.diary_name("other-desk",
                                   {"desks": {"other-desk": {"display": "Other-desk"}}}),
            "Other-desk-Diary")

    def test_empty_mode_has_no_feeds(self):
        root, info = self.build("empty")
        self.assertEqual(info["diary_entries"], [])
        desk = os.path.join(root, "desks", "planning")
        self.assertEqual(glob.glob(os.path.join(desk, "records", "context", "*.md")), [])
        self.assertEqual(glob.glob(os.path.join(desk, "diary", "*", "*", "*.md")), [])
        # the skeleton is still there — folders exist, they are empty
        for need in ("canon/canon.md", "canon/purpose.md", "open-loops.md", "desk.yaml", "CLAUDE.md"):
            self.assertTrue(os.path.isfile(os.path.join(desk, need)), need)


if __name__ == "__main__":
    unittest.main(verbosity=2)
