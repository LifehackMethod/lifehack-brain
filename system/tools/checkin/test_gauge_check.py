#!/usr/bin/env python3
"""
test_gauge_check.py — unittest fixtures for gauge_check.py's closed verdict set.

One fixture per verdict (ONE-GAUGE, COMPETING-GAUGES, OVERSIZED, STALE,
NO-GAUGE, CANNOT-READ). Every assertion checks the exit code AND an
EXACT-MATCH of the verdict token parsed off the first line of stdout —
never a substring, because 'GAUGE' in out passes falsely for both
ONE-GAUGE and COMPETING-GAUGES, and this project has already lost time to
exactly that trap twice.

Run:  python3 system/tools/test_gauge_check.py -v
"""

import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "gauge_check.py")


def run_check(brief_path):
    """Invoke `gauge_check.py check <path>`; return (exit_code, verdict_token, stdout)."""
    proc = subprocess.run(
        [sys.executable, SCRIPT, "check", brief_path],
        capture_output=True, text=True,
    )
    first_line = proc.stdout.splitlines()[0] if proc.stdout else ""
    return proc.returncode, first_line, proc.stdout


def write_brief(tmpdir, text, name="brief.md"):
    path = os.path.join(tmpdir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


ONE_GAUGE_BRIEF = """# Test Brief

## 1. FRAME
> the desired outcome, for context only.

## 2. CURRENT STATE (2026-08-01)

**▲ 10,000 — the top-level claim.** Some supporting prose that stays
inside budget.

**▲ 5,000 — the reusable machine.** More supporting prose, still short.

**▲ ground — the specific thing being worked on right now.** Final line
of supporting prose, dated 2026-08-01.

## 3. STORY LOG

""" + "\n".join(f"- 2026-07-{(i % 28) + 1:02d}: padding story-log entry {i}, "
                 "so §2 stays well under the 25% budget."
                 for i in range(1, 41)) + """
- 2026-08-01: wrote this brief's current gauge.

## 4. OPEN LOOPS

- none
"""


COMPETING_GAUGES_BRIEF = """# Test Brief

## 2. CURRENT STATE (2026-08-01)

**▲ 10,000 — the top-level claim.** Text.

**▲ 5,000 — the reusable machine.** Text.

**▲ ground — the specific thing being worked on right now.** Text.

**⭐⭐⭐⭐ WHERE WE ARE (2026-07-20, session close) — a second, competing status block
that duplicates the trio above and disagrees with it.** More text here that a
cold reader would also read as the current status.

## 3. STORY LOG

- 2026-07-01: opened the project.
- 2026-07-20: session close, wrote the block above.
"""


OVERSIZED_BRIEF = """# Test Brief

## 2. CURRENT STATE (2026-08-01)

**▲ 10,000 — the top-level claim.** Text.

**▲ 5,000 — the reusable machine.** Text.

**▲ ground — the specific thing being worked on right now.** Text.

""" + "\n".join(f"Filler line {i} of plain prose, not a heading or a bold lead-in."
                 for i in range(130)) + """

## 3. STORY LOG

- 2026-08-01: only entry, so the % check does not also fire; the absolute
  line cap alone must trip OVERSIZED.
"""


STALE_BRIEF = """# Test Brief

## 2. CURRENT STATE (2026-07-01)

**▲ 10,000 — the top-level claim.** Text, dated 2026-07-01.

**▲ 5,000 — the reusable machine.** Text.

**▲ ground — the specific thing being worked on right now.** Text.

## 3. STORY LOG

""" + "\n".join(f"- 2026-07-{(i % 28) + 1:02d}: padding story-log entry {i}, "
                 "so §2 stays well under the 25% budget."
                 for i in range(1, 41)) + """
- 2026-08-01: did new work the gauge above was never updated to reflect.
"""


# SECTION_RATIO_FLOOR fixtures (added 2026-08-07). One gauge, comfortably
# under the 120-line absolute cap, with a Story Log deliberately tiny enough
# to push the percentage WAY over 25% either way — the only variable under
# test is whether §2's own line count is above or below the floor.
BELOW_FLOOR_BRIEF = """# Test Brief

## 2. CURRENT STATE (2026-08-01)

**▲ 10,000 — the top-level claim.** Text.

**▲ 5,000 — the reusable machine.** Text.

**▲ ground — the specific thing being worked on right now.** Text.

## 3. STORY LOG

- 2026-08-01: only entry, so pct is high while section stays small.
"""
# section_lines=8 (well under SECTION_RATIO_FLOOR=40) · pct=266.7% (well over
# the 25% cap) · must still be ONE-GAUGE: the floor suppresses the pct check.

ABOVE_FLOOR_BRIEF = """# Test Brief

## 2. CURRENT STATE (2026-08-01)

**▲ 10,000 — the top-level claim.** Text.

**▲ 5,000 — the reusable machine.** Text.

**▲ ground — the specific thing being worked on right now.** Text.

""" + "\n".join(f"Filler line {i} of plain prose, not a heading or a bold lead-in."
                 for i in range(38)) + """

## 3. STORY LOG

- 2026-08-01: only entry, so pct is high while section stays under the absolute cap.
"""
# section_lines=47 (at/above SECTION_RATIO_FLOOR=40, still under the 120-line
# absolute cap) · pct=1566.7% (well over 25%) · must be OVERSIZED: at/above
# the floor, the pct check applies same as before this change.


NO_GAUGE_BRIEF = """# Test Brief

## 2. CURRENT STATE (2026-08-01)

Just a paragraph of plain prose. No altitude trio, no heading, no bolded
lead-in line anywhere in this section — nothing a whitelist scan would ever
call a status surface.

## 3. STORY LOG

- 2026-08-01: opened the project.
"""


# STALE-FRONTMATTER fixtures (added 2026-08-07). A warning LINE, not a new verdict token — see
# gauge_check.py's render_text() comment. Compares frontmatter `updated_at:` against the newest
# Story Log entry date (the same value the existing STALE check already computes).
STALE_FRONTMATTER_BRIEF = """---
id: test-brief
updated_at: 2026-07-01
---
# Test Brief

## 2. CURRENT STATE (2026-08-01)

**▲ 10,000 — the top-level claim.** Text, dated 2026-08-01.

**▲ 5,000 — the reusable machine.** Text.

**▲ ground — the specific thing being worked on right now.** Text.

## 3. STORY LOG

- 2026-07-01: opened the project.
- 2026-08-01: newer work than the frontmatter's updated_at claims.
"""

# Frontmatter agrees with (postdates) the newest Story Log entry -> must stay silent.
FRESH_FRONTMATTER_BRIEF = """---
id: test-brief
updated_at: 2026-08-01
---
# Test Brief

## 2. CURRENT STATE (2026-08-01)

**▲ 10,000 — the top-level claim.** Text, dated 2026-08-01.

**▲ 5,000 — the reusable machine.** Text.

**▲ ground — the specific thing being worked on right now.** Text.

## 3. STORY LOG

- 2026-07-01: opened the project.
- 2026-08-01: same date as the frontmatter's updated_at.
"""

# No `updated_at:` key at all -> NOT an error, stays silent.
NO_UPDATED_AT_BRIEF = """---
id: test-brief
title: "no updated_at key here"
---
# Test Brief

## 2. CURRENT STATE (2026-08-01)

**▲ 10,000 — the top-level claim.** Text, dated 2026-08-01.

**▲ 5,000 — the reusable machine.** Text.

**▲ ground — the specific thing being worked on right now.** Text.

## 3. STORY LOG

- 2026-07-01: opened the project.
- 2026-08-01: newer work, but no updated_at key exists to compare.
"""


class TestGaugeCheck(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_one_gauge(self):
        path = write_brief(self.tmpdir, ONE_GAUGE_BRIEF)
        rc, verdict, out = run_check(path)
        self.assertEqual(verdict, "ONE-GAUGE", out)
        self.assertEqual(rc, 0, out)

    def test_competing_gauges(self):
        path = write_brief(self.tmpdir, COMPETING_GAUGES_BRIEF)
        rc, verdict, out = run_check(path)
        self.assertEqual(verdict, "COMPETING-GAUGES", out)
        self.assertEqual(rc, 2, out)
        # must name each surface with its line number
        self.assertIn("altitude-trio @ lines", out)
        self.assertIn("bold-lead-in @ line", out)

    def test_oversized(self):
        path = write_brief(self.tmpdir, OVERSIZED_BRIEF)
        rc, verdict, out = run_check(path)
        self.assertEqual(verdict, "OVERSIZED", out)
        self.assertEqual(rc, 2, out)
        self.assertIn("section:", out)

    def test_stale(self):
        path = write_brief(self.tmpdir, STALE_BRIEF)
        rc, verdict, out = run_check(path)
        self.assertEqual(verdict, "STALE", out)
        self.assertEqual(rc, 2, out)
        self.assertIn("2026-07-01", out)
        self.assertIn("2026-08-01", out)

    def test_below_ratio_floor_not_oversized(self):
        """§2 far under SECTION_RATIO_FLOOR, pct far over 25% -> the
        percentage half of the oversized `or` must NOT fire."""
        path = write_brief(self.tmpdir, BELOW_FLOOR_BRIEF)
        rc, verdict, out = run_check(path)
        self.assertEqual(verdict, "ONE-GAUGE", out)
        self.assertEqual(rc, 0, out)

    def test_at_ratio_floor_still_oversized(self):
        """§2 at/above SECTION_RATIO_FLOOR, pct far over 25%, still under the
        120-line absolute cap -> the percentage check still applies."""
        path = write_brief(self.tmpdir, ABOVE_FLOOR_BRIEF)
        rc, verdict, out = run_check(path)
        self.assertEqual(verdict, "OVERSIZED", out)
        self.assertEqual(rc, 2, out)

    def test_stale_frontmatter_warns(self):
        path = write_brief(self.tmpdir, STALE_FRONTMATTER_BRIEF)
        rc, verdict, out = run_check(path)
        # still a normal ONE-GAUGE verdict/exit code — the warning is additive, not a new token
        self.assertEqual(verdict, "ONE-GAUGE", out)
        self.assertEqual(rc, 0, out)
        self.assertIn("STALE-FRONTMATTER", out)
        self.assertIn("2026-07-01", out)
        self.assertIn("2026-08-01", out)

    def test_fresh_frontmatter_silent(self):
        path = write_brief(self.tmpdir, FRESH_FRONTMATTER_BRIEF)
        rc, verdict, out = run_check(path)
        self.assertEqual(verdict, "ONE-GAUGE", out)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("STALE-FRONTMATTER", out)

    def test_no_updated_at_key_silent(self):
        path = write_brief(self.tmpdir, NO_UPDATED_AT_BRIEF)
        rc, verdict, out = run_check(path)
        self.assertEqual(verdict, "ONE-GAUGE", out)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("STALE-FRONTMATTER", out)

    def test_no_gauge(self):
        path = write_brief(self.tmpdir, NO_GAUGE_BRIEF)
        rc, verdict, out = run_check(path)
        self.assertEqual(verdict, "NO-GAUGE", out)
        self.assertEqual(rc, 3, out)

    def test_cannot_read_missing_file(self):
        path = os.path.join(self.tmpdir, "does-not-exist.md")
        rc, verdict, out = run_check(path)
        self.assertEqual(verdict, "CANNOT-READ", out)
        self.assertEqual(rc, 4, out)

    def test_cannot_read_no_section(self):
        path = write_brief(
            self.tmpdir,
            "# Test Brief\n\n## 1. FRAME\n> no current-state section at all.\n",
        )
        rc, verdict, out = run_check(path)
        self.assertEqual(verdict, "CANNOT-READ", out)
        self.assertEqual(rc, 4, out)

    def test_verdict_tokens_are_exact_not_substrings(self):
        """Guard the trap this file's docstring warns about: 'GAUGE' in out
        would falsely pass for BOTH ONE-GAUGE and COMPETING-GAUGES. Assert
        the parsed first-line token with == against each other's token."""
        path_one = write_brief(self.tmpdir, ONE_GAUGE_BRIEF, name="one.md")
        path_comp = write_brief(self.tmpdir, COMPETING_GAUGES_BRIEF, name="comp.md")
        _, verdict_one, _ = run_check(path_one)
        _, verdict_comp, _ = run_check(path_comp)
        self.assertEqual(verdict_one, "ONE-GAUGE")
        self.assertEqual(verdict_comp, "COMPETING-GAUGES")
        self.assertNotEqual(verdict_one, verdict_comp)
        # the substring trap, demonstrated and then rejected:
        self.assertTrue("GAUGE" in verdict_one and "GAUGE" in verdict_comp)
        self.assertNotEqual(verdict_one, "COMPETING-GAUGES")


if __name__ == "__main__":
    unittest.main()
