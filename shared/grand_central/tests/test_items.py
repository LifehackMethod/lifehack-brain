import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import os, sqlite3, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import db, migrate, store, store_items

MIG1 = [p for n, p in migrate.list_migrations() if n == 1][0]


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.tmp.name, "rig.db")
        c = sqlite3.connect(self.p, isolation_level=None)
        migrate.apply_file(c, MIG1, 1)
        c.execute("PRAGMA foreign_keys=ON")
        for i in range(5):
            c.execute("INSERT INTO messages(id,thread_id,internal_date,label_ids,from_addr,subject,is_sent) VALUES(?,?,?,?,?,?,?)",
                      ("m%d" % i, "t%d" % (i // 2), 1700000000000 + i * 1000, '["INBOX"]' if i % 2 else '["SENT"]',
                       "A%d@X.com" % i, "subj %d" % i, 1 if i == 4 else 0))
        for i in range(3):
            c.execute("INSERT INTO calendar_events(id,start,end,all_day,status,organizer_email,summary) VALUES(?,?,?,?,?,?,?)",
                      ("e%d" % i, "2026-11-1%dT10:00:00-05:00" % i, "x", 0, "confirmed", "Org@x.com", "ev %d" % i))
        for i in range(2):
            c.execute("INSERT INTO tasks(id,list_id,title,status,due,updated) VALUES(?,?,?,?,?,?)",
                      ("k%d" % i, "L", "task %d" % i, "needsAction", "2026-11-2%dT00:00:00.000Z" % i, "2026-11-01T00:00:00.000Z"))
        c.close()
        self.up()
        store.set_path(self.p)
        self.hand = os.path.join(self.tmp.name, "handoff")
        os.mkdir(self.hand)

    def up(self):
        c = sqlite3.connect(self.p, isolation_level=None)
        migrate.apply_file(c, [p for n, p in migrate.list_migrations() if n == 2][0], 2)
        c.close()

    def tearDown(self):
        store.set_path(None)
        self.tmp.cleanup()

    def q(self, sql, a=()):
        c = sqlite3.connect(self.p)
        try:
            return c.execute(sql, a).fetchall()
        finally:
            c.close()

    def test_migration_bumps_version_and_creates_tables(self):
        self.assertEqual(db.current_version(sqlite3.connect(self.p)), 2)
        names = {r[0] for r in self.q("SELECT name FROM sqlite_master")}
        for n in ("items", "item_events", "item_email", "item_calendar", "item_task", "text_pointers"):
            self.assertIn(n, names)

    def test_backfill_counts_and_idempotent(self):
        self.assertEqual(store_items.backfill_items(), {"gmail": 5, "calendar": 3, "tasks": 2})
        self.assertEqual(store_items.item_counts(), {"gmail": 5, "calendar": 3, "tasks": 2})
        self.assertEqual(self.q("SELECT count(*) FROM item_events")[0][0], 10)
        self.assertEqual(self.q("SELECT count(*) FROM item_email")[0][0], 5)
        self.assertEqual(store_items.backfill_items(), {"gmail": 0, "calendar": 0, "tasks": 0})
        self.assertEqual(self.q("SELECT count(*) FROM items")[0][0], 10)
        self.assertEqual(self.q("SELECT count(*) FROM item_events")[0][0], 10)
        it = store_items.get_item("gmail", "m4")
        self.assertEqual((it["kind"], it["status"], it["person_address"]), ("email", "sent", "a4@x.com"))
        self.assertEqual(store_items.get_item("gmail", "m1")["status"], "inbox")

    def test_upsert_and_queries(self):
        a, made = store_items.upsert_item("x", "1", "thing", title="t", occurred_at="2026-01-02")
        self.assertTrue(made)
        b, made = store_items.upsert_item("x", "1", "thing", title="t2", occurred_at="2026-01-02")
        self.assertEqual((a, made), (b, False))
        self.assertEqual(store_items.get_item("x", "1")["title"], "t2")
        self.assertEqual(len(store_items.items_between("2026-01-01", "2026-01-03", kind="thing")), 1)
        self.assertEqual(store_items.items_between("2026-01-03", "2026-01-04"), [])
        store_items.append_item_event(a, "arrived", at="2026-01-02T00:00:00Z")
        store_items.append_item_event(a, "labeled", at="2026-01-02T01:00:00Z", detail="Example-Label")
        self.assertEqual([e["kind"] for e in store_items.item_history(a)], ["arrived", "labeled"])
        with self.assertRaises(ValueError):
            store_items.upsert_item("x", "", "thing")

    def test_item_events_append_only(self):
        a, _ = store_items.upsert_item("x", "1", "thing")
        eid = store_items.append_item_event(a, "arrived")
        c = sqlite3.connect(self.p)
        with self.assertRaisesRegex(sqlite3.DatabaseError, "append-only"):
            c.execute("UPDATE item_events SET kind='x' WHERE id=?", (eid,))
        with self.assertRaisesRegex(sqlite3.DatabaseError, "append-only"):
            c.execute("DELETE FROM item_events WHERE id=?", (eid,))
        c.close()
        self.assertEqual(len(store_items.item_history(a)), 1)

    def test_pointer_stores_no_text(self):
        f = os.path.join(self.hand, "body.txt")
        open(f, "w", encoding="utf-8").write("SECRET-BODY-TEXT")
        a, _ = store_items.upsert_item("x", "1", "thing")
        pid = store_items.add_text_pointer(f, item_id=a, handoff_dir=self.hand)
        self.assertEqual(pid, store_items.add_text_pointer(f, item_id=a, handoff_dir=self.hand))
        row = store_items.text_pointers_for(a)[0]
        self.assertEqual((row["bytes"], len(row["sha256"])), (16, 64))
        self.assertTrue(store_items.verify_text_pointer(pid))
        cols = [r[1] for r in self.q("PRAGMA table_info(text_pointers)")]
        self.assertEqual(set(cols), {"id", "item_id", "path", "sha256", "bytes", "added_at"})
        self.assertEqual(self.q("SELECT count(*) FROM text_pointers WHERE path LIKE '%SECRET%'")[0][0], 0)
        raw = open(self.p, "rb").read() + (open(self.p + "-wal", "rb").read() if os.path.exists(self.p + "-wal") else b"")
        self.assertNotIn(b"SECRET-BODY-TEXT", raw)
        open(f, "w", encoding="utf-8").write("changed")
        self.assertFalse(store_items.verify_text_pointer(pid))

    def test_pointer_refuses_outside_handoff(self):
        out = os.path.join(self.tmp.name, "elsewhere.txt")
        open(out, "w", encoding="utf-8").write("x")
        with self.assertRaises(ValueError):
            store_items.add_text_pointer(out, handoff_dir=self.hand)
        with self.assertRaises(ValueError):
            store_items.add_text_pointer(os.path.join(self.hand, "nope.txt"), handoff_dir=self.hand)


if __name__ == "__main__":
    unittest.main()
