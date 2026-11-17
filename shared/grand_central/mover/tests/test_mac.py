# origin: 92a9739:mover/tests/test_mac.py
"""Mac side: mover_request.py, mover_usage.py, limits.py."""
import datetime, json, os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import limits as L, mover_request as R, mover_usage as U  # noqa: E402
import gc_settings  # noqa: E402
import gsrun  # noqa: E402

def _cache_listing(root):
    base = os.path.join(root, "drive-cache")
    return sorted(os.path.join(dp, n) for dp, _d, fns in os.walk(base) for n in fns) if root else []


class Isolated(unittest.TestCase):
    """Every test gets its OWN GC_DATA_ROOT (local_first writes drive-cache/ under it), and the data root that was in effect
    before (the real one on a standalone run) must end the test with the same drive-cache file list it started with."""
    def setUp(self):
        try:
            self._real_root = gc_settings.data_root()
        except Exception:
            self._real_root = None
        self._before = _cache_listing(self._real_root)
        self._old_env = os.environ.get("GC_DATA_ROOT")
        self._own = tempfile.TemporaryDirectory()
        os.environ["GC_DATA_ROOT"] = self._own.name
        self.addCleanup(self._unisolate)

    def _unisolate(self):
        if self._old_env is None:
            os.environ.pop("GC_DATA_ROOT", None)
        else:
            os.environ["GC_DATA_ROOT"] = self._old_env
        self._own.cleanup()
        self.assertEqual(_cache_listing(self._real_root), self._before, "the test changed the real data root's drive-cache")


NOW = datetime.datetime(2026, 11, 12, 20, 0, tzinfo=datetime.timezone.utc)   # 12:00 PT


def usage(n, runtime_ms=1000, ids_modified=0, props=3, day="2026-11-12", hour=19):
    return [{"ts": "%sT%02d:%02d:00.000Z" % (day, hour, i % 60), "runtime_ms": runtime_ms, "gmail_calls": 1,
             "ids_modified": ids_modified, "drive_ops": 4, "properties_ops": props} for i in range(n)]


class Limits(unittest.TestCase):
    def test_confirmed_ceilings(self):
        self.assertEqual(L.CEILINGS["runtime_min_per_day"][0], 90)
        self.assertEqual(L.CEILINGS["runtime_min_per_run"][0], 6)
        self.assertEqual(L.CEILINGS["gmail_ops_per_day"][0], 20000)
        self.assertEqual(L.CEILINGS["properties_ops_per_day"][0], 50000)
        self.assertEqual(L.BATCHMODIFY_MAX_IDS, 1000)
        self.assertEqual(L.WARN_FRACTION, 0.5)
        self.assertIn("confirmed 2026-11-12", Path(L.__file__).read_text())


class Usage(Isolated):
    def tile(self, us):
        return U.build_tile({"usage": us}, now=NOW)

    def test_ok_when_light(self):
        t = self.tile(usage(96))
        self.assertEqual(t["status"], "OK")
        self.assertEqual(t["items"], [])
        self.assertEqual(t["pulse_job"], "mover-usage")

    def test_warn_at_50_percent_of_runtime_ceiling(self):
        t = self.tile(usage(45, runtime_ms=60000))              # exactly 45 min = 50% of 90
        self.assertEqual(t["status"], "WARN")
        t = self.tile(usage(44, runtime_ms=60000) + usage(1, runtime_ms=59999, hour=16))
        self.assertEqual(t["status"], "OK")

    def test_warn_at_50_percent_of_email_ops(self):
        self.assertEqual(self.tile(usage(2, ids_modified=5000))["status"], "WARN")      # 10,000
        self.assertEqual(self.tile(usage(2, ids_modified=4999))["status"], "OK")

    def test_warn_at_50_percent_of_properties(self):
        self.assertEqual(self.tile(usage(5, props=5000))["status"], "WARN")             # 25,000

    def test_warn_on_long_single_run(self):
        self.assertEqual(self.tile(usage(1, runtime_ms=180000))["status"], "WARN")      # 3 min = 50% of 6

    def test_only_today_counts_in_pacific_time(self):
        t = self.tile(usage(100, ids_modified=1000, day="2026-11-11") + usage(1))
        self.assertEqual(t["status"], "OK")

    def test_stale_heartbeat_warns(self):
        t = self.tile(usage(3, hour=15))                       # newest 15:02Z, now 20:00Z -> 4h
        self.assertEqual(t["status"], "WARN")
        self.assertIn("mover timer has not run for 4h", t["items"][0]["detail"])
        self.assertIn("In production", t["items"][0]["detail"])

    def test_fresh_heartbeat_ok(self):
        t2 = U.build_tile({"usage": [{"ts": "2026-11-12T19:30:00.000Z", "runtime_ms": 1000}]}, now=NOW)
        self.assertEqual(t2["status"], "OK")

    def test_no_entries_uses_mtime_only_after_an_hour(self):
        old = (NOW - datetime.timedelta(hours=2)).timestamp()
        new = (NOW - datetime.timedelta(minutes=30)).timestamp()
        self.assertEqual(U.build_tile({"usage": []}, now=NOW, result_mtime=old)["status"], "WARN")
        self.assertEqual(U.build_tile({"usage": []}, now=NOW, result_mtime=new)["status"], "OK")

    def test_ceiling_50_percent_still_warns_when_fresh(self):
        us = [{"ts": "2026-11-12T19:50:00.000Z", "runtime_ms": 45 * 60000, "ids_modified": 0, "properties_ops": 0}]
        t = U.build_tile({"usage": us}, now=NOW)
        self.assertEqual(t["status"], "WARN")
        self.assertNotIn("timer has not run", json.dumps(t))

    def test_default_paths_come_from_settings(self):
        self.assertTrue(U.tile_path().endswith("/state/status/gc-mover.json"))
        self.assertTrue(U.tile_path().startswith(gc_settings.notes_root()))
        self.assertEqual(U.mover_dir(), gc_settings.gc("mover_dir"))
        self.assertEqual(self.tile([])["desk"], gc_settings.pulse_desk())

    def test_main_writes_tile_to_temp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            res, tile = os.path.join(d, "result.json"), os.path.join(d, "tile.json")
            json.dump({"usage": usage(1)}, open(res, "w", encoding="utf-8"))
            self.assertEqual(U.main(["--result", res, "--tile", tile]), 0)
            self.assertIn(json.load(open(tile, encoding="utf-8"))["status"], ("OK", "NEEDS_REVIEW"))
            self.assertEqual(U.main(["--result", os.path.join(d, "missing.json"), "--tile", tile]), 1)
            self.assertEqual(json.load(open(tile, encoding="utf-8"))["status"], "ERROR")


class Request(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.d.name, "request.json")
        self.actions = os.path.join(self.d.name, "actions.json")
        json.dump([{"op": "archive", "ids": gsrun.ids(3)}], open(self.actions, "w", encoding="utf-8"))

    def tearDown(self):
        self.d.cleanup()

    def test_dry_run_default_writes_nothing(self):
        open(self.path, "w", encoding="utf-8").write("")
        self.assertEqual(R.main([self.actions, "--path", self.path]), 0)
        self.assertEqual(open(self.path, encoding="utf-8").read(), "")

    def test_write_in_place_keeps_inode(self):
        open(self.path, "w", encoding="utf-8").write("x" * 500)
        ino = os.stat(self.path).st_ino
        self.assertEqual(R.main([self.actions, "--path", self.path, "--write", "--request-id", "req-test-0001"]), 0)
        self.assertEqual(os.stat(self.path).st_ino, ino)
        got = json.load(open(self.path, encoding="utf-8"))
        self.assertEqual(got["request_id"], "req-test-0001")
        self.assertEqual(got["actions"][0]["op"], "archive")

    def test_never_creates_the_file(self):
        with self.assertRaises(FileNotFoundError):
            R.main([self.actions, "--path", self.path, "--write"])
        self.assertFalse(os.path.exists(self.path))

    def test_invalid_refused(self):
        json.dump([{"op": "delete", "ids": gsrun.ids(1)}], open(self.actions, "w", encoding="utf-8"))
        open(self.path, "w", encoding="utf-8").write("")
        self.assertEqual(R.main([self.actions, "--path", self.path, "--write"]), 2)
        self.assertEqual(open(self.path, encoding="utf-8").read(), "")

    def test_over_cap_refused(self):
        json.dump([{"op": "archive", "ids": gsrun.ids(5001)}], open(self.actions, "w", encoding="utf-8"))
        self.assertEqual(R.main([self.actions, "--path", self.path]), 2)




class ReadRetry(Isolated):
    def test_read_result_retries_edeadlk_then_succeeds(self):
        import errno
        from unittest import mock
        calls = {"n": 0}
        real_open = open
        def flaky(path, *a, **k):
            calls["n"] += 1
            if calls["n"] < 3:
                raise OSError(errno.EDEADLK, "Resource deadlock avoided")
            return real_open(path, *a, **k)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.json"); json.dump({"usage": []}, real_open(p, "w"))
            with mock.patch("builtins.open", flaky):
                self.assertEqual(U.read_result(p, tries=4, wait=0), {"usage": []})
            calls["n"] = -10
            p2 = os.path.join(d, "r2.json"); json.dump({"usage": []}, real_open(p2, "w"))   # no local copy of this one yet
            with mock.patch("builtins.open", flaky):
                with self.assertRaises(OSError):
                    U.read_result(p2, tries=2, wait=0)


if __name__ == "__main__":
    unittest.main()
