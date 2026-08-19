#!/usr/bin/env python3
"""Record guard-fire-test PRODUCER LIVENESS into the machine-local fault ledger — NOT the
guard-test VERDICT (PORTED 2026-08-14 from claudeops-config's
system/tools/guard_fire_test_record.py).

Split out of guard-fire-test-run.sh rather than inlined as a heredoc: the runner is built
from a subsystem jig, and an embedded heredoc makes the shell body harder to lint and
collides with generator heredocs. One job, deterministic, no LLM.

WHAT THIS DOES AND DOES NOT RECORD. The ACTUAL fire-test verdict (RED/GREEN, which guard,
the raw output) goes ONLY through `emit_finding.py` (called from `guard-fire-test-run.sh`'s
`do_work()`, via its CLI — see that script). This module's only job is the ORTHOGONAL
question `fault_ledger`'s `producers` dict is FOR: did the guard-fire-test PRODUCER itself
complete a run. Reaching this line already proves that (the caller's "verify-hooks itself
FAILED to run" branch returns BEFORE calling this script at all), so the recorded rc is
always 0. No arguments are read; any passed are ignored (tolerant of a stale caller).

WHY THIS SPLIT MATTERS (kept from the donor, because the failure mode it documents is
general, not specific to that system): a RED verdict — a real found-result, "a guard
downgraded" — must never be smuggled through the SAME field `fault_ledger.failed_producers()`
uses to mean "this producer's script crashed / its tile is not being refreshed". Conflating
a detector's finding with a producer-liveness channel makes a health sweep render a message
that is LITERALLY WRONG for a downgrade (the script ran fine; a guard just downgraded). That
conflation is exactly the "fault schema in disguise" Hospital's `emit_finding.py` exists to
end — kept as a live design note here since this file is the other half of the fix.

Exit 0 = producer-liveness recorded. Exit 3 = the ledger could NOT be written, which the
runner treats as a broken tool — a liveness signal nobody can read is no signal at all.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import fault_ledger as FL  # noqa: E402


def main():
    d = FL.load()
    FL.note_producer(d, "guard-fire-test", 0, time.time(), "")
    if not FL.save(d):
        sys.stderr.write("[guard-fire-test] FATAL: fault ledger could not be written — the "
                         "producer-liveness signal would be invisible. Failing loudly, not "
                         "reporting a silent pass.\n")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
