#!/usr/bin/env python3
"""inputs_check.py — the inputs line and the pause, per sub-step.

CALLER: run at the start of each skill-builder sub-step, by that sub-step's step
prompt's "what you read and write" routine (prompts/step-1…5-*.md; the runner's
step code may also call it before launching a helper). Usage:

    inputs_check.py --workdir <packet folder> --substep <e.g. 1.6> [--timeout 20]

WHY NO SHARED TOOL COVERS IT: the shared tools in system/register/toolbox.md are
generic file readers/writers and repo guards; none of them knows this skill's
spec §4 "incoming" table or the §5 section names. This is skill-local knowledge,
so it lives in the skill. Repo paths (if ever needed) resolve through
shared/paths.py, never hard-coded; this script takes every path as an argument
and writes NOTHING anywhere — stdout only.

Scratchpad layout (documented, as the task requires): ONE folder per skill being
designed — the packet folder. Each §5 scratchpad section is ONE file:

    <workdir>/scratchpad/<section>.md

A section counts as PRESENT only if its file exists AND is non-empty after
trimming whitespace. Missing file, empty file and whitespace-only file are all
"missing".

Exit codes: 0 PASS — all required sections present; prints `inputs: <list>`.
1 FAIL — at least one required section missing; prints the pause line(s) the
spec §4 gives (exact wording where the spec states it), and NEVER launches
anything. 2 COULD-NOT-CHECK — bad args, unknown sub-step, unreadable workdir,
timeout.

Off-list values are rejected LOUDLY: every refusal prints why, what to do, and
the rule.
"""

import argparse
import os
import signal
import sys
import time

# Repo-shared helpers, found from THIS FILE's position (walk up to the folder
# that holds shared/paths.py), never from cwd. When the script runs from a
# copied location (the broken-copy test), the walk finds nothing and PYTHONPATH
# must carry <repo>/shared instead.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _d in (os.path.dirname(_HERE), os.path.dirname(os.path.dirname(_HERE)),
           os.path.dirname(os.path.dirname(os.path.dirname(_HERE))),
           os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_HERE))))):
    if os.path.isfile(os.path.join(_d, "shared", "paths.py")):
        sys.path.insert(0, os.path.join(_d, "shared"))
        break
try:
    import paths  # shared/paths.py — the one place repo paths are answered; no hard-coded path here
except Exception:
    paths = None  # only reachable from a copied location; this script needs no repo path

DEFAULT_TIMEOUT = 20

# ── Spec §4 "incoming" table. sub-step -> [(section, required)] ──────────────────
INCOMING = {
    "1.1": [("handoff-in", False)],
    "1.2": [("packet-path", True), ("pointed-skill", False)],
    "1.3": [("skill-reading", True)],
    "1.4": [("packet-path", True), ("known", True), ("skill-checked", False),
            ("harness-checked", False), ("research-mark", False), ("size-sense", False)],
    "1.6": [("outcome", True), ("packet-path", True)],
    "1.7": [("harness-findings", True)],
    "1.8": [("outcome", True), ("which-skill", False), ("packet-path", True),
            ("steps-draft", False)],
    "1.9": [("outcome", True), ("packet-path", True)],
    "2.1": [("outcome", True), ("skill-checked", False), ("harness-checked", True),
            ("research-mark", False), ("status", False)],
    "3.1": [("packet-path", True), ("steps-draft", True), ("step-prompts-checked", True),
            ("heal-checked", False), ("tension-rulings", False), ("correction", False),
            ("status", False)],
    "3.2": [("break", True)],
    "3.3": [("heal-proposal", True)],
    "3.4": [("packet-path", True), ("answers", True), ("heal-checked", False),
            ("step-prompts-checked", True), ("stale", False)],
    "4.0a": [("packet-path", True), ("step-prompts-checked", True)],
    "4.0": [("status", True), ("packet-path", True), ("steps-draft", True)],
    "4.1a": [("steps-draft", True), ("packet-updated", False), ("packet-path", True),
             ("prep-decisions", False)],
    "4.1b": [("open-facts", True), ("packet-path", True)],
    "4.1c": [("facts", True), ("steps-draft", True), ("packet-updated", False),
             ("packet-path", True), ("prep-decisions", False)],
    "4.2": [("tensions", True), ("proposals", True)],
    "4.3": [("tensions-checked", True), ("status", False)],
    "4.5": [("packet-path", True)],
    "4.6": [("validation", True), ("status", False)],
    "5.0": [("packet-path", True), ("validation", False), ("status", False)],
    "5.1": [("packet-path", True), ("known", False), ("parts-result", False)],
    "5.2": [("draft-spec", True), ("packet-path", True), ("stale", False)],
    "5.3": [("draft-spec", True), ("draft-check", True), ("status", False)],
    "5.4": [("draft-spec", True), ("packet-path", True), ("destination", False),
            ("filing", False)],
    "5.5": [("status", True)],
}

# Who writes each section — spec §5 table — words the pause line when the spec
# does not state one explicitly for this sub-step.
WRITER = {
    "handoff-in": "background (/build)",
    "packet-path": "1.1",
    "known": "1.1",
    "pointed-skill": "1.4",
    "which-skill": "1.4",
    "skill-reading": "1.2",
    "skill-checked": "1.3",
    "outcome": "1.4",
    "harness-findings": "1.6",
    "harness-checked": "1.7",
    "research-mark": "1.8",
    "size-sense": "1.9",
    "steps-draft": "2.1",
    "step-prompts": "2.1",
    "step-prompts-checked": "2.1",
    "break": "3.1",
    "heal-proposal": "3.2",
    "heal-checked": "3.3",
    "answers": "3.1",
    "packet-updated": "3.4",
    "prep-decisions": "4.0",
    "tensions": "4.1a",
    "open-facts": "4.1a",
    "facts": "4.1b",
    "proposals": "4.1c",
    "tensions-checked": "4.2",
    "tension-rulings": "4.3",
    "validation": "4.5",
    "tool-builder-message": "5.0",
    "parts-result": "5.0",
    "draft-spec": "5.1",
    "draft-check": "5.2",
    "destination": "5.3",
    "filing": "5.3",
    "correction": "5.3",
    "handoff-note": "5.4",
    "stale": "the TALK sub-step landed on after a /back",
    "status": "the last sub-step",
}

# Pause lines spec §4 states word for word: sub-step -> {section: exact phrase}.
EXPLICIT_PAUSE = {
    "1.2": {"packet-path": "waiting: packet from 1.1"},
    "1.4": {"packet-path": "waiting: packet from 1.1"},
    "2.1": {"harness-checked": "waiting: findings checked by 1.7"},
    "3.1": {"steps-draft": "waiting: steps from 2.1"},
    "3.4": {"answers": "waiting: answers from 3.1"},
    "4.0": {"packet-path": "waiting: packet from 1.1",
            "steps-draft": "waiting: steps from 2.1"},
    "4.3": {"tensions-checked": "waiting: checked tensions from 4.2"},
    "4.6": {"validation": "waiting: validation from 4.5"},
    "5.3": {"draft-check": "waiting: checked draft spec from 5.2"},
    "5.5": {"status": "waiting: hand-over result from 5.4"},
}


class TimeUp(Exception):
    pass


def arm_timeout(seconds):
    def handler(signum, frame):
        raise TimeUp()
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(max(1, int(seconds)))


def refuse(why, what_to_do, rule):
    print(f"REFUSED: {why}")
    print(f"WHAT TO DO: {what_to_do}")
    print(f"RULE: {rule}")


def script_name():
    return os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else "inputs_check.py"


def section_present(workdir, section):
    """Present = <workdir>/scratchpad/<section>.md exists and non-empty after trim.

    The filename must match the section name EXACTLY (case-sensitive compare
    against the scratchpad listing) — a case-insensitive filesystem must not turn
    a near-miss spelling into a pass.
    """
    path = os.path.join(workdir, "scratchpad", section + ".md")
    try:
        entries = os.listdir(os.path.join(workdir, "scratchpad"))
    except OSError:
        return False
    if (section + ".md") not in entries:  # exact, case-sensitive
        return False
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except OSError:
        return False
    return bool(content.strip())


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check a sub-step's required scratchpad sections (skill-builder).")
    parser.add_argument("--workdir", required=True, help="the packet folder")
    parser.add_argument("--substep", required=True, help="e.g. 1.6")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    args = parser.parse_args(argv)

    if args.substep not in INCOMING:
        refuse(f"sub-step '{args.substep}' is not one spec §4 defines",
               "pass a sub-step number from spec §4, e.g. --substep 1.6",
               "off-list values are rejected loudly; an unknown sub-step's inputs are UNKNOWN, "
               "never guessed, and this script never exits 0 when it could not check")
        print(f"RECEIPT {script_name()} COULD-NOT-CHECK unknown sub-step {args.substep} | "
              f"untested: nothing was checked")
        return 2

    if not os.path.isdir(args.workdir):
        refuse(f"workdir '{args.workdir}' is not a readable folder",
               "pass the packet folder: --workdir <packet folder>",
               "a missing packet folder is COULD-NOT-CHECK, never a pass")
        print(f"RECEIPT {script_name()} COULD-NOT-CHECK unreadable workdir | "
              f"untested: nothing was checked")
        return 2

    arm_timeout(args.timeout)
    try:
        required = [s for s, req in INCOMING[args.substep] if req]
        optional = [s for s, req in INCOMING[args.substep] if not req]
        missing = [s for s in required if not section_present(args.workdir, s)]
        present_optional = [s for s in optional if section_present(args.workdir, s)]
    except TimeUp:
        print(f"RECEIPT {script_name()} COULD-NOT-CHECK timed out after {args.timeout}s | "
              f"untested: presence of the required sections")
        return 2
    finally:
        signal.alarm(0)

    if missing:
        for section in missing:
            phrase = EXPLICIT_PAUSE.get(args.substep, {}).get(section)
            if not phrase:
                phrase = f"waiting: {section} from {WRITER.get(section, 'an earlier sub-step')}"
            print(phrase)
        print(f"RECEIPT {script_name()} FAIL missing {len(missing)} of {len(required)} required "
              f"({', '.join(missing)}) | untested: content of the sections that were present")
        return 1

    names = required + present_optional
    print(f"inputs: {', '.join(names) if names else '(none)'}")
    print(f"RECEIPT {script_name()} PASS all {len(required)} required sections present | "
          f"untested: section contents beyond non-emptiness; sections of other sub-steps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
