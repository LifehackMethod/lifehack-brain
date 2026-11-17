"""Tests for Step 5 (migrations/003_meaning.sql + store_meaning.py). All on temp DBs built from the migrations; never the live rig.db."""
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
import migrate, store_meaning as sm  # noqa: E402
import gc_settings  # noqa: E402

MIG = os.path.join(ROOT, "migrations")
STANDIN_002 = """CREATE TABLE items(id INTEGER PRIMARY KEY, source TEXT NOT NULL, source_id TEXT NOT NULL, due_at TEXT, UNIQUE(source, source_id));"""


def build(path):
    """001, then the real 002 if on disk (else a stand-in items table), then 003. Returns an isolation_level=None-free connection."""
    c = sqlite3.connect(path, isolation_level=None)
    migrate.apply_file(c, os.path.join(MIG, "001_baseline.sql"), 1)
    p2 = os.path.join(MIG, "002_items.sql")
    if not os.path.exists(p2):
        p2 = path + ".002.sql"
        open(p2, "w", encoding="utf-8").write(STANDIN_002)
    migrate.apply_file(c, p2, 2)
    migrate.apply_file(c, os.path.join(MIG, "003_meaning.sql"), 3)
    c.close()
    c = sqlite3.connect(path)
    c.execute("PRAGMA foreign_keys=ON")
    return c


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "t.db")
        self.con = build(self.path)
        self._old = os.environ.get("AGE_NOW")
        os.environ["AGE_NOW"] = "2026-11-12T09:00:00+00:00"

    def tearDown(self):
        if self._old is None:
            os.environ.pop("AGE_NOW", None)
        else:
            os.environ["AGE_NOW"] = self._old
        self.con.close(); self.tmp.cleanup()

    def circle(self, name, kind, until=None):
        cur = self.con.execute("INSERT INTO circles(name,kind_guess,valid_until) VALUES(?,?,?)", (name, kind, until))
        self.con.commit(); return cur.lastrowid

    def item(self, sid, due=None):
        cur = self.con.execute("INSERT INTO items(source,source_id,kind,title,due_at,created_at) VALUES('tasks',?, 'task','t',?,'2026-11-01T00:00:00+00:00')"
                               if self._real002() else "INSERT INTO items(source,source_id,due_at) VALUES('tasks',?,?)", (sid, due))
        self.con.commit(); return cur.lastrowid

    def _real002(self):
        return os.path.exists(os.path.join(MIG, "002_items.sql"))


class Meaning(Base):
    def test_version_is_3(self):
        self.assertEqual(self.con.execute("PRAGMA user_version").fetchone()[0], 3)

    def test_urgency_shape(self):
        u = lambda d, n: sm.urgency(d, n)
        self.assertIsNone(u(None, "2026-11-12"))
        self.assertEqual(u("2026-12-31", "2026-11-12"), sm.FLOOR)           # far out: floor
        rising = [u("2026-11-20", "2026-11-%02d" % d) for d in range(6, 21)]
        self.assertEqual(rising, sorted(rising))                             # rises toward the date
        self.assertEqual(u("2026-11-20", "2026-11-20"), 1.0)                 # peak on the day
        fading = [u("2026-11-20", "2026-11-%02d" % d) for d in range(20, 30)]
        self.assertEqual(fading, sorted(fading, reverse=True))               # fades after
        self.assertEqual(u("2026-11-20", "2026-11-27"), 0.0)
        self.assertEqual(sm.urgency("2026-11-12"), 1.0)                      # default clock = AGE_NOW
        tables = {r[0] for r in self.con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertFalse([t for t in tables if "urgen" in t])               # never stored
        for t in ("projects", "item_projects", "notes", "overrides", "queue"):
            self.assertFalse([c for c in self.con.execute("PRAGMA table_info(%s)" % t) if "urgen" in c[1]])

    def test_dated_circle_is_a_project_not_a_copy(self):
        d = self.circle("production: X", "dated", "2026-11-14")
        s = self.circle("family", "standing")
        pid = sm.project_from_circle(self.con, d)
        self.assertEqual(sm.project_from_circle(self.con, d), pid)           # idempotent
        with self.assertRaises(ValueError):
            sm.project_from_circle(self.con, s)
        name, due = self.con.execute("SELECT name, due_on FROM v_projects WHERE id=?", (pid,)).fetchone()
        self.assertEqual((name, due), ("production: X", "2026-11-14"))
        self.assertIsNone(self.con.execute("SELECT name FROM projects WHERE id=?", (pid,)).fetchone()[0])  # name not duplicated
        self.con.execute("UPDATE circles SET name='renamed' WHERE id=?", (d,))
        self.assertEqual(self.con.execute("SELECT name FROM v_projects WHERE id=?", (pid,)).fetchone()[0], "renamed")
        self.assertEqual(sm.sync_dated_circles(self.con), 0)
        self.circle("job: Y", "dated"); self.assertEqual(sm.sync_dated_circles(self.con), 1)

    def test_item_links_notes_and_urgency(self):
        d = self.circle("job", "dated", "2026-11-14"); pid = sm.project_from_circle(self.con, d)
        i = self.item("a"); j = self.item("b", "2026-11-13")
        sm.link_item(self.con, i, pid); sm.link_item(self.con, i, pid)
        self.assertEqual(sm.item_projects_v1(self.con, i), [pid])
        with self.assertRaises(ValueError):
            sm.link_item(self.con, 9999, pid)
        self.assertEqual(sm.item_urgency_v1(self.con, i), sm.urgency("2026-11-14"))   # inherits project due
        self.assertEqual(sm.item_urgency_v1(self.con, j), sm.urgency("2026-11-13"))   # own due wins
        sm.add_note(self.con, "project", pid, "wraps early"); sm.add_note(self.con, "project", pid, "second")
        self.assertEqual(sm.notes_for(self.con, "project", pid), ["wraps early", "second"])
        with self.assertRaises(sqlite3.IntegrityError):
            sm.add_note(self.con, "rule", 1, "x")

    def test_overrides(self):
        d = self.circle("job", "dated", "2026-11-30"); pid = sm.project_from_circle(self.con, d)
        base = sm.effective_urgency_v1(self.con, "project", pid, "2026-11-30")
        sm.add_override(self.con, "project", pid, "pin", "he said so", "2026-12-01")
        self.assertEqual(sm.effective_urgency_v1(self.con, "project", pid, "2026-11-30"), 1.0)
        o = sm.add_override(self.con, "project", pid, "quiet-until", "on vacation", "2026-12-01", until_on="2026-11-20")
        self.assertEqual(sm.effective_urgency_v1(self.con, "project", pid, "2026-11-30"), 0.0)
        self.assertEqual(sm.effective_urgency_v1(self.con, "project", pid, "2026-11-30", now="2026-11-20"), 1.0)  # quiet over, pin remains
        sm.retire_override(self.con, o)
        self.assertEqual(sm.effective_urgency_v1(self.con, "project", pid, "2026-11-30"), 1.0)
        self.assertLess(base, 1.0)
        for lvl in sm.LEVELS:                                                # one list, any level
            sm.add_override(self.con, lvl, 1, "pin", "r", "2026-11-12")
        self.assertEqual(len(sm.overrides_due_for_review_v1(self.con)), 4)      # the four review_by == today (pin on project not due)
        for bad in (dict(reason=""), dict(reason="  "), dict(review_by=None)):
            kw = dict(level="item", subject_id=1, type_="pin", reason="r", review_by="2026-12-01"); kw.update(bad)
            with self.assertRaises(ValueError):
                sm.add_override(self.con, kw["level"], kw["subject_id"], kw["type_"], kw["reason"], kw["review_by"])
        with self.assertRaises(sqlite3.IntegrityError):                      # quiet-until without a date
            sm.add_override(self.con, "item", 1, "quiet-until", "r", "2026-12-01")
        with self.assertRaises(sqlite3.IntegrityError):                      # unknown type / level
            self.con.execute("INSERT INTO overrides(level,subject_id,type,reason,review_by,created_at) VALUES('item',1,'mute','r','2026-12-01','x')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute("INSERT INTO overrides(level,subject_id,type,reason,review_by,created_at) VALUES('desk',1,'pin','r','2026-12-01','x')")

    def test_person_score_rollup(self):
        c = self.con
        c.execute("INSERT INTO people(id,label) VALUES(1,'A'),(2,'B'),(3,'C')")
        c.executemany("INSERT INTO addresses(address,person_id,person_id_override) VALUES(?,?,?)",
                      [("a1@x.com", 1, None), ("a2@x.com", 1, None), ("b1@x.com", None, 2), ("c1@x.com", 3, None), ("svc@x.com", None, None)])
        c.executemany("INSERT INTO relationship_scores(address,score_guess,score_override) VALUES(?,?,?)",
                      [("a1@x.com", 3, None), ("a2@x.com", 6, 2), ("b1@x.com", 5, None), ("svc@x.com", 9, None)])
        c.commit()
        self.assertEqual(sm.person_score(c, 1), 3)         # a2's override (2) beats its guess (6); best of 3 and 2
        self.assertEqual(sm.person_score(c, 2), 5)         # via person_id_override
        self.assertIsNone(sm.person_score(c, 3))           # address with no score
        self.assertEqual(c.execute("SELECT best_address, n_addresses FROM v_person_scores WHERE person_id=1").fetchone(), ("a1@x.com", 2))
        self.assertEqual(c.execute("SELECT COUNT(*) FROM v_person_scores").fetchone()[0], 3)  # services (no person) excluded

    def test_queue(self):
        q = sm.queue_add(self.con, "person-tier", "person:1", "Is A high tier?", "high")
        self.assertEqual([r[0] for r in sm.queue_open(self.con)], [q])
        aid = sm.queue_answer(self.con, q, "yes, high")
        row = self.con.execute("SELECT status, answer, answered_at FROM queue WHERE id=?", (q,)).fetchone()
        self.assertEqual((row[0], row[1]), ("answered", "yes, high")); self.assertTrue(row[2])
        self.assertIsNone(aid)  # words go to kg_answers via store.answer_proposal; no old answer_log row (2.4 reader 1)
        with self.assertRaises(ValueError):
            sm.queue_answer(self.con, q, "again")
        self.assertEqual(sm.queue_open(self.con), [])
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute("INSERT INTO queue(kind,subject_ref,question,status,created_at) VALUES('k','r','q','weird','x')")


if __name__ == "__main__":
    unittest.main()
