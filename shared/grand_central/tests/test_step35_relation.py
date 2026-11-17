"""Phase 3 step 3.5: relation to the person. Synthetic data on temp databases; never the live rig.db.
Each planted case runs a deliberately BROKEN version first and requires the check to FAIL on it, then the real one and requires it to pass:
(1) a machine-guessed row never appears (plant: the trust filter dropped); (2) a person with no links gives an empty relation, not a guess
(plant: a default level 0 for everyone); (3) his example reads correctly: a boss who is not head of the company, on a project with him,
at an event next week that belongs to that project (plant: shared projects not looked at). Plus: nothing is stored."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import glob, os, sqlite3, sys, tempfile, unittest
from unittest import mock
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import migrate, store_graph as sg, store_levels, store_relation as sr  # noqa: E402

ASOF = "2026-11-16"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        c = self.c = sqlite3.connect(os.path.join(self.tmp.name, "rig.db"), isolation_level=None)
        for path in sorted(glob.glob(os.path.join(ROOT, "migrations", "*.sql"))):
            migrate.apply_file(c, path, int(os.path.basename(path)[:3]))
        sg.thing(c, "world", "world")
        self.t = {}
        for k in ("me", "boss", "head", "stranger", "friend"):
            self.t[k] = sg.thing(c, "person", k, key="person:" + k)
        self.aid = c.execute("INSERT INTO kg_answers(question,words,asked_by,said_on,subject_key,subject_kind,subject_name,fact_key,value,recorded_at,words_kind) "
                             "VALUES('q','his words','t','2026-11-01','person:me','person','me','x','y','2026-11-01T00:00:00Z','verbatim')").lastrowid

    def tearDown(self):
        self.c.close()
        self.tmp.cleanup()

    def his(self, a, kind, b, role=None):
        sg.add_link(self.c, a, kind, b, "owner", "sure", "answer", answer_id=self.aid)
        if role:
            self.c.execute("UPDATE kg_links SET role=? WHERE id=(SELECT max(id) FROM kg_links)", (role,))

    def rel(self, key):
        return sr.relation_to_me(self.c, key, ASOF)

    def example(self):
        c, t = self.c, self.t
        acme = self.acme = sg.thing(c, "organization", "Acme", key="organization:acme")
        sg.assert_fact(c, acme, "org_type", "company", "owner", "sure", "answer", answer_id=self.aid)
        proj = self.proj = sg.thing(c, "project", "Launch", key="project:launch")
        ev = self.ev = sg.thing(c, "event", "Launch review", key="event:calendar:x1")
        c.execute("UPDATE kg_things SET starts_at='2026-11-20T10:00:00-05:00' WHERE id=?", (ev,))
        self.his(t["me"], "member_of", acme, "engineer"); self.his(t["boss"], "member_of", acme, "VP product"); self.his(t["head"], "member_of", acme, "CEO")
        self.his(t["me"], "reports_to", t["boss"]); self.his(t["boss"], "reports_to", t["head"])
        self.his(proj, "part_of", acme); self.his(proj, "involves", t["me"]); self.his(proj, "involves", t["boss"])
        self.his(ev, "part_of", proj)
        sg.add_link(c, ev, "involves", t["me"], "code", "sure", "code")        # the invite

    # the three checks, each returns True when the rule holds
    def check_guess_never_shows(self):
        sg.assert_fact(self.c, self.t["friend"], "relationship", "his brother", "ai_guess", "guess", "legacy")
        sg.assert_fact(self.c, self.t["stranger"], "relationship", "likely a client", "code", "likely", "code")
        self.c.execute("DROP TRIGGER IF EXISTS kg_links_involves_by_code_insert")     # the lock refuses a guessed project line; drop it in this temp DB only, to plant one
        g = sg.thing(self.c, "project", "Guessed", key="project:guessed")
        self.c.execute("INSERT INTO kg_links(from_id,kind,to_id,who,certainty,source_kind,created_at) VALUES(?,?,?,?,?,?,?)", (g, "involves", self.t["me"], "ai_research", "likely", "file", "2026-11-01T00:00:00Z"))
        self.c.execute("INSERT INTO kg_links(from_id,kind,to_id,who,certainty,source_kind,created_at) VALUES(?,?,?,?,?,?,?)", (g, "involves", self.t["friend"], "ai_research", "likely", "file", "2026-11-01T00:00:00Z"))
        for k in ("friend", "stranger"):
            r = self.rel("person:" + k)
            if r["relationship"] or r["text"] or r["projects"] or not r["empty"]:
                return False
        return True

    def check_no_links_empty(self):
        r = self.rel("person:stranger")
        return (r["empty"] and r["text"] == "" and r["relationship"] is None and r["level"] is None and not (r["direct"] or r["organizations"] or r["projects"] or r["events"])
                and self.rel("person:nobody-here")["empty"] and self.rel("address:nobody@example.org")["empty"])

    def check_example(self):
        self.example()
        b = self.rel("person:boss")
        ok = (any(d["kind"] == "reports_to" and d["direction"] == "he_to_them" for d in b["direct"])
              and b["level"] == {"level": 1, "source": "chain"}
              and [(o["name"], o["their_role"]) for o in b["organizations"]] == [("Acme", "VP product")]
              and [p["name"] for p in b["projects"]] == ["Launch"]
              and [e["name"] for e in b["events"]] == ["Launch review"] and b["events"][0]["via"] == "through a shared project"
              and "his boss" in b["text"] and "one level above him" in b["text"] and "Launch" in b["text"] and "2026-11-20" in b["text"])
        h = self.rel("person:head")      # head of the company: two levels, same company, but NOT on the project
        ok = ok and h["level"] == {"level": 2, "source": "chain"} and h["projects"] == [] and h["organizations"][0]["their_role"] == "CEO"
        p = self.rel("project:launch")
        e = self.rel("event:calendar:x1")
        o = self.rel("organization:acme")
        return (ok and p["projects"][0]["via"] == "he is on it" and "Launch" in p["text"]
                and e["projects"][0]["name"] == "Launch" and "he is on it" in e["projects"][0]["via"] and e["events"][0]["via"] == "he is invited"
                and "2026-11-20" in e["text"]
                and o["direct"][0]["kind"] == "member_of" and o["direct"][0]["role"] == "engineer")


class TestRelation(Base):
    def test_guess_never_shows(self):
        full = sr.TRUSTED
        with mock.patch.object(sr, "LIVE_LINK", "l.replaced_by IS NULL AND l.true_until IS NULL"), mock.patch.object(sr, "LIVE_FACT", "f.replaced_by IS NULL AND f.true_until IS NULL"):
            self.assertFalse(self.check_guess_never_shows(), "plant not caught: the check passed with the trust filter dropped")
        self.tearDown(); self.setUp()
        self.assertTrue(self.check_guess_never_shows())
        self.assertEqual(sr.TRUSTED, full)

    def test_no_links_empty_not_a_guess(self):
        with mock.patch.object(store_levels, "levels_above_me", lambda con, key=None: (0, "chain")):
            self.assertFalse(self.check_no_links_empty(), "plant not caught: a default level for everyone passed")
        self.tearDown(); self.setUp()
        self.assertTrue(self.check_no_links_empty())

    def test_his_example(self):
        with mock.patch.object(sr, "_projects_of_person", lambda con, pid: {}):
            self.assertFalse(self.check_example(), "plant not caught: the example passed without shared projects")
        self.tearDown(); self.setUp()
        self.assertTrue(self.check_example())

    def test_nothing_is_stored(self):
        self.example()
        def snap():
            tabs = [r[0] for r in self.c.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")]
            return tabs, {t: self.c.execute('SELECT count(*) FROM "%s"' % t).fetchone()[0] for t in tabs if not t.startswith("sqlite_")}
        before = snap()
        for k in ("person:boss", "person:head", "project:launch", "event:calendar:x1", "organization:acme", "person:stranger"):
            self.rel(k)
        self.assertEqual(before, snap())
        self.assertNotIn("relation", " ".join(before[0]).replace("relationship", ""))

    def test_a_retired_or_merged_thing_is_empty(self):
        self.example()
        self.c.execute("UPDATE kg_things SET retired_at='2026-11-10T00:00:00Z' WHERE id=?", (self.t["boss"],))
        self.assertTrue(self.rel("person:boss")["empty"])


if __name__ == "__main__":
    unittest.main()
