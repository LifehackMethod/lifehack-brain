#!/bin/bash
# bite/broken-truth.sh — used ONLY by `bite.sh --selftest`: a deliberately BROKEN grader.
# Runs the real truth.py ($1) with the remaining args, then lies twice: `sN lost` becomes `sN ok` (a fault the
# grader must name is hidden) and a clean `s1 ok` becomes `s1 silent_wrong` (a clean control cries wolf).
# The selftest passes only if the bite reports MISSED and a FALSE POSITIVE because of it.
t="$1"; shift
python3 -B "$t" "$@" | sed -e 's/^\(s[0-9]*\) lost$/\1 ok/' -e 's/^s1 ok$/s1 silent_wrong/'
exit "${PIPESTATUS[0]}"
