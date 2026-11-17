#!/usr/bin/env python3
"""test_inbox_backfill.py - pull.py --inbox-backfill: lists with labelIds=["INBOX"] only (never q),
paginates, skips ids already in the store, fetches the rest. Stubbed gws door: no network, no model."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import test_date_window as T  # noqa: E402  (shares its fakes; importing it runs nothing)
import pull  # noqa: E402


class FakeDoor(T.FakeFetch):
    def __init__(self, threads):
        super().__init__(threads)
        self.calls = []

    def _call(self, path, params, timeout=30):
        self.calls.append((list(path), dict(params)))
        if path != ["messages", "list"]:
            return None, "unexpected call"
        start = int(params.get("pageToken") or 0)
        ids = [(m["id"], t) for t, ms in self.threads.items() for m in ms]
        chunk = ids[start:start + 2]
        out = {"messages": [{"id": i, "threadId": t} for i, t in chunk]}
        if start + 2 < len(ids):
            out["nextPageToken"] = str(start + 2)
        return out, None


def run_backfill(max_threads=10):
    threads = {"T1": [T.msg("m1", "T1", T.ms(2026, 5, 1))], "T2": [T.msg("m2", "T2", T.ms(2026, 5, 2))],
               "T3": [T.msg("m3", "T3", T.ms(2026, 5, 3))], "T4": [T.msg("m4", "T4", T.ms(2026, 5, 4))],
               "T5": [T.msg("m5", "T5", T.ms(2026, 5, 5))]}
    ff, db = T.setup(threads)
    door = FakeDoor(threads)
    door.__dict__.update({k: v for k, v in ff.__dict__.items() if k not in ("calls",)})
    pull.email_fetch = door
    # m2 is already known to the store
    pull.store_message(db, threads["T2"][0], "T2")
    pull.flush_pending(db)
    db.commit()
    door.get_calls.clear()
    pull.pull_inbox_backfill(db, max_threads)
    pull.flush_pending(db)
    return door, db


def test_lists_inbox_only_no_q_and_skips_known():
    door, db = run_backfill()
    lists = [p for path, p in door.calls if path == ["messages", "list"]]
    assert len(lists) == 3, lists                       # 5 ids, pages of 2
    assert all(p["labelIds"] == ["INBOX"] for p in lists)
    assert all("q" not in p for p in lists)
    assert sorted(door.get_calls) == ["T1", "T3", "T4", "T5"], door.get_calls   # T2 known: not fetched
    assert pull.STATS["inbox_listed"] == 5 and pull.STATS["inbox_already_known"] == 1
    assert {r[0] for r in db.execute("SELECT id FROM messages")} == {"m1", "m2", "m3", "m4", "m5"}


def test_max_threads_caps_fetches():
    door, _db = run_backfill(max_threads=2)
    assert len(door.get_calls) == 2


def test_refused_listing_stops_with_exact_error():
    door, db = run_backfill()
    door._call = lambda path, params, timeout=30: (None, "gws_error: insufficient scope for labelIds")
    pull.BACKOFF_S = 0
    try:
        pull.list_inbox_ids(db)
    except SystemExit as e:
        assert "insufficient scope for labelIds" in str(e)
    else:
        raise AssertionError("should have stopped")


def test_label_resync_ids_only():
    """--label-resync: lists ids per label (INBOX + user labels), rewrites label_ids of stored mail, fetches no thread."""
    ff, db = T.setup({"T6": [T.msg("m6", "T6", T.ms(2026, 5, 6))], "T7": [T.msg("m7", "T7", T.ms(2026, 5, 7))]})
    door = FakeDoor({})
    door.__dict__.update({k: v for k, v in ff.__dict__.items() if k not in ("calls", "threads")})
    pull.email_fetch = door
    for m in ("m6", "m7"):
        pull.store_message(db, T.msg(m, "T" + m[1], T.ms(2026, 5, 6), labels=("INBOX", "UNREAD")), "T" + m[1])
    pull.flush_pending(db)
    db.commit()
    listing = {"INBOX": ["m7"], "Label_C": ["m6"]}
    door.labels_list = lambda *a, **k: ({"labels": [{"id": "INBOX", "name": "INBOX", "type": "system"},
                                                     {"id": "Label_C", "name": "Commercial", "type": "user"}]}, None)
    door._call = lambda path, params, timeout=30: ({"messages": [{"id": i, "threadId": "x"} for i in listing.get(params["labelIds"][0], [])]}, None)
    door.get_calls.clear()
    changed, n = pull.label_resync(db)
    assert door.get_calls == [], door.get_calls
    assert (changed, n) == (1, 2)
    l6 = db.execute("SELECT label_ids FROM messages WHERE id='m6'").fetchone()[0]
    l7 = db.execute("SELECT label_ids FROM messages WHERE id='m7'").fetchone()[0]
    assert "INBOX" not in l6 and "Label_C" in l6 and "UNREAD" in l6, l6
    assert "INBOX" in l7, l7

if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
