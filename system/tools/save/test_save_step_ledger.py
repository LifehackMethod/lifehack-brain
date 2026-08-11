#!/usr/bin/env python3
"""
test_save_step_ledger.py — unittest fixtures for save_step_ledger.py's `graduate` stamp.

`graduate` is the CAUSED-not-ASSERTED stamp for /checkin's Step "§2 CURRENT STATE graduated":
it must refuse unless `pad_archive.py verify <brief> --heading <heading>` proves the archive
chain for that exact section is intact AND the newest archive block postdates this ledger run's
`start` (proving THIS run did the archiving, not that it's inheriting a stale block from a prior
session). Mirrors the discipline `_verify_compact()` already carries for the `compact` stamp,
which itself has no test file of its own to mirror — so this file builds the minimum set the
Phase 7 task called for: refuses with no archive, refuses on a stale block, passes after a fresh
archive. Plus two guard fixtures specific to `graduate`'s design (it needs `--heading`, unlike
`compact`, because a named section's archive filename is heading-derived, not fixed).

Each test runs the REAL CLI (`save_step_ledger.py` and `pad_archive.py` both as subprocesses)
against a real temp brief, so the archive that `graduate` checks is one pad_archive.py itself
actually wrote — never a hand-faked file standing in for it. Each test gets its own
CLAUDE_CODE_SESSION_ID so ledger state never leaks between tests, and cleans its ledger file up
in tearDown.

Run:  python3 system/tools/test_save_step_ledger.py -v
"""

import os
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER_SCRIPT = os.path.join(HERE, "save_step_ledger.py")
ARCHIVE_SCRIPT = os.path.join(HERE, "pad_archive.py")
RUN_DIR = Path.home() / ".claude" / "run" / "save-ledger"

HEADING = "## 2. CURRENT STATE (2026-08-07)"

BRIEF_TEXT = f"""# Test Brief

{HEADING}

**▲ 10,000 — the top-level claim.** Text.

**▲ 5,000 — the reusable machine.** Text.

**▲ ground — the specific thing being worked on right now.** Text.

## 3. STORY LOG

- 2026-08-07: wrote this brief.
"""


def _env_for(sid):
    env = os.environ.copy()
    env["CLAUDE_CODE_SESSION_ID"] = sid
    return env


def run_ledger(args, sid):
    proc = subprocess.run(
        [sys.executable, LEDGER_SCRIPT] + args,
        capture_output=True, text=True, env=_env_for(sid),
    )
    return proc.returncode, proc.stdout, proc.stderr


def run_archive(brief, heading=HEADING):
    proc = subprocess.run(
        [sys.executable, ARCHIVE_SCRIPT, "archive", brief, "--heading", heading],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


class TestGraduateStamp(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = self._tmp.name
        self.sid = "test-graduate-%s" % uuid.uuid4().hex
        self.brief = os.path.join(self.tmpdir, "brief.md")
        with open(self.brief, "w", encoding="utf-8") as f:
            f.write(BRIEF_TEXT)

    def tearDown(self):
        self._tmp.cleanup()
        ledger_file = RUN_DIR / ("save-%s.json" % self.sid)
        if ledger_file.exists():
            ledger_file.unlink()

    def test_refuses_with_no_archive(self):
        rc, out, err = run_ledger(["start"], self.sid)
        self.assertEqual(rc, 0, err)

        rc, out, err = run_ledger(
            ["stamp", "graduate", self.brief, "--heading", HEADING], self.sid
        )
        self.assertNotEqual(rc, 0, out)
        self.assertIn("refused", err)
        self.assertIn("pad_archive.py verify", err)

    def test_refuses_without_heading(self):
        rc, out, err = run_ledger(["start"], self.sid)
        self.assertEqual(rc, 0, err)

        rc, out, err = run_ledger(["stamp", "graduate", self.brief], self.sid)
        self.assertNotEqual(rc, 0, out)
        self.assertIn("--heading required", err)

    def test_refuses_on_stale_block(self):
        # Archive FIRST (block ts = T0), then start the ledger (started = T1 > T0). The
        # archive predates the ledger run, so it must read as a stale inheritance, not
        # evidence THIS run graduated §2.
        rc, out, err = run_archive(self.brief)
        self.assertEqual(rc, 0, err or out)
        self.assertTrue(out.startswith("RECEIPT"), out)

        time.sleep(1.1)  # force a real second-level gap (ISO ts is second-precision)

        rc, out, err = run_ledger(["start"], self.sid)
        self.assertEqual(rc, 0, err)

        rc, out, err = run_ledger(
            ["stamp", "graduate", self.brief, "--heading", HEADING], self.sid
        )
        self.assertNotEqual(rc, 0, out)
        self.assertIn("NOT after this", err)

    def test_passes_after_fresh_archive(self):
        # Start the ledger FIRST (started = T0), then archive (block ts = T1 > T0). The
        # archive postdates the ledger run, so `graduate` must succeed.
        rc, out, err = run_ledger(["start"], self.sid)
        self.assertEqual(rc, 0, err)

        time.sleep(1.1)

        rc, out, err = run_archive(self.brief)
        self.assertEqual(rc, 0, err or out)
        self.assertTrue(out.startswith("RECEIPT"), out)

        rc, out, err = run_ledger(
            ["stamp", "graduate", self.brief, "--heading", HEADING], self.sid
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("stamped graduate", out)

        # and the coverage report must show graduate as ✓, not MISSED
        rc, out, err = run_ledger(["report", "--session-close"], self.sid)
        self.assertIn("graduate", out)
        graduate_line = next(l for l in out.splitlines() if "graduate" in l)
        self.assertIn("✓", graduate_line, out)
        self.assertNotIn("MISSED", graduate_line, out)

    def test_chain_break_refuses(self):
        # A verify failure (no archive at all, simplest way to force chain-not-intact)
        # must refuse via the same `pad_archive.py verify` exit-code check, and must
        # NEVER leave a stamp behind.
        rc, out, err = run_ledger(["start"], self.sid)
        self.assertEqual(rc, 0, err)

        rc, out, err = run_ledger(
            ["stamp", "graduate", self.brief, "--heading", HEADING], self.sid
        )
        self.assertNotEqual(rc, 0, out)

        rc, out, err = run_ledger(["report", "--session-close"], self.sid)
        graduate_line = next(l for l in out.splitlines() if "graduate" in l)
        self.assertIn("MISSED", graduate_line, out)


class TestArchiveFilenameIsNotDuplicated(unittest.TestCase):
    """⚖ The ledger used to hand-copy the archiver's slugify(), with a comment saying a drift would
    make `graduate` refuse — or silently check the WRONG file — without the archiver ever changing.
    It imports it now. This test fails if anyone re-introduces a second copy."""

    def test_the_ledger_asks_the_archiver_for_the_filename(self):
        sys.path.insert(0, HERE)
        import save_step_ledger as led
        import pad_archive as pa
        for heading in ("## 7. SCRATCHPAD",
                        "## 2. CURRENT STATE (2026-08-07)",
                        "## 1. CURRENT STATE `ACTIVE`",
                        "## 2a. PRIOR STATE"):
            self.assertEqual(led._archive_file("/x/brief.md", heading),
                             pa.archive_path("/x/brief.md", heading), heading)

    def test_no_second_slugify_survives_in_the_ledger(self):
        src = open(os.path.join(HERE, "save_step_ledger.py")).read()
        self.assertNotIn("def _slugify_heading", src,
                         "a duplicate of the archiver's slugify() is back in the ledger")


if __name__ == "__main__":
    unittest.main()
