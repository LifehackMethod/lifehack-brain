import os, subprocess, sys, tempfile, unittest
CHK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "checks", "connected.py")
GOOD = "run by hand for the monthly audit; the cadence job is a later step"


def sh(cwd, *a):
    subprocess.run(a, cwd=cwd, check=True, capture_output=True)


class T(unittest.TestCase):
    """Round C 3: `# not-wired-yet:` needs a real reason when allow_silence_reason is ON; OFF = today. Fictional fixtures."""
    def run_with(self, reason, sw):
        d = tempfile.mkdtemp(prefix="chk1r-")
        sh(d, "git", "init", "-q"); sh(d, "git", "config", "user.email", "t@t"); sh(d, "git", "config", "user.name", "t")
        open(os.path.join(d, "README.md"), "w", encoding="utf-8").write("x\n"); sh(d, "git", "add", "-A"); sh(d, "git", "commit", "-qm", "i")
        os.makedirs(os.path.join(d, "system/tools"))
        open(os.path.join(d, "system/tools/widget_orphan.sh"), "w", encoding="utf-8").write("#!/bin/bash\n# not-wired-yet: %s\necho hi\n" % reason)
        sh(d, "git", "add", "-A")
        r = subprocess.run([sys.executable, CHK, d], capture_output=True, text=True, env=dict(os.environ, ROUNDB_ALLOW_SILENCE_REASON=sw))
        return r.returncode, r.stdout

    def test_off_any_reason_passes(self):
        for r in ("rig", "todo", GOOD):
            self.assertEqual(self.run_with(r, "off")[0], 0, r)

    def test_on_junk_refused(self):
        for r in ("rig", "todo", "later", "fine ok"):
            rc, out = self.run_with(r, "on")
            self.assertEqual(rc, 1, r); self.assertIn("not-wired-yet reason is", out)

    def test_on_real_passes(self):
        rc, out = self.run_with(GOOD, "on")
        self.assertEqual(rc, 0); self.assertIn("allowed", out)


if __name__ == "__main__":
    unittest.main()
