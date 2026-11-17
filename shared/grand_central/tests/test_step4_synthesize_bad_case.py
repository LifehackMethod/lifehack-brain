"""Step 4 planted bad case: the old one-shot summary (synthesize.py) fails fixture case 1 (paid test-reel while his
note says all tryouts are closed). NO model is called: the bundle and prompt it WOULD send are built from a scratch
database (a temp copy shaped by the repo migrations, never the live rig.db), and the old-style write-up (demo/bad_draft_case1)
is graded by grade.py.   Run: python3 tests/test_step4_synthesize_bad_case.py

What it shows (all by code, from the fixture):
  1. the AI would receive only an ENVELOPE line for the test-reel (subject, sender, date): none of the body-only facts
     (the tape due date, the end-of-day time, the ask to confirm, the upload promise) reach the prompt;
  2. his stored "tryouts closed" note IS in the prompt as his own word, but nothing in the prompt or the reply schema
     asks the AI to check it against new mail, and the reply schema has no needs_him / deadlines / money form and no
     per-email accounting, so there is no place for the contradiction or for the proof that the email was used;
  3. the write-up shaped like what that reply produces fails grade.py on case 1.
"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import contextlib
import importlib.util
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import step3_fixture  # noqa: E402
import migrate, store, store_items  # noqa: E402
import run as er  # noqa: E402
import synthesize as syn  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures", "morning_weeks")
CASE = os.path.join(FIX, "cases", "01_paid_testreel")
NOW = "2026-11-15T09:00:00+00:00"
ME = "owner@me.test"


class OldSummaryFailsCase1(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.tmp.name, "scratch-rig.db")
        c = sqlite3.connect(self.p, isolation_level=None)
        for n, path in migrate.list_migrations():
            migrate.apply_file(c, path, n)
        step3_fixture.seed_domain_vocab(c)
        c.close()
        store.set_path(self.p)
        self._old = dict((k, os.environ.get(k)) for k in ("AGE_NOW", "AGE_NOTES_ROOT"))
        os.environ["AGE_NOW"] = NOW
        os.environ["AGE_NOTES_ROOT"] = self.tmp.name
        self._lm = syn.LIFE_MAP_PATH
        syn.LIFE_MAP_PATH = os.path.join(self.tmp.name, "no-life-map.md")

    def tearDown(self):
        syn.LIFE_MAP_PATH = self._lm
        store.set_path(None)
        for k, v in self._old.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.tmp.cleanup()

    def sql(self, q, a=()):
        c = sqlite3.connect(self.p)
        c.execute(q, a)
        c.commit()
        c.close()

    def load_case1(self):
        with open(os.path.join(CASE, "delta", "catalogue.jsonl"), encoding="utf-8") as fh:
            row = json.loads(fh.readline())
        import datetime as dt
        ms = int(dt.datetime(2026, 11, 15, 8, 42, tzinfo=dt.timezone.utc).timestamp() * 1000)
        # the front room's database only ever holds the ENVELOPE: sender, subject, date, labels (no body column exists)
        self.sql("INSERT INTO labels(id,name,type) VALUES('INBOX','INBOX','system')")
        self.sql("INSERT INTO messages(id,thread_id,internal_date,label_ids,from_addr,from_name,to_addrs,cc_addrs,subject,is_sent) "
                 "VALUES(?,?,?,?,?,?,?,?,?,0)", ("m1", "th-101", ms, json.dumps(["INBOX"]), "dana.whitfield@hollismarshtalent.example",
                                                 "Dana Whitfield", json.dumps([ME]), "[]", row["subject"]))
        # his confirmed note, as his own word: the baseline's "all tryouts closed"
        store.record_answer("Any tryouts open?", "No tryouts pending, all tryouts closed", "test", "2026-11-13", "project", "Gigs",
                            "storyline", "No tryouts pending. All tryouts closed as of 2026-11-10; nothing out on submission.")
        store_items.backfill_items()
        er.run()

    def test_old_summary_never_sees_the_body_and_has_no_place_for_the_contradiction(self):
        self.load_case1()
        bundle = syn.build_bundle()
        prompt = syn.build_prompt(bundle, (1, 2, 3))
        with open(os.path.join(CASE, "delta", "thread-01-hollis.md"), encoding="utf-8") as fh:
            body = fh.read()
        # 1. the envelope line is there; the body-only facts are not
        self.assertIn("Paid test-reel", prompt)
        for body_only in ("Tape due Thursday", "end of day", "Can you confirm", "upload link", "sides attached"):
            self.assertIn(body_only, body)                    # they ARE in the email...
            self.assertNotIn(body_only, prompt, body_only)    # ...and never reach the old summary's AI
        self.assertNotIn("2026-11-20", prompt)
        # 2. his note is in the prompt as his word; nothing asks to check it against new mail; no form, no per-email accounting
        self.assertIn("All tryouts closed", prompt)
        low = prompt.lower()
        # (its rule 10 does say "if the data seems to disagree with his word, ask a question": see the best-case test below)
        for must_have in ("needs_him", "deadlines", "sorted_out_by_triage", "skipped_with_reason"):
            self.assertNotIn(must_have, low, must_have)
        self.assertEqual(len(bundle["sections"]["email"]), 1)     # (one email in this case; in a real mailbox EMAIL_CAP=350 applies)

    def test_the_write_up_that_reply_shape_produces_fails_the_grader(self):
        spec = importlib.util.spec_from_file_location("morning_grade", os.path.join(FIX, "grade.py"))
        grade = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(grade)
        demo = os.path.join(FIX, "demo")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = grade.run(os.path.join(demo, "bad_draft_case1.md"), os.path.join(CASE, "expected.json"),
                           os.path.join(demo, "bad_draft_case1.form.json"))
        if os.environ.get("MORNING_TEST_VERBOSE"):
            print(buf.getvalue())
        self.assertEqual(rc, 1)
        self.assertIn("RESULT: FAIL (0/6 checks passed)", buf.getvalue())

    def test_even_a_best_case_old_reply_fails_on_what_it_structurally_cannot_carry(self):
        """Be fair to the old summary: its prompt (rule 10) tells it to ask when the data seems to disagree with his word, and
        the test-reel's SUBJECT line is in the bundle, so a good reply could ask the question. Grade that best case: the
        question is asked (those checks pass), but it has no form for the deadline, the money or the needs-him item (only the
        subject reached it) and no per-email accounting, so the grader still fails it."""
        spec = importlib.util.spec_from_file_location("morning_grade", os.path.join(FIX, "grade.py"))
        grade = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(grade)
        draft = os.path.join(self.tmp.name, "best_old.md")
        form = os.path.join(self.tmp.name, "best_old.form.json")
        with open(draft, "w", encoding="utf-8") as f:
            f.write("## What changed\n- A talent email about a paid test-reel arrived (seen by its subject line only).\n\n"
                    "## Picture\n- Gigs is moving.\n\n## Questions\n- Q1: Your note says all tryouts closed, but a paid "
                    "test-reel email arrived: did something change?\n")
        with open(form, "w", encoding="utf-8") as f:
            json.dump({"deadlines": [], "money": [], "needs_him": [], "project_updates": [], "questions": [], "coverage": {}}, f)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = grade.run(draft, os.path.join(CASE, "expected.json"), form)
        out = buf.getvalue()
        if os.environ.get("MORNING_TEST_VERBOSE"):
            print(out)
        self.assertEqual(rc, 1)
        self.assertIn("PASS  contradiction-asked", out)
        self.assertIn("PASS  closed-not-a-fact", out)
        for failing in ("FAIL  needs-him-testreel", "FAIL  deadline-nov20", "FAIL  money-850", "FAIL  coverage"):
            self.assertIn(failing, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
