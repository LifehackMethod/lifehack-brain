"""Phase 4 step 4.3: keys in every diary entry. Works on a COPY of the live database (sqlite backup; the live file is only
read), plus a made-up person, merge and retirement written into the copy. Each planted case first runs a deliberately BROKEN
writer and requires the check to catch it, then the real code.
  1. a name in the prose with no staged key is NOT in mentions (broken writer: looks names up in prose)
  2. a staged person's key IS in mentions (broken writer: writes nothing)
  3. a merged-away key is written as the survivor's key (broken writer: writes the old key)
  4. a retired key is not written; a mentions line naming an unstaged key is refused."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import json, os, shutil, sqlite3, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import migrate, store_graph as sg  # noqa: E402
import diary_keys as dk, morning  # noqa: E402
import gc_settings  # noqa: E402

LIVE = gc_settings.db_path()
DAY = "2026-11-15"


def make_db(path):
    if os.path.exists(LIVE):
        src = sqlite3.connect("file:%s?mode=ro" % LIVE, uri=True)
        dst = sqlite3.connect(path)
        src.backup(dst)
        src.close()
        dst.close()
    else:
        fresh = migrate.fresh_build(10**6)       # no live database on this machine: every migration, empty
        dst = sqlite3.connect(path)
        fresh.backup(dst)
        dst.close()
    return sqlite3.connect(path)


# the planted-bad writers
def broken_prose_writer(con, forms, prose):
    """looks names up in the prose and mints their keys: the thing the rule forbids"""
    out = []
    for key, name in con.execute("SELECT key, name FROM kg_things WHERE kind='person' AND length(name)>5"):
        if name.lower() in prose.lower():
            out.append(key)
    return sorted(out), []


def broken_empty_writer(con, forms):
    return [], []


def broken_old_key_writer(con, forms):
    out = []
    for f in forms:
        out += dk.staged_from_form(f)[0]
    return sorted(set(out)), []


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.con = make_db(os.path.join(self.tmp, "t.db"))
        c = self.con
        self.dana = sg.thing(c, "person", "Dana Plantedname")          # staged: carries a key
        self.wren = sg.thing(c, "person", "Wren Plantedother")         # named in prose only, no staged key
        self.old = sg.thing(c, "person", "Olu Plantedold")
        self.new = sg.thing(c, "person", "Olu Plantednew")
        c.execute("UPDATE kg_things SET merged_into=?, retired_at='2026-11-01T00:00:00Z' WHERE id=?", (self.new, self.old))
        self.gone = sg.thing(c, "person", "Gil Plantedretired")
        c.execute("UPDATE kg_things SET retired_at='2026-11-01T00:00:00Z' WHERE id=?", (self.gone,))
        self.k = lambda i: c.execute("SELECT key FROM kg_things WHERE id=?", (i,)).fetchone()[0]
        self.thread = "ab12cd34ef56"

    def tearDown(self):
        self.con.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def form(self, keys=(), prose="Wren Plantedother needs a reply"):
        return {"thing_keys": list(keys), "thread_ids": [self.thread], "needs_him": [{"what": prose, "kind": "do", "how_soon": "today",
                "confidence": "low", "source": None}]}

    def test_1_prose_name_without_staged_key_not_written(self):
        forms = [self.form()]
        prose = forms[0]["needs_him"][0]["what"]
        bad, _ = broken_prose_writer(self.con, forms, prose)
        self.assertIn(self.k(self.wren), bad)                                   # the plant is caught: the broken writer leaks it
        real, _ = dk.mentions_for_forms(self.con, forms)
        self.assertNotIn(self.k(self.wren), real)
        self.assertEqual(real, ["conversation:" + self.thread])

    def test_2_staged_person_key_written(self):
        forms = [self.form([self.k(self.dana)])]
        self.assertNotIn(self.k(self.dana), broken_empty_writer(self.con, forms)[0])   # the plant is caught
        real, _ = dk.mentions_for_forms(self.con, forms)
        self.assertIn(self.k(self.dana), real)
        self.assertIn("conversation:" + self.thread, real)

    def test_3_merged_key_becomes_survivor(self):
        forms = [self.form([self.k(self.old)])]
        bad, _ = broken_old_key_writer(self.con, forms)
        self.assertIn(self.k(self.old), bad)                                    # the plant is caught: old key written
        real, _ = dk.mentions_for_forms(self.con, forms)
        self.assertIn(self.k(self.new), real)
        self.assertNotIn(self.k(self.old), real)

    def test_4_retired_dropped_and_unstaged_refused(self):
        forms = [self.form([self.k(self.gone), self.k(self.dana), "person:no-such-key", "address:x@example.test"])]
        real, dropped = dk.mentions_for_forms(self.con, forms)
        self.assertNotIn(self.k(self.gone), real)
        self.assertEqual(sorted(w for _, w in dropped), ["kind_not_allowed", "retired", "unknown_key"])
        text = dk.front_matter([self.k(self.wren)]) + "# entry\n"             # a mentions line naming a key no staged record carries
        self.assertEqual(dk.check_entry(text, [self.k(self.dana)], self.con), ["not_staged:" + self.k(self.wren)])
        self.assertEqual(dk.check_entry(dk.front_matter(real) + "# e\n", dk.staged_from_form(forms[0])[0], self.con,
                                        dk.staged_from_form(forms[0])[1]), [])
        self.assertEqual(dk.check_entry(dk.front_matter([self.k(self.gone)]), [self.k(self.gone)], self.con),
                         ["retired_or_merged_key_written:" + self.k(self.gone)])
        self.assertTrue(dk.check_entry("# no front matter\n", [], self.con))

    def test_5_morning_diary_entry_writes_and_reader_parses_back(self):
        diary = os.path.join(self.tmp, "diary")
        stamped = [{"source": "email", "id": "m1", "keys": [self.k(self.old), self.k(self.dana)]}]
        handed = [{"id": "m1", "thread_id": self.thread}]
        res = morning.write_diary_entry(DAY, "desk-b", diary, [DAY + "-desk-b"], handed, stamped,
                                        None, con=self.con)
        self.assertEqual(res["status"], "written")
        with open(res["path"], encoding="utf-8") as f:
            text = f.read()
        got = dk.read_front_matter(text)
        self.assertEqual(sorted(got["keys"]), sorted([self.k(self.new), self.k(self.dana)]))     # the merged key becomes its survivor
        self.assertEqual(got["conversations"], [self.thread])
        self.assertEqual(got["confidence"], "low")
        form = {"thing_keys": [self.k(self.old), self.k(self.dana)], "thread_ids": [self.thread]}
        self.assertEqual(dk.check_entry(text, dk.staged_from_form(form)[0], self.con, [self.thread], [DAY + "-desk-b"]), [])
        self.assertNotIn(self.k(self.wren), got["keys"])                  # named in the AI text only: never a key
        # no database handed in: still an entry, keys are never written unchecked
        res2 = morning.write_diary_entry("2026-11-14", "desk-b", diary, [DAY + "-desk-b"], handed, stamped, None)
        self.assertEqual(res2["status"], "written")
        self.assertEqual(dk.read_front_matter(open(res2["path"], encoding="utf-8").read())["keys"], [])


if __name__ == "__main__":
    unittest.main()
