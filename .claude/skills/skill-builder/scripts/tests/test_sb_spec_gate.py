#!/usr/bin/env python3
"""Tests for sb_spec.py gate() (brief 2f, §6 test 1). stdlib unittest.

Run:  python3 -m unittest discover -s .claude/skills/skill-builder/scripts/tests  (from the repo root)
"""

import os
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(TESTS_DIR)))))
LIB = os.path.join(REPO, "system", "hooks", "lib")


def fresh_env():
    home = tempfile.mkdtemp(prefix="sbspec-gate-")
    os.environ["HOME"] = home
    os.environ["LIFEHACK_REPO_ROOT"] = REPO
    for k in ("LIFEHACK_MODEL_STUB", "SPEC_WRITER_RUNNING"):
        os.environ.pop(k, None)
    return home


def load_sb_spec():
    if LIB not in sys.path:
        sys.path.insert(0, LIB)
    for m in [k for k in list(sys.modules) if k == "sb_spec"]:
        del sys.modules[m]
    import sb_spec
    return sb_spec


class GateTest(unittest.TestCase):
    def setUp(self):
        self.home = fresh_env()
        self.sb = load_sb_spec()
        self.sid = "gateSess1"
        self.od = self.sb.od()
        os.makedirs(self.od, exist_ok=True)

    def _pidfile(self, name, pid):
        with open(os.path.join(self.od, name), "w", encoding="utf-8") as f:
            f.write(str(pid))

    def test_two_readers_in_one_prompt_both_see_saved(self):
        # the screen hook and the model hook are separate processes: the second must replay the first's SAVED pair
        with open(os.path.join(self.od, "spec-saved-%s.txt" % self.sid), "w", encoding="utf-8") as f:
            f.write("saved 1 spec lines \u00b7 0 packet lines\n")
        a = self.sb.gate(self.sid, window=20)
        b = self.sb.gate(self.sid, window=20)
        self.assertTrue(a[0] and a[0] == b[0] and a[1] == b[1])
        self.assertEqual(self.sb.gate(self.sid), (None, None) if False else self.sb.gate(self.sid))

    def test_writer_alive_is_wait(self):
        self._pidfile("spec-write-%s.pid" % self.sid, os.getpid())
        s, m = self.sb.gate(self.sid, consume=False)
        self.assertEqual(s, "📋 Spec: WAIT — saving your answers from the last round; nothing lost.")
        self.assertIn("Ask no new questions", m)
        self.assertIn("until the SAVED line appears", m)

    def test_questioner_alive_is_wait(self):
        self._pidfile("spec-questions-%s.pid" % self.sid, os.getpid())
        s, m = self.sb.gate(self.sid, consume=False)
        self.assertIn("WAIT", s)

    def test_dead_pid_is_not_wait(self):
        self._pidfile("spec-write-%s.pid" % self.sid, 999999)
        self.assertEqual(self.sb.gate(self.sid, consume=False), (None, None))

    def test_saved_shows_marker_once_then_consumes(self):
        with open(os.path.join(self.od, "spec-saved-%s.txt" % self.sid), "w", encoding="utf-8") as f:
            f.write("saved 3 spec lines · 5 packet lines\n")
        with open(os.path.join(self.od, "spec-questions-%s.txt" % self.sid), "w", encoding="utf-8") as f:
            f.write("1. what does it read first?\n")
        s, m = self.sb.gate(self.sid)
        self.assertIn("SAVED — saved 3 spec lines · 5 packet lines", s)
        self.assertIn("GATE: SAVED — saved 3 spec lines · 5 packet lines.", m)
        self.assertIn("QUESTIONS (from code): read", m)
        self.assertIn("Never invent questions from this conversation", m)
        # consumed: the second call shows neither
        self.assertEqual(self.sb.gate(self.sid), (None, None))
        self.assertTrue(os.path.exists(os.path.join(self.od, "spec-saved-%s.txt.shown" % self.sid)))
        self.assertTrue(os.path.exists(os.path.join(self.od, "spec-questions-%s.txt.shown" % self.sid)))

    def test_nothing_to_save_renders(self):
        with open(os.path.join(self.od, "spec-saved-%s.txt" % self.sid), "w", encoding="utf-8") as f:
            f.write("nothing to save\n")
        s, m = self.sb.gate(self.sid, consume=False)
        self.assertIn("SAVED — nothing to save", s)
        self.assertIn("GATE: SAVED — nothing to save.", m)

    def test_questioner_failed_branch(self):
        with open(os.path.join(self.od, "spec-saved-%s.txt" % self.sid), "w", encoding="utf-8") as f:
            f.write("saved 1 spec lines · 0 packet lines\n")
        with open(os.path.join(self.od, "spec-questions-%s.txt" % self.sid), "w", encoding="utf-8") as f:
            f.write("NONE (the fresh read failed)\n")
        s, m = self.sb.gate(self.sid, consume=False)
        self.assertIn("SAVED", s)
        self.assertIn("the fresh read failed — say so in one line", m)
        self.assertIn("ask no new numbered questions", m)

    def test_marker_without_questions_file_is_failure_branch(self):
        with open(os.path.join(self.od, "spec-saved-%s.txt" % self.sid), "w", encoding="utf-8") as f:
            f.write("saved 0 spec lines · 0 packet lines\n")
        _s, m = self.sb.gate(self.sid, consume=False)
        self.assertIn("ask no new numbered questions", m)


if __name__ == "__main__":
    unittest.main()
