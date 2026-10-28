#!/bin/bash
# score.sh - reads $BUILD_TEST_OUT/runs.txt (written by run-all.sh), writes $BUILD_TEST_OUT/toy.log.
T="${BUILD_TEST_OUT:-$HOME/lifehack-scratch/build-skill/toy-runs}"
OUT="$T/toy.log"; : > "$OUT"
cnt() { grep -cx "$2" "$1/invocations.log"; }
while read -r name R; do
  rcl="$(tr '\n' ' ' < "$R/rc.txt")"; rec="$R/record.tsv"; last="$(tail -n 1 "$R/rc.txt")"; exp=""; got=""
  case "$name" in
  clean) exp="done/door3=PASS"
    if [ "$rcl" = "70 0 " ] && grep -q "door3 verdict=PASS" "$rec" 2>/dev/null; then got="done/door3=PASS"; else got="rcs=[$rcl]"; fi ;;
  planted) exp="stopped/ALW-1"
    if [ "$last" = 1 ] && grep -q "ALW-1" "$rec" 2>/dev/null && ! grep -q "build.*done" "$rec"; then got="stopped/ALW-1"; else got="rcs=[$rcl] alw1=$(grep -c ALW-1 "$rec" 2>/dev/null)"; fi ;;
  resume) exp="done/resume-clean"
    probs=""
    [ "$last" = 0 ] || probs="$probs lastrc=$last"
    [ "$(cnt "$R" TC1)" = 1 ] || probs="$probs TC1x$(cnt "$R" TC1)"
    c2="$(cnt "$R" TC2)"; { [ "$c2" -ge 1 ] && [ "$c2" -le 2 ]; } || probs="$probs TC2x$c2"
    [ "$(cnt "$R" TC3)" = 1 ] || probs="$probs TC3x$(cnt "$R" TC3)"
    for c in TC1 TC2 TC3; do n="$(awk -F'\t' -v c=$c '$3==c&&$4=="passed"' "$rec" | wc -l | tr -d ' ')"; [ "$n" = 1 ] || probs="$probs passed-$c=$n"; done
    [ "$(tail -c 1 "$rec" | od -An -c | tr -d ' ')" = '\n' ] || probs="$probs truncated"
    grep -q "door3 verdict=PASS" "$rec" || probs="$probs nodoor3"
    if [ -z "$probs" ]; then got="done/resume-clean"; else got="problems:$probs"; fi ;;
  checkpoint-no) exp="stopped/refused"
    if [ "$rcl" = "70 70 1 " ] && awk -F'\t' '$3=="TD2"&&$4=="refused"' "$rec" | grep -q . && ! grep -qx TD3 "$R/invocations.log" && ! grep -q "build.*done" "$rec"; then got="stopped/refused"; else got="rcs=[$rcl]"; fi ;;
  esac
  if [ "$exp" = "$got" ]; then m=MATCH; else m=MISMATCH; fi
  echo "CASE $name EXPECTED $exp GOT $got $m" >> "$OUT"
done < "$T/runs.txt"
