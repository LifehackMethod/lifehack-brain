#!/usr/bin/env python3
"""test_p3w_wake.py — 4P.3D slice W: "work happens when the laptop is awake".

Planted cases (each shown FAILING first against the unmodified branch — see result-d-wake.md):
  1. the same thread seen on two ticks gets exactly ONE AI judgement (a fake reader counts calls);
  2. 3 consecutive in-run failures light "3 tries failed, retrying within the hour", and a relaunch after
     more than 1 hour happens (the per-wake rule resets the day's count);
  3. the 6th attempt of the day is the last, and the ceiling lights its warning;
  4. a text_shape failure gets one repair call before the attempt counts;
  5. the once-a-day launcher starts gc-snapshot when today has no success, and not again once it has;
  6. a laptop first opened at 12:00 still gets the once-a-day jobs at 12:00;
  7. the gc-gmail tile WARNs at 25,000 units and is OK below;
  8. gc-daily no longer calls the envelope pull.

SYNTHETIC only: fakes for the model, the Gmail door and the launchers; temp folders and a temp database only;
no network, no real model calls, never the live rig.db.
Run: venv python tests/test_p3w_wake.py   (from shared/grand_central/)"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import datetime
import json
import sqlite3
import sys
import tempfile
import unittest

HERE = _o.path.dirname(_o.path.abspath(__file__))
ROOT = _o.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
sys.path.insert(0, _o.path.join(ROOT, "system", "tools"))  # the sanitizer (real), as test_date_window does
import gc_settings, gcjobs, morning, status_lights, daily, pull  # noqa: E402
import test_step13_14_jobs as t13  # noqa: E402 (its scratch rooms)
import test_step4_morning as t4  # noqa: E402 (fake model, fixtures)
import test_date_window as dw  # noqa: E402 (FakeFetch, ms(), the real sanitize)
import test_daily as td  # noqa: E402 (its migrated temp db, OK_TOKEN)

gcjobs.MORNING_ATTEMPT_WAIT_S = 0  # the in-run retry wait is a test seam; tests never sleep


def fake_ts(hh, mm=0, day=16):
    return datetime.datetime(2026, 11, day, hh, mm).timestamp()


def fake_dt(hh, mm=0, day=16):
    return datetime.datetime(2026, 11, day, hh, mm)


DAY = t4.DAY  # 2026-11-15


# ================================================================ 1. one judgement per message
class OneJudgementPerMessage(unittest.TestCase):
    """pull.py skips every message id already in the database, so the Sentinel/AI reader never judges the
    same message twice (item C). The metadata fetch still happens (pull keeps no historyId bookmark) —
    the JUDGEMENT is what must not repeat."""

    def setUp(self):
        self.judges = 0
        self.d = tempfile.mkdtemp(prefix="p3w-pull-")
        self.addCleanup(_sh.rmtree, self.d, True)
        pull.BACKOFF_S = 0
        pull.sanitize = dw.real_sanitize

        def counting(items, **kw):
            self.judges += 1
            return dict((i, "CLEAN") for i, _t in items)

        pull.batch_reader.judge_all = counting

    def _run(self, dbfile):
        when = dw.ms(2026, 11, 14, 12)  # inside the window (first run: 2 days back)
        ff = dw.FakeFetch({"t1": [dw.msg("m1", "t1", when)]})
        pull.email_fetch = ff
        pull.PENDING.clear()
        for k in list(pull.STATS):
            pull.STATS[k] = 0
        _o.environ["RIG_DB"] = dbfile
        db = pull.open_db()
        pull.pull_email(db, None, 10, after="2026-11-13")
        pull.flush_pending(db)
        db.commit()
        db.close()
        return ff

    def test_PLANTED_a_thread_seen_on_two_ticks_gets_exactly_one_ai_judgement(self):
        dbfile = _o.path.join(self.d, "rig.db")
        self._run(dbfile)
        self.assertEqual(self.judges, 1, "the first tick judges the new message once")
        n1 = sqlite3.connect(dbfile).execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        self.assertEqual(n1, 1)
        ff2 = self._run(dbfile)  # the SAME thread, seen again on a later tick
        self.assertEqual(ff2.get_calls, ["t1"], "metadata is still fetched (no historyId bookmark)")
        self.assertEqual(self.judges, 1, "the second tick judges NOTHING: the message is already stored")
        self.assertEqual(pull.STATS.get("already_stored"), 1)
        n2 = sqlite3.connect(dbfile).execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        self.assertEqual(n2, 1, "no duplicate row either")


# ================================================================ 2 and 3. the morning's in-run retries
class MorningInRunRetries(t13.MorningJob):
    def ledger(self):
        with open(_o.path.join(self.state, "gc-morning", "launch.json"), encoding="utf-8") as f:
            return json.load(f)

    def check(self, hh, mm=0):
        return gcjobs.morning_launch_check(fake_dt(hh, mm), desk="desk-a",
            launcher=lambda d, st2: self.launched.append(d), state=_o.path.join(self.state, "gc-morning"))

    def test_PLANTED_three_consecutive_in_run_failures_light_retrying_within_the_hour(self):
        self.put_case()
        rc = self.job(t4.FakeModel(self.env, "this is not json at all"))
        self.assertEqual(rc, 1)
        led = self.ledger()
        self.assertEqual(led["fail_streak"], 3, "each in-run attempt counts")
        self.assertEqual(led["attempts"], 3, "every attempt counts toward the day's ceiling")
        self.assertTrue(led["failed"])
        light = status_lights.morning_ledger_light(led, has_draft=False)  # the ledger is dated the real today
        self.assertIsNotNone(light)
        self.assertEqual(light["status"], "ERROR")
        self.assertIn("3 tries failed, retrying within the hour", light["summary"])

    def test_a_success_stops_the_retries_and_one_attempt_counts_once(self):
        self.put_case()
        m = t4.FakeModel(self.env, t4.NOBASE)
        rc = self.job(m)
        self.assertEqual(rc, 0, self.lines)
        self.assertEqual(len(m.prompts), 1, "a good first attempt runs once")
        led = self.ledger()
        self.assertEqual(led["attempts"], 1)
        self.assertFalse(led.get("failed"))

    def test_PLANTED_a_text_shape_failure_gets_one_repair_call_inside_the_same_attempt(self):
        self.put_case()
        long_line = "x" * 5000  # _clean_text: over MAX_TEXT -> "text_shape"
        bad = t4.reply(what_changed=[long_line])
        m = t4.FakeModel(self.env, bad, t4.NOBASE)
        rc = self.job(m)
        self.assertEqual(rc, 0, self.lines)
        self.assertEqual(len(m.prompts), 2, "exactly ONE repair call after the bad reply")
        self.assertIn("corrected JSON", m.prompts[1], "the second prompt asks for the corrected reply")
        led = self.ledger()
        self.assertEqual(led["attempts"], 1, "the repair happens INSIDE the attempt: it still counts once")

    def test_PLANTED_after_more_than_an_hour_the_fast_clock_relaunches(self):
        st = _o.path.join(self.state, "gc-morning")
        _o.makedirs(st, exist_ok=True)
        led = {"day": "2026-11-16", "attempts": 6, "last": fake_ts(6, 0), "last_epoch": fake_ts(6, 0)}
        with open(_o.path.join(st, "launch.json"), "w", encoding="utf-8") as f:
            json.dump(led, f)
        self.assertEqual(self.check(8, 0), "launched", "more than 3600 s since the last attempt resets the count")


class CeilingLedger(t13.Scratch):
    def check(self, hh, mm=0):
        return gcjobs.morning_launch_check(fake_dt(hh, mm), desk="desk-a",
            launcher=lambda d, st2: self.launched.append(d), state=_o.path.join(self.state, "gc-morning"))

    def write_ledger(self, **kw):
        st = _o.path.join(self.state, "gc-morning")
        _o.makedirs(st, exist_ok=True)
        led = {"day": "2026-11-16", "attempts": 0, "last": 0}
        led.update(kw)
        with open(_o.path.join(st, "launch.json"), "w", encoding="utf-8") as f:
            json.dump(led, f)

    def test_PLANTED_the_sixth_attempt_of_the_day_is_the_last_and_the_ceiling_lights_its_warning(self):
        self.write_ledger(attempts=5, last=fake_ts(6, 0), last_epoch=fake_ts(6, 0))
        self.assertEqual(self.check(6, 31), "launched")  # the 6th try still happens
        led = {"day": "2026-11-16", "attempts": 6, "last": fake_ts(6, 31), "last_epoch": fake_ts(6, 31)}
        self.assertEqual(self.check(7, 1), "gave-up-today")
        self.assertEqual(self.launched, ["desk-a"])  # only the 6th
        light = status_lights.morning_ledger_light(led, has_draft=False, today="2026-11-16")
        self.assertIsNotNone(light)
        self.assertEqual(light["status"], "ERROR")
        self.assertIn("daily ceiling of 6 tries reached", light["summary"])

    def test_a_draft_means_the_light_stays_with_the_morning_read(self):
        led = {"day": "2026-11-16", "attempts": 6, "fail_streak": 3, "last": fake_ts(6, 0)}
        self.assertIsNone(status_lights.morning_ledger_light(led, has_draft=True, today="2026-11-16"))


# ================================================================ 4. the once-a-day launcher
class OnceLauncher(t13.Scratch):
    def launch(self, job, code_root=None):
        self.launched.append(job)

    def check(self, hh, mm=0):
        return gcjobs.once_a_day_check(fake_dt(hh, mm), launcher=self.launch, state_root=self.state)

    def receipt(self, job, day="2026-11-16"):
        st = _o.path.join(self.state, job)
        _o.makedirs(st, exist_ok=True)
        with open(_o.path.join(st, "last-run.txt"), "w", encoding="utf-8") as f:
            f.write("%s ok date=%s at=2026-11-16T06:00:00Z\n" % (job, day))

    def test_PLANTED_the_launcher_starts_gc_snapshot_when_today_has_no_success_and_not_again_once_it_has(self):
        words = self.check(6)
        self.assertEqual(words["gc-snapshot"], "launched", "no success today -> started")
        self.assertEqual(self.launched, ["gc-snapshot", "gc-diary-index", "gc-daily"], "in that order")
        self.assertEqual(words["gc-diary-index"], "launched")
        self.assertEqual(words["gc-daily"], "launched")
        for job in gcjobs.ONCE_A_DAY_JOBS:
            self.receipt(job)
        words = self.check(6, 10)
        self.assertEqual([words[j] for j in gcjobs.ONCE_A_DAY_JOBS], ["done", "done", "done"])
        self.assertEqual(len(self.launched), 3, "a success today is never started again")

    def test_PLANTED_a_laptop_first_opened_at_12_00_still_gets_the_once_a_day_jobs(self):
        words = self.check(12)
        self.assertEqual(words["gc-snapshot"], "launched", "the trigger is no success today, never a clock hour")

    def test_the_per_day_ceiling_and_the_gap_hold(self):
        self.check(6)
        words = self.check(6, 5)  # 5 minutes later: backoff, not another launch
        self.assertEqual(words["gc-snapshot"], "backoff")
        self.assertEqual(len(self.launched), 3)
        for job in gcjobs.ONCE_A_DAY_JOBS:  # freeze all three ledgers, so only the ceiling is under test
            st = _o.path.join(self.state, job, "launch.json")
            with open(st, encoding="utf-8") as f:
                led = json.load(f)
            led["attempts"] = 3
            with open(st, "w", encoding="utf-8") as f:
                json.dump(led, f)
        words = self.check(7)
        self.assertEqual(words["gc-snapshot"], "gave-up-today", "at most 3 launches a day")
        self.assertEqual(len(self.launched), 3)

    def test_a_running_job_is_not_started_again(self):
        st = _o.path.join(self.state, "gc-snapshot")
        _o.makedirs(_o.path.join(st, "run.lock"), exist_ok=True)
        with open(_o.path.join(st, "run.lock", "pid"), "w", encoding="utf-8") as f:
            f.write("%d\n" % _o.getpid())
        words = self.check(6)
        self.assertEqual(words["gc-snapshot"], "running")


# ================================================================ 5. the gc-gmail tile
class GmailTile(unittest.TestCase):
    def test_PLANTED_the_gc_gmail_tile_warns_at_25_000_units_and_is_ok_below(self):
        ok = status_lights.gmail_usage_light(1000)  # 1,000 calls x 5 = 5,000 units
        self.assertEqual(ok["status"], "OK")
        warn = status_lights.gmail_usage_light(5000)  # 5,000 calls x 5 = 25,000 units
        self.assertEqual(warn["status"], "NEEDS_REVIEW")
        self.assertIn("WARN", warn["summary"])
        self.assertIn("25,000", warn["summary"])
        self.assertEqual(warn["payload"]["estimated_units"], 25000)

    def test_the_rollup_sums_todays_gmail_calls_from_the_runs_rows(self):
        d = tempfile.mkdtemp(prefix="p3w-gmail-")
        self.addCleanup(_sh.rmtree, d, True)
        p = _o.path.join(d, "rig.db")
        con = sqlite3.connect(p)
        con.execute("CREATE TABLE runs(started TEXT, finished TEXT, args TEXT, counts TEXT)")
        now = datetime.datetime.now(datetime.timezone.utc)
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        today = now.strftime(fmt)
        yesterday = (now - datetime.timedelta(days=1)).strftime(fmt)
        con.executemany("INSERT INTO runs VALUES(?,?,?,?)", [
            (yesterday, yesterday, "{}", json.dumps({"gmail_calls": 999})),  # yesterday: excluded
            (today, today, "{}", json.dumps({"gmail_calls": 6})),
            (today, today, "{}", json.dumps({"gmail_calls": 4})),
            (today, today, "{}", json.dumps({})),  # no counter: counts as 0, not a crash
        ])
        con.commit(); con.close()
        self.assertEqual(status_lights._gmail_calls_today(db=p), 10)

    def test_a_missing_database_is_never_green(self):
        light = status_lights._gmail_light_safe({"gmail_runs_db": _o.path.join(
            tempfile.gettempdir(), "no-such-db-here.db")})
        self.assertEqual(light["status"], "NEEDS_REVIEW")


# ================================================================ 6. gc-daily drops the envelope pull
class DailyNoEnvelopePull(td.T):
    def test_PLANTED_gc_daily_no_longer_calls_the_envelope_pull(self):
        calls = []
        real = daily.run_pull
        daily.run_pull = lambda after, mt: calls.append((after, mt)) or (0, "")
        self.addCleanup(setattr, daily, "run_pull", real)
        r = self.run_daily(pull_fn=None, label_fn=lambda: (0, ""))
        self.assertEqual(calls, [], "the default run pulls nothing: the fast clock owns the envelope pull now")
        self.assertIsNone(r.get("pull"))
        self.assertIsNotNone(td.store.get_source_state("daily"), "its own watermark still advances")

    def test_an_injected_pull_fn_still_runs_for_explicit_callers(self):
        seen = []
        r = self.run_daily(pull_fn=lambda after, mt: seen.append(after) or (0, ""), label_fn=lambda: (0, ""))
        self.assertEqual(len(seen), 1)
        self.assertEqual(r["pull"]["rc"], 0)


# ================================================================ 7. the fast clock's envelope step
class FastClockEnvelope(t13.FastClock):
    def test_the_fast_clock_pulls_envelopes_on_the_watermarks_own_day(self):
        self.put_delivery(1)
        wm = "2026-11-15T23:30:00+00:00"
        rc = self.fast(now_local=fake_dt(6, 0), envelope_watermark=lambda: wm)
        self.assertEqual(rc, 0, self.lines)
        self.assertEqual(self.envelope_pulls, ["2026-11-15"], "the watermark's own day is re-covered (America/New_York)")

    def test_the_first_envelope_pull_looks_two_days_back(self):
        rc = self.fast(today=datetime.date(2026, 11, 16), envelope_watermark=lambda: None)
        self.assertEqual(rc, 0, self.lines)
        self.assertEqual(self.envelope_pulls, ["2026-11-14"], "first run: 2 days back from the fake today")

    def test_a_failed_envelope_pull_is_a_problem_not_a_silent_zero(self):
        rc = self.fast(envelope_pull=lambda after: (1, "boom"))
        self.assertEqual(rc, 1)
        self.assertTrue(any("envelope_pull_failed" in x for x in self.lines), self.lines)
        self.assertIsNone(self.receipt("gc-fast-clock"))

    def test_the_proof_line_gains_one_field_per_once_job(self):
        rc = self.fast()
        self.assertEqual(rc, 0, self.lines)
        line = self.receipt("gc-fast-clock")
        for field in ("once_snapshot=", "once_diary_index=", "once_daily="):
            self.assertIn(field, line)
        self.assertTrue(t13.check_passes("gc-fast-clock", line), line)


if __name__ == "__main__":
    unittest.main(verbosity=1)
