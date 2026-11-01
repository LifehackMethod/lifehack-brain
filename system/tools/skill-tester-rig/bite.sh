#!/bin/bash
# bite.sh — card TR1.6 of the skill-tester-rig: the rung-1 GATE. bash 3.2 + BSD tools, pure code (ruling 2).
#
#   bite.sh --rung 1 [--sentinel]
#                         every fake-plantable fault in `inject.sh list` (21 rows: F-19 at TR1.7, F-20 2026-10-31),
#                         n=3 runs each, one fault per run; then 5 clean controls. Last line, exactly:
#                           BITE rung1 caught <c>/21 fp <f>/5 CLEAN        (c=21 and f=0)
#                           BITE FAILED caught <c>/21 fp <f>/5             (anything else, exit 1; the missed list is above it)
#                         --sentinel (TR1.7): sentinel.sh writes into THIS bite's own stand-in, OUTSIDE the guard, for
#                         the WHOLE bite (faults and controls), seed 1729, log <bite scratch>/sentinel.log.
# STAND-IN ISOLATION (CONTRACT §3b, 2026-10-31): every bite exports SEAM_STANDIN=$CANON/notes-standin/<bite-id>/, so
#   its runs snapshot ONLY their own stand-in (plus the real roots) and only its own sentinel writes there. Two bites
#   at once never see each other's sentinel. The guard still denies the whole notes-standin/ tree.
# RECEIPT: the full gate (`--rung 1`, no dev-subset flags) ends by calling `receipt.sh write rung1 "<final BITE line>"`
#   from this unguarded script, after the whole bite (see receipt.sh). Its stdout is also kept at
#   ~/lifehack-scratch/skill-tester-rig/bite-rung1-<bite-id>.out. Exit 3 if the receipt could not be written.
#   bite.sh --selftest    proves the bite CAN say FAILED (a mini-bite, normal, then with a broken check, then with a
#                         broken grader). Last line 'SELFTEST bite can-fail OK'.
#   dev subset (never the gate: denominators shrink so the gate line cannot be produced; results go to
#   bite-rung1-partial.tsv):  bite.sh --rung 1 [--only F-xx,F-yy] [--n N] [--controls K]
#
# Per run: `inject.sh plan` FIRST (the answer key, ruling 11), then protocol.tsv phase by phase (pre-run ·
# run1 [+ mid-run concurrent] · between-runs · run2 · post-run · truth), env from plans/<id>/<run1|run2>.env, then
# grade: every line of expected.tsv (col 3) must EQUAL a whole line of events.log or of truth.py stdout (CONTRACT §3),
# except the key ORACLE-EXIT-NONZERO, which is satisfied only when truth.py exited 1 (F-20: graded by the oracle alone).
# A fault is CAUGHT only if all n runs caught it.
#   F-14 is ONE row run as BOTH plantings (F-14a live, F-14b aftermath), n runs each; the row counts as caught only
#        if every run of BOTH variants caught it.
#   F-09 rotates its variant by run index: r1 delete, r2 corrupt, r3 zero.
#   F-20 rotates K by run index: odd runs K=0 (zero steps), even runs K=6 (r1 0, r2 6, r3 0).
# Clean control (inject.sh plan <id> none; RIG_TEST unset): a FALSE POSITIVE is any of
#   - any events.log line at all EXCEPT `SEAM-AMBIENT ` lines (a clean run writes none; a superset of CHECK-FAIL/
#     CANNOT-READ/WATCHDOG/MODEL-FAIL/RECORD-*/PATH-REFUSED/SELFTEST-REFUSED/VERSION-CHANGE, and also SEAM-DENIED,
#     SEAM-LEAK, SEAM-CANNOT-READ, GUARD-PROBE-FAILED, BUDGET-REFUSED, RERUN, RESUME, WAITING). SEAM-AMBIENT is a change
#     the write guard proves no rig process made (CONTRACT §3a): recorded and counted (`AMBIENT <n>`), never a flag
#   - `RIG-TEST ON` in events.log (a test-path run is REFUSED as a control and counted as a false positive)
#   - a truth.py step line other than `sN ok`, any FLAG line, no exact TOTAL ok=12-with-zeros line, truth rc != 0
#   - run.sh exit != 0
# SENTINEL CROSS-CHECK (TR1.7), every run, faults and controls: a SEAM-AMBIENT path INSIDE the notes stand-in must
#   appear in this bite's sentinel.log (only the sentinel writes there). One that does not is printed as
#   `SUSPICIOUS-AMBIENT <run-id> <path>` and counted as a false positive (fp may then exceed the control count).
#   Without --sentinel the log is treated as EMPTY (a stale log can never vouch for a path). A SEAM-AMBIENT path in
#   ANOTHER bite's stand-in (inside notes-standin/ but outside this bite's subtree) is always SUSPICIOUS: it can
#   never count as clean. Ambient paths OUTSIDE the stand-in tree (the real notes root under load: other windows)
#   cannot be cross-checked; they are counted apart.
# SENTINEL HANDSHAKE (TR1.8), every CONTROL under --sentinel: a control must PROVE the sentinel wrote during its own
#   seam window, else it proves nothing about ambient classification. A watcher waits for that run's seam snapshot,
#   then for a NEW sentinel.log line, then releases the fake actor, which holds at s3 (FAKE_WAIT_FILE) until then;
#   so the write lands after the snapshot and before the verify. Either wait running out prints `WAIT-TIMEOUT <what>`
#   and the control FAILS by that name (counted in fp; the actor is released so the run still ends). The bite's
#   start also waits (handshake) for the sentinel's first write; no write -> WAIT-TIMEOUT + BITE FAILED, nothing run.
# Up to 3 runs at once (xargs -P 3). Run ids b1-<fault>-r<k>-<bite-id> (bite-id = epoch-pid; never reused; inject
# refuses an existing plan). Runs live under ~/lifehack-scratch/skill-tester-rig/bite-r1-<bite-id>/ (never src/).
# Cost: $0 — fake model only; this script never passes --real and never launches claude.

set -u
export PYTHONDONTWRITEBYTECODE=1
SRC="$(cd "$(dirname "$0")" && pwd)"
SELF="$SRC/$(basename "$0")"
CANON="$HOME/lifehack-scratch/skill-tester-rig"
. "$SRC/wait.lib.sh" || { echo "bite: wait.lib.sh missing" >&2; exit 2; }   # TR1.8 handshakes
# nothing inherited may steer a run: these are set per run from plans/<id>/*.env only
unset RIG_TEST CHECKS_DIR FAKE_MODE_STEP FAKE_DELAY FAKE_DELAY_STEP FAKE_MODEL_ID RIG_WATCHDOG_SECS \
      RIG_HOLD_BEFORE_RECORD RIG_RUN_DIR STRESS_TODAY CANARY_SEED SKILL_TESTER_SEED SKILL_TESTER_RIG CLAUDE_BIN \
      FAKE_MODE BUDGET_WATCHDOG_FLOOR RIG_GUARD_TAG RIG_GUARD_PARENT RIG_GUARD_T0 RIG_GUARD_PROFILE RIG_GUARD_HANDOFF \
      SEAM_GUARD_DISABLE GUARD_TEST_NO_LOG RIG_TEST_SEAM_WRITE SENTINEL_LOG FAKE_WAIT_FILE FAKE_WAIT_STEP FAKE_WAIT_SECS

die() { echo "bite: $*" >&2; exit 2; }
CLEAN_TOTAL="TOTAL ok=12 silent_wrong=0 double_ran=0 stuck=0 lost=0 skipped=0 out_of_order=0 false_done=0"

# ── one run (called by xargs): --one <fault|control> <fault-id> <k> <run-id> ──────────────────────────────────
# reads: _BITE_S (scratch), _BITE_OUT (result dir), _BITE_CHECKS (broken-check override, selftest only),
#        _BITE_TRUTH (broken-grader override, selftest only)
snap_of()   { ls "$_BITE_S/seam/$1".*.sha >/dev/null 2>&1; }
slog_grew() { [ "$(wc -l < "$_BITE_SLOG" | tr -d ' ')" -gt "$1" ]; }
sent_watch() {  # sent_watch <run-id> <driver dir> : the per-control sentinel HANDSHAKE (TR1.8; see the header)
  local R="$1" L="$2" n0 sec="${_BITE_SENT_WAIT_SECS:-20}" what
  what="$R seam snapshot"
  if wait_until 120 "$what" snap_of "$R" 2>/dev/null; then
    n0="$(wc -l < "$_BITE_SLOG" | tr -d ' ')"          # counted AFTER the snapshot exists
    what="$R sentinel write after the snapshot"
    if wait_until "$sec" "$what" slog_grew "$n0" 2>/dev/null; then : > "$L/sentinel-wrote"; return 0; fi
  fi
  echo "WAIT-TIMEOUT $what" | tee "$L/sentinel-watch.timeout" >&2
  : > "$L/sentinel-wrote"                               # release the actor so the run ends; the control already FAILED
  return 1
}

one() {
  local kind="$1" F="$2" k="$3" R="$4" S="$_BITE_S" OUT="$_BITE_OUT"
  local bp="" PD="$S/plans/$R" RD L="$S/driver/$R" notes="" rc1="-" rc2="-" trc="-" v="" pf="$F" w c line
  RD="$(python3 -I "$SRC/run_helper.py" rundir "$S" "$R")"   # layout.py (TR2.0b): the run dir inside the actor home
  local ILOG="$S/driver/$R/inject.log"
  mkdir -p "$L"
  export SKILL_TESTER_SCRATCH="$S"
  local K=""
  if [ "$F" = F-09 ]; then case $(( (k-1) % 3 )) in 0) v=delete ;; 1) v=corrupt ;; 2) v=zero ;; esac; fi
  if [ "$F" = F-20 ]; then case $(( k % 2 )) in 1) K=0 ;; 0) K=6 ;; esac; fi
  # 1. the answer key, BEFORE anything runs
  if [ -n "$v" ]; then bash "$SRC/inject.sh" plan "$R" "$F" --variant "$v" >> "$ILOG" 2>&1
  elif [ -n "$K" ]; then bash "$SRC/inject.sh" plan "$R" "$F" --step "$K" >> "$ILOG" 2>&1
  else bash "$SRC/inject.sh" plan "$R" "$F" >> "$ILOG" 2>&1; fi
  if [ $? != 0 ] || [ ! -s "$PD/expected.tsv" ]; then
    printf '%s\t%s\t%s\t0\t%s\t%s\t%s\n' "$kind" "$F" "$k" "plan-failed" "$R" "-" > "$OUT/$R.res"; return 0
  fi
  [ -n "$v" ] && pf="$F($v)"
  [ -n "$K" ] && pf="$F(K=$K)"
  has() { awk -F'\t' -v p="$1" -v a="$2" '$2==p && $3==a{x=1} END{exit !x}' "$PD/protocol.tsv"; }
  arg() { awk -F'\t' -v p="$1" '$2==p && $3=="args"{print $4; exit}' "$PD/protocol.tsv"; }
  want(){ awk -F'\t' -v p="$1" '$2==p && $3=="expect-exit"{print $4; exit}' "$PD/protocol.tsv"; }
  apply(){ bash "$SRC/inject.sh" apply "$R" "$F" "$1" >> "$ILOG" 2>&1 || notes="$notes apply-$1-rc=$?"; }
  runone() {  # runone <run1|run2> : a subshell with exactly that run's env, then run.sh
    local ph="$1" a; a="$(arg "$ph")"
    (
      if [ -f "$PD/$ph.env" ]; then while IFS= read -r kv; do [ -n "$kv" ] && export "$kv"; done < "$PD/$ph.env"; fi
      if [ -n "${_BITE_CHECKS:-}" ] && [ -z "${CHECKS_DIR:-}" ]; then export CHECKS_DIR="$_BITE_CHECKS"; fi
      exec bash "$SRC/run.sh" $a >> "$L/$ph.out" 2>&1 </dev/null
    )
  }
  has pre-run inject && apply pre-run
  # TR1.8 sentinel handshake for a control (see the header): watcher in the background, actor held at s3 until it
  local swp="" swrc="-" SWT="$L/sentinel-watch.timeout"
  if [ "$kind" = control ] && [ "${_BITE_SLOG:-/dev/null}" != /dev/null ]; then
    rm -f "$L/sentinel-wrote" "$SWT"
    sent_watch "$R" "$L" &
    swp=$!
    export FAKE_WAIT_FILE="$L/sentinel-wrote" FAKE_WAIT_STEP=3 FAKE_WAIT_SECS=$(( ${_BITE_SENT_WAIT_SECS:-20} + 90 ))
  fi
  if [ -n "$(arg run1)" ]; then
    if has mid-run inject-concurrent; then
      # F-07 plants a SIGKILL: bash's "Killed: 9" job notice goes to the driver log, not the bite's output
      {
        runone run1 &
        bp=$!
        apply mid-run
        wait $bp; rc1=$?
      } 2>> "$L/jobs.err"
    else
      runone run1; rc1=$?
    fi
    w="$(want run1)"
    case "$w" in
      "killed (SIGKILL)") [ "$rc1" = 137 ] || notes="$notes rc1=$rc1(want-kill)" ;;
      "$rc1") ;;
      *) notes="$notes rc1=$rc1(want-$w)" ;;
    esac
  fi
  if [ -n "$swp" ]; then
    wait "$swp"; swrc=$?           # bounded: the watcher's own two deadlines
    unset FAKE_WAIT_FILE FAKE_WAIT_STEP FAKE_WAIT_SECS
    if [ "$swrc" = 0 ]; then notes="$notes sentinel-write=proven"
    else notes="$notes sentinel-write=UNPROVEN"; fi
  fi
  has between-runs inject && apply between-runs
  if [ -n "$(arg run2)" ]; then
    runone run2; rc2=$?
    w="$(want run2)"; [ "$w" = "$rc2" ] || notes="$notes rc2=$rc2(want-$w)"
  fi
  has post-run inject && apply post-run
  if has post-run check; then [ -e /Volumes/GoogleDrive ] && notes="$notes drive-path-exists"; fi
  # truth (the oracle), into the driver dir
  if [ -n "${_BITE_TRUTH:-}" ]; then bash "$_BITE_TRUTH" "$SRC/truth.py" --run "$R" > "$L/truth.out" 2> "$L/truth.err"
  else python3 -B "$SRC/truth.py" --run "$R" > "$L/truth.out" 2> "$L/truth.err"; fi
  trc=$?
  local EV="$RD/events.log"
  if [ ! -f "$EV" ]; then : > "$L/events.none"; EV="$L/events.none"; notes="$notes no-events.log"; fi
  if [ "$kind" = fault ]; then
    # 2. grade: whole-line equality, events.log or truth stdout (CONTRACT §3)
    local miss=""
    while IFS= read -r line; do
      [ -n "$line" ] || continue
      if [ "$line" = ORACLE-EXIT-NONZERO ]; then [ "$trc" = 1 ] || miss="$miss | $line(truth rc=$trc)"; continue; fi
      grep -Fxq -- "$line" "$EV" || grep -Fxq -- "$line" "$L/truth.out" || miss="$miss | $line"
    done <<EOF
$(cut -f3- "$PD/expected.tsv")
EOF
    c=1; [ -n "$miss" ] && c=0
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$kind" "$pf" "$k" "$c" "${miss# | }" "$R" "rc1=$rc1 rc2=$rc2 truth=$trc${notes}" > "$OUT/$R.res"
  else
    local fl=""
    if [ -n "$swp" ] && [ "$swrc" != 0 ]; then
      fl="$fl | $(head -1 "$SWT" 2>/dev/null || echo "WAIT-TIMEOUT $R sentinel watcher rc=$swrc")"
    fi
    grep -qx 'RIG-TEST ON' "$EV" && fl="$fl | REFUSED-AS-CONTROL: RIG-TEST ON"
    local amb=0
    while IFS= read -r line; do
      case "$line" in
        "") ;;
        "SEAM-AMBIENT "*) amb=$((amb+1)) ;;          # TR1.7: proven not the rig's (CONTRACT §3a); never a flag
        *) fl="$fl | event: $line" ;;
      esac
    done < "$EV"
    notes="$notes ambient=$amb"
    while IFS= read -r line; do
      case "$line" in
        s[0-9]*" ok"|"$CLEAN_TOTAL"|"") ;;
        *) fl="$fl | truth: $line" ;;
      esac
    done < "$L/truth.out"
    grep -Fxq -- "$CLEAN_TOTAL" "$L/truth.out" || fl="$fl | no clean TOTAL line"
    [ "$trc" = 0 ] || fl="$fl | truth rc=$trc"
    [ "$rc1" = 0 ] || fl="$fl | run.sh rc=$rc1"
    c=1; [ -n "$fl" ] && c=0       # for a control, c=1 means clean
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$kind" "control" "$k" "$c" "${fl# | }" "$R" "rc1=$rc1 truth=$trc${notes}" > "$OUT/$R.res"
  fi
  local done_n; done_n="$(ls "$OUT" | grep -c '\.res$')"
  SKILL_TESTER_SCRATCH="$_BITE_STATUS_DIR" bash "$SRC/status.sh" "bite-rung1" "$_BITE_ID" \
    "$done_n/$_BITE_TOTAL runs" "0" "$R done ($kind ok=$c)" >/dev/null 2>&1
  return 0
}

# ── a bite: bite <scratch> <results.tsv> <n> <controls> <fault list> ──────────────────────────────────────────
bite() {
  local S="$1" TSV="$2" N="$3" NC="$4" FAULTS="$5"
  local OUT="$1/results" JOBS="$1/jobs.txt" t0 t1 f k
  case "$S/" in "$SRC"/*) die "scratch $S is inside src/" ;; esac
  mkdir -p "$S/actor-home" "$S/plans" "$S/seeds" "$OUT" || die "cannot create $S"
  t0=$(date +%s)
  : > "$S/jobs.txt"
  for f in $FAULTS; do
    for k in $(seq 1 "$N"); do
      if [ "$f" = F-14 ]; then
        echo "fault F-14a $k b1-F-14a-r$k-$_BITE_ID" >> "$S/jobs.txt"
        echo "fault F-14b $k b1-F-14b-r$k-$_BITE_ID" >> "$S/jobs.txt"
      else
        echo "fault $f $k b1-$f-r$k-$_BITE_ID" >> "$S/jobs.txt"
      fi
    done
  done
  k=1; while [ "$k" -le "$NC" ]; do echo "control none $k b1-ctl-r$k-$_BITE_ID" >> "$S/jobs.txt"; k=$((k+1)); done
  export _BITE_S="$S" _BITE_OUT="$OUT" _BITE_TOTAL="$(wc -l < "$JOBS" | tr -d ' ')"
  echo "bite: $_BITE_TOTAL runs ($(echo $FAULTS | wc -w | tr -d ' ') faults x n=$N, F-14 as a+b, + $NC controls), up to 3 at once, scratch $S" >&2
  # CONTRACT §3b: this bite's OWN stand-in; every run (and the sentinel) inherits it, whatever the caller had set
  export SEAM_STANDIN="$CANON/notes-standin/$_BITE_ID"
  rm -rf "$SEAM_STANDIN"; mkdir -p "$SEAM_STANDIN" || die "cannot create $SEAM_STANDIN"
  local SLOG=/dev/null spid=""
  if [ "${_BITE_SENTINEL:-}" = 1 ]; then
    SLOG="$S/sentinel.log"
    : > "$SLOG"
    SENTINEL_LOG="$SLOG" bash "$SRC/sentinel.sh" run --seed 1729 > "$S/sentinel.out" 2>&1 &
    spid=$!; echo "$spid" > "$S/sentinel.pid"
    trap 'kill -TERM '"$spid"' 2>/dev/null' EXIT
    echo "bite: SENTINEL pid $spid writing into this bite's stand-in $SEAM_STANDIN (outside the guard); log $SLOG" >&2
    # TR1.8 HANDSHAKE: its first write lands before any run starts; none -> the bite FAILS, it never runs blind
    if ! wait_until "${_BITE_SENT_WAIT_SECS:-20}" "sentinel first write ($SLOG)" test -s "$SLOG"; then
      kill -TERM "$spid" 2>/dev/null; wait "$spid" 2>/dev/null; trap - EXIT
      echo "WAIT-TIMEOUT sentinel first write ($SLOG)"
      echo "BITE FAILED WAIT-TIMEOUT sentinel first write (nothing run)"; return 1
    fi
  fi
  export _BITE_SLOG="$SLOG"
  xargs -P 3 -L 1 bash "$SELF" --one < "$JOBS"
  if [ -n "$spid" ]; then kill -TERM "$spid" 2>/dev/null; wait "$spid" 2>/dev/null; rm -f "$S/sentinel.pid"; trap - EXIT; fi
  t1=$(date +%s)
  # aggregate, in list order
  local caught=0 nf=0 fp=0 missed_list="" first ka kb ma r ctl_n
  printf 'kind\tfault\trun\tcaught\tmissing_or_flags\trun_id\tnotes\n' > "$TSV"
  local res=( "$OUT"/*.res )
  if [ ! -e "${res[0]}" ]; then echo "bite: no result files in $OUT: every job died before reporting" >&2; return 1; fi
  cat "${res[@]}" | sort -t "$(printf '\t')" -k1,1 -k2,2 -k3,3n >> "$TSV"
  for f in $FAULTS; do
    nf=$((nf+1))
    if [ "$f" = F-14 ]; then
      ka=$(awk -F'\t' '$1=="fault" && $2=="F-14a" && $4==1' "$TSV" | wc -l | tr -d ' ')
      kb=$(awk -F'\t' '$1=="fault" && $2=="F-14b" && $4==1' "$TSV" | wc -l | tr -d ' ')
      first="$(head -1 "$S/plans/b1-F-14a-r1-$_BITE_ID/expected.tsv" 2>/dev/null | cut -f3-)"
      echo "  F-14 counted once: F-14a (live) $ka/$N, F-14b (aftermath) $kb/$N — caught only if both are $N/$N"
      if [ "$ka" = "$N" ] && [ "$kb" = "$N" ]; then echo "PLANTED F-14 → CAUGHT \"$first\""; caught=$((caught+1))
      else
        ma="$(awk -F'\t' '$1=="fault" && ($2=="F-14a"||$2=="F-14b") && $4!=1{print $2" r"$3": "$5}' "$TSV" | tr '\n' ';')"
        echo "PLANTED F-14 → MISSED (a $ka/$N, b $kb/$N) $ma"; missed_list="$missed_list F-14"
      fi
    else
      ka=$(awk -F'\t' -v f="$f" '$1=="fault" && ($2==f || index($2, f"(")==1) && $4==1' "$TSV" | wc -l | tr -d ' ')
      first="$(head -1 "$S/plans/b1-$f-r1-$_BITE_ID/expected.tsv" 2>/dev/null | cut -f3-)"
      if [ "$ka" = "$N" ]; then echo "PLANTED $f → CAUGHT \"$first\""; caught=$((caught+1))
      else
        ma="$(awk -F'\t' -v f="$f" '$1=="fault" && ($2==f || index($2, f"(")==1) && $4!=1{print $2" r"$3": "$5" ["$7"]"}' "$TSV" | tr '\n' ';')"
        echo "PLANTED $f → MISSED ($ka/$N) $ma"; missed_list="$missed_list $f"
      fi
    fi
  done
  for r in $(awk -F'\t' '$1=="control"{print $3":"$4}' "$TSV"); do
    if [ "${r#*:}" != 1 ]; then
      fp=$((fp+1))
      echo "CONTROL r${r%%:*} → FALSE POSITIVE: $(awk -F'\t' -v k="${r%%:*}" '$1=="control" && $3==k{print $5}' "$TSV")"
    else echo "CONTROL r${r%%:*} → clean"; fi
  done
  ctl_n=$(awk -F'\t' '$1=="control"' "$TSV" | wc -l | tr -d ' ')
  # TR1.7 sentinel cross-check over every run's SEAM-AMBIENT lines (see the header)
  local standin_r tree_r amb_all=0 amb_in=0 amb_ext=0 sus=0 rid ap rdd
  standin_r="$(python3 -I -B -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$SEAM_STANDIN")"
  tree_r="$(python3 -I -B -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$CANON/notes-standin")"
  for rid in $(awk -F'\t' 'NR>1{print $6}' "$TSV"); do
    rdd="$(python3 -I "$SRC/run_helper.py" rundir "$S" "$rid")"
    [ -f "$rdd/events.log" ] || continue
    while IFS= read -r ap; do
      [ -n "$ap" ] || continue
      amb_all=$((amb_all+1))
      case "$ap/" in
        "$standin_r"/*)
          amb_in=$((amb_in+1))
          if ! awk -F'\t' -v p="$ap" '$3==p{x=1} END{exit !x}' "$SLOG"; then
            echo "SUSPICIOUS-AMBIENT $rid $ap (in the stand-in, but not in the sentinel's log)"; sus=$((sus+1))
          fi ;;
        "$tree_r"/*)
          amb_in=$((amb_in+1))
          echo "SUSPICIOUS-AMBIENT $rid $ap (in ANOTHER bite's stand-in: never clean)"; sus=$((sus+1)) ;;
        *) amb_ext=$((amb_ext+1)) ;;
      esac
    done <<EOF2
$(sed -n 's/^SEAM-AMBIENT [A-Z]* //p' "$rdd/events.log")
EOF2
  done
  fp=$((fp+sus))
  rm -rf "$SEAM_STANDIN"            # this bite's stand-in only (its sentinel is stopped)
  echo "AMBIENT $amb_all (stand-in $amb_in, all sentinel-vouched: $([ "$sus" = 0 ] && echo yes || echo "NO, $sus suspicious"); outside the stand-in $amb_ext, not cross-checkable) · sentinel $([ "$SLOG" = /dev/null ] && echo off || echo "on, $(wc -l < "$SLOG" | tr -d ' ') writes")"
  echo "WALL $((t1-t0))s for $_BITE_TOTAL runs · COST \$0 (fake model, zero tokens) · results $TSV"
  SKILL_TESTER_SCRATCH="$_BITE_STATUS_DIR" bash "$SRC/status.sh" "bite-rung1" "$_BITE_ID" "$_BITE_TOTAL/$_BITE_TOTAL runs" "0" \
    "finished: caught $caught/$nf fp $fp/$ctl_n" >/dev/null 2>&1
  [ -n "$missed_list" ] && echo "MISSED:$missed_list"
  # a missing control result counts against CLEAN (ctl_n must equal NC)
  if [ "$caught" = "$nf" ] && [ "$fp" = 0 ] && [ "$ctl_n" = "$NC" ]; then echo "BITE rung1 caught $caught/$nf fp $fp/$NC CLEAN"
  else echo "BITE FAILED caught $caught/$nf fp $fp/$NC"; return 1; fi   # TR1.8: a failed bite exits nonzero
}

new_id() { echo "$(date +%s)-$$"; }

case "${1:-}" in
  --one) shift; one "$@"; exit 0 ;;
  --rung)
    [ "${2:-}" = 1 ] || die "only --rung 1 exists"
    shift 2
    for v in _BITE_CHECKS _BITE_TRUTH _BITE_S _BITE_OUT SKILL_TESTER_RECEIPTS SKILL_TESTER_RECEIPT_RIG; do
      eval "[ -z \"\${$v:-}\" ]" || die "$v is set in the environment — overrides exist only inside --selftest (no bypass)"
    done
    ONLY=""; N=3; NC=5
    while [ $# -gt 0 ]; do
      case "$1" in
        --only) ONLY="$(echo "${2:-}" | tr ',' ' ')"; shift 2 ;;
        --n) N="${2:-}"; shift 2 ;;
        --controls) NC="${2:-}"; shift 2 ;;
        --sentinel) export _BITE_SENTINEL=1; shift ;;
        *) die "unknown argument '$1'" ;;
      esac
    done
    case "$N$NC" in ''|*[!0-9]*) die "--n/--controls must be integers" ;; esac
    ALL="$(bash "$SRC/inject.sh" list | cut -f1 | tr '\n' ' ')"
    [ "$(echo $ALL | wc -w | tr -d ' ')" = 21 ] || die "inject.sh list does not have 21 rows (19 + F-19 + F-20): $ALL"
    FAULTS="$ALL"; TSV="$CANON/bite-rung1.tsv"
    if [ -n "$ONLY" ] || [ "$N" != 3 ] || [ "$NC" != 5 ]; then
      [ -n "$ONLY" ] && FAULTS="$ONLY"
      TSV="$CANON/bite-rung1-partial.tsv"
      echo "bite: DEV SUBSET (not the gate): faults=[$FAULTS] n=$N controls=$NC" >&2
    fi
    _BITE_ID="$(new_id)"
    export _BITE_ID _BITE_STATUS_DIR="$CANON" _BITE_CHECKS="" _BITE_TRUTH=""
    GATE=1; [ "$TSV" = "$CANON/bite-rung1.tsv" ] || GATE=0
    mkdir -p "$CANON" || die "cannot create $CANON"
    BOUT="$CANON/bite-rung1-$_BITE_ID.out"
    bite "$CANON/bite-r1-$_BITE_ID" "$TSV" "$N" "$NC" "$FAULTS" | tee "$BOUT"
    BRC=${PIPESTATUS[0]}
    # LONG-GATE RECEIPT (plan rule 2026-10-31; receipt.sh): written HERE, by this unguarded orchestrator, after the
    # whole bite has ended, whatever the outcome (a FAILED line is a receipt too; it simply never matches the
    # card's expected line). Real gate runs only: never a dev subset, never --mini or --selftest.
    if [ "$GATE" = 1 ]; then
      RLINE="$(grep -E '^BITE (rung1 caught|FAILED) ' "$BOUT" | tail -1)"
      [ -n "$RLINE" ] || RLINE="BITE FAILED no result line (bite rc=$BRC)"
      bash "$SRC/receipt.sh" write rung1 "$RLINE" || { echo "bite: RECEIPT NOT WRITTEN for '$RLINE'" >&2; exit 3; }
    fi
    exit "$BRC" ;;
  --mini)
    # TR1.7 selftest-load only (seam_load.sh): bite.sh --mini <dir under $CANON/selftest-load/> <n> <controls>
    # <faults|none> [--sentinel]. Never the gate (its TSV lives in <dir>), never a broken-check/grader override.
    MD="${2:-}"; MN="${3:-}"; MC="${4:-}"; MF="${5:-}"
    case "$MD/" in "$CANON/selftest-load/"*/) ;; *) die "--mini dir must lie under $CANON/selftest-load/" ;; esac
    case "$MN$MC" in ''|*[!0-9]*) die "--mini n/controls must be integers" ;; esac
    [ "$MF" = none ] && MF=""
    [ "${6:-}" = --sentinel ] && export _BITE_SENTINEL=1
    _BITE_ID="mini-$(new_id)"
    export _BITE_ID _BITE_STATUS_DIR="$MD" _BITE_CHECKS="" _BITE_TRUTH=""
    bite "$MD" "$MD/bite.tsv" "$MN" "$MC" "$MF" ;;
  --selftest)
    ST="$CANON/selftest-bite/$(new_id)"
    mkdir -p "$ST"
    export _BITE_STATUS_DIR="$ST"
    # (a) normal mini-bite (2 faults x n=1 + 1 control): must be CLEAN
    export _BITE_ID="st-ok-$(new_id)" _BITE_CHECKS="" _BITE_TRUTH=""
    bite "$ST/ok" "$ST/ok.tsv" 1 1 "F-01 F-06b" > "$ST/ok.out" 2>&1
    # (b) broken CHECK: a scratch checks/ copy whose ai.sh always exits 0 (a rubber stamp)
    #     code.sh/human.sh are wrappers that CALL the real checks in place (inject.sh's pattern; a copied check
    #     cannot run outside the rig and would be CANNOT-READ), so only ai.sh is broken.
    mkdir -p "$ST/broken-checks"
    for kk in code human; do
      printf '#!/bin/bash\n# bite selftest wrapper: the real check, in place\nexec bash "%s/checks/%s.sh" "$@"\n' "$SRC" "$kk" > "$ST/broken-checks/$kk.sh"
    done
    printf '#!/bin/bash\n# bite selftest: BROKEN check, passes everything\nexit 0\n' > "$ST/broken-checks/ai.sh"
    export _BITE_ID="st-bc-$(new_id)" _BITE_CHECKS="$ST/broken-checks" _BITE_TRUTH=""
    bite "$ST/bc" "$ST/bc.tsv" 1 1 "F-01 F-06b" > "$ST/bc.out" 2>&1
    # (c) broken GRADER: truth.py wrapped so `lost` reads `ok` and a clean s1 reads silent_wrong (cries wolf)
    export _BITE_ID="st-bt-$(new_id)" _BITE_CHECKS="" _BITE_TRUTH="$SRC/bite/broken-truth.sh"
    bite "$ST/bt" "$ST/bt.tsv" 1 1 "F-01 F-06b" > "$ST/bt.out" 2>&1
    bad=""
    for x in ok bc bt; do echo "── $x ──"; grep -E '^(PLANTED|CONTROL|MISSED|WALL|BITE)' "$ST/$x.out"; done
    tail -1 "$ST/ok.out" | grep -qx 'BITE rung1 caught 2/2 fp 0/1 CLEAN' || bad="$bad normal-not-clean"
    tail -1 "$ST/bc.out" | grep -q '^BITE FAILED ' || bad="$bad broken-check-not-FAILED"
    grep -q '^PLANTED F-01 → MISSED' "$ST/bc.out" || bad="$bad broken-check-F-01-not-missed"
    grep -q '^CONTROL r1 → FALSE POSITIVE' "$ST/bc.out" || bad="$bad broken-check-control-not-fp"
    tail -1 "$ST/bt.out" | grep -q '^BITE FAILED ' || bad="$bad broken-truth-not-FAILED"
    grep -q '^PLANTED F-06b → MISSED' "$ST/bt.out" || bad="$bad broken-truth-F-06b-not-missed"
    grep -q '^PLANTED F-01 → CAUGHT' "$ST/bt.out" || bad="$bad broken-truth-F-01-should-still-be-caught"
    grep -q '^CONTROL r1 → FALSE POSITIVE' "$ST/bt.out" || bad="$bad broken-truth-control-not-fp"
    echo "selftest dir: $ST"
    if [ -z "$bad" ]; then echo "SELFTEST bite can-fail OK"; exit 0; fi
    echo "SELFTEST bite FAILED:$bad"; exit 1 ;;
  *) echo "usage: bite.sh --rung 1 | --selftest   (dev: --rung 1 --only F-xx,F-yy --n N --controls K)" >&2; exit 2 ;;
esac
