#!/usr/bin/env bash
# job-run.sh — the ONE wrapper every scheduled job runs inside (self-monitoring plan §A, §B.2).
#
# WHY: "ran" is not "succeeded." Dead end [F2] — a script exiting 0 on a skip, an absent input or a
# swallowed error — failed 166 times, the most expensive mistake in this system's history. This
# wrapper is where a job's exit 0 is earned: the job's own command runs, then the OUTPUT CHECK DECLARED IN ITS ROW
# must pass before last-success is stamped. A job with no declared output check can never succeed.
#
# HOW IT IS CALLED: by one launchd LaunchAgent per job (install-schedulers.sh), whose launch line is
#   /bin/bash -c 'exec /bin/bash "$(cat "$HOME/.config/lifehack/code-root")/system/tools/job-run.sh" <job> --if-overdue'
# so no plist ever carries a code path (§B.1). By hand: bash system/tools/job-run.sh <job>
#
# --force (BY-HAND USE ONLY, 5.7): runs a row whose `enabled` is not `yes` (off, waiting-on-port...) exactly ONCE, so a
# migrated job can be dry-run and its output check proven BEFORE its row is flipped. It NEVER changes the row (this script
# never writes the manifest). A plain run of the same row still stands down 75. A forced run is a test: it sends NO push
# (no "job down", no recovery, no deferred-queue flush), so a forced failure cannot page anyone. launchd never passes it.
#
# STATE (local, never Drive — §B.2): ~/.config/lifehack/state/jobs/<job>/
#   last-run      "<ISO time> rc=<n> calls=<N> secs=<S> model=<tier> <reason>" — calls/secs = model calls this run
#                 (5.3, via model.lib.sh run_model; 0/0 for a job with no AI), model = the row's tier or none — every run that got past the overdue check
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
# is missing or at least 2 x INTERVAL old (2.5d: the 2nd consecutive miss, same instant health_line.py says "overdue"), then drops the `alerted` marker so later failures stay quiet.
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
FORCE=0
[ "$#" -gt 0 ] && shift
for _a in "$@"; do
  case "$_a" in
    --if-overdue) IF_OVERDUE=1 ;;
    --force) FORCE=1 ;;
    *) echo "usage: job-run.sh <job-name> [--if-overdue] [--force]" >&2; exit 64 ;;
  esac
done
case "$JOB" in
  ''|*[!a-z0-9-]*) echo "usage: job-run.sh <job-name> [--if-overdue] [--force]" >&2; exit 64 ;;
esac

CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# TEST-ONLY seams (self-monitoring 2.0): LIFEHACK_JOBS_FILE and LIFEHACK_STATE_DIR. Inert when unset.
MANIFEST="${LIFEHACK_JOBS_FILE:-$CODE_ROOT/system/pulse-config.md}"
STATE="${LIFEHACK_STATE_DIR:-$HOME/.config/lifehack/state}/jobs/$JOB"
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

# TEST-ONLY seam LIFEHACK_FAKE_NOW (epoch seconds; inert unless all digits). When set: every "now" and age
# computation reads it, and files whose MTIME is a clock (last-success, last-run, alerted) are stamped to it.
FAKE_NOW=""; case "${LIFEHACK_FAKE_NOW:-}" in ''|*[!0-9]*) ;; *) FAKE_NOW="$LIFEHACK_FAKE_NOW" ;; esac
now_epoch() { if [ -n "$FAKE_NOW" ]; then echo "$FAKE_NOW"; else date +%s; fi; }
fake_fmt() { date -r "$FAKE_NOW" "+$1" 2>/dev/null || date -d "@$FAKE_NOW" "+$1"; }
iso_now() { if [ -n "$FAKE_NOW" ]; then fake_fmt %Y-%m-%dT%H:%M:%S%z; else date +%Y-%m-%dT%H:%M:%S%z; fi; }
err_stamp() { if [ -n "$FAKE_NOW" ]; then fake_fmt %Y%m%dT%H%M%S; else date +%Y%m%dT%H%M%S; fi; }
stamp() { [ -n "$FAKE_NOW" ] || return 0; touch -t "$(fake_fmt %Y%m%d%H%M.%S)" "$@"; }
mtime() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null || echo 0; }
echo "=== run $(iso_now) job=$JOB code_root=$CODE_ROOT$([ "$IF_OVERDUE" = 1 ] && echo ' --if-overdue')$([ "$FORCE" = 1 ] && echo ' --force')"

if [ -s "$STATE/launch.err" ]; then
  echo "[job-run] launch.err was non-empty (pointer was broken before this run):"
  sed 's/^/  launch.err: /' "$STATE/launch.err"
  : > "$STATE/launch.err"
fi

# ── finish: the one exit path. Records last-run (unless told not to), an error file on failure,
#    appends this run to the rolling log and trims it to 20 runs. ──
LOCKDIR=""
# notify <title> <message> <identity> [priority] — fail-soft: one log line on failure, never touches the exit code.
notify() {
  local sender="${JOB_RUN_NOTIFY:-$CODE_ROOT/shared/notify/notify-send.sh}" prio="${4:-normal}"
  # 2.5b: source is per job ("job-run:<job>") so the governor's cap of 3/day applies to each job; a
  # recovery goes out as priority "recovery" (cap-exempt; still respects quiet hours and dedup).
  bash "$sender" --source "job-run:$JOB" --title "$1" --message "$2" --identity "$3" --priority "$prio" --tags warning \
    || echo "[job-run] notify failed or unavailable ($sender) — run result unchanged"
  return 0
}
# flush_deferred — 2.5a: every run of any job replays the governor's quiet-hours queue. The governor only
# releases items once quiet hours (22-07) are over and drops any older than 18 h, so "the first run after
# 07:00 delivers last night's text". Cheap (one python start), fail-soft, never touches the exit code.
# Honours LIFEHACK_FAKE_NOW and NOTIFY_STATE_FILE through the environment.
flush_deferred() {
  local sender="${JOB_RUN_NOTIFY:-$CODE_ROOT/shared/notify/notify-send.sh}"
  bash "$sender" --flush-deferred \
    || echo "[job-run] deferred-queue flush failed or unavailable ($sender) — run result unchanged"
  return 0
}
# alert_check <rc> — the alert rule above; called from finish() so every exit path gets it.
alert_check() {
  local rc="$1" ls_age="" last_ok="never" mark="$STATE/alerted"
  if [ "$rc" -eq 0 ]; then
    [ -f "$mark" ] || return 0
    notify "Job recovered: $JOB" "$JOB succeeded again · output check passed" "job-up:$JOB:$(awk '{print $3}' "$mark")" recovery
    rm -f "$mark"
    return 0
  fi
  [ "$rc" -eq 75 ] && return 0
  case "${INTERVAL:-}" in ''|*[!0-9]*) return 0 ;; esac   # no usable period: nothing to measure against
  [ -f "$mark" ] && return 0
  if [ -f "$STATE/last-success" ]; then
    ls_age=$(( $(now_epoch) - $(mtime "$STATE/last-success") ))
    [ "$ls_age" -lt $(( 2 * INTERVAL )) ] && return 0   # 2.5d: page at age >= 2 x INTERVAL (the 2nd miss)
    last_ok="$(( ls_age / 3600 ))h ago"
  fi
  # The identity carries this incident's id: the marker already dedups within an incident, and the
  # governor's 24 h identity dedup must not swallow the NEXT incident (e.g. a real failure hours after a test).
  local incident; incident="$(now_epoch)"
  notify "Job down: $JOB" "exit $rc · last success $last_ok · next: open any desk; the first line names it, the error is in ~/.config/lifehack/state/jobs/$JOB/errors/" "job-down:$JOB:$incident"
  printf '%s rc=%s %s\n' "$(iso_now)" "$rc" "$incident" > "$mark"
  stamp "$mark"
}
finish() {
  local rc="$1" reason="$2" record="${3:-yes}"
  echo "[job-run] exit $rc — $reason"
  local ncalls=0 nsecs=0
  if [ -s "${JOB_RUN_CALLS_FILE:-}" ]; then
    ncalls="$(wc -l < "$JOB_RUN_CALLS_FILE" | tr -d ' ')"; nsecs="$(awk '{s+=$2} END{print s+0}' "$JOB_RUN_CALLS_FILE")"
  fi
  [ "$record" = yes ] && printf '%s rc=%s calls=%s secs=%s model=%s %s\n' "$(iso_now)" "$rc" "$ncalls" "$nsecs" "${MODEL_TIER:-none}" "$reason" > "$STATE/last-run"
  [ "$record" = yes ] && stamp "$STATE/last-run"
  if [ "$rc" -ne 0 ] && [ "$rc" -ne 75 ] && [ "$rc" -ne 2 ]; then
    cp "$RUNLOG" "$STATE/errors/$(err_stamp).txt" 2>/dev/null
  fi
  [ -n "$LOCKDIR" ] && rm -rf "$LOCKDIR"
  if [ "$FORCE" != 1 ]; then flush_deferred; alert_check "$rc"; fi   # --force is a test: it never pushes
  cat "$RUNLOG" >> "$STATE/log"
  awk '/^=== run /{n++} {line[NR]=$0; sec[NR]=n} END{for(i=1;i<=NR;i++) if(sec[i]>n-20) print line[i]}' \
    "$STATE/log" > "$STATE/log.tmp" && mv -f "$STATE/log.tmp" "$STATE/log"
  rm -f "$RUNLOG" "${JOB_RUN_CALLS_FILE:-}" "${JOB_RUN_CALLS_FILE:+$JOB_RUN_CALLS_FILE.fail}"
  exit "$rc"
}

# ── 1) the job's row in the manifest's ```jobs block:
#    name | enabled | interval | outcome | check | model | budget | source | command  (command LAST: it may hold `|`) ──
ROW="$(awk -v j="$JOB" '
  /^```jobs[[:space:]]*$/ {inb=1; next}
  inb && /^```[[:space:]]*$/ {inb=0}
  inb && $0 !~ /^[[:space:]]*#/ {
    split($0, f, "|"); n=f[1]; gsub(/^[[:space:]]+|[[:space:]]+$/, "", n)
    if (n == j) { print; exit }
  }' "$MANIFEST" 2>/dev/null)"
[ -n "$ROW" ] || finish 1 "no row named '$JOB' in the jobs block of $MANIFEST"
IFS='|' read -r _ ENABLED INTERVAL OUTCOME CHECK MODEL BUDGET SOURCE CMD <<< "$ROW"
ENABLED="$(echo "$ENABLED" | tr -d '[:space:]')"
INTERVAL="$(echo "$INTERVAL" | tr -d '[:space:]')"
CMD="$(echo "$CMD" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
CHECK="$(echo "$CHECK" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
SOURCE="$(echo "$SOURCE" | tr -d '[:space:]')"
# 5.3: the row's model tier and budget go to the job's command; run_model (model.lib.sh) counts calls into the file.
MODEL_TIER="$(echo "$MODEL" | tr -d '[:space:]')"; [ -n "$MODEL_TIER" ] || MODEL_TIER=none
JOB_RUN_BUDGET="$(echo "$BUDGET" | tr -d '[:space:]')"
export JOB_RUN_BUDGET MODEL_TIER JOB_RUN_MODEL="$MODEL_TIER"
JOB_RUN_CALLS_FILE="$STATE/calls.current"; : > "$JOB_RUN_CALLS_FILE"; rm -f "$JOB_RUN_CALLS_FILE.fail"
export JOB_RUN_CALLS_FILE
case "$INTERVAL" in ''|*[!0-9]*) finish 1 "interval '$INTERVAL' is not a number of seconds" ;; esac
[ -n "$CMD" ] || { [ "$ENABLED" != yes ] && [ "$FORCE" != 1 ]; } || finish 1 "row has no command (is it an old 4-column row? the contract columns are required)"
if [ "$ENABLED" != yes ]; then
  [ "$FORCE" = 1 ] || finish 75 "row is '$ENABLED' in the manifest, not 'yes' — stood down"
  echo "[job-run] --force: row is '$ENABLED', running ONCE by hand; the row is not changed and nothing is pushed"
fi

# ── 2) per-job declarations: what credentials it needs, how long it may run, what it promises ──
# NEEDS comes from the row's `source` (5.1): gmail -> the gws credentials. WATCHDOG stays per job until 5.3.
NEEDS=""; WATCHDOG=3600
case "$SOURCE" in gmail) NEEDS="gws" ;; esac
case "$JOB" in
  email-summary-write) WATCHDOG=1200 ;;
  # TEST-ONLY (self-monitoring 2.0 rig): "sim-*" jobs get a short watchdog. Honoured ONLY while
  # LIFEHACK_STATE_DIR is set (a throwaway state root), so it can never act on production state.
  sim-*) [ -n "${LIFEHACK_STATE_DIR:-}" ] && WATCHDOG=60 ;;
esac
# Test seam (kill-one-job, plan 2.3): a by-hand run may shorten the watchdog. launchd never sets it.
case "${JOB_RUN_WATCHDOG:-}" in ''|*[!0-9]*) ;; *) WATCHDOG="$JOB_RUN_WATCHDOG" ;; esac

# The output check is READ FROM THE ROW (5.1): `check` = `<path> ~ <extended regex>`. It passes only if <path> exists,
# its mtime is newer than $START_MARK (this run's start), and some line of it matches the regex (grep -E). $HOME,
# ${HOME}, $LIFEHACK_CODE_ROOT, $JOB_SIM_DIR and a leading ~ are expanded in <path>. The reason for a failure goes to
# stdout (the log). A row with an empty / TBD check never succeeds. Returns 0 pass, 1 fail, 3 no check declared.
expand_path() {
  local p="$1"
  p="${p//\$\{HOME\}/$HOME}"; p="${p//\$HOME/$HOME}"
  p="${p//\$LIFEHACK_CODE_ROOT/${LIFEHACK_CODE_ROOT:-}}"; p="${p//\$JOB_SIM_DIR/${JOB_SIM_DIR:-}}"
  case "$p" in "~"|"~/"*) p="$HOME${p#\~}" ;; esac
  printf '%s' "$p"
}
run_row_check() {
  local path re hit
  case "$CHECK" in ''|TBD) return 3 ;; esac
  case "$CHECK" in *" ~ "*) ;; *) echo "[check] malformed check (want '<path> ~ <regex>'): $CHECK"; return 1 ;; esac
  path="$(echo "${CHECK%% ~ *}" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
  re="$(echo "${CHECK#* ~ }" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
  [ -n "$path" ] && [ -n "$re" ] || { echo "[check] malformed check (empty path or regex): $CHECK"; return 1; }
  path="$(expand_path "$path")"
  [ -f "$path" ] || { echo "[check] output file missing: $path"; return 1; }
  [ "$path" -nt "$START_MARK" ] || { echo "[check] output file not written by this run: $path"; return 1; }
  hit="$(grep -E -e "$re" "$path" 2>/dev/null | tail -1)"
  [ -n "$hit" ] || { echo "[check] no line of $path matches /$re/"; return 1; }
  echo "[check] ok: $hit"
}

# ── 3) --if-overdue ──
if [ "$IF_OVERDUE" = 1 ] && [ -f "$STATE/last-success" ]; then
  GRACE=$(( INTERVAL / 10 )); [ "$GRACE" -gt 1800 ] && GRACE=1800
  AGE=$(( $(now_epoch) - $(mtime "$STATE/last-success") ))
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
[ -n "${LIFEHACK_STATE_DIR:-}" ] && LOCKDIR="$LIFEHACK_STATE_DIR/.lock-$JOB"   # test seam: lock lives in the throwaway root
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  if [ $(( $(now_epoch) - $(mtime "$LOCKDIR") )) -gt $(( WATCHDOG + 300 )) ]; then
    echo "[job-run] stale lock — stealing"; rm -rf "$LOCKDIR"
    mkdir "$LOCKDIR" 2>/dev/null || { LOCKDIR=""; finish 75 "lock race lost"; }
  else
    LOCKDIR=""; finish 75 "another run holds the lock"
  fi
fi

# ── 6) run the command under a watchdog ──
START_MARK="$STATE/.run-start"
if [ -n "$FAKE_NOW" ]; then   # test seam: no real sleep; the run starts one fake second before "now"
  touch "$START_MARK"; FAKE_NOW=$((FAKE_NOW - 1)) stamp "$START_MARK"
else
  touch "$START_MARK"; sleep 1   # mtime granularity is one second; outputs must land strictly after
fi
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

# 5.3: a model failure run_model recorded (over budget, empty output, timeout...) fails the run and is NAMED,
# even when the job swallowed the return code (exit 0 alone is never a success). Stand-downs keep their meaning.
if [ -s "$JOB_RUN_CALLS_FILE.fail" ] && [ "$RC" -ne 75 ] && [ "$RC" -ne 2 ]; then
  finish "$([ "$RC" -eq 0 ] && echo 1 || echo "$RC")" "$(head -1 "$JOB_RUN_CALLS_FILE.fail")"
fi
case "$RC" in
  0)  ;;
  75) finish 75 "the job's own pre-flight stood down" ;;
  2)  finish 2 "the job reported a transient failure" ;;
  *)  finish "$RC" "the job's command failed (rc=$RC)" ;;
esac

# ── 7) output check, then — and only then — last-success ──
run_row_check; _crc=$?
[ "$_crc" -ne 3 ] || finish 1 "no output check declared for '$JOB' — exit 0 alone is never a success"
[ "$_crc" -eq 0 ] || finish 1 "output check failed"
iso_now > "$STATE/last-success"
stamp "$STATE/last-success"
finish 0 "output check passed"
