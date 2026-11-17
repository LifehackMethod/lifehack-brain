#!/usr/bin/env python3
"""daily.py: Grand Central's daily engine (plan STEP 7 / Phase E1+E2). PROPOSALS ONLY.

One run, in order:
  1. token_check   local look at the rig login's 7-day testing-mode clock (no network). Near expiry -> WARN tile
                   and a loud stderr line. Past the 7 days we still TRY the pull (the app may be In production,
                   which local files cannot tell); if the pull then fails, the run is an ERROR that says why.
  2. backup        backup.local_backup() (one local copy of rig.db), before anything is written.
  3. pull          pull.py --after <watermark date> --max-threads CAP, as a subprocess. Read-only toward Google,
                   every stranger-written field goes through Sentinel (phrase scan + the AI reader) inside pull.py.
  4. items         store_items.backfill_items() (idempotent) turns the new rows into items + an 'arrived' event.
  5. proposals     rows in the `queue` table, nothing else:
                     who-is-this    a first-time sender (unknown address, never mailed before the window)
                     apply-label    an approved rule matches the new item (the label is the rule's folder/kind)
                     flag-urgent    subject has a clock word or job phrase from the keywords table
                   Deduped on (kind, subject_ref) over ALL statuses, so a dismissed question is never re-asked.
  6. tile          <NOTES>/state/status/gc-daily.json  (OK | WARN | ERROR, counts).
  7. watermark     source_state['daily'] = this run's START time, set ONLY after every step above succeeded.

HARD LIMITS: this file never writes to Gmail, never imports or calls the mover, never imports a Google module.
It reaches Google only by running pull.py (a read-only puller). tests/test_daily.py enforces that statically.

  python3 daily.py [--dry-run] [--max-threads N] [--tile PATH] [--first-days D]
  --dry-run: no pull, no backup, no watermark move, no tile file (the tile is printed). Proposals are still
             computed from the existing DB and written to the queue (idempotent).
Exit: 0 OK or WARN, 1 ERROR. Last stdout line: RESULT status=... (the runner's proof line reads it).
Env for tests: AGE_RIG_DB (db), AGE_NOTES_ROOT (tile root), AGE_NOW (clock).
"""
import argparse
import datetime
import fnmatch
import json
import os
import subprocess
import sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import backup  # noqa: E402
import clock  # noqa: E402
import store  # noqa: E402
import store_items  # noqa: E402
import store_meaning  # noqa: E402
import token_check  # noqa: E402

WATERMARK_SOURCE = "daily"
NY = ZoneInfo("America/New_York")
DEFAULT_MAX_THREADS = 150      # modest: newest-first paging, a normal day is well under this
DEFAULT_FIRST_DAYS = 2
PROPOSAL_CAP_PER_KIND = 40     # a flood (e.g. an old backlog landing) is capped and flagged WARN, not queued
PULL_TIMEOUT_S = 3 * 3600
KINDS = ("who-is-this", "apply-label", "flag-urgent")


def _iso(t):
    return t.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(s):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))


def tile_path():
    import gc_settings
    root = gc_settings.notes_root()       # AGE_NOTES_ROOT, else gc.json notes_root
    return os.path.join(root, "state", "status", "gc-daily.json")


# ---------------------------------------------------------------------------------------------- watermark / window
def watermark():
    r = store.get_source_state(WATERMARK_SOURCE)
    return r["last_success_at"] if r and r["last_success_at"] else None


def window(now, wm, first_days=DEFAULT_FIRST_DAYS):
    """(after_date 'YYYY-MM-DD' in America/New_York, window_start_iso UTC). pull.py's --after is inclusive, so the
    watermark's own day is re-covered (idempotent upserts; same-day overlap is cheap and never loses mail)."""
    start = _parse(wm) if wm else now - datetime.timedelta(days=first_days)
    d = start.astimezone(NY).date()
    lo = datetime.datetime.combine(d, datetime.time.min, tzinfo=NY)
    return d.isoformat(), _iso(lo)


# ---------------------------------------------------------------------------------------------- the pull step
def run_pull(after, max_threads):
    """Default pull step: pull.py as a subprocess. Returns (rc, tail_of_output). pull.py rig-isolates its own env."""
    p = subprocess.run([sys.executable, os.path.join(HERE, "pull.py"), "--after", after,
                        "--max-threads", str(max_threads)],
                       capture_output=True, text=True, timeout=PULL_TIMEOUT_S, cwd=HERE)
    return p.returncode, ((p.stdout or "") + (p.stderr or ""))[-1500:]


def last_run_counts(since_iso):
    """counts JSON of the newest `runs` row finished at/after since_iso (pull.py writes it), else {}."""
    for r in store.recent_runs(1):
        if r["finished"] and _parse(r["finished"]) >= _parse(since_iso):
            try:
                return json.loads(r["counts"] or "{}")
            except ValueError:
                return {}
    return {}


# ---------------------------------------------------------------------------------------------- new items
def new_items(prev_wm, window_start):
    """New inbox-side gmail items: created since the previous successful run AND occurring inside the window
    (so a backfill of old mail never floods proposals). Sent mail is not proposed on."""
    sql = ("SELECT id, source_id, title, person_address, occurred_at FROM items WHERE source='gmail' AND kind='email' "
           "AND COALESCE(status,'')<>'sent' AND occurred_at >= ?")
    args = [window_start]
    if prev_wm:
        sql += " AND created_at > ?"
        args.append(prev_wm)
    return store._rows(sql + " ORDER BY occurred_at, id", args)


def ensure_arrived(items, at):
    """backfill_items already adds 'arrived' for new rows; this only fills a gap, once per item."""
    made = 0
    for it in items:
        if not [e for e in store_items.item_history(it["id"]) if e["kind"] == "arrived"]:
            store_items.append_item_event(it["id"], "arrived", at=it["occurred_at"] or at, detail="daily", actor="gc-daily")
            made += 1
    return made


# ---------------------------------------------------------------------------------------------- proposals
def _known_addresses(window_start):
    """Addresses we already know: in the world model, mailed by me, in contacts, or seen before this window."""
    known = {r["address"] for r in store._rows("SELECT address FROM addresses")}
    known |= {r["address"] for r in store._rows("SELECT address FROM s_me")}
    known |= {r["address"] for r in store._rows("SELECT address FROM s_contact_addr")}
    return known


def _seen_before(addr, window_start_ms):
    r = store._one("SELECT 1 AS x FROM messages WHERE lower(from_addr)=? AND internal_date<? LIMIT 1", (addr, window_start_ms))
    return bool(r)


def _is_bulk(addr_msgs):
    return any(m["list_id"] or m["list_unsubscribe_present"] or (m["precedence"] or "").lower() in ("bulk", "list", "junk")
               or (m["auto_submitted"] or "").lower() not in ("", "no") for m in addr_msgs)


def compute_proposals(items, window_start):
    """Pure read: list of dicts {kind, subject_ref, question, proposed_answer}. Never writes anywhere."""
    wm_ms = int(_parse(window_start).timestamp() * 1000)
    known = _known_addresses(window_start)
    rules = [r for r in store.rules(approved_only=True) if (r.get("folder") or r.get("kind_label"))]
    exc = {}
    for e in store.rule_exceptions():
        exc.setdefault(e["rule_id"], []).append((e["word"] or "").lower())
    kw = {}
    for k in store.keywords():
        kw.setdefault(k["list_name"], []).append((k["phrase"] or "").lower())
    urgent_words = [("clock word", w) for w in kw.get("clock_words", []) if w] + \
                   [("job phrase", w) for w in kw.get("job_phrases", []) if w]
    out, asked = [], set()
    for it in items:
        subj = (it["title"] or "").strip()
        low = subj.lower()
        addr = (it["person_address"] or "").lower()
        domain = addr.rsplit("@", 1)[-1] if "@" in addr else ""
        unknown = bool(addr) and addr not in known and not _seen_before(addr, wm_ms)
        if unknown and addr not in asked:
            msgs = store._rows("SELECT list_id,list_unsubscribe_present,precedence,auto_submitted FROM messages WHERE id=?",
                               (it["source_id"],))
            if not _is_bulk(msgs):   # newsletters and robots are rules' business, not a "who is this" question
                asked.add(addr)
                out.append({"kind": "who-is-this", "subject_ref": "address:" + addr,
                            "question": "Who is %s? First message: \"%s\" (%s)." % (addr, subj[:120], (it["occurred_at"] or "")[:10]),
                            "proposed_answer": None})
        for r in rules:
            mv = (r["match_value"] or "").lower()
            if not ((r["match_kind"] == "address" and addr == mv) or (r["match_kind"] == "domain" and domain == mv)):
                continue
            g = (r["subject_glob"] or "").lower()
            if g and not fnmatch.fnmatchcase(low, g):
                continue
            if any(w and w in low for w in exc.get(r["id"], [])):
                continue   # a rule exception word is in the subject: the rule does not apply as written
            label = r.get("folder") or r.get("kind_label")
            out.append({"kind": "apply-label", "subject_ref": "item:%d" % it["id"],
                        "question": "Apply label '%s' to \"%s\" from %s? (rule %d)" % (label, subj[:100], addr, r["id"]),
                        "proposed_answer": label})
            break
        hits = [(what, w) for what, w in urgent_words if w in low]
        if hits:
            why = ", ".join("%s '%s'" % h for h in hits[:3])
            out.append({"kind": "flag-urgent", "subject_ref": "item:%d" % it["id"],
                        "question": "Looks time-sensitive (%s)%s: \"%s\" from %s." % (
                            why, ", sender not yet known" if unknown else "", subj[:100], addr),
                        "proposed_answer": "flag"})
    return out


def queue_proposals(props):
    """The ONLY write that proposals cause: queue rows via store_meaning.queue_add. Returns ({kind: added}, capped_kinds)."""
    added, capped = {k: 0 for k in KINDS}, []
    with store._write() as con:
        have = {(r[0], r[1]) for r in con.execute("SELECT kind, subject_ref FROM queue")}
        for p in props:
            key = (p["kind"], p["subject_ref"])
            if key in have:
                continue
            if added[p["kind"]] >= PROPOSAL_CAP_PER_KIND:
                if p["kind"] not in capped:
                    capped.append(p["kind"])
                continue
            store_meaning.queue_add(con, p["kind"], p["subject_ref"], p["question"], p["proposed_answer"])
            have.add(key)
            added[p["kind"]] += 1
    return added, capped


# ---------------------------------------------------------------------------------------------- the engine
def run_engine(warn):
    """Window -> signals -> episodes -> rank -> gaps (engine/). Skipped on a DB older than migration 008. A failure is a
    WARN, never an ERROR: the daily pull must not break because the engine did. Returns its counts or None."""
    try:
        if store.user_version() < 8:
            return None
        return store.engine_run()
    except Exception as e:  # noqa: BLE001
        warn("engine failed (the pull is fine): %s: %s" % (type(e).__name__, e))
        return None


# ---------------------------------------------------------------------------------------------- the run
def run_label_resync():
    """Keep the memory in step with Gmail (plan STEP 4b): ids-only label refresh, about a minute, no text, no gate."""
    p = subprocess.run([sys.executable, os.path.join(HERE, "pull.py"), "--label-resync", "--max-threads", "1"],
                       capture_output=True, text=True, timeout=600, cwd=HERE)
    return p.returncode, ((p.stdout or "") + (p.stderr or ""))[-800:]


def run(max_threads=DEFAULT_MAX_THREADS, dry_run=False, first_days=DEFAULT_FIRST_DAYS,
        pull_fn=None, backup_fn=None, token_fn=None, label_fn=None):
    """Returns the result dict (also the tile's source). Raises nothing for expected failures: status='ERROR'."""
    now = clock.now()
    started = _iso(now)
    res = {"status": "OK", "dry_run": dry_run, "started": started, "warnings": [], "error": None,
           "window_after": None, "new_items": 0, "arrived_added": 0, "proposals": {k: 0 for k in KINDS},
           "pull": None, "token": None, "backfilled": {}, "engine": None}
    warn = res["warnings"].append
    try:
        tok = (token_fn or token_check.facts)()
        res["token"] = tok.get("status")
        if tok.get("status") == "EXPIRES-SOON-IF-TESTING":
            warn("rig login may expire within 2 days if the Google app is in Testing (dies %s): re-run the rig login, or "
                 "publish the app to In production" % tok.get("if_testing_mode_refresh_token_dies"))
        elif tok.get("status") == "EXPIRED-IF-TESTING":
            warn("rig login is older than 7 days: fine if the app is In production, dead if it is in Testing; "
                 "trying the pull anyway")
        elif str(tok.get("status", "")).startswith("UNKNOWN"):
            warn("token check: %s" % tok.get("status"))

        prev = watermark()
        after, win_start = window(now, prev, first_days)
        res["window_after"] = after

        if not dry_run:
            (backup_fn or (lambda: backup.local_backup(store.db_path())))()
            rc, tail = (pull_fn or run_pull)(after, max_threads)
            res["pull"] = {"rc": rc}
            if rc != 0:
                hint = ""
                if rc == 75:
                    hint = " (Sentinel PAUSED unit rig: a human must look, then pull.py --unpause rig --why ...)"
                elif "invalid_grant" in tail or "401" in tail or "auth" in tail.lower():
                    hint = " (looks like an expired rig login: run the rig login again)"
                raise RuntimeError("pull.py failed rc=%s%s: %s" % (rc, hint, tail.strip().splitlines()[-1] if tail.strip() else ""))
            counts = last_run_counts(started)
            res["pull"]["counts"] = {k: counts.get(k) for k in ("threads", "messages", "quarantined", "errors", "judge_calls")
                                     if k in counts}
            if counts.get("threads", 0) >= max_threads:
                warn("pull hit the %d-thread cap: older mail in the window may be missing; raise the cap or re-run" % max_threads)
            if counts.get("quarantined"):
                warn("%d item(s) quarantined by Sentinel this run (see the quarantine table)" % counts["quarantined"])
            if counts.get("errors"):
                warn("%d fetch error(s) recorded this run (errors table)" % counts["errors"])

            # STEP 4b: refresh labels on stored mail right after the pull (the mover/filters change Gmail, not the store).
            # Tests that inject pull_fn get no real refresh unless they pass label_fn too.
            lf = label_fn or (run_label_resync if pull_fn is None else None)
            if lf is not None:
                lrc, ltail = lf()
                res["label_resync"] = {"rc": lrc}
                if lrc != 0:
                    warn("label refresh failed rc=%s: %s" % (lrc, ltail.strip().splitlines()[-1] if ltail.strip() else ""))

        res["backfilled"] = store_items.backfill_items()
        items = new_items(prev, win_start)
        res["new_items"] = len(items)
        res["arrived_added"] = ensure_arrived(items, started)
        added, capped = queue_proposals(compute_proposals(items, win_start))
        res["proposals"] = added
        for k in capped:
            warn("proposal cap (%d) hit for '%s': the rest were not queued" % (PROPOSAL_CAP_PER_KIND, k))
        res["engine"] = run_engine(warn)
        if not dry_run:
            store.set_source_state(WATERMARK_SOURCE, started, len(items))
            store.append_event("daily-run", {"after": after, "new_items": len(items), "proposals": added})
    except Exception as e:  # noqa: BLE001  every failure becomes a loud ERROR tile, never a silent pass
        res["status"], res["error"] = "ERROR", "%s: %s" % (type(e).__name__, e)
    if res["status"] == "OK" and res["warnings"]:
        res["status"] = "WARN"
    return res


def build_tile(res, now=None):
    import gc_settings
    now = now or clock.now()
    n = sum(res["proposals"].values())
    if res["status"] == "ERROR":
        summary = "ERROR: daily run failed: %s" % res["error"]
    else:
        summary = "%s%s: %d new item(s), %d proposal(s) queued (window from %s)" % (
            res["status"], " (dry run)" if res["dry_run"] else "", res["new_items"], n, res["window_after"])
    kpis = [{"key": "new_items", "label": "New mail items", "value": res["new_items"], "sub": "since the last daily run"}]
    for k, label in (("who-is-this", "Who is this?"), ("apply-label", "Apply label?"), ("flag-urgent", "Flagged urgent")):
        kpis.append({"key": k, "label": label, "value": res["proposals"].get(k, 0), "sub": "proposals queued today"})
    items = [{"title": "Warning", "detail": w} for w in res["warnings"]]
    if res["error"]:
        items.insert(0, {"title": "Daily run failed", "detail": res["error"]})
    return {"desk": gc_settings.pulse_desk(), "schema_version": 2, "pulse_job": "gc-daily", "emit_mode": "pulse",
            "stale_after_s": 172800, "last_run": now.astimezone().isoformat(timespec="seconds"),
            "rc": 1 if res["status"] == "ERROR" else 0, "status": res["status"], "summary": summary,
            "kpis": kpis, "items": items}


def write_tile(tile, path):
    # through the plugin's one writer; it rejects any status word it does not allow (WARN is written as NEEDS_REVIEW)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from status_lights import write_tile as _write
    _write(path, tile)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="skip pull/backup/watermark/tile file; use the existing DB")
    ap.add_argument("--max-threads", type=int, default=DEFAULT_MAX_THREADS)
    ap.add_argument("--first-days", type=int, default=DEFAULT_FIRST_DAYS, help="window for the very first run")
    ap.add_argument("--tile", default=None, help="tile path (default <NOTES>/state/status/gc-daily.json)")
    a = ap.parse_args(argv)
    res = run(max_threads=a.max_threads, dry_run=a.dry_run, first_days=a.first_days)
    tile = build_tile(res)
    if a.dry_run and not a.tile:
        print(json.dumps(tile, indent=2))
    else:
        try:
            write_tile(tile, a.tile or tile_path())
        except OSError as e:
            print("[gc-daily] WARN: could not write tile: %s" % e, file=sys.stderr)
    for w in res["warnings"]:
        print("[gc-daily] WARN: %s" % w, file=sys.stderr)
    if res["error"]:
        print("[gc-daily] ERROR: %s" % res["error"], file=sys.stderr)
    print("RESULT status=%s new_items=%d proposals=%d after=%s dry_run=%d" % (
        res["status"], res["new_items"], sum(res["proposals"].values()), res["window_after"], int(res["dry_run"])))
    return 1 if res["status"] == "ERROR" else 0


if __name__ == "__main__":
    sys.exit(main())
