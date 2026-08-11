#!/usr/bin/env python3
"""test_canon_conflict_scan.py — the gate that stands between an incoming item and canon.

The only outcome that actually costs anything is a FALSE CLEAN — reporting "nothing in canon
covers this" when the scan did not, or could not, read canon. Most of these tests are about that
one failure, from every direction it can arrive.

Run: python3 system/tools/test_canon_conflict_scan.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "canon_conflict_scan.py")
sys.path.insert(0, HERE)
import canon_conflict_scan as ccs  # noqa: E402

SCANNED, BAD_ARGS, NO_CANON_YET, CANNOT_READ = 0, 2, 3, 4


def run(*args):
    p = subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.canon = os.path.join(self.d, "canon")
        os.makedirs(self.canon)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def write(self, name, body):
        path = os.path.join(self.canon, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        return path


class Surfacing(Base):

    def test_a_planted_duplicate_is_surfaced_with_its_line_number(self):
        self.write("current.md", "# canon\n\n- The primary casting type is warm authority.\n")
        rc, out, _ = run("--canon-root", self.canon, "--terms", "casting type",
                         "--title", "casting note")
        self.assertEqual(rc, SCANNED)
        self.assertIn("POSSIBLE DUPLICATE/CONFLICT", out)
        self.assertIn("current.md:3", out)
        self.assertIn("warm authority", out)

    def test_nothing_matching_reports_likely_new_and_says_how_many_it_read(self):
        self.write("current.md", "# canon\n\n- Something entirely unrelated.\n")
        rc, out, _ = run("--canon-root", self.canon, "--terms", "casting type")
        self.assertEqual(rc, SCANNED)
        self.assertIn("LIKELY-NEW", out)
        self.assertIn("1 canon file(s) read", out)

    def test_it_scans_recursively_and_matches_case_insensitively(self):
        self.write("sub/deeper.md", "- WARM AUTHORITY is the lane.\n")
        rc, out, _ = run("--canon-root", self.canon, "--terms", "warm authority")
        self.assertEqual(rc, SCANNED)
        self.assertIn("sub/deeper.md", out)

    def test_a_single_canon_file_can_be_the_root(self):
        f = self.write("canon.md", "- one true thing\n")
        rc, out, _ = run("--canon-root", f, "--terms", "true thing")
        self.assertEqual(rc, SCANNED)
        self.assertIn("POSSIBLE DUPLICATE", out)

    def test_terms_are_matched_literally_not_as_regex(self):
        self.write("current.md", "- a line about a.b\n- a line about axb\n")
        rc, out, _ = run("--canon-root", self.canon, "--terms", "a.b")
        self.assertEqual(rc, SCANNED)
        self.assertIn("about a.b", out)
        self.assertNotIn("about axb", out, "the term was treated as a regex wildcard")

    def test_reported_paths_are_relative_to_canon_not_the_current_directory(self):
        # The caller runs from the repo; canon lives in the person's notes folder. A cwd-relative
        # path is a wall of ../.. at best, and plausible-but-wrong at worst.
        self.write("sub/deeper.md", "- warm authority\n")
        rc, out, _ = run("--canon-root", self.canon, "--terms", "warm authority", "--json")
        self.assertEqual(rc, SCANNED)
        data = json.loads(out)
        self.assertEqual(data["matched_files"], ["sub/deeper.md"])
        self.assertNotIn("..", data["hits"][0]["file"])


class NeverAFalseClean(Base):

    def test_an_unreadable_canon_file_fails_closed_and_does_not_report_new(self):
        # ⭐ THE BUG THIS FILE EXISTS FOR. The per-file read used to sit in a bare
        # `except Exception: continue`, so an unreadable canon dir scanned nothing, matched
        # nothing, and reported LIKELY-NEW — the exact false clean the gate exists to prevent.
        p = self.write("current.md", "- warm authority\n")
        os.chmod(p, 0o000)
        try:
            rc, out, _ = run("--canon-root", self.canon, "--terms", "warm authority")
        finally:
            os.chmod(p, 0o644)
        self.assertEqual(rc, CANNOT_READ)
        self.assertIn("CANNOT-READ", out)
        self.assertNotIn("LIKELY-NEW", out)
        self.assertIn("BLOCK", out)

    def test_one_unreadable_file_among_readable_ones_still_fails_closed(self):
        self.write("ok.md", "- something\n")
        p = self.write("broken.md", "- warm authority\n")
        os.chmod(p, 0o000)
        try:
            rc, out, _ = run("--canon-root", self.canon, "--terms", "warm authority")
        finally:
            os.chmod(p, 0o644)
        self.assertEqual(rc, CANNOT_READ, "a partial scan cannot certify anything")
        self.assertIn("1 of 2", out)

    def test_a_missing_canon_root_is_no_canon_yet_not_a_clean_scan(self):
        rc, out, _ = run("--canon-root", os.path.join(self.d, "nope"), "--terms", "x")
        self.assertEqual(rc, NO_CANON_YET)
        self.assertIn("NO-CANON-YET", out)
        self.assertNotIn("LIKELY-NEW", out)

    def test_an_empty_canon_dir_is_no_canon_yet_not_a_clean_scan(self):
        rc, out, _ = run("--canon-root", self.canon, "--terms", "x")
        self.assertEqual(rc, NO_CANON_YET)
        self.assertIn("NO-CANON-YET", out)
        self.assertNotIn("LIKELY-NEW", out)

    def test_a_dir_holding_only_non_markdown_is_no_canon_yet(self):
        with open(os.path.join(self.canon, "notes.txt"), "w") as f:
            f.write("warm authority\n")
        rc, out, _ = run("--canon-root", self.canon, "--terms", "warm authority")
        self.assertEqual(rc, NO_CANON_YET)

    def test_no_terms_is_refused_as_theatre(self):
        self.write("current.md", "- anything\n")
        rc, _out, err = run("--canon-root", self.canon, "--terms", "  ,  ")
        self.assertEqual(rc, BAD_ARGS)
        self.assertIn("theatre", err)

    def test_a_missing_canon_root_argument_is_refused(self):
        rc, _out, _err = run("--terms", "x")
        self.assertEqual(rc, BAD_ARGS)

    def test_the_four_outcomes_are_distinguishable_in_json(self):
        self.write("current.md", "- warm authority\n")
        _rc, out, _ = run("--canon-root", self.canon, "--terms", "warm authority", "--json")
        self.assertEqual(json.loads(out)["status"], "SCANNED")
        _rc, out, _ = run("--canon-root", os.path.join(self.d, "nope"), "--terms", "x", "--json")
        self.assertEqual(json.loads(out)["status"], "NO-CANON-YET")


class NeverDecides(Base):
    """The judgment is the human's. The tool surfaces evidence and stops."""

    def test_it_never_prints_a_bare_verdict_word_as_a_decision(self):
        self.write("current.md", "- warm authority is the lane\n")
        _rc, out, _ = run("--canon-root", self.canon, "--terms", "warm authority")
        self.assertIn("classify", out.lower())
        self.assertIn("Existing canon wins by default", out)

    def test_it_writes_nothing(self):
        self.write("current.md", "- warm authority\n")
        before = {p: os.path.getmtime(os.path.join(self.canon, p))
                  for p in os.listdir(self.canon)}
        run("--canon-root", self.canon, "--terms", "warm authority")
        after = {p: os.path.getmtime(os.path.join(self.canon, p))
                 for p in os.listdir(self.canon)}
        self.assertEqual(before, after)
        self.assertEqual(sorted(os.listdir(self.canon)), ["current.md"])


class NoHiddenDefault(unittest.TestCase):

    def test_canon_root_has_no_default_placement_is_the_callers_judgment(self):
        src = open(TOOL).read()
        self.assertIn('"--canon-root", required=True', src)
        self.assertNotIn("expanduser(", src, "a hardcoded home-relative default has crept back in")


if __name__ == "__main__":
    unittest.main(verbosity=2)
