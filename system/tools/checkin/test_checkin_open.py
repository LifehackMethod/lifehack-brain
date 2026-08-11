#!/usr/bin/env python3
"""
test_checkin_open.py — unittest fixtures for checkin_open.py's `print` and `hint` verbs.

REWRITTEN 2026-08-06 on the proven-live bug: the old single `rungs` command did
`if MARKER in line` (▲) over the WHOLE FILE, so three lines of ordinary prose
elsewhere in a real brief that merely MENTIONED the ▲ glyph (describing this very
tool) got counted as rungs, returning PARTIAL-RUNGS 6 on a brief with an entirely
healthy 3-rung §2. The fix replaces the symbol-hunt with two verbs:

  `print <brief> --start N --end M`  — CALLER-SUPPLIED range, mechanical, scoped.
                                        The LLM has already read the brief and
                                        knows which lines are the rung block.
  `hint <brief>`                     — PERMISSIVE, file-wide, advisory only, so
                                        the LLM can find candidate line numbers.
                                        Never a verdict token; costs nothing to
                                        be wrong because nothing acts on it alone.

Every assertion checks the exit code AND an EXACT-MATCH of the verdict token
parsed off the first line of stdout — never a substring (gauge_check.py's test
suite already documents why: 'GAUGE' in out would pass for both of that tool's
gauge verdicts; the analogous trap here is 'RUNGS' in out passing for both a
real RUNGS line and a BAD-RANGE line that happens to mention rungs).

Run:  python3 system/tools/test_checkin_open.py -v
"""

import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "checkin_open.py")


def run_print(brief_path, start, end):
    proc = subprocess.run(
        [sys.executable, SCRIPT, "print", brief_path, "--start", str(start), "--end", str(end)],
        capture_output=True, text=True,
    )
    first_line = proc.stdout.splitlines()[0] if proc.stdout else ""
    return proc.returncode, first_line, proc.stdout, proc.stderr


def run_hint(brief_path):
    proc = subprocess.run(
        [sys.executable, SCRIPT, "hint", brief_path],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def write_brief(tmpdir, text, name="brief.md"):
    path = os.path.join(tmpdir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


# Line numbers below are 1-indexed and were counted by hand against this exact
# string so the tests can pass explicit --start/--end the way the LLM caller
# would after reading the file. Blank line 1 is the string's own leading blank
# (triple-quoted strings start with a newline) — line 1 is "# Test Brief".
#
#  1  # Test Brief
#  2  (blank)
#  3  ## 2. CURRENT STATE (2026-08-06)
#  4  (blank)
#  5  > **▲ 10,000 —** The top-level claim, all on one line.
#  6  (blank)
#  7  > **▲  5,000 —** The reusable machine, all on one line.
#  8  (blank)
#  9  > **▲ ground —** The specific thing being worked on right now, one line.
# 10  (blank)
# 11  ## 3. STORY LOG
# 12  (blank)
# 13  - 2026-08-06: wrote this brief.
THREE_RUNGS_BRIEF = """# Test Brief

## 2. CURRENT STATE (2026-08-06)

> **▲ 10,000 —** The top-level claim, all on one line.

> **▲  5,000 —** The reusable machine, all on one line.

> **▲ ground —** The specific thing being worked on right now, one line.

## 3. STORY LOG

- 2026-08-06: wrote this brief.
"""
# The three rung lines sit at 5, 7, 9. A caller who read the brief would give
# a span covering them; --start 4 --end 10 (heading's blank line through the
# blank line before "## 3. STORY LOG") comfortably covers all three without
# reaching into STORY LOG.
THREE_RUNGS_START = 4
THREE_RUNGS_END = 10


# ⭐ THE REGRESSION THAT MATTERS. Three SEPARATE lines of prose OUTSIDE the
# given span each mention the ▲ glyph once (describing this very tool,
# exactly like the live bug — one glyph per line so "6 triangles" also reads
# as "6 candidate lines" for the `hint` fixture below). print, scoped to the
# span, must still return exactly RUNGS 3 — proving the bug (a file-wide
# `if MARKER in line` scan) is dead.
#
#  1  # Test Brief
#  2  (blank)
#  3  ## 1. NOTES
#  4  (blank)
#  5  This brief describes checkin_open.py's `▲` marker convention.
#  6  The tool looks for lines containing that glyph, referenced again as ▲.
#  7  And one final prose mention of ▲, purely for the regression test.
#  8  (blank)
#  9  ## 2. CURRENT STATE (2026-08-06)
# 10  (blank)
# 11  > **▲ 10,000 —** The top-level claim, all on one line.
# 12  (blank)
# 13  > **▲  5,000 —** The reusable machine, all on one line.
# 14  (blank)
# 15  > **▲ ground —** The specific thing being worked on right now, one line.
# 16  (blank)
# 17  ## 3. STORY LOG
# 18  (blank)
# 19  - 2026-08-06: wrote this brief.
PROSE_MENTIONS_MARKER_BRIEF = """# Test Brief

## 1. NOTES

This brief describes checkin_open.py's `▲` marker convention.
The tool looks for lines containing that glyph, referenced again as ▲.
And one final prose mention of ▲, purely for the regression test.

## 2. CURRENT STATE (2026-08-06)

> **▲ 10,000 —** The top-level claim, all on one line.

> **▲  5,000 —** The reusable machine, all on one line.

> **▲ ground —** The specific thing being worked on right now, one line.

## 3. STORY LOG

- 2026-08-06: wrote this brief.
"""
# The rungs are at 11, 13, 15. A span of --start 10 --end 16 covers only the
# CURRENT STATE section's body, never lines 5-7 where the prose mentions ▲.
REGRESSION_START = 10
REGRESSION_END = 16


# Mirrors the real project-system/brief.md shape: a rung's own line plus a
# continuation line inside the SAME blockquote, wrapped because the author's
# editor line-wrapped mid-sentence. Proves the join produces ONE output line,
# scoped to the span.
#
#  1  # Test Brief
#  2  (blank)
#  3  ## 2. CURRENT STATE (2026-08-06)
#  4  (blank)
#  5  > **▲ 10,000 —** The tooling that keeps a brief honest is BUILT — 4 of 5 phases,
#  6  > 18 of 19 tasks, 11 commits pushed. What remains is cleaning up briefs already damaged.
#  7  (blank)
#  8  > **▲  5,000 —** Phase 4 of the plan, "the migration." Scoped to 3 briefs.
#  9  (blank)
# 10  > **▲ ground —** Task T4.2 on the financial brief.
# 11  (blank)
# 12  ## 3. STORY LOG
# 13  (blank)
# 14  - 2026-08-06: wrote this brief.
WRAPPED_RUNG_BRIEF = """# Test Brief

## 2. CURRENT STATE (2026-08-06)

> **▲ 10,000 —** The tooling that keeps a brief honest is BUILT — 4 of 5 phases,
> 18 of 19 tasks, 11 commits pushed. What remains is cleaning up briefs already damaged.

> **▲  5,000 —** Phase 4 of the plan, "the migration." Scoped to 3 briefs.

> **▲ ground —** Task T4.2 on the financial brief.

## 3. STORY LOG

- 2026-08-06: wrote this brief.
"""
WRAPPED_START = 4
WRAPPED_END = 11


# Proves quote-marker strip is the ONLY transform applied: bold markers,
# backticks, and a unicode em-dash inside the rung text must survive
# byte-identical. The blockquote prefix "> " must be gone; nothing else
# about the line's content may change.
VERBATIM_RUNG_TEXT = (
    "**▲ 10,000 —** The claim uses `inline code`, **nested bold**, "
    "an em-dash — right here, and a smart quote “like this.”"
)
#  1  # Test Brief
#  2  (blank)
#  3  ## 2. CURRENT STATE (2026-08-06)
#  4  (blank)
#  5  > <VERBATIM_RUNG_TEXT>
#  6  (blank)
#  7  > **▲  5,000 —** The reusable machine.
#  8  (blank)
#  9  > **▲ ground —** The specific thing being worked on right now.
# 10  (blank)
# 11  ## 3. STORY LOG
VERBATIM_FIDELITY_BRIEF = f"""# Test Brief

## 2. CURRENT STATE (2026-08-06)

> {VERBATIM_RUNG_TEXT}

> **▲  5,000 —** The reusable machine.

> **▲ ground —** The specific thing being worked on right now.

## 3. STORY LOG

- 2026-08-06: wrote this brief.
"""
VERBATIM_START = 4
VERBATIM_END = 10


# A brief with 6 total ▲ occurrences (3 real rungs + 3 prose mentions), used
# to test `hint`'s permissive, file-wide, numbered-candidate behavior.
SIX_TRIANGLES_BRIEF = PROSE_MENTIONS_MARKER_BRIEF


class TestCheckinOpenPrint(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_print_clean_three_rung_span(self):
        path = write_brief(self.tmpdir, THREE_RUNGS_BRIEF)
        rc, verdict, out, err = run_print(path, THREE_RUNGS_START, THREE_RUNGS_END)
        self.assertEqual(verdict, "RUNGS 3", out)
        self.assertEqual(rc, 0, out)
        body_lines = out.splitlines()[1:]
        self.assertEqual(len(body_lines), 3)
        self.assertIn("10,000", body_lines[0])
        self.assertIn("5,000", body_lines[1])
        self.assertIn("ground", body_lines[2])
        for line in body_lines:
            self.assertFalse(line.startswith(">"), line)

    def test_regression_prose_outside_span_never_counted(self):
        """⭐ THE REGRESSION THAT MATTERS: prose outside the given span mentions
        ▲ three times (six total in the file). print, scoped to the span
        covering only the real rungs, must return exactly RUNGS 3 rc 0."""
        path = write_brief(self.tmpdir, PROSE_MENTIONS_MARKER_BRIEF)
        # sanity: the file really does contain 6 occurrences of the glyph
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read().count("▲"), 6)
        rc, verdict, out, err = run_print(path, REGRESSION_START, REGRESSION_END)
        self.assertEqual(verdict, "RUNGS 3", out)
        self.assertEqual(rc, 0, out)
        body_lines = out.splitlines()[1:]
        self.assertEqual(len(body_lines), 3)
        for line in body_lines:
            self.assertNotIn("marker convention", line)
            self.assertNotIn("a third time", line)

    def test_wrapped_rung_joins_to_one_line(self):
        path = write_brief(self.tmpdir, WRAPPED_RUNG_BRIEF)
        rc, verdict, out, err = run_print(path, WRAPPED_START, WRAPPED_END)
        self.assertEqual(verdict, "RUNGS 3", out)
        self.assertEqual(rc, 0, out)
        body_lines = out.splitlines()[1:]
        self.assertEqual(len(body_lines), 3)
        ten_k = body_lines[0]
        self.assertIn("The tooling that keeps a brief honest is BUILT", ten_k)
        self.assertIn("11 commits pushed", ten_k)
        self.assertIn("What remains is cleaning up briefs already damaged.", ten_k)
        self.assertNotIn("> ", ten_k)
        self.assertNotIn(">", ten_k)

    def test_verbatim_fidelity(self):
        path = write_brief(self.tmpdir, VERBATIM_FIDELITY_BRIEF)
        rc, verdict, out, err = run_print(path, VERBATIM_START, VERBATIM_END)
        self.assertEqual(verdict, "RUNGS 3", out)
        self.assertEqual(rc, 0, out)
        body_lines = out.splitlines()[1:]
        self.assertEqual(body_lines[0], VERBATIM_RUNG_TEXT)

    def test_inverted_range_is_bad_range(self):
        path = write_brief(self.tmpdir, THREE_RUNGS_BRIEF)
        rc, verdict, out, err = run_print(path, THREE_RUNGS_END, THREE_RUNGS_START)
        self.assertEqual(verdict.split()[0], "BAD-RANGE", out)
        self.assertEqual(rc, 2, out)

    def test_out_of_bounds_range_is_bad_range(self):
        path = write_brief(self.tmpdir, THREE_RUNGS_BRIEF)
        n_lines = len(THREE_RUNGS_BRIEF.splitlines())
        rc, verdict, out, err = run_print(path, 1, n_lines + 500)
        self.assertEqual(verdict.split()[0], "BAD-RANGE", out)
        self.assertEqual(rc, 2, out)

    def test_empty_span_is_bad_range(self):
        path = write_brief(self.tmpdir, THREE_RUNGS_BRIEF)
        rc, verdict, out, err = run_print(path, 5, 5)
        self.assertEqual(verdict.split()[0], "BAD-RANGE", out)
        self.assertEqual(rc, 2, out)

    def test_nonexistent_file_is_cannot_read(self):
        path = os.path.join(self.tmpdir, "does-not-exist.md")
        rc, verdict, out, err = run_print(path, 1, 5)
        self.assertEqual(rc, 4, err)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("CANNOT-READ"), err)
        self.assertNotEqual(rc, 0)


class TestCheckinOpenHint(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_hint_six_triangles_six_candidates(self):
        path = write_brief(self.tmpdir, SIX_TRIANGLES_BRIEF)
        rc, out, err = run_hint(path)
        self.assertEqual(rc, 0, err)
        lines = [l for l in out.splitlines() if l.strip()]
        self.assertEqual(len(lines), 6, out)
        # every line is prefixed with its 1-indexed line number
        for line in lines:
            prefix = line.split(":", 1)[0]
            self.assertTrue(prefix.strip().isdigit(), line)
        # never a verdict token on the first line
        first_token = out.splitlines()[0].split()[0] if out.strip() else ""
        self.assertNotIn(first_token, ("RUNGS", "BAD-RANGE", "CANNOT-READ", "NO-RUNGS", "PARTIAL-RUNGS"))

    def test_hint_nonexistent_file_is_cannot_read(self):
        path = os.path.join(self.tmpdir, "does-not-exist.md")
        rc, out, err = run_hint(path)
        self.assertEqual(rc, 4, err)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("CANNOT-READ"), err)


if __name__ == "__main__":
    unittest.main()
