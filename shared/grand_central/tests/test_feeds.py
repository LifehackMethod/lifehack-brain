#!/usr/bin/env python3
"""4P.0b: the named no-feed state (feeds.py) and the gate in the gc read commands, plus the quiet-week
receipt. SYNTHETIC only: tmp setup folders, tmp databases, AGE_NOW frozen; the live
DB and the real setup are never opened. Planted bad cases are marked PLANTED (each was shown FAILING
on the unfixed code before the fix: no DB -> 'unable to open database file' exit 1; empty DB -> a quiet
week indistinguishable from a connected one; a configured-but-errored calendar read as data).
Run: python3 -m unittest tests.test_feeds   (from shared/grand_central/)"""
import atexit as _ax, os as _o, shutil as _sh, sqlite3, tempfile as _t  # isolation: tmp only
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
import contextlib, importlib.util, io, json, os, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import feeds, gc_settings, migrate, store, clock  # noqa: E402

spec = importlib.util.spec_from_file_location("rig_gc", os.path.join(ROOT, "gc.py"))
rig_gc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rig_gc)

NOW = "2026-11-17T09:00:00+00:00"


class Base(unittest.TestCase):
    """Each test: its own tmp setup folder and tmp database; AGE_NOW frozen; store path restored."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.setup = os.path.join(self.tmp.name, "setup")
        os.makedirs(self.setup)
        self.db = os.path.join(self.tmp.name, "rig.db")
        self._old_env = {k: os.environ.get(k) for k in ("GC_SETUP_DIR", "AGE_NOW", "GC_DATA_ROOT")}
        os.environ["GC_SETUP_DIR"] = self.setup
        os.environ["AGE_NOW"] = NOW
        store.set_path(self.db)

    def tearDown(self):
        store.set_path(None)
        for k, v in self._old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def write_setup(self, doc=None):
        with open(os.path.join(self.setup, "gc.json"), "w", encoding="utf-8") as f:
            json.dump(doc if doc is not None else {"owner_name": "Probe", "owner_id": "probe",
                                                   "default_desk": "desk-a", "mailroom_user": "probe-mailroom"}, f)

    def make_db(self, path=None, rows=()):
        path = path or self.db
        c = sqlite3.connect(path, isolation_level=None)
        for n, mp in migrate.list_migrations():
            migrate.apply_file(c, mp, n)
        c.execute("CREATE TABLE IF NOT EXISTS source_state(source TEXT PRIMARY KEY, last_success_at TEXT, rows INTEGER)")
        for src, at in rows:
            c.execute("INSERT OR REPLACE INTO source_state VALUES(?,?,?)", (src, at, 1))
        c.close()

    def gc(self, *argv, db=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = rig_gc.main(["--db", db or self.db] + list(argv))
        return rc, out.getvalue(), err.getvalue()


class FeedStates(Base):
    def test_no_setup_every_feed_not_set_up_and_the_gate_says_no_feed_connected(self):
        g = feeds.read_gate()
        self.assertEqual(g["state"], "no_feed_connected")
        self.assertEqual([f["state"] for f in g["feeds"].values()], ["not_set_up"] * 3)

    def test_setup_with_no_database_is_feed_failing_not_an_error(self):
        self.write_setup()                       # configured, but the database file does not exist
        g = feeds.read_gate()
        self.assertEqual(g["state"], "feed_failing")
        self.assertEqual([f["state"] for f in g["feeds"].values()], ["failing"] * 3)

    def test_email_without_mailroom_user_is_not_set_up_while_calendar_tasks_are(self):
        self.write_setup({"owner_name": "P", "owner_id": "p"})   # no mailroom_user key
        g = feeds.read_gate()
        self.assertEqual(g["feeds"]["email"]["state"], "not_set_up")
        self.assertEqual(g["feeds"]["calendar"]["state"], "failing")   # configured, no successful pull
        self.assertEqual(g["state"], "feed_failing")                    # something IS configured: distinguishable

    def test_PLANTED_broken_login_calendar_stale_reads_failing_never_not_set_up(self):
        self.write_setup()
        self.make_db(rows=[("calendar", "2026-11-13T00:00:00Z")])  # a pull 4 days ago: the errored/broken-login shape
        g = feeds.read_gate()
        self.assertEqual(g["feeds"]["calendar"]["state"], "failing")
        self.assertNotEqual(g["feeds"]["calendar"]["state"], "not_set_up")
        self.assertEqual(g["feeds"]["calendar"]["age_min"] > 18 * 60, True)
        self.assertEqual(g["state"], "feed_failing")

    def test_PLANTED_stale_feeds_never_hide_data_already_in_the_model(self):
        # build window review: with people in the model, every feed stale or missing still answers from the
        # model (gate None); the failing feeds show in feed_states / `gc status --json` instead.
        self.write_setup()
        self.make_db(rows=[("calendar", "2026-11-13T00:00:00Z"), ("tasks", "2026-11-13T00:00:00Z")])
        c = sqlite3.connect(self.db, isolation_level=None)
        c.execute("INSERT INTO kg_things(kind, key, name, created_by, created_at) VALUES('person', 'person:alex', 'Alex', 'code', '2026-11-01')")
        c.close()
        self.assertIsNone(feeds.read_gate())
        self.assertEqual(feeds.feed_states()["calendar"]["state"], "failing")

    def test_email_freshness_also_reads_the_daily_envelope_pull(self):
        self.write_setup({"mailroom_user": "_mailroom"})
        import clock as _clock
        self.make_db(rows=[("daily", _clock.now().strftime("%Y-%m-%dT%H:%M:%SZ"))])
        self.assertEqual(feeds.feed_states()["email"]["state"], "connected")

    def test_fresh_pulls_read_connected_and_the_gate_opens(self):
        self.write_setup()
        self.make_db(rows=[(s, "2026-11-17T08:00:00Z") for s in ("gmail", "calendar", "tasks")])
        self.assertIsNone(feeds.read_gate())     # connected: the reads answer from the model as before
        fs = feeds.feed_states()
        self.assertEqual([f["state"] for f in fs.values()], ["connected"] * 3)

    def test_email_honours_age_stale_min_like_store_freshness(self):
        self.write_setup()
        self.make_db(rows=[("gmail", "2026-11-17T08:00:00Z")])
        os.environ["AGE_STALE_MIN"] = "10"       # 60 min old > 10 min: failing under the tightened threshold
        try:
            self.assertEqual(feeds.feed_states()["email"]["state"], "failing")
        finally:
            os.environ.pop("AGE_STALE_MIN")
        self.assertEqual(feeds.feed_states()["email"]["state"], "connected")

    def test_the_rows_read_come_from_the_named_database_and_never_create_one(self):
        self.write_setup()
        missing = os.path.join(self.tmp.name, "nope.db")
        store.set_path(missing)
        try:
            self.assertEqual(feeds.read_gate()["state"], "feed_failing")
            self.assertFalse(os.path.exists(missing))    # a read never creates a database
        finally:
            store.set_path(self.db)


class CliReads(Base):
    def test_PLANTED_no_db_no_setup_every_read_is_the_named_state_exit_0(self):
        rc, out, _ = self.gc("week", "--json", db=os.path.join(self.tmp.name, "ghost.db"))
        d = json.loads(out)
        self.assertEqual((rc, d["state"]), (0, "no_feed_connected"))
        self.assertIn("feeds", d)
        for cmd in (("status",), ("upcoming",), ("due",), ("urgent", "--limit", "5"),
                    ("person", "nobody"), ("org", "nobody")):
            rc, out, _ = self.gc(*cmd, "--json", db=os.path.join(self.tmp.name, "ghost.db"))
            self.assertEqual((rc, json.loads(out)["state"]), (0, "no_feed_connected"), cmd)

    def test_PLANTED_empty_db_reads_the_named_state_not_a_quiet_week(self):
        self.write_setup()
        self.make_db()                           # migrated, zero rows: was indistinguishable from a quiet week
        rc, out, _ = self.gc("week", "--json")
        self.assertEqual((rc, json.loads(out)["state"]), (0, "feed_failing"))
        rc, out, _ = self.gc("person", "nobody", "--json")
        self.assertEqual((rc, json.loads(out)["state"]), (0, "feed_failing"))

    def test_text_reads_print_the_plain_line_and_exit_0(self):
        rc, out, _ = self.gc("week", db=os.path.join(self.tmp.name, "ghost.db"))
        self.assertEqual(rc, 0)
        self.assertIn("no feed connected", out)

    def test_connected_feed_output_is_unchanged(self):
        self.write_setup()
        self.make_db(rows=[(s, "2026-11-17T08:00:00Z") for s in ("gmail", "calendar", "tasks")])
        rc, out, _ = self.gc("urgent", "--limit", "5", "--json")
        d = json.loads(out)
        self.assertEqual((rc, d["count"], d["items"]), (0, 0, []))       # exactly the old shape, no gate keys
        rc, out, _ = self.gc("person", "nobody", "--json")
        self.assertEqual((rc, json.loads(out)["found"]), (1, False))     # not-found stays exit 1 with a feed
        rc, out, _ = self.gc("week", "--json")
        self.assertNotIn("state", json.loads(out))

    def test_PLANTED_status_json_on_a_broken_login_names_the_failing_feed(self):
        self.write_setup()
        self.make_db(rows=[("calendar", "2026-11-13T00:00:00Z")])
        rc, out, _ = self.gc("status", "--json")
        d = json.loads(out)
        self.assertEqual((rc, d["state"], d["feeds"]["calendar"]["state"]), (0, "feed_failing", "failing"))
        self.assertNotEqual(d["feeds"]["calendar"]["state"], "not_set_up")

    def test_status_json_with_a_connected_feed_adds_feeds_and_keeps_the_counts(self):
        self.write_setup()
        self.make_db(rows=[(s, "2026-11-17T08:00:00Z") for s in ("gmail", "calendar", "tasks")])
        rc, out, _ = self.gc("status", "--json")
        d = json.loads(out)
        self.assertEqual((rc, d["user_version"]), (0, 29))
        self.assertEqual({k: v["state"] for k, v in d["feeds"].items()},
                         {"email": "connected", "calendar": "connected", "tasks": "connected"})

    def test_PLANTED_status_does_not_crash_on_a_zero_byte_database_file(self):
        empty = os.path.join(self.tmp.name, "zero.db")
        open(empty, "w", encoding="utf-8").close()
        rc, out, err = self.gc("status", "--json", db=empty)
        self.assertEqual(rc, 0)
        d = json.loads(out)
        self.assertIn("state", d)            # zero rows recorded: the named state, never a traceback
        self.assertNotIn("Traceback", err)
        rc, out, err = self.gc("status", db=empty)
        self.assertEqual(rc, 0)
        self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
