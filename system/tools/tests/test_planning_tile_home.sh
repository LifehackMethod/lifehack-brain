#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# test_planning_tile_home.sh — CR-9 step 2(c) / BUILD-ORDER move 18: the planning
# desk's tiles land at <brain>/status/<producer>.json through the ONE writer,
# emit_status.py, and never under the old state/status/ home or by a second
# (hand-rolled) writer.
#
# Part 1 is DYNAMIC: with a temp brain root via the seam ($LIFEHACK_ROOT, the
# first route in shared/brain_root.py), the exact CLI call the runners make must
# put the tile at <root>/status/<producer>.json with the full envelope, and must
# NOT create <root>/state/status/.
# Part 2 is STATIC plus a PLANTED FAULT: the checker greps the planning runners
# for the old home and for a second writer (an inline json.dump writing a status
# tile). The same checker, run over a planted faulty fixture, must FAIL — and
# name the file and line — proving the check actually catches the fault.
# ─────────────────────────────────────────────────────────────────────────────
set -u
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
fails=0
note() { echo "  $*"; }
die()  { echo "✗ $*"; fails=$((fails+1)); }

# ── Part 1: the tile lands at <brain>/status/ through emit_status.py (seam) ──
TMPROOT="$(mktemp -d "${TMPDIR:-/tmp}/cr9-tile.XXXXXX")"
printf '{"iso_week": "2026-W47", "no_pulse": true}' | \
  LIFEHACK_ROOT="$TMPROOT" python3 "$CODE_ROOT/system/tools/emit_status.py" \
    --out "$TMPROOT/status/planning-weekly-analyze.json" \
    --desk planning --pulse-job planning-weekly-analyze --stale-after-s 604800 \
    --status OK --rc 0 \
    --summary "test emit through the one writer" \
    --json -
rc=$?
[ $rc -eq 0 ] || die "emit_status.py CLI exited rc=$rc (expected 0)"
if [ -f "$TMPROOT/status/planning-weekly-analyze.json" ]; then
  note "tile landed at <brain>/status/planning-weekly-analyze.json"
else
  die "tile NOT at $TMPROOT/status/planning-weekly-analyze.json"
fi
python3 - "$TMPROOT/status/planning-weekly-analyze.json" <<'PYEOF' || die "tile envelope wrong or incomplete"
import json, sys
d = json.load(open(sys.argv[1]))
missing = [k for k in ("desk","schema_version","pulse_job","emit_mode","stale_after_s","last_run","rc","status","summary") if k not in d]
assert not missing, "missing envelope fields: %s" % missing
assert d["desk"] == "planning" and d["pulse_job"] == "planning-weekly-analyze"
assert d["status"] == "OK" and d["iso_week"] == "2026-W47"
PYEOF
if [ -e "$TMPROOT/state/status" ]; then
  die "old home <brain>/state/status/ was created — a tile went to the wrong home"
else
  note "no $TMPROOT/state/status/ was created"
fi
rm -rf "$TMPROOT"

# ── Part 2a: the static checker (shared by the real tree and the fault) ──
check_runner() {  # file -> prints "FAIL <file>:<line>: <reason>" lines; empty = clean
  python3 - "$1" <<'PYEOF'
import sys, re
path = sys.argv[1]
bad = []
for n, line in enumerate(open(path).read().splitlines(), 1):
    if line.lstrip().startswith("#"):
        continue  # comments may NAME the fault they fixed; only code is checked
    if re.search(r"state/status", line):
        bad.append((n, "old tile home state/status"))
    # a SECOND writer: an inline python tile build (json.dump) inside a runner
    if re.search(r"json\.dump", line):
        bad.append((n, "inline json.dump — a hand-rolled second tile writer"))
for n, why in bad:
    print("FAIL %s:%d: %s" % (path, n, why))
PYEOF
}

# ── Part 2b: the PLANTED FAULT must be caught, BY NAME ──
FAULT="$(mktemp -d "${TMPDIR:-/tmp}/cr9-fault.XXXXXX")"
cat > "$FAULT/planted-second-writer.sh" <<'FEOF'
_TILE="$DRIVE/state/status/planning-diary.json"
python3 -c "
import json, os
json.dump(d, open('$_TILE.tmp','w'), indent=2)
"
FEOF
planted_out="$(check_runner "$FAULT/planted-second-writer.sh")"
case "$planted_out" in
  *":1: old tile home state/status"*) note "planted fault caught: old home, line 1" ;;
  *) die "planted fault (old home) NOT caught by name. Checker said: ${planted_out:-<nothing>}" ;;
esac
case "$planted_out" in
  *":4: inline json.dump"*) note "planted fault caught: second writer, line 4" ;;
  *) die "planted fault (second writer) NOT caught by name. Checker said: ${planted_out:-<nothing>}" ;;
esac
rm -rf "$FAULT"

# ── Part 2c: the real tree must come back clean ──
for f in "$CODE_ROOT"/system/tools/planning-weekly-prime-run.sh \
         "$CODE_ROOT"/system/tools/planning-weekly-analyze-run.sh; do
  out="$(check_runner "$f")"
  if [ -n "$out" ]; then die "real tree still dirty: $out"; else note "clean: $(basename "$f")"; fi
done

# ── verdict ──
if [ "$fails" -eq 0 ]; then echo "test_planning_tile_home.sh PASSED"; else echo "test_planning_tile_home.sh FAILED ($fails)"; exit 1; fi
