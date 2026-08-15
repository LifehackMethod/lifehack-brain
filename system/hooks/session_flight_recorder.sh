#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: Session learnings were repeatedly lost when /save was never called, and
#      there was no lightweight, durable record of what each session actually did
#      (which desk, how many tool calls, how many files written). Without a flight
#      log, sessions left no trace; without a /save nudge, hard-won learnings
#      evaporated when the window closed.
# GUARDS: This is a Stop hook — it never blocks. It records a one-line flight-log
#      entry per session, flushes any pending observability buffer to durable
#      storage, and nudges (stderr only) when /save was not called so learnings
#      are not silently lost.
# REDIRECT: Flight log, observability, and the learnings stub all live under the
#      notes root resolved through `shared/brain_root.py` — Flight log →
#      `<notes root>/system/flight-log.jsonl`. Observability →
#      `<notes root>/system/observability/<YYYY-MM-DD>.jsonl`. Learnings stub →
#      `<notes root>/system/learnings.md`. If no notes root is set yet
#      (`brain_root.py --quiet` returns nothing), this hook skips those three
#      writes rather than guessing a location — set one with
#      `python3 shared/brain_root.py --set <path>`. To preserve learnings, run
#      /save before ending regardless of whether a notes root is set.
# UPDATED: 2026-05-30 (ported; DRIVE resolution replaced with brain_root.py, the
#      retired per-desk email-lane flag cleanup dropped — see below)
# ─────────────────────────────────────────────────────────────────────────────

# Stop hook: ALWAYS exit 0. Defensive throughout — never abort on a failed step.

REPO="$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)"
ROOT=""
if [ -n "$REPO" ] && [ -f "$REPO/shared/brain_root.py" ]; then
  ROOT="$(python3 "$REPO/shared/brain_root.py" --quiet 2>/dev/null)"
fi
# NOT-SET is a real, expected state (e.g. a fresh install) — degrade by skipping the
# notes-root-dependent writes below, never by guessing a path or failing loud (this is a
# Stop hook; it must always exit 0).
FLIGHT_LOG=""
OBS_DIR=""
LEARNINGS=""
if [ -n "$ROOT" ]; then
  FLIGHT_LOG="$ROOT/system/flight-log.jsonl"
  OBS_DIR="$ROOT/system/observability"
  LEARNINGS="$ROOT/system/learnings.md"
fi
OBS_BUFFER="/tmp/lifehack-observability-buffer.jsonl"

# ── Read stdin payload ────────────────────────────────────────────────────────
INPUT=$(cat 2>/dev/null)

SESSION_ID=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('session_id','') or '')
except Exception:
    print('')
" 2>/dev/null)

TRANSCRIPT=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('transcript_path','') or '')
except Exception:
    print('')
" 2>/dev/null)

CWD=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('cwd','') or '')
except Exception:
    print('')
" 2>/dev/null)

# ── Derive desk from cwd ────────────────────────────────────────────────────────
# .../desks/<desk>/...  → <desk> ; else "root"
DESK="root"
case "$CWD" in
  */desks/*)
    DESK=$(printf '%s' "$CWD" | sed -E 's#.*/desks/([^/]+).*#\1#')
    [ -z "$DESK" ] && DESK="root"
    ;;
esac

# ── Compute lightweight stats from transcript (defensive) ───────────────────────
TOOL_CALLS=0
FILES_WRITTEN=0
DURATION="null"
SAVE_FOUND=0

if [ -n "$TRANSCRIPT" ] && [ -r "$TRANSCRIPT" ]; then
    TOOL_CALLS=$(grep -c '"type":"tool_use"' "$TRANSCRIPT" 2>/dev/null)
    [ -z "$TOOL_CALLS" ] && TOOL_CALLS=0

    # tool_use entries whose name is Write or Edit. Each transcript line is one
    # full message; a tool_use block carries both the type and name markers on
    # the same line, so count lines that contain both.
    FILES_WRITTEN=$(grep '"type":"tool_use"' "$TRANSCRIPT" 2>/dev/null | grep -cE '"name":"(Write|Edit)"')
    [ -z "$FILES_WRITTEN" ] && FILES_WRITTEN=0

    # best-effort duration: file mtime minus timestamp on first line (if present)
    DURATION=$(python3 -c "
import sys, json, os, re
from datetime import datetime
path = sys.argv[1]
try:
    mtime = os.path.getmtime(path)
    first_ts = None
    with open(path, 'r', errors='replace') as f:
        line = f.readline()
    try:
        obj = json.loads(line)
        ts = obj.get('timestamp') or obj.get('ts') or obj.get('time')
        if ts:
            s = str(ts).replace('Z', '+00:00')
            first_ts = datetime.fromisoformat(s).timestamp()
    except Exception:
        first_ts = None
    if first_ts is not None:
        d = int(mtime - first_ts)
        print(d if d >= 0 else 'null')
    else:
        print('null')
except Exception:
    print('null')
" "$TRANSCRIPT" 2>/dev/null)
    [ -z "$DURATION" ] && DURATION="null"

    if grep -q '/save' "$TRANSCRIPT" 2>/dev/null; then
        SAVE_FOUND=1
    fi
fi

# ── Append one flight-log line (only if a notes root is set) ────────────────────
if [ -n "$FLIGHT_LOG" ]; then
    TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    mkdir -p "$(dirname "$FLIGHT_LOG")" 2>/dev/null
    printf '{"ts":"%s","desk":"%s","session":"%s","tool_calls":%s,"files_written":%s,"duration_s":%s}\n' \
        "$TS" "$DESK" "$SESSION_ID" "$TOOL_CALLS" "$FILES_WRITTEN" "$DURATION" \
        >> "$FLIGHT_LOG" 2>/dev/null
fi

# ── Observability flush (only if a notes root is set) ────────────────────────────
# Append buffer to today's observability file, then delete buffer ONLY on success.
# If no notes root is set, the buffer is simply left for a later session to flush
# once one is — never dropped, never guessed to a path.
if [ -n "$OBS_DIR" ] && [ -f "$OBS_BUFFER" ]; then
    TODAY=$(date +"%Y-%m-%d")
    OBS_FILE="$OBS_DIR/$TODAY.jsonl"
    if mkdir -p "$OBS_DIR" 2>/dev/null && cat "$OBS_BUFFER" >> "$OBS_FILE" 2>/dev/null; then
        rm -f "$OBS_BUFFER" 2>/dev/null
    fi
fi

# ── Ensure learnings.md exists (create stub ONLY if missing — never overwrite) ──
if [ -n "$LEARNINGS" ] && [ ! -e "$LEARNINGS" ]; then
    mkdir -p "$(dirname "$LEARNINGS")" 2>/dev/null
    printf '# Learnings\n\nDurable session learnings. Created by session_flight_recorder.sh stub.\n' \
        > "$LEARNINGS" 2>/dev/null
fi

# ── /save nudge (stderr only) ───────────────────────────────────────────────────
if [ "$SAVE_FOUND" -eq 0 ]; then
    echo "[session_end] /save was not called this session. Learnings may be lost." >&2
fi

# NOTE: the donor version of this hook also cleared a stale per-desk email-trust-lane
# flag (`current_email_lane`) here. That mechanism (TRUSTED_EMAIL_LANE / per-desk trusted
# lane) was already retired in the donor system itself and does not exist in this repo at
# all — dropped rather than ported as dead code for a flag file nothing here ever writes.

exit 0
