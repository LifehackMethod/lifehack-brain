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

# Tests 1-2 are pure path-resolution checks and must never touch this machine's REAL old-location
# files (a real /tmp/lifehack-pulse-state.json legitimately exists on an install with a live cron
# job) — a real migration firing mid-assertion would make the FIRST line of output "migrated state
# ..." instead of the heartbeat line these checks grep for. Isolate with a throwaway HOME (so
# cache_dir() lands in a sandbox) AND point both old-location envs at paths that never exist.
H12="$(mktemp -d "${TMPDIR:-/tmp}/pulsehome12.XXXXXX")"

# 1) Interactive-shaped env (a real per-user TMPDIR set) vs cron-shaped env (TMPDIR unset) must
#    resolve to the IDENTICAL default state path.
out_interactive="$(HOME="$H12" TMPDIR="/tmp/fake-per-user-launchd-dir" _PULSE_OLD_CRON_STATE="/nonexistent-cron-state.json" _PULSE_OLD_INTERACTIVE_STATE="/nonexistent-interactive-state.json" PULSE_CONFIG="$SANDBOX/empty-config.md" bash "$PULSE" --status 2>&1 | head -1)"
out_cron="$(HOME="$H12" env -u TMPDIR _PULSE_OLD_CRON_STATE="/nonexistent-cron-state.json" _PULSE_OLD_INTERACTIVE_STATE="/nonexistent-interactive-state.json" PULSE_CONFIG="$SANDBOX/empty-config.md" bash "$PULSE" --status 2>&1 | head -1)"

state_interactive="$(echo "$out_interactive" | grep -o 'state=[^ )]*')"
state_cron="$(echo "$out_cron" | grep -o 'state=[^ )]*')"

check "default STATE path is TMPDIR-invariant (interactive vs cron env)" "$state_interactive" "$state_cron"

# 2) An explicit PULSE_STATE override must still win over the default resolution either way.
override="$SANDBOX/explicit-state.json"
out_override="$(HOME="$H12" TMPDIR="/tmp/fake-per-user-launchd-dir" PULSE_STATE="$override" _PULSE_OLD_CRON_STATE="/nonexistent-cron-state.json" _PULSE_OLD_INTERACTIVE_STATE="/nonexistent-interactive-state.json" PULSE_CONFIG="$SANDBOX/empty-config.md" bash "$PULSE" --status 2>&1 | head -1)"
state_override="$(echo "$out_override" | grep -o 'state=[^ )]*')"
check "explicit PULSE_STATE override still wins" "$state_override" "state=$override"

# ── Migration coverage (added after the 2026-08-26 disclosure: the fix above MOVES the default
# state path but, on its own, does not MIGRATE it — the real file carries breaker keys
# (fails:/disabled:/trips:/retry_at:), not just last-run timestamps, and starting the new location
# empty silently revives a deliberately-disabled job and forgets its backoff). ──────────────────────
#
# Each sub-test gets its own throwaway $HOME so shared/paths.py's cache_dir() (which honours $HOME
# via os.path.expanduser) resolves under a sandbox instead of the real ~/Library/Caches — this
# exercises the TRUE default-resolution + migration path without ever touching the operator's real
# cache or real /tmp state.

# 3) A populated OLD cron-location file migrates into the new location, breaker keys intact.
H3="$(mktemp -d "${TMPDIR:-/tmp}/pulsehome3.XXXXXX")"
OLDCRON3="$(mktemp -d "${TMPDIR:-/tmp}/pulseold3.XXXXXX")/old-cron-state.json"
cat > "$OLDCRON3" <<'EOF'
{"system-health": 1787574041, "fails:system-health": 0, "disabled:bootstrap-sync": 1, "retry_at:bootstrap-sync": 1787835869, "trips:bootstrap-sync": 3}
EOF
HOME="$H3" _PULSE_OLD_CRON_STATE="$OLDCRON3" _PULSE_OLD_INTERACTIVE_STATE="/nonexistent-interactive-state.json" \
  PULSE_CONFIG="$SANDBOX/empty-config.md" bash "$PULSE" --status >/dev/null 2>&1
NEWSTATE3="$(HOME="$H3" python3 "$HERE/../../shared/paths.py" cache pulse 2>/dev/null)/lifehack-pulse-state.json"
disabled_val="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('disabled:bootstrap-sync','MISSING'))" "$NEWSTATE3" 2>/dev/null)"
retry_val="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('retry_at:bootstrap-sync','MISSING'))" "$NEWSTATE3" 2>/dev/null)"
check "migration carries disabled:bootstrap-sync breaker key" "$disabled_val" "1"
check "migration carries retry_at:bootstrap-sync breaker key" "$retry_val" "1787835869"
[ -e "$OLDCRON3" ] && old_survived3=yes || old_survived3=no
check "old cron-location file left in place (copy, never move)" "$old_survived3" "yes"

# 4) When BOTH old locations exist, /tmp (cron's real one) wins over the interactive copy.
H4="$(mktemp -d "${TMPDIR:-/tmp}/pulsehome4.XXXXXX")"
OLDCRON4="$(mktemp -d "${TMPDIR:-/tmp}/pulseoldcron4.XXXXXX")/cron-state.json"
OLDINT4="$(mktemp -d "${TMPDIR:-/tmp}/pulseoldint4.XXXXXX")/interactive-state.json"
echo '{"marker": "from-cron"}' > "$OLDCRON4"
echo '{"marker": "from-interactive"}' > "$OLDINT4"
HOME="$H4" _PULSE_OLD_CRON_STATE="$OLDCRON4" _PULSE_OLD_INTERACTIVE_STATE="$OLDINT4" \
  PULSE_CONFIG="$SANDBOX/empty-config.md" bash "$PULSE" --status >/dev/null 2>&1
NEWSTATE4="$(HOME="$H4" python3 "$HERE/../../shared/paths.py" cache pulse 2>/dev/null)/lifehack-pulse-state.json"
marker4="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('marker','MISSING'))" "$NEWSTATE4" 2>/dev/null)"
check "when both old locations exist, /tmp (cron) wins" "$marker4" "from-cron"

# 5) Idempotence: running twice must NOT let stale old-location data clobber fresh new-location state.
H5="$(mktemp -d "${TMPDIR:-/tmp}/pulsehome5.XXXXXX")"
OLDCRON5="$(mktemp -d "${TMPDIR:-/tmp}/pulseold5.XXXXXX")/old-cron-state.json"
echo '{"marker": "stale-old-value"}' > "$OLDCRON5"
HOME="$H5" _PULSE_OLD_CRON_STATE="$OLDCRON5" _PULSE_OLD_INTERACTIVE_STATE="/nonexistent-interactive-state.json" \
  PULSE_CONFIG="$SANDBOX/empty-config.md" bash "$PULSE" --status >/dev/null 2>&1
NEWSTATE5="$(HOME="$H5" python3 "$HERE/../../shared/paths.py" cache pulse 2>/dev/null)/lifehack-pulse-state.json"
# Mutate the now-migrated new-location file to a value the OLD file never had, simulating a real
# job run that updated state since the migration.
python3 -c "
import json
p = '$NEWSTATE5'
d = json.load(open(p))
d['marker'] = 'fresh-value-after-a-real-run'
json.dump(d, open(p, 'w'))
"
# Second invocation: old file (still 'stale-old-value') must NOT overwrite the fresh marker.
HOME="$H5" _PULSE_OLD_CRON_STATE="$OLDCRON5" _PULSE_OLD_INTERACTIVE_STATE="/nonexistent-interactive-state.json" \
  PULSE_CONFIG="$SANDBOX/empty-config.md" bash "$PULSE" --status >/dev/null 2>&1
marker5="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('marker','MISSING'))" "$NEWSTATE5" 2>/dev/null)"
check "second run is idempotent — does not clobber fresh state with stale old data" "$marker5" "fresh-value-after-a-real-run"

# 6) Fail-safe: if the copy step itself fails, the cycle must refuse to run rather than proceed as
#    though state were fresh (a bad source path — e.g. unreadable/absent — is simulated by pointing
#    the "old cron" location at a directory, which `cp` (no -r) refuses to copy).
H6="$(mktemp -d "${TMPDIR:-/tmp}/pulsehome6.XXXXXX")"
BADSRC6="$(mktemp -d "${TMPDIR:-/tmp}/pulsebadsrc6.XXXXXX")"   # a directory, not a file — cp fails
HOME="$H6" _PULSE_OLD_CRON_STATE="$BADSRC6" _PULSE_OLD_INTERACTIVE_STATE="/nonexistent-interactive-state.json" \
  PULSE_CONFIG="$SANDBOX/empty-config.md" bash "$PULSE" --status >/dev/null 2>&1
rc6=$?
NEWSTATE6="$(HOME="$H6" python3 "$HERE/../../shared/paths.py" cache pulse 2>/dev/null)/lifehack-pulse-state.json"
[ -e "$NEWSTATE6" ] && new6_exists=yes || new6_exists=no
check "failed migration exits non-zero (refuses the cycle)" "$rc6" "1"
check "failed migration does NOT leave a fresh/empty new-location file behind" "$new6_exists" "no"

echo "pulse state-path: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
