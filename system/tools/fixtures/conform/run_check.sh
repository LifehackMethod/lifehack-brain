#!/bin/bash
# run_check.sh — regenerate check.log: run conform.py on every fixture in expected.tsv order and compare.
# Usage: run_check.sh [logfile]   (default: check.log next to this script)
here="$(cd "$(dirname "$0")" && pwd)"
tool="$here/../../conform.py"
log="${1:-$here/check.log}"
: > "$log"
while IFS=$'\t' read -r fx exp_v exp_r; do
  [ -n "$fx" ] || continue
  out="$(python3 "$tool" "$here/$fx" 2>&1)"; rc=$?
  final="$(printf '%s\n' "$out" | grep '^verdict=' | tail -1)"
  got_v="$(printf '%s' "$final" | sed -n 's/^verdict=\([A-Z/]*\).*/\1/p')"
  [ -n "$got_v" ] || got_v="NONE"
  if [ "$got_v" = "FAIL" ]; then
    got_r="$(printf '%s\n' "$out" | awk '$1=="FAIL"{print $2}' | sort -u | paste -sd, -)"
  else
    got_r="$(printf '%s\n' "$out" | awk '$1=="EXCEPTION" && $3!="-"{print $2}' | sort -u | paste -sd, -)"
  fi
  [ -n "$got_r" ] || got_r="-"
  case "$got_v" in PASS) want_rc=0;; FAIL) want_rc=1;; N/A) want_rc=3;; *) want_rc=-1;; esac
  res=MISMATCH
  if [ "$got_v" = "$exp_v" ] && [ "$got_r" = "$exp_r" ] && [ "$rc" = "$want_rc" ]; then res=MATCH; fi
  printf '%s EXPECTED %s/%s GOT %s/%s %s\n' "$fx" "$exp_v" "$exp_r" "$got_v" "$got_r" "$res" >> "$log"
done < "$here/expected.tsv"
cat "$log"
