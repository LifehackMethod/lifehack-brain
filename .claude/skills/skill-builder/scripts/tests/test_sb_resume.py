#!/usr/bin/env python3
"""Tests for ITEM 1 (resume like /ingest) and ITEM 5 (a mode command counts only at the start of the person's prompt).
Every folder is a temporary one: a temp HOME and a temp notes folder (LIFEHACK_ROOT); the real notes folder is never read.
SB_START_LIB may point at a directory holding a candidate sb_start.py (to test a copy before it goes live)."""

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(os.path.dirname(TESTS_DIR))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(SKILL)))
HOOKS = os.path.join(REPO, "system", "hooks")
LIB = os.path.join(HOOKS, "lib")
PARTS = os.path.join(REPO, "system", "parts")
RUNNER = os.path.join(PARTS, "stage_runner.py")
REAL_CARD = os.path.join(SKILL, "card.json")
for p in (PARTS, LIB, os.environ.get("SB_START_LIB") or LIB):   # last inserted wins the import
    if p not in sys.path:
        sys.path.insert(0, p)
import sb_start  # noqa: E402
import stage_runner  # noqa: E402

UPDATED_TEXT = "the skill was updated since you started"
DAMAGED_TEXT = "its record is damaged, so it cannot be picked up"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sbresume-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        self.brain = os.path.join(self.tmp, "notes")
        os.makedirs(self.home)
        os.makedirs(os.path.join(self.brain, "drafts", "builds"))
        self.saved = {k: os.environ.get(k) for k in ("HOME", "LIFEHACK_ROOT", "CLAUDE_CODE_SESSION_ID")}
        os.environ["HOME"] = self.home
        os.environ["LIFEHACK_ROOT"] = self.brain
        os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
        self.addCleanup(self._restore)
        self.cwd = os.path.join(self.tmp, "elsewhere")   # a window whose cwd has no run
        os.makedirs(self.cwd)
        self.n = 0

    def _restore(self):
        for k, v in self.saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def start_run(self, wd, card=REAL_CARD, sid="oldsess"):
        os.makedirs(wd, exist_ok=True)
        env = dict(os.environ, CLAUDE_CODE_SESSION_ID=sid)
        p = subprocess.run([sys.executable, RUNNER, "start", "--card", card, "--workdir", wd],
                           capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return wd

    def design(self, name, age=0):
        wd = self.start_run(os.path.join(self.brain, "drafts", "builds", name))
        if age:   # make the run look older: the record's mtime decides "most recent first"
            for f in glob.glob(os.path.join(wd, "runs", "*", "record.jsonl")):
                t = os.path.getmtime(f) - age
                os.utime(f, (t, t))
        return wd

    def runs(self, wd):
        return sorted(os.listdir(os.path.join(wd, "runs"))) if os.path.isdir(os.path.join(wd, "runs")) else []

    def holdings(self):
        return sorted(glob.glob(os.path.join(self.brain, "drafts", "builds", "_holding-*")))

    def pid(self):
        self.n += 1
        return "p%d" % self.n

    def bare(self, sid="newsess"):
        return sb_start.begin(stage_runner, HOOKS, self.cwd, sid, self.pid(), "")

    def reply(self, text, sid="newsess"):
        return sb_start.offer_reply(stage_runner, HOOKS, self.cwd, sid, self.pid(), text)

    def pointer(self, sid="newsess"):
        return sb_start._get_pointer(HOOKS, sid)

    def damaged_design(self, name):
        """A run whose card was edited after it started (the runner reports DAMAGED). A private copy of the card is used."""
        cdir = os.path.join(self.tmp, "cardcopy-" + name, "skill-builder")
        os.makedirs(cdir)
        shutil.copy(REAL_CARD, os.path.join(cdir, "card.json"))
        shutil.copytree(os.path.join(SKILL, "prompts"), os.path.join(cdir, "prompts"))
        wd = self.start_run(os.path.join(self.brain, "drafts", "builds", name), card=os.path.join(cdir, "card.json"))
        with open(os.path.join(cdir, "prompts", "step-1-what-you-want.md"), "a", encoding="utf-8") as f:
            f.write("\nan edit made after the run started\n")
        p = subprocess.run([sys.executable, RUNNER, "status", "--json", "--workdir", wd], capture_output=True, text=True)
        self.assertEqual(p.returncode, stage_runner.CARDCHANGED, p.stdout)
        return wd

    def corrupt_design(self, name):
        """A run whose record was hand-edited (truly DAMAGED)."""
        wd = self.design(name)
        rec = glob.glob(os.path.join(wd, "runs", "*", "record.jsonl"))[0]
        with open(rec, "a", encoding="utf-8") as f:
            f.write("not json\n")
        return wd


class NoUnfinished(Base):
    def test_zero_runs_starts_a_holding_run_as_before(self):
        out = "\n".join(self.bare())
        self.assertIn("RUN: step 1 of", out)
        self.assertEqual(len(self.holdings()), 1)
        self.assertFalse(os.path.exists(sb_start._offer_path("newsess")))

    def test_finished_runs_are_not_offered(self):
        wd = self.design("done-one")
        os.rename(os.path.join(wd, ".stage-runner.json"), os.path.join(wd, ".stage-runner.json.done-x"))
        out = "\n".join(self.bare())
        self.assertNotIn("RESUME OFFER", out)
        self.assertEqual(len(self.holdings()), 1)


class OneUnfinished(Base):
    def test_offer_is_one_line_and_nothing_moves(self):
        wd = self.design("component-builder")
        before = self.runs(wd)
        out = self.bare()
        self.assertEqual(len(out), 1)
        self.assertIn("[[You left off at step 1 of component-builder. Pick up? (yes / start new)]]", out[0])
        self.assertEqual(self.runs(wd), before)
        self.assertEqual(self.holdings(), [])          # no holding run, no new run
        self.assertEqual(self.pointer(), "")           # the pointer is not touched until yes

    def test_packet_folder_is_found_and_named_without_the_prefix(self):
        wd = self.start_run(os.path.join(self.brain, "state", "projects", "build-x", "packet-component-builder"))
        out = "\n".join(self.bare())
        self.assertIn("step 1 of component-builder.", out)
        self.assertEqual(self.holdings(), [])
        self.assertTrue(os.path.isdir(wd))

    def test_yes_resumes_without_creating_a_run_and_repoints(self):
        wd = self.design("component-builder")
        self.bare()
        before = self.runs(wd)
        out = "\n".join(self.reply("Yes."))
        self.assertIn("RUN: step 1 of", out)
        self.assertIn(wd, out)
        self.assertEqual(self.runs(wd), before)        # the same run, no new one
        self.assertEqual(self.holdings(), [])
        self.assertEqual(os.path.realpath(self.pointer()), os.path.realpath(wd))
        self.assertFalse(os.path.exists(sb_start._offer_path("newsess")))
        self.assertIn('"event": "reissue"', open(os.path.join(wd, "runs", before[0], "record.jsonl"), encoding="utf-8").read())

    def test_pick_up_words(self):
        for word in ("pick up", "y", "yes please"):
            wd = self.design("d-" + word.replace(" ", "-"))
            self.bare(sid="s-" + word.replace(" ", "-"))
            out = "\n".join(self.reply(word, sid="s-" + word.replace(" ", "-")))
            self.assertIn("RUN: step 1 of", out, word)
            shutil.rmtree(wd)

    def test_start_new_starts_one_and_leaves_the_old_run_alone(self):
        wd = self.design("component-builder")
        self.bare()
        before = self.runs(wd)
        out = "\n".join(self.reply("start new"))
        self.assertIn("RUN: step 1 of", out)
        self.assertEqual(len(self.holdings()), 1)
        self.assertEqual(self.runs(wd), before)        # the unfinished run was not touched
        self.assertEqual(len(self.runs(self.holdings()[0])), 1)

    def test_another_answer_drops_the_offer_and_starts_nothing(self):
        wd = self.design("component-builder")
        self.bare()
        self.assertIsNone(self.reply("what does that mean?"))
        self.assertEqual(self.holdings(), [])
        self.assertIsNone(self.reply("yes"))            # the offer is gone: a later yes is just a word
        self.assertEqual(self.pointer(), "")
        self.assertEqual(len(self.runs(wd)), 1)

    def test_no_offer_means_the_prompt_goes_on(self):
        self.assertIsNone(self.reply("yes"))

    def test_twin_copy_of_the_hook_handles_one_prompt_once(self):
        wd = self.design("component-builder")
        self.bare()
        pid = "same-prompt"
        first = sb_start.offer_reply(stage_runner, HOOKS, self.cwd, "newsess", pid, "yes")
        twin = sb_start.offer_reply(stage_runner, HOOKS, self.cwd, "newsess", pid, "yes")
        self.assertIn("RUN: step 1 of", "\n".join(first))
        self.assertEqual(twin, [])
        self.assertEqual(len(self.runs(wd)), 1)

    def test_a_run_found_by_cwd_still_resumes_without_a_question(self):
        wd = self.design("component-builder")
        out = "\n".join(sb_start.begin(stage_runner, HOOKS, wd, "newsess", self.pid(), ""))
        self.assertNotIn("RESUME OFFER", out)
        self.assertIn("RUN: step 1 of", out)

    def test_a_named_skill_is_not_asked_about(self):
        self.design("component-builder")
        out = "\n".join(sb_start.begin(stage_runner, HOOKS, self.cwd, "newsess", self.pid(), "monthly-budget"))
        self.assertNotIn("RESUME OFFER", out)
        self.assertTrue(os.path.isdir(os.path.join(self.brain, "drafts", "builds", "monthly-budget", "runs")))


class SeveralUnfinished(Base):
    def setUp(self):
        super().setUp()
        self.old = self.design("older-design", age=5000)
        self.new = self.design("newer-design", age=10)

    def test_listed_most_recent_first(self):
        out = "\n".join(self.bare())
        self.assertIn("1. step 1 of newer-design", out)
        self.assertIn("2. step 1 of older-design", out)
        self.assertLess(out.index("newer-design"), out.index("older-design"))
        self.assertEqual(self.holdings(), [])

    def test_the_number_picks_that_run(self):
        self.bare()
        out = "\n".join(self.reply("2"))
        self.assertIn(self.old, out)
        self.assertEqual(os.path.realpath(self.pointer()), os.path.realpath(self.old))
        self.assertEqual(len(self.runs(self.old)), 1)
        self.assertEqual(self.holdings(), [])

    def test_a_bare_yes_is_not_a_pick_and_the_offer_stays(self):
        self.bare()
        out = "\n".join(self.reply("yes"))
        self.assertIn("type the number", out)
        self.assertEqual(self.pointer(), "")
        self.assertTrue(os.path.exists(sb_start._offer_path("newsess")))
        self.assertIn(self.new, "\n".join(self.reply("1")))

    def test_start_new_with_several(self):
        self.bare()
        out = "\n".join(self.reply("start new"))
        self.assertIn("RUN: step 1 of", out)
        self.assertEqual(len(self.holdings()), 1)
        self.assertEqual(len(self.runs(self.old)) + len(self.runs(self.new)), 2)


class UpdatedCardRun(Base):
    def test_updated_run_is_listed_marked_and_yes_refreshes_and_resumes_at_the_same_step(self):
        good = self.design("good-design", age=5000)
        bad = self.damaged_design("changed-design")
        out = "\n".join(self.bare())
        self.assertIn("changed-design", out)
        self.assertIn(UPDATED_TEXT + "; carry on with the new version from step 1", out)
        self.assertIn("good-design", out)
        rec = os.path.join(bad, "runs", self.runs(bad)[0], "record.jsonl")
        n = len(open(rec, encoding="utf-8").read().splitlines())
        out = "\n".join(self.reply("1"))                 # the updated one is the most recent
        self.assertIn("RUN: step 1 of", out)
        self.assertIn(bad, out)
        lines = [json.loads(l) for l in open(rec, encoding="utf-8")]
        self.assertEqual([l["event"] for l in lines][n:], ["refresh"])   # one refresh line, nothing restarted
        self.assertEqual(len(self.runs(bad)), 1)
        self.assertEqual(self.holdings(), [])
        self.assertEqual(os.path.realpath(self.pointer()), os.path.realpath(bad))
        p = subprocess.run([sys.executable, RUNNER, "verify", "--workdir", bad], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertEqual(len(self.runs(good)), 1)

    def test_a_single_updated_run_offers_yes_and_start_new(self):
        self.damaged_design("changed-design")
        out = "\n".join(self.bare())
        self.assertIn("You left off at step 1 of changed-design: " + UPDATED_TEXT + "; carry on with the new version from step 1? (yes / start new)", out)

    def test_nothing_changes_until_the_person_answers(self):
        bad = self.damaged_design("changed-design")
        rec = os.path.join(bad, "runs", self.runs(bad)[0], "record.jsonl")
        before = open(rec, encoding="utf-8").read()
        self.bare()
        self.assertEqual(open(rec, encoding="utf-8").read(), before)
        self.assertEqual(self.pointer(), "")

    def test_open_step_removed_from_the_new_card_refuses_and_writes_nothing(self):
        bad = self.damaged_design("changed-design")
        cj = os.path.join(self.tmp, "cardcopy-changed-design", "skill-builder", "card.json")
        c = json.load(open(cj, encoding="utf-8"))
        del c["stages"][0]
        json.dump(c, open(cj, "w", encoding="utf-8"))
        rec = os.path.join(bad, "runs", self.runs(bad)[0], "record.jsonl")
        before = open(rec, encoding="utf-8").read()
        self.bare()
        out = "\n".join(self.reply("yes"))
        self.assertIn("NO RUN", out)
        self.assertIn("no longer in the updated card", out)
        self.assertEqual(open(rec, encoding="utf-8").read(), before)


class DamagedRun(Base):
    def test_a_truly_damaged_run_is_listed_marked_and_never_resumed(self):
        good = self.design("good-design", age=5000)
        bad = self.corrupt_design("broken-design")
        out = "\n".join(self.bare())
        self.assertIn("broken-design", out)
        self.assertIn(DAMAGED_TEXT, out)
        rec = os.path.join(bad, "runs", self.runs(bad)[0], "record.jsonl")
        before = open(rec, encoding="utf-8").read()
        reply = "\n".join(self.reply("1"))
        self.assertIn("that run cannot be picked up", reply)
        self.assertEqual(open(rec, encoding="utf-8").read(), before)
        self.assertEqual(self.pointer(), "")
        self.assertEqual(self.holdings(), [])
        self.assertIn(good, "\n".join(self.reply("2")))


class HoldingFolders(Base):
    def test_holding_ignored_when_a_real_run_exists(self):
        self.start_run(os.path.join(self.brain, "drafts", "builds", "_holding-abcd1234"))
        self.design("component-builder")
        out = "\n".join(self.bare())
        self.assertIn("step 1 of component-builder. Pick up?", out)
        self.assertNotIn("_holding", out)

    def test_holding_offered_when_nothing_else_exists(self):
        self.start_run(os.path.join(self.brain, "drafts", "builds", "_holding-abcd1234"))
        out = "\n".join(self.bare())
        self.assertIn("RESUME OFFER", out)
        self.assertIn("_holding-abcd1234", out)


class ModeCommandOnlyAtStart(unittest.TestCase):
    def test_leading_commands_are_modes(self):
        for p in ("/skill-builder observe audit", "  /skill-builder note this moved on too early", "\n/skill-builder wrap",
                  "/lifehack-brain:skill-builder observe skill-builder", "/skill-builder note: a thing", "/skill-builder observe off"):
            self.assertEqual(sb_start.detect(p), ("other", ""), p)

    def test_a_pasted_or_mid_message_mention_is_nothing(self):
        for p in ("Hey, I am launching it /skill-builder observe skill-builder",
                  "here is the log:\n/skill-builder note blah\nand more",
                  "please try /skill-builder wrap now",
                  "a /skill-builder observe audit then /skill-builder wrap"):
            self.assertEqual(sb_start.detect(p), (None, ""), p)

    def test_other_commands_unchanged(self):
        self.assertEqual(sb_start.detect("/skill-builder"), ("normal", ""))
        self.assertEqual(sb_start.detect("/skill-builder monthly-budget"), ("normal", "monthly-budget"))
        self.assertEqual(sb_start.detect("/skill-builder catch-up 3 /x/y"), ("catchup", "3 /x/y"))
        self.assertEqual(sb_start.detect("paste: /skill-builder note x\nthen /skill-builder"), ("normal", ""))
        self.assertEqual(sb_start.detect("/skill-builder noted-things"), ("normal", "noted-things"))   # a kebab word is a skill name, not a mode
        self.assertEqual(sb_start.detect("no command here"), (None, ""))


class HookEndToEnd(Base):
    """The real mover (run_step_hook.sh) through its registered entry point: bare /skill-builder, then yes."""
    def fire(self, prompt, sid="newsess"):
        self.n += 1
        payload = json.dumps({"session_id": sid, "prompt_id": "pp%d" % self.n, "cwd": self.cwd, "prompt": prompt})
        env = dict(os.environ, HOME=self.home, LIFEHACK_ROOT=self.brain)
        env.pop("CLAUDE_CODE_SESSION_ID", None)
        return subprocess.run(["sh", os.path.join(HOOKS, "run_step_hook.sh")], input=payload, capture_output=True,
                              text=True, env=env, timeout=120).stdout

    def test_offer_then_yes(self):
        wd = self.design("component-builder")
        out = self.fire("/skill-builder")
        self.assertIn("You left off at step 1 of component-builder. Pick up? (yes / start new)", out)
        self.assertEqual(self.holdings(), [])
        out = self.fire("yes")
        self.assertIn("RUN: step 1 of", out)
        self.assertNotIn("WAVE", out.split("RUN:")[0])
        self.assertEqual(len(self.runs(wd)), 1)
        self.assertEqual(self.holdings(), [])
        self.assertEqual(os.path.realpath(self.pointer()), os.path.realpath(wd))

    def test_yes_with_no_offer_is_silent(self):
        self.design("component-builder")
        self.assertEqual(self.fire("yes").strip(), "")


if __name__ == "__main__":
    unittest.main()
