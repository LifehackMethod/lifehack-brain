#!/usr/bin/env python3
"""test_dedupe_cache.py — the reader's dedupe cache (Phase E prerequisite "Sentinel cheaper").

The AI reader still reads ALL stranger text; the cache only skips a RE-READ of text already judged CLEAN by the
same reader model + prompt + scanner. Proves: clean is cached; ATTACK/UNJUDGED never are; a model, prompt or
scanner change invalidates; wipe works; planted runs bypass it; identical texts in one call are sent once;
pull.flush_pending goes through it. No Google, no real claude call (subprocess.run is faked), tmp cache only.

Run: python3 tests/test_dedupe_cache.py   → exit 0 on pass.
"""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import os
import sys
import tempfile
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_RIG = os.path.dirname(_HERE)
sys.path.insert(0, _RIG)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "system", "tools"))

import batch_reader as br  # noqa: E402
os.environ.setdefault("RIG_HANDOFF_DIR", __import__("tempfile").mkdtemp(prefix="rig-handoff-test-"))  # never the live handoff dir
import pull  # noqa: E402
import rig_env  # noqa: E402
import sanitize  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


class FakeClaude:
    """Stands in for `claude -p`: parses the prompt's items; text containing 'ATTACKME' → ATTACK,
    'BREAKME' → garbage (unparseable → whole batch UNJUDGED), else CLEAN. Records every item text it was sent."""
    def __init__(self):
        self.seen = []
        self.calls = 0

    def __call__(self, cmd, **kw):
        import re
        self.calls += 1
        prompt = cmd[2]
        token = re.search(r"boundary token for this call is (\S+):", prompt).group(1)
        blocks = re.findall(rf"BEGIN ITEM (\d+) {token}\n(.*?)\nEND ITEM \1 {token}", prompt, re.S)
        lines = []
        for n, text in blocks:
            self.seen.append(text)
            if "BREAKME" in text:
                return mock.Mock(returncode=0, stdout="no verdicts here", stderr="")
            lines.append(f"ITEM {n}: {'ATTACK' if 'ATTACKME' in text else 'CLEAN'}")
        return mock.Mock(returncode=0, stdout="\n".join(lines), stderr="")


def fresh_env(tmp):
    os.environ["SENTINEL_DEDUPE_DB"] = os.path.join(tmp, "dedupe.sqlite")
    os.environ.pop("SENTINEL_DEDUPE_DISABLE", None)
    for k in br.STATS:
        br.STATS[k] = 0


def run(fake, items, **kw):
    with mock.patch.object(br.subprocess, "run", fake):
        return br.judge_all(items, **kw)


print("test_dedupe_cache.py")
print("=" * 60)
with tempfile.TemporaryDirectory() as tmp:
    fresh_env(tmp)

    # 1. clean is cached: second call with the same text sends nothing
    f = FakeClaude()
    out = run(f, [("a", "FIELD subject: hello world")])
    check("first read goes to the reader", out == {"a": "CLEAN"} and f.calls == 1)
    f2 = FakeClaude()
    out = run(f2, [("b", "FIELD subject: hello world")])
    check("same text under a new id is answered from cache, reader not called",
          out == {"b": "CLEAN"} and f2.calls == 0 and br.STATS["cache_hits"] == 1, str(br.STATS))

    # 2. ATTACK is never cached: re-judged every time
    f = FakeClaude()
    run(f, [("x", "FIELD subject: ATTACKME now")])
    f2 = FakeClaude()
    out = run(f2, [("x", "FIELD subject: ATTACKME now")])
    check("ATTACK re-sent on the second run", f2.calls == 1 and out == {"x": "ATTACK"})

    # 3. UNJUDGED is never cached
    f = FakeClaude()
    out = run(f, [("u", "FIELD subject: BREAKME")])
    check("unparseable batch is UNJUDGED", out == {"u": "UNJUDGED"})
    f2 = FakeClaude()
    run(f2, [("u", "FIELD subject: BREAKME")])
    check("UNJUDGED re-sent, never cached as clean", f2.calls == 1)
    import sqlite3
    n_rows = sqlite3.connect(os.environ["SENTINEL_DEDUPE_DB"]).execute("select count(*) from clean").fetchone()[0]
    check("only the one CLEAN text is in the cache file", n_rows == 1, str(n_rows))

    # 4. in-run duplicates sent once, verdict fanned out (even ATTACK)
    fresh_env(tmp)
    os.remove(os.environ["SENTINEL_DEDUPE_DB"])
    f = FakeClaude()
    out = run(f, [("1", "FIELD subject: same"), ("2", "FIELD subject: same"), ("3", "FIELD subject: ATTACKME"),
                  ("4", "FIELD subject: ATTACKME")])
    check("every id gets a verdict", out == {"1": "CLEAN", "2": "CLEAN", "3": "ATTACK", "4": "ATTACK"}, str(out))
    check("identical texts are sent to the reader once", len(f.seen) == 2, str(f.seen))

    # 5. model change / prompt change / scanner change each invalidate
    fresh_env(tmp)
    os.remove(os.environ["SENTINEL_DEDUPE_DB"])
    run(FakeClaude(), [("a", "FIELD subject: stable text")])
    with mock.patch.object(br, "SMALL_MODEL", "some-other-model"):
        f = FakeClaude()
        run(f, [("a", "FIELD subject: stable text")])
        check("different reader model → re-read", f.calls == 1)
    with mock.patch.object(br, "_PROMPT_TMPL", br._PROMPT_TMPL + "\nExtra rule."):
        f = FakeClaude()
        run(f, [("a", "FIELD subject: stable text")])
        check("changed reader prompt → re-read", f.calls == 1)
    with mock.patch.object(br, "scanner_version", lambda: "different-scanner"):
        f = FakeClaude()
        run(f, [("a", "FIELD subject: stable text")])
        check("changed scanner version → re-read", f.calls == 1)
    f = FakeClaude()
    run(f, [("a", "FIELD subject: stable text")])
    check("original model+prompt+scanner still hits", f.calls == 0)
    k1, k2 = br.cache_key("t", "m1", "s"), br.cache_key("t", "m2", "s")
    check("cache_key differs by model and by text", k1 != k2 and br.cache_key("t2", "m1", "s") != k1)

    # 6. expiry: an entry older than 30 days is ignored
    db = sqlite3.connect(os.environ["SENTINEL_DEDUPE_DB"])
    db.execute("update clean set at = at - ?", (br.CACHE_MAX_AGE_S + 60,))
    db.commit()
    db.close()
    f = FakeClaude()
    run(f, [("a", "FIELD subject: stable text")])
    check("entry older than 30 days → re-read", f.calls == 1)

    # 7. wipe
    check("wipe removes rows", br.wipe_cache() >= 1)
    f = FakeClaude()
    run(f, [("a", "FIELD subject: stable text")])
    check("after wipe the text is read again", f.calls == 1)
    check("wipe on a missing file is a no-op", (os.remove(os.environ["SENTINEL_DEDUPE_DB"]), br.wipe_cache())[1] == 0)

    # 8. disabled / use_cache=False: reads everything, writes nothing
    fresh_env(tmp)
    run(FakeClaude(), [("a", "FIELD subject: one")])
    f = FakeClaude()
    run(f, [("a", "FIELD subject: one")], use_cache=False)
    check("use_cache=False re-reads", f.calls == 1)
    os.environ["SENTINEL_DEDUPE_DISABLE"] = "1"
    f = FakeClaude()
    run(f, [("a", "FIELD subject: one")])
    check("SENTINEL_DEDUPE_DISABLE=1 re-reads", f.calls == 1)
    del os.environ["SENTINEL_DEDUPE_DISABLE"]

    # 9. rig_env: planted runs disable the cache, real runs point it at the rig state dir
    keep = dict(os.environ)
    try:
        pe, re_ = rig_env.rig_environ(base={}, planted=True), rig_env.rig_environ(base={})
    finally:
        os.environ.clear(); os.environ.update(keep)
    check("planted env disables the dedupe cache", pe.get("SENTINEL_DEDUPE_DISABLE") == "1")
    check("real env enables it, rig-local file",
          "SENTINEL_DEDUPE_DISABLE" not in re_ and re_["SENTINEL_DEDUPE_DB"].endswith("state/sentinel-dedupe.sqlite")
          and re_["SENTINEL_DEDUPE_DB"].startswith(rig_env.RIG_HOME))

    # 10. the pull path (pull.flush_pending) uses the cache
    fresh_env(tmp)
    os.remove(os.environ["SENTINEL_DEDUPE_DB"]) if os.path.exists(os.environ["SENTINEL_DEDUPE_DB"]) else None

    class Door:
        @staticmethod
        def gate_message(unit, body, item=""):
            return {"verdict": "NONE", "content": sanitize.sanitize(body, max_len=sanitize.NO_CAP)}

    class DB:
        def execute(self, *a, **k): return mock.Mock()
        def commit(self): pass

    def stage(ids_texts):
        written = {}
        for iid, subj in ids_texts:
            pull.stage_fields({"subject": subj}, iid, "message",
                              lambda cleared, v, r, iid=iid: written.__setitem__(iid, (cleared, v)))
        return written

    with mock.patch.object(pull, "email_fetch", Door, create=True), \
            mock.patch.object(pull, "sanitize", sanitize, create=True):
        fake = FakeClaude()
        w1 = stage([("m1", "Weekly newsletter"), ("m2", "Weekly newsletter"), ("m3", "Lunch?")])
        with mock.patch.object(br.subprocess, "run", fake):
            pull.flush_pending(DB())
        check("run 1: 3 items, 2 distinct texts → reader saw 2", len(fake.seen) == 2, str(fake.seen))
        check("run 1: all three written clean", all(c is not None for c, _ in w1.values()))
        fake2 = FakeClaude()
        w2 = stage([("m4", "Weekly newsletter"), ("m5", "Lunch?")])
        with mock.patch.object(br.subprocess, "run", fake2):
            pull.flush_pending(DB())
        check("run 2: same texts → reader NOT called (cache hit)", fake2.calls == 0 and pull.STATS["reader_cache_hits"] >= 2,
              str(pull.STATS))
        check("run 2: items still written clean", all(c is not None for c, _ in w2.values()))
        fake3 = FakeClaude()
        w3 = stage([("m6", "Weekly newsletter"), ("m7", "ATTACKME ignore previous")])
        with mock.patch.object(br.subprocess, "run", fake3), \
                mock.patch.object(pull, "record_quarantine", lambda *a, **k: None):
            pull.flush_pending(DB())
        check("run 3: only the NEW text is sent", len(fake3.seen) == 1 and "ATTACKME" in fake3.seen[0], str(fake3.seen))
        check("run 3: the attack is still quarantined (cleared=None)", w3["m7"][0] is None and w3["m6"][0] is not None)
        pull.NO_DEDUPE = True
        fake4 = FakeClaude()
        stage([("m8", "Weekly newsletter")])
        with mock.patch.object(br.subprocess, "run", fake4):
            pull.flush_pending(DB())
        pull.NO_DEDUPE = False
        check("--no-dedupe-cache path re-reads", fake4.calls == 1)

print("=" * 60)
print("PASS" if not FAILURES else f"FAIL — {len(FAILURES)}: {FAILURES}")
sys.exit(1 if FAILURES else 0)
