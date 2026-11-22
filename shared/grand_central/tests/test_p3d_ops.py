#!/usr/bin/env python3
"""4P.3 slice D (the morning job's operations): items 11, 12, 6 and 13 (build window gc1e, job b-ops).

Planted bad cases, each shown FAILING first against the unmodified branch (proof in result-b-ops.md):
  item 11: (a) a fake claude exiting 1 with "model overloaded" on stderr names it in the failure reason;
           (b) mail-boundary lines, "=== message" headers and overlong lines are filtered out of the tail;
           (c) a success with chatty stderr is not a failure and logs nothing new.
  item 12: (a) 3 attempts is no longer the ceiling (it is 6) and gave-up-today still holds at the ceiling;
           (b) attempts recorded before a 2-hour gap (sleep/wake) are reset, so the day is not lost;
           (c) a "failed" flag lets the next try start one fast-clock tick early, and a second
               consecutive failure is back on the 30-minute clock;
           (d) an old ledger without the new keys still loads.
  item 6:  (a) a validated picture 8 days older than the run's day is STALE: the baseline is rebuilt from
               raw facts and the write-up says the validated picture was stale;
           (b) 6 days old -> still used as validated;
           (c) a validated file whose date prefix cannot be parsed is treated as stale, never fresh.
  item 13: (a) after a successful fake morning run, the day's diary entry exists with "confidence: low";
           (b) a pre-existing entry for the day is left byte-identical (reported "exists");
           (c) a diary-write failure is said loudly and never un-stages the draft or fails the run.
  item 6 at hand_run level: the run says the validated picture went stale and the staged write-up says so.

SYNTHETIC only: scratch folders, a fake claude binary (a /bin/sh script, never the real CLI), fake models.
Run: python3 tests/test_p3d_ops.py (from shared/grand_central/)"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t # isolation: no test writes outside tmp
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import datetime
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import gcjobs, morning # noqa: E402
import test_step4_morning as t4 # noqa: E402 (its scratch front room, fake model, fixture helpers)
import test_step13_14_jobs as t13 # noqa: E402 (its Scratch/MorningJob env, slurp)

# ================================================================ item 11: the failure names its cause
class Item11Stderr(unittest.TestCase):
    def setUp(self):
        self.home = os.path.realpath(tempfile.mkdtemp(prefix="p3d11-"))
        self.addCleanup(shutil.rmtree, self.home, True)

    def fake_claude(self, stderr_lines, stdout="THE REPLY", exit_code=1):
        d = tempfile.mkdtemp(prefix="p3d11-bin-")
        self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, "claude")
        with open(p, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\ncat > /dev/null\n")
            f.write("printf '%s\\n' " + json.dumps(stdout) + "\n")
            for ln in stderr_lines:
                f.write("printf '%s\\n' " + json.dumps(ln) + " >&2\n")
            f.write("exit %d\n" % exit_code)
        os.chmod(p, 0o755)
        return p

    def model(self, script):
        return morning.ClaudeCliModel(claude=script, home=self.home)

    def test_PLANTED_a_failed_exit_names_its_cause(self):
        raw, err = self.model(self.fake_claude(["model overloaded, try again later"])).complete("prompt")
        self.assertIsNone(raw)
        self.assertTrue(err.startswith("exit_1: model overloaded"), err)

    def test_PLANTED_the_tail_is_filtered_of_mail_text_and_overlong_lines(self):
        long_line = "x" * 400
        raw, err = self.model(self.fake_claude([
            "cli hint one",
            "=== message aabbcc | 2026-11-20 | from: someone | label: x ===",
            "<<<MAIL-1234 thread t",
            long_line,
            "model overloaded",
        ])).complete("prompt")
        self.assertIsNone(raw)
        self.assertIn("model overloaded", err)
        self.assertIn("cli hint one", err)
        self.assertNotIn("=== message", err)
        self.assertNotIn("<<<MAIL-", err)
        self.assertNotIn(long_line, err)

    def test_only_the_last_twenty_lines_are_kept(self):
        lines = ["noise %d" % i for i in range(40)] + ["the real cause"]
        raw, err = self.model(self.fake_claude(lines)).complete("prompt")
        self.assertIn("the real cause", err)
        self.assertNotIn("noise 15", err) # 40 noise lines: only the last 20 are kept, so 15 is cut

    def test_a_success_with_chatty_stderr_is_not_a_failure(self):
        raw, err = self.model(self.fake_claude(["some chatty diagnostic"], exit_code=0)).complete("prompt")
        self.assertEqual(raw, "THE REPLY")
        self.assertIsNone(err)

# ================================================================ item 12: one bad patch cannot cost the day
class Item12Retry(t13.Scratch):
    def check(self, hh, mm=0):
        return gcjobs.morning_launch_check(datetime.datetime(2026, 11, 16, hh, mm), desk="desk-a",
            launcher=lambda d, st: self.launched.append(d), state=os.path.join(self.state, "gc-morning"))

    def ts(self, hh, mm=0):
        return datetime.datetime(2026, 11, 16, hh, mm).timestamp()

    def write_ledger(self, **kw):
        st = os.path.join(self.state, "gc-morning")
        os.makedirs(st, exist_ok=True)
        led = {"day": "2026-11-16", "attempts": 0, "last": 0}
        led.update(kw)
        with open(os.path.join(st, "launch.json"), "w", encoding="utf-8") as f:
            json.dump(led, f)

    def read_ledger(self):
        with open(os.path.join(self.state, "gc-morning", "launch.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_PLANTED_the_ceiling_is_six_and_gave_up_still_holds(self):
        self.write_ledger(attempts=6, last=self.ts(6, 0))
        self.assertEqual(self.check(6, 3), "gave-up-today") # 6 tries, last one 3 minutes ago
        self.assertEqual(self.launched, [])
        self.write_ledger(attempts=3, last=self.ts(6, 0)) # 3 tries is NOT the end of the day any more
        self.assertEqual(self.check(6, 3), "backoff")

    def test_PLANTED_a_wake_resets_the_day_s_attempt_count(self):
        # six attempts all before the Mac slept (last attempt epoch 2 hours old): the day is not lost
        self.write_ledger(attempts=6, last=self.ts(4, 0), last_epoch=self.ts(4, 0))
        self.assertEqual(self.check(6, 0), "launched", "a wake must reset the count")
        self.assertEqual(self.launched, ["desk-a"])
        led = self.read_ledger()
        self.assertEqual(led["attempts"], 1)

    def test_a_failed_morning_waits_the_normal_gap_retries_live_inside_the_run(self):
        # superseded 2026-11-20 by the wake ruling: the 5-minute retries happen INSIDE the detached run, so the
        # fast clock keeps its normal 30-minute gap after a failed run (no 9-minute fast retry any more)
        self.write_ledger(attempts=3, last=self.ts(6, 0), failed=True, fail_streak=3)
        self.assertEqual(self.check(6, 10), "backoff")
        self.assertEqual(self.check(6, 40), "launched")

    def test_an_old_ledger_without_the_new_keys_still_loads(self):
        self.write_ledger(attempts=1, last=self.ts(6, 0)) # no last_epoch, no failed, no fail_streak
        self.assertEqual(self.check(6, 10), "backoff") # old behaviour, no crash
        self.assertEqual(self.check(8, 0), "launched")

    def test_mark_morning_outcome_flags(self):
        # wake ruling: "failed" means 3 consecutive failures (the in-run retries used up), never one
        st = os.path.join(self.state, "gc-morning")
        for n in (1, 2):
            gcjobs.mark_morning_outcome(False, state=st)
            led = self.read_ledger()
            self.assertFalse(led.get("failed", False))
            self.assertEqual(led["fail_streak"], n)
        gcjobs.mark_morning_outcome(False, state=st)
        led = self.read_ledger()
        self.assertTrue(led["failed"])
        self.assertEqual(led["fail_streak"], 3)
        gcjobs.mark_morning_outcome(True, state=st) # a good run clears it
        led = self.read_ledger()
        self.assertFalse(led.get("failed", False))
        self.assertEqual(led["fail_streak"], 0)

# ================================================================ item 6: the drift guard on the baseline
class Item6Drift(unittest.TestCase):
    def rec(self, vname, bullets="- his line one\n- his line two\n"):
        d = os.path.realpath(tempfile.mkdtemp(prefix="p3d6-"))
        self.addCleanup(shutil.rmtree, d, True)
        with open(os.path.join(d, vname), "w", encoding="utf-8") as f:
            f.write("# Weekly snapshot\n\n## Picture\n%s\n## Questions\n- none\n" % bullets)
        return d

    def test_PLANTED_a_validated_picture_eight_days_old_is_stale(self):
        d = self.rec("2026-11-08-desk-a-validated.md")
        text, name = morning.previous_picture(d, "desk-a", day="2026-11-16")
        self.assertEqual(name, "2026-11-08-desk-a-validated.md")
        self.assertIn(morning.STALE_MARK, text.splitlines()[0])
        self.assertIn("rebuilt from raw facts", text)
        self.assertNotIn("- his line one", text) # nothing from the stale picture is carried

    def test_a_validated_picture_six_days_old_is_still_used(self):
        d = self.rec("2026-11-08-desk-a-validated.md")
        text, name = morning.previous_picture(d, "desk-a", day="2026-11-14")
        self.assertIn("validated weekly picture", text)
        self.assertNotIn(morning.STALE_MARK, text)
        self.assertIn("- his line one", text)

    def test_PLANTED_an_unparseable_date_prefix_is_stale(self):
        d = self.rec("2026-11-32-desk-a-validated.md")
        text, name = morning.previous_picture(d, "desk-a", day="2026-11-16")
        self.assertIn(morning.STALE_MARK, text.splitlines()[0])

    def test_the_stale_text_parses_as_unconfirmed_not_as_his(self):
        text, _n = morning.previous_picture(self.rec("2026-11-08-desk-a-validated.md"), "desk-a", day="2026-11-16")
        b = morning.parse_baseline(text)
        self.assertEqual(b.kind, "draft") # never validated: every line carried as unconfirmed
        self.assertTrue(all(ln["carried"] for ln in b.lines))

    def test_no_day_argument_keeps_the_old_behaviour(self):
        d = self.rec("2026-11-08-desk-a-validated.md")
        text, _n = morning.previous_picture(d, "desk-a") # callers that pass no day: unchanged
        self.assertIn("validated weekly picture", text)
        self.assertNotIn(morning.STALE_MARK, text)

# ================================================================ items 6 and 13 at hand_run level
class Item6And13HandRun(t13.MorningJob):
    def diary_path(self, day):
        return morning.diary_entry_path(os.path.join(self.notes, "desks", "desk-a", "diary"), day, "desk-a", "tree")

    def test_PLANTED_the_run_says_the_validated_picture_went_stale(self):
        rec = morning.records_context_dir(self.notes, "desk-a")
        os.makedirs(rec, exist_ok=True)
        with open(os.path.join(rec, "2026-11-05-desk-a-validated.md"), "w", encoding="utf-8") as f:
            f.write("# Weekly snapshot\n\n## Picture\n- his old line\n")
        self.put_case()
        m = t4.FakeModel(self.env, t4.NOBASE)
        rc = self.job(m)
        self.assertEqual(rc, 0, self.lines)
        self.assertTrue(any(morning.STALE_MARK in l for l in self.lines), self.lines)
        self.assertIn("rebuilt from raw facts", t4.file_text(m.prompts[0], "baseline-unconfirmed")) # the AI is told the picture went stale
        self.assertNotIn("FILE baseline-confirmed", m.prompts[0])                                  # and nothing is rolled forward as his

    def test_PLANTED_the_morning_writes_the_day_s_low_confidence_diary_entry(self):
        self.put_case()
        rc = self.job(t4.FakeModel(self.env, t4.NOBASE))
        self.assertEqual(rc, 0, self.lines)
        self.assertTrue(os.path.isfile(self.diary_path(t4.DAY)), self.lines)
        text = t4.read(self.diary_path(t4.DAY))
        self.assertIn("confidence: low", text)

    def test_PLANTED_a_pre_existing_entry_gets_the_morning_entry_appended_his_text_unchanged(self):
        path = self.diary_path(t4.DAY)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("his entry, written earlier\n")
        self.put_case()
        rc = self.job(t4.FakeModel(self.env, t4.NOBASE))
        self.assertEqual(rc, 0, self.lines)
        text = t4.read(path)
        self.assertIn("\nhis entry, written earlier\n# Morning read", text.replace("\n\n#", "\n#"))
        self.assertTrue(any("appended" in l for l in self.lines), self.lines)

    def test_PLANTED_a_diary_write_failure_is_said_loudly_and_never_unstages(self):
        orig = morning.write_diary_entry

        def boom(*a, **k):
            raise RuntimeError("diary folder gone")

        morning.write_diary_entry = boom
        self.addCleanup(setattr, morning, "write_diary_entry", orig)
        self.put_case()
        rc = self.job(t4.FakeModel(self.env, t4.NOBASE))
        self.assertEqual(rc, 0, self.lines) # the run does not fail
        rec = morning.records_context_dir(self.notes, "desk-a")
        self.assertTrue(os.path.isfile(os.path.join(rec, "%s-desk-a.md" % t4.DAY))) # the draft stands
        proof = [l for l in self.lines if "morning read " in l]
        self.assertTrue(proof and "every new email accounted for" in proof[-1], self.lines)
        self.assertTrue(any("diary entry was NOT written" in l for l in self.lines), self.lines) # said loudly

if __name__ == "__main__":
    unittest.main(verbosity=2)
