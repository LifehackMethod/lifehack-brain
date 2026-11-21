#!/usr/bin/env python3
"""audit_run.py - PART 1 of the audit of one validation draft (code only, no AI), plus the plain-text inputs a read-only
reader needs.

  python3 audit_run.py --run DIR --day D --draft PATH --out AUDITDIR [--desk DESK] [--expected expected.json]

DIR is a validation-run scratch folder: rig.db, front-room/, drop/facts, notes/desks/..., run.out. The COPIES are read ONLY
(the database is opened read-only through store._read; nothing under DIR or anywhere else is written except AUDITDIR).
No model call, no network, no live path: every location comes from DIR.

PART 1, NOTHING DROPPED: every input the morning read had for day D is listed, and for each one WHERE it appears in the draft
(section heading plus line number) or its CODE-STATED reason for absence (triage junk, routed to a desk, excluded label, the
list cap, out of the 7-day window ...). An input with NEITHER is a DEFECT. -> AUDITDIR/part1-nothing-dropped.md ("DEFECTS: n").

READER INPUTS (AUDITDIR/inputs/): calendar.txt, tasks.txt, handed.txt, questions.txt, answers.txt, diary-lines.txt.
Output lines carry envelope facts only (sender, subject, date), cut short; no email body text is ever written.
Python 3.9 compatible."""
import argparse
import datetime
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

CAL_DAYS = 7              # the reader's calendar window (the read itself looks 14 days ahead)
DIARY_DAYS = 30


# ================================================================ small helpers

def _read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _jsonl(path):
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    try:
                        out.append(json.loads(ln))
                    except ValueError:
                        continue
    except OSError:
        pass
    return out


def _one_line(s, n=70):
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[:n - 3] + "..."


def _cell(s):
    return _one_line(s, 90).replace("|", "/")


def _addr(sender):
    m = re.search(r"<([^>]+)>", sender or "")
    a = (m.group(1) if m else (sender or "")).strip().lower()
    return a if "@" in a else ""


def _subject_key(subject):
    s = re.sub(r"^\s*((re|fwd?)\s*:\s*)+", "", subject or "", flags=re.I).strip()
    return s[:50].lower()


# ================================================================ the draft: lines and sections

class Draft(object):
    def __init__(self, text):
        self.lines = text.split("\n")
        self.section = []           # section heading in force at each line
        cur = "(top)"
        for ln in self.lines:
            if ln.startswith("## "):
                cur = ln.strip()
            self.section.append(cur)
        self.low = [ln.lower() for ln in self.lines]

    def find(self, needles, section=None, limit=3):
        """-> [(line number, section heading)] of the lines holding ANY needle (case-folded); needles shorter than 4 characters
        are ignored (too weak to mean anything)."""
        needles = [n.lower() for n in needles if n and len(n.strip()) >= 4]
        hits = []
        for i, ln in enumerate(self.low):
            if section and section.lower() not in self.section[i].lower():
                continue
            if any(n in ln for n in needles):
                hits.append((i + 1, self.section[i]))
                if len(hits) >= limit:
                    break
        return hits


def locate(draft, needles, section=None):
    """where an input appears in the draft: [(line, heading)] (empty = nowhere). A seam the test replaces with a broken copy."""
    return draft.find(needles, section=section)


def _where(hits):
    return "; ".join("%s, line %d" % (h, n) for n, h in hits[:3])


# ================================================================ the copy's inputs

def catalogue_rows(run):
    rows = {}
    for r in _jsonl(os.path.join(run, "front-room", "catalogue", "catalogue.jsonl")):
        if isinstance(r, dict) and r.get("message_id"):
            rows[r["message_id"]] = r
    return rows


def marks_for_day(run, day):
    return [m for m in _jsonl(os.path.join(run, "front-room", "catalogue", "used-in-draft.jsonl")) if m.get("day") == day]


def facts_of(run):
    try:
        with open(os.path.join(run, "drop", "facts", "_reader_pass.json"), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


class DB(object):
    """the copied rig.db, read-only (through store._read)"""

    def __init__(self, run):
        self.path = os.path.join(run, "rig.db")

    def __enter__(self):
        import store
        store.set_path(self.path)
        self.cm = store._read()
        return self.cm.__enter__()

    def __exit__(self, *a):
        return self.cm.__exit__(*a)


def has_db(run):
    return os.path.isfile(os.path.join(run, "rig.db"))


def calendar_rows(con, day, days=CAL_DAYS):
    d0 = datetime.date.fromisoformat(day)
    lo, hi = d0.isoformat(), (d0 + datetime.timedelta(days=days)).isoformat()
    rows = con.execute("SELECT summary, start, end, location, id FROM calendar_events WHERE substr(start,1,10) BETWEEN ? AND ? "
                       "AND lower(COALESCE(status,'')) != 'cancelled'", (lo, hi)).fetchall()
    out = [{"title": r[0], "start": r[1], "end": r[2], "location": r[3], "id": r[4]} for r in rows]
    out.sort(key=lambda c: str(c.get("start")))
    return out


def task_rows(con):
    """the same rows hand_run builds"""
    out = []
    for t in con.execute("SELECT title, status, due, updated, id FROM tasks"):
        out.append({"title": t[0], "status": "open" if str(t[1]).lower() != "completed" else "completed",
                    "due": (t[2] or "")[:10] or None, "updated": t[3], "_tid": t[4]})
    return out


def desk_of(draft_text):
    """the desk named in the draft's own title line; else the engine's default desk (gc.json default_desk)"""
    m = re.match(r"# Morning write-up \d{4}-\d{2}-\d{2} - (\S+) desk", draft_text)
    if m:
        return m.group(1)
    import gc_settings
    return gc_settings.default_desk()


def records_dir(run, desk):
    return os.path.join(run, "notes", "desks", desk, "records", "context")


def baseline_files(run, desk, day):
    """-> (confirmed path or None, unconfirmed path or None): the newest validated picture before the day, and the latest
    staged morning draft before the day that is newer than it (or, with no validated one, simply the latest)."""
    d = records_dir(run, desk)
    try:
        names = sorted(os.listdir(d))
    except OSError:
        return None, None
    val = [n for n in names if re.fullmatch(r"\d{4}-\d{2}-\d{2}-%s-validated\.md" % re.escape(desk), n) and n[:10] < day]
    dr = [n for n in names if re.fullmatch(r"\d{4}-\d{2}-\d{2}-%s(-topup\d+)?\.md" % re.escape(desk), n) and n[:10] < day]
    confirmed = os.path.join(d, val[-1]) if val else None
    if confirmed:
        mt = os.path.getmtime(confirmed)
        dr = [n for n in dr if os.path.getmtime(os.path.join(d, n)) > mt]
    dr.sort(key=lambda n: os.path.getmtime(os.path.join(d, n)))
    return confirmed, (os.path.join(d, dr[-1]) if dr else None)


# ================================================================ Part 1

class Item(object):
    def __init__(self, category, label, hits=None, reason=None):
        self.category, self.label, self.hits, self.reason = category, label, hits or [], reason

    @property
    def defect(self):
        return not self.hits and not self.reason


def classify_mark(row, expected):
    """-> ("handed" | "sorted out", reason). The run's own rules: triage junk (morning.triage_class), and the expected-pattern
    routes (only when an expected file is given)."""
    import morning
    cls = morning.triage_class(row)
    if expected:
        route, pat = morning.classify_expected(expected, row.get("from"), row.get("subject"))
        if route in ("routine", "desk") and cls != "junk":
            return "sorted out", "%s notice: logged by code (%s)" % ("desk-routed" if route == "desk" else "routine", (pat or {}).get("name", "?"))
    if cls == "junk":
        return "sorted out", "triage junk/notification (triage_class)"
    if row.get("verdict") != "safe":
        return "sorted out", "verdict %s: never handed" % row.get("verdict")
    return "handed", None


def audit(run, day, draft_text, desk=None, expected=None):
    """-> (items, context). Every input the morning read had for `day`, with where it appears or why it is absent."""
    import morning
    desk = desk or desk_of(draft_text)
    draft = Draft(draft_text)
    items = []
    cat = catalogue_rows(run)
    marks = marks_for_day(run, day)
    ctx = {"desk": desk, "marks": len(marks)}

    # ---- the emails the read had for this day (the used-in-draft marks for the day, joined to the catalogue)
    classes = {}
    for m in marks:
        r = cat.get(m.get("message_id"))
        if r is None:
            items.append(Item("email", "%s (no catalogue row)" % m.get("message_id")))
            continue
        cls, why = classify_mark(r, expected)
        classes[r["message_id"]] = cls
        needles = ["mail:" + str(r.get("thread_id") or ""), str(r["message_id"])[:12], _addr(r.get("from")), _subject_key(r.get("subject"))]
        hits = locate(draft, needles)
        nm = (r.get("triage") or {}).get("needs_me") if isinstance(r.get("triage"), dict) else "none"
        label = "%s | %s | %s | %s | needs_me %s" % (str(r["message_id"])[:12], r.get("date"), _addr(r.get("from")) or _one_line(r.get("from"), 30),
                                                    _one_line(r.get("subject"), 50), nm)
        if cls == "handed":
            items.append(Item("email (handed)", label, hits))
        else:
            items.append(Item("email (not handed)", label, hits, reason=why))
    ctx["classes"] = classes

    # ---- calendar and tasks from the copied database (the same queries morning.py uses)
    events, tasks = [], []
    if has_db(run):
        with DB(run) as con:
            events = calendar_rows(con, day)
            tasks = task_rows(con)
    opens = [t for t in tasks if t["status"] != "completed"]
    kept = morning.select_tasks(tasks, day)[0] if tasks else []
    kept_ids = set(t["_tid"] for t in kept)
    for c in events:
        needles = [morning._safe_line(c["title"], 100)[:60], str(c["title"] or "")[:60]]
        hits = locate(draft, needles)
        items.append(Item("calendar (7 days)", "%s | %s" % (str(c["start"])[:16], _one_line(c["title"], 60)), hits))
    for t in opens:
        hits = locate(draft, [morning._safe_line(t["title"], 100)[:60], str(t["title"] or "")[:60]])
        reason = None
        if not hits and t["_tid"] not in kept_ids:
            reason = "left out by the task cap (select_tasks keeps %d of %d open)" % (len(kept), len(opens))
        items.append(Item("task (open)", "%s | %s" % (t["due"] or "no due date", _one_line(t["title"], 60)), hits, reason))

    # ---- every triage needs-him flag (among the emails of the day), by code
    for m in marks:
        r = cat.get(m.get("message_id"))
        t = r.get("triage") if r and isinstance(r.get("triage"), dict) else {}
        if t.get("needs_me") == "yes":
            hits = locate(draft, [str(r["message_id"])[:12]], section="Needs him")
            reason = None
            if not hits and classes.get(r["message_id"]) not in ("handed", None):
                reason = "not listed: %s" % classify_mark(r, expected)[1]
            items.append(Item("needs-him flag", "%s | %s | %s" % (str(r["message_id"])[:12], _addr(r.get("from")), _one_line(r.get("subject"), 50)), hits, reason))

    # ---- held and quarantined, through the same functions as the run
    facts = facts_of(run)
    held_items = []
    if facts:
        if has_db(run):
            with DB(run) as con:
                held_items, _dropped = morning.held_items_from_facts(facts, con, ())
        else:
            held_items, _dropped = morning.held_items_from_facts(facts, None, ())
    more = 0
    m_more = re.search(r"\.\.\.and (\d+) more", draft_text)
    if m_more:
        more = int(m_more.group(1))
    has_still = re.search(r"Still held or quarantined from earlier: \d+", draft_text) is not None
    has_excl = re.search(r"In labels you chose not to open: \d+", draft_text) is not None
    unlisted_budget = more
    for it in held_items:
        mid = it["message_id"]
        if it["sender"].startswith("unknown sender"):
            needles = [mid[:12]]
        else:
            needles = [_addr(it["sender"]), _subject_key(it["subject"]), mid[:12]]
        hits = locate(draft, needles)
        reason = None
        if not hits:
            if it.get("reason_code") == "excluded_label" and has_excl:
                reason = "excluded label: counted, never listed ('In labels you chose not to open')"
            elif has_still and "seen in an earlier draft" in it["reason"]:
                reason = "held from an earlier draft: counted ('Still held or quarantined from earlier')"
            elif unlisted_budget > 0:
                unlisted_budget -= 1
                reason = "past the list cap (the draft says '...and %d more')" % more
        items.append(Item("held/quarantined", "%s | %s | %s | %s" % (mid[:12], _one_line(it["sender"], 40), _one_line(it["subject"], 40), it.get("reason_code")),
                          hits, reason))

    # ---- the unclassified list
    import snapshot_layout
    rows_u = []
    for m in marks:
        r = cat.get(m.get("message_id"))
        if r:
            rows_u.append(dict(r))
    for u in snapshot_layout.unclassified_rows(rows_u):
        hits = locate(draft, [_subject_key(u["subject"]), _addr(u["sender"])], section="Unclassified emails")
        items.append(Item("unclassified", "%s | %s | %s" % (u["message_id"][:12], _addr(u["sender"]), _one_line(u["subject"], 50)), hits))

    # ---- the Life Map and the baselines
    lm = os.path.join(run, "notes", "desks", desk, "life-map.md")
    if os.path.isfile(lm):
        hits = locate(draft, ["Life Map (used)", "Life Map (not used)"])
        items.append(Item("life map", os.path.relpath(lm, run), hits))
    else:
        items.append(Item("life map", "(no life-map.md in the copy)", reason="no Life Map file exists in the copy"))
    confirmed, unconfirmed = baseline_files(run, desk, day)
    for kind, p in (("baseline (confirmed)", confirmed), ("baseline (unconfirmed)", unconfirmed)):
        if p is None:
            items.append(Item(kind, "(none)", reason="no such file exists before %s" % day))
            continue
        name = os.path.basename(p)
        hits = locate(draft, ["Starting point:"]) if re.search(r"Starting point: [^\n]*%s" % re.escape(name[:10]), draft_text) else []
        items.append(Item(kind, name, hits))
    return items, ctx


# ================================================================ the report

def write_part1(items, ctx, day, draft_path, out_dir):
    defects = [it for it in items if it.defect]
    lines = ["# Part 1: nothing dropped (day %s, draft %s)" % (day, os.path.basename(draft_path)), "",
             "Every input the morning read had for the day, and where it appears in the draft or the code-stated reason it is absent.",
             "Envelope facts only (cut short); no email body text.", "",
             "| # | input | what | where in the draft | reason for absence (code-stated) | status |",
             "|---|---|---|---|---|---|"]
    for i, it in enumerate(items, 1):
        status = "DEFECT" if it.defect else ("found" if it.hits else "reasoned")
        lines.append("| %d | %s | %s | %s | %s | %s |" % (i, it.category, _cell(it.label), _cell(_where(it.hits)) or "-", _cell(it.reason) or "-", status))
    lines += ["", "## Counts"]
    cats = {}
    for it in items:
        c = cats.setdefault(it.category, [0, 0, 0, 0])
        c[0] += 1
        c[1] += 1 if it.hits else 0
        c[2] += 1 if (not it.hits and it.reason) else 0
        c[3] += 1 if it.defect else 0
    for k, (n, f, r, d) in sorted(cats.items()):
        lines.append("- %s: %d inputs, %d found in the draft, %d with a stated reason, %d defect(s)" % (k, n, f, r, d))
    lines += ["", "DEFECTS: %d" % len(defects)]
    for it in defects:
        lines.append("- %s: %s" % (it.category, _cell(it.label)))
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "part1-nothing-dropped.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path, len(defects)


# ================================================================ the reader inputs

def _w(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def write_inputs(run, day, out_dir, desk, expected, setup_note=None):
    inp = os.path.join(out_dir, "inputs")
    cat = catalogue_rows(run)
    marks = marks_for_day(run, day)
    events, tasks = [], []
    if has_db(run):
        with DB(run) as con:
            events = calendar_rows(con, day)
            tasks = task_rows(con)
    _w(os.path.join(inp, "calendar.txt"), ["# his calendar, next %d days from %s (title | start | end | location)" % (CAL_DAYS, day)] +
       ["%s | %s | %s | %s" % (_one_line(c["title"], 120), c["start"], c["end"], _one_line(c["location"], 80)) for c in events])
    opens = sorted((t for t in tasks if t["status"] != "completed"), key=lambda t: (t["due"] or "9999", str(t["title"])))
    _w(os.path.join(inp, "tasks.txt"), ["# his open tasks (title | due)"] + ["%s | %s" % (_one_line(t["title"], 140), t["due"] or "no due date") for t in opens])
    tdir = os.path.join(run, "front-room", "transcripts")
    handed, other = [], []
    for m in marks:
        r = cat.get(m.get("message_id"))
        if not r:
            continue
        cls, why = classify_mark(r, expected)
        t = r.get("triage") if isinstance(r.get("triage"), dict) else {}
        path = os.path.join(tdir, "%s.txt" % r.get("thread_id"))
        line = "%s | thread %s | %s | %s | %s | triage needs_me=%s area=%s | %s%s" % (
            r["message_id"], r.get("thread_id"), r.get("date"), _addr(r.get("from")) or _one_line(r.get("from"), 40), _one_line(r.get("subject"), 80),
            t.get("needs_me"), t.get("area"), path, "" if os.path.isfile(path) else "  (MISSING)")
        (handed if cls == "handed" else other).append(line + ("" if cls == "handed" else "  [sorted out: %s]" % why))
    _w(os.path.join(inp, "handed.txt"), ["# the emails handed to the model on %s (id | thread | date | sender | subject | triage | transcript file)" % day] + handed +
       ["", "# marked for the day but NOT handed"] + other)
    _w(os.path.join(inp, "questions.txt"), question_lines(run, day, desk, setup_note))
    ans = []
    if has_db(run):
        with DB(run) as con:
            for r in con.execute("SELECT said_on, COALESCE(subject_name, question), words FROM kg_answers ORDER BY said_on, id"):
                ans.append("%s | %s | %s" % (r[0], _one_line(r[1], 100), " ".join(str(r[2] or "").split())))
    _w(os.path.join(inp, "answers.txt"), ["# his recorded answers (date | subject | his words)"] + ans)
    _w(os.path.join(inp, "diary-lines.txt"), ["# his diary lines for the %d days before %s (file:line: text)" % (DIARY_DAYS, day)] + diary_lines(run, day))
    return [os.path.join(inp, n + ".txt") for n in ("calendar", "tasks", "handed", "questions", "answers", "diary-lines")]


def diary_lines(run, day):
    d1 = datetime.date.fromisoformat(day)
    d0 = d1 - datetime.timedelta(days=DIARY_DAYS)
    out = []
    base = os.path.join(run, "notes", "desks")
    for dp, _dn, fs in sorted(os.walk(base)):
        parts = os.path.relpath(dp, base).split(os.sep)
        if len(parts) != 4 or parts[1] != "diary":
            continue
        for f in sorted(fs):
            m = re.fullmatch(r"(\d{2})\.md", f)
            if not m:
                continue
            try:
                d = datetime.date(int(parts[2]), int(parts[3]), int(m.group(1)))
            except ValueError:
                continue
            if not (d0 <= d < d1):
                continue
            rel = os.path.relpath(os.path.join(dp, f), run)
            for n, ln in enumerate(_read(os.path.join(dp, f)).split("\n"), 1):
                if ln.strip():
                    out.append("%s:%d: %s" % (rel, n, ln.rstrip()))
    return out


def question_lines(run, day, desk, setup_note=None):
    """The questions handed to the model, regenerated on the copy exactly as hand_run builds them (delta.run over the
    copied database, then rank_questions). The window starts at the newest staged morning record BEFORE the day and ends at the
    day's own record time. The calendar/task snapshot the run compared against was overwritten when it finished, so calendar and
    task questions cannot be regenerated; the run's own count line (run.out) is quoted beside the regenerated count."""
    import morning
    head = ["# the questions handed to the model, regenerated on the copy with morning.py's own functions"]
    said = None
    try:
        for ln in _read(os.path.join(run, "run.out")).splitlines():
            m = re.search(r"questions handed to the model: (\d+)", ln)
            if m:
                said = int(m.group(1))
    except OSError:
        pass
    rec = records_dir(run, desk)
    prior, today_t = [], []
    try:
        for n in os.listdir(rec):
            m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})-%s(-topup\d+)?\.md" % re.escape(desk), n)
            if m:
                (prior if m.group(1) < day else today_t).append(os.path.getmtime(os.path.join(rec, n)))
    except OSError:
        pass
    now = min(today_t) if today_t else datetime.datetime.now().timestamp()
    since = max(prior) if prior else now - 2 * 86400
    qs = []
    if has_db(run):
        try:
            import delta as delta_mod
            with DB(run) as con:
                d = delta_mod.run(con, int(since * 1000), int(now * 1000), prev_snapshot=None, day=day)
                try:
                    import scorecard as sc
                    mb, cfg = sc.Mailbox.load(con), sc.Config.load()
                    stand = lambda addr: sc.standing(mb, addr, cfg, int(now * 1000))["standing"]   # noqa: E731
                except Exception:
                    stand = lambda addr: 0.0   # noqa: E731
                qs, _n = morning.rank_questions(list(d["questions"]), stand)
        except Exception as e:
            head.append("# NOT REGENERATED: %s" % type(e).__name__)
    head.append("# the run said: %s questions handed; regenerated now: %d%s" % (
        said if said is not None else "(no count in run.out)", len(qs),
        "" if said is None or said == len(qs) else "  <-- DIFFERENT (see the note at the end)"))
    if setup_note:
        head.append("# " + setup_note)
    body = ["%d. %s" % (i, " ".join(q.split())) for i, q in enumerate(qs, 1)]
    tail = []
    if said is not None and said != len(qs):
        tail = ["", "# NOTE: the count differs from the run's. The scoring settings (setup folder) and the earlier calendar/task snapshot the run used may not be",
                "# the ones available here; treat this list as the closest regeneration, not the exact text."]
    return head + body + tail


# ================================================================ command line

def main(argv=None):
    ap = argparse.ArgumentParser(description="audit_run.py: part 1 of the audit of one validation draft")
    ap.add_argument("--run", required=True)
    ap.add_argument("--day", required=True)
    ap.add_argument("--draft", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--desk", default=None)
    ap.add_argument("--expected", default=None, help="expected-patterns file (to name routine / desk-routed mail); default none")
    a = ap.parse_args(argv)
    run = os.path.realpath(a.run)
    if not os.path.isdir(run):
        print("audit_run: --run is not a folder: %s" % run)
        return 2
    # every location the engine code looks up points INTO the copy (never a live path); the setup folder is only a read-only
    # source of scoring settings, from the environment if given, else the tests' own fixture setup
    os.environ["AGE_FRONT_ROOM"] = os.path.join(run, "front-room")
    os.environ["GC_DATA_ROOT"] = os.path.join(run, "gc-data")
    os.environ["GC_STATE_ROOT"] = os.path.join(run, "state")
    os.environ["AGE_NOTES_ROOT"] = os.path.join(run, "notes")
    setup_note = None
    if not os.environ.get("GC_SETUP_DIR"):
        os.environ["GC_SETUP_DIR"] = os.path.join(HERE, "fixtures", "setup")
        setup_note = "scoring settings: the tests' fixture setup (GC_SETUP_DIR was not given)"
    draft_text = _read(a.draft)
    desk = a.desk or desk_of(draft_text)
    expected = None
    if a.expected:
        import morning
        expected = morning.load_expected(a.expected)
    items, ctx = audit(run, a.day, draft_text, desk=desk, expected=expected)
    path, n = write_part1(items, ctx, a.day, a.draft, a.out)
    written = write_inputs(run, a.day, a.out, desk, expected, setup_note)
    print("audit_run: part 1 written: %s" % path)
    print("audit_run: %d inputs listed, DEFECTS: %d" % (len(items), n))
    print("audit_run: reader inputs: %s" % ", ".join(os.path.basename(w) for w in written))
    return 0


if __name__ == "__main__":
    sys.exit(main())
