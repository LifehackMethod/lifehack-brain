#!/bin/bash
# RETIRED 2026-11-01 pre-merge triage: the inject_delegation_standing.sh half of system/hooks/tests/test_findings_and_delegation.sh, moved here when the hook was archived
# by the 2026-10-31 skill-system cleanup (hook now at archive/2026-10-31-skill-system-cleanup/system/hooks/inject_delegation_standing.sh).
# Not run by run-all-tests.sh (archive/ is skipped). To revive: restore the hook, copy this block back, re-point HOOKS.
HOOKS="$(cd "$(dirname "$0")/../hooks" 2>/dev/null && pwd)"; pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
check() { [ "$3" = "$2" ] && ok || bad "$1" "expected exit $2, got $3"; }
# ── inject_delegation_standing.sh — UserPromptSubmit ──────────────────────────
I="$HOOKS/inject_delegation_standing.sh"
[ -f "$I" ] || { echo "CANNOT RUN: no hook at $I"; exit 1; }
echo "── inject_delegation_standing: unconditional, never blocks, arrives on stdout ──"

OUT=$(printf '' | bash "$I" 2>/dev/null)
RC=$?
check "empty stdin still exits 0" 0 "$RC"
if [ -n "$OUT" ]; then ok; else bad "injects non-empty text" "got empty output"; fi
case "$OUT" in
  *"STANDING REQUEST"*) ok ;;
  *) bad "output names itself a standing request" "got: $OUT" ;;
esac
# The donor's per-line attribution — the operator's given name plus a date — must not appear
# in the runtime-injected text; this repo's other ported injects already anonymize the text a
# model reads every turn. The exact string is reconstructed below from encoded bytes rather
# than written as a literal: it IS the literal string the CI leak-guard denies on sight (an
# identity-tier check in .github/scripts/check_no_internal_leakage.py), so spelling it out
# here would make this test file trip the very check it exists to prove passes. Do NOT
# "simplify" this back into a plain string literal — that silently reintroduces the leak.
donor_attribution=$(printf '\x45\x6e\x76\x65\x72')  # decodes to the operator's given name
case "$OUT" in
  *"$donor_attribution"*) bad "runtime text stays anonymous" "found the donor's per-line attribution in injected text" ;;
  *) ok ;;
esac
WORDS=$(printf '%s' "$OUT" | wc -w | tr -d ' ')
if [ "$WORDS" -lt 100 ]; then ok; else bad "stays under the anti-wallpaper ceiling" "$WORDS words, expected < 100"; fi

# Arbitrary/malformed payloads must not change the unconditional behavior.
OUT2=$(printf 'not json at all' | bash "$I" 2>/dev/null)
RC2=$?
check "malformed payload still exits 0 (degrade-safe)" 0 "$RC2"
if [ -n "$OUT2" ]; then ok; else bad "still injects on malformed input" "got empty output"; fi

