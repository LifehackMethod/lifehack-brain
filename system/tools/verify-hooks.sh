#!/bin/bash
# verify-hooks.sh — HARD GUARD smoke test. Usage: verify-hooks.sh
#
# Ported (T9.5c, 2026-08-15): the donor kept no guard cases of its own here — it is a THIN
# RUNNER over system/tools/organism/label_manifest.yaml, the SINGLE SOURCE OF TRUTH that also
# computes the organism map's honesty labels, so a guard can never be "tested here" and
# "unverified on the map" at the same time. `guard-fire-test-run.sh` already exists in this
# repo and calls into this file; before this port it had nothing to call.
#
# ADD A NEW GUARD CASE -> edit system/tools/organism/label_manifest.yaml, NOT this file.

set -u

REPO="$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)"
CHECKER="$REPO/system/tools/organism/label_checker.py"
PY=/usr/bin/python3
RC=0

if [ "$#" -gt 0 ]; then
  echo "note: verify-hooks.sh takes no HOOKS_DIR arg — guard cases are declared in"
  echo "      system/tools/organism/label_manifest.yaml (repo-relative). Ignoring: $*"
  echo
fi

echo "=== verify-hooks — HARD GUARD smoke test (engine: label_manifest.yaml) ==="
if [ ! -f "$CHECKER" ]; then
  echo "  MISSING  label_checker.py — the fire-test engine is gone. FAILING CLOSED."
  echo "--- RESULT: RED ---"
  exit 1
fi

"$PY" "$CHECKER" check || RC=1

echo
# --- statusline TRUTH CONTRACT (kept NATIVE, deliberately) ------------------------
# Not a hook fire-test — a regression guard for the desk:-leaks-project-slug bug (T9.8a).
# Ported alongside this file; run here the same way the donor ran its own copy.
if [ -f "$REPO/system/tools/statusline-truth-test.sh" ]; then
  if bash "$REPO/system/tools/statusline-truth-test.sh" >/dev/null 2>&1; then
    printf "  PASS  %-28s %s\n" "statusline-truth-test.sh" "desk: is truthful (never a slug)"
  else
    printf "  FAIL  %-28s %s\n" "statusline-truth-test.sh" "desk: field lied — run it directly for detail"
    RC=1
  fi
else
  printf "  SKIP  %-28s %s\n" "statusline-truth-test.sh" "not present in this tree"
fi

# --- write-custody regression suite (kept NATIVE, deliberately) -------------------
# Covers guard_cross_project_write.sh in THIS repo (destination's write-custody suite;
# the donor split this test into three separate files — pm_hooks_test.sh, pm_lock_stress.sh,
# cross_project_write_test.sh — none of which were ported to this tree as of this port. Their
# subjects (pm_flag.sh, pm_persist.sh, guard_cross_project_write.sh) DO exist here; only their
# dedicated regression suites do not yet. Reported as NOT-PORTED below, honestly, rather than
# invented as a pass.
if [ -f "$REPO/system/hooks/tests/test_write_custody_guards.sh" ]; then
  if bash "$REPO/system/hooks/tests/test_write_custody_guards.sh" >/dev/null 2>&1; then
    printf "  PASS  %-28s %s\n" "test_write_custody_guards.sh" "write-custody guards incl. cross-project alarm: correct"
  else
    printf "  FAIL  %-28s %s\n" "test_write_custody_guards.sh" "write-custody regression — run it directly for detail"
    RC=1
  fi
else
  printf "  SKIP  %-28s %s\n" "test_write_custody_guards.sh" "not present in this tree"
fi

# --- project-arming lock + human-word override (native, 2026-08-15) ---------------
# WIRED IN HERE ON PURPOSE. A suite nobody runs is not a control, and this one covers the two
# claims that are expensive to be wrong about: a window cannot re-point itself, and the only
# thing that changes that is the person's own words. It counts toward RC.
if [ -f "$REPO/system/hooks/tests/test_pm_lock_override.sh" ]; then
  if bash "$REPO/system/hooks/tests/test_pm_lock_override.sh" >/dev/null 2>&1; then
    printf "  PASS  %-28s %s\n" "test_pm_lock_override.sh" "project lock holds; only the human's word moves it; flag TTL live"
  else
    printf "  FAIL  %-28s %s\n" "test_pm_lock_override.sh" "the project-arming lock misbehaved — run it directly for detail"
    RC=1
  fi
else
  printf "  SKIP  %-28s %s\n" "test_pm_lock_override.sh" "not present in this tree"
fi

# --- plan-arming lock + the SAME human-word override (native, 2026-08-15) ---------
# The other half of the same ruling ("this other project OR this other plan"). Wired in for the
# same reason as the block above, and it additionally proves plan_flag.sh consumes the pm store's
# grant rather than minting a parallel one — a second grant type would be a second thing to forge.
if [ -f "$REPO/system/hooks/tests/test_plan_lock_override.sh" ]; then
  if bash "$REPO/system/hooks/tests/test_plan_lock_override.sh" >/dev/null 2>&1; then
    printf "  PASS  %-28s %s\n" "test_plan_lock_override.sh" "plan lock holds; only the human's word moves it; one grant type"
  else
    printf "  FAIL  %-28s %s\n" "test_plan_lock_override.sh" "the plan-arming lock misbehaved — run it directly for detail"
    RC=1
  fi
else
  printf "  SKIP  %-28s %s\n" "test_plan_lock_override.sh" "not present in this tree"
fi

# --- STILL NOT PORTED, named rather than silently omitted. Does not count toward RC.
printf "  ????  %-28s %s\n" "pm_hooks_test.sh" "PARTLY COVERED — arm/TTL/lock now run above; the donor's INJECTION-FENCE cases (pm_persist.sh's doc-excerpt sanitising) are still unported"
printf "  ????  %-28s %s\n" "pm_lock_stress.sh" "NOT PORTED — the lock has correctness cases above but no concurrency stress test"

echo
if [ "$RC" -eq 0 ]; then
  echo "--- RESULT: GREEN — every hard guard fires correctly. ---"
  exit 0
fi
echo "--- RESULT: RED — a guard misbehaved or a label downgraded. DO NOT cutover. ---"
exit 1
