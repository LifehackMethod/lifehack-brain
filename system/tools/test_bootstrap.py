#!/usr/bin/env python3
"""test_bootstrap.py — day one makes exactly three things, and no fourth.

Run:  python3 system/tools/test_bootstrap.py

The "and nothing else" half is the one that needs teeth. It is easy and tempting for a later change to
have this scaffold a helpful starting structure; that would hand every person a guess about how their
own life divides up, which is the thing this system refuses to do everywhere else.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import bootstrap  # noqa: E402

EXPECTED = {"system/journal.md", "system/project-registry.md", "state/projects/"}


def tree(root):
    """Every path under root, relative, directories with a trailing slash."""
    out = set()
    for dirpath, dirnames, filenames in os.walk(root):
        for d in dirnames:
            out.add(os.path.relpath(os.path.join(dirpath, d), root) + "/")
        for f in filenames:
            out.add(os.path.relpath(os.path.join(dirpath, f), root))
    return out


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bootstrap-test-")
        self.root = os.path.join(self.tmp, "notes")
        os.makedirs(self.root)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestExactly(Case):

    def test_creates_the_three(self):
        created, existed = bootstrap.bootstrap(self.root)
        self.assertEqual(set(created), EXPECTED)
        self.assertEqual(existed, [])

    def test_and_nothing_else(self):
        """The load-bearing one. Whatever appears on disk is EXACTLY the three, plus the two parent
        directories they have to live in — no subject folders, no example note, no template."""
        bootstrap.bootstrap(self.root)
        self.assertEqual(tree(self.root), EXPECTED | {"system/", "state/"})

    def test_dry_run_touches_nothing(self):
        created, _ = bootstrap.bootstrap(self.root, dry_run=True)
        self.assertEqual(set(created), EXPECTED)
        self.assertEqual(tree(self.root), set(), "--dry-run wrote to disk")


class TestIdempotent(Case):

    def test_second_run_creates_nothing(self):
        bootstrap.bootstrap(self.root)
        created, existed = bootstrap.bootstrap(self.root)
        self.assertEqual(created, [])
        self.assertEqual(set(existed), EXPECTED)

    def test_never_clobbers_real_content(self):
        """Someone's journal with a year in it must survive a re-run. This is the one that would hurt."""
        bootstrap.bootstrap(self.root)
        j = os.path.join(self.root, "system", "journal.md")
        with open(j, "w", encoding="utf-8") as f:
            f.write("2026-08-11 — the thing I must not lose\n")
        bootstrap.bootstrap(self.root)
        with open(j, encoding="utf-8") as f:
            self.assertIn("must not lose", f.read())


class TestRefuses(Case):

    def test_refuses_a_root_that_is_not_there(self):
        root, reason = bootstrap.resolve_root(os.path.join(self.tmp, "nope"))
        self.assertIsNone(root)
        self.assertIn("not a directory", reason)

    def test_cli_refuses_with_no_root_set_and_teaches(self):
        env = dict(os.environ)
        env["HOME"] = os.path.join(self.tmp, "home")
        env.pop("LIFEHACK_ROOT", None)
        r = subprocess.run([sys.executable, os.path.join(HERE, "bootstrap.py")],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no data root set", r.stdout + r.stderr)
        self.assertIn("--set", r.stdout + r.stderr, "a refusal has to say how to fix it")

    def test_cli_runs_against_an_explicit_root(self):
        r = subprocess.run([sys.executable, os.path.join(HERE, "bootstrap.py"), "--root", self.root],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(tree(self.root), EXPECTED | {"system/", "state/"})


class TestSitsBesideIngest(Case):
    """The spine and the subject folders have to coexist — the spine goes above, /ingest builds below."""

    def test_a_scaffolded_subject_folder_lands_beside_the_spine(self):
        bootstrap.bootstrap(self.root)
        vocab = os.path.join(self.root, "memory", "topic-vocab.md")
        os.makedirs(os.path.dirname(vocab))
        with open(vocab, "w", encoding="utf-8") as f:
            f.write("# my subjects\n\n- `money`\n")
        r = subprocess.run([sys.executable,
                            os.path.join(REPO, "system", "tools", "cowork-ingest", "folder_scaffold.py"),
                            "--drive-root", self.root, "--path", "desks/money",
                            "--purpose", "what comes in and what goes out",
                            "--topic", "money", "--desk", "money", "--vocab", vocab],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        got = tree(self.root)
        for p in EXPECTED:
            self.assertIn(p, got, "the spine must survive a scaffold")
        self.assertIn("desks/money/canon/current.md", got)
        self.assertIn("desks/money/canon/purpose.md", got)


if __name__ == "__main__":
    unittest.main(verbosity=2)
