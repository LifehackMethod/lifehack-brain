#!/usr/bin/env bash
# run_selftests.sh — the parts-library gate.
#
# Every part in this directory must pass its own two-sided self-test. A part without a
# passing self-test is NOT trusted and does not count as built (SOP §II.4: a gate that
# fails open is worse than no gate, because you trust it).
#
# Exit 0 only if every part passes. Any failure, or any part that exposes no --selftest,
# fails the gate — a part that cannot prove itself is a finding, not a pass.
#
# Usage:  bash system/parts/run_selftests.sh
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
PASS=0; FAIL=0; MISSING=0
FAILED_PARTS=""

echo "═══ parts library self-test gate ═══"
echo

for f in "$HERE"/*.py; do
  name="$(basename "$f")"
  if ! grep -q -- "--selftest" "$f"; then
    echo "  ✘ $name — exposes NO --selftest (a part must be able to prove itself)"
    MISSING=$((MISSING + 1)); FAILED_PARTS="$FAILED_PARTS $name(no-selftest)"
    continue
  fi
  if out="$(python3 "$f" --selftest 2>&1)"; then
    n="$(printf '%s' "$out" | grep -c '\[PASS\]')"
    echo "  ✔ $name — $n checks"
    PASS=$((PASS + 1))
  else
    echo "  ✘ $name — SELFTEST FAILED"
    printf '%s\n' "$out" | grep '\[FAIL\]' | sed 's/^/      /'
    FAIL=$((FAIL + 1)); FAILED_PARTS="$FAILED_PARTS $name"
  fi
done

echo
# ── IS ANYTHING HERE BUILT BUT UNREACHABLE? ───────────────────────────────────────────
#
# A part that passes its own self-test and is called by nothing is still dead weight — it
# enforces nothing. The lesson is a measured one: two parts were once built, verified, and
# recorded as unblocking a phase while being invisible to their caller the whole time,
# because building a part and WIRING it are two different acts and only the first was done.
#
# ⚠ THE CHECK CHANGED SHAPE WHEN THIS LIBRARY MOVED, AND THAT IS STATED RATHER THAN HIDDEN.
# It used to ask a central router (`system/factory/route_to_part.py`) whether it could name
# every part. That router is not in this repo and is not coming: these parts are invoked
# directly, by name, as subprocesses of the shipping-lane scripts. Ported unchanged, the
# check fails to import the router, correctly refuses to call unknown coverage a pass, and
# so the gate FAILS FOREVER — a check that can only ever report failure gets deleted, and
# then the question stops being asked at all.
#
# So it asks the same question against how this repo actually works: is each part named by
# at least one file OUTSIDE this directory? That is exactly what "wired" means here.
#
# SHIPPING A PART IS NOT WIRING IT.
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
ORPHANS=""
for f in "$HERE"/*.py; do
  name="$(basename "$f" .py)"
  if ! grep -rqI --exclude-dir=.git --exclude-dir=parts -- "$name" "$REPO_ROOT" 2>/dev/null; then
    ORPHANS="$ORPHANS $name"
  fi
done
ORPHAN_FAIL=0
if [ -n "$ORPHANS" ]; then
  echo "  ✘ reachability — BUILT BUT CALLED BY NOTHING:$ORPHANS"
  echo "      these parts exist and enforce NOTHING — no file outside system/parts/ names them."
  ORPHAN_FAIL=1
else
  echo "  ✔ reachability — every part is named by a caller outside system/parts/"
fi

echo
echo "─────────────────────────────────────"
echo "parts passing: $PASS · failing: $FAIL · without a self-test: $MISSING"
if [ "$FAIL" -eq 0 ] && [ "$MISSING" -eq 0 ] && [ "$ORPHAN_FAIL" -eq 0 ]; then
  echo "GATE: PASS — every part proved itself on both sides, and every part is reachable."
  exit 0
fi
[ "$ORPHAN_FAIL" -eq 1 ] && FAILED_PARTS="$FAILED_PARTS reachability"
echo "GATE: FAIL —$FAILED_PARTS"
exit 1
