# shellcheck shell=bash
# checks/_lib.sh — sourced by ai.sh / code.sh / human.sh. Runs _check.py and ENFORCES its verdict contract:
#   rc 0 needs first line "PASS ", rc 1 needs "FAIL ", rc 4 needs "CANNOT-READ".
# Anything else (python missing, syntax error, a traceback that exits 1, a stray rc) becomes CANNOT-READ / exit 4,
# so a crash can never be read as a pass OR as a fail. 4 = shared/emit/verdicts.py CANNOT_READ (selftest asserts
# the two agree; this copy exists only for the case where python itself cannot run).
_CHECKS_CANNOT_READ=4
run_check() {
  local kind="$1"; shift
  local here out rc first
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || { printf 'CANNOT-READ\n  cannot locate checks/\n'; return $_CHECKS_CANNOT_READ; }
  out="$(python3 -I -B "$here/_check.py" "$kind" "$@" 2>&1)"; rc=$?
  first="${out%%$'\n'*}"
  case "$rc:$first" in
    "0:PASS "*|"1:FAIL "*|"4:CANNOT-READ") printf '%s\n' "$out"; return "$rc" ;;
  esac
  printf 'CANNOT-READ\n  %s check broke its verdict contract (rc=%s, first line: %s)\n' "$kind" "$rc" "${first:-<none>}"
  return $_CHECKS_CANNOT_READ
}
