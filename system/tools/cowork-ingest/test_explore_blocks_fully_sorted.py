#!/usr/bin/env python3
"""test_explore_blocks_fully_sorted.py — a basket parked entirely in EXPLORE must never be told
"fully sorted".

Run:  python3 system/tools/cowork-ingest/test_explore_blocks_fully_sorted.py

WHY THIS EXISTS — BUG #57. `scan_review.py cmd_show()` builds its ruling screen from
`pipeline._scanned_unruled()`, which deliberately EXCLUDES a chat already ruled 'explore'
(skim_verdict == "explore" — the human already looked once and asked for a wider second read; see
pipeline.py `_scanned_unruled` vs `_in_explore`). So a basket whose every remaining chat sits in the
EXPLORE stack computed `total == 0` and the old code printed the all-clear:
    ✓  "<name>" is fully sorted — nothing left to rule here.
Meanwhile `pipeline.set_basket_status`'s skim-complete gate independently REFUSES to close that same
basket while any chat is parked in EXPLORE. The human was told the pile was done while the machine
still blocked closing it — a false all-clear masking a real blocker.

The fix adds an EXPLORE-aware branch in the `total == 0` case: if `pipeline.basket_chats(m, basket,
pipeline._in_explore)` is non-empty, it prints a "NOT fully sorted — N chat(s) are parked in EXPLORE"
message instead of the all-clear, and never prints "fully sorted" in that case.

This file tests both sides, so the fix is proven to have ADDED a case rather than deleted the original
one: a basket genuinely fully sorted (no chats left at all, or every chat closed by toss/park) must
still get the all-clear.
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
EXPLORE_CHATS = {"weird-one.txt": "attic", "another-weird-one.txt": "attic"}
CLOSED_CHATS = {"clear-cut.txt": "attic", "also-clear.txt": "attic"}


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="explore-fully-sorted-test-")
        self.tags = os.path.join(self.tmp, "world-tags.json")
        self.map = os.path.join(self.tmp, "corpus-map.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, tool, *args, expect_ok=True):
        r = subprocess.run([sys.executable, os.path.join(HERE, tool), *args],
                           capture_output=True, text=True)
        if expect_ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def _seed(self, chats):
        rows = [{"file": f, "categories": ["canon"], "freshness": "fresh"} for f in chats]
        with io.open(self.tags, "w", encoding="utf-8") as fh:
            json.dump({"rows": rows}, fh)
        self.run_tool("corpus_map.py", "init", "--tags", self.tags, "--out", self.map)
        self.run_tool("corpus_map.py", "migrate", "--map", self.map)
        for f, subject in chats.items():
            self.run_tool("corpus_map.py", "set", "--map", self.map, "--file", f,
                          "--subject", subject)
        self.run_tool("corpus_map.py", "migrate", "--map", self.map)

    def show(self, basket):
        r = self.run_tool("scan_review.py", "show", "--map", self.map, "--basket", basket)
        return r.stdout


class TestABasketAllInExploreIsNotFullySorted(Case):

    def setUp(self):
        super().setUp()
        self._seed(EXPLORE_CHATS)
        for f in EXPLORE_CHATS:
            # give it a SCAN gist first (the ordinary path a real chat takes before it's ruled) …
            self.run_tool("pipeline.py", "scan", "--map", self.map, "--file", f,
                          "--summary", "a short gist of what this chat is about")
            # … then rule it EXPLORE — no --human-approved needed, explore closes nothing.
            self.run_tool("pipeline.py", "skim", "--map", self.map, "--file", f, "--verdict", "explore")

    def test_the_screen_does_not_claim_fully_sorted(self):
        out = self.show("attic")
        # "fully sorted" alone is not specific enough — the fixed NOT-fully-sorted message contains it
        # as a substring. Check the actual all-clear phrasing/marker instead.
        self.assertNotIn("✓", out, "the ✓ all-clear marker must not appear")
        self.assertNotIn("nothing left to rule here", out,
                         "a basket parked entirely in EXPLORE must never get the all-clear")

    def test_the_screen_reports_the_explore_parking_instead(self):
        out = self.show("attic")
        self.assertIn("NOT fully sorted", out)
        self.assertIn("EXPLORE", out)
        self.assertIn("2", out, "should report the count of parked chats (2)")

    def test_this_matches_what_the_real_gate_says(self):
        """The whole point of the fix: agree with set_basket_status's independent refusal, rather than
        contradicting it."""
        HERE_ = HERE
        sys.path.insert(0, HERE_)
        import importlib
        import pipeline
        importlib.reload(pipeline)
        m = pipeline.load(self.map)
        ok, msg = pipeline.set_basket_status(m, "attic", "skim-complete")
        self.assertFalse(ok, "the gate should also refuse to close this basket")
        self.assertIn("explore", msg.lower())


class TestAGenuinelySortedBasketStillGetsTheAllClear(Case):
    """Proves the fix ADDED a branch rather than silently deleting the original all-clear."""

    def setUp(self):
        super().setUp()
        self._seed(CLOSED_CHATS)
        for f in CLOSED_CHATS:
            self.run_tool("pipeline.py", "scan", "--map", self.map, "--file", f,
                          "--summary", "a short gist of what this chat is about")
            # toss CLOSES the chat (filing_status=declined) — this is what "actually done" looks like.
            self.run_tool("pipeline.py", "skim", "--map", self.map, "--file", f, "--verdict", "toss",
                         "--human-approved")

    def test_the_screen_says_fully_sorted(self):
        out = self.show("attic")
        self.assertIn("fully sorted", out)

    def test_the_screen_does_not_mention_explore_parking(self):
        out = self.show("attic")
        self.assertNotIn("NOT fully sorted", out)


class TestAnEmptyBasketStillGetsTheAllClear(Case):
    """The other genuinely-done shape: nothing was ever scanned into the basket at all."""

    def setUp(self):
        super().setUp()
        self._seed({"only-chat.txt": "attic"})
        # left completely untouched — no scan, no skim.

    def test_untouched_basket_is_not_reported_as_explore_parked(self):
        out = self.show("attic")
        self.assertNotIn("NOT fully sorted", out, "an untouched chat is not an EXPLORE chat")


class TestProvesItCatchesTheOldBug(Case):
    """Runs the all-EXPLORE case against a copy of scan_review.py with the #57 fix reverted (the
    `total == 0` branch always prints the all-clear, exactly as it did before), to demonstrate the
    positive assertions above actually fail on the old behavior. Does not touch the real source file —
    copies scan_review.py + pipeline.py into a throwaway directory and patches the copy."""

    def setUp(self):
        super().setUp()
        self.buggy_dir = tempfile.mkdtemp(prefix="explore-fully-sorted-buggy-")
        for f in ("scan_review.py", "pipeline.py"):
            shutil.copy(os.path.join(HERE, f), os.path.join(self.buggy_dir, f))
        target = os.path.join(self.buggy_dir, "scan_review.py")
        with io.open(target, encoding="utf-8") as fh:
            src = fh.read()
        # Delete everything from the "exploring = ..." check through its "return 0" — the WHOLE
        # #57 addition — leaving only the original unconditional all-clear print in the `total == 0`
        # branch (still present, byte-for-byte, in the tail of the file). This reproduces the exact
        # code shape that shipped before #57, without retyping any of its unicode literals by hand.
        marker_start = "        # ⚠ EXPLORE-AWARE BRANCH (#57)."
        marker_end = "        print(pipeline.compose_screen([f'  "
        start = src.index(marker_start)
        end = src.index(marker_end)
        self.assertGreater(end, start, "splice markers out of order — scan_review.py's shape changed")
        reverted = src[:start] + src[end:]
        self.assertNotEqual(reverted, src, "the revert did not change anything — check the splice points")
        self.assertNotIn("EXPLORE-AWARE BRANCH", reverted, "the old #57 branch is still present")
        self.assertNotIn("_in_explore", reverted, "the explore lookup should be fully removed")
        with io.open(target, "w", encoding="utf-8") as fh:
            fh.write(reverted)

    def tearDown(self):
        shutil.rmtree(self.buggy_dir, ignore_errors=True)
        super().tearDown()

    def _seed_and_explore(self):
        self._seed(EXPLORE_CHATS)
        for f in EXPLORE_CHATS:
            self.run_tool("pipeline.py", "scan", "--map", self.map, "--file", f,
                          "--summary", "a short gist of what this chat is about")
            self.run_tool("pipeline.py", "skim", "--map", self.map, "--file", f, "--verdict", "explore")

    def show_buggy(self, basket):
        real_shared = os.path.normpath(os.path.join(HERE, "..", "..", "..", "shared"))
        real_tools = os.path.normpath(os.path.join(HERE, ".."))  # for utf8_stdio
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([real_shared, real_tools, env.get("PYTHONPATH", "")])
        r = subprocess.run([sys.executable, os.path.join(self.buggy_dir, "scan_review.py"),
                            "show", "--map", self.map, "--basket", basket],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def test_the_old_code_falsely_claims_fully_sorted(self):
        self._seed_and_explore()
        out = self.show_buggy("attic")
        self.assertIn("fully sorted", out, "sanity: the reverted copy really does behave like the old code")
        with self.assertRaises(AssertionError,
                               msg="the old code printed the all-clear here — if this does NOT raise, "
                                   "the fixture no longer reproduces the false all-clear"):
            self.assertNotIn("nothing left to rule here", out)

    def test_the_old_code_never_mentions_explore_parking(self):
        self._seed_and_explore()
        out = self.show_buggy("attic")
        with self.assertRaises(AssertionError,
                               msg="the old code never told the human EXPLORE was blocking — if this "
                                   "does NOT raise, the fixture no longer reproduces the bug"):
            self.assertIn("NOT fully sorted", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
