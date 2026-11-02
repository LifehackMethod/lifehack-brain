#!/bin/bash
# test_ledger_discipline.sh — system/hooks/guard_ledger_discipline.sh.
#
# The guard enforces the 2026-06-18 drain rule: the ## Open section of
# state/debt-ledger.md is DELETION-ONLY; ADDING a status-annotation line
# (✅ / RESOLVED / CLEARED / FIXED) there is a deny (exit 2).
#
# THE BUG this file pins (found by the observation-check layer_firing signal, 2026-11-02): a
# payload whose tool_input is not a dict (observed in real traffic as a plain string),
# or whose top level is not a JSON object, crashed the embedded python with an
# AttributeError and the hook exited 1 — an ERROR, not an allow. The header's SCOPING
# NOTE promises the opposite: "On any parse failure or non-ledger target it exits 0
# (allow) — a bug here must NEVER block the whole edit surface". Exit 1 also trips the
# observation-check layer_firing check (exit_code not in (0, 2) = red). Every malformed-payload
# shape below must therefore exit 0.
#
# Deny = exit 2. Allow = exit 0. Run: bash system/hooks/tests/test_ledger_discipline.sh

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$HOOKS/../.." && pwd)"
G="$HOOKS/guard_ledger_discipline.sh"
[ -f "$G" ] || { echo "CANNOT RUN: no hook at $G"; exit 1; }

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
check() { # check <label> <expected-rc> <actual-rc>
  [ "$3" = "$2" ] && ok || bad "$1" "expected exit $2, got $3"
}

# The guard must never write to the real fire journal from a test.
export LHB_JOURNAL_PATH="$(mktemp -d)/journal.jsonl"
trap 'rm -rf "$(dirname "$LHB_JOURNAL_PATH")"' EXIT

LEDGER_DIR="$(mktemp -d)"
LEDGER="$LEDGER_DIR/state/debt-ledger.md"
mkdir -p "$(dirname "$LEDGER")"

run_guard() { # run_guard <payload-file> -> exit code
  (cd "$REPO" && bash "$G" < "$1") >/dev/null 2>&1
  echo $?
}

payload() { # payload <file> <json>
  printf '%s' "$2" > "$1"
}

echo "── guard_ledger_discipline: the drain rule itself ──"

# A real ledger: two open items.
cat > "$LEDGER" <<'MD'
# Debt ledger

## Open
- item one: the pond gate sticks
- item two: the frog count is stale

## Cleared
- 2026-06-18 drained the backlog
MD

# json_payload <file> <tool> <python-dict-literal of tool_input>
json_payload() {
  python3 -c '
import json, sys
print(json.dumps({"tool_name": sys.argv[1], "tool_input": eval(sys.argv[2])}))' "$2" "$3" > "$1"
}

# 1. Write that ADDS a status annotation to ## Open -> DENY.
json_payload "$LEDGER_DIR/p1" Write "{'file_path': '$LEDGER', 'content': '# Debt ledger\n\n## Open\n- item one ✅ RESOLVED\n\n## Cleared\n'}"
check "write adds annotation -> deny" 2 "$(run_guard "$LEDGER_DIR/p1")"

# 2. Write to the ledger that only DELETES a line (no annotation) -> ALLOW.
json_payload "$LEDGER_DIR/p2" Write "{'file_path': '$LEDGER', 'content': '# Debt ledger\n\n## Open\n- item two: the frog count is stale\n\n## Cleared\n'}"
check "write deletes a line -> allow" 0 "$(run_guard "$LEDGER_DIR/p2")"

# 3. Non-ledger write -> ALLOW (scoping).
json_payload "$LEDGER_DIR/p3" Write "{'file_path': '$LEDGER_DIR/other.md', 'content': '✅ RESOLVED'}"
check "non-ledger target -> allow" 0 "$(run_guard "$LEDGER_DIR/p3")"

# 4. Annotation under ## Cleared is legal -> ALLOW.
json_payload "$LEDGER_DIR/p4" Edit "{'file_path': '$LEDGER', 'old_string': '## Cleared', 'new_string': '## Cleared\n- 2026-11-02 item one FIXED, moved from Open'}"
check "annotation under Cleared -> allow" 0 "$(run_guard "$LEDGER_DIR/p4")"

echo "── malformed payloads: must ALLOW (exit 0), never error (exit 1) ──"

# 5. THE REGRESSION: tool_input is a plain string, not a dict.
payload "$LEDGER_DIR/p5" '{"tool_name":"Write","tool_input":"/notes/state/debt-ledger.md"}'
check "tool_input is a string -> allow" 0 "$(run_guard "$LEDGER_DIR/p5")"

# 6. tool_input is a list.
payload "$LEDGER_DIR/p6" '{"tool_name":"Edit","tool_input":["a","b"]}'
check "tool_input is a list -> allow" 0 "$(run_guard "$LEDGER_DIR/p6")"

# 7. Top level is a JSON array, not an object.
payload "$LEDGER_DIR/p7" '["tool_name","Write"]'
check "payload is an array -> allow" 0 "$(run_guard "$LEDGER_DIR/p7")"

# 8. tool_input is a bare number.
payload "$LEDGER_DIR/p8" '{"tool_name":"Write","tool_input":42}'
check "tool_input is a number -> allow" 0 "$(run_guard "$LEDGER_DIR/p8")"

echo "── pass=$pass fail=$fail"
[ "$fail" = 0 ] || exit 1
exit 0
