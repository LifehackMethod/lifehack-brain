#!/usr/bin/env python3
"""Tests for sb_spec.py build-questions / questions-out (brief 2f, §6 test 4). stdlib unittest."""

import os
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(TESTS_DIR)))))
LIB = os.path.join(REPO, "system", "hooks", "lib")


def load():
    home = tempfile.mkdtemp(prefix="sbspec-q-")
    os.environ["HOME"] = home
    os.environ.pop("SPEC_WRITER_RUNNING", None)
    if LIB not in sys.path:
        sys.path.insert(0, LIB)
    import sb_spec
    return sb_spec, home


SPEC = """# Draft spec

## 1. WHAT
- Every receipt gets a category before it is filed (D1)
- The skill reads <[ask] what the skill reads first>
"""
TRANSCRIPT = "PRIVATE-TOKENS-FROM-THE-CONVERSATION-xyzzy"


class QuestionsTest(unittest.TestCase):
    def setUp(self):
        self.sb, self.home = load()
        self.wd = os.path.join(self.home, "run")
        os.makedirs(self.wd, exist_ok=True)
        with open(os.path.join(self.wd, "draft-spec.md"), "w", encoding="utf-8") as f:
            f.write(SPEC)
        self.out = os.path.join(self.home, "qprompt.md")

    def test_prompt_has_spec_not_transcript(self):
        res = self.sb.build_questions(REPO, self.wd, self.out, findings="")
        self.assertEqual(res, "OK")
        p = open(self.out, encoding="utf-8").read()
        self.assertIn("Every receipt gets a category before it is filed (D1)", p)
        self.assertIn("up to six leveraged questions", p)
        self.assertIn("Never use any conversation", p)
        self.assertIn("QUESTIONS-END", p)
        self.assertNotIn(TRANSCRIPT, p)

    def test_findings_section_when_handed(self):
        fp = os.path.join(self.home, "tensions-checked.md")
        with open(fp, "w", encoding="utf-8") as f:
            f.write("1. the date sort is load-bearing\n")
        self.sb.build_questions(REPO, self.wd, self.out, findings=fp)
        p = open(self.out, encoding="utf-8").read()
        self.assertIn("THE CHECKED FINDINGS (4.3)", p)
        self.assertIn("the date sort is load-bearing", p)

    def test_missing_spec_fails(self):
        os.remove(os.path.join(self.wd, "draft-spec.md"))
        self.assertTrue(self.sb.build_questions(REPO, self.wd, self.out).startswith("FAIL"))

    def _qout(self, reply_text):
        rf = os.path.join(self.home, "qreply.md")
        with open(rf, "w", encoding="utf-8") as f:
            f.write(reply_text)
        qf = os.path.join(self.home, "questions.txt")
        self.sb.questions_out(rf, qf)
        return open(qf, encoding="utf-8").read()

    def test_reply_parses_to_questions(self):
        body = self._qout("1. what does it read first?\n2. nothing else matters\nQUESTIONS-END\n")
        self.assertIn("1. what does it read first?", body)
        self.assertNotIn("QUESTIONS-END", body)
        self.assertNotIn("NONE (the fresh read failed)", body)

    def test_nothing_reply_stays_nothing(self):
        body = self._qout("NOTHING\nQUESTIONS-END\n")
        self.assertEqual(body.strip(), "NOTHING")

    def test_reply_without_marker_degrades(self):
        body = self._qout("1. a question with no end marker\n")
        self.assertEqual(body.strip(), "NONE (the fresh read failed)")

    def test_empty_reply_degrades(self):
        self.assertEqual(self._qout("").strip(), "NONE (the fresh read failed)")


if __name__ == "__main__":
    unittest.main()
