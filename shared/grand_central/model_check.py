"""model_check.py: `gc rebuild` and `gc check` (Phase 2 step 2.6; Vision 3.7.4 rules 5 and 6, 3.17 health check).

rebuild: copy the database to a scratch file, rebuild the model there from the permanent record (store_graph.rebuild_model),
         leave the scratch file for inspection. The live database is only ever READ (a read-only handle).
check:   rebuild into a scratch copy, compare with the live model (same things and keys, same current facts, same current
         links), also PRAGMA integrity_check and foreign_key_check on the live file. Writes a small result file the health
         light reads. Never gates anything.
"""
import json
import os
import re
import sqlite3
import sys
import tempfile
import time

import db
import store_graph as sg
import gc_settings

RIG_HOME = gc_settings.data_root()


def result_path():
    return os.path.join(os.environ.get("GC_STATE_ROOT") or os.path.join(RIG_HOME, "state"), "model-check", "last.json")


def _copy(live_path, dest):
    src = db.connect(live_path, readonly=True)
    dst = db.connect(dest)
    try:
        src.backup(dst)
    finally:
        src.close()
    return dst


def rebuild(live_path, dest=None):
    """-> (scratch path, counts). The scratch copy holds the rebuilt model."""
    dest = dest or tempfile.mktemp(prefix="gc-rebuild-", suffix=".db")
    con = _copy(live_path, dest)
    con.isolation_level = None
    try:
        con.execute("BEGIN IMMEDIATE")
        try:
            counts = sg.rebuild_model(con)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        counts["carry_over"] = _replay_carry_over(con)
        counts["organizations"] = _replay_org_moves(con)
        # 3.2: events come from calendar_events (Vision 3.7.4 rule 5). LAST, after his answers and the carry-over: the live builder
        # runs against the model as it stands today (guesses already retired), so the rebuild must too, or the two differ.
        import store_events
        con.execute("BEGIN IMMEDIATE")
        try:
            counts["events"] = store_events.build_events(con)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        # senders (migration 026): each address tied to its organization and marked person / bot / question mark. After the events,
        # because the live builder runs in that order and reads the persons the events made.
        import senders
        con.execute("BEGIN IMMEDIATE")
        try:
            counts["senders"] = senders.build_senders(con)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
    finally:
        con.close()
    return dest, counts


def _replay_carry_over(con):
    """Step 2.5's retirement is part of how the model got its current picture: code/AI guesses retired, and rows that trace to
    HIS word (grade answers, canon lines, approved rules, his overrides) carried over as owner copies under a recorded answer.
    The answers are on record; the copies are re-derived by the same function, reusing those answers (none are written)."""
    import retire_machine_guesses as rmg
    con.row_factory = sqlite3.Row
    cache = {}
    for aid, q in con.execute("SELECT id, question FROM kg_answers WHERE question LIKE 'carried over from old % row %'").fetchall():
        m = re.fullmatch(r"carried over from old (\w+) row (\d+)", q)
        if m:
            cache[(m.group(1), int(m.group(2)))] = aid
    n_before = con.execute("SELECT count(*) FROM kg_answers").fetchone()[0]
    res = rmg.apply(con, include_legacy=True, cache=cache)
    res["new_answers_written"] = con.execute("SELECT count(*) FROM kg_answers").fetchone()[0] - n_before
    con.row_factory = None
    return res


def _replay_org_moves(con):
    """Migration 021's moves (companies and circles into organizations) are part of how the model got its picture. They are on
    record (org_moves, thing_keys); the same function builds them again, after the carry-over, so the keys are the same."""
    import org_moves
    has = con.execute("SELECT 1 FROM sqlite_master WHERE name='org_moves'").fetchone()
    if not has:
        return None
    con.isolation_level = None
    con.execute("BEGIN IMMEDIATE")
    try:
        res = org_moves.apply_moves(con)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return res


def check(live_path, keep=None, mutate=None):
    """Rebuild into a scratch copy and compare. mutate(con): test hook that changes the REBUILT copy before comparing."""
    scratch = keep or tempfile.mktemp(prefix="gc-check-", suffix=".db")
    try:
        _, counts = rebuild(live_path, scratch)
        reb = db.connect(scratch)
        live = db.connect(live_path, readonly=True)
        try:
            if mutate:
                mutate(reb)
                reb.commit()
            diffs = sg.diff_pictures(sg.model_picture(live), sg.model_picture(reb))
            integrity = live.execute("PRAGMA integrity_check").fetchall()
            fk = live.execute("PRAGMA foreign_key_check").fetchall()
        finally:
            reb.close()
            live.close()
    finally:
        if not keep:
            for suf in ("", "-wal", "-shm"):
                try:
                    os.remove(scratch + suf)
                except OSError:
                    pass
    by = {}
    for what, side, _row in diffs:
        by["%s %s" % (what, side)] = by.get("%s %s" % (what, side), 0) + 1
    ok_integrity = [r[0] for r in integrity] == ["ok"]
    res = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "differences": len(diffs), "by_kind": by,
           "sample": [[w, s, list(r)] for w, s, r in diffs[:40]], "integrity_ok": ok_integrity, "fk_problems": len(fk),
           "rebuild": counts}
    res["clean"] = (not diffs) and ok_integrity and not fk
    return res


def write_result(res, path=None):
    path = path or result_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(res, f, sort_keys=True)
    os.replace(path + ".tmp", path)
    return path


def read_result(path=None):
    try:
        with open(path or result_path(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None
