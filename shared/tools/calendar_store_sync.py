#!/usr/bin/env python3
"""calendar_store_sync.py — mechanical writer for the durable Calendar item store (Phase G-3).

Mirrors the tasks writer pattern (tasks_store_sync.py) and the email writer pattern
(email_summary_sync.py) for Google Calendar events:
  - Pulls via safe_calendar.py --redact (sanitized, injection spans neutralized)
  - One durable item record per event written atomically (.tmp→rename) to a BLUE-GREEN
    store at $DRIVE/state/item-store/calendar/{event_id}.json
  - Lifecycle (mirrors email + tasks):
      past event (end < now)         → state=cold  (graceful retirement — NEVER deleted)
      event.status == 'cancelled'    → state=cold
      new/future event               → state=active
      event re-appears after cold    → state=active (revive)
  - Delta-only: unchanged events (same updated timestamp) are skipped
  - No LLM in the write path — mechanical only

Usage:
  python3 calendar_store_sync.py --sync [--calendar-id <id>] [--verbose] [--dry-run]
  python3 calendar_store_sync.py --self-test

Security: pulls run through safe_calendar.py --redact; injection spans are neutralized
before any field is stored. The raw free-text never hits the store unchecked.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────

CODE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# The data root, through the one resolver (shared/brain_root.py) — never a hardcoded personal Drive
# path. NOT-SET degrades DRIVE to "" rather than guessing; the store then simply resolves to nothing
# found, which the existing os.path.isdir/os.path.exists checks already handle gracefully.
if os.path.join(CODE_ROOT, "shared") not in sys.path:
    sys.path.insert(0, os.path.join(CODE_ROOT, "shared"))
import brain_root                                                            # noqa: E402
import cal_config                                                            # noqa: E402
_BR_SOURCE, _BR_PATH = brain_root.resolve_brain_root()
DRIVE = _BR_PATH or ""

SAFE_CALENDAR = os.path.join(CODE_ROOT, "system", "tools", "safe_calendar.py")

# gws binary — resolve via PATH (same pattern as safe_calendar.py). Called via subprocess (NOT the Bash
# tool), so the ingest hook doesn't gate it; `calendar calendarList list` is calendar METADATA (ids +
# names). Names can be shared/third-party-authored → stored as free-text + SCANNED at read.
GWS_BIN = __import__("shutil").which("gws") or "/opt/homebrew/bin/gws"

# Blue-green store path — BESIDE email-summary and tasks, NEVER touching them.
STORE_ROOT = os.path.join(DRIVE, "state", "item-store", "calendar")

WRITER_ID = "calendar-store-sync"
SOURCE = "google-calendar"

# ─────────────────────────────────────────────────────────────────────────────
# CALENDAR ALLOWLIST — resolved from the reader's OWN shared/cal_config.py, never hardcoded.
# ⛔ THIS WAS THE WORST LEAK IN THIS FILE: it hardcoded FIVE of the original author's real calendar
# addresses — his own personal account, the Agent-Ops calendar id, his consulting-business domain, and
# a NAMED THIRD PARTY'S personal email. A public repo must never carry any of that.
# cal_config.py only knows two identifiers this system can name without guessing: personal_calendar
# (the reader's own calendar — read-only) and agent_calendar (the one calendar this system may write
# to). Anything beyond those two — a coaching-business calendar, a shared family calendar, a public
# holiday feed — is NOT a generalizable default; a reader who wants more calendars pulled adds them by
# editing their own <notes>/config/cal.md and this dict, never by another commit to this file.
# A key that is not on file is simply OMITTED here (fewer calendars pulled), never guessed or defaulted.
# ─────────────────────────────────────────────────────────────────────────────
def _default_calendar_allowlist():
    cfg = cal_config.load()
    out = {}
    personal = cfg.get("personal_calendar")
    if personal:
        out[personal] = "Personal"
    agent = cfg.get("agent_calendar")
    if agent:
        out[agent] = "Agent Calendar"
    return out


CALENDAR_ALLOWLIST = _default_calendar_allowlist()

# TWO-PASS window model (CT-3.5, fixes the 25k-instance explosion):
#   Pass R (recurring SERIES MASTERS): singleEvents=False → ONE record per series (the RRULE), NOT expanded.
#     Pulled WITHOUT an upper bound and with a wide lookback so a series that started years ago is still caught.
#   Pass O (true ONE-OFF events): singleEvents=True, tight ±window → we don't want thousands of ancient one-offs.
ONEOFF_LOOKBACK_DAYS = 90     # Pass O: how far back one-off events are kept
ONEOFF_LOOKAHEAD_DAYS = 90    # Pass O: how far forward one-off events are kept
SERIES_LOOKBACK_DAYS = 1825   # Pass R: ~5y back so long-running recurring series' masters are still returned

# ─────────────────────────────────────────────────────────────────────────────
# Schema import
# ─────────────────────────────────────────────────────────────────────────────

_SHARED_TOOLS = os.path.join(CODE_ROOT, "shared", "tools")
if _SHARED_TOOLS not in sys.path:
    sys.path.insert(0, _SHARED_TOOLS)

try:
    from item_schema import (
        validate_item_record, make_item_record, make_calendar_payload,
        VALID_STATES,
    )
    _SCHEMA_AVAILABLE = True
    _SCHEMA_ERROR = None
except Exception as _se:
    _SCHEMA_AVAILABLE = False
    _SCHEMA_ERROR = str(_se)
    sys.stderr.write(
        f"[calendar-store-sync] FATAL: item_schema import failed ({_se}); "
        "writer will HARD-STOP before any live run.\n")


# ─────────────────────────────────────────────────────────────────────────────
# Security imports — scan_for_injection (system/tools) + intake reader (shared/tools)
# ─────────────────────────────────────────────────────────────────────────────

_SYS_TOOLS = os.path.join(CODE_ROOT, "system", "tools")
if _SYS_TOOLS not in sys.path:
    sys.path.insert(0, _SYS_TOOLS)

try:
    from safe_input import scan_for_injection as _scan_for_injection
    _SCAN_AVAILABLE = True
except Exception as _scan_e:
    _scan_for_injection = None
    _SCAN_AVAILABLE = False
    sys.stderr.write(f"[calendar-store-sync] WARNING: scan_for_injection import failed ({_scan_e}); "
                     "writer will HARD-STOP before storing any event free-text.\n")

try:
    from intake_reader import run_intake_judge as _run_intake_judge
    _READER_AVAILABLE = True
except Exception as _reader_e:
    _run_intake_judge = None
    _READER_AVAILABLE = False
    sys.stderr.write(f"[calendar-store-sync] WARNING: intake_reader import failed ({_reader_e}); "
                     "writer will HARD-STOP before storing any event free-text.\n")


# ─────────────────────────────────────────────────────────────────────────────
# Timestamp helpers
# ─────────────────────────────────────────────────────────────────────────────

def _iso_now():
    lt = time.localtime()
    off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off


def _parse_dt(s):
    """Parse an ISO-8601 datetime string to a timezone-aware datetime. Returns None on failure."""
    if not s:
        return None
    try:
        clean = s.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except Exception:
        return None


def _event_end_dt(event_raw):
    """Extract the event end as a datetime. Handles both dateTime and date fields."""
    end = event_raw.get("end") or {}
    if isinstance(end, dict):
        s = end.get("dateTime") or end.get("date") or ""
    elif isinstance(end, str):
        s = end
    else:
        s = ""
    if not s:
        return None
    # date-only (YYYY-MM-DD) → treat as end of that day in UTC
    if len(s) == 10:
        try:
            return datetime(int(s[:4]), int(s[5:7]), int(s[8:10]),
                            23, 59, 59, tzinfo=timezone.utc)
        except Exception:
            return None
    return _parse_dt(s)


def _event_start_str(event_raw):
    """Extract start as a string (dateTime or date, whichever is present)."""
    start = event_raw.get("start") or {}
    if isinstance(start, dict):
        return start.get("dateTime") or start.get("date") or ""
    return str(start) if start else ""


def _event_end_str(event_raw):
    """Extract end as a string (dateTime or date, whichever is present)."""
    end = event_raw.get("end") or {}
    if isinstance(end, dict):
        return end.get("dateTime") or end.get("date") or ""
    return str(end) if end else ""


# ─────────────────────────────────────────────────────────────────────────────
# Store I/O — atomic write (mirrors write_thread_v2_atomic exactly)
# ─────────────────────────────────────────────────────────────────────────────

def _event_path(event_id):
    # event ids can contain characters unsafe for filenames on some systems;
    # use a sha256-based short hash as the filename to be safe.
    import hashlib
    safe_id = hashlib.sha256(event_id.encode()).hexdigest()[:16] + "_" + \
        "".join(c for c in event_id[:32] if c.isalnum() or c in "-_")
    return os.path.join(STORE_ROOT, f"{safe_id}.json")


def _load_record_by_event_id(event_id):
    path = _event_path(event_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_atomic(event_id, record):
    """Atomically write {safe_event_id}.json via .tmp → os.replace."""
    os.makedirs(STORE_ROOT, exist_ok=True)
    path = _event_path(event_id)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    # S8.4 append-on-write (optimisation only — see store_date_index.py's contract): keep the sidecar
    # date-index current without waiting for the next read's reconciliation. Never raises.
    try:
        import store_date_index as _sdi
        _sdi.append_entry("calendar", os.path.basename(path), path)
    except Exception:
        pass


def _list_stored_paths():
    """Return a dict of {item_id: path} for all records in the store."""
    if not os.path.isdir(STORE_ROOT):
        return {}
    result = {}
    for fn in os.listdir(STORE_ROOT):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(STORE_ROOT, fn)
        try:
            with open(path, encoding="utf-8") as f:
                rec = json.load(f)
            iid = rec.get("item_id", "")
            if iid:
                result[iid] = path
        except Exception:
            pass
    return result


# ─────────────────────────────────────────────────────────────────────────────
# safe_calendar.py integration — subprocess pull with --redact
# ─────────────────────────────────────────────────────────────────────────────

def _pull_paginated(base_params, timeout=60, max_pages=40):
    """Pull ALL pages for a params dict via safe_calendar.py --redact, following nextPageToken.
    Returns (items_list, rc). rc: 0=clean, 1=some page flagged, 2=error."""
    all_items = []
    page_token = None
    worst_rc = 0
    for _page in range(max_pages):
        p = dict(base_params)
        if page_token:
            p["pageToken"] = page_token
        one, rc = _pull_events_page(json.dumps(p), timeout=timeout)
        if one is None:
            return None, 2
        if rc == 1:
            worst_rc = 1
        items, page_token = one
        all_items.extend(items)
        if not page_token:
            break
    return all_items, worst_rc


def _pull_series(calendar_id, timeout=60, max_pages=60):
    """PASS R — recurring SERIES MASTERS. singleEvents=False returns each series as ONE unexpanded master
    (carrying its `recurrence` RRULE) instead of every occurrence. Wide lookback (SERIES_LOOKBACK_DAYS), NO
    upper bound → a long-running series is still caught. Caller keeps only items WITH a `recurrence` field.
    NOTE: `orderBy:startTime` is INVALID when singleEvents=False, so it is omitted here."""
    from datetime import timedelta
    now_utc = datetime.now(tz=timezone.utc)
    time_min = (now_utc - timedelta(days=SERIES_LOOKBACK_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return _pull_paginated({
        "calendarId": calendar_id,
        "maxResults": 500,
        "singleEvents": False,
        "timeMin": time_min,
    }, timeout=timeout, max_pages=max_pages)


def _pull_oneoffs(calendar_id, timeout=60, max_pages=40):
    """PASS O — true ONE-OFF events in a tight ±window. singleEvents=True expands the window; caller keeps
    only items WITHOUT a `recurringEventId` (drops the expanded recurring occurrences — those are the 25k
    explosion — since the series is already captured as a master by Pass R)."""
    from datetime import timedelta
    now_utc = datetime.now(tz=timezone.utc)
    time_min = (now_utc - timedelta(days=ONEOFF_LOOKBACK_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    time_max = (now_utc + timedelta(days=ONEOFF_LOOKAHEAD_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return _pull_paginated({
        "calendarId": calendar_id,
        "maxResults": 500,
        "singleEvents": True,
        "orderBy": "startTime",
        "timeMin": time_min,
        "timeMax": time_max,
    }, timeout=timeout, max_pages=max_pages)


def _pull_events_page(params, timeout=60):
    """One page: run safe_calendar.py --redact. Returns ((items, nextPageToken), rc) or (None, 2)."""
    cmd = [sys.executable, SAFE_CALENDAR, "--redact", params]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        sys.stderr.write("[calendar-store-sync] safe_calendar.py timed out\n")
        return None, 2
    except Exception as e:
        sys.stderr.write(f"[calendar-store-sync] safe_calendar.py subprocess error: {e}\n")
        return None, 2

    if proc.returncode == 2:
        sys.stderr.write(
            f"[calendar-store-sync] safe_calendar.py error (exit 2): "
            f"{proc.stderr.strip()[:500]}\n")
        return None, 2

    if proc.stderr.strip():
        sys.stderr.write(
            f"[calendar-store-sync] safe_calendar stderr: {proc.stderr.strip()[:500]}\n")

    try:
        data = json.loads(proc.stdout.strip())
    except Exception as e:
        sys.stderr.write(f"[calendar-store-sync] could not parse safe_calendar output: {e}\n")
        return None, 2

    items = data.get("items", []) or []
    next_token = data.get("nextPageToken") if isinstance(data, dict) else None
    return (items, next_token), proc.returncode


# ─────────────────────────────────────────────────────────────────────────────
# CT-3.5: enumerate ALL of the user's calendars (id + name)
# ─────────────────────────────────────────────────────────────────────────────

def _list_calendars(timeout=30):
    """Enumerate the user's calendars via `gws calendar calendarList list`. Returns [(cal_id, cal_name), ...]
    or None on failure. Metadata only (no event free-text). Names can be shared/third-party → stored as
    free-text + SCANNED at read."""
    try:
        proc = subprocess.run([GWS_BIN, "calendar", "calendarList", "list"],
                              capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        sys.stderr.write(f"[calendar-store-sync] calendarList enumerate failed: {e}\n")
        return None
    if proc.returncode != 0:
        sys.stderr.write(f"[calendar-store-sync] calendarList error: {proc.stderr.strip()[:300]}\n")
        return None
    try:
        data = json.loads(proc.stdout.strip())
    except Exception as e:
        sys.stderr.write(f"[calendar-store-sync] could not parse calendarList output: {e}\n")
        return None
    out = []
    for it in (data.get("items", []) or []):
        cid = it.get("id")
        if cid:
            out.append((cid, it.get("summary") or cid))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Provenance tag
# ─────────────────────────────────────────────────────────────────────────────

def _provenance_tag(event_id):
    import hashlib
    h = hashlib.sha256(f"{event_id}:{_iso_now()}".encode()).hexdigest()[:12]
    return f"item-store/calendar/{event_id[:32]}/{h}"


# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle state logic
# ─────────────────────────────────────────────────────────────────────────────

def _lifecycle_state(event_raw, existing_record):
    """Determine the new lifecycle state for a calendar event.

    event.status == 'cancelled'  → state=cold
    past event (end < now)       → state=cold
    new event (no existing)      → state=active
    existing cold + still future → state=active (revive)
    otherwise                    → preserve existing state
    """
    gstatus = (event_raw.get("status") or "").lower()
    if gstatus == "cancelled":
        return "cold"

    # A recurring SERIES MASTER's end = the end of its FIRST occurrence (usually long past), so the
    # past-end→cold rule below would wrongly retire an active weekly series. A master (has `recurrence`)
    # stays active unless cancelled. (An exhausted series with an RRULE UNTIL in the past is a rare
    # over-inclusion — kept active, harmless, tiny.)
    if event_raw.get("recurrence"):
        if existing_record is not None and (existing_record.get("state") or "active") == "cold":
            return "active"
        return "active"

    # Check if the event has ended
    end_dt = _event_end_dt(event_raw)
    now_utc = datetime.now(tz=timezone.utc)
    if end_dt is not None:
        # Make sure end_dt is timezone-aware
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        if end_dt < now_utc:
            return "cold"

    # Event is current/future
    if existing_record is None:
        return "active"

    existing_state = existing_record.get("state") or "active"
    if existing_state == "cold":
        return "active"  # revive a cold event that's back in range or was re-scheduled
    return existing_state


def _is_unchanged(event_raw, existing_record):
    """Delta-only: skip if the event's 'updated' timestamp hasn't changed."""
    if existing_record is None:
        return False
    new_updated = event_raw.get("updated", "")
    old_updated = (existing_record.get("payload") or {}).get("updated", "")
    return bool(new_updated and new_updated == old_updated)


# ─────────────────────────────────────────────────────────────────────────────
# Core sync logic — process one calendar event
# ─────────────────────────────────────────────────────────────────────────────

def _attendee_emails(event_raw):
    """Extract attendee email addresses (structural field — safe to store directly)."""
    attendees = event_raw.get("attendees") or []
    emails = []
    for att in attendees:
        if isinstance(att, dict):
            email = att.get("email", "")
            if email:
                emails.append(email)
    return emails


def _organizer_email(event_raw):
    """Extract organizer email (structural field)."""
    org = event_raw.get("organizer") or {}
    if isinstance(org, dict):
        return org.get("email", "")
    return ""


def _process_event(event_raw, calendar_id, calendar_name=None, verbose=False, dry_run=False):
    """Build, validate, and write one calendar item record. Returns (action_str, ok_bool)."""
    event_id = event_raw.get("id", "")
    if not event_id:
        sys.stderr.write("[calendar-store-sync] skipping event with no id\n")
        return "SKIP (no id)", False

    existing = _load_record_by_event_id(event_id)

    # Delta-only skip
    if _is_unchanged(event_raw, existing):
        return f"UNCHANGED  {event_id[:24]}", True

    state = _lifecycle_state(event_raw, existing)
    now = _iso_now()
    first_seen = (existing.get("first_seen") if existing else None) or now
    prov = (existing.get("provenance_tag") if existing else None) or _provenance_tag(event_id)

    # ── Security gate: scan + decode-and-judge the event free-text fields ───────
    raw_summary = event_raw.get("summary") or ""
    raw_description = event_raw.get("description") or ""
    raw_location = event_raw.get("location") or ""
    free_text = "\n".join(filter(None, [raw_summary, raw_description, raw_location]))

    reader_applied = None
    verdict = None
    cleared_summary = raw_summary
    cleared_description = event_raw.get("description")   # preserve None vs "" distinction
    cleared_location = event_raw.get("location")         # preserve None vs "" distinction

    # HARD-STOP (verified defect (c), organism-audit 2026-07-16): if there is free-text to
    # scan but either the injection scanner or the intake judge failed to import, refuse to
    # store rather than silently skipping the scan and persisting raw attacker-controllable text.
    # Mirrors the item_schema deferred-hard-stop pattern (flag set at import, stop at use-site).
    if free_text and not (_SCAN_AVAILABLE and _READER_AVAILABLE):
        sys.stderr.write(
            "[calendar-store-sync] HARD-STOP: injection scanner / intake judge unavailable "
            f"(scan_available={_SCAN_AVAILABLE}, reader_available={_READER_AVAILABLE}); "
            "refusing to store unscanned event free-text.\n")
        sys.exit(1)

    if _SCAN_AVAILABLE and _READER_AVAILABLE and free_text:
        findings = _scan_for_injection(free_text)
        judge_result = _run_intake_judge(free_text, findings)
        reader_applied = judge_result.get("reader_applied")
        verdict = judge_result.get("verdict")
        # Splice cleared text back: split on the same newlines used to join.
        # Order matches the join above: summary, description, location.
        cleared = judge_result.get("cleared_text") or free_text
        parts = cleared.split("\n", 2)
        cleared_summary = parts[0] if len(parts) > 0 else raw_summary
        if event_raw.get("description") is not None:
            cleared_description = parts[1] if len(parts) > 1 else ""
        if event_raw.get("location") is not None:
            cleared_location = parts[2] if len(parts) > 2 else ""
    # ─────────────────────────────────────────────────────────────────────────

    payload = make_calendar_payload(
        event_id=event_id,
        summary=cleared_summary,
        start=_event_start_str(event_raw),
        end=_event_end_str(event_raw),
        status=event_raw.get("status") or "",
        calendar_id=calendar_id,
        description=cleared_description,
        location=cleared_location,
        attendees=_attendee_emails(event_raw),
        organizer=_organizer_email(event_raw),
        updated=event_raw.get("updated"),
        calendar_name=calendar_name,   # CT-3.5: which calendar, by name
        recurrence=event_raw.get("recurrence"),  # CT-3.5: RRULE for a series master → flags is_recurring
        recurring_event_id=event_raw.get("recurringEventId"),  # CT-3.5b: a dated INSTANCE's link to its master
    )

    record = make_item_record(
        item_id=event_id,
        item_type="calendar",
        payload=payload,
        writer_id=WRITER_ID,
        source=SOURCE,
        first_seen=first_seen,
        last_synced=now,
        provenance_tag=prov,
        state=state,
    )

    # Attach security metadata when the reader ran (optional schema fields).
    if reader_applied is not None:
        record["reader_applied"] = reader_applied
    if verdict is not None:
        record["verdict"] = verdict

    violations = validate_item_record(record)
    if violations:
        sys.stderr.write(
            f"[calendar-store-sync] {event_id} SCHEMA VIOLATION (record NOT written): {violations}\n")
        return f"SCHEMA-FAIL {event_id[:24]}: {violations[0][:60]}", False

    if dry_run:
        if verbose:
            print(f"  DRY  {event_id} — {event_raw.get('summary','')[:50]} ({state})")
        return f"DRY   {event_id[:24]} — {state}", True

    _write_atomic(event_id, record)
    if verbose:
        print(f"  WRITE {event_id} — {event_raw.get('summary','')[:50]} ({state})")
    return f"WRITE {event_id[:24]} — {state}", True


# ─────────────────────────────────────────────────────────────────────────────
# Cold sweep — events that vanished from the pull window → state=cold (NEVER delete)
# ─────────────────────────────────────────────────────────────────────────────

def _cold_sweep(active_ids, dry_run=False, verbose=False):
    """Mark records for events no longer in the pull as state=cold. Never deletes."""
    stored = _list_stored_paths()  # {item_id: path}
    cold_count = 0
    for eid, path in stored.items():
        if eid in active_ids:
            continue
        try:
            with open(path, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            continue
        if (rec.get("state") or "active") in ("cold", "completed", "deep-cold"):
            continue
        rec["state"] = "cold"
        rec["cold_at"] = _iso_now()
        if not dry_run:
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(rec, f, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
        cold_count += 1
        if verbose:
            print(f"  COLD  {eid[:24]} — departed from pull window")
    return cold_count


# ─────────────────────────────────────────────────────────────────────────────
# Default calendar — the reader's own, from cal_config (never hardcoded). Unused elsewhere in this
# module today (sync() resolves via CALENDAR_ALLOWLIST / _resolve_calendars instead); kept for a
# future targeted-run default, so it holds the SAME never-guess contract as the allowlist above.
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_CALENDAR_ID = cal_config.load().get("personal_calendar", "")


# ─────────────────────────────────────────────────────────────────────────────
# Public sync entry point
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_calendars(calendar_id):
    """Return [(cal_id, cal_name), ...] to pull. Default = the ALLOWLIST resolved from cal_config
    (personal_calendar + agent_calendar — whichever are on file), each named from the LIVE
    calendarList summary when available (falls back to the allowlist label). A single --calendar-id
    overrides for a targeted run."""
    if calendar_id:
        name = CALENDAR_ALLOWLIST.get(calendar_id, calendar_id)
        return [(calendar_id, name)]
    live = _list_calendars() or []
    live_names = {cid: cname for (cid, cname) in live}
    return [(cid, live_names.get(cid) or label) for cid, label in CALENDAR_ALLOWLIST.items()]


def sync(calendar_id=None, verbose=False, dry_run=False):
    """CT-3.5 (rebuilt): pull ONLY the ALLOWLISTED calendars, via a TWO-PASS model that fixes the 25k
    recurring-instance explosion — Pass R stores each recurring series as ONE master (its RRULE), Pass O
    stores true one-offs in a tight ±90d window. CRITICAL: accumulate the active set across ALL calendars
    AND BOTH passes, then ONE cold-sweep at the very end (a per-source sweep would cold-mark everything
    else; event ids are globally unique so the union sweep is safe)."""
    if not _SCHEMA_AVAILABLE:
        sys.stderr.write(
            f"[calendar-store-sync] HARD-STOP: item_schema unavailable ({_SCHEMA_ERROR})\n")
        return {"error": "schema_unavailable"}

    cals = _resolve_calendars(calendar_id)

    print(f"[calendar-store-sync] sync — {len(cals)} allowlisted calendar(s), two-pass → {STORE_ROOT}"
          + (" [DRY-RUN]" if dry_run else ""))

    counts = {"written": 0, "unchanged": 0, "cold": 0, "errors": 0, "calendars": 0,
              "masters": 0, "oneoffs": 0, "instances": 0}
    active_ids = set()          # UNION across ALL calendars + BOTH passes — the cold-sweep diffs against this ONCE
    any_flagged = False

    def _handle(event, cal_id, cal_name):
        """Process one event; update counts + the active-id union. Returns True if it was an error."""
        if not isinstance(event, dict):
            return False
        eid = event.get("id", "")
        if eid:
            active_ids.add(eid)
        action, ok = _process_event(event, cal_id, calendar_name=cal_name,
                                    verbose=verbose, dry_run=dry_run)
        if "UNCHANGED" in action:
            counts["unchanged"] += 1
        elif "WRITE" in action or "DRY" in action:
            counts["written"] += 1
        elif "SCHEMA-FAIL" in action or not ok:
            counts["errors"] += 1
            return True
        return False

    for (cal_id, cal_name) in cals:
        cal_pulled = False

        # ── PASS R: recurring series masters (keep only items WITH a recurrence rule) ──
        series, rcR = _pull_series(cal_id)
        if series is None:
            sys.stderr.write(f"[calendar-store-sync] {cal_name!r} Pass-R (series) pull failed — skipping calendar\n")
            counts["errors"] += 1
            continue
        cal_pulled = True
        if rcR == 1:
            any_flagged = True
        nM = 0
        for event in series:
            if isinstance(event, dict) and event.get("recurrence"):
                _handle(event, cal_id, cal_name)
                counts["masters"] += 1
                nM += 1

        # ── PASS O: true one-offs in the ±window (drop expanded recurring occurrences) ──
        oneoffs, rcO = _pull_oneoffs(cal_id)
        if oneoffs is None:
            sys.stderr.write(f"[calendar-store-sync] {cal_name!r} Pass-O (one-offs) pull failed — partial\n")
            counts["errors"] += 1
        else:
            if rcO == 1:
                any_flagged = True
            nO = 0
            nI = 0
            for event in oneoffs:
                if not isinstance(event, dict):
                    continue
                if event.get("recurrence"):
                    continue  # a master somehow surfacing here — Pass R owns it
                _handle(event, cal_id, cal_name)
                # CT-3.5b: a dated INSTANCE of a recurring series (has recurringEventId) is now STORED —
                # bounded to Pass O's ±window (ONEOFF_LOOKBACK/AHEAD), NOT dropped — so a windowed reader
                # (the cadence weekly/monthly review) sees real meeting dates. Google already did the RRULE
                # expansion; we simply stop discarding it. The window is what keeps this from re-exploding.
                if event.get("recurringEventId"):
                    counts["instances"] += 1
                    nI += 1
                else:
                    counts["oneoffs"] += 1
                    nO += 1

        if cal_pulled:
            counts["calendars"] += 1
        if verbose:
            print(f"  CAL   {cal_name[:40]} — masters={nM} one-offs={locals().get('nO', 0)} instances={locals().get('nI', 0)}")

    if any_flagged:
        print("[calendar-store-sync] WARNING: safe_calendar flagged injection patterns in ≥1 calendar; "
              "spans neutralized — proceeding with sanitized data")

    # ONE union cold-sweep across ALL calendars (never per-calendar).
    if not dry_run and active_ids:
        counts["cold"] = _cold_sweep(active_ids, dry_run=False, verbose=verbose)
        if counts["cold"]:
            print(f"[calendar-store-sync] cold-sweep: {counts['cold']} departed event(s) → "
                  "state=cold (KEPT on disk — never deleted)")
    elif dry_run:
        stored = _list_stored_paths()
        counts["cold"] = len(set(stored.keys()) - active_ids)

    print(f"[calendar-store-sync] sync DONE — calendars={counts['calendars']} "
          f"masters={counts['masters']} one-offs={counts['oneoffs']} instances={counts['instances']} "
          f"written={counts['written']} unchanged={counts['unchanged']} "
          f"cold={counts['cold']} errors={counts['errors']}")
    return counts


# ─────────────────────────────────────────────────────────────────────────────
# Self-tests — synthetic data, NO live Google pull required
# ─────────────────────────────────────────────────────────────────────────────

def _run_self_tests():
    """Run self-tests using synthetic calendar data. Returns (passed, failed)."""
    import shutil
    import tempfile
    import traceback
    from datetime import timedelta

    passed = failed = 0

    def ok(name):
        nonlocal passed
        passed += 1
        print(f"  PASS  {name}")

    def fail(name, reason):
        nonlocal failed
        failed += 1
        print(f"  FAIL  {name}: {reason}")

    now_utc = datetime.now(tz=timezone.utc)
    future_start = (now_utc + timedelta(days=3)).strftime("%Y-%m-%dT10:00:00Z")
    future_end = (now_utc + timedelta(days=3)).strftime("%Y-%m-%dT11:00:00Z")
    past_start = (now_utc - timedelta(days=5)).strftime("%Y-%m-%dT10:00:00Z")
    past_end = (now_utc - timedelta(days=5)).strftime("%Y-%m-%dT11:00:00Z")

    SYNTHETIC_EVENTS = [
        {   # future confirmed event → active
            "id": "test_event_001",
            "summary": "Weekly skydive debrief",
            "start": {"dateTime": future_start},
            "end": {"dateTime": future_end},
            "status": "confirmed",
            "updated": "2026-07-09T08:00:00.000Z",
            "location": "Dropzone HQ",
            "attendees": [
                {"email": "test.person@example.com"},
                {"email": "coach@dz.example.com"},
            ],
            "organizer": {"email": "test.person@example.com"},
        },
        {   # past event → cold
            "id": "test_event_002",
            "summary": "Client kickoff call",
            "start": {"dateTime": past_start},
            "end": {"dateTime": past_end},
            "status": "confirmed",
            "updated": "2026-07-04T09:00:00.000Z",
        },
        {   # cancelled event → cold
            "id": "test_event_003",
            "summary": "Cancelled: team lunch",
            "start": {"dateTime": future_start},
            "end": {"dateTime": future_end},
            "status": "cancelled",
            "updated": "2026-07-08T15:00:00.000Z",
        },
        {   # another future event for cold-sweep test
            "id": "test_event_004",
            "summary": "Investors call",
            "start": {"dateTime": future_start},
            "end": {"dateTime": future_end},
            "status": "confirmed",
            "updated": "2026-07-07T12:00:00.000Z",
        },
    ]

    tmp_store = tempfile.mkdtemp(prefix="cal_store_test_")
    import calendar_store_sync as _mod
    _original_store_root = _mod.STORE_ROOT
    _mod.STORE_ROOT = tmp_store

    try:
        # ── Test 1: future confirmed event → state=active ──
        try:
            ev = SYNTHETIC_EVENTS[0]
            action, ok_flag = _mod._process_event(ev, "test-cal@example.com")
            rec = _mod._load_record_by_event_id("test_event_001")
            assert ok_flag, f"process_event returned ok=False: {action}"
            assert rec is not None, "record not written"
            assert rec["state"] == "active", f"expected active, got {rec['state']}"
            assert rec["item_type"] == "calendar"
            assert rec["payload"]["summary"] == "Weekly skydive debrief"
            ok("future-event — confirmed future event written as state=active")
        except Exception as e:
            fail("future-event", f"{e}\n{traceback.format_exc()}")

        # ── Test 2: past event → state=cold ──
        try:
            ev = SYNTHETIC_EVENTS[1]
            action, ok_flag = _mod._process_event(ev, "test-cal@example.com")
            rec = _mod._load_record_by_event_id("test_event_002")
            assert ok_flag, f"process_event returned ok=False: {action}"
            assert rec is not None
            assert rec["state"] == "cold", f"expected cold, got {rec['state']}"
            ok("past-event — past event written as state=cold")
        except Exception as e:
            fail("past-event", f"{e}\n{traceback.format_exc()}")

        # ── Test 3: cancelled event → state=cold ──
        try:
            ev = SYNTHETIC_EVENTS[2]
            action, ok_flag = _mod._process_event(ev, "test-cal@example.com")
            rec = _mod._load_record_by_event_id("test_event_003")
            assert ok_flag, f"process_event returned ok=False: {action}"
            assert rec is not None
            assert rec["state"] == "cold", f"expected cold, got {rec['state']}"
            ok("cancelled-event — cancelled event written as state=cold")
        except Exception as e:
            fail("cancelled-event", f"{e}\n{traceback.format_exc()}")

        # ── Test 4: unchanged event (same updated timestamp) is skipped ──
        try:
            ev = SYNTHETIC_EVENTS[3]
            _mod._process_event(ev, "test-cal@example.com")  # write first
            action, ok_flag = _mod._process_event(ev, "test-cal@example.com")  # same updated
            assert "UNCHANGED" in action, f"expected UNCHANGED, got: {action}"
            ok("delta-skip — unchanged event skipped (same updated timestamp)")
        except Exception as e:
            fail("delta-skip", f"{e}\n{traceback.format_exc()}")

        # ── Test 5: event with new updated timestamp triggers re-write ──
        try:
            import copy
            ev_updated = copy.deepcopy(SYNTHETIC_EVENTS[3])
            ev_updated["updated"] = "2026-07-10T12:00:00.000Z"
            ev_updated["summary"] = "Investors call (RESCHEDULED)"
            action, ok_flag = _mod._process_event(ev_updated, "test-cal@example.com")
            assert "WRITE" in action, f"expected WRITE, got: {action}"
            rec = _mod._load_record_by_event_id("test_event_004")
            assert rec["payload"]["summary"] == "Investors call (RESCHEDULED)"
            ok("delta-write — changed event re-written on updated timestamp change")
        except Exception as e:
            fail("delta-write", f"{e}\n{traceback.format_exc()}")

        # ── Test 6: cold sweep marks departed event as cold, never deletes ──
        try:
            # Active ids = only event_001 and event_004; 002 and 003 are already cold from above
            # Write event_004 (it's active) then sweep without it
            active = {"test_event_001"}  # 004 is NOT in active set → should be cold-swept
            cold_count = _mod._cold_sweep(active, dry_run=False, verbose=False)
            rec004 = _mod._load_record_by_event_id("test_event_004")
            assert rec004 is not None, "swept record should still exist (never deleted)"
            assert rec004["state"] == "cold", f"expected state=cold after sweep, got {rec004['state']}"
            assert cold_count >= 1, f"expected at least 1 cold, got {cold_count}"
            ok("cold-sweep — departed event marked cold, file kept (never deleted)")
        except Exception as e:
            fail("cold-sweep", f"{e}\n{traceback.format_exc()}")

        # ── Test 7: reviving a cold event (re-appears as future with new updated) ──
        try:
            # test_event_002 was cold (past event); simulate it being rescheduled to the future
            rec = _mod._load_record_by_event_id("test_event_002")
            assert rec is not None and rec["state"] == "cold"
            import copy
            ev_rescheduled = copy.deepcopy(SYNTHETIC_EVENTS[1])
            ev_rescheduled["start"] = {"dateTime": future_start}
            ev_rescheduled["end"] = {"dateTime": future_end}
            ev_rescheduled["updated"] = "2026-07-10T11:00:00.000Z"  # new timestamp
            action, ok_flag = _mod._process_event(ev_rescheduled, "test-cal@example.com")
            rec_revived = _mod._load_record_by_event_id("test_event_002")
            assert rec_revived["state"] == "active", \
                f"expected active after revival, got {rec_revived['state']}"
            ok("cold-revival — cold event revived to active when rescheduled to future")
        except Exception as e:
            fail("cold-revival", f"{e}\n{traceback.format_exc()}")

        # ── Test 8: atomic write — no .tmp left behind ──
        try:
            ev = SYNTHETIC_EVENTS[0]
            _mod._process_event(ev, "test-cal@example.com")
            eid_path = _mod._event_path("test_event_001")
            tmp_path = eid_path + ".tmp"
            assert not os.path.exists(tmp_path), ".tmp file left behind after atomic write"
            ok("atomic-write — .tmp cleaned up after os.replace")
        except Exception as e:
            fail("atomic-write", f"{e}\n{traceback.format_exc()}")

        # ── Test 9: dry-run writes nothing to disk ──
        try:
            dry_store = tempfile.mkdtemp(prefix="cal_dry_")
            _mod.STORE_ROOT = dry_store
            import copy
            ev_dry = copy.deepcopy(SYNTHETIC_EVENTS[0])
            ev_dry["id"] = "dry_event_999"
            action, ok_flag = _mod._process_event(ev_dry, "test-cal@example.com", dry_run=True)
            assert "DRY" in action, f"expected DRY in action, got: {action}"
            dry_path = _mod._event_path("dry_event_999")
            assert not os.path.exists(dry_path), "dry-run should not write to disk"
            ok("dry-run — no disk writes in dry-run mode")
            _mod.STORE_ROOT = tmp_store
        except Exception as e:
            fail("dry-run", f"{e}\n{traceback.format_exc()}")
            _mod.STORE_ROOT = tmp_store

        # ── Test 10: validate_item_record gate rejects a bad calendar record ──
        try:
            from item_schema import validate_item_record as _v
            bad = {"item_id": "ev_x", "item_type": "calendar", "payload": {}}
            violations = _v(bad)
            assert len(violations) > 0, "expected violations"
            ok("schema-gate — malformed calendar record rejected")
        except Exception as e:
            fail("schema-gate", f"{e}\n{traceback.format_exc()}")

        # ── Test 10b: a recurring MASTER whose first occurrence is in the PAST stays state=active ──
        try:
            ev_master = {
                "id": "test_master_010b", "summary": "Weekly team sync", "status": "confirmed",
                "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=WE"],
                "start": {"dateTime": past_start}, "end": {"dateTime": past_end},  # first occ is PAST
                "updated": "2026-07-09T10:00:00Z",
            }
            action, ok_flag = _mod._process_event(ev_master, "test-cal@example.com")
            rec = _mod._load_record_by_event_id("test_master_010b")
            assert rec is not None and rec["state"] == "active", \
                f"expected recurring master active despite past first-occurrence, got {rec and rec['state']}"
            assert rec["payload"].get("is_recurring") is True, "master not flagged is_recurring"
            ok("recurring-master-active — series master w/ past first occurrence stays active (not cold)")
        except Exception as e:
            fail("recurring-master-active", f"{e}\n{traceback.format_exc()}")

        # ── Test 11: CT-3.5 multi-calendar UNION sweep — an event in calendar B is NOT false-cold when
        #    calendar A is also pulled; each event tagged with its calendar_name ──
        try:
            import tempfile as _tf11
            mc_store = _tf11.mkdtemp(prefix="cal_mc_")
            _mod.STORE_ROOT = mc_store
            _save_lc, _save_ps, _save_po, _save_al = \
                _mod._list_calendars, _mod._pull_series, _mod._pull_oneoffs, _mod.CALENDAR_ALLOWLIST
            _fut = (datetime.now(tz=timezone.utc) + __import__("datetime").timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
            _mod.CALENDAR_ALLOWLIST = {"work@example.com": "Work", "fam@example.com": "Family"}
            _mod._list_calendars = lambda: [("work@example.com", "Work"), ("fam@example.com", "Family")]
            # Pass R returns a recurring MASTER on the work calendar; Pass O returns a one-off on family.
            def _fake_series(cal_id, **kw):
                if cal_id == "work@example.com":
                    return ([{"id": "ev_series", "summary": "Weekly Standup", "status": "confirmed",
                              "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO"],
                              "start": {"dateTime": "2025-01-01T09:00:00Z"},
                              "end": {"dateTime": "2025-01-01T09:30:00Z"},
                              "updated": "2026-07-10T01:00:00Z"}], 0)
                return ([], 0)
            def _fake_oneoffs(cal_id, **kw):
                if cal_id == "fam@example.com":
                    return ([{"id": "ev_fam", "summary": "Dinner", "status": "confirmed",
                              "start": {"dateTime": _fut}, "end": {"dateTime": _fut},
                              "updated": "2026-07-10T02:00:00Z"},
                             # CT-3.5b: an expanded recurring occurrence (has recurringEventId) is now STORED
                             # as a dated INSTANCE (bounded to the ±window), not dropped:
                             {"id": "ev_series_inst", "summary": "Weekly Standup", "status": "confirmed",
                              "recurringEventId": "ev_series", "start": {"dateTime": _fut},
                              "end": {"dateTime": _fut}, "updated": "2026-07-10T03:00:00Z"}], 0)
                return ([], 0)
            _mod._pull_series = _fake_series
            _mod._pull_oneoffs = _fake_oneoffs
            c = _mod.sync(verbose=False, dry_run=False)
            rS = _mod._load_record_by_event_id("ev_series")
            rF = _mod._load_record_by_event_id("ev_fam")
            rInst = _mod._load_record_by_event_id("ev_series_inst")
            cond = (rS and rF and rInst and rS["state"] == "active" and rF["state"] == "active"
                    and rInst["state"] == "active"                     # CT-3.5b: instance STORED (future date → active)
                    and c["cold"] == 0 and c["calendars"] == 2
                    and c["masters"] == 1 and c["oneoffs"] == 1 and c["instances"] == 1
                    and rS["payload"].get("is_recurring") is True
                    and rS["payload"].get("recurrence") == ["RRULE:FREQ=WEEKLY;BYDAY=MO"]
                    # the instance is a concrete dated occurrence: NOT flagged recurring, linked to its master
                    and not rInst["payload"].get("is_recurring")
                    and rInst["payload"].get("recurring_event_id") == "ev_series"
                    and rS["payload"].get("calendar_name") == "Work"
                    and rF["payload"].get("calendar_name") == "Family")
            ok("ct35:multi-calendar-union — 2 cals, two-pass: master flagged, INSTANCE stored+linked (±window), no false-cold") \
                if cond else fail("ct35:multi-calendar-union",
                                  f"cold={c.get('cold')} cals={c.get('calendars')} "
                                  f"masters={c.get('masters')} oneoffs={c.get('oneoffs')} instances={c.get('instances')} "
                                  f"S={rS and rS['state']} F={rF and rF['state']} inst={rInst is not None} "
                                  f"inst_link={rInst and rInst['payload'].get('recurring_event_id')}")
            _mod._list_calendars, _mod._pull_series, _mod._pull_oneoffs, _mod.CALENDAR_ALLOWLIST = \
                _save_lc, _save_ps, _save_po, _save_al
            _mod.STORE_ROOT = tmp_store
            shutil.rmtree(mc_store, ignore_errors=True)
        except Exception as e:
            fail("ct35:multi-calendar-union", f"{e}\n{traceback.format_exc()}")
            _mod.STORE_ROOT = tmp_store

    finally:
        _mod.STORE_ROOT = _original_store_root
        shutil.rmtree(tmp_store, ignore_errors=True)

    print(f"\nCalendar store sync self-test results: {passed} passed, {failed} failed")
    return passed, failed


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="calendar_store_sync.py — durable Google Calendar item store writer (Phase G-3)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sync", action="store_true",
                       help="Pull calendar events and sync into the item store")
    group.add_argument("--self-test", action="store_true",
                       help="Run synthetic self-tests (no live Google pull)")
    parser.add_argument("--calendar-id", default=None,
                        help="A single calendar id for a TARGETED run. Default (omitted) = sync ALL of the "
                             "user's calendars (CT-3.5).")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print planned actions; write nothing to disk")
    args = parser.parse_args()

    if args.self_test:
        p, f = _run_self_tests()
        sys.exit(0 if f == 0 else 1)

    if args.sync:
        counts = sync(
            calendar_id=args.calendar_id,
            verbose=args.verbose,
            dry_run=args.dry_run,
        )
        if "error" in counts:
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()
