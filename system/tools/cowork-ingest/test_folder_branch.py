#!/usr/bin/env python3
"""test_folder_branch.py — a pile can earn MORE THAN ONE folder path; recording it must not lose any of
them, and a map written before this fix must keep reading exactly as it always did.

Run:  python3 system/tools/cowork-ingest/test_folder_branch.py

WHY THIS EXISTS — [5.1.1] (2026-08-11): `propose_folder_shape()` can legitimately return SEVERAL paths
for one pile (e.g. one subject 'nested' under the pile's own folder AND another 'diverse' subject sitting
'sibling' beside it), but `set_folder_branch()` stored a single bare string per basket — so only the last
call's branch survived and every earlier one was silently overwritten. This file proves:
  (1) a pile that earns 1 nested + 1 sibling branch reloads from disk with BOTH present;
  (2) an OLD-FORMAT map (bare string `folder_branch`) still loads and still yields the same single path
      it always did — no migration, no schema change, no consumer breakage.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pipeline  # noqa: E402


def _map_dict(baskets=("alpha",)):
    return {
        "source": "world-tags.json",
        "schema_version": 2,
        "baskets": {b: {"sort_order": i, "basket_status": "queued"} for i, b in enumerate(baskets)},
        "rows": {f"{b}.txt": {"file": f"{b}.txt", "basket": b} for b in baskets},
    }


class FolderBranchCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="folder-branch-test-")
        self.map_path = os.path.join(self.tmp, "corpus-map.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_map(self, m):
        with io.open(self.map_path, "w", encoding="utf-8") as f:
            json.dump(m, f)

    def _reload(self):
        with io.open(self.map_path, encoding="utf-8") as f:
            return json.load(f)


class TestMultiBranchSurvives(FolderBranchCase):
    """The acceptance case: a fixture pile whose folder-shape proposal legitimately yields one `nested`
    path and one `sibling` path — both must survive a save + reload, not just the last one written."""

    def test_propose_folder_shape_can_return_two_paths(self):
        """Confirm the fixture is real: propose_folder_shape() itself returns 2 distinct shapes for a
        pile with one big core subject (nested) and one diverse subject (sibling) — this is the situation
        set_folder_branch() must be able to persist without losing either."""
        subjects = [
            {"name": "taxes", "item_count": 20, "relation": "core"},
            {"name": "unrelated-hobby", "item_count": 5, "relation": "diverse"},
        ]
        proposal = pipeline.propose_folder_shape("money", subjects, page_size=10)
        shapes = {p["shape"] for p in proposal}
        self.assertIn("nested", shapes)
        self.assertIn("sibling", shapes)
        paths = [p["path"] for p in proposal]
        self.assertEqual(len(paths), 2)
        self.assertNotEqual(paths[0], paths[1])
        self.branch_paths = paths  # used by the test below

    def test_both_paths_present_after_write_and_reload(self):
        subjects = [
            {"name": "taxes", "item_count": 20, "relation": "core"},
            {"name": "unrelated-hobby", "item_count": 5, "relation": "diverse"},
        ]
        proposal = pipeline.propose_folder_shape("money", subjects, page_size=10)
        paths = [p["path"] for p in proposal]
        self.assertEqual(len(paths), 2, "fixture must actually yield 2 branches or this test proves nothing")

        m = _map_dict(baskets=("money",))
        self._write_map(m)

        # Record BOTH paths in one call, exactly as the phase file now instructs (5.1.1).
        m = pipeline.load(self.map_path)
        ok, msg = pipeline.set_folder_branch(m, "money", paths)
        self.assertTrue(ok, msg)
        pipeline._save(m, self.map_path)

        # Reload from disk — a fresh process/session, same as PHASE 4 would see it.
        reloaded = pipeline.load(self.map_path)
        stored = reloaded["baskets"]["money"]["folder_branch"]
        self.assertIsInstance(stored, list, "2+ branches must persist as a list, not overwrite to one string")
        self.assertEqual(set(stored), set(paths))
        self.assertEqual(len(stored), 2)

        # The shared reader must also report both, regardless of on-disk shape.
        branches = pipeline.folder_branches(reloaded["baskets"]["money"])
        self.assertEqual(set(branches), set(paths))

    def test_two_separate_calls_accumulate_instead_of_clobbering(self):
        """Even if a session records one branch, then later a second branch in a SEPARATE call (rather
        than one call with both), the first must not be silently overwritten — this is the exact defect
        reported: 'only one survives into the persisted map; the rest are silently lost.'"""
        m = _map_dict(baskets=("money",))
        self._write_map(m)

        m = pipeline.load(self.map_path)
        ok1, _ = pipeline.set_folder_branch(m, "money", "money/taxes")
        self.assertTrue(ok1)
        ok2, _ = pipeline.set_folder_branch(m, "money", "unrelated-hobby")
        self.assertTrue(ok2)
        pipeline._save(m, self.map_path)

        reloaded = pipeline.load(self.map_path)
        branches = pipeline.folder_branches(reloaded["baskets"]["money"])
        self.assertIn("money/taxes", branches)
        self.assertIn("unrelated-hobby", branches)
        self.assertEqual(len(branches), 2)


class TestOldFormatStillLoads(FolderBranchCase):
    """A map written BEFORE this fix carries a bare string in `folder_branch`. It must load and behave
    identically to before — no migration, back-compat preserved."""

    def test_bare_string_map_reads_as_before(self):
        m = _map_dict(baskets=("alpha",))
        m["baskets"]["alpha"]["folder_branch"] = "alpha"   # the pre-fix shape: a plain string
        self._write_map(m)

        reloaded = pipeline.load(self.map_path)
        raw = reloaded["baskets"]["alpha"]["folder_branch"]
        self.assertEqual(raw, "alpha", "a legacy bare string must be untouched by merely loading the map")
        self.assertIsInstance(raw, str)

        # The new shared reader must normalize it to a 1-item list without altering the on-disk value.
        branches = pipeline.folder_branches(reloaded["baskets"]["alpha"])
        self.assertEqual(branches, ["alpha"])

    def test_recording_a_second_branch_on_a_legacy_string_upgrades_it_without_losing_the_first(self):
        m = _map_dict(baskets=("alpha",))
        m["baskets"]["alpha"]["folder_branch"] = "alpha"   # legacy shape, written by pre-fix code
        self._write_map(m)

        m = pipeline.load(self.map_path)
        ok, msg = pipeline.set_folder_branch(m, "alpha", "alpha/sub-topic")
        self.assertTrue(ok, msg)
        pipeline._save(m, self.map_path)

        reloaded = pipeline.load(self.map_path)
        branches = pipeline.folder_branches(reloaded["baskets"]["alpha"])
        self.assertIn("alpha", branches)          # the original legacy value is NOT lost
        self.assertIn("alpha/sub-topic", branches)

    def test_single_branch_write_on_a_fresh_basket_still_stores_a_bare_string(self):
        """The common case (one branch, the overwhelming majority) must remain byte-for-byte what every
        existing consumer (4-place.md's inline python, world-map-state) already expects — a plain string,
        not a one-element list."""
        m = _map_dict(baskets=("alpha",))
        self._write_map(m)
        m = pipeline.load(self.map_path)
        ok, msg = pipeline.set_folder_branch(m, "alpha", "alpha")
        self.assertTrue(ok, msg)
        pipeline._save(m, self.map_path)

        reloaded = pipeline.load(self.map_path)
        stored = reloaded["baskets"]["alpha"]["folder_branch"]
        self.assertEqual(stored, "alpha")
        self.assertIsInstance(stored, str)


class TestBlankBranchRefused(FolderBranchCase):
    def test_blank_string_refused(self):
        m = _map_dict(baskets=("alpha",))
        ok, msg = pipeline.set_folder_branch(m, "alpha", "   ")
        self.assertFalse(ok)
        self.assertIn("REFUSED", msg)

    def test_empty_list_refused(self):
        m = _map_dict(baskets=("alpha",))
        ok, msg = pipeline.set_folder_branch(m, "alpha", [])
        self.assertFalse(ok)
        self.assertIn("REFUSED", msg)

    def test_list_of_blanks_refused(self):
        m = _map_dict(baskets=("alpha",))
        ok, msg = pipeline.set_folder_branch(m, "alpha", ["  ", ""])
        self.assertFalse(ok)
        self.assertIn("REFUSED", msg)


class TestCLIAcceptsMultipleBranches(FolderBranchCase):
    """The `folder-branch` CLI subcommand — `--branch` now takes nargs='+' (5.1.1)."""

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, os.path.join(HERE, "pipeline.py"), *args],
            capture_output=True, text=True)

    def test_cli_single_branch_unchanged(self):
        m = _map_dict(baskets=("alpha",))
        self._write_map(m)
        r = self._run("folder-branch", "--map", self.map_path, "--basket", "alpha", "--branch", "alpha")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        reloaded = self._reload()
        self.assertEqual(reloaded["baskets"]["alpha"]["folder_branch"], "alpha")

    def test_cli_multiple_branches_in_one_call(self):
        m = _map_dict(baskets=("money",))
        self._write_map(m)
        r = self._run("folder-branch", "--map", self.map_path, "--basket", "money",
                       "--branch", "money/taxes", "unrelated-hobby")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        reloaded = self._reload()
        stored = reloaded["baskets"]["money"]["folder_branch"]
        self.assertIsInstance(stored, list)
        self.assertEqual(set(stored), {"money/taxes", "unrelated-hobby"})

    def test_cli_world_map_state_prints_all_branches(self):
        m = _map_dict(baskets=("money",))
        self._write_map(m)
        self._run("folder-branch", "--map", self.map_path, "--basket", "money",
                   "--branch", "money/taxes", "unrelated-hobby")
        r = self._run("world-map-state", "--map", self.map_path, "--basket", "money")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("money/taxes", r.stdout)
        self.assertIn("unrelated-hobby", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
