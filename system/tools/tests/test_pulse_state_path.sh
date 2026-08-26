#!/bin/bash
# test_pulse_state_path.sh — pulse.sh must resolve the SAME state file no matter which shell calls
# it, cron or interactive.
#
# THE BUG THIS GUARDS (found 2026-08-26 during a completion audit): pulse.sh used to default STATE
# to "${TMPDIR:-/tmp}/lifehack-pulse-state.json". On macOS, cron's environment carries no TMPDIR (so
# it falls back to /tmp), while an interactive Terminal gets a per-user launchd-assigned
# /var/folders/.../T path — two DIFFERENT directories on the SAME machine. `pulse.sh --status` run by
# hand read the interactive path, saw a stale-or-missing file, and reported every scheduled job as
# days overdue when the real (cron-written) state showed the schedule healthy. A status tool reporting
# a false alarm is exactly the failure this test exists to catch before it ships again.
#
# Run: bash system/tools/tests/test_pulse_state_path.sh   (exit 0 = pass)

HERE="$(cd "$(dirname "$0")/.." && pwd)"           # .../system/tools
PULSE="$HERE/pulse.sh"
[ -f "$PULSE" ] || { echo "CANNOT RUN: no pulse.sh at $PULSE"; exit 1; }

# Point PULSE_CONFIG at an empty manifest so --status has nothing real to touch, and isolate PARK_FILE
# from the real notes root (NOTES_ROOT resolution is untouched by this fix and irrelevant to it).
SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/pulsestatetest.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
cat > "$SANDBOX/empty-config.md" <<'EOF'
```crontab
```
EOF

pass=0; fail=0
check() { if [ "$2" = "$3" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL: $1 — expected [$3] got [$2]"; fi; }

# 1) Interactive-shaped env (a real per-user TMPDIR set) vs cron-shaped env (TMPDIR unset) must
#    resolve to the IDENTICAL default state path.
out_interactive="$(TMPDIR="/tmp/fake-per-user-launchd-dir" PULSE_CONFIG="$SANDBOX/empty-config.md" bash "$PULSE" --status 2>&1 | head -1)"
out_cron="$(env -u TMPDIR PULSE_CONFIG="$SANDBOX/empty-config.md" bash "$PULSE" --status 2>&1 | head -1)"

state_interactive="$(echo "$out_interactive" | grep -o 'state=[^ )]*')"
state_cron="$(echo "$out_cron" | grep -o 'state=[^ )]*')"

check "default STATE path is TMPDIR-invariant (interactive vs cron env)" "$state_interactive" "$state_cron"

# 2) An explicit PULSE_STATE override must still win over the default resolution either way.
override="$SANDBOX/explicit-state.json"
out_override="$(TMPDIR="/tmp/fake-per-user-launchd-dir" PULSE_STATE="$override" PULSE_CONFIG="$SANDBOX/empty-config.md" bash "$PULSE" --status 2>&1 | head -1)"
state_override="$(echo "$out_override" | grep -o 'state=[^ )]*')"
check "explicit PULSE_STATE override still wins" "$state_override" "state=$override"

echo "pulse state-path: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
