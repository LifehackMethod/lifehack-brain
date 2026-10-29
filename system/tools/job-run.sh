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
#   last-run      "<ISO time> rc=<n> calls=<N> secs=<S> model=<tier> ccv=<claude version|none|stub|unknown> <reason>" — calls/secs = model calls this run
#                 (5.3, via model.lib.sh run_model; 0/0 for a job with no AI), model = the row's tier or none — every run that got past the overdue check
#   last-success  "<ISO time>" — written ONLY after the output check passed; its mtime is the clock
#   log           the last 20 runs, one "=== run …" section each
#   pending.current  per-run list of *-last-seen.pending files the shared fetch wrote (5.9(f)); promoted on rc 0 + a passing check, else deleted
#   errors/       one file per FAILED run (not 75, not 2), named by time
#   alerted       exists while ONE "job down" push is out and no success has followed: "<ISO time> rc=<n> <incident id>"
#   standdown-since / standdown-alerted   5.10(2): the first recorded 75 of the current run of 75s / the one 'stood down since' text is out
#   ../.watch/<job>.alerted|.seen         5.10(3): the one 'not running' text for ANOTHER job is out / when a never-run row was first seen
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
# code. 5.10(1): `alerted` is written ONLY on a confirmed send (notify-send rc 0; a quiet-hours deferral is rc 0 and counts); a failed send is
# logged loudly and retried on the next run, recovery included. Sent through shared/notify/notify-send.sh (its governor owns quiet hours and dedup);
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
MANIFEST="${LIFEHACK_JOBS_FILE:-$CODE_ROOT/system/jobs.md}"
STATE="${LIFEHACK_STATE_DIR:-$HOME/.config/lifehack/state}/jobs/$JOB"
mkdir -p "$STATE/errors" || exit 1

# launchd starts jobs with PATH=/usr/bin:/bin:/usr/sbin:/sbin. gws and claude live in
# ~/.local/bin on this kind of install; Homebrew in /opt/homebrew/bin or /usr/local/bin.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:${PATH:-/usr/bin:/bin}"
export LIFEHACK_CODE_ROOT="$CODE_ROOT"
# 5.5 fix: a SCHEDULED job's web reads are sealed to the job host list (safe_fetch.py Level 2, per-run seal). Sessions are not.
_JH="$(grep -vE '^[[:space:]]*(#|$)' "$CODE_ROOT/system/tools/job-fetch-hosts.txt" 2>/dev/null | tr -d '[:blank:]' | paste -sd, -)"
[ -n "$_JH" ] && export SAFE_FETCH_ALLOWLIST="$_JH"

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
# claude_version_short — `claude --version` reduced to its version number; only asked when the row names a model tier (else "none"),
# never hangs the wrapper (10 s cap), "unknown" if it cannot be read. Called once per run (finish caches it).
claude_version_short() {
  [ "${MODEL_TIER:-none}" != none ] || { echo none; return 0; }
  [ -z "${LIFEHACK_MODEL_STUB:-}" ] || { echo stub; return 0; }
  local bin="${CLAUDE_BIN:-$(command -v claude)}" tmp="$STATE/ccv.tmp" v="" p i=0
  [ -n "$bin" ] || { echo unknown; return 0; }
  "$bin" --version > "$tmp" 2>&1 < /dev/null & p=$!
  while kill -0 "$p" 2>/dev/null && [ "$i" -lt 50 ]; do sleep 0.2; i=$((i + 1)); done
  kill "$p" 2>/dev/null
  v="$(head -1 "$tmp" | awk '{print $1}')"; rm -f "$tmp"
  echo "${v:-unknown}"
}
# notify <title> <message> <identity> [priority] [source-job] — returns notify-send's exit code (5.10(1)): the caller writes its marker ONLY on a confirmed
# send. A failure is logged LOUDLY and never touches the run's exit code; the caller leaves the marker unwritten so the next run retries.
notify() {
  local sender="${JOB_RUN_NOTIFY:-$CODE_ROOT/shared/notify/notify-send.sh}" prio="${4:-normal}" src="${5:-$JOB}" nrc targs=()
  # 2.5b: source is per job ("job-run:<job>") so the governor's cap of 3/day applies to each job; a
  # recovery goes out as priority "recovery" (cap-exempt; still respects quiet hours and dedup).
  # 5.14: the text carries its own symbol and no title; job-run NEVER sends priority critical, so none of its texts can break quiet hours (22-07).
  [ -z "$1" ] || targs=(--title "$1")
  bash "$sender" --source "job-run:$src" "${targs[@]+"${targs[@]}"}" --message "$2" --identity "$3" --priority "$prio"; nrc=$?
  [ "$nrc" -eq 0 ] || echo "[job-run] NOTIFY FAILED (rc=$nrc, $sender): the text '${2:0:60}' was NOT delivered -- it will be retried on the next run; run result unchanged"
  return "$nrc"
}
# ── 5.14: the words of every text live in ONE file, system/tools/job-texts.txt (editable without touching code); a job's plain name lives in
# job-names.txt beside the jobs table. job_text <key> prints the wording; plain_name <job> its plain name (no entry: the code name with dashes
# turned into spaces); when_text <epoch> reads "2:10 PM", "yesterday 2:10 PM" or "Tuesday 8 AM"; render_text <key> <job> [epoch...] fills the blanks.
TEXTS_FILE="${LIFEHACK_JOB_TEXTS:-$CODE_ROOT/system/tools/job-texts.txt}"
NAMES_FILE="${LIFEHACK_JOB_NAMES:-$(dirname "$MANIFEST")/job-names.txt}"
job_text() {
  local line
  while IFS= read -r line; do
    case "$line" in "$1 = "*) printf '%s' "${line#"$1 = "}"; return 0 ;; esac
  done < "$TEXTS_FILE" 2>/dev/null
  printf '%s' "⚠ Something needs a look. Open Claude and say: what broke?"   # the file or the key is missing: still say something, plainly
}
plain_name() {
  local line n=""
  while IFS= read -r line; do
    case "$line" in "$1 = "*) n="${line#"$1 = "}"; break ;; esac
  done < "$NAMES_FILE" 2>/dev/null
  [ -n "$n" ] || n="${1//-/ }"
  printf '%s' "$n"
}
when_text() {
  local e="$1" now d y h m ap clock
  now="$(now_epoch)"
  _wf() { date -r "$1" "+$2" 2>/dev/null || date -d "@$1" "+$2"; }
  h="$(_wf "$e" %I)"; m="$(_wf "$e" %M)"; ap="$(_wf "$e" %p)"; h="${h#0}"
  if [ "$m" = 00 ]; then clock="$h $ap"; else clock="$h:$m $ap"; fi
  d="$(_wf "$e" %Y%m%d)"; y="$(_wf $(( now - 86400 )) %Y%m%d)"
  if [ "$d" = "$(_wf "$now" %Y%m%d)" ]; then printf '%s' "$clock"
  elif [ "$d" = "$y" ]; then printf '%s' "yesterday $clock"
  elif [ $(( now - e )) -lt $(( 6 * 86400 )) ]; then printf '%s' "$(_wf "$e" %A) $clock"
  else d="$(_wf "$e" %d)"; printf '%s' "$(_wf "$e" %b) ${d#0}, $clock"; fi
}
render_text() {   # render_text <key> <job> [<epoch for {last_ok} and {since}>]
  local t name when=""; t="$(job_text "$1")"; name="$(plain_name "$2")"
  [ -z "${3:-}" ] || when="$(when_text "$3")"
  t="${t//\{name\}/$name}"; t="${t//\{last_ok\}/$when}"; t="${t//\{since\}/$when}"
  printf '%s' "$t"
}
# confirmed_send <notify rc> — the ONE definition of "the text went out": notify-send exit 0 = sent, OR suppressed by the governor (dedup/cap:
# correct permanent drops), OR queued for quiet hours (the queue delivers it). Anything else (1 failed, 2 setup, 3 corrupt state, 127 missing)
# is NOT a send.
confirmed_send() { [ "$1" -eq 0 ]; }
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
# 5.10(2)(3) test seam: JOB_RUN_NO_WATCH=1 switches OFF the stand-down text and the not-running watch. Honoured ONLY while LIFEHACK_STATE_DIR is set
# (a throwaway state root), so it can never silence production. launchd never sets either.
NO_WATCH=0; [ "${JOB_RUN_NO_WATCH:-}" = 1 ] && [ -n "${LIFEHACK_STATE_DIR:-}" ] && NO_WATCH=1
SD_MULT=2   # 5.10(2): a job is "standing down" once its run of recorded 75s is LONGER than SD_MULT x its interval (one text)
WATCH_MULT=2   # 5.10(3): a job is "not running" once its last-run is OLDER than WATCH_MULT x its interval (one text)
fmt_epoch() { date -r "$1" "+%Y-%m-%d %H:%M" 2>/dev/null || date -d "@$1" "+%Y-%m-%d %H:%M"; }
# standdown_check <record> — 5.10(2). "Continuously 75" is measured by a streak marker, standdown-since (its mtime = the first recorded 75 of the
# run of 75s). finish() clears it on EVERY other result (0, 2, a failure), so the streak is exactly "the recorded runs since X were all 75".
# A run that records nothing (--if-overdue "not overdue", --force) neither starts nor extends it. A row that is not `yes` is never texted
# (an off row stands down by design). Past SD_MULT x INTERVAL: ONE text "<job> stood down since <time>: <reason>" (reason = last-run's);
# standdown-alerted is written only on a confirmed send (a failed one is retried next run); the next pass sends ONE recovery (alert_check).
standdown_check() {
  local since="$STATE/standdown-since" mark="$STATE/standdown-alerted" age incident nrc t0
  [ "$NO_WATCH" = 1 ] && return 0
  [ "$1" = yes ] && [ "${ENABLED:-}" = yes ] || return 0
  case "${INTERVAL:-}" in ''|*[!0-9]*) return 0 ;; esac
  [ -f "$since" ] || { iso_now > "$since"; stamp "$since"; }
  [ -f "$mark" ] && return 0
  t0="$(mtime "$since")"; age=$(( $(now_epoch) - t0 ))
  [ "$age" -gt $(( SD_MULT * INTERVAL )) ] || return 0
  incident="$(now_epoch)"
  notify "" "$(render_text standdown "$JOB" "$t0")" "job-standdown:$JOB:$incident"; nrc=$?
  if confirmed_send "$nrc"; then printf '%s rc=75 %s\n' "$(iso_now)" "$incident" > "$mark"; stamp "$mark"
  else echo "[job-run] stand-down text for $JOB NOT confirmed (notify rc=$nrc): no marker written; retried on the next stood-down run"; fi
}
# human_s <seconds> — "90m", "5h", "3d" for a text.
human_s() { local s="$1"; if [ "$s" -lt 7200 ]; then echo "$(( s / 60 ))m"; elif [ "$s" -lt 172800 ]; then echo "$(( s / 3600 ))h"; else echo "$(( s / 86400 ))d"; fi; }
# watch_others — 5.10(3), runs AFTER the job's own work (finish). Reads every row of the jobs block once; for each ENABLED (yes) row other than this
# one whose last-run is OLDER than WATCH_MULT x its interval -- or that has no last-run at all (never ran: the clock starts the first time any job
# sees the row, in jobs/.watch/<name>.seen) -- sends ONE "not running" text, source job-run:<that job> (so the governor's dedup + cap of 3/day apply to
# it), identity job-down:<job>:<epoch>. The marker jobs/.watch/<name>.alerted is written only on a confirmed send (5.10(1)); when the row is fresh again
# (this job's own row counts) ONE "running again" recovery goes out and the marker is removed. A row that is not `yes` is never watched (its marker
# is dropped). Cheap: one awk over the manifest, a stat per row, a python start only when a text is actually due.
NEVER_RAN_WATCHED=1   # 5.10(3): 1 = a row that never ran is watched too (the unloaded-plist case); the rig's bite plants 0
watch_others() {
  local root wdir wn we wi ref age mark seen nrc incident lr what
  root="$(dirname "$STATE")"; wdir="$root/.watch"
  [ -r "$MANIFEST" ] || { echo "[job-run] WATCH ERROR: cannot read the manifest $MANIFEST -- the other jobs were not checked"; return 1; }
  mkdir -p "$wdir" || { echo "[job-run] WATCH ERROR: cannot create $wdir -- the other jobs were not checked"; return 1; }
  while IFS='|' read -r wn we wi; do
    case "$wn" in ''|*[!a-z0-9-]*) continue ;; esac
    case "$wi" in ''|*[!0-9]*) continue ;; esac
    mark="$wdir/$wn.alerted"; seen="$wdir/$wn.seen"; lr="$root/$wn/last-run"
    if [ "$we" != yes ]; then rm -f "$mark" "$seen"; continue; fi
    if [ -f "$lr" ]; then ref="$(mtime "$lr")"; rm -f "$seen"
    elif [ -f "$root/$wn/last-success" ]; then ref="$(mtime "$root/$wn/last-success")"; rm -f "$seen"
    else
      [ "$NEVER_RAN_WATCHED" = 1 ] || continue
      [ -f "$seen" ] || { iso_now > "$seen"; stamp "$seen"; }
      ref="$(mtime "$seen")"
    fi
    age=$(( $(now_epoch) - ref ))
    if [ "$age" -gt $(( WATCH_MULT * wi )) ]; then
      [ "$wn" = "$JOB" ] && continue      # this job just ran: its own staleness is the job-down rule's business
      [ -f "$mark" ] && continue
      if [ -f "$lr" ] || [ -f "$root/$wn/last-success" ]; then what="$(render_text notrunning "$wn" "$ref")"; else what="$(render_text notrunning_never "$wn")"; fi
      incident="$(now_epoch)"
      notify "" "$what" "job-down:$wn:$incident" normal "$wn"; nrc=$?
      if confirmed_send "$nrc"; then printf '%s %s\n' "$(iso_now)" "$incident" > "$mark"; stamp "$mark"
      else echo "[job-run] not-running text for $wn NOT confirmed (notify rc=$nrc): no marker written; retried on the next job run"; fi
    elif [ -f "$mark" ]; then
      incident="$(awk '{print $2}' "$mark")"
      notify "" "$(render_text running_again "$wn")" "job-up:$wn:$incident" recovery "$wn"; nrc=$?
      if confirmed_send "$nrc"; then rm -f "$mark"; else echo "[job-run] running-again text for $wn NOT confirmed (notify rc=$nrc): marker stays, retried on the next job run"; fi
    fi
  done < <(awk '
    /^```jobs[[:space:]]*$/ {inb=1; next}
    inb && /^```[[:space:]]*$/ {inb=0}
    inb && $0 !~ /^[[:space:]]*#/ && NF {
      n=split($0, f, "|"); if (n < 3) next
      for (i=1; i<=3; i++) gsub(/[[:space:]]+/, "", f[i])
      print f[1] "|" f[2] "|" f[3]
    }' "$MANIFEST")
}
# watch_jobs — fail-safe wrapper: the watch runs in a subshell; ANY error is logged loudly and NEVER changes this run's exit code.
watch_jobs() {
  [ "$NO_WATCH" = 1 ] && return 0
  ( watch_others ) || echo "[job-run] WATCH STEP FAILED (rc=$?): the other jobs were not (fully) checked this run; this job's own result is unchanged"
  return 0
}
# alert_check <rc> [record] — the alert rule above; called from finish() so every exit path gets it.
alert_check() {
  local rc="$1" record="${2:-yes}" ls_age="" last_ok="" mark="$STATE/alerted" nrc smark="$STATE/standdown-alerted"
  [ "$rc" -eq 75 ] || rm -f "$STATE/standdown-since"   # 5.10(2): any result but 75 ends a run of stand-downs
  if [ "$rc" -eq 0 ] && [ -f "$smark" ] && [ "$NO_WATCH" != 1 ]; then   # 5.10(2): ONE recovery after a stand-down text
    notify "" "$(render_text running_again "$JOB")" "job-standdown-up:$JOB:$(awk '{print $3}' "$smark")" recovery; nrc=$?
    if confirmed_send "$nrc"; then rm -f "$smark"; else echo "[job-run] stand-down recovery text not confirmed: marker stays, retried on the next passing run"; fi
  fi
  if [ "$rc" -eq 0 ]; then
    [ -f "$mark" ] || return 0
    notify "" "$(render_text recovered "$JOB")" "job-up:$JOB:$(awk '{print $3}' "$mark")" recovery; nrc=$?
    if confirmed_send "$nrc"; then rm -f "$mark"; else echo "[job-run] recovery text not confirmed: the alerted marker stays, the recovery is retried on the next passing run"; fi
    return 0
  fi
  [ "$rc" -eq 75 ] && { standdown_check "$record"; return 0; }
  case "${INTERVAL:-}" in ''|*[!0-9]*) return 0 ;; esac   # no usable period: nothing to measure against
  [ -f "$mark" ] && return 0
  if [ -f "$STATE/last-success" ]; then
    ls_age=$(( $(now_epoch) - $(mtime "$STATE/last-success") ))
    [ "$ls_age" -lt $(( 2 * INTERVAL )) ] && return 0   # 2.5d: page at age >= 2 x INTERVAL (the 2nd miss)
    last_ok="$(mtime "$STATE/last-success")"
  fi
  # The identity carries this incident's id: the marker already dedups within an incident, and the
  # governor's 24 h identity dedup must not swallow the NEXT incident (e.g. a real failure hours after a test).
  local incident dtext; incident="$(now_epoch)"
  if [ -n "$last_ok" ]; then dtext="$(render_text down "$JOB" "$last_ok")"; else dtext="$(render_text down_never "$JOB")"; fi
  notify "" "$dtext" "job-down:$JOB:$incident"; nrc=$?
  # 5.10(1): the marker is written ONLY on a confirmed send. A failed send leaves it unwritten, so the next failing run tries again.
  if confirmed_send "$nrc"; then
    printf '%s rc=%s %s\n' "$(iso_now)" "$rc" "$incident" > "$mark"
    stamp "$mark"
  else
    echo "[job-run] down text for $JOB NOT confirmed (notify rc=$nrc): no alerted marker written; retried on the next failing run"
  fi
}
finish() {
  local rc="$1" reason="$2" record="${3:-yes}"
  echo "[job-run] exit $rc — $reason"
  local ncalls=0 nsecs=0
  if [ -s "${JOB_RUN_CALLS_FILE:-}" ]; then
    ncalls="$(wc -l < "$JOB_RUN_CALLS_FILE" | tr -d ' ')"; nsecs="$(awk '{s+=$2} END{print s+0}' "$JOB_RUN_CALLS_FILE")"
  fi
  # 5.9(g): ccv = the Claude Code version that ran (cached per run; "none" for a job with no model, "stub" under the rig's model stub)
  [ -n "${_CCV:-}" ] || _CCV="$(claude_version_short)"
  [ "$record" = yes ] && printf '%s rc=%s calls=%s secs=%s model=%s ccv=%s %s\n' "$(iso_now)" "$rc" "$ncalls" "$nsecs" "${MODEL_TIER:-none}" "$_CCV" "$reason" > "$STATE/last-run"
  [ "$record" = yes ] && stamp "$STATE/last-run"
  if [ "$rc" -ne 0 ] && [ "$rc" -ne 75 ] && [ "$rc" -ne 2 ]; then
    # 5.10(4): cp's own error is SHOWN (it lands in this run's log), and the failure is named -- never dropped.
    cp "$RUNLOG" "$STATE/errors/$(err_stamp).txt" || echo "[job-run] could not save the error file under $STATE/errors/ (cp's error is above) -- this failed run has no errors/ file"
  fi
  if [ -n "${JOB_RUN_PENDING_LIST:-}" ] && [ -f "$JOB_RUN_PENDING_LIST" ]; then
    while IFS= read -r _pp; do
      [ -n "$_pp" ] && [ -e "$_pp" ] && { rm -f "$_pp" && echo "[job-run] dropped $_pp (not promoted: the work did not finish with a passing check, or this was a forced test)"; }
    done < "$JOB_RUN_PENDING_LIST"
    rm -f "$JOB_RUN_PENDING_LIST"
  fi
  [ -n "$LOCKDIR" ] && rm -rf "$LOCKDIR"
  if [ "$FORCE" != 1 ]; then flush_deferred; alert_check "$rc" "$record"; watch_jobs; fi   # --force is a test: it never pushes
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
export JOB_RUN_FORCED="$FORCE"   # 5.7: 1 on a by-hand --force run (a test: a command must not push or stamp "done today" state), else 0
JOB_RUN_CALLS_FILE="$STATE/calls.current"; : > "$JOB_RUN_CALLS_FILE"; rm -f "$JOB_RUN_CALLS_FILE.fail"
export JOB_RUN_CALLS_FILE
# 5.9(f): the shared fetch appends the path of each *-last-seen.pending it writes to this list. They are PROMOTED to the bookmark only on
# rc 0 AND a passing row check (below); on any other outcome, and on a --force run (a test), finish() deletes them: a bookmark moves
# only when the work is done.
JOB_RUN_PENDING_LIST="$STATE/pending.current"; : > "$JOB_RUN_PENDING_LIST"; export JOB_RUN_PENDING_LIST
case "$INTERVAL" in ''|*[!0-9]*) finish 1 "interval '$INTERVAL' is not a number of seconds" ;; esac
# ── 1b) 5.9(e): a state file that is PRESENT but unreadable is REFUSED and NAMED -- never treated as a first run ("start fresh" would
#    hide a torn write or a tamper, and e.g. a last-success of garbage would read as an old success). A MISSING file is normal (first run).
#    The lock is checked by runner-lock.lib.sh at step 5. last-run is left as it is (record=no) so the damaged bytes stay for inspection. ──
_ISO='[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}([+-][0-9]{4}|Z)?'
# An OFF row stands down BEFORE the corrupt-state checks (a by-hand run of an off row is not a failure). A damaged last-run is still
# left unread (record=no), so its bytes stay for inspection. --force still goes through the checks below.
if [ "$ENABLED" != yes ] && [ "$FORCE" != 1 ]; then
  if [ -e "$STATE/last-run" ] && ! head -1 "$STATE/last-run" 2>/dev/null | grep -qE "^${_ISO} rc=[0-9]+( |\$)"; then
    finish 75 "row is '$ENABLED' in the manifest, not 'yes' — stood down (its last-run is damaged; left as it is)" no
  fi
  finish 75 "row is '$ENABLED' in the manifest, not 'yes' — stood down"
fi
if [ -e "$STATE/last-success" ]; then
  if [ ! -f "$STATE/last-success" ] || ! head -1 "$STATE/last-success" | grep -qE "^${_ISO}\$" || [ "$(wc -l < "$STATE/last-success" | tr -d ' ')" -gt 1 ]; then
    finish 1 "corrupt state file: $STATE/last-success is not one ISO timestamp -- refusing to treat it as a first run; fix or remove it by hand"
  fi
fi
if [ -e "$STATE/last-run" ]; then
  if [ ! -f "$STATE/last-run" ] || ! head -1 "$STATE/last-run" | grep -qE "^${_ISO} rc=[0-9]+( |\$)"; then
    finish 1 "corrupt state file: $STATE/last-run is not '<ISO time> rc=<n> ...' -- refusing to overwrite it unread; fix or remove it by hand" no
  fi
fi
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
  # 5.10(4): grep's stderr is SHOWN (it lands in the log). rc 1 = no match (normal); rc 2 = grep could not run (bad regex, unreadable file) -> named.
  hit="$(grep -E -e "$re" "$path" | tail -1; exit "${PIPESTATUS[0]}")"; _grc=$?
  [ "$_grc" -le 1 ] || { echo "[check] grep failed (rc=$_grc) on $path with /$re/ -- its error is above; the check cannot pass"; return 1; }
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
# 5.9(h)+(e): the lock records its owner pid (runner-lock.lib.sh). A dead owner's lock is taken at once; a LIVE owner stands this run down
# (75); a lock that is present but unreadable is refused and NAMED (exit 1), never guessed at. The mtime window is only a pid-reuse guard.
. "$CODE_ROOT/system/tools/runner-lock.lib.sh" || finish 1 "cannot source runner-lock.lib.sh"
runner_lock_acquire "$LOCKDIR" $(( WATCHDOG + 300 )) "job-run:$JOB"; _lrc=$?
case "$_lrc" in
  0) ;;
  75) LOCKDIR=""; finish 75 "${RUNNER_LOCK_MSG:-another run holds the lock}" ;;
  *)  _lmsg="${RUNNER_LOCK_MSG:-the lock could not be taken}"; LOCKDIR=""; finish 1 "$_lmsg" ;;
esac

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
# 5.9(f): the work is done (rc 0) and its check passed -> NOW the bookmarks may move. A forced run is a test: finish() drops them instead.
if [ "$FORCE" != 1 ] && [ -s "$JOB_RUN_PENDING_LIST" ]; then
  while IFS= read -r _pp; do
    [ -n "$_pp" ] || continue
    python3 "$CODE_ROOT/shared/tools/email_fetch.py" --promote-pending "$_pp" \
      || finish 1 "bookmark promotion failed for $_pp (named above); last-success NOT stamped"
  done < "$JOB_RUN_PENDING_LIST"
  : > "$JOB_RUN_PENDING_LIST"
fi
iso_now > "$STATE/last-success"
stamp "$STATE/last-success"
finish 0 "output check passed"
