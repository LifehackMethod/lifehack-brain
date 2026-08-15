#!/usr/bin/env bash
# install-schedulers.sh — replay the schedule from the VERSIONED manifest (pulse-config.md) onto
# THIS machine's OS scheduler. This is what makes the schedule edit-once-and-run-everywhere: update
# the ```crontab``` block in pulse-config.md -> commit -> run this on a machine -> that machine is
# current. No hand-editing crontab, one declaration per job, no duplication.
#
# PORTED (2026-08-14) from claudeops-config's system/tools/install-schedulers.sh, under a 2026-08-13
# product ruling ("automation ships with its scheduler — if it ran on the donor author's laptop, it
# goes on a student's laptop"). The donor script only ever wrote a macOS/Linux crontab; this product's own
# INSTALL.md explicitly walks Windows students through a real install (Step 1's own rule: "Darwin
# means a Mac. Linux means Linux. Anything else, treat it as Windows.") — and Windows has no cron.
# That branch below is NEW DESIGN, not a port: no file in the donor answers "what does a Windows
# install need," because every install target there was implicitly a Mac.
#
# ⛔ A38, ADDRESSED DIRECTLY (found in the donor's own dead-end record, `system/sops/skill-building-
# sop.md:1207` / `records/logs/2026-05-26-cross-machine-sync-infrastructure.md`): launchd was tried
# for scheduled jobs once already and FAILED — "blocked by macOS Full Disk Access — 'Operation not
# permitted' on the Drive path" — and the donor system reverted to cron for exactly that reason.
# ⇒ CRON, NOT LAUNCHD, on Mac — but not by reflexively copying that outcome forward. A38's failure
# was specific to a job whose DATA PATH lived on a Google-Drive FUSE mount, which is what tripped
# TCC/Full-Disk-Access. This product's own INSTALL.md Step 4 now REFUSES to install into a
# Drive/Dropbox/OneDrive/iCloud folder at all (fire-tested 13/13, symlink bypass closed) — so the
# precondition that caused A38 cannot occur here; a student's data path is always a plain local
# folder, which launchd CAN read. A38 does not bind this decision. The reasons cron still won:
#   1. Windows already forces a THIRD mechanism (Task Scheduler, below) that neither cron nor
#      launchd covers — adding launchd as a mac-only FOURTH mechanism buys no cross-platform
#      unification; cron+schtasks already covers Mac+Linux+Windows with two.
#   2. The donor repo's `system/sops/cron-safety.md` documents cron's real quirks (its minimal PATH,
#      the /usr/sbin gap) from lived incidents — ⚠ VERIFIED THIS SESSION: that SOP has NOT been
#      ported to this repo yet (no `system/sops/cron-safety.md` here — it belongs to a different
#      migration category, not this one). Naming it here as a reason to prefer cron over an
#      unexplored launchd integration is directional, not a claim that the safety net already
#      exists in THIS repo — the PATH= prefix on the crontab lines below (mirroring that SOP's own
#      fix) is what actually carries the lesson forward until the doc itself lands.
#   3. Idempotent re-install is simpler for cron: ONE owned marked region in `crontab -l` (below),
#      vs juggling N per-job `.plist` files plus `launchctl load`/`unload` state. The donor's own
#      launchd block was never more than a straight copy of static plists — it never had to solve
#      the idempotent-diff problem cron's marked-region approach already solves cleanly here.
#
# ⭐ WHAT THIS MEANS FOR VERIFICATION — read together with A38's other half, the "printed PASSED for
# two months and wrote nothing" failure class this whole project is built to catch. A scheduler that
# REGISTERS successfully but is silently denied at FIRE time (permission, a wrong path, anything)
# would look identical to a healthy install if the only check is "is the crontab entry there." It is
# NOT the only check here: the proof this design relies on is downstream of the scheduler entirely —
# each job's OWN tile write (state/status/<job>.json, produced by that job's REAL work, not by this
# installer) and `health-deadman-check.sh` watching for that tile going stale. If cron itself were
# silently blocked, tiles would stop refreshing and the deadman would flag it within 45 minutes —
# UNLESS the deadman's OWN cron entry is equally blocked, which this design cannot rule out by
# construction (there is no second, independent watcher of the watcher here). That residual gap is
# named, not hidden: `--install`'s own success message below tells you how to verify EXECUTION, not
# just registration, precisely because `crontab -l` succeeding proves nothing about whether the job
# ever actually fires.
#
# THE DECISION, AND WHY: pulse.sh itself stays a Bash script rather than being rewritten in Python.
# Two things made that the smaller, safer move, not a bigger one:
#   1. Every job pulse.sh dispatches is ALSO a Bash script (system-health-run.sh, planning-health.py
#      launched via python3, etc.) — a Windows install already needs a working `bash` to run those,
#      independent of what runs the dispatcher itself. INSTALL.md's own Step 2 GUARANTEES Git Bash
#      is present on Windows (it installs Git for Windows via winget specifically so `bash` exists),
#      so that dependency is already paid for. Rewriting only pulse.sh in Python would remove Bash
#      from ONE call site while every job it dispatches still needs it — no real reduction in what a
#      Windows student's machine must have working.
#   2. pulse.sh's breaker/backoff/park-file state machine is proven (see that file's own header) —
#      re-deriving it in a second language is exactly the kind of behavioural-regression risk
#      port-manifest-04's own landmine list warns about, for a benefit (avoiding Git Bash) that
#      doesn't materialize per point 1.
#   ⇒ The generalization is in THIS file (how the dispatcher gets invoked on a schedule), not in
#     pulse.sh (what invokes it). Mac/Linux: crontab runs `bash pulse.sh` directly. Windows: Task
#     Scheduler runs Git Bash's `bash.exe pulse.sh` — same script, different trigger.
#
# ⛔ NOT PORTED, ON PURPOSE: the donor's `launchd` block (bootstrap/Supabase plists) and the
# lead-machine gate that stripped the manifest down to "rows for THIS machine". Neither concept
# exists here — this repo has one machine (docs/data-layout.md: "the two-machine plane is not part
# of this system") and nothing in this category's job list needs launchd specifically (the donor's
# own reasoning for needing it — a launchd agent cannot read a FUSE-mounted cloud-drive folder — does
# not apply to a plain local `data/` folder). If a future job genuinely needs launchd, that is new
# scope for whoever adds it, not a gap in this installer.
#
# Reads the ```crontab``` fenced block in pulse-config.md: `name | schedule(cron 5-field) | command`.
# Every row is installed (single machine — there is no `machine` column to filter on anymore).
#
# Usage:
#   install-schedulers.sh              # DRY-RUN (default, safe): print what it WOULD install
#   install-schedulers.sh --install    # actually install it
set -uo pipefail

CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="${PULSE_CONFIG:-$CODE_ROOT/system/pulse-config.md}"
MODE="${1:---dry-run}"
BEGIN="# >>> LIFEHACK SCHEDULERS (managed by install-schedulers.sh — do not edit by hand) >>>"
END="# <<< LIFEHACK SCHEDULERS <<<"
PULSE_SH="$CODE_ROOT/system/tools/pulse.sh"

[ -f "$MANIFEST" ] || { echo "[install-schedulers] FATAL: manifest not found: $MANIFEST" >&2; exit 1; }

trim() { local s="$1"; s="${s#"${s%%[![:space:]]*}"}"; s="${s%"${s##*[![:space:]]}"}"; printf '%s' "$s"; }

# ── 1) OS detection — THE SAME RULE this product's own INSTALL.md states to a human installer
# (Step 1: "Darwin means a Mac. Linux means Linux. Anything else, treat it as Windows.") — one rule,
# stated once, followed by both the human-facing doc and this script. ──────────────────────────────
_UNAME="$(uname -s 2>/dev/null || true)"
case "$_UNAME" in
  Darwin) OS="mac" ;;
  Linux)  OS="linux" ;;
  *)      OS="windows" ;;   # includes MSYS/MINGW/CYGWIN (Git Bash) and a bare uname failure
esac
# TEST-ONLY override — there is no Windows box in this build environment, so the Windows branch is
# verified by forcing this rather than by claiming it works unread. Never set outside a test.
OS="${LIFEHACK_TEST_OS_OVERRIDE:-$OS}"

# ── 2) Parse the ```crontab``` block → [(name, schedule, command)] ─────────────────────────────
declare -a JOB_NAMES=() JOB_SCHEDS=() JOB_CMDS=()
in=0
while IFS= read -r line || [ -n "$line" ]; do
  if [ "$line" = '```crontab' ]; then in=1; continue; fi
  if [ "$in" -eq 1 ] && [ "$line" = '```' ]; then in=0; continue; fi
  [ "$in" -eq 1 ] || continue
  case "$line" in ''|\#*) continue;; esac
  IFS='|' read -r name sched cmd <<< "$line"
  name="$(trim "$name")"; sched="$(trim "$sched")"; cmd="$(trim "$cmd")"
  [ -n "$name" ] || continue
  # ⚠ LITERAL TEXT SUBSTITUTION, not shell expansion. These crontab-block rows run OUTSIDE this
  # process (as independent OS-scheduled entries) and can never inherit an `export` from here — a
  # crontab line of the shape `VAR=val bash "$VAR/x"` does NOT do what it looks like it does: the
  # outer shell expands "$VAR" in the argument word BEFORE the same-line prefix assignment takes
  # effect, so it silently resolves to empty (measured: `LIFEHACK_CODE_ROOT=/x bash
  # "$LIFEHACK_CODE_ROOT/pulse.sh"` fails with "bash: /pulse.sh: No such file or directory" — the
  # leading slash is the tell). pulse.sh's OWN jobs (the ```jobs``` block, dispatched at runtime via
  # a plain `export` as a separate statement, then a separate `bash -c "$cmd"`) don't have this
  # problem — only these OS-level rows do. Fixed here, once, by baking in the real resolved path.
  cmd="${cmd//\$LIFEHACK_CODE_ROOT/$CODE_ROOT}"
  JOB_NAMES+=("$name"); JOB_SCHEDS+=("$sched"); JOB_CMDS+=("$cmd")
done < "$MANIFEST"

if [ "${#JOB_NAMES[@]}" -eq 0 ]; then
  echo "[install-schedulers] no rows in the \`\`\`crontab\`\`\` block of $MANIFEST — nothing to install." >&2
  exit 0
fi

echo "[install-schedulers] detected OS: $_UNAME -> $OS"
echo "[install-schedulers] ${#JOB_NAMES[@]} scheduled entr$([ "${#JOB_NAMES[@]}" -eq 1 ] && echo y || echo ies) in the manifest."

# ── 3a) Mac / Linux — crontab ───────────────────────────────────────────────────────────────────
install_mac_linux() {
  if ! command -v crontab >/dev/null 2>&1; then
    # LANDMINE the donor script never checked: a bare `crontab -` on a system with no cron binary
    # exits non-zero but the donor didn't look — it would have reported success anyway. Refuse
    # loudly instead of guessing this ever works.
    echo "[install-schedulers] FATAL: no 'crontab' binary found on PATH. This machine (uname=$_UNAME)" >&2
    echo "  claims to be Mac/Linux but has no cron. Nothing was installed. If this is a minimal" >&2
    echo "  container/server image, install a cron package (e.g. 'cronie' or 'cron') and re-run." >&2
    exit 1
  fi

  local region_body=""
  local i
  for i in "${!JOB_NAMES[@]}"; do
    region_body+="${JOB_SCHEDS[$i]} ${JOB_CMDS[$i]}"$'\n'
  done
  local region="$BEGIN"$'\n'"$region_body$END"

  local existing stripped
  existing="$(crontab -l 2>/dev/null || true)"
  # strip the old managed region (exact-line awk match — robust against the marker's special chars)
  stripped="$(printf '%s\n' "$existing" | awk -v b="$BEGIN" -v e="$END" '
    $0==b {skip=1; next} $0==e {skip=0; next} !skip {print}')"
  # absorb any pre-existing standalone lines for the runners THIS installer owns, so re-running
  # after a manual edit doesn't duplicate them.
  local rn
  for rn in pulse.sh health-deadman-check.sh; do
    stripped="$(printf '%s\n' "$stripped" | grep -vF "$rn" || true)"
  done
  stripped="$(printf '%s\n' "$stripped" | sed '/^[[:space:]]*$/d')"   # drop blank lines
  local newcron="$stripped"$'\n'"$region"

  if [ "$MODE" = "--install" ]; then
    mkdir -p "$HOME/.config/lifehack/crontab-backups"
    local bk="$HOME/.config/lifehack/crontab-backups/crontab.$(date +%Y%m%d-%H%M%S).bak"
    printf '%s\n' "$existing" > "$bk"
    printf '%s\n' "$newcron" | crontab -
    echo "[install-schedulers] CRONTAB installed (backup: $bk)."
    echo "[install-schedulers] REGISTRATION check (proves the entry exists, NOT that it will fire): crontab -l"
    echo "[install-schedulers] REAL verification (proves it actually RAN — do this in ~10 min): "
    echo "  bash system/tools/pulse.sh --status   # shows DUE/waiting per job, no side effects"
    echo "  then check a tile's own last_run, e.g.: cat <your notes folder>/state/status/sentinel.json"
    echo "  A fresh last_run there was written by that job's REAL work — a registered-but-silently-"
    echo "  denied cron entry (the A38 failure class) would leave that timestamp stuck, not fake-fresh."
  else
    echo "[install-schedulers] CRONTAB dry-run (re-run with --install to apply):"
    echo "----------------------------------------------------------------------"
    printf '%s\n' "$newcron"
    echo "----------------------------------------------------------------------"
  fi
}

# ── 3b) Windows — Task Scheduler via Git Bash ───────────────────────────────────────────────────
# schtasks.exe is a native Windows binary and is reachable from Git Bash's PATH (it lives in
# C:\Windows\System32, which Windows always puts on PATH, and Git Bash inherits the Windows PATH).
# The task's own ACTION must be an absolute WINDOWS-style path — Task Scheduler does not understand
# POSIX paths like /usr/bin/bash or /c/Users/<name>/... — so both bash.exe and pulse.sh's own path are
# converted with `cygpath -w`, which Git for Windows ships specifically for this.
_win_path() { cygpath -w "$1" 2>/dev/null; }   # POSIX path -> "C:\..." ; empty on failure

_resolve_bash_exe() {
  local cand
  cand="$(command -v bash 2>/dev/null || true)"
  if [ -n "$cand" ]; then
    _win_path "$cand" && return 0
  fi
  # Known default Git-for-Windows install locations, in case PATH resolution above failed for some
  # reason (e.g. invoked from a non-Git-Bash shell that still has bash.exe on disk).
  local guess
  for guess in "/c/Program Files/Git/bin/bash.exe" "/c/Program Files (x86)/Git/bin/bash.exe"; do
    if [ -f "$guess" ]; then _win_path "$guess"; return 0; fi
  done
  return 1
}

# A DELIBERATELY SMALL cron-schedule -> schtasks translator: it understands exactly the two shapes
# this manifest actually uses (`*/N * * * *` = every N minutes; `M * * * *` = once an hour, minute
# M) and refuses anything else rather than guessing a wrong schedule. Prints schtasks /SC + /MO (+
# /ST for the hourly form) args on stdout, or nothing + returns 1 if the shape is unrecognized.
_cron_to_schtasks() {
  local sched="$1" minute hour
  minute="$(echo "$sched" | awk '{print $1}')"
  hour="$(echo "$sched" | awk '{print $2}')"
  if [[ "$minute" =~ ^\*/([0-9]+)$ ]] && [ "$hour" = "*" ]; then
    echo "/SC MINUTE /MO ${BASH_REMATCH[1]}"
    return 0
  fi
  if [[ "$minute" =~ ^[0-9]+$ ]] && [ "$hour" = "*" ]; then
    printf '/SC HOURLY /MO 1 /ST 00:%02d:00\n' "$minute"
    return 0
  fi
  return 1
}

install_windows() {
  local bash_win
  if ! bash_win="$(_resolve_bash_exe)" || [ -z "$bash_win" ]; then
    echo "[install-schedulers] FATAL: could not find Git Bash's bash.exe (tried PATH + the two" >&2
    echo "  standard Git-for-Windows install locations). Task Scheduler needs an absolute .exe" >&2
    echo "  path — it cannot run a POSIX script directly. Install Git for Windows (INSTALL.md" >&2
    echo "  Step 2 covers this), then re-run." >&2
    exit 1
  fi
  local pulse_win
  pulse_win="$(_win_path "$PULSE_SH")"
  if [ -z "$pulse_win" ]; then
    echo "[install-schedulers] FATAL: could not resolve a Windows path for $PULSE_SH (cygpath failed)." >&2
    exit 1
  fi

  local i name sched cmd schtasks_args task_name log_win
  for i in "${!JOB_NAMES[@]}"; do
    name="${JOB_NAMES[$i]}"; sched="${JOB_SCHEDS[$i]}"; cmd="${JOB_CMDS[$i]}"
    task_name="Lifehack-$(echo "$name" | sed -E 's/[^A-Za-z0-9]+/-/g')"
    if ! schtasks_args="$(_cron_to_schtasks "$sched")"; then
      echo "[install-schedulers] SKIP '$name' — schedule '$sched' isn't one of the two shapes this" >&2
      echo "  installer understands (*/N * * * * or M * * * *). Add it to Windows Task Scheduler" >&2
      echo "  by hand, or extend _cron_to_schtasks() in this script." >&2
      continue
    fi
    # ⚠ Every job's OWN command (from the manifest) is a *nix-shaped Bash command string
    # (e.g. `bash "<path>/system-health-run.sh"`) — it runs UNCHANGED, inside the bash.exe process
    # Task Scheduler launches, exactly the same string pulse.sh's own `bash -c "$cmd"` would run on
    # Mac/Linux. Only the ENTRY POINT (what Task Scheduler itself invokes) differs by OS: here it is
    # `bash.exe "<pulse.sh-win-path>"`, not the manifest command directly — pulse.sh is always the
    # thing the scheduler calls; pulse.sh is what parses the ```jobs``` block and runs each job's
    # own command in turn. This crontab-block row IS pulse.sh's own entry for the `pulse` name (and
    # health-deadman's dedicated entry) — see pulse-config.md.
    local action="\"$bash_win\" \"$pulse_win\""
    if [ "$name" != "pulse" ]; then
      # health-deadman (and any future non-Pulse crontab row) runs its OWN command directly, not
      # through pulse.sh — same distinction the manifest draws between the ```jobs``` block (Pulse-
      # dispatched) and the ```crontab``` block (OS-dispatched).
      action="\"$bash_win\" -c \"$cmd\""
    fi
    if [ "$MODE" = "--install" ]; then
      # shellcheck disable=SC2086
      schtasks /Create $schtasks_args /TN "$task_name" /TR "$action" /F
      echo "[install-schedulers] installed Windows Task Scheduler entry '$task_name' ($schtasks_args)."
    else
      echo "[install-schedulers] WOULD RUN: schtasks /Create $schtasks_args /TN \"$task_name\" /TR $action /F"
    fi
  done
  if [ "$MODE" != "--install" ]; then
    echo "[install-schedulers] Windows dry-run (re-run with --install to apply)."
  else
    echo "[install-schedulers] REGISTRATION check (proves the task exists, NOT that it will fire): schtasks /Query /TN Lifehack-Pulse"
    echo "[install-schedulers] REAL verification (proves it actually RAN — do this in ~10 min): "
    echo "  bash pulse.sh --status   # from Git Bash, in this repo's system/tools/"
    echo "  then check a tile's own last_run under your notes folder's state/status/ — see the"
    echo "  Mac/Linux branch's identical note above for why registration alone is not proof."
  fi
}

case "$OS" in
  mac|linux) install_mac_linux ;;
  windows)   install_windows ;;
esac
