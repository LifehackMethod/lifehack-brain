#!/usr/bin/env python3
"""test_subject_basket_lockstep.py — a RE-cluster must move BOTH `subject` and `basket`, always.

Run:  python3 system/tools/cowork-ingest/test_subject_basket_lockstep.py

WHY THIS EXISTS — BUG #56, a split-brain between two tools that both read the corpus map but look at
different columns. `pipeline.py` routes work on `row["basket"]`; `basket_review.py` matches on
`row["subject"]`. `corpus_map.py do_set()` used to write ONLY `row["subject"] = a.subject` when a chat
was clustered (Pass-1 `set --subject`). `do_migrate()` seeds `basket` from `subject` ONLY while `basket`
is still falsy or the placeholder "UNCLUSTERED" — never over a real value (that guard is what
test_sort_to_baskets.py protects). So the FIRST `set --subject` looked fine (basket got seeded by the
next migrate), but a SECOND `set --subject` on the same chat — an ordinary re-cluster, no migrate
required to trigger it — moved `subject` and left `basket` stale. From then on, `pipeline.py` believed
the chat was still in the OLD pile while `basket_review.py` believed it was in the NEW one: one row, two
piles, depending which tool you asked.

The fix (corpus_map.py do_set, the `if getattr(a, "subject", None):` block) writes BOTH fields at that
one call site. This test re-clusters a chat TWICE and asserts both columns agree with the SECOND
(current) clustering — the exact sequence that exposed the split-brain.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CHAT = "meal-plan.txt"


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="subject-basket-test-")
        self.tags = os.path.join(self.tmp, "world-tags.json")
        self.map = os.path.join(self.tmp, "corpus-map.json")
        rows = [{"file": CHAT, "categories": ["canon"], "freshness": "fresh"}]
        with io.open(self.tags, "w", encoding="utf-8") as fh:
            json.dump({"rows": rows}, fh)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, cwd, tool, *args, env=None):
        r = subprocess.run([sys.executable, os.path.join(cwd, tool), *args],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def _row(self):
        with io.open(self.map, encoding="utf-8") as fh:
            m = json.load(fh)
        return m["rows"][CHAT]


class TestReclusterKeepsSubjectAndBasketInLockstep(Case):

    def test_first_cluster_sets_both(self):
        self.run_tool(HERE, "corpus_map.py", "init", "--tags", self.tags, "--out", self.map)
        self.run_tool(HERE, "corpus_map.py", "migrate", "--map", self.map)
        self.run_tool(HERE, "corpus_map.py", "set", "--map", self.map, "--file", CHAT,
                     "--subject", "cooking")
        row = self._row()
        self.assertEqual(row["subject"], "cooking")
        self.assertEqual(row["basket"], "cooking")

    def test_reclustering_moves_both_fields_not_just_subject(self):
        """The exact sequence that produced the split-brain: set once, then set AGAIN (a re-cluster,
        no migrate in between). Before the fix, `basket` stayed at the FIRST value while `subject`
        moved to the second — this is the assertion that must fail against that old behavior."""
        self.run_tool(HERE, "corpus_map.py", "init", "--tags", self.tags, "--out", self.map)
        self.run_tool(HERE, "corpus_map.py", "migrate", "--map", self.map)
        self.run_tool(HERE, "corpus_map.py", "set", "--map", self.map, "--file", CHAT,
                     "--subject", "cooking")
        self.run_tool(HERE, "corpus_map.py", "set", "--map", self.map, "--file", CHAT,
                     "--subject", "health")
        row = self._row()
        self.assertEqual(row["subject"], "health", "subject should reflect the re-cluster")
        self.assertEqual(row["basket"], "health",
                         "basket must move WITH subject on a re-cluster, or pipeline.py and "
                         "basket_review.py disagree about which pile this chat is in")

    def test_a_migrate_in_between_does_not_mask_the_bug(self):
        """Belt and braces: run migrate between the two sets too (a real session would, per
        1-sort.md). migrate's UNCLUSTERED-only reseed must not be what's carrying basket along —
        the write itself, in do_set, is what has to do it."""
        self.run_tool(HERE, "corpus_map.py", "init", "--tags", self.tags, "--out", self.map)
        self.run_tool(HERE, "corpus_map.py", "migrate", "--map", self.map)
        self.run_tool(HERE, "corpus_map.py", "set", "--map", self.map, "--file", CHAT,
                     "--subject", "cooking")
        self.run_tool(HERE, "corpus_map.py", "migrate", "--map", self.map)
        self.run_tool(HERE, "corpus_map.py", "set", "--map", self.map, "--file", CHAT,
                     "--subject", "health")
        row = self._row()
        self.assertEqual(row["subject"], "health")
        self.assertEqual(row["basket"], "health")


class TestProvesItCatchesTheOldBug(Case):
    """Runs the SAME test logic against a copy of corpus_map.py with the fix reverted (do_set writes
    only `subject`, mirroring the code before #56), to demonstrate the assertion above actually fails
    on the old behavior. This does not touch the real source file — it copies corpus_map.py + pipeline.py
    into a throwaway directory and patches the copy."""

    def setUp(self):
        super().setUp()
        self.buggy_dir = tempfile.mkdtemp(prefix="subject-basket-buggy-")
        for f in ("corpus_map.py", "pipeline.py"):
            shutil.copy(os.path.join(HERE, f), os.path.join(self.buggy_dir, f))
        buggy_path = os.path.join(self.buggy_dir, "corpus_map.py")
        with io.open(buggy_path, encoding="utf-8") as fh:
            src = fh.read()
        fixed = '        row["subject"] = a.subject\n        row["basket"] = a.subject\n'
        old = '        row["subject"] = a.subject\n'
        self.assertIn(fixed, src, "fixture is stale — do_set's write site changed shape; update this test")
        reverted = src.replace(fixed, old)
        self.assertNotEqual(reverted, src, "the revert did not apply — nothing was patched")
        with io.open(buggy_path, "w", encoding="utf-8") as fh:
            fh.write(reverted)

    def tearDown(self):
        shutil.rmtree(self.buggy_dir, ignore_errors=True)
        super().tearDown()

    def test_the_regression_test_fails_against_the_old_do_set(self):
        # pipeline.py resolves shared/brain_root.py relative to its OWN path (../../../shared), which
        # breaks once it's copied out to a throwaway dir — point PYTHONPATH at the real repo's shared/
        # so that unrelated resolver still imports; nothing under test lives there.
        real_shared = os.path.normpath(os.path.join(HERE, "..", "..", "..", "shared"))
        real_tools = os.path.normpath(os.path.join(HERE, ".."))  # for utf8_stdio
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([real_shared, real_tools, env.get("PYTHONPATH", "")])
        # Same sequence as test_a_migrate_in_between_does_not_mask_the_bug: a migrate reseeds `basket`
        # from `subject` after the FIRST set (basket goes UNCLUSTERED → cooking), so the second set is
        # what actually exercises the split-brain — basket is a REAL value ("cooking") at that point,
        # not the falsy/placeholder case migrate's own guard already covers.
        self.run_tool(self.buggy_dir, "corpus_map.py", "init", "--tags", self.tags, "--out", self.map,
                     env=env)
        self.run_tool(self.buggy_dir, "corpus_map.py", "migrate", "--map", self.map, env=env)
        self.run_tool(self.buggy_dir, "corpus_map.py", "set", "--map", self.map, "--file", CHAT,
                     "--subject", "cooking", env=env)
        self.run_tool(self.buggy_dir, "corpus_map.py", "migrate", "--map", self.map, env=env)
        self.run_tool(self.buggy_dir, "corpus_map.py", "set", "--map", self.map, "--file", CHAT,
                     "--subject", "health", env=env)
        row = self._row()
        self.assertEqual(row["subject"], "health", "subject still moves under the old code")
        with self.assertRaises(AssertionError,
                               msg="the old do_set left basket stale at 'cooking' — if this does NOT "
                                   "raise, the fixture no longer reproduces the split-brain"):
            self.assertEqual(row["basket"], "health")
        self.assertEqual(row["basket"], "cooking", "confirms the exact split-brain: two tools would "
                         "now disagree about which pile this chat is in")


if __name__ == "__main__":
    unittest.main(verbosity=2)
