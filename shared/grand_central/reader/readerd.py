#!/usr/bin/env python3
"""reader/readerd.py - the mailroom's background job (replaces the earlier prototype daemon).

Runs ONLY as the mailroom account, one pass per start (a LaunchDaemon starts it every 10
minutes: the fast clock). One pass, in this order:

  1. discover: for each read label, list threads (date-bounded query); a thread whose history id
     is unchanged costs nothing; for a changed thread, ask for ids only; every id never seen gets
     a register row at once with status "held" (so no message id can ever be lost);
  2. work: every "held" id is fetched in full, once per attempt, and handed to the PINNED Sentinel
     (reader/screen.py: pinned pattern scan + one tool-less reader call + pinned verdict) BEFORE
     anything is filed; a verdict without Sentinel's proof is refused (stays held);
       verdict safe        -> flattened (reader/flatten.py) and delivered one way (a file in the
                              deliveries folder, which the front room's ingest files), marked delivered
       any other verdict   -> quarantine folder (text kept there for him to look at), marked
                              quarantined, never delivered
       no verdict (scanner could not run, or its answer failed validation, or the fetch failed)
                           -> stays "held", unread, tried again on the next pass. Never delivered flagged.
  3. write a facts file with COUNTS ONLY (no ids of mail, no text). (Step 1.7: also the age of the oldest
     held message, held_oldest_age_s, and quarantined_total.)

The register (sqlite, mailroom's own folder) holds ids, status, verdict and thread state, never text.
Verdicts are sticky: a delivered or quarantined id is never fetched or scanned again.
Every id the pass ever saw is delivered, quarantined or held: Register.account() is the check.
Python 3.9 compatible (the LaunchDaemon runs Apple's root-owned python).
"""
import argparse
import datetime
import fcntl
import json
import os
import pwd
import re
import sqlite3
import stat
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from reader import fetch, flatten  # noqa: E402
from reader import screen  # noqa: E402  (own line: the connected gate reads only the first name of a multi-name import)

STATUSES = ("held", "delivered", "quarantined")
ATTENTION_LIMIT = 200
HELD_REASONS = ("discovered", "fetch_failed", "id_mismatch", "scanner_unavailable", "scan_invalid",
                "deferred_cap", "no_sentinel_proof", "excluded_label", "scan_unjudged",
                "not_in_read_label")
ATTENTION_REASONS = ("attack", "suspicious", "no_outcome") + HELD_REASONS
CONFIG_KEYS = {"read_labels": list, "exclude_labels": list, "days": int, "max_threads_per_source": int,
               "max_messages_per_pass": int, "max_body_chars": int, "model": str,
               "sentinel_dir": str, "sentinel_sha256": dict}
MODEL_RE = re.compile(r"^[a-z0-9.\-\[\]]{1,64}$")
MAX_CONFIG_BYTES = 64 * 1024


def now_ms():
    return int(time.time() * 1000)


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg):
    sys.stderr.write("%s readerd: %s\n" % (now_iso(), msg))   # codes and counts only
    sys.stderr.flush()


# ---------------------------------------------------------------- the register

class Register(object):
    """Ids, statuses, verdicts and thread states. No text, ever."""

    def __init__(self, path):
        self.lock_path = path + ".lock"
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, mode=0o700, exist_ok=True)
        self.db = sqlite3.connect(path)
        os.chmod(path, 0o600)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS messages(
          id TEXT PRIMARY KEY, thread_id TEXT NOT NULL, label TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('held','delivered','quarantined')),
          reason TEXT, verdict TEXT, attempts INTEGER NOT NULL DEFAULT 0,
          first_seen_ms INTEGER NOT NULL, updated_ms INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS threads(
          id TEXT PRIMARY KEY, history_id TEXT, newest_message_id TEXT, state TEXT,
          updated_ms INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS seen_log(id TEXT NOT NULL, seen_ms INTEGER NOT NULL);
        """)
        self.db.commit()

    # -- what fetch.discover() uses
    def thread_history(self, tid):
        r = self.db.execute("SELECT history_id FROM threads WHERE id=?", (tid,)).fetchone()
        return r[0] if r else None

    def has_message(self, mid):
        return self.db.execute("SELECT 1 FROM messages WHERE id=?", (mid,)).fetchone() is not None

    def add_message(self, mid, tid, label, t, reason="discovered"):
        self.db.execute("INSERT OR IGNORE INTO messages(id,thread_id,label,status,reason,attempts,"
                        "first_seen_ms,updated_ms) VALUES(?,?,?,?,?,0,?,?)",
                        (mid, tid, label, "held", reason, t, t))
        self.db.execute("INSERT INTO seen_log(id,seen_ms) VALUES(?,?)", (mid, t))
        self.db.commit()

    def release_excluded(self, mid):
        """A message that was excluded (DRAFT/SPAM/TRASH) and no longer carries such a label."""
        self.db.execute("UPDATE messages SET reason='discovered' WHERE id=? AND status='held' "
                        "AND reason IN ('excluded_label','not_in_read_label')", (mid,))
        self.db.commit()

    def thread_state(self, tid):
        r = self.db.execute("SELECT state FROM threads WHERE id=?", (tid,)).fetchone()
        return r[0] if r else None

    def set_thread(self, tid, history_id, newest, state, t):
        self.db.execute("INSERT INTO threads(id,history_id,newest_message_id,state,updated_ms) "
                        "VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET history_id=excluded.history_id,"
                        "newest_message_id=excluded.newest_message_id,state=excluded.state,"
                        "updated_ms=excluded.updated_ms", (tid, history_id, newest, state, t))
        self.db.commit()

    # -- the pass
    def held(self, limit, t_ms=None):
        """The work list. Excluded and not-in-read-label rows are never in it. A row that has used up its
        tries (scan_unjudged, or fetch_failed with MAX_TRIES used) comes back once COOLDOWN_MS has passed,
        and goes straight back to cooling if it fails again: capped, never permanent."""
        t = now_ms() if t_ms is None else t_ms
        return [dict(zip(("id", "thread_id", "label", "attempts"), r)) for r in self.db.execute(
            "SELECT id,thread_id,label,attempts FROM messages WHERE status='held' "
            "AND COALESCE(reason,'') NOT IN ('excluded_label','not_in_read_label') "
            "AND (COALESCE(reason,'') NOT IN ('scan_unjudged','fetch_failed','scanner_unavailable') OR attempts < ? "
            "     OR updated_ms <= ?) "
            "ORDER BY first_seen_ms, id LIMIT ?", (MAX_TRIES, t - COOLDOWN_MS, limit))]

    def get(self, mid):
        r = self.db.execute("SELECT id,thread_id,label,status,reason,verdict,attempts FROM messages "
                            "WHERE id=?", (mid,)).fetchone()
        return dict(zip(("id", "thread_id", "label", "status", "reason", "verdict", "attempts"),
                        r)) if r else None

    def mark(self, mid, status, verdict=None, reason=None, bump=False, t=None):
        assert status in STATUSES
        self.db.execute("UPDATE messages SET status=?, verdict=COALESCE(?,verdict), reason=?, "
                        "attempts=attempts+?, updated_ms=? WHERE id=?",
                        (status, verdict, reason, 1 if bump else 0, now_ms() if t is None else t, mid))
        self.db.commit()

    def account(self):
        """Every id ever seen is in exactly one of the three statuses. -> counts dict, plus
        'lost' = ids in the seen log with no (valid) row. Must be 0."""
        c = dict((s, 0) for s in STATUSES)
        for s, n in self.db.execute("SELECT status,COUNT(*) FROM messages GROUP BY status"):
            c[s] = n
        c["threads_not_yet_fetched"] = self.db.execute(
            "SELECT COUNT(*) FROM threads WHERE state='not_yet_fetched'").fetchone()[0]
        c["excluded"] = self.db.execute(
            "SELECT COUNT(*) FROM messages WHERE reason='excluded_label' AND status='held'").fetchone()[0]
        c["not_in_read_label"] = self.db.execute(
            "SELECT COUNT(*) FROM messages WHERE reason='not_in_read_label' AND status='held'").fetchone()[0]
        c["fetch_failed"] = self.db.execute(
            "SELECT COUNT(*) FROM messages WHERE reason='fetch_failed' AND status='held'").fetchone()[0]
        c["unjudged"] = self.db.execute(
            "SELECT COUNT(*) FROM messages WHERE reason='scan_unjudged' AND status='held'").fetchone()[0]
        c["lost"] = self.db.execute(
            "SELECT COUNT(DISTINCT s.id) FROM seen_log s LEFT JOIN messages m ON m.id=s.id "
            "WHERE m.id IS NULL OR m.status NOT IN ('held','delivered','quarantined')").fetchone()[0]
        return c

    def held_messages(self, limit=200):
        """Quarantined and held messages, newest first, as ids and a closed code only (never a sender,
        a subject or any text). -> (rows, total). Quarantined: reason is the verdict (attack, suspicious,
        no_outcome). Held: reason is the hold code."""
        rows = []
        for mid, tid, status, reason, verdict in self.db.execute(
                "SELECT id,thread_id,status,reason,verdict FROM messages WHERE status IN ('quarantined','held') "
                "ORDER BY updated_ms DESC, id DESC LIMIT ?", (limit,)):
            code = verdict if status == "quarantined" else reason
            rows.append({"message_id": mid, "thread_id": tid, "status": status,
                         "reason": code if code in ATTENTION_REASONS else "other"})
        total = self.db.execute("SELECT COUNT(*) FROM messages WHERE status IN ('quarantined','held')").fetchone()[0]
        return rows, total

    def held_oldest_age_s(self, t_ms):
        """Age in seconds (as of t_ms) of the oldest message that is held and WAITING to be read: the
        age of mail sitting unread because the scanner, the sign-in or the AI tool is not working.
        A parked row (a message that carries an excluded label, or is not in a read label) is held
        on purpose for ever and is NOT waiting, so it does not count. None when nothing is waiting."""
        r = self.db.execute(
            "SELECT MIN(first_seen_ms) FROM messages WHERE status='held' "
            "AND COALESCE(reason,'') NOT IN ('excluded_label','not_in_read_label')").fetchone()
        return None if r is None or r[0] is None else max(0, int((t_ms - r[0]) // 1000))

    def quarantined_total(self):
        return self.db.execute("SELECT COUNT(*) FROM messages WHERE status='quarantined'").fetchone()[0]

    def close(self):
        self.db.close()


# ---------------------------------------------------------------- files out (delivery, quarantine)

def _write_atomic(dirpath, name, obj):
    os.makedirs(dirpath, mode=0o700, exist_ok=True)
    data = (json.dumps(obj, sort_keys=True) + "\n").encode("utf-8")
    tmp = os.path.join(dirpath, ".tmp-" + uuid.uuid4().hex)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.rename(tmp, os.path.join(dirpath, name))


def deliver(deliveries_dir, row, email, verdict_doc, partial=False):
    """One file, one way. Only called for a message Sentinel passed as safe. A message that was cut
    at the size cap is delivered as 'partial' with no triage: only the part that was scanned."""
    clean = flatten.clean_message(email)
    _write_atomic(deliveries_dir, "%s.%s.json" % (row["thread_id"], row["id"]), {
        "schema": "gc.delivery/1", "thread_id": row["thread_id"], "message_id": row["id"],
        "subject": clean["subject"], "from": clean["from"], "date": clean["date"],
        "label": flatten.normalise_line(row["label"]), "verdict": verdict_doc["verdict"],
        "triage": None if partial else verdict_doc["triage"],
        "block": flatten.render_block(clean, row["label"], partial=partial),
        "header": flatten.render_header(row["thread_id"], clean["subject"]),
        "seen": "partial" if partial else "full", "internal_ms": int(email.get("internal_ms") or 0)})


def quarantine(quarantine_dir, row, email, verdict):
    _write_atomic(quarantine_dir, row["id"] + ".json", {
        "message_id": row["id"], "thread_id": row["thread_id"], "label": row["label"],
        "verdict": verdict, "quarantined_at": now_iso(), "email": email})


# ---------------------------------------------------------------- one pass

MAX_TRIES = 3                # tries (scan answers that fail validation, downloads that fail) per message
MAX_INVALID_ATTEMPTS = MAX_TRIES
FETCH_OUTAGE_RUN = 3         # this many failed downloads in a row: Gmail is failing, stop the pass
SCAN_OUTAGE_RUN = 3          # this many unavailable scans in a row with no answer: the scanner is down
COOLDOWN_MS = 24 * 3600 * 1000   # a message that used up its tries is tried again after this


def _lock(path):
    """Single instance: -> an fd holding the lock, or None if another run has it."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, mode=0o700, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    return fd


def run_pass(gmail, scanner, sentinel, register, deliveries_dir, quarantine_dir, cfg, today=None, t_ms=None):
    """One pass, single instance: a second run while one is going returns {"skipped": ...} cleanly."""
    fd = _lock(register.lock_path)
    if fd is None:
        return {"skipped": "another_pass_running", "discover": None, "downloaded": 0, "scan_calls": 0,
                "delivered": 0, "quarantined": 0, "held_after": None, "lost": None, "gmail_error": None,
                "scanner_error": None, "missing_labels": []}
    try:
        return _run_pass(gmail, scanner, sentinel, register, deliveries_dir, quarantine_dir, cfg, today, t_ms)
    finally:
        os.close(fd)


def _hold_unjudged(register, row, why, t_ms=None):
    """Hold for a reason that is the message's own (invalid answer, scanner exception): counted, and
    after MAX_TRIES held as unjudged and left alone until the cool-down passes, so it cannot starve
    others and is not lost for ever."""
    n = row["attempts"] + 1
    register.mark(row["id"], "held", reason="scan_unjudged" if n >= MAX_TRIES else why, bump=True, t=t_ms)


def _run_pass(gmail, scanner, sentinel, register, deliveries_dir, quarantine_dir, cfg, today=None, t_ms=None):
    t_ms = t_ms or now_ms()
    out = {"discover": None, "downloaded": 0, "scan_calls": 0, "delivered": 0, "quarantined": 0,
           "held_after": 0, "gmail_error": None, "scanner_error": None, "missing_labels": [],
           "missing_exclude_labels": [], "scanner_exceptions": 0}
    labels, exclude_ids = [], set()
    try:
        labels, missing = fetch.resolve_read_labels(gmail, cfg["read_labels"])
        out["missing_labels"] = missing
        # His exclude list resolves exactly like the read list. A name that does not resolve fails
        # CLOSED: reported here, and nothing is listed or read this pass (a message cannot be proven
        # clean of a label we cannot find).
        ex_found, ex_missing = fetch.resolve_read_labels(gmail, cfg["exclude_labels"])
        out["missing_exclude_labels"] = ex_missing
        exclude_ids = set(lid for _n, lid in ex_found)
        if not ex_missing:
            out["discover"] = fetch.discover(gmail, register, labels, cfg["days"],
                                             cfg["max_threads_per_source"], t_ms, today, exclude_ids)
    except fetch.GmailUnavailable as e:
        out["gmail_error"] = e.code   # nothing new could be listed; held ids still get a try below
    if out["gmail_error"] is None and not labels:
        out["gmail_error"] = "no_read_label_resolved"       # nothing may be read without a read label
    read_ids = set(lid for _n, lid in labels) if (out["gmail_error"] is None
                                                  and not out["missing_exclude_labels"]) else set()
    work = register.held(cfg["max_messages_per_pass"], t_ms) if read_ids else []
    fails_in_a_row = 0
    fetch_fails, scan_unavail, scans_answered, unavail_in_a_row = [], [], 0, 0
    fetch_outage = False
    for row in work:
        try:
            raw = gmail.get_message(row["id"])
        except fetch.GmailUnavailable as e:
            # Gmail answered the listing this pass. A download that fails is probably THIS message's
            # problem, but several in a row (or a high failure rate over the pass) means Gmail itself is
            # failing: stop, and count no tries. Only isolated failures count (applied after the loop).
            register.mark(row["id"], "held", reason="fetch_failed", t=t_ms)
            fetch_fails.append(row)
            out["fetch_failures"] = out.get("fetch_failures", 0) + 1
            fails_in_a_row += 1
            if fails_in_a_row >= FETCH_OUTAGE_RUN:
                fetch_outage = True
                out["gmail_error"] = e.code
                break
            continue
        fails_in_a_row = 0
        out["downloaded"] += 1
        email = fetch.message_to_email(raw, cfg["max_body_chars"])
        if email["message_id"] != row["id"]:
            _hold_unjudged(register, row, "id_mismatch", t_ms)
            continue
        mlabels = email["labels"].split(",")
        if fetch.excluded(mlabels, exclude_ids):
            register.mark(row["id"], "held", reason="excluded_label", t=t_ms)   # labels changed since listing
            continue
        if not (set(mlabels) & read_ids):
            register.mark(row["id"], "held", reason="not_in_read_label", t=t_ms)
            continue
        email = flatten.normalise_email(email)      # normalise BEFORE the scan: scanned == delivered
        try:
            res = screen.scan_email(email, scanner, sentinel)   # the scan comes first: no file exists yet
        except (screen.ScannerNotToolLess, screen.SentinelNotPinned):
            raise                                   # a wiring fault, not this message's fault: stop loudly
        except Exception:
            out["scanner_exceptions"] += 1          # the model blew up on THIS email: hold it, go on
            _hold_unjudged(register, row, "scan_invalid", t_ms)
            continue
        out["scan_calls"] += res["calls"]
        if res["status"] == "ok" and not screen.has_sentinel_proof(res, sentinel):
            res = {"status": "invalid", "reason": "no_sentinel_proof", "calls": res["calls"]}
        if res["status"] != "ok":
            if res["status"] == "unavailable":
                # One email the scanner could not handle (a timeout, an error): hold THAT one and go on.
                # Several in a row with no answer at all this pass is a real outage: stop. Tries are
                # counted after the loop, and only if the scanner answered something this pass.
                register.mark(row["id"], "held", reason="scanner_unavailable", t=t_ms)
                scan_unavail.append(row)
                out["scanner_error"] = res["reason"]
                unavail_in_a_row += 1
                if unavail_in_a_row >= SCAN_OUTAGE_RUN and not scans_answered:
                    break
                continue
            scans_answered += 1
            unavail_in_a_row = 0
            _hold_unjudged(register, row, "no_sentinel_proof" if res["reason"] == "no_sentinel_proof"
                           else "scan_invalid", t_ms)
            continue
        scans_answered += 1
        unavail_in_a_row = 0
        if res["verdict"] == "safe":
            deliver(deliveries_dir, row, email, {"verdict": "safe", "triage": res["triage"]},
                    partial=bool(res.get("partial")))
            register.mark(row["id"], "delivered", verdict="safe", t=t_ms)
            out["delivered"] += 1
        else:
            quarantine(quarantine_dir, row, email, res["verdict"])
            register.mark(row["id"], "quarantined", verdict=res["verdict"], t=t_ms)
            out["quarantined"] += 1
    # tries are counted only for isolated failures: not in a Gmail outage, not in a scanner outage
    if fetch_fails and not fetch_outage and not (len(fetch_fails) >= 2 and len(fetch_fails) >= out["downloaded"]):
        for row in fetch_fails:
            register.mark(row["id"], "held", reason="fetch_failed", bump=True, t=t_ms)
    if scan_unavail and (scans_answered or len(scan_unavail) < SCAN_OUTAGE_RUN):
        for row in scan_unavail:
            register.mark(row["id"], "held", reason="scanner_unavailable", bump=True, t=t_ms)
    acc = register.account()
    out["held_after"], out["lost"] = acc["held"], acc["lost"]
    out["threads_not_yet_fetched"], out["unjudged"] = acc["threads_not_yet_fetched"], acc["unjudged"]
    # for the front room's "check these" list: ids and closed codes only, bounded, newest first
    out["held_messages"], out["held_messages_total"] = register.held_messages(ATTENTION_LIMIT)
    # How the numbers add up: held_messages_total = held_after + quarantined_total (the list holds BOTH
    # the held and the quarantined). held_parked is the part of held_after that is not waiting for the
    # scanner (excluded label, not in a read label). held_oldest_age_s is the status light's field.
    out["quarantined_total"] = register.quarantined_total()
    out["held_parked"] = acc["excluded"] + acc["not_in_read_label"]
    out["held_oldest_age_s"] = register.held_oldest_age_s(t_ms)
    return out


# ---------------------------------------------------------------- config, main

def load_config(path, root_only=True):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_CONFIG_BYTES:
            raise ValueError("config_bad")
        if root_only and (st.st_uid != 0 or st.st_mode & 0o022):
            raise ValueError("config_bad")   # root-owned only: his account cannot change what is read
        raw = os.read(fd, MAX_CONFIG_BYTES)
    finally:
        os.close(fd)
    cfg = json.loads(raw.decode("utf-8"))
    cfg = dict((k, v) for k, v in cfg.items() if not k.startswith("_"))
    if set(cfg) != set(CONFIG_KEYS):
        raise ValueError("config_bad")
    for k, t in CONFIG_KEYS.items():
        if not isinstance(cfg[k], t) or (t is int and isinstance(cfg[k], bool)):
            raise ValueError("config_bad")
    if not cfg["read_labels"] or not all(isinstance(x, str) and 0 < len(x) <= 100
                                         for x in cfg["read_labels"]):
        raise ValueError("config_bad")   # no read label, no reading
    if not all(isinstance(x, str) and 0 < len(x) <= 100 for x in cfg["exclude_labels"]):
        raise ValueError("config_bad")   # may be empty; names, like read_labels
    if not (1 <= cfg["days"] <= 60 and 1 <= cfg["max_messages_per_pass"] <= 2000
            and 1 <= cfg["max_threads_per_source"] <= 1000
            and 1000 <= cfg["max_body_chars"] <= 200000 and MODEL_RE.match(cfg["model"])):
        raise ValueError("config_bad")
    sd = cfg["sentinel_sha256"]
    if not cfg["sentinel_dir"].startswith("/") or set(sd) != set(screen.PINNED_FILES) \
            or not all(isinstance(v, str) and re.match(r"^[0-9a-f]{64}$", v) for v in sd.values()):
        raise ValueError("config_bad")   # no pin, no reading
    return cfg


def main(argv=None):
    ap = argparse.ArgumentParser(description="mailroom reader daemon (one pass)")
    ap.add_argument("--drop", required=True, help="shared drop folder: deliveries/ and facts/ inside")
    ap.add_argument("--home", required=True, help="the mailroom account's home")
    ap.add_argument("--gws", required=True)
    ap.add_argument("--claude", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--expect-user", default=None)
    ap.add_argument("--test-allow-nonroot-config", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    os.umask(0o077)
    if os.getuid() == 0:
        log("refusing_to_run_as_root")
        return 2
    if a.expect_user is not None and pwd.getpwuid(os.getuid()).pw_name != a.expect_user:
        log("wrong_user")
        return 2
    work = os.path.join(a.home, "work")
    os.makedirs(work, mode=0o700, exist_ok=True)
    try:
        lock_fd = os.open(os.path.join(work, "readerd.lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log("another_pass_running")
        return 0
    if os.path.exists(os.path.join(work, ".env")):
        log("refusing: work/.env exists (gws would load it)")
        return 3
    try:
        cfg = load_config(a.config, root_only=not a.test_allow_nonroot_config)
    except (OSError, ValueError):
        log("config_bad")
        return 3
    facts = os.path.join(a.drop, "facts")
    try:
        gmail = fetch.GwsGmail(a.gws, a.home, os.path.join(a.home, "gws"))
    except fetch.GwsError as e:
        log("cannot_start %s" % e.code)
        _write_atomic(facts, "_reader_pass.json", {"written_at": now_iso(), "started": False,
                                                    "error": e.code})
        return 3
    try:
        sentinel = screen.PinnedSentinel(cfg["sentinel_dir"], cfg["sentinel_sha256"],
                                         os.path.join(a.home, "sentinel-state"))
    except screen.SentinelNotPinned as e:
        log("cannot_start sentinel %s" % e.code)
        _write_atomic(facts, "_reader_pass.json", {"written_at": now_iso(), "started": False,
                                                    "error": "sentinel_" + e.code})
        return 3
    scanner = screen.ClaudeScanner(a.claude, a.home, os.path.join(a.home, "secret"), cfg["model"])
    register = Register(os.path.join(a.home, "register.db"))
    try:
        res = run_pass(gmail, scanner, sentinel, register, os.path.join(a.drop, "deliveries"),
                       os.path.join(a.home, "quarantine"), cfg)
    finally:
        register.close()
    if res.get("skipped"):
        # A quarantine review holds the register lock for a moment: this pass did nothing, so it must
        # not overwrite the last real pass file with a stub that lacks the counts.
        log("pass_skipped %s" % res["skipped"])
        os.close(lock_fd)
        return 0
    res.update({"written_at": now_iso(), "started": True})
    _write_atomic(facts, "_reader_pass.json", res)    # counts and closed codes only
    log("pass_done delivered=%d quarantined=%d held=%d" % (res["delivered"], res["quarantined"],
                                                         res["held_after"]))
    os.close(lock_fd)
    return 0


if __name__ == "__main__":
    sys.exit(main())
