#!/usr/bin/env python3
"""intake_plumbing_check.py: ONE reusable, code-only, READ-ONLY check of Grand Central's intake and plumbing.

No model call, no email body read, nothing written to the live data. It answers two questions:

  (i)  INTAKE, source vs system. Is everything that is in Google (mail, calendar, tasks) also in the system's database
       and front room, and is every gap explained (held, quarantined, excluded label, lag, stale pull) or named a REAL MISS?
  (ii) PLUMBING. Is every input the planning-weekly producer reads present, current and consistent with (i)?

Everything one person owns comes from the engine's settings loader (gc_settings) or from arguments; nothing is named here.

Read-only rules this file obeys:
  * the live database is opened mode=ro; the plumbing reads (gc person/org/upcoming/due/week/urgent) run against a COPY made
    with sqlite's backup API (--scratch);
  * Google is reached only the way the live jobs reach it: the rig login picked by rig_env.apply_to_this_process(), the same
    gws program, email_fetch's own list/get calls (envelope metadata: only ids, dates and label ids are kept; no header text is
    stored), and the same safe_calendar.py / safe_tasks.py doors in isolate mode (their scratch file is deleted unread);
  * the one thread-door call (transcripts.read_thread, read-only Caller) keeps only ok/refused and a byte count; the door's access
    log append is switched off for this process so the front room is not written.

Usage:
    python3 intake_plumbing_check.py --scratch DIR [--result-md FILE] [--today YYYY-MM-DD] [--days-ahead 7]
                                     [--db PATH] [--branch-draft FILE] [--no-google]
Exit 0 = no REAL MISS and nothing missing/error in the plumbing; 1 = at least one; 2 = could not run.
Python 3.9 compatible.
"""
import argparse
import concurrent.futures
import datetime
import glob
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zoneinfo

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE)
import gc_settings  # noqa: E402

NY = zoneinfo.ZoneInfo("America/New_York")   # the envelope window's day, as pull.py's window_bounds
LAG_MIN = 20
RETRIES = 2
RESULTS = {"intake": {}, "plumbing": [], "google_calls": {}, "notes": []}


def cut(s, n=12):
    s = str(s or "")
    return s if len(s) <= n else s[:n] + "..."


def note(msg):
    RESULTS["notes"].append(msg)


def count_call(kind):
    RESULTS["google_calls"][kind] = RESULTS["google_calls"].get(kind, 0) + 1


def day_bounds_ms(day):
    lo = datetime.datetime(day.year, day.month, day.day, tzinfo=NY)
    hi = lo + datetime.timedelta(days=1)
    return int(lo.timestamp() * 1000), int(hi.timestamp() * 1000)


def utc_iso(ms):
    return datetime.datetime.fromtimestamp(ms / 1000.0, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(s):
    try:
        return datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def local_date_of(start):
    """The local calendar date an event's start falls on (an all-day date stays as it is)."""
    s = str(start or "")
    if len(s) == 10:
        return s
    t = parse_ts(s)
    return t.astimezone(NY).date().isoformat() if t else ""


# ------------------------------------------------------------------------------------------------ the system side (read-only)
def open_ro(path):
    con = sqlite3.connect("file:%s?mode=ro" % path, uri=True, timeout=20)
    con.execute("PRAGMA query_only=1")
    return con


def copy_db(path, dest):
    src = open_ro(path)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    os.chmod(dest, 0o600)


# ------------------------------------------------------------------------------------------------ the source side (Google)
class Source(object):
    """Google reads through the live jobs' own doors. Built only after rig_env.apply_to_this_process()."""

    def __init__(self):
        import rig_env
        self.rig_env = rig_env
        rig_env.apply_to_this_process()
        sys.path.insert(0, rig_env.EMAIL_DOOR_DIR)
        import email_fetch
        self.ef = email_fetch

    def confirm_program(self):
        """What would be called: the exact binary and the login folder, for the report (no Google call here)."""
        gws = self.ef._gws()
        env = self.ef._gws_env()
        return {"gws": gws, "gws_is_file": os.path.isfile(gws),
                "login_dir": env.get("GOOGLE_WORKSPACE_CLI_CONFIG_DIR"),
                "keyring": env.get("GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND"),
                "broad_login_selected": bool(env.get("GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE")),
                "calendar_door": self.rig_env.SAFE_CALENDAR, "tasks_door": self.rig_env.SAFE_TASKS}

    def paused(self):
        try:
            self.ef.check_paused("rig")
            return False
        except Exception as e:  # noqa: BLE001
            return "%s: %s" % (type(e).__name__, e)

    def gmail(self, kind, fn, *a):
        err = None
        for _ in range(RETRIES + 1):
            count_call(kind)
            data, err = fn(*a)
            if err is None:
                return data
        raise RuntimeError("%s failed: %s" % (kind, err))

    def labels(self):
        return (self.gmail("gmail.labels.list", self.ef.labels_list) or {}).get("labels", [])

    def ids_with_label(self, label_id):
        ids, token = set(), None
        while True:
            params = {"labelIds": [label_id], "maxResults": 500}
            if token:
                params["pageToken"] = token
            data = self.gmail("gmail.messages.list", lambda p=params: self.ef._call(
                ["messages", "list"], dict({"userId": "me"}, **p)))
            ids |= {m.get("id") for m in (data or {}).get("messages", []) if m.get("id")}
            token = (data or {}).get("nextPageToken")
            if not token:
                return ids

    def day_envelopes(self, lo, hi, cap=400):
        """The fast clock's envelope scope: threads.list (no q, includeSpamTrash, newest first) then threads.get metadata,
        paged until a whole page is older than the window. Keeps only id, thread, ms, label ids, sender (cut)."""
        out, token, budget = {}, None, cap
        while budget > 0:
            params = {"maxResults": min(25, budget), "includeSpamTrash": True}
            if token:
                params["pageToken"] = token
            data = self.gmail("gmail.threads.list", self.ef.list_threads, params)
            page = [t.get("id") for t in (data or {}).get("threads", []) if t.get("id")][:budget]
            budget -= len(page)
            newest_seen = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
                got = list(pool.map(lambda tid: self._get_thread(tid), page))
            for tid, th in zip(page, got):
                newest = 0
                for m in (th or {}).get("messages") or []:
                    try:
                        ms = int(m.get("internalDate") or 0)
                    except (TypeError, ValueError):
                        ms = 0
                    newest = max(newest, ms)
                    if ms and lo <= ms < hi:
                        hdr = dict((h.get("name", "").lower(), h.get("value", ""))
                                   for h in (m.get("payload") or {}).get("headers", []) if h.get("name", "").lower() == "from")
                        frm = re.sub(r"^.*<|>.*$", "", hdr.get("from", "")).strip()
                        out[m["id"]] = {"id": m["id"], "thread": tid, "ms": ms, "labels": list(m.get("labelIds") or []),
                                        "from": cut(frm, 14)}
                newest_seen.append(newest)
            token = (data or {}).get("nextPageToken")
            if not token or not page or (newest_seen and all(n < lo for n in newest_seen)):
                break
        return out

    def _get_thread(self, tid):
        for _ in range(RETRIES + 1):
            count_call("gmail.threads.get(metadata)")
            data, err = self.ef.get_thread(tid, "metadata")
            if err is None:
                return data
        return None

    def door(self, kind, script, params):
        """safe_calendar.py / safe_tasks.py in isolate mode, as pull.run_door runs them. Their scratch file (free text) is
        removed unread."""
        err = "?"
        for _ in range(RETRIES + 1):
            count_call(kind)
            try:
                p = subprocess.run([sys.executable, script, json.dumps(params)], capture_output=True, text=True,
                                   timeout=180, env=os.environ.copy())
            except Exception as e:  # noqa: BLE001
                err = str(e)
                continue
            if p.returncode in (0, 1):
                try:
                    data = json.loads(p.stdout[p.stdout.find("{"):])
                except ValueError as e:
                    err = "json parse: %s" % e
                    continue
                sc = data.get("_reader_scratch")
                if sc and os.path.isfile(sc):
                    try:
                        os.remove(sc)
                    except OSError:
                        pass
                return data
            err = (p.stderr.strip().splitlines() or ["?"])[-1][:200]
        raise RuntimeError("%s failed: %s" % (kind, err))

    def calendar(self, t_min, t_max):
        items, token = [], None
        while True:
            params = {"calendarId": "primary", "timeMin": t_min, "timeMax": t_max, "singleEvents": True,
                      "orderBy": "startTime", "maxResults": 250}
            if token:
                params["pageToken"] = token
            d = self.door("calendar.events.list(door)", self.rig_env.SAFE_CALENDAR, params)
            items += d.get("items") or []
            token = d.get("nextPageToken")
            if not token:
                return items

    def tasks(self):
        count_call("tasks.tasklists.list")
        tl = subprocess.run(["gws", "tasks", "tasklists", "list", "--params", "{}"], capture_output=True, text=True,
                            timeout=60, env=os.environ.copy())
        if tl.returncode != 0:
            raise RuntimeError("tasklists.list failed: %s" % ((tl.stderr or "?").strip().splitlines() or ["?"])[-1][:200])
        lists = json.loads(tl.stdout[tl.stdout.find("{"):]).get("items") or []
        out = []
        for lst in lists:
            token = None
            while True:
                params = {"tasklist": lst.get("id"), "showCompleted": True, "showHidden": True, "maxResults": 100}
                if token:
                    params["pageToken"] = token
                d = self.door("tasks.tasks.list(door)", self.rig_env.SAFE_TASKS, params)
                out += [dict(t, _list=lst.get("id")) for t in d.get("items") or []]
                token = d.get("nextPageToken")
                if not token:
                    break
        return out, len(lists)


# ------------------------------------------------------------------------------------------------ settings the live pull uses
def read_and_exclude_labels():
    """(read names, exclude names, note). The read labels come from the engine's own decision (scorecard.decide_read_labels over
    setup labels.json plus the mailroom's reader-config.json); the excluded ones from the same mailroom config."""
    import scorecard
    warn = []
    doc = scorecard.load_labels_doc(gc_settings.setup_path("labels.json"))
    try:
        mail = scorecard.mailroom_read_labels()
    except Exception as e:  # noqa: BLE001
        mail = set()
        warn.append("mailroom config unreadable (%s): read labels are setup-only" % type(e).__name__)
    readable, _refuse, w = scorecard.decide_read_labels(doc, mail)
    warn += w
    excl = set()
    try:
        cfg = os.path.join(gc_settings.mailroom_install_dir(), "reader-config.json")
        with open(cfg, encoding="utf-8") as f:
            excl = {str(x).strip().lower() for x in json.load(f).get("exclude_labels") or []}
    except Exception as e:  # noqa: BLE001
        warn.append("exclude labels unreadable (%s)" % type(e).__name__)
    return readable, excl, warn


# ------------------------------------------------------------------------------------------------ CHECK (i) INTAKE
def classify_missing(mid, info, ctx):
    """The reason a source message is not in the system. info: ms, labels (ids)."""
    if mid in ctx["quarantined_ids"]:
        return "quarantined (rig.db)"
    if mid in ctx["held"]:
        return "held: %s" % ctx["held"][mid]
    names = {ctx["label_name"].get(l, l).lower() for l in info.get("labels", [])}
    if names & ctx["exclude"]:
        return "excluded label"
    if info["ms"] >= ctx["lag_cut_ms"]:
        return "lag (arrived in the last %d min)" % LAG_MIN
    return None


def stream_compare(src_ids, sys_ids, src_info, ctx, pull_cut_ms=None, pull_note=""):
    missing, reasons = [], {}
    for mid in sorted(src_ids - sys_ids):
        r = classify_missing(mid, src_info.get(mid, {"ms": 0, "labels": []}), ctx)
        if r is None and pull_cut_ms is not None and src_info.get(mid, {}).get("ms", 0) > pull_cut_ms:
            r = "STALE PULL: arrived after the system's last pull (%s)" % pull_note
        if r is None:
            r = "REAL MISS"
            missing.append(mid)
        reasons.setdefault(r, []).append(mid)
    return missing, reasons


def check_intake(a, db, src, today, lo, hi, lag_cut_ms, fr_meta, facts):
    I = RESULTS["intake"]
    now_ms = int(datetime.datetime.now().timestamp() * 1000)
    labels_src = src.labels()
    label_name = dict((l["id"], l.get("name") or l["id"]) for l in labels_src)
    name_id = dict((str(l.get("name") or "").strip().lower(), l["id"]) for l in labels_src)
    read_names, excl_names, warn = read_and_exclude_labels()
    for w in warn:
        note(w)
    read_ids = {name_id[n] for n in read_names if n in name_id}
    I["read_labels"] = {"configured": len(read_names), "found_in_gmail": len(read_ids),
                        "not_found_names": sorted(n for n in read_names if n not in name_id)}
    I["exclude_labels"] = {"configured": len(excl_names), "found_in_gmail": len({n for n in excl_names if n in name_id})}

    held = {}
    for r in (facts or {}).get("held_messages") or []:
        if isinstance(r, dict) and r.get("message_id"):
            held[r["message_id"]] = "%s/%s" % (r.get("status"), r.get("reason"))
    quarantined_ids = {r[0] for r in db.execute("SELECT item_id FROM quarantine WHERE kind='message'")}
    ctx = {"label_name": label_name, "exclude": excl_names, "held": held, "quarantined_ids": quarantined_ids,
           "lag_cut_ms": lag_cut_ms}

    # -- the day's envelopes from the source
    env = src.day_envelopes(lo, hi)
    I["envelopes_source_today"] = len(env)
    sys_msgs = {r[0]: {"ms": r[1]} for r in db.execute(
        "SELECT id, internal_date FROM messages WHERE internal_date>=? AND internal_date<?", (lo, hi))}
    daily = db.execute("SELECT last_success_at FROM source_state WHERE source='daily'").fetchone()
    env_wm = db.execute("SELECT last_success_at FROM source_state WHERE source='envelopes'").fetchone()
    max_ms = db.execute("SELECT max(internal_date) FROM messages").fetchone()[0] or 0
    pull_note = "newest stored message %s, daily pull %s, envelope watermark %s" % (
        utc_iso(max_ms) if max_ms else "none", daily[0] if daily else "none", env_wm[0] if env_wm else "none")
    if not env_wm:
        note("rig.db has no 'envelopes' source_state row: the fast clock's envelope pull has not run on this data (the live pinned code predates it); mail reaches rig.db only through the daily pull")
    I["system_mail_pull"] = {"newest_stored_message": utc_iso(max_ms) if max_ms else None,
                             "daily_pull": daily[0] if daily else None,
                             "envelope_watermark_row": env_wm[0] if env_wm else None}
    missing, reasons = stream_compare(set(env), set(sys_msgs), env, ctx, pull_cut_ms=max_ms, pull_note=pull_note)
    extra = sorted(set(sys_msgs) - set(env))
    I["envelopes"] = {"source": len(env), "system": len(sys_msgs), "gaps_by_reason": dict((k, len(v)) for k, v in reasons.items()),
                      "REAL_MISS_ids": missing, "in_system_not_in_source_ids": extra}
    I["envelopes_gap_examples"] = dict((k, [{"id": i, "from": env[i]["from"], "ms": utc_iso(env[i]["ms"])} for i in v[:6]])
                                       for k, v in reasons.items())

    # -- read-label message ids (all time, as the live label listing does) against the front room catalogue and rig.db
    src_read_all = set()
    per_label = {}
    for lid in sorted(read_ids):
        ids = src.ids_with_label(lid)
        per_label[label_name[lid]] = len(ids)
        src_read_all |= ids
    I["read_label_ids_source_all_time"] = len(src_read_all)
    cat_ids = {r["message_id"] for r in fr_meta if r.get("message_id")}
    db_ids = {r[0] for r in db.execute("SELECT id FROM messages")}
    sys_any = cat_ids | db_ids
    cat_today = {r["message_id"] for r in fr_meta if r.get("internal_ms") and lo <= int(r["internal_ms"]) < hi}
    src_read_today = {m for m in src_read_all if m in env}
    sys_read_today = cat_today | (set(sys_msgs) & src_read_all)
    # the mailroom's own newest pass: anything that arrived after it has not been offered yet
    pass_at = parse_ts((facts or {}).get("written_at")) if facts else None
    pass_ms = int(pass_at.timestamp() * 1000) if pass_at else None
    miss_t, reas_t = stream_compare(src_read_today, sys_read_today, env, ctx)
    I["read_labels_today"] = {"source": len(src_read_today), "system": len(sys_read_today),
                              "catalogue_today": len(cat_today),
                              "gaps_by_reason": dict((k, len(v)) for k, v in reas_t.items()), "REAL_MISS_ids": miss_t,
                              "in_system_not_in_source_ids": sorted(cat_today - src_read_today)}
    miss_all, reas_all = stream_compare(src_read_all, sys_any, {}, ctx)
    # all-time: no dates for ids we did not list today, so reasons other than held/quarantined are 'older than today, undated'
    undated = [m for m in miss_all if m not in env]
    I["read_labels_all_time"] = {"source": len(src_read_all), "system_any": len(src_read_all & sys_any),
                                 "not_in_system": len(src_read_all - sys_any),
                                 "held_or_quarantined": len((src_read_all - sys_any) & (set(held) | quarantined_ids)),
                                 "older_than_window_undated": len(undated), "per_label_counts": per_label,
                                 "mailroom_window_days_note": "the mailroom reads a rolling window (reader-config days); older ids are not expected in the front room",
                                 "mailroom_pass_written_at": (facts or {}).get("written_at")}
    

    # -- calendar: today + days-ahead, local dates
    d0 = today
    d1 = today + datetime.timedelta(days=a.days_ahead)
    t_min = datetime.datetime(d0.year, d0.month, d0.day, tzinfo=NY).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    e1 = d1 + datetime.timedelta(days=1)
    t_max = datetime.datetime(e1.year, e1.month, e1.day, tzinfo=NY).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    src_cal = dict((e["id"], e) for e in src.calendar(t_min, t_max)
                   if e.get("id") and e.get("status") != "cancelled")
    sys_cal = {}
    for r in db.execute("SELECT id, start, status FROM calendar_events"):
        if r[2] == "cancelled":
            continue
        ld = local_date_of(r[1])
        if d0.isoformat() <= ld <= d1.isoformat():
            sys_cal[r[0]] = r[1]
    q_cal = {r[0].split(":", 1)[-1]: r[1] for r in db.execute("SELECT item_id, verdict FROM quarantine WHERE kind='calendar_event'")}
    cal_wm = db.execute("SELECT last_success_at FROM source_state WHERE source='calendar'").fetchone()
    I["calendar"] = _compare_simple(set(src_cal), set(sys_cal), q_cal, cal_wm[0] if cal_wm else None,
                                    dict((k, (v.get("updated") or "")) for k, v in src_cal.items()))
    I["calendar"]["window"] = "%s .. %s" % (d0, d1)
    I["calendar"]["system_pull_state"] = cal_wm[0] if cal_wm else None

    # -- tasks: all open
    src_tasks_all, nlists = src.tasks()
    src_open = dict((t["id"], t) for t in src_tasks_all if t.get("id") and t.get("status") == "needsAction")
    sys_open = {r[0]: r[1] for r in db.execute("SELECT id, updated FROM tasks WHERE status='needsAction'")}
    q_task = {r[0].split(":", 1)[-1]: r[1] for r in db.execute("SELECT item_id, verdict FROM quarantine WHERE kind='task'")}
    task_wm = db.execute("SELECT last_success_at FROM source_state WHERE source='tasks'").fetchone()
    I["tasks"] = _compare_simple(set(src_open), set(sys_open), q_task, task_wm[0] if task_wm else None,
                                 dict((k, (v.get("updated") or "")) for k, v in src_open.items()))
    I["tasks"]["task_lists"] = nlists
    I["tasks"]["system_pull_state"] = task_wm[0] if task_wm else None
    # tasks completed in source but still open in system (a stale mirror), cheap to say
    src_done = {t["id"] for t in src_tasks_all if t.get("status") == "completed"}
    I["tasks"]["open_in_system_but_completed_in_source_ids"] = sorted(set(sys_open) & src_done)
    return env


def _compare_simple(src_ids, sys_ids, quarantined, pull_state, src_updated):
    """Calendar/tasks: reasons are quarantine (ids named in the quarantine table), lag (changed in the source since the last
    pull of that stream), or REAL MISS."""
    pull_t = parse_ts(pull_state) if pull_state else None
    miss, reasons = [], {}
    for i in sorted(src_ids - sys_ids):
        if i in quarantined:
            r = "quarantined (%s)" % quarantined[i]
        else:
            upd = parse_ts(src_updated.get(i)) if src_updated.get(i) else None
            if pull_t and upd and upd > pull_t:
                r = "lag (changed in the source after the last pull)"
            else:
                r = "REAL MISS"
                miss.append(i)
        reasons.setdefault(r, []).append(i)
    return {"source": len(src_ids), "system": len(sys_ids), "in_both": len(src_ids & sys_ids),
            "gaps_by_reason": dict((k, len(v)) for k, v in reasons.items()), "REAL_MISS_ids": miss,
            "in_system_not_in_source_ids": sorted(sys_ids - src_ids)}


# ------------------------------------------------------------------------------------------------ CHECK (ii) PLUMBING
def plumb(name, status, why):
    RESULTS["plumbing"].append({"input": name, "status": status, "why": why})


LISTS = [("needs-you", re.compile(r"^## Needs him", re.M)), ("Capacity", re.compile(r"^## Capacity", re.M)),
         ("unclassified", re.compile(r"^## Unclassified emails", re.M)),
         ("held/quarantined", re.compile(r"^(New held or quarantined|Held or quarantined since|Held \(not read\))", re.M)),
         ("overdue", re.compile(r"^## Overdue tasks", re.M))]


def lists_in(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return dict((n, bool(rx.search(text))) for n, rx in LISTS)


def check_morning_draft(a, notes, desk_folder, today):
    ctxdir = os.path.join(notes, "desks", desk_folder, "records", "context")
    files = sorted(glob.glob(os.path.join(ctxdir, "*-%s*.md" % gc_settings.default_desk())) or glob.glob(os.path.join(ctxdir, "*.md")))
    files = [f for f in files if re.match(r"\d{4}-\d{2}-\d{2}-", os.path.basename(f))]
    if not files:
        plumb("morning draft (live)", "missing", "no morning draft in %s" % ctxdir)
        return
    newest = files[-1]
    d = os.path.basename(newest)[:10]
    age = (today - datetime.date.fromisoformat(d)).days
    have = lists_in(newest)
    RESULTS["morning_draft_live"] = {"file": os.path.basename(newest), "lists": have}
    missing = [n for n, ok in have.items() if not ok]
    status = "ok" if age == 0 else ("stale" if age <= 2 else "missing")
    plumb("morning draft (live): %s" % os.path.basename(newest), status,
          "dated %s (%d day(s) old); lists present: %s; absent: %s (the live system runs the older pinned code)" % (
              d, age, ",".join(n for n, ok in have.items() if ok) or "none", ",".join(missing) or "none"))
    if a.branch_draft:
        if os.path.isfile(a.branch_draft):
            hb = lists_in(a.branch_draft)
            RESULTS["morning_draft_branch"] = {"file": os.path.basename(a.branch_draft), "lists": hb}
            plumb("morning draft (branch run): %s" % os.path.basename(a.branch_draft), "ok" if all(hb.values()) else "stale",
                  "lists present: %s; absent: %s" % (",".join(n for n, ok in hb.items() if ok) or "none",
                                                      ",".join(n for n, ok in hb.items() if not ok) or "none"))
        else:
            plumb("morning draft (branch run)", "missing", "file not found: %s" % a.branch_draft)
    # consistency with (i): the draft's held count against the mailroom's held list
    try:
        with open(newest, encoding="utf-8") as f:
            m = re.search(r"Held or quarantined since the last draft: (\d+)", f.read())
        facts_total = RESULTS.get("_facts_held_total")
        if m and facts_total is not None:
            plumb("held count: draft vs mailroom facts", "ok" if int(m.group(1)) == facts_total else "stale",
                  "draft says %s, the mailroom's held list holds %s" % (m.group(1), facts_total))
    except OSError:
        pass


def key_of(db, kind):
    r = db.execute("SELECT key FROM kg_things WHERE kind=? AND merged_into IS NULL AND retired_at IS NULL "
                   "ORDER BY (SELECT count(*) FROM kg_facts f WHERE f.subject_key=kg_things.key) DESC LIMIT 1", (kind,)).fetchone() \
        if _has_col(db, "kg_facts", "subject_key") else \
        db.execute("SELECT key FROM kg_things WHERE kind=? AND merged_into IS NULL AND retired_at IS NULL LIMIT 1", (kind,)).fetchone()
    return r[0] if r else None


def _has_col(db, table, col):
    return col in [r[1] for r in db.execute("PRAGMA table_info(%s)" % table)]


def run_gc_reads(a, copy_path, today, scratch):
    db = open_ro(copy_path)
    pk, ok_ = key_of(db, "person"), key_of(db, "organization")
    db.close()
    env = dict(os.environ)
    env["AGE_FRONT_ROOM"] = os.path.join(scratch, "gc-front-room")
    env["GC_STATE_ROOT"] = os.path.join(scratch, "gc-state")
    reads = [("person", ["person", pk]), ("org", ["org", ok_]),
             ("upcoming", ["upcoming", "--start", today.isoformat(), "--days", str(a.days_ahead)]),
             ("due", ["due"]), ("week", ["week", "--start", today.isoformat()]), ("urgent", ["urgent", "--limit", "10"])]
    out = {}
    for name, argv in reads:
        if None in argv:
            plumb("gc reads %s --json" % name, "missing", "no such person/organization found in the world model copy")
            out[name] = "skipped"
            continue
        p = subprocess.run([sys.executable, os.path.join(ENGINE, "gc.py"), "--db", copy_path] + argv + ["--json"],
                           capture_output=True, text=True, timeout=300, env=env)
        if p.returncode != 0:
            out[name] = "error"
            plumb("gc reads %s --json" % name, "error", "exit %s: %s" % (p.returncode, ((p.stderr or "").strip().splitlines() or ["?"])[-1][:140]))
            continue
        try:
            doc = json.loads(p.stdout)
        except ValueError:
            out[name] = "error"
            plumb("gc reads %s --json" % name, "error", "output is not JSON")
            continue
        empty = _is_empty(doc)
        out[name] = "empty" if empty else "ok"
        plumb("gc reads %s --json" % name, "empty" if empty else "ok",
              ("empty result (keys: %s)" % ",".join(sorted(doc)[:6])) if empty and isinstance(doc, dict) else
              "returns data (%d bytes)" % len(p.stdout))
    RESULTS["gc_reads"] = out
    RESULTS["gc_reads_keys"] = {"person": pk, "org": ok_}


def _is_empty(doc):
    if not doc:
        return True
    if isinstance(doc, dict):
        vals = [v for k, v in doc.items() if k not in ("asof", "start", "days", "count", "start_date", "end_date")]
        return all((v in (None, "", [], {}, 0)) for v in vals) if vals else True
    return False


def check_diaries(a, notes, today):
    import desk_list
    ids = sorted(desk_list.desk_ids())
    found = {}
    n_files = n_keys = 0
    newest = None
    for d in ids:
        folder, _e = desk_list.desk_folder(d)
        folder = folder or d
        root = os.path.join(notes, "desks", folder, "diary")
        if not os.path.isdir(root):
            continue
        for day in range(a.diary_days):
            dt = today - datetime.timedelta(days=day)
            p = os.path.join(root, "%04d" % dt.year, "%02d" % dt.month, "%02d.md" % dt.day)
            if os.path.isfile(p):
                with open(p, encoding="utf-8", errors="replace") as f:
                    head = f.read(6000)
                m = re.match(r"\A---\n(.*?)\n---\n", head, re.S)
                mentions = None
                if m:
                    mm = re.search(r"^mentions:\s*(.*)$", m.group(1), re.M)
                    if mm:
                        mentions = len([x for x in re.split(r"\s*,\s*", mm.group(1).strip().strip("[]")) if x.strip()])
                found.setdefault(d, []).append({"day": dt.isoformat(), "mentions": mentions})
                n_files += 1
                if mentions:
                    n_keys += mentions
                newest = max(newest or dt, dt)
    RESULTS["diaries"] = {"desks_in_list": len(ids), "desks_with_entries_in_window": len(found), "entries": n_files,
                          "entries_with_mentions_key": sum(1 for v in found.values() for e in v if e["mentions"] is not None),
                          "mention_keys_total": n_keys, "per_desk": dict((k, v) for k, v in found.items())}
    if not n_files:
        plumb("diaries (last %d days)" % a.diary_days, "missing", "no diary entry found in %d desk(s) over %d days" % (len(ids), a.diary_days))
        return
    age = (today - newest).days
    with_m = RESULTS["diaries"]["entries_with_mentions_key"]
    plumb("diaries (last %d days)" % a.diary_days, "ok" if age <= 1 and with_m else "stale",
          "%d entries across %d of %d desk(s); newest %s (%d day(s) old); %d entr(ies) carry a mentions key (%d keys)" % (
              n_files, len(found), len(ids), newest, age, with_m, n_keys))


def check_door(today, fr_meta):
    import transcripts
    rows = [r for r in fr_meta if str(r.get("ingested_at") or "").startswith(today.isoformat()) and r.get("thread_id")]
    if not rows:
        rows = [r for r in fr_meta if r.get("thread_id")]
        which = "newest (none handed today)"
    else:
        which = "handed today"
    if not rows:
        plumb("read-only email door (read_thread)", "missing", "the catalogue has no thread to test")
        return
    tid = sorted(rows, key=lambda r: str(r.get("ingested_at")))[-1]["thread_id"]
    transcripts._log_access = lambda *x, **k: None      # no access-log append: the front room is not written by this check
    caller = transcripts.Caller("intake-plumbing-check", read_only=("Read",))
    try:
        text = transcripts.read_thread(tid, caller)
        n = len(text.encode("utf-8"))
        del text
        RESULTS["door"] = {"thread_id": tid, "outcome": "ok", "bytes": n, "which": which}
        plumb("read-only email door (read_thread)", "ok", "ok on one thread %s (id %s), %d bytes (text discarded)" % (which, tid, n))
    except transcripts.Refused as e:
        RESULTS["door"] = {"thread_id": tid, "outcome": "refused:%s" % e.reason, "which": which}
        plumb("read-only email door (read_thread)", "error", "refused: %s (thread %s)" % (e.reason, tid))


def check_life_map(notes, today):
    import desk_list
    folder, err = desk_list.planning_desk_folder()
    if not folder:
        plumb("Life Map", "missing", "planning-desk lookup: %s" % (err or "none"))
        return
    cands = [os.path.join(notes, "desks", folder, n) for n in ("life-map.md",)]
    cands += glob.glob(os.path.join(notes, "desks", folder, "**", "life-map*.md"), recursive=True)
    path = next((c for c in cands if os.path.isfile(c)), None)
    if not path:
        plumb("Life Map", "missing", "planning desk folder '%s' found, but no life-map file in it" % folder)
        return
    upd = None
    with open(path, encoding="utf-8", errors="replace") as f:
        head = f.read(3000)
    m = re.search(r"^updated_at:\s*(\d{4}-\d{2}-\d{2})", head, re.M)
    if m:
        upd = datetime.date.fromisoformat(m.group(1))
    mt = datetime.date.fromtimestamp(os.path.getmtime(path))
    age = (today - (upd or mt)).days
    RESULTS["life_map"] = {"file": os.path.basename(path), "updated_at": str(upd), "mtime": str(mt)}
    plumb("Life Map", "ok" if age <= 45 else "stale", "present via the planning-desk lookup (folder '%s'); updated_at %s, file modified %s (%d day(s) ago)" % (
        folder, upd, mt, age))


def check_answers(db, today):
    try:
        n, newest = db.execute("SELECT count(*), max(recorded_at) FROM kg_answers").fetchone()
        db.execute("SELECT id, subject_key, fact_key, value FROM kg_answers ORDER BY id DESC LIMIT 1").fetchone()
    except sqlite3.Error as e:
        plumb("kg_answers", "error", "cannot read: %s" % e)
        return
    RESULTS["kg_answers"] = {"count": n, "newest_recorded_at": newest}
    t = parse_ts(newest) if newest else None
    age = (today - t.astimezone(NY).date()).days if t else None
    plumb("kg_answers (his answers ledger)", "ok" if n and age is not None else "missing",
          "%s rows, newest recorded_at %s (%s day(s) ago); readable" % (n, newest, age))


def check_state(db, state_dir, today, now):
    """Lights and last-run proofs the fast clock and the morning job leave, and the sources' pull states."""
    out = {}
    for job in ("gc-fast-clock", "gc-morning", "gc-daily", "gc-midnight", "gc-snapshot"):
        p = os.path.join(state_dir, job, "last-run.txt")
        try:
            with open(p, encoding="utf-8") as f:
                line = f.read().strip().splitlines()[-1]
            m = re.search(r"\bat=(\S+)", line)
            out[job] = {"at": m.group(1) if m else None, "ok": line.split()[1] == "ok" if len(line.split()) > 1 else False}
        except (OSError, IndexError):
            out[job] = {"at": None, "ok": False}
    RESULTS["last_runs"] = out
    for job, maxage_h in (("gc-fast-clock", 1), ("gc-morning", 30)):
        o = out[job]
        t = parse_ts(o["at"]) if o["at"] else None
        if not t:
            plumb("%s last run" % job, "missing", "no last-run proof")
            continue
        age = (now - t).total_seconds() / 3600.0
        plumb("%s last run" % job, "ok" if o["ok"] and age <= maxage_h else "stale", "ok=%s at %s (%.1f h ago; expected within %s h)" % (o["ok"], o["at"], age, maxage_h))
    return out


# ------------------------------------------------------------------------------------------------ report
def write_md(path, today, now):
    I = RESULTS["intake"]
    L = ["# Phase 1a: intake and plumbing check, %s" % today, "",
         "Envelope facts only: ids, counts, dates, senders cut short. No email body or subject text. Read-only run; the weekly skill was not run.",
         "Run at %s." % now.strftime("%Y-%m-%dT%H:%M:%SZ"), "", "## Google calls made (kinds, counts)", ""]
    for k, v in sorted(RESULTS["google_calls"].items()):
        L.append("- %s: %d" % (k, v))
    if not RESULTS["google_calls"]:
        L.append("- none (--no-google)")
    L += ["", "## Check (i) intake: source vs system", ""]
    if I.get("envelopes"):
        e = I["envelopes"]
        L += ["- all-mail envelopes today: source %d, system (rig.db) %d; gaps by reason: %s; REAL MISS: %d" % (
            e["source"], e["system"], json.dumps(e["gaps_by_reason"]), len(e["REAL_MISS_ids"])),
              "  - in system but not in source: %d" % len(e["in_system_not_in_source_ids"]),
              "  - system mail pull: %s" % json.dumps(I["system_mail_pull"])]
        r = I["read_labels_today"]
        L += ["- read-label mail today: source %d, system (catalogue + rig.db) %d; gaps by reason: %s; REAL MISS: %d" % (
            r["source"], r["system"], json.dumps(r["gaps_by_reason"]), len(r["REAL_MISS_ids"])),
              "  - in system but not in source: %d" % len(r["in_system_not_in_source_ids"])]
        al = I["read_labels_all_time"]
        L += ["- read-label ids, all time: source %d, found in system %d, not in system %d (held or quarantined %d, older than today's window and not expected in the front room %d); mailroom pass written %s" % (
            al["source"], al["system_any"], al["not_in_system"], al["held_or_quarantined"], al["older_than_window_undated"], al["mailroom_pass_written_at"])]
        for k in ("calendar", "tasks"):
            c = I[k]
            L.append("- %s: source %d, system %d, in both %d; gaps by reason: %s; REAL MISS: %d; in system not in source: %d" % (
                k, c["source"], c["system"], c["in_both"], json.dumps(c["gaps_by_reason"]), len(c["REAL_MISS_ids"]), len(c["in_system_not_in_source_ids"])))
        L += ["", "REAL MISS ids (mail today): %s" % (", ".join(e["REAL_MISS_ids"]) or "none"),
              "REAL MISS ids (read-label mail today): %s" % (", ".join(r["REAL_MISS_ids"]) or "none"),
              "REAL MISS ids (calendar): %s" % (", ".join(I["calendar"]["REAL_MISS_ids"]) or "none"),
              "REAL MISS ids (tasks): %s" % (", ".join(I["tasks"]["REAL_MISS_ids"]) or "none")]
        ex = I.get("envelopes_gap_examples") or {}
        if ex:
            L += ["", "Gap examples (id | sender cut | arrived UTC):"]
            for k, v in ex.items():
                for x in v:
                    L.append("- %s: %s | %s | %s" % (k, x["id"], x["from"], x["ms"]))
    else:
        L.append("- intake not run (--no-google)")
    L += ["", "## Check (ii) plumbing", "", "| input | status | why |", "|---|---|---|"]
    for p in RESULTS["plumbing"]:
        L.append("| %s | %s | %s |" % (p["input"], p["status"], p["why"].replace("|", "/")))
    L += ["", "## Notes", ""] + ["- %s" % n for n in RESULTS["notes"]]
    text = "\n".join(L) + "\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)   # refuses to overwrite
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--scratch", required=True, help="local owner-only folder for output and the database copy")
    ap.add_argument("--result-md", help="write the human-readable result here (refuses to overwrite)")
    ap.add_argument("--today", help="YYYY-MM-DD (default: today, local)")
    ap.add_argument("--days-ahead", type=int, default=7)
    ap.add_argument("--diary-days", type=int, default=4)
    ap.add_argument("--db", help="the live database (default: the engine's)")
    ap.add_argument("--branch-draft", help="a draft produced by branch code, to list its code lists")
    ap.add_argument("--no-google", action="store_true", help="skip every Google call (plumbing only)")
    a = ap.parse_args(argv)

    os.makedirs(a.scratch, exist_ok=True)
    os.chmod(a.scratch, 0o700)
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    now = datetime.datetime.now(datetime.timezone.utc)
    lo, hi = day_bounds_ms(today)
    lag_cut_ms = int(now.timestamp() * 1000) - LAG_MIN * 60 * 1000
    db_path = a.db or gc_settings.db_path()
    db = open_ro(db_path)
    notes = gc_settings.configured_notes_root() if hasattr(gc_settings, "configured_notes_root") else None
    sys.path.insert(0, gc_settings.SHARED)
    import desk_list  # noqa: E402  (sibling in shared/)
    import transcripts
    fr_meta = transcripts.catalogue_meta()
    drop = None
    facts = None
    try:
        drop = gc_settings.drop_dir()
        with open(os.path.join(drop, "facts", "_reader_pass.json"), encoding="utf-8") as f:
            facts = json.load(f)
        RESULTS["_facts_held_total"] = facts.get("held_messages_total")
    except Exception as e:  # noqa: BLE001
        note("the mailroom's facts file could not be read (%s): held reasons unavailable" % type(e).__name__)
    gate_ok = True
    if not a.no_google:
        try:
            src = Source()
            RESULTS["google_program"] = src.confirm_program()
            gp = RESULTS["google_program"]
            if gp["broad_login_selected"] or not gp["gws_is_file"] or not (gp["login_dir"] or "").endswith(".config/gws-rig") \
                    or gp["keyring"] != "file":
                print("STOP: the Google call would not be the live jobs' own: %s" % json.dumps(gp), file=sys.stderr)
                return 2
            paused = src.paused()
            if paused:
                print("STOP: the rig unit is paused: %s" % paused, file=sys.stderr)
                return 2
            count_call("gmail.getProfile")
            if not src.ef.preflight():
                print("STOP: rig login preflight failed (getProfile did not answer)", file=sys.stderr)
                return 2
            check_intake(a, db, src, today, lo, hi, lag_cut_ms, fr_meta, facts)
        except Exception as e:  # noqa: BLE001
            gate_ok = False
            note("INTAKE CHECK FAILED: %s: %s" % (type(e).__name__, str(e)[:200]))
    else:
        note("--no-google: check (i) not run")

    # ---- plumbing
    copy_path = os.path.join(a.scratch, "rig-copy.db")
    copy_db(db_path, copy_path)
    try:
        folder, err = desk_list.planning_desk_folder()
        if not folder:
            plumb("planning desk", "missing", err or "unknown")
        else:
            check_morning_draft(a, notes, folder, today)
            check_life_map(notes, today)
        check_diaries(a, notes, today)
        run_gc_reads(a, copy_path, today, a.scratch)
        check_door(today, fr_meta)
        check_answers(db, today)
        check_state(db, gc_settings.state_dir(), today, now)
    finally:
        db.close()

    out_json = os.path.join(a.scratch, "intake_plumbing_check.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(dict((k, v) for k, v in RESULTS.items() if not k.startswith("_")), f, indent=1, sort_keys=True, default=str)
    os.chmod(out_json, 0o600)
    if a.result_md:
        write_md(a.result_md, today, now)
    I = RESULTS["intake"]
    real = sum(len(v.get("REAL_MISS_ids", [])) for k, v in I.items() if isinstance(v, dict))
    bad = [p for p in RESULTS["plumbing"] if p["status"] in ("missing", "error")]
    print("intake REAL MISS: %d; plumbing missing/error: %d; stale: %d; json: %s" % (
        real, len(bad), sum(1 for p in RESULTS["plumbing"] if p["status"] == "stale"), out_json))
    for p in RESULTS["plumbing"]:
        print("  [%s] %s: %s" % (p["status"], p["input"], p["why"]))
    return 0 if (gate_ok and not real and not bad) else 1


if __name__ == "__main__":
    sys.exit(main())
