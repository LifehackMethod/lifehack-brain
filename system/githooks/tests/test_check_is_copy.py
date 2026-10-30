#!/usr/bin/env python3
"""Tests for system/githooks/checks/is_copy.py in a throwaway scratch repo (never the real one)."""
import json, os, shutil, subprocess, sys, tempfile, unittest

CODE = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
CHECK = os.path.join(CODE, "system", "githooks", "checks", "is_copy.py")


def sh(cwd, *a):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True)


class T(unittest.TestCase):
    def setUp(self):
        self.r = tempfile.mkdtemp(prefix="chk3-")
        for rel in ("shared/notify/notify-send.sh", "shared/paths.py", "system/sops/hook-sop.md"):
            os.makedirs(os.path.dirname(os.path.join(self.r, rel)), exist_ok=True)
            shutil.copy(os.path.join(CODE, rel), os.path.join(self.r, rel))
        os.makedirs(os.path.join(self.r, "system/register"))
        with open(os.path.join(self.r, "system/register/register.jsonl"), "w", encoding="utf-8") as f:
            for p in ("/shared/notify/notify-send.sh", "/shared/paths.py"):
                f.write(json.dumps({"type": "tool", "path": p}) + "\n")
        sh(self.r, "git", "init", "-q")
        sh(self.r, "git", "config", "user.email", "t@t")
        sh(self.r, "git", "config", "user.name", "t")
        sh(self.r, "git", "add", "-A")
        sh(self.r, "git", "commit", "-qm", "base")

    def tearDown(self):
        shutil.rmtree(self.r, ignore_errors=True)

    def put(self, rel, text):
        p = os.path.join(self.r, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(text)
        sh(self.r, "git", "add", rel)

    def run_check(self):
        return sh(self.r, sys.executable, CHECK)

    def refused(self, rel, shared):
        p = self.run_check()
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertIn("is_copy: REFUSED %s: copy of %s — use it, don't copy it" % (rel, shared), p.stderr)
        fl = [l for l in p.stderr.splitlines() if l.startswith("FINDING ")]
        self.assertEqual(json.loads(fl[0][8:])["check"], "is_copy")

    def test_copy_of_shared_tool(self):
        src = open(os.path.join(CODE, "shared/notify/notify-send.sh"), encoding="utf-8").read()
        self.put("desks/x/tools/notify-send.sh", src)
        self.refused("desks/x/tools/notify-send.sh", "/shared/notify/notify-send.sh")

    def test_renamed_copy(self):
        src = open(os.path.join(CODE, "shared/notify/notify-send.sh"), encoding="utf-8").read()
        self.put("desks/x/tools/pinger.sh", src)
        self.refused("desks/x/tools/pinger.sh", "/shared/notify/notify-send.sh")

    def test_wrapper_passes(self):
        self.put("desks/x/tools/notify-send.sh", '#!/bin/sh\n# wraps-shared:\nexec bash "$(cat ~/.config/lifehack/code-root)/shared/notify/notify-send.sh" "$@"\n')
        self.assertEqual(self.run_check().returncode, 0)

    def test_near_duplicate_sop(self):
        t = open(os.path.join(CODE, "system/sops/hook-sop.md"), encoding="utf-8").read().splitlines()
        t[3] = "changed line"
        self.put("system/sops/hook-sop-v2.md", "\n".join(t) + "\n")
        self.refused("system/sops/hook-sop-v2.md", "system/sops/hook-sop.md")

    def test_same_name_sop_elsewhere(self):
        self.put("desks/x/hook-sop.md", "# my own\nshort\n")
        self.refused("desks/x/hook-sop.md", "system/sops/hook-sop.md")

    def test_new_sop_passes(self):
        self.put("system/sops/gardening-sop.md", "".join("Unique rule %d about gardening.\n" % i for i in range(30)))
        self.assertEqual(self.run_check().returncode, 0)

    def test_generic_name_different_content_passes(self):
        self.put("desks/x/paths.py", "".join("x%d = %d\n" % (i, i) for i in range(20)))
        self.assertEqual(self.run_check().returncode, 0)

    def test_retired_dir_exempt(self):
        src = open(os.path.join(CODE, "shared/notify/notify-send.sh"), encoding="utf-8").read()
        self.put("desks/x/_retired-old/notify-send.sh", src)
        self.assertEqual(self.run_check().returncode, 0)

    def test_modified_existing_passes(self):
        with open(os.path.join(self.r, "shared/notify/notify-send.sh"), "a", encoding="utf-8") as f:
            f.write("# edit\n")
        sh(self.r, "git", "add", "-A")
        self.assertEqual(self.run_check().returncode, 0)

    def test_files_mode_new_sop_not_a_copy_of_itself(self):
        # practice-round bug: in --files mode a NEW file in system/sops was compared with itself and refused
        f = os.path.join(CODE, "system", "sops", "zz-unit-test-only-sop.md")
        try:
            open(f, "w", encoding="utf-8").write("# a brand new rulebook\nkeep calm\n")
            p = subprocess.run([sys.executable, CHECK, "--files", f], cwd=CODE, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
        finally:
            os.path.exists(f) and os.remove(f)

    def test_real_repo_nothing_staged(self):
        p = subprocess.run([sys.executable, CHECK], cwd=CODE, capture_output=True, text=True)
        if sh(CODE, "git", "diff", "--cached", "--quiet").returncode == 0:
            self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
