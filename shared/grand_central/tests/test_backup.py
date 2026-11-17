"""Tests for backup.py. Everything runs in temp dirs; the real rig.db / notes folder are never touched.
Run: python3 -m unittest tests/test_backup.py   (or python3 tests/test_backup.py)"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import os, sqlite3, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import backup as B
import gc_settings  # noqa: E402

REAL_DB = Path(gc_settings.db_path())
REAL_NOTES = Path(gc_settings.configured_notes_root())


def make_db(path, wal=True, extra_ddl=""):
    con = sqlite3.connect(path)
    if wal:
        con.execute("PRAGMA journal_mode=WAL")
    con.executescript("""
        CREATE TABLE messages(id INTEGER PRIMARY KEY, subject TEXT, from_addr TEXT);
        CREATE TABLE tasks(id INTEGER PRIMARY KEY, title TEXT, notes TEXT);
        CREATE TABLE answer_log(id INTEGER PRIMARY KEY AUTOINCREMENT, text_verbatim TEXT);
    """ + extra_ddl)
    con.executemany("INSERT INTO messages(subject, from_addr) VALUES(?,?)", [(f"subj {i}", f"a{i}@x.com") for i in range(50)])
    con.executemany("INSERT INTO tasks(title, notes) VALUES(?,?)", [(f"t{i}", f"n{i}") for i in range(7)])
    con.execute("INSERT INTO answer_log(text_verbatim) VALUES('my own words')")
    con.commit()
    con.close()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.db, self.bdir, self.notes = t / "rig.db", t / "backups", t / "notes"
        make_db(self.db)
        env = {"AGE_RIG_DB": str(self.db), "AGE_BACKUP_DIR": str(self.bdir), "AGE_NOTES_ROOT": str(self.notes)}
        p = mock.patch.dict(os.environ, env); p.start(); self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_paths_are_not_real(self):
        self.assertNotEqual(B.rig_db().resolve(), REAL_DB.resolve())
        self.assertFalse(str(B.backup_dir()).startswith(str(Path(gc_settings.data_root()))))
        self.assertFalse(str(B.snapshot_dir()).startswith(str(REAL_NOTES)))
        self.assertTrue(str(B.snapshot_dir()).startswith(self.tmp.name))


class TestSingleFile(Base):
    def test_no_sidecars_after_snapshot_and_verify(self):
        out = B.snapshot()
        B.verify(out); B.verify(B.local_backup())
        for d, pat in ((B.snapshot_dir(), r"rig-\d{8}\.db"), (self.bdir, r"rig-\d{8}T\d{6}(-\d+)?Z\.db")):
            names = [p.name for p in d.iterdir()]
            self.assertTrue(names)
            for n in names:
                self.assertRegex(n, "^" + pat + "$")
        self.assertEqual(sqlite3.connect(out).execute("PRAGMA journal_mode").fetchone()[0], "delete")


class TestLocal(Base):
    def test_backup_while_wal_writer_open(self):
        w = sqlite3.connect(self.db, isolation_level=None)
        w.execute("BEGIN IMMEDIATE")
        w.execute("INSERT INTO messages(subject) VALUES('uncommitted')")
        out = B.local_backup()
        self.assertEqual(B.row_counts(out)["messages"], 50)  # committed state only, consistent
        w.execute("COMMIT"); w.close()
        self.assertEqual(B.integrity(out), ["ok"])

    def test_modes_and_retention(self):
        out = B.local_backup()
        self.assertEqual(oct(out.stat().st_mode & 0o777), "0o600")
        self.assertEqual(oct(self.bdir.stat().st_mode & 0o777), "0o700")
        for _ in range(B.KEEP_LOCAL + 4):
            B.local_backup()
        self.assertEqual(len(list(self.bdir.glob("rig-*.db"))), B.KEEP_LOCAL)

    def test_source_unchanged(self):
        before = B.row_counts(self.db)
        B.local_backup()
        self.assertEqual(B.row_counts(self.db), before)

    def test_backup_matches_guard(self):
        out = B.local_backup()
        self.assertTrue(B.backup_matches(out, self.db))
        c = sqlite3.connect(self.db); c.execute("INSERT INTO tasks(title) VALUES('new')"); c.commit(); c.close()
        self.assertFalse(B.backup_matches(out, self.db))  # stale backup no longer permits real-db use


class TestSnapshot(Base):
    def test_one_per_day_and_keep_14(self):
        import datetime as dt
        sd = B.snapshot_dir()
        base = dt.datetime(2026, 11, 1, 12, tzinfo=dt.timezone.utc)
        for day in range(20):
            with mock.patch.object(B, "_utcnow", return_value=base + dt.timedelta(days=day)):
                B.snapshot()
        names = sorted(p.name for p in sd.glob("rig-*.db"))
        self.assertEqual(len(names), 14)
        self.assertEqual(names[0], "rig-20261107.db"); self.assertEqual(names[-1], "rig-20261120.db")
        # same-day rerun replaces, not adds
        c = sqlite3.connect(self.db); c.execute("INSERT INTO tasks(title) VALUES('later')"); c.commit(); c.close()
        with mock.patch.object(B, "_utcnow", return_value=base + dt.timedelta(days=19, hours=5)):
            B.snapshot()
        self.assertEqual(len(list(sd.glob("rig-*.db"))), 14)
        self.assertEqual(B.row_counts(sd / "rig-20261120.db")["tasks"], 8)
        self.assertEqual(list(sd.glob(".*tmp")), [])

    def test_body_column_with_data_refused(self):
        c = sqlite3.connect(self.db)
        c.execute("ALTER TABLE messages ADD COLUMN body_text TEXT")
        c.execute("UPDATE messages SET body_text='secret email' WHERE id=1"); c.commit(); c.close()
        with self.assertRaises(SystemExit) as cm:
            B.snapshot()
        self.assertIn("messages.body_text", str(cm.exception))
        self.assertFalse(B.snapshot_dir().exists() and list(B.snapshot_dir().glob("*")))

    def test_empty_body_column_allowed_but_named_ones_checked(self):
        c = sqlite3.connect(self.db); c.execute("ALTER TABLE messages ADD COLUMN snippet TEXT"); c.commit(); c.close()
        B.snapshot()  # column exists but holds no data: ok
        for col in ("html", "text_plain", "snippet"):
            c = sqlite3.connect(self.db)
            try: c.execute(f"ALTER TABLE tasks ADD COLUMN {col} TEXT")
            except sqlite3.OperationalError: pass
            c.execute(f"UPDATE tasks SET {col}='x' WHERE id=1"); c.commit(); c.close()
            with self.assertRaises(SystemExit):
                B.snapshot()
            c = sqlite3.connect(self.db); c.execute(f"UPDATE tasks SET {col}=NULL"); c.commit(); c.close()

    def test_own_words_columns_not_flagged(self):
        B.check_no_body(B.local_backup())  # answer_log.text_verbatim has data and is fine


class TestRestore(Base):
    def test_round_trip(self):
        out = B.local_backup()
        to = Path(self.tmp.name) / "r" / "restore.db"
        ok, counts, probs = B.restore(out, to)
        self.assertTrue(ok, probs); self.assertEqual(counts, B.row_counts(self.db))
        a, b = sqlite3.connect(self.db), sqlite3.connect(to)
        for q in ("SELECT * FROM messages WHERE id IN (1,25,50) ORDER BY id", "SELECT * FROM tasks ORDER BY id", "SELECT * FROM answer_log"):
            self.assertEqual(a.execute(q).fetchall(), b.execute(q).fetchall())

    def test_refuses_existing_and_live_path(self):
        out = B.local_backup()
        with self.assertRaises(SystemExit): B.restore(out, self.db)
        existing = Path(self.tmp.name) / "e.db"; existing.write_bytes(b"x")
        with self.assertRaises(SystemExit): B.restore(out, existing)
        self.assertEqual(existing.read_bytes(), b"x")

    def test_verify_detects_corruption(self):
        out = B.local_backup()
        data = bytearray(out.read_bytes())
        for i in range(4096 * 2, min(len(data), 4096 * 2 + 400)): data[i] = 0xFF
        out.write_bytes(bytes(data))
        try:
            ok, _, probs = B.verify(out)
        except sqlite3.DatabaseError:
            ok = False
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
