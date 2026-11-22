#!/usr/bin/env bash
# test_planning_desk_checks.sh — CR-9 step 6c: the planning desk component's four checks,
# tested against the REAL repo.
# What it proves: each check's --selftest exits 0 (a planted fault bites BY NAME — the
# selftest's own exit code carries that) · a real smoke run of the door-rows check against
# the plugin's manifest runs to a verdict (a FAIL there is a FINDING, not a test failure —
# the smoke run only proves the probes RAN) · no file in the repo is changed by the runs.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CHECKS="$ROOT/system/tools/organism/checks"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
FAIL=0
ok() { echo "ok $1"; }
bad() { echo "FAIL $1"; FAIL=1; }

for c in planning_door_rows_check planning_guard_tests_check planning_data_path_check planning_weekly_receipt_check; do
  [ -f "$CHECKS/$c.py" ] || { bad "check script missing: $c"; continue; }
  if python3 "$CHECKS/$c.py" --selftest > "$T/$c.out" 2>&1; then
    ok "$c selftest exits 0"
  else
    bad "$c selftest exits non-zero (a planted fault DID-NOT-BITE?)"; cat "$T/$c.out"
  fi
  grep -q "DID-NOT-BITE" "$T/$c.out" && bad "$c selftest output names a DID-NOT-BITE" || ok "$c: every planted fault bites"
done

# smoke run of the door-rows check against the plugin's own manifest — verdict recorded,
# not judged here (a FAIL is a finding for the page's delta reading)
python3 "$CHECKS/planning_door_rows_check.py" --out "$T/smoke-tile.json" > "$T/smoke.out" 2>&1
grep -q "door-row:calendar-store-sync" "$T/smoke.out" && ok "door-rows smoke run probes all rows" || bad "door-rows smoke run did not probe the rows"
grep -q "receipt:" "$T/smoke.out" && ok "door-rows smoke run wrote a receipt" || bad "no receipt from smoke run"

# the repo is unchanged by the runs
if git -C "$ROOT" status --porcelain | grep -v -E '^([??A]|AM|M)  system/(tools/organism/checks/planning_(door_rows|guard_tests|data_path|weekly_receipt)_check\.py|tools/tests/test_planning_desk_checks\.sh|canon/components/planning-desk\.md)$' > "$T/dirty.out"; then
  [ -s "$T/dirty.out" ] && { bad "the runs changed files outside the new-file set:"; cat "$T/dirty.out"; } || ok "repo unchanged outside the new-file set"
else
  ok "repo unchanged outside the new-file set"
fi

if [ "$FAIL" -eq 0 ]; then echo "ALL PASS"; else echo "FAILURES PRESENT"; fi
exit "$FAIL"
