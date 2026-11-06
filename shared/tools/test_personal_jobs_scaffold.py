#!/usr/bin/env python3
"""test_personal_jobs_scaffold.py -- Run: python3 shared/tools/test_personal_jobs_scaffold.py (stdlib only; throwaway HOME)."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "personal_jobs_scaffold.py")
MANIFEST = os.path.join(HERE, "..", "jobs_manifest.py")
EXPECT = ["jobs.md", "job-fetch-hosts.txt", "vendor-read-allowlist.txt", "job-sim/README.txt", "tools", "JOBS-README.txt"]


def snapshot(root):
    out = {}
    for d, dirs, files in os.walk(root):
        for n in dirs + files:
            p = os.path.join(d, n)
            out[os.path.relpath(p, root)] = (open(p, "rb").read() if os.path.isfile(p) else None, os.stat(p).st_mtime_ns)
    return out


class Scaffold(unittest.TestCase):
    def setUp(self):
        self.home = os.path.realpath(tempfile.mkdtemp(prefix="scaffold."))
        self.addCleanup(shutil.rmtree, self.home, True)
        self.pc = os.path.join(self.home, "pc")
        os.makedirs(self.pc)
        self.env = dict(os.environ, HOME=self.home)

    def run_t(self, *a):
        r = subprocess.run([sys.executable, TOOL, *a], env=self.env, capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr

    def test_creates_everything(self):
        rc, out, _ = self.run_t(self.pc)
        self.assertEqual(rc, 0)
        for rel in EXPECT:
            self.assertTrue(os.path.lexists(os.path.join(self.pc, rel)), rel)
            self.assertIn("created: %s" % rel, out)
        self.assertTrue(os.path.isdir(os.path.join(self.pc, "tools")))
        self.assertNotIn("skipped", out)

    def test_second_run_changes_nothing(self):
        self.run_t(self.pc)
        before = snapshot(self.pc)
        rc, out, _ = self.run_t(self.pc)
        self.assertEqual(rc, 0)
        self.assertEqual(snapshot(self.pc), before)
        self.assertNotIn("created", out)
        for rel in EXPECT:
            self.assertIn("skipped (already there): %s" % rel, out)

    def test_existing_file_never_touched(self):
        for rel, text in (("jobs.md", "MINE jobs\n"), ("job-fetch-hosts.txt", "mine.example.org\n"), ("vendor-read-allowlist.txt", "")):
            open(os.path.join(self.pc, rel), "w", encoding="utf-8").write(text)
        before = {r: snapshot(self.pc)[r] for r in ("jobs.md", "job-fetch-hosts.txt", "vendor-read-allowlist.txt")}
        rc, out, _ = self.run_t(self.pc)
        self.assertEqual(rc, 0)
        after = snapshot(self.pc)
        for r, v in before.items():
            self.assertEqual(after[r], v, r)
            self.assertIn("skipped (already there): %s" % r, out)
        self.assertIn("created: JOBS-README.txt", out)

    def test_template_is_a_valid_empty_personal_table(self):
        self.run_t(self.pc)
        os.makedirs(os.path.join(self.home, ".config", "lifehack"))
        open(os.path.join(self.home, ".config", "lifehack", "personal-code"), "w", encoding="utf-8").write(self.pc + "\n")
        r = subprocess.run([sys.executable, MANIFEST, "--personal"], env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_no_folder_is_an_error_and_creates_nothing(self):
        gone = os.path.join(self.home, "nope")
        rc, _, err = self.run_t(gone)
        self.assertEqual(rc, 1)
        self.assertIn("NO-FOLDER", err)
        self.assertFalse(os.path.exists(gone))

    def test_default_folder_from_resolver(self):
        os.makedirs(os.path.join(self.home, "lifehack-personal-code"))
        rc, out, _ = self.run_t()
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(os.path.join(self.home, "lifehack-personal-code", "jobs.md")))

    def test_templates_name_no_person(self):
        self.run_t(self.pc)
        text = "".join(open(os.path.join(self.pc, r), encoding="utf-8").read() for r in EXPECT if r != "tools")
        self.assertNotIn(self.home, text)


if __name__ == "__main__":
    unittest.main()
