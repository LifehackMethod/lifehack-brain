#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# status-tile.lib.sh — THE status-tile emit for shell runners. One copy, many callers.
#
# SIBLING of claude-auth.lib.sh / gws-auth.lib.sh, built for the same reason: on 2026-08-27 the
# three store writers (calendar-store-sync, tasks-store-sync, email-summary-write) had died at
# their gws preflight (rc=2) every run for a whole night, and nothing on the status board said so —
# they wrote only machine-local proofs under ~/.local/share/lifehack/, so system-health rendered
# them NO-TILE (job ticked, no tile anywhere) while the stores sat empty. The pulse convention
# (system/pulse-config.md: every job "EMITS a status tile on finish — that is how you learn it
# happened") was being honored by every job EXCEPT the three whose silence cost the most.
#
# CONTRACT — mirrors the rc table in system/pulse-config.md and the planning-health.py tile shape:
#   rc=0  -> status OK, the caller's summary verbatim
#   rc=75 -> status OK, configured:false, summary "stood down: <reason arg>" — an unconfigured
#            install must NEVER render as breakage (see gws-auth.lib.sh's header), but per
#            ABSENT-SUBJECT-RULE-v1 the stand-down is NAMED, never spelled like a clean pass
#   else  -> status ERROR, summary "<caller's summary> (rc=N)"
# The write is atomic (tmp + rename) and NON-FATAL on failure: a tile write must never turn a
# succeeded job into a failed one. No notes root -> warn line, skip.
#
# USAGE (from a runner's EXIT trap, so failures tile too):
#   source "$CODE_ROOT/system/tools/status-tile.lib.sh"
#   write_status_tile "<job>" "$RC" <stale_after_s> "<ok summary>" "<err summary>" ["<standdown reason>"]
# The tile lands at <brain>/state/status/<job>.json — the eponymous name system-health.py's
# tile_for() resolves with ZERO alias entries.
# ─────────────────────────────────────────────────────────────────────────────

write_status_tile() {  # job rc stale_after_s ok_summary err_summary [standdown_reason]
  local _job="$1" _rc="$2" _stale="$3" _ok="$4" _err="$5" _sd="${6:-required credentials not configured yet}"
  local _root
  _root="$(python3 "${CODE_ROOT:?write_status_tile: CODE_ROOT unset}/shared/brain_root.py" --quiet 2>/dev/null)"
  if [ -z "$_root" ]; then
    echo "[$_job] WARN: no notes root — skipping status tile." >&2
    return 0
  fi
  TILE_JOB="$_job" TILE_RC="$_rc" TILE_STALE="$_stale" TILE_OK="$_ok" TILE_ERR="$_err" TILE_SD="$_sd" TILE_ROOT="$_root" \
  python3 - <<'PYEOF' || echo "[$_job] WARN: status tile write failed (non-fatal)." >&2
import json, os, time
job, root = os.environ["TILE_JOB"], os.environ["TILE_ROOT"]
rc = int(os.environ["TILE_RC"]); stale = int(os.environ["TILE_STALE"])
lt = time.localtime(); off = time.strftime("%z", lt); off = off[:3] + ":" + off[3:] if off else "+00:00"
d = {"desk": "root", "schema_version": 2, "pulse_job": job, "emit_mode": "pulse",
     "stale_after_s": stale, "last_run": time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off,
     "rc": rc, "configured": True}
if rc == 0:
    d.update(status="OK", summary=os.environ["TILE_OK"])
elif rc == 75:
    d.update(status="OK", configured=False, summary="stood down: " + os.environ["TILE_SD"])
else:
    d.update(status="ERROR", summary="%s (rc=%d)" % (os.environ["TILE_ERR"], rc))
status_dir = os.path.join(root, "state", "status")
os.makedirs(status_dir, exist_ok=True)
tile = os.path.join(status_dir, job + ".json")
tmp = tile + ".tmp"
json.dump(d, open(tmp, "w"), indent=2)
os.replace(tmp, tile)
PYEOF
  return 0
}
