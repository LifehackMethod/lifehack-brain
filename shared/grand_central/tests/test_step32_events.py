"""Phase 3 step 3.2: events built by code from the calendar mirror. Temp databases, synthetic mail and calendar only.
Each planted case runs a deliberately BROKEN builder first and requires the check to catch it (the check fails on the plant),
then the real builder and requires it to pass."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import glob
import json
import re
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import migrate, model_check, store, store_events as se, store_graph as sg  # noqa: E402
import scorecard  # noqa: E402

ME = "me@example.test"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.tmp.name, "rig.db")
        c = sqlite3.connect(self.p, isolation_level=None)
        for path in sorted(glob.glob(os.path.join(ROOT, "migrations", "*.sql"))):   # in order; contiguity is migrate.py's own test
            migrate.apply_file(c, path, int(os.path.basename(path)[:3]))
        c.close()
        store.set_path(self.p)
        self.n = 0

    def tearDown(self):
        store.set_path(None)
        self.tmp.cleanup()

    def x(self, sql, args=()):
        c = sqlite3.connect(self.p, isolation_level=None)
        try:
            return c.execute(sql, args).fetchall()
        finally:
            c.close()

    # ---- synthetic data
    def event(self, eid, start, attendees, organizer=ME, summary="Standup", status="confirmed", location=None):
        self.x("INSERT OR REPLACE INTO calendar_events(id,start,end,all_day,status,organizer_email,attendee_emails,summary,location,description,gate_verdict) "
               "VALUES(?,?,?,0,?,?,?,?,?,NULL,'NONE')",
               (eid, start, start[:11] + "23:00:00Z", status, organizer, json.dumps(attendees), summary, location))

    def mail(self, thread, frm, to, sent, bulk=False):
        self.n += 1
        self.x("INSERT INTO messages(id,thread_id,internal_date,label_ids,from_addr,to_addrs,cc_addrs,subject,is_sent,list_id,"
               "list_unsubscribe_present,dmarc_pass) VALUES(?,?,?,?,?,?,?,?,?,?,?,1)",
               ("m%d" % self.n, thread, 1700000000000 + self.n * 1000, "[]", frm, json.dumps(to), "[]", "s", 1 if sent else 0,
                "list.example.test" if bulk else None, 1 if bulk else 0))

    def conversation(self, addr, bulk=False):
        """real two-way history: they write, he answers, in one thread"""
        self.mail("t-" + addr, addr, [ME], False, bulk)
        self.mail("t-" + addr, ME, [addr], True)

    def build(self, **k):
        with store._write() as c:
            res = se.build_events(c, starters=k.get("starters", []))
            if k.get("senders", True):
                import senders       # as production: pull.py runs the senders step right after the events step
                senders.build_senders(c)
            return res

    def person_of(self, addr):
        return self.x("SELECT p.key FROM kg_things ad JOIN kg_links l ON l.from_id=ad.id AND l.kind='address_of' AND l.replaced_by IS NULL "
                      "JOIN kg_things p ON p.id=l.to_id WHERE ad.key=?", ("address:" + addr,))

    def involves(self, eid):
        return {r[0] for r in self.x("SELECT t.key FROM kg_links l JOIN kg_things t ON t.id=l.to_id JOIN kg_things e ON e.id=l.from_id "
                                     "WHERE e.key=? AND l.kind='involves' AND l.replaced_by IS NULL", ("event:calendar:" + eid,))}

    def counts(self):
        return [self.x("SELECT count(*) FROM %s" % t)[0][0] for t in ("kg_things", "kg_facts", "kg_links", "thing_keys")]


class Events(Base):
    def test_an_event_has_its_facts_and_its_attendees(self):
        self.conversation("pat@example.test")
        self.event("e1", "2026-12-01T10:00:00Z", [ME, "pat@example.test", "stranger@example.test"], location="Room 4")
        r = self.build()
        self.assertEqual(r["new"], 1)
        self.assertEqual(self.x("SELECT kind,name,starts_at FROM kg_things WHERE key='event:calendar:e1'"),
                         [("event", "Standup", "2026-12-01T10:00:00Z")])
        facts = dict(self.x("SELECT fact_key, value FROM kg_facts f JOIN kg_things t ON t.id=f.thing_id WHERE t.key='event:calendar:e1' AND replaced_by IS NULL"))
        self.assertEqual((facts["place"], facts["event_status"], facts["starts_at"]), ("Room 4", "confirmed", "2026-12-01T10:00:00Z"))
        got = self.involves("e1")
        self.assertIn("person:me", got)                                   # his own address is him
        self.assertIn("address:stranger@example.test", got)               # no history: stays an address
        self.assertEqual(len(got), 3)

    # ---- planted 1: an attendee with no history stays an address
    def _no_history_check(self):
        self.event("e1", "2026-12-01T10:00:00Z", [ME, "nobody@example.test"])
        self.build()
        if self.person_of("nobody@example.test") or "address:nobody@example.test" not in self.involves("e1"):
            raise AssertionError("an attendee with no history became a person")

    def test_PLANTED_no_history_attendee_stays_an_address(self):
        with mock.patch.object(se._People, "two_way", lambda self, a: True):          # the plant: admit everybody
            with self.assertRaises(AssertionError):
                self._no_history_check()
        self.tearDown(); self.setUp()
        self._no_history_check()                                                       # the real builder passes
        self.assertEqual(self.x("SELECT count(*) FROM kg_things WHERE created_by='code' AND kind='person' AND key<>'person:me'")[0][0], 0)

    # ---- planted 2: a bulk or automated sender is never made a person
    def _bulk_check(self):
        self.conversation("news@example.test", bulk=True)          # they write bulk mail, he replied once
        self.conversation("noreply@example.test")                  # an automated address
        self.event("e1", "2026-12-01T10:00:00Z", [ME, "news@example.test", "noreply@example.test"])
        self.build()
        if self.person_of("news@example.test") or self.person_of("noreply@example.test"):
            raise AssertionError("a bulk or automated sender became a person")

    def test_PLANTED_bulk_sender_is_not_made_a_person(self):
        with mock.patch.object(se, "looks_automated", lambda a: False), mock.patch.object(se, "AUTO_SHARE", 2.0):   # the plant: no bulk guard
            with self.assertRaises(AssertionError):
                self._bulk_check()
        self.tearDown(); self.setUp()
        self._bulk_check()

    def test_two_way_history_makes_a_person_once_and_starter_list_and_his_confirmation_count(self):
        self.conversation("pat@example.test")
        self.event("e1", "2026-12-01T10:00:00Z", [ME, "pat@example.test", "vip@example.test", "his@example.test"])
        sg_ = sg
        with store._write() as c:   # his confirmation: his@ is Hal
            sg_.record_answer(c, "Who is his@?", "that is Hal", "owner-session", subject_kind="address", subject_name="his@example.test",
                              fact_key="link:address_of", value="person:hal")
        self.build(starters=["VIP@example.test"])
        self.assertEqual(len(self.person_of("pat@example.test")), 1)
        self.assertEqual(len(self.person_of("vip@example.test")), 1)
        self.assertIn("person:hal", self.involves("e1"))
        before = self.person_of("pat@example.test")
        self.build(starters=["vip@example.test"])
        self.assertEqual(self.person_of("pat@example.test"), before)   # same key, no second person
        self.assertEqual(self.x("SELECT count(*) FROM thing_keys WHERE made_from='event-admit:pat@example.test'")[0][0], 1)

    # ---- planted 3: a re-run changes nothing
    def _rerun_check(self):
        self.conversation("pat@example.test")
        self.event("e1", "2026-12-01T10:00:00Z", [ME, "pat@example.test", "x@example.test"], location="Room")
        self.build()
        first = self.counts()
        r = self.build()
        if self.counts() != first:
            raise AssertionError("a re-run changed the database: %s -> %s" % (first, self.counts()))
        return r

    def test_PLANTED_rerun_makes_no_duplicates(self):
        with mock.patch.object(se, "_current_fact", lambda *a: None):                  # the plant: always rewrite the facts
            with self.assertRaises(AssertionError):
                self._rerun_check()
        self.tearDown(); self.setUp()
        r = self._rerun_check()
        self.assertEqual((r["new"], r["links_added"], r["people_made"]), (0, 0, 0))

    # ---- planted 4: a moved event changes its time, the old row is kept
    def _move_check(self):
        self.event("e1", "2026-12-01T10:00:00Z", [ME])
        self.build()
        self.event("e1", "2026-12-02T15:00:00Z", [ME])
        self.build()
        cur = self.x("SELECT value FROM kg_facts f JOIN kg_things t ON t.id=f.thing_id WHERE t.key='event:calendar:e1' AND fact_key='starts_at' AND replaced_by IS NULL")
        old = self.x("SELECT value FROM kg_facts f JOIN kg_things t ON t.id=f.thing_id WHERE t.key='event:calendar:e1' AND fact_key='starts_at' AND replaced_by IS NOT NULL")
        if cur != [("2026-12-02T15:00:00Z",)] or old != [("2026-12-01T10:00:00Z",)]:
            raise AssertionError("the move was not a supersession: current %s old %s" % (cur, old))

    def test_PLANTED_a_moved_event_keeps_the_old_row(self):
        real = sg.assert_fact

        def in_place(con, tid, fk, val, *a, **k):          # the plant: edit the fact where it stands
            r = con.execute("SELECT id FROM kg_facts WHERE thing_id=? AND fact_key=? AND replaced_by IS NULL", (tid, fk)).fetchone()
            if r:
                con.execute("UPDATE kg_facts SET value=? WHERE id=?", (val, r[0]))
                return r[0]
            return real(con, tid, fk, val, *a, **k)
        with mock.patch.object(sg, "assert_fact", in_place):
            with self.assertRaises(AssertionError):
                self._move_check()
        self.tearDown(); self.setUp()
        self._move_check()
        self.assertEqual(self.x("SELECT starts_at FROM kg_things WHERE key='event:calendar:e1'"), [("2026-12-02T15:00:00Z",)])

    def test_cancelled_is_a_new_status_fact(self):
        self.event("e1", "2026-12-01T10:00:00Z", [ME])
        self.build()
        self.event("e1", "2026-12-01T10:00:00Z", [ME], status="cancelled")
        r = self.build()
        self.assertEqual(r["status_changed"], 1)
        self.assertEqual(self.x("SELECT count(*) FROM kg_facts f JOIN kg_things t ON t.id=f.thing_id WHERE t.key='event:calendar:e1' AND fact_key='event_status'")[0][0], 2)

    def test_an_address_that_later_qualifies_is_upgraded_and_the_old_link_kept(self):
        self.event("e1", "2026-12-01T10:00:00Z", [ME, "pat@example.test"])
        self.build()
        self.assertIn("address:pat@example.test", self.involves("e1"))
        self.conversation("pat@example.test")
        r = self.build()
        got = self.involves("e1")
        self.assertNotIn("address:pat@example.test", got)
        self.assertEqual(len(self.person_of("pat@example.test")), 1)
        self.assertEqual(r["links_ended"], 2)   # pat's address link, and his own address now known as him
        old = self.x("SELECT l.replaced_by FROM kg_links l JOIN kg_things t ON t.id=l.to_id WHERE t.key='address:pat@example.test' AND l.kind='involves'")
        self.assertEqual(len(old), 1)
        self.assertIsNotNone(old[0][0])      # kept, superseded by the person link

    def test_no_project_is_stored_by_code_and_his_word_survives(self):
        self.event("e1", "2026-12-01T10:00:00Z", [ME])
        self.build()
        self.assertEqual(self.x("SELECT count(*) FROM kg_links WHERE kind='part_of' AND from_id=(SELECT id FROM kg_things WHERE key='event:calendar:e1')")[0][0], 0)
        # his word goes through record_answer with the event's own key; the builder must leave it alone
        with store._write() as c:
            sg.record_answer(c, "Which project is Standup?", "the launch", "owner-session", subject_kind="event", subject_name="Standup",
                             fact_key="link:part_of", value="project:launch")
        self.build()
        self.assertEqual(self.x("SELECT count(*) FROM kg_links WHERE kind='part_of' AND who='owner' AND replaced_by IS NULL")[0][0], 1)


class WiderRule(Base):
    """Coordinator ruling 2026-11-16: a contact is a person if (1) mail two-way, (2) 2+ real shared events, (3) he named them."""
    def two_events(self, addr, n=2, others=(), start="2026-12-%02dT10:00:00Z"):
        for i in range(n):
            self.event("%s-%d" % (addr, i), start % (i + 1), [ME, addr] + list(others))

    def _rule2_check(self):
        self.mail("tt", ME, ["x@example.test"], True)                              # his own address is known as him
        self.two_events("pair@example.test")                                         # qualifies: 2 small shared events
        self.event("once@example.test-0", "2026-12-05T10:00:00Z", [ME, "once@example.test"])   # one event: not enough
        crowd = ["c%d@example.test" % i for i in range(12)]
        self.two_events("mass@example.test", others=crowd)                          # two mass invites (14 people): do not count
        self.two_events("room@group.calendar.google.com")                        # a room calendar: never
        self.event("x-0", "2026-12-09T10:00:00Z", [ME, "gone@example.test"], status="cancelled")
        self.event("x-1", "2026-12-10T10:00:00Z", [ME, "gone@example.test"], status="cancelled")   # cancelled: do not count
        r = self.build()
        bad = [a for a in ("once@example.test", "mass@example.test", "room@group.calendar.google.com", "gone@example.test", "c1@example.test")
               if self.person_of(a)]
        if bad or not self.person_of("pair@example.test"):
            raise AssertionError("rule 2 wrong: %s, pair person=%s" % (bad, self.person_of("pair@example.test")))
        return r

    def test_PLANTED_rule2_shared_events(self):
        with mock.patch.object(se, "ATTENDEE_CAP", 1000), mock.patch.object(se, "SHARED_MIN", 1), \
                mock.patch.object(se, "BOT_DOMAIN", re.compile("^$")):               # the plant: no cap, one event is enough, rooms count
            with self.assertRaises(AssertionError):
                self._rule2_check()
        self.tearDown(); self.setUp()
        r = self._rule2_check()
        self.assertEqual(r["by_rule"]["2_shared_events"], 1)

    def _rule3_check(self):
        with store._write() as c:   # his word on an address (a tier), no mail, no shared events
            sg.record_answer(c, "How much does named@ matter?", "high", "owner-session", subject_kind="address",
                             subject_name="named@example.test", fact_key="tier", value="high")
            sg.assert_fact(c, sg.thing(c, "address", "guessed@example.test"), "tier", "high", "ai_guess", "guess", "code")
        self.event("e1", "2026-12-01T10:00:00Z", [ME, "named@example.test", "guessed@example.test"])
        r = self.build()
        if not self.person_of("named@example.test") or self.person_of("guessed@example.test"):
            raise AssertionError("rule 3 wrong: named=%s guessed=%s" % (self.person_of("named@example.test"), self.person_of("guessed@example.test")))
        return r

    def test_PLANTED_rule3_named_by_him_not_by_a_guess(self):
        with mock.patch.object(se._People, "named", lambda self, a: self.con.execute(
                "SELECT 1 FROM kg_things ad JOIN kg_facts f ON f.thing_id=ad.id WHERE ad.key=?", ("address:" + a,)).fetchone() is not None):
            with self.assertRaises(AssertionError):                                   # the plant: any writer's fact counts
                self._rule3_check()
        self.tearDown(); self.setUp()
        r = self._rule3_check()
        self.assertEqual(r["by_rule"]["3_named_by_him"], 1)

    def _automated_check(self):
        self.two_events("noreply@example.test")                                      # group 2 bot
        self.two_events("weekendlist@example.test")
        with store._write() as c:                                                    # group 3 bot: he has a rule on it
            sg.record_answer(c, "Where does it go?", "trash", "owner-session", subject_kind="address",
                             subject_name="alerts@example.test", fact_key="importance", value="low")
        self.event("e9", "2026-12-20T10:00:00Z", [ME, "alerts@example.test", "pat@example.test"])
        self.conversation("pat@example.test")                                        # a real one still goes through
        r = self.build()
        bad = [a for a in ("noreply@example.test", "weekendlist@example.test", "alerts@example.test") if self.person_of(a)]
        if bad or not self.person_of("pat@example.test"):
            raise AssertionError("list/bot check wrong: %s" % bad)
        return r

    def test_PLANTED_list_and_bot_check_over_all_three_groups(self):
        with mock.patch.object(se, "looks_automated", lambda a: False):
            with self.assertRaises(AssertionError):
                self._automated_check()
        self.tearDown(); self.setUp()
        r = self._automated_check()
        self.assertEqual(sorted(r["excluded_automated"]), ["alerts@example.test", "noreply@example.test", "weekendlist@example.test"])

    def _role_check(self):
        for a in ("contact@example.test", "info@example.test", "hello@example.test", "team@example.test", "support@example.test"):
            self.conversation(a)
        self.conversation("elle@example.test")                                       # a real person at his own company
        with store._write() as c:                                                    # he named this one
            sg.record_answer(c, "Who is hello2?", "high", "owner-session", subject_kind="address", subject_name="info2@example.test",
                             fact_key="tier", value="high")
        self.conversation("info2@example.test")
        self.event("e1", "2026-12-01T10:00:00Z", [ME, "contact@example.test", "info@example.test", "hello@example.test", "team@example.test",
                                                  "support@example.test", "elle@example.test", "info2@example.test"])
        self.build()
        bad = [a for a in ("contact", "info", "hello", "team", "support") if self.person_of(a + "@example.test")]
        if bad or not self.person_of("elle@example.test") or not self.person_of("info2@example.test"):
            raise AssertionError("role inboxes wrong: %s" % bad)

    def test_PLANTED_role_inboxes_are_not_people_unless_he_named_them(self):
        with mock.patch.object(se, "is_role_inbox", lambda a: False):
            with self.assertRaises(AssertionError):
                self._role_check()
        self.tearDown(); self.setUp()
        self._role_check()

    def _trash_check(self):
        with store._write() as c:   # he only ever ruled "trash" on these; a rule also applies to one of them
            for a in ("tracker@example.test", "deals@example.test"):
                sg.record_answer(c, "Where does %s go?" % a, "trash", "owner-session", subject_kind="address", subject_name=a,
                                 fact_key="destination", value="trash")
            sg.record_answer(c, "Which label?", "notifications", "owner-session", subject_kind="address", subject_name="deals@example.test",
                             fact_key="label", value="Notifications")
            sg.record_answer(c, "How much does Gina matter?", "high", "owner-session", subject_kind="address", subject_name="gina@example.test",
                             fact_key="tier", value="high")
        self.event("e1", "2026-12-01T10:00:00Z", [ME, "tracker@example.test", "deals@example.test", "gina@example.test"])
        self.build()
        bad = [a for a in ("tracker@example.test", "deals@example.test") if self.person_of(a)]
        if bad or not self.person_of("gina@example.test"):
            raise AssertionError("a trash ruling named somebody: %s" % bad)

    def test_PLANTED_a_sender_he_only_ruled_trash_is_not_a_person(self):
        def any_owner_fact(self, addr):          # the plant: the old rule, any owner fact names them
            return self.con.execute("SELECT 1 FROM kg_facts f JOIN kg_things ad ON ad.id=f.thing_id WHERE ad.key=? AND f.who='owner'",
                                    ("address:" + addr,)).fetchone() is not None
        with mock.patch.object(se._People, "named", any_owner_fact):
            with self.assertRaises(AssertionError):
                self._trash_check()
        self.tearDown(); self.setUp()
        self._trash_check()

    def _retire_check(self):
        for a in ("old@example.test", "graded@example.test"):
            self.event("e-" + a, "2026-12-01T10:00:00Z", [ME, a])
        self.build(starters=["old@example.test", "graded@example.test"])
        gk = self.person_of("graded@example.test")[0][0]
        with store._write() as c:   # his grade on the PERSON
            sg.record_answer(c, "How much does Graded matter?", "high", "owner-session", subject_kind="person", subject_name=gk.split(":", 1)[1],
                             fact_key="tier", value="high")
        r = self.build(starters=[])             # the starter list no longer names them: re-evaluated, the first has nothing left
        old = self.x("SELECT retired_at IS NOT NULL FROM kg_things WHERE key=?", (self.x("SELECT key FROM thing_keys WHERE made_from='event-admit:old@example.test'")[0][0],))
        grd = self.x("SELECT retired_at IS NOT NULL FROM kg_things WHERE key=?", (gk,))
        if old != [(1,)] or grd != [(0,)] or r["retired_persons"] != ["old@example.test"] or self.person_of("old@example.test"):
            raise AssertionError("retire wrong: old=%s graded=%s %s" % (old, grd, r["retired_persons"]))
        return r

    def test_PLANTED_a_person_who_no_longer_qualifies_is_retired_but_one_with_his_grade_stays(self):
        with mock.patch.object(se, "_retire_unqualified", lambda con, people: []):     # the plant: nothing is ever retired
            with self.assertRaises(AssertionError):
                self._retire_check()
        self.tearDown(); self.setUp()
        self._retire_check()
        # ... and the person is kept as a row, the event points at the address again, and qualifying again brings the same person back
        self.assertIn("address:old@example.test", self.involves("e-old@example.test"))
        key = self.x("SELECT key FROM thing_keys WHERE made_from='event-admit:old@example.test'")[0][0]
        self.build(starters=["old@example.test"])
        self.assertEqual(self.person_of("old@example.test"), [(key,)])
        self.assertEqual(self.x("SELECT retired_at FROM kg_things WHERE key=?", (key,)), [(None,)])

    def test_PLANTED_retire_ignores_his_word_is_caught(self):
        def retire_everyone(con, people):
            out = []
            for pid, key, mf in con.execute("SELECT t.id, t.key, k.made_from FROM kg_things t JOIN thing_keys k ON k.key=t.key WHERE k.made_from LIKE 'event-admit:%'").fetchall():
                hit, ex = people.verdict(mf.split(":", 1)[1])
                if not hit or ex:
                    con.execute("UPDATE kg_things SET retired_at='x' WHERE id=?", (pid,))
                    out.append(mf.split(":", 1)[1])
            return out
        with mock.patch.object(se, "_retire_unqualified", retire_everyone):          # the plant: retires the graded person too
            with self.assertRaises(AssertionError):
                self._retire_check()

    def test_an_existing_person_stays_even_with_a_bot_like_address(self):
        with store._write() as c:
            p = sg.thing(c, "person", "Old Friend")
            sg.add_link(c, sg.thing(c, "address", "news@example.test"), "address_of", p, "code", "likely", "legacy")
        self.event("e1", "2026-12-01T10:00:00Z", [ME, "news@example.test"])
        r = self.build()
        self.assertEqual(r["already_persons"], 1)
        self.assertEqual(len(self.person_of("news@example.test")), 1)


class Rebuild(Base):
    def seed(self):
        with store._write() as c:
            sg.copy_legacy(c)                    # as in real history: the legacy copy and the engine's settings were seeded once
            import common as ec
            ec.seed_settings(c)
        self.conversation("pat@example.test")
        self.event("e1", "2026-12-01T10:00:00Z", [ME, "pat@example.test", "x@example.test"], location="Room")
        self.event("e2", "2026-12-03T10:00:00Z", [ME], summary="Lunch")
        self.build()
        self.event("e1", "2026-12-02T10:00:00Z", [ME, "pat@example.test"])   # moved, and x@ dropped
        self.build()

    def test_rebuild_reproduces_events_and_gc_check_is_clean(self):
        self.seed()
        res = model_check.check(self.p)
        self.assertTrue(res["clean"], res["sample"])
        self.assertEqual(res["rebuild"]["events"]["events"], 2)

    # ---- planted 5: a rebuild that loses or changes an event is caught
    def test_PLANTED_a_missing_event_or_changed_time_is_caught(self):
        self.seed()
        res = model_check.check(self.p, mutate=lambda con: con.execute("DELETE FROM kg_things WHERE key='event:calendar:e2'") if
                                (con.execute("DELETE FROM kg_links WHERE from_id=(SELECT id FROM kg_things WHERE key='event:calendar:e2')"),
                                 con.execute("DELETE FROM kg_facts WHERE thing_id=(SELECT id FROM kg_things WHERE key='event:calendar:e2')")) else None)
        self.assertFalse(res["clean"])
        self.assertIn("things live_only", res["by_kind"])
        res = model_check.check(self.p, mutate=lambda con: con.execute(
            "UPDATE kg_facts SET value='2030-01-01' WHERE fact_key='starts_at' AND replaced_by IS NULL"))
        self.assertFalse(res["clean"])
        res = model_check.check(self.p)
        self.assertTrue(res["clean"], res["sample"])


if __name__ == "__main__":
    unittest.main()
