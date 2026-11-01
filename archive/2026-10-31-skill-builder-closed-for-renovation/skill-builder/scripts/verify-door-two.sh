#!/usr/bin/env bash
# verify-door-two.sh -- the DOOR TWO posture gate, run against the six phase drivers.
#
# WHAT: two mechanical checks, reused as-is (no new primitive):
#   1. order_lint.py       -- the DOOR TWO posture block must appear BEFORE the locked
#                              step ladder in every driver (door-two-rules.json).
#   2. forbidden_content.py -- the stale "NOT BUILT ... no prompts/ folder exists yet"
#                              claim must never regress (door-two-forbidden-rules.json).
#
# USAGE (one line, from anywhere):
#   bash .claude/skills/skill-builder/scripts/verify-door-two.sh
#
# Prints one PASS/FAIL line per file per check. On any FAIL, the checker's own output is
# shown indented underneath. Exits 0 only if every file passes both checks.

set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
# The two checkers used to sit beside this script as vendored copies, byte-identical to the ones in
# system/parts/. A part with two copies has two behaviours the day one of them is fixed, so the
# copies were dropped and this points at the library. Resolved, not counted -- the counted form
# breaks the moment this skill moves a directory.
REPO_ROOT="$(git -C "$HERE" rev-parse --show-toplevel 2>/dev/null || (cd "$HERE/../../../.." && pwd))"
PARTS="$REPO_ROOT/system/parts"
PHASES_DIR="$HERE/../phases"
ORDER_RULES="$HERE/door-two-rules.json"
FORBIDDEN_RULES="$HERE/door-two-forbidden-rules.json"

overall_status=0
tmp_out="$(mktemp)"
trap 'rm -f "$tmp_out"' EXIT

for f in "$PHASES_DIR"/*.md; do
    name="$(basename "$f")"

    if python3 "$PARTS/order_lint.py" --rules "$ORDER_RULES" --artifact "$f" >"$tmp_out" 2>&1; then
        echo "PASS  order       $name"
    else
        rc=$?
        echo "FAIL  order       $name  (exit $rc)"
        sed 's/^/        /' "$tmp_out"
        overall_status=1
    fi

    if python3 "$PARTS/forbidden_content.py" --rules "$FORBIDDEN_RULES" --text-file "$f" >"$tmp_out" 2>&1; then
        echo "PASS  forbidden   $name"
    else
        rc=$?
        echo "FAIL  forbidden   $name  (exit $rc)"
        sed 's/^/        /' "$tmp_out"
        overall_status=1
    fi
done

if [ "$overall_status" -eq 0 ]; then
    echo "ALL PASS"
else
    echo "AT LEAST ONE FAILURE -- see FAIL lines above"
fi

exit "$overall_status"
