#!/usr/bin/env python3
"""Tests for sb_spec.py packet-record apply (brief 2f, §6 test 3). stdlib unittest."""

import json
import os
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(TESTS_DIR)))))
LIB = os.path.join(REPO, "system", "hooks", "lib")
SID = "pktSess1"

SPEC = """# Draft spec

## 1. WHAT
- Every receipt gets a category before it is filed (D1)
"""


def load():
    home = tempfile.mkdtemp(prefix="sbspec-pkt-")
    os.environ["HOME"] = home
    if LIB not in sys.path:
        sys.path.insert(0, LIB)
    import sb_spec
    return sb_spec, home


def setup(sb, wd, notes="", rulings="", research=""):
    os.makedirs(wd, exist_ok=True)
    with open(os.path.join(wd, "draft-spec.md"), "w", encoding="utf-8") as f:
        f.write(SPEC)
    for name, body in (("notes.md", notes), ("rulings.md", rulings), ("research.md", research)):
        with open(os.path.join(wd, name), "w", encoding="utf-8") as f:
            f.write(body)
    person = "it should also tell me when a receipt has no date"
    with open(os.path.join(wd, "evidence.json"), "w", encoding="utf-8") as f:   # 2c: the evidence sits beside the reply file
        json.dump({"person": [person], "all": "PERSON: " + person}, f)
    return person


def run_apply(sb, wd, reply):
    rf = os.path.join(wd, "_reply.md")
    with open(rf, "w", encoding="utf-8") as f:
        f.write(reply)
    return sb.apply_reply(REPO, rf, wd, SID)


class PacketTest(unittest.TestCase):
    def setUp(self):
        self.sb, self.home = load()
        self.wd = os.path.join(self.home, "run")
        self.person = setup(self.sb, self.wd,
                            notes="# Notes\n\n## SAID\n\n## STALE\n- what it reads\n",
                            rulings="# Rulings\n\n## RULED\n",
                            research="# Research\n\n## RESEARCH\n")

    def test_said_goes_to_notes_verbatim(self):
        run_apply(self.sb, self.wd, "SAID: %s\n---\nEND-WRITE\n" % self.person)
        notes = open(os.path.join(self.wd, "notes.md"), encoding="utf-8").read()
        self.assertIn(self.person, notes)
        self.assertLess(notes.index("## SAID"), notes.index(self.person))

    def test_said_never_lands_in_rulings(self):
        run_apply(self.sb, self.wd, "SAID: %s\n---\nEND-WRITE\n" % self.person)
        self.assertNotIn(self.person, open(os.path.join(self.wd, "rulings.md"), encoding="utf-8").read())

    def test_ruled_goes_to_rulings(self):
        run_apply(self.sb, self.wd, 'RULED: "every receipt gets a category first" — said yes\n---\nEND-WRITE\n')
        self.assertIn("said yes", open(os.path.join(self.wd, "rulings.md"), encoding="utf-8").read())
        self.assertNotIn("said yes", open(os.path.join(self.wd, "notes.md"), encoding="utf-8").read())

    def test_duplicate_line_is_skipped_and_counted(self):
        r1 = run_apply(self.sb, self.wd, "SAID: %s\n---\nEND-WRITE\n" % self.person)
        self.assertIn("packet=1", r1)
        r2 = run_apply(self.sb, self.wd, "SAID: %s\n---\nEND-WRITE\n" % self.person)
        self.assertIn("packet=0", r2)
        self.assertIn("skipped 1", r2)
        self.assertEqual(open(os.path.join(self.wd, "notes.md"), encoding="utf-8").read().count(self.person), 1)

    def test_stale_record_updates_the_stale_list(self):
        run_apply(self.sb, self.wd, "STALE: the screens section\n---\nEND-WRITE\n")
        stale = open(os.path.join(self.wd, "notes.md"), encoding="utf-8").read()
        self.assertIn("the screens section", stale)
        run_apply(self.sb, self.wd, "UNSTALE: what it reads\n---\nEND-WRITE\n")
        stale = open(os.path.join(self.wd, "notes.md"), encoding="utf-8").read()
        self.assertNotIn("- what it reads", stale)
        self.assertIn("the screens section", stale)   # the other stale line untouched

    def test_research_goes_to_research_md(self):
        run_apply(self.sb, self.wd, "RESEARCH: five readers found no egress rule — the reviewers — shown\n---\nEND-WRITE\n")
        self.assertIn("five readers found no egress rule", open(os.path.join(self.wd, "research.md"), encoding="utf-8").read())

    def test_packet_records_count_toward_the_marker(self):
        res = run_apply(self.sb, self.wd, "SAID: %s\n---\nRULED: a yes on a play-back\n---\nEND-WRITE\n" % self.person)
        self.assertIn("packet=2", res)
        self.assertIn("spec=0", res)


if __name__ == "__main__":
    unittest.main()
