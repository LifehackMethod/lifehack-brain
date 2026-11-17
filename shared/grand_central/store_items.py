"""store_items.py: STEP 4 front-door functions for items, item_events and text pointers.

Same rules as store.py: no caller-supplied SQL, bound parameters, one short transaction per call, no DDL
(the schema is migrations/002_items.sql), no backup. Uses store.set_path() / store.db_path() so tests point
both modules at one temp DB. The text of mail/events/tasks never goes through here; text_pointers holds
a path, a hash and a byte count only.
"""
import datetime
import hashlib
import os

import store
from rig_env import RIG_HOME

HANDOFF_DIR = os.path.join(RIG_HOME, "handoff")
ITEM_COLS = ("source", "source_id", "kind", "title", "person_address", "occurred_at", "due_at", "status")


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _item_id(c, source, source_id):
    r = c.execute("SELECT id FROM items WHERE source=? AND source_id=?", (source, source_id)).fetchone()
    return r["id"] if r else None


def upsert_item(source, source_id, kind, title=None, person_address=None, occurred_at=None, due_at=None,
                status=None):
    """Insert or update the common-shape row for (source, source_id). Returns (item_id, created)."""
    if not source or not source_id or not kind:
        raise ValueError("upsert_item: source, source_id and kind are required")
    addr = person_address.strip().lower() if person_address else None
    vals = (kind, title, addr, occurred_at, due_at, status)
    with store._write() as c:
        iid = _item_id(c, source, str(source_id))
        if iid is None:
            cur = c.execute("INSERT INTO items(source,source_id,kind,title,person_address,occurred_at,due_at,"
                            "status,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                            (source, str(source_id)) + vals + (_now(),))
            return cur.lastrowid, True
        c.execute("UPDATE items SET kind=?,title=?,person_address=?,occurred_at=?,due_at=?,status=? WHERE id=?",
                  vals + (iid,))
        return iid, False


def get_item(source, source_id):
    return store._one("SELECT * FROM items WHERE source=? AND source_id=?", (source, str(source_id)))


def append_item_event(item_id, kind, at=None, detail=None, actor=None):
    """Add one line to an item's history. There is no update or delete; the database refuses both."""
    with store._write() as c:
        cur = c.execute("INSERT INTO item_events(item_id,at,kind,detail,actor) VALUES(?,?,?,?,?)",
                        (item_id, at or _now(), kind, detail, actor))
        return cur.lastrowid


def item_history(item_id):
    return store._rows("SELECT * FROM item_events WHERE item_id=? ORDER BY at, id", (item_id,))


def items_between(start, end, kind=None, source=None):
    """Items whose occurred_at is in [start, end) (text compare, ISO strings), oldest first."""
    sql, args = "SELECT * FROM items WHERE occurred_at >= ? AND occurred_at < ?", [start, end]
    if kind:
        sql, args = sql + " AND kind=?", args + [kind]
    if source:
        sql, args = sql + " AND source=?", args + [source]
    return store._rows(sql + " ORDER BY occurred_at, id", args)


def item_counts():
    """{source: count}"""
    return {r["source"]: r["n"] for r in store._rows("SELECT source, count(*) n FROM items GROUP BY source")}


def add_text_pointer(path, item_id=None, handoff_dir=None):
    """Record a file in the handoff folder: its path, sha256 and size. The file's text is never read into the DB.
    Refuses a path outside the handoff folder. Returns the pointer id (existing id if already recorded)."""
    root = os.path.realpath(handoff_dir or HANDOFF_DIR)
    full = os.path.realpath(os.path.expanduser(path))
    if os.path.commonpath([root, full]) != root or full == root:
        raise ValueError("add_text_pointer: %s is outside the handoff folder %s" % (path, root))
    if not os.path.isfile(full):
        raise ValueError("add_text_pointer: no such file: %s" % full)
    h, n = hashlib.sha256(), 0
    with open(full, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
            n += len(chunk)
    with store._write() as c:
        c.execute("INSERT OR IGNORE INTO text_pointers(item_id,path,sha256,bytes,added_at) VALUES(?,?,?,?,?)",
                  (item_id, full, h.hexdigest(), n, _now()))
        return c.execute("SELECT id FROM text_pointers WHERE path=? AND sha256=?", (full, h.hexdigest())).fetchone()["id"]


def text_pointers_for(item_id):
    return store._rows("SELECT * FROM text_pointers WHERE item_id=? ORDER BY id", (item_id,))


def verify_text_pointer(pointer_id):
    """True if the file still exists with the recorded hash."""
    p = store._one("SELECT * FROM text_pointers WHERE id=?", (pointer_id,))
    if not p or not os.path.isfile(p["path"]):
        return False
    with open(p["path"], "rb") as f:
        return hashlib.sha256(f.read()).hexdigest() == p["sha256"]


def backfill_items():
    """Populate items (+ thin detail + one 'arrived' event per NEW item) from messages, calendar_events, tasks.
    Idempotent: unique(source, source_id), links and events only added for rows created this run.
    Returns {source: rows_created_this_run}."""
    made = {"gmail": 0, "calendar": 0, "tasks": 0}
    now = _now()
    with store._write() as c:
        def run(source, kind, select, detail_sql):
            before = c.execute("SELECT count(*) FROM items WHERE source=?", (source,)).fetchone()[0]
            c.execute("INSERT OR IGNORE INTO items(source,source_id,kind,title,person_address,occurred_at,due_at,"
                      "status,created_at) " + select, (now,))
            c.execute(detail_sql)
            made[source] = c.execute("SELECT count(*) FROM items WHERE source=?", (source,)).fetchone()[0] - before
            # arrived event for items that have no history yet
            c.execute("INSERT INTO item_events(item_id,at,kind,detail,actor) "
                      "SELECT i.id, COALESCE(i.occurred_at, i.created_at), 'arrived', 'backfill', 'backfill_items' "
                      "FROM items i WHERE i.source=? AND NOT EXISTS (SELECT 1 FROM item_events e WHERE e.item_id=i.id)",
                      (source,))
        run("gmail", "email",
            "SELECT 'gmail', id, 'email', subject, lower(NULLIF(from_addr,'')), "
            "strftime('%Y-%m-%dT%H:%M:%SZ', internal_date/1000, 'unixepoch'), NULL, "
            "CASE WHEN is_sent=1 THEN 'sent' WHEN label_ids LIKE '%\"INBOX\"%' THEN 'inbox' ELSE 'archived' END, ? "
            "FROM messages",
            "INSERT OR IGNORE INTO item_email(item_id,message_id,thread_id) "
            "SELECT i.id, m.id, m.thread_id FROM items i JOIN messages m ON i.source='gmail' AND i.source_id=m.id")
        run("calendar", "event",
            "SELECT 'calendar', id, 'event', summary, lower(NULLIF(organizer_email,'')), start, NULL, status, ? "
            "FROM calendar_events",
            "INSERT OR IGNORE INTO item_calendar(item_id,calendar_event_id,all_day) "
            "SELECT i.id, e.id, e.all_day FROM items i JOIN calendar_events e ON i.source='calendar' AND i.source_id=e.id")
        run("tasks", "task",
            "SELECT 'tasks', id, 'task', title, NULL, updated, due, status, ? FROM tasks",
            "INSERT OR IGNORE INTO item_task(item_id,task_id,list_id) "
            "SELECT i.id, t.id, t.list_id FROM items i JOIN tasks t ON i.source='tasks' AND i.source_id=t.id")
    return made
