#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: cron/Pulse wrapper for planning-health.py — the wrapper pulse-config.md's own row note said
#      was missing ("no *-run.sh wrapper exists yet for this job"). Without it the checker ran bare
#      under cron with NO Google credential environment: the keychain is locked in a headless
#      context, so every unattended run died with "Access denied. No credentials provided" while the
#      same command worked interactively (first seen 2026-08-27 00:05; ledger [GOOGLE] line, filed
#      by the stale-sweep's first live run the same night).
# WHAT IT ADDS: (1) the ONE shared gws credential preflight — require_gws_credentials exports the
#      keychain-free GOOGLE_WORKSPACE_CLI_* env from ~/.config/lifehack/gws-credentials.json, and
#      stands down rc=75 (named line, never a fault) when that file is absent/unusable — true for
#      every machine before the one-time export, and permanently true for a no-Google install.
#      (2) a single-instance lock. The checker itself is unchanged: READ-ONLY, degrades rc=75 on an
#      unconfigured config/cal.md, exit 1 on a real read failure (Pulse's breaker).
# NOTE: a hand-run on a machine with keychain auth but no export file will stand down here even
#      though `python3 system/tools/planning-health.py` would work — call the checker directly for
#      interactive one-offs; this wrapper exists for the headless path.
# EXIT CODES (pulse-config.md's contract): 75 stood down (no/unusable creds, or checker's own
#      not-configured) · 0 ran · 1 real failure · 2 transient (checker's own mapping passes through).
# ─────────────────────────────────────────────────────────────────────────────
set -u
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PH_LABEL="planning-health"

_plog() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${PH_LABEL}: $*"; }

# The ONE shared gws preflight — never hand-rolled (see gws-auth.lib.sh's eleven-copy history).
# A missing library is a REAL defect (exit 1), never a stand-down.
. "$CODE_ROOT/system/tools/gws-auth.lib.sh" || {
  echo "[$PH_LABEL] FATAL: cannot source $CODE_ROOT/system/tools/gws-auth.lib.sh"; exit 1; }
require_gws_credentials "$PH_LABEL" _plog || exit 75

# ── SINGLE-INSTANCE LOCK (mkdir atomic; stale-steal after 30 min — the checker is a quick read) ──
LOCKDIR="/tmp/lifehack-${PH_LABEL}.lock"
STEAL=1800
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  if [ -d "$LOCKDIR" ] && [ "$(( $(date +%s) - $(stat -f %m "$LOCKDIR" 2>/dev/null || echo 0) ))" -gt "$STEAL" ]; then
    _plog "stale lock (>${STEAL}s) — stealing."; rm -rf "$LOCKDIR"
    mkdir "$LOCKDIR" 2>/dev/null || { _plog "lock race — skip."; exit 0; }
  else
    _plog "another run in progress — skip this tick."; exit 0
  fi
fi
trap "rm -rf '$LOCKDIR' 2>/dev/null" EXIT

python3 "$CODE_ROOT/system/tools/planning-health.py" "$@"
RC=$?
_plog "checker exit: $RC"
exit "$RC"
