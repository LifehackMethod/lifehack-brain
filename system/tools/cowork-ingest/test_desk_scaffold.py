#!/usr/bin/env python3
"""test_desk_scaffold.py — a new desk is born to the desk-building SOP's §2 shape, and a scaffold that
does NOT match that shape cannot print OK.

Run:  python3 system/tools/cowork-ingest/test_desk_scaffold.py

WHY THIS EXISTS — CR-9 step 2(a) (ledger L34/D11): desk_scaffold.py was rewritten to the SOP's desk
shape (no `state/` folder; `canon/canon.md`; `canon/purpose.md`; a `desk.yaml` card of exactly three
facts; records, diary, open-loops at the desk root, the desk's own CLAUDE.md, `projects/`; a row in
the person's ONE desk list through shared/desk_list.py). A scaffold that still builds the v1 shape
fails the desk door, so these tests pin the new shape AND prove a planted fault is caught:
a scaffold missing `canon/purpose.md` must FAIL, never print OK.

The tests run the tool as a subprocess into a temp notes root. They never touch the person's real
desks or desk list (item 4 of the step: the desk list is found only at <notes>/desks/desk-registry.yaml
under the temp root).
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TOOL = os.path.join(HERE, "desk_scaffold.py")


def run_scaffold(notes_root, extra=()):
    return subprocess.run(
        [sys.executable, TOOL, "--drive-root", notes_root, "--desk", "alpha",
         "--purpose", "one line of purpose", *extra],
        capture_output=True, text=True, cwd=REPO)


class DeskScaffoldCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="desk-scaffold-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestShape(DeskScaffoldCase):
    """A scaffolded desk matches canon/desk-building-sop.md §2 exactly."""

    def test_scaffold_builds_the_sop_shape_and_passes_its_own_check(self):
        r = run_scaffold(self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        base = os.path.join(self.tmp, "desks", "alpha")
        # the eight items, exactly as §2/§7 list them
        for d in ("canon", "records", "diary", "projects"):
            self.assertTrue(os.path.isdir(os.path.join(base, d)), d)
        for f in ("canon/canon.md", "canon/purpose.md", "open-loops.md", "desk.yaml", "CLAUDE.md"):
            self.assertTrue(os.path.isfile(os.path.join(base, f)), f)
        # the v1 shape is GONE: no state/ folder, no canon/current.md, no _registry.md
        self.assertFalse(os.path.exists(os.path.join(base, "state")))
        self.assertFalse(os.path.exists(os.path.join(base, "canon", "current.md")))
        self.assertFalse(os.path.exists(os.path.join(base, "_registry.md")))
        # the card: exactly three facts — name, canon, diary — and the pointers resolve
        with open(os.path.join(base, "desk.yaml"), encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh.read().splitlines() if ln.strip() and not ln.strip().startswith("#")]
        self.assertEqual(sorted(lines), ["canon: canon/canon.md", "diary: Alpha-Diary", "name: alpha"])
        self.assertTrue(os.path.isfile(os.path.join(base, "canon", "canon.md")))

    def test_diary_is_named_by_the_ONE_shared_pattern_not_a_copy(self):
        """'<Desk>-Diary' comes from shared/grand_central/diary_names.py — the tool reuses it."""
        r = run_scaffold(self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Alpha-Diary", r.stdout)
        sys.path.insert(0, os.path.join(REPO, "shared"))
        sys.path.insert(0, os.path.join(REPO, "shared", "grand_central"))
        import diary_names
        import desk_scaffold
        # the tool's own helper and the shared pattern agree, without the tool carrying a copy
        self.assertEqual(desk_scaffold.diary_name_for("bravo"), "Bravo-Diary")
        self.assertEqual(desk_scaffold.diary_name_for("bravo"),
                         diary_names.diary_name("bravo", {"desks": {"bravo": {"display": "Bravo"}}}))

    def test_row_lands_in_the_ONE_desk_list_and_loads_through_desk_list(self):
        r = run_scaffold(self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        list_path = os.path.join(self.tmp, "desks", "desk-registry.yaml")
        self.assertTrue(os.path.isfile(list_path))
        with open(list_path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("schema_version: 2", text)
        self.assertIn("- desk_id: alpha", text)
        self.assertIn("open_loops_path: desks/alpha/open-loops.md", text)  # desk root — no state/
        # the ONE list reads back through shared/desk_list.py, via its env seam
        env = dict(os.environ, LIFEHACK_DESK_LIST=list_path)
        sys.path.insert(0, os.path.join(REPO, "shared"))
        import desk_list
        desks, err = desk_list.load_desks(env)
        self.assertIsNone(err)
        self.assertEqual([d["desk_id"] for d in desks], ["alpha"])
        folder, ferr = desk_list.desk_folder("alpha", env)
        self.assertIsNone(ferr)
        self.assertEqual(folder, "alpha")
        # a second scaffold of the same desk_id is refused — one desk, one row
        shutil.rmtree(os.path.join(self.tmp, "desks", "alpha"))
        r2 = run_scaffold(self.tmp)
        self.assertNotEqual(r2.returncode, 0)
        self.assertIn("already has a row", r2.stderr)
        with open(list_path, encoding="utf-8") as fh:
            self.assertEqual(fh.read().count("desk_id: alpha"), 1)

    def test_register_no_prints_the_row_and_writes_no_list(self):
        r = run_scaffold(self.tmp, ["--register", "no"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "desks", "desk-registry.yaml")))

    def test_dry_run_writes_nothing(self):
        r = run_scaffold(self.tmp, ["--dry-run"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "desks", "alpha")))

    def test_existing_desk_and_bad_slug_are_refused(self):
        r = run_scaffold(self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r2 = run_scaffold(self.tmp)
        self.assertNotEqual(r2.returncode, 0)
        self.assertIn("REFUSED", r2.stderr)
        r3 = run_scaffold(self.tmp, ["--desk", "../escape"])
        self.assertNotEqual(r3.returncode, 0)
        self.assertIn("REFUSED", r3.stderr)


class TestPlantedFaultFails(DeskScaffoldCase):
    """The step's requirement: a planted fault FAILS — e.g. a scaffold missing canon/purpose.md."""

    def _scaffold_then(self, mutate):
        r = run_scaffold(self.tmp)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        base = os.path.join(self.tmp, "desks", "alpha")
        mutate(base)
        sys.path.insert(0, HERE)
        import desk_scaffold
        return desk_scaffold.check_shape(base, "alpha")

    def test_missing_canon_purpose_md_is_caught(self):
        problems = self._scaffold_then(
            lambda base: os.remove(os.path.join(base, "canon", "purpose.md")))
        self.assertEqual(len(problems), 1)
        self.assertIn("canon/purpose.md", problems[0])

    def test_missing_purpose_fails_a_whole_recheck_run_not_OK(self):
        """End to end: the tool refuses to print OK over a wrong shape (its own check runs after writing)."""
        import desk_scaffold
        base = os.path.join(self.tmp, "desks", "alpha")
        os.makedirs(os.path.join(base, "canon"))
        with open(os.path.join(base, "desk.yaml"), "w", encoding="utf-8") as fh:
            fh.write("name: alpha\ncanon: canon/canon.md\ndiary: Alpha-Diary\n")
        list_path = os.path.join(self.tmp, "desks", "desk-registry.yaml")
        with open(list_path, "w", encoding="utf-8") as fh:
            fh.write("schema_version: 2\ndesks:\n  - desk_id: alpha\n")
        problems = desk_scaffold.check_shape(base, "alpha", list_path=list_path)
        self.assertTrue(any("canon/purpose.md" in p for p in problems), problems)

    def test_a_fourth_card_fact_is_caught(self):
        def plant(base):
            with open(os.path.join(base, "desk.yaml"), encoding="utf-8") as fh:
                text = fh.read()
            with open(os.path.join(base, "desk.yaml"), "w", encoding="utf-8") as fh:
                fh.write(text + "jobs: some-row\n")  # jobs belong to the job list, never the card
        problems = self._scaffold_then(plant)
        self.assertTrue(any("may not carry" in p and "jobs" in p for p in problems), problems)

    def test_a_state_folder_is_caught(self):
        problems = self._scaffold_then(
            lambda base: os.makedirs(os.path.join(base, "state")))
        self.assertTrue(any("state/" in p for p in problems), problems)

    def test_a_dangling_card_pointer_is_caught(self):
        def plant(base):
            with open(os.path.join(base, "desk.yaml"), encoding="utf-8") as fh:
                text = fh.read()
            with open(os.path.join(base, "desk.yaml"), "w", encoding="utf-8") as fh:
                fh.write(text.replace("canon/canon.md", "canon/gone.md"))
        problems = self._scaffold_then(plant)
        self.assertTrue(any("does not resolve" in p for p in problems), problems)

    def test_a_desk_missing_from_the_list_is_caught(self):
        import desk_scaffold
        base = os.path.join(self.tmp, "desks", "alpha")
        r = run_scaffold(self.tmp, ["--register", "no"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        list_path = os.path.join(self.tmp, "desks", "desk-registry.yaml")
        os.makedirs(os.path.join(self.tmp, "desks"), exist_ok=True)
        with open(list_path, "w", encoding="utf-8") as fh:
            fh.write("schema_version: 2\ndesks:\n  - desk_id: other\n")
        problems = desk_scaffold.check_shape(base, "alpha", list_path=list_path)
        self.assertTrue(any("no row in the desk list" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
