#!/usr/bin/env bash
# run_selftests.sh — the shipping lane's gate.
#
# WHY THIS EXISTS SEPARATELY FROM THE REPO'S TEST SWEEP. The lane's modules carry their
# proofs as `--selftest`, not as `test_*.py`, so the repo-wide sweep for test files walks
# straight past all five of them and reports a green count that never included the lane.
# A tested thing nobody runs is an untested thing with a good reputation.
#
# Every module here must pass its own two-sided self-test, and the rule sets must pass
# `verify_rules.py`, which proves the rules against planted fixtures via the real engine
# rather than by reading them.
#
# Exit 0 only if everything passes. Any failure, or any module that exposes no --selftest,
# fails the gate — a module that cannot prove itself is a finding, not a pass.
#
# Usage:  bash system/shipping-lane/run_selftests.sh
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
PASS=0; FAIL=0; MISSING=0; TOTAL=0
FAILED=""

echo "═══ shipping lane self-test gate ═══"
echo

for f in "$HERE"/*.py; do
  name="$(basename "$f")"
  # verify_rules.py IS a proof, not a thing that needs one — it is run on its own below.
  # Asking it for a --selftest would be asking a test to test itself.
  [ "$name" = "verify_rules.py" ] && continue
  if ! grep -q -- "--selftest" "$f"; then
    echo "  ✘ $name — exposes NO --selftest (a module in this lane must prove itself)"
    MISSING=$((MISSING + 1)); FAILED="$FAILED $name(no-selftest)"
    continue
  fi
  if out="$(python3 "$f" --selftest 2>&1)"; then
    n="$(printf '%s' "$out" | grep -c '\[PASS\]')"
    echo "  ✔ $name — $n checks"
    PASS=$((PASS + 1)); TOTAL=$((TOTAL + n))
  else
    echo "  ✘ $name — SELFTEST FAILED"
    printf '%s\n' "$out" | grep '\[FAIL\]' | sed 's/^/      /'
    FAIL=$((FAIL + 1)); FAILED="$FAILED $name"
  fi
done

echo
# The rule sets are not a module and cannot self-test; verify_rules.py is their proof, and
# it composes the personal tier from the lane's own invented identity fixture so this runs
# identically on every machine and involves nobody's real identity.
if out="$(python3 "$HERE/verify_rules.py" 2>&1)"; then
  n="$(printf '%s' "$out" | grep -c '\[PASS\]')"
  echo "  ✔ rule sets — $n checks (verify_rules.py, against the planted fixtures)"
  TOTAL=$((TOTAL + n))
else
  echo "  ✘ rule sets — verify_rules.py FAILED"
  printf '%s\n' "$out" | grep -E '\[FAIL\]|CANNOT EVALUATE' | sed 's/^/      /'
  FAIL=$((FAIL + 1)); FAILED="$FAILED verify_rules"
fi

echo
echo "─────────────────────────────────────"
echo "modules passing: $PASS · failing: $FAIL · without a self-test: $MISSING · checks: $TOTAL"
if [ "$FAIL" -eq 0 ] && [ "$MISSING" -eq 0 ]; then
  echo "GATE: PASS — every module proved itself on both sides, and the rules were verified."
  exit 0
fi
echo "GATE: FAIL —$FAILED"
exit 1
