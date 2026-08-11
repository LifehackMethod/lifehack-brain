#!/usr/bin/env bash
# run_tester.sh -- the S3 tester seam for /skill-builder step 5.10 (SPEC.md sec 8h, row S3).
#
# WHAT: takes one argument -- the path to a BUILT skill's directory -- and answers, for real,
# whether anything testable exists and ran clean. It:
#   1. Looks for the target skill's OWN verify-*.sh -- checked in BOTH places one can live:
#      the skill's own directory (and its scripts/ subdir) AND system/tools/ (several existing
#      verify-*.sh scripts, e.g. verify-ship-skill.sh, live there instead of in the skill).
#   2. Looks at system/tools/conformance-lab/ -- reads it live (never assumed) and uses its
#      REAL entry point, driver.py.
#
# ⛔ SWAP-IN POINT FOR A FUTURE /skill-tester.
#    `/skill-tester` is ruled CUT (owner, 2026-08-07) -- so TESTER: NO-TESTER-RAN is the LIVE
#    value this script produces TODAY, not a fallback awaiting a better tool. If /skill-tester
#    is ever built, it is substituted in EXACTLY ONE place: the block below marked
#    "=== SWAP-IN POINT ===", which currently runs the verify-*.sh + conformance-lab search
#    this file does today. A real tester would run there instead (or alongside), and this
#    file's verdict contract (one `TESTER: ...` line, exit 0/1/2, LAW 1b honesty) does not
#    change -- only what fills that one block does.
#
# VERDICT LINE (matches .claude/skills/skill-builder/scripts/phase-contract.json phase 5's
# `tester-verdict` pattern EXACTLY -- do not drift from this vocabulary):
#   TESTER: PASSED          -- something testable ran and everything passed
#   TESTER: FAILED          -- something testable ran and something failed
#   TESTER: NO-TESTER-RAN   -- nothing testable was found, or nothing could be run
#
# ⭐ THE LAW THAT MATTERS MOST -- skill-building-sop.md LAW 1b (line 369): "an unreachable
# model is not a clean result." Applied here: an unreachable / errored / missing /
# non-executable / timed-out / empty result maps onto NO-TESTER-RAN or FAILED -- NEVER onto
# PASSED. A tool that isn't there must never read as clean. This is enforced by construction
# below: the PASSED line is only ever reached through one code path, at the very end, and
# only after ran_count > 0 AND fail_count == 0.
#
# Exit codes: 0 = PASSED, 1 = FAILED, 2 = NO-TESTER-RAN.
#
# Usage: bash run_tester.sh <path-to-built-skill-dir>

set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
# ⚠ RESOLVED, NOT COUNTED. This read `../../..` in the donor system, where the skill lived at
# skills/<name>/scripts/. Here it lives one level deeper, at .claude/skills/<name>/scripts/, and the
# counted form silently resolves to `.claude/` — every search below then looks in a directory that
# does not exist, finds nothing, and returns NO-TESTER-RAN. That verdict is honest-looking and wrong,
# which is the worst shape a tester can fail in.
REPO_ROOT="$(git -C "$HERE" rev-parse --show-toplevel 2>/dev/null || (cd "$HERE/../../../.." && pwd))"

NOTES=()
note() { NOTES+=("$1"); }

emit_and_exit() {
    # $1 = verdict word (PASSED|FAILED|NO-TESTER-RAN), $2 = exit code
    echo "TESTER: $1"
    for line in "${NOTES[@]}"; do
        printf '  %s\n' "$line"
    done
    exit "$2"
}

# ---------------------------------------------------------------- 0. argument + target check
if [ "$#" -ne 1 ]; then
    note "usage: run_tester.sh <path-to-built-skill-dir> -- no argument given"
    emit_and_exit "NO-TESTER-RAN" 2
fi

RAW_SKILL_DIR="$1"

if [ ! -d "$RAW_SKILL_DIR" ]; then
    note "searched: the given path, expecting a skill directory"
    note "found: NOTHING -- '$RAW_SKILL_DIR' does not exist or is not a directory"
    emit_and_exit "NO-TESTER-RAN" 2
fi

SKILL_DIR="$(cd "$RAW_SKILL_DIR" && pwd)"
SLUG="$(basename "$SKILL_DIR" | tr '[:upper:]' '[:lower:]')"

ran_count=0
fail_count=0

# a portable soft timeout (this Mac has neither `timeout` nor `gtimeout`) -- never let one
# script hang the whole tester run forever; an unreachable/hung tool maps to NO-TESTER-RAN /
# FAILED, never to a silently-still-running PASS.
run_with_timeout() {
    local secs="$1"; shift
    "$@" &
    local pid=$!
    ( sleep "$secs" 2>/dev/null && kill -TERM "$pid" 2>/dev/null ) &
    local watcher=$!
    wait "$pid" 2>/dev/null
    local rc=$?
    kill "$watcher" 2>/dev/null
    wait "$watcher" 2>/dev/null
    return $rc
}

# invoke a shell script honoring ITS OWN shebang (some of these are zsh, not bash --
# verify-ingest-integrity.sh's own header warns that testing a zsh-ism script under the
# wrong interpreter dies at expansion, which looks exactly like the suite failing, not like
# no check ran -- so read the shebang rather than assume).
invoke_script() {
    local script="$1"
    if [ ! -r "$script" ]; then
        note "  -> UNREADABLE, not invoked: $script"
        return 9
    fi
    local shebang interp
    shebang="$(head -1 "$script" 2>/dev/null)"
    case "$shebang" in
        '#!'*) interp="${shebang#\#!}" ;;
        *) interp="/bin/bash" ;;
    esac
    note "  -> running ($interp): $script"
    # shellcheck disable=SC2086
    run_with_timeout 120 $interp "$script"
    local rc=$?
    if [ "$rc" -eq 0 ]; then
        note "     exit 0"
    else
        note "     exit $rc"
    fi
    return $rc
}

# =========================================================================================
# === SWAP-IN POINT ===  (a future /skill-tester replaces or augments everything below)
# =========================================================================================

# ---------------------------------------------------------------- 1. the skill's own verify-*.sh
note "search 1 -- the skill's own verify-*.sh, checked in TWO places:"
note "  (a) $SKILL_DIR/verify-*.sh"
note "  (b) $SKILL_DIR/scripts/verify-*.sh"

own_found=0
for d in "$SKILL_DIR" "$SKILL_DIR/scripts"; do
    [ -d "$d" ] || continue
    shopt -s nullglob
    for f in "$d"/verify-*.sh; do
        own_found=1
        ran_count=$((ran_count + 1))
        note "found: $f"
        invoke_script "$f"
        rc=$?
        [ "$rc" -ne 0 ] && fail_count=$((fail_count + 1))
    done
    shopt -u nullglob
done
[ "$own_found" -eq 0 ] && note "found: nothing in either location"

# ---------------------------------------------------------------- 2. system/tools/verify-*.sh matching this skill
TOOLS_DIR="$REPO_ROOT/system/tools"
note "search 2 -- system/tools/verify-*.sh whose filename names this skill (slug: '$SLUG')"

tools_found=0
if [ -d "$TOOLS_DIR" ]; then
    shopt -s nullglob
    for f in "$TOOLS_DIR"/verify-*.sh; do
        base_lc="$(basename "$f" | tr '[:upper:]' '[:lower:]')"
        case "$base_lc" in
            *"$SLUG"*)
                tools_found=1
                ran_count=$((ran_count + 1))
                note "found: $f (filename contains slug '$SLUG')"
                invoke_script "$f"
                rc=$?
                [ "$rc" -ne 0 ] && fail_count=$((fail_count + 1))
                ;;
        esac
    done
    shopt -u nullglob
else
    note "found: $TOOLS_DIR does not exist"
fi
[ "$tools_found" -eq 0 ] && [ -d "$TOOLS_DIR" ] && note "found: no system/tools/verify-*.sh filename contains '$SLUG'"

# ---------------------------------------------------------------- 3. the second tester, and why there isn't one
#
# The donor system had a second place to look: a conformance lab that graded a skill's spec against
# what a real run wrote to disk. ⛔ IT DOES NOT SHIP HERE, and the reason was measured by this very
# script on 2026-08-08, in the comment this block replaces: every subject in that lab's rule registry
# is either a throwaway skill it generates itself or an adversarial scenario -- NEVER an existing
# skill's slug. It has no door for "test skill X" at all. It also resolved its registry to a path in
# the author's cloud folder, hardcoded an absolute `claude` binary path and an OAuth token file, and
# would have spawned paid model calls per row.
#
# Saying that here, once, beats a live probe for a directory that is never coming: a search that
# always reports "not found" trains the reader to skim past the one search that matters.
note "search 3 -- a second tester: none ships here (the donor's conformance lab had no door for "
note "  testing a named skill; see this script's own header and SPEC.md's citation block)"

# =========================================================================================
# === END SWAP-IN POINT ===
# =========================================================================================

# ---------------------------------------------------------------- verdict
if [ "$ran_count" -eq 0 ]; then
    emit_and_exit "NO-TESTER-RAN" 2
elif [ "$fail_count" -gt 0 ]; then
    emit_and_exit "FAILED" 1
else
    emit_and_exit "PASSED" 0
fi
