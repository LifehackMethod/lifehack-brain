#!/usr/bin/env python3
"""Tests for brief 2g: one test per audit blocker (B1-B4) plus the SHOULDs, on sb_spec.py. stdlib unittest.
Each was seen FAILING on the pre-2g code (audit probe, temporary HOME) before the fix."""

import json
import os
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(TESTS_DIR)))))
LIB = os.path.join(REPO, "system", "hooks", "lib")
SID = "g2sess1"
SPEC = """# Draft spec

## 1. WHAT
- Every receipt gets a category before it is filed (D1)
- Receipts are sorted by vendor [inferred]
- The skill reads <[ask] what the skill reads first>

## ROUTED NOTES
D1 · 2026-11-24 · every receipt gets a category before it is filed · the person's words
"""


def load():
    home = tempfile.mkdtemp(prefix="sbspec-2g-")
    os.environ["HOME"] = home
    os.environ["LIFEHACK_REPO_ROOT"] = REPO
    for k in ("LIFEHACK_MODEL_STUB", "SPEC_WRITER_RUNNING"):
        os.environ.pop(k, None)
    if LIB not in sys.path:
        sys.path.insert(0, LIB)
    for m in [k for k in list(sys.modules) if k == "sb_spec"]:
        del sys.modules[m]
    import sb_spec
    return sb_spec, home


class G2Test(unittest.TestCase):
    def setUp(self):
        self.sb, self.home = load()
        self.od = self.sb.od()
        os.makedirs(self.od, exist_ok=True)
        self.wd = os.path.join(self.home, "run")
        os.makedirs(self.wd)
        self.write("draft-spec.md", SPEC)
        with open(os.path.join(self.od, "spec-turn-%s.json" % SID), "w", encoding="utf-8") as f:
            json.dump({"person": ["sort receipts by date, not by vendor"], "all": "PERSON: sort receipts by date, not by vendor"}, f)
        self.cwd = os.path.join(self.home, "cwd")
        os.makedirs(self.cwd)
        self.old_cwd = os.getcwd()
        os.chdir(self.cwd)

    def tearDown(self):
        os.chdir(self.old_cwd)

    def write(self, name, text):
        with open(os.path.join(self.wd, name), "w", encoding="utf-8") as f:
            f.write(text)

    def apply(self, reply, wd=None, off="123"):
        rf = os.path.join(self.home, "reply.txt")
        with open(rf, "w", encoding="utf-8") as f:
            f.write(reply)
        return self.sb.apply_reply(REPO, rf, self.wd if wd is None else wd, SID, off)

    def offset(self):
        return os.path.exists(os.path.join(self.od, "spec-offset-%s" % SID))

    # B1: the model must be able to get the questions from the line itself
    def test_b1_model_line_carries_the_questions_text(self):
        with open(os.path.join(self.od, "spec-saved-%s.txt" % SID), "w", encoding="utf-8") as f:
            f.write("saved 1 spec lines · 0 packet lines\n")
        with open(os.path.join(self.od, "spec-questions-%s.txt" % SID), "w", encoding="utf-8") as f:
            f.write("1. what does it read first?\n2. who files the receipts?\n")
        _s, m = self.sb.gate(SID)    # consume=True renames the questions file in this same call
        self.assertIn("1. what does it read first?", m)
        self.assertIn("2. who files the receipts?", m)
        self.assertNotIn(".txt", m)  # no path to a file that was just renamed away

    # B2: a vanished run folder never writes into the cwd
    def test_b2_empty_run_folder_refuses_and_writes_nothing_in_cwd(self):
        res = self.apply("SAID: sort receipts by date, not by vendor\n---\nEND-WRITE\n", wd="")
        self.assertTrue(res.startswith("FAILED"), res)
        self.assertEqual(os.listdir(self.cwd), [])
        res = self.apply("SAID: x\n---\nEND-WRITE\n", wd=os.path.join(self.home, "gone"))
        self.assertTrue(res.startswith("FAILED"), res)
        self.assertEqual(os.listdir(self.cwd), [])
        self.assertFalse(self.offset())
        self.assertTrue(self.sb.build_questions(REPO, "", os.path.join(self.home, "q.md")).startswith("FAIL"))

    # B3: newest wins on a confirmed (D#) line; one bad line never aborts the others
    def test_b3_confirmed_line_replaced_old_kept_and_others_land(self):
        res = self.apply("""REPLACE: Every receipt gets a category before it is filed
NEW: Categories come later
EVIDENCE: sort receipts by date, not by vendor
---
REPLACE: A line that does not exist anywhere
NEW: nope
EVIDENCE: nope
---
SLOT: <[ask] what the skill reads first>
VALUE: the receipts folder
BY: INFERRED
EVIDENCE: the receipts folder
---
END-WRITE
""")
        self.assertTrue(res.startswith("APPLIED"), res)
        text = open(os.path.join(self.wd, "draft-spec.md"), encoding="utf-8").read()
        self.assertIn("- Categories come later (D2)", text)
        self.assertRegex(text, r"- Every receipt gets a category before it is filed \(superseded \d{4}-\d\d-\d\d\)")
        self.assertIn("the receipts folder [inferred]", text)
        self.assertIn("rejected=1", res)

    # B4: three states; a failure keeps the offset so the next run retries
    def test_b4_all_rejected_is_failed_and_offset_does_not_advance(self):
        res = self.apply("REPLACE: A line that does not exist anywhere\nNEW: nope\nEVIDENCE: nope\n---\nEND-WRITE\n")
        self.assertTrue(res.startswith("FAILED"), res)
        self.assertFalse(self.offset())

    def test_b4_unparseable_reply_is_failed_and_offset_does_not_advance(self):
        res = self.apply("I am sorry, I could not do that.")
        self.assertTrue(res.startswith("FAILED"), res)
        self.assertFalse(self.offset())

    def test_b4_nothing_is_saved_nothing_and_advances(self):
        res = self.apply("NOTHING\nEND-WRITE\n")
        self.assertTrue(res.startswith("APPLIED spec=0 packet=0"), res)
        self.assertTrue(self.offset())

    def test_b4_saved_advances(self):
        res = self.apply("SAID: sort receipts by date, not by vendor\n---\nEND-WRITE\n")
        self.assertIn("packet=1", res)
        self.assertTrue(self.offset())

    # SHOULD: a failed writer leaves a loud gate line, releases no questions
    def test_failed_marker_gives_could_not_save(self):
        with open(os.path.join(self.od, "spec-saved-%s.txt" % SID), "w", encoding="utf-8") as f:
            f.write("FAILED: could not save: 1 record(s) rejected\n")
        s, m = self.sb.gate(SID)
        self.assertIn("COULD NOT SAVE", s)
        self.assertIn("1 record(s) rejected", s)
        self.assertIn("COULD NOT SAVE", m)
        self.assertIn("Ask no new numbered questions", m)

    # SHOULD: SAVED is not shown twice (screen once, model once, a later prompt nothing)
    def test_saved_not_replayed_to_a_later_prompt(self):
        with open(os.path.join(self.od, "spec-saved-%s.txt" % SID), "w", encoding="utf-8") as f:
            f.write("nothing to save\n")
        self.assertTrue(self.sb.gate(SID, window=20, who="screen")[0])
        self.assertTrue(self.sb.gate(SID, window=20, who="model")[1])
        self.assertEqual(self.sb.gate(SID, window=20, who="screen"), (None, None))
        self.assertEqual(self.sb.gate(SID, window=20, who="model"), (None, None))


if __name__ == "__main__":
    unittest.main()
