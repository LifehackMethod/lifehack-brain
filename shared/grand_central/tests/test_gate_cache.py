#!/usr/bin/env python3
"""test_gate_cache.py — the gate cache (migration 012): a calendar/task item whose gated text is
unchanged since its last CLEAN verdict skips BOTH gate layers on a later pull; changed text, a new
item, a quarantined item or an UNJUDGED/ATTACK verdict re-gate exactly as before. No Google, no real
claude call (judge_all is faked). Run: python3 tests/test_gate_cache.py"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import os, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "system", "tools"))
import migrate, pull  # noqa: E402
import sanitize as real_sanitize  # noqa: E402

MARK = "QZGATECACHE-9f2b41"


class Fetch:
    def gate_message(self, unit, body, item=""):
        return {"verdict": "NONE", "content": body, "reason": ""}


class FakeJudge:
    """Stands in for batch_reader.judge_all: every staged text → its verdict, and remembers what it saw."""
    def __init__(self, verdict="CLEAN"):
        self.verdict = verdict
        self.calls = 0
        self.seen = []

    def __call__(self, items, use_cache=True, reasons=None):
        self.calls += 1
        self.seen.extend(i for i, _ in items)
        return {i: self.verdict for i, _ in items}


FIELDS = {"title": "plan the week", "notes": f"review {MARK} notes"}


class GateCache(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        t = self._t.name
        dbp, hand = os.path.join(t, "rig.db"), os.path.join(t, "handoff")
        bk = os.path.join(t, "bk"); open(bk, "w", encoding="utf-8").close()
        self.assertEqual(migrate.run(dbp, apply=True, backup_ok=bk, out=lambda *_: None), 0)
        os.environ.update(RIG_DB=dbp, RIG_HANDOFF_DIR=hand)
        self.db = pull.open_db()
        self.judge = FakeJudge()
        self._orig = (pull.batch_reader.judge_all, getattr(pull, "email_fetch", None), getattr(pull, "sanitize", None),
                      pull.NO_GATE_CACHE, pull.REGATE_IDS, pull.RELEASE, pull.QUAR_TABLE)
        pull.batch_reader.judge_all = self.judge
        pull.email_fetch, pull.sanitize = Fetch(), real_sanitize
        pull.NO_GATE_CACHE, pull.REGATE_IDS, pull.RELEASE = False, None, None
        pull.QUAR_TABLE = "quarantine"
        pull.PENDING.clear()

    def tearDown(self):
        (pull.batch_reader.judge_all, _ef, _sn,
         pull.NO_GATE_CACHE, pull.REGATE_IDS, pull.RELEASE, pull.QUAR_TABLE) = self._orig
        if _ef is None:
            del pull.email_fetch
        else:
            pull.email_fetch = _ef
        if _sn is None:
            del pull.sanitize
        else:
            pull.sanitize = _sn
        pull.PENDING.clear()
        self.db.close()
        os.environ.pop("RIG_DB", None); os.environ.pop("RIG_HANDOFF_DIR", None)
        self._t.cleanup()

    def stage(self, item_id="task:t1", kind="task", fields=None):
        pull.stage_fields(fields if fields is not None else dict(FIELDS), item_id, kind,
                          lambda c, v, r, _id=item_id:
                          self.db.execute("INSERT OR REPLACE INTO tasks(id,title,notes,gate_verdict) "
                                          "VALUES(?,?,?,?)",
                                          (_id, c and c.get("title"), c and c.get("notes"), v)))

    def cached(self, item_id="task:t1"):
        return self.db.execute("SELECT text_hash, verdict FROM gate_cache WHERE item_id=?",
                               (item_id,)).fetchone()

    def test_migration_012_applied(self):
        # at least 012 (013 and later add more; the head is checked by test_migrations)
        self.assertGreaterEqual(self.db.execute("PRAGMA user_version").fetchone()[0], 12)
        self.assertIsNotNone(self.db.execute(
            "SELECT 1 FROM sqlite_master WHERE name='gate_cache'").fetchone())

    def test_unchanged_clean_item_skipped(self):
        self.stage(); pull.flush_pending(self.db)
        self.assertEqual(self.judge.calls, 1)          # new item is gated
        self.assertEqual(self.cached()[1], "CLEAN")
        row = self.db.execute("SELECT title, notes, gate_verdict FROM tasks").fetchone()
        self.assertEqual(row[0], real_sanitize.sanitize(FIELDS["title"], max_len=real_sanitize.NO_CAP))
        self.assertEqual(row[2], "NONE")
        # second pull, same text: skipped — no judge call, verdict kept, row rewritten
        self.judge.calls, self.judge.seen = 0, []
        pull.PENDING.clear()
        self.stage(); pull.flush_pending(self.db)
        self.assertEqual((self.judge.calls, self.judge.seen), (0, []))
        self.assertEqual(pull.STATS["gate_skipped"], 1)
        row = self.db.execute("SELECT title, notes, gate_verdict FROM tasks").fetchone()
        self.assertEqual(row[2], "NONE")
        self.assertEqual(row[0], real_sanitize.sanitize(FIELDS["title"], max_len=real_sanitize.NO_CAP))

    def test_changed_text_is_regated(self):
        self.stage(); pull.flush_pending(self.db)
        self.judge.calls = 0
        pull.PENDING.clear()
        self.stage(fields={"title": "plan the week", "notes": "CHANGED notes"})
        pull.flush_pending(self.db)
        self.assertEqual(self.judge.calls, 1)          # changed text → re-gated
        self.assertEqual(self.cached()[1], "CLEAN")    # re-cached with the new hash

    def test_quarantined_item_never_skipped(self):
        self.stage(); pull.flush_pending(self.db)
        self.judge.calls = 0
        self.db.execute("INSERT INTO quarantine(item_id,kind,verdict,reason,at) VALUES"
                        "('task:t1','task','REAL-ATTACK','ai','2026-11-12T20:00:00+00:00')")
        self.db.commit()
        pull.PENDING.clear()
        self.stage(); pull.flush_pending(self.db)
        self.assertEqual(self.judge.calls, 1)          # a quarantined item is never skipped

    def test_flagged_item_not_cached(self):
        self.judge.verdict = "ATTACK"
        self.stage(); pull.flush_pending(self.db)
        self.assertIsNone(self.cached())               # ATTACK is never cached
        self.judge.verdict, self.judge.calls = "CLEAN", 0
        pull.PENDING.clear()
        self.stage(); pull.flush_pending(self.db)
        self.assertEqual(self.judge.calls, 1)          # so the next pull re-gates it

    def test_unjudged_item_not_cached(self):
        self.judge.verdict = "UNJUDGED"
        self.stage(); pull.flush_pending(self.db)
        self.assertIsNone(self.cached())               # UNJUDGED is never cached (fail toward reading)

    def test_no_gate_cache_flag_regates(self):
        self.stage(); pull.flush_pending(self.db)
        self.judge.calls = 0
        pull.NO_GATE_CACHE = True
        pull.PENDING.clear()
        self.stage(); pull.flush_pending(self.db)
        self.assertEqual(self.judge.calls, 1)          # --no-gate-cache re-gates everything

    def test_filters_and_contacts_never_cached(self):
        pull.stage_fields({"name": MARK}, "contact_group:x", "contact_group",
                          lambda c, v, r: None)
        pull.flush_pending(self.db)
        self.assertIsNone(self.cached("contact_group:x"))  # only calendar/task items are cached


if __name__ == "__main__":
    unittest.main()
