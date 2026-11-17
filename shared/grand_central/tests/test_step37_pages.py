"""Phase 3 step 3.7: the four read commands (gc person / org / upcoming / due). Synthetic data on temp databases; never the live rig.db.
Each planted case runs a deliberately BROKEN version first and requires the check to FAIL on it, then the real code and requires a pass:
(1) his example (a boss who is not head of the company, on a project with him, at an event next week in that project) reads correctly
through person, org and upcoming (plant: the relation is dropped); (2) a merged-away key still opens the survivor's page (plant: keys
not followed); (3) a guessed row never shows (plant: trust filter dropped); (4) due lists a known due item (plant: last contact faked as today).
Plus: empty database -> empty answers, nothing stored, and the gc text/--json run."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import contextlib, io, json, os, sqlite3, sys, tempfile, unittest
from unittest import mock
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import importlib.util
import store, store_graph as sg, store_pages as sp, store_relation as sr  # noqa: E402
import test_step35_relation as t35  # noqa: E402

ASOF = "2026-11-16"
_spec = importlib.util.spec_from_file_location("gc_cli", os.path.join(ROOT, "gc.py"))
gc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gc)      # `gc` alone is Python's own module name, so load ours by path


class Base(t35.Base):
    def setUp(self):
        super().setUp()
        self.c.row_factory = sqlite3.Row

    def gc(self, *args):
        self.c.close()
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = gc.main(["--db", os.path.join(self.tmp.name, "rig.db"), *args])
        self.c = sqlite3.connect(os.path.join(self.tmp.name, "rig.db"), isolation_level=None)
        self.c.row_factory = sqlite3.Row
        return rc, out.getvalue()

    def check_example(self):
        self.example()
        b = sp.person_page(self.c, "person:boss", ASOF)
        ok = ("his boss" in b["relation"]["text"] and "one level above him" in b["relation"]["text"]
              and [o["name"] for o in b["organizations"]] == ["Acme"] and b["organizations"][0]["role"] == "VP product"
              and [r["name"] for r in b["reports_to"]] == ["head"] and [p["name"] for p in b["projects"]] == ["Launch"]
              and [e["name"] for e in b["upcoming_events"]] == ["Launch review"])
        ok = ok and [e["name"] for e in b["upcoming_events"]] == ["Launch review"] and b["upcoming_events"][0]["via"] == "through project Launch"
        o = sp.org_chart(self.c, "organization:acme", ASOF)
        ok = ok and o["org_type"] == "company" and {m["name"]: m["role"] for m in o["members"]} == {"me": "engineer", "boss": "VP product", "head": "CEO"}
        ok = ok and {(l["person_name"], l["boss_name"]) for l in o["reporting_lines"]} == {("me", "boss"), ("boss", "head")}
        ok = ok and [p["name"] for p in o["projects"]] == ["Launch"]
        u = sp.upcoming(self.c, ASOF, 7)
        e = u["events"][0] if len(u["events"]) == 1 else {}
        boss = [p for p in e.get("people", []) if p["key"] == "person:boss"]
        ok = ok and e.get("name") == "Launch review" and [p["name"] for p in e["projects"]] == ["Launch"] and len(boss) == 1
        ok = ok and "his boss" in (boss[0]["relation"] or "") and boss[0]["via"] == "through project Launch" and "he is on it" in (e["relation"] or "")
        ok = ok and sp.upcoming(self.c, "2026-12-01", 7)["events"] == []        # outside the window: not listed
        return ok

    def check_merged_key_opens_survivor(self):
        self.example()
        self.c.row_factory = None
        old = sg.thing(self.c, "person", "Bossy", key="person:bossy")
        sg.merge_things(self.c, "person:bossy", "person:boss", "same person", "owner-one", "2026-11-10")
        self.c.row_factory = sqlite3.Row
        p = sp.person_page(self.c, "person:bossy", ASOF)
        return p is not None and p["key"] == "person:boss" and p["asked_as"] == "person:bossy" and sp.person_page(self.c, "person:boss", ASOF)["key"] == "person:boss"

    def check_guess_never_shows(self):
        self.example()
        sg.assert_fact(self.c, self.t["friend"], "relationship", "his brother", "ai_guess", "guess", "legacy")
        sg.assert_fact(self.c, self.t["friend"], "note", "likes jazz", "code", "likely", "code")
        sg.assert_fact(self.c, self.t["friend"], "note", "plays chess", "owner", "sure", "answer", answer_id=self.aid)
        p = sp.person_page(self.c, "person:friend", ASOF)
        vals = [f["value"] for f in p["facts"]]
        return vals == ["plays chess"] and p["relation"]["relationship"] is None

    def keep_setup(self):
        self.example()
        self.c.execute("INSERT OR IGNORE INTO kg_fact_keys(key,value_list,subject_kinds,note) VALUES('keep_in_touch_days',NULL,'person','test')")
        ad = sg.thing(self.c, "address", "boss@example.test")
        sg.add_link(self.c, ad, "address_of", self.t["boss"], "owner", "sure", "answer", answer_id=self.aid)
        ms = lambda d: int(__import__("datetime").datetime.fromisoformat(d + "T12:00:00+00:00").timestamp() * 1000)
        for i, (frm, sent, d) in enumerate((("boss@example.test", 0, "2026-09-01"), ("me@example.test", 1, "2026-09-02"))):
            self.c.execute("INSERT INTO messages(id,thread_id,internal_date,from_addr,to_addrs,is_sent) VALUES(?,?,?,?,?,?)",
                           ("m%d" % i, "t1", ms(d), frm, json.dumps(["boss@example.test" if sent else "me@example.test"]), sent))
        sg.assert_fact(self.c, self.t["boss"], "keep_in_touch_days", "30", "owner", "sure", "answer", answer_id=self.aid)

    def check_due(self):
        self.keep_setup()
        d = sp.due(self.c, ASOF)["due"]
        return len(d) == 1 and d[0]["key"] == "person:boss" and d[0]["days_since"] == 75 and d[0]["overdue_by"] == 45 and d[0]["last_contact"] == "2026-09-02"


class TestPages(Base):
    def planted(self, check, patches):
        with contextlib.ExitStack() as st:
            for p in patches:
                st.enter_context(p)
            self.assertFalse(check(), "plant not caught")
        self.tearDown(); self.setUp()
        self.assertTrue(check())

    def test_his_example(self):
        empty = {"key": "x", "kind": None, "name": None, "empty": True, "text": "", "relationship": None, "direct": [], "level": None,
                 "organizations": [], "projects": [], "events": [], "events_total": 0}
        self.planted(self.check_example, [mock.patch.object(sr, "relation_to_me", lambda con, key, asof=None: dict(empty, key=key))])

    def test_merged_key(self):
        self.planted(self.check_merged_key_opens_survivor, [mock.patch.object(sg, "resolve_key", lambda con, k: k)])

    def test_guess_never_shows(self):
        self.planted(self.check_guess_never_shows, [mock.patch.object(sr, "LIVE_LINK", "l.replaced_by IS NULL AND l.true_until IS NULL"),
                                                    mock.patch.object(sr, "LIVE_FACT", "f.replaced_by IS NULL AND f.true_until IS NULL")])

    def test_due(self):
        self.planted(self.check_due, [mock.patch.object(sp, "last_contact", lambda con, pid: 1900000000000)])

    def test_due_unknown_contact_is_unknown_and_not_set_is_absent(self):
        self.keep_setup()
        self.c.execute("DELETE FROM messages")
        d = sp.due(self.c, ASOF)["due"]
        self.assertEqual((d[0]["last_contact"], d[0]["days_since"]), (None, None))      # unknown stays unknown
        self.c.execute("UPDATE kg_facts SET value='9999' WHERE fact_key='keep_in_touch_days'")
        self.assertEqual(len(sp.due(self.c, ASOF)["due"]), 1)                           # still no contact on record: unknown, listed as unknown
        self.assertEqual(sp.due(self.c, ASOF)["due"][0]["days_since"], None)

    def test_empty_database(self):
        self.assertEqual(sp.upcoming(self.c, ASOF)["events"], [])
        self.assertEqual(sp.due(self.c, ASOF)["due"], [])
        self.assertIsNone(sp.person_page(self.c, "person:nobody", ASOF))
        self.assertIsNone(sp.org_chart(self.c, "organization:nobody", ASOF))
        for cmd in ("upcoming", "due"):
            rc, out = self.gc(cmd, "--json")
            self.assertEqual(rc, 0)
        rc, out = self.gc("person", "person:nobody")
        self.assertEqual(rc, 1)
        self.assertIn("unknown", out)

    def test_retired_is_absent(self):
        self.example()
        self.c.execute("UPDATE kg_things SET retired_at='2026-11-10T00:00:00Z' WHERE id=?", (self.t["boss"],))
        self.assertIsNone(sp.person_page(self.c, "person:boss", ASOF))
        self.assertNotIn("person:boss", [m["key"] for m in sp.org_chart(self.c, "organization:acme", ASOF)["members"]])

    def test_gc_commands_run_and_store_nothing(self):
        self.example()
        before = {t: self.c.execute('SELECT count(*) FROM "%s"' % t).fetchone()[0] for (t,) in self.c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        for args in (("person", "person:boss"), ("org", "organization:acme"), ("upcoming", "--start", "2026-11-16"), ("due",)):
            for j in ([], ["--json"]):
                rc, out = self.gc(*args, *j)
                self.assertEqual(rc, 0, args)
                if j:
                    json.loads(out)
        rc, out = self.gc("person", "person:boss")
        self.assertIn("his boss", out)
        after = {t: self.c.execute('SELECT count(*) FROM "%s"' % t).fetchone()[0] for t in before}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
