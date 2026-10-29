#!/usr/bin/env python3
"""test_toolbox.py -- v2 step 2.2: toolbox.py generates the toolbox list from the register.

Run directly:  python3 system/register/tests/test_toolbox.py
"""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTER_DIR = os.path.dirname(HERE)
sys.path.insert(0, REGISTER_DIR)
import toolbox  # noqa: E402


def row(path, typ="tool", **kw):
    r = {"id": f"{typ}:public:{path}", "type": typ, "repo": "public", "path": path, "exists": True}
    r.update(kw)
    return r


class Purpose(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def w(self, name, text):
        p = os.path.join(self.d, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p

    def test_py_docstring_first_sentence(self):
        p = self.w("a.py", '"""a.py — does the thing, with plenty of enough words in it. Then more detail follows.\n\nBody."""\n')
        self.assertEqual(toolbox.purpose_of(p), "does the thing, with plenty of enough words in it")

    def test_sh_comment_name_dash(self):
        p = self.w("b.sh", "#!/usr/bin/env bash\n# b.sh -- watches a folder\n# second line\n\necho hi\n")
        self.assertEqual(toolbox.purpose_of(p), "watches a folder second line")

    def test_what_label_fallback(self):
        p = self.w("c.sh", "#!/bin/bash\n# ── LLM CONTEXT ──\n# WHY: because.\n# WHAT: sends the\n#       thing out.\n")
        self.assertEqual(toolbox.purpose_of(p), "sends the thing out")

    def test_no_header(self):
        p = self.w("d.sh", "echo hi\n")
        self.assertIn("no header", toolbox.purpose_of(p))

    def test_long_is_capped(self):
        p = self.w("e.py", '"""e — ' + "word " * 80 + '"""\n')
        self.assertLessEqual(len(toolbox.purpose_of(p)), toolbox.MAX_PURPOSE)


class Generate(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        for rel, hdr in {
            "shared/notify/n.sh": "# n.sh — pushes\n",
            "shared/tools/email_x.py": '"""email_x — mail thing."""\n',
            "shared/tools/store_y.py": '"""store_y — store thing."""\n',
            "system/tools/job-run.sh": "# job-run.sh — wrapper\n",
            "system/tools/other.py": '"""other — not shared."""\n',
        }.items():
            full = os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as fh:
                fh.write(hdr)
        self.rows = [row("/" + p) for p in ("shared/notify/n.sh", "shared/tools/email_x.py", "shared/tools/store_y.py",
                                             "system/tools/job-run.sh", "system/tools/other.py", "shared/tools/gone.py")]
        self.rows.append(row("/system/jobs.md", "scheduled", schedule_name="j1", interval_seconds=3600,
                             enabled="yes", command='bash "$X/system/tools/j1-run.sh"'))

    def test_scope_groups(self):
        t = toolbox.generate(self.root, self.rows)
        self.assertIn("## Notify\n\n- `/shared/notify/n.sh` · pushes", t)
        self.assertIn("## Email\n\n- `/shared/tools/email_x.py` · mail thing", t)
        self.assertIn("## Store and sync\n\n- `/shared/tools/store_y.py`", t)
        self.assertIn("## Job runner", t)
        self.assertNotIn("other.py", t)   # system/tools but not the runner/libs: not in the toolbox
        self.assertNotIn("gone.py", t)    # registered but missing on disk: not listed
        self.assertIn("- `j1` · every 1h · enabled: yes · runs `j1-run.sh`", t)

    def test_deterministic(self):
        self.assertEqual(toolbox.generate(self.root, self.rows),
                         toolbox.generate(self.root, list(reversed(self.rows))))


class RealRepo(unittest.TestCase):
    def test_committed_toolbox_is_current(self):
        r = subprocess.run([sys.executable, os.path.join(REGISTER_DIR, "toolbox.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_every_nontest_shared_file_is_listed(self):
        text = toolbox.generate()
        for dp, _, fs in os.walk(os.path.join(toolbox.ROOT, "shared")):
            for f in fs:
                if f.endswith((".py", ".sh")) and not f.startswith("test_") and "__pycache__" not in dp:
                    rel = "/" + os.path.relpath(os.path.join(dp, f), toolbox.ROOT)
                    self.assertIn(f"`{rel}`", text)

    def test_check_fails_when_stale(self):
        with open(toolbox.OUT, encoding="utf-8") as fh:
            cur = fh.read()
        try:
            with open(toolbox.OUT, "w", encoding="utf-8") as fh:
                fh.write(cur + "\nhand edit\n")
            self.assertEqual(toolbox.main(["--check"]), 1)
        finally:
            with open(toolbox.OUT, "w", encoding="utf-8") as fh:
                fh.write(cur)


if __name__ == "__main__":
    unittest.main()
