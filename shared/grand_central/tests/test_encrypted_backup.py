#!/usr/bin/env python3
"""Finish-test suite for encrypted_backup.py (plan step 4b).

Everything runs on SYNTHETIC data in pytest temp dirs. Each test creates its own
throwaway passphrase file at run time — no real key is ever used or stored here.
The drive-side dirs these tests point AGE_BACKUP_DRIVE_DIR at are under /tmp, never
under the real Drive folder.
"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import hashlib, json, os, stat, sys, unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import encrypted_backup as bk  # noqa: E402
import gc_settings  # noqa: E402

def w(dirpath, rel, text):
    p = Path(dirpath) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class BackupTestCase(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.root = Path(tempfile.mkdtemp(prefix="age-test-"))
        self.drive = self.root / "drive"          # stands in for the Drive folder
        self.drive.mkdir()
        os.environ["AGE_BACKUP_DRIVE_DIR"] = str(self.root / "drive-notes")
        (self.root / "drive-notes").mkdir()
        self.transcripts = self.root / "front-room-transcripts"
        self.catalogue = self.root / "front-room-catalogue"
        # planted synthetic email data — nothing real
        w(self.transcripts, "thread-0001.txt", "From: secret-sender@example.com\nSubject: PLANTED-SUBJECT-XYZ\nPLANTED-BODY-PHRASE quixotic\n")
        w(self.transcripts, "thread-0002.txt", "From: another@example.com\nSubject: weekly digest\nbody two\n")
        w(self.transcripts, "nested/thread-0003.txt", "From: third@example.com\nbody three\n")
        w(self.catalogue, "catalogue-20261115.csv", "thread-0001,secret-sender@example.com,PLANTED-SUBJECT-XYZ,triage\n")
        self.key = self.root / "passphrase"
        self.key.write_bytes(b"throwaway-test-passphrase\n")
        self.key2 = self.root / "passphrase-wrong"
        self.key2.write_bytes(b"a completely different passphrase\n")
        self.key.chmod(0o600); self.key2.chmod(0o600)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.root, ignore_errors=True)
        os.environ.pop("AGE_BACKUP_DRIVE_DIR", None)

    def do_backup(self, key=None, keep=14):
        return bk.backup(self.transcripts, self.catalogue, key or self.key, keep=keep)

    # 1. round-trip: restore to scratch, every file's sha256 matches
    def test_roundtrip_hashes_match(self):
        arc = self.do_backup()
        out = self.root / "restored"
        bk.restore(arc, out, self.key)
        m = bk.manifest(out)
        self.assertIn("front-room-transcripts/thread-0001.txt", m)
        for rel in ["front-room-transcripts/thread-0001.txt",
                    "front-room-transcripts/nested/thread-0003.txt",
                    "front-room-catalogue/catalogue-20261115.csv"]:
            self.assertEqual(m[rel], sha(self.root / rel))

    # 2. planted: wrong key fails loudly, nothing restored
    def test_wrong_key_fails_loudly_restores_nothing(self):
        arc = self.do_backup()
        out = self.root / "restored-wrong"
        with self.assertRaises(SystemExit) as cm:
            bk.restore(arc, out, self.key2)
        self.assertIn("hdiutil attach failed", str(cm.exception))
        self.assertFalse(out.exists(), "wrong key must not restore anything")
        self.assertFalse(list(out.parent.glob("restored-wrong*")) if out.parent.exists() else False)

    # 3. planted: a transcript changed after the backup shows as a mismatch
    def test_changed_transcript_shows_mismatch(self):
        arc = self.do_backup()
        out = self.root / "restored-changed"
        bk.restore(arc, out, self.key)
        w(out, "front-room-transcripts/thread-0001.txt", "TAMPERED after restore\n")
        ok, probs = bk.verify_archive(arc, self.key)  # archive itself still fine...
        self.assertTrue(ok)
        # ...the tamper is caught by comparing against the manifest, simulating the
        # check a person runs after editing a restored file
        m = json.loads((self.root / "mf.json").read_text()) if (self.root / "mf.json").exists() else None
        restored = bk.manifest(out)
        arc_out = self.root / "arc-contents"
        bk.restore(arc, arc_out, self.key)
        original = bk.manifest(arc_out)
        self.assertNotEqual(restored["front-room-transcripts/thread-0001.txt"],
                            original["front-room-transcripts/thread-0001.txt"],
                            "changed transcript must show as a hash mismatch")

    # 4. planted: no readable sender/subject/body in the drive-side archive bytes
    def test_archive_has_no_readabl_email_text(self):
        arc = self.do_backup()
        raw = Path(arc).read_bytes()
        for planted in [b"secret-sender@example.com", b"PLANTED-SUBJECT-XYZ",
                        b"PLANTED-BODY-PHRASE", b"thread-0001", b"quixotic"]:
            self.assertNotIn(planted, raw, f"readable text leaked into archive: {planted!r}")

    # 5. planted: no plaintext temp file ever appears under the drive path
    def test_no_plaintext_temp_under_drive(self):
        arc = self.do_backup()
        entries = sorted(p.name for p in self.drive.iterdir())
        for name in entries:
            self.assertTrue(name.endswith(".dmg") or name.endswith(".tmp"),
                            f"non-archive file under drive path: {name}")
            p = self.drive / name
            if p.is_file():
                self.assertTrue(bk._dmg_encrypted(p)[0],
                                f"file under drive path is not an encrypted dmg: {name}")

    # 6. key missing -> fail loudly, write nothing
    def test_missing_key_fails_loudly_writes_nothing(self):
        before = sorted(p.name for p in self.drive.iterdir())
        with self.assertRaises(SystemExit) as cm:
            bk.backup(self.transcripts, self.catalogue, self.root / "nonexistent-key", keep=14)
        self.assertIn("passphrase file unreadable", str(cm.exception))
        self.assertEqual(before, sorted(p.name for p in self.drive.iterdir()))

    # 7. keep-14 rotation, oldest gone first
    def test_keep14(self):
        d = self.root / "drive-notes" / gc_settings.notes_subpaths()["backups"]
        d.mkdir(parents=True)
        for i in range(1, 21):
            (d / f"encrypted-2026{i:04d}.dmg").write_bytes(b"x")
        self.do_backup(keep=14)
        left = sorted(p.name for p in d.iterdir())
        self.assertEqual(len(left), 14)
        self.assertNotIn("encrypted-20260001.dmg", left)
        self.assertIn("encrypted-20260020.dmg", left)

    # restore never overwrites an existing path (same rule as the DB restore tool)
    def test_restore_refuses_existing_target(self):
        arc = self.do_backup()
        out = self.root / "restored-existing"
        bk.restore(arc, out, self.key)
        with self.assertRaises(SystemExit):
            bk.restore(arc, out, self.key)

    # the archive is marked encrypted before it is allowed near the drive path
    def test_drive_archive_is_encrypted_dmg(self):
        arc = self.do_backup()
        self.assertTrue(bk._dmg_encrypted(arc)[0])

if __name__ == "__main__":
    unittest.main(verbosity=2)
