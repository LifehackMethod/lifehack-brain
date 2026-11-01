#!/bin/bash
# from orchestrator-v2/rig/run.sh @ 2026-10-28
#   (kept: card parse `id | kind | what | check`, one fresh `claude -p` per ai step with --output-format json,
#    --allowedTools Read and stdin </dev/null, the watchdog, the dead-owner lock steal, `--run-id` resume that logs
#    passed steps skipped-done, human step = record `waiting` + exit 70 then `--answer` on re-run, exit codes
#    0/70/75/1/124, no `set -e` (B21); rewritten for TR1.4: RUN_DIR under scratch, the rowsummed record appended
#    ONLY by the runner and ONLY after the check passed, malformed/foreign rows refused on resume, candidate files
#    checked BEFORE rename, random seed outside RUN_DIR and never in the actor's env, budget.sh for every model
#    call, seam snapshot/verify, the fake model and the fake clock.)
#
# run.sh — card TR1.4 of the skill-tester-rig: the runner and the record. bash 3.2 + BSD tools.
#
#   run.sh --fake <mode> [--run-id R] [--card canary|PATH] [--answer sN=yes|no]... [--seed S] [--rung X]
#          [--model-tier small|medium|large] [--test-skip-step N] [--test-exit-after K]
#   run.sh --real ...           the ONLY way to launch a real `claude`. Without --fake or --real: refused (exit 2).
#   run.sh --print-real-cmd     print the real actor command line (one argv element per line) and exit; launches nothing
#   run.sh --selftest           fake scenarios only; last line 'SELFTEST run OK'
#
#   <mode> = good|empty|almost|garbage|hang|exit127|lossy (fake-claude.sh; FAKE_MODE_STEP=N = that step only).
#
# CONTRACT.md is the interface (layout §1, record §2, event lines §3, fake §5); inject.sh's header table R0–R12
# lists what this runner supports for each planted fault. Summary of behaviour:
#   * every step: PRE-FLIGHT (N>=2: step-(N-1).json exists and the record vouches for its sha, else
#     `CHECK-FAIL sN input-missing`, exit 1) -> exec.log begin -> produce a CANDIDATE outside RUN_DIR
#     ($SCRATCH/stage/<run-id>/sN) -> check it (checks/<kind>.sh RUN_DIR N CANDIDATE) -> rename it to
#     step-N.json -> append the record row -> exec.log end. Nothing is committed or recorded on a failed check.
#   * resume: rows are scanned first (RECORD-FOREIGN / RECORD-REFUSED, never trusted); a step whose last valid row is
#     done/skipped-done AND whose file still has that sha AND still passes its check is logged `skipped-done`;
#     anything else that was begun before is `RERUN sN`. The first step that runs logs `RESUME sN gap_days=<d>`.
#   * the actor (real or fake) runs with cwd = RUN_DIR via `env -u CANARY_SEED -u SKILL_TESTER_SEED`; only code
#     steps, human.py and the checks get CANARY_SEED.
#   * clock: STRESS_TODAY (YYYY-MM-DD) only. With --fake and no STRESS_TODAY the clock is drive.py day(1).
#   * test-only knobs (honoured only with --fake): RIG_HOLD_BEFORE_RECORD=N:SECS (F-07; writes hold-sN.held, SECS = deadline), --test-skip-step N
#     (F-14a, also needs RIG_TEST=1; it can only make a run fail), --test-exit-after K (F-20, also needs RIG_TEST=1:
#     exit 0 right after committing step K, K=0 = before any step — a runner that stops short SILENTLY; only the
#     oracle can catch it). RIG_WATCHDOG_SECS, CHECKS_DIR, RIG_RUN_DIR as R2/R8/R11.
#   * EVERY check the run will use (default checks/ or a planted CHECKS_DIR) is judged first (checks/selftest.sh
#     --judge; default verdicts cached by content key in $SCRATCH/judge-cache); REFUSED -> `SELFTEST-REFUSED
#     <kind>.sh`, exit 1. RIG_TEST=1 runs on past a refused PLANTED check only (R8b), never past a refused
#     default check. Any RIG_TEST=1 invocation logs `RIG-TEST ON` first and
#     writes RIG_TEST=1 to meta.env: a test-path run, never a clean control.
#
# Exit: 0 done (or halted by a human "no") · 70 waiting for a human · 75 budget refused / lock held ·
#       124 watchdog · 1 step failed / CANNOT-READ / path refused / seam leak · 2 refused invocation.

# ── own process group (R0: exec.log's pid leads its group, so a kill injector can SIGKILL the whole tree) ──────
# (TR1.7: the guarded CHILD stays in its PARENT's group, so one group kill takes the whole run, parent included.)
if [ "${RIG_RUNNER_PGRP:-}" != "$$" ] && [ "${RIG_GUARD_PARENT:-}" != "$PPID" ]; then
  RIG_RUNNER_PGRP=$$ exec python3 -I -B -c '
import os, sys
try:
    os.setpgid(0, 0)
except OSError:
    pass
os.execv("/bin/bash", ["/bin/bash"] + sys.argv[1:])' "$0" "$@"
fi
unset RIG_RUNNER_PGRP
ORIG_ARGS=( "$@" )                            # TR1.7: the guard re-executes this runner with the same argv

SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
RIG="${SKILL_TESTER_RIG:-$(cd "$(dirname "$0")" && pwd)}"
CANON="$HOME/lifehack-scratch/skill-tester-rig"
SCRATCH="${SKILL_TESTER_SCRATCH:-$CANON}"
H="$RIG/run_helper.py"
MODES=" good empty almost garbage hang exit127 lossy "
CATS=" empty parse keys step token value facts answer "
unset CANARY_SEED SKILL_TESTER_SEED          # the seed lives in $SEED only; it is passed inline, never exported

say()  { echo "run.sh: $*" >&2; }
refuse() { say "REFUSED: $*"; exit 2; }
hp()   { python3 -I "$H" "$@"; }

# ── args ──────────────────────────────────────────────────────────────────────────────────────────────────────
FAKE=""; REAL=0; RUN_ID=""; CARD="canary"; ANSWERS=""; SEED_ARG=""; RUNG="${RIG_RUNG:-adhoc}"; TIER="medium"
SKIP_STEP=""; PRINT_REAL=0; EXIT_AFTER=""
while [ $# -gt 0 ]; do
  case "$1" in
    --selftest) shift; SELFTEST=1 ;;
    --fake) FAKE="${2:-}"; shift 2 || refuse "--fake needs a mode" ;;
    --real) REAL=1; shift ;;
    --run-id) RUN_ID="${2:-}"; shift 2 || refuse "--run-id needs a value" ;;
    --card) CARD="${2:-}"; shift 2 || refuse "--card needs a value" ;;
    --answer) case "${2:-}" in s[0-9]*=*) ANSWERS="$ANSWERS
${2}" ;; *) refuse "--answer must be sN=<answer>, got '${2:-}'" ;; esac; shift 2 ;;
    --seed) SEED_ARG="${2:-}"; shift 2 || refuse "--seed needs a value" ;;
    --rung) RUNG="${2:-}"; shift 2 || refuse "--rung needs a value" ;;
    --model-tier) TIER="${2:-}"; shift 2 || refuse "--model-tier needs a value" ;;
    --test-skip-step) SKIP_STEP="${2:-}"; shift 2 || refuse "--test-skip-step needs N" ;;
    --test-exit-after) EXIT_AFTER="${2:-}"; shift 2 || refuse "--test-exit-after needs K" ;;
    --print-real-cmd) PRINT_REAL=1; shift ;;
    *) refuse "unknown argument '$1'" ;;
  esac
done

case "$TIER" in small|medium|large) ;; *) refuse "--model-tier must be small|medium|large" ;; esac
MODEL_ID="$(python3 -I -B -c 'import sys; sys.path.insert(0, sys.argv[1]); from model_ids import model_id; print(model_id(sys.argv[2]))' \
  "${LIFEHACK_V2:-$HOME/lifehack-v2}/shared/tools" "$TIER")"
[ -n "$MODEL_ID" ] || refuse "cannot read the model id from shared/tools/model_ids.py"
NO_MODEL="-"   # the record's model field for a step no model ran (code/human); a placeholder, never an id

# actor_cmd <prompt> : the ONE actor command line (real and fake share it; only CLAUDE_BIN differs).
# Never --dangerously-skip-permissions (ruling 8): read-only tools + deny list + no stdin + watchdog.
actor_argv() {
  ACTOR=( "$CLAUDE_BIN" -p "$1" --output-format json --model "$MODEL_ID" --allowedTools Read
          --permission-mode bypassPermissions --settings "$LAB_SETTINGS" )
}
# LAB_SETTINGS: rendered at launch from lab-settings.template.json into $SCRATCH/settings/<run-id>.lab-settings.json
# (the absolute-path deny rules cannot be committed, so the committed file is a template; see the scratch guard).
LAB_SETTINGS="<scratch>/settings/<run-id>.lab-settings.json"
if [ "$PRINT_REAL" = 1 ]; then
  CLAUDE_BIN="claude"; actor_argv "<rendered prompt>"
  printf '%s\n' "env" "-u" "CANARY_SEED" "-u" "SKILL_TESTER_SEED" "${ACTOR[@]}"
  echo "# cwd=RUN_DIR stdin=/dev/null via: budget.sh call <run-id> -- <the above>"
  exit 0
fi

if [ -n "${SELFTEST:-}" ]; then
  [ -f "$RIG/run_selftest.sh" ] || { echo "SELFTEST run FAILED: run_selftest.sh missing"; exit 1; }
  exec bash "$RIG/run_selftest.sh" "$SELF"
fi

[ -n "$FAKE" ] && [ "$REAL" = 1 ] && refuse "--fake and --real together"
[ -z "$FAKE" ] && [ "$REAL" = 0 ] && refuse "run.sh launches a model only with --fake <mode>, or the explicit --real (never implied)"
if [ -n "$FAKE" ]; then
  case "$MODES" in *" $FAKE "*) ;; *) refuse "unknown fake mode '$FAKE' (good|empty|almost|garbage|hang|exit127|lossy)" ;; esac
  CLAUDE_BIN="$RIG/fake-claude.sh"
else
  CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude)}"
  [ -n "$CLAUDE_BIN" ] || refuse "--real: no claude binary on PATH"
fi
if [ -n "$SKIP_STEP" ]; then
  [ "${RIG_TEST:-}" = 1 ] || refuse "--test-skip-step is a fault injector (F-14a, a deliberate runner bug); it needs RIG_TEST=1"
  [ -n "$FAKE" ] || refuse "--test-skip-step is honoured only with --fake"
  case "$SKIP_STEP" in [1-9]|1[0-2]) ;; *) refuse "--test-skip-step N needs N in 1..12" ;; esac
fi
if [ -n "$EXIT_AFTER" ]; then
  [ "${RIG_TEST:-}" = 1 ] || refuse "--test-exit-after is a fault injector (F-20, a runner that stops short silently); it needs RIG_TEST=1"
  [ -n "$FAKE" ] || refuse "--test-exit-after is honoured only with --fake"
  case "$EXIT_AFTER" in [0-9]|1[01]) ;; *) refuse "--test-exit-after K needs K in 0..11" ;; esac
fi
[ -z "$SEED_ARG" ] || case "$SEED_ARG" in *[!0-9]*) refuse "--seed must be a non-negative integer" ;; esac
[ -n "$RUN_ID" ] || RUN_ID="r-$(python3 -I -B -c 'import secrets; print(secrets.token_hex(4))')"
case "$RUN_ID" in .*|*[!A-Za-z0-9._-]*) refuse "bad run-id '$RUN_ID' (allowed: A-Za-z0-9._-, no leading dot)" ;; esac
case "$CARD" in canary) CARDF="$RIG/canary/card.txt" ;; *) CARDF="$CARD" ;; esac
[ -f "$CARDF" ] || refuse "card not found: $CARDF"

# ── scratch guard (ruling 6) ──────────────────────────────────────────────────────────────────────────────────
case "$SCRATCH" in /*) ;; *) refuse "SKILL_TESTER_SCRATCH must be absolute: $SCRATCH" ;; esac
mkdir -p "$CANON" || refuse "cannot create $CANON"
CANON_R="$(hp realpath "$CANON")"; SCRATCH_R="$(hp realpath "$SCRATCH")"
case "$SCRATCH_R/" in "$CANON_R"/*) ;; *) refuse "SCRATCH $SCRATCH resolves outside $CANON (ruling 6)" ;; esac
case "$SCRATCH_R" in *"/Library/CloudStorage"*|*"Google"*"Drive"*) refuse "SCRATCH is on a cloud drive (ruling 6)" ;; esac
# 2026-10-31: the rig may itself live under scratch (staging copy during the v2 freeze). Runs, seeds and plans must
# never land inside the rig folder (the seeds would sit beside the code the actor can be denied, or not).
case "$SCRATCH_R/" in "$(hp realpath "$RIG")"/*) refuse "SCRATCH $SCRATCH_R is inside the rig folder $RIG" ;; esac
if [ "$REAL" = 1 ]; then
  # the rendered lab settings deny Read on the CANONICAL scratch seeds/plans and the canonical rig folder only.
  [ "$SCRATCH_R" = "$CANON_R" ] || refuse "--real needs the canonical scratch $CANON (the deny list is written for it)"
  [ "$(hp realpath "$RIG")" = "$(hp realpath "$HOME/lifehack-v2/system/tools/skill-tester-rig")" ] \
    || refuse "--real needs the canonical rig folder (the deny list is written for it)"
fi
# the actor's settings: lab-settings.template.json rendered for THIS scratch and rig ({{SCRATCH}}, {{RIG}} -> their
# realpaths, giving the absolute `Read(//...)` deny forms beside the literal `~/` ones). With --real the two checks
# above pin both to the canonical folders, so the rendered deny list is exactly the canonical one.
mkdir -p "$SCRATCH_R/settings" || refuse "cannot create $SCRATCH_R/settings"
LAB_SETTINGS="$SCRATCH_R/settings/$RUN_ID.lab-settings.json"
hp render-settings "$RIG/lab-settings.template.json" "$LAB_SETTINGS" "$SCRATCH_R" "$(hp realpath "$RIG")" \
  || refuse "cannot render the actor settings from $RIG/lab-settings.template.json"

# ── TR1.7 WRITE GUARD (CONTRACT §3a). This runner splits in two:
#   PARENT (unguarded, tiny): builds the profile, starts the CHILD under `sandbox-exec -f <profile>`, waits, then
#     does what cannot run inside a sandbox (`log show` refuses: "Cannot run while sandboxed", seen 2026-10-31):
#     the barrier (a refused write through the SAME profile, after the child and its tree have exited), the denial
#     read (SEAM-DENIED / SEAM-CANNOT-READ denials), and seam verify + classification (SEAM-AMBIENT / SEAM-LEAK).
#     The parent writes nothing but events.log/seam.log/guard-denials.txt lines in the run dir (scratch).
#   CHILD (guarded): the whole run, exactly as before: runner, budget.sh, actor, code steps, checks, seam snapshot.
#     It probes the guard before the snapshot (rule 2) and hands RUN_DIR/EVT/SEAM_ID to the parent via a handoff
#     file in $SCRATCH/guard/. Every process it starts inherits the profile.
# guard.sh's header lists the profile and the reason for every allowance.
STANDIN_R="$(hp realpath "${SEAM_STANDIN:-$CANON/notes-standin}")"
GUARD_OUT="$(hp realpath "$HOME/lifehack-scratch")"            # outside the allow list; never the real notes folder
TAB1="$(printf '\t')"

# seam_classify <run_dir> <seam_id> <amb_ok 0|1> <denials-file> : seam.sh verify, then one events line per moved
# path: SEAM-AMBIENT (only if amb_ok and the path has no denial) or SEAM-LEAK. Returns 1 if anything COUNTS.
seam_classify() {
  local rd="$1" sid="$2" amb="$3" dn="$4" out vrc cls op p bad=0
  out="$(bash "$RIG/seam.sh" verify "$sid" 2>&1)"; vrc=$?
  printf '%s\n' "$out" >> "$rd/seam.log"
  if [ "$vrc" = 1 ]; then
    printf '%s\n' "$out" | grep -E "^  (CHANGED|ADDED|REMOVED)$TAB1" | sed 's/^  //' > "$rd/.seam-moved"
    python3 -I -B -c '
import os, sys
amb_ok = sys.argv[1] == "1"
denied = set(os.path.realpath(l.rstrip("\n")) for l in open(sys.argv[2]) if l.strip())
for l in open(sys.argv[3]):
    op, _, p = l.rstrip("\n").partition("\t")
    if not p:
        continue
    cls = "AMBIENT" if amb_ok and os.path.realpath(p) not in denied else "LEAK"
    print("%s\t%s\t%s" % (cls, op, p))' "$amb" "$dn" "$rd/.seam-moved" > "$rd/.seam-classed"
    while IFS="$TAB1" read -r cls op p; do
      [ -n "$cls" ] || continue
      ev "SEAM-$cls $op $p"; [ "$cls" = LEAK ] && bad=1
    done < "$rd/.seam-classed"
    [ -s "$rd/.seam-classed" ] || { ev "SEAM-CANNOT-READ rc=1"; bad=1; }
    rm -f "$rd/.seam-moved" "$rd/.seam-classed"
  elif [ "$vrc" != 0 ]; then ev "SEAM-CANNOT-READ rc=$vrc"; bad=1
  fi
  return $bad
}

if [ -n "${RIG_GUARD_TAG:-}" ] && [ "${RIG_GUARD_PARENT:-}" = "$PPID" ] && [ -n "${RIG_GUARD_HANDOFF:-}" ]; then
  GUARD=on                                                     # claimed; the probe below must prove it (rule 2)
else
  unset RIG_GUARD_TAG RIG_GUARD_PARENT RIG_GUARD_T0 RIG_GUARD_PROFILE RIG_GUARD_HANDOFF
  if [ "${SEAM_GUARD_DISABLE:-}" = 1 ]; then
    [ -n "$FAKE" ] || refuse "SEAM_GUARD_DISABLE=1 is honoured only with --fake (it can only make a run stricter)"
    GUARD="off:disabled-by-env"
  elif ! bash "$RIG/guard.sh" available; then
    GUARD="off:sandbox-unavailable"
  else
    mkdir -p "$STANDIN_R" "$CANON_R/notes-standin" "$CANON_R/guard" "$CANON_R/tmp/$RUN_ID.$$" || refuse "cannot prepare the guard dirs"
    # the seam roots (same defaults as seam.sh): denied explicitly AFTER the scratch allow
    V2D="${LIFEHACK_V2:-$HOME/lifehack-v2}"
    # the notes state root comes from seam.sh itself (ONE resolver: SEAM_STATE_ROOT, else <notes-root>/state via
    # shared/brain_root.py), so the guard denies exactly the folder the seam watches. Unresolvable -> refused.
    SEAM_STATE_R="$(bash "$RIG/seam.sh" state-root 2>/dev/null)" \
      || refuse "cannot resolve the notes state root for the write guard: $(printf '%s' "$SEAM_STATE_R" | tr '\n' ' ')"
    DENY_ROOTS=( "$(hp realpath "$SEAM_STATE_R")"
                 "$(hp realpath "${SEAM_HOOKS_JSON:-$V2D/hooks/hooks.json}")" )
    oifs="$IFS"; IFS=':'
    for r in ${SEAM_SKILL_ROOTS:-$HOME/.claude/skills:$V2D/.claude/skills:$V2D/skills}; do
      [ -n "$r" ] && DENY_ROOTS[${#DENY_ROOTS[@]}]="$(hp realpath "$r")"
    done
    IFS="$oifs"
    # CONTRACT §3b: the profile denies the WHOLE stand-in tree ($CANON/notes-standin, every bite's own subtree); a
    # stand-in outside that tree (a test's) is denied as an extra root
    STANDIN_TREE_R="$(hp realpath "$CANON_R/notes-standin")"
    case "$STANDIN_R/" in "$STANDIN_TREE_R"/*) ;; *) DENY_ROOTS[${#DENY_ROOTS[@]}]="$STANDIN_R" ;; esac
    RIG_GUARD_TAG="RIGDENY-$RUN_ID-$$-$(python3 -I -B -c 'import secrets; print(secrets.token_hex(4))')"
    GPROF="$CANON_R/guard/$RUN_ID.$$.sb"
    bash "$RIG/guard.sh" profile "$RIG_GUARD_TAG" "$CANON_R" "$(hp realpath "$RIG")" "$STANDIN_TREE_R" "${DENY_ROOTS[@]}" \
      > "$CANON_R/guard/$RUN_ID.$$.sb" || refuse "cannot write the guard profile"
    RIG_GUARD_PROFILE="$GPROF"
    RIG_GUARD_T0="$(date -v-2S '+%Y-%m-%d %H:%M:%S')"
    # bash 3.2 here-docs use /tmp (allowed narrowly); everything else that honours TMPDIR lands in scratch
    G_TMP="$CANON_R/tmp/$RUN_ID.$$"
    RIG_GUARD_HANDOFF="$CANON_R/guard/$RUN_ID.$$.handoff"; rm -f "$RIG_GUARD_HANDOFF"
    # the child stays in THIS process's group (this parent leads it, R0) and writes THIS pid into exec.log, so a
    # group kill (the F-07 injector, run_selftest k1) takes parent and child at once, exactly like the unsplit runner
    TMPDIR="$G_TMP" RIG_GUARD_TAG="$RIG_GUARD_TAG" RIG_GUARD_PROFILE="$GPROF" RIG_GUARD_T0="$RIG_GUARD_T0" \
      RIG_GUARD_PARENT=$$ RIG_GUARD_HANDOFF="$RIG_GUARD_HANDOFF" \
      /usr/bin/sandbox-exec -f "$GPROF" /bin/bash "$SELF" "${ORIG_ARGS[@]}"
    rc=$?
    # ── PARENT post-run (unguarded) ──
    HO_RUN_DIR=""; HO_SEAM_ID=""
    [ -f "$RIG_GUARD_HANDOFF" ] && { HO_RUN_DIR="$(sed -n 's/^RUN_DIR=//p' "$RIG_GUARD_HANDOFF" | tail -1)"
                                     HO_SEAM_ID="$(sed -n 's/^SEAM_ID=//p' "$RIG_GUARD_HANDOFF" | tail -1)"; }
    rm -f "$RIG_GUARD_HANDOFF"; rm -rf "$G_TMP"
    if [ -z "$HO_RUN_DIR" ] || [ ! -d "$HO_RUN_DIR" ]; then exit "$rc"; fi   # refused before a run dir existed
    EVT="$HO_RUN_DIR/events.log"
    ev() { printf '%s\n' "$*" >> "$EVT"; say "EVENT $*"; }
    bump() { { [ "$rc" = 0 ] || [ "$rc" = 70 ]; } && rc=1; return 0; }
    # §3a rule 3: the barrier, a refused write through the SAME profile after the child's tree has exited; then the
    # log is read until the barrier's denial shows (readable AND flushed past every earlier denial of this run)
    barrier="$GUARD_OUT/.seam-guard-barrier-$RIG_GUARD_TAG"
    /usr/bin/sandbox-exec -f "$GPROF" /bin/bash -c '( : > "$1" ) 2>/dev/null && { rm -f "$1"; exit 9; }; exit 0' _ "$barrier"
    [ $? = 9 ] && { ev "GUARD-PROBE-FAILED barrier-write-landed"; bump; }
    : > "$HO_RUN_DIR/guard-denials.txt"
    deny_ok=0
    if bash "$RIG/guard.sh" denials "$RIG_GUARD_TAG" "$RIG_GUARD_T0" "$barrier" > "$HO_RUN_DIR/.guard-denials.raw" 2>> "$HO_RUN_DIR/seam.log"; then
      deny_ok=1
      grep -vxF -e "$STANDIN_R/.seam-guard-probe-$RIG_GUARD_TAG" -e "$GUARD_OUT/.seam-guard-probe-$RIG_GUARD_TAG" \
        "$HO_RUN_DIR/.guard-denials.raw" > "$HO_RUN_DIR/guard-denials.txt"
      while IFS= read -r p; do [ -n "$p" ] && { ev "SEAM-DENIED $p"; bump; }; done < "$HO_RUN_DIR/guard-denials.txt"
    else
      ev "SEAM-CANNOT-READ denials"; bump
    fi
    rm -f "$HO_RUN_DIR/.guard-denials.raw"
    if [ -n "$HO_SEAM_ID" ]; then seam_classify "$HO_RUN_DIR" "$HO_SEAM_ID" "$deny_ok" "$HO_RUN_DIR/guard-denials.txt" || bump; fi
    exit "$rc"
  fi
fi
handoff() { [ "$GUARD" = on ] && printf '%s\n' "$1" >> "$RIG_GUARD_HANDOFF"; return 0; }

CANON_RUN="$SCRATCH_R/runs/$RUN_ID"
RUN_DIR="$CANON_RUN"
if [ -n "${RIG_RUN_DIR:-}" ]; then
  rr="$(hp realpath "$RIG_RUN_DIR")"
  case "$RIG_RUN_DIR" in /*) ;; *) rr="" ;; esac
  case "$rr/" in "$SCRATCH_R"/*/) RUN_DIR="$rr" ;;
    *) mkdir -p "$CANON_RUN"; handoff "RUN_DIR=$CANON_RUN"
       printf 'PATH-REFUSED %s\n' "$RIG_RUN_DIR" >> "$CANON_RUN/events.log"
       say "PATH-REFUSED $RIG_RUN_DIR (outside $SCRATCH_R; ruling 6)"; exit 1 ;;
  esac
fi
mkdir -p "$RUN_DIR" "$SCRATCH_R/seeds" "$SCRATCH_R/stage/$RUN_ID" || { say "cannot create $RUN_DIR"; exit 1; }
handoff "RUN_DIR=$RUN_DIR"
REC="$RUN_DIR/record.tsv"; EXEC="$RUN_DIR/exec.log"; EVT="$RUN_DIR/events.log"
STAGE_ROOT="$SCRATCH_R/stage/$RUN_ID"
CHECKS_DIR="${CHECKS_DIR:-$RIG/checks}"

ev() { printf '%s\n' "$*" >> "$EVT"; say "EVENT $*"; }

# ── lock (dead owner -> steal; SIGKILL skips traps) ─────────────────────────────────────────────────────────────
LOCK="$RUN_DIR/.lock"; SEAM_ID=""
if ! mkdir "$LOCK" 2>/dev/null; then
  owner="$(cat "$LOCK/pid" 2>/dev/null)"
  if [ -n "$owner" ] && kill -0 "$owner" 2>/dev/null; then say "lock held by pid $owner — standing down"; exit 75; fi
  say "stale lock (owner ${owner:-unknown} gone) — stealing"; rm -rf "$LOCK"
  mkdir "$LOCK" 2>/dev/null || { say "lock race"; exit 75; }
fi
echo $$ > "$LOCK/pid"
# CONTRACT §3: a RIG_TEST=1 invocation is a test-path run; marked first, so bite/ladder can refuse it as a control.
[ "${RIG_TEST:-}" = 1 ] && ev "RIG-TEST ON"

bump() { { [ "$rc" = 0 ] || [ "$rc" = 70 ]; } && rc=1; return 0; }   # (sets finish's local rc)
finish() {  # finish <rc> : seam verify (unguarded only), unlock, exit
  local rc="$1"
  if [ -n "$SEAM_ID" ]; then
    # guarded: SEAM_ID was handed to the PARENT right after the snapshot (so even a SIGKILLed child is verified);
    # the parent reads the denials, then verifies and classifies (§3a). Unguarded: verify here, every change LEAK.
    if [ "$GUARD" != on ]; then
      : > "$RUN_DIR/guard-denials.txt"
      seam_classify "$RUN_DIR" "$SEAM_ID" 0 "$RUN_DIR/guard-denials.txt" || bump
    fi
  fi
  rm -rf "$LOCK" 2>/dev/null
  exit "$rc"
}
trap 'finish 143' INT TERM

# ── clock ─────────────────────────────────────────────────────────────────────────────────────────────────────
if [ -z "${STRESS_TODAY:-}" ] && [ -n "$FAKE" ]; then STRESS_TODAY="$(hp day 1)"; fi
export STRESS_TODAY
now_epoch() {
  if [ -n "${STRESS_TODAY:-}" ]; then hp today | awk '{print $2}'
  else date +%s; fi                                   # --real without STRESS_TODAY only
}
NOW="$(now_epoch)"; [ -n "$NOW" ] || { say "STRESS_TODAY is not YYYY-MM-DD: $STRESS_TODAY"; finish 2; }

# ── seed (CONTRACT §0: random, outside RUN_DIR, never in the actor's env) ───────────────────────────────────────
SEEDF="$SCRATCH_R/seeds/$RUN_ID"
if [ -f "$SEEDF" ]; then
  SEED="$(tr -d '[:space:]' < "$SEEDF")"
  case "$SEED" in ''|*[!0-9]*) ev "CANNOT-READ seed"; say "seed file unreadable: $SEEDF"; finish 1 ;; esac
  [ -z "$SEED_ARG" ] || [ "$SEED_ARG" = "$SEED" ] || { say "--seed $SEED_ARG differs from the run's seed file"; finish 2; }
else
  if [ -s "$REC" ] || [ -s "$EXEC" ]; then ev "CANNOT-READ seed"; say "run $RUN_ID has history but no seed file"; finish 1; fi
  SEED="${SEED_ARG:-$(hp seed)}"
  ( umask 077; printf '%s\n' "$SEED" > "$SEEDF.tmp.$$" && mv "$SEEDF.tmp.$$" "$SEEDF" ) || { say "cannot write seed"; finish 1; }
fi

if [ ! -f "$RUN_DIR/meta.env" ]; then
  { echo "RUN_ID=$RUN_ID"; echo "CARD=$CARD"; echo "MODEL_ID=$MODEL_ID"; echo "FAKE_MODE=${FAKE:-real}"; echo "START=$STRESS_TODAY"; } > "$RUN_DIR/meta.env"
else
  echo "RESUMED=${STRESS_TODAY:-$NOW} FAKE_MODE=${FAKE:-real}" >> "$RUN_DIR/meta.env"
fi
[ "${RIG_TEST:-}" = 1 ] && echo "RIG_TEST=1" >> "$RUN_DIR/meta.env"
touch "$EXEC" "$EVT"
{ echo "SEAM_GUARD=$GUARD"; [ "$GUARD" = on ] && echo "SEAM_GUARD_PROFILE=$RIG_GUARD_PROFILE"; } >> "$RUN_DIR/meta.env"

# ── TR1.7 GUARD PROBE (§3a rule 2, ruling 12: the guard is seen refusing before it is trusted) ─────────────────
if [ "$GUARD" = on ]; then
  probe_bad=""
  pp="$RUN_DIR/.guard-probe-$$"
  if ( : > "$pp" ) 2>/dev/null && [ -f "$pp" ]; then rm -f "$pp"; else probe_bad="$probe_bad run-dir-write-refused"; fi
  for pp in "$STANDIN_R/.seam-guard-probe-$RIG_GUARD_TAG" "$GUARD_OUT/.seam-guard-probe-$RIG_GUARD_TAG"; do
    if ( : > "$pp" ) 2>/dev/null; then rm -f "$pp"; probe_bad="$probe_bad write-landed:$pp"; fi
  done
  hd=""; read -r hd <<EOF
here-doc-ok
EOF
  [ "$hd" = here-doc-ok ] || probe_bad="$probe_bad here-document"
  if [ -n "$probe_bad" ]; then
    for pp in $probe_bad; do ev "GUARD-PROBE-FAILED $pp"; done
    finish 1
  fi
fi

if [ "$REAL" = 1 ]; then
  TOKEN_FILE="$HOME/.config/lifehack/claude-oauth-token"
  if [ -r "$TOKEN_FILE" ] && [ -s "$TOKEN_FILE" ]; then
    CLAUDE_CODE_OAUTH_TOKEN="$(tr -d '[:space:]' < "$TOKEN_FILE")"; export CLAUDE_CODE_OAUTH_TOKEN
  else say "no token at $TOKEN_FILE — standing down"; finish 75; fi
fi

bash "$RIG/budget.sh" open "$RUN_ID" >> "$RUN_DIR/budget.log" 2>&1 || { say "budget.sh open failed"; finish 1; }

SEAM_ID="$RUN_ID.$$"
if ! bash "$RIG/seam.sh" snapshot "$SEAM_ID" >> "$RUN_DIR/seam.log" 2>&1; then
  SEAM_ID=""; ev "SEAM-CANNOT-READ snapshot"; finish 1
fi
handoff "SEAM_ID=$SEAM_ID"
# F-19 (TR1.7, test-only: --fake AND RIG_TEST=1): the RIG ITSELF writes outside its lane. The write's outcome is LOGGED
# and never changes the verdict: the leak must be caught by the kernel's denial log, never by the runner's EPERM.
if [ -n "${RIG_TEST_SEAM_WRITE:-}" ] && [ -n "$FAKE" ] && [ "${RIG_TEST:-}" = 1 ]; then
  say "RIG_TEST_SEAM_WRITE: planted rig write to $RIG_TEST_SEAM_WRITE (F-19)"
  if { printf 'rig leak %s\n' "$RUN_ID" > "$RIG_TEST_SEAM_WRITE"; } 2>> "$RUN_DIR/seam.log"; then
    say "RIG_TEST_SEAM_WRITE: planted write landed (the seam check must catch it)"
  else
    say "RIG_TEST_SEAM_WRITE: planted write refused by the OS (reason in seam.log); verdict still from the seam check"
  fi
fi

# ── resume scan: rows the runner did not write, or that were cut, are refused (CONTRACT §2) ────────────────────
REFUSED_STEPS=" "
while IFS=' ' read -r what a b; do
  case "$what" in
    FOREIGN) ev "RECORD-FOREIGN row=$a" ;;
    REFUSED) ev "RECORD-REFUSED $a row=$b"; REFUSED_STEPS="$REFUSED_STEPS$a " ;;
  esac
done <<EOF
$(hp scan "$REC" "$RUN_ID")
EOF
# PRE-FLIGHT JUDGE (TR1.4 amendment + R8b; F-13, F-11): EVERY check this run will use is judged by
# `checks/selftest.sh --judge <check> <kind>` BEFORE s1, the default checks/ included. Any refusal (it passes a bad
# fixture, fails a good one, or cannot say CANNOT-READ) -> `SELFTEST-REFUSED <kind>.sh` and exit 1, nothing run.
#   * DEFAULT checks/ refused: always exit 1. RIG_TEST=1 does NOT override it: a broken default check is a rig
#     defect, never a test path. A missing default check is judged too (the judge refuses it).
#   * planted CHECKS_DIR refused: exit 1, unless RIG_TEST=1 (R8b: run on so the oracle's catch is measured; the run
#     is already marked RIG-TEST ON). A missing planted check is skipped here (CANNOT-READ at its first step, F-12).
#   * CACHE (default checks only; a planted dir's wrappers may read files the key does not cover): an ACCEPTED
#     verdict is stored at $SCRATCH/judge-cache/<key>, key = run_helper.py judge-key (sha256 over the check, the
#     check machinery, every fixture, canary/expected.py + card.txt + prompts, verdicts.py, python version). A
#     refusal is never cached; a changed byte in any keyed file is a new key, so a miss. Hits/misses go to judge.log
#     only (events.log stays empty on a clean run).
DEFAULT_CHECKS=0; [ "$(hp realpath "$CHECKS_DIR")" = "$(hp realpath "$RIG/checks")" ] && DEFAULT_CHECKS=1
JCACHE="$SCRATCH_R/judge-cache"; EMIT="${LIFEHACK_V2:-$HOME/lifehack-v2}/shared/emit"
judged_bad=0
for k in ai code human; do
  c="$CHECKS_DIR/$k.sh"
  if [ "$DEFAULT_CHECKS" = 0 ] && [ ! -f "$c" ]; then continue; fi
  key=""
  if [ "$DEFAULT_CHECKS" = 1 ] && [ -f "$c" ]; then
    key="$(hp judge-key "$RIG" "$EMIT" "$k" "$c" 2>/dev/null)" || key=""
    if [ -n "$key" ] && [ "$(cat "$JCACHE/$key" 2>/dev/null)" = "ACCEPTED $k" ]; then
      echo "judge-cache HIT $k.sh $key" >> "$RUN_DIR/judge.log"; continue
    fi
    echo "judge-cache MISS $k.sh ${key:-<no-key>}" >> "$RUN_DIR/judge.log"
  fi
  if bash "$RIG/checks/selftest.sh" --judge "$c" "$k" >> "$RUN_DIR/judge.log" 2>&1; then
    if [ -n "$key" ]; then
      mkdir -p "$JCACHE" && printf 'ACCEPTED %s\n' "$k" > "$JCACHE/.$key.$$" && mv -f "$JCACHE/.$key.$$" "$JCACHE/$key"
    fi
  else
    ev "SELFTEST-REFUSED $k.sh"; judged_bad=1
  fi
done
if [ "$judged_bad" = 1 ]; then
  if [ "$DEFAULT_CHECKS" = 0 ] && [ "${RIG_TEST:-}" = 1 ]; then
    say "RIG_TEST=1: running on with a REFUSED planted check (so the oracle's catch is measured)"
  else
    [ "$DEFAULT_CHECKS" = 1 ] && say "a DEFAULT check was refused by the judge: rig defect, refusing to start (RIG_TEST cannot override)"
    finish 1
  fi
fi

RESUMED=0; LAST_EPOCH=""
if LAST_EPOCH="$(hp last-valid-any "$REC" "$RUN_ID")"; then RESUMED=1; fi
RESUME_SAID=0

# ── helpers ────────────────────────────────────────────────────────────────────────────────────────────────────
sha_of() { shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'; }
RUNNER_PID=$$; [ "$GUARD" = on ] && RUNNER_PID="$RIG_GUARD_PARENT"   # exec.log names the group leader (R0)
xlog()   { printf '%s\ts%s\t%s\t%s\n' "$NOW" "$1" "$2" "$RUNNER_PID" >> "$EXEC"; }
append_row() {  # <n> <status> <sha> <model>
  local f1="$RUN_ID" f2="s$1" f3="$2" f4="$NOW" f5="$3" f6="$4" sum
  sum="$(hp rowsum "$f1" "$f2" "$f3" "$f4" "$f5" "$f6")"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$f1" "$f2" "$f3" "$f4" "$f5" "$f6" "$sum" >> "$REC"
}
status_upd() { bash "$RIG/status.sh" "$RUNG" "$RUN_ID" "$1" "$(hp cost "$RUN_DIR")" "$2" >/dev/null 2>&1; }
answer_for() {  # <n> -> the last --answer for sN, else the stored sN.answer
  local a; a="$(printf '%s\n' "$ANSWERS" | sed -n "s/^s$1=//p" | tail -1)"
  if [ -z "$a" ] && [ -f "$RUN_DIR/s$1.answer" ]; then a="$(head -1 "$RUN_DIR/s$1.answer")"; fi
  printf '%s' "$a"
}
# do_check <n> <kind> <file> -> CRC (0 pass / 1 fail / 4 cannot-read) and CCAT
do_check() {
  local n="$1" k="$2" f="$3" s="$CHECKS_DIR/$2.sh" out rc first
  CCAT=""
  if [ ! -f "$s" ]; then echo "check script missing: $s" >> "$RUN_DIR/s$n.check.log"; CRC=4; return; fi
  out="$(cd "$RIG" && CANARY_SEED="$SEED" bash "$s" "$RUN_DIR" "$n" "$f" 2>&1 </dev/null)"; rc=$?
  printf '%s\n' "$out" >> "$RUN_DIR/s$n.check.log"
  first="${out%%$'\n'*}"
  case "$rc" in
    0) CRC=0 ;;
    1) CCAT="$(printf '%s' "$first" | sed -n 's/^FAIL \([a-z-]*\): .*/\1/p')"
       case "$CATS" in *" $CCAT "*) CRC=1 ;; *) CRC=4 ;; esac ;;   # a fail without a contract category = rig defect
    *) CRC=4 ;;
  esac
}
fail_step() {  # <n> <event> <rc> [candidate]
  [ -n "${4:-}" ] && [ -f "$4" ] && cp -f "$4" "$RUN_DIR/s$1.rejected"
  ev "$2"; xlog "$1" end; status_upd "s$1" "$2"; finish "$3"
}
commit() {  # <n> <candidate> <status> <model>
  local n="$1" sha
  mv -f "$2" "$RUN_DIR/step-$n.json" || { ev "CANNOT-READ s$n"; finish 1; }
  sha="$(sha_of "$RUN_DIR/step-$n.json")"
  if [ -n "$FAKE" ] && [ -n "${RIG_HOLD_BEFORE_RECORD:-}" ] && [ "${RIG_HOLD_BEFORE_RECORD%%:*}" = "$n" ]; then
    # TR1.8 HANDSHAKE: the held marker tells the killer the hold has begun; the killer acts on the MARKER, never on
    # a clock. SECS is only the hold's deadline: if nobody killed us by then, the .expired marker + WAIT-TIMEOUT
    # make the late kill visible (k1 and inject F-07 refuse it), and the run carries on (its row then exists).
    say "RIG_HOLD_BEFORE_RECORD: holding up to ${RIG_HOLD_BEFORE_RECORD#*:}s between commit and record row of s$n"
    : > "$RUN_DIR/hold-s$n.held"
    sleep "${RIG_HOLD_BEFORE_RECORD#*:}"   # pacing: the hold's own deadline; the killer waits on hold-sN.held, not on this
    : > "$RUN_DIR/hold-s$n.expired"
    echo "WAIT-TIMEOUT hold s$n: not killed within ${RIG_HOLD_BEFORE_RECORD#*:}s" >&2
  fi
  append_row "$n" "$3" "$sha" "$4"
  xlog "$n" end
  status_upd "s$n" "$3"
}
check_or_fail() {  # <n> <kind> <candidate> : returns only on pass
  do_check "$1" "$2" "$3"
  case "$CRC" in
    0) return 0 ;;
    1) fail_step "$1" "CHECK-FAIL s$1 $CCAT" 1 "$3" ;;
    *) fail_step "$1" "CANNOT-READ s$1" 1 "$3" ;;
  esac
}

# ── the steps ──────────────────────────────────────────────────────────────────────────────────────────────────
# F-20 (RIG_TEST=1 + --fake only): the runner stops short and SAYS NOTHING (no event, exit 0). K=0: zero steps.
if [ "$EXIT_AFTER" = 0 ]; then say "TEST-EXIT-AFTER 0 (RIG_TEST=1: deliberate silent stop F-20)"; finish 0; fi
STEPS="$(grep -vE '^[[:space:]]*(#|$)' "$CARDF")"
while IFS= read -r line; do
  [ -n "$line" ] || continue
  id="${line%% | *}"; rest="${line#* | }"; kind="${rest%% | *}"; rest="${rest#* | }"; what="${rest%% | *}"
  n="${id#s}"
  case "$n" in ''|*[!0-9]*) say "bad card row: $line"; finish 1 ;; esac
  case "$kind" in ai|code|human) ;; *) say "bad kind '$kind' in card row: $line"; finish 1 ;; esac
  F="$RUN_DIR/step-$n.json"

  if [ "$n" = "$SKIP_STEP" ]; then say "TEST-SKIP s$n (RIG_TEST=1, --test-skip-step: deliberate runner bug F-14a)"; continue; fi

  # resume: is this step already done and still verified?
  rerun=0
  if vr="$(hp last-valid "$REC" "$RUN_ID" "s$n")"; then
    set -- $vr; vst="$1"; vsha="$2"; vmodel="$3"
    if [ "$vst" = done ] || [ "$vst" = skipped-done ] || [ "$vst" = halted ]; then
      ok=0
      if [ -f "$F" ] && [ "$(sha_of "$F")" = "$vsha" ]; then
        if [ "$vst" = halted ]; then
          [ "$(hp yes-swap "$F" "$STAGE_ROOT/s$n.yes" 2>/dev/null; echo $?)" = 0 ] && do_check "$n" "$kind" "$STAGE_ROOT/s$n.yes" && [ "$CRC" = 0 ] && ok=1
        else
          do_check "$n" "$kind" "$F"; [ "$CRC" = 0 ] && ok=1
        fi
      fi
      if [ "$ok" = 1 ] && [ "$vst" = halted ]; then say "s$n: halted earlier by a human 'no' — the run stays halted"; finish 0; fi
      if [ "$ok" = 1 ]; then append_row "$n" skipped-done "$vsha" "$vmodel"; say "skipped-done s$n"; status_upd "s$n" skipped-done; continue; fi
      rerun=1
    fi
  fi
  if [ "$rerun" = 0 ]; then
    case "$REFUSED_STEPS" in *" s$n "*) rerun=1 ;; esac
    [ -f "$F" ] && rerun=1
    awk -F'\t' -v s="s$n" '$2==s && $3=="begin"{f=1} END{exit !f}' "$EXEC" && rerun=1
  fi

  ans=""
  if [ "$kind" = human ]; then
    ans="$(answer_for "$n")"
  fi
  if [ "$RESUMED" = 1 ] && [ "$RESUME_SAID" = 0 ]; then
    ev "RESUME s$n gap_days=$(( (NOW - LAST_EPOCH) / 86400 ))"; RESUME_SAID=1
  fi
  [ "$rerun" = 1 ] && ev "RERUN s$n"

  if [ "$kind" = human ] && [ -z "$ans" ]; then
    append_row "$n" waiting "-" "-"; ev "WAITING s$n"; status_upd "s$n" waiting; finish 70
  fi

  xlog "$n" begin
  # PRE-FLIGHT (CONTRACT §3, F-14 live): the input step must be committed AND vouched for by the record.
  # It runs after `begin`, so the oracle sees that sN was reached while s(N-1) was passed over.
  if [ "$n" -ge 2 ]; then
    P="$RUN_DIR/step-$((n-1)).json"
    if [ ! -f "$P" ] || ! hp has-vouch "$REC" "$RUN_ID" "s$((n-1))" "$(sha_of "$P")"; then
      printf 'PRE-FLIGHT: step-%d.json missing or not vouched for by a valid done row\n' "$((n-1))" > "$RUN_DIR/s$n.rejected"
      ev "CHECK-FAIL s$n input-missing"; xlog "$n" end; status_upd "s$n" input-missing; finish 1
    fi
  fi

  ST="$STAGE_ROOT/s$n"; rm -rf "$ST"; mkdir -p "$ST"
  case "$kind" in
    code|human)
      [ "$n" -ge 2 ] && cp "$RUN_DIR/step-$((n-1)).json" "$ST/step-$((n-1)).json"
      if [ "$kind" = code ]; then
        script="$(printf '%s' "$what" | awk '{print $2}')"
        ( cd "$RIG" && CANARY_SEED="$SEED" python3 "$RIG/$script" "$ST" </dev/null ) >> "$RUN_DIR/s$n.code.log" 2>&1; rc=$?
      else
        printf '%s\n' "$ans" > "$RUN_DIR/.s$n.answer.tmp" && mv -f "$RUN_DIR/.s$n.answer.tmp" "$RUN_DIR/s$n.answer"
        ( cd "$RIG" && CANARY_SEED="$SEED" python3 "$RIG/canary/code/human.py" "$ST" "$n" "$ans" </dev/null ) >> "$RUN_DIR/s$n.code.log" 2>&1; rc=$?
        [ "$rc" = 3 ] && fail_step "$n" "CHECK-FAIL s$n answer" 1
      fi
      [ "$rc" = 0 ] || fail_step "$n" "CANNOT-READ s$n" 1
      CAND="$ST/step-$n.json"; MODEL="$NO_MODEL"
      if [ "$kind" = human ] && [ "$ans" = no ]; then
        # a "no" is a legitimate halt: the file is committed (SPEC §4), content-checked with the answer swapped
        hp yes-swap "$CAND" "$ST/yes.json" || fail_step "$n" "CANNOT-READ s$n" 1 "$CAND"
        check_or_fail "$n" "$kind" "$ST/yes.json"
        commit "$n" "$CAND" halted "$NO_MODEL"; say "HALTED s$n (human answered no)"; finish 0
      fi
      check_or_fail "$n" "$kind" "$CAND" ;;
    ai)
      PROMPT="$(cd "$RIG" && CANARY_SEED="$SEED" python3 -I -B -c '
import os, sys
sys.path.insert(0, sys.argv[1]); import expected
sys.stdout.write(expected.render(int(sys.argv[2]), sys.argv[3], int(os.environ["CANARY_SEED"])))' "$RIG/canary" "$n" "$RUN_DIR")"
      [ -n "$PROMPT" ] || fail_step "$n" "CANNOT-READ s$n" 1
      actor_argv "$PROMPT"
      RAW="$ST/raw.json"
      wd=""; [ -n "${RIG_WATCHDOG_SECS:-}" ] && wd="$RIG_WATCHDOG_SECS"
      ( cd "$RUN_DIR" && env ${wd:+BUDGET_WATCHDOG_FLOOR=$wd} FAKE_MODE="${FAKE:-}" \
          bash "$RIG/budget.sh" call "$RUN_ID" -- env -u CANARY_SEED -u SKILL_TESTER_SEED "${ACTOR[@]}" ) \
          > "$RAW" 2>> "$RUN_DIR/s$n.budget.log" </dev/null
      rc=$?
      [ -s "$RAW" ] && cp -f "$RAW" "$RUN_DIR/s$n.raw.json"
      case "$rc" in
        0) ;;
        75) fail_step "$n" "BUDGET-REFUSED s$n" 75 ;;
        124) fail_step "$n" "WATCHDOG s$n" 124 ;;
        *) fail_step "$n" "MODEL-FAIL s$n rc=$rc" 1 ;;
      esac
      CAND="$ST/cand.json"
      if [ -z "$(tr -d '[:space:]' < "$RAW")" ]; then
        : > "$CAND"; MODEL="$MODEL_ID"                   # empty reply: the check names it (CHECK-FAIL sN empty)
      else
        MODEL="$(hp result "$RAW" "$CAND" "$MODEL_ID")" || fail_step "$n" "MODEL-FAIL s$n rc=0" 1   # no JSON result / is_error
      fi
      check_or_fail "$n" ai "$CAND"
      if OLD="$(hp last-ai-model "$REC" "$RUN_ID")" && [ "$OLD" != "$MODEL" ]; then ev "VERSION-CHANGE s$n $OLD -> $MODEL"; fi ;;
  esac
  commit "$n" "$CAND" done "$MODEL"
  if [ -n "$EXIT_AFTER" ] && [ "$n" = "$EXIT_AFTER" ]; then say "TEST-EXIT-AFTER $n (RIG_TEST=1: deliberate silent stop F-20)"; finish 0; fi
done <<EOF
$STEPS
EOF
finish 0
