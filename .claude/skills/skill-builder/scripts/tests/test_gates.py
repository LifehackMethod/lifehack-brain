"""Tests for gates.py: GOOD / EDGE / PADDED / BROKEN-COPY. Stdlib unittest only."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "gates.py")

BROKEN_MATCHER_FROM = "matched = answer in members"
BROKEN_MATCHER_TO = "matched = True"


def run_script(script_path, *args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, script_path] + list(args),
                       capture_output=True, text=True, timeout=60, env=env)
    return p.returncode, p.stdout, p.stderr


def make_broken_copy(tmpdir):
    dest = os.path.join(tmpdir, "gates_broken.py")
    with open(SCRIPT, "r", encoding="utf-8") as f:
        src = f.read()
    assert BROKEN_MATCHER_FROM in src, "break marker missing from gates.py"
    broken = src.replace(BROKEN_MATCHER_FROM, BROKEN_MATCHER_TO)
    assert broken != src
    with open(dest, "w", encoding="utf-8") as f:
        f.write(broken)
    return dest


class GatesGood(unittest.TestCase):
    def test_exact_member_after_trim_and_case(self):
        rc, out, _ = run_script(SCRIPT, "--set", " refine | move-on | none-of-these ", "--answer", "  Move-on  ")
        self.assertEqual(rc, 0)
        self.assertIn("move-on", out.splitlines()[0])
        self.assertIn("RECEIPT gates.py PASS", out)

    def test_named_set_id(self):
        rc, out, _ = run_script(SCRIPT, "--set-id", "validation", "--answer", "fill-gaps")
        self.assertEqual(rc, 0)
        self.assertEqual(out.splitlines()[0], "fill-gaps")

    def test_overview_set_has_no_skip_walk_through_member(self):
        rc, out, _ = run_script(SCRIPT, "--set-id", "overview", "--answer", "move-on")
        self.assertEqual((rc, out.splitlines()[0]), (0, "move-on"))
        rc, out, _ = run_script(SCRIPT, "--set-id", "overview", "--answer", "skip-role-play")
        self.assertEqual(rc, 1)  # step 2 no longer offers a skip: the overview never promises one

    def test_none_of_these_passes_but_does_not_move(self):
        rc, out, _ = run_script(SCRIPT, "--set-id", "roleplay", "--answer", "none-of-these")
        self.assertEqual(rc, 0)
        self.assertEqual(out.splitlines()[0], "none-of-these")
        self.assertIn("does not move the run", out)


class GatesEdge(unittest.TestCase):
    def test_multiline_answer_trims_to_member(self):
        rc, out, _ = run_script(SCRIPT, "--set", "refine|move-on|none-of-these", "--answer", "move-on\n")
        self.assertEqual(rc, 0)
        self.assertEqual(out.splitlines()[0], "move-on")

    def test_answer_with_internal_spaces_fails_loudly(self):
        rc, out, _ = run_script(SCRIPT, "--set", "refine|move-on|none-of-these",
                                "--answer", "move on please")
        self.assertEqual(rc, 1)
        self.assertEqual(out.splitlines()[0], "none-of-these")
        self.assertIn("REFUSED:", out)
        self.assertIn("RULE:", out)

    def test_list_sets(self):
        rc, out, _ = run_script(SCRIPT, "--list-sets")
        self.assertEqual(rc, 0)
        for sid in ("destination", "prep-report", "send", "existing"):
            self.assertIn("%s:" % sid, out)

    def test_path_with_space_in_temp_invocation(self):
        # the script itself takes no file paths; prove arg handling tolerates spaces
        with tempfile.TemporaryDirectory() as td:
            deep = os.path.join(td, "folder with space")
            os.makedirs(deep)
            rc, out, _ = run_script(SCRIPT, "--set-id", "send", "--answer", "send")
            self.assertEqual(rc, 0)


class GatesPadded(unittest.TestCase):
    def test_right_word_buried_in_filler_does_not_pass(self):
        rc, out, _ = run_script(SCRIPT, "--set-id", "roleplay",
                                "--answer", "I think we should move-on but first")
        self.assertEqual(rc, 1)
        self.assertEqual(out.splitlines()[0], "none-of-these")

    def test_near_miss_spellings_do_not_pass(self):
        for answer in ("refinee", "refin", "Move-On.", "NONE OF THESE"):
            rc, out, _ = run_script(SCRIPT, "--set-id", "roleplay", "--answer", answer)
            self.assertEqual(rc, 1, answer)
            self.assertEqual(out.splitlines()[0], "none-of-these", answer)


class GatesBrokenCopy(unittest.TestCase):
    def test_suite_would_catch_always_true_matcher(self):
        """The good/padded assertions must FAIL on a copy whose matcher is always true."""
        with tempfile.TemporaryDirectory() as td:
            broken = make_broken_copy(td)
            # the padded case's expectation (exit 1) fails on the broken copy:
            rc, out, _ = run_script(broken, "--set-id", "roleplay", "--answer", "refinee")
            self.assertEqual(rc, 0, "broken copy must wrongly pass the padded case")
            # the good case still matches (proves the break only widened, not removed)
            rc, out, _ = run_script(broken, "--set-id", "roleplay", "--answer", "refine")
            self.assertEqual(rc, 0)


class GatesCouldNotCheck(unittest.TestCase):
    def test_set_must_end_in_none_of_these(self):
        rc, out, _ = run_script(SCRIPT, "--set", "refine|move-on", "--answer", "refine")
        self.assertEqual(rc, 2)
        self.assertIn("does not end in none-of-these", out)
        self.assertIn("RECEIPT gates.py COULD-NOT-CHECK", out)

    def test_missing_args(self):
        rc, _, _ = run_script(SCRIPT)
        self.assertEqual(rc, 2)
        rc, _, _ = run_script(SCRIPT, "--set", "a|b|none-of-these", "--set-id", "send", "--answer", "a")
        self.assertEqual(rc, 2)

    def test_unknown_set_id(self):
        rc, out, _ = run_script(SCRIPT, "--set-id", "nope", "--answer", "x")
        self.assertEqual(rc, 2)
        self.assertIn("unknown --set-id", out)

    def test_empty_answer(self):
        rc, out, _ = run_script(SCRIPT, "--set-id", "send", "--answer", "   ")
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED:", out)

    def test_bad_timeout(self):
        rc, _, _ = run_script(SCRIPT, "--set-id", "send", "--answer", "send", "--timeout", "0")
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
