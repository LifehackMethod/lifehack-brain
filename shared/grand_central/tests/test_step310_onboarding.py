"""Phase 3 step 3.10: the onboarding sitting. Synthetic data on a temp database; never the live rig.db.
Planted cases, each run first with a deliberately BROKEN version that the check must catch, then the real one:
(1) a pre-filled guess is not stored by making the sheet (plant: a sheet maker that stores its guesses);
(2) his "ok" becomes his own fact with its answer (plant: a confirmation written as code);
(3) his correction replaces the guess and the guess is nowhere in the database (plant: a recorder that also keeps the guess);
(4) a person who does not matter (a bot, a stranger) is left out (plant: no threshold);
plus: levels and weights land as his word and the settings read them back; held and mapping questions close with his answer."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import glob, json, os, sqlite3, sys, tempfile, unittest
from unittest import mock
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import migrate, org_moves, store_graph as sg, onboarding as ob  # noqa: E402


def snap(c):
    return [c.execute("SELECT * FROM %s ORDER BY 1" % t).fetchall() for t in ("kg_things", "kg_facts", "kg_links", "kg_answers", "queue")]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # standing is now the live computed figure (tie-up c, tested in test_step3_tieups). These tests plant standing through the
        # frozen table on a database with no mail, so they read it by the old route on the old 0 to 10 scale.
        def frozen(con, tids):
            best = None
            for tid in tids:
                for (sc_,) in con.execute("SELECT s.score FROM v_thing_senders ts JOIN v_relationship_scores s ON s.address=ts.sender WHERE ts.thing_id=?", (tid,)):
                    if sc_ is not None and (best is None or sc_ > best):
                        best = sc_
            return best
        self._mocks = [mock.patch.object(ob, "_standing", frozen), mock.patch.object(ob, "_live", lambda con: None)]
        for m in self._mocks:
            m.start()
        c = self.c = sqlite3.connect(os.path.join(self.tmp.name, "rig.db"), isolation_level=None)
        for path in sorted(glob.glob(os.path.join(ROOT, "migrations", "*.sql"))):
            migrate.apply_file(c, path, int(os.path.basename(path)[:3]))
        c.execute("DROP TRIGGER frozen_relationship_scores_no_insert")      # temp database only: lets the test plant standing
        sg.thing(c, "world", "world")
        sg.thing(c, "person", "me", key="person:me")
        self.org = sg.thing(c, "organization", "Agency-One", key="organization:agency-one")
        sg.assert_fact(c, self.org, "org_type", "company", "code", "sure", "code")
        self.grp = sg.thing(c, "organization", "family", key="organization:family")
        sg.assert_fact(c, self.grp, "org_type", "group", "code", "sure", "code")
        self.p = {}
        for nm, addr, score in (("Pat Agent", "pat@agency-one.example", 9.0), ("Sam Pal", "sam@freemail.example", 5.0), ("No Body", "nobody@xorg.example", 0.0),
                                ("Alert Bot", "noreply@bank.example", 10.0)):
            self.p[nm] = pid = sg.thing(c, "person", nm, key="person:" + nm.lower().replace(" ", ""))
            a = sg.thing(c, "address", addr)
            sg.add_link(c, a, "address_of", pid, "code", "sure", "code")
            c.execute("INSERT INTO relationship_scores(address,score_guess) VALUES(?,?)", (addr, score))
        self.hq = c.execute("INSERT INTO queue(kind,subject_ref,question,proposed_answer,status,created_at,answer) VALUES('onboarding-org-type','organization:family',"
                            "'What kind of thing is family?','group','dismissed','2026-11-01',?)", (org_moves.HELD,)).lastrowid
        self.mq = c.execute("INSERT INTO queue(kind,subject_ref,question,proposed_answer,status,created_at) VALUES('confirm-guess','address:sam@freemail.example',"
                            "'I had guessed that sam@freemail.example is an address of sam. Is that right?','yes','open','2026-11-01')").lastrowid
        sg.thing(c, "person", "sam", key="person:sam")
        self.mq2 = c.execute("INSERT INTO queue(kind,subject_ref,question,proposed_answer,status,created_at) VALUES('confirm-guess','address:kay@xorg.example',"
                             "'I had guessed that kay@xorg.example is an address of kay. Is that right?','yes','open','2026-11-01')").lastrowid
        sg.thing(c, "address", "kay@xorg.example"); sg.thing(c, "person", "kay", key="person:kay")

    def tearDown(self):
        for m in self._mocks:
            m.stop()
        self.c.close()
        self.tmp.cleanup()

    def sheet(self):
        s = ob.build(self.c)
        return s, ob._ids(s)

    def pid(self, ids, name):
        return [k for k, v in ids.items() if v["kind"] == "person" and v["name"] == name][0]

    def facts(self, key, fact):
        return [r[0] for r in self.c.execute("SELECT value FROM kg_facts f JOIN kg_things t ON t.id=f.thing_id WHERE t.key=? AND fact_key=?", (key, fact))]


class Planted(Base):
    def test_1_guess_not_stored_by_making_the_sheet(self):
        def unchanged(maker):
            before = snap(self.c)
            maker()
            return snap(self.c) == before

        def bad():
            s, ids = self.sheet()
            for v in ids.values():
                if v["kind"] == "person" and v["guess"].get("relationship"):
                    sg.assert_fact(self.c, sg.thing_by_key(self.c, v["key"])["id"], "relationship", v["guess"]["relationship"], "code", "likely", "code")
        self.assertFalse(unchanged(bad), "the planted sheet maker that stores guesses was not caught")
        self.tearDown(); self.setUp()
        out = os.path.join(self.tmp.name, "sheet.md")
        self.assertTrue(unchanged(lambda: ob.write_sheet(self.c, out)))
        with open(out, encoding="utf-8") as f:
            self.assertIn("*guess*", f.read())

    def test_2_confirmation_is_his_fact(self):
        s, ids = self.sheet()
        pid = self.pid(ids, "Pat Agent")
        g = ids[pid]["guess"]
        self.assertEqual(g["organization"], "organization:agency-one")      # shown as a guess from the address
        self.assertEqual(self.facts("person:pataagent", "importance"), [])

        def ok(c):
            return [r for r in c.execute("SELECT f.who, f.answer_id, f.value FROM kg_facts f JOIN kg_things t ON t.id=f.thing_id WHERE t.key=? AND fact_key='importance'", (ids[pid]["key"],))]
        # plant: a confirmation written as code is not an owner fact with an answer
        sg.assert_fact(self.c, self.p["Pat Agent"], "importance", "high", "code", "likely", "code")
        self.assertNotEqual([r[:2] for r in ok(self.c)], [("owner", r[1]) for r in ok(self.c)])
        self.tearDown(); self.setUp()
        s, ids = self.sheet(); pid = self.pid(ids, "Pat Agent")
        self.c.execute("BEGIN")
        rec = ob.record(self.c, ids, [{"id": pid, "importance": "ok", "organization": "ok", "relationship": "ok"}], "2026-11-17")
        self.c.execute("COMMIT")
        rows = ok(self.c)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "owner"); self.assertIsNotNone(rows[0][1]); self.assertEqual(rows[0][2], g["importance"])
        link = self.c.execute("SELECT who, answer_id FROM kg_current_links l JOIN kg_things t ON t.id=l.from_id WHERE t.key=? AND l.kind='member_of'", (ids[pid]["key"],)).fetchone()
        self.assertEqual(link[0], "owner"); self.assertIsNotNone(link[1])
        self.assertEqual(len(rec), 3)

    def test_3_correction_replaces_the_guess(self):
        s, ids = self.sheet(); pid = self.pid(ids, "Pat Agent")
        guess = ids[pid]["guess"]["importance"]
        self.c.execute("BEGIN")
        ob.record(self.c, ids, [{"id": pid, "importance": "low", "organization": "family"}], "2026-11-17")
        self.c.execute("COMMIT")
        self.assertEqual(self.facts(ids[pid]["key"], "importance"), ["low"])
        self.assertNotIn(guess, self.facts(ids[pid]["key"], "importance"))
        tgt = self.c.execute("SELECT t2.key FROM kg_current_links l JOIN kg_things t ON t.id=l.from_id JOIN kg_things t2 ON t2.id=l.to_id WHERE t.key=? AND l.kind='member_of'", (ids[pid]["key"],)).fetchall()
        self.assertEqual(tgt, [("organization:family",)])           # his organization, not the guessed Agency-One
        # plant: a recorder that keeps the guess too would leave it in the database
        sg.assert_fact(self.c, self.p["Pat Agent"], "importance", guess, "owner", "sure", "answer", answer_id=self.c.execute("SELECT max(id) FROM kg_answers").fetchone()[0])
        self.assertEqual(self.facts(ids[pid]["key"], "importance")[-1], guess)    # the plant is visible to the check above

    def test_4_someone_who_does_not_matter_is_left_out(self):
        s, ids = self.sheet()
        names = [v["name"] for v in ids.values() if v["kind"] == "person"]
        self.assertIn("Pat Agent", names); self.assertIn("Sam Pal", names)
        self.assertNotIn("Alert Bot", names)
        self.assertNotIn("No Body", names)
        old = ob.MIN_STANDING_FRAC
        ob.MIN_STANDING_FRAC = -1.0           # plant: no threshold lets the stranger in
        try:
            ids2 = ob._ids(ob.build(self.c))
            self.assertIn("No Body", [v["name"] for v in ids2.values() if v["kind"] == "person"])
        finally:
            ob.MIN_STANDING_FRAC = old

    def test_levels_weights_held_mapping(self):
        s, ids = self.sheet(); pid = self.pid(ids, "Pat Agent")
        self.assertIsNone(self.c.execute("SELECT level FROM v_levels_above_me WHERE person_key=?", (ids[pid]["key"],)).fetchone()[0])   # blank on purpose
        self.assertIsNone(ob.level_points(self.c))
        self.assertIn("1.0", ob.render(s)[0])
        h = [k for k, v in ids.items() if v["kind"] == "held"][0]
        m = [k for k, v in ids.items() if v["kind"] == "mapping" and v["ref"] == "address:kay@xorg.example"]
        self.assertEqual(len(m), 1)
        self.c.execute("BEGIN")
        ob.record(self.c, ids, [{"id": "B1", "reports_to": pid, "levels": {pid: 1}}, {"id": "W1", "value": "1,0.5,0.1"},
                                {"id": h, "type": "team"}, {"id": m[0], "answer": "yes"}], "2026-11-17")
        self.c.execute("COMMIT")
        self.assertEqual(self.c.execute("SELECT level, source FROM v_levels_above_me WHERE person_key=?", (ids[pid]["key"],)).fetchone(), (1, "owner"))
        self.assertEqual(ob.level_points(self.c), {"1": 1.0, "2": 0.5, "3_or_more": 0.1})
        self.assertEqual(self.facts("organization:family", "org_type")[-1], "team")
        self.assertEqual(self.c.execute("SELECT status FROM queue WHERE id=?", (self.hq,)).fetchone()[0], "answered")
        self.assertEqual(self.c.execute("SELECT l.who FROM kg_current_links l JOIN kg_things t ON t.id=l.from_id JOIN kg_things t2 ON t2.id=l.to_id WHERE t.key='address:kay@xorg.example' AND l.kind='address_of' AND t2.key='person:kay'").fetchone()[0], "owner")
        self.assertEqual([q['ref'] for q in ob.mapping_questions(self.c)], ['address:sam@freemail.example'])

    def test_mapping_yes_never_makes_one_address_two_people(self):
        s, ids = self.sheet()
        m = [k for k, v in ids.items() if v["kind"] == "mapping"][0]
        self.assertEqual(ids[m]["clash"], "Sam Pal")       # the address already belongs to Sam Pal; the question says "sam"
        self.c.execute("BEGIN"); rec = ob.record(self.c, ids, [{"id": m, "answer": "yes"}], "2026-11-17"); self.c.execute("COMMIT")
        self.assertIn("merge_needed", rec[0])
        n = self.c.execute("SELECT count(*) FROM kg_current_links l JOIN kg_things a ON a.id=l.from_id WHERE a.key='address:sam@freemail.example' AND l.kind='address_of'").fetchone()[0]
        self.assertEqual(n, 1)

    def test_duplicates_only_proposed_merge_only_on_yes(self):
        c = self.c
        leg = sg.thing(c, "person", "Pat Agent", key="person:legacy-1")          # the same name on file twice
        sg.assert_fact(c, leg, "role", "agent", "code", "sure", "legacy")
        s, ids = self.sheet()
        d = [k for k, v in ids.items() if v["kind"] == "dup" and "Pat Agent" in (v["keep_name"], v["fold_name"])]
        self.assertEqual(len(d), 1)
        self.assertEqual(ids[d[0]]["fold_key"], "person:legacy-1")
        live = c.execute("SELECT count(*) FROM kg_things WHERE kind='person' AND merged_into IS NULL").fetchone()[0]
        ob.write_sheet(c, os.path.join(self.tmp.name, "s.md"))                   # making the sheet merges nothing
        self.assertEqual(c.execute("SELECT count(*) FROM kg_things WHERE kind='person' AND merged_into IS NULL").fetchone()[0], live)
        c.execute("BEGIN"); ob.record(c, ids, [{"id": d[0], "answer": "no"}], "2026-11-17"); c.execute("COMMIT")
        self.assertEqual(c.execute("SELECT count(*) FROM kg_things WHERE kind='person' AND merged_into IS NULL").fetchone()[0], live)   # a no merges nothing
        c.execute("BEGIN"); ob.record(c, ids, [{"id": d[0], "answer": "yes"}], "2026-11-17"); c.execute("COMMIT")
        self.assertEqual(c.execute("SELECT count(*) FROM kg_things WHERE kind='person' AND merged_into IS NULL").fetchone()[0], live - 1)
        self.assertIsNotNone(c.execute("SELECT merged_into FROM kg_things WHERE key='person:legacy-1'").fetchone()[0])
        self.assertEqual(c.execute("SELECT count(*) FROM kg_answers WHERE fact_key='merge_into'").fetchone()[0], 1)  # his word is on record

    def test_no_answer_stores_nothing_and_bad_ok_refused(self):
        s, ids = self.sheet(); pid = self.pid(ids, "Sam Pal")
        before = snap(self.c)
        self.c.execute("BEGIN"); rec = ob.record(self.c, ids, [{"id": pid}, {"id": "W1"}], "2026-11-17"); self.c.execute("COMMIT")
        self.assertEqual(rec, []); self.assertEqual(snap(self.c), before)
        with self.assertRaises(ob.AnswerError):
            self.c.execute("BEGIN")
            try:
                ob.record(self.c, ids, [{"id": pid, "role": "ok"}], "2026-11-17")      # no role guess existed
            finally:
                self.c.execute("ROLLBACK")


if __name__ == "__main__":
    unittest.main()
