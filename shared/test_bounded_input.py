#!/usr/bin/env python3
"""test_bounded_input.py — the check that asks the question nobody asks.

Run:  python3 shared/test_bounded_input.py
      python3 -m unittest discover -s shared -p 'test_*.py'

Every completeness check ever written asks "did we get everything?" This one asks the other
question — "did we get ONLY that?" — and the reason it needs a test rather than a code review is
that its failure mode produces no symptom at all. A job that quietly processes ten times its work
does not crash, does not slow down, and produces output indistinguishable from a correct job that
was simply handed more to do. If this check stops working, nothing anywhere notices.

The cases below fall into three groups, and the third is the one that matters most:

  1. It catches the runaway. An id that was processed and never handed is refused, by name.
  2. It stays quiet on correct work — including the near-misses that a lazier check would refuse:
     duplicates in either list, a run that did less than it was asked, a run that did nothing.
  3. IT REFUSES TO EVALUATE RATHER THAN PASS VACUOUSLY. An empty handed list, a missing file, a
     count instead of a list — every one of these exits 2, never 0. This is the whole discipline:
     a check that cannot see its denominator must say so, because a vacuous pass and a real pass
     look identical in a log and only one of them means anything.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "bounded_input.py")
sys.path.insert(0, HERE)

WITHIN, REFUSED, CANNOT_EVALUATE = 0, 1, 2
HANDED = ["msg_aaa111", "msg_bbb222", "msg_ccc333"]


class BoundedInputCase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bounded-test-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, payload):
        p = os.path.join(self.tmp, name)
        with open(p, "w") as f:
            if isinstance(payload, str):
                f.write(payload)
            else:
                json.dump(payload, f)
        return p

    def run_check(self, handed, processed):
        h = handed if isinstance(handed, str) else self.write("handed.json", handed)
        p = processed if isinstance(processed, str) else self.write("processed.json", processed)
        return subprocess.run([sys.executable, TOOL, "--handed", h, "--processed", p],
                              capture_output=True, text=True)

    # ── 1. it catches the runaway ─────────────────────────────────────────────────────────────

    def test_an_id_that_was_never_handed_is_refused_and_named(self):
        r = self.run_check(HANDED, HANDED + ["msg_NEVER_HANDED"])
        self.assertEqual(r.returncode, REFUSED)
        self.assertIn("msg_NEVER_HANDED", r.stdout + r.stderr,
                      "naming the extra is the point — a count would send nobody anywhere")

    def test_the_backlog_case_the_incident_was_about(self):
        """The shape of the real failure: a job handed two things chews forty-five."""
        r = self.run_check(HANDED[:2], [f"msg_{i:04d}" for i in range(45)])
        self.assertEqual(r.returncode, REFUSED)

    # ── 2. it stays quiet on correct work, including the awkward cases ────────────────────────

    def test_an_exact_match_passes(self):
        self.assertEqual(self.run_check(HANDED, list(HANDED)).returncode, WITHIN)

    def test_doing_less_than_asked_is_reported_but_is_not_a_failure_here(self):
        """A drop and a runaway are different problems that send you down different pipelines.
        Conflating them costs an hour of looking in the wrong place."""
        r = self.run_check(HANDED, HANDED[:1])
        self.assertEqual(r.returncode, WITHIN)
        self.assertIn("under-processed", r.stdout)

    def test_doing_nothing_at_all_is_still_within_bounds(self):
        self.assertEqual(self.run_check(HANDED, []).returncode, WITHIN)

    def test_duplicates_on_either_side_do_not_change_the_answer(self):
        self.assertEqual(self.run_check(HANDED + [HANDED[0]], list(HANDED)).returncode, WITHIN)
        self.assertEqual(self.run_check(HANDED, [HANDED[0]] * 5).returncode, WITHIN)

    def test_a_duplicated_extra_is_counted_once(self):
        r = self.run_check(HANDED, ["msg_STRAY"] * 4)
        self.assertEqual(r.returncode, REFUSED)
        self.assertIn("1 --", r.stdout, "four copies of one stray id is one problem, not four")

    def test_the_shapes_a_caller_might_hand_it_all_work(self):
        for payload in ({"ids": HANDED}, {"items": [{"item_id": i} for i in HANDED]}, HANDED):
            with self.subTest(shape=type(payload).__name__ + str(list(payload)[:1])):
                self.assertEqual(self.run_check(payload, list(HANDED)).returncode, WITHIN)

    # ── 3. it refuses to evaluate rather than pass vacuously ──────────────────────────────────

    def test_an_empty_handed_list_is_never_a_pass(self):
        """⭐ THE ONE THAT MATTERS. With nothing handed, `processed - handed` is empty for ANY
        input, so the check would pass everything while appearing to work. A denominator of zero
        is not a clean bill of health, it is the absence of a question."""
        r = self.run_check([], HANDED)
        self.assertEqual(r.returncode, CANNOT_EVALUATE)
        self.assertIn("CANNOT EVALUATE", r.stderr)

    def test_a_count_instead_of_a_list_cannot_be_checked(self):
        """The convention this enforces: a run reports WHAT it touched, never HOW MANY. A number
        is an assertion by the thing under examination; a list can be diffed against the handoff.
        Hand this a count and it must refuse, not shrug and pass."""
        counted = self.write("counted.json", json.dumps({"processed_count": 3}))
        r = self.run_check(HANDED, counted)
        self.assertEqual(r.returncode, CANNOT_EVALUATE,
                         "a hand-composed count must never satisfy this check")

    def test_a_missing_file_is_never_a_pass(self):
        r = self.run_check(HANDED, os.path.join(self.tmp, "nothing-here.json"))
        self.assertEqual(r.returncode, CANNOT_EVALUATE)

    def test_unreadable_json_is_never_a_pass(self):
        broken = self.write("broken.json", "{ not json at all")
        self.assertEqual(self.run_check(HANDED, broken).returncode, CANNOT_EVALUATE)

    def test_no_arguments_is_never_a_pass(self):
        r = subprocess.run([sys.executable, TOOL], capture_output=True, text=True)
        self.assertEqual(r.returncode, CANNOT_EVALUATE)

    # ── the tool's own selftest, run as one case so it cannot rot unnoticed ───────────────────

    def test_the_built_in_selftest_passes(self):
        r = subprocess.run([sys.executable, TOOL, "--selftest"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("SELFTEST: PASS", r.stdout)

    # ── and the bound it cannot close, asserted so nobody later assumes it did ────────────────

    def test_it_genuinely_cannot_detect_a_forged_processed_list(self):
        """Not a gap to be fixed — a stated, measured limit, asserted here so that a future reader
        cannot mistake this check for something stronger than it is. A job that did nothing and
        copied its own work-list is byte-identical to a faithful run. Catching that needs a third
        witness that records the work as it happens; nothing here is one."""
        forged = self.write("forged.json", list(HANDED))    # a straight copy of the handoff
        self.assertEqual(self.run_check(HANDED, forged).returncode, WITHIN,
                         "if this ever starts failing, something stronger was built — update the "
                         "header, which currently says this is undecidable from these two inputs")


if __name__ == "__main__":
    unittest.main(verbosity=2)
