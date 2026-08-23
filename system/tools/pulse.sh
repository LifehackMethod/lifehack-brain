#!/usr/bin/env bash
# ── PULSE — the heartbeat daemon ─────────────────────────────────────────────
# WHY (the gap this CLOSED — past tense on purpose): until this file landed on 2026-08-14, the repo
#      shipped without any scheduler — no cron/launchd/Task-Scheduler wiring, no daemon, nothing
#      that ever called a health check or a sync job on its own. Pulse is the fix, and it is now the
#      live answer: ONE scheduled entry (installed by install-schedulers.sh, which covers cron AND
#      Windows Task Scheduler) invokes THIS script, and this script reads a plain-text manifest
#      (system/pulse-config.md) and runs whichever job is due.
#      ⚠ Do not re-read this paragraph as a present-tense claim that scheduling is missing — that
#      reading was the single most-copied stale fact in the tree (T9.7d sweep, 2026-08-15).
#
# PORTED (2026-08-14) from claudeops-config's system/tools/pulse.sh, generalized under a 2026-08-13
# product ruling ("automation ships with its scheduler"). Two structural things were CUT, not
# translated, because they answer a question this product doesn't have:
#   - the "which of two machines is in charge" lead-machine preflight + nag (donor pulse.sh:159-172).
#     This product is single-machine by design (shared/brain_root.py; docs/data-layout.md:214,
#     "there is one machine"), so a lead election has nothing to elect.
#   - the machine-namespaced heartbeat mirror (the donor suffixed the heartbeat file with a per-machine
#     token — _pulse-<machine>.json — so the primary and the second machine's ticks wouldn't clobber
#     one shared file). One machine writes one file: _pulse.json.
# Everything else below — the breaker, the doubling backoff, the durable park file, the rc=75/rc=2
# exit-code contract — is the proven, tested part and ships close to verbatim, because a scheduler
# that can wedge a broken job into running forever, or that can't tell "ran and failed" from "chose
# not to run", is worse than having none at all.
#
# RUN:  cron/Task-Scheduler → every 5 min → bash "<repo>/system/tools/pulse.sh" >> <tmp>/pulse.log 2>&1
#       (install-schedulers.sh writes this entry for you; see that script.)
# TEST: PULSE_CONFIG=... PULSE_STATE=... bash pulse.sh        (sandbox a run)
#       bash pulse.sh --status                                (show due/not-due, no exec)
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail   # NOT -e: one failing job must never kill the daemon

CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # this script's own repo root
# Exported (a separate statement, not a same-line prefix) so every job command dispatched below via
# `bash -c "$cmd"` can reference "$LIFEHACK_CODE_ROOT/..." and have it resolve — a job's command
# string is parsed and expanded by the CHILD bash `-c` receives, which inherits this exported value
# from THIS process's environment. This is NOT the same as writing `VAR=val bash "$VAR/x"` on one
# line — that classic gotcha expands "$VAR" in the OUTER shell BEFORE the prefix assignment takes
# effect and silently resolves to empty (measured while building this file; see also
# install-schedulers.sh, which substitutes this token literally for the OS-scheduled crontab/
# Task-Scheduler entries, which run outside this process entirely and can't inherit an export).
export LIFEHACK_CODE_ROOT="$CODE_ROOT"
CONFIG="${PULSE_CONFIG:-$CODE_ROOT/system/pulse-config.md}"        # the manifest — always CODE-resident
STATE="${PULSE_STATE:-${TMPDIR:-/tmp}/lifehack-pulse-state.json}"  # machine-local; lost state just means jobs re-run next cycle (safe)

# ── The notes root — resolved once, the same way every other tool in this repo resolves it.
# NOT-SET is a legitimate state on a fresh install (nobody has pointed this at a folder yet): Pulse
# still runs and still dispatches jobs whose commands don't need a notes root (e.g. a job that only
# touches CODE-resident files); anything that DOES need one (the durable park file below, most job
# bodies) degrades gracefully on its own — see PARK_FILE's own comment. Pulse itself never refuses
# to run for want of a root; only individual jobs decide that for themselves.
_ROOT_LINE="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
NOTES_ROOT="${_ROOT_LINE:-}"

# ── Deliberate-park marker: DURABLE, never /tmp ─────────────────────────────
# STATE above (last-run + breaker fails/disabled) is correctly ephemeral — a fresh /tmp just means
# every job looks "never run" and Pulse rebuilds from there. But a HUMAN'S deliberate park (see
# get_park_retry below) must never live in the same wipeable file, or a reboot silently un-parks a
# job the human explicitly turned off. PARK_FILE lives under the notes root (durable, synced with
# your own backup of that folder) so no reboot ever touches it. Absence must mean "nothing parked" —
# every reader below fails open to empty on a missing/corrupt file, never to "everything parked."
PARK_FILE="${PULSE_PARK_FILE:-${NOTES_ROOT:+$NOTES_ROOT/state/pulse-parked-jobs.json}}"
PARK_HORIZON_S=$((7 * 86400))   # breaker backoff caps at 24h; this is just a generous outer bound
# Circuit breaker: a job that fails this many times IN A ROW auto-disables itself (machine-local, in
# STATE) + logs loud — so a broken/destructive job can never run unattended forever. Clears when the
# job next succeeds, or on a state reset.
MAX_FAILURES="${PULSE_MAX_FAILURES:-3}"
# ── BACKOFF, not OFF-FOREVER ────────────────────────────────────────────────
# A trip is a TIMEOUT, not a tombstone: the job is held off for a doubling interval and then gets
# ONE half-open probe. If it passes, everything resets; if it fails, the next hold is twice as long,
# capped. A genuinely broken job still cannot run unattended in a loop — it just retries at 1h, 2h,
# 4h... instead of never. (Donor incident: three jobs sat disabled 11/25/28 days after a transient
# blip tripped the old off-forever breaker; when finally run by hand, all three exited clean.)
BACKOFF_BASE="${PULSE_BACKOFF_BASE:-3600}"    # first hold: 1h
BACKOFF_MAX="${PULSE_BACKOFF_MAX:-86400}"     # never wait longer than a day to re-probe

NOW=$(date +%s)
TS=$(date '+%Y-%m-%d %H:%M:%S')
MODE="${1:-run}"   # run | --status

log() { echo "[$TS] pulse: $*"; }

# ── State helpers (machine-local JSON: { "job_name": last_run_epoch }) ────────
[ -f "$STATE" ] || echo '{}' > "$STATE" 2>/dev/null

get_last() {
  python3 -c "import json,sys
try:
    print(json.load(open('$STATE')).get('''$1''',0))
except Exception:
    print(0)" 2>/dev/null || echo 0
}

set_last() {
  python3 -c "import json
try:
    d=json.load(open('$STATE'))
except Exception:
    d={}
d['''$1''']=$NOW
json.dump(d,open('$STATE','w'))" 2>/dev/null
}

# Generic numeric state accessors for the circuit breaker (keys: fails:<name>, disabled:<name>).
get_state() {   # get_state <key> <default>
  python3 -c "import json
try:
    d=json.load(open('$STATE'))
except Exception:
    d={}
print(d.get('''$1''',$2))" 2>/dev/null || echo "$2"
}
set_state() {   # set_state <key> <int-value>
  python3 -c "import json
try:
    d=json.load(open('$STATE'))
except Exception:
    d={}
d['''$1''']=$2
json.dump(d,open('$STATE','w'))" 2>/dev/null
}

# get_park_retry <job> -> retry_at epoch, or 0 if not durably parked. Reads PARK_FILE ONLY (never
# STATE) — this is the one check that must survive a wiped /tmp. Fails open to 0 (= not parked) on a
# missing/corrupt/unset file: absence is never read as permission to stay off.
get_park_retry() {
  [ -n "$PARK_FILE" ] || { echo 0; return; }
  python3 -c "import json
try:
    d=json.load(open('$PARK_FILE'))
    print(int(d.get('''$1''',0)))
except Exception:
    print(0)" 2>/dev/null || echo 0
}

# ── Internal builtins (referenced from config with a leading @) ───────────────
# @trim_md_days <file> <days>  — drop '## YYYY-MM-DD' sections older than cutoff
# @find_delete  <dir>  <days>  — delete *.jsonl under dir older than N days
run_builtin() {
  local verb="$1"; shift
  case "$verb" in
    @trim_md_days)
      local file="$1" days="$2"
      [ -f "$file" ] || { log "  builtin @trim_md_days: $file not found, skip"; return 0; }
      local cutoff
      cutoff=$(date -v-"${days}"d '+%Y-%m-%d' 2>/dev/null || date -d "-${days} days" '+%Y-%m-%d' 2>/dev/null) || return 0
      local tmp="${file}.pulse.tmp"
      awk -v cutoff="$cutoff" '
        /^## [0-9]{4}-[0-9]{2}-[0-9]{2}/ {
          d=$2; keep=(d >= cutoff)
        }
        # lines before the first dated section (title/preamble) are always kept
        !seen_section && /^## [0-9]{4}-[0-9]{2}-[0-9]{2}/ { seen_section=1 }
        { if (!seen_section || keep) print }
      ' "$file" > "$tmp" 2>/dev/null && mv "$tmp" "$file"
      log "  builtin @trim_md_days: trimmed $file to >= $cutoff"
      ;;
    @find_delete)
      local dir="$1" days="$2"
      [ -d "$dir" ] || { log "  builtin @find_delete: $dir not found, skip"; return 0; }
      local n
      n=$(find "$dir" -name '*.jsonl' -type f -mtime +"$days" 2>/dev/null | wc -l | tr -d ' ')
      find "$dir" -name '*.jsonl' -type f -mtime +"$days" -delete 2>/dev/null
      log "  builtin @find_delete: removed $n file(s) older than ${days}d in $dir"
      ;;
    *)
      log "  builtin: unknown verb '$verb', skip"
      ;;
  esac
}

trim() { echo "$1" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'; }

# ── Main: parse ```jobs block, dispatch due jobs ──────────────────────────────
if [ ! -f "$CONFIG" ]; then
  log "config not found: $CONFIG — nothing to do (this is expected on a fresh clone before any job is defined)"
  exit 0
fi

log "heartbeat (config=$CONFIG state=$STATE root=${NOTES_ROOT:-NOT-SET})"

ran=0; skipped=0; failed=0
in_block=0

while IFS= read -r line || [ -n "$line" ]; do
  # Strip a trailing CR: a CRLF-checked-out manifest (Git for Windows' core.autocrlf=true default,
  # or an existing student's checkout predating the .gitattributes pin) defeats the exact string
  # match on the fence lines otherwise, silently parsing 0 rows and exiting 0. See .gitattributes.
  line="${line%$'\r'}"
  if [ "$line" = '```jobs' ]; then in_block=1; continue; fi
  if [ "$in_block" -eq 1 ] && [ "$line" = '```' ]; then in_block=0; continue; fi
  [ "$in_block" -eq 1 ] || continue
  case "$line" in ''|\#*) continue;; esac

  IFS='|' read -r name enabled interval cmd <<< "$line"
  name=$(trim "$name"); enabled=$(trim "$enabled"); interval=$(trim "$interval"); cmd=$(trim "$cmd")
  [ -n "$name" ] || continue

  if [ "$enabled" != "yes" ]; then
    [ "$MODE" = "--status" ] && log "  DISABLED $name"
    continue
  fi

  # Deliberate park: reads PARK_FILE DIRECTLY, never STATE — so this holds even right after a
  # reboot wipes STATE to '{}'. Independent of, and checked BEFORE, the ephemeral breaker below: a
  # human park is never a breaker trip and must never be confused with one going the other direction.
  park_retry=$(get_park_retry "$name")
  if [ "$park_retry" -gt "$NOW" ]; then
    [ "$MODE" = "--status" ] && log "  PARKED   $name (durable park, retry_at=$park_retry)"
    skipped=$((skipped+1)); continue
  fi

  # Circuit breaker: a tripped job is HELD OFF until its backoff expires, then gets one half-open
  # probe. It is never held off permanently — see BACKOFF_BASE above.
  if [ "$(get_state "disabled:$name" 0)" = "1" ]; then
    retry_at=$(get_state "retry_at:$name" 0)
    # A job disabled WITHOUT a retry_at was disabled by something other than this backoff: the
    # pre-backoff breaker semantics, or a HUMAN deliberately parking it (legacy path). Treating a
    # missing retry_at as 0 would make every such job instantly "backoff expired" and half-open on
    # the very next tick — a retry mechanism must never resurrect a deliberate park.
    if [ "$retry_at" -le 0 ]; then
      [ "$MODE" = "--status" ] && log "  PARKED   $name (disabled with no backoff timer — deliberate park or pre-backoff trip; will NOT auto-retry)"
      skipped=$((skipped+1)); continue
    fi
    if [ "$NOW" -lt "$retry_at" ]; then
      [ "$MODE" = "--status" ] && log "  BACKOFF  $name (tripped breaker; re-probes in $(( (retry_at - NOW) / 60 ))min)"
      skipped=$((skipped+1)); continue
    fi
    # Half-open: clear the trip and let this one run decide. Success resets everything below;
    # failure re-trips with the next (doubled) hold.
    set_state "disabled:$name" 0
    log "  HALF-OPEN '$name' — backoff expired, attempting one probe run"
  fi

  last=$(get_last "$name")
  due=0
  if [ $(( NOW - last )) -ge "$interval" ]; then due=1; fi

  if [ "$MODE" = "--status" ]; then
    if [ "$due" -eq 1 ]; then log "  DUE      $name (last=$last interval=${interval}s)"
    else log "  waiting  $name ($(( interval - (NOW - last) ))s remaining)"; fi
    continue
  fi

  if [ "$due" -eq 0 ]; then skipped=$((skipped+1)); continue; fi

  log "running '$name': $cmd"
  # CRITICAL: each job runs with stdin from /dev/null. The job loop reads the config on stdin
  # (`done < "$CONFIG"`); a job that reads stdin would otherwise eat the remaining job lines and
  # silently abort the cycle (only the first jobs run).
  if [ "${cmd:0:1}" = "@" ]; then
    # Re-parse the command string so quoted paths and $VAR are honored. Raw `run_builtin $cmd`
    # would word-split on any space in a path AND never expand a literal $HOME from the config
    # line — `eval set --` expands vars + respects quotes; safe here because the config is trusted
    # (same trust boundary as the bash -c branch below: this file is CODE, not untrusted input).
    eval "set -- $cmd"
    run_builtin "$@" </dev/null
    rc=$?
  else
    bash -c "$cmd" </dev/null
    rc=$?
  fi
  set_last "$name"
  if [ "$rc" -eq 0 ]; then
    ran=$((ran+1)); log "  ok '$name' (rc=0)"
    set_state "fails:$name" 0          # success resets the failure streak (and would clear a trip)
    set_state "disabled:$name" 0       # explicit: a half-open probe that passes fully re-arms the job
    set_state "trips:$name" 0          # and forgets the backoff history, so the next hold starts at BASE
    set_state "retry_at:$name" 0
  elif [ "$rc" -eq 75 ]; then
    # rc=75 = THE JOB DISPATCHED AND THEN DECLINED TO RUN (stood down) — BY ITS OWN PREFLIGHT, not
    # a failure. On the donor system this code meant "not the lead machine"; that condition doesn't
    # exist here, but the CONTRACT is still useful and kept: any job whose own preflight decides not
    # to proceed this tick (e.g. a job that needs credentials nobody has configured yet — see
    # planning-health.py / backlog-health.py, which map a missing config to this exact convention) should
    # use it, so "chose not to run" is never confused with "ran and failed" OR with "ran and
    # succeeded". It maps to `skipped`, never `ran` and never `failed`:
    #   ran    — it did no work; counting it hides a standing-down job behind a healthy number.
    #   failed — standing down on missing config is CORRECT, expected behaviour on a fresh install
    #            and would happen every tick until configured; counting it would trip the 3-strike
    #            breaker and disable the job within 15 minutes of a clean install.
    skipped=$((skipped+1))
    log "  STOOD DOWN '$name' (rc=75) — dispatched, then declined (its own preflight said not yet). Not a fault; not counted as ran."
  elif [ "$rc" -eq 2 ]; then
    # rc=2 = TRANSIENT pre-flight/infra failure (auth blip, network) by runner convention. NOT a
    # real job failure, so it MUST NOT count toward the circuit breaker — a transient that spans a
    # few 5-min ticks would otherwise permanently disable a perfectly healthy job. The streak is
    # held (not incremented, not reset).
    failed=$((failed+1))
    log "  WARN '$name' transient pre-flight failure (rc=2) — NOT counted toward breaker; retry next interval"
  else
    failed=$((failed+1))
    fails=$(( $(get_state "fails:$name" 0) + 1 ))
    set_state "fails:$name" "$fails"
    if [ "$fails" -ge "$MAX_FAILURES" ]; then
      trips=$(( $(get_state "trips:$name" 0) + 1 ))
      set_state "trips:$name" "$trips"
      # doubling hold: BASE, 2xBASE, 4xBASE ... capped at BACKOFF_MAX
      hold="$BACKOFF_BASE"; i=1
      while [ "$i" -lt "$trips" ] && [ "$hold" -lt "$BACKOFF_MAX" ]; do
        hold=$(( hold * 2 )); i=$(( i + 1 ))
      done
      [ "$hold" -gt "$BACKOFF_MAX" ] && hold="$BACKOFF_MAX"
      set_state "disabled:$name" 1
      set_state "retry_at:$name" $(( NOW + hold ))
      set_state "fails:$name" 0        # streak restarts for the next window
      log "  BREAKER TRIPPED '$name' — failed ${fails}x in a row (rc=$rc); holding off $(( hold / 60 ))min (trip #${trips}), then one probe run"
      bash "$CODE_ROOT/shared/notify/notify-send.sh" --source pulse --tags rotating_light \
        --title "Pulse breaker: $name held $(( hold / 60 ))min" \
        --message "$name failed ${fails}x in a row (rc=$rc) — trip #${trips}, re-probing in $(( hold / 60 ))min. Not disabled forever." </dev/null 2>/dev/null || true
    else
      log "  WARN '$name' exited rc=$rc (${fails}/${MAX_FAILURES} fails; will retry next interval)"
    fi
  fi
done < "$CONFIG"

# ── Durable heartbeat mirror (the dead-man's-switch feed; system-health.py reads this) ──────────
# Single machine, single file — no namespacing needed (the donor split this into _pulse-<machine>.json
# because two machines could clobber one shared file; here there is exactly one writer). Atomic; never
# fails the daemon; skipped entirely if no notes root is configured (fresh install, nothing to watch
# yet — system-health.py degrades the same way on the read side).
if [ "$MODE" != "--status" ] && [ -n "$NOTES_ROOT" ]; then
  python3 - "$STATE" "$NOTES_ROOT/state/status" <<'PYEOF' 2>/dev/null
import json, sys, time, os
state_path, out_dir = sys.argv[1], sys.argv[2]
def iso(epoch):
    lt = time.localtime(epoch); off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off
try:
    raw = json.load(open(state_path))
except Exception:
    raw = {}
jobs = {}
for k, v in raw.items():
    if k.startswith("fails:") or k.startswith("disabled:") or k.startswith("trips:") or k.startswith("retry_at:"):
        continue
    try:
        last = int(v)
    except Exception:
        continue
    jobs[k] = {"last_tick": iso(last),
               "consecutive_fails": int(raw.get("fails:" + k, 0)),
               "disabled": bool(raw.get("disabled:" + k, 0))}
out = {"schema_version": 1, "written_at": iso(int(time.time())), "machine": "local", "jobs": jobs}
os.makedirs(out_dir, exist_ok=True)
tmp = os.path.join(out_dir, "_pulse.json") + ".tmp"
json.dump(out, open(tmp, "w"), indent=2)
os.replace(tmp, os.path.join(out_dir, "_pulse.json"))
PYEOF
fi

[ "$MODE" = "--status" ] || log "done — ran=$ran skipped=$skipped failed=$failed"
exit 0
