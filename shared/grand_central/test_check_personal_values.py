#!/usr/bin/env python3
"""Tests for check_personal_values.py -- synthetic values only."""
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_personal_values as cpv

PLANT = "zorblax-quuxington"


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.setup = os.path.join(self.tmp.name, "setup")
        self.root = os.path.join(self.tmp.name, "engine")
        os.makedirs(self.setup)
        os.makedirs(self.root)
        with open(os.path.join(self.setup, "a.json"), "w", encoding="utf-8") as f:
            json.dump({"_note": "ignoredvalue", "label": PLANT, "short": "ab", "ok": "true"}, f)
        self.write("clean.py", "x = 1  # nothing personal here\n")
        self._home = os.environ.get("HOME")
        os.environ["HOME"] = self.tmp.name   # home user name becomes a synthetic temp name
        self.addCleanup(self._restore)

    def _restore(self):
        os.environ["HOME"] = self._home

    def write(self, name, text, root=None):
        with open(os.path.join(root or self.root, name), "w", encoding="utf-8") as f:
            f.write(text)

    def go(self, setup="default"):
        buf = io.StringIO()
        s = self.setup if setup == "default" else setup
        code = cpv.run(self.root, setup=s, out=buf) if s and os.path.isdir(s) else None
        return code, buf.getvalue()

    def main(self, setup=None):
        return cpv.main(["--root", self.root, "--setup", setup or self.setup])

    def test_clean_tree_passes(self):
        self.assertEqual(self.main(), 0)

    def test_name_in_code_fails_and_is_not_printed(self):
        self.write("bad.py", 'LABEL = "%s"\n' % PLANT)
        code, out = self.go()
        self.assertEqual(code, 1)
        self.assertIn("bad.py:1:setup-name:", out)
        self.assertNotIn(PLANT, out)
        self.assertNotIn("zorblax", out.lower())

    def test_name_in_comment_fails(self):
        self.write("c.py", "x = 1\n# note about %s\n" % PLANT.upper())
        code, out = self.go()
        self.assertEqual(code, 1)
        self.assertIn("c.py:2:", out)

    def test_generic_word_in_setup_is_not_a_term(self):
        with open(os.path.join(self.setup, "b.json"), "w", encoding="utf-8") as f:
            json.dump({"phrases": ["verdict", "deadline"], "display": "verdict", "status": "zzprose"}, f)
        self.write("g.py", "# verdict deadline python3 home zzprose\n")
        self.assertEqual(self.main(), 0)

    def test_underscore_keys_and_short_values_ignored(self):
        self.write("ok.py", "# ignoredvalue ab\n")
        self.assertEqual(self.main(), 0)

    def test_allowed_exception_passes(self):
        self.write("mail.py", 'D = "%s"\n' % PLANT)
        self.assertEqual(self.main(), 1)
        self.write(cpv.ALLOW_NAME, "mail.py:%s   # set by install script\n" % PLANT, root=self.setup)
        self.assertEqual(self.main(), 0)
        self.write(cpv.ALLOW_NAME, root=self.setup, text="mail.py:sha:%s  # by hash\n" % cpv.h8(PLANT))
        self.assertEqual(self.main(), 0)
        self.write("other.py", 'D = "%s"\n' % PLANT)   # allow is per file
        self.assertEqual(self.main(), 1)

    def test_allow_line_without_reason_cannot_evaluate(self):
        self.write(cpv.ALLOW_NAME, root=self.setup, text="mail.py:%s\n" % PLANT)
        self.assertEqual(self.main(), 2)

    def test_missing_setup_cannot_evaluate(self):
        self.assertEqual(self.main(setup=os.path.join(self.tmp.name, "nope")), 2)

    def test_empty_setup_cannot_evaluate(self):
        empty = os.path.join(self.tmp.name, "empty")
        os.makedirs(empty)
        self.assertEqual(self.main(setup=empty), 2)

    def test_home_user_name_is_a_term(self):
        os.environ["HOME"] = os.path.join(self.tmp.name, "pqrstuvw")
        self.write("h.py", "# /" + "Users/pqrstuvw/x\n")
        code, out = self.go()
        self.assertEqual(code, 1)
        self.assertIn("home-user", out)
        self.assertNotIn("pqrstuvw", out)

    # ---- the shipped generic defaults, the harness's own name, and real home paths (H3) ----
    def test_shipped_generic_defaults_are_not_flagged(self):
        with open(os.path.join(self.setup, "d.json"), "w", encoding="utf-8") as f:
            json.dump({"desks": {"planning": {"display": "Planning"}}, "main_diary": {"name": "Planning-Diary"}}, f)
        self.write("g.py", "# the planning desk keeps Planning-Diary\n")
        self.assertEqual(self.main(), 0)

    def test_a_setup_desk_that_is_not_a_shipped_default_still_fails(self):
        with open(os.path.join(self.setup, "d.json"), "w", encoding="utf-8") as f:
            json.dump({"desks": {"desk-x": {"display": "Desk-X"}}, "default_desk": "desk-x"}, f)
        self.write("g.py", 'DESK = "desk-x"\n')
        code, out = self.go()
        self.assertEqual(code, 1)
        self.assertIn("g.py:1:setup-name:", out)

    def test_harness_own_name_is_derived_and_not_flagged(self):
        import gc_settings
        name = gc_settings.harness_name()
        with open(os.path.join(self.setup, "d.json"), "w", encoding="utf-8") as f:
            json.dump({"label": name}, f)
        self.write("g.py", "# running inside %s\n" % name)
        self.assertEqual(self.main(), 0)

    def test_real_home_folder_path_fails_whoever_the_person_is(self):
        self.write("p.py", 'P = "/' + 'Users/someone/projects/lifehack-brain/x"\n')
        code, out = self.go()
        self.assertEqual(code, 1)
        self.assertIn("p.py:1:personal-path:", out)
        self.assertNotIn("someone", out)
        self.write("p.py", 'P = "/' + 'home/another/x"\n')
        self.assertEqual(self.go()[0], 1)

    def test_shared_folder_and_relative_paths_are_not_home_paths(self):
        self.write("p.py", 'P = "~/.local/share/x"  # and a/Users_b is not a home path\n')
        self.assertEqual(self.main(), 0)

    # --precommit: three paths
    def pre(self, setup):
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            code = cpv.main(["--root", self.root, "--precommit"] + (["--setup", setup] if setup else []))
        finally:
            sys.stdout = old
        return code, buf.getvalue()

    def test_precommit_clean_passes(self):
        self.assertEqual(self.pre(self.setup)[0], 0)

    def test_precommit_finding_blocks_without_echo(self):
        self.write("bad.py", "# %s\n" % PLANT)
        code, out = self.pre(self.setup)
        self.assertEqual(code, 1)
        self.assertNotIn("zorblax", out.lower())

    def test_precommit_no_setup_skips_with_exact_note(self):
        for k in ("GC_SETUP_DIR", "LIFEHACK_ROOT"):
            os.environ.pop(k, None)
        self.write("bad.py", "# %s\n" % PLANT)
        code, out = self.pre(None)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "personal-values check skipped: no owner setup on this machine; "
                                      "No Private Desks covers CI")
        code, out = self.pre(os.path.join(self.tmp.name, "nope"))   # named but missing: cannot evaluate, never a skip
        self.assertEqual(code, 2)
        self.assertNotIn("skipped", out)


class ProseKeysAndDb(T):
    """The lock also takes the words of the prose-ish setup keys, and the names that live only in the owner's database."""

    def prose_setup(self):
        d = os.path.join(self.tmp.name, "setup2")
        os.makedirs(d)
        with open(os.path.join(d, "g.json"), "w", encoding="utf-8") as f:
            json.dump({"label": PLANT,
                       "prompt_examples": {"q": "Were the Zorblaxia / Quuxville tapes handled or passed?"},
                       "trip_words": {"city_country": {"vorpalburg": "vorpalland"}, "airlines": ["flibberjet air"]},
                       "needs_words_extra": ["flimflamcall"],
                       "negative_fact_words": {"g1": {"words": "snarfblat|grindle.?wort", "projects": ["desk-a"]}}}, f)
        return d

    def test_prose_key_words_are_search_terms(self):
        d = self.prose_setup()
        for i, word in enumerate(["Quuxville", "vorpalland", "VORPALBURG", "flibberjet air", "flimflamcall",
                                  "snarfblat", "grindlewort"]):
            self.write("p%d.py" % i, "x = '%s'\n" % word)
        self.write("ok.py", "y = 'handled'  # generic words of those values stay free\n")
        code, out = self.go(d)
        self.assertEqual(code, 1)
        for i in range(7):
            self.assertIn("p%d.py:1:setup-topic:" % i, out)
        self.assertNotIn("ok.py", out)
        self.assertNotIn("quuxville", out.lower())

    def make_db(self, people=(), orgs=(), senders=()):
        import sqlite3
        path = os.path.join(self.tmp.name, "rig.db")
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE kg_things(id INTEGER PRIMARY KEY, kind TEXT, key TEXT, name TEXT)")
        con.execute("CREATE TABLE v_thing_senders(thing_kind TEXT, sender TEXT)")
        for i, n in enumerate(people):
            con.execute("INSERT INTO kg_things(kind,key,name) VALUES('person',?,?)", ("person:%d" % i, n))
        for i, n in enumerate(orgs):
            con.execute("INSERT INTO kg_things(kind,key,name) VALUES('organization',?,?)", ("organization:%d" % i, n))
        for sdr in senders:
            con.execute("INSERT INTO v_thing_senders VALUES('person',?)", (sdr,))
        con.commit()
        con.close()
        return path

    def test_surname_only_in_the_database_is_caught(self):
        db = self.make_db(people=["Quillon Zibberwick"], orgs=["Frobnitz Holdings"],
                          senders=["quillon@frobnicorp.example", "someone@freemail.example"])
        for i, w in enumerate(["Zibberwick", "quillon@frobnicorp.example", "frobnicorp.example", "Frobnitz Holdings"]):
            self.write("d%d.py" % i, "x = '%s'\n" % w)
        self.write("fm.py", "x = 'gmail.com'\n")
        buf = io.StringIO()
        code = cpv.run(self.root, setup=self.setup, out=buf, db=db)
        out = buf.getvalue()
        self.assertEqual(code, 1)
        for i in range(4):
            self.assertIn("d%d.py:1:db-" % i, out)
        self.assertNotIn("fm.py", out)                    # free-mail domains are not personal
        self.assertNotIn("zibberwick", out.lower())

    def test_generic_first_name_in_the_database_does_not_trigger(self):
        db = self.make_db(people=["Will Zibberwick"])
        self.write("w.py", "# will the job grant this? Mark my words.\n")
        buf = io.StringIO()
        self.assertEqual(cpv.run(self.root, setup=self.setup, out=buf, db=db), 0)

    def test_no_owner_database_skips_the_layer_and_an_unreadable_one_cannot_evaluate(self):
        self.assertEqual(self.main(), 0)                   # HOME is a temp folder: no owner DB resolves
        bad = os.path.join(self.tmp.name, "bad.db")
        with open(bad, "w", encoding="utf-8") as f:
            f.write("this is not a database")
        self.assertEqual(cpv.main(["--root", self.root, "--setup", self.setup, "--db", bad]), 2)

    def test_org_stored_only_as_a_domain_is_caught_by_its_label(self):
        db = self.make_db(orgs=["zibbertalent.co.uk", "uber.com"], senders=["a@frumbleshop.example"])
        self.write("l1.py", "AGENCY = 'Zibbertalent'\n")
        self.write("l2.py", "SHOP = 'frumbleshop'\n")
        self.write("l3.py", "RIDE = 'uber'\n")            # a public service is not personal
        buf = io.StringIO()
        code = cpv.run(self.root, setup=self.setup, out=buf, db=db)
        out = buf.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("l1.py:1:db-label:", out)
        self.assertIn("l2.py:1:db-label:", out)
        self.assertNotIn("l3.py", out)
        self.assertNotIn("zibbertalent", out.lower())

    def test_org_initials_only_when_not_a_common_word(self):
        db = self.make_db(orgs=["Qzx Vlorp Mgnt", "Cats And Dogs"])
        self.write("i1.py", "x = 'QVM'\n")
        self.write("i2.py", "x = 'cad'\n")                  # a common word: not a term
        buf = io.StringIO()
        code = cpv.run(self.root, setup=self.setup, out=buf, db=db)
        out = buf.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("i1.py:1:db-initials:", out)
        self.assertNotIn("i2.py", out)


if __name__ == "__main__":
    unittest.main()
