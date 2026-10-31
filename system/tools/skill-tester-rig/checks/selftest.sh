#!/bin/bash
# from orchestrator-v2/rig/stress/selftest.sh @ 2026-10-28
#   (the pattern, rewritten for TR1.3: every checker must FAIL on known-bad and PASS on known-good, logged as
#    "<name> bad=<rc> good=<rc>"; here also CANNOT-READ must be distinct, and a presence-only check is refused)
#
# selftest.sh                      judge the three shipped checks, the edge cases, and refuse the F-13 demo check.
#                                  Last line exactly "SELFTEST bad=fail good=pass cannot-read=distinct ALL OK"
#                                  only if everything held; else "SELFTEST FAILED: <names>" and exit 1.
# selftest.sh --judge CHECK KIND   judge ANY check script against fixtures/KIND. Exit 0 = ACCEPTED, 1 = REFUSED.
#                                  This is the same judge the main mode uses; it is how a new or edited check is
#                                  watched failing first (ruling 12). There is no flag that skips any part of it.
#
# The judge, for a check script C and kind K (fixtures/K/case.env gives SEED and STEP):
#   every fixtures/K/bad/*  -> C must exit exactly 1      (4 on a bad fixture = C could not read it = refused)
#   every fixtures/K/good/* -> C must exit exactly 0
#   a missing candidate     -> C must exit 4 AND print a line "CANNOT-READ" (distinct from fail)
#   the fixture set must hold the required bad cases (so deleting fixtures cannot make a weak check pass).
# Writes only a temp folder under ~/lifehack-scratch/skill-tester-rig/selftest/ (removed on exit). bash 3.2.

CHECKS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || exit 1
RIG="$(cd "$CHECKS/.." && pwd)"
FX="$CHECKS/fixtures"
SCRATCH="${SKILL_TESTER_SCRATCH:-$HOME/lifehack-scratch/skill-tester-rig}"
REQUIRED_BAD="empty token-missing token-wrong-step value-wrong fact-dropped fact-reordered fact-edited extra-key fenced-json"
REQUIRED_BAD_HUMAN="answer-no answer-uppercase answer-missing"

mkdir -p "$SCRATCH/selftest" || { echo "SELFTEST FAILED: cannot create $SCRATCH/selftest"; exit 1; }
T="$(mktemp -d "$SCRATCH/selftest/checks.XXXXXX")" || { echo "SELFTEST FAILED: mktemp"; exit 1; }
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/run"

# run_c CHECK SEED N [CANDIDATE] : run a check the way the card does (cwd = rig root); sets RC and OUT
run_c() {
  local c="$1" s="$2"; shift 2
  OUT="$(cd "$RIG" && CANARY_SEED="$s" bash "$c" "$T/run" "$@" 2>&1)"; RC=$?
}
has_cannot_read() { printf '%s\n' "$1" | grep -qx 'CANNOT-READ'; }

# want_cat FIXTURE-NAME : the CONTRACT §3 category the shipped checks must print (`FAIL <cat>: ...`) for that bad
# fixture. Unknown name -> "?" (an unmapped new fixture fails the category assertion until it is mapped here).
want_cat() {
  case "$1" in
    empty|whitespace-only) echo empty ;;
    array-not-object|duplicate-key|fenced-json|prose-wrapped|truncated|two-objects) echo parse ;;
    answer-on-non-human|extra-key|step-missing|answer-missing) echo keys ;;
    step-as-string|step-wrong) echo step ;;
    token-missing|token-truncated|token-wrong-seed|token-wrong-step) echo token ;;
    value-as-string|value-prev-step|value-wrong) echo value ;;
    fact-dropped|fact-edited|fact-extra|fact-reordered) echo facts ;;
    answer-bool|answer-no|answer-padded|answer-uppercase) echo answer ;;
    *) echo "?" ;;
  esac
}

# judge CHECK KIND LABEL [cats] : prints one summary line (+ one line per violation); returns 0 accepted / 1 refused
#   with "cats", every bad fixture must ALSO print first line `FAIL <want_cat>: ...` (the shipped checks; TR1.4
#   copies <cat> into `CHECK-FAIL sN <cat>`). Foreign checks (--judge, presence-only) are judged on exit codes.
judge() {
  local c="$1" k="$2" label="$3" cats="${4:-}" SEED STEP f name nb=0 ng=0 nc=0 v="" req first
  [ -f "$c" ] || { echo "$label REFUSED: no such check $c"; return 1; }
  [ -f "$FX/$k/case.env" ] || { echo "$label REFUSED: no fixtures for kind $k"; return 1; }
  . "$FX/$k/case.env"
  req="$REQUIRED_BAD"; [ "$k" = human ] && req="$req $REQUIRED_BAD_HUMAN"
  for name in $req; do [ -f "$FX/$k/bad/$name.json" ] || v="$v missing-fixture:$name"; done
  for f in "$FX/$k/bad/"*; do
    [ -f "$f" ] || continue; nb=$((nb + 1))
    run_c "$c" "$SEED" "$STEP" "$f"
    [ "$RC" = 1 ] || v="$v bad:$(basename "$f" .json)=rc$RC"
    if [ -n "$cats" ]; then
      first="${OUT%%$'\n'*}"
      case "$first" in
        "FAIL $(want_cat "$(basename "$f" .json)"): "*) nc=$((nc + 1)) ;;
        *) v="$v cat:$(basename "$f" .json)(want $(want_cat "$(basename "$f" .json)"), got '${first%%:*}')" ;;
      esac
    fi
  done
  for f in "$FX/$k/good/"*; do
    [ -f "$f" ] || continue; ng=$((ng + 1))
    run_c "$c" "$SEED" "$STEP" "$f"
    [ "$RC" = 0 ] || v="$v good:$(basename "$f" .json)=rc$RC"
  done
  [ "$nb" -gt 0 ] || v="$v no-bad-fixtures"
  [ "$ng" -gt 0 ] || v="$v no-good-fixtures"
  run_c "$c" "$SEED" "$STEP" "$T/does-not-exist.json"
  if [ "$RC" = 4 ] && has_cannot_read "$OUT"; then :; else v="$v missing-file=rc$RC(want 4+CANNOT-READ)"; fi
  if [ -z "$v" ]; then
    echo "$label ACCEPTED bad=fail($nb/$nb) good=pass($ng/$ng) cannot-read=distinct${cats:+ category=ok($nc/$nb)}"
    return 0
  fi
  echo "$label REFUSED:$v"
  return 1
}

if [ "$1" = "--judge" ]; then
  [ $# -eq 3 ] || { echo "usage: selftest.sh --judge CHECK KIND"; exit 1; }
  judge "$2" "$3" "judge $(basename "$2") [$3]"; exit $?
fi
[ $# -eq 0 ] || { echo "usage: selftest.sh | selftest.sh --judge CHECK KIND"; exit 1; }

FAILS=""
fail() { FAILS="$FAILS $1"; echo "  FAIL $1${2:+: $2}"; }
expect() { # name want-rc [cannot-read] : compare the last run_c
  if [ "$RC" != "$2" ]; then fail "$1" "rc=$RC want $2 ($(printf '%s' "$OUT" | head -1))"; return; fi
  if [ "$3" = cr ] && ! has_cannot_read "$OUT"; then fail "$1" "rc=4 but no CANNOT-READ line"; return; fi
  echo "  ok   $1 rc=$RC"
}

echo "== the shipped checks, judged"
for k in ai code human; do judge "$CHECKS/$k.sh" "$k" "checks/$k.sh" cats || FAILS="$FAILS judge:$k"; done

echo "== F-13: a presence-only check must be REFUSED by the same judge"
PRESENCE_ONLY="$FX/presence-only.sh"   # the deliberately weak check; judge runs it like a real one
for k in ai code human; do
  if judge "$PRESENCE_ONLY" "$k" "presence-only [$k]" >"$T/po.out"; then
    cat "$T/po.out"; fail "f13:$k" "presence-only check was ACCEPTED"
  else
    echo "  ok   presence-only [$k] refused ($(tr ' ' '\n' < "$T/po.out" | grep -c '^bad:') bad fixtures passed it)"
  fi
done

echo "== edge cases on the shipped checks"
. "$FX/ai/case.env"
mkdir -p "$T/run"
cp "$FX/ai/good/canonical.json" "$T/run/step-$STEP.json"
run_c "$CHECKS/ai.sh" "$SEED" "$STEP";                       expect default-path-good 0
cp "$FX/ai/bad/value-wrong.json" "$T/run/step-$STEP.json"
run_c "$CHECKS/ai.sh" "$SEED" "$STEP";                       expect default-path-bad 1
rm -f "$T/run/step-$STEP.json"
run_c "$CHECKS/ai.sh" "$SEED" "$STEP";                       expect default-path-missing 4 cr
run_c "$CHECKS/ai.sh" "$((SEED + 1))" "$STEP" "$FX/ai/good/canonical.json"; expect other-seed-fails 1
run_c "$CHECKS/ai.sh" "abc" "$STEP" "$FX/ai/good/canonical.json";           expect seed-unreadable 4 cr
run_c "$CHECKS/ai.sh" "" "$STEP" "$FX/ai/good/canonical.json";              expect seed-empty 4 cr
mkdir -p "$T/scr/runs/rid" "$T/scr/seeds"; echo "$SEED" > "$T/scr/seeds/rid"
OUT="$(cd "$RIG" && env -u CANARY_SEED SKILL_TESTER_SCRATCH="$T/scr" bash "$CHECKS/ai.sh" "$T/scr/runs/rid" "$STEP" "$FX/ai/good/canonical.json" 2>&1)"; RC=$?
expect seed-from-seeds-file 0
rm -f "$T/scr/seeds/rid"
OUT="$(cd "$RIG" && env -u CANARY_SEED SKILL_TESTER_SCRATCH="$T/scr" bash "$CHECKS/ai.sh" "$T/scr/runs/rid" "$STEP" "$FX/ai/good/canonical.json" 2>&1)"; RC=$?
expect seed-absent 4 cr
run_c "$CHECKS/ai.sh" "$SEED" 4 "$FX/human/good/canonical.json";            expect miswired-ai-on-human-step 4 cr
run_c "$CHECKS/human.sh" "$SEED" "$STEP" "$FX/ai/good/canonical.json";      expect miswired-human-on-ai-step 4 cr
run_c "$CHECKS/code.sh" "$SEED" 2 "$FX/ai/good/canonical.json";             expect miswired-code-on-ai-step 4 cr
run_c "$CHECKS/ai.sh" "$SEED" 13 "$FX/ai/good/canonical.json";              expect step-not-on-card 4 cr
run_c "$CHECKS/ai.sh" "$SEED" "five" "$FX/ai/good/canonical.json";          expect step-not-a-number 4 cr
run_c "$CHECKS/ai.sh" "$SEED" "$STEP" "$T";                                 expect candidate-is-a-directory 4 cr
OUT="$(cd "$RIG" && CANARY_SEED="$SEED" bash "$CHECKS/ai.sh" 2>&1)"; RC=$?;  expect no-arguments 4 cr
CR="$(cd "${LIFEHACK_V2:-$HOME/lifehack-v2}" && python3 -I -B -c 'import sys; sys.path.insert(0,"shared/emit"); import verdicts; print(verdicts.CANNOT_READ)' 2>&1)"
LIB="$(sed -n 's/^_CHECKS_CANNOT_READ=//p' "$CHECKS/_lib.sh")"
if [ "$CR" = 4 ] && [ "$LIB" = 4 ]; then echo "  ok   exit-code-agrees-with-verdicts.py (CANNOT_READ=$CR)"
else fail exit-code-vs-verdicts "verdicts.py=$CR _lib.sh=$LIB"; fi

if [ -z "$FAILS" ]; then
  echo "SELFTEST bad=fail good=pass cannot-read=distinct ALL OK"
  exit 0
fi
echo "SELFTEST FAILED:$FAILS"
exit 1
