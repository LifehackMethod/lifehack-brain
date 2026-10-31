#!/bin/bash
# budget.sh — skill-tester-rig card TR0.3: per-run dollar + call budget, refused BEFORE it is exceeded,
# and a per-call watchdog. macOS bash 3.2 / BSD tools. ⛔ NO `set -e` (build-sop B21: one call's failure
# must never abort a loop or wipe a run's ledger). Ledgers are APPEND-ONLY; nothing here rewrites one.
#
# USAGE
#   budget.sh open   <run-id> [--usd N] [--calls N] [--ladder-id ID] [--ladder-usd N]
#   budget.sh charge <run-id> <usd|UNKNOWN> <calls>      exit 75 = refused, nothing recorded
#   budget.sh call   <run-id> -- <cmd args…>             cmd `run_model` = the shared run_model, used in place
#   budget.sh status <run-id>
#   budget.sh selftest                                    final exit = the 2nd charge's exit (75 when healthy)
#
# DEFAULTS  $5.00 and 40 model calls per run · $50.00 per ladder pass. Any non-default cap prints a
#   "CAP OVERRIDE:" banner on stderr — never silent.
# STATE     ${SKILL_TESTER_SCRATCH:-~/lifehack-scratch/skill-tester-rig}/budget/<run-id>.tsv
#           ${SKILL_TESTER_SCRATCH:-…}/budget/ladder-<id>.tsv
# WATCHDOG  per call = 2 × median duration of this run's prior successful calls, floor 120 s;
#   kill -9 on expiry, exit 124. BUDGET_WATCHDOG_FLOOR=<s> overrides the floor — TESTS ONLY, announced.
# EXIT      0 ok · 2 usage · 75 budget refused/exhausted · 124 watchdog · else the wrapped command's rc.

SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
TOOLS_DIR="${LIFEHACK_V2:-$HOME/lifehack-v2}/system/tools"   # shared layer, used in place
SCRATCH="${SKILL_TESTER_SCRATCH:-$HOME/lifehack-scratch/skill-tester-rig}"
BDIR="$SCRATCH/budget"

DEF_USD="5"; DEF_CALLS="40"; DEF_LADDER_USD="50"; DEF_FLOOR="120"

say()  { printf 'budget: %s\n' "$*" >&2; }
die()  { say "$1"; exit "${2:-2}"; }
now()  { date -u +%Y-%m-%dT%H:%M:%SZ; }
isnum() { case "$1" in ''|.|*[!0-9.]*|*.*.*) return 1 ;; esac; return 0; }
isint() { case "$1" in ''|*[!0-9]*) return 1 ;; esac; return 0; }
runf()  { printf '%s/%s.tsv' "$BDIR" "$1"; }
ladf()  { printf '%s/ladder-%s.tsv' "$BDIR" "$1"; }
kv()    { awk -F'\t' -v k="$2" '$1==k {v=$2} END{print v}' "$1"; }    # last value of a key line
spent() { awk -F'\t' -v c="$2" '$1=="charge" && $c!="UNKNOWN" {s+=$c} END{printf "%.4f", s+0}' "$1"; }
ncalls(){ awk -F'\t' -v c="$2" '$1=="charge" {s+=$c} END{print s+0}' "$1"; }
nunk()  { awk -F'\t' -v c="$2" '$1=="charge" && $c=="UNKNOWN" {n++} END{print n+0}' "$1"; }
gt()    { awk -v a="$1" -v b="$2" 'BEGIN{exit !(a+0 > b+0 + 1e-9)}'; }      # float a > b
add()   { awk -v a="$1" -v b="$2" 'BEGIN{printf "%.4f", a+b}'; }


lock()   { local i=0; while ! mkdir "$BDIR/.lock" 2>/dev/null; do i=$((i+1)); [ $i -gt 100 ] && { say "lock stuck: $BDIR/.lock"; return 1; }; sleep 0.1; done; }
unlock() { rmdir "$BDIR/.lock" 2>/dev/null; }

# ── open ─────────────────────────────────────────────────────────────────────────────────────────────
cmd_open() {
  local run="$1"; shift
  [ -n "$run" ] || die "open: need <run-id>"
  case "$run" in */*|.*) die "open: bad run-id '$run'" ;; esac
  local usd="$DEF_USD" calls="$DEF_CALLS" lid="" lusd="$DEF_LADDER_USD"
  while [ $# -gt 0 ]; do
    case "$1" in
      --usd) usd="$2"; shift 2 ;;
      --calls) calls="$2"; shift 2 ;;
      --ladder-id) lid="$2"; shift 2 ;;
      --ladder-usd) lusd="$2"; shift 2 ;;
      *) die "open: unknown arg '$1'" ;;
    esac
  done
  isnum "$usd" || die "open: --usd not a number: $usd"
  isint "$calls" || die "open: --calls not an integer: $calls"
  isnum "$lusd" || die "open: --ladder-usd not a number: $lusd"
  [ "$usd" != "$DEF_USD" ] && say "CAP OVERRIDE: run $run usd cap \$$usd (default \$$DEF_USD)"
  [ "$calls" != "$DEF_CALLS" ] && say "CAP OVERRIDE: run $run calls cap $calls (default $DEF_CALLS)"
  [ "$lusd" != "$DEF_LADDER_USD" ] && say "CAP OVERRIDE: ladder ${lid:-?} usd cap \$$lusd (default \$$DEF_LADDER_USD)"
  mkdir -p "$BDIR" || die "cannot create $BDIR" 1
  local f; f="$(runf "$run")"
  if [ -f "$f" ]; then
    say "run $run already open — existing ledger kept as is (caps \$$(kv "$f" cap_usd) / $(kv "$f" cap_calls) calls)"
    return 0
  fi
  if [ -n "$lid" ]; then
    local lf; lf="$(ladf "$lid")"
    if [ -f "$lf" ]; then
      [ "$(kv "$lf" cap_usd)" != "$lusd" ] && say "ladder $lid already open with cap \$$(kv "$lf" cap_usd) — kept; requested \$$lusd ignored"
    else
      printf 'cap_usd\t%s\nopened\t%s\n' "$lusd" "$(now)" > "$lf"
    fi
  fi
  printf 'cap_usd\t%s\ncap_calls\t%s\nladder\t%s\nopened\t%s\n' "$usd" "$calls" "${lid:--}" "$(now)" > "$f"
  say "opened run $run: \$$usd / $calls calls${lid:+, ladder $lid}"
}

# ── refusal check (shared by charge and call's pre-check). Prints the reason; 0 = allowed. ─────────────
would_cross() {  # <run-id> <usd|UNKNOWN> <calls>
  local f lf lid c cu s n u; f="$(runf "$1")"
  u="$2"; [ "$u" = UNKNOWN ] && u=0
  s="$(add "$(spent "$f" 3)" "$u")"; n=$(( $(ncalls "$f" 4) + $3 ))
  cu="$(kv "$f" cap_usd)"; c="$(kv "$f" cap_calls)"
  gt "$s" "$cu" && { echo "run $1 would reach \$$s > cap \$$cu"; return 0; }
  [ "$n" -gt "$c" ] && { echo "run $1 would reach $n calls > cap $c"; return 0; }
  lid="$(kv "$f" ladder)"
  if [ -n "$lid" ] && [ "$lid" != "-" ]; then
    lf="$(ladf "$lid")"
    s="$(add "$(spent "$lf" 4)" "$u")"; cu="$(kv "$lf" cap_usd)"
    gt "$s" "$cu" && { echo "ladder $lid would reach \$$s > cap \$$cu"; return 0; }
  fi
  return 1
}

record() {  # <run-id> <usd|UNKNOWN> <calls> <secs> <note>   (append-only, both ledgers)
  local f lid; f="$(runf "$1")"; lid="$(kv "$f" ladder)"
  printf 'charge\t%s\t%s\t%s\t%s\t%s\n' "$(now)" "$2" "$3" "$4" "$5" >> "$f"
  [ -n "$lid" ] && [ "$lid" != "-" ] && printf 'charge\t%s\t%s\t%s\t%s\t%s\n' "$(now)" "$1" "$2" "$3" "$5" >> "$(ladf "$lid")"
  return 0
}

warn_unknown() {
  local k; k="$(nunk "$(runf "$1")" 3)"
  [ "$k" -gt 0 ] && say "WARNING: run $1 has $k call(s) of UNKNOWN cost — not counted in the \$ total, which is therefore a FLOOR"
  return 0
}

# ── charge ───────────────────────────────────────────────────────────────────────────────────────────
cmd_charge() {
  local run="$1" usd="$2" calls="$3" f why
  [ $# -eq 3 ] || die "charge: need <run-id> <usd|UNKNOWN> <calls>"
  f="$(runf "$run")"; [ -f "$f" ] || die "charge: run $run not open ($f)"
  [ "$usd" = UNKNOWN ] || isnum "$usd" || die "charge: usd not a number: $usd"
  isint "$calls" || die "charge: calls not an integer: $calls"
  lock || exit 1
  if why="$(would_cross "$run" "$usd" "$calls")"; then
    unlock; say "REFUSED (75): charge \$$usd/$calls — $why. Nothing recorded."; exit 75
  fi
  record "$run" "$usd" "$calls" "" "charge"
  unlock
  say "charged run $run \$$usd/$calls → spent \$$(spent "$f" 3) of \$$(kv "$f" cap_usd), $(ncalls "$f" 4) of $(kv "$f" cap_calls) calls"
  warn_unknown "$run"
  return 0
}

# ── watchdog ─────────────────────────────────────────────────────────────────────────────────────────
watchdog_secs() {  # 2 × median of prior successful call durations, floor
  local floor="$DEF_FLOOR" med
  if [ -n "${BUDGET_WATCHDOG_FLOOR:-}" ]; then
    isint "$BUDGET_WATCHDOG_FLOOR" || die "BUDGET_WATCHDOG_FLOOR not an integer"
    floor="$BUDGET_WATCHDOG_FLOOR"
    say "WATCHDOG FLOOR OVERRIDE (tests only): ${floor}s instead of ${DEF_FLOOR}s"
  fi
  med="$(awk -F'\t' '$1=="charge" && $6=="call-ok" && $5!="" {print $5}' "$(runf "$1")" | sort -n |
        awk '{a[NR]=$1} END{ if(NR==0){print 0} else if(NR%2){print a[(NR+1)/2]} else {printf "%d", (a[NR/2]+a[NR/2+1])/2 + 0.5} }')"
  med=$(( med * 2 )); [ "$med" -lt "$floor" ] && med="$floor"
  echo "$med"
}

killtree() {  # kill -9 a pid and every descendant (children grabbed BEFORE the parent dies)
  local k; for k in $(pgrep -P "$1" 2>/dev/null); do killtree "$k"; done
  kill -9 "$1" 2>/dev/null
}

# from orchestrator-v2/rig/run.sh @ 2026-10-28  (run_ai watchdog + stop_wd, lines 29-34 / 62-75;
#   adapted: generic command instead of a hard-coded claude line, killtree instead of a bare kill -9)
WDPID=""
stop_wd() {
  [ -n "$WDPID" ] || return 0
  local kids; kids="$(pgrep -P "$WDPID" 2>/dev/null)"   # grab the sleep child BEFORE killing the subshell
  kill "$WDPID" 2>/dev/null; [ -n "$kids" ] && kill $kids 2>/dev/null
  wait "$WDPID" 2>/dev/null; WDPID=""
}
run_watched() {  # <secs> <stdout-file> <wd-flag-file> <cmd…>  → sets RC (124 on watchdog)
  local secs="$1" out="$2" wd="$3"; shift 3
  rm -f "$wd"
  if [ "$1" = run_model ]; then
    shift
    ( . "$TOOLS_DIR/model.lib.sh" || exit 1; run_model "$@" ) > "$out" </dev/null &
  else
    ( exec "$@" ) > "$out" </dev/null &
  fi
  local pid=$!
  ( sleep "$secs"; : > "$wd"; killtree "$pid" ) >/dev/null 2>&1 &
  WDPID=$!
  wait "$pid"; RC=$?
  stop_wd
  if [ -e "$wd" ] || [ "$RC" = 137 ]; then RC=124; fi
  rm -f "$wd"
}
# end stolen part

# ── call ─────────────────────────────────────────────────────────────────────────────────────────────
cmd_call() {
  local run="$1"; shift
  [ "$1" = "--" ] || die "call: usage: call <run-id> -- <cmd args…>"
  shift; [ $# -gt 0 ] || die "call: no command after --"
  local f why secs out wd t0 dur cost note mfile=""
  f="$(runf "$run")"; [ -f "$f" ] || die "call: run $run not open ($f)"
  if why="$(would_cross "$run" 0 1)"; then say "REFUSED (75): budget exhausted before call — $why"; exit 75; fi
  # also refuse when the $ cap is already fully spent (a $0 pre-check cannot cross an exactly-met cap)
  if ! gt "$(kv "$f" cap_usd)" "$(spent "$f" 3)"; then
    say "REFUSED (75): run $run has spent its whole \$$(kv "$f" cap_usd)"; exit 75
  fi
  secs="$(watchdog_secs "$run")"
  mkdir -p "$BDIR/out"
  out="$BDIR/out/$run.$$.$(date +%s).stdout"; wd="$out.wd"
  [ "$1" = run_model ] && mfile="$4"                       # run_model <tier> <prompt> <out-file>
  say "call: watchdog ${secs}s · $*"
  t0="$(date +%s)"
  run_watched "$secs" "$out" "$wd" "$@"
  dur=$(( $(date +%s) - t0 ))
  cat "$out" 2>/dev/null                                   # pass the command's stdout through
  cost="$( { cat "$out"; [ -n "$mfile" ] && cat "$mfile"; } 2>/dev/null |
           grep -oE '"total_cost_usd"[[:space:]]*:[[:space:]]*[0-9.eE+-]+' | tail -1 | sed 's/.*:[[:space:]]*//')"
  if [ -n "$cost" ]; then cost="$(awk -v c="$cost" 'BEGIN{printf "%.6f", c}')"
  else cost=UNKNOWN; say "COST UNKNOWN: no total_cost_usd in the result — recorded as UNKNOWN, not 0"; fi
  if [ "$RC" = 124 ]; then note="call-timeout"; elif [ "$RC" = 0 ]; then note="call-ok"; else note="call-rc$RC"; fi
  lock || exit 1
  # the money is already spent: the ledger must say so even if it crosses the cap (an unrecorded overrun is a lie)
  if why="$(would_cross "$run" "$cost" 1)"; then
    record "$run" "$cost" 1 "$dur" "$note;OVERRUN"; unlock
    say "OVERRUN (75): this call pushed past the cap — $why. Recorded; further calls refused."
    warn_unknown "$run"; exit 75
  fi
  record "$run" "$cost" 1 "$dur" "$note"; unlock
  say "call done rc=$RC in ${dur}s, cost \$$cost → run spent \$$(spent "$f" 3) of \$$(kv "$f" cap_usd)"
  [ "$RC" = 124 ] && say "WATCHDOG FIRED after ${secs}s — process tree killed (-9). Ledger intact."
  warn_unknown "$run"
  exit "$RC"
}

cmd_status() {
  local f; f="$(runf "$1")"; [ -f "$f" ] || die "status: run $1 not open"
  printf 'run %s: $%s of $%s · %s of %s calls · ladder %s\n' "$1" "$(spent "$f" 3)" "$(kv "$f" cap_usd)" \
    "$(ncalls "$f" 4)" "$(kv "$f" cap_calls)" "$(kv "$f" ladder)"
  warn_unknown "$1"
}

# ── selftest ─────────────────────────────────────────────────────────────────────────────────────────
cmd_selftest() {
  local base="${SKILL_TESTER_SCRATCH:-$HOME/lifehack-scratch/skill-tester-rig}/selftest/$(date -u +%Y%m%dT%H%M%SZ)-$$"
  local fails="" rc err t0 dt B="bash $SELF"
  mkdir -p "$base" || { echo "selftest: cannot create $base"; return 1; }
  export SKILL_TESTER_SCRATCH="$base"; BDIR="$base/budget"
  echo "selftest: scratch $base  (fake commands only — no model is ever called)"

  # 1. an override prints the banner
  err="$($B open st-banner --usd 2 2>&1 >/dev/null)"
  if printf '%s' "$err" | grep -q 'CAP OVERRIDE: run st-banner usd cap \$2'; then echo "  ok   override banner printed"
  else echo "  FAIL override banner missing"; fails="$fails banner"; fi

  # 2. watchdog kills a hanging fake with 124, and the run's prior ledger survives (B21)
  $B open st-wd >/dev/null 2>&1
  $B charge st-wd 0.01 1 >/dev/null 2>&1
  t0="$(date +%s)"
  BUDGET_WATCHDOG_FLOOR=2 $B call st-wd -- bash -c 'sleep 30' >/dev/null 2>&1; rc=$?
  dt=$(( $(date +%s) - t0 ))
  if [ "$rc" = 124 ] && [ "$dt" -lt 15 ] && grep -q $'\t0.01\t1\t' "$BDIR/st-wd.tsv" && grep -q 'call-timeout' "$BDIR/st-wd.tsv"; then
    echo "  ok   watchdog killed hang → 124 in ${dt}s; ledger kept"
  else echo "  FAIL watchdog (rc=$rc, ${dt}s)"; fails="$fails watchdog"; fi

  # 3. cost parsed from JSON; missing cost recorded UNKNOWN, never 0
  $B call st-wd -- printf '{"type":"result","total_cost_usd":0.0123}\n' > "$base/cost-json.log" 2>&1; rc=$?
  $B call st-wd -- echo 'no json here' > "$base/cost-none.log" 2>&1
  if [ "$rc" = 0 ] && grep -q $'\t0.012300\t1\t' "$BDIR/st-wd.tsv" && grep -q $'\tUNKNOWN\t1\t' "$BDIR/st-wd.tsv"; then
    echo "  ok   cost parsed (0.0123) and missing cost → UNKNOWN"
  else echo "  FAIL cost parsing (rc=$rc)"; fails="$fails cost"; fi

  # 4. the ladder cap refuses even when each run is under its own cap
  $B open st-la --ladder-id st-lad --ladder-usd 1 >/dev/null 2>&1
  $B open st-lb --ladder-id st-lad --ladder-usd 1 >/dev/null 2>&1
  $B charge st-la 0.70 1 >/dev/null 2>&1; local r1=$?
  $B charge st-lb 0.70 1 >/dev/null 2>&1; rc=$?
  if [ "$r1" = 0 ] && [ "$rc" = 75 ] && ! grep -q 'st-lb' "$BDIR/ladder-st-lad.tsv"; then
    echo "  ok   ladder cap refused (75), nothing recorded"
  else echo "  FAIL ladder cap (first=$r1 second=$rc)"; fails="$fails ladder"; fi

  # 5. THE card test: $1 budget, 0.60 ok, 0.60 refused
  $B open st-main --usd 1 >/dev/null 2>&1
  $B charge st-main 0.60 1 >/dev/null 2>&1; r1=$?
  $B charge st-main 0.60 1 >/dev/null 2>&1; rc=$?
  echo "  main \$1 budget: 1st charge 0.60 → $r1 (want 0), 2nd charge 0.60 → $rc (want 75)"
  [ "$r1" = 0 ] || fails="$fails main-first"

  if [ -n "$fails" ]; then echo "selftest: INTERNAL FAILURE:$fails"; return 1; fi
  echo "selftest: exiting with the 2nd charge's code ($rc)"
  return "$rc"
}

sub="${1:-}"; [ $# -gt 0 ] && shift
case "$sub" in
  open) cmd_open "$@" ;;
  charge) cmd_charge "$@" ;;
  call) cmd_call "$@" ;;
  status) cmd_status "$@" ;;
  selftest) cmd_selftest; exit $? ;;
  *) sed -n '2,20p' "$SELF" >&2; exit 2 ;;
esac
