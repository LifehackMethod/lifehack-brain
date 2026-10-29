#!/usr/bin/env python3
"""test_toolbox_staged.py -- v2 step 2.2b: pre-commit regenerates toolbox.md from the STAGED register.

Runs the REAL pre-commit hook in a throwaway `git clone --no-hardlinks` (absolute core.hooksPath), with the
hook, refresh script, harvest.py and toolbox.py overlaid from this working tree.

Run directly:  python3 system/register/tests/test_toolbox_staged.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTER_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(REGISTER_DIR))
REG = "system/register/register.jsonl"
TB = "system/register/toolbox.md"
OVERLAY = ("system/githooks/pre-commit", "system/register/refresh_staged.py",
           "system/register/harvest.py", "system/register/toolbox.py",
           "system/githooks/report_checks.sh", "system/githooks/checks/connected.py",
           "system/githooks/checks/hides_failure.py", "system/githooks/checks/is_copy.py",
           "system/githooks/checks/safe_to_ship.py", "system/hooks/lib/journal.sh",
           "system/hooks/lib/build_mode.py", "system/tools/door_rules.py",
           ".github/scripts/check_no_internal_leakage.py", "system/hooks/placement.conf")
ENV = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null", "LHB_JOURNAL_DISABLE": "1",
       "LHB_PRECOMMIT_FINDINGS": "/dev/null"}
LINE = "pre-commit: regenerated toolbox.md"


def git(cwd, *args, **kw):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, env=ENV, **kw)


def py(cwd, *args):
    r = subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True, env=ENV)
    return r


class Staged(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp(prefix="toolbox-clone-")
        shutil.rmtree(d)
        r = subprocess.run(["git", "clone", "-q", "--no-hardlinks", REPO_ROOT, d], capture_output=True, text=True, env=ENV)
        assert r.returncode == 0, r.stderr
        self.d = d
        self.addCleanup(shutil.rmtree, d, True)
        for rel in OVERLAY:
            os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
        shutil.copy2(os.path.join(REPO_ROOT, rel), os.path.join(d, rel))
        git(d, "config", "user.email", "t@t")
        git(d, "config", "user.name", "t")
        git(d, "config", "core.hooksPath", os.path.join(d, "system", "githooks"))
        assert py(d, "system/register/harvest.py", "--no-cache", "--update-register", REG).returncode == 0
        assert py(d, "system/register/toolbox.py").returncode == 0
        git(d, "add", "-A")
        git(d, "commit", "-qm", "baseline", "--no-verify")

    def add_shared_tool(self, name="zz_new_tool.py"):
        p = os.path.join(self.d, "shared", name)
        with open(p, "w", encoding="utf-8") as f:
            f.write('"""%s -- frobnicates the widgets for the test, nothing else."""\n' % name[:-3])
        assert py(self.d, "system/register/harvest.py", "--no-cache", "--update-register", REG).returncode == 0
        git(self.d, "add", "shared/" + name, REG)
        return "shared/" + name

    def commit(self):
        r = git(self.d, "commit", "-qm", "t")
        return r.returncode, r.stdout + r.stderr

    def test_a_new_shared_tool_regenerates_in_same_commit(self):
        self.add_shared_tool()
        rc, out = self.commit()
        self.assertEqual(rc, 0, out)
        self.assertIn(LINE, out)
        head = git(self.d, "show", "HEAD:" + TB).stdout
        self.assertIn("`/shared/zz_new_tool.py` · frobnicates the widgets", head)
        with open(os.path.join(self.d, TB), encoding="utf-8") as f:
            self.assertEqual(f.read(), head)  # working copy synced
        self.assertEqual(git(self.d, "status", "--porcelain", "--", TB).stdout, "")
        self.assertEqual(py(self.d, "system/register/toolbox.py", "--check").returncode, 0)

    def test_b_nothing_relevant_staged_is_silent(self):
        p = os.path.join(self.d, "README-unrelated.txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write("x\n")
        git(self.d, "add", "README-unrelated.txt")
        before = git(self.d, "rev-parse", "HEAD:" + TB).stdout
        rc, out = self.commit()
        self.assertEqual(rc, 0, out)
        self.assertNotIn("toolbox", out)
        self.assertEqual(git(self.d, "rev-parse", "HEAD:" + TB).stdout, before)

    def test_c_corrupt_staged_register_refused(self):
        self.add_shared_tool()
        bad = os.path.join(self.d, REG)
        with open(bad, "a", encoding="utf-8") as f:
            f.write("{not json\n")
        git(self.d, "add", REG)
        rc, out = self.commit()
        self.assertNotEqual(rc, 0)
        # the toolbox step itself fails closed on a corrupt staged register (not only the refresh step)
        r = py(self.d, "system/register/toolbox.py", "--staged")
        self.assertEqual(r.returncode, 1)
        self.assertIn("corrupt", r.stderr)
        # a parseable-but-malformed row is refused too
        with open(bad, "a", encoding="utf-8") as f:
            f.write('{"id": "x", "type": "tool"}\n')
        git(self.d, "add", REG)
        # (truncate the bad JSON line first)
        with open(bad, encoding="utf-8") as f:
            lines = [l for l in f.read().splitlines() if l != "{not json"]
        with open(bad, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        git(self.d, "add", REG)
        self.assertEqual(py(self.d, "system/register/toolbox.py", "--staged").returncode, 1)

    def test_d_unrelated_unstaged_toolbox_edit_stays_out(self):
        self.add_shared_tool()
        tb = os.path.join(self.d, TB)
        with open(tb, "a", encoding="utf-8") as f:
            f.write("\nHAND EDIT\n")
        rc, out = self.commit()
        self.assertEqual(rc, 0, out)
        self.assertIn(LINE, out)
        self.assertNotIn("HAND EDIT", git(self.d, "show", "HEAD:" + TB).stdout)
        with open(tb, encoding="utf-8") as f:
            self.assertIn("HAND EDIT", f.read())  # still there, still unstaged

    def test_stdin_and_path_register(self):
        reg = os.path.join(self.d, REG)
        a = py(self.d, "system/register/toolbox.py", "--stdout", "--register", reg).stdout
        with open(reg, encoding="utf-8") as f:
            reg_text = f.read()
        r = subprocess.run([sys.executable, "system/register/toolbox.py", "--stdout", "--register", "-"],
                           cwd=self.d, input=reg_text, capture_output=True, text=True, env=ENV)
        self.assertEqual(a, r.stdout)


if __name__ == "__main__":
    unittest.main()
