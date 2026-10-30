#!/usr/bin/env python3
"""test_personal_code_root.py — Run: python3 shared/test_personal_code_root.py (stdlib unittest only).
Every case runs the real CLI under a temp HOME, so the developer's own ~/.config is never touched."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "personal_code_root.py")


class PersonalCodeRootCase(unittest.TestCase):
    def setUp(self):
        self.home = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, True)

    def run_cli(self, *args):
        env = dict(os.environ, HOME=self.home)
        p = subprocess.run([sys.executable, SCRIPT, *args], env=env, capture_output=True, text=True)
        return p.returncode, p.stdout.strip()

    def write_pointer(self, value):
        d = os.path.join(self.home, ".config", "lifehack")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "personal-code"), "w", encoding="utf-8") as f:
            f.write(value + "\n")

    def test_no_pointer_no_default_is_not_set(self):
        rc, out = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertTrue(out.startswith("NOT-SET"))

    def test_no_pointer_falls_back_to_default_folder(self):
        os.makedirs(os.path.join(self.home, "lifehack-personal-code"))
        rc, out = self.run_cli("--quiet")
        self.assertEqual((rc, out), (0, os.path.join(self.home, "lifehack-personal-code")))

    def test_pointer_present(self):
        target = os.path.join(self.home, "elsewhere")
        os.makedirs(target)
        os.makedirs(os.path.join(self.home, "lifehack-personal-code"))  # pointer must win over default
        self.write_pointer(target)
        rc, out = self.run_cli()
        self.assertEqual(rc, 0)
        self.assertIn("(source: pointer)", out)
        self.assertIn(target, out)

    def test_pointer_present_folder_missing_never_falls_back(self):
        os.makedirs(os.path.join(self.home, "lifehack-personal-code"))  # a default exists, still must not be used
        self.write_pointer(os.path.join(self.home, "gone"))
        rc, out = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertTrue(out.startswith("POINTER-MISSING"))
        rc, out = self.run_cli("--quiet")
        self.assertEqual((rc, out), (1, ""))


if __name__ == "__main__":
    unittest.main()
