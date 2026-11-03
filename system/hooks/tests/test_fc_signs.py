#!/usr/bin/env python3
"""test_fc_signs.py - fine china's street signs (lib/fc_sign.py, plan fix 23(d)) through the WHOLE registered PreToolUse chain, in parallel as the harness runs it.

Payloads are real stdin captured from a live session (Claude Code 2.1.316, 2026-11-03, tests/fixtures/pre_real_stdin_*.json), with only the tool input,
cwd and ids filled in; a sub-agent's call carries the parent's session_id plus its own agent_id. Nothing a payload describes is executed.
Proves: the first attempt is refused with one STOP and one Instead and no word about repeating; the second attempt equals switch OFF; OFF pins today's ask;
each route a sign names passes every hook in every shell shape AFTER its sign fired; near-misses draw no sign; the sheet guide stop's route opens it; the old hole is closed.
Run: python3 system/hooks/tests/test_fc_signs.py     (FC_SIGNS_REPO=<other checkout> runs it against that code: the signs fail on old code)"""
import concurrent.futures as cf
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

TESTS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.realpath(os.environ.get("FC_SIGNS_REPO") or os.path.dirname(os.path.dirname(os.path.dirname(TESTS))))
SHEET = "A" * 44
SWITCHES = ["fc_var_targets", "fc_sign_sops", "fc_sign_canon", "fc_sign_claudemd", "fc_sign_data", "fc_sign_db", "fc_sign_folder", "fc_sign_drive", "fc_sign_conf", "fc_sign_sheet_guide"]
RANK = {"block": 4, "deny": 3, "ask": 2}


def fixture(name):
    with open(os.path.join(TESTS, "fixtures", "pre_real_stdin_%s.json" % name), encoding="utf-8") as f:
        return json.load(f)


def chain(tool):
    with open(os.path.join(REPO, "hooks", "hooks.json"), encoding="utf-8") as f:
        groups = json.load(f)["hooks"]["PreToolUse"]
    out, seen = [], set()
    for g in groups:
        if re.fullmatch(g.get("matcher") or ".*", tool):
            for h in g["hooks"]:
                if not h.get("if") and h["command"] not in seen:
                    seen.add(h["command"])
                    out.append(h["command"])
    return out


class Base(unittest.TestCase):
    n = 0

    @classmethod
    def setUpClass(cls):
        cls.T = os.path.realpath(tempfile.mkdtemp())
        cls.home = os.path.join(cls.T, "home")
        cls.notes = os.path.join(cls.home, "notes")
        cfg = os.path.join(cls.home, ".config", "lifehack")
        for d in (cfg, os.path.join(cls.home, ".claude"), os.path.join(cls.notes, "records"), os.path.join(cls.home, "pc", "tools"), os.path.join(cls.T, "bin")):
            os.makedirs(d)
        with open(os.path.join(cfg, "code-root"), "w", encoding="utf-8") as f:
            f.write(REPO + "\n")
        with open(os.path.join(cfg, "personal-code"), "w", encoding="utf-8") as f:
            f.write(os.path.join(cls.home, "pc") + "\n")
        gws = os.path.join(cls.T, "bin", "gws")
        with open(gws, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\nexit 1\n")
        os.chmod(gws, 0o755)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.T, ignore_errors=True)

    def setUp(self):
        Base.n += 1
        self.sid = "00000000-0000-4000-8000-%012d" % Base.n
        self.cwd = os.path.join(self.notes, "w%d" % Base.n)
        self.tr = os.path.join(self.T, "t%d.jsonl" % Base.n)
        with open(self.tr, "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "user", "sessionId": self.sid, "message": {"role": "user", "content": "test"}}) + "\n")
        self.seed()

    def w(self, rel, txt):
        p = os.path.join(self.cwd, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(txt)

    def seed(self):
        self.w("Archive-2023/a.md", "x\n")
        self.w("Archive-2023/b.md", "y\n")
        self.w("My Folder/a.md", "x\n")
        self.w("canon/voice.md", "# Voice\nWarm.\n")
        self.w("sops/mornings-sop.md", "# Mornings\n1. Water.\n")
        self.w("Thistledown/CLAUDE.md", "# T\n")
        self.w("rates.csv", "client,rate\nA,1\n")
        self.w("pantry.db", "SQLite format 3\n")
        self.w("canon/old.md", "# Old\n")
        self.w("canon/old.proposed.md", "stale\n")
        self.w("old.csv", "a,b\n")
        self.w("old.new.csv", "stale\n")
        self.w("readme.md", "hello\n")
        past = time.time() - 86400
        for root, _d, fs in os.walk(self.cwd):
            for f in fs:
                os.utime(os.path.join(root, f), (past, past))

    def call(self, tool, tin, off=(), on=(), agent=False, sheet_marks=None):
        name = {"Bash": "bash", "Write": "write"}.get(tool, "bash")
        p = fixture(("subagent_" if agent else "") + name)
        p.update(session_id=self.sid, transcript_path=self.tr, cwd=self.cwd, tool_name=tool, tool_input=tin)
        env = {"HOME": self.home, "LIFEHACK_ROOT": self.notes, "PATH": os.path.join(self.T, "bin") + ":/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin", "LANG": "en_US.UTF-8",
               "TMPDIR": self.T, "CLAUDE_PLUGIN_ROOT": REPO, "CLAUDE_PROJECT_DIR": self.cwd, "CLAUDECODE": "1", "GWS_BIN": os.path.join(self.T, "bin", "gws"),
               "SHEET_LLM_MARKDIR": sheet_marks or os.path.join(self.T, "marks-" + self.sid), "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1", "LHB_JOURNAL_DISABLE": "1"}
        for s in off:
            env["ROUNDB_" + s.upper()] = "off"
        for s in on:
            env["ROUNDB_" + s.upper()] = "on"

        def one(cmd):
            argv = shlex.split(cmd.replace("${CLAUDE_PLUGIN_ROOT}", REPO))
            r = subprocess.run(argv, input=json.dumps(p), capture_output=True, text=True, env=env, cwd=self.cwd, timeout=120)
            dec, msg = "allow", ""
            if r.returncode == 2:
                dec, msg = "block", r.stderr.strip()
            elif r.stdout.strip().startswith("{"):
                try:
                    j = json.loads(r.stdout)
                    h = j.get("hookSpecificOutput") or {}
                    if h.get("permissionDecision") in ("ask", "deny"):
                        dec, msg = h["permissionDecision"], h.get("permissionDecisionReason") or ""
                    elif j.get("decision") == "block":
                        dec, msg = "block", j.get("reason") or ""
                except ValueError:
                    pass
            return os.path.basename(argv[1]), dec, msg
        with cf.ThreadPoolExecutor(max_workers=12) as ex:
            res = list(ex.map(one, chain(tool)))
        best = max((r[1] for r in res), key=lambda d: RANK.get(d, 0))
        return best, [r for r in res if r[1] == best and best != "allow"]

    def B(self, c):
        return ("Bash", {"command": c, "description": "x"})

    def W(self, rel, txt="new text\n"):
        return ("Write", {"file_path": os.path.join(self.cwd, rel), "content": txt})

    def assertSign(self, res, *needles):
        best, who = res
        self.assertEqual(best, "block", res)
        signs = [m for _h, _d, m in who if m.startswith("STOP. ")]
        # Only one exit-2 message reaches the model, so every hook that refuses must be showing a sign (Drive and cloud both own a gws drive delete).
        self.assertEqual(len(signs), len(who), "another exit 2 could hide the sign: %r" % (who,))
        self.assertGreaterEqual(len(signs), 1, res)
        for m in signs:
            self.assertEqual(m.count("STOP."), 1, m)
            self.assertEqual(m.count("Instead,"), 1, m)
            self.assertNotRegex(m.lower(), r"retry|again|repeat|second try|goes through|rule:|fc_\w+")
            for n in needles:
                self.assertIn(n, m)
        return signs[0]


class Signs(Base):
    def cases(self):
        c = self.cwd
        return [
            ("fc_sign_sops", self.B("rm sops/mornings-sop.md"), "ask the person"),
            ("fc_sign_sops", self.B("mv sops/mornings-sop.md /tmp/x.md"), "ask the person"),
            ("fc_sign_sops", self.W("sops/mornings-sop.md"), "ask the person"),
            ("fc_sign_canon", self.W("canon/voice.md"), c + "/canon/voice.proposed.md"),
            ("fc_sign_canon", self.B("rm canon/voice.md"), "ask the person"),
            ("fc_sign_claudemd", self.B("rm Thistledown/CLAUDE.md"), "ask the person"),
            ("fc_sign_claudemd", self.W("Thistledown/CLAUDE.md"), "ask the person"),
            ("fc_sign_data", self.W("rates.csv", "x,y\n"), c + "/rates.new.csv"),
            ("fc_sign_data", self.B("truncate -s 0 rates.csv"), c + "/rates.new.csv"),
            ("fc_sign_data", self.B("python3 -c \"open('rates.csv','w').write('')\""), c + "/rates.new.csv"),
            ("fc_sign_data", self.B("rm rates.csv"), "ask the person"),
            ("fc_sign_db", self.B("rm pantry.db"), "ask whether they want it"),
            ("fc_sign_db", self.B(": > pantry.db"), "ask whether they want it"),
            ("fc_sign_db", self.B("sqlite3 pantry.db 'DROP TABLE items'"), "ask whether they want it"),
            ("fc_sign_folder", self.B("rm -rf Archive-2023"), "_archive"),
            ("fc_sign_folder", self.B("find Archive-2023 -delete"), "_archive"),
            ("fc_sign_folder", self.B("python3 -c \"import shutil; shutil.rmtree('Archive-2023')\""), "_archive"),
            ("fc_sign_drive", self.B("gws drive files delete --params '{\"fileId\":\"f1\"}'"), "ask whether they want it"),
            ("fc_sign_drive", self.B("gcloud storage rm gs://b/x"), "ask whether they want it"),
            ("fc_sign_drive", self.B("gws sheets spreadsheets values clear --params '{\"spreadsheetId\":\"%s\",\"range\":\"Log!A:Z\"}'" % SHEET), "ask whether they want it"),
            ("fc_sign_conf", ("Write", {"file_path": os.path.join(self.home, ".config", "lifehack", "placement.conf"), "content": "off\tx\n"}), "exact line"),
            ("fc_sign_conf", self.B("echo x >> ~/.config/lifehack/placement.conf"), "exact line"),
        ]

    def test_first_is_a_sign_second_equals_off_and_off_is_todays(self):
        for i, (sw, (tool, tin), need) in enumerate(self.cases()):
            with self.subTest(sw=sw, call=str(tin)[:70]):
                self.sid = self.sid[:-6] + "%06d" % (900000 + i)
                self.assertSign(self.call(tool, tin), need)
                second = self.call(tool, tin)
                self.sid = self.sid[:-6] + "%06d" % (800000 + i)
                off = self.call(tool, tin, off=SWITCHES)
                self.assertEqual(off[0], "ask", off)
                self.assertEqual(second[0], off[0], (second, off))
                self.assertNotIn("STOP.", " ".join(m for _h, _d, m in second[1]))

    def test_a_drive_trash_tool_call_gets_the_sign_then_the_ask(self):
        tool, tin = "mcp__claude_ai_Google_Drive__trash_file", {"fileId": "1WorkshopDraft01"}
        self.assertSign(self.call(tool, tin), "ask whether they want it")
        self.assertEqual(self.call(tool, tin)[0], "ask")

    def test_each_switch_alone_turns_its_group_off(self):
        seen = set()
        for sw, (tool, tin), _n in self.cases():
            if sw in seen:
                continue
            seen.add(sw)
            with self.subTest(sw=sw):
                self.assertEqual(self.call(tool, tin, off=[sw])[0], "ask")

    def test_a_subagent_gets_its_own_sign(self):
        tool, tin = self.B("rm pantry.db")
        self.assertSign(self.call(tool, tin))
        self.assertEqual(self.call(tool, tin)[0], "ask")
        self.assertSign(self.call(tool, tin, agent=True))
        self.assertEqual(self.call(tool, tin, agent=True)[0], "ask")

    def test_another_tool_on_the_same_target_gets_no_second_sign(self):
        self.assertSign(self.call(*self.B("rm pantry.db")))
        self.assertEqual(self.call(*self.B("python3 -c \"import os; os.remove('pantry.db')\""))[0], "ask")

    def test_several_targets_one_sign_one_route(self):
        m = self.assertSign(self.call(*self.B("rm -rf Archive-2023 'My Folder'")))
        self.assertIn("The same goes for:", m)
        self.assertEqual(self.call(*self.B("rm -rf Archive-2023 'My Folder'"))[0], "ask")

    def test_folder_route_is_quoted_for_a_path_with_a_space(self):
        m = self.assertSign(self.call(*self.B("rm -rf 'My Folder'")))
        self.assertIn(shlex.quote(os.path.join(self.cwd, "My Folder")), m)

    def test_edit_carries_no_sign(self):
        for rel, old in (("sops/mornings-sop.md", "Water"), ("Thistledown/CLAUDE.md", "# T")):
            with self.subTest(rel=rel):
                r = self.call("Edit", {"file_path": os.path.join(self.cwd, rel), "old_string": old, "new_string": "Tea", "replace_all": False})
                self.assertEqual(r[0], "ask", r)

    def test_data_clean_tracked_no_sign_modified_and_untracked_sign(self):
        g = ["git", "-C", self.cwd, "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
        subprocess.run(g + ["init", "-q"], check=True)
        self.w("kept.json", "{\"a\":1}\n")
        self.w("changed.json", "{\"a\":1}\n")
        subprocess.run(g + ["add", "kept.json", "changed.json"], check=True)
        subprocess.run(g + ["commit", "-q", "-m", "x"], check=True, env=dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null"))
        self.w("changed.json", "{\"a\":2}\n")
        self.w("loose.json", "{\"a\":1}\n")
        past = time.time() - 86400
        for f in ("kept.json", "changed.json", "loose.json"):
            os.utime(os.path.join(self.cwd, f), (past, past))
        self.assertEqual(self.call(*self.W("kept.json", "{}\n"))[0], "ask")
        self.assertEqual(self.call(*self.B("rm kept.json"))[0], "ask")
        self.assertSign(self.call(*self.W("changed.json", "{}\n")), "changed.new.json")
        self.assertSign(self.call(*self.W("loose.json", "{}\n")), "loose.new.json")


class Routes(Base):
    def shapes(self, core, probe="."):
        return [core, "true && " + core, "ls %s | wc -l; %s" % (probe, core), "if [ -e /nonexistent ]; then echo clash; else %s; fi" % core,
                "for i in 1; do %s; done" % core, "cd %s && %s" % (shlex.quote(self.cwd), core), "ls %s && %s && ls" % (probe, core)]

    def assertPasses(self, tool, tin):
        r = self.call(tool, tin)
        self.assertEqual(r[0], "allow", (tin, r))

    def test_folder_route_every_shape_after_the_sign(self):
        self.assertSign(self.call(*self.B("rm -rf Archive-2023")))
        for core in ("mkdir -p _archive && mv Archive-2023 _archive/", "mkdir -p _archive && mv -- Archive-2023 _archive/", "mkdir -p _archive; mv -v Archive-2023 _archive/",
                     "mkdir -p %s/_archive && mv -- %s/Archive-2023 %s/_archive/" % (self.cwd, self.cwd, self.cwd)):
            for c in self.shapes(core):
                with self.subTest(c=c):
                    self.assertPasses(*self.B(c))
        self.assertPasses(*self.B("mkdir -p _archive; for d in Archive-2023; do mv -- \"$d\" _archive/; done"))

    def test_canon_route_every_shape_after_the_sign(self):
        self.assertSign(self.call(*self.W("canon/voice.md")), "voice.proposed.md")
        self.assertPasses(*self.W("canon/voice.proposed.md", "x" * 4000))   # longer than the canon rail: a draft is not canon
        self.assertPasses(*self.W("canon/old.proposed.md"))                 # a stale one
        for core in ("printf 'x\\n' > canon/voice.proposed.md", "cp canon/voice.md canon/voice.proposed.md", "cp -- canon/voice.md canon/voice.proposed.md",
                     "printf 'x\\n' > canon/old.proposed.md", "cp canon/voice.md canon/old.proposed.md"):
            for c in self.shapes(core):
                with self.subTest(c=c):
                    self.assertPasses(*self.B(c))
        self.assertPasses(*self.B("cat canon/voice.md | sed s/Warm/Short/ > canon/voice.proposed.md"))
        for core in ("printf 'x\\n' > %s/canon/voice.proposed.md" % self.cwd, "cp -- %s/canon/voice.md %s/canon/old.proposed.md" % (self.cwd, self.cwd)):   # the sign names the absolute path
            for c in self.shapes(core):
                with self.subTest(c=c):
                    self.assertPasses(*self.B(c))

    def test_data_route_every_shape_after_the_sign(self):
        self.assertSign(self.call(*self.W("rates.csv", "x,y\n")), "rates.new.csv")
        self.assertPasses(*self.W("rates.new.csv"))
        self.assertPasses(*self.W("old.new.csv"))   # a stale one
        for core in ("head -1 rates.csv > rates.new.csv", "cp rates.csv rates.new.csv", "cp -- rates.csv rates.new.csv", "printf 'a\\n' > old.new.csv", "cp old.csv old.new.csv"):
            for c in self.shapes(core):
                with self.subTest(c=c):
                    self.assertPasses(*self.B(c))
        self.assertPasses(*self.B("cut -d, -f1 rates.csv | sort > rates.new.csv"))
        self.assertPasses(*self.B("for f in rates.csv; do head -1 \"$f\" > rates.new.csv; done"))


class NearMisses(Base):
    def test_no_sign_and_no_change(self):
        calls = [self.B("ls -la Archive-2023"), self.B("cat rates.csv canon/voice.md sops/mornings-sop.md"), self.B("grep -n rm rates.csv"), self.B("sqlite3 pantry.db .tables"),
                 self.B("cp pantry.db pantry.bak.db"), self.B("cp rates.csv rates.csv.bak"), self.B("echo 'rm -rf Archive-2023' > note.txt"), self.B("du -sh Archive-2023"),
                 self.B("rm readme.md"), self.W("brand-new.csv", "a,b\n"), self.W("canon/brand-new.md", "# x\n"), self.W("sops/brand-new-sop.md", "# x\n"),
                 self.W("Other/CLAUDE.md", "# x\n"), self.B("echo x >> rates.csv"), self.B("cat ~/.config/lifehack/placement.conf"), self.B("rm -rf node_modules __pycache__"),
                 self.B("mv readme.md notes.md"), self.B("gws drive files list --params '{\"q\":\"name=x\"}'"), self.B("echo 'gws drive files delete' > note.txt")]
        for tool, tin in calls:
            with self.subTest(call=str(tin)[:70]):
                on = self.call(tool, tin)
                self.assertNotIn("STOP.", " ".join(m for _h, _d, m in on[1]), on)
                self.assertEqual(on[0], self.call(tool, tin, off=SWITCHES)[0], on)

    def test_a_fresh_file_and_an_empty_folder_draw_no_sign(self):
        self.w("fresh.csv", "a,b\n")
        os.makedirs(os.path.join(self.cwd, "empty"))
        self.assertEqual(self.call(*self.W("fresh.csv", "c\n"))[0], "allow")
        self.assertEqual(self.call(*self.B("rm -rf empty"))[0], "allow")

    def test_a_proposed_name_is_only_exempt_while_the_canon_sign_is_on(self):
        self.assertEqual(self.call(*self.W("canon/old.proposed.md"), off=["fc_sign_canon"])[0], "ask")
        self.assertEqual(self.call(*self.W("old.new.csv"), off=["fc_sign_data"])[0], "ask")


class SheetGuide(Base):
    APPEND = "gws sheets spreadsheets values append --params '{\"spreadsheetId\":\"%s\",\"range\":\"Log!A1\"}' --json '{\"values\":[[1]]}'" % SHEET
    GET = "gws sheets spreadsheets get --params '{\"spreadsheetId\":\"%s\",\"ranges\":\"_LLM_GUIDE!A:Z\"}'" % SHEET

    def marks(self):
        return os.path.join(self.T, "gm-" + self.sid)

    def reader(self):
        return "python3 %s/system/tools/safe_sheets.py %s '_LLM_GUIDE!A:Z'" % (REPO, SHEET)

    def test_stop_names_a_read_that_passes_and_opens_it(self):
        m = self.marks()
        r = self.call(*self.B(self.APPEND), sheet_marks=m)
        msg = self.assertSign(r, "safe_sheets.py", SHEET)
        self.assertNotIn("values get", msg)
        self.assertEqual(self.call(*self.B(self.APPEND), sheet_marks=m)[0], "block")   # the stop keeps its trigger: not a speed bump
        self.assertEqual(self.call(*self.B(self.reader()), sheet_marks=m)[0], "allow")
        self.assertEqual(self.call(*self.B(self.APPEND), sheet_marks=m)[0], "allow")

    def test_the_read_in_every_shape(self):
        for core in (self.reader(), self.reader() + " | head -5", "true && " + self.reader(), "if true; then %s; fi" % self.reader(), "for i in 1; do %s; done" % self.reader()):
            with self.subTest(c=core):
                m = self.marks() + str(abs(hash(core)))
                self.assertEqual(self.call(*self.B(core), sheet_marks=m)[0], "allow")
                self.assertEqual(self.call(*self.B(self.APPEND), sheet_marks=m)[0], "allow")

    def test_a_read_and_a_write_in_one_command_are_judged_as_a_write(self):
        for core in (self.GET + " && " + self.APPEND, self.GET + " ; " + self.APPEND, self.GET + " | " + self.APPEND, "if %s; then %s; fi" % (self.GET, self.APPEND),
                     "for i in 1; do %s; %s; done" % (self.GET, self.APPEND), self.reader() + " && " + self.APPEND):
            with self.subTest(c=core[:50]):
                m = self.marks() + str(abs(hash(core)))
                self.assertEqual(self.call(*self.B(core), sheet_marks=m)[0], "block")
                self.assertFalse(os.path.isdir(m) and os.listdir(m), "the chained read earned a marker")

    def test_a_marker_from_before_lets_the_chain_through(self):
        m = self.marks()
        self.assertEqual(self.call(*self.B(self.reader()), sheet_marks=m)[0], "allow")
        self.assertEqual(self.call(*self.B(self.GET + " && " + self.APPEND), sheet_marks=m)[0], "allow")

    def test_near_misses_a_read_stays_a_read(self):
        for core in (self.GET, self.GET + " | grep update", self.GET + " > update.txt", "gws sheets spreadsheets get --params '{\"spreadsheetId\":\"%s\",\"ranges\":\"append log!A1\"}'" % SHEET):
            with self.subTest(c=core[:70]):
                self.assertEqual(self.call(*self.B(core), sheet_marks=self.marks())[0], "allow")

    def test_off_pins_the_old_text_read_branch_and_marker(self):
        off = ["fc_sign_sheet_guide"]
        m = self.marks()
        r = self.call(*self.B(self.APPEND), sheet_marks=m, off=off)
        self.assertIn("BLOCKED (sheet guard)", " ".join(x[2] for x in r[1]))
        self.assertEqual(self.call(*self.B(self.reader()), sheet_marks=m, off=off)[0], "allow")
        self.assertEqual(self.call(*self.B(self.APPEND), sheet_marks=m, off=off)[0], "block")   # the old missing marker
        self.assertEqual(self.call(*self.B(self.GET + " && " + self.APPEND), sheet_marks=self.marks() + "x", off=off)[0], "allow")   # the old hole


class VarTargets(Base):
    """A path held in a variable set in the same command (live sample, 2026-11-03: f=~/.config/lifehack/placement.conf; printf ... >> "$f" switched a check off with no sign and no ask)."""
    CONF = "~/.config/lifehack/placement.conf"
    LINE = "printf 'off\\tx\\n'"

    def setUp(self):
        super().setUp()
        p = os.path.join(self.home, ".config", "lifehack", "placement.conf")
        with open(p, "w", encoding="utf-8") as f:
            f.write("# mine\n")

    def fresh(self, n):
        self.sid = self.sid[:-6] + "%06d" % n

    def test_switch_file_every_shape(self):
        D = "~/.config/lifehack"
        shapes = ["f=%s; %s >> \"$f\"" % (self.CONF, self.LINE), "f=%s; %s > \"$f\"" % (self.CONF, self.LINE), "f=%s && %s >> \"${f}\"" % (self.CONF, self.LINE),
                  "f=%s\n%s >> \"$f\"" % (self.CONF, self.LINE), "export f=%s; %s >> \"$f\"" % (self.CONF, self.LINE), "f=\"$HOME/.config/lifehack/placement.conf\"; %s >> \"$f\"" % self.LINE,
                  "f=%s; %s | tee -a \"$f\"" % (self.CONF, self.LINE), "f=%s; sed -i '' '1d' \"$f\"" % self.CONF, "f=%s; cp readme.md \"$f\"" % self.CONF, "f=%s; mv readme.md \"$f\"" % self.CONF,
                  "f=%s; python3 -c \"open('$f','a').write('x')\"" % self.CONF, "D=%s; cd \"$D\" && %s >> placement.conf" % (D, self.LINE), "D=%s; %s >> \"$D/placement.conf\"" % (D, self.LINE),
                  "d=~/.config; f=$d/lifehack/placement.conf; %s >> \"$f\"" % self.LINE]
        for i, c in enumerate(shapes):
            with self.subTest(c=c):
                self.fresh(700000 + i)
                self.assertSign(self.call(*self.B(c)), "exact line")
                self.assertEqual(self.call(*self.B(c))[0], "ask")

    def test_an_assignment_inside_an_if_is_still_stopped(self):
        # guard_canon_write's existing stop on a bare unresolved variable already refuses this shape, and stays as it is.
        r = self.call(*self.B("if true; then f=%s; %s >> \"$f\"; fi" % (self.CONF, self.LINE)))
        self.assertEqual(r[0], "block", r)

    def test_a_command_after_a_shell_keyword_is_read(self):
        for i, (c, need) in enumerate((("if [ -d Archive-2023 ]; then rm -rf Archive-2023; fi", "_archive"), ("for i in 1; do rm pantry.db; done", "ask whether they want it"),
                                       ("if true; then echo no; else rm rates.csv; fi", "ask the person"), ("if true; then cp readme.md %s/rates.csv; fi" % self.cwd, "rates.new.csv"))):
            with self.subTest(c=c):
                self.fresh(300000 + i)
                self.assertSign(self.call(*self.B(c)), need)
                self.assertEqual(self.call(*self.B(c))[0], "ask")

    def test_every_sign_group_through_a_variable(self):
        cases = [("f=sops/mornings-sop.md; rm \"$f\"", "ask the person"), ("f=canon/voice.md; rm \"$f\"", "ask the person"), ("f=Thistledown/CLAUDE.md; rm \"$f\"", "ask the person"),
                 ("f=rates.csv; rm \"$f\"", "ask the person"), ("f=rates.csv; printf 'a\\n' > \"$f\"", "rates.new.csv"), ("f=rates.csv; truncate -s 0 \"$f\"", "rates.new.csv"),
                 ("f=pantry.db; rm \"$f\"", "ask whether they want it"), ("f=pantry.db; : > \"$f\"", "ask whether they want it"), ("d=Archive-2023; rm -rf \"$d\"", "_archive"),
                 ("D=%s; cd \"$D\" && rm -rf Archive-2023" % self.cwd, "_archive"), ("D=%s; rm -rf \"$D/Archive-2023\"" % self.cwd, "_archive"), ("for d in Archive-2023; do rm -rf \"$d\"; done", "_archive"),
                 ("f=%s/rates.csv; python3 -c \"open('$f','w').write('')\"" % self.cwd, "rates.new.csv")]
        for i, (c, need) in enumerate(cases):
            with self.subTest(c=c):
                self.fresh(600000 + i)
                self.assertSign(self.call(*self.B(c)), need)
                self.assertEqual(self.call(*self.B(c))[0], "ask")

    def test_canon_or_sop_shell_overwrite_through_a_variable_is_a_sign_not_a_new_block(self):
        for i, (rel, need) in enumerate((("sops/mornings-sop.md", "ask the person"),)):
            self.fresh(500000 + i)
            c = "f=%s/%s; printf 'x\\n' > \"$f\"" % (self.cwd, rel)
            self.assertSign(self.call(*self.B(c)), need)
            self.assertEqual(self.call(*self.B(c))[0], "ask")

    def test_near_misses_stay_as_they_were(self):
        calls = ["f=%s; cat \"$f\"" % self.CONF, "f=%s; grep off \"$f\"" % self.CONF, "f=rates.csv; wc -l \"$f\"", "f=rates.csv; printf 'a\\n' >> \"$f\"", "x=1; echo \"$x\" > note.txt",
                 "f=pantry.db; echo '$f' > note.txt", "f=pantry.db; echo \"\\$f\" > note.txt", "rm -rf \"$NOT_SET_ANYWHERE/x\"", "D=$(pwd); rm -rf \"$D/nothing-here\"", "f=readme.md; rm \"$f\"",
                 "f=brand-new.csv; printf 'a\\n' > \"$f\"", "d=node_modules; rm -rf \"$d\"", "f=pantry.db; ls -la \"$f\"", "f=pantry.db FOO=1 true; echo done"]
        for c in calls:
            with self.subTest(c=c):
                on = self.call(*self.B(c))
                self.assertNotIn("STOP.", " ".join(m for _h, _d, m in on[1]), on)

    def test_a_variable_this_command_does_not_set_behaves_as_today(self):
        for c in ("rm -rf \"$SOMEDIR\"/x", "f=$(cat list.txt); rm -rf \"$f\"", "f=`cat list.txt`; rm -rf \"$f\"", "for d in a b; do rm -rf \"$d\"; done"):
            with self.subTest(c=c):
                a, b = self.call(*self.B(c)), self.call(*self.B(c), off=SWITCHES + ["fc_var_targets"])
                self.assertEqual(a[0], b[0], (a, b))

    def test_the_routes_pass_through_a_variable_too(self):
        for i, c in enumerate(("A=_archive; mkdir -p \"$A\" && mv -- Archive-2023 \"$A/\"", "T=rates.new.csv; head -1 rates.csv > \"$T\"", "T=old.new.csv; printf 'a\\n' > \"$T\"", "P=%s/canon/old.proposed.md; printf 'x\\n' > \"$P\"" % self.cwd)):
            with self.subTest(c=c):
                self.fresh(400000 + i)
                self.assertEqual(self.call(*self.B(c))[0], "allow")

    def test_off_pins_the_old_hole(self):
        c = "f=%s; %s >> \"$f\"" % (self.CONF, self.LINE)
        self.assertEqual(self.call(*self.B(c), off=["fc_var_targets"])[0], "allow")


class SignBeforeCut(Base):
    """Live sample, 2026-11-03: in 8 of 12 canon sessions archive-before-cut fired first, and the session logged a cut that never happened."""

    def long_canon(self):
        self.w("canon/long.md", "# Voice\n" + "A line of the person's own settled voice that would be lost in a replace. " * 4 + "\n")
        past = time.time() - 86400
        os.utime(os.path.join(self.cwd, "canon/long.md"), (past, past))

    def test_the_sign_comes_first_and_leaves_no_history(self):
        self.long_canon()
        tool, tin = self.W("canon/long.md", "# Voice\nShort.\n")
        m = self.assertSign(self.call(tool, tin), "long.proposed.md")
        self.assertNotIn("cutlog", m)
        self.assertFalse(os.path.exists(os.path.join(self.cwd, "canon", "long.history.md")))

    def test_off_and_second_attempt_get_archive_before_cut_as_today(self):
        self.long_canon()
        tool, tin = self.W("canon/long.md", "# Voice\nShort.\n")
        off = self.call(tool, tin, off=["fc_sign_canon"])
        self.assertEqual(off[0], "block")
        self.assertIn("cutlog", " ".join(x[2] for x in off[1]))
        self.assertSign(self.call(tool, tin))
        second = self.call(tool, tin)
        self.assertEqual(second[0], "block")
        self.assertIn("cutlog", " ".join(x[2] for x in second[1]))

    def test_an_edit_that_cuts_still_goes_to_archive_before_cut(self):
        self.long_canon()
        p = os.path.join(self.cwd, "canon/long.md")
        with open(p, encoding="utf-8") as f:
            text = f.read()
        r = self.call("Edit", {"file_path": p, "old_string": text[8:], "new_string": "x", "replace_all": False})
        self.assertEqual(r[0], "block")
        self.assertIn("cutlog", " ".join(x[2] for x in r[1]))


class Fixtures(unittest.TestCase):
    def test_fixtures_carry_the_real_keys(self):
        for name in ("bash", "write", "subagent_bash"):
            p = fixture(name)
            for k in ("session_id", "transcript_path", "cwd", "permission_mode", "hook_event_name", "tool_name", "tool_input", "tool_use_id"):
                self.assertIn(k, p, name)
        self.assertIn("agent_id", fixture("subagent_bash"))
        self.assertNotIn("agent_id", fixture("bash"))

    def test_every_switch_is_a_real_line_with_a_comment(self):
        with open(os.path.join(REPO, "system", "hooks", "roundB.conf"), encoding="utf-8") as f:
            conf = f.read()
        for s in SWITCHES:
            self.assertRegex(conf, r"(?m)^%s=on$" % s)
            self.assertRegex(conf, r"(?m)^# %s:" % s)


if __name__ == "__main__":
    unittest.main(verbosity=1)
