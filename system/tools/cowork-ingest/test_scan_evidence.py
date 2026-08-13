#!/usr/bin/env python3
"""Tests for the SHORT-keeper evidence path in pipeline.py (2026-08-12).

WHAT BROKE. `3-deep-read.md` Step 2 says a keeper at or under WHOLE_READ_MAX was already read whole at
SCAN, so no deep reader is spawned for it — "its SCAN summary IS the finding." The `read-complete` gate
then demanded the deep reader's output as proof. A pile whose keepers are all short could therefore NEVER
close. Found on the first real run against a notes vault, where most notes are short.

WHAT MUST NOT REGRESS. The fix routes those keepers to the SCAN reader's output instead — it does NOT
weaken the gate. The whole point of the gate (skill-building-sop §V.4b) is that it reads an INDEPENDENT
trace rather than a value the session typed. So the tests that matter here are the negative ones: with no
reader output, or with output that names the chat but carries no gist, the pile must still refuse to close.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipeline  # noqa: E402

CHAT = "Projects__Thing__Note.txt"


class ScanEvidenceCase(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="lifehack-scanev-")
        # ⛔ HARDCODED ON PURPOSE, AND IT MUST STAY HARDCODED. This is the name 2-scan.md:51 tells
        # the model to write (`RAW="$COWORK_WORK/raw-scan-$BASKET"`), so this line is the WRITER's
        # side of the contract and the only reason this file can catch a mismatch.
        # Until 2026-08-13 it said `os.path.join(self.work, "scan-raw", "pile")` -- a directory
        # nothing in the pipeline has ever created. The test built it by hand, so it passed on a
        # handoff that could not work, for the whole life of the feature. **Do NOT "tidy" this into
        # pipeline.scan_raw_dir(): importing the path from the code under test is exactly how this
        # bug hid.** If the two ever disagree again, this line is what fails.
        self.raw = os.path.join(self.work, "raw-scan-pile")

    def write_reader(self, payload, name="agent-abc.json"):
        os.makedirs(self.raw, exist_ok=True)
        with open(os.path.join(self.raw, name), "w", encoding="utf-8") as fh:
            json.dump(payload, fh)


class TestScanEvidence(ScanEvidenceCase):
    def test_missing_directory_is_no_evidence(self):
        path, found = pipeline.scan_evidence("pile", self.work)
        self.assertIsNone(found, "a missing reader dir must fail closed, not pass")

    def test_gist_counts_as_evidence(self):
        self.write_reader([{"file": CHAT, "guess": "research", "gist": "a real three sentence gist."}])
        _, found = pipeline.scan_evidence("pile", self.work)
        self.assertTrue(found[CHAT])

    def test_empty_gist_is_not_evidence(self):
        """The row can claim a finding; if the reader returned nothing, that is a dropped read."""
        self.write_reader([{"file": CHAT, "guess": "research", "gist": "   "}])
        _, found = pipeline.scan_evidence("pile", self.work)
        self.assertFalse(found.get(CHAT))

    def test_unreadable_file_does_not_veto_a_good_one(self):
        self.write_reader([{"file": CHAT, "gist": "good"}], name="agent-ok.json")
        os.makedirs(self.raw, exist_ok=True)
        with open(os.path.join(self.raw, "agent-bad.json"), "w", encoding="utf-8") as fh:
            fh.write("{not json")
        _, found = pipeline.scan_evidence("pile", self.work)
        self.assertTrue(found[CHAT])

    def test_accepts_the_summary_key_too(self):
        self.write_reader([{"file": CHAT, "summary": "also a finding"}])
        _, found = pipeline.scan_evidence("pile", self.work)
        self.assertTrue(found[CHAT])

    def test_no_work_dir_is_no_evidence(self):
        env = os.environ.pop("COWORK_WORK", None)
        try:
            _, found = pipeline.scan_evidence("pile", None)
            self.assertIsNone(found)
        finally:
            if env is not None:
                os.environ["COWORK_WORK"] = env


class TestGateUsesIt(ScanEvidenceCase):
    """End-to-end through set_basket_status: the gate must accept a real trace and refuse a fake one."""

    def _map(self):
        return {
            "schema_version": 2,
            "rows": {CHAT: dict(pipeline.CHAT_V2_DEFAULTS,
                                basket="pile", skim_verdict="research",
                                resolution_rung="read-complete", status="done",
                                extraction="scan-summary")},
            "baskets": {"pile": dict(pipeline.BASKET_DEFAULTS, basket_status="skim-complete")},
        }

    def test_refuses_with_no_reader_output(self):
        ok, msg = pipeline.set_basket_status(self._map(), "pile", "read-complete", work_dir=self.work)
        self.assertFalse(ok)
        self.assertIn("short keeper", msg)

    def test_refuses_when_the_reader_returned_an_empty_gist(self):
        self.write_reader([{"file": CHAT, "gist": ""}])
        ok, msg = pipeline.set_basket_status(self._map(), "pile", "read-complete", work_dir=self.work)
        self.assertFalse(ok)
        self.assertIn("no content", msg)

    def test_accepts_a_real_scan_trace(self):
        self.write_reader([{"file": CHAT, "guess": "research", "gist": "a real gist with substance."}])
        ok, msg = pipeline.set_basket_status(self._map(), "pile", "read-complete", work_dir=self.work)
        self.assertTrue(ok, msg)

    def test_a_long_keeper_still_needs_the_DEEP_read_trace(self):
        """The exemption is scoped to rows that record the short path. Anything else must still produce
        the deep reader's output — otherwise this fix would become a hole in the original gate."""
        m = self._map()
        m["rows"][CHAT]["extraction"] = "deep-read"      # not the short path
        self.write_reader([{"file": CHAT, "gist": "scan gist"}])   # scan trace exists...
        ok, msg = pipeline.set_basket_status(m, "pile", "read-complete", work_dir=self.work)
        self.assertFalse(ok, "a deep-read keeper must not be satisfied by SCAN evidence")
        self.assertIn("reader evidence", msg)


if __name__ == "__main__":
    unittest.main()
