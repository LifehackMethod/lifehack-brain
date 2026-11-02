#!/bin/bash
# test_session_context_loader_desk_scope.sh — COMPASS P-71, decision 2g: a desk window loads only
# that desk's knowledge. Until 2026-11-02 the loader globbed EVERY desk's canon/current.md into
# EVERY session; this suite locks the desk-scoped behaviour in.
#
# Cases (from the P-71 fix brief):
#   1. cwd inside desk A -> A's canon loads, B's does NOT;
#   2. cwd outside every desk -> NO desk canon at all;
#   3. the shared root canon still loads in both;
#   4. a missing desk list (no desk-registry.yaml) -> no crash, still exit 0.
# Plus: the explicit $LIFEHACK_DESK signal selects the desk; a desk name with no folder is a LOUD
# miss, not a silent one; the nested-canon warning (Issue #96-§5) still fires for the chosen desk.
#
# Run: bash system/hooks/tests/test_session_context_loader_desk_scope.sh (exit 0 = all pass)
#
# BEFORE/AFTER SEAM: set LOADER_UNDER_TEST to run this suite against a different copy of
# session_context_loader.sh (the old, all-desks loader fails every desk-scope assertion). The copy
# under test must sit in a tree that has shared/brain_root.py two levels up from it.

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
LOADER="${LOADER_UNDER_TEST:-$HOOKS/session_context_loader.sh}"
REPO="${HOOKS%/system/hooks}"
[ -f "$LOADER" ] || { echo "CANNOT RUN: no loader at $LOADER"; exit 1; }
LREPO="$(cd "$(dirname "$LOADER")/../.." && pwd)"
[ -f "$LREPO/shared/brain_root.py" ] || { echo "CANNOT RUN: $LREPO/shared/brain_root.py missing"; exit 1; }

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/loader-desk-scope.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
NOTES="$SANDBOX/notes"
mkdir -p "$NOTES/desks/alpha/canon" "$NOTES/desks/beta/canon" "$NOTES/desks/beta/nested-subject/canon"
printf 'Shared root canon: one L.\n' > "$NOTES/canon.md"
printf 'ALPHA canon: prefer warm bulbs 2700K.\n' > "$NOTES/desks/alpha/canon/current.md"
printf 'BETA canon: the tax year ends in April.\n' > "$NOTES/desks/beta/canon/current.md"
printf 'BETA NESTED canon: nested subject facts.\n' > "$NOTES/desks/beta/nested-subject/canon/current.md"
# Deliberately NO desk-registry.yaml and no $LIFEHACK_DESK_LIST: the desk is inferred from the
# folder schema, and a missing desk list must mean "no desks to consult", never a crash.

pass=0; fail=0
ok() { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo " FAIL [$1]: $2"; }

# runin <cwd> [extra env as KEY=VAL...] — runs the loader under test, captures output + rc.
runin() {
  local d="$1"; shift
  OUT="$(cd "$d" && env -u CLAUDE_PLUGIN_ROOT -u LIFEHACK_DESK -u LIFEHACK_DESK_LIST \
        HOME="$SANDBOX" LIFEHACK_ROOT="$NOTES" "$@" bash "$LOADER" 2>&1)"
  RC=$?
}
says() { printf '%s' "$OUT" | grep -q "$1"; }
saysnot() { ! printf '%s' "$OUT" | grep -q "$1"; }

echo "── 1: cwd inside desk alpha -> alpha's canon, and ONLY alpha's ────────────"
runin "$NOTES/desks/alpha"
says "2700K" && ok || bad "in desk A: A loads" "alpha canon missing from output"
saysnot "ends in April" && ok || bad "in desk A: B must not load" "beta canon leaked into a desk-alpha session"
says "alpha (this session's desk)" && ok || bad "in desk A: header" "the desk is not named in the output"
[ "$RC" = 0 ] && ok || bad "in desk A: exit code" "expected 0, got $RC"

echo "── 2: cwd outside every desk -> NO desk canon ─────────────────────────────"
runin "$SANDBOX"
saysnot "2700K" && ok || bad "outside desks: A must not load" "alpha canon leaked into a no-desk session"
saysnot "ends in April" && ok || bad "outside desks: B must not load" "beta canon leaked into a no-desk session"
says "No desk this session" && ok || bad "outside desks: wording" "did not say no desk canon was loaded"
[ "$RC" = 0 ] && ok || bad "outside desks: exit code" "expected 0, got $RC"

echo "── 3: the shared root canon still loads, in a desk and out of one ────────"
runin "$NOTES/desks/beta"
says "one L" && ok || bad "shared canon in desk" "root canon dropped inside a desk"
says "ends in April" && ok || bad "shared canon in desk: B loads" "beta canon missing in a beta session"
saysnot "2700K" && ok || bad "shared canon in desk: A must not load" "alpha canon leaked into a desk-beta session"
runin "$SANDBOX"
says "one L" && ok || bad "shared canon outside desks" "root canon dropped outside desks"
[ "$RC" = 0 ] && ok || bad "shared canon outside: exit code" "expected 0, got $RC"

echo "── 4: a missing desk list means no desks, never a crash ───────────────────"
# No desk-registry.yaml exists anywhere in $NOTES (asserted here so the fixture cannot rot in
# silence), no $LIFEHACK_DESK, no $LIFEHACK_DESK_LIST, cwd in a desk that exists only as folders.
[ ! -e "$NOTES/desks/desk-registry.yaml" ] && ok || bad "fixture" "a desk-registry.yaml appeared — the no-list case tests nothing"
runin "$NOTES/desks/alpha"
says "2700K" && ok || bad "missing desk list: desk still loads" "a missing registry stopped desk inference"
[ "$RC" = 0 ] && ok || bad "missing desk list: exit code" "expected 0, got $RC"

echo "── the explicit signal: \$LIFEHACK_DESK selects the desk from anywhere ───"
OUT="$(cd "$SANDBOX" && env -u CLAUDE_PLUGIN_ROOT -u LIFEHACK_DESK_LIST \
      HOME="$SANDBOX" LIFEHACK_ROOT="$NOTES" LIFEHACK_DESK=beta bash "$LOADER" 2>&1)"; RC=$?
says "ends in April" && ok || bad "env signal" "LIFEHACK_DESK=beta did not load beta's canon"
saysnot "2700K" && ok || bad "env signal: A must not load" "alpha canon leaked despite LIFEHACK_DESK=beta"
[ "$RC" = 0 ] && ok || bad "env signal: exit code" "expected 0, got $RC"

echo "── a desk name that matches no folder is a LOUD miss ─────────────────────"
OUT="$(cd "$SANDBOX" && env -u CLAUDE_PLUGIN_ROOT -u LIFEHACK_DESK_LIST \
      HOME="$SANDBOX" LIFEHACK_ROOT="$NOTES" LIFEHACK_DESK=ghost bash "$LOADER" 2>&1)"; RC=$?
says "DESK NOT FOUND" && ok || bad "unknown desk" "no visible message for a desk with no folder"
saysnot "2700K" && ok || bad "unknown desk: nothing loads" "canon loaded despite an unknown desk name"
saysnot "ends in April" && ok || bad "unknown desk: nothing loads (2)" "canon loaded despite an unknown desk name"
[ "$RC" = 0 ] && ok || bad "unknown desk: exit code" "expected 0, got $RC"

echo "── the nested-canon warning (Issue #96-§5) still fires for the chosen desk"
runin "$NOTES/desks/beta"
says "NESTED CANON NOT LOADED" && ok || bad "nested canon" "no warning for the nested subject under beta"
says "nested-subject" && ok || bad "nested canon: names it" "the warning did not name the nested folder"
runin "$NOTES/desks/alpha"
saysnot "NESTED CANON NOT LOADED" && ok || bad "nested canon: scoped" "a nested warning fired for a desk with none"

echo ""
echo "RESULT: $pass passed, $fail failed."
[ "$fail" = 0 ] && echo "SESSION CONTEXT DESK-SCOPE GREEN" || exit 1
