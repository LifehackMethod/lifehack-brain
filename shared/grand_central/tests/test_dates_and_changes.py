#!/usr/bin/env python3
"""The read is handed DATES and CALENDAR CHANGES by code (validation run 5 audit): an email dated the day before reads
'yesterday' in the handed list (the AI had said 'today' for two emails dated the day before); a previous staged draft's
'Your next 14 days' list is diffed against today's by code, so the read is never left to say 'I have no earlier calendar
picture' (the loader handed only the AI's prose part of the previous draft, never its calendar list).
Run: python3 -I -B tests/test_dates_and_changes.py   (from shared/grand_central/)"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t, unittest
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)
import morning  # noqa: E402
import test_step4_morning as T  # noqa: E402

DAY = "2026-11-21"
RULE_DATE = "Say 'yesterday' or the date, never 'today', unless the email is dated today."


class Dates(T.Base):
    def setUp(self):
        T.Base.setUp(self)
        self.t = T.triage_of({"needs_me": "cant_tell", "do_or_know": "cant_tell", "how_soon": "cant_tell", "life_area": "cant_tell"})
        self.recs = os.path.join(self.env.root, "recs")

    def run_read(self, **kw):
        self.env.ingest()
        m = T.FakeModel(self.env, T.NOBASE)
        out = morning.run_morning(m, DAY, "desk-a", self.recs, expected=T.EXPECTED, **kw)
        return out, m.prompts[0]

    def test_an_email_dated_the_day_before_says_yesterday(self):
        self.env.deliver("th-1", "msg-1", "Dana <d@h.test>", "The agreement", "2026-11-20 09:55", "read-x", self.t, "Please sign the agreement.")
        out, p = self.run_read()
        self.assertTrue(out["ok"], out)
        dates = T.file_text(p, "mail-dates")
        self.assertIn("dated Fri 20 Nov 2026 09:55 (yesterday)", dates)
        self.assertNotIn("(today)", dates)

    def test_an_email_dated_today_says_today_and_the_rule_is_word_for_word(self):
        self.env.deliver("th-2", "msg-2", "Dana <d@h.test>", "Hello", "2026-11-21 08:10", "read-x", self.t, "Morning.")
        _out, p = self.run_read()
        self.assertIn("dated Sat 21 Nov 2026 08:10 (today)", T.file_text(p, "mail-dates"))
        self.assertIn(RULE_DATE, p)

    def test_relative_day_words(self):
        import datetime
        self.assertEqual(morning.relative_day(datetime.date(2026, 11, 18), DAY), "3 days ago")
        self.assertEqual(morning.relative_day(datetime.date(2026, 11, 22), DAY), "tomorrow")


class CalendarChanges(T.Base):
    def setUp(self):
        T.Base.setUp(self)
        self.t = T.triage_of({"needs_me": "cant_tell", "do_or_know": "cant_tell", "how_soon": "cant_tell", "life_area": "cant_tell"})
        self.recs = os.path.join(self.env.root, "recs")
        os.makedirs(self.recs)

    def previous_draft(self, events):
        lines = ["# Morning snapshot 2026-11-20", "", "## Needs him", "- none flagged", "", "## What code read and counted"]
        lines += ["- Your next 14 days: %s" % morning.calendar_line(e) for e in events]
        lines += ["", "## The morning draft", "(Written by the AI)", "A short picture.", ""]
        with open(os.path.join(self.recs, "2026-11-20-desk-a.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def ev(self, title, s, e, loc=""):
        return {"title": title, "start": "2026-11-2%sT%s:00-05:00" % (s[0], s[1:]), "end": "2026-11-2%sT%s:00-05:00" % (s[0], e), "location": loc}

    def test_a_previous_draft_hands_the_read_a_code_computed_calendar_diff(self):
        old = [{"title": "Dentist", "start": "2026-11-23T10:00:00-05:00", "end": "2026-11-23T11:00:00-05:00", "location": ""},
               {"title": "Lunch with Pat", "start": "2026-11-24T12:00:00-05:00", "end": "2026-11-24T13:00:00-05:00", "location": ""}]
        self.previous_draft(old)
        now = [{"title": "Dentist", "start": "2026-11-23T15:00:00-05:00", "end": "2026-11-23T16:00:00-05:00", "location": ""},
               {"title": "Board call", "start": "2026-11-25T09:00:00-05:00", "end": "2026-11-25T10:00:00-05:00", "location": ""}]
        self.env.deliver("th-3", "msg-3", "Dana <d@h.test>", "Hi", "2026-11-20 09:00", "read-x", self.t, "Note.")
        self.env.ingest()
        m = T.FakeModel(self.env, T.NOBASE)
        out = morning.run_morning(m, DAY, "desk-a", self.recs, expected=T.EXPECTED, calendar=now)
        self.assertTrue(out["ok"], out)
        ch = T.file_text(m.prompts[0], "calendar-changes")
        self.assertIn("previous draft is 2026-11-20", ch)
        self.assertIn("- NEW 2026-11-25: Board call", ch)
        self.assertIn("- CHANGED 2026-11-23: Dentist was 2026-11-23T10:00:00-05:00", ch)
        self.assertIn("- NO LONGER LISTED 2026-11-24: Lunch with Pat", ch)

    def test_no_change_is_said_in_words_not_left_empty(self):
        old = [{"title": "Dentist", "start": "2026-11-23T10:00:00-05:00", "end": "2026-11-23T11:00:00-05:00", "location": ""}]
        self.previous_draft(old)
        self.env.deliver("th-4", "msg-4", "Dana <d@h.test>", "Hi", "2026-11-20 09:00", "read-x", self.t, "Note.")
        self.env.ingest()
        m = T.FakeModel(self.env, T.NOBASE)
        morning.run_morning(m, DAY, "desk-a", self.recs, expected=T.EXPECTED, calendar=old)
        self.assertIn("no changes since the previous draft", T.file_text(m.prompts[0], "calendar-changes"))

    def test_no_previous_draft_is_said_too(self):
        self.env.deliver("th-5", "msg-5", "Dana <d@h.test>", "Hi", "2026-11-20 09:00", "read-x", self.t, "Note.")
        self.env.ingest()
        m = T.FakeModel(self.env, T.NOBASE)
        morning.run_morning(m, DAY, "desk-a", self.recs, expected=T.EXPECTED, calendar=[])
        self.assertIn("no previous draft to compare against", T.file_text(m.prompts[0], "calendar-changes"))


if __name__ == "__main__":
    unittest.main()
