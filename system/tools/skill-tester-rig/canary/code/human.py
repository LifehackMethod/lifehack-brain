#!/usr/bin/env python3
"""human steps (s4, s9): the RUNNER calls this after it receives --answer for a waiting human step.
usage: CANARY_SEED=S python3 canary/code/human.py RUN_DIR N ANSWER
Writes step-N.json = formula from step-(N-1).json + token_N + "answer". ANSWER must be exactly yes|no
(lowercase, no whitespace); anything else exits 3 and writes NOTHING (off-menu — F-M3).
A "no" IS written (exit 0); it is the human check that refuses to carry on past a "no"."""
import sys
from _common import expected, read_prev, seed

run_dir, n, ans = sys.argv[1], int(sys.argv[2]), sys.argv[3]
if expected.kinds().get(n) != "human":
    sys.exit("human.py: s%d is not a human step" % n)
if ans not in expected.MENU:
    print("human.py: OFF-MENU answer %r for s%d (menu: yes/no) — nothing written" % (ans, n), file=sys.stderr)
    sys.exit(3)
expected.write_step(run_dir, expected.record_from_prev(n, read_prev(run_dir, n), expected.token(seed(), n), ans))
print("s%d answered %s" % (n, ans))
