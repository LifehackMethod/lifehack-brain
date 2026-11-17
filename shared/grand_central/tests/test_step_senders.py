"""Senders (migration 026): every address tied to its organization by domain; every sender a person, a bot or a question mark;
bots sorted by whether they need him; only the question marks that matter go to the onboarding sheet. Temp databases, synthetic
mail only. Each planted case runs a deliberately BROKEN version first and requires the check to catch it, then the real one."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import json
import os
import re
import sqlite3
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import model_check, senders, store, store_graph as sg  # noqa: E402
from test_step32_events import Base, ME  # noqa: E402


class S(Base):
    def setUp(self):
        super().setUp()
        # a reserved-domain stand-in for a free-mail provider: the engine's own free-mail list gains it for this test only
        p = mock.patch.object(senders, "FREE_MAIL", set(senders.FREE_MAIL) | {"freemail.example"})
        p.start()
        self.addCleanup(p.stop)

    def msg(self, frm, subject="hello", sent=False, to=None, thread=None, **hdr):
        self.n += 1
        self.x("INSERT INTO messages(id,thread_id,internal_date,label_ids,from_addr,to_addrs,cc_addrs,subject,is_sent,list_id,"
               "list_unsubscribe_present,precedence,auto_submitted,dmarc_pass) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
               ("s%d" % self.n, thread or "t%d" % self.n, 1700000000000 + self.n * 1000, hdr.get("labels", "[]"), frm,
                json.dumps(to or [ME]), "[]", subject, 1 if sent else 0, hdr.get("list_id"), hdr.get("unsub", 0),
                hdr.get("precedence"), hdr.get("auto")))

    def two_way(self, addr):
        self.msg(addr, thread="tw-" + addr)
        self.msg(ME, sent=True, to=[addr], thread="tw-" + addr)

    def build(self, **k):
        with store._write() as c:
            return senders.build_senders(c, starters=k.get("starters", []))

    def fact(self, addr, key):
        r = self.x("SELECT f.value FROM kg_facts f JOIN kg_things t ON t.id=f.thing_id WHERE t.key=? AND f.fact_key=? AND f.replaced_by IS NULL",
                   ("address:" + addr, key))
        return r[0][0] if r else None

    def org(self, addr):
        r = self.x("SELECT o.key, o.name FROM kg_things a JOIN kg_links l ON l.from_id=a.id AND l.kind='belongs_to' AND l.replaced_by IS NULL "
                   "JOIN kg_things o ON o.id=l.to_id WHERE a.key=?", ("address:" + addr,))
        return r[0] if r else None

    def rule(self, addr, fact_key, value):
        """his own ruling on a sender (an owner fact under a recorded answer)"""
        with store._write() as c:
            sg.record_answer(c, "What about %s?" % addr, "his words", "owner-session", subject_kind="address", subject_name=addr,
                             fact_key=fact_key, value=value)

    def planted(self, check, plant_ctx):
        """the broken version must be caught (the check raises), then the real one must pass on a fresh database"""
        with plant_ctx:
            with self.assertRaises(AssertionError):
                check()
        self.tearDown(); self.setUp()
        check()


class Senders(S):
    # 1. no-reply -> bot
    def _noreply(self):
        self.msg("no-reply@shop.example", "Your order")
        self.build()
        if self.fact("no-reply@shop.example", "sender_kind") != "bot":
            raise AssertionError("a no-reply address was not marked a bot")

    def test_PLANTED_noreply_is_a_bot(self):
        self.planted(self._noreply, mock.patch.object(senders.se, "looks_automated", lambda a: False))

    # 2. newsletter -> bot, FYI by default, junk only from his ruling
    def _newsletter(self):
        self.msg("letters@news.example", "Weekly digest", list_id="<l.news.example>", unsub=1)
        self.msg("letters@news.example", "Weekly digest 2", list_id="<l.news.example>", unsub=1)
        self.build()
        if self.fact("letters@news.example", "sender_kind") != "bot":
            raise AssertionError("a newsletter was not marked a bot")
        if self.fact("letters@news.example", "bot_need") != "fyi":
            raise AssertionError("a newsletter with no ruling must be FYI, got %r" % self.fact("letters@news.example", "bot_need"))

    def test_PLANTED_newsletter_is_a_bot_and_fyi_not_junk(self):
        self.planted(self._newsletter, mock.patch.object(senders, "AUTO_SHARE", 2.0))            # no bulk test: stays a question mark
        self.tearDown(); self.setUp()
        with mock.patch.object(senders, "classify_need", lambda *a: ("junk", "likely", "code", "assumed")):   # the plant: assume junk
            with self.assertRaises(Exception):                                                      # the front door (a trigger) refuses it
                self._newsletter()

    def test_his_junk_ruling_makes_a_bot_junk(self):
        self.msg("letters@news.example", "Weekly digest", list_id="<l>", unsub=1)
        self.rule("letters@news.example", "destination", "trash")
        self.build()
        self.assertEqual(self.fact("letters@news.example", "bot_need"), "junk")

    def test_his_ruling_on_the_domain_reaches_the_sender(self):
        self.msg("alerts@bank.example", "x", list_id="<l>", unsub=1)
        with store._write() as c:
            sg.record_answer(c, "What about bank.example?", "his words", "owner-session", subject_kind="domain", subject_name="bank.example",
                             fact_key="inbox", value="stay")
        self.build()
        self.assertEqual(self.fact("alerts@bank.example", "bot_need"), "needs_him")       # his stay-in-inbox ruling, not the bulk default

    # 3. bank notice -> bot, needs him or FYI, never junk
    def _bank(self):
        self.msg("alerts@bigbank.example", "Your payment was declined")
        self.msg("alerts@bigbank.example", "Security alert on your account")
        self.build()
        if self.fact("alerts@bigbank.example", "sender_kind") != "bot":
            raise AssertionError("a bank notice was not marked a bot")
        if self.fact("alerts@bigbank.example", "bot_need") not in ("needs_him", "fyi"):
            raise AssertionError("a bank notice must need him or be FYI, got %r" % self.fact("alerts@bigbank.example", "bot_need"))

    def test_PLANTED_bank_notice_never_junk(self):
        self.planted(self._bank, mock.patch.object(senders, "NEEDS_WORDS", re.compile("^$")))      # no category words: left 'unsure'

    # 4. a real two-way human -> person
    def _human(self):
        self.two_way("pat@acme.example")
        self.build()
        if self.fact("pat@acme.example", "sender_kind") != "person":
            raise AssertionError("a real two-way human was not marked a person")
        if not self.x("SELECT 1 FROM kg_things ad JOIN kg_links l ON l.from_id=ad.id AND l.kind='address_of' AND l.replaced_by IS NULL "
                      "WHERE ad.key='address:pat@acme.example'"):
            raise AssertionError("no person thing behind the address")

    def test_PLANTED_two_way_human_is_a_person(self):
        self.planted(self._human, mock.patch.object(senders.se._People, "two_way", lambda self, a: False))

    # 5. ambiguous -> question mark
    def _ambiguous(self):
        self.msg("someone@odd.example", "hi there")
        self.build()
        if self.fact("someone@odd.example", "sender_kind") != "unknown":
            raise AssertionError("an ambiguous sender was not left a question mark")
        if self.fact("someone@odd.example", "bot_need") is not None:
            raise AssertionError("a question mark was given a bot need")

    def test_PLANTED_ambiguous_is_a_question_mark(self):
        self.planted(self._ambiguous, mock.patch.object(senders.se, "looks_automated", lambda a: True))   # everything a bot

    # 6. free mail is no organization
    def _gmail(self):
        self.two_way("pat@freemail.example")
        self.build()
        if self.org("pat@freemail.example") is not None or self.x("SELECT 1 FROM kg_things WHERE kind='organization' AND name LIKE '%freemail%'"):
            raise AssertionError("free mail was turned into an organization")

    def test_PLANTED_gmail_has_no_organization(self):
        self.planted(self._gmail, mock.patch.object(senders, "FREE_MAIL", set()))

    # 7. two addresses at one domain -> one organization, named by the domain, no type
    def _one_org(self):
        self.msg("a@mail.acme.example", "x")
        self.msg("b@acme.example", "y")
        self.build()
        oa, ob = self.org("a@mail.acme.example"), self.org("b@acme.example")
        if not oa or oa != ob:
            raise AssertionError("two addresses at one domain are not one organization: %s %s" % (oa, ob))
        if oa[1] != "acme.example":
            raise AssertionError("the organization is not named by its domain: %s" % (oa,))
        if self.x("SELECT 1 FROM kg_facts f JOIN kg_things t ON t.id=f.thing_id WHERE t.key=? AND f.fact_key='org_type'", (oa[0],)):
            raise AssertionError("code guessed a type for a new organization")

    def test_PLANTED_one_domain_one_organization(self):
        self.planted(self._one_org, mock.patch.object(senders, "registrable", lambda d: d))       # sub-domains split into separate ones

    # 8. only the question marks that MATTER go on the sheet, ranked, at most the limit
    def _sheet(self, fn=None):
        fn = fn or senders.onboarding_questions
        self.msg("quiet@odd1.example", "never answered")                       # a question mark that does not matter
        self.msg(ME, sent=True, to=["mattered@odd2.example"], thread="m1")             # he wrote to them once, they never wrote: matters
        self.msg(ME, sent=True, to=["more@odd3.example"], thread="m2")                  # he wrote twice, starting both threads: ranks higher
        self.msg(ME, sent=True, to=["more@odd3.example"], thread="m2b")
        self.build()
        with store._write() as c:
            got = fn(c, 30)
        names = [q["address"] for q in got]
        if "quiet@odd1.example" in names:
            raise AssertionError("a question mark that does not matter was put on the sheet")
        if names[:2] != ["more@odd3.example", "mattered@odd2.example"]:
            raise AssertionError("the sheet is not ranked: %s" % names)

    def test_PLANTED_only_question_marks_that_matter(self):
        def everything(con, limit):
            return [{"address": r[0]} for r in con.execute(
                "SELECT lower(t.name) FROM kg_things t JOIN kg_facts f ON f.thing_id=t.id AND f.fact_key='sender_kind' AND f.value='unknown' "
                "AND f.replaced_by IS NULL ORDER BY 1")]
        with self.assertRaises(AssertionError):
            self._sheet(everything)
        self.tearDown(); self.setUp()
        self._sheet()

    def test_the_sheet_is_capped_at_the_limit(self):
        for i in range(35):
            a = "p%02d@cap%02d.example" % (i, i)
            self.msg(ME, sent=True, to=[a], thread="c%d" % i)
        self.build()
        with store._write() as c:
            self.assertEqual(len(senders.onboarding_questions(c, 30)), 30)
            self.assertEqual(len(senders.onboarding_questions(c, 5)), 5)
            q = senders.onboarding_questions(c, 1)[0]
        self.assertIn("best guess", q["guess"])
        self.assertIsNone(self.fact(q["address"], "bot_need"))           # the guess lives in the question only, never in the model

    # 9. code records only what it is sure of: the front door's second lock
    def test_PLANTED_code_cannot_store_a_guess_or_junk(self):
        def writes():
            with store._write() as c:
                aid = sg.thing(c, "address", "x@y.example.test")
                for who, cert, key, val, sk, ref in (("code", "likely", "sender_kind", "person", "code", "x"),
                                                     ("ai_guess", "sure", "sender_kind", "bot", "code", "x"),
                                                     ("ai_guess", "likely", "bot_need", "fyi", "code", "x"),
                                                     ("code", "likely", "bot_need", "junk", "code", "assumed")):
                    try:
                        sg.assert_fact(c, aid, key, val, who, cert, sk, ref)
                    except (sqlite3.IntegrityError, sg.Refused, sqlite3.DatabaseError):
                        continue
                    raise AssertionError("code stored %s=%s as %s/%s" % (key, val, who, cert))
        # the plant: the three triggers dropped (a database without migration 026's second lock) accepts the writes, so the check fires
        for t in ("kg_facts_sender_kind_by_code", "kg_facts_bot_need_by_code", "kg_facts_bot_junk_is_his"):
            self.x("DROP TRIGGER %s" % t)
        with self.assertRaises(AssertionError):
            writes()
        self.tearDown(); self.setUp()
        writes()

    # 10. idempotent, and the rebuild reproduces it
    def seed(self):
        with store._write() as c:
            sg.copy_legacy(c)                    # as in real history: the legacy copy and the engine's settings were seeded once
            import common as ec
            ec.seed_settings(c)

    def test_rerun_changes_nothing_and_rebuild_check_is_clean(self):
        self.seed()
        self.two_way("pat@acme.example")
        self.msg("no-reply@shop.example", "Your order")
        self.msg("someone@odd.example", "hi")
        self.msg("letters@news.example", "d", list_id="<l>", unsub=1)
        self.build()
        first = self.counts()
        r = self.build()
        self.assertEqual(self.counts(), first)
        self.assertEqual(r["organizations_made"], 0)
        res = model_check.check(self.p)
        self.assertTrue(res["clean"], res["sample"][:5])
        self.assertEqual(res["rebuild"]["senders"]["bot"], 2)

    # a rebuild that loses a sender fact is caught
    def test_PLANTED_rebuild_that_loses_a_sender_fact_is_caught(self):
        self.seed()
        self.msg("no-reply@shop.example", "Your order")
        self.build()
        lose = lambda reb: reb.execute("DELETE FROM kg_facts WHERE fact_key='sender_kind'")   # noqa: E731
        self.assertFalse(model_check.check(self.p, mutate=lose)["clean"])
        self.assertTrue(model_check.check(self.p)["clean"])


if __name__ == "__main__":
    unittest.main()
