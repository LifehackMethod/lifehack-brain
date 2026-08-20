#!/usr/bin/env python3
"""sentinel-health.py — recompute state/status/sentinel.json from system/logs/sentinel-events.jsonl,
on demand or on whatever cadence a future scheduler gives it.

PORTED (2026-08-14) from claudeops-config's system/tools/sentinel-health.py, which rolled the same
log into a tile through two pieces of infrastructure that do not exist in this repo: an `emit_status`
/ `emit_finding` writer, and a "Hospital" findings store with a dead-man-switch that needed a
`_is_system_health_child()` guard to avoid double-reporting from two different call sites. Neither
concept is here — confirmed absent (no system-health.py, no Hospital, no emit_status/emit_finding
anywhere in this repo) — so both were dropped rather than reimplemented as new shared infrastructure
this port does not own.

What's left is the part that still means something: shared/gate/sentinel_response.py ALREADY computes
and writes this exact tile (its own write_status(), same file, same shape, unit-tested), but only
inline, at the moment a per-item check happens. If nothing gets checked for hours, the tile's
last_run goes stale even though nothing is wrong. This script exists to let the SAME tile be
refreshed on its own, independent of any check firing — so a person, or a scheduler this repo builds
later, has a way to say "recompute now" without needing an event to trigger it.

Rather than re-derive the roll-up (a second implementation of the same counts is exactly the kind of
drift that made the donor's two parallel computations need a "keeps this twin in sync with..." comment
in the first place), this script imports and calls sentinel_response.write_status() directly — one
implementation, reused. It resolves the notes root itself first (mirroring shared/gate/
sentinel_response.py's own resolve_brain_root() call, its lines ~42-49) purely to report what it found
before touching anything; the actual read/write paths still come from sentinel_response's own
module-level LOG/STATUS constants, so there is no second, independently-hardcoded path anywhere in
this file.

Exit 0 = the tile was recomputed (regardless of what security status it reports — DANGER is a fact
about the log, not a failure of this script). Exit 1 = this script itself could not do its job
(import failure, write failure, unreadable output) — mapped explicitly, never silently folded into
looking like a clean run with nothing to report.
"""
import json
import os
import sys

CODE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))  # system/tools/ → repo root
_SHARED = os.path.join(CODE_ROOT, "shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)
try:
    from brain_root import resolve_brain_root       # shared/brain_root.py — the one root variable
except Exception as e:
    sys.stderr.write(f"sentinel-health: cannot import brain_root ({e})\n")
    sys.exit(1)

_GATE_DIR = os.path.join(CODE_ROOT, "shared", "gate")
if _GATE_DIR not in sys.path:
    sys.path.insert(0, _GATE_DIR)
try:
    import sentinel_response                        # shared/gate/sentinel_response.py
except Exception as e:
    sys.stderr.write(f"sentinel-health: cannot import sentinel_response ({e})\n")
    sys.exit(1)


def main():
    # Resolved again here, explicitly, purely so this script can NAME what it found before writing
    # anything — resolve_brain_root() is cheap and side-effect-free; sentinel_response.py already
    # does the same call at import time to set its own LOG/STATUS paths, so this is not a second,
    # divergent source of truth, just a visible echo of the one it already made.
    source, root = resolve_brain_root()
    if root is None:
        sys.stderr.write(
            "sentinel-health: notes root NOT-SET (no $LIFEHACK_ROOT, no persisted "
            "~/.config/lifehack/brain-root) — proceeding on sentinel_response.py's own fallback "
            "(~/.cache/lifehack-sentinel) so a fresh install still gets a tile.\n")
    else:
        print(f"[sentinel-health] root resolved via {source}: {root}")

    try:
        sentinel_response.write_status()
    except Exception as e:
        sys.stderr.write(f"sentinel-health: write_status() failed ({e})\n")
        return 1

    try:
        with open(sentinel_response.STATUS) as f:
            tile = json.load(f)
    except Exception as e:
        sys.stderr.write(f"sentinel-health: wrote the tile but could not read it back ({e})\n")
        return 1

    status = tile.get("status", "UNKNOWN")
    ev24 = tile.get("event_count_24h", 0)
    danger24 = tile.get("danger_count_24h", 0)
    print(f"[sentinel-health] {status} — {ev24} events/24h ({danger24} danger)")
    return 0


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    sys.exit(main())
