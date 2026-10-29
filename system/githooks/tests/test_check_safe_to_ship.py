import os, subprocess, sys, tempfile, unittest
CHK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "checks", "safe_to_ship.py")


def sh(cwd, *a):
    subprocess.run(a, cwd=cwd, check=True, capture_output=True)


class T(unittest.TestCase):
    def repo(self):
        d = tempfile.mkdtemp(prefix="chk4-")
        sh(d, "git", "init", "-q")
        sh(d, "git", "config", "user.email", "t@t"); sh(d, "git", "config", "user.name", "t")
        self.w(d, "README.md", "x\n"); sh(d, "git", "add", "-A"); sh(d, "git", "commit", "-qm", "i")
        return d

    def w(self, d, rel, text, mode=None):
        p = os.path.join(d, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(text)
        if mode:
            os.chmod(p, mode)

    def run_chk(self, d):
        sh(d, "git", "add", "-A")
        r = subprocess.run([sys.executable, CHK, d], capture_output=True, text=True)
        print(r.stdout.strip()); return r.returncode, r.stdout, r.stderr

    def test_a_private_worksheet_refused(self):
        d = self.repo()
        # fixture strings are assembled from fragments so this test file itself stays clean of the patterns
        U, AT, HTTPS = "/Us" + "ers/", "@" + "gmail.com", "https" + "://"
        self.w(d, "system/sops/worksheet.md",
               "notes\nsee " + U + "jdoe/work/x\nand " + U + "x/Library/CloudStor" + "age/GoogleDrive-jdoe" + AT + "/My Drive/a\n"
               "mail bob.smith" + AT + "\nrepo " + HTTPS + "github.com/someone/Claude" + "Ops\n"
               + HTTPS + "claude.ai/co" + "de/sess" + "ion_01AbCdEfGh\n")
        rc, out, err = self.run_chk(d)
        self.assertEqual(rc, 1)
        for rule in ("home-path-generic", "operator-drive-account", "email-address-generic",
                     "private-repo-name", "session-url"):
            self.assertIn("[%s]" % rule, out)
        self.assertIn("system/sops/worksheet.md:2", out)
        self.assertIn('"check": "safe_to_ship"', err)

    def test_b_exec_bit(self):
        d = self.repo()
        self.w(d, "system/hooks/guard_x.sh", "#!/bin/bash\nexit 0\n", 0o644)
        rc, out, err = self.run_chk(d)
        self.assertEqual(rc, 1); self.assertIn("exec-bit-missing", out)
        self.assertIn("git update-index --chmod=+x system/hooks/guard_x.sh", out)
        os.chmod(os.path.join(d, "system/hooks/guard_x.sh"), 0o755)
        rc, out, err = self.run_chk(d)
        self.assertEqual(rc, 0)

    def test_c_fakeroot_fixture_passes(self):
        d = self.repo()
        self.w(d, "system/hooks/tests/t.sh", 'LB="$(mktemp -d)"\nmkdir -p "$LB/fakeroot/.claude"\nmail you@example.com\n')
        self.assertEqual(self.run_chk(d)[0], 0)

    def test_d_clean_doc_passes(self):
        d = self.repo()
        self.w(d, "docs/clean.md", "# Hello\nA plain doc. Use ~/notes and $HOME.\n")
        self.assertEqual(self.run_chk(d)[0], 0)

    def test_e_nothing_staged_passes(self):
        self.assertEqual(self.run_chk(self.repo())[0], 0)


if __name__ == "__main__":
    unittest.main()
