"""Phase 3 tie-ups (a)-(e). Synthetic data, temp databases only. Every planted case runs a deliberately BROKEN version first and requires
the check to FAIL on it (the check raises AssertionError), then the real code and requires a pass:
(a) his level weights (owner fact) win over the PROPOSED ones in leans.json (plant: the owner value ignored);
(b) the live Path A job passes level= from levels_above_me (plant: level not passed);
(c) the onboarding sheet uses the live computed standing, not the frozen relationship_scores (plant: the old frozen read);
(d) the sheet's question marks are deduped against the people already on it, ranked and capped (plant: no dedupe);
(e) migration 027: keep_in_touch_days is an allowed word, his word only, whole days (plant: a database at 026, which refuses it)."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import contextlib, glob, io, json, os, sqlite3, sys, tempfile, unittest
from unittest import mock
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import migrate, onboarding as ob, store, store_graph as sg, store_pages as sp  # noqa: E402
import gcjobs, scorecard as sc, transcripts  # noqa: E402

ME = "me@example.test"


def planted(tc, check, plant_ctx):
    with plant_ctx:
        with tc.assertRaises(AssertionError):
            check()
    tc.tearDown(); tc.setUp()
    check()


class Base(unittest.TestCase):
    def setUp(self, upto=99):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.tmp.name, "rig.db")
        c = self.c = sqlite3.connect(self.p, isolation_level=None)
        for path in sorted(glob.glob(os.path.join(ROOT, "migrations", "*.sql"))):
            n = int(os.path.basename(path)[:3])
            if n <= upto:
                migrate.apply_file(c, path, n)
        store.set_path(self.p)
        sg.thing(c, "world", "world")
        self.me = sg.thing(c, "person", "me", key="person:me")
        self.n = 0

    def tearDown(self):
        store.set_path(None)
        self.c.close()
        self.tmp.cleanup()

    def say(self, question, subject_kind, subject_name, fact_key, value):
        return sg.record_answer(self.c, question, "his words", "test", "2026-11-16", subject_kind, subject_name, fact_key, value, words_kind="summary")

    def mail(self, thread, frm, to, sent):
        self.n += 1
        self.c.execute("INSERT INTO messages(id,thread_id,internal_date,label_ids,from_addr,to_addrs,cc_addrs,subject,is_sent,list_id,"
                       "list_unsubscribe_present,dmarc_pass) VALUES(?,?,?,?,?,?,?,?,?,NULL,0,1)",
                       ("m%d" % self.n, thread, 1763000000000 + self.n * 1000, "[]", frm, json.dumps(to), "[]", "s", 1 if sent else 0))
        return "m%d" % self.n

    def person(self, name, addr):
        pid = sg.thing(self.c, "person", name, key="person:" + name.lower())
        a = sg.thing(self.c, "address", addr)
        sg.add_link(self.c, a, "address_of", pid, "code", "sure", "code")
        return pid


class A_OwnerWeights(Base):
    def check(self):
        base = sc.Config.load()
        proposed = base.points["path_a"]["level_points"]
        r0 = sc.importance_urgency({"direct_ask": True}, base, 1.0, False, level=1)["importance_points"]
        self.say("W1: points per level above you", "topic", "level_points", "setting", "level_points=3,2,1")
        cfg = sc.Config.load()
        use = getattr(cfg, "use_owner_level_points", lambda con: cfg)
        use(self.c)
        r1 = sc.importance_urgency({"direct_ask": True}, cfg, 1.0, False, level=1)["importance_points"]
        r2 = sc.importance_urgency({"direct_ask": True}, cfg, 1.0, False, level=5)["importance_points"]
        assert abs((r1 - r0) - (3.0 - proposed["1"])) < 1e-9, "his value for level 1 did not win: %s vs %s" % (r1, r0)
        assert abs((r2 - r0) - (1.0 - proposed["1"])) < 1e-9, "his value for 3 or more did not win"
        assert cfg.points["attention"]["level_points"] == {"1": 3.0, "2": 2.0, "3_or_more": 1.0}
        assert base.points["path_a"]["level_points"] == proposed, "the file's proposal object was changed"

    def test_owner_value_wins(self):
        planted(self, self.check, mock.patch.object(sc.Config, "use_owner_level_points", lambda self_, con: self_))

    def test_no_owner_value_proposed_stands(self):
        cfg = sc.Config.load()
        before = json.dumps(cfg.points, sort_keys=True)
        cfg.use_owner_level_points(self.c)
        self.assertEqual(json.dumps(cfg.points, sort_keys=True), before)
        self.say("x", "topic", "level_points", "setting", "level_points=1,2")     # malformed (two numbers): ignored
        cfg.use_owner_level_points(self.c)
        self.assertEqual(json.dumps(cfg.points, sort_keys=True), before)


class B_LivePathA(Base):
    def run_job(self):
        seen = []
        real = sc.importance_urgency

        def spy(obs, cfg, standing_value=0.0, automated=False, level=None):
            seen.append((level, cfg.points["path_a"]["level_points"]["1"]))
            return real(obs, cfg, standing_value, automated, level=level)
        row = lambda mid: {"message_id": mid, "thread_id": "t", "ingested_at": "2099-01-01", "seen": "full", "verdict": "safe",
                           "triage": {"obs": {"direct_ask": "yes"}}}
        mids = {k: self.mail("t-" + k, k + "@example.test", [ME], False) for k in ("boss", "peer", "stranger")}
        boss = self.person("Boss", "boss@example.test")
        self.person("Peer", "peer@example.test")
        self.say("B1", "person", "boss", "levels_above_me", "1")
        self.say("B1", "person", "peer", "levels_above_me", "0")
        self.say("W1", "topic", "level_points", "setting", "level_points=2.5,0.5,0.25")
        self.c.commit()
        import datetime
        with mock.patch.object(transcripts, "catalogue_meta", lambda: [row(m) for m in mids.values()]), \
                mock.patch.object(sc, "importance_urgency", spy):
            gcjobs.alarm_candidates("2000-01-01", datetime.date(2026, 11, 16), out_path=os.path.join(self.tmp.name, "cand.jsonl"))
        return mids, seen

    def check(self):
        mids, seen = self.run_job()
        assert [s[0] for s in seen] == [1, None, None] or sorted([s[0] for s in seen], key=lambda x: -1 if x is None else x) == [None, None, 1], seen
        assert all(s[1] == 2.5 for s in seen), "his weights did not reach the job: %s" % seen

    def test_level_reaches_path_a(self):
        planted(self, self.check, mock.patch.object(gcjobs, "message_levels", lambda con: {}))

    def test_unknown_and_peer_count_zero(self):
        mids, seen = self.run_job()
        self.assertEqual(sorted(x for x, _ in seen if x is not None), [1])       # the peer (0) and the stranger pass nothing


class C_LiveStanding(Base):
    def setUp(self):
        super().setUp()
        self.c.execute("DROP TRIGGER frozen_relationship_scores_no_insert")
        self.pal = self.person("Pal", "pal@example.test")
        self.ghost = self.person("Ghost", "ghost@example.test")
        for i in range(4):                          # real two-way history with Pal; none with Ghost
            self.mail("t%d" % i, "pal@example.test", [ME], False)
            self.mail("t%d" % i, ME, ["pal@example.test"], True)
        self.c.execute("INSERT INTO relationship_scores(address,score_guess) VALUES('ghost@example.test', 9.0)")   # the frozen old score
        self.c.commit()

    def frozen_standing(con, tids):
        best = None
        for tid in tids:
            for (s,) in con.execute("SELECT s.score FROM v_thing_senders ts JOIN v_relationship_scores s ON s.address=ts.sender WHERE ts.thing_id=?", (tid,)).fetchall():
                if s is not None and (best is None or s > best):
                    best = s
        return best

    def check(self):
        ob._LIVE.clear()
        pal, ghost = ob._standing(self.c, [self.pal]), ob._standing(self.c, [self.ghost])
        assert pal and 0 < pal <= 4.0, "no live standing for a real correspondent: %r" % pal
        assert not ghost, "the frozen old score leaked into the standing: %r" % ghost
        want = sc.standing(sc.Mailbox.load(self.c), "pal@example.test", sc.Config.load(), ob._live(self.c)[3])["standing"]
        assert pal == want, "not the same figure gc who uses"

    def test_live_standing(self):
        planted(self, self.check, mock.patch.object(ob, "_standing", C_LiveStanding.frozen_standing))


class D_Questions(Base):
    def setUp(self):
        super().setUp()
        import senders
        self.senders = senders
        # question marks he wrote to: q0 .. q14, more messages = higher rank; q12 is already a person on the sheet
        for i in range(15):
            a = "q%d@example.test" % i
            for _ in range(i + 1):
                self.mail("q%d" % i, ME, [a], True)
        self.person("Dana Q", "q12@example.test")
        self.c.commit()
        with store._write() as c:
            senders.build_senders(c)

    def sheet_people(self):
        return [dict(name="Dana Q", key="person:dana q", also=[])]

    def check(self):
        with store._read() as c:
            raw = self.senders.onboarding_questions(c, limit=30)
            out = ob.sender_questions(c, self.sheet_people())
        assert "q12@example.test" in [q["address"] for q in raw], "fixture: q12 should be a question mark"
        assert "q12@example.test" not in [q["address"] for q in out], "someone already on the sheet was asked again"
        assert len(out) == ob.QUESTION_N, len(out)
        sc_ = [q["score"] for q in out]
        assert sc_ == sorted(sc_, reverse=True), "not ranked"

    def test_deduped_ranked_capped(self):
        real = ob.sender_questions
        def no_dedupe(con, people_rows, n=ob.QUESTION_N):
            return real(con, [], n)
        planted(self, self.check, mock.patch.object(ob, "sender_questions", lambda con, p, n=ob.QUESTION_N: no_dedupe(con, p, n)))

    def test_bare_domain_organizations_stay_off_the_sheet(self):
        every = ob.organizations(self.c)
        bare = [o for o in every if o["name"] == "example.test"]
        self.assertTrue(bare, "fixture: senders should have made a bare domain organization")
        s = ob.build(self.c)
        self.assertNotIn("example.test", [o["name"] for o in s["orgs"]])       # plant (no filter) would list every one of `every`
        self.assertLess(len(s["orgs"]), len(every))

    def test_on_the_sheet_and_recorded(self):
        s = ob.build(self.c)
        text, ids = ob.render(s, self.c)
        self.assertIn("## 7. Who is this?", text)
        qid = [k for k, v in ids.items() if v["kind"] == "sender"][0]
        self.c.execute("BEGIN")
        ob.record(self.c, ids, [{"id": qid, "answer": "bot"}], "2026-11-17")
        self.c.execute("COMMIT")
        r = self.c.execute("SELECT f.value, f.who, f.answer_id FROM kg_current_facts f JOIN kg_things t ON t.id=f.thing_id WHERE t.key=? AND f.fact_key='sender_kind'", (ids[qid]["key"],)).fetchall()
        self.assertEqual([(x[0], x[1]) for x in r], [("bot", "owner")])
        self.assertIsNotNone(r[0][2])
        with self.assertRaises(ob.AnswerError):
            ob.record(self.c, ids, [{"id": qid, "answer": "maybe"}], "2026-11-17")


class E_KeepInTouch(Base):
    def setUp(self, upto=99):
        super().setUp(upto)
        self.pal = self.person("Pal", "pal@example.test")

    def check(self):
        r = self.say("keep in touch", "person", "pal", "keep_in_touch_days", "30")
        assert r["applied"] == "fact"
        with self.assertRaises(sg.Refused):
            self.say("keep in touch", "person", "pal", "keep_in_touch_days", "weekly")
        with self.assertRaises(sg.Refused):
            self.say("keep in touch", "person", "pal", "keep_in_touch_days", "0")
        for who in ("code", "ai"):          # code and AI guesses never write it (the trigger, below the front door)
            with self.assertRaises((sg.Refused, sqlite3.IntegrityError)):
                sg.assert_fact(self.c, self.pal, "keep_in_touch_days", "7", who, "likely", "code")

    def test_the_word_is_allowed(self):
        self.tearDown(); self.setUp(upto=26)
        planted_ok = False
        try:
            self.check()                    # plant: a database still at 026 has no such word
        except (AssertionError, sg.Refused, sqlite3.Error):
            planted_ok = True
        self.assertTrue(planted_ok, "the 026 database accepted the word: the plant was not caught")
        self.tearDown(); self.setUp()
        self.check()

    def test_gc_due_works_with_his_word(self):
        self.say("keep in touch", "person", "pal", "keep_in_touch_days", "30")
        self.mail("t1", "pal@example.test", [ME], False)
        self.mail("t1", ME, ["pal@example.test"], True)
        self.c.commit()
        self.c.row_factory = sqlite3.Row
        d = sp.due(self.c, "2026-12-30")["due"]
        self.assertEqual([x["key"] for x in d], ["person:pal"])

    def test_sheet_asks_it_for_the_top_people_only(self):
        sg.assert_fact(self.c, self.pal, "importance", "high", "owner", "sure", "answer",
                       answer_id=self.say("x", "person", "pal", "note", "n")["answer_id"])
        s = ob.build(self.c)
        text, ids = ob.render(s, self.c)
        self.assertEqual(text.count("keep in touch: how many days"), min(len(s["people"]), ob.KEEP_N))


if __name__ == "__main__":
    unittest.main()
