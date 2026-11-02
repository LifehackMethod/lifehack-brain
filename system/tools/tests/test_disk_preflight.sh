#!/usr/bin/env bash
# test_disk_preflight.sh -- shared/disk_preflight.py and every runner wired to it: with the threshold forced ABOVE the
# free space they refuse with the named message before doing any work; with a low threshold they proceed.
# Run: bash system/tools/tests/test_disk_preflight.sh
set -u
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
PY="${PY:-/usr/bin/python3}"
T="$(mktemp -d "${TMPDIR:-/tmp}/disk-preflight-test.XXXXXX")" || { echo "FAIL: mktemp"; exit 1; }
trap 'rm -rf "$T"' EXIT
pass=0; fail=0
ok() { pass=$((pass+1)); echo "   ok   $1"; }
no() { fail=$((fail+1)); echo "  FAIL  $1"; }
MSG='^REFUSED: only [0-9]+\.[0-9] GB free on .+ \(need 999999 GB\): free disk space first\.$'

refuses() {  # refuses <label> <cmd...> : forced-high threshold -> non-zero exit and the REFUSED line
  local label="$1"; shift
  LH_DISK_MIN_GB=999999 "$@" >"$T/out" 2>&1; local rc=$?
  if [ "$rc" -ne 0 ] && grep -Eq "$MSG" "$T/out"; then ok "$label refuses (exit $rc) with the named message"
  else no "$label: expected refusal + message, got exit $rc: $(head -c 400 "$T/out")"; fi
}

# 1. the helper itself
refuses "disk_preflight.py" "$PY" "$REPO/shared/disk_preflight.py" "$T"
LH_DISK_MIN_GB=999999 "$PY" "$REPO/shared/disk_preflight.py" >/dev/null 2>&1; [ $? -eq 3 ] && ok "refusal exit code is 3" || no "refusal exit code is not 3"
LH_DISK_MIN_GB=0.01 "$PY" "$REPO/shared/disk_preflight.py" "$T" >"$T/out" 2>&1 && [ ! -s "$T/out" ] && ok "low threshold: proceeds silently (exit 0)" || no "low threshold did not proceed: $(cat "$T/out")"
LH_DISK_MIN_GB=999999 "$PY" -c "import sys; sys.path.insert(0, '$REPO/shared'); import disk_preflight as d; m = d.check(); sys.exit(0 if m and m.startswith('REFUSED: only ') else 1)" && ok "library check() returns the REFUSED line" || no "library check()"
LH_DISK_MIN_GB=0.01 "$PY" -c "import sys; sys.path.insert(0, '$REPO/shared'); import disk_preflight as d; sys.exit(0 if d.check(['$T']) is None else 1)" && ok "library check() returns None when there is room" || no "library check() with room"

# 2. every runner refuses before doing any work (none of these reaches a session, a clone or a test)
refuses "run-all-tests.sh" bash "$REPO/system/tools/run-all-tests.sh"
grep -q 'aggregate test gate' "$T/out" && no "run-all-tests.sh started the suite despite refusing" || ok "run-all-tests.sh ran no test"
refuses "test_rig_selftest.sh" bash "$REPO/system/hooks/tests/test_rig_selftest.sh"
refuses "rig_run.py" "$PY" "$REPO/system/tools/rig/rig_run.py" --no-write
refuses "rig_meal.py run" "$PY" "$REPO/system/tools/rig/rig_meal.py" run --modes jobdoor --only zz-no-such-case
refuses "rig_live_free.py run" "$PY" "$REPO/system/tools/rig/rig_live_free.py" run --cases "$T/none.jsonl" --label zz --scratch "$T"
refuses "rig_canary_live.py run" "$PY" "$REPO/system/tools/rig/rig_canary_live.py" run

# 3. with a normal-or-lower threshold the runners proceed past the preflight
LH_DISK_MIN_GB=0.01 bash "$REPO/system/tools/run-all-tests.sh" --list >/dev/null 2>&1 && ok "run-all-tests.sh --list unaffected" || no "run-all-tests.sh --list"
: > "$T/empty.jsonl"   # an empty case file: the runner gets past the preflight and stops at "no replay cases" (cheap, no suite)
LH_DISK_MIN_GB=0.01 "$PY" "$REPO/system/tools/rig/rig_run.py" --cases "$T/empty.jsonl" --no-write >"$T/out" 2>&1
grep -q 'no replay cases found' "$T/out" && ! grep -q REFUSED "$T/out" && ok "rig_run.py proceeds past the preflight with room" || no "rig_run.py with room: $(tail -c 400 "$T/out")"

echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
