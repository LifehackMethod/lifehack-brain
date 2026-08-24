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

issue #13 — WIDENED 2026-08-23: `.claude/agents/*.md` is not the only place a sub-agent gets
dispatched from. `council` and `advisory-council` (and, it turns out, several other skills — see
`skill_files_with_unpinned_dispatch()` below) drive a bare `Agent` tool call from PROSE inside their
own `SKILL.md`. That dispatch is structurally invisible to a checker that only walks
`.claude/agents/` — a bare, unpinned spawn there inherits BOTH the session's model tier (the
expensive outcome `test_every_agent_pins_a_model` exists to catch) AND the harness's default agent
type, and until now nothing here could see it happen at all. This module cannot fix those skills —
`.claude/skills/**` is edited under its own gate, deliberately not this one — so it only WIDENS THE
CHECK: any `SKILL.md` whose own prose instructs dispatching a sub-agent (the `Agent` tool,
"dispatch/spawn/launch ... sub-agent") is reported by name UNLESS the file also pins a real model
tier, the same way a bare `.claude/agents/*.md` file already is.

issue #13 FOLLOW-UP — same day, before this ever shipped: the first cut of this check literally
grepped for the token `subagent_type`, on the theory that a dispatch naming its target agent type is
"pinned". That is the wrong question. The house rule this test enforces (CLAUDE.md, "Sending work to
a sub-agent") is about the MODEL, not the agent type: "spawned helpers always get an explicit model —
they never inherit the session's." `subagent_type` says WHICH agent template runs; it says nothing
about which model tier it runs ON, so a checker keyed to it is checking the wrong field entirely — and
it produced 3 false positives out of 8 (`council`, `advisory-council`, `audit` all pin the model in
emphatic prose — e.g. council SKILL.md: "**Model — HARD:** pin `model: sonnet` on EVERY `Agent`
dispatch" — and were still flagged, because none of them happen to also contain the literal word
`subagent_type`).

issue #13 SECOND FOLLOW-UP — same day, measured against the second cut before shipping it: the
`model:\s*(sonnet|opus|haiku)` key-value shape was ALSO the wrong question, and it produced 4 false
positives out of 5 flagged — `archivist-deepmine`, `canon-audit`, `design-lifehack`, and `throughline`
all name a tier in prose that never happens to sit next to a colon
(`archivist-deepmine`:57 "Sonnet only, never opus (subagent model rule)"; `canon-audit`:53 "Subagents
sonnet-only, waves of 2–3"; `design-lifehack`:74 "FRESH-EYES and de-bias subagents run Sonnet —
always, no exception"; `throughline`:164 "one sub-agent, sonnet"). Only `clair-session-close` names no
tier anywhere.

THE ROOT CAUSE, written down elsewhere in this repo already: `system/build-rules-index.md`
(CODE-SPIRAL-v2) — "IS THERE A SOFT WORD IN IT? … If you must define the word before you can write
the check, that definition IS the judgment — and judgment is the model's half. Code gets membership
('is X in this list?'), artifacts, and timing. Nothing else." "Is this dispatch properly pinned, in
the right shape, close enough to the dispatch to count" is a judgment question — both prior cuts tried
to mechanize it by inventing a shape (`subagent_type`, then `model:<tier>`) and both shapes turned out
not to be the invariant the house rule actually depends on. A regex cannot tell "an instruction
pinning THIS dispatch" from "a sentence that happens to mention a tier" — that is reading for meaning,
which is exactly the job a cheap mechanical check must not attempt.

THE RULE NOW, narrowed to membership only: a skill is compliant if it names a model tier — the literal
word `sonnet`, `opus`, or `haiku`, case-insensitive — ANYWHERE in the file. No colon, no `model:` key,
no proximity to the dispatch required. This is deliberately, admittedly LOOSER than either prior cut:
a skill that named a tier in a sentence wholly unrelated to any dispatch (an example, a comparison, a
throwaway aside) would still PASS here, uninspected. That is an accepted false negative, not an
oversight — the alternative (judging whether the naming is "properly attached to the dispatch") is
the exact judgment call that produced two rounds of false positives, and a check that keeps crying
wolf gets ignored, which protects nothing. An honest narrow check that only catches the blatant case
— a dispatching skill that never says a tier at all, anywhere, in any context — beats a broad one
nobody trusts enough to act on. Verified against all 8 originally-flagged skills: `council`,
`advisory-council`, `audit`, `archivist-deepmine`, `canon-audit`, `design-lifehack`, and `throughline`
all contain at least one of the three tier words somewhere and now PASS; only `clair-session-close`
contains none of the three anywhere in the file and is FLAGGED.
"""

import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AGENTS = os.path.join(REPO, ".claude", "agents")
SKILLS = os.path.join(REPO, ".claude", "skills")

# ── issue #13 — bare Agent/sub-agent dispatch, invisible in `.claude/agents/*.md` alone ─────────
# Matches the actual phrasing this repo's skills use to instruct a real dispatch (verified against
# every current SKILL.md, see the 2026-08-23 investigation): the literal `Agent` tool referenced by
# name, or a dispatch/spawn/launch verb sitting near "sub-agent"/"subagent" within the same
# sentence-ish span. Deliberately NOT just the bare word "agent" — this repo's prose also uses
# "agent" for unrelated things (e.g. a Google Calendar literally named "Agent Ops"), and matching
# that word alone would flag those, not a real dispatch.
_SKILL_DISPATCH_PATTERNS = (
    re.compile(r"`Agent`\s+tool|\bAgent\s+tool\b"),
    re.compile(r"\bdispatch\w*\b[^.\n]{0,100}\bsub-?agents?\b", re.I),
    re.compile(r"\bsub-?agents?\b[^.\n]{0,100}\bdispatch\w*\b", re.I),
    re.compile(r"\bspawn\w*\b[^.\n]{0,100}\bsub-?agents?\b", re.I),
    re.compile(r"\blaunch\w*\b[^.\n]{0,100}\b(?:Agent tool|sub-?agents?)\b", re.I),
)

# MEMBERSHIP ONLY (see the module docstring's second follow-up): does the file contain one of the
# three model-tier words ANYWHERE, in any shape, any context? That is a list-membership question code
# can answer without judgment. It is deliberately NOT trying to confirm the naming is attached to the
# dispatch, in a `model:` key shape, or anywhere near it — two earlier attempts at that judgment both
# produced false positives, because "is this pin properly attached" is a meaning question, not a
# mechanical one. This pattern will pass a file that names a tier in prose wholly unrelated to any
# dispatch — an accepted, stated trade-off, not an oversight; see the docstring.
_MODEL_PIN_PATTERN = re.compile(r"\b(sonnet|opus|haiku)\b", re.I)


def skill_files():
    if not os.path.isdir(SKILLS):
        return []
    out = []
    for name in sorted(os.listdir(SKILLS)):
        path = os.path.join(SKILLS, name, "SKILL.md")
        if os.path.isfile(path):
            out.append(path)
    return out


def skill_files_with_unpinned_dispatch():
    """Every `SKILL.md` whose prose instructs a real sub-agent dispatch (see the patterns above)
    but never names a model tier — `sonnet`/`opus`/`haiku`, membership only, see `_MODEL_PIN_PATTERN`
    above and the module docstring's second follow-up for why this is deliberately NOT checking
    `model:` or proximity to the dispatch. Returns repo-relative paths, sorted, so a failure names
    exactly which skill(s) to fix — under their own edit gate, not this one."""
    hits = []
    for path in skill_files():
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if _MODEL_PIN_PATTERN.search(text):
            continue
        if any(p.search(text) for p in _SKILL_DISPATCH_PATTERNS):
            hits.append(os.path.relpath(path, REPO))
    return sorted(hits)

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

    def test_no_skill_dispatches_a_bare_unpinned_agent(self):
        """issue #13 — a `.claude/agents/*.md` file is not the only place a sub-agent gets spawned
        from. A `SKILL.md` that instructs dispatching one via prose, without ever pinning a real
        model tier (`sonnet`/`opus`/`haiku`, named anywhere in the file — membership only, see
        `_MODEL_PIN_PATTERN`) is exactly as unpinned as a bare agent frontmatter would be — it just
        was invisible to this test before now. This CANNOT be fixed here (`.claude/skills/**` is
        edited under its own gate, not this test's), so it only names names."""
        offenders = skill_files_with_unpinned_dispatch()
        self.assertEqual(
            offenders, [],
            "these SKILL.md files instruct a bare sub-agent dispatch (the `Agent` tool / "
            "dispatch·spawn·launch a sub-agent) but never name a model tier "
            "(`sonnet`/`opus`/`haiku`, anywhere in the file) at all, so the spawn is "
            f"structurally invisible and unpinned: {offenders}")

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
