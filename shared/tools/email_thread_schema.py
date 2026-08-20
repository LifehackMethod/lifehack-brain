#!/usr/bin/env python3
"""email_thread_schema.py — the v2 FAITHFUL DE-DUPLICATED THREAD record contract (W0-1).

This module is the SCHEMA-FIRST gate for the Email Service write-side redesign. The store no
longer holds a lossy Haiku *summary* of the first + last message (v1); it holds a FAITHFUL,
MECHANICALLY DE-DUPLICATED THREAD: every unique message of the thread, kept in chronological
order, with quoted-reply stacking + signatures/disclaimers stripped, attachments as pointers.
Read the thread WELL, ONCE — never re-read it.

  ┌─ WHY "faithful", not "summary" ────────────────────────────────────────────────────────┐
  │ An LLM summary FABRICATES claims the source never made and COLLAPSES action items (names, │
  │ dates, dollar amounts) into vague mush — a lossy artifact is the wrong thing to OPERATE   │
  │ on. The /research convergence map (2026-07-10) confirmed the fix is mechanical de-dup:    │
  │ strip HTML→text · strip signatures/disclaimers · strip quoted replies · keep every real  │
  │ message. Cheap, lossless, deterministic, always faithful. NO LLM in the write path.       │
  └────────────────────────────────────────────────────────────────────────────────────────┘

THE CONTRACT THIS MODULE ENFORCES
  validate_thread_record(record) returns a list of violation strings (empty == valid). It is
  the single validator every write path (the janitor Wc-2, the backfill We-3) MUST pass before
  a record touches the store — mirroring the validate_contract() posture in
  email_summary_sync.py (return-a-list, never silently accept a malformed record).

  The load-bearing assertion is EVERY-MESSAGE-PRESENT: message_count (from Gmail thread
  metadata) must equal len(messages). A dropped message is the exact "the LLM cut sheet"
  failure this redesign exists to prevent — so it is a hard violation, not a warning.

Schema doc (human-facing): system/schemas/email-summary-schema.md (v2 section, drawn at We-4).
Plan: ~/.claude/plans/okay-but-for-whatever-enchanted-cherny.md → Phase W0.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Contract constants — the ONE place the v2 shape is declared.
# ─────────────────────────────────────────────────────────────────────────────

SCHEMA_V = 2

# Single-writer identity. The janitor stamps this; readers assert it (single-writer tripwire).
# Kept identical to the v1 writer_id so the read-side tripwire in load_digest() still matches.
# RENAMED 2026-08-15 (cal desk → planning desk): was "cal-daily-janitor". Any record written BEFORE
# this rename still carries the old id and will fail validate_thread_record() → served as
# STORE-TAMPERED. See LEGACY_WRITER_IDS below — old ids are accepted so existing records survive.
EXPECTED_WRITER_ID = "planning-daily-janitor"

# Writer ids this store accepted in the past. A record stamped with one of these is STILL VALID on
# read (it was written by the same single writer under its former name) — without this, the desk
# rename would orphan every already-synced record behind a STORE-TAMPERED flag. New writes always
# stamp EXPECTED_WRITER_ID; this list is read-side only and shrinks as records are re-synced.
LEGACY_WRITER_IDS = ("cal-daily-janitor",)

# A v2 record is perishable-by-design (a mirror of live mail) AND holds adversarial-derived text,
# so it is tier=snapshot / confidence=INFERRED — never CONFIRMED, even though the de-dup is lossless.
# (Faithful ≠ trusted: the CONTENT is still untrusted email; the read adapter re-scans it.)
EXPECTED_TIER = "snapshot"
EXPECTED_CONFIDENCE = "INFERRED"

# Lifecycle states (Wr — the store is DURABLE MEMORY, never hard-deleted):
#   active     — live in a tracked label; surfaced by default reads.
#   completed  — manually marked done/retired (fast path); kept, skipped by default reads, revivable.
#   cold       — left all tracked labels; kept indefinitely, skipped by default, REVIVED on a new message.
#   deep-cold  — very old cold record moved to a compressed/relocated cold tier; still retrievable, NEVER deleted.
# state is OPTIONAL on a record: a MISSING state is treated as "active" so the records written before Wr
# (schema_v:2 without a state field) still validate — additive, no schema_v bump.
VALID_STATES = ("active", "completed", "cold", "deep-cold")
DEFAULT_STATE = "active"

# item_type keeps the record OPEN to non-email item types later (Tasks/Calendar — Phase G, design-for-only).
# OPTIONAL; a MISSING item_type is treated as "email". No non-email code is built now.
DEFAULT_ITEM_TYPE = "email"


def record_state(record):
    """The effective lifecycle state of a record (missing → active). The one place readers/writers
    resolve state, so 'missing == active' is defined once."""
    return record.get("state") or DEFAULT_STATE

# Top-level keys every v2 record must carry. archived_at is intentionally NOT here (optional;
# absent = active — set only when a thread exits all tracked labels, exactly as in v1).
REQUIRED_TOP_FIELDS = (
    "thread_id",
    "subject",
    "labels",
    "messages",        # the faithful chronological list — the heart of v2
    "attachments",
    "first_seen",
    "last_message_id",
    "message_count",
    "last_synced",
    "provenance_tag",
    "flag",
    "writer_id",
    "tier",
    "confidence",
    "schema_v",
    "tracked_scope",
)

# Per-message keys. body may be "" (a pure-attachment message has no text) but the KEY must be
# present — an absent body key means the cleaner dropped content, which we must catch.
REQUIRED_MESSAGE_FIELDS = ("message_id", "from", "date", "body")

# Attachment pointer keys (metadata only — NEVER body bytes). Per the operator, 2026-07-10 (We-2):
# attachments are POINTER-ONLY — we do NOT download or extract attachment bodies (policy unchanged). A
# reader infers what an attachment is from its filename + the surrounding thread context. The
# `captured_text` field stays defined-but-unused so the schema is future-proof, but the write path
# never populates it.
REQUIRED_ATTACHMENT_FIELDS = ("filename", "mimeType", "message_id")


# ─────────────────────────────────────────────────────────────────────────────
# Builders — so the v2 shape is constructed in ONE place (used by the janitor Wc-2
# and the backfill We-3). Building through these + validating the result is the
# schema-first discipline: no write path hand-rolls the dict.
# ─────────────────────────────────────────────────────────────────────────────

def make_message(message_id, sender, date, body):
    """Build one cleaned, faithful message entry (quotes+sig already stripped by email_convert)."""
    return {
        "message_id": message_id or "",
        "from": sender or "",
        "date": date or "",
        "body": body if body is not None else "",
    }


def make_thread_record(
    *,
    thread_id,
    subject,
    labels,
    messages,
    attachments,
    first_seen,
    last_message_id,
    message_count,
    last_synced,
    provenance_tag,
    flag="OK",
    tracked_scope=None,
    archived_at=None,
    state=DEFAULT_STATE,
    item_type=DEFAULT_ITEM_TYPE,
):
    """Assemble a v2 thread record with the fixed metadata stamped. The caller is responsible
    for passing an ALREADY-CLEANED `messages` list (one per unique thread message); this builder
    does NOT clean — cleaning is email_convert.py's job (mechanical-only). validate_thread_record()
    must still be called on the result before any write (the builder does not self-validate, so a
    caller cannot forget the gate by leaning on the builder)."""
    record = {
        "thread_id": thread_id,
        "subject": subject or "",
        "labels": list(labels or []),
        "messages": list(messages or []),
        "attachments": list(attachments or []),
        "first_seen": first_seen,
        "last_message_id": last_message_id,
        "message_count": message_count,
        "last_synced": last_synced,
        "provenance_tag": provenance_tag,
        "flag": flag or "OK",
        "writer_id": EXPECTED_WRITER_ID,
        "tier": EXPECTED_TIER,
        "confidence": EXPECTED_CONFIDENCE,
        "schema_v": SCHEMA_V,
        "tracked_scope": list(tracked_scope) if tracked_scope is not None else [],
        "state": state or DEFAULT_STATE,
        "item_type": item_type or DEFAULT_ITEM_TYPE,
    }
    if archived_at:
        record["archived_at"] = archived_at
    return record


# ─────────────────────────────────────────────────────────────────────────────
# The validator — the schema-first gate.
# ─────────────────────────────────────────────────────────────────────────────

def validate_thread_record(record, override_writer_id=None):
    """Validate a v2 faithful-thread record. Returns a list of violation strings (empty == valid).

    Never raises on a bad record (returns violations); only a non-dict input is a structural error
    reported as a single violation. Collects ALL violations (not fail-fast) so a caller sees the
    whole picture in one pass — mirrors validate_contract() in email_summary_sync.py.

    The load-bearing checks:
      • every REQUIRED_TOP_FIELDS key present
      • messages is a non-empty list; each entry carries REQUIRED_MESSAGE_FIELDS
      • EVERY-MESSAGE-PRESENT: message_count == len(messages)   ← the anti-"cut sheet" guard
      • writer_id / tier / confidence / schema_v pinned to the contract constants
      • attachments is a list of metadata-only pointers (no captured *body bytes*)

    override_writer_id: substitute for EXPECTED_WRITER_ID (tests only).
    """
    violations = []
    expected_writer = override_writer_id if override_writer_id is not None else EXPECTED_WRITER_ID

    if not isinstance(record, dict):
        return [f"not_a_dict: record is {type(record).__name__}, expected dict"]

    # 1 — required top-level keys present
    for key in REQUIRED_TOP_FIELDS:
        if key not in record:
            violations.append(f"missing_field: '{key}' is required in a v2 thread record")

    # 2 — thread_id / last_message_id / provenance_tag must be non-empty strings
    for key in ("thread_id", "last_message_id", "provenance_tag"):
        val = record.get(key)
        if key in record and (not isinstance(val, str) or not val.strip()):
            violations.append(f"empty_field: '{key}' must be a non-empty string (got {val!r})")

    # 3 — pinned metadata (the single-writer / tier / confidence / schema tripwires)
    # A record stamped with a FORMER name of the same single writer (LEGACY_WRITER_IDS) is still
    # valid on read — the desk rename must not orphan already-synced records. An explicit
    # override_writer_id (tests) pins the accepted set exactly, with no legacy widening.
    _accepted = ({expected_writer} if override_writer_id is not None
                 else {expected_writer} | set(LEGACY_WRITER_IDS))
    if "writer_id" in record and record.get("writer_id") not in _accepted:
        violations.append(
            f"writer_mismatch: writer_id={record.get('writer_id')!r} != expected {expected_writer!r} "
            "(only the janitor may write the store)")
    if "tier" in record and record.get("tier") != EXPECTED_TIER:
        violations.append(f"tier: expected {EXPECTED_TIER!r}, got {record.get('tier')!r}")
    if "confidence" in record and record.get("confidence") != EXPECTED_CONFIDENCE:
        violations.append(
            f"confidence: expected {EXPECTED_CONFIDENCE!r} (adversarial-derived, never CONFIRMED), "
            f"got {record.get('confidence')!r}")
    if "schema_v" in record and record.get("schema_v") != SCHEMA_V:
        violations.append(f"schema_v: expected {SCHEMA_V}, got {record.get('schema_v')!r}")

    # 4 — labels / attachments / tracked_scope must be lists
    for key in ("labels", "attachments", "tracked_scope"):
        if key in record and not isinstance(record.get(key), list):
            violations.append(f"type: '{key}' must be a list (got {type(record.get(key)).__name__})")

    # 5 — flag must be a string, either OK or a REPLY-FLAGGED marker
    flag = record.get("flag")
    if "flag" in record:
        if not isinstance(flag, str) or not flag:
            violations.append(f"flag: must be a non-empty string (got {flag!r})")
        elif flag != "OK" and not flag.startswith("REPLY-FLAGGED"):
            violations.append(
                f"flag: must be 'OK' or start with 'REPLY-FLAGGED' (got {flag!r})")

    # 6 — messages: non-empty list of well-formed entries
    messages = record.get("messages")
    if "messages" in record:
        if not isinstance(messages, list):
            violations.append(f"messages: must be a list (got {type(messages).__name__})")
        elif not messages:
            violations.append("messages: empty — a thread has at least one message (nothing to store)")
        else:
            for i, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    violations.append(f"messages[{i}]: not a dict (got {type(msg).__name__})")
                    continue
                for mkey in REQUIRED_MESSAGE_FIELDS:
                    if mkey not in msg:
                        violations.append(f"messages[{i}]: missing '{mkey}'")
                # body key must be a string (may be "" for a pure-attachment message, but present)
                if "body" in msg and not isinstance(msg.get("body"), str):
                    violations.append(
                        f"messages[{i}].body: must be a string (got {type(msg.get('body')).__name__})")
                if "message_id" in msg and not (isinstance(msg.get("message_id"), str)
                                                and msg.get("message_id").strip()):
                    violations.append(f"messages[{i}].message_id: must be a non-empty string")

    # 7 — EVERY-MESSAGE-PRESENT (the anti-"cut sheet" fidelity guard). message_count is the
    # authoritative Gmail thread message count; the stored messages list must match it exactly.
    mc = record.get("message_count")
    if "message_count" in record and "messages" in record and isinstance(messages, list):
        if not isinstance(mc, int):
            violations.append(f"message_count: must be an int (got {type(mc).__name__})")
        elif mc != len(messages):
            violations.append(
                f"message_dropped: message_count={mc} but stored {len(messages)} message(s) — "
                "every unique message must be present (faithful de-dup drops QUOTES, never MESSAGES)")

    # 8 — attachments are metadata-only pointers (no decoded body bytes). captured_text (optional)
    # is fine; a 'data' key (decoded body) is a policy violation (bodies are FORBIDDEN — pointers only).
    atts = record.get("attachments")
    if isinstance(atts, list):
        for i, att in enumerate(atts):
            if not isinstance(att, dict):
                violations.append(f"attachments[{i}]: not a dict (got {type(att).__name__})")
                continue
            for akey in REQUIRED_ATTACHMENT_FIELDS:
                if akey not in att:
                    violations.append(f"attachments[{i}]: missing '{akey}'")
            if "data" in att:
                violations.append(
                    f"attachments[{i}]: carries a 'data' key — attachment BODIES are forbidden "
                    "(pointers + optional captured_text only)")

    # 9 — lifecycle state + item_type (both OPTIONAL — missing is valid, treated as active/email).
    # If PRESENT, state must be a known lifecycle value and item_type a string. This is what keeps
    # a pre-Wr record (no state key) valid while catching a garbage state on a new record.
    if "state" in record and record.get("state") not in VALID_STATES:
        violations.append(
            f"state: {record.get('state')!r} not in {VALID_STATES} (omit for the default 'active')")
    if "item_type" in record and not isinstance(record.get("item_type"), str):
        violations.append(f"item_type: must be a string (got {type(record.get('item_type')).__name__})")

    # 10 — reader_applied + verdict (both OPTIONAL — intake decode-and-judge reader fields).
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

    return violations


# ─────────────────────────────────────────────────────────────────────────────
# Synthetic self-tests (python3 email_thread_schema.py --self-test)
# ─────────────────────────────────────────────────────────────────────────────

def _good_record():
    """A minimal well-formed v2 record for the tests to mutate."""
    return make_thread_record(
        thread_id="t_abc",
        subject="Re: the $125k contract",
        labels=["INBOX", "Consulting"],
        messages=[
            make_message("m1", "Alex <alex@example.com>", "2026-07-06T09:00:00-04:00",
                         "Sending over the SOW for review."),
            make_message("m2", "Sam <sam@example.com>", "2026-07-07T10:00:00-04:00",
                         "Agreed to the $125k. Signing today."),
        ],
        attachments=[
            {"filename": "sow_v3.pdf", "mimeType": "application/pdf", "message_id": "m1",
             "size": 83211, "attachmentId": "a1"},
        ],
        first_seen="2026-07-06T09:00:00-04:00",
        last_message_id="m2",
        message_count=2,
        last_synced="2026-07-07T10:05:00-04:00",
        provenance_tag="email-summary/email/deadbeef",
        tracked_scope=["Consulting"],
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

    # 1 — a good record validates clean
    try:
        v = validate_thread_record(_good_record())
        ok("good-record — validates clean (0 violations)") if v == [] \
            else fail("good-record", f"unexpected violations: {v}")
    except Exception as e:
        fail("good-record", f"exception: {e}\n{traceback.format_exc()}")

    # 2 — a dropped message (message_count != len(messages)) is caught — THE key guard
    try:
        rec = _good_record()
        rec["message_count"] = 3  # claims 3, stores 2
        v = validate_thread_record(rec)
        ok("drop-guard — message_count!=len(messages) flagged") \
            if any("message_dropped" in x for x in v) \
            else fail("drop-guard", f"drop not caught: {v}")
    except Exception as e:
        fail("drop-guard", f"exception: {e}")

    # 3 — a missing required top field is caught
    try:
        rec = _good_record()
        del rec["provenance_tag"]
        v = validate_thread_record(rec)
        ok("missing-field — absent provenance_tag flagged") \
            if any("missing_field" in x and "provenance_tag" in x for x in v) \
            else fail("missing-field", f"not caught: {v}")
    except Exception as e:
        fail("missing-field", f"exception: {e}")

    # 4 — a foreign writer_id is caught (single-writer tripwire)
    try:
        rec = _good_record()
        rec["writer_id"] = "rogue-writer"
        v = validate_thread_record(rec)
        ok("writer-tripwire — foreign writer_id flagged") \
            if any("writer_mismatch" in x for x in v) \
            else fail("writer-tripwire", f"not caught: {v}")
    except Exception as e:
        fail("writer-tripwire", f"exception: {e}")

    # 4b — a LEGACY writer_id (the janitor's former name, pre cal→planning rename) still VALIDATES.
    # This is the guard that stops the desk rename orphaning every already-synced record behind a
    # STORE-TAMPERED flag on read. Regression-locks LEGACY_WRITER_IDS.
    try:
        rec = _good_record()
        rec["writer_id"] = "cal-daily-janitor"
        v = validate_thread_record(rec)
        ok("writer-legacy — pre-rename writer_id still accepted (no orphaned records)") \
            if not any("writer_mismatch" in x for x in v) \
            else fail("writer-legacy", f"legacy record rejected: {v}")
    except Exception as e:
        fail("writer-legacy", f"exception: {e}")

    # 5 — confidence CONFIRMED is rejected (must stay INFERRED)
    try:
        rec = _good_record()
        rec["confidence"] = "CONFIRMED"
        v = validate_thread_record(rec)
        ok("confidence-pin — CONFIRMED rejected (must be INFERRED)") \
            if any("confidence" in x for x in v) \
            else fail("confidence-pin", f"not caught: {v}")
    except Exception as e:
        fail("confidence-pin", f"exception: {e}")

    # 6 — a message missing a required subfield is caught
    try:
        rec = _good_record()
        del rec["messages"][1]["body"]
        v = validate_thread_record(rec)
        ok("message-subfield — missing message body key flagged") \
            if any("messages[1]" in x and "body" in x for x in v) \
            else fail("message-subfield", f"not caught: {v}")
    except Exception as e:
        fail("message-subfield", f"exception: {e}")

    # 7 — empty messages list is caught
    try:
        rec = _good_record()
        rec["messages"] = []
        rec["message_count"] = 0
        v = validate_thread_record(rec)
        ok("empty-messages — empty message list flagged") \
            if any("messages: empty" in x for x in v) \
            else fail("empty-messages", f"not caught: {v}")
    except Exception as e:
        fail("empty-messages", f"exception: {e}")

    # 8 — an attachment carrying decoded body bytes ('data') is caught (pointers only)
    try:
        rec = _good_record()
        rec["attachments"][0]["data"] = "base64bodybytes=="
        v = validate_thread_record(rec)
        ok("attachment-bodies — decoded 'data' key flagged (pointers only)") \
            if any("attachments[0]" in x and "data" in x for x in v) \
            else fail("attachment-bodies", f"not caught: {v}")
    except Exception as e:
        fail("attachment-bodies", f"exception: {e}")

    # 9 — a REPLY-FLAGGED flag is ALLOWED (a flagged-but-faithful record is valid)
    try:
        rec = _good_record()
        rec["flag"] = "REPLY-FLAGGED: suspicious instruction in body"
        v = validate_thread_record(rec)
        ok("flag-allowed — REPLY-FLAGGED record still validates") if v == [] \
            else fail("flag-allowed", f"unexpected violations: {v}")
    except Exception as e:
        fail("flag-allowed", f"exception: {e}")

    # 10 — a non-dict input is a structural violation, not a crash
    try:
        v = validate_thread_record("not a record")
        ok("non-dict — string input flagged, no crash") \
            if any("not_a_dict" in x for x in v) \
            else fail("non-dict", f"not caught: {v}")
    except Exception as e:
        fail("non-dict", f"exception: {e}")

    # 11 — default record carries state=active/item_type=email and validates
    try:
        rec = _good_record()
        good = rec.get("state") == "active" and rec.get("item_type") == "email" \
            and validate_thread_record(rec) == []
        ok("state-default — new record is state=active/item_type=email + validates") if good \
            else fail("state-default", f"state={rec.get('state')} item_type={rec.get('item_type')}")
    except Exception as e:
        fail("state-default", f"exception: {e}")

    # 12 — back-compat: a pre-Wr record with NO state key still validates (missing == active)
    try:
        rec = _good_record()
        del rec["state"]
        del rec["item_type"]
        v = validate_thread_record(rec)
        ok("state-backcompat — stateless (pre-Wr) record still validates") if v == [] \
            else fail("state-backcompat", f"unexpected: {v}")
        if record_state(rec) == "active":
            ok("state-resolve — missing state resolves to active")
        else:
            fail("state-resolve", f"got {record_state(rec)}")
    except Exception as e:
        fail("state-backcompat", f"exception: {e}")

    # 13 — a garbage state on a record is rejected; every valid state accepted
    try:
        rec = _good_record()
        rec["state"] = "banana"
        bad = any("state:" in x for x in validate_thread_record(rec))
        allok = all(validate_thread_record(dict(_good_record(), state=s)) == [] for s in VALID_STATES)
        ok("state-values — bad state rejected, all VALID_STATES accepted") if (bad and allok) \
            else fail("state-values", f"bad={bad} allok={allok}")
    except Exception as e:
        fail("state-values", f"exception: {e}")

    print(f"\nSchema self-test results: {passed} passed, {failed} failed")
    return passed, failed


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    import sys
    if "--self-test" in sys.argv:
        p, f = _run_self_tests()
        sys.exit(0 if f == 0 else 1)
    print("email_thread_schema.py — v2 faithful-thread record contract. "
          "Run with --self-test to validate.")
