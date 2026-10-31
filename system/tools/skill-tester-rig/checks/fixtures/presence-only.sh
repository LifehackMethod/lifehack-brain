#!/bin/bash
# fixtures/presence-only.sh — a DELIBERATELY WEAK check (failure matrix F-13). NEVER wire this into a card.
# It only tests that the file exists and is non-empty: the exact shape of the October rig's 8 silent_wrong.
# It is shipped so checks/selftest.sh can prove, every run, that its judge REFUSES a presence-only check
# (it passes the bad fixtures, so the judge must reject it). Same interface as the real checks.
f="${3:-$1/step-$2.json}"
[ -s "$f" ]
