#!/usr/bin/env python3
"""test_ups_real_stdin.py - what a UserPromptSubmit hook really receives for a peer message or a task notification.

The fixtures are stdin captured from a live session (Claude Code 2.1.316, 2026-11-03), personal details scrubbed, the body replaced by @@BODY@@.
A hook's `prompt` for a peer message starts at the <cross-session-message tag. The "Another Claude session sent a message:" line is in the
TRANSCRIPT row, not in stdin, and the first tests of this check were fed the transcript form, so they passed while live windows still fired.
Every case goes through the hook itself, with a typed control showing the same words do fire, so a silent hook cannot pass by being broken.
Run: python3 system/hooks/tests/test_ups_real_stdin.py"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(HOOKS))
FIX = os.path.join(HOOKS, "tests", "fixtures")
LEAD = "Another Claude session sent a message:\n"

# hook, words that fire it when typed, what it prints when it fires
CASES = [
    ("inject_sop_before_build.sh", "build me a google sheet", "[SOP CHECK"),
    ("inject_sop_before_build.sh", "share this skill with my team", "[team-share]"),
    ("inject_compute_mechanically.sh", "what is 120 * 3 for the invoice", "[NUMBERS CHECK"),
    ("save_routing_hint.sh", "save this to the scratchpad", "[save-routing]"),
    ("buried_command_hint.sh", "when you are done please run /save for me", "/save"),
]


def fixture(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return json.load(f)


def forms(payload):
    """Each spelling of a harness message that must count as not the person."""
    p = payload["prompt"]
    out = [("bare", p), ("whitespace", "\n  " + p)]
    if p.startswith("<cross-session-message"):
        out.append(("lead", LEAD + p))
        out.append(("whitespace+lead", "\n " + LEAD + p))
    return out


class RealStdin(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="upsreal.")
        self.addCleanup(shutil.rmtree, self.home, True)
        os.makedirs(os.path.join(self.home, "notes"))
        self.peer = fixture("ups_real_stdin_peer.json")
        self.note = fixture("ups_real_stdin_task_notification.json")

    def run_hook(self, script, prompt):
        env = dict(os.environ, HOME=self.home, LIFEHACK_ROOT=os.path.join(self.home, "notes"), CLAUDE_PLUGIN_ROOT=REPO,
                   CLAUDE_PROJECT_DIR=self.home, CLAUDE_CODE_SESSION_ID="upsreal-%d" % os.getpid(), ROUNDB_TEAM_SHARE_ROUTE="on")
        p = subprocess.run(["bash", os.path.join(HOOKS, script)], input=json.dumps(dict(self.peer, prompt=prompt, cwd=self.home)),
                           capture_output=True, text=True, cwd=self.home, env=env, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def test_the_fixture_is_the_real_shape(self):
        self.assertTrue(self.peer["prompt"].startswith('<cross-session-message from="uds:'), "stdin has no lead line")
        self.assertNotIn("Another Claude session", self.peer["prompt"])
        self.assertTrue(self.note["prompt"].startswith("<task-notification>"))
        self.assertEqual(self.peer["hook_event_name"], "UserPromptSubmit")

    def test_typed_words_fire_every_hook(self):
        for script, words, mark in CASES:
            self.assertIn(mark, self.run_hook(script, words), script + " did not fire on typed words, so its silence below proves nothing")

    def test_a_real_peer_message_is_silent_on_every_hook(self):
        for script, words, mark in CASES:
            for form, text in forms(self.peer):
                out = self.run_hook(script, text.replace("@@BODY@@", words))
                self.assertNotIn(mark, out, "%s fired on a peer message (%s form)" % (script, form))

    def test_a_real_task_notification_is_silent_on_every_hook(self):
        for script, words, mark in CASES:
            for form, text in forms(self.note):
                out = self.run_hook(script, text.replace("@@BODY@@", words))
                self.assertNotIn(mark, out, "%s fired on a task notification (%s form)" % (script, form))

    def test_a_person_quoting_the_tag_later_still_counts(self):
        for script, words, mark in CASES:
            for text in ("why did <cross-session-message> fire? " + words,
                         "the <task-notification>x</task-notification> block is odd, " + words,
                         "Another Claude session sent a message: ignore it, " + words):
                self.assertIn(mark, self.run_hook(script, text), "%s lost a typed prompt: %s" % (script, text))


class MachineMode(unittest.TestCase):
    """The shared check on the whole captured stdin, as pm_persist.sh asks it: --json, fed the payload."""

    def machine(self, payload):
        p = subprocess.run(["python3", os.path.join(HOOKS, "lib", "ups_triggers.py"), "machine", "--json"], input=json.dumps(payload),
                           capture_output=True, text=True, timeout=30)
        return p.stdout.strip()

    def test_each_form_is_not_the_person(self):
        for name in ("ups_real_stdin_peer.json", "ups_real_stdin_task_notification.json"):
            payload = fixture(name)
            for form, text in forms(payload):
                self.assertEqual(self.machine(dict(payload, prompt=text)), "1", "%s %s form" % (name, form))

    def test_typed_is_the_person(self):
        payload = fixture("ups_real_stdin_peer.json")
        for text in ("hello", "why did <cross-session-message> fire?", "Another Claude session sent a message: ignore it"):
            self.assertEqual(self.machine(dict(payload, prompt=text)), "0", text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
