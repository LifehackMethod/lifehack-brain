"""Phase 3 step 3.1: organizations. Synthetic data on temp databases; never the live rig.db.
Planted cases: (1) a company or circle with no organization, a duplicate, or a deleted old thing is reported by check_moves;
(2) a code-written member_of / part_of / reports_to / levels_above_me on an organization is refused, in the front door AND in
the database; (3) a rebuild reproduces organizations with the same keys (gc check clean), and a planted difference is reported;
(4) the one reader (sender_context, behind gc who) gives the same circles before and after the move, and a planted loss shows."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import os, sqlite3, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import migrate, model_check, org_moves, store, store_graph as sg  # noqa: E402


def who(c):
    return sorted((x["name"], x["role"]) for x in store.sender_context("jo@example.test")["circles"])


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.tmp.name, "rig.db")
        c = sqlite3.connect(self.p, isolation_level=None)
        for n, path in migrate.list_migrations():
            migrate.apply_file(c, path, n)
        c.close()
        store.set_path(self.p)
        self.c = sqlite3.connect(self.p, isolation_level=None)
        self.c.row_factory = None
        c = self.c
        import common as ec
        sg.thing(c, "world", "world")
        ec.seed_settings(c)
        # two companies (one his), two circles (one with two members, one with one member), a person with an address
        sg.record_answer(c, "q", "Acme is the studio", "t", "2026-11-01", "company", "Acme Studio", "relationship", "the studio he works with")
        sg.thing(c, "company", "Beta Corp", created_by="ai_research")
        self.fam = sg.thing(c, "circle", "Test Family", legacy_ref="circles:1")
        self.biz = sg.thing(c, "circle", "Test Business", legacy_ref="circles:2")
        self.jo = sg.thing(c, "person", "Jo Example", key="person:legacy-1")
        self.al = sg.thing(c, "person", "Al Example", key="person:legacy-2")
        # his two membership lines are his recorded words (answers), so a rebuild replays them
        self.ans = self.say("person:legacy-1", "Jo Example", "circle:test family", "Jo is family")
        self.say("person:legacy-2", "Al Example", "circle:test business", "Al is my partner in the business", role=None)
        self.say("person:legacy-2", "Al Example", "circle:test family", "Al is family too", role=None)
        self.cy = sg.thing(c, "person", "Cy Example", key="person:legacy-3")

    def say(self, pkey, pname, ckey, words, role=None):
        aid = self.c.execute("INSERT INTO kg_answers(question,words,asked_by,said_on,subject_key,subject_kind,subject_name,fact_key,value,recorded_at,words_kind) "
                             "VALUES('q',?,'t','2026-11-01',?,'person',?,'link:member_of',?,'2026-11-01T00:00:00Z','verbatim')", (words, pkey, pname, ckey)).lastrowid
        row = dict(zip(sg._ACOLS, self.c.execute("SELECT %s FROM kg_answers WHERE id=?" % ",".join(sg._ACOLS), (aid,)).fetchone()))
        sg._apply_answer(self.c, row)
        return aid

    def tearDown(self):
        self.c.close()
        store.set_path(None)
        self.tmp.cleanup()

    def move(self):
        self.c.execute("BEGIN IMMEDIATE")
        r = (org_moves.record_moves(self.c), org_moves.apply_moves(self.c), org_moves.ask_what_kind(self.c))
        self.c.execute("COMMIT")
        return r

    def x(self, sql, args=()):
        return self.c.execute(sql, args).fetchall()


class Moves(Base):
    def test_every_old_company_and_circle_has_one_organization_and_a_key_row_nothing_deleted(self):
        sg.add_link(self.c, self.cy, "member_of", self.fam, "code", "likely", "legacy", "circle_members:2", role="uncle")   # the code's own line
        before = self.x("SELECT count(*) FROM kg_things")[0][0]
        rec, applied, _ = self.move()
        self.assertEqual(rec, {"company": 2, "circle": 2})
        self.assertEqual(org_moves.check_moves(self.c), [])
        self.assertEqual(self.x("SELECT count(*) FROM kg_things")[0][0], before + 4)      # nothing deleted, four organizations added
        self.assertEqual(self.x("SELECT count(*) FROM thing_keys WHERE kind='organization'")[0][0], 4)
        self.assertEqual(self.x("SELECT count(*) FROM thing_keys t JOIN org_moves m ON m.new_key=t.key AND t.made_from=m.old_key")[0][0], 4)
        types = dict(self.x("SELECT m.old_kind, f.value FROM org_moves m JOIN kg_things t ON t.key=m.new_key JOIN kg_facts f ON f.thing_id=t.id "
                            "AND f.fact_key='org_type' AND f.replaced_by IS NULL GROUP BY m.old_kind"))
        self.assertEqual(types, {"company": "company", "circle": "group"})
        # his words follow the company; his membership line moved with its answer; the code's own line did not
        self.assertEqual(self.x("SELECT f.value, f.who FROM kg_current_facts f JOIN org_moves m ON m.new_key=f.thing_key WHERE m.old_key='company:acme studio' AND f.fact_key='relationship'"),
                         [("the studio he works with", "owner")])
        self.assertEqual(self.x("SELECT l.role, l.who, l.answer_id FROM kg_current_links l JOIN org_moves m ON m.new_key=l.to_key WHERE m.old_key='circle:test family' AND l.kind='member_of'"),
                         [(None, "owner", self.ans), (None, "owner", self.ans + 2)])
        self.assertEqual(self.x("SELECT count(*) FROM kg_current_links l JOIN kg_things t ON t.id=l.to_id WHERE t.key='circle:test family' AND l.who='code'")[0][0], 1)

    def test_rerun_changes_nothing(self):
        self.move()
        n = self.x("SELECT (SELECT count(*) FROM kg_facts)+(SELECT count(*) FROM kg_links)+(SELECT count(*) FROM kg_things)+(SELECT count(*) FROM org_moves)")
        self.move()
        self.assertEqual(self.x("SELECT (SELECT count(*) FROM kg_facts)+(SELECT count(*) FROM kg_links)+(SELECT count(*) FROM kg_things)+(SELECT count(*) FROM org_moves)"), n)

    def test_circle_that_may_not_be_a_group_becomes_a_question_not_a_guess(self):
        self.move()
        self.assertEqual(self.x("SELECT count(*) FROM queue WHERE status='open'")[0][0], 0)     # not in his everyday list
        qs = org_moves.onboarding_set(self.c)                                                    # held for the sitting
        keys = {r[1] for r in qs}
        biz = self.x("SELECT new_key FROM org_moves WHERE old_key='circle:test business'")[0][0]
        fam = self.x("SELECT new_key FROM org_moves WHERE old_key='circle:test family'")[0][0]
        self.assertIn(biz, keys)          # one member: asked
        self.assertNotIn(fam, keys)       # a family with members: not asked
        self.assertEqual(self.x("SELECT who, certainty FROM kg_current_facts WHERE thing_key=? AND fact_key='org_type'", (biz,)), [("code", "likely")])

    def test_PLANTED_missing_duplicate_or_deleted_is_reported(self):
        self.move()
        self.assertEqual(org_moves.check_moves(self.c), [])
        sg.thing(self.c, "company", "Gamma Ltd")                       # a company with no organization
        bad = org_moves.check_moves(self.c)
        self.assertTrue(any("company:gamma ltd has 0 organization" in b for b in bad), bad)
        self.c.execute("DELETE FROM kg_things WHERE key='circle:test business'")   # an old thing deleted
        self.assertTrue(any("deleted" in b for b in org_moves.check_moves(self.c)))
        with self.assertRaises(sqlite3.IntegrityError):                  # the record itself cannot be rewritten
            self.c.execute("DELETE FROM org_moves")

    def test_PLANTED_a_second_current_type_is_reported(self):
        self.move()
        org = self.x("SELECT id FROM kg_things WHERE key=(SELECT new_key FROM org_moves WHERE old_key='company:beta corp')")[0][0]
        self.c.execute("INSERT INTO kg_facts(thing_id,fact_key,value,who,certainty,source_kind,created_at) VALUES(?,?,?,?,?,?,?)",
                       (org, "org_type", "team", "code", "likely", "code", "2026-11-16T00:00:00Z"))
        self.assertTrue(any("exactly one current org_type" in b for b in org_moves.check_moves(self.c)))


class FilterSpec(Base):
    def spec(self):
        mp = dict(self.x("SELECT new_key, old_key FROM org_moves"))
        return sorted(repr((r[3], r[5], r[6], r[7], r[8], r[9], r[10], mp.get(r[11], r[11])))
                      for r in self.x("SELECT * FROM v_filter_spec"))

    def test_the_gmail_filter_spec_is_the_same_before_and_after_the_move(self):
        sg.record_answer(self.c, "q", "Acme mail gets the Studio label", "t", "2026-11-02", "company", "Acme Studio", "label", "Studio")
        sg.record_answer(self.c, "q", "Acme stays in the inbox", "t", "2026-11-02", "company", "Acme Studio", "inbox", "stay")
        sg.add_link(self.c, sg.thing(self.c, "domain", "acme.test"), "domain_of", sg.thing(self.c, "company", "Acme Studio"), "code", "sure", "code")
        before = self.spec()
        self.assertGreaterEqual(len(before), 2)
        self.assertIn("@acme.test", before[0])      # the company's domain is the sender the filter is written for
        self.move()
        self.assertEqual(self.spec(), before)       # PLANTED regression (found by the checker): with the old view, these rows vanished
        self.assertEqual(self.x("SELECT count(*) FROM kg_things t JOIN v_confirmed_filter_facts f ON f.thing_id=t.id WHERE t.kind='company'")[0][0], 0)


class Placement(Base):
    def test_PLANTED_code_cannot_place_anyone(self):
        self.move()
        org = sg.thing_by_key(self.c, self.x("SELECT new_key FROM org_moves WHERE old_key='company:acme studio'")[0][0])["id"]
        org2 = sg.thing_by_key(self.c, self.x("SELECT new_key FROM org_moves WHERE old_key='company:beta corp'")[0][0])["id"]
        for kind, a, b in (("member_of", self.al, org), ("part_of", org2, org), ("reports_to", self.al, self.jo), ("knows", self.al, self.jo)):
            with self.assertRaises(sg.Refused, msg=kind):
                sg.add_link(self.c, a, kind, b, "code", "likely", "code")
            with self.assertRaises(sqlite3.IntegrityError, msg="database: " + kind):     # the second lock, around the front door
                self.c.execute("INSERT INTO kg_links(from_id,kind,to_id,who,certainty,source_kind,created_at) VALUES(?,?,?,'code','likely','code','2026-11-16T00:00:00Z')", (a, kind, b))
        with self.assertRaises(sg.Refused):
            sg.assert_fact(self.c, self.al, "levels_above_me", "1", "code", "likely", "code")
        with self.assertRaises(sqlite3.IntegrityError):
            self.c.execute("INSERT INTO kg_facts(thing_id,fact_key,value,who,certainty,source_kind,created_at) VALUES(?,?,?,?,?,?,?)",
                           (self.al, "levels_above_me", "1", "code", "likely", "code", "2026-11-16T00:00:00Z"))
        # his word with his answer is accepted, and a plain code link of another kind still is
        sg.add_link(self.c, self.al, "member_of", org, "owner", "sure", "answer", None, self.ans, role="partner")
        sg.assert_fact(self.c, self.al, "levels_above_me", "1", "owner", "sure", "answer", None, self.ans)
        sg.add_link(self.c, self.al, "works_at", org, "code", "likely", "code")

    def test_a_write_to_a_merged_company_lands_on_its_organization(self):
        self.move()
        sg.assert_fact(self.c, sg.thing(self.c, "company", "Acme Studio"), "label", "Studio", "code", "likely", "code")
        org = self.x("SELECT new_key FROM org_moves WHERE old_key='company:acme studio'")[0][0]
        self.assertEqual(self.x("SELECT value FROM kg_current_facts WHERE thing_key=? AND fact_key='label'", (org,)), [("Studio",)])


class Rebuild(Base):
    def test_rebuild_reproduces_organizations_with_the_same_keys_and_a_planted_difference_is_seen(self):
        self.move()
        keys = sorted(r[0] for r in self.x("SELECT key FROM kg_things WHERE kind='organization'"))
        self.c.close()
        res = model_check.check(self.p)
        self.assertEqual(res["differences"], 0, res["sample"])
        dest = os.path.join(self.tmp.name, "rb.db")
        model_check.rebuild(self.p, dest)
        rb = sqlite3.connect(dest)
        self.assertEqual(sorted(r[0] for r in rb.execute("SELECT key FROM kg_things WHERE kind='organization'")), keys)
        self.assertEqual(rb.execute("SELECT name FROM kg_things WHERE key=?", (keys[0],)).fetchone()[0] in ("Acme Studio", "Beta Corp", "Test Family", "Test Business"), True)
        rb.close()
        bad = model_check.check(self.p, mutate=lambda con: con.execute("DELETE FROM kg_facts WHERE fact_key='org_type'"))
        self.assertGreater(bad["differences"], 0)
        self.c = sqlite3.connect(self.p, isolation_level=None)


class Reader(Base):
    def test_one_reader_same_answer_before_and_after_and_a_planted_loss_shows(self):
        sg.add_link(self.c, sg.thing(self.c, "address", "jo@example.test"), "address_of", self.jo, "code", "sure", "code")
        before = who(self.c)
        self.assertEqual(before, [("Test Family", None)])
        self.move()
        self.assertEqual(who(self.c), before)
        pers = store.sender_context("jo@example.test")["organizations"]
        self.assertEqual([(o["name"], o["org_type"]) for o in pers], [("Test Family", "group")])
        # planted: his membership line retired; the same question now gives a different answer, and the comparison says so
        self.c.execute("UPDATE kg_links SET replaced_by=id WHERE kind='member_of' AND who='owner' AND to_id IN (SELECT id FROM kg_things WHERE kind='organization')")
        self.assertNotEqual(who(self.c), before)


if __name__ == "__main__":
    unittest.main()
