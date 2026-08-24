#!/usr/bin/env python3
"""Tests for shared/paths.py — the cross-platform path resolver.

The point of these is NOT that the paths look pretty. It is that the two rules the module exists to
keep are actually kept:

  1. **It never guesses.** Anything derived from the brain root returns None when the root is
     NOT-SET, so the caller stops instead of writing someone's notes into an invented folder.
  2. **It produces the same answer the ten shell preambles produced**, so this refactor is a
     substitution and not a silent relocation of everybody's data.
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
        # ...and the two routes that read a POINTER FILE off disk, which no env var or module
        # constant above can reach: this repo's own `.brain-root` (route 2, added 2026-08-17) and,
        # when this folder is a linked git worktree, the main worktree's (route 2b, added
        # 2026-08-21). Both were live through the scrubbing, so this suite has been red in the main
        # clone — which HAS a pointer — since 2026-08-17, and green in a worktree only because git
        # never materialises a gitignored file there. Both hang off harness_root(), so redirecting
        # that single seam closes both, and any later route derived from it.
        self._harness = brain_root.harness_root
        brain_root.harness_root = lambda: os.path.join(os.environ["HOME"], "no-such-harness")

    def tearDown(self):
        brain_root.harness_root = self._harness
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


class TestLegacyCacheIsNeverStranded(unittest.TestCase):
    """Moving where an answer comes from must never orphan the data the old answer pointed at.

    A real flatten costs real time to rebuild, and the person whose machine already has one did not
    ask for a migration. So an existing legacy directory WINS, and only a machine without one gets
    the portable location."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="paths-legacy-test-")
        self._saved_home = os.environ.get("HOME")
        self._saved_legacy = paths.LEGACY_CACHE
        os.environ["HOME"] = self.tmp
        paths.LEGACY_CACHE = os.path.join(self.tmp, ".cache", "cowork-ingest")

    def tearDown(self):
        paths.LEGACY_CACHE = self._saved_legacy
        if self._saved_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self._saved_home
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_legacy(self, *parts):
        d = os.path.join(paths.LEGACY_CACHE, *parts)
        os.makedirs(d)
        return d

    def test_an_existing_legacy_flatten_wins(self):
        want = self._make_legacy("some-corpus", "flatten")
        self.assertEqual(paths.flatten_dir("some-corpus"), want)

    def test_no_legacy_means_the_portable_location(self):
        got = paths.flatten_dir("some-corpus")
        self.assertNotIn(os.path.join(".cache", "cowork-ingest"), got)
        self.assertIn("some-corpus", got)

    def test_pre_slug_flatten_serves_only_the_original_corpus(self):
        """⛔ The scoping is a SAFETY rule, not a convenience: unscoped, a brand-new corpus resolves
        to the original's flatten and silently reads its chats."""
        want = self._make_legacy("flatten")
        self.assertEqual(paths.flatten_dir(paths.LEGACY_CORPUS), want)
        self.assertNotEqual(paths.flatten_dir("a-brand-new-corpus"), want)

    def test_a_slugged_legacy_beats_the_pre_slug_one(self):
        self._make_legacy("flatten")
        want = self._make_legacy(paths.LEGACY_CORPUS, "flatten")
        self.assertEqual(paths.flatten_dir(paths.LEGACY_CORPUS), want)

    def test_an_existing_legacy_anchor_wins(self):
        os.makedirs(os.path.join(paths.LEGACY_CACHE, "c"))
        want = os.path.join(paths.LEGACY_CACHE, "c", "ingest-anchor.txt")
        open(want, "w").write("x")
        self.assertEqual(paths.anchor_file("c"), want)

    def test_no_legacy_anchor_means_the_portable_location(self):
        got = paths.anchor_file("c")
        self.assertTrue(got.endswith("ingest-anchor.txt"))
        self.assertNotIn(os.path.join(".cache", "cowork-ingest"), got)


class TestCli(unittest.TestCase):
    """The CLI exists so a markdown command block can ASK for a path instead of building one. Its
    contract is: exactly one path on stdout, or a non-zero exit and NOTHING on stdout."""

    def _run(self, argv):
        buf, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            rc = paths.main(argv)
        return rc, buf.getvalue().strip(), err.getvalue().strip()

    def test_scratch_prints_one_absolute_path(self):
        rc, out, _ = self._run(["scratch", "ingest_body", "scan-money"])
        self.assertEqual(rc, 0)
        self.assertEqual(len(out.splitlines()), 1)
        self.assertTrue(os.path.isabs(out))
        self.assertTrue(out.endswith(os.path.join("ingest_body", "scan-money")))

    def test_parts_are_joined_with_the_platform_separator(self):
        _, out, _ = self._run(["scratch", "a", "b"])
        self.assertTrue(out.endswith(os.path.join("a", "b")))

    def test_scratchfile_gives_a_file_whose_parent_exists(self):
        """⛔ The trap: scratch_dir("x.json") would MAKE A DIRECTORY called x.json, and the next
        open(...,'w') dies. The parent must exist; the file itself must not."""
        rc, out, _ = self._run(["scratchfile", "filer", "filer-plan.json"])
        self.assertEqual(rc, 0)
        self.assertTrue(out.endswith("filer-plan.json"))
        self.assertTrue(os.path.isdir(os.path.dirname(out)))
        self.assertFalse(os.path.isdir(out))
        with open(out, "w") as fh:          # the whole point: this must not raise
            fh.write("{}")
        os.remove(out)

    def test_scratchfile_with_no_arguments_is_an_error_not_a_directory(self):
        with self.assertRaises(ValueError):
            paths.scratch_file()

    def test_no_arguments_is_still_the_diagnostic_dump(self):
        rc, out, _ = self._run([])
        self.assertEqual(rc, 0)
        self.assertIn("repo_root", out)

    def test_an_unknown_name_exits_2_with_nothing_on_stdout(self):
        rc, out, err = self._run(["nonsense"])
        self.assertEqual(rc, 2)
        self.assertEqual(out, "", "a caller doing VAR=$(...) must not capture an error as a path")
        self.assertIn("unknown path", err)

    def test_not_set_exits_1_with_nothing_on_stdout(self):
        """⛔ The fail-closed case. An empty capture plus a failed exit is recoverable; a plausible
        wrong folder is not."""
        saved = dict(os.environ)
        saved_harness = paths.brain_root.harness_root
        try:
            os.environ.pop(paths.brain_root.BRAIN_ROOT_ENV, None)
            os.environ["HOME"] = os.path.join(tempfile.gettempdir(), "lifehack-no-such-home")
            paths.brain_root.BRAIN_ROOT_CONFIG = os.path.join(os.environ["HOME"], "nope")
            paths.brain_root.BRAIN_ROOT_LEGACY_GLOB = ""
            # the pointer routes too — see TestNeverGuesses.setUp for why the env scrubbing above
            # never reached them
            paths.brain_root.harness_root = lambda: os.path.join(os.environ["HOME"], "no-such-harness")
            rc, out, err = self._run(["map"])
            self.assertEqual(rc, 1)
            self.assertEqual(out, "")
            self.assertIn("NOT-SET", err)
        finally:
            paths.brain_root.harness_root = saved_harness
            os.environ.clear()
            os.environ.update(saved)


if __name__ == "__main__":
    unittest.main()
