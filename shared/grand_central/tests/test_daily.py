"""Tests for daily.py (Step 7). Temp DB built from the migrations; the pull step is a fake; never the live rig.db,
never the network, never Google."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import ast, json, os, re, sqlite3, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import clock, daily, migrate, store  # noqa: E402

NOW = "2026-11-12T15:00:00+00:00"
OK_TOKEN = lambda: {"status": "OK-FOR-NOW-IF-TESTING"}  # noqa: E731
NO_BACKUP = lambda: None  # noqa: E731
MS = lambda iso: int(__import__("datetime").datetime.fromisoformat(iso).timestamp() * 1000)  # noqa: E731


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.tmp.name, "rig.db")
        c = sqlite3.connect(self.p, isolation_level=None)
        for n, path in migrate.list_migrations():
            migrate.apply_file(c, path, n)
            # step 2.6: this fixture seeds old-table rows, which migration 020 freezes in a real database
            for (_t,) in c.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'frozen!_%' ESCAPE '!'").fetchall():
                c.execute("DROP TRIGGER " + _t)
        c.close()
        store.set_path(self.p)
        self._env = {k: os.environ.get(k) for k in ("AGE_NOW", "AGE_NOTES_ROOT")}
        os.environ["AGE_NOW"] = NOW
        os.environ["AGE_NOTES_ROOT"] = self.tmp.name

    def tearDown(self):
        store.set_path(None)
        for k, v in self._env.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.tmp.cleanup()

    def sql(self, q, a=()):
        c = sqlite3.connect(self.p)
        c.execute(q, a); c.commit(); c.close()

    def msg(self, mid, frm, subj, iso, extra=None):
        self.sql("INSERT INTO messages(id,thread_id,internal_date,label_ids,from_addr,subject,is_sent,list_id) VALUES(?,?,?,?,?,?,0,?)",
                 (mid, "t" + mid, MS(iso), '["INBOX"]', frm, subj, extra))

    def queue(self):
        c = sqlite3.connect(self.p)
        r = c.execute("SELECT kind,subject_ref,question,proposed_answer,status FROM queue ORDER BY id").fetchall()
        c.close()
        return r

    def run_daily(self, **kw):
        kw.setdefault("token_fn", OK_TOKEN)
        kw.setdefault("backup_fn", NO_BACKUP)
        kw.setdefault("pull_fn", lambda after, mt: (0, ""))
        return daily.run(**kw)

    # ---- watermark -------------------------------------------------------------------------------------
    def test_first_run_window_is_two_days(self):
        seen = []
        r = self.run_daily(pull_fn=lambda a, mt: (seen.append((a, mt)) or (0, "")))
        self.assertEqual(r["status"], "OK")
        self.assertEqual(seen, [("2026-11-10", daily.DEFAULT_MAX_THREADS)])

    def test_watermark_set_on_success_and_used_next(self):
        self.run_daily()
        self.assertEqual(daily.watermark(), "2026-11-12T15:00:00Z")
        os.environ["AGE_NOW"] = "2026-11-13T15:00:00+00:00"
        seen = []
        self.run_daily(pull_fn=lambda a, mt: (seen.append(a) or (0, "")))
        self.assertEqual(seen, ["2026-11-12"])
        self.assertEqual(daily.watermark(), "2026-11-13T15:00:00Z")

    def test_failed_pull_keeps_watermark_and_is_error(self):
        self.run_daily()
        wm = daily.watermark()
        os.environ["AGE_NOW"] = "2026-11-14T15:00:00+00:00"
        r = self.run_daily(pull_fn=lambda a, mt: (1, "boom invalid_grant"))
        self.assertEqual(r["status"], "ERROR")
        self.assertIn("expired rig login", r["error"])
        self.assertEqual(daily.watermark(), wm)
        self.assertEqual(daily.build_tile(r)["status"], "ERROR")

    def test_paused_is_error_with_hint(self):
        r = self.run_daily(pull_fn=lambda a, mt: (75, "STOP paused"))
        self.assertEqual(r["status"], "ERROR")
        self.assertIn("PAUSED", r["error"])

    def test_window_uses_new_york_day(self):
        after, lo = daily.window(clock.now(), "2026-11-13T03:30:00Z")   # 22:30 on the 12th in Testburg
        self.assertEqual(after, "2026-11-12")
        self.assertEqual(lo, "2026-11-12T05:00:00Z")

    # ---- proposals -------------------------------------------------------------------------------------
    def seed_world(self):
        self.msg("old1", "Pal@Known.example", "hello", "2026-06-01T10:00:00+00:00")        # seen before the window
        self.sql("INSERT INTO rules(match_kind,match_value,subject_glob,kind_label,folder_guess,status) VALUES('domain','shop.example','*receipt*','receipt','Receipts','approved')")
        self.sql("INSERT INTO rules(match_kind,match_value,status,folder_guess) VALUES('address','draft@x.com','proposed','Nope')")
        self.sql("INSERT INTO keywords(list_name,phrase) VALUES('clock_words','by friday'),('job_phrases','tryout')")

    def test_proposals_generated(self):
        self.seed_world()
        pull = lambda a, mt: (self.msg("n1", "pal@known.example", "lunch?", "2026-11-12T12:00:00+00:00") or   # noqa: E731
                              self.msg("n2", "Stranger@new.example", "Hi there", "2026-11-12T12:05:00+00:00") or
                              self.msg("n3", "orders@shop.example", "Your receipt 123", "2026-11-12T12:10:00+00:00") or
                              self.msg("n4", "pal@known.example", "Need the form by Friday", "2026-11-12T12:20:00+00:00") or
                              self.msg("n5", "talent@agency.example", "Tryout: Fred", "2026-11-12T12:30:00+00:00") or
                              self.msg("n6", "news@letter.example", "Weekly digest", "2026-11-12T12:40:00+00:00", "<list.x>") or
                              self.msg("n7", "orders@shop.example", "Shipping notice", "2026-11-12T12:50:00+00:00") or (0, ""))
        r = self.run_daily(pull_fn=pull)
        self.assertEqual(r["status"], "OK", r)
        self.assertEqual(r["new_items"], 7)
        q = self.queue()
        kinds = lambda k: [x for x in q if x[0] == k]  # noqa: E731
        who = {x[1] for x in kinds("who-is-this")}
        self.assertEqual(who, {"address:stranger@new.example", "address:talent@agency.example", "address:orders@shop.example"})   # known + bulk senders excluded
        lab = kinds("apply-label")
        self.assertEqual(len(lab), 1)                         # only n3: glob matches, n7 does not; the proposed rule is ignored
        self.assertEqual(lab[0][3], "Receipts")
        urg = {x[2] for x in kinds("flag-urgent")}
        self.assertEqual(len(urg), 2)                          # n4 clock word, n5 job phrase
        self.assertTrue(all(x[4] == "open" for x in q))
        # 'arrived' event for every new item
        c = sqlite3.connect(self.p)
        self.assertEqual(c.execute("SELECT count(DISTINCT item_id) FROM item_events WHERE kind='arrived'").fetchone()[0], 8)
        c.close()

    def test_rerun_is_idempotent_and_dismissed_not_reasked(self):
        self.seed_world()
        self.msg("n2", "Stranger@new.example", "Hi there", "2026-11-12T12:05:00+00:00")
        self.run_daily()
        self.assertEqual(len(self.queue()), 1)
        self.sql("UPDATE queue SET status='dismissed'")
        os.environ["AGE_NOW"] = "2026-11-12T16:00:00+00:00"
        self.run_daily(dry_run=True)             # dry-run recomputes over the same items: nothing new
        self.assertEqual(len(self.queue()), 1)

    def test_old_backfilled_mail_does_not_flood(self):
        self.msg("o", "stranger@new.example", "Urgent by friday", "2026-05-01T12:00:00+00:00")
        self.sql("INSERT INTO keywords(list_name,phrase) VALUES('clock_words','by friday')")
        r = self.run_daily()
        self.assertEqual(r["new_items"], 0)
        self.assertEqual(self.queue(), [])

    def test_cap_warns(self):
        for i in range(daily.PROPOSAL_CAP_PER_KIND + 3):
            self.msg("c%d" % i, "s%d@new.example" % i, "hi", "2026-11-12T12:00:00+00:00")
        r = self.run_daily()
        self.assertEqual(r["status"], "WARN")
        self.assertEqual(len(self.queue()), daily.PROPOSAL_CAP_PER_KIND)

    # ---- dry run ---------------------------------------------------------------------------------------
    def test_dry_run_never_pulls_backs_up_or_moves_watermark(self):
        self.msg("n2", "Stranger@new.example", "Hi there", "2026-11-12T12:05:00+00:00")
        def boom(*a):
            raise AssertionError("dry-run must not call this")
        r = daily.run(dry_run=True, pull_fn=boom, backup_fn=boom, token_fn=OK_TOKEN)
        self.assertEqual(r["status"], "OK")
        self.assertIsNone(daily.watermark())
        self.assertEqual(len(self.queue()), 1)
        self.assertFalse(os.path.exists(daily.tile_path()))

    # ---- tile / token ----------------------------------------------------------------------------------
    def test_tile_written_and_token_warnings(self):
        r = self.run_daily(token_fn=lambda: {"status": "EXPIRES-SOON-IF-TESTING", "if_testing_mode_refresh_token_dies": "2026-11-13"})
        self.assertEqual(r["status"], "WARN")
        daily.write_tile(daily.build_tile(r), daily.tile_path())
        with open(daily.tile_path(), encoding="utf-8") as f:
            t = json.load(f)
        self.assertEqual(t["status"], "NEEDS_REVIEW")
        self.assertIn("2026-11-13", t["items"][0]["detail"])
        self.assertEqual([k["key"] for k in t["kpis"]], ["new_items", "who-is-this", "apply-label", "flag-urgent"])
        r = self.run_daily(token_fn=lambda: {"status": "EXPIRED-IF-TESTING"})
        self.assertEqual(r["status"], "WARN")     # still tries, and a pull that works is not an error

    def test_pull_cap_and_quarantine_warn(self):
        def pull(a, mt):
            c = sqlite3.connect(self.p)
            c.execute("INSERT INTO runs(started,finished,args,counts) VALUES(?,?,?,?)",
                      ("x", "2026-11-12T15:00:05+00:00", "{}", json.dumps({"threads": daily.DEFAULT_MAX_THREADS, "quarantined": 2})))
            c.commit(); c.close()
            return 0, ""
        r = self.run_daily(pull_fn=pull)
        self.assertEqual(r["status"], "WARN")
        self.assertEqual(len(r["warnings"]), 2)

    # ---- never any Gmail write path --------------------------------------------------------------------
    def test_label_refresh_runs_after_pull_and_failure_is_warn(self):
        order = []
        r = self.run_daily(pull_fn=lambda a, mt: (order.append("pull") or (0, "")),
                           label_fn=lambda: (order.append("labels") or (0, "")))
        self.assertEqual(order, ["pull", "labels"])
        self.assertEqual(r["label_resync"], {"rc": 0})
        r = self.run_daily(pull_fn=lambda a, mt: (0, ""), label_fn=lambda: (1, "boom"))
        self.assertEqual(r["status"], "WARN")
        self.assertTrue(any("label refresh failed" in w for w in r["warnings"]))

    def test_no_gmail_write_path(self):
        with open(os.path.join(ROOT, "daily.py"), encoding="utf-8") as f:
            full = f.read()
        tree = ast.parse(full)
        tree.body = tree.body[1:]            # drop the module docstring (it names the things it forbids)
        src = ast.unparse(tree)
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                mods.add((n.module or "").split(".")[0])
        allowed = {"argparse", "datetime", "fnmatch", "json", "os", "subprocess", "sys", "zoneinfo", "status_lights",
                   "backup", "clock", "gc_settings", "store", "store_items", "store_meaning", "token_check"}
        self.assertEqual(mods - allowed, set())
        self.assertNotRegex(src, r"(?i)\bmover\b.*import|import.*\bmover\b|batchModify|messages/modify|labels/modify|email_fetch|safe_calendar|safe_tasks|rig_env")
        # every subprocess it launches is pull.py (the pull, and since STEP 4b the ids-only label refresh)
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") in ("run", "Popen", "call", "check_output", "system")]
        self.assertEqual(len(calls), 2)
        for c in calls:
            self.assertIn("'pull.py'", ast.unparse(c))
        self.assertIn("pull.py", full)
        # only proposals are written: queue rows, items/events (backfill), source_state, diary event
        writes = set(re.findall(r"(?:INSERT(?: OR \w+)? INTO|UPDATE|DELETE FROM)\s+(\w+)", src))
        self.assertEqual(writes, set())      # daily.py itself holds no raw write SQL; writes go through store*/queue_add



class PullWindowTests(unittest.TestCase):
    """STEP 6 (calendar/tasks freshness): the ahead window, the freshness cutoff and the sources-only mode."""
    def setUp(self):
        os.environ.setdefault("RIG_HANDOFF_DIR", tempfile.mkdtemp(prefix="rig-handoff-test-"))
        import pull
        self.pull = pull

    def test_calendar_window_reaches_mid_february(self):
        self.assertEqual(self.pull.CALENDAR_AHEAD_DAYS, 95)

    def test_auto_freshness_is_under_a_day(self):
        self.assertLess(self.pull.FRESH_HOURS, 24)

    def test_sources_only_skips_email_and_pulls_sources(self):
        import argparse
        p = self.pull
        calls = []
        saved = (p.pull_email, p.pull_source_if_needed, p.flush_pending, p.prune_quarantine_files)
        p.pull_email = lambda *a, **k: calls.append("email")
        p.pull_source_if_needed = lambda db, src, mode, fn: calls.append((src, mode))
        p.flush_pending = lambda db: None
        p.prune_quarantine_files = lambda *a, **k: None
        try:
            db = sqlite3.connect(":memory:")
            db.executescript("CREATE TABLE runs(started,finished,args,counts);")
            args = argparse.Namespace(planted=None, regate_quarantined=None, release_quarantined=None, label_resync=False,
                                      inbox_backfill=False, sources_only=True, months=None, max_threads=0, after=None,
                                      before=None, calendar="always", tasks="always", filters="never", contacts="never")
            p.db_path = lambda: ":memory:"
            p.run(args, db)
        finally:
            p.pull_email, p.pull_source_if_needed, p.flush_pending, p.prune_quarantine_files = saved
        self.assertNotIn("email", calls)
        self.assertEqual(calls, [("calendar", "always"), ("tasks", "always"), ("filters", "never"), ("contacts", "never")])

if __name__ == "__main__":
    unittest.main()
