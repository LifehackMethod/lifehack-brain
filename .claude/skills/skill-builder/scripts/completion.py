#!/usr/bin/env python3
"""completion.py — Caller: step prompt 4 (step-4-shake-the-tree.md, the prep report 4.0 and the
validation moment 4.6) and step 5 (step-5-the-hand-off.md, 5.3's Screen B): wherever the house
style's figure line `<the bar from code> <the figure from code>% · *<the footer phrase from code>*`
is rendered for the draft spec.
Sub-step: computes the draft spec's completion figure BY CODE, never by the AI (form's "READY FOR
THE PLANNER?", and spec §10: informs and never insists).
Usage:
    completion.py --spec <path to draft-spec.md> [--timeout 20]

What counts (from the form's READY FOR THE PLANNER section + spec extract):
  A SLOT is a line in the counted sections (COVER SHEET through §11, RESEARCH FOLDED IN, DECISIONS,
  ROUTED NOTES — the LEGEND, the form header and *Example:* lines are excluded) that carries one of
  the form's line-kind marks. DONE means FILLED and CONFIRMED. Per line, first rule that fires wins:
    1. `[stale]` (or a trailing `· stale`)                → slot, NOT done (stale is never done)
    2. `[inferred]` or `[hypothesis]` marker              → slot, NOT done (unconfirmed)
    3. an unfilled blank `<…>` still present              → slot, NOT done (not filled)
    4. `[builder's choice]`                               → slot, DONE ([builder] lines filled count)
    5. a confirmed citation `(D<n>)`                      → slot, DONE (no marker, cites its D-number)
  Each OPEN §8 item (## 8. OPEN — NOT YET DECIDED, numbered lines) is one extra unfilled slot.
  FOR THE PLANNER AND THE BUILD and READY FOR THE PLANNER sections are NEVER counted.

Output: ONE finished string on stdout: `<bar> <figure>% · *<phrase>*`, the house style's figure
line. The bar is ten segments, `▰` filled / `▱` empty, filled = round(figure/10).
Band edges (recorded here per the task; the house style fixes only the phrases and the ~90% edge —
the 50% edge for "mostly filled" is this script's judgment call, chose because "mostly filled, with
some gaps" reads as at least half):
    figure <  50 → *not ready to move on*            (important parts still undecided)
    figure <  90 → *wouldn't recommend moving on yet* (mostly filled, some gaps)
    figure >= 90 → *probably okay to move on*         (the house style's own edge)

Exit codes (distinct, documented):
    0 PASS — figure printed; or NOTHING printed when there is no figure to give (zero countable
             slots — judgment call: the task's "prints NOTHING (and exit 0)" rule is taken literally,
             so no receipt either).
    1 FAIL — never used: this script reports a figure, it does not gate.
    2 COULD-NOT-CHECK — spec path missing/unreadable, bad args, or the timeout fired (loud refusal,
             nothing else).

Writes NOTHING anywhere (stdout only) — it never gates and never writes.
"""

import argparse
import os
import re
import signal
import sys

DEFAULT_TIMEOUT = 20  # seconds

BLANK_RE = re.compile(r"<[^<>]{1,300}>")
OPEN_ITEM_RE = re.compile(r"^\s*\d+\.\s")
D_CITE_RE = re.compile(r"\(D\d+\)")
SECTION_RE = re.compile(r"^##\s+")
# Sections never counted, matched as prefixes of the `## ` heading.
SKIP_SECTIONS = ("## LEGEND", "## FOR THE PLANNER AND THE BUILD", "## READY FOR THE PLANNER")
# The open §8 section: its numbered items each count as an unfilled slot.
OPEN_SECTION = "## 8. OPEN"


def refuse(why, what_to_do, rule):
    print("REFUSED: %s" % why)
    print("DO: %s" % what_to_do)
    print("RULE: %s" % rule)


def receipt(verdict, reason, untested):
    print("RECEIPT completion.py %s %s | untested: %s" % (verdict, reason, untested))


def _classify(line):
    """Return 'done', 'not-done' or None (not a slot). First rule that fires wins."""
    stripped = line.strip()
    if "[stale]" in line or stripped.endswith("· stale") or stripped.endswith("- stale"):
        return "not-done"
    if "[inferred]" in line or "[hypothesis]" in line:
        return "not-done"
    if BLANK_RE.search(line):
        return "not-done"
    if "[builder's choice]" in line:
        return "done"
    if D_CITE_RE.search(line):
        return "done"
    return None


def count(spec_text):
    total = done = 0
    section = "count"  # lines before the first heading count too
    in_fence = False
    for raw in spec_text.splitlines():
        line = raw
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if SECTION_RE.match(line):
            heading = line.strip()
            if any(heading.startswith(p) for p in SKIP_SECTIONS):
                section = "skip"
            elif heading.startswith(OPEN_SECTION):
                section = "open"
            else:
                section = "count"
            continue
        if "*Example:*" in line:
            continue
        if section == "open":
            if OPEN_ITEM_RE.match(line):
                total += 1
            continue
        if section != "count":
            continue
        verdict = _classify(line)
        if verdict is None:
            continue
        total += 1
        if verdict == "done":
            done += 1
    return total, done


def bar_and_phrase(figure):
    filled = int(round(figure / 10.0))
    filled = max(0, min(10, filled))
    bar = "▰" * filled + "▱" * (10 - filled)
    if figure >= 90:
        phrase = "probably okay to move on"
    elif figure >= 50:
        phrase = "wouldn't recommend moving on yet"
    else:
        phrase = "not ready to move on"
    return bar, phrase


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True, help="path to the draft spec (markdown, on the skill spec form)")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = ap.parse_args(argv)

    if args.timeout <= 0:
        refuse("timeout must be a positive number of seconds",
               "pass --timeout <seconds> greater than 0",
               "every script wraps its work in a hard time limit and exits 2 when it fires")
        receipt("COULD-NOT-CHECK", "bad --timeout %r" % args.timeout, "the spec was not counted")
        return 2

    def _on_timeout(signum, frame):
        refuse("the run exceeded its %d s time limit" % args.timeout,
               "retry once; if it still hangs, report the hang to the step's owner",
               "every script fails loudly on a timeout and exits 2, never 0")
        receipt("COULD-NOT-CHECK", "timed out after %ds" % args.timeout, "the spec was not counted")
        sys.exit(2)

    signal.signal(signal.SIGALRM, _on_timeout)
    signal.alarm(args.timeout)
    try:
        if not os.path.isfile(args.spec):
            refuse("no spec file at %r" % args.spec,
                   "pass --spec with the draft spec's real path (the packet's draft-spec section names it)",
                   "a completion figure is computed from the form's own text; no file, no figure")
            receipt("COULD-NOT-CHECK", "spec file missing", "the spec was not counted")
            return 2
        try:
            with open(args.spec, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            refuse("the spec file could not be read: %s" % e,
                   "check the path and its permissions, then retry",
                   "a figure computed from a file that cannot be read is a guess, not a figure")
            receipt("COULD-NOT-CHECK", "spec unreadable", "the spec was not counted")
            return 2

        total, done = count(text)
        if total == 0:
            # No figure to give: prints NOTHING, exit 0 (judgment call recorded in the docstring).
            return 0
        figure = int(round(100.0 * done / total))
        bar, phrase = bar_and_phrase(figure)
        print("%s %d%% · *%s*" % (bar, figure, phrase))
        receipt("PASS", "%d of %d slots filled and confirmed" % (done, total),
                "the D-number citations' authenticity (that each cited D-line exists) is 5.2's check, not this one")
        return 0
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
