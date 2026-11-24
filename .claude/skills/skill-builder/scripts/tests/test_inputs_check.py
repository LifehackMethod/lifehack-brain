#!/usr/bin/env python3
"""Tests for inputs_check.py (stdlib unittest).

Run:  python3 -m unittest discover -s .claude/skills/skill-builder/scripts/tests
(from the repo root; from a staged copy the repo is found by walking up, or set
LIFEHACK_REPO_ROOT).
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(TESTS_DIR)
SCRIPT = os.path.join(SCRIPTS_DIR, "inputs_check.py")


def repo_root():
    env = os.environ.get("LIFEHACK_REPO_ROOT")
    if env:
        return env
    d = os.path.dirname(SCRIPTS_DIR)
    for _ in range(8):
        if os.path.isfile(os.path.join(d, "shared", "paths.py")):
            return d
        d = os.path.dirname(d)
    return None


def run_script(script_path, argv):
    env = dict(os.environ)
    r = repo_root()
    if r:
        env["PYTHONPATH"] = os.path.join(r, "shared") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, script_path] + argv,
                          capture_output=True, text=True, env=env, timeout=60)


def make_packet(parent, name, sections):
    """sections: {section_name: content or None (omit file)}"""
    workdir = os.path.join(parent, name)  # names may contain spaces
    os.makedirs(os.path.join(workdir, "scratchpad"), exist_ok=True)
    for section, content in sections.items():
        if content is not None:
            with open(os.path.join(workdir, "scratchpad", section + ".md"), "w", encoding="utf-8") as fh:
                fh.write(content)
    return workdir


GOOD_1_2 = {"packet-path": "/somewhere/the-packet-folder\n(multi-line value)\n"}


class InputsCheckGood(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_good_required_present(self):
        wd = make_packet(self.tmp, "packet folder", GOOD_1_2)
        r = run_script(SCRIPT, ["--workdir", wd, "--substep", "1.2"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("inputs: packet-path", r.stdout)
        self.assertIn("RECEIPT inputs_check.py PASS", r.stdout)

    def test_good_optional_only(self):
        # 1.1 needs nothing required; an absent optional is not a pause
        wd = make_packet(self.tmp, "packet folder", {})
        r = run_script(SCRIPT, ["--workdir", wd, "--substep", "1.1"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("inputs: (none)", r.stdout)

    def test_optional_present_is_listed(self):
        wd = make_packet(self.tmp, "packet folder",
                         dict(GOOD_1_2, **{"pointed-skill": "/a/skill/folder\n"}))
        r = run_script(SCRIPT, ["--workdir", wd, "--substep", "1.2"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("inputs: packet-path, pointed-skill", r.stdout)


class InputsCheckEdge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_whitespace_only_section_is_missing(self):
        wd = make_packet(self.tmp, "packet folder", {"packet-path": "   \n\t\n"})
        r = run_script(SCRIPT, ["--workdir", wd, "--substep", "1.2"])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("waiting: packet from 1.1", r.stdout)
        self.assertIn("FAIL", r.stdout)

    def test_absent_required_section_is_missing_with_spec_pause(self):
        wd = make_packet(self.tmp, "packet folder", {})
        r = run_script(SCRIPT, ["--workdir", wd, "--substep", "1.2"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("waiting: packet from 1.1", r.stdout)

    def test_spec_worded_pause_for_2_1(self):
        wd = make_packet(self.tmp, "packet folder", {"outcome": "wants a receipts skill\n"})
        r = run_script(SCRIPT, ["--workdir", wd, "--substep", "2.1"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("waiting: findings checked by 1.7", r.stdout)

    def test_multi_line_value_and_spaces_in_path(self):
        wd = make_packet(self.tmp, "a packet folder with spaces",
                         {"packet-path": "line one\nline two\n"})
        r = run_script(SCRIPT, ["--workdir", wd, "--substep", "1.2"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_unknown_substep_refused_loudly(self):
        wd = make_packet(self.tmp, "packet folder", GOOD_1_2)
        r = run_script(SCRIPT, ["--workdir", wd, "--substep", "9.9"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("REFUSED", r.stdout)
        self.assertIn("WHAT TO DO", r.stdout)
        self.assertIn("RULE", r.stdout)
        self.assertIn("COULD-NOT-CHECK", r.stdout)

    def test_unreadable_workdir(self):
        r = run_script(SCRIPT, ["--workdir", os.path.join(self.tmp, "nope"),
                                "--substep", "1.2"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("COULD-NOT-CHECK", r.stdout)


class InputsCheckPadded(unittest.TestCase):
    """Right words buried in filler / near-miss spellings must NOT pass."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_near_miss_section_names_do_not_count(self):
        wd = make_packet(self.tmp, "packet folder", {
            "packet-paths": "near-miss plural\n",
            "packet_path": "near-miss underscore\n",
            "PACKET-PATH": "near-miss case\n",
            "packet-path-backup": "near-miss suffix\n",
        })
        r = run_script(SCRIPT, ["--workdir", wd, "--substep", "1.2"])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("waiting: packet from 1.1", r.stdout)

    def test_mention_of_the_words_in_another_file_does_not_count(self):
        # the words "packet-path" buried in an unrelated section's text
        wd = make_packet(self.tmp, "packet folder", {"known": "the packet-path is elsewhere\n"})
        r = run_script(SCRIPT, ["--workdir", wd, "--substep", "1.2"])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)


class InputsCheckBrokenCopy(unittest.TestCase):
    """Copy the script, break its core check, and prove the suite would catch it."""

    def test_broken_copy_passes_where_it_must_fail(self):
        with open(SCRIPT, encoding="utf-8") as fh:
            src = fh.read()
        needle = "missing = [s for s in required if not section_present(args.workdir, s)]"
        self.assertIn(needle, src, "core check line changed; fix the broken-copy test")
        broken_src = src.replace(needle, "missing = []")
        with tempfile.TemporaryDirectory() as tmp:
            broken = os.path.join(tmp, "inputs_check.py")
            with open(broken, "w", encoding="utf-8") as fh:
                fh.write(broken_src)
            wd = make_packet(tmp, "packet folder", {})  # required section missing
            good = run_script(SCRIPT, ["--workdir", wd, "--substep", "1.2"])
            bad = run_script(broken, ["--workdir", wd, "--substep", "1.2"])
        self.assertEqual(good.returncode, 1, good.stdout)
        self.assertEqual(bad.returncode, 0, bad.stdout)  # the break is visible


if __name__ == "__main__":
    unittest.main()
