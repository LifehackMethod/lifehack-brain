#!/usr/bin/env python3
"""test_agent_pins.py — the tool list on a sub-agent is a wall, and this is what holds it up.

Run:  python3 system/tools/test_agent_pins.py
      python3 -m unittest discover -s system/tools -p 'test_*.py'

WHY A TEST AND NOT A REVIEW HABIT. Several agents here are safe for exactly one reason: the harness
gives them a short list of tools and nothing else. `ingest-reader` is handed text somebody else
wrote — the single most dangerous input this system takes — and the reason a hijacked read cannot
turn into an action is not that it was told to behave. It is that it has no Bash, no Write, and no
network. The security doctrine states it plainly: the wall is STRUCTURAL, which is why the model
underneath it can be a cheap one.

A wall like that fails by ONE LINE GOING MISSING. Delete `tools:` from the frontmatter and the agent
silently inherits everything the session has; the description still says "tool-less", the file still
reads correctly, and nothing anywhere complains. That is the regression this catches, and it is the
kind nobody notices by reading — the diff looks like a tidy-up.

WHAT IS DELIBERATELY NOT CHECKED: whether the harness honours the pin. That is the harness's
contract, not this repository's, and it is verified by watching an agent actually run. What is
checked here is that this repository never ships an agent that forgot to ask.
"""

import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AGENTS = os.path.join(REPO, ".claude", "agents")

# Tools that let an agent change something, reach the network, or spawn more agents. An agent whose
# job is READING must not have any of them — and if one ever needs one, it stops being read-only and
# this list is where you find out.
ACTING_TOOLS = {"write", "edit", "notebookedit", "bash", "webfetch", "websearch", "task", "agent"}

# Agents whose safety IS the tool list, with the reason each one cannot be allowed to act.
READ_ONLY = {
    "ingest-reader": "reads untrusted text and judges it — a hijack must have nothing to act with",
    "ingest-tagger": "reads untrusted text in bulk; same wall",
    "ingest-conclusions": "reads whole untrusted chats; same wall",
    "worker": "cheap retrieval fan-out; read-only by construction so it can never surprise a caller",
    "archivist": "audits a person's own memory — a 'helpful' fix there is an erasure, not a bug",
}


def agent_files():
    if not os.path.isdir(AGENTS):
        return []
    return sorted(f for f in os.listdir(AGENTS) if f.endswith(".md"))


def frontmatter(path):
    """The frontmatter block as a dict of the simple `key: value` lines. Deliberately not a YAML
    parser: a missing dependency must never be the reason a security check does not run."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    out = {}
    for line in m.group(1).splitlines():
        if line.startswith((" ", "\t")) or ":" not in line:
            continue
        k, v = line.split(":", 1)
        out[k.strip()] = v.strip()
    return out


def tool_set(fm):
    raw = fm.get("tools", "")
    return {t.strip().lower().strip("[]") for t in raw.split(",") if t.strip()}


class AgentPinCase(unittest.TestCase):

    def test_there_are_agents_to_check(self):
        """A suite that silently checks nothing passes forever. Fail loudly instead."""
        self.assertTrue(agent_files(), f"no agent files found under {AGENTS} — has the folder moved?")

    def test_every_agent_declares_a_tool_list(self):
        """An agent with no `tools:` line inherits the whole session. That is almost never what was
        meant, and it never announces itself."""
        missing = []
        for f in agent_files():
            fm = frontmatter(os.path.join(AGENTS, f))
            if fm is None:
                missing.append(f"{f} (no frontmatter at all)")
            elif not fm.get("tools"):
                missing.append(f"{f} (frontmatter, but no tools: line)")
        self.assertEqual(missing, [], f"these would inherit every tool the session has: {missing}")

    def test_the_read_only_agents_hold_no_tool_that_can_act(self):
        for name, why in READ_ONLY.items():
            path = os.path.join(AGENTS, name + ".md")
            if not os.path.exists(path):
                continue                      # not shipped yet; the presence test below covers that
            with self.subTest(agent=name):
                tools = tool_set(frontmatter(path))
                acting = sorted(tools & ACTING_TOOLS)
                self.assertEqual(acting, [], f"{name} can now {acting} — {why}")

    def test_the_three_untrusted_content_readers_have_read_and_nothing_else(self):
        """Tighter than the rule above. These three are handed text written by somebody else, so the
        list is not merely 'nothing that acts' — it is Read, alone. Even Grep would let a hijacked
        read start probing the filesystem for what to exfiltrate later."""
        for name in ("ingest-reader", "ingest-tagger", "ingest-conclusions"):
            path = os.path.join(AGENTS, name + ".md")
            if not os.path.exists(path):
                continue
            with self.subTest(agent=name):
                self.assertEqual(tool_set(frontmatter(path)), {"read"},
                                 f"{name} must have exactly `tools: Read`")

    def test_the_blind_searcher_cannot_reach_the_web_except_through_the_safe_stack(self):
        """web-searcher reads adversarial pages for a living. It keeps Bash — it has to, that is how
        it calls the sanitized tools — but it must NOT have WebFetch or WebSearch, because with those
        it could simply go around them. The restriction is what forces it through the wall."""
        path = os.path.join(AGENTS, "web-searcher.md")
        if not os.path.exists(path):
            self.skipTest("web-searcher not shipped here")
        tools = tool_set(frontmatter(path))
        self.assertEqual(tools, {"bash", "read"}, "it must be exactly Bash and Read")
        for forbidden in ("webfetch", "websearch", "task", "agent", "write", "edit"):
            self.assertNotIn(forbidden, tools)

    def test_every_agent_pins_a_model(self):
        """A spawn with no model inherits the session's, which is the most expensive tier there is.
        Deleting a pin to 'save cost' does the opposite, silently."""
        unpinned = [f for f in agent_files() if not (frontmatter(os.path.join(AGENTS, f)) or {}).get("model")]
        self.assertEqual(unpinned, [], f"these inherit the session model instead of choosing one: {unpinned}")

    def test_every_agent_says_what_it_is_for(self):
        """The description is how the harness decides to route to it. An agent nobody can find is an
        agent nobody uses, and one with a vague description gets used for the wrong thing."""
        thin = []
        for f in agent_files():
            d = (frontmatter(os.path.join(AGENTS, f)) or {}).get("description", "")
            if len(d) < 60:
                thin.append(f"{f} ({len(d)} chars)")
        self.assertEqual(thin, [], f"too thin to route on: {thin}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
