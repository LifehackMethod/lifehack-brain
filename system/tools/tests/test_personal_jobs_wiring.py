#!/usr/bin/env python3
"""test_personal_jobs_wiring.py -- the personal-jobs scaffold is wired into bootstrap.py and install-schedulers.sh.
Run: python3 system/tools/tests/test_personal_jobs_wiring.py   (stdlib only; throwaway HOME, plan-only, no --install)."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BOOTSTRAP = os.path.join(ROOT, "system", "tools", "bootstrap.py")
INSTALL = os.path.join(ROOT, "system", "tools", "install-schedulers.sh")
EXPECT = ["jobs.md", "job-fetch-hosts.txt", "vendor-read-allowlist.txt", "job-sim/README.txt", "tools", "JOBS-README.txt"]


def snapshot(root):
    out = {}
    for d, dirs, files in os.walk(root):
        for n in dirs + files:
            p = os.path.join(d, n)
            data = None
            if os.path.isfile(p):
                with open(p, "rb") as f:
                    data = f.read()
            out[os.path.relpath(p, root)] = (data, os.stat(p).st_mtime_ns)
    return out


class Wiring(unittest.TestCase):
    def setUp(self):
        self.home = os.path.realpath(tempfile.mkdtemp(prefix="wiring."))
        self.addCleanup(shutil.rmtree, self.home, True)
        self.la = os.path.join(self.home, "LaunchAgents")
        os.makedirs(self.la)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("LIFEHACK_")}
        self.env.update(HOME=self.home, LAUNCHAGENTS_DIR=self.la)
        self.pc = os.path.join(self.home, "lifehack-personal-code")

    def test_bootstrap_creates_scaffold(self):
        notes = os.path.join(self.home, "notes")
        os.makedirs(notes)
        r = subprocess.run([sys.executable, BOOTSTRAP, "--root", notes],
                           env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for rel in EXPECT:
            self.assertTrue(os.path.lexists(os.path.join(self.pc, rel)), rel)
            self.assertIn("personal jobs: created %s" % rel, r.stdout)
        self.assertNotIn("WARNING", r.stdout)

    def run_plan(self):
        return subprocess.run(["bash", INSTALL], env=self.env, capture_output=True, text=True)

    def test_plan_path_scaffolds_then_idempotent(self):
        os.makedirs(self.pc)
        r = self.run_plan()
        self.assertIn("plan only", r.stdout, r.stdout + r.stderr)
        for rel in EXPECT:
            self.assertTrue(os.path.lexists(os.path.join(self.pc, rel)), rel)
            self.assertIn("personal jobs created: %s" % rel, r.stdout)
        self.assertEqual(os.listdir(self.la), [])
        before = snapshot(self.pc)
        r2 = self.run_plan()
        self.assertEqual(snapshot(self.pc), before)
        self.assertNotIn("personal jobs created", r2.stdout)

    def test_plan_path_never_creates_the_folder(self):
        self.run_plan()
        self.assertFalse(os.path.exists(self.pc))

    def test_check_row_is_read_only(self):
        os.makedirs(self.pc)
        subprocess.run(["bash", INSTALL, "--check-row", "email-summary-write"], env=self.env, capture_output=True, text=True)
        self.assertEqual(os.listdir(self.pc), [])


if __name__ == "__main__":
    unittest.main()
