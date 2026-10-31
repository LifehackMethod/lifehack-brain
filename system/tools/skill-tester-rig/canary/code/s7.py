#!/usr/bin/env python3
"""s7 (code): step-7.json from step-6.json by the formula; token_7 from CANARY_SEED; facts copied.
usage: CANARY_SEED=S python3 canary/code/s7.py RUN_DIR      (idempotent: temp file + rename)"""
import sys
from _common import expected, read_prev, seed

N = 7
expected.write_step(sys.argv[1], expected.record_from_prev(N, read_prev(sys.argv[1], N), expected.token(seed(), N)))
print("s7 done")
