"""Tests for store.py on a temp DB built from migrations/001_baseline.sql. The real rig.db is never opened."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import os, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import gc_settings  # noqa: E402
import store

REAL_DB = Path(gc_settings.db_path())


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "rig.db")
        con = sqlite3.connect(self.path)  # test fixture only (tests/ is outside the guard)
        con.executescript((ROOT / "migrations/001_baseline.sql").read_text())
        con.execute("PRAGMA user_version=1")
        con.commit(); con.close()
        store.set_path(self.path)
        self.addCleanup(store.set_path, None)

    def test_not_real_db(self):
        self.assertNotEqual(Path(store.db_path()).resolve(), REAL_DB.resolve())

    def test_meta(self):
        self.assertEqual(store.user_version(), 1)
        self.assertIn("messages", store.table_counts())
        store.append_event("x")  # first write connection switches the file to WAL (db.connect)
        self.assertEqual(store.journal_mode(), "wal")

    def test_events(self):
        store.append_event("pull", {"n": 2}, at="2026-01-01T00:00:00Z")
        store.append_event("backup", "ok", at="2026-01-02T00:00:00Z")
        ev = store.recent_events(5)
        self.assertEqual([e["kind"] for e in ev], ["backup", "pull"])
        self.assertEqual(ev[1]["detail"], '{"n": 2}')
        self.assertEqual(len(store.recent_events(5, kind="pull")), 1)
        with self.assertRaises(ValueError):
            store.append_event("")

    def test_source_state(self):
        self.assertIsNone(store.get_source_state("gmail"))
        store.set_source_state("gmail", "2026-01-01T00:00:00Z", 5)
        store.set_source_state("gmail", "2026-01-02T00:00:00Z", 7)
        self.assertEqual(store.get_source_state("gmail")["rows"], 7)
        self.assertEqual(len(store.all_source_state()), 1)

    def test_messages(self):
        for i, ms in enumerate([100, 200, 300]):
            store.upsert_message({"id": "m%d" % i, "thread_id": "t", "internal_date": ms, "subject": "s%d" % i,
                                  "is_sent": 1 if i == 2 else 0})
        self.assertEqual([m["id"] for m in store.messages_between(100, 300)], ["m0", "m1"])
        self.assertEqual([m["id"] for m in store.messages_between(100, 400, include_sent=False)], ["m0", "m1"])
        self.assertEqual(store.message_envelope("m1")["subject"], "s1")
        self.assertIsNone(store.message_envelope("nope"))
        self.assertEqual(len(store.thread_messages("t")), 3)
        self.assertEqual(store.newest_message_ms(), 300)
        self.assertEqual(store.message_count(), 3)

    def test_upsert_whitelist(self):
        with self.assertRaises(ValueError):
            store.upsert_message({"id": "x", "bogus": 1})
        with self.assertRaises(ValueError):
            store.upsert_message({"subject": "no id"})
        with self.assertRaises(ValueError):
            store.upsert_message({"id": "x", "a); DROP TABLE messages;--": 1})  # column names never reach SQL
        self.assertEqual(store.message_count(), 0)

    def test_sql_injection_in_values(self):
        store.upsert_filter("f'; DROP TABLE filters;--", "{}", "{}")
        self.assertEqual(len(store.filters()), 1)

    def test_filters_contacts(self):
        store.upsert_filter("f1", '{"a":1}', '{"b":2}')
        store.upsert_contact("people/1", '["a@x.com"]', "[]")
        self.assertEqual(store.filters()[0]["criteria_json"], '{"a":1}')
        self.assertEqual(store.contacts()[0]["resource_name"], "people/1")

    def test_calendar_tasks(self):
        store.upsert_calendar_event({"id": "e1", "start": "2026-01-02T10:00:00Z", "summary": "x"})
        store.upsert_calendar_event({"id": "e2", "start": "2026-02-02T10:00:00Z"})
        self.assertEqual([e["id"] for e in store.calendar_events_between("2026-01-01", "2026-02-01")], ["e1"])
        store.upsert_task({"id": "t1", "title": "a", "status": "needsAction"})
        store.upsert_task({"id": "t2", "title": "b", "status": "completed"})
        self.assertEqual([t["id"] for t in store.tasks("completed")], ["t2"])
        self.assertEqual(len(store.tasks()), 2)

    def test_runs_errors_quarantine(self):
        store.record_run("2026-01-01", "2026-01-02", {"a": 1}, {"n": 2})
        self.assertEqual(store.recent_runs(1)[0]["counts"], '{"n": 2}')
        store.record_error("m1", "message", "boom", "2026-01-01")
        store.record_quarantine("m1", "message", "block", "why", "2026-01-01")
        self.assertEqual(store.quarantined()[0]["reason"], "why")

    def test_world_model_views(self):
        con = sqlite3.connect(self.path)
        con.execute("INSERT INTO people(id,label,tier_guess,tier_override) VALUES(1,'A','normal','high')")
        con.execute("INSERT INTO rules(id,match_kind,match_value,need_guess,need_override,status) "
                    "VALUES(1,'domain','x.com','low','high','approved')")
        con.execute("INSERT INTO rules(id,match_kind,match_value,status) VALUES(2,'domain','y.com','proposed')")
        con.execute("INSERT INTO circles(id,name) VALUES(1,'Fam')")
        con.execute("INSERT INTO relationship_scores(address,score_guess,score_override) VALUES('a@x.com',1.0,5.0)")
        con.execute("INSERT INTO canon_facts(category,entity,detail_guess) VALUES('bank','B','d')")
        con.commit(); con.close()
        self.assertEqual(len(store.people()), 1)
        self.assertEqual(len(store.circles()), 1)
        self.assertEqual(len(store.rules()), 2)
        r = store.rules(approved_only=True)
        self.assertEqual((len(r), r[0]["need"]), (1, "high"))  # override wins through the view
        self.assertEqual(store.relationship_score("A@X.com")["score"], 5.0)
        self.assertEqual(store.relationship_scores()[0]["address"], "a@x.com")
        self.assertEqual(store.canon_facts()[0]["entity"], "B")
        for f in (store.addresses, store.circle_members, store.rule_exceptions, store.facts, store.keywords):
            self.assertEqual(f(), [])

    def test_answer_log_append_only(self):
        store.append_answer("f.md", 1, "free", 0, "my words", "{}", subject_key="a@x.com")
        self.assertEqual(store.answer_log()[0]["text_verbatim"], "my words")
        with self.assertRaises(sqlite3.IntegrityError):  # UNIQUE(source_file, entry_kind, ordinal)
            store.append_answer("f.md", 1, "free", 0, "dup", "{}")
        con = sqlite3.connect(self.path)
        with self.assertRaises(sqlite3.DatabaseError):
            con.execute("DELETE FROM answer_log")
        con.close()

    def test_corrections_wm_meta(self):
        store.append_correction("2026-01-01", "wrong_need", "rule:1", "low", "high", "owner-one")
        self.assertEqual(store.corrections()[0]["new"], "high")
        with self.assertRaises(sqlite3.IntegrityError):
            store.append_correction("2026-01-01", "not_a_kind", "t", None, None, "s")
        store.set_wm_meta("k", "v", "2026-01-01")
        self.assertEqual(store.wm_meta(), {"k": "v"})

    def test_failed_write_rolls_back(self):
        with self.assertRaises(sqlite3.IntegrityError):
            store.append_correction("2026-01-01", "bad", "t", None, None, "s")
        self.assertEqual(store.corrections(), [])

    def test_reads_are_readonly(self):
        with store._read() as c:
            with self.assertRaises(sqlite3.OperationalError):
                c.execute("INSERT INTO events VALUES('a','b','c')")

    def test_gc_status_and_events(self):
        import migrate
        head = migrate.list_migrations()[-1][0]
        hp = os.path.join(self.tmp.name, "head.db")  # a DB at migrations HEAD, whatever head is
        con = sqlite3.connect(hp, isolation_level=None)
        for n, p in migrate.list_migrations():
            migrate.apply_file(con, p, n)
        con.close()
        store.set_path(hp)
        self.path = hp
        store.append_event("hello", "x")
        env = dict(os.environ, AGE_BACKUP_DIR=os.path.join(self.tmp.name, "b"), AGE_NOTES_ROOT=os.path.join(self.tmp.name, "n"))
        for args, want in ((["status"], "user_version: %d" % head), (["events", "3"], "hello"), (["migrate"], "up to date")):
            p = subprocess.run([sys.executable, str(ROOT / "gc.py"), "--db", self.path] + args,
                               capture_output=True, text=True, env=env)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn(want, p.stdout)


if __name__ == "__main__":
    unittest.main()
