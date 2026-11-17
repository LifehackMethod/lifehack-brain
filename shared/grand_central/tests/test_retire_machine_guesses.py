"""Phase 2 step 2.5 planted cases (synthetic, temp database): a guess with a later human fact is retired with no question;
a human fact is untouched; an ordinary guess becomes exactly one question; rows are kept."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import os, sqlite3, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "world_model")]
import migrate, store_graph as sg  # noqa: E402
import retire_machine_guesses as R  # noqa: E402


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.tmp.name, "rig.db")
        c = sqlite3.connect(self.p, isolation_level=None)
        for n, path in migrate.list_migrations():
            migrate.apply_file(c, path, n)
            # step 2.6: this fixture seeds old-table rows, which migration 020 freezes in a real database (temp DB only)
            for (_t,) in c.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'frozen!_%' ESCAPE '!'").fetchall():
                c.execute("DROP TRIGGER " + _t)
        c.close()
        self.con = sqlite3.connect(self.p, isolation_level=None)
        self.con.row_factory = sqlite3.Row
        c = self.con
        self.pa = sg.thing(c, "person", "Ann"); self.pb = sg.thing(c, "person", "Bob"); self.pc = sg.thing(c, "person", "Cy")
        # A: guess, then HIS later word on the same key (written raw, as old data: the guess stayed current)
        self.ga = c.execute("INSERT INTO kg_facts(thing_id,fact_key,value,who,certainty,source_kind,created_at) VALUES(?, 'role','boss','ai_guess','guess','file','t')", (self.pa,)).lastrowid
        a = sg.record_answer(c, "ann role?", "she is the plumber", "test", None, "person", "Ann", "role", "plumber")
        self.his = c.execute("SELECT id FROM kg_facts WHERE thing_id=? AND who ='owner'", (self.pa,)).fetchone()[0]
        c.execute("UPDATE kg_facts SET replaced_by=NULL WHERE id=?", (self.ga,))
        # B: plain guess about a person tied to a current project -> question
        pj = sg.thing(c, "project", "Pilot")
        aid = c.execute("INSERT INTO kg_answers(question,words,asked_by,said_on,recorded_at) VALUES('Bob on Pilot?','yes, Bob is on Pilot','test','2026-11-13','t')").lastrowid
        c.execute("INSERT INTO kg_links(from_id,kind,to_id,who,certainty,source_kind,answer_id,created_at) VALUES(?, 'involves', ?, 'owner','sure','answer',?,'t')", (pj, self.pb, aid))   # since 023, a project's people are his word
        # C: code 'likely' row (engine-recomputable) -> dropped, no question;  D: guess about an unimportant person -> dropped
        self.gc = c.execute("INSERT INTO kg_facts(thing_id,fact_key,value,who,certainty,source_kind,created_at) VALUES(?, 'member_item','1,2','code','likely','code','t')", (self.pc,)).lastrowid
        self.gd = c.execute("INSERT INTO kg_facts(thing_id,fact_key,value,who,certainty,source_kind,created_at) VALUES(?, 'role','x','ai_guess','guess','file','t')", (self.pc,)).lastrowid
        # E: a legacy copy is held
        self.ge = c.execute("INSERT INTO kg_facts(thing_id,fact_key,value,who,certainty,source_kind,source_ref,created_at) VALUES(?, 'tier','high','code','likely','legacy','people:9','t')", (self.pc,)).lastrowid
        self.gb = c.execute("INSERT INTO kg_facts(thing_id,fact_key,value,who,certainty,source_kind,created_at) VALUES(?, 'role','cousin','ai_research','likely','file','t')", (self.pb,)).lastrowid

    def tearDown(self):
        self.con.close(); self.tmp.cleanup()

    def test_planted(self):
        c = self.con
        before_his = tuple(c.execute("SELECT * FROM kg_facts WHERE id=?", (self.his,)).fetchone())
        nq0 = c.execute("SELECT count(*) FROM queue").fetchone()[0]; nf0 = c.execute("SELECT count(*) FROM kg_facts").fetchone()[0]
        R.apply(c)
        rep = lambda i: c.execute("SELECT replaced_by FROM kg_facts WHERE id=?", (i,)).fetchone()[0]
        self.assertEqual(rep(self.ga), self.his)                          # superseded by his word
        self.assertEqual(rep(self.gb), self.gb)                           # retired (self)
        self.assertEqual(tuple(c.execute("SELECT * FROM kg_facts WHERE id=?", (self.his,)).fetchone()), before_his)  # his fact untouched
        qs = c.execute("SELECT subject_ref,question FROM queue WHERE kind='confirm-guess'").fetchall()
        self.assertEqual(len(qs), 1)                                      # only B asked, A not
        self.assertIn("Bob", qs[0][1])
        self.assertEqual(rep(self.gc), self.gc)                           # recomputable: dropped, no question
        self.assertEqual(rep(self.gd), self.gd)                           # does not matter: dropped, no question
        self.assertIsNone(rep(self.ge))                                   # legacy copy held
        self.assertEqual(c.execute("SELECT count(*) FROM kg_facts").fetchone()[0], nf0)   # nothing deleted
        self.assertEqual(c.execute("SELECT count(*) FROM kg_current_facts WHERE who IN ('ai_guess','ai_research') OR (who='code' AND certainty<>'sure' AND source_kind<>'legacy')").fetchone()[0], 0)
        self.assertEqual(c.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_legacy_mirror_split(self):
        c = self.con
        c.execute("INSERT INTO rules(id,match_kind,match_value,need_guess,status,source) VALUES(1,'address','boss@x.test','action-urgent','approved','Owner 2026-11-13 test round')")
        c.execute("INSERT INTO rules(id,match_kind,match_value,need_guess,status,source) VALUES(2,'address','news@y.test','just-see','proposed','insider-grades-round1.json#round1:grade1')")
        c.execute("INSERT INTO answer_log(id,source_file,round,entry_kind,ordinal,subject_key,text_verbatim,raw_json) VALUES(900,'insider-grades-round1.json',1,'grade',1,'g@z.test','grade: keep','{}')")
        c.execute("INSERT INTO rules(id,match_kind,match_value,need_guess,status,source,answer_id) VALUES(3,'address','g@z.test','just-keep','proposed','insider-grades-round1.json#round1:grade2',900)")
        c.execute("INSERT INTO canon_facts(id,category,entity,detail_guess,status,source) VALUES(1,'union','SAG','Actor, Guild-Example','proposed','/x/CANON.md')")
        sg.copy_legacy(c)
        t1 = c.execute("SELECT id FROM kg_things WHERE legacy_ref='rules:1'").fetchone()[0]
        t2 = c.execute("SELECT id FROM kg_things WHERE legacy_ref='rules:2'").fetchone()[0]
        n0 = c.execute("SELECT count(*) FROM kg_facts").fetchone()[0]
        R.apply(c, include_legacy=True)
        cur = lambda t, k: c.execute("SELECT who,source_ref,answer_id FROM kg_facts WHERE thing_id=? AND fact_key=? AND replaced_by IS NULL", (t, k)).fetchall()
        got = cur(t1, "rule_status")
        self.assertEqual([tuple(r)[:2] for r in got], [("owner", "rules:1")])            # the approved rule is an owner fact, provenance kept
        self.assertIsNotNone(got[0][2])                                                   # ... citing a recorded answer
        t3 = c.execute("SELECT id FROM kg_things WHERE legacy_ref='rules:3'").fetchone()[0]
        self.assertEqual([r[0] for r in cur(t3, "need")], ["owner"])                      # a grade-file answer of his is his word
        w = c.execute("SELECT id FROM kg_things WHERE kind='world'").fetchone()[0]
        self.assertTrue(all(r[0] == "owner" for r in cur(w, "canon")) and len(cur(w, "canon")) == 1)   # canon line carried as owner
        self.assertEqual(cur(t2, "need"), [])                                             # the machine-made mirror row is retired
        self.assertEqual(cur(t2, "rule_status"), [])
        self.assertGreater(c.execute("SELECT count(*) FROM kg_facts").fetchone()[0], n0)  # copies added, nothing deleted
        self.assertEqual(c.execute("SELECT count(*) FROM kg_current_facts WHERE source_kind='legacy' AND who<>'owner'").fetchone()[0], 0)
        self.assertEqual(c.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_live_file_needs_the_lock(self):
        lk = os.path.join(self.tmp.name, "db-writer.lock")
        os.mkdir(lk)
        open(os.path.join(lk, "pid"), "w", encoding="utf-8").write("%d\n" % os.getpid())      # a live holder
        old = (R.LIVE_DB, R.LOCK_WAIT_S, os.environ.get("GC_DB_LOCK"))
        R.LIVE_DB, R.LOCK_WAIT_S = self.p, 1
        os.environ["GC_DB_LOCK"] = lk
        try:
            with self.assertRaises(SystemExit) as e:
                R.main(["--db", self.p, "--apply"])
            self.assertIn("lock is held", str(e.exception))
            n = self.con.execute("SELECT count(*) FROM kg_facts WHERE replaced_by IS NULL").fetchone()[0]
            self.assertGreater(n, 0)                                         # nothing was written
            self.assertIsNone(self.con.execute("SELECT replaced_by FROM kg_facts WHERE id=?", (self.gb,)).fetchone()[0])
        finally:
            R.LIVE_DB, R.LOCK_WAIT_S = old[0], old[1]
            os.environ.pop("GC_DB_LOCK") if old[2] is None else os.environ.__setitem__("GC_DB_LOCK", old[2])


if __name__ == "__main__":
    unittest.main()
