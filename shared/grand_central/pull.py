#!/usr/bin/env python3
"""pull.py — the rig's puller (plan task 1.4). Envelopes, calendar events and tasks into rig.db.

Hard rules this file obeys (INTAKE.md §1/§2/§5):
  - Gmail is reached ONLY through email_fetch (labels_list / list_threads / get_thread(id, "metadata")).
    No raw `gws gmail` call, no Gmail URL, no format=full/raw, no q= search anywhere in this file.
  - Calendar ONLY via safe_calendar.py (isolate mode); tasks via `gws tasks tasklists list` (permitted)
    + safe_tasks.py (isolate mode).
  - Every stranger-written field goes through the lane (task 1.5b): scrub → phrase scan
    (email_fetch.gate_message, unit="rig", unchanged — it mints provenance) AND the batched AI reader
    (batch_reader.judge_all — reads ALL stranger text, tools locked off). Quarantine if EITHER layer
    flags: phrase REAL-ATTACK/UNJUDGED or AI ATTACK/UNJUDGED. Store only items clean on both.
    All items of a run are staged first, judged in batches, then written — ~N/100 AI reader calls per
    run, not N. Which layer flagged an item (phrase / ai / both) is recorded in quarantine.reason.
  - Addresses: sanitize() only. Auth/Content-Type headers: booleans only. The dropped-header list from
    INTAKE §1 is simply never read.
  - Read-only toward Google; at most 5 Gmail calls in flight (thread pool 5); 2 retries with backoff,
    then an `errors` row and move on.
  - Idempotent: every table upserts by id.

Usage:
    python3 pull.py (--months N | --after YYYY-MM-DD [--before YYYY-MM-DD]) --max-threads M
                    [--calendar-months K] [--planted FILE]
    python3 pull.py --inbox-backfill --max-threads M     # read-only: fill in INBOX mail the store lacks, and
    python3 pull.py --label-resync                       # read-only, ids only: refresh INBOX + user labels on stored mail

--inbox-backfill lists message ids with messages.list labelIds=["INBOX"] ONLY (never q; paginated), drops ids
already in the messages table, then fetches/gates/stores the rest through the normal path (metadata fetch,
phrase + AI gate, quarantine files, a `runs` row). Calendar/tasks/filters/contacts are skipped in this mode.

Date window (--after/--before, inclusive, America/New_York): the date check runs BEFORE the gate, and a
thread wholly outside the window leaves no trace in the db (see pull_email). RIG_DB overrides the db path.
"""
import argparse
import concurrent.futures
import datetime
import getpass
import hashlib
import json
import os
import re
import secrets
import sqlite3
import subprocess
import sys
import time
import zoneinfo

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
import rig_env  # noqa: E402  — FIRST import; the environment is decided here and nowhere else
import batch_reader  # noqa: E402
import db as rigdb  # noqa: E402
import clock  # noqa: E402

FIELD_PREFIX = re.compile(r"^\s*FIELD\s+(\S+?):\s*", re.S)
GMAIL_WORKERS = 5
RETRIES = 2
BACKOFF_S = 3
DB_PATH = os.environ.get("RIG_DB") or os.path.join(rig_env.RIG_HOME, "rig.db")
NY = zoneinfo.ZoneInfo("America/New_York")

# New messages columns (SCHEMA CONTRACT) — added by a guarded ALTER on an existing db.
NEW_MESSAGE_COLUMNS = (("precedence", "TEXT"), ("auto_submitted", "TEXT"),
                       ("list_headers_present", "INTEGER"))

RIG_UNIT = "rig"   # the one Sentinel unit every rig run gates under (gate_message unit="rig")
EXIT_PAUSED = 75   # == email_fetch.EXIT_PAUSED

NO_DEDUPE = False   # --no-dedupe-cache: this run neither reads nor writes the reader's dedupe cache
QUAR_TABLE = "quarantine"  # planted runs switch this to planted_quarantine
STATS = {"gate_calls": 0, "quarantined": 0, "errors": 0, "messages": 0, "threads": 0,
         "calendar_events": 0, "tasks": 0, "gmail_calls": 0, "judge_calls": 0, "ai_items": 0,
         "reader_cache_hits": 0, "reader_in_run_dupes": 0, "reader_items_sent": 0,
         "gate_seen": 0, "gate_skipped": 0, "gate_judged": 0,
         "phrase_pass_s": 0, "ai_pass_s": 0}


def now_iso():
    return clock.now().isoformat(timespec="seconds")


def db_path():
    """RIG_DB (env, read at call time) wins; else DB_PATH (itself RIG_DB-or-default at import)."""
    return os.environ.get("RIG_DB") or DB_PATH


def ensure_message_columns(db):
    """Guarded ALTER TABLE: add any contract column the messages table lacks. Old rows survive (NULL)."""
    have = {r[1] for r in db.execute("PRAGMA table_info(messages)")}
    for name, typ in NEW_MESSAGE_COLUMNS:
        if name not in have:
            db.execute(f"ALTER TABLE messages ADD COLUMN {name} {typ}")


def open_db():
    path = db_path()
    os.makedirs(rig_env.RIG_HOME, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    db = rigdb.connect(path)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS labels(
        id TEXT PRIMARY KEY, name TEXT, type TEXT);
    CREATE TABLE IF NOT EXISTS threads(
        id TEXT PRIMARY KEY, message_count INTEGER, first_ms INTEGER, last_ms INTEGER);
    CREATE TABLE IF NOT EXISTS messages(
        id TEXT PRIMARY KEY, thread_id TEXT, internal_date INTEGER, label_ids TEXT, size INTEGER,
        from_addr TEXT, from_name TEXT, to_addrs TEXT, to_names TEXT, cc_addrs TEXT, cc_names TEXT,
        reply_to TEXT, subject TEXT, list_id TEXT, list_unsubscribe_present INTEGER,
        multipart_mixed INTEGER, spf_pass INTEGER, dkim_pass INTEGER, dmarc_pass INTEGER,
        is_sent INTEGER, gate_verdict TEXT,
        precedence TEXT, auto_submitted TEXT, list_headers_present INTEGER);
    CREATE TABLE IF NOT EXISTS calendar_events(
        id TEXT PRIMARY KEY, start TEXT, end TEXT, all_day INTEGER, status TEXT,
        organizer_email TEXT, attendee_emails TEXT, summary TEXT, location TEXT, description TEXT,
        gate_verdict TEXT);
    CREATE TABLE IF NOT EXISTS tasks(
        id TEXT PRIMARY KEY, list_id TEXT, title TEXT, notes TEXT, status TEXT,
        due TEXT, completed TEXT, updated TEXT, gate_verdict TEXT);
    CREATE TABLE IF NOT EXISTS quarantine(
        item_id TEXT, kind TEXT, verdict TEXT, reason TEXT, at TEXT);
    CREATE TABLE IF NOT EXISTS errors(
        item_id TEXT, kind TEXT, error TEXT, at TEXT);
    CREATE TABLE IF NOT EXISTS runs(
        started TEXT, finished TEXT, args TEXT, counts TEXT);
    CREATE TABLE IF NOT EXISTS planted_results(
        item_id TEXT PRIMARY KEY, kind TEXT, verdict TEXT, expect TEXT, reason TEXT, at TEXT);
    CREATE TABLE IF NOT EXISTS planted_quarantine(
        item_id TEXT, kind TEXT, verdict TEXT, reason TEXT, at TEXT);
    CREATE TABLE IF NOT EXISTS source_state(
        source TEXT PRIMARY KEY, last_success_at TEXT, rows INTEGER);
    CREATE TABLE IF NOT EXISTS filters(
        id TEXT PRIMARY KEY, criteria_json TEXT, action_json TEXT);
    CREATE TABLE IF NOT EXISTS contacts(
        resource_name TEXT PRIMARY KEY, emails_json TEXT, groups_json TEXT);
    """)
    ensure_message_columns(db)
    db.commit()
    return db


def record_error(db, item_id, kind, error):
    STATS["errors"] += 1
    db.execute("INSERT INTO errors(item_id, kind, error, at) VALUES(?,?,?,?)",
               (str(item_id)[:120], kind, str(error)[:500], now_iso()))
    db.commit()


def record_quarantine(db, item_id, kind, verdict, reason, table=None, detail=None):
    """detail = the judge's one-line reason (phrase-layer label and/or AI reader reason; never item text).
    The column comes from migration 004; on a db not yet migrated the row is written without it, loudly."""
    global _WARNED_NO_DETAIL
    if table is None:
        table = QUAR_TABLE
    STATS["quarantined"] += 1
    has_detail = "detail" in {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
    if has_detail:
        db.execute(f"INSERT INTO {table}(item_id, kind, verdict, reason, at, detail) VALUES(?,?,?,?,?,?)",
                   (str(item_id)[:120], kind, verdict, str(reason)[:500], now_iso(),
                    None if detail is None else str(detail)[:500]))
    else:
        if not _WARNED_NO_DETAIL:
            _WARNED_NO_DETAIL = True
            print(f"[pull] WARNING: {table}.detail column missing (migration 004 not applied); "
                  "quarantine reasons are NOT being kept. Run migrate.py.", file=sys.stderr)
        db.execute(f"INSERT INTO {table}(item_id, kind, verdict, reason, at) VALUES(?,?,?,?,?)",
                   (str(item_id)[:120], kind, verdict, str(reason)[:500], now_iso()))
    db.commit()


def update_quarantine_row(db, item_id, verdict, reason, detail):
    """Re-gate mode: fill reason/detail on the item's NEWEST existing quarantine row (no new row)."""
    STATS["quarantined"] += 1
    db.execute("""UPDATE quarantine SET verdict=?, reason=?, detail=? WHERE rowid =
                  (SELECT MAX(rowid) FROM quarantine WHERE item_id=?)""",
               (verdict, str(reason)[:500], None if detail is None else str(detail)[:500], str(item_id)[:120]))
    db.commit()


def regate_ids(db, since=None):
    """Item ids of calendar/task rows in the quarantine table (optionally only rows with at >= since)."""
    q = "SELECT DISTINCT item_id, kind FROM quarantine WHERE kind IN ('calendar_event','task')"
    args = ()
    if since:
        q += " AND at >= ?"
        args = (since,)
    return sorted((r[0], r[1]) for r in db.execute(q, args))


# ───────────────────── quarantine review files (local only; never Drive, never the DB) ─────────────────────
#
# A quarantined item's text is dropped from the db. So a human can later judge a false positive, the raw
# stranger-written fields go to ONE local file per item, under handoff/_unpacked/quarantine/. The `_unpacked`
# path component is what the plugin's ingest gate (ingest_gate_enforce.sh) treats as untrusted raw material:
# a plain Read there is refused; only safe_read.py or the tool-less ingest-reader can open the file.
# Files are mode 600, the directories 700. Pruned after QUARANTINE_KEEP_DAYS at the start of each pull run.
QUARANTINE_KEEP_DAYS = 30
_WARNED_NO_DETAIL = False


def quarantine_dir():
    """RIG_HANDOFF_DIR (env seam, read at call time) overrides the handoff root; default RIG_HOME/handoff."""
    root = os.environ.get("RIG_HANDOFF_DIR") or os.path.join(rig_env.RIG_HOME, "handoff")
    return os.path.join(root, "_unpacked", "quarantine")


def safe_item_id(item_id):
    """Filesystem-safe name; a hash suffix is added whenever anything was changed so ids never collide."""
    raw = str(item_id)
    clean = re.sub(r"[^A-Za-z0-9._-]", "_", raw).lstrip(".")[:100] or "item"
    if clean != raw:
        clean += "-" + hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()[:8]
    return clean


def write_quarantine_file(item_id, kind, verdict, reason, fields):
    """Write the raw fields of one quarantined item. Returns the path, or None on failure (stderr says why:
    a failed review file never blocks the run or the db row)."""
    try:
        d = quarantine_dir()
        for part in (os.path.dirname(d), d):       # _unpacked/, then quarantine/ — both 700
            os.makedirs(part, mode=0o700, exist_ok=True)
            os.chmod(part, 0o700)
        path = os.path.join(d, safe_item_id(item_id) + ".txt")
        lines = [f"item_id: {item_id}", f"kind: {kind}", f"verdict: {verdict}", f"reason: {reason}",
                 f"quarantined_at: {now_iso()}",
                 "NOTE: raw stranger-written text below, UNTRUSTED. Open only with safe_read.py or the ingest-reader.",
                 "=" * 60]
        for name, val in fields.items():
            lines.append(f"[{name}]")
            lines.append(str(val) if val else "")
            lines.append("")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fd = None
                fh.write("\n".join(lines))
        finally:
            if fd is not None:
                os.close(fd)
        return path
    except OSError as e:
        print(f"[pull] ERROR: could not write quarantine file for {str(item_id)[:60]!r}: {e}", file=sys.stderr)
        return None


def prune_quarantine_files(now=None, keep_days=QUARANTINE_KEEP_DAYS):
    """Delete quarantine files older than keep_days. Logs the count; errors go to stderr. Returns the count."""
    d = quarantine_dir()
    if not os.path.isdir(d):
        print(f"[pull] quarantine files pruned: 0 (no {d})", flush=True)
        return 0
    cutoff = (time.time() if now is None else now) - keep_days * 86400
    pruned = 0
    for name in sorted(os.listdir(d)):
        path = os.path.join(d, name)
        try:
            if os.path.isfile(path) and not os.path.islink(path) and os.path.getmtime(path) < cutoff:
                os.remove(path)
                pruned += 1
        except OSError as e:
            print(f"[pull] ERROR: could not prune {path}: {e}", file=sys.stderr)
    print(f"[pull] quarantine files pruned: {pruned} (older than {keep_days} days)", flush=True)
    return pruned


# ───────────────────────── the lane (INTAKE §2 + task 1.5b) ─────────────────────────
#
# Two layers, per stranger-written field, per item:
#   phrase layer — email_fetch.gate_message(unit="rig", ...) UNCHANGED: it scrubs, scans, mints
#                  provenance, and runs its own reader only on scanner hits.
#   AI layer     — batch_reader.judge_all: EVERY item's sanitized stranger text, in batches of ≤100,
#                  tools locked off (owner ruling 2026-11-10).
# An item is quarantined if EITHER layer flags. All items of a run are staged first (no db writes),
# judged, then written — so a run makes ~N/100 AI reader calls, not N.

REGATE_IDS = None   # set by --regate-quarantined: only these staged ids are judged/written (None = normal run)

RELEASE = None      # set by --release-quarantined: {"reason": str, "override": set(ids)}; None = not a release run

PENDING = []   # {"item": id, "kind": kind, "fields": {name: raw}, "write": fn(cleared|None, verdict, reason)}


def stage_fields(fields, item, kind, write):
    """Stage one item's stranger fields for the run-wide lane. write(cleared|None, verdict, reason)
    is called once at flush with the combined verdict; it owns the db row for this item."""
    if REGATE_IDS is not None and str(item) not in REGATE_IDS:
        return
    PENDING.append({"item": str(item), "kind": kind,
                    "fields": {k: v for k, v in fields.items()}, "write": write})


def join_fields(fields):
    """Join stranger fields into one gate body under a RANDOM per-call separator token.

    THE SPLIT-BACK BUG, for the record: the old fixed separator '\\n---\\n' was indistinguishable
    after the gate — FIELD-mode sanitize flattens '\\n---\\n' AND any '---' inside a field value to
    the same ' --- ', so a task whose notes contained '---' split into unattributable chunks,
    parse failed, and 3 real tasks were wrongly quarantined 'gate split-back failed'. A random
    token (@@RIGSEP-<hex>@@, plain ASCII, no angle brackets, not whitespace) survives FIELD-mode
    sanitize intact and is per-call secret, so a field can neither collide with it nor fake it."""
    token = "RIGSEP-" + secrets.token_hex(12).upper()
    sep = f"\n@@{token}@@\n"
    body = sep.join(f"FIELD {name}: {val}" for name, val in fields.items() if val)
    return body, token


def split_fields(content, token, field_names):
    """Split gate content back into per-field values using the call's own separator token.
    Each chunk is 'FIELD <name>: <value>'. Returns None if reconstruction is not clean."""
    chunks = [c for c in content.split(f"@@{token}@@") if c.strip()]
    out, seen = {}, set()
    for chunk in chunks:
        m = FIELD_PREFIX.match(chunk.strip())
        if not m:
            return None
        name = m.group(1)
        if name not in field_names or name in seen:
            return None
        seen.add(name)
        out[name] = chunk.strip()[m.end():].strip()
    for name in field_names:
        out.setdefault(name, "")   # fields that were empty going in stay empty
    return out


def gate_field_alone(name, val, item):
    """Fallback: one field, one gate_message call. Returns (verdict, cleared|None, reason)."""
    body, token = join_fields({name: val})
    res = email_fetch.gate_message(unit="rig", body=body, item=item)
    verdict = res.get("verdict") or "UNJUDGED"
    if verdict not in ("NONE", "BENIGN"):
        return verdict, None, str(res.get("reason") or "")
    cleared = split_fields(res.get("content") or "", token, {name: val})
    if cleared is None:
        return "UNJUDGED", None, "gate split-back failed (per-field)"
    return verdict, cleared, ""


# ───────────── gate cache: skip re-gating unchanged calendar/task items ─────────────
#
# A calendar/task item whose gated text is unchanged since its last CLEAN gate verdict is neither
# phrase-gated nor AI-judged again — the verdict is kept and the row is written as before. The hash
# covers EXACTLY the text the AI judge inspects (_gate_text), so any field change is a miss. Safety
# rules (mirroring batch_reader's dedupe cache):
#   * ONLY a clean verdict on both layers is stored. A flagged or UNJUDGED item's row is deleted, so
#     quarantined, released and re-gated items always re-gate.
#   * Skips apply to calendar_event/task items ONLY, never email (which arrives by the thousands),
#     never filters/contacts, never planted runs, never --regate/--release, never with --no-gate-cache.
#   * An item with ANY row in the quarantine table is never skipped, even if it was later released.
#   * A db without the gate_cache table (migration 012 not applied) skips nothing, loudly — the run
#     gates as before (fail toward reading).
GATE_CACHE_KINDS = ("calendar_event", "task")
GATE_CACHE_CLEAN = "CLEAN"
NO_GATE_CACHE = False   # --no-gate-cache: this run re-gates everything and writes no cache rows
_WARNED_NO_GATE_CACHE = False


def _gate_text(fields):
    """The exact text the AI judge inspects for one item: FIELD-mode sanitized stranger fields,
    empties dropped, fixed dict order. Shared by the AI pass and the gate-cache hash so the two
    can never drift apart."""
    return "\n".join(f"FIELD {name}: {sanitize.sanitize(val, max_len=sanitize.NO_CAP)}"
                     for name, val in fields.items() if val)


def gate_text_hash(fields):
    """sha256 of the gated text — the key stored with the item's last gate verdict."""
    return hashlib.sha256(_gate_text(fields).encode("utf-8")).hexdigest()


def _gate_cache_table(db):
    """True if migration 012 has been applied. Warn once, loudly, if not."""
    global _WARNED_NO_GATE_CACHE
    try:
        have = "gate_cache" in {r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='gate_cache'")}
    except Exception:  # noqa: BLE001 — an unreadable db skips nothing (fail toward gating)
        return False
    if not have and not _WARNED_NO_GATE_CACHE:
        _WARNED_NO_GATE_CACHE = True
        print("[pull] WARNING: gate_cache table missing (migration 012 not applied); unchanged items "
              "are being RE-GATED this run. Run migrate.py.", file=sys.stderr)
    return have


def _gate_cache_skips(db):
    """Return {item_id: fields} for staged calendar/task items whose gated text is unchanged since
    their last CLEAN verdict. Everything else stays in the lane untouched."""
    skips = {}
    if NO_GATE_CACHE or REGATE_IDS is not None or RELEASE is not None or QUAR_TABLE != "quarantine":
        return skips
    if not _gate_cache_table(db):
        return skips
    try:
        quarantined = {r[0] for r in db.execute(f"SELECT DISTINCT item_id FROM {QUAR_TABLE}")}
        for p in PENDING:
            if p["kind"] not in GATE_CACHE_KINDS or not any(v for v in p["fields"].values()):
                continue
            if p["item"] in quarantined:
                continue   # a quarantined item is never skipped, even if later released
            row = db.execute("SELECT text_hash, verdict FROM gate_cache WHERE item_id=?",
                             (p["item"],)).fetchone()
            if row and row[1] == GATE_CACHE_CLEAN and row[0] == gate_text_hash(p["fields"]):
                skips[p["item"]] = p["fields"]
    except Exception as e:  # noqa: BLE001 — an unreadable cache skips nothing (fail toward gating)
        sys.stderr.write(f"[pull] gate cache unreadable ({e}); gating everything\n")
        return {}
    return skips


def _gate_cache_update(db, item_id, kind, fields, clean):
    """Record (clean verdict on both layers) or drop (anything else) the item's cache row."""
    if kind not in GATE_CACHE_KINDS:
        return
    if clean:
        db.execute("INSERT OR REPLACE INTO gate_cache(item_id, kind, text_hash, verdict, at) "
                   "VALUES(?,?,?,?,?)",
                   (str(item_id)[:120], kind, gate_text_hash(fields), GATE_CACHE_CLEAN, now_iso()))
    else:
        db.execute("DELETE FROM gate_cache WHERE item_id=?", (str(item_id)[:120],))


def flush_pending(db):
    """Judge everything staged this run (phrase pass, then batched AI pass), then write."""
    if not PENDING:
        return
    # 0. gate-cache pass — unchanged clean calendar/task items skip both layers (verdict kept)
    STATS["gate_seen"] = len(PENDING)
    skips = _gate_cache_skips(db)
    STATS["gate_skipped"] = len(skips)
    STATS["gate_judged"] = len(PENDING) - len(skips)
    # 1. phrase pass — gate_message per item, unchanged (provenance + scanner-hit reader)
    _t_phrase = time.time()
    phrase = {}
    for p in PENDING:
        fields = p["fields"]
        if p["item"] in skips:
            # skipped: text unchanged, last verdict clean on both layers — keep it, store the
            # sanitized fields as cleared (the release-override path stores exactly this shape)
            phrase[p["item"]] = ("NONE", "",
                                 {k: sanitize.sanitize(v, max_len=sanitize.NO_CAP) if v else ""
                                  for k, v in fields.items()})
            continue
        if not any(v for v in fields.values()):
            phrase[p["item"]] = ("NONE", "", {k: "" for k in fields})
            continue
        STATS["gate_calls"] += 1
        body, token = join_fields(fields)
        res = email_fetch.gate_message(unit="rig", body=body, item=p["item"])
        verdict = res.get("verdict") or "UNJUDGED"
        reason = str(res.get("reason") or "")
        cleared = None
        if verdict in ("NONE", "BENIGN"):
            cleared = split_fields(res.get("content") or "", token, fields)
            if cleared is None:
                # split-back still failed → judge fields ONE AT A TIME before giving up
                cleared, bad = {}, ""
                for name, val in fields.items():
                    if not val:
                        cleared[name] = ""
                        continue
                    v2, c2, r2 = gate_field_alone(name, val, p["item"])
                    if v2 not in ("NONE", "BENIGN") or c2 is None:
                        verdict, cleared, bad = (v2 if v2 != "NONE" else "UNJUDGED"), None, (r2 or bad)
                        break
                    cleared[name] = c2[name]
                if cleared is None:
                    reason = bad or reason
        phrase[p["item"]] = (verdict, reason, cleared)

    STATS["phrase_pass_s"] = round(time.time() - _t_phrase, 1)   # phase timing: where do the minutes go?
    _t_ai = time.time()
    # 2. AI pass — EVERY item with stranger text (not only scanner hits), in batches
    batch, seen = [], set()
    for p in PENDING:
        if not any(v for v in p["fields"].values()) or p["item"] in seen or p["item"] in skips:
            continue
        seen.add(p["item"])
        batch.append((p["item"], _gate_text(p["fields"])))
    # still reads ALL stranger text: the dedupe cache only skips text already judged CLEAN (batch_reader.py)
    ai_reasons = {}
    ai = batch_reader.judge_all(batch, use_cache=not NO_DEDUPE, reasons=ai_reasons) if batch else {}
    STATS["ai_items"] = len(batch)
    STATS["judge_calls"] = batch_reader.STATS["claude_calls"]
    STATS["reader_cache_hits"] = batch_reader.STATS["cache_hits"]
    STATS["reader_in_run_dupes"] = batch_reader.STATS["in_run_dupes"]
    STATS["reader_items_sent"] = batch_reader.STATS["sent_to_reader"]
    STATS["ai_pass_s"] = round(time.time() - _t_ai, 1)
    print(f"[pull] gate cache: {STATS['gate_seen']} item(s) seen, {STATS['gate_skipped']} skipped unchanged, "
          f"{STATS['gate_judged']} gated, {STATS['judge_calls']} judge call(s) this run", flush=True)

    # 3. combine: quarantine if EITHER layer flags; record which layer in reason
    for p in PENDING:
        pv, preason, cleared = phrase[p["item"]]
        av = ai.get(p["item"], "NONE") if p["item"] in seen else "NONE"
        ph_flag = pv in ("REAL-ATTACK", "UNJUDGED")
        ai_flag = av in ("ATTACK", "UNJUDGED")
        layers = "+".join(n for n, f in (("phrase", ph_flag), ("ai", ai_flag)) if f)
        if RELEASE is not None:
            # owner-approved release of a quarantined calendar/task item through the normal gate: judged clean ->
            # stored as cleared; still flagged -> stored ONLY if the owner named it in --override (sanitized text,
            # verdict OWNER-OVERRIDE, reason kept on the quarantine row); otherwise stays quarantined.
            override = p["item"] in RELEASE["override"]
            if layers and not override:
                update_quarantine_row(db, p["item"], "REAL-ATTACK", "release-refused",
                                      f"release refused: gate still flags ({layers}); no override given")
                continue
            if layers:
                out = {k: sanitize.sanitize(v, max_len=sanitize.NO_CAP) if v else "" for k, v in p["fields"].items()}
                vout, note = "OWNER-OVERRIDE", f"released by owner override ({layers} flagged): {RELEASE['reason']}"
            else:
                out, vout, note = cleared, pv, f"released: re-judged clean ({pv}/{av}): {RELEASE['reason']}"
            p["write"](out, vout, "")
            update_quarantine_row(db, p["item"], "RELEASED", "released", note)
            continue
        if layers:
            verdict = "REAL-ATTACK" if (pv == "REAL-ATTACK" or av == "ATTACK") else "UNJUDGED"
            reason = layers + (f": {preason}" if preason else "")
            detail = "; ".join(x for x in (
                f"phrase: {preason}" if ph_flag and preason else ("phrase: flagged" if ph_flag else ""),
                f"ai: {ai_reasons.get(p['item']) or av}" if ai_flag else "") if x)
            if REGATE_IDS is not None:
                update_quarantine_row(db, p["item"], verdict, reason, detail)
            else:
                record_quarantine(db, p["item"], p["kind"], verdict, reason, detail=detail)
            if QUAR_TABLE == "quarantine":   # planted fixtures get no review file
                write_quarantine_file(p["item"], p["kind"], verdict, detail or reason, p["fields"])
            if REGATE_IDS is None and RELEASE is None and QUAR_TABLE == "quarantine":
                _gate_cache_update(db, p["item"], p["kind"], p["fields"], clean=False)
            p["write"](None, verdict, layers)
        elif REGATE_IDS is not None:
            # re-gate of a previously quarantined item that the judge now clears: do NOT store its text.
            # Give the human the review file anyway and note the re-judgement on the existing row.
            note = f"regate: re-judged {pv}/{av} now (originally quarantined); text not stored"
            update_quarantine_row(db, p["item"], "REGATE-CLEARED", "regate-cleared", note)
            write_quarantine_file(p["item"], p["kind"], "REGATE-CLEARED", note, p["fields"])
        else:
            # clean on both layers (or skipped as unchanged-clean): record/refresh the cache row so
            # the next pull can skip this item unless its text changes
            _gate_cache_update(db, p["item"], p["kind"], p["fields"], clean=True)
            p["write"](cleared, pv, "")
    PENDING.clear()


# ───────────────────────── retry wrapper + Gmail calls (only via email_fetch) ─────────────────────────

def gate():
    """Pause gate: raise email_fetch.Paused if unit "rig" is paused. Called before EVERY Google call
    (the door's own check_paused only guards fetch(), which the rig never uses). Paused is never
    swallowed: nothing below catches it (the broad excepts wrap only subprocess.run)."""
    email_fetch.check_paused(RIG_UNIT)


def with_retries(db, item_id, kind, fn, *args, **kwargs):
    """Retry a door call twice with backoff; on final failure record in `errors` and move on."""
    for attempt in range(RETRIES + 1):
        gate()
        STATS["gmail_calls"] += 1
        data, err = fn(*args, **kwargs)
        if err is None:
            return data
        time.sleep(BACKOFF_S * (attempt + 1))
    record_error(db, item_id, kind, err)
    return None


# ───────────────────────── email ─────────────────────────

def cutoff_ms(months):
    return int((clock.now().timestamp() - months * 30 * 24 * 3600) * 1000)


def window_bounds(months, after, before):
    """Return (lo_ms, hi_ms_exclusive|None, windowed). --after/--before are inclusive YYYY-MM-DD dates
    in America/New_York: lo = 00:00 ET of `after`, hi = 00:00 ET of the day AFTER `before`.
    windowed is False for the legacy --months-only run (old behavior: out-of-range threads are kept)."""
    if not after and not before:
        if months is None:
            raise SystemExit("need --months, or --after/--before")
        return cutoff_ms(months), None, False
    lo = hi = None
    if after:
        d = datetime.date.fromisoformat(after)
        lo = int(datetime.datetime(d.year, d.month, d.day, tzinfo=NY).timestamp() * 1000)
    elif months is not None:
        lo = cutoff_ms(months)
    else:
        lo = 0
    if before:
        d = datetime.date.fromisoformat(before) + datetime.timedelta(days=1)
        hi = int(datetime.datetime(d.year, d.month, d.day, tzinfo=NY).timestamp() * 1000)
    return lo, hi, True


def in_window(ms, lo, hi):
    return ms > 0 and ms >= lo and (hi is None or ms < hi)


def iter_thread_pages(db, max_threads, page_size=200):
    """Lazily page list_threads (NO q — metadata scope forbids it), newest-first, one page of ids per
    yield, so the caller can stop paging early. includeSpamTrash=true so SPAM/TRASH mail is listed."""
    token, budget, n = None, max_threads, 0
    while budget > 0:
        params = {"maxResults": min(page_size, budget), "includeSpamTrash": True}
        if token:
            params["pageToken"] = token
        data = with_retries(db, f"threads.list p{n}", "threads.list", email_fetch.list_threads, params)
        n += 1
        if data is None:
            return
        page = [t.get("id") for t in data.get("threads", []) if t.get("id")][:budget]
        budget -= len(page)
        if page:
            yield page
        token = data.get("nextPageToken")
        if not token or not page:
            return


def fetch_thread(tid):
    """Thread-pool safe: NO db access here (sqlite connection is main-thread only)."""
    for attempt in range(RETRIES + 1):
        gate()   # runs in a pool worker; Paused re-raises out of pool.map in pull_email
        STATS["gmail_calls"] += 1
        data, err = email_fetch.get_thread(tid, "metadata")
        if err is None:
            return data, None
        time.sleep(BACKOFF_S * (attempt + 1))
    return None, err


def header_map(msg):
    return {h.get("name", ""): h.get("value", "") for h in (msg.get("payload") or {}).get("headers", [])}


def header_ci(headers, name):
    """Case-insensitive header lookup ('' when absent)."""
    low = name.lower()
    for k, v in headers.items():
        if k.lower() == low:
            return v
    return ""


# List-* headers that count as "list_headers_present" (List-Id / List-Unsubscribe have their own columns).
LIST_EXTRA = {"list-post", "list-help", "list-archive", "list-owner", "list-subscribe"}


def list_headers_present(headers):
    return 1 if any(k.lower() in LIST_EXTRA for k in headers) else 0


def norm_machine_header(value, cap):
    """Precedence / Auto-Submitted after the lane: lowercased, whitespace-collapsed, capped; else None."""
    v = " ".join((value or "").lower().split())[:cap]
    return v or None


def parse_addr_header(value):
    """Return ([addr-spec, ...], [display-name, ...]) from a From/To/Cc header value."""
    from email.utils import getaddresses
    addrs, names = [], []
    for _display, addr in getaddresses([value or ""]):
        if addr:
            addrs.append(addr)
            names.append(_display or "")
    return addrs, names


def auth_booleans(headers):
    """Authentication-Results / Received-SPF → spf/dkim/dmarc booleans ONLY (raw values dropped)."""
    ar = " ".join(v for k, v in headers.items() if k.lower() == "authentication-results").lower()
    spf_hdr = " ".join(v for k, v in headers.items() if k.lower() == "received-spf").lower()
    def has(what):
        return 1 if (re.search(rf"{what}\s*=\s*pass", ar) or spf_hdr.startswith(what)) else 0
    return has("spf"), has("dkim"), has("dmarc")


def store_message(db, msg, tid):
    mid = msg.get("id") or ""
    headers = header_map(msg)
    from_addrs, from_names = parse_addr_header(headers.get("From", ""))
    to_addrs, to_names = parse_addr_header(headers.get("To", ""))
    cc_addrs, cc_names = parse_addr_header(headers.get("Cc", ""))
    ct = headers.get("Content-Type", "")
    spf, dkim, dmarc = auth_booleans(headers)
    label_ids = msg.get("labelIds") or []
    is_sent = 1 if "SENT" in label_ids else 0
    try:
        ms = int(msg.get("internalDate") or 0)
    except (TypeError, ValueError):
        ms = 0

    # Stranger-written fields (INTAKE §1: full lane). Addresses are NOT here — sanitize() only.
    stranger = {
        "subject": headers.get("Subject", ""),
        "from_name": " ".join(n for n in from_names if n),
        "to_names": " ".join(n for n in to_names if n),
        "cc_names": " ".join(n for n in cc_names if n),
        "reply_to": headers.get("Reply-To", ""),
        "list_id": headers.get("List-Id", ""),
        "list_unsubscribe": headers.get("List-Unsubscribe", ""),
        "precedence": header_ci(headers, "Precedence"),
        "auto_submitted": header_ci(headers, "Auto-Submitted"),
    }
    lhp = list_headers_present(headers)

    def addr_json(addrs):
        return json.dumps([sanitize_addr(a) for a in addrs], ensure_ascii=False)

    def write(cleared, verdict, _reason):
        # cleared None → quarantined: structural fields only, stranger fields NULL, never the text
        db.execute("""
            INSERT OR REPLACE INTO messages(id, thread_id, internal_date, label_ids, size,
                from_addr, from_name, to_addrs, to_names, cc_addrs, cc_names,
                reply_to, subject, list_id, list_unsubscribe_present,
                multipart_mixed, spf_pass, dkim_pass, dmarc_pass, is_sent, gate_verdict,
                precedence, auto_submitted, list_headers_present)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (mid, tid, ms, json.dumps(label_ids), msg.get("sizeEstimate") or 0,
             sanitize_addr(from_addrs[0]) if from_addrs else None,
             cleared.get("from_name") if cleared else None,
             addr_json(to_addrs), cleared.get("to_names") if cleared else None,
             addr_json(cc_addrs), cleared.get("cc_names") if cleared else None,
             cleared.get("reply_to") if cleared else None,
             cleared.get("subject") if cleared else None,
             cleared.get("list_id") if cleared else None,
             1 if headers.get("List-Unsubscribe") else 0,
             1 if "mixed" in ct.lower() else 0,
             spf, dkim, dmarc, is_sent, verdict,
             norm_machine_header(cleared.get("precedence"), 20) if cleared else None,
             norm_machine_header(cleared.get("auto_submitted"), 30) if cleared else None,
             lhp))

    stage_fields(stranger, mid, "message", write)
    return ms


def sanitize_addr(addr):
    """Addresses: scrub only (INTAKE §1) — sanitize(), never the reader."""
    return sanitize.sanitize(addr or "")


def pull_email(db, months, max_threads, after=None, before=None):
    # labels
    ldata = with_retries(db, "labels.list", "labels.list", email_fetch.labels_list)
    for lab in (ldata or {}).get("labels", []):
        db.execute("INSERT OR REPLACE INTO labels(id, name, type) VALUES(?,?,?)",
                   (lab.get("id"), lab.get("name"), lab.get("type")))
    db.commit()

    stored_ids = {r[0] for r in db.execute("SELECT id FROM messages")} # an already-stored message is
    # never judged again (slice W item C): loaded once, before the first page
    lo, hi, windowed = window_bounds(months, after, before)
    print(f"[email] paging threads newest-first (metadata only); windowed={windowed}", flush=True)
    prev_newest = None   # newest message date of the previous (in list order) successfully fetched thread
    for page in iter_thread_pages(db, max_threads):
        with concurrent.futures.ThreadPoolExecutor(max_workers=GMAIL_WORKERS) as pool:
            results = list(pool.map(fetch_thread, page))
        newest_seen, stop = [], False
        for tid, (th, err) in zip(page, results):
            if err:
                # NO-TRACE GUARD for failures: the date of a failed thread is unknown, but the list is
                # newest-first, so it cannot be newer than the previous fetched thread. If that one was
                # already older than the window, the failed thread is certainly out of window: no error
                # row, in-memory counter only. Otherwise (date unknown / maybe in window) record the error.
                if windowed and prev_newest is not None and prev_newest < lo:
                    STATS["failed_unrecorded"] = STATS.get("failed_unrecorded", 0) + 1
                else:
                    record_error(db, tid, "threads.get", err)
                continue
            # DATE CHECK FIRST — before store_message / stage_fields, i.e. before the sentinel gate
            # (the gate only ever sees what was staged, at flush_pending).
            dated = []
            for msg in (th or {}).get("messages") or []:
                try:
                    ms = int(msg.get("internalDate") or 0)
                except (TypeError, ValueError):
                    ms = 0
                dated.append((msg, ms))
            newest = max((ms for _m, ms in dated), default=0)
            prev_newest = newest
            newest_seen.append(newest)
            keep = [(m, ms) for m, ms in dated if in_window(ms, lo, hi)] if windowed else dated
            if windowed and not keep:
                STATS["threads_out_of_window"] = STATS.get("threads_out_of_window", 0) + 1
                continue   # leaves no trace: no thread row, no message row, nothing staged
            fresh = [(m, ms) for m, ms in keep if (m.get("id") or "") not in stored_ids]
            if len(fresh) != len(keep):
                STATS["already_stored"] = STATS.get("already_stored", 0) + (len(keep) - len(fresh))
            keep = fresh
            if not keep:
                continue # every message of the thread is already stored: nothing staged, nothing judged again
            dates = []
            for msg, _ms in keep:
                dates.append(store_message(db, msg, tid))
                STATS["messages"] += 1
            if dates:
                db.execute("INSERT OR REPLACE INTO threads(id, message_count, first_ms, last_ms) VALUES(?,?,?,?)",
                           (tid, len(dates), min(dates), max(dates)))
                STATS["threads"] += 1
        db.commit()
        if windowed:
            stop = bool(newest_seen) and all(n < lo for n in newest_seen)   # whole fetched page older than --after
        else:
            stop = any(n < lo for n in newest_seen)   # legacy --months behavior
        if stop:
            break
    db.commit()


def list_messages(params):
    """messages.list through the door's one raw call (email_fetch._call: same creds, same read-only login).
    The door has no list_messages wrapper and the plugin's door is not edited from here."""
    return email_fetch._call(["messages", "list"], dict({"userId": "me"}, **params))


def list_inbox_ids(db):
    """Every message id carrying INBOX: labelIds=["INBOX"] ONLY, no q, paginated. Stops the run with the
    exact error if the listing is refused (no other listing method is tried)."""
    ids, token, n = [], None, 0
    while True:
        params = {"labelIds": ["INBOX"], "maxResults": 500}
        if token:
            params["pageToken"] = token
        data = with_retries(db, f"messages.list p{n}", "messages.list", list_messages, params)
        n += 1
        if data is None:
            err = db.execute("SELECT error FROM errors WHERE kind='messages.list' ORDER BY rowid DESC LIMIT 1").fetchone()
            raise SystemExit(f"STOP: messages.list labelIds=INBOX failed: {err[0] if err else 'unknown'}")
        ids += [(m.get("id"), m.get("threadId")) for m in data.get("messages", []) if m.get("id")]
        token = data.get("nextPageToken")
        if not token:
            return ids


def list_ids_with_label(db, label_id):
    """Every message id carrying one label: labelIds=[label] ONLY, no q, paginated, ids only (no text)."""
    ids, token, n = set(), None, 0
    while True:
        params = {"labelIds": [label_id], "maxResults": 500}
        if token:
            params["pageToken"] = token
        data = with_retries(db, f"messages.list {label_id} p{n}", "messages.list", list_messages, params)
        n += 1
        if data is None:
            raise SystemExit(f"STOP: messages.list labelIds={label_id} failed")
        ids |= {m.get("id") for m in data.get("messages", []) if m.get("id")}
        token = data.get("nextPageToken")
        if not token:
            return ids


def label_resync(db):
    """Fast, text-free label refresh (2026-11-13): for INBOX and every user label, list the ids that carry it now,
    and rewrite label_ids on messages already in the store. Only ids are read (no subject, no sender, no body),
    so nothing passes the Sentinel gate and nothing new is stored. Other system labels (UNREAD, CATEGORY_*...)
    are left as they were. Returns (messages_changed, labels_listed)."""
    ldata = with_retries(db, "labels.list", "labels.list", email_fetch.labels_list)
    labs = [(l.get("id"), l.get("name"), l.get("type")) for l in (ldata or {}).get("labels", []) if l.get("id")]
    if not labs:
        raise SystemExit("STOP: labels.list returned nothing")
    for lid, name, typ in labs:
        db.execute("INSERT OR REPLACE INTO labels(id, name, type) VALUES(?,?,?)", (lid, name, typ))
    managed = ["INBOX"] + [lid for lid, _n, typ in labs if typ == "user"]
    carry = {}
    for lid in managed:
        for mid in list_ids_with_label(db, lid):
            carry.setdefault(mid, set()).add(lid)
    managed_set = set(managed)
    changed = 0
    for mid, lj in db.execute("SELECT id, label_ids FROM messages").fetchall():
        try:
            old = json.loads(lj) if lj else []
        except ValueError:
            old = []
        new = sorted([l for l in old if l not in managed_set] + sorted(carry.get(mid, set())))
        if sorted(old) != new:
            db.execute("UPDATE messages SET label_ids=? WHERE id=?", (json.dumps(new), mid))
            changed += 1
    db.execute("INSERT OR REPLACE INTO source_state(source, last_success_at, rows) VALUES(?,?,?)",
               ("labels", now_iso(), changed))
    db.commit()
    STATS["label_resync_changed"] = changed
    STATS["label_resync_labels"] = len(managed)
    print(f"[email] label resync: labels={len(managed)} messages_changed={changed}", flush=True)
    return changed, len(managed)


def pull_inbox_backfill(db, max_threads):
    ldata = with_retries(db, "labels.list", "labels.list", email_fetch.labels_list)
    for lab in (ldata or {}).get("labels", []):
        db.execute("INSERT OR REPLACE INTO labels(id, name, type) VALUES(?,?,?)",
                   (lab.get("id"), lab.get("name"), lab.get("type")))
    db.commit()
    listed = list_inbox_ids(db)
    known = {r[0] for r in db.execute("SELECT id FROM messages")}
    new = [(m, t) for m, t in listed if m not in known]
    # Report mail the store still thinks is in INBOX but Gmail no longer lists there (moved by the mover / filters /
    # by hand); fix it with --label-resync.
    listed_ids = {m for m, _t in listed}
    stale = [(r[0], r[1]) for r in db.execute(
        "SELECT id, thread_id FROM messages WHERE EXISTS (SELECT 1 FROM json_each(CASE WHEN json_valid(label_ids) "
        "THEN label_ids ELSE '[]' END) WHERE value='INBOX')") if r[0] not in listed_ids]
    STATS["inbox_stale_messages"] = len(stale)
    # Stale threads are NOT re-fetched here (that re-gated ~660 unchanged threads through the AI reader: far too
    # slow). Run --label-resync instead: ids only, no text, minutes.
    tids = list(dict.fromkeys(t for _m, t in new if t))[:max_threads]
    STATS["inbox_listed"] = len(listed)
    STATS["inbox_already_known"] = len(listed) - len(new)
    STATS["inbox_new_messages"] = len(new)
    STATS["inbox_threads_to_fetch"] = len(tids)
    print(f"[email] inbox backfill: listed={len(listed)} known={len(listed) - len(new)} "
          f"new={len(new)} stale_inbox={len(stale)} threads_to_fetch={len(tids)}", flush=True)
    for i in range(0, len(tids), 200):
        page = tids[i:i + 200]
        with concurrent.futures.ThreadPoolExecutor(max_workers=GMAIL_WORKERS) as pool:
            results = list(pool.map(fetch_thread, page))
        for tid, (th, err) in zip(page, results):
            if err:
                record_error(db, tid, "threads.get", err)
                continue
            dates = []
            for msg in (th or {}).get("messages") or []:
                dates.append(store_message(db, msg, tid))
                STATS["messages"] += 1
            if dates:
                db.execute("INSERT OR REPLACE INTO threads(id, message_count, first_ms, last_ms) VALUES(?,?,?,?)",
                           (tid, len(dates), min(dates), max(dates)))
                STATS["threads"] += 1
        db.commit()


def _clean_str(v):
    return sanitize.sanitize(v) if isinstance(v, str) else v


def _clean_full(v):
    """Like _clean_str but UNCAPPED. sanitize()'s default max_len is 200 chars (DEFAULT_FIELD_CAP): right for
    a stranger's subject line, wrong for the owner's own Gmail filter, whose `from` list can run to thousands
    of chars. Still scrubbed (entities, unsafe unicode, control chars); never clipped."""
    return sanitize.sanitize(v, max_len=sanitize.NO_CAP) if isinstance(v, str) else v


def _clean_list(vs):
    return [_clean_str(x) for x in vs if isinstance(x, str)]


FILTER_CRITERIA_KEYS = ("from", "to", "subject", "query", "negatedQuery", "hasAttachment",
                        "excludeChats", "size", "sizeComparison")
FILTER_ACTION_KEYS = ("addLabelIds", "removeLabelIds", "forward")


def store_filters(db, api_json):
    """Store Gmail filters from ALREADY-FETCHED users.settings.filters.list JSON ({"filter": [...]}).
    Contract fields only (id, criteria, action); every string value goes through sanitize(). No Google call.
    Returns the number of filters stored."""
    n = 0
    for f in (api_json or {}).get("filter") or []:
        fid = f.get("id")
        if not fid:
            continue
        crit = {k: _clean_full(v) for k, v in (f.get("criteria") or {}).items() if k in FILTER_CRITERIA_KEYS}
        act = {}
        for k, v in (f.get("action") or {}).items():
            if k in FILTER_ACTION_KEYS:
                act[k] = [_clean_full(x) for x in v if isinstance(x, str)] if isinstance(v, list) else _clean_full(v)
        db.execute("INSERT OR REPLACE INTO filters(id, criteria_json, action_json) VALUES(?,?,?)",
                   (_clean_full(str(fid)), json.dumps(crit, ensure_ascii=False, sort_keys=True),
                    json.dumps(act, ensure_ascii=False, sort_keys=True)))
        n += 1
    db.commit()
    return n


def store_contacts(db, connections_json, groups_json):
    """Store contacts from ALREADY-FETCHED People API JSON: people.connections.list ({"connections": [...]})
    and contactGroups.list ({"contactGroups": [...]}). Keeps ONLY lowercased email addresses and contact-group
    NAMES; names, phones, notes, everything else is dropped. No Google call. Returns the number stored."""
    gname = {}
    for g in (groups_json or {}).get("contactGroups") or []:
        if g.get("resourceName") and g.get("name"):
            gname[g["resourceName"]] = _clean_str(g["name"])
    n = 0
    for c in (connections_json or {}).get("connections") or []:
        rn = c.get("resourceName")
        if not rn:
            continue
        emails = sorted({_clean_str(e["value"]).lower() for e in c.get("emailAddresses") or []
                         if isinstance(e.get("value"), str) and e["value"].strip()})
        groups = []
        for m in c.get("memberships") or []:
            ref = (m.get("contactGroupMembership") or {}).get("contactGroupResourceName")
            if ref in gname and gname[ref] not in groups:
                groups.append(gname[ref])
        db.execute("INSERT OR REPLACE INTO contacts(resource_name, emails_json, groups_json) VALUES(?,?,?)",
                   (_clean_str(str(rn)), json.dumps(emails, ensure_ascii=False),
                    json.dumps(sorted(groups), ensure_ascii=False)))
        n += 1
    db.commit()
    return n


# ───────────────────────── calendar & tasks (isolate-mode doors + scratch lane) ─────────────────────────

def run_door(db, kind, script, params):
    """Run safe_calendar.py / safe_tasks.py in isolate mode; retry twice; return parsed stdout JSON or None."""
    for attempt in range(RETRIES + 1):
        gate()
        try:
            proc = subprocess.run([sys.executable, script, json.dumps(params)],
                                  capture_output=True, text=True, timeout=180,
                                  env=os.environ.copy())
        except Exception as e:  # noqa: BLE001
            proc = None
            err = str(e)
        if proc is not None:
            if proc.returncode in (0, 1):   # 1 = FLAGGED by the door's own scan — output is still isolate-mode structure
                try:
                    return json.loads(proc.stdout[proc.stdout.find("{"):])
                except Exception as e:  # noqa: BLE001
                    err = f"json parse: {e}"
            else:
                err = (proc.stderr.strip().splitlines() or ["?"])[-1][:300]
        time.sleep(BACKOFF_S * (attempt + 1))
    record_error(db, params.get("tasklist") or params.get("calendarId") or kind, kind, err)
    return None


def parse_scratch_blocks(db, scratch_path, kind):
    """Read a door's _reader_scratch file: blocks 'EVENT/TASK <id>' then 'NAME: value' lines.
    Pure parse — returns {id: {name: raw_value}}; staging/judging happens via stage_fields/flush."""
    out = {}
    try:
        text = open(scratch_path, encoding="utf-8", errors="replace").read()
    except OSError as e:
        record_error(db, scratch_path, f"{kind}.scratch", e)
        return out
    blocks = re.split(r"\n\n---\n\n|\n\n", text)
    for block in blocks:
        if not block.strip():
            continue
        lines = block.splitlines()
        m = re.match(r"^(EVENT|TASK)\s+(\S+)", lines[0].strip())
        if not m:
            continue
        item_id = m.group(2)
        fields = {}
        for line in lines[1:]:
            fm = re.match(r"^([A-Z_]+):\s*(.*)$", line)
            if fm:
                fields[fm.group(1).lower()] = fm.group(2)
        out[item_id] = fields
    try:
        os.remove(scratch_path)   # the raw scratch file is never stored — use it, then drop it
    except OSError:
        pass
    return out


CALENDAR_AHEAD_DAYS = 95   # about three months ahead


def pull_calendar(db, months_back):
    time_min = (clock.now()
                - datetime.timedelta(days=months_back * 30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    time_max = (clock.now()  # World Model Trial Step 3: the window reaches 2 months ahead (was 31 days)
                + datetime.timedelta(days=CALENDAR_AHEAD_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    token = None
    while True:
        params = {"calendarId": "primary", "timeMin": time_min, "timeMax": time_max,
                  "singleEvents": True, "orderBy": "startTime", "maxResults": 250}
        if token:
            params["pageToken"] = token
        data = run_door(db, "calendar", rig_env.SAFE_CALENDAR, params)
        if not data:
            break
        scratch = {}
        if data.get("_reader_scratch") and os.path.isfile(data["_reader_scratch"]):
            scratch = parse_scratch_blocks(db, data["_reader_scratch"], "calendar_event")
        for ev in data.get("items") or []:
            eid = ev.get("id") or ""
            if REGATE_IDS is not None and f"calendar_event:{eid}" not in REGATE_IDS:
                continue
            start = (ev.get("start") or {}).get("dateTime") or (ev.get("start") or {}).get("date")
            end = (ev.get("end") or {}).get("dateTime") or (ev.get("end") or {}).get("date")
            all_day = 1 if ((ev.get("start") or {}).get("date") and not (ev.get("start") or {}).get("dateTime")) else 0
            organizer = ev.get("organizer") or {}
            att_emails = json.dumps([sanitize_addr(a.get("email") or "")
                                     for a in (ev.get("attendees") or []) if a.get("email")],
                                    ensure_ascii=False)

            def write(cleared, verdict, _reason, ev_status=ev.get("status"),
                      eid=eid, start=start, end=end, all_day=all_day,
                      organizer=organizer, att_emails=att_emails):
                ok = verdict in ("NONE", "BENIGN", "OWNER-OVERRIDE") and cleared
                db.execute("""INSERT OR REPLACE INTO calendar_events(id, start, end, all_day, status,
                    organizer_email, attendee_emails, summary, location, description, gate_verdict)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                           (eid, start, end, all_day, ev_status,
                            sanitize_addr(organizer.get("email") or "") or None,
                            att_emails,
                            cleared.get("summary") if ok else None,
                            cleared.get("location") if ok else None,
                            cleared.get("description") if ok else None,
                            verdict))
                STATS["calendar_events"] += 1

            stage_fields(scratch.get(eid) or {}, f"calendar_event:{eid}", "calendar_event", write)
        db.commit()
        token = data.get("nextPageToken")
        if not token:
            break


def pull_tasks(db):
    gate()
    tl = subprocess.run(["gws", "tasks", "tasklists", "list", "--params", "{}"],
                        capture_output=True, text=True, timeout=60, env=os.environ.copy())
    lists = []
    if tl.returncode == 0:
        try:
            lists = json.loads(tl.stdout[tl.stdout.find("{"):]).get("items") or []
        except Exception as e:  # noqa: BLE001
            record_error(db, "tasklists.list", "tasks.tasklists", e)
    else:
        record_error(db, "tasklists.list", "tasks.tasklists", (tl.stderr or "?")[-300:])
    for lst in lists:
        lid = lst.get("id")
        token = None
        while True:
            params = {"tasklist": lid, "showCompleted": True, "showHidden": True, "maxResults": 100}
            if token:
                params["pageToken"] = token
            data = run_door(db, "tasks", rig_env.SAFE_TASKS, params)
            if not data:
                break
            scratch = {}
            if data.get("_reader_scratch") and os.path.isfile(data["_reader_scratch"]):
                scratch = parse_scratch_blocks(db, data["_reader_scratch"], "task")
            for t in data.get("items") or []:
                tid = t.get("id") or ""
                if REGATE_IDS is not None and f"task:{tid}" not in REGATE_IDS:
                    continue

                def write(cleared, verdict, _reason, tid=tid, lid=lid, t=t):
                    ok = verdict in ("NONE", "BENIGN", "OWNER-OVERRIDE") and cleared
                    db.execute("""INSERT OR REPLACE INTO tasks(id, list_id, title, notes, status,
                        due, completed, updated, gate_verdict) VALUES(?,?,?,?,?,?,?,?,?)""",
                               (tid, lid, cleared.get("title") if ok else None,
                                cleared.get("notes") if ok else None,
                                t.get("status"), t.get("due"), t.get("completed"), t.get("updated"),
                                verdict))
                    STATS["tasks"] += 1

                stage_fields(scratch.get(tid) or {}, f"task:{tid}", "task", write)
            db.commit()
            token = data.get("nextPageToken")
            if not token:
                break


# ───────────────────────── filters & contacts (2.0b: rig login reads them directly, read-only scopes) ─────────────────────────
# Same pattern as the tasklists call above: a direct `gws` READ with the rig env (rig_env.apply_to_this_process
# has already run); read-only scopes enforced by Google (gmail.settings.filters.readonly, contacts.readonly).
# The owner approved 2026-11-10. Filter criteria, forward address and contact-group names go through the same
# Sentinel lane (stage_fields -> flush_pending); contact email addresses get sanitize() only, exactly like
# message addresses. Contacts = the address book (people.connections), NOT otherContacts.

FILTER_TEXT_KEYS = ("from", "to", "subject", "query", "negatedQuery")
FILTERS_LIST_ARGV = ["gmail", "users", "settings", "filters", "list"]          # read-only
GROUPS_LIST_ARGV = ["people", "contactGroups", "list"]                          # read-only
CONNECTIONS_LIST_ARGV = ["people", "people", "connections", "list"]             # read-only


def gws_read(db, kind, argv, params):
    """One read-only gws call with the rig env, retried. Returns parsed JSON or None (error recorded)."""
    err = "?"
    for attempt in range(RETRIES + 1):
        gate()
        try:
            proc = subprocess.run(["gws", *argv, "--params", json.dumps(params)],
                                  capture_output=True, text=True, timeout=120, env=os.environ.copy())
        except Exception as e:  # noqa: BLE001
            err = str(e)
        else:
            if proc.returncode == 0:
                try:
                    return json.loads(proc.stdout[proc.stdout.find("{"):])
                except Exception as e:  # noqa: BLE001
                    err = f"bad json: {e}"
            else:
                err = (proc.stderr or proc.stdout or "?")[-300:]
        time.sleep(BACKOFF_S * (attempt + 1))
    record_error(db, kind, kind, err)
    return None


def pull_filters(db):
    data = gws_read(db, "gmail.filters", FILTERS_LIST_ARGV, {"userId": "me"})
    if data is None:
        return
    for f in data.get("filter") or []:
        fid = f.get("id")
        if not fid:
            continue
        crit = f.get("criteria") or {}
        act = f.get("action") or {}
        if act.get("forward"):
            STATS["filters_forwarding"] = STATS.get("filters_forwarding", 0) + 1
        fields = {k: crit[k] for k in FILTER_TEXT_KEYS if isinstance(crit.get(k), str) and crit.get(k)}
        if isinstance(act.get("forward"), str) and act["forward"]:
            fields["forward"] = act["forward"]

        def write(cleared, verdict, _reason, f=f, fid=fid):
            if cleared is None:   # quarantined: keep the id and the non-text label actions only
                act_ids = {k: v for k, v in (f.get("action") or {}).items()
                           if k in ("addLabelIds", "removeLabelIds")}
                db.execute("INSERT OR REPLACE INTO filters(id, criteria_json, action_json) VALUES(?,?,?)",
                           (str(fid), json.dumps({"_quarantined": verdict}), json.dumps(act_ids, sort_keys=True)))
            else:
                f2 = {"id": fid, "criteria": dict(f.get("criteria") or {}), "action": dict(f.get("action") or {})}
                for k, v in cleared.items():
                    if k == "forward":
                        f2["action"]["forward"] = v
                    else:
                        f2["criteria"][k] = v
                store_filters(db, {"filter": [f2]})
            STATS["filters"] = STATS.get("filters", 0) + 1

        stage_fields(fields, f"filter:{fid}", "filter", write)


def _paged(db, kind, argv, params, key):
    out, token = [], None
    while True:
        p = dict(params)
        if token:
            p["pageToken"] = token
        data = gws_read(db, kind, argv, p)
        if data is None:
            return None
        out.extend(data.get(key) or [])
        token = data.get("nextPageToken")
        if not token:
            return out


def pull_contacts(db):
    groups = _paged(db, "people.contactGroups", GROUPS_LIST_ARGV, {"pageSize": 1000}, "contactGroups")
    if groups is None:
        return   # no partial contacts without group names; error recorded
    conns = _paged(db, "people.connections", CONNECTIONS_LIST_ARGV,
                   {"resourceName": "people/me", "personFields": "emailAddresses,memberships",
                    "pageSize": 1000}, "connections")
    if conns is None:
        return
    cleared_names = {}
    for g in groups:
        rn, name = g.get("resourceName"), g.get("name")
        if not rn or not name:
            continue

        def write(cleared, _verdict, _reason, rn=rn):
            if cleared is not None and cleared.get("name"):
                cleared_names[rn] = cleared["name"]

        stage_fields({"name": name}, f"contact_group:{rn}", "contact_group", write)

    def write_contacts(_cleared, _verdict, _reason):
        # flush_pending writes in staging order, so every group name above has been judged by now;
        # a quarantined group name is absent from cleared_names and is never stored.
        gj = {"contactGroups": [{"resourceName": rn, "name": n} for rn, n in cleared_names.items()]}
        STATS["contacts"] = STATS.get("contacts", 0) + store_contacts(db, {"connections": conns}, gj)

    stage_fields({}, "contacts:store", "contacts", write_contacts)


# ───────────────────────── source freshness (calendar/tasks: fetch once per 24h under auto) ─────────────────────────

FRESH_HOURS = 18   # under 24h so a daily run never skips calendar/tasks for being 23h59m old


def fetched_recently(db, source, hours=FRESH_HOURS):
    """True if `source` was fetched successfully (recorded in source_state) within the last `hours`."""
    row = db.execute("SELECT last_success_at FROM source_state WHERE source=?", (source,)).fetchone()
    if not row or not row[0]:
        return False
    try:
        last = datetime.datetime.fromisoformat(row[0])
    except ValueError:
        return False
    return (clock.now() - last) < datetime.timedelta(hours=hours)


def pull_source_if_needed(db, source, mode, fn):
    """Run one calendar/tasks pull under its mode (auto|always|never), recording last-success time
    ONLY if the pull added no new error rows (a partial failure is not a success)."""
    if mode == "never":
        print(f"[pull] skipping {source}: mode=never")
        return
    if mode == "auto" and fetched_recently(db, source):
        print(f"[pull] skipping {source}: fetched successfully within the last {FRESH_HOURS}h (mode=auto)")
        return
    err_before = db.execute("SELECT COUNT(*) FROM errors").fetchone()[0]
    key = {"calendar": "calendar_events"}.get(source, source)
    rows_before = STATS.get(key, 0)
    fn()
    rows = STATS.get(key, 0) - rows_before
    err_after = db.execute("SELECT COUNT(*) FROM errors").fetchone()[0]
    if err_after > err_before:
        print(f"[pull] {source}: pulled {rows} row(s) but {err_after - err_before} error(s) recorded — "
              f"NOT marking source fresh (will retry next run)")
        return
    db.execute("INSERT OR REPLACE INTO source_state(source, last_success_at, rows) VALUES(?,?,?)",
        (source, now_iso(), rows))
    db.commit()
    print(f"[pull] {source}: pulled {rows} row(s), marked fresh at {now_iso()}")


# ───────────────────────── planted mode (task 1.5 hook — kept simple) ─────────────────────────

def run_planted(db, path):
    """Run planted.json items through the SAME lane (phrase + batched AI); verdicts (never text)
    into planted_results, with the flagging layer (phrase/ai/both) in reason.
    Quarantine rows from a planted run go to planted_quarantine — NEVER the real quarantine table.
    Any planted rows already sitting in `quarantine` from older runs (item ids match planted.json)
    are deleted here, and the count printed."""
    global QUAR_TABLE
    QUAR_TABLE = "planted_quarantine"
    with open(path, encoding="utf-8") as fh:
        items = json.load(fh)
    for it in items:
        fields = it.get("fields") or {}

        def write(cleared, verdict, reason, it=it):
            db.execute("""INSERT OR REPLACE INTO planted_results(item_id, kind, verdict, expect, reason, at)
                VALUES(?,?,?,?,?,?)""",
                       (str(it.get("id")), it.get("kind") or "message",
                        verdict, str(it.get("expect") or ""),
                        str(reason)[:300], now_iso()))

        stage_fields(fields, str(it.get("id")), it.get("kind") or "message", write)
    flush_pending(db)
    planted_ids = [str(it.get("id")) for it in items if it.get("id")]
    if planted_ids:
        qmarks = ",".join("?" * len(planted_ids))
        cur = db.execute(f"DELETE FROM quarantine WHERE item_id IN ({qmarks})", planted_ids)
        db.commit()
        print(f"[planted] removed {cur.rowcount} old planted row(s) from the real quarantine table")
    db.commit()


# ───────────────────────── pause: loud refusal + the one sanctioned unpause path ─────────────────────────

def pause_refusal(unit, db=None):
    """Loud stderr message for a paused rig; best-effort row in `errors`. Returns EXIT_PAUSED."""
    pf = os.environ.get("SENTINEL_PAUSE_FILE", "?")
    print(f"\nSTOP: unit {unit!r} is PAUSED (a REAL-ATTACK verdict paused it). No further Google calls.\n"
          f"  pause file: {pf}\n"
          f"  to unpause (after a human has looked): python pull.py --unpause {unit} --why \"<reason>\"",
          file=sys.stderr, flush=True)
    if db is not None:
        try:
            record_error(db, f"unit:{unit}", "paused", f"run stopped: unit paused ({pf})")
        except Exception as e:  # noqa: BLE001 — the refusal must not depend on the db
            print("  (could not record the pause in the errors table: %s: %s)" % (type(e).__name__, e), file=sys.stderr, flush=True)
    return EXIT_PAUSED


def unpause(unit, why):
    """Remove `email:<unit>` from the REAL rig pause file, after the operator retypes the unit name at a TTY.
    Needs no Google and no door. The log line is appended BEFORE the pause file is rewritten."""
    rig_env.apply_to_this_process(planted=False)
    pf = os.environ["SENTINEL_PAUSE_FILE"]
    target = f"email:{unit}"
    try:
        with open(pf, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines(keepends=True)
    except OSError:
        lines = []
    hits = [ln for ln in lines if ln.strip() == target]
    if not hits:
        print(f"unit {unit!r} is not paused ({pf}); nothing to do.")
        return 0
    if not sys.stdin.isatty():
        print("REFUSED: --unpause needs an interactive terminal (stdin is not a TTY).", file=sys.stderr)
        return 1
    typed = input(f"Unit {unit!r} was paused by a REAL-ATTACK verdict. Type the unit name to confirm unpause: ")
    if typed.strip() != unit:
        print("REFUSED: typed name does not match; pause file unchanged.", file=sys.stderr)
        return 1
    log = os.path.join(os.path.dirname(os.path.abspath(pf)), "sentinel-unpause-log.jsonl")
    entry = {"ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "unit": unit,
             "line": hits[0], "who": getpass.getuser(), "why": why, "pause_file": pf}
    with open(log, "a", encoding="utf-8") as fh:   # append-only; never deleted or truncated
        fh.write(json.dumps(entry) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    tmp = f"{pf}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.writelines(ln for ln in lines if ln.strip() != target)
    os.replace(tmp, pf)
    print(f"unpaused {unit!r}; logged to {log}")
    return 0


# ───────────────────────── main ─────────────────────────

def build_events_step(db):
    """Phase 3 step 3.2: bring the event things in step with calendar_events (code only; no outside call). Idempotent.
    One transaction; a failure rolls back and is LOUD (exit 1), it never leaves half an event."""
    import store_events
    try:
        counts = store_events.build_events(db)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[pull] events: FAILED {type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
    print("[pull] events: " + json.dumps(counts, sort_keys=True))


def build_senders_step(db):
    """Migration 026: tie every sender address to its organization and mark it person / bot / question mark (code only; no outside
    call). Idempotent, one transaction, loud on failure, like the events step."""
    import senders
    try:
        counts = senders.build_senders(db)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[pull] senders: FAILED {type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
    print("[pull] senders: " + json.dumps(counts, sort_keys=True))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=None,
                    help="required unless --after is given")
    ap.add_argument("--after", default=None, help="YYYY-MM-DD inclusive, America/New_York")
    ap.add_argument("--before", default=None, help="YYYY-MM-DD inclusive, America/New_York")
    ap.add_argument("--max-threads", type=int, default=None, help="required (except with --unpause)")
    ap.add_argument("--unpause", default=None, metavar="UNIT",
                    help="remove UNIT from the real pause file (interactive confirm; no Google); needs --why")
    ap.add_argument("--why", default=None, help="reason, logged with --unpause")
    ap.add_argument("--calendar-months", type=int, default=12)
    ap.add_argument("--planted", default=None)
    ap.add_argument("--label-resync", action="store_true",
                    help="read-only, ids only: refresh INBOX and user labels on messages already stored")
    ap.add_argument("--inbox-backfill", action="store_true",
                    help="read-only: list INBOX ids (labelIds only, no q), fetch the ones not in the store")
    ap.add_argument("--calendar", choices=("auto", "always", "never"), default="auto",
                    help="calendar pull mode: auto = skip if fetched successfully in the last 24h")
    ap.add_argument("--tasks", choices=("auto", "always", "never"), default="auto",
                    help="tasks pull mode: auto = skip if fetched successfully in the last 24h")
    ap.add_argument("--filters", choices=("auto", "always", "never"), default="auto",
                    help="Gmail filters pull mode (read-only scope)")
    ap.add_argument("--contacts", choices=("auto", "always", "never"), default="auto",
                    help="contacts pull mode: address book only, emails + group names")
    ap.add_argument("--regate-quarantined", nargs="?", const="", default=None, metavar="SINCE_ISO",
                    help="re-gate ONLY the calendar/task items already in the quarantine table (optionally only rows "
                         "with at >= SINCE_ISO) through the same doors, write their review files, fill reason/detail "
                         "on the existing rows. No new rows, no email, no other items.")
    ap.add_argument("--release-quarantined", default=None, metavar="ID[,ID...]",
                    help="owner-approved release of these quarantined calendar_event:/task: ids: re-gate through the "
                         "doors; clean items are stored as cleared; flagged items only if also named in --override. "
                         "Needs --release-reason. Existing quarantine row is updated to RELEASED (no new row).")
    ap.add_argument("--override", default="", metavar="ID[,ID...]",
                    help="with --release-quarantined: ids stored (sanitized, verdict OWNER-OVERRIDE) even if flagged")
    ap.add_argument("--release-reason", default=None, help="required with --release-quarantined; kept on the row")
    ap.add_argument("--wipe-dedupe-cache", action="store_true",
                    help="delete the reader's dedupe cache (rig-local file; no Google) and exit")
    ap.add_argument("--sources-only", action="store_true",
                    help="calendar/tasks/filters/contacts only: no email pull (no --max-threads/--months needed); "
                         "the sources still follow their own --calendar/--tasks/... modes (default auto)")
    ap.add_argument("--no-dedupe-cache", action="store_true",
                    help="this run re-reads everything: the dedupe cache is neither read nor written")
    ap.add_argument("--no-gate-cache", action="store_true",
                    help="this run re-gates every calendar/task item: the gate cache (unchanged-text "
                         "skip, migration 012) is neither read nor written")
    args = ap.parse_args()
    if args.wipe_dedupe_cache:
        rig_env.apply_to_this_process()
        print(f"[pull] dedupe cache wiped: {batch_reader.wipe_cache()} verdict(s) removed "
              f"({batch_reader.cache_path()})")
        return 0
    global NO_DEDUPE
    NO_DEDUPE = bool(args.no_dedupe_cache)
    global NO_GATE_CACHE
    NO_GATE_CACHE = bool(args.no_gate_cache)
    if args.unpause:
        if not args.why or not args.why.strip():
            ap.error("--unpause requires --why \"<reason>\"")
        return unpause(args.unpause, args.why)
    if args.release_quarantined is not None:
        if not (args.release_reason or "").strip():
            ap.error("--release-quarantined requires --release-reason \"<reason>\"")
        if args.regate_quarantined is not None:
            ap.error("--release-quarantined and --regate-quarantined are exclusive")
    _quar = args.regate_quarantined is not None or args.release_quarantined is not None
    if args.sources_only:
        args.max_threads = args.max_threads or 0
    if args.max_threads is None and not _quar:
        ap.error("--max-threads is required")
    if _quar:
        args.max_threads = args.max_threads or 0
    if args.months is None and not _quar and not args.after and not args.planted and not args.inbox_backfill and not args.label_resync and not args.sources_only:
        ap.error("--months is required unless --after is given")
    for d in (args.after, args.before):
        if d:
            try:
                datetime.date.fromisoformat(d)
            except ValueError:
                ap.error(f"bad date {d!r}, want YYYY-MM-DD")

    rig_env.apply_to_this_process(planted=bool(args.planted))   # FIRST — before importing the doors
    sys.path.insert(0, rig_env.EMAIL_DOOR_DIR)
    global email_fetch, sanitize
    import email_fetch  # noqa: E402
    _lt = os.path.join(rig_env.LIFEHACK, "system", "tools")
    if _lt not in sys.path:
        sys.path.insert(0, _lt)
    import sanitize  # noqa: E402

    db = None
    try:
        gate()   # BEFORE any Google call (preflight included); re-checked before every door call below
        if not args.planted:
            if not email_fetch.preflight():
                print("STOP: rig login preflight failed (getProfile did not answer)", file=sys.stderr)
                return 2
        db = open_db()
        return run(args, db)
    except email_fetch.Paused as e:
        return pause_refusal(str(e) or RIG_UNIT, db)


def run(args, db):
    started = now_iso()
    print(f"[pull] db={db_path()} planted={bool(args.planted)}", flush=True)

    if args.regate_quarantined is not None or args.release_quarantined is not None:
        global REGATE_IDS, RELEASE
        found = regate_ids(db, args.regate_quarantined or None)
        if args.release_quarantined is not None:
            want = {x.strip() for x in args.release_quarantined.split(",") if x.strip()}
            found = [(i, k) for i, k in found if i in want]
            RELEASE = {"reason": args.release_reason.strip(),
                       "override": {x.strip() for x in args.override.split(",") if x.strip()} & want}
        REGATE_IDS = {i for i, _ in found}
        print(f"[pull] {'release' if RELEASE else 'regate'}: {len(REGATE_IDS)} quarantined item(s)", flush=True)
        prune_quarantine_files()
        if any(k == "calendar_event" for _, k in found):
            pull_calendar(db, args.calendar_months)
        if any(k == "task" for _, k in found):
            pull_tasks(db)
        flush_pending(db)
    elif args.planted:
        run_planted(db, args.planted)
    elif args.label_resync:
        label_resync(db)
    elif args.inbox_backfill:
        prune_quarantine_files()
        pull_inbox_backfill(db, args.max_threads)
        flush_pending(db)
    else:
        prune_quarantine_files()
        if not args.sources_only:
            pull_email(db, args.months, args.max_threads, args.after, args.before)
            db.execute("INSERT OR REPLACE INTO source_state(source, last_success_at, rows) VALUES(?,?,?)",
                ("envelopes", started, STATS["messages"])) # the fast clock's own watermark (slice W item C)
            db.commit()
        pull_source_if_needed(db, "calendar", args.calendar,
            lambda: pull_calendar(db, args.calendar_months))
        pull_source_if_needed(db, "tasks", args.tasks, lambda: pull_tasks(db))
        pull_source_if_needed(db, "filters", args.filters, lambda: pull_filters(db))
        pull_source_if_needed(db, "contacts", args.contacts, lambda: pull_contacts(db))
        flush_pending(db)   # judge everything staged, THEN write (task 1.5b: batched AI reader)
    db.commit()
    if not (args.planted or args.label_resync or args.inbox_backfill):
        build_events_step(db)   # 3.2: event things from the calendar mirror, under the same database lock this run already holds
        build_senders_step(db)  # senders: organization by domain, person / bot / question mark (after the events: it reads the persons they made)

    finished = now_iso()
    db.execute("INSERT INTO runs(started, finished, args, counts) VALUES(?,?,?,?)",
               (started, finished, json.dumps(vars(args)),
                json.dumps({k: v for k, v in STATS.items()} | {"planted": bool(args.planted)})))
    db.commit()
    print(json.dumps({"started": started, "finished": finished, "stats": STATS}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
