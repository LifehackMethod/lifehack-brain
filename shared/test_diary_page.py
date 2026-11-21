#!/usr/bin/env python3
"""test_diary_page.py -- shared/diary_page.py: written / appended / exists, the merge, and what must never change.
Run: python3 shared/test_diary_page.py
DIARY_PAGE_MODULE=<path> runs the same cases against a broken copy (how each planted case was seen failing first)."""
import importlib.util
import os
import stat
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("diary_page_under_test", os.environ.get("DIARY_PAGE_MODULE") or os.path.join(HERE, "diary_page.py"))
dp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dp)

HEAD = "# Morning read 2026-11-20 - cal desk (s1)"
BODY = HEAD + "\nconfidence: low\nstamp: machine draft, unconfirmed\n- Counts: 1\n"


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="diary-page-test.")
        self.p = os.path.join(self.d, "2026", "11", "20.md")

    def put(self, text):
        os.makedirs(os.path.dirname(self.p), exist_ok=True)
        with open(self.p, "w", encoding="utf-8", newline="") as f:
            f.write(text)

    def get(self):
        with open(self.p, encoding="utf-8", newline="") as f:
            return f.read()

    def test_written(self):
        self.assertEqual(dp.append_entry(self.p, BODY, ["person:a"], ["s1"], heading=HEAD), "written")
        t = self.get()
        self.assertTrue(t.startswith('---\nmentions: ["person:a"]\nstaged: ["s1"]\nconfidence: low\n---\n' + HEAD))
        self.assertEqual(stat.S_IMODE(os.stat(self.p).st_mode), 0o600)

    def test_appended_union_and_other_keys(self):
        old = '---\ntype: x\nmentions: ["person:z"]\nstaged: ["s0"]\nconfidence: low\nowner: kept\n---\n# His page\nline one\nline two'
        self.put(old)
        self.assertEqual(dp.append_entry(self.p, BODY, ["person:a", "person:b"], ["s1"], heading=HEAD), "appended")
        t = self.get()
        self.assertIn('mentions: ["person:z", "person:a", "person:b"]', t)
        self.assertIn('staged: ["s0", "s1"]', t)
        self.assertIn("type: x\n", t)
        self.assertIn("owner: kept\n", t)
        self.assertTrue(t.endswith("\n" + BODY))
        self.assertEqual(t.count("---\n"), 2)

    def test_existing_lines_byte_for_byte(self):
        lines = '# His page\r\nline "one"  \n\n  indented\t\nunicode: café — end\n'
        self.put('---\nmentions: []\nconfidence: low\n---\n' + lines)
        dp.append_entry(self.p, BODY, [], ["s1"], heading=HEAD)
        t = self.get()
        self.assertEqual(t[t.index("# His page"):t.index("# His page") + len(lines)], lines)
        self.assertTrue(t.endswith(lines + "\n" + BODY))

    def test_high_and_medium_kept(self):
        for c in ("high", "medium"):
            self.put('---\nmentions: []\nconfidence: %s\n---\nhis line\n' % c)
            dp.append_entry(self.p, BODY, [], ["s1"], heading=HEAD)
            top = self.get().split("\n---\n", 1)[0]
            self.assertIn("\nconfidence: %s" % c, top)
            self.assertNotIn("confidence: low", top)

    def test_no_front_matter_keeps_every_line(self):
        old = "plain line 1\n\nplain line 3\n"
        self.put(old)
        self.assertEqual(dp.append_entry(self.p, BODY, ["person:a"], ["s1"], heading=HEAD), "appended")
        t = self.get()
        self.assertTrue(t.startswith('---\nmentions: ["person:a"]\nstaged: ["s1"]\nconfidence: low\n---\n' + old))
        self.assertTrue(t.endswith(BODY))

    def test_exists_changes_nothing(self):
        self.put("# Other\n")
        dp.append_entry(self.p, BODY, ["person:a"], ["s1"], heading=HEAD)
        before = self.get()
        calls = []
        self.assertEqual(dp.append_entry(self.p, BODY, ["person:a"], ["s1"], heading=HEAD, after_write=calls.append), "exists")
        self.assertEqual(self.get(), before)
        self.assertEqual(calls, [])

    def test_no_heading_always_appends(self):
        dp.append_entry(self.p, BODY, [], [])
        self.assertEqual(dp.append_entry(self.p, BODY, [], []), "appended")
        self.assertEqual(self.get().count(HEAD), 2)

    def test_mode_0600_after_append(self):
        self.put("x\n")
        os.chmod(self.p, 0o644)
        dp.append_entry(self.p, BODY, [], [], heading=HEAD)
        self.assertEqual(stat.S_IMODE(os.stat(self.p).st_mode), 0o600)

    def test_after_write_once_per_write(self):
        calls = []
        dp.append_entry(self.p, BODY, [], [], heading=HEAD, after_write=calls.append)
        self.assertEqual(calls, [self.p])
        calls.clear()
        dp.append_entry(self.p, BODY, [], [], heading="# second", after_write=calls.append)
        self.assertEqual(calls, [self.p])

    def test_unreadable_page_refused_loudly(self):
        os.makedirs(os.path.dirname(self.p))
        with open(self.p, "wb") as f:
            f.write(b"\xff\xfe\x00bad")
        with self.assertRaises(dp.DiaryPageError):
            dp.append_entry(self.p, BODY, [], [], heading=HEAD)
        with open(self.p, "rb") as f:
            self.assertEqual(f.read(), b"\xff\xfe\x00bad")

    def test_no_temp_files_left(self):
        self.put("x\n")
        dp.append_entry(self.p, BODY, [], [], heading=HEAD)
        self.assertEqual(os.listdir(os.path.dirname(self.p)), ["20.md"])

    def test_same_bytes_as_grand_central(self):
        """The lift is as-is: the same page text as morning._merge_front_matter / diary_keys.front_matter."""
        sys.path.insert(0, os.path.join(HERE, "grand_central"))
        try:
            import diary_keys
            import morning
        except Exception as e:  # engine not importable here: the byte-equality case is skipped, loudly
            self.skipTest("grand_central not importable: %s" % e)
        self.assertEqual(dp.front_matter(["k"], ["s"], "low"), diary_keys.front_matter(["k"], ["s"], "low"))
        for old in ('---\ntype: x\nmentions: ["a"]\nstaged: ["s0"]\nconfidence: high\nz: 1\n---\nbody\n', "no fm\n",
                    '---\nmentions: []\nconfidence: weird\n---\nb'):
            self.assertEqual(dp._merge_front_matter(old, ["a", "b"], ["s1"]), morning._merge_front_matter(old, ["a", "b"], ["s1"]))


if __name__ == "__main__":
    unittest.main(verbosity=1)
