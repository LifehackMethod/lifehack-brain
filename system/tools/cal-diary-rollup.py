#!/usr/bin/env python3
"""Cal diary PERIODIC tee-up — weekly / monthly / quarterly / yearly roll-up (P2).

Runs AHEAD of a check-in (cron, at the period boundary) and pre-computes the LOOK-BACK so the
human check-in is a short gray-matter session, not a recount. Mechanical, NO LLM:
  - aggregates the period's daily entries (pointers) + journal activity (by desk) + completed Tasks
  - pulls the period's WIN goal from the Life Map as the PLAN side (weekly subtasks / monthly+yearly notes)
  - writes a period REVIEW DRAFT (machine recap, unverified) — deltas-first scaffold
It does NOT write canon.md: graduation into a level's canon is HUMAN-GATED (reasoned-or-repeated),
so automation only drafts the review; the check-in (P3) stamps the Human Delta + promotes facts.

Review-draft paths (the diary tree — cadence + period are READABLE FROM THE NAME):
  weekly    → desks/cal/diary/YYYY/MM/review-week-YYYY-Www.md
  monthly   → desks/cal/diary/YYYY/MM/review-month-YYYY-MM.md
  quarterly → desks/cal/diary/YYYY/review-quarter-YYYY-Q{N}.md
  yearly    → desks/cal/diary/YYYY/review-year-YYYY.md

SAFETY: fail-soft (source failure → section marked source-unavailable, exit 0); atomic write;
PRESERVES any "## Human Delta — verified" section; READ-ONLY against Google. The "ready" buzz is
fired by the runner (cal-diary-run.sh), not here.

Usage: cal-diary-rollup.py --cadence weekly|monthly|quarterly|yearly [--date YYYY-MM-DD]
The period is the {week|month|quarter|year} CONTAINING --date (default today). The cron runner passes
--date = the just-ended day (e.g. yesterday) so a 1st-of-month run wraps the PRIOR month.
"""
import argparse, calendar as calmod, json, os, re, subprocess, sys, time
from datetime import datetime, timedelta, time as dtime, timezone, date as datecls

GWS = __import__("shutil").which("gws") or "gws"  # PATH first, like the rest of the cal tools —
# a hardcoded Homebrew path breaks Windows AND Intel Macs (Intel Homebrew installs to /usr/local).
# The notes folder, through the one resolver. ⛔ NOT a default and NOT a guess: the tool this came
# from hardcoded one person's Drive path, so on any other machine it wrote its diary into a
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
DIARY_ROOT = os.path.join(DRIVE, "desks/cal/diary")
PROJECT_REGISTRY = os.path.join(DRIVE, "system/project-registry.md")  # the watchlist (active/paused slugs)

# ⛔ THESE WERE HARDCODED, AND THAT IS THE WORST KIND OF HARDCODING. A calendar or task-list id
# baked into a tool means an agent reads — or writes — SOMEBODY ELSE'S CALENDAR/TASKS, and the
# person running it sees nothing wrong: their own events simply never appear. They are the
# reader's, at <notes>/config/cal.md, and there is deliberately no default. See shared/cal_config.py.
_CAL = cal_config.load()
PERSONAL_CAL = _CAL.get("personal_calendar", "")
AGENTOPS_CAL = _CAL.get("agent_calendar", "")
LIFEMAP_TASKLIST = _CAL.get("goals_tasklist", "")

# Human-resolved ambiguous aliases. The project registry's `dissolved →` / `superseded →` / `split`
# notes are too ambiguous to auto-apply, so they get surfaced to a human and decided by hand;
# CONFIRMED_ALIASES folds a resolved rename/merge, REVIEWED_NO_ALIAS marks one reviewed and kept
# separate on purpose. ⛔ SHIPS EMPTY, deliberately — the source repo's contents are this
# person's own project history and mean nothing on anyone else's registry; an empty dict/set is
# the honest starting point (nothing folds, nothing is pre-excluded) until you resolve your own.
CONFIRMED_ALIASES = {}
REVIEWED_NO_ALIAS = set()
HUMAN_DELTA_MARKER = "## Human Delta"
WIN_TITLE = {"weekly": "Weekly Win", "monthly": "Monthly Win", "yearly": "Yearly Win"}  # quarterly: none


def gws_json(args):
    r = subprocess.run([GWS] + args, capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stderr.strip().splitlines() or ["(no stderr)"])[-1]
        raise RuntimeError(f"gws {args[0]} {args[1]} failed: {tail}")
    return json.loads(r.stdout or "{}")


def iso_now():
    lt = time.localtime(); off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off


# ---------- period math ----------

def period_range(cadence, anchor):
    """Return (label, start_date, end_date, out_path) for the period containing anchor."""
    y = anchor.year
    if cadence == "weekly":
        monday = anchor - timedelta(days=anchor.weekday())
        sunday = monday + timedelta(days=6)
        iso_y, iso_w, _ = anchor.isocalendar()
        label = f"{iso_y}-W{iso_w:02d}"
        out = os.path.join(DIARY_ROOT, f"{monday:%Y}", f"{monday:%m}", f"review-week-{label}.md")
        return label, monday, sunday, out
    if cadence == "monthly":
        last = calmod.monthrange(y, anchor.month)[1]
        start, end = datecls(y, anchor.month, 1), datecls(y, anchor.month, last)
        label = f"{y}-{anchor.month:02d}"
        out = os.path.join(DIARY_ROOT, f"{y:04d}", f"{anchor.month:02d}", f"review-month-{label}.md")
        return label, start, end, out
    if cadence == "quarterly":
        q = (anchor.month - 1) // 3 + 1
        m0 = (q - 1) * 3 + 1
        last = calmod.monthrange(y, m0 + 2)[1]
        start, end = datecls(y, m0, 1), datecls(y, m0 + 2, last)
        label = f"{y}-Q{q}"
        out = os.path.join(DIARY_ROOT, f"{y:04d}", f"review-quarter-{label}.md")
        return label, start, end, out
    if cadence == "yearly":
        start, end = datecls(y, 1, 1), datecls(y, 12, 31)
        label = f"{y}"
        out = os.path.join(DIARY_ROOT, f"{y:04d}", f"review-year-{label}.md")
        return label, start, end, out
    raise ValueError(f"bad cadence {cadence}")


# ---------- sources ----------

def daily_pointers(start, end):
    """List DD.md entries present in [start,end] (the look-back detail)."""
    found = []
    d = start
    while d <= end:
        p = os.path.join(DIARY_ROOT, f"{d:%Y}", f"{d:%m}", f"{d:%d}.md")
        if os.path.exists(p):
            found.append((d.isoformat(), os.path.relpath(p, DRIVE)))
        d += timedelta(days=1)
    return found


def day_coverage(start, end):
    """For each day d in [start, end] inclusive, resolve the best source tier.
    - 'verified': file exists AND contains '## Human Delta'
    - 'machine':  file exists, no Human Delta
    - 'raw':      no daily file at all
    Returns (days_list, counts) where days_list = [{date, tier, human_delta}]
    and counts = {verified, machine, raw, total}."""
    days = []
    counts = {"verified": 0, "machine": 0, "raw": 0, "total": 0}
    d = start
    while d <= end:
        p = os.path.join(DIARY_ROOT, f"{d:%Y}", f"{d:%m}", f"{d:%d}.md")
        entry = {"date": d.isoformat(), "tier": "raw", "human_delta": None}
        if os.path.exists(p):
            try:
                txt = open(p, encoding="utf-8").read()
            except Exception:
                txt = ""
            idx = txt.find("\n" + HUMAN_DELTA_MARKER)
            if idx != -1:
                entry["tier"] = "verified"
                # Capture Human Delta block: from the marker line to end-of-file (or next top-level heading)
                block_start = idx + 1  # include the marker line itself
                remaining = txt[block_start:]
                # Stop at the next top-level heading (^# ) that isn't ## (i.e. only a single #)
                next_h1 = re.search(r"\n(?=#[^#])", remaining)
                if next_h1:
                    entry["human_delta"] = remaining[:next_h1.start()].rstrip()
                else:
                    entry["human_delta"] = remaining.rstrip()
            else:
                entry["tier"] = "machine"
        counts[entry["tier"]] += 1
        counts["total"] += 1
        days.append(entry)
        d += timedelta(days=1)
    return days, counts


def coverage_confidence(counts):
    """Compute HIGH/MEDIUM/LOW confidence label from coverage counts."""
    if counts["verified"] == counts["total"]:
        return "HIGH"
    if counts["verified"] >= 1:
        return "MEDIUM"
    return "LOW"


def calendar_range(start, end):
    """Pull calendar events for the whole span [start, end] inclusive.
    timeMin = start 00:00 local ISO, timeMax = (end+1day) 00:00 local ISO.
    Returns ({date_str: [(hhmm, title)]}, status_str).
    Fail-soft: on any exception returns ({}, 'source-unavailable')."""
    local_tz = datetime.now().astimezone().tzinfo
    time_min = datetime.combine(start, dtime.min, tzinfo=local_tz).isoformat()
    time_max = datetime.combine(end + timedelta(days=1), dtime.min, tzinfo=local_tz).isoformat()

    def one(cal_id):
        params = {"calendarId": cal_id, "maxResults": 250, "singleEvents": True,
                  "orderBy": "startTime", "timeMin": time_min, "timeMax": time_max}
        return gws_json(["calendar", "events", "list", "--params", json.dumps(params)]).get("items", [])

    try:
        evs = one(PERSONAL_CAL) + one(AGENTOPS_CAL)
    except Exception as e:
        sys.stderr.write(f"cal-rollup: calendar read failed: {e}\n")
        return {}, "source-unavailable"

    seen, by_date = set(), {}
    for e in evs:
        st = e.get("start", {})
        when = st.get("dateTime") or st.get("date") or ""
        summary = e.get("summary", "(untitled)").strip()
        key = (summary.lower(), when)
        if key in seen:
            continue
        seen.add(key)
        hhmm = ""
        date_str = ""
        if "dateTime" in st:
            try:
                dt = datetime.fromisoformat(st["dateTime"])
                hhmm = dt.strftime("%H:%M")
                date_str = dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
        elif "date" in st:
            date_str = st["date"]
        if not date_str:
            continue
        by_date.setdefault(date_str, []).append((hhmm, summary))

    # Sort events within each day
    for k in by_date:
        by_date[k].sort()
    return by_date, "ok"


def journal_range(start, end, aliases=None):
    """Aggregate journal activity in [start,end] BY DESK and BY SLUG → ({desk:[ev]}, {slug:[ev]}).
    Parses TWO formats:
      1. Pipe-delimited rows (historical): `| date | desk | slug | event |` and the older variant.
      2. Prose SESSION CONTEXT blocks (current): headers `## SESSION CONTEXT — date | desk | slug (...)`.
    `aliases` {old_slug: canonical} folds a renamed/merged project's history under one slug."""
    aliases = aliases or {}
    by_desk, by_slug = {}, {}
    try:
        with open(JOURNAL, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return by_desk, by_slug, "source-unavailable"
    sset = {(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)}
    OLD = re.compile(r"^\d{4}-\d{2}-\d{2}\s*\|")  # pre-June format: leading DATE, no leading pipe
    # Matches ## or ### SESSION CONTEXT headers with an em-dash (U+2014) followed by pipe-delimited fields.
    SC_HDR = re.compile(r"^#{2,3}\s+SESSION CONTEXT\s*—\s*(.+)$")
    PAREN = re.compile(r"\s*\([^)]*\)\s*$")  # trailing (parenthetical) to strip from desk/slug
    DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    i = 0
    while i < len(lines):
        ln = lines[i].rstrip("\n")

        # ── Prose SESSION CONTEXT block ──────────────────────────────────────────
        m = SC_HDR.match(ln)
        if m:
            remainder = m.group(1)
            fields = [f.strip() for f in remainder.split("|")]
            date_str = fields[0].strip()
            if DATE_RE.match(date_str) and date_str in sset and len(fields) >= 2:
                desk = PAREN.sub("", fields[1]).strip()
                # Extract parenthetical from the header for fallback event text
                paren_match = re.search(r"\(([^)]+)\)", remainder)
                paren_text = paren_match.group(1) if paren_match else ""
                if len(fields) >= 3 and fields[2]:
                    slug = PAREN.sub("", fields[2]).strip()
                else:
                    slug = desk  # desk-level session: slug = desk so it shows as a dot
                slug = aliases.get(slug, slug)

                # Scan the block body (until next ## heading or EOF) for event text
                event = ""
                j = i + 1
                while j < len(lines):
                    body_ln = lines[j].rstrip("\n")
                    if body_ln.startswith("## ") or body_ln.startswith("### "):
                        break
                    # Priority 1: **Session:** marker
                    sm = re.match(r"^\*\*Session:\*\*\s*(.+)", body_ln)
                    if sm:
                        event = sm.group(1).strip()
                        break
                    # Priority 2: **End state:** or **End state —** marker
                    em = re.match(r"^\*\*End state(?:\s*[:—])?\*\*\s*(.+)", body_ln)
                    if em:
                        event = em.group(1).strip()
                        break
                    j += 1

                # Priority 3: parenthetical from the header
                if not event and paren_text:
                    event = paren_text.strip()

                # Priority 4: first non-empty, non-bold-only prose line in the block
                if not event:
                    j2 = i + 1
                    while j2 < len(lines):
                        body_ln = lines[j2].rstrip("\n")
                        if body_ln.startswith("## ") or body_ln.startswith("### "):
                            break
                        stripped = body_ln.strip()
                        if stripped and stripped not in ("**", "__"):
                            event = stripped
                            break
                        j2 += 1

                # Strip markdown bold markers and truncate
                event = re.sub(r"\*\*", "", event).strip()
                event = (event[:140] + "…") if len(event) > 140 else event

                if desk and event:
                    by_desk.setdefault(desk, []).append(f"[{slug}] {event}")
                    by_slug.setdefault(slug, []).append(f"[{desk}] {event}")
            i += 1
            continue

        # ── Pipe-delimited rows (historical) ─────────────────────────────────────
        parts = [p.strip() for p in ln.split("|")]
        # NEW format (Jun 2026→): `| date | desk | slug | event |` → date/desk/slug/event = parts[1..4]
        if ln.startswith("| ") and len(parts) >= 5:
            date, desk, slug, event = parts[1], parts[2], parts[3], parts[4]
        # OLD format (pre-Jun): `date | desk | slug | event | …` → the leading pipe is absent, cols shift −1
        elif OLD.match(ln) and len(parts) >= 4:
            date, desk, slug, event = parts[0], parts[1], parts[2], parts[3]
        else:
            i += 1
            continue
        if date not in sset:
            i += 1
            continue
        slug = aliases.get(slug, slug)  # fold a renamed/merged slug into its canonical project
        event = (event[:140] + "…") if len(event) > 140 else event
        by_desk.setdefault(desk, []).append(f"[{slug}] {event}")
        by_slug.setdefault(slug, []).append(f"[{desk}] {event}")
        i += 1
    return by_desk, by_slug, "ok"


def read_registry():
    """Active/paused slugs from the project registry → {slug: desk}. This is the watchlist:
    it lets a tracked project show as 'quiet' when it has no activity, instead of vanishing.
    Fail-soft (registry unreadable → empty watchlist, no quiet line)."""
    tracked = {}
    try:
        with open(PROJECT_REGISTRY, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return tracked
    for ln in lines:
        if "|" not in ln:
            continue
        parts = [p.strip() for p in ln.split("|")]
        if len(parts) < 4:
            continue
        desk, slug, status = parts[0], parts[1], parts[3]
        # accept only real kebab-case slugs (rejects the format-doc line {desk}|{slug}|… and headers)
        if not slug or not all(c.islower() or c.isdigit() or c == "-" for c in slug):
            continue
        st = status.lower()
        if st.startswith("active") or st.startswith("paused"):
            tracked[slug] = desk
    return tracked


def read_aliases():
    """Parse the registry's rename/merge notes → ({old_slug: canonical_slug}, [ambiguous]).
    HIGH-confidence, auto-applied: 'renamed from X' / 'slug standardized from X' (X → this slug),
    'merged → Y' (this slug → Y). AMBIGUOUS, surfaced not auto-applied: 'dissolved → …', 'split',
    'superseded → Y' (a split/replacement, not a clean continuation). Fail-soft → ({}, [])."""
    alias, ambiguous = {}, []
    try:
        with open(PROJECT_REGISTRY, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return alias, ambiguous
    for ln in lines:
        if "|" not in ln:
            continue
        parts = [p.strip() for p in ln.split("|")]
        if len(parts) < 4:
            continue
        slug, status = parts[1], parts[3]
        if not slug or not all(c.islower() or c.isdigit() or c == "-" for c in slug):
            continue
        st = status.lower()
        m = re.search(r"(?:renamed from|slug standardized from)\s+([a-z0-9-]+)", st)
        if m:                                       # old X → this (canonical) slug
            alias[m.group(1)] = slug
        m2 = re.search(r"merged\s*→\s*([a-z0-9-]+)", st)
        if m2:                                      # this slug merged INTO Y
            alias[slug] = m2.group(1)
        if ("dissolved →" in st) or ("split" in st) or ("superseded →" in st):
            ambiguous.append((slug, status))        # surface for a human call — never auto-applied
    alias.update(CONFIRMED_ALIASES)                 # apply the human-resolved folds
    resolved = set(CONFIRMED_ALIASES) | REVIEWED_NO_ALIAS
    ambiguous = [(s, n) for s, n in ambiguous if s not in resolved]  # drop anything already decided
    return alias, ambiguous


def completed_tasks_range(start, end):
    cmin = datetime.combine(start, dtime.min).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cmax = datetime.combine(end + timedelta(days=1), dtime.min).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        params = {"tasklist": LIFEMAP_TASKLIST, "showCompleted": True, "showHidden": True,
                  "completedMin": cmin, "completedMax": cmax, "maxResults": 100}
        data = gws_json(["tasks", "tasks", "list", "--params", json.dumps(params)])
        return [t.get("title", "(untitled)").strip() for t in data.get("items", [])
                if t.get("status") == "completed"], "ok"
    except Exception as e:
        sys.stderr.write(f"cal-rollup: tasks read failed: {e}\n")
        return [], "source-unavailable"


def pull_win(cadence):
    """The PLAN side: the period's Win goal from the Life Map (read-only)."""
    title = WIN_TITLE.get(cadence)
    if not title:
        return None, "n/a"  # quarterly has no Life-Map Win horizon
    try:
        data = gws_json(["tasks", "tasks", "list", "--params",
                         json.dumps({"tasklist": LIFEMAP_TASKLIST, "showCompleted": False, "maxResults": 100})])
        items = data.get("items", [])
        parent = next((t for t in items if t.get("title", "").strip() == title), None)
        if not parent:
            return None, "ok"
        if cadence in ("monthly", "yearly"):
            return (parent.get("notes") or "").strip(), "ok"
        kids = [t.get("title", "").strip() for t in items if t.get("parent") == parent.get("id")]
        return kids, "ok"
    except Exception as e:
        sys.stderr.write(f"cal-rollup: win pull failed: {e}\n")
        return None, "source-unavailable"


def preserve_human_delta(path):
    if not os.path.exists(path):
        return ""
    try:
        txt = open(path, encoding="utf-8").read()
    except Exception:
        return ""
    idx = txt.find("\n" + HUMAN_DELTA_MARKER)
    return (txt[idx + 1:].rstrip() + "\n") if idx != -1 else ""


# ---------- compose ----------

def build(cadence, label, start, end, pointers, journal, by_slug, tracked, tasks, win, win_state, src,
          backfill=False, days_coverage=None, cov_counts=None, cal_by_date=None):
    days_coverage = days_coverage or []
    cov_counts = cov_counts or {"verified": 0, "machine": 0, "raw": 0, "total": 0}
    cal_by_date = cal_by_date or {}
    conf_label = coverage_confidence(cov_counts)

    desks = sorted(journal.keys())
    n_events = sum(len(v) for v in journal.values())
    out = ["---"]
    out.append(f"type: cal-diary-review")
    out.append(f"cadence: {cadence}")
    out.append(f"period: {label}")
    out.append(f"range: {start.isoformat()}..{end.isoformat()}")
    out.append(f"scope: [{', '.join(desks)}]")
    out.append(f"projects: [{', '.join(sorted(by_slug.keys()))}]")
    out.append(f'generated_at: "{iso_now()}"')
    out.append(f"sources: {json.dumps(src)}")
    out.append(f"confidence: {conf_label.lower()}")
    if backfill:  # historical reconstruction — machine guess, no contemporaneous human check-in
        out.append("backfilled: true")
    out.append("---\n")
    out.append(f"# {cadence.capitalize()} Review — {label}  ({start:%b %d} – {end:%b %d})\n")
    out.append("<!-- TEE-UP draft (machine, unverified). The check-in confirms/corrects, adds the "
               "Human Delta, and promotes durable facts into canon.md via reasoned-or-repeated. -->\n")

    # COVERAGE & CONFIDENCE
    out.append("## Coverage & confidence")
    v, m, r, tot = cov_counts["verified"], cov_counts["machine"], cov_counts["raw"], cov_counts["total"]
    out.append(f"- **{v}/{tot} days human-verified · {m}/{tot} machine-captured · "
               f"{r}/{tot} raw-reconstructed → overall: {conf_label}**")
    per_day = " · ".join(f"{d['date']} {d['tier']}" for d in days_coverage)
    out.append(f"- Per-day: {per_day}")
    out.append("")

    # PLAN (the Win goal)
    out.append("## Plan — the Win for this period")
    if win_state == "n/a":
        out.append("_quarterly has no Life-Map Win horizon — set the quarterly intent at check-in_")
    elif win_state != "ok":
        out.append("_source-unavailable (Life Map read failed this run)_")
    elif not win:
        out.append(f"_no {WIN_TITLE.get(cadence,'Win')} set_")
    elif isinstance(win, list):
        for w in win:
            out.append(f"- {w}")
    else:
        out.append(win)
    out.append("")

    # WHAT HAPPENED (the actual side)
    out.append("## What happened (machine recap, unverified)")
    out.append(f"- {n_events} journal event(s) across {len(desks)} desk(s) · "
               f"{len(tasks)} task(s) completed · {len(pointers)} daily entr{'y' if len(pointers)==1 else 'ies'} captured.")
    if journal:
        busiest = max(journal.items(), key=lambda kv: len(kv[1]))[0]
        out.append(f"- Busiest desk: **{busiest}** ({len(journal[busiest])} events).")
    out.append("")

    # DELTA scaffold (deltas-first — the WHY is for the human)
    out.append("## Delta — plan vs. actual (scaffold)")
    out.append("- ⚠️ **unverified — needs HITL.** Mechanical: the Plan above vs. the activity below. "
               "Only the human can supply the *why* of any gap (the gray matter). The check-in fills this.")
    out.append("")

    # Per-desk activity
    if src["journal"] != "ok":
        out.append("## Activity by desk\n_source-unavailable (journal read failed this run)_\n")
    elif desks:
        out.append("## Activity by desk")
        for desk in desks:
            out.append(f"### {desk} ({len(journal[desk])})")
            for b in journal[desk][:8]:
                out.append(f"- {b}")
            if len(journal[desk]) > 8:
                out.append(f"- … +{len(journal[desk]) - 8} more (see daily entries)")
        out.append("")

    # Per-PROJECT activity — the plot "dots" (origin→now for a slug) + the watchlist quiet markers.
    # Present project = had journal entries this period; tracked-but-silent = a compact "quiet" line
    # (so a dormant project shows as QUIET, never silently vanishes — but no 40-block ABSENT noise).
    if src["journal"] == "ok":
        slugs_present = sorted(by_slug.keys())
        out.append("## Activity by project")
        if slugs_present:
            for slug in slugs_present:
                out.append(f"### {slug} ({len(by_slug[slug])})")
                for b in by_slug[slug][:8]:
                    out.append(f"- {b}")
                if len(by_slug[slug]) > 8:
                    out.append(f"- … +{len(by_slug[slug]) - 8} more")
        else:
            out.append("_no project-tagged activity this period_")
        if tracked:
            quiet = sorted(s for s in tracked if s not in by_slug)
            if quiet:
                out.append("")
                out.append("**Quiet this period** (registry-active, no entries — tracked but dormant): "
                           + ", ".join(f"`{s}`" for s in quiet))
        out.append("")

    # Completed tasks
    out.append("## Tasks completed this period")
    if src["tasks"] != "ok":
        out.append("_source-unavailable (tasks read failed this run)_")
    elif not tasks:
        out.append("_none recorded_  <!-- note: Google purges completed tasks >30d, so long periods may undercount -->")
    else:
        for t in tasks[:40]:
            out.append(f"- {t}")
    out.append("")

    # Daily pointers (the look-back detail lives in the dailies)
    out.append("## Daily entries (pointers)")
    if pointers:
        for d, rel in pointers:
            out.append(f"- {d} → `{rel}`")
    else:
        out.append("_no daily entries captured in this period_")
    out.append("")

    # CALENDAR & WHEREABOUTS (live calendar backstop)
    out.append("## Calendar & whereabouts")
    if src.get("calendar") == "source-unavailable":
        out.append("_source-unavailable (calendar read failed this run)_")
    elif not cal_by_date:
        out.append("_no calendar events found for this period_")
    else:
        # Build a set of raw-tier dates for annotation
        raw_dates = {d["date"] for d in days_coverage if d["tier"] == "raw"}
        d = start
        while d <= end:
            ds = d.isoformat()
            evs = cal_by_date.get(ds, [])
            raw_note = " _(raw-reconstructed)_" if ds in raw_dates else ""
            out.append(f"### {ds}{raw_note}")
            if evs:
                for hhmm, title in evs:
                    out.append(f"- {hhmm + '  ' if hhmm else ''}{title}")
            else:
                out.append("_no events_")
            d += timedelta(days=1)
    out.append("")

    # HUMAN-VERIFIED NOTES (rolled-up Human Delta blocks from verified days)
    out.append("## Human-verified notes (rolled up)")
    verified_days = [d for d in days_coverage if d["tier"] == "verified"]
    if not verified_days:
        out.append("_none this week — no daily check-ins were verified_")
    else:
        for d in verified_days:
            out.append(f"### {d['date']}")
            out.append(d["human_delta"] or "_no content_")
            out.append("")
    out.append("")

    # Promote? — candidates for canon (NOT auto-promoted)
    out.append("## Promote to canon? (check-in decides — reasoned-or-repeated)")
    out.append("- _candidates the human marks during the check-in; nothing graduates automatically_")
    out.append("")

    return "\n".join(out).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cadence", required=True, choices=["weekly", "monthly", "quarterly", "yearly"])
    ap.add_argument("--date", help="anchor YYYY-MM-DD (default today); period = the one containing it")
    ap.add_argument("--backfill", action="store_true",
                    help="historical reconstruction — stamp frontmatter backfilled:true + confidence:low")
    args = ap.parse_args()

    if args.date:
        try:
            anchor = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            sys.stderr.write("cal-rollup: --date must be YYYY-MM-DD\n"); return 2
    else:
        anchor = datetime.now().date()

    aliases, _ambiguous = read_aliases()
    label, start, end, out_path = period_range(args.cadence, anchor)
    pointers = daily_pointers(start, end)
    journal, by_slug, s_j = journal_range(start, end, aliases)
    tracked = read_registry()
    tasks, s_t = completed_tasks_range(start, end)
    win, s_w = pull_win(args.cadence)
    days_cov, cov_counts = day_coverage(start, end)
    cal_by_date, s_c = calendar_range(start, end)
    src = {"journal": s_j, "tasks": s_t, "win": s_w, "calendar": s_c}

    body = build(args.cadence, label, start, end, pointers, journal, by_slug, tracked, tasks, win, s_w, src,
                 backfill=args.backfill, days_coverage=days_cov, cov_counts=cov_counts, cal_by_date=cal_by_date)
    body = body.rstrip() + "\n\n" + preserve_human_delta(out_path)
    body = body.rstrip() + "\n"

    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        tmp = out_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(body)
        os.replace(tmp, out_path)
    except Exception as e:
        sys.stderr.write(f"cal-rollup: FATAL could not write {out_path}: {e}\n"); return 1

    bad = [k for k, v in src.items() if v not in ("ok", "n/a")]
    print(f"[cal-rollup] {args.cadence} {label} → {os.path.relpath(out_path, DRIVE)} — "
          f"{sum(len(v) for v in journal.values())} journal / {len(tasks)} tasks / {len(pointers)} dailies"
          + (f" · ⚠ source-unavailable: {', '.join(bad)}" if bad else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
