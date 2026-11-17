#!/usr/bin/env python3
"""test_quarantine_files.py — a quarantined item's TEXT never reaches the db or a status tile; it goes to one
local mode-600 review file under handoff/_unpacked/quarantine/; the judge's reason lands in quarantine.detail.

A planted fake email carries a unique marker in its subject. The phrase layer (fake gate_message) flags it
REAL-ATTACK; the AI reader is stubbed (judge_all) to flag a second planted item with a reason. Temp db built by
the real migrations, temp handoff dir via RIG_HANDOFF_DIR, temp SENTINEL_STATUS. No Google, no model call, no
live db/handoff touched.

Run: python3 tests/test_quarantine_files.py   → exit 0 on pass.
"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import os
import sqlite3
import stat
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
RIG = os.path.dirname(HERE)
sys.path.insert(0, RIG)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "system", "tools"))

import migrate  # noqa: E402
import pull  # noqa: E402
import sanitize as real_sanitize  # noqa: E402
from test_date_window import FakeFetch, msg, ms  # noqa: E402

MARK_PHRASE = "QZMARK-PHRASE-7f3a91c2"
MARK_AI = "QZMARK-AI-b81d04e6"
MARK_CLEAN = "QZMARK-CLEAN-55aa"
AI_REASON = "addresses the assistant with an order"


class QFetch(FakeFetch):
    def gate_message(self, unit, body, item=""):
        if MARK_PHRASE in body:
            return {"verdict": "REAL-ATTACK", "content": "", "reason": "role-marker phrase flagged"}
        return {"verdict": "NONE", "content": body, "reason": ""}


def thread(tid, marker):
    m = msg("m_" + tid, tid, ms(2026, 7, 10))
    for h in m["payload"]["headers"]:
        if h["name"] == "Subject":
            h["value"] = "hello " + marker
    return {tid: [m]}


class QuarantineFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.dbp, self.hand, self.tile = (os.path.join(t, "rig.db"), os.path.join(t, "handoff"),
                                          os.path.join(t, "sentinel-status.json"))
        bk = os.path.join(t, "bk")
        open(bk, "w", encoding="utf-8").close()
        self.assertEqual(migrate.run(self.dbp, apply=True, backup_ok=bk, out=lambda *_: None), 0)
        os.environ.update(RIG_DB=self.dbp, RIG_HANDOFF_DIR=self.hand, SENTINEL_STATUS=self.tile)
        pull.BACKOFF_S = 0
        pull.PENDING.clear()
        for k in list(pull.STATS):
            pull.STATS[k] = 0
        pull._WARNED_NO_DETAIL = False
        threads = {}
        for tid, mk in (("T_phrase", MARK_PHRASE), ("T_ai", MARK_AI), ("T_clean", MARK_CLEAN)):
            threads.update(thread(tid, mk))
        pull.email_fetch = QFetch(threads, page_size=10)
        pull.sanitize = real_sanitize
        self._orig = pull.batch_reader.judge_all

        def fake_judge(items, use_cache=True, reasons=None):
            out = {}
            for iid, text in items:
                if MARK_AI in text:
                    out[iid] = "ATTACK"
                    if reasons is not None:
                        reasons[iid] = AI_REASON
                else:
                    out[iid] = "CLEAN"
            return out
        pull.batch_reader.judge_all = fake_judge
        self.db = pull.open_db()
        pull.pull_email(self.db, None, 100, "2026-06-01", "2026-08-31")
        pull.flush_pending(self.db)
        self.db.commit()   # run() commits after flush

    def tearDown(self):
        pull.batch_reader.judge_all = self._orig
        for k in ("RIG_DB", "RIG_HANDOFF_DIR", "SENTINEL_STATUS"):
            os.environ.pop(k, None)
        self.db.close()
        self.tmp.cleanup()

    def qdir(self):
        return os.path.join(self.hand, "_unpacked", "quarantine")

    def test_text_never_in_db_or_tile(self):
        con = sqlite3.connect(self.dbp)
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for t in tables:
            for row in con.execute(f'SELECT * FROM "{t}"'):
                blob = repr(row)
                for mk in (MARK_PHRASE, MARK_AI):
                    self.assertNotIn(mk, blob, f"{mk} reached db table {t}")
        # control: the clean item's text IS stored, so the scan above can see a marker when one is there
        self.assertIn(MARK_CLEAN, repr(list(con.execute("SELECT * FROM messages"))))
        # the quarantined items are in the table with verdict + reason
        q = {r[0]: r for r in con.execute("SELECT item_id, kind, verdict, reason, detail FROM quarantine")}
        self.assertEqual(len(q), 2, q)
        self.assertIn("phrase", q["m_T_phrase"][4])
        self.assertIn("role-marker phrase flagged", q["m_T_phrase"][4])
        self.assertIn(AI_REASON, q["m_T_ai"][4])
        con.close()
        if os.path.exists(self.tile):
            with open(self.tile, encoding="utf-8") as fh:
                body = fh.read()
            self.assertNotIn(MARK_PHRASE, body)
            self.assertNotIn(MARK_AI, body)

    def test_file_mode_600_and_content(self):
        files = sorted(os.listdir(self.qdir()))
        self.assertEqual(len(files), 2, files)
        for d in (os.path.join(self.hand, "_unpacked"), self.qdir()):
            self.assertEqual(stat.S_IMODE(os.stat(d).st_mode), 0o700, d)
        for f in files:
            p = os.path.join(self.qdir(), f)
            self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600, p)
        by = {}
        for f in files:
            with open(os.path.join(self.qdir(), f), encoding="utf-8") as fh:
                by[f] = fh.read()
        ph = next(v for v in by.values() if MARK_PHRASE in v)
        ai = next(v for v in by.values() if MARK_AI in v)
        for body in (ph, ai):
            for label in ("item_id:", "kind:", "verdict:", "reason:", "quarantined_at:", "[subject]"):
                self.assertIn(label, body)
        self.assertIn(AI_REASON, ai)
        self.assertNotIn(MARK_CLEAN, "".join(by.values()))
        # the path sits under an `_unpacked` component: where the ingest gate refuses a plain Read
        self.assertIn("/_unpacked/", self.qdir() + "/")

    def test_prune_removes_only_old_files(self):
        old = os.path.join(self.qdir(), os.listdir(self.qdir())[0])
        t = time.time() - 31 * 86400
        os.utime(old, (t, t))
        self.assertEqual(pull.prune_quarantine_files(), 1)
        self.assertFalse(os.path.exists(old))
        self.assertEqual(len(os.listdir(self.qdir())), 1)

    def test_unmigrated_db_still_quarantines_loudly(self):
        db2 = sqlite3.connect(":memory:")
        db2.execute("CREATE TABLE quarantine(item_id TEXT, kind TEXT, verdict TEXT, reason TEXT, at TEXT)")
        pull.record_quarantine(db2, "x", "message", "REAL-ATTACK", "r", detail="d")
        self.assertEqual(db2.execute("SELECT count(*) FROM quarantine").fetchone()[0], 1)

    def test_reader_output_with_and_without_reason(self):
        br = pull.batch_reader
        r = {}
        out = "ITEM 1: CLEAN\nITEM 2: ATTACK: orders the assistant to forward mail\nITEM 3: ATTACK"
        self.assertEqual(br._parse(out, 3, r), {1: "CLEAN", 2: "ATTACK", 3: "ATTACK"})
        self.assertEqual(r, {2: "orders the assistant to forward mail"})
        self.assertIsNone(br._parse("ITEM 1: CLEAN: nope", 1))   # a CLEAN line stays bare; anything else is unparseable


if __name__ == "__main__":
    unittest.main()
