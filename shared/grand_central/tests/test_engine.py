"""The engine (migration 008, engine/): window settings, signals, episodes, rank, gaps, idempotence, daily.py wiring.
Temp DBs only, never the live rig.db. A small fake world is seeded straight into the tables."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import datetime as dt, json, os, sqlite3, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import step3_fixture  # noqa: E402
import daily, migrate, store, store_graph as sg, store_items  # noqa: E402
import run as er  # noqa: E402
import stitch as st  # noqa: E402
import common as C  # noqa: E402
from signals import first_seen_sender, long_quiet_returns, on_calendar_14d, sender_history, to_vs_cc  # noqa: E402

NOW = "2026-11-13T09:00:00+00:00"
ME = "owner@me.test"


def ms(iso):
    return int(dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.tmp.name, "rig.db")
        c = sqlite3.connect(self.p, isolation_level=None)
        for n, path in migrate.list_migrations():
            migrate.apply_file(c, path, n)
            # step 2.6: this fixture seeds old-table rows, which migration 020 freezes in a real database
            for (_t,) in c.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'frozen!_%' ESCAPE '!'").fetchall():
                c.execute("DROP TRIGGER " + _t)
        step3_fixture.seed_domain_vocab(c)
        c.close()
        store.set_path(self.p)
        self._old = {k: os.environ.get(k) for k in ("AGE_NOW", "AGE_NOTES_ROOT")}
        os.environ["AGE_NOW"] = NOW
        os.environ["AGE_NOTES_ROOT"] = self.tmp.name
        import clock as _clock  # 4P.0b: the feeds gate must see a connected feed in these CLI-read tests
        _st = _clock.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        for _src in ("gmail", "calendar", "tasks"):
            store.set_source_state(_src, _st, 0)
        self.n = 0
        self._old_st = st.STORE_GUESSES
        st.STORE_GUESSES = getattr(self, "STORE", True)   # these tests exercise the old storing path; TestNoGuessesStored turns it off

    def tearDown(self):
        st.STORE_GUESSES = self._old_st
        store.set_path(None)
        for k, v in self._old.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.tmp.cleanup()

    # ---- seeding ---------------------------------------------------------------------------------------
    def sql(self, q, a=()):
        c = sqlite3.connect(self.p)
        c.execute(q, a)
        c.commit()
        c.close()

    def msg(self, frm, subj, iso, thread=None, labels=("INBOX",), to=(ME,), cc=(), sent=0, name=""):
        self.n += 1
        mid = "m%d" % self.n
        self.sql("INSERT INTO messages(id,thread_id,internal_date,label_ids,from_addr,from_name,to_addrs,cc_addrs,subject,is_sent) "
                 "VALUES(?,?,?,?,?,?,?,?,?,?)", (mid, thread or "t" + mid, ms(iso), json.dumps(list(labels)), frm, name,
                                                 json.dumps(list(to)), json.dumps(list(cc)), subj, sent))
        return mid

    def label(self, lid, name):
        self.sql("INSERT INTO labels(id,name,type) VALUES(?,?,'user')", (lid, name))

    def event(self, eid, start, end, summary, attendees=(), status="confirmed"):
        self.sql("INSERT INTO calendar_events(id,start,end,all_day,status,organizer_email,attendee_emails,summary) VALUES(?,?,?,0,?,?,?,?)",
                 (eid, start, end, status, "", json.dumps(list(attendees)), summary))

    def task(self, tid, title, status="needsAction", due=None, completed=None):
        self.sql("INSERT INTO tasks(id,list_id,title,status,due,completed,updated) VALUES(?,?,?,?,?,?,?)",
                 (tid, "l", title, status, due, completed, "2026-11-10T00:00:00Z"))

    def world(self):
        """a small fake world; returns nothing, everything is found by subject"""
        self.label("Label_E", "Example-B"); self.label("Label_X", "Misc")
        self.msg(ME, "hi person_y", "2026-01-01T10:00:00Z", sent=1, labels=("SENT",), to=("person-y@agency-two.test",))
        # person_y: wrote 6 times, he replied twice; a thread with his last word (their move)
        for i in range(6):
            self.msg("person-y@agency-two.test", "Tryout sides %d" % i, "2026-11-%02dT10:00:00Z" % (3 + i), thread="tj%d" % (i % 2),
                     labels=("INBOX", "Label_E"), name="Person-Y Example")
        self.msg(ME, "Re: sides", "2026-11-12T09:00:00Z", thread="tj0", sent=1, labels=("SENT",), to=("person-y@agency-two.test",))
        self.msg(ME, "Re: sides", "2026-11-12T09:30:00Z", thread="tj1", sent=1, labels=("SENT",), to=("person-y@agency-two.test",))
        # a stranger, cc only, first message ever
        self.msg("new@stranger.test", "Hello there", "2026-11-12T12:00:00Z", to=("other@x.test",), cc=(ME,))
        # a list (neither To nor Cc)
        self.msg("news@list.test", "Weekly", "2026-11-12T13:00:00Z", to=("undisclosed@x.test",))
        # returns after a long quiet
        self.msg("old@friend.test", "long ago", "2026-03-01T10:00:00Z", labels=("INBOX",))
        self.msg("old@friend.test", "I am back", "2026-11-11T10:00:00Z")
        # an event in 5 days with person_y and an unknown attendee, and a mail from that attendee
        self.event("ev1", "2026-11-18T15:00:00Z", "2026-11-18T16:00:00Z", "Fitting", ["person-y@agency-two.test", "ghost@unknown.test", ME])
        self.msg("ghost@unknown.test", "Re: fitting", "2026-11-10T08:00:00Z", labels=("INBOX",))
        self.event("ev2", "2026-11-20T15:00:00Z", "2026-11-20T16:00:00Z", "Dentist", ["doc@clinic.test"])
        self.task("tk1", "Send headshots", due="2026-11-15"); self.task("tk2", "Old done", status="completed", completed="2026-11-01T00:00:00Z")
        store_items.backfill_items()

    def raw(self):
        return sqlite3.connect(self.p)

    def q(self, sql, a=()):
        c = self.raw()
        r = c.execute(sql, a).fetchall()
        c.close()
        return r

    def item(self, subject_like=None, source=None, source_id=None):
        if subject_like:
            return self.q("SELECT id FROM items WHERE title LIKE ? ORDER BY id LIMIT 1", (subject_like,))[0][0]
        return self.q("SELECT id FROM items WHERE source=? AND source_id=?", (source, source_id))[0][0]

    def score(self, iid, signal):
        r = self.q("SELECT value, reason FROM kg_scores WHERE subject_ref=? AND signal=?", ("item:%d" % iid, signal))
        return r[0] if r else None

    def picture(self):
        """the memory as the engine leaves it, ids and timestamps left out"""
        c = self.raw()
        out = {
            "things": c.execute("SELECT kind,key,name FROM kg_things ORDER BY key").fetchall(),
            "facts": c.execute("SELECT t.key,f.fact_key,f.value,f.who,f.certainty,f.source_kind,f.source_ref,f.replaced_by IS NULL "
                               "FROM kg_facts f JOIN kg_things t ON t.id=f.thing_id ORDER BY 1,2,3,4,7").fetchall(),
            "links": c.execute("SELECT a.key,l.kind,b.key,l.source_ref,l.replaced_by IS NULL FROM kg_links l JOIN kg_things a ON a.id=l.from_id "
                               "JOIN kg_things b ON b.id=l.to_id ORDER BY 1,2,3,4").fetchall(),
            "scores": c.execute("SELECT subject_ref,signal,signal_version,value,reason FROM kg_scores ORDER BY 1,2").fetchall(),
            "queue": c.execute("SELECT kind,subject_ref,question,proposed_answer,status FROM queue ORDER BY kind,subject_ref,question").fetchall(),
        }
        c.close()
        return out


class TestWindow(Base):
    def test_settings_seeded_once_and_read_from_facts(self):
        self.world()
        # plugin migration 029 wrote the six settings when the database was built: written once, the engine never reseeds
        before = {f["value"] for f in store.graph_read("current_facts", "topic:engine window", "setting")}
        self.assertEqual(len(before), 6)
        r1 = er.run()
        self.assertEqual(r1["gather"]["settings_seeded"], 0)
        self.assertEqual(er.run()["gather"]["settings_seeded"], 0)
        facts = {f["value"] for f in store.graph_read("current_facts", "topic:engine window", "setting")}
        self.assertEqual(facts, before)
        self.assertIn("calendar_ahead_days=62", facts)
        self.assertEqual(len(facts), 6)
        # a later answer from him changes the window
        store.record_answer("how far ahead", "only 3 days", "test", "2026-11-13", "topic", "engine window", "setting", "calendar_ahead_days=3")
        cfg = C.settings(self.raw())
        self.assertEqual(cfg["calendar_ahead_days"], 3)
        er.run()
        refs = [r[0] for r in self.q("SELECT subject_ref FROM kg_scores WHERE signal='window'")]
        self.assertNotIn("item:%d" % self.item(source="calendar", source_id="ev1"), refs)   # 5 days out, now outside the window

    def test_window_membership(self):
        self.world()
        er.run()
        w = {r[0]: r[1] for r in self.q("SELECT subject_ref, reason FROM kg_scores WHERE signal='window'")}
        self.assertEqual(w["item:%d" % self.item("Tryout sides 0")], "inbox")
        self.assertTrue(w["item:%d" % self.item(source="calendar", source_id="ev1")].startswith("calendar in 5"))
        self.assertEqual(w["item:%d" % self.item(source="tasks", source_id="tk1")], "open task")
        self.assertEqual(w["item:%d" % self.item(source="tasks", source_id="tk2")], "task done in the last 14 days")
        # sent mail is never in the window
        self.assertNotIn("item:%d" % self.item("Re: sides"), w)

    def test_label_that_matters_brings_in_recent_non_inbox_mail(self):
        self.world()
        self.msg("x@y.test", "Archived but Example-B", "2026-11-10T10:00:00Z", labels=("Label_E",))
        self.msg("x@y.test", "Archived and old", "2026-08-10T10:00:00Z", labels=("Label_E",))
        store_items.backfill_items()
        store.record_answer("is Example-B one that matters", "yes", "test", "2026-11-13", "label", "Example-B", "label_matters", "yes")
        er.run()
        w = {r[0]: r[1] for r in self.q("SELECT subject_ref, reason FROM kg_scores WHERE signal='window'")}
        self.assertEqual(w["item:%d" % self.item("Archived but Example-B")], "label Example-B (matters)")
        self.assertNotIn("item:%d" % self.item("Archived and old"), w)


class TestSignals(Base):
    def setUp(self):
        super().setUp()
        self.world()
        er.run()

    def test_sender_history(self):
        v, reason = self.score(self.item("Tryout sides 0"), "sender_history")
        self.assertEqual(reason, "wrote 6 times; you replied 3")
        self.assertAlmostEqual(v, round(0.5 * 6 / 20 + 0.5 * 3 / 5, 3))
        self.assertEqual(self.score(self.item("Hello there"), "sender_history")[1], "wrote 1 time; you replied 0")

    def test_on_calendar_14d(self):
        v, reason = self.score(self.item("Tryout sides 0"), "on_calendar_14d")
        self.assertEqual((v, reason), (1.0, "attends Fitting on 2026-11-18"))
        self.assertIsNone(self.score(self.item("Hello there"), "on_calendar_14d"))

    def test_first_seen_sender(self):
        self.assertEqual(self.score(self.item("Hello there"), "first_seen_sender")[0], 1.0)
        self.assertIsNone(self.score(self.item("Tryout sides 3"), "first_seen_sender"))
        self.assertEqual(self.score(self.item("Tryout sides 0"), "first_seen_sender")[0], 1.0)   # person_y's very first

    def test_long_quiet_returns(self):
        v, reason = self.score(self.item("I am back"), "long_quiet_returns")
        self.assertIn("back after 255 days", reason)
        self.assertIn("2026-03-01", reason)
        self.assertGreater(v, 0.6)
        self.assertIsNone(self.score(self.item("Tryout sides 3"), "long_quiet_returns"))

    def test_to_vs_cc(self):
        self.assertEqual(self.score(self.item("Tryout sides 0"), "to_vs_cc")[0], 1.0)
        self.assertEqual(self.score(self.item("Hello there"), "to_vs_cc"), (0.4, "you are only in Cc"))
        self.assertEqual(self.score(self.item("Weekly"), "to_vs_cc")[0], 0.0)

    def test_every_signal_module_is_discovered(self):
        import score
        self.assertEqual(sorted(m.NAME for m in score.discover()),
                         sorted(m.NAME for m in (first_seen_sender, long_quiet_returns, on_calendar_14d, sender_history, to_vs_cc)))


class TestEpisodes(Base):
    def test_calendar_episode_exact_addresses_only(self):
        self.world()
        er.run()
        key = "episode:desk-a:ev1"
        facts = {(f["fact_key"], f["value"]) for f in store.graph_read("current_facts", key)}
        self.assertIn(("trigger", "calendar event"), facts)
        self.assertIn(("date_window", "2026-11-18..2026-11-18"), facts)
        self.assertIn(("whose_move", "them"), facts)    # newest message in person_y's threads is his own reply
        members = {v for k, v in facts if k == "member_item"}
        self.assertIn("item:%d" % self.item(source="calendar", source_id="ev1"), members)
        self.assertIn("item:%d" % self.item("Tryout sides 0"), members)
        self.assertIn(("domain", "part-b"), facts)
        links = {l["to_key"] for l in store.graph_read("current_links", key) if l["from_key"] == key}
        self.assertEqual(links, {"address:person-y@agency-two.test", "address:ghost@unknown.test"})
        self.assertTrue(all(k.startswith("address:") and "@" in k for k in links))
        self.assertFalse([r for r in self.q("SELECT 1 FROM kg_links l JOIN kg_things t ON t.id=l.to_id WHERE t.kind='domain'")])

    def test_recurring_instances_collapse_into_one_series_episode(self):
        self.world()
        for d in ("20261116", "20261119", "20261123"):
            self.event("garb_%s" % d, "2026-11-%sT12:00:00Z" % d[6:], "2026-11-%sT12:30:00Z" % d[6:], "Garbage p/up", ["gc@town.test"])
        self.event("walk_20261117T140000Z", "2026-11-17T14:00:00Z", "2026-11-17T14:30:00Z", "Walk", ["w@x.test"])
        store_items.backfill_items()
        er.run()
        keys = [r[0] for r in self.q("SELECT key FROM kg_things WHERE key LIKE 'episode:desk-a:garb%'")]
        self.assertEqual(keys, ["episode:desk-a:garb"])
        facts = {(f["fact_key"], f["value"]) for f in store.graph_read("current_facts", "episode:desk-a:garb")}
        self.assertIn(("date_window", "2026-11-16..2026-11-23"), facts)
        self.assertEqual(len([1 for k, v in facts if k == "member_item"]), 3)
        self.assertEqual([r[0] for r in self.q("SELECT key FROM kg_things WHERE key LIKE 'episode:desk-a:walk%'")], ["episode:desk-a:walk"])

    def test_solo_event_in_near_view_is_an_episode_and_is_ranked(self):
        self.world()
        self.event("solo1", "2026-11-19T10:00:00Z", "2026-11-19T11:00:00Z", "Gym", [ME])
        self.event("far1", "2026-12-19T10:00:00Z", "2026-12-19T11:00:00Z", "Far away", [ME])
        self.event("past_ok", "2026-11-08T10:00:00Z", "2026-11-08T11:00:00Z", "Lunch", [ME])
        self.event("past_old", "2026-11-01T10:00:00Z", "2026-11-01T11:00:00Z", "Old thing", [ME])
        store_items.backfill_items()
        er.run()
        self.assertEqual(self.q("SELECT COUNT(*) FROM kg_things WHERE key='episode:desk-a:solo1'")[0][0], 1)
        facts = {(f["fact_key"], f["value"]) for f in store.graph_read("current_facts", "episode:desk-a:solo1")}
        self.assertIn(("trigger", "calendar solo: near view"), facts)
        for k, n in (("far1", 0), ("past_ok", 1), ("past_old", 0)):     # next 14 days and last 7 only
            self.assertEqual(self.q("SELECT COUNT(*) FROM kg_things t WHERE key=? AND EXISTS (SELECT 1 FROM kg_facts WHERE thing_id=t.id)",
                                    ("episode:desk-a:" + k,))[0][0], n, k)
        iid = self.item(source="calendar", source_id="solo1")
        self.assertIsNotNone(self.score(iid, "window"))
        self.assertIsNotNone(self.score(iid, "rank"))

    def test_important_person_episodes_over_one_thread_do_not_merge(self):
        self.world()
        self.msg("boss@agency-one.test", "Re: sides", "2026-11-12T11:00:00Z", thread="tj0", labels=("INBOX",), name="Boss Agency-One")
        store_items.backfill_items()
        store.record_answer("who matters", "agency-two", "test", "2026-11-13", "domain", "agency-two.test", "importance", "high")
        store.record_answer("who matters", "agency-one", "test", "2026-11-13", "domain", "agency-one.test", "importance", "high")
        er.run()
        keys = [r[0] for r in self.q("SELECT key FROM kg_things WHERE key LIKE 'episode:person:%' AND id IN "
                                     "(SELECT thing_id FROM kg_facts WHERE fact_key='member_item')")]
        self.assertEqual(sorted(keys), ["episode:person:boss@agency-one.test", "episode:person:person-y@agency-two.test"])
        self.assertEqual(self.q("SELECT name FROM kg_things WHERE key='episode:person:boss@agency-one.test'")[0][0], "Boss Agency-One")
        facts = {(f["fact_key"], f["value"]) for f in store.graph_read("current_facts", "episode:person:boss@agency-one.test")}
        self.assertIn(("trigger", "important person: boss@agency-one.test"), facts)
        a = self.picture(); er.run(); self.assertEqual(a, self.picture())

    def trip(self):
        """the January example trip as tasks (due dates spread over months), plus noise"""
        for tid, title, due, notes in (
                ("a1", "Pick Exampleair seats EXA \u2192 EXB", "2026-11-15", "exampleair.test"),
                ("a2", "Call Exampleton Airlines (ref EJSWTW)", "2026-11-15", "bags checked through to EXB?"),
                ("a3", "Call Samplejet: confirm booking, add miles number", "2026-10-28", "SJ738 EXC\u2192EXD"),
                ("a4", "Add Samplecard to Apple Wallet on both iPhones", "2026-12-05", ""),
                ("a5", "Re-check Jan 25 Sample Town \u2192 EXC train times", "2026-12-15", ""),
                ("a6", "Re-check entry rule for EXD transit (Jan 26)", "2026-12-15", ""),
                ("a7", "Set up eSIMs (Exampleland, Examplevale, Placeville)", "2026-12-15", ""),
                ("a8", "Buy travel insurance", "2026-11-08", "Cover Jan 10-26, both travelers"),
                ("a9", "Download offline maps (Example City, Placeville, Sample Town)", "2027-01-08", "")):
            self.task(tid, title, due=due + "T00:00:00.000Z", completed=None)
            self.sql("UPDATE tasks SET notes=? WHERE id=?", (notes, tid))
        self.task("n1", "Buy milk", due="2026-11-14T00:00:00.000Z")
        self.task("n2", "Life insurance?")

    def test_task_with_due_date_starts_an_episode(self):
        self.task("t1", "Renew library card", due="2026-11-20T00:00:00.000Z")
        self.task("t2", "Think about gifts")                      # no due date, no place: nothing starts
        store_items.backfill_items()
        er.run()
        k = "episode:task:%d" % self.item(source="tasks", source_id="t1")
        facts = {(f["fact_key"], f["value"]) for f in store.graph_read("current_facts", k)}
        self.assertIn(("trigger", "task: due date"), facts)
        self.assertIn(("member_item", "item:%d" % self.item(source="tasks", source_id="t1")), facts)
        self.assertEqual(self.q("SELECT COUNT(*) FROM kg_things WHERE key LIKE 'episode:task:%'")[0][0], 1)

    def test_example_trip_tasks_are_one_trip_episode(self):
        self.world()
        self.trip()
        self.msg("air@exampleair.test", "Your Exampleair booking EXA to EXB", "2026-11-05T10:00:00Z")     # inside the window, names Exampleair
        self.msg("shop@x.test", "Exampleair sale on shoes", "2026-04-01T10:00:00Z")                 # names Exampleair, months outside the window
        self.event("exc", "2026-12-20T10:00:00Z", "2026-12-20T11:00:00Z", "Sample Town EXC transfer", [ME])
        self.event("gym2", "2026-12-20T10:00:00Z", "2026-12-20T11:00:00Z", "Gym", [ME])
        store_items.backfill_items()
        er.run()
        trips = [r[0] for r in self.q("SELECT key FROM kg_things WHERE key LIKE 'episode:trip:%' AND EXISTS "
                                      "(SELECT 1 FROM kg_facts f WHERE f.thing_id=kg_things.id AND f.replaced_by IS NULL)")]
        self.assertEqual(len(trips), 1)
        facts = {(f["fact_key"], f["value"]) for f in store.graph_read("current_facts", trips[0])}
        members = {v for k, v in facts if k == "member_item"}
        for tid in ("a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9"):
            self.assertIn("item:%d" % self.item(source="tasks", source_id=tid), members, tid)
        for tid in ("n1", "n2"):
            self.assertNotIn("item:%d" % self.item(source="tasks", source_id=tid), members, tid)
        self.assertIn("item:%d" % self.item("Your Exampleair booking%"), members)
        self.assertNotIn("item:%d" % self.item("Exampleair sale%"), members)
        self.assertIn("item:%d" % self.item(source="calendar", source_id="exc"), members)
        self.assertNotIn("item:%d" % self.item(source="calendar", source_id="gym2"), members)
        self.assertTrue(any(k == "trigger" and v.startswith("trip:") for k, v in facts))
        a = self.picture(); er.run(); self.assertEqual(a, self.picture())

    def test_unrelated_dated_tasks_stay_apart(self):
        self.task("t1", "Renew library card", due="2026-11-20T00:00:00.000Z")
        self.task("t2", "Fix the gutter", due="2026-11-21T00:00:00.000Z")
        store_items.backfill_items()
        er.run()
        self.assertEqual(self.q("SELECT COUNT(*) FROM kg_things WHERE key LIKE 'episode:task:%'")[0][0], 2)

    def test_job_phrase_episode(self):
        self.world()
        wid = store.graph_write("thing", "world", "world")
        store.graph_write("assert_fact", wid, "keyword", "job_phrases=tryout", "code", "likely", "legacy", "keywords:1")
        er.run()
        eps = [r[0] for r in self.q("SELECT key FROM kg_things WHERE key LIKE 'episode:job:%'")]
        self.assertEqual(sorted(eps), ["episode:job:tj0", "episode:job:tj1"])
        facts = {(f["fact_key"], f["value"]) for f in store.graph_read("current_facts", "episode:job:tj0")}
        self.assertIn(("trigger", "job phrase: tryout"), facts)
        self.assertIn(("whose_move", "them"), facts)
        self.assertTrue(any(k == "date_window" for k, _ in facts))
        links = {l["to_key"] for l in store.graph_read("current_links", "episode:job:tj0") if l["from_key"] == "episode:job:tj0"}
        self.assertEqual(links, {"address:person-y@agency-two.test"})

    def test_important_person_episode_by_domain_fact(self):
        self.world()
        store.record_answer("who matters", "agency-two matters", "test", "2026-11-13", "domain", "agency-two.test", "importance", "high")
        er.run()
        facts = {(f["fact_key"], f["value"]) for f in store.graph_read("current_facts", "episode:person:person-y@agency-two.test")}
        self.assertIn(("trigger", "important person: person-y@agency-two.test"), facts)
        self.assertIn(("whose_move", "them"), facts)
        links = {l["to_key"] for l in store.graph_read("current_links", "episode:person:person-y@agency-two.test")}
        self.assertEqual(links, {"address:person-y@agency-two.test"})     # the exact address, not the domain
        self.assertEqual(self.q("SELECT COUNT(*) FROM kg_things WHERE kind='domain'")[0][0], 1)  # only his own answer's thing

    def test_his_move_when_newest_is_from_someone_else(self):
        self.world()
        self.msg("person-y@agency-two.test", "One more", "2026-11-13T07:00:00Z", thread="tj0", labels=("INBOX",))
        store_items.backfill_items()
        er.run()
        facts = {(f["fact_key"], f["value"]) for f in store.graph_read("current_facts", "episode:desk-a:ev1")}
        self.assertIn(("whose_move", "him"), facts)


class TestNoGuessesStored(Base):
    """Phase 2 step 2.5 planted case: with the shipped setting an engine run writes no stitch guesses (episodes) into the model."""
    STORE = False
    world = TestEpisodes.world

    def test_engine_run_stores_no_stitch_guesses(self):
        self.world()
        n0 = self.q("SELECT (SELECT count(*) FROM kg_things),(SELECT count(*) FROM kg_facts),(SELECT count(*) FROM kg_links)")[0]
        res = er.run()
        n1 = self.q("SELECT (SELECT count(*) FROM kg_things WHERE key LIKE 'episode:%'),(SELECT count(*) FROM kg_facts WHERE source_ref='engine:stitch'),"
                    "(SELECT count(*) FROM kg_links WHERE source_ref='engine:stitch')")[0]
        self.assertEqual(tuple(n1), (0, 0, 0))
        self.assertGreater(res["stitch"]["episodes"], 0)        # it still works the episodes out


class TestRank(Base):
    def rank(self, iid):
        return self.score(iid, "rank")

    def test_his_override_beats_signals(self):
        self.world()
        er.run()
        hello, person_y = self.item("Hello there"), self.item("Tryout sides 5")
        self.assertGreater(self.rank(person_y)[0], self.rank(hello)[0])           # signals alone: person_y first
        self.sql("INSERT INTO overrides(level,subject_id,type,reason,review_by,created_at) VALUES('item',?,'pin','he said so','2026-12-01','x')", (hello,))
        er.run()
        self.assertGreater(self.rank(hello)[0], self.rank(person_y)[0])
        self.assertIn("pinned (his override: he said so)", self.rank(hello)[1])

    def test_his_word_on_importance_beats_signals(self):
        self.world()
        store.record_answer("q", "she is nothing", "test", "2026-11-13", "address", "person-y@agency-two.test", "importance", "low")
        er.run()
        r = self.rank(self.item("Tryout sides 5"))
        self.assertIn("his word: person-y@agency-two.test importance low", r[1])
        stranger = self.rank(self.item("Hello there"))
        self.assertLess(r[0], stranger[0])

    def test_demote_never_hide(self):
        self.world()
        er.run()
        base = self.rank(self.item("Weekly"))[0]
        store.record_answer("q", "skip them", "test", "2026-11-13", "domain", "list.test", "inbox", "skip")
        iid = self.item("Hello there")
        self.sql("INSERT INTO overrides(level,subject_id,type,until_on,reason,review_by,created_at) VALUES('item',?,'quiet-until','2026-12-01','later','2026-12-01','x')", (iid,))
        er.run()
        weekly = self.rank(self.item("Weekly"))
        self.assertIsNotNone(weekly)                       # a demoted item still has a rank row
        self.assertIn("his word: list.test inbox skip", weekly[1])
        self.assertLessEqual(weekly[0], base)
        q = self.rank(iid)
        self.assertIsNotNone(q)                            # quiet-until: still ranked, at the bottom
        self.assertEqual(q[0], min(r[0] for r in self.q("SELECT value FROM kg_scores WHERE signal='rank'")))
        self.assertIn("quiet until 2026-12-01", q[1])
        window = {r[0] for r in self.q("SELECT subject_ref FROM kg_scores WHERE signal='window'")}
        ranked = {r[0] for r in self.q("SELECT subject_ref FROM kg_scores WHERE signal='rank'")}
        self.assertEqual(window, ranked)                   # nothing hidden

    def test_reason_parts_and_task_due(self):
        self.world()
        er.run()
        v, reason = self.rank(self.item(source="tasks", source_id="tk1"))
        self.assertIn("due in 2 days", reason)
        self.assertIn("your move", reason)

    def test_urgent_and_week_digest_do_not_carry_rank(self):
        """2.4 reader 5: rank and top_ranked are outside docs/planning-interface.md's contract and are gone from gc urgent / gc week."""
        self.world()
        er.run()
        us = store.urgent_items()
        self.assertTrue(us)
        self.assertTrue(all("rank" not in u and "rank_reason" not in u for u in us))
        d = store.week_digest(dt.date(2026, 11, 13), dt.date(2026, 11, 20))
        self.assertNotIn("top_ranked", d)
        self.assertTrue(all("rank" not in u for u in d["top_urgent"]))


class TestGaps(Base):
    def gaps(self, status="open"):
        return self.q("SELECT subject_ref, question, proposed_answer FROM queue WHERE kind='gap' AND status=? ORDER BY subject_ref, question", (status,))

    def test_gaps_found_and_stable(self):
        self.world()
        store.record_answer("matters", "yes", "test", "2026-11-13", "label", "Example-B", "label_matters", "yes")
        er.run()
        g = self.gaps()
        qs = {x[1] for x in g}
        self.assertIn("sender writes often and is linked to no person or company", qs)
        self.assertIn("episode has no domain", qs)         # the Dentist episode: one member, one address
        self.assertIn("calendar event in the next 2 weeks has attendees the memory doesn't know", qs)
        self.assertIn("label that matters has no fact saying what it is for", qs)
        sender = [x for x in g if x[0] == "address:person-y@agency-two.test"][0]
        self.assertIn("6 messages", sender[2])
        self.assertNotIn("6", sender[1])           # no counts in the question text
        self.assertNotIn("address:news@list.test", {x[0] for x in g})   # one message: below the bar
        er.run()
        self.assertEqual(self.gaps(), g)
        self.assertEqual(self.q("SELECT COUNT(*) FROM queue WHERE kind='gap'")[0][0], len(g))

    def test_fixed_gap_is_dismissed_on_rerun(self):
        self.world()
        er.run()
        self.assertIn("address:person-y@agency-two.test", {x[0] for x in self.gaps()})
        store.record_answer("who is person_y", "a talent agent", "test", "2026-11-13", "address", "person-y@agency-two.test", "domain", "part-b")
        er.run()
        self.assertNotIn("address:person-y@agency-two.test", {x[0] for x in self.gaps()})
        self.assertIn("address:person-y@agency-two.test", {x[0] for x in self.gaps("dismissed")})
        self.assertEqual(self.q("SELECT answer FROM queue WHERE kind='gap' AND status='dismissed' AND subject_ref='address:person-y@agency-two.test'")[0][0],
                         "engine: no longer found")

    def test_other_queue_kinds_untouched_and_his_dismissal_kept(self):
        self.world()
        qid, _ = store.queue_question("who-is-this", "address:z@z.test", "who is z?")
        er.run()
        gid = self.q("SELECT id FROM queue WHERE kind='gap' AND subject_ref='address:person-y@agency-two.test'")[0][0]
        import store_meaning
        with store._write() as c:
            store_meaning.queue_dismiss(c, gid)       # he dismisses it himself
        er.run()
        self.assertNotIn("address:person-y@agency-two.test", {x[0] for x in self.gaps()})   # not re-asked
        self.assertEqual(self.q("SELECT status FROM queue WHERE id=?", (qid,))[0][0], "open")

    def test_cap(self):
        self.world()
        for i in range(50):
            for k in range(5):
                self.msg("bulk%d@p.test" % i, "hi %d" % k, "2026-11-12T10:%02d:00Z" % k)
        store_items.backfill_items()
        r = er.run()
        self.assertEqual(r["gaps"]["gaps_kept"], 40)
        self.assertEqual(self.q("SELECT COUNT(*) FROM queue WHERE kind='gap' AND status='open'")[0][0], 40)


class TestWholeEngine(Base):
    def test_two_runs_identical_picture(self):
        self.world()
        store.record_answer("matters", "yes", "test", "2026-11-13", "label", "Example-B", "label_matters", "yes")
        store.record_answer("who matters", "agency-two", "test", "2026-11-13", "domain", "agency-two.test", "importance", "high")
        wid = store.graph_write("thing", "world", "world")
        store.graph_write("assert_fact", wid, "keyword", "job_phrases=tryout", "code", "likely", "legacy", "keywords:1")
        r1 = er.run()
        a = self.picture()
        r2 = er.run()
        b = self.picture()
        self.assertEqual(a, b)
        self.assertEqual({k: v for k, v in r1.items() if k != "gather"}, {k: v for k, v in r2.items() if k != "gather"})
        self.assertTrue(a["facts"] and a["scores"] and a["queue"])

    def test_empty_database_is_fine(self):
        r = er.run()
        self.assertEqual(r["gather"]["window_items"], 0)
        self.assertEqual(r["gaps"]["gaps_kept"], 0)

    def test_gc_engine_command(self):
        import contextlib, importlib.util, io
        spec = importlib.util.spec_from_file_location("rig_gc_engine", os.path.join(ROOT, "gc.py"))
        gc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gc)
        self.world()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = gc.main(["--db", self.p, "engine", "--json"])
        self.assertEqual(rc, 0)
        self.assertIn("window_items", json.loads(out.getvalue())["gather"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(gc.main(["--db", self.p, "engine"]), 0)
        self.assertTrue(out.getvalue().startswith("engine: "))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gc.main(["--db", self.p, "urgent"])
        self.assertNotIn("why:", out.getvalue())   # the engine's rank is no longer shown (2.4 reader 5)
        self.assertIn("urgent item(s)", out.getvalue())


class TestDailyWiring(Base):
    def run_daily(self):
        return daily.run(token_fn=lambda: {"status": "OK-FOR-NOW-IF-TESTING"}, backup_fn=lambda: None, pull_fn=lambda a, m: (0, ""))

    def test_daily_runs_the_engine(self):
        self.world()
        r = self.run_daily()
        self.assertIn(r["status"], ("OK", "WARN"))
        self.assertIsNotNone(r["engine"])
        self.assertGreater(r["engine"]["gather"]["window_items"], 0)
        self.assertEqual(self.q("SELECT COUNT(*) FROM kg_scores WHERE signal='rank'")[0][0], r["engine"]["rank"]["ranked"])

    def test_engine_failure_is_a_warn_not_an_error(self):
        self.world()
        orig = er.run_con
        er.run_con = lambda con: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            r = self.run_daily()
        finally:
            er.run_con = orig
        self.assertEqual(r["status"], "WARN")
        self.assertIsNone(r["error"])
        self.assertTrue(any("engine failed" in w and "boom" in w for w in r["warnings"]))
        self.assertIsNone(r["engine"])

    def test_engine_skipped_on_a_db_older_than_008(self):
        self.world()
        c = self.raw(); c.execute("PRAGMA user_version=7"); c.commit(); c.close()
        r = self.run_daily()
        self.assertIsNone(r["engine"])
        self.assertEqual(r["warnings"], [])

    def test_engine_failure_rolls_back_whole_run(self):
        self.world()
        import rank as rank
        orig = rank.run
        rank.run = lambda con: (_ for _ in ()).throw(RuntimeError("rank broke"))
        try:
            with self.assertRaises(RuntimeError):
                er.run()
        finally:
            rank.run = orig
        self.assertEqual(self.q("SELECT COUNT(*) FROM kg_scores")[0][0], 0)    # nothing half-written


class TestStatic(unittest.TestCase):
    def test_engine_never_opens_a_database_or_touches_google(self):
        import ast, glob
        for f in glob.glob(os.path.join(ROOT, "engine", "**", "*.py"), recursive=True):
            with open(f, encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            for n in ast.walk(tree):
                if isinstance(n, ast.Import):
                    mods = [a.name for a in n.names]
                elif isinstance(n, ast.ImportFrom):
                    mods = [n.module or ""]
                else:
                    continue
                for m in mods:
                    self.assertNotIn(m.split(".")[0], ("sqlite3", "db", "pull", "hands", "mover", "urllib", "requests", "googleapiclient"), f)


class TestLabelAliases(unittest.TestCase):
    def test_aliases(self):
        import common as C
        self.assertIn("example-b", C.label_aliases("Example-B-Inbox"))
        self.assertIn("sub", C.label_aliases("Example-B-Inbox/Sub"))
        self.assertIn("example-d", C.label_aliases("Example-D Inbox"))
        self.assertIn("receipts", C.label_aliases("Example-C-Inbox/Receipts"))
        self.assertNotIn("example-b", C.label_aliases("Example-B-Inbox/Example-B-Archive"))


if __name__ == "__main__":
    unittest.main()
