#!/usr/bin/env python3
"""test_source_freshness.py — task 2.0a: --calendar/--tasks modes skip under `auto` when the
source was fetched successfully within 24h (source_state), and a pull that records errors is
NOT marked fresh. Runs against an in-memory db — never the real rig.db, never gws."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import datetime
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("RIG_HANDOFF_DIR", __import__("tempfile").mkdtemp(prefix="rig-handoff-test-"))  # never the live handoff dir
import pull  # noqa: E402

SCHEMA = """
CREATE TABLE errors(item_id TEXT, kind TEXT, error TEXT, at TEXT);
CREATE TABLE source_state(source TEXT PRIMARY KEY, last_success_at TEXT, rows INTEGER);
"""


def fresh_db():
    db = sqlite3.connect(":memory:")
    db.executescript(SCHEMA)
    return db


def mark(db, source, hours_ago):
    t = (datetime.datetime.now(datetime.timezone.utc)
         - datetime.timedelta(hours=hours_ago)).isoformat(timespec="seconds")
    db.execute("INSERT OR REPLACE INTO source_state(source, last_success_at, rows) VALUES(?,?,?)",
               (source, t, 0))
    db.commit()


def add_error(db):
    def fn():
        db.execute("INSERT INTO errors(item_id, kind, error, at) VALUES('x', 'calendar', 'boom', 'now')")
        db.commit()
    return fn


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    return cond


def main():
    ok = True
    db = fresh_db()

    # 1. auto with no recorded success → fetches, and a clean pull is marked fresh
    pull.STATS.update({"calendar_events": 0, "tasks": 0})
    called = []
    pull.pull_source_if_needed(db, "calendar", "auto", lambda: called.append("calendar"))
    ok &= check("auto, never fetched -> pulls", called == ["calendar"])
    ok &= check("auto, clean pull -> marked fresh with rows=0",
                db.execute("SELECT rows FROM source_state WHERE source='calendar'").fetchone()[0] == 0)
    ok &= check("last_success_at recorded",
                db.execute("SELECT last_success_at FROM source_state WHERE source='calendar'").fetchone()[0] is not None)

    # 2. auto, fetched 1h ago → skipped
    mark(db, "tasks", 1)
    called = []
    pull.pull_source_if_needed(db, "tasks", "auto", lambda: called.append("tasks"))
    ok &= check("auto, fetched 1h ago -> skipped", called == [])

    # 3. auto, fetched 25h ago → fetches again
    mark(db, "tasks", 25)
    called = []
    pull.pull_source_if_needed(db, "tasks", "auto", lambda: called.append("tasks"))
    ok &= check("auto, fetched 25h ago -> pulls", called == ["tasks"])

    # 4. always → fetches even when fresh
    called = []
    pull.pull_source_if_needed(db, "calendar", "always", lambda: called.append("calendar"))
    ok &= check("always -> pulls even when fresh", called == ["calendar"])

    # 5. never → never fetches
    called = []
    pull.pull_source_if_needed(db, "calendar", "never", lambda: called.append("calendar"))
    ok &= check("never -> skipped", called == [])

    # 6. a pull that records errors is NOT marked fresh
    db.execute("DELETE FROM source_state WHERE source='tasks'")
    db.execute("DELETE FROM errors")
    db.commit()
    pull.pull_source_if_needed(db, "tasks", "auto", add_error(db))
    ok &= check("pull with errors -> not marked fresh",
                db.execute("SELECT COUNT(*) FROM source_state WHERE source='tasks'").fetchone()[0] == 0)

    print("ALL PASS" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
