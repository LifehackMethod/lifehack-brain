"""intake_backfill.py — One-time backfill: re-scrub all already-stored records with the
intake reader/judge, stamping reader_applied + verdict + storing cleared bodies.

Mirrors the EXACT logic each live writer uses:
  - EMAIL: per-message body scan/judge, agg verdict, reader_applied=all-judged
  - TASKS: free_text join (title\\nnotes), split cleared back on first \\n
  - CALENDAR: free_text join (summary\\ndescription\\nlocation), split cleared on \\n up to 3 parts

Records where "reader_applied" is ALREADY PRESENT are skipped (live writer stamped them).

CLI:
    python3 intake_backfill.py [--dry-run] [--limit N] [--store email|tasks|calendar|all]

PARALLELISM: ThreadPoolExecutor(max_workers=4) over records that HAVE findings (need LLM).
The no-findings majority is the instant inline path.

Supervised-session tool — not wired to a scheduler (none exists in this repo). Run by hand after
connecting Gmail/Tasks/Calendar for the first time, or whenever a reader/judge upgrade should be
re-applied to records written before it landed.
"""

import argparse
import concurrent.futures
import glob
import json
import os
import sys

# ---------------------------------------------------------------------------
# Path bootstrap — same pattern as the live sync modules
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_CODE_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
_SYSTEM_TOOLS = os.path.join(_CODE_ROOT, "system", "tools")

# shared/tools already on path (we are there), add system/tools for safe_input
if _SYSTEM_TOOLS not in sys.path:
    sys.path.insert(0, _SYSTEM_TOOLS)
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

# The data root, through the one resolver (shared/brain_root.py) — never a hardcoded personal Drive
# path. NOT-SET degrades DRIVE to "" rather than guessing; the existing os.path.isdir checks below
# then simply report each store dir as "not found" (mirrors calendar_store_sync.py / tasks_store_sync.py).
if os.path.join(_CODE_ROOT, "shared") not in sys.path:
    sys.path.insert(0, os.path.join(_CODE_ROOT, "shared"))
import brain_root                                                            # noqa: E402
_BR_SOURCE, _BR_PATH = brain_root.resolve_brain_root()
DRIVE = _BR_PATH or ""

# ---------------------------------------------------------------------------
# Import live helpers — same imports the live writers use
# ---------------------------------------------------------------------------
try:
    from intake_reader import run_intake_judge as _run_intake_judge
    _READER_AVAILABLE = True
except ImportError as e:
    sys.stderr.write(f"[intake-backfill] FATAL: intake_reader unavailable: {e}\n")
    sys.exit(1)

try:
    from safe_input import scan_for_injection as _scan_for_injection
    _SCAN_AVAILABLE = True
except ImportError as e:
    sys.stderr.write(f"[intake-backfill] FATAL: safe_input unavailable: {e}\n")
    sys.exit(1)

# Email schema validator
try:
    from email_thread_schema import validate_thread_record as _validate_thread
    _EMAIL_SCHEMA_OK = True
except ImportError as e:
    sys.stderr.write(f"[intake-backfill] WARNING: email_thread_schema unavailable: {e}\n")
    _validate_thread = None
    _EMAIL_SCHEMA_OK = False

# Item schema validator
try:
    from item_schema import validate_item_record as _validate_item
    _ITEM_SCHEMA_OK = True
except ImportError as e:
    sys.stderr.write(f"[intake-backfill] WARNING: item_schema unavailable: {e}\n")
    _validate_item = None
    _ITEM_SCHEMA_OK = False

# ---------------------------------------------------------------------------
# Store paths — match the live writer constants exactly
# ---------------------------------------------------------------------------
THREADS_V2_DIR = os.path.join(DRIVE, "state", "email-summary", "threads-v2")
TASKS_STORE_ROOT = os.path.join(DRIVE, "state", "item-store", "tasks")
CALENDAR_STORE_ROOT = os.path.join(DRIVE, "state", "item-store", "calendar")

# Verdict rank — same ordering as the live writers
_VERDICT_RANK = {"NONE": 0, "BENIGN": 1, "REAL-ATTACK": 2}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_atomic(path, data):
    """Write JSON atomically via .tmp + os.replace — same pattern as all live writers."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# EMAIL store backfill
# ---------------------------------------------------------------------------

def _backfill_email_record(path, dry_run):
    """Process a single thread-v2 record. Returns (status_str, had_findings).
    Mirrors email_summary_sync.py process_thread_v2's per-message judge loop exactly.
    """
    try:
        record = _load_json(path)
    except Exception as e:
        return f"LOAD-ERR  {os.path.basename(path)}: {e}", False

    thread_id = os.path.basename(path)[:-5]

    # Skip if already stamped by the live writer
    if record.get("reader_applied") is True:
        return f"SKIP(stamped) {thread_id[:20]}", False

    messages = record.get("messages", [])
    if not messages:
        # No messages — stamp as reader_applied=True, verdict=None (nothing to scan)
        record["reader_applied"] = True
        if not dry_run:
            if _validate_thread:
                violations = _validate_thread(record)
                if violations:
                    return f"SCHEMA-FAIL {thread_id[:20]}: {violations[0][:60]}", False
            _write_atomic(path, record)
        return f"CLEAN(nomsg) {thread_id[:20]}", False

    # Per-message scan — mirrors the live writer loop exactly
    _all_judged = True
    _agg_verdict = "NONE"
    _needs_llm = False
    cleared_bodies = []
    findings_per_msg = []

    for msg in messages:
        body = msg.get("body", "")
        try:
            findings = _scan_for_injection(body) or []
        except Exception:
            findings = []
        findings_per_msg.append(findings)
        if findings:
            _needs_llm = True

    # Cheap path: no findings in any message — skip LLM, stamp inline
    if not _needs_llm:
        for msg in messages:
            cleared_bodies.append(msg.get("body", ""))
        _reader_applied = True
        _verdict = None
        # Write the record with stamps (bodies unchanged)
        record["reader_applied"] = _reader_applied
        if _verdict is not None:
            record["verdict"] = _verdict
        if not dry_run:
            if _validate_thread:
                violations = _validate_thread(record)
                if violations:
                    return f"SCHEMA-FAIL {thread_id[:20]}: {violations[0][:60]}", False
            _write_atomic(path, record)
        return f"CLEAN {thread_id[:20]}", False

    # Has findings — dry-run: skip LLM, just count
    if dry_run:
        return f"WOULD-JUDGE {thread_id[:20]}", True

    # Has findings — run LLM per message (called from the thread pool)
    for i, msg in enumerate(messages):
        body = msg.get("body", "")
        findings = findings_per_msg[i]
        if not findings:
            cleared_bodies.append(body)
            continue
        try:
            result = _run_intake_judge(body, findings)
            cleared_bodies.append(result["cleared_text"])
            msg_v = result.get("verdict") or "NONE"
            if _VERDICT_RANK.get(msg_v, 0) > _VERDICT_RANK.get(_agg_verdict, 0):
                _agg_verdict = msg_v
            if not result.get("reader_applied", False):
                _all_judged = False
        except Exception:
            cleared_bodies.append(body)
            _all_judged = False

    _reader_applied = _all_judged
    _verdict = _agg_verdict if _agg_verdict != "NONE" else None

    # Splice cleared bodies back into the record messages
    updated_messages = []
    for i, msg in enumerate(messages):
        updated_msg = dict(msg)
        updated_msg["body"] = cleared_bodies[i]
        updated_messages.append(updated_msg)
    record["messages"] = updated_messages
    record["reader_applied"] = _reader_applied
    if _verdict is not None:
        record["verdict"] = _verdict

    if not dry_run:
        if _validate_thread:
            violations = _validate_thread(record)
            if violations:
                return f"SCHEMA-FAIL {thread_id[:20]}: {violations[0][:60]}", True
        _write_atomic(path, record)
    return f"JUDGED {thread_id[:20]} verdict={_verdict or 'NONE'}", True


def backfill_email(dry_run, limit):
    """Backfill the email threads-v2 store."""
    print(f"\n[EMAIL] Scanning {THREADS_V2_DIR} ...")
    counts = {"scanned": 0, "already_stamped": 0, "clean_no_llm": 0,
              "judged": 0, "skipped_error": 0}

    if not os.path.isdir(THREADS_V2_DIR):
        print(f"[EMAIL] Store dir not found: {THREADS_V2_DIR}")
        return counts

    # Collect all paths; filter already-stamped in a quick pre-pass
    all_paths = [
        os.path.join(THREADS_V2_DIR, fn)
        for fn in os.listdir(THREADS_V2_DIR)
        if fn.endswith(".json")
    ]

    paths_to_process = []
    for path in all_paths:
        counts["scanned"] += 1
        try:
            rec = _load_json(path)
            if rec.get("reader_applied") is True:
                counts["already_stamped"] += 1
                continue
        except Exception:
            counts["skipped_error"] += 1
            continue
        paths_to_process.append(path)

    if limit is not None:
        paths_to_process = paths_to_process[:limit]

    print(f"[EMAIL] {counts['scanned']} total, {counts['already_stamped']} already stamped, "
          f"{len(paths_to_process)} to process")

    # Split: instant (no findings) vs needs-LLM. We discover at process time.
    # Use ThreadPoolExecutor; those without findings return instantly.
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_backfill_email_record, p, dry_run): p
                   for p in paths_to_process}
        for future in concurrent.futures.as_completed(futures):
            try:
                status, had_findings = future.result()
            except Exception as e:
                status = f"EXC: {e}"
                had_findings = False
            if "SKIP(stamped)" in status:
                counts["already_stamped"] += 1
            elif "WOULD-JUDGE" in status:
                counts["judged"] += 1  # would-judge = counts as needing LLM
            elif "CLEAN" in status or "SKIP" in status:
                counts["clean_no_llm"] += 1
            elif "JUDGED" in status:
                counts["judged"] += 1
            elif "SCHEMA-FAIL" in status or "ERR" in status or "EXC" in status:
                counts["skipped_error"] += 1
                print(f"  [EMAIL] {status}")

    print(f"[EMAIL] Done. scanned={counts['scanned']} already_stamped={counts['already_stamped']} "
          f"clean_no_llm={counts['clean_no_llm']} judged={counts['judged']} "
          f"skipped_error={counts['skipped_error']}")
    return counts


# ---------------------------------------------------------------------------
# TASKS store backfill
# ---------------------------------------------------------------------------

def _backfill_task_record(path, dry_run):
    """Process a single task record.
    Mirrors tasks_store_sync.py's reader/judge splice exactly (title\\nnotes join, split on
    first \\n)."""
    try:
        record = _load_json(path)
    except Exception as e:
        return f"LOAD-ERR  {os.path.basename(path)}: {e}", False

    item_id = record.get("item_id", os.path.basename(path)[:-5])

    if record.get("reader_applied") is True:
        return f"SKIP(stamped) {item_id[:24]}", False

    payload = record.get("payload", {})
    raw_title = payload.get("title") or ""
    raw_notes = payload.get("notes")
    free_text = "\n".join(filter(None, [raw_title, raw_notes or ""]))

    reader_applied = None
    verdict = None
    cleared_title = raw_title
    cleared_notes = raw_notes  # preserve None vs ""

    if free_text:
        try:
            findings = _scan_for_injection(free_text) or []
        except Exception:
            findings = []

        had_findings = bool(findings)
        # Dry-run: skip LLM, just count
        if dry_run and had_findings:
            return f"WOULD-JUDGE {item_id[:24]}", True
        if dry_run:
            return f"CLEAN(dry) {item_id[:24]}", False

        judge_result = _run_intake_judge(free_text, findings)
        reader_applied = judge_result.get("reader_applied")
        verdict = judge_result.get("verdict")
        cleared = judge_result.get("cleared_text") or free_text
        cleared_lines = cleared.split("\n", 1)
        cleared_title = cleared_lines[0]
        if raw_notes is not None:
            cleared_notes = cleared_lines[1] if len(cleared_lines) > 1 else ""
    else:
        # No free text — still stamp reader_applied=True (nothing to scan)
        reader_applied = True
        verdict = "NONE"
        had_findings = False
        if dry_run:
            return f"CLEAN(dry) {item_id[:24]}", False

    # Splice cleared text back into payload
    record["payload"]["title"] = cleared_title
    if raw_notes is not None:
        record["payload"]["notes"] = cleared_notes

    if reader_applied is not None:
        record["reader_applied"] = reader_applied
    if verdict is not None and verdict != "NONE":
        record["verdict"] = verdict

    if not dry_run:
        if _validate_item:
            violations = _validate_item(record)
            if violations:
                return f"SCHEMA-FAIL {item_id[:24]}: {violations[0][:60]}", had_findings
        _write_atomic(path, record)

    verdict_str = verdict or "NONE"
    if had_findings:
        return f"JUDGED {item_id[:24]} verdict={verdict_str}", True
    return f"CLEAN {item_id[:24]}", False


def backfill_tasks(dry_run, limit):
    """Backfill the tasks item store."""
    print(f"\n[TASKS] Scanning {TASKS_STORE_ROOT} ...")
    counts = {"scanned": 0, "already_stamped": 0, "clean_no_llm": 0,
              "judged": 0, "skipped_error": 0}

    if not os.path.isdir(TASKS_STORE_ROOT):
        print(f"[TASKS] Store dir not found: {TASKS_STORE_ROOT}")
        return counts

    all_paths = [
        os.path.join(TASKS_STORE_ROOT, fn)
        for fn in os.listdir(TASKS_STORE_ROOT)
        if fn.endswith(".json")
    ]

    paths_to_process = []
    for path in all_paths:
        counts["scanned"] += 1
        try:
            rec = _load_json(path)
            if rec.get("reader_applied") is True:
                counts["already_stamped"] += 1
                continue
        except Exception:
            counts["skipped_error"] += 1
            continue
        paths_to_process.append(path)

    if limit is not None:
        paths_to_process = paths_to_process[:limit]

    print(f"[TASKS] {counts['scanned']} total, {counts['already_stamped']} already stamped, "
          f"{len(paths_to_process)} to process")

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_backfill_task_record, p, dry_run): p
                   for p in paths_to_process}
        for future in concurrent.futures.as_completed(futures):
            try:
                status, had_findings = future.result()
            except Exception as e:
                status = f"EXC: {e}"
                had_findings = False
            if "SKIP(stamped)" in status:
                counts["already_stamped"] += 1
            elif "WOULD-JUDGE" in status:
                counts["judged"] += 1
            elif "CLEAN" in status or "SKIP" in status:
                counts["clean_no_llm"] += 1
            elif "JUDGED" in status:
                counts["judged"] += 1
            elif "SCHEMA-FAIL" in status or "ERR" in status or "EXC" in status:
                counts["skipped_error"] += 1
                print(f"  [TASKS] {status}")

    print(f"[TASKS] Done. scanned={counts['scanned']} already_stamped={counts['already_stamped']} "
          f"clean_no_llm={counts['clean_no_llm']} judged={counts['judged']} "
          f"skipped_error={counts['skipped_error']}")
    return counts


# ---------------------------------------------------------------------------
# CALENDAR store backfill
# ---------------------------------------------------------------------------

def _backfill_calendar_record(path, dry_run):
    """Process a single calendar event record.
    Mirrors calendar_store_sync.py's reader/judge splice exactly (summary\\ndescription\\nlocation
    join, split on \\n up to 3 parts)."""
    try:
        record = _load_json(path)
    except Exception as e:
        return f"LOAD-ERR  {os.path.basename(path)}: {e}", False

    event_id = record.get("item_id", os.path.basename(path)[:-5])

    if record.get("reader_applied") is True:
        return f"SKIP(stamped) {event_id[:24]}", False

    payload = record.get("payload", {})
    raw_summary = payload.get("summary") or ""
    # Preserve None vs "" distinction — same as live writer
    raw_description = payload.get("description")
    raw_location = payload.get("location")

    free_text = "\n".join(filter(None, [
        raw_summary,
        raw_description or "",
        raw_location or "",
    ]))

    reader_applied = None
    verdict = None
    cleared_summary = raw_summary
    cleared_description = raw_description  # preserve None vs ""
    cleared_location = raw_location        # preserve None vs ""

    if free_text:
        try:
            findings = _scan_for_injection(free_text) or []
        except Exception:
            findings = []

        had_findings = bool(findings)
        # Dry-run: skip LLM, just count
        if dry_run and had_findings:
            return f"WOULD-JUDGE {event_id[:24]}", True
        if dry_run:
            return f"CLEAN(dry) {event_id[:24]}", False

        judge_result = _run_intake_judge(free_text, findings)
        reader_applied = judge_result.get("reader_applied")
        verdict = judge_result.get("verdict")
        cleared = judge_result.get("cleared_text") or free_text
        parts = cleared.split("\n", 2)
        cleared_summary = parts[0] if len(parts) > 0 else raw_summary
        if raw_description is not None:
            cleared_description = parts[1] if len(parts) > 1 else ""
        if raw_location is not None:
            cleared_location = parts[2] if len(parts) > 2 else ""
    else:
        reader_applied = True
        verdict = "NONE"
        had_findings = False
        if dry_run:
            return f"CLEAN(dry) {event_id[:24]}", False

    # Splice cleared fields back into payload
    record["payload"]["summary"] = cleared_summary
    if raw_description is not None:
        record["payload"]["description"] = cleared_description
    if raw_location is not None:
        record["payload"]["location"] = cleared_location

    if reader_applied is not None:
        record["reader_applied"] = reader_applied
    if verdict is not None and verdict != "NONE":
        record["verdict"] = verdict

    if not dry_run:
        if _validate_item:
            violations = _validate_item(record)
            if violations:
                return f"SCHEMA-FAIL {event_id[:24]}: {violations[0][:60]}", had_findings
        _write_atomic(path, record)

    verdict_str = verdict or "NONE"
    if had_findings:
        return f"JUDGED {event_id[:24]} verdict={verdict_str}", True
    return f"CLEAN {event_id[:24]}", False


def backfill_calendar(dry_run, limit):
    """Backfill the calendar item store."""
    print(f"\n[CALENDAR] Scanning {CALENDAR_STORE_ROOT} ...")
    counts = {"scanned": 0, "already_stamped": 0, "clean_no_llm": 0,
              "judged": 0, "skipped_error": 0}

    if not os.path.isdir(CALENDAR_STORE_ROOT):
        print(f"[CALENDAR] Store dir not found: {CALENDAR_STORE_ROOT}")
        return counts

    all_paths = [
        os.path.join(CALENDAR_STORE_ROOT, fn)
        for fn in os.listdir(CALENDAR_STORE_ROOT)
        if fn.endswith(".json")
    ]

    paths_to_process = []
    for path in all_paths:
        counts["scanned"] += 1
        try:
            rec = _load_json(path)
            if rec.get("reader_applied") is True:
                counts["already_stamped"] += 1
                continue
        except Exception:
            counts["skipped_error"] += 1
            continue
        paths_to_process.append(path)

    if limit is not None:
        paths_to_process = paths_to_process[:limit]

    print(f"[CALENDAR] {counts['scanned']} total, {counts['already_stamped']} already stamped, "
          f"{len(paths_to_process)} to process")

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_backfill_calendar_record, p, dry_run): p
                   for p in paths_to_process}
        for future in concurrent.futures.as_completed(futures):
            try:
                status, had_findings = future.result()
            except Exception as e:
                status = f"EXC: {e}"
                had_findings = False
            if "SKIP(stamped)" in status:
                counts["already_stamped"] += 1
            elif "WOULD-JUDGE" in status:
                counts["judged"] += 1
            elif "CLEAN" in status or "SKIP" in status:
                counts["clean_no_llm"] += 1
            elif "JUDGED" in status:
                counts["judged"] += 1
            elif "SCHEMA-FAIL" in status or "ERR" in status or "EXC" in status:
                counts["skipped_error"] += 1
                print(f"  [CALENDAR] {status}")

    print(f"[CALENDAR] Done. scanned={counts['scanned']} already_stamped={counts['already_stamped']} "
          f"clean_no_llm={counts['clean_no_llm']} judged={counts['judged']} "
          f"skipped_error={counts['skipped_error']}")
    return counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Backfill intake reader/judge stamps across all three stores.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Count only — no writes.")
    parser.add_argument("--limit", type=int, default=None, metavar="N",
                        help="Process at most N un-stamped records total (across all stores).")
    parser.add_argument("--store", choices=["email", "tasks", "calendar", "all"],
                        default="all", help="Which store(s) to backfill (default: all).")
    args = parser.parse_args()

    if not DRIVE:
        sys.stderr.write(
            "[intake-backfill] FATAL: no data root resolved (brain_root.resolve_brain_root() "
            "returned NOT-SET). Run `python3 shared/brain_root.py --set <path>` first.\n")
        return 1

    if args.dry_run:
        print("DRY-RUN mode — no writes will be made.")

    # Distribute the global limit across stores
    # Simple: let each store consume up to limit until budget exhausted.
    remaining = args.limit  # None = unlimited

    stores = []
    if args.store in ("email", "all"):
        stores.append(("email", backfill_email))
    if args.store in ("tasks", "all"):
        stores.append(("tasks", backfill_tasks))
    if args.store in ("calendar", "all"):
        stores.append(("calendar", backfill_calendar))

    total_judged = 0
    total_clean = 0
    total_stamped = 0
    total_errors = 0

    for store_name, fn in stores:
        store_limit = remaining
        counts = fn(dry_run=args.dry_run, limit=store_limit)
        processed = counts.get("clean_no_llm", 0) + counts.get("judged", 0)
        total_judged += counts.get("judged", 0)
        total_clean += counts.get("clean_no_llm", 0)
        total_stamped += counts.get("already_stamped", 0)
        total_errors += counts.get("skipped_error", 0)
        if remaining is not None:
            remaining = max(0, remaining - processed)
            if remaining == 0:
                print(f"[backfill] --limit {args.limit} reached; stopping.")
                break

    print(f"\n{'='*60}")
    print(f"BACKFILL SUMMARY  {'(DRY-RUN)' if args.dry_run else ''}")
    print(f"  already_stamped : {total_stamped}")
    print(f"  clean (no LLM)  : {total_clean}")
    print(f"  judged (LLM)    : {total_judged}")
    print(f"  skipped/errors  : {total_errors}")
    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    sys.exit(main() or 0)
