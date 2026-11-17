#!/usr/bin/env python3
"""Tests for tools/lulu_rules_check.py: PASS must never be said for a rule that is not in force.
Run:  python3 -I -B tools/test_lulu_rules_check.py     (from the engine folder)
Each planted case runs first against a NAIVE judge (the first version: ignores disabled / expiry / pid /
LuLu's own settings) and must be wrongly PASS there; then the real judge must say NOT YET."""
import copy
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lulu_rules_check as L  # noqa: E402

GWS, CLAUDE = L.BIN + "gws", L.BIN + "claude"


def rule(host, **kw):
    r = {"endpointAddr": host, "endpointHost": "$null", "endpointPort": "443", "action": 1, "creation": "2026-11-16 12:00:00",
         "isDisabled": "$null", "expiration": "$null", "pid": "$null"}
    r.update(kw)
    return r


def good():
    return {GWS: {"rules": [rule(h) for h in sorted(L.WANT[GWS])]}, CLAUDE: {"rules": [rule("api.anthropic.com")]}}


PREFS = {"disabled": False, "passiveMode": False, "blockMode": False}


def naive_judge(top, prefs):
    """The first version: looks only at the address."""
    t = copy.deepcopy(top)
    for v in t.values():
        for r in v["rules"]:
            r["isDisabled"] = r["expiration"] = r["pid"] = "$null"
    return L.judge(t, {})


class Check(unittest.TestCase):
    def planted(self, name, top, prefs, needle):
        nl, nbad = naive_judge(top, prefs)
        self.assertEqual(nbad, [], "planted case %r: the naive judge was supposed to be fooled" % name)   # shown failing
        lines, bad = L.judge(top, prefs)
        self.assertTrue(any(needle in b for b in bad), (name, bad))

    def test_good_state_passes(self):
        self.assertEqual(L.judge(good(), PREFS)[1], [])

    def test_planted_disabled_rule(self):
        t = good(); t[CLAUDE]["rules"][0]["isDisabled"] = 1
        self.planted("disabled rule", t, PREFS, "disabled")

    def test_planted_expiring_rule(self):
        t = good(); t[GWS]["rules"][0]["expiration"] = "2026-11-16 13:00:00"
        self.planted("rule that expires", t, PREFS, "expires")

    def test_planted_temporary_rule_for_one_process(self):
        t = good(); t[GWS]["rules"][1]["pid"] = 4242
        self.planted("temporary (pid) rule", t, PREFS, "temporary")

    def test_planted_lulu_off_or_passive(self):
        nl, nbad = naive_judge(good(), {"disabled": True})
        self.assertEqual(nbad, [])   # naive ignores settings entirely
        self.assertTrue(any("switched off" in b for b in L.judge(good(), dict(PREFS, disabled=True))[1]))
        self.assertTrue(any("passive" in b for b in L.judge(good(), dict(PREFS, passiveMode=True))[1]))

    def test_wide_rule_and_missing_rule_still_caught(self):
        t = good(); t[GWS]["rules"].append(rule("*"))
        self.assertTrue(any("allow-everything" in b for b in L.judge(t, PREFS)[1]))
        t = good(); t[GWS]["rules"].pop()
        self.assertTrue(any("no lasting allow rule" in b for b in L.judge(t, PREFS)[1]))
        t = good(); t[CLAUDE]["rules"].append(rule("example.invalid"))
        self.assertTrue(any("not on the list" in b for b in L.judge(t, PREFS)[1]))

    def test_ip_with_name_in_host_field_is_accepted(self):
        t = good(); t[CLAUDE]["rules"] = [rule("160.79.104.10", endpointHost="api.anthropic.com")]
        self.assertEqual(L.judge(t, PREFS)[1], [])

    def test_a_lima_rule_is_caught(self):
        t = good(); t["/opt/homebrew/Cellar/lima/2.3.0/bin/limactl"] = {"rules": [rule("*")]}
        self.assertTrue(any("Lima" in b for b in L.judge(t, PREFS)[1]))


if __name__ == "__main__":
    unittest.main()
