#!/usr/bin/env python3
"""Step 2 attack fixes, front-room side: ingest and catalogue
(builder's self-check; the attacker re-grades). Synthetic data only, under a FAKE HOME so that the
'~' and '$HOME' spellings are really exercised (the folder sits under the fake home).

Run:  python3 -I -B tests/test_step2_door.py     (from shared/grand_central/)
"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import fcntl
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import transcripts  # noqa: E402

REL = ".local/share/example-data/front-room"
TOOLLESS = transcripts.Caller("test-reader", tools=())


class FakeHome(object):
    def __init__(self):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="fakehome-"))
        self.front = os.path.join(self.root, REL)
        self.drop = os.path.join(self.root, "drop", "deliveries")
        os.makedirs(self.drop)
        self._env = dict((k, os.environ.get(k)) for k in ("HOME", "AGE_FRONT_ROOM", "GC_DATA_ROOT"))
        os.environ["HOME"] = self.root
        os.environ["GC_DATA_ROOT"] = os.path.join(self.root, ".local", "share", "example-data")   # the front room is under it
        os.environ.pop("AGE_FRONT_ROOM", None)

    def close(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.root, ignore_errors=True)

    def delivery(self, tid, mid, **over):
        d = {"schema": "gc.delivery/1", "thread_id": tid, "message_id": mid, "subject": "s", "from": "f",
             "date": "d", "label": "l", "verdict": "safe", "triage": {"needs_me": "no", "deadline": None},
             "seen": "full", "internal_ms": 1000,
             "header": "# thread %s | subject: s\n\n" % tid,
             "block": "=== message %s | d | from: f | label: l ===\nbody of %s\n\n" % (mid, mid)}
        d.update(over)
        return d

    def put(self, doc, raw=None):
        name = "%s.%s.json" % (doc["thread_id"], doc["message_id"])
        with open(os.path.join(self.drop, name), "w", encoding="utf-8") as f:
            f.write(raw if raw is not None else json.dumps(doc))
        return name

    def ingest(self, uid=None):
        return transcripts.ingest(self.drop, mailroom_uid=os.getuid() if uid is None else uid)


class Door(unittest.TestCase):
    def setUp(self):
        self.h = FakeHome()
        self.addCleanup(self.h.close)

    def test_only_files_owned_by_the_mailroom_account_are_filed(self):
        """B4: the owner is checked by the OS uid, not by anything the file says."""
        t, m = "b000001", "a000001"
        self.h.put(self.h.delivery(t, m))
        out = self.h.ingest(uid=os.getuid() + 4242)      # 'the mailroom' is somebody else
        self.assertEqual((out["ingested"], out["refused"]), (0, 1))
        self.assertEqual(transcripts.list_threads(), [])
        self.h.put(self.h.delivery(t, m))
        self.assertEqual(self.h.ingest()["ingested"], 1)

    def test_nobody_known_means_nothing_accepted(self):
        """No mailroom uid and no such account on this machine -> fail closed."""
        self.h.put(self.h.delivery("b000001", "a000001"))
        os.environ["AGE_MAILROOM_USER"] = "no-such-account-xyz"
        self.addCleanup(os.environ.pop, "AGE_MAILROOM_USER", None)
        out = transcripts.ingest(self.h.drop)
        self.assertEqual(out["ingested"], 0)

    def test_hand_written_catalogue_line_is_not_trusted(self):
        """B3b: a catalogue line nobody's ingest wrote cannot make an unscanned block readable."""
        t = "b000001"
        self.h.put(self.h.delivery(t, "a000001"))
        self.h.ingest()
        self.assertIn("body of a000001", transcripts.read_thread(t, TOOLLESS))
        tpath = os.path.join(transcripts.transcripts_dir(), t + ".txt")
        with open(tpath, "a", encoding="utf-8") as f:
            f.write("=== message a0000ff | d | from: f | label: l ===\nsneaked in\n\n")
        with open(transcripts.catalogue_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps({"thread_id": t, "message_id": "a0000ff", "verdict": "safe", "seen": "full"}) + "\n")
        with self.assertRaises(transcripts.Refused):
            transcripts.read_thread(t, TOOLLESS)
        self.assertNotIn("a0000ff", [m["message_id"] for m in transcripts.catalogue_meta()])

    def test_edited_catalogue_line_is_not_trusted(self):
        t = "b000001"
        self.h.put(self.h.delivery(t, "a000001"))
        self.h.ingest()
        p = transcripts.catalogue_path()
        s = open(p, encoding="utf-8").read().replace('"subject": "s"', '"subject": "edited"')
        open(p, "w", encoding="utf-8").write(s)
        with self.assertRaises(transcripts.Refused):
            transcripts.read_thread(t, TOOLLESS)

    def test_edited_block_text_is_not_served(self):
        """The row carries the block's hash: text changed after filing is refused."""
        t = "b000001"
        self.h.put(self.h.delivery(t, "a000001"))
        self.h.ingest()
        tp = os.path.join(transcripts.transcripts_dir(), t + ".txt")
        s = open(tp, encoding="utf-8").read().replace("body of a000001", "body of a000001 PLUS-INJECTED")
        open(tp, "w", encoding="utf-8").write(s)
        with self.assertRaises(transcripts.Refused):
            transcripts.read_thread(t, TOOLLESS)

    def test_header_is_validated_like_the_block(self):
        """B5c."""
        t, m = "b000001", "a000001"
        bad_headers = ["# thread %s | subject: s\n\n=== message %s | d | from: f | label: l ===\nSMUGGLED\n\n" % (t, m),
                       "# thread b0000ee | subject: s\n\n",           # wrong thread id
                       "hello\n\n", "# thread %s | subject: s\n" % t,  # wrong shape
                       "# thread %s | subject: x\n# thread %s | subject: y\n\n" % (t, t)]
        for i, hd in enumerate(bad_headers):
            self.h.put(self.h.delivery(t, "a00000%d" % (i + 1), header=hd,
                                       block="=== message a00000%d | d | from: f | label: l ===\nx\n\n" % (i + 1)))
        out = self.h.ingest()
        self.assertEqual((out["ingested"], out["refused"]), (0, len(bad_headers)))
        self.assertEqual(transcripts.list_threads(), [])

    def test_duplicate_json_keys_refused(self):
        """Same trap as the scanner's answer: first key says one thing, last says another."""
        d = self.h.delivery("b000001", "a000001")
        raw = json.dumps(d)[:-1] + ', "verdict": "attack"}'
        self.h.put(d, raw=raw)
        raw2 = json.dumps(self.h.delivery("b000002", "a000002", verdict="attack"))[:-1] + ', "verdict": "safe"}'
        self.h.put(self.h.delivery("b000002", "a000002"), raw=raw2)
        out = self.h.ingest()
        self.assertEqual((out["ingested"], out["refused"]), (0, 2))

    def test_dates_and_typed_values_parse_strictly(self):
        for i, bad in enumerate(("2026-01-01\n", "2026-13-45", "٢٠٢٦-٠١-٠١", "2026-02-30")):
            self.h.put(self.h.delivery("b00000%d" % (i + 1), "a00000%d" % (i + 1),
                                       triage={"needs_me": "no", "deadline": bad},
                                       header="# thread b00000%d | subject: s\n\n" % (i + 1),
                                       block="=== message a00000%d | d | from: f | label: l ===\nx\n\n" % (i + 1)))
        out = self.h.ingest()
        self.assertEqual((out["ingested"], out["refused"]), (0, 4))
        self.h.put(self.h.delivery("b000009", "a000009", triage={"deadline": "2026-02-28"},
                                   header="# thread b000009 | subject: s\n\n",
                                   block="=== message a000009 | d | from: f | label: l ===\nx\n\n"))
        self.assertEqual(self.h.ingest()["ingested"], 1)

    def test_triage_is_none_only_when_not_read_in_full(self):
        self.h.put(self.h.delivery("b000001", "a000001", triage=None, seen="full"))
        self.h.put(self.h.delivery("b000002", "a000002", triage=None, seen="partial",
                                   header="# thread b000002 | subject: s\n\n",
                                   block="=== message a000002 | d | from: f | label: l ===\nx\n\n"))
        self.h.put(self.h.delivery("b000003", "a000003", triage={"needs_me": "no"}, seen="partial",
                                   header="# thread b000003 | subject: s\n\n",
                                   block="=== message a000003 | d | from: f | label: l ===\nx\n\n"))
        out = self.h.ingest()
        self.assertEqual((out["ingested"], out["refused"]), (1, 2))

    def test_surrogates_and_separators_refused_without_crashing(self):
        """A6b: a bad delivery is refused; the good one behind it is still filed."""
        self.h.put(self.h.delivery("b000001", "a000001", subject="bad \ud800 subject"))
        self.h.put(self.h.delivery("b000002", "a000002", subject="sep   subject",
                                   header="# thread b000002 | subject: s\n\n",
                                   block="=== message a000002 | d | from: f | label: l ===\nx\n\n"))
        self.h.put(self.h.delivery("b000003", "a000003", header="# thread b000003 | subject: s\n\n",
                                   block="=== message a000003 | d | from: f | label: l ===\nfine\n\n"))
        out = self.h.ingest()
        self.assertEqual((out["ingested"], out["refused"]), (1, 2))
        self.assertIn("fine", transcripts.read_thread("b000003", TOOLLESS))

    def test_only_safe_deliveries_are_filed(self):
        """m06: an otherwise perfect delivery with any other verdict is refused."""
        for i, v in enumerate(("attack", "suspicious", "no_outcome", None, "", "SAFE", True)):
            n = "%06x" % (i + 1)
            self.h.put(self.h.delivery("b" + n, "a" + n, verdict=v, header="# thread b%s | subject: s\n\n" % n,
                                       block="=== message a%s | d | from: f | label: l ===\nx\n\n" % n))
        out = self.h.ingest()
        self.assertEqual((out["ingested"], out["refused"]), (0, 7))
        self.assertEqual(transcripts.list_threads(), [])

    def test_i7_a_failed_catalogue_append_is_retried_not_refused(self):
        t = "b000001"
        self.h.put(self.h.delivery(t, "a000001"))
        real = transcripts._append
        state = {"fail": True}

        def flaky(path, text):
            if state["fail"] and path.endswith("catalogue.jsonl"):
                state["fail"] = False
                raise OSError(28, "No space left on device")
            return real(path, text)
        transcripts._append = flaky
        self.addCleanup(setattr, transcripts, "_append", real)
        out = self.h.ingest()
        self.assertEqual((out["ingested"], out["refused"], out["deferred"]), (0, 0, 1))
        self.assertEqual(os.listdir(self.h.drop), ["%s.%s.json" % (t, "a000001")])   # still retryable
        self.assertFalse(os.path.isdir(os.path.join(transcripts.front_room(), "refused")) and
                         os.listdir(os.path.join(transcripts.front_room(), "refused")))
        # a later reply in the same thread arrives; the stuck one is healed first and nothing doubles
        self.h.put(self.h.delivery(t, "a000002", internal_ms=2000,
                                   block="=== message a000002 | d | from: f | label: l ===\nreply\n\n"))
        out = self.h.ingest()
        self.assertEqual((out["ingested"], out["refused"]), (2, 0))
        text = transcripts.read_thread(t, TOOLLESS)
        self.assertEqual(text.count("=== message a000001"), 1)
        self.assertIn("reply", text)

    def test_i8_a_refused_delivery_is_never_silent(self):
        """The front room cannot answer the mailroom, so the refusal is recorded with id and reason, and
        the coverage proof counts it for the status light."""
        import coverage
        self.h.put(self.h.delivery("b000001", "a000001", verdict="attack"))
        self.h.put(self.h.delivery("b000002", "a000002", header="# thread b000009 | subject: s\n\n"))
        self.h.ingest()
        recs = transcripts.refused_records()
        self.assertEqual(sorted((r["message_id"], r["reason"]) for r in recs),
                         [("a000001", "quarantined_or_unscanned"), ("a000002", "bad_delivery")])
        self.assertTrue(all(set(r) == {"ts", "message_id", "thread_id", "reason"} for r in recs))   # no text
        proof = coverage.ingest_proof()
        self.assertEqual(proof["refused_at_ingest"], 2)
        self.assertEqual(proof["light"], "red")
        self.assertIn("2", coverage.ingest_proof_line())
        self.h.ingest()                                   # the record persists across runs
        self.assertEqual(coverage.ingest_proof()["refused_at_ingest"], 2)

    def test_i8b_clean_ingest_is_green(self):
        import coverage
        self.h.put(self.h.delivery("b000001", "a000001"))
        self.h.ingest()
        self.assertEqual(coverage.ingest_proof()["light"], "green")

    def status(self):
        return json.load(open(os.path.join(transcripts.front_room(), "ingest-status.json"), encoding="utf-8"))

    def test_r14_the_status_light_is_red_after_a_refusal_and_green_otherwise(self):
        self.h.put(self.h.delivery("b000001", "a000001"))
        self.h.ingest()
        self.assertEqual(self.status()["light"], "green")
        self.h.put(self.h.delivery("b000002", "a000002", verdict="attack"))
        self.h.ingest()
        st = self.status()
        self.assertEqual((st["light"], st["refused_at_ingest"]), ("red", 1))
        self.assertIn("refused_at_ingest", st["reasons"])

    def test_i7b_an_unreadable_transcript_turns_the_light_red_with_a_named_reason(self):
        t = "b000001"
        self.h.put(self.h.delivery(t, "a000001"))
        self.h.ingest()
        tp = os.path.join(transcripts.transcripts_dir(), t + ".txt")
        with open(tp, "ab") as f:
            f.write(b"\xff\xfe not utf-8 \xff")                 # a disk fault
        self.h.put(self.h.delivery(t, "a000002", internal_ms=2000,
                                   block="=== message a000002 | d | from: f | label: l ===\nreply\n\n"))
        out = self.h.ingest()
        self.assertEqual((out["ingested"], out["deferred"]), (0, 1))
        st = self.status()
        self.assertEqual(st["light"], "red")
        self.assertIn("transcript_unreadable", st["reasons"])
        self.assertEqual(len(os.listdir(self.h.drop)), 1)           # kept, not lost
        self.h.ingest()                                              # and it stays red on every run
        self.assertEqual(self.status()["light"], "red")

    def test_f6c_an_empty_key_file_recovers_when_nothing_depends_on_it_and_is_loud_otherwise(self):
        os.makedirs(transcripts.catalogue_dir())
        open(os.path.join(transcripts.catalogue_dir(), ".ledger-key"), "w", encoding="utf-8").close()   # crash at first ingest
        self.h.put(self.h.delivery("b000001", "a000001"))
        self.assertEqual(self.h.ingest()["ingested"], 1)
        self.assertIn("body of a000001", transcripts.read_thread("b000001", TOOLLESS))
        for junk in (b"", b"not a key at all"):                       # now a catalogue exists
            with open(os.path.join(transcripts.catalogue_dir(), ".ledger-key"), "wb") as f:
                f.write(junk)
            self.h.put(self.h.delivery("b000002", "a000002", header="# thread b000002 | subject: s\n\n",
                                       block="=== message a000002 | d | from: f | label: l ===\nx\n\n"))
            with self.assertRaises(transcripts.LedgerKeyLost):
                self.h.ingest()
            st = self.status()
            self.assertEqual(st["light"], "red")
            self.assertIn("ledger_key_lost", st["reasons"])

    def test_f6d_a_missing_catalogue_with_a_key_is_loud(self):
        t = "b000001"
        self.h.put(self.h.delivery(t, "a000001"))
        self.h.ingest()
        os.unlink(transcripts.catalogue_path())
        self.h.put(self.h.delivery("b000002", "a000002", header="# thread b000002 | subject: s\n\n",
                                   block="=== message a000002 | d | from: f | label: l ===\nx\n\n"))
        with self.assertRaises(transcripts.CatalogueMissing):
            self.h.ingest()
        self.assertIn("catalogue_missing", self.status()["reasons"])
        with self.assertRaises(transcripts.CatalogueMissing):
            transcripts.read_thread(t, TOOLLESS)

    def test_f6_a_missing_ledger_key_is_loud_and_is_never_replaced(self):
        t = "b000001"
        self.h.put(self.h.delivery(t, "a000001"))
        self.h.ingest()
        os.unlink(os.path.join(transcripts.catalogue_dir(), ".ledger-key"))
        self.h.put(self.h.delivery("b000002", "a000002", header="# thread b000002 | subject: s\n\n",
                                   block="=== message a000002 | d | from: f | label: l ===\nx\n\n"))
        with self.assertRaises(transcripts.LedgerKeyLost):
            self.h.ingest()
        self.assertFalse(os.path.exists(os.path.join(transcripts.catalogue_dir(), ".ledger-key")))
        with self.assertRaises(transcripts.LedgerKeyLost):
            transcripts.read_thread(t, TOOLLESS)

    def test_ingest_is_single_instance(self):
        """K1: a second ingest while one runs does nothing and says so."""
        self.h.put(self.h.delivery("b000001", "a000001"))
        os.makedirs(transcripts.front_room(), exist_ok=True)
        fd = os.open(os.path.join(transcripts.front_room(), "ingest.lock"), os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            out = self.h.ingest()
        finally:
            os.close(fd)
        self.assertEqual(out.get("skipped"), "another_ingest_running")
        self.assertEqual((out["ingested"], transcripts.list_threads()), (0, []))
        self.assertEqual(self.h.ingest()["ingested"], 1)

    def test_blocks_are_filed_in_message_date_order(self):
        t = "b000001"
        self.h.put(self.h.delivery(t, "a000002", internal_ms=2000,
                                   block="=== message a000002 | d | from: f | label: l ===\nSECOND\n\n"))
        self.h.ingest()
        self.h.put(self.h.delivery(t, "a000001", internal_ms=1000,
                                   block="=== message a000001 | d | from: f | label: l ===\nFIRST\n\n"))
        self.h.ingest()
        text = transcripts.read_thread(t, TOOLLESS)
        self.assertLess(text.index("FIRST"), text.index("SECOND"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
