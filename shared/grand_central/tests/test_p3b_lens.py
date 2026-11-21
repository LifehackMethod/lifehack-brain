#!/usr/bin/env python3
"""4P.3 slice B (items 1, 2): the four plain-words lens passes and the final pass with ONE uncapped question list.

SYNTHETIC only: made-up people, FAKE lens runners (the real claude is never run; one test runs a FAKE claude shell
script to see the real argument list and working directory), scratch folders only.

Planted-bad-case proof (each case is shown FAILING first, then passing):
  - cases about morning.py (the question cap, run_morning taking a lens stage) run against the PRE-change morning.py
    loaded from git commit 55b0ca4 (pinned: the last morning.py before the 4P.3R rebuild; HEAD would turn into the rebuilt code once it is committed) into a scratch module, then against the built code;
  - cases about the new modules run a plausible WRONG first version (a naive stub, or the real code with the one safety
    switched off) and show the check catches it, then the real code.

Run: python3 -I -B tests/test_p3b_lens.py   (from shared/grand_central/)
"""
import atexit as _ax, os as _o, shutil as _sh, subprocess as _sp, tempfile as _t, unittest
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.environ.get("GC_STATE_ROOT") or _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import importlib.util
import json
import stat
import sys
import tempfile
import shutil
import hashlib

ROOT = _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import lens  # noqa: E402
import morning  # noqa: E402
import transcripts  # noqa: E402

DAY = "2026-11-20"
PRE_NAME = "_pre_slB_morning.py"
pre_src = _sp.run(["git", "-C", ROOT, "show", "55b0ca4:shared/grand_central/morning.py"], check=True, capture_output=True).stdout.decode("utf-8")
pre_path = _o.path.join(ROOT, PRE_NAME)
with open(pre_path, "w", encoding="utf-8") as f:
    f.write(pre_src)
_ax.register(lambda: _o.path.exists(pre_path) and _o.remove(pre_path))
_spec = importlib.util.spec_from_file_location("pre_slB_morning", pre_path)
pre = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pre)


def planted(testcase, check, naive):
    """Show the check FAILING against the wrong version, then it must pass against the real one (caller runs that)."""
    with testcase.assertRaises((AssertionError, TypeError, AttributeError, OSError), msg="the planted wrong version should FAIL the check"):
        check(naive)


# ---------------------------------------------------------------- a scratch front room with scanned threads
def hx(s):
    return hashlib.sha1(s.encode()).hexdigest()[:12]


class Env(object):
    def __init__(self):
        self.root = _o.path.realpath(tempfile.mkdtemp(prefix="p3b-"))
        self.front = _o.path.join(self.root, "front-room")
        self.drop = _o.path.join(self.root, "drop")
        self.records = _o.path.join(self.root, "records", "context")
        _o.makedirs(self.drop)
        self._old = _o.environ.get("AGE_FRONT_ROOM")
        _o.environ["AGE_FRONT_ROOM"] = self.front

    def close(self):
        if self._old is None:
            _o.environ.pop("AGE_FRONT_ROOM", None)
        else:
            _o.environ["AGE_FRONT_ROOM"] = self._old
        shutil.rmtree(self.root, ignore_errors=True)

    def deliver(self, tag, body):
        t, m = hx("th-" + tag), hx("msg-" + tag)
        doc = {"schema": transcripts.SCHEMA, "thread_id": t, "message_id": m, "subject": "About " + tag, "from": "a@example.test",
               "date": DAY, "label": "inbox", "verdict": "safe", "seen": "full", "internal_ms": 1763600000000,
               "triage": {"needs_me": "cant_tell", "do_or_know": "cant_tell", "how_soon": "cant_tell", "deadline": None, "area": "cant_tell",
                          "obs": {"deadline_stated": "no", "direct_ask": "cant_tell", "reply_expected": "cant_tell", "money_involved": "no"}},
               "header": "# thread %s | subject: About %s\n\n" % (t, tag),
               "block": "=== message %s | %s | from: a@example.test | label: inbox ===\n%s\n\n" % (m, DAY, body)}
        with open(_o.path.join(self.drop, "%s.%s.json" % (t, m)), "w", encoding="utf-8") as f:
            json.dump(doc, f)
        return t, m

    def ingest(self):
        return transcripts.ingest(self.drop, mailroom_uid=_o.getuid())


def kind_of(prompt):
    head = prompt.splitlines()[0]
    for k, word in (("conflicts", "CONFLICTS"), ("lanes", "LANES"), ("body", "BODY AND ENERGY"), ("delta", "DELTA VS")):
        if word in head:
            return k
    raise AssertionError(head)


class FakeRunner(object):
    """A fake lens runner. replies: {kind: reply text | (None, code) | callable(prompt, folder)}. Records what each call saw."""

    def __init__(self, replies=None):
        self.replies, self.calls = replies or {}, []

    def complete_in(self, prompt, folder):
        k = kind_of(prompt)
        st = _o.stat(folder)
        self.calls.append({"kind": k, "prompt": prompt, "folder": folder, "mode": stat.S_IMODE(st.st_mode),
                           "files": sorted(_o.path.relpath(_o.path.join(dp, f), folder) for dp, _d, fs in _o.walk(folder) for f in fs)})
        r = self.replies.get(k, "Nothing stands out today.")
        if callable(r):
            r = r(prompt, folder)
        if isinstance(r, tuple):
            return r
        return r, None


# ================================================================ item 2: the question list is never capped
class Questions(unittest.TestCase):
    QS = ["Calendar: 'E%d' moved: what knocks on?" % i for i in range(5)] + ["Task: 'T%d' is gone: dropped?" % i for i in range(3)] + \
         ["New sender n%d@x.test: who?" % i for i in range(12)]

    def check(self, mod):
        kept, rest = mod.rank_questions(list(self.QS), lambda a: 0)
        self.assertEqual((len(kept), rest), (20, 0))
        self.assertEqual([q.split(" ")[0] for q in kept], ["Calendar:"] * 5 + ["Task:"] * 3 + ["New"] * 12)   # ordered, nothing dropped
        self.assertEqual(sorted(kept), sorted(self.QS))

    def test_twenty_in_twenty_out_ordered(self):
        planted(self, self.check, pre)          # pre-change: capped at 15 with per-source shares
        self.check(morning)
        self.assertFalse(hasattr(morning, "MAX_QUESTIONS"))

    def test_missing_ones_still_ordered_by_standing(self):
        qs = ["You wrote to a@x.test on 2026-11-01 and no reply: ?", "New sender n@x.test: who?", "You wrote to c@x.test on 2026-11-02 and no reply: ?"]
        kept, rest = morning.rank_questions(qs, lambda a: {"a@x.test": 1.0, "c@x.test": 5.0}[a])
        self.assertEqual((kept[0], rest), (qs[1], 0))
        self.assertIn("c@x.test", kept[1])


# ================================================================ item 1: what a lens may do
class Cmd(unittest.TestCase):
    def setUp(self):
        self.folder = _o.path.realpath(tempfile.mkdtemp(prefix="p3b-f-"))
        self.addCleanup(shutil.rmtree, self.folder, True)

    def arg(self, cmd, flag):
        return cmd[cmd.index(flag) + 1].split(",")

    def check(self, build):
        cmd = build(self.folder)
        scope = "//" + self.folder.lstrip("/") + "/**"
        allowed, tools, denied = self.arg(cmd, "--allowedTools"), self.arg(cmd, "--tools"), self.arg(cmd, "--disallowedTools")
        for w in ("Write", "Edit", "Bash", "WebFetch", "WebSearch", "NotebookEdit", "Agent"):
            self.assertNotIn(w, tools, "write/net tool available: " + w)
            self.assertFalse(any(a.startswith(w + "(") or a == w for a in allowed), "write/net tool allowed: " + w)
            self.assertIn(w, denied)
        self.assertEqual(sorted(a.split("(")[0] for a in allowed), ["Glob", "Grep", "Read"])
        self.assertTrue(all(a.endswith("(%s)" % scope) for a in allowed), allowed)      # scoped to the one folder, nothing else
        self.assertIn("--strict-mcp-config", cmd)

    def test_built_argument_list(self):
        real = morning.ClaudeLensModel(claude="/x/claude")
        self.check(real.build_cmd)
        naive_write = lambda f: ["claude", "-p", "--tools", "Read,Write", "--allowedTools", "Read,Write", "--disallowedTools", "Bash"]
        naive_net = lambda f: ["claude", "-p", "--tools", "Read,Grep,Glob,WebFetch", "--allowedTools",
                               ",".join("%s(//%s/**)" % (t, f.lstrip("/")) for t in ("Read", "Grep", "Glob", "WebFetch")),
                               "--disallowedTools", "Write,Edit,Bash,WebSearch,NotebookEdit,Agent", "--strict-mcp-config"]
        naive_scope = lambda f: ["claude", "-p", "--tools", "Read,Grep,Glob", "--allowedTools", "Read,Grep,Glob",
                                 "--disallowedTools", "Write,Edit,Bash,WebFetch,WebSearch,NotebookEdit,Agent", "--strict-mcp-config"]
        planted(self, self.check, naive_write)      # a write tool in the list
        planted(self, self.check, naive_net)        # a network tool in the list
        planted(self, self.check, naive_scope)      # a read outside the per-run folder (no scope names the folder)

    def test_fake_claude_sees_the_cwd_and_the_list_and_main_door_refuses_it_as_main_model(self):
        out = _o.path.join(self.folder, "..", "p3b-argv-%d.txt" % _o.getpid())
        binp = _o.path.join(tempfile.mkdtemp(prefix="p3b-bin-"), "claude")
        with open(binp, "w", encoding="utf-8") as f:
            f.write('#!/bin/sh\nprintf "%%s\\n" "$@" > "%s"\npwd >> "%s"\ncat > /dev/null\necho plain words\n' % (out, out))
        _o.chmod(binp, 0o755)
        self.addCleanup(shutil.rmtree, _o.path.dirname(binp), True)
        self.addCleanup(lambda: _o.path.exists(out) and _o.remove(out))
        m = morning.ClaudeLensModel(claude=binp, home=self.folder)
        text, err = m.complete_in("hi", self.folder)
        self.assertEqual((text, err), ('plain words', None))
        got = open(out, encoding="utf-8").read().splitlines()
        self.assertEqual(got[-1], self.folder)                 # working directory = the per-run folder
        self.assertNotIn("Write", " ".join(got).replace("--disallowedTools", "").split("Write,Edit")[0])
        # as the MAIN model it declares tools, so the morning read's tool-less door refuses it
        self.assertEqual(m.complete("x"), (None, "lens_model_has_tools"))
        self.assertFalse(transcripts.Caller("morning-read", tools=m.tools).tool_less)


# ================================================================ the export folder
class Export(unittest.TestCase):
    def setUp(self):
        self.env = Env()
        self.addCleanup(self.env.close)
        self.folder = lens.make_run_folder()
        self.addCleanup(shutil.rmtree, self.folder, True)

    def setup_threads(self):
        if getattr(self, "_done", None):
            return self._done
        good = self.env.deliver("good", "Please confirm the schedule for the meeting on Thursday.")
        bad = self.env.deliver("tampered", "This text will be edited after it was scanned.")
        self.env.ingest()
        path = _o.path.join(transcripts.transcripts_dir(), bad[0] + ".txt")
        with open(path, "a", encoding="utf-8") as f:
            f.write("added after the scan\n")          # block hash no longer matches the catalogue line
        ghost = hx("th-never-ingested")
        self._done = (good, bad, ghost)
        return self._done

    def check(self, export):
        good, bad, ghost = self.setup_threads()
        shutil.rmtree(self.folder, True)
        self.folder = lens.make_run_folder()
        out = export(self.folder, [good[0], bad[0], ghost])
        self.assertEqual(out["exported"], [good[0]])
        self.assertTrue(_o.path.exists(_o.path.join(self.folder, "threads", good[0] + ".txt")))
        for t in (bad[0], ghost):
            self.assertFalse(_o.path.exists(_o.path.join(self.folder, "threads", t + ".txt")), "refused thread is present")
        self.assertEqual(sorted(out["absent"]), sorted([bad[0], ghost]))

    def test_refused_or_unscanned_thread_is_absent(self):
        def naive(folder, ids):          # reads the file directly: no verdict, no hash check
            done = []
            for t in ids:
                try:
                    txt = open(_o.path.join(transcripts.transcripts_dir(), t + ".txt"), encoding="utf-8").read()
                except OSError:
                    continue
                _o.makedirs(_o.path.join(folder, "threads"), exist_ok=True)
                open(_o.path.join(folder, "threads", t + ".txt"), "w", encoding="utf-8").write(txt)
                done.append(t)
            return {"exported": done, "absent": {}}
        planted(self, self.check, naive)
        self.check(lens.export_threads)

    def test_export_goes_through_the_door_with_a_read_only_caller_and_logs_the_allowlist(self):
        good, _b, _g = self.setup_threads()
        lens.export_threads(self.folder, [good[0]])
        log = [json.loads(x) for x in open(transcripts._access_log(), encoding="utf-8").read().splitlines() if x.strip()]
        mine = [e for e in log if e.get("caller") == "lens-export"]
        self.assertTrue(mine and mine[-1]["outcome"] == "ok" and mine[-1]["allowlist"] == ["Read"])


# ================================================================ the run folder: local, 0700, gone after any run
SETTINGS = {"lanes": "- body\n- work", "life_map": "a life map", "facts": "{}"}


class RunFolder(unittest.TestCase):
    def setUp(self):
        self.env = Env()
        self.addCleanup(self.env.close)
        self.t, self.m = self.env.deliver("one", "Please confirm the schedule for the meeting on Thursday.")
        self.env.ingest()

    def check(self, boom=False):
        runner = FakeRunner()
        if boom:
            def raise_(prompt, folder):
                raise RuntimeError("a lens raising")
            runner.replies["conflicts"] = raise_
        stage = lens.run_lenses(DAY, [self.t], (), None, runner, SETTINGS)
        folder = runner.calls[0]["folder"]
        self.assertEqual(runner.calls[0]["mode"], 0o700)
        self.assertFalse(any(mk in folder for mk in lens.UNSYNCED_MARKS))
        self.assertTrue(folder.startswith(_o.path.realpath(tempfile.gettempdir())))
        self.assertFalse(_o.path.exists(folder), "the per-run folder is still there after the run")
        return runner, stage

    def test_local_0700_and_gone_after_a_successful_run(self):
        real_rm = shutil.rmtree
        shutil.rmtree = lambda *a, **k: None        # planted: cleanup switched off
        try:
            with self.assertRaises(AssertionError):
                self.check()
        finally:
            shutil.rmtree = real_rm
        self.check()

    def test_planted_wide_open_folder_fails_the_mode_check(self):
        real = lens.make_run_folder

        def open_folder():
            p = real()
            _o.chmod(p, 0o755)
            return p
        lens.make_run_folder = open_folder
        try:
            with self.assertRaises(AssertionError):
                self.check()
        finally:
            lens.make_run_folder = real
        self.check()

    def test_gone_after_a_failed_run_a_lens_raising(self):
        r, stage = self.check(boom=True)
        self.assertEqual(len(r.calls), 4)             # the other lenses still ran
        by = dict((x["name"], x) for x in stage["results"])
        self.assertEqual((by["conflicts"]["status"], by["conflicts"]["reason"]), ("failed", "exception_RuntimeError"))
        self.assertEqual([by[n]["status"] for n in ("lanes", "body", "delta")], ["ok"] * 3)

    def test_a_stage_failure_returns_every_lens_failed_and_removes_the_folder(self):
        seen = {}
        real = lens.export_threads

        def boom(folder, ids, drop=()):
            seen["f"] = folder
            raise RuntimeError("export blew up")
        lens.export_threads = boom
        try:
            r = FakeRunner()
            stage = lens.run_lenses(DAY, [self.t], (), None, r, SETTINGS)       # must not raise
        finally:
            lens.export_threads = real
        self.assertEqual(r.calls, [])
        self.assertEqual([(x["name"], x["status"]) for x in stage["results"]],
                         [("conflicts", "failed"), ("lanes", "failed"), ("body", "failed"), ("delta", "failed")])
        self.assertTrue(all(x["reason"] == "lens_stage_RuntimeError" for x in stage["results"]))
        self.assertFalse(_o.path.exists(seen["f"]))

    def test_a_folder_that_cannot_be_made_returns_every_lens_failed(self):
        old = tempfile.tempdir
        base = _o.path.join(tempfile.mkdtemp(prefix="p3b-s-"), "CloudStorage", "GoogleDrive-x")
        _o.makedirs(base)
        self.addCleanup(shutil.rmtree, _o.path.dirname(_o.path.dirname(base)), True)
        tempfile.tempdir = base
        try:
            stage = lens.run_lenses(DAY, [self.t], (), None, FakeRunner(), SETTINGS)
        finally:
            tempfile.tempdir = old
        self.assertTrue(all(x["status"] == "failed" and x["reason"] == "lens_stage_LensError" for x in stage["results"]))

    def test_a_synced_temp_dir_is_refused(self):
        base = _o.path.join(tempfile.mkdtemp(prefix="p3b-s-"), "CloudStorage", "GoogleDrive-x")
        _o.makedirs(base)
        self.addCleanup(shutil.rmtree, _o.path.dirname(_o.path.dirname(base)), True)
        old = tempfile.tempdir
        tempfile.tempdir = base
        try:
            with self.assertRaises(lens.LensError):
                lens.make_run_folder()
        finally:
            tempfile.tempdir = old


# ================================================================ the plain-words stage
class Stage(unittest.TestCase):
    def setUp(self):
        self.env = Env()
        self.addCleanup(self.env.close)
        self.t, self.m = self.env.deliver("one", "Please confirm the schedule for the meeting on Thursday afternoon.")
        self.env.ingest()
        self.prm = lambda day: {"upcoming": {"events": [{"key": "event:e1", "people": [{"key": "person:ann"}]}]}}

    def go(self, runner, settings=SETTINGS, threads=None, **kw):
        return lens.run_lenses(DAY, [self.t] if threads is None else threads, (), kw.get("prm_reader", self.prm), runner, settings)

    def by(self, stage):
        return dict((r["name"], r) for r in stage["results"])

    def test_a_plain_text_reply_comes_back_as_text(self):
        r = FakeRunner({"conflicts": '  The meeting may collide with a trip.\x00\n\n\n\nHe said "see you Thursday".  '})
        st = self.go(r)
        c = self.by(st)["conflicts"]
        self.assertEqual((c["status"], c["reason"]), ("ok", ""))
        self.assertEqual(c["text"], 'The meeting may collide with a trip.\n\nHe said "see you Thursday".')
        self.assertEqual(set(c), {"name", "label", "status", "text", "reason"})
        self.assertIn("threads/%s.txt" % self.t, r.calls[0]["files"])
        self.assertIn("prm/upcoming.json", r.calls[0]["files"])
        self.assertTrue(all(self.by(st)[n]["status"] == "ok" for n in ("lanes", "body", "delta")))

    def test_the_reply_is_capped(self):
        st = self.go(FakeRunner({"body": "word " * 5000}))
        self.assertLessEqual(len(self.by(st)["body"]["text"]), lens.MAX_LENS_CHARS)
        self.assertTrue(self.by(st)["body"]["text"])

    def test_json_looking_reply_is_just_text(self):
        st = self.go(FakeRunner({"body": '{"findings": []}'}))
        self.assertEqual((self.by(st)["body"]["status"], self.by(st)["body"]["text"]), ("ok", '{"findings": []}'))

    def test_a_failing_lens_is_failed_with_a_reason_while_the_others_are_ok(self):
        r = FakeRunner({"conflicts": (None, "timeout"), "body": "   "})
        by = self.by(self.go(r))
        self.assertEqual((by["conflicts"]["status"], by["conflicts"]["reason"]), ("failed", "timeout"))
        self.assertEqual((by["body"]["status"], by["body"]["reason"]), ("failed", "empty_reply"))
        self.assertEqual((by["lanes"]["status"], by["delta"]["status"]), ("ok", "ok"))

    def test_planted_a_failure_that_fails_everything_is_caught(self):
        def check(fn):
            by = self.by(fn(FakeRunner({"conflicts": (None, "timeout")})))
            self.assertEqual(by["conflicts"]["status"], "failed")
            self.assertEqual(by["body"]["status"], "ok")
        check(self.go)

        def naive(runner):
            st = self.go(runner)
            for x in st["results"]:
                x["status"] = "failed"
            return st
        with self.assertRaises(AssertionError):
            check(naive)

    def test_no_lanes_defined_skips_the_lanes_lens_and_says_so(self):
        for settings in (dict(SETTINGS, lanes=None), dict(SETTINGS, lanes=""), {"life_map": "x"}):
            r = FakeRunner()
            st = self.go(r, settings=settings)
            self.assertEqual([c["kind"] for c in r.calls], ["conflicts", "body", "delta"])
            lanes = self.by(st)["lanes"]
            self.assertEqual((lanes["status"], lanes["reason"]), ("skipped", "no lanes defined"))
            self.assertIn("- lens Lanes skipped: no lanes defined", lens.snapshot_lines(st))
            self.assertIn("lens Lanes: skipped (no lanes defined)", lens.render_block(st))

    def test_the_export_holds_only_exported_threads_never_the_transcripts_folder(self):
        r = FakeRunner()
        self.go(r, threads=[self.t, hx("th-never-ingested")])
        files = r.calls[0]["files"]
        self.assertEqual([f for f in files if f.startswith("threads/")], ["threads/%s.txt" % self.t])
        self.assertTrue(all(f.startswith(("threads/", "prm/")) for f in files), files)
        tdir = _o.path.realpath(transcripts.transcripts_dir())
        for c in r.calls:
            self.assertFalse(c["folder"].startswith(tdir) or tdir.startswith(c["folder"]))
            self.assertNotIn(tdir, c["prompt"])

    def test_planted_export_that_copies_the_transcripts_folder_fails_the_check(self):
        def check(export):
            r = FakeRunner()
            old = lens.export_threads
            lens.export_threads = export
            try:
                lens.run_lenses(DAY, [self.t], (), None, r, SETTINGS)
            finally:
                lens.export_threads = old
            self.assertEqual([f for f in r.calls[0]["files"] if f.startswith("threads/")], ["threads/%s.txt" % self.t])

        real = lens.export_threads
        check(real)

        def leaky2(folder, ids, drop=()):
            out = real(folder, ids, drop)
            shutil.copytree(transcripts.transcripts_dir(), _o.path.join(folder, "threads", "all"))
            return out
        with self.assertRaises(AssertionError):
            check(leaky2)

    def test_a_fake_lens_asking_to_write_gets_nothing_written(self):
        victim = _o.path.join(tempfile.mkdtemp(prefix="p3b-v-"), "owned.txt")
        self.addCleanup(shutil.rmtree, _o.path.dirname(victim), True)
        self.go(FakeRunner({"body": "Please Write the file %s now" % victim}))      # prose is data; nothing executes it
        self.assertFalse(_o.path.exists(victim))

    def test_the_prompts_are_plain_words(self):
        for n, _l, f in lens.LENSES:
            with open(_o.path.join(lens.PROMPT_DIR, f), encoding="utf-8") as fh:
                body = fh.read()
            for old in ("JSON", "cite the ids", "refs", "pre-draft", "Pre-draft"):
                self.assertNotIn(old, body, f)
            for want in ("today's new facts", "plain", "low confidence", "straight double quotes", "only the files in your folder"):
                self.assertIn(want, body, f)
        p = lens.lens_prompt("body", DAY, "FACTS", listing="threads/x.txt")
        self.assertIn("FACTS", p)
        self.assertNotIn("JSON", p)

    def test_render_block_and_snapshot_show_name_text_and_reasons(self):
        st = self.go(FakeRunner({"conflicts": "Two things collide.", "body": (None, "timeout")}), settings=dict(SETTINGS, lanes=None))
        blk, snap = lens.render_block(st), "\n".join(lens.snapshot_lines(st))
        self.assertIn("lens Conflicts:\nTwo things collide.", blk)
        self.assertIn("lens Body and energy: failed (timeout)", blk)
        self.assertIn("lens Lanes: skipped (no lanes defined)", blk)
        self.assertIn("- lens Body and energy failed: timeout", snap)
        self.assertIn("Two things collide.", snap)
        for gone in ("finding_id", "weaker", "REPEAT", "pre-drafted"):
            self.assertNotIn(gone, blk + snap)

    def desk(self, lanes=None, life_map=None, row=True):
        """a temp notes folder with a fake planning desk; lens.desk_list / gc_settings pointed at it"""
        d = tempfile.mkdtemp(prefix="p3b-n-")
        self.addCleanup(shutil.rmtree, d, True)
        _o.makedirs(_o.path.join(d, "desks", "myplan"))
        for name, text in (("lanes.md", lanes), ("life-map.md", life_map)):
            if text is not None:
                with open(_o.path.join(d, "desks", "myplan", name), "w", encoding="utf-8") as f:
                    f.write(text)
        cache = tempfile.mkdtemp(prefix="p3b-c-")          # local_first keeps a copy per relative path; one per test
        self.addCleanup(shutil.rmtree, cache, True)
        old_cache = lens.local_first.cache_root
        lens.local_first.cache_root = lambda: cache
        self.addCleanup(setattr, lens.local_first, "cache_root", old_cache)
        olds = (lens.desk_list.planning_desk_folder, lens.gc_settings.configured_notes_root)
        lens.desk_list.planning_desk_folder = (lambda env=None: ("myplan", None)) if row else (lambda env=None: (None, "no row"))
        lens.gc_settings.configured_notes_root = lambda: d
        self.addCleanup(lambda: (setattr(lens.desk_list, "planning_desk_folder", olds[0]), setattr(lens.gc_settings, "configured_notes_root", olds[1])))
        return d

    def test_lanes_md_in_the_planning_desk_is_used(self):
        self.desk(lanes="# Lanes\n- body\n- work\n", life_map="# Map\nunrelated deep phrase")
        text, note = lens.load_lanes()
        self.assertIn("- work", text)
        self.assertNotIn("unrelated deep phrase", text)
        self.assertIsNone(note)

    def test_no_lanes_md_hands_in_the_whole_life_map(self):
        body = "# Map\n" + "filler line\n" * 200 + "the deep phrase: rank 3 is boats\n"
        self.desk(life_map=body)
        text, note = lens.load_lanes()
        self.assertIn("the deep phrase: rank 3 is boats", text)
        self.assertIn("# Map", text)
        self.assertIsNone(note)
        st = lens.run_lenses(DAY, [], (), None, (r := FakeRunner()), {"lanes": text, "life_map": "x"})
        self.assertIn("the deep phrase: rank 3 is boats", [c for c in r.calls if c["kind"] == "lanes"][0]["prompt"])

    def test_neither_file_skips_with_the_reason(self):
        self.desk()
        self.assertEqual(lens.load_lanes(), (None, "no lanes.md and no Life Map"))
        self.desk(row=False)
        text, note = lens.load_lanes()
        self.assertIsNone(text)
        self.assertTrue(note)

    def test_the_lanes_prompt_carries_the_no_lanes_instruction(self):
        p = lens.lens_prompt("lanes", DAY, "F", lanes="whole life map text")
        for want in ("whole Life Map", "find the lanes", "no lanes, say so in one plain line and stop"):
            self.assertIn(want.lower(), p.lower())

    def test_there_is_no_gc_json_lanes_route(self):
        self.assertNotIn("lanes_file", open(lens.__file__, encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
