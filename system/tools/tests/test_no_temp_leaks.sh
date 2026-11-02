#!/usr/bin/env bash
# test_no_temp_leaks.sh -- regression test: the tests that used to leak temp dirs into $TMPDIR leave nothing behind.
#
# WHY: on 2026-11-01 leaked test temp dirs (chk2-* x1820, lifehack-scanev-* x700, no-upstream-test.* x648, chk1-* x594,
# safe-sheets-* x531, refresh-clone-* x232 at 50-60 MB each, tmp.* x622 ...) filled the Mac's disk. Each leaker now
# cleans up (trap / addCleanup / TemporaryDirectory / finally). This runs a representative subset of them and asserts
# that no new entry with a leaker prefix remains.
#
# The children run with a PRIVATE $TMPDIR (made inside the real one, removed on exit): other windows' suites write the
# same prefixes into the shared $TMPDIR at the same time, and a shared snapshot would blame this run for their files.
# Run: bash system/tools/tests/test_no_temp_leaks.sh
set -u
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
PY="${PY:-/usr/bin/python3}"
PRIV="$(mktemp -d "${TMPDIR:-/tmp}/no-temp-leaks.XXXXXX")" || { echo "FAIL: mktemp"; exit 1; }
trap 'rm -rf "$PRIV"' EXIT
ROOT="$PRIV/.lhroot"; mkdir -p "$ROOT/config"; printf 'zz-no-temp-leaks-fixture-term\n' > "$ROOT/config/ship-identity.md"
LOGS="$PRIV/.logs"; mkdir -p "$LOGS"

PREFIXES="chk2- chk1- lifehack-scanev- no-upstream-test safe-sheets- refresh-clone- rigmeal- riglive- tmp"
snapshot() {  # every entry directly in $PRIV whose name starts with a leaker prefix, sorted
  local p
  for p in $PREFIXES; do find "$PRIV" -mindepth 1 -maxdepth 1 -name "${p}*" 2>/dev/null; done | sort
}

SUBSET=(
  system/githooks/tests/test_check_connected.py
  system/githooks/tests/test_check_hides_failure.py
  system/tools/cowork-ingest/test_scan_evidence.py
  system/tools/test_safe_sheets.py
  system/hooks/tests/test_no_upstream_commit_signpost.sh
  system/hooks/tests/test_hook_sop_read_fail_closed.sh
  system/hooks/tests/test_drive_destructive_guard.sh
)

before="$(snapshot)"
fail=0
for rel in "${SUBSET[@]}"; do
  case "$rel" in *.py) cmd=("$PY" "$REPO/$rel") ;; *) cmd=(bash "$REPO/$rel") ;; esac
  log="$LOGS/$(echo "$rel" | tr '/' '_').log"
  ( cd "$REPO" && TMPDIR="$PRIV/" LIFEHACK_ROOT="$ROOT" "${cmd[@]}" >"$log" 2>&1 )
  rc=$?
  # the child's own pass/fail is the suite's business, not this test's; a crash still has to clean up
  echo "   ran  $rel (exit $rc)"
done
after="$(snapshot)"
new="$(comm -13 <(printf '%s\n' "$before") <(printf '%s\n' "$after") | sed '/^$/d')"
if [ -n "$new" ]; then
  fail=1
  echo "  FAIL  leaked temp entries remain after the subset:"
  printf '%s\n' "$new" | sed "s|^$PRIV/|          |"
else
  echo "   ok   no new leaker-prefixed entries in TMPDIR after ${#SUBSET[@]} tests"
fi

# the check itself must be able to fail: plant one leaker-shaped dir and watch the snapshot see it
mkdir "$PRIV/chk2-planted"
if [ -n "$(comm -13 <(printf '%s\n' "$after") <(snapshot) | sed '/^$/d')" ]; then
  echo "   ok   a planted chk2-* dir is detected (the check can fail)"
else
  fail=1; echo "  FAIL  the snapshot did not see a planted chk2-* dir"
fi

[ "$fail" -eq 0 ] && { echo "ALL PASSED"; exit 0; }
exit 1
