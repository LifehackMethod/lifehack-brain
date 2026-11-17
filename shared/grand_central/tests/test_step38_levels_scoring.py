"""Phase 3 step 3.8: levels above the person as a scoring input (scorecard.py). Synthetic data, temp databases only.
Each planted case first runs a deliberately BROKEN scorer and requires the check to FAIL on it, then the real one and requires a pass:
(1) an unknown level leaves the score unchanged (plant: unknown counted as level 1); (2) his owner level changes the score by exactly the
settings weight, and changing the settings changes it and nothing else (plant: weights hard-coded in code); (3) no new weights: the only
level setting is level_points {1, 2, 3_or_more} in attention and path_a, and with it removed the scores equal the no-level scores (plant: code defaults)."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import json, os, shutil, sys, tempfile, unittest
from unittest import mock
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import step3_fixture, store_graph as sg  # noqa: E402
import scorecard as sc  # noqa: E402

NOW = 1763197200000   # 2026-11-15 09:00 UTC
D = 86400000


REAL = sc.level_points


def broken_unknown_is_one(P, level):
    return REAL(P, 1 if level is None else level)


def broken_hardcoded(P, level):
    return {1: 1.0, 2: 0.5}.get(level, 0.25 if (level or 0) >= 3 else 0.0)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.con = step3_fixture.new_db(os.path.join(self.tmp.name, "rig.db"))
        self.cfg_dir = os.path.join(self.tmp.name, "setup")
        shutil.copytree(os.path.join(HERE, "fixtures", "setup"), self.cfg_dir)
        self.aid = self.con.execute(
            "INSERT INTO kg_answers(question,words,asked_by,said_on,subject_key,subject_kind,subject_name,fact_key,value,recorded_at,words_kind) "
            "VALUES('q','his words','t','2026-11-01','person:me','person','me','x','y','2026-11-01T00:00:00Z','verbatim')").lastrowid
        self.n = 0
        sg.thing(self.con, "world", "world")
        self.me = sg.thing(self.con, "person", "me", key="person:me")

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def person(self, name, addr, level=None, boss_of_me=False):
        pid = sg.thing(self.con, "person", name, key="person:" + name)
        aid = sg.thing(self.con, "address", addr)
        sg.add_link(self.con, aid, "address_of", pid, "code", "sure", "code", "t")
        if level is not None:
            sg.assert_fact(self.con, pid, "levels_above_me", level, "owner", "sure", "answer", answer_id=self.aid)
        self.mail(addr)
        self.con.commit()
        return pid

    def mail(self, frm):
        self.n += 1
        self.con.execute("INSERT INTO messages(id,thread_id,internal_date,label_ids,from_addr,from_name,to_addrs,cc_addrs,subject,is_sent,"
                         "list_id,list_unsubscribe_present,dmarc_pass,dkim_pass,spf_pass) VALUES(?,?,?,?,?,?,?,?,?,0,NULL,0,1,1,1)",
                         ("m%d" % self.n, "t%d" % self.n, NOW - D, json.dumps(["INBOX"]), frm, "", json.dumps(["me@home.test"]), "[]", "hello"))

    def settings(self, mutate=None):
        path = os.path.join(self.cfg_dir, "leans.json")
        d = json.load(open(path, encoding="utf-8"))
        if mutate:
            mutate(d["proposed_points"])
            with open(path, "w", encoding="utf-8") as f:
                json.dump(d, f)
        return sc.Config.load(self.cfg_dir)

    def scores(self, cfg):
        mb = sc.Mailbox.load(self.con)
        out = {}
        for m in mb.msgs:
            r = sc.attention_score(mb, m["id"], cfg, NOW)
            out[m["frm"]] = (r["score"], r["reasons"])
        return out, mb

    def a_rank(self, cfg, level):
        return sc.importance_urgency({"direct_ask": True}, cfg, 1.0, False, level=level)["importance_points"]

    # the checks: True when the rule holds
    def check_unknown_neutral(self):
        self.person("noone", "noone@x.test")                       # no level, no chain: unknown
        self.person("bossy", "bossy@x.test", level=1)
        cfg = self.settings()
        base_cfg = self.settings(lambda p: (p["attention"].pop("level_points", None), p["path_a"].pop("level_points", None)))
        with_lv, _ = self.scores(cfg)
        without, _ = self.scores(base_cfg)
        return (with_lv["noone@x.test"] == without["noone@x.test"] and self.a_rank(cfg, None) == self.a_rank(base_cfg, None)
                and with_lv["bossy@x.test"][0] > without["bossy@x.test"][0])

    def check_owner_level_exact(self):
        self.person("two", "two@x.test", level=2)
        self.person("three", "three@x.test", level=5)
        self.person("one", "one@x.test", level=1)
        self.person("peer", "peer@x.test", level=0)
        cfg = self.settings()
        base_cfg = self.settings(lambda p: (p["attention"].pop("level_points", None), p["path_a"].pop("level_points", None)))
        a, _ = self.scores(cfg)
        b, _ = self.scores(base_cfg)
        want = {"one": 1.0, "two": 0.5, "three": 0.25, "peer": 0.0}
        ok = all(abs((a[k + "@x.test"][0] - b[k + "@x.test"][0]) - w) < 1e-9 for k, w in want.items())
        ok = ok and all(abs(self.a_rank(cfg, lv) - self.a_rank(base_cfg, None) - w) < 1e-9 for lv, w in ((1, 1.0), (2, 0.5), (3, 0.25), (9, 0.25), (0, 0.0)))
        cfg2 = self.settings(lambda p: p["attention"].__setitem__("level_points", {"1": 2.0, "2": 0.7, "3_or_more": 0.1}))   # changing the file changes the score, nothing else
        c, _ = self.scores(cfg2)
        ok = ok and abs((c["two@x.test"][0] - b["two@x.test"][0]) - 0.7) < 1e-9 and c["peer@x.test"] == b["peer@x.test"] \
            and abs((c["one@x.test"][0] - b["one@x.test"][0]) - 2.0) < 1e-9
        return ok

    def check_no_new_weights(self):
        pts = json.load(open(os.path.join(HERE, "fixtures", "setup", "leans.json"), encoding="utf-8"))["proposed_points"]
        lp = {"attention": pts["attention"].get("level_points"), "path_a": pts["path_a"].get("level_points")}
        shape = all(isinstance(v, dict) and set(v) == {"1", "2", "3_or_more"} for v in lp.values())
        stray = [k for sect in ("standing", "delta") for k in pts[sect] if "level" in k.lower() and not k.endswith("_at")]
        self.person("two", "two@x.test", level=2)
        base_cfg = self.settings(lambda p: (p["attention"].pop("level_points", None), p["path_a"].pop("level_points", None)))
        with_none, _ = self.scores(base_cfg)
        self.person("plain", "plain@x.test")
        base2, _ = self.scores(base_cfg)
        return shape and not stray and with_none["two@x.test"] == base2["two@x.test"] and self.a_rank(base_cfg, 2) == self.a_rank(base_cfg, None)

    def run_with(self, broken, check):
        try:
            if broken is None:
                return check()
            with mock.patch.object(sc, "level_points", broken):
                return check()
        except Exception:       # a plant that blows up is also caught
            return False
        finally:
            if broken is not None:
                self.tearDown()
                self.setUp()     # the real run starts from a clean database and the untouched settings


class Planted(Base):
    def test_1_unknown_level_changes_nothing(self):
        self.assertFalse(self.run_with(broken_unknown_is_one, self.check_unknown_neutral), "plant must be caught")
        self.assertTrue(self.check_unknown_neutral())

    def test_2_owner_level_is_exactly_the_settings_weight(self):
        self.assertFalse(self.run_with(broken_hardcoded, self.check_owner_level_exact), "plant must be caught")
        self.assertTrue(self.check_owner_level_exact())

    def test_3_no_new_weights_and_nothing_hard_coded(self):
        self.assertFalse(self.run_with(broken_hardcoded, self.check_no_new_weights), "plant must be caught")
        self.assertTrue(self.check_no_new_weights())


if __name__ == "__main__":
    unittest.main()
