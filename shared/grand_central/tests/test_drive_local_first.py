"""Drive reads in the scheduled paths go through a local working copy (local_first.py).
Why: Google Drive for desktop offloads files; a launchd job cannot fetch them, so open() fails with errno 11 (EDEADLK,
"Resource deadlock avoided"). The 2026-11-17 morning job failed 3 times on the previous picture; mover-usage failed the same
way since 11-14. Every case is planted against the real call site (morning.previous_picture, synthesize.load_life_map,
store_diary.index_entry, mover_usage.read_result, status_lights.backup_light, morning.midnight_entry) with a Drive file whose
open() raises OSError(EDEADLK). SCRATCH ONLY: a tmp notes folder, a tmp data folder; nothing real is opened.
  1. EDEADLK on Drive + a local copy        -> the read succeeds from the local copy
  2. EDEADLK on Drive + NO local copy       -> a loud error naming BOTH paths (never a silent empty picture)
  3. a newer Drive file                     -> Drive is preferred (and the local copy is refreshed from it)
  4. a job write                            -> the local copy is written too (the newest truth)
  plus: a truly missing file stays 'missing' (life map -> []), the mover result, the diary index, the snapshot light."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import builtins, datetime as dt, errno, json, os, sqlite3, sys, tempfile, time, unittest
from unittest import mock
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "mover"))
import gc_settings  # noqa: E402
import morning, synthesize, store_diary, status_lights, local_first  # noqa: E402

DESK = "desk-a"
PICTURE = "# Write-up\n\n## Picture\n- the kettle is on\n- the car is blue\n\n## Next\nnothing\n"
NEW_PICTURE = "# Write-up\n\n## Picture\n- he edited this one by hand\n\n## Next\nnothing\n"
_real_open = builtins.open


def cache_of(notes, drive_path):
    """The contract: local copies live under <data_root>/drive-cache/ mirroring the path relative to the notes folder."""
    return os.path.join(gc_settings.data_root(), "drive-cache", os.path.relpath(drive_path, notes))


def deadlock_on(*paths):
    """A builtins.open that raises EDEADLK for these exact Drive paths (the offloaded file) and works for everything else."""
    bad = set(os.path.abspath(p) for p in paths)

    def fake(file, *a, **k):
        if isinstance(file, (str, bytes, os.PathLike)) and os.path.abspath(os.fsdecode(file)) in bad:
            raise OSError(errno.EDEADLK, "Resource deadlock avoided", os.fsdecode(file))
        return _real_open(file, *a, **k)
    return mock.patch("builtins.open", fake)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.notes = os.path.join(self.tmp.name, "drive-notes")
        self.rec = morning.records_context_dir(self.notes, DESK)
        os.makedirs(self.rec)
        p = mock.patch("local_first.time.sleep")      # the Drive-busy retries must not slow the tests
        self.sleeps = p.start()
        self.addCleanup(p.stop)
        import local_first
        local_first.take_notes()
        self.old_env = os.environ.get("AGE_NOTES_ROOT")
        os.environ["AGE_NOTES_ROOT"] = self.notes
        self.addCleanup(self._restore)

    def _restore(self):
        if self.old_env is None:
            os.environ.pop("AGE_NOTES_ROOT", None)
        else:
            os.environ["AGE_NOTES_ROOT"] = self.old_env
        self.tmp.cleanup()
        cache = os.path.join(gc_settings.data_root(), "drive-cache")
        self.assertIn("gc-test-data-", cache, "refusing to touch a drive-cache that is not under the gc-test-data- temp root: " + cache)
        _sh.rmtree(cache, ignore_errors=True)

    def put(self, path, text, mtime=None):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with _real_open(path, "w", encoding="utf-8") as f:
            f.write(text)
        if mtime:
            os.utime(path, (mtime, mtime))
        return path


class PreviousPicture(Base):
    def drive_file(self):
        return self.put(os.path.join(self.rec, "2026-11-16-%s.md" % DESK), PICTURE, time.time() - 3600)

    def test_1_deadlock_with_local_copy_reads_local(self):
        p = self.drive_file()
        self.put(cache_of(self.notes, p), PICTURE)                      # the local working copy the last run left
        with deadlock_on(p):
            base, latest = morning.previous_picture(self.rec, DESK)
        self.assertEqual(latest, "2026-11-16-%s.md" % DESK)
        self.assertIn("- the kettle is on", base)

    def test_2_deadlock_without_local_copy_is_loud_and_names_both_paths(self):
        p = self.drive_file()
        with deadlock_on(p):
            with self.assertRaises(Exception) as cm:
                morning.previous_picture(self.rec, DESK)
        msg = str(cm.exception)
        self.assertIn(p, msg)
        self.assertIn(cache_of(self.notes, p), msg)

    def test_3_newer_drive_file_is_preferred_and_refreshes_the_copy(self):
        p = self.drive_file()
        c = self.put(cache_of(self.notes, p), PICTURE, time.time() - 7200)   # older than the Drive file
        self.put(p, NEW_PICTURE)                                             # he edited it: Drive is newer now
        base, _ = morning.previous_picture(self.rec, DESK)
        self.assertIn("he edited this one by hand", base)
        self.assertNotIn("kettle", base)
        with _real_open(c, encoding="utf-8") as f:
            self.assertEqual(f.read(), NEW_PICTURE)

    def test_3b_newer_drive_file_but_unreadable_falls_back_to_local(self):
        p = self.drive_file()
        self.put(cache_of(self.notes, p), PICTURE, time.time() - 7200)
        os.utime(p, None)
        with deadlock_on(p):
            base, _ = morning.previous_picture(self.rec, DESK)
        self.assertIn("kettle", base)

    def test_no_picture_at_all_still_means_none(self):
        self.assertEqual(morning.previous_picture(self.rec, DESK), (None, None))

    def test_4_a_write_refreshes_the_local_copy(self):
        diary = os.path.join(self.notes, "desks", DESK, "diary")
        staged = self.put(os.path.join(self.rec, "2026-11-15-%s.md" % DESK), PICTURE)
        res = morning.midnight_entry("2026-11-15", DESK, [staged], diary, "tree", os.path.join(self.tmp.name, "forms"))
        self.assertEqual(res["status"], "written")
        c = cache_of(self.notes, res["path"])
        self.assertTrue(os.path.isfile(c), "the diary entry was written to Drive but not to the local copy")
        with _real_open(res["path"], encoding="utf-8") as a, _real_open(c, encoding="utf-8") as b:
            self.assertEqual(a.read(), b.read())

    def test_4b_the_morning_picture_write_helper_writes_both(self):
        p = os.path.join(self.rec, "2026-11-17-%s.md" % DESK)
        morning._excl_write_drive(p, PICTURE)
        with _real_open(cache_of(self.notes, p), encoding="utf-8") as f:
            self.assertEqual(f.read(), PICTURE)
        with deadlock_on(p):                       # and the next morning can still read it when Drive offloads it
            base, latest = morning.previous_picture(self.rec, DESK)
        self.assertIn("kettle", base)


class Stale(Base):
    def test_newer_drive_unreadable_returns_local_with_a_visible_stale_note_after_retries(self):
        p = self.put(os.path.join(self.rec, "x.md"), "drive\n")
        self.put(cache_of(self.notes, p), "local\n", time.time() - 7200)
        os.utime(p, None)
        with deadlock_on(p):
            data, stale = local_first.read_ex(p)
        self.assertEqual(data, b"local\n")
        self.assertIn("older local copy", stale)
        self.assertEqual(self.sleeps.call_count, 2, "3 tries = 2 backoffs")
        self.assertEqual([n["path"] for n in local_first.take_notes()], [p])
        self.assertEqual(local_first.take_notes(), [])

    def test_fresh_local_is_not_stale(self):
        p = self.put(os.path.join(self.rec, "x.md"), "drive\n", time.time() - 3600)
        self.put(cache_of(self.notes, p), "local\n")
        self.assertEqual(local_first.read_ex(p), (b"local\n", None))

    def test_life_map_stale_is_recorded_for_the_caller(self):
        p = self.put(os.path.join(self.notes, "desks", DESK, "life-map.md"), LifeMap.TEXT)
        self.put(cache_of(self.notes, p), LifeMap.TEXT, time.time() - 7200)
        os.utime(p, None)
        with deadlock_on(p):
            self.assertEqual(len(synthesize.load_life_map(p)), 2)
        self.assertEqual([n["path"] for n in local_first.take_notes()], [p])

    def test_listing_uses_drive_only_when_drive_lists(self):
        a = self.put(os.path.join(self.rec, "2026-11-15-%s.md" % DESK), PICTURE, time.time() - 7200)
        b = self.put(os.path.join(self.rec, "2026-11-16-%s.md" % DESK), PICTURE, time.time() - 3600)
        self.put(cache_of(self.notes, a), PICTURE)
        self.put(cache_of(self.notes, b), PICTURE)
        os.remove(b)                                       # deleted on Drive; its cached copy must not come back as the latest
        base, latest = morning.previous_picture(self.rec, DESK)
        self.assertEqual(latest, "2026-11-15-%s.md" % DESK)
        self.assertEqual(local_first.take_notes(), [])

    def test_listing_falls_back_to_the_mirror_only_when_the_drive_listing_fails_and_says_so(self):
        a = self.put(os.path.join(self.rec, "2026-11-15-%s.md" % DESK), PICTURE)
        self.put(cache_of(self.notes, a), PICTURE)
        real = os.listdir
        def bad(path="."):
            if os.path.abspath(path) == os.path.abspath(self.rec):
                raise OSError(errno.EDEADLK, "Resource deadlock avoided", path)
            return real(path)
        with mock.patch("os.listdir", bad):
            self.assertEqual(local_first.list_names(self.rec), ["2026-11-15-%s.md" % DESK])
        self.assertEqual(len(local_first.take_notes()), 1)

    def test_listing_fails_with_no_mirror_is_loud(self):
        def bad(path="."):
            raise OSError(errno.EDEADLK, "Resource deadlock avoided", path)
        with mock.patch("os.listdir", bad):
            with self.assertRaises(local_first.DriveReadError):
                local_first.list_names(self.rec)


class HandRunLifeMap(Base):
    def test_hand_run_does_not_swallow_a_life_map_that_cannot_be_read(self):
        p = self.put(os.path.join(self.tmp.name, "lm", "life-map.md"), LifeMap.TEXT)    # under no notes root: cache lives under other/
        drop = os.path.join(self.tmp.name, "drop"); os.makedirs(drop)
        with deadlock_on(p):
            with self.assertRaises(local_first.DriveReadError):
                morning.hand_run(["--dry-run", "--notes-root", self.notes, "--desk", DESK, "--drop", drop, "--db",
                                  os.path.join(self.tmp.name, "no.db"), "--life-map", p], out=lambda m: None)

    def test_a_truly_missing_life_map_still_runs_without_it(self):
        drop = os.path.join(self.tmp.name, "drop"); os.makedirs(drop)
        lines = []
        morning.hand_run(["--dry-run", "--notes-root", self.notes, "--desk", DESK, "--drop", drop, "--db",
                          os.path.join(self.tmp.name, "no.db"), "--life-map", os.path.join(self.tmp.name, "absent.md")], out=lines.append)
        self.assertTrue(any("MISSING, said so in the prompt" in ln for ln in lines))


class LifeMap(Base):
    TEXT = "## 2027 Win\nBe well.\n\n## Weekly Win\nSleep.\n"

    def test_1_deadlock_with_local_copy(self):
        p = self.put(os.path.join(self.notes, "desks", DESK, "life-map.md"), self.TEXT, time.time() - 3600)
        self.put(cache_of(self.notes, p), self.TEXT)
        with deadlock_on(p):
            got = synthesize.load_life_map(p)
        self.assertEqual(len(got), 2)

    def test_2_deadlock_without_local_copy_is_loud_not_empty(self):
        p = self.put(os.path.join(self.notes, "desks", DESK, "life-map.md"), self.TEXT)
        with deadlock_on(p):
            with self.assertRaises(Exception) as cm:
                synthesize.load_life_map(p)
        self.assertIn(p, str(cm.exception))
        self.assertIn(cache_of(self.notes, p), str(cm.exception))

    def test_a_truly_missing_life_map_still_continues_without_it(self):
        self.assertEqual(synthesize.load_life_map(os.path.join(self.notes, "absent.md")), [])


class DiaryIndex(Base):
    def test_deadlock_with_local_copy_indexes_from_local(self):
        entry = self.put(os.path.join(self.notes, "desks", DESK, "diary", "2026", "11", "15.md"),
                         "---\nconfidence: low\n---\n# entry\n", time.time() - 3600)
        self.put(cache_of(self.notes, entry), "---\nconfidence: low\n---\n# entry\n")
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE diary_index(id INTEGER PRIMARY KEY, diary TEXT, date TEXT, keys_mentioned TEXT, staged_ids TEXT, "
                    "entry_path TEXT, confidence TEXT, indexed_at TEXT)")
        with deadlock_on(entry):
            self.assertEqual(store_diary.index_entry(con, "Main-Diary", entry, self.notes), "added")

    def test_deadlock_without_local_copy_is_loud(self):
        entry = self.put(os.path.join(self.notes, "desks", DESK, "diary", "2026", "11", "15.md"), "# entry\n")
        con = sqlite3.connect(":memory:")
        with deadlock_on(entry):
            with self.assertRaises(Exception) as cm:
                store_diary.index_entry(con, "Main-Diary", entry, self.notes)
        self.assertIn(entry, str(cm.exception))


class MoverResult(Base):
    RESULT = {"usage": [{"ts": "2026-11-17T01:00:00Z", "runtime_ms": 1000}]}

    def setUp(self):
        super().setUp()
        import mover_usage
        self.mu = mover_usage
        self.mdir = os.path.join(self.tmp.name, "mover-drive")
        self.res = self.put(os.path.join(self.mdir, "result.json"), json.dumps(self.RESULT), time.time() - 3600)
        patcher = mock.patch.object(gc_settings, "gc", lambda k: self.mdir if k == "mover_dir" else {}[k])
        patcher.start()
        self.addCleanup(patcher.stop)

    def local(self):
        return os.path.join(gc_settings.data_root(), "drive-cache", "mover", "result.json")

    def test_1_deadlock_with_local_copy(self):
        self.put(self.local(), json.dumps(self.RESULT))
        with deadlock_on(self.res), mock.patch("time.sleep"):
            self.assertEqual(self.mu.read_result(self.res), self.RESULT)

    def test_2_deadlock_without_local_copy_is_loud(self):
        with deadlock_on(self.res), mock.patch("time.sleep"):
            with self.assertRaises(Exception) as cm:
                self.mu.read_result(self.res)
        self.assertIn(self.res, str(cm.exception))
        self.assertIn(self.local(), str(cm.exception))

    def test_3_a_successful_drive_read_leaves_a_local_copy_for_the_next_run(self):
        self.assertEqual(self.mu.read_result(self.res), self.RESULT)
        self.assertTrue(os.path.isfile(self.local()))
        with deadlock_on(self.res), mock.patch("time.sleep"):
            self.assertEqual(self.mu.read_result(self.res), self.RESULT)


class SnapshotLight(Base):
    def test_the_snapshot_integrity_check_is_given_a_local_file(self):
        snap = os.path.join(self.notes, "state", "snapshots")
        d = os.path.join(self.notes, "state", "snapshots", "rig-20261116.db")
        os.makedirs(snap)
        con = sqlite3.connect(d); con.execute("CREATE TABLE t(x)"); con.commit(); con.close()
        seen = []
        cfg = {"snapshot_dir": snap}
        status_lights.backup_light(cfg, dt.datetime.now(dt.timezone.utc), db_check=lambda p: seen.append(p) or True)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0], cache_of(self.notes, d), "the integrity check opened the Drive file itself")


class SnapshotLightDeadlock(Base):
    def _snap(self):
        snap = os.path.join(self.notes, "state", "snapshots")
        d = os.path.join(snap, "rig-20261116.db")
        os.makedirs(snap)
        con = sqlite3.connect(d); con.execute("CREATE TABLE t(x)"); con.commit(); con.close()
        return snap, d

    def test_edeadlock_on_the_drive_snapshot_with_a_local_copy_still_checks(self):
        snap, d = self._snap()
        self.put(cache_of(self.notes, d), "copy")
        os.utime(d, (time.time() - 3600,) * 2)
        seen = []
        with deadlock_on(d):
            light = status_lights.backup_light({"snapshot_dir": snap}, dt.datetime.now(dt.timezone.utc), db_check=lambda p: seen.append(p) or True)
        self.assertEqual(seen, [cache_of(self.notes, d)])
        self.assertNotIn("unreadable", light["summary"])

    def test_edeadlock_on_the_drive_snapshot_with_no_local_copy_is_a_loud_error_light(self):
        snap, d = self._snap()
        with deadlock_on(d):
            light = status_lights.backup_light({"snapshot_dir": snap}, dt.datetime.now(dt.timezone.utc), db_check=lambda p: True)
        self.assertEqual(light["status"], "ERROR")
        self.assertIn("snapshot unreadable", light["summary"])
        self.assertIn(d, light["summary"])


class MidnightEntries(Base):
    """midnight_entries is the writer the live midnight job calls."""
    TABLE = {"main_diary": "Main-Diary", "diary_pattern": "{desk}-Diary", "parts_to_desk": {}}

    def test_each_written_entry_also_gets_its_local_copy(self):
        staged = self.put(os.path.join(self.rec, "2026-11-15-%s.md" % DESK), PICTURE)
        diary = os.path.join(self.notes, "desks", DESK, "diary")
        res = morning.midnight_entries("2026-11-15", [staged], {"Main-Diary": diary}, self.TABLE, "tree", os.path.join(self.tmp.name, "forms"), con=None)
        self.assertEqual(res["Main-Diary"]["status"], "written")
        c = cache_of(self.notes, res["Main-Diary"]["path"])
        with _real_open(res["Main-Diary"]["path"], encoding="utf-8") as a, _real_open(c, encoding="utf-8") as b:
            self.assertEqual(a.read(), b.read())


class IndexRefresh(Base):
    def test_one_unreadable_entry_with_no_local_copy_is_skipped_loudly_and_the_rest_is_indexed(self):
        d = os.path.join(self.notes, "desks", DESK, "diary", "2026", "11")
        good = self.put(os.path.join(d, "14.md"), "---\nconfidence: low\n---\n# a\n")
        bad = self.put(os.path.join(d, "15.md"), "# b\n")
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE diary_index(id INTEGER PRIMARY KEY, diary TEXT, date TEXT, keys_mentioned TEXT, staged_ids TEXT, "
                    "entry_path TEXT, confidence TEXT, indexed_at TEXT)")
        with deadlock_on(bad):
            res = store_diary.refresh_index(con, "Main-Diary", os.path.join(self.notes, "desks", DESK, "diary"), self.notes)
        self.assertEqual(res["added"], 1)
        self.assertEqual(res["unreadable"], [bad])
        self.assertEqual(con.execute("SELECT COUNT(*) FROM diary_index").fetchone()[0], 1)


class MoverStale(Base):
    def test_a_stale_result_is_flagged_on_the_tile_and_not_paired_with_drives_newer_mtime(self):
        import mover_usage
        mdir = os.path.join(self.tmp.name, "mover-drive")
        res = self.put(os.path.join(mdir, "result.json"), json.dumps({"usage": []}))      # Drive: new mtime
        local = os.path.join(gc_settings.data_root(), "drive-cache", "mover", "result.json")
        self.put(local, json.dumps({"usage": []}), time.time() - 86400)                    # local copy: a day old
        tile = os.path.join(self.tmp.name, "tile.json")
        with mock.patch.object(gc_settings, "gc", lambda k: mdir), deadlock_on(res):
            self.assertEqual(mover_usage.main(["--result", res, "--tile", tile]), 0)
        t = json.load(_real_open(tile, encoding="utf-8"))
        self.assertIn("STALE", t["summary"])
        self.assertIn("result.json is stale", json.dumps(t))
        self.assertIn("Mover timer stale", json.dumps(t))    # the copy is a day old: judged by the copy's age, not Drive's mtime
        self.assertEqual(self.sleeps.call_count, 3, "the 4-try retry runs even with a local copy")


if __name__ == "__main__":
    unittest.main()
