"""Step 1.9 dated lights. Stubs only: no Google call, no real login. Each planted bad case is asserted NOT green."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import datetime as dt, json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import status_lights as S

U = dt.timezone.utc
BEFORE = dt.datetime(2026, 11, 16, 18, 0, tzinfo=U)
AFTER = dt.datetime(2026, 11, 23, 18, 0, tzinfo=U)
iso = lambda ago, now=AFTER: (now - dt.timedelta(seconds=ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
CFG = {"dated": True}


def passf(**kw):
    d = {"gmail_error": None, "written_at": iso(60), "discover": {"threads_listed": 132}}
    d.update(kw)
    return d


class Dated(unittest.TestCase):
    def test_not_due_is_ok_and_says_so(self):
        for l in (S.login_light(CFG, BEFORE, check=lambda: self.fail("must not call"), state_path="/nonexistent/x"),
                  S.mover_light(CFG, BEFORE, run=lambda: self.fail("must not run")),
                  S.mailkey_light(CFG, None, "file not found", BEFORE)):
            self.assertEqual(l["status"], "OK"); self.assertIn("not due", l["summary"])

    def test_PLANTED_failed_preflight_is_error_and_points_to_fix(self):
        sp = tempfile.mkdtemp() + "/s.json"
        l = S.login_light(CFG, AFTER, check=lambda: (False, "getProfile did not answer"), state_path=sp)
        self.assertEqual(l["status"], "ERROR"); self.assertIn("step-1a-reauth-walkthrough.md", l["summary"])

    def test_login_checked_at_most_once_a_day(self):
        sp = tempfile.mkdtemp() + "/s.json"; calls = []
        chk = lambda: (calls.append(1) or (True, ""))
        self.assertEqual(S.login_light(CFG, AFTER, chk, sp)["status"], "OK")
        S.login_light(CFG, AFTER + dt.timedelta(minutes=10), chk, sp)
        self.assertEqual(len(calls), 1)
        S.login_light(CFG, AFTER + dt.timedelta(hours=25), chk, sp)
        self.assertEqual(len(calls), 2)

    def test_PLANTED_gmail_error_not_green(self):
        l = S.mailkey_light(CFG, passf(gmail_error="invalid_grant"), None, AFTER)
        self.assertEqual(l["status"], "ERROR"); self.assertIn("step-1a-reauth-walkthrough.md", l["summary"])

    def test_PLANTED_stale_or_missing_or_empty_pass_not_green(self):
        self.assertEqual(S.mailkey_light(CFG, passf(written_at=iso(5000)), None, AFTER)["status"], "ERROR")
        self.assertEqual(S.mailkey_light(CFG, None, "file not found", AFTER)["status"], "ERROR")
        self.assertEqual(S.mailkey_light(CFG, passf(discover={"threads_listed": 0}), None, AFTER)["status"], "NEEDS_REVIEW")

    def test_mailkey_green(self):
        self.assertEqual(S.mailkey_light(CFG, passf(), None, AFTER)["status"], "OK")

    def test_mover_verdicts(self):
        f = lambda t, rc=0: (lambda: (rc, t))
        self.assertEqual(S.mover_light(CFG, AFTER, f("VERDICT: PASS (x)\nVERDICT: PASS (y)"))["status"], "OK")
        self.assertEqual(S.mover_light(CFG, AFTER, f("VERDICT: PENDING (2 of 8 days)\nVERDICT: PASS"))["status"], "NEEDS_REVIEW")
        self.assertEqual(S.mover_light(CFG, AFTER, f("VERDICT: FAIL (gap)\nVERDICT: PASS"))["status"], "ERROR")
        self.assertEqual(S.mover_light(CFG, AFTER, f("REFUSED: result.json not found", 1))["status"], "ERROR")

    def test_wired_into_the_mailroom_call_and_writes_with_right_rhythm(self):
        d = tempfile.mkdtemp(); pf = d + "/p.json"; json.dump(passf(), open(pf, "w", encoding="utf-8"))
        cfg = {"dated": True, "status_dir": d + "/st", "pass_file": pf, "login_state": d + "/ls.json",
               "mover_cmd": []}
        wrote = {}
        def writer(path, payload=None, **kw): wrote[os.path.basename(path)] = kw
        r = S.run_lights(cfg, only=["mailroom"], now=BEFORE, writer=writer)
        self.assertTrue({"gc-login.json", "gc-mover-verdict.json", "gc-mailkey.json"} <= set(wrote))
        self.assertEqual(wrote["gc-login.json"]["stale_after_s"], 86400)
        self.assertEqual(wrote["gc-mailkey.json"]["stale_after_s"], 1200)
        self.assertTrue(all(v["status"] != "stale" for v in wrote.values()))


if __name__ == "__main__":
    unittest.main()
