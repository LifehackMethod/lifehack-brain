#!/usr/bin/env python3
"""test_check_slug_folder.py — the folder-name drift detector.

The rule it enforces (folder leaf == slug) has no write-time gate anywhere; this detector is the
only thing that catches the drift. So the cases that matter are the ones where it would stay quiet
about a real mismatch, and the ones where it would cry wolf about a legitimate one.

Run: python3 system/tools/project-manager/test_check_slug_folder.py
"""

import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "check_slug_folder.py")
sys.path.insert(0, HERE)
import check_slug_folder as csf  # noqa: E402


def rows(*lines):
    return list(lines)


class Detects(unittest.TestCase):

    def test_a_matching_leaf_is_clean(self):
        checked, bad = csf.check(rows("root | widget | Widget | active | state/projects/widget"))
        self.assertEqual((checked, bad), (1, []))

    def test_a_category_prefix_is_fine_only_the_leaf_matters(self):
        checked, bad = csf.check(rows(
            "root | widget | Widget | active | state/projects/infrastructure/widget"))
        self.assertEqual((checked, bad), (1, []))

    def test_a_mismatched_leaf_is_reported(self):
        checked, bad = csf.check(rows(
            "root | lifehack-organism | Organism | active | state/projects/organism-build"))
        self.assertEqual(checked, 1)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0][0], "lifehack-organism")
        self.assertEqual(bad[0][1], "organism-build")

    def test_a_row_ending_in_brief_md_compares_the_folder_not_the_file(self):
        checked, bad = csf.check(rows(
            "root | widget | Widget | active | state/projects/widget/brief.md"))
        self.assertEqual((checked, bad), (1, []))

    def test_a_trailing_slash_does_not_create_an_empty_leaf(self):
        checked, bad = csf.check(rows("root | widget | Widget | active | state/projects/widget/"))
        self.assertEqual((checked, bad), (1, []))


class StaysQuiet(unittest.TestCase):
    """Every case here is a row it must NOT count — a detector that cries wolf gets ignored."""

    def test_a_completed_project_is_skipped(self):
        checked, bad = csf.check(rows(
            "root | widget | Widget | complete | state/projects/old-widget-name"))
        self.assertEqual((checked, bad), (0, []))

    def test_a_split_project_is_skipped(self):
        checked, bad = csf.check(rows(
            "root | widget | Widget | split → [a, b] | state/projects/whatever"))
        self.assertEqual((checked, bad), (0, []))

    def test_a_four_field_row_has_no_path_to_check(self):
        checked, bad = csf.check(rows("root | widget | Widget | active"))
        self.assertEqual((checked, bad), (0, []))

    def test_prose_and_table_decoration_are_not_rows(self):
        checked, bad = csf.check(rows(
            "The format is: {desk} | {slug} | {display name} | {status} | {path}",
            "|---|---|---|---|---|",
            "# Projects",
            ""))
        self.assertEqual((checked, bad), (0, []))

    def test_an_empty_path_field_is_skipped(self):
        checked, bad = csf.check(rows("root | widget | Widget | active |   "))
        self.assertEqual((checked, bad), (0, []))


class Cli(unittest.TestCase):

    def _run(self, *args, env=None):
        e = dict(os.environ)
        e.pop("LIFEHACK_ROOT", None)
        if env:
            e.update(env)
        p = subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True, env=e)
        return p.returncode, p.stdout.strip(), p.stderr.strip()

    def test_a_mismatch_is_a_result_not_a_failure_exit_0(self):
        with tempfile.TemporaryDirectory() as d:
            reg = os.path.join(d, "project-registry.md")
            open(reg, "w").write("root | widget | Widget | active | state/projects/wrong-name\n")
            rc, out, _ = self._run(reg)
            self.assertEqual(rc, 0, "a found mismatch must not read as a broken tool")
            self.assertIn("1 mismatch", out)
            self.assertIn("wrong-name", out)

    def test_a_clean_registry_says_so(self):
        with tempfile.TemporaryDirectory() as d:
            reg = os.path.join(d, "project-registry.md")
            open(reg, "w").write("root | widget | Widget | active | state/projects/widget\n")
            rc, out, _ = self._run(reg)
            self.assertEqual(rc, 0)
            self.assertIn("✓", out)

    def test_an_unreadable_registry_exits_1_and_says_which_file(self):
        rc, out, _ = self._run("/tmp/definitely-not-a-registry-xyz.md")
        self.assertEqual(rc, 1)
        self.assertIn("cannot read the registry", out)

    def test_with_no_notes_folder_chosen_it_refuses_rather_than_guessing(self):
        # The whole point of the resolver: no root set means STOP, never the current directory.
        with tempfile.TemporaryDirectory() as fake_home:
            rc, out, _ = self._run(env={"HOME": fake_home})
            self.assertEqual(rc, 1)
            self.assertIn("REFUSED", out)
            self.assertNotIn("mismatch", out)

    def test_it_finds_the_registry_under_the_notes_folder(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "system"))
            open(os.path.join(d, "system", "project-registry.md"), "w").write(
                "root | widget | Widget | active | state/projects/nope\n")
            rc, out, _ = self._run(env={"LIFEHACK_ROOT": d})
            self.assertEqual(rc, 0)
            self.assertIn("1 mismatch", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
