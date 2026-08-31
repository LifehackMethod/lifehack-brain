#!/usr/bin/env python3
"""calendar_sweep_pull.py — build the weekly calendar sweep's events TSV from the roster.

WHY: the v1 sweep hand-carried API results into a TSV (see calendar_sweep.py's own INPUT doc);
this helper does that mechanically. Every calendar read goes through safe_calendar.py --redact
(the sanitizer's store path) so free-text fields (titles) reaching the report have flagged
injection spans neutralized — the report is later read by sessions, so it is a store, not plumbing.
NO LLM anywhere in this path. READ-ONLY: `gws calendar events list` is the only call made,
inside safe_calendar.py.

Usage:
    python3 calendar_sweep_pull.py --roster <roster.tsv> --span-days 60 --out <events.tsv>

Roster TSV: name<TAB>calendar_id per line; lines starting '#' ignored
(the owner's copy lives at <notes>/config/calendar-sweep-roster.tsv).

Exit codes (pulse contract): 0 = every roster calendar pulled; 1 = one or more calendars failed
(a partial TSV IS still written and stderr names the failures — the caller decides whether a
partial sweep is worth reporting); 2 = setup error (missing roster, no calendars, bad args).
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
SAFE_CAL = os.path.join(_HERE, "safe_calendar.py")

TSV_HEADER = "calendar\tcalendar_id\tevent_id\ttitle\tstart\ttz_label\tcreated\tseries"


def _cell(value):
    """TSV cells must not carry tabs/newlines; free-text titles can."""
    return str(value or "").replace("\t", " ").replace("\n", " ").replace("\r", " ")


def read_roster(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2 or not parts[1].strip():
                sys.stderr.write(f"[sweep-pull] malformed roster line skipped: {line[:80]}\n")
                continue
            rows.append((parts[0].strip(), parts[1].strip()))
    return rows


def pull_calendar(name, cal_id, time_min, time_max):
    """One calendar's expanded events via safe_calendar --redact. Returns (events, ok)."""
    params = json.dumps({
        "calendarId": cal_id,
        "singleEvents": True,
        "orderBy": "startTime",
        "maxResults": 2500,
        "timeMin": time_min,
        "timeMax": time_max,
    })
    try:
        proc = subprocess.run(
            [sys.executable, SAFE_CAL, "--redact", params],
            capture_output=True, text=True, timeout=90,
        )
    except Exception as e:
        sys.stderr.write(f"[sweep-pull] {name}: safe_calendar call failed: {e}\n")
        return [], False
    # safe_calendar: 0 = clean, 1 = flagged-but-redacted (still usable data), 2 = error.
    if proc.returncode not in (0, 1):
        sys.stderr.write(f"[sweep-pull] {name}: safe_calendar rc={proc.returncode}: "
                         f"{proc.stderr.strip()[:300]}\n")
        return [], False
    try:
        data = json.loads(proc.stdout.strip())
    except Exception as e:
        sys.stderr.write(f"[sweep-pull] {name}: unparseable safe_calendar output: {e}\n")
        return [], False
    events = data.get("items") if isinstance(data, dict) else data
    return (events if isinstance(events, list) else []), True


def event_row(name, cal_id, ev):
    if not isinstance(ev, dict) or ev.get("status") == "cancelled":
        return None
    start = ev.get("start") or {}
    start_val = start.get("dateTime") or start.get("date") or ""
    if not start_val:
        return None
    return "\t".join(_cell(x) for x in (
        name, cal_id, ev.get("id", ""), ev.get("summary", ""),
        start_val, start.get("timeZone", ""), ev.get("created", ""),
        ev.get("recurringEventId", ""),
    ))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster", required=True)
    ap.add_argument("--span-days", type=int, default=60)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if not os.path.isfile(args.roster):
        sys.stderr.write(f"[sweep-pull] roster not found: {args.roster}\n")
        return 2
    roster = read_roster(args.roster)
    if not roster:
        sys.stderr.write("[sweep-pull] roster has zero usable rows\n")
        return 2

    now = datetime.now(timezone.utc)
    time_min = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    time_max = (now + timedelta(days=args.span_days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines, failures = [TSV_HEADER], []
    for name, cal_id in roster:
        events, ok = pull_calendar(name, cal_id, time_min, time_max)
        if not ok:
            failures.append(name)
            continue
        n = 0
        for ev in events:
            row = event_row(name, cal_id, ev)
            if row:
                lines.append(row)
                n += 1
        sys.stderr.write(f"[sweep-pull] {name}: {n} event(s)\n")

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    sys.stderr.write(f"[sweep-pull] wrote {len(lines) - 1} row(s) from "
                     f"{len(roster) - len(failures)}/{len(roster)} calendar(s) -> {args.out}\n")
    if failures:
        sys.stderr.write(f"[sweep-pull] FAILED calendars: {', '.join(failures)}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
