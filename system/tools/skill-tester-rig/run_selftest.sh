#!/bin/bash
# run_selftest.sh RUNSH — the scenarios behind `run.sh --selftest` (TR1.4). FAKE MODEL ONLY: every run passes
# --fake; nothing here can launch a real claude (run.sh refuses without --fake/--real, and --real is never passed).
# Graded by code: events.log lines (exact whole-line match), record.tsv rows, exit codes, truth.py output.
# Writes only $HOME/lifehack-scratch/skill-tester-rig/selftest-run/<stamp> (kept for inspection on failure,
# removed on success). The seam roots point at a small fake tree there (seam.sh's own env), so the real-state
# seam is not exercised here; seam.sh has its own selftest. Last line 'SELFTEST run OK' or 'SELFTEST run FAILED: ...'.
# There is no flag that skips a scenario.

RUNSH="${1:?usage: run_selftest.sh /path/to/run.sh}"
RIG="${SKILL_TESTER_RIG:-$(cd "$(dirname "$0")" && pwd)}"
export SKILL_TESTER_RIG="$RIG"
BASE="$HOME/lifehack-scratch/skill-tester-rig/selftest-run/$(date -u +%Y%m%dT%H%M%SZ)-$$"
export SKILL_TESTER_SCRATCH="$BASE"
export SEAM_STATE_ROOT="$BASE/fake-state" SEAM_SKILL_ROOTS="$BASE/fake-skills" SEAM_HOOKS_JSON="$BASE/fake-hooks.json"
# CONTRACT §3b: this selftest's OWN stand-in, inside the denied tree; no sentinel of any bite ever writes it
export SEAM_STANDIN="$HOME/lifehack-scratch/skill-tester-rig/notes-standin/selftest-run-$(basename "$BASE")"
mkdir -p "$SEAM_STATE_ROOT" "$SEAM_SKILL_ROOTS" || { echo "SELFTEST run FAILED: cannot create $BASE"; exit 1; }
echo state > "$SEAM_STATE_ROOT/a.md"
unset CANARY_SEED SKILL_TESTER_SEED FAKE_MODE FAKE_MODE_STEP FAKE_DELAY FAKE_DELAY_STEP FAKE_WAIT_FILE FAKE_WAIT_STEP FAKE_WAIT_SECS FAKE_MODEL_ID STRESS_TODAY \
      RIG_WATCHDOG_SECS RIG_HOLD_BEFORE_RECORD RIG_RUN_DIR RIG_TEST CHECKS_DIR
ANS="--answer s4=yes --answer s9=yes"
FAILS=""
LOG="$BASE/selftest.log"

ok()   { echo "  ok   $1"; }
bad()  { echo "  FAIL $1${2:+: $2}"; FAILS="$FAILS $1"; }
run()  { bash "$RUNSH" "$@" >>"$LOG" 2>&1; RC=$?; }         # sets RC
rd()   { echo "$BASE/runs/$1"; }
has_ev()  { grep -qxF -- "$2" "$(rd "$1")/events.log" 2>/dev/null; }
no_fail_ev() { ! grep -qE '^(CHECK-FAIL|CANNOT-READ|WATCHDOG|MODEL-FAIL|RECORD-|PATH-REFUSED|BUDGET-REFUSED|SEAM-)' "$(rd "$1")/events.log" 2>/dev/null; }
total()   { python3 "$RIG/truth.py" --run "$1" 2>/dev/null | tail -1; }
tline()   { python3 "$RIG/truth.py" --run "$1" 2>/dev/null | grep -x "$2" >/dev/null; }
T12="TOTAL ok=12 silent_wrong=0 double_ran=0 stuck=0 lost=0 skipped=0 out_of_order=0 false_done=0"
rows()    { awk -F'\t' -v s="$2" '$3==s{n++} END{print n+0}' "$(rd "$1")/record.tsv" 2>/dev/null; }
nrows()   { [ -f "$(rd "$1")/record.tsv" ] && wc -l < "$(rd "$1")/record.tsv" | tr -d ' ' || echo 0; }
scan()    { python3 -I "$RIG/run_helper.py" scan "$(rd "$1")/record.tsv" "$1"; }
expect()  { # name cond...
  local name="$1"; shift
  if "$@"; then ok "$name"; else bad "$name" "$*"; fi
}
eq() { [ "$1" = "$2" ]; }
. "$RIG/wait.lib.sh" || { echo "SELFTEST run FAILED: wait.lib.sh missing"; exit 1; }

echo "selftest: scratch $BASE (fake model only)"

echo "== refusals"
run --run-id ref1 --card canary $ANS
expect "no --fake/--real -> exit 2" eq "$RC" 2
expect "no --fake/--real -> nothing created" eval "[ ! -e '$BASE/runs/ref1' ]"
run --fake nonsense --run-id ref2;           expect "unknown fake mode -> 2" eq "$RC" 2
run --fake good --real --run-id ref3;        expect "--fake + --real -> 2" eq "$RC" 2
run --fake good --run-id ../x;               expect "bad run-id -> 2" eq "$RC" 2
run --fake good --run-id sk1 --test-skip-step 5 $ANS
expect "--test-skip-step without RIG_TEST=1 -> 2" eq "$RC" 2
expect "--test-skip-step refused -> nothing created" eval "[ ! -e '$BASE/runs/sk1' ]"
run --fake good --run-id ea1 --test-exit-after 6 $ANS
expect "--test-exit-after without RIG_TEST=1 -> 2" eq "$RC" 2
expect "--test-exit-after refused -> nothing created" eval "[ ! -e '$BASE/runs/ea1' ]"
RIG_TEST=1 run --fake good --run-id ea2 --test-exit-after 12 $ANS
expect "--test-exit-after 12 (out of 0..11) -> 2" eq "$RC" 2
out="$(bash "$RUNSH" --print-real-cmd 2>&1)"
mid="$(python3 -I -B -c 'import sys; sys.path.insert(0, sys.argv[1]); from model_ids import model_id; print(model_id("medium"))' "${LIFEHACK_V2:-$HOME/lifehack-v2}/shared/tools")"
expect "real cmd: -p --output-format json --allowedTools Read --permission-mode bypassPermissions --settings lab-settings" \
  eval 'printf "%s\n" "$out" | tr "\n" " " | grep -q -- "-u CANARY_SEED -u SKILL_TESTER_SEED claude -p <rendered prompt> --output-format json --model $mid --allowedTools Read --permission-mode bypassPermissions --settings <scratch>/settings/<run-id>.lab-settings.json"'
expect "real cmd: never --dangerously-skip-permissions" eval '! printf "%s" "$out" | grep -q dangerously'
expect "lab-settings: deny AskUserQuestion + Read on seeds/plans/rig" python3 -I -B -c '
import json, sys
d = json.load(open(sys.argv[1]))["permissions"]["deny"]
need = ["AskUserQuestion", "Read(~/lifehack-scratch/skill-tester-rig/seeds/**)", "Read(~/lifehack-scratch/skill-tester-rig/plans/**)",
        "Read(~/lifehack-v2/system/tools/skill-tester-rig/**)", "Bash", "Edit", "Write"]
sys.exit(0 if all(n in d for n in need) else 1)' "$RIG/lab-settings.template.json"
expect "lab-settings: no committed rendered copy beside the template" eval "[ ! -e '$RIG/lab-settings.json' ]"
python3 -I -B "$RIG/run_helper.py" render-settings "$RIG/lab-settings.template.json" "$BASE/lab-settings.rendered.json" "$BASE" "$RIG"; r=$?
expect "lab-settings: rendered deny list carries the absolute //<scratch>/seeds|plans and //<rig> forms" python3 -I -B -c '
import json, os, sys
d = json.load(open(sys.argv[1]))["permissions"]["deny"]
b, rig = os.path.realpath(sys.argv[2]), os.path.realpath(sys.argv[3])
need = ["Read(/%s/seeds/**)" % b, "Read(/%s/plans/**)" % b, "Read(/%s/**)" % rig]
sys.exit(0 if all(n in d for n in need) and not any("{{" in x for x in d) else 1)' "$BASE/lab-settings.rendered.json" "$BASE" "$RIG"
expect "lab-settings: render refuses a non-absolute scratch (exit 2)" eval "python3 -I -B '$RIG/run_helper.py' render-settings '$RIG/lab-settings.template.json' '$BASE/x.json' rel '$RIG' 2>/dev/null; [ \$? = 2 ] && [ ! -e '$BASE/x.json' ]"
CANARY_SEED=1 bash "$RIG/fake-claude.sh" -p "x" >/dev/null 2>&1; r=$?
expect "fake asserts CANARY_SEED unset (rc 3 when present)" eq "$r" 3
bash "$RIG/fake-claude.sh" -p "x" --dangerously-skip-permissions >/dev/null 2>&1; r=$?
expect "fake refuses --dangerously-skip-permissions" eq "$r" 2
printf '{"type":"result","is_error":false}\n' > "$BASE/noresult.json"
python3 -I "$RIG/run_helper.py" result "$BASE/noresult.json" "$BASE/x.out" m >/dev/null; r=$?
expect "missing JSON result -> helper exit 5 (runner: MODEL-FAIL)" eq "$r" 5

echo "== good full run, answers pre-supplied, one invocation"
run --fake good --run-id g1 --card canary $ANS
expect "g1 exit 0" eq "$RC" 0
expect "g1 truth TOTAL ok=12" eq "$(total g1)" "$T12"
expect "g1 12 done rows" eq "$(rows g1 done)" 12
expect "g1 every row valid (rowsum)" eq "$(scan g1)" ""
expect "g1 no failure events" no_fail_ev g1
expect "g1 seed outside RUN_DIR, not in meta.env" eval "[ -s '$BASE/seeds/g1' ] && ! grep -qi seed '$(rd g1)/meta.env' && [ -z \"\$(ls '$(rd g1)' | grep -i seed)\" ]"
expect "g1 no stray step-file copies" eval "! python3 '$RIG/truth.py' --run g1 | grep -q '^FLAG'"
echo "== re-run of a finished run: all skipped-done"
run --fake good --run-id g1 --card canary $ANS
expect "g1 resume exit 0" eq "$RC" 0
expect "g1 resume 12 skipped-done rows" eq "$(rows g1 skipped-done)" 12
expect "g1 resume still TOTAL ok=12" eq "$(total g1)" "$T12"
expect "g1 resume: no RERUN" eval "! grep -q '^RERUN' '$(rd g1)/events.log'"

echo "== human pause (exit 70) then resume"
run --fake good --run-id h1
expect "h1 pauses: exit 70" eq "$RC" 70
expect "h1 WAITING s4" has_ev h1 "WAITING s4"
expect "h1 waiting row" eq "$(rows h1 waiting)" 1
expect "h1 no step-4.json while waiting" eval "[ ! -e '$(rd h1)/step-4.json' ]"
run --fake good --run-id h1 --answer s4=yes
expect "h1 second pause at s9: exit 70" eq "$RC" 70
expect "h1 RESUME s4 gap_days=0" has_ev h1 "RESUME s4 gap_days=0"
expect "h1 WAITING s9" has_ev h1 "WAITING s9"
run --fake good --run-id h1 --answer s9=yes
expect "h1 completes: exit 0" eq "$RC" 0
expect "h1 TOTAL ok=12" eq "$(total h1)" "$T12"
run --fake good --run-id h2 --answer s4=no
expect "h2 human no: exit 0 (legitimate halt)" eq "$RC" 0
expect "h2 halted row" eq "$(rows h2 halted)" 1
expect "h2 step-4 says no, no step-5" eval "grep -q '\"answer\":\"no\"' '$(rd h2)/step-4.json' && [ ! -e '$(rd h2)/step-5.json' ]"
expect "h2 truth ok=4" eq "$(total h2)" "TOTAL ok=4 silent_wrong=0 double_ran=0 stuck=0 lost=0 skipped=0 out_of_order=0 false_done=0"
run --fake good --run-id h2 --answer s4=yes --answer s9=yes
expect "h2 resume stays halted (exit 0, no step-5)" eval "[ $RC = 0 ] && [ ! -e '$(rd h2)/step-5.json' ]"
run --fake good --run-id h3 --answer s4=maybe
expect "h3 off-menu: exit 1 + CHECK-FAIL s4 answer" eval "[ $RC = 1 ] && has_ev h3 'CHECK-FAIL s4 answer'"

echo "== each fake mode at FAKE_MODE_STEP=5"
for spec in "empty:1:CHECK-FAIL s5 empty" "almost:1:CHECK-FAIL s5 token" "garbage:1:CHECK-FAIL s5 parse" \
            "lossy:1:CHECK-FAIL s5 facts" "hang:124:WATCHDOG s5" "exit127:1:MODEL-FAIL s5 rc=127"; do
  m="${spec%%:*}"; rest="${spec#*:}"; want="${rest%%:*}"; line="${rest#*:}"
  RIG_WATCHDOG_SECS=3 FAKE_MODE_STEP=5 run --fake "$m" --run-id "m-$m" $ANS
  expect "$m: exit $want + '$line'" eval "[ $RC = $want ] && has_ev m-$m '$line'"
  expect "$m: s5 stuck, nothing committed, no s5 row" eval "tline m-$m 's5 stuck' && [ ! -e '$(rd m-$m)/step-5.json' ] && ! awk -F'\t' '\$2==\"s5\"{f=1} END{exit !f}' '$(rd m-$m)/record.tsv'"
done

echo "== record tampering refused on resume (F-08, F-M1, foreign)"
run --fake good --run-id t1 $ANS
python3 -I - "$(rd t1)/record.tsv" <<'PY'
import sys
p = sys.argv[1]; L = open(p).read().split("\n")
f = L[4].split("\t"); L[4] = "\t".join(f[:3]) + "\t" + f[3][:4]          # s5 row: 3 fields + partial 4th, newline kept
open(p, "w").write("\n".join(L))
PY
run --fake good --run-id t1 $ANS
expect "t1 truncated row: RECORD-REFUSED s5 row=5" has_ev t1 "RECORD-REFUSED s5 row=5"
expect "t1 RERUN s5, exit 0" eval "[ $RC = 0 ] && has_ev t1 'RERUN s5'"
expect "t1 TOTAL ok=12 after refusal" eq "$(total t1)" "$T12"
n="$(nrows t1)"
printf 't1\ts6\tdone\t1\tdeadbeef\tmodel\t000000000000\n' >> "$(rd t1)/record.tsv"        # model-written row (forged rowsum)
printf 'other-run\ts6\tdone\t1\tdeadbeef\tmodel\t000000000000\n' >> "$(rd t1)/record.tsv"
run --fake good --run-id t1 $ANS
expect "t1 model-written row: RECORD-REFUSED s6 row=$((n+1))" has_ev t1 "RECORD-REFUSED s6 row=$((n+1))"
expect "t1 foreign row: RECORD-FOREIGN row=$((n+2))" has_ev t1 "RECORD-FOREIGN row=$((n+2))"
expect "t1 still TOTAL ok=12" eq "$(total t1)" "$T12"

echo "== seed never reaches the actor"
CANARY_SEED=12345 SKILL_TESTER_SEED=678 run --fake good --run-id e1 $ANS
expect "e1 caller exports the seed vars: run still exit 0, ok=12 (fake exits 3 on a leak)" eval "[ $RC = 0 ] && [ \"\$(total e1)\" = '$T12' ]"

echo "== kill after the side effect, before the record row (F-07)"
# TR1.8 HANDSHAKE, no clock: run.sh writes hold-s7.held once step-7.json is committed and BEFORE the s7 row; we kill
# on that marker. The hold's 60 s is only its deadline: a kill that missed it leaves hold-s7.expired (a FAIL by name).
# Fail-first (selftest-all.sh --waits): a rig COPY whose run.sh never writes the marker must FAIL here with
# WAIT-TIMEOUT (RIG_K1_WAIT_SECS only shortens that deadline; it can make k1 fail, never pass).
RIG_HOLD_BEFORE_RECORD=7:60 bash "$RUNSH" --fake good --run-id k1 $ANS >>"$LOG" 2>&1 &
kp=$!
k1held() { [ -f "$(rd k1)/hold-s7.held" ] && [ -f "$(rd k1)/step-7.json" ] && grep -q $'\ts7\tbegin' "$(rd k1)/exec.log" 2>/dev/null; }
K1W="WAIT-TIMEOUT k1 hold-s7.held"
if wait_until "${RIG_K1_WAIT_SECS:-30}" "k1 hold-s7.held" k1held 2>>"$LOG"; then ok "k1 handshake: hold-s7.held seen before the kill"
else echo "$K1W"; bad "k1 handshake" "$K1W"; fi
pg="$(ps -o pgid= -p "$kp" | tr -d ' ')"
expect "k1 runner leads its own process group" eq "$pg" "$kp"
kill -KILL -- "-$kp" 2>/dev/null; wait "$kp" 2>/dev/null; krc=$?
expect "k1 runner died by SIGKILL (rc 137, got $krc), not by finishing" eq "$krc" 137
expect "k1 kill landed inside the hold (no hold-s7.expired)" eval "[ ! -e '$(rd k1)/hold-s7.expired' ]"
expect "k1 no valid s7 row after the kill" eval "! python3 -I '$RIG/run_helper.py' last-valid '$(rd k1)/record.tsv' k1 s7 >/dev/null"
run --fake good --run-id k1 $ANS
expect "k1 resume: RERUN s7, exit 0" eval "[ $RC = 0 ] && has_ev k1 'RERUN s7'"
expect "k1 TOTAL ok=12 (no double_ran)" eq "$(total k1)" "$T12"

echo "== live skip (F-14a) and pre-flight"
RIG_TEST=1 run --fake good --run-id sk2 --test-skip-step 5 $ANS
expect "sk2 exit 1 + CHECK-FAIL s6 input-missing" eval "[ $RC = 1 ] && has_ev sk2 'CHECK-FAIL s6 input-missing'"
expect "sk2 no step-5/step-6, no s5 row" eval "[ ! -e '$(rd sk2)/step-5.json' ] && [ ! -e '$(rd sk2)/step-6.json' ] && ! grep -q $'\ts5\t' '$(rd sk2)/record.tsv'"
expect "sk2 truth: s5 skipped" tline sk2 "s5 skipped"
expect "sk2 RIG_TEST run: first event 'RIG-TEST ON', meta.env RIG_TEST=1" eval "[ \"\$(head -1 '$(rd sk2)/events.log')\" = 'RIG-TEST ON' ] && grep -qx 'RIG_TEST=1' '$(rd sk2)/meta.env'"
expect "g1 normal run: no RIG-TEST marker" eval "! grep -q 'RIG-TEST' '$(rd g1)/events.log' && ! grep -q RIG_TEST '$(rd g1)/meta.env'"

echo "== committed file edited after its check (F-06b): resume re-verifies"
run --fake good --run-id f6 $ANS
python3 -I - "$(rd f6)/step-5.json" <<'PY'
import json, sys
p = sys.argv[1]; r = json.load(open(p)); k, v = r["facts"][0].split("="); v = int(v); r["facts"][0] = "%s=%d" % (k, v + 1 if v < 999 else v - 1)
open(p, "w").write(json.dumps(r, separators=(",", ":")) + "\n")
PY
f6cat="$(python3 "$RIG/truth.py" --run f6 2>/dev/null | grep '^s5 ' | cut -d' ' -f2)"
expect "f6 un-resumed: truth s5 lost (got '$f6cat')" eq "$f6cat" lost
run --fake good --run-id f6 $ANS
expect "f6 resume: RERUN s5, exit 0, TOTAL ok=12" eval "[ $RC = 0 ] && has_ev f6 'RERUN s5' && [ \"\$(total f6)\" = '$T12' ]"

echo "== version change across a pause (F-18), clock gap (F-16)"
FAKE_MODEL_ID=fake-model-A run --fake good --run-id v1
FAKE_MODEL_ID=fake-model-B run --fake good --run-id v1 $ANS
expect "v1 VERSION-CHANGE s5 fake-model-A -> fake-model-B, exit 0, ok=12" eval "[ $RC = 0 ] && has_ev v1 'VERSION-CHANGE s5 fake-model-A -> fake-model-B' && [ \"\$(total v1)\" = '$T12' ]"
STRESS_TODAY=2026-01-01 run --fake good --run-id c1
r1=$RC
STRESS_TODAY=2026-01-29 run --fake good --run-id c1 $ANS
expect "c1 pause 70, resume: RESUME s4 gap_days=28, exit 0, ok=12" eval "[ $r1 = 70 ] && [ $RC = 0 ] && has_ev c1 'RESUME s4 gap_days=28' && [ \"\$(total c1)\" = '$T12' ]"

echo "== path guard (F-17)"
RIG_RUN_DIR="/Volumes/GoogleDrive/My Drive/skill-tester-rig/p1" run --fake good --run-id p1 $ANS
expect "p1 exit 1 + PATH-REFUSED in the canonical events.log" eval "[ $RC = 1 ] && has_ev p1 'PATH-REFUSED /Volumes/GoogleDrive/My Drive/skill-tester-rig/p1' && [ ! -e /Volumes/GoogleDrive ]"

echo "== check missing / crashing (F-11, F-12)"
mkdir -p "$BASE/cm" "$BASE/cc"
for k in code human; do printf '#!/bin/bash\nexec bash "%s/checks/%s.sh" "$@"\n' "$RIG" "$k" > "$BASE/cm/$k.sh"; done
CHECKS_DIR="$BASE/cm" run --fake good --run-id x1 $ANS
expect "x1 ai.sh missing: CANNOT-READ s2, exit 1" eval "[ $RC = 1 ] && has_ev x1 'CANNOT-READ s2'"
for k in ai code human; do printf '#!/bin/bash\n[ "$2" = 5 ] && kill -SEGV $$\nexec bash "%s/checks/%s.sh" "$@"\n' "$RIG" "$k" > "$BASE/cc/$k.sh"; done
CHECKS_DIR="$BASE/cc" run --fake good --run-id x2 $ANS
expect "x2 crashing check judged first: SELFTEST-REFUSED ai.sh, exit 1, nothing run" eval "[ $RC = 1 ] && has_ev x2 'SELFTEST-REFUSED ai.sh' && [ ! -e '$(rd x2)/step-1.json' ]"
RIG_TEST=1 CHECKS_DIR="$BASE/cc" run --fake good --run-id x3 $ANS
expect "x3 RIG_TEST=1 runs on: CANNOT-READ s5, exit 1, s5 stuck" eval "[ $RC = 1 ] && has_ev x3 'SELFTEST-REFUSED ai.sh' && has_ev x3 'CANNOT-READ s5' && tline x3 's5 stuck'"
mkdir -p "$BASE/po"; cp "$BASE/cm/code.sh" "$BASE/cm/human.sh" "$BASE/po/"
printf '#!/bin/bash\n[ -s "${3:-$1/step-$2.json}" ]\n' > "$BASE/po/ai.sh"
CHECKS_DIR="$BASE/po" FAKE_MODE_STEP=5 run --fake almost --run-id x4 $ANS
expect "x4 presence-only check (F-13): SELFTEST-REFUSED ai.sh, exit 1" eval "[ $RC = 1 ] && has_ev x4 'SELFTEST-REFUSED ai.sh' && [ ! -e '$(rd x4)/step-1.json' ]"
RIG_TEST=1 CHECKS_DIR="$BASE/po" FAKE_MODE_STEP=5 run --fake almost --run-id x5 $ANS
expect "x5 presence-only + RIG_TEST=1: refused AND oracle s5 silent_wrong" eval "has_ev x5 'SELFTEST-REFUSED ai.sh' && tline x5 's5 silent_wrong'"

echo "== pre-flight judge of the DEFAULT checks (TR1.4 amendment) + its cache"
# Full copies of the rig under $BASE (never inside the rig under test); each copy runs its OWN run.sh and checks/.
rigcopy() { rm -rf "$1"; cp -Rp "$RIG" "$1" && find "$1" -name __pycache__ -prune -exec rm -rf {} + ; }
crun() { local d="$1"; shift; SKILL_TESTER_RIG="$d" bash "$d/run.sh" "$@" >>"$LOG" 2>&1; RC=$?; }
jlog() { cat "$(rd "$1")/judge.log" 2>/dev/null; }
begins() { awk -F'\t' '$3=="begin"{n++} END{print n+0}' "$(rd "$1")/exec.log" 2>/dev/null || echo 0; }
EMITD="${LIFEHACK_V2:-$HOME/lifehack-v2}/shared/emit"
D0="$BASE/rig-ai-exit0"; rigcopy "$D0"
printf '#!/bin/bash\nexit 0\n' > "$D0/checks/ai.sh"                  # a default check that passes everything
crun "$D0" --fake good --run-id d1 $ANS
expect "d1 default ai.sh always exit 0: SELFTEST-REFUSED ai.sh, exit 1" eval "[ $RC = 1 ] && has_ev d1 'SELFTEST-REFUSED ai.sh'"
expect "d1 refused before any step: no exec.log begin, no step-1.json, no record row" \
  eval "[ \"\$(begins d1)\" = 0 ] && [ ! -e '$(rd d1)/step-1.json' ] && [ ! -s '$(rd d1)/record.tsv' ]"
expect "d1 only ai.sh refused (code.sh, human.sh accepted)" eval "! has_ev d1 'SELFTEST-REFUSED code.sh' && ! has_ev d1 'SELFTEST-REFUSED human.sh'"
k0="$(python3 -I -B "$RIG/run_helper.py" judge-key "$D0" "$EMITD" ai "$D0/checks/ai.sh")"
expect "d1 a refusal is never cached (no judge-cache/<key of the broken ai.sh>)" eval "[ -n '$k0' ] && [ ! -e '$BASE/judge-cache/$k0' ]"
RIG_TEST=1 crun "$D0" --fake good --run-id d1t $ANS
expect "d1t RIG_TEST=1 does NOT override a refused DEFAULT check: exit 1, no step begun" \
  eval "[ $RC = 1 ] && has_ev d1t 'SELFTEST-REFUSED ai.sh' && [ \"\$(begins d1t)\" = 0 ]"
D1="$BASE/rig-cache"; rigcopy "$D1"
rm -rf "$BASE/judge-cache"     # earlier runs cached the identical (content-keyed) default checks
crun "$D1" --fake good --run-id d2 $ANS
expect "d2 normal run with the judge: exit 0, TOTAL ok=12, events.log empty" eval "[ $RC = 0 ] && [ \"\$(total d2)\" = '$T12' ] && [ ! -s '$(rd d2)/events.log' ]"
expect "d2 first run: 3 cache MISS + 3 ACCEPTED" eval "[ \"\$(jlog d2 | grep -c '^judge-cache MISS ')\" = 3 ] && [ \"\$(jlog d2 | grep -c ' ACCEPTED ')\" = 3 ]"
crun "$D1" --fake good --run-id d3 $ANS
expect "d3 unchanged files: 3 cache HIT, no judge re-run, exit 0" eval "[ $RC = 0 ] && [ \"\$(jlog d3 | grep -c '^judge-cache HIT ')\" = 3 ] && ! jlog d3 | grep -q ACCEPTED"
kold="$(jlog d3 | awk '$3=="ai.sh"{print $4}')"
printf '\n' >> "$D1/checks/fixtures/ai/good/reordered-keys-pretty.json"    # one byte, still a good fixture
crun "$D1" --fake good --run-id d4 $ANS
knew="$(jlog d4 | awk '$2=="MISS" && $3=="ai.sh"{print $4}')"
expect "d4 one-byte fixture change: cache MISS for all 3, new ai key, judged again, exit 0" \
  eval "[ $RC = 0 ] && [ \"\$(jlog d4 | grep -c '^judge-cache MISS ')\" = 3 ] && [ -n '$knew' ] && [ '$knew' != '$kold' ] && [ \"\$(jlog d4 | grep -c ' ACCEPTED ')\" = 3 ]"

echo "== F-20 silent stop (RIG_TEST=1 --test-exit-after K): exit 0, and ONLY the oracle says so"
RIG_TEST=1 run --fake good --run-id f20a --test-exit-after 6 $ANS
expect "f20a K=6: exit 0, 6 done rows, RIG-TEST ON" eval "[ $RC = 0 ] && [ \"\$(rows f20a done)\" = 6 ] && has_ev f20a 'RIG-TEST ON'"
expect "f20a K=6: truth names s7 stuck, rc 1" eval "tline f20a 's7 stuck' && ! python3 '$RIG/truth.py' --run f20a >/dev/null 2>&1"
RIG_TEST=1 run --fake good --run-id f20b --test-exit-after 0 $ANS
expect "f20b K=0: exit 0, no record rows, truth names s1 stuck" eval "[ $RC = 0 ] && [ ! -s '$(rd f20b)/record.tsv' ] && tline f20b 's1 stuck'"

echo "== budget refusal"
bash "$RIG/budget.sh" open b1 --calls 1 >/dev/null 2>&1
run --fake good --run-id b1 $ANS
expect "b1 one-call budget: BUDGET-REFUSED s3, exit 75" eval "[ $RC = 75 ] && has_ev b1 'BUDGET-REFUSED s3'"

echo "== seam change during a run (TR1.7: a writer OUTSIDE the guard is AMBIENT when the guard is on, LEAK when off)"
# HANDSHAKE, no clock: the writer waits for THIS run's seam snapshot (seam.sh writes it atomically: .partial, then
# mv), then writes; the fake actor holds step 3 until the written file exists, so the write always lands between
# snapshot and verify. Both waits are bounded (30 s) and fail the case by name, never silently.
seam_snap_exists() { ls "$BASE/seam/$1".*.sha >/dev/null 2>&1; }
seam_writer() {  # seam_writer <run-id> <file to write> <marker>
  if ! wait_until 30 "$1 seam snapshot" seam_snap_exists "$1" 2>>"$LOG"; then echo "WAIT-TIMEOUT $1 seam snapshot" > "$3"; return 1; fi
  echo leak > "$2" && echo WROTE > "$3"
}
rm -f "$BASE"/seam/s1.*.sha "$BASE"/seam/s2.*.sha "$BASE/s1.handshake" "$BASE/s2.handshake"
seam_writer s1 "$SEAM_STATE_ROOT/leak.md" "$BASE/s1.handshake" &
FAKE_WAIT_FILE="$SEAM_STATE_ROOT/leak.md" FAKE_WAIT_STEP=3 run --fake good --run-id s1 $ANS
wait
expect "s1 handshake: writer saw the snapshot, then wrote ($(cat "$BASE/s1.handshake" 2>/dev/null))" grep -qx WROTE "$BASE/s1.handshake"
expect "s1 guard ON: exit 0 + SEAM-AMBIENT ADDED <path>, no SEAM-LEAK" eval "[ $RC = 0 ] && has_ev s1 'SEAM-AMBIENT ADDED $SEAM_STATE_ROOT/leak.md' && ! grep -q '^SEAM-LEAK' '$(rd s1)/events.log' && grep -qx SEAM_GUARD=on '$(rd s1)/meta.env'"
rm -f "$SEAM_STATE_ROOT/leak.md"
seam_writer s2 "$SEAM_STATE_ROOT/leak2.md" "$BASE/s2.handshake" &
SEAM_GUARD_DISABLE=1 FAKE_WAIT_FILE="$SEAM_STATE_ROOT/leak2.md" FAKE_WAIT_STEP=3 run --fake good --run-id s2 $ANS
wait
expect "s2 handshake: writer saw the snapshot, then wrote ($(cat "$BASE/s2.handshake" 2>/dev/null))" grep -qx WROTE "$BASE/s2.handshake"
expect "s2 guard OFF: exit 1 + SEAM-LEAK ADDED <path>, meta SEAM_GUARD=off:disabled-by-env" eval "[ $RC = 1 ] && has_ev s2 'SEAM-LEAK ADDED $SEAM_STATE_ROOT/leak2.md' && grep -qx SEAM_GUARD=off:disabled-by-env '$(rd s2)/meta.env'"
rm -f "$SEAM_STATE_ROOT/leak2.md"
echo "== the rig itself writes seam scope (TR1.7: refused by the guard and named)"
RIG_TEST=1 RIG_TEST_SEAM_WRITE="$SEAM_STATE_ROOT/rig-leak.md" run --fake good --run-id s3 $ANS
expect "s3 exit 1 + SEAM-DENIED <path>, file absent" eval "[ $RC = 1 ] && has_ev s3 'SEAM-DENIED $SEAM_STATE_ROOT/rig-leak.md' && [ ! -e '$SEAM_STATE_ROOT/rig-leak.md' ]"
GUARD_TEST_NO_LOG=1 run --fake good --run-id s4 $ANS
expect "s4 denial log unreadable: exit 1 + SEAM-CANNOT-READ denials" eval "[ $RC = 1 ] && has_ev s4 'SEAM-CANNOT-READ denials'"

if [ -z "$FAILS" ]; then
  rm -rf "$BASE"
  echo "SELFTEST run OK"; exit 0
fi
echo "selftest: kept $BASE for inspection (log: $LOG)"
echo "SELFTEST run FAILED:$FAILS"; exit 1
