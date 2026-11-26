#!/usr/bin/env python3
"""Tests for inputs_check.py --requires (brief 2f, §6 test 6). stdlib unittest."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(TESTS_DIR)
SCRIPT = os.path.join(SCRIPTS_DIR, "inputs_check.py")


def run_script(argv):
    env = dict(os.environ)
    env["LIFEHACK_REPO_ROOT"] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(TESTS_DIR)))))
    env["PYTHONPATH"] = os.path.join(env["LIFEHACK_REPO_ROOT"], "shared") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, SCRIPT] + argv, capture_output=True, text=True, env=env, timeout=60)


class RequiresGateTest(unittest.TestCase):
    def setUp(self):
        self.wd = tempfile.mkdtemp(prefix="inputs-gate-")
        os.makedirs(os.path.join(self.wd, "scratchpad"), exist_ok=True)

    def _present(self, name):
        with open(os.path.join(self.wd, "scratchpad", name + ".md"), "w", encoding="utf-8") as f:
            f.write("done\n")

    def test_missing_requires_fails_with_the_waiting_line(self):
        p = run_script(["--workdir", self.wd, "--substep", "4.1a", "--requires", "spec-update-checked"])
        self.assertEqual(p.returncode, 1)
        self.assertIn("waiting: the spec update check (4.0a)", p.stdout)

    def test_present_requires_passes(self):
        self._present("spec-update-checked")
        self._present("steps-draft")
        self._present("packet-path")
        p = run_script(["--workdir", self.wd, "--substep", "4.1a", "--requires", "spec-update-checked"])
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("spec-update-checked", p.stdout)

    def test_other_required_sections_still_gate(self):
        self._present("spec-update-checked")   # the gate passes but steps-draft is still missing
        p = run_script(["--workdir", self.wd, "--substep", "4.1a", "--requires", "spec-update-checked"])
        self.assertEqual(p.returncode, 1)
        self.assertIn("steps-draft", p.stdout)

    def test_without_requires_flag_unchanged(self):
        self._present("steps-draft")
        self._present("packet-path")
        p = run_script(["--workdir", self.wd, "--substep", "4.1a"])
        self.assertEqual(p.returncode, 0, p.stdout)


if __name__ == "__main__":
    unittest.main()
