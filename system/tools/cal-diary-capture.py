#!/usr/bin/env python3
"""Cal diary daily auto-capture — PULL emitter (look-back: what happened on a date).

Writes desks/cal/diary/YYYY/MM/DD.md from sources that ALREADY EXIST — no new emit jobs,
NO LLM (mechanical + ported only):
  - system/journal.md   : entry rows + session blocks for the date, grouped by desk
                          (this is "what got built/debugged/decided", cross-desk incl. ClaudeOps)
                          FORMAT-TOLERANT by contract — the journal writes six shapes and all
                          six are read; see "JOURNAL FORMAT TOLERANCE" below before touching it.
                          Locked by system/tools/test_cal_diary_capture.py — run it after any edit.
  - state/status/*.json : each desk's current-state snapshot (labelled "as of last_run")
  - Google Tasks        : tasks completed on the date (Life Map list), via gws
  - Calendar            : timed events that occurred on the date (personal + Agent Ops), via gws

Composes per-desk sections + a mechanical "## Machine Recap (unverified)" (the committed read
a check-in later reacts to). Part of the calendar-diary system
(desks/cal/projects/calendar-diary/ — see checkin-method.md + brief.md).

SAFETY / CONTRACT:
  - Fail-soft: any gws/source failure → that section marked `source-unavailable`, exit 0
    (so the Pulse circuit breaker never trips on a content/source gap; only a real crash is non-0).
  - Idempotent: regenerates the machine portion; PRESERVES any "## Human Delta — verified"
    section verbatim (never overwrites a human gray-matter stamp).
  - Atomic write (tmp + os.replace).
  - READ-ONLY against Google (lists only). Only write is the local diary .md.

Usage: cal-diary-capture.py [--date YYYY-MM-DD]   (default: today, local)
The headless runner (cal-diary-run.sh) exports the keychain-free gws-cron env before calling this.
"""
import argparse, json, os, re, subprocess, sys, time
from datetime import datetime, timedelta, time as dtime, timezone

GWS = __import__("shutil").which("gws") or "gws"  # PATH first, like cal-light-sweep.py/cal-vault-pull.py —
# was hardcoded Homebrew-only, so it broke Windows AND Intel Macs (Intel Homebrew installs to /usr/local)
# The notes folder, through the one resolver. ⛔ NOT a default and NOT a guess: the tool this came
# from hardcoded one person's Drive path, so on any other machine it wrote its vault into a
# directory that did not exist. `resolve_brain_root()` returns (source, path); NOT-SET is (None,
# None), and a tool with nowhere to write must say so rather than invent somewhere.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "shared"))
import brain_root                                                            # noqa: E402
import cal_config                                                            # noqa: E402
_SRC, DRIVE = brain_root.resolve_brain_root()
if not DRIVE:
    sys.stderr.write(
        "no notes folder is set, so there is nowhere to put what this reads.\n"
        "Set it once:  python3 shared/brain_root.py --set \"<the folder your notes live in>\"\n")
    sys.exit(2)
JOURNAL = os.path.join(DRIVE, "system/journal.md")
STATUS_DIR = os.path.join(DRIVE, "state/status")
DIARY_ROOT = os.path.join(DRIVE, "desks/cal/diary")

# ⛔ THESE WERE HARDCODED, AND THAT IS THE WORST KIND OF HARDCODING. A calendar id baked into a
# tool means an agent reads — or writes — SOMEBODY ELSE'S CALENDAR, and the person running it sees
# nothing wrong: their own events simply never appear. They are the reader's, at
# <notes>/config/cal.md, and there is deliberately no default. See shared/cal_config.py.
_CAL = cal_config.load()
PERSONAL_CAL = _CAL.get("personal_calendar", "")
AGENTOPS_CAL = _CAL.get("agent_calendar", "")
LIFEMAP_TASKLIST = _CAL.get("goals_tasklist", "")
HUMAN_DELTA_MARKER = "## Human Delta"        # everything from here down is preserved across re-runs

# Subjects that write their OWN diary directly, bypassing this journal→one-liner capture. The
# one-line-per-subject funnel is being retired gradually: a subject on this list writes whatever it
# wants into <notes>/desks/{subject}/diary/YYYY/MM/DD.md, and the shared diary just leaves a
# pointer to it. ⛔ SHIPS EMPTY, deliberately — the set names subject folders, and which folders
# exist is the reader's, not this file's. Add your own if you start writing a subject's diary
# directly; an empty set means everything funnels, which is the behaviour that needs no setup.
DESK_OWNS_OWN_DIARY = set()

# ---------------------------------------------------------------------------
# JOURNAL FORMAT TOLERANCE  (fix 2026-08-02 — [CAL-DIARY-FORMAT-DRIFT])
#
# The journal is the PRODUCER and this file is the CONSUMER, and they drifted: the parser
# accepted exactly two shapes while the journal writes six. 125 of 466 entry rows and 196 of
# 288 session blocks were being silently dropped — nothing errored, the diary just came out
# thin, which is why the cal-weekly lookback kept reading an empty week.
#
# FIX THE READER, NOT THE WRITERS: the writers are every skill, cron and session that appends
# to the journal, and re-training them cannot repair the two months already written. The
# journal is append-only history and is never rewritten — the reader adapts to the data.
# Both formats have coexisted since June, so nothing here may assume "the old shape ended on
# date X". Full reasoning: state/handoff-cal-diary-format-drift.md
#
# Shapes accepted (all six are live in the corpus):
#   ENTRY ROWS   | DATE | desk | slug | event        ← original
#                - DATE | desk | slug | event        ← markdown list item (leading dash)
#                **DECISION DATE | desk | slug |** … and **BUILD DATE | desk | slug |** …
#   BLOCKS       --- SESSION CONTEXT | DATE | desk | slug ---   (terminated by a bare ---)
#                ## SESSION CONTEXT — DATE | desk | slug   /  — DATE — free text
#                ## DATE — desk — slug — text  /  ## DATE — text [SLUG]
# ---------------------------------------------------------------------------

DATE_RX = r"\d{4}-\d{2}-\d{2}"
# An entry row: optional indent, optional markdown bullet, optional leading pipe, then the date.
ENTRY_RE = re.compile(rf"^\s*(?:[-*]\s+)?\|?\s*({DATE_RX})\s*\|(.*)$")
# A dated bold decision/build line. The date is required — '**DECISION (the person):**' must NOT match.
BOLD_RE = re.compile(rf"^\*\*(?:DECISION|BUILD)\b[^|]*?({DATE_RX})[^|]*\|(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
LEGACY_BLOCK_RE = re.compile(r"^---\s*SESSION CONTEXT\s*\|")
UNATTRIBUTED = "unattributed"  # blocks that name no desk — captured, never silently dropped

# Desk ids, read from the registry (the keystone every organ reads) with a static fallback so a
# missing/renamed registry degrades to visible 'unattributed', never to a crash.
# ⛔ THE FALLBACK SHIPS EMPTY. In the system this came from it listed that person's seven subjects,
# so a missing registry degraded to *their* names — which on anyone else's machine means every block
# is attributed to a subject that does not exist, silently and wrongly. Empty means an unreadable
# registry degrades to visible 'unattributed', which is the honest answer and the one this file's
# own comment says it wants.
_FALLBACK_DESKS = set()


def _known_desks():
    desks = set()
    try:
        reg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "desk-registry.yaml")
        with open(reg, encoding="utf-8") as f:
            for ln in f:
                m = re.match(r"^\s*-\s*desk_id:\s*(\S+)", ln)
                if m:
                    desks.add(m.group(1).strip().strip('"\''))
    except Exception:
        pass
    return (desks or _FALLBACK_DESKS) | {"root"}  # 'root' is the shell, not a registry desk


KNOWN_DESKS = _known_desks()


def _row_fields(rest):
    """Split the post-date remainder of an entry row into (desk, slug, event) or None.

    Tolerates the slug-less two-field row '| desk | event' the journal also writes."""
    parts = [p.strip() for p in rest.split("|")]
    if len(parts) < 2 or not parts[0]:
        return None
    desk = parts[0]
    if len(parts) >= 3 and parts[2]:
        slug, event = parts[1], parts[2]
    else:
        slug, event = "", parts[1]          # slug-less row: the event sits where the slug would
    return desk, slug, event.lstrip("*").strip()


def _clip(s, n=200):
    return (s[:n] + "…") if len(s) > n else s


def _heading_desk(head):
    """Desk named in a heading ('… | root | slug', '… — root — slug', '| root / slug').

    Segment-EXACT first, on purpose: prose that merely mentions a desk name must not hijack the
    attribution. Only if no segment is a bare desk id do we fall back to the desk- PREFIX of a
    slug segment ('### SESSION CONTEXT — DATE — some-skill-name'), which is how the 155 H3-era
    blocks name their desk. The hyphen boundary is required, so 'calendar-diary' is not 'cal'."""
    segs = [s.strip().lower() for s in re.split(r"[|—/]", head)]
    for t in segs:
        if t in KNOWN_DESKS:
            return t
    for t in segs:
        for d in KNOWN_DESKS:
            if t.startswith(d + "-"):
                return d
    return None


def _heading_gist(head):
    """The descriptive tail of a heading — the last segment that is not the date or a desk."""
    segs = [s.strip() for s in re.split(r"[|—]", head)]
    for seg in reversed(segs):
        if not seg or seg.lower() in KNOWN_DESKS:
            continue
        if re.fullmatch(rf"[\s(]*{DATE_RX}.*", seg) and len(seg) < 40:
            continue  # just the date (plus a '(session 2, cont.)'-style qualifier)
        return seg
    return ""


def _ends_block(ln):
    """True if `ln` starts something new — so a heading block never swallows the rest of the
    file. The '##' form has NO '---' terminator; this is what stands in for one."""
    s = ln.strip()
    return bool(
        s == "---"
        or HEADING_RE.match(ln)
        or LEGACY_BLOCK_RE.match(ln)
        or BOLD_RE.match(ln)
        or ENTRY_RE.match(ln)
    )


def _block_gist(lines, start):
    """Scan a block body for its 'session:' line; return (gist, index_where_the_block_ends).

    Bounded by _ends_block for EVERY block form, legacy included. The legacy form nominally ends
    at a bare '---', but plenty of legacy blocks were written without one, and the original
    unbounded scan then ate every row that followed — 28 of them on 2026-06-07 alone."""
    sess = ""
    j = start
    while j < len(lines):
        raw = lines[j].rstrip("\n")
        s = raw.strip()
        if _ends_block(raw):
            break
        m = re.match(r"^\**\s*session\s*\**\s*:\s*(.*)$", s, re.I)
        if m and not sess:
            sess = m.group(1).strip().lstrip("*").strip()
        j += 1
    return sess, j


def gws_json(args):
    """Run a gws read; return parsed JSON or raise."""
    r = subprocess.run([GWS] + args, capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stderr.strip().splitlines() or ["(no stderr)"])[-1]
        raise RuntimeError(f"gws {args[0]} {args[1]} failed: {tail}")
    return json.loads(r.stdout or "{}")


# ---------- sources (each fail-soft: return (data, status_str)) ----------

def read_journal(date_str):
    """Every entry row + session block the journal writes for date_str, grouped by desk.

    Tolerant by design — see the JOURNAL FORMAT TOLERANCE block above for the six live shapes
    and why the reader (not the writers) is the thing that adapts."""
    by_desk = {}
    try:
        with open(JOURNAL, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return by_desk, "source-unavailable"

    def add(desk, label, text):
        bullet = f"[{label}] {_clip(text)}" if label else _clip(text)
        by_desk.setdefault(desk, []).append(bullet)

    i = 0
    while i < len(lines):
        ln = lines[i].rstrip("\n")

        # --- legacy block: --- SESSION CONTEXT | DATE | desk | slug ---  (bare '---' terminates)
        if LEGACY_BLOCK_RE.match(ln):
            hdr = [p.strip() for p in ln.split("|")]
            if len(hdr) >= 4 and hdr[1] == date_str:
                sess, j = _block_gist(lines, i + 1)
                add(hdr[2], "session", sess or "(see journal)")
                i = j      # j is the terminating line — re-examine it, don't consume it
                continue
            i += 1
            continue

        # --- dated bold line: **DECISION|BUILD DATE | desk | slug |** event
        m = BOLD_RE.match(ln)
        if m:
            if m.group(1) == date_str:
                f = _row_fields(m.group(2))
                if f:
                    add(f[0], f[1], f[2])
            i += 1
            continue

        # --- entry row: '| DATE | …' or '- DATE | …' (optionally indented)
        m = ENTRY_RE.match(ln)
        if m:
            if m.group(1) == date_str:
                f = _row_fields(m.group(2))
                if f:
                    add(f[0], f[1], f[2])
            i += 1
            continue

        # --- heading block: '## SESSION CONTEXT — DATE …' or '## DATE …'
        m = HEADING_RE.match(ln)
        if m:
            head = m.group(2)
            d = re.search(DATE_RX, head)
            if d and d.group(0) == date_str:
                sess, j = _block_gist(lines, i + 1)
                add(_heading_desk(head) or UNATTRIBUTED, "session",
                    sess or _heading_gist(head) or "(see journal)")
                i = j          # j is the terminating line — re-examine it, don't consume it
                continue
            i += 1
            continue

        i += 1
    return by_desk, "ok"


def read_status():
    """Current-state snapshot per desk that emits a status json."""
    out = []
    try:
        names = sorted(os.listdir(STATUS_DIR))
    except Exception:
        return out, "source-unavailable"
    for name in names:
        if not name.endswith(".json"):
            continue
        if name.startswith("_") or name.startswith("location") or ".bak" in name:
            continue
        try:
            with open(os.path.join(STATUS_DIR, name), encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        out.append({
            "desk": d.get("desk", name[:-5]),
            "status": d.get("status", "?"),
            "summary": d.get("summary", ""),
            "work_count": d.get("work_count"),
            "work_noun": d.get("work_noun", ""),
            "last_run": d.get("last_run", ""),
        })
    return out, "ok"


def read_completed_tasks(cmin, cmax):
    try:
        params = {"tasklist": LIFEMAP_TASKLIST, "showCompleted": True,
                  "showHidden": True, "completedMin": cmin, "completedMax": cmax,
                  "maxResults": 100}
        data = gws_json(["tasks", "tasks", "list", "--params", json.dumps(params)])
        items = [t.get("title", "(untitled)").strip()
                 for t in data.get("items", []) if t.get("status") == "completed"]
        return items, "ok"
    except Exception as e:
        sys.stderr.write(f"cal-diary: tasks read failed: {e}\n")
        return [], "source-unavailable"


def read_calendar(time_min, time_max):
    def one(cal_id):
        params = {"calendarId": cal_id, "maxResults": 100, "singleEvents": True,
                  "orderBy": "startTime", "timeMin": time_min, "timeMax": time_max}
        return gws_json(["calendar", "events", "list", "--params", json.dumps(params)]).get("items", [])
    try:
        evs = one(PERSONAL_CAL) + one(AGENTOPS_CAL)
    except Exception as e:
        sys.stderr.write(f"cal-diary: calendar read failed: {e}\n")
        return [], "source-unavailable"
    seen, merged = set(), []
    for e in evs:
        st = e.get("start", {})
        when = st.get("dateTime") or st.get("date") or ""
        key = (e.get("summary", "").strip().lower(), when)
        if key in seen:
            continue
        seen.add(key)
        hhmm = ""
        if "dateTime" in st:
            try:
                hhmm = datetime.fromisoformat(st["dateTime"]).strftime("%H:%M")
            except ValueError:
                hhmm = ""
        merged.append((hhmm, e.get("summary", "(untitled)").strip()))
    merged.sort()
    return merged, "ok"


# ---------- compose ----------

def preserve_human_delta(path):
    """Return the existing '## Human Delta...' block (verbatim) if present, else ''."""
    if not os.path.exists(path):
        return ""
    try:
        with open(path, encoding="utf-8") as f:
            txt = f.read()
    except Exception:
        return ""
    idx = txt.find("\n" + HUMAN_DELTA_MARKER)
    if idx == -1:
        return ""
    return txt[idx + 1:].rstrip() + "\n"


def build(date_str, journal, status, tasks, cal, src):
    day = datetime.strptime(date_str, "%Y-%m-%d")
    weekday = day.strftime("%A")
    desks = sorted(journal.keys())

    fm = {
        "type": "cal-diary-daily", "date": date_str,
        "scope": desks,
        "generated_at": iso_now(), "sources": src,
    }
    out = ["---"]
    out.append(f'type: {fm["type"]}')
    out.append(f'date: {date_str}')
    out.append(f'scope: [{", ".join(desks)}]')
    out.append(f'generated_at: "{fm["generated_at"]}"')
    out.append(f'sources: {json.dumps(src)}')
    out.append("---\n")
    out.append(f"# {weekday} {date_str} — Daily Diary\n")

    # Calendar
    out.append("## Calendar")
    if src["calendar"] != "ok":
        out.append("_source-unavailable (calendar read failed this run)_")
    elif not cal:
        out.append("_no timed events_")
    else:
        for hhmm, title in cal:
            out.append(f"- {hhmm + '  ' if hhmm else ''}{title}")
    out.append("")

    # Tasks completed
    out.append("## Tasks Completed")
    if src["tasks"] != "ok":
        out.append("_source-unavailable (tasks read failed this run)_")
    elif not tasks:
        out.append("_none recorded_")
    else:
        for t in tasks:
            out.append(f"- {t}")
    out.append("")

    # Per-desk activity (from journal)
    if src["journal"] != "ok":
        out.append("## Desk Activity")
        out.append("_source-unavailable (journal read failed this run)_\n")
    elif not desks:
        out.append("## Desk Activity")
        out.append("_no journal activity recorded this day_\n")
    else:
        for desk in desks:
            out.append(f"## {desk}")
            if desk in DESK_OWNS_OWN_DIARY:
                # This desk owns its diary directly — don't one-line it here (see DESK_OWNS_OWN_DIARY).
                out.append(f"- _writes its own diary directly → desks/{desk}/diary/{desk}-{date_str}.txt_")
                out.append("")
                continue
            for b in journal[desk]:
                out.append(f"- {b}")
            out.append("")

    # Desk status snapshot (current-state, labelled)
    out.append("## Desk Status (snapshot, as of each desk's last run)")
    if src["status"] != "ok" or not status:
        out.append("_source-unavailable_" if src["status"] != "ok" else "_no status files_")
    else:
        for s in status:
            wc = ""
            if s["work_count"] is not None:
                wc = f" · {s['work_count']} {s['work_noun']}".rstrip()
            out.append(f"- **{s['desk']}** [{s['status']}]{wc} — {s['summary']} _(as of {s['last_run']})_")
    out.append("")

    # Machine recap (mechanical, unverified)
    n_events = sum(len(v) for v in journal.values())
    busiest = max(journal.items(), key=lambda kv: len(kv[1]))[0] if journal else None
    out.append("## Machine Recap (unverified)")
    out.append(f"- {n_events} journal event(s) across {len(desks)} desk(s) · "
               f"{len(tasks)} task(s) completed · {len(cal)} calendar event(s).")
    if busiest:
        out.append(f"- Busiest desk: **{busiest}** ({len(journal[busiest])} events).")
    out.append("- ⚠️ Mechanical read, **unverified — needs HITL**: machine-pulled from "
               "journal/tasks/calendar/status; no human gray-matter absorbed yet. "
               "A check-in confirms/corrects this and adds the Human Delta below.")
    out.append("")

    body = "\n".join(out).rstrip() + "\n"
    return body


def iso_now():
    lt = time.localtime()
    off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (default: today, local)")
    args = ap.parse_args()

    if args.date:
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            sys.stderr.write("cal-diary: --date must be YYYY-MM-DD\n")
            return 2
        date_str = args.date
    else:
        date_str = time.strftime("%Y-%m-%d", time.localtime())

    local_tz = datetime.now().astimezone().tzinfo
    day = datetime.strptime(date_str, "%Y-%m-%d").date()
    start_local = datetime.combine(day, dtime.min, tzinfo=local_tz)
    end_local = start_local + timedelta(days=1)
    time_min, time_max = start_local.isoformat(), end_local.isoformat()
    cmin = start_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cmax = end_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    journal, s_j = read_journal(date_str)
    status, s_s = read_status()
    tasks, s_t = read_completed_tasks(cmin, cmax)
    cal, s_c = read_calendar(time_min, time_max)
    src = {"journal": s_j, "status": s_s, "tasks": s_t, "calendar": s_c}

    body = build(date_str, journal, status, tasks, cal, src)
    body = body.rstrip() + "\n\n" + preserve_human_delta(  # re-attach preserved human delta
        os.path.join(DIARY_ROOT, day.strftime("%Y"), day.strftime("%m"), day.strftime("%d") + ".md"))
    body = body.rstrip() + "\n"

    out_dir = os.path.join(DIARY_ROOT, day.strftime("%Y"), day.strftime("%m"))
    out_path = os.path.join(out_dir, day.strftime("%d") + ".md")
    try:
        os.makedirs(out_dir, exist_ok=True)
        tmp = out_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(body)
        os.replace(tmp, out_path)
    except Exception as e:
        sys.stderr.write(f"cal-diary: FATAL could not write {out_path}: {e}\n")
        return 1

    bad = [k for k, v in src.items() if v != "ok"]
    print(f"[cal-diary] wrote {out_path} — "
          f"{sum(len(v) for v in journal.values())} journal / {len(tasks)} tasks / "
          f"{len(cal)} cal / {len(status)} status"
          + (f" · ⚠ source-unavailable: {', '.join(bad)}" if bad else ""))
    return 0  # always 0 on a successful write (content/source gaps are findings, not failures)


if __name__ == "__main__":
    sys.exit(main())
