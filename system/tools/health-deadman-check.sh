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
# read) answering "which of two machines is the lead, and can I even trust reading that marker off a
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
#
# ⚠ T10.A3 OL-N1 ②, CORRECTING THE ABOVE: this script WAS calling notify-send.sh unconditionally,
# every single run, for as long as the ERROR condition held — measured live: 46 sends in 46 hours
# (hourly cron, every run in-fault fired). `~/.local/state/claudeops/faults.json` (this repo's own
# equivalent: `~/.config/lifehack/faults.json`, via `shared/fault_ledger.py` below) carried ZERO
# `health-deadman` keys, because nothing here ever wrote to it — the "24h gate" the org map
# describes was never wired to THIS caller. `system/tools/fault_ledger.py` was ported
# correct-and-callable (its own docstring says so) but nothing called `record_faults()` on a
# cadence — this is that missing call. From now on: an ERROR condition alerts on the EDGE (first
# time it's newly true — a human should hear about a new outage immediately) and then only once
# per `fault_ledger.ESCALATE_AFTER_S`/`RE_ALERT_EVERY_S` (24h/24h) after that, using
# `fault_ledger.due_for_escalation()` — the exact mechanism the ledger was built for. Recovery
# (condition clears) reaps the row via `record_faults(..., active=[])`, so a NEW outage after a
# recovery is correctly treated as new, not as a stale escalation timer.
set -uo pipefail

CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
THRESHOLD=2700   # 45 min. system-health runs every 5 min -> 9 consecutive misses = genuinely dead, not a blip.

# ── Hook-plane regression guard (D1, found+fixed 2026-08-30) ─────────────────────────────────
# WHY THIS LIVES HERE, NOT smoke-check.sh: smoke-check.sh is manual-only (grep of
# system/pulse-config.md turns up no scheduled entry for it) — a defect it would catch sits
# uncaught until a human happens to run it. This script is the one thing on this install that
# genuinely runs UNATTENDED on its own crontab entry, independent of Pulse (see file header) —
# the only home that actually re-checks this every hour with nobody watching.
#
# THE DEFECT THIS CATCHES: core.hooksPath is LOCAL git config (.git/config), never committed and
# never shared. Set to a RELATIVE path ("system/githooks"), git resolves it against EACH
# WORKTREE'S OWN toplevel — so a worktree checked out at a commit that predates a hook's
# introduction has that hook simply MISSING on disk there, and git treats a missing hook as a
# SILENT NO-OP: no error, no output, the push just goes through unguarded. A fresh clone or a new
# machine that never runs the one-time absolute-path fix reopens this hole with zero symptoms.
# Fix applied on this machine: `git config core.hooksPath <absolute path>/system/githooks`.
_check_hooks_path() {
  local hp
  hp="$(git -C "$CODE_ROOT" config --get core.hooksPath 2>/dev/null || true)"
  if [ -z "$hp" ]; then
    echo "[health-deadman] core.hooksPath is UNSET — git falls back to .git/hooks, NOT this repo's tracked pre-push/pre-commit. Tracked hooks (including the public-push gate) will NOT run." >&2
    return 1
  fi
  case "$hp" in
    /*) ;;  # absolute — resolves the same regardless of which worktree/commit is checked out. Fine.
    *)
      echo "[health-deadman] core.hooksPath is RELATIVE ('$hp') — resolves against EACH WORKTREE'S OWN toplevel. A worktree checked out at a commit predating a hook's introduction will silently be missing it, and git fails OPEN (no error). Fix: git config core.hooksPath <absolute path to this repo>/system/githooks" >&2
      return 1
      ;;
  esac
  if [ ! -x "$hp/pre-push" ]; then
    echo "[health-deadman] pre-push is not resolvable/executable at '$hp/pre-push' — the public-push gate cannot fire. FAIL." >&2
    return 1
  fi
  return 0
}

if ! _check_hooks_path; then
  bash "$CODE_ROOT/shared/notify/notify-send.sh" --source health-deadman --tags rotating_light --priority critical \
    --identity "health-deadman-hookspath" \
    --title "core.hooksPath regression — push gate may be fail-OPEN" \
    --message "core.hooksPath is unset/relative, or pre-push is unresolvable from $CODE_ROOT. The public-push gate may not fire from every worktree. Fix: git config core.hooksPath <absolute path>/system/githooks, then re-run this check." \
    2>/dev/null || true
  echo "[health-deadman] HOOKSPATH CHECK FAILED — see message above. Not overriding the health-tile watch below; both conditions are reported independently." >&2
  HOOKSPATH_BAD=1
else
  HOOKSPATH_BAD=0
fi

# ── OL-N1 ② gate: should THIS run actually alert, given the ledger's edge+24h-escalation rule? ──
# args: <state: "missing"|"silent"|""(=healthy, clears both)>
# Prints "1" (alert now) or "0" (stay quiet — already alerted, not yet due to escalate), and
# durably records the fault's presence/absence either way. Best-effort: any failure here degrades
# to "1" (alert) — a ledger outage must never be the reason a genuine dead-man goes silent.
_deadman_gate() {
  local state="$1"
  python3 - "$CODE_ROOT" "$state" <<'PYEOF' 2>/dev/null || echo 1
import sys, time
code_root, state = sys.argv[1], sys.argv[2]
sys.path.insert(0, f"{code_root}/system/tools")
import fault_ledger as FL

JOB = "health-deadman"
now = time.time()
d = FL.load()
active = [(JOB, state)] if state else []
was_active = FL.key(JOB, state) in d["faults"] if state else False
d = FL.record_faults(d, active, now)
should_alert = False
if state:
    if not was_active:
        should_alert = True                      # edge: newly in fault -> alert immediately
    elif FL.due_for_escalation(d, JOB, state, now):
        should_alert = True                      # >=24h old AND >=24h since last alert
    if should_alert:
        FL.mark_alerted(d, JOB, state, now)
FL.save(d)
print(1 if should_alert else 0)
PYEOF
}

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
  # Fold the hooksPath regression guard into this run's verdict: a broken push gate is at least
  # as urgent as a stale health tile, and must not be silently overridden by an otherwise-healthy
  # exit 0 from the tile-watching logic below.
  if [ "${HOOKSPATH_BAD:-0}" = "1" ]; then
    [ "$rc" -eq 0 ] && rc=1
    DEADMAN_STATUS="ERROR"
    DEADMAN_SUMMARY="$DEADMAN_SUMMARY | ALSO: core.hooksPath regression detected — see stderr above"
  fi
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
    if [ "$(_deadman_gate missing)" = "1" ]; then
      bash "$CODE_ROOT/shared/notify/notify-send.sh" --source health-deadman --tags rotating_light --priority critical \
        --identity "health-deadman-missing" \
        --title "Health monitor file MISSING" \
        --message "_system-health.json is gone, and this install has reported before — the sweeper is wedged or the tile was deleted. Check the Pulse log + system-health-run.sh." \
        2>/dev/null || true
    fi
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
  if [ "$(_deadman_gate silent)" = "1" ]; then
    bash "$CODE_ROOT/shared/notify/notify-send.sh" --source health-deadman --tags rotating_light --priority critical \
      --identity "health-deadman-silent" \
      --title "Health monitor SILENT" \
      --message "system-health has not emitted in $(( AGE / 60 ))min — Pulse or the sweeper may be wedged. Check the Pulse log + system-health-run.sh." \
      2>/dev/null || true
  fi
else
  _deadman_gate "" >/dev/null   # healthy: reap any previously-active fault row (self-heal)
fi
exit 0
