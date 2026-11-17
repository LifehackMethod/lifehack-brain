"""Phase 2 step 2.4: readers moved to the one model (kg_things, kg_links, kg_facts). Temp DBs only; never the live rig.db.
Each class is one reader; each has a planted case that fails on the pre-switch code."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import os, sqlite3, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import migrate, store, store_items, store_meaning as sm  # noqa: E402


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
        c.close()
        store.set_path(self.p)

    def tearDown(self):
        store.set_path(None)
        self.tmp.cleanup()

    def x(self, sql, args=()):
        c = sqlite3.connect(self.p, isolation_level=None)
        try:
            return c.execute(sql, args).fetchall()
        finally:
            c.close()


class AnswerWritesNoOldTable(Base):
    """Reader 1 (gc answer). PLANTED: a write to the old answer_log after the switch must be caught."""
    def test_answer_does_not_write_answer_log(self):
        q = self.x("INSERT INTO queue(kind,subject_ref,question,proposed_answer,created_at) VALUES('who-is-this','address:t@example.test','Who?','yes','x') RETURNING id")[0][0]
        n = self.x("SELECT count(*) FROM answer_log")[0][0]
        r = store.answer_proposal(q, "yes")
        self.assertEqual(self.x("SELECT count(*) FROM answer_log")[0][0], n, "answer_log was written: the old table is frozen at 2.6")
        self.assertEqual(self.x("SELECT words FROM kg_answers WHERE id=?", (r["answer_id"],))[0][0], "yes")
        self.assertIsNone(self.x("SELECT legacy_answer_log_id FROM kg_answers WHERE id=?", (r["answer_id"],))[0][0])


class WhoReadsTheModel(Base):
    """Reader 2 (gc who). PLANTED: a person that exists only in the old tables must NOT be known; one only in the model must be."""
    def test_old_table_only_person_is_unknown_model_only_person_is_known(self):
        self.x("INSERT INTO people(id,label,tier_guess) VALUES(1,'Old Only','normal')")
        self.x("INSERT INTO addresses(address,person_id) VALUES('old@example.test',1)")
        self.assertFalse(store.sender_context("old@example.test")["known"], "gc who read the old people/addresses tables")
        store.graph_write("copy_legacy")                     # now both old and new know it
        self.assertTrue(store.sender_context("old@example.test")["known"])
        self.x("DELETE FROM kg_links")                       # break the model's link only: the old tables still say known
        self.assertFalse(store.sender_context("old@example.test")["known"], "gc who read the old tables, not the links")


class KnownHomesReadTheModel(Base):
    """Reader 3 (delta._known_homes, feeds the morning read). PLANTED: an address in the old table only is not a home."""
    def test_homes_follow_address_of_links(self):
        import delta
        con = sqlite3.connect(self.p)
        cfg = type("C", (), {"leans": {}})()
        self.x("INSERT INTO people(id,label,tier_guess) VALUES(1,'Old Only','normal')")
        self.x("INSERT INTO addresses(address,person_id) VALUES('old@example.test',1)")
        self.assertEqual(delta._known_homes(con, cfg), set(), "the morning read still reads the old addresses table")
        store.graph_write("copy_legacy")
        self.assertEqual(delta._known_homes(con, cfg), {"old@example.test"})
        self.assertEqual(delta._known_homes(con, type("C", (), {"leans": {"starter_people": ["S@example.test"]}})()),
                         {"old@example.test", "s@example.test"})


class UrgentReadsTheModel(Base):
    """Reader 4 (pins, quiet-until, projects behind gc urgent). PLANTED: pins / quiet-until / project links written only to the
    old tables after the switch must change nothing; the same words in the model must."""
    def setUp(self):
        super().setUp()
        os.environ["AGE_NOW"] = "2026-11-12T09:00:00+00:00"
        self.top = store_items.upsert_item("t", "top", "task", title="top", occurred_at="2026-11-10T10:00:00Z", due_at="2026-11-13", status="open")[0]
        self.nodate = store_items.upsert_item("t", "nodate", "task", title="nodate", occurred_at="2026-11-10T10:00:00Z", due_at=None, status="open")[0]

    def tearDown(self):
        os.environ.pop("AGE_NOW", None)
        super().tearDown()

    def model(self, fn, *a, **k):
        c = sqlite3.connect(self.p, isolation_level=None)
        try:
            c.execute("BEGIN"); r = fn(c, *a, **k); c.execute("COMMIT"); return r
        finally:
            c.close()

    def ids(self):
        return [u["item_id"] for u in store.urgent_items()]

    def test_old_overrides_table_is_not_read(self):
        before = store.urgent_items()
        self.x("INSERT INTO overrides(level,subject_id,type,reason,review_by,created_at) VALUES('item',?,'pin','old','2026-12-01','x')", (self.nodate,))
        self.x("INSERT INTO overrides(level,subject_id,type,until_on,reason,review_by,created_at) VALUES('item',?,'quiet-until','2027-01-01','old','2026-12-01','x')", (self.top,))
        self.assertEqual(store.urgent_items(), before, "gc urgent read the old overrides table")
        self.assertEqual(store.expiry_questions(), [])
        self.assertEqual(store.week_digest("2026-11-09", "2026-11-16")["overdue_reviews"], [])

    def test_old_project_links_are_not_read(self):
        self.x("INSERT INTO projects(id,name,due_on,created_at) VALUES(1,'Old','2026-11-13','x')")
        self.x("INSERT INTO item_projects(item_id,project_id,created_at) VALUES(?,1,'x')", (self.nodate,))
        self.assertNotIn(self.nodate, self.ids(), "gc urgent read the old item_projects / projects tables")

    def test_model_pin_quiet_project_and_end(self):
        self.model(sm.set_override, "item", self.nodate, "pin", "he said so", "2026-11-01")
        u = {x["item_id"]: x for x in store.urgent_items()}
        self.assertTrue(u[self.nodate]["pinned"]); self.assertEqual(u[self.nodate]["urgency"], 1.0)
        self.assertEqual([r["type"] for r in [dict(zip(("id", "level", "subject_id", "type", "reason", "review_by"), r))
                                             for r in sm.overrides_due()]], ["pin"])   # review_by already past
        self.model(sm.set_override, "item", self.top, "quiet-until", "later", "2026-12-01", until_on="2026-11-20")
        self.assertNotIn(self.top, self.ids())
        self.assertEqual(self.x("SELECT who, fact_key, answer_id IS NOT NULL FROM kg_facts WHERE fact_key IN ('pin','quiet_until') ORDER BY id"),
                         [("owner", "pin", 1), ("owner", "quiet_until", 1)])             # his word, each citing its answer
        self.model(sm.end_override, "item", self.top, "quiet-until")
        self.assertIn(self.top, self.ids())
        self.model(sm.end_override, "item", self.nodate, "pin")
        self.assertNotIn(self.nodate, self.ids())

    def test_machine_guess_link_does_not_move_the_list(self):
        import store_graph as sg
        def go(c):
            p = sg.thing(c, "project", "Guessed")
            sg.assert_fact(c, p, "date_window", "2026-10-01..2026-11-13", "ai_guess", "guess", "code")
            sg.add_link(c, sg.thing(c, "item", str(self.nodate)), "part_of", p, "ai_guess", "guess", "code")
        self.model(go)
        self.assertNotIn(self.nodate, self.ids())


class WeekKeepsOnlyTheContract(Base):
    """Reader 5 (gc week). PLANTED: an engine rank row in kg_scores must not leak into gc week / gc urgent; the keys are exactly
    the ones docs/planning-interface.md lists."""
    def test_rank_does_not_leak_and_keys_are_the_contract(self):
        os.environ["AGE_NOW"] = "2026-11-12T09:00:00+00:00"
        try:
            i = store_items.upsert_item("t", "x", "task", title="x", occurred_at="2026-11-10T10:00:00Z", due_at="2026-11-14", status="open")[0]
            self.x("INSERT INTO kg_scores(subject_ref,signal,signal_version,value,reason,computed_at) VALUES(?,'rank','1',9.0,'planted','x')", ("item:%d" % i,))
            d = store.week_digest("2026-11-09", "2026-11-16")
            self.assertEqual(set(d), {"start", "end", "as_of", "counts", "top_urgent", "due_in_window", "open_proposals", "overdue_reviews"},
                             "gc week carries something outside docs/planning-interface.md")
            self.assertEqual(set(d["counts"]), {"arrived", "arrived_total", "open_proposals", "due_in_window", "expiry_questions"})
            item_keys = {"item_id", "source", "kind", "title", "person_address", "due_at", "status", "urgency", "pinned", "projects"}
            self.assertTrue(d["top_urgent"])
            self.assertTrue(all(set(u) == item_keys for u in d["top_urgent"] + store.urgent_items()))
        finally:
            os.environ.pop("AGE_NOW", None)


if __name__ == "__main__":
    unittest.main()
