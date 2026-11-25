#!/usr/bin/env python3
"""gates.py — Caller: every TALK sub-step's step prompt (step-1…step-6-*.md), at each
`→ CODE (...)` question: the instant the person answers a fixed question, the sub-step runs this
to read the typed answer against ONE closed answer set and print the chosen member.
Usage:
    gates.py --set "refine|move-on|none-of-these" --answer "<what the person typed>"
    gates.py --set-id <id> --answer "<what the person typed>"
    gates.py --list-sets

Why no shared tool covers it: the toolbox has text matchers for files and receipts, but nothing
that enforces the ladder's closed-answer-set rule (spec §4: every set ends in `none-of-these`,
which never moves the run) in code, at the moment a person answers.

Exit codes (distinct, documented):
    0 PASS — a member matched exactly (trimmed, lower-cased), or `none-of-these` was chosen.
    1 FAIL — the answer is not one of the set: prints `none-of-these` and a refusal (why / what to
             do / rule). Deny by default: anything unrecognised is a fail, never a pass.
    2 COULD-NOT-CHECK — bad args, set missing or not ending in `none-of-these`, unknown --set-id,
             empty answer, or the timeout fired.

The named sets (--set-id ids), from the skill's spec §4 ladder (documented ids):
    destination    autoplan | project-window | none-of-these          (step 6, where it goes)
    prep-report    decide-now | let-reviewers-guess | none-of-these    (step 5, the prep report)
    validation     fill-gaps | move-on | none-of-these                 (step 5, the validation)
    audience       for-me | for-everyone | none-of-these               (step 6, who it is for)
    findings       more | redesign | move-on | none-of-these           (step 5, the findings)
    roleplay       refine | move-on | none-of-these                    (step 4, each round)
    roleplay-skip  refine | move-on | skip-role-play | none-of-these   (step 3, each walk-through round)
    overview       refine | move-on | none-of-these                    (step 2, each round)
    rounds-step1   refine | points-at-skill | move-on | none-of-these  (step 1, each round)
    send           send | not-yet | none-of-these                      (step 6, send it)
    existing       start-from-existing | build-new | none-of-these     (step 1, lifehack already does it)
    hand-to-build  take-it | carry-on | none-of-these                  (steps 1 & 2, too big for a skill)
    parts-round    refine | move-on | none-of-these                    (step 6, the parts round)

Writes NOTHING anywhere (stdout only) — the caller owns the scratchpad.
"""

import argparse
import signal
import sys

ANSWER_SETS = {
    "destination": ["autoplan", "project-window", "none-of-these"],
    "prep-report": ["decide-now", "let-reviewers-guess", "none-of-these"],
    "validation": ["fill-gaps", "move-on", "none-of-these"],
    "audience": ["for-me", "for-everyone", "none-of-these"],
    "findings": ["more", "redesign", "move-on", "none-of-these"],
    "roleplay": ["refine", "move-on", "none-of-these"],
    "roleplay-skip": ["refine", "move-on", "skip-role-play", "none-of-these"],
    "overview": ["refine", "move-on", "none-of-these"],
    "rounds-step1": ["refine", "points-at-skill", "move-on", "none-of-these"],
    "send": ["send", "not-yet", "none-of-these"],
    "existing": ["start-from-existing", "build-new", "none-of-these"],
    "hand-to-build": ["take-it", "carry-on", "none-of-these"],
    "parts-round": ["refine", "move-on", "none-of-these"],
}

DEFAULT_TIMEOUT = 20  # seconds


# Marker line the BROKEN-COPY test rewrites; keep this exact form stable.
def _matches(answer, members):
    matched = answer in members
    return matched


def refuse(why, what_to_do, rule):
    print("REFUSED: %s" % why)
    print("DO: %s" % what_to_do)
    print("RULE: %s" % rule)


def receipt(verdict, reason, untested):
    print("RECEIPT gates.py %s %s | untested: %s" % (verdict, reason, untested))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default=None,
                    help='closed answer set, pipe-separated, MUST end in "none-of-these"')
    ap.add_argument("--set-id", default=None, help="a named set id (see --list-sets)")
    ap.add_argument("--answer", default=None, help="what the person typed")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--list-sets", action="store_true")
    args = ap.parse_args(argv)

    if args.list_sets:
        for sid, members in ANSWER_SETS.items():
            print("%s: %s" % (sid, " | ".join(members)))
        receipt("PASS", "listed %d answer sets" % len(ANSWER_SETS), "no answer was checked in this run")
        return 0

    if args.timeout <= 0:
        refuse("timeout must be a positive number of seconds",
               "pass --timeout <seconds> greater than 0",
               "every script wraps its work in a hard time limit and exits 2 when it fires")
        receipt("COULD-NOT-CHECK", "bad --timeout %r" % args.timeout, "no answer was checked in this run")
        return 2

    def _on_timeout(signum, frame):
        refuse("the run exceeded its %d s time limit" % args.timeout,
               "retry once; if it still hangs, report the hang to the step's owner",
               "every script fails loudly on a timeout and exits 2, never 0")
        receipt("COULD-NOT-CHECK", "timed out after %ds" % args.timeout, "no answer was checked in this run")
        sys.exit(2)

    signal.signal(signal.SIGALRM, _on_timeout)
    signal.alarm(args.timeout)
    try:
        return _run(args)
    finally:
        signal.alarm(0)


def _run(args):
    if (args.set is None) == (args.set_id is None):
        refuse("exactly one of --set or --set-id is required (got %s)"
               % ("both" if args.set is not None else "neither"),
               'pass --set "a|b|none-of-these" or --set-id <id from --list-sets>',
               "every code-read answer set ends in none-of-these, which never moves the run")
        receipt("COULD-NOT-CHECK", "bad arguments", "no answer was checked in this run")
        return 2

    if args.set_id is not None:
        if args.set_id not in ANSWER_SETS:
            refuse("unknown --set-id %r" % args.set_id,
                   "run --list-sets to see the ids the skill uses",
                   "every code-read answer set ends in none-of-these, which never moves the run")
            receipt("COULD-NOT-CHECK", "unknown set id", "no answer was checked in this run")
            return 2
        members = list(ANSWER_SETS[args.set_id])
        set_desc = "set-id %s" % args.set_id
    else:
        members = [p.strip() for p in args.set.split("|")]
        set_desc = "inline set"

    if not members or members[-1] != "none-of-these":
        refuse("the answer set does not end in none-of-these (got: %s)" % (" | ".join(members) or "<empty>"),
               "append none-of-these to the set, or use a named set (--list-sets)",
               "every code-read answer set ends in none-of-these, which never moves the run")
        receipt("COULD-NOT-CHECK", "set does not end in none-of-these", "no answer was checked in this run")
        return 2

    if args.answer is None or not args.answer.strip():
        refuse("no answer was given (empty or missing --answer)",
               "ask the person again, in the sub-step's own words, and pass what they typed",
               "an empty answer is never a match; the set's none-of-these never fires on silence")
        receipt("COULD-NOT-CHECK", "empty answer", "no answer was checked in this run")
        return 2

    answer = args.answer.strip().lower()
    if _matches(answer, [m.strip().lower() for m in members]):
        if answer == "none-of-these":
            print("none-of-these")
            receipt("PASS", "none-of-these chosen — does not move the run",
                    "the sub-step's re-ask behaviour is the caller's, not this script's")
            return 0
        print(answer)
        receipt("PASS", "matched %s of %s" % (answer, set_desc),
                "downstream effects of the choice belong to the caller, not this script")
        return 0

    # Not recognised — deny by default: print none-of-these, refuse loudly, exit 1.
    print("none-of-these")
    refuse("the answer %r is not one of: %s" % (args.answer.strip(), " | ".join(members)),
           "ask the person again, in the sub-step's own words, and offer the same fixed choices",
           "every code-read answer set ends in none-of-these, which never moves the run")
    receipt("FAIL", "answer not one of: %s" % " | ".join(members),
            "the re-ask itself is the caller's act, not this script's")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
