#!/bin/bash
# test_flag_lib.sh — B5.1: the shared library contract, and the three simple flags that had no
# dedicated suite before this one (skill_anchor.sh, scratch_flag.sh, altitude_flag.sh — numbers_flag
# and throughline_flag are already covered end-to-end by test_numbers_mode.sh / test_throughline_scope.sh).
#
# TWO THINGS THIS SUITE EXISTS TO CATCH:
#
#   1. A SILENT NO-OP WHEN THE SHARED LIBRARY IS GONE OR BROKEN (D6 condition 3). Five scripts now
#      depend on one file (system/hooks/lib/flag.sh); if it goes missing or corrupts and a shim
#      quietly exits 0, every downstream reader sees "nothing armed" and a lock could look un-armed
#      at once. Every shim must fail LOUD instead: non-zero exit, a clear stderr line.
#   2. A REGRESSION IN THE THREE FLAGS THAT HAD NO TEST AT ALL BEFORE B5.1. Converting them to thin
#      shims is exactly the kind of change that can silently alter a payload field or an exit code
#      with nobody noticing, because nothing was watching these three before.
#
# Run: bash system/hooks/tests/test_flag_lib.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
LIB="$HOOKS/lib/flag.sh"
[ -f "$LIB" ] || { echo "CANNOT RUN: no library at $LIB"; exit 1; }
for s in skill_anchor.sh scratch_flag.sh altitude_flag.sh numbers_flag.sh throughline_flag.sh; do
  [ -f "$HOOKS/$s" ] || { echo "CANNOT RUN: no script at $HOOKS/$s"; exit 1; }
done

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/flaglib.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
FAKEHOME="$SANDBOX/home"; mkdir -p "$FAKEHOME"
ANCHOR_FILE="$SANDBOX/anchor.md"; : > "$ANCHOR_FILE"
SCRATCH_FILE="$SANDBOX/pad.md"; : > "$SCRATCH_FILE"

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

echo "── skill_anchor.sh: arm / status / clear, and its own arg validation ─────"
SID="sess-alpha"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/skill_anchor.sh" status)"
[ "$out" = "none" ] && ok || bad "status before arm" "expected 'none', got '$out'"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/skill_anchor.sh" arm demo-slug "$ANCHOR_FILE")"
printf '%s' "$out" | grep -q "^ANCHOR ARMED: demo-slug -> $ANCHOR_FILE" && ok || bad "arm output" "$out"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/skill_anchor.sh" status)"
[ "$out" = "demo-slug" ] && ok || bad "status after arm shows the slug" "expected 'demo-slug', got '$out'"
env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/skill_anchor.sh" arm demo-slug "$SANDBOX/no-such-file.md" >/dev/null 2>&1
[ "$?" = 1 ] && ok || bad "arm rejects a missing anchor file" "expected exit 1"
env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/skill_anchor.sh" arm >/dev/null 2>&1
[ "$?" = 1 ] && ok || bad "arm rejects missing args" "expected exit 1"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="sess-beta" bash "$HOOKS/skill_anchor.sh" status)"
[ "$out" = "none" ] && ok || bad "cross-session leak" "beta saw alpha's anchor: '$out'"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" ANCHOR_TTL_HOURS=0 bash "$HOOKS/skill_anchor.sh" status)"
[ "$out" = "none" ] && ok || bad "TTL expiry" "expected 'none' at TTL 0, got '$out'"
env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/skill_anchor.sh" arm demo-slug "$ANCHOR_FILE" >/dev/null
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/skill_anchor.sh" clear)"
printf '%s' "$out" | grep -q "^ANCHOR CLEARED" && ok || bad "clear output" "$out"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/skill_anchor.sh" status)"
[ "$out" = "none" ] && ok || bad "status after clear" "expected 'none', got '$out'"
env HOME="$FAKEHOME" bash "$HOOKS/skill_anchor.sh" wibble >/dev/null 2>&1
[ "$?" = 2 ] && ok || bad "unknown verb" "expected exit 2"

echo "── scratch_flag.sh: arm / status / clear ─────────────────────────────────"
SID="sess-gamma"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/scratch_flag.sh" status)"
[ "$out" = "none" ] && ok || bad "status before arm" "expected 'none', got '$out'"
env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/scratch_flag.sh" arm "$SCRATCH_FILE" demo-skill >/dev/null
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/scratch_flag.sh" status)"
[ "$out" = "armed" ] && ok || bad "status after arm" "expected 'armed', got '$out'"
FLAG_FILE="$FAKEHOME/.claude/run/scratch/scratch-sess-$SID.flag"
grep -q "^scratch_path=$SCRATCH_FILE\$" "$FLAG_FILE" && ok || bad "scratch_path field" "missing/wrong in $FLAG_FILE"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" SCRATCH_TTL_MIN=0 bash "$HOOKS/scratch_flag.sh" status)"
[ "$out" = "none" ] && ok || bad "TTL expiry" "expected 'none' at TTL 0, got '$out'"
env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/scratch_flag.sh" arm "$SCRATCH_FILE" demo-skill >/dev/null
env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/scratch_flag.sh" clear >/dev/null
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/scratch_flag.sh" status)"
[ "$out" = "none" ] && ok || bad "status after clear" "expected 'none', got '$out'"
env HOME="$FAKEHOME" bash "$HOOKS/scratch_flag.sh" wibble >/dev/null 2>&1
[ "$?" = 2 ] && ok || bad "unknown verb" "expected exit 2"

echo "── altitude_flag.sh: set / status / clear, and its divergent quirks ──────"
SID="sess-delta"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/altitude_flag.sh" status)"
[ "$out" = "none" ] && ok || bad "status before set" "expected 'none', got '$out'"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/altitude_flag.sh" set --10k "the goal")"
printf '%s' "$out" | grep -q "10,000 — the goal" && ok || bad "set --10k output" "$out"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/altitude_flag.sh" status)"
printf '%s' "$out" | grep -q "^10k=the goal$" && ok || bad "status shows 10k only" "$out"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/altitude_flag.sh" set --5k "the seam")"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/altitude_flag.sh" status)"
printf '%s' "$out" | grep -q "^10k=the goal$" && ok || bad "partial set PRESERVES the other rung" "10k rung was lost: $out"
printf '%s' "$out" | grep -q "^5k=the seam$" && ok || bad "partial set writes the new rung" "$out"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="sess-epsilon" bash "$HOOKS/altitude_flag.sh" status)"
[ "$out" = "none" ] && ok || bad "session-mismatch status" "another session saw the rungs: '$out'"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/altitude_flag.sh" set 2>&1)"
rc=$?
[ "$rc" = 0 ] && ok || bad "'set' with nothing to set still exits 0 (degrade-safe)" "expected exit 0, got $rc"
env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/altitude_flag.sh" clear >/dev/null
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/altitude_flag.sh" status)"
[ "$out" = "none" ] && ok || bad "status after clear" "expected 'none', got '$out'"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKS/altitude_flag.sh" wibble 2>&1)"
rc=$?
[ "$rc" = 0 ] && ok || bad "unknown verb is degrade-safe here (unlike the other four)" "expected exit 0, got $rc"

echo "── shared library: FAIL LOUD when it is missing or broken (D6 condition 3) ─"
BROKEN="$SANDBOX/broken-hooks"
rm -rf "$BROKEN"; cp -R "$HOOKS" "$BROKEN"
rm -f "$BROKEN/lib/flag.sh"
for s in skill_anchor.sh scratch_flag.sh altitude_flag.sh numbers_flag.sh throughline_flag.sh; do
  out="$(env HOME="$FAKEHOME" bash "$BROKEN/$s" status 2>&1)"
  rc=$?
  if [ "$rc" != 0 ] && printf '%s' "$out" | grep -qi "FATAL"; then ok
  else bad "$s fails loud when lib is MISSING" "expected non-zero exit + FATAL stderr, got exit=$rc: $out"; fi
done
printf '#!/usr/bin/env bash\n# corrupt: no functions defined\ntrue\n' > "$BROKEN/lib/flag.sh"
for s in skill_anchor.sh scratch_flag.sh altitude_flag.sh numbers_flag.sh throughline_flag.sh; do
  out="$(env HOME="$FAKEHOME" bash "$BROKEN/$s" status 2>&1)"
  rc=$?
  if [ "$rc" != 0 ] && printf '%s' "$out" | grep -qi "FATAL"; then ok
  else bad "$s fails loud when lib is CORRUPT" "expected non-zero exit + FATAL stderr, got exit=$rc: $out"; fi
done

echo "── the library path is resolved relative to the shim, not hardcoded (D6 condition 5) ─"
# Copy hooks (with a real lib) to a path containing a space, and confirm it still works —
# proof the resolution is quoted, since the notes root and the plugin cache path both have spaces.
SPACED="$SANDBOX/a path with spaces/hooks"
mkdir -p "$(dirname "$SPACED")"
cp -R "$HOOKS" "$SPACED"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="sess-spaced" bash "$SPACED/numbers_flag.sh" arm 2>&1)"
printf '%s' "$out" | grep -q "^ARMED: numbers-mode" && ok || bad "shim works from a path containing spaces" "$out"

echo
if [ "$fail" = 0 ]; then echo "RESULT: $pass passed, 0 failed."; echo "FLAG LIB GREEN"; exit 0
else echo "RESULT: $pass passed, $fail failed."; exit 1; fi
