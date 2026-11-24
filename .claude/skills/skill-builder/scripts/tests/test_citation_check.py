#!/usr/bin/env python3
"""Tests for citation_check.py (stdlib unittest).

Run:  python3 -m unittest discover -s .claude/skills/skill-builder/scripts/tests
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(TESTS_DIR)
SCRIPT = os.path.join(SCRIPTS_DIR, "citation_check.py")


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


def make_packet(parent, name, files):
    """files: {relative path inside packet: content}"""
    workdir = os.path.join(parent, name)
    os.makedirs(workdir, exist_ok=True)
    for rel, content in files.items():
        p = os.path.join(workdir, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(content)
    return workdir


def write_packet_file(workdir, name, text):
    p = os.path.join(workdir, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


class CitationCheckGood(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_existing_citation_passes(self):
        wd = make_packet(self.tmp, "packet folder",
                         {"scratchpad/packet-path.md": "the packet\n"})
        f = write_packet_file(wd, "packet.md", "see `scratchpad/packet-path.md` for the packet\n")
        r = run_script(SCRIPT, ["--workdir", wd, "--file", f])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("RECEIPT citation_check.py PASS 1 citation(s) checked", r.stdout)

    def test_outside_paths_skipped_and_counted(self):
        wd = make_packet(self.tmp, "packet folder", {"scratchpad/a.md": "x\n"})
        f = write_packet_file(wd, "packet.md",
                              "`/abs/path` `~home` `<brain>` `system/jobs.md` `1.6` "
                              "`none-of-these` `scratchpad/a.md`\n")
        r = run_script(SCRIPT, ["--workdir", wd, "--file", f])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("6 not checked here", r.stdout)


class CitationCheckEdge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_path_with_space(self):
        wd = make_packet(self.tmp, "packet folder",
                         {"notes/my file.md": "spaces are fine\n"})
        f = write_packet_file(wd, "packet.md", "read `notes/my file.md` now\n")
        r = run_script(SCRIPT, ["--workdir", wd, "--file", f])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_duplicate_reported_not_fatal(self):
        wd = make_packet(self.tmp, "packet folder",
                         {"scratchpad/packet-path.md": "the packet\n"})
        f = write_packet_file(wd, "packet.md",
                              "see `scratchpad/packet-path.md`; again `scratchpad/packet-path.md`\n")
        r = run_script(SCRIPT, ["--workdir", wd, "--file", f])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("duplicate citations (1)", r.stdout)

    def test_missing_citation_fails_with_count(self):
        wd = make_packet(self.tmp, "packet folder", {})
        f = write_packet_file(wd, "packet.md",
                              "see `scratchpad/packet-path.md` and `scratchpad/outcome.md`\n")
        r = run_script(SCRIPT, ["--workdir", wd, "--file", f])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("missing (2)", r.stdout)
        self.assertIn("scratchpad/outcome.md", r.stdout)
        self.assertIn("RECEIPT citation_check.py FAIL", r.stdout)

    def test_unreadable_file_is_could_not_check(self):
        wd = make_packet(self.tmp, "packet folder", {})
        r = run_script(SCRIPT, ["--workdir", wd,
                                "--file", os.path.join(wd, "not-there.md")])
        self.assertEqual(r.returncode, 2)
        self.assertIn("COULD-NOT-CHECK", r.stdout)
        self.assertIn("REFUSED", r.stdout)

    def test_unreadable_workdir_is_could_not_check(self):
        f = os.path.join(self.tmp, "loose.md")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write("nothing\n")
        r = run_script(SCRIPT, ["--workdir", os.path.join(self.tmp, "nope"), "--file", f])
        self.assertEqual(r.returncode, 2)


class CitationCheckPadded(unittest.TestCase):
    """Near-miss spellings must NOT pass."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_near_miss_filename_fails(self):
        wd = make_packet(self.tmp, "packet folder",
                         {"scratchpad/packet-path.md": "the packet\n"})
        f = write_packet_file(wd, "packet.md",
                              "see `scratchpad/packet-paths.md` and `scratchpad/packet_path.md`"
                              " and `scratchpad/PACKET-PATH.md`\n")
        r = run_script(SCRIPT, ["--workdir", wd, "--file", f])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("missing (3)", r.stdout)

    def test_whitespace_inside_the_path_is_a_near_miss(self):
        # a stray space INSIDE the cited path changes the path — must not pass
        wd = make_packet(self.tmp, "packet folder",
                         {"scratchpad/packet-path.md": "the packet\n"})
        f = write_packet_file(wd, "packet.md", "see `scratchpad/ packet-path.md` now\n")
        r = run_script(SCRIPT, ["--workdir", wd, "--file", f])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)


class CitationCheckBrokenCopy(unittest.TestCase):
    def test_broken_copy_passes_where_it_must_fail(self):
        with open(SCRIPT, encoding="utf-8") as fh:
            src = fh.read()
        needle = "if not packet_exists(args.workdir, p):"
        self.assertIn(needle, src, "core check line changed; fix the broken-copy test")
        broken_src = src.replace(needle, "if False:")
        with tempfile.TemporaryDirectory() as tmp:
            broken = os.path.join(tmp, "citation_check.py")
            with open(broken, "w", encoding="utf-8") as fh:
                fh.write(broken_src)
            wd = make_packet(tmp, "packet folder", {})
            f = write_packet_file(wd, "packet.md", "see `scratchpad/gone.md`\n")
            good = run_script(SCRIPT, ["--workdir", wd, "--file", f])
            bad = run_script(broken, ["--workdir", wd, "--file", f])
        self.assertEqual(good.returncode, 1, good.stdout)
        self.assertEqual(bad.returncode, 0, bad.stdout)  # the break is visible


if __name__ == "__main__":
    unittest.main()
