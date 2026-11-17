#!/usr/bin/env python3
"""gc: Grand Central's one command. Read-only unless the subcommand says otherwise.

  gc status            db path, user_version, journal mode, rows per table, last backup/snapshot, last events
  gc rebuild / check    rebuild the model into a scratch copy; compare it with the live model (the health light's source)
  gc backup            backup.py local, then verified; exit 1 + message on failure. The session-end call.
  gc snapshot          backup.py snapshot (local backup, then the Drive-backed snapshot)
  gc migrate           dry run by default; --apply --backup-ok FILE to act
  gc events [N]        last N diary events (default 10)
  gc tests [--live]    run run_tests.py
  gc fresh [--json]    is the mailbox picture current? exit 0 fresh, 3 stale, 1 error
  gc new LABEL [--since X] [--limit N] [--json]   threads in a label (name or id), newest first
  gc onboarding sheet|answer   (on a copy, --db) the onboarding sitting: the sheet of pre-filled questions, and recording his answers
  gc merge LOSER SURVIVOR --words "..."   merge two people or organizations, only on his words; gc unmerge LOSER --words "..." undoes it
  gc who ADDRESS [--json]   who is this sender (person, circles, score, rules, first seen, overrides)
  gc person KEY [--json]    a person's page (KEY: person key, old/merged key or address); gc org KEY [--json] an organization's chart
  gc upcoming [--start D] [--days N] [--json]   events in a window with their people, relation to him, projects; gc due [--json] who is past their keep_in_touch_days
  gc thread ID [--json]     envelopes + meaning (items, projects, urgency) for one thread
  gc proposals [--kind K] [--status S] [--limit N] [--json]   open proposals/questions in the queue
  gc answer ID ANSWER [--by WHO, default gc.json owner_id] [--json]   answer one proposal (yes|no|free text): the ONLY write among these; never touches Gmail
  gc answer --subject-kind K --subject NAME --fact KEY --value V --words "his words" --question Q [--said-on D] [--until D]
                       THE ONE DOOR for a decision: one per call, checked against the allowed words (kg_vocab)
  gc urgent [--limit N] [--json]   open items ranked by computed urgency + overrides (pins up, quiet-until hidden)
  gc engine [--json]   run the engine now: window -> signals -> episodes -> rank -> gaps (writes the memory and the gap queue)
  gc week [--start DATE] [--json]  one-week digest for a planning skill (start defaults to today; 7 days)
  (fresh/new/who/thread/proposals/urgent/week are read-only; --json prints one JSON document on stdout; errors exit 1)
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import store  # noqa: E402
import gc_settings  # noqa: E402
import feeds  # noqa: E402  (4P.0b: the named no-feed state)


def _feed_gate(a):
    """4P.0b: with no feed connected (or no database to read), the read commands return the named
    state (exit 0) instead of data or an error. None means a feed is connected: answer as before."""
    g = feeds.read_gate()
    if g is None:
        return None
    _emit(a, g, feeds.text_line(g))
    return 0


def _age(p):
    s = int(time.time() - p.stat().st_mtime)
    for unit, n in (("d", 86400), ("h", 3600), ("m", 60)):
        if s >= n:
            return "%d%s ago" % (s // n, unit)
    return "%ds ago" % s


def _newest(d, pattern):
    if not d.is_dir():
        return None
    files = sorted((p for p in d.iterdir() if re.fullmatch(pattern, p.name)), key=lambda p: p.name)
    return files[-1] if files else None


def cmd_status(a):
    import backup
    path = Path(store.db_path())
    gate = feeds.read_gate()           # 4P.0b: the named no-feed state, exit 0, never "(no such file)" or a crash
    if gate is not None:
        gate["db"] = str(path)
        gate["db_exists"] = path.exists()
        if a.json:
            print(json.dumps(gate, sort_keys=True, default=str))
        else:
            print("db: %s" % path)
            if not path.exists():
                print(" (no such file)")
            print(feeds.text_line(gate))
        return 0
    if a.json:
        payload = {"db": str(path), "db_exists": True}
        try:
            payload["user_version"] = store.user_version()
            payload["journal_mode"] = store.journal_mode()
            payload["rows"] = store.table_counts()
        except Exception as e:  # noqa: BLE001 (an empty or unreadable file: say so, never crash)
            payload["db_error"] = str(e)
        payload["feeds"] = feeds.feed_states()
        print(json.dumps(payload, sort_keys=True, default=str))
        return 0
    print("db: %s" % path)
    try:
        print("user_version: %d" % store.user_version())
        print("journal_mode: %s" % store.journal_mode())
        print("rows:")
        for t, n in store.table_counts().items():
            print(" %-22s %d" % (t, n))
    except Exception as e:  # noqa: BLE001 (4P.0b: an empty database file is a state, not a crash)
        print(" (database not readable yet: %s)" % e)
    for label, d, pat in (("last backup", backup.backup_dir(), r"rig-.*\.db"),
        ("last snapshot", backup.snapshot_dir(), r"rig-\d{8}\.db")):
        f = _newest(d, pat)
        print("%-13s %s" % (label + ":", "%s (%s)" % (f.name, _age(f)) if f else "none in %s" % d))
    print("last events:")
    try:
        ev = store.recent_events(5)
    except Exception:  # noqa: BLE001
        ev = []
    for e in ev:
        print(" %s %s %s" % (e["at"], e["kind"], (e["detail"] or "")[:80]))
    if not ev:
        print(" (none)")
    return 0

def cmd_backup(a):
    """Local database backup, then checked. Fails loudly (stderr + exit 1) if it cannot write: a planning
    session ends with this, and a silent miss would leave the day's answers with one copy."""
    import backup
    import sqlite3
    try:
        out = backup.local_backup()
        ok, counts, probs = backup.verify(out)
    except (OSError, sqlite3.Error, SystemExit) as e:
        print("BACKUP FAILED: %s" % e, file=sys.stderr)
        return 1
    if not ok:
        print("BACKUP FAILED verification: %s" % "; ".join(probs), file=sys.stderr)
        return 1
    print("backup ok: %s (%d tables, %d rows)" % (out, len(counts), sum(counts.values())))
    return 0


def cmd_snapshot(a):
    import backup
    print(backup.snapshot())
    return 0


def cmd_migrate(a):
    import migrate
    return migrate.run(store.db_path(), apply=a.apply, backup_ok=a.backup_ok)


def cmd_events(a):
    for e in store.recent_events(a.n):
        print("%s  %-20s %s" % (e["at"], e["kind"], e["detail"] or ""))
    return 0


def cmd_items(a):
    import store_items
    try:
        counts = store_items.item_counts()
    except Exception as e:
        print("no items table (%s); run: gc migrate" % e)
        return 1
    for src, n in sorted(counts.items()):
        print("  %-22s %d" % (src, n))
    print("  %-22s %d" % ("TOTAL", sum(counts.values())))
    return 0


def cmd_queue(a):
    import db
    con = db.connect(store.db_path(), readonly=True)
    try:
        rows = con.execute("SELECT id,kind,subject_ref,question,proposed_answer FROM queue WHERE status='open' ORDER BY id").fetchall()
    except Exception as e:
        print("no queue table (%s); run: gc migrate" % e)
        return 1
    finally:
        con.close()
    for r in rows:
        print("  #%d [%s] %s: %s%s" % (r[0], r[1], r[2], r[3], ("  (proposed: %s)" % r[4]) if r[4] else ""))
    print("%d open question(s)" % len(rows))
    return 0


def cmd_tests(a):
    return subprocess.call([sys.executable, str(ROOT / "run_tests.py")] + (["--live"] if a.live else []))


def cmd_rebuild(a):
    """Rebuild the model into a SCRATCH copy of the database (never the live file) and say where it is."""
    import model_check
    dest = a.out or os.path.join(gc_settings.data_root(), "scratch", "gc-rebuild-%s.db" % time.strftime("%Y%m%dT%H%M%S"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest):
        print("refusing to overwrite %s" % dest, file=sys.stderr)
        return 1
    path, counts = model_check.rebuild(store.db_path(), dest)
    print("rebuilt model written to the copy %s\n%s" % (path, json.dumps(counts, sort_keys=True)))
    return 0


def cmd_check(a):
    """Rebuild into a scratch copy and compare with the live model; record the result for the health light. Exit 1 if not clean."""
    import model_check
    res = model_check.check(store.db_path())
    if not a.no_record:
        model_check.write_result(res)
    print("gc check: %s (%d difference(s); integrity %s, foreign keys %d problem(s))" % (
        "CLEAN" if res["clean"] else "NOT CLEAN", res["differences"], "ok" if res["integrity_ok"] else "BAD", res["fk_problems"]))
    for k, v in sorted(res["by_kind"].items()):
        print("  %-26s %d" % (k, v))
    for w, side, row in res["sample"][:10]:
        print("  e.g. %s %s %s" % (w, side, row))
    return 0 if res["clean"] else 1


def _emit(a, data, text):
    if a.json:
        print(json.dumps(data, sort_keys=True, default=str))
    else:
        print(text)


def _ms(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%d %H:%M") if ms else "-"


def _guard(f):
    """Read commands: any exception -> exit 1 with the message on stderr (and a JSON error body under --json)."""
    def run(a):
        try:
            return f(a)
        except Exception as e:  # noqa: BLE001
            if a.json:
                print(json.dumps({"error": str(e)}))
            print("gc: %s" % e, file=sys.stderr)
            return 1
    return run


def store_relation_key(c):
    """The key to ask about for a `gc who` answer: the person the address belongs to, else the address itself."""
    import store_relation
    try:
        with store._read() as con:
            return store_relation.person_key_for_address(con, c["address"]) or "address:" + c["address"]
    except Exception:  # noqa: BLE001
        return "address:" + c["address"]


def _relation(key):
    """What this person/thing is to him (store_relation, assembled on demand, stored nowhere). None if the model is too old to say."""
    import store_relation
    try:
        with store._read() as c:
            return store_relation.relation_to_me(c, key)
    except Exception:  # noqa: BLE001  (a database older than the model: the field is simply left out)
        return None


def _relation_of_item(u):
    """Relation of an item's person and projects (two optional parts); None when the item names neither."""
    import store_relation
    try:
        with store._read() as c:
            pk = store_relation.person_key_for_address(c, u.get("person_address")) if u.get("person_address") else None
            ps = []
            for n in u.get("projects") or []:
                r = c.execute("SELECT key FROM kg_things WHERE kind='project' AND name=? ORDER BY id LIMIT 1", (n,)).fetchone()
                if r:
                    ps.append(store_relation.relation_to_me(c, r[0]))
            return {"person": store_relation.relation_to_me(c, pk) if pk else None, "projects": ps}
    except Exception:  # noqa: BLE001
        return None


def _with_relation(items):
    """Add the optional `relation` key to each urgent item; every old key is left exactly as it was."""
    for u in items:
        r = _relation_of_item(u)
        if r is not None:
            u["relation"] = r
    return items


def cmd_fresh(a):
    if a.labels:  # STEP 4b: run before the rehearsal and before any session
        f = store.labels_freshness(max_age_min=a.max_age_min)
        _emit(a, f, "labels %s: %s" % ("STALE" if f["stale"] else "fresh", f["reason"]))
        return 3 if f["stale"] else 0
    f = store.freshness(max_age_min=a.max_age_min)
    _emit(a, f, "%s: %s (last pull %s, newest message %s)" % (
        "STALE" if f["stale"] else "fresh", f["reason"], f["last_success_at"] or "never", f["newest_message_at"] or "-"))
    return 3 if f["stale"] else 0


def cmd_new(a):
    ts = store.threads_in_label(a.label, since=a.since, limit=a.limit)
    text = "\n".join("%s  %s  %s  %s" % (t["thread_id"], _ms(t["newest_ms"]), t["from_addr"], t["subject"]) for t in ts)
    _emit(a, {"label": a.label, "count": len(ts), "threads": ts}, (text + "\n" if text else "") + "%d thread(s)" % len(ts))
    return 0


def cmd_who(a):
    c = store.sender_context(a.address)
    try:
        w = store.graph_read("about_sender", a.address)
    except Exception:  # noqa: BLE001  (DB older than migration 005)
        w = {"keys": [], "facts": [], "links": []}
    c["memory"] = w
    rel = _relation(store_relation_key(c))
    if rel is not None:
        c["relation"] = rel
    text = "%s: %s; tier %s; score %s; circles %s; %d rule(s); first seen %s; %d msg(s); %d override(s)" % (
        c["address"], ("person " + str(c["person"]["label"])) if c["known"] else "UNKNOWN", c["tier"], c["relationship_score"],
        ",".join(x["name"] for x in c["circles"]) or "-", len(c["rules_matching"]), _ms(c["first_seen_ms"]),
        c["message_count"], len(c["overrides"]))
    his = [f for f in w["facts"] if f["who"] == "owner"]
    other = [f for f in w["facts"] if f["who"] != "owner" and f["source_kind"] != "legacy"]
    for f in his:
        text += "\n  HIS WORD  %s %s = %s  (%s, answer #%s)" % (f["thing_key"], f["fact_key"], f["value"], f["true_from"], f["answer_id"])
    for f in other:
        text += "\n  %-9s %s %s = %s  (%s)" % (f["who"], f["thing_key"], f["fact_key"], f["value"], f["certainty"])
    if rel is not None and rel["text"]:
        text += "\n  RELATION  %s" % rel["text"]
    _emit(a, c, text)
    return 0


def cmd_thread(a):
    msgs = store.thread_messages(a.id)
    ctx = store.thread_item_context(a.id)
    _emit(a, {"thread_id": a.id, "messages": msgs, "context": ctx},
          "%s: %d message(s); %d item(s); projects %s; urgency %s" % (
              a.id, len(msgs), len(ctx["items"]), ",".join(str(p.get("name")) for p in ctx["projects"]) or "-", ctx["urgency"]))
    return 0 if msgs else 1


def cmd_proposals(a):
    ps = store.proposals(kind=a.kind, status=a.status, limit=a.limit)
    text = "\n".join("#%d [%s] %s: %s%s" % (p["id"], p["kind"], p["subject_ref"], p["question"],
                                           ("  (proposed: %s)" % p["proposed_answer"]) if p["proposed_answer"] else "") for p in ps)
    _emit(a, {"kind": a.kind, "status": a.status, "count": len(ps), "proposals": ps}, (text + "\n" if text else "") + "%d proposal(s)" % len(ps))
    return 0


def cmd_answer(a):
    if a.fact:  # the one door: one decision about one thing
        if not (a.subject and a.subject_kind and a.value and a.words and a.question):
            raise ValueError("a decision needs --subject-kind --subject --fact --value --words --question")
        r = store.record_answer(a.question, a.words, a.asked_by or "gc answer", a.said_on, a.subject_kind, a.subject,
                                a.fact, a.value, a.until, words_kind=a.words_kind, condition=a.condition)
        _emit(a, r, "answer #%d saved; %s #%s" % (r["answer_id"], r["applied"], r["row_id"]))
        return 0
    if a.id is None or a.answer is None:
        raise ValueError("give ID ANSWER (a queue proposal) or --fact ... (a decision)")
    r = store.answer_proposal(a.id, a.answer, decided_by=a.by)
    _emit(a, r, "answered #%d [%s] %s: %s (answer #%s)" % (r["id"], r["kind"], r["subject_ref"], r["answer"], r.get("answer_id")))
    return 0


def cmd_merge(a):
    """His yes that two things are one: gc merge LOSER SURVIVOR --words "..."  (the first is folded into the second)."""
    if not a.words:
        raise ValueError("a merge needs his own words: --words \"...\"")
    r = store.merge_things(a.loser, a.survivor, a.words, a.asked_by or "gc merge", a.said_on)
    _emit(a, r, "merged %s into %s (answer #%d): %d fact(s) and %d link(s) moved, %d fact(s) and %d link(s) kept as history only" % (
        a.loser, a.survivor, r["answer_id"], r["moved_facts"], r["moved_links"], r["kept_facts"], r["retired_links"]))
    return 0


def cmd_unmerge(a):
    if not a.words:
        raise ValueError("an un-merge needs his own words: --words \"...\"")
    r = store.unmerge_things(a.loser, a.words, a.asked_by or "gc unmerge", a.said_on)
    _emit(a, r, "un-merged %s (answer #%d)" % (a.loser, r["answer_id"]))
    return 0


def cmd_approve(a):
    """His yes to ONE staged filter pair, by sha256 (the ONLY way an approval is recorded). Needs his own words."""
    if not a.digest or not a.words:
        raise ValueError("give DIGEST and --words (his own words)")
    aid = store.approve_staged(a.digest, a.words, "gc approve" + (":" + a.name if a.name else ""), a.said_on)
    _emit(a, {"answer_id": aid, "digest": a.digest}, "approval of staged pair %s saved as answer #%d (nothing was pushed)" % (a.digest[:12], aid))
    return 0


def cmd_urgent(a):
    g = _feed_gate(a)
    if g is not None:
        return g
    us = _with_relation(store.urgent_items(limit=a.limit))
    text = "\n".join("%.2f  #%d  %s  due %s%s" % (u["urgency"], u["item_id"], (u["title"] or "")[:70], (u["due_at"] or "-")[:10],
                                                    "  PINNED" if u["pinned"] else "") for u in us)
    _emit(a, {"count": len(us), "items": us}, (text + "\n" if text else "") + "%d urgent item(s)" % len(us))
    return 0


def cmd_engine(a):
    """gc engine: run the engine (gather -> score -> stitch -> rank -> gaps). Retiring: kept only for gc-daily's proposals until Phase 5."""
    import run as er
    res = er.run()
    _emit(a, res, er.summary_line(res))
    return 0


def cmd_onboarding(a):
    """The onboarding sitting (step 3.10): `gc --db COPY onboarding sheet --out F` / `onboarding answer --guesses F.guesses.json --file A.json`.
    Never the live file: a copy must be named with --db."""
    if not a.db:
        raise ValueError("onboarding works on a copy only: name it with --db")
    if a.mode == "sheet" and not a.out:
        print("gc: onboarding sheet needs --out FILE (the sheet is written there, with FILE.guesses.json beside it)", file=sys.stderr)
        return 2
    import onboarding
    args = [a.mode, "--db", a.db] + (["--out", a.out] if a.mode == "sheet" else ["--guesses", a.guesses, "--file", a.file] + (["--dry"] if a.dry else []))
    return onboarding.main(args)


def _pages(f, *args):
    import store_pages
    with store._read() as c:
        return getattr(store_pages, f)(c, *args)


def _rel(x):
    return ("  [%s]" % x["relation"]) if x.get("relation") else ""


def cmd_person(a):
    import clock
    g = _feed_gate(a)
    if g is not None:
        return g
    p = _pages("person_page", a.key, clock.today())
    if p is None:
        _emit(a, {"key": a.key, "found": False}, "%s: unknown" % a.key)
        return 1
    p["found"] = True
    t = "%s (%s)%s" % (p["name"], p["key"], (" asked as %s" % p["asked_as"]) if p["asked_as"] else "")
    t += "\n  RELATION  %s" % (p["relation"]["text"] or "unknown")
    for f in p["facts"]:
        t += "\n  %s = %s  (%s, %s, since %s)" % (f["fact"], f["value"], f["certainty"], f["source"], (f["since"] or "?")[:10])
    for k, lab in (("organizations", "in"), ("reports_to", "reports to"), ("reports_here", "reports to him/her"), ("knows", "knows"), ("projects", "project")):
        for o in p[k]:
            t += "\n  %s %s%s" % (lab, o["name"], (" (%s)" % o["role"]) if o.get("role") else "")
    if p["addresses"]:
        t += "\n  addresses: " + ", ".join(p["addresses"])
    for e in p["upcoming_events"]:
        t += "\n  UPCOMING  %s  %s (%s)" % ((e["starts_at"] or "?")[:16], e["name"], e["via"])
    for e in p["recent_events"][:3]:
        t += "\n  RECENT  %s  %s" % ((e["starts_at"] or "?")[:16], e["name"])
    t += "\n  %d upcoming, %d past event(s); %d item(s)" % (p["upcoming_total"], p["recent_total"], p["items_total"])
    for e in p.get("diary", []):
        t += "\n  DIARY  %s  %s  (%s confidence)" % (e["date"], e["entry_path"], e["confidence"] or "unstamped")
    _emit(a, p, t)
    return 0


def _type_label(n):
    """The type with its certainty: only 'sure' counts as confirmed; anything weaker says so."""
    if not n["org_type"]:
        return "type unknown"
    return n["org_type"] if n.get("org_type_certainty") == "sure" else "%s (not yet confirmed by you)" % n["org_type"]


def _org_text(n, depth=0):
    pad = "  " * (depth + 1)
    t = "%s%s (%s, %s)" % (pad, n["name"], n["key"], _type_label(n))
    for m in n["members"]:
        t += "\n%s  - %s%s" % (pad, m["name"], (" : " + m["role"]) if m["role"] else "")
    for q in n["parts"]:
        t += "\n" + _org_text(q, depth + 1)
    return t


def cmd_org(a):
    import clock
    g = _feed_gate(a)
    if g is not None:
        return g
    o = _pages("org_chart", a.key, clock.today())
    if o is None:
        _emit(a, {"key": a.key, "found": False}, "%s: unknown" % a.key)
        return 1
    o["found"] = True
    t = _org_text(o)
    for ln in o["reporting_lines"]:
        t += "\n  %s reports to %s" % (ln["person_name"], ln["boss_name"])
    if o["relation"]["text"]:
        t += "\n  RELATION  %s" % o["relation"]["text"]
    for e in o.get("diary", []):
        t += "\n  DIARY  %s  %s  (%s confidence)" % (e["date"], e["entry_path"], e["confidence"] or "unstamped")
    _emit(a, o, t)
    return 0


def cmd_upcoming(a):
    import clock
    g = _feed_gate(a)
    if g is not None:
        return g
    start = a.start or clock.today().isoformat()
    u = _pages("upcoming", start, a.days)
    t = "\n".join("%s  %s%s\n%s" % ((e["starts_at"] or "?")[:16], e["name"], _rel(e),
                                       "\n".join("    %s%s (%s)" % (p["name"], _rel(p), p["via"]) for p in e["people"]) +
                                       ("\n    projects: " + ", ".join(p["name"] for p in e["projects"]) if e["projects"] else "") +
                                       "".join("\n    DIARY  %s  %s  (%s confidence)" % (d["date"], d["entry_path"], d["confidence"] or "unstamped") for d in e.get("diary", []))) for e in u["events"])
    _emit(a, u, (t + "\n" if t else "") + "%d event(s) %s..%s" % (len(u["events"]), u["start"], u["end"]))
    return 0


def cmd_due(a):
    import clock
    g = _feed_gate(a)
    if g is not None:
        return g
    d = _pages("due", clock.today())
    t = "\n".join("%s  every %d day(s); last contact %s%s" % (x["name"], x["keep_in_touch_days"], x["last_contact"] or "unknown",
                                                                  (" (%d days ago)" % x["days_since"]) if x["days_since"] is not None else "") for x in d["due"])
    _emit(a, d, (t + "\n" if t else "") + "%d due" % len(d["due"]))
    return 0


def cmd_week(a):
    import clock
    g = _feed_gate(a)
    if g is not None:
        return g
    start = dt.date.fromisoformat(a.start) if a.start else clock.today()
    d = store.week_digest(start, start + dt.timedelta(days=7))
    _with_relation(d["top_urgent"])
    c = d["counts"]
    _emit(a, d, "week %s..%s: %d arrived; %d due; %d urgent shown; %d open proposal(s) (%s); %d expiry question(s); %d override review(s) due" % (
        d["start"], d["end"], c["arrived_total"], c["due_in_window"], len(d["top_urgent"]), c["open_proposals"],
        ",".join("%s %d" % (k, v["count"]) for k, v in d["open_proposals"].items()) or "none", c["expiry_questions"], len(d["overdue_reviews"])))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gc", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=None, help="use another database file (default: the live rig.db)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    st_ = sub.add_parser("status")
    st_.add_argument("--json", action="store_true")
    st_.set_defaults(f=cmd_status)
    sub.add_parser("backup").set_defaults(f=cmd_backup)
    sub.add_parser("snapshot").set_defaults(f=cmd_snapshot)
    m = sub.add_parser("migrate")
    m.add_argument("--apply", action="store_true")
    m.add_argument("--backup-ok", default=None, metavar="FILE")
    m.set_defaults(f=cmd_migrate)
    e = sub.add_parser("events")
    e.add_argument("n", nargs="?", type=int, default=10)
    e.set_defaults(f=cmd_events)
    rb = sub.add_parser("rebuild")
    rb.add_argument("--out", default=None, help="the scratch copy to write (default: a new file in scratch/)")
    rb.set_defaults(f=cmd_rebuild)
    ck = sub.add_parser("check")
    ck.add_argument("--no-record", action="store_true", help="do not write the result file the health light reads")
    ck.set_defaults(f=cmd_check)
    ob = sub.add_parser("onboarding")
    ob.add_argument("mode", choices=["sheet", "answer"])
    ob.add_argument("--out", default=None)
    ob.add_argument("--guesses", default=None)
    ob.add_argument("--file", default=None)
    ob.add_argument("--dry", action="store_true")
    ob.set_defaults(f=cmd_onboarding)
    sub.add_parser("items").set_defaults(f=cmd_items)
    sub.add_parser("queue").set_defaults(f=cmd_queue)
    t = sub.add_parser("tests")
    t.add_argument("--live", action="store_true")
    t.set_defaults(f=cmd_tests)
    for name, fn, args in (("fresh", cmd_fresh, [("--max-age-min", dict(type=float, default=None)), ("--labels", dict(action="store_true"))]),
                           ("new", cmd_new, [("label", {}), ("--since", dict(default=None)), ("--limit", dict(type=int, default=50))]),
                           ("who", cmd_who, [("address", {})]),
                           ("person", cmd_person, [("key", {})]),
                           ("org", cmd_org, [("key", {})]),
                           ("upcoming", cmd_upcoming, [("--start", dict(default=None)), ("--days", dict(type=int, default=7))]),
                           ("due", cmd_due, []),
                           ("thread", cmd_thread, [("id", {})]),
                           ("proposals", cmd_proposals, [("--kind", dict(default=None)), ("--status", dict(default="open", choices=["open", "answered", "dismissed", "all"])),
                                                         ("--limit", dict(type=int, default=None))]),
                           ("answer", cmd_answer, [("id", dict(type=int, nargs="?")), ("answer", dict(nargs="?")), ("--by", dict(default=None)),
                                                   ("--subject-kind", dict(default=None)), ("--subject", dict(default=None)),
                                                   ("--fact", dict(default=None)), ("--value", dict(default=None)),
                                                   ("--words", dict(default=None)), ("--question", dict(default=None)),
                                                   ("--said-on", dict(default=None)), ("--until", dict(default=None)),
                                                   ("--asked-by", dict(default=None)), ("--words-kind", dict(default="verbatim")),
                                                   ("--condition", dict(default=None))]),
                           ("approve", cmd_approve, [("digest", {}), ("--words", dict(default=None)), ("--name", dict(default=None)),
                                                     ("--said-on", dict(default=None))]),
                           ("merge", cmd_merge, [("loser", {}), ("survivor", {}), ("--words", dict(default=None)), ("--asked-by", dict(default=None)),
                                                 ("--said-on", dict(default=None))]),
                           ("unmerge", cmd_unmerge, [("loser", {}), ("--words", dict(default=None)), ("--asked-by", dict(default=None)),
                                                     ("--said-on", dict(default=None))]),
                           ("urgent", cmd_urgent, [("--limit", dict(type=int, default=20))]),
                           ("week", cmd_week, [("--start", dict(default=None))]),
                           ("engine", cmd_engine, [])):
        sp = sub.add_parser(name)
        for flag, kw in args:
            sp.add_argument(flag, **kw)
        sp.add_argument("--json", action="store_true")
        sp.set_defaults(f=_guard(fn))
    a = ap.parse_args(argv)
    if a.db:
        store.set_path(a.db)
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
