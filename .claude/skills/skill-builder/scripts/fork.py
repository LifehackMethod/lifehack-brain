#!/usr/bin/env python3
"""fork.py — read the human's turn-closing answer, and REFUSE to guess.

WHY THIS EXISTS. Every turn of /skill-builder ends by offering the human exactly two answers
(SPEC.md §8f):

    A — Keep refining this.        (we stay here and sharpen it)
    B — Lock it and move on.       (this is good enough; the next phase opens)

That is a CLOSED VOCABULARY, and `skill-building-sop.md` LAW 1 says what a closed vocabulary owes:
code hands over a bounded set of outcomes, the other side picks a member, and CODE ENFORCES
MEMBERSHIP FAIL-CLOSED. The set must also contain a member meaning NO OUTCOME WAS REACHED — so that
"they did not decide" can never be spelled the same way as "they said move on."

⛔ THE ONE THING THIS MUST NEVER DO IS GUESS. An unrecognised answer is not a weak A or a probable B.
It is the absence of a decision, and the caller must stop and re-ask. `/ingest` shipped three separate
bugs where something unrecognised fell through as agreement; this is the part that makes that
impossible here.

USAGE
    python3 fork.py "<the human's raw answer>" [--phase N] [--step S] [--ledger PATH]
                                                    -> prints A | B | NO_OUTCOME
                                                       exit 0 on A or B, 2 on NO_OUTCOME,
                                                       3 on DECIDED-BUT-NOT-RECORDED
    python3 fork.py --verify --phase N --step S [--since EPOCH] [--ledger PATH]
                                                    -> exit 0 only if a real row exists (and is fresh)
    python3 fork.py --selftest                      -> two-sided self-test, exit 0 only if both sides hold

THE EXIT CODE IS THE POINT. A caller that ignores stdout still cannot read a non-decision as consent,
because the process failed.

⭐ WHY THIS WRITES A LEDGER (added 2026-08-08, F2.5.2b). Until today this script classified the human's
answer correctly and then THREW IT AWAY -- it printed the verdict and exited. Nine forks across the six
phase drivers, and no record that any of them ever fired. That made every phase's "done" the model's own
word, which is the LAW 3 failure the artifact floor exists to close. The human's raw answer is the ONE
trace in this whole chain that the model cannot produce by itself, so it is the thing worth keeping.

⛔ AND WHY A FAILED LEDGER WRITE IS ITS OWN EXIT CODE, NOT A WARNING. "The human decided, but nothing
recorded it" is exactly the state this build exists to prevent, so it must never be spelled the same way
as a clean pass -- LAW 1, the same reason NO_OUTCOME exists. It is exit 3 rather than exit 2 because a
caller must be able to tell "re-ask the human" (2) from "do not re-ask; the answer was good, the DISK
failed" (3). Collapsing them would make a storage fault look like an undecided human.

Python 3.9-compatible on purpose: /usr/bin/python3 on macOS is 3.9, and that is the interpreter
cron and the harness actually invoke. No `X | None` annotations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time

# The closed vocabulary. Three members, and the third is the one that makes the other two safe.
KEEP_REFINING = "A"
LOCK_AND_MOVE_ON = "B"
NO_OUTCOME = "NO_OUTCOME"
MEMBERS = (KEEP_REFINING, LOCK_AND_MOVE_ON, NO_OUTCOME)

# Exit codes. Three outcomes, and the third is new: a decision that could not be recorded.
EXIT_DECIDED = 0
EXIT_NO_OUTCOME = 2
EXIT_NOT_RECORDED = 3

# The raw answer is kept VERBATIM -- it is the independent trace. Capped only so a paste of a whole
# document cannot bloat the ledger; the cap is recorded on the row so a truncation is never silent.
_RAW_CAP = 500

# What a human actually types when they mean A or B. Deliberately narrow: every phrase here is
# unambiguous on its own. Anything that needs interpretation belongs in NO_OUTCOME, not here.
_A_FORMS = {
    "a", "a)", "a.", "(a)", "a:", "-a",
    "keep refining", "keep refining this", "refine", "refine it", "refine more",
    "keep going", "more", "again", "not yet",
}
_B_FORMS = {
    "b", "b)", "b.", "(b)", "b:", "-b",
    "lock it", "lock it and move on", "lock", "move on", "next", "next phase",
    "good enough", "approved", "approve", "proceed", "go",
}

# Strip only decoration a human might type around their answer. NOT a general cleanup — the more this
# normalises, the more it starts interpreting, and interpreting is the failure mode.
_DECORATION = re.compile(r"^[\s\"'`*_]+|[\s\"'`*_!.]+$")


def classify(raw):
    # type: (object) -> str
    """Return exactly one member of MEMBERS. Never raises, never guesses."""
    if raw is None:
        return NO_OUTCOME
    if not isinstance(raw, str):
        return NO_OUTCOME

    answer = _DECORATION.sub("", raw).strip().lower()
    if not answer:
        return NO_OUTCOME

    # Exact membership only. A sentence that CONTAINS "a" is not an A answer — that substring trap is
    # a real logged failure in this system (a status gate read "READY" inside "NOT READY" and let a
    # wrong billing statement out the door).
    if answer in _A_FORMS:
        return KEEP_REFINING
    if answer in _B_FORMS:
        return LOCK_AND_MOVE_ON

    # Anything else: the human said something, but not one of the two things this turn can act on.
    return NO_OUTCOME


# ── the decision ledger ────────────────────────────────────────────────────────────────────────────
# Append-only JSONL, one row per fork fired. Deliberately NOT a second copy of save_step_ledger.py:
# that tool is hardcoded to /save in five places (RUN_DIR, its MANDATORY step list, two archive
# filename patterns, --pad-had-content). What is REUSED here is its PATTERN, which is the part that
# matters -- a stamp is CAUSED, not GENERATED, and freshness is proven by an epoch comparison against
# the run's own start rather than trusted. Same idea, own store, no second ledger for /save.


def _session_key():
    # type: () -> str
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if sid:
        return "sess-" + sid
    return "cwd-" + hashlib.sha1(os.getcwd().encode("utf-8")).hexdigest()[:12]


def default_ledger():
    # type: () -> str
    return os.path.join(os.path.expanduser("~"), ".claude", "run", "skill-builder",
                        "decisions-%s.jsonl" % _session_key())


def append_row(ledger, verdict, raw, phase=None, step=None):
    # type: (str, str, object, object, object) -> bool
    """Append one decision. Returns True on success, False on ANY failure -- never raises, because a
    storage fault must not be able to crash a human's turn. The caller turns False into exit 3."""
    text = raw if isinstance(raw, str) else repr(raw)
    row = {
        "ts": int(time.time()),
        "phase": phase,
        "step": step,
        "verdict": verdict,
        "raw": text[:_RAW_CAP],
        "raw_truncated": len(text) > _RAW_CAP,
        "session": os.environ.get("CLAUDE_CODE_SESSION_ID", ""),
    }
    try:
        os.makedirs(os.path.dirname(ledger), exist_ok=True)
        with open(ledger, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return True
    except (OSError, TypeError, ValueError):
        return False


def read_rows(ledger):
    # type: (str) -> list
    """Every parseable row. A corrupt line is SKIPPED, never guessed at -- and because verify below
    demands a positive match, skipping can only ever make verify stricter, never laxer."""
    rows = []
    try:
        with open(ledger, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return []
    return rows


def verify_row(ledger, phase, step, since=None):
    # type: (str, object, object, object) -> tuple
    """Is there a real, fresh decision for this fork? Returns (ok, message).

    FAIL-CLOSED in every direction: no file, no matching row, or a row that predates `since` all
    return False. `since` is the run's own start epoch -- the save_step_ledger rule, which exists so a
    row inherited from a PRIOR session cannot be read as evidence that THIS run asked the human.
    """
    rows = [r for r in read_rows(ledger)
            if str(r.get("phase")) == str(phase) and str(r.get("step")) == str(step)]
    if not rows:
        return False, ("no decision recorded for phase %s step %s in %s -- the fork never fired, or "
                       "fired without being recorded" % (phase, step, ledger))
    rows.sort(key=lambda r: r.get("ts", 0))
    newest = rows[-1]
    if newest.get("verdict") not in (KEEP_REFINING, LOCK_AND_MOVE_ON):
        return False, ("newest decision for phase %s step %s is %r -- not a decision"
                       % (phase, step, newest.get("verdict")))
    if since is not None:
        # `<` not `<=` on purpose, matching save_step_ledger.py's own documented reasoning: a row can
        # legitimately land in the SAME SECOND as the run's start, and a same-second row cannot be a
        # stale inheritance -- a prior session's row is seconds to days older.
        if int(newest.get("ts", 0)) < int(since):
            return False, ("newest decision for phase %s step %s (ts %s) PREDATES this run's start "
                           "(%s) -- a stale row inherited from a prior session is not evidence that "
                           "THIS run asked the human" % (phase, step, newest.get("ts"), since))
    return True, "decision %s recorded for phase %s step %s at ts %s" % (
        newest.get("verdict"), phase, step, newest.get("ts"))


# ── the two-sided self-test ────────────────────────────────────────────────────────────────────────
# The parts library's own law: A GATE THAT FAILS OPEN IS WORSE THAN NO GATE, BECAUSE YOU TRUST IT.
# So this proves BOTH directions — it accepts real answers AND refuses known-bad ones. A test that only
# proves the happy path proves nothing about the only path that matters.

_MUST_ACCEPT_A = ["A", "a", " a ", "A)", "(a)", "keep refining", "Keep Refining This", "not yet", "*a*"]
_MUST_ACCEPT_B = ["B", "b", "B.", "lock it and move on", "Move on", "good enough", "go", '"b"']
_MUST_REFUSE = [
    "",                       # said nothing
    "   ",                    # said nothing, with whitespace
    None,                     # no answer object at all
    "C",                      # a third option that does not exist
    "D — none of these",      # invented an option
    "I think A is probably right but maybe B?",   # ambiguous: contains both letters
    "Actually, hold on",      # a real sentence that is not a decision
    "yes",                    # agreement with WHAT? the classic non-answer
    "no",                     # refusal of WHAT?
    "ok",                     # the most dangerous one: reads as consent, decides nothing
    "a bit more work please", # CONTAINS "a" — the substring trap
    "maybe",
    "1",
    42,                       # not even a string
]


def _ledger_selftest(failures):
    # type: (list) -> int
    """Prove the LEDGER both directions too. The parts-library law applies to the new half exactly as
    it applied to the old one: a gate that fails open is worse than no gate, because you trust it."""
    import tempfile
    checks = 0
    tmp = tempfile.mkdtemp(prefix="fork-ledger-selftest-")
    led = os.path.join(tmp, "decisions.jsonl")

    # 1. a real write lands and is readable back
    checks += 1
    if not append_row(led, LOCK_AND_MOVE_ON, "b", phase=2, step="2.6"):
        failures.append("LEDGER write failed on a writable path")
    elif len(read_rows(led)) != 1:
        failures.append("LEDGER read-back did not return the row just written")

    # 2. verify FINDS a real row
    checks += 1
    ok, msg = verify_row(led, 2, "2.6")
    if not ok:
        failures.append("LEDGER verify missed a row that exists: %s" % msg)

    # 3. verify REFUSES a fork that never fired  ← the direction that matters
    checks += 1
    ok, _ = verify_row(led, 4, "4.8")
    if ok:
        failures.append("LEDGER verify PASSED a phase/step with no row — fails open")

    # 4. verify REFUSES a stale row (predates this run's start)
    checks += 1
    ok, _ = verify_row(led, 2, "2.6", since=int(time.time()) + 60)
    if ok:
        failures.append("LEDGER verify PASSED a row that predates the run start — stale-row fail-open")

    # 5. verify REFUSES when the recorded verdict is a non-decision
    checks += 1
    led2 = os.path.join(tmp, "no-outcome.jsonl")
    append_row(led2, NO_OUTCOME, "ok", phase=5, step="5.4")
    ok, _ = verify_row(led2, 5, "5.4")
    if ok:
        failures.append("LEDGER verify read a NO_OUTCOME row as a decision")

    # 6. an UNWRITABLE ledger reports failure rather than pretending to have written
    checks += 1
    if append_row(os.path.join(os.devnull, "cannot", "exist.jsonl"), "B", "b", 1, "1.1"):
        failures.append("LEDGER claimed success writing to an impossible path")

    # 7. a corrupt line is skipped, not guessed at
    checks += 1
    with open(led, "a", encoding="utf-8") as fh:
        fh.write("{this is not json\n")
    if len(read_rows(led)) != 1:
        failures.append("LEDGER did not skip a corrupt line cleanly")

    return checks


def selftest():
    # type: () -> int
    failures = []

    for good in _MUST_ACCEPT_A:
        got = classify(good)
        if got != KEEP_REFINING:
            failures.append("ACCEPT-A failed: %r -> %s (expected A)" % (good, got))

    for good in _MUST_ACCEPT_B:
        got = classify(good)
        if got != LOCK_AND_MOVE_ON:
            failures.append("ACCEPT-B failed: %r -> %s (expected B)" % (good, got))

    for bad in _MUST_REFUSE:
        got = classify(bad)
        if got != NO_OUTCOME:
            failures.append("REFUSE failed: %r -> %s (expected NO_OUTCOME)" % (bad, got))

    ledger_checks = _ledger_selftest(failures)

    classify_total = len(_MUST_ACCEPT_A) + len(_MUST_ACCEPT_B) + len(_MUST_REFUSE)
    total = classify_total + ledger_checks
    print("fork.py self-test — %d cases (%d accept-A, %d accept-B, %d must-refuse, %d ledger)"
          % (total, len(_MUST_ACCEPT_A), len(_MUST_ACCEPT_B), len(_MUST_REFUSE), ledger_checks))
    if failures:
        print("FAILED — %d case(s):" % len(failures))
        for f in failures:
            print("  - " + f)
        return 1
    print("PASS — it accepts every real answer AND refuses every known-bad one,")
    print("       AND the ledger records a real decision AND refuses a missing, stale,")
    print("       or non-decision row. Both directions proven on both halves.")
    return 0


def main(argv):
    # type: (list) -> int
    if len(argv) == 2 and argv[1] == "--selftest":
        return selftest()

    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("answer", nargs="?")
    ap.add_argument("--phase")
    ap.add_argument("--step")
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--since", type=int, default=None)
    ap.add_argument("--verify", action="store_true")
    try:
        a = ap.parse_args(argv[1:])
    except SystemExit:
        print("usage: fork.py \"<answer>\" [--phase N] [--step S]   |   "
              "fork.py --verify --phase N --step S [--since EPOCH]   |   fork.py --selftest",
              file=sys.stderr)
        return EXIT_NO_OUTCOME

    ledger = a.ledger or default_ledger()

    if a.verify:
        if a.phase is None or a.step is None:
            print("--verify needs --phase and --step", file=sys.stderr)
            return EXIT_NO_OUTCOME
        ok, msg = verify_row(ledger, a.phase, a.step, a.since)
        print(msg)
        return EXIT_DECIDED if ok else EXIT_NO_OUTCOME

    if a.answer is None:
        print("usage: fork.py \"<the human's answer>\"   |   fork.py --selftest", file=sys.stderr)
        return EXIT_NO_OUTCOME

    verdict = classify(a.answer)
    print(verdict)

    # The row is written for EVERY outcome, including NO_OUTCOME. A refused answer is evidence too —
    # it is how "we asked and they did not decide" stays distinguishable from "we never asked."
    recorded = append_row(ledger, verdict, a.answer, a.phase, a.step)

    if verdict == NO_OUTCOME:
        # Non-zero on purpose. A caller that ignores stdout still cannot read a non-decision as
        # consent — it has to stop and re-ask, which is exactly what the spec's forks require.
        print("The answer was neither A nor B. Do NOT proceed — re-ask the human.", file=sys.stderr)
        return EXIT_NO_OUTCOME

    if not recorded:
        print("DECIDED BUT NOT RECORDED: the answer was %s, but the decision ledger at %s could not "
              "be written. Do NOT close this phase on it — an unrecorded decision is exactly the "
              "state the artifact floor exists to prevent. Fix the path and re-ask, or record it by "
              "hand." % (verdict, ledger), file=sys.stderr)
        return EXIT_NOT_RECORDED

    return EXIT_DECIDED


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    sys.exit(main(sys.argv))
