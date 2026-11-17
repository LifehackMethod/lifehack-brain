"""store_pages.py: Phase 3 step 3.7. The four read-only pages: a person, an organization's chart, what is coming up, who is due.

Same rule as store_relation: only HIS WORD (who='owner') or CODE-CERTAIN rows (who='code', certainty='sure', source_kind='code') are read;
a machine guess never shows. Nothing known shows as unknown/None, never as a guess. Nothing is stored (no table, no cache, no write).
A key that was merged away resolves to the survivor (store_graph.resolve_key); an address resolves to its person; a retired thing is absent.
Every fact and line carries certainty, source and since (freshness). Every person/organization/event also carries `relation`
(store_relation.relation_to_me). Functions take a connection and an `asof` date (ISO string or date); they never open the file themselves.
"""
import datetime as dt
import sqlite3

import store_graph as sg
import store_relation as sr
import store_diary as sdi

CAP_EVENTS, CAP_ITEMS, CAP_PEOPLE = 10, 10, 30


def _asof(asof):
    return asof if isinstance(asof, str) else (asof or dt.date.today()).isoformat()


def _rows(con):
    con.row_factory = sqlite3.Row
    return con


def resolve(con, key):
    """-> thing row (current, not retired) for a person/organization key, an old key, or an address; None if unknown or retired."""
    _rows(con)
    key = (key or "").strip()
    if key.startswith("address:"):
        key = sr.person_key_for_address(con, key[8:]) or key
    elif "@" in key and ":" not in key:
        key = sr.person_key_for_address(con, key) or key
    key = sg.resolve_key(con, key)
    t = sr._thing(con, key)
    if t is None or t["merged_into"] is not None or t["retired_at"] is not None:
        return None
    return t


def _facts(con, tid):
    return [{"fact": r["fact_key"], "value": r["value"], "certainty": r["certainty"], "who": r["who"],
             "source": "%s%s" % (r["source_kind"], (":" + str(r["source_ref"])) if r["source_ref"] else ""),
             "since": r["true_from"] or r["created_at"]}
            for r in con.execute("SELECT f.* FROM kg_facts f WHERE f.thing_id=? AND " + sr.LIVE_FACT + " ORDER BY f.fact_key, f.id", (tid,))]


def _line(con, l):
    return {"role": l["role"], "certainty": l["certainty"], "who": l["who"],
            "source": "%s%s" % (l["source_kind"], (":" + str(l["source_ref"])) if l["source_ref"] else ""), "since": l["true_from"] or l["created_at"]}


def _links(con, tid, kind, out=True):
    """live trusted lines of one kind, out of (or into) a thing, to a current thing -> [(other thing row, line dict)]"""
    a, b = ("from_id", "to_id") if out else ("to_id", "from_id")
    res = []
    for l in con.execute("SELECT l.* FROM kg_links l WHERE l.%s=? AND l.kind=? AND %s ORDER BY l.id" % (a, sr.LIVE_LINK), (tid, kind)):
        o = con.execute("SELECT id, kind, key, name, starts_at, ends_at FROM kg_things WHERE id=? AND merged_into IS NULL AND retired_at IS NULL", (l[b],)).fetchone()
        if o:
            res.append((o, _line(con, l)))
    return res


def _short(con, t, asof):
    rel = sr.relation_to_me(con, t["key"], asof)
    return {"key": t["key"], "name": t["name"], "relation": rel["text"] or None}


def _addresses(con, pid):
    return [o["key"][8:] for o, _ in _links(con, pid, "address_of", out=False) if o["kind"] == "address"]


def _event_row(t, asof):
    return {"key": t["key"], "name": t["name"], "starts_at": t["starts_at"], "ends_at": t["ends_at"]}


def _diary(con, key):
    """Diary entries whose front-matter mentions carry this key (a merged-away key counts as its survivor), newest first, each with
    its confidence stamp. Entries with no mentions are on no page; nothing is guessed from prose. [] when there is no diary index."""
    try:
        return [dict(diary=e["diary"], date=e["date"], entry_path=e["entry_path"], confidence=e["confidence"])
                for e in sdi.entries_mentioning(con, key)]
    except sqlite3.OperationalError:
        return []


def person_page(con, key, asof=None):
    """A person's page (Vision 3.7.5 v_person_page), or None when the key is unknown or retired."""
    asof = _asof(asof)
    t = resolve(con, key)
    if t is None or t["kind"] != "person":
        return None
    tid = t["id"]
    me = sr._me(con)
    page = {"key": t["key"], "name": t["name"], "asked_as": key if key != t["key"] else None, "relation": sr.relation_to_me(con, t["key"], asof),
            "facts": _facts(con, tid), "addresses": _addresses(con, tid)}
    page["organizations"] = [dict(name=o["name"], key=o["key"], **ln) for o, ln in _links(con, tid, "member_of") if o["kind"] == "organization"]
    page["reports_to"] = [dict(key=o["key"], name=o["name"], **ln) for o, ln in _links(con, tid, "reports_to")]
    page["reports_here"] = [dict(key=o["key"], name=o["name"], **ln) for o, ln in _links(con, tid, "reports_to", out=False)]
    page["knows"] = [dict(key=o["key"], name=o["name"], **ln) for o, ln in _links(con, tid, "knows")]
    page["projects"] = [dict(key=o["key"], name=o["name"], **ln) for o, ln in _links(con, tid, "involves", out=False) if o["kind"] == "project"]
    ev = {}
    for o, ln in _links(con, tid, "involves", out=False):
        if o["kind"] == "event":
            ev[o["id"]] = (o, "invited")
    for p in page["projects"]:
        pt = sr._thing(con, p["key"])
        for o, ln in _links(con, pt["id"], "part_of", out=False):
            if o["kind"] == "event":
                ev.setdefault(o["id"], (o, "through project " + p["name"]))
    evs = sorted(ev.values(), key=lambda x: ((x[0]["starts_at"] or ""), x[0]["id"]))
    up = [dict(_event_row(o, asof), via=v) for o, v in evs if (o["starts_at"] or "")[:10] >= asof]
    past = [dict(_event_row(o, asof), via=v) for o, v in evs if (o["starts_at"] or "")[:10] and (o["starts_at"] or "")[:10] < asof]
    page["upcoming_events"], page["upcoming_total"] = up[:CAP_EVENTS], len(up)
    page["recent_events"], page["recent_total"] = list(reversed(past))[:CAP_EVENTS], len(past)
    items = []
    for ad in page["addresses"]:
        items += [dict(r) for r in con.execute("SELECT source, kind, title, occurred_at, due_at, status FROM items WHERE person_address=?", (ad,))]
    items.sort(key=lambda x: x["occurred_at"] or "", reverse=True)
    page["recent_items"], page["items_total"] = items[:CAP_ITEMS], len(items)
    page["is_me"] = t["id"] == me
    d = _diary(con, t["key"])
    if d:                                   # optional field: absent when no entry names this person
        page["diary"] = d
    return page


def _org_type(con, tid):
    """(value, certainty) of the organization's current type, shown even when only 'likely' (the label says so; it is never passed off as
    confirmed). (None, None) when no type is on file."""
    r = con.execute("SELECT value, certainty, who FROM kg_facts f WHERE f.thing_id=? AND f.fact_key='org_type' AND f.replaced_by IS NULL "
                    "AND f.true_until IS NULL ORDER BY f.id DESC LIMIT 1", (tid,)).fetchone()
    if r is None:
        return None, None
    return r["value"], r["certainty"]


def org_chart(con, key, asof=None):
    """An organization's chart (v_org_chart): parts (nested), members with roles, reporting lines among them. None if unknown."""
    asof = _asof(asof)
    t = resolve(con, key)
    if t is None or t["kind"] != "organization":
        return None
    seen = set()

    def node(o, depth):
        seen.add(o["id"])
        ot = _org_type(con, o["id"])
        n = {"key": o["key"], "name": o["name"], "org_type": ot[0], "org_type_certainty": ot[1], "members": [], "parts": []}
        for p, ln in _links(con, o["id"], "member_of", out=False):
            if p["kind"] == "person":
                n["members"].append(dict(key=p["key"], name=p["name"], **ln))
        for q, ln in _links(con, o["id"], "part_of", out=False):
            if q["kind"] == "organization" and q["id"] not in seen and depth < 10:
                n["parts"].append(node(q, depth + 1))
        return n

    tree = node(t, 0)
    ids = {}

    def collect(n):
        for m in n["members"]:
            ids[m["key"]] = m["name"]
        for p in n["parts"]:
            collect(p)
    collect(tree)
    lines = []
    for k, nm in sorted(ids.items()):
        th = sr._thing(con, k)
        for b, ln in _links(con, th["id"], "reports_to"):
            if b["key"] in ids:
                lines.append(dict(person=k, person_name=nm, boss=b["key"], boss_name=b["name"], **ln))
    tree["reporting_lines"] = lines
    tree["parent_of_this"] = [dict(key=o["key"], name=o["name"], **ln) for o, ln in _links(con, t["id"], "part_of") if o["kind"] == "organization"]
    tree["projects"] = [dict(key=o["key"], name=o["name"]) for o, _ in _links(con, t["id"], "part_of", out=False) if o["kind"] == "project"]
    tree["facts"] = _facts(con, t["id"])
    tree["relation"] = sr.relation_to_me(con, t["key"], asof)
    tree["asked_as"] = key if key != t["key"] else None
    d = _diary(con, t["key"])
    if d:                                   # optional field: absent when no entry names this organization
        tree["diary"] = d
    return tree


def upcoming(con, start=None, days=7):
    """Events whose start falls in [start, start+days): each with its people (and each one's relation to him) and its projects."""
    _rows(con)
    start = _asof(start)
    end = (dt.date.fromisoformat(start) + dt.timedelta(days=days)).isoformat()
    me = sr._me(con)
    out = []
    for e in con.execute("SELECT id, kind, key, name, starts_at, ends_at FROM kg_things WHERE kind='event' AND merged_into IS NULL AND retired_at IS NULL "
                         "AND substr(starts_at,1,10)>=? AND substr(starts_at,1,10)<? ORDER BY starts_at, id", (start, end)).fetchall():
        st = next((f["value"] for f in _facts(con, e["id"]) if f["fact"] == "event_status"), None)
        if st == "cancelled":
            continue
        projects = [{"key": p["key"], "name": p["name"]} for p, _ in _links(con, e["id"], "part_of") if p["kind"] == "project"]
        people, seen = [], set()
        for o, ln in _links(con, e["id"], "involves"):
            if o["kind"] == "person" and o["id"] != me and o["id"] not in seen:
                seen.add(o["id"])
                people.append(dict(_short(con, o, start), via="invited"))
            elif o["kind"] == "address":
                people.append({"key": o["key"], "name": o["name"], "relation": None, "via": "invited (address only)"})
        for pr in projects:
            pt = sr._thing(con, pr["key"])
            for o, ln in _links(con, pt["id"], "involves"):
                if o["kind"] == "person" and o["id"] != me and o["id"] not in seen:
                    seen.add(o["id"])
                    people.append(dict(_short(con, o, start), via="through project " + pr["name"]))
        rel = sr.relation_to_me(con, e["key"], start)
        out.append({"key": e["key"], "name": e["name"], "starts_at": e["starts_at"], "ends_at": e["ends_at"], "status": st,
                    "projects": projects, "people_total": len(people), "people": people[:CAP_PEOPLE], "relation": rel["text"] or None})
        d = _diary(con, e["key"])
        if d:                               # optional field: absent when no entry names this event
            out[-1]["diary"] = d
    return {"start": start, "end": end, "events": out}


def last_contact(con, pid):
    """Last two-way contact (ms since epoch) across the person's addresses: only an address where they wrote AND he sent. None = none on record."""
    best = None
    for ad in _addresses(con, pid):
        r = con.execute("SELECT last_from_ms, last_to_ms, two_way FROM s_addr_signals WHERE address=?", (ad,)).fetchone()
        if r and r["two_way"]:
            m = max(r["last_from_ms"] or 0, r["last_to_ms"] or 0)
            best = max(best or 0, m)
    return best


def due(con, asof=None):
    """People past THEIR keep_in_touch_days (his word, whole days). Last contact unknown shows as unknown (counted as due, never guessed)."""
    _rows(con)
    asof = _asof(asof)
    today = dt.date.fromisoformat(asof)
    out = []
    for f in con.execute("SELECT f.thing_id, f.value, f.certainty, f.who, f.source_kind, f.source_ref, f.true_from, f.created_at FROM kg_facts f "
                         "WHERE f.fact_key='keep_in_touch_days' AND " + sr.LIVE_FACT + " ORDER BY f.id"):
        t = con.execute("SELECT id, kind, key, name FROM kg_things WHERE id=? AND kind='person' AND merged_into IS NULL AND retired_at IS NULL", (f["thing_id"],)).fetchone()
        if not t or not str(f["value"]).isdigit() or t["key"] == "person:me":
            continue
        keep = int(f["value"])
        ms = last_contact(con, t["id"])
        last = dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).date() if ms else None
        days = (today - last).days if last else None
        if last is None or days > keep:
            out.append({"key": t["key"], "name": t["name"], "keep_in_touch_days": keep, "last_contact": last.isoformat() if last else None,
                        "days_since": days, "overdue_by": (days - keep) if days is not None else None,
                        "certainty": f["certainty"], "source": "%s%s" % (f["source_kind"], (":" + str(f["source_ref"])) if f["source_ref"] else ""),
                        "since": f["true_from"] or f["created_at"], "relation": sr.relation_to_me(con, t["key"], asof)["text"] or None})
    out.sort(key=lambda x: (x["overdue_by"] is None, -(x["overdue_by"] or 0), x["key"]))
    return {"asof": asof, "due": out}
