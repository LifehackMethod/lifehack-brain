"""delta.py: Grand Central V2 step 3. Compare what arrived in [since, now] against the baseline (everything before)
and report three kinds of surprise from ENVELOPE facts only (no body text exists here):
  NEW      a sender with no home in the baseline;
  CHANGED  a quiet project (user label) with a burst; a thread heating up;
  MISSING  an expected reply that never came; a regular correspondent gone silent (silence counts).
Each becomes a question for the morning read.
Step 1.2 (vision 3.9, equal weight): calendar and tasks get the same three kinds of surprise, compared against the snapshot
the last real morning read saved (snapshot() / compare_cal_tasks(); source "calendar" and "tasks" on each entry):
  NEW      an event or open task that was not there;   CHANGED  an event moved or retitled, a task's due date or title changed;
  MISSING  an upcoming event cancelled or removed, an open task dropped (gone, not completed).
A task he completed is not a surprise: it is listed as settled, no question. Thresholds come from setup/leans.json 'proposed_points.delta'
(PROPOSED, NOT APPROVED); nothing is hard-coded. Reads only; writes nothing, not even to the database."""
import datetime
import sqlite3
import statistics
import sys

import scorecard as S

DAY, HOUR = S.DAY, S.HOUR


def _fmt(ms):
    import datetime as dt
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).date().isoformat()


def _known_homes(con, cfg):
    """addresses that have a home outside the mail itself: his starter list, and addresses linked to a person in the memory"""
    homes = {a.lower() for a in (cfg.leans.get("starter_people") or []) if isinstance(a, str)}
    try:
        # the one model (2.4 reader 3): an address with a current address_of link to a person
        homes |= {r[0].lower() for r in con.execute(
            "SELECT ad.name FROM kg_things ad JOIN kg_current_links l ON l.from_id=ad.id AND l.kind='address_of' "
            "JOIN kg_things p ON p.id=l.to_id AND p.kind='person' WHERE ad.kind='address'")}
    except sqlite3.OperationalError as e:
        # an older memory without the link tables: no linked addresses, the starter list alone stands -- said, not hidden
        print("delta: linked-address lookup skipped (%s)" % e, file=sys.stderr)
    return homes


def run(con, since_ms, now_ms, points=None, cfg=None, prev_snapshot=None, day=None):
    """Email compare always; calendar and tasks compare too when `prev_snapshot` (from snapshot()) and `day` are given.
    Their entries carry source "calendar"/"tasks", and also come back whole under out["calendar_tasks"]."""
    cfg = cfg or S.Config.load()
    P = points or cfg.points["delta"]
    mb = S.Mailbox.load(con)
    me = mb.me
    out = {"new": [], "changed": [], "missing": [], "questions": [], "skipped_rows": list(mb.skipped_ids), "calendar_tasks": None}   # ids of message rows with a bad date; len() is the count
    homes = _known_homes(con, cfg)

    # ---- NEW: a sender with no home --------------------------------------------------------------------------
    base_known = set()
    for m in mb.msgs:
        if m["ms"] >= since_ms:
            break
        if m["sent"]:
            base_known |= set(m["to"]) | set(m["cc"])
        else:
            base_known.add(m["frm"])
    seen = {}
    for m in mb.msgs:
        if since_ms <= m["ms"] <= now_ms and not m["sent"] and m["frm"] and m["frm"] not in me:
            seen.setdefault(m["frm"], []).append(m)
    for addr, ms_ in sorted(seen.items()):
        if addr in base_known or addr in homes:
            continue
        auto = any(x["bulk"] for x in ms_)
        out["new"].append({"kind": "sender", "ref": addr, "first_ms": ms_[0]["ms"], "msgs": len(ms_), "threads": sorted({x["thread"] for x in ms_}),
                           "automated": auto, "evidence": "first seen %s, %d message(s), no earlier mail and no home in the memory" % (_fmt(ms_[0]["ms"]), len(ms_))})
        if not auto:
            out["questions"].append("New sender %s (first seen %s): who are they, and does a project or part of your life already own them?" % (addr, _fmt(ms_[0]["ms"])))

    # ---- CHANGED: a quiet project with a burst ----------------------------------------------------------------
    lookback = P["burst_lookback_days"] * DAY
    window_weeks = max((now_ms - since_ms) / DAY / 7.0, 1e-9)
    user_labels = {r[0]: r[1] for r in con.execute("SELECT id, name FROM labels WHERE type='user'")}
    per = {lid: {"base": 0, "win": 0, "win_first": None} for lid in user_labels}
    for m in mb.msgs:
        for lid in m["label_ids"]:
            if lid in per:
                if since_ms - lookback <= m["ms"] < since_ms:
                    per[lid]["base"] += 1
                elif since_ms <= m["ms"] <= now_ms:
                    per[lid]["win"] += 1
                    per[lid]["win_first"] = per[lid]["win_first"] or m["ms"]
    for lid, c in sorted(per.items(), key=lambda kv: user_labels[kv[0]]):
        rate = c["base"] / (P["burst_lookback_days"] / 7.0)
        expected = rate * window_weeks
        if rate <= P["burst_quiet_max_per_week"] and c["win"] >= P["burst_min_msgs"] and c["win"] / max(expected, 1.0) >= P["burst_ratio"]:
            name = user_labels[lid]
            out["changed"].append({"kind": "burst", "ref": name, "baseline_per_week": round(rate, 2), "in_window": c["win"],
                                   "evidence": "%d messages since %s against about %.1f a week before" % (c["win"], _fmt(since_ms), rate)})
            out["questions"].append("'%s' has been quiet (about %.1f a week) and had %d messages since %s: what changed?" % (name, rate, c["win"], _fmt(since_ms)))

    # ---- CHANGED: a thread heating up ---------------------------------------------------------------------
    lo = now_ms - P["heat_window_hours"] * HOUR
    for t, th in sorted(mb.by_thread.items()):
        recent = [x for x in th if lo <= x["ms"] <= now_ms]
        who = {x["frm"] for x in recent}
        if len(recent) >= P["heat_min_msgs"] and len(who) >= P["heat_min_senders"]:
            out["changed"].append({"kind": "heating", "ref": t, "in_window": len(recent), "people": len(who),
                                   "evidence": "%d messages from %d people in %d hours" % (len(recent), len(who), P["heat_window_hours"])})
            out["questions"].append("A thread has %d messages from %d people in %d hours: does it need you now?" % (len(recent), len(who), P["heat_window_hours"]))

    # ---- MISSING: an expected reply that never came -----------------------------------------------------------
    reply_delays = {}   # address -> list of ms between his message to them and their next message to him
    for th in mb.by_thread.values():
        pend = {}
        for m in th:
            if m["sent"]:
                for a in set(m["to"]) | set(m["cc"]):
                    pend.setdefault(a, m["ms"])
            elif m["frm"] in pend:
                reply_delays.setdefault(m["frm"], []).append(m["ms"] - pend.pop(m["frm"]))
    for t, th in sorted(mb.by_thread.items()):
        last = th[-1]
        if not last["sent"] or last["ms"] > now_ms:
            continue
        age_d = (now_ms - last["ms"]) / DAY
        if age_d > P["missing_forget_days"]:
            continue
        who = [a for a in last["to"] if a not in me]
        if not who:
            continue
        a = who[0]
        d = reply_delays.get(a, [])
        if len(d) < P["missing_min_past_replies"]:
            continue
        usual = statistics.median(d) / DAY
        wait = max(P["missing_floor_days"], P["missing_reply_factor"] * usual)
        if age_d > wait:
            out["missing"].append({"kind": "reply", "ref": t, "who": a, "days_silent": round(age_d, 1), "usual_reply_days": round(usual, 2),
                                   "evidence": "you wrote %s; no reply in %.0f days; they usually answer in about %.1f" % (_fmt(last["ms"]), age_d, usual)})
            out["questions"].append("You wrote to %s on %s and no reply has come in %.0f days (they usually answer within about %.1f): are you still expecting one?" % (
                a, _fmt(last["ms"]), age_d, max(usual, 0.1)))

    # ---- MISSING: a regular correspondent gone silent ----------------------------------------------------------
    for a, ms_ in sorted(mb.from_msgs.items()):
        if a in me or len(ms_) < P["cadence_min_msgs"] or not mb.sent_to_in.get(a) or any(x["bulk"] for x in ms_[-3:]):
            continue
        ts = [x["ms"] for x in ms_ if x["ms"] < now_ms]
        gaps = [(b - c) / DAY for c, b in zip(ts, ts[1:])]
        if len(gaps) < P["cadence_min_msgs"] - 1:
            continue
        g = statistics.median(gaps)
        silent = (now_ms - ts[-1]) / DAY
        if g > 0 and silent >= P["missing_floor_days"] and P["cadence_silence_factor"] * g < silent <= max(10 * P["cadence_silence_factor"] * g, P["missing_forget_days"]) and ts[-1] < since_ms:
            out["missing"].append({"kind": "silence", "ref": a, "days_silent": round(silent, 1), "usual_gap_days": round(g, 1),
                                   "evidence": "usually writes every ~%.0f days; silent %.0f days" % (g, silent)})
            out["questions"].append("%s usually writes every ~%.0f days and has been silent %.0f days: is that expected?" % (a, g, silent))
    for kind in ("new", "changed", "missing"):
        for e in out[kind]:
            e.setdefault("source", "email")
    if prev_snapshot is not None and day:
        ct = compare_cal_tasks(prev_snapshot, snapshot(con, day), day)
        out["calendar_tasks"] = ct
        for src in ("calendar", "tasks"):
            for kind in ("new", "changed", "missing"):
                out[kind] += ct[src][kind]
        out["questions"] += ct["questions"]
    return out


# ================================================================ calendar and tasks (equal weight with email)

def _title(v):
    return " ".join(str(v or "").split())[:200] or "(no title)"


def snapshot(con, day):
    """What the calendar and the task list look like today, small enough to keep: every event starting today or later
    (any status), every task that is open or was touched in the last 60 days. Read-only. Saved by the morning read after a
    real run and handed back next time as `prev_snapshot`. -> {"day", "calendar": {id: {...}}, "tasks": {id: {...}}}"""
    events, tasks = {}, {}
    for r in con.execute("SELECT id, summary, start, end, status, location FROM calendar_events WHERE substr(start,1,10) >= ?", (day,)):
        events[str(r[0])] = {"title": _title(r[1]), "start": str(r[2] or ""), "end": str(r[3] or ""), "location": _title(r[5]) if r[5] else "",
                          "cancelled": str(r[4] or "").lower() == "cancelled"}
    cutoff = (datetime.date.fromisoformat(day) - datetime.timedelta(days=60)).isoformat()
    for r in con.execute("SELECT id, title, status, due, updated FROM tasks"):
        done = str(r[2] or "").lower() == "completed"
        if done and str(r[4] or "")[:10] < cutoff:
            continue
        tasks[str(r[0])] = {"title": _title(r[1]), "due": str(r[3] or "")[:10], "done": done}
    return {"day": day, "calendar": events, "tasks": tasks}


def _in_window(start, day, ahead_days):
    d0 = datetime.date.fromisoformat(day)
    s = str(start or "")[:10]
    try:
        n = (datetime.date.fromisoformat(s) - d0).days
    except ValueError:
        return False
    return 0 <= n <= ahead_days


def compare_cal_tasks(prev, cur, day, ahead_days=14):
    """Pure compare of two snapshots. Calendar looks at events starting in [day, day+ahead_days]; tasks look at open tasks.
    -> {"calendar": {"new","changed","missing"}, "tasks": {...}, "questions": [...]}. Each entry has id, ref (title), source,
    evidence, question; an entry he has no need to be asked about carries "settled" (the reason) instead of a question."""
    out = {"calendar": {"new": [], "changed": [], "missing": []}, "tasks": {"new": [], "changed": [], "missing": []}, "questions": []}
    pc, cc = prev.get("calendar") or {}, cur.get("calendar") or {}
    for i, e in sorted(cc.items()):
        if e["cancelled"]:
            continue
        p = pc.get(i)
        if p is None or p["cancelled"]:
            if _in_window(e["start"], day, ahead_days):
                q = "Calendar: a new event '%s' on %s: does it change the plan for that week?" % (e["title"], e["start"][:10])
                out["calendar"]["new"].append({"kind": "event", "source": "calendar", "id": i, "ref": e["title"], "start": e["start"],
                                               "evidence": "not on the calendar at the last read", "question": q})
        elif (p["start"], p["end"], p["title"], p["location"]) != (e["start"], e["end"], e["title"], e["location"]) \
                and (_in_window(e["start"], day, ahead_days) or _in_window(p["start"], day, ahead_days)):
            if p["start"] != e["start"] or p["end"] != e["end"]:
                what = "moved from %s to %s" % (p["start"][:16], e["start"][:16])
            else:
                what = "renamed from '%s'" % p["title"] if p["title"] != e["title"] else "location changed"
            q = "Calendar: '%s' %s: what does that knock on?" % (e["title"], what)
            out["calendar"]["changed"].append({"kind": "event", "source": "calendar", "id": i, "ref": e["title"], "start": e["start"],
                                               "evidence": what, "question": q})
    for i, p in sorted(pc.items()):
        e = cc.get(i)
        if p["cancelled"] or not _in_window(p["start"], day, ahead_days) or (e is not None and not e["cancelled"]):
            continue
        out["calendar"]["missing"].append({"kind": "event", "source": "calendar", "id": i, "ref": p["title"], "start": p["start"],
                                           "evidence": "was on the calendar for %s; now %s" % (p["start"][:10], "cancelled" if e else "gone"),
                                           "question": "Calendar: '%s' on %s is no longer on the calendar: was that on purpose?" % (p["title"], p["start"][:10])})
    pt, ct = prev.get("tasks") or {}, cur.get("tasks") or {}
    for i, t in sorted(ct.items()):
        p = pt.get(i)
        if t["done"]:
            if p is not None and not p["done"]:       # he finished it: not a surprise, not a question
                out["tasks"]["changed"].append({"kind": "task", "source": "tasks", "id": i, "ref": t["title"], "evidence": "completed", "settled": "completed"})
            continue
        due = " (due %s)" % t["due"] if t["due"] else ""
        if p is None or p["done"]:
            out["tasks"]["new"].append({"kind": "task", "source": "tasks", "id": i, "ref": t["title"], "due": t["due"],
                                        "evidence": "not on the list at the last read",
                                        "question": "Task: a new task '%s'%s: does it belong in this week?" % (t["title"], due)})
        elif (p["due"], p["title"]) != (t["due"], t["title"]):
            what = "due date changed from %s to %s" % (p["due"] or "none", t["due"] or "none") if p["due"] != t["due"] else "renamed from '%s'" % p["title"]
            out["tasks"]["changed"].append({"kind": "task", "source": "tasks", "id": i, "ref": t["title"], "due": t["due"], "evidence": what,
                                            "question": "Task: '%s' %s: what changed?" % (t["title"], what)})
    for i, p in sorted(pt.items()):
        if not p["done"] and i not in ct:
            out["tasks"]["missing"].append({"kind": "task", "source": "tasks", "id": i, "ref": p["title"], "due": p["due"],
                                            "evidence": "open at the last read; gone from the list, not completed",
                                            "question": "Task: '%s'%s is gone from the list without being completed: dropped on purpose?" % (
                                                p["title"], " (was due %s)" % p["due"] if p["due"] else "")})
    for src in ("calendar", "tasks"):
        for kind in ("new", "changed", "missing"):
            out["questions"] += [e["question"] for e in out[src][kind] if e.get("question")]
    return out
