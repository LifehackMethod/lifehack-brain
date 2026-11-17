"""Phase 3 step 3.6: merging two people or two organizations, only on his confirmation. Synthetic data, temp databases.
Each planted case runs a deliberately BROKEN version first and requires the check to catch it (the check fails on the plant),
then the real code and requires it to pass: (1) a merge with no owner answer is refused; (2) a merge that fails half way leaves
nothing changed; (3) the old key still answers (and still is a key on record); (4) a rebuild reproduces the merge; plus the
un-merge from the record, and 'code may only ask'."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import os, sqlite3, sys, tempfile, unittest
from unittest import mock
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import migrate, model_check, org_moves, store, store_graph as sg  # noqa: E402
import test_step31_organizations as t31  # noqa: E402


def dump(c):
    return {t: c.execute("SELECT * FROM %s ORDER BY 1" % t).fetchall() for t in ("kg_things", "kg_facts", "kg_links", "kg_answers", "queue", "thing_keys")}


class Base(t31.Base):
    CODE_ROWS = True      # rows the code wrote by itself (not his words): a rebuild cannot rebuild these in a synthetic database

    def setUp(self):
        super().setUp()
        c = self.c
        # two people who are really one; Jo (the survivor) and Joe (to fold in)
        self.joe = sg.thing(c, "person", "Joe Example", key="person:legacy-9")
        self.ja = sg.thing(c, "address", "jo@example.test")
        self.jb = sg.thing(c, "address", "joe@example.test")
        if self.CODE_ROWS:
            sg.add_link(c, self.ja, "address_of", self.jo, "code", "sure", "code")
            sg.add_link(c, self.jb, "address_of", self.joe, "code", "sure", "code")
            sg.assert_fact(c, self.jo, "relationship", "friend", "code", "likely", "legacy", "x")
        else:
            self.say_fact("address:jo@example.test", "jo@example.test", "link:address_of", "person:legacy-1", "jo@ is Jo", "address")
            self.say_fact("address:joe@example.test", "joe@example.test", "link:address_of", "person:legacy-9", "joe@ is Joe", "address")
            self.say_fact("person:legacy-1", "Jo Example", "relationship", "friend", "Jo is a friend")
        self.say_fact("person:legacy-9", "Joe Example", "relationship", "colleague", "he is a colleague")
        self.say("person:legacy-9", "Joe Example", "circle:test family", "Joe is family")
        self.say("person:legacy-1", "Jo Example", "circle:test family", "Jo is family")   # both in the same circle: a duplicate line
        import senders           # as production: pull.py runs the senders step after intake and the events step
        senders.build_senders(self.c)

    def say_fact(self, pkey, pname, fact, value, words, kind="person"):
        aid = self.c.execute("INSERT INTO kg_answers(question,words,asked_by,said_on,subject_key,subject_kind,subject_name,fact_key,value,recorded_at,words_kind) "
                             "VALUES('q',?,'t','2026-11-02',?,?,?,?,?,'2026-11-02T00:00:00Z','verbatim')", (words, pkey, kind, pname, fact, value)).lastrowid
        row = dict(zip(sg._ACOLS, self.c.execute("SELECT %s FROM kg_answers WHERE id=?" % ",".join(sg._ACOLS), (aid,)).fetchone()))
        sg._apply_answer(self.c, row)
        return aid

    def merge(self, lo="person:legacy-9", sv="person:legacy-1", words="yes, that is the same person"):
        return sg.merge_things(self.c, lo, sv, words, "t", "2026-11-10")

    def picture(self):
        return sg.model_picture(self.c)

    def check_clean(self):
        self.c.close()
        res = model_check.check(self.p)
        self.c = sqlite3.connect(self.p, isolation_level=None)
        return res


class OwnerAnswer(Base):
    def refused(self, fn):
        before = dump(self.c)
        try:
            fn()
        except sg.Refused:
            return dump(self.c) == before
        except Exception:
            return False
        return False

    def test_a_merge_with_no_owner_answer_is_refused_and_a_planted_merge_that_skips_the_check_is_caught(self):
        def broken(words=None):   # the plant: merges whatever it is given, no words needed
            row = {"id": 9999, "subject_key": "person:legacy-9", "subject_name": "Joe", "value": "person:legacy-1"}
            self.c.execute("INSERT INTO kg_answers(id,question,words,asked_by,said_on,subject_key,subject_kind,subject_name,fact_key,value,recorded_at) "
                           "VALUES(9999,'q','','t','2026-11-10','person:legacy-9','person','Joe','merge_into','person:legacy-1','2026-11-10T00:00:00Z')")
            sg._do_merge(self.c, row)
        self.c.execute("SAVEPOINT plant")
        self.assertFalse(self.refused(broken), "the plant (no owner answer) must be caught")
        self.c.execute("ROLLBACK TO plant")
        self.c.execute("RELEASE plant")
        for words in (None, "", "   "):
            self.assertTrue(self.refused(lambda w=words: sg.merge_things(self.c, "person:legacy-9", "person:legacy-1", w, "t")), words)
        self.assertTrue(self.refused(lambda: sg.merge_things(self.c, "person:legacy-9", "person:legacy-1", "yes", "")))
        self.assertTrue(self.refused(lambda: sg.merge_things(self.c, "person:legacy-9", "person:legacy-9", "yes", "t")))
        self.assertTrue(self.refused(lambda: sg.merge_things(self.c, "person:me", "person:legacy-1", "yes", "t")))
        self.assertTrue(self.refused(lambda: sg.merge_things(self.c, "person:legacy-9", "address:jo@example.test", "yes", "t")))
        self.assertTrue(self.refused(lambda: sg.merge_things(self.c, "person:nobody", "person:legacy-1", "yes", "t")))
        # the one door for plain answers will not take a merge, and the front door's gc path needs words too
        with self.assertRaises(sg.Refused):
            sg.record_answer(self.c, "q", "yes", "t", "2026-11-10", "person", "Joe Example", "merge_into", "person:legacy-1")
        with self.assertRaises(sg.Refused):
            store.set_path(self.p)
            store.merge_things("person:legacy-9", "person:legacy-1", "", "t")
        self.assertEqual(self.x("SELECT count(*) FROM kg_things WHERE merged_into IS NOT NULL")[0][0], 0)
        self.merge()
        self.assertEqual(self.x("SELECT count(*) FROM kg_things WHERE key='person:legacy-9' AND merged_into IS NOT NULL")[0][0], 1)

    def test_code_may_only_ask_and_a_no_or_silence_merges_nothing(self):
        before = self.picture()
        self.assertIsNone(sg.propose_merge(self.c, "person:legacy-1", "person:legacy-9", "similar names", matters=False))   # tilt to drop
        self.assertEqual(self.x("SELECT count(*) FROM queue WHERE kind='possible_duplicate'")[0][0], 0)
        qid = sg.propose_merge(self.c, "person:legacy-1", "person:legacy-9", "same first name, one shared circle", matters=True)
        self.assertIsNone(sg.propose_merge(self.c, "person:legacy-9", "person:legacy-1", "again", matters=True))   # once per pair
        self.assertEqual(self.picture(), before)       # asking changes nothing
        store.set_path(self.p)
        self.c.close()
        store.answer_proposal(qid, "no")
        self.c = sqlite3.connect(self.p, isolation_level=None)
        self.assertEqual(self.picture(), before)
        qid2 = sg.propose_merge(self.c, "person:legacy-1", "person:legacy-2", "x", matters=True)
        self.c.close()
        r = store.answer_proposal(qid2, "yes, same person")   # the answer path carries it out
        self.c = sqlite3.connect(self.p, isolation_level=None)
        self.assertEqual(self.x("SELECT merged_into IS NOT NULL FROM kg_things WHERE key='person:legacy-2'")[0][0], 1)
        self.assertEqual(self.x("SELECT status FROM queue WHERE id=?", (qid2,))[0][0], "answered")
        self.assertEqual(self.x("SELECT fact_key, queue_id FROM kg_answers WHERE id=?", (r["answer_id"],))[0], ("merge_into", qid2))


class Atomic(Base):
    def same_after_failure(self, fn):
        before = dump(self.c)
        calls = {"n": 0}
        real = sg.add_link

        def flaky(*a, **k):
            calls["n"] += 1
            if calls["n"] == 2:
                raise sqlite3.OperationalError("planted failure half way")
            return real(*a, **k)
        with mock.patch.object(sg, "add_link", flaky):
            try:
                fn()
            except sqlite3.OperationalError:
                pass
        return dump(self.c) == before and calls["n"] >= 2

    def test_a_merge_that_fails_half_way_leaves_nothing_changed_and_a_planted_non_atomic_merge_is_caught(self):
        def broken():   # the plant: the same steps with no savepoint around them
            aid = self.c.execute("INSERT INTO kg_answers(question,words,asked_by,said_on,subject_key,subject_kind,subject_name,fact_key,value,recorded_at) "
                                 "VALUES('q','yes','t','2026-11-10','person:legacy-9','person','Joe','merge_into','person:legacy-1','2026-11-10T00:00:00Z')").lastrowid
            sg._do_merge(self.c, {"id": aid, "subject_key": "person:legacy-9", "subject_name": "Joe", "value": "person:legacy-1"})
        self.c.execute("SAVEPOINT plant")
        self.assertFalse(self.same_after_failure(broken), "the plant must leave a half-done merge, and be caught")
        self.c.execute("ROLLBACK TO plant")
        self.c.execute("RELEASE plant")
        self.assertTrue(self.same_after_failure(self.merge), "the real merge must leave nothing changed")
        self.merge()
        self.assertEqual(self.x("SELECT merged_into IS NOT NULL FROM kg_things WHERE key='person:legacy-9'")[0][0], 1)

    def test_a_merge_the_database_refuses_midway_is_undone_whole(self):
        # a real refusal from the database's own rules: Joe reports to Jo's boss; Jo's boss reports to Joe -> the merge would make a loop
        boss = sg.thing(self.c, "person", "Boss Example", key="person:legacy-8")
        self.say_fact("person:legacy-9", "Joe Example", "link:reports_to", "person:legacy-8", "Joe reports to Boss")
        self.say_fact("person:legacy-8", "Boss Example", "link:reports_to", "person:legacy-1", "Boss reports to Jo")
        before = dump(self.c)
        with self.assertRaises(Exception):
            self.merge()
        self.assertEqual(dump(self.c), before)


class OldKeys(Base):
    def test_the_old_key_still_answers_and_still_is_on_record_and_a_planted_non_following_read_is_caught(self):
        self.merge()
        keys = {r[0] for r in self.x("SELECT key FROM thing_keys")}
        self.assertTrue({"person:legacy-9", "person:legacy-1"} <= keys)
        want = [(f["fact_key"], f["value"]) for f in sg.current_facts(self.c, "person:legacy-1")]
        self.assertIn(("relationship", "colleague"), want)           # his later word (Joe was a colleague) is the survivor's now
        got = lambda: [(f["fact_key"], f["value"]) for f in sg.current_facts(self.c, "person:legacy-9")]   # noqa: E731
        self.assertEqual(got(), want)
        self.assertEqual(sg.resolve_key(self.c, "person:legacy-9"), "person:legacy-1")
        self.assertEqual(sorted(l["from_key"] for l in sg.current_links(self.c, "person:legacy-9") if l["kind"] == "address_of"),
                         ["address:joe@example.test", "address:jo@example.test"][::-1] if False else sorted(["address:jo@example.test", "address:joe@example.test"]))
        with mock.patch.object(sg, "resolve_key", lambda con, k: k):   # the plant: a read that does not follow merged_into
            self.assertNotEqual(got(), want, "the plant must be caught")
        # a later word about the OLD key lands on the survivor; a code write about the old key too
        self.say_fact("person:legacy-9", "Joe Example", "relationship", "vendor", "Joe is a vendor now")
        self.assertIn(("relationship", "vendor"), [(f["fact_key"], f["value"]) for f in sg.current_facts(self.c, "person:legacy-1")])
        self.assertEqual(self.x("SELECT count(*) FROM kg_facts f JOIN kg_things t ON t.id=f.thing_id WHERE t.key='person:legacy-9' AND f.replaced_by IS NULL")[0][0], 0)
        self.assertEqual(sg.thing(self.c, "person", "Joe Example", key="person:legacy-9"), self.jo)

    def test_history_is_kept_and_his_word_beats_a_guess_on_one_answer_keys(self):
        n0 = self.x("SELECT count(*) FROM kg_facts")[0][0]
        self.merge()
        self.assertGreaterEqual(self.x("SELECT count(*) FROM kg_facts")[0][0], n0)          # nothing deleted
        # Jo's own 'friend' was a code guess; Joe's 'colleague' was his word: his word is current, the guess is kept, superseded
        cur = self.x("SELECT value, who FROM kg_facts WHERE thing_id=? AND fact_key='relationship' AND replaced_by IS NULL", (self.jo,))
        self.assertEqual(cur, [("colleague", "owner")])
        self.assertEqual(self.x("SELECT count(*) FROM kg_facts WHERE thing_id=? AND value='friend'", (self.jo,))[0][0], 1)
        # the circle line both had: one current line, not two
        self.assertEqual(self.x("SELECT count(*) FROM kg_links l WHERE l.from_id=? AND l.kind='member_of' AND l.replaced_by IS NULL", (self.jo,))[0][0], 1)


class Rebuild(Base):
    CODE_ROWS = False

    def test_the_rebuild_reproduces_a_merge_and_a_planted_loss_of_it_is_seen(self):
        self.merge()
        res = self.check_clean()
        self.assertEqual(res["differences"], 0, res["sample"])
        self.c.close()
        with mock.patch.object(sg, "_do_merge", lambda con, a, detail=False: a["id"]):   # the plant: a rebuild that forgets merges
            bad = model_check.check(self.p)
        self.c = sqlite3.connect(self.p, isolation_level=None)
        self.assertGreater(bad["differences"], 0, "the plant must be caught")
        self.assertTrue(any("person:legacy-9" in str(r) for _, _, r in bad["sample"]))

    def test_merging_two_organizations_survives_the_rebuild_and_the_unmerge_returns_the_picture(self):
        self.move()
        keys = [r[0] for r in self.x("SELECT key FROM kg_things WHERE kind='organization' AND name IN ('Acme Studio','Beta Corp') ORDER BY name")]
        self.say_fact(keys[0], "Acme Studio", "org_type", "team", "Acme runs a team", "organization")
        before = self.picture()
        r = sg.merge_things(self.c, keys[1], keys[0], "Beta is Acme", "t", "2026-11-10")
        self.assertEqual(sg.resolve_key(self.c, keys[1]), keys[0])
        self.assertEqual(self.check_clean()["differences"], 0)
        sg.unmerge_things(self.c, keys[1], "no, they are two", "t", "2026-11-11")
        self.assertEqual(self.picture(), before)
        res = self.check_clean()
        self.assertEqual(res["differences"], 0, res["sample"])

    def test_unmerge_puts_everything_back_from_the_record_and_a_rebuild_replays_both(self):
        before = self.picture()
        self.merge()
        self.assertNotEqual(self.picture(), before)
        with self.assertRaises(sg.Refused):
            sg.unmerge_things(self.c, "person:legacy-9", "", "t")             # his words, again
        with self.assertRaises(sg.Refused):
            sg.unmerge_things(self.c, "person:legacy-3", "no", "t")           # never merged
        sg.unmerge_things(self.c, "person:legacy-9", "no, two people after all", "t", "2026-11-11")
        self.assertEqual(self.picture(), before)
        self.assertEqual(self.x("SELECT count(*) FROM kg_answers WHERE fact_key IN ('merge_into','unmerge')")[0][0], 2)
        res = self.check_clean()
        self.assertEqual(res["differences"], 0, res["sample"])
        self.merge()                                                          # and he can change his mind again
        self.assertEqual(self.check_clean()["differences"], 0)

    def test_a_merged_into_a_merged_thing_resolves_to_the_end_and_unmerge_goes_last_in_first_out(self):
        self.merge("person:legacy-9", "person:legacy-1")
        self.merge("person:legacy-1", "person:legacy-2", words="and Jo is Al")
        self.assertEqual(sg.resolve_key(self.c, "person:legacy-9"), "person:legacy-2")
        with self.assertRaises(sg.Refused):
            sg.unmerge_things(self.c, "person:legacy-9", "undo", "t")          # its survivor was merged since
        sg.unmerge_things(self.c, "person:legacy-1", "undo the second", "t")
        sg.unmerge_things(self.c, "person:legacy-9", "undo the first", "t")
        self.assertEqual(self.check_clean()["differences"], 0)


if __name__ == "__main__":
    unittest.main()
