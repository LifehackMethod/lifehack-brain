#!/usr/bin/env python3
"""cal-health.py — READ-ONLY calendar health check (7-day forward window): flags timed-event
CONFLICTS (overlaps) and UNCONFIRMED invites (RSVP needsAction / tentative) across the two calendars
a person has told this system about.

PORTED (2026-08-14) from claudeops-config's system/tools/cal-health.py (408 lines) and cut down hard
on purpose — this is a scheduler-category port, not a Cal-desk feature port. Kept: the actual health
check (conflicts + unconfirmed invites), which is the thing a dead-man's-switch needs something real
to watch. Dropped, because each is either desk-specific enrichment beyond a health CHECK, or reads a
Google Tasks list this repo has no config key for: the "compass" (Life Map year/month/week/today
goals), snoozed-mail metadata, the stale-task radar, and the "brush fires" overload/buffer radar. A
future Cal-desk port can add these back onto this same tile without touching the check this file
exists to make.

⭐ THE DESIGN CONSTRAINT THIS FILE IS THE CONCRETE ANSWER TO: a student may have no Google account at
all, or one but no calendar connected yet. Two independent things must degrade cleanly, never crash:
  1. NO IDENTIFIERS CONFIGURED — `shared/cal_config.py` (already ships in this repo) holds no default
     calendar id; a fresh install has nothing in `<notes>/config/cal.md`. This is NOT an error: the
     job runs, finds nothing configured, and says so on the SAME tile a configured run would write
     (status OK, rc 0) — a student who never uses Cal never sees an alarm about it.
  2. NO `gws` / NO GOOGLE AUTH — even with ids configured, the machine might have no `gws` binary or
     no credentials. This IS worth surfacing (a real, fixable problem, not an absent feature) — the
     tile says so plainly and the runner-standard rc=1 (a real read failure) still applies so Pulse's
     circuit breaker can watch it — but the WORDING stays "not connected" rather than a stack trace.

Exit 0 on a clean or content-finding run (a conflict is a CONTENT finding, not a job failure) or on a
"not configured" run. Exit 1 only on a real gws/calendar read failure once IDs ARE configured (feeds
Pulse's circuit breaker exactly as documented in pulse-config.md's exit-code table).
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
CODE_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_SHARED = os.path.join(CODE_ROOT, "shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from brain_root import resolve_brain_root          # noqa: E402 — shared/brain_root.py
import cal_config                                    # noqa: E402 — shared/cal_config.py
from emit_finding import emit_finding, FindingContractError   # noqa: E402

SAFE_CAL = os.path.join(_HERE, "safe_calendar.py")

# routine personal time-blocks — overlapping these isn't an actionable scheduling conflict
FILLER_TITLES = {"eat", "lunch", "dinner", "breakfast", "sleep", "wake", "wake up"}
CAL_URL = "https://calendar.google.com"


def iso(epoch):
    lt = time.localtime(epoch); off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off


def read_events(cal_id, time_min, time_max):
    """One calendar's events over [time_min, time_max), via safe_calendar.py --no-isolate (a no-LLM
    health-tile computer needs the real free-text to dedup on, not a reader-scratch pointer — see
    that file's own comment on why --no-isolate is correct for plumbing callers). Raises RuntimeError
    on any read failure (missing gws, bad auth, network) — the caller maps that to rc=1."""
    params = {"calendarId": cal_id, "maxResults": 100, "singleEvents": True,
              "orderBy": "startTime", "timeMin": time_min, "timeMax": time_max}
    r = subprocess.run(["python3", SAFE_CAL, "--desk", "cal", "--no-isolate", json.dumps(params)],
                       capture_output=True, text=True)
    if r.returncode == 2:
        tail = (r.stderr.strip().splitlines() or ["(no stderr)"])[-1]
        raise RuntimeError(f"calendar read failed for {cal_id[:24]}...: {tail}")
    return json.loads(r.stdout).get("items", [])


def start_dt(ev):
    st = ev.get("start", {})
    if "dateTime" in st:
        try:
            return datetime.fromisoformat(st["dateTime"])
        except ValueError:
            return None
    return None


def end_dt(ev):
    en = ev.get("end", {})
    if "dateTime" in en:
        try:
            return datetime.fromisoformat(en["dateTime"])
        except ValueError:
            return None
    return None


def _write_tile(out_path, *, status, summary, rc, payload):
    """Minimal local tile writer — this repo does not have a shared `emit_status.py` yet (only
    `emit_finding.py`, the findings-store writer, has landed). Same envelope shape a future
    `emit_status.py` would produce (desk / schema_version / pulse_job / stale_after_s / last_run / rc
    / status / summary + payload merged in), written atomically. Replace this with a real import if
    `emit_status.py` lands later — the shape is deliberately compatible."""
    env = {"desk": "cal", "schema_version": 2, "pulse_job": "cal-health", "emit_mode": "pulse",
           "stale_after_s": 43200, "last_run": iso(int(time.time())), "rc": rc, "status": status,
           "summary": summary}
    env.update(payload)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = out_path + ".tmp"
    json.dump(env, open(tmp, "w"), indent=2)
    os.replace(tmp, out_path)


def main():
    _src, notes_root = resolve_brain_root()
    if notes_root is None:
        sys.stderr.write("[cal-health] no notes root configured (shared/brain_root.py) — nothing to check or write yet.\n")
        return 0
    out_path = os.path.join(notes_root, "state", "status", "cal.json")

    # ── 1) Are the two calendar ids even configured? ────────────────────────────────────────────
    try:
        ids = cal_config.require("personal_calendar", "agent_calendar", notes_root=notes_root)
    except cal_config.CalConfigMissing as e:
        summary = "not configured — no calendar connected yet"
        _write_tile(out_path, status="OK", summary=summary, rc=0,
                    payload={"work_count": 0, "work_noun": "flags", "kpis": [], "items": [],
                             "configured": False, "link": CAL_URL})
        try:
            emit_finding(producer="cal-health", status="OK", scanned_n=1,
                        labels={"job": "cal-health", "check": "calendar"},
                        summary=summary, payload={"detail": str(e)}, rc=0)
        except (FindingContractError, Exception) as fe:
            sys.stderr.write(f"[cal-health] emit_finding failed: {fe}\n")
        print(f"[cal-health] {summary}")
        return 0

    personal_cal, agent_cal = ids["personal_calendar"], ids["agent_calendar"]
    calendars = (personal_cal, agent_cal)

    # ── 2) Configured — do the actual read-only check. A read failure here (no gws / bad auth /
    # network) is a REAL problem worth Pulse's circuit breaker, not a "not configured" state. ──────
    now = datetime.now(timezone.utc)
    t_min, t_max = now.isoformat(), (now + timedelta(days=7)).isoformat()
    t_72 = now + timedelta(hours=72)
    try:
        evs = read_events(personal_cal, t_min, t_max) + read_events(agent_cal, t_min, t_max)
    except Exception as e:
        sys.stderr.write(f"[cal-health] {e}\n")
        _write_tile(out_path, status="ERROR", summary=f"calendar read failed: {e}", rc=1,
                    payload={"work_count": 0, "work_noun": "flags", "kpis": [], "items": [],
                             "configured": True, "link": CAL_URL})
        return 1
    calendars_scanned = len(calendars)

    seen, merged = set(), []
    for e in evs:
        st = e.get("start", {})
        key = (e.get("summary", "").strip().lower(), st.get("dateTime") or st.get("date") or "")
        if key in seen:
            continue
        seen.add(key)
        merged.append(e)

    events_7d, events_72h = len(merged), 0
    timed = []
    for e in merged:
        s, en = start_dt(e), end_dt(e)
        if s and s <= t_72:
            events_72h += 1
        if s and en:
            timed.append((s, en, e))

    items, conflicts = [], 0
    timed.sort(key=lambda x: x[0])
    for i in range(len(timed)):
        s1, e1, ev1 = timed[i]
        for j in range(i + 1, len(timed)):
            s2, e2, ev2 = timed[j]
            if s2 >= e1:
                break
            t1 = ev1.get("summary", "").strip().lower()
            t2 = ev2.get("summary", "").strip().lower()
            if t1 and t2 and (t1 == t2 or t1 in t2 or t2 in t1):
                continue
            if t1 in FILLER_TITLES or t2 in FILLER_TITLES:
                continue
            conflicts += 1
            items.append({
                "title": f"CONFLICT: {ev1.get('summary', '(untitled)')} <-> {ev2.get('summary', '(untitled)')}",
                "status": "NEEDS_REVIEW",
                "detail": f"overlap {s2.strftime('%a %m/%d %H:%M')}",
                "link": ev1.get("htmlLink", CAL_URL),
            })

    unconfirmed = 0
    for e in merged:
        flagged = e.get("status") == "tentative"
        if not flagged:
            for a in e.get("attendees", []) or []:
                if a.get("self") and a.get("responseStatus") == "needsAction":
                    flagged = True
                    break
        if flagged:
            unconfirmed += 1
            items.append({
                "title": f"UNCONFIRMED: {e.get('summary', '(untitled)')}",
                "status": "NEEDS_REVIEW", "detail": "RSVP pending",
                "link": e.get("htmlLink", CAL_URL),
            })

    flags = conflicts + unconfirmed
    status = "NEEDS_REVIEW" if flags else "OK"
    summary = (f"{events_72h} event(s) in 72h - {conflicts} conflict(s), {unconfirmed} unconfirmed."
               if flags else f"Calendar clear - {events_7d} event(s) in 7d, no conflicts.")

    kpis = [{"key": "events_72h", "label": "Events (72h)", "value": str(events_72h)},
            {"key": "events_7d", "label": "Events (7d)", "value": str(events_7d)},
            {"key": "conflicts", "label": "Conflicts", "value": str(conflicts)},
            {"key": "unconfirmed", "label": "Unconfirmed", "value": str(unconfirmed)}]

    _write_tile(out_path, status=status, summary=summary, rc=0,
                payload={"work_count": flags, "work_noun": "flags", "kpis": kpis,
                         "items": items[:8], "configured": True, "link": CAL_URL})

    try:
        emit_finding(
            producer="cal-health", status=status, scanned_n=calendars_scanned,
            labels={"job": "cal-health", "check": "calendar"}, summary=summary,
            payload={"conflicts": conflicts, "unconfirmed": unconfirmed,
                     "events_72h": events_72h, "events_7d": events_7d},
            rc=0 if status == "OK" else 1,
        )
    except (FindingContractError, Exception) as e:
        sys.stderr.write(f"[cal-health] emit_finding failed: {e}\n")

    print(f"[cal-health] {summary} -> {status}")
    for it in items[:8]:
        print(f"  ! {it['title']}: {it['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
