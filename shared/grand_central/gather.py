# retiring: kept only for gc-daily's proposals until Phase 5
"""gather.py: step 1. Picks the items in the window and writes one kg_scores row each (signal 'window', value 1,
reason = why it is in). The numbers come from the setting facts on topic:engine window (seeded here the first time)."""
import datetime as dt
import json

import common as C
import store_graph as sg

NAME, VERSION = "window", 1


def matters_label_ids(con):
    """label id -> label name for every label with a current label_matters=yes fact (any who)."""
    want = {str(f["thing_name"]).strip().lower() for f in sg.current_facts(con, fact_key="label_matters")
            if f["value"] == "yes" and f["thing_kind"] == "label"}
    return {lid: name for lid, name in C.label_names(con).items() if C.label_aliases(name) & want}


def run(con):
    seeded = C.seed_settings(con)
    cfg = C.settings(con)
    now = C.now()
    sg.clear_scores(con, NAME)
    picked = {}   # item id -> reason

    # email: in the inbox (any age) or carrying a label that matters and recent
    mlabels = matters_label_ids(con)
    cut_ms = int((now - dt.timedelta(days=cfg["email_recent_days"])).timestamp() * 1000)
    any_age = str(cfg["email_inbox_any_age"]).lower() == "yes"
    rows = con.execute("SELECT i.id, m.internal_date, m.label_ids FROM items i JOIN item_email ie ON ie.item_id=i.id "
                       "JOIN messages m ON m.id=ie.message_id WHERE i.kind='email' AND COALESCE(m.is_sent,0)=0 ORDER BY i.id").fetchall()
    for iid, ms, lj in rows:
        try:
            labels = json.loads(lj) if lj else []
        except ValueError:
            labels = []
        if "TRASH" in labels or "SPAM" in labels:
            continue
        if "INBOX" in labels and (any_age or (ms or 0) >= cut_ms):
            picked[iid] = "inbox"
            continue
        if (ms or 0) >= cut_ms:
            hit = [mlabels[l] for l in labels if l in mlabels]
            if hit:
                picked[iid] = "label %s (matters)" % sorted(hit)[0]

    # calendar: start between now-back and now+ahead (cancelled events skipped)
    lo = now - dt.timedelta(days=cfg["calendar_back_days"])
    hi = now + dt.timedelta(days=cfg["calendar_ahead_days"])
    for iid, start, status in con.execute("SELECT ic.item_id, e.start, e.status FROM item_calendar ic "
                                          "JOIN calendar_events e ON e.id=ic.calendar_event_id ORDER BY ic.item_id").fetchall():
        s = C.parse_dt(start)
        if s is None or str(status or "").lower() == "cancelled" or not (lo <= s <= hi):
            continue
        d = (s - now).days
        picked[iid] = "calendar in %d days" % d if d >= 0 else "calendar %d days ago" % -d

    # tasks: not completed, or completed within tasks_done_days
    tcut = now - dt.timedelta(days=cfg["tasks_done_days"])
    for iid, status, completed in con.execute("SELECT it.item_id, t.status, t.completed FROM item_task it "
                                              "JOIN tasks t ON t.id=it.task_id ORDER BY it.item_id").fetchall():
        if str(status or "").lower() != "completed":
            picked[iid] = "open task"
        else:
            c = C.parse_dt(completed)
            if c is not None and c >= tcut:
                picked[iid] = "task done in the last %d days" % cfg["tasks_done_days"]

    for iid in sorted(picked):
        sg.set_score(con, "item:%d" % iid, NAME, VERSION, 1, picked[iid])
    kinds = {}
    for r in con.execute("SELECT i.kind, COUNT(*) FROM items i JOIN kg_scores s ON s.subject_ref='item:'||i.id "
                         "AND s.signal='window' GROUP BY i.kind"):
        kinds[r[0]] = r[1]
    return {"window_items": len(picked), "by_kind": kinds, "settings_seeded": seeded}
