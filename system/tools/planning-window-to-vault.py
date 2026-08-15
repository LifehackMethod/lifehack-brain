#!/usr/bin/env python3
"""planning-window-to-vault.py — fill the weekly deep-mine's VAULT from the CENTRAL LIBRARY (F.2.p).

The weekly deep-mine (`planning-weekly-analyze-run.sh`) reads a vault directory
`desks/cal/state/weekly-vault/YYYY-Www/` (calendar.json, tasks.json, _manifest.json, per-thread
inbox|sent/{tid}_first.txt/_last.txt). This producer fills that vault contract from the library —
`item_store_window.read_window` (windowing), `item_store_read.read_item` (task/calendar secure
payload), `email_service_read.thread_messages` (first/last email bodies) — never a bespoke
Gmail/gws scrape. Stage-2 (planning-weekly-analyze-run.sh) and the vault SHAPE are unaffected by which
producer fills it; only the source is the library.

⚖ PORT NOTE: donor's history here (a retired bespoke `cal-vault-weekly-pull.py` this replaced) is
dropped — that predecessor is explicitly excluded from this port (dead code, superseded). This file
IS the live producer and is a straight functional port; only the data-root resolution changed (see
below) — the algorithm, the HITL-note flywheel, and the freshness gate are unmodified.

WHY this is safe (grounded in system/information-ingestion-interpretation.md):
  • NO-LLM PLUMBING. This module only windows + copies + writes files; it never interprets/judges.
  • It composes only the sanctioned adapters — `item_store_window.read_window` (windowing),
    `item_store_read.read_item` (task/calendar secure payload), `email_service_read.thread_messages`
    (first/last email bodies). All adversarial-content handling (injection re-scan, REFUSE-flagged,
    tamper-detect) is INHERITED; the store holds a faithful cleared copy so a flagged item is WRITTEN
    to the vault (using its stored cleared text) and COUNTED in the manifest with flagged=True
    (no silent loss — pre-mortem FM3). Only items with no body at all are skipped.
  • Freshness gate (pre-mortem FM4/FM6): the store's freshness + email coverage are stamped into the
    manifest; a stale store raises a loud banner so a downstream reader knows the picture may be old.
  • Calendar comes from the library too (the email window's ±90d recurring-instance expansion) — no
    live-Google workaround.

Per-file adversarial banner (pre-mortem FM8): every produced email/free-text file carries the
adapters' MARKER banner so the deep-mine treats it as DATA, not instructions.

CLI:
  python3 planning-window-to-vault.py --week 2026-W28 [--out-suffix -lib] [--out-dir PATH]
  python3 planning-window-to-vault.py            (defaults to the current ISO week)
  python3 planning-window-to-vault.py --self-test
"""

import argparse
import datetime
import json
import os
import re
import sys

CODE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.join(CODE_ROOT, "shared", "tools") not in sys.path:
    sys.path.insert(0, os.path.join(CODE_ROOT, "shared", "tools"))
if os.path.join(CODE_ROOT, "shared") not in sys.path:
    sys.path.insert(0, os.path.join(CODE_ROOT, "shared"))

import item_store_window as isw          # noqa: E402
import item_store_read as isr            # noqa: E402
import email_service_read as esr         # noqa: E402
import hitl_note_store as hns            # noqa: E402
import brain_root                        # noqa: E402

# The data root, through the ONE resolver — never a hardcoded personal Drive path. NOT-SET is a
# real answer (None, None); every caller below treats a missing root as "nothing to build", not a
# guess at where to write.
_ROOT_SOURCE, DRIVE = brain_root.resolve_brain_root()
# ⚠ The DATA PATH is deliberately still `desks/cal/`. This desk's code, tools, jobs and tiles are
# renamed to `planning`; the records directory is NOT, because moving the operator's live records is
# his decision and has not been taken. KNOWN, INTENTIONAL split — do not "complete" it without his word.
VAULT_ROOT = os.path.join(DRIVE, "desks", "cal", "state", "weekly-vault") if DRIVE else None

# Known free-text keys the adapters render into read_item's `content` blob (as "key: value" lines).
# Splitting ONLY at these known key-starts preserves multi-line values (a description with newlines).
_FREE_KEYS = ("summary", "description", "location", "organizer", "calendar_name",
              "title", "notes", "list_title")
_FREE_RE = re.compile(r"(?m)^(" + "|".join(_FREE_KEYS) + r"): ")


def _parse_freetext(content):
    """Parse read_item's marker-wrapped free-text `content` blob back into a {key: value} dict.
    Strips the MARKER banner first; splits only at known-key line starts so multi-line values survive."""
    if not content:
        return {}
    body = content
    if body.startswith(isr.MARKER):
        body = body[len(isr.MARKER):].lstrip("\n")
    out, matches = {}, list(_FREE_RE.finditer(body))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        out[m.group(1)] = body[m.end():end].strip()
    return out


def _week_bounds(week=None, ref=None):
    """Return (monday_date, sunday_date, 'YYYY-Www'). `week`='2026-W28' or default = ref's ISO week."""
    if week:
        y = int(week[:4])
        w = int(week.split("W")[1])
        monday = datetime.date.fromisocalendar(y, w, 1)
    else:
        ref = ref or datetime.date.today()
        monday = ref - datetime.timedelta(days=ref.weekday())
    sunday = monday + datetime.timedelta(days=6)
    iy, iw, _ = monday.isocalendar()
    return monday, sunday, f"{iy}-W{iw:02d}"


def _email_file_text(subject, msg):
    """Deep-mine `_first.txt`/`_last.txt` shape: adversarial banner, then Subject/From/Date, then body."""
    body = msg.get("body", "") or ""
    if body.startswith(esr.MARKER):
        body = body[len(esr.MARKER):].lstrip("\n")
    return (f"{esr.MARKER}\n\nSubject: {subject}\nFrom: {msg.get('from','')}\n"
            f"Date: {msg.get('date','')}\n\n{body}")


# ---------------------------------------------------------------------------
# HITL-note flywheel (Phase D) — the vault's consuming side.
#
# This producer is NO-LLM PLUMBING (it windows + copies + writes files); the note lookup below is
# the same deterministic-code pattern item_store_window.py's `_secure()` already uses for bundle mode
# — hash/read/decide, never interpret. Wiring it HERE (not just in item_store_window) matters because
# this producer bypasses read_window's own per-item secure fetch (it re-fetches raw content itself via
# isr.read_item / esr.thread_messages for the vault's bespoke shape), so read_window's hitl_verdict
# annotation never reaches the actual served content unless this producer also consults the store.
# ---------------------------------------------------------------------------

def _hitl_lookup(item_type, item_id, desk=""):
    """Consult the HITL note store for one item. Returns (verdict, note, delta_ids). Any failure (no
    note, load error) degrades to ("NO_NOTE", None, []) — the safe else-branch: fresh-mine the raw
    item exactly as before this wiring existed."""
    try:
        note = hns.read_note(item_type, item_id)
        if note is None:
            return "NO_NOTE", None, []
        raw = hns._load_raw(item_type, item_id, desk=desk)
        verdict, delta = hns.decide_read(note, raw, source=item_type)
        return verdict, note, (delta or [])
    except Exception:
        return "NO_NOTE", None, []


def _hitl_render_if_clean(note):
    """Scan BOTH halves of a note (human_confirmed + provisional — a hostile human_confirmed is as
    dangerous as a poisoned provisional) for injection; fail-closed. Returns the rendered note text
    if the scanner is present, ran clean, and found nothing; else None (caller keeps the raw item —
    a note is NEVER served unscanned)."""
    hc = (note.get("human_confirmed") or {}).get("text", "")
    prov = note.get("provisional", "")
    combined = "\n".join(t for t in (hc, prov) if t)
    scanner = getattr(isr, "_scan_for_injection", None)
    if scanner is None or not combined:
        return None
    try:
        clean = not scanner(combined)
    except Exception:
        clean = False   # scanner errored → fail-closed (serve the raw item)
    return hns.render_note(note) if clean else None


def build(week=None, out_dir=None, out_suffix="", ref=None):
    """Fill the vault for a week from the library. Returns the manifest dict (also written to disk)."""
    if not out_dir and not DRIVE:
        raise SystemExit(
            "no data root is set, so there is nowhere to build the vault into.\n"
            "Set it once:  python3 shared/brain_root.py --set \"<the folder your notes live in>\"")
    monday, sunday, label = _week_bounds(week, ref)
    vault = out_dir or os.path.join(VAULT_ROOT, label + out_suffix)
    inbox_dir = os.path.join(vault, "inbox")
    sent_dir = os.path.join(vault, "sent")
    snoozed_dir = os.path.join(vault, "snoozed")
    for d in (vault, inbox_dir, sent_dir, snoozed_dir):
        os.makedirs(d, exist_ok=True)

    # Per-type windows (match the bespoke pull): calendar Mon-7d..Sun+7d; email+tasks the week itself.
    cal_since = (monday - datetime.timedelta(days=7)).isoformat()
    cal_until = (sunday + datetime.timedelta(days=8)).isoformat()   # Sun+7d inclusive → +8 exclusive
    wk_since = monday.isoformat()
    wk_until = (sunday + datetime.timedelta(days=1)).isoformat()

    flagged = []   # every excluded (adversarial/tampered) item — surfaced, never silently dropped

    # ---- calendar → {window, events} ----
    events = []
    hitl_served = hitl_seen = 0
    cal_res = isw.read_window(cal_since, cal_until, item_types=("calendar",))
    for it in cal_res["items"]:
        r = isr.read_item("calendar", it["item_id"], isolate=False, include_inactive=True)
        _is_flagged = r["flag"] in ("REFUSED-FLAGGED", "STORE-TAMPERED")
        if _is_flagged:
            flagged.append({"type": "calendar", "id": it["item_id"], "flag": r["flag"]})
        s = r.get("structured", {})
        ft = _parse_freetext(r.get("content", ""))
        # HITL note flywheel (Phase D): a hash-unchanged item is served from its human-annotated NOTE
        # instead of re-mined from the raw description — the compounding half of the flywheel. Only
        # the deep free-text (`description`) is swapped; `summary`/`location`/structured fields stay
        # raw (cheap, needed for identification regardless of annotation state).
        verdict, note, _delta = ("NO_NOTE", None, []) if _is_flagged else _hitl_lookup("calendar", it["item_id"])
        hitl_seen += 1 if verdict != "NO_NOTE" else 0
        served = False
        if verdict == "NOTE_ONLY":
            rendered = _hitl_render_if_clean(note)
            if rendered is not None:
                ft["description"] = rendered
                served = True
                hitl_served += 1
        events.append({
            "calendar_id": s.get("calendar_id", ""), "start": s.get("start", ""),
            "end": s.get("end", ""), "summary": ft.get("summary", ""),
            "location": ft.get("location", ""), "description": ft.get("description", ""),
            "status": s.get("status", ""), "is_recurring": s.get("is_recurring", False),
            "recurring_event_id": s.get("recurring_event_id", ""), "flagged": _is_flagged,
            "hitl_verdict": verdict, "hitl_served": served,
        })
    with open(os.path.join(vault, "calendar.json"), "w") as f:
        json.dump({"window": [cal_since, cal_until], "events": events}, f, indent=1)

    # ---- tasks → {lists:[{title, tasks:[...]}]} (grouped by list) ----
    lists = {}
    task_res = isw.read_window(wk_since, wk_until, item_types=("task",), task_mode="touched-due-open")
    for it in task_res["items"]:
        r = isr.read_item("task", it["item_id"], isolate=False, include_inactive=True)
        _is_flagged = r["flag"] in ("REFUSED-FLAGGED", "STORE-TAMPERED")
        if _is_flagged:
            flagged.append({"type": "task", "id": it["item_id"], "flag": r["flag"]})
        s = r.get("structured", {})
        ft = _parse_freetext(r.get("content", ""))
        # HITL note flywheel (Phase D) — same pattern as calendar: a hash-unchanged task is served
        # from its NOTE (the `notes` field), not re-mined from the raw item.
        verdict, note, _delta = ("NO_NOTE", None, []) if _is_flagged else _hitl_lookup("task", it["item_id"])
        hitl_seen += 1 if verdict != "NO_NOTE" else 0
        served = False
        if verdict == "NOTE_ONLY":
            rendered = _hitl_render_if_clean(note)
            if rendered is not None:
                ft["notes"] = rendered
                served = True
                hitl_served += 1
        lid = s.get("list_id", "") or "unknown"
        lst = lists.setdefault(lid, {"id": lid, "title": ft.get("list_title", "") or lid, "tasks": []})
        lst["tasks"].append({
            "title": ft.get("title", ""), "notes": ft.get("notes", ""), "due": s.get("due", ""),
            "status": s.get("status", ""), "parent": s.get("parent", ""),
            "position": s.get("position", ""), "when": it.get("when_field", ""), "flagged": _is_flagged,
            "hitl_verdict": verdict, "hitl_served": served,
        })
    task_lists = [dict(v, total=len(v["tasks"]), kept=len(v["tasks"]), truncated=False, full_pull=True)
                  for v in lists.values()]
    total_tasks = sum(len(v["tasks"]) for v in lists.values())
    with open(os.path.join(vault, "tasks.json"), "w") as f:
        json.dump({"lists": task_lists}, f, indent=1)

    # ---- email → inbox/sent per-thread first+last text files ----
    n_inbox = n_sent = 0
    hitl_delta_applied = 0
    em_res = isw.read_window(wk_since, wk_until, item_types=("email",))
    for it in em_res["items"]:
        tid = it["item_id"]
        tm = esr.thread_messages(tid, include_inactive=True)
        if tm is None:
            continue
        _em_flagged = tm.get("flag") != "OK"
        if not tm.get("first"):
            # No body available at all — nothing to write regardless of flag status.
            flagged.append({"type": "email", "id": tid, "flag": tm.get("flag", "NO-BODY")})
            continue
        if _em_flagged:
            # Flagged but body present (cleared copy in store) — record in telemetry, still write.
            flagged.append({"type": "email", "id": tid, "flag": tm.get("flag")})
        labels = [str(l).upper() for l in tm.get("labels", [])]
        dest, is_sent = (sent_dir, True) if "SENT" in labels else (inbox_dir, False)
        subj = tm.get("subject", "")
        first_txt = _email_file_text(subj, tm["first"])
        last_txt = _email_file_text(subj, tm["last"] or tm["first"])
        # HITL note flywheel (Phase D) — the ONLY multi-constituent source (per-message segments), so
        # this is where `hitl_delta` is actually consumed, not just `hitl_verdict`:
        #   NOTE_ONLY    — the whole thread is unchanged since annotation: serve the NOTE in place of
        #                  BOTH first/last (no raw re-mine at all).
        #   DELTA_APPEND — the noted constituents are a clean subset of live (a genuine new reply
        #                  landed): serve the NOTE for `first` (the already-annotated old context,
        #                  cheap) and keep `last` RAW — mine ONLY the new segment, per hitl_delta.
        #   anything else (FULL_REMINE / ORPHANED / NO_NOTE) — unchanged: both files raw, as before
        #                  this wiring existed (the safe else-branch).
        verdict, note, delta = "NO_NOTE", None, []
        if not _em_flagged:
            note = hns.read_note("email", tid)
            if note is not None:
                raw = hns._load_raw("email", tid)
                verdict, delta = hns.decide_read(note, raw, source="email")
                delta = delta or []
        hitl_seen += 1 if verdict != "NO_NOTE" else 0
        if verdict == "NOTE_ONLY":
            rendered = _hitl_render_if_clean(note)
            if rendered is not None:
                note_txt = f"{esr.MARKER}\n\nSubject: {subj}\n\n{rendered}"
                first_txt = last_txt = note_txt
                hitl_served += 1
        elif verdict == "DELTA_APPEND":
            rendered = _hitl_render_if_clean(note)
            if rendered is not None and delta:
                # `last` is served raw only if it is actually among the new constituents `decide_read`
                # flagged (checked against the RAW record's own message_id — `tm`'s first/last carry
                # no id at all) — else there's nothing new to mine and NOTE_ONLY-style serving is still
                # safe (defensive; decide_read's DELTA_APPEND already implies the newest message is new,
                # but never assume — check the id against the raw record directly).
                msgs = (raw or {}).get("messages", []) or []
                last_mid = str(msgs[-1].get("message_id", "")) if msgs else ""
                if not last_mid or last_mid in delta:
                    first_txt = f"{esr.MARKER}\n\nSubject: {subj}\n\n{rendered}"
                    hitl_delta_applied += 1
        with open(os.path.join(dest, f"{tid}_first.txt"), "w") as f:
            f.write(first_txt)
        with open(os.path.join(dest, f"{tid}_last.txt"), "w") as f:
            f.write(last_txt)
        n_sent += is_sent
        n_inbox += (not is_sent)

    # ---- freshness gate (FM4/FM6) ----
    try:
        item_status, item_reasons, _ = isr.freshness_check(write_tile=False)
    except Exception as e:
        item_status, item_reasons = "UNKNOWN", [f"freshness_check error: {e}"]
    try:
        email_stale = esr._store_is_stale()
    except Exception:
        email_stale = True
    stale = (item_status != "OK") or email_stale

    # ---- orphan-reaper (D6, the sweep side) — hosted here, the weekly sweep, no dedicated cron.
    # MARKS (never deletes) any note whose source item has vanished since it was written; a status
    # flip only (content_hash/constituents/provisional/human_confirmed all carried forward byte-
    # identical) — never breaks the build on error (fail-soft: an empty reap list, not a crash).
    try:
        reaped = hns.reap_orphans()
    except Exception as e:
        reaped = []
        flagged.append({"type": "hitl-reaper", "id": "orphan-sweep", "flag": f"reap-error: {e}"})

    manifest = {
        "week": label, "week_monday": monday.isoformat(), "week_sunday": sunday.isoformat(),
        "anchor_date": datetime.date.today().isoformat(),
        "generated_at": datetime.datetime.now().astimezone().isoformat(),
        "source": "item-store-window",   # blue-green traceability (vs bespoke)
        "scope": {
            "calendar": "Mon-7d .. Sun+7d (library, recurring instances expanded ±90d)",
            "email": "the week (library, windowed on message dates)",
            "tasks": "all open + touched/due in-week (library)",
        },
        "counts": {"calendar": len(events), "tasks": total_tasks,
                   "email_inbox": n_inbox, "email_sent": n_sent},
        "flagged": {"count": len(flagged), "items": flagged},   # written-but-flagged (adversarial/tampered, cleared copy used) — VISIBLE
        "store_freshness": {"item_store": item_status, "item_reasons": item_reasons,
                            "email_stale": email_stale},
        # Phase D flywheel telemetry: how much of THIS build was served from a compounding HITL note
        # vs freshly mined from the raw item, plus the orphan-reaper's sweep result (never destructive).
        "hitl": {"items_with_note": hitl_seen, "served_note_only": hitl_served,
                 "delta_append_applied": hitl_delta_applied, "orphans_reaped": len(reaped),
                 "orphans_reaped_ids": [f"{s}/{n}" for s, n in reaped]},
    }
    if stale:
        manifest["STALE_WARNING"] = ("⚠ the library was STALE/degraded at pull time — this vault may be "
                                     "behind live Google; verify anything load-bearing.")
    with open(os.path.join(vault, "_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    return manifest


# ---------------------------------------------------------------------------
# Self-test: build the CURRENT-vault-equivalent for a real week into a temp dir, assert structure.
# (The full end-to-end proof is the live run + the blue-green PROVE gate; this catches structural breaks.)
# ---------------------------------------------------------------------------

def _run_self_tests(week="2026-W28"):
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

    # unit: free-text parser handles multi-line values + a leading marker
    try:
        blob = isr.MARKER + "\n\nsummary: Weekly standup\ndescription: line one\nline two\nlocation: HQ"
        ft = _parse_freetext(blob)
        good = (ft.get("summary") == "Weekly standup" and ft.get("location") == "HQ"
                and "line two" in ft.get("description", ""))
        ok("parse:freetext — marker stripped, multi-line description preserved") if good \
            else fail("parse:freetext", f"{ft}")
    except Exception as e:
        fail("parse:freetext", f"{e}")

    # integration: build a real week into a temp dir and validate the vault contract
    root = tempfile.mkdtemp(prefix="c2v_")
    try:
        m = build(week=week, out_dir=root)
        cal = json.load(open(os.path.join(root, "calendar.json")))
        tasks = json.load(open(os.path.join(root, "tasks.json")))
        man = json.load(open(os.path.join(root, "_manifest.json")))

        ok("build:calendar-shape — {window, events[]} with summaries") \
            if (isinstance(cal.get("events"), list) and "window" in cal
                and (not cal["events"] or "summary" in cal["events"][0])) \
            else fail("build:calendar-shape", f"{list(cal.keys())}")
        ok("build:tasks-shape — {lists[]} grouped, tasks carry title") \
            if (isinstance(tasks.get("lists"), list)
                and all("tasks" in L for L in tasks["lists"])) \
            else fail("build:tasks-shape", f"{list(tasks.keys())}")
        ok("build:manifest — source=item-store-window + counts + flagged + freshness") \
            if (man.get("source") == "item-store-window" and "counts" in man
                and "flagged" in man and "store_freshness" in man) \
            else fail("build:manifest", f"{man.get('source')}")

        # flagged items should be WRITTEN to the vault (not dropped) and counted in the manifest
        ok("build:flagged-counted — flagged items written to vault, counted in manifest") \
            if isinstance(man["flagged"]["count"], int) \
            else fail("build:flagged-counted", f"flagged.count not an int: {man.get('flagged')}")

        # email files exist + carry the adversarial banner
        import glob
        firsts = glob.glob(os.path.join(root, "inbox", "*_first.txt")) + \
            glob.glob(os.path.join(root, "sent", "*_first.txt"))
        banner_ok = True
        if firsts:
            txt = open(firsts[0]).read()
            banner_ok = esr.MARKER in txt and "Subject:" in txt
        ok(f"build:email-files — {len(firsts)} first.txt written, carry banner+Subject") if banner_ok \
            else fail("build:email-files", "email file missing banner/Subject")

        print(f"\n  [live counts for {week}] {man['counts']}  flagged={man['flagged']['count']}  "
              f"fresh={man['store_freshness']['item_store']}")
    except Exception as e:
        fail("build:*", f"{e}\n{traceback.format_exc()}")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print(f"\nplanning-window-to-vault self-test results: {passed} passed, {failed} failed")
    return passed, failed


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        p, f = _run_self_tests()
        sys.exit(0 if f == 0 else 1)
    ap = argparse.ArgumentParser(description="Fill the weekly deep-mine vault from the central library.")
    ap.add_argument("--week", help="ISO week 'YYYY-Www' (default: current ISO week)")
    ap.add_argument("--out-dir", help="explicit vault dir (default: weekly-vault/<week><suffix>)")
    ap.add_argument("--out-suffix", default="", help="suffix on the week dir, e.g. -lib for a PROVE sibling")
    a = ap.parse_args()
    if not a.out_dir and not DRIVE:
        sys.stderr.write(
            "no data root is set, so there is nowhere to build the vault into.\n"
            "Set it once:  python3 shared/brain_root.py --set \"<the folder your notes live in>\"\n")
        sys.exit(2)
    man = build(week=a.week, out_dir=a.out_dir, out_suffix=a.out_suffix)
    print(json.dumps({k: v for k, v in man.items() if k != "flagged"}, indent=1))
    print(f"flagged (written+flagged=True, counted): {man['flagged']['count']}")
    sys.exit(0)
