#!/bin/bash
# test_hook_sop_read_guard.sh — guard_hook_sop_read.sh: the hook plane's own SOP-receipt gate.
#
# ⭐ THE CASE THIS SUITE EXISTS FOR, measured 2026-09-15: an Edit/Bash write to
# ~/.claude/plans/lifehack-migration.plan.md — a PLAN file, nowhere near the hook plane — was
# BLOCKED because the TEXT being written to it contained the string "system/hooks/". Traced to
# the WRITE-VERB argument scan inside this guard's Bash path: shlex has no concept of a bash
# heredoc (`<< 'EOF' ... EOF`), so `tee <plan path> << 'EOF' ... this plan touches system/hooks/
# ... EOF` tokenizes with the heredoc BODY glued onto tee's own argv, and the mere MENTION of a
# hooks path inside that body tripped `any(HOOK.search(a) for a in args)`. The fix trims `args`
# at the first heredoc operator token (`<<`/`<<-`) before that scan runs, in
# system/hooks/guard_hook_sop_read.sh's `_trim_heredoc()`.
#
# Deny = exit 2. Allow = exit 0. Per the hook SOP: ALLOW cases come first.
# Run: bash system/hooks/tests/test_hook_sop_read_guard.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$HOOKS/../.." && pwd)"
GUARD="$HOOKS/guard_hook_sop_read.sh"
[ -f "$GUARD" ] || { echo "CANNOT RUN: no hook at $GUARD"; exit 1; }

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

# A fresh, never-seen session_id per invocation -- guarantees no stale SOP receipt exists for it,
# so a DENY case reliably hits the real deny (exit 2), never the CANNOT-DETERMINE path (exit 3).
_sid() { python3 -c "import uuid; print(uuid.uuid4())"; }

# run_bash <label> <expected-rc> <command>
run_bash() {
  local label="$1" exp="$2" cmd="$3" got
  python3 -c "
import json,sys
print(json.dumps({'tool_name':'Bash','tool_input':{'command':sys.argv[1]},'session_id':sys.argv[2]}))" \
    "$cmd" "$(_sid)" \
    | env CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" >/dev/null 2>&1
  got=$?
  [ "$got" = "$exp" ] && ok || bad "$label" "expected exit $exp, got $got"
}

# run_write <label> <expected-rc> <tool> <file_path>
run_write() {
  local label="$1" exp="$2" tool="$3" path="$4" got
  python3 -c "
import json,sys
print(json.dumps({'tool_name':sys.argv[2],'tool_input':{'file_path':sys.argv[1]},'session_id':sys.argv[3]}))" \
    "$path" "$tool" "$(_sid)" \
    | env CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" >/dev/null 2>&1
  got=$?
  [ "$got" = "$exp" ] && ok || bad "$label" "expected exit $exp, got $got"
}

echo "── ALLOW: ⭐ the false positive, fixed — a heredoc BODY merely mentions system/hooks/ ────"
run_bash "plan file authored via heredoc mentioning a hooks path in its own content" \
  0 "tee $HOME/.claude/plans/lifehack-migration.plan.md << 'EOF'
This plan covers migrating system/hooks/guard_egress.sh to the new layout.
EOF"

echo "── ALLOW: ordinary read-shaped and non-hook traffic ─────────────────────────────────────"
run_bash "cat a hook (read-shaped)"        0 "cat $REPO/system/hooks/guard_egress.sh"
run_bash "git checkout a hook"             0 "git checkout $REPO/system/hooks/guard_egress.sh"
run_bash "no hooks path mentioned at all"  0 "tee $HOME/.claude/plans/other.plan.md << 'EOF'
just an ordinary plan, no mentions here.
EOF"
run_write "Write a plan file"              0 "Write" "$HOME/.claude/plans/lifehack-migration.plan.md"
run_write "Edit a hook test"               0 "Edit"  "$REPO/system/hooks/tests/test_new_thing.sh"

echo "── DENY: true positives are still caught (no weakening) ─────────────────────────────────"
run_bash "chmod on a real hook, no receipt"            2 "chmod 644 $REPO/system/hooks/guard_egress.sh"
run_bash "redirect write into a hook via >"            2 "cat > $REPO/system/hooks/malicious.sh << 'EOF'
payload
EOF"
run_bash "heredoc write whose TARGET (not body) is a hook" \
  2 "tee $REPO/system/hooks/malicious.sh << 'EOF'
payload
EOF"
run_write "Edit a hook directly"                        2 "Edit" "$REPO/system/hooks/guard_egress.sh"
run_write "Write a brand-new hook file"                 2 "Write" "$REPO/system/hooks/guard_invented.sh"

echo
if [ "$fail" = 0 ]; then echo "RESULT: $pass passed, 0 failed."; echo "HOOK-SOP-READ GUARD GREEN"; exit 0
else echo "RESULT: $pass passed, $fail failed."; exit 1; fi
