"""The proposal and week doors: store.proposals / answer_proposal / expiry_questions / urgent_items / week_digest and gc proposals|answer|urgent|week.
Temp DBs only; never the live rig.db."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import contextlib, importlib.util, io, json, os, sqlite3, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import migrate, store, store_items, store_meaning as sm  # noqa: E402

spec = importlib.util.spec_from_file_location("rig_gc_doors", os.path.join(ROOT, "gc.py"))
rig_gc = importlib.util.module_from_spec(spec); spec.loader.exec_module(rig_gc)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.tmp.name, "rig.db")
        c = sqlite3.connect(self.p, isolation_level=None)
        for n, path in migrate.list_migrations():
            migrate.apply_file(c, path, n)
        c.close()
        store.set_path(self.p)
        self._old = os.environ.get("AGE_NOW")
        os.environ["AGE_NOW"] = "2026-11-12T09:00:00+00:00"
        import clock as _clock  # 4P.0b: the feeds gate must see a connected feed in these CLI-read tests
        _st = _clock.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        for _src in ("gmail", "calendar", "tasks"):
            store.set_source_state(_src, _st, 0)
        self.seed()

    def tearDown(self):
        store.set_path(None)
        if self._old is None:
            os.environ.pop("AGE_NOW", None)
        else:
            os.environ["AGE_NOW"] = self._old
        self.tmp.cleanup()

    def x(self, sql, a=()):
        c = sqlite3.connect(self.p)
        try:
            r = c.execute(sql, a).fetchall(); c.commit(); return r
        finally:
            c.close()

    def item(self, sid, kind="email", due=None, occ="2026-11-10T10:00:00Z", status="inbox", title=None):
        return store_items.upsert_item("t", sid, kind, title=title or sid, occurred_at=occ, due_at=due, status=status)[0]

    def gc(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = rig_gc.main(["--db", self.p] + list(argv))
        return rc, out.getvalue(), err.getvalue()

    def model(self, fn, *a, **k):
        """run a store_meaning / store_graph writer on its own connection (pins and projects live in the one model)"""
        c = sqlite3.connect(self.p, isolation_level=None)
        try:
            c.execute("BEGIN"); r = fn(c, *a, **k); c.execute("COMMIT"); return r
        finally:
            c.close()

    def project(self, name, due, items=()):
        import store_graph as sg
        def go(c):
            pid = sg.thing(c, "project", name)
            sg.assert_fact(c, pid, "date_window", "2026-10-01..%s" % due, "code", "likely", "code")
            for i in items:
                sg.add_link(c, sg.thing(c, "item", str(i)), "part_of", pid, "code", "likely", "code")
            return pid
        return self.model(go)

    def seed(self):
        self.soon = self.item("soon", due="2026-11-14")
        self.far = self.item("far", due="2027-03-01")
        self.nodate = self.item("nodate")
        self.pinned = self.item("pinned")
        self.quiet = self.item("quiet", due="2026-11-13")
        self.done = self.item("done", due="2026-11-12", status="completed")
        self.old = self.item("old", occ="2026-09-01T00:00:00Z")
        self.stale_task = self.item("stale", kind="task", due="2026-10-01", status="needsAction", occ="2026-09-20T00:00:00Z")
        self.model(sm.set_override, "item", self.pinned, "pin", "why", "2026-12-01")
        self.model(sm.set_override, "item", self.quiet, "quiet-until", "why", "2026-12-01", until_on="2026-11-20")
        import store_graph as sg
        person = self.model(lambda c: sg.thing(c, "person", "Old Pin Person"))
        self.model(sm.set_override, "person", person, "pin", "old pin", "2026-11-01")
        self.q1 = self.x("INSERT INTO queue(kind,subject_ref,question,proposed_answer,created_at) VALUES('apply-label','item:1','Label it?','Example-Label','x') RETURNING id")[0][0]
        self.q2 = self.x("INSERT INTO queue(kind,subject_ref,question,created_at) VALUES('who-is-this','address:a@b.example','Who?','x') RETURNING id")[0][0]


class Proposals(Base):
    def test_list_filter_and_limit(self):
        self.assertEqual([p["id"] for p in store.proposals()], [self.q1, self.q2])
        self.assertEqual([p["id"] for p in store.proposals(kind="who-is-this")], [self.q2])
        self.assertEqual(len(store.proposals(limit=1)), 1)
        self.assertEqual(store.proposals(status="answered"), [])

    def test_answer_logs_and_closes(self):
        r = store.answer_proposal(self.q1, "yes", decided_by="owner-one")
        self.assertIs(r["accepted"], True)
        self.assertEqual(r["proposed_answer"], "Example-Label")
        self.assertEqual([p["id"] for p in store.proposals()], [self.q2])
        row = store.proposals(status="answered")[0]
        self.assertEqual((row["answer"], row["status"]), ("yes", "answered"))
        kg = self.x("SELECT words, asked_by, queue_id FROM kg_answers WHERE id=?", (r["answer_id"],))[0]  # the model's answer path
        self.assertEqual((kg[0], kg[2]), ("yes", self.q1))
        self.assertIn("owner-one", kg[1])
        self.assertIsNone(r["answer_log_id"])  # the old answer_log is no longer written (2.4 reader 1)

    def test_free_text_and_no(self):
        self.assertIsNone(store.answer_proposal(self.q2, "my accountant")["accepted"])
        self.assertIs(store.answer_proposal(self.q1, "No")["accepted"], False)

    def test_refusals(self):
        store.answer_proposal(self.q1, "yes")
        for bad in ((self.q1, "yes"), (9999, "yes"), (self.q2, "  ")):
            with self.assertRaises(ValueError):
                store.answer_proposal(*bad)


class Expiry(Base):
    def test_questions_not_actions(self):
        before = self.x("SELECT id,status FROM items ORDER BY id")
        qs = store.expiry_questions()
        self.assertEqual({q["item_id"] for q in qs}, {self.old, self.stale_task})
        self.assertTrue(all(q["question"].endswith("?") for q in qs))
        self.assertEqual(self.x("SELECT id,status FROM items ORDER BY id"), before)  # nothing changed
        self.assertEqual(self.x("SELECT count(*) FROM queue")[0][0], 2)             # and nothing queued

    def test_pin_and_already_asked_excluded(self):
        self.model(sm.set_override, "item", self.old, "pin", "keep", "2026-12-01")
        self.x("INSERT INTO queue(kind,subject_ref,question,created_at) VALUES('expiry',?,'q','x')", ("item:%d" % self.stale_task,))
        self.assertEqual(store.expiry_questions(), [])

    def test_fresh_not_flagged(self):
        self.assertNotIn(self.soon, {q["item_id"] for q in store.expiry_questions()})


class Urgent(Base):
    def test_ranked_pins_up_quiet_hidden(self):
        us = store.urgent_items()
        ids = [u["item_id"] for u in us]
        self.assertEqual(ids[0], self.pinned)                 # pin = 1.0 (ties break by earlier due, so the pin leads only if nothing else is 1.0)
        self.assertNotIn(self.quiet, ids)                     # quiet-until hides
        self.assertNotIn(self.done, ids)                      # closed
        self.assertNotIn(self.nodate, ids)                    # no opinion
        self.assertLess(ids.index(self.soon), ids.index(self.far))
        self.assertTrue(next(u for u in us if u["item_id"] == self.pinned)["pinned"])
        self.assertEqual([u["urgency"] for u in us], sorted((u["urgency"] for u in us), reverse=True))

    def test_limit_and_project_due(self):
        self.assertEqual(len(store.urgent_items(limit=1)), 1)
        self.project("Lease", "2026-11-13", items=[self.nodate])
        u = {x["item_id"]: x for x in store.urgent_items()}
        self.assertIn(self.nodate, u)
        self.assertEqual(u[self.nodate]["projects"], ["Lease"])

    def test_quiet_expires(self):
        ids = [u["item_id"] for u in store.urgent_items(now="2026-11-21")]
        self.assertNotIn(self.quiet, ids)  # past its own due and faded, not hidden by quiet
        ids2 = [u["item_id"] for u in store.urgent_items(now="2026-11-12")]
        self.assertNotIn(self.quiet, ids2)


class Digest(Base):
    def test_shape(self):
        d = store.week_digest("2026-11-09", "2026-11-16")
        self.assertEqual(set(d), {"start", "end", "as_of", "counts", "top_urgent", "due_in_window", "open_proposals", "overdue_reviews"})
        self.assertEqual(set(d["open_proposals"]), {"apply-label", "who-is-this"})
        self.assertEqual(d["open_proposals"]["apply-label"]["count"], 1)
        self.assertEqual(d["counts"]["open_proposals"], 2)
        self.assertEqual(d["counts"]["expiry_questions"], 2)
        self.assertEqual([r["level"] for r in d["overdue_reviews"]], ["person"])
        self.assertIn(self.soon, [i["item_id"] for i in d["due_in_window"]])
        self.assertNotIn(self.done, [i["item_id"] for i in d["due_in_window"]])
        self.assertEqual(d["counts"]["arrived"]["t/email"], 6)
        json.dumps(d)

    def test_answer_changes_digest(self):
        store.answer_proposal(self.q1, "yes")
        self.assertEqual(store.week_digest("2026-11-09", "2026-11-16")["counts"]["open_proposals"], 1)


class GcCommands(Base):
    def test_proposals_json_and_kind(self):
        rc, out, _ = self.gc("proposals", "--json")
        self.assertEqual((rc, json.loads(out)["count"]), (0, 2))
        rc, out, _ = self.gc("proposals", "--kind", "apply-label", "--json")
        self.assertEqual([p["id"] for p in json.loads(out)["proposals"]], [self.q1])

    def test_answer_then_gone(self):
        rc, out, _ = self.gc("answer", str(self.q1), "yes", "--json")
        self.assertEqual(rc, 0); self.assertIs(json.loads(out)["accepted"], True)
        self.assertEqual(json.loads(self.gc("proposals", "--json")[1])["count"], 1)
        rc, out, err = self.gc("answer", str(self.q1), "yes", "--json")
        self.assertEqual(rc, 1); self.assertIn("error", json.loads(out)); self.assertIn("already", err)

    def test_urgent_and_week(self):
        rc, out, _ = self.gc("urgent", "--limit", "2", "--json")
        self.assertEqual((rc, json.loads(out)["count"]), (0, 2))
        rc, out, _ = self.gc("week", "--start", "2026-11-09", "--json")
        self.assertEqual(rc, 0); self.assertEqual(json.loads(out)["end"], "2026-11-16")
        self.assertEqual(self.gc("week")[0], 0)
        self.assertIn("urgent", self.gc("urgent")[1])

    def test_read_commands_do_not_write(self):
        before = self.x("SELECT (SELECT count(*) FROM queue WHERE status='open'), (SELECT count(*) FROM answer_log), (SELECT count(*) FROM items)")
        for c in (("proposals",), ("urgent",), ("week",)):
            self.gc(*c, "--json")
        self.assertEqual(self.x("SELECT (SELECT count(*) FROM queue WHERE status='open'), (SELECT count(*) FROM answer_log), (SELECT count(*) FROM items)"), before)


if __name__ == "__main__":
    unittest.main()
