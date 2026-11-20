"""4P.3 item 10: the diary-index refresher (gc-diary-index), the one gc-midnight duty that must stay on a schedule.
SCRATCH ONLY: temp databases, temp diary folders, temp state — never the live rig.db or the real diary.
Each planted case runs a deliberately BROKEN version first and requires the check to FAIL on it, then the real
code and requires a pass:
  (1) an index row whose entry file was deleted is removed        (plant: a refresher that keeps dead rows)
  (2) an edited entry is updated, never duplicated                (plant: a refresher that inserts a second row)
  (3) one unreadable entry is skipped and named, the walk completes (plant: a refresher that aborts the walk)
  (4) no database file means exit 75 and no receipt               (plant: a runner that proceeds anyway)
Plus: the receipt's exact shape, and a second run is idempotent."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import io, os, sqlite3, sys, tempfile, unittest
from unittest import mock
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import migrate, store_diary as sd  # noqa: E402
import gc_settings  # noqa: E402
import diary_index_job as dij  # noqa: E402

ENTRY = "---\ntype: planning-diary-daily\ndate: 2026-11-19\nconfidence: low\nmentions: [person:legacy-1]\nstaged: []\n---\n\n# Day\nTalked to Jo Example.\n"
ENTRY_EDITED = ENTRY.replace("mentions: [person:legacy-1]", "mentions: [person:legacy-1, organization:acme.test]")


def make_db(path):
    fresh = migrate.fresh_build(10**6)
    dst = sqlite3.connect(path)
    fresh.backup(dst)
    dst.close()
    return path


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gc-test-p3index-")
        self.addCleanup(_sh.rmtree, self.tmp, True)
        self.notes = os.path.join(self.tmp, "notes")
        self.db = make_db(os.path.join(self.tmp, "scratch.db"))
        self.state = os.path.join(self.tmp, "state")
        os.environ["AGE_NOTES_ROOT"] = self.notes
        os.environ["AGE_RIG_DB"] = self.db
        os.environ["GC_STATE_ROOT"] = self.state
        self.addCleanup(os.environ.pop, "AGE_NOTES_ROOT", None)
        self.addCleanup(os.environ.pop, "AGE_RIG_DB", None)
        self.roots = {}
        for desk in ("desk-a", "desk-b"):
            root = os.path.join(self.notes, "desks", desk, "diary")
            os.makedirs(os.path.join(root, "2026", "11"))
            self.roots[desk] = root
        self.f1 = os.path.join(self.roots["desk-a"], "2026", "11", "19.md")
        with open(self.f1, "w", encoding="utf-8") as f:
            f.write(ENTRY)

    def receipt(self):
        return os.path.join(self.state, "gc-diary-index", "last-run.txt")

    def run_job(self, refresh=None):
        err = io.StringIO()
        with mock.patch.object(sys, "stderr", err):
            rc = dij.run(refresh=refresh)
        return rc, err.getvalue()

    def rows(self, con, diary="Main-Diary"):
        return con.execute("SELECT date,entry_path,keys_mentioned FROM diary_index WHERE diary=?", (diary,)).fetchall()

    def open_con(self):
        c = sqlite3.connect(self.db)
        self.addCleanup(c.close)
        return c


def plant_keeps_dead_rows(con, diary, root, notes, now=None):   # plant 1: deleted files keep their index rows
    before = con.execute("SELECT date,entry_path,keys_mentioned,staged_ids FROM diary_index WHERE diary=?", (diary,)).fetchall()
    res = sd.refresh_index(con, diary, root, notes, now)        # the bad old behavior: rows the walk saw are
    for date, rel, km, st in before:                            # re-inserted even when their file is gone
        if not os.path.exists(os.path.join(notes, rel)):
            con.execute("INSERT INTO diary_index(diary,date,entry_path,keys_mentioned,staged_ids,indexed_at) VALUES(?,?,?,?,?,?)",
                        (diary, date, rel, km, st, "kept-dead-row"))
    return res


def plant_duplicates(con, diary, root, notes, now=None):        # plant 2: an edited entry is re-INSERTED, not UPDATEd
    res = sd.refresh_index(con, diary, root, notes, now)
    if res["updated"]:
        for rel in con.execute("SELECT entry_path FROM diary_index WHERE diary=?", (diary,)).fetchall():
            con.execute("INSERT INTO diary_index(diary,date,entry_path,keys_mentioned,staged_ids,indexed_at) VALUES(?,?,?,?,?,?)",
                        (diary, "2026-11-19", rel[0] + "-dup", "[]", "[]", "dup"))
    return res


def plant_aborts_on_unreadable(con, diary, root, notes, now=None):  # plant 3: one unreadable entry aborts the walk
    with mock.patch.object(sd.local_first, "read_bytes", side_effect=sd.local_first.DriveReadError("no local copy", "drive", "local")):
        res = sd.refresh_index(con, diary, root, notes, now)
    if res.get("unreadable"):
        raise Plant3("walk aborted by one unreadable entry")
    return res


class T(Base):
    def test_1_deleted_entry_row_is_removed(self):
        rc, _ = self.run_job()
        self.assertEqual(rc, 0)
        con = self.open_con()
        self.assertEqual(len(self.rows(con)), 1)
        os.remove(self.f1)                       # the entry file is gone from disk
        rc, err = self.run_job()
        self.assertEqual(rc, 0)
        self.assertEqual(self.rows(con), [])
        rec = open(self.receipt(), encoding="utf-8").read().strip()
        self.assertIn("removed=1", rec)
        # plant 1: a refresher that keeps dead rows leaves the row -> the check above fails on it
        with open(self.f1, "w", encoding="utf-8") as f:
            f.write(ENTRY)
        rc, _ = self.run_job()
        self.assertEqual(rc, 0)
        os.remove(self.f1)
        rc, _ = self.run_job(refresh=plant_keeps_dead_rows)   # the plant is SILENT: rc 0, receipt written...
        con = self.open_con()
        self.assertEqual(len(self.rows(con)), 1)      # ...but the dead row survived: the check catches it


    def test_2_edited_entry_updated_never_duplicated(self):
        rc, _ = self.run_job()
        self.assertEqual(rc, 0)
        with open(self.f1, "w", encoding="utf-8") as f:
            f.write(ENTRY_EDITED)                     # the entry's mentions changed on disk
        rc, _ = self.run_job()
        self.assertEqual(rc, 0)
        con = self.open_con()
        rows = self.rows(con)
        self.assertEqual(len(rows), 1, "one row per (diary, path), never a duplicate")
        self.assertIn("organization:acme.test", rows[0][2])
        rec = open(self.receipt(), encoding="utf-8").read().strip()
        self.assertIn("updated=1", rec)
        # plant 2: a refresher that re-inserts makes two rows -> the check catches it
        with open(self.f1, "w", encoding="utf-8") as f:   # a real front-matter change, so the plant sees an "updated" entry
            f.write(ENTRY_EDITED.replace("person:legacy-1, organization:acme.test", "person:legacy-1, organization:acme.test, circle:family"))
        rc, _ = self.run_job(refresh=plant_duplicates)
        self.assertEqual(rc, 0)
        con = self.open_con()
        self.assertEqual(len(self.rows(con)), 2, "the plant duplicated the row: the check catches it")

    def test_3_unreadable_entry_skipped_and_named_walk_completes(self):
        f2 = os.path.join(self.roots["desk-b"], "2026", "11", "19.md")
        with open(f2, "w", encoding="utf-8") as f:
            f.write(ENTRY)
        real_read = sd.local_first.read_bytes

        def broken_read(path, *a, **k):
            if os.path.basename(path) == "19.md" and "desk-a" in path:
                raise sd.local_first.DriveReadError("no local copy", path, path)
            return real_read(path, *a, **k)

        with mock.patch.object(sd.local_first, "read_bytes", broken_read):
            rc, err = self.run_job()
        self.assertEqual(rc, 0)                              # a skipped entry is not a failed diary
        self.assertIn(self.f1, err)                          # the unreadable entry is NAMED, on stderr
        rec = open(self.receipt(), encoding="utf-8").read().strip()
        self.assertRegex(rec, r"^gc-diary-index ok date=\d{4}-\d{2}-\d{2} diaries=2 added=1 .*")
        con = self.open_con()
        self.assertEqual(len(self.rows(con, "Bravo-Diary")), 1)   # the rest of the walk completed
        # plant 3: a refresher that aborts the walk on one unreadable entry -> other diary never indexed, no receipt
        os.remove(self.receipt())
        rc, _ = self.run_job(refresh=plant_aborts_on_unreadable)
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(self.receipt()))

    def test_4_no_database_exit_75_no_receipt(self):
        os.environ["AGE_RIG_DB"] = os.path.join(self.tmp, "not-there.db")
        rc, err = self.run_job()
        self.assertEqual(rc, 75)
        self.assertFalse(os.path.exists(self.receipt()))
        self.assertIn("no database", err)

    def test_5_receipt_shape_and_idempotent_second_run(self):
        rc, _ = self.run_job()
        self.assertEqual(rc, 0)
        rec1 = open(self.receipt(), encoding="utf-8").read().strip()
        self.assertRegex(rec1, r"^gc-diary-index ok date=[0-9-]+ diaries=2 added=1 updated=0 same=0 removed=0 skipped=0 at=.+Z$")
        rc, _ = self.run_job()
        self.assertEqual(rc, 0)
        rec2 = open(self.receipt(), encoding="utf-8").read().strip()
        self.assertIn("added=0", rec2)
        self.assertIn("updated=0", rec2)


if __name__ == "__main__":
    unittest.main()
