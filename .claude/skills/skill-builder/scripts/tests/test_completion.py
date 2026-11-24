"""Tests for completion.py: GOOD / EDGE / PADDED / BROKEN-COPY. Stdlib unittest only."""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "completion.py")

BROKEN_DONE_FROM = 'if verdict == "done":'
BROKEN_DONE_TO = 'if True or verdict == "done":'

SPEC = """# draft spec — receipt sorter

## COVER SHEET
- **Skill name:** receipt sorter (D1)
- **One-liner:** <one line what it does>

## 1. WHAT THIS SKILL IS FOR
- The person it serves: actors and freelancers [inferred]
- This skill runs only after /x has finished (D2)
- The screen shows one line per receipt (D3) [stale]
- The prompt file lives at prompts/step-1.md [builder's choice]

## 8. OPEN — NOT YET DECIDED
1. **Where do unsorted receipts go?** Recommendation: a holding folder · Confidence: medium · Load-bearing: high
"""

# hand-computed over SPEC:
#   done: D1, D2, builder's choice            = 3
#   not done: blank, inferred, stale, §8 item = 4
#   total = 7 → figure = round(300/7) = 43 → bar round(43/10) = 4 filled
EXPECTED_LINE = "▰▰▰▰▱▱▱▱▱▱ 43% · *not ready to move on*"


def run_script(script_path, *args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, script_path] + list(args),
                       capture_output=True, text=True, timeout=60, env=env)
    return p.returncode, p.stdout, p.stderr


def make_broken_copy(tmpdir):
    dest = os.path.join(tmpdir, "completion_broken.py")
    with open(SCRIPT, "r", encoding="utf-8") as f:
        src = f.read()
    assert BROKEN_DONE_FROM in src, "break marker missing from completion.py"
    broken = src.replace(BROKEN_DONE_FROM, BROKEN_DONE_TO)
    assert broken != src
    with open(dest, "w", encoding="utf-8") as f:
        f.write(broken)
    return dest


class CompletionGood(unittest.TestCase):
    def test_figure_line(self):
        with tempfile.TemporaryDirectory() as td:
            spec = os.path.join(td, "spec.md")
            with open(spec, "w", encoding="utf-8") as f:
                f.write(SPEC)
            rc, out, _ = run_script(SCRIPT, "--spec", spec)
            self.assertEqual(rc, 0)
            self.assertEqual(out.splitlines()[0], EXPECTED_LINE)
            self.assertIn("RECEIPT completion.py PASS", out)

    def test_high_figure_gets_probandly_okay_phrase(self):
        text = "\n".join("- line %d (D%d)" % (i, i) for i in range(1, 10)) + \
               "\n\n## 8. OPEN — NOT YET DECIDED\n"
        with tempfile.TemporaryDirectory() as td:
            spec = os.path.join(td, "spec.md")
            with open(spec, "w", encoding="utf-8") as f:
                f.write(text)
            rc, out, _ = run_script(SCRIPT, "--spec", spec)
            self.assertEqual(rc, 0)
            self.assertEqual(out.splitlines()[0], "▰▰▰▰▰▰▰▰▰▰ 100% · *probably okay to move on*")


class CompletionEdge(unittest.TestCase):
    def test_path_with_a_space(self):
        with tempfile.TemporaryDirectory() as td:
            spec = os.path.join(td, "my draft spec.md")
            with open(spec, "w", encoding="utf-8") as f:
                f.write(SPEC)
            rc, out, _ = run_script(SCRIPT, "--spec", spec)
            self.assertEqual(rc, 0)
            self.assertEqual(out.splitlines()[0], EXPECTED_LINE)

    def test_multiline_value_line_counts(self):
        text = "- The answer spans two lines:\n  second line carries the citation (D5)\n"
        with tempfile.TemporaryDirectory() as td:
            spec = os.path.join(td, "spec.md")
            with open(spec, "w", encoding="utf-8") as f:
                f.write(text)
            rc, out, _ = run_script(SCRIPT, "--spec", spec)
            self.assertEqual(rc, 0)
            self.assertIn("100%", out)

    def test_empty_spec_prints_nothing_exits_zero(self):
        with tempfile.TemporaryDirectory() as td:
            spec = os.path.join(td, "empty.md")
            open(spec, "w", encoding="utf-8").close()
            rc, out, _ = run_script(SCRIPT, "--spec", spec)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")


class CompletionPadded(unittest.TestCase):
    def test_right_words_buried_in_filler(self):
        # [inferred] anywhere on the line keeps it unconfirmed, even mid-sentence
        line = "- The legend describes how the [inferred] marker is removed on confirmation (D9)\n"
        with tempfile.TemporaryDirectory() as td:
            spec = os.path.join(td, "spec.md")
            with open(spec, "w", encoding="utf-8") as f:
                f.write(line)
            rc, out, _ = run_script(SCRIPT, "--spec", spec)
            self.assertEqual(rc, 0)
            self.assertIn("0%", out)

    def test_planner_and_ready_sections_not_counted(self):
        text = SPEC + "\n## FOR THE PLANNER AND THE BUILD\n- [ ] something the build does (D1)\n" \
                       "\n## READY FOR THE PLANNER?\n- How complete this spec is: computed by code (D2) [builder's choice]\n"
        with tempfile.TemporaryDirectory() as td:
            spec = os.path.join(td, "spec.md")
            with open(spec, "w", encoding="utf-8") as f:
                f.write(text)
            rc, out, _ = run_script(SCRIPT, "--spec", spec)
            self.assertEqual(rc, 0)
            self.assertEqual(out.splitlines()[0], EXPECTED_LINE)  # unchanged figure

    def test_example_lines_and_prose_not_counted(self):
        text = "*Example:* `D1 · 2026-11-24 · amounts exactly as written (their request)`\n" \
               "A plain prose paragraph with no line-kind mark and no citation at all.\n"
        with tempfile.TemporaryDirectory() as td:
            spec = os.path.join(td, "spec.md")
            with open(spec, "w", encoding="utf-8") as f:
                f.write(text)
            rc, out, _ = run_script(SCRIPT, "--spec", spec)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_stale_is_never_done_even_when_confirmed(self):
        text = "- Filled and cited (D1) [stale]\n"
        with tempfile.TemporaryDirectory() as td:
            spec = os.path.join(td, "spec.md")
            with open(spec, "w", encoding="utf-8") as f:
                f.write(text)
            rc, out, _ = run_script(SCRIPT, "--spec", spec)
            self.assertEqual(rc, 0)
            self.assertIn("0%", out)


class CompletionBrokenCopy(unittest.TestCase):
    def test_suite_would_catch_everything_counts_done(self):
        """Good/padded figure assertions must FAIL on a copy where every slot counts done."""
        with tempfile.TemporaryDirectory() as td:
            broken = make_broken_copy(td)
            with tempfile.TemporaryDirectory() as td2:
                spec = os.path.join(td2, "spec.md")
                with open(spec, "w", encoding="utf-8") as f:
                    f.write(SPEC)
                rc, out, _ = run_script(broken, "--spec", spec)
                self.assertEqual(rc, 0)
                self.assertNotEqual(out.splitlines()[0], EXPECTED_LINE,
                                    "broken copy must not reproduce the true figure")
                # deterministic broken behaviour: every classified slot counts done (6 of 7)
                self.assertIn("▰▰▰▰▰▰▰▰▰▱ 86%", out)


class CompletionCouldNotCheck(unittest.TestCase):
    def test_missing_spec_file(self):
        rc, out, _ = run_script(SCRIPT, "--spec", "/nonexistent/no-spec.md")
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED:", out)
        self.assertIn("RECEIPT completion.py COULD-NOT-CHECK", out)

    def test_bad_args(self):
        rc, _, _ = run_script(SCRIPT)
        self.assertEqual(rc, 2)
        rc, _, _ = run_script(SCRIPT, "--spec", "/nonexistent/x.md", "--timeout", "0")
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
