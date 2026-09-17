#!/bin/bash
# test_checkin_save_seam.sh — K6-DESIGN-SPEC.md §3: proof that a value travels the WHOLE
# checkin->save seam (F13, skill-building-sop.md:936-937), plus the proven-fail case (F4,
# skill-building-sop.md:900-901): a corrupt or expired receipt makes save's own fallback fire, and
# NEVER reads garbage as a project. And the kill line this whole card turns on: this seam is
# ADVISORY/INFORMATIONAL ONLY (R9/R34) — it must NEVER deny anything, on any path.
#
# What this exercises: `system/hooks/step_receipt.sh`, the exact CLI both phase files call —
# `.claude/skills/checkin/phases/3-propose.md` step 3.65 (write) and
# `.claude/skills/save/phases/session-close.md` SC-0 (read). Not a simulation of those markdown
# files — the literal same commands, so this suite breaks the moment either snippet's contract
# changes, instead of drifting silently alongside a hand-copied re-implementation.
#
# Run: bash system/hooks/tests/test_checkin_save_seam.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
RECEIPT="$HOOKS/step_receipt.sh"
[ -f "$RECEIPT" ] || { echo "CANNOT RUN: no script at $RECEIPT"; exit 1; }

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
check() { [ "$3" = "$2" ] && ok || bad "$1" "expected exit $2, got $3"; }

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/checkin-save-seam.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
mkdir -p "$SANDBOX/fakehome"
SESS="seam-test-$$"

# ─────────────────────────────────────────────────────────────────────────────────────────────
echo "── (1) a value travels the whole seam — write, then read back IDENTICAL, not 'a flag exists' ──"

SLUG="enforcement-layer-k6-seam-test"
DOC="/fake/path/to/enforcement-layer.brief.md"

OUT="$(CLAUDE_CODE_SESSION_ID="$SESS" HOME="$SANDBOX/fakehome" bash "$RECEIPT" write checkin \
  slug="$SLUG" doc_path="$DOC")"
RC=$?
check "write exits 0" 0 "$RC"
printf '%s' "$OUT" | grep -q "RECEIPT WRITTEN: checkin" && ok || bad "write output" "missing confirmation line: $OUT"

READBACK="$(CLAUDE_CODE_SESSION_ID="$SESS" HOME="$SANDBOX/fakehome" bash "$RECEIPT" read checkin slug doc_path)"
RC=$?
check "read exits 0 on a good receipt" 0 "$RC"

GOT_SLUG="$(printf '%s\n' "$READBACK" | grep '^slug=' | cut -d= -f2-)"
GOT_DOC="$(printf '%s\n' "$READBACK" | grep '^doc_path=' | cut -d= -f2-)"
[ "$GOT_SLUG" = "$SLUG" ] && ok || bad "slug round-trip" "wrote '$SLUG', read back '$GOT_SLUG'"
[ "$GOT_DOC" = "$DOC" ] && ok || bad "doc_path round-trip" "wrote '$DOC', read back '$GOT_DOC'"

# ─────────────────────────────────────────────────────────────────────────────────────────────
echo
echo "── (2) proven-fail case — a CORRUPT receipt is rejected, never read as a real project ──"

SESS2="seam-test-corrupt-$$"
CLAUDE_CODE_SESSION_ID="$SESS2" HOME="$SANDBOX/fakehome" bash "$RECEIPT" write checkin \
  slug="real-slug" doc_path="/real/path.md" >/dev/null

# Find the actual flag file on disk and corrupt it directly — a partially-written / truncated /
# garbage-bytes receipt, exactly the shape a crash mid-write or a hand-edit would leave behind.
# The key is derived from the session id DIRECTLY when one is set (flag.sh: KEY="sess-$CLAUDE_CODE_SESSION_ID",
# no hashing) — find the file by the session= line it was just written with.
FLAGFILE="$(grep -rl "session=$SESS2" "$SANDBOX/fakehome/.claude/run/step-receipts/" 2>/dev/null | head -1)"
[ -n "$FLAGFILE" ] && [ -f "$FLAGFILE" ] || { bad "corrupt setup" "could not locate the written flag file to corrupt"; }

if [ -n "$FLAGFILE" ]; then
  # Corrupt it: truncate to garbage bytes with no well-formed field=value lines at all.
  printf '\x00\x01\x02 not a receipt at all %%%%%%' > "$FLAGFILE"

  CORRUPT_OUT="$(CLAUDE_CODE_SESSION_ID="$SESS2" HOME="$SANDBOX/fakehome" bash "$RECEIPT" read checkin slug doc_path)"
  RC=$?
  [ "$RC" -ne 0 ] && ok || bad "corrupt receipt must fail" "read exited 0 on a corrupt receipt — would have handed save garbage as a real project"
  printf '%s' "$CORRUPT_OUT" | grep -q "INVALID" && ok || bad "corrupt receipt verdict" "expected INVALID, got: $CORRUPT_OUT"
  # And prove it did NOT silently emit slug=/doc_path= lines a careless caller might use anyway.
  printf '%s' "$CORRUPT_OUT" | grep -q "^slug=" && bad "corrupt receipt leaked a field" "read printed slug= on a corrupt receipt" || ok
fi

# ─────────────────────────────────────────────────────────────────────────────────────────────
echo
echo "── (3) an EXPIRED receipt is treated as absent, not as a stale-but-usable value ──"

SESS3="seam-test-expired-$$"
CLAUDE_CODE_SESSION_ID="$SESS3" HOME="$SANDBOX/fakehome" bash "$RECEIPT" write checkin \
  slug="stale-slug" doc_path="/stale/path.md" >/dev/null

EXPIRED_OUT="$(CLAUDE_CODE_SESSION_ID="$SESS3" HOME="$SANDBOX/fakehome" STEP_RECEIPT_TTL_HOURS=0 \
  bash "$RECEIPT" read checkin slug doc_path)"
RC=$?
[ "$RC" -ne 0 ] && ok || bad "expired receipt must fail" "read exited 0 on an expired (TTL=0) receipt"
printf '%s' "$EXPIRED_OUT" | grep -q "EXPIRED" && ok || bad "expired receipt verdict" "expected EXPIRED, got: $EXPIRED_OUT"

# ─────────────────────────────────────────────────────────────────────────────────────────────
echo
echo "── (4) absent receipt (never written this session) — same non-blocking shape ──"

SESS4="seam-test-absent-$$"
ABSENT_OUT="$(CLAUDE_CODE_SESSION_ID="$SESS4" HOME="$SANDBOX/fakehome" bash "$RECEIPT" read checkin slug doc_path)"
RC=$?
[ "$RC" -ne 0 ] && ok || bad "absent receipt must fail" "read exited 0 with nothing ever written for this session"
printf '%s' "$ABSENT_OUT" | grep -q "ABSENT" && ok || bad "absent receipt verdict" "expected ABSENT, got: $ABSENT_OUT"

# ─────────────────────────────────────────────────────────────────────────────────────────────
echo
echo "── (5) the kill line: NEVER a hook deny, on any of the failure paths above ──"

# The house deny shape (system/hook-contract.md) is stderr text containing 'BLOCKED' + exit code 2.
# This seam must never produce either, on ANY read outcome — good, corrupt, expired, or absent.
for CASE_SESS in "$SESS2" "$SESS3" "$SESS4"; do
  RC="$(CLAUDE_CODE_SESSION_ID="$CASE_SESS" HOME="$SANDBOX/fakehome" STEP_RECEIPT_TTL_HOURS=0 \
    bash "$RECEIPT" read checkin slug doc_path >/dev/null 2>"$SANDBOX/stderr.txt"; echo $?)"
  [ "$RC" -eq 1 ] && ok || bad "non-hook exit code" "expected the plain exit 1 (never hook-deny's exit 2), got $RC for session $CASE_SESS"
  grep -qi "BLOCKED" "$SANDBOX/stderr.txt" && bad "no hook-deny text" "found 'BLOCKED' text on a read failure — this must never look like a hook deny" || ok
done

echo
echo "RESULT: $pass passed, $fail failed."
[ "$fail" -eq 0 ] && echo "CHECKIN->SAVE SEAM GREEN" || echo "CHECKIN->SAVE SEAM RED"
exit $([ "$fail" -eq 0 ] && echo 0 || echo 1)
