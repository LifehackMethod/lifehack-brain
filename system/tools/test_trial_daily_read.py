#!/usr/bin/env python3
"""test_trial_daily_read.py — the V2 trial daily read, on FIXTURE logs only (never the real ones).

Run: python3 system/tools/test_trial_daily_read.py

Pins: planned asks vs unplanned popups (COMPASS P-72) and how each ask was answered; blocks and hook errors from the
fire journal, inside the window only; the false-alarm hook point (absent / present / failing); new files grouped by
home; flight-log running totals counted once per session; and that the tool writes nothing but its one page.
"""
import json, os, subprocess, sys, tempfile, time, types, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trial_daily_read as tdr  # noqa: E402

NOW = time.time()


def iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + "Z"


def jl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write((r if isinstance(r, str) else json.dumps(r)) + "\n")


def use(tid, t, cmd):
    return {"type": "assistant", "timestamp": iso(t), "sessionId": "s1",
            "message": {"role": "assistant", "content": [{"type": "tool_use", "id": tid, "name": "Bash", "input": {"command": cmd}}]}}


def ask(tid, t, reason):
    out = json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": reason}})
    return {"type": "attachment", "timestamp": iso(t), "sessionId": "s1",
            "attachment": {"type": "hook_success", "hookEvent": "PreToolUse", "toolUseID": tid, "stdout": out,
                           "command": "bash \"${CLAUDE_PLUGIN_ROOT}/system/hooks/guard_fine_china_ask.sh\""}}


def result(tid, t, text, err=False):
    return {"type": "user", "timestamp": iso(t), "sessionId": "s1",
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid, "content": text, "is_error": err}]}}


REJ = "The user doesn't want to proceed with this tool use. The tool use was rejected (eg. if it was a file edit, the new_string was NOT written to the file)."


class Fixture:
    def __init__(self):
        self.T = tempfile.mkdtemp(prefix="tdr-")
        T = self.T
        self.journal = os.path.join(T, "run", "fire-journal.jsonl")
        jl(self.journal, [
            {"ts": NOW - 100, "hook": "guard_a.sh", "event": "PreToolUse", "decision": "deny", "exit_code": 2, "session_id": "s1", "harness": "V2"},
            {"ts": NOW - 200, "hook": "guard_a.sh", "event": "PreToolUse", "decision": "deny", "exit_code": 2, "session_id": "s2", "harness": "V2"},
            {"ts": NOW - 90000, "hook": "guard_old.sh", "event": "PreToolUse", "decision": "deny", "exit_code": 2, "session_id": "s1"},
            {"ts": NOW - 50, "hook": "guard_crash.sh", "event": "PreToolUse", "decision": "deny", "exit_code": 1, "session_id": "s1"},
            {"ts": NOW - 40, "hook": "guard_a.sh", "event": "PreToolUse", "decision": "allow", "exit_code": 0, "session_id": "s1"},
            "not json at all",
        ])
        self.projects = os.path.join(T, "projects")
        t = NOW - 600
        jl(os.path.join(self.projects, "-proj", "s1.jsonl"), [
            use("t1", t, "mv pond.db attic/"), ask("t1", t + 1, "ASK FIRST: moves a database. RULE: switch fc_db_delete_ask in roundB.conf."),
            result("t1", t + 9, "moved"),
            use("t2", t + 20, "rm -r heron"), ask("t2", t + 21, "ASK FIRST: deletes a folder. RULE: switch fc_folder_delete_ask."),
            result("t2", t + 30, REJ, err=True),
            use("t3", t + 40, "sed -n 1,5p frogs.md"), result("t3", t + 50, REJ, err=True),
            use("t4", t + 60, "rm -r reeds"), ask("t4", t + 61, "ASK FIRST: deletes a folder. RULE: switch fc_folder_delete_ask."),
            result("t4", t + 62, "PreToolUse:Bash hook error: [bash guard_b.sh]: BLOCKED", err=True),
            use("t5", t + 70, "rm lilypad.txt"), ask("t5", t + 71, "ASK FIRST: no switch named here"),
            use("t6", NOW - 90000, "rm old"), ask("t6", NOW - 89999, "ASK FIRST: RULE: switch fc_old."), result("t6", NOW - 89990, "ok"),
        ])
        jl(os.path.join(self.projects, "-proj", "s1", "subagents", "agent-x.jsonl"), [
            use("t7", t + 80, "mv canon.md attic/"), ask("t7", t + 81, "ASK FIRST: RULE: switch fc_canon_replace."), result("t7", t + 85, "ok"),
        ])
        self.notes = os.path.join(T, "notes")
        self.code = os.path.join(T, "code")
        os.makedirs(os.path.join(self.notes, "state", "desks"))
        os.makedirs(os.path.join(self.code, "system", "tools"))
        n1 = os.path.join(self.notes, "state", "desks", "pond.md")
        c1 = os.path.join(self.code, "system", "tools", "frog.py")
        for p in (n1, c1):
            with open(p, "w", encoding="utf-8") as f:
                f.write("x\n")
        self.tw = os.path.join(T, "turn-writes")
        jl(os.path.join(self.tw, "s1.list"), [
            "p1\tnew\t%s" % n1, "p1\tnew\t%s" % c1, "p1\tedit\t%s" % os.path.join(self.notes, "edited.md"),
            "p1\tnew\t/nowhere-known-zz/heron.txt", "garbage line"])
        jl(os.path.join(self.notes, "system", "flight-log.jsonl"), [
            {"ts": iso(NOW - 500), "desk": "root", "session": "s1", "tool_calls": 10, "files_written": 1},
            {"ts": iso(NOW - 300), "desk": "root", "session": "s1", "tool_calls": 25, "files_written": 3},
            {"ts": iso(NOW - 300), "desk": "pond", "session": "s2", "tool_calls": 5, "files_written": 0},
            {"ts": iso(NOW - 90000), "desk": "root", "session": "s0", "tool_calls": 999, "files_written": 99},
        ])
        day = time.strftime("%Y-%m-%d", time.localtime(NOW))
        jl(os.path.join(self.notes, "system", "observability", "%s.jsonl" % day), [
            {"ts": iso(NOW - 100), "tool": "Bash", "desk": "root", "session": "s1", "status": "ok"},
            {"ts": iso(NOW - 99), "tool": "Bash", "desk": "root", "session": "s1", "status": "ok"},
            {"ts": iso(NOW - 98), "tool": "Write", "desk": "root", "session": "s1", "status": "ok"},
        ])
        self.hs = [("notes", os.path.realpath(self.notes)), ("plugin code", os.path.realpath(self.code))]

    def build(self, fa=None):
        return tdr.build(self.journal, self.projects, self.tw, self.notes, 24, NOW + 60, fa, hs=self.hs)[1]


class DailyRead(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.F = Fixture()
        cls.page = cls.F.build()

    def test_planned_vs_unplanned(self):
        # planned: t1 Yes, t2 No, t4 blocked by a hook, t5 no answer, t7 (sub-agent) Yes; t6 is outside the window
        self.assertIn("| PLANNED asks (our hooks chose to ask) | 5 | Yes 2 · No 1 · no answer seen 1 · blocked by a hook 1 |", self.page)
        # unplanned: t3 only (a rejected call with NO planned ask on it); t2's rejection is a planned ask, not a popup
        self.assertIn("| UNPLANNED popups (nobody chose them) | 1 (lower bound) | No 1", self.page)
        self.assertIn("`sed -n 1,5p frogs.md`", self.page)

    def test_asks_by_rule_and_answer(self):
        self.assertIn("fc_folder_delete_ask 2", self.page)
        self.assertRegex(self.page, r"fc_db_delete_ask · \*\*Yes\*\* · Bash `mv pond.db attic/`")
        self.assertRegex(self.page, r"fc_folder_delete_ask · \*\*No\*\* · Bash `rm -r heron`")
        self.assertRegex(self.page, r"guard_fine_china_ask.sh · \*\*no answer seen\*\*")   # no RULE line: falls back to the hook name
        self.assertNotIn("fc_old", self.page)

    def test_blocks_and_errors_in_window_only(self):
        self.assertIn("| guard_a.sh | 2 | 2 |", self.page)
        self.assertNotIn("guard_old.sh", self.page)
        self.assertIn("guard_crash.sh rc=1 ×1", self.page)

    def test_false_alarm_hook_point(self):
        self.assertIn("not available yet: system/tools/false_alarm_daily.py", self.page)
        seen = {}

        def fal(journal, hours, now, projects_root):
            seen.update(journal=journal, hours=hours, projects=projects_root)
            return [{"x": 1}]
        fake = types.SimpleNamespace(false_alarm_list=fal, render_markdown=lambda items, now=None, hours=24: "FAKE-FA %d" % len(items))
        page = self.F.build(fa=fake)
        self.assertIn("FAKE-FA 1", page)
        self.assertEqual(seen, {"journal": self.F.journal, "hours": 24, "projects": self.F.projects})

        def boom(**k):
            raise RuntimeError("pond frozen")
        page = self.F.build(fa=types.SimpleNamespace(false_alarm_list=boom, render_markdown=None))
        self.assertIn("false_alarm_daily.py failed: RuntimeError: pond frozen", page)

    def test_new_files_by_home(self):
        self.assertIn("| notes | 1 |", self.page)
        self.assertIn("| plugin code | 1 |", self.page)
        self.assertIn("| elsewhere | 1 |", self.page)
        self.assertIn("`/nowhere-known-zz` (1)", self.page)
        self.assertNotIn("edited.md", self.page)

    def test_flight_log_counts_each_session_once(self):
        self.assertIn("flight log: 2 sessions ended, 30 tool calls, 3 files written", self.page)
        self.assertIn("observability: 3 tool calls; top: Bash 2, Write 1", self.page)

    def test_cli_writes_only_its_page(self):
        F = self.F
        before = {}
        for d, _, fs in os.walk(F.T):
            for f in fs:
                p = os.path.join(d, f)
                before[p] = os.path.getmtime(p)
        home = tempfile.mkdtemp(prefix="tdr-home-")
        env = dict(os.environ, HOME=home)
        args = [sys.executable, os.path.join(HERE, "trial_daily_read.py"), "--journal", F.journal, "--projects", F.projects,
                "--turn-writes", F.tw, "--notes", F.notes, "--now", str(NOW + 60)]
        p = subprocess.run(args + ["--stdout"], capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("## Popups (COMPASS P-72)", p.stdout)
        p = subprocess.run(args, capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        day = time.strftime("%Y-%m-%d", time.localtime(NOW + 60))
        out = os.path.join(F.notes, "state", "projects", "v2", "trial", "%s-daily.md" % day)
        self.assertEqual(p.stdout.strip(), out)
        self.assertTrue(os.path.isfile(out))
        after = {}
        for d, _, fs in os.walk(F.T):
            for f in fs:
                q = os.path.join(d, f)
                after[q] = os.path.getmtime(q)
        self.assertEqual(set(after) - set(before), {out})
        self.assertEqual({k: v for k, v in after.items() if k in before}, before)


class JournalAskFixture(Fixture):
    """The same transcripts, plus fire-journal ASK rows (journal.sh records decision "ask" since journal-records-ask)."""
    def __init__(self):
        super().__init__()
        t = NOW - 600
        FC, ANY = "guard_fine_china_ask.sh", "Bash|Write|Edit|MultiEdit"
        jl(self.journal, [
            {"ts": NOW - 40, "hook": "guard_a.sh", "event": "PreToolUse", "decision": "allow", "exit_code": 0, "session_id": "s1"},
            # pre-fix row: an ask that exited 0 and was journaled "allow" -- must stay an allow, never be re-read as an ask
            {"ts": t + 71, "hook": FC, "event": "PreToolUse", "matcher": ANY, "decision": "allow", "exit_code": 0, "session_id": "s1"},
            # matches transcript ask t1 (same session, Bash in the matcher, 0.5 s apart)
            {"ts": int(t + 1), "hook": FC, "event": "PreToolUse", "matcher": ANY, "decision": "ask", "exit_code": 0, "session_id": "s1"},
            # matches t4 (t5 is 10 s away; the nearest wins and each transcript ask is used once)
            {"ts": int(t + 61), "hook": FC, "event": "PreToolUse", "matcher": ANY, "decision": "ask", "exit_code": 0, "session_id": "s1"},
            # journal-only: another session at the same moment as t2 -- the session is part of the key
            {"ts": int(t + 21), "hook": FC, "event": "PreToolUse", "matcher": ANY, "decision": "ask", "exit_code": 0, "session_id": "s2"},
            # journal-only: right session, but no transcript ask within 30 s
            {"ts": int(t + 300), "hook": "guard_sheet_writes.sh", "event": "PreToolUse", "matcher": "Bash", "decision": "ask", "exit_code": 0, "session_id": "s1"},
            # journal-only: a session with no transcript at all (headless)
            {"ts": NOW - 30, "hook": "guard_cloud_destructive.sh", "event": "PreToolUse", "matcher": "Bash", "decision": "ask", "exit_code": 0, "session_id": "s9"},
            # journal-only would be wrong here: right session and time as t1, but a Write-only hook cannot be t1's Bash ask
            {"ts": int(t + 1), "hook": "guard_organism_map.sh", "event": "PreToolUse", "matcher": "Write", "decision": "ask", "exit_code": 0, "session_id": "s1"},
            # outside the window
            {"ts": NOW - 90000, "hook": FC, "event": "PreToolUse", "matcher": ANY, "decision": "ask", "exit_code": 0, "session_id": "s1"},
            # the journal could not parse the hook's decision JSON
            {"ts": NOW - 20, "hook": "guard_odd.sh", "event": "PreToolUse", "matcher": "Bash", "decision": "unknown", "exit_code": 0, "session_id": "s1"},
        ])


class JournalAsks(unittest.TestCase):
    """trial-read-journal-ask: journal asks counted, merged with transcript asks without double counting, unknown shown apart."""
    @classmethod
    def setUpClass(cls):
        cls.F = JournalAskFixture()
        cls.page = cls.F.build()

    def test_transcript_row_unchanged(self):
        # the 5 transcript asks are still 5: the 2 journal asks that match them are NOT added on top
        self.assertIn("| PLANNED asks (our hooks chose to ask) | 5 | Yes 2 · No 1 · no answer seen 1 · blocked by a hook 1 |", self.page)

    def test_journal_only_asks_counted_once(self):
        self.assertIn("| PLANNED asks seen only in the fire journal (no transcript has them) | 4 | answer not visible in the journal |", self.page)
        self.assertIn("Fire journal: 6 asks in window; 2 matched a transcript ask (same session, same tool, within 30 s), 4 journal-only.", self.page)

    def test_journal_only_asks_listed(self):
        self.assertRegex(self.page, r"guard_cloud_destructive.sh · \*\*journal only\*\* · session s9")
        self.assertRegex(self.page, r"guard_sheet_writes.sh · \*\*journal only\*\* · session s1")
        self.assertRegex(self.page, r"guard_fine_china_ask.sh · \*\*journal only\*\* · session s2")
        self.assertRegex(self.page, r"guard_organism_map.sh · \*\*journal only\*\* · session s1")

    def test_unknown_shown_separately(self):
        self.assertIn("Journal rows with decision unknown (the hook's decision JSON could not be parsed): guard_odd.sh ×1", self.page)

    def test_pre_fix_allow_rows_stay_allows(self):
        # the pre-fix row (decision allow, exit 0) is neither an ask nor an unknown: 6 asks exactly, one unknown
        self.assertNotIn("7 asks in window", self.page)
        self.assertNotIn("guard_a.sh ×", self.page)

    def test_no_journal_asks_says_none(self):
        page = Fixture().build()   # the old-style journal: no ask rows at all
        self.assertIn("Fire journal: 0 asks in window.", page)
        self.assertIn("| PLANNED asks seen only in the fire journal (no transcript has them) | 0 |", page)
        self.assertIn("Journal rows with decision unknown (the hook's decision JSON could not be parsed): none", page)


if __name__ == "__main__":
    unittest.main(verbosity=1)
