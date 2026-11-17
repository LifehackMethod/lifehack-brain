"""Grand Central V2 step 3: the front room's compare (delta.py) and scorecard (scorecard.py).
SYNTHETIC cases only (made-up people, *.test addresses). Temp DBs only, never the live rig.db. Each planted case was
written and shown failing before the code was written.  Run: python3 tests/test_step3_front_room.py"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import datetime as dt, json, os, shutil, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import step3_fixture  # noqa: E402  (builds the temp database; sqlite3 is not allowed under engine/)
import delta, scorecard as sc  # noqa: E402

ME = "me@home.test"
D = 86400000
H = 3600000
NOW = int(dt.datetime(2026, 11, 15, 9, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.tmp.name, "rig.db")
        self.con = step3_fixture.new_db(self.p)
        self.n = 0
        self.cfg_dir = os.path.join(self.tmp.name, "setup")
        src = os.path.join(HERE, "fixtures", "setup")
        shutil.copytree(src, self.cfg_dir) if os.path.isdir(src) else os.makedirs(self.cfg_dir)

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def msg(self, frm, ago_days, subject="hello", thread=None, labels=("INBOX",), to=(ME,), cc=(), sent=0, list_id=None,
            auth=1, ago_hours=None, null_thread=False):
        self.n += 1
        mid = "m%d" % self.n
        d_, k_, s_ = auth if isinstance(auth, tuple) else (auth, auth, auth)   # dmarc, dkim, spf
        ms = NOW - (int(ago_hours * H) if ago_hours is not None else int(ago_days * D))
        self.con.execute(
            "INSERT INTO messages(id,thread_id,internal_date,label_ids,from_addr,from_name,to_addrs,cc_addrs,subject,is_sent,"
            "list_id,list_unsubscribe_present,dmarc_pass,dkim_pass,spf_pass) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (mid, None if null_thread else (thread or "t" + mid), ms, json.dumps(list(labels)), frm, "", json.dumps(list(to)), json.dumps(list(cc)), subject,
             sent, list_id, 1 if list_id else 0, d_, k_, s_))
        self.con.commit()
        return mid

    def label(self, lid, name):
        self.con.execute("INSERT INTO labels(id,name,type) VALUES(?,?,'user')", (lid, name))
        self.con.commit()

    def event(self, eid, in_days, summary, attendees):
        start = dt.datetime.fromtimestamp((NOW + int(in_days * D)) / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.con.execute("INSERT INTO calendar_events(id,start,end,all_day,status,organizer_email,attendee_emails,summary) "
                         "VALUES(?,?,?,0,'confirmed','',?,?)", (eid, start, start, json.dumps(list(attendees)), summary))
        self.con.commit()

    def exchange(self, who, ago_days, rounds=1, reply_hours=2, thread=None, subject="chat"):
        """they write, he replies reply_hours later, `rounds` times, in one thread; ago_days = when it started"""
        t = thread or "x%d" % (self.n + 1)
        for i in range(rounds):
            base = ago_days - i * 0.5
            self.msg(who, base, subject, thread=t)
            self.msg(ME, base - reply_hours / 24.0, subject, thread=t, sent=1, labels=("SENT",), to=(who,))
        return t

    def cfg(self):
        return sc.Config.load(self.cfg_dir)

    def mb(self):
        return sc.Mailbox.load(self.con)

    def write_leans(self, obj):
        """merge into leans.json (it also carries the proposed points), so defaults stay loaded"""
        path = os.path.join(self.cfg_dir, "leans.json")
        cur = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
        cur.update(obj)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cur, f)


class TestDelta(Base):
    def test_sender_with_no_home_is_reported_new(self):
        for i in range(3):
            self.exchange("regular@pal.test", 120 - i * 10)          # a known person, in the baseline
        self.msg("regular@pal.test", 2, "again")                      # known sender writes in the window
        self.msg("stranger@fresh.test", 1, "hello out of nowhere")     # no home anywhere
        out = delta.run(self.con, NOW - 7 * D, NOW)
        new_who = {x["ref"] for x in out["new"]}
        self.assertIn("stranger@fresh.test", new_who)
        self.assertNotIn("regular@pal.test", new_who)
        self.assertTrue(any("stranger@fresh.test" in q for q in out["questions"]))

    def test_quiet_project_with_a_burst_is_reported_changed(self):
        self.label("L_q", "Quiet-Project"); self.label("L_s", "Steady-Project")
        for k in range(6):                                            # baseline: about one a month
            self.msg("a@pal.test", 25 + 30 * k, "q", labels=("INBOX", "L_q"))
        for k in range(36):                                           # steady project: about one every 5 days, still so
            self.msg("b@pal.test", 2 + 5 * k, "s", labels=("INBOX", "L_s"))
        for k in range(9):                                            # the burst, last 3 days
            self.msg("a@pal.test", 0.2 + k * 0.3, "burst", labels=("INBOX", "L_q"))
        out = delta.run(self.con, NOW - 7 * D, NOW)
        changed = {(x["kind"], x["ref"]) for x in out["changed"]}
        self.assertIn(("burst", "Quiet-Project"), changed)
        self.assertNotIn(("burst", "Steady-Project"), changed)

    def test_thread_heating_up_is_reported_changed(self):
        t = "hot"
        for k in range(6):
            self.msg("p@pal.test" if k % 2 == 0 else "q@pal.test", ago_days=0, ago_hours=40 - k * 6, thread=t, subject="heating")
        self.msg("r@pal.test", 3, "calm", thread="calm")
        out = delta.run(self.con, NOW - 7 * D, NOW)
        self.assertIn(("heating", "hot"), {(x["kind"], x["ref"]) for x in out["changed"]})
        self.assertNotIn(("heating", "calm"), {(x["kind"], x["ref"]) for x in out["changed"]})

    def test_expected_reply_that_never_came_is_reported_missing(self):
        for i in range(4):                                            # this person always answers within a day
            self.exchange("prompt@pal.test", 200 - i * 20, rounds=3, reply_hours=2)
        # he wrote, they usually answer within a day; 12 days of silence now
        self.msg(ME, 12, "any news?", thread="ask1", sent=1, labels=("SENT",), to=("prompt@pal.test",))
        # control: wrote yesterday, nothing yet is normal
        self.msg(ME, 1, "ping", thread="ask2", sent=1, labels=("SENT",), to=("prompt@pal.test",))
        # control: a reply did come
        self.msg(ME, 9, "question", thread="ask3", sent=1, labels=("SENT",), to=("prompt@pal.test",))
        self.msg("prompt@pal.test", 8.5, "answer", thread="ask3")
        out = delta.run(self.con, NOW - 7 * D, NOW)
        missing = {x["ref"] for x in out["missing"]}
        self.assertIn("ask1", missing)
        self.assertNotIn("ask2", missing)
        self.assertNotIn("ask3", missing)
        self.assertTrue(any("prompt@pal.test" in q for q in out["questions"]))


class TestScorecard(Base):
    def setUp(self):
        super().setUp()
        for who in ("lean@pal.test", "plain@pal.test"):               # identical histories
            for i in range(5):
                self.exchange(who, 300 - i * 30)

    def test_same_email_scores_higher_from_a_sender_with_a_lean_and_reasons_say_so(self):
        a = self.msg("lean@pal.test", 0.1, "quick one", labels=("INBOX", "CATEGORY_PERSONAL"))
        b = self.msg("plain@pal.test", 0.1, "quick one", labels=("INBOX", "CATEGORY_PERSONAL"))
        without = sc.attention_score(self.mb(), a, self.cfg(), NOW)
        self.write_leans({"senders": {"lean@pal.test": {"kind": "floor", "value": 3.9, "reason": "he said so"}}})
        cfg = self.cfg()
        with_lean = sc.attention_score(self.mb(), a, cfg, NOW)
        plain = sc.attention_score(self.mb(), b, cfg, NOW)
        self.assertGreater(with_lean["score"], without["score"])
        self.assertGreater(with_lean["score"], plain["score"])
        self.assertTrue(any("lean" in r.lower() for r in with_lean["reasons"]), with_lean["reasons"])
        self.assertFalse(any("lean" in r.lower() for r in plain["reasons"]), plain["reasons"])

    def test_no_leans_no_answers_a_direct_dated_ask_outranks_a_bulk_mailer(self):
        cfg = self.cfg()
        self.assertEqual(cfg.leans.get("senders", {}), {})
        ask = sc.importance_urgency({"deadline_days": 2, "direct_ask": True, "reply_expected": True, "money": None},
                                    cfg, standing_value=0.0, automated=False)
        bulk = sc.importance_urgency({"deadline_days": 2, "direct_ask": False, "reply_expected": False, "money": None},
                                     cfg, standing_value=0.0, automated=True)
        self.assertGreater(ask["rank"], bulk["rank"])
        # and from the outside only
        p = self.msg("person@fresh.test", 0.1, "can you do thursday?", labels=("INBOX", "CATEGORY_PERSONAL"))
        n = self.msg("deals@shop.test", 0.1, "Sale ends in 2 days", labels=("INBOX", "CATEGORY_PROMOTIONS"), list_id="<d.shop.test>")
        mb = self.mb()
        self.assertGreater(sc.attention_score(mb, p, cfg, NOW)["score"], sc.attention_score(mb, n, cfg, NOW)["score"])

    def test_importance_caps_urgency_for_path_a(self):
        cfg = self.cfg()
        r = sc.importance_urgency({"deadline_days": 0, "direct_ask": False, "reply_expected": False, "money": False},
                                  cfg, standing_value=0.0, automated=True)
        order = ["low", "medium", "high"]
        self.assertLessEqual(order.index(r["urgency"]), order.index(r["importance"]))
        self.assertTrue(any("cap" in x.lower() for x in r["reasons"]), r["reasons"])

    def test_calendar_match_outside_read_labels_is_on_short_list_newsletter_is_not(self):
        self.event("e1", 3, "Wardrobe fitting", ["evts@fresh.test", ME])
        c = self.msg("evts@fresh.test", 0.2, "see you then", labels=("INBOX",))
        n = self.msg("weekly@news.test", 0.2, "This week in widgets", labels=("INBOX", "CATEGORY_PROMOTIONS"), list_id="<w.news.test>")
        sl = sc.short_list(self.mb(), self.cfg(), NOW)
        ids = [x["msg_id"] for x in sl]
        self.assertIn(c, ids)
        self.assertNotIn(n, ids)

    def test_mail_in_a_read_label_gets_no_attention_score_and_goes_to_the_mailroom(self):
        self.label("Label_R", "Example-Reads")
        r = self.msg("person@fresh.test", 0.2, "tryout tomorrow", labels=("INBOX", "Label_R", "CATEGORY_PERSONAL"))
        mb, cfg = self.mb(), self.cfg()
        self.assertEqual(sc.route(mb, r, cfg), "A")
        out = sc.attention_score(mb, r, cfg, NOW)
        self.assertIsNone(out["score"])
        self.assertEqual(out["route"], "A")
        self.assertNotIn(r, [x["msg_id"] for x in sc.short_list(mb, cfg, NOW)])


class TestStandingGuards(Base):
    def test_reply_all_to_a_crowd_does_not_credit_everyone(self):
        crowd = ["c%d@crowd.test" % i for i in range(30)]
        for k in range(10):
            t = "crowd%d" % k
            for c in crowd[:3]:
                self.msg(c, 100 - k, "cast list", thread=t)
            self.msg(ME, 99 - k, "reply all", thread=t, sent=1, labels=("SENT",), to=tuple(crowd))
        for k in range(10):
            self.exchange("solo@pal.test", 100 - k)
        mb, cfg = self.mb(), self.cfg()
        self.assertLess(sc.standing(mb, "c0@crowd.test", cfg, NOW)["raw"], sc.standing(mb, "solo@pal.test", cfg, NOW)["raw"])

    def test_standing_applies_only_if_sender_authentication_passes(self):
        for i in range(8):
            self.exchange("real@pal.test", 300 - i * 30)
        mb, cfg = self.mb(), self.cfg()
        self.assertGreater(sc.standing(mb, "real@pal.test", cfg, NOW, auth_ok=True)["standing"], 1.0)
        bad = sc.standing(mb, "real@pal.test", cfg, NOW, auth_ok=False)
        self.assertEqual(bad["standing"], 0.0)
        self.assertTrue(any("confirm" in r.lower() for r in bad["reasons"]))

    def test_two_addresses_merge_only_on_confirmation(self):
        for i in range(6):
            self.exchange("one@pal.test", 300 - i * 30)
        for i in range(6):
            self.exchange("two@pal.test", 150 - i * 20)
        solo = sc.standing(self.mb(), "one@pal.test", self.cfg(), NOW)["raw"]
        self.write_leans({"merges": [{"addresses": ["one@pal.test", "two@pal.test"], "confirmed": False}]})
        self.assertAlmostEqual(sc.standing(self.mb(), "one@pal.test", self.cfg(), NOW)["raw"], solo)
        self.write_leans({"merges": [{"addresses": ["one@pal.test", "two@pal.test"], "confirmed": True}]})
        self.assertGreater(sc.standing(self.mb(), "one@pal.test", self.cfg(), NOW)["raw"], solo)

    def test_someone_gone_quiet_fades_but_never_to_zero(self):
        for i in range(6):
            self.exchange("gone@pal.test", 2500 - i * 20)
        r = sc.standing(self.mb(), "gone@pal.test", self.cfg(), NOW)
        self.assertGreater(r["standing"], 0.5)
        self.assertTrue(any("quiet" in x.lower() or "fad" in x.lower() or "keep" in x.lower() for x in r["reasons"]), r["reasons"])

    def test_fade_floor_is_about_half_his_ruling(self):
        # The owner's accepted fix (2026-11-15): fade to about half, never zero. Not the old 0.70 draft value.
        for i in range(6):
            self.exchange("recent@pal.test", 10 + i * 20)
            self.exchange("decade@pal.test", 3650 + i * 20)
        fresh = sc.standing(self.mb(), "recent@pal.test", self.cfg(), NOW)["raw"]
        old = sc.standing(self.mb(), "decade@pal.test", self.cfg(), NOW)["raw"]
        self.assertGreater(fresh, 0)
        ratio = old / fresh
        self.assertGreaterEqual(ratio, 0.48, ratio)
        self.assertLessEqual(ratio, 0.56, ratio)

    def test_new_sender_with_a_job_keyword_is_always_flagged(self):
        kw = json.load(open(os.path.join(self.cfg_dir, "keywords.json"), encoding="utf-8"))
        phrase = kw["lists"]["job"]["phrases"][0]
        j = self.msg("brandnew@fresh.test", 0.1, "Re: " + phrase + " thursday", labels=("INBOX",))
        out = sc.attention_score(self.mb(), j, self.cfg(), NOW)
        self.assertTrue(out["shortlist"])
        self.assertTrue(any("new sender" in r.lower() for r in out["reasons"]), out["reasons"])


class TestAttackFixes(Base):
    """Fixes after the independent attack (step-3-attack.md): each case was added and shown failing first."""
    def trusted(self, who="boss@corp.test", n=12):
        for i in range(n):
            self.exchange(who, 200 - i * 10, rounds=2)

    def write_setup(self, name, obj):
        with open(os.path.join(self.cfg_dir, name), "w", encoding="utf-8") as f:
            f.write(obj if isinstance(obj, str) else json.dumps(obj))

    def points_edit(self, section, **kw):
        cur = json.load(open(os.path.join(self.cfg_dir, "leans.json"), encoding="utf-8"))
        cur["proposed_points"][section].update(kw)
        self.write_setup("leans.json", cur)

    def test_A1e_dmarc_fail_with_dkim_pass_gets_no_trusted_standing(self):
        self.trusted()
        bad = self.msg("boss@corp.test", 0.1, "need you", auth=(0, 1, 1))     # dmarc fail, dkim pass
        good = self.msg("boss@corp.test", 0.1, "need you", auth=(1, 0, 0))    # dmarc pass only
        mb, cfg = self.mb(), self.cfg()
        rb, rg = sc.attention_score(mb, bad, cfg, NOW), sc.attention_score(mb, good, cfg, NOW)
        self.assertTrue(any("confirm" in r.lower() for r in rb["reasons"]), rb["reasons"])
        self.assertGreater(rg["score"], rb["score"])

    def test_A2a_silent_recipient_of_a_crowd_send_gets_no_standing(self):
        crowd = ["c%d@crowd.test" % i for i in range(40)]
        for k in range(4):
            self.msg(ME, 50 - k, "blast", thread="b%d" % k, sent=1, labels=("SENT",), to=tuple(crowd))
        self.assertEqual(sc.standing(self.mb(), "c0@crowd.test", self.cfg(), NOW)["raw"], 0.0)

    def test_A2a_crowd_answers_are_discounted_in_breadth_and_initiation_too(self):
        crowd = ["c%d@crowd.test" % i for i in range(40)]
        for k in range(10):
            t = "s%d" % k
            self.msg(ME, 100 - k, "survey", thread=t, sent=1, labels=("SENT",), to=tuple(crowd))
            self.msg("c0@crowd.test", 99.5 - k, "answer", thread=t)
        for k in range(10):
            self.exchange("solo@pal.test", 100 - k)
        mb, cfg = self.mb(), self.cfg()
        self.assertLess(sc.standing(mb, "c0@crowd.test", cfg, NOW)["raw"], 0.5 * sc.standing(mb, "solo@pal.test", cfg, NOW)["raw"])

    def test_A8b_job_keyword_flags_any_mail_before_his_first_reply(self):
        kw = json.load(open(os.path.join(self.cfg_dir, "keywords.json"), encoding="utf-8"))["lists"]["job"]["phrases"][0]
        self.msg("slow@fresh.test", 3, "just saying hi")
        second = self.msg("slow@fresh.test", 0.1, "about the " + kw)
        out = sc.attention_score(self.mb(), second, self.cfg(), NOW)
        self.assertTrue(out["shortlist"], out["reasons"])
        # once he has replied, it is no longer a never-met sender
        self.msg("met@fresh.test", 5, "hi"); self.msg(ME, 4, "hello", sent=1, labels=("SENT",), to=("met@fresh.test",))
        later = self.msg("met@fresh.test", 0.1, "about the " + kw)
        out2 = sc.attention_score(self.mb(), later, self.cfg(), NOW)
        self.assertFalse(any("new sender" in r.lower() for r in out2["reasons"]), out2["reasons"])

    def test_A10d_every_score_carries_a_reason(self):
        a = self.msg("nobody@fresh.test", 0.1, "hello", labels=("INBOX",))
        out = sc.attention_score(self.mb(), a, self.cfg(), NOW)
        self.assertTrue(out["reasons"])
        self.assertTrue(sc.importance_urgency({}, self.cfg())["reasons"])

    def test_A5_missing_or_malformed_setup_files_fail_loudly_naming_the_file(self):
        for name in ("leans.json", "labels.json", "keywords.json"):
            path = os.path.join(self.cfg_dir, name)
            keep = open(path, encoding="utf-8").read()
            os.remove(path)
            with self.assertRaises(sc.SetupError) as cm:
                sc.Config.load(self.cfg_dir)
            self.assertIn(name, str(cm.exception))
            open(path, "w", encoding="utf-8").write("{ not json")
            with self.assertRaises(sc.SetupError) as cm:
                sc.Config.load(self.cfg_dir)
            self.assertIn(name, str(cm.exception))
            open(path, "w", encoding="utf-8").write(keep)
        with self.assertRaises(sc.SetupError):
            sc.Config.load(os.path.join(self.tmp.name, "nope"))

    def test_A5_missing_senders_and_merges_work_as_empty(self):
        cur = json.load(open(os.path.join(self.cfg_dir, "leans.json"), encoding="utf-8"))
        cur.pop("senders", None); cur.pop("merges", None)
        self.write_setup("leans.json", cur)
        self.assertEqual(sc.Config.load(self.cfg_dir).leans.get("senders", {}), {})

    def test_A5_malformed_hand_edits_name_the_entry(self):
        def leans(**kw):
            cur = json.load(open(os.path.join(self.cfg_dir, "leans.json"), encoding="utf-8")); cur.update(kw); self.write_setup("leans.json", cur)
        leans(senders={"bad@pal.test": {"kind": "floor", "value": "high", "reason": "x"}})
        with self.assertRaises(sc.SetupError) as cm:
            sc.Config.load(self.cfg_dir)
        self.assertIn("bad@pal.test", str(cm.exception))
        leans(senders={"nul@pal.test": None})
        with self.assertRaises(sc.SetupError) as cm:
            sc.Config.load(self.cfg_dir)
        self.assertIn("nul@pal.test", str(cm.exception))
        leans(senders={})
        self.write_setup("labels.json", {"labels": {"Broken-Label": None}})
        with self.assertRaises(sc.SetupError) as cm:
            sc.Config.load(self.cfg_dir)
        self.assertIn("Broken-Label", str(cm.exception))
        self.write_setup("labels.json", {"labels": {}})
        self.write_setup("keywords.json", {"lists": {"job": {"weight": 1, "phrases": None}}})
        with self.assertRaises(sc.SetupError) as cm:
            sc.Config.load(self.cfg_dir)
        self.assertIn("job", str(cm.exception))

    def test_A5_lean_addresses_match_case_insensitively(self):
        for i in range(5):
            self.exchange("lean@pal.test", 300 - i * 30)
        self.write_leans({"senders": {"LEAN@Pal.Test": {"kind": "mute", "reason": "his word"}}})
        r = sc.standing(self.mb(), "lean@pal.test", self.cfg(), NOW)
        self.assertEqual(r["standing"], 0.0)
        self.assertTrue(any("lean" in x.lower() for x in r["reasons"]))

    def test_A7_label_names_are_trimmed_and_read_must_be_boolean_true(self):
        self.label("Label_R", "Example-Reads")
        r = self.msg("p@fresh.test", 0.2, "x", labels=("INBOX", "Label_R"))
        self.write_setup("labels.json", {"labels": {"Example-Reads ": {"read": True}}})
        self.assertEqual(sc.route(self.mb(), r, self.cfg()), "A")             # trailing space in the setup file
        self.write_setup("labels.json", {"labels": {"Example-Reads": {"read": "false"}}})
        cfg = self.cfg()
        self.assertEqual(sc.route(self.mb(), r, cfg), "B")                     # a string is not a permission (fail closed)
        self.assertTrue(any("Example-Reads" in w for w in cfg.warnings), cfg.warnings)

    def test_A9g_silence_check_handles_sub_day_gaps(self):
        for k in range(40):
            self.msg("busy@pal.test", 60 + k * 0.75, "note")
        self.msg(ME, 100, "hi", sent=1, labels=("SENT",), to=("busy@pal.test",))
        out = delta.run(self.con, NOW - 7 * D, NOW)
        self.assertIn(("silence", "busy@pal.test"), {(x["kind"], x["ref"]) for x in out["missing"]})

    def test_A4f_clock_skew_cannot_make_standing_grow(self):
        for i in range(6):
            self.exchange("pal@pal.test", 100 - i * 10)
        mb, cfg = self.mb(), self.cfg()
        newest = max(m["ms"] for m in mb.msgs)
        at_newest = sc.standing(mb, "pal@pal.test", cfg, newest)["raw"]       # no fade yet: the most it can ever be
        self.assertLessEqual(sc.standing(mb, "pal@pal.test", cfg, NOW - 400 * D)["raw"], at_newest + 1e-9)

    def test_A6i_null_thread_ids_never_merge_threads(self):
        self.msg(ME, 5, "mine", sent=1, labels=("SENT",), to=("x@y.test",), null_thread=True)
        s = self.msg("stranger@fresh.test", 0.1, "hello", null_thread=True)
        out = sc.attention_score(self.mb(), s, self.cfg(), NOW)
        self.assertFalse(any("reply to your own" in r for r in out["reasons"]), out["reasons"])

    def test_A6f_a_bad_date_row_is_skipped_and_counted(self):
        self.msg("a@pal.test", 1, "ok")
        self.con.execute("INSERT INTO messages(id,thread_id,internal_date,from_addr,subject,is_sent) VALUES('bad','tb','garbage','z@pal.test','x',0)")
        self.con.commit()
        mb = self.mb()
        self.assertEqual(mb.skipped_rows, 1)
        self.assertEqual(len(delta.run(self.con, NOW - 7 * D, NOW)["skipped_rows"]), 1)

    def test_A3_path_a_validates_its_input(self):
        cfg = self.cfg()
        sc.importance_urgency(None, cfg)
        sc.importance_urgency({"deadline_days": float("nan")}, cfg)
        t = sc.importance_urgency({"deadline_days": True}, cfg)
        self.assertEqual(t["importance_points"], 0.0)

    def test_A4j_and_fade_floor_guards_refuse_bad_settings(self):
        for sect, key, val in (("standing", "tau_days", 0), ("standing", "keep_floor", 0), ("standing", "keep_floor", 1.5), ("standing", "squash_k", 0)):
            self.write_setup("leans.json", json.load(open(os.path.join(HERE, "fixtures", "setup", "leans.json"), encoding="utf-8")))
            self.points_edit(sect, **{key: val})
            with self.assertRaises(sc.SetupError) as cm:
                sc.Config.load(self.cfg_dir)
            self.assertIn(key, str(cm.exception))

    def test_A11g_standing_cache_follows_content_not_object_identity(self):
        for i in range(6):
            self.exchange("pal@pal.test", 100 - i * 10)
        mb, cfg = self.mb(), self.cfg()
        a = sc.standing(mb, "pal@pal.test", cfg, NOW)["standing"]
        cfg.points["standing"]["scale_max"] = 2.0
        self.assertNotEqual(sc.standing(mb, "pal@pal.test", cfg, NOW)["standing"], a)


    # ---- round 2: mutants that survived, and two small fixes -----------------------------------------------------
    def test_R2_bulk_penalty_pins_a_bulk_mailer_with_a_keyword_to_zero(self):
        kw = json.load(open(os.path.join(self.cfg_dir, "keywords.json"), encoding="utf-8"))["lists"]["job"]["phrases"][0]
        b = self.msg("promo@shop.test", 0.1, "our " + kw + " sale", labels=("INBOX", "CATEGORY_PROMOTIONS"), list_id="<p.shop.test>")
        out = sc.attention_score(self.mb(), b, self.cfg(), NOW)
        self.assertEqual(out["score"], 0.0, out["reasons"])      # keyword +1.0 is wiped out by the bulk penalty -2.0
        self.assertTrue(any("bulk" in r for r in out["reasons"]), out["reasons"])

    def test_R2_heating_needs_more_than_one_voice(self):
        for k in range(6):
            self.msg("solo@pal.test", ago_days=0, ago_hours=40 - k * 6, thread="mono", subject="monologue")
        out = delta.run(self.con, NOW - 7 * D, NOW)
        self.assertNotIn(("heating", "mono"), {(x["kind"], x["ref"]) for x in out["changed"]})

    def test_R2_burst_needs_the_ratio_not_just_the_count(self):
        self.label("L_b", "Busy-ish-Project")
        for k in range(25):                                           # about one a week over the lookback
            self.msg("a@pal.test", 30 + 7 * k, "b", labels=("INBOX", "L_b"))
        for k in range(5):                                            # 5 in a 28-day window is about normal for it
            self.msg("a@pal.test", 2 + 5 * k, "b", labels=("INBOX", "L_b"))
        out = delta.run(self.con, NOW - 28 * D, NOW)
        self.assertNotIn(("burst", "Busy-ish-Project"), {(x["kind"], x["ref"]) for x in out["changed"]})

    def test_R2_a_label_listed_twice_once_readable_once_not_is_not_readable(self):
        self.label("Label_R", "Example-Reads")
        r = self.msg("p@fresh.test", 0.2, "x", labels=("INBOX", "Label_R"))
        self.write_setup("labels.json", {"labels": {"Example-Reads": {"read": True}, "example-reads ": {"read": False}}})
        cfg = self.cfg()
        self.assertEqual(sc.route(self.mb(), r, cfg), "B")
        self.assertTrue(any("example-reads" in w.lower() for w in cfg.warnings), cfg.warnings)

    def test_R2_keep_floor_outside_about_half_is_refused_citing_his_ruling(self):
        for val in (0.3, 0.39, 0.61, 0.7):
            self.write_setup("leans.json", json.load(open(os.path.join(HERE, "fixtures", "setup", "leans.json"), encoding="utf-8")))
            self.points_edit("standing", keep_floor=val)
            with self.assertRaises(sc.SetupError) as cm:
                sc.Config.load(self.cfg_dir)
            self.assertIn("keep_floor", str(cm.exception))
            self.assertIn("ruling", str(cm.exception).lower())
        for val in (0.4, 0.5, 0.6):
            self.write_setup("leans.json", json.load(open(os.path.join(HERE, "fixtures", "setup", "leans.json"), encoding="utf-8")))
            self.points_edit("standing", keep_floor=val)
            sc.Config.load(self.cfg_dir)


if __name__ == "__main__":
    unittest.main()
