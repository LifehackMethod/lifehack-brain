#!/usr/bin/env python3
"""test_regate.py — --regate-quarantined machinery: only ids in REGATE_IDS are staged; a flagged item gets its
review file (mode 600) and reason/detail filled on the EXISTING quarantine row (no new row); text never enters
the db. No Google, no model call. Run: python3 tests/test_regate.py"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import os, sqlite3, stat, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "system", "tools"))
import migrate, pull  # noqa: E402
import sanitize as real_sanitize  # noqa: E402

MARK = "QZREGATE-b81d04e6"


class Fetch:
    def gate_message(self, unit, body, item=""):
        return {"verdict": "NONE", "content": body, "reason": ""}


class Regate(unittest.TestCase):
    def test_regate(self):
        with tempfile.TemporaryDirectory() as t:
            dbp, hand = os.path.join(t, "rig.db"), os.path.join(t, "handoff")
            bk = os.path.join(t, "bk"); open(bk, "w", encoding="utf-8").close()
            self.assertEqual(migrate.run(dbp, apply=True, backup_ok=bk, out=lambda *_: None), 0)
            os.environ.update(RIG_DB=dbp, RIG_HANDOFF_DIR=hand)
            orig = pull.batch_reader.judge_all
            try:
                pull.email_fetch, pull.sanitize = Fetch(), real_sanitize
                pull.PENDING.clear()
                def fake(items, use_cache=True, reasons=None):
                    for i, _ in items:
                        if reasons is not None:
                            reasons[i] = "orders the assistant"
                    return {i: "ATTACK" for i, _ in items}
                pull.batch_reader.judge_all = fake
                db = pull.open_db()
                db.execute("INSERT INTO quarantine(item_id,kind,verdict,reason,at) VALUES"
                           "('calendar_event:e1','calendar_event','REAL-ATTACK','ai','2026-11-12T20:00:00+00:00')")
                db.commit()
                self.assertEqual(pull.regate_ids(db), [("calendar_event:e1", "calendar_event")])
                self.assertEqual(pull.regate_ids(db, "2026-11-13"), [])
                pull.REGATE_IDS = {"calendar_event:e1"}
                wrote = []
                for iid in ("calendar_event:e1", "calendar_event:other"):
                    pull.stage_fields({"summary": MARK}, iid, "calendar_event", lambda c, v, r: wrote.append(v))
                self.assertEqual(len(pull.PENDING), 1)
                pull.flush_pending(db)
                rows = list(db.execute("SELECT item_id, detail FROM quarantine"))
                self.assertEqual(len(rows), 1)
                self.assertIn("orders the assistant", rows[0][1])
                d = os.path.join(hand, "_unpacked", "quarantine")
                files = os.listdir(d)
                self.assertEqual(len(files), 1)
                self.assertEqual(stat.S_IMODE(os.stat(os.path.join(d, files[0])).st_mode), 0o600)
                for tb in [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
                    self.assertNotIn(MARK, repr(list(db.execute(f'SELECT * FROM "{tb}"'))))
                db.close()
            finally:
                pull.REGATE_IDS = None
                pull.batch_reader.judge_all = orig
                os.environ.pop("RIG_DB", None); os.environ.pop("RIG_HANDOFF_DIR", None)


class Release(unittest.TestCase):
    """--release-quarantined: clean item stored as cleared; flagged item stored only with --override; row -> RELEASED."""
    def _run(self, judged, override):
        with tempfile.TemporaryDirectory() as t:
            dbp, hand = os.path.join(t, "rig.db"), os.path.join(t, "handoff")
            bk = os.path.join(t, "bk"); open(bk, "w", encoding="utf-8").close()
            self.assertEqual(migrate.run(dbp, apply=True, backup_ok=bk, out=lambda *_: None), 0)
            os.environ.update(RIG_DB=dbp, RIG_HANDOFF_DIR=hand)
            orig = pull.batch_reader.judge_all
            try:
                pull.email_fetch, pull.sanitize = Fetch(), real_sanitize
                pull.PENDING.clear()
                pull.batch_reader.judge_all = lambda items, use_cache=True, reasons=None: {i: judged for i, _ in items}
                db = pull.open_db()
                for iid in ("task:t1", "task:t2"):
                    db.execute("INSERT INTO quarantine(item_id,kind,verdict,reason,at) VALUES(?,?,?,?,?)",
                               (iid, "task", "REAL-ATTACK", "ai", "2026-11-12T20:00:00+00:00"))
                db.commit()
                pull.REGATE_IDS = {"task:t1"}
                pull.RELEASE = {"reason": "owner-approved false positive", "override": set(override)}
                pull.stage_fields({"title": "plan the week"}, "task:t1", "task",
                                  lambda c, v, r: db.execute("INSERT INTO tasks(id,title,gate_verdict) VALUES('t1',?,?)",
                                                             (c["title"] if c else None, v)))
                pull.flush_pending(db)
                q = {r[0]: r[1:] for r in db.execute("SELECT item_id, verdict, reason FROM quarantine")}
                tk = list(db.execute("SELECT title, gate_verdict FROM tasks"))
                db.close()
                return q, tk
            finally:
                pull.REGATE_IDS = None; pull.RELEASE = None
                pull.batch_reader.judge_all = orig
                os.environ.pop("RIG_DB", None); os.environ.pop("RIG_HANDOFF_DIR", None)

    def test_clean_released(self):
        q, tk = self._run("NONE", [])
        self.assertEqual(q["task:t1"][0], "RELEASED")
        self.assertEqual(q["task:t2"][0], "REAL-ATTACK")          # untouched: not named
        self.assertEqual(tk, [("plan the week", "NONE")])

    def test_flagged_needs_override(self):
        q, tk = self._run("ATTACK", [])
        self.assertEqual(q["task:t1"], ("REAL-ATTACK", "release-refused"))
        self.assertEqual(tk, [])
        q, tk = self._run("ATTACK", ["task:t1"])
        self.assertEqual(q["task:t1"][0], "RELEASED")
        self.assertEqual(tk, [("plan the week", "OWNER-OVERRIDE")])


if __name__ == "__main__":
    unittest.main()
