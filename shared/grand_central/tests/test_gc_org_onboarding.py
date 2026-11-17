"""Phase 3 combined-check fixes: (1) gc org shows a 'likely' organization type WITH its certainty, never as unknown and never as confirmed;
(2) gc onboarding sheet without --out gives a clear usage message, not a traceback. Synthetic temp database."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import contextlib, io, json, os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_step37_pages as t37  # noqa: E402
import store_graph as sg  # noqa: E402


class T(t37.Base):
    def circle(self, certainty, who="code"):
        o = sg.thing(self.c, "organization", "Book Circle", key="organization:circle")
        sg.assert_fact(self.c, o, "org_type", "group", who, certainty, "code" if who == "code" else "answer", answer_id=self.aid if who == "owner" else None)

    def test_PLANTED_likely_type_shown_with_certainty_not_unknown_not_confirmed(self):
        self.circle("likely")
        rc, out = self.gc("org", "organization:circle")
        self.assertEqual(rc, 0)
        self.assertNotIn("type unknown", out)
        self.assertIn("group (not yet confirmed by you)", out)
        rc, out = self.gc("org", "organization:circle", "--json")
        j = json.loads(out)
        self.assertEqual((j["org_type"], j["org_type_certainty"]), ("group", "likely"))

    def test_confirmed_type_has_no_caveat_and_missing_type_is_unknown(self):
        self.example()
        rc, out = self.gc("org", "organization:acme")
        self.assertIn("(organization:acme, company)", out)
        self.assertEqual(json.loads(self.gc("org", "organization:acme", "--json")[1])["org_type_certainty"], "sure")
        sg.thing(self.c, "organization", "Bare", key="organization:bare")
        rc, out = self.gc("org", "organization:bare")
        self.assertIn("type unknown", out)

    def test_PLANTED_onboarding_sheet_without_out_is_a_usage_message(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = t37.gc.main(["--db", os.path.join(self.tmp.name, "rig.db"), "onboarding", "sheet"])
        self.assertEqual(rc, 2)
        self.assertIn("--out", err.getvalue())


if __name__ == "__main__":
    unittest.main()
