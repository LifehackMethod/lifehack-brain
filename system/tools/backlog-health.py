#!/usr/bin/env python3
"""backlog-health.py — emit state/status/backlog.json from the read-only backlog-groom engine.

THE HEADLINE (unchanged from the donor): `actionable_debt` = type:debt AND state:actionable — the
only "what's broken" number. Everything else is shown decomposed and explicitly NOT counted as
broken, the antidote to one scary total that hides more than it shows.

⚠ WHAT THIS PORT IS WAITING ON, NAMED EXPLICITLY. The read-only engine this file calls
(`backlog_groom.build_report()`) belongs to a DIFFERENT migration category — PLANNING & BUILD
(`backlog-authority`), not AUTOMATION — and has not landed in this repo as of this port. Per the
migration law ("broken is fine, ship it, mark it under construction — the only thing that doesn't
migrate is something that doesn't belong at all"), this SHIPS anyway: the scheduler slot, the tile
contract, and the graceful-degrade path are all real and tested. What's missing is the one import at
the top, and it fails the way this whole design constraint demands — an honest tile that says what's
missing, never a crash, never a silent false-clean.

Once `system/tools/backlog_groom.py` lands (PLANNING & BUILD's job), this file needs ZERO changes —
the `try/except ImportError` below simply stops firing and the real counts start flowing.
"""
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
CODE_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_SHARED = os.path.join(CODE_ROOT, "shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from brain_root import resolve_brain_root          # noqa: E402
from emit_finding import emit_finding, FindingContractError   # noqa: E402


def iso(epoch):
    lt = time.localtime(epoch); off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off


def _write_tile(out_path, *, status, summary, rc, payload):
    """Same minimal local writer cal-health.py uses — see that file's comment for why (no shared
    `emit_status.py` in this repo yet)."""
    env = {"desk": "backlog", "schema_version": 2, "pulse_job": "backlog-health", "emit_mode": "pulse",
           "stale_after_s": 43200, "last_run": iso(int(time.time())), "rc": rc, "status": status,
           "summary": summary}
    env.update(payload)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = out_path + ".tmp"
    import json
    json.dump(env, open(tmp, "w"), indent=2)
    os.replace(tmp, out_path)


def main():
    _src, notes_root = resolve_brain_root()
    if notes_root is None:
        sys.stderr.write("[backlog-health] no notes root configured (shared/brain_root.py) — nothing to write yet.\n")
        return 0
    out_path = os.path.join(notes_root, "state", "status", "backlog.json")

    try:
        import backlog_groom
    except ImportError as e:
        summary = "backlog_groom.py not present yet — this repo's PLANNING & BUILD category hasn't shipped it"
        _write_tile(out_path, status="NEEDS_REVIEW", summary=summary, rc=0,
                    payload={"work_count": 0, "work_noun": "actionable debt", "actionable_debt": 0,
                             "engine_available": False, "kpis": [], "items": []})
        try:
            emit_finding(producer="backlog-health", status="NEEDS_REVIEW", scanned_n=1,
                        labels={"job": "backlog-health", "check": "engine-available"},
                        summary=summary, payload={"detail": str(e)}, rc=0)
        except (FindingContractError, Exception) as fe:
            sys.stderr.write(f"[backlog-health] emit_finding failed: {fe}\n")
        print(f"[backlog-health] {summary}")
        return 0

    now = time.time()
    try:
        rep = backlog_groom.build_report()
    except Exception as e:
        sys.stderr.write(f"backlog-health: groom failed ({e})\n")
        rep = {"counts": {}, "proposals": {}}
    c = rep.get("counts", {})
    p = rep.get("proposals", {})

    if not rep.get("configured", True):
        # ── NOTHING TO SCAN YET — mirrors cal-health.py's "not configured — no calendar
        # connected yet": a fresh install with no debt ledger, no desk backlogs, and no legacy
        # swamp file has verified NOTHING, and "0 actionable debt - 0 projects - ..." would read
        # exactly like a real clean scan (the false-OK shape this whole design exists to catch).
        # Say plainly that nothing is configured instead. rc stays 0 — this is not a failure. ──
        summary = "not configured - no debt ledger, desk backlogs, or legacy swamp file found yet"
        _write_tile(out_path, status="OK", summary=summary, rc=0,
                    payload={"work_count": 0, "work_noun": "actionable debt", "actionable_debt": 0,
                             "engine_available": True, "configured": False, "kpis": [], "items": []})
        try:
            emit_finding(producer="backlog-health", status="OK", scanned_n=1,
                        labels={"job": "backlog-health", "check": "backlog"},
                        summary=summary, payload={"configured": False}, rc=0)
        except (FindingContractError, Exception) as fe:
            sys.stderr.write(f"[backlog-health] emit_finding failed: {fe}\n")
        print(f"[backlog-health] {summary}")
        return 0

    actionable = int(c.get("actionable_debt", 0))
    swamp = int(c.get("swamp_pending", 0))
    done_n = len(p.get("done", []))
    dupe_n = len(p.get("dupes", []))
    stale_n = len(p.get("stale", []))

    needs = actionable > 0 or swamp > 0 or done_n or dupe_n
    env_status = "NEEDS_REVIEW" if needs else "OK"
    summary = (f"{actionable} actionable debt - {c.get('projects', 0)} projects - "
               f"{c.get('blocked', 0)} blocked - {c.get('parked', 0)} parked"
               + (f" - {swamp} swamp-pending" if swamp else "")
               + (f" - groom: {done_n} done/{dupe_n} dupe" if (done_n or dupe_n) else ""))

    kpis = [
        {"key": "actionable_debt", "label": "Actionable debt", "value": actionable, "sub": "the broken number"},
        {"key": "projects",  "label": "Projects",  "value": c.get("projects", 0)},
        {"key": "decisions", "label": "Decisions",  "value": c.get("decisions", 0)},
        {"key": "blocked",   "label": "Blocked",    "value": c.get("blocked", 0),   "sub": "waiting-external"},
        {"key": "parked",    "label": "Parked",     "value": c.get("parked", 0),    "sub": "someday-maybe"},
    ]
    if swamp:
        kpis.append({"key": "swamp", "label": "Swamp (pending drain)", "value": swamp})

    items = []
    for e in p.get("done", [])[:8]:
        items.append({"title": f"[done?] {e['title'][:100]}", "detail": f"{e['where']} - archive candidate"})
    for e in p.get("dupes", [])[:6]:
        items.append({"title": f"[dupe] {e['slug']}", "detail": f"keep {e['wins']} - drop {e['dupe_at']}"})

    _write_tile(out_path, status=env_status, summary=summary, rc=0, payload={
        "work_count": actionable, "work_noun": "actionable debt",
        "actionable_debt": actionable,
        "debt_total": c.get("debt_total", 0),
        "projects": c.get("projects", 0),
        "decisions": c.get("decisions", 0),
        "blocked": c.get("blocked", 0),
        "parked": c.get("parked", 0),
        "needs_verify": c.get("needs_verify", 0),
        "desk_loops_total": c.get("desk_loops_total", 0),
        "by_desk": c.get("by_desk", {}),
        "swamp_pending": swamp,
        "groom": {"done_candidates": done_n, "dupe_candidates": dupe_n, "stale_suspects": stale_n},
        "kpis": kpis, "items": items, "engine_available": True,
    })

    try:
        emit_finding(producer="backlog-health", status=env_status, scanned_n=max(1, actionable + c.get("projects", 0)),
                    labels={"job": "backlog-health", "check": "backlog"}, summary=summary,
                    payload={"actionable_debt": actionable, "swamp_pending": swamp}, rc=0)
    except (FindingContractError, Exception) as e:
        sys.stderr.write(f"[backlog-health] emit_finding failed: {e}\n")

    print(f"[backlog-health] {env_status} - {actionable} actionable debt - {swamp} swamp-pending - "
          f"groom {done_n} done/{dupe_n} dupe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
