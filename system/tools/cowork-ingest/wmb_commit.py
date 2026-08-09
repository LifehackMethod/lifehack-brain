#!/usr/bin/env python3
"""
wmb_commit.py — the ENFORCED save-and-verify step for world-model-builder.

Council verdict (2026-07-09, lifehack-architecture): persistence must be a
deterministic script the loop is FORCED THROUGH, never a prose rule the LLM is
trusted to remember. This script is that program. It:

  1. writes the per-chat state into the corpus map (the resume/provenance tracker),
  2. appends a ledger row + a receipt (the machine-verifiable audit trail),
  3. READS THE FILE BACK and verifies the write actually landed,
  4. exits NON-ZERO on any verification failure — so a caller that checks the exit
     code / receipt cannot advance on a silent-failed save.

The printed status line is generated FROM THE READ-BACK, never from the write call.
That inversion is what closes the "reported saved when it wasn't" failure mode.

Write order (Dijon's rule): mark a chat `in-flight` with `start` BEFORE its deep-read
is launched, flip it to a terminal status with `save` AFTER the record lands. A crash
then leaves `in-flight` rows that are safe to re-run and terminal rows that are skip-safe.

Cold-restore: read the corpus map → skip terminal rows → requeue `in-flight` + `untouched`.

Usage:
  wmb_commit.py start --map MAP --chat CHAT_ID [--receipts R]
  wmb_commit.py save  --map MAP --chat CHAT_ID --status {filed,pointer-only,deferred,declined}
                      [--record PATH] [--desk DESK] [--note NOTE] [--human-approved]
                      [--ledger LEDGER] [--receipts R]

Terminal statuses (human-set ONLY): filed | pointer-only | deferred | declined
EVERY terminal status REQUIRES --human-approved — ONLY THE HUMAN CLOSES A CHAT (extended 2026-07-10
from declined-only; a machine auto-`filed` a chat the human never ruled).
`noise` is RETIRED (it silently discarded chats). Machine statuses untouched | maybe-skip | in-flight
are written by corpus_map.py init/set/start, never here.
"""
import argparse, json, os, sys, tempfile, datetime

TERMINAL = {"filed", "pointer-only", "deferred", "declined"}  # human-set only; `noise` RETIRED


def _load(path):
    with open(path) as f:
        return json.load(f)


def _atomic_write_json(path, obj):
    """tmp-then-rename so a crash mid-write never leaves a half-file (Tomas's rule)."""
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _rows(cm):
    r = cm.get("rows")
    if not isinstance(r, dict):
        sys.exit("FATAL: corpus map has no 'rows' dict — wrong file?")
    return r


def _receipt(receipts_path, entry):
    log = []
    if os.path.exists(receipts_path):
        try:
            log = json.load(open(receipts_path))
        except Exception:
            log = []
    log.append(entry)
    _atomic_write_json(receipts_path, log)
    # read-back verify the receipt landed
    back = json.load(open(receipts_path))
    if not back or back[-1] != entry:
        sys.exit("FAIL: receipt read-back mismatch — NOT durably logged")
    return len(back)


def cmd_start(a):
    cm = _load(a.map)
    rows = _rows(cm)
    if a.chat not in rows:
        sys.exit(f"FAIL: chat '{a.chat}' not in corpus map")
    rows[a.chat]["filing_status"] = "in-flight"
    if getattr(a, "vein", None):
        rows[a.chat]["vein"] = a.vein
    rows[a.chat]["learned_note"] = "deep-read launched " + _now()
    _atomic_write_json(a.map, cm)
    # READ-BACK VERIFY (status generated from disk, not from the write call)
    disk = _rows(_load(a.map))[a.chat]["filing_status"]
    if disk != "in-flight":
        sys.exit(f"FAIL: read-back says '{disk}', expected 'in-flight' — NOT saved")
    n = _receipt(a.receipts, {"ts": _now(), "chat": a.chat, "action": "start",
                              "status": "in-flight", "verified": True})
    print(f"OK start: {a.chat} -> in-flight (verified on disk) · receipts={n}")


def cmd_save(a):
    if a.status not in TERMINAL:
        sys.exit(f"FAIL: --status must be one of {sorted(TERMINAL)} (human-set terminal rulings)")
    # ONLY THE HUMAN CLOSES A CHAT: EVERY terminal ruling (filed | pointer-only | deferred |
    # declined) is a decision the human made — none may be written without --human-approved, the
    # flag the controller sets ONLY after a human ruled. A forgetful/hijacked subagent that omits
    # it fails closed. (Extended 2026-07-10 from declined-only after a live audit caught the machine
    # auto-`filed`ing a chat the human never ruled. conformance-tested — test_status_gate.py.)
    if not getattr(a, "human_approved", False):
        verb = "ELIMINATES" if a.status == "declined" else "CLOSES"
        sys.exit(f"REFUSED: status '{a.status}' {verb} a chat — it REQUIRES --human-approved "
                 "(set only after a human ruled). Only the human closes a chat.")
    if a.status == "filed" and (not a.record or a.record == "-"):
        sys.exit("FAIL: status 'filed' REQUIRES --record <path> (the durable record)")
    if a.status == "deferred" and (not a.record or a.record == "-") and not a.note:
        sys.exit("FAIL: status 'deferred' REQUIRES a --record pointer or a --note")

    # VALIDATE BEFORE ANY WRITE — a claimed record must exist on disk FIRST, so a
    # bad save can never leave a half-committed 'filed' row in the tracker.
    if a.record and a.record != "-" and not os.path.exists(a.record):
        sys.exit(f"FAIL: --record '{a.record}' does not exist on disk — record was NOT written; map untouched")

    cm = _load(a.map)
    rows = _rows(cm)
    if a.chat not in rows:
        sys.exit(f"FAIL: chat '{a.chat}' not in corpus map")
    row = rows[a.chat]
    row["filing_status"] = a.status
    row["verdict"] = "wmb_commit " + _now()
    if a.record and a.record != "-":
        row["record"] = a.record
    if a.desk:
        row["desk"] = a.desk
    if getattr(a, "vein", None):
        row["vein"] = a.vein
    if a.note:
        row["learned_note"] = a.note
    _atomic_write_json(a.map, cm)

    # READ-BACK VERIFY corpus map
    disk = _rows(_load(a.map))[a.chat]["filing_status"]
    if disk != a.status:
        sys.exit(f"FAIL: read-back says '{disk}', expected '{a.status}' — NOT saved")

    # Ledger append (audit trail) + read-back
    if a.ledger:
        line = f"- [{_now()}] {a.chat} → {a.status}" \
               + (f" · record={a.record}" if a.record and a.record != '-' else "") \
               + (f" · desk={a.desk}" if a.desk else "") \
               + (f" · {a.note}" if a.note else "") + "\n"
        pre = os.path.getsize(a.ledger) if os.path.exists(a.ledger) else 0
        with open(a.ledger, "a") as f:
            f.write(line)
            f.flush(); os.fsync(f.fileno())
        if os.path.getsize(a.ledger) <= pre:
            sys.exit("FAIL: ledger did not grow — append not durable")

    n = _receipt(a.receipts, {"ts": _now(), "chat": a.chat, "action": "save",
                              "status": a.status, "record": a.record or "-",
                              "desk": a.desk or "-", "verified": True})
    print(f"OK save: {a.chat} -> {a.status} (verified on disk) · receipts={n}")


def cmd_arena_close(a):
    """Regenerate the living world-model.md — a human-readable synthesis built
    DETERMINISTICALLY from the corpus map, so it can never silently drift from
    what was actually filed. (The LLM may add narrative on top; this skeleton is
    the durable, always-true artifact.)"""
    cm = _load(a.map)
    rows = _rows(cm)
    from collections import Counter, defaultdict
    counts = Counter(r.get("filing_status", "untouched") for r in rows.values())
    by_desk = defaultdict(list)
    open_items = []
    for f, r in rows.items():
        st = r.get("filing_status", "untouched")
        if st in ("filed", "pointer-only") and r.get("desk"):
            by_desk[r["desk"]].append((f, st, r.get("record", "-"), r.get("learned_note", "")))
        elif st in ("deferred", "in-flight"):
            open_items.append((f, st, r.get("learned_note", "")))

    L = []
    L.append("# World Model — living synthesis")
    L.append("")
    L.append(f"> Regenerated deterministically from `corpus-map.json` by `wmb_commit arena-close` at {_now()}.")
    if a.arena:
        L.append(f"> Last arena closed: **{a.arena}**.")
    L.append("> This is the ALWAYS-TRUE skeleton (what is actually filed). Narrative synthesis may be layered on top.")
    L.append("")
    L.append("## Coverage")
    total = sum(counts.values())
    for k in ("filed", "pointer-only", "declined", "deferred", "in-flight", "maybe-skip", "untouched"):
        if counts.get(k):
            L.append(f"- **{k}**: {counts[k]}")
    L.append(f"- **total chats**: {total}")
    L.append("")
    L.append("## What we know — filed / decided, by desk")
    if by_desk:
        for desk in sorted(by_desk):
            L.append(f"\n### {desk}")
            for f, st, rec, note in sorted(by_desk[desk]):
                rec_s = f" → `{rec}`" if rec and rec != "-" else ""
                L.append(f"- [{st}] {note or f}{rec_s}  ·  src: `{f}`")
    else:
        L.append("_(nothing filed to a desk yet)_")
    L.append("")
    L.append("## Still open (deferred / in-flight — needs a decision or a re-run)")
    if open_items:
        for f, st, note in sorted(open_items):
            L.append(f"- [{st}] {note or ''}  ·  src: `{f}`")
    else:
        L.append("_(nothing open)_")
    L.append("")

    _dir = os.path.dirname(a.map) or "."
    wm = a.world_model or os.path.join(_dir, "world-model.md")
    with open(wm, "w") as fh:
        fh.write("\n".join(L) + "\n")
        fh.flush(); os.fsync(fh.fileno())
    # read-back verify it wrote
    if not os.path.exists(wm) or os.path.getsize(wm) == 0:
        sys.exit("FAIL: world-model.md did not write")
    print(f"OK arena-close: refreshed {wm} ({counts.get('filed',0)} filed, {len(open_items)} open) [verified]")
    # DONE-GATE (Tomas's fitness function): an arena is NOT done while any chat is still machine-only
    # (untouched / maybe-skip / in-flight) — i.e. never human-reviewed. The doc regenerates either way
    # (shows progress); the EXIT CODE is the honest done-signal. "The human sees EVERYTHING."
    not_reviewed = counts.get("untouched", 0) + counts.get("maybe-skip", 0) + counts.get("in-flight", 0)
    if not_reviewed and not getattr(a, "allow_open", False):
        sys.exit(f"NOT DONE: {not_reviewed} chat(s) still un-reviewed by a human "
                 f"(untouched/maybe-skip/in-flight). The human must see EVERY chat before an arena "
                 f"closes. Re-run with --allow-open only to snapshot mid-progress.")


def main():
    p = argparse.ArgumentParser(description="Enforced save-and-verify for world-model-builder")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--map", required=True, help="corpus-map.json path")
        sp.add_argument("--chat", required=True, help="chat id / flattened filename")
        sp.add_argument("--vein", default=None, help="the named vein this chat belongs to (convergence tracking)")
        sp.add_argument("--receipts", default=None, help="receipts json (default: <mapdir>/world-model-receipts.json)")

    s = sub.add_parser("start"); common(s); s.set_defaults(fn=cmd_start)

    v = sub.add_parser("save"); common(v)
    v.add_argument("--status", required=True)
    v.add_argument("--record", default=None)
    v.add_argument("--desk", default=None)
    v.add_argument("--note", default=None)
    v.add_argument("--ledger", default=None)
    v.add_argument("--human-approved", action="store_true",
                   help="REQUIRED for EVERY terminal status: attests a HUMAN ruled this chat's fate")
    v.set_defaults(fn=cmd_save)

    ac = sub.add_parser("arena-close")
    ac.add_argument("--map", required=True, help="corpus-map.json path")
    ac.add_argument("--arena", default=None, help="name of the arena just closed (for the header)")
    ac.add_argument("--world-model", default=None, help="output path (default: <mapdir>/world-model.md)")
    ac.add_argument("--allow-open", action="store_true",
                    help="snapshot mid-progress without failing the human-review done-gate")
    ac.set_defaults(fn=cmd_arena_close, receipts=None)

    a = p.parse_args()
    if getattr(a, "receipts", None) is None and a.cmd != "arena-close":
        a.receipts = os.path.join(os.path.dirname(a.map) or ".", "world-model-receipts.json")
    a.fn(a)


if __name__ == "__main__":
    main()
