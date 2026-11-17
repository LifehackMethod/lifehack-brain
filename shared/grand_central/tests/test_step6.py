"""Step 6: desk-facing reads (store.threads_in_label / sender_context / thread_item_context / freshness),
the front-door readers in store_meaning, and the gc read commands. Temp DBs only; never the live rig.db."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import contextlib, io, json, os, sqlite3, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import step3_fixture  # noqa: E402
import importlib.util
import migrate, store, store_items, store_meaning as sm  # noqa: E402

spec = importlib.util.spec_from_file_location("rig_gc", os.path.join(ROOT, "gc.py"))
rig_gc = importlib.util.module_from_spec(spec); spec.loader.exec_module(rig_gc)

T0 = 1762900000000  # 2025-11-11, ms
H = 3600 * 1000


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
        os.environ["AGE_NOW"] = "2025-11-12T09:00:00+00:00"
        self.seed()

    def tearDown(self):
        store.set_path(None)
        if self._old is None:
            os.environ.pop("AGE_NOW", None)
        else:
            os.environ["AGE_NOW"] = self._old
        self.tmp.cleanup()

    def x(self, sql, a=()):
        c = sqlite3.connect(self.p)
        try:
            r = c.execute(sql, a).fetchall(); c.commit(); return r
        finally:
            c.close()

    def project(self, name, due, items=()):
        import store_graph as sg
        c = sqlite3.connect(self.p, isolation_level=None)
        try:
            c.execute("BEGIN")
            pid = sg.thing(c, "project", name)
            sg.assert_fact(c, pid, "date_window", "2025-10-01..%s" % due, "code", "likely", "code")
            for i in items:
                sg.add_link(c, sg.thing(c, "item", str(i)), "part_of", pid, "code", "likely", "code")
            c.execute("COMMIT")
            return pid
        finally:
            c.close()

    def seed(self):
        for i, n in (("Label_E", "Example-B-Inbox"), ("Label_D", "Example-C-Inbox"), ("INBOX", "INBOX")):
            store.upsert_label({"id": i, "name": n, "type": "user"})
        def m(id, th, ms, labels, frm, subj, unsub=0):
            store.upsert_message({"id": id, "thread_id": th, "internal_date": ms, "label_ids": json.dumps(labels),
                                  "from_addr": frm, "from_name": "N", "subject": subj, "list_unsubscribe_present": unsub, "is_sent": 0})
        m("m1", "t1", T0, ["Label_E"], "Agent@Agency.example", "Tryout A")
        m("m2", "t1", T0 + H, ["Label_E", "INBOX"], "agent@agency.example", "Re: Tryout A")
        m("m3", "t2", T0 + 2 * H, ["Label_E"], "cd@studio.example", "Tryout B", 1)
        m("m4", "t3", T0 + 3 * H, ["Label_D"], "bank@bank.example", "Statement")
        m("m5", "t4", T0 + 4 * H, ["Label_E_extra"], "x@y.example", "near-miss label id")
        # world model
        x = self.x
        x("INSERT INTO people(id,label,tier_guess,tier_override) VALUES(1,'Agent Smith','normal','high')")
        x("INSERT INTO addresses(address,person_id) VALUES('agent@agency.example',1)")
        x("INSERT INTO circles(id,name,kind_guess,domain_guess) VALUES(1,'Part-B Reps','standing','part-b')")
        x("INSERT INTO circle_members(circle_id,person_id,role) VALUES(1,1,'agent')")
        x("INSERT INTO relationship_scores(address,score_guess,score_override,basis) VALUES('agent@agency.example',0.4,0.9,'said')")
        x("INSERT INTO rules(match_kind,match_value,need_guess,status) VALUES('address','agent@agency.example','action-urgent','approved')")
        x("INSERT INTO rules(match_kind,match_value,need_guess,status) VALUES('domain','agency.example','action-urgent','proposed')")
        x("INSERT INTO rules(match_kind,match_value,need_guess,status) VALUES('domain','other.com','nothing','approved')")
        store.graph_write("copy_legacy")   # sender_context reads the one model (2.4 reader 2)
        import store_meaning as sm   # her pin is a fact in the one model (2.4 reader 4)
        c = sqlite3.connect(self.p, isolation_level=None)
        try:
            c.execute("BEGIN")
            sm.set_override(c, "person", c.execute("SELECT id FROM kg_things WHERE legacy_ref='people:1'").fetchone()[0], "pin", "she matters", "2026-01-01")
            c.execute("COMMIT")
        finally:
            c.close()


class Threads(Base):
    def test_label_by_name_and_id_same(self):
        a = store.threads_in_label("Example-B-Inbox"); b = store.threads_in_label("Label_E")
        self.assertEqual(a, b)
        self.assertEqual([t["thread_id"] for t in a], ["t2", "t1"])  # newest first

    def test_exact_element_not_substring(self):
        self.assertNotIn("t4", [t["thread_id"] for t in store.threads_in_label("Label_E")])
        self.assertEqual(store.threads_in_label("Label_E_extra"), [])  # not a registered label

    def test_thread_rollup(self):
        t1 = [t for t in store.threads_in_label("Example-B-Inbox") if t["thread_id"] == "t1"][0]
        self.assertEqual(sorted(t1["message_ids"]), ["m1", "m2"])
        self.assertEqual(t1["newest_ms"], T0 + H)
        self.assertEqual(t1["subject"], "Re: Tryout A")
        self.assertEqual(t1["label_ids"], ["Label_E", "INBOX"])

    def test_since_and_limit_and_unknown(self):
        self.assertEqual([t["thread_id"] for t in store.threads_in_label("Example-B-Inbox", since=T0 + 2 * H)], ["t2"])
        self.assertEqual([t["thread_id"] for t in store.threads_in_label("Example-B-Inbox", since="2025-11-11T00:00:00Z")], ["t2", "t1"])
        self.assertEqual(len(store.threads_in_label("Example-B-Inbox", limit=1)), 1)
        self.assertEqual(store.threads_in_label("No-Such-Label"), [])
        self.assertEqual(store.threads_in_label("Example-B-Inbox", since="2030-01-01"), [])

    def test_unsub_flag(self):
        t2 = store.threads_in_label("Example-B-Inbox")[0]
        self.assertEqual(t2["list_unsubscribe_present"], 1)


class Sender(Base):
    def test_known_sender(self):
        c = store.sender_context("Agent@Agency.example")
        self.assertTrue(c["known"]); self.assertEqual(c["person"]["label"], "Agent Smith")
        self.assertEqual(c["tier"], "high")                       # override wins over guess
        self.assertIsInstance(c["relationship_score"], float)     # now the computed standing (nothing stored); the old 0-10 guess is gone
        self.assertIsInstance(c["relationship_basis"], str)
        self.assertEqual([x["name"] for x in c["circles"]], ["Part-B Reps"])
        self.assertEqual(sorted((r["match_kind"], r["status"]) for r in c["rules_matching"]),
                         [("address", "approved"), ("domain", "proposed")])  # other.com not matched
        self.assertEqual(c["first_seen_ms"], T0); self.assertEqual(c["message_count"], 2)  # m1 (mixed case) + m2, case-insensitive
        self.assertEqual(len(c["overrides"]), 1)

    def test_display_name_form(self):
        self.assertEqual(store.sender_context("Agent <agent@agency.example>")["address"], "agent@agency.example")

    def test_unknown_sender(self):
        c = store.sender_context("stranger@nowhere.example")
        self.assertFalse(c["known"]); self.assertIsNone(c["person"]); self.assertEqual(c["relationship_score"], 0.0)
        self.assertEqual(c["rules_matching"], []); self.assertEqual(c["circles"], []); self.assertEqual(c["message_count"], 0)
        self.assertIsNone(c["first_seen_ms"])


class Context(Base):
    def test_thread_item_context(self):
        store_items.backfill_items()
        iid = store_items.get_item("gmail", "m2")["id"]
        pid = self.project("Show", "2025-11-12", [iid])
        c = store.thread_item_context("t1")
        self.assertEqual(len(c["items"]), 2)
        self.assertEqual([p["name"] for p in c["projects"]], ["Show"])
        self.assertEqual(c["urgency"], 1.0)                      # due today
        self.assertTrue(all(i["history"] for i in c["items"]))   # 'arrived' event each

    def test_unknown_thread_empty(self):
        c = store.thread_item_context("nope")
        self.assertEqual((c["items"], c["projects"], c["urgency"]), ([], [], None))

    def test_no_items_table_tolerated(self):
        p2 = os.path.join(self.tmp.name, "old.db")
        c = sqlite3.connect(p2, isolation_level=None)
        migrate.apply_file(c, [q for n, q in migrate.list_migrations() if n == 1][0], 1); c.close()
        store.set_path(p2)
        self.assertEqual(store.thread_item_context("t1")["items"], [])


class FrontDoorReaders(Base):
    def test_wrappers_match_con_functions(self):
        store_items.backfill_items()
        iid = store_items.get_item("gmail", "m1")["id"]
        pid = self.project("P", "2025-11-20", [iid])
        self.x("INSERT INTO notes(subject_kind,subject_id,body,created_at) VALUES('person',1,'hi','x')")
        self.x("INSERT INTO queue(kind,subject_ref,question,created_at) VALUES('k','person:1','q?','x')")
        con = sqlite3.connect(self.p)
        try:
            self.assertEqual(sm.projects_of_item(iid), sm.item_projects(con, iid))
            self.assertEqual(sm.urgency_of_item(iid), sm.item_urgency(con, iid))
            self.assertEqual(sm.notes_of("person", 1), sm.notes_for(con, "person", 1))
            self.assertEqual(sm.score_of_person(1), sm.person_score(con, 1))
            self.assertEqual(sm.open_queue(), [tuple(r) for r in sm.queue_open(con)])
            self.assertEqual(sm.project_urgencies(), sm.project_urgency(con))
        finally:
            con.close()
        self.assertEqual(sm.projects_of_item(iid), [pid])

    def test_wrappers_are_read_only(self):
        sm.open_queue()
        with store._read() as c:
            with self.assertRaises(sqlite3.OperationalError):
                c.execute("INSERT INTO notes(subject_kind,subject_id,body,created_at) VALUES('person',1,'x','x')")


class Fresh(Base):
    def test_no_gmail_row_is_stale(self):
        f = store.freshness()
        self.assertTrue(f["stale"]); self.assertIn("no successful", f["reason"])
        self.assertEqual(f["newest_message_ms"], T0 + 4 * H)

    def test_fresh_then_stale_by_threshold(self):
        store.set_source_state("gmail", "2025-11-12T08:00:00Z", 5)
        f = store.freshness()
        self.assertFalse(f["stale"]); self.assertEqual(f["age_min"], 60.0)
        self.assertTrue(store.freshness(max_age_min=30)["stale"])
        os.environ["AGE_STALE_MIN"] = "10"
        try:
            self.assertTrue(store.freshness()["stale"])
        finally:
            os.environ.pop("AGE_STALE_MIN")
        store.set_source_state("gmail", "2025-11-10T08:00:00Z", 5)
        self.assertTrue(store.freshness()["stale"])  # 49h > 25h default

    def test_other_source_does_not_count(self):
        store.set_source_state("calendar", "2025-11-12T08:59:00Z", 1)
        self.assertTrue(store.freshness()["stale"])


class Cli(Base):
    def run_gc(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = rig_gc.main(["--db", self.p] + list(argv))
        return rc, out.getvalue(), err.getvalue()

    def test_fresh_exit_codes(self):
        rc, out, _ = self.run_gc("fresh", "--json")
        self.assertEqual(rc, 3); self.assertTrue(json.loads(out)["stale"])
        store.set_source_state("gmail", "2025-11-12T08:30:00Z", 5)
        rc, out, _ = self.run_gc("fresh", "--json")
        self.assertEqual(rc, 0); self.assertFalse(json.loads(out)["stale"])

    def test_new_who_thread_json(self):
        rc, out, _ = self.run_gc("new", "Example-B-Inbox", "--json")
        d = json.loads(out); self.assertEqual((rc, d["count"], d["threads"][0]["thread_id"]), (0, 2, "t2"))
        rc, out, _ = self.run_gc("who", "agent@agency.example", "--json")
        self.assertEqual((rc, json.loads(out)["known"]), (0, True))
        rc, out, _ = self.run_gc("thread", "t1", "--json")
        d = json.loads(out); self.assertEqual((rc, len(d["messages"])), (0, 2))
        rc, out, _ = self.run_gc("thread", "ghost", "--json")
        self.assertEqual(rc, 1)

    def test_text_output_and_error(self):
        rc, out, _ = self.run_gc("who", "nobody@xorg.example")
        self.assertIn("UNKNOWN", out)
        rc, out, err = self.run_gc("new", "Example-B-Inbox", "--since", "garbage", "--json")
        self.assertEqual(rc, 1); self.assertIn("error", json.loads(out))

    def test_read_only_no_writes(self):
        before = self.x("SELECT (SELECT COUNT(*) FROM events), (SELECT COUNT(*) FROM messages), (SELECT COUNT(*) FROM source_state)")
        for a in (("fresh",), ("new", "Example-B-Inbox"), ("who", "agent@agency.example"), ("thread", "t1")):
            self.run_gc(*a)
        self.assertEqual(before, self.x("SELECT (SELECT COUNT(*) FROM events), (SELECT COUNT(*) FROM messages), (SELECT COUNT(*) FROM source_state)"))

    def test_missing_db_errors_not_creates(self):
        out = io.StringIO()
        missing = os.path.join(self.tmp.name, "nope.db")
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = rig_gc.main(["--db", missing, "fresh", "--json"])
        self.assertEqual(rc, 1); self.assertFalse(os.path.exists(missing))


if __name__ == "__main__":
    unittest.main()
