#!/bin/bash
# ladder.sh — card TR2.1 of the skill-tester-rig: the rung-2 LADDER (n independent canary runs on the real actor).
# ENTRY POINT, on-demand (ruling 9): a person starts it from a window's Bash, NEVER from an Agent-tool sub-agent
# (ruling 7). It is an UNGUARDED orchestrator, like bite.sh and actor-guard.sh: it starts the guarded runs and reads
# their evidence; it never runs inside sandbox-exec itself (refused when RIG_GUARD_TAG is set).
#
#   ladder.sh --rung 2 [--n 3] [--model small|medium|large]       REAL. --model also takes the card's words:
#                         haiku -> small · sonnet -> medium · opus -> large (passed to run.sh as --model-tier; no model
#                         id is ever typed here, run.sh reads it from shared/tools/model_ids.py). Default medium, n 3.
#                         Each run is `run.sh --real --model-tier <t> --run-id <id> --rung rung2 --answer s4=yes
#                         --answer s9=yes`: exactly actor-guard.sh's real shape (the write guard, the throwaway HOME,
#                         the Harness as --plugin-dir, all inside run.sh). The n runs are launched with `xargs -P 3`.
#   ladder.sh --rung 2 --fake [--n N] [--scratch DIR] [--test-fault K:ok11|seam|budget]...
#                         TEST PATH: the same fan-out, the same run.sh argv except `--fake good` for `--real` (so the
#                         FAKE model, fake-claude.sh; a real claude cannot start), RIG_TEST=1 on every run (each run's
#                         events.log starts `RIG-TEST ON`), results in <DIR>/ladder-results.tsv (DIR under the scratch
#                         root, default <scratch>/ladder-fake), NEVER the real results file, NEVER a receipt.
#                         Parallelism is PROVEN, not trusted: every fake actor holds at s2 until min(n,3) runs have
#                         started (a wait.lib.sh handshake; `WAIT-TIMEOUT ladder: <k> runs started` if they never do).
#                         --test-fault plants one fault in run K: ok11 (run.sh --test-exit-after 11: rc 0, truth ok=11),
#                         seam (F-19's planted rig write into a fake-real state root: SEAM-DENIED), budget (the run's
#                         budget opened with a $0 cap: BUDGET-REFUSED s2, exit 75).
#   ladder.sh --rung 2 ... --dry-run    print the plan (one run.sh argv per run) and exit; launches and writes nothing.
#   ladder.sh --selftest  fake model only; every check watched failing first. Last line `SELFTEST ladder <n>/<n> ALL OK`.
#
# SCORE, per run, in launch order. A run is `ok` ONLY when ALL hold, else `fail` with the reasons named:
#   truth.py --run <id> prints EXACTLY `TOTAL ok=12 silent_wrong=0 double_ran=0 stuck=0 lost=0 skipped=0
#   out_of_order=0 false_done=0`, no FLAG line, exit 0 · run.sh exit 0 · SEAM_GUARD=on in meta.env · seam verify clean:
#   no SEAM-LEAK / SEAM-DENIED / SEAM-CANNOT-READ / GUARD-PROBE-FAILED line (SEAM-AMBIENT and SEAM-DENIED-RULED are
#   allowed and counted, CONTRACT §3a and the TR2.0b ruling) · no BUDGET-REFUSED (exit 75 is a NAMED failure, never a
#   pass) · no other event line · real mode: no `RIG-TEST ON` (a test-path run is refused) · the ladder proved its
#   parallelism (max overlap of the runs' start/end stamps >= min(n,3); else every row fails `parallel-unproven`).
# SEAM: the snapshot before / verify after is run.sh's own (seam.sh, per run, under the write guard, classified per
#   CONTRACT §3a). A ladder-wide unguarded snapshot is NOT taken: it could not tell another window's write from a
#   run's and would cry wolf (ruling 13). Each ladder gives its runs their own stand-in, <scratch>/notes-standin/<id>/.
# BUDGET: before launch, each run's ledger is opened with `budget.sh open <run> --ladder-id <ladder-id>` (default caps
#   $5 / 40 calls per run, $50 per ladder), so the $50 ladder cap binds across all its runs; run.sh's own `open` then
#   keeps that ledger.
# COST: total_cost_usd and num_turns of every ai step, read from the step's JSON result (sN.raw.json), go to
#   <ladder dir>/cost.tsv (run_id, step, total_cost_usd, num_turns, model). An ai step that began with no readable
#   cost is UNKNOWN, never 0; the ladder's $ is then a floor and says so (`COST-UNKNOWN <k> steps`).
# STATUS: run.sh updates STATUS.md on every step (status.sh, rung `rung2`); the ladder updates it at start and end.
# RESULTS FILE DESIGN (no double counting): every ladder invocation writes a FRESH results file. At the start, an
#   existing ladder-results.tsv is MOVED (never deleted) to ladder-results.tsv.prev-<UTC stamp>-<pid>; then one row
#   per run is appended as the runs are scored. So the card's Verify,
#     awk -F"\t" '$1=="rung2" && $2=="ok" {n++} END {print n"/3"}' ladder-results.tsv
#   only ever counts the LATEST ladder, and a crashed ladder leaves a short file (fewer ok rows), never a stale 3/3.
#   Row: rung2 <TAB> ok|fail <TAB> run-id <TAB> TOTAL line <TAB> cost_usd <TAB> UTC timestamp <TAB> why (`-` if ok).
#   A lock ($S/ladder.lock, released by moving it to <scratch>/trash/) keeps two ladders off one results file.
# OUTPUT: one line per run, the parallel proof, the costs, `NEAR-MISS 2/3: run --n 5 before deciding` when exactly one
#   run fails, and LAST:  LADDER rung2 ok <N>/<M> cost $<X>
# RECEIPT: real mode only, written HERE after every run has ended, whatever the outcome:
#   `receipt.sh write rung2 "<the LADDER line>"` (a fail line is a receipt too; it never matches).
# Files: <scratch>/ladder/<ladder-id>/{jobs.txt,faults.txt,cost.tsv,runs/<run-id>.{t0,t1,rc,run.out,truth.out}}.
# Exit: 0 every run ok · 1 not · 2 refused · 3 receipt not written. bash 3.2 + BSD tools, no set -e. This script
# deletes nothing.
set -u
export PYTHONDONTWRITEBYTECODE=1
RIG="$(cd "$(dirname "$0")" && pwd)"
SELF="$RIG/$(basename "$0")"
CANON="$HOME/lifehack-scratch/skill-tester-rig"
TRASH="$HOME/lifehack-scratch/skill-tester-rig/trash"
. "$RIG/wait.lib.sh" || { echo "ladder: wait.lib.sh missing" >&2; exit 2; }
CLEAN_TOTAL="TOTAL ok=12 silent_wrong=0 double_ran=0 stuck=0 lost=0 skipped=0 out_of_order=0 false_done=0"
ANS=( --answer s4=yes --answer s9=yes )
# the env a real ladder refuses (it could steer a run or the receipt); SKILL_TESTER_RECEIPTS and SKILL_TESTER_SCRATCH
# are checked LAST so a refusal test can keep them set as a backstop
REFUSE_ENV="CLAUDE_BIN RIG_TEST SKILL_TESTER_RIG CHECKS_DIR SEAM_STATE_ROOT RIG_TEST_SEAM_WRITE SEAM_GUARD_DISABLE RIG_NUDGE
RIG_RUN_DIR SEAM_SKILL_ROOTS SEAM_HOOKS_JSON SKILL_TESTER_RECEIPT_RIG SKILL_TESTER_RECEIPTS SKILL_TESTER_SCRATCH"
unset FAKE_MODE FAKE_MODE_STEP FAKE_MODEL_ID FAKE_WAIT_FILE FAKE_WAIT_STEP FAKE_WAIT_SECS RIG_HOLD_BEFORE_RECORD \
      RIG_WATCHDOG_SECS STRESS_TODAY CANARY_SEED SKILL_TESTER_SEED BUDGET_WATCHDOG_FLOOR SEAM_STANDIN SENTINEL_LOG

die()   { echo "ladder: REFUSED: $*" >&2; exit 2; }
utc()   { date -u +%Y-%m-%dT%H:%M:%SZ; }
stamp() { python3 -I -B -c 'import time; print("%.3f" % time.time())'; }
tier_of() {
  case "$1" in small|haiku) echo small ;; medium|sonnet) echo medium ;; large|opus) echo large ;; *) return 1 ;; esac
}
# run_argv <real|fake> <tier> <run-id> : sets RUNARGV, the ONE run.sh argv (real and fake differ only in --real/--fake)
run_argv() {
  if [ "$1" = real ]; then RUNARGV=( --real ); else RUNARGV=( --fake good ); fi
  RUNARGV=( "${RUNARGV[@]}" --model-tier "$2" --run-id "$3" --rung rung2 "${ANS[@]}" )
}

# ── the judge: judge <run-dir> <truth-out> <truth-rc> <run-rc|-> <real|fake>
#    prints ONE line `ok<TAB>-<TAB><notes>` or `fail<TAB><reasons><TAB><notes>`. Pure: reads files, writes nothing.
judge() {
  python3 -I -B - "$@" "$CLEAN_TOTAL" <<'PY'
import os, sys
rd, tout, trc, rrc, mode, clean = sys.argv[1:7]
def lines(p):
    try: return [l.rstrip("\n") for l in open(p, encoding="utf-8", errors="replace")]
    except OSError: return None
bad = []
if rrc == "-":
    print("fail\trun not launched\t-"); sys.exit(0)
ev = lines(os.path.join(rd, "events.log"))
if ev is None: bad.append("no events.log"); ev = []
ev = [l for l in ev if l.strip()]
budget = [l for l in ev if l.startswith("BUDGET-REFUSED ")]
seam = [l for l in ev if l.startswith(("SEAM-LEAK ", "SEAM-DENIED ", "SEAM-CANNOT-READ", "GUARD-PROBE-FAILED"))]
amb = sum(1 for l in ev if l.startswith("SEAM-AMBIENT "))
ruled = sum(1 for l in ev if l.startswith("SEAM-DENIED-RULED "))
rigtest = "RIG-TEST ON" in ev
other = [l for l in ev if not (l in budget or l in seam or l == "RIG-TEST ON"
                               or l.startswith(("SEAM-AMBIENT ", "SEAM-DENIED-RULED ")))]
if budget: bad.insert(0, "%s (exit 75, a named failure)" % budget[0])
if rrc == "75" and not budget: bad.append("run rc=75 with no BUDGET-REFUSED line (lock held or no token)")
elif rrc != "0" and not (rrc == "75" and budget): bad.append("run rc=%s" % rrc)
if seam: bad.append("seam %d (%s)" % (len(seam), seam[0]))
if rigtest and mode == "real": bad.append("test-path run refused (RIG-TEST ON)")
meta = lines(os.path.join(rd, "meta.env"))
if meta is None: bad.append("no meta.env")
elif "SEAM_GUARD=on" not in meta: bad.append("guard not on (%s)" % (",".join(l for l in meta if l.startswith("SEAM_GUARD=")) or "no SEAM_GUARD line"))
if other: bad.append("events %d (%s)" % (len(other), other[0]))
tl = lines(tout) or []
if trc != "0": bad.append("truth rc=%s" % trc)
if clean not in tl: bad.append("truth %s" % next((l for l in tl if l.startswith("TOTAL ")), "no TOTAL line"))
flags = [l for l in tl if l.startswith("FLAG")]
if flags: bad.append("truth %s" % flags[0])
notes = "ambient=%d ruled=%d" % (amb, ruled)
print(("ok\t-\t" if not bad else "fail\t" + " · ".join(bad).replace("\t", " ") + "\t") + notes)
PY
}

# ── one run (called by xargs): --one <k> <run-id>. Reads _LAD_MODE _LAD_TIER _LAD_DIR _LAD_S _LAD_PAR_WAIT.
one() {
  local k="$1" R="$2" D rc trc fault fr
  [ -n "${_LAD_DIR:-}" ] && [ -n "${_LAD_S:-}" ] && [ -n "$R" ] || { echo "ladder --one: missing context" >&2; return 1; }
  D="$_LAD_DIR/runs"
  if [ ! -e "$D/$R.budget-ok" ]; then echo "-" > "$D/$R.rc"; return 0; fi   # its ledger never opened: never launched
  fault="$(awk -v k="$k" '$1==k{print $2}' "$_LAD_DIR/faults.txt" 2>/dev/null | tail -1)"
  run_argv "$_LAD_MODE" "$_LAD_TIER" "$R"
  stamp > "$D/$R.t0"
  (
    if [ "$_LAD_MODE" = fake ]; then
      export SKILL_TESTER_SCRATCH="$_LAD_S" RIG_TEST=1
      export FAKE_WAIT_FILE="$_LAD_DIR/release" FAKE_WAIT_STEP=2 FAKE_WAIT_SECS=$(( _LAD_PAR_WAIT + 60 ))
      case "$fault" in
        ok11) RUNARGV=( "${RUNARGV[@]}" --test-exit-after 11 ) ;;
        seam) # F-19's planting: the rig itself writes into a fake-real state root OUTSIDE the guard's allow list
              fr="$HOME/lifehack-scratch/skill-tester-rig-fake-real/$R/state"
              mkdir -p "$fr" && echo "fake real note for $R" > "$fr/note.md"
              export SEAM_STATE_ROOT="$fr" RIG_TEST_SEAM_WRITE="$fr/rig-leak-$R.md" ;;
      esac
    fi
    exec bash "$RIG/run.sh" "${RUNARGV[@]}"
  ) > "$D/$R.run.out" 2>&1 </dev/null
  rc=$?
  stamp > "$D/$R.t1"
  echo "$rc" > "$D/$R.rc"
  if [ "$_LAD_MODE" = fake ]; then
    SKILL_TESTER_SCRATCH="$_LAD_S" python3 -B "$RIG/truth.py" --run "$R" > "$D/$R.truth.out" 2> "$D/$R.truth.err"; trc=$?
  else
    python3 -B "$RIG/truth.py" --run "$R" > "$D/$R.truth.out" 2> "$D/$R.truth.err"; trc=$?
  fi
  echo "$trc" > "$D/$R.truth.rc"
  SKILL_TESTER_SCRATCH="$_LAD_S" bash "$RIG/status.sh" rung2 "$R" "end" 0 "run ended rc=$rc truth=$trc" >/dev/null 2>&1
  return 0
}

# ── results file: FRESH per invocation, the previous one KEPT (moved, never deleted). See the header.
results_fresh() {
  if [ -e "$RES" ]; then mv "$RES" "$RES.prev-$(date -u +%Y%m%dT%H%M%SZ)-$$" || return 1; fi
  printf '# rung\tverdict\trun_id\ttotal\tcost_usd\tutc\twhy\n' > "$RES"   # fresh
}

LOCKD=""; WPID=""
release() {
  [ -n "$WPID" ] && kill "$WPID" 2>/dev/null
  if [ -n "$LOCKD" ] && [ -d "$LOCKD" ]; then mkdir -p "$TRASH" && mv "$LOCKD" "$TRASH/ladder.lock.$(date -u +%Y%m%dT%H%M%SZ)-$$"; fi
  return 0
}
take_lock() {
  local owner
  LOCKD="$S/ladder.lock"
  if ! mkdir "$LOCKD" 2>/dev/null; then
    owner="$(cat "$LOCKD/pid" 2>/dev/null)"
    if [ -n "$owner" ] && kill -0 "$owner" 2>/dev/null; then LOCKD=""; die "another ladder (pid $owner) holds $S/ladder.lock"; fi
    mkdir -p "$TRASH" && mv "$S/ladder.lock" "$TRASH/ladder.lock.stale-$(date -u +%Y%m%dT%H%M%SZ)-$$" || { LOCKD=""; die "cannot move the stale lock"; }
    mkdir "$LOCKD" 2>/dev/null || { LOCKD=""; die "lock race on $S/ladder.lock"; }
  fi
  echo $$ > "$LOCKD/pid"
  trap release EXIT
  trap 'exit 143' INT TERM
}
started_n() { [ "$(ls "$LD/runs" 2>/dev/null | grep -c '\.t0$')" -ge "$1" ]; }

# ── the ladder ──────────────────────────────────────────────────────────────────────────────────────────────────
ladder() {
  local RUNG="" N=3 MODEL=medium MODE=real SCR="" DRY=0 FAULTS="" TIER f k kind R v
  while [ $# -gt 0 ]; do
    case "$1" in
      --rung) RUNG="${2:-}"; shift 2 || die "--rung needs a value" ;;
      --n) N="${2:-}"; shift 2 || die "--n needs a value" ;;
      --model) MODEL="${2:-}"; shift 2 || die "--model needs a value" ;;   # allow-silence: flag parsing; the value is a tier or family alias mapped to a tier by tier_of, never a model id
      --fake) MODE=fake; shift ;;
      --scratch) SCR="${2:-}"; shift 2 || die "--scratch needs a value" ;;
      --test-fault) FAULTS="$FAULTS ${2:-}"; shift 2 || die "--test-fault needs K:kind" ;;
      --dry-run) DRY=1; shift ;;
      *) die "unknown argument '$1'" ;;
    esac
  done
  [ "$RUNG" = 2 ] || die "only --rung 2 exists"
  TIER="$(tier_of "$MODEL")" || die "--model must be small|medium|large (or haiku|sonnet|opus), got '$MODEL'"   # allow-silence: tier_of maps family aliases to small|medium|large; no model id is named
  case "$N" in ''|0|*[!0-9]*) die "--n must be a positive integer" ;; esac
  [ -z "${RIG_GUARD_TAG:-}" ] || die "inside a guarded run (this is the unguarded orchestrator)"
  if [ "$MODE" = real ]; then
    for v in $REFUSE_ENV; do
      eval "vv=\${$v:-}"; [ -z "$vv" ] || die "$v is set; the real ladder writes the real results and the rung2 receipt and refuses overrides"
    done
    [ -z "$SCR" ] || die "--scratch is a test path (it needs --fake)"
    [ -z "$FAULTS" ] || die "--test-fault is a test path (it needs --fake)"
    S="$CANON"; RES="$CANON/ladder-results.tsv"
  else
    unset CLAUDE_BIN SKILL_TESTER_RIG CHECKS_DIR SEAM_STATE_ROOT RIG_TEST_SEAM_WRITE SEAM_GUARD_DISABLE RIG_NUDGE RIG_RUN_DIR
    S="${SCR:-$CANON/ladder-fake}"
    case "$S" in *..*) die "--scratch must not contain '..'" ;; esac
    case "$S/" in "$CANON"/?*/) ;; *) die "--scratch must lie under $CANON (ruling 6), got '$S'" ;; esac
    RES="$S/ladder-results.tsv"
    for f in $FAULTS; do
      k="${f%%:*}"; kind="${f#*:}"
      case "$k" in ''|*[!0-9]*) die "--test-fault K must be a run number: '$f'" ;; esac
      [ "$k" -ge 1 ] && [ "$k" -le "$N" ] || die "--test-fault run $k is outside 1..$N"
      case "$kind" in ok11|seam|budget) ;; *) die "--test-fault kind must be ok11|seam|budget: '$f'" ;; esac
    done
  fi
  local LID="L2-$(date -u +%Y%m%dT%H%M%SZ)-$$" PP=3 IDS="" i
  [ "$N" -lt 3 ] && PP="$N"
  i=1; while [ "$i" -le "$N" ]; do IDS="$IDS l2-r$i-${LID#L2-}"; i=$((i+1)); done
  if [ "$DRY" = 1 ]; then
    echo "LADDER PLAN rung2 mode=$MODE tier=$TIER n=$N parallel=xargs -P 3 ladder-id=$LID results=$RES receipt=$([ "$MODE" = real ] && echo rung2 || echo none)"
    for R in $IDS; do run_argv "$MODE" "$TIER" "$R"; echo "bash $RIG/run.sh ${RUNARGV[*]}"; done
    echo "LADDER DRY-RUN: nothing launched, nothing written"; return 0
  fi
  if [ "$MODE" = real ]; then
    [ -s "$HOME/.config/lifehack/claude-oauth-token" ] || die "no token at ~/.config/lifehack/claude-oauth-token (run.sh would stand down)"
    command -v claude >/dev/null 2>&1 || die "no claude binary on PATH"
  fi
  mkdir -p "$S" || die "cannot create $S"
  take_lock
  LD="$S/ladder/$LID"
  mkdir -p "$LD/runs" || die "cannot create $LD"
  results_fresh || die "cannot start a fresh results file at $RES"
  : > "$LD/faults.txt"
  for f in $FAULTS; do printf '%s\t%s\n' "${f%%:*}" "${f#*:}" >> "$LD/faults.txt"; done
  export SEAM_STANDIN="$CANON/notes-standin/$LID"           # CONTRACT §3b: this ladder's own stand-in
  mkdir -p "$SEAM_STANDIN" || die "cannot create $SEAM_STANDIN"
  echo "LADDER rung2: id=$LID mode=$MODE tier=$TIER n=$N (xargs -P 3) dir=$LD results=$RES"
  # budget: each run's ledger opened INSIDE this ladder's ledger, so the ladder cap binds across the runs
  : > "$LD/jobs.txt"; k=1
  for R in $IDS; do
    local usd=()
    [ "$MODE" = fake ] && grep -qx "$k	budget" "$LD/faults.txt" && usd=( --usd 0 )
    if SKILL_TESTER_SCRATCH="$S" bash "$RIG/budget.sh" open "$R" --ladder-id "$LID" ${usd[@]+"${usd[@]}"} > "$LD/runs/$R.budget-open.log" 2>&1; then
      : > "$LD/runs/$R.budget-ok"
    else echo "  run $k $R: budget ledger NOT opened (see $LD/runs/$R.budget-open.log); it will not launch"; fi
    echo "$k $R" >> "$LD/jobs.txt"; k=$((k+1))
  done
  SKILL_TESTER_SCRATCH="$S" bash "$RIG/status.sh" rung2 "$LID" "0/$N runs" 0 "ladder started ($MODE, $TIER)" >/dev/null 2>&1
  export _LAD_MODE="$MODE" _LAD_TIER="$TIER" _LAD_DIR="$LD" _LAD_S="$S" _LAD_PAR_WAIT="${_LAD_PAR_WAIT:-60}"
  case "$_LAD_PAR_WAIT" in ''|*[!0-9]*) die "_LAD_PAR_WAIT must be an integer" ;; esac
  if [ "$MODE" = fake ]; then
    # the parallel HANDSHAKE: every fake actor holds at s2 until min(n,3) runs have started; then released. Run out ->
    # WAIT-TIMEOUT, released anyway (so the runs end) and the barrier-met marker is never written
    ( if wait_until "$_LAD_PAR_WAIT" "ladder: $PP runs started" started_n "$PP"; then : > "$LD/barrier-met"; fi
      : > "$LD/release" ) &
    WPID=$!
  fi
  local t0 t1; t0=$(date +%s)
  xargs -P 3 -L 1 bash "$SELF" --one < "$LD/jobs.txt"
  t1=$(date +%s)
  if [ -n "$WPID" ]; then wait "$WPID"; WPID=""; fi
  # ── parallel proof: the max overlap of the runs' [t0,t1] stamps
  local MX PAR_BAD=""
  MX="$(python3 -I -B - "$LD/runs" $IDS <<'PY'
import sys
d, ids = sys.argv[1], sys.argv[2:]
ev = []
for r in ids:
    try:
        t0 = float(open("%s/%s.t0" % (d, r)).read()); t1 = float(open("%s/%s.t1" % (d, r)).read())
    except (OSError, ValueError):
        continue
    ev += [(t0, 1), (t1, -1)]
ev.sort(key=lambda e: (e[0], e[1]))        # an end and a start at the same instant: the end first (conservative)
cur = mx = 0
for _, x in ev:
    cur += x; mx = max(mx, cur)
print(mx)
PY
)"
  [ "${MX:-0}" -ge "$PP" ] || PAR_BAD="parallel-unproven max-overlap ${MX:-0}/$PP"
  if [ "$MODE" = fake ] && [ ! -e "$LD/barrier-met" ]; then PAR_BAD="${PAR_BAD:+$PAR_BAD · }parallel handshake WAIT-TIMEOUT"; echo "WAIT-TIMEOUT ladder: $PP runs started"; fi
  echo "PARALLEL max-overlap ${MX:-0}/$PP (start/end stamps$([ "$MODE" = fake ] && echo ", s2 handshake $([ -e "$LD/barrier-met" ] && echo met || echo NOT met)"))"
  # ── cost.tsv (every ai step's total_cost_usd and num_turns from its JSON result)
  local RDS=() CSUM
  for R in $IDS; do RDS=( ${RDS[@]+"${RDS[@]}"} "$R" "$(python3 -I "$RIG/run_helper.py" rundir "$S" "$R")" ); done
  CSUM="$(python3 -I -B - "$RIG/canary/card.txt" "$LD/cost.tsv" ${RDS[@]+"${RDS[@]}"} <<'PY'
import json, os, re, sys
card, out, rest = sys.argv[1], sys.argv[2], sys.argv[3:]
ai = [m.group(1) for m in (re.match(r"^s(\d+) \| ai \|", l) for l in open(card)) if m]
rows = ["run_id\tstep\ttotal_cost_usd\tnum_turns\tmodel"]
for i in range(0, len(rest), 2):
    rid, rd = rest[i], rest[i + 1]
    began = set()
    try:
        for l in open(os.path.join(rd, "exec.log")):
            f = l.rstrip("\n").split("\t")
            if len(f) >= 3 and f[2] == "begin": began.add(f[1])
    except OSError:
        pass
    s = 0.0; unk = 0; turns = 0
    for n in ai:
        p = os.path.join(rd, "s%s.raw.json" % n)
        if not os.path.exists(p) and ("s" + n) not in began:
            continue                              # never reached: no call, no cost
        c = t = "UNKNOWN"; model = "-"   # allow-silence: a placeholder for an unreported model field, not a model id
        try:
            j = json.loads(open(p, encoding="utf-8").read())
            if isinstance(j.get("total_cost_usd"), (int, float)): c = "%.6f" % j["total_cost_usd"]
            if isinstance(j.get("num_turns"), int): t = str(j["num_turns"])
            model = str(j.get("model") or "-")
        except (OSError, ValueError, AttributeError):
            pass
        if c == "UNKNOWN": unk += 1
        else: s += float(c)
        if t != "UNKNOWN": turns += int(t)
        rows.append("%s\ts%s\t%s\t%s\t%s" % (rid, n, c, t, model))
    print("%s\t%.4f\t%d\t%d" % (rid, s, unk, turns))
open(out, "w").write("\n".join(rows) + "\n")
PY
)"
  # ── score every run, in launch order; one row each
  local NOK=0 M=0 TOTC=0 UNK=0 rc trc rd TL J verdict why notes c u tn
  for R in $IDS; do
    M=$((M+1))
    rc="$(cat "$LD/runs/$R.rc" 2>/dev/null)"; [ -n "$rc" ] || rc="-"
    trc="$(cat "$LD/runs/$R.truth.rc" 2>/dev/null)"; [ -n "$trc" ] || trc="-"
    rd="$(python3 -I "$RIG/run_helper.py" rundir "$S" "$R")"
    [ -f "$LD/runs/$R.truth.out" ] || : > "$LD/runs/$R.truth.out"
    TL="$(grep '^TOTAL ' "$LD/runs/$R.truth.out" | tail -1)"; [ -n "$TL" ] || TL="no TOTAL line"
    J="$(judge "$rd" "$LD/runs/$R.truth.out" "$trc" "$rc" "$MODE")"
    [ -n "$J" ] || J="fail	judge produced no line	-"
    verdict="$(printf '%s' "$J" | cut -f1)"; why="$(printf '%s' "$J" | cut -f2)"; notes="$(printf '%s' "$J" | cut -f3)"
    if [ -n "$PAR_BAD" ]; then verdict=fail; if [ "$why" = - ]; then why="$PAR_BAD"; else why="$PAR_BAD · $why"; fi; fi
    c="$(printf '%s\n' "$CSUM" | awk -F'\t' -v r="$R" '$1==r{print $2}')"; [ -n "$c" ] || c="0.0000"
    u="$(printf '%s\n' "$CSUM" | awk -F'\t' -v r="$R" '$1==r{print $3}')"; [ -n "$u" ] || u=0
    tn="$(printf '%s\n' "$CSUM" | awk -F'\t' -v r="$R" '$1==r{print $4}')"; [ -n "$tn" ] || tn=0
    TOTC="$(awk -v a="$TOTC" -v b="$c" 'BEGIN{printf "%.4f", a+b}')"; UNK=$((UNK+u))
    [ "$verdict" = ok ] && NOK=$((NOK+1))
    printf 'rung2\t%s\t%s\t%s\t%s\t%s\t%s\n' "$verdict" "$R" "$TL" "$c" "$(utc)" "$why" >> "$RES"
    echo "RUN $M $R $verdict rc=$rc $TL cost \$$c turns $tn $notes$([ "$why" = - ] || printf ' · why: %s' "$why")"
    grep -h '^BUDGET-REFUSED ' "$rd/events.log" 2>/dev/null | head -1 | sed "s/^/BUDGET-REFUSED $R: /"
  done
  [ "$UNK" -gt 0 ] && echo "COST-UNKNOWN $UNK steps (no total_cost_usd in their result: the \$ below is a FLOOR)"
  local LF="$S/budget/ladder-$LID.tsv"
  [ -f "$LF" ] && echo "BUDGET ladder $LID spent \$$(awk -F'\t' '$1=="charge" && $4!="UNKNOWN"{s+=$4} END{printf "%.4f", s+0}' "$LF") of \$$(awk -F'\t' '$1=="cap_usd"{v=$2} END{print v}' "$LF") · cost.tsv $LD/cost.tsv"
  echo "WALL $((t1-t0))s for $M runs · results $RES"
  [ "$NOK" = $((M-1)) ] && [ "$M" -ge 2 ] && { if [ "$M" -lt 5 ]; then echo "NEAR-MISS $NOK/$M: run --n 5 before deciding"; else echo "NEAR-MISS $NOK/$M"; fi; }
  SKILL_TESTER_SCRATCH="$S" bash "$RIG/status.sh" rung2 "$LID" "$M/$M runs" "$TOTC" "ladder finished: ok $NOK/$M" >/dev/null 2>&1
  local LAST="LADDER rung2 ok $NOK/$M cost \$$TOTC" RC=1
  [ "$NOK" = "$M" ] && RC=0
  release; LOCKD=""; trap - EXIT
  if [ "$MODE" = real ]; then
    # RECEIPT: here, unguarded, after every run has ended, whatever the outcome
    if ! bash "$RIG/receipt.sh" write rung2 "$LAST" 1>&2; then echo "ladder: RECEIPT NOT WRITTEN for '$LAST'" >&2; echo "$LAST"; return 3; fi
  fi
  echo "$LAST"
  return "$RC"
}

# ───────────────────────────────────────── selftest (FAKE model only) ─────────────────────────────────────────
SN=0; SF=0
chk() { local l="$1"; shift; SN=$((SN+1)); if "$@"; then echo "  ok   $l"; else SF=$((SF+1)); echo "  FAIL $l"; fi; }
has_line() { printf '%s\n' "$LOUT" | grep -qxF -- "$1"; }
has_re()   { printf '%s\n' "$LOUT" | grep -qE -- "$1"; }
no_re()    { ! has_re "$1"; }
okrows()   { awk -F"\t" '$1=="rung2" && $2=="ok" {n++} END {print n+0}' "$1" 2>/dev/null; }
card_verify() { awk -F"\t" '$1=="rung2" && $2=="ok" {n++} END {print n"/3"}' "$1"; }   # the card's Verify, verbatim
row_field() { awk -F'\t' -v k="$2" -v c="$3" '$1=="rung2"{i++; if(i==k) print $c}' "$1"; }   # row_field <tsv> <k> <col>
# st_lad <case> <want-rc> <args...> : one fake ladder into $B/<case>; sets LOUT LRC LLAST LDIR LLD
st_lad() {
  local c="$1" w="$2"; shift 2
  LDIR="$B/$c"
  LOUT="$(env SKILL_TESTER_RECEIPTS="$B/receipts" bash "$LSELF" --rung 2 --fake --scratch "$LDIR" "$@" 2>&1)"; LRC=$?
  printf '%s\n' "$LOUT" >> "$B/$c.log"
  LLAST="$(printf '%s\n' "$LOUT" | tail -1)"
  LLD="$(ls -dt "$LDIR"/ladder/L2-* 2>/dev/null | head -1)"
  chk "$c: exit $w (got $LRC) · last: $LLAST" [ "$LRC" = "$w" ]
}
# crafted runs for the judge
st_craft() {
  local D="$1" n
  mkdir -p "$D/run"
  printf 'RUN_ID=x\nSEAM_GUARD=on\n' > "$D/run/meta.env"; : > "$D/run/events.log"
  { for n in 1 2 3 4 5 6 7 8 9 10 11 12; do echo "s$n ok"; done; echo "$CLEAN_TOTAL"; } > "$D/truth.out"
}
st_judge() {  # the judge on crafted runs; returns the number of failures
  local B2="$1" f=0 got C
  C="$B2/j"
  jj() {  # jj <label> <want-regex> [rrc] [trc] [mode]
    got="$(judge "$C/run" "$C/truth.out" "${4:-0}" "${3:-0}" "${5:-real}")"
    if printf '%s' "$got" | grep -qE -- "$2"; then echo "  ok   judge $1 -> $(printf '%s' "$got" | cut -f1,2)"
    else echo "  FAIL judge $1 -> '$got' want /$2/"; f=$((f+1)); fi
  }
  st_craft "$C"; jj clean '^ok	-	ambient=0 ruled=0$'
  st_craft "$C"; sed -i '' 's/^TOTAL ok=12 /TOTAL ok=11 /; s/stuck=0/stuck=1/' "$C/truth.out"; jj truth-ok11 '^fail	truth TOTAL ok=11 '
  st_craft "$C"; jj run-rc1 '^fail	run rc=1	' 1
  st_craft "$C"; jj truth-rc1 '^fail	truth rc=1	' 0 1
  st_craft "$C"; printf 'SEAM-LEAK CHANGED /s/x\n' >> "$C/run/events.log"; jj seam-leak-rc0 '^fail	seam 1 \(SEAM-LEAK CHANGED /s/x\)	'
  st_craft "$C"; printf 'SEAM-DENIED /s/y\n' >> "$C/run/events.log"; jj seam-denied '^fail	seam 1 \(SEAM-DENIED /s/y\)	'
  st_craft "$C"; printf 'SEAM-CANNOT-READ denials\n' >> "$C/run/events.log"; jj seam-cannot-read '^fail	seam 1 \(SEAM-CANNOT-READ denials\)	'
  st_craft "$C"; printf 'SEAM-AMBIENT CHANGED /n/z\n' >> "$C/run/events.log"; jj ambient-allowed '^ok	-	ambient=1 ruled=0$'
  st_craft "$C"; printf 'SEAM-DENIED-RULED /private/tmp/cc-socks/1.sock\n' >> "$C/run/events.log"; jj ruled-allowed '^ok	-	ambient=0 ruled=1$'   # allow-silence: selftest fixture line naming a ruled-denied path; nothing is written there
  st_craft "$C"; printf 'BUDGET-REFUSED s2\n' >> "$C/run/events.log"; jj budget-named '^fail	BUDGET-REFUSED s2 \(exit 75, a named failure\)' 75
  st_craft "$C"; jj rc75-no-event '^fail	run rc=75 with no BUDGET-REFUSED line' 75
  st_craft "$C"; printf 'RIG-TEST ON\n' > "$C/run/events.log"; jj rigtest-real-refused '^fail	test-path run refused \(RIG-TEST ON\)	'
  st_craft "$C"; printf 'RIG-TEST ON\n' > "$C/run/events.log"; jj rigtest-fake-allowed '^ok	-	' 0 0 fake
  st_craft "$C"; echo "FLAG second-copy step-5.json.bak" >> "$C/truth.out"; jj truth-flag '^fail	truth FLAG second-copy step-5.json.bak	'
  st_craft "$C"; printf 'RUN_ID=x\nSEAM_GUARD=off:sandbox-unavailable\n' > "$C/run/meta.env"; jj guard-off '^fail	guard not on \(SEAM_GUARD=off:sandbox-unavailable\)	'
  st_craft "$C"; printf 'CHECK-FAIL s5 facts\n' >> "$C/run/events.log"; jj other-event '^fail	events 1 \(CHECK-FAIL s5 facts\)	'
  st_craft "$C"; jj not-launched '^fail	run not launched	' -
  return $f
}
JUDGE_CASES=17

selftest() {
  local stmp RR0 RR1 C R i rows
  B="$CANON/selftest/ladder-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  mkdir -p "$B/receipts" || { echo "SELFTEST ladder FAILED: cannot create $B"; exit 1; }
  LSELF="$SELF"
  RR0="$(ls -l "$HOME/lifehack-scratch/skill-tester-rig-receipts/rung2.receipt" 2>&1)"
  echo "SELFTEST ladder (FAKE model only; base $B)"

  echo "-- judge on crafted runs (each rule seen failing)"
  st_judge "$B"; i=$?; SN=$((SN+JUDGE_CASES)); SF=$((SF+i))

  echo "-- fail-first: broken copies of the judge must fail the crafted cases"
  ffj() {  # ffj <label> <sed-expr>
    C="$B/ffj-$1"; mkdir -p "$C"; cp -p "$SELF" "$RIG/wait.lib.sh" "$C/"
    sed -i '' "$2" "$C/ladder.sh"
    if cmp -s "$SELF" "$C/ladder.sh"; then chk "ffj $1: the break applied" false; return; fi
    if bash "$C/ladder.sh" --selftest-judge "$C/run" > "$C/judge.log" 2>&1; then chk "ffj $1: the broken judge FAILED a crafted case" false
    else chk "ffj $1: the broken judge FAILED a crafted case ($(grep -m1 'FAIL judge' "$C/judge.log" | cut -c1-90))" true; fi
  }
  ffj seam-ignored 's/^if seam: bad.append/if False: bad.append/'
  ffj total-not-exact 's/^if clean not in tl: bad.append/if False: bad.append/'
  ffj budget-unnamed 's/^if budget: bad.insert/if False: bad.insert/'
  ffj rigtest-accepted 's/^if rigtest and mode == "real": bad.append/if False: bad.append/'

  echo "-- plan and refusals (dry-run: launches nothing, writes nothing)"
  local CLEANENV=( env -u SKILL_TESTER_SCRATCH -u SKILL_TESTER_RECEIPTS -u SKILL_TESTER_RECEIPT_RIG -u CLAUDE_BIN -u RIG_TEST
                   -u SKILL_TESTER_RIG -u CHECKS_DIR -u SEAM_STATE_ROOT -u RIG_TEST_SEAM_WRITE -u SEAM_GUARD_DISABLE -u RIG_GUARD_TAG
                   -u RIG_NUDGE -u RIG_RUN_DIR -u SEAM_SKILL_ROOTS -u SEAM_HOOKS_JSON )
  local m t
  for m in sonnet:medium haiku:small opus:large small:small medium:medium large:large; do
    LOUT="$("${CLEANENV[@]}" bash "$SELF" --rung 2 --n 3 --model "${m%%:*}" --dry-run 2>&1)"; LRC=$?
    t="${m#*:}"
    chk "dry-run --model ${m%%:*} -> --model-tier $t on 3 real runs with s4/s9 answered" \
      [ "$LRC" = 0 ] && [ "$(printf '%s\n' "$LOUT" | grep -c -- "/run.sh --real --model-tier $t --run-id l2-r[123]-[^ ]* --rung rung2 --answer s4=yes --answer s9=yes\$")" = 3 ]
  done
  LOUT="$("${CLEANENV[@]}" bash "$SELF" --rung 2 --model gpt --dry-run 2>&1)"; LRC=$?   # allow-silence: selftest of the refusal of an unknown --model value; no model id
  chk "unknown --model refused (rc 2)" [ "$LRC" = 2 ]   # allow-silence: selftest of the refusal of an unknown --model value; no model id
  LOUT="$("${CLEANENV[@]}" bash "$SELF" --rung 3 --dry-run 2>&1)"; LRC=$?
  chk "--rung 3 refused (rc 2)" [ "$LRC" = 2 ]
  LOUT="$("${CLEANENV[@]}" bash "$SELF" --rung 2 --test-fault 1:ok11 --dry-run 2>&1)"; LRC=$?
  chk "--test-fault without --fake refused (rc 2)" [ "$LRC" = 2 ]
  # real-mode env refusals; backstops: PATH holds no claude, SKILL_TESTER_RECEIPTS/SCRATCH point into this base, and
  # --dry-run would stop before any launch even if a refusal broke
  for v in CLAUDE_BIN RIG_TEST SEAM_STATE_ROOT SKILL_TESTER_RECEIPTS SKILL_TESTER_SCRATCH; do
    LOUT="$("${CLEANENV[@]}" PATH=/usr/bin:/bin:/usr/sbin:/sbin SKILL_TESTER_RECEIPTS="$B/receipts-refusal" \
           SKILL_TESTER_SCRATCH="$B/not-canonical" "$v=$B/refusal-not-a-binary" bash "$SELF" --rung 2 --n 1 --dry-run 2>&1)"; LRC=$?
    chk "real mode refuses $v (rc 2)" [ "$LRC" = 2 ] && has_re "REFUSED: $v is set"
  done

  echo "-- end to end: fake ladders through the real run.sh, the real guard, xargs -P 3"
  st_lad clean 0 --n 3
  chk "clean: last line exactly 'LADDER rung2 ok 3/3 cost \$0.0000'" [ "$LLAST" = 'LADDER rung2 ok 3/3 cost $0.0000' ]
  chk "clean: the card's Verify on the test results prints 3/3" [ "$(card_verify "$LDIR/ladder-results.tsv")" = 3/3 ]
  chk "clean: every row carries the exact clean TOTAL line" [ "$(awk -F'\t' -v t="$CLEAN_TOTAL" '$1=="rung2" && $4==t' "$LDIR/ladder-results.tsv" | wc -l | tr -d ' ')" = 3 ]
  chk "clean: parallelism proven (max overlap 3/3, s2 handshake met)" has_line "PARALLEL max-overlap 3/3 (start/end stamps, s2 handshake met)"
  chk "clean: no NEAR-MISS line" no_re '^NEAR-MISS'
  chk "clean: cost.tsv has 24 ai-step rows (8 x 3), each cost 0.000000 turns 1" \
    [ "$(awk -F'\t' 'NR>1 && $3=="0.000000" && $4=="1"' "$LLD/cost.tsv" | wc -l | tr -d ' ')" = 24 ]
  chk "clean: STATUS.md written in the test scratch" [ -s "$LDIR/STATUS.md" ]
  rows=0
  for R in $(awk -F'\t' '$1=="rung2"{print $3}' "$LDIR/ladder-results.tsv"); do
    head -1 "$(python3 -I "$RIG/run_helper.py" rundir "$LDIR" "$R")/events.log" | grep -qx 'RIG-TEST ON' && rows=$((rows+1))
  done
  chk "clean: every fake run is marked a test path (events.log starts RIG-TEST ON)" [ "$rows" = 3 ]
  R="$(row_field "$LDIR/ladder-results.tsv" 1 3)"
  chk "clean: run ledgers opened inside this ladder's ledger (cap \$50)" \
    grep -qx "ladder	${LLD##*/}" "$LDIR/budget/$R.tsv" && grep -qx 'cap_usd	50' "$LDIR/budget/ladder-${LLD##*/}.tsv"
  chk "clean: no receipt written by a fake ladder" [ ! -e "$B/receipts/rung2.receipt" ]

  st_lad clean 0 --n 3
  chk "re-run: still 3/3 (no double counting)" [ "$(card_verify "$LDIR/ladder-results.tsv")" = 3/3 ]
  chk "re-run: the previous results file was KEPT as a stamped copy with its 3 ok rows" \
    [ "$(okrows "$(ls "$LDIR"/ladder-results.tsv.prev-* 2>/dev/null | head -1)")" = 3 ]

  st_lad ok11 1 --n 3 --test-fault 2:ok11
  chk "ok11: run 2 is a fail row with TOTAL ok=11" [ "$(row_field "$LDIR/ladder-results.tsv" 2 2)" = fail ]
  chk "ok11: ...whose TOTAL field starts 'TOTAL ok=11 '" has_re "^RUN 2 l2-r2-[^ ]* fail rc=0 TOTAL ok=11 "
  chk "ok11: Verify 2/3" [ "$(card_verify "$LDIR/ladder-results.tsv")" = 2/3 ]
  chk "ok11: NEAR-MISS line exactly" has_line "NEAR-MISS 2/3: run --n 5 before deciding"
  chk "ok11: last line 'LADDER rung2 ok 2/3 cost \$0.0000'" [ "$LLAST" = 'LADDER rung2 ok 2/3 cost $0.0000' ]

  st_lad seam-budget 1 --n 3 --test-fault 1:seam --test-fault 3:budget
  chk "seam: run 1 fails on the seam (SEAM-DENIED named)" [ "$(row_field "$LDIR/ladder-results.tsv" 1 2)" = fail ] && \
    row_field "$LDIR/ladder-results.tsv" 1 7 | grep -q 'seam [0-9]* (SEAM-DENIED '
  R="$(row_field "$LDIR/ladder-results.tsv" 1 3)"
  chk "seam: the planted write did not land (the guard refused it)" [ ! -e "$HOME/lifehack-scratch/skill-tester-rig-fake-real/$R/state/rig-leak-$R.md" ]
  chk "budget: run 3 fails, named BUDGET-REFUSED s2 (exit 75)" [ "$(row_field "$LDIR/ladder-results.tsv" 3 2)" = fail ] && \
    row_field "$LDIR/ladder-results.tsv" 3 7 | grep -q '^BUDGET-REFUSED s2 (exit 75, a named failure)'
  chk "budget: a 'BUDGET-REFUSED <run>' line is printed" has_re '^BUDGET-REFUSED l2-r3-[^ ]*: BUDGET-REFUSED s2$'
  chk "seam+budget: run 2 still ok, Verify 1/3, last line ok 1/3" [ "$(card_verify "$LDIR/ladder-results.tsv")" = 1/3 ] && \
    [ "$LLAST" = 'LADDER rung2 ok 1/3 cost $0.0000' ]

  echo "-- fail-first on broken COPIES of the rig"
  C="$B/rig-ff-par"; mkdir -p "$C"; cp -Rp "$RIG/." "$C/"
  sed -i '' 's/xargs -P 3 -L 1 bash/xargs -P 1 -L 1 bash/' "$C/ladder.sh"
  if cmp -s "$SELF" "$C/ladder.sh"; then chk "ff-parallel: the break applied" false
  else
    LSELF="$C/ladder.sh"; export _LAD_PAR_WAIT=6
    st_lad ff-par 1 --n 3
    unset _LAD_PAR_WAIT; LSELF="$SELF"
    chk "ff-parallel (xargs -P 1): the handshake FAILS by WAIT-TIMEOUT" has_line "WAIT-TIMEOUT ladder: 3 runs started"
    chk "ff-parallel: stamps show max overlap 1/3" has_re '^PARALLEL max-overlap 1/3 '
    chk "ff-parallel: every row fails parallel-unproven, last line ok 0/3" [ "$LLAST" = 'LADDER rung2 ok 0/3 cost $0.0000' ] && \
      [ "$(awk -F'\t' '$1=="rung2" && $2=="fail" && $7 ~ /^parallel-unproven max-overlap 1\/3/' "$LDIR/ladder-results.tsv" | wc -l | tr -d ' ')" = 3 ]
  fi
  C="$B/rig-ff-rot"; mkdir -p "$C"; cp -Rp "$RIG/." "$C/"
  sed -i '' -e 's/^  if \[ -e "\$RES" \]; then mv .*$/  : rotation disabled/' \
            -e 's/ > "\$RES"   # fresh$/ >> "$RES"   # appends/' "$C/ladder.sh"
  if [ "$(grep -c '^  : rotation disabled$' "$C/ladder.sh")" != 1 ] || [ "$(grep -cE '^  printf .# rung.* >> "\$RES"   # appends$' "$C/ladder.sh")" != 1 ]; then
    chk "ff-recount: the break applied" false
  else
    LSELF="$C/ladder.sh"
    st_lad ff-rot 0 --n 1
    st_lad ff-rot 0 --n 1
    LSELF="$SELF"
    chk "ff-recount (append, no rotation): the broken copy DOUBLE-COUNTS (2 ok rows for a 1-run ladder)" [ "$(okrows "$LDIR/ladder-results.tsv")" = 2 ]
  fi

  RR1="$(ls -l "$HOME/lifehack-scratch/skill-tester-rig-receipts/rung2.receipt" 2>&1)"
  chk "the real rung2 receipt is untouched by the selftest" [ "$RR0" = "$RR1" ]
  echo "selftest base: $B"
  if [ "$SF" = 0 ]; then echo "SELFTEST ladder $SN/$SN ALL OK"; exit 0; fi
  echo "SELFTEST ladder FAILED $SF/$SN"; exit 1
}

case "${1:-}" in
  --one) shift; one "$@"; exit $? ;;
  --selftest) selftest ;;
  --selftest-judge) [ -n "${2:-}" ] || exit 2; mkdir -p "$2"; st_judge "$2"; exit $? ;;
  --rung) ladder "$@"; exit $? ;;
  *) echo "usage: ladder.sh --rung 2 [--n N] [--model small|medium|large|haiku|sonnet|opus] [--dry-run] | --rung 2 --fake [...] | --selftest" >&2; exit 2 ;;   # allow-silence: usage text listing tiers and family aliases, no model id
esac
