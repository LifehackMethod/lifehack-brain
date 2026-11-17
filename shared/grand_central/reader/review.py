#!/usr/bin/env python3
"""reader/review.py - the person's review of the mailroom's quarantine (step 1.7 and 1.8).

The mailroom puts every message that is not "safe" in its quarantine folder and marks it
"quarantined" in the register. This is the way back out, and it never lets anything past the scanner:

  RELEASE = SCAN AGAIN. A message he releases (or that the batch mode takes) is scanned a second time by
  the mailroom's own scanner and pinned Sentinel, the same path readerd uses (Vision 3.1: "released after
  a fresh scan; anything still suspicious goes to the person"). Clean -> delivered through the usual
  one-way slot carrying the NEW verdict and triage (register: "delivered", reason "released_by_review").
  Still flagged, or the scan cannot run or fails -> it stays quarantined, the row records the new verdict
  (reason "rescanned_flagged"; a scan that could not run changes nothing) and he is told in plain words.
  There is NO override: nothing here can deliver a message the scanner does not pass.

It runs ONLY as the mailroom account, by his hand, in his own Terminal (the quarantine is readable by
that account and root only):
    cd / && sudo -u <mailroom-user> <apple-python3> -I -B <install-dir>/reader/review.py [options]
(<apple-python3> is Apple's python3, in /usr/bin, named by its full path on purpose: root-owned code running as the mailroom account must
not take python3 from a PATH someone else controls. His password is the sudo password; the mailroom
account has none. The code is root-owned like the rest of the mailroom, so it cannot change it.)

  review.py --rescan-all   BATCH: scan every quarantined message again once (those not already rescanned or
                           kept), release the clean ones, leave the rest. Prints envelope facts only
                           (sender, subject, date, new verdict in words): never any message text.
  review.py                go through the quarantined messages not yet kept, one at a time, showing the
                           text; r = release (a fresh scan decides), k = keep, s = skip, m = more, q = quit
  review.py --all          also the ones he already chose to keep
  review.py list           one line per message (sender, subject, date, why held); no message text

What it writes, and only this: for a clean rescan, one file in deliveries/ (readerd.deliver()) and the
register mark; for a flagged rescan or a keep, the register mark. The quarantined copy is never deleted.
Every write is made while holding the register's own lock (the same one a pass takes), only for the moment
of the write; the scan itself runs outside the lock. A pass that finds the lock held does nothing and the
next pass (10 minutes later) does the work.

Everything shown on screen has control characters removed (an email cannot move his cursor or write to
his Terminal). Message text is shown only in the interactive mode, on his own screen: it is never logged,
never put on a command line, and never written anywhere (the delivery file of a message that passed the
scan is the one exception, the usual one-way slot).
Python 3.9 compatible (Apple's python).
"""
import argparse
import json
import os
import pwd
import re
import stat
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from reader import flatten, readerd, screen  # noqa: E402

ID_RE = re.compile(r"^[0-9a-f]{6,32}$")
MAX_FILE_BYTES = 8 * 1024 * 1024
PREVIEW_CHARS = 2000
KEPT = "kept_by_review"
RESCANNED = "rescanned_flagged"
RELEASED = "released_by_review"


def clean(text, limit=None):
    """Text for his screen: control and invisible characters removed, line ends normalised."""
    t = flatten.normalise_body(text if isinstance(text, str) else str(text))
    return t if limit is None else t[:limit]


def read_quarantine_file(qdir, mid):
    """-> the saved record, or None if it is missing or not a plain, sane file for exactly this id.
    Never follows a link; never trusts a name."""
    if not ID_RE.match(mid):
        return None
    path = os.path.join(qdir, mid + ".json")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        return None
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_FILE_BYTES:
            return None
        raw = b""
        while True:
            chunk = os.read(fd, 1 << 20)
            if not chunk:
                break
            raw += chunk
    finally:
        os.close(fd)
    try:
        d = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, RecursionError):
        return None
    if not isinstance(d, dict) or d.get("message_id") != mid or not isinstance(d.get("email"), dict) \
            or d["email"].get("message_id") != mid:
        return None
    return d


def pending(register, include_kept):
    """The quarantined rows to look at, oldest first."""
    rows = register.db.execute(
        "SELECT id,thread_id,label,verdict,reason FROM messages WHERE status='quarantined' "
        "ORDER BY first_seen_ms, id").fetchall()
    out = []
    for mid, tid, label, verdict, reason in rows:
        if reason == KEPT and not include_kept:
            continue
        out.append({"id": mid, "thread_id": tid, "label": label, "verdict": verdict, "reason": reason})
    return out


def _sender(e):
    if e.get("from_name"):
        return "%s <%s>" % (e["from_name"], e.get("from_addr", ""))
    return e.get("from_addr", "") or "?"


def summary_line(row, rec):
    e = (rec or {}).get("email", {})
    tag = (" [kept]" if row["reason"] == KEPT else "") + ("" if rec else " [file missing]")
    return "%s  held as: %-10s  from: %s | subject: %s | date: %s%s" % (
        row["id"], row["verdict"] or "?", clean(_sender(e), 80).replace("\n", " "),
        clean(e.get("subject", "") or "(none)", 90).replace("\n", " "),
        clean(e.get("date", "") or "?", 40).replace("\n", " "), tag)


def _locked(register, fn, out, tries=5, wait=2.0):
    """Run fn() holding the register's lock. A pass holding it: wait a little, then give up."""
    for _i in range(tries):
        fd = readerd._lock(register.lock_path)
        if fd is not None:
            try:
                return fn()
            finally:
                os.close(fd)
        out("  (the mailroom is in the middle of a pass; waiting a moment)")
        time.sleep(wait)
    return None


PLAIN = {"attack": "it looks like an attempt to give the AI orders",
         "suspicious": "it looks suspicious",
         "no_outcome": "the scanner could not reach a clear answer about it"}


def rescan(rec, scanner, sentinel):
    """Scan a quarantined message again, exactly as the pass does (normalise first, pinned Sentinel
    proof required). -> (res or None, plain_reason, new_verdict or None). res is returned ONLY if the
    scanner and the pinned Sentinel both passed it as safe; new_verdict is set when a real scan flagged it."""
    try:
        email = flatten.normalise_email(rec["email"])
        res = screen.scan_email(email, scanner, sentinel)
    except (screen.ScannerNotToolLess, screen.SentinelNotPinned):
        return None, "the scanner is not set up safely right now, so it stays held", None
    except Exception:
        return None, "the scan failed, so it stays held", None
    if res.get("status") == "ok" and not screen.has_sentinel_proof(res, sentinel):
        return None, "the scan could not be proven, so it stays held", None
    if res.get("status") != "ok":
        return None, "the scanner could not run (%s), so it stays held" % (res.get("reason") or "no answer"), None
    if res["verdict"] != "safe":
        return None, "the scanner still flags it: %s. It stays held" % PLAIN.get(res["verdict"], "it is flagged"), res["verdict"]
    return res, "", "safe"


def release(register, deliveries_dir, qdir, mid, res, t_ms=None):
    """Deliver one quarantined message whose NEW scan (res, from rescan()) said safe. Call it holding
    the register lock. -> "released" or a closed code. Delivers what the new scan decided; never a
    hand-stamped verdict."""
    row = register.get(mid)
    if not row or row["status"] != "quarantined":
        return "not_quarantined"
    if not isinstance(res, dict) or res.get("verdict") != "safe" or res.get("status") != "ok":
        return "not_scanned_safe"
    rec = read_quarantine_file(qdir, mid)
    if rec is None:
        return "no_file"
    email = flatten.normalise_email(rec["email"])
    readerd.deliver(deliveries_dir, row, email, {"verdict": res["verdict"], "triage": res["triage"]},
                    partial=bool(res.get("partial")))
    register.mark(mid, "delivered", verdict=res["verdict"], reason=RELEASED, t=t_ms)
    return "released"


def keep(register, mid, t_ms=None):
    row = register.get(mid)
    if not row or row["status"] != "quarantined":
        return "not_quarantined"
    register.mark(mid, "quarantined", reason=KEPT, t=t_ms)
    return "kept"


def try_release(register, deliveries_dir, qdir, row, rec, get_scan, out):
    """The one release path (interactive and batch): scan again, deliver only if clean.
    -> ("released", "") | ("held", plain reason, new_verdict or None) | ("error", code)."""
    if rec is None:
        return ("error", "the saved copy is missing")
    try:
        scanner, sentinel = get_scan()
        res, why, verdict = rescan(rec, scanner, sentinel)
    except Exception:
        res, why, verdict = None, "the scanner could not be set up, so it stays held", None
    if res is None:
        if verdict:      # a real scan flagged it again: remember the new verdict (nothing else changes)
            _locked(register, lambda: register.mark(row["id"], "quarantined", verdict=verdict, reason=RESCANNED), out)
        return ("held", why, verdict)
    done = _locked(register, lambda: release(register, deliveries_dir, qdir, row["id"], res), out)
    if done == "released":
        return ("released", "")
    return ("error", done or "mailroom busy")


def rescan_all(register, deliveries_dir, qdir, include_done, get_scan, out):
    """BATCH: one fresh scan of each quarantined message; release the clean ones. Prints envelope
    facts only. -> counts."""
    rows = [r for r in pending(register, include_done) if include_done or r["reason"] != RESCANNED]
    counts = {"scanned": 0, "released": 0, "still_held": 0, "errors": 0}
    flagged = []
    out("Scanning %d quarantined message(s) again, one at a time (a minute or so each at most)." % len(rows))
    for i, row in enumerate(rows, 1):
        rec = read_quarantine_file(qdir, row["id"])
        r = try_release(register, deliveries_dir, qdir, row, rec, get_scan, out)
        counts["scanned"] += 1
        if r[0] == "released":
            counts["released"] += 1
        elif r[0] == "held":
            counts["still_held"] += 1
            flagged.append((row, rec, r[1], r[2]))
        else:
            counts["errors"] += 1
            flagged.append((row, rec, "could not be handled: " + r[1], None))
        out("  %d of %d scanned" % (i, len(rows)))
    if flagged:
        out("")
        out("STILL HELD (for you to look at; envelope facts only, no message text):")
        for row, rec, why, verdict in flagged:
            e = (rec or {}).get("email", {})
            out("  %s | from: %s | subject: %s | date: %s" % (
                row["id"], clean(_sender(e), 80).replace("\n", " "),
                clean(e.get("subject", "") or "(none)", 90).replace("\n", " "),
                clean(e.get("date", "") or "?", 40).replace("\n", " ")))
            out("      now: %s" % why)
    return counts


def show(row, rec, n, total, full, out):
    e = rec["email"] if rec else {}
    body = clean(e.get("body", "") or "")
    out("")
    out("=" * 78)
    out("[%d of %d]  id %s   held as: %s" % (n, total, row["id"], row["verdict"] or "?"))
    out("From:    %s" % clean(_sender(e), 200).replace("\n", " "))
    out("Subject: %s" % clean(e.get("subject", "") or "(none)", 300).replace("\n", " "))
    out("Date:    %s" % clean(e.get("date", "") or "?", 80).replace("\n", " "))
    if not rec:
        out("(the saved copy of this message is missing or unreadable; you can keep or skip it)")
        return
    shown = body if full else body[:PREVIEW_CHARS]
    out("-" * 30 + " message text, as it arrived " + "-" * 19)
    out(shown)
    if len(shown) < len(body):
        out("... [%d more characters; press m to see the rest]" % (len(body) - len(shown)))
    out("-" * 78)


def review(register, deliveries_dir, qdir, include_kept, inp, out, get_scan=None):
    """-> counts dict. inp(prompt) returns a line (raises EOFError at end of input). get_scan() ->
    (scanner, sentinel) for the second scan a release needs (built only when first needed)."""
    rows = pending(register, include_kept)
    counts = {"released": 0, "kept": 0, "skipped": 0, "left": 0, "errors": 0, "still_held": 0}
    if not rows:
        out("Nothing waiting for review.")
        return counts
    out("%d quarantined message(s) to look at. r = release, k = keep, s = skip, m = more text, q = quit."
        % len(rows))
    for i, row in enumerate(rows, 1):
        rec = read_quarantine_file(qdir, row["id"])
        full = False
        while True:
            show(row, rec, i, len(rows), full, out)
            try:
                ans = inp("Release / Keep / Skip / More / Quit  [r/k/s/m/q]: ").strip().lower()
            except EOFError:
                ans = "q"
            if ans == "m":
                full = True
                continue
            if ans == "s":
                counts["skipped"] += 1
                break
            if ans == "q":
                counts["left"] = len(rows) - i + 1
                return counts
            if ans in ("r", "k"):
                if ans == "r" and rec is None:
                    out("  cannot release: the saved copy is missing. Keep or skip.")
                    continue
                if ans == "r":
                    out("  Scanning it again first (this can take up to a minute)...")
                    r = try_release(register, deliveries_dir, qdir, row, rec, get_scan, out)
                    if r[0] == "released":
                        counts["released"] += 1
                        out("  -> released: the new scan passed it, so it is filed like normal mail.")
                    elif r[0] == "held":
                        counts["still_held"] += 1
                        out("  -> NOT released: %s. It stays quarantined." % r[1])
                    else:
                        counts["errors"] += 1
                        out("  -> NOT done (%s). It stays as it was." % r[1])
                    break
                res = _locked(register, lambda: keep(register, row["id"]), out)
                if res in ("released", "kept"):
                    counts[res] += 1
                    out("  -> %s." % res)
                else:
                    counts["errors"] += 1
                    out("  -> NOT done (%s). It stays as it was." % (res or "mailroom busy"))
                break
            out("  please press r, k, s, m or q.")
    return counts


def main(argv=None, inp=input, out=print):
    ap = argparse.ArgumentParser(description="review the mailroom's quarantine")
    ap.add_argument("command", nargs="?", default="review", choices=("review", "list"))
    ap.add_argument("--rescan-all", action="store_true", help="batch: scan every quarantined message again")
    ap.add_argument("--all", action="store_true", help="include messages already kept")
    # The mailroom's places are the person's own install values, so there are no defaults here: the install script passes
    # all five (the mailroom cannot read the setup folder, so the install script is where they are written down).
    ap.add_argument("--drop", required=True, help="the one-way drop folder")
    ap.add_argument("--home", required=True, help="the mailroom account's home folder")
    ap.add_argument("--expect-user", required=True, help="the account this must run as ('' = do not check)")
    ap.add_argument("--config", required=True, help="the mailroom's root-owned reader-config.json")
    ap.add_argument("--claude", required=True, help="the mailroom's own claude binary")
    ap.add_argument("--test-allow-nonroot-config", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    os.umask(0o077)
    if os.getuid() == 0:
        out("refusing to run as root: run it as the mailroom account (see the walkthrough line)")
        return 2
    if a.expect_user and pwd.getpwuid(os.getuid()).pw_name != a.expect_user:
        out("wrong account: this must run as %s" % a.expect_user)
        return 2
    path = os.path.join(a.home, "register.db")
    if not os.path.isfile(path):
        out("no register at the mailroom's home: nothing to review")
        return 3
    register = readerd.Register(path)
    qdir = os.path.join(a.home, "quarantine")
    deliveries = os.path.join(a.drop, "deliveries")
    try:
        if a.command == "list":
            rows = pending(register, True)
            for row in rows:
                out(summary_line(row, read_quarantine_file(qdir, row["id"])))
            held = register.db.execute("SELECT COUNT(*) FROM messages WHERE status='held'").fetchone()[0]
            out("%d quarantined; %d held (held = waiting for the scanner, or parked on purpose: "
                "nothing to review there)" % (len(rows), held))
            return 0
        cache = []

        def get_scan():
            if cache:
                return cache[0]
            cfg = readerd.load_config(a.config, root_only=not a.test_allow_nonroot_config)
            sentinel = screen.PinnedSentinel(cfg["sentinel_dir"], cfg["sentinel_sha256"],
                                             os.path.join(a.home, "sentinel-state"))
            scanner = screen.ClaudeScanner(a.claude, a.home, os.path.join(a.home, "secret"), cfg["model"])
            cache.append((scanner, sentinel))
            return cache[0]
        if a.rescan_all:
            c = rescan_all(register, deliveries, qdir, a.all, get_scan, out)
            out("")
            out("DONE: %d scanned, %d released (clean on the new scan), %d still held, %d could not be handled" % (
                c["scanned"], c["released"], c["still_held"], c["errors"]))
            return 0
        counts = review(register, deliveries, qdir, a.all, inp, out, get_scan)
        out("")
        out("DONE: %d released, %d kept, %d skipped, %d not released (scanned again and still held), "
            "%d not asked (you quit), %d not done" % (
                counts["released"], counts["kept"], counts["skipped"], counts["still_held"], counts["left"],
                counts["errors"]))
        return 0
    finally:
        register.close()


if __name__ == "__main__":
    sys.exit(main())
