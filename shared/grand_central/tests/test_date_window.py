#!/usr/bin/env python3
"""test_date_window.py — step 2.0b: --after/--before window, NO-TRACE guard, gate order, machine headers,
guarded ALTER, store_filters/store_contacts. Synthetic fixtures; email_fetch is monkeypatched; no Google,
no real rig.db writes (a COPY of it is used for the ALTER test). Run: venv python tests/test_date_window.py
(or pytest)."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import datetime
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import zoneinfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import gc_settings  # noqa: E402
os.environ.setdefault("RIG_HANDOFF_DIR", __import__("tempfile").mkdtemp(prefix="rig-handoff-test-"))  # never the live handoff dir
import pull  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "system", "tools"))
import sanitize as real_sanitize  # noqa: E402

NY = zoneinfo.ZoneInfo("America/New_York")
SCRATCH = tempfile.mkdtemp(prefix="rig-test-")   # was a dead session's scratchpad path
REAL_DB = gc_settings.db_path()


def ms(y, mo, d, h=12, mi=0, s=0):
    return int(datetime.datetime(y, mo, d, h, mi, s, tzinfo=NY).timestamp() * 1000)


def msg(mid, tid, when, headers=None, labels=("INBOX",)):
    hs = [{"name": "From", "value": "a@example.test"}, {"name": "To", "value": "me@example.test"},
          {"name": "Subject", "value": f"subject {mid}"}]
    hs += [{"name": k, "value": v} for k, v in (headers or {}).items()]
    return {"id": mid, "threadId": tid, "internalDate": str(when), "labelIds": list(labels),
            "sizeEstimate": 100, "payload": {"headers": hs}}


class FakeFetch:
    """Stands in for email_fetch: list pages of `page_size`, get_thread from a dict (or raise-as-error)."""
    def __init__(self, threads, failing=(), page_size=2):
        self.threads, self.failing, self.page_size = threads, set(failing), page_size
        self.order = list(threads)          # newest-first listing order
        self.list_params, self.get_calls, self.gate_items = [], [], []

    def check_paused(self, unit):   # the pause gate (never paused here; see test_pause_gate.py)
        pass

    def labels_list(self):
        return {"labels": []}, None

    def list_threads(self, params):
        self.list_params.append(dict(params))
        start = int(params.get("pageToken") or 0)
        chunk = self.order[start:start + self.page_size]
        out = {"threads": [{"id": t} for t in chunk]}
        if start + self.page_size < len(self.order):
            out["nextPageToken"] = str(start + self.page_size)
        return out, None

    def get_thread(self, tid, fmt="metadata"):
        self.get_calls.append(tid)
        if tid in self.failing:
            return None, "boom"
        return {"id": tid, "messages": self.threads[tid]}, None

    def gate_message(self, unit, body, item=""):
        self.gate_items.append(item)
        return {"verdict": "NONE", "content": body, "reason": ""}


def setup(threads, failing=(), page_size=2, db_file=None):
    pull.BACKOFF_S = 0
    pull.PENDING.clear()
    for k in list(pull.STATS):
        pull.STATS[k] = 0
    ff = FakeFetch(threads, failing, page_size)
    pull.email_fetch = ff
    pull.sanitize = real_sanitize
    pull.batch_reader.judge_all = lambda items, **_kw: {i: "CLEAN" for i, _t in items}
    d = tempfile.mkdtemp()
    os.environ["RIG_DB"] = db_file or os.path.join(d, "rig.db")
    return ff, pull.open_db()


def counts(db):
    tabs = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    return {t: db.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tabs}


def run(db, **kw):
    pull.pull_email(db, kw.pop("months", None), kw.pop("max_threads", 100), kw.get("after"), kw.get("before"))
    pull.flush_pending(db)


AFTER, BEFORE = "2026-06-01", "2026-08-31"


def sample_threads():
    return {
        "T_new": [msg("m_new", "T_new", ms(2026, 9, 5))],                                   # after window
        "T_edge_hi": [msg("m_hi", "T_edge_hi", ms(2026, 8, 31, 23, 59, 59))],               # last second, in
        "T_after_edge": [msg("m_ae", "T_after_edge", ms(2026, 9, 1, 0, 0, 0))],             # first second after
        "T_mid": [msg("m_mid", "T_mid", ms(2026, 7, 10))],
        "T_overlap": [msg("m_ov_old", "T_overlap", ms(2026, 5, 31, 23, 59, 59)),
                      msg("m_ov_in", "T_overlap", ms(2026, 6, 1, 0, 0, 0))],                # edge lo
        "T_old": [msg("m_old", "T_old", ms(2026, 5, 20))],
        "T_fail": [],                                                                       # fetch raises
        "T_older": [msg("m_older", "T_older", ms(2026, 4, 1))],                             # must never be fetched
    }


ORDER = ["T_new", "T_edge_hi", "T_after_edge", "T_mid", "T_overlap", "T_old", "T_fail", "T_older"]


def ordered():
    t = sample_threads()
    return {k: t[k] for k in ORDER}


def test_window_filter_and_stop_paging():
    ff, db = setup(ordered(), failing=["T_fail"])
    run(db, after=AFTER, before=BEFORE)
    mids = {r[0] for r in db.execute("SELECT id FROM messages")}
    assert mids == {"m_hi", "m_mid", "m_ov_in"}, mids        # inclusive both ends, overlap keeps in-window only
    th = {r[0]: r[1] for r in db.execute("SELECT id, message_count FROM threads")}
    assert th == {"T_edge_hi": 1, "T_mid": 1, "T_overlap": 1}, th
    # pages of 2: [new,edge_hi] [after_edge,mid] [overlap,old] [fail,older]; page 3 = overlap(in-window) so
    # paging continues; page 4 (fail + older) is entirely older -> stops after it; nothing beyond is listed.
    assert "T_older" in ff.get_calls and len(ff.list_params) == 4
    assert all(p.get("includeSpamTrash") is True for p in ff.list_params)
    assert all("q" not in p for p in ff.list_params)


def test_stop_paging_point():
    # pages of 2: [new,mid] [old,older] <- entirely older, so paging stops; T_edge_hi (page 3) is never listed
    order = ["T_new", "T_mid", "T_old", "T_older", "T_edge_hi"]   # last one is out of order on purpose: never reached
    t2 = {k: sample_threads()[k] for k in order}
    ff, db = setup(t2, page_size=2)
    ff.order = order
    run(db, after=AFTER, before=BEFORE)
    assert "T_edge_hi" not in ff.get_calls and len(ff.list_params) == 2, (ff.get_calls, len(ff.list_params))
    assert {r[0] for r in db.execute("SELECT id FROM messages")} == {"m_mid"}


def test_no_trace_out_of_window():
    t = {"T_new": sample_threads()["T_new"], "T_old": sample_threads()["T_old"],
         "T_fail": [], "T_older": sample_threads()["T_older"]}
    # T_fail sits after T_old (older than the window) -> certainly out of window -> no error row either
    ff, db = setup(t, failing=["T_fail"], page_size=10)
    before = counts(db)
    state_dir = os.environ.get("LIFEHACK_LAST_SEEN_DIR")
    run(db, after=AFTER, before=BEFORE)
    after = counts(db)
    assert before == after, {k: (before[k], after[k]) for k in before if before[k] != after[k]}
    assert all(v == 0 for v in after.values()), after          # not one row anywhere, errors included
    assert pull.PENDING == [] and ff.gate_items == []
    assert pull.STATS["failed_unrecorded"] == 1 and pull.STATS["threads_out_of_window"] == 3
    assert os.environ.get("LIFEHACK_LAST_SEEN_DIR") == state_dir   # pull.py never touches the door's bookmarks


def test_failure_with_unknown_date_records_error():
    t = {"T_fail": [], "T_mid": sample_threads()["T_mid"]}
    ff, db = setup(t, failing=["T_fail"], page_size=10)
    run(db, after=AFTER, before=BEFORE)
    assert counts(db)["errors"] == 1          # head-of-list failure: date unknown, may be in window


def test_gate_never_called_for_out_of_window():
    ff, db = setup(ordered(), failing=["T_fail"])
    run(db, after=AFTER, before=BEFORE)
    out = {"m_new", "m_ae", "m_ov_old", "m_old", "m_older"}
    assert out.isdisjoint(set(ff.gate_items)), ff.gate_items
    assert set(ff.gate_items) == {"m_hi", "m_mid", "m_ov_in"}


def test_machine_headers():
    t = {"T1": [msg("m1", "T1", ms(2026, 7, 1), {"Precedence": "Bulk", "Auto-Submitted": "Auto-Generated",
                                                 "List-Post": "<mailto:x@example.test>"})],
         "T2": [msg("m2", "T2", ms(2026, 7, 2), {"precedence": "x" * 40, "AUTO-SUBMITTED": "no", "List-Id": "<l.example.test>"})],
         "T3": [msg("m3", "T3", ms(2026, 7, 3))]}
    ff, db = setup(t, page_size=10)
    run(db, after=AFTER, before=BEFORE)
    rows = {r[0]: r[1:] for r in db.execute("SELECT id, precedence, auto_submitted, list_headers_present FROM messages")}
    assert rows["m1"] == ("bulk", "auto-generated", 1)
    assert rows["m2"] == ("x" * 20, "no", 0)       # List-Id alone does not count; precedence capped at 20
    assert rows["m3"] == (None, None, 0)


def test_guarded_alter_on_real_db_copy():
    if not os.path.exists(REAL_DB):
        return
    os.makedirs(SCRATCH, exist_ok=True)
    copy = os.path.join(SCRATCH, "rig_copy_test.db")
    if os.path.exists(copy):
        os.remove(copy)
    src = sqlite3.connect(f"file:{REAL_DB}?mode=ro", uri=True)
    dst = sqlite3.connect(copy)
    src.backup(dst)
    src.close()
    dst.close()
    chk = sqlite3.connect(copy)
    cols0 = {r[1] for r in chk.execute("PRAGMA table_info(messages)")}
    old = chk.execute("SELECT id, thread_id, subject, from_addr FROM messages ORDER BY id").fetchall()
    new_cols = [c for c, _ in pull.NEW_MESSAGE_COLUMNS if c in cols0]
    old_new = (chk.execute(f"SELECT id, {', '.join(new_cols)} FROM messages ORDER BY id").fetchall()
               if new_cols else None)
    n_before = counts(chk)
    chk.close()
    os.environ["RIG_DB"] = copy
    db = pull.open_db()
    pull.open_db().close()                                     # second open: ALTER is idempotent
    cols1 = {r[1] for r in db.execute("PRAGMA table_info(messages)")}
    assert {"precedence", "auto_submitted", "list_headers_present"} <= cols1
    assert cols0 <= cols1
    assert db.execute("SELECT id, thread_id, subject, from_addr FROM messages ORDER BY id").fetchall() == old
    n_after = counts(db)
    assert all(n_after[k] == v for k, v in n_before.items()), "old tables changed"
    # The real db now carries populated contract columns (the 2.0b byte filled them), so the old
    # "all NULL" assertion went stale (2026-11-11). What the guard must guarantee: values already
    # there are untouched by open_db. The NULL-on-ALTER case is checked on a synthetic old schema below.
    if new_cols:
        assert db.execute(f"SELECT id, {', '.join(new_cols)} FROM messages ORDER BY id").fetchall() == old_new
    assert {"filters", "contacts"} <= set(n_after)


def test_guarded_alter_on_old_schema():
    """A pre-contract messages table (no precedence/auto_submitted/list_headers_present) gains exactly the
    missing columns; old rows survive with NULLs; a second open is a no-op."""
    d = tempfile.mkdtemp()
    path = os.path.join(d, "old.db")
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE messages(
        id TEXT PRIMARY KEY, thread_id TEXT, internal_date INTEGER, label_ids TEXT, size INTEGER,
        from_addr TEXT, from_name TEXT, to_addrs TEXT, to_names TEXT, cc_addrs TEXT, cc_names TEXT,
        reply_to TEXT, subject TEXT, list_id TEXT, list_unsubscribe_present INTEGER,
        multipart_mixed INTEGER, spf_pass INTEGER, dkim_pass INTEGER, dmarc_pass INTEGER,
        is_sent INTEGER, gate_verdict TEXT)""")
    con.execute("INSERT INTO messages(id, thread_id, subject, from_addr) VALUES ('m1', 't1', 's', 'a@x.test')")
    con.commit()
    con.close()
    prev = os.environ.get("RIG_DB")
    os.environ["RIG_DB"] = path
    try:
        db = pull.open_db()
        pull.open_db().close()
        cols = {r[1] for r in db.execute("PRAGMA table_info(messages)")}
        assert {c for c, _ in pull.NEW_MESSAGE_COLUMNS} <= cols
        row = db.execute("SELECT id, subject, precedence, auto_submitted, list_headers_present FROM messages").fetchall()
        assert row == [("m1", "s", None, None, None)]
        db.close()
    finally:
        if prev is None:
            os.environ.pop("RIG_DB", None)
        else:
            os.environ["RIG_DB"] = prev
        shutil.rmtree(d, ignore_errors=True)


def test_store_filters_and_contacts():
    ff, db = setup({})
    n = pull.store_filters(db, {"filter": [
        {"id": "f1", "criteria": {"from": "Bob@Example.test", "subject": "hi &amp; bye", "hasAttachment": True,
                                  "secret": "drop me"},
         "action": {"addLabelIds": ["Label_1"], "removeLabelIds": ["INBOX"], "forward": "x@example.test",
                    "bogus": "drop"}},
        {"criteria": {"from": "no id"}}]})
    assert n == 1
    cid, crit, act = db.execute("SELECT id, criteria_json, action_json FROM filters").fetchone()
    crit, act = json.loads(crit), json.loads(act)
    assert cid == "f1" and set(crit) == {"from", "subject", "hasAttachment"} and crit["hasAttachment"] is True
    assert "&amp;" not in crit["subject"]                      # sanitize() ran on the string value
    assert set(act) == {"addLabelIds", "removeLabelIds", "forward"}
    n = pull.store_contacts(db,
        {"connections": [{"resourceName": "people/c1",
                          "names": [{"displayName": "Secret Name"}], "phoneNumbers": [{"value": "555"}],
                          "biographies": [{"value": "note"}],
                          "emailAddresses": [{"value": "Zed@Example.TEST"}, {"value": "a@example.test"}],
                          "memberships": [{"contactGroupMembership": {"contactGroupResourceName": "contactGroups/g1"}},
                                          {"contactGroupMembership": {"contactGroupResourceName": "contactGroups/zz"}}]}]},
        {"contactGroups": [{"resourceName": "contactGroups/g1", "name": "Family", "memberCount": 3}]})
    assert n == 1
    rn, em, gr = db.execute("SELECT * FROM contacts").fetchone()
    assert rn == "people/c1" and json.loads(em) == ["a@example.test", "zed@example.test"] and json.loads(gr) == ["Family"]
    dump = json.dumps([rn, em, gr])
    assert "Secret" not in dump and "555" not in dump and "note" not in dump
    assert [c[1] for c in db.execute("PRAGMA table_info(contacts)")] == ["resource_name", "emails_json", "groups_json"]


def test_window_bounds_dst_and_inclusive():
    lo, hi, w = pull.window_bounds(None, "2026-03-08", "2026-03-08")      # US DST starts that day: 23h long
    assert w and hi - lo == 23 * 3600 * 1000
    lo, hi, w = pull.window_bounds(3, None, None)
    assert not w and hi is None


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception as e:  # noqa: BLE001
                import traceback
                traceback.print_exc()
                print("FAIL", name, repr(e))
                fails += 1
    sys.exit(1 if fails else 0)
