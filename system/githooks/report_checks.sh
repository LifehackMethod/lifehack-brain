#!/bin/bash
# report_checks.sh -- the pre-commit checks' report to the observation rig (v2 Phase 3b).
# WHY: every friction piece must record when it catches something, so Phase 3c can show which layer is
#      doing the work. This is the ONE place the four commit checks (connected, hides_failure, is_copy,
#      safe_to_ship) write that record.
# USAGE: report_checks.sh <dir>   where <dir> holds, per check, <check>.rc (exit code) and <check>.err
#      (its stderr, containing `FINDING {json}` lines). Called by system/githooks/pre-commit.
# WRITES: (1) system/hooks/lib/journal.sh's lhb_journal_fire, hook "precommit:<check>", event
#      "pre-commit", exit code 0 pass / 1 deny / 3 warn / 2 check-error -- one line per FINDING, plus one
#      "pass" line per clean check run (so the observer can see the checks are alive);
#      (2) the FINDING detail, one JSON line each, appended to $HOME/.claude/run/precommit-findings.jsonl.
# FAIL_POSTURE: SILENT-DEGRADE. Reporting must never change the commit's verdict: it always exits 0.
d="${1:-}"
[ -d "$d" ] || exit 0
here="${BASH_SOURCE[0]%/*}"
. "$here/../hooks/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }  # allow-silence: the journal is an observer; a missing lib degrades to a no-op
log="${LHB_PRECOMMIT_FINDINGS:-${HOME:-/nonexistent}/.claude/run/precommit-findings.jsonl}"
mkdir -p "${log%/*}" 2>/dev/null
# keep it small: one rotation at 1 MB
sz=$(wc -c <"$log" 2>/dev/null || echo 0)
[ "${sz:-0}" -gt 1048576 ] 2>/dev/null && mv -f "$log" "$log.1" 2>/dev/null
ts=$(date +%s 2>/dev/null)
for rcf in "$d"/*.rc; do
  [ -f "$rcf" ] || continue
  chk="${rcf##*/}"; chk="${chk%.rc}"
  rc=$(cat "$rcf" 2>/dev/null); rc="${rc:-2}"
  n=0
  while IFS= read -r line; do
    case "$line" in 'FINDING '*) ;; *) continue ;; esac
    json="${line#FINDING }"
    case "$json" in '{'*'}') ;; *) continue ;; esac
    n=$((n+1))
    case "$json" in
      *'"decision": "warn"'*|*'"decision":"warn"'*) frc=3 ;;
      *) if [ "$rc" = "1" ]; then frc=1; else frc=3; fi ;;
    esac
    printf '{"ts":%s,"check":"%s","rc":%s,"finding":%s}\n' "${ts:-0}" "$chk" "$frc" "$json" >>"$log" 2>/dev/null  # allow-silence: reporting must never change the commit verdict
    lhb_journal_fire "$frc" "precommit:$chk" "pre-commit" "" 2>/dev/null
  done <"$d/$chk.err"
  if [ "$n" -eq 0 ]; then
    case "$rc" in
      0) lhb_journal_fire 0 "precommit:$chk" "pre-commit" "" 2>/dev/null ;;
      *) # refused or errored with no parseable FINDING: still a record
         [ "$rc" = "1" ] || rc=2
         printf '{"ts":%s,"check":"%s","rc":%s,"finding":null}\n' "${ts:-0}" "$chk" "$rc" >>"$log" 2>/dev/null  # allow-silence: reporting must never change the commit verdict
         lhb_journal_fire "$rc" "precommit:$chk" "pre-commit" "" 2>/dev/null ;;
    esac
  fi
done
exit 0
