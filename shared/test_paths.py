#!/usr/bin/env python3
"""Tests for shared/paths.py — the cross-platform path resolver.

The point of these is NOT that the paths look pretty. It is that the two rules the module exists to
keep are actually kept:

  1. **It never guesses.** Anything derived from the brain root returns None when the root is
     NOT-SET, so the caller stops instead of writing someone's notes into an invented folder.
  2. **It produces the same answer the ten shell preambles produced**, so this refactor is a
     substitution and not a silent relocation of everybody's data.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain_root  # noqa: E402
import paths       # noqa: E402


class TestNeverGuesses(unittest.TestCase):
    """Rule 1 — NOT-SET propagates as None, all the way down."""

    def setUp(self):
        self._env = dict(os.environ)
        # Kill every resolution route: env var, persisted config (via HOME), legacy glob.
        os.environ.pop(paths.brain_root.BRAIN_ROOT_ENV, None)
        os.environ["HOME"] = os.path.join(tempfile.gettempdir(), "lifehack-test-nonexistent-home")
        os.environ["INGEST_LEGACY_ROOT_GLOB"] = ""
        # brain_root caches the config path at import time, so point it at nothing that exists.
        self._cfg = brain_root.BRAIN_ROOT_CONFIG
        brain_root.BRAIN_ROOT_CONFIG = os.path.join(os.environ["HOME"], ".config", "lifehack", "brain-root")
        self._glob = brain_root.BRAIN_ROOT_LEGACY_GLOB
        brain_root.BRAIN_ROOT_LEGACY_GLOB = ""

    def tearDown(self):
        brain_root.BRAIN_ROOT_CONFIG = self._cfg
        brain_root.BRAIN_ROOT_LEGACY_GLOB = self._glob
        os.environ.clear()
        os.environ.update(self._env)

    def test_corpus_map_is_none_not_a_default(self):
        self.assertIsNone(paths.corpus_map())

    def test_corpus_work_is_none_not_a_default(self):
        self.assertIsNone(paths.corpus_work())

    def test_never_falls_back_to_cwd(self):
        """The specific failure this guards: silently writing into whatever folder we happen to be in."""
        for got in (paths.corpus_map(), paths.corpus_work()):
            self.assertIsNone(got)
            if got is not None:                      # belt and braces if the above ever regresses
                self.assertNotIn(os.getcwd(), got)

    def test_repo_root_still_answers(self):
        """repo_root does NOT depend on the brain root — it must keep working when the root is unset,
        or the error messages that tell you how to set the root cannot themselves be printed."""
        self.assertTrue(os.path.isdir(paths.repo_root()))


class TestMatchesTheOldShellPreamble(unittest.TestCase):
    """Rule 2 — same answer as the shell it replaces, so nobody's data moves."""

    def setUp(self):
        self._env = dict(os.environ)
        self.root = tempfile.mkdtemp(prefix="lifehack-test-brain-")
        os.environ[paths.brain_root.BRAIN_ROOT_ENV] = self.root

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def test_corpus_map_matches_the_shell_expression(self):
        # The literal the preambles built:
        #   MAP="$DRIVE/state/projects/$INGEST_CORPUS/work/corpus-map.json"
        os.environ[paths.CORPUS_ENV] = "my-corpus"
        expected = os.path.join(self.root, "state", "projects", "my-corpus", "work", "corpus-map.json")
        self.assertEqual(paths.corpus_map(), expected)

    def test_corpus_slug_is_env_overridable(self):
        os.environ[paths.CORPUS_ENV] = "other-corpus"
        self.assertIn("other-corpus", paths.corpus_map())

    def test_corpus_slug_defaults_to_the_historical_value(self):
        os.environ.pop(paths.CORPUS_ENV, None)
        self.assertEqual(paths.corpus_slug(), "my-corpus")


class TestPlatformCorrectness(unittest.TestCase):
    """The POSIX literals these replace (`/tmp`, `$HOME/.cache`) are what issue #7 is about."""

    def test_scratch_dir_is_real_and_writable(self):
        d = paths.scratch_dir("unit-test")
        self.assertTrue(os.path.isdir(d))
        probe = os.path.join(d, "probe.txt")
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("ok")
        with open(probe, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "ok")
        os.remove(probe)

    def test_scratch_dir_is_not_hardcoded_tmp(self):
        """On Windows `/tmp` is not a path. The value must come from the platform, not a literal."""
        self.assertEqual(paths.scratch_dir(), os.path.join(tempfile.gettempdir(), "lifehack"))

    def test_cache_dir_is_real_and_platform_shaped(self):
        d = paths.cache_dir("unit-test")
        self.assertTrue(os.path.isdir(d))
        if sys.platform == "darwin":
            self.assertIn(os.path.join("Library", "Caches"), d)
        elif os.name == "nt":
            self.assertNotIn("/.cache", d.replace("\\", "/"))

    def test_interpreter_is_an_absolute_existing_file(self):
        """Bare `python3` does not exist on a standard Windows install; this must be a real path."""
        exe = paths.interpreter()
        self.assertTrue(os.path.isabs(exe))
        self.assertTrue(os.path.exists(exe))


if __name__ == "__main__":
    unittest.main()
