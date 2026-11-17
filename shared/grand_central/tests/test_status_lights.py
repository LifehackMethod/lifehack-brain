"""Light tests for status_lights.py. Synthetic data only; writes to a temp dir, never Drive.
Each planted bad case is asserted NOT green (caught)."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import datetime as dt, json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import status_lights as S
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NOW = dt.datetime(2026, 11, 16, 18, 0, 0, tzinfo=dt.timezone.utc)
iso = lambda secs_ago: (NOW - dt.timedelta(seconds=secs_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def pass_obj(**kw):
    d = {"delivered": 3, "quarantined": 0, "held_after": 0, "held_messages": [], "lost": 0, "missing_labels": [],
         "missing_exclude_labels": [], "started": True, "gmail_error": None, "scanner_error": None,
         "discover": {"threads_listed": 10}, "written_at": iso(60)}
    d.update(kw)
    return d


PROOF = ("morning read 2026-11-16 (desk): 4 new of 40 examined; used 3, sorted out by triage 1, skipped with a reason 0; "
         "flagged-as-needing-him dropped: 0; every new email accounted for")


class Lights(unittest.TestCase):
    def test_mailroom_green(self):
        self.assertEqual(S.mailroom_light(pass_obj(), None, NOW)["status"], "OK")

    def test_PLANTED_stale_pass_not_green(self):
        l = S.mailroom_light(pass_obj(written_at=iso(5000)), None, NOW)
        self.assertEqual(l["status"], "ERROR"); self.assertIn("stopped", l["summary"])

    def test_missing_pass_not_green_no_crash(self):
        self.assertEqual(S.mailroom_light(None, "file not found", NOW)["status"], "ERROR")

    def test_held_age_unknown_then_known(self):
        l = S.mailroom_light(pass_obj(held_after=2, held_messages=[{"message_id": "a"}, {"message_id": "b"}]), None, NOW)
        self.assertEqual(l["status"], "NEEDS_REVIEW"); self.assertIn("unknown", l["summary"])
        self.assertEqual(S.mailroom_light(pass_obj(held_after=2, held_oldest_age_s=20000), None, NOW)["status"], "ERROR")
        self.assertEqual(S.mailroom_light(pass_obj(held_after=2, held_oldest_age_s=600), None, NOW)["status"], "NEEDS_REVIEW")
        h = [{"message_id": "a", "held_since": iso(30000)}]
        self.assertEqual(S.mailroom_light(pass_obj(held_after=1, held_messages=h), None, NOW)["status"], "ERROR")

    def test_zero_work_not_silently_green(self):
        l = S.mailroom_light(pass_obj(delivered=0, discover={"threads_listed": 0}), None, NOW)
        self.assertEqual(l["status"], "NEEDS_REVIEW")
        l = S.mailroom_light(pass_obj(delivered=0), None, NOW)
        self.assertEqual(l["status"], "OK"); self.assertIn("nothing new", l["summary"])

    def test_signed_out_sets_75(self):
        l = S.mailroom_light(pass_obj(gmail_error="invalid_grant"), None, NOW)
        self.assertTrue(l["signed_out"])

    def test_intake(self):
        ok = {"ts": iso(100), "light": "green", "reasons": [], "refused_at_ingest": 0, "ever_ingested": 5}
        self.assertEqual(S.intake_light(ok, None, NOW)["status"], "OK")
        self.assertEqual(S.intake_light(dict(ok, light="red", reasons=["refused_at_ingest"]), None, NOW)["status"], "ERROR")
        self.assertEqual(S.intake_light(dict(ok, ever_ingested=0), None, NOW)["status"], "NEEDS_REVIEW")
        self.assertEqual(S.intake_light(None, "file not found", NOW)["status"], "ERROR")

    def test_morning_green_and_tolerates_new_fields(self):
        self.assertEqual(S.morning_light(PROOF, None, NOW)["status"], "OK")
        l = S.morning_light({"proof_line": PROOF + "; by source: email 4", "per_source": {"email": 4}}, None, NOW)
        self.assertEqual(l["status"], "OK")

    def test_PLANTED_malformed_proof_not_green(self):
        for bad in ("morning read looked fine I guess", PROOF.replace("4 new of", "four new of"),
                    PROOF.replace("every new email accounted for", "NOT ACCOUNTED: coverage:shape"),
                    PROOF.replace("used 3", "used 1"), "{not json", ""):
            self.assertNotEqual(S.morning_light(bad, None, NOW)["status"], "OK", bad)
        self.assertEqual(S.morning_light(None, "file not found", NOW)["status"], "NEEDS_REVIEW")

    def test_morning_old_day(self):
        self.assertEqual(S.morning_light(PROOF.replace("2026-11-16", "2026-11-10"), None, NOW)["status"], "ERROR")

    def test_backup(self):
        sys.path.insert(0, os.path.join(_ROOT, "tests"))
        import step3_fixture
        d = tempfile.mkdtemp()
        for sub in ("l", "s", "a"):
            os.makedirs(os.path.join(d, sub))
        for sub in ("l", "s"):
            c = step3_fixture.rw(os.path.join(d, sub, "rig-1.db")); c.execute("create table t(x)"); c.commit(); c.close()
        open(os.path.join(d, "a", "encrypted-1.dmg"), "wb").write(b"x")
        cfg = {"local_dir": d + "/l", "snapshot_dir": d + "/s", "archive_dir": d + "/a"}
        now = dt.datetime.fromtimestamp(os.path.getmtime(d + "/a/encrypted-1.dmg") + 60, dt.timezone.utc)
        self.assertEqual(S.backup_light(cfg, now)["status"], "OK")
        open(d + "/l/rig-1.db", "wb").write(b"not a database at all")      # PLANTED corrupt backup
        self.assertEqual(S.backup_light(cfg, now)["status"], "ERROR")
        self.assertEqual(S.backup_light(cfg, now + dt.timedelta(days=3))["status"], "ERROR")  # stale

    def test_run_lights_writes_through_real_writer_and_exit_codes(self):
        d = tempfile.mkdtemp()
        pf = os.path.join(d, "pass.json"); json.dump(pass_obj(written_at=iso(5000)), open(pf, "w", encoding="utf-8"))
        cfg = {"status_dir": d + "/status", "pass_file": pf}
        r = S.run_lights(cfg, only=["mailroom"], now=NOW)
        self.assertEqual(r["exit"], 0); self.assertEqual(r["written"], ["gc-mailroom"])
        tile = json.load(open(d + "/status/gc-mailroom.json", encoding="utf-8"))
        self.assertEqual((tile["status"], tile["stale_after_s"], tile["pulse_job"]), ("ERROR", 1200, "mailroom-pass"))
        json.dump(pass_obj(gmail_error="token expired"), open(pf, "w", encoding="utf-8"))
        self.assertEqual(S.run_lights(cfg, only=["mailroom"], now=NOW)["exit"], 75)

    def test_PLANTED_mailroom_stale_limit_is_twice_the_rhythm(self):
        # round-five triage: a pass file 22 minutes old gave a false ERROR. 15 minutes old: not ERROR; 25 minutes: ERROR.
        self.assertNotEqual(S.mailroom_light(pass_obj(written_at=iso(15 * 60)), None, NOW)["status"], "ERROR")
        self.assertEqual(S.mailroom_light(pass_obj(written_at=iso(25 * 60)), None, NOW)["status"], "ERROR")
        d = tempfile.mkdtemp(); pf = os.path.join(d, "p.json")
        for mins, want in ((15, "OK"), (25, "ERROR")):
            json.dump(pass_obj(written_at=iso(mins * 60)), open(pf, "w", encoding="utf-8"))
            S.run_lights({"status_dir": d + "/st", "pass_file": pf}, only=["mailroom"], now=NOW)
            tile = json.load(open(d + "/st/gc-mailroom.json", encoding="utf-8"))
            self.assertEqual((tile["status"], tile["stale_after_s"]), (want, 1200))

    def test_PLANTED_sentinel_drift(self):
        d = tempfile.mkdtemp(); os.makedirs(d + "/sentinel")
        files = {"sentinel/a.py": b"alpha", "sentinel/b.py": b"beta"}
        for k, v in files.items(): open(os.path.join(d, k), "wb").write(v)
        open(d + "/step2.manifest", "w", encoding="utf-8").write("part: sentinel/a.py <- x/a.py\npart: sentinel/b.py <- x/b.py\n")
        cfg = {"sentinel_drift": {"pinned_dir": d}}
        branch = {"x/a.py": b"alpha", "x/b.py": b"beta"}
        l = S.sentinel_drift_light(cfg, NOW, d + "/s1.json", branch.__getitem__)
        self.assertEqual(l["status"], "OK")
        branch["x/b.py"] = b"beta CHANGED"                     # PLANTED: one file changed upstream
        l = S.sentinel_drift_light(cfg, NOW, d + "/s2.json", branch.__getitem__)
        self.assertEqual(l["status"], "DRIFT"); self.assertIn("b.py", l["summary"]); self.assertNotIn("a.py", l["summary"])
        self.assertIn("refresh the mailroom's Sentinel copy at the next mailroom sitting", l["summary"])
        self.assertNotEqual(l["status"], "ERROR")
        def boom(_): raise OSError("no git")
        self.assertEqual(S.sentinel_drift_light(cfg, NOW, d + "/s3.json", boom)["status"], "NEEDS_REVIEW")  # unreadable: never ERROR


if __name__ == "__main__":
    unittest.main()
