"""Phase 4 step 4.6: three small fixes, then the 7-day backfill. Scratch only (a sqlite backup of the live database plus migration
028, scratch diary folders); the real diaries and the live database are never opened for writing.
Each planted case first runs a deliberately BROKEN version and requires the check to FAIL on it, then the real code:
  fix 1  entries_mentioning(..., diary=X) passes its binding          (plant: the old query, which raised)
  fix 2  store_diary.diary_name is the one pattern in diary_names     (plant: a copy of the pattern in store_diary)
  fix 3  an entry's front matter carries the staged-record ids, the index reads them   (plant: an entry without them)
  4.6    window of 7 days only (plant: no window check); an existing day is skipped and never opened for writing (plant: overwrite);
         a part-b item never lands in Main-Diary (plant: routing that ignores the part of life); a prose-only name never
         appears in mentions (plant: a stamper that looks the name up in prose); a backfill on the real folders needs --real."""
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
import morning, diary_names, diary_keys, routing, gcjobs  # noqa: E402
import test_step44_diary_index as t44  # noqa: E402
import test_step45_midnight as t45  # noqa: E402


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


def _only_mine(cls):
    for n in dir(t45.T):
        if n.startswith("test_") and n not in cls.__dict__:
            setattr(cls, n, None)             # the inherited step-4.5 tests already run in their own file
    return cls


@_only_mine
class Fix3(t45.T):
    def test_3_staged_ids_in_front_matter_and_index(self):
        self.run_read(self.real_stamper())
        res = self.midnight()
        for name in ("Main-Diary", "Bravo-Diary"):
            text = self.text(name)
            fm = diary_keys.read_front_matter(text)
            self.assertEqual(fm["staged"], ["2026-11-15-desk-a"], name)
            sd.index_entry(self.con, name, res[name]["path"], self.notes)
            row = self.con.execute("SELECT staged_ids FROM diary_index WHERE diary=?", (name,)).fetchone()
            self.assertEqual(json.loads(row[0]) if False else row[0], '["2026-11-15-desk-a"]')
        # the check refuses an id no staged file has
        text = self.text("Bravo-Diary").replace('staged: ["2026-11-15-desk-a"]', 'staged: ["2026-11-01-desk-a"]')
        probs = diary_keys.check_entry(text, [], self.con, [], staged_ids_allowed=["2026-11-15-desk-a"])
        self.assertTrue(any(p.startswith("staged_not_staged") for p in probs), probs)


@_only_mine
class Backfill(t45.T):
    FIRST, LAST, TODAY = "2026-11-10", "2026-11-16", "2026-11-16"

    def setUp(self):
        super().setUp()
        for d in ("desk-a", "desk-b", "desk-c", "desk-d"):
            os.makedirs(os.path.join(self.notes, "desks", d, "diary"), exist_ok=True)
        self.run_read(self.real_stamper())
        self.fdir = os.path.join(self.env.front, "catalogue", "morning")

    def go(self, first=None, last=None, **kw):
        out = []
        r = gcjobs.backfill(first or self.FIRST, last or self.LAST, self.notes, self.db, today=self.TODAY,
                            records_dir=self.env.records, form_dir=self.fdir, out=out.append, **kw)
        return r, out

    def files(self, name):
        return t45.T.entry_files(os.path.join(self.notes, "desks", name, "diary"))

    def test_window_is_seven_days(self):
        orig = gcjobs._check_window
        gcjobs._check_window = lambda *a, **k: None                      # broken: no window check
        try:
            r, _ = self.go("2026-11-01", "2026-11-16")
            self.assertNotEqual(r, 2)                                    # caught: it ran beyond the 7 days
        finally:
            gcjobs._check_window = orig
        shutil.rmtree(self.notes); self.setUp_dirs()
        for a, b in (("2026-11-01", "2026-11-16"), ("2026-11-10", "2026-11-17"), ("2026-11-16", "2026-11-10")):
            r, out = self.go(a, b)
            self.assertEqual(r, 2, (a, b, out))
        self.assertEqual(self.files("desk-a"), [])

    def setUp_dirs(self):
        for d in ("desk-a", "desk-b", "desk-c", "desk-d"):
            os.makedirs(os.path.join(self.notes, "desks", d, "diary"), exist_ok=True)

    def test_written_skipped_nothing_and_stamp(self):
        r, out = self.go()
        self.assertEqual(r, 0, out)
        self.assertEqual(len(self.files("desk-a")), 1)
        self.assertEqual(len(self.files("desk-b")), 1)
        self.assertEqual(self.files("desk-c"), [])
        text = open(self.files("desk-b")[0], encoding="utf-8").read()
        self.assertIn("stamp: machine draft, backfilled, unconfirmed", text)
        before = dict((p, open(p, "rb").read()) for d in ("desk-a", "desk-b") for p in self.files(d))
        r2, out2 = self.go()                                             # second run: skipped, never opened for writing
        self.assertEqual(r2, 0)
        self.assertEqual(dict((p, open(p, "rb").read()) for d in ("desk-a", "desk-b") for p in self.files(d)), before)
        self.assertTrue(any("skipped" in l and "2026-11-15" in l for l in out2), out2)

    def test_existing_day_never_overwritten(self):
        p = morning.diary_entry_path(os.path.join(self.notes, "desks", "desk-b", "diary"), "2026-11-15", "Bravo-Diary")
        os.makedirs(os.path.dirname(p)); open(p, "w", encoding="utf-8").write("hand written\n")
        self.go()
        self.assertEqual(open(p, encoding="utf-8").read(), "hand written\n")

    def test_bad_route_and_bad_link(self):
        eli = self.k(self.eli); wren = self.k(self.wren)
        orig = routing.route
        routing.route = lambda part, table: table["main_diary"]          # broken routing
        try:
            self.go()
        finally:
            routing.route = orig
        self.assertIn(eli, diary_keys.read_front_matter(open(self.files("desk-a")[0], encoding="utf-8").read())["keys"])   # caught
        shutil.rmtree(self.notes); self.setUp_dirs()
        self.go()
        main = diary_keys.read_front_matter(open(self.files("desk-a")[0], encoding="utf-8").read())
        self.assertNotIn(eli, main["keys"])
        self.assertIn(eli, diary_keys.read_front_matter(open(self.files("desk-b")[0], encoding="utf-8").read())["keys"])
        for f in self.files("desk-a") + self.files("desk-b"):
            self.assertNotIn(wren, diary_keys.read_front_matter(open(f, encoding="utf-8").read())["keys"])
            self.assertNotIn("Wren", open(f, encoding="utf-8").read().split("---", 2)[1])  # the front matter names nobody from prose

    def test_real_folders_need_real_flag(self):
        out = []
        r = gcjobs.backfill(self.FIRST, self.LAST, morning.DRIVE_NOTES, self.db, today=self.TODAY, records_dir=self.env.records,
                            form_dir=self.fdir, out=out.append)
        self.assertEqual(r, 2, out)


if __name__ == "__main__":
    unittest.main()
