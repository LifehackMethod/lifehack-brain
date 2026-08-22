#!/usr/bin/env python3
"""test_journal.py — the append-only backstop.

Two failures matter here and both are quiet ones: a row nobody can read six weeks later, and a read
that misses everything before the last rotation and comes back looking like a quiet stretch.

Run: python3 system/tools/test_journal.py
"""

import datetime
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "journal.py")
sys.path.insert(0, HERE)
import journal as j  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def seg(self, key, *rows):
        d = os.path.join(self.root, "system", "journal")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, key + ".md"), "a") as f:
            f.writelines(r + "\n" for r in rows)

    def cur(self, *rows):
        p = os.path.join(self.root, "system", "journal.md")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a") as f:
            f.writelines(r + "\n" for r in rows)


class Appending(Base):

    def test_a_good_row_lands_with_six_fields(self):
        row = j.append(self.root, "widget", "Chose the folder layout over the flat one because a "
                                            "flat brief has nowhere for the project's own records.",
                       artifact="state/projects/widget/brief.md")
        self.assertEqual(row.count("|"), 5)
        self.assertIn("supersedes: —", row)
        with open(os.path.join(self.root, "system", "journal.md")) as f:
            self.assertIn(row, f.read())

    def test_it_creates_the_journal_if_it_is_missing(self):
        j.append(self.root, "widget", "Started the widget project after the third time it came up.")
        self.assertTrue(os.path.isfile(os.path.join(self.root, "system", "journal.md")))

    def test_a_filename_echo_is_refused(self):
        # The measured failure: a row that says nothing is indistinguishable from no row at all.
        for bad in ("Updated state.", "Saved", "Made changes"):
            with self.assertRaises(ValueError, msg=bad):
                j.append(self.root, "widget", bad)

    def test_a_too_short_event_is_refused(self):
        with self.assertRaises(ValueError):
            j.append(self.root, "widget", "fixed the bug")

    def test_supersedes_must_be_a_path_never_a_concept(self):
        with self.assertRaises(ValueError):
            j.append(self.root, "widget", "Replaced the earlier approach after it failed twice.",
                     supersedes="the old approach")

    def test_supersedes_accepts_a_path_a_dash_and_the_two_annotations(self):
        for s in ("—", "state/projects/widget/old.md", "[partial: only the counts]", "[renamed]"):
            j.append(self.root, "widget", "Replaced the earlier approach after it failed twice.",
                     supersedes=s)

    def test_two_comma_separated_paths_are_a_merge_and_are_allowed(self):
        j.append(self.root, "widget", "Merged the two notes into one after they kept disagreeing.",
                 supersedes="records/a.md, records/b.md")

    def test_nothing_is_written_when_the_row_is_refused(self):
        p = os.path.join(self.root, "system", "journal.md")
        with self.assertRaises(ValueError):
            j.append(self.root, "widget", "Saved")
        self.assertFalse(os.path.exists(p), "a refused row must not create the journal")


class ReadingAcrossSegments(Base):

    def test_a_slice_finds_entries_in_a_rotated_segment(self):
        # ⭐ THE FAILURE THIS FILE EXISTS FOR. Reading only the current file returns a short slice
        # that looks like a quiet project rather than a truncated search.
        self.seg("2026-06", "2026-06-02 | root | widget | A thing from June, and why. | supersedes: — | → y.md")
        self.cur("2026-08-10 | root | widget | The newest thing, and why. | supersedes: — | → x.md")
        rows = j.slice_(self.root, "widget")
        self.assertEqual(len(rows), 2, "the rotated segment was not read")
        self.assertIn("June", rows[0], "segments must come first, so the arc reads forwards")

    def test_the_current_file_alone_would_have_found_one(self):
        self.seg("2026-06", "2026-06-02 | root | widget | A thing from June, and why. | supersedes: — | → y.md")
        self.cur("2026-08-10 | root | widget | The newest thing, and why. | supersedes: — | → x.md")
        with open(os.path.join(self.root, "system", "journal.md")) as f:
            naive = [l for l in f if "| widget |" in l]
        self.assertEqual(len(naive), 1)
        self.assertEqual(len(j.slice_(self.root, "widget")), 2)

    def test_it_filters_by_slug(self):
        self.cur("2026-08-10 | root | widget | The widget thing, and why. | supersedes: — | → x.md",
                 "2026-08-10 | root | gadget | The gadget thing, and why. | supersedes: — | → y.md")
        self.assertEqual(len(j.slice_(self.root, "widget")), 1)
        self.assertEqual(len(j.slice_(self.root)), 2)

    def test_prose_and_headings_are_not_rows(self):
        self.cur("# Journal", "", "Appended to as you work.",
                 "2026-08-10 | root | widget | A real row, with a reason. | supersedes: — | → x.md")
        self.assertEqual(len(j.slice_(self.root)), 1)

    def test_an_unreadable_segment_does_not_take_the_whole_slice_down(self):
        self.seg("2026-06", "2026-06-02 | root | widget | June, and why. | supersedes: — | → y.md")
        self.cur("2026-08-10 | root | widget | August, and why. | supersedes: — | → x.md")
        bad = os.path.join(self.root, "system", "journal", "2026-07.md")
        open(bad, "w").write("x")
        os.chmod(bad, 0o000)
        try:
            self.assertEqual(len(j.slice_(self.root, "widget")), 2)
        finally:
            os.chmod(bad, 0o644)

    def test_an_empty_slice_is_empty_not_an_error(self):
        self.assertEqual(j.slice_(self.root, "nothing-here"), [])

    def test_a_mixed_format_journal_returns_both_canonical_and_legacy_rows_for_a_slug(self):
        self.cur("2026-08-10 | root | widget | The widget thing, and why. | supersedes: — | → x.md",
                 "- 2026-06-21: PROJECT CREATED widget. Chose the layout.",
                 "Just some prose about widget in the middle of the file.",
                 "- just a note about widget")
        rows = j.slice_(self.root, "widget")
        self.assertEqual(len(rows), 2, "expected exactly the canonical and legacy rows")
        self.assertTrue(any("| widget |" in r for r in rows), "canonical row missing")
        self.assertTrue(any(r.startswith("- 2026-06-21: PROJECT CREATED widget") for r in rows),
                        "legacy row missing")
        self.assertFalse(any("Just some prose" in r for r in rows), "prose is not a row")
        self.assertFalse(any(r == "- just a note about widget" for r in rows),
                         "an undated bullet is not a legacy row")

    def test_legacy_rows_are_filtered_by_slug_token_boundaries(self):
        self.cur("- 2026-06-21: PROJECT CREATED widget. Chose the layout.",
                 "- 2026-06-22: PROJECT CREATED gadget. Chose the color.",
                 "- 2026-06-23: PROJECT CREATED widget-v2. A different project entirely.")
        rows = j.slice_(self.root, "widget")
        self.assertEqual(len(rows), 1, "slug filter must not pick up widget-v2 for widget")
        self.assertIn("PROJECT CREATED widget.", rows[0])

    def test_legacy_rows_are_included_with_no_slug_argument(self):
        self.cur("- 2026-06-21: PROJECT CREATED widget. Chose the layout.")
        rows = j.slice_(self.root)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0].startswith("- 2026-06-21:"))

    def test_a_legacy_row_in_a_rotated_segment_is_found_too(self):
        self.seg("2026-06", "- 2026-06-21: PROJECT CREATED widget. Chose the layout.")
        self.cur("2026-08-10 | root | widget | The newest thing, and why. | supersedes: — | → x.md")
        rows = j.slice_(self.root, "widget")
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0].startswith("- 2026-06-21:"), "segments must still come first")


class Rotating(Base):

    def test_a_completed_month_moves_and_the_current_month_stays(self):
        today = datetime.date(2026, 8, 11)
        self.cur("2026-06-02 | root | widget | June, and why. | supersedes: — | → y.md",
                 "2026-07-14 | root | widget | July, and why. | supersedes: — | → z.md",
                 "2026-08-10 | root | widget | August, and why. | supersedes: — | → x.md")
        moved = j.rotate(self.root, today=today)
        self.assertEqual(moved, {"2026-06": 1, "2026-07": 1})
        with open(os.path.join(self.root, "system", "journal.md")) as f:
            left = f.read()
        self.assertIn("August", left)
        self.assertNotIn("June", left)
        self.assertTrue(os.path.isfile(os.path.join(self.root, "system", "journal", "2026-06.md")))

    def test_rotation_loses_nothing_a_slice_still_finds_everything(self):
        today = datetime.date(2026, 8, 11)
        self.cur("2026-06-02 | root | widget | June, and why. | supersedes: — | → y.md",
                 "2026-08-10 | root | widget | August, and why. | supersedes: — | → x.md")
        before = len(j.slice_(self.root, "widget"))
        j.rotate(self.root, today=today)
        self.assertEqual(len(j.slice_(self.root, "widget")), before)

    def test_the_header_prose_is_never_moved(self):
        today = datetime.date(2026, 8, 11)
        self.cur("# Journal", "", "Appended to as you work.",
                 "2026-06-02 | root | widget | June, and why. | supersedes: — | → y.md")
        j.rotate(self.root, today=today)
        with open(os.path.join(self.root, "system", "journal.md")) as f:
            left = f.read()
        self.assertIn("# Journal", left)
        self.assertIn("Appended to as you work.", left)

    def test_dry_run_touches_nothing(self):
        today = datetime.date(2026, 8, 11)
        self.cur("2026-06-02 | root | widget | June, and why. | supersedes: — | → y.md")
        moved = j.rotate(self.root, dry_run=True, today=today)
        self.assertEqual(moved, {"2026-06": 1})
        with open(os.path.join(self.root, "system", "journal.md")) as f:
            self.assertIn("June", f.read())
        self.assertFalse(os.path.isdir(os.path.join(self.root, "system", "journal")))

    def test_rotating_twice_does_not_duplicate(self):
        today = datetime.date(2026, 8, 11)
        self.cur("2026-06-02 | root | widget | June, and why. | supersedes: — | → y.md")
        j.rotate(self.root, today=today)
        j.rotate(self.root, today=today)
        self.assertEqual(len(j.slice_(self.root, "widget")), 1)

    def test_rotating_an_absent_journal_is_a_no_op(self):
        self.assertEqual(j.rotate(self.root), {})


class Cli(Base):
    def _run(self, *args):
        p = subprocess.run([sys.executable, TOOL, "--root", self.root, *args],
                           capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr

    def test_append_refuses_a_bad_event_with_a_nonzero_exit(self):
        rc, _out, err = self._run("append", "--slug", "widget", "--event", "Updated state.")
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", err)

    def test_a_slice_carries_the_coverage_disclaimer(self):
        self.cur("2026-08-10 | root | widget | A real row, with a reason. | supersedes: — | → x.md")
        rc, out, _ = self._run("slice", "--slug", "widget")
        self.assertEqual(rc, 0)
        self.assertIn("A clean-looking journal is not a complete journal.", out)

    def test_an_empty_slice_says_so_rather_than_printing_nothing(self):
        rc, out, _ = self._run("slice", "--slug", "nothing")
        self.assertEqual(rc, 0)
        self.assertIn("No journal entries", out)

    def test_a_slice_whose_only_match_is_a_legacy_row_prints_it_with_the_pre_format_notice(self):
        self.cur("- 2026-06-21: PROJECT CREATED bootcamp-install-recovery. Chose the layout.")
        rc, out, _ = self._run("slice", "--slug", "bootcamp-install-recovery")
        self.assertEqual(rc, 0)
        self.assertIn("- 2026-06-21: PROJECT CREATED bootcamp-install-recovery.", out)
        self.assertIn("⚠ 1 pre-format row(s) shown verbatim", out)
        self.assertNotIn("No journal entries", out)

    def test_a_slug_that_appears_nowhere_still_prints_no_journal_entries(self):
        self.cur("- 2026-06-21: PROJECT CREATED widget. Chose the layout.",
                 "2026-08-10 | root | widget | The widget thing, and why. | supersedes: — | → x.md")
        rc, out, _ = self._run("slice", "--slug", "nowhere-to-be-found")
        self.assertEqual(rc, 0)
        self.assertIn("No journal entries", out)


class FindsTheNotesFolderOnItsOwn(Base):
    """The path every CALLER actually takes, and the one nothing above covers.

    Every test in `Cli` passes --root, which is the one shape that never touches the resolver. That
    is why a broken repo-root computation survived this file's twenty-three tests and was found only
    by running a real session: `_REPO` was one directory short, so `shared/` was looked for at
    `system/shared`, the import failed, and every call refused with "no notes folder is set" -- which
    is ALSO the correct answer when nobody has set a root. A wrong answer wearing a right answer's
    face. `/read` step 2b and `/save` step 7 both call it exactly this way, with no --root at all.
    """

    def _run_with_env(self, *args):
        env = dict(os.environ, LIFEHACK_ROOT=self.root)
        p = subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True, env=env)
        return p.returncode, p.stdout, p.stderr

    def test_repo_root_actually_contains_shared_brain_root(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("journal_under_test", TOOL)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue(os.path.exists(os.path.join(mod._REPO, "shared", "brain_root.py")),
                        "_REPO does not point at the repository root: %s" % mod._REPO)

    def test_a_slice_resolves_the_root_from_the_environment_with_no_root_flag(self):
        self.cur("2026-08-10 | root | widget | A real row, with a reason. | supersedes: — | → x.md")
        rc, out, err = self._run_with_env("slice", "--slug", "widget")
        self.assertEqual(rc, 0, err)
        self.assertIn("A real row", out)
        self.assertNotIn("no notes folder is set", out + err)

    def test_an_append_resolves_the_root_from_the_environment_too(self):
        rc, _out, err = self._run_with_env(
            "append", "--slug", "widget", "--event",
            "Chose local computation over an API call, because it must work offline.",
            "--to", "state/projects/widget/brief.md")
        self.assertEqual(rc, 0, err)
        self.assertIn("widget", open(os.path.join(self.root, "system", "journal.md")).read())


if __name__ == "__main__":
    unittest.main(verbosity=2)
