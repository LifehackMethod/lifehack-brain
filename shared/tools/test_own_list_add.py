#!/usr/bin/env python3
"""test_own_list_add.py -- Run: python3 shared/tools/test_own_list_add.py (stdlib only; temp HOME, fictional names).
ALLOW cases first: things that must stay silent."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "own_list_add.py")


class OwnList(unittest.TestCase):
    def setUp(self):
        self.home = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, True)
        self.pc = os.path.join(self.home, "my-code")
        os.makedirs(os.path.join(self.pc, "bin"))
        os.makedirs(os.path.join(self.home, ".config", "lifehack"))
        open(os.path.join(self.home, ".config", "lifehack", "personal-code"), "w", encoding="utf-8").write(self.pc + "\n")

    def mk(self, rel, text="echo hi\n"):
        p = os.path.join(self.pc, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(text)
        return p

    def run_t(self, *a, home=None):
        r = subprocess.run([sys.executable, TOOL, *a], env=dict(os.environ, HOME=home or self.home), capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr

    # ---- ALLOW (silent) ----
    def test_non_tool_files_silent(self):
        ps = [self.mk("notes.md"), self.mk("tests/test_x.py"), self.mk("bin/test_y.sh"), self.mk("data.json"),
              self.mk("_retired-old/z.py"), self.mk("archive/z.sh"), self.mk(".hidden/z.py")]
        self.assertEqual(self.run_t("--check", *ps)[1], "")

    def test_outside_personal_folder_silent(self):
        other = os.path.join(self.home, "elsewhere.py"); open(other, "w", encoding="utf-8").write("x=1\n")
        self.assertEqual(self.run_t("--check", other)[1], "")

    def test_listed_tool_silent(self):
        p = self.mk("bin/ping-me.py")
        self.run_t(p)
        self.assertEqual(self.run_t("--check", p)[1], "")

    def test_no_personal_folder_silent(self):
        bare = os.path.realpath(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, bare, True)
        self.assertEqual(self.run_t("--check", os.path.join(bare, "a.py"), home=bare)[1], "")

    def test_list_file_itself_silent(self):
        p = self.mk("register.jsonl", "")
        self.assertEqual(self.run_t("--check", p)[1], "")

    # ---- FLAG ----
    def test_unlisted_tool_flagged_with_exact_command(self):
        p = self.mk("bin/ping-me.py")
        out = self.run_t("--check", p)[1]
        self.assertIn("not in your own list", out)
        self.assertIn('python3 "%s" "%s"' % (TOOL, p), out)

    def test_skill_flagged(self):
        p = self.mk("skills/tidy/SKILL.md", "---\nname: tidy\n---\n")
        self.assertIn("not in your own list", self.run_t("--check", p)[1])

    # ---- ADD ----
    def test_add_writes_register_row_and_is_idempotent(self):
        p = self.mk("bin/ping-me.py")
        self.assertEqual(self.run_t(p)[0], 0)
        self.assertIn("already listed", self.run_t(p)[1])
        rows = [json.loads(l) for l in open(os.path.join(self.pc, "register.jsonl"), encoding="utf-8")]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["type"], rows[0]["path"]), ("tool", "/bin/ping-me.py"))

    def test_add_refuses_file_outside_folder(self):
        other = os.path.join(self.home, "elsewhere.py"); open(other, "w", encoding="utf-8").write("x=1\n")
        rc, _, err = self.run_t(other)
        self.assertEqual(rc, 1); self.assertIn("not a file inside", err)
        self.assertFalse(os.path.exists(os.path.join(self.pc, "register.jsonl")))

    def test_add_with_no_folder_says_how_to_fix(self):
        bare = os.path.realpath(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, bare, True)
        rc, _, err = self.run_t(os.path.join(bare, "a.py"), home=bare)
        self.assertEqual(rc, 1); self.assertIn("bootstrap", err)


if __name__ == "__main__":
    unittest.main()
