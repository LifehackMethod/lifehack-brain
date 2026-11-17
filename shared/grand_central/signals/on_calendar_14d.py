"""on_calendar_14d: the sender is an attendee of a calendar event starting in the next 14 days. Only fires when true."""
import datetime as dt

import common as C

NAME, VERSION = "on_calendar_14d", 1


def compute(con, item_ids):
    info = C.email_info(con, item_ids)
    now = C.now()
    hi = now + dt.timedelta(days=14)
    soonest = {}   # address -> (start dt, date, summary)
    for start, status, att, summary in con.execute("SELECT start, status, attendee_emails, summary FROM calendar_events"):
        s = C.parse_dt(start)
        if s is None or not (now <= s <= hi) or str(status or "").lower() == "cancelled":
            continue
        for a in C.jlist(att):
            if a not in soonest or s < soonest[a][0]:
                soonest[a] = (s, C.day(start), summary or "(no title)")
    out = {}
    for iid, em in info.items():
        if em["from"] in soonest:
            _, d, summary = soonest[em["from"]]
            out[iid] = (1.0, "attends %s on %s" % (summary, d))
    return out
