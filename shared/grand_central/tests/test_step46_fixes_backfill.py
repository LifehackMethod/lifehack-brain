"""Phase 4 step 4.6: the small fixes (the 7-day backfill and the midnight job it rode on are retired, 4P.3R; the front-matter
staged-ids check now lives in test_step4_morning.DiaryEntry). Scratch only; the real diaries and the live database are never opened.
Each planted case first runs a deliberately BROKEN version and requires the check to FAIL on it, then the real code:
  fix 1  entries_mentioning(..., diary=X) passes its binding          (plant: the old query, which raised)
  fix 2  store_diary.diary_name is the one pattern in diary_names     (plant: a copy of the pattern in store_diary)
"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import hashlib, json, os, re, shutil, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import store_diary as sd  # noqa: E402
import diary_names  # noqa: E402
import test_step44_diary_index as t44  # noqa: E402


class Fix1and2(t44.Base):
    def test_1_diary_filter_binds(self):
        self.refresh()
        def old(con, key, diary=None):                                   # the 4.4 query: WHERE ... but no bindings
            sql = "SELECT diary FROM diary_index" + (" WHERE diary=?" if diary else "")
            return con.execute(sql).fetchall()
        with self.assertRaises(Exception):                               # caught: the old shape raises
            old(self.c, "person:legacy-1", diary="Main-Diary")
        got = sd.entries_mentioning(self.c, "person:legacy-1", diary="Main-Diary")
        self.assertEqual([g["date"] for g in got], ["2026-11-06"])
        self.assertEqual(sd.entries_mentioning(self.c, "person:legacy-1", diary="Bravo-Diary"), [])

    def test_2_diary_name_one_source(self):
        self.assertEqual(sd.diary_name("desk-b"), diary_names.diary_name("desk-b"))
        self.assertEqual(sd.diary_name("desk-a"), "Main-Diary")
        src = open(os.path.join(ROOT, "store_diary.py"), encoding="utf-8").read()
        self.assertNotRegex(src, r'"%s-Diary"|-Diary"')                  # no copy of the pattern in store_diary
        planted = 'def diary_name(d):\n    return "%s-Diary" % d\n'
        self.assertRegex(planted, r'-Diary"')                            # caught: a copy is detected


if __name__ == "__main__":
    unittest.main()
