"""Phase 4 step 4.7: diary entries on a person's page (gc person; also org and upcoming). Synthetic entry files and temp databases;
never the live rig.db or the real diary. Each planted case runs a deliberately BROKEN version first and requires the check to FAIL on it,
then the real code and requires a pass:
(1) an entry mentioning a person shows on their page, newest first, with its stamp (plant: the page never looks at the diary);
(2) an entry that does not mention them does not show (plant: every entry is listed on every page);
(3) a merged-away key's page shows the survivor's entries (plant: the key is looked up exactly as written);
(4) an old entry with no mentions shows on no page, never guessed from the prose (plant: guesses by name in the text).
Plus: a person named in no entry has no diary field at all (old fields unchanged), and the gc text and --json both carry it."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import contextlib, io, json, os, re, sqlite3, sys, tempfile, unittest
from unittest import mock
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import importlib.util
import store_diary as sd  # noqa: E402
import store_pages as sp  # noqa: E402
import test_step36_merging as t36  # noqa: E402

ASOF = "2026-11-16"
_spec = importlib.util.spec_from_file_location("gc_cli", os.path.join(ROOT, "gc.py"))
gc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gc)

ENTRIES = {   # day -> text
    "03": "# Old entry\nconfidence: low\n\nTalked to Joe Example and person:legacy-9 in prose only.\n",
    "06": "---\nconfidence: low\nmentions: [person:legacy-9]\n---\nJoe day.\n",
    "08": "---\nconfidence: medium\nmentions: [person:legacy-1]\n---\nJo day.\n",
    "09": "---\nconfidence: high\nmentions: [person:legacy-1, person:legacy-9]\n---\nBoth.\n",
}


class Base(t36.Base):
    def setUp(self):
        super().setUp()
        self.c.row_factory = sqlite3.Row
        self.notes = tempfile.mkdtemp()
        d = os.path.join(self.notes, "desks", "desk-a", "diary", "2026", "11")
        os.makedirs(d)
        for day, text in ENTRIES.items():
            p = os.path.join(d, day + ".md")
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
            sd.index_entry(self.c, "Main-Diary", p, self.notes)

    def days(self, key):
        p = sp.person_page(self.c, key, ASOF)
        return [(e["date"][8:], e["confidence"]) for e in p.get("diary", [])]

    def gc(self, *args):
        self.c.close()
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = gc.main(["--db", os.path.join(self.tmp.name, "rig.db"), *args])
        self.c = sqlite3.connect(os.path.join(self.tmp.name, "rig.db"), isolation_level=None)
        self.c.row_factory = sqlite3.Row
        return rc, out.getvalue()


def no_diary(con, key):          # plant 1: the page never looks at the diary
    return []


def every_entry(con, key):       # plant 2: every entry on every page
    return [dict(diary=d, date=dd, entry_path=p, confidence=c) for d, dd, p, c in
            con.execute("SELECT diary,date,entry_path,confidence FROM diary_index ORDER BY date DESC")]


def literal_key(con, key):       # plant 3: the key exactly as written, no merge followed
    return [dict(diary=d, date=dd, entry_path=p, confidence=c) for d, dd, p, c in
            con.execute("SELECT diary,date,entry_path,confidence FROM diary_index ORDER BY date DESC") if '"%s"' % key in
            con.execute("SELECT keys_mentioned FROM diary_index WHERE entry_path=?", (p,)).fetchone()[0]]


def guess_from_prose(con, key):  # plant 4: also lists entries whose text names the person
    out = literal_key(con, key)
    if key.startswith("person:"):
        out.append(dict(diary="Main-Diary", date="2026-11-03", entry_path="desks/desk-a/diary/2026/11/03.md", confidence="low"))
    return sorted(out, key=lambda e: e["date"], reverse=True)


class T(Base):
    def with_plant(self, fn):
        return mock.patch.object(sp, "_diary", fn)

    def check_shows_newest_first_with_stamp(self):
        return self.days("person:legacy-1") == [("09", "high"), ("08", "medium")]

    def check_not_mentioning_not_shown(self):
        return self.days("person:legacy-1") == [("09", "high"), ("08", "medium")] and ("06", "low") not in self.days("person:legacy-1")

    def check_merged_shows_survivor(self):
        self.merge()                                       # person:legacy-9 folds into person:legacy-1
        want = [("09", "high"), ("08", "medium"), ("06", "low")]
        return self.days("person:legacy-9") == want and self.days("person:legacy-1") == want

    def check_old_entry_on_no_page(self):
        self.merge()
        return all(d != "03" for k in ("person:legacy-9", "person:legacy-1") for d, _ in self.days(k))

    def test_1_shows_newest_first_with_stamp(self):
        with self.with_plant(no_diary):
            self.assertFalse(self.check_shows_newest_first_with_stamp(), "plant must be caught")
        self.assertTrue(self.check_shows_newest_first_with_stamp())

    def test_2_not_mentioning_not_shown(self):
        with self.with_plant(every_entry):
            self.assertFalse(self.check_not_mentioning_not_shown(), "plant must be caught")
        self.assertTrue(self.check_not_mentioning_not_shown())
        self.assertEqual(self.days("person:legacy-9"), [("09", "high"), ("06", "low")])    # his own page: entries 09 and 06 only

    def test_3_merged_key_shows_survivor(self):
        with self.with_plant(literal_key):
            self.assertFalse(self.check_merged_shows_survivor(), "plant must be caught")

    def test_3b_real(self):
        self.assertTrue(self.check_merged_shows_survivor())

    def test_4_old_entry_never_guessed(self):
        with self.with_plant(guess_from_prose):
            self.assertFalse(self.check_old_entry_on_no_page(), "plant must be caught")

    def test_4b_real(self):
        self.assertTrue(self.check_old_entry_on_no_page())

    def test_named_in_no_entry_has_no_field_and_old_fields_unchanged(self):
        self.c.execute("DELETE FROM diary_index")
        base = sp.person_page(self.c, "person:legacy-1", ASOF)
        self.assertNotIn("diary", base)
        sd.index_entry(self.c, "Main-Diary", os.path.join(self.notes, "desks/desk-a/diary/2026/11/08.md"), self.notes)
        with_d = sp.person_page(self.c, "person:legacy-1", ASOF)
        self.assertEqual({k: v for k, v in with_d.items() if k != "diary"}, base)       # only the added field differs

    def test_gc_text_and_json(self):
        rc, txt = self.gc("person", "person:legacy-1")
        self.assertEqual(rc, 0)
        lines = [l for l in txt.splitlines() if "DIARY" in l]
        self.assertEqual(len(lines), 2)
        self.assertIn("2026-11-09", lines[0]); self.assertIn("(high confidence)", lines[0]); self.assertIn("2026-11-08", lines[1])
        rc, js = self.gc("person", "person:legacy-1", "--json")
        self.assertEqual([e["date"] for e in json.loads(js)["diary"]], ["2026-11-09", "2026-11-08"])

    def test_org_and_event_pages(self):
        from store_graph import thing
        thing(self.c, "organization", "Acme", key="organization:acme")
        thing(self.c, "event", "Launch", key="event:launch")
        self.c.execute("UPDATE kg_things SET starts_at='2026-11-17T10:00:00Z' WHERE key='event:launch'")
        d = os.path.join(self.notes, "desks", "desk-a", "diary", "2026", "11", "10.md")
        with open(d, "w", encoding="utf-8") as f:
            f.write("---\nconfidence: low\nmentions: [organization:acme, event:launch]\n---\nx\n")
        sd.index_entry(self.c, "Main-Diary", d, self.notes)
        o = sp.org_chart(self.c, "organization:acme", ASOF)
        self.assertEqual([e["date"] for e in o["diary"]], ["2026-11-10"])
        u = sp.upcoming(self.c, ASOF, 7)
        self.assertEqual([e["diary"][0]["date"] for e in u["events"] if e["key"] == "event:launch"], ["2026-11-10"])


if __name__ == "__main__":
    unittest.main()
