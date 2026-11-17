"""synthesize.py (STEP 6a, 6a-2). Temp DBs only; the AI is a FAKE function, the real claude CLI is never run here
(the one subprocess test replaces subprocess.run). The fake world has tasks, calendar and email as equal inputs."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import datetime as dt, json, os, sqlite3, subprocess, sys, tempfile, unittest
from unittest import mock
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import step3_fixture  # noqa: E402
import migrate, store, store_items  # noqa: E402
import run as er  # noqa: E402
import synthesize as syn  # noqa: E402

NOW = "2026-11-13T09:00:00+00:00"
ME = "owner@me.test"


def ms(iso):
    return int(dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)


class PicBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.tmp.name, "rig.db")
        c = sqlite3.connect(self.p, isolation_level=None)
        for n, path in migrate.list_migrations():
            migrate.apply_file(c, path, n)
            # step 2.6: this fixture seeds old-table rows, which migration 020 freezes in a real database
            for (_t,) in c.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'frozen!_%' ESCAPE '!'").fetchall():
                c.execute("DROP TRIGGER " + _t)
        step3_fixture.seed_domain_vocab(c)
        c.close()
        store.set_path(self.p)
        self._old = {k: os.environ.get(k) for k in ("AGE_NOW", "AGE_NOTES_ROOT")}
        os.environ["AGE_NOW"] = NOW
        os.environ["AGE_NOTES_ROOT"] = self.tmp.name
        self._old_lm = syn.LIFE_MAP_PATH
        syn.LIFE_MAP_PATH = os.path.join(self.tmp.name, "no-life-map-here.md")  # tests set their own when needed
        self.n = 0
        self._old_sg = syn.STORE_GUESSES
        syn.STORE_GUESSES = getattr(self, "STORE", True)   # the old saving path is what these tests exercise; NoGuesses turns it off
        self.world()

    def tearDown(self):
        syn.STORE_GUESSES = self._old_sg
        syn.LIFE_MAP_PATH = self._old_lm
        store.set_path(None)
        for k, v in self._old.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.tmp.cleanup()

    def sql(self, q, a=()):
        c = sqlite3.connect(self.p)
        c.execute(q, a)
        c.commit()
        c.close()

    def msg(self, frm, subj, iso, name=""):
        self.n += 1
        self.sql("INSERT INTO messages(id,thread_id,internal_date,label_ids,from_addr,from_name,to_addrs,cc_addrs,subject,is_sent) "
                 "VALUES(?,?,?,?,?,?,?,?,?,0)", ("m%d" % self.n, "t%d" % self.n, ms(iso), json.dumps(["INBOX"]), frm, name,
                                                 json.dumps([ME]), "[]", subj))

    def event(self, eid, start, summary):
        self.sql("INSERT INTO calendar_events(id,start,end,all_day,status,organizer_email,attendee_emails,summary) VALUES(?,?,?,0,'confirmed','',?,?)",
                 (eid, start, start, "[]", summary))

    def task(self, tid, title, due=None, status="needsAction", completed=None):
        self.sql("INSERT INTO tasks(id,list_id,title,status,due,completed,updated) VALUES(?,?,?,?,?,?,?)",
                 (tid, "l", title, status, due, completed, "2026-11-10T00:00:00Z"))

    def world(self):
        self.sql("INSERT INTO labels(id,name,type) VALUES('INBOX','INBOX','system')")
        self.msg("agent-one@agency-one.test", "Tryout sides for Thursday", "2026-11-12T10:00:00Z", "Person-X")
        self.msg("person-y@agency-two.test", "Booking update", "2026-11-11T10:00:00Z", "Person-Y")
        self.msg("shop@deals.test", "Big sale", "2026-11-10T10:00:00Z")
        self.task("k1", "Buy travel insurance for the trip", "2026-11-16")
        self.task("k2", "Book the checkup", "2026-11-20")
        self.task("k3", "Project-One Academy lesson 4 edit", "2026-12-05")
        self.task("k4", "Old finished thing", status="completed", completed="2026-10-01T00:00:00Z")
        self.event("e1", "2026-11-14T10:00:00Z", "boiler visit")
        self.event("e2", "2026-11-15T09:00:00Z", "Exampleton Airlines call")
        self.event("e3", "2026-11-17T15:00:00Z", "Example call Videochat")
        self.event("e4", "2026-11-18T18:00:00Z", "Mom and Dad anniversaries dinner")
        self.event("e5", "2027-01-10T01:00:00Z", "Flight to Exampleton")
        store_items.backfill_items()
        er.run()

    def tok(self, title_like):
        for it in store_items.items_between("0000", "9999"):
            if title_like.lower() in (it["title"] or "").lower():
                return {"task": "t", "event": "c", "email": "m"}[it["kind"]] + str(it["id"])
        raise KeyError(title_like)

    def reply(self, drop=(), extra=None):
        T = self.tok
        near = [
            {"project": "p1", "item": T("travel insurance"), "line": "Travel insurance must be bought before the January trip, so do it this weekend.", "confidence": "sure", "cites": [T("travel insurance"), T("Flight to Exampleton")]},
            {"project": "p4", "item": T("the checkup"), "line": "The checkup is due on the 20th; it keeps your health on track.", "confidence": "sure", "cites": [T("the checkup")]},
            {"project": "p4", "item": T("boiler"), "line": "The boiler visit tomorrow keeps the house warm for the winter.", "confidence": "sure", "cites": [T("boiler")]},
            {"project": "p4", "item": T("anniversaries"), "line": "The anniversaries dinner on the 18th is a family fixed point.", "confidence": "guess", "cites": [T("anniversaries")]},
            {"project": "p3", "item": T("Example call Videochat"), "line": "The Example call Videochat on the 17th is a Project-One call you should prepare for.", "confidence": "sure", "cites": [T("Example call Videochat"), T("Project-One Academy")]},
            {"project": "p1", "item": T("Exampleton Airlines call"), "line": "The Exampleton Airlines call Sunday settles the January flight.", "confidence": "sure", "cites": [T("Exampleton Airlines call")]},
            {"project": "p2", "item": T("Tryout sides"), "line": "Person-X's tryout sides need a reply from you.", "confidence": "sure", "cites": [T("Tryout sides"), T("Booking update")]},
        ]
        near = [n for n in near if not any(d in n["line"] for d in drop)]
        r = {"projects": [
            {"id": "p1", "name": "The Example trip in January", "storyline": "The January Example trip is booked and the loose ends are insurance and a flight call.",
             "confidence": "sure", "cites": [T("Flight to Exampleton"), T("travel insurance")], "month_state": "This month is about insurance and the airline.", "month_cites": [T("Exampleton Airlines call")]},
            {"id": "p2", "name": "Gigs, with Agency-One (Person-X) and Agency-Two (Person-Y)", "storyline": "Gigs work is moving with both agents.", "confidence": "sure",
             "cites": [T("Tryout sides"), T("Booking update")], "month_state": "Gigs is heating up.", "month_cites": [T("Tryout sides")]},
            {"id": "p3", "name": "Project-One Academy", "storyline": "Project-One is the course business you keep building.", "confidence": "sure", "cites": [T("Project-One Academy")],
             "month_state": "Lesson 4 is the next step.", "month_cites": [T("Project-One Academy")]},
            {"id": "p4", "name": "Family and home", "storyline": "Family and the house take steady care.", "confidence": "sure", "cites": [T("anniversaries"), T("boiler")],
             "month_state": "Anniversaries and the checkup land this month.", "month_cites": [T("anniversaries")]},
        ], "near": near, "orphans": [],
            "questions": {"1": [{"q": "Is Project-One one project or two?", "guess": "one", "settles": 2, "cites": [T("Project-One Academy")], "subject": "p3"},
                                {"q": "Is there a missing project?", "guess": "", "settles": 5, "cites": [T("Big sale")]}],
                          "2": [{"q": "Is gigs heating up?", "guess": "yes", "settles": 1, "cites": [T("Tryout sides")], "subject": "p2"}], "3": []},
            "housekeeping": [{"line": "Want a filter for the sale emails?", "cites": [T("Big sale")]}]}
        if extra:
            extra(r)
        return json.dumps(r)

    def run_syn(self, reply=None, layers=(1, 2, 3)):
        seen = []
        res = syn.run(ai=lambda prompt: (seen.append(prompt), reply if reply is not None else self.reply())[1], layers=layers)
        self.prompt = seen[0]
        return res


class TestSynthesize(PicBase):
    def test_bundle_has_all_three_sources_and_ids(self):
        b = syn.build_bundle()
        self.assertGreaterEqual(b["counts"]["tasks"], 3)
        self.assertGreaterEqual(b["counts"]["calendar"], 5)
        self.assertGreaterEqual(b["counts"]["email"], 2)
        self.assertNotIn("Old finished thing", " ".join(b["sections"]["tasks"]))          # done 6 weeks ago
        self.assertTrue(all(r.split(" | ")[0][0] in "tcmefhl" for k in b["sections"] for r in b["sections"][k]))
        self.assertEqual(len(b["must_place"]), 6)                                          # 2 tasks + 4 events in the next 14 days

    def test_prompt_marks_data_untrusted_and_bounded(self):
        self.run_syn()
        self.assertIn("UNTRUSTED", self.prompt)
        self.assertRegex(self.prompt, r"BEGIN DATA[0-9A-F]{24}")
        self.assertIn("Go UP the inference chain", self.prompt)

    def test_good_run_saves_three_layers_and_coverage(self):
        res = self.run_syn()
        self.assertEqual(res["dropped"], {"projects": 0, "month_state": 0, "near": 0, "questions": 0, "housekeeping": 0, "orphans": 0})
        pic = syn.read_picture()
        self.assertEqual([p["name"][:8] for p in pic["projects"]], ["The Exam", "Gigs, wi", "Project-", "Family a"])
        self.assertTrue(all(p["month_state"] and p["cites"][0] for p in pic["projects"]))
        self.assertEqual(len(pic["near"]), 7)
        self.assertTrue(all(n["projects"] for n in pic["near"]))
        kinds = {t[0] for t in sqlite3.connect(self.p).execute("SELECT kind FROM kg_things WHERE key LIKE 'item:%'")}
        self.assertEqual(kinds, {"item"})
        who = {r[0] for r in sqlite3.connect(self.p).execute("SELECT who FROM kg_facts WHERE source_ref=?", (syn.SOURCE_REF,))}
        self.assertEqual(who, {"ai_guess"})
        cov = res["coverage"]
        for s in syn.SOURCES:
            self.assertGreater(cov["all"][s], 0)
        self.assertEqual({k: len(pic["questions"][k]) for k in "123H"}, {"1": 2, "2": 1, "3": 0, "H": 1})
        q = store.proposals(kind="picture-q", status="open")
        self.assertEqual(len(q), 4)
        self.assertTrue(q[0]["question"].startswith("[L1]"))

    def test_guess_line_says_i_think(self):
        self.run_syn()
        line = next(n["line"] for n in syn.read_picture()["near"] if "anniversaries" in n["line"])
        self.assertTrue(line.startswith("I think "))

    def test_line_without_a_real_cite_is_dropped_and_counted(self):
        def bad(r):
            r["near"].append({"project": "p1", "item": "t99999", "line": "Invented thing.", "confidence": "sure", "cites": ["t99999"]})
            r["near"].append({"project": "p1", "item": self.tok("boiler"), "line": "Duplicate primary.", "confidence": "sure", "cites": ["zzz"]})
            r["projects"].append({"id": "p5", "name": "Ghost", "storyline": "Nothing behind it.", "confidence": "sure", "cites": ["t424242"]})
            r["questions"]["3"].append({"q": "Fake?", "settles": 9, "cites": ["m31337"]})
            r["housekeeping"].append({"line": "No cite", "cites": []})
        res = self.run_syn(self.reply(extra=bad))
        self.assertEqual(res["dropped"]["near"], 2)
        self.assertEqual(res["dropped"]["projects"], 1)
        self.assertEqual(res["dropped"]["questions"], 1)
        self.assertEqual(res["dropped"]["housekeeping"], 1)
        names = [p["name"] for p in syn.read_picture()["projects"]]
        self.assertNotIn("Ghost", names)
        self.assertEqual(len(syn.read_picture()["near"]), 7)

    def test_near_line_with_unknown_project_becomes_a_layer1_question(self):
        def odd(r):
            r["near"][2]["project"] = "p9"
        self.run_syn(self.reply(extra=odd))
        pic = syn.read_picture()
        self.assertEqual(len(pic["near"]), 6)
        texts = [q["question"] for q in pic["questions"]["1"]]
        self.assertTrue(any("boiler" in t for t in texts))

    def test_rerun_replaces_its_own_earlier_output(self):
        self.run_syn()
        self.run_syn(self.reply(drop=("boiler",), extra=lambda r: r["projects"].pop(2) and None))
        pic = syn.read_picture()
        self.assertEqual(len(pic["projects"]), 3)
        self.assertNotIn("Project-One Academy", [p["name"] for p in pic["projects"]])
        self.assertFalse(any("boiler" in n["line"] for n in pic["near"]))
        # 4 again plus one: the Project-One near line lost its project and became a layer-1 question; the old rows were retired
        self.assertEqual(len(store.proposals(kind="picture-q", status="open")), 5)
        again = len(pic["near"])
        self.run_syn(self.reply(drop=("boiler",), extra=lambda r: r["projects"].pop(2) and None))
        self.assertEqual(len(syn.read_picture()["near"]), again)

    def test_layers_2_3_keep_the_project_list(self):
        self.run_syn()
        before = [(p["key"], p["storyline"]) for p in syn.read_picture()["projects"]]

        def re23(r):
            r["projects"] = [{"id": "p%d" % i, "month_state": "Fresh month line %d." % i, "month_cites": [self.tok("Project-One Academy")]} for i in (1, 2, 3, 4)]
            r["questions"]["1"] = [{"q": "Should not be saved", "settles": 1, "cites": [self.tok("Big sale")]}]
        res = self.run_syn(self.reply(extra=re23), layers=(2, 3))
        pic = syn.read_picture()
        self.assertEqual([(p["key"], p["storyline"]) for p in pic["projects"]], before)
        self.assertTrue(all(p["month_state"].startswith("Fresh month") for p in pic["projects"]))
        self.assertIn("THE PROJECT LIST IS FIXED", self.prompt)
        self.assertNotIn("Should not be saved", " ".join(q["question"] for q in pic["questions"]["1"]))
        self.assertGreater(res["coverage"]["layer3"]["calendar"], 0)

    def test_layers_2_3_refuse_without_a_project_list(self):
        with self.assertRaises(syn.SynthError):
            self.run_syn(layers=(2, 3))

    def test_his_answer_beats_the_guess_and_is_shown_as_his(self):
        self.run_syn()
        store.record_answer("What is Project-One?", "It is my teaching business", "test", "2026-11-13", "project", "Project-One Academy", "storyline",
                            "Project-One is my teaching business.")
        self.run_syn()
        p = next(p for p in syn.read_picture()["projects"] if p["name"] == "Project-One Academy")
        self.assertEqual(p["storyline"], "Project-One is my teaching business.")
        self.assertTrue(p["his_word"])

    def test_bad_json_saves_nothing(self):
        with self.assertRaises(syn.SynthError):
            self.run_syn("I cannot do that")
        self.assertEqual(syn.read_picture()["projects"], [])

    def test_reply_in_code_fence_still_parses(self):
        self.run_syn("Here you go:\n```json\n" + self.reply() + "\n```")
        self.assertEqual(len(syn.read_picture()["projects"]), 4)

    def test_cli_call_has_no_tools_and_no_typed_model_id(self):
        out = json.dumps({"type": "result", "is_error": False, "result": "{}"})
        with mock.patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, out, "")) as m:
            self.assertEqual(syn.claude_ai("hello"), "{}")
        argv = m.call_args[0][0]
        self.assertEqual(argv[argv.index("--tools") + 1], "")
        self.assertIn("--output-format", argv)
        self.assertEqual(m.call_args[1]["input"], "hello")
        with open(os.path.join(ROOT, "synthesize.py"), encoding="utf-8") as f:
            self.assertNotIn("sonnet", f.read().lower())

    def test_session_time_only(self):
        for f in ("daily.py", "pull.py", "run.py"):
            with open(os.path.join(ROOT, f), encoding="utf-8") as fh:
                self.assertNotIn("synthesize", fh.read(), f)


    def test_life_map_loader_parses_headings_and_skips_records(self):
        p = os.path.join(self.tmp.name, "life-map.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write("# Life Map\n\n## 2027 Win\nSmall, minimal and mobile.\n\n"
                    "*Previous 2027 Win (2026-10-18), superseded: keep life small.*\n\nmore record text\n\n"
                    "## Weekly Win\nGet the system back online.\n\n## Daily Win\n(transient)\n")
        lm = syn.load_life_map(p)
        self.assertEqual(len(lm), 2)
        self.assertEqual(lm[0], "(2027) Small, minimal and mobile.")
        self.assertEqual(lm[1], "(this week) Get the system back online.")
        self.assertNotIn("superseded", " ".join(lm))
        self.assertEqual(syn.load_life_map(os.path.join(self.tmp.name, "absent.md")), [])

    def test_bundle_and_prompt_carry_his_direction(self):
        p = os.path.join(self.tmp.name, "life-map.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write("## 2027 Win\nSmall, minimal and mobile.\n")
        syn.LIFE_MAP_PATH = p
        b = syn.build_bundle()
        self.assertEqual(b["counts"]["direction"], 1)
        self.assertEqual(b["sections"]["direction"], ["(2027) Small, minimal and mobile."])
        prompt = syn.build_prompt(b, (1, 2, 3))
        self.assertIn("HIS STATED DIRECTION", prompt)
        self.assertIn("(2027) Small, minimal and mobile.", prompt)
        self.assertIn("update the goal, or just make it a task", prompt)

    def test_missing_life_map_continues_without_it(self):
        syn.LIFE_MAP_PATH = os.path.join(self.tmp.name, "absent.md")
        b = syn.build_bundle()
        self.assertEqual(b["sections"]["direction"], [])
        self.assertEqual(b["counts"]["direction"], 0)
        self.run_syn()  # the full pass still works; the screen shows the loud warning instead
        self.assertIn("HIS CONFIRMED WORD", self.prompt)  # the prompt still builds without the map

LIFE_FACT = "No open tryouts as of 2026-11-13; expires when an tryout opens"



class TestNoGuessesStored(PicBase):
    """Phase 2 step 2.5 planted case: with the shipped setting a synthesize run writes no machine guesses into the model."""
    STORE = False

    def test_run_writes_no_guesses(self):
        con = sqlite3.connect(self.p)
        before = tuple(con.execute("SELECT (SELECT count(*) FROM kg_things),(SELECT count(*) FROM kg_facts),"
                                   "(SELECT count(*) FROM kg_links)").fetchone())
        res = self.run_syn()
        after = tuple(con.execute("SELECT (SELECT count(*) FROM kg_things),(SELECT count(*) FROM kg_facts),"
                                  "(SELECT count(*) FROM kg_links)").fetchone())
        self.assertEqual(before, after)
        self.assertEqual(con.execute("SELECT count(*) FROM kg_facts WHERE who IN ('ai_guess','ai_research') OR "
                                     "(who='code' AND certainty='likely' AND source_ref=?)", (syn.SOURCE_REF,)).fetchone()[0], 0)
        self.assertTrue(res["saved"])                                            # the run itself still completes, questions still queue
        self.assertGreater(len(store.proposals(kind="picture-q", status="open")), 0)


class TestHisWord(PicBase):
    """STEP 6 follow-up: the picture must never contradict his saved word. An uncle in the Family circle whose
    email the fake AI places under Advice & guidance, and a fake AI line praising tryout test-reels while
    his "No open tryouts" fact stands."""

    def uncle_world(self):
        self.sql("INSERT INTO people(id,label,tier_guess) VALUES(11,'Orlo Tanglewick','normal')")
        self.sql("INSERT INTO addresses(id,address,person_id) VALUES(7,'orlo@example.test',11)")
        self.sql("INSERT INTO circles(id,name,kind_guess,domain_guess) VALUES(3,'Family','standing','part-a')")
        self.sql("INSERT INTO circle_members(id,circle_id,person_id) VALUES(5,3,11)")
        store.graph_write("copy_legacy")
        store.record_answer("Anything open?", LIFE_FACT, "test", "2026-11-13", "topic", "part-b", "life_fact", LIFE_FACT)
        self.msg("orlo@example.test", "Catching up soon", "2026-11-12T12:00:00Z", "Orlo Tanglewick")
        store_items.backfill_items()
        er.run()

    def uncle_reply(self):
        T = self.tok
        r = json.loads(self.reply())
        r["projects"].append({"id": "p5", "name": "Advice & guidance", "storyline": "A new advice prospect is on the table.",
                              "confidence": "sure", "cites": [T("Catching up soon")],
                              "month_state": "A advice prospect this month.", "month_cites": [T("Catching up soon")]})
        r["near"].append({"project": "p5", "item": T("Catching up soon"),
                          "line": "Orlo's email is a advice prospect worth pursuing.", "confidence": "sure",
                          "cites": [T("Catching up soon")]})
        return json.dumps(r)

    def test_bundle_carries_his_word_section(self):
        self.uncle_world()
        b = syn.build_bundle()
        hw = " ".join(b["sections"]["his_word"])
        self.assertGreater(b["counts"]["his_word"], 0)
        self.assertIn("Orlo Tanglewick", hw)
        self.assertIn("part-a", hw)                       # the Family circle's domain, from his answers
        self.assertIn(LIFE_FACT, hw)                        # his life fact, word for word
        self.assertIn("circle_members", hw)                 # the legacy link he answered for
        prompt = syn.build_prompt(b, (1, 2, 3))
        self.assertIn("HIS CONFIRMED WORD", prompt)
        self.assertIn("never contradict", prompt)

    def test_synthesize_turns_contradictions_into_questions(self):
        self.uncle_world()
        res = self.run_syn(self.uncle_reply())
        self.assertEqual(res["counts"]["contradictions"], 3)  # uncle near line, uncle month line, tryouts near line
        pic = syn.read_picture()
        texts = " ".join(n["line"] for n in pic["near"])
        self.assertNotIn("advice prospect", texts)        # the uncle line is not saved as a statement
        self.assertNotIn("Orlo's email", texts)
        qs = [q["question"] for q in pic["questions"]["3"]]
        self.assertEqual(len(qs), 2)
        self.assertTrue(all("His word says otherwise" in q for q in qs))
        q2 = [q["question"] for q in pic["questions"]["2"]]
        self.assertEqual(len(q2), 2)                        # the AI's own question, plus the uncle month line
        self.assertTrue(sum("His word says otherwise" in q for q in q2) == 1)
        names = [p["name"] for p in pic["projects"]]
        self.assertIn("Advice & guidance", names)       # the project stays; only the contradicting line moved

    def test_clean_reply_in_uncle_world_still_passes(self):
        self.uncle_world()
        res = self.run_syn()                                # the base reply's tryouts line contradicts his fact
        self.assertEqual(res["counts"]["contradictions"], 1)
        qs = [q["question"] for q in syn.read_picture()["questions"]["3"]]
        self.assertTrue(any("tryout" in q for q in qs))
        self.assertFalse(any("tryout sides need a reply" in n["line"] for n in syn.read_picture()["near"]))


if __name__ == "__main__":
    unittest.main()
