#!/usr/bin/env python3
"""test_sort_to_baskets.py — the piles a person sorts into have to become real baskets.

Run:  python3 system/tools/cowork-ingest/test_sort_to_baskets.py

WHY THIS EXISTS — found by driving PHASE 1 end to end on a fixture corpus, 2026-08-11.
PHASE 1 runs `migrate` at step 1.0d, before any chat has a subject, so every row is seeded into
`UNCLUSTERED`. It then sorts chats into piles (1.2, writing `subject`) and tells you to "re-migrate to
seed the new baskets" (1.2b). The re-migrate did nothing, because the guard was `if not r.get("basket")`
and the string `"UNCLUSTERED"` is not falsy. So a corpus sorted into five piles stayed one basket, and
`pad-init` — documented as "one pad PER PILE" — wrote a single pad.

Nothing errored. That is what made it worth a test: the run looked fine at every step.
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
PILES = {"kitchen-tap.txt": "home", "roof-gutter.txt": "home", "gas-bill.txt": "money",
         "isa-vs-savings.txt": "money", "couch-to-5k.txt": "health", "sourdough.txt": "cooking"}


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sort-baskets-test-")
        self.tags = os.path.join(self.tmp, "world-tags.json")
        self.map = os.path.join(self.tmp, "corpus-map.json")
        rows = [{"file": f, "categories": ["canon"], "freshness": "fresh"} for f in PILES]
        with io.open(self.tags, "w", encoding="utf-8") as fh:
            json.dump({"rows": rows}, fh)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, tool, *args):
        r = subprocess.run([sys.executable, os.path.join(HERE, tool), *args],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def phase_one(self):
        """Exactly the order PHASE 1 runs in: init, migrate, sort, re-migrate."""
        self.run_tool("corpus_map.py", "init", "--tags", self.tags, "--out", self.map)
        self.run_tool("corpus_map.py", "migrate", "--map", self.map)
        for f, subject in PILES.items():
            self.run_tool("corpus_map.py", "set", "--map", self.map, "--file", f, "--subject", subject)
        self.run_tool("corpus_map.py", "migrate", "--map", self.map)
        with io.open(self.map, encoding="utf-8") as fh:
            return json.load(fh)


class TestPilesBecomeBaskets(Case):

    def test_every_chat_lands_in_its_pile(self):
        m = self.phase_one()
        for f, subject in PILES.items():
            self.assertEqual(m["rows"][f]["basket"], subject,
                             "%s should be in basket %r" % (f, subject))

    def test_the_baskets_section_lists_every_pile(self):
        m = self.phase_one()
        self.assertEqual(set(m["baskets"]) - {"UNCLUSTERED"}, set(PILES.values()))

    def test_nothing_is_left_unclustered(self):
        """The symptom as it actually presented: everything in one giant basket."""
        m = self.phase_one()
        stuck = [f for f, r in m["rows"].items() if r["basket"] == "UNCLUSTERED"]
        self.assertEqual(stuck, [], "these never left UNCLUSTERED")

    def test_a_chat_with_no_pile_stays_unclustered(self):
        """Re-seeding must not invent a pile for something the human has not sorted."""
        self.run_tool("corpus_map.py", "init", "--tags", self.tags, "--out", self.map)
        self.run_tool("corpus_map.py", "migrate", "--map", self.map)
        self.run_tool("corpus_map.py", "set", "--map", self.map, "--file", "gas-bill.txt",
                      "--subject", "money")
        self.run_tool("corpus_map.py", "migrate", "--map", self.map)
        with io.open(self.map, encoding="utf-8") as fh:
            m = json.load(fh)
        self.assertEqual(m["rows"]["gas-bill.txt"]["basket"], "money")
        self.assertEqual(m["rows"]["sourdough.txt"]["basket"], "UNCLUSTERED")

    def test_an_existing_real_basket_is_never_overwritten(self):
        """Only UNCLUSTERED gets re-seeded. A basket somebody deliberately set stays put."""
        m = self.phase_one()
        with io.open(self.map, encoding="utf-8") as fh:
            raw = json.load(fh)
        raw["rows"]["gas-bill.txt"]["basket"] = "deliberately-elsewhere"
        with io.open(self.map, "w", encoding="utf-8") as fh:
            json.dump(raw, fh)
        self.run_tool("corpus_map.py", "migrate", "--map", self.map)
        with io.open(self.map, encoding="utf-8") as fh:
            after = json.load(fh)
        self.assertEqual(after["rows"]["gas-bill.txt"]["basket"], "deliberately-elsewhere")

    def test_migrate_is_still_idempotent(self):
        m1 = self.phase_one()
        self.run_tool("corpus_map.py", "migrate", "--map", self.map)
        self.run_tool("corpus_map.py", "migrate", "--map", self.map)
        with io.open(self.map, encoding="utf-8") as fh:
            m2 = json.load(fh)
        self.assertEqual({f: r["basket"] for f, r in m1["rows"].items()},
                         {f: r["basket"] for f, r in m2["rows"].items()})


class TestOnePadPerPile(Case):
    """The user-visible consequence: pad-init is documented as one pad per pile."""

    def test_a_pad_per_pile_plus_the_corpus_pad(self):
        self.phase_one()
        root = os.path.join(self.tmp, "notes")
        os.makedirs(root)
        # ⛔ 2026-08-11 D1.2.1: this fixture's map is a flat tmp path, not shaped like
        # .../projects/<corpus>/work/<file>.json, so the corpus id can no longer be resolved from the
        # path (and must never be guessed from `source`, which corpus_map.py sets to "world-tags.json"
        # here — that names the tag file, not the corpus). --corpus-id makes the resolution explicit,
        # same as a real caller whose map does not live under a `projects/` tree would have to.
        self.run_tool("pipeline.py", "pad-init", "--map", self.map, "--root", root,
                      "--corpus-id", "test-corpus")
        pads = set()
        for dirpath, _dirnames, filenames in os.walk(root):
            for f in filenames:
                if f == "scratchpad.md":
                    pads.add(os.path.relpath(os.path.join(dirpath, f), root))
        self.assertGreaterEqual(len(pads), len(set(PILES.values())),
                                "expected one pad per pile plus the corpus pad, got: %s" % sorted(pads))
        for subject in set(PILES.values()):
            # issue #79: `p` comes from os.path.relpath, which on Windows joins with `\`, so
            # "/%s/" % subject never matches "\subject\" there — normalize separators to `/` before
            # comparing rather than assuming POSIX-style paths.
            self.assertTrue(
                any(("/%s/" % subject) in ("/" + p.replace(os.sep, "/")) for p in pads),
                "no pad for pile %r among %s" % (subject, sorted(pads)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
