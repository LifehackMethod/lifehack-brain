"""Grand Central V2 phase 1 step 1.2: calendar, tasks and email carry equal weight in the morning read (vision 3.9).
SYNTHETIC only: made-up events, tasks and mail, a FAKE model, scratch folders and a scratch database. No real model, no
real mail. Planted-bad-case proof: EQUAL_TEST_OLD=1 puts the old behaviour back (email-only compare, email takes the whole
budget, only email accounted); the planted cases are written to FAIL under it and pass with the new code.
    python3 tests/test_step12_equal_weight.py
    EQUAL_TEST_OLD=1 python3 tests/test_step12_equal_weight.py     (the planted cases must FAIL)
"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
sys.path.insert(0, HERE)
import test_step4_morning as t4  # noqa: E402
import step3_fixture  # noqa: E402
import delta, morning, transcripts  # noqa: E402

OLD = bool(os.environ.get("EQUAL_TEST_OLD"))
if OLD:
    _empty = {"calendar": {"new": [], "changed": [], "missing": []}, "tasks": {"new": [], "changed": [], "missing": []}, "questions": []}
    delta.compare_cal_tasks = lambda prev, cur, day, ahead_days=14: json.loads(json.dumps(_empty))
    morning.source_budgets = lambda total, c, t: {"share": total // 3, "calendar": total, "tasks": total, "email": total}
    morning.account_sources = lambda sd, shown: {"counts": {}, "problems": [], "segment": ""}
    _old_rank = morning.rank_questions

    def _rank_old(questions, standing_of, cap=morning.MAX_QUESTIONS):   # email first, no shares
        q = sorted(questions, key=lambda x: morning._question_source(x) != "email")
        return q[:cap], max(0, len(q) - cap)
    morning.rank_questions = _rank_old

DAY = "2026-11-16"
D0 = {"calendar": {}, "tasks": {}}


def ev(i, title, start, cancelled=False, end=None):
    return {"title": title, "start": start, "end": end or start, "location": "", "cancelled": cancelled}


def tk(title, due="", done=False):
    return {"title": title, "due": due, "done": done}


PREV = {"day": "2026-11-15",
        "calendar": {"e1": ev("e1", "Dentist", "2026-11-18T10:00:00Z"), "e2": ev("e2", "Board call", "2026-11-20T15:00:00Z"),
                     "e3": ev("e3", "Flight to Exampleville", "2026-11-22T08:00:00Z"), "e4": ev("e4", "Lunch", "2026-11-17T12:00:00Z")},
        "tasks": {"t1": tk("File the quarterly tax estimate", "2026-11-20"), "t2": tk("Call the bank", "2026-11-17"),
                  "t3": tk("Renew passport", "2026-12-01"), "t4": tk("Book hotel")}}
CUR = {"day": DAY,
       "calendar": {"e1": ev("e1", "Dentist", "2026-11-19T10:00:00Z"),             # moved a day
                    "e2": ev("e2", "Board call", "2026-11-20T15:00:00Z"),          # same
                    "e3": ev("e3", "Flight to Exampleville", "2026-11-22T08:00:00Z", cancelled=True),   # cancelled
                    "e5": ev("e5", "Site visit", "2026-11-21T09:00:00Z"),          # new
                    "e6": ev("e6", "Conference", "2027-03-01T09:00:00Z")},         # new, far away: not this window
       "tasks": {"t1": tk("File the quarterly tax estimate", "2026-11-27"),        # due moved
                 "t3": tk("Renew passport", "2026-12-01"),
                 "t4": tk("Book hotel", done=True),                                # completed: settled
                 "t5": tk("Send the invoice", "2026-11-18")}}                      # new  (t2 is gone: dropped)


def ids(lst):
    return sorted(e["id"] for e in lst)


class Compare(unittest.TestCase):
    def test_a_moved_event_and_a_dropped_task_are_caught(self):
        r = delta.compare_cal_tasks(PREV, CUR, DAY)
        self.assertEqual(ids(r["calendar"]["changed"]), ["e1"], r)
        self.assertIn("moved from 2026-11-18T10:00 to 2026-11-19T10:00", r["calendar"]["changed"][0]["evidence"])
        self.assertEqual(ids(r["tasks"]["missing"]), ["t2"], r)
        self.assertTrue(any("Call the bank" in q and "gone from the list" in q for q in r["questions"]))

    def test_new_changed_and_missing_for_both_sources(self):
        r = delta.compare_cal_tasks(PREV, CUR, DAY)
        self.assertEqual(ids(r["calendar"]["new"]), ["e5"])                  # the far-away conference is not this window
        self.assertEqual(ids(r["calendar"]["missing"]), ["e3", "e4"])           # e3 cancelled, e4 gone
        self.assertIn("cancelled", r["calendar"]["missing"][0]["evidence"])
        self.assertIn("gone", r["calendar"]["missing"][1]["evidence"])
        self.assertEqual(ids(r["tasks"]["new"]), ["t5"])
        self.assertEqual(ids(r["tasks"]["changed"]), ["t1", "t4"])
        self.assertIn("due date changed from 2026-11-20 to 2026-11-27", [e for e in r["tasks"]["changed"] if e["id"] == "t1"][0]["evidence"])

    def test_a_completed_task_is_settled_not_a_surprise_and_unchanged_things_are_quiet(self):
        r = delta.compare_cal_tasks(PREV, CUR, DAY)
        done = [e for e in r["tasks"]["changed"] if e["id"] == "t4"][0]
        self.assertEqual(done["settled"], "completed")
        self.assertNotIn("question", done)
        self.assertFalse(any("Board call" in q or "passport" in q for q in r["questions"]))
        self.assertEqual(delta.compare_cal_tasks(PREV, PREV, DAY)["questions"], [])

    def test_the_snapshot_reads_a_real_database_and_run_merges_all_three_sources(self):
        import tempfile
        p = os.path.join(tempfile.mkdtemp(prefix="step12-"), "s.db")
        con = step3_fixture.new_db(p)
        con.execute("INSERT INTO calendar_events(id,start,end,summary,status) VALUES('e1','2026-11-19T10:00:00Z','2026-11-19T11:00:00Z','Dentist','confirmed')")
        con.execute("INSERT INTO calendar_events(id,start,end,summary,status) VALUES('old','2026-11-01T10:00:00Z','2026-11-01T11:00:00Z','Past thing','confirmed')")
        con.execute("INSERT INTO tasks(id,list_id,title,status,due,updated) VALUES('t5','l','Send the invoice','needsAction','2026-11-18','2026-11-15T00:00:00Z')")
        con.execute("INSERT INTO tasks(id,list_id,title,status,due,updated) VALUES('t9','l','Ancient','completed','2020-01-01','2020-01-02T00:00:00Z')")
        con.commit()
        snap = delta.snapshot(con, DAY)
        self.assertEqual((sorted(snap["calendar"]), sorted(snap["tasks"])), (["e1"], ["t5"]))      # past event and ancient done task left out
        out = delta.run(con, 0, 10 ** 13, prev_snapshot=PREV, day=DAY)
        self.assertTrue(all("source" in e for k in ("new", "changed", "missing") for e in out[k]))
        self.assertTrue({"email", "calendar", "tasks"} >= {e["source"] for k in ("new", "changed", "missing") for e in out[k]})
        self.assertIsNone(delta.run(con, 0, 10 ** 13)["calendar_tasks"])      # no earlier snapshot: not compared, said so by None
        con.close()


class Questions(unittest.TestCase):
    def test_each_source_keeps_a_third_of_the_questions_even_when_mail_floods(self):
        mail = ["You wrote to p%d@x.test on 2026-11-01 and no reply: ?" % i for i in range(40)] + ["New sender z%d@x.test: who?" % i for i in range(10)]
        evts = ["Calendar: 'Dentist' moved: what knocks on?", "Calendar: 'Flight' is no longer on the calendar: on purpose?"]
        tasks = ["Task: 'Call the bank' is gone from the list: dropped?"]
        kept, rest = morning.rank_questions(mail + evts + tasks, lambda a: 0, cap=15)
        self.assertEqual(len(kept), 15)
        for q in evts + tasks:
            self.assertIn(q, kept)
        self.assertEqual(rest, 53 - 15)

    def test_quiet_sources_give_their_slots_to_the_others(self):
        mail = ["New sender z%d@x.test: who?" % i for i in range(20)]
        kept, rest = morning.rank_questions(mail, lambda a: 0, cap=15)
        self.assertEqual((len(kept), rest), (15, 5))


def cal_items(n):
    return [{"title": "Event number %02d about the planning of things" % i, "start": "2026-11-%02dT10:00:00Z" % (17 + i % 10), "id": "c%d" % i} for i in range(n)]


def task_items(n):
    return [{"title": "Task number %02d, something to do soon" % i, "status": "open", "due": "2026-11-%02d" % (17 + i % 10), "id": "k%d" % i} for i in range(n)]


class Prompt(t4.Base):
    def setUp(self):
        t4.Base.setUp(self)
        self.recs = os.path.join(self.env.root, "recs")
        self.t = t4.triage_of({"needs_me": "cant_tell", "do_or_know": "cant_tell", "how_soon": "cant_tell", "life_area": "cant_tell"})

    def flood(self, n, size=9000):
        for i in range(n):
            self.env.deliver("th-%d" % i, "msg-%d" % i, "Dana <d%d@h.test>" % i, "Long note %d" % i, "2026-11-15 08:00", "read-x", self.t,
                             ("A long made-up paragraph number %d about nothing in particular. " % i) * (size // 60))
        self.env.ingest()

    def test_a_flood_of_email_cannot_push_out_the_calendar_and_tasks(self):
        self.flood(6)
        evts, tasks = cal_items(30), task_items(30)
        m = t4.FakeModel(self.env, t4.reply())
        out = morning.run_morning(m, DAY, "desk-a", self.recs, calendar=evts, tasks=tasks, budget=60000, dry_run=True)
        self.assertTrue(out["ok"])
        c = out["counts"]
        # all of the calendar and tasks fit their third; mail got what they did not need, so some threads are skipped
        self.assertEqual((c["calendar_items"], c["tasks_shown"]), (30, 30), c)
        self.assertGreater(c["skipped_by_reason"].get("over_prompt_budget", 0), 0, c)
        sh = c["prompt_share_chars"]
        self.assertLessEqual(sh["calendar"], sh["a_third"])
        self.assertLessEqual(sh["email_transcripts"] + sh["calendar"] + sh["tasks"], 60000)
        self.assertEqual(sh["email_budget"], 60000 - sh["calendar"] - sh["tasks"])

    def test_a_source_that_is_too_big_is_trimmed_to_its_third_and_the_rest_counted(self):
        evts = cal_items(200)
        kept, cut = morning.fit_to_share(evts, 6000)
        self.assertEqual(len(kept) + len(cut), 200)
        self.assertGreater(len(cut), 0)
        self.assertLessEqual(len(json.dumps(morning._no_ids(kept), indent=1, sort_keys=True)), 6000)
        self.assertEqual(kept, evts[:len(kept)])                  # the front (most important) is kept
        b = morning.source_budgets(300000, 500, 90000)
        self.assertEqual((b["share"], b["email"]), (100000, 300000 - 500 - 90000))

    def test_the_rules_name_the_three_as_equal_and_ids_stay_out_of_the_prompt(self):
        self.assertIn("Email, calendar and tasks weigh equally", morning.MORNING_RULES)
        files = morning.build_files(DAY, "desk-a", None, None, None, None, task_items(2), cal_items(2), [], None)
        p = morning._rh().whole_prompt(morning.MORNING_TASK, files, rules=morning.MORNING_RULES)
        self.assertNotIn('"id"', p)
        self.assertIn("Event number 00", p)


class Accounting(t4.Base):
    def setUp(self):
        t4.Base.setUp(self)
        self.recs = os.path.join(self.env.root, "recs")
        self.sd = delta.compare_cal_tasks(PREV, CUR, DAY)
        for s in ("calendar", "tasks"):
            for k in ("new", "changed", "missing"):
                for e in self.sd[s][k]:
                    e["asked"] = "settled" not in e

    def go(self, sd, **kw):
        return morning.run_morning(t4.FakeModel(self.env, t4.reply()), DAY, "desk-a", self.recs, calendar=cal_items(3), tasks=task_items(3), source_delta=sd, **kw)

    def test_every_new_item_of_each_source_is_accounted_and_the_old_fields_are_untouched(self):
        out = self.go(self.sd)
        self.assertTrue(out["ok"], out)
        pl = out["proof_line"]
        self.assertTrue(pl.startswith("morning read %s (desk-a): 0 new of 0 examined; used 0, sorted out by triage 0, skipped with a reason 0; "
                                      "flagged-as-needing-him dropped: 0; every new email accounted for" % DAY), pl)
        self.assertIn("calendar 1 new, 1 changed, 2 missing: 4 handed to the model, 0 left out with a reason", pl)
        self.assertIn("tasks 1 new, 2 changed, 1 missing: 3 handed to the model, 1 left out with a reason", pl)     # the completed one is settled
        c = out["accounting"]["counts"]
        self.assertEqual(c["new"], 0)                                   # existing keys keep their meaning
        self.assertEqual(c["by_source"]["tasks"]["left_out"], {"completed": 1})
        self.assertTrue(all(c["by_source"][s]["accounted"] for s in ("calendar", "tasks", "email")))

    def test_a_new_calendar_item_nobody_accounted_for_stops_the_read(self):
        for e in self.sd["calendar"]["new"]:
            e["asked"] = False                    # not asked, not in the list shown (ids c0..c2), no reason given
        out = self.go(self.sd)
        self.assertFalse(out["ok"], out)
        self.assertIn("unaccounted:calendar:e5", out["problems"])
        self.assertIn("NOT ACCOUNTED", out["proof_line"])
        self.assertIsNone(out.get("record_path"))

    def test_a_dropped_task_left_out_needs_a_stated_reason(self):
        for e in self.sd["tasks"]["missing"]:
            e["asked"] = False
        self.assertFalse(self.go(self.sd)["ok"])
        for e in self.sd["tasks"]["missing"]:
            e["left_out"] = "over_question_cap"
        out = self.go(self.sd)
        self.assertTrue(out["ok"], out)
        self.assertIn("2 handed to the model, 2 left out with a reason", out["proof_line"])

    def test_calendar_changes_alone_still_make_a_read_after_a_staged_day(self):
        self.go(self.sd)                                               # stages
        out = self.go(self.sd)                                         # nothing new in mail, but calendar/task changes: not skipped
        self.assertNotIn("nothing new since the staged write-up", out["proof_line"])


class HandRunSources(t4.Base):
    """two real hand-runs against a scratch database: the first takes the picture, the second sees the moved event and the dropped task"""

    def setUp(self):
        t4.Base.setUp(self)
        import tempfile
        self.notes = os.path.join(self.env.root, "notes")
        self.db = os.path.join(self.env.root, "scratch.db")
        con = step3_fixture.new_db(self.db)
        con.execute("INSERT INTO calendar_events(id,start,end,summary,status) VALUES('e1','2026-11-18T10:00:00Z','2026-11-18T11:00:00Z','Dentist','confirmed')")
        con.execute("INSERT INTO calendar_events(id,start,end,summary,status) VALUES('e2','2026-11-20T10:00:00Z','2026-11-20T11:00:00Z','Board call','confirmed')")
        con.execute("INSERT INTO tasks(id,list_id,title,status,due,updated) VALUES('t1','l','Send proposal','needsAction','2026-11-18','2026-11-10T00:00:00Z')")
        con.execute("INSERT INTO tasks(id,list_id,title,status,due,updated) VALUES('t2','l','Call the bank','needsAction','2026-11-17','2026-11-10T00:00:00Z')")
        con.commit()
        con.close()
        self.lm = os.path.join(self.env.root, "life-map.md")
        t4.write(self.lm, "## Weekly Win\nShip the proposal.\n")
        os.makedirs(os.path.join(self.env.drop, "deliveries"))

    def hand(self, day):
        lines = []
        rc = morning.hand_run(["--drop", self.env.drop, "--notes-root", self.notes, "--db", self.db, "--life-map", self.lm, "--day", day,
                               "--mailroom-uid", str(os.getuid()), "--i-know-this-calls-the-real-model"],
                              model=t4.FakeModel(self.env, t4.reply()), out=lines.append)
        return rc, "\n".join(lines)

    def test_the_second_read_catches_a_moved_event_and_a_dropped_task(self):
        rc, text = self.hand("2026-11-16")
        self.assertEqual(rc, 0, text)
        self.assertIn("first look", text)
        self.assertTrue(os.path.exists(os.path.join(transcripts.catalogue_dir(), "desk-a-tasks-seen.json")))
        import step3_fixture
        con = step3_fixture.rw(self.db)
        con.execute("UPDATE calendar_events SET start='2026-11-19T10:00:00Z', end='2026-11-19T11:00:00Z' WHERE id='e1'")
        con.execute("DELETE FROM tasks WHERE id='t2'")
        con.execute("INSERT INTO tasks(id,list_id,title,status,due,updated) VALUES('t3','l','Pay the invoice','needsAction','2026-11-18','2026-11-16T00:00:00Z')")
        con.commit()
        con.close()
        rc, text = self.hand("2026-11-17")
        self.assertEqual(rc, 0, text)
        self.assertIn("calendar 0 new, 1 changed, 0 missing: 1 handed", text)
        self.assertIn("tasks 1 new, 0 changed, 1 missing: 2 handed", text)
        self.assertIn("(email 0, calendar 1, tasks 2)", text)
        rec = t4.read(os.path.join(self.notes, "desks", "desk-a", "records", "context", "2026-11-17-desk-a.md"))
        self.assertIn("Dentist", rec)
        self.assertIn("Call the bank", rec)


if __name__ == "__main__":
    unittest.main(verbosity=1)
