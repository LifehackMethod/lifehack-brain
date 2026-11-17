"""Grand Central V2 step 5: the alarm's path (alarm.py). SYNTHETIC only: made-up people, a FAKE reader (never a
model), a FAKE notifier (nothing is sent, nothing pops up), the status tile written to a scratch folder only.
Each planted bad case was shown failing against a naive first version before the real code was written.
Run: python3 tests/test_step5_alarm.py"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import json, os, sys, tempfile, time, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import alarm, scorecard as sc  # noqa: E402

TRIGGERS = os.path.join(HERE, "fixtures", "alarm", "triggers.json")
URGENT = {"deadline_days": 1, "direct_ask": True, "reply_expected": True, "money": None}
CALM = {"deadline_days": None, "direct_ask": False, "reply_expected": False, "money": False}


class FakeReader:
    has_tools = False

    def __init__(self, text="Needs a reply today about a fitting; deadline tomorrow."):
        self.calls, self.text = [], text

    def read(self, thread_text):
        self.calls.append(thread_text)
        return self.text


class FakeNotifier:
    def __init__(self):
        self.sent = []

    def send(self, *, source, message, priority, identity, title):
        self.sent.append(dict(source=source, message=message, priority=priority, identity=identity, title=title))
        return True


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tile = os.path.join(self.tmp.name, "status", "grand-central-alarm.json")   # scratch, never the live folder
        self.cfg = sc.Config.load()
        self.settings = alarm.Settings.load(TRIGGERS)
        self.reader, self.notifier = FakeReader(), FakeNotifier()
        self.texts = {"t-urgent": "synthetic scanned transcript one", "t-calm": "synthetic transcript two"}

    def tearDown(self):
        self.tmp.cleanup()

    def cand(self, mid, obs, verdict="clean", thread=None):
        return {"message_id": mid, "thread_id": thread or ("t-urgent" if obs is URGENT else "t-calm"), "verdict": verdict,
                "obs": obs, "standing": 2.0, "automated": False}

    def run_alarm(self, cands, **kw):
        return alarm.run(cands, cfg=self.cfg, settings=self.settings, fetch_text=lambda t: self.texts[t], reader=self.reader,
                         notifier=self.notifier, tile_path=self.tile, writeup_dir=os.path.join(self.tmp.name, "wu"),
                         state_path=os.path.join(self.tmp.name, "state.json"), **kw)

    def tile_json(self):
        with open(self.tile, encoding="utf-8") as f:
            return json.load(f)


class TestAlarm(Base):
    def test_planted_urgent_reaches_phone_without_waiting(self):
        res = self.run_alarm([self.cand("m1", URGENT)])
        self.assertEqual(res["outcomes"][0]["outcome"], "alarmed")
        self.assertEqual(len(self.notifier.sent), 1)
        self.assertEqual(len(self.reader.calls), 1)          # that one thread, read once
        self.assertEqual(self.reader.calls[0], self.texts["t-urgent"])
        n = self.notifier.sent[0]
        self.assertEqual(n["priority"], "critical")
        self.assertNotIn("fitting", n["message"])             # a teaser, never the parcel: nothing from the write-up
        self.assertIn("fitting", open(os.path.join(self.tmp.name, "wu", "t-urgent.md"), encoding="utf-8").read())
        t = self.tile_json()
        self.assertEqual(t["status"], "NEEDS_REVIEW")
        self.assertEqual(t["stale_after_s"], 1500)

    def test_planted_urgent_that_fails_scan_raises_quarantined_and_is_not_read(self):
        res = self.run_alarm([self.cand("m2", URGENT, verdict="flagged")])
        self.assertEqual(res["outcomes"][0]["outcome"], "quarantined")
        self.assertEqual(self.reader.calls, [])               # the reader is never called
        self.assertEqual(len(self.notifier.sent), 1)
        self.assertIn("quarantined", self.notifier.sent[0]["message"].lower())
        self.assertEqual(self.tile_json()["status"], "NEEDS_REVIEW")

    def test_no_verdict_is_never_read_and_never_alarms(self):
        res = self.run_alarm([self.cand("m3", URGENT, verdict=None)])
        self.assertEqual(res["outcomes"][0]["outcome"], "unscanned")
        self.assertEqual(self.reader.calls, [])
        self.assertEqual(self.notifier.sent, [])

    def test_non_urgent_triggers_nothing(self):
        res = self.run_alarm([self.cand("m4", CALM)])
        self.assertEqual(res["outcomes"][0]["outcome"], "not_triggered")
        self.assertEqual(self.reader.calls, [])
        self.assertEqual(self.notifier.sent, [])
        self.assertEqual(self.tile_json()["status"], "OK")    # the run still stamps the light (that is what goes stale)

    def test_tile_shows_stale_when_a_run_is_missed(self):
        self.run_alarm([])
        t = self.tile_json()
        ran = time.mktime(time.strptime(t["last_run"][:19], "%Y-%m-%dT%H:%M:%S"))
        self.assertEqual(alarm.tile_freshness(self.tile, now=ran + 60), "fresh")
        self.assertEqual(alarm.tile_freshness(self.tile, now=ran + 1500 + 60), "stale")   # one missed run
        self.assertEqual(alarm.tile_freshness(self.tile + ".nope", now=ran), "missing")

    def test_reader_with_tools_is_refused(self):
        bad = FakeReader(); bad.has_tools = True
        self.reader = bad
        with self.assertRaises(alarm.AlarmError):
            self.run_alarm([self.cand("m5", URGENT)])
        self.assertEqual(bad.calls, [])

    def test_reader_failure_still_alerts_and_marks_error(self):
        class Boom(FakeReader):
            def read(self, t):
                raise RuntimeError("model down")
        self.reader = Boom()
        res = self.run_alarm([self.cand("m6", URGENT)])
        self.assertEqual(res["outcomes"][0]["outcome"], "read_failed")
        self.assertEqual(len(self.notifier.sent), 1)          # urgent mail is not lost because the write-up failed
        self.assertEqual(self.tile_json()["status"], "ERROR")

    def test_same_message_is_not_handled_twice(self):
        self.run_alarm([self.cand("m7", URGENT)])
        res = self.run_alarm([self.cand("m7", URGENT)])
        self.assertEqual(res["outcomes"][0]["outcome"], "already_handled")
        self.assertEqual(len(self.reader.calls), 1)
        self.assertEqual(len(self.notifier.sent), 1)

    def test_triggers_come_from_the_settings_file(self):
        p = os.path.join(self.tmp.name, "t.json")
        json.dump({"pulse_job": "x", "stale_after_s": 60, "triggers": []}, open(p, "w", encoding="utf-8"))
        self.settings = alarm.Settings.load(p)               # his rules replace the first one: no triggers, so no alarm
        res = self.run_alarm([self.cand("m8", URGENT)])
        self.assertEqual(res["outcomes"][0]["outcome"], "not_triggered")
        json.dump({"pulse_job": "x", "stale_after_s": 60, "triggers": [{"id": "z", "kind": "nope"}]}, open(p, "w", encoding="utf-8"))
        with self.assertRaises(alarm.AlarmError):
            alarm.Settings.load(p)                            # an unknown rule kind fails loud, never silently ignored

    def test_tile_path_is_required(self):
        with self.assertRaises(alarm.AlarmError):
            alarm.run([], cfg=self.cfg, settings=self.settings, fetch_text=None, reader=self.reader,
                      notifier=self.notifier, tile_path=None)

    def test_shell_notifier_builds_the_governed_call_without_running_it(self):
        seen = []

        class R:
            returncode = 0; stderr = ""; stdout = ""
        n = alarm.ShellNotifier(script="/x/notify-send.sh", runner=lambda argv, **k: (seen.append(argv), R())[1])
        self.assertTrue(n.send(source="grand-central-alarm", message="m", priority="critical", identity="i", title="t"))
        self.assertEqual(seen[0][:2], ["bash", "/x/notify-send.sh"])
        for flag in ("--source", "--message", "--priority", "--identity", "--title"):
            self.assertIn(flag, seen[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
