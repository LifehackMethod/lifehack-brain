"""Phase 2 step 2.6: rebuild, check, freeze. Temp DBs only; never the live rig.db.
Planted cases: (1) a planted difference between the rebuilt and the live model is reported by gc check; (2) a write to a frozen
old table is refused (insert, update, delete); (3) a write to the proposals table (queue) still works; (4) the health light
goes red on a dirty check and is green on a clean one; (5) rebuild_from_answers no longer trips the unique current-link index."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import datetime as dt, os, sqlite3, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import migrate, model_check, store, store_graph as sg  # noqa: E402
import status_lights as S  # noqa: E402

FROZEN = ("answer_log people addresses circles circle_members rules rule_exceptions facts keywords canon_facts corrections "
          "relationship_scores chapters chapter_closures entity_resets overrides notes projects item_projects desk_verdicts wm_meta").split()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.tmp.name, "rig.db")
        c = sqlite3.connect(self.p, isolation_level=None)
        for n, path in migrate.list_migrations():
            migrate.apply_file(c, path, n)
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


class Frozen(Base):
    def test_freeze_migration_exists_and_runs_before_any_later_one(self):
        nums = {os.path.basename(path): n for n, path in migrate.list_migrations()}
        freeze = [n for name, n in nums.items() if name.startswith("020_freeze")]
        self.assertEqual(freeze, [20])
        self.assertGreaterEqual(self.x("PRAGMA user_version")[0][0], 20)     # the freeze is applied; later migrations come after it
        self.assertTrue(all(n > 20 for name, n in nums.items() if not name.startswith("020_freeze") and n >= 20))

    def test_PLANTED_every_frozen_table_refuses_insert_update_delete(self):
        for t in FROZEN:
            names = {r[0] for r in self.x("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (t,))}
            for op in ("insert", "update", "delete"):
                self.assertIn("frozen_%s_no_%s" % (t, op), names)
        # real refusals through sqlite, one of each kind
        with self.assertRaises(sqlite3.IntegrityError):
            self.x("INSERT INTO people(label) VALUES('x')")
        c = sqlite3.connect(self.p, isolation_level=None)
        c.execute("DROP TRIGGER frozen_people_no_insert")
        c.execute("INSERT INTO people(id,label) VALUES(1,'A')")
        c.execute("CREATE TRIGGER frozen_people_no_insert BEFORE INSERT ON people BEGIN SELECT RAISE(ABORT, 'x'); END")
        for sql in ("UPDATE people SET label='B'", "DELETE FROM people"):
            with self.assertRaises(sqlite3.IntegrityError, msg=sql):
                c.execute(sql)
        c.close()

    def test_the_proposals_table_still_takes_writes(self):
        self.x("INSERT INTO queue(kind,subject_ref,question,proposed_answer,created_at) VALUES('apply-label','thread:1','Label it?','yes','x')")
        qid = self.x("SELECT id FROM queue")[0][0]
        self.x("UPDATE queue SET status='dismissed' WHERE id=?", (qid,))
        self.assertEqual(self.x("SELECT status FROM queue")[0][0], "dismissed")


class RebuildAndCheck(Base):
    def seed(self):
        with store._write() as c:
            sg.copy_legacy(c)                    # as in real history: the legacy copy and the engine's settings were seeded once
            import common as ec
            ec.seed_settings(c)
            sg.record_answer(c, "Who is Pat?", "Pat is high", "owner-session", subject_kind="person", subject_name="Pat Test",
                             fact_key="tier", value="high")
            sg.record_answer(c, "Pat's address?", "pat@example.test is Pat", "owner-session", subject_kind="address",
                             subject_name="pat@example.test", fact_key="link:address_of", value="person:pat test")
        import senders
        with store._write() as c:
            senders.build_senders(c)             # as production: pull.py runs the senders step after intake, and rebuild runs it too

    def test_rebuild_reproduces_the_model_same_keys(self):
        self.seed()
        res = model_check.check(self.p)
        self.assertTrue(res["clean"], res["sample"])
        self.assertGreater(res["rebuild"]["answers_replayed"], 0)

    def test_PLANTED_a_difference_is_reported(self):
        self.seed()

        def plant(con):
            con.execute("UPDATE kg_facts SET value='low' WHERE fact_key='tier' AND replaced_by IS NULL")
        res = model_check.check(self.p, mutate=plant)
        self.assertFalse(res["clean"])
        self.assertGreaterEqual(res["differences"], 2)          # the rebuilt row differs: one missing, one extra
        self.assertTrue(any(w == "facts" for w, _s, _r in res["sample"]))

    def test_PLANTED_a_missing_thing_key_is_reported(self):
        self.seed()

        def plant(con):
            con.execute("DELETE FROM kg_facts WHERE thing_id=(SELECT id FROM kg_things WHERE key='person:pat test')")
            con.execute("DELETE FROM kg_links")
            con.execute("DELETE FROM kg_things WHERE key='person:pat test'")
        res = model_check.check(self.p, mutate=plant)
        self.assertFalse(res["clean"])
        self.assertIn("things live_only", res["by_kind"])

    def test_PLANTED_rebuild_from_answers_no_longer_trips_the_unique_link_index(self):
        """Two code links on one pair, both superseded by his word: releasing both used to leave two current rows."""
        with store._write() as c:
            a = sg.thing(c, "person", "A Test"); b = sg.thing(c, "circle", "C Test")
            sg.add_link(c, a, "member_of", b, "code", "likely", "code", "r1")
            sg.record_answer(c, "In C?", "yes", "owner-session", subject_kind="person", subject_name="A Test",
                             fact_key="link:member_of", value="circle:c test")
            sg.add_link(c, a, "member_of", b, "code", "likely", "code", "r2")      # superseded by his word, a second row
            sg.rebuild_from_answers(c)                                              # must not raise IntegrityError
            cur = c.execute("SELECT count(*) FROM kg_links WHERE from_id=? AND to_id=? AND replaced_by IS NULL", (a, b)).fetchone()[0]
            self.assertEqual(cur, 1)


class HealthLight(unittest.TestCase):
    NOW = dt.datetime(2026, 11, 16, 18, 0, 0, tzinfo=dt.timezone.utc)

    def res(self, **kw):
        d = {"at": "2026-11-16T17:00:00Z", "clean": True, "differences": 0, "integrity_ok": True, "fk_problems": 0, "by_kind": {}}
        d.update(kw)
        return d

    def test_green_only_when_clean(self):
        self.assertEqual(S.model_light(self.res(), self.NOW)["status"], "OK")

    def test_PLANTED_dirty_check_is_red(self):
        l = S.model_light(self.res(clean=False, differences=3), self.NOW)
        self.assertEqual(l["status"], "ERROR")
        self.assertIn("3 difference", l["summary"])

    def test_PLANTED_no_result_or_stale_result_is_red(self):
        self.assertEqual(S.model_light(None, self.NOW)["status"], "ERROR")
        self.assertEqual(S.model_light(self.res(at="2026-11-10T00:00:00Z"), self.NOW)["status"], "ERROR")

    def test_light_never_crashes_its_caller(self):
        cfg = {"status_dir": tempfile.mkdtemp(), "model_check": True, "model_result": "/nonexistent-dir-x/y.json", "db": "/nonexistent/x.db"}
        out = S.run_lights(cfg, only=["morning"], dry_run=True)
        self.assertIn("model", out["lights"])
        self.assertEqual(out["lights"]["model"]["status"], "ERROR")


if __name__ == "__main__":
    unittest.main()
