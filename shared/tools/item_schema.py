#!/usr/bin/env python3
"""item_schema.py — generalized durable item record contract (Phase G).

Extends the email-store pattern (email_thread_schema.py) to cover Google Tasks and
Google Calendar events under a unified item record with a typed payload. The lifecycle
states, default state resolution, and validator shape are deliberately mirrored from
the email schema so the two stores share a single operating doctrine.

item_type ∈ {email, task, calendar}
  email   — the existing store (email_thread_schema.py is its own standalone contract;
             this schema is NOT used for the email store — it is purely for task/calendar)
  task    — one Google Task item (safe_tasks.py → tasks_store_sync.py)
  calendar — one Google Calendar event (safe_calendar.py → calendar_store_sync.py)

Lifecycle (identical to email_thread_schema VALID_STATES — imported, not redefined):
  active     — the item is current (task=needsAction; event=in the future or recent past)
  completed  — task.status==completed OR a past calendar event that was gracefully retired
  cold       — item no longer appears in the pull (vanished, cancelled) — NEVER deleted
  deep-cold  — very old cold record, eligible for relocation to the cold tier

validate_item_record(record) → list of violation strings (empty == valid).
Every write path MUST call this before touching the store.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Import lifecycle state from the email schema (single source of truth)
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from email_thread_schema import VALID_STATES, DEFAULT_STATE, record_state  # noqa: F401

# ─────────────────────────────────────────────────────────────────────────────
# Item schema constants
# ─────────────────────────────────────────────────────────────────────────────

ITEM_SCHEMA_V = 1

VALID_ITEM_TYPES = ("email", "task", "calendar", "task_list")

# Tier/confidence mirror email_thread_schema: these records are mechanical mirrors of
# live Google data (perishable, externally-derived) — snapshot/INFERRED exactly like email.
EXPECTED_TIER = "snapshot"
EXPECTED_CONFIDENCE = "INFERRED"

# Required top-level fields every item record must carry.
REQUIRED_TOP_FIELDS = (
    "item_id",       # the Google-side id (task id or event id)
    "item_type",     # "task" or "calendar"
    "state",         # lifecycle state (VALID_STATES)
    "payload",       # typed dict — task or calendar fields
    "first_seen",    # ISO-8601: when this record was first written
    "last_synced",   # ISO-8601: most recent write timestamp
    "provenance_tag", # opaque tag from the sanitizer/gate pass
    "writer_id",     # the janitor that wrote this (single-writer tripwire)
    "tier",          # "snapshot"
    "confidence",    # "INFERRED"
    "schema_v",      # ITEM_SCHEMA_V
    "source",        # e.g. "google-tasks" or "google-calendar"
)

# Payload field specs per item_type.
# Required = the key MUST be present (value may be "" or None for optional data).
# All payload values are strings, lists of strings, or None — no nested dicts except
# attendees (a list of email-address strings).
TASK_PAYLOAD_REQUIRED = (
    "id",       # Google Tasks task id (same as item_id — carried in payload for convenience)
    "title",    # task title (sanitized via safe_tasks --redact)
    "status",   # "needsAction" | "completed"
    "list_id",  # the tasklist id this task belongs to
    "source",   # "google-tasks"
)
TASK_PAYLOAD_OPTIONAL = ("notes", "due", "updated", "parent", "position", "list_title", "web_view_link")

CALENDAR_PAYLOAD_REQUIRED = (
    "id",       # Google Calendar event id (same as item_id)
    "summary",  # event title/summary (sanitized)
    "start",    # ISO-8601 start (dateTime or date)
    "end",      # ISO-8601 end
    "status",   # "confirmed" | "tentative" | "cancelled"
    "calendar_id",  # the calendarId this event came from
    "source",   # "google-calendar"
)
CALENDAR_PAYLOAD_OPTIONAL = ("description", "location", "attendees", "organizer", "updated",
                             "calendar_name", "recurrence", "is_recurring", "recurring_event_id")

# CT-3.5: a lightweight LIST MANIFEST record (item_type="task_list") so the store knows a Google Task list
# exists — its id, human name, and active count — even when the list is empty/sparse.
TASK_LIST_PAYLOAD_REQUIRED = (
    "id",            # the tasklist id
    "list_title",    # human-readable list name (USER-authored free text → reader scans it)
    "active_count",  # ACTIVE task count in this list at write time
    "source",        # "google-tasks"
)


# ─────────────────────────────────────────────────────────────────────────────
# Builders — assemble a record in ONE place; callers must still validate.
# ─────────────────────────────────────────────────────────────────────────────

def _iso_now():
    import time
    lt = time.localtime()
    off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off


def make_task_payload(
    *,
    task_id,
    title,
    status,
    list_id,
    notes=None,
    due=None,
    updated=None,
    parent=None,
    position=None,
    list_title=None,
    web_view_link=None,
):
    """Build the payload dict for a task item record.

    CT-3.5: `list_title` (the human-readable list name — USER-authored free text, reader SCANS it) +
    `web_view_link` (the task's Google URL) preserve list membership + a tappable pointer. `parent`/`position`
    preserve the subtask hierarchy + ordering within a list."""
    payload = {
        "id": task_id or "",
        "title": title or "",
        "status": status or "",
        "list_id": list_id or "",
        "source": "google-tasks",
    }
    if notes is not None:
        payload["notes"] = notes
    if due is not None:
        payload["due"] = due
    if updated is not None:
        payload["updated"] = updated
    if parent is not None:
        payload["parent"] = parent
    if position is not None:
        payload["position"] = position
    if list_title is not None:
        payload["list_title"] = list_title
    if web_view_link is not None:
        payload["web_view_link"] = web_view_link
    return payload


def make_task_list_payload(*, list_id, list_title, active_count):
    """CT-3.5: build the payload for a task_list MANIFEST record (one per Google Task list)."""
    return {
        "id": list_id or "",
        "list_title": list_title or "",
        "active_count": int(active_count or 0),
        "source": "google-tasks",
    }


def make_calendar_payload(
    *,
    event_id,
    summary,
    start,
    end,
    status,
    calendar_id,
    description=None,
    location=None,
    attendees=None,
    organizer=None,
    updated=None,
    calendar_name=None,
    recurrence=None,
    recurring_event_id=None,
):
    """Build the payload dict for a calendar item record. CT-3.5: `calendar_name` = the human-readable
    calendar name this event came from (so events can be grouped/separated by calendar, not just id).
    `recurrence` = the raw RRULE list for a recurring SERIES MASTER (machine-format, e.g.
    ["RRULE:FREQ=WEEKLY;BYDAY=TU"]) — its presence FLAGS the record as a recurring series, so we store ONE
    master per series instead of expanding every occurrence (the fix for the 25k-instance explosion).
    CT-3.5b: `recurring_event_id` = the master's event id, set ONLY on a concrete dated INSTANCE of a
    recurring series (Google-expanded, stored bounded to Pass O's ±window). An instance has NO `recurrence`
    (so is_recurring stays False — it IS a single dated occurrence) but links back to its master via this
    field, so a windowed reader can find real meeting dates without re-expanding RRULEs itself."""
    payload = {
        "id": event_id or "",
        "summary": summary or "",
        "start": start or "",
        "end": end or "",
        "status": status or "",
        "calendar_id": calendar_id or "",
        "source": "google-calendar",
    }
    if description is not None:
        payload["description"] = description
    if location is not None:
        payload["location"] = location
    if attendees is not None:
        payload["attendees"] = list(attendees)
    if organizer is not None:
        payload["organizer"] = organizer
    if updated is not None:
        payload["updated"] = updated
    if calendar_name is not None:
        payload["calendar_name"] = calendar_name
    if recurrence:
        payload["recurrence"] = list(recurrence)
        payload["is_recurring"] = True
    if recurring_event_id:
        payload["recurring_event_id"] = recurring_event_id
    return payload


def make_item_record(
    *,
    item_id,
    item_type,
    payload,
    writer_id,
    source,
    first_seen=None,
    last_synced=None,
    provenance_tag,
    state=DEFAULT_STATE,
    flag="OK",
):
    """Assemble a durable item record. Caller must call validate_item_record() before writing."""
    now = _iso_now()
    record = {
        "item_id": item_id or "",
        "item_type": item_type,
        "state": state or DEFAULT_STATE,
        "payload": dict(payload) if payload else {},
        "first_seen": first_seen or now,
        "last_synced": last_synced or now,
        "provenance_tag": provenance_tag or "",
        "writer_id": writer_id or "",
        "tier": EXPECTED_TIER,
        "confidence": EXPECTED_CONFIDENCE,
        "schema_v": ITEM_SCHEMA_V,
        "source": source or "",
        "flag": flag or "OK",
    }
    return record


# ─────────────────────────────────────────────────────────────────────────────
# Validator — the schema-first gate (mirrors validate_thread_record shape exactly)
# ─────────────────────────────────────────────────────────────────────────────

def validate_item_record(record):
    """Validate a durable item record. Returns a list of violation strings (empty == valid).

    Collects ALL violations (not fail-fast) so the caller sees the whole picture in one pass.
    Never raises on a bad record — a non-dict input is reported as a single violation.

    Checks:
      • non-dict input caught
      • every REQUIRED_TOP_FIELD present
      • item_type in VALID_ITEM_TYPES
      • state in VALID_STATES (required here — unlike email where state is optional for backcompat)
      • tier / confidence / schema_v pinned to constants
      • payload is a dict with the required keys for its item_type
      • flag is a string
    """
    violations = []

    if not isinstance(record, dict):
        return [f"not_a_dict: record is {type(record).__name__}, expected dict"]

    # 1 — required top-level keys
    for key in REQUIRED_TOP_FIELDS:
        if key not in record:
            violations.append(f"missing_field: '{key}' is required in an item record")

    # 2 — item_id / provenance_tag / writer_id must be non-empty strings
    for key in ("item_id", "provenance_tag", "writer_id", "source"):
        val = record.get(key)
        if key in record and (not isinstance(val, str) or not val.strip()):
            violations.append(f"empty_field: '{key}' must be a non-empty string (got {val!r})")

    # 3 — item_type must be a known type
    itype = record.get("item_type")
    if "item_type" in record:
        if itype not in VALID_ITEM_TYPES:
            violations.append(
                f"item_type: {itype!r} not in {VALID_ITEM_TYPES}")

    # 4 — state must be a known lifecycle value (required in item records)
    if "state" in record and record.get("state") not in VALID_STATES:
        violations.append(
            f"state: {record.get('state')!r} not in {VALID_STATES}")

    # 5 — pinned metadata
    if "tier" in record and record.get("tier") != EXPECTED_TIER:
        violations.append(f"tier: expected {EXPECTED_TIER!r}, got {record.get('tier')!r}")
    if "confidence" in record and record.get("confidence") != EXPECTED_CONFIDENCE:
        violations.append(
            f"confidence: expected {EXPECTED_CONFIDENCE!r} (externally-derived, never CONFIRMED), "
            f"got {record.get('confidence')!r}")
    if "schema_v" in record and record.get("schema_v") != ITEM_SCHEMA_V:
        violations.append(f"schema_v: expected {ITEM_SCHEMA_V}, got {record.get('schema_v')!r}")

    # 6 — flag must be a non-empty string
    flag = record.get("flag")
    if "flag" in record:
        if not isinstance(flag, str) or not flag:
            violations.append(f"flag: must be a non-empty string (got {flag!r})")

    # 6b — reader_applied + verdict (both OPTIONAL — intake decode-and-judge reader fields).
    # reader_applied: bool (present only when the reader ran). verdict: one of the three allowed
    # values (present only when reader_applied is True). Neither field is required; their absence
    # is always valid so every existing record continues to validate unchanged.
    _VALID_VERDICTS = ("REAL-ATTACK", "BENIGN", "NONE")
    if "reader_applied" in record and not isinstance(record.get("reader_applied"), bool):
        violations.append(
            f"reader_applied: must be a bool (got {type(record.get('reader_applied')).__name__})")
    if "verdict" in record:
        v_val = record.get("verdict")
        if v_val not in _VALID_VERDICTS:
            violations.append(
                f"verdict: {v_val!r} not in {_VALID_VERDICTS}")

    # 7 — payload: must be a dict with the required keys for this item_type
    payload = record.get("payload")
    if "payload" in record:
        if not isinstance(payload, dict):
            violations.append(f"payload: must be a dict (got {type(payload).__name__})")
        else:
            # Check required payload fields for the declared item_type
            if itype == "task":
                for pkey in TASK_PAYLOAD_REQUIRED:
                    if pkey not in payload:
                        violations.append(f"payload.{pkey}: required for item_type=task")
            elif itype == "calendar":
                for pkey in CALENDAR_PAYLOAD_REQUIRED:
                    if pkey not in payload:
                        violations.append(f"payload.{pkey}: required for item_type=calendar")
            elif itype == "task_list":   # CT-3.5 list manifest
                for pkey in TASK_LIST_PAYLOAD_REQUIRED:
                    if pkey not in payload:
                        violations.append(f"payload.{pkey}: required for item_type=task_list")
            # email item_type is not built here (email_thread_schema is the contract for email)
            # but we accept it without payload field-level checks to keep the union clean.

    return violations


# ─────────────────────────────────────────────────────────────────────────────
# Self-tests (python3 item_schema.py --self-test)
# ─────────────────────────────────────────────────────────────────────────────

def _good_task_record():
    return make_item_record(
        item_id="task_abc123",
        item_type="task",
        payload=make_task_payload(
            task_id="task_abc123",
            title="Review the SOW for the $125k contract",
            status="needsAction",
            list_id="TESTLIST0000000000000",
            notes="Due before the client call on Friday.",
            due="2026-07-11T00:00:00.000Z",
            updated="2026-07-09T10:00:00.000Z",
        ),
        writer_id="tasks-store-sync",
        source="google-tasks",
        provenance_tag="item-store/task/task_abc123/abc123deadbeef",
    )


def _good_calendar_record():
    return make_item_record(
        item_id="cal_event_xyz789",
        item_type="calendar",
        payload=make_calendar_payload(
            event_id="cal_event_xyz789",
            summary="Weekly skydive debrief",
            start="2026-07-11T09:00:00-04:00",
            end="2026-07-11T10:00:00-04:00",
            status="confirmed",
            calendar_id="test.person@example.com",
            location="Dropzone HQ",
            attendees=["test.person@example.com", "coach@dz.example.com"],
            organizer="test.person@example.com",
            updated="2026-07-09T08:00:00.000Z",
        ),
        writer_id="calendar-store-sync",
        source="google-calendar",
        provenance_tag="item-store/calendar/cal_event_xyz789/deadbeef1234",
    )


def _run_self_tests():
    import traceback
    passed = failed = 0

    def ok(name):
        nonlocal passed
        passed += 1
        print(f"  PASS  {name}")

    def fail(name, reason):
        nonlocal failed
        failed += 1
        print(f"  FAIL  {name}: {reason}")

    # 1 — a valid task record validates clean
    try:
        v = validate_item_record(_good_task_record())
        ok("task-record-valid — validates clean (0 violations)") if v == [] \
            else fail("task-record-valid", f"unexpected violations: {v}")
    except Exception as e:
        fail("task-record-valid", f"exception: {e}\n{traceback.format_exc()}")

    # 2 — a valid calendar record validates clean
    try:
        v = validate_item_record(_good_calendar_record())
        ok("cal-record-valid — validates clean (0 violations)") if v == [] \
            else fail("cal-record-valid", f"unexpected violations: {v}")
    except Exception as e:
        fail("cal-record-valid", f"exception: {e}\n{traceback.format_exc()}")

    # 3 — a malformed record (missing required top field) is rejected
    try:
        rec = _good_task_record()
        del rec["provenance_tag"]
        v = validate_item_record(rec)
        ok("missing-top-field — absent provenance_tag flagged") \
            if any("missing_field" in x and "provenance_tag" in x for x in v) \
            else fail("missing-top-field", f"not caught: {v}")
    except Exception as e:
        fail("missing-top-field", f"exception: {e}")

    # 4 — an unknown item_type is rejected
    try:
        rec = _good_task_record()
        rec["item_type"] = "asana-task"  # not yet a valid type
        v = validate_item_record(rec)
        ok("bad-item-type — unknown item_type rejected") \
            if any("item_type" in x for x in v) \
            else fail("bad-item-type", f"not caught: {v}")
    except Exception as e:
        fail("bad-item-type", f"exception: {e}")

    # 5 — a bad state is rejected
    try:
        rec = _good_task_record()
        rec["state"] = "banana"
        v = validate_item_record(rec)
        ok("bad-state — invalid state rejected") \
            if any("state:" in x for x in v) \
            else fail("bad-state", f"not caught: {v}")
    except Exception as e:
        fail("bad-state", f"exception: {e}")

    # 6 — all VALID_STATES accepted on a task record
    try:
        all_ok = all(
            validate_item_record(dict(_good_task_record(), state=s)) == []
            for s in VALID_STATES
        )
        ok("all-states-valid — all VALID_STATES accepted") if all_ok \
            else fail("all-states-valid", "one or more valid states rejected")
    except Exception as e:
        fail("all-states-valid", f"exception: {e}")

    # 7 — non-dict input caught without crash
    try:
        v = validate_item_record("not a record")
        ok("non-dict — string input flagged, no crash") \
            if any("not_a_dict" in x for x in v) \
            else fail("non-dict", f"not caught: {v}")
    except Exception as e:
        fail("non-dict", f"exception: {e}")

    # 8 — wrong tier is caught
    try:
        rec = _good_task_record()
        rec["tier"] = "confirmed"
        v = validate_item_record(rec)
        ok("tier-pin — wrong tier rejected") \
            if any("tier:" in x for x in v) \
            else fail("tier-pin", f"not caught: {v}")
    except Exception as e:
        fail("tier-pin", f"exception: {e}")

    # 9 — CONFIRMED confidence is rejected (must stay INFERRED)
    try:
        rec = _good_task_record()
        rec["confidence"] = "CONFIRMED"
        v = validate_item_record(rec)
        ok("confidence-pin — CONFIRMED rejected (must be INFERRED)") \
            if any("confidence:" in x for x in v) \
            else fail("confidence-pin", f"not caught: {v}")
    except Exception as e:
        fail("confidence-pin", f"exception: {e}")

    # 10 — task missing a required payload field is caught
    try:
        rec = _good_task_record()
        del rec["payload"]["status"]
        v = validate_item_record(rec)
        ok("task-payload-field — missing payload.status flagged") \
            if any("payload.status" in x for x in v) \
            else fail("task-payload-field", f"not caught: {v}")
    except Exception as e:
        fail("task-payload-field", f"exception: {e}")

    # 11 — calendar record missing a required payload field is caught
    try:
        rec = _good_calendar_record()
        del rec["payload"]["start"]
        v = validate_item_record(rec)
        ok("cal-payload-field — missing payload.start flagged") \
            if any("payload.start" in x for x in v) \
            else fail("cal-payload-field", f"not caught: {v}")
    except Exception as e:
        fail("cal-payload-field", f"exception: {e}")

    # 12 — payload being a non-dict is caught
    try:
        rec = _good_task_record()
        rec["payload"] = "not a dict"
        v = validate_item_record(rec)
        ok("payload-type — non-dict payload flagged") \
            if any("payload: must be a dict" in x for x in v) \
            else fail("payload-type", f"not caught: {v}")
    except Exception as e:
        fail("payload-type", f"exception: {e}")

    # 12b — CT-3.5: new task fields (list_title, web_view_link) + calendar_name + a task_list manifest all validate
    try:
        trec = make_item_record(
            item_id="L1__task_abc", item_type="task",
            payload=make_task_payload(task_id="task_abc", title="Sub-task under a parent", status="needsAction",
                                      list_id="L1", list_title="[ Consulting / Coaching ]",
                                      web_view_link="https://tasks.google.com/task/abc", parent="task_parent",
                                      position="00000000000000000001"),
            writer_id="tasks-store-sync", source="google-tasks",
            provenance_tag="item-store/task/L1__task_abc/abcd1234")
        crec = make_item_record(
            item_id="ev1", item_type="calendar",
            payload=make_calendar_payload(event_id="ev1", summary="s", start="2026-07-11T09:00:00-04:00",
                                          end="2026-07-11T10:00:00-04:00", status="confirmed",
                                          calendar_id="work@example.com", calendar_name="Work"),
            writer_id="calendar-store-sync", source="google-calendar",
            provenance_tag="item-store/calendar/ev1/abcd1234")
        mrec = make_item_record(
            item_id="L1", item_type="task_list",
            payload=make_task_list_payload(list_id="L1", list_title="[ Consulting / Coaching ]", active_count=7),
            writer_id="tasks-store-sync", source="google-tasks",
            provenance_tag="item-store/task_list/L1/abcd1234")
        vt, vc, vm = validate_item_record(trec), validate_item_record(crec), validate_item_record(mrec)
        okp = (trec["payload"].get("list_title") and trec["payload"].get("web_view_link")
               and trec["payload"].get("parent") and crec["payload"].get("calendar_name"))
        if vt == [] and vc == [] and vm == [] and okp:
            ok("ct35:new-fields — task list_title/web_view_link/parent + calendar_name + task_list manifest all validate")
        else:
            fail("ct35:new-fields", f"task={vt} cal={vc} manifest={vm} payload_ok={bool(okp)}")
    except Exception as e:
        fail("ct35:new-fields", f"exception: {e}\n{traceback.format_exc()}")

    # 12c — CT-3.5: a task_list manifest MISSING a required field is caught
    try:
        bad = make_item_record(item_id="L2", item_type="task_list",
                               payload={"id": "L2", "source": "google-tasks"},  # missing list_title + active_count
                               writer_id="tasks-store-sync", source="google-tasks",
                               provenance_tag="item-store/task_list/L2/x")
        v = validate_item_record(bad)
        ok("ct35:manifest-required — missing list_title/active_count flagged") \
            if any("payload.list_title" in x for x in v) and any("payload.active_count" in x for x in v) \
            else fail("ct35:manifest-required", f"not caught: {v}")
    except Exception as e:
        fail("ct35:manifest-required", f"exception: {e}")

    # 13 — VALID_STATES imported from email_thread_schema (not redefined here)
    try:
        from email_thread_schema import VALID_STATES as _vs
        ok("import-valid-states — VALID_STATES imported from email_thread_schema") \
            if VALID_STATES is _vs \
            else fail("import-valid-states", f"different object: {VALID_STATES} vs {_vs}")
    except Exception as e:
        fail("import-valid-states", f"exception: {e}")

    print(f"\nItem schema self-test results: {passed} passed, {failed} failed")
    return passed, failed


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        p, f = _run_self_tests()
        sys.exit(0 if f == 0 else 1)
    print("item_schema.py — generalized durable item record contract (Phase G). "
          "Run with --self-test to validate.")
