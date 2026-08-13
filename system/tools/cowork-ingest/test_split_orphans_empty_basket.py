#!/usr/bin/env python3
"""test_split_orphans_empty_basket.py — a basket emptied by a Split correction must never be handed
back as work, and the handoff screen must never print a raw None.

Run:  python3 system/tools/cowork-ingest/test_split_orphans_empty_basket.py

WHY THIS EXISTS — two bugs found running PHASE 1 end to end on a fixture corpus, 2026-08-13.
`corpus_map.py migrate` seeds every chat into UNCLUSTERED before a subject exists (1-sort.md 1.0d),
then re-seeds real piles once the human Splits them out (1.2b, THE MOVE SET's "Split" — every chat
moved out of its auto-tagged basket into named subject piles). `migrate` only ever ADDS/refreshes
basket entries in `m['baskets']` — it never prunes one (deliberately: a stray entry is safer than
silently deleting something a later reader might expect). So once EVERY chat has left UNCLUSTERED, its
basket ENTRY survives with zero member rows, still `basket_status: queued`.

Two symptoms of that one root cause:
  BUG 1 — `pipeline.py phase` named UNCLUSTERED as the next pile to SCAN, and `pipeline.py lock` happily
    locked it for scanning — even though `basket-list --basket UNCLUSTERED --files-only` returns
    nothing. A scan session would open on a pile with nothing in it.
  BUG 2 — `pipeline.py suggest --skill ingest-1`, called right after `sort-confirm` and before
    `pad-init` (1-sort.md step 1.6, BEFORE step 1.10 runs pad-init), printed the literal string
    "...SCAN pile 'None'." straight onto the human-facing close screen.
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
PILES = {"kitchen-tap.txt": "home", "roof-gutter.txt": "home",
         "gas-bill.txt": "money", "isa-vs-savings.txt": "money"}


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="split-orphan-test-")
        self.tags = os.path.join(self.tmp, "world-tags.json")
        self.map = os.path.join(self.tmp, "corpus-map.json")
        rows = [{"file": f, "categories": ["canon"], "freshness": "fresh"} for f in PILES]
        with io.open(self.tags, "w", encoding="utf-8") as fh:
            json.dump({"rows": rows}, fh)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, tool, *args, expect_ok=True):
        r = subprocess.run([sys.executable, os.path.join(HERE, tool), *args],
                           capture_output=True, text=True)
        if expect_ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def split_every_chat_out_of_unclustered(self):
        """Exactly THE MOVE SET's Split, over the WHOLE corpus — 1-sort.md 1.0d, 1.2, 1.2b."""
        self.run_tool("corpus_map.py", "init", "--tags", self.tags, "--out", self.map)
        self.run_tool("corpus_map.py", "migrate", "--map", self.map)          # 1.0d — all UNCLUSTERED
        for f, subject in PILES.items():
            self.run_tool("corpus_map.py", "set", "--map", self.map, "--file", f, "--subject", subject)
        self.run_tool("corpus_map.py", "migrate", "--map", self.map)          # 1.2b — re-seed real piles


class TestEmptyBasketNeverNamedOrLocked(Case):
    """BUG 1."""

    def test_unclustered_survives_the_map_with_zero_chats(self):
        """Sanity: the orphan really is there, and really is empty — the premise of this whole file."""
        self.split_every_chat_out_of_unclustered()
        with io.open(self.map, encoding="utf-8") as fh:
            m = json.load(fh)
        self.assertIn("UNCLUSTERED", m["baskets"])
        self.assertEqual([f for f, r in m["rows"].items() if r["basket"] == "UNCLUSTERED"], [])

    def test_phase_never_names_the_empty_basket(self):
        self.split_every_chat_out_of_unclustered()
        self.run_tool("pipeline.py", "sort-confirm", "--map", self.map, "--human-approved")
        self.run_tool("pipeline.py", "pad-init", "--map", self.map, "--root",
                      os.path.join(self.tmp, "notes"), "--corpus-id", "test-corpus")
        r = self.run_tool("pipeline.py", "phase", "--map", self.map)
        ph, basket = r.stdout.strip().split("|", 1)
        self.assertNotEqual(basket, "UNCLUSTERED",
                            "phase named the empty basket as the next pile to scan: %r" % r.stdout)

    def test_basket_list_on_the_orphan_really_is_empty(self):
        """The other half of the symptom: if it WERE named, there'd be nothing to scan there."""
        self.split_every_chat_out_of_unclustered()
        r = self.run_tool("pipeline.py", "basket-list", "--map", self.map,
                          "--basket", "UNCLUSTERED", "--files-only")
        self.assertEqual(r.stdout.strip(), "")

    def test_lock_refuses_the_empty_basket(self):
        self.split_every_chat_out_of_unclustered()
        r = self.run_tool("pipeline.py", "lock", "--map", self.map, "--basket", "UNCLUSTERED",
                          "--machine", "test-machine", "--skill", "ingest-2",
                          "--now", "2026-08-13T12:00:00+00:00", expect_ok=False)
        self.assertNotEqual(r.returncode, 0,
                            "lock succeeded on a basket with zero member chats: %r" % r.stdout)


class TestSuggestNeverPrintsNone(Case):
    """BUG 2 — the literal string that reaches the human's screen."""

    def test_suggest_after_sort_confirm_names_a_real_basket(self):
        """The exact call site: 1-sort.md 1.6 runs `suggest --skill ingest-1` right after
        `sort-confirm`, BEFORE `pad-init` (1.10) — no --basket, nothing else has run yet."""
        self.split_every_chat_out_of_unclustered()
        self.run_tool("pipeline.py", "sort-confirm", "--map", self.map, "--human-approved")
        r = self.run_tool("pipeline.py", "suggest", "--map", self.map, "--skill", "ingest-1")
        self.assertNotIn("None", r.stdout, "suggest printed a literal None: %r" % r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
