#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# planning-vault-weekly-run.sh — WEEKLY deep-pull runner.
# WHY: the weekly check-in is the DEEP dive; this pre-builds the week-scoped deep vault
#      (every open task + the week's email + the full calendar behind/ahead) before the
#      human sits down. Stage 1 of the weekly cadence system (the analog of the daily
#      planning-vault-run.sh — never edit that file). Chains Stage 2 (the weekly deep-mine).
# GUARDS: READ-ONLY against Google (safe-ingest primitives only); vault writes to the notes root.
# REDIRECT: vault → desks/cal/state/weekly-vault/<YYYY-Www>/ ; status → $OUT_DIR/last-run.json.
# ⚠ That DATA PATH is deliberately still `desks/cal/` — code/jobs/tiles are renamed to `planning`,
#   the records directory is NOT (the operator's call, untaken). Do not "complete" it without his word.
#
# ⛔ DO NOT PORT `cal-vault-weekly-pull.py` — it is dead code, superseded by
#    `planning-window-to-vault.py` (the library-backed producer this script calls below). This file
#    never called the bespoke pull script even in the donor.
#
# ⚖ PORT NOTE, three changes from donor:
#   1. LEAD-MACHINE gate (state/primary-machine marker election between two machines) is DELETED, not
#      translated — a student has one computer, so there is nothing to elect between.
#   2. The Drive status-tile write used donor's `emit_status.py` (system/tools/emit_status.py),
#      which has not been ported to this repo yet (out of this port's scope — a different
#      subsystem). Rather than ship an import that fails on every run, this uses the same plain
#      json.dump the sibling daily runner (planning-vault-run.sh) already uses for the identical job —
#      same tile shape, no new dependency. If/when emit_status.py lands, this can switch to it.
#   3. `${CODE_ROOT}/desks/cal` (a donor multi-desk CODE directory for CLAUDE.md context) does not
#      exist in this repo's layout and is dropped — nothing here depends on it.
# ─────────────────────────────────────────────────────────────────────────────
set -eo pipefail
export PATH="/usr/sbin:/sbin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"   # cron PATH may omit /usr/sbin

# ── LIBRARY-ONLY source: the weekly vault is filled ONLY from the central library
#    (planning-window-to-vault.py). There is NO bespoke Gmail-scrape fallback and NO on/off switch — a
#    single mandatory path is the whole point (a fresh session cannot route around the library). A
#    broken/stale library is made LOUD (the producer stamps a STALE_WARNING into _manifest.json),
#    NEVER silently rerouted to a live scrape. Extract --week for the producer; leave all args for
#    the Stage-2 mine. ──
WEEK=""; _ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --week)   WEEK="$2"; _ARGS+=("$1" "$2"); shift 2 ;;
    --week=*) WEEK="${1#*=}"; _ARGS+=("$1"); shift ;;
    *)        _ARGS+=("$1"); shift ;;
  esac
done
set -- "${_ARGS[@]:-}"

# ── Identity + residency ──
SUBSYSTEM_NAME="planning-vault-weekly"
STALE_AFTER_HOURS="168"                            # weekly cadence → 7 days before the freshness check alarms
STALE_AFTER_S=$((STALE_AFTER_HOURS * 3600))        # single source for both the local proof AND the status tile
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# The ONE headless-gws credential preflight — shared with the ten other runners that reach Google.
# A missing library is a REAL defect (exit 1), never a stand-down. (It sets no shell options, so
# this file's `set -eo pipefail` above is unaffected.)
. "$CODE_ROOT/system/tools/gws-auth.lib.sh" || {
  echo "[$SUBSYSTEM_NAME] FATAL: cannot source $CODE_ROOT/system/tools/gws-auth.lib.sh"; exit 1; }

DRIVE="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
if [ -z "$DRIVE" ]; then
  echo "[$SUBSYSTEM_NAME] no data root set — nothing to pull into. Set one: python3 shared/brain_root.py --set <folder>"
  exit 2
fi

OUT_DIR="$HOME/.local/share/lifehack/${SUBSYSTEM_NAME}"    # machine-local, OUTSIDE the indexed vault
STATUS_ARTIFACT="$OUT_DIR/last-run.json"
mkdir -p "$OUT_DIR" 2>/dev/null || true
GWS_BIN="$(command -v gws 2>/dev/null || echo /opt/homebrew/bin/gws)"

# ── Headless gws auth (keychain-free isolated config) ──
# OPTIONAL by design: the weekly pull degrades gracefully and marks each unreachable source in its
# own manifest, so a person with no Google account still gets a completed vault rather than a crash.
# ⚖ 2026-08-15: was a hand-rolled `[ -s "$GWS_CREDS" ]` block, one of eleven identical copies —
# now the shared helper (gws-auth.lib.sh, sourced at the top). Two things change: `[ -s ]` passed a
# whitespace-only or corrupt file and exported it anyway, and the absence was SILENT. The helper
# validates, and names the absence in one non-fatal line. ⛔ Do not re-inline it.
load_gws_credentials_optional "$SUBSYSTEM_NAME"

# ── Single-instance lock (weekly pull takes minutes; 30-min stale reclaim) ──
LOCKDIR="/tmp/lifehack-${SUBSYSTEM_NAME}.lock"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  if [ -d "$LOCKDIR" ] && [ "$(( $(date +%s) - $(stat -c %Y "$LOCKDIR" 2>/dev/null || stat -f %m "$LOCKDIR" 2>/dev/null || echo 0) ))" -gt 1800 ]; then
    rm -rf "$LOCKDIR"; mkdir "$LOCKDIR" 2>/dev/null || exit 0
  else
    echo "[$SUBSYSTEM_NAME] another run in progress — skip."; exit 0
  fi
fi

# ── ONE exit handler: writes the {rc,ts} status artifact, the status TILE, AND clears the lock on
#    ANY exit (success, set -e death, or kill) — so "it ran" vs "it succeeded" is always recorded,
#    and a lead-gate/lock-contention early exit above this point never touches the tile (this trap
#    is registered AFTER those). ──
RC=1   # pessimistic default: die before do_work returns → honest non-zero
_on_exit() {
  printf '{"subsystem":"%s","rc":%s,"ts":"%s","stale_after_h":%s}\n' \
    "$SUBSYSTEM_NAME" "$RC" "$(date -u +%FT%TZ)" "$STALE_AFTER_HOURS" > "$STATUS_ARTIFACT" 2>/dev/null || true
  rm -rf "$LOCKDIR" 2>/dev/null || true

  local _status="OK"; [ "${RC:-1}" -ne 0 ] && _status="ERROR"
  local _summary="planning-vault-weekly pull ok"
  [ "${RC:-1}" -ne 0 ] && _summary="planning-vault-weekly run failed (rc=${RC:-1})"
  python3 -c "
import json, os
os.makedirs('$DRIVE/state/status', exist_ok=True)
d={'schema_version':1,'emit_mode':'manual','last_run':'$(date -u +%FT%TZ)','rc':${RC:-1},'stale_after_s':$STALE_AFTER_S,'status':'$_status','summary':'$_summary','no_pulse':True}
tmp='$DRIVE/state/status/planning-vault-weekly.json.tmp'
json.dump(d,open(tmp,'w'),indent=2)
os.replace(tmp,'$DRIVE/state/status/planning-vault-weekly.json')
" 2>/dev/null || true
}
trap _on_exit EXIT INT TERM

# ── THE WORK: pre-flight (warn-only), Stage 1 the deep pull (from the library), emit the status
#    tile, then chain Stage 2 the deep-mine (non-fatal — the mine has its own lock + watchdog; a
#    mine stall must not fail the pull). Return non-zero ONLY when the pull itself broke. ──
do_work() {
  local _ok=0 _try
  for _try in 1 2 3; do
    if "$GWS_BIN" gmail users getProfile --params '{"userId":"me"}' >/dev/null 2>&1; then _ok=1; break; fi
    [ "$_try" -lt 3 ] && { echo "[$SUBSYSTEM_NAME] gws pre-flight $_try failed — retry 4s…"; sleep 4; }
  done
  [ "$_ok" -ne 1 ] && echo "[$SUBSYSTEM_NAME] WARN: gws pre-flight failed (or gws is not installed) — sources may be marked failed."

  echo "[$SUBSYSTEM_NAME] filling the weekly vault from the central library …"
  # ONLY path: fill the vault from the library. --week is forwarded (else the producer defaults to
  # the current ISO week). A stale library surfaces as a STALE_WARNING in the manifest — never a
  # silent fall-back to a live Google scrape.
  local _wk=(); [ -n "$WEEK" ] && _wk=(--week "$WEEK")
  # NOTE: use "${_wk[@]}" NOT "${_wk[@]:-}" — the :- default operator on an EMPTY array expands
  # to a single empty-string arg (argparse then errors "unrecognized arguments: "). Bare "${_wk[@]}"
  # expands to nothing when empty (script has no `set -u`), so a no-args run defaults to current week.
  python3 "$CODE_ROOT/system/tools/planning-window-to-vault.py" "${_wk[@]}" || return $?

  # Status tile: written in the exit trap (above), not here — do_work() only ever reaches this
  # line on the SUCCESS path, which would otherwise be a blind spot on failure/kill.

  # Stage 2: chain the weekly deep-mine (bounded by its own lock + 15-min watchdog).
  if [ -x "$CODE_ROOT/system/tools/planning-weekly-analyze-run.sh" ]; then
    echo "[$SUBSYSTEM_NAME] pull ok — chaining Stage 2 (weekly deep-mine) …"
    bash "$CODE_ROOT/system/tools/planning-weekly-analyze-run.sh" "$@" \
      || echo "[$SUBSYSTEM_NAME] analyze stage rc=$? (non-fatal to the pull)"
  fi
  return 0
}

# Capture do_work's REAL rc without set -e aborting first (a kill mid-run leaves RC=1).
do_work "$@" && RC=0 || RC=$?

# ── Active failure-buzz: a hard pull failure pages NOW, not after a 3-strike breaker ──
if [ "$RC" -ne 0 ]; then
  bash "$CODE_ROOT/shared/notify/notify-send.sh" --source "$SUBSYSTEM_NAME" --tags warning --priority critical \
    --title "⚠️ ${SUBSYSTEM_NAME} failed" \
    --message "${SUBSYSTEM_NAME} run failed (rc=$RC). Check $STATUS_ARTIFACT." 2>/dev/null || true
fi

echo "[$SUBSYSTEM_NAME] done (rc=$RC)."
exit "$RC"
