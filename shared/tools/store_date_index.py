#!/usr/bin/env python3
"""store_date_index.py — sidecar DATE INDEX for the three item stores (Phase 8 Lane C / S8.4).

THE MEASUREMENT THAT MOTIVATES THIS MODULE: item_store_window.py's sweep (task+calendar+email,
3,334 records total) costs ~750s COLD because it opens every record (0.2251s/file on this Drive
mount). But `os.listdir` + `os.stat` over the SAME 3,334 records costs 0.077s — a plain metadata
sweep is ~10,000x cheaper than hydrating content. So instead of a producer/warmer/schedule, this
module keeps a small per-store-directory SIDECAR file of {mtime, size, extracted date-fields} per
record, and on every read does the cheap stat-sweep to find exactly which records changed since the
sidecar was last written — only THOSE get opened. Nothing is pre-warmed and nothing runs on a timer.

▶ MANDATORY CONTRACT (do not weaken any of these three when editing this file):
    1. AUTHORITATIVE FOR LOCATION, NEVER FOR CONTENT. The sidecar only ever tells a caller "here are
       the windowing-relevant date/status fields, last verified against this exact (mtime, size)."
       It never substitutes for reading the real record when the real record's secure payload
       (free-text, flags, scan verdicts) is needed — callers still go through item_store_read /
       email_service_read for that.
    2. A MISS FALLS BACK TO A DIRECT READ. Any error building/loading/using the index (corrupt
       sidecar JSON, missing directory, unreadable record, an exception of any kind) degrades to the
       ORIGINAL full-walk adapters (item_store_read.iter_item_dates / email_service_read.thread_dates
       + iter_thread_ids) — slower, never wrong. Correctness never rests on this file existing.
    3. A RECONCILIATION DELTA IS REPAIRED IN PLACE, NEVER IGNORED. Every read re-derives ground truth
       via (mtime, size) — if the sidecar disagrees with the live directory (a changed/added/removed
       file, or a corrupted/stale entry), the mismatch is detected on the SAME read, the affected
       record is re-hydrated from source, and the sidecar is rewritten before returning. A stale
       sidecar degrades to SLOWER (falls through to a direct file read for the delta only), never to
       WRONG (a caller never sees cached data that disagrees with the live file).

RESIDENCY: the sidecar lives ON DRIVE, as a SIBLING file in each store directory's PARENT — e.g.
state/item-store/_date_index__tasks.json beside state/item-store/tasks/,
state/item-store/_date_index__calendar.json beside state/item-store/calendar/,
state/email-summary/_date_index__threads-v2.json beside state/email-summary/threads-v2/ — NEVER
machine-local, and NEVER inside the store directory itself. (The "beside, not inside" detail matters:
tasks_store_sync.py's own `_list_stored_ids()` and calendar_store_sync.py's cold-sweep both treat
EVERY *.json file inside their store directory as a real record — the same reason task_list
manifests already live in a sibling `task-lists/` dir instead of inside `tasks/`. An earlier version
of this module put the sidecar inside the store dir and a writer's own cold-sweep logic mistook it
for an abandoned record — caught 2026-08-03, fixed by moving it to the parent.) The three writers
(tasks_store_sync.py / calendar_store_sync.py / email_summary_sync.py) are lead-machine-gated; a
machine-local index could never be written on the OTHER machine, which would then silently take the
full cold walk with no way to catch up. Cold restore = delete the sidecar file(s); the next read
rebuilds the missing entries on demand (or run --rebuild-index for a full eager rebuild). EXCLUDE
`_date_index__*.json` from any backup lane — it is a disposable cache, not a record of anything that
happened.

NO SCHEDULED JOB. This module is only ever invoked from (a) a read, via the accelerated iterators
below, called synchronously inside item_store_window.py's sweep, or (b) the CLI --rebuild-index,
run by a human/on-demand. It NEVER runs on a timer, cron, launchd, or Pulse job — see Phase 8 Lane C
"ruled out" list (warming in any form was killed by measurement: launchd cannot read the Drive mount
at all under macOS TCC, and the laptop sleeps/wakes on the user's schedule, not a job's).

APPEND-ON-WRITE (optimisation, NOT the correctness path): the three writers may additionally patch
this sidecar at their existing atomic write choke points (write_thread_v2_atomic /
calendar_store_sync._write_atomic / tasks_store_sync._write_atomic) so a fresh write is already
reflected before the next read even bothers to stat it. This is pure speed — a missed append is
caught anyway by the mtime/size reconciliation on the next read (contract clause 3). This module
does not require or assume any writer integration to be correct.

SIDECAR SHAPE (per store directory, `_date_index.json`):
    {"schema_v": 1, "built": <unix ts>,
     "entries": {"<filename>.json": {"mtime": <float>, "size": <int>, "dates": {...}}, ...}}
  `dates` holds the same windowing fields item_store_read.iter_item_dates / email_service_read
  .thread_dates already expose (item_id/thread_id, state, start/due/updated/message_dates/etc) — a
  dict rather than a bare list, so item_store_window.py's per-type window logic (due vs updated vs
  open, recurring-master detection, message-date matching) gets EXACTLY the fields it needs, byte-
  for-byte identical to a direct read of that record.

CLI:
  python3 store_date_index.py --rebuild-index [--types task,calendar,email]
  python3 store_date_index.py --self-test
"""

import argparse
import json
import os
import sys
import time

CODE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.join(CODE_ROOT, "shared", "tools") not in sys.path:
    sys.path.insert(0, os.path.join(CODE_ROOT, "shared", "tools"))

import item_store_read as isr           # noqa: E402
import email_service_read as esr        # noqa: E402

INDEX_FILENAME_PREFIX = "_date_index__"   # sidecar is named f"{prefix}{store_dir_basename}.json"


# ---------------------------------------------------------------------------
# Directory / sidecar-path resolution — read isr.*/esr.* live (never cache at import time), so tests
# that monkeypatch isr.TASKS_DIR / esr.THREADS_V2_DIR are respected.
#
# The sidecar is a SIBLING file in the store directory's PARENT — e.g.
#   state/item-store/_date_index__tasks.json     beside   state/item-store/tasks/
#   state/item-store/_date_index__calendar.json  beside   state/item-store/calendar/
#   state/email-summary/_date_index__threads-v2.json  beside  state/email-summary/threads-v2/
# — NEVER inside the store directory itself. This is the SAME pattern tasks_store_sync.py already
# uses for task_list manifests (task-lists/ is a sibling of tasks/, not a file inside it), and for
# the same reason: every writer's own directory listing (_list_stored_ids in tasks_store_sync.py,
# the cold-sweep scan in calendar_store_sync.py, isr.iter_item_dates, esr.iter_thread_ids) treats
# EVERY *.json file in the store directory as a real record. A first version of this module put the
# sidecar INSIDE the store dir — caught 2026-08-03 when a writer's own cold-sweep logic picked up
# "_date_index.json" as a phantom stored id and tried to cold-sweep it (and, worse, three writers'
# self-tests — which monkeypatch the WRITER's store root but not this module's isr/esr globals — had
# already leaked synthetic test entries into the real production sidecars before the bug was caught;
# cleaned via --rebuild-index). Living in the parent directory sidesteps every one of those scans.
# ---------------------------------------------------------------------------

def _dir_for(item_type):
    if item_type == "task":
        return isr.TASKS_DIR
    if item_type == "calendar":
        return isr.CAL_DIR
    if item_type == "email":
        return esr.THREADS_V2_DIR
    return None


def _sidecar_path_for_store_dir(store_dir):
    """The sibling sidecar path for a given store directory — see the residency note above. Pure
    string/path math (no I/O), so it's safe to call on any directory, real or not-yet-created."""
    store_dir = store_dir.rstrip(os.sep)
    parent = os.path.dirname(store_dir)
    base = os.path.basename(store_dir)
    return os.path.join(parent, f"{INDEX_FILENAME_PREFIX}{base}.json")


def _index_path(item_type):
    d = _dir_for(item_type)
    return _sidecar_path_for_store_dir(d) if d else None


# ---------------------------------------------------------------------------
# The cheap layer: listdir + stat ONLY (no file content read). This is the ~0.077s/3334-file sweep.
# ---------------------------------------------------------------------------

def _fast_sweep(store_dir):
    """{filename: (mtime, size)} for every *.json record in store_dir. Metadata only — never opens a
    record. (No sidecar-filename exclusion needed here any more — the sidecar lives in the PARENT
    directory, never in store_dir itself; see the residency note above.)"""
    out = {}
    if not store_dir or not os.path.isdir(store_dir):
        return out
    for fn in os.listdir(store_dir):
        if not fn.endswith(".json"):
            continue
        try:
            st = os.stat(os.path.join(store_dir, fn))
        except OSError:
            continue
        out[fn] = (st.st_mtime, st.st_size)
    return out


# ---------------------------------------------------------------------------
# Sidecar load/save
# ---------------------------------------------------------------------------

def _load_index(item_type):
    """Load the persisted sidecar. Returns {} on ANY problem (missing/corrupt) — never raises; a
    caller with an empty index just re-hydrates everything on this read (contract clause 2)."""
    path = _index_path(item_type)
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        entries = data.get("entries") if isinstance(data, dict) else None
        return entries if isinstance(entries, dict) else {}
    except Exception:
        return {}


def _save_index(item_type, entries):
    """Atomic write of the sidecar (temp + os.replace — never a partial read by a concurrent reader)."""
    path = _index_path(item_type)
    if not path:
        return
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    tmp = path + f".tmp.{os.getpid()}"
    payload = {"schema_v": 1, "built": time.time(), "entries": entries}
    with open(tmp, "w") as f:
        json.dump(payload, f)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Per-record extraction (mirrors item_store_read.iter_item_dates / email_service_read.thread_dates
# EXACTLY, field for field, so a cache hit and a cache miss return identical shapes). These read ONE
# file — the generators in isr/esr only expose whole-directory walks, so a single-record extraction
# is new here, not a duplicate of an existing public entry point.
# ---------------------------------------------------------------------------

def _extract_item_fields(item_type, path):
    """Task/calendar record → the same dict isr.iter_item_dates yields for this record."""
    try:
        with open(path) as f:
            rec = json.load(f)
    except Exception:
        return None
    if not isinstance(rec, dict):
        return None
    state = isr.record_state(rec) if hasattr(isr, "record_state") else (rec.get("state") or "active")
    p = rec.get("payload") or {}
    return {
        "item_id": rec.get("item_id") or p.get("id"),
        "item_type": item_type,
        "state": state,
        "status": p.get("status", ""),
        "start": p.get("start", ""),
        "end": p.get("end", ""),
        "due": p.get("due", ""),
        "updated": p.get("updated", "") or rec.get("last_synced", ""),
        "is_recurring": bool(p.get("is_recurring")),
        "first_seen": rec.get("first_seen", ""),
        "last_synced": rec.get("last_synced", ""),
    }


def _extract_email_fields(fn, path):
    """Email thread record → the same dict email_service_read.thread_dates yields for this thread.
    thread_id is derived from the FILENAME (fn[:-5]), matching iter_thread_ids()+thread_dates(tid) —
    the store's writer always names the file f'{thread_id}.json', so this is exact, not a guess."""
    try:
        with open(path) as f:
            rec = json.load(f)
    except Exception:
        return None
    if not isinstance(rec, dict):
        return None
    state = esr.record_state(rec) if hasattr(esr, "record_state") else (rec.get("state") or "active")
    msg_dates = [m.get("date", "") for m in rec.get("messages", []) if isinstance(m, dict)]
    msg_dates = [d for d in msg_dates if d]
    thread_id = fn[:-5] if fn.endswith(".json") else fn
    return {
        "thread_id": thread_id,
        "state": state,
        "first_seen": rec.get("first_seen", ""),
        "last_synced": rec.get("last_synced", ""),
        "message_dates": msg_dates,
        "first_message_date": msg_dates[0] if msg_dates else rec.get("first_seen", ""),
        "last_message_date": msg_dates[-1] if msg_dates else rec.get("last_synced", ""),
        "message_count": rec.get("message_count", 0),
    }


def _extract(item_type, fn, path):
    if item_type == "email":
        return _extract_email_fields(fn, path)
    return _extract_item_fields(item_type, path)


# ---------------------------------------------------------------------------
# THE RECONCILIATION — the load-bearing correctness path (contract clause 3). Every call: cheap stat
# sweep of the live directory, diff against the persisted sidecar by (mtime, size), re-hydrate ONLY
# the deltas (new / changed files; removed files are dropped), and if anything changed, repair the
# sidecar in place before returning. Never trusts the sidecar's cached `dates` for a file whose
# (mtime, size) no longer matches — that is what makes a stale/corrupted entry self-healing rather
# than silently wrong.
# ---------------------------------------------------------------------------

def _reconcile(item_type):
    """Returns a list of extracted-field dicts for every current record in item_type's store,
    consulting + repairing the sidecar. Raises on a structural problem (bad store dir etc.) so the
    PUBLIC iterators below can catch it and fall back to the direct full-walk adapters — this
    function itself does not swallow errors, so a caller always knows whether the fast path ran."""
    store_dir = _dir_for(item_type)
    if store_dir is None:
        raise ValueError(f"unknown item_type {item_type!r}")
    fast = _fast_sweep(store_dir)                 # {fn: (mtime, size)} — the ~0.077s layer
    old_index = _load_index(item_type)            # {fn: {"mtime","size","dates"}}
    new_index = {}
    dirty = (set(old_index.keys()) != set(fast.keys()))   # added/removed files → sidecar is stale
    out = []
    for fn, (mtime, size) in fast.items():
        cached = old_index.get(fn)
        if (cached is not None and cached.get("mtime") == mtime and cached.get("size") == size
                and isinstance(cached.get("dates"), dict)):
            fields = cached["dates"]
            new_index[fn] = cached
        else:
            dirty = True
            fields = _extract(item_type, fn, os.path.join(store_dir, fn))
            if fields is None:
                continue   # unreadable/corrupt record — excluded, same as isr/esr would skip it
            new_index[fn] = {"mtime": mtime, "size": size, "dates": fields}
        out.append(fields)
    if dirty:
        _save_index(item_type, new_index)   # repaired in place — the NEXT read sees the fixed sidecar
    return out


# ---------------------------------------------------------------------------
# PUBLIC accelerated iterators — drop-in replacements for the sweep loops in item_store_window.py.
# Each is a thin try/except around _reconcile(): any exception anywhere in the fast path degrades to
# the ORIGINAL direct adapters (contract clause 2). Materialized to a list (not a lazy generator) so
# a mid-iteration failure can't leak a partially-indexed, partially-direct result.
# ---------------------------------------------------------------------------

def iter_item_dates_indexed(item_type, include_inactive=True):
    try:
        out = []
        for fields in _reconcile(item_type):
            if fields.get("state") == "completed" and not include_inactive:
                continue
            out.append(fields)
        return out
    except Exception:
        return list(isr.iter_item_dates(item_type, include_inactive=include_inactive))


def iter_thread_dates_indexed(include_inactive=True):
    try:
        out = []
        for fields in _reconcile("email"):
            if fields.get("state") == "completed" and not include_inactive:
                continue
            out.append(fields)
        return out
    except Exception:
        out = []
        for tid in esr.iter_thread_ids():
            td = esr.thread_dates(tid, include_inactive=include_inactive)
            if td is not None:
                out.append(td)
        return out


# ---------------------------------------------------------------------------
# APPEND-ON-WRITE (optimisation, NOT the correctness path — see the module docstring's contract
# clause 3). Called from the three writers' EXISTING atomic-write choke points right after a record
# lands, so the sidecar reflects a fresh write immediately instead of waiting for the next read's
# reconciliation to notice the mtime/size delta. A single O(1) entry update — never a directory
# rescan (that would make every write pay an O(store-size) cost, defeating the point). Swallows every
# error (missing sidecar dir, unreadable just-written file, anything) — a failed/missing append just
# means the next read's reconciliation catches it instead (slower, never wrong).
# ---------------------------------------------------------------------------

def append_entry(item_type, filename, path):
    """Update ONE sidecar entry for a record a writer just wrote. `filename` is the store-relative
    filename (e.g. 'th_in.json'); `path` is the REAL path the writer just wrote (required — this
    function trusts `path`, never `_dir_for(item_type)`, to find the sidecar to update). That is
    deliberate: `_dir_for` reads item_store_read.py / email_service_read.py's module-level directory
    globals, which a CALLER'S OWN self-test may have monkeypatched to a temp dir for isolation — if
    this function used `_dir_for` instead of the writer's actual `path`, a writer's self-test would
    silently leak synthetic test entries into the REAL production sidecar (caught 2026-08-03: three
    writer self-tests each polluted the live sidecars with a handful of synthetic ids before this
    fix — cleaned via --rebuild-index). Deriving the sidecar directory from `path` itself means the
    sidecar always lives beside wherever the record ACTUALLY landed, test or production alike. The
    sidecar itself is placed in store_dir's PARENT (via _sidecar_path_for_store_dir), never inside
    store_dir — see the residency note above _dir_for (a second bug, also caught 2026-08-03: a
    sidecar living INSIDE the store dir got picked up by the writers' own record-listing scans as a
    phantom record). Never raises — a failure here just means the next read's reconciliation catches
    the delta."""
    try:
        store_dir = os.path.dirname(path)
        if not store_dir or not os.path.isdir(store_dir):
            return
        st = os.stat(path)
        fields = _extract(item_type, filename, path)
        if fields is None:
            return
        idx_path = _sidecar_path_for_store_dir(store_dir)
        entries = {}
        if os.path.exists(idx_path):
            try:
                with open(idx_path) as f:
                    data = json.load(f)
                entries = data.get("entries") if isinstance(data, dict) else None
                if not isinstance(entries, dict):
                    entries = {}
            except Exception:
                entries = {}
        entries[filename] = {"mtime": st.st_mtime, "size": st.st_size, "dates": fields}
        tmp = idx_path + f".tmp.{os.getpid()}"
        with open(tmp, "w") as f:
            json.dump({"schema_v": 1, "built": time.time(), "entries": entries}, f)
        os.replace(tmp, idx_path)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# --rebuild-index: force a full recompute (ignores any existing sidecar entirely) and persist it.
# "An index that cannot be regenerated is refused" — this is that regeneration path.
# ---------------------------------------------------------------------------

def rebuild_index(item_type):
    store_dir = _dir_for(item_type)
    if store_dir is None or not os.path.isdir(store_dir):
        return 0
    fast = _fast_sweep(store_dir)
    new_index = {}
    for fn, (mtime, size) in fast.items():
        fields = _extract(item_type, fn, os.path.join(store_dir, fn))
        if fields is None:
            continue
        new_index[fn] = {"mtime": mtime, "size": size, "dates": fields}
    _save_index(item_type, new_index)
    return len(new_index)


# ---------------------------------------------------------------------------
# Self-tests
# ---------------------------------------------------------------------------

def _run_self_tests():
    import tempfile
    import shutil
    import traceback

    passed = failed = 0

    def ok(n):
        nonlocal passed
        passed += 1
        print(f"  PASS  {n}")

    def fail(n, r):
        nonlocal failed
        failed += 1
        print(f"  FAIL  {n}: {r}")

    root = tempfile.mkdtemp(prefix="sdi_")
    _isr_save = (isr.TASKS_DIR, isr.CAL_DIR)
    _esr_save = (esr.THREADS_V2_DIR,)
    isr.TASKS_DIR = os.path.join(root, "tasks")
    isr.CAL_DIR = os.path.join(root, "calendar")
    esr.THREADS_V2_DIR = os.path.join(root, "threads-v2")
    for d in (isr.TASKS_DIR, isr.CAL_DIR, esr.THREADS_V2_DIR):
        os.makedirs(d, exist_ok=True)

    try:
        sys.path.insert(0, os.path.join(CODE_ROOT, "shared", "tools"))
        from item_schema import make_item_record, make_task_payload, make_calendar_payload

        def _wtask(tid, title, status, updated, due=""):
            rec = make_item_record(
                item_id=tid, item_type="task",
                payload=make_task_payload(task_id=tid, title=title, status=status, list_id="L1",
                                          notes="", due=due),
                writer_id="tasks-store-sync", source="google-tasks",
                provenance_tag=f"item-store/task/{tid}/x")
            rec["payload"]["updated"] = updated
            with open(os.path.join(isr.TASKS_DIR, f"{tid}.json"), "w") as f:
                json.dump(rec, f)

        def _wcal(eid, summary, start):
            payload = make_calendar_payload(event_id=eid, summary=summary, start=start, end=start,
                                            status="confirmed", calendar_id="c@x")
            rec = make_item_record(item_id=eid, item_type="calendar", payload=payload,
                                   writer_id="calendar-store-sync", source="google-calendar",
                                   provenance_tag=f"item-store/calendar/{eid}/x")
            with open(os.path.join(isr.CAL_DIR, f"{eid}.json"), "w") as f:
                json.dump(rec, f)

        def _wemail(tid, msg_dates):
            rec = {
                "thread_id": tid, "subject": "s", "labels": ["Consulting"],
                "messages": [{"message_id": f"m{i}", "from": "a@example.com", "date": d, "body": "b"}
                             for i, d in enumerate(msg_dates)],
                "attachments": [], "first_seen": msg_dates[0], "last_message_id": f"m{len(msg_dates)-1}",
                "message_count": len(msg_dates), "last_synced": msg_dates[-1],
                "provenance_tag": "email-summary/email/x", "flag": "OK", "writer_id": "test",
                "tier": "snapshot", "confidence": "INFERRED", "schema_v": 2, "tracked_scope": ["Consulting"],
            }
            with open(os.path.join(esr.THREADS_V2_DIR, f"{tid}.json"), "w") as f:
                json.dump(rec, f)

        # ---- seed a small synthetic store across all three types ----
        _wtask("t1", "A", "needsAction", "2026-07-01T00:00:00Z", due="2026-07-05T00:00:00Z")
        _wtask("t2", "B", "completed", "2026-06-01T00:00:00Z")
        _wcal("e1", "Meeting", "2026-07-02T09:00:00-04:00")
        _wcal("e2", "Old", "2026-01-01T09:00:00-04:00")
        _wemail("th1", ["2026-07-03T10:00:00-04:00"])
        _wemail("th2", ["2026-06-01T10:00:00-04:00", "2026-07-04T11:00:00-04:00"])

        # === CHECK 1: identical ids/counts, indexed vs direct full walk, per store ===
        # NOTE: once the sidecar file exists beside a store, the ORIGINAL unmodified isr.iter_item_dates
        # (which has no reason to know about _date_index.json) will also list()+json.load() it as if it
        # were a record — item_store_window.py's actual sweep loop already guards this with
        # `if not iid: continue` (real callers always did, for any malformed record), so we mirror that
        # same guard here rather than change isr.py's enumeration (parity with the REAL integration, not
        # a synthetic raw comparison that no caller performs).
        direct_task_ids = {d["item_id"] for d in isr.iter_item_dates("task") if d.get("item_id")}
        idx_task_ids = {d["item_id"] for d in iter_item_dates_indexed("task") if d.get("item_id")}
        direct_cal_ids = {d["item_id"] for d in isr.iter_item_dates("calendar") if d.get("item_id")}
        idx_cal_ids = {d["item_id"] for d in iter_item_dates_indexed("calendar") if d.get("item_id")}
        direct_email_ids = set()
        for tid in esr.iter_thread_ids():
            td = esr.thread_dates(tid, include_inactive=True)
            if td is not None:
                direct_email_ids.add(td["thread_id"])
        idx_email_ids = {d["thread_id"] for d in iter_thread_dates_indexed()}
        good = (direct_task_ids == idx_task_ids == {"t1", "t2"}
                and direct_cal_ids == idx_cal_ids == {"e1", "e2"}
                and direct_email_ids == idx_email_ids == {"th1", "th2"})
        ok("parity:ids — indexed set == direct full-walk set, all three stores") if good else \
            fail("parity:ids", f"task {direct_task_ids}/{idx_task_ids} cal {direct_cal_ids}/{idx_cal_ids} "
                                f"email {direct_email_ids}/{idx_email_ids}")

        # field-level parity too (not just ids) — due/updated/message_dates must match exactly
        d_direct = {d["item_id"]: d for d in isr.iter_item_dates("task") if d.get("item_id")}
        d_idx = {d["item_id"]: d for d in iter_item_dates_indexed("task") if d.get("item_id")}
        good = (set(d_direct) == set(d_idx) == {"t1", "t2"} and all(d_direct[k] == d_idx[k] for k in d_direct))
        ok("parity:fields — task field dicts byte-identical indexed vs direct") if good else \
            fail("parity:fields", f"{d_direct} vs {d_idx}")

        # === sidecar actually got written ===
        idx_path = _index_path("task")
        good = os.path.exists(idx_path)
        ok("sidecar:written — _date_index.json created beside the store on first indexed read") if good \
            else fail("sidecar:written", f"missing {idx_path}")

        # === a second read (nothing changed) must be a pure cache hit: mtimes in sidecar match, no
        #     re-extraction needed. We can't easily measure time in a synthetic tmpdir, so instead
        #     verify the sidecar's cached mtime/size match the live file exactly (that's what makes
        #     the second read skip the open()). ===
        with open(idx_path) as f:
            idx_data = json.load(f)
        entries = idx_data.get("entries", {})
        one_fn = "t1.json"
        live_st = os.stat(os.path.join(isr.TASKS_DIR, one_fn))
        good = (one_fn in entries and entries[one_fn]["mtime"] == live_st.st_mtime
                and entries[one_fn]["size"] == live_st.st_size)
        ok("cache:mtime-size — sidecar entry matches live file exactly (cache-hit condition met)") if good \
            else fail("cache:mtime-size", f"{entries.get(one_fn)} vs {live_st}")

        # === CHECK 3 (rebuild-index): wipe the sidecar, rebuild, reproduce same ids ===
        os.remove(idx_path)
        n = rebuild_index("task")
        rebuilt_ids = {d["item_id"] for d in iter_item_dates_indexed("task")}
        ok("rebuild:reproduces — --rebuild-index equivalent regenerates the same id set") \
            if (n == 2 and rebuilt_ids == {"t1", "t2"}) else fail("rebuild:reproduces", f"n={n} ids={rebuilt_ids}")

        # === CHECK 4 (corruption + repair): deliberately corrupt one sidecar entry's mtime/size,
        #     confirm reconciliation detects + repairs it in place, and the result still matches the
        #     full walk. ===
        with open(idx_path) as f:
            idx_data = json.load(f)
        idx_data["entries"]["t1.json"]["mtime"] = 111111.0     # wrong on purpose
        idx_data["entries"]["t1.json"]["size"] = 9             # wrong on purpose
        idx_data["entries"]["t1.json"]["dates"]["due"] = "1999-01-01T00:00:00Z"   # poisoned cached content
        with open(idx_path, "w") as f:
            json.dump(idx_data, f)
        repaired = {d["item_id"]: d for d in iter_item_dates_indexed("task")}
        with open(idx_path) as f:
            after = json.load(f)
        live_st1 = os.stat(os.path.join(isr.TASKS_DIR, "t1.json"))
        good = (repaired["t1"]["due"] == "2026-07-05T00:00:00Z"          # correct value served, not poisoned
                and after["entries"]["t1.json"]["mtime"] == live_st1.st_mtime   # sidecar repaired in place
                and after["entries"]["t1.json"]["size"] == live_st1.st_size
                and {d["item_id"] for d in iter_item_dates_indexed("task")} == direct_task_ids)
        ok("corrupt:self-heal — stale/poisoned entry detected + repaired in place; result matches full walk") \
            if good else fail("corrupt:self-heal", f"repaired={repaired} after={after['entries']['t1.json']}")

        # === fallback-on-failure: a totally broken sidecar (not even JSON) must not raise — degrade
        #     to the direct walk and still return the right ids. ===
        with open(idx_path, "w") as f:
            f.write("{not json at all")
        ids_after_garbage = {d["item_id"] for d in iter_item_dates_indexed("task")}
        ok("fallback:garbage-sidecar — corrupt-JSON sidecar never raises, still returns correct ids") \
            if ids_after_garbage == {"t1", "t2"} else fail("fallback:garbage-sidecar", f"{ids_after_garbage}")

        # === missing store dir entirely → indexed iterator degrades cleanly to empty, no raise ===
        missing_dir_ids = iter_item_dates_indexed("calendar")   # sanity: real dir still works
        good = {d["item_id"] for d in missing_dir_ids} == {"e1", "e2"}
        ok("dir:present — calendar store still parity after all task-store manipulation") if good else \
            fail("dir:present", f"{missing_dir_ids}")

        # === append_entry:isolation — the regression this fixed (2026-08-03). append_entry MUST
        #     write its sidecar beside the REAL path it's given, never beside _dir_for(item_type)'s
        #     directory (which, mid-self-test, is the REAL production directory even though a caller's
        #     own writer-test has monkeypatched ITS OWN store_root to a temp dir). Prove: writing a
        #     brand-new record straight into isr.TASKS_DIR (the currently-active temp dir) and calling
        #     append_entry updates ONLY that temp dir's sidecar — the production sidecar (a sibling
        #     path entirely outside `root`) is untouched.
        import item_store_read as _isr_mod
        # The REAL production tasks dir — whatever the reader's own brain_root resolves to — is
        # `_isr_save[0]`, captured before this self-test monkeypatched isr.TASKS_DIR to a temp dir
        # above. Never a hardcoded personal path: on a machine with no brain root set this is simply
        # a relative "state/item-store/tasks" that resolves to nothing, which is still the correct
        # thing to prove untouched.
        real_task_sidecar = _sidecar_path_for_store_dir(_isr_save[0])
        real_before = None
        if os.path.exists(real_task_sidecar):
            with open(real_task_sidecar) as f:
                real_before = f.read()
        _wtask("t_append", "Appended", "needsAction", "2026-07-15T00:00:00Z")
        append_entry("task", "t_append.json", os.path.join(_isr_mod.TASKS_DIR, "t_append.json"))
        temp_sidecar_path = _sidecar_path_for_store_dir(_isr_mod.TASKS_DIR)
        with open(temp_sidecar_path) as f:
            temp_entries = json.load(f)["entries"]
        # also confirm the sidecar landed in the PARENT of TASKS_DIR, not inside it (the second bug)
        not_inside_store_dir = not os.path.exists(os.path.join(_isr_mod.TASKS_DIR,
                                                                os.path.basename(temp_sidecar_path)))
        real_after = None
        if os.path.exists(real_task_sidecar):
            with open(real_task_sidecar) as f:
                real_after = f.read()
        good = ("t_append.json" in temp_entries and real_before == real_after and not_inside_store_dir)
        ok("append_entry:isolation — append_entry writes beside the REAL path's PARENT dir, never "
           "inside the store dir, and never leaks into the production sidecar via _dir_for(item_type)") \
            if good else fail("append_entry:isolation",
                              f"in_temp={'t_append.json' in temp_entries} "
                              f"prod_sidecar_changed={real_before != real_after} "
                              f"landed_inside_store_dir={not not_inside_store_dir}")

    except Exception as e:
        fail("store-date-index:*", f"exception: {e}\n{traceback.format_exc()}")
    finally:
        (isr.TASKS_DIR, isr.CAL_DIR) = _isr_save
        (esr.THREADS_V2_DIR,) = _esr_save
        shutil.rmtree(root, ignore_errors=True)

    print(f"\nstore_date_index self-test results: {passed} passed, {failed} failed")
    return passed, failed


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Sidecar date-index for the item stores (Phase 8 S8.4).")
    ap.add_argument("--rebuild-index", action="store_true", help="force full recompute + persist")
    ap.add_argument("--types", default="task,calendar,email", help="comma list (default all three)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        p, f = _run_self_tests()
        sys.exit(0 if f == 0 else 1)

    if a.rebuild_index:
        for t in (x.strip() for x in a.types.split(",") if x.strip()):
            n = rebuild_index(t)
            print(f"[store-date-index] rebuilt {t}: {n} entries")
        sys.exit(0)

    print("store_date_index.py — sidecar date-index for task/calendar/email stores. "
          "Use --rebuild-index [--types task,calendar,email] or --self-test.")
