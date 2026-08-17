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

    def tearDown(self):
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
        rel = os.path.relpath(self.data, os.getcwd())
        ok, res, _note = brain_root.set_brain_root(rel)
        self.assertTrue(ok, res)
        self.assertTrue(os.path.isabs(res))
        with open(brain_root.BRAIN_ROOT_CONFIG) as fh:
            self.assertEqual(fh.read().strip(), self.data)


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
