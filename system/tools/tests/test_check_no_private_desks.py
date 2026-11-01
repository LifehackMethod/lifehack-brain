#!/usr/bin/env python3
"""test_check_no_private_desks.py — the no-personal-desk / no-private-repo check (3b.7 B).

Run: python3 system/tools/tests/test_check_no_private_desks.py   (stdlib unittest; also run by run-all-tests.sh and CI)

Proves: the real plugin tree is CLEAN; a planted mention FAILS (zero-tolerance surface, ratchet, the public names'
desk-material rule, the private handle); findings are printed REDACTED. The real names are never written in this
file: the generic cases plant a throwaway word through LIFEHACK_PRIVATE_DESK_NAMES, and the real-name cases read the
names from the maintainer's own personal code folder when it exists (desks/<name>/ folders, the origin remote's
owner) and are skipped elsewhere (a student machine, CI)."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CHECK = os.path.join(ROOT, "system", "tools", "check_no_private_desks.py")
sys.path.insert(0, os.path.join(ROOT, "system", "tools"))
sys.path.insert(0, os.path.join(ROOT, "shared"))
import check_no_private_desks as cnd  # noqa: E402

PLANT = "zzplantdesk"


def run(root, extra=None):
    env = dict(os.environ)
    env.pop("LIFEHACK_PRIVATE_DESK_NAMES", None)
    if extra:
        env["LIFEHACK_PRIVATE_DESK_NAMES"] = extra
    r = subprocess.run([sys.executable, CHECK, "--root", root], env=env, capture_output=True, text=True)
    return r.returncode, r.stdout


def personal_root():
    try:
        import personal_code_root
        src, p = personal_code_root.resolve_personal_code_root()
        return p if src in ("pointer", "default") else None
    except Exception:
        return None


class Fixture(unittest.TestCase):
    def setUp(self):
        self.d = os.path.realpath(tempfile.mkdtemp(prefix="cnd-test."))
        self.addCleanup(shutil.rmtree, self.d, True)
        subprocess.run(["git", "init", "-q", self.d], check=True)
        self.write("system/jobs.md", "```jobs\nsome-job | off | 3600 | o | c | none | 0 | none | bash x.sh\n```\n")
        self.write("docs/note.md", "An ordinary note about cal and sentinel, the product's own planning and security names.\n")

    def write(self, rel, text):
        p = os.path.join(self.d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        subprocess.run(["git", "-C", self.d, "add", rel], check=True)

    def test_clean_fixture_passes(self):
        rc, out = run(self.d, PLANT)
        self.assertEqual(rc, 0, out)

    def test_planted_name_on_zero_surface_fails_redacted(self):
        self.write("system/jobs.md", "```jobs\n%s-health | off | 3600 | o | c | none | 0 | none | bash x.sh\n```\n" % PLANT)
        rc, out = run(self.d, PLANT)
        self.assertEqual(rc, 1, out)
        self.assertIn("system/jobs.md:2: R2", out)
        self.assertNotIn(PLANT, out)   # never echoed

    def test_ratchet_allows_baseline_and_refuses_a_new_mention(self):
        self.write("docs/old.md", "%s and %s\n" % (PLANT, PLANT))
        self.write(cnd.BASELINE_REL, "2\tdocs/old.md\n")
        self.assertEqual(run(self.d, PLANT)[0], 0)
        self.write("docs/old.md", "%s and %s and %s\n" % (PLANT, PLANT, PLANT))
        rc, out = run(self.d, PLANT)
        self.assertEqual(rc, 1, out)
        self.assertIn("docs/old.md: R3 holds 3", out)
        self.write("docs/new.md", "%s\n" % PLANT)   # a file not in the baseline may hold none
        rc, out = run(self.d, PLANT)
        self.assertIn("docs/new.md: R3 holds 1", out)

    def test_public_names_as_desk_material_on_zero_surface_fail(self):
        self.write("system/jobs.md", "```jobs\ncal-billing | off | 3600 | o | c | none | 0 | none | bash \"$HOME/desks/cal/tools/x.sh\"\n```\n")
        rc, out = run(self.d)
        self.assertEqual(rc, 1, out)
        self.assertIn("R4", out)

    def test_public_desk_path_outside_zero_surface_is_fine(self):
        self.write("docs/planning.md", "The planning skill writes desks/cal/records/ and the sentinel agent reads.\n")
        self.assertEqual(run(self.d)[0], 0)

    def test_hash_tables_shape(self):
        self.assertEqual(len(cnd.DESK_HASHES), 7)
        self.assertEqual(len(cnd.HANDLE_HASHES), 1)

    def test_not_a_git_checkout_cannot_evaluate(self):
        d = os.path.realpath(tempfile.mkdtemp(prefix="cnd-nogit."))
        self.addCleanup(shutil.rmtree, d, True)
        self.assertEqual(run(d)[0], 2)


class RealNames(unittest.TestCase):
    """Only where the maintainer's personal code folder exists; elsewhere skipped (nothing to read the names from)."""

    def setUp(self):
        self.pc = personal_root()
        if not self.pc:
            self.skipTest("no personal code folder on this machine")
        self.d = os.path.realpath(tempfile.mkdtemp(prefix="cnd-real."))
        self.addCleanup(shutil.rmtree, self.d, True)
        subprocess.run(["git", "init", "-q", self.d], check=True)

    def plant(self, rel, text):
        p = os.path.join(self.d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(text)
        subprocess.run(["git", "-C", self.d, "add", rel], check=True)

    def test_each_real_desk_name_is_caught(self):
        desks = os.path.join(self.pc, "desks")
        names = [n for n in (os.listdir(desks) if os.path.isdir(desks) else []) if cnd.word_hash(n) in cnd.DESK_HASHES]
        if not names:
            self.skipTest("no desk folder in the personal code folder matches the hash table")
        for n in names:
            self.plant("system/job-names.txt", "%s-thing = a thing\n" % n)
            rc, out = run(self.d)
            self.assertEqual(rc, 1, (n, out))
            self.assertNotIn(n, out)

    def test_real_private_handle_is_caught_anywhere(self):
        r = subprocess.run(["git", "-C", self.pc, "remote", "get-url", "origin"], capture_output=True, text=True)
        m = re.search(r"github\.com[:/]([^/]+)/", r.stdout)
        if r.returncode != 0 or not m or cnd.word_hash(m.group(1)) not in cnd.HANDLE_HASHES:
            self.skipTest("the personal code folder's origin owner is not the hashed handle")
        self.plant("docs/any.md", "see %s/whatever\n" % m.group(1))
        rc, out = run(self.d)
        self.assertEqual(rc, 1, out)
        self.assertIn("R1", out)
        self.assertNotIn(m.group(1), out)


class RealTree(unittest.TestCase):
    def test_the_plugin_tree_is_clean(self):
        rc, out = run(ROOT)
        self.assertEqual(rc, 0, out)

    def test_a_planted_mention_in_a_copy_of_the_tree_fails(self):
        d = os.path.realpath(tempfile.mkdtemp(prefix="cnd-tree."))
        self.addCleanup(shutil.rmtree, d, True)
        r = subprocess.run(["git", "clone", "-q", "--shared", ROOT, d + "/c"], capture_output=True, text=True)
        if r.returncode != 0:
            self.skipTest("could not clone the tree: " + r.stderr.strip())
        p = os.path.join(d, "c", "system", "jobs.md")
        with open(p, "a", encoding="utf-8") as f:
            f.write("\n# planted: %s-health\n" % PLANT)
        rc, out = run(d + "/c", PLANT)
        self.assertEqual(rc, 1, out)
        self.assertIn("system/jobs.md", out)


if __name__ == "__main__":
    unittest.main()
