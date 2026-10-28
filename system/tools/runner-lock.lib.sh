#!/usr/bin/env bash
# runner-lock.lib.sh — the ONE single-instance lock every job runner and the job-run.sh wrapper share (self-monitoring 5.9(h) + 5.9(e)).
#
# WHY: a lock that is only a directory with an mtime cannot tell "a run is still going" from "the last run died": it either blocks a dead
# owner's successor for the whole stale window or steals from a live one. Worse, six runners used to `exit 0` on contention, which is the
# [F2] shape (a skip that looks like success). This lock RECORDS ITS OWNER'S PID, so:
#   - a lock whose owner is DEAD is taken at once;
#   - a lock whose owner is ALIVE is a stand-down (return 75) — never a 0, never a steal;
#   - a lock that is present but unreadable (no pid, or a pid that is not a number) is CORRUPT: refused and named (return 1), not
#     guessed at ("start fresh" would risk running two copies of a job that writes).
#   - the mtime stale window survives only as a guard against PID REUSE: an ALIVE owner on a lock older than <stale-secs> is a hung run
#     or a recycled pid; it is stolen, loudly.
#
# USAGE:  . "$CODE_ROOT/system/tools/runner-lock.lib.sh"
#         runner_lock_acquire "$LOCKDIR" <stale-secs> "<label>" || exit $?       # 75 = stood down (contention), 1 = corrupt lock
#         (the caller's EXIT trap removes "$LOCKDIR"; the lock is a DIRECTORY holding a file `pid`)
# RETURNS 0 acquired (pid recorded) · 75 a live owner holds it · 1 the lock is corrupt, or its owner could not be recorded.
# SETS    RUNNER_LOCK_MSG — one line saying what happened (the caller may use it as a reason). Also printed.
# SEAMS   job-run.sh defines now_epoch / mtime for its fake clock (LIFEHACK_FAKE_NOW); this lib uses them when present.
# ⛔ NO `set` LINE: sourced into callers with different option sets.

_rl_now()   { if type now_epoch >/dev/null 2>&1; then now_epoch; else date +%s; fi; }
_rl_mtime() { if type mtime >/dev/null 2>&1; then mtime "$1"; else stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null || echo 0; fi; }

_rl_take() {   # _rl_take <dir> <label> -> mkdir + record pid
  mkdir "$1" 2>/dev/null || return 1
  if ! printf '%s\n' "$$" > "$1/pid"; then
    RUNNER_LOCK_MSG="FAILED to record the lock owner in $1/pid"; echo "[$2] $RUNNER_LOCK_MSG" >&2; rm -rf "$1"; return 2
  fi
  return 0
}

runner_lock_acquire() {
  local dir="$1" stale="${2:-1500}" label="${3:-runner}" owner="" age rc
  RUNNER_LOCK_MSG=""
  _rl_take "$dir" "$label"; rc=$?
  [ "$rc" -eq 0 ] && return 0
  [ "$rc" -eq 2 ] && return 1
  if [ -f "$dir/pid" ]; then owner="$(cat "$dir/pid")"; fi
  age=$(( $(_rl_now) - $(_rl_mtime "$dir") ))
  case "$owner" in
    '')
      if [ "$age" -lt 10 ]; then
        RUNNER_LOCK_MSG="another run holds the lock (its owner pid is not recorded yet) — standing down"
        echo "[$label] $RUNNER_LOCK_MSG"; return 75
      fi
      RUNNER_LOCK_MSG="CORRUPT lock $dir: no owner pid in $dir/pid — refused, not guessed at; once you have checked nothing is running, remove $dir"
      echo "[$label] $RUNNER_LOCK_MSG" >&2; return 1 ;;
    *[!0-9]*)
      RUNNER_LOCK_MSG="CORRUPT lock $dir: $dir/pid holds '$owner', which is not a pid — refused, not guessed at; once you have checked nothing is running, remove $dir"
      echo "[$label] $RUNNER_LOCK_MSG" >&2; return 1 ;;
  esac
  if kill -0 "$owner" 2>/dev/null; then
    if [ "$age" -le "$stale" ]; then
      RUNNER_LOCK_MSG="another run holds the lock (pid $owner is alive) — standing down"
      echo "[$label] $RUNNER_LOCK_MSG"; return 75
    fi
    echo "[$label] lock owner pid $owner is alive but the lock is ${age}s old (> ${stale}s): a hung run or a recycled pid — stealing it."
  else
    echo "[$label] lock owner pid $owner is dead — taking the lock at once."
  fi
  rm -rf "$dir"
  _rl_take "$dir" "$label"; rc=$?
  [ "$rc" -eq 0 ] && return 0
  [ "$rc" -eq 2 ] && return 1
  RUNNER_LOCK_MSG="lock race lost — standing down"; echo "[$label] $RUNNER_LOCK_MSG"; return 75
}
