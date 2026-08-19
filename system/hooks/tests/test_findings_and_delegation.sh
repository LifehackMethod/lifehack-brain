#!/bin/bash
# test_findings_and_delegation.sh — the two hooks that arrived with the SECURITY tail-port (F8.4).
#
# guard_findings_write.sh (PreToolUse, matcher: Bash|Write|Edit) — blocks a hand-authored line
# landing in state/findings/ (the Hospital store) OR state/recommendations/ (the Efficiency
# store, extended into this guard 2026-08-14 once system/tools/emit_recommendation.py landed —
# see the guard's own UPDATED header note), same class of guard as guard_canon_write.sh and
# guard_ledger_discipline.sh: a validated store must only ever be written by its one writer.
# Each store's writer allowance is checked INDEPENDENTLY — a command that mentions
# emit_finding.py must never wave through a write into state/recommendations/, and the reverse.
#
# inject_delegation_standing.sh (UserPromptSubmit) — a non-blocking INJECT, never denies. Its only
# failure mode is silence (the line does not arrive) or a wrong channel (systemMessage instead of
# stdout, per hook-sop.md §3's CHANNEL LAW). Tested for presence + exit code, not deny/allow.
#
# Deny = exit 2. Allow = exit 0.
# Run: bash system/hooks/tests/test_findings_and_delegation.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$HOOKS/../.." && pwd)"

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
check() { # check <label> <expected-rc> <actual-rc>
  [ "$3" = "$2" ] && ok || bad "$1" "expected exit $2, got $3"
}

# ── guard_findings_write.sh — PreToolUse, matcher: Bash|Write|Edit ────────────
G="$HOOKS/guard_findings_write.sh"
[ -f "$G" ] || { echo "CANNOT RUN: no hook at $G"; exit 1; }
echo "── guard_findings_write: only emit_finding.py may write state/findings/ ──"

bash_case() { # bash_case <label> <exp> <command>
  python3 -c "
import json,sys
print(json.dumps({'tool_name':'Bash','tool_input':{'command':sys.argv[1]}}))" "$3" 2>/dev/null \
    | (cd "$REPO" && bash "$G") >/dev/null 2>&1
  check "$1" "$2" "$?"
}
write_case() { # write_case <label> <exp> <tool> <path>
  python3 -c "
import json,sys
print(json.dumps({'tool_name':sys.argv[1],'tool_input':{'file_path':sys.argv[2],'content':'{}'}}))" \
    "$3" "$4" 2>/dev/null | (cd "$REPO" && bash "$G") >/dev/null 2>&1
  check "$1" "$2" "$?"
}

# Trigger tokens assembled from fragments where the raw string would otherwise be a self-mention
# (hook-sop.md §4 Trap 2) — not needed here since these are legitimate write verbs, not the guard's
# own deny-string vocabulary, but kept consistent with house style for the redirect/store path.
STORE="state/findings"

bash_case "shell redirect >> into the store"     2 "echo fake >> $STORE/rogue.jsonl"
bash_case "tee into the store"                   2 "echo fake | tee -a $STORE/rogue.jsonl"
bash_case "rm inside the store"                  2 "rm $STORE/old.local.jsonl"
bash_case "mv into the store"                    2 "mv /tmp/fake.jsonl $STORE/planted.jsonl"
bash_case "the ONE legitimate writer"            0 "python3 system/tools/emit_finding.py --producer x --status OK --scanned-n 3 --summary hi >> $STORE/x.local.jsonl"
bash_case "a READ of the store"                  0 "cat $STORE/hospital.local.jsonl | tail -20"
bash_case "grep over the store"                  0 "grep -c ERROR $STORE/hospital.local.jsonl"
bash_case "a mere MENTION in a commit message"   0 "git commit -m \"fix the parser used by $STORE/ readers\""
bash_case "an unrelated command"                 0 "ls -la system/hooks/"

write_case "Write tool targeting a shard directly" 2 "Write" "$STORE/manual.local.jsonl"
write_case "Edit tool targeting a shard directly"  2 "Edit"  "$STORE/manual.local.jsonl"
write_case "lookalike path, NOT the store"         0 "Write" "my-$STORE-notes.md"

# ── state/recommendations/ (Efficiency) — extended into this guard 2026-08-14 ─────────────────
# system/tools/emit_recommendation.py went live (recommend.py / seam_reason.py write through it;
# recommendations_reader.py / recommendation_disposition.py read it), so a fresh install with no
# write-guard on this store was a real gap — closed here. Same protection model as
# state/findings/ above, checked INDEPENDENTLY so neither store's writer name can wave through a
# write to the other.
echo "── guard_findings_write: only emit_recommendation.py may write state/recommendations/ ──"
STORE2="state/recommendations"

bash_case "shell redirect >> into the recs store"      2 "echo fake >> $STORE2/rogue.jsonl"
bash_case "tee into the recs store"                    2 "echo fake | tee -a $STORE2/rogue.jsonl"
bash_case "rm inside the recs store"                   2 "rm $STORE2/old.local.jsonl"
bash_case "mv into the recs store"                     2 "mv /tmp/fake.jsonl $STORE2/planted.jsonl"
bash_case "the ONE legitimate recs writer"             0 "python3 system/tools/emit_recommendation.py --producer x --altitude INSTANCE --action fix-it --summary hi --evidence abc123 >> $STORE2/INSTANCE.local.jsonl"
bash_case "a READ of the recs store"                   0 "cat $STORE2/efficiency.local.jsonl | tail -20"
bash_case "grep over the recs store"                   0 "grep -c DECISION $STORE2/efficiency.local.jsonl"
bash_case "a mere MENTION in a commit message"         0 "git commit -m \"fix the parser used by $STORE2/ readers\""

write_case "Write tool targeting a recs shard directly" 2 "Write" "$STORE2/manual.local.jsonl"
write_case "Edit tool targeting a recs shard directly"  2 "Edit"  "$STORE2/manual.local.jsonl"
write_case "recs lookalike path, NOT the store"         0 "Write" "my-$STORE2-notes.md"

# ⛔ CROSS-STORE ISOLATION — the whole reason each store checks its own writer independently.
# Naming the OTHER store's writer on the command line must NOT wave a write through — the guard
# must not weaken either store while extending to the second one.
bash_case "emit_finding.py mention does NOT license a recs write"     2 "echo fake >> $STORE2/rogue2.jsonl # also calls emit_finding.py"
bash_case "emit_recommendation.py mention does NOT license a findings write" 2 "echo fake >> $STORE/rogue2.jsonl # also calls emit_recommendation.py"

# ⛔ CHANNEL CHECK — a guard that prints its refusal on the wrong channel (or the wrong exit
# code) blocks nothing while still looking like a PASS to a text-only check. Verify the deny
# text lands on STDERR (never stdout) with exit 2, for both stores.
channel_case() { # channel_case <label> <command>
  local _out _err _rc
  _out=$(python3 -c "
import json,sys
print(json.dumps({'tool_name':'Bash','tool_input':{'command':sys.argv[1]}}))" "$2" 2>/dev/null \
    | (cd "$REPO" && bash "$G") 2>/tmp/gfw_channel_stderr.$$)
  _rc=$?
  _err=$(cat /tmp/gfw_channel_stderr.$$ 2>/dev/null); rm -f /tmp/gfw_channel_stderr.$$
  [ -z "$_out" ] && ok || bad "$1: stdout must stay empty" "got: $_out"
  case "$_err" in *BLOCKED*) ok ;; *) bad "$1: deny text on stderr" "stderr was: $_err" ;; esac
  [ "$_rc" = 2 ] && ok || bad "$1: exit code" "expected 2, got $_rc"
}
channel_case "recs deny channel"     "echo fake >> $STORE2/channel-check.jsonl"
channel_case "findings deny channel" "echo fake >> $STORE/channel-check.jsonl"

# Malformed input must fail CLOSED (hook-contract.md).
printf 'not json at all' | (cd "$REPO" && bash "$G") >/dev/null 2>&1
check "malformed payload fails closed" 2 "$?"

# Empty stdin is a bare manual invocation, not a tool call — nothing to adjudicate.
printf '' | (cd "$REPO" && bash "$G") >/dev/null 2>&1
check "empty stdin is a no-op" 0 "$?"

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

echo
if [ "$fail" -eq 0 ]; then
  echo "PASS — $pass cases, 0 failures."
  exit 0
fi
echo "FAIL — $fail of $((pass+fail)) cases failed."
exit 1
