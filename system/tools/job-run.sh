#!/usr/bin/env bash
# job-run.sh — the ONE wrapper every scheduled job runs inside (self-monitoring plan §A, §B.2).
#
# WHY: "ran" is not "succeeded." Dead end [F2] — a script exiting 0 on a skip, an absent input or a
# swallowed error — failed 166 times, the most expensive mistake in this system's history. This
# wrapper is where a job's exit 0 is earned: the job's own command runs, then a PER-JOB OUTPUT CHECK
# must pass before last-success is stamped. A job with no declared output check can never succeed.
#
# HOW IT IS CALLED: by one launchd LaunchAgent per job (install-schedulers.sh), whose launch line is
#   /bin/bash -c 'exec /bin/bash "$(cat "$HOME/.config/lifehack/code-root")/system/tools/job-run.sh" <job> --if-overdue'
# so no plist ever carries a code path (§B.1). By hand: bash system/tools/job-run.sh <job>
#
# STATE (local, never Drive — §B.2): ~/.config/lifehack/state/jobs/<job>/
#   last-run      "<ISO time> rc=<n> <reason>" — every run that got past the overdue check
#   last-success  "<ISO time>" — written ONLY after the output check passed; its mtime is the clock
#   log           the last 20 runs, one "=== run …" section each
#   errors/       one file per FAILED run (not 75, not 2), named by time
#   alerted       exists while ONE "job down" push is out and no success has followed: "<ISO time> rc=<n> <incident id>"
#   launch.err    launchd's StandardErrorPath — non-empty means the launch line could not find this
#                 file (a bad code-root pointer). This wrapper moves its contents into the log and
#                 clears it, because reaching this line proves the pointer works again.
#
# EXIT CONTRACT (§A laws):
#   0  the output check passed — nothing else ever exits 0
#   75 stood down: row not enabled, not configured, not overdue, another run holds the lock
#   2  transient (network / Google pre-flight); retried next period
#   *  failed — an errors/ file is written
#
# ALERT RULE (§A, "two misses"): a FAILED run (not 0, not 75; 2 counts) pushes ONCE when last-success
# is missing or older than 2 x INTERVAL, then drops the `alerted` marker so later failures stay quiet.
# The next success pushes ONE recovery and removes the marker. A push that fails never changes the exit
# code. Sent through shared/notify/notify-send.sh (its governor owns quiet hours and dedup);
# JOB_RUN_NOTIFY overrides the path, for tests.
#
# --if-overdue: run only if last-success is older than one period minus a 10% grace (capped at
# 30 min). launchd gives a plist ONE argument list, so the calendar fire and RunAtLoad cannot pass
# different flags; with the grace, every calendar fire is overdue (the last success is ~one period
# old) while a login shortly after a success stands down. After a Shut Down, the at-login fire runs.
#
# REUSES system/tools/ingest-run.lib.sh for binary resolution and the credential/pre-flight checks.
# Its lock (ingest_acquire_lock) and watchdog (ingest_run_claude) are NOT used: the lock `exit 0`s on
# contention — the [F2] shape — and the watchdog only launches `claude -p`. Both are done here.
set -uo pipefail

JOB="${1:-}"
IF_OVERDUE=0
[ "${2:-}" = "--if-overdue" ] && IF_OVERDUE=1
case "$JOB" in
  ''|*[!a-z0-9-]*) echo "usage: job-run.sh <job-name> [--if-overdue]" >&2; exit 64 ;;
esac

CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="$CODE_ROOT/system/pulse-config.md"
STATE="$HOME/.config/lifehack/state/jobs/$JOB"
mkdir -p "$STATE/errors" || exit 1

# launchd starts jobs with PATH=/usr/bin:/bin:/usr/sbin:/sbin. gws and claude live in
# ~/.local/bin on this kind of install; Homebrew in /opt/homebrew/bin or /usr/local/bin.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:${PATH:-/usr/bin:/bin}"
export LIFEHACK_CODE_ROOT="$CODE_ROOT"

# Everything this run prints goes to one capture file, appended to the rolling log at the end.
# stderr too: launch.err must stay empty unless the launch line itself failed.
RUNLOG="$STATE/run.current"
: > "$RUNLOG"
exec >>"$RUNLOG" 2>&1

iso_now() { date +%Y-%m-%dT%H:%M:%S%z; }
mtime() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null || echo 0; }
echo "=== run $(iso_now) job=$JOB code_root=$CODE_ROOT$([ "$IF_OVERDUE" = 1 ] && echo ' --if-overdue')"

if [ -s "$STATE/launch.err" ]; then
  echo "[job-run] launch.err was non-empty (pointer was broken before this run):"
  sed 's/^/  launch.err: /' "$STATE/launch.err"
  : > "$STATE/launch.err"
fi

# ── finish: the one exit path. Records last-run (unless told not to), an error file on failure,
#    appends this run to the rolling log and trims it to 20 runs. ──
LOCKDIR=""
# notify <title> <message> <identity> — fail-soft: one log line on failure, never touches the exit code.
notify() {
  local sender="${JOB_RUN_NOTIFY:-$CODE_ROOT/shared/notify/notify-send.sh}"
  bash "$sender" --source job-run --title "$1" --message "$2" --identity "$3" --tags warning \
    || echo "[job-run] notify failed or unavailable ($sender) — run result unchanged"
  return 0
}
# alert_check <rc> — the alert rule above; called from finish() so every exit path gets it.
alert_check() {
  local rc="$1" ls_age="" last_ok="never" mark="$STATE/alerted"
  if [ "$rc" -eq 0 ]; then
    [ -f "$mark" ] || return 0
    notify "Job recovered: $JOB" "$JOB succeeded again · output check passed" "job-up:$JOB:$(awk '{print $3}' "$mark")"
    rm -f "$mark"
    return 0
  fi
  [ "$rc" -eq 75 ] && return 0
  case "${INTERVAL:-}" in ''|*[!0-9]*) return 0 ;; esac   # no usable period: nothing to measure against
  [ -f "$mark" ] && return 0
  if [ -f "$STATE/last-success" ]; then
    ls_age=$(( $(date +%s) - $(mtime "$STATE/last-success") ))
    [ "$ls_age" -le $(( 2 * INTERVAL )) ] && return 0
    last_ok="$(( ls_age / 3600 ))h ago"
  fi
  # The identity carries this incident's id: the marker already dedups within an incident, and the
  # governor's 24 h identity dedup must not swallow the NEXT incident (e.g. a real failure hours after a test).
  local incident; incident="$(date +%s)"
  notify "Job down: $JOB" "exit $rc · last success $last_ok · next: open any desk; the first line names it, the error is in ~/.config/lifehack/state/jobs/$JOB/errors/" "job-down:$JOB:$incident"
  printf '%s rc=%s %s\n' "$(iso_now)" "$rc" "$incident" > "$mark"
}
finish() {
  local rc="$1" reason="$2" record="${3:-yes}"
  echo "[job-run] exit $rc — $reason"
  [ "$record" = yes ] && printf '%s rc=%s %s\n' "$(iso_now)" "$rc" "$reason" > "$STATE/last-run"
  if [ "$rc" -ne 0 ] && [ "$rc" -ne 75 ] && [ "$rc" -ne 2 ]; then
    cp "$RUNLOG" "$STATE/errors/$(date +%Y%m%dT%H%M%S).txt" 2>/dev/null
  fi
  [ -n "$LOCKDIR" ] && rm -rf "$LOCKDIR"
  alert_check "$rc"
  cat "$RUNLOG" >> "$STATE/log"
  awk '/^=== run /{n++} {line[NR]=$0; sec[NR]=n} END{for(i=1;i<=NR;i++) if(sec[i]>n-20) print line[i]}' \
    "$STATE/log" > "$STATE/log.tmp" && mv -f "$STATE/log.tmp" "$STATE/log"
  rm -f "$RUNLOG"
  exit "$rc"
}

# ── 1) the job's row in the manifest's ```jobs block: name | enabled | interval | command ──
ROW="$(awk -v j="$JOB" '
  /^```jobs[[:space:]]*$/ {inb=1; next}
  inb && /^```[[:space:]]*$/ {inb=0}
  inb && $0 !~ /^[[:space:]]*#/ {
    split($0, f, "|"); n=f[1]; gsub(/^[[:space:]]+|[[:space:]]+$/, "", n)
    if (n == j) { print; exit }
  }' "$MANIFEST" 2>/dev/null)"
[ -n "$ROW" ] || finish 1 "no row named '$JOB' in the jobs block of $MANIFEST"
IFS='|' read -r _ ENABLED INTERVAL CMD <<< "$ROW"
ENABLED="$(echo "$ENABLED" | tr -d '[:space:]')"
INTERVAL="$(echo "$INTERVAL" | tr -d '[:space:]')"
CMD="$(echo "$CMD" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
case "$INTERVAL" in ''|*[!0-9]*) finish 1 "interval '$INTERVAL' is not a number of seconds" ;; esac
[ "$ENABLED" = yes ] || finish 75 "row is '$ENABLED' in the manifest, not 'yes' — stood down"

# ── 2) per-job declarations: what credentials it needs, how long it may run, what it promises ──
NEEDS=""; WATCHDOG=3600
case "$JOB" in
  email-summary-write) NEEDS="gws"; WATCHDOG=1200 ;;
esac
# Test seam (kill-one-job, plan 2.3): a by-hand run may shorten the watchdog. launchd never sets it.
case "${JOB_RUN_WATCHDOG:-}" in ''|*[!0-9]*) ;; *) WATCHDOG="$JOB_RUN_WATCHDOG" ;; esac

# Each check returns 0 only if the job's promised output is there AND newer than $START_MARK.
# The reason for a failure goes to stdout (the log). A job without a check never succeeds.
check_email_summary_write() {
  # write_v2 SKIPS unchanged threads, so a quiet period writes nothing into threads-v2/ — a file
  # there is not a per-run promise. And write_v2 exits 0 on a HARD-STOP and when every label lists
  # zero threads. The run's own worklog is the honest receipt: newer than this run, carrying the
  # DONE summary, having seen at least one thread.
  local wl="$HOME/.local/share/lifehack/email-summary-write/last-write.log" done_line w u e
  [ -f "$wl" ] || { echo "[check] worklog missing: $wl"; return 1; }
  [ "$wl" -nt "$START_MARK" ] || { echo "[check] worklog not written by this run: $wl"; return 1; }
  done_line="$(grep 'v2 write DONE' "$wl" | tail -1)"
  [ -n "$done_line" ] || { echo "[check] no 'v2 write DONE' line — write_v2 stopped early (HARD-STOP?)"; return 1; }
  w="$(echo "$done_line" | sed -nE 's/.*written=([0-9]+).*/\1/p')"
  u="$(echo "$done_line" | sed -nE 's/.*unchanged=([0-9]+).*/\1/p')"
  e="$(echo "$done_line" | sed -nE 's/.*errors=([0-9]+).*/\1/p')"
  if [ $(( ${w:-0} + ${u:-0} )) -lt 1 ]; then
    echo "[check] zero threads seen (written=${w:-?} unchanged=${u:-?} errors=${e:-?}) — an empty result is not a success"
    return 1
  fi
  echo "[check] ok: written=$w unchanged=$u errors=${e:-0}"
}

# ── 3) --if-overdue ──
if [ "$IF_OVERDUE" = 1 ] && [ -f "$STATE/last-success" ]; then
  GRACE=$(( INTERVAL / 10 )); [ "$GRACE" -gt 1800 ] && GRACE=1800
  AGE=$(( $(date +%s) - $(mtime "$STATE/last-success") ))
  if [ "$AGE" -lt $(( INTERVAL - GRACE )) ]; then
    finish 75 "not overdue: last success ${AGE}s ago, period ${INTERVAL}s" no
  fi
fi

# ── 4) credentials + pre-flight, through the shared library ──
. "$CODE_ROOT/system/tools/ingest-run.lib.sh" || finish 1 "cannot source ingest-run.lib.sh"
case " $NEEDS " in *" claude "*)
  require_claude_token "$JOB" || finish 75 "claude token not configured" ;;
esac
case " $NEEDS " in *" gws "*)
  # ingest_load_gws exits (75 / 2) rather than returning — run it in a subshell to read the code.
  ( ingest_load_gws "$JOB" ); _rc=$?
  case "$_rc" in
    0) ;;
    75) finish 75 "gws credentials not configured" ;;
    2) finish 2 "gws pre-flight failed (transient)" ;;
    *) finish 1 "gws pre-flight broke (rc=$_rc)" ;;
  esac ;;
esac

# ── 5) single-instance lock — contention is a stand-down (75), never a 0 ──
LOCKDIR="/tmp/lifehack-job-$JOB.lock"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  if [ $(( $(date +%s) - $(mtime "$LOCKDIR") )) -gt $(( WATCHDOG + 300 )) ]; then
    echo "[job-run] stale lock — stealing"; rm -rf "$LOCKDIR"
    mkdir "$LOCKDIR" 2>/dev/null || { LOCKDIR=""; finish 75 "lock race lost"; }
  else
    LOCKDIR=""; finish 75 "another run holds the lock"
  fi
fi

# ── 6) run the command under a watchdog ──
START_MARK="$STATE/.run-start"
touch "$START_MARK"; sleep 1   # mtime granularity is one second; outputs must land strictly after
echo "[job-run] command: $CMD (watchdog ${WATCHDOG}s)"
bash -c "$CMD" & CPID=$!
( sleep "$WATCHDOG"; echo "[job-run] watchdog: killing after ${WATCHDOG}s"
  pkill -TERM -P "$CPID" 2>/dev/null; kill -TERM "$CPID" 2>/dev/null; sleep 10
  pkill -KILL -P "$CPID" 2>/dev/null; kill -KILL "$CPID" 2>/dev/null ) & WPID=$!
disown "$WPID" # so stopping it below does not print a "Terminated" line into every run's log
wait "$CPID"; RC=$?
# Stop the watchdog: note its sleep, kill the watchdog FIRST (so it can never go on to its kill
# lines), then the sleep, which would otherwise linger as an orphan for the whole watchdog period.
WSLEEP="$(pgrep -P "$WPID" 2>/dev/null)"
kill "$WPID" 2>/dev/null; [ -n "$WSLEEP" ] && kill $WSLEEP 2>/dev/null

case "$RC" in
  0)  ;;
  75) finish 75 "the job's own pre-flight stood down" ;;
  2)  finish 2 "the job reported a transient failure" ;;
  *)  finish "$RC" "the job's command failed (rc=$RC)" ;;
esac

# ── 7) output check, then — and only then — last-success ──
FN="check_$(echo "$JOB" | tr '-' '_')"
declare -F "$FN" >/dev/null || finish 1 "no output check declared for '$JOB' — exit 0 alone is never a success"
"$FN" || finish 1 "output check failed"
iso_now > "$STATE/last-success"
finish 0 "output check passed"
