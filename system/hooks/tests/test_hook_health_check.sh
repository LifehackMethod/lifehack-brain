#!/bin/bash
# test_hook_health_check.sh -- hook_health_check.sh (SessionStart): runner check + unacknowledged alert shown until acked.
# Run: bash system/hooks/tests/test_hook_health_check.sh   (exit 0 = all pass)
HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
CHECK="${HOOK_UNDER_TEST:-$HOOKS/hook_health_check.sh}"
ACK="$HOOKS/../tools/hook_alert_ack.sh"
pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
export LIFEHACK_STATE_DIR="$T/state"
bash -n "$CHECK" && ok || bad syntax "fails bash -n"
bash -n "$ACK" && ok || bad ack-syntax "ack tool fails bash -n"
mk() { rm -rf "$T/h" "$T/state"; mkdir -p "$T/h/lib" "$T/state"; cp "$CHECK" "$T/h/hook_health_check.sh"; cp "$HOOKS/hook_runner.sh" "$T/h/hook_runner.sh"; }
run() { echo '{}' | bash "$T/h/hook_health_check.sh" 2>&1; }

mk; out=$(run); rc=$?
[ "$rc" = 0 ] && [ -z "$out" ] && ok || bad quiet "healthy runner and no alert must print nothing: rc=$rc out=$out"

mk; rm "$T/h/hook_runner.sh"; out=$(run); rc=$?
[ "$rc" = 0 ] && echo "$out" | grep -q 'HOOK ALERT' && echo "$out" | grep -q 'missing' && ok || bad runner-missing "rc=$rc out=$out"

mk; printf 'if true; then\n' > "$T/h/hook_runner.sh"; out=$(run); rc=$?
[ "$rc" = 0 ] && echo "$out" | grep -q 'HOOK ALERT' && ok || bad runner-broken "rc=$rc out=$out"

mk; printf '{"alert":"hook-runner","hook":"d.sh","what":"RESTORED-MARKER"}\n' > "$T/state/hooks-alert.json"
out=$(run); echo "$out" | grep -q 'unacknowledged' && echo "$out" | grep -q RESTORED-MARKER && ok || bad alert-shown "$out"
out=$(run); echo "$out" | grep -q RESTORED-MARKER && ok || bad alert-persists "alert must show on EVERY session until acknowledged"
bash "$ACK" >/dev/null 2>&1; out=$(run)
[ -z "$out" ] && ok || bad acked "still printing after acknowledge: $out"
ls "$T/state"/hooks-alert.acked.* >/dev/null 2>&1 && ok || bad ack-history "acknowledged alert was not kept"

echo "$pass passed, $fail failed"; [ "$fail" = 0 ]
