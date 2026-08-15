#!/usr/bin/env bash
# health-deadman-check.sh — the OUT-OF-BAND watcher for system-health ITSELF.
#
# WHY: system-health.py is the dead-man's-switch that flags any job whose heartbeat goes stale — but
# nothing watches system-health ITSELF. If Pulse wedges or the sweeper dies, its own tile
# (_system-health.json) simply stops refreshing, and the only signal is that file quietly going
# stale — invisible unless someone happens to look. This script is the answer: a SEPARATE scheduled
# entry (never a Pulse job — see below) that checks whether the sweep is still alive and says so
# LOUDLY if it isn't. SILENCE = ALARM.
#
# ⛔ DELIBERATELY NOT A PULSE JOB. If this were dispatched FROM pulse.sh, a wedged Pulse would take
# its own watchdog down with it, and the silence would look exactly like health. It is installed as
# its OWN crontab/Task-Scheduler entry by install-schedulers.sh (see system/pulse-config.md's
# ```crontab``` block) — running independently means it can still notice Pulse going dark.
#
# PORTED (2026-08-14) from claudeops-config's system/tools/health-deadman-check.sh, radically
# simplified. The donor spent roughly two-thirds of this file (its own ~70 lines, plus a fault-ledger
# read) answering "which of my two Macs is the lead, and can I even trust reading that marker off a
# flaky cloud-drive mount" — a whole class of failure (a FUSE mount returning a false-empty read,
# EDEADLK) that a plain local `data/` folder does not have, because there is exactly one machine and
# no marker to race on. That machinery is CUT, not translated — dropping it removes the very failure
# mode it existed to work around. What's kept is the part that still matters on one machine: is the
# health tile still being refreshed, and if not, say so loudly.
#
# Also dropped: the fault-ledger read (`~/.local/state/.../faults.json`) that surfaced jobs dead
# >72h even while the tile itself stayed fresh — that ledger is a DIFFERENT category's object
# (Hospital / SELF-AUDIT) and hasn't landed in this repo. This script's own job is narrower and does
# not need it: "is the sweep itself alive." A future Hospital port can extend this without needing to
# touch the watcher's core contract.
set -uo pipefail

CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
THRESHOLD=2700   # 45 min. system-health runs every 5 min -> 9 consecutive misses = genuinely dead, not a blip.

# ── The notes root ───────────────────────────────────────────────────────────
# Resolved fresh every run, same as every other tool. NOT-SET is a legitimate state on a fresh
# install (nobody has pointed this at a folder yet, or system-health has never run) — there is
# nothing to watch yet, so this exits clean rather than alarming about an absence that is expected.
_ROOT_LINE="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
NOTES_ROOT="${_ROOT_LINE:-}"
if [ -z "$NOTES_ROOT" ]; then
  echo "[health-deadman] no notes root configured yet — nothing to watch. (Run shared/brain_root.py --set <folder> once, or run any tool that asks for it.)"
  exit 0
fi

HEALTH_JSON="$NOTES_ROOT/state/status/_system-health.json"
DEADMAN_TILE="$NOTES_ROOT/state/status/health-deadman.json"
# Machine-local, deliberately NOT in the tracked repo or the notes root: "has this install EVER
# produced a health tile before" — the flag that tells "fresh install, quiet is expected" apart from
# "this used to work and has gone dark," the same distinction the donor's fault-ledger read made,
# reduced here to the smallest thing that can answer it without depending on infrastructure this
# script does not own.
SEEN_MARKER="$HOME/.config/lifehack/health-deadman-seen-alive"

DEADMAN_STATUS="ERROR"   # pessimistic default — if this script dies before a branch below sets it,
DEADMAN_SCANNED=0        # the Hospital finding must read as broken, never as a quiet false-clean.
DEADMAN_SUMMARY="ran; no verdict recorded"

_deadman_on_exit() {
  local rc=$?
  mkdir -p "$(dirname "$DEADMAN_TILE")" 2>/dev/null
  local tmp="${DEADMAN_TILE}.tmp"
  python3 - "$tmp" "$DEADMAN_TILE" "$DEADMAN_STATUS" "$rc" "$DEADMAN_SUMMARY" <<'PYEOF' 2>/dev/null
import json, os, sys, time
tmp, out, status, rc, summary = sys.argv[1:6]
def iso(epoch):
    lt = time.localtime(epoch); off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off
env = {"desk": "system", "schema_version": 2, "pulse_job": "health-deadman", "emit_mode": "manual",
       "stale_after_s": 7800, "last_run": iso(int(time.time())), "rc": int(rc), "status": status,
       "summary": summary}
json.dump(env, open(tmp, "w"), indent=2)
os.replace(tmp, out)
PYEOF
  # Hospital finding — ONE per run, always, so "found nothing wrong" and "did not run" stay
  # distinguishable (the exact ambiguity a scheduled job's silence usually hides). `|| true`: a
  # failed Hospital write must never change this script's own exit code.
  python3 "$CODE_ROOT/system/tools/emit_finding.py" \
    --producer health-deadman --status "$DEADMAN_STATUS" --scanned-n "$DEADMAN_SCANNED" \
    --label job=health-deadman --label check=deadman-liveness \
    --summary "$DEADMAN_SUMMARY" --rc "$rc" >/dev/null 2>&1 || true
  exit "$rc"
}
trap _deadman_on_exit EXIT

SEEN_ALIVE=0
[ -f "$SEEN_MARKER" ] && SEEN_ALIVE=1

if [ ! -f "$HEALTH_JSON" ]; then
  DEADMAN_SCANNED=1
  DEADMAN_SUMMARY="health file MISSING; seen-alive-before=$SEEN_ALIVE"
  if [ "$SEEN_ALIVE" = "1" ]; then
    # A real wedge — this install HAS reported before, and now the tile is simply gone (sweeper
    # wedged, or someone deleted it).
    DEADMAN_STATUS="ERROR"
    bash "$CODE_ROOT/shared/notify/notify-send.sh" --source health-deadman --tags rotating_light --priority critical \
      --title "Health monitor file MISSING" \
      --message "_system-health.json is gone, and this install has reported before — the sweeper is wedged or the tile was deleted. Check the Pulse log + system-health-run.sh." \
      2>/dev/null || true
  else
    # never-seen -> fresh install / system-health has simply never run yet -> silence, by design.
    DEADMAN_STATUS="OK"
    DEADMAN_SUMMARY="health file not present yet — fresh install, nothing has run yet. Not an alarm."
  fi
  exit 0
fi

# First time we've ever SEEN the tile exist — remember it, durably, machine-local.
if [ "$SEEN_ALIVE" = "0" ]; then
  mkdir -p "$(dirname "$SEEN_MARKER")" 2>/dev/null
  date +%s > "$SEEN_MARKER" 2>/dev/null || true
fi

MTIME="$(python3 -c "import os,sys; print(int(os.path.getmtime(sys.argv[1])))" "$HEALTH_JSON" 2>/dev/null || echo 0)"
if [ "$MTIME" -le 0 ]; then
  DEADMAN_STATUS="NEEDS_REVIEW"
  DEADMAN_SCANNED=1
  DEADMAN_SUMMARY="health file exists but its mtime could not be read"
  exit 0
fi

AGE=$(( $(date +%s) - MTIME ))
DEADMAN_SCANNED=1
DEADMAN_SUMMARY="watched: health tile ${AGE}s old (limit ${THRESHOLD}s)"
DEADMAN_STATUS="OK"
if [ "$AGE" -gt "$THRESHOLD" ]; then
  DEADMAN_STATUS="ERROR"
  DEADMAN_SUMMARY="ALARM: health monitor SILENT for $(( AGE / 60 ))min (limit $(( THRESHOLD / 60 ))min)"
  bash "$CODE_ROOT/shared/notify/notify-send.sh" --source health-deadman --tags rotating_light --priority critical \
    --title "Health monitor SILENT" \
    --message "system-health has not emitted in $(( AGE / 60 ))min — Pulse or the sweeper may be wedged. Check the Pulse log + system-health-run.sh." \
    2>/dev/null || true
fi
exit 0
