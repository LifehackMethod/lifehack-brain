"""tools/lulu_rules_check.py: rules filed under a code-signing SIGNER key. Synthetic rules only."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
import lulu_rules_check as L  # noqa: E402

GWS, CL = L.BIN + "gws", L.BIN + "claude"
SIG = "com.anthropic.claude-code:Developer ID Application: Anthropic PBC (Q6L2SF6YDW)"
SIGNERS = {CL: SIG}


def rule(path, host, **kw):
    r = {"path": path, "endpointAddr": host, "endpointPort": "443", "action": 1, "creation": "t"}
    r.update(kw)
    return r


GWS_OK = {GWS: {"rules": [rule(GWS, h) for h in sorted(L.WANT[GWS])]}}
PREFS = {}


def run(extra):
    top = dict(GWS_OK)
    top.update(extra)
    return L.judge(top, PREFS, SIGNERS)


class T(unittest.TestCase):
    def test_signer_keyed_allow_found(self):
        lines, bad = run({SIG: {"rules": [rule("/other/claude", "api.anthropic.com")]}})
        self.assertEqual(bad, [])

    def test_signer_wildcard_is_accepted(self):
        lines, bad = run({SIG: {"rules": [rule("/other/claude", "api.anthropic.com"), rule("/other/claude", "*")]}})
        self.assertEqual(bad, [])
        self.assertTrue(any("ACCEPTED: covered by signer rule" in l and "claude" in l for l in lines))

    def test_signer_wildcard_alone_is_not_enough(self):
        lines, bad = run({SIG: {"rules": [rule("/other/claude", "*")]}})
        self.assertTrue(bad)

    def test_path_keyed_still_works(self):
        lines, bad = run({CL: {"rules": [rule(CL, "api.anthropic.com")]}})
        self.assertEqual(bad, [])
        self.assertFalse(any("ACCEPTED" in l for l in lines))

    def test_path_keyed_wildcard_still_fails(self):
        lines, bad = run({CL: {"rules": [rule(CL, "api.anthropic.com"), rule(CL, "*")]}})
        self.assertTrue(bad)

    def test_disabled_signer_rule_does_not_count(self):
        lines, bad = run({SIG: {"rules": [rule("/other/claude", "api.anthropic.com", isDisabled=1)]}})
        self.assertTrue(any("api.anthropic.com" in b for b in bad))

    def test_gws_stays_path_keyed(self):
        top = {CL: {"rules": [rule(CL, "api.anthropic.com")]}, "gws-signer": {"rules": [rule(GWS, h) for h in L.WANT[GWS]]}}
        lines, bad = L.judge(top, PREFS, SIGNERS)
        self.assertTrue(any("gws" in b for b in bad))


if __name__ == "__main__":
    unittest.main()
