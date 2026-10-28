#!/usr/bin/env bash
# mirror-fetch-run.sh — the scheduled fetch that keeps mirror_line.sh's "behind" figure honest.
#
# WHY THIS EXISTS (M14, 2026-09-08): mirror_line.sh (M9/M13) reads only local refs and never
# fetches — correctly, since a session-start line must not touch the network. That means it can
# only ever SEE "behind" if something else fetched first. Nothing did, so `fetch.prune=true`
# (M6) fired only on a fetch that never ran, and `main` drifted 12 commits behind `origin/main`
# for days without any tool noticing. This job is that "something else."
#
# FETCH ONLY. Never pull, never merge, never checkout, never touch a working tree or a local
# branch — it updates remote-tracking refs (`refs/remotes/origin/*`) and nothing else. §9: a
# REPORT, not a gate.
#
# Runs against ITS OWN clone (the one this script lives inside, via CODE_ROOT) — the shape that
# generalizes to every student's single clone. Verified separately against a second clone by hand
# (see the M14 commit message) to prove the logic is not accidentally specific to one repo.
set -uo pipefail
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

JOB="mirror-fetch"
# Single-instance lock, inline (5.7): this job needs nothing from ingest-run.lib.sh but its lock, and that library
# carries the Gmail pre-flight, which the door (install-schedulers.sh --check-row) refuses to see inside a job that
# never touches Gmail. Contention is a STAND-DOWN (75), never exit 0 — exit 0 on a skip is the [F2] shape.
LOCKDIR="${LIFEHACK_RUNNER_LOCK_ROOT:-/tmp}/claudeops-${JOB}.lock"
. "$CODE_ROOT/system/tools/runner-lock.lib.sh" || { echo "FATAL: cannot source runner-lock.lib.sh" >&2; exit 1; }
# 5.9(h): the lock records its owner pid. A dead owner's lock is taken at once; a LIVE owner is a stand-down (75), never a 0;
# a lock that is present but unreadable is refused and named (1).
runner_lock_acquire "$LOCKDIR" 1500 "$JOB" || exit $?
trap 'rm -rf "$LOCKDIR" 2>/dev/null' EXIT

GIT_BIN="$(command -v git 2>/dev/null)"
if [ -z "$GIT_BIN" ]; then
  echo "[$JOB] git not found — infra condition, standing down this tick."
  exit 2
fi

if ! "$GIT_BIN" -C "$CODE_ROOT" rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "[$JOB] $CODE_ROOT is not a git repo — infra condition, standing down this tick."
  exit 2
fi

# ── the only network call in this whole job ──────────────────────────────────────────
if ! "$GIT_BIN" -C "$CODE_ROOT" fetch origin --prune 2>&1; then
  echo "[$JOB] fetch failed (network blip / auth hiccup) — held, not a real failure."
  RC=2
else
  RC=0
fi

# ── measure, only if the fetch actually ran. rev-list --left-right prints TAB-separated
#    "<behind> <ahead>" — read splits on any IFS whitespace, tab included. ──────────────
BEHIND=""
AHEAD=""
if [ "$RC" -eq 0 ]; then
  # Which pair to measure (5.7): the branch this clone is ON against its upstream; if it has none, origin/<branch>;
  # if that does not exist, the original origin/main...main. A clone with no local `main` (the V2 sandbox) used to read
  # "?" here and could never pass the row's check.
  _BR="$("$GIT_BIN" -C "$CODE_ROOT" symbolic-ref --quiet --short HEAD 2>/dev/null)"
  _UP="$("$GIT_BIN" -C "$CODE_ROOT" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)"
  if [ -z "$_BR" ]; then _BR="main"; _UP="origin/main"
  elif [ -z "$_UP" ] && "$GIT_BIN" -C "$CODE_ROOT" rev-parse --verify --quiet "refs/remotes/origin/$_BR" >/dev/null 2>&1; then _UP="origin/$_BR"
  elif [ -z "$_UP" ]; then _BR="main"; _UP="origin/main"; fi
  COUNTS="$("$GIT_BIN" -C "$CODE_ROOT" rev-list --left-right --count "$_UP...$_BR" 2>/dev/null)"
  read -r BEHIND AHEAD <<EOF_COUNTS
$COUNTS
EOF_COUNTS
  case "$BEHIND" in ''|*[!0-9]*) BEHIND="" ;; esac
  case "$AHEAD" in ''|*[!0-9]*) AHEAD="" ;; esac
fi

# ── SUCCESS RECEIPT (self-monitoring 5.7): the row's output check reads this file. Written ONLY when the fetch
#    succeeded (RC=0) — a held fetch, a lock skip or a skipped run leaves the old file, which is not newer than the run
#    start, so the check fails honestly. The counts are "?" if rev-list could not be read, which the check refuses. ──
if [ "$RC" -eq 0 ]; then
  _RCPT_DIR="$HOME/.config/lifehack/$JOB"
  mkdir -p "$_RCPT_DIR" || echo "[$JOB] WARN: cannot create $_RCPT_DIR" >&2
  printf '%s DONE behind=%s ahead=%s %s\n' "$JOB" "${BEHIND:-?}" "${AHEAD:-?}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    > "$_RCPT_DIR/last-ok" || echo "[$JOB] WARN: receipt write failed — the row check will fail" >&2
fi

# ── STATUS TILE EMIT — hourly Pulse job; stale_after_s = 2x the interval (7200). Values pass
#    through the environment, never string-interpolated into the python source, so a path with
#    spaces (Drive folder names) or an empty behind/ahead can never produce broken python. ──────
_NOW="$(date -u +"%Y-%m-%dT%H:%M:%S+00:00")"
DRIVE="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
if [ -n "$DRIVE" ]; then
  _STATUS_STR="$( [ "$RC" -eq 0 ] && echo "OK" || echo "HELD" )"
  _SUMMARY="$( [ "$RC" -eq 0 ] && echo "fetched origin --prune ok" || echo "fetch held (rc=$RC)" )"
  MF_TILE="$DRIVE/state/status/mirror-fetch.json" \
  MF_NOW="$_NOW" MF_RC="$RC" MF_STATUS="$_STATUS_STR" MF_SUMMARY="$_SUMMARY" \
  MF_BEHIND="$BEHIND" MF_AHEAD="$AHEAD" \
  python3 -c "
import json, os
tile = os.environ['MF_TILE']
behind = os.environ.get('MF_BEHIND') or None
ahead = os.environ.get('MF_AHEAD') or None
d = {
    'schema_version': 1,
    'emit_mode': 'pulse',
    'last_run': os.environ['MF_NOW'],
    'rc': int(os.environ['MF_RC']),
    'stale_after_s': 7200,
    'status': os.environ['MF_STATUS'],
    'summary': os.environ['MF_SUMMARY'],
    'behind': int(behind) if behind is not None else None,
    'ahead': int(ahead) if ahead is not None else None,
}
tmp = tile + '.tmp'
os.makedirs(os.path.dirname(tile), exist_ok=True)
with open(tmp, 'w') as f:
    json.dump(d, f, indent=2)
os.replace(tmp, tile)
" || echo "[$JOB] WARN: status tile write failed (non-fatal)"
else
  echo "[$JOB] no data root set — fetch still ran, tile skipped (non-fatal). Set one: python3 shared/brain_root.py --set <folder>"
fi

exit "$RC"
