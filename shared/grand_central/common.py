"""common.py: shared helpers for the engine steps. Every function takes a `con` handed in by a store.py wrapper;
nothing here opens a database. Envelope data only (no body text exists)."""
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import clock  # noqa: E402
import store_graph as sg  # noqa: E402
import gc_settings  # noqa: E402

SETTINGS_THING = ("topic", "engine window")
SETTINGS_REF = "plan:STEP3"
DEFAULT_SETTINGS = (("calendar_back_days", "14"), ("calendar_ahead_days", "62"), ("calendar_focus_days", "14"),
                    ("tasks_done_days", "14"), ("email_recent_days", "30"), ("email_inbox_any_age", "yes"))
IMP = {"high": 1.0, "normal": 0.6, "low": 0.15}


# ---- time -------------------------------------------------------------------------------------------
def now():
    return clock.now().astimezone(dt.timezone.utc)


def parse_dt(s):
    """ISO date or datetime (Z or offset) -> aware datetime (UTC); a bare date is midnight UTC. None if unparseable."""
    if not s:
        return None
    s = str(s).strip()
    try:
        if len(s) == 10:
            return dt.datetime.combine(dt.date.fromisoformat(s), dt.time.min, tzinfo=dt.timezone.utc)
        t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return (t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)).astimezone(dt.timezone.utc)
    except ValueError:
        return None


def ms_dt(ms):
    return dt.datetime.fromtimestamp(int(ms) / 1000, dt.timezone.utc) if ms is not None else None


def day(s):
    return str(s)[:10] if s else None


def chunks(seq, n=400):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def jlist(s):
    try:
        v = json.loads(s) if s else []
    except (TypeError, ValueError):
        return []
    return [str(x).strip().lower() for x in v if x] if isinstance(v, list) else []


# ---- the window settings (facts on topic:engine window) -----------------------------------------------
def _settings_rows(con):
    key = sg.thing_key(*SETTINGS_THING)
    return con.execute("SELECT f.value FROM kg_facts f JOIN kg_things t ON t.id=f.thing_id WHERE t.key=? AND "
                       "f.fact_key='setting' AND f.replaced_by IS NULL ORDER BY (f.who='owner'), f.id", (key,)).fetchall()


def settings(con):
    """name -> value. Defaults, overlaid by current setting facts (his word last, then newest)."""
    out = {k: v for k, v in DEFAULT_SETTINGS}
    for (v,) in _settings_rows(con):
        name, _, val = str(v).partition("=")
        if name.strip():
            out[name.strip()] = val.strip()
    typed = {}
    for k, v in out.items():
        try:
            typed[k] = int(v)
        except ValueError:
            typed[k] = v
    return typed


def seed_settings(con):
    """Write a missing setting once (who=code). A setting that already has any current fact is left alone. Returns #written."""
    have = {str(v).partition("=")[0].strip() for (v,) in _settings_rows(con)}
    tid = None
    n = 0
    for name, val in DEFAULT_SETTINGS:
        if name in have:
            continue
        tid = tid or sg.thing(con, SETTINGS_THING[0], SETTINGS_THING[1], created_by="code")
        sg.assert_fact(con, tid, "setting", "%s=%s" % (name, val), "code", "sure", "code", SETTINGS_REF)
        n += 1
    return n


# ---- the window ---------------------------------------------------------------------------------------
def window_ids(con):
    return [int(r[0].split(":", 1)[1]) for r in con.execute(
        "SELECT subject_ref FROM kg_scores WHERE signal='window' ORDER BY id")]


def load_items(con, ids):
    out = {}
    for ch in chunks(ids):
        q = ",".join("?" * len(ch))
        for r in con.execute("SELECT id, source, source_id, kind, title, person_address, occurred_at, due_at, status "
                             "FROM items WHERE id IN (%s)" % q, ch):
            out[r[0]] = dict(zip(("id", "source", "source_id", "kind", "title", "addr", "occurred_at", "due_at", "status"), r))
    return out


def email_info(con, ids):
    """item_id -> envelope facts of its message (from, to, cc, thread, ms, subject, label ids)."""
    out = {}
    for ch in chunks(ids):
        q = ",".join("?" * len(ch))
        for r in con.execute(
                "SELECT ie.item_id, m.id, m.thread_id, lower(m.from_addr), m.from_name, m.to_addrs, m.cc_addrs, "
                "m.internal_date, m.subject, m.label_ids, m.is_sent FROM item_email ie JOIN messages m ON m.id=ie.message_id "
                "WHERE ie.item_id IN (%s)" % q, ch):
            try:
                labels = json.loads(r[9]) if r[9] else []
            except ValueError:
                labels = []
            out[r[0]] = {"message_id": r[1], "thread_id": r[2], "from": r[3] or "", "from_name": r[4] or "",
                         "to": jlist(r[5]), "cc": jlist(r[6]), "ms": r[7], "dt": ms_dt(r[7]), "subject": r[8] or "",
                         "labels": labels if isinstance(labels, list) else [], "is_sent": r[10]}
    return out


def cal_info(con, ids):
    """item_id -> calendar event facts. end_date for an all-day event is the last day (Google stores it exclusive)."""
    out = {}
    for ch in chunks(ids):
        q = ",".join("?" * len(ch))
        for r in con.execute(
                "SELECT ic.item_id, e.id, e.start, e.end, e.all_day, e.status, e.organizer_email, e.attendee_emails, e.summary "
                "FROM item_calendar ic JOIN calendar_events e ON e.id=ic.calendar_event_id WHERE ic.item_id IN (%s)" % q, ch):
            s, e = parse_dt(r[2]), parse_dt(r[3])
            sd, ed = day(r[2]), day(r[3])
            if r[4] and sd and ed and ed > sd:
                ed = (dt.date.fromisoformat(ed) - dt.timedelta(days=1)).isoformat()
            out[r[0]] = {"event_id": r[1], "start": s, "end": e, "start_date": sd, "end_date": ed or sd, "all_day": r[4],
                         "status": (r[5] or "").lower(), "organizer": (r[6] or "").lower(), "attendees": jlist(r[7]),
                         "summary": r[8] or ""}
    return out


def me_set(con):
    return {r[0] for r in con.execute("SELECT address FROM s_me")}


def label_names(con):
    return {r[0]: r[1] for r in con.execute("SELECT id, name FROM labels")}


def sender_sequence(con):
    """message id -> (n-th message from this address, previous message ms from it or None). Whole mailbox."""
    return {r[0]: (r[1], r[2]) for r in con.execute(
        "SELECT id, ROW_NUMBER() OVER w, LAG(internal_date) OVER w FROM messages "
        "WHERE from_addr IS NOT NULL AND from_addr<>'' WINDOW w AS (PARTITION BY lower(from_addr) ORDER BY internal_date, id)")}


# ---- what the memory says about a sender --------------------------------------------------------------
def sender_facts(con, address, today=None):
    """Current facts on the address, its domains and what they link to, in about_sender order, dropping facts whose
    true_from/true_until do not cover today. Each dict has thing_key/thing_name/fact_key/value/who/certainty."""
    today = (today or now().date()).isoformat()
    out = []
    for f in sg.about_sender(con, address)["facts"]:
        if f["true_until"] and str(f["true_until"])[:10] < today:
            continue
        if f["true_from"] and str(f["true_from"])[:10] > today:
            continue
        out.append(f)
    return out


def importance_of(facts):
    """(value, who, fact) from importance/tier facts: his word first, then code/AI; None if nothing says."""
    for pool in ([f for f in facts if f["who"] == "owner"], [f for f in facts if f["who"] != "owner"]):
        for key in ("importance", "tier"):
            for f in pool:
                if f["fact_key"] == key and f["value"] in IMP:
                    return f["value"], f["who"], f
    return None


def domain_of_labels(label_ids, names):
    """The domain (gc.json domains, by label_prefix) from a message's label names, else None (first match by name order)."""
    hits = []
    label_domains = gc_settings.label_domains()
    for lid in label_ids:
        n = str(names.get(lid) or "").lower()
        for pref, dom in label_domains:
            if n.startswith(pref):
                hits.append(dom)
    return sorted(hits)[0] if hits else None


def label_aliases(gmail_name):
    """The short names a Gmail label answers to: full name, its last part, and the last part without '-Inbox'/' Inbox'.
    'Desk-Inbox' -> desk; 'Desk-Inbox/Sub' -> sub; 'Work Inbox' -> work; 'Example' -> example."""
    full = str(gmail_name or "").strip().lower()
    leaf = full.rsplit("/", 1)[-1]
    out = {full, leaf}
    for suf in ("-inbox", " inbox"):
        if leaf.endswith(suf):
            out.add(leaf[: -len(suf)].strip())
    return out


def label_ids_for(con, short_name):
    """Gmail label ids whose aliases include short_name (case-insensitive)."""
    s = str(short_name or "").strip().lower()
    return [lid for lid, nm in label_names(con).items() if s in label_aliases(nm)]
