"""store_relation.py: Phase 3 step 3.5. What a person, organization, project or event IS TO HIM (Vision 3.7.5 "relation to the person").

Assembled on demand by `relation_to_me(con, key)`, stored nowhere (no table, no cache). Same job as the planned view v_relation_to_me;
a function rather than a migration, because it needs a date window (upcoming events) and one sentence of words, which a view can't give.
Only rows that are HIS WORD (who='owner') or CODE-CERTAIN (who='code', certainty='sure', source_kind='code') are read. A machine guess
(ai_guess, ai_research, anything 'likely'/'guess') never shows. Nothing known -> an EMPTY relation (all lists empty, text ''), never a guess.

Shape (same keys always; `empty` is True when nothing is known):
  {key, kind, name, empty, text,
   relationship: his `relationship` fact (person/organization) or None,
   direct: [{kind, direction, role}]   the lines between him and the thing (knows, reports_to, member_of, involves, part_of)
   level: {level, source} or None      persons only, from store_levels (his number, or his reports_to chain)
   organizations: [{name, org_type, his_role, their_role}]   organizations he and the thing share (members or parts of)
   projects: [{name, via}]             projects both are on (or, for an event, the projects it belongs to)
   events: [{key, name, starts_at, via}]  upcoming events both are in, soonest first (max EVENT_CAP); events_total = all shared
  }
"""
import datetime as dt

import store_levels

EVENT_CAP = 5
TRUSTED = "(%s.who='owner' OR (%s.who='code' AND %s.certainty='sure' AND %s.source_kind='code'))"


def _t(a):
    return TRUSTED % (a, a, a, a)


LIVE_LINK = "l.replaced_by IS NULL AND l.true_until IS NULL AND " + _t("l")
LIVE_FACT = "f.replaced_by IS NULL AND f.true_until IS NULL AND " + _t("f")


def _thing(con, key):
    return con.execute("SELECT id, kind, key, name, merged_into, retired_at FROM kg_things WHERE key=?", (key,)).fetchone()


def _me(con):
    r = con.execute("SELECT id FROM kg_things WHERE key='person:me'").fetchone()
    return r[0] if r else None


def person_key_for_address(con, address):
    """The person an address belongs to (his or certain-code `address_of`), or None."""
    r = con.execute("SELECT p.key FROM kg_things ad JOIN kg_links l ON l.from_id=ad.id AND l.kind='address_of' AND " + LIVE_LINK +
                    " JOIN kg_things p ON p.id=l.to_id AND p.kind='person' AND p.merged_into IS NULL AND p.retired_at IS NULL "
                    "WHERE ad.kind='address' AND ad.key=? ORDER BY l.id LIMIT 1", ("address:" + (address or "").strip().lower(),)).fetchone()
    return r[0] if r else None


def _out(con, tid, kind):
    """live trusted links out of tid of one kind -> [(to_id, role)]"""
    return [(r[0], r[1]) for r in con.execute("SELECT l.to_id, l.role FROM kg_links l WHERE l.from_id=? AND l.kind=? AND " + LIVE_LINK, (tid, kind))]


def _in(con, tid, kind):
    return [(r[0], r[1]) for r in con.execute("SELECT l.from_id, l.role FROM kg_links l WHERE l.to_id=? AND l.kind=? AND " + LIVE_LINK, (tid, kind))]


def _live(con, ids, kinds):
    """ids restricted to things that are current (not merged, not retired) and of one of these kinds -> {id: row}"""
    out = {}
    for i in set(ids):
        r = con.execute("SELECT id, kind, key, name, starts_at FROM kg_things WHERE id=? AND merged_into IS NULL AND retired_at IS NULL", (i,)).fetchone()
        if r and r[1] in kinds:
            out[i] = r
    return out


def _ancestors(con, org_id):
    """the organization and every organization above it (part_of, organization -> organization)"""
    seen, todo = [], [org_id]
    while todo and len(seen) < 50:
        o = todo.pop()
        if o in seen:
            continue
        seen.append(o)
        todo += [p for p, _ in _out(con, o, "part_of") if _live(con, [p], ("organization",))]
    return seen


def _member_orgs(con, tid):
    """{org_id: role} the thing is a direct member of (organization kind)"""
    got = _live(con, [o for o, _ in _out(con, tid, "member_of")], ("organization",))
    return {o: role for o, role in _out(con, tid, "member_of") if o in got}


def _org_closure(con, tid):
    """every organization the thing sits in, directly or through a parent: {org_id: via_direct_member_of or None}"""
    out = {}
    for o in _member_orgs(con, tid):
        for a in _ancestors(con, o):
            out.setdefault(a, o)
    return out


def _on(con, thing_id, target_id):
    """thing (a project or event) involves target directly -> True"""
    return any(t == target_id for t, _ in _out(con, thing_id, "involves"))


def _projects_of_person(con, pid):
    """{project_id: role} projects that involve the person"""
    got = _live(con, [p for p, _ in _in(con, pid, "involves")], ("project",))
    return {p: role for p, role in _in(con, pid, "involves") if p in got}


def _events_of(con, pid):
    """{event_id: via} events that involve the person (invite or his word), or belong to a project that involves them"""
    out = {}
    for e, _ in _in(con, pid, "involves"):
        out[e] = "invited"
    for p in _projects_of_person(con, pid):
        for e, _ in _in(con, p, "part_of"):
            out.setdefault(e, "project")
    return {e: v for e, v in out.items() if _live(con, [e], ("event",))}


def _empty(key, kind=None, name=None):
    return {"key": key, "kind": kind, "name": name, "empty": True, "text": "", "relationship": None, "direct": [], "level": None,
            "organizations": [], "projects": [], "events": [], "events_total": 0}


def _fact(con, tid, key):
    r = con.execute("SELECT f.value FROM kg_facts f WHERE f.thing_id=? AND f.fact_key=? AND " + LIVE_FACT + " ORDER BY f.id DESC LIMIT 1", (tid, key)).fetchone()
    return r[0] if r else None


def relation_to_me(con, key, asof=None):
    """What `key` (person:..., organization:..., project:..., event:... or an address) is to him. Read-only; never stores."""
    import sqlite3
    con.row_factory = sqlite3.Row
    asof = asof if isinstance(asof, str) else (asof or dt.date.today()).isoformat()
    if key.startswith("address:"):
        key = person_key_for_address(con, key[8:]) or key
    t = _thing(con, key)
    me = _me(con)
    if t is None or me is None or t["merged_into"] is not None or t["retired_at"] is not None or t["id"] == me:
        return _empty(key, t["kind"] if t else None, t["name"] if t else None)
    r = _empty(key, t["kind"], t["name"])
    tid, kind = t["id"], t["kind"]

    # the direct line: the lines between him and the thing, both ways
    for k in ("knows", "reports_to", "member_of", "involves", "part_of"):
        for to, role in _out(con, me, k):
            if to == tid:
                r["direct"].append({"kind": k, "direction": "he_to_them", "role": role})
        for fr, role in _in(con, me, k):
            if fr == tid:
                r["direct"].append({"kind": k, "direction": "them_to_he", "role": role})
    if kind in ("person", "organization"):
        r["relationship"] = _fact(con, tid, "relationship")
    if kind == "person":
        lv, src = store_levels.levels_above_me(con, key)
        if lv is not None:
            r["level"] = {"level": lv, "source": src}

    if kind in ("person", "organization"):
        mine, theirs = _org_closure(con, me), _org_closure(con, tid)
        if kind == "organization":
            theirs = {a: None for a in _ancestors(con, tid)}
        my_direct, their_direct = _member_orgs(con, me), _member_orgs(con, tid) if kind == "person" else {}
        for o in sorted(set(mine) & set(theirs)):
            row = _live(con, [o], ("organization",))
            if not row:
                continue
            r["organizations"].append({"name": row[o]["name"], "org_type": _fact(con, o, "org_type"),
                                       "his_role": my_direct.get(mine[o]) if mine[o] == o else None,
                                       "their_role": their_direct.get(o)})
        r["organizations"].sort(key=lambda x: x["name"])

    # projects both are on
    mine_p = _projects_of_person(con, me)
    if kind == "person":
        theirs_p = _projects_of_person(con, tid)
        shared_p = [p for p in mine_p if p in theirs_p]
        r["projects"] = [{"name": _live(con, [p], ("project",))[p]["name"], "via": "both on it", "his_role": mine_p[p], "their_role": theirs_p[p]}
                         for p in shared_p]
    elif kind == "project":
        r["projects"] = [{"name": t["name"], "via": "he is on it" if tid in mine_p else "he is not on it", "his_role": mine_p.get(tid), "their_role": None}]
    elif kind == "event":
        ps = _live(con, [p for p, _ in _out(con, tid, "part_of")], ("project",))
        r["projects"] = [{"name": ps[p]["name"], "via": "belongs to it" + (", he is on it" if p in mine_p else ""), "his_role": mine_p.get(p),
                          "their_role": None} for p, _ in _out(con, tid, "part_of") if p in ps]

    # events both are in (people) / this event's own place in his week (event)
    if kind == "person":
        mine_e, theirs_e = _events_of(con, me), _events_of(con, tid)
        shared_e = [e for e in mine_e if e in theirs_e]
        rows = sorted((x for x in _live(con, shared_e, ("event",)).values() if (x["starts_at"] or "")[:10] >= asof), key=lambda x: (x["starts_at"], x["id"]))
        r["events_total"] = len(shared_e)
        r["events"] = [{"key": x["key"], "name": x["name"], "starts_at": x["starts_at"],
                        "via": "invited" if theirs_e[x["id"]] == "invited" and mine_e[x["id"]] == "invited" else "through a shared project"}
                       for x in rows[:EVENT_CAP]]
    elif kind == "event":
        mine_e = _events_of(con, me)
        r["events_total"] = 1 if tid in mine_e else 0
        if tid in mine_e:
            r["events"] = [{"key": key, "name": t["name"], "starts_at": _live(con, [tid], ("event",))[tid]["starts_at"],
                            "via": "he is invited" if mine_e[tid] == "invited" else "it belongs to a project he is on"}]

    r["text"] = _say(r)
    r["empty"] = not (r["text"] or r["direct"] or r["relationship"] or r["level"] or r["organizations"] or r["projects"] or r["events"])
    return r


_LEVEL_WORDS = {0: "at his level", 1: "one level above him"}


def _say(r):
    """One plain sentence from the facts above ('' if nothing is known)."""
    bits = []
    if r["relationship"]:
        bits.append(r["relationship"].rstrip("."))
    for d in r["direct"]:
        if d["kind"] == "reports_to":
            bits.append("his boss" if d["direction"] == "he_to_them" else "reports to him")
        elif d["kind"] == "knows":
            bits.append("he knows them")
    if r["level"]:
        lv = r["level"]["level"]
        bits.append(_LEVEL_WORDS.get(lv, "%d levels above him" % lv))
    for o in r["organizations"]:
        bits.append("shares %s%s" % (o["name"], (" (their role: %s)" % o["their_role"]) if o["their_role"] else ""))
    for p in r["projects"]:
        bits.append("project %s (%s)" % (p["name"], p["via"]))
    if r["events"]:
        e = r["events"][0]
        bits.append("next shared event: %s on %s" % (e["name"], (e["starts_at"] or "")[:10]))
    return "; ".join(bits)
