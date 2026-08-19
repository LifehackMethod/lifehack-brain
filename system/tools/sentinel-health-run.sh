#!/usr/bin/env bash
# sentinel-health-run.sh — single-instance-guarded wrapper that recomputes the Sentinel security tile.
#
# PORTED (2026-08-14) from claudeops-config's system/tools/sentinel-health-run.sh. Two things in the
# donor version were dropped, both for the same reason ingest-run.lib.sh's header explains at length:
#   - `ingest_studio_gate` — the donor called this before the lock to stand down on the non-lead of
#     two machines. That function does not exist in this repo's ported ingest-run.lib.sh (no
#     two-machine model here — see docs/data-layout.md:214), so calling it would just be an error,
#     not a no-op.
#     ⚖ NOTE 2026-08-15 — that `…_studio_…` name is a DONOR CODE IDENTIFIER and is deliberately NOT
#     renamed. It named one of the donor's own machines, from an era before that gate was renamed to
#     a role. **The function does not exist in this repo** — verified by grep: no definition and no
#     call site anywhere, in any language; it survives only inside port notes like this one recording
#     that it was dropped. The surrounding sentence is DONOR DESCRIPTION, not a description of this
#     system. Renaming an identifier that points at nothing would only invent a new false name; the
#     machine it was named after is deliberately not named here. Same handling, same wording, as
#     system/organism/elements/pulse-cron.md's note on the identical name.
#   - the Pulse-specific framing ("gives the tile its OWN named Pulse slot", "Organism Window 2") —
#     there is no Pulse/scheduler here to slot into. See below.
#
# READ-ONLY: rolls system/logs/sentinel-events.jsonl → state/status/sentinel.json (via
# shared/gate/sentinel_response.py's write_status(), reused by sentinel-health.py — see that file's
# header for why it isn't a second, independent computation). No gws, no Google, no claude call —
# local jsonl only.
#
# ⚠ NOTHING SCHEDULES THIS YET. This repo has no cron/launchd wiring and none was added here — running
# it is a manual `bash system/tools/sentinel-health-run.sh`, or whatever a future scheduler calls.
# The single-instance lock still matters even run-by-hand: it protects against a person (or a script)
# invoking this twice concurrently and racing on the same tile file.
set -uo pipefail
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$CODE_ROOT/system/tools/ingest-run.lib.sh"

JOB="sentinel-health"

ingest_acquire_lock "$JOB"

# ── Run the read-only roll-up (writes state/status/sentinel.json atomically, via write_status()) ──
python3 "$CODE_ROOT/system/tools/sentinel-health.py"; RC=$?
exit "$RC"
