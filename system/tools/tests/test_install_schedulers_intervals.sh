#!/usr/bin/env bash
# test_install_schedulers_intervals.sh -- canon cron-jobs-sop L81: a scheduled job may run at ANY interval.
# Proves install-schedulers.sh accepts a 600 s (10-minute) interval and emits a launchd StartInterval job,
# accepts other non-whole-hour intervals, and keeps the old whole-hour / whole-day StartCalendarInterval
# behaviour byte-for-byte, while still refusing < 60 s and non-numbers.
# Stubs only: no network, no real launchctl, nothing installed on this machine.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
T="$(mktemp -d "${TMPDIR:-/tmp}/tinst.XXXXXX")"; trap 'rm -rf "$T"' EXIT
FAILS=0
pass() { echo "$1 PASS"; }
fail() { echo "$1 FAIL ${2:-}"; FAILS=$((FAILS+1)); }

mkdir -p "$T/code/system/tools" "$T/home" "$T/bin"
printf '#!/usr/bin/env bash\necho ran n=1 items\n' > "$T/code/system/tools/ok-run.sh"
cat > "$T/bin/launchctl" <<'STUB'
#!/bin/bash
echo "launchctl $*" >> "$STUBLOG"
exit 0
STUB
chmod +x "$T/bin/launchctl"

# run_install <manifest-text> -> sets OUT, ERR, RC, LA (agents dir, fresh each call)
run_install() {
  printf '%s\n' "$1" > "$T/manifest.md"
  rm -rf "$T/la"; mkdir -p "$T/la"
  STUBLOG="$T/log" PATH="$T/bin:$PATH" PULSE_CONFIG="$T/manifest.md" LIFEHACK_CODE_ROOT="$T/code" LIFEHACK_DESK_REPO="$T/nodesk" \
    HOME="$T/home" LAUNCHAGENTS_DIR="$T/la" LIFEHACK_TEST_OS_OVERRIDE=mac bash "$ROOT/system/tools/install-schedulers.sh" --install >"$T/out" 2>"$T/err"
  RC=$?
  ERR="$(cat "$T/err")"
}

ROW() { # name interval -> a full door-passing jobs row
  printf '%s | yes | %s | o. | $HOME/x ~ ^ran n=[0-9]+ items | none | 0 | none | bash "$LIFEHACK_CODE_ROOT/system/tools/ok-run.sh"' "$1" "$2"
}
JOBS() { # rows... -> a ```jobs fence
  printf '```jobs\n'; for r in "$@"; do printf '%s\n' "$r"; done; printf '```\n'
}

plist_field() { # plist key -> value (integer/string right after the key)
  python3 -c 'import plistlib,sys; d=plistlib.load(open(sys.argv[1],"rb")); print(d.get(sys.argv[2],""))' "$1" "$2"
}

# ── 1) a 600 s interval is ACCEPTED and produces StartInterval 600 ──
run_install "$(JOBS "$(ROW j600 600)")"
if [ "$RC" -eq 0 ] && [ -f "$T/la/ai.lifehack.j600.plist" ]; then
  v="$(plist_field "$T/la/ai.lifehack.j600.plist" StartInterval)"
  [ "$v" = "600" ] && pass "p1-600s-startinterval" || fail "p1-600s-startinterval" "StartInterval=$v rc=$RC"
  plutil -lint "$T/la/ai.lifehack.j600.plist" >/dev/null && pass "p1-600s-lint" || fail "p1-600s-lint" "plutil rejected the plist"
  # a StartInterval job must NOT carry a StartCalendarInterval schedule
  if plist_field "$T/la/ai.lifehack.j600.plist" StartCalendarInterval >/dev/null 2>&1; then
    python3 -c 'import plistlib,sys; d=plistlib.load(open(sys.argv[1],"rb")); sys.exit(0 if "StartCalendarInterval" not in d else 1)' "$T/la/ai.lifehack.j600.plist" \
      && pass "p1-600s-no-calendar" || fail "p1-600s-no-calendar" "calendar keys present"
  else pass "p1-600s-no-calendar"; fi
  python3 -c 'import plistlib,sys; d=plistlib.load(open(sys.argv[1],"rb")); a=d["ProgramArguments"]; sys.exit(0 if a[-1].endswith("job-run.sh\" j600 --if-overdue") else 1)' "$T/la/ai.lifehack.j600.plist" \
    && pass "p1-600s-if-overdue-launch" || fail "p1-600s-if-overdue-launch" "launch line lost --if-overdue"
else fail "p1-600s-startinterval" "rc=$RC; err=$(head -c 200 "$ERR")"; fi

# ── 2) another non-whole-hour interval (5400 s = 90 min) is accepted, StartInterval ──
run_install "$(JOBS "$(ROW j5400 5400)")"
[ "$RC" -eq 0 ] && [ "$(plist_field "$T/la/ai.lifehack.j5400.plist" StartInterval)" = "5400" ] \
  && pass "p2-5400s-accepted" || fail "p2-5400s-accepted" "rc=$RC; err=$(head -c 200 "$ERR")"

# ── 3) hour-based intervals keep the OLD StartCalendarInterval behaviour ──
run_install "$(JOBS "$(ROW j3600 3600)")"
if [ "$RC" -eq 0 ]; then
  python3 - "$T/la/ai.lifehack.j3600.plist" <<'PY'
import plistlib, sys
d = plistlib.load(open(sys.argv[1], "rb"))
cal = d.get("StartCalendarInterval")
ok = ("StartInterval" not in d and isinstance(cal, list)
      and [e["Hour"] for e in cal] == list(range(24))
      and all(e["Minute"] == 0 for e in cal))
sys.exit(0 if ok else 1)
PY
  [ $? -eq 0 ] && pass "p3-3600s-calendar-hours" || fail "p3-3600s-calendar-hours" "calendar changed for 3600"
else fail "p3-3600s-calendar-hours" "rc=$RC; err=$(head -c 200 "$ERR")"; fi

run_install "$(JOBS "$(ROW j43200 43200)")"
python3 - "$T/la/ai.lifehack.j43200.plist" <<'PY'
import plistlib, sys
d = plistlib.load(open(sys.argv[1], "rb"))
cal = d.get("StartCalendarInterval")
sys.exit(0 if [e["Hour"] for e in cal] == [0, 12] else 1)
PY
[ $? -eq 0 ] && pass "p3-43200s-calendar-12h" || fail "p3-43200s-calendar-12h" "12h calendar changed"

# ── 4) day-based intervals: NO clock-time trigger (owed, not scheduled): hourly heartbeat StartInterval, RunAtLoad kept ──
for pair in "j86400 86400" "j604800 604800"; do
  set -- $pair
  run_install "$(JOBS "$(ROW "$1" "$2")")"
  python3 - "$T/la/ai.lifehack.$1.plist" <<'PY'
import plistlib, sys
d = plistlib.load(open(sys.argv[1], "rb"))
sys.exit(0 if ("StartCalendarInterval" not in d and d.get("StartInterval") == 3600 and d.get("RunAtLoad") is True) else 1)
PY
  [ $? -eq 0 ] && pass "p4-$2s-heartbeat-no-calendar" || fail "p4-$2s-heartbeat-no-calendar" "daily-or-longer row still has a clock trigger, or lost heartbeat/RunAtLoad"
done

# ── 5) refusals: under 60 s, zero, and non-numbers still fail loudly, no plist ──
for case_v in 59 0 abc; do
  run_install "$(JOBS "$(ROW "jbad$case_v" "$case_v")")"
  if [ "$RC" -ne 0 ] && echo "$ERR" | grep -q "FATAL.*jbad$case_v" && [ ! -f "$T/la/ai.lifehack.jbad$case_v.plist" ]; then
    pass "p5-refuse-$case_v"
  else fail "p5-refuse-$case_v" "rc=$RC err=$(head -c 160 "$ERR")"; fi
done

# ── 6) one invalid sibling blocks the WHOLE install (validate-all-before-touching, unchanged) ──
run_install "$(JOBS "$(ROW jok 600)" "$(ROW jbad 30)")"
if [ "$RC" -ne 0 ] && [ ! -f "$T/la/ai.lifehack.jok.plist" ] && [ ! -f "$T/la/ai.lifehack.jbad.plist" ]; then
  pass "p6-invalid-sibling-blocks-all"
else fail "p6-invalid-sibling-blocks-all" "rc=$RC; $(ls "$T/la" 2>/dev/null | tr '\n' ' ')"; fi

# ── 7) plan-only mode names the 600 s interval without touching launchctl ──
printf '%s\n' "$(JOBS "$(ROW jplan 600)")" > "$T/manifest.md"
rm -rf "$T/la"; mkdir -p "$T/la"; : > "$T/log"
STUBLOG="$T/log" PATH="$T/bin:$PATH" PULSE_CONFIG="$T/manifest.md" LIFEHACK_CODE_ROOT="$T/code" LIFEHACK_DESK_REPO="$T/nodesk" \
  HOME="$T/home" LAUNCHAGENTS_DIR="$T/la" LIFEHACK_TEST_OS_OVERRIDE=mac bash "$ROOT/system/tools/install-schedulers.sh" >"$T/out" 2>"$T/err"; rc=$?
if [ "$rc" -eq 0 ] && grep -q "600" "$T/out" && [ ! -s "$T/log" ] && [ ! -f "$T/la/ai.lifehack.jplan.plist" ]; then
  pass "p7-plan-only-600"
else fail "p7-plan-only-600" "rc=$rc out=$(head -c 160 "$T/out")"; fi

[ "$FAILS" -eq 0 ] || echo "$FAILS case(s) FAILED"
exit "$FAILS"
