#!/usr/bin/env python3
"""test_pad_init.py — `pad-init` must not be able to print OK while persisting nothing.

Run:  python3 system/tools/cowork-ingest/test_pad_init.py

WHY THIS EXISTS — two bugs, reported by avitals25 (GitHub issue #2, Windows 11) with no code attached:
(1) `pad_write()`'s CREATE branch built the skeleton via `compose_pad()` and never read the caller's
    `entry` at all — a first-ever `pad-init --entry "..."` printed OK and silently dropped the note.
(2) the corpus folder was derived from `_slugify(m.get("source") or "corpus")` — `source` names the TAG
    FILE the map was built from (e.g. "world-tags.json"), not the corpus, so pads landed at
    `memory/world-tags/...`, a folder nothing reads. A pad written to the wrong folder SUCCEEDS, so the
    fallback was invisible until someone went looking for their notes and found nothing.

Both bugs share one shape: the tool reported success (`OK`, gate flag set) without the thing it claimed
to have done actually happening. These tests exist so that shape can never come back unnoticed.
"""

import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pipeline  # noqa: E402


def _map_dict(source="world-tags.json", baskets=("alpha",)):
    return {
        "source": source,
        "schema_version": 2,
        "baskets": {b: {"sort_order": i, "basket_status": "queued"} for i, b in enumerate(baskets)},
        "rows": {f"{b}.txt": {"file": f"{b}.txt", "basket": b} for b in baskets},
    }


class PadWriteCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pad-init-test-")

    def tearDown(self):
        # restore write perms before rmtree in case a permission test left something locked down
        for root, dirs, _files in os.walk(self.tmp):
            for d in dirs:
                try:
                    os.chmod(os.path.join(root, d), 0o700)
                except OSError:
                    pass
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestCreateWithEntry(PadWriteCase):
    """The bug: the create branch never looked at `entry` at all."""

    def test_entry_lands_on_first_ever_write(self):
        m = _map_dict()
        outcome, path, detail = pipeline.pad_write(
            m, "my-corpus", self.tmp, entry="THIS TEXT MUST SURVIVE", basket="alpha",
            now_iso="2026-08-11T00:00:00+00:00")
        self.assertEqual(outcome, "CREATED", detail)
        self.assertIsNone(detail)
        with io.open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("THIS TEXT MUST SURVIVE", text)
        # the skeleton must ALSO still be there — entry does not replace it
        for h in pipeline.PAD_HEADINGS:
            self.assertIn(h, text)

    def test_no_entry_on_create_leaves_skeleton_alone(self):
        m = _map_dict()
        outcome, path, detail = pipeline.pad_write(
            m, "my-corpus", self.tmp, entry=None, basket="alpha", now_iso="2026-08-11T00:00:00+00:00")
        self.assertEqual(outcome, "CREATED", detail)
        with io.open(path, encoding="utf-8") as f:
            text = f.read()
        # no dated block was appended — the file ends with the skeleton, no trailing "### <date>" block
        self.assertNotIn("---\n\n### 2026-08-11", text)
        for h in pipeline.PAD_HEADINGS:
            self.assertIn(h, text)

    def test_empty_string_entry_on_create_also_leaves_skeleton_alone(self):
        m = _map_dict()
        outcome, path, detail = pipeline.pad_write(
            m, "my-corpus", self.tmp, entry="   ", basket="alpha", now_iso="2026-08-11T00:00:00+00:00")
        self.assertEqual(outcome, "CREATED", detail)
        with io.open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("### 2026-08-11", text)


class TestAppendWithEntry(PadWriteCase):
    """Prior content must survive — APPEND, NEVER OVERWRITE."""

    def test_second_write_appends_and_keeps_the_first(self):
        m = _map_dict()
        outcome1, path1, _ = pipeline.pad_write(
            m, "my-corpus", self.tmp, entry="FIRST ENTRY MUST SURVIVE", basket="alpha",
            now_iso="2026-08-11T00:00:00+00:00")
        self.assertEqual(outcome1, "CREATED")
        outcome2, path2, _ = pipeline.pad_write(
            m, "my-corpus", self.tmp, entry="SECOND ENTRY MUST ALSO SURVIVE", basket="alpha",
            now_iso="2026-08-12T00:00:00+00:00")
        self.assertEqual(outcome2, "APPENDED")
        self.assertEqual(path1, path2)
        with io.open(path1, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("FIRST ENTRY MUST SURVIVE", text)
        self.assertIn("SECOND ENTRY MUST ALSO SURVIVE", text)
        # the first entry's text must precede the second's — this is an append, not a rewrite
        self.assertLess(text.index("FIRST ENTRY MUST SURVIVE"), text.index("SECOND ENTRY MUST ALSO SURVIVE"))


class TestCorpusIdResolution(PadWriteCase):
    """All four resolution paths, and `source` never used even when present in the map."""

    def _map_path(self, corpus="my-corpus", fname="corpus-map.json"):
        d = os.path.join(self.tmp, "state", "projects", corpus, "work")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, fname)
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(_map_dict(source="world-tags.json"), f)
        return p

    def test_1_explicit_corpus_id_wins(self):
        p = self._map_path(corpus="path-corpus")
        corpus_id, label = pipeline.resolve_corpus_id("explicit-corpus", p)
        self.assertEqual(corpus_id, "explicit-corpus")
        self.assertEqual(label, "--corpus-id")

    def test_2_map_path_shape_resolves(self):
        p = self._map_path(corpus="path-corpus")
        corpus_id, label = pipeline.resolve_corpus_id(None, p)
        self.assertEqual(corpus_id, "path-corpus")
        self.assertIn(p, label)

    def test_3_env_var_used_when_path_shape_does_not_match(self):
        # a map NOT shaped like .../projects/<corpus>/work/<file>.json
        p = os.path.join(self.tmp, "somewhere", "flat-map.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(_map_dict(), f)
        old = os.environ.get("INGEST_CORPUS")
        os.environ["INGEST_CORPUS"] = "env-corpus"
        try:
            corpus_id, label = pipeline.resolve_corpus_id(None, p)
        finally:
            if old is None:
                os.environ.pop("INGEST_CORPUS", None)
            else:
                os.environ["INGEST_CORPUS"] = old
        self.assertEqual(corpus_id, "env-corpus")
        self.assertIn("INGEST_CORPUS", label)

    def test_4_refuses_when_nothing_resolves(self):
        p = os.path.join(self.tmp, "somewhere", "flat-map.json")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(_map_dict(), f)
        old = os.environ.pop("INGEST_CORPUS", None)
        try:
            corpus_id, message = pipeline.resolve_corpus_id(None, p)
        finally:
            if old is not None:
                os.environ["INGEST_CORPUS"] = old
        self.assertIsNone(corpus_id)
        self.assertIn("--corpus-id", message)
        self.assertIn("INGEST_CORPUS", message)

    def test_map_path_outranks_env_var(self):
        """The map path is evidence about the file actually being operated on; the env var is a session
        leftover that can point at a different corpus. Order matters."""
        p = self._map_path(corpus="path-corpus")
        old = os.environ.get("INGEST_CORPUS")
        os.environ["INGEST_CORPUS"] = "env-corpus"
        try:
            corpus_id, _label = pipeline.resolve_corpus_id(None, p)
        finally:
            if old is None:
                os.environ.pop("INGEST_CORPUS", None)
            else:
                os.environ["INGEST_CORPUS"] = old
        self.assertEqual(corpus_id, "path-corpus")

    def test_source_field_never_used_even_when_present(self):
        """The live defect: `source` names the tag file the map was built from, not the corpus. A map
        whose `source` is "world-tags.json" must never produce corpus_id "world-tags"."""
        p = self._map_path(corpus="my-real-corpus", fname="corpus-map.json")
        corpus_id, _label = pipeline.resolve_corpus_id(None, p)
        self.assertEqual(corpus_id, "my-real-corpus")
        self.assertNotEqual(corpus_id, "world-tags")
        self.assertNotIn("world-tags", corpus_id)

    def test_end_to_end_pad_lands_under_corpus_not_source(self):
        """The acceptance case: a pad written via the resolved corpus id lands at
        memory/<corpus>/..., never memory/<source-derived-slug>/...."""
        p = self._map_path(corpus="my-corpus")
        m = pipeline.load(p)
        corpus_id, _label = pipeline.resolve_corpus_id(None, p)
        outcome, path, _detail = pipeline.pad_write(m, corpus_id, self.tmp, entry="hello", basket="alpha")
        self.assertEqual(outcome, "CREATED")
        self.assertIn(os.path.join("memory", "my-corpus"), path)
        self.assertNotIn("world-tags", path)


class TestReadBackGuard(PadWriteCase):
    """`pad_write` must not report success on trust alone."""

    def test_refuses_when_directory_is_unwritable(self):
        m = _map_dict()
        memory_dir = os.path.join(self.tmp, "memory")
        os.makedirs(memory_dir, exist_ok=True)
        os.chmod(memory_dir, 0o500)  # read+execute, no write — os.makedirs for the corpus subdir must fail
        try:
            outcome, path, detail = pipeline.pad_write(
                m, "my-corpus", self.tmp, entry="should not land", basket="alpha")
        finally:
            os.chmod(memory_dir, 0o700)
        self.assertEqual(outcome, "REFUSED")
        self.assertIsNotNone(detail)

    def test_refuses_when_no_root_given_outside_dry_run(self):
        m = _map_dict()
        outcome, path, detail = pipeline.pad_write(m, "my-corpus", None, entry="x", basket="alpha")
        self.assertEqual(outcome, "REFUSED")
        self.assertIsNone(path)

    def test_dry_run_with_no_root_still_previews_entry(self):
        """Dry-run must show exactly what a real run would write, including the entry text."""
        m = _map_dict()
        outcome, path, detail = pipeline.pad_write(
            m, "my-corpus", None, entry="PREVIEW ME", basket="alpha", dry_run=True)
        self.assertEqual(outcome, "CREATED")
        self.assertIn("PREVIEW ME", detail)

    def test_read_back_confirms_entry_present_after_a_clean_write(self):
        m = _map_dict()
        outcome, path, detail = pipeline.pad_write(
            m, "my-corpus", self.tmp, entry="CONFIRM ME", basket="alpha")
        self.assertEqual(outcome, "CREATED")
        self.assertIsNone(detail)

    def test_read_back_catches_a_write_that_did_not_actually_land(self):
        """Simulate a write that raised nothing but left the file without what it should hold — the
        read-back guard, not the write() call, is what must catch this."""
        m = _map_dict()
        outcome, path, _detail = pipeline.pad_write(m, "my-corpus", self.tmp, entry=None, basket="alpha")
        self.assertEqual(outcome, "CREATED")
        # corrupt the file after the fact, then perform an append with no entry — the append-branch
        # placeholder write will land, but the read-back heading check must still fire on the corrupted
        # base content.
        with io.open(path, "w", encoding="utf-8") as f:
            f.write("")
        outcome2, _path2, detail2 = pipeline.pad_write(m, "my-corpus", self.tmp, entry=None, basket="alpha")
        self.assertEqual(outcome2, "REFUSED")
        self.assertIn("read-back", detail2)


class TestGateStaysShut(PadWriteCase):
    """After a REFUSED outcome, the CLI must not call mark_pad_written or save the map."""

    def _map_path(self, corpus="gate-corpus"):
        d = os.path.join(self.tmp, "state", "projects", corpus, "work")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "corpus-map.json")
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(_map_dict(source="world-tags.json"), f)
        return p

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, os.path.join(HERE, "pipeline.py"), "pad-init", *args],
            capture_output=True, text=True)

    def test_refused_corpus_id_resolution_exits_nonzero_and_leaves_gate_shut(self):
        # a map path that does NOT match .../projects/<corpus>/work/<file>.json, no --corpus-id, no env var
        flat = os.path.join(self.tmp, "flat-map.json")
        with io.open(flat, "w", encoding="utf-8") as f:
            json.dump(_map_dict(), f)
        env = dict(os.environ)
        env.pop("INGEST_CORPUS", None)
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "pipeline.py"), "pad-init",
             "--map", flat, "--root", self.tmp, "--basket", "alpha", "--entry", "x"],
            capture_output=True, text=True, env=env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSED", r.stdout + r.stderr)
        with io.open(flat, encoding="utf-8") as f:
            saved = json.load(f)
        self.assertIsNone(saved.get("pad_written"))

    def test_refused_write_exits_nonzero_and_leaves_gate_shut(self):
        p = self._map_path()
        memory_dir = os.path.join(self.tmp, "memory")
        os.makedirs(memory_dir, exist_ok=True)
        os.chmod(memory_dir, 0o500)
        try:
            r = self._run("--map", p, "--root", self.tmp, "--basket", "alpha", "--entry", "x")
        finally:
            os.chmod(memory_dir, 0o700)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("REFUSED", r.stdout + r.stderr)
        with io.open(p, encoding="utf-8") as f:
            saved = json.load(f)
        self.assertIsNone(saved.get("pad_written"))

    def test_a_real_success_case_still_sets_the_gate(self):
        """The control's control: prove the gate CAN open on a genuine success, so the shut-gate tests
        above are proving something real rather than a guard that never opens."""
        p = self._map_path()
        r = self._run("--map", p, "--root", self.tmp, "--basket", "alpha", "--entry", "x")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with io.open(p, encoding="utf-8") as f:
            saved = json.load(f)
        self.assertIsNotNone(saved.get("pad_written"))


class TestPadInitAll(PadWriteCase):
    """The PHASE 1 close path must still work end to end."""

    def test_pad_init_all_creates_one_pad_per_pile_plus_corpus_pad(self):
        m = _map_dict(baskets=("alpha", "beta"))
        results, refused = pipeline.pad_init_all(m, "multi-corpus", self.tmp, now_iso="2026-08-11T00:00:00+00:00")
        self.assertEqual(refused, [])
        self.assertEqual(len(results), 3)  # corpus pad + 2 baskets
        for _b, outcome, path in results:
            self.assertIn(outcome, ("CREATED", "APPENDED"))
            self.assertTrue(os.path.isfile(path), path)

    def test_pad_init_all_never_uses_source_for_the_folder(self):
        m = _map_dict(source="world-tags.json", baskets=("alpha",))
        results, refused = pipeline.pad_init_all(m, "real-corpus", self.tmp)
        self.assertEqual(refused, [])
        for _b, _outcome, path in results:
            self.assertIn(os.path.join("memory", "real-corpus"), path)
            self.assertNotIn("world-tags", path)

    def test_pad_init_all_via_cli_no_basket_no_entry(self):
        d = os.path.join(self.tmp, "state", "projects", "cli-corpus", "work")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "corpus-map.json")
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump(_map_dict(source="world-tags.json", baskets=("alpha", "beta")), f)
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "pipeline.py"), "pad-init",
             "--map", p, "--root", self.tmp],
            capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("cli-corpus", r.stdout)
        with io.open(p, encoding="utf-8") as f:
            saved = json.load(f)
        pw = saved.get("pad_written")
        self.assertIsNotNone(pw)
        self.assertEqual(pw.get("corpus_id"), "cli-corpus")
        self.assertIn(os.path.join("memory", "cli-corpus"), pw.get("path", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
