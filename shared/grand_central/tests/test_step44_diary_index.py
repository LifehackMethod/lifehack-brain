"""Phase 4 step 4.4: the diary index. Synthetic entry files and temp databases; never the live rig.db or the real diary.
Each planted case runs a deliberately BROKEN version first and requires the check to FAIL on it, then the real code and requires a pass:
(1) an existing entry is indexed and its file is byte-identical afterwards (plant: an indexer that touches the file);
(2) a re-run makes no duplicates (plant: an indexer that inserts every time);
(3) a mentions key that was merged away finds the entry under the survivor (plant: keys not resolved).
Plus: keys are taken only from front matter (prose names nothing); a rebuild/check stays clean with index rows present."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import hashlib, os, sqlite3, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import store_diary as sd  # noqa: E402
import test_step36_merging as t36  # noqa: E402

ENTRY1 = "---\ntype: planning-diary-daily\ndate: 2026-11-06\nconfidence: low\nmentions: [person:legacy-9, person:legacy-1]\nstaged: [d1, d2]\n---\n\n# Day\nTalked to Joe Example and Jo Example.\n"
ENTRY2 = "# Diary entry 2026-11-07\nconfidence: low\n\nMet person:legacy-9 for lunch (prose only).\n"


class Base(t36.Base):
    def setUp(self):
        super().setUp()
        self.notes = tempfile.mkdtemp()
        self.root = os.path.join(self.notes, "desks", "desk-a", "diary")
        os.makedirs(os.path.join(self.root, "2026", "11"))
        self.f1 = os.path.join(self.root, "2026", "11", "06.md")
        self.f2 = os.path.join(self.root, "2026", "11", "07.md")
        for p, t in ((self.f1, ENTRY1), (self.f2, ENTRY2)):
            with open(p, "w", encoding="utf-8") as f:
                f.write(t)
        with open(os.path.join(self.root, "2026", "11", "review-month-2026-11.md"), "w", encoding="utf-8") as f:
            f.write("---\nperiod: 2026-11\n---\nx\n")

    @staticmethod
    def sha(p):
        return hashlib.sha256(open(p, "rb").read()).hexdigest()

    def refresh(self, fn=None):
        return (fn or sd.refresh_index)(self.c, "Main-Diary", self.root, self.notes)

    def n(self):
        return self.c.execute("SELECT count(*) FROM diary_index").fetchone()[0]

    # the three checks, each True when the rule holds
    def check_indexed_and_untouched(self, fn=None):
        before = (self.sha(self.f1), self.sha(self.f2), os.stat(self.f1).st_mtime_ns)
        self.refresh(fn)
        r = self.c.execute("SELECT date,keys_mentioned,staged_ids,confidence,entry_path FROM diary_index WHERE entry_path LIKE '%06.md'").fetchone()
        ok = r is not None and r[0] == "2026-11-06" and r[3] == "low" and r[4] == "desks/desk-a/diary/2026/11/06.md"
        return ok and before == (self.sha(self.f1), self.sha(self.f2), os.stat(self.f1).st_mtime_ns)

    def check_no_duplicates(self, fn=None):
        self.refresh(fn); self.refresh(fn)
        return self.n() == 2

    def check_merged_key_finds_survivor(self, find=None):
        self.refresh()
        self.merge()          # person:legacy-9 folds into person:legacy-1
        got = (find or sd.entries_mentioning)(self.c, "person:legacy-9")
        return len(got) == 1 and got[0]["date"] == "2026-11-06"


def literal_find(con, key):    # plant 3: looks the key up exactly as written, never follows a merge
    return [{"date": d} for (d,) in con.execute("SELECT date FROM diary_index WHERE keys_mentioned LIKE ?", ('%"' + key + '"%',))
            if con.execute("SELECT merged_into FROM kg_things WHERE key=?", (key,)).fetchone()[0] is None]


def touching_refresh(con, diary, root, notes, now=None):    # plant 1: an indexer that rewrites the file
    r = sd.refresh_index(con, diary, root, notes, now)
    p = os.path.join(root, "2026", "11", "06.md")
    with open(p, "a", encoding="utf-8") as f:
        f.write("")
    os.utime(p, None)
    return r


def duplicating_refresh(con, diary, root, notes, now=None):    # plant 2: inserts every time
    for p in (os.path.join(root, "2026", "11", "06.md"), os.path.join(root, "2026", "11", "07.md")):
        con.execute("INSERT INTO diary_index(diary,date,entry_path,indexed_at) VALUES(?,?,?,?)",
                    (diary, "2026-11-06", "dup/%d" % con.execute("SELECT count(*) FROM diary_index").fetchone()[0], "x"))
    return {}


class T(Base):
    def test_1_indexed_and_file_byte_identical(self):
        self.assertFalse(self.check_indexed_and_untouched(touching_refresh), "plant must be caught")
        self.c.execute("DELETE FROM diary_index")
        self.assertTrue(self.check_indexed_and_untouched())

    def test_2_rerun_no_duplicates(self):
        self.assertFalse(self.check_no_duplicates(duplicating_refresh), "plant must be caught")
        self.c.execute("DELETE FROM diary_index")
        self.assertTrue(self.check_no_duplicates())
        self.assertEqual(self.refresh()["same"], 2)

    def test_3_merged_key_resolves_to_survivor(self):
        self.assertFalse(self.check_merged_key_finds_survivor(literal_find), "plant must be caught")
        self.assertEqual(len(sd.entries_mentioning(self.c, "person:legacy-9")), 1)
        self.assertEqual(len(sd.entries_mentioning(self.c, "person:legacy-1")), 1)    # the survivor's own key too

    def test_3b_real(self):
        self.assertTrue(self.check_merged_key_finds_survivor())

    def test_keys_only_from_front_matter(self):
        self.refresh()
        self.assertEqual(self.c.execute("SELECT keys_mentioned FROM diary_index WHERE entry_path LIKE '%07.md'").fetchone()[0], "[]")
        self.assertEqual(len(sd.entries_mentioning(self.c, "person:legacy-9")), 1)    # the prose mention names nothing
        self.assertEqual(self.c.execute("SELECT staged_ids FROM diary_index WHERE entry_path LIKE '%06.md'").fetchone()[0], '["d1", "d2"]')
        self.assertEqual(self.n(), 2, "the review file has a period, not a day: not indexed")

    def test_removed_file_leaves_index(self):
        self.refresh(); os.remove(self.f2)
        self.assertEqual(self.refresh()["removed"], 1); self.assertEqual(self.n(), 1)

    def test_rebuild_check_clean_with_index_rows(self):
        self.refresh()
        self.check_clean()      # raises/asserts if the rebuild differs from live; the index is derived and outside the model picture


if __name__ == "__main__":
    unittest.main()
