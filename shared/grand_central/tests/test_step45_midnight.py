"""Phase 4 step 4.5: the midnight job writes ONE entry per diary, and the morning read stamps code-certain keys.
SCRATCH ONLY: a sqlite backup of the live database (plus migration 028 when the copy is still at 27), scratch diary folders, a scratch
front room. The real diaries and the live database are never opened for writing. Each planted case first runs a deliberately BROKEN
version and requires the check to FAIL on it, then the real code and requires a pass:
  1. two diaries with items -> two entries, one each     (broken: everything into one main entry, the old single-diary writer)
  2. a second run the same day never overwrites           (broken: a writer that overwrites)
  3. a part-b item never lands in the main diary          (broken: routing that ignores the part of life)
  4. a staged email carries its sender's key in mentions  (broken: a stamper that stamps no keys)
  5. a name that is only in prose gets no key             (broken: a stamper that looks names up in prose)
Plus: an event key from the calendar item, a task with no link gets none, an organization key when only the domain is linked,
every written entry is in the index and the index matches the files."""
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
sys.path.insert(0, HERE)
import gc_settings  # noqa: E402
import migrate, store, store_graph as sg, store_diary as sd  # noqa: E402
import morning, stamp_keys, diary_keys, routing, diary_names  # noqa: E402
import test_step4_morning as t4  # noqa: E402

LIVE = gc_settings.db_path()
DAY = "2026-11-15"
LABELS = {"labels": {"Example-Label-B": {"life_part": "part-b"}, "read-a": {}}}
TABLE = {"main_diary": "Main-Diary", "diary_pattern": "{desk}-Diary", "parts_to_desk": {"part-b": "Bravo"}}


def make_db(path):
    if os.path.exists(LIVE):
        src = sqlite3.connect("file:%s?mode=ro" % LIVE, uri=True)
        dst = sqlite3.connect(path)
        src.backup(dst)
        src.close()
        dst.close()
        c = sqlite3.connect(path, isolation_level=None)
        for n, p in migrate.list_migrations():
            if n > c.execute("PRAGMA user_version").fetchone()[0]:
                migrate.apply_file(c, p, n)
        c.close()
    else:
        fresh = migrate.fresh_build(10**6)
        dst = sqlite3.connect(path)
        fresh.backup(dst)
        dst.close()
    return sqlite3.connect(path)


class T(t4.Base):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.db = os.path.join(self.tmp, "scratch.db")
        c = make_db(self.db)
        mk = lambda kind, name, key=None: sg.thing(c, kind, name, key=key)   # noqa: E731
        self.eli, self.pat_org = mk("person", "Eli Emilyplant"), mk("organization", "Planorg Plantedco")
        self.wren = mk("person", "Wren Prosewrenplant")                      # named in prose only: no address, no link, no staged key
        self.k = lambda i: c.execute("SELECT key FROM kg_things WHERE id=?", (i,)).fetchone()[0]
        for addr, kind, to in (("eli@partb.example", "address_of", self.eli), ("pat@planorg.example", "belongs_to", self.pat_org)):
            sg.add_link(c, mk("address", addr), kind, to, "code", "sure", "code")
        mk("event", "Plantedlunch", key="event:calendar:EVT1")
        self.mids = {}
        for fid, addr in (("msg-A1", "eli@partb.example"), ("msg-B1", "pat@planorg.example"), ("msg-C1", "stranger@nowhere.example")):
            self.mids[fid] = t4.hexid(fid)
            c.execute("INSERT INTO messages(id, from_addr) VALUES(?,?)", (t4.hexid(fid), addr))
        c.commit()
        self.con = c
        self.notes = os.path.join(self.tmp, "notes")
        self.roots = {"Main-Diary": os.path.join(self.notes, "desks", "desk-a", "diary"),
                      "Bravo-Diary": os.path.join(self.notes, "desks", "desk-b", "diary")}
        e = self.env
        t = t4.triage_of({"needs_me": "yes", "do_or_know": "do", "how_soon": "2 days", "life_area": "gigs"})
        e.deliver("th-A", "msg-A1", "Eli <eli@partb.example>", "Tryout", "2026-11-15 08:00", "Example-Label-B", t, "Please send the tape by Friday.")
        e.deliver("th-B", "msg-B1", "Pat <pat@planorg.example>", "Invoice", "2026-11-15 09:00", "read-a", t, "The invoice is ready for review.")
        e.deliver("th-C", "msg-C1", "S <stranger@nowhere.example>", "Hello", "2026-11-15 09:30", "read-a", t,
                  "Wren Prosewrenplant said hello and asks for a call.")
        self.assertEqual(e.ingest()["ingested"], 3)
        self.evts = [{"title": "Plantedlunch", "start": "2026-11-16T12:00:00", "id": "EVT1"}]
        self.tasks = [{"title": "Unlinked task", "status": "open", "due": "2026-11-20", "updated": "2026-11-14", "_tid": "T1"}]

    def tearDown(self):
        self.con.close()

    # ---- the morning read, with a given stamper
    def run_read(self, stamper):
        m = t4.FakeModel(self.env, t4.reply(
            what_changed=["Three messages arrived: a tape request, an invoice and a greeting from someone unfamiliar."],
            picture=[{"text": "Wren Prosewrenplant may want a call; this is only a note in the greeting.", "basis": []}],
            form={"needs_him": [t4.need("Send the tape", "msg-A1"), t4.need("Review the invoice", "msg-B1"),
                                t4.need("Decide on a call", "msg-C1", kind="know", soon="this_week")]},
            coverage=t4.used("msg-A1", "msg-B1", "msg-C1")))
        out = morning.run_morning(m, DAY, "desk-a", self.env.records, calendar=self.evts, tasks=self.tasks, stamper=stamper)
        self.assertTrue(out["ok"], out)
        return out

    def real_stamper(self):
        return morning._live_stamper(self.db, LABELS)

    def midnight(self, writer=None, day=DAY):
        files = morning.find_staged(self.env.records, DAY, "desk-a")
        fdir = os.path.join(self.env.front, "catalogue", "morning")
        con = sqlite3.connect("file:%s?mode=ro" % self.db, uri=True)
        try:
            return (writer or morning.midnight_entries)(day, files, self.roots, TABLE, "tree", fdir, con=con)
        finally:
            con.close()

    @staticmethod
    def entry_files(root):
        return sorted(os.path.join(dp, f) for dp, _, fs in os.walk(root) for f in fs if f.endswith(".md"))

    def text(self, name):
        return open(morning.diary_entry_path(self.roots[name], DAY, name), encoding="utf-8").read()

    # ---- the planted-bad writers
    @staticmethod
    def broken_single_diary(day, files, roots, table, layout, fdir, con=None):
        r = morning.midnight_entry(day, "desk-a", files, roots["Main-Diary"], layout, fdir, con=con)
        return {"Main-Diary": r}

    def check_two_one_each(self, res):
        return (sorted(res) == ["Bravo-Diary", "Main-Diary"] and all(r["status"] == "written" for r in res.values())
                and len(self.entry_files(self.roots["Main-Diary"])) == 1 and len(self.entry_files(self.roots["Bravo-Diary"])) == 1)

    # ---- 1
    def test_1_two_diaries_two_entries(self):
        self.run_read(self.real_stamper())
        bad = self.midnight(self.broken_single_diary)
        self.assertFalse(self.check_two_one_each(bad))                      # caught: the old writer makes one entry
        shutil.rmtree(self.notes)
        res = self.midnight()
        self.assertTrue(self.check_two_one_each(res), res)

    # ---- 2
    @staticmethod
    def broken_overwrite(day, files, roots, table, layout, fdir, con=None):
        res = {}
        for name, root in roots.items():
            path = morning.diary_entry_path(root, day, name, layout)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:                                          # no exclusive create: the entry is rewritten
                f.write("rewritten\n")
            res[name] = {"status": "written", "path": path}
        return res

    def test_2_second_run_never_overwrites(self):
        self.run_read(self.real_stamper())
        first = self.midnight()
        p = first["Bravo-Diary"]["path"]
        before = open(p, "rb").read()
        self.midnight(self.broken_overwrite)
        self.assertNotEqual(open(p, "rb").read(), before)                       # caught: the broken writer changed the entry
        shutil.rmtree(self.notes)
        first = self.midnight()
        before = dict((d, open(r["path"], "rb").read()) for d, r in first.items())
        opened = []
        real_os_open = os.open
        def spy(path, flags, *a, **k):
            if os.path.exists(path):
                opened.append((path, flags))
            return real_os_open(path, flags, *a, **k)
        os.open = spy
        try:
            again = self.midnight()
        finally:
            os.open = real_os_open
        self.assertEqual({d: r["status"] for d, r in again.items()}, {"Bravo-Diary": "exists", "Main-Diary": "exists"})
        self.assertEqual(dict((d, open(r["path"], "rb").read()) for d, r in first.items()), before)
        self.assertEqual([o for o in opened if "diary" in o[0]], [])             # no existing entry was even opened
        with self.assertRaises(FileExistsError):                                 # and a forced exclusive create is refused
            morning._excl_write(first["Bravo-Diary"]["path"], "x")

    # ---- 3
    def test_3_part_b_item_never_in_main_diary(self):
        self.run_read(self.real_stamper())
        part_b_key = self.k(self.eli)
        orig = routing.route
        routing.route = lambda part, table: table["main_diary"]               # broken routing: ignores the part of life
        try:
            bad = self.midnight()
        finally:
            routing.route = orig
        self.assertIn(part_b_key, diary_keys.read_front_matter(open(bad["Main-Diary"]["path"], encoding="utf-8").read())["keys"])   # caught: part-b's key leaks into main
        shutil.rmtree(self.notes)
        self.midnight()
        main_keys = diary_keys.read_front_matter(self.text("Main-Diary"))["keys"]
        self.assertNotIn(part_b_key, main_keys)
        self.assertIn(part_b_key, diary_keys.read_front_matter(self.text("Bravo-Diary"))["keys"])
        self.assertIn(self.k(self.pat_org), main_keys)                          # the organization-only sender, no desk owns it: main
        self.assertNotIn("Eli", self.text("Main-Diary"))

    # ---- 4
    def test_4_staged_email_gets_sender_key(self):
        broken = lambda emails, evts, tasks: [dict(i, keys=[]) for i in morning._live_stamper(self.db, LABELS)(emails, evts, tasks)]   # noqa: E731
        out = self.run_read(broken)
        self.assertNotIn(self.k(self.eli), out["form"]["thing_keys"])           # caught: no key stamped
        shutil.rmtree(self.env.records)
        for f in os.listdir(os.path.join(self.env.front, "catalogue", "morning")):
            os.remove(os.path.join(self.env.front, "catalogue", "morning", f))
        self.env.deliver("th-D", "msg-D1", "Eli <eli@partb.example>", "again", "2026-11-15 10:00", "Example-Label-B",
                         t4.triage_of({"needs_me": "yes", "do_or_know": "do", "how_soon": "2 days", "life_area": "gigs"}), "More.")
        self.con.execute("INSERT INTO messages(id, from_addr) VALUES(?,?)", (t4.hexid("msg-D1"), "eli@partb.example"))
        self.con.commit()
        self.env.ingest()
        m = t4.FakeModel(self.env, t4.reply(what_changed=["Another note from the same talent contact arrived."],
                                            form={"needs_him": [t4.need("Reply to the note", "msg-D1")]}, coverage=t4.used("msg-D1")))
        out = morning.run_morning(m, DAY, "desk-a", self.env.records, calendar=self.evts, tasks=self.tasks, stamper=self.real_stamper())
        self.assertTrue(out["ok"], out)
        self.assertIn(self.k(self.eli), out["form"]["thing_keys"])
        self.midnight()
        self.assertIn(self.k(self.eli), diary_keys.read_front_matter(self.text("Bravo-Diary"))["keys"])

    # ---- 5
    def test_5_prose_only_name_gets_no_key(self):
        def prose_stamper(emails, evts, tasks):                                  # broken: looks the name up in the email text
            items = morning._live_stamper(self.db, LABELS)(emails, evts, tasks)
            for it in items:
                if it["id"] == self.mids["msg-C1"]:
                    it["keys"] = [self.k(self.wren)]
            return items
        bad = self.run_read(prose_stamper)
        self.assertIn(self.k(self.wren), bad["form"]["thing_keys"])             # caught
        shutil.rmtree(self.env.records)
        shutil.rmtree(os.path.join(self.env.front, "catalogue", "morning"))
        self.env.ids.clear()
        for f in ("msg-A1", "msg-B1", "msg-C1"):
            self.env.hx(f)
        os.environ.pop("AGE_FRONT_ROOM", None)
        # a fresh front room with the same three messages
        self.env.close()
        self.env = t4.Env()
        e = self.env
        t = t4.triage_of({"needs_me": "yes", "do_or_know": "do", "how_soon": "2 days", "life_area": "gigs"})
        e.deliver("th-C", "msg-C1", "S <stranger@nowhere.example>", "Hello", "2026-11-15 09:30", "read-a", t, "Wren Prosewrenplant said hello.")
        e.deliver("th-A", "msg-A1", "Eli <eli@partb.example>", "Tryout", "2026-11-15 08:00", "Example-Label-B", t, "Please send the tape.")
        e.deliver("th-B", "msg-B1", "Pat <pat@planorg.example>", "Invoice", "2026-11-15 09:00", "read-a", t, "The invoice is ready.")
        e.ingest()
        out = self.run_read(self.real_stamper())
        self.assertNotIn(self.k(self.wren), out["form"]["thing_keys"])
        c_item = [i for i in out["form"]["stamped"] if i["id"] == self.mids["msg-C1"]][0]
        self.assertEqual(c_item["keys"], [])
        self.midnight()
        self.assertNotIn(self.k(self.wren), diary_keys.read_front_matter(self.text("Main-Diary"))["keys"])

    # ---- the rest: event key, unlinked task, organization key, stamp, index
    def test_6_event_task_org_stamp_and_index(self):
        out = self.run_read(self.real_stamper())
        by = {(i["source"], i["id"]): i for i in out["form"]["stamped"]}
        self.assertEqual(by[("calendar", "EVT1")]["keys"], ["event:calendar:EVT1"])
        self.assertEqual(by[("task", "T1")]["keys"], [])                        # a task is stamped only with a key it is already linked to
        self.assertEqual(by[("email", self.mids["msg-B1"])]["keys"], [self.k(self.pat_org)])
        self.assertEqual(by[("email", self.mids["msg-A1"])]["life_part"], "part-b")
        self.assertNotIn("eli@partb.example", json.dumps(out["form"]))          # the sender's address is not kept in the form
        # a task already linked to a person gets that key and only that
        t = sg.thing(self.con, "item", "Task thing", key="item:task-T1")
        proj = sg.thing(self.con, "project", "Plantedproject")
        self.con.execute("UPDATE kg_things SET legacy_ref='task:T1' WHERE id=?", (t,))
        sg.add_link(self.con, t, "part_of", proj, "code", "sure", "code")
        self.con.commit()
        self.assertEqual(stamp_keys.task_keys(self.con, "T1"), [self.k(proj)])
        res = self.midnight()
        text = self.text("Main-Diary")
        self.assertIn("stamp: machine draft, unconfirmed", text)
        self.assertIn("confidence: low", text)
        self.assertEqual(text.count("# Midnight diary entry"), 1)
        for name, r in res.items():                                             # the index follows the files (4.4)
            sd.index_entry(self.con, name, r["path"], self.notes)
            rows = self.con.execute("SELECT entry_path, keys_mentioned FROM diary_index WHERE diary=?", (name,)).fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(json.loads(rows[0][1]), diary_keys.read_front_matter(open(r["path"], encoding="utf-8").read())["mentions"])
        got = sd.entries_mentioning(self.con, self.k(self.eli))      # (not the diary= filter: it passes no bindings, 4.4's bug, reported)
        self.assertEqual([g["diary"] for g in got], ["Bravo-Diary"])

    def test_7_hook_called_per_written_entry(self):
        self.run_read(self.real_stamper())
        seen = []
        files = morning.find_staged(self.env.records, DAY, "desk-a")
        con = sqlite3.connect("file:%s?mode=ro" % self.db, uri=True)
        morning.midnight_entries(DAY, files, self.roots, TABLE, "tree", os.path.join(self.env.front, "catalogue", "morning"),
                                 con=con, index=lambda n, p: seen.append(n))
        self.assertEqual(sorted(seen), ["Bravo-Diary", "Main-Diary"])
        self.assertEqual(morning.midnight_entries(DAY, files, self.roots, TABLE, "tree", os.path.join(self.env.front, "catalogue", "morning"),
                                                  con=con, index=lambda n, p: seen.append("again"))["Bravo-Diary"]["status"], "exists")
        self.assertNotIn("again", seen)
        con.close()

    def test_8_desk_names_not_hard_coded(self):
        for f in ("stamp_keys.py", "gcjobs.py"):
            self.assertNotIn("Bravo-Diary", open(os.path.join(ROOT, f), encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
