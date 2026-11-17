# retiring: kept only for gc-daily's proposals until Phase 5
"""gaps.py: step 5. The code's plain observations with something missing. It reports; it does not write research
questions. Each gap is one queue row (kind 'gap'; subject_ref + a STABLE question; counts and dates go in proposed_answer).
Highest volume first, capped at GAP_CAP. Open gap rows not found again this run are dismissed (answer 'engine: ...')."""
import datetime as dt

import common as C
import store_graph as sg
import store_meaning as sm

GAP_CAP = 40
MIN_MSGS = 5
Q_SENDER = "sender writes often and is linked to no person or company"
Q_NOEND = "episode has no end date"
Q_NODOM = "episode has no domain"
Q_ATT = "calendar event in the next 2 weeks has attendees the memory doesn't know"
Q_LABEL = "label that matters has no fact saying what it is for"


def _knows(con, addr, cache):
    """The memory knows an address if any fact sits on it or its domains (or on what it links to), or it is linked to a
    person or company. The engine's own 'involves' links do not count."""
    if addr not in cache:
        w = sg.about_sender(con, addr)
        known = bool(w["facts"]) or bool(w["links"])
        if not known:  # a rule pointing at it (legacy or his) or an open question about it also counts as known
            keys = [k for k in w["keys"]] or [sg.thing_key("address", addr)]
            dom = addr.rsplit("@", 1)[1] if "@" in addr else ""
            keys += [sg.thing_key("address", addr), sg.thing_key("domain", dom)]
            q = ",".join("?" * len(keys))
            known = con.execute("SELECT 1 FROM kg_current_links WHERE kind='applies_to' AND to_key IN (%s) LIMIT 1" % q,
                                keys).fetchone() is not None or con.execute(
                "SELECT 1 FROM queue WHERE status='open' AND kind<>'gap' AND subject_ref IN (%s) LIMIT 1" % q,
                keys).fetchone() is not None
        cache[addr] = known
    return cache[addr]


def _machine_only(con, addr):
    r = con.execute("SELECT COUNT(*), SUM(CASE WHEN mc.has_list_id=1 OR mc.bulk_precedence=1 OR mc.noreply_pattern=1 "
                    "THEN 1 ELSE 0 END) FROM messages m JOIN s_machine mc ON mc.message_id=m.id WHERE lower(m.from_addr)=?", (addr,)).fetchone()
    return bool(r[0]) and r[0] == (r[1] or 0)


def run(con):
    cfg = C.settings(con)
    now = C.now()
    ids = C.window_ids(con)
    items = C.load_items(con, ids)
    emails = C.email_info(con, [i for i in ids if items.get(i, {}).get("kind") == "email"])
    cals = C.cal_info(con, [i for i in ids if items.get(i, {}).get("kind") == "event"])
    me = C.me_set(con)
    gaps = []   # (volume, subject_ref, question, evidence)

    # 1. senders who write often and are linked to nobody
    senders = sorted({em["from"] for em in emails.values() if em["from"] and em["from"] not in me})
    known = {}
    for a in senders:
        n, first, last = con.execute("SELECT COUNT(*), MIN(internal_date), MAX(internal_date) FROM messages WHERE lower(from_addr)=?", (a,)).fetchone()
        if n < MIN_MSGS or _knows(con, a, known) or _machine_only(con, a):
            continue
        gaps.append((n, "address:%s" % a, Q_SENDER, "%d messages from %s (%s to %s)" % (
            n, a, C.ms_dt(first).date().isoformat(), C.ms_dt(last).date().isoformat())))

    # 2. episodes missing an end date / a domain
    for tid, key, name, trig in con.execute(
            "SELECT t.id, t.key, t.name, (SELECT value FROM kg_facts WHERE thing_id=t.id AND fact_key='trigger' AND replaced_by IS NULL LIMIT 1) "
            "FROM kg_things t WHERE t.kind='episode' ORDER BY t.id").fetchall():
        n = con.execute("SELECT COUNT(*) FROM kg_facts WHERE thing_id=? AND fact_key='member_item' AND replaced_by IS NULL", (tid,)).fetchone()[0]
        if not n:
            continue
        win = con.execute("SELECT value FROM kg_facts WHERE thing_id=? AND fact_key='date_window' AND replaced_by IS NULL", (tid,)).fetchone()
        if str(trig or "").startswith("job phrase"):
            gaps.append((n, key, Q_NOEND, "%s: %d item(s), mail seen %s" % (name, n, win[0] if win else "no dates")))
        has_dom = con.execute("SELECT 1 FROM kg_facts WHERE thing_id=? AND fact_key='domain' AND replaced_by IS NULL", (tid,)).fetchone()
        n_addr = con.execute("SELECT COUNT(*) FROM kg_links WHERE from_id=? AND kind='involves' AND replaced_by IS NULL", (tid,)).fetchone()[0]
        if not has_dom and (n >= 2 or n_addr >= 1):
            gaps.append((n, key, Q_NODOM, "%s: %d item(s)" % (name, n)))

    # 3. calendar events in the next focus days with attendees the memory doesn't know
    hi = now + dt.timedelta(days=cfg["calendar_focus_days"])
    for iid, ce in sorted(cals.items()):
        if ce["status"] == "cancelled" or ce["start"] is None or not (now <= ce["start"] <= hi):
            continue
        unknown = [a for a in ce["attendees"] if a not in me and not _knows(con, a, known)]
        if unknown:
            gaps.append((len(unknown), "item:%d" % iid, Q_ATT, "%s on %s: %d unknown attendee(s): %s" % (
                ce["summary"] or "(no title)", ce["start_date"], len(unknown), ", ".join(sorted(unknown)[:5]))))

    # 4. labels that matter with no label_role
    for f in sg.current_facts(con, fact_key="label_matters"):
        if f["value"] != "yes" or f["thing_kind"] != "label":
            continue
        if sg.current_facts(con, f["thing_key"], "label_role"):
            continue
        lids = C.label_ids_for(con, f["thing_name"])
        n = 0
        for lid in lids:
            n += con.execute("SELECT COUNT(*) FROM messages WHERE label_ids LIKE ?", ('%"' + lid + '"%',)).fetchone()[0]
        gaps.append((n, f["thing_key"], Q_LABEL, "label %s is on %d message(s)" % (f["thing_name"], n)))

    gaps.sort(key=lambda g: (-g[0], g[1], g[2]))
    kept, by_type, seen = [], {}, set()
    for g in gaps:
        if (g[1], g[2]) in seen:
            continue
        seen.add((g[1], g[2]))
        if len(kept) < GAP_CAP:
            kept.append(g)
    keep_ids = []
    for vol, ref, q, ev in kept:
        qid = sm.queue_gap(con, ref, q, ev)
        if qid is not None:
            keep_ids.append(qid)
        by_type[q] = by_type.get(q, 0) + 1
    dismissed = sm.queue_retire_missing(con, "gap", keep_ids)
    return {"gaps_found": len(gaps), "gaps_kept": len(kept), "gaps_dismissed": dismissed, "gaps_by_type": by_type}
