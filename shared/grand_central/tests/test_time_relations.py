#!/usr/bin/env python3
"""Code hands the morning read its TIME RELATIONS (validation run 5 audit): which events overlap, which fall inside a
travel window, which sit in a layover - computed from the real instants (the zone each stored string carries), never
worked out by the model. Planted cases: a flight 07:10-08:59 and a meeting 09:30-10:30 are NOT overlapping; a workout
07:30-09:00 is inside the travel window; a 06:00 reminder between legs 01:34-04:54 and 07:10-08:59 is in the layover.
Run: python3 -I -B tests/test_time_relations.py   (from shared/grand_central/)"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t, unittest
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import sys
ROOT = _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import capacity  # noqa: E402
import morning  # noqa: E402

DAY = "2026-11-21"


def ev(title, s, e, loc=""):
    return {"title": title, "start": "2026-11-21T%s:00-05:00" % s, "end": "2026-11-21T%s:00-05:00" % e, "location": loc}


LEG1 = ev("Flight to Dallas", "01:34", "04:54")
LEG2 = ev("Flight home", "07:10", "08:59")
MEET = ev("xx meeting", "09:30", "10:30")
WORK = ev("Workout", "07:30", "09:00")
REM = ev("Call the plumber", "06:00", "06:00")


def rel(*rows):
    return "\n".join(capacity.time_relations(list(rows), DAY))


class TimeRelations(unittest.TestCase):
    def test_a_meeting_after_the_landing_is_not_overlapping(self):
        out = rel(LEG2, MEET)
        self.assertIn("none overlap", out)
        self.assertNotIn("OVERLAPS", out)
        self.assertNotIn("inside this travel window: \"xx meeting\"", out)

    def test_a_workout_during_the_flight_is_listed_inside_the_travel_window(self):
        out = rel(LEG2, WORK)
        self.assertIn('TRAVEL "Flight home"', out)
        self.assertIn('inside this travel window: "Workout"', out)

    def test_a_reminder_between_legs_is_in_the_layover(self):
        out = rel(LEG1, LEG2, REM)
        self.assertIn("in the layover: \"Call the plumber\"", out)
        self.assertNotIn('inside this travel window: "Call the plumber"', out)

    def test_two_real_overlaps_are_listed_with_both_titles_and_times(self):
        out = rel(ev("Dentist", "13:00", "14:00"), ev("Call with Pat", "13:30", "14:30"))
        self.assertIn('"Dentist", Sat 21 Nov 13:00-14:00  OVERLAPS  "Call with Pat", Sat 21 Nov 13:30-14:30', out)

    def test_zones_are_real_instants(self):
        # 09:00 in -06:00 is 10:00 local (-05:00): a 09:30 local meeting IS inside a flight that lands 09:00 -06:00 (a naive wall-clock compare would say it is after)
        flight = {"title": "Flight", "start": "2026-11-21T07:00:00-05:00", "end": "2026-11-21T09:00:00-06:00"}
        out = rel(flight, ev("Standup", "09:30", "10:00"))
        self.assertIn('inside this travel window: "Standup"', out)
        self.assertIn("[stored as", out)

    def test_the_prompt_carries_the_file_and_the_rule_word_for_word(self):
        files = dict(morning.build_files(DAY, "desk-a", None, None, None, None, [], [LEG2, WORK], [], None))
        self.assertIn('inside this travel window: "Workout"', files["time-relations"])
        self.assertIn("Never work out yourself whether two times overlap or fall during travel; use code's time-relations list.",
                      morning.MORNING_RULES)

    def test_a_bad_row_never_crashes(self):
        out = rel({"title": "x", "start": "garbage", "end": None}, {"start": "2026-11-21"}, "not a dict")
        self.assertIn("none overlap", out)


if __name__ == "__main__":
    unittest.main()
