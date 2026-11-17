#!/usr/bin/env python3
"""test_pause_gate.py — the rig honours the Sentinel pause (exit 75 before any Google call, re-checked
mid-run), planted runs use separate state files, and --unpause is a confirmed, logged, line-only removal.
Everything runs in tmp dirs with the door monkeypatched; never the real state dir, never Google.
Run: venv python tests/test_pause_gate.py (or pytest, if installed)."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import contextlib
import io
import json
import os
import sys
import tempfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("RIG_HANDOFF_DIR", __import__("tempfile").mkdtemp(prefix="rig-handoff-test-"))  # never the live handoff dir
import pull  # noqa: E402
import rig_env  # noqa: E402

sys.path.insert(0, rig_env.EMAIL_DOOR_DIR)
import email_fetch  # noqa: E402


def boom(name):
    def f(*a, **k):
        raise AssertionError(f"{name} called")
    return f


@contextlib.contextmanager
def rig(tty=None, typed=""):
    """Isolated RIG_HOME + db in a tmp dir; every door/fetcher raises if called unless a test re-patches it.
    os.environ is restored afterwards (apply_to_this_process clears it). Yields the pause-file Path-like str."""
    saved = dict(os.environ)
    with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as st:
        st.enter_context(mock.patch.object(rig_env, "RIG_HOME", os.path.join(tmp, "rig")))
        st.enter_context(mock.patch.dict(os.environ, {"RIG_DB": os.path.join(tmp, "rig.db")}))
        st.enter_context(mock.patch.object(pull, "BACKOFF_S", 0))
        st.enter_context(mock.patch.object(pull, "email_fetch", email_fetch, create=True))
        for n in ("list_threads", "get_thread", "labels_list", "preflight"):
            st.enter_context(mock.patch.object(email_fetch, n, boom(n)))
        for n in ("pull_calendar", "pull_tasks", "pull_filters", "pull_contacts"):
            st.enter_context(mock.patch.object(pull, n, boom(n)))
        if tty is not None:
            st.enter_context(mock.patch.object(sys.stdin, "isatty", lambda: tty, create=True))
            st.enter_context(mock.patch("builtins.input", lambda prompt="": typed))
        pf = os.path.join(tmp, "rig", "state", "sentinel-paused-sources")
        os.makedirs(os.path.dirname(pf))
        try:
            yield pf
        finally:
            os.environ.clear()
            os.environ.update(saved)


def write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def run_main(*argv):
    err = io.StringIO()
    with mock.patch.object(sys, "argv", ["pull.py", *argv]), contextlib.redirect_stderr(err), \
            contextlib.redirect_stdout(io.StringIO()):
        try:
            rc = pull.main()
        except SystemExit as e:
            rc = e.code
    return rc, err.getvalue()


def log_path(pf):
    return os.path.join(os.path.dirname(pf), "sentinel-unpause-log.jsonl")


def test_paused_exits_75_before_any_door_call():
    with rig() as pf:
        write(pf, "email:rig\n")
        rc, err = run_main("--months", "1", "--max-threads", "5")
        assert rc == 75
        assert "PAUSED" in err and "--unpause rig" in err and pf in err


def test_planted_state_is_separate():
    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(rig_env, "RIG_HOME", os.path.join(tmp, "rig")):
        real, planted = rig_env.rig_environ(planted=False), rig_env.rig_environ(planted=True)
        pdir = os.path.join(tmp, "rig", "state", "planted")
        for k in ("SENTINEL_PAUSE_FILE", "SENTINEL_LOG", "SENTINEL_STATUS", "SENTINEL_ACKED_FP"):
            assert planted[k] != real[k]
            assert planted[k].startswith(pdir + os.sep)
            assert not real[k].startswith(pdir)


def test_pause_mid_run_stops_before_page_2():
    calls = {"list": 0, "get": 0}
    with rig() as pf:
        def list_threads(params):
            calls["list"] += 1
            write(pf, "email:rig\n")   # a REAL-ATTACK verdict lands while the run is in flight
            return {"threads": [{"id": "t1"}], "nextPageToken": "tok"}, None

        def get_thread(tid, fmt):
            calls["get"] += 1
            return {"messages": []}, None
        with mock.patch.object(email_fetch, "preflight", lambda: True), \
                mock.patch.object(email_fetch, "labels_list", lambda: ({"labels": []}, None)), \
                mock.patch.object(email_fetch, "list_threads", list_threads), \
                mock.patch.object(email_fetch, "get_thread", get_thread):
            rc, _ = run_main("--months", "1", "--max-threads", "500")
        assert rc == 75
        assert calls == {"list": 1, "get": 0}   # stopped before get_thread and before page 2


def test_unpaused_gate_passes():
    calls = []
    with rig() as pf:
        with mock.patch.object(email_fetch, "preflight", lambda: calls.append("preflight") or True), \
                mock.patch.object(email_fetch, "labels_list",
                                  lambda: calls.append("labels") or ({"labels": []}, None)), \
                mock.patch.object(email_fetch, "list_threads",
                                  lambda p: calls.append("list") or ({"threads": []}, None)), \
                mock.patch.object(pull, "pull_calendar", lambda *a, **k: None), \
                mock.patch.object(pull, "pull_tasks", lambda *a, **k: None), \
                mock.patch.object(pull, "pull_filters", lambda *a, **k: None), \
                mock.patch.object(pull, "pull_contacts", lambda *a, **k: None):
            rc, _ = run_main("--months", "1", "--max-threads", "5")
        assert rc == 0
        assert calls[:3] == ["preflight", "labels", "list"]


# ───────────── --unpause ─────────────

def test_unpause_requires_why():
    with rig(tty=True, typed="rig") as pf:
        write(pf, "email:rig\n")
        rc, _ = run_main("--unpause", "rig")
        assert rc not in (0, None)
        assert read(pf) == "email:rig\n"


def test_unpause_wrong_name_refuses():
    with rig(tty=True, typed="rog") as pf:
        write(pf, "email:other\nemail:rig\n")
        rc, _ = run_main("--unpause", "rig", "--why", "x")
        assert rc not in (0, None)
        assert read(pf) == "email:other\nemail:rig\n"
        assert not os.path.exists(log_path(pf))


def test_unpause_right_name_logs_then_removes_only_that_line():
    with rig(tty=True, typed="rig") as pf:
        write(pf, "email:other\nemail:rig\nslack:keep\n")
        rc, _ = run_main("--unpause", "rig", "--why", "looked at T09, planted")
        assert rc == 0
        assert read(pf) == "email:other\nslack:keep\n"
        lines = read(log_path(pf)).splitlines()
        assert len(lines) == 1
        e = json.loads(lines[0])
        assert e["unit"] == "rig" and e["line"] == "email:rig\n" and e["why"] == "looked at T09, planted"
        assert e["pause_file"] == pf and e["who"] and e["ts"]


def test_unpause_non_tty_refuses():
    with rig(tty=False, typed="rig") as pf:
        write(pf, "email:rig\n")
        rc, _ = run_main("--unpause", "rig", "--why", "x")
        assert rc not in (0, None)
        assert read(pf) == "email:rig\n"
        assert not os.path.exists(log_path(pf))


def test_unpause_not_paused_exits_0_without_writing():
    with rig(tty=True, typed="rig") as pf:
        write(pf, "email:other\n")
        rc, _ = run_main("--unpause", "rig", "--why", "x")
        assert rc == 0
        assert read(pf) == "email:other\n"
        assert not os.path.exists(log_path(pf))


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
