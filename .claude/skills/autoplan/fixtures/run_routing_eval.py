#!/usr/bin/env python3
"""run_routing_eval — the first caller of system/parts/routing_evals.py (card 6.4, 2026-09-05).

WHAT: hands routing.json (five SHOULD-FIRE /autoplan prompts, five near-miss BOUNDARY prompts
that should NOT fire it) and autoplan's own SKILL.md description to routing_evals.py, per the
CLI it documents in system/sops/skill-building-sop.md:
    routing_evals.py --cases CASES.json (--description "..." | --description-file F)
                      [--k N] [--model sonnet] [--json] [--selftest]

This script is a thin adapter: it locates routing_evals.py, pulls the `description:` field out
of autoplan's SKILL.md frontmatter, and shells out. It makes zero routing judgment itself.

KNOWN BLOCKER, stated plainly rather than worked around: as of 2026-09-05, `git log --all` for
this repo has no commit ever touching system/parts/routing_evals.py -- the file the
skill-building-sop.md catalog describes as "Tier 3 -- BUILT, ZERO CALLERS ANYWHERE" does not
exist on disk in this checkout. This script is the caller the card asked for; it cannot exercise
routing_evals.py until that file exists. Running this prints exactly that, with exit code 1,
rather than a bare traceback or a silent no-op that looks like a pass.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
ROUTING_EVALS = os.path.join(REPO_ROOT, "system", "parts", "routing_evals.py")
CASES = os.path.join(HERE, "routing.json")
SKILL_MD = os.path.join(HERE, "..", "SKILL.md")


def skill_description(path):
    """Pull the `description: "..."` line out of a SKILL.md frontmatter block."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("description:"):
                val = line[len("description:"):].strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                return val
    raise ValueError(f"no `description:` line found in {path}")


def main():
    if not os.path.exists(CASES):
        print(f"CANNOT-READ: no cases file at {CASES}")
        return 1
    with open(CASES, encoding="utf-8") as f:
        json.load(f)  # fail loud on malformed cases, before ever shelling out

    if not os.path.exists(ROUTING_EVALS):
        print(f"BLOCKED: {ROUTING_EVALS} does not exist in this checkout.")
        print("This script (fixtures/run_routing_eval.py) is the caller card 6.4 was asked to")
        print("write for it -- system/parts/routing_evals.py itself is out of this card's owned")
        print("scope (fixtures/ + this caller only) and is not mine to author. Flagging rather")
        print("than fabricating it: see system/sops/skill-building-sop.md's Tier 3 catalog entry,")
        print("which describes it as already built -- it is not, in this checkout.")
        return 1

    desc = skill_description(os.path.normpath(SKILL_MD))
    cmd = [sys.executable, ROUTING_EVALS, "--cases", CASES, "--description", desc]
    print("running:", " ".join(cmd))
    r = subprocess.run(cmd)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
