import os, subprocess, sys, tempfile, unittest
CHK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "checks", "connected.py")


def sh(cwd, *a):
    subprocess.run(a, cwd=cwd, check=True, capture_output=True)


class T(unittest.TestCase):
    def repo(self):
        d = tempfile.mkdtemp(prefix="chk1-")
        sh(d, "git", "init", "-q")
        sh(d, "git", "config", "user.email", "t@t"); sh(d, "git", "config", "user.name", "t")
        self.w(d, "README.md", "x\n"); sh(d, "git", "add", "-A"); sh(d, "git", "commit", "-qm", "i")
        return d

    def w(self, d, rel, text):
        p = os.path.join(d, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(text)

    def run_chk(self, d):
        sh(d, "git", "add", "-A")
        r = subprocess.run([sys.executable, CHK, d], capture_output=True, text=True)
        return r.returncode, r.stdout, r.stderr

    def test_a_unwired_tool_refused(self):
        d = self.repo(); self.w(d, "system/tools/orphan.sh", "echo hi\n")
        rc, out, err = self.run_chk(d)
        print(out.strip()); self.assertEqual(rc, 1)
        self.assertIn("connected: REFUSED system/tools/orphan.sh", out); self.assertIn('"decision": "deny"', err)

    def test_b_tool_with_caller(self):
        d = self.repo(); self.w(d, "system/tools/used.sh", "echo hi\n")
        self.w(d, "system/tools/runner.sh", "bash system/tools/used.sh\n# not-wired-yet: entry\n")
        self.assertEqual(self.run_chk(d)[0], 0)

    def test_b2_mention_only_not_a_call(self):
        d = self.repo(); self.w(d, "system/tools/used.sh", "echo hi\n")
        self.w(d, "docs.txt", "see used.sh sometime\n")
        self.assertEqual(self.run_chk(d)[0], 1)

    def test_c_hook(self):
        d = self.repo(); self.w(d, "system/hooks/h.sh", "exit 0\n")
        self.assertEqual(self.run_chk(d)[0], 1)
        self.w(d, "hooks/hooks.json", '{"hooks":{"PreToolUse":[{"command":"${CLAUDE_PLUGIN_ROOT}/system/hooks/h.sh"}]}}\n')
        self.assertEqual(self.run_chk(d)[0], 0)

    def test_d_not_wired_yet(self):
        d = self.repo(); self.w(d, "system/tools/later.py", "# not-wired-yet: waits for 3b\nprint(1)\n")
        rc, out, err = self.run_chk(d)
        self.assertEqual(rc, 0); self.assertIn('"decision": "warn"', err)

    def test_e_existing_modified(self):
        d = self.repo(); self.w(d, "system/tools/old.sh", "echo 1\n")
        sh(d, "git", "add", "-A"); sh(d, "git", "commit", "-qm", "old")
        self.w(d, "system/tools/old.sh", "echo 2\n")
        self.assertEqual(self.run_chk(d)[0], 0)

    def test_f_test_file(self):
        d = self.repo(); self.w(d, "system/tools/tests/test_x.py", "pass\n")
        self.assertEqual(self.run_chk(d)[0], 0)

    def test_lib_and_import(self):
        d = self.repo(); self.w(d, "system/tools/a.lib.sh", "x=1\n"); self.w(d, "shared/lib/m.py", "x=1\n")
        self.assertEqual(self.run_chk(d)[0], 1)
        self.w(d, "system/tools/use.sh", "source system/tools/a.lib.sh\n# not-wired-yet: x\n")
        self.w(d, "shared/use.py", "import m\n# not-wired-yet: x\n")
        self.assertEqual(self.run_chk(d)[0], 0)

    def test_skill(self):
        d = self.repo(); self.w(d, ".claude/skills/s/SKILL.md", "---\nname: s\ndescription: d\n---\nbody\n")
        self.assertEqual(self.run_chk(d)[0], 0)
        self.w(d, ".claude/skills/t/SKILL.md", "no frontmatter\n")
        self.assertEqual(self.run_chk(d)[0], 1)


if __name__ == "__main__":
    unittest.main()
