# retiring: kept only for gc-daily's proposals until Phase 5
"""rank.py: step 4. One 'rank' score per window item with its reasons ("his word: example.com importance high · due
in 3 days · your move"). Order of precedence:
  1. His overrides: an active pin goes to the top; an active quiet-until goes to the bottom (never hidden; quiet wins).
  2. His own facts (who=owner) on the sender: importance sets how much it matters; inbox=skip, destination=trash/promos demote.
  3. Otherwise importance x how soon x whose move.
       importance: his fact > tier/importance from code or AI facts > signals (sender_history, on_calendar_14d) > 0.3
       how soon:   store_meaning.urgency(due) when the item has a date; else its episode's date window; else mild recency
       whose move: 1.0 his, 0.5 theirs, 0.7 nobody/unknown
Demote, never hide: every window item gets a row. Values: pinned 2+base, normal base (0..1), demoted base*0.2,
quiet-until -1+base*0.01."""
import common as C
import store_graph as sg
import store_meaning as sm

NAME, VERSION = "rank", 1
MOVE = {"him": 1.0, "them": 0.5, "nobody": 0.7, "undecided": 0.7}
DEMOTE_DEST = ("trash", "promos")


def _plural(n, w):
    return "%d %s%s" % (n, w, "" if n == 1 else "s")


def _when(delta, what):
    """what = 'starts' | 'due'"""
    if delta > 0:
        return "%s in %s" % (what, _plural(delta, "day"))
    if delta == 0:
        return "%s today" % what
    return ("overdue %s" if what == "due" else "started %s ago") % _plural(-delta, "day")


def run(con):
    today = C.now().date()
    ids = C.window_ids(con)
    items = C.load_items(con, ids)
    emails = C.email_info(con, [i for i in ids if items.get(i, {}).get("kind") == "email"])
    cals = C.cal_info(con, [i for i in ids if items.get(i, {}).get("kind") == "event"])

    sig = {}
    for ref, name, val, reason in con.execute("SELECT subject_ref, signal, value, reason FROM kg_scores "
                                              "WHERE signal IN ('sender_history','on_calendar_14d')"):
        sig.setdefault(int(ref.split(":")[1]), {})[name] = (val or 0.0, reason)

    # episodes an item belongs to
    ep_name = {r[0]: r[1] for r in con.execute("SELECT id, name FROM kg_things WHERE kind='episode'")}
    ep_facts = {}
    for tid, key, val in con.execute("SELECT thing_id, fact_key, value FROM kg_facts WHERE replaced_by IS NULL AND "
                                     "fact_key IN ('date_window','whose_move') AND thing_id IN (SELECT id FROM kg_things WHERE kind='episode')"):
        ep_facts.setdefault(tid, {})[key] = val
    item_eps = {}
    for tid, val in con.execute("SELECT thing_id, value FROM kg_facts WHERE replaced_by IS NULL AND fact_key='member_item' "
                                "AND thing_id IN (SELECT id FROM kg_things WHERE kind='episode')"):
        item_eps.setdefault(int(str(val).split(":")[1]), []).append(tid)

    # his overrides
    ovs = {}
    for level, sid, typ, until, reason in con.execute("SELECT level, subject_id, type, until_on, reason FROM overrides WHERE status='active'"):
        ovs.setdefault((level, sid), []).append((typ, until, reason))
    person_of = {r[0]: r[1] for r in con.execute("SELECT address, person_id FROM v_addresses WHERE person_id IS NOT NULL")}
    rules = con.execute("SELECT id, match_kind, match_value FROM v_rules_v1").fetchall()
    projects_of = {}
    for iid, pid in con.execute("SELECT item_id, project_id FROM item_projects"):
        projects_of.setdefault(iid, []).append(pid)

    fcache = {}
    sg.clear_scores(con, NAME)
    n = {"pinned": 0, "quiet": 0, "demoted": 0}
    for iid in sorted(items):
        it = items[iid]
        addr = (it["addr"] or "").lower()
        domain = addr.rsplit("@", 1)[1] if "@" in addr else ""
        parts = []

        # 1. his overrides
        keys = [("item", iid)] + ([("person", person_of[addr])] if addr in person_of else []) + \
               [("rule", rid) for rid, mk, mv in rules if (mk == "address" and addr == (mv or "").lower()) or
                (mk == "domain" and domain and domain == (mv or "").lower())] + \
               [("project", p) for p in projects_of.get(iid, [])]
        pin = quiet = None
        for k in keys:
            for typ, until, reason in ovs.get(k, []):
                if typ == "quiet-until" and until and today.isoformat() < str(until)[:10]:
                    quiet = quiet or (until, reason)
                elif typ == "pin":
                    pin = pin or reason

        # 2. his facts on the sender, and importance
        facts = fcache.setdefault(addr, C.sender_facts(con, addr)) if addr else []
        demote = []
        for f in facts:
            if f["who"] != "owner":
                continue
            if f["fact_key"] == "inbox" and f["value"] == "skip":
                demote.append("his word: %s inbox skip" % f["thing_name"])
            elif f["fact_key"] == "destination" and f["value"] in DEMOTE_DEST:
                demote.append("his word: %s destination %s" % (f["thing_name"], f["value"]))
        imp = C.importance_of(facts)
        s = sig.get(iid, {})
        if imp and imp[1] == "owner":
            importance = C.IMP[imp[0]]
            imp_txt = "his word: %s %s %s" % (imp[2]["thing_name"], imp[2]["fact_key"], imp[0])
        elif imp:
            importance = C.IMP[imp[0]]
            imp_txt = "%s %s (%s)" % (imp[2]["fact_key"], imp[0], imp[1])
        else:
            m = max([s.get("sender_history", (0, ""))[0], s.get("on_calendar_14d", (0, ""))[0]])
            if m > 0:
                importance = round(0.3 + 0.6 * m, 4)
                best = "on_calendar_14d" if s.get("on_calendar_14d", (0, ""))[0] >= s.get("sender_history", (0, ""))[0] and \
                    "on_calendar_14d" in s else "sender_history"
                imp_txt = "signals: %s" % s[best][1]
            else:
                importance, imp_txt = 0.3, "no strong signal"

        # how soon
        soon, soon_txt = None, None
        if it["kind"] == "task":
            if str(it["status"] or "").lower() == "completed":
                soon, soon_txt = 0.05, "done"
        due = it["due_at"] or (cals[iid]["start_date"] if iid in cals else None)
        if soon is None and due:
            dd = C.day(due)
            u = sm.urgency(dd, today)
            delta = (C.parse_dt(dd).date() - today).days
            what = "starts" if it["kind"] == "event" else "due"
            if it["kind"] == "task" and u is not None and u <= 0.0:
                soon, soon_txt = 0.3, "overdue %s" % _plural(-delta, "day")
            else:
                soon = max(u if u is not None else 0.0, 0.05)
                soon_txt = _when(delta, what)
        if soon is None:
            best_ep = None
            for tid in item_eps.get(iid, []):
                w = ep_facts.get(tid, {}).get("date_window")
                if not w or ".." not in w:
                    continue
                a, b = w.split("..", 1)
                if a >= today.isoformat():
                    delta = (C.parse_dt(a).date() - today).days
                    cand = (sm.urgency(a, today), "episode %s" % _when(delta, "starts"), tid)
                elif b >= today.isoformat():
                    cand = (1.0, "episode under way", tid)
                else:
                    continue
                if best_ep is None or cand[0] > best_ep[0]:
                    best_ep = cand
            if best_ep:
                soon, soon_txt = max(best_ep[0], 0.05), "%s (%s)" % (best_ep[1], ep_name.get(best_ep[2], "?"))
        if soon is None:
            when = emails[iid]["dt"].date() if iid in emails and emails[iid]["dt"] else C.parse_dt(it["occurred_at"])
            when = when.date() if hasattr(when, "date") else when
            age = (today - when).days if when else 0
            soon = max(0.1, round(0.6 - 0.01 * age, 4))
            soon_txt = "arrived %s ago" % _plural(max(age, 0), "day") if age > 0 else "arrived today"

        # whose move
        moves = [ep_facts.get(t, {}).get("whose_move") for t in item_eps.get(iid, [])]
        moves = [m for m in moves if m]
        if it["kind"] == "task":
            wm, move_txt = (1.0, "your move: open task") if str(it["status"] or "").lower() != "completed" else (0.5, "finished")
        elif moves:
            pick = "him" if "him" in moves else "them" if "them" in moves else moves[0]
            wm = MOVE.get(pick, 0.7)
            move_txt = {"him": "your move", "them": "their move", "nobody": "nobody's move"}.get(pick, "move unclear")
        else:
            wm, move_txt = 0.7, "move unclear"

        base = round(importance * soon * wm, 4)
        if quiet:
            value = round(-1 + base * 0.01, 6)
            parts.append("quiet until %s (his override: %s)" % (str(quiet[0])[:10], quiet[1]))
            n["quiet"] += 1
        elif pin:
            value = round(2 + base, 4)
            parts.append("pinned (his override: %s)" % pin)
            n["pinned"] += 1
        elif demote:
            value = round(base * 0.2, 4)
            parts.extend(demote)
            n["demoted"] += 1
        else:
            value = base
        parts += [imp_txt, soon_txt, move_txt]
        sg.set_score(con, "item:%d" % iid, NAME, VERSION, value, " · ".join(p for p in parts if p))
    return {"ranked": len(items), **n}
