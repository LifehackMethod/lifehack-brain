#!/usr/bin/env bash
# run-all-tests.sh — THE aggregate test runner: every test_*.py and test_*.sh, one gate.
#
# WHY THIS EXISTS. DEST ships 35 test files and nothing ran them: no .github/workflows/ (the
# folder does not exist), no Makefile/justfile/Taskfile. The one runner that existed,
# system/shipping-lane/run_selftests.sh, only ever iterates its own folder — 0 of the 35 land in
# it, because that gate proves `--selftest` modules, a different contract from a test_*.py/sh
# file entirely. The port carried the machinery and not the switch that turns it on. This is
# the switch — and it is additive: it does not replace the shipping-lane gate, it covers what
# that gate structurally cannot see.
#
# Finds every test_*.py / test_*.sh in the repo (excluding .git/), runs each one under a
# per-file timeout, and prints ONE summary line. Exits non-zero if anything failed.
#
# Usage:  bash system/tools/run-all-tests.sh
# Env:    TEST_TIMEOUT_SECS=90   per-file wall-clock limit, in seconds (default 90)
#
# ⛔ SAFETY NET, NOT A SUBSTITUTE FOR READING THE TESTS. This script exports its own throwaway
# LIFEHACK_ROOT for the whole run so a test that forgets to sandbox itself still cannot reach a
# real data root — belt on top of the braces most individual tests already wear (they override
# LIFEHACK_ROOT themselves, per-subprocess, into their own tempdir). It does NOT sandbox the
# network: a test that makes a live outbound call stays live no matter what this script sets.
# That is why one file below is skipped BY NAME rather than run — see SKIP_RELPATHS — and why
# adding a new skip entry always needs a reason that names the actual call, not a guess.
PY="${PY:-/usr/bin/python3}"   # PINNED: bare `python3` can resolve to a Homebrew install with no
                                # third-party packages, which would silently misreport results.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"

TIMEOUT_SECS="${TEST_TIMEOUT_SECS:-90}"

# A throwaway data root and a throwaway output buffer, both for this run only.
RUN_TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/run-all-tests-root.XXXXXX")"
OUT="$(mktemp "${TMPDIR:-/tmp}/run-all-tests-out.XXXXXX")"
trap 'rm -rf "$RUN_TMP_ROOT" "$OUT"' EXIT
export LIFEHACK_ROOT="$RUN_TMP_ROOT"

# ── files this gate will not run, and why ─────────────────────────────────────────────────────
# A file goes on this list ONLY when reading its source shows a real outbound network call this
# runner cannot neutralize (sandboxing the data root above does not sandbox the network) —
# never for convenience, never because a file is slow or flaky. Each path is repo-root-relative.
SKIP_RELPATHS=(
  "system/tools/test_safe_readers.py"
)
SKIP_REASONS=(
  "GoogleReaderCase/SearchCase make REAL outbound calls: test_the_key_file_is_preferred_over_the_keychain writes a working-shaped (fake-valued) key to a file and calls safe_search_api.sh for real, which POSTs to https://google.serper.dev/search; test_no_key_anywhere_names_all_three_places_it_looked falls through to the macOS keychain and would fire a genuinely live query if this machine has a real Serper key configured there. Neither call is mocked."
)

is_skipped() {  # is_skipped <repo-relative-path>  ->  prints the reason + rc 0 if on the list, else rc 1
  local rp="$1" i
  for i in "${!SKIP_RELPATHS[@]}"; do
    [ "${SKIP_RELPATHS[$i]}" = "$rp" ] && { printf '%s' "${SKIP_REASONS[$i]}"; return 0; }
  done
  return 1
}

# ── a portable per-file timeout ───────────────────────────────────────────────────────────────
# Neither `timeout` nor `gtimeout` ships on a plain macOS box (no coreutils by default) — this
# polls once a second instead of depending on either.
run_with_timeout() {  # run_with_timeout <secs> <outfile> <cmd...>   ->  return code (124 = timed out)
  local secs="$1" outfile="$2"; shift 2
  "$@" >"$outfile" 2>&1 &
  local pid=$! n=0
  while kill -0 "$pid" 2>/dev/null; do
    if [ "$n" -ge "$secs" ]; then
      kill -TERM "$pid" 2>/dev/null; sleep 1; kill -KILL "$pid" 2>/dev/null
      wait "$pid" 2>/dev/null
      return 124
    fi
    sleep 1; n=$((n + 1))
  done
  wait "$pid"
}

# ── discover every test file, deterministically ───────────────────────────────────────────────
FILES=()
while IFS= read -r f; do
  FILES+=("$f")
done < <(find "$REPO_ROOT" -path "$REPO_ROOT/.git" -prune -o -type f \( -name 'test_*.py' -o -name 'test_*.sh' \) -print | sort)

TOTAL=${#FILES[@]}

# ── --help / --list, and why a test runner needs them ─────────────────────────────────────────
# Handled AFTER discovery so --list can report it, but BEFORE a single test runs.
# ⛔ THIS IS NOT POLITENESS. Without it, anything that probes this folder with --help -- which is
# exactly what system/tools/smoke-check.sh does to every tool -- falls through to the loop below
# and RUNS THE ENTIRE SUITE. Measured 2026-08-14: the smoke check hit its 15s cap on this file and
# reported it as a timeout, because asking a test runner for help ran every test in the repo.
# A tool that cannot be asked what it is, cannot be swept.
case "${1:-}" in
  --help|-h)
    echo "run-all-tests.sh — runs every test_*.py / test_*.sh in the repo, one gate."
    echo
    echo "Usage:  bash system/tools/run-all-tests.sh [--help|--list]"
    echo "  --list   print the test files that WOULD run, one per line, and exit 0"
    echo "  (no arg) run them all; exits non-zero if any failed"
    echo
    echo "Env:    TEST_TIMEOUT_SECS=90   per-file wall-clock limit, in seconds"
    echo "Found $TOTAL test files. ${#SKIP_RELPATHS[@]} on the skip list (live network calls)."
    exit 0
    ;;
  --list)
    for f in "${FILES[@]}"; do printf '%s\n' "${f#"$REPO_ROOT"/}"; done
    exit 0
    ;;
esac

PASS=0; FAIL=0; SKIP=0
FAILED_NAMES=""
SKIPPED_NAMES=""

echo "═══ aggregate test gate — $TOTAL test files found ═══"
echo

for f in "${FILES[@]}"; do
  rel="${f#"$REPO_ROOT"/}"

  if reason="$(is_skipped "$rel")"; then
    echo "  ⏭ SKIP  $rel"
    echo "      $reason"
    SKIP=$((SKIP + 1)); SKIPPED_NAMES="$SKIPPED_NAMES $rel"
    continue
  fi

  case "$f" in
    *.py) cmd=("$PY" "$f") ;;
    *.sh) cmd=(bash "$f") ;;
    *) echo "  ⏭ SKIP  $rel (unrecognized extension)"; SKIP=$((SKIP + 1)); SKIPPED_NAMES="$SKIPPED_NAMES $rel"; continue ;;
  esac

  run_with_timeout "$TIMEOUT_SECS" "$OUT" "${cmd[@]}"
  rc=$?

  if [ "$rc" -eq 0 ]; then
    echo "  ✔ PASS  $rel"
    PASS=$((PASS + 1))
  elif [ "$rc" -eq 124 ]; then
    echo "  ✘ TIMEOUT  $rel  (exceeded ${TIMEOUT_SECS}s)"
    tail -n 15 "$OUT" | sed 's/^/      /'
    FAIL=$((FAIL + 1)); FAILED_NAMES="$FAILED_NAMES $rel(timeout)"
  else
    echo "  ✘ FAIL  $rel  (exit $rc)"
    tail -n 15 "$OUT" | sed 's/^/      /'
    FAIL=$((FAIL + 1)); FAILED_NAMES="$FAILED_NAMES $rel"
  fi
done

echo
echo "─────────────────────────────────────"
[ -n "$FAILED_NAMES" ] && echo "FAILED:$FAILED_NAMES"
[ -n "$SKIPPED_NAMES" ] && echo "SKIPPED:$SKIPPED_NAMES"
echo "TESTS: $PASS passed · $FAIL failed · $SKIP skipped ($TOTAL total)"

[ "$FAIL" -eq 0 ] && exit 0
exit 1
