#!/usr/bin/env python3
"""test_topic_check.py — the two PHASE 4 vocabulary gates must agree, always.

Run:  python3 system/tools/cowork-ingest/test_topic_check.py

WHY THIS EXISTS: PHASE 4 runs two tools six lines apart in the same phase file — `folder_scaffold.py`
(scaffolds the folder) and `pipeline.py topic-check` (gates the frontmatter). Until 2026-08-11 they
resolved the vocabulary differently: one looked beside the person's material, the other only inside the
repo. So `folder_scaffold` would accept a slug that `topic-check` then refused, minutes later, in the
same phase. The fix was to make one import the other; these tests are what stops them separating again.
"""

import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import folder_scaffold  # noqa: E402
import pipeline  # noqa: E402

VOCAB = """# my topics

- `financial`
- `health`
- `writing`

## Not topics — use `record_type:` instead
- `research-consensus`
"""


class VocabCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="topic-check-test-")
        self.vocab = os.path.join(self.tmp, "topic-vocab.md")
        with io.open(self.vocab, "w", encoding="utf-8") as f:
            f.write(VOCAB)
        # Point both resolvers at throwaway paths so a developer's real vocabulary is never consulted
        # and the in-repo legacy path (which must not exist) is never confused with a temp file.
        self._saved = (folder_scaffold.VOCAB_PATH, folder_scaffold.REPO_VOCAB_PATH,
                       folder_scaffold.LEGACY_VOCAB_PATH)
        folder_scaffold.VOCAB_PATH = os.path.join(self.tmp, "data", "memory", "topic-vocab.md")
        folder_scaffold.REPO_VOCAB_PATH = os.path.join(self.tmp, "repo", "memory", "topic-vocab.md")
        folder_scaffold.LEGACY_VOCAB_PATH = os.path.join(self.tmp, "repo", "system", "topic-vocab.md")

    def tearDown(self):
        (folder_scaffold.VOCAB_PATH, folder_scaffold.REPO_VOCAB_PATH,
         folder_scaffold.LEGACY_VOCAB_PATH) = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _plant(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        shutil.copy(self.vocab, path)


class TestResolutionOrder(VocabCase):

    def test_nothing_resolves_when_nothing_exists(self):
        resolved, tried = pipeline.resolve_topic_vocab()
        self.assertIsNone(resolved)
        self.assertEqual(len(tried), 3, "every rung should be reported as tried, so the refusal can name them")

    def test_explicit_wins(self):
        self._plant(folder_scaffold.VOCAB_PATH)
        resolved, _ = pipeline.resolve_topic_vocab(self.vocab)
        self.assertEqual(resolved, self.vocab)

    def test_the_persons_own_beats_the_legacy_in_repo_copy(self):
        self._plant(folder_scaffold.VOCAB_PATH)
        self._plant(folder_scaffold.LEGACY_VOCAB_PATH)
        resolved, _ = pipeline.resolve_topic_vocab()
        self.assertEqual(resolved, folder_scaffold.VOCAB_PATH)

    def test_the_data_root_beats_the_in_repo_back_compat_copy(self):
        """Their notes moved out of the repo; a vocabulary left behind in the old place must not win."""
        self._plant(folder_scaffold.VOCAB_PATH)
        self._plant(folder_scaffold.REPO_VOCAB_PATH)
        resolved, _ = pipeline.resolve_topic_vocab()
        self.assertEqual(resolved, folder_scaffold.VOCAB_PATH)

    def test_an_in_repo_vocabulary_still_works_for_an_existing_install(self):
        self._plant(folder_scaffold.REPO_VOCAB_PATH)
        resolved, _ = pipeline.resolve_topic_vocab()
        self.assertEqual(resolved, folder_scaffold.REPO_VOCAB_PATH)

    def test_legacy_in_repo_still_resolves_for_an_existing_install(self):
        self._plant(folder_scaffold.LEGACY_VOCAB_PATH)
        resolved, _ = pipeline.resolve_topic_vocab()
        self.assertEqual(resolved, folder_scaffold.LEGACY_VOCAB_PATH)

    def test_both_gates_resolve_to_the_same_file(self):
        """The whole point. If this ever fails, PHASE 4 contradicts itself again."""
        self._plant(folder_scaffold.VOCAB_PATH)
        self.assertEqual(pipeline.resolve_topic_vocab()[0], folder_scaffold.resolve_vocab()[0])


class TestMembership(VocabCase):

    def test_a_known_slug_passes(self):
        ok, bad, vocab = pipeline.validate_topics(["financial"], vocab_path=self.vocab)
        self.assertTrue(ok, bad)
        self.assertEqual(bad, [])

    def test_an_unknown_slug_fails(self):
        ok, bad, _ = pipeline.validate_topics(["financial", "astrology"], vocab_path=self.vocab)
        self.assertFalse(ok)
        self.assertEqual(bad, ["astrology"])

    def test_no_vocabulary_at_all_fails_closed(self):
        """'Could not check' must never read as 'passes'."""
        ok, bad, vocab = pipeline.validate_topics(["financial"])
        self.assertFalse(ok)
        self.assertIsNone(vocab)

    def test_entries_under_not_topics_are_not_slugs(self):
        """`research-consensus` is a record_type marker. It parses like a slug and must not be one."""
        ok, bad, _ = pipeline.validate_topics(["research-consensus"], vocab_path=self.vocab)
        self.assertFalse(ok, "the parser must stop at the '## Not topics' heading")

    def test_the_two_gates_accept_the_same_set(self):
        self.assertEqual(pipeline.load_topic_vocab(self.vocab), folder_scaffold.load_vocab(self.vocab))


class TestCliRefusalTeaches(VocabCase):
    """A refusal that does not say what to do next sends someone hunting for a file that was never
    supposed to exist. That happened to a real person; this is the regression test."""

    def _run(self, *args, env_extra=None):
        env = dict(os.environ)
        env["HOME"] = os.path.join(self.tmp, "home")
        env.update(env_extra or {})
        return subprocess.run([sys.executable, os.path.join(HERE, "pipeline.py"), "topic-check", *args],
                              capture_output=True, text=True, env=env)

    def _run_probe(self, env_extra=None):
        """A fresh subprocess (never touched by VocabCase.setUp's in-process monkeypatch) that
        imports folder_scaffold for real and prints whatever `resolve_vocab(None)` resolves to,
        or nothing. Used only by the issue #79 fix in test_missing_vocabulary_exits_1_and_teaches
        to ask what the real CLI subprocess would see, under the identical env, before asserting
        anything about it."""
        env = dict(os.environ)
        env["HOME"] = os.path.join(self.tmp, "home")
        env.update(env_extra or {})
        code = ("import sys; sys.path.insert(0, %r); import folder_scaffold; "
                "p, _tried = folder_scaffold.resolve_vocab(None); print(p or '')") % HERE
        return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)

    def test_missing_vocabulary_exits_1_and_teaches(self):
        # issue #79: this ran `pipeline.py topic-check` as a SEPARATE subprocess with only $HOME
        # overridden. `resolve_vocab()` treats an explicit --vocab as the FIRST candidate, not the
        # ONLY one (by design — see folder_scaffold.resolve_vocab's docstring) — on a miss it falls
        # through to <brain root>/memory/topic-vocab.md, then the in-repo copy. $HOME being
        # overridden only neutralises the PERSISTED-config route to the brain root; it does nothing
        # about $LIFEHACK_ROOT (if exported in the real shell), this repo's own gitignored
        # `.brain-root` pointer, or a real `memory/topic-vocab.md` a developer happens to have
        # locally (also gitignored — see TestNoVocabularyShips, which only guards the in-repo
        # LEGACY path, not this one). Whichever of those resolves on the machine running this
        # suite, the subprocess would silently check against THAT vocabulary instead of refusing —
        # this test asserted a REFUSAL either way, so it could pass or fail purely on machine state.
        #
        # Fix (smaller than changing resolve_vocab()'s shipped fallthrough — see the note in
        # folder_scaffold.py:resolve_vocab about why that fallthrough is deliberate, not a bug):
        # neutralise $LIFEHACK_ROOT explicitly (cheap, always safe) and, for the one route that
        # can't be neutralised via env at all — a real vocabulary genuinely present at the brain
        # root or in-repo — verify first that none exists rather than mutate or hide anyone's real
        # file. If one does, the REFUSAL path this test exists to lock in cannot be exercised
        # honestly here, so it SKIPS with a stated reason instead of asserting past it.
        env_extra = {"LIFEHACK_ROOT": os.path.join(self.tmp, "definitely-does-not-exist")}
        # Probe with the EXACT env the real CLI subprocess below will run under (same HOME
        # override, same neutralised LIFEHACK_ROOT) — a fresh process, never touched by setUp()'s
        # in-process monkeypatch, so this asks precisely what the CLI subprocess would resolve
        # with no explicit --vocab: the brain-root route, then the two in-repo fallbacks.
        probe = self._run_probe(env_extra=env_extra)
        real_vocab_path = probe.stdout.strip() or None
        if real_vocab_path:
            self.skipTest(
                f"a real topic vocabulary already resolves on this machine ({real_vocab_path}) — "
                "the CLI would legitimately fall through to it, so the REFUSED-with-no-vocabulary "
                "path this test checks cannot be exercised here without touching a real file "
                "(issue #79)."
            )
        r = self._run("--topics", "financial", "--vocab", os.path.join(self.tmp, "nope.md"),
                      env_extra=env_extra)
        self.assertEqual(r.returncode, 1)
        out = r.stdout + r.stderr
        self.assertIn("no topic vocabulary found", out)
        self.assertIn("memory/topic-vocab.md", out, "it must say where to put one")
        self.assertIn("will not invent one", out, "it must say it will not guess")
        self.assertIn("nope.md", out, "it must name every path it tried")

    def test_a_known_slug_exits_0(self):
        r = self._run("--topics", "financial", "--vocab", self.vocab)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK topic-check", r.stdout)

    def test_an_unknown_slug_exits_1_and_names_the_file(self):
        r = self._run("--topics", "astrology", "--vocab", self.vocab)
        self.assertEqual(r.returncode, 1)
        self.assertIn("astrology", r.stdout + r.stderr)
        self.assertIn(self.vocab, r.stdout + r.stderr, "it must name the vocabulary it checked against")


class TestNoVocabularyShips(unittest.TestCase):

    def test_the_repo_carries_no_topic_vocabulary(self):
        """Shipping one hands every student someone else's categories. If this file ever appears,
        something re-introduced the thing folder_scaffold.py:39-53 rules out."""
        repo = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
        self.assertFalse(os.path.exists(os.path.join(repo, "system", "topic-vocab.md")),
                         "system/topic-vocab.md must not ship — the vocabulary is the person's own")


if __name__ == "__main__":
    unittest.main(verbosity=2)
