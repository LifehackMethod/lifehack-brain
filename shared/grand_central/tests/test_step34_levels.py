"""Phase 3 step 3.4: levels above the person. Synthetic data on temp databases; never the live rig.db.
Each planted case runs a deliberately BROKEN version first and requires the check to FAIL on it, then the real one and requires it to pass:
(1) a code-written level is refused (plant: the database lock dropped); (2) his number beats a reporting chain (plant: a view that counts
the chain first); (3) no reports_to lines (or a broken chain) gives unknown, never a guess (plant: a view that defaults to 0)."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import glob, os, re, sqlite3, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import migrate, store_graph as sg, store_levels  # noqa: E402

VIEW_SQL = open(os.path.join(ROOT, "migrations", "024_levels_above_me.sql"), encoding="utf-8").read()
VIEW_SQL = VIEW_SQL[VIEW_SQL.index("CREATE VIEW v_levels_above_me"):]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.tmp.name, "rig.db")
        c = self.c = sqlite3.connect(self.p, isolation_level=None)
        for path in sorted(glob.glob(os.path.join(ROOT, "migrations", "*.sql"))):    # 023 may be absent here: the view needs nothing from it
            migrate.apply_file(c, path, int(os.path.basename(path)[:3]))
        sg.thing(c, "world", "world")
        self.t = {k: sg.thing(c, "person", k, key="person:" + k) for k in ("me", "a", "b", "c", "d")}
        self.aid = c.execute("INSERT INTO kg_answers(question,words,asked_by,said_on,subject_key,subject_kind,subject_name,fact_key,value,recorded_at,words_kind) "
                             "VALUES('q','his words','t','2026-11-01','person:me','person','me','x','y','2026-11-01T00:00:00Z','verbatim')").lastrowid

    def tearDown(self):
        self.c.close()
        self.tmp.cleanup()

    def boss(self, sub, boss):        # his word: sub reports to boss
        sg.add_link(self.c, self.t[sub], "reports_to", self.t[boss], "owner", "sure", "answer", answer_id=self.aid)

    def his_number(self, who, n):
        sg.assert_fact(self.c, self.t[who], "levels_above_me", n, "owner", "sure", "answer", answer_id=self.aid)

    def level(self, who):
        return store_levels.levels_above_me(self.c, "person:" + who)

    def replace_view(self, sql):
        self.c.execute("DROP VIEW v_levels_above_me")
        self.c.execute(sql)

    # the three checks, each returns True when the rule holds
    def check_code_level_refused(self):
        for how in ("front door", "database"):
            try:
                if how == "front door":
                    sg.assert_fact(self.c, self.t["a"], "levels_above_me", 2, "code", "sure", "code")
                else:
                    self.c.execute("INSERT INTO kg_facts(thing_id,fact_key,value,who,certainty,source_kind,created_at) VALUES(?,?,?,?,?,?,?)",
                                   (self.t["a"], "levels_above_me", "2", "code", "sure", "code", "2026-11-01T00:00:00Z"))
                return False                      # it went in
            except (sg.Refused, sqlite3.Error):
                pass
        return not self.c.execute("SELECT 1 FROM kg_facts WHERE fact_key='levels_above_me'").fetchone()

    def check_his_number_wins(self):
        self.boss("me", "a"); self.boss("a", "b"); self.boss("b", "c")
        self.his_number("c", 1)
        return self.level("c") == (1, "owner") and self.level("b") == (2, "chain")

    def check_no_reports_to_is_unknown(self):
        self.boss("me", "a")                                   # d is on no chain; b is past a break
        self.boss("c", "b")                                    # a floating pair, not reached from me
        return (self.level("d") == (None, "unknown") and self.level("b") == (None, "unknown")
                and self.level("c") == (None, "unknown") and self.level("a") == (1, "chain"))


class TestLevels(Base):
    def test_chain_of_three_gives_three(self):
        self.boss("me", "a"); self.boss("a", "b"); self.boss("b", "c")
        self.assertEqual([self.level(k) for k in "abc"], [(1, "chain"), (2, "chain"), (3, "chain")])
        self.assertEqual(self.level("d"), (None, "unknown"))

    def test_nothing_set_everyone_unknown_and_nothing_stored(self):
        self.assertTrue(all(lv is None and s == "unknown" for k, (lv, s) in store_levels.levels_above_me(self.c).items() if k != "person:me"))
        self.assertEqual(self.c.execute("SELECT count(*) FROM kg_facts WHERE fact_key='levels_above_me'").fetchone()[0], 0)

    def test_a_loop_cannot_hang_the_view(self):            # 023 refuses loops; the view must still end if one ever got in
        self.boss("me", "a"); self.boss("a", "b")
        for t in ("kg_links_no_loop_insert", "kg_links_no_loop_update"):
            self.c.execute("DROP TRIGGER IF EXISTS " + t)
        self.c.execute("INSERT INTO kg_links(from_id,kind,to_id,who,certainty,source_kind,answer_id,created_at) VALUES(?,?,?,?,?,?,?,?)",
                       (self.t["b"], "reports_to", self.t["a"], "owner", "sure", "answer", self.aid, "2026-11-01T00:00:00Z"))
        self.assertEqual(self.level("b"), (2, "chain"))

    def test_a_non_number_from_him_is_refused(self):
        with self.assertRaises(sqlite3.Error):
            self.c.execute("INSERT INTO kg_facts(thing_id,fact_key,value,who,certainty,source_kind,answer_id,created_at) VALUES(?,?,?,?,?,?,?,?)",
                           (self.t["a"], "levels_above_me", "two", "owner", "sure", "answer", self.aid, "2026-11-01T00:00:00Z"))

    def test_planted_code_written_level_is_refused(self):
        self.c.execute("DROP TRIGGER kg_facts_levels_is_his")                      # plant: the database lock removed, and the front door bypassed
        self.c.execute("INSERT INTO kg_facts(thing_id,fact_key,value,who,certainty,source_kind,created_at) VALUES(?,?,?,?,?,?,?)",
                       (self.t["a"], "levels_above_me", "2", "code", "sure", "code", "2026-11-01T00:00:00Z"))
        self.assertFalse(self.check_code_level_refused())                          # caught: the check fails on the plant
        # and even then the view ignores a level that is not his
        self.assertEqual(self.level("a"), (None, "unknown"))

    def test_real_code_written_level_is_refused(self):
        self.assertTrue(self.check_code_level_refused())

    def test_planted_chain_first_view_loses_his_number(self):
        self.replace_view(VIEW_SQL.replace("CASE WHEN h.level IS NOT NULL THEN h.level WHEN c.id IS NOT NULL THEN c.depth END",
                                           "CASE WHEN c.id IS NOT NULL THEN c.depth ELSE h.level END")
                                  .replace("CASE WHEN h.level IS NOT NULL THEN 'owner' WHEN c.id IS NOT NULL THEN 'chain' ELSE 'unknown' END",
                                           "CASE WHEN c.id IS NOT NULL THEN 'chain' WHEN h.level IS NOT NULL THEN 'owner' ELSE 'unknown' END"))
        self.assertFalse(self.check_his_number_wins())

    def test_real_his_number_beats_the_chain(self):
        self.assertTrue(self.check_his_number_wins())

    def test_planted_guessing_view_gives_zero_instead_of_unknown(self):
        self.replace_view(VIEW_SQL.replace("END AS level,", "ELSE 0 END AS level,", 1))
        self.assertFalse(self.check_no_reports_to_is_unknown())

    def test_real_no_reports_to_is_unknown(self):
        self.assertTrue(self.check_no_reports_to_is_unknown())


if __name__ == "__main__":
    unittest.main()
