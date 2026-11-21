#!/usr/bin/env python3
"""Phase 1 steps 1.3 and 1.4: the fast clock, and the morning job (gcjobs.py; the midnight job is retired).
SYNTHETIC only: made-up mail, scratch folders, a FAKE pull (nothing touches Google), a FAKE model, a FAKE status light.
The live database and the live front room are never opened. Each planted bad case below was shown FAILING first
(see the "planted" notes in phase-1-step-3-result.md and phase-1-step-4-result.md).

Run: python3 tests/test_step13_14_jobs.py     (from shared/grand_central/)"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import gc_settings, gcjobs, morning, transcripts  # noqa: E402
import test_step4_morning as t4  # noqa: E402  (its scratch front room, fake model and fixture helpers)
gcjobs.MORNING_ATTEMPT_WAIT_S = 0 # 4P.3D slice W: the in-run retry wait is a test seam; tests never sleep

# The rows' checks, copied from the ready-to-install list: the tests grade receipts with the SAME grep -E the runner uses.
CHECKS = {
    "gc-fast-clock": r"^gc-fast-clock ok date=[0-9]{4}-[0-9]{2}-[0-9]{2} waiting=([0-9]+) cleared=\1 filed=[0-9]+ duplicate=[0-9]+ refused=[0-9]+ calendar=[fs][kre][a-z]+ tasks=[fs][kre][a-z]+ db=[dh][a-z]+ considered=[0-9]+ candidates=[0-9]+ morning=[a-z-]+( once_snapshot=[a-z-]+ once_diary_index=[a-z-]+ once_daily=[a-z-]+)? at=[0-9]{4}-",
    "gc-morning": r"^gc-morning ok date=[0-9]{4}-[0-9]{2}-[0-9]{2} desk=[a-z-]+ new=([0-9]+) accounted=\1 examined=[0-9]+ draft=[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z-]+(-topup[0-9]+)?\.md sources=[a-z]+ at=[0-9]{4}-",
}


def slurp(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def check_passes(job, line):
    """The runner's own test: grep -E on the line."""
    p = subprocess.run(["grep", "-E", CHECKS[job]], input=line + "\n", capture_output=True, text=True)
    return p.returncode == 0


class Scratch(unittest.TestCase):
    def setUp(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="step1314-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.drop = os.path.join(self.root, "drop")
        self.deliv = os.path.join(self.drop, "deliveries")
        os.makedirs(self.deliv)
        self.state = os.path.join(self.root, "state")
        self.notes = os.path.join(self.root, "notes")
        self.front = os.path.join(self.root, "front-room")
        self._env = dict((k, os.environ.get(k)) for k in ("AGE_FRONT_ROOM", "AGE_NOTES_ROOT", "GC_STATE_ROOT"))
        os.environ.update({"AGE_FRONT_ROOM": self.front, "AGE_NOTES_ROOT": self.notes, "GC_STATE_ROOT": self.state})
        self.addCleanup(self._restore)
        self.lines = []
        self.lights = []
        self.launched = []

    def _restore(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def say(self, m):
        self.lines.append(str(m))

    def light(self, only, out=None):
        self.lights.append(only)

    def receipt(self, job):
        p = os.path.join(self.state, job, "last-run.txt")
        return slurp(p).strip() if os.path.exists(p) else None

    def put_delivery(self, n, urgent=False, ms=1000):
        tid, mid = "b%05d" % n, "a%05d" % n
        obs = ({"deadline_stated": "yes", "direct_ask": "yes", "money_involved": "yes", "reply_expected": "yes"} if urgent
               else {"deadline_stated": "no", "direct_ask": "no", "money_involved": "no", "reply_expected": "no"})
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        doc = {"schema": "gc.delivery/1", "thread_id": tid, "message_id": mid, "subject": "s", "from": "f", "date": "d",
               "label": "l", "verdict": "safe",
               "triage": {"area": "work", "deadline": tomorrow if urgent else None, "do_or_know": "do", "how_soon": "now",
                          "needs_me": "yes" if urgent else "no", "obs": obs},
               "seen": "full", "internal_ms": ms, "header": "# thread %s | subject: s\n\n" % tid,
               "block": "=== message %s | d | from: f | label: l ===\nbody of %s\n\n" % (mid, mid)}
        name = "%s.%s.json" % (tid, mid)
        with open(os.path.join(self.deliv, name), "w", encoding="utf-8") as f:
            json.dump(doc, f)
        return name

    FRESH = "[pull] skipping calendar: fetched successfully within the last 18h (mode=auto)\n[pull] skipping tasks: fetched successfully within the last 18h (mode=auto)\n"

    def fast(self, pull=None, login_ok=None, **kw):
        kw.setdefault("now_local", datetime.datetime(2026, 11, 16, 3, 0))        # before 05:00: the morning is not due
        kw.setdefault("launch", lambda desk, st: self.launched.append(desk))
        self.envelope_pulls = [] # 4P.3D slice W: the envelope pull and the once-a-day launcher are stubbed per tick
        kw.setdefault("envelope_pull", lambda after: self.envelope_pulls.append(after) or (0, "[pull] envelopes ok after %s" % after))
        kw.setdefault("envelope_watermark", lambda: None)
        kw.setdefault("once", lambda now_local: dict((j, "done") for j in gcjobs.ONCE_A_DAY_JOBS))
        return gcjobs.fast_clock(drop=self.drop, state=os.path.join(self.state, "gc-fast-clock"),
                                 pull=pull or (lambda mode: (0, self.FRESH)), login_ok=login_ok or (lambda: True),
                                 mailroom_uid=os.getuid(), status_light=self.light, out=self.say, **kw)


# ================================================================ 1.3 the fast clock
class FastClock(Scratch):
    def test_a_good_run_files_pulls_proposes_candidates_and_writes_a_proof_that_passes_the_check(self):
        self.put_delivery(1, urgent=True)
        self.put_delivery(2)
        rc = self.fast()
        self.assertEqual(rc, 0, self.lines)
        self.assertEqual(os.listdir(self.deliv), [])
        line = self.receipt("gc-fast-clock")
        self.assertIn("waiting=2 cleared=2 filed=2 duplicate=0 refused=0 calendar=fresh tasks=fresh db=done considered=2 candidates=1 morning=not-due", line)
        self.assertTrue(check_passes("gc-fast-clock", line), line)
        cand = [json.loads(x) for x in slurp(os.path.join(self.front, "alarm-candidates.jsonl")).splitlines()]
        self.assertEqual([c["message_id"] for c in cand], ["a00001"])
        self.assertIn("nothing sent", cand[0]["status"])
        self.assertEqual(self.lights, ["intake,mailroom"])                 # the status-light call site was reached

    def test_a_quiet_ten_minutes_is_a_legitimate_zero_and_still_proves_what_it_examined(self):
        self.assertEqual(self.fast(), 0, self.lines)
        line = self.receipt("gc-fast-clock")
        self.assertIn("waiting=0 cleared=0", line)
        self.assertTrue(check_passes("gc-fast-clock", line), line)

    def test_PLANTED_ingest_that_moves_nothing_while_three_wait_leaves_no_proof(self):
        """A run that would claim success over zero filed items: the folder still holds 3, ingest 'did nothing'."""
        for n in (1, 2, 3):
            self.put_delivery(n)
        real = transcripts.ingest
        transcripts.ingest = lambda d, **k: {"ingested": 0, "duplicate": 0, "refused": 0, "deferred": 0}
        try:
            rc = self.fast()
        finally:
            transcripts.ingest = real
        self.assertEqual(rc, 1)
        self.assertIsNone(self.receipt("gc-fast-clock"))
        self.assertTrue(any("deliveries_not_cleared:0_of_3" in x for x in self.lines), self.lines)

    def test_PLANTED_a_forged_proof_line_over_zero_cleared_items_fails_the_check(self):
        good = "gc-fast-clock ok date=2026-11-16 waiting=3 cleared=3 filed=3 duplicate=0 refused=0 calendar=fresh tasks=fresh db=done considered=3 candidates=0 morning=done at=2026-11-16T10:00:00Z"
        self.assertTrue(check_passes("gc-fast-clock", good))
        self.assertFalse(check_passes("gc-fast-clock", good.replace("cleared=3", "cleared=0")))
        self.assertFalse(check_passes("gc-fast-clock", good.replace("calendar=fresh", "calendar=none")))
        self.assertFalse(check_passes("gc-fast-clock", good.replace("tasks=fresh", "tasks=failed")))
        self.assertFalse(check_passes("gc-fast-clock", "gc-fast-clock ok"))

    def test_PLANTED_a_pull_that_accounts_for_neither_source_is_not_a_success(self):
        self.put_delivery(1)
        rc = self.fast(pull=lambda mode: (0, "[pull] db=x planted=False\n"))
        self.assertEqual(rc, 1)
        self.assertIsNone(self.receipt("gc-fast-clock"))
        self.assertTrue(any("source_not_accounted:calendar,tasks" in x for x in self.lines), self.lines)
        self.assertEqual(os.listdir(self.deliv), [])                       # the mail was still filed

    def test_PLANTED_a_pull_with_recorded_errors_is_not_a_success(self):
        bad = "[pull] calendar: pulled 4 row(s) but 2 error(s) recorded — NOT marking source fresh (will retry next run)\n" + \
              "[pull] tasks: pulled 1 row(s), marked fresh at 2026-11-16T10:00:00Z\n"
        self.assertEqual(self.fast(pull=lambda mode: (0, bad)), 1)
        self.assertIsNone(self.receipt("gc-fast-clock"))

    def test_not_signed_in_is_75_files_the_mail_and_leaves_no_proof(self):
        self.put_delivery(1)
        self.assertEqual(self.fast(login_ok=lambda: False), 75)
        self.assertEqual(os.listdir(self.deliv), [])
        self.assertIsNone(self.receipt("gc-fast-clock"))
        self.assertEqual(self.fast(pull=lambda mode: (1, "error: Not logged in to Google")), 75)
        self.assertIsNone(self.receipt("gc-fast-clock"))

    def test_no_mailroom_folder_is_75_not_a_quiet_zero_and_an_unreadable_one_is_a_failure(self):
        shutil.rmtree(self.deliv)
        self.assertEqual(self.fast(), 75)
        os.makedirs(self.deliv)
        os.chmod(self.deliv, 0)
        try:
            self.assertEqual(self.fast(), 1)
        finally:
            os.chmod(self.deliv, 0o700)
        self.assertIsNone(self.receipt("gc-fast-clock"))

    def test_the_same_delivery_twice_is_a_duplicate_not_a_second_filing(self):
        self.put_delivery(1)
        self.assertEqual(self.fast(), 0)
        self.put_delivery(1)
        self.assertEqual(self.fast(), 0, self.lines)
        self.assertIn("filed=0 duplicate=1", self.receipt("gc-fast-clock"))
        cp = os.path.join(self.front, "alarm-candidates.jsonl")
        cand = slurp(cp) if os.path.exists(cp) else ""
        self.assertEqual(cand.count("a00001"), 0)

    def test_PLANTED_a_raw_network_read_in_this_code_would_be_caught_by_this_scan(self):
        """The fast clock must hold no outside read of its own. Shown failing on a planted copy first."""
        pat = re.compile(r"\b(urllib|requests|http\.client|socket|curl|wget)\b|gws\s+(gmail|calendar|tasks|sheets)|googleapis|messages\.get|format=full")
        src = slurp(os.path.join(ROOT, "gcjobs.py"))
        code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
        # the module docstring and comments may NAME what is forbidden; strip the docstring too
        code = re.sub(r'"""(?:.|\n)*?"""', "", code)
        self.assertEqual(pat.findall(code), [], "gcjobs.py holds an outside read")
        self.assertTrue(pat.search("import urllib.request\nurllib.request.urlopen(u)"))      # the scan itself can fail
        self.assertTrue(pat.search("subprocess.run(['curl','-s',u])"))


# ================================================================ 1.4 the morning job
class MorningJob(Scratch):
    def setUp(self):
        Scratch.setUp(self)
        self.env = t4.Env()
        self.addCleanup(self.env.close)
        os.environ["AGE_FRONT_ROOM"] = self.env.front
        sys.path.insert(0, HERE)
        import step3_fixture
        self.db = os.path.join(self.root, "scratch.db")
        step3_fixture.new_db(self.db).close()
        self.lm = os.path.join(self.root, "life-map.md")
        t4.write(self.lm, "## Weekly Win\nShip the proposal.\n")
        self.mdrop = os.path.join(self.root, "mdrop")
        self.mdeliv = os.path.join(self.mdrop, "deliveries")
        os.makedirs(self.mdeliv)
        os.makedirs(os.path.join(self.mdrop, "facts"))

    def put_case(self):
        self.env.drop, keep = self.mdeliv, self.env.drop
        cdir = os.path.join(t4.CASES, "01_paid_testreel")
        row = json.loads(t4.read(os.path.join(cdir, "delta", "catalogue.jsonl")).splitlines()[0])
        when, body = t4.parse_thread(os.path.join(cdir, "delta", row["file"]))[row["msg"]]
        self.env.rows[row["msg"]] = row
        self.env.deliver(row["thread"], row["msg"], row["sender"], row["subject"], when, row["label"], t4.triage_of(row["triage"]), body)
        self.env.drop = keep

    PULL_OK = "[pull] calendar: pulled 2 row(s), marked fresh at x\n[pull] tasks: pulled 1 row(s), marked fresh at x\n"

    def job(self, model, day=t4.DAY, **kw):
        self.pull_modes = []
        kw.setdefault("pull", lambda mode: (self.pull_modes.append(mode), (0, self.PULL_OK))[1])
        kw.setdefault("login_ok", lambda: True)
        extra = ["--drop", self.mdrop, "--notes-root", self.notes, "--db", self.db, "--life-map", self.lm, "--mailroom-uid", str(os.getuid())]
        return gcjobs.morning_job(day=day, desk="desk-a", state=os.path.join(self.state, "gc-morning"),
                                  hand_run=lambda argv, out: morning.hand_run(argv, model=model, out=out),
                                  status_light=self.light, extra_argv=extra, out=self.say, **kw)

    def test_a_good_morning_stages_a_draft_and_the_proof_names_it_and_passes_the_check(self):
        self.put_case()
        m = t4.FakeModel(self.env, t4.NOBASE)
        rc = self.job(m)
        self.assertEqual(rc, 0, self.lines)
        self.assertEqual(len(m.prompts), 1)
        line = self.receipt("gc-morning")
        self.assertIn("date=%s desk=desk-a new=1 accounted=1" % t4.DAY, line)
        self.assertIn("sources=refreshed", line)
        self.assertIn("draft=%s-desk-a.md" % t4.DAY, line)
        self.assertTrue(check_passes("gc-morning", line), line)
        proof = slurp(os.path.join(self.state, "morning", "last-proof.txt"))      # the lights read this one
        self.assertTrue(proof.startswith("morning read %s (desk-a): 1 new" % t4.DAY), proof)
        self.assertEqual(self.lights, ["morning"])
        for l in self.lines:
            self.assertNotIn("Lighthouse", l)

    def test_GC_DROP_points_the_morning_at_a_scratch_drop_with_no_drop_argument(self):
        self.put_case()
        os.environ["GC_DROP"] = self.mdrop
        self.addCleanup(os.environ.pop, "GC_DROP", None)
        self.assertEqual(gcjobs.default_drop(), self.mdrop)
        self.assertEqual(morning.default_drop(), self.mdrop)
        m = t4.FakeModel(self.env, t4.NOBASE)
        extra = ["--notes-root", self.notes, "--db", self.db, "--life-map", self.lm, "--mailroom-uid", str(os.getuid())]   # NO --drop
        rc = gcjobs.morning_job(day=t4.DAY, desk="desk-a", state=os.path.join(self.state, "gc-morning"),
                                hand_run=lambda argv, out: morning.hand_run(argv, model=m, out=out), status_light=self.light,
                                extra_argv=extra, out=self.say, pull=lambda mode: (0, self.PULL_OK), login_ok=lambda: True)
        self.assertEqual(rc, 0, self.lines)
        self.assertEqual(os.listdir(self.mdeliv), [])        # the scratch folder was filed and cleared

    def test_PLANTED_with_GC_DROP_unset_the_default_path_is_used(self):
        os.environ.pop("GC_DROP", None)
        self.assertEqual(gcjobs.default_drop(), gc_settings.drop_dir())
        self.assertEqual(morning.default_drop(), gc_settings.drop_dir())
        os.environ["GC_DROP"] = ""                            # empty counts as unset
        self.addCleanup(os.environ.pop, "GC_DROP", None)
        self.assertEqual(gcjobs.default_drop(), gc_settings.drop_dir())

    def test_PLANTED_a_morning_that_stages_nothing_leaves_no_proof(self):
        """The model call fails: nothing staged, the read says FAILED, and the job writes no success line."""
        self.put_case()
        rc = self.job(t4.Dead("timeout"))
        self.assertEqual(rc, 1)
        self.assertIsNone(self.receipt("gc-morning"))
        self.assertEqual(os.path.exists(os.path.join(self.notes, "desks", "desk-a", "records", "context", "%s-desk-a.md" % t4.DAY)), False)
        self.assertEqual(self.lights, ["morning"])                          # the light still gets its turn (it will read FAILED)

    @property
    def stub(self):
        return {"pull": lambda mode: (0, self.PULL_OK), "login_ok": lambda: True}

    def _fake_hand(self, proof):
        return lambda argv, out: (out("hand-run:    coverage: " + proof), 0)[1]

    def test_PLANTED_a_clean_looking_morning_with_no_draft_file_on_disk_is_not_a_success(self):
        """The read says every email is accounted for, but nothing was staged: the job checks the disk itself."""
        good = ("morning read %s (desk-a): 2 new of 2 examined; used 2, sorted out by triage 0, skipped with a reason 0; "
                "flagged-as-needing-him dropped: 0; every new email accounted for" % t4.DAY)
        rc = gcjobs.morning_job(day=t4.DAY, desk="desk-a", state=os.path.join(self.state, "gc-morning"),
                                hand_run=self._fake_hand(good), status_light=self.light, out=self.say, **self.stub)
        self.assertEqual(rc, 1)
        self.assertIsNone(self.receipt("gc-morning"))
        self.assertTrue(any("no_staged_draft_for_%s" % t4.DAY in x for x in self.lines), self.lines)

    def test_PLANTED_a_morning_whose_counts_do_not_add_up_is_not_a_success(self):
        rec = morning.records_context_dir(self.notes, "desk-a")
        os.makedirs(rec)
        t4.write(os.path.join(rec, "%s-desk-a.md" % t4.DAY), "# draft\n")
        bad = ("morning read %s (desk-a): 3 new of 3 examined; used 1, sorted out by triage 0, skipped with a reason 0; "
               "flagged-as-needing-him dropped: 0; every new email accounted for" % t4.DAY)
        rc = gcjobs.morning_job(day=t4.DAY, desk="desk-a", state=os.path.join(self.state, "gc-morning"),
                                hand_run=self._fake_hand(bad), status_light=self.light, out=self.say, **self.stub)
        self.assertEqual(rc, 1)
        self.assertIsNone(self.receipt("gc-morning"))
        self.assertTrue(any("new_emails_not_accounted" in x for x in self.lines), self.lines)

    def test_PLANTED_forged_morning_proofs_fail_the_check(self):
        good = "gc-morning ok date=2026-11-16 desk=desk-a new=4 accounted=4 examined=9 draft=2026-11-16-desk-a.md sources=refreshed at=2026-11-16T06:00:00Z"
        self.assertTrue(check_passes("gc-morning", good))
        self.assertFalse(check_passes("gc-morning", good.replace("accounted=4", "accounted=0")))
        self.assertFalse(check_passes("gc-morning", good.replace("draft=2026-11-16-desk-a.md", "draft=")))
        self.assertFalse(check_passes("gc-morning", "gc-morning ok"))

    def test_signed_out_model_is_75_and_a_second_run_the_same_day_starts_from_the_draft(self):
        self.put_case()
        self.assertEqual(self.job(t4.FakeModel(self.env, t4.NOBASE)), 0)
        self.assertEqual(self.job(t4.FakeModel(self.env, t4.NOBASE)), 0, self.lines)     # nothing new: no model call, still accounted
        self.assertIn("new=0 accounted=0", self.receipt("gc-morning"))
        self.assertTrue(check_passes("gc-morning", self.receipt("gc-morning")))
        rc = gcjobs.morning_job(day=t4.DAY, desk="desk-a", state=os.path.join(self.state, "gc-morning"),
                                hand_run=lambda argv, out: (out("hand-run: 5. FAILED, nothing staged: Not logged in"), 1)[1],
                                status_light=self.light, out=self.say, **self.stub)
        self.assertEqual(rc, 75)


# (the 1.4 midnight job is retired, 4P.3R: the morning run writes its own diary entry; see test_step4_morning.DiaryEntry)


# ================================================================ coordinator conditions, 2026-11-16
def hold(path, pid=None):
    """Make a lock directory held by a live process (this test run, unless another pid is given)."""
    os.makedirs(path)
    with open(os.path.join(path, "pid"), "w", encoding="utf-8") as f:
        f.write("%d\n" % (pid or os.getpid()))


class MorningTrigger(Scratch):
    """1. The fast clock starts the morning detached, once, after 05:00, never twice."""

    def at(self, hh, mm=0):
        return datetime.datetime(2026, 11, 16, hh, mm)

    def test_before_five_nothing_starts_and_after_five_one_detached_morning_starts(self):
        self.assertEqual(self.fast(now_local=self.at(4, 59)), 0)
        self.assertEqual(self.launched, [])
        self.assertIn("morning=not-due", self.receipt("gc-fast-clock"))
        self.assertEqual(self.fast(now_local=self.at(5, 0)), 0, self.lines)
        self.assertEqual(self.launched, ["desk-a"])
        line = self.receipt("gc-fast-clock")
        self.assertIn("morning=launched", line)
        self.assertTrue(check_passes("gc-fast-clock", line), line)

    def test_PLANTED_a_morning_already_running_is_not_started_again_and_the_tick_finishes(self):
        hold(gcjobs.morning_run_lock())                            # a live morning holds its own lock
        t0 = time.time()
        self.assertEqual(self.fast(now_local=self.at(7)), 0, self.lines)
        self.assertLess(time.time() - t0, 5)                       # the tick does not wait for the morning
        self.assertEqual(self.launched, [])
        self.assertIn("morning=running", self.receipt("gc-fast-clock"))

    def test_a_morning_that_just_started_or_keeps_failing_is_not_hammered(self):
        # 4P.3D slice W: the failed retries happen INSIDE the detached run; between detached launches the gap is
        # 1800 s and the day's hard ceiling is 6 attempts (every attempt counts, in-run ones included).
        self.assertEqual(self.fast(now_local=self.at(6, 0)), 0)
        self.assertEqual(self.fast(now_local=self.at(6, 10)), 0)       # 10 minutes later, no draft, nothing running
        self.assertEqual(self.launched, ["desk-a"])
        self.assertIn("morning=backoff", self.receipt("gc-fast-clock"))
        for hh, mm in ((6, 40), (7, 20), (8, 0), (8, 40), (9, 20)): # 1800 s apart: tries 2..6
            self.assertEqual(self.fast(now_local=self.at(hh, mm)), 0)
        self.assertEqual(len(self.launched), 6)
        self.assertEqual(self.fast(now_local=self.at(9, 50)), 0) # 30 min later, but the ceiling is 6
        self.assertIn("morning=gave-up-today", self.receipt("gc-fast-clock"))
        self.assertEqual(len(self.launched), 6)

    def test_a_staged_draft_for_today_means_done(self):
        rec = morning.records_context_dir(self.notes, "desk-a")
        os.makedirs(rec)
        with open(os.path.join(rec, "2026-11-16-desk-a.md"), "w", encoding="utf-8") as f:
            f.write("# draft\n")
        self.assertEqual(self.fast(now_local=self.at(8)), 0)
        self.assertEqual(self.launched, [])
        self.assertIn("morning=done", self.receipt("gc-fast-clock"))

    def test_the_real_launcher_starts_its_own_session_without_waiting(self):
        calls = []
        real = subprocess.Popen
        subprocess.Popen = lambda argv, **kw: calls.append((argv, kw))
        try:
            gcjobs.launch_morning_detached("desk-a", os.path.join(self.state, "gc-morning"))
        finally:
            subprocess.Popen = real
        argv, kw = calls[0]
        self.assertEqual(argv[-3:], ["morning", "--desk", "desk-a"])
        self.assertTrue(kw["start_new_session"])
        self.assertIs(kw["stdin"], subprocess.DEVNULL)

    def test_PLANTED_two_mornings_never_run_at_once(self):
        hold(gcjobs.morning_run_lock())
        called = []
        rc = gcjobs.morning_job(day=t4.DAY, desk="desk-a", state=os.path.join(self.state, "gc-morning"),
                                hand_run=lambda argv, out: called.append(1) or 0, status_light=self.light, out=self.say,
                                pull=lambda m: (0, ""), login_ok=lambda: True)
        self.assertEqual((rc, called), (75, []))


class SharedDbLock(Scratch):
    """2. gc-daily and the fast clock never write the live database together."""

    def test_PLANTED_gc_daily_holding_the_lock_makes_the_fast_clock_skip_only_its_database_part_honestly(self):
        self.put_delivery(1)
        hold(gcjobs.db_lock_path())
        pulls = []
        rc = self.fast(pull=lambda m: pulls.append(m) or (0, self.FRESH))
        self.assertEqual(rc, 0, self.lines)                          # a skip is not a failure
        self.assertEqual(pulls, [])
        self.assertEqual(os.listdir(self.deliv), [])                 # non-database work still done
        line = self.receipt("gc-fast-clock")
        self.assertIn("calendar=skipped tasks=skipped db=held", line)
        self.assertTrue(check_passes("gc-fast-clock", line), line)
        self.assertTrue(os.path.isdir(gcjobs.db_lock_path()))        # and the other run's lock was not touched

    def test_the_fast_clock_takes_and_releases_the_lock_around_its_pull(self):
        seen = []
        self.assertEqual(self.fast(pull=lambda m: seen.append(gcjobs.lock_holder_alive(gcjobs.db_lock_path())) or (0, self.FRESH)), 0)
        self.assertEqual(seen, [True])
        self.assertFalse(os.path.exists(gcjobs.db_lock_path()))
        self.assertIn("db=done", self.receipt("gc-fast-clock"))

    def test_a_dead_owners_lock_is_taken_over(self):
        hold(gcjobs.db_lock_path(), pid=2 ** 22 + 12345)             # no such process
        self.assertEqual(self.fast(), 0, self.lines)
        self.assertIn("db=done", self.receipt("gc-fast-clock"))


class MorningRefresh(MorningJob):
    """3. The morning alone forces a fresh calendar and tasks pull just before it reads."""

    def test_PLANTED_stale_sources_are_refreshed_in_always_mode_before_the_read(self):
        self.put_case()
        order = []
        real = morning.hand_run
        rc = gcjobs.morning_job(
            day=t4.DAY, desk="desk-a", state=os.path.join(self.state, "gc-morning"), status_light=self.light, out=self.say,
            pull=lambda mode: (order.append("pull:" + mode), (0, self.PULL_OK))[1], login_ok=lambda: True,
            extra_argv=["--drop", self.mdrop, "--notes-root", self.notes, "--db", self.db, "--life-map", self.lm,
                        "--mailroom-uid", str(os.getuid())],
            hand_run=lambda argv, out: (order.append("read"), real(argv, model=t4.FakeModel(self.env, t4.NOBASE), out=out))[1])
        self.assertEqual(rc, 0, self.lines)
        self.assertEqual(order, ["pull:always", "read"])
        self.assertIn("sources=refreshed", self.receipt("gc-morning"))
        self.assertFalse(os.path.exists(gcjobs.db_lock_path()))

    def test_when_gc_daily_holds_the_database_the_morning_reads_stored_sources_and_says_so(self):
        self.put_case()
        hold(gcjobs.db_lock_path())
        gcjobs.REFRESH_LOCK_WAIT_S, keep = 0, gcjobs.REFRESH_LOCK_WAIT_S
        try:
            rc = self.job(t4.FakeModel(self.env, t4.NOBASE))
        finally:
            gcjobs.REFRESH_LOCK_WAIT_S = keep
        self.assertEqual(rc, 0, self.lines)
        self.assertEqual(self.pull_modes, [])
        self.assertIn("sources=held", self.receipt("gc-morning"))
        self.assertTrue(check_passes("gc-morning", self.receipt("gc-morning")))

    def test_a_failed_refresh_does_not_stop_the_morning_but_is_named_in_the_proof(self):
        self.put_case()
        rc = self.job(t4.FakeModel(self.env, t4.NOBASE), pull=lambda m: (1, "boom"))
        self.assertEqual(rc, 0, self.lines)
        self.assertIn("sources=failed", self.receipt("gc-morning"))


if __name__ == "__main__":
    unittest.main()
