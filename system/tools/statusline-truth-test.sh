#!/usr/bin/env bash
# statusline-truth-test.sh — TRUTH CONTRACT test for the status bar's "desk:" field.
#
# WHY: the bottom-bar "desk:" field is load-bearing — the user steers across many session
# windows by it, so it MUST equal the session's real desk and MUST NEVER show a project slug.
# The donor system shipped a regression on 2026-07-13 (commit d54133c) that set this field to
# "${SLUG:-$DESK}", which made it display the armed project slug instead of the desk — plausible-
# looking, and hard to spot, because it still rendered a real-looking name. This test feeds
# system/statusline.sh known inputs and asserts: (1) desk = the real desk, (2) the slug never
# appears in the desk field.
#
# Runs standalone (exit 0 = GREEN, 1 = RED).
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SL="$ROOT/system/statusline.sh"
FLAGDIR="$HOME/.claude/run/pm"; mkdir -p "$FLAGDIR"
NOW=$(date +%s)
PASS=0; FAIL=0
TEST_FLAGS=()

cleanup() { for f in "${TEST_FLAGS[@]:-}"; do [ -n "$f" ] && rm -f "$f"; done; rm -rf "$SANDBOX"; }
trap cleanup EXIT

strip() { sed $'s/\x1b\\[[0-9;]*m//g'; }   # drop ANSI color escapes

# arm a fake session flag: $1=sid $2=desk $3=slug
arm() {
  local flag="$FLAGDIR/pm-sess-$1.flag"
  printf 'slug=%s\ndesk=%s\narmed_at=%s\nsession=%s\n' "$3" "$2" "$NOW" "$1" > "$flag"
  TEST_FLAGS+=("$flag")
}

json() {  # $1=sid $2=project_dir
  python3 -c 'import json,sys; print(json.dumps({
    "model":{"display_name":"Opus"},
    "context_window":{"used_percentage":10},
    "cost":{"total_cost_usd":1.0},
    "workspace":{"project_dir":sys.argv[2]},
    "session_id":sys.argv[1]}))' "$1" "$2"
}

# $1=case-name $2=sid $3=project_dir $4=expected-desk $5=slug-that-must-not-leak
assert_desk() {
  local name="$1" out got
  out=$(json "$2" "$3" | bash "$SL" 2>/dev/null | strip)
  got=$(printf '%s' "$out" | grep -o 'desk: [^ ]*' | tail -1 | sed 's/desk: //')
  if [ "$got" = "$4" ]; then PASS=$((PASS+1)); printf "  PASS  %-32s desk: %s\n" "$name" "$got"
  else FAIL=$((FAIL+1)); printf "  FAIL  %-32s expected desk:%s got desk:%s\n" "$name" "$4" "$got"; fi
  if [ -n "$5" ] && [ "$got" = "$5" ]; then
    FAIL=$((FAIL+1)); printf "  FAIL  %-32s SLUG '%s' LEAKED into desk field\n" "$name" "$5"; fi
}

CLONE="$ROOT"                                   # no /desks/ in path → root
# generic fixture desk (sandboxed, no real personal desk name — matches the "lamps"/"money"
# convention already used by system/hooks/tests/test_session_context_loader.sh)
SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/sltruth.XXXXXX")"
LAMPS="$SANDBOX/desks/lamps/state"
mkdir -p "$LAMPS"

echo "=== statusline truth test (desk: must be a desk, never a slug) ==="
# 1. the exact real-world break: armed root project — desk must be root, NOT the slug
arm zz-sltruth-1 root budget-review
assert_desk "armed root proj"        zz-sltruth-1      "$CLONE" root  budget-review
# 2. armed on a real non-root desk — desk must be that desk, NOT the slug
arm zz-sltruth-2 money quarterly-plan
assert_desk "armed money proj"       zz-sltruth-2      "$CLONE" money quarterly-plan
# 3. no flag, cwd under /desks/lamps/ — desk from folder detection
assert_desk "no flag, /desks/lamps"  zz-sltruth-noflag "$LAMPS" lamps ""
# 4. no flag, launched from the clone — desk falls back to root
assert_desk "no flag, clone cwd"     zz-sltruth-nf2    "$CLONE" root  ""

echo
echo "--- statusline-truth: $PASS passed, $FAIL failed ---"
[ "$FAIL" -eq 0 ] && { echo "GREEN - desk field is truthful."; exit 0; } || { echo "RED - desk field lied. FIX system/statusline.sh."; exit 1; }
