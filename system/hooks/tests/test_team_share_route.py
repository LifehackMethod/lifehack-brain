#!/usr/bin/env python3
"""test_team_share_route.py - exam D-B08/D-B09 (plan fix 23(c)): a session asked to share a skill with a team never reached
shared/tools/team_skills.py. Switch team_share_route: inject_sop_before_build.sh prints the one route when the prompt asks for it.
Everything runs through the REGISTERED hook entry points. A FAKE HOME and FAKE Drive mount under a temp dir only: the real
~/Library/CloudStorage is never touched and no model is called.
  1. the trigger fires on the exam's words; harmless messages stay silent; OFF = silent
  2. the printed commands, run exactly as printed, put the skill in the fake Drive and leave the person's folder alone
  3. every PreToolUse hook registered for Bash passes the named route in every shell shape (with a control that proves the check bites)
  4. the route does not set off the end-of-turn "long command, offer to keep it" note
Run: python3 system/hooks/tests/test_team_share_route.py"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HOOKS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(HOOKS))
INJECT = os.path.join(HOOKS, "inject_sop_before_build.sh")
TOOL = os.path.join(REPO, "shared", "tools", "team_skills.py")
sys.path.insert(0, os.path.join(HOOKS, "lib"))
import inline_keep  # noqa: E402

D_B08 = "my team at the studio all need this invoice-checker skill I just built. share it with them"
D_B09 = "I run a small agency and want our company-specific intake skill available to my whole staff"
FIRES = [
    D_B08, D_B09,
    "share this skill with my team",
    "Can you send the invoice-checker skill to my coworkers?",
    "give my staff the intake skill",
    "how do I get this skill to my colleagues",
    "make the intake skill available to everyone at the company",
    "I built this skill, share it with the team please",
    "how can my team use this skill?",
    "give my team access to our onboarding skill",
    "share my skills with the team",
]
SILENT = [
    "build a new skill for checking invoices",
    "what skills do I have?",
    "share this doc with my team",
    "share the invoice spreadsheet with staff",
    "my team needs better communication skills",
    "share my leadership skills on the team page",
    "give my team the skills they need to succeed",
    "give my staff a skill to handle refunds",
    "the team skills matrix spreadsheet needs updating",
    "share the skill matrix with my team",
    "share the skill-building SOP with my team",
    "write a skill that shares files with my team",
    "write a skill to share invoices with my team",
    "what skill should I build to share docs with the team",
    "add a sharing skill for my team",
    "don't share this skill with my team",
    "use my team's skills",
    "keep it simple",
    "save this",
    "<task-notification>share this skill with my team</task-notification>",
    "`share this skill with my team` is the phrase in the docs, check the docs build",
    "here is a long paste. " * 80 + "share this skill with my team",
]
# what the model types: the tool may sit anywhere, the Drive path has a space, ~ and $HOME both appear
SIM_TOOL = "$HOME/.claude/plugins/cache/lifehack-brain/lifehack-brain/2.0/shared/tools/team_skills.py"
SIM_FOLDER = "$HOME/Library/CloudStorage/GoogleDrive-test/My Drive/Team skills"


def shapes(tool, folder):
    t = '"%s"' % tool
    f = '"%s"' % folder
    disc = "python3 %s discover" % t
    setc = "python3 %s set team %s --create" % (t, f)
    share = "python3 %s share invoice-checker --yes --no-link" % t
    link = "python3 %s share invoice-checker --yes" % t
    return [
        disc, setc, share, link,
        "python3 %s share invoice-checker" % t,                                             # dry run
        "python3 %s set team --create -- %s" % (t, f),                                      # `--`
        "python3 %s share --yes --no-link -- invoice-checker" % t,                          # `--`
        "%s && %s && %s" % (disc, setc, share),                                             # chained
        "%s; %s; %s" % (disc, setc, share),                                                 # chained
        "cd ~/.claude/skills && %s" % share,                                                # chained, from the skills folder
        "if [ -d %s ]; then %s; else %s; fi" % (f, share, setc),                            # if/else
        "if %s; then %s; else echo none; fi" % (disc, setc),                                # if/else
        "%s 2>&1 | tail -5" % share,                                                        # piped
        "for s in invoice-checker; do python3 %s share \"$s\" --yes --no-link; done" % t,   # loop
        "T=%s; python3 \"$T\" share invoice-checker --yes --no-link" % t,                   # variable
        "ls -la ~/Library/CloudStorage/ && %s" % disc,                                      # the look a person would take first
    ]


class Base(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="teamroute.")
        self.addCleanup(shutil.rmtree, self.home, True)
        self.drive = os.path.join(self.home, "Library", "CloudStorage", "GoogleDrive-test", "My Drive")
        os.makedirs(self.drive)
        os.makedirs(os.path.join(self.home, "notes"))
        os.makedirs(os.path.join(self.home, ".config", "lifehack"))
        self.skill = os.path.join(self.home, ".claude", "skills", "invoice-checker")
        os.makedirs(os.path.join(self.skill, "scripts"))
        with open(os.path.join(self.skill, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: invoice-checker\ndescription: Check an invoice. Use on \"check this invoice\".\n---\n\n# Invoice checker\n")
        with open(os.path.join(self.skill, "scripts", "total.py"), "w", encoding="utf-8") as f:
            f.write("print(1)\n")

    def env(self, **kw):
        e = dict(os.environ, HOME=self.home, LIFEHACK_ROOT=os.path.join(self.home, "notes"), CLAUDE_PLUGIN_ROOT=REPO,
                 CLAUDE_CODE_SESSION_ID="teamroute-%d" % os.getpid())
        e.pop("ROUNDB_TEAM_SHARE_ROUTE", None)
        e.update(kw)
        return e

    def hook(self, prompt, switch="on"):
        p = subprocess.run(["bash", INJECT], input=json.dumps({"prompt": prompt, "cwd": self.home}), capture_output=True, text=True,
                           cwd=self.home, env=self.env(ROUNDB_TEAM_SHARE_ROUTE=switch), timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def run_cmd(self, cmd):
        return subprocess.run(["bash"], input=cmd, capture_output=True, text=True, cwd=self.home, env=self.env(), timeout=30)

    def printed_commands(self, text):
        return re.findall(r'python3 "[^"]+" [^\n]*', text)


class Trigger(Base):
    def test_fires_on_the_exam_words_and_plain_share_requests(self):
        for s in FIRES:
            self.assertIn("[team-share]", self.hook(s), "should fire on: " + s)

    def test_silent_on_harmless_messages(self):
        for s in SILENT:
            self.assertNotIn("[team-share]", self.hook(s), "false alarm on: " + s[:80])

    def test_switch_off_is_exactly_old_behaviour(self):
        self.assertEqual(self.hook(D_B08, "off"), "")
        self.assertEqual(self.hook(D_B09, "off"), "")

    def test_the_build_injector_still_works_and_stays_separate(self):
        out = self.hook("build a new skill for checking invoices")
        self.assertIn("[SOP CHECK", out)
        self.assertNotIn("[team-share]", out)

    def test_the_sign_names_one_route(self):
        out = self.hook(D_B08)
        self.assertIn(TOOL, out)
        self.assertRegex(out, r"(?i)not a zip")
        self.assertNotRegex(out, r"(?i)\bretry\b|try again")
        self.assertLess(len(out.replace(TOOL, "T")), 800, "lean injection (hook SOP section 3): the words, not counting the tool's path")

    def test_switch_line_is_in_the_conf_with_its_comment(self):
        conf = open(os.path.join(HOOKS, "roundB.conf"), encoding="utf-8").read().split("\n")
        i = [n for n, l in enumerate(conf) if l.startswith("team_share_route=")]
        self.assertEqual(len(i), 1)
        self.assertTrue(conf[i[0] - 1].startswith("# 2026-11-"), "a dated comment line above the switch, like its neighbours")


class Route(Base):
    def fill(self, cmd):
        cmd = re.sub(r'"<[^>]*folder[^>]*>"', '"%s"' % os.path.join(self.drive, "Team skills"), cmd)
        return cmd.replace("<skill-name>", "invoice-checker")

    def test_first_time_the_printed_route_runs_as_printed(self):
        cmds = self.printed_commands(self.hook(D_B08))
        self.assertEqual([re.search(r'" (\w+)', c).group(1) for c in cmds], ["discover", "set", "share", "share"])
        for c in cmds[:3]:
            p = self.run_cmd(self.fill(c))
            self.assertEqual(p.returncode, 0, c + "\n" + p.stdout + p.stderr)
        copy = os.path.join(self.drive, "Team skills", "skills", "invoice-checker")
        self.assertTrue(os.path.isfile(os.path.join(copy, "SKILL.md")), "the real folder is in Drive")
        self.assertTrue(os.path.isfile(os.path.join(copy, "scripts", "total.py")))
        self.assertTrue(os.path.isdir(self.skill) and not os.path.islink(self.skill), "the link is offered, never forced")
        p = self.run_cmd(self.fill(cmds[3]))    # the person says yes to the offer
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue(os.path.islink(self.skill), "the offered link works")
        self.assertEqual(os.path.realpath(self.skill), os.path.realpath(copy))

    def test_folder_already_set_goes_straight_to_share(self):
        team = os.path.join(self.drive, "Our team")
        self.assertEqual(self.run_cmd('python3 "%s" set team "%s" --create' % (TOOL, team)).returncode, 0)
        out = self.hook(D_B08)
        cmds = self.printed_commands(out)
        self.assertEqual([re.search(r'" (\w+)', c).group(1) for c in cmds], ["share", "share"], out)
        self.assertNotIn("set team", out, "must never repoint a folder the person already chose")
        self.assertIn(team, out)

    def test_a_saved_solo_answer_still_gets_the_first_time_route(self):
        self.assertEqual(self.run_cmd('python3 "%s" set solo' % TOOL).returncode, 0)
        self.assertIn(" discover", self.hook(D_B08))

    def test_every_shell_shape_really_runs(self):
        for n, cmd in enumerate(shapes(TOOL, os.path.join(self.drive, "Team skills"))):
            if " --no-link" not in cmd:     # the link forms are proved in the first test; here the local folder must stay
                continue
            p = self.run_cmd(cmd)
            self.assertNotIn("usage:", p.stderr, cmd)
            self.assertNotIn("Traceback", p.stderr, cmd)

    def test_the_route_does_not_set_off_the_keep_it_note(self):
        for c in self.printed_commands(self.hook(D_B08)):
            self.assertFalse(inline_keep.is_reusable(self.fill(c)), c)


class Chain(Base):
    """Every hook registered for Bash in hooks/hooks.json, run through its registered command."""

    def bash_hooks(self):
        reg = json.load(open(os.path.join(REPO, "hooks", "hooks.json"), encoding="utf-8"))["hooks"]["PreToolUse"]
        out = []
        for row in reg:
            if re.fullmatch(row.get("matcher") or ".*", "Bash"):
                out += [h["command"] for h in row["hooks"]]
        self.assertGreaterEqual(len(out), 20, "the chain was not found")
        return out

    def verdicts(self, cmd, hooks):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": self.home, "session_id": "teamroute",
                              "hook_event_name": "PreToolUse"})
        said = []
        for h in hooks:
            p = subprocess.run(["bash"], input='%s <<\'__P__\'\n%s\n__P__\n' % (h, payload), capture_output=True, text=True,
                               cwd=self.home, env=self.env(), timeout=60)
            stopped = p.returncode != 0 or re.search(r'"(?:permissionDecision|decision)"\s*:\s*"(?:deny|ask|block)"', p.stdout)
            if stopped:
                said.append("%s rc=%d %s %s" % (h.split("/")[-1], p.returncode, p.stdout[:300], p.stderr[:300]))
        return said

    def test_control_the_chain_really_stops_things(self):
        said = self.verdicts("gcloud projects delete my-real-project", self.bash_hooks())
        self.assertTrue(said, "the control was not stopped: this check proves nothing")

    def test_no_hook_stops_the_named_route_in_any_shape(self):
        hooks = self.bash_hooks()
        problems = []
        cases = shapes(SIM_TOOL, SIM_FOLDER) + shapes(TOOL, os.path.join(self.drive, "Team skills"))
        for cmd in cases:
            said = self.verdicts(cmd, hooks)
            if said:
                problems.append(cmd + "\n   " + "\n   ".join(said))
        self.assertEqual(problems, [], "\n".join(problems))

    def test_the_printed_commands_pass(self):
        hooks = self.bash_hooks()
        for c in self.printed_commands(self.hook(D_B08)):
            c = c.replace("<skill-name>", "invoice-checker")
            c = re.sub(r'"<[^>]*folder[^>]*>"', '"%s"' % SIM_FOLDER, c)
            self.assertEqual(self.verdicts(c, hooks), [], c)


if __name__ == "__main__":
    unittest.main(verbosity=1)
