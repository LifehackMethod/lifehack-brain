"""store_meaning.py: Step 5 functions (projects, notes, overrides, urgency, score rollup, queue, model rebuild).
Tables live in migrations/003_meaning.sql. "Now" always comes from clock.py (AGE_NOW freezes it); urgency takes it as a parameter.
The functions that take `con` are for migrations/tests that already hold a connection. Everything else (the desks, gc) uses
the front-door readers at the bottom of this file, which open their own connection through store.py -> db.connect."""
import datetime as _dt
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import clock  # noqa: E402

LEVELS = ("item", "project", "person", "rule")
TYPES = ("pin", "quiet-until")
# derived (rebuildable-from-answer_log) world-model tables, delete order
DERIVED = ("rule_exceptions", "rules", "circle_members", "addresses", "people", "circles", "facts", "keywords")


def _ts():
    return clock.now().isoformat(timespec="seconds")


def _day(x):
    if x is None:
        return None
    if isinstance(x, _dt.datetime):
        return x.astimezone(_dt.timezone.utc).date()
    if isinstance(x, _dt.date):
        return x
    return _dt.date.fromisoformat(str(x)[:10])


# ---- urgency: computed, never stored ------------------------------------------------------------------
RISE_DAYS = 14   # starts rising 14 days out
FADE_DAYS = 7    # fades to zero 7 days after the due date
FLOOR = 0.1      # urgency of something with a due date still far off


def urgency(due, now=None):
    """0..1. Rises linearly from FLOOR (RISE_DAYS out) to 1.0 on the due day, then fades linearly to 0 over FADE_DAYS.
    due None -> None (no date, no opinion). now: date/datetime/ISO string; default clock.now()."""
    d = _day(due)
    if d is None:
        return None
    n = _day(now) if now is not None else clock.today()
    delta = (d - n).days
    if delta >= RISE_DAYS:
        return FLOOR
    if delta >= 0:
        return round(FLOOR + (1 - FLOOR) * (RISE_DAYS - delta) / RISE_DAYS, 4)
    return round(max(0.0, 1 - (-delta) / FADE_DAYS), 4)


# ---- pins, quiet-until and projects: read from the one model (2.4 reader 4) -----------------------------------
# A pin / quiet-until is a current fact on the thing (fact keys `pin`, `quiet_until`, migration 017), a project is a `project`
# thing, an item belongs to it by a `part_of` link, its due date is the end of its `date_window` fact. The old tables'
# readers survive as *_v1 (version-3 test and the old writers; retired at 2.6): nothing live calls them.
OFF = "off"   # a pin / quiet_until fact whose value is 'off' was ended


def _thing_id(con, level, subject_id):
    """The model thing behind an override level: item ids are keyed 'item:<id>'; project / person / rule ids are thing ids."""
    if level == "item":
        r = con.execute("SELECT id FROM kg_things WHERE key=?", ("item:%d" % int(subject_id),)).fetchone()
        return r[0] if r else None
    return subject_id


def _facts_on(con, thing_id):
    """[(type, until_on or None)] of the current pin / quiet_until facts on one thing (ended ones left out)."""
    if thing_id is None:
        return []
    out = []
    for key, val in con.execute("SELECT fact_key, value FROM kg_current_facts WHERE thing_id=? AND fact_key IN ('pin','quiet_until') "
                                "ORDER BY id", (thing_id,)):
        if val == OFF:
            continue
        out.append(("pin", None) if key == "pin" else ("quiet-until", val))
    return out


def effective_urgency(con, level, subject_id, due=None, now=None):
    """urgency() after overrides: an active pin at this level floors it at 1.0; an active quiet-until still in the future
    (today < until_on) silences it to 0.0. Quiet wins over pin when both are active. Reads the one model."""
    n = _day(now) if now is not None else clock.today()
    rows = _facts_on(con, _thing_id(con, level, subject_id))
    if any(t == "quiet-until" and n < _day(u) for t, u in rows):
        return 0.0
    base = urgency(due, n)
    if any(t == "pin" for t, _ in rows):
        return 1.0
    return base


def project_info(con, project_id):
    """{id, name, due_on, domain, status} of one project thing, or None. due_on = end of its date_window (else the legacy
    'due_on=..;status=..' line); status 'active' unless the legacy line says otherwise."""
    t = con.execute("SELECT id, name FROM kg_things WHERE id=? AND kind='project'", (project_id,)).fetchone()
    if t is None:
        return None
    f = {}
    for k, v in con.execute("SELECT fact_key, value FROM kg_current_facts WHERE thing_id=? AND fact_key IN ('date_window','life_fact','domain') "
                            "ORDER BY id", (project_id,)):
        f[k] = v
    due, status = None, "active"
    if f.get("date_window") and ".." in f["date_window"]:
        due = f["date_window"].split("..", 1)[1].strip()[:10] or None
    lf = f.get("life_fact") or ""
    if lf.startswith("due_on="):
        parts = dict(p.split("=", 1) for p in lf.split(";") if "=" in p)
        due = due or (parts.get("due_on") if parts.get("due_on") not in (None, "None", "") else None)
        status = parts.get("status", "active")
    return {"id": t[0], "name": t[1], "due_on": due, "domain": f.get("domain"), "status": status}


def item_projects(con, item_id):
    """Thing ids of the projects an item is part_of, in id order. Machine guesses (who ai_guess / ai_research) are not read:
    a guess must not move a thing in his urgent list."""
    return [r[0] for r in con.execute(
        "SELECT p.id FROM kg_things i JOIN kg_current_links l ON l.from_id=i.id AND l.kind='part_of' "
        "JOIN kg_things p ON p.id=l.to_id AND p.kind='project' WHERE i.key=? AND l.who IN ('owner','code') ORDER BY p.id", ("item:%d" % int(item_id),))]


def item_urgency(con, item_id, now=None):
    """Urgency of one item: its own due_at, else the earliest due date of its projects; item-level overrides applied."""
    r = con.execute("SELECT due_at FROM items WHERE id=?", (item_id,)).fetchone()
    due = r[0] if r else None
    if not due:
        ds = sorted(d for d in (project_info(con, p)["due_on"] for p in item_projects(con, item_id)) if d)
        due = ds[0] if ds else None
    return effective_urgency(con, "item", item_id, due, now)


def project_urgency(con, now=None):
    """[(project_id, name, due_on, urgency)] for active projects, overrides applied."""
    out = []
    for (pid,) in con.execute("SELECT id FROM kg_things WHERE kind='project' ORDER BY id").fetchall():
        info = project_info(con, pid)
        if info["status"] == "active":
            out.append((pid, info["name"], info["due_on"], effective_urgency(con, "project", pid, info["due_on"], now)))
    return out


def _item_override_ids(con):
    """item id -> [(type, until_on)] for every item with a current pin / quiet_until fact (one query for the whole list)."""
    out = {}
    for key, fk, val in con.execute("SELECT thing_key, fact_key, value FROM kg_current_facts WHERE thing_kind='item' "
                                    "AND fact_key IN ('pin','quiet_until') ORDER BY id"):
        if val == OFF:
            continue
        try:
            iid = int(key.split(":", 1)[1])
        except ValueError:
            continue
        out.setdefault(iid, []).append(("pin", None) if fk == "pin" else ("quiet-until", val))
    return out


def set_override(con, level, subject_id, type_, reason, review_by, until_on=None, said_on=None, asked_by="set_override"):
    """Write a pin or quiet-until into the one model as his word: one kg_answers row (his reason) and the fact on the thing,
    plus the thing's review_by. Returns the pin / quiet_until fact id. type_ 'pin' | 'quiet-until'; until_on for quiet-until."""
    import store_graph as sg
    if type_ not in TYPES or level not in LEVELS:
        raise ValueError("type must be one of %s, level one of %s" % (TYPES, LEVELS))
    if not reason or not str(reason).strip():
        raise ValueError("an override needs a reason")
    if not review_by:
        raise ValueError("an override needs a review_by date")
    _day(review_by)
    if (type_ == "quiet-until") != bool(until_on):
        raise ValueError("quiet-until needs until_on; a pin has none")
    if until_on:
        _day(until_on)
    tid = _thing_id(con, level, subject_id)
    if tid is None:
        tid = sg.thing(con, "item", str(int(subject_id)), created_by="owner")
    kind, key, name = con.execute("SELECT kind, key, name FROM kg_things WHERE id=?", (tid,)).fetchone()
    said_on = said_on or clock.today().isoformat()
    fk, val = ("pin", str(reason).strip()) if type_ == "pin" else ("quiet_until", str(until_on)[:10])
    aid = con.execute("INSERT INTO kg_answers(question,words,asked_by,said_on,subject_key,subject_kind,subject_name,fact_key,value,recorded_at) "
                      "VALUES(?,?,?,?,?,?,?,?,?,?)", ("%s on %s" % (type_, key), str(reason).strip(), asked_by, said_on, key, kind, name, fk, val,
                                                      _ts())).lastrowid
    fid = sg.assert_fact(con, tid, fk, val, "owner", "sure", "answer", str(aid), aid, true_from=said_on)
    sg.assert_fact(con, tid, "review_by", str(review_by)[:10], "owner", "sure", "answer", str(aid), aid, true_from=said_on)
    return fid


def end_override(con, level, subject_id, type_, said_on=None, asked_by="end_override"):
    """End a pin or quiet-until: his word 'off' replaces the fact (the old fact is kept, superseded). Returns the answer id or None."""
    import store_graph as sg
    tid = _thing_id(con, level, subject_id)
    fk = "pin" if type_ == "pin" else "quiet_until"
    if tid is None or not con.execute("SELECT 1 FROM kg_current_facts WHERE thing_id=? AND fact_key=? AND value<>?", (tid, fk, OFF)).fetchone():
        return None
    kind, key, name = con.execute("SELECT kind, key, name FROM kg_things WHERE id=?", (tid,)).fetchone()
    said_on = said_on or clock.today().isoformat()
    aid = con.execute("INSERT INTO kg_answers(question,words,asked_by,said_on,subject_key,subject_kind,subject_name,fact_key,value,recorded_at) "
                      "VALUES(?,?,?,?,?,?,?,?,?,?)", ("end %s on %s" % (type_, key), "off", asked_by, said_on, key, kind, name, fk, OFF, _ts())).lastrowid
    sg.assert_fact(con, tid, fk, OFF, "owner", "sure", "answer", str(aid), aid, true_from=said_on)
    return aid


def overrides_on(con, thing_ids):
    """Current pins / quiet-untils on these things as dicts {id, level, subject_id, type, until_on, reason, review_by} (gc who)."""
    out = []
    for tid in thing_ids:
        rb = con.execute("SELECT value FROM kg_current_facts WHERE thing_id=? AND fact_key='review_by' ORDER BY id DESC LIMIT 1", (tid,)).fetchone()
        for fid, fk, val, kind, key, words in con.execute(
                "SELECT f.id, f.fact_key, f.value, f.thing_kind, f.thing_key, (SELECT a.words FROM kg_answers a WHERE a.id=f.answer_id) "
                "FROM kg_current_facts f WHERE f.thing_id=? AND f.fact_key IN ('pin','quiet_until') ORDER BY f.id", (tid,)):
            if val == OFF:
                continue
            out.append({"id": fid, "level": kind, "subject_id": int(key.split(":", 1)[1]) if kind == "item" else tid,
                        "type": "pin" if fk == "pin" else "quiet-until", "until_on": val if fk == "quiet_until" else None,
                        "reason": words or val if fk == "pin" else (words or ""), "review_by": rb[0] if rb else None})
    return out


def overrides_due_for_review(con, now=None):
    """[(fact id, level, subject_id, type, reason, review_by)] for current pins / quiet-untils whose thing's review_by <= now."""
    n = _day(now) if now is not None else clock.today()
    out = []
    for fid, fk, val, kind, key, tid, words, rb in con.execute(
            "SELECT f.id, f.fact_key, f.value, f.thing_kind, f.thing_key, f.thing_id, "
            "(SELECT a.words FROM kg_answers a WHERE a.id=f.answer_id), "
            "(SELECT r.value FROM kg_current_facts r WHERE r.thing_id=f.thing_id AND r.fact_key='review_by' ORDER BY r.id DESC LIMIT 1) "
            "FROM kg_current_facts f WHERE f.fact_key IN ('pin','quiet_until') ORDER BY f.id").fetchall():
        if val == OFF or not rb or rb > n.isoformat():
            continue
        sid = int(key.split(":", 1)[1]) if kind == "item" else tid
        out.append((fid, kind, sid, "pin" if fk == "pin" else "quiet-until", (words or val) if fk == "pin" else (words or ""), rb))
    out.sort(key=lambda r: (r[5], r[0]))
    return out


# ---- the old-table versions (retired readers; kept for the version-3 test and the old writers, to be dropped at 2.6) ----------
def effective_urgency_v1(con, level, subject_id, due=None, now=None):
    """urgency() after overrides: an active pin at this level floors it at 1.0; an active quiet-until still in the future
    (today < until_on) silences it to 0.0. Quiet wins over pin when both are active."""
    n = _day(now) if now is not None else clock.today()
    rows = con.execute("SELECT type, until_on FROM overrides WHERE level=? AND subject_id=? AND status='active'",
                       (level, subject_id)).fetchall()
    if any(t == "quiet-until" and n < _day(u) for t, u in rows):
        return 0.0
    base = urgency(due, n)
    if any(t == "pin" for t, _ in rows):
        return 1.0
    return base


def item_urgency_v1(con, item_id, now=None):
    """Urgency of one item: its own due_at, else the earliest due date of its projects; item-level overrides applied."""
    r = con.execute("SELECT due_at FROM items WHERE id=?", (item_id,)).fetchone()
    due = r[0] if r else None
    if not due:
        ds = [x[0] for x in con.execute("""SELECT v.due_on FROM item_projects ip JOIN v_projects v ON v.id=ip.project_id
                                           WHERE ip.item_id=? AND v.due_on IS NOT NULL ORDER BY v.due_on""", (item_id,))]
        due = ds[0] if ds else None
    return effective_urgency_v1(con, "item", item_id, due, now)


def project_urgency_v1(con, now=None):
    """[(project_id, name, due_on, urgency)] for active projects, overrides applied."""
    out = []
    for pid, name, due in con.execute("SELECT id, name, due_on FROM v_projects WHERE status='active' ORDER BY id").fetchall():
        out.append((pid, name, due, effective_urgency_v1(con, "project", pid, due, now)))
    return out


# ---- projects ----------------------------------------------------------------------------------------
def project_from_circle(con, circle_id, due_on=None, source=None, answer_id=None):
    """A dated circle is a project: link, don't duplicate. Idempotent. Refuses a standing circle."""
    row = con.execute("SELECT kind FROM v_circles WHERE id=?", (circle_id,)).fetchone()
    if row is None:
        raise ValueError("no such circle %r" % circle_id)
    if row[0] != "dated":
        raise ValueError("circle %r is %r, not dated: not a project" % (circle_id, row[0]))
    con.execute("INSERT OR IGNORE INTO projects(circle_id,due_on,source,answer_id,created_at) VALUES(?,?,?,?,?)",
                (circle_id, due_on, source, answer_id, _ts()))
    if due_on:
        con.execute("UPDATE projects SET due_on=? WHERE circle_id=?", (due_on, circle_id))
    return con.execute("SELECT id FROM projects WHERE circle_id=?", (circle_id,)).fetchone()[0]


def sync_dated_circles(con):
    """Make sure every dated circle has its project row. Returns the number created."""
    n = 0
    for (cid,) in con.execute("SELECT id FROM v_circles WHERE kind='dated'").fetchall():
        if not con.execute("SELECT 1 FROM projects WHERE circle_id=?", (cid,)).fetchone():
            project_from_circle(con, cid, source="sync_dated_circles"); n += 1
    return n


def add_project(con, name, due_on=None, source=None, answer_id=None):
    return con.execute("INSERT INTO projects(name,due_on,source,answer_id,created_at) VALUES(?,?,?,?,?)",
                       (name, due_on, source, answer_id, _ts())).lastrowid


def link_item(con, item_id, project_id, source=None, answer_id=None):
    if not con.execute("SELECT 1 FROM items WHERE id=?", (item_id,)).fetchone():
        raise ValueError("no such item %r" % item_id)
    if not con.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
        raise ValueError("no such project %r" % project_id)
    con.execute("INSERT OR IGNORE INTO item_projects(item_id,project_id,source,answer_id,created_at) VALUES(?,?,?,?,?)",
                (item_id, project_id, source, answer_id, _ts()))


def item_projects_v1(con, item_id):
    return [r[0] for r in con.execute("SELECT project_id FROM item_projects WHERE item_id=? ORDER BY project_id", (item_id,))]


# ---- notes -------------------------------------------------------------------------------------------
def add_note(con, subject_kind, subject_id, body, source=None, answer_id=None):
    return con.execute("INSERT INTO notes(subject_kind,subject_id,body,source,answer_id,created_at) VALUES(?,?,?,?,?,?)",
                       (subject_kind, subject_id, body, source, answer_id, _ts())).lastrowid


def notes_for(con, subject_kind, subject_id):
    return [r[0] for r in con.execute("SELECT body FROM notes WHERE subject_kind=? AND subject_id=? ORDER BY id", (subject_kind, subject_id))]


# ---- overrides ---------------------------------------------------------------------------------------
def add_override(con, level, subject_id, type_, reason, review_by, until_on=None, source=None, answer_id=None):
    """reason and review_by are required (the table refuses blanks too)."""
    if not reason or not str(reason).strip():
        raise ValueError("an override needs a reason")
    if not review_by:
        raise ValueError("an override needs a review_by date")
    _day(review_by)
    if until_on:
        _day(until_on)
    return con.execute("""INSERT INTO overrides(level,subject_id,type,until_on,reason,review_by,source,answer_id,created_at)
        VALUES(?,?,?,?,?,?,?,?,?)""", (level, subject_id, type_, until_on, reason, str(review_by)[:10], source, answer_id, _ts())).lastrowid


def retire_override(con, override_id):
    con.execute("UPDATE overrides SET status='retired', retired_at=? WHERE id=?", (_ts(), override_id))


def overrides_due_for_review_v1(con, now=None):
    n = _day(now) if now is not None else clock.today()
    return [r for r in con.execute("SELECT id, level, subject_id, type, reason, review_by FROM overrides WHERE status='active' AND review_by<=? ORDER BY review_by, id",
                                   (n.isoformat(),))]


# ---- scores ------------------------------------------------------------------------------------------
def person_score(con, person_id):
    r = con.execute("SELECT score FROM v_person_scores WHERE person_id=?", (person_id,)).fetchone()
    return r[0] if r else None


# ---- queue -------------------------------------------------------------------------------------------
def queue_add(con, kind, subject_ref, question, proposed_answer=None):
    return con.execute("INSERT INTO queue(kind,subject_ref,question,proposed_answer,created_at) VALUES(?,?,?,?,?)",
                       (kind, subject_ref, question, proposed_answer, _ts())).lastrowid


def queue_open(con):
    return con.execute("SELECT id,kind,subject_ref,question,proposed_answer FROM queue WHERE status='open' ORDER BY id").fetchall()


def queue_answer(con, queue_id, answer, decided_by=None):
    """Close the queue row with his answer. The words themselves are recorded by the caller through the model's answer path
    (kg_answers, store.answer_proposal); this no longer writes the old answer_log (phase 2 step 2.4, reader 1). Returns None."""
    row = con.execute("SELECT subject_ref, question, status FROM queue WHERE id=?", (queue_id,)).fetchone()
    if row is None:
        raise ValueError("no such queue row %r" % queue_id)
    if row[2] != "open":
        raise ValueError("queue row %r is already %s" % (queue_id, row[2]))
    con.execute("UPDATE queue SET status='answered', answered_at=?, answer=? WHERE id=?", (_ts(), answer, queue_id))
    return None


ENGINE_CLOSED = "engine: no longer found"


def queue_gap(con, subject_ref, question, proposed_answer):
    """The engine's gap list: one open 'gap' row per (subject_ref, question). An open row gets its evidence line refreshed.
    Not re-asked when he answered it, or dismissed it himself (only a row the engine closed may come back). Returns the open
    row's id, or None when it is suppressed."""
    rows = con.execute("SELECT id, status, answer FROM queue WHERE kind='gap' AND subject_ref=? AND question=? ORDER BY id",
                       (subject_ref, question)).fetchall()
    for qid, status, _a in rows:
        if status == "open":
            con.execute("UPDATE queue SET proposed_answer=? WHERE id=?", (proposed_answer, qid))
            return qid
    if any(st == "answered" or (st == "dismissed" and a != ENGINE_CLOSED) for _i, st, a in rows):
        return None
    return queue_add(con, "gap", subject_ref, question, proposed_answer)


def queue_retire_missing(con, kind, keep_ids):
    """Dismiss every open row of this kind that is not in keep_ids (the engine closing its own gaps). Never touches other kinds."""
    keep = set(keep_ids)
    n = 0
    for (qid,) in con.execute("SELECT id FROM queue WHERE kind=? AND status='open'", (kind,)).fetchall():
        if qid not in keep:
            con.execute("UPDATE queue SET status='dismissed', answered_at=?, answer=? WHERE id=?", (_ts(), ENGINE_CLOSED, qid))
            n += 1
    return n


def queue_dismiss(con, queue_id):
    con.execute("UPDATE queue SET status='dismissed', answered_at=? WHERE id=? AND status='open'", (_ts(), queue_id))


# ---- planning doors (con-taking cores; the front-door wrappers live in store.py) -----------------------
SHELF_DAYS = {"email": 30, "task": 14}   # inbox mail older than 30 days / a task overdue by 14 days -> ask, never act
CLOSED_STATUSES = ("sent", "completed", "cancelled", "done", "archived")


def _proposal_dict(r):
    return {"id": r[0], "kind": r[1], "subject_ref": r[2], "question": r[3], "proposed_answer": r[4],
            "status": r[5], "created_at": r[6], "answered_at": r[7], "answer": r[8]}


_PCOLS = "id,kind,subject_ref,question,proposed_answer,status,created_at,answered_at,answer"


def proposals_list(con, kind=None, status="open", limit=None):
    """Queue rows as dicts, oldest first. status: open|answered|dismissed|all."""
    sql, args = "SELECT %s FROM queue WHERE 1=1" % _PCOLS, []
    if status != "all":
        sql += " AND status=?"; args.append(status)
    if kind:
        sql += " AND kind=?"; args.append(kind)
    sql += " ORDER BY id"
    if limit:
        sql += " LIMIT ?"; args.append(int(limit))
    return [_proposal_dict(r) for r in con.execute(sql, args)]


def proposal_answer(con, queue_id, answer, decided_by=None):
    """Answer one open proposal: closes the queue row (the words go to kg_answers in store.answer_proposal). Never touches Gmail.
    decided_by defaults to the owner's stored id (gc_settings.owner_id())."""
    if decided_by is None:
        import gc_settings
        decided_by = gc_settings.owner_id()
    if answer is None or not str(answer).strip():
        raise ValueError("an answer is required")
    row = con.execute("SELECT kind, subject_ref, proposed_answer FROM queue WHERE id=?", (queue_id,)).fetchone()
    if row is None:
        raise ValueError("no such proposal %r" % queue_id)
    aid = queue_answer(con, queue_id, str(answer).strip(), decided_by)
    a = str(answer).strip().lower()
    return {"id": queue_id, "kind": row[0], "subject_ref": row[1], "answer": str(answer).strip(), "decided_by": decided_by,
            "accepted": True if a in ("yes", "y") else False if a in ("no", "n") else None,
            "proposed_answer": row[2], "answer_log_id": aid}  # aid is None now; kept so older callers do not break


def expiry_questions_list(con, now=None, limit=None):
    """Items past their shelf life, each as a QUESTION (never an action): inbox mail older than SHELF_DAYS['email'],
    tasks overdue by SHELF_DAYS['task']. Skips items with a pin or active quiet-until, and items already asked about
    (any 'expiry' queue row for that item). Pure read."""
    n = _day(now) if now is not None else clock.today()
    asked = {r[0] for r in con.execute("SELECT subject_ref FROM queue WHERE kind='expiry'")}
    held = _item_override_ids(con)
    out = []
    rows = con.execute("SELECT id, source, kind, title, person_address, occurred_at, due_at, status FROM items ORDER BY occurred_at, id").fetchall()
    for r in rows:
        iid, source, kind, title, addr, occ, due, status = tuple(r)
        if "item:%d" % iid in asked or (status or "") in CLOSED_STATUSES:
            continue
        if any(t == "pin" or n < _day(u) for t, u in held.get(iid, ())):
            continue
        if kind == "email" and status == "inbox" and occ:
            age = (n - _day(occ)).days
            if age > SHELF_DAYS["email"]:
                out.append({"item_id": iid, "kind": kind, "title": title, "person_address": addr, "age_days": age, "due_at": due,
                            "reason": "in the inbox %d days" % age,
                            "question": "\"%s\" has sat in the inbox %d days: still a to-do, or put it away?" % ((title or "")[:100], age)})
        elif kind == "task" and due:
            over = (n - _day(due)).days
            if over > SHELF_DAYS["task"]:
                out.append({"item_id": iid, "kind": kind, "title": title, "person_address": addr, "age_days": over, "due_at": due,
                            "reason": "overdue %d days" % over,
                            "question": "Task \"%s\" was due %s (%d days ago): still wanted, or drop it?" % ((title or "")[:100], str(due)[:10], over)})
    out.sort(key=lambda x: -x["age_days"])
    return out[:int(limit)] if limit else out


def urgent_items_list(con, now=None, limit=20):
    """Open items ranked by computed urgency with overrides applied: pins float to 1.0, quiet-until hides (urgency 0 is dropped),
    items with no date and no pin have no opinion and are left out. Ties: earlier due first, then id."""
    n = _day(now) if now is not None else clock.today()
    out = []
    held = _item_override_ids(con)
    ids = ",".join(str(int(k)) for k in held) or "NULL"
    rows = con.execute("SELECT id, source, kind, title, person_address, due_at, status FROM items i WHERE due_at IS NOT NULL "
                       "OR EXISTS(SELECT 1 FROM kg_things t JOIN kg_current_links l ON l.from_id=t.id AND l.kind='part_of' AND l.who IN ('owner','code') "
                       "WHERE t.key='item:'||i.id) OR i.id IN (%s)" % ids).fetchall()
    for iid, source, kind, title, addr, due, status in (tuple(r) for r in rows):
        pinned = any(t == "pin" for t, _ in held.get(iid, ()))
        if (status or "") in CLOSED_STATUSES and not pinned:
            continue
        u = item_urgency(con, iid, n)
        if not u:       # None (no opinion) or 0.0 (quiet / faded out)
            continue
        names = [(project_info(con, p) or {}).get("name") for p in item_projects(con, iid)]
        out.append({"item_id": iid, "source": source, "kind": kind, "title": title, "person_address": addr, "due_at": due,
                    "status": status, "urgency": u, "pinned": pinned, "projects": [x for x in names if x]})
    out.sort(key=lambda x: (-x["urgency"], x["due_at"] or "9999", x["item_id"]))
    return out[:int(limit)] if limit else out


def week_digest_dict(con, start, end, now=None, top=5):
    """One dict for a planning skill. start/end: dates, [start, end). Counts, top urgent, due in window, open proposals by kind,
    overrides overdue for review as of `end`, expiry questions waiting."""
    s, e = _day(start), _day(end)
    n = _day(now) if now is not None else clock.today()
    arrived = {}
    for src, kind, c in con.execute("SELECT source, kind, count(*) FROM items WHERE occurred_at>=? AND occurred_at<? GROUP BY source, kind",
                                    (s.isoformat(), e.isoformat())):
        arrived["%s/%s" % (src, kind)] = c
    due = [dict(item_id=r[0], kind=r[1], title=r[2], due_at=r[3], status=r[4]) for r in con.execute(
        "SELECT id, kind, title, due_at, status FROM items WHERE due_at>=? AND due_at<? ORDER BY due_at, id", (s.isoformat(), e.isoformat()))
        if (r[4] or "") not in CLOSED_STATUSES]
    by_kind = {}
    for p in proposals_list(con):
        by_kind.setdefault(p["kind"], []).append(p)
    return {"start": s.isoformat(), "end": e.isoformat(), "as_of": n.isoformat(),
            "counts": {"arrived": arrived, "arrived_total": sum(arrived.values()), "open_proposals": sum(len(v) for v in by_kind.values()),
                       "due_in_window": len(due), "expiry_questions": len(expiry_questions_list(con, n))},
            "top_urgent": urgent_items_list(con, n, top),
            "due_in_window": due,
            "open_proposals": {k: {"count": len(v), "items": v} for k, v in sorted(by_kind.items())},
            "overdue_reviews": [{"id": r[0], "level": r[1], "subject_id": r[2], "type": r[3], "reason": r[4], "review_by": r[5]}
                                for r in overrides_due_for_review(con, e)]}


# ---- rebuild -----------------------------------------------------------------------------------------
def rebuild_model(con, state_dir=None):
    """The old world-model rebuild (from the Phase B grade files, world_model/load_answers.py) stayed behind on the rig
    branch as history (step 4M.2): no gc command or job uses it. The current rebuild is store_graph.rebuild_model."""
    raise RuntimeError("store_meaning.rebuild_model is retired here: the Phase B world_model/ loaders stayed on the rig "
                       "branch as history; use store_graph.rebuild_model (gc rebuild)")


def derived_snapshot(con):
    """Comparable picture of every derived table, ordered by id (rebuild must reproduce it exactly)."""
    snap = {}
    for t in DERIVED:
        cols = [c[1] for c in con.execute("PRAGMA table_info(%s)" % t)]
        snap[t] = con.execute("SELECT %s FROM %s ORDER BY id" % (",".join(cols), t)).fetchall()
    return snap


# ---- front-door readers: same answers as the con-taking functions above, but each opens its own read-only
# connection via store._read() (db.connect). Callers (gc, desks) never hold or pass a connection. ---------
def _fd(fn, *a, **k):
    import store
    with store._read() as c:
        return fn(c, *a, **k)


def projects_of_item(item_id):
    return _fd(item_projects, item_id)


def urgency_of_item(item_id, now=None):
    return _fd(item_urgency, item_id, now)


def project_urgencies(now=None):
    return _fd(project_urgency, now)


def notes_of(subject_kind, subject_id):
    return _fd(notes_for, subject_kind, subject_id)


def overrides_due(now=None):
    return [tuple(r) for r in _fd(overrides_due_for_review, now)]


def score_of_person(person_id):
    return _fd(person_score, person_id)


def open_queue():
    return [tuple(r) for r in _fd(queue_open)]
