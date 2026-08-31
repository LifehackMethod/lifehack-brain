#!/usr/bin/env python3
"""test_bootstrap.py — day one makes exactly four things, and no fifth.

Run:  python3 system/tools/test_bootstrap.py

The "and nothing else" half is the one that needs teeth. It is easy and tempting for a later change to
have this scaffold a helpful starting structure; that would hand every person a guess about how their
own life divides up, which is the thing this system refuses to do everywhere else. That includes the
root canon added 2026-08-11 (task 2.1.1): its FRAME ships empty, never pre-filled canon lines.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import bootstrap  # noqa: E402

EXPECTED = {"system/journal.md", "system/project-registry.md", "state/projects/", "canon.md"}


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


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

    def test_creates_the_four(self):
        created, existed = bootstrap.bootstrap(self.root)
        self.assertEqual(set(created), EXPECTED)
        self.assertEqual(existed, [])

    def test_and_nothing_else(self):
        """The load-bearing one. Whatever appears on disk is EXACTLY the four, plus the two parent
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


class TestRootCanon(Case):
    """task 2.1.1's own acceptance test: the root canon is created once, seeded with purpose only,
    and a second run leaves it byte-identical — proven by hash, not by inspection."""

    def test_root_canon_created_on_fresh_root(self):
        created, existed = bootstrap.bootstrap(self.root)
        self.assertIn("canon.md", created)
        self.assertEqual(existed, [])
        p = os.path.join(self.root, "canon.md")
        self.assertTrue(os.path.isfile(p))
        with open(p, encoding="utf-8") as f:
            body = f.read()
        # frame, not content: a purpose line, no numeric threshold, and no canon bullet yet.
        self.assertIn("intent", body.lower())
        self.assertNotRegex(body, r"\bno more than\b|\bmax(imum)?\s*\d|\d+\s*lines?\b",
                            "a numeric size threshold leaked into the seeded root canon")
        self.assertNotIn("\n- ", body, "a canon line was pre-filled — it must ship empty")

    def test_second_run_does_not_modify_root_canon(self):
        """The load-bearing check: hash before, hash after — not just 'still contains the phrase'."""
        bootstrap.bootstrap(self.root)
        p = os.path.join(self.root, "canon.md")
        before = sha256(p)
        created, existed = bootstrap.bootstrap(self.root)
        after = sha256(p)
        self.assertEqual(before, after, "a second run changed the root canon's bytes")
        self.assertNotIn("canon.md", created)
        self.assertIn("canon.md", existed)

    def test_second_run_does_not_modify_a_hand_edited_root_canon(self):
        """Mirrors test_never_clobbers_real_content above, for the fourth artifact specifically."""
        bootstrap.bootstrap(self.root)
        p = os.path.join(self.root, "canon.md")
        with open(p, "a", encoding="utf-8") as f:
            f.write("- the human's own line, added by hand\n")
        before = sha256(p)
        bootstrap.bootstrap(self.root)
        after = sha256(p)
        self.assertEqual(before, after)
        with open(p, encoding="utf-8") as f:
            self.assertIn("the human's own line", f.read())

    def test_existing_three_still_created_and_not_clobbered_alongside_the_fourth(self):
        """The fourth artifact must not have come at the cost of the first three."""
        created, existed = bootstrap.bootstrap(self.root)
        for rel in ("system/journal.md", "system/project-registry.md", "state/projects/"):
            self.assertIn(rel, created)
        j = os.path.join(self.root, "system", "journal.md")
        with open(j, "w", encoding="utf-8") as f:
            f.write("2026-08-11 — must not lose this either\n")
        before = sha256(j)
        bootstrap.bootstrap(self.root)
        after = sha256(j)
        self.assertEqual(before, after)


class TestRefuses(Case):

    def test_refuses_a_root_that_is_not_there(self):
        root, reason = bootstrap.resolve_root(os.path.join(self.tmp, "nope"))
        self.assertIsNone(root)
        self.assertIn("not a directory", reason)

    def test_cli_refuses_with_no_root_set_and_teaches(self):
        """Must sandbox against ALL FIVE resolution routes in brain_root.resolve_brain_root(), not
        just the persisted-config route (3). Route (2), the repo pointer, is read from bootstrap.py's
        OWN file location — independent of $HOME and every env var — so running this straight out of
        HERE (the real checkout) leaks a developer's real `.brain-root` (gitignored, so it survives
        untouched no matter what env is cleared) and the test can never observe NOT-SET on any machine
        that has ever run --set. Fix (2026-08-28): `git archive` a clean, pointer-free checkout —
        gitignored files are never tracked, so it has no `.brain-root`, and it has no `.git` at all,
        so route (2b), the main-worktree-pointer, cannot fire either — and run bootstrap.py from
        THERE instead of from the real repo. Verified as a test-isolation defect, not a product bug:
        the CLI does refuse (exit 1) in a genuinely rootless environment (repo-issue reproduced by hand
        against a `git archive` checkout before this fix, matching what this test now automates)."""
        clean_repo = os.path.join(self.tmp, "clean-repo")
        os.makedirs(clean_repo)
        archive = subprocess.run(["git", "archive", "HEAD"], cwd=REPO, capture_output=True, check=True)
        subprocess.run(["tar", "-x"], cwd=clean_repo, input=archive.stdout, check=True)
        self.assertFalse(os.path.exists(os.path.join(clean_repo, ".brain-root")),
                         "a clean checkout must not carry a pointer — if this fires, the isolation "
                         "this test relies on is itself broken")
        env = dict(os.environ)
        env["HOME"] = os.path.join(self.tmp, "home")
        env.pop("LIFEHACK_ROOT", None)
        env.pop("INGEST_LEGACY_ROOT_GLOB", None)
        r = subprocess.run([sys.executable, os.path.join(clean_repo, "system", "tools", "bootstrap.py")],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
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


class TestPython3ShimUTF8(unittest.TestCase):
    """T8.2a, 2026-08-13. `ensure_python3_shim` is Windows-only (`os.name != "nt"` short-circuits),
    so on macOS/Linux CI it has to be exercised by simulating Windows, not by actually being on it —
    the same honesty bound the task's own verification carries. Mocks `os.name` and `sys.executable`
    so the function believes it is Windows, pointed at a throwaway interpreter folder."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="shim-test-")
        self.fake_python = os.path.join(self.tmp, "python.exe")
        open(self.fake_python, "w").close()
        self.shim = os.path.join(self.tmp, "python3.cmd")
        self.shim_posix = os.path.join(self.tmp, "python3")
        self.patches = [
            mock.patch.object(bootstrap.os, "name", "nt"),
            mock.patch.object(bootstrap.sys, "executable", self.fake_python),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_not_windows_is_a_noop(self):
        for p in self.patches:
            p.stop()
        self.patches = []
        status, detail = bootstrap.ensure_python3_shim()
        self.assertEqual(status, "not-needed")

    def test_fresh_windows_machine_creates_a_shim_with_utf8(self):
        """A fresh install now writes TWO files: python3.cmd (cmd.exe) and an extensionless
        python3 (Git Bash, which execs a PATH entry by exact name and never resolves .cmd files).
        The .cmd content/contract is unchanged from before this fix; the POSIX companion is new
        and its own content is asserted directly -- not via a substring match loose enough to pass
        if it silently stopped being written."""
        with mock.patch.object(shutil, "which", return_value=None):
            status, detail = bootstrap.ensure_python3_shim()
        self.assertEqual(status, "created")

        # the .cmd shim: unchanged contract
        cmd_body = open(self.shim, encoding="ascii").read()
        self.assertIn("PYTHONUTF8=1", cmd_body)
        self.assertIn("python.exe", cmd_body)

        # the POSIX companion: must exist, must be a real shebang script, must set UTF-8 mode and
        # exec the real interpreter next to it
        self.assertTrue(os.path.exists(self.shim_posix), "POSIX companion shim was not written")
        posix_lines = open(self.shim_posix, encoding="ascii").read().splitlines()
        self.assertEqual(posix_lines[0], "#!/bin/sh", "first line must be a POSIX shebang")
        posix_body = "\n".join(posix_lines)
        self.assertIn("PYTHONUTF8=1", posix_body)
        self.assertIn('exec "$(dirname "$0")/python.exe" "$@"', posix_body)

        # the returned detail must name BOTH paths -- this is the load-bearing assertion: it fails
        # if either file silently stops being reported (or written)
        self.assertIn(self.shim, detail)
        self.assertIn(self.shim_posix, detail)

    def test_second_run_reports_already_and_does_not_rewrite(self):
        with mock.patch.object(shutil, "which", return_value=None):
            bootstrap.ensure_python3_shim()
            before = open(self.shim, "rb").read()
            status, detail = bootstrap.ensure_python3_shim()
        self.assertEqual(status, "already")
        self.assertEqual(open(self.shim, "rb").read(), before)

    def test_older_shim_without_utf8_is_upgraded_in_place(self):
        # simulate a machine that installed before T8.2a: the pre-fix two-line shim, no PYTHONUTF8.
        with open(self.shim, "w", encoding="ascii", newline="") as f:
            f.write('@echo off\r\n"%~dp0python.exe" %*\r\n')
        with mock.patch.object(shutil, "which", return_value=self.shim):
            status, detail = bootstrap.ensure_python3_shim()
        self.assertEqual(status, "upgraded")
        body = open(self.shim, encoding="ascii").read()
        self.assertIn("PYTHONUTF8=1", body)

    def test_dry_run_upgrade_touches_nothing(self):
        with open(self.shim, "w", encoding="ascii", newline="") as f:
            f.write('@echo off\r\n"%~dp0python.exe" %*\r\n')
        before = open(self.shim, "rb").read()
        with mock.patch.object(shutil, "which", return_value=self.shim):
            status, detail = bootstrap.ensure_python3_shim(dry_run=True)
        self.assertEqual(status, "would-upgrade")
        self.assertEqual(open(self.shim, "rb").read(), before, "--dry-run wrote to disk")

    def test_a_foreign_python3_elsewhere_on_path_is_left_alone(self):
        # e.g. WSL, msys, a real python3.exe from a different install — not ours to rewrite.
        foreign = os.path.join(self.tmp, "elsewhere", "python3.exe")
        os.makedirs(os.path.dirname(foreign))
        open(foreign, "w").close()
        with mock.patch.object(shutil, "which", return_value=foreign):
            status, detail = bootstrap.ensure_python3_shim()
        self.assertEqual(status, "already")
        self.assertFalse(os.path.exists(self.shim), "wrote a shim over something not ours")

    def test_store_alias_stub_is_not_usable_and_gets_replaced(self):
        # The Microsoft Store execution-alias stub lives at a WindowsApps-shaped path and is a few
        # KB, never a real interpreter. It must be treated as ABSENT -- not "already" -- and our
        # shim pair must be installed in its place.
        stub = os.path.join(self.tmp, "AppData", "Local", "Microsoft", "WindowsApps", "python3.exe")
        os.makedirs(os.path.dirname(stub))
        with open(stub, "wb") as f:
            f.write(b"\x00" * 2048)  # well under the stub-size threshold
        with mock.patch.object(shutil, "which", return_value=stub):
            status, detail = bootstrap.ensure_python3_shim()
        self.assertEqual(status, "created")
        self.assertIn(stub, detail, "should name the stub it is replacing")
        self.assertTrue(os.path.exists(self.shim))
        self.assertTrue(os.path.exists(self.shim_posix))

    def test_cannot_determine_is_its_own_status_never_folded_into_already(self):
        # A WindowsApps-shaped path we cannot stat (dangling symlink here) must surface as its own
        # distinct outcome -- never silently treated as "already" (which would skip the fix on a
        # machine that needs it) and never treated as a plain pass.
        broken_dir = os.path.join(self.tmp, "AppData", "Local", "Microsoft", "WindowsApps")
        os.makedirs(broken_dir)
        broken = os.path.join(broken_dir, "python3.exe")
        os.symlink(os.path.join(broken_dir, "does_not_exist.exe"), broken)
        with mock.patch.object(shutil, "which", return_value=broken):
            status, detail = bootstrap.ensure_python3_shim()
        self.assertEqual(status, "undetermined")
        self.assertNotEqual(status, "already")
        self.assertNotEqual(status, "refused")
        self.assertIn(broken, detail)
        self.assertFalse(os.path.exists(self.shim), "must not write over an undetermined case")
        self.assertFalse(os.path.exists(self.shim_posix))


if __name__ == "__main__":
    unittest.main(verbosity=2)
