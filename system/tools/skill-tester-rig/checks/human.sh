#!/bin/bash
# checks/human.sh RUN_DIR N [CANDIDATE] — content check for a human step (s4 s9); also fails on answer "no" or off-menu.
# Card form: bash checks/human.sh "$RUN_DIR" N   (cwd = rig root, CANARY_SEED in env).
# CANDIDATE (optional) = the file to check, default RUN_DIR/step-N.json; the runner passes its temp file so it can
# check BEFORE renaming into step-N.json. Exit 0 PASS · 1 FAIL (one-line reason) · 4 CANNOT-READ. See _check.py.
. "$(dirname "${BASH_SOURCE[0]}")/_lib.sh" 2>/dev/null || { printf 'CANNOT-READ\n  checks/_lib.sh missing\n'; exit 4; }
run_check human "$@"
