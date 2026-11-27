#!/usr/bin/env python3
"""Tests for round 2c: the wave table (waves.json), the renderer that turns it into the injected text, the receipt check, and the
writer's input / receipt (sb_spec.build_turn_input, apply_and_mark). Code hands over the list; the AI runs it; code checks the
receipts: every one of those three is exercised here, with the receipt check shown present / missing / stale-from-an-earlier-turn.
stdlib unittest; every folder is a temporary one."""

import json
import os
import re
import sys
import tempfile
import time
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(os.path.dirname(TESTS_DIR))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(SKILL)))
HOOKS = os.path.join(REPO, "system", "hooks")
LIB = os.path.join(HOOKS, "lib")
SID = "wavesess1"
SPEC = """# Draft spec

## 1. WHAT
- Receipts are sorted by vendor [inferred]
- The skill reads <[ask] what the skill reads first>

## ROUTED NOTES
"""


def load():
    home = tempfile.mkdtemp(prefix="sbwaves-")
    os.environ["HOME"] = home
    if LIB not in sys.path:
        sys.path.insert(0, LIB)
    import sb_spec
    import sb_waves
    return sb_spec, sb_waves, home


class Base(unittest.TestCase):
    def setUp(self):
        self.sb, self.wv, self.home = load()
        self.wd = os.path.join(self.home, "design")
        self.run = os.path.join(self.wd, "runs", "r1")
        os.makedirs(self.run)
        with open(os.path.join(self.wd, "draft-spec.md"), "w", encoding="utf-8") as f:
            f.write(SPEC)
        self.table = self.wv.load(REPO)

    def render(self, step, moment, pid="p1", prompt="my answer", tp="", complete=False, visit=True):
        st = {"index": step, "total": 6, "complete": complete, "skill": "skill-builder"}
        return self.wv.render(REPO, HOOKS, self.wd, self.run, st, SID, pid, moment, prompt, tp, visit)

    def brief(self, pid, job):
        with open(os.path.join(self.wv.turn_dir(self.run, pid), "briefs", job + ".md"), encoding="utf-8") as f:
            return f.read()

    def section(self, name, text="x"):
        d = os.path.join(self.wd, "scratchpad")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, name + ".md"), "w", encoding="utf-8") as f:
            f.write(text)

    def output(self, pid, name, text="done\n", age=0):
        d = os.path.join(self.run, "waves", pid)
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        if age:
            t = time.time() - age
            os.utime(p, (t, t))
        return p


class TableTest(Base):
    def test_every_step_and_both_moments_exist(self):
        for k in ("1", "2", "3", "4", "5", "6", "done"):
            self.assertIn(k, self.table["steps"], k)
            for m in ("start", "answer"):
                self.assertIn(m, self.table["steps"][k], "%s %s" % (k, m))

    def test_every_job_in_a_list_is_defined_and_well_formed(self):
        for k, step in self.table["steps"].items():
            for m in ("start", "answer"):
                for w in step[m]:
                    for ent in w["jobs"]:
                        jid = ent if isinstance(ent, str) else ent["id"]
                        self.assertIn(jid, self.table["jobs"], "%s/%s %s" % (k, m, jid))
                    if w.get("optional"):
                        self.assertTrue(w.get("when"), "an optional wave names its condition (%s/%s)" % (k, m))
        for jid, j in self.table["jobs"].items():
            self.assertIn(j["kind"], ("agent", "bash"), jid)
            self.assertTrue(j.get("brief") or j.get("cmd"), jid)
            if j["kind"] == "agent":
                self.assertIn(j["tier"], self.table["tiers"], jid)

    def test_no_job_repeats_in_one_moment_and_outputs_do_not_collide(self):
        for k, step in self.table["steps"].items():
            for m in ("start", "answer"):
                ids, outs = [], {}
                for w in step[m]:
                    for ent in w["jobs"]:
                        j = self.wv._entry(self.table, ent)
                        ids.append(j["id"])
                        self.assertNotIn(j["out"], outs, "%s/%s: %s and %s write the same file" % (k, m, j["id"], outs.get(j["out"])))
                        outs[j["out"]] = j["id"]
                self.assertEqual(len(ids), len(set(ids)), "%s/%s repeats a job" % (k, m))

    def test_every_brief_file_named_exists_and_every_token_resolves(self):
        ctx = self.wv.make_ctx(REPO, HOOKS, self.wd, self.run, SID, "p1", self.table, "5")
        for jid, j in self.table["jobs"].items():
            text = j.get("brief") or j.get("cmd")
            for m in re.finditer(r"\{B:([^}]+)\}", text):
                self.assertTrue(os.path.isfile(os.path.join(SKILL, "prompts", "subagents", m.group(1) + ".md")), "%s: %s" % (jid, m.group(1)))
            out = self.wv.resolve(text + " " + self.wv.TAIL, ctx, self.table, self.wv._entry(self.table, jid))
            self.assertNotRegex(out, r"\{[A-Za-z]+(:[^}]*)?\}", "%s has an unresolved token: %s" % (jid, out))

    def test_a_checker_is_its_own_agent_call_after_its_worker_and_no_job_names_a_model_rule(self):
        pairs = {"save-check": "writer", "skill-check": "skill-reader", "harness-check": "harness-search", "step-check": "step-drafter",
                 "heal-check": "healer", "spec-check-a": "spec-updater-a", "validation-check": "validation-update",
                 "draft-check": "compiler", "tensions-check": "proposer"}
        for chk, worker in pairs.items():
            c = self.table["jobs"][chk]
            self.assertEqual(c["kind"], "agent", chk)                       # its own Agent call (so its own brief file and token)
            self.assertIn(worker, c["needs_out"], chk)
        text = json.dumps(self.table).lower()
        self.assertNotIn("different model", text)
        self.assertNotIn("same_tier_ok", text)

    def test_every_tier_a_job_names_exists_in_the_tier_table(self):
        for jid, j in self.table["jobs"].items():
            if j["kind"] == "agent":
                self.assertIn(j["tier"], self.table["tiers"], jid)

    def test_the_spec_names_every_helper_the_table_covers(self):
        covered = set()
        for j in self.table["jobs"].values():
            covered.update(re.findall(r"\{B:([^}]+)\}", j.get("brief") or ""))
        folder = os.path.join(SKILL, "prompts", "subagents")
        briefs = {f[:-3] for f in os.listdir(folder) if f.endswith(".md") and f != "README.md"}
        # spec-writer reaches its helper through the writer's input file (code builds it: sb_spec.build_turn_input), packet-writer is
        # the 3.4 writer the 2f spec-writer replaced; the two bases are named inside their uses
        self.assertEqual(sorted(briefs - covered - {"packet-writer", "spec-writer"}), [], "a helper brief no wave runs")

    def test_a_checker_follows_every_checked_worker_in_an_earlier_wave(self):
        for k, step in self.table["steps"].items():
            for m in ("start", "answer"):
                seen = set()
                for w in step[m]:
                    for ent in w["jobs"]:
                        j = self.wv._entry(self.table, ent)
                        for d in j.get("needs_out", []):
                            if d in [e if isinstance(e, str) else e["id"] for ww in step[m] for e in ww["jobs"]]:
                                self.assertIn(d, seen, "%s/%s: %s must come after %s" % (k, m, j["id"], d))
                    seen.update(e if isinstance(e, str) else e["id"] for e in w["jobs"])


class RenderTest(Base):
    def test_answer_moment_step_1_hands_over_the_waves_in_order(self):
        lines = self.render(1, "answer", prompt="I want a receipt sorter")
        text = "\n".join(lines)
        self.assertIn("1. Your reply's FIRST line, exactly: saving your answers and running checks…", text)
        self.assertLess(text.index("writer — "), text.index("save-check — "))
        self.assertLess(text.index("save-check — "), text.index("questioner — "))
        self.assertIn("Agent, model haiku (small tier)", text)       # the writer
        self.assertIn("Agent, model sonnet (medium tier)", text)
        self.assertIn("PROMPT, pass exactly (you may add context, never drop the [token]): ⟦Read ", text)
        self.assertIn("sb_spec.py apply", self.brief("p1", "writer"))   # the writer's command lives in its brief file, not in the list
        self.assertNotIn("sb_spec.py apply", text)
        self.assertIn("run with Bash, exactly: ⟦", text)             # the citation check
        self.assertIn("questions.md", text)
        self.assertIn("never from this conversation", text.replace("Never invent a question from this conversation", "never from this conversation"))

    def test_the_brief_is_the_tables_own_words_in_a_file_and_the_list_carries_a_one_line_prompt(self):
        self.section("outcome", "a receipt sorter")
        text = "\n".join(self.render(1, "answer"))
        td = self.wv.turn_dir(self.run, "p1")
        for jid in ("harness-search", "size-sense"):
            head = re.sub(r"\{[^}]+\}.*", "", self.table["jobs"][jid]["brief"])
            self.assertIn(head, self.brief("p1", jid))
        b = self.brief("p1", "harness-search")
        self.assertIn(os.path.join(SKILL, "prompts", "subagents", "harness-search.md"), b)
        self.assertIn(os.path.join(td, "harness-findings.md"), b)
        rec = json.load(open(os.path.join(td, "turn.json"), encoding="utf-8"))
        job = next(j for j in rec["jobs"] if j["id"] == "harness-search")
        self.assertEqual(job["prompt"], "Read %s and do exactly what it says. [%s]" % (os.path.join(td, "briefs", "harness-search.md"), job["token"]))
        self.assertIn("⟦" + job["prompt"] + "⟧", text)
        self.assertNotIn("Inputs:", text)                              # no brief text in the injected list

    def test_tokens_are_fresh_per_turn_and_per_job_and_not_guessable(self):
        self.section("outcome", "x")
        toks = []
        for pid in ("p1", "p2"):
            self.render(1, "answer", pid=pid)
            rec = json.load(open(os.path.join(self.wv.turn_dir(self.run, pid), "turn.json"), encoding="utf-8"))
            toks += [j["token"] for j in rec["jobs"] if j["kind"] == "agent"]
            self.assertIn(rec["jobs"][0]["token"], self.brief(pid, rec["jobs"][0]["id"]))
        self.assertEqual(len(toks), len(set(toks)))
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{12}", t) for t in toks))

    def test_the_injected_list_is_small(self):
        self.section("outcome", "a receipt sorter")
        n1 = len("\n".join(self.render(1, "answer", pid="s1")))
        self.assertLess(n1, 6500, n1)
        self.output("s5", "spec-update-checked.md")
        n5 = len("\n".join(self.render(5, "answer", pid="s5a")))
        self.assertLess(n5, 9000, n5)

    def test_the_turns_folder_holds_the_persons_words_the_writers_input_and_the_receipt_list(self):
        self.render(1, "answer", prompt="Sort my receipts by date, please")
        td = self.wv.turn_dir(self.run, "p1")
        self.assertIn("Sort my receipts by date, please", open(os.path.join(td, "person.md"), encoding="utf-8").read())
        win = open(os.path.join(td, "writer-input.md"), encoding="utf-8").read()
        self.assertIn("Sort my receipts by date, please", win)
        self.assertIn("THE DRAFT SPEC (current)", win)
        self.assertNotIn("TEST CARD", win)
        rec = json.load(open(os.path.join(td, "turn.json"), encoding="utf-8"))
        ids = [j["id"] for j in rec["jobs"]]
        self.assertEqual(ids[0], "writer")
        self.assertIn("questioner", ids)
        self.assertEqual([j["receipt"] for j in rec["jobs"] if j["id"] == "writer"], ["writer.md.applied"])
        self.assertTrue(os.path.isfile(os.path.join(self.sb.od(), "spec-wave-%s.json" % SID)))

    def test_nothing_is_written_into_the_cwd(self):
        cwd = os.path.join(self.home, "cwd")
        os.makedirs(cwd)
        old = os.getcwd()
        os.chdir(cwd)
        try:
            self.render(1, "answer")
        finally:
            os.chdir(old)
        self.assertEqual(os.listdir(cwd), [])

    def test_first_screen_of_a_step_has_no_writer(self):
        self.assertEqual(self.render(1, "start"), [])                 # step 1: nothing to run at the start
        text = "\n".join(self.render(5, "start", pid="p5"))
        self.assertIn("running checks…", text)
        self.assertNotIn("saving your answers", text)
        self.assertNotIn("writer — ", text)
        self.assertLess(text.index("spec-updater-a — "), text.index("spec-check-a — "))
        self.assertLess(text.index("spec-check-a — "), text.index("questioner — "))

    def test_start_moment_logs_the_visit(self):
        self.render(5, "start", pid="p5")
        self.assertGreater(self.wv.visit_t(self.run, "5"), 0)

    def test_the_three_outcome_helpers_wait_for_the_outcome_and_run_again_when_it_changes(self):
        self.render(1, "start", pid="s1")
        first = "\n".join(self.render(1, "answer", pid="a1"))
        self.assertNotIn("harness-search — ", first)               # no outcome written yet: said loudly, not silently
        self.assertIn("NOT RUN YET: `outcome` is not written yet", first)
        self.section("outcome", "a receipt sorter")
        second = "\n".join(self.render(1, "answer", pid="a2"))
        for j in ("harness-search", "research-mark", "size-sense"):
            self.assertIn(j + " — ", second)
        self.assertNotIn("NOT RUN YET", second)
        for j, n in (("harness-search", "harness-findings.md"), ("research-mark", "research-mark.md"), ("size-sense", "size-sense.md")):
            self.output("a2", n)
        third = "\n".join(self.render(1, "answer", pid="a3"))
        self.assertNotIn("harness-search — ", third)                # done for this outcome
        self.assertIn("writer — ", third)                           # the writer runs on every answer
        time.sleep(0.05)
        self.section("outcome", "a receipt sorter that also pings me")   # the framed outcome changed
        fourth = "\n".join(self.render(1, "answer", pid="a4"))
        self.assertIn("harness-search — ", fourth)

    def test_a_checker_is_not_run_again_while_its_producer_is_done(self):
        self.section("outcome", "x")
        self.output("a1", "harness-findings.md")
        time.sleep(0.05)
        self.output("a1", "harness-checked.md")
        text = "\n".join(self.render(1, "answer", pid="a2"))
        self.assertNotIn("harness-check — ", text)
        self.assertNotIn("harness-search — ", text)
        os.remove(os.path.join(self.run, "waves", "a1", "harness-checked.md"))   # the producer ran but its checker never did
        self.assertIn("harness-check — ", "\n".join(self.render(1, "answer", pid="a3")))

    def test_a_resume_is_not_a_new_visit(self):
        self.render(5, "start", pid="s5")
        t = self.wv.visit_t(self.run, "5")
        time.sleep(0.05)
        self.render(5, "start", pid="s5b", visit=False)
        self.assertEqual(self.wv.visit_t(self.run, "5"), t)
        self.render(5, "start", pid="s5c")
        self.assertGreater(self.wv.visit_t(self.run, "5"), t)

    def test_the_questioner_wave_is_gated_on_the_writers_receipt_and_dropped_when_the_writer_is_held(self):
        text = "\n".join(self.render(1, "answer", pid="a1"))
        self.assertIn("Run it ONLY if", text)
        self.assertIn("writer.md.applied (in the turn's folder) exists and its first word is APPLIED", text)
        os.unlink(os.path.join(self.wd, "draft-spec.md"))
        text = "\n".join(self.render(1, "answer", pid="a2"))
        self.assertNotIn("questioner — ", text)

    def test_a_job_that_needs_a_section_is_left_out_until_it_exists(self):
        self.assertNotIn("healer — ", "\n".join(self.render(4, "answer", pid="a1")))
        self.section("break", "the sort step failed")
        text = "\n".join(self.render(4, "answer", pid="a2"))
        self.assertIn("healer — ", text)
        self.assertIn("scratchpad", self.brief("a2", "healer"))

    def test_the_reviewers_are_held_back_until_the_spec_check_has_a_file(self):
        self.render(5, "start", pid="s5")                              # the 4.0a waves are listed, but no file exists yet
        text = "\n".join(self.render(5, "answer", pid="a1"))
        self.assertIn("HELD BACK BY CODE: reviewer-screens", text)
        self.assertNotIn("reviewer-screens — ", text)
        self.output("s5", "spec-update-checked.md")
        text = "\n".join(self.render(5, "answer", pid="a2"))
        self.assertNotIn("HELD BACK BY CODE", text)
        self.assertIn("reviewer-screens — ", text)
        order = [text.index(n + " — ") for n in ("reviewer-screens", "reviewer-order", "research-pass", "proposer", "tensions-check", "questioner")]
        self.assertEqual(order, sorted(order))

    def test_optional_waves_say_when_and_are_not_receipt_checked(self):
        self.output("s5", "spec-update-checked.md")
        self.render(5, "start", pid="s5")
        self.output("s5", "spec-update-checked.md")
        self.render(5, "answer", pid="a1")
        rec = json.load(open(os.path.join(self.wv.turn_dir(self.run, "a1"), "turn.json"), encoding="utf-8"))
        self.assertNotIn("validation-update", [j["id"] for j in rec["jobs"]])

    def test_a_failed_receipt_last_turn_is_the_line_right_after_the_first_line_and_said_once(self):
        os.makedirs(os.path.join(self.run, "waves"), exist_ok=True)
        with open(os.path.join(self.run, "waves", "receipt-warn.txt"), "w", encoding="utf-8") as f:
            f.write("1 of 3 back-room jobs from last turn left no file: wave 2, save-check.")
        lines = self.render(1, "answer", pid="a1")
        i = next(n for n, l in enumerate(lines) if l.startswith("1. Your reply's FIRST line"))
        self.assertTrue(lines[i + 1].startswith("2. RECEIPT CHECK FAILED LAST TURN: 1 of 3 back-room jobs"), lines[i + 1])
        self.assertFalse(os.path.exists(os.path.join(self.run, "waves", "receipt-warn.txt")))
        self.assertNotIn("RECEIPT CHECK FAILED", "\n".join(self.render(1, "answer", pid="a2")))

    def test_the_results_line_lists_only_checked_results(self):
        self.output("s1", "harness-findings.md")                       # unchecked: never listed
        self.output("s1", "harness-checked.md")
        text = "\n".join(self.render(2, "answer", pid="a1"))
        self.assertIn("harness-checked →", text)
        self.assertNotIn("harness-findings", text.split("WAVES FOR THIS TURN")[0])

    def test_the_final_handover_lists_the_hand_off_note(self):
        text = "\n".join(self.render(6, "start", pid="done1", complete=True))
        self.assertIn("handoff-note — ", text)
        self.assertNotIn("compiler — ", text)

    def test_a_twin_copy_of_the_hook_hands_over_the_list_once(self):
        a = self.render(1, "answer", pid="twin")
        b = self.render(1, "answer", pid="twin")
        self.assertTrue(a)
        self.assertEqual(b, [])

    def test_a_missing_table_is_one_plain_line(self):
        st = {"index": 1, "total": 6, "complete": False}
        out = self.wv.render(os.path.join(self.home, "no-plugin"), HOOKS, self.wd, self.run, st, SID, "p9", "answer", "x", "")
        self.assertEqual(len(out), 1)
        self.assertIn("WAVE LIST UNAVAILABLE", out[0])

    def test_no_draft_spec_holds_the_writer_back_loudly(self):
        os.unlink(os.path.join(self.wd, "draft-spec.md"))
        text = "\n".join(self.render(1, "answer", pid="a1"))
        self.assertIn("HELD BACK BY CODE: writer", text)
        self.assertNotIn("writer — ", text)
        self.assertNotIn("save-check — ", text)


class SpacedPathTest(Base):
    """The owner's real notes folder has 'My Drive' in its path: every substituted path must stay one word."""

    def setUp(self):
        super().setUp()
        self.wd = os.path.join(self.home, "My Drive", "brain", "drafts", "builds", "demo")
        self.run = os.path.join(self.wd, "runs", "r1")
        os.makedirs(self.run)
        with open(os.path.join(self.wd, "draft-spec.md"), "w", encoding="utf-8") as f:
            f.write(SPEC)
        with open(os.path.join(self.wd, "notes.md"), "w", encoding="utf-8") as f:
            f.write("## SAID\n- nothing cited\n")

    def jobs(self, step="1", pid="p1"):
        self.section("outcome", "x")
        lines = self.render(int(step), "answer", pid=pid, prompt="sort my receipts")
        return lines

    def test_a_bash_job_runs_in_a_spaced_folder(self):
        import subprocess
        lines = self.jobs()
        cmd = next(l for l in lines if l.startswith("  • citations —"))
        cmd = re.search(r"⟦(.*)⟧", cmd).group(1)
        os.makedirs(self.wv.turn_dir(self.run, "p1"), exist_ok=True)
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
        self.assertIn("== notes.md", r.stdout, r.stdout + r.stderr)
        self.assertIn("all 0 packet citation(s) exist", r.stdout)
        out = os.path.join(self.wv.turn_dir(self.run, "p1"), "citations.txt")
        self.assertTrue(os.path.getsize(out) > 0)

    def test_the_backup_cmd_copies_in_a_spaced_folder(self):
        import subprocess
        st = {"index": 6, "total": 6, "complete": False}
        lines = self.wv.render(REPO, HOOKS, self.wd, self.run, st, SID, "p6", "start", "", "")
        cmd = re.search(r"⟦(cp .*?)⟧", "\n".join(lines)).group(1)
        self.assertTrue(subprocess.run(["bash", "-c", cmd], capture_output=True).returncode == 0, cmd)
        self.assertTrue(os.path.isfile(os.path.join(self.wv.turn_dir(self.run, "p6"), "draft-spec.before-compile.md")))

    def test_the_writers_command_gets_the_whole_run_folder(self):
        import shlex
        self.jobs()
        text = self.brief("p1", "writer")
        cmd = re.search(r"report the line it prints: (python3 .*?)   It applies|report the line it prints: (python3 .*?) It applies", text)
        cmd = [g for g in cmd.groups() if g][0]
        argv = shlex.split(cmd)
        self.assertEqual(argv[-1], self.wd)                     # the folder with the space is ONE argument
        self.assertEqual(argv[-3], os.path.join(self.wv.turn_dir(self.run, "p1"), "writer.md"))
        with open(argv[-3], "w", encoding="utf-8") as f:
            f.write("SAID: sort my receipts\n---\nEND-WRITE\n")
        with open(os.path.join(self.wv.turn_dir(self.run, "p1"), "evidence.json"), encoding="utf-8") as f:
            self.assertIn("sort my receipts", f.read())
        res = self.sb.apply_and_mark(REPO, argv[-3], argv[-1], SID)
        self.assertTrue(res.startswith("APPLIED"), res)

    def test_prose_briefs_quote_a_spaced_path(self):
        self.jobs()
        self.assertIn('"%s"' % os.path.join(self.wd, "draft-spec.md"), self.brief("p1", "save-check"))
        text = "\n".join(self.jobs(pid="p2"))
        bp = os.path.join(self.wv.turn_dir(self.run, "p2"), "briefs", "save-check.md")
        self.assertIn('Read "%s" and do exactly what it says. [' % bp, text)   # a spaced path stays one word in the one-line prompt too


class ProofTest(Base):
    """A receipt file is not enough: the transcript must hold this turn's real helper call (the list's own prompt, the model it names)."""

    def setUp(self):
        super().setUp()
        self.section("outcome", "a receipt sorter")
        self.render(1, "answer", pid="t1", prompt="Sort my receipts by date")
        self.td = self.wv.turn_dir(self.run, "t1")
        self.rec = json.load(open(os.path.join(self.td, "turn.json"), encoding="utf-8"))
        self.tp = os.path.join(self.home, "t.jsonl")

    def calls_for(self, jobs):
        out = []
        for j in jobs:
            if j["kind"] == "agent":
                out.append({"type": "tool_use", "name": "Agent", "input": {"model": j["model"], "prompt": j["prompt"]}})
            else:
                out.append({"type": "tool_use", "name": "Bash", "input": {"command": j["cmd"]}})
        return out

    def transcript(self, blocks):
        with open(self.tp, "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "user", "message": {"role": "user", "content": "Sort my receipts by date"}}) + "\n")
            f.write(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": blocks}}) + "\n")

    def files(self, skip=()):
        for j in self.rec["jobs"]:
            if j["id"] not in skip:
                self.output("t1", j["receipt"], "APPLIED spec=1 packet=1 (skipped 0) rejected=0\n" if j["receipt"].endswith(".applied") else "ok\n")

    def test_files_and_real_helper_calls_pass(self):
        self.files()
        self.transcript(self.calls_for(self.rec["jobs"]))
        self.assertEqual(self.wv.check(SID, self.tp), [])

    def test_a_file_the_ai_wrote_itself_does_not_pass(self):
        self.files()
        self.transcript(self.calls_for([j for j in self.rec["jobs"] if j["id"] != "save-check"]))
        problems = self.wv.check(SID, self.tp)
        self.assertEqual(len(problems), 1)
        self.assertIn("save-check", problems[0])
        self.assertIn("no helper call", problems[0])

    def test_a_hand_written_applied_receipt_does_not_pass_without_the_writer_helper(self):
        self.files()
        self.transcript(self.calls_for([j for j in self.rec["jobs"] if j["id"] != "writer"]))
        problems = self.wv.check(SID, self.tp)
        self.assertEqual(len(problems), 1)
        self.assertIn("writer", problems[0])

    def test_a_call_that_lacks_the_token_or_names_the_wrong_model_does_not_pass(self):
        self.files()
        calls = self.calls_for(self.rec["jobs"])
        for j, c in zip(self.rec["jobs"], calls):
            if j["id"] == "save-check":
                c["input"]["model"] = "haiku"
            if j["id"] == "questioner":   # a prompt the AI wrote itself: no brief, no token
                c["input"]["prompt"] = "Ask the person three questions about the Kestrel card."
        self.transcript(calls)
        problems = " | ".join(self.wv.check(SID, self.tp))
        self.assertIn("save-check", problems)
        self.assertIn("different model", problems)
        self.assertIn("questioner", problems)
        self.assertIn("no helper call carrying the list's own token", problems)

    def test_a_token_from_another_turn_or_job_does_not_count(self):
        self.files()
        calls = self.calls_for(self.rec["jobs"])
        other = next(j for j in self.rec["jobs"] if j["id"] == "writer")["token"]
        for j, c in zip(self.rec["jobs"], calls):
            if j["id"] == "questioner":
                c["input"]["prompt"] = "Read something. [%s]" % other
        self.transcript(calls)
        self.assertTrue(any("questioner" in p for p in self.wv.check(SID, self.tp)))

    def test_added_context_is_fine_as_long_as_the_token_is_there(self):
        self.files()
        calls = self.calls_for(self.rec["jobs"])
        for c in calls:
            if c["input"].get("prompt"):
                c["input"]["prompt"] += " (Context: the person is a beginner.)"
        self.transcript(calls)
        self.assertEqual(self.wv.check(SID, self.tp), [])

    def test_a_crashed_check_warns_next_turn_and_never_reads_as_all_present(self):
        self.files()
        bad = dict(self.rec); bad.pop("t", None)          # a damaged turn.json makes the check raise inside
        with open(os.path.join(self.td, "turn.json"), "w", encoding="utf-8") as f:
            json.dump(bad, f)
        problems = self.wv.check(SID, self.tp)
        self.assertTrue(problems and "COULD NOT RUN" in problems[0])
        warn = open(os.path.join(self.run, "waves", "receipt-warn.txt"), encoding="utf-8").read()
        self.assertIn("RECEIPT CHECK COULD NOT RUN", warn)

    def test_an_unreadable_transcript_checks_the_files_only_and_says_so(self):
        self.files()
        self.assertEqual(self.wv.check(SID, os.path.join(self.home, "none.jsonl")), [])
        self.assertIn("no proof a helper ran", open(os.path.join(self.run, "waves", "receipts.log"), encoding="utf-8").read())

    def test_an_optional_chain_is_checked_once_any_job_of_it_ran(self):
        st = {"index": 6, "total": 6, "complete": False, "skill": "skill-builder"}
        self.wv.render(REPO, HOOKS, self.wd, self.run, st, SID, "t6", "answer", "a small correction", "")
        td = self.wv.turn_dir(self.run, "t6")
        rec = json.load(open(os.path.join(td, "turn.json"), encoding="utf-8"))
        chain = [o for o in rec["optional"] if o["chain"] == "recompile"]
        self.assertEqual([o["id"] for o in chain], ["backup", "compiler", "draft-check"])
        for j in rec["jobs"]:
            self.output("t6", j["receipt"], "APPLIED spec=0 packet=0 (skipped 0) rejected=0\n" if j["receipt"].endswith(".applied") else "ok\n")
        self.output("t6", "draft-spec.before-compile.md")          # only the backup ran: its output exists
        calls = self.calls_for(rec["jobs"]) + self.calls_for(chain[:1])
        with open(self.tp, "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "user", "message": {"role": "user", "content": "a small correction"}}) + "\n")
            f.write(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": calls}}) + "\n")
        problems = " | ".join(self.wv.check(SID, self.tp))
        self.assertIn("compiler", problems)
        self.assertIn("draft-check", problems)
        self.assertNotIn("backup", problems)

    def test_a_chain_nobody_started_is_not_demanded(self):
        self.files()
        self.transcript(self.calls_for(self.rec["jobs"]))
        self.assertEqual(self.wv.check(SID, self.tp), [])


class OutcomeNudgeTest(Base):
    """The outcome nudge: said from the second step-1 answer on (and at later steps) while `outcome` is unwritten."""

    FIRST = "FIRST, before any wave: write the `outcome` section now"

    def test_the_first_answer_has_no_nudge_only_not_run_yet(self):
        text = "\n".join(self.render(1, "answer", pid="a1"))
        self.assertNotIn(self.FIRST, text)
        self.assertIn("NOT RUN YET: `outcome`", text)

    def test_the_second_step_1_answer_without_outcome_gets_the_nudge_after_the_first_line_and_warning(self):
        self.render(1, "answer", pid="a1")
        os.makedirs(os.path.join(self.run, "waves"), exist_ok=True)
        with open(os.path.join(self.run, "waves", "receipt-warn.txt"), "w", encoding="utf-8") as f:
            f.write("1 back-room job problem(s) from last turn: x.")
        lines = self.render(1, "answer", pid="a2")
        i = next(n for n, l in enumerate(lines) if l.startswith("1. Your reply's FIRST line"))
        self.assertTrue(lines[i + 1].startswith("2. RECEIPT CHECK FAILED"))
        self.assertTrue(lines[i + 2].startswith(self.FIRST), lines[i + 2][:80])
        self.assertIn("cannot run until it exists.", lines[i + 2])
        self.assertTrue(any(self.FIRST in l for l in self.render(2, "start", pid="s2")))   # and at a later step start

    def test_no_nudge_once_outcome_is_written(self):
        self.render(1, "answer", pid="a1")
        self.section("outcome", "a receipt sorter")
        self.assertNotIn(self.FIRST, "\n".join(self.render(1, "answer", pid="a2")))
        self.assertNotIn(self.FIRST, "\n".join(self.render(3, "answer", pid="a3")))


class ReoffersAndOrderTest(Base):
    """Round 2c, coordinator fixes 1-4."""

    def test_the_outcome_helpers_are_re_offered_at_a_later_step_until_they_have_run_on_the_outcome(self):
        for step in (2, 3, 4, 5, 6):
            for moment in ("start", "answer"):
                text = "\n".join(self.render(step, moment, pid="n%d%s" % (step, moment)))
                if moment == "answer" or step in (4, 5, 6):
                    self.assertIn("NOT RUN YET: `outcome` is not written yet", text, "%s %s" % (step, moment))
        self.section("outcome", "a receipt sorter")
        for step in (2, 5):
            text = "\n".join(self.render(step, "answer", pid="o%d" % step))
            for j in ("harness-search — ", "research-mark — ", "size-sense — "):
                self.assertIn(j, text, "step %d" % step)
            self.assertLess(text.index("harness-search — "), text.index("harness-check — "))

    def test_once_they_have_run_on_this_outcome_a_later_step_does_not_run_them_again(self):
        self.section("outcome", "a receipt sorter")
        time.sleep(0.05)
        for n in ("harness-findings.md", "research-mark.md", "size-sense.md"):
            self.output("a1", n)
        time.sleep(0.05)
        self.output("a1", "harness-checked.md")
        text = "\n".join(self.render(2, "answer", pid="a2"))
        for j in ("harness-search — ", "research-mark — ", "size-sense — ", "harness-check — "):
            self.assertNotIn(j, text)
        self.assertNotIn("NOT RUN YET", text)

    def _tx(self, calls):
        tp = os.path.join(self.home, "o.jsonl")
        with open(tp, "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "user", "message": {"role": "user", "content": "answer"}}) + "\n")
            f.write(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": calls}}) + "\n")
        return tp

    def _turn(self, pid="o1"):
        self.render(1, "answer", pid=pid, prompt="sort by date")
        td = self.wv.turn_dir(self.run, pid)
        rec = json.load(open(os.path.join(td, "turn.json"), encoding="utf-8"))
        jobs = {j["id"]: j for j in rec["jobs"]}
        return td, rec, jobs

    def _call(self, j):
        return {"type": "tool_use", "name": "Agent", "input": {"model": j["model"], "prompt": j["prompt"]}}

    def _files(self, td, rec, applied="APPLIED spec=1 packet=1 (skipped 0) rejected=0\n"):
        for j in rec["jobs"]:
            if j["id"] == "questioner":
                continue
            self.output(os.path.basename(td), j["receipt"], applied if j["receipt"].endswith(".applied") else "ok\n")
        time.sleep(0.02)
        self.output(os.path.basename(td), "questions.md", "1. q\nQUESTIONS-END\n")

    def test_questions_after_the_writer_pass_and_the_order_check_is_silent(self):
        td, rec, jobs = self._turn()
        self._files(td, rec)
        calls = [self._call(jobs[i]) for i in ("writer", "save-check", "questioner")] + [self._call(j) for i, j in jobs.items() if i not in ("writer", "save-check", "questioner") and j["kind"] == "agent"]
        calls += [{"type": "tool_use", "name": "Bash", "input": {"command": jobs["citations"]["cmd"]}}]
        self.assertEqual(self.wv.check(SID, self._tx(calls)), [])

    def test_the_questioner_started_before_the_writer_is_caught(self):
        td, rec, jobs = self._turn()
        self._files(td, rec)
        order = ["questioner", "writer"] + [i for i in jobs if i not in ("questioner", "writer") and jobs[i]["kind"] == "agent"]
        calls = [self._call(jobs[i]) for i in order] + [{"type": "tool_use", "name": "Bash", "input": {"command": jobs["citations"]["cmd"]}}]
        problems = " | ".join(self.wv.check(SID, self._tx(calls)))
        self.assertIn("questioner was started before the writer", problems)
        self.assertIn("RECEIPT", "\n".join(self.render(1, "answer", pid="o2")))

    def test_questions_after_a_failed_or_missing_save_warn_loudly_next_turn(self):
        td, rec, jobs = self._turn()
        self._files(td, rec, applied="FAILED: 1 record(s) rejected, none could be applied\n")
        self.assertTrue(any("questions were made although the save did not apply" in p for p in self.wv.check(SID)))
        self.assertIn("questions were made although the save did not apply", "\n".join(self.render(1, "answer", pid="o2")))
        td, rec, jobs = self._turn("o3")
        self._files(td, rec)
        os.unlink(os.path.join(td, "writer.md.applied"))               # no receipt at all
        self.assertTrue(any("although the save did not apply" in p for p in self.wv.check(SID)))

    def test_questions_older_than_the_save_receipt_are_caught(self):
        td, rec, jobs = self._turn()
        self._files(td, rec)
        old = time.time() - 600
        os.utime(os.path.join(td, "questions.md"), (old, old))
        self.assertTrue(any("older than the save receipt" in p for p in self.wv.check(SID)))

    def test_a_files_only_check_is_shown_on_the_next_turn_not_only_in_the_log(self):
        td, rec, jobs = self._turn()
        self._files(td, rec)
        self.assertEqual(self.wv.check(SID, os.path.join(self.home, "gone.jsonl")), [])
        nxt = "\n".join(self.render(1, "answer", pid="o2"))
        self.assertIn("RECEIPT NOTE:", nxt)
        self.assertIn("files only", nxt)
        self.assertNotIn("RECEIPT CHECK FAILED", nxt)
        self.assertNotIn("RECEIPT NOTE", "\n".join(self.render(1, "answer", pid="o3")))     # said once

    def test_every_list_carries_the_slash_command_line_and_long_chains_the_esc_hint(self):
        self.section("outcome", "x")
        self.output("s5", "spec-update-checked.md")
        for step, moment in ((1, "answer"), (5, "answer"), (6, "start"), (4, "start")):
            text = "\n".join(self.render(step, moment, pid="l%d%s" % (step, moment)))
            self.assertIn("If the person types /next or /back, start no further waves; say in one line what is still running.", text)
            long = (step, moment) in ((5, "answer"), (6, "start"))
            self.assertEqual("press Esc, then type /next, to move on now" in text, long, "%s %s" % (step, moment))


class ReceiptTest(Base):
    """The Stop check: every required job's output file for THIS turn exists (present), is absent (missing), or is a file that
    belongs to an earlier moment (stale)."""

    def setUp(self):
        super().setUp()
        self.render(1, "answer", pid="t1", prompt="Sort my receipts by date")
        self.td = self.wv.turn_dir(self.run, "t1")
        self.rec = json.load(open(os.path.join(self.td, "turn.json"), encoding="utf-8"))

    def fill(self, skip=()):
        for j in self.rec["jobs"]:
            if j["id"] not in skip:
                self.output("t1", j["receipt"], "APPLIED spec=1 packet=1 (skipped 0) rejected=0\n" if j["receipt"].endswith(".applied") else "ok\n")

    def test_present_every_receipt_found(self):
        self.fill()
        self.assertEqual(self.wv.check(SID), [])
        self.assertIn("ALL RECEIPTS PRESENT", open(os.path.join(self.run, "waves", "receipts.log"), encoding="utf-8").read())

    def test_missing_a_job_leaves_a_warning_the_next_turn_carries(self):
        self.fill(skip=("save-check",))
        problems = self.wv.check(SID)
        self.assertEqual(len(problems), 1)
        self.assertIn("save-check", problems[0])
        warn = open(os.path.join(self.run, "waves", "receipt-warn.txt"), encoding="utf-8").read()
        self.assertIn("save-check", warn)
        self.assertIn("1 back-room job problem", warn)
        nxt = "\n".join(self.render(1, "answer", pid="t2"))
        self.assertIn("RECEIPT CHECK FAILED LAST TURN", nxt)
        self.assertIn("save-check", nxt)

    def test_missing_everything_names_every_job(self):
        problems = self.wv.check(SID)
        self.assertEqual(len(problems), len(self.rec["jobs"]))

    def test_a_stale_file_from_an_earlier_moment_never_passes(self):
        self.fill(skip=("writer",))
        # a writer receipt that is older than this turn (a file left from before the turn began)
        p = self.output("t1", "writer.md.applied", "APPLIED spec=1 packet=1 (skipped 0) rejected=0\n", age=3600)
        problems = self.wv.check(SID)
        self.assertEqual(len(problems), 1)
        self.assertIn("writer", problems[0])
        self.assertTrue(os.path.exists(p))

    def test_an_earlier_turns_files_are_not_this_turns(self):
        # turn t0 produced everything; turn t1 (this one) produced nothing: the files in t0's folder must not count
        for j in self.rec["jobs"]:
            self.output("t0", j["receipt"], "ok\n")
        self.assertEqual(len(self.wv.check(SID)), len(self.rec["jobs"]))

    def test_a_failed_save_is_a_problem_even_though_its_file_exists(self):
        self.fill(skip=("writer",))
        self.output("t1", "writer.md.applied", "FAILED: 2 record(s) rejected, none could be applied\n")
        problems = self.wv.check(SID)
        self.assertEqual(len(problems), 2)
        self.assertIn("did not apply", problems[0])
        self.assertIn("questions were made although the save did not apply", problems[1])

    def test_a_partly_rejected_save_is_said(self):
        self.fill(skip=("writer",))
        self.output("t1", "writer.md.applied", "APPLIED spec=0 packet=1 (skipped 0) rejected=2\n")
        problems = self.wv.check(SID)
        self.assertEqual(len(problems), 1)
        self.assertIn("2 record(s) were rejected", problems[0])

    def test_checked_once_per_turn(self):
        self.fill()
        self.wv.check(SID)
        self.wv.check(SID)
        self.assertEqual(open(os.path.join(self.run, "waves", "receipts.log"), encoding="utf-8").read().count("\n"), 1)

    def test_no_pointer_is_a_quiet_nothing(self):
        os.unlink(os.path.join(self.sb.od(), "spec-wave-%s.json" % SID))
        self.assertEqual(self.wv.check(SID), [])

    def test_the_stop_check_runs_the_receipt_check(self):
        self.fill(skip=("questioner",))
        with open(os.path.join(self.sb.od(), "spec-sess-%s.flag" % SID), "w", encoding="utf-8") as f:
            f.write("wd=%s\nat=1\n" % self.wd)
        self.sb.stop_check(HOOKS, SID, json.dumps({"last_assistant_message": "hi", "transcript_path": ""}))
        self.assertIn("questioner", open(os.path.join(self.run, "waves", "receipt-warn.txt"), encoding="utf-8").read())


class WriterInputTest(Base):
    def test_unsaved_earlier_turns_are_carried_and_settled_by_a_good_save(self):
        self.render(1, "answer", pid="t1", prompt="FIRST answer: weekly receipts")
        # t1's save never applied (no receipt). t2 must carry t1's words.
        self.render(1, "answer", pid="t2", prompt="SECOND answer: sort by date")
        t2 = self.wv.turn_dir(self.run, "t2")
        win = open(os.path.join(t2, "writer-input.md"), encoding="utf-8").read()
        self.assertIn("FIRST answer: weekly receipts", win)
        self.assertIn("SECOND answer: sort by date", win)
        ev = json.load(open(os.path.join(t2, "evidence.json"), encoding="utf-8"))
        self.assertEqual(ev["carried"], ["t1"])
        self.assertEqual(ev["person"][-1], "SECOND answer: sort by date")
        reply = os.path.join(t2, "writer.md")
        with open(reply, "w", encoding="utf-8") as f:
            f.write("SAID: SECOND answer: sort by date\n---\nEND-WRITE\n")
        res = self.sb.apply_and_mark(REPO, reply, self.wd, SID)
        self.assertTrue(res.startswith("APPLIED"), res)
        self.assertEqual(open(reply + ".applied", encoding="utf-8").read().strip(), res)
        self.assertIn("CARRIED into t2", open(os.path.join(self.wv.turn_dir(self.run, "t1"), "writer.md.applied"), encoding="utf-8").read())
        self.render(1, "answer", pid="t3", prompt="THIRD")
        self.assertNotIn("FIRST answer", open(os.path.join(self.wv.turn_dir(self.run, "t3"), "writer-input.md"), encoding="utf-8").read())

    def test_a_failed_apply_leaves_a_failed_receipt_and_the_words_stay_carried(self):
        self.render(1, "answer", pid="t1", prompt="an answer that fails")
        reply = os.path.join(self.wv.turn_dir(self.run, "t1"), "writer.md")
        with open(reply, "w", encoding="utf-8") as f:
            f.write("this is not a record")
        res = self.sb.apply_and_mark(REPO, reply, self.wd, SID)
        self.assertTrue(res.startswith("FAILED"), res)
        self.assertTrue(open(reply + ".applied", encoding="utf-8").read().startswith("FAILED"))
        self.render(1, "answer", pid="t2", prompt="next")
        self.assertIn("an answer that fails", open(os.path.join(self.wv.turn_dir(self.run, "t2"), "writer-input.md"), encoding="utf-8").read())

    def test_a_missing_records_file_is_failed_not_a_quiet_success(self):
        self.render(1, "answer", pid="t1", prompt="x")
        reply = os.path.join(self.wv.turn_dir(self.run, "t1"), "writer.md")
        self.assertTrue(self.sb.apply_and_mark(REPO, reply, self.wd, SID).startswith("FAILED"))

    def test_the_window_s_last_reply_is_part_of_the_evidence(self):
        tp = os.path.join(self.home, "t.jsonl")
        with open(tp, "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "user", "message": {"role": "user", "content": "earlier"}}) + "\n")
            f.write(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "Is it the Kestrel card?"}]}}) + "\n")
        self.render(1, "answer", pid="t1", prompt="yes", tp=tp)
        win = open(os.path.join(self.wv.turn_dir(self.run, "t1"), "writer-input.md"), encoding="utf-8").read()
        self.assertIn("SKILL: Is it the Kestrel card?", win)
        self.assertIn("PERSON: yes", win)


if __name__ == "__main__":
    unittest.main()
