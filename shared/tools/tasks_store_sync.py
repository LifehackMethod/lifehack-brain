#!/usr/bin/env python3
"""tasks_store_sync.py — mechanical writer for the durable Tasks item store (Phase G-2).

Mirrors the email writer pattern (email_summary_sync.py) for Google Tasks:
  - Pulls via safe_tasks.py --desk planning --redact (sanitized, injection spans neutralized)
  - One durable item record per task written atomically (.tmp→rename) to a BLUE-GREEN
    store at $DRIVE/state/item-store/tasks/{task_id}.json
  - Lifecycle (mirrors email):
      task.status==completed         → state=completed
      task vanished from the pull    → state=cold   (NEVER deleted)
      task re-appears with new data  → state=active  (revive)
  - Delta-only: unchanged tasks (same updated timestamp) are skipped
  - No LLM in the write path — mechanical only

Usage:
  python3 tasks_store_sync.py --sync [--tasklist <id>] [--verbose] [--dry-run]
  python3 tasks_store_sync.py --self-test

Security: pulls run through safe_tasks.py --redact; injection spans are neutralized
before any field is stored. The raw free-text never hits the store unchecked.
"""

import argparse
import json
import os
import subprocess
import sys
import time

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
_BR_SOURCE, _BR_PATH = brain_root.resolve_brain_root()
DRIVE = _BR_PATH or ""

SAFE_TASKS = os.path.join(CODE_ROOT, "system", "tools", "safe_tasks.py")

# Blue-green store path — BESIDE email-summary, NEVER touching it.
STORE_ROOT = os.path.join(DRIVE, "state", "item-store", "tasks")
# CT-3.5: list MANIFESTS live in a SEPARATE dir so they are NOT swept as tasks nor counted as tasks by
# the item-store freshness dead-man (which reads only tasks/ + calendar/).
MANIFEST_ROOT = os.path.join(DRIVE, "state", "item-store", "task-lists")

# gws binary — resolve via PATH, survive a binary move (same pattern as safe_tasks.py). Called via
# subprocess (NOT the Bash tool), so the ingest hook doesn't gate it; `tasks tasklists list` is list
# METADATA (ids + user-authored titles). Titles are stored as free-text + SCANNED at read (item_store_read).
GWS_BIN = __import__("shutil").which("gws") or "/opt/homebrew/bin/gws"

WRITER_ID = "tasks-store-sync"
SOURCE = "google-tasks"

# ─────────────────────────────────────────────────────────────────────────────
# Schema import
# ─────────────────────────────────────────────────────────────────────────────

_SHARED_TOOLS = os.path.join(CODE_ROOT, "shared", "tools")
if _SHARED_TOOLS not in sys.path:
    sys.path.insert(0, _SHARED_TOOLS)

try:
    from item_schema import (
        validate_item_record, make_item_record, make_task_payload,
        make_task_list_payload, VALID_STATES,
    )
    _SCHEMA_AVAILABLE = True
    _SCHEMA_ERROR = None
except Exception as _se:
    _SCHEMA_AVAILABLE = False
    _SCHEMA_ERROR = str(_se)
    sys.stderr.write(
        f"[tasks-store-sync] FATAL: item_schema import failed ({_se}); "
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
    sys.stderr.write(f"[tasks-store-sync] WARNING: scan_for_injection import failed ({_scan_e}); "
                     "security scan will be skipped.\n")

try:
    from intake_reader import run_intake_judge as _run_intake_judge
    _READER_AVAILABLE = True
except Exception as _reader_e:
    _run_intake_judge = None
    _READER_AVAILABLE = False
    sys.stderr.write(f"[tasks-store-sync] WARNING: intake_reader import failed ({_reader_e}); "
                     "decode-and-judge step will be skipped.\n")


# ─────────────────────────────────────────────────────────────────────────────
# Timestamp helpers
# ─────────────────────────────────────────────────────────────────────────────

def _iso_now():
    lt = time.localtime()
    off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off


# ─────────────────────────────────────────────────────────────────────────────
# Store I/O — atomic write (mirrors write_thread_v2_atomic exactly)
# ─────────────────────────────────────────────────────────────────────────────

def _task_path(task_id):
    return os.path.join(STORE_ROOT, f"{task_id}.json")


def _load_record(task_id):
    path = _task_path(task_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_atomic(task_id, record):
    """Atomically write {task_id}.json via .tmp → os.replace (never a partial read)."""
    os.makedirs(STORE_ROOT, exist_ok=True)
    path = _task_path(task_id)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    # S8.4 append-on-write (optimisation only — see store_date_index.py's contract): keep the sidecar
    # date-index current without waiting for the next read's reconciliation. Never raises.
    try:
        import store_date_index as _sdi
        _sdi.append_entry("task", f"{task_id}.json", path)
    except Exception:
        pass


def _list_stored_ids():
    """Return the set of task_ids already in the store (from filenames)."""
    if not os.path.isdir(STORE_ROOT):
        return set()
    return {fn[:-5] for fn in os.listdir(STORE_ROOT) if fn.endswith(".json")}


# ─────────────────────────────────────────────────────────────────────────────
# safe_tasks.py integration — subprocess pull with --redact
# ─────────────────────────────────────────────────────────────────────────────

def _pull_tasks(tasklist_id, show_completed=True, timeout=60, max_pages=50):
    """Pull ALL tasks in a list (PAGINATED) via safe_tasks.py --desk planning --redact. Returns (items_list, rc).

    CT-3.5: follows nextPageToken until the list is drained (bounded by max_pages × 100 = 5000/list) so a
    list with >100 tasks is COMPLETE — otherwise the overflow silently false-colds. --redact neutralizes
    injection spans in-place. rc: 0=clean, 1=some page flagged (still valid), 2=error.
    """
    all_items = []
    page_token = None
    worst_rc = 0
    for _page in range(max_pages):
        p = {
            "tasklist": tasklist_id,
            "showCompleted": show_completed,
            "showDeleted": False,
            "maxResults": 100,
        }
        if page_token:
            p["pageToken"] = page_token
        one, rc = _pull_tasks_page(json.dumps(p), timeout=timeout)
        if one is None:
            return None, 2
        if rc == 1:
            worst_rc = 1
        items, page_token = one
        all_items.extend(items)
        if not page_token:
            break
    return all_items, worst_rc


def _pull_tasks_page(params, timeout=60):
    """One page: run safe_tasks.py --redact with the given params-json. Returns ((items, nextPageToken), rc)
    or (None, 2) on error."""
    cmd = [
        sys.executable, SAFE_TASKS,
        "--desk", "planning",
        "--redact",
        params,
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        sys.stderr.write("[tasks-store-sync] safe_tasks.py timed out\n")
        return None, 2
    except Exception as e:
        sys.stderr.write(f"[tasks-store-sync] safe_tasks.py subprocess error: {e}\n")
        return None, 2

    if proc.returncode == 2:
        sys.stderr.write(
            f"[tasks-store-sync] safe_tasks.py error (exit 2): {proc.stderr.strip()[:500]}\n")
        return None, 2

    if proc.stderr.strip():
        # exit 1 = flagged but still valid; print the warning
        sys.stderr.write(f"[tasks-store-sync] safe_tasks stderr: {proc.stderr.strip()[:500]}\n")

    try:
        data = json.loads(proc.stdout.strip())
    except Exception as e:
        sys.stderr.write(f"[tasks-store-sync] could not parse safe_tasks output: {e}\n")
        return None, 2

    items = data.get("items", []) or []
    next_token = data.get("nextPageToken") if isinstance(data, dict) else None
    return (items, next_token), proc.returncode


# ─────────────────────────────────────────────────────────────────────────────
# Provenance tag (lightweight — no full ingest_gate needed here; safe_tasks
# already ran the sanitizer; we generate a stable tag from the task id + timestamp)
# ─────────────────────────────────────────────────────────────────────────────

def _provenance_tag(record_id):
    import hashlib
    h = hashlib.sha256(f"{record_id}:{_iso_now()}".encode()).hexdigest()[:12]
    return f"item-store/task/{record_id}/{h}"


# ─────────────────────────────────────────────────────────────────────────────
# CT-3.5: enumerate ALL Google Task lists + write a per-list MANIFEST record
# ─────────────────────────────────────────────────────────────────────────────

def _list_tasklists(timeout=30):
    """Enumerate all Google Task lists (id + title) via `gws tasks tasklists list`. Returns
    [(list_id, list_title), ...] or None on failure. Metadata only (no task free-text). Titles are
    user-authored → stored as free-text + SCANNED at read (item_store_read field-branch)."""
    try:
        proc = subprocess.run([GWS_BIN, "tasks", "tasklists", "list"],
                              capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        sys.stderr.write(f"[tasks-store-sync] tasklists enumerate failed: {e}\n")
        return None
    if proc.returncode != 0:
        sys.stderr.write(f"[tasks-store-sync] tasklists list error: {proc.stderr.strip()[:300]}\n")
        return None
    try:
        data = json.loads(proc.stdout.strip())
    except Exception as e:
        sys.stderr.write(f"[tasks-store-sync] could not parse tasklists output: {e}\n")
        return None
    out = []
    for it in (data.get("items", []) or []):
        lid = it.get("id")
        if lid:
            out.append((lid, it.get("title") or lid))
    return out


def _manifest_path(list_id):
    return os.path.join(MANIFEST_ROOT, f"{list_id}.json")


def _write_manifest(list_id, list_title, active_count):
    """Write one task_list manifest record (id, title, active count) to the SEPARATE task-lists/ dir."""
    rec = make_item_record(
        item_id=list_id,
        item_type="task_list",
        payload=make_task_list_payload(list_id=list_id, list_title=list_title, active_count=active_count),
        writer_id=WRITER_ID,
        source=SOURCE,
        provenance_tag=f"item-store/task_list/{list_id}/"
                       + __import__("hashlib").sha256(f"{list_id}:{_iso_now()}".encode()).hexdigest()[:12],
        state="active",
    )
    violations = validate_item_record(rec)
    if violations:
        sys.stderr.write(f"[tasks-store-sync] manifest {list_id} SCHEMA VIOLATION (not written): {violations}\n")
        return False
    os.makedirs(MANIFEST_ROOT, exist_ok=True)
    path = _manifest_path(list_id)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Core sync logic — process one task item
# ─────────────────────────────────────────────────────────────────────────────

def _lifecycle_state(task_raw, existing_record):
    """Determine the new lifecycle state for a task.

    task.status == 'completed'  → state=completed
    new task (no existing)      → state=active
    task re-appeared with NEW   → state=active (revive from cold)
    task unchanged              → preserve existing state
    """
    gstatus = (task_raw.get("status") or "").lower()
    if gstatus == "completed":
        return "completed"
    if existing_record is None:
        return "active"
    # If the task re-appeared (we're processing it again), and it was cold, revive it.
    existing_state = existing_record.get("state") or "active"
    if existing_state == "cold":
        return "active"
    return existing_state


def _is_unchanged(task_raw, existing_record):
    """Delta-only: skip if the task's 'updated' timestamp hasn't changed since last write.
    Mirrors the email writer's Wr-3 UNCHANGED-skip heuristic."""
    if existing_record is None:
        return False  # new task, must write
    new_updated = task_raw.get("updated", "")
    old_updated = (existing_record.get("payload") or {}).get("updated", "")
    return bool(new_updated and new_updated == old_updated)


def _qualified_id(task_raw):
    """CT-3.5: the RECORD id = {list_id}__{task_id}. Google task ids are LIST-SCOPED, not globally unique —
    two tasks in different lists can share an id, so the bare id would collide/overwrite in a flat store."""
    return f"{task_raw.get('_list_id') or ''}__{task_raw.get('id') or ''}"


def _process_task(task_raw, verbose=False, dry_run=False):
    """Build, validate, and write one item record. Returns (action_str, ok_bool)."""
    task_id = task_raw.get("id", "")
    if not task_id:
        sys.stderr.write("[tasks-store-sync] skipping task with no id\n")
        return "SKIP (no id)", False

    qid = _qualified_id(task_raw)           # list-qualified record id (filename + item_id + provenance)
    existing = _load_record(qid)

    # Delta-only skip
    if _is_unchanged(task_raw, existing):
        return f"UNCHANGED  {qid[:32]}", True

    state = _lifecycle_state(task_raw, existing)
    now = _iso_now()
    first_seen = (existing.get("first_seen") if existing else None) or now
    prov = (existing.get("provenance_tag") if existing else None) or _provenance_tag(qid)

    # ── Security gate: scan + decode-and-judge the task free-text fields ──────
    raw_title = task_raw.get("title") or ""
    raw_notes = task_raw.get("notes") or ""
    free_text = "\n".join(filter(None, [raw_title, raw_notes]))

    reader_applied = None
    verdict = None
    cleared_title = raw_title
    cleared_notes = raw_notes if task_raw.get("notes") is not None else None

    # HARD-STOP parity with calendar_store_sync (organism-audit 2026-07-24): if there is
    # free-text to scan but either the injection scanner or the intake judge failed to import,
    # refuse to store rather than silently persisting raw attacker-controllable text. Mirrors the
    # calendar writer's verified-defect-(c) fix (flag set at import, stop at use-site).
    if free_text and not (_SCAN_AVAILABLE and _READER_AVAILABLE):
        sys.stderr.write(
            "[tasks-store-sync] HARD-STOP: injection scanner / intake judge unavailable "
            f"(scan_available={_SCAN_AVAILABLE}, reader_available={_READER_AVAILABLE}); "
            "refusing to store unscanned task free-text.\n")
        sys.exit(1)

    if _SCAN_AVAILABLE and _READER_AVAILABLE and free_text:
        findings = _scan_for_injection(free_text)
        judge_result = _run_intake_judge(free_text, findings)
        reader_applied = judge_result.get("reader_applied")
        verdict = judge_result.get("verdict")
        # Splice cleared text back: cleared_text replaces the full free_text blob.
        # Re-split on the same newline boundary used to join (title is first line).
        cleared = judge_result.get("cleared_text") or free_text
        cleared_lines = cleared.split("\n", 1)
        cleared_title = cleared_lines[0]
        if task_raw.get("notes") is not None:
            cleared_notes = cleared_lines[1] if len(cleared_lines) > 1 else ""
    # ─────────────────────────────────────────────────────────────────────────

    payload = make_task_payload(
        task_id=task_id,
        title=cleared_title,
        status=task_raw.get("status") or "",
        list_id=task_raw.get("_list_id") or "",
        notes=cleared_notes,
        due=task_raw.get("due"),
        updated=task_raw.get("updated"),
        parent=task_raw.get("parent"),
        position=task_raw.get("position"),
        list_title=task_raw.get("_list_title"),       # CT-3.5: which list, by name
        web_view_link=task_raw.get("webViewLink"),    # CT-3.5: tappable Google URL
    )

    record = make_item_record(
        item_id=qid,
        item_type="task",
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
            f"[tasks-store-sync] {qid} SCHEMA VIOLATION (record NOT written): {violations}\n")
        return f"SCHEMA-FAIL {qid[:32]}: {violations[0][:60]}", False

    if dry_run:
        if verbose:
            print(f"  DRY  {qid} — {task_raw.get('title','')[:50]} ({state})")
        return f"DRY   {qid[:32]} — {state}", True

    _write_atomic(qid, record)
    if verbose:
        print(f"  WRITE {qid[:40]} — {task_raw.get('title','')[:44]} ({state})")
    return f"WRITE {qid[:32]} — {state}", True


# ─────────────────────────────────────────────────────────────────────────────
# Cold sweep — tasks that vanished from the pull → state=cold (NEVER delete)
# Mirrors email write_v2's cold-sweep exactly.
# ─────────────────────────────────────────────────────────────────────────────

def _cold_sweep(active_ids, dry_run=False, verbose=False):
    """Mark records for tasks no longer in the pull as state=cold. Never deletes."""
    stored = _list_stored_ids()
    cold_count = 0
    for tid in stored - active_ids:
        rec = _load_record(tid)
        if rec is None:
            continue
        if (rec.get("state") or "active") in ("cold", "completed", "deep-cold"):
            continue  # already inactive — leave it
        rec["state"] = "cold"
        rec["cold_at"] = _iso_now()
        if not dry_run:
            _write_atomic(tid, rec)
        cold_count += 1
        if verbose:
            print(f"  COLD  {tid[:24]} — departed from pull")
    return cold_count


# ─────────────────────────────────────────────────────────────────────────────
# Default tasklist resolver — uses the "planning" desk default
# ─────────────────────────────────────────────────────────────────────────────

# The planning desk uses a hardcoded default tasklist id; the user can override via --tasklist.
# We don't autodiscover all tasklists here — that's a future extension.
# This matches the safe_tasks.py usage in planning-vault-pull.py.
DEFAULT_TASKLIST_ID = "@default"


# ─────────────────────────────────────────────────────────────────────────────
# Public sync entry point
# ─────────────────────────────────────────────────────────────────────────────

def sync(tasklist_id=None, verbose=False, dry_run=False):
    """CT-3.5: pull EVERY Google Task list (or a single list if tasklist_id is given) into the durable
    store, preserving list membership (list_id+list_title) + subtask hierarchy (parent/position). Returns
    counts. CRITICAL: accumulate the active set across ALL lists, then run ONE cold-sweep — a per-list sweep
    would cold-mark every OTHER list's tasks (they're not in that list's pull)."""
    if not _SCHEMA_AVAILABLE:
        sys.stderr.write(
            f"[tasks-store-sync] HARD-STOP: item_schema unavailable ({_SCHEMA_ERROR})\n")
        return {"error": "schema_unavailable"}

    # Resolve the list set: a single list on request (targeted run), else ALL lists.
    if tasklist_id:
        lists = [(tasklist_id, tasklist_id)]
    else:
        lists = _list_tasklists()
        if lists is None:
            sys.stderr.write("[tasks-store-sync] could not enumerate task lists — aborting sync\n")
            return {"error": "tasklists_failed"}

    print(f"[tasks-store-sync] sync — {len(lists)} list(s) → {STORE_ROOT}"
          + (" [DRY-RUN]" if dry_run else ""))

    counts = {"written": 0, "unchanged": 0, "cold": 0, "errors": 0, "lists": 0, "manifests": 0}
    active_ids = set()          # UNION across ALL lists — the cold-sweep diffs against this ONCE
    any_flagged = False

    for (list_id, list_title) in lists:
        items, rc = _pull_tasks(list_id)
        if items is None:
            sys.stderr.write(f"[tasks-store-sync] list {list_title!r} pull failed — skipping this list\n")
            counts["errors"] += 1
            continue
        if rc == 1:
            any_flagged = True
        list_active = 0
        for task in items:
            if not isinstance(task, dict):
                continue
            task["_list_id"] = list_id
            task["_list_title"] = list_title
            tid = task.get("id", "")
            if tid:
                active_ids.add(f"{list_id}__{tid}")
            if (task.get("status") or "").lower() != "completed":
                list_active += 1
            action, ok = _process_task(task, verbose=verbose, dry_run=dry_run)
            if "UNCHANGED" in action:
                counts["unchanged"] += 1
            elif "WRITE" in action or "DRY" in action:
                counts["written"] += 1
            elif "SCHEMA-FAIL" in action or not ok:
                counts["errors"] += 1
        counts["lists"] += 1
        if not dry_run and _write_manifest(list_id, list_title, list_active):
            counts["manifests"] += 1
        if verbose:
            print(f"  LIST  {list_title[:40]} — {list_active} active")

    if any_flagged:
        print("[tasks-store-sync] WARNING: safe_tasks flagged injection patterns in ≥1 list; "
              "spans neutralized — proceeding with sanitized data")

    # ONE union cold-sweep across ALL lists (never per-list — that would cold the other lists).
    if not dry_run and active_ids:
        counts["cold"] = _cold_sweep(active_ids, dry_run=False, verbose=verbose)
        if counts["cold"]:
            print(f"[tasks-store-sync] cold-sweep: {counts['cold']} departed task(s) → "
                  "state=cold (KEPT on disk — never deleted)")
    elif dry_run:
        stored = _list_stored_ids()
        counts["cold"] = len(stored - active_ids)  # count only, no write

    print(f"[tasks-store-sync] sync DONE — lists={counts['lists']} manifests={counts['manifests']} "
          f"written={counts['written']} unchanged={counts['unchanged']} "
          f"cold={counts['cold']} errors={counts['errors']}")
    return counts


# ─────────────────────────────────────────────────────────────────────────────
# Self-tests — synthetic data, NO live Google pull required
# ─────────────────────────────────────────────────────────────────────────────

def _run_self_tests():
    """Run self-tests using monkeypatched synthetic data. Returns (passed, failed)."""
    import tempfile
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

    # Synthetic safe_tasks output (the shape --redact returns: same as gws items list)
    SYNTHETIC_TASKS = [
        {
            "id": "test_task_001",
            "title": "Review the $125k SOW",
            "notes": "Due before the client call on Friday.",
            "status": "needsAction",
            "due": "2026-07-11T00:00:00.000Z",
            "updated": "2026-07-09T10:00:00.000Z",
            "position": "00000000000000000001",
            "_list_id": "tasklist_xyz",
        },
        {
            "id": "test_task_002",
            "title": "Send invoice for June",
            "status": "completed",
            "updated": "2026-07-01T08:00:00.000Z",
            "_list_id": "tasklist_xyz",
        },
        {
            "id": "test_task_003",
            "title": "Schedule the skydive coaching session",
            "status": "needsAction",
            "updated": "2026-07-08T15:00:00.000Z",
            "_list_id": "tasklist_xyz",
        },
    ]

    # Use a temp directory as the store for the tests (never touches Drive)
    tmp_store = tempfile.mkdtemp(prefix="tasks_store_test_")
    original_store_root = globals().get("STORE_ROOT")

    # Monkey-patch the module-level STORE_ROOT and helper functions
    import tasks_store_sync as _mod
    _original_store_root = _mod.STORE_ROOT
    _mod.STORE_ROOT = tmp_store

    try:
        # ── Test 1: a new needsAction task is written as state=active ──
        try:
            task = SYNTHETIC_TASKS[0]
            action, ok_flag = _mod._process_task(task, verbose=False, dry_run=False)
            rec = _mod._load_record("tasklist_xyz__test_task_001")
            assert ok_flag, f"process_task returned ok=False: {action}"
            assert rec is not None, "record not written"
            assert rec["state"] == "active", f"expected state=active, got {rec['state']}"
            assert rec["item_type"] == "task"
            assert rec["payload"]["title"] == "Review the $125k SOW"
            ok("new-task — written as state=active")
        except Exception as e:
            fail("new-task", f"{e}\n{traceback.format_exc()}")

        # ── Test 2: a completed task is written as state=completed ──
        try:
            task = SYNTHETIC_TASKS[1]
            action, ok_flag = _mod._process_task(task, verbose=False, dry_run=False)
            rec = _mod._load_record("tasklist_xyz__test_task_002")
            assert ok_flag, f"process_task returned ok=False: {action}"
            assert rec is not None
            assert rec["state"] == "completed", f"expected state=completed, got {rec['state']}"
            ok("completed-task — written as state=completed")
        except Exception as e:
            fail("completed-task", f"{e}\n{traceback.format_exc()}")

        # ── Test 3: an unchanged task (same updated timestamp) is skipped ──
        try:
            # Write it first
            task = SYNTHETIC_TASKS[2]
            _mod._process_task(task, verbose=False, dry_run=False)
            # Process again — same updated → should be UNCHANGED
            action, ok_flag = _mod._process_task(task, verbose=False, dry_run=False)
            assert "UNCHANGED" in action, f"expected UNCHANGED, got: {action}"
            ok("delta-skip — unchanged task skipped (same updated timestamp)")
        except Exception as e:
            fail("delta-skip", f"{e}\n{traceback.format_exc()}")

        # ── Test 4: a task with a new updated timestamp triggers a re-write ──
        try:
            import copy
            task_updated = copy.deepcopy(SYNTHETIC_TASKS[2])
            task_updated["updated"] = "2026-07-10T09:00:00.000Z"  # newer timestamp
            task_updated["title"] = "Schedule the skydive coaching session (UPDATED)"
            action, ok_flag = _mod._process_task(task_updated, verbose=False, dry_run=False)
            assert "WRITE" in action, f"expected WRITE, got: {action}"
            rec = _mod._load_record("tasklist_xyz__test_task_003")
            assert rec["payload"]["title"] == "Schedule the skydive coaching session (UPDATED)"
            ok("delta-write — changed task re-written on updated timestamp change")
        except Exception as e:
            fail("delta-write", f"{e}\n{traceback.format_exc()}")

        # ── Test 5: cold sweep marks a departed task as cold (never deletes) ──
        try:
            # Active ids = only tasks 001 and 002; task 003 is "departed"
            active = {"tasklist_xyz__test_task_001", "tasklist_xyz__test_task_002"}
            cold_count = _mod._cold_sweep(active, dry_run=False, verbose=False)
            rec = _mod._load_record("tasklist_xyz__test_task_003")
            assert rec is not None, "cold record should still exist (never deleted)"
            assert rec["state"] == "cold", f"expected state=cold, got {rec['state']}"
            assert "cold_at" in rec, "cold_at stamp missing"
            assert cold_count == 1, f"expected 1 cold, got {cold_count}"
            ok("cold-sweep — departed task marked cold, file kept (never deleted)")
        except Exception as e:
            fail("cold-sweep", f"{e}\n{traceback.format_exc()}")

        # ── Test 6: a cold task that re-appears is revived to active ──
        try:
            # task_003 is now cold; re-process it with a new updated timestamp
            import copy
            task_revived = copy.deepcopy(SYNTHETIC_TASKS[2])
            task_revived["updated"] = "2026-07-10T12:00:00.000Z"  # new timestamp so it's not "unchanged"
            action, ok_flag = _mod._process_task(task_revived, verbose=False, dry_run=False)
            rec = _mod._load_record("tasklist_xyz__test_task_003")
            assert rec["state"] == "active", f"expected state=active after revival, got {rec['state']}"
            ok("cold-revival — cold task revived to active on re-appearance")
        except Exception as e:
            fail("cold-revival", f"{e}\n{traceback.format_exc()}")

        # ── Test 7: validate_item_record is called and rejects a bad record ──
        try:
            from item_schema import validate_item_record as _v
            bad = {"item_id": "", "item_type": "task"}  # missing many fields
            violations = _v(bad)
            assert len(violations) > 0, "expected violations on malformed record"
            ok("schema-gate — malformed record rejected by validate_item_record")
        except Exception as e:
            fail("schema-gate", f"{e}\n{traceback.format_exc()}")

        # ── Test 8: atomic write uses .tmp → os.replace (check no .tmp left behind) ──
        try:
            task = SYNTHETIC_TASKS[0]
            _mod._process_task(task, verbose=False, dry_run=False)
            tmp_path = _mod._task_path("tasklist_xyz__test_task_001") + ".tmp"
            assert not os.path.exists(tmp_path), ".tmp file left behind after atomic write"
            ok("atomic-write — .tmp file cleaned up after os.replace")
        except Exception as e:
            fail("atomic-write", f"{e}\n{traceback.format_exc()}")

        # ── Test 9: dry-run writes nothing to disk ──
        try:
            import tempfile
            dry_store = tempfile.mkdtemp(prefix="tasks_dry_")
            _mod.STORE_ROOT = dry_store
            task = dict(SYNTHETIC_TASKS[0], id="dry_task_999", _list_id="list_x")
            action, ok_flag = _mod._process_task(task, verbose=False, dry_run=True)
            assert "DRY" in action, f"expected DRY in action, got: {action}"
            assert not os.path.exists(os.path.join(dry_store, "list_x__dry_task_999.json")), \
                "dry-run should not write to disk"
            ok("dry-run — no disk writes in dry-run mode")
            _mod.STORE_ROOT = tmp_store  # restore
        except Exception as e:
            fail("dry-run", f"{e}\n{traceback.format_exc()}")
            _mod.STORE_ROOT = tmp_store

        # ── Test 10: CT-3.5 multi-list UNION sweep — a task in list B is NOT false-cold when list A is
        #    also pulled; same task-id in two lists → two distinct files (no collision); manifests + list_title ──
        try:
            import tempfile as _tf10
            ml_store = _tf10.mkdtemp(prefix="tasks_ml_"); ml_man = _tf10.mkdtemp(prefix="tasks_mlman_")
            _save_man = _mod.MANIFEST_ROOT
            _mod.STORE_ROOT = ml_store; _mod.MANIFEST_ROOT = ml_man
            _save_lt, _save_pt = _mod._list_tasklists, _mod._pull_tasks
            _mod._list_tasklists = lambda: [("listA", "Work"), ("listB", "[ Consulting ]")]
            def _fake_pull(list_id, **kw):
                if list_id == "listA":
                    return ([{"id": "shared_id", "title": "A task", "status": "needsAction",
                              "updated": "2026-07-10T01:00:00Z", "webViewLink": "https://tasks.google.com/a"}], 0)
                return ([{"id": "shared_id", "title": "B task (same id, diff list)", "status": "needsAction",
                          "updated": "2026-07-10T02:00:00Z"}], 0)
            _mod._pull_tasks = _fake_pull
            c = _mod.sync(verbose=False, dry_run=False)
            recA = _mod._load_record("listA__shared_id"); recB = _mod._load_record("listB__shared_id")
            man_ok = (os.path.exists(os.path.join(ml_man, "listA.json"))
                      and os.path.exists(os.path.join(ml_man, "listB.json")))
            cond = (recA and recB
                    and recA["state"] == "active" and recB["state"] == "active"
                    and c["cold"] == 0 and c["lists"] == 2 and c["manifests"] == 2 and man_ok
                    and recA["payload"]["list_title"] == "Work"
                    and recB["payload"]["list_title"] == "[ Consulting ]"
                    and recA["payload"].get("web_view_link") == "https://tasks.google.com/a")
            ok("ct35:multi-list-union — 2 lists w/ same task-id: no collision, no false-cold, manifests + list_title") \
                if cond else fail("ct35:multi-list-union",
                                  f"cold={c.get('cold')} lists={c.get('lists')} man_ok={man_ok} "
                                  f"A={recA and recA['state']} B={recB and recB['state']}")
            _mod._list_tasklists, _mod._pull_tasks = _save_lt, _save_pt
            _mod.MANIFEST_ROOT = _save_man; _mod.STORE_ROOT = tmp_store
            import shutil as _sh10
            _sh10.rmtree(ml_store, ignore_errors=True); _sh10.rmtree(ml_man, ignore_errors=True)
        except Exception as e:
            fail("ct35:multi-list-union", f"{e}\n{traceback.format_exc()}")
            _mod.STORE_ROOT = tmp_store

    finally:
        _mod.STORE_ROOT = _original_store_root
        import shutil
        shutil.rmtree(tmp_store, ignore_errors=True)

    print(f"\nTasks store sync self-test results: {passed} passed, {failed} failed")
    return passed, failed


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="tasks_store_sync.py — durable Google Tasks item store writer (Phase G-2)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sync", action="store_true",
                       help="Pull tasks and sync into the item store")
    group.add_argument("--self-test", action="store_true",
                       help="Run synthetic self-tests (no live Google pull)")
    parser.add_argument("--tasklist", default=None,
                        help="A single Google Tasks tasklist id for a TARGETED run. Default (omitted) = "
                             "sync ALL of the user's task lists (CT-3.5).")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print planned actions; write nothing to disk")
    args = parser.parse_args()

    if args.self_test:
        p, f = _run_self_tests()
        sys.exit(0 if f == 0 else 1)

    if args.sync:
        counts = sync(
            tasklist_id=args.tasklist,
            verbose=args.verbose,
            dry_run=args.dry_run,
        )
        if "error" in counts:
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    main()
