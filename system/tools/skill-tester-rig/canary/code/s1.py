#!/usr/bin/env python3
"""s1 (code): plant the run — token_1, value_1 and the five telephone facts, all from CANARY_SEED.
usage: CANARY_SEED=S python3 canary/code/s1.py RUN_DIR      (idempotent: temp file + rename)"""
import sys
from _common import expected, seed

expected.write_step(sys.argv[1], expected.record1(seed()))
print("s1 planted")
