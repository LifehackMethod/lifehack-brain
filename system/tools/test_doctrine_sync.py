#!/usr/bin/env python3
"""Tests for system/tools/doctrine_sync.py — the 3-way compare, push/check/pull, archive-before-overwrite.
Runs entirely in temp folders: a fake repo root (the two local files) and a fake notes root."""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import doctrine_sync as ds  # noqa: E402


def _r(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _j(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="doctrine-sync-")
        self.code = os.path.join(self.tmp, "repo")
        self.brain = os.path.join(self.tmp, "brain")
        _w(os.path.join(self.code, "CLAUDE.local.md"), "# rules v1\n")
        _w(os.path.join(self.code, ".claude", "settings.local.json"), '{"env": {"X": "1"}}\n')
        _w(os.path.join(self.code, ".brain-root"), self.brain + "\n")
        os.makedirs(self.brain)
        self.desk = ds.Ctx(self.code, self.brain, "desktop")
        self.code2 = os.path.join(self.tmp, "repo2")          # a second machine: own repo copy, same mirror
        shutil.copytree(self.code, self.code2)
        self.lap = ds.Ctx(self.code2, self.brain, "laptop")
        self.out = io.StringIO()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def findings(self, ctx):
        p = os.path.join(ctx.findings_dir, ctx.producer + ".local.jsonl")
        if not os.path.exists(p):
            return []
        with open(p, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]


class TestClassify(unittest.TestCase):
    def test_table(self):
        c = ds.classify
        self.assertEqual(c("a", "a", None), "OK")
        self.assertEqual(c("a", None, None), "NO-MIRROR")
        self.assertEqual(c(None, "a", None), "NO-LOCAL")
        self.assertEqual(c(None, None, None), "OK")
        self.assertEqual(c("b", "a", "a"), "AHEAD")      # mirror unchanged since sync, local moved
        self.assertEqual(c("a", "b", "a"), "BEHIND")     # local unchanged since sync, mirror moved
        self.assertEqual(c("b", "c", "a"), "CONFLICT")   # both moved
        self.assertEqual(c("b", "a", None), "CONFLICT")  # never synced here, and they differ


class TestFlow(Base):
    def test_first_check_adopts_then_ok(self):
        r = ds.do_check(self.desk, out=self.out)
        self.assertEqual([k for _, k in r], ["NO-MIRROR", "NO-MIRROR"])
        self.assertTrue(os.path.exists(self.desk.mirror("CLAUDE.local.md")))
        f = self.findings(self.desk)
        self.assertEqual(len(f), 2)
        self.assertTrue(all(x["status"] == "OK" for x in f))
        self.assertEqual(f[0]["producer"], "doctrine-sync-desktop")
        self.assertEqual(f[0]["scanned_n"], 2)
        r = ds.do_check(self.desk, out=self.out)
        self.assertEqual([k for _, k in r], ["OK", "OK"])

    def test_behind_is_drift_and_pull_archives(self):
        ds.do_check(self.desk, out=self.out)                      # desktop adopts
        ds.do_check(self.lap, out=self.out)                       # laptop: identical content -> OK, synced
        _w(os.path.join(self.code, "CLAUDE.local.md"), "# rules v2\n")
        r = ds.do_check(self.desk, out=self.out)                  # desktop AHEAD -> auto-push
        self.assertEqual(dict(r)["CLAUDE.local.md"], "AHEAD")
        r = ds.do_check(self.lap, out=self.out)                   # laptop BEHIND -> DRIFT finding
        self.assertEqual(dict(r)["CLAUDE.local.md"], "BEHIND")
        rows = [x for x in self.findings(self.lap) if x["labels"]["file"] == "CLAUDE.local.md"]
        self.assertEqual(rows[-1]["status"], "DRIFT")
        self.assertIn("pull", rows[-1]["summary"])
        self.assertEqual(len({x["fingerprint"] for x in rows}), 1)   # stable identity across kinds
        ds.do_pull(self.lap, ds.select(["CLAUDE.local.md"]), dry_run=True, out=self.out)
        self.assertEqual(_r(os.path.join(self.code2, "CLAUDE.local.md")), "# rules v1\n")
        self.assertIn("-# rules v1", self.out.getvalue())
        self.assertIn("+# rules v2", self.out.getvalue())
        ds.do_pull(self.lap, ds.select(["CLAUDE.local.md"]), dry_run=False, out=self.out)
        self.assertEqual(_r(os.path.join(self.code2, "CLAUDE.local.md")), "# rules v2\n")
        arch = os.listdir(self.lap.archive_dir)
        self.assertEqual(len(arch), 1)
        self.assertTrue(arch[0].startswith("CLAUDE.local.md.laptop."))
        self.assertEqual(_r(os.path.join(self.lap.archive_dir, arch[0])), "# rules v1\n")
        r = ds.do_check(self.lap, out=self.out)
        self.assertEqual(dict(r)["CLAUDE.local.md"], "OK")

    def test_conflict_needs_review_and_copies_nothing(self):
        ds.do_check(self.desk, out=self.out)
        ds.do_check(self.lap, out=self.out)
        _w(os.path.join(self.code, "CLAUDE.local.md"), "# desktop edit\n")
        ds.do_check(self.desk, out=self.out)                      # pushed
        _w(os.path.join(self.code2, "CLAUDE.local.md"), "# laptop edit\n")
        r = ds.do_check(self.lap, out=self.out)
        self.assertEqual(dict(r)["CLAUDE.local.md"], "CONFLICT")
        rows = [x for x in self.findings(self.lap) if x["labels"]["file"] == "CLAUDE.local.md"]
        self.assertEqual(rows[-1]["status"], "NEEDS_REVIEW")
        self.assertEqual(_r(self.desk.mirror("CLAUDE.local.md")), "# desktop edit\n")
        self.assertEqual(_r(os.path.join(self.code2, "CLAUDE.local.md")), "# laptop edit\n")

    def test_brain_root_recorded_never_flagged(self):
        _w(os.path.join(self.code2, ".brain-root"), "/somewhere/else\n")
        ds.do_check(self.desk, out=self.out)
        r = ds.do_check(self.lap, out=self.out)
        self.assertEqual([k for _, k in r], ["OK", "OK"])
        st = _j(self.lap.state_path)
        self.assertNotEqual(st["brain_root_sha256"], _j(self.desk.state_path)["brain_root_sha256"])
        self.assertFalse(os.path.exists(self.lap.mirror(".brain-root")))

    def test_one_writer_per_path(self):
        ds.do_check(self.desk, out=self.out)
        ds.do_check(self.lap, out=self.out)
        names = sorted(os.listdir(self.desk.mirror_dir))
        for n in ("machine.desktop.json", "machine.laptop.json", "manifest.json"):
            self.assertIn(n, names)
        f = sorted(os.listdir(self.desk.findings_dir))
        self.assertEqual(f, ["doctrine-sync-desktop.local.jsonl", "doctrine-sync-laptop.local.jsonl"])

    def test_check_crash_emits_error_finding(self):
        bad = ds.Ctx(self.code, self.brain, "desktop")
        blocker = os.path.join(self.brain, "blocker")
        _w(blocker, "x")
        bad.state_path = os.path.join(blocker, "child.json")      # parent is a file -> OSError on save
        r = ds.do_check(bad, out=self.out)
        self.assertEqual(r[-1], ("_self", "ERROR"))
        f = self.findings(bad)
        self.assertEqual(f[-1]["status"], "ERROR")
        self.assertEqual(f[-1]["scanned_n"], 0)

    def test_slug(self):
        self.assertEqual(ds.slug("Wren’s Mac mini"), "wren-s-mac-mini")
        self.assertEqual(ds.slug(""), "unknown")


if __name__ == "__main__":
    unittest.main(verbosity=1)
