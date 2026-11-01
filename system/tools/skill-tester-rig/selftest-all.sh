#!/bin/bash
# selftest-all.sh — card TR1.8 of the skill-tester-rig: every rig selftest, one after another. FAKE MODEL ONLY.
# ENTRY POINT (run by hand from a window's Bash; never from a sub-agent, ruling 7).
#
#   selftest-all.sh            runs every rig selftest SEQUENTIALLY (never in parallel: several share scratch and the
#                              guard's log): status · seam · budget (exit 75 = healthy) · expected · truth · checks ·
#                              inject · run · bite · seam selftest-load · probe-hooks · probe-actor-writes ·
#                              actor-guard · ladder · receipt · guard · sentinel ·
#                              waits-scan. One `ok`/`FAIL` line each; last line exactly
#                                SELFTEST-ALL OK <n>/<n>     or     SELFTEST-ALL FAILED <k>/<n>: <names>
#   selftest-all.sh --waits    TR1.8's Verify: the wait scan, the scan watched failing, the FAIL-FIRST cases, and the
#                              selftests that contain waits (budget, guard, sentinel, inject, run, bite, seam-load).
#                              Last line exactly, only when ALL hold:
#                                WAITS handshake-only silent-giveup 0 scan fail-first OK
#                              else  WAITS FAILED: <names>
# FAIL-FIRST (each in a throwaway COPY of the rig under ~/lifehack-scratch/skill-tester-rig/selftest-all/, where the
# awaited event never happens; each must FAIL, and by WAIT-TIMEOUT, never pass and never give up silently):
#   ff-k1                run.sh never writes hold-s7.held      -> run selftest FAILS "k1 handshake: WAIT-TIMEOUT ..."
#   ff-sentinel-silent   the sentinel writes once, then never  -> the control FAILS "WAIT-TIMEOUT <run> sentinel write
#                        after the snapshot", BITE FAILED (before TR1.8 the same control passed CLEAN)
#   ff-sentinel-mute     the sentinel never writes             -> "BITE FAILED WAIT-TIMEOUT sentinel first write"
#   ff-f07-standin       (inject 4d) the injector cannot kill   -> inject selftest FAILS "WAIT-TIMEOUT F-07 stand-in kill"
# Logs: ~/lifehack-scratch/skill-tester-rig/selftest-all/<stamp>/<name>.log (kept). Cost: $0, zero tokens.
set -u
export PYTHONDONTWRITEBYTECODE=1
RIG="$(cd "$(dirname "$0")" && pwd)"
CANON="$HOME/lifehack-scratch/skill-tester-rig"
OUT="$CANON/selftest-all/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$OUT" || { echo "SELFTEST-ALL FAILED 0/0: cannot create $OUT"; exit 1; }
unset SKILL_TESTER_RIG SKILL_TESTER_SCRATCH CLAUDE_BIN RIG_TEST CHECKS_DIR FAKE_WAIT_FILE FAKE_WAIT_STEP FAKE_WAIT_SECS \
      RIG_HOLD_BEFORE_RECORD RIG_WATCHDOG_SECS _BITE_SENT_WAIT_SECS RIG_K1_WAIT_SECS
FAILED=""; N=0; NOK=0

# one <name> <want-rc> <want-last-line|-> <cmd…> : run, log, judge by exit code AND exact last line
one() {
  local name="$1" wrc="$2" wline="$3" rc last t0
  shift 3
  N=$((N+1)); t0=$(date +%s)
  "$@" > "$OUT/$name.log" 2>&1 </dev/null; rc=$?
  last="$(tail -1 "$OUT/$name.log")"
  if [ "$rc" = "$wrc" ] && { [ "$wline" = - ] || [ "$last" = "$wline" ]; }; then
    NOK=$((NOK+1)); echo "  ok   $name (rc $rc, $(( $(date +%s) - t0 ))s) $last"
  else
    FAILED="$FAILED $name"; echo "  FAIL $name (rc $rc, want $wrc; $(( $(date +%s) - t0 ))s) last line: $last"
  fi
}

st_status()  { one status  0 "SELFTEST OK" bash "$RIG/status.sh" selftest; }
st_seam()    { one seam    0 - bash "$RIG/seam.sh" selftest; }
st_budget()  { one budget  75 - bash "$RIG/budget.sh" selftest; }
st_expected(){ one expected 0 "SELFTEST expected OK" python3 -B "$RIG/canary/expected.py" --selftest; }
st_truth()   { one truth   0 "SELFTEST 8/8 categories each seen failing" python3 -B "$RIG/truth.py" --selftest; }
st_checks()  { one checks  0 "SELFTEST bad=fail good=pass cannot-read=distinct ALL OK" bash "$RIG/checks/selftest.sh"; }
st_inject()  { one inject  0 "SELFTEST inject OK" bash "$RIG/inject.sh" selftest; }
st_run()     { one run     0 "SELFTEST run OK" bash "$RIG/run.sh" --selftest; }
st_bite()    { one bite    0 "SELFTEST bite can-fail OK" bash "$RIG/bite.sh" --selftest; }
st_load()    { one seam-load 0 "SEAM under load denied 1/1 named ambient-only fp 0/5 actor-needs listed" bash "$RIG/seam.sh" selftest-load; }
st_probe()   { one probe-hooks 0 - bash "$RIG/probe-hooks.sh" --selftest; }
st_paw()     { one probe-actor-writes 0 "SELFTEST probe-actor-writes 7/7 ALL OK" bash "$RIG/probe-actor-writes.sh" --selftest; }
st_ag()      { one actor-guard 0 "SELFTEST actor-guard 29/29 ALL OK" bash "$RIG/actor-guard.sh" --selftest; }
st_ladder()  { one ladder  0 "SELFTEST ladder 69/69 ALL OK" bash "$RIG/ladder.sh" --selftest; }
st_receipt() { one receipt 0 "SELFTEST receipt OK" bash "$RIG/receipt.sh" --selftest; }
st_guard()   { one guard   0 "SELFTEST guard receipts-deny OK" bash "$RIG/guard.sh" selftest; }
st_sentinel(){ one sentinel 0 "SELFTEST sentinel OK" bash "$RIG/sentinel.sh" selftest; }
st_wscan()   { one waits-scan-selftest 0 "SELFTEST waits-scan OK" bash "$RIG/waits_scan.sh" --selftest; }

# ── fail-first helpers ──────────────────────────────────────────────────────────────────────────────────────────
rigcopy() {  # rigcopy <dir> : a throwaway copy of this rig (never inside the rig)
  rm -rf "$1"; cp -Rp "$RIG" "$1" && find "$1" -name __pycache__ -prune -exec rm -rf {} +
}
# ff <name> <cmd…> : the case must exit nonzero AND its log must carry a WAIT-TIMEOUT line naming <needle> (FF_NEEDLE)
ff() {
  local name="$1" rc; shift
  N=$((N+1))
  "$@" > "$OUT/$name.log" 2>&1 </dev/null; rc=$?
  if [ "$rc" != 0 ] && grep -q "WAIT-TIMEOUT $FF_NEEDLE" "$OUT/$name.log" && grep -qE "$FF_FAILLINE" "$OUT/$name.log"; then
    NOK=$((NOK+1)); echo "  ok   $name FAILED as it must (rc $rc): $(grep -m1 "WAIT-TIMEOUT $FF_NEEDLE" "$OUT/$name.log")"
  else
    FAILED="$FAILED $name"; echo "  FAIL $name did not fail by WAIT-TIMEOUT (rc $rc; last: $(tail -1 "$OUT/$name.log"))"
  fi
}
ff_k1() {
  local C="$OUT/rig-ff-k1"; rigcopy "$C"
  grep -qF ': > "$RUN_DIR/hold-s$n.held"' "$C/run.sh" || { N=$((N+1)); FAILED="$FAILED ff-k1(no-marker-line)"; echo "  FAIL ff-k1: marker line not found in the copy"; return; }
  sed -i.bak '/: > "$RUN_DIR\/hold-s$n.held"/d' "$C/run.sh" && rm -f "$C/run.sh.bak"
  FF_NEEDLE="k1 hold-s7.held" FF_FAILLINE='^SELFTEST run FAILED:.* k1 handshake' \
    ff ff-k1 env RIG_K1_WAIT_SECS=5 bash "$C/run.sh" --selftest
}
silent_sentinel() {  # silent_sentinel <copy> <writes 0|1> : replace the copy's sentinel with one that writes N times, then idles
  cat > "$1/sentinel.sh" <<EOF
#!/bin/bash
# fail-first stand-in (selftest-all.sh): writes $2 time(s), then never again; still dies on SIGTERM like the real one
st="\${SEAM_STANDIN:?}"; mkdir -p "\$st"
if [ "$2" = 1 ]; then echo once > "\$st/sentinel-00.md"; printf '%s\tADDED\t%s\n' "\$(date +%s).000" "\$(cd "\$st" && pwd -P)/sentinel-00.md" >> "\${SENTINEL_LOG:?}"; fi
exec sleep 3600   # pacing: the silence under test
EOF
}
ff_sentinel() {
  local C="$OUT/rig-ff-sent" D
  rigcopy "$C"; silent_sentinel "$C" 1
  D="$CANON/selftest-load/ff-silent-$$"; rm -rf "$D"
  FF_NEEDLE="b1-ctl-r1-.* sentinel write after the snapshot" FF_FAILLINE='^BITE FAILED caught 0/0 fp 1/1' \
    ff ff-sentinel-silent env _BITE_SENT_WAIT_SECS=8 bash "$C/bite.sh" --mini "$D" 1 1 none --sentinel
  rm -rf "$C"; rigcopy "$C"; silent_sentinel "$C" 0
  D="$CANON/selftest-load/ff-mute-$$"; rm -rf "$D"
  FF_NEEDLE="sentinel first write" FF_FAILLINE='^BITE FAILED WAIT-TIMEOUT sentinel first write' \
    ff ff-sentinel-mute env _BITE_SENT_WAIT_SECS=5 bash "$C/bite.sh" --mini "$D" 1 1 none --sentinel
}
ff_f07() {
  local C="$OUT/rig-ff-f07"; rigcopy "$C"
  # the copy's F-07 injector never kills (its kill lines become no-ops), so the stand-in's hold runs out
  sed -i.bak -e 's/kill -KILL -- "-$pg" 2>\/dev\/null; how=/: ; how=/' -e 's/        kill -KILL "$pid" 2>\/dev\/null; how=/        : ; how=/' \
    -e 's/sleep 30   # pacing: the stand-in hold/sleep 3   # pacing: the stand-in hold/' "$C/inject.sh" && rm -f "$C/inject.sh.bak"
  FF_NEEDLE="F-07 stand-in kill" FF_FAILLINE='^SELFTEST inject FAIL.*F07-not-killed' \
    ff ff-f07-standin bash "$C/inject.sh" selftest
}

echo "selftest-all: logs $OUT (fake model only, sequential)"
if [ "${1:-}" = --waits ]; then
  # A receipt must describe the real rig in the real receipts dir: refuse test overrides (same rule as bite.sh).
  for v in SKILL_TESTER_RECEIPTS SKILL_TESTER_RECEIPT_RIG; do
    eval "vv=\${$v:-}"; [ -z "$vv" ] || { echo "WAITS FAILED: $v is set; the --waits run writes the real 'waits' receipt and refuses overrides" >&2; exit 2; }
  done
  echo "== wait scan"
  N=$((N+1))
  if bash "$RIG/waits_scan.sh" > "$OUT/waits-scan.log" 2>&1; then NOK=$((NOK+1)); echo "  ok   waits-scan $(tail -1 "$OUT/waits-scan.log")"
  else FAILED="$FAILED waits-scan"; echo "  FAIL waits-scan:"; grep '^REFUSED' "$OUT/waits-scan.log" | sed 's/^/       /'; fi
  st_wscan
  echo "== fail-first (copies where the awaited event never happens)"
  ff_k1; ff_sentinel; ff_f07
  echo "== selftests that contain waits"
  st_budget; st_guard; st_sentinel; st_inject; st_run; st_bite; st_load
  if [ -z "$FAILED" ]; then RESULT="WAITS handshake-only silent-giveup 0 scan fail-first OK"; RC=0
  else RESULT="WAITS FAILED:$FAILED"; RC=1; fi
  # The receipt (TR1.8 Verify) is written by this unguarded orchestrator only after everything above has ended,
  # whatever the outcome (a FAILED line is a receipt too; it just never matches). Its notice goes to stderr so the
  # result stays the last stdout line.
  if ! bash "$RIG/receipt.sh" write waits "$RESULT" 1>&2; then echo "selftest-all: receipt write FAILED" >&2; RC=1; fi
  echo "$RESULT"; exit "$RC"
fi
[ -z "${1:-}" ] || { echo "usage: selftest-all.sh [--waits]" >&2; exit 2; }
st_status; st_seam; st_budget; st_expected; st_truth; st_checks; st_inject; st_run; st_bite; st_load; st_probe; st_paw; st_ag
st_ladder
st_receipt; st_guard; st_sentinel; st_wscan
if [ -z "$FAILED" ]; then echo "SELFTEST-ALL OK $NOK/$N"; exit 0; fi
echo "SELFTEST-ALL FAILED $((N-NOK))/$N:$FAILED"; exit 1
