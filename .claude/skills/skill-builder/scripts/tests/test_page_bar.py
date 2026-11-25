"""Tests for page_bar.py: GOOD / EDGE / PADDED / BROKEN-COPY. Stdlib unittest only."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "page_bar.py")

# Two deliberate breaks, each must make a named test fail (seen failing first, no AI involved).
BREAK_DONE_FROM = "        if p in done:\n            cells.append(DONE)"
BREAK_DONE_TO = "        if False and p in done:\n            cells.append(DONE)"
BREAK_YES_FROM = "if not a.said or not a.said.strip():"
BREAK_YES_TO = "if False:"


def run(script, *args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, script] + list(args), capture_output=True, text=True, timeout=60, env=env)
    return p.returncode, p.stdout.strip(), p.stderr


def make_broken_copy(td, frm, to):
    dest = os.path.join(td, "page_bar_broken.py")
    with open(SCRIPT, "r", encoding="utf-8") as f:
        src = f.read()
    assert frm in src, "break marker missing from page_bar.py"
    with open(dest, "w", encoding="utf-8") as f:
        f.write(src.replace(frm, to))
    return dest


def init4(script, td):
    return run(script, "init", "--workdir", td, "--section", "walk", "--label", "Walk-through", "--total", "4")


def mark_done(script, td, page, said="yes, that's right"):
    return run(script, "done", "--workdir", td, "--section", "walk", "--page", str(page), "--said", said)


def bar(script, td):
    return run(script, "bar", "--workdir", td, "--section", "walk")


class PageBarGood(unittest.TestCase):
    def test_zero_of_four(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(init4(SCRIPT, td)[:2], (0, "Walk-through · page 1 of 4   ▶ ⬜ ⬜ ⬜"))
            self.assertEqual(bar(SCRIPT, td)[:2], (0, "Walk-through · page 1 of 4   ▶ ⬜ ⬜ ⬜"))

    def test_two_of_four_with_current_page(self):
        with tempfile.TemporaryDirectory() as td:
            init4(SCRIPT, td)
            mark_done(SCRIPT, td, 1)
            mark_done(SCRIPT, td, 2)
            rc, out, _ = run(SCRIPT, "current", "--workdir", td, "--section", "walk", "--page", "3")
            self.assertEqual((rc, out), (0, "Walk-through · page 3 of 4   ✅ ✅ ▶ ⬜"))
            self.assertEqual(bar(SCRIPT, td)[1], "Walk-through · page 3 of 4   ✅ ✅ ▶ ⬜")

    def test_the_spec_example_page_two(self):
        with tempfile.TemporaryDirectory() as td:
            init4(SCRIPT, td)
            mark_done(SCRIPT, td, 1)
            run(SCRIPT, "current", "--workdir", td, "--section", "walk", "--page", "2")
            self.assertEqual(bar(SCRIPT, td)[1], "Walk-through · page 2 of 4   ✅ ▶ ⬜ ⬜")

    def test_all_done(self):
        with tempfile.TemporaryDirectory() as td:
            init4(SCRIPT, td)
            for p in (1, 2, 3, 4):
                mark_done(SCRIPT, td, p)
            self.assertEqual(bar(SCRIPT, td)[1], "Walk-through · all 4 pages done   ✅ ✅ ✅ ✅")


class PageBarEdge(unittest.TestCase):
    def test_current_page_already_done_says_so(self):
        with tempfile.TemporaryDirectory() as td:
            init4(SCRIPT, td)
            mark_done(SCRIPT, td, 1)
            run(SCRIPT, "current", "--workdir", td, "--section", "walk", "--page", "1")
            self.assertEqual(bar(SCRIPT, td)[1], "Walk-through · page 1 of 4 · done   ✅ ⬜ ⬜ ⬜")

    def test_page_out_of_range_refused(self):
        with tempfile.TemporaryDirectory() as td:
            init4(SCRIPT, td)
            for page in ("0", "5"):
                rc, _, err = run(SCRIPT, "current", "--workdir", td, "--section", "walk", "--page", page)
                self.assertEqual(rc, 1)
                self.assertIn("outside 1..4", err)
            self.assertEqual(mark_done(SCRIPT, td, 9)[0], 1)

    def test_init_twice_refused_until_reset(self):
        with tempfile.TemporaryDirectory() as td:
            init4(SCRIPT, td)
            mark_done(SCRIPT, td, 1)
            self.assertEqual(init4(SCRIPT, td)[0], 1)
            self.assertEqual(bar(SCRIPT, td)[1], "Walk-through · page 1 of 4 · done   ✅ ⬜ ⬜ ⬜")  # untouched
            rc, out, _ = run(SCRIPT, "init", "--workdir", td, "--section", "walk", "--label", "Walk-through",
                             "--total", "3", "--reset")
            self.assertEqual((rc, out), (0, "Walk-through · page 1 of 3   ▶ ⬜ ⬜"))

    def test_unknown_section_and_missing_folder(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(run(SCRIPT, "bar", "--workdir", td, "--section", "nope")[0], 1)
            self.assertEqual(run(SCRIPT, "bar", "--workdir", os.path.join(td, "gone"), "--section", "x")[0], 2)

    def test_corrupt_page_file_is_could_not_check(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "pages.json"), "w", encoding="utf-8") as f:
                f.write("{not json")
            self.assertEqual(bar(SCRIPT, td)[0], 2)

    def test_path_with_a_space_and_a_second_section(self):
        with tempfile.TemporaryDirectory() as td:
            wd = os.path.join(td, "my packet")
            os.mkdir(wd)
            init4(SCRIPT, wd)
            rc, out, _ = run(SCRIPT, "init", "--workdir", wd, "--section", "find", "--label", "Findings", "--total", "2")
            self.assertEqual((rc, out), (0, "Findings · page 1 of 2   ▶ ⬜"))
            self.assertEqual(bar(SCRIPT, wd)[1], "Walk-through · page 1 of 4   ▶ ⬜ ⬜ ⬜")


class PageBarPadded(unittest.TestCase):
    def test_no_yes_no_tick(self):
        with tempfile.TemporaryDirectory() as td:
            init4(SCRIPT, td)
            for said in ("", "   "):
                rc, _, err = mark_done(SCRIPT, td, 2, said)
                self.assertEqual(rc, 1)
                self.assertIn("played-back yes", err)
            self.assertNotIn("✅", bar(SCRIPT, td)[1])

    def test_yes_is_saved_in_its_own_file_and_never_touches_the_runner_record(self):
        with tempfile.TemporaryDirectory() as td:
            rec = os.path.join(td, "record.jsonl")
            with open(rec, "w", encoding="utf-8") as f:
                f.write('{"ev":"start"}\n')
            init4(SCRIPT, td)
            mark_done(SCRIPT, td, 2, "yes, that's it")
            with open(rec, encoding="utf-8") as f:
                self.assertEqual(f.read(), '{"ev":"start"}\n')
            with open(os.path.join(td, "pages.json"), encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["sections"]["walk"]["done"]["2"]["said"], "yes, that's it")
            self.assertEqual(sorted(os.listdir(td)), ["pages.json", "record.jsonl"])  # no stray temp files


class PageBarBrokenCopy(unittest.TestCase):
    def test_broken_bar_that_never_ticks_is_caught(self):
        with tempfile.TemporaryDirectory() as td:
            broken = make_broken_copy(td, BREAK_DONE_FROM, BREAK_DONE_TO)
            wd = os.path.join(td, "w")
            os.mkdir(wd)
            init4(broken, wd)
            mark_done(broken, wd, 1)
            run(broken, "current", "--workdir", wd, "--section", "walk", "--page", "2")
            got = bar(broken, wd)[1]
            self.assertNotEqual(got, "Walk-through · page 2 of 4   ✅ ▶ ⬜ ⬜")  # the real tests would FAIL on this copy
            self.assertNotIn("✅", got)

    def test_broken_yes_check_is_caught(self):
        with tempfile.TemporaryDirectory() as td:
            broken = make_broken_copy(td, BREAK_YES_FROM, BREAK_YES_TO)
            wd = os.path.join(td, "w")
            os.mkdir(wd)
            init4(broken, wd)
            rc, _, _ = mark_done(broken, wd, 2, "")
            self.assertEqual(rc, 0)  # the broken copy ticks with no yes: the real script refuses (rc 1)
            self.assertEqual(mark_done(SCRIPT, wd, 3, "")[0], 1)


if __name__ == "__main__":
    unittest.main()
