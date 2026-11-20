#!/usr/bin/env python3
"""4P.3 item 9 (D8): the transcript access point admits read-only callers.
A caller may declare a CLOSED allowlist of read-only tools {"Read","Grep","Glob"}; anything
outside it (writes, network, mcp__*) is refused and logged, as today. The tool-less shape is
unchanged. Every admitted access logs the allowlist.

Run: python3 -I -B tests/test_p3door_readonly.py (from shared/grand_central/)
Planted bad cases, shown failing against the pre-change code first, passing after.
"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t # isolation: no test writes outside tmp
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import transcripts # noqa: E402

REL = ".local/share/example-data/front-room"

class FakeHome(object):
    """Same shape as test_step2_door.py's fixture: a fake home, one ingested thread."""
    def __init__(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="fakehome-"))
        self.front = os.path.join(self.root, REL)
        self.drop = os.path.join(self.root, "drop", "deliveries")
        os.makedirs(self.drop)
        self._env = dict((k, os.environ.get(k)) for k in ("HOME", "AGE_FRONT_ROOM", "GC_DATA_ROOT"))
        os.environ["HOME"] = self.root
        os.environ["GC_DATA_ROOT"] = os.path.join(self.root, ".local", "share", "example-data")
        os.environ.pop("AGE_FRONT_ROOM", None)

    def close(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.root, ignore_errors=True)

    def put_and_ingest(self, tid, mid):
        d = {"schema": "gc.delivery/1", "thread_id": tid, "message_id": mid, "subject": "s", "from": "f",
             "date": "d", "label": "l", "verdict": "safe", "triage": {"needs_me": "no", "deadline": None},
             "seen": "full", "internal_ms": 1000,
             "header": "# thread %s | subject: s\n\n" % tid,
             "block": "=== message %s | d | from: f | label: l ===\nbody of %s\n\n" % (mid, mid)}
        name = "%s.%s.json" % (tid, mid)
        with open(os.path.join(self.drop, name), "w", encoding="utf-8") as f:
            f.write(json.dumps(d))
        out = transcripts.ingest(self.drop, mailroom_uid=os.getuid())
        if out["ingested"] != 1:
            raise AssertionError("fixture ingest failed: %r" % out)

    def access_lines(self):
        with open(os.path.join(self.front, "access.log"), encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

class P3Door(unittest.TestCase):
    def setUp(self):
        self.h = FakeHome()
        self.addCleanup(self.h.close)
        self.h.put_and_ingest("b000001", "a000001")

    def _read(self, caller):
        return transcripts.read_thread("b000001", caller)

    def test_read_only_allowlist_with_a_write_tool_is_refused(self):
        """planted (a): ("Read","Write") is refused, as today."""
        c = transcripts.Caller("leaky", read_only=("Read", "Write"))
        with self.assertRaises(transcripts.Refused) as cm:
            self._read(c)
        self.assertEqual(cm.exception.reason, "caller_has_tools")
        refused = [l for l in self.h.access_lines() if l.get("outcome", "").startswith("refused:")]
        self.assertTrue(refused)

    def test_read_only_allowlist_with_network_is_refused(self):
        """planted (b): ("Read","WebFetch") is refused (a way out)."""
        c = transcripts.Caller("netty", read_only=("Read", "WebFetch"))
        with self.assertRaises(transcripts.Refused):
            self._read(c)
        c2 = transcripts.Caller("netty2", read_only=("Read", "WebSearch"))
        with self.assertRaises(transcripts.Refused):
            self._read(c2)

    def test_mcp_tool_is_refused(self):
        """planted (d): any mcp__ tool is refused."""
        c = transcripts.Caller("mcp", read_only=("Read", "mcp__easel__chart"))
        with self.assertRaises(transcripts.Refused):
            self._read(c)
        c2 = transcripts.Caller("mcp2", read_only=("mcp__x",))
        with self.assertRaises(transcripts.Refused):
            self._read(c2)

    def test_read_only_caller_is_admitted_and_allowlist_logged(self):
        """planted (c): ("Read",) is allowed and the access is logged with the allowlist."""
        c = transcripts.Caller("session-reader", read_only=("Read",))
        text = self._read(c)
        self.assertIn("body of a000001", text)
        ok = [l for l in self.h.access_lines()
              if l.get("caller") == "session-reader" and l.get("outcome") == "ok"]
        self.assertTrue(ok)
        self.assertEqual(ok[-1].get("allowlist"), ["Read"])

    def test_closed_allowlist_means_closed(self):
        """An empty allowlist admits nothing, and the tools= shape with any tool stays refused."""
        with self.assertRaises(transcripts.Refused):
            self._read(transcripts.Caller("empty", read_only=()))
        with self.assertRaises(transcripts.Refused):
            self._read(transcripts.Caller("tools-shape", tools=("Read",)))
        with self.assertRaises(transcripts.Refused):
            self._read(transcripts.Caller("not-a-caller", "nope"))

    def test_catalogue_text_admits_read_only_caller(self):
        c = transcripts.Caller("cat-reader", read_only=("Grep",))
        rows = transcripts.read_catalogue_text(c)
        self.assertTrue(rows)
        ok = [l for l in self.h.access_lines()
              if l.get("caller") == "cat-reader" and l.get("outcome") == "ok"]
        self.assertTrue(ok)
        self.assertEqual(ok[-1].get("allowlist"), ["Grep"])

    def test_tool_less_caller_unchanged(self):
        """planted (e): the tool-less caller keeps working unchanged."""
        c = transcripts.Caller("test-reader", tools=())
        self.assertTrue(c.tool_less)
        text = self._read(c)
        self.assertIn("body of a000001", text)
        rows = transcripts.read_catalogue_text(transcripts.Caller("test-reader", tools=()))
        self.assertTrue(rows)

if __name__ == "__main__":
    unittest.main(verbosity=2)
