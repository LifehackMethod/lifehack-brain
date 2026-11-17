"""store.py: the front door. The ONLY module other code should use to touch rig.db.

Rules
- Callers never pass SQL. Every read and every write is a named function here; each opens its own short
  connection through db.connect() (pragmas live there) and closes it. Reads open the file read-only.
- Rows come back as plain dicts. Values going in are bound parameters; column names for upserts come from
  a fixed whitelist below, never from the caller.
- Writes do NOT take a backup. Scheduled runs call `backup.py local` (or `gc backup`) BEFORE they start;
  store never backs up on its own, so a write function is always one cheap, predictable transaction.
- The schema itself belongs to migrate.py / migrations/*.sql; store never issues DDL.
- Which file: set_path(p) > env AGE_RIG_DB > db.DEFAULT_PATH. Tests use set_path() on a temp copy.
"""
import contextlib
import json
import os
import sqlite3
import sys

import db

_path = None


def set_path(path):
    """Point the store at another database file (tests). None restores the default."""
    global _path
    _path = path


def db_path():
    return os.path.abspath(os.path.expanduser(_path or os.environ.get("AGE_RIG_DB") or db.DEFAULT_PATH))


@contextlib.contextmanager
def _read():
    conn = db.connect(db_path(), readonly=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@contextlib.contextmanager
def _write():
    conn = db.connect(db_path())
    conn.row_factory = sqlite3.Row
    try:
        with conn:  # one transaction: commit on success, rollback on error
            yield conn
    finally:
        conn.close()


def _rows(sql, args=()):
    with _read() as c:
        return [dict(r) for r in c.execute(sql, args)]


def _one(sql, args=()):
    with _read() as c:
        r = c.execute(sql, args).fetchone()
        return dict(r) if r else None


def _upsert(table, cols, row, key_cols):
    """INSERT OR REPLACE using only whitelisted columns; the key columns must be present."""
    for k in key_cols:
        if row.get(k) is None:
            raise ValueError("%s: missing key column %r" % (table, k))
    unknown = set(row) - set(cols)
    if unknown:
        raise ValueError("%s: unknown column(s) %s" % (table, sorted(unknown)))
    use = [c for c in cols if c in row]
    with _write() as c:
        c.execute('INSERT OR REPLACE INTO %s(%s) VALUES(%s)' % (table, ",".join(use), ",".join("?" * len(use))),
                  [row[k] for k in use])


# ---- the rig's own bookkeeping ------------------------------------------------------------------
def user_version():
    with _read() as c:
        return db.current_version(c)


def journal_mode():
    with _read() as c:
        return c.execute("PRAGMA journal_mode").fetchone()[0]


def table_counts():
    """{table: rows} for every real table."""
    with _read() as c:
        names = [r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {t: c.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0] for t in names}


# events: the rig's diary (at, kind, detail)
def append_event(kind, detail="", at=None):
    """Append one diary line. `at` defaults to now (UTC ISO, seconds). detail dicts are stored as JSON."""
    if not kind:
        raise ValueError("append_event: kind required")
    if not isinstance(detail, str):
        detail = json.dumps(detail, sort_keys=True)
    if at is None:
        import datetime as dt
        at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _write() as c:
        c.execute("INSERT INTO events(at, kind, detail) VALUES(?,?,?)", (at, kind, detail))


def recent_events(n=10, kind=None):
    """Newest first."""
    if kind:
        return _rows("SELECT at, kind, detail FROM events WHERE kind=? ORDER BY at DESC, rowid DESC LIMIT ?", (kind, int(n)))
    return _rows("SELECT at, kind, detail FROM events ORDER BY at DESC, rowid DESC LIMIT ?", (int(n),))


# source_state: when each source last fetched successfully
def get_source_state(source):
    return _one("SELECT source, last_success_at, rows FROM source_state WHERE source=?", (source,))


def all_source_state():
    return _rows("SELECT source, last_success_at, rows FROM source_state ORDER BY source")


def set_source_state(source, last_success_at, rows):
    with _write() as c:
        c.execute("INSERT OR REPLACE INTO source_state(source, last_success_at, rows) VALUES(?,?,?)",
                  (source, last_success_at, rows))


def record_run(started, finished, args, counts):
    """runs: args/counts may be dicts (stored as JSON)."""
    j = lambda v: v if isinstance(v, str) or v is None else json.dumps(v, sort_keys=True)
    with _write() as c:
        c.execute("INSERT INTO runs(started, finished, args, counts) VALUES(?,?,?,?)",
                  (started, finished, j(args), j(counts)))


def recent_runs(n=10):
    return _rows("SELECT started, finished, args, counts FROM runs ORDER BY started DESC, rowid DESC LIMIT ?", (int(n),))


def record_error(item_id, kind, error, at):
    with _write() as c:
        c.execute("INSERT INTO errors(item_id, kind, error, at) VALUES(?,?,?,?)", (item_id, kind, error, at))


def record_quarantine(item_id, kind, verdict, reason, at):
    with _write() as c:
        c.execute("INSERT INTO quarantine(item_id, kind, verdict, reason, at) VALUES(?,?,?,?,?)",
                  (item_id, kind, verdict, reason, at))


# ---- mail: envelope reads -----------------------------------------------------------------------
_MSG_COLS = ["id", "thread_id", "internal_date", "label_ids", "size", "from_addr", "from_name", "to_addrs",
             "to_names", "cc_addrs", "cc_names", "reply_to", "subject", "list_id", "list_unsubscribe_present",
             "multipart_mixed", "spf_pass", "dkim_pass", "dmarc_pass", "is_sent", "gate_verdict", "precedence",
             "auto_submitted", "list_headers_present"]


def messages_between(start_ms, end_ms, include_sent=True):
    """Envelopes with start_ms <= internal_date < end_ms, oldest first."""
    sql = "SELECT %s FROM messages WHERE internal_date >= ? AND internal_date < ?" % ",".join(_MSG_COLS)
    if not include_sent:
        sql += " AND COALESCE(is_sent,0)=0"
    return _rows(sql + " ORDER BY internal_date, id", (int(start_ms), int(end_ms)))


def message_envelope(message_id):
    return _one("SELECT %s FROM messages WHERE id=?" % ",".join(_MSG_COLS), (message_id,))


def thread_messages(thread_id):
    return _rows("SELECT %s FROM messages WHERE thread_id=? ORDER BY internal_date, id" % ",".join(_MSG_COLS), (thread_id,))


def newest_message_ms():
    r = _one("SELECT MAX(internal_date) AS m FROM messages")
    return r["m"] if r else None


def message_count():
    return _one("SELECT COUNT(*) AS n FROM messages")["n"]


def labels():
    return _rows("SELECT id, name, type FROM labels ORDER BY name")


def threads():
    return _rows("SELECT id, message_count, first_ms, last_ms FROM threads ORDER BY last_ms")


def filters():
    return _rows("SELECT id, criteria_json, action_json FROM filters ORDER BY id")


def contacts():
    return _rows("SELECT resource_name, emails_json, groups_json FROM contacts ORDER BY resource_name")


def calendar_events_between(start_iso, end_iso):
    """Events with start >= start_iso and start < end_iso (ISO strings compare lexically)."""
    return _rows("SELECT id, start, end, all_day, status, organizer_email, attendee_emails, summary, location, "
                 "description, gate_verdict FROM calendar_events WHERE start >= ? AND start < ? ORDER BY start, id",
                 (start_iso, end_iso))


def tasks(status=None):
    cols = "id, list_id, title, notes, status, due, completed, updated, gate_verdict"
    if status:
        return _rows("SELECT %s FROM tasks WHERE status=? ORDER BY due, id" % cols, (status,))
    return _rows("SELECT %s FROM tasks ORDER BY due, id" % cols)


def quarantined():
    return _rows("SELECT item_id, kind, verdict, reason, at FROM quarantine ORDER BY at")


# ---- mail: writes (pull.py's job) ---------------------------------------------------------------
def upsert_message(envelope):
    _upsert("messages", _MSG_COLS, envelope, ["id"])


def upsert_thread(row):
    _upsert("threads", ["id", "message_count", "first_ms", "last_ms"], row, ["id"])


def upsert_label(row):
    _upsert("labels", ["id", "name", "type"], row, ["id"])


def upsert_filter(id, criteria_json, action_json):
    _upsert("filters", ["id", "criteria_json", "action_json"],
            {"id": id, "criteria_json": criteria_json, "action_json": action_json}, ["id"])


def upsert_contact(resource_name, emails_json, groups_json):
    _upsert("contacts", ["resource_name", "emails_json", "groups_json"],
            {"resource_name": resource_name, "emails_json": emails_json, "groups_json": groups_json}, ["resource_name"])


def upsert_calendar_event(row):
    _upsert("calendar_events", ["id", "start", "end", "all_day", "status", "organizer_email", "attendee_emails",
                                "summary", "location", "description", "gate_verdict"], row, ["id"])


def upsert_task(row):
    _upsert("tasks", ["id", "list_id", "title", "notes", "status", "due", "completed", "updated", "gate_verdict"],
            row, ["id"])


# ---- world model: reads through the views (the same "effective value" the desks use) -----------
def people():
    return _rows("SELECT * FROM v_people")


def addresses():
    return _rows("SELECT * FROM v_addresses")


def circles():
    return _rows("SELECT * FROM v_circles")


def circle_members():
    return _rows("SELECT * FROM v_circle_members")


def rules(approved_only=False):
    if approved_only:
        return _rows("SELECT * FROM v_rules_v1 WHERE status='approved'")
    return _rows("SELECT * FROM v_rules_v1")


def rule_exceptions():
    return _rows("SELECT * FROM v_rule_exceptions")


def facts():
    return _rows("SELECT * FROM v_facts")


def keywords():
    return _rows("SELECT * FROM v_keywords")


def canon_facts():
    return _rows("SELECT * FROM v_canon_facts")


def relationship_scores():
    return _rows("SELECT * FROM v_relationship_scores ORDER BY score DESC, address")


def relationship_score(address):
    return _one("SELECT * FROM v_relationship_scores WHERE address=?", (address.lower(),))


def wm_meta():
    return {r["key"]: r["value"] for r in _rows("SELECT key, value FROM wm_meta")}


def set_wm_meta(key, value, set_at):
    with _write() as c:
        c.execute("INSERT OR REPLACE INTO wm_meta(key, value, set_at) VALUES(?,?,?)", (key, value, set_at))


def corrections():
    return _rows("SELECT id, at, kind, target, old, new, source, answer_id FROM corrections ORDER BY id")


def append_correction(at, kind, target, old, new, source, answer_id=None):
    """`kind` is checked by the table's CHECK constraint."""
    with _write() as c:
        c.execute("INSERT INTO corrections(at, kind, target, old, new, source, answer_id) VALUES(?,?,?,?,?,?,?)",
                  (at, kind, target, old, new, source, answer_id))


# answer_log: the owner's own words, append-only (the table's triggers refuse UPDATE and DELETE)
def answer_log(limit=None):
    sql = "SELECT * FROM answer_log ORDER BY id"
    if limit:
        return _rows(sql + " LIMIT ?", (int(limit),))
    return _rows(sql)


def append_answer(source_file, round, entry_kind, ordinal, text_verbatim, raw_json, subject_key=None, grade=None,
                  pattern=None, note=None, circle=None, answered_on=None):
    with _write() as c:
        c.execute("INSERT INTO answer_log(source_file, round, entry_kind, ordinal, subject_key, grade, pattern, note, "
                  "circle, text_verbatim, raw_json, answered_on) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                  (source_file, round, entry_kind, ordinal, subject_key, grade, pattern, note, circle,
                   text_verbatim, raw_json, answered_on))


# ---- Step 6: desk-facing reads (Grand Central answers; read-only; each opens its own connection) --
def _to_ms(since):
    """since: epoch ms (int/str digits), or an ISO date/datetime string (naive = UTC). None passes through."""
    if since is None:
        return None
    if isinstance(since, (int, float)) or str(since).strip().isdigit():
        return int(since)
    import datetime as dt
    t = dt.datetime.fromisoformat(str(since).replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return int(t.timestamp() * 1000)


def _label_id(c, label):
    """A label id or a label NAME (case-insensitive) -> id; unknown -> None."""
    r = c.execute("SELECT id FROM labels WHERE id=?", (label,)).fetchone()
    if r:
        return r["id"]
    r = c.execute("SELECT id FROM labels WHERE lower(name)=lower(?) ORDER BY id LIMIT 1", (label,)).fetchone()
    return r["id"] if r else None


def threads_in_label(label, since=None, limit=50):
    """Threads with at least one message carrying `label` (id or name), newest first (as Gmail lists them).
    `since` (ms or ISO) keeps threads whose newest labelled message is at/after it. Label match is an exact element
    of the label_ids JSON array. Returns [{thread_id, newest_ms, message_ids, from_addr, from_name, subject,
    list_unsubscribe_present, label_ids}] (from/subject are of the newest labelled message). Unknown label -> []."""
    since_ms = _to_ms(since)
    with _read() as c:
        lid = _label_id(c, label)
        if lid is None:
            return []
        sql = ("SELECT id, thread_id, internal_date, from_addr, from_name, subject, list_unsubscribe_present, label_ids "
               "FROM messages WHERE EXISTS (SELECT 1 FROM json_each(messages.label_ids) WHERE value=?)")
        args = [lid]
        if since_ms is not None:
            sql, args = sql + " AND internal_date >= ?", args + [since_ms]
        by = {}
        for r in c.execute(sql + " ORDER BY internal_date DESC, id DESC", args):
            t = by.get(r["thread_id"])
            if t is None:
                by[r["thread_id"]] = {"thread_id": r["thread_id"], "newest_ms": r["internal_date"],
                                      "message_ids": [r["id"]], "from_addr": r["from_addr"], "from_name": r["from_name"],
                                      "subject": r["subject"], "list_unsubscribe_present": r["list_unsubscribe_present"],
                                      "label_ids": json.loads(r["label_ids"] or "[]")}
            else:
                t["message_ids"].append(r["id"])
    out = sorted(by.values(), key=lambda t: (-(t["newest_ms"] or 0), t["thread_id"] or ""))
    return out[:int(limit)] if limit else out


def sender_context(address):
    """Who is this sender: person, tier, circles (name/domain/role), relationship score, matching rules (address rule
    or domain rule, with status), first/last seen and message count in the mailbox, active overrides.
    `known` is True when the address maps to a person. Advisory data only."""
    addr = (address or "").strip().lower()
    if "<" in addr and ">" in addr:
        addr = addr[addr.index("<") + 1:addr.index(">")].strip()
    domain = addr.rsplit("@", 1)[1] if "@" in addr else ""
    out = {"address": addr, "domain": domain, "known": False, "person": None, "tier": None, "circles": [], "organizations": [],
           "relationship_score": None, "relationship_basis": None, "rules_matching": [], "first_seen_ms": None,
           "last_seen_ms": None, "message_count": 0, "overrides": []}
    with _read() as c:
        # the one model (2.4 reader 2): person, tier, circles and rules come from kg_things / kg_links / kg_facts
        a = c.execute("SELECT p.id, p.name FROM kg_things ad JOIN kg_current_links l ON l.from_id=ad.id AND l.kind='address_of' "
                      "JOIN kg_things p ON p.id=l.to_id AND p.kind='person' WHERE ad.kind='address' AND ad.key=? "
                      "ORDER BY l.id LIMIT 1", ("address:" + addr,)).fetchone()
        pid = a["id"] if a else None
        if pid is not None:
            t = c.execute("SELECT value FROM kg_current_facts WHERE thing_id=? AND fact_key='tier' ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
            out.update(known=True, person={"id": pid, "label": a["name"]}, tier=t["value"] if t else None)
            # circles: an old circle thing, or (after migration 021) a `group` organization. `kind` is the circle kind
            # (standing/dated) for an old circle and the organization type for an organization. Nothing else changed.
            out["circles"] = [dict(r) for r in c.execute(
                "SELECT ci.id, ci.name, "
                "COALESCE((SELECT value FROM kg_current_facts WHERE thing_id=ci.id AND fact_key='org_type' ORDER BY id DESC LIMIT 1), "
                "(SELECT value FROM kg_current_facts WHERE thing_id=ci.id AND fact_key='circle_kind' ORDER BY id DESC LIMIT 1)) AS kind, "
                "(SELECT value FROM kg_current_facts WHERE thing_id=ci.id AND fact_key='domain' ORDER BY id DESC LIMIT 1) AS domain, "
                "m.role FROM kg_current_links m JOIN kg_things ci ON ci.id=m.to_id AND (ci.kind='circle' OR (ci.kind='organization' "
                "AND EXISTS(SELECT 1 FROM kg_current_facts g WHERE g.thing_id=ci.id AND g.fact_key='org_type' AND g.value='group'))) "
                "WHERE m.from_id=? AND m.kind='member_of' AND ci.merged_into IS NULL ORDER BY ci.name", (pid,))]
            # every organization he belongs to, of any type (new in 3.1)
            out["organizations"] = [dict(r) for r in c.execute(
                "SELECT ci.id, ci.name, (SELECT value FROM kg_current_facts WHERE thing_id=ci.id AND fact_key='org_type' "
                "ORDER BY id DESC LIMIT 1) AS org_type, m.role FROM kg_current_links m JOIN kg_things ci ON ci.id=m.to_id "
                "AND ci.kind='organization' WHERE m.from_id=? AND m.kind='member_of' ORDER BY ci.name", (pid,))]
        # relationship score: computed standing (Vision 3.7.5), nothing stored; the field names stay
        try:
            import scorecard as sc
            import clock
            mb, cfg = sc.Mailbox.load(c), sc.Config.load()
            st = sc.standing(mb, addr, cfg, int(clock.now().timestamp() * 1000))
            out["relationship_score"], out["relationship_basis"] = st["standing"], "; ".join(st["reasons"])
        except Exception as e:  # noqa: BLE001  (no setup files / no mailbox: advisory data, left empty, and said so)
            print("store: relationship score left empty (%s: %s)" % (type(e).__name__, e), file=sys.stderr)
        out["rules_matching"] = [dict(r) for r in c.execute(
            "SELECT r.id, f_mk.value AS match_kind, tg.name AS match_value, COALESCE(f_sg.value, '') AS subject_glob, f_kl.value AS kind_label, "
            "f_nd.value AS need, f_dm.value AS domain, f_st.value AS status "
            "FROM kg_things r JOIN kg_current_links l ON l.from_id=r.id AND l.kind='applies_to' "
            "JOIN kg_things tg ON tg.id=l.to_id AND ((tg.kind='address' AND tg.key=?) OR (tg.kind='domain' AND tg.key=?)) "
            "LEFT JOIN kg_current_facts f_mk ON f_mk.thing_id=r.id AND f_mk.fact_key='match_kind' "
            "LEFT JOIN kg_current_facts f_sg ON f_sg.thing_id=r.id AND f_sg.fact_key='subject_glob' "
            "LEFT JOIN kg_current_facts f_kl ON f_kl.thing_id=r.id AND f_kl.fact_key='kind_label' "
            "LEFT JOIN kg_current_facts f_nd ON f_nd.thing_id=r.id AND f_nd.fact_key='need' "
            "LEFT JOIN kg_current_facts f_dm ON f_dm.thing_id=r.id AND f_dm.fact_key='domain' "
            "LEFT JOIN kg_current_facts f_st ON f_st.thing_id=r.id AND f_st.fact_key='rule_status' "
            "WHERE r.kind='rule' ORDER BY r.id", ("address:" + addr, "domain:" + domain))]
        m = c.execute("SELECT MIN(internal_date) a, MAX(internal_date) b, COUNT(*) n FROM messages "
                      "WHERE lower(from_addr)=?", (addr,)).fetchone()
        out["first_seen_ms"], out["last_seen_ms"], out["message_count"] = m["a"], m["b"], m["n"]
        import store_meaning as sm  # pins / quiet-untils are facts on the person and rule things (2.4 reader 4)
        out["overrides"] = sm.overrides_on(c, ([pid] if pid is not None else []) + [r["id"] for r in out["rules_matching"]])
    return out


def thread_item_context(thread_id, now=None):
    """Meaning for a thread: per gmail message that has an item row -> item id, status, projects, urgency, history.
    Rolls up to `projects` (unique) and `urgency` (max of the items'; None if none has an opinion).
    Tolerates a DB without items/meaning tables (returns empty lists)."""
    import store_meaning as sm
    out = {"thread_id": thread_id, "items": [], "projects": [], "urgency": None}
    with _read() as c:
        try:
            rows = c.execute("SELECT i.id, i.source_id, i.status, i.due_at FROM items i JOIN item_email e ON e.item_id=i.id "
                             "WHERE e.thread_id=? ORDER BY i.occurred_at, i.id", (thread_id,)).fetchall()
        except sqlite3.OperationalError:
            return out
        seen = {}
        for r in rows:
            projs = []
            for pid in sm.item_projects(c, r["id"]):
                v = sm.project_info(c, pid)
                projs.append(v if v else {"id": pid})
                seen[pid] = projs[-1]
            hist = [dict(h) for h in c.execute("SELECT at, kind, detail, actor FROM item_events WHERE item_id=? "
                                               "ORDER BY at, id", (r["id"],))]
            out["items"].append({"item_id": r["id"], "message_id": r["source_id"], "status": r["status"],
                                 "projects": projs, "urgency": sm.item_urgency(c, r["id"], now), "history": hist})
        out["projects"] = [seen[k] for k in sorted(seen)]
        us = [i["urgency"] for i in out["items"] if i["urgency"] is not None]
        out["urgency"] = max(us) if us else None
    return out


DEFAULT_STALE_MIN = 25 * 60  # one daily pull plus an hour of slack


def freshness(source="gmail", max_age_min=None, now=None):
    """Is Grand Central's picture current? {source, last_success_at, age_min, newest_message_ms, newest_message_at,
    threshold_min, stale, reason}. stale is True when there is no successful pull recorded for `source` or it is
    older than the threshold (arg > env AGE_STALE_MIN > 25h). The newest message date is reported but does not
    decide staleness (a quiet mailbox is not a stale one)."""
    import datetime as dt
    import clock
    thr = max_age_min if max_age_min is not None else float(os.environ.get("AGE_STALE_MIN") or DEFAULT_STALE_MIN)
    now = now or clock.now()
    st = get_source_state(source)
    nm = newest_message_ms()
    out = {"source": source, "last_success_at": st["last_success_at"] if st else None, "age_min": None,
           "newest_message_ms": nm, "newest_message_at": None, "threshold_min": thr, "stale": True, "reason": None}
    if nm is not None:
        out["newest_message_at"] = dt.datetime.fromtimestamp(nm / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not st or not st["last_success_at"]:
        out["reason"] = "no successful %s pull recorded in source_state" % source
        return out
    t = dt.datetime.fromisoformat(st["last_success_at"].replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    out["age_min"] = round((now - t).total_seconds() / 60, 1)
    out["stale"] = out["age_min"] > thr
    out["reason"] = ("last pull %.0f min ago, over the %.0f min threshold" % (out["age_min"], thr)) if out["stale"] else "ok"
    return out


# ---- planning doors: what a planning skill (weekly/daily) reads and answers through. Gmail is never written here. -------
def proposals(kind=None, status="open", limit=None):
    """Queue rows (proposals and questions) as dicts, oldest first. status: open|answered|dismissed|all."""
    import store_meaning as sm
    with _read() as c:
        return sm.proposals_list(c, kind, status, limit)


def answer_proposal(id, answer, decided_by=None):
    """decided_by defaults to the owner's stored id (gc_settings.owner_id()). Record an answer: one kg_answers row (the model's answer path; the old answer_log is no longer written) and the queue row
    closed, in one transaction. Returns {id, kind, subject_ref, answer, decided_by, accepted(True|False|None), proposed_answer,
    answer_log_id (always None now), answer_id (the kg_answers id)}."""
    if decided_by is None:
        import gc_settings
        decided_by = gc_settings.owner_id()
    import store_meaning as sm
    with _write() as c:
        kind0 = c.execute("SELECT kind, subject_ref FROM queue WHERE id=?", (int(id),)).fetchone()
        r = sm.proposal_answer(c, int(id), answer, decided_by)
        if kind0 and kind0[0] == "possible_duplicate" and (r["accepted"] is True or str(answer).strip().lower().replace(",", " ").split()[:1] in (["yes"], ["y"])) and _has_graph(c):
            # his yes to "are these the same?" IS the merge (his word recorded, then carried out, in this one transaction)
            import store_graph as sg
            fold, keep = kind0[1].split("|")[1], kind0[1].split("|")[0]
            c.execute("UPDATE queue SET status='open', answered_at=NULL, answer=NULL WHERE id=?", (int(id),))   # merge_things closes it
            r["answer_id"] = sg.merge_things(c, fold, keep, r["answer"], "gc answer (%s)" % decided_by, queue_id=int(id))["answer_id"]
            return r
        if _has_graph(c):  # also one row in the one-door log (no fact: a yes/no to a proposal carries no decision shape)
            import store_graph as sg
            q = c.execute("SELECT question FROM queue WHERE id=?", (int(id),)).fetchone()[0]
            r["answer_id"] = c.execute("INSERT INTO kg_answers(question,words,asked_by,said_on,queue_id,recorded_at) "
                      "VALUES(?,?,?,?,?,?)", (q, r["answer"], "gc answer (%s)" % decided_by, sg.clock.today().isoformat(),
                                                int(id), sg._ts())).lastrowid
        return r


def expiry_questions(now=None, limit=None):
    """Items past their shelf life, as questions (never actions). Pure read."""
    import store_meaning as sm
    with _read() as c:
        return sm.expiry_questions_list(c, now, limit)


def urgent_items(now=None, limit=20):
    """Open items ranked by computed urgency + overrides (pins up, quiet-until hidden)."""
    import store_meaning as sm
    with _read() as c:
        return sm.urgent_items_list(c, now, limit)


def week_digest(start, end, now=None):
    """One dict to render a week: counts, top urgent, due in window, open proposals by kind, overdue override reviews."""
    import store_meaning as sm
    with _read() as c:
        return sm.week_digest_dict(c, start, end, now)


# ---- the flexible memory (migration 005; cores in store_graph.py) ---------------------------------------
def _has_graph(c):
    return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='kg_answers'").fetchone() is not None


def record_answer(question, words, asked_by, said_on=None, subject_kind=None, subject_name=None, fact_key=None,
                  value=None, true_until=None, words_kind="verbatim", condition=None):
    """THE ONE DOOR for his answers: one decision per call, validated against the allowed words, appended to kg_answers
    and applied as his fact or link, in one transaction. Raises store_graph.Refused on anything not allowed."""
    import store_graph as sg
    with _write() as c:
        return sg.record_answer(c, question, words, asked_by, said_on, subject_kind, subject_name, fact_key, value,
                                true_until, words_kind=words_kind, condition=condition)


def graph_write(fn_name, *a, **k):
    """Code/AI writes to the memory (facts, links, things, scores) by store_graph function name, in one transaction.
    Only these names are allowed; his answers never come this way (use record_answer)."""
    import store_graph as sg
    allowed = {"thing", "assert_fact", "add_link", "set_score", "clear_scores", "copy_legacy", "add_vocab"}
    if fn_name not in allowed:
        raise ValueError("graph_write: %r is not an allowed write" % fn_name)
    with _write() as c:
        return getattr(sg, fn_name)(c, *a, **k)


def merge_things(loser_key, survivor_key, words, asked_by, said_on=None, question=None):
    """Merge two people or two organizations on HIS word (`gc merge`): one transaction, all or nothing (Vision 3.7.4 rule 2)."""
    import store_graph as sg
    with _write() as c:
        return sg.merge_things(c, loser_key, survivor_key, words, asked_by, said_on, question)


def unmerge_things(loser_key, words, asked_by, said_on=None, question=None):
    """Undo a merge from the record, on HIS word (`gc unmerge`)."""
    import store_graph as sg
    with _write() as c:
        return sg.unmerge_things(c, loser_key, words, asked_by, said_on, question)


def propose_merge(keep_key, other_key, why, matters=False):
    """Code may only ASK whether two things are one (a possible_duplicate question). Never merges. Returns the queue id or None."""
    import store_graph as sg
    with _write() as c:
        return sg.propose_merge(c, keep_key, other_key, why, matters)


def graph_read(fn_name, *a, **k):
    """Read-only memory reads by store_graph function name."""
    import store_graph as sg
    allowed = {"thing_by_key", "current_facts", "current_links", "about_sender", "answers", "scores_for", "vocab",
               "his_picture", "legacy_equivalence", "source_refs_with_prefix", "resolve_key"}
    if fn_name not in allowed:
        raise ValueError("graph_read: %r is not an allowed read" % fn_name)
    with _read() as c:
        return getattr(sg, fn_name)(c, *a, **k)


def build_events():
    """3.2: bring the event things in step with the calendar mirror (store_events.build_events), in one transaction.
    The caller holds the shared database lock. Idempotent. Returns the counts."""
    import store_events
    with _write() as c:
        return store_events.build_events(c)


def graph_rebuild_from_answers():
    """Replay kg_answers and report whether his picture came back identical. Returns {same, before, after} counts."""
    import store_graph as sg
    with _write() as c:
        before = sg.his_picture(c)
        sg.rebuild_from_answers(c)
        after = sg.his_picture(c)
    return {"same": before == after, "facts": len(after["facts"]), "links": len(after["links"])}


# ---- confirmations (plan B2 step 6; cores in store_graph.py). His word only: each write is a recorded answer. ----------
def list_suggestions(draft):
    """The draft's suggestions as plain rows for his session (validates the draft; writes nothing)."""
    import store_graph as sg
    with _read() as c:
        return sg.list_suggestions(c, draft)


def record_decisions(draft, decisions, said_on=None):
    """His yes / no / later to each suggestion. Writes ONLY the yeses (one answer, one dated fact each); returns the
    validated snapshot for the caller to save. Refuses everything before writing if any decision is bad."""
    import store_graph as sg
    with _write() as c:
        return sg.record_decisions(c, draft, decisions, said_on)


def check_snapshot(draft, snap):
    import store_graph as sg
    with _read() as c:
        return sg.check_snapshot(c, draft, snap)


def check_unconfirmed():
    """Unconfirmed claims and guesses sitting where only his word belongs (ids and classes, no text)."""
    import store_graph as sg
    with _read() as c:
        return sg.check_unconfirmed(c)


def retract_fact(fact_id, words, asked_by, said_on=None):
    """His retraction of one current fact through the one door. Returns the answer id."""
    import store_graph as sg
    with _write() as c:
        return sg.retract_fact(c, fact_id, words, asked_by, said_on)


def approve_staged(digest, words, asked_by, said_on=None):
    """His yes to one staged filter pair (by sha256). The only writer of an approval. Returns the answer id."""
    import store_graph as sg
    with _write() as c:
        return sg.approve_staged(c, digest, words, asked_by, said_on)


def queue_question(kind, subject_ref, question, proposed_answer=None):
    """Add one open question to the queue unless the same (kind, subject_ref, question) is already open. Returns
    (queue_id, added). For the engine's gap list and for open questions (e.g. unsettled conflicts). Never touches Gmail."""
    import store_meaning as sm
    with _write() as c:
        r = c.execute("SELECT id FROM queue WHERE status='open' AND kind=? AND subject_ref=? AND question=?",
                      (kind, subject_ref, question)).fetchone()
        if r:
            return r[0], False
        return sm.queue_add(c, kind, subject_ref, question, proposed_answer), True


def queue_retire_missing(kind, keep_ids):
    """Dismiss open queue rows of one kind that are not in keep_ids (the engine closing its own gaps). Returns how many."""
    import store_meaning as sm
    with _write() as c:
        return sm.queue_retire_missing(c, kind, keep_ids)


def engine_run():
    """Run the engine (gather, score, stitch, rank, gaps) in ONE transaction: all of it lands or none of it. Needs migration 008."""
    import run as er
    with _write() as c:
        return er.run_con(c)



DEFAULT_LABELS_STALE_MIN = 120


def labels_freshness(max_age_min=None, now=None):
    """Does the memory's picture of Gmail's labels match Gmail recently enough? (plan STEP 4b) Based on the last
    `pull.py --label-resync` (source_state 'labels'). {last_resync_at, age_min, threshold_min, stale, reason}."""
    import datetime as dt
    import clock
    thr = max_age_min if max_age_min is not None else float(os.environ.get("AGE_LABELS_STALE_MIN") or DEFAULT_LABELS_STALE_MIN)
    st = get_source_state("labels")
    out = {"last_resync_at": st["last_success_at"] if st else None, "age_min": None, "threshold_min": thr,
           "stale": True, "reason": None}
    if not st or not st["last_success_at"]:
        out["reason"] = "labels never re-synced: run pull.py --label-resync --max-threads 1"
        return out
    t = dt.datetime.fromisoformat(st["last_success_at"].replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    out["age_min"] = round(((now or clock.now()) - t).total_seconds() / 60, 1)
    out["stale"] = out["age_min"] > thr
    out["reason"] = ("labels last re-synced %.0f min ago, over %.0f: run pull.py --label-resync --max-threads 1"
                     % (out["age_min"], thr)) if out["stale"] else "ok"
    return out


def queue_dismiss(queue_id):
    """Close one open queue row as dismissed (e.g. a picture question merged into another). Never touches Gmail."""
    import store_meaning as sm
    with _write() as c:
        sm.queue_dismiss(c, int(queue_id))
