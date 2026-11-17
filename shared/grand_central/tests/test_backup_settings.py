"""Tests for the settings copy (backup.py settings / verify-settings) and `gc backup` failure behaviour.
All in temp dirs. Run: python3 tests/test_backup_settings.py"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import os, stat, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import backup as B
from test_backup import make_db


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.src, self.notes, self.bdir, self.db = t / "setup", t / "notes", t / "backups", t / "rig.db"
        self.src.mkdir()
        for n in ("expected", "keywords", "labels"):
            (self.src / f"{n}.json").write_text('{"n": "%s"}' % n)
        make_db(self.db)
        env = {"AGE_SETTINGS_DIR": str(self.src), "AGE_NOTES_ROOT": str(self.notes),
               "AGE_RIG_DB": str(self.db), "AGE_BACKUP_DIR": str(self.bdir)}
        p = mock.patch.dict(os.environ, env); p.start(); self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)


class TestSettings(Base):
    def test_copy_is_complete_and_checked(self):
        out = B.settings_snapshot()
        self.assertEqual(sorted(p.name for p in out.glob("*.json")), ["expected.json", "keywords.json", "labels.json"])
        self.assertEqual(B.check_settings(out), [])
        self.assertTrue(str(out).startswith(str(self.notes)))

    def test_planted_missing_file_is_flagged(self):
        out = B.settings_snapshot()
        (out / "labels.json").unlink()  # the snapshot "missed" a settings file
        probs = B.check_settings(out)
        self.assertEqual(probs, ["missing from snapshot: labels.json"])
        r = subprocess.run([sys.executable, str(ROOT / "backup.py"), "verify-settings", str(out)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("labels.json", r.stdout)

    def test_planted_changed_file_is_flagged(self):
        out = B.settings_snapshot()
        (out / "keywords.json").write_text("{}")
        self.assertEqual(B.check_settings(out), ["differs from source: keywords.json"])

    def test_empty_source_is_a_failure_not_a_success(self):
        for f in self.src.glob("*.json"):
            f.unlink()
        with self.assertRaises(SystemExit):
            B.settings_snapshot()

    def test_keeps_14(self):
        d = B.snapshot_dir(); d.mkdir(parents=True)
        for i in range(20):
            (d / f"settings-202610{i + 1:02d}").mkdir()
        B.settings_snapshot()
        self.assertEqual(len(list(d.glob("settings-*"))), 14)

    def test_db_snapshot_does_not_depend_on_settings(self):
        for f in self.src.glob("*.json"):
            f.unlink()
        self.assertTrue(B.snapshot().is_file())  # db snapshot unaffected by a broken settings folder


class TestGcBackupLoud(Base):
    def test_backup_ok(self):
        r = subprocess.run([sys.executable, str(ROOT / "gc.py"), "backup"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("backup ok", r.stdout)

    def test_planted_unwritable_destination_fails_loudly(self):
        # (backup.py re-opens its own folder's permissions, so "unwritable" = a destination that cannot exist:
        # its parent is a plain file, and a read-only parent folder)
        blocker = Path(self.tmp.name) / "a-file"
        blocker.write_text("x")
        env = dict(os.environ, AGE_BACKUP_DIR=str(blocker / "backups"))
        r = subprocess.run([sys.executable, str(ROOT / "gc.py"), "backup"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 1)
        self.assertIn("BACKUP FAILED", r.stderr)
        self.assertEqual(r.stdout, "")


if __name__ == "__main__":
    unittest.main()
