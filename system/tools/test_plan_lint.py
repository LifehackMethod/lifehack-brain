#!/usr/bin/env python3
"""
test_plan_lint.py — regression tests for card 0R.15.

Covers, in order:
  (1) plan_lint.py now recognises a DIGIT-THEN-LETTER phase id (`0R.15`, `0N.2`, `0R.E1`,
      `0R.8a`) as a full card id — and every previously-recognised shape (`3b.1`, `6.12`,
      `B2.0`) still matches unchanged.
  (2) an unparseable `- [ ] **` card header is a HARD FAIL (CANNOT-READ, rc=4) — never one
      line folded into the ordinary per-card `defects` list.
  (3) a card whose `Owner:` names BUILD may not also carry an undecided instruction
      (`rule each one`, `decide`, `establish which`) — flagged; a non-BUILD owner or a
      BUILD-owned card with no such phrase is not.
  (4) the mixed `Owner: NAV to specify (done, this card), BUILD to implement` phrasing (and
      the plain `NAV to specify, BUILD to implement` form) is recognised as containing BUILD
      for rule (3) — never missed the way a grep keyed to a closed set of "sanctioned"
      strings would miss it (the same failure class the ID pattern in (1)/(2) already had).

Run:  python3 system/tools/test_plan_lint.py -v
"""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plan_lint       # noqa: E402
import verify_parse    # noqa: E402

PLAN_LINT_PY = os.path.join(HERE, "plan_lint.py")
MALFORMED_FIXTURE = os.path.normpath(os.path.join(
    HERE, "..", "..", ".claude", "skills", "autoplan", "fixtures", "malformed_header.plan.md"))

# A proven-good SHAPE Verify clause -- the exact shape verify_parse.py's own _self_smoke()
# already proves parses cleanly (module-level ok_lines[0]), so a test failure here can never
# be blamed on this scaffolding.
GOOD_VERIFY = ('  `Verify: SHAPE` — `grep -c "x" system/tools/pulse_alert.py` '
               '→ before `0`, after `1`.')


def card_lines(cid, owner="Owner: BUILD", do="do the work."):
    """One minimal, otherwise-clean card: `Repo: none` so no Commit:/branch checks fire, an
    absolute `Where:` so the path-shape check passes, and GOOD_VERIFY so only the rule under
    test can produce a defect."""
    return [
        f"- [ ] **{cid} Synthetic card.** `{owner}`",
        "  `Where: /tmp/fixture/does-not-need-to-exist.py`",
        f"  `Do:` {do}",
        "  `Repo: none`",
        GOOD_VERIFY,
        "  `Done: Verify passes (re-run by plan_retire.py) → retire`",
    ]


def make_plan(card_blocks):
    lines = [
        "# Plan: synthetic fixture",
        "",
        "**Desired outcome:** exercise plan_lint.py for card 0R.15's regression tests.",
        "",
        "> **Review:** SKIPPED 2026-09-16 synthetic test fixture, no six-lens needed.",
        "",
        "## Phase 1 -- synthetic",
        "",
    ]
    for block in card_blocks:
        lines.extend(block)
        lines.append("")
    return "\n".join(lines)


def write_plan(tmpdir, name, card_blocks):
    path = os.path.join(tmpdir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(make_plan(card_blocks))
    return path


class WidenedPhaseId(unittest.TestCase):
    """(1) digit-then-letter phase ids, and the older forms that must keep matching."""

    def test_new_digit_then_letter_forms_match_in_full(self):
        for cid in ("0R.15", "0N.2", "0R.E1", "0R.8a"):
            with self.subTest(cid=cid):
                m = verify_parse.CARD_ID_RE.match(f"- [ ] **{cid} Some title.**")
                self.assertIsNotNone(m, f"{cid!r} was not matched at all")
                self.assertEqual(m.group(1), cid, f"{cid!r} matched only {m.group(1)!r}")

    def test_older_forms_still_match_in_full(self):
        for cid in ("3b.1", "6.12", "2.3", "B2.0", "1.1"):
            with self.subTest(cid=cid):
                m = verify_parse.CARD_ID_RE.match(f"- [ ] **{cid} Some title.**")
                self.assertIsNotNone(m, f"{cid!r} regressed -- no match")
                self.assertEqual(m.group(1), cid)

    def test_parse_cards_recognises_new_forms_with_no_unrecognised(self):
        ids = ("0R.15", "0N.2", "0R.E1", "0R.8a")
        lines = []
        for cid in ids:
            lines.append(f"- [ ] **{cid} Some title.** `Owner: BUILD`")
            lines.append("  `Where: /tmp/x`")
        cards, unrecognised = plan_lint.parse_cards(lines)
        self.assertEqual(unrecognised, [])
        self.assertEqual([c["id"] for c in cards], list(ids))


class UnparseableHeaderHardFail(unittest.TestCase):
    """(2) an unparseable header is CANNOT-READ (rc=4), never folded into `defects`."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_malformed_header_hard_fails_in_process(self):
        good = card_lines("1.1")
        bad_header = ["- [ ] **BROKEN-ID Not a real id.** `Owner: BUILD`",
                       "  `Where: /tmp/x`"]
        path = write_plan(self.tmp.name, "malformed.plan.md", [good, bad_header])
        with self.assertRaises(SystemExit) as cm:
            plan_lint.lint(path, [])
        self.assertEqual(cm.exception.code, plan_lint.CANNOT_READ)

    def test_clean_plan_does_not_hard_fail(self):
        path = write_plan(self.tmp.name, "clean.plan.md", [card_lines("1.1")])
        cards, defects = plan_lint.lint(path, [])
        self.assertEqual([c["id"] for c in cards], ["1.1"])
        self.assertEqual(defects, [])

    def test_repo_fixture_exists(self):
        self.assertTrue(os.path.exists(MALFORMED_FIXTURE),
                         f"missing fixture: {MALFORMED_FIXTURE}")

    def test_cli_rc_is_cannot_read_on_repo_fixture(self):
        r = subprocess.run([sys.executable, PLAN_LINT_PY, MALFORMED_FIXTURE],
                            capture_output=True, text=True, timeout=30)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.returncode, plan_lint.CANNOT_READ, r.stdout + r.stderr)
        self.assertIn("CANNOT-READ", r.stdout)


class BuildOwnerUndecidedInstruction(unittest.TestCase):
    """(3) Owner: BUILD + an undecided phrase is flagged; (4) the mixed NAV/BUILD owner
    phrasing is recognised as containing BUILD for that same rule."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _defects_for(self, owner, do):
        path = write_plan(self.tmp.name, "case.plan.md",
                           [card_lines("1.1", owner=owner, do=do)])
        _, defects = plan_lint.lint(path, [])
        return defects

    @staticmethod
    def _has_undecided_defect(defects):
        return any("undecided instruction" in msg for _, msg in defects)

    def test_build_owner_with_each_undecided_phrase_is_flagged(self):
        for phrase in ("decide which config wins.",
                       "rule each one on its own merits.",
                       "establish which branch is authoritative."):
            with self.subTest(phrase=phrase):
                defects = self._defects_for("Owner: BUILD", phrase)
                self.assertTrue(self._has_undecided_defect(defects),
                                 f"no undecided-instruction defect for {phrase!r}: {defects}")

    def test_build_owner_with_no_undecided_phrase_is_clean(self):
        defects = self._defects_for("Owner: BUILD", "widen the regex and ship it.")
        self.assertEqual(defects, [])

    def test_non_build_owner_with_undecided_phrase_is_not_flagged_by_this_rule(self):
        defects = self._defects_for("Owner: NAV", "decide which config wins.")
        self.assertFalse(self._has_undecided_defect(defects), defects)

    def test_mixed_owner_variant_with_parenthetical_is_recognised_as_build(self):
        owner = "Owner: NAV to specify (done, this card), BUILD to implement"
        defects = self._defects_for(owner, "decide which config wins.")
        self.assertTrue(self._has_undecided_defect(defects), defects)

    def test_mixed_owner_variant_plain_is_recognised_as_build(self):
        owner = "Owner: NAV to specify, BUILD to implement"
        defects = self._defects_for(owner, "decide which config wins.")
        self.assertTrue(self._has_undecided_defect(defects), defects)

    def test_mixed_owner_variant_with_no_undecided_phrase_is_clean(self):
        owner = "Owner: NAV to specify (done, this card), BUILD to implement"
        defects = self._defects_for(owner, "widen the regex and ship it.")
        self.assertEqual(defects, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
