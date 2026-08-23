#!/usr/bin/env python3
"""sentinel_ack.py — retire ("acknowledge") Sentinel alerts by setting their disposition.

THE PROBLEM IT SOLVES: a DANGER/FLAG event holds the security status file red until it ages out of
the 24h window — so a false-positive flood (e.g. research agents reading security papers) keeps it
red and the operator starts ignoring it. This is the human "I've seen it, we're good" action: it
flips events from `disposition:"unreviewed"` to a reviewed value, which `sentinel_response.write_status`
treats as NO LONGER ACTIVE — so the status goes clear. The events + their evidence stay in the ledger
as history and feed a false-positive rate.

REVERSIBLE + SAFE: only sets a metadata field (disposition + reviewed_at); never deletes an event.
Idempotent. Atomic ledger rewrite. Reuses sentinel_response's LOG/STATUS paths (so SENTINEL_LOG /
SENTINEL_STATUS env overrides work for testing) and its write_status() so the status file refreshes
instantly.

USAGE:
  sentinel_ack.py                      mark ALL unreviewed events false-positive ("I looked, it's noise")
  sentinel_ack.py --real               ... mark them 'real' (a confirmed attack you've now handled)
  sentinel_ack.py --reviewed           ... mark them 'reviewed' (seen, leaving classification blank)
  sentinel_ack.py --source web         only events from that source
  sentinel_ack.py --item bad.txt       only events whose item EXACTLY equals this (one fixture/file)
  sentinel_ack.py --ts 2026-06-18      only events whose ts starts with this (a day, or one alert)
  sentinel_ack.py --list               show current unreviewed events, change NOTHING (dry run)
  sentinel_ack.py --undo --ts <ts>     set matched events back to 'unreviewed' (revoke an ack)

Disposition values: unreviewed (default on a new event) | false-positive | real | reviewed.
The tile counts ONLY 'unreviewed' as active; any other value = acknowledged/retired.
"""
import sys, os, json, time, argparse

_THIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS)
import sentinel_response as sr   # reuse LOG / STATUS / iso / write_status — one source of truth

REVIEWED = {"false-positive", "real", "reviewed"}


def _load_store():
    """The known-accepted fingerprint store (Window 3) — recurrences of these auto-retire instead of
    re-flooding. sentinel_response.load_acked_fingerprints() reads the same file."""
    try:
        with open(sr.ACKED_FP) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _save_store(store):
    os.makedirs(os.path.dirname(sr.ACKED_FP), exist_ok=True)
    tmp = sr.ACKED_FP + ".tmp"
    with open(tmp, "w") as f:
        json.dump(store, f, indent=2)
    os.replace(tmp, sr.ACKED_FP)


def _load():
    rows = []
    if os.path.exists(sr.LOG):
        with open(sr.LOG) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    rows.append({"_raw": line})   # preserve unparseable lines verbatim, never drop
    return rows


def _matches(e, source, ts_prefix, fp="", only_unreviewed=True, item=""):
    if "_raw" in e:
        return False
    if only_unreviewed and e.get("disposition", "unreviewed") != "unreviewed":
        return False
    if source and e.get("source") != source:
        return False
    if ts_prefix and not str(e.get("ts", "")).startswith(ts_prefix):
        return False
    if fp and e.get("fingerprint") != fp:
        return False
    # --item: EXACT match on the event's item, never a substring. Added 2026-08-05 (T20.1) because
    # --source was too coarse for the real case: `cowork-ingest` held 97 unreviewed DANGER events of
    # which 65 were one synthetic test fixture (`bad.txt`) and 32 were REAL chat files. Acking by
    # source would have retired 32 genuine detections to clear 65 fake ones — the precise inversion
    # of what triage is for. Exact-match (not `in`) so a crafted item string can never widen the
    # sweep: a substring filter is a suppression primitive, an equality filter is a scalpel.
    if item and str(e.get("item", "")) != item:
        return False
    return True


def _fmt(e):
    return (f"  {str(e.get('ts',''))[:19]}  {(e.get('verdict') or '?').upper():6}  "
            f"{(e.get('source') or '?'):14}  fp={(e.get('fingerprint') or '-'):12}  {(e.get('item') or '')[:38]}")


def main():
    ap = argparse.ArgumentParser(description="Retire Sentinel alerts by setting disposition.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--fp", "--false-positive", dest="disp", action="store_const", const="false-positive")
    g.add_argument("--real", dest="disp", action="store_const", const="real")
    g.add_argument("--reviewed", dest="disp", action="store_const", const="reviewed")
    ap.add_argument("--source", default="", help="only events from this source (e.g. web)")
    ap.add_argument("--ts", default="", help="only events whose ts starts with this prefix")
    ap.add_argument("--item", default="", help="only events whose item EXACTLY equals this (not a "
                    "substring) — e.g. a single test fixture, without touching real items from the "
                    "same source")
    ap.add_argument("--fingerprint", default="", help="only events with this fingerprint; on ack, REGISTER "
                    "it in the known-accepted store so its RECURRENCES auto-retire (recurrence-silencing)")
    ap.add_argument("--remember", action="store_true", help="also register the acked events' fingerprints "
                    "in the known-accepted store, so identical findings stay silent in future")
    ap.add_argument("--list", action="store_true", help="show current unreviewed events; change nothing")
    ap.add_argument("--undo", action="store_true", help="set matched events back to 'unreviewed' (and, with "
                    "--fingerprint/--remember, de-register the fingerprint so it can alarm again)")
    a = ap.parse_args()
    disp = a.disp or "false-positive"   # default: the common case is FP noise

    rows = _load()

    # --list: preview the active (unreviewed) board and stop
    if a.list:
        hits = [e for e in rows if _matches(e, a.source, a.ts, a.fingerprint, item=a.item)]
        if not hits:
            print("No unreviewed events match — the active board is clear.")
            return 0
        print(f"{len(hits)} unreviewed event(s)" + (f" [source={a.source}]" if a.source else "")
              + (f" [ts~{a.ts}]" if a.ts else "") + (f" [fp={a.fingerprint}]" if a.fingerprint else "")
              + (f" [item={a.item}]" if a.item else "") + ":")
        for e in hits:
            print(_fmt(e))
        print("\nRetire them with:  sentinel_ack.py"
              + (f" --source {a.source}" if a.source else "") + (f" --ts {a.ts}" if a.ts else "")
              + (f" --fingerprint {a.fingerprint}" if a.fingerprint else "")
              + (f" --item {a.item}" if a.item else "")
              + "   (add --remember to silence recurrences)")
        return 0

    # --undo: re-open acked events (only_unreviewed=False so it can target already-acked ones)
    target_disp = "unreviewed" if a.undo else disp
    changed = 0
    changed_fps = set()
    for e in rows:
        if _matches(e, a.source, a.ts, a.fingerprint, only_unreviewed=not a.undo, item=a.item):
            if e.get("disposition", "unreviewed") != target_disp:
                e["disposition"] = target_disp
                e["reviewed_at"] = None if a.undo else sr.iso(time.time())
                changed += 1
                if e.get("fingerprint"):
                    changed_fps.add(e["fingerprint"])

    # Decide which fingerprints to (de)register in the known-accepted store. --fingerprint always
    # targets its own value (supports PRE-EMPTIVE acking of a fingerprint with no current events);
    # --remember sweeps in every acked event's fingerprint.
    fps_to_persist = set()
    if a.fingerprint:
        fps_to_persist.add(a.fingerprint)
    if a.remember:
        fps_to_persist |= changed_fps

    if changed == 0 and not fps_to_persist:
        print("Nothing to do — no matching events (the board may already be clear).")
        return 0

    # atomic rewrite of the ledger (preserve _raw lines verbatim) — only if events actually changed
    if changed:
        tmp = sr.LOG + ".tmp"
        with open(tmp, "w") as f:
            for e in rows:
                f.write((e["_raw"] if "_raw" in e else json.dumps(e)) + "\n")
        os.replace(tmp, sr.LOG)

    # update the known-accepted fingerprint store (the recurrence-silencer)
    store_msg = ""
    if fps_to_persist:
        store = _load_store()
        if a.undo:
            for fp in fps_to_persist:
                store.pop(fp, None)
            store_msg = f" De-registered {len(fps_to_persist)} fingerprint(s) — they can alarm again."
        else:
            for fp in fps_to_persist:
                store[fp] = {"acked_at": sr.iso(time.time()), "disposition": target_disp,
                             "source": a.source or None}
            store_msg = (f" Registered {len(fps_to_persist)} fingerprint(s) as known-accepted "
                         f"({target_disp}) — recurrences will auto-retire.")
        _save_store(store)

    # refresh the status file immediately (rather than waiting for the next scan to touch it)
    if changed:
        try:
            sr.write_status()
        except Exception as ex:
            sys.stderr.write(f"[sentinel-ack] ledger updated, but status refresh failed ({ex}) — the next scan will fix it\n")

    verb = "re-opened" if a.undo else f"retired as '{target_disp}'"
    print(f"✓ {changed} event(s) {verb}.{(' Status refreshed.' if changed else '')}{store_msg}")
    return 0


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    sys.exit(main())
