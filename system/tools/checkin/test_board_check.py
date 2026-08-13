#!/usr/bin/env python3
"""test_board_check.py — the check that audits what a session actually acts on.

Everything else in the check-in audits the GAUGE — is the status reading right, is it alone. This
one audits the QUEUE. The failure it exists for was measured: a brief's rungs were rewritten and
verified clean, and the very next session still did the wrong work, because the open bucket
underneath still queued a task the plan had already marked done. The operator had cleaned the one
surface being inspected, the check reported clean, and both were telling the truth.

So the cases that matter are the ones where it would report clean and be wrong, and the ones where
it would cry wolf on an honest board.

Run: python3 system/tools/checkin/test_board_check.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "board_check.py")

BOARD_CLEAN, STALE_OPEN, NO_BOARD, CANNOT_READ = 0, 2, 3, 4


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def write(self, name, text):
        p = os.path.join(self.d, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def brief(self, ground="▲ ground — start with `2.1`, the joiner.", open_items="- `2.1` does part three need a joiner?"):
        return self.write("brief.md",
                          "# B\n\n## 2. CURRENT STATE — the DECISION BOARD\n"
                          "▲ 10,000 — half built.\n▲ 5,000 — inside the assembly seam.\n"
                          + ground + "\n\n✅ LOCKED — parts one and two joined.\n"
                          + "❓ OPEN\n" + open_items + "\n\n## 4. STORY LOG\n- a thing\n")

    def plan(self, *tasks):
        body = "# Plan\n\n## Phase 2\n" + "\n".join(tasks) + "\n"
        return self.write("plan.md", body)

    def check(self, brief, plan):
        p = subprocess.run([sys.executable, TOOL, brief, "--plan", plan],
                           capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr


class Clean(Base):

    def test_an_open_item_the_plan_still_has_open_is_clean(self):
        b = self.brief()
        p = self.plan("- [ ] `2.1` write the joiner")
        rc, out = self.check(b, p)
        self.assertEqual(rc, BOARD_CLEAN, out)
        self.assertIn("BOARD-CLEAN", out)

    def test_a_rung_that_honestly_says_nothing_is_planned_is_clean_not_orphaned(self):
        # ⭐ Refusing an honest "nothing queued" would just train people to invent a fake id to
        # pass the check — which is worse than the thing being checked for.
        b = self.brief(ground="▲ ground — no task planned; run the planner.",
                       open_items="- is part three worth doing at all?")
        p = self.plan("- [ ] `2.1` write the joiner")
        rc, out = self.check(b, p)
        self.assertEqual(rc, BOARD_CLEAN, out)


class NeverAFalseClean(Base):

    def test_an_open_item_the_plan_marks_done_is_named(self):
        # ⭐ THE MEASURED FAILURE. The rung is fine; the queue underneath is stale, and the queue is
        # what the next session actually reads.
        b = self.brief()
        p = self.plan("- [x] `2.1` write the joiner")
        rc, out = self.check(b, p)
        self.assertEqual(rc, STALE_OPEN, out)
        self.assertIn("STALE-OPEN", out)
        self.assertIn("2.1", out, "the verdict must NAME the id, not just count it")

    def test_a_ground_rung_naming_a_task_the_plan_does_not_hold_is_orphaned(self):
        b = self.brief(ground="▲ ground — start with `9.9`, which nobody planned.")
        p = self.plan("- [ ] `2.1` write the joiner")
        rc, out = self.check(b, p)
        self.assertEqual(rc, STALE_OPEN, out)   # RUNG-ORPHANED shares the rc-2 "found a problem" code
        self.assertIn("RUNG-ORPHANED", out)
        self.assertIn("9.9", out)

    def test_a_missing_brief_is_cannot_read_never_clean(self):
        p = self.plan("- [ ] `2.1` x")
        rc, out = self.check(os.path.join(self.d, "nope.md"), p)
        self.assertEqual(rc, CANNOT_READ, out)
        self.assertIn("CANNOT-READ", out)

    def test_a_missing_plan_is_cannot_read_never_clean(self):
        b = self.brief()
        rc, out = self.check(b, os.path.join(self.d, "nope.md"))
        self.assertEqual(rc, CANNOT_READ, out)

    def test_an_empty_brief_is_cannot_read_not_an_empty_board(self):
        b = self.write("brief.md", "   \n\n")
        p = self.plan("- [ ] `2.1` x")
        rc, out = self.check(b, p)
        self.assertEqual(rc, CANNOT_READ, out)

    def test_an_unreadable_brief_is_cannot_read(self):
        b = self.brief()
        p = self.plan("- [ ] `2.1` x")
        os.chmod(b, 0o000)
        try:
            rc, out = self.check(b, p)
        finally:
            os.chmod(b, 0o644)
        self.assertEqual(rc, CANNOT_READ, out)

    def test_no_board_and_no_rung_is_its_own_verdict_not_a_pass(self):
        b = self.write("brief.md", "# B\n\n## 4. STORY LOG\n- a thing\n")
        p = self.plan("- [ ] `2.1` x")
        rc, out = self.check(b, p)
        self.assertEqual(rc, NO_BOARD, out)
        self.assertIn("NO-BOARD", out)

    def test_it_recognises_an_ordinary_markdown_checkbox_as_done(self):
        # ⚖ The shape this tool did NOT know until 2026-08-11. It only understood four ✅-emoji
        # forms, all of them one person's habit, so the commonest markdown convention on earth read
        # as not-done and a stale board came back clean.
        b = self.brief()
        for done in ("- [x] `2.1` write the joiner",
                     "* [X] 2.1 write the joiner",
                     "- `2.1` — DONE",
                     "## ✅ `2.1` write the joiner"):
            p = self.plan(done)
            rc, out = self.check(b, p)
            self.assertEqual(rc, STALE_OPEN, "%r did not read as done\n%s" % (done, out))

    def test_a_ticked_bullet_mentioning_an_id_mid_sentence_is_not_a_claim_about_it(self):
        b = self.brief()
        p = self.plan("- [x] rewrite the thing that `2.1` depends on")
        rc, out = self.check(b, p)
        self.assertEqual(rc, BOARD_CLEAN, out)


class DoesNotCryWolf(Base):

    def test_an_id_mentioned_mid_sentence_in_a_board_bullet_is_discussion_not_a_queue_entry(self):
        # A queue entry LEADS with its id. Matching an id anywhere reproduces the bug where a tool
        # matched its own description.
        b = self.brief(open_items="- should this be folded into the approach `2.1` used?")
        p = self.plan("- [x] `2.1` write the joiner")
        rc, out = self.check(b, p)
        self.assertEqual(rc, BOARD_CLEAN, out)

    def test_an_id_late_in_the_ground_rung_headline_is_still_found(self):
        # ⛔ The lead-only window is NOT applied to the rung: a rung is one prose sentence, so its
        # id naturally sits mid-sentence. Applying the window here was a live false positive — a
        # correct rung flipped to orphaned by one character, carrying a reason key that lied.
        b = self.brief(ground="▲ ground — PHASE 2, and the place to begin is `2.1`, the joiner.")
        p = self.plan("- [ ] `2.1` write the joiner")
        rc, out = self.check(b, p)
        self.assertEqual(rc, BOARD_CLEAN, out)

    def test_the_first_id_in_the_rung_is_the_named_next_action(self):
        b = self.brief(ground="▲ ground — start with `2.1`, then `2.2` and `2.3`.")
        p = self.plan("- [ ] `2.1` a", "- [ ] `2.2` b", "- [ ] `2.3` c")
        rc, out = self.check(b, p)
        self.assertEqual(rc, BOARD_CLEAN, out)


class EmptyBucketMarker(unittest.TestCase):
    """A bucket can say it is deliberately empty without that counting as work.

    The ground rung already had this (`no task planned`); the three board buckets did not, so
    "- (nothing open right now)" was counted as a real open item. The risk in fixing it is the
    opposite error — swallowing a genuine item that happens to open with "nothing" or "none" —
    so both directions are pinned here.
    """

    def marker(self, line):
        sys.path.insert(0, HERE)
        import board_check
        return board_check.is_empty_bucket_marker(line)

    def test_explicit_empty_markers_are_not_items(self):
        for line in ("- (nothing open right now)", "- none", "- (none)", "- nothing yet",
                     "- N/A", "- no items", "- [empty]", "* nothing"):
            self.assertTrue(self.marker(line), f"should be treated as empty: {line!r}")

    def test_real_items_starting_with_an_empty_word_still_count(self):
        for line in ("- Nothing ships until pricing is signed off",
                     "- none of the vendors replied, chase them",
                     "- No decision yet on the pricing tier"):
            self.assertFalse(self.marker(line), f"should stay an item: {line!r}")

    def test_ordinary_items_are_unaffected(self):
        for line in ("- fix the login bug", "- decide on pricing"):
            self.assertFalse(self.marker(line), f"should stay an item: {line!r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
