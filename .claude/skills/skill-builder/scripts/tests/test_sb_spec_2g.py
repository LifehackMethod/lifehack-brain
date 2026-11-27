#!/usr/bin/env python3
"""Tests for brief 2g, kept through 2c: one test per audit blocker that still applies (B2 never writes into the cwd, B3 newest wins
on a confirmed line, B4 saved / nothing / FAILED) on sb_spec.py. B1 (a questions file renamed before it is read) and the gate
SHOULDs went with the gate itself in 2c: there is no gate and no questions file to rename. stdlib unittest."""

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
    os.environ.pop("LIFEHACK_MODEL_STUB", None)
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
        with open(os.path.join(self.home, "evidence.json"), "w", encoding="utf-8") as f:   # beside the reply file
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

    def apply(self, reply, wd=None):
        rf = os.path.join(self.home, "reply.txt")
        with open(rf, "w", encoding="utf-8") as f:
            f.write(reply)
        return self.sb.apply_reply(REPO, rf, self.wd if wd is None else wd, SID)

    # B2: a vanished run folder never writes into the cwd
    def test_b2_empty_run_folder_refuses_and_writes_nothing_in_cwd(self):
        res = self.apply("SAID: sort receipts by date, not by vendor\n---\nEND-WRITE\n", wd="")
        self.assertTrue(res.startswith("FAILED"), res)
        self.assertEqual(os.listdir(self.cwd), [])
        res = self.apply("SAID: x\n---\nEND-WRITE\n", wd=os.path.join(self.home, "gone"))
        self.assertTrue(res.startswith("FAILED"), res)
        self.assertEqual(os.listdir(self.cwd), [])
        self.assertTrue(self.sb.build_turn_input(REPO, "", SID, os.path.join(self.home, "turn"), "x", "").startswith("FAIL"))

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

    # B4: three states; a failure leaves no receipt, so the next turn's input carries those words again (test_sb_waves)
    def test_b4_all_rejected_is_failed(self):
        res = self.apply("REPLACE: A line that does not exist anywhere\nNEW: nope\nEVIDENCE: nope\n---\nEND-WRITE\n")
        self.assertTrue(res.startswith("FAILED"), res)

    def test_b4_unparseable_reply_is_failed(self):
        res = self.apply("I am sorry, I could not do that.")
        self.assertTrue(res.startswith("FAILED"), res)

    def test_b4_nothing_is_saved_nothing(self):
        res = self.apply("NOTHING\nEND-WRITE\n")
        self.assertTrue(res.startswith("APPLIED spec=0 packet=0"), res)

    def test_b4_saved_says_how_many(self):
        res = self.apply("SAID: sort receipts by date, not by vendor\n---\nEND-WRITE\n")
        self.assertIn("packet=1", res)


if __name__ == "__main__":
    unittest.main()
