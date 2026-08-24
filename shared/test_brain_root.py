#!/usr/bin/env python3
"""test_brain_root.py — the teeth on the one root variable.

Run:  python3 shared/test_brain_root.py          (from the repo root)
      python3 -m unittest discover -s shared -p 'test_*.py'

Every case here is a way the resolver could quietly hand back a WRONG directory. A resolver that
guesses is worse than one that refuses, so the NOT-SET cases matter as much as the RESOLVED ones.
No third-party test runner — stdlib unittest only, because a student's fresh clone has nothing
installed.
"""

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain_root  # noqa: E402


class BrainRootCase(unittest.TestCase):
    """Isolates the three inputs the resolver reads: the env var, the persisted file, the legacy glob.
    None of the real ones are touched — the persisted-config path is redirected into a temp dir, so a
    developer's own ~/.config/lifehack/brain-root survives the suite untouched."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="brain-root-test-")
        self.data = os.path.join(self.tmp, "my-data")
        os.makedirs(self.data)
        self._saved = (brain_root.BRAIN_ROOT_CONFIG, brain_root.BRAIN_ROOT_LEGACY_GLOB,
                       os.environ.get(brain_root.BRAIN_ROOT_ENV))
        brain_root.BRAIN_ROOT_CONFIG = os.path.join(self.tmp, "config", "brain-root")
        brain_root.BRAIN_ROOT_LEGACY_GLOB = ""
        os.environ.pop(brain_root.BRAIN_ROOT_ENV, None)
        # 2026-08-17: the resolver now also reads a repo pointer file — redirect it into the temp
        # dir the same way, so the suite never sees (or writes) the real repo's .brain-root.
        self._saved_pointer_fn = brain_root.repo_pointer_path
        brain_root.repo_pointer_path = lambda: os.path.join(self.tmp, ".brain-root")
        # 2026-08-18: --set now REFUSES any target inside the Harness folder, and it finds that
        # folder via harness_root(). Point it at a fake harness inside the temp dir, so the
        # containment cases are exercised without depending on where the real clone happens to be.
        self.harness = os.path.join(self.tmp, "harness")
        os.makedirs(self.harness)
        self._saved_harness_fn = brain_root.harness_root
        brain_root.harness_root = lambda: self.harness

    def tearDown(self):
        brain_root.harness_root = self._saved_harness_fn
        brain_root.repo_pointer_path = self._saved_pointer_fn
        brain_root.BRAIN_ROOT_CONFIG, brain_root.BRAIN_ROOT_LEGACY_GLOB, env = self._saved
        os.environ.pop(brain_root.BRAIN_ROOT_ENV, None)
        if env is not None:
            os.environ[brain_root.BRAIN_ROOT_ENV] = env
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestResolve(BrainRootCase):

    def test_env_wins(self):
        os.environ[brain_root.BRAIN_ROOT_ENV] = self.data
        self.assertEqual(brain_root.resolve_brain_root(), ("env", self.data))

    def test_env_pointing_nowhere_is_ignored_not_obeyed(self):
        """A stale env var must not resolve to a directory that does not exist."""
        os.environ[brain_root.BRAIN_ROOT_ENV] = os.path.join(self.tmp, "gone")
        self.assertEqual(brain_root.resolve_brain_root(), (None, None))

    def test_persisted(self):
        """The persisted-global route, in isolation: --set now ALSO writes the repo pointer
        (2026-08-17), so exercise route (3) by removing the pointer it wrote."""
        ok, res, _note = brain_root.set_brain_root(self.data)
        self.assertTrue(ok, res)
        os.remove(brain_root.repo_pointer_path())
        self.assertEqual(brain_root.resolve_brain_root(), ("persisted", self.data))

    def test_env_beats_persisted(self):
        other = os.path.join(self.tmp, "other")
        os.makedirs(other)
        brain_root.set_brain_root(self.data)
        os.environ[brain_root.BRAIN_ROOT_ENV] = other
        self.assertEqual(brain_root.resolve_brain_root(), ("env", other))

    def test_persisted_pointing_at_a_deleted_folder_falls_through(self):
        brain_root.set_brain_root(self.data)
        shutil.rmtree(self.data)
        self.assertEqual(brain_root.resolve_brain_root(), (None, None))

    def test_legacy_glob(self):
        legacy = os.path.join(self.tmp, "legacy", "SomeCloud", "_Brain")
        os.makedirs(legacy)
        brain_root.BRAIN_ROOT_LEGACY_GLOB = os.path.join(self.tmp, "legacy", "*", "_Brain")
        self.assertEqual(brain_root.resolve_brain_root(), ("legacy-glob", legacy))

    def test_legacy_glob_unset_is_a_noop_not_a_guess(self):
        """The default on every machine but the original author's. Step 3 must vanish, not improvise."""
        self.assertEqual(brain_root.BRAIN_ROOT_LEGACY_GLOB, "")
        self.assertEqual(brain_root.resolve_brain_root(), (None, None))

    def test_not_set_is_the_answer_when_nothing_is_configured(self):
        """The whole point: no env, no persisted file, no glob -> NOT-SET. Never the cwd."""
        source, path = brain_root.resolve_brain_root()
        self.assertIsNone(source)
        self.assertIsNone(path)
        self.assertNotEqual(path, os.getcwd())


class TestSet(BrainRootCase):

    def test_refuses_a_file_masquerading_as_a_dir(self):
        f = os.path.join(self.tmp, "not-a-folder.md")
        with open(f, "w") as fh:
            fh.write("x")
        ok, msg, _note = brain_root.set_brain_root(f)
        self.assertFalse(ok)
        self.assertIn("is a FILE", msg)
        self.assertFalse(os.path.exists(brain_root.BRAIN_ROOT_CONFIG),
                         "a refused --set must not persist anything")

    def test_refuses_a_missing_path_without_create(self):
        ok, msg, _note = brain_root.set_brain_root(os.path.join(self.tmp, "nope"))
        self.assertFalse(ok)
        self.assertIn("--create", msg)

    def test_create_makes_it_parents_included(self):
        deep = os.path.join(self.tmp, "a", "b", "c")
        ok, res, _note = brain_root.set_brain_root(deep, create=True)
        self.assertTrue(ok, res)
        self.assertTrue(os.path.isdir(deep))
        # --set writes the repo pointer first since 2026-08-17, so that is the resolving source
        self.assertEqual(brain_root.resolve_brain_root(), ("repo-pointer", deep))

    def test_persists_an_absolute_path(self):
        """A path given with a ~ still lands absolute in the config file. (Until 2026-08-18 this
        case used a RELATIVE path and asserted it was accepted — that acceptance is precisely the
        bug that put a student's AI Brain inside the repo, so the relative case is now a REFUSAL
        and lives in TestRefusesUnusableTargets below.)"""
        home = os.path.join(self.tmp, "fake-home")
        os.makedirs(os.path.join(home, "AI Brain"))
        saved = os.environ.get("HOME")
        os.environ["HOME"] = home
        try:
            ok, res, _note = brain_root.set_brain_root("~/AI Brain")
        finally:
            if saved is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = saved
        self.assertTrue(ok, res)
        self.assertTrue(os.path.isabs(res))
        with open(brain_root.BRAIN_ROOT_CONFIG) as fh:
            self.assertEqual(fh.read().strip(), os.path.join(home, "AI Brain"))


class TestRefusesUnusableTargets(BrainRootCase):
    """2026-08-18, from a real student run on Windows/Codex. The installer could not find their
    Google Drive, so `--set "G:\\My Drive\\AI Brain" --create` was tried on a machine that was not
    Windows. It was taken as a RELATIVE path: a folder with that literal name was created INSIDE
    the repo, the student's canon, journal and registry were written into it, and four checks
    afterwards all passed — including the cloud-backup one, which was matching the words "my drive"
    in the folder's own name. Each test here is one link of that chain, cut."""

    def _assert_nothing_persisted(self):
        self.assertFalse(os.path.exists(brain_root.BRAIN_ROOT_CONFIG),
                         "a refused --set must not persist anything")
        self.assertFalse(os.path.exists(brain_root.repo_pointer_path()),
                         "a refused --set must not write the repo pointer either")

    def test_the_exact_tester_input_is_refused_and_creates_nothing(self):
        """THE acceptance case."""
        before = sorted(os.listdir(self.harness))
        ok, msg, _note = brain_root.set_brain_root(r"G:\My Drive\AI Brain", create=True)
        self.assertFalse(ok)
        self.assertIn("Windows", msg)
        self.assertEqual(sorted(os.listdir(self.harness)), before,
                         "nothing may be created inside the Harness folder")
        self.assertFalse(os.path.isdir(os.path.join(os.getcwd(), r"G:\My Drive\AI Brain")))
        self._assert_nothing_persisted()

    def test_refuses_a_windows_drive_letter_with_forward_slashes(self):
        ok, msg, _note = brain_root.set_brain_root("C:/ProgramData/AI Brain", create=True)
        self.assertFalse(ok)
        self.assertIn("Windows", msg)

    def test_refuses_a_bare_relative_name(self):
        ok, msg, _note = brain_root.set_brain_root("AI Brain", create=True)
        self.assertFalse(ok)
        self.assertIn("not a complete path", msg)
        self._assert_nothing_persisted()

    def test_refuses_a_dotted_relative_path(self):
        ok, msg, _note = brain_root.set_brain_root("../foo", create=True)
        self.assertFalse(ok)
        self.assertIn("not a complete path", msg)

    def test_refuses_a_target_inside_the_harness(self):
        """The one that matters most: the student's material never lives inside the clone."""
        inside = os.path.join(self.harness, "data", "foo")
        ok, msg, _note = brain_root.set_brain_root(inside, create=True)
        self.assertFalse(ok)
        self.assertIn("inside the Harness", msg)
        self.assertFalse(os.path.exists(inside), "and it was not created on the way to refusing")
        self._assert_nothing_persisted()

    def test_refuses_the_harness_root_itself(self):
        ok, msg, _note = brain_root.set_brain_root(self.harness)
        self.assertFalse(ok)
        self.assertIn("Harness folder itself", msg)

    def test_refuses_a_target_inside_the_harness_reached_through_a_symlink(self):
        """/tmp is a symlink to /private/tmp on macOS, and Drive folders are often symlinked too —
        so containment is decided on realpath, never on the path as typed."""
        link = os.path.join(self.tmp, "link-to-harness")
        os.symlink(self.harness, link)
        ok, msg, _note = brain_root.set_brain_root(os.path.join(link, "data", "foo"), create=True)
        self.assertFalse(ok)
        self.assertIn("inside the Harness", msg)
        self.assertFalse(os.path.exists(os.path.join(self.harness, "data")))

    def test_refuses_an_empty_path(self):
        ok, msg, _note = brain_root.set_brain_root("")
        self.assertFalse(ok)
        self.assertIn("no folder was given", msg)

    def test_every_refusal_says_what_to_do_instead(self):
        """These are read aloud to someone non-technical. A refusal that does not name the next
        move just gets worked around — which is how the original improvisation happened."""
        for bad in (r"G:\My Drive\AI Brain", "AI Brain", "../foo",
                    os.path.join(self.harness, "data", "foo"), self.harness, ""):
            msg = brain_root.reject_unusable_target(bad)
            self.assertIsNotNone(msg, bad)
            self.assertTrue(msg.startswith("REFUSED"), bad)
            self.assertIn("/", msg.split("REFUSED", 1)[1], bad)

    def test_the_good_paths_still_pass_the_gate(self):
        """The gate must be invisible to every legitimate install."""
        drive = os.path.join(self.tmp, "CloudStorage", "GoogleDrive-account", "My Drive", "AI Brain")
        os.makedirs(drive)
        for good in (self.data, drive, os.path.join(self.tmp, "not-yet-made")):
            self.assertIsNone(brain_root.reject_unusable_target(good), good)
        ok, res, _note = brain_root.set_brain_root(drive)
        self.assertTrue(ok, res)
        self.assertEqual(res, drive)
        ok, res, _note = brain_root.set_brain_root(os.path.join(self.tmp, "not-yet-made"), create=True)
        self.assertTrue(ok, res)
        self.assertTrue(os.path.isdir(res))

    def test_the_cli_exits_nonzero_on_the_tester_input(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = brain_root.main(["--set", r"G:\My Drive\AI Brain", "--create"])
        self.assertEqual(rc, 1)
        self.assertIn("REFUSED", buf.getvalue())


class TestCli(BrainRootCase):
    """The CLI is the surface INSTALL and the skills call. Its exit codes are the contract."""

    def test_quiet_exits_1_when_not_set(self):
        self.assertEqual(brain_root.main(["--quiet"]), 1)

    def test_quiet_exits_0_and_prints_the_path(self):
        os.environ[brain_root.BRAIN_ROOT_ENV] = self.data
        self.assertEqual(brain_root.main(["--quiet"]), 0)

    def test_set_then_resolve_round_trip(self):
        self.assertEqual(brain_root.main(["--set", self.data]), 0)
        self.assertEqual(brain_root.main([]), 0)

    def test_set_a_missing_path_exits_1(self):
        self.assertEqual(brain_root.main(["--set", os.path.join(self.tmp, "nope")]), 1)


class TestReplacementIsNeverSilent(BrainRootCase):
    """Issue #4. The config is ONE global value outside the repo, so a second install repoints the
    first. That is allowed — it is what the caller asked for — but it may never happen quietly."""

    def setUp(self):
        super().setUp()
        self.other = os.path.join(self.tmp, "other-brain")
        os.makedirs(self.other)

    def _set(self, path, *extra):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = brain_root.main(["--set", path, *extra])
        return rc, buf.getvalue()

    def test_read_persisted_is_none_before_anything_is_set(self):
        self.assertIsNone(brain_root.read_persisted())

    def test_read_persisted_returns_the_raw_value(self):
        brain_root.set_brain_root(self.data)
        self.assertEqual(brain_root.read_persisted(), self.data)

    def test_read_persisted_reports_a_root_whose_folder_is_gone(self):
        """resolve_brain_root() hides this by returning NOT-SET; the whole point of read_persisted()
        is that a root pointing at a deleted folder is the case most worth reporting."""
        brain_root.set_brain_root(self.data)
        shutil.rmtree(self.data)
        self.assertEqual(brain_root.read_persisted(), self.data)
        self.assertEqual(brain_root.resolve_brain_root(), (None, None))

    def test_first_set_says_nothing_about_replacing(self):
        rc, out = self._set(self.data)
        self.assertEqual(rc, 0)
        self.assertNotIn("REPLACED", out)

    def test_overwriting_a_different_root_is_now_GUARDED(self):
        """CONTRACT CHANGE 2026-08-17 (after a logged near-miss): --set no longer silently repoints
        a different existing global. It writes the repo pointer, leaves the global alone, and says
        so, naming the old value. --replace-global is the deliberate path."""
        self._set(self.data)
        rc, out = self._set(self.other)
        self.assertEqual(rc, 0, "still succeeds — the repo pointer is written")
        self.assertIn("GLOBAL UNCHANGED", out)
        self.assertIn(self.data, out, "must name the global it declined to touch")
        self.assertEqual(brain_root.read_persisted(), self.data, "global really untouched")
        self.assertEqual(brain_root.read_repo_pointer(), self.other, "pointer really written")

    def test_replace_global_flag_does_replace_and_warns(self):
        self._set(self.data)
        rc, out = self._set(self.other, "--replace-global")
        self.assertEqual(rc, 0)
        self.assertIn("REPLACED", out)
        self.assertIn(self.data, out, "the warning must name the path it replaced, or it is useless")
        self.assertEqual(brain_root.read_persisted(), self.other)

    def test_repo_pointer_beats_persisted_global(self):
        """The shared-computer case: global points at brain A, this repo's pointer at brain B —
        a session in this repo must resolve B."""
        ok, _res, _n = brain_root.set_brain_root(self.data)   # writes pointer=data, global=data
        with open(brain_root.repo_pointer_path(), "w", encoding="utf-8") as f:
            f.write(self.other + "\n")
        self.assertEqual(brain_root.resolve_brain_root(), ("repo-pointer", self.other))

    def test_missing_pointer_falls_back_to_persisted(self):
        brain_root.set_brain_root(self.data)
        os.remove(brain_root.repo_pointer_path())
        self.assertEqual(brain_root.resolve_brain_root(), ("persisted", self.data))

    def test_setting_the_same_root_twice_is_not_a_warning(self):
        """A re-run of a normal install must stay quiet, or the warning becomes noise and is ignored
        on the one run where it matters."""
        self._set(self.data)
        rc, out = self._set(self.data)
        self.assertEqual(rc, 0)
        self.assertNotIn("REPLACED", out)

    def test_a_refused_set_leaves_the_previous_root_alone(self):
        self._set(self.data)
        rc, out = self._set(os.path.join(self.tmp, "does-not-exist"))
        self.assertEqual(rc, 1)
        self.assertNotIn("REPLACED", out)
        self.assertEqual(brain_root.read_persisted(), self.data)


class TestTheWindowsShapeRuleIsPlatformGated(BrainRootCase):
    """2026-08-19, field report #84. A student ON WINDOWS is really keeping their AI Brain at
    `G:\\My Drive\\AI Brain`, and there that is a perfectly real, correct place — Google Drive
    genuinely mounts as a drive letter. The shape rule fired on every platform and refused them,
    while telling them their own computer was macOS or Linux. Since INSTALL.md instructs the
    assistant to STOP when --set refuses, that dead-ended a correct install on a falsehood.

    So: the shape rule is now asked only when os.name is not "nt". The other three refusals —
    not-absolute, inside-the-Harness, and the Harness itself — are untouched on every platform."""

    def _refusal_on(self, os_name, path):
        """reject_unusable_target() as it behaves under a given os.name. Only the gate is
        simulated: os.path stays posix here, which is why the Windows cases below assert what
        must NOT be in the message rather than asserting outright acceptance."""
        saved = os.name
        os.name = os_name
        try:
            return brain_root.reject_unusable_target(path)
        finally:
            os.name = saved

    def test_the_shape_rule_still_fires_when_not_on_windows(self):
        """The 2026-08-18 catastrophe case, unchanged where it was right."""
        msg = self._refusal_on("posix", r"G:\My Drive\AI Brain")
        self.assertIsNotNone(msg)
        self.assertIn("Windows", msg)

    def test_the_shape_rule_does_not_fire_on_windows(self):
        """THE new acceptance case. It may still be refused by a LATER rule under this simulation
        (os.path is posix here, so isabs is posix), but never by the shape rule."""
        msg = self._refusal_on("nt", r"G:\My Drive\AI Brain")
        if msg is not None:
            # NB the sentinel is the shape refusal's own phrase, not the words "drive letter" —
            # since 2026-08-19 the not-absolute message says "drive letter" quite legitimately
            # when it is speaking to a Windows user.
            self.assertNotIn("Windows", msg)
            self.assertNotIn("written in the Windows style", msg)

    def test_a_forward_slash_drive_letter_is_not_shape_refused_on_windows(self):
        msg = self._refusal_on("nt", "C:/ProgramData/AI Brain")
        if msg is not None:
            self.assertNotIn("Windows", msg)

    def test_a_native_windows_path_passes_the_gate_when_os_path_is_windows_too(self):
        """The honest end of the simulation: with BOTH os.name and os.path switched to Windows —
        which is what a real Windows interpreter has — the drive-letter path passes cleanly."""
        import ntpath
        saved_name, saved_path = os.name, os.path
        os.name, os.path = "nt", ntpath
        try:
            self.assertIsNone(brain_root.reject_unusable_target(r"G:\My Drive\AI Brain"))
            self.assertIsNone(brain_root.reject_unusable_target(r"C:\Users\somebody\AI Brain"))
        finally:
            os.name, os.path = saved_name, saved_path

    def test_the_other_three_refusals_are_unchanged_on_windows(self):
        """Gating the shape rule must not open any of the other doors."""
        self.assertIn("not a complete path", self._refusal_on("nt", "AI Brain"))
        self.assertIn("no folder was given", self._refusal_on("nt", ""))
        self.assertIn("inside the Harness",
                      self._refusal_on("nt", os.path.join(self.harness, "data", "foo")))
        self.assertIn("Harness folder itself", self._refusal_on("nt", self.harness))

    def test_the_catastrophe_is_still_caught_if_the_shape_rule_is_taken_away(self):
        """DEFENCE IN DEPTH. On macOS/Linux `G:\\My Drive\\AI Brain` is a RELATIVE path, so the
        not-absolute rule refuses it on its own. The shape rule supplies the CLEAR message; it was
        never the only wall, and gating it does not leave the original hole open."""
        saved = brain_root.looks_like_a_windows_path
        brain_root.looks_like_a_windows_path = lambda raw: False
        try:
            msg = brain_root.reject_unusable_target(r"G:\My Drive\AI Brain")
            ok, setmsg, _n = brain_root.set_brain_root(r"G:\My Drive\AI Brain", create=True)
        finally:
            brain_root.looks_like_a_windows_path = saved
        self.assertIsNotNone(msg)
        self.assertIn("not a complete path", msg)
        self.assertFalse(ok)
        self.assertIn("not a complete path", setmsg)
        self.assertFalse(os.path.isdir(os.path.join(os.getcwd(), r"G:\My Drive\AI Brain")))

    def test_no_refusal_ever_asserts_what_os_the_machine_is(self):
        """The message told a Windows student their computer was macOS or Linux. A refusal may
        describe the PATH all it likes; it may not make a claim about the machine."""
        bad = (r"G:\My Drive\AI Brain", "C:/ProgramData/AI Brain", "AI Brain", "../foo", "",
               os.path.join(self.harness, "data", "foo"), self.harness)
        for path in bad:
            for os_name in ("posix", "nt"):
                msg = self._refusal_on(os_name, path)
                if msg is None:
                    continue
                for claim in ("running macOS", "running Linux", "This computer is running",
                              "macOS or Linux", "you are on Windows", "your computer is"):
                    self.assertNotIn(claim, msg, f"{path!r} under os.name={os_name!r}")
                if os_name == "nt":
                    # the sibling bug, 2026-08-19: on Windows a complete path starts with a drive
                    # letter, so no refusal may tell a Windows user it must start with a slash
                    for slash_claim in ("does not start with a / ", "starts with a slash",
                                        "starting with a / ", "starts with a, /", "with a slash, /"):
                        self.assertNotIn(slash_claim, msg, f"{path!r} under os.name={os_name!r}")


class TestALinkedWorktreeBorrowsTheMainWorktreesPointer(BrainRootCase):
    """2026-08-21. A session running in `.claude/worktrees/<name>/` started BLIND.

    `git worktree add` materialises only TRACKED files, and `.brain-root` is deliberately gitignored
    — so route (2) was looking at the worktree root for a pointer git will never put there.
    Resolution fell silently through to the machine-global config, which had gone stale after the
    2026-08-17 restructure (it still named a folder that no longer existed). Nothing raised: the
    session simply read nothing. Each test here is one link of that chain, cut — and the ones at the
    bottom are the fences, because a route that borrows a path from elsewhere is exactly the kind
    that starts guessing."""

    def _make_worktree(self, brain=None, relative_gitdir=False, name="wt"):
        """Build git's real linked-worktree layout in the temp dir and point harness_root() at the
        worktree. Returns (worktree_dir, main_dir). `brain` writes the MAIN worktree's pointer."""
        main = os.path.join(self.tmp, "main")
        common = os.path.join(main, ".git")
        gitdir = os.path.join(common, "worktrees", name)
        worktree = os.path.join(self.tmp, name)
        os.makedirs(gitdir)
        os.makedirs(worktree)
        with open(os.path.join(gitdir, "commondir"), "w", encoding="utf-8") as f:
            f.write("../..\n")                      # exactly what git writes
        pointer = gitdir if not relative_gitdir else os.path.relpath(gitdir, worktree)
        with open(os.path.join(worktree, ".git"), "w", encoding="utf-8") as f:
            f.write(f"gitdir: {pointer}\n")
        if brain is not None:
            with open(os.path.join(main, brain_root.REPO_POINTER_NAME), "w", encoding="utf-8") as f:
                f.write(brain + "\n")
        brain_root.harness_root = lambda: worktree
        return worktree, main

    def test_a_linked_worktree_resolves_the_main_worktrees_brain(self):
        """THE acceptance case: no pointer of its own, nothing else configured, and it still finds
        the brain instead of going blind."""
        self._make_worktree(brain=self.data)
        self.assertEqual(brain_root.resolve_brain_root(), ("main-worktree-pointer", self.data))

    def test_the_incident_a_stale_global_no_longer_decides(self):
        """2026-08-21 exactly: the global named a folder deleted in the 2026-08-17 restructure, so
        route (3) could not answer either and the session got NOT-SET — silently, mid-work."""
        gone = os.path.join(self.tmp, "old-brain", "data")
        os.makedirs(gone)
        brain_root.set_brain_root(gone)
        os.remove(brain_root.repo_pointer_path())    # a worktree never had one to begin with
        shutil.rmtree(gone)                          # ...and then the restructure removed it
        self._make_worktree(brain=self.data)
        self.assertEqual(brain_root.read_persisted(), gone, "the stale global is still there")
        self.assertEqual(brain_root.resolve_brain_root(), ("main-worktree-pointer", self.data))

    def test_it_also_beats_a_global_that_merely_disagrees(self):
        """Order, not just rescue: (2b) sits ABOVE the machine-global, which belongs to no repo in
        particular, so a worktree of THIS repo resolves THIS repo's brain."""
        other = os.path.join(self.tmp, "someone-elses-brain")
        os.makedirs(other)
        brain_root.set_brain_root(other)
        os.remove(brain_root.repo_pointer_path())
        self._make_worktree(brain=self.data)
        self.assertEqual(brain_root.resolve_brain_root(), ("main-worktree-pointer", self.data))

    def test_the_worktrees_own_pointer_still_wins(self):
        """Route (2) is untouched. A worktree that HAS been given a pointer by hand — as
        intelligent-wu-7374b1 was on 2026-08-21 — keeps using it."""
        own = os.path.join(self.tmp, "this-worktrees-own-brain")
        os.makedirs(own)
        self._make_worktree(brain=self.data)
        with open(brain_root.repo_pointer_path(), "w", encoding="utf-8") as f:
            f.write(own + "\n")
        self.assertEqual(brain_root.resolve_brain_root(), ("repo-pointer", own))

    def test_env_still_beats_everything(self):
        other = os.path.join(self.tmp, "env-brain")
        os.makedirs(other)
        self._make_worktree(brain=self.data)
        os.environ[brain_root.BRAIN_ROOT_ENV] = other
        self.assertEqual(brain_root.resolve_brain_root(), ("env", other))

    def test_a_relative_gitdir_line_is_resolved_against_the_worktree(self):
        """git is free to write `gitdir:` relative. Resolved against the WORKTREE folder — never
        against the cwd, which is the whole family of bugs this module exists to refuse."""
        self._make_worktree(brain=self.data, relative_gitdir=True)
        saved = os.getcwd()
        os.chdir(self.tmp)          # a cwd that would resolve it wrong, if cwd were consulted
        try:
            self.assertEqual(brain_root.resolve_brain_root(), ("main-worktree-pointer", self.data))
        finally:
            os.chdir(saved)

    # ── the fences ────────────────────────────────────────────────────────────────────────────────

    def test_an_ordinary_clone_is_not_a_worktree(self):
        """A normal clone has a .git DIRECTORY. The new route must be invisible to it."""
        os.makedirs(os.path.join(self.harness, ".git"))
        self.assertIsNone(brain_root.main_worktree_root())
        self.assertIsNone(brain_root.read_main_worktree_pointer())

    def test_a_folder_with_no_git_at_all_is_not_a_worktree(self):
        self.assertIsNone(brain_root.main_worktree_root())

    def test_a_submodule_is_not_mistaken_for_a_worktree(self):
        """A submodule ALSO has a `.git` file holding a `gitdir:` line — but its git dir carries no
        `commondir`, and its parent is another project's folder entirely. Borrowing a pointer from
        there would be a guess."""
        parent = os.path.join(self.tmp, "parent")
        modules = os.path.join(parent, ".git", "modules", "sub")
        sub = os.path.join(parent, "sub")
        os.makedirs(modules)
        os.makedirs(sub)
        with open(os.path.join(sub, ".git"), "w", encoding="utf-8") as f:
            f.write(f"gitdir: {modules}\n")
        with open(os.path.join(parent, ".brain-root"), "w", encoding="utf-8") as f:
            f.write(self.data + "\n")
        brain_root.harness_root = lambda: sub
        self.assertIsNone(brain_root.main_worktree_root())
        self.assertEqual(brain_root.resolve_brain_root(), (None, None))

    def test_a_common_dir_that_is_not_dot_git_is_not_guessed_at(self):
        """A bare repo, or one made with --separate-git-dir, has no main worktree at the parent of
        the common dir. NOT-SET is the correct answer there; a plausible-looking parent is not."""
        worktree, main = self._make_worktree(brain=self.data)
        gitdir = os.path.join(main, ".git", "worktrees", "wt")
        elsewhere = os.path.join(self.tmp, "repo.git")
        os.makedirs(elsewhere)
        with open(os.path.join(gitdir, "commondir"), "w", encoding="utf-8") as f:
            f.write(elsewhere + "\n")
        self.assertIsNone(brain_root.main_worktree_root())

    def test_a_borrowed_pointer_at_a_deleted_folder_falls_through_to_not_set(self):
        """NOT-SET semantics are unchanged: a route may only answer with a REAL directory."""
        self._make_worktree(brain=os.path.join(self.tmp, "never-existed"))
        self.assertEqual(brain_root.resolve_brain_root(), (None, None))

    def test_a_main_worktree_with_no_pointer_falls_through_quietly(self):
        """The ordinary pre-fix state of a fresh clone: nothing to borrow, and no invention."""
        self._make_worktree(brain=None)
        self.assertIsNone(brain_root.read_main_worktree_pointer())
        self.assertEqual(brain_root.resolve_brain_root(), (None, None))

    def test_an_empty_or_malformed_git_file_is_survived_not_crashed(self):
        """A resolver that raises is worse than one that declines — it is consulted on every path
        in the system, including from hooks nobody is watching."""
        worktree = os.path.join(self.tmp, "broken")
        os.makedirs(worktree)
        brain_root.harness_root = lambda: worktree
        for junk in ("", "   ", "not a gitdir line", "gitdir:", "gitdir:    ",
                     "gitdir: /nowhere/at/all", "\n\n", "gitdir: /nowhere\nand a second line"):
            with open(os.path.join(worktree, ".git"), "w", encoding="utf-8") as f:
                f.write(junk)
            self.assertIsNone(brain_root.main_worktree_root(), repr(junk))
            self.assertEqual(brain_root.resolve_brain_root(), (None, None), repr(junk))

    def test_resolution_never_writes_anything(self):
        """Reading where the brain is must not create a pointer, in the worktree or the main
        worktree — a resolver with side effects would make the stale-global bug unrepeatable."""
        worktree, main = self._make_worktree(brain=self.data)
        before = (sorted(os.listdir(worktree)), sorted(os.listdir(main)))
        brain_root.resolve_brain_root()
        self.assertEqual((sorted(os.listdir(worktree)), sorted(os.listdir(main))), before)
        self.assertFalse(os.path.exists(brain_root.BRAIN_ROOT_CONFIG))


class TestOutputSurvivesANarrowConsole(BrainRootCase):
    """2026-08-19, field report #72. This module prints a warning sign and other characters that do
    not exist in a narrow console codepage such as Windows cp1252. Printing one there raised
    UnicodeEncodeError and killed the process AT THE MOMENT IT WAS WARNING SOMEBODY that their AI
    Brain had just been repointed — the single worst message to lose."""

    def test_it_is_a_silent_no_op_on_a_stream_that_cannot_reconfigure(self):
        """StringIO has no .reconfigure — and this whole suite redirects stdout into one. The
        guard must swallow that, because a crash while making output readable is a new bug."""
        saved = (sys.stdout, sys.stderr)
        sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
        try:
            brain_root.make_console_output_safe()
        finally:
            sys.stdout, sys.stderr = saved

    def test_it_is_called_before_anything_is_printed(self):
        """It has to run inside main(), not at import, or a library caller changes the host
        program's streams as a side effect of importing."""
        import inspect
        body = inspect.getsource(brain_root.main)
        self.assertIn("make_console_output_safe()", body)

    def test_the_warning_sign_prints_on_a_cp1252_console_without_dying(self):
        """End to end in a real subprocess with the console forced narrow. Before the fix this
        exits non-zero on UnicodeEncodeError. Imports the module only — reads no config, writes
        nothing, touches no brain root."""
        shared_dir = os.path.dirname(os.path.abspath(brain_root.__file__))
        code = ("import sys; sys.path.insert(0, %r); import brain_root;"
                " brain_root.make_console_output_safe();"
                " print('\\u26a0 REPLACED the machine-global brain root that was already set')"
                % shared_dir)
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        proc = subprocess.run([sys.executable, "-c", code], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        self.assertIn(b"REPLACED", proc.stdout)

    def test_without_the_guard_that_same_print_really_does_die(self):
        """POSITIVE CONTROL. Same subprocess, same console, only make_console_output_safe() is not
        called — so the test proves the fix, not the environment."""
        code = ("print('\\u26a0 REPLACED the machine-global brain root that was already set')")
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        proc = subprocess.run([sys.executable, "-c", code], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(proc.returncode, 0, "the control must fail, or it controls nothing")
        self.assertIn(b"UnicodeEncodeError", proc.stderr)


class TestTheCompletePathAdviceIsTrueOnTheMachineItRunsOn(BrainRootCase):
    """2026-08-19, the sibling of field report #84. Gating the drive-letter rule on os.name let
    Windows users through it — straight into the NEXT rule, whose message told them a complete
    path "does not start with a / ". On Windows a complete path starts with a drive letter, so the
    dead end had simply moved one rule down. Behaviour is frozen here: every path refused before is
    still refused, for the same reason. Only the words changed."""

    def _refusal_on(self, os_name, path):
        saved = os.name
        os.name = os_name
        try:
            return brain_root.reject_unusable_target(path)
        finally:
            os.name = saved

    def test_the_helper_answers_for_the_machine_it_is_asked_about(self):
        saved = os.name
        try:
            os.name = "nt"
            starts, example, _how = brain_root.how_a_complete_path_is_written_here()
            self.assertIn("drive letter", starts)
            self.assertIn("C:", example)
            os.name = "posix"
            starts, example, _how = brain_root.how_a_complete_path_is_written_here()
            self.assertIn("/", starts)
            self.assertNotIn("drive letter", starts)
        finally:
            os.name = saved

    def test_not_a_complete_path_says_drive_letter_on_windows(self):
        msg = self._refusal_on("nt", "AI Brain")
        self.assertIn("not a complete path", msg, "the REFUSAL itself is unchanged")
        self.assertIn("drive letter", msg)
        self.assertNotIn("does not start with a / ", msg)

    def test_not_a_complete_path_still_says_slash_off_windows(self):
        msg = self._refusal_on("posix", "AI Brain")
        self.assertIn("not a complete path", msg)
        self.assertIn("starts with a slash, /", msg)
        self.assertNotIn("drive letter", msg)

    def test_the_empty_path_refusal_is_true_on_both(self):
        nt = self._refusal_on("nt", "")
        posix = self._refusal_on("posix", "")
        self.assertIn("no folder was given", nt, "the REFUSAL itself is unchanged")
        self.assertIn("no folder was given", posix)
        self.assertIn("drive letter", nt)
        self.assertNotIn("starting with a / ", nt)
        self.assertIn("/", posix)

    def test_the_terminal_hint_is_not_given_where_it_would_be_wrong(self):
        """`pwd` is a POSIX shell builtin. Telling a cmd.exe user to type it is the same category
        of small falsehood that started all of this."""
        self.assertNotIn("pwd", self._refusal_on("nt", "AI Brain"))
        self.assertIn("pwd", self._refusal_on("posix", "AI Brain"))

    def test_behaviour_is_frozen_only_the_words_moved(self):
        """The whole point of the amendment: same paths refused, same rules firing, both platforms.
        Compares WHICH rule answered, never the prose."""
        cases = (("", "no folder was given"),
                 ("AI Brain", "not a complete path"),
                 ("../foo", "not a complete path"),
                 (os.path.join(self.harness, "data", "foo"), "inside the Harness"),
                 (self.harness, "Harness folder itself"))
        for path, rule in cases:
            for os_name in ("posix", "nt"):
                msg = self._refusal_on(os_name, path)
                self.assertIsNotNone(msg, f"{path!r} must still be refused under {os_name}")
                self.assertTrue(msg.startswith("REFUSED"), path)
                self.assertIn(rule, msg, f"{path!r} under {os_name} must still hit the SAME rule")

    def test_every_refusal_still_names_the_next_move_on_windows_too(self):
        """The original acceptance property, re-checked on the other platform: a refusal that does
        not say what to do instead just gets worked around."""
        for bad in (r"G:\My Drive\AI Brain", "AI Brain", "../foo", "",
                    os.path.join(self.harness, "data", "foo"), self.harness):
            for os_name in ("posix", "nt"):
                msg = self._refusal_on(os_name, bad)
                if msg is None:
                    continue
                self.assertTrue(msg.startswith("REFUSED"), bad)
                self.assertIn("AI Brain", msg, f"{bad!r} under {os_name} names no example")


if __name__ == "__main__":
    unittest.main(verbosity=2)
