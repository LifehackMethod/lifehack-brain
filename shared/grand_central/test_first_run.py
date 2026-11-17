"""test_first_run.py -- tests for first_run.py (step 4M.7(a)). Tmp folders only; never the real root."""
import glob
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = os.path.dirname(HERE)
PLUGIN = os.path.dirname(SHARED)
WORKTREE = os.path.dirname(PLUGIN)
if SHARED not in sys.path:
    sys.path.insert(0, SHARED)

import first_run  # noqa: E402
import gc_settings  # noqa: E402

PYTHON = sys.executable


def run_cli(args):
    return subprocess.run([PYTHON, os.path.join(HERE, "first_run.py")] + args,
                          capture_output=True, text=True, cwd=WORKTREE)


class FirstRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gc-first-run-")
        self.root = os.path.join(self.tmp, "personal-code")
        os.makedirs(self.root)  # the personal code root must already exist

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def setup_dir(self):
        return os.path.join(self.root, "tools", "grand-central", "setup")

    # 1. a fresh root gets every file --------------------------------------------------------------------------------
    def test_fresh_root_gets_every_template(self):
        tdir, _setup, pairs = first_run.plan(self.root)
        self.assertTrue(pairs)
        rc = first_run.run(root=self.root)
        self.assertEqual(rc, 0)
        got = sorted(os.path.basename(p) for p in glob.glob(os.path.join(self.setup_dir(), "*")))
        for _src, dst in pairs:
            self.assertIn(os.path.basename(dst), got)
            self.assertTrue(os.path.isfile(dst))
        # every template lands; migrations/ exists (empty series is valid)
        self.assertTrue(os.path.isdir(os.path.join(self.setup_dir(), "migrations")))
        # the scaffold pieces exist too
        for rel in ("jobs.md", "tools", "JOBS-README.txt"):
            self.assertTrue(os.path.lexists(os.path.join(self.root, rel)), rel)
        # example names never leak through
        self.assertFalse(glob.glob(os.path.join(self.setup_dir(), "*.example.json")))
        # every copied file parses as JSON
        for p in glob.glob(os.path.join(self.setup_dir(), "*.json")):
            with open(p, encoding="utf-8") as f:
                json.load(f)
        # idempotent: second run creates nothing
        before = {p: os.path.getmtime(p) for p in glob.glob(os.path.join(self.setup_dir(), "*"))}
        rc2 = first_run.run(root=self.root)
        self.assertEqual(rc2, 0)
        after = {p: os.path.getmtime(p) for p in glob.glob(os.path.join(self.setup_dir(), "*"))}
        self.assertEqual(before, after)

    def test_second_run_overwrites_nothing(self):
        first_run.run(root=self.root)
        gc_path = os.path.join(self.setup_dir(), "gc.json")
        with open(gc_path, encoding="utf-8") as f:
            edited = json.load(f)
        edited["owner_name"] = "My Own Edit"
        with open(gc_path, "w", encoding="utf-8") as f:
            json.dump(edited, f, indent=2)
        first_run.run(root=self.root)
        with open(gc_path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["owner_name"], "My Own Edit")

    def test_dry_run_writes_nothing(self):
        rc = first_run.run(root=self.root, dry_run=True)
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(self.setup_dir()))
        self.assertEqual(sorted(os.listdir(self.root)), [])
        # and the CLI flag behaves the same
        p = run_cli(["--dry-run", "--root", self.root])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(sorted(os.listdir(self.root)), [])

    def test_setup_loads_through_gc_settings(self):
        first_run.run(root=self.root)
        old = os.environ.pop("GC_SETUP_DIR", None)
        try:
            # point gc_settings straight at the freshly written setup folder
            os.environ["GC_SETUP_DIR"] = self.setup_dir()
            self.assertEqual(gc_settings.owner_name(), "Owner One")
            self.assertEqual(gc_settings.default_desk(), "desk-a")
            self.assertEqual(gc_settings.main_diary(), "Main-Diary")
            self.assertIn("part-a", gc_settings.domains())
            gc_settings.labels()
            gc_settings.routing()
            gc_settings.load("leans.json")
            gc_settings.load("keywords.json")
            gc_settings.load("expected.json")
            gc_settings.load("alarm-settings.json")
            gc_settings.load("status_lights.json")
        finally:
            if old is not None:
                os.environ["GC_SETUP_DIR"] = old
            else:
                del os.environ["GC_SETUP_DIR"]
    def test_no_template_holds_any_real_value(self):
        """None of the templates holds a personal value of the real setup folder: the lock itself (the one
        place that knows what is personal) is run over templates/. The real values are never printed."""
        import io
        import check_personal_values as lock
        old = os.environ.pop("GC_SETUP_DIR", None)   # the harness points it at the synthetic fixture; we need the real one
        try:
            try:
                real_dir = lock.setup_dir(None, lock.load_roots())
            except lock.CannotEvaluate:
                real_dir = None
            if not real_dir or not os.path.isdir(real_dir):
                self.skipTest("no real setup folder on this machine")
            out = io.StringIO()
            rc = lock.run(os.path.join(HERE, "templates"), real_dir, out=out)
        finally:
            if old is not None:
                os.environ["GC_SETUP_DIR"] = old
        self.assertEqual(rc, 0, out.getvalue())

    def test_cli_end_to_end(self):
        p = run_cli(["--root", self.root])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("created:", p.stdout)
        self.assertIn("scaffold", p.stdout)
        self.assertTrue(os.path.isfile(os.path.join(self.setup_dir(), "gc.json")))


if __name__ == "__main__":
    unittest.main()
