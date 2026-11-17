"""The flexible memory (migrations 005-006, store_graph.py): allowed words, the one door for answers, his word wins,
recency, rebuild-from-answers, the legacy copy reproduces today's people and rules exactly. Temp DBs only."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import contextlib, importlib.util, io, json, os, sqlite3, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import step3_fixture  # noqa: E402
import migrate, store, store_graph as sg  # noqa: E402

spec = importlib.util.spec_from_file_location("rig_gc_graph", os.path.join(ROOT, "gc.py"))
rig_gc = importlib.util.module_from_spec(spec); spec.loader.exec_module(rig_gc)


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
        self._old = os.environ.get("AGE_NOW")
        os.environ["AGE_NOW"] = "2026-11-13T09:00:00+00:00"

    def tearDown(self):
        store.set_path(None)
        if self._old is None:
            os.environ.pop("AGE_NOW", None)
        else:
            os.environ["AGE_NOW"] = self._old
        self.tmp.cleanup()

    def raw(self):
        return sqlite3.connect(self.p)

    def gc(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = rig_gc.main(["--db", self.p] + list(argv))
        return rc, out.getvalue()


class TestAllowedWords(Base):
    def test_refuses_unknown_value_key_kind_and_wrong_subject(self):
        R = sg.Refused
        with self.assertRaises(R):
            store.record_answer("q", "w", "t", "2026-11-13", "domain", "x.com", "inbox", "maybe")
        with self.assertRaises(R):
            store.record_answer("q", "w", "t", "2026-11-13", "domain", "x.com", "colour", "red")
        with self.assertRaises(R):
            store.record_answer("q", "w", "t", "2026-11-13", "planet", "mars", "inbox", "stay")
        with self.assertRaises(R):
            store.record_answer("q", "w", "t", "2026-11-13", "trip", "city-a", "label_matters", "yes")  # label-only fact
        with self.assertRaises(R):
            store.record_answer("q", "w", "t", "13/11/2026", "domain", "x.com", "inbox", "stay")
        with self.assertRaises(R):
            store.record_answer("q", "", "t", "2026-11-13", "domain", "x.com", "inbox", "stay")
        self.assertEqual(self.raw().execute("SELECT COUNT(*) FROM kg_answers").fetchone()[0], 0,
                         "a refused answer must write nothing")

    def test_every_value_list_has_undecided(self):
        c = self.raw()
        lists = [r[0] for r in c.execute("SELECT DISTINCT value_list FROM kg_fact_keys WHERE value_list IS NOT NULL")]
        for lst in lists:
            if lst in ("v:rule_status", "v:match_kind"):  # legacy bookkeeping, not decisions he is asked
                continue
            self.assertIsNotNone(c.execute("SELECT 1 FROM kg_vocab WHERE list=? AND value='undecided'", (lst,)).fetchone(), lst)

    def test_code_writes_are_checked_too(self):
        tid = store.graph_write("thing", "label", "Example-B")
        with self.assertRaises(sg.Refused):
            store.graph_write("assert_fact", tid, "label_matters", "kinda", "ai_guess", "guess", "code")
        with self.assertRaises(sg.Refused):
            store.graph_write("assert_fact", tid, "label_matters", "yes", "owner", "sure", "code")  # his word needs an answer
        with self.assertRaises(ValueError):
            store.graph_write("record_answer")  # not a code write


class TestOneDoor(Base):
    def test_one_answer_one_fact_with_provenance(self):
        r = store.record_answer("Where does Agency-One go?", "my main agent, high importance", "test-window", "2026-11-13",
                                "domain", "agency-one.example", "importance", "high")
        self.assertEqual(r["applied"], "fact")
        f = store.graph_read("current_facts", "domain:agency-one.example")
        self.assertEqual([(x["fact_key"], x["value"], x["who"], x["answer_id"], x["true_from"]) for x in f],
                         [("importance", "high", "owner", r["answer_id"], "2026-11-13")])
        a = store.graph_read("answers")[0]
        self.assertEqual((a["words"], a["asked_by"], a["fact_key"]), ("my main agent, high importance", "test-window", "importance"))

    def test_link_answer(self):
        r = store.record_answer("Who is Person-Y?", "Person-Y at Agency-Two", "t", "2026-11-13", "address", "person-y@agency-two.example",
                                "link:works_at", "company:Agency-Two")
        self.assertEqual(r["applied"], "link")
        links = store.graph_read("current_links", "address:person-y@agency-two.example")
        self.assertEqual([(l["kind"], l["to_key"], l["who"]) for l in links], [("works_at", "company:agency-two", "owner")])

    def test_one_current_link_per_pair_through_the_writer_and_the_database(self):
        # migration 019: the writer supersedes in an order the unique index allows; a raw second current row is refused
        import db
        con = db.connect(self.p); con.isolation_level = None
        a = sg.thing(con, "address", "a@x.test", created_by="code"); b = sg.thing(con, "domain", "x.test", created_by="code")
        l1 = sg.add_link(con, a, "address_of", b, "code", "sure", "code")
        l2 = sg.add_link(con, a, "address_of", b, "code", "sure", "code")          # same pair again: replaces l1
        cur = [r[0] for r in con.execute("SELECT id FROM kg_links WHERE from_id=? AND to_id=? AND replaced_by IS NULL", (a, b))]
        self.assertEqual(cur, [l2])
        self.assertEqual(con.execute("SELECT replaced_by FROM kg_links WHERE id=?", (l1,)).fetchone()[0], l2)
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("INSERT INTO kg_links(from_id,kind,to_id,who,certainty,source_kind,created_at) VALUES(?,?,?,?,?,?,?)",
                        (a, "address_of", b, "code", "sure", "code", "2026-11-16T00:00:00Z"))

    def test_answers_are_append_only(self):
        store.record_answer("q", "w", "t", "2026-11-13", "domain", "x.com", "inbox", "stay")
        c = self.raw()
        with self.assertRaises(sqlite3.DatabaseError):
            c.execute("UPDATE kg_answers SET words='changed'")
        with self.assertRaises(sqlite3.DatabaseError):
            c.execute("DELETE FROM kg_answers")

    def test_recency_later_word_wins(self):
        store.record_answer("Agency-Three?", "never filter them", "t", "2026-11-10", "domain", "agency-three.example", "inbox", "stay")
        store.record_answer("Agency-Three?", "out of the inbox", "t", "2026-11-13", "domain", "agency-three.example", "inbox", "skip")
        f = store.graph_read("current_facts", "domain:agency-three.example", "inbox")
        self.assertEqual([x["value"] for x in f], ["skip"])

    def test_his_word_beats_ai_and_code(self):
        store.record_answer("Agency-One?", "stay in the inbox", "t", "2026-11-13", "domain", "agency-one.example", "inbox", "stay")
        tid = store.graph_read("thing_by_key", "domain:agency-one.example")["id"]
        store.graph_write("assert_fact", tid, "inbox", "skip", "ai_guess", "guess", "code")
        f = store.graph_read("current_facts", "domain:agency-one.example", "inbox")
        self.assertEqual([(x["value"], x["who"]) for x in f], [("stay", "owner")])
        c = self.raw()
        self.assertEqual(c.execute("SELECT COUNT(*) FROM kg_facts WHERE who='ai_guess'").fetchone()[0], 1, "AI guess kept as history")

    def test_multi_valued_labels(self):
        store.record_answer("Site-One?", "Example-Top", "t", "2026-11-13", "domain", "castingsite.example", "label", "Example-Top")
        store.record_answer("Site-One?", "also Example-B", "t", "2026-11-13", "domain", "castingsite.example", "label", "Example-B")
        f = store.graph_read("current_facts", "domain:castingsite.example", "label")
        self.assertEqual(sorted(x["value"] for x in f), ["Example-B", "Example-Top"])

    def test_gc_answer_decision_and_who(self):
        rc, out = self.gc("answer", "--subject-kind", "domain", "--subject", "agency-one.example", "--fact", "inbox", "--value", "stay",
                          "--words", "stay in the inbox", "--question", "Agency-One?", "--said-on", "2026-11-13", "--json")
        self.assertEqual(rc, 0, out)
        self.assertEqual(json.loads(out)["applied"], "fact")
        rc, out = self.gc("answer", "--subject-kind", "domain", "--subject", "agency-one.example", "--fact", "inbox", "--value", "nope",
                          "--words", "w", "--question", "q", "--json")
        self.assertEqual(rc, 1)
        self.assertIn("not an allowed word", out)
        rc, out = self.gc("who", "person-x.asst@agency-one.example")
        self.assertEqual(rc, 0)
        self.assertIn("HIS WORD  domain:agency-one.example inbox = stay", out)

    def test_queue_answer_also_lands_in_one_door_log(self):
        c = self.raw()
        c.execute("INSERT INTO queue(kind,subject_ref,question,created_at) VALUES('apply-label','person:1','Label?','2026-11-13')")
        c.commit()
        store.answer_proposal(1, "yes")
        a = store.graph_read("answers")
        self.assertEqual((len(a), a[0]["queue_id"], a[0]["words"], a[0]["fact_key"]), (1, 1, "yes", None))


class TestRebuild(Base):
    def test_rebuild_from_answers_gives_the_same_picture(self):
        store.record_answer("a", "never filter", "t", "2026-11-10", "domain", "agency-three.example", "inbox", "stay")
        store.record_answer("b", "out", "t", "2026-11-13", "domain", "agency-three.example", "inbox", "skip")
        store.record_answer("c", "Example-Top", "t", "2026-11-13", "domain", "agency-three.example", "label", "Example-Top")
        store.record_answer("d", "Person-Y at Agency-Two", "t", "2026-11-13", "address", "person-y@agency-two.example", "link:works_at", "company:agency-two")
        tid = store.graph_read("thing_by_key", "domain:agency-three.example")["id"]
        store.graph_write("assert_fact", tid, "inbox", "stay", "ai_research", "likely", "file", "notes.md#x")
        before = store.graph_read("his_picture")
        r = store.graph_rebuild_from_answers()
        self.assertTrue(r["same"])
        self.assertEqual(store.graph_read("his_picture"), before)
        self.assertEqual([x["value"] for x in store.graph_read("current_facts", "domain:agency-three.example", "inbox")], ["skip"])


class TestLegacyCopy(Base):
    def seed_legacy(self):
        c = self.raw()
        c.executescript("""
          INSERT INTO people(id,label,tier_guess,tier_override) VALUES(1,'Person-Y',  'normal','high'),(2,'person-one','high',NULL),(3,NULL,'low',NULL);
          INSERT INTO people(id,label,tier_guess,status) VALUES(4,'Gone','low','retired');
          INSERT INTO addresses(id,address,person_id,person_id_override) VALUES(1,'person-y@agency-two.example',1,NULL),(2,'r@x.com',NULL,2),(3,'svc@y.example',NULL,NULL);
          INSERT INTO circles(id,name,kind_guess,domain_guess,domain_override) VALUES(1,'Reps','standing','part-b',NULL),(2,'Family','standing','part-a','part-d');
          INSERT INTO circle_members(id,circle_id,person_id,role,valid_from,valid_until,valid_until_override) VALUES(1,1,1,'agent','2026-01-01',NULL,'2026-12-31'),(2,2,2,NULL,NULL,NULL,NULL);
          INSERT INTO rules(id,match_kind,match_value,subject_glob,kind_label,need_guess,need_override,domain_guess,shelf_days_guess,shelf_anchor_guess,status,folder_guess)
            VALUES(1,'domain','agency-three.example','','agency','just-see','action-not-urgent','part-b',7,'arrival','approved','Example-Top'),
                  (2,'address','a@b.example','*receipt*',NULL,NULL,NULL,NULL,NULL,NULL,'proposed',NULL);
          INSERT INTO rule_exceptions(id,rule_id,word,need_guess) VALUES(1,1,'callback','action-urgent');
          INSERT INTO facts(id,subject_kind,subject_id,fact_key,value_guess,value_override) VALUES(1,'person',1,'role','agent',NULL),(2,'world',0,'receipts_label','Receipts','Receipts2');
          INSERT INTO keywords(id,list_name,phrase,active_guess,active_override) VALUES(1,'job_phrases','callback',1,NULL),(2,'job_phrases','off',1,0);
        """)
        c.commit()

    def test_copy_reproduces_today_exactly_and_is_idempotent(self):
        self.seed_legacy()
        n1 = store.graph_write("copy_legacy")
        self.assertEqual((n1["people"], n1["addresses"], n1["circles"], n1["members"], n1["rules"], n1["exceptions"], n1["keywords"]),
                         (3, 3, 2, 2, 2, 1, 1))
        eq = store.graph_read("legacy_equivalence")
        for table, (missing, extra) in eq.items():
            self.assertEqual((missing, extra), (set(), set()), table)
        c = self.raw()
        rows = c.execute("SELECT COUNT(*) FROM kg_facts").fetchone()[0], c.execute("SELECT COUNT(*) FROM kg_links").fetchone()[0]
        store.graph_write("copy_legacy")
        self.assertEqual((c.execute("SELECT COUNT(*) FROM kg_facts").fetchone()[0], c.execute("SELECT COUNT(*) FROM kg_links").fetchone()[0]), rows)

    def test_equivalence_catches_a_drift(self):
        self.seed_legacy()
        store.graph_write("copy_legacy")
        c = self.raw()
        c.execute("UPDATE rules SET need_override='nothing' WHERE id=1")
        c.commit()
        missing, extra = store.graph_read("legacy_equivalence")["rules"]
        self.assertEqual(len(missing), 1)
        self.assertEqual(len(extra), 1)


class TestReview1Shape(Base):
    def test_condition_keeps_two_values_on_one_subject(self):
        store.record_answer("Uber?", "ride receipts yes", "t", "2026-11-13", "domain", "uber.com", "label", "Receipts", condition="receipt")
        store.record_answer("Uber?", "vouchers no", "t", "2026-11-13", "domain", "uber.com", "destination", "trash", condition="voucher")
        store.record_answer("Uber?", "rest archive", "t", "2026-11-13", "domain", "uber.com", "destination", "archive")
        f = store.graph_read("current_facts", "domain:uber.com", "destination")
        self.assertEqual(sorted((x["condition"] or "", x["value"]) for x in f), [("", "archive"), ("voucher", "trash")])
        self.assertTrue(store.graph_rebuild_from_answers()["same"])

    def test_words_kind_is_checked_and_kept(self):
        r = store.record_answer("q", "summary of round 2", "t", "2026-11-11", "address", "a@b.example", "need", "just-see",
                                words_kind="summary")
        self.assertEqual(store.graph_read("answers")[0]["words_kind"], "summary")
        with self.assertRaises(sg.Refused):
            store.record_answer("q", "w", "t", "2026-11-11", "address", "a@b.example", "need", "just-see", words_kind="vibes")

    def test_topic_and_process_rule(self):
        r = store.record_answer("Trash?", "Gmail empties it", "t", "2026-11-12", "topic", "Trash", "process_rule",
                                "Don't empty Trash ourselves; moving to Trash is fine")
        self.assertEqual(r["applied"], "fact")


class TestRetireOneValue(Base):
    """On a multi-valued key, his "not:<v>" retires the current value <v> (labels stack; "folded into family")."""
    def vals(self, key="label"):
        return sorted(x["value"] for x in store.graph_read("current_facts", "domain:personone.example", key))

    def say(self, v, day="2026-11-13", **k):
        return store.record_answer("person-one label?", "w " + v, "t", day, "domain", "personone.example", "label", v, **k)

    def test_not_retires_one_value_and_is_never_current(self):
        self.say("person-one"); self.say("Family")
        self.assertEqual(self.vals(), ["Family", "person-one"])
        r = self.say("not:person-one")
        self.assertEqual(self.vals(), ["Family"])
        c = self.raw()
        row = c.execute("SELECT id, replaced_by FROM kg_facts WHERE value='not:person-one'").fetchone()
        self.assertEqual(row[0], row[1], "the not: fact is stored already superseded by itself")
        self.assertEqual(c.execute("SELECT replaced_by FROM kg_facts WHERE value='person-one'").fetchone()[0], r["row_id"])
        self.assertEqual(c.execute("SELECT COUNT(*) FROM kg_current_facts WHERE value LIKE 'not:%'").fetchone()[0], 0)

    def test_later_plain_value_makes_it_current_again(self):
        self.say("person-one"); self.say("Family"); self.say("not:person-one")
        self.say("person-one", day="2026-11-14")
        self.assertEqual(self.vals(), ["Family", "person-one"])

    def test_not_is_checked_like_the_value(self):
        with self.assertRaises(sg.Refused):
            self.say("not:")
        with self.assertRaises(sg.Refused):
            store.record_answer("q", "w", "t", "2026-11-13", "domain", "personone.example", "importance", "not:high")  # single-valued key: plain text
        with self.assertRaises(sg.Refused):
            store.record_answer("q", "w", "t", "2026-11-13", "domain", "personone.example", "note", "not:")

    def test_only_the_same_condition_is_retired(self):
        self.say("person-one", condition="receipt"); self.say("person-one")
        self.say("not:person-one", condition="receipt")
        f = store.graph_read("current_facts", "domain:personone.example", "label")
        self.assertEqual([(x["value"], x["condition"]) for x in f], [("person-one", None)])

    def test_rebuild_reproduces_it_exactly(self):
        tid = store.graph_write("thing", "domain", "personone.example")
        store.graph_write("assert_fact", tid, "label", "person-one", "code", "likely", "legacy", "x:1")
        self.say("Family"); self.say("not:person-one")
        self.assertEqual(self.vals(), ["Family"])
        before = store.graph_read("his_picture")
        self.assertTrue(store.graph_rebuild_from_answers()["same"])
        self.assertEqual(store.graph_read("his_picture"), before)
        self.assertEqual(self.vals(), ["Family"])
        self.say("person-one", day="2026-11-14")
        before = store.graph_read("his_picture")
        self.assertTrue(store.graph_rebuild_from_answers()["same"])
        self.assertEqual(store.graph_read("his_picture"), before)
        self.assertEqual(self.vals(), ["Family", "person-one"])

    def test_code_cannot_bring_back_a_value_he_retired(self):
        self.say("person-one"); self.say("not:person-one")
        tid = store.graph_read("thing_by_key", "domain:personone.example")["id"]
        store.graph_write("assert_fact", tid, "label", "person-one", "code", "likely", "legacy", "x:2")
        self.assertEqual(self.vals(), [])
        self.assertTrue(store.graph_rebuild_from_answers()["same"])
        self.assertEqual(self.vals(), [])


if __name__ == "__main__":
    unittest.main()
