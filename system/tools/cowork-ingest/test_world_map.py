#!/usr/bin/env python3
"""test_world_map.py — the phase-3 world map, both directions.

WHY THIS FILE EXISTS. The world map is the reward and the verification of the whole ingest:
the human reads a paragraph about themselves, corrects what is wrong, and rules where each
finding belongs. Every piece of it was built — the shape check, the fabrication check, the
batcher, the four turn outcomes, the type proposer — and NONE of it had a test. A gate
nobody has watched refuse is a gate nobody has tested, and three of the five pieces below
exist *because a specific failure was measured*:

  - the prose-not-a-list rule: "a wrong sentence about someone jumps out; wrong item
    fourteen of twenty does not". A list marker slipping through defeats the turn.
  - the fabrication check: a helper told to use real data returned a fluent paragraph about
    a person who does not exist, with figures that appear nowhere in the corpus. It
    satisfied its instruction in letter. Containment is what is enforceable.
  - the turn-outcome closed set: a keyword classifier caught 0 of 3 corrections, including
    this skill's own worked example — so the single highest-value thing a human produces
    was the one input it could not hear. Membership is code's half; meaning is the model's.

Run: python3 system/tools/cowork-ingest/test_world_map.py
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pipeline  # noqa: E402


class TestParagraphShape(unittest.TestCase):
    """check_world_map_paragraph — SHAPE only. It never rewrites or improves the text."""

    TITLE = None

    def setUp(self):
        self.title = pipeline.world_map_title("alpha")

    def body(self, *paragraphs):
        return self.title + "\n\n" + "\n\n".join(paragraphs) + "\n"

    P1 = ("They think in systems and keep coming back to the same three questions across a "
          "year of notes.")
    P2 = ("When a decision is hard they write it out longhand first and then argue with "
          "what they wrote.")

    # ---- the catch side ----

    def test_missing_title_refuses(self):
        ok, msg = pipeline.check_world_map_paragraph(self.P1, "alpha", self.P1)
        self.assertFalse(ok)
        self.assertIn("missing the required title", msg)

    def test_zero_paragraphs_refuses(self):
        ok, msg = pipeline.check_world_map_paragraph(self.title + "\n\n", "alpha", "x")
        self.assertFalse(ok)
        self.assertIn("paragraph(s) found", msg)

    def test_five_paragraphs_refuses(self):
        text = self.body(*[self.P1] * 5)
        ok, msg = pipeline.check_world_map_paragraph(text, "alpha", self.P1)
        self.assertFalse(ok)
        self.assertIn("5 paragraph(s) found", msg)

    def test_every_list_marker_refuses(self):
        """The one mechanical choice in this phase that is not negotiable on taste."""
        for marker in ("- ", "* ", "+ ", "1. ", "2) "):
            with self.subTest(marker=marker):
                text = self.body(self.P1 + "\n" + marker + "a listed thing")
                ok, msg = pipeline.check_world_map_paragraph(text, "alpha", self.P1)
                self.assertFalse(ok, "%r was accepted as prose" % marker)
                self.assertIn("prose only, never a list", msg)

    # ---- the no-false-positive side; a guard that only ever fires is not a guard ----

    def test_one_paragraph_passes(self):
        ok, msg = pipeline.check_world_map_paragraph(
            self.body(self.P1), "alpha", self.P1)
        self.assertTrue(ok, msg)

    def test_four_paragraphs_passes(self):
        text = self.body(self.P1, self.P2, self.P1, self.P2)
        ok, msg = pipeline.check_world_map_paragraph(text, "alpha", self.P1 + " " + self.P2)
        self.assertTrue(ok, msg)

    def test_a_hyphen_inside_a_sentence_is_not_a_list(self):
        """'well-worn' and an em-dash aside must survive, or the check becomes noise."""
        prose = ("Their well-worn habit — writing longhand before deciding — shows up in "
                 "note after note.")
        ok, msg = pipeline.check_world_map_paragraph(
            self.body(prose), "alpha", prose)
        self.assertTrue(ok, msg)


class TestContainmentIsNotOptional(unittest.TestCase):
    """The fabrication check. A paragraph is about a real person or it is not shown."""

    def setUp(self):
        self.title = pipeline.world_map_title("alpha")

    def test_no_material_is_not_a_pass(self):
        """SHAPE-ONLY must SAY it verified nothing. Silence here is how a fabricated map
        reaches a human wearing a green tick."""
        text = self.title + "\n\nThey think in systems.\n"
        ok, msg = pipeline.check_world_map_paragraph(text, "alpha", None)
        self.assertTrue(ok)
        self.assertIn("SHAPE ONLY", msg)
        self.assertIn("NO CONTAINMENT CHECK RAN", msg)

    def test_a_figure_absent_from_the_material_refuses(self):
        """The measured incident: 40,000 words of interviews that were never in the corpus."""
        material = "notes about a film shoot and the schedule around it"
        text = self.title + "\n\nThey wrote 40,000 words of interviews about it.\n"
        ok, msg = pipeline.check_world_map_paragraph(text, "alpha", material)
        self.assertFalse(ok)
        self.assertIn("40,000", msg)
        self.assertIn("fabrication", msg)

    def test_a_figure_present_in_the_material_passes(self):
        material = "the shoot ran 12 days across two locations"
        text = self.title + "\n\nThe shoot ran 12 days across two locations.\n"
        ok, msg = pipeline.check_world_map_paragraph(text, "alpha", material)
        self.assertTrue(ok, msg)

    def test_unsupported_words_warn_but_do_not_block(self):
        """Deliberately NOT a threshold: it surfaces the terms so a human sees them. Only a
        number with no source is unambiguous enough to refuse on."""
        material = "notes about a film shoot"
        text = self.title + "\n\nThey kept returning to questions about memoir and notebooks.\n"
        ok, msg = pipeline.check_world_map_paragraph(text, "alpha", material)
        self.assertTrue(ok, msg)
        self.assertIn("appear nowhere in the pile's", msg)

    def test_coverage_is_reported(self):
        material = "they think in systems and write longhand"
        text = self.title + "\n\nThey think in systems and write longhand.\n"
        _unsupported, bad, coverage = pipeline.world_map_unsupported_terms(text, material)
        self.assertEqual(bad, [])
        self.assertGreater(coverage, 0.5)


class TestPagination(unittest.TestCase):
    """paginate_items — the count decides. One batcher, shared with phase 2's chat batcher."""

    def test_empty_in_empty_out(self):
        self.assertEqual(pipeline.paginate_items([]), [])

    def test_under_the_cap_is_one_page(self):
        self.assertEqual(len(pipeline.paginate_items(list(range(10)))), 1)

    def test_one_over_the_cap_splits(self):
        pages = pipeline.paginate_items(list(range(11)))
        self.assertEqual(len(pages), 2)
        self.assertEqual(len(pages[0]), 10)
        self.assertEqual(len(pages[1]), 1)

    def test_no_page_is_ever_empty(self):
        for n in range(1, 35):
            with self.subTest(n=n):
                pages = pipeline.paginate_items(list(range(n)))
                self.assertTrue(all(pages), "an empty page for n=%d" % n)
                self.assertEqual(sum(len(p) for p in pages), n)


class TestTurnOutcome(unittest.TestCase):
    """MEMBERSHIP ONLY. The model decides what a reply meant; this only checks the answer
    is a legal member — so an unrecognised one can never be promoted to APPROVE."""

    def test_every_legal_move_is_accepted(self):
        for v in ("APPROVE", "NOTE_AND_MOVE_ON", "REFINE_AND_REPEAT", "NO_OUTCOME"):
            with self.subTest(v=v):
                ok, val, _msg = pipeline.validate_turn_outcome(v)
                self.assertTrue(ok)
                self.assertEqual(val, v)

    def test_an_off_list_answer_is_refused_not_guessed(self):
        for v in ("yes", "ok", "sure", "APPROVED", "", None, "approve please"):
            with self.subTest(v=v):
                ok, val, msg = pipeline.validate_turn_outcome(v)
                self.assertFalse(ok, "%r was accepted" % v)
                self.assertIsNone(val)
                self.assertIn("REFUSED", msg)

    def test_nothing_off_list_ever_becomes_approve(self):
        """The structural invariant, stated as a test rather than as a comment."""
        for v in ("yeah that's right", "fine", "APPROVE_ALL", "no_outcome"):
            ok, val, _ = pipeline.validate_turn_outcome(v)
            self.assertNotEqual(val, "APPROVE", "%r reached APPROVE" % v)


class TestFindingTypeProposal(unittest.TestCase):
    """propose_finding_type — a deterministic FIRST bucket only. The human still rules."""

    def test_a_historical_record_proposes_record(self):
        self.assertEqual(
            pipeline.propose_finding_type({"suggested_category": "historical-record"}),
            "record")

    def test_a_dated_finding_proposes_dated(self):
        self.assertEqual(
            pipeline.propose_finding_type({"suggested_category": "craft",
                                           "freshness": "dated"}),
            "dated")

    def test_an_empty_finding_still_returns_a_legal_type(self):
        """Fail-safe, not fail-silent: an unclassifiable finding still lands in a turn where
        the human can see and rule it, rather than vanishing between the three."""
        self.assertIn(pipeline.propose_finding_type({}),
                      ("canonical", "dated", "record"))


if __name__ == "__main__":
    unittest.main(verbosity=1)
