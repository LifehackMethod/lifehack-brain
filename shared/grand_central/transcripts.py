#!/usr/bin/env python3
"""transcripts.py - the ONE access point to email text, and the catalogue.

Front room, code only. Email text lives in two places here, both under the local folder that never
syncs to Drive (default <data root>/front-room, gc_settings.front_room_dir(), env AGE_FRONT_ROOM, same
convention as backup.py):
  transcripts/<thread_id>.txt   one file per thread, append-only, one block per message
  catalogue/catalogue.jsonl     one line per message: sender, subject, dates, label, file, verdict,
                                triage guess, how much was seen, which draft used it

Rules enforced here (plan B1 "Security, honestly"; the owner, 2026-11-15 evening):
  1. Text is handed ONLY to a caller that declares itself tool-less (Caller.tool_less is True, i.e.
     it lists no tools). A caller with tools is refused and the refusal is logged. A declaration
     can be false; the deny hook (setup/hooks/) and the out-of-place-read check (coverage.py)
     are what catch a window that goes around this door.
  2. Anything with no verdict in the catalogue is refused by every read: a transcript that holds a
     message block the catalogue has no "safe" verdict for is refused whole.
  3. Only messages the mailroom scanned as safe are ever ingested; a delivery that says anything
     else (or nothing) is refused and set aside, never filed.
  4. Fields a stranger wrote (sender, subject) are text too: they come back only through the same
     door. The typed fields (ids, dates, label, verdict, triage) are open: catalogue_meta().
The one-way delivery: the mailroom drops one file per message into a deliveries folder (it never
reads the front room); ingest() files it here and removes the delivery (it holds email text).
Python 3.9 compatible.
"""
import datetime
import fcntl
import hashlib
import hmac
import json
import os
import pwd
import re
import stat
import unicodedata

import gc_settings

BLOCK_MARK = "=== message "
ID_RE = re.compile(r"^[0-9a-f]{6,32}$")
DELIVERY_NAME_RE = re.compile(r"^[0-9a-f]{6,32}\.[0-9a-f]{6,32}\.json$")
MAX_DELIVERY_BYTES = 3 * 1024 * 1024
TYPED_RE = re.compile(r"[a-z_0-9\-]{1,16}")
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
DELIVERY_KEYS = {"schema", "thread_id", "message_id", "subject", "from", "date", "label",
                 "verdict", "triage", "block", "header", "seen", "internal_ms"}
SEEN = ("full", "partial")
SCHEMA = "gc.delivery/1"
_BLOCK_LINE = re.compile(r"^=== message ([0-9a-f]{6,32}) \|", re.M)


class LedgerKeyLost(Exception):
    """The catalogue exists but its key is gone. Loud on purpose: a new key would silently turn every
    existing thread into a refusal. Restore the key from backup; nothing here mints a replacement."""


class CatalogueMissing(Exception):
    """The catalogue file is gone (or empty) although this front room has filed mail before. Loud on
    purpose: every thread would otherwise just look 'refused'. Restore the catalogue from backup."""


class Refused(Exception):
    def __init__(self, reason):
        Exception.__init__(self, reason)
        self.reason = reason   # closed: caller_has_tools, no_verdict, bad_id, no_such_thread,
        #                        bad_delivery, quarantined_or_unscanned


# ---------------------------------------------------------------- places

def front_room():
    return gc_settings.front_room_dir()


def transcripts_dir():
    return os.path.join(front_room(), "transcripts")


def catalogue_dir():
    return os.path.join(front_room(), "catalogue")


def catalogue_path():
    return os.path.join(catalogue_dir(), "catalogue.jsonl")


def _access_log():
    return os.path.join(front_room(), "access.log")


def _mkdir(path):
    os.makedirs(path, mode=0o700, exist_ok=True)


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, text.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


# ---------------------------------------------------------------- callers

class Caller(object):
    """Who is asking. `tools` lists every tool the asking call can use; the empty tuple is the
    only thing that counts as tool-less. (A real reader call is `claude -p --tools ""`.)"""

    def __init__(self, name, tools=()):
        self.name = str(name)[:40]
        self.tools = tuple(tools)

    @property
    def tool_less(self):
        return self.tools == ()


def _log_access(caller, what, outcome):
    try:
        _mkdir(front_room())
        name = getattr(caller, "name", "unknown")
        _append(_access_log(), json.dumps({"ts": _now(), "caller": str(name)[:40], "what": what,
                                           "outcome": outcome}, sort_keys=True) + "\n")
    except OSError:
        pass   # logging must never turn a refusal into a read


def _require_tool_less(caller, what):
    if not isinstance(caller, Caller) or caller.tool_less is not True:
        _log_access(caller, what, "refused:caller_has_tools")
        raise Refused("caller_has_tools")


# ---------------------------------------------------------------- the catalogue
# The catalogue is DERIVED, never trusted as input: every line is written by ingest() from a
# validated delivery and carries a MAC (HMAC-SHA256 under a key that lives beside it, created at
# first ingest) and the sha256 of the block it vouches for. A line without a valid MAC is ignored
# (a hand-written or edited line cannot make anything readable), and read_thread() also checks that
# each block's text still hashes to what its line says.

def _key_path():
    return os.path.join(catalogue_dir(), ".ledger-key")


_KEY_RE = re.compile(rb"[0-9a-f]{64}")


def _catalogue_nonempty():
    try:
        return os.path.getsize(catalogue_path()) > 0
    except OSError:
        return False


def _key(create=False):
    """The ledger key, or None. A key file that is empty or corrupt is treated as missing: with a
    catalogue behind it that is LedgerKeyLost (loud, never replaced); with no catalogue yet (a crash at
    the very first ingest) nothing depends on it, so create=True writes a fresh one."""
    try:
        with open(_key_path(), "rb") as f:
            k = f.read().strip()
        if _KEY_RE.fullmatch(k):
            return k
        exists = True
    except OSError:
        exists = False
    if not create:
        return None
    if _catalogue_nonempty():
        raise LedgerKeyLost("the ledger key %s is %s but the catalogue exists: not minting a new key "
                            "(restore the key from the backup)" % (_key_path(), "unreadable" if exists else "missing"))
    _mkdir(catalogue_dir())
    tmp = _key_path() + ".new-%d" % os.getpid()
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, os.urandom(32).hex().encode("ascii") + b"\n")
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, _key_path())
    return _key()


def _mac(key, row):
    body = json.dumps(dict((k, v) for k, v in row.items() if k != "mac"), sort_keys=True)
    return hmac.new(key, body.encode("utf-8"), hashlib.sha256).hexdigest()


def _catalogue_rows():
    """Only lines with a valid MAC."""
    key = _key()
    rows = []
    if key is None:
        if _catalogue_nonempty():
            raise LedgerKeyLost("the ledger key is missing or unreadable but the catalogue exists")
        return rows
    if not _catalogue_nonempty() and _status().get("ever_ingested", 0) > 0:
        raise CatalogueMissing("the catalogue is missing but mail was filed before: restore it from backup")
    try:
        with open(catalogue_path(), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and isinstance(r.get("mac"), str) \
                        and hmac.compare_digest(r["mac"], _mac(key, r)):
                    rows.append(r)
    except OSError:
        pass
    return rows


_OPEN_FIELDS = ("thread_id", "message_id", "date", "label", "file", "verdict", "triage", "seen",
                "used_in_draft", "ingested_at", "internal_ms")


def catalogue_meta():
    """Typed fields only (no sender, no subject): open to code. -> list of dicts."""
    return [dict((k, r.get(k)) for k in _OPEN_FIELDS) for r in _catalogue_rows()]


def read_catalogue_text(caller):
    """Full catalogue rows, sender and subject included: only for a tool-less caller."""
    _require_tool_less(caller, "catalogue")
    _log_access(caller, "catalogue", "ok")
    return [dict((k, v) for k, v in r.items() if k not in ("mac", "block_sha256")) for r in _catalogue_rows()]


def _rows_by_id():
    return dict((r.get("message_id"), r) for r in _catalogue_rows())


# ---------------------------------------------------------------- ingest (the one-way slot)

def _typed_ok(v, depth=0):
    if v is None:
        return True
    if isinstance(v, str):
        if DATE_RE.fullmatch(v):
            try:
                datetime.date(int(v[:4]), int(v[5:7]), int(v[8:10]))
            except ValueError:
                return False
            return True
        return bool(TYPED_RE.fullmatch(v))
    if isinstance(v, dict) and depth < 2:
        return all(isinstance(k, str) and TYPED_RE.fullmatch(k) and _typed_ok(x, depth + 1)
                   for k, x in v.items())
    return False


def _text_ok(s, multiline):
    """Plain strings only: encodable, no surrogates, no line/paragraph separators, no controls
    (a block or header may contain newlines and tabs; a single-line field may not)."""
    if not isinstance(s, str):
        return False
    try:
        s.encode("utf-8")
    except UnicodeEncodeError:
        return False
    for ch in s:
        if ch in "\n\t":
            if not multiline and ch == "\n":
                return False
            continue
        if unicodedata.category(ch) in ("Cc", "Cs", "Zl", "Zp"):
            return False
    return True


def _no_dupes(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise Refused("bad_delivery")
        d[k] = v
    return d


def _no_const(_n):
    raise Refused("bad_delivery")


def _mailroom_uid(explicit):
    """The OS user id the mailroom runs as. Given by the caller, else looked up by account name
    (AGE_MAILROOM_USER, else gc.json mailroom_user). Unknown -> None -> nothing is accepted."""
    if explicit is not None:
        return explicit
    try:
        return pwd.getpwnam(gc_settings.mailroom_user()).pw_uid
    except KeyError:
        return None


def _read_delivery(path, uid):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > MAX_DELIVERY_BYTES:
            raise Refused("bad_delivery")
        if uid is None or st.st_uid != uid:
            raise Refused("bad_delivery")     # only a file the mailroom account itself wrote
        return os.read(fd, MAX_DELIVERY_BYTES + 1)
    finally:
        os.close(fd)


_BLOCK_HEAD_FULL = re.compile(r"=== message ([0-9a-f]{6,32}) \| [^\n]* ===\n")
_HEADER_RE = re.compile(r"# thread ([0-9a-f]{6,32}) \| subject: [^\n]*\n\n")


def _validate_delivery(raw, filename):
    try:
        d = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_dupes, parse_constant=_no_const)
    except Refused:
        raise
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise Refused("bad_delivery")
    if not isinstance(d, dict) or set(d.keys()) != DELIVERY_KEYS or d["schema"] != SCHEMA:
        raise Refused("bad_delivery")
    tid, mid = d["thread_id"], d["message_id"]
    if not (isinstance(tid, str) and ID_RE.fullmatch(tid) and isinstance(mid, str) and ID_RE.fullmatch(mid)):
        raise Refused("bad_delivery")
    if filename != "%s.%s.json" % (tid, mid):
        raise Refused("bad_delivery")
    if d["verdict"] != "safe":
        raise Refused("quarantined_or_unscanned")   # no verdict / any other verdict: never filed
    if d["seen"] not in SEEN:
        raise Refused("bad_delivery")
    if d["seen"] == "full":
        if not isinstance(d["triage"], dict) or not _typed_ok(d["triage"]):
            raise Refused("bad_delivery")
    elif d["triage"] is not None:               # not read in full: no triage guess
        raise Refused("bad_delivery")
    ms = d["internal_ms"]
    if isinstance(ms, bool) or not isinstance(ms, int) or not 0 <= ms <= 4 * 10 ** 12:
        raise Refused("bad_delivery")
    for k in ("subject", "from", "date", "label"):
        if not _text_ok(d[k], False):
            raise Refused("bad_delivery")
    for k in ("block", "header"):
        if not _text_ok(d[k], True):
            raise Refused("bad_delivery")
    hm = _HEADER_RE.fullmatch(d["header"])
    if not hm or hm.group(1) != tid:
        raise Refused("bad_delivery")           # exactly one header line for THIS thread, nothing else
    bm = _BLOCK_HEAD_FULL.match(d["block"])
    marks = _BLOCK_LINE.findall(d["block"])
    if not bm or bm.group(1) != mid or marks != [mid] or not d["block"].endswith("\n\n"):
        raise Refused("bad_delivery")           # exactly one block, and it is this message
    return d


def _split_blocks(text):
    """-> (header, [(message_id, block_text)]). Blocks run from one marker line to the next."""
    ms = list(_BLOCK_LINE.finditer(text))
    if not ms:
        return text, []
    out = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        out.append((m.group(1), text[m.start():end]))
    return text[:ms[0].start()], out


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _atomic_write(path, text):
    tmp = "%s.tmp-%d" % (path, os.getpid())
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, text.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)


def _file_block(tpath, d, rows):
    """Put the block in its thread's transcript in MESSAGE-DATE order: appended when it is the
    newest, otherwise inserted above the first later block (the file is rewritten atomically; every
    block's own text, and so its hash, is unchanged)."""
    mid, ms = d["message_id"], d["internal_ms"]
    if not os.path.isfile(tpath):
        _append(tpath, d["header"] + d["block"])
        return
    with open(tpath, encoding="utf-8") as f:
        text = f.read()
    header, blocks = _split_blocks(text)
    if mid in dict(blocks):
        return                                   # already there (an interrupted earlier run)
    key = lambda i: (rows.get(i, {}).get("internal_ms", 10 ** 15), i)   # noqa: E731  unknown sorts last
    new = (ms, mid)
    pos = len(blocks)
    for n, (i, _t) in enumerate(blocks):
        if key(i) > new:
            pos = n
            break
    if pos == len(blocks):
        _append(tpath, d["block"])
        return
    blocks.insert(pos, (mid, d["block"]))
    _atomic_write(tpath, header + "".join(t for _i, t in blocks))


def ingest(deliveries_dir, refused_dir=None, mailroom_uid=None):
    """File every delivery: put its block in the thread's transcript, add its catalogue line, remove the
    delivery. Idempotent per message id. Single instance (a lock file): a second run returns
    {"skipped": "another_ingest_running"}. A delivery is accepted only if the file is owned by the
    mailroom account's OS user id, parses without duplicate keys, and passes every check in
    _validate_delivery; anything else is set aside in refused/. One bad delivery never stops the rest.
    -> {"ingested", "duplicate", "refused"}"""
    _mkdir(front_room())
    counts = {"ingested": 0, "duplicate": 0, "refused": 0}
    lock = os.open(os.path.join(front_room(), "ingest.lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(lock)
        counts["skipped"] = "another_ingest_running"
        return counts
    try:
        return _ingest(deliveries_dir, refused_dir, _mailroom_uid(mailroom_uid), counts)
    finally:
        os.close(lock)


def _refused_path():
    return os.path.join(front_room(), "refused-at-ingest.jsonl")


def refused_records():
    """Every delivery ingest() refused: {ts, message_id, thread_id, reason}. Ids and a closed reason
    only, never text. The front room cannot send an acknowledgement back to the mailroom (one way by
    design), so this record, and the coverage proof that counts it, are how a delivery that the
    register called 'delivered' but the front room refused is never silent."""
    out = []
    try:
        with open(_refused_path(), encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def _record_refusal(name, reason):
    m = DELIVERY_NAME_RE.fullmatch(name)
    tid, mid = (name.split(".")[0], name.split(".")[1]) if m else (None, None)
    try:
        _append(_refused_path(), json.dumps({"ts": _now(), "message_id": mid, "thread_id": tid,
                                             "reason": reason if re.fullmatch(r"[a-z_]{1,40}", str(reason)) else "error"},
                                            sort_keys=True) + "\n")
    except OSError:
        pass


def _status():
    try:
        with open(os.path.join(front_room(), "ingest-status.json"), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_status(counts, reasons=()):
    """The ingest status, for the status light: RED, with named reasons, if anything was ever refused
    at ingest or if this run hit a problem (an unreadable transcript, a filing failure, a lost ledger
    key, a missing catalogue). It is rewritten every run, so a problem that persists stays red."""
    n = len(refused_records())
    why = sorted(set(reasons) | ({"refused_at_ingest"} if n else set()))
    ever = int(_status().get("ever_ingested", 0)) + int(counts.get("ingested", 0))
    try:
        _atomic_write(os.path.join(front_room(), "ingest-status.json"),
                      json.dumps({"ts": _now(), "refused_at_ingest": n, "light": "red" if why else "green",
                                  "reasons": why, "ever_ingested": ever,
                                  "last_run": dict((k, v) for k, v in counts.items() if isinstance(v, int))},
                                 sort_keys=True) + "\n")
    except OSError:
        pass


def _ingest(deliveries_dir, refused_dir, uid, counts):
    _mkdir(transcripts_dir())
    _mkdir(catalogue_dir())
    counts["deferred"] = 0
    problems = set()
    try:
        key = _key(create=True)         # LedgerKeyLost if the catalogue exists without a usable key
        rows = _rows_by_id()            # CatalogueMissing if the catalogue vanished
    except LedgerKeyLost:
        _write_status(counts, ["ledger_key_lost"])
        raise
    except CatalogueMissing:
        _write_status(counts, ["catalogue_missing"])
        raise
    refused_dir = refused_dir or os.path.join(front_room(), "refused")
    try:
        names = sorted(os.listdir(deliveries_dir))
    except OSError:
        return counts
    for name in names:
        if name.startswith("."):
            continue
        path = os.path.join(deliveries_dir, name)
        # phase 1: is it a delivery we accept? any failure here is a REFUSAL (recorded, set aside)
        try:
            if not DELIVERY_NAME_RE.fullmatch(name):
                raise Refused("bad_delivery")
            d = _validate_delivery(_read_delivery(path, uid), name)
        except Exception as e:
            counts["refused"] += 1
            reason = getattr(e, "reason", "error")
            _record_refusal(name, reason)
            try:
                _mkdir(refused_dir)
                os.rename(path, os.path.join(refused_dir, name + ".refused"))
            except OSError:
                pass
            _log_access(Caller("ingest"), "delivery", "refused:%s" % reason)
            continue
        # phase 2: filing it. A failure here (disk full, ...) is NOT a refusal: the delivery stays
        # where it is and is retried next run; _file_block skips a block that is already there, so
        # the retry heals a block that was written before the catalogue line could be.
        mid = d["message_id"]
        try:
            if mid in rows:
                counts["duplicate"] += 1
                os.unlink(path)
                continue
            tpath = os.path.join(transcripts_dir(), d["thread_id"] + ".txt")
            _file_block(tpath, d, rows)
            row = {"thread_id": d["thread_id"], "message_id": mid, "from": d["from"],
                   "subject": d["subject"], "date": d["date"], "label": d["label"],
                   "file": "transcripts/%s.txt" % d["thread_id"], "verdict": "safe",
                   "triage": d["triage"], "seen": d["seen"], "used_in_draft": None,
                   "internal_ms": d["internal_ms"], "ingested_at": _now(),
                   "block_sha256": _sha(d["block"])}
            row["mac"] = _mac(key, row)
            _append(catalogue_path(), json.dumps(row, sort_keys=True) + "\n")
            rows[mid] = row
            os.unlink(path)    # the delivery holds email text; the filed copy is the only one left
            counts["ingested"] += 1
        except Exception as e:
            counts["deferred"] += 1
            problems.add("transcript_unreadable" if isinstance(e, (UnicodeDecodeError, ValueError))
                         else "filing_failed")
            _log_access(Caller("ingest"), "delivery", "deferred:%s" % type(e).__name__)
    _write_status(counts, problems)
    return counts


# ---------------------------------------------------------------- the access point

def read_thread(thread_id, caller):
    """The one door to a thread's text. Tool-less callers only. Every block in the file must have a
    catalogue line that ingest() wrote (valid MAC, verdict safe) AND whose recorded hash still
    matches the block's text, and the header must be the one ingest wrote; otherwise the whole
    thread is refused."""
    _require_tool_less(caller, "thread:%s" % str(thread_id)[:32])
    if not isinstance(thread_id, str) or not ID_RE.fullmatch(thread_id):
        _log_access(caller, "thread", "refused:bad_id")
        raise Refused("bad_id")
    path = os.path.join(transcripts_dir(), thread_id + ".txt")
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        _log_access(caller, "thread:%s" % thread_id, "refused:no_such_thread")
        raise Refused("no_such_thread")
    header, blocks = _split_blocks(text)
    rows = _rows_by_id()
    hm = _HEADER_RE.fullmatch(header)
    ok = bool(blocks) and bool(hm) and hm.group(1) == thread_id
    if ok:
        for mid, btxt in blocks:
            r = rows.get(mid)
            if not r or r.get("verdict") != "safe" or r.get("thread_id") != thread_id \
                    or r.get("block_sha256") != _sha(btxt):
                ok = False
                break
    if not ok:
        _log_access(caller, "thread:%s" % thread_id, "refused:no_verdict")
        raise Refused("no_verdict")
    _log_access(caller, "thread:%s" % thread_id, "ok")
    return text


def list_threads():
    """Thread ids that have a transcript (ids only; no text)."""
    try:
        return sorted(n[:-4] for n in os.listdir(transcripts_dir())
                      if n.endswith(".txt") and ID_RE.match(n[:-4]))
    except OSError:
        return []


if __name__ == "__main__":
    import sys
    sys.stderr.write("transcripts.py is a library: the access point has no command line "
                     "(a command line would be a way around it).\n")
    sys.exit(2)
