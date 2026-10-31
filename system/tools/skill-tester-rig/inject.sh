#!/bin/bash
# from orchestrator-v2/rig/stress/inject.sh @ 2026-10-28
#   (kept: the named-injector shape, the faults.tsv-row-per-planting log, wait-for-exec.log-begin then SIGKILL the
#    group, input delete / corrupt (keep half the bytes) / zero (every digit -> 0), record-truncate (one row cut to
#    3 fields + a partial 4th, newline kept), env-line injectors for the fake model and version-change;
#    new: the answer key written BEFORE the run, the path guard, the scratch check copies, the 18-row table.)
#
# inject.sh — TR1.5 of the skill-tester-rig: the fault injector and the answer key. bash 3.2, pure code.
#
#   inject.sh list                                   the 21 fake-plantable faults (Appendix A + F-19 + F-20), one line each
#   inject.sh plan <run-id> <fault-id…|none> [--step N] [--variant delete|corrupt|zero]
#        BEFORE the run: writes $SCRATCH/plans/<run-id>/expected.tsv  (fault-id \t sN \t exact grader line)
#        and $SCRATCH/plans/<run-id>/protocol.tsv (fault-id \t phase \t action \t payload: what the driver and
#        run.sh must do, in order). Refuses if the run dir or the plan already exists (ruling 11).
#        protocol phases: pre-run · run1 · mid-run · between-runs · run2 · post-run · truth. actions: inject (call
#        it, wait) · inject-concurrent (start it alongside run1) · env (K=V for that run; also written by apply to
#        plans/<run-id>/<run1|run2>.env, split at the first '=', values may hold spaces) · args (run.sh argv) ·
#        expect-exit · run (the grader) · check (a manual/seam assertion).
#   inject.sh apply <run-id> <fault-id> <phase>      plant it now; appends one line to plans/<run-id>/faults.tsv
#        (epoch \t fault-id \t sN \t what was done). The fault must be in that run's plan, for that phase.
#   inject.sh selftest                               last line 'SELFTEST inject OK'
#
# SCRATCH = ${SKILL_TESTER_SCRATCH:-~/lifehack-scratch/skill-tester-rig}; it must resolve INSIDE
# ~/lifehack-scratch/skill-tester-rig (ruling 6). Every path inject.sh writes, deletes or kills for must resolve
# inside $SCRATCH, else exit 2 with the reason. It never writes the rig's own files: the real checks/ are only
# ever CALLED, by absolute path, from wrapper scripts in a scratch copy.
#
# Exit: 0 ok · 1 selftest/list failure · 2 refused (bad args, path outside SCRATCH, no plan, wrong phase, run
# active) · 3 planting could not be made valid (e.g. kill landed after the record row; real checks/ absent).
#
# ─── Expected lines (CONTRACT §3, exact whole lines). A = run.sh gets --answer s4=yes --answer s9=yes.
#     T(...) = the truth.py TOTAL line with those counts and every other count 0. N = the planting step.
#     TOTAL rows are written only for single-fault plans (two faults in one run interact).
#   F-01 empty / F-02 almost / F-03 garbage / F-06 lossy (N ai, default 5): CHECK-FAIL sN <cat> · sN stuck · T(ok=N-1 stuck=1)
#        <cat> per checks/_check.py + fake-claude.sh as built: empty->empty (no reply), almost->token (token key
#        dropped), garbage->parse (non-JSON result), lossy->facts (last fact dropped)
#   F-06b facts lost AFTER commit (N any, default 5; between-runs on a finished run, one fact's number edited in
#        step-N.json): sN lost · T(ok=11 lost=1)
#   F-04 hang    (N ai, default 5): WATCHDOG sN · sN stuck · T(ok=N-1 stuck=1)
#   F-05 exit127 (N ai, default 5): MODEL-FAIL sN rc=127 · sN stuck · T(ok=N-1 stuck=1)
#   F-07 kill-sigkill (N any, default 7, a code step = a real side effect): RERUN sN · sN ok · T(ok=12)
#   F-08 record-truncate (N any, default 5): RECORD-REFUSED sN row=N · T(ok=12)
#   F-09 input-delete|corrupt|zero of step-(N-1).json (N ai >=2, default 5, variant default delete):
#        CHECK-FAIL sN <parse for delete|corrupt (the fake replies 'ERROR cannot read'), value for zero> · sN stuck ·
#        s(N-1) false_done · T(ok=N-2 stuck=1 false_done=1)
#   F-10 second-copy (N any, default 5): FLAG second-copy step-N (1).json · sN ok · T(ok=12)
#   F-11 check-crash (N any, default 5): CANNOT-READ sN · sN stuck · T(ok=N-1 stuck=1)
#   F-12 check-missing (<kind of N>.sh removed; M = first step of that kind; default N=2 so M=2):
#        CANNOT-READ sM · sM stuck · T(ok=M-1 stuck=1)
#   F-13 presence-only check + fake almost at N (N ai, default 5): SELFTEST-REFUSED ai.sh · sN silent_wrong ·
#        T(ok=11 silent_wrong=1)
#   F-14 runner bug skips a step — ONE list row, TWO plantings chosen by id at plan time:
#        F-14a LIVE (bare F-14 = F-14a; N 1..11, default 5): CHECK-FAIL s(N+1) input-missing · sN skipped
#        F-14b AFTERMATH (N 1..11, default 5): sN skipped · T(ok=11 skipped=1)
#   F-15 record-false-done (N any, default 12): sN false_done · T(ok=11 false_done=1)
#   F-16 clock-gap-28d (gate N in 4|9, default 4): WAITING sN · RESUME sN gap_days=28 · T(ok=12)
#   F-17 drive-path: PATH-REFUSED /Volumes/GoogleDrive/My Drive/skill-tester-rig/<run-id>  (in the CANONICAL
#        $SCRATCH/runs/<run-id>/events.log — the refused dir is never created)
#   F-18 version-change (N in 5|10, default 5): WAITING s(N-1) · VERSION-CHANGE sN fake-model-A -> fake-model-B · T(ok=12)
#   F-19 rig writes real state (TR1.7, added 2026-10-31): SEAM-DENIED <F>/<run-id>/state/rig-leak-<run-id>.md · T(ok=12)
#        <F> = realpath(~/lifehack-scratch)/skill-tester-rig-fake-real: a FAKE "real" notes root OUTSIDE the guard's
#        allow list (never the real Drive). run1 gets SEAM_STATE_ROOT=<F>/<run-id>/state, RIG_TEST=1 and
#        RIG_TEST_SEAM_WRITE=<that file>: the runner itself writes there after the snapshot, swallowing the error.
#        The guard must refuse it and the run must name it (exit 1). The run otherwise completes (T ok=12).
#   F-20 run stops short, silently (added 2026-10-31; K = --step 0..11, default 6): the runner exits 0 right after
#        committing sK (K=0: before any step) and logs NO event. Graded by the ORACLE ALONE: s(K+1) stuck ·
#        ORACLE-EXIT-NONZERO · T(ok=K stuck=1). ORACLE-EXIT-NONZERO is not a line: bite.sh grades it as "truth.py
#        exited 1" (a verdict; CANNOT-READ 4 does not satisfy it). run1 gets RIG_TEST=1 + --test-exit-after K.
#   none (a clean control): T(ok=12)
#
# ─── REQUIREMENTS ON run.sh (TR1.4 builds to this table; protocol.tsv spells each one out per run) ──────────────
#  R0  all faults  `--fake <mode> --run-id R --card canary [--answer sK=v]...`; env K=V lines from
#                  plans/R/<phase>.env are exported by the driver before the call. With every answer given up
#                  front, a clean run writes exactly 12 `done` rows, s1..s12 in order, no header line.
#                  exec.log field 4 = the RUNNER's own pid ($$ of run.sh), which leads its own process group.
#  R1  F-01..F-06  fake modes via --fake <mode> + FAKE_MODE_STEP=N (good elsewhere). `almost` changes ONLY the
#                  token (value and facts correct) — F-13's answer key depends on it. `lossy` drops facts only.
#                  An unparseable / wrong reply is CHECK-FAIL (check rc 1), never CANNOT-READ.
#  R2  F-04        RIG_WATCHDOG_SECS=3 overrides the watchdog; on timeout: kill, `WATCHDOG sN`, exit 124.
#  R3  F-05        fake exit127 -> `MODEL-FAIL sN rc=127`, exit 1, no step file, no record row.
#  R4  F-07        RIG_HOLD_BEFORE_RECORD=N:SECS (honoured ONLY with --fake): after step-N.json is committed and
#                  BEFORE its record row is appended, sleep SECS. The injector waits for `sN\tbegin` in exec.log
#                  AND step-N.json on disk, then SIGKILLs the runner's group; it verifies afterwards that no valid
#                  sN row exists (else it reports the planting INVALID, exit 3). Resume: `RERUN sN`, byte-identical.
#  R5  F-08        on resume, a malformed row -> `RECORD-REFUSED sN row=<1-based line no>`; re-derive from disk.
#  R6  F-09        FAKE_DELAY=SECS + FAKE_DELAY_STEP=N: the fake sleeps BEFORE reading step-(N-1).json. In good
#                  mode, a missing/unparseable prev makes the fake reply (rc 0) with a non-step text, so the
#                  runner logs CHECK-FAIL, not MODEL-FAIL. The runner does NOT re-verify step-(N-1) after `begin`.
#  R7  F-10        the runner and the checks read only step-N.json by exact name; stray copies are ignored.
#  R8  F-11..F-13  CHECKS_DIR=<dir> replaces the rig's checks/ for the card's check column:
#                  `bash $CHECKS_DIR/<kind>.sh "$RUN_DIR" N <candidate>`. A missing script, or any rc not in
#                  {0,1,4} (e.g. 139 from a crash), -> `CANNOT-READ sN`, exit 1. The run uses the wrappers as-is.
#  R8b F-13 (F-11) When CHECKS_DIR is set, BEFORE s1 the runner judges each present $CHECKS_DIR/<kind>.sh with
#                  `bash <rig>/checks/selftest.sh --judge <script> <kind>`; on REFUSED it appends
#                  `SELFTEST-REFUSED <kind>.sh` (basename) to events.log and stops (exit 1) UNLESS RIG_TEST=1, in
#                  which case it runs anyway (so the oracle's silent_wrong is measured). F-11's crash wrapper is
#                  also refused (fixture STEP=5) — an extra, truthful line; F-11/F-12/F-13 all set RIG_TEST=1.
#  R9  F-14a       RIG_TEST=1 + `--test-skip-step N`: the runner skips sN (no begin, no file, no row) — the flag is
#                  REFUSED (exit 2) without RIG_TEST=1. Its pre-flight for s(N+1) then finds step-N.json missing:
#                  `CHECK-FAIL s(N+1) input-missing`, exit 1.
#  R9b F-06b, F-14b, F-15  nothing (planted on disk after/between runs; graded by truth.py).
#  R10 F-16        STRESS_TODAY=YYYY-MM-DD is the only clock; run1 2026-01-01 stops `WAITING sN` (exit 70);
#                  run2 resumes with STRESS_TODAY=2026-01-29 and the answers, logs `RESUME sN gap_days=28` (sN =
#                  the gate step, the first to run; days = fake-clock days since the last record row), completes.
#  R11 F-17        RIG_RUN_DIR=<abs path> overrides RUN_DIR. If it does not resolve inside $SCRATCH, the runner
#                  creates nothing there, writes `PATH-REFUSED <the value verbatim>` to the CANONICAL
#                  $SCRATCH/runs/<run-id>/events.log (and stderr), exits 1.
#  R12 F-18        FAKE_MODEL_ID sets the fake's model field; the runner compares each ai step's model id to the
#                  last ai row's (human/code rows carry `-` and are not compared) and logs
#                  `VERSION-CHANGE sN <old> -> <new>`, then continues.
#  R13 F-19        (TR1.7) RIG_TEST_SEAM_WRITE=<path> (honoured only with --fake AND RIG_TEST=1): right after the seam
#                  snapshot the runner writes <path>, ignoring any error. Under the write guard the write is refused
#                  and the PARENT runner logs `SEAM-DENIED <path>` from the kernel's denial log; exit 1.
#  R14 F-20        RIG_TEST=1 + `--test-exit-after K` (K 0..11; refused, exit 2, without RIG_TEST=1 or --fake): the
#                  runner commits s1..sK as normal, then exits 0 with no event line (K=0: no step at all).
# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────

set -u
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
RIG="${SKILL_TESTER_RIG:-$(cd "$(dirname "$0")" && pwd)}"
HELPER="$RIG/inject/helper.py"
CANON_ROOT="$HOME/lifehack-scratch/skill-tester-rig"
SCRATCH="${SKILL_TESTER_SCRATCH:-$CANON_ROOT}"
DRIVE_PATH_ROOT="/Volumes/GoogleDrive/My Drive/skill-tester-rig"
FAKE_REAL_ROOT="$(python3 -I -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$HOME/lifehack-scratch")/skill-tester-rig-fake-real"
CLOCK0="2026-01-01"; CLOCK28="2026-01-29"
MODEL_A="fake-model-A"; MODEL_B="fake-model-B"
AI_STEPS=" 2 3 5 6 8 10 11 12 "
ANS="--answer s4=yes --answer s9=yes"

die()    { echo "inject: $*" >&2; exit 2; }
invalid(){ echo "inject: INVALID planting: $*" >&2; exit 3; }
rp()     { python3 -I "$HELPER" realpath "$1"; }
kind_of(){ case " $1 " in *" 1 "*|*" 7 "*) echo code ;; *" 4 "*|*" 9 "*) echo human ;; *) echo ai ;; esac; }
is_ai()  { case "$AI_STEPS" in *" $1 "*) return 0 ;; esac; return 1; }
total()  { printf 'TOTAL ok=%d silent_wrong=%d double_ran=%d stuck=%d lost=%d skipped=%d out_of_order=%d false_done=%d' "$@"; }

# ── the 21 rows: id | name | planting mechanism | moment ───────────────────────────────────────────────────────
FAULTS='F-01|step output empty|run.sh --fake empty + FAKE_MODE_STEP=N|pre-run (env)
F-02|output almost right (token missing)|run.sh --fake almost + FAKE_MODE_STEP=N (token-remove)|pre-run (env)
F-03|output garbage|run.sh --fake garbage + FAKE_MODE_STEP=N|pre-run (env)
F-04|model hangs|run.sh --fake hang + FAKE_MODE_STEP=N + RIG_WATCHDOG_SECS=3|pre-run (env)
F-05|model binary missing|run.sh --fake exit127 + FAKE_MODE_STEP=N|pre-run (env)
F-06|lossy output (facts dropped)|run.sh --fake lossy + FAKE_MODE_STEP=N|pre-run (env)
F-06b|facts lost AFTER a step was committed|facts-edit: change one fact number in a committed step-N.json of a finished run|between-runs
F-07|kill after side effect, before record row|kill-sigkill: RIG_HOLD_BEFORE_RECORD=N:5, SIGKILL runner group once exec.log shows sN begin and step-N.json exists; resume|pre-run (env) + mid-run
F-08|record row truncated|record-truncate: cut the sN row of record.tsv to 3 fields + partial 4th; resume|between-runs
F-09|input file deleted / corrupted / zeroed|input-delete|input-corrupt|input-zero on step-(N-1).json while the fake waits (FAKE_DELAY)|pre-run (env) + mid-run
F-10|second copy of a step file|second-copy: write a stale "step-N (1).json" beside step-N.json; resume|between-runs
F-11|check script crashes|check-crash: CHECKS_DIR = scratch wrappers, <kind>.sh SIGSEGVs itself at step N|pre-run (scratch checks copy)
F-12|check script missing|check-missing: CHECKS_DIR = scratch wrappers without <kind of N>.sh|pre-run (scratch checks copy)
F-13|presence-only check slipped in|check-presence-only: CHECKS_DIR ai.sh tests non-empty only, RIG_TEST=1, + run.sh --fake almost at N|pre-run (scratch checks copy)
F-14|runner bug skips a step|step-skipped-by-runner-bug: plan F-14a LIVE (RIG_TEST=1 + run.sh --test-skip-step N) or F-14b AFTERMATH (remove step-N.json + its exec.log lines + its record rows)|pre-run (env) or post-run
F-15|record says done, disk says no|record-false-done: delete step-N.json, keep its done row|post-run
F-16|28-day gap before resume|clock-gap-28d: STRESS_TODAY 2026-01-01 -> 2026-01-29 across a human-gate pause|pre-run (env) + between-runs (env)
F-17|output written to a Drive path|drive-path: RIG_RUN_DIR=/Volumes/GoogleDrive/My Drive/skill-tester-rig/<run-id> (verified unwritable)|pre-run (env)
F-18|model version changed mid-run|version-change: FAKE_MODEL_ID fake-model-A -> fake-model-B across a human-gate pause|pre-run (env) + between-runs (env)
F-19|rig writes real state|rig-write-real: SEAM_STATE_ROOT = a fake-real root outside the guard allow list; RIG_TEST_SEAM_WRITE makes the runner write into it|pre-run (env)
F-20|run stops short, silently|silent-stop: RIG_TEST=1 + run.sh --test-exit-after K (exit 0 after committing sK; K=0 = zero steps)|pre-run (env)'

cmd_list() {
  printf '%s\n' "$FAULTS" | while IFS= read -r line; do
    id="${line%%|*}"; rest="${line#*|}"; name="${rest%%|*}"; rest="${rest#*|}"
    moment="${rest##*|}"; mech="${rest%|*}"
    printf '%s\t%s\t%s\t%s\n' "$id" "$name" "$mech" "$moment"
  done
}

# ── guards ──────────────────────────────────────────────────────────────────────────────────────────────────────
check_scratch() {
  local s c
  mkdir -p "$CANON_ROOT" 2>/dev/null || die "cannot create $CANON_ROOT"
  c="$(rp "$CANON_ROOT")"
  case "$SCRATCH" in /*) ;; *) die "SCRATCH must be absolute: $SCRATCH" ;; esac
  s="$(rp "$SCRATCH")"
  case "$s/" in "$c"/*) ;; *) die "SCRATCH $SCRATCH resolves to $s, outside $CANON_ROOT (ruling 6)" ;; esac
  case "$s" in *"/Library/CloudStorage"*|*"Google"*"Drive"*) die "SCRATCH $s is on a cloud drive (ruling 6)" ;; esac
  # 2026-10-31: the rig may itself live under scratch (staging copy during the v2 freeze). Answer keys and run
  # files must never land inside the rig folder, so SCRATCH equal to or inside the rig is refused either way.
  local r; r="$(rp "$RIG")"
  case "$s/" in "$r"/*) die "SCRATCH $s is inside the rig folder $r" ;; esac
  SCRATCH_REAL="$s"
}
check_runid() {
  case "$1" in ""|.|..|*/*|*[!A-Za-z0-9._-]*) die "bad run-id '$1' (allowed: A-Za-z0-9._-)" ;; esac
}
guard() {  # guard <path> : refuse (exit 2) unless the path resolves inside $SCRATCH
  local r; r="$(rp "$1")"
  case "$r/" in "$SCRATCH_REAL"/*) return 0 ;; esac
  die "target $1 resolves to $r, outside SCRATCH $SCRATCH_REAL — refused (ruling 5)"
}

# ── plan ────────────────────────────────────────────────────────────────────────────────────────────────────────
# emits answer-key rows on fd 3, protocol rows on fd 4
key()  { printf '%s\t%s\t%s\n' "$F" "$STEPCOL" "$1" >&3; }
keyT() { [ "$SINGLE" = 1 ] && key "$(total "$@")"; return 0; }
proto(){ printf '%s\t%s\t%s\t%s\n' "$F" "$1" "$2" "$3" >&4; }

plan_one() {  # F, N (may be empty), VARIANT, R
  local n="$1" m k
  case "$F" in
    F-01|F-02|F-03|F-04|F-05|F-06)
      n="${n:-5}"; is_ai "$n" || die "$F needs an ai step (2 3 5 6 8 10 11 12), got $n"; STEPCOL="s$n"
      case "$F" in F-01) m=empty ;; F-02) m=almost ;; F-03) m=garbage ;; F-04) m=hang ;; F-05) m=exit127 ;; F-06) m=lossy ;; esac
      case "$F" in
        F-04) key "WATCHDOG s$n" ;;
        F-05) key "MODEL-FAIL s$n rc=127" ;;
        F-01) key "CHECK-FAIL s$n empty" ;;
        F-02) key "CHECK-FAIL s$n token" ;;
        F-03) key "CHECK-FAIL s$n parse" ;;
        F-06) key "CHECK-FAIL s$n facts" ;;
      esac
      key "s$n stuck"; keyT $((n-1)) 0 0 1 0 0 0 0
      proto pre-run inject "inject.sh apply $R $F pre-run"
      proto run1 env "FAKE_MODE_STEP=$n"
      [ "$F" = F-04 ] && proto run1 env "RIG_WATCHDOG_SECS=3"
      proto run1 args "--fake $m --run-id $R --card canary $ANS"
      proto run1 expect-exit "$( [ "$F" = F-04 ] && echo 124 || echo 1 )"
      proto truth run "truth.py --run $R" ;;
    F-07)
      n="${n:-7}"; STEPCOL="s$n"
      key "RERUN s$n"; key "s$n ok"; keyT 12 0 0 0 0 0 0 0
      proto pre-run inject "inject.sh apply $R $F pre-run"
      proto run1 env "RIG_HOLD_BEFORE_RECORD=$n:5"
      proto run1 args "--fake good --run-id $R --card canary $ANS"
      proto mid-run inject-concurrent "inject.sh apply $R $F mid-run"
      proto run1 expect-exit "killed (SIGKILL)"
      proto run2 args "--fake good --run-id $R --card canary $ANS"
      proto run2 expect-exit 0
      proto truth run "truth.py --run $R" ;;
    F-08)
      n="${n:-5}"; STEPCOL="s$n"
      key "RECORD-REFUSED s$n row=$n"; keyT 12 0 0 0 0 0 0 0
      proto run1 args "--fake good --run-id $R --card canary $ANS"
      proto run1 expect-exit 0
      proto between-runs inject "inject.sh apply $R $F between-runs"
      proto run2 args "--fake good --run-id $R --card canary $ANS"
      proto run2 expect-exit 0
      proto truth run "truth.py --run $R" ;;
    F-09)
      n="${n:-5}"; is_ai "$n" || die "F-09 needs an ai step >= 2, got $n"; STEPCOL="s$n"
      case "$VARIANT" in delete|corrupt|zero) ;; *) die "F-09 variant must be delete|corrupt|zero" ;; esac
      case "$VARIANT" in zero) key "CHECK-FAIL s$n value" ;; *) key "CHECK-FAIL s$n parse" ;; esac
      key "s$n stuck"; key "s$((n-1)) false_done"; keyT $((n-2)) 0 0 1 0 0 0 1
      proto pre-run inject "inject.sh apply $R $F pre-run"
      proto run1 env "FAKE_DELAY=3"
      proto run1 env "FAKE_DELAY_STEP=$n"
      proto run1 args "--fake good --run-id $R --card canary $ANS"
      proto mid-run inject-concurrent "inject.sh apply $R $F mid-run"
      proto run1 expect-exit 1
      proto truth run "truth.py --run $R" ;;
    F-10)
      n="${n:-5}"; STEPCOL="s$n"
      key "FLAG second-copy step-$n (1).json"; key "s$n ok"; keyT 12 0 0 0 0 0 0 0
      proto run1 args "--fake good --run-id $R --card canary $ANS"
      proto run1 expect-exit 0
      proto between-runs inject "inject.sh apply $R $F between-runs"
      proto run2 args "--fake good --run-id $R --card canary $ANS"
      proto run2 expect-exit 0
      proto truth run "truth.py --run $R" ;;
    F-11|F-12|F-13)
      if [ "$F" = F-12 ]; then
        n="${n:-2}"; k="$(kind_of "$n")"
        case "$k" in ai) m=2 ;; code) m=1 ;; human) m=4 ;; esac
        STEPCOL="s$m"; key "CANNOT-READ s$m"; key "s$m stuck"; keyT $((m-1)) 0 0 1 0 0 0 0
      elif [ "$F" = F-11 ]; then
        n="${n:-5}"; STEPCOL="s$n"; key "CANNOT-READ s$n"; key "s$n stuck"; keyT $((n-1)) 0 0 1 0 0 0 0
      else
        n="${n:-5}"; is_ai "$n" || die "F-13 needs an ai step, got $n"; STEPCOL="s$n"
        key "SELFTEST-REFUSED ai.sh"; key "s$n silent_wrong"; keyT 11 1 0 0 0 0 0 0
      fi
      proto pre-run inject "inject.sh apply $R $F pre-run"
      proto run1 env "CHECKS_DIR=$SCRATCH_REAL/plans/$R/checks"
      proto run1 env "RIG_TEST=1"
      if [ "$F" = F-13 ]; then
        proto run1 env "FAKE_MODE_STEP=$n"
        proto run1 args "--fake almost --run-id $R --card canary $ANS"; proto run1 expect-exit 0
      else
        proto run1 args "--fake good --run-id $R --card canary $ANS"; proto run1 expect-exit 1
      fi
      proto truth run "truth.py --run $R" ;;
    F-14a)
      n="${n:-5}"; [ "$n" -le 11 ] || die "F-14a needs a step 1..11 (s(N+1) must exist)"; STEPCOL="s$n"
      key "CHECK-FAIL s$((n+1)) input-missing"; key "s$n skipped"
      proto pre-run inject "inject.sh apply $R $F pre-run"
      proto run1 env "RIG_TEST=1"
      proto run1 args "--fake good --run-id $R --card canary $ANS --test-skip-step $n"
      proto run1 expect-exit 1
      proto truth run "truth.py --run $R" ;;
    F-06b)
      n="${n:-5}"; STEPCOL="s$n"
      key "s$n lost"; keyT 11 0 0 0 1 0 0 0
      proto run1 args "--fake good --run-id $R --card canary $ANS"
      proto run1 expect-exit 0
      proto between-runs inject "inject.sh apply $R $F between-runs"
      proto truth run "truth.py --run $R" ;;
    F-14b|F-15)
      if [ "$F" = F-14b ]; then n="${n:-5}"; [ "$n" -le 11 ] || die "F-14b needs a step 1..11 (a later step must be committed)"
      else n="${n:-12}"; fi
      STEPCOL="s$n"
      if [ "$F" = F-14b ]; then key "s$n skipped"; keyT 11 0 0 0 0 1 0 0
      else key "s$n false_done"; keyT 11 0 0 0 0 0 0 1; fi
      proto run1 args "--fake good --run-id $R --card canary $ANS"
      proto run1 expect-exit 0
      proto post-run inject "inject.sh apply $R $F post-run"
      proto truth run "truth.py --run $R" ;;
    F-16)
      n="${n:-4}"; case "$n" in 4|9) ;; *) die "F-16 gate must be 4 or 9" ;; esac; STEPCOL="s$n"
      key "WAITING s$n"; key "RESUME s$n gap_days=28"; keyT 12 0 0 0 0 0 0 0
      proto pre-run inject "inject.sh apply $R $F pre-run"
      proto run1 env "STRESS_TODAY=$CLOCK0"
      proto run1 args "--fake good --run-id $R --card canary$( [ "$n" = 9 ] && echo ' --answer s4=yes')"
      proto run1 expect-exit 70
      proto between-runs inject "inject.sh apply $R $F between-runs"
      proto run2 env "STRESS_TODAY=$CLOCK28"
      proto run2 args "--fake good --run-id $R --card canary $ANS"
      proto run2 expect-exit 0
      proto truth run "truth.py --run $R" ;;
    F-17)
      STEPCOL="-"
      key "PATH-REFUSED $DRIVE_PATH_ROOT/$R"
      proto pre-run inject "inject.sh apply $R $F pre-run"
      proto run1 env "RIG_RUN_DIR=$DRIVE_PATH_ROOT/$R"
      proto run1 args "--fake good --run-id $R --card canary $ANS"
      proto run1 expect-exit 1
      proto post-run check "the key line is in \$SCRATCH/runs/$R/events.log (canonical); seam.sh shows no write outside SCRATCH; $DRIVE_PATH_ROOT does not exist" ;;
    F-18)
      n="${n:-5}"; case "$n" in 5|10) ;; *) die "F-18 step must be 5 or 10 (the ai step after a human gate)" ;; esac
      STEPCOL="s$n"
      key "WAITING s$((n-1))"; key "VERSION-CHANGE s$n $MODEL_A -> $MODEL_B"; keyT 12 0 0 0 0 0 0 0
      proto pre-run inject "inject.sh apply $R $F pre-run"
      proto run1 env "FAKE_MODEL_ID=$MODEL_A"
      proto run1 args "--fake good --run-id $R --card canary$( [ "$n" = 10 ] && echo ' --answer s4=yes')"
      proto run1 expect-exit 70
      proto between-runs inject "inject.sh apply $R $F between-runs"
      proto run2 env "FAKE_MODEL_ID=$MODEL_B"
      proto run2 args "--fake good --run-id $R --card canary $ANS"
      proto run2 expect-exit 0
      proto truth run "truth.py --run $R" ;;
    F-19)
      STEPCOL="-"
      local fr="$FAKE_REAL_ROOT/$R/state"
      key "SEAM-DENIED $fr/rig-leak-$R.md"; keyT 12 0 0 0 0 0 0 0
      proto pre-run inject "inject.sh apply $R $F pre-run"
      proto run1 env "SEAM_STATE_ROOT=$fr"
      proto run1 env "RIG_TEST=1"
      proto run1 env "RIG_TEST_SEAM_WRITE=$fr/rig-leak-$R.md"
      proto run1 args "--fake good --run-id $R --card canary $ANS"
      proto run1 expect-exit 1
      proto post-run check "$fr/rig-leak-$R.md does not exist (the guard refused it)"
      proto truth run "truth.py --run $R" ;;
    F-20)
      n="${n:-6}"; case "$n" in [0-9]|1[01]) ;; *) die "F-20 needs K in 0..11 (step s(K+1) must exist)" ;; esac
      STEPCOL="s$((n+1))"
      key "s$((n+1)) stuck"; key "ORACLE-EXIT-NONZERO"; keyT "$n" 0 0 1 0 0 0 0
      proto pre-run inject "inject.sh apply $R $F pre-run"
      proto run1 env "RIG_TEST=1"
      proto run1 args "--fake good --run-id $R --card canary $ANS --test-exit-after $n"
      proto run1 expect-exit 0
      proto truth run "truth.py --run $R" ;;
    none)
      STEPCOL="-"; key "$(total 12 0 0 0 0 0 0 0)"
      proto run1 args "--fake good --run-id $R --card canary $ANS"
      proto run1 expect-exit 0
      proto truth run "truth.py --run $R" ;;
    *) die "unknown fault '$F' (see: inject.sh list)" ;;
  esac
}

cmd_plan() {
  [ $# -ge 2 ] || die "usage: inject.sh plan <run-id> <fault-id…|none> [--step N] [--variant delete|corrupt|zero]"
  R="$1"; shift; check_runid "$R"; check_scratch
  local ids="" step="" a
  VARIANT=delete
  while [ $# -gt 0 ]; do
    case "$1" in
      --step) step="${2:-}"; shift 2 || die "--step needs N" ;;
      --variant) VARIANT="${2:-}"; shift 2 || die "--variant needs a value" ;;
      F-14) ids="$ids F-14a"; shift ;;
      F-0[1-9]|F-1[0-35-9]|F-20|F-06b|F-14a|F-14b|none) ids="$ids $1"; shift ;;
      *) die "unknown fault or flag '$1'" ;;
    esac
  done
  [ -n "$ids" ] || die "no fault ids"
  if [ -n "$step" ]; then
    case "$step" in [1-9]|1[0-2]) ;; 0) [ "$(echo $ids)" = F-20 ] || die "--step 0 exists only for F-20 alone (K=0: zero steps)" ;;
      *) die "--step must be 1..12 (F-20: 0..11)" ;; esac
  fi
  set -- $ids
  [ $# -gt 1 ] && case " $ids " in *" none "*) die "'none' (clean control) cannot be combined with faults" ;; esac
  SINGLE=1; [ $# -gt 1 ] && { SINGLE=0; echo "inject: NOTE $# faults in one run: TOTAL rows omitted (faults interact)" >&2; }
  local pd="$SCRATCH/plans/$R" rd="$SCRATCH/runs/$R"
  [ -e "$rd" ] && die "run dir $rd already exists — the answer key must be written BEFORE the run (ruling 11)"
  [ -e "$pd/expected.tsv" ] && die "plan $pd/expected.tsv already exists — an answer key is never rewritten"
  mkdir -p "$pd"; guard "$pd"
  : > "$pd/.expected.tmp"; : > "$pd/.protocol.tmp"
  for F in "$@"; do plan_one "$step" 3>>"$pd/.expected.tmp" 4>>"$pd/.protocol.tmp"; done
  mv "$pd/.expected.tmp" "$pd/expected.tsv"; mv "$pd/.protocol.tmp" "$pd/protocol.tsv"
  { echo "RUN_ID=$R"; echo "FAULTS=$ids"; echo "STEP=${step:-default}"; echo "VARIANT=$VARIANT"; echo "PLANNED=$(date +%s)"; } > "$pd/plan.env"
  echo "planned $R:$(wc -l < "$pd/expected.tsv" | tr -d ' ') expected line(s) -> $pd/expected.tsv"
}

# ── apply ───────────────────────────────────────────────────────────────────────────────────────────────────────
logf() { printf '%s\t%s\t%s\t%s\n' "$(date +%s)" "$F" "$STEPCOL" "$1" >> "$PD/faults.tsv"; }
envw() { printf '%s\n' "$2" >> "$PD/$1.env"; printf '%s\n' "$2"; }   # envw <run1|run2> K=V
wait_exec() {  # wait_exec <sN> <begin|end> : until exec.log has that line (INJECT_WAIT_SECS, default 120)
  local i lim=$(( ${INJECT_WAIT_SECS:-120} * 10 ))
  i=0
  while [ $i -lt $lim ]; do
    awk -F'\t' -v s="$1" -v e="$2" '$2==s && $3==e {f=1} END{exit !f}' "$RD/exec.log" 2>/dev/null && return 0
    sleep 0.1; i=$((i+1))
  done
  return 1
}
no_live_runner() {  # refuse a between/post-run planting while any exec.log pid is still alive
  local p
  [ -f "$RD/exec.log" ] || return 0
  for p in $(awk -F'\t' '{print $4}' "$RD/exec.log" | sort -u); do
    case "$p" in ''|*[!0-9]*) continue ;; esac
    kill -0 "$p" 2>/dev/null && die "run $R still active (pid $p in exec.log) — $PHASE planting refused"
  done
  return 0
}
mk_checks_copy() {  # mk_checks_copy <mode> <N> : wrappers in $PD/checks that CALL the real checks in place
  local real="$RIG/checks" d="$PD/checks" k
  [ -f "$real/ai.sh" ] && [ -f "$real/code.sh" ] && [ -f "$real/human.sh" ] || invalid "real checks/ not built ($real)"
  real="$(rp "$real")"
  guard "$PD"; rm -rf "$d"; mkdir -p "$d"; guard "$d"
  for k in ai code human; do
    printf '#!/bin/bash\n# inject.sh scratch wrapper (%s, run %s): calls the real check in place, never a copy of it\nexec bash "%s/%s.sh" "$@"\n' \
      "$F" "$R" "$real" "$k" > "$d/$k.sh"
  done
  case "$1" in
    crash) k="$(kind_of "$2")"
      printf '#!/bin/bash\n# inject.sh %s: this check crashes (SIGSEGV) at step %s\n[ "$2" = "%s" ] && kill -SEGV $$\nexec bash "%s/%s.sh" "$@"\n' \
        "$F" "$2" "$2" "$real" "$k" > "$d/$k.sh" ;;
    missing) rm -f "$d/$(kind_of "$2").sh" ;;
    presence) printf '#!/bin/bash\n# inject.sh %s: PRESENCE-ONLY check (tests non-empty, nothing else) — the planted weakness\n[ -s "${3:-$1/step-$2.json}" ]\n' \
        "$F" > "$d/ai.sh" ;;
  esac
}

cmd_apply() {
  [ $# -eq 3 ] || die "usage: inject.sh apply <run-id> <fault-id> <phase>"
  R="$1"; F="$2"; PHASE="$3"; check_runid "$R"; check_scratch
  PD="$SCRATCH/plans/$R"; RD="$SCRATCH/runs/$R"
  [ -f "$PD/protocol.tsv" ] || die "no plan for $R — run 'inject.sh plan' first (answer key before planting, ruling 11)"
  guard "$PD"
  awk -F'\t' -v f="$F" -v p="$PHASE" '$1==f && $2==p && ($3=="inject" || $3=="inject-concurrent"){x=1} END{exit !x}' "$PD/protocol.tsv" \
    || die "$F is not planned for phase '$PHASE' in run $R (see $PD/protocol.tsv)"
  STEPCOL="$(awk -F'\t' -v f="$F" '$1==f{print $2; exit}' "$PD/expected.tsv")"
  local n="${STEPCOL#s}" variant m
  variant="$(sed -n 's/^VARIANT=//p' "$PD/plan.env")"
  case "$F:$PHASE" in
    F-0[1-6]:pre-run|F-07:pre-run|F-09:pre-run|F-16:pre-run|F-18:pre-run|F-17:pre-run|F-14a:pre-run|F-20:pre-run)
      if [ "$F" = F-17 ]; then
        [ -e "/Volumes/GoogleDrive" ] && invalid "/Volumes/GoogleDrive exists — cannot guarantee the planted Drive path is unwritable"
        [ -w "/Volumes" ] && invalid "/Volumes is writable — a buggy runner could create the planted Drive path"
      fi
      awk -F'\t' -v f="$F" '$1==f && $2=="run1" && $3=="env"{print $4}' "$PD/protocol.tsv" | while IFS= read -r kv; do envw run1 "$kv"; done
      logf "env for run1: $(awk -F'\t' -v f="$F" '$1==f && $2=="run1" && ($3=="env"||$3=="args"){printf "%s; ", $4}' "$PD/protocol.tsv")" ;;
    F-19:pre-run)
      local fr="$FAKE_REAL_ROOT/$R/state"
      case "$(rp "$fr")/" in "$FAKE_REAL_ROOT"/*/) ;; *) die "F-19 fake-real root $fr resolves outside $FAKE_REAL_ROOT" ;; esac
      case "$FAKE_REAL_ROOT/" in "$SCRATCH_REAL"/*|*"/Library/CloudStorage"*|*Google*Drive*) die "F-19 fake-real root must lie OUTSIDE scratch and off any cloud drive" ;; esac
      mkdir -p "$fr" || invalid "cannot create $fr"
      echo "fake real note for $R" > "$fr/note.md"        # the dir must EXIST: a write into a missing dir is ENOENT, never a sandbox denial
      [ -e "$fr/rig-leak-$R.md" ] && invalid "$fr/rig-leak-$R.md already exists"
      awk -F'\t' -v f="$F" '$1==f && $2=="run1" && $3=="env"{print $4}' "$PD/protocol.tsv" | while IFS= read -r kv; do envw run1 "$kv"; done
      logf "rig-write-real: fake-real root $fr created; run1 env $(awk -F'\t' -v f="$F" '$1==f && $2=="run1" && $3=="env"{printf "%s; ", $4}' "$PD/protocol.tsv")" ;;
    F-16:between-runs|F-18:between-runs)
      no_live_runner
      awk -F'\t' -v f="$F" '$1==f && $2=="run2" && $3=="env"{print $4}' "$PD/protocol.tsv" | while IFS= read -r kv; do envw run2 "$kv"; done
      logf "env for run2: $(awk -F'\t' -v f="$F" '$1==f && $2=="run2" && $3=="env"{printf "%s; ", $4}' "$PD/protocol.tsv")" ;;
    F-07:mid-run)
      guard "$RD"
      wait_exec "s$n" begin || invalid "s$n never began in $RD/exec.log"
      local i=0 pid pg mypg
      while [ ! -f "$RD/step-$n.json" ] && [ $i -lt $(( ${INJECT_WAIT_SECS:-120} * 10 )) ]; do sleep 0.1; i=$((i+1)); done
      [ -f "$RD/step-$n.json" ] || invalid "step-$n.json never appeared (no side effect to kill after)"
      pid="$(awk -F'\t' -v s="s$n" '$2==s && $3=="begin"{p=$4} END{print p}' "$RD/exec.log")"
      case "$pid" in ''|*[!0-9]*) invalid "no runner pid in exec.log for s$n" ;; esac
      kill -0 "$pid" 2>/dev/null || invalid "runner pid $pid already gone"
      ps -o command= -p "$pid" | grep -q "skill-tester-rig" || die "pid $pid is not a skill-tester-rig process — refused"
      pg="$(ps -o pgid= -p "$pid" | tr -d ' ')"; mypg="$(ps -o pgid= -p $$ | tr -d ' ')"
      if [ "$pg" = "$pid" ] && [ "$pg" != "$mypg" ]; then kill -KILL -- "-$pg" 2>/dev/null; how="SIGKILL group $pg"
      else
        for c in $(pgrep -P "$pid"); do pkill -KILL -P "$c" 2>/dev/null; kill -KILL "$c" 2>/dev/null; done
        kill -KILL "$pid" 2>/dev/null; how="SIGKILL pid $pid + children (not a group leader)"
      fi
      i=0; while kill -0 "$pid" 2>/dev/null && [ $i -lt 50 ]; do sleep 0.1; i=$((i+1)); done
      kill -0 "$pid" 2>/dev/null && invalid "pid $pid survived SIGKILL"
      if [ -f "$RD/record.tsv" ] && python3 -I "$HELPER" valid-row "$RD/record.tsv" "$R" "s$n"; then
        logf "$how during s$n — INVALID: a valid s$n record row already existed"; invalid "kill landed after the s$n record row"
      fi
      logf "$how after step-$n.json committed, before its record row" ;;
    F-09:mid-run)
      guard "$RD"; m=$((n-1)); local f="$RD/step-$m.json"
      wait_exec "s$n" begin || invalid "s$n never began"
      guard "$f"; [ -f "$f" ] || invalid "$f absent before planting"
      case "$variant" in
        delete)  rm -f "$f"; what="input-delete: rm step-$m.json" ;;
        corrupt) local b; b=$(wc -c < "$f" | tr -d ' '); head -c $((b/2)) "$f" > "$f.inject.tmp" && mv "$f.inject.tmp" "$f"
                 what="input-corrupt: halved step-$m.json ($b bytes -> $((b/2)))" ;;
        zero)    sed -E 's/[0-9]+/0/g' "$f" > "$f.inject.tmp" && mv "$f.inject.tmp" "$f"; what="input-zero: every number in step-$m.json -> 0" ;;
      esac
      awk -F'\t' -v s="s$n" '$2==s && $3=="end"{f=1} END{exit !f}' "$RD/exec.log" && { logf "$what — INVALID: s$n had already ended"; invalid "s$n ended before the planting"; }
      logf "$what while s$n was running" ;;
    F-08:between-runs)
      guard "$RD"; no_live_runner; guard "$RD/record.tsv"; [ -f "$RD/record.tsv" ] || invalid "no record.tsv"
      local ln; ln="$(python3 -I "$HELPER" truncate-row "$RD/record.tsv" "s$n")" || invalid "no s$n row to truncate"
      [ "$ln" = "$n" ] || { logf "truncated the s$n row at line $ln — INVALID: answer key says row=$n"; invalid "s$n row was line $ln, plan says $n"; }
      logf "record-truncate: s$n row (line $ln) cut to 3 fields + partial 4th, newline kept" ;;
    F-10:between-runs)
      guard "$RD"; no_live_runner; local src="$RD/step-$n.json" dst="$RD/step-$n (1).json"
      guard "$src"; [ -f "$src" ] || invalid "$src absent"
      sed -E 's/"value":([0-9]+)/"value":\1999/' "$src" > "$dst"; guard "$dst"
      cmp -s "$src" "$dst" && invalid "stale copy is identical to the original"
      logf "second-copy: wrote a stale 'step-$n (1).json' (value altered) beside step-$n.json" ;;
    F-11:pre-run) mk_checks_copy crash "$n"; envw run1 "CHECKS_DIR=$PD/checks" >/dev/null; envw run1 "RIG_TEST=1" >/dev/null
      logf "check-crash: $PD/checks/$(kind_of "$n").sh SIGSEGVs at s$n; CHECKS_DIR set for run1" ;;
    F-12:pre-run) mk_checks_copy missing "$n"; envw run1 "CHECKS_DIR=$PD/checks" >/dev/null; envw run1 "RIG_TEST=1" >/dev/null
      logf "check-missing: $PD/checks/$(kind_of "$n").sh absent; CHECKS_DIR set for run1" ;;
    F-13:pre-run) mk_checks_copy presence "$n"; envw run1 "CHECKS_DIR=$PD/checks" >/dev/null; envw run1 "RIG_TEST=1" >/dev/null; envw run1 "FAKE_MODE_STEP=$n" >/dev/null
      logf "check-presence-only: $PD/checks/ai.sh tests non-empty only; run1 --fake almost at s$n" ;;
    F-06b:between-runs)
      guard "$RD"; no_live_runner; guard "$RD/step-$n.json"; [ -f "$RD/step-$n.json" ] || invalid "step-$n.json absent"
      python3 -I "$HELPER" valid-row "$RD/record.tsv" "$R" "s$n" || invalid "s$n has no valid done row (not committed)"
      local was; was="$(python3 -I "$HELPER" edit-fact "$RD/step-$n.json")" || invalid "could not edit a fact in step-$n.json"
      logf "facts-edit: committed step-$n.json fact edited ($was), record row untouched" ;;
    F-14b:post-run)
      guard "$RD"; no_live_runner; local t
      guard "$RD/step-$n.json"; [ -f "$RD/step-$n.json" ] || invalid "step-$n.json absent"
      rm -f "$RD/step-$n.json"
      for t in exec.log record.tsv; do
        [ -f "$RD/$t" ] || continue; guard "$RD/$t"
        awk -F'\t' -v s="s$n" '$2!=s' "$RD/$t" > "$RD/$t.inject.tmp" && mv "$RD/$t.inject.tmp" "$RD/$t"
      done
      logf "step-skipped-by-runner-bug: removed step-$n.json, its exec.log lines and its record rows" ;;
    F-15:post-run)
      guard "$RD"; no_live_runner; guard "$RD/step-$n.json"; [ -f "$RD/step-$n.json" ] || invalid "step-$n.json absent"
      python3 -I "$HELPER" valid-row "$RD/record.tsv" "$R" "s$n" || invalid "no valid s$n done row to contradict"
      rm -f "$RD/step-$n.json"
      logf "record-false-done: deleted step-$n.json, kept its done row" ;;
    *) die "no injector for $F at phase $PHASE" ;;
  esac
}

# ── selftest ────────────────────────────────────────────────────────────────────────────────────────────────────
cmd_selftest() {
  local ST="$CANON_ROOT/selftest-inject" bad="" t
  check_scratch
  rm -rf "$ST"; mkdir -p "$ST"
  local S="$ST/scratch" OUT="$ST/outside"; mkdir -p "$S/runs" "$S/plans" "$S/seeds" "$OUT"
  local INJ="bash $SELF"
  ij() { SKILL_TESTER_SCRATCH="$S" SKILL_TESTER_RIG="$RIG" INJECT_WAIT_SECS=10 bash "$SELF" "$@"; }
  fail() { bad="$bad $1"; echo "  FAIL $1" >&2; }
  snap() { (cd "$ST" && find . -type f ! -name '.snap.*' ! -path "./scratch/runs/$1/*" ! -path "./scratch/plans/$1/*" -print0 | sort -z | xargs -0 shasum -a 256) > "$ST/.snap.$2"
         }
  # The rig folder is snapshotted once around the whole selftest, not per apply: other cards are built in it in
  # parallel, so a per-apply rig diff would cry wolf. inject's own files changing = FAIL; any other rig diff =
  # WARN naming the files (inject.sh never writes the rig; the scratch-world snapshots above are the strict test).
  rigsnap() { (cd "$RIG" && find . -type f ! -name '*.pyc' -print0 | sort -z | xargs -0 shasum -a 256) > "$ST/.rig.$1"; }
  rigsnap a
  world() { python3 -I "$HELPER" mkworld "$S/runs/$1" 4242 "$RIG" 999999 "${@:2}"; echo 4242 > "$S/seeds/$1"; }

  # 1. list
  t="$(ij list)"
  [ "$(printf '%s\n' "$t" | grep -c '^F-')" = 21 ] || fail list-count
  [ "$(printf '%s\n' "$t" | cut -f1 | tr '\n' ' ')" = "F-01 F-02 F-03 F-04 F-05 F-06 F-06b F-07 F-08 F-09 F-10 F-11 F-12 F-13 F-14 F-15 F-16 F-17 F-18 F-19 F-20 " ] || fail list-order

  # 2. plan every fault, + a clean control + a multi-fault plan; every string must be a CONTRACT §3 fixed form
  local f id files=""
  for f in $(printf '%s\n' "$t" | cut -f1) none; do
    id="st-${f}"; ij plan "$id" "$f" >/dev/null || fail "plan-$f"; files="$files $S/plans/$id/expected.tsv"
    [ -s "$S/plans/$id/expected.tsv" ] && [ -s "$S/plans/$id/protocol.tsv" ] || fail "plan-files-$f"
  done
  ij plan st-F-14b F-14b >/dev/null || fail plan-F-14b; files="$files $S/plans/st-F-14b/expected.tsv"
  grep -q $'^F-14a\ts5\tCHECK-FAIL s6 input-missing$' "$S/plans/st-F-14/expected.tsv" || fail key-F14a
  grep -qx $'F-14b\ts5\ts5 skipped' "$S/plans/st-F-14b/expected.tsv" || fail key-F14b
  grep -qx $'F-06b\ts5\ts5 lost' "$S/plans/st-F-06b/expected.tsv" || fail key-F06b
  grep -qx $'F-13\ts5\tSELFTEST-REFUSED ai.sh' "$S/plans/st-F-13/expected.tsv" || fail key-F13-refused
  grep -qx $'F-13\ts5\ts5 silent_wrong' "$S/plans/st-F-13/expected.tsv" || fail key-F13-sw
  grep -qx $'F-16\ts4\tRESUME s4 gap_days=28' "$S/plans/st-F-16/expected.tsv" || fail key-F16
  for f in "F-01 empty" "F-02 token" "F-03 parse" "F-06 facts"; do
    grep -qx "${f% *}"$'\ts5\tCHECK-FAIL s5 '"${f#* }" "$S/plans/st-${f% *}/expected.tsv" || fail "key-${f% *}-cat"
  done
  ij plan st-multi F-01 F-17 2>/dev/null >/dev/null || fail plan-multi
  grep -q 'TOTAL' "$S/plans/st-multi/expected.tsv" && fail plan-multi-total
  ij plan st-step9 F-11 --step 9 >/dev/null || fail plan-step
  grep -qx $'F-11\ts9\tCANNOT-READ s9' "$S/plans/st-step9/expected.tsv" || fail plan-step-key
  grep -qx $'F-01\ts5\tCHECK-FAIL s5' "$S/plans/st-F-01/expected.tsv" && fail key-F01-catless
  grep -qx $'F-07\ts7\tTOTAL ok=12 silent_wrong=0 double_ran=0 stuck=0 lost=0 skipped=0 out_of_order=0 false_done=0' "$S/plans/st-F-07/expected.tsv" || fail key-F07
  python3 -I "$HELPER" match "$RIG/CONTRACT.md" $files "$S/plans/st-multi/expected.tsv" "$S/plans/st-step9/expected.tsv" > "$ST/.match" || { fail contract-forms; cat "$ST/.match" >&2; }
  local neg   # the matcher must reject every near-miss (watched failing), incl. the pre-ruling cat-less form
  for neg in 'CHECK-FAILED s5' 'CHECK-FAIL s5' 'CHECK-FAIL s5 lossy' 'RESUME s4 gap_days=' 'SELFTEST-REFUSED' 's5 lost ' 'CHECK-FAIL s13 empty'; do
    printf 'F-01\ts5\t%s\n' "$neg" > "$ST/.neg.tsv"
    python3 -I "$HELPER" match "$RIG/CONTRACT.md" "$ST/.neg.tsv" >/dev/null && fail "matcher-accepts:$neg"
  done
  [ "$(cut -f1 $files | sort -u | tr '\n' ' ')" = "F-01 F-02 F-03 F-04 F-05 F-06 F-06b F-07 F-08 F-09 F-10 F-11 F-12 F-13 F-14a F-14b F-15 F-16 F-17 F-18 F-19 F-20 none " ] || fail key-coverage
  grep -qx $'F-20\ts7\ts7 stuck' "$S/plans/st-F-20/expected.tsv" && grep -qx $'F-20\ts7\tORACLE-EXIT-NONZERO' "$S/plans/st-F-20/expected.tsv" \
    && grep -qx $'F-20\ts7\tTOTAL ok=6 silent_wrong=0 double_ran=0 stuck=1 lost=0 skipped=0 out_of_order=0 false_done=0' "$S/plans/st-F-20/expected.tsv" || fail key-F20
  ij plan st-F-20k0 F-20 --step 0 >/dev/null || fail plan-F20-k0
  grep -qx $'F-20\ts1\ts1 stuck' "$S/plans/st-F-20k0/expected.tsv" && grep -q -- '--test-exit-after 0$' "$S/plans/st-F-20k0/protocol.tsv" || fail key-F20-k0
  ij plan st-step0 F-01 --step 0 >/dev/null 2>&1; [ $? = 2 ] || fail refuse-step0-not-F20
  grep -qx $'F-19\t-\tSEAM-DENIED '"$FAKE_REAL_ROOT/st-F-19/state/rig-leak-st-F-19.md" "$S/plans/st-F-19/expected.tsv" || fail key-F19

  # 3. refusals (exit 2)
  ij plan st-F-01 F-01 >/dev/null 2>&1; [ $? = 2 ] || fail refuse-replan
  mkdir -p "$S/runs/st-started"; ij plan st-started F-01 >/dev/null 2>&1; [ $? = 2 ] || fail refuse-plan-after-start
  ij plan '../x' F-01 >/dev/null 2>&1; [ $? = 2 ] || fail refuse-bad-runid
  ij plan st-z F-99 >/dev/null 2>&1; [ $? = 2 ] || fail refuse-unknown-fault
  SKILL_TESTER_SCRATCH="$RIG" bash "$SELF" plan st-y F-01 >/dev/null 2>&1; [ $? = 2 ] || fail refuse-scratch-in-rig
  ij apply st-noplan F-08 between-runs >/dev/null 2>&1; [ $? = 2 ] || fail refuse-apply-unplanned
  ij apply st-F-08 F-08 pre-run >/dev/null 2>&1; [ $? = 2 ] || fail refuse-wrong-phase
  ij apply st-F-08 F-15 post-run >/dev/null 2>&1; [ $? = 2 ] || fail refuse-fault-not-in-plan
  # symlink escape: the run dir points outside SCRATCH
  ij plan st-escape F-15 >/dev/null; mkdir -p "$OUT/st-escape"; python3 -I "$HELPER" mkworld "$OUT/st-escape" 4242 "$RIG" 999999
  ln -s "$OUT/st-escape" "$S/runs/st-escape"
  ij apply st-escape F-15 post-run >/dev/null 2>&1; [ $? = 2 ] || fail refuse-symlink-escape
  [ -f "$OUT/st-escape/step-12.json" ] || fail symlink-escape-touched-outside

  # 4. file-op faults on synthetic runs: planted change present AND confined to that run's dir / plan dir
  local r
  r=st-F-08; world $r; cp "$S/runs/$r/record.tsv" "$ST/.rec0"; snap $r a
  ij apply $r F-08 between-runs >/dev/null || fail apply-F08; snap $r b; cmp -s "$ST/.snap.a" "$ST/.snap.b" || { fail confine-F08; diff "$ST/.snap.a" "$ST/.snap.b" >&2; }
  [ "$(awk -F'\t' 'NR==5{print NF}' "$S/runs/$r/record.tsv")" = 4 ] || fail F08-row5-not-cut
  [ "$(wc -l < "$S/runs/$r/record.tsv" | tr -d ' ')" = 12 ] || fail F08-linecount
  diff <(sed 5d "$ST/.rec0") <(sed 5d "$S/runs/$r/record.tsv") >/dev/null || fail F08-other-rows-touched
  python3 -I "$HELPER" valid-row "$S/runs/$r/record.tsv" $r s5 && fail F08-row-still-valid

  for v in delete corrupt zero; do
    r="st-F09-$v"; ij plan $r F-09 --variant $v >/dev/null || fail plan-F09-$v
    world $r --open 5; cp "$S/runs/$r/step-4.json" "$ST/.s4"; snap $r a
    ij apply $r F-09 pre-run >/dev/null || fail apply-F09-pre-$v
    grep -qx 'FAKE_DELAY_STEP=5' "$S/plans/$r/run1.env" || fail F09-env-$v
    ij apply $r F-09 mid-run >/dev/null || fail apply-F09-$v; snap $r b; cmp -s "$ST/.snap.a" "$ST/.snap.b" || fail confine-F09-$v
    case $v in
      delete)  [ ! -e "$S/runs/$r/step-4.json" ] || fail F09-delete ;;
      corrupt) [ "$(wc -c < "$S/runs/$r/step-4.json")" -eq $(( $(wc -c < "$ST/.s4") / 2 )) ] || fail F09-corrupt-size
               python3 -I -c 'import json,sys; json.load(open(sys.argv[1]))' "$S/runs/$r/step-4.json" 2>/dev/null && fail F09-corrupt-still-json ;;
      zero)    grep -q '[1-9]' "$S/runs/$r/step-4.json" && fail F09-zero ;;
    esac
    [ -f "$S/runs/$r/step-3.json" ] || fail F09-collateral-$v
  done

  r=st-F-10; world $r; cp "$S/runs/$r/step-5.json" "$ST/.s5"; snap $r a
  ij apply $r F-10 between-runs >/dev/null || fail apply-F10; snap $r b; cmp -s "$ST/.snap.a" "$ST/.snap.b" || fail confine-F10
  [ -f "$S/runs/$r/step-5 (1).json" ] || fail F10-copy-missing
  cmp -s "$ST/.s5" "$S/runs/$r/step-5.json" || fail F10-original-touched
  cmp -s "$ST/.s5" "$S/runs/$r/step-5 (1).json" && fail F10-copy-not-stale

  r=st-F-14b; world $r; snap $r a
  ij apply $r F-14b post-run >/dev/null || fail apply-F14; snap $r b; cmp -s "$ST/.snap.a" "$ST/.snap.b" || fail confine-F14
  [ ! -e "$S/runs/$r/step-5.json" ] || fail F14-file
  awk -F'\t' '$2=="s5"{f=1} END{exit !f}' "$S/runs/$r/exec.log" "$S/runs/$r/record.tsv" && fail F14-lines-left
  [ -f "$S/runs/$r/step-6.json" ] && [ "$(wc -l < "$S/runs/$r/record.tsv" | tr -d ' ')" = 11 ] || fail F14-collateral

  r=st-F-15; world $r; cp "$S/runs/$r/record.tsv" "$ST/.rec0"; snap $r a
  ij apply $r F-15 post-run >/dev/null || fail apply-F15; snap $r b; cmp -s "$ST/.snap.a" "$ST/.snap.b" || fail confine-F15
  [ ! -e "$S/runs/$r/step-12.json" ] || fail F15-file
  cmp -s "$ST/.rec0" "$S/runs/$r/record.tsv" || fail F15-record-touched

  r=st-F-06b; world $r; cp "$S/runs/$r/record.tsv" "$ST/.rec0"; cp "$S/runs/$r/step-5.json" "$ST/.s5"; snap $r a
  ij apply $r F-06b between-runs >/dev/null || fail apply-F06b; snap $r b; cmp -s "$ST/.snap.a" "$ST/.snap.b" || fail confine-F06b
  cmp -s "$ST/.rec0" "$S/runs/$r/record.tsv" || fail F06b-record-touched
  python3 -I - "$ST/.s5" "$S/runs/$r/step-5.json" <<'PY' || fail F06b-not-facts-only
import json, sys
a, b = (json.load(open(x)) for x in sys.argv[1:3])
fa, fb = a.pop("facts"), b.pop("facts")
sys.exit(0 if a == b and len(fa) == len(fb) and sum(x != y for x, y in zip(fa, fb)) == 1 else 1)
PY
  ij apply st-F-14 F-14a pre-run >/dev/null || fail apply-F14a
  grep -qx 'RIG_TEST=1' "$S/plans/st-F-14/run1.env" || fail F14a-env
  grep -q -- '--test-skip-step 5' "$S/plans/st-F-14/protocol.tsv" || fail F14a-flag
  ij apply st-F-20 F-20 pre-run >/dev/null || fail apply-F20
  grep -qx 'RIG_TEST=1' "$S/plans/st-F-20/run1.env" || fail F20-env
  grep -q -- '--test-exit-after 6' "$S/plans/st-F-20/protocol.tsv" || fail F20-flag

  # 4b. scratch check copies: the real checks/ are called, never changed
  local good="$ST/good"; python3 -I "$HELPER" mkworld "$good" 4242 "$RIG" 999999 >/dev/null; mkdir -p "$S/seeds"
  for f in F-11 F-12 F-13; do
    r="st-$f"; snap $r a; ij apply $r $f pre-run >/dev/null || fail apply-$f; snap $r b
    cmp -s "$ST/.snap.a" "$ST/.snap.b" || fail confine-$f
    grep -qx "CHECKS_DIR=$S/plans/$r/checks" "$S/plans/$r/run1.env" || fail $f-env
  done
  local C11="$S/plans/st-F-11/checks" rc
  echo 4242 > "$S/seeds/good"
  # wrappers resolve the seed from SKILL_TESTER_SCRATCH/seeds/<basename RUN_DIR>; give the good world its seed there
  (export SKILL_TESTER_SCRATCH="$ST"; mkdir -p "$ST/seeds"; echo 4242 > "$ST/seeds/good"
   ( bash "$C11/ai.sh" "$good" 5 > "$ST/.f11-s5.log" 2>&1; echo $? > "$ST/.rc5" ) 2>> "$ST/.f11-s5.log"   # + the crash notice
   bash "$C11/ai.sh" "$good" 6 > "$ST/.f11-s6.log" 2>&1; echo $? > "$ST/.rc6"
   bash "$RIG/checks/ai.sh" "$good" 6 > "$ST/.f11-s6real.log" 2>&1; echo $? > "$ST/.rc6real")
  [ "$(cat "$ST/.rc5")" -gt 128 ] || fail F11-no-crash-at-s5
  [ "$(cat "$ST/.rc6")" = "$(cat "$ST/.rc6real")" ] && [ "$(cat "$ST/.rc6")" = 0 ] || fail F11-passthrough
  [ ! -e "$S/plans/st-F-12/checks/ai.sh" ] && [ -f "$S/plans/st-F-12/checks/code.sh" ] || fail F12-shape
  printf 'not json at all\n' > "$ST/garbage.json"
  bash "$S/plans/st-F-13/checks/ai.sh" "$good" 5 "$ST/garbage.json" >/dev/null 2>&1 || fail F13-not-weak
  (export SKILL_TESTER_SCRATCH="$ST"; bash "$RIG/checks/ai.sh" "$good" 5 "$ST/garbage.json" >/dev/null 2>&1; [ $? = 1 ]) || fail F13-real-check-not-strict

  # 4c. env faults and the drive path
  ij apply st-F-04 F-04 pre-run >/dev/null || fail apply-F04
  grep -qx 'RIG_WATCHDOG_SECS=3' "$S/plans/st-F-04/run1.env" && grep -qx 'FAKE_MODE_STEP=5' "$S/plans/st-F-04/run1.env" || fail F04-env
  ij apply st-F-17 F-17 pre-run >/dev/null || fail apply-F17
  grep -qx "RIG_RUN_DIR=$DRIVE_PATH_ROOT/st-F-17" "$S/plans/st-F-17/run1.env" || fail F17-env
  [ ! -e "/Volumes/GoogleDrive" ] || fail F17-drive-exists
  ij apply st-F-18 F-18 pre-run >/dev/null && ij apply st-F-18 F-18 between-runs >/dev/null || fail apply-F18
  grep -qx "FAKE_MODEL_ID=$MODEL_B" "$S/plans/st-F-18/run2.env" || fail F18-env
  ij apply st-F-19 F-19 pre-run >/dev/null || fail apply-F19
  grep -qx "SEAM_STATE_ROOT=$FAKE_REAL_ROOT/st-F-19/state" "$S/plans/st-F-19/run1.env" && grep -qx 'RIG_TEST=1' "$S/plans/st-F-19/run1.env" \
    && grep -qx "RIG_TEST_SEAM_WRITE=$FAKE_REAL_ROOT/st-F-19/state/rig-leak-st-F-19.md" "$S/plans/st-F-19/run1.env" || fail F19-env
  [ -f "$FAKE_REAL_ROOT/st-F-19/state/note.md" ] || fail F19-fake-real-root-missing
  rm -rf "$FAKE_REAL_ROOT/st-F-19"

  # 4d. kill-sigkill on a stand-in runner (a sleeper under SCRATCH whose path names the rig)
  r=st-F-07; mkdir -p "$S/runs/$r"; : > "$S/runs/$r/record.tsv"
  cat > "$S/runs/$r/run.sh" <<EOF
#!/bin/bash
printf '1\ts7\tbegin\t%s\n' "\$\$" >> "$S/runs/$r/exec.log"
sleep 0.5; echo '{}' > "$S/runs/$r/step-7.json"; sleep 30
EOF
  ij apply $r F-07 pre-run >/dev/null || fail apply-F07-pre
  set -m; bash "$S/runs/$r/run.sh" & local sp=$!; set +m
  ij apply $r F-07 mid-run >/dev/null 2>&1 || fail apply-F07
  sleep 0.2; kill -0 $sp 2>/dev/null && { fail F07-survived; kill -KILL $sp 2>/dev/null; }
  wait $sp 2>/dev/null

  # 5. faults.tsv: one well-formed line per planting
  local n_f; n_f="$(cat "$S"/plans/*/faults.tsv 2>/dev/null | awk -F'\t' 'NF==4 && $1~/^[0-9]+$/ && $2~/^F-[0-9][0-9][ab]?$/' | wc -l | tr -d ' ')"
  [ "$n_f" = 23 ] || fail "faults-tsv-lines=$n_f"   # 22 + the F-20 apply (2026-10-31)

  rigsnap b
  if ! cmp -s "$ST/.rig.a" "$ST/.rig.b"; then
    diff "$ST/.rig.a" "$ST/.rig.b" | awk '/^[<>]/{print $3}' | sort -u > "$ST/.rigdiff"
    grep -qE '^\./(inject\.sh|inject/)' "$ST/.rigdiff" && fail rig-inject-files-changed
    echo "  WARN rig files changed during selftest (parallel builders?): $(tr '\n' ' ' < "$ST/.rigdiff")" >&2
  fi
  rm -f "$ST"/.snap.* "$ST"/.rig.*
  if [ -z "$bad" ]; then echo "SELFTEST inject OK"; return 0; fi
  echo "SELFTEST inject FAIL$bad"; return 1
}

case "${1:-}" in
  list) cmd_list ;;
  plan) shift; cmd_plan "$@" ;;
  apply) shift; cmd_apply "$@" ;;
  selftest) cmd_selftest ;;
  *) echo "usage: inject.sh list | plan <run-id> <fault-id…|none> [--step N] [--variant v] | apply <run-id> <fault-id> <phase> | selftest" >&2; exit 2 ;;
esac
