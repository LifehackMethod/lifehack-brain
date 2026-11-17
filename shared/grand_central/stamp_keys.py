"""Phase 4 step 4.5 (closes 4.3's open join): the morning read stamps CODE-CERTAIN keys onto each staged item.
  - an email item   -> its sender's person key, else the sender's organization key, through the address links
                       (address -address_of-> person, address -belongs_to-> organization; current links only, never an AI guess);
  - a calendar item -> its event key (event:calendar:<id>), only if store_events has made that event;
  - a task          -> only a key the task is already linked to (a thing for the task with links to a person, organization,
                       event or project); none exists -> none.
Nothing is ever read out of prose and looked up. Each stamped item also carries its part of life (routing.py: the
label's life_part, else the sender's `domain` fact) so the midnight job can route it. The sender's address is NOT kept:
only the key and the part of life are written into the form.
stamp_items(con, emails, calendar, tasks, labels) -> [ {"source", "id", "life_part", "keys", ["thread_id"]} ]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import store_graph as sg  # noqa: E402
import routing  # noqa: E402

KEY_KINDS = ("person", "organization", "event", "project")


def _link_target(con, from_key, kinds, to_kind):
    r = con.execute("SELECT t.key FROM kg_things f JOIN kg_current_links l ON l.from_id=f.id "
                    "JOIN kg_things t ON t.id=l.to_id AND t.kind=? "
                    "WHERE f.key=? AND l.kind IN (%s) ORDER BY l.id LIMIT 1" % ",".join("?" * len(kinds)),
                    (to_kind, from_key) + tuple(kinds)).fetchone()
    return r[0] if r else None


def sender_key(con, address):
    """-> the sender's person key, else organization key, else None. Only through the address's own links."""
    if not address:
        return None
    ak = sg.thing_key("address", address)
    return _link_target(con, ak, ("address_of",), "person") or _link_target(con, ak, ("belongs_to",), "organization")


def event_key(con, cal_id):
    key = "event:calendar:%s" % cal_id
    return key if con.execute("SELECT 1 FROM kg_things WHERE key=? AND kind='event'", (key,)).fetchone() else None


def task_keys(con, task_id):
    """Keys a task is ALREADY linked to (its thing's current links, either direction). No such thing -> []."""
    out = []
    for ref in ("task:%s" % task_id,):
        r = con.execute("SELECT id FROM kg_things WHERE key=? OR legacy_ref=?", (ref, ref)).fetchone()
        if not r:
            continue
        for (k,) in con.execute("SELECT t.key FROM kg_current_links l JOIN kg_things t ON t.id=(CASE WHEN l.from_id=? THEN l.to_id ELSE l.from_id END) "
                                "WHERE (l.from_id=? OR l.to_id=?) AND t.kind IN ('person','organization','event','project') "
                                "AND t.retired_at IS NULL", (r[0], r[0], r[0])).fetchall():
            out.append(k)
    return sorted(set(out))


def stamp_items(con, emails, calendar, tasks, labels=None):
    """emails: [{"id", "label", "thread_id"}] (the ones the read used); calendar: [{"id"}]; tasks: [{"id"}]."""
    items = []
    for e in emails or []:
        row = con.execute("SELECT from_addr FROM messages WHERE id=?", (e["id"],)).fetchone()
        addr = row[0] if row else None
        k = sender_key(con, addr)
        part = routing.part_of_life({"label": e.get("label"), "sender": addr}, labels or {}, con)
        it = {"source": "email", "id": e["id"], "life_part": part, "keys": [k] if k else []}
        if e.get("thread_id"):
            it["thread_id"] = e["thread_id"]
        items.append(it)
    for c in calendar or []:
        if isinstance(c, dict) and c.get("id"):
            k = event_key(con, c["id"])
            items.append({"source": "calendar", "id": c["id"], "life_part": None, "keys": [k] if k else []})
    for t in tasks or []:
        if isinstance(t, dict) and t.get("id"):
            items.append({"source": "task", "id": t["id"], "life_part": None, "keys": task_keys(con, t["id"])})
    return items
