#!/usr/bin/env python3
"""Step 1.7 finish tests: the quarantine review command, held_oldest_age_s, and the 16-vs-40 explanation.
SYNTHETIC mail only: fake Gmail, stub scanner, temp folders, no network, no model, no live register.

Run:  python3 -I -B reader/tests/test_step7_review.py        (from shared/grand_central/)

"Shown failing first": each finish case is a CHECK function. It runs first against a NAIVE stand-in
(the obvious first version) and must FAIL; only then does it run against the real code and must pass.
The stand-ins live in this file only.
"""
import json
import os
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from reader import flatten, readerd, review  # noqa: E402  (import the package first: it fixes which reader/ is used)
for p in (HERE, os.path.join(ROOT, "reader", "tests"), os.environ.get("GC_RIG_TESTS", HERE)):
    if p not in sys.path:
        sys.path.append(p)
import test_step2_attack as att  # noqa: E402
from fakes import FakeGmail, FakeScanner, SAFE, hid, NOW_MS  # noqa: E402
from test_step2_intake import have_sentinel_sources  # noqa: E402
import transcripts  # noqa: E402

SHOW = os.environ.get("PRINT_PLANTED") == "1"
NAIVE_FAILS = []


def must_fail(name, check, *args):
    """The check must raise AssertionError on the naive stand-in, or it cannot catch anything."""
    try:
        check(*args)
    except AssertionError as e:
        NAIVE_FAILS.append(name)
        if SHOW:
            print("  planted case caught: %s: %s" % (name, e))
        return
    raise AssertionError("PLANTED CASE NOT CAUGHT: %s" % name)


class Script(object):
    """Scripted keystrokes for the interactive review; collects what it printed."""
    def __init__(self, *answers):
        self.answers, self.lines = list(answers), []

    def inp(self, prompt):
        self.lines.append("PROMPT " + prompt)
        if not self.answers:
            raise EOFError
        return self.answers.pop(0)

    def out(self, s=""):
        self.lines.append(s)

    @property
    def text(self):
        return "\n".join(self.lines)


class SafeScanner(FakeScanner):
    """A scanner that changes its mind: says safe about everything (the second look finds nothing)."""
    def scan(self, prompt):
        self.calls += 1
        return json.dumps(SAFE), None


class DownScanner(FakeScanner):
    def scan(self, prompt):
        return None, "timeout"


# ------------------------------------------------------------------ naive stand-ins
def naive_rescan_stamps_safe(rec, scanner, sentinel):      # no second scan: hand-stamped
    return {"status": "ok", "verdict": "safe", "triage": None, "partial": True}, "", "safe"

def naive_clean(text, limit=None):          # shows the text as it arrived: escape codes and all
    t = text if isinstance(text, str) else str(text)
    return t if limit is None else t[:limit]


def naive_release_flips_register_only(register, deliveries_dir, qdir, mid, res=None, t_ms=None):
    register.mark(mid, "delivered", reason="released_by_review", t=t_ms)     # nothing is delivered
    return "released"


def naive_release_keeps_verdict(register, deliveries_dir, qdir, mid, res=None, t_ms=None):
    rec = review.read_quarantine_file(qdir, mid)
    row = register.get(mid)
    readerd.deliver(deliveries_dir, row, rec["email"], {"verdict": row["verdict"], "triage": None}, partial=True)
    register.mark(mid, "delivered", reason="released_by_review", t=t_ms)
    return "released"


def naive_oldest_over_all_held(self, t_ms):    # counts parked rows too
    r = self.db.execute("SELECT MIN(first_seen_ms) FROM messages WHERE status='held'").fetchone()
    return None if r[0] is None else max(0, int((t_ms - r[0]) // 1000))


@unittest.skipUnless(have_sentinel_sources(), "plugin Sentinel files not found (SKIPPED, not passed)")
class Step7(unittest.TestCase):
    def sysm(self):
        s = att.Sys()
        self.addCleanup(s.close)
        return s

    def quarantine_one(self, s, n=1, body="SUSPICIOUS-ONE please look \x1b[2J‮ at this"):
        s.gmail.add(hid("b", n), hid("a", n), body, NOW_MS - 50, frm="Pat Sender <pat@example.invalid>",
                    subject="Synthetic subject %d" % n)
        s.run()
        self.assertIn(hid("a", n), s.quarantined())
        return hid("a", n)

    # ---- (a) release really delivers, and the front room files it
    def check_release_reaches_front_room(self, s, mid, release_fn):
        rec = review.read_quarantine_file(s.quar, mid)
        scan, why, _v = review.rescan(rec, SafeScanner(), s.sentinel)
        assert scan is not None, "rescan said no: %s" % why
        res = release_fn(s.register, s.deliveries, s.quar, mid, scan)
        assert res == "released", "release said %r" % res
        assert s.register.get(mid)["status"] == "delivered", "register not delivered"
        out = transcripts.ingest(s.deliveries, mailroom_uid=os.getuid())
        assert out["ingested"] == 1 and out["refused"] == 0, "front room did not file it: %r" % out
        assert mid in set(r["message_id"] for r in transcripts.catalogue_meta()), "not in the catalogue"

    def test_release_delivers_and_ingest_files_it(self):
        for name, fn in (("naive: register flipped, nothing delivered", naive_release_flips_register_only),
                         ("naive: delivered with the scanner's flagged verdict", naive_release_keeps_verdict)):
            s = self.sysm()
            mid = self.quarantine_one(s)
            must_fail(name, self.check_release_reaches_front_room, s, mid, fn)
        s = self.sysm()
        mid = self.quarantine_one(s)
        self.check_release_reaches_front_room(s, mid, review.release)
        row = s.register.get(mid)
        self.assertEqual((row["status"], row["reason"], row["verdict"]), ("delivered", "released_by_review", "safe"))   # the NEW verdict
        self.assertIn(mid, s.quarantined())             # the quarantined copy is left, never deleted

    # ---- (b) nothing a message contains can write to his Terminal
    def check_screen_is_clean(self, clean_fn):
        saved = review.clean
        review.clean = clean_fn
        try:
            s = self.sysm()
            mid = self.quarantine_one(s)
            path = os.path.join(s.quar, mid + ".json")       # the door already strips these; plant them
            with open(path, encoding="utf-8") as f:                             # in the saved file anyway (defence in depth)
                d = json.load(f)
            d["email"]["body"] += "\nplease look \x1b[2J\u202e at this"
            d["email"]["subject"] += " \x1b]0;pwned\x07"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(d, f)
            sc = Script("q")
            review.review(s.register, s.deliveries, s.quar, False, sc.inp, sc.out)
        finally:
            review.clean = saved
        for bad in ("\x1b", "‮"):
            assert bad not in sc.text, "screen carries %r" % bad
        assert "Synthetic subject 1" in sc.text and "please look" in sc.text, "the message was not shown"

    def test_screen_text_has_controls_removed(self):
        must_fail("naive: text shown as it arrived (escape code and bidi reach the screen)", self.check_screen_is_clean, naive_clean)
        self.check_screen_is_clean(review.clean)

    # ---- (c) interactive flow: confirm word, keep, skip, quit, --all
    def test_interactive_keys(self):
        s = self.sysm()
        ids = [self.quarantine_one(s, n, body="SUSPICIOUS-ONE note %d" % n) for n in (1, 2, 3, 4)]
        sc = Script("x",                 # not a key: asked again
                    "k",                 # keep #1
                    "s",                 # skip #2
                    "r",                 # release #3 (a fresh scan decides; this scanner passes it)
                    "q")                 # quit before #4
        c = review.review(s.register, s.deliveries, s.quar, False, sc.inp, sc.out,
                          lambda: (SafeScanner(), s.sentinel))
        self.assertEqual(c, {"released": 1, "kept": 1, "skipped": 1, "left": 1, "errors": 0, "still_held": 0})
        self.assertEqual(s.register.get(ids[0])["reason"], "kept_by_review")
        self.assertEqual(s.register.get(ids[0])["status"], "quarantined")
        self.assertEqual(s.register.get(ids[2])["status"], "delivered")
        self.assertEqual(s.register.get(ids[1])["reason"], None)                 # skipped: untouched
        self.assertEqual(s.register.get(ids[3])["reason"], None)
        again = review.pending(s.register, False)
        self.assertEqual([r["id"] for r in again], [ids[1], ids[3]])             # kept and released are not asked again
        self.assertEqual([r["id"] for r in review.pending(s.register, True)], [ids[0], ids[1], ids[3]])
        sc2 = Script()                                                           # end of input = quit
        c2 = review.review(s.register, s.deliveries, s.quar, False, sc2.inp, sc2.out)
        self.assertEqual((c2["released"], c2["kept"], c2["left"]), (0, 0, 2))

    # ---- (d) a bad file is never released; ids are checked
    def test_missing_or_forged_files_are_never_released(self):
        s = self.sysm()
        mid = self.quarantine_one(s)
        os.rename(os.path.join(s.quar, mid + ".json"), os.path.join(s.quar, "moved"))
        okres = {"status": "ok", "verdict": "safe", "triage": None, "partial": True}
        self.assertEqual(review.release(s.register, s.deliveries, s.quar, mid, okres), "no_file")
        self.assertEqual(s.register.get(mid)["status"], "quarantined")
        os.symlink("/etc/hosts", os.path.join(s.quar, mid + ".json"))            # a link is refused
        self.assertIsNone(review.read_quarantine_file(s.quar, mid))
        os.unlink(os.path.join(s.quar, mid + ".json"))
        os.rename(os.path.join(s.quar, "moved"), os.path.join(s.quar, mid + ".json"))
        other = hid("a", 9)
        self.assertIsNone(review.read_quarantine_file(s.quar, "../" + mid))      # not an id
        self.assertIsNone(review.read_quarantine_file(s.quar, other))            # no such file
        with open(os.path.join(s.quar, other + ".json"), "w", encoding="utf-8") as f:              # file for another id
            json.dump({"message_id": mid, "email": {"message_id": mid}}, f)
        self.assertIsNone(review.read_quarantine_file(s.quar, other))
        self.assertEqual(review.release(s.register, s.deliveries, s.quar, hid("a", 77), okres), "not_quarantined")
        self.assertEqual(os.listdir(s.deliveries) if os.path.isdir(s.deliveries) else [], [])

    def test_a_delivered_message_cannot_be_released_twice(self):
        s = self.sysm()
        mid = self.quarantine_one(s)
        scan, _w, _v = review.rescan(review.read_quarantine_file(s.quar, mid), SafeScanner(), s.sentinel)
        self.assertEqual(review.release(s.register, s.deliveries, s.quar, mid, scan), "released")
        self.assertEqual(review.release(s.register, s.deliveries, s.quar, mid, scan), "not_quarantined")

    # ---- (g) Vision 3.1: a released message is scanned again; no override
    def check_flagged_rescan_stays_held(self, rescan_fn, scanner):
        saved = review.rescan
        review.rescan = rescan_fn
        try:
            s = self.sysm()
            mid = self.quarantine_one(s)
            sc = Script("r")
            c = review.review(s.register, s.deliveries, s.quar, False, sc.inp, sc.out, lambda: (scanner, s.sentinel))
        finally:
            review.rescan = saved
        assert s.register.get(mid)["status"] == "quarantined", "a message the scanner still flags was delivered"
        assert not os.path.isdir(s.deliveries) or os.listdir(s.deliveries) == [], "a file was delivered"
        assert c["still_held"] == 1 and "stays quarantined" in sc.text, "he was not told it stays held"
        return sc.text

    def test_release_is_scanned_again_and_cannot_override(self):
        must_fail("naive: release hand-stamps safe, no second scan", self.check_flagged_rescan_stays_held,
                  naive_rescan_stamps_safe, FakeScanner())
        txt = self.check_flagged_rescan_stays_held(review.rescan, FakeScanner())      # still flags: suspicious
        self.assertIn("looks suspicious", txt)
        self.check_flagged_rescan_stays_held(review.rescan, DownScanner())            # scanner error: stays held
        self.assertIn("could not run", self.check_flagged_rescan_stays_held(review.rescan, DownScanner()))

    def test_released_message_carries_the_new_scan_not_a_stamp(self):
        s = self.sysm()
        mid = self.quarantine_one(s)
        sc = Script("r")
        review.review(s.register, s.deliveries, s.quar, False, sc.inp, sc.out, lambda: (SafeScanner(), s.sentinel))
        name = [n for n in os.listdir(s.deliveries) if n.endswith(".json")][0]
        with open(os.path.join(s.deliveries, name), encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(d["verdict"], "safe")
        self.assertEqual(d["seen"], "full")                                           # a real triage came with it
        self.assertEqual(d["triage"]["needs_me"], "cant_tell")

    # ---- (h) the batch: --rescan-all (step 1.8)
    def batch(self, s, scanner):
        sc = Script()
        c = review.rescan_all(s.register, s.deliveries, s.quar, False, lambda: (scanner, s.sentinel), sc.out)
        return c, sc.text

    def test_batch_clean_rescan_is_delivered_and_filed(self):
        s = self.sysm()
        ids = [self.quarantine_one(s, n, body="SUSPICIOUS-ONE note %d" % n) for n in (1, 2)]
        c, txt = self.batch(s, SafeScanner())
        self.assertEqual((c["scanned"], c["released"], c["still_held"]), (2, 2, 0))
        for mid in ids:
            row = s.register.get(mid)
            self.assertEqual((row["status"], row["verdict"], row["reason"]), ("delivered", "safe", "released_by_review"))
        out = transcripts.ingest(s.deliveries, mailroom_uid=os.getuid())
        self.assertEqual((out["ingested"], out["refused"]), (2, 0))                  # the front room accepts what the new scan passed

    def check_batch_holds(self, scanner, rescan_fn=None):
        saved = review.rescan
        if rescan_fn:
            review.rescan = rescan_fn
        try:
            s = self.sysm()
            mid = self.quarantine_one(s)
            c, txt = self.batch(s, scanner)
        finally:
            review.rescan = saved
        assert s.register.get(mid)["status"] == "quarantined", "flagged or unscanned message was delivered"
        assert not os.path.isdir(s.deliveries) or os.listdir(s.deliveries) == [], "a file was delivered"
        assert c["released"] == 0 and c["still_held"] == 1, c
        return s, mid, txt

    def test_batch_flagged_rescan_is_held_with_the_new_verdict(self):
        must_fail("naive: batch hand-stamps safe, no second scan", self.check_batch_holds, FakeScanner(), naive_rescan_stamps_safe)
        s, mid, txt = self.check_batch_holds(FakeScanner())
        self.assertIn("looks suspicious", txt)
        self.assertIn("Synthetic subject 1", txt)                                     # envelope facts are listed
        self.assertEqual(s.register.get(mid)["reason"], "rescanned_flagged")
        # asked again by the interactive mode; not rescanned again by a second batch
        self.assertEqual([r["id"] for r in review.pending(s.register, False)], [mid])
        c2, _ = self.batch(s, SafeScanner())
        self.assertEqual(c2["scanned"], 0)

    def test_batch_scan_error_is_held_and_changes_nothing(self):
        s, mid, txt = self.check_batch_holds(DownScanner())
        self.assertIn("could not run", txt)
        self.assertIsNone(s.register.get(mid)["reason"])                              # untouched: the next batch tries again
        self.assertEqual(s.register.get(mid)["verdict"], "suspicious")

    def test_batch_prints_no_body_text(self):
        s = self.sysm()
        self.quarantine_one(s, 1, body="SUSPICIOUS-ONE BODY-SECRET-PLANTED-1")
        self.quarantine_one(s, 2, body="SUSPICIOUS-ONE BODY-SECRET-PLANTED-2")
        c, txt = self.batch(s, FakeScanner())
        self.assertNotIn("BODY-SECRET", txt)
        self.assertIn("Synthetic subject 2", txt)
        c, txt2 = self.batch(s, SafeScanner())                                        # (rescanned rows are skipped)
        s2 = self.sysm()
        self.quarantine_one(s2, 1, body="SUSPICIOUS-ONE BODY-SECRET-PLANTED-3")
        c, txt3 = self.batch(s2, SafeScanner())
        self.assertNotIn("BODY-SECRET", txt3)

    def test_main_batch_end_to_end_prints_done_line(self):
        # the real command line, with the real PinnedSentinel but a stub scanner swapped in at the one seam
        s = self.sysm()
        mid = self.quarantine_one(s)
        home = os.path.dirname(s.quar)
        cfg = dict(att.CFG, sentinel_dir=s.sdir, sentinel_sha256=s.hashes)
        cpath = os.path.join(home, "cfg.json")
        with open(cpath, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        saved = review.screen.ClaudeScanner
        review.screen.ClaudeScanner = lambda *a, **k: SafeScanner()
        sc = Script()
        try:
            rc = review.main(["--rescan-all", "--home", home, "--drop", os.path.dirname(s.deliveries), "--expect-user", "",
                              "--config", cpath, "--test-allow-nonroot-config"], inp=sc.inp, out=sc.out)
        finally:
            review.screen.ClaudeScanner = saved
        self.assertEqual(rc, 0)
        self.assertIn("DONE: 1 scanned, 1 released", sc.text)
        self.assertEqual(s.register.get(mid)["status"], "delivered")

    # ---- (e) the lock: a review never writes while a pass holds the register
    def test_busy_register_means_nothing_changes(self):
        s = self.sysm()
        mid = self.quarantine_one(s)
        fd = readerd._lock(s.register.lock_path)
        self.addCleanup(lambda: os.close(fd) if fd is not None else None)
        res = review._locked(s.register, lambda: review.keep(s.register, mid), lambda *_: None, tries=2, wait=0.01)
        self.assertIsNone(res)
        self.assertIsNone(s.register.get(mid)["reason"])
        out = readerd.run_pass(s.gmail, s.scanner, s.sentinel, s.register, s.deliveries, s.quar, s.cfg,
                               today=att.TODAY, t_ms=NOW_MS)
        self.assertEqual(out.get("skipped"), "another_pass_running")             # (the daemon then leaves the facts file alone)

    # ---- (f) the pass file: held_oldest_age_s, and how 16 and 40 add up
    def check_oldest_age(self, s, expect, patch=None):
        saved = readerd.Register.held_oldest_age_s
        if patch:
            readerd.Register.held_oldest_age_s = patch
        try:
            out = s.run()
        finally:
            readerd.Register.held_oldest_age_s = saved
        assert out["held_oldest_age_s"] == expect, "held_oldest_age_s=%r, expected %r" % (out["held_oldest_age_s"], expect)
        return out

    def test_held_oldest_age_s(self):
        s = self.sysm()
        out = self.check_oldest_age(s, None)                                      # nothing held: null, not 0
        # a message waiting for the scanner for 2 hours, and a parked one 5 days old
        s.register.add_message("a0000a1", "b0000a1", "L", NOW_MS - 7200 * 1000)
        s.register.mark("a0000a1", "held", reason="scanner_unavailable", t=NOW_MS - 7200 * 1000)
        s.register.add_message("a0000a2", "b0000a2", "L", NOW_MS - 5 * 86400 * 1000)
        s.register.mark("a0000a2", "held", reason="excluded_label", t=NOW_MS)
        s.register.add_message("a0000a3", "b0000a3", "L", NOW_MS - 6 * 86400 * 1000)
        s.register.mark("a0000a3", "held", reason="not_in_read_label", t=NOW_MS)
        s.gmail.down = True                                                       # the pass cannot fetch: the waiting one stays held
        must_fail("naive: parked rows counted (a permanent RED light)", self.check_oldest_age, s, 7200, naive_oldest_over_all_held)
        out = self.check_oldest_age(s, 7200)
        self.assertEqual(out["held_parked"], 2)

    def test_held_oldest_age_s_in_the_pass_file_is_an_int_or_null(self):
        s = self.sysm()
        s.gmail.add(hid("b", 1), hid("a", 1), "GARBLE-ME x", NOW_MS - 1000)       # held, scan_invalid
        out = s.run()
        self.assertIsInstance(out["held_oldest_age_s"], int)
        self.assertGreaterEqual(out["held_oldest_age_s"], 0)
        self.assertIsNone(json.loads(json.dumps(self.sysm().run()))["held_oldest_age_s"])

    def test_sixteen_and_forty_add_up(self):
        """held_after counts only status 'held'; the list (held_messages) holds held AND quarantined."""
        s = self.sysm()
        for i in range(1, 25):
            mid = "a%06x" % i
            s.register.add_message(mid, "b%06x" % i, "L", NOW_MS - i)
            s.register.mark(mid, "quarantined", verdict="suspicious", t=NOW_MS - i)
        for i in range(25, 39):
            mid = "a%06x" % i
            s.register.add_message(mid, "b%06x" % i, "L", NOW_MS - i)
            s.register.mark(mid, "held", reason="not_in_read_label", t=NOW_MS)
        for i in range(39, 41):
            mid = "a%06x" % i
            s.register.add_message(mid, "b%06x" % i, "L", NOW_MS - i)
            s.register.mark(mid, "held", reason="excluded_label", t=NOW_MS)
        out = s.run()
        self.assertEqual((out["held_after"], out["quarantined_total"], out["held_messages_total"]), (16, 24, 40))
        self.assertEqual(len(out["held_messages"]), 40)
        self.assertEqual(out["held_parked"], 16)
        self.assertEqual(out["held_after"] + out["quarantined_total"], out["held_messages_total"])
        self.assertIsNone(out["held_oldest_age_s"])                               # all 16 are parked: nothing is waiting

    def test_the_new_fields_carry_no_text(self):
        s = self.sysm()
        self.quarantine_one(s, 1, body="SUSPICIOUS-ONE SECRET-BODY")
        blob = json.dumps(s.run())
        for forbidden in ("SECRET", "pat@example", "Synthetic subject"):
            self.assertNotIn(forbidden, blob)

    def test_list_shows_envelope_not_text(self):
        s = self.sysm()
        mid = self.quarantine_one(s, 1, body="SUSPICIOUS-ONE SECRET-BODY")
        line = review.summary_line(review.pending(s.register, True)[0], review.read_quarantine_file(s.quar, mid))
        self.assertIn("Synthetic subject 1", line)
        self.assertNotIn("SECRET-BODY", line)


if __name__ == "__main__":
    unittest.main(verbosity=1)
