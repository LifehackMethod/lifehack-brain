#!/usr/bin/env python3
"""Tests for sb_spec.py apply_reply REPLACE + inferred marks (brief 2f, §6 test 2). stdlib unittest."""

import json
import os
import re
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(TESTS_DIR)))))
LIB = os.path.join(REPO, "system", "hooks", "lib")


def load():
    home = tempfile.mkdtemp(prefix="sbspec-repl-")
    os.environ["HOME"] = home
    os.environ.pop("SPEC_WRITER_RUNNING", None)
    if LIB not in sys.path:
        sys.path.insert(0, LIB)
    import sb_spec
    return sb_spec, home


SPEC = """# Draft spec

## 1. WHAT
- Every receipt gets a category before it is filed (D1)
- Receipts are sorted by vendor [inferred]
- The skill reads <[ask] what the skill reads first>

## ROUTED NOTES
D1 · 2026-11-24 · every receipt gets a category before it is filed · the person's words
"""


def setup(sb, wd, spec_text, person):
    os.makedirs(wd, exist_ok=True)
    with open(os.path.join(wd, "draft-spec.md"), "w", encoding="utf-8") as f:
        f.write(spec_text)
    od = sb.od()
    os.makedirs(od, exist_ok=True)
    with open(os.path.join(od, "spec-turn-%s.json" % SID), "w", encoding="utf-8") as f:
        json.dump({"person": [person], "all": "PERSON: " + person}, f)


SID = "replSess1"


def run_apply(sb, wd, reply):
    rf = os.path.join(wd, "_reply.md")
    with open(rf, "w", encoding="utf-8") as f:
        f.write(reply)
    return sb.apply_reply(REPO, rf, wd, SID, "")


class ReplaceTest(unittest.TestCase):
    def setUp(self):
        self.sb, self.home = load()
        self.wd = os.path.join(self.home, "run")
        setup(self.sb, self.wd, SPEC, "sort receipts by date, not by vendor")

    def test_replace_swaps_and_keeps_old_line(self):
        res = run_apply(self.sb, self.wd, """REPLACE: Receipts are sorted by vendor
NEW: Receipts are sorted by date, oldest first
EVIDENCE: sort receipts by date, not by vendor
---
END-WRITE
""")
        self.assertTrue(res.startswith("APPLIED"), res)
        text = open(os.path.join(self.wd, "draft-spec.md"), encoding="utf-8").read()
        self.assertIn("- Receipts are sorted by date, oldest first", text)
        self.assertIn("- Receipts are sorted by vendor [inferred] (superseded ", text)
        self.assertLess(text.index("sorted by date, oldest first"), text.index("(superseded "))

    def test_replace_without_person_words_gets_inferred(self):
        run_apply(self.sb, self.wd, """REPLACE: Receipts are sorted by vendor
NEW: Receipts are sorted by month
EVIDENCE: the receipts come in monthly folders
---
END-WRITE
""")
        text = open(os.path.join(self.wd, "draft-spec.md"), encoding="utf-8").read()
        self.assertIn("- Receipts are sorted by month [inferred]", text)

    def test_replace_on_confirmed_line_is_newest_wins_and_never_aborts_the_rest(self):
        # 2g B3: the person changed their mind about a confirmed (D1) line: replace it, keep the old text beneath
        # marked superseded, and the same write's other records still land
        res = run_apply(self.sb, self.wd, """REPLACE: Every receipt gets a category before it is filed
NEW: Categories come later
EVIDENCE: sort receipts by date
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
        self.assertIn("- Categories come later", text)
        self.assertIn("the receipts folder [inferred]", text)
        self.assertRegex(text, r"- Every receipt gets a category before it is filed \(superseded \d{4}-\d\d-\d\d\)")
        self.assertLess(text.index("Categories come later"), text.index("(superseded "))
        self.assertIn("REPLACED", open(os.path.join(self.wd, "spec-evidence.md"), encoding="utf-8").read())

    def test_inferred_added_by_code_only(self):
        # the writer typing the mark itself is harmless: code strips and re-adds
        run_apply(self.sb, self.wd, """SLOT: <[ask] what the skill reads first>
VALUE: the receipts folder [inferred]
BY: INFERRED
EVIDENCE: the receipts folder
---
END-WRITE
""")
        text = open(os.path.join(self.wd, "draft-spec.md"), encoding="utf-8").read()
        self.assertNotIn("<[ask]", text)
        self.assertIn("the receipts folder [inferred]", text)

    def test_no_silent_delete(self):
        # a replace is the ONLY way a line changes: a record naming a non-existent line is rejected, nothing removed
        res = run_apply(self.sb, self.wd, """REPLACE: Receipts are filed in lavender folders
NEW: Receipts are filed in blue folders
EVIDENCE: blue folders please
---
END-WRITE
""")
        text = open(os.path.join(self.wd, "draft-spec.md"), encoding="utf-8").read()
        for line in SPEC.splitlines():
            self.assertIn(line, text)
        self.assertIn("REJECTED replace", open(os.path.join(self.wd, "spec-evidence.md"), encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
