#!/bin/bash
# test_findings_and_delegation.sh — the two hooks that arrived with the SECURITY tail-port (F8.4).
#
# guard_findings_write.sh (PreToolUse, matcher: Bash|Write|Edit) — blocks a hand-authored line
# landing in state/findings/ (the Hospital store), same class of guard as guard_canon_write.sh and
# guard_ledger_discipline.sh: a validated store must only ever be written by its one writer.
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
# The donor's per-line attribution ("Enver, <date>") must not appear in the runtime-injected
# text — this repo's other ported injects already anonymize the text a model reads every turn.
case "$OUT" in
  *"Enver"*) bad "runtime text stays anonymous" "found 'Enver' in injected text" ;;
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
