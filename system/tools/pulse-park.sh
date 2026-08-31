#!/usr/bin/env bash
# ── PULSE-PARK — durable stand-down for ONE Pulse job ────────────────────────────────────
# WHY: the `bootstrap-sync` job re-created 47 symlinks a session had just deleted, at 09:58 on
#      2026-08-23, because nothing existed that could durably tell Pulse "leave this one alone"
#      across a reboot. `pulse.sh` already understands a durable park record (its own
#      get_park_retry(), reading $PULSE_PARK_FILE — see that script's header) — this tool is the
#      thing that WRITES that record, safely, plus a STATUS check that tells the truth about
#      whether a job is actually parked instead of assuming it. pulse.sh itself is unmodified;
#      this is the missing writer + verifier, nothing more.
#
# PARK FILE: one JSON object, {"<job-name>": <retry_at-epoch-seconds>, ...}, living under the
#      Drive-backed notes root ($NOTES_ROOT/state/pulse-parked-jobs.json) — NEVER /tmp — so a
#      reboot or a pulse.sh restart never silently un-parks a job a human deliberately stood down.
#      Both this tool and pulse.sh re-read the file fresh on every invocation; neither caches it.
#
# SEVEN DISTINGUISHABLE `status` OUTCOMES (ABSENT-SUBJECT-RULE-v1 — "I checked and it's clean"
# and "I could not check" must never share a result):
#   NOT PAUSED        rc=1   nothing parked (file missing, key missing, or retry_at in the past)
#   PAUSED — until ts  rc=0   a live, future park record exists
#   CANNOT DETERMINE   rc=3   the manifest or the park file exists but cannot be parsed/trusted
#   ABSENT SUBJECT     rc=2   <job> has no row in the pulse-config.md jobs block at all
#
# USAGE:
#   pulse-park.sh set <job> --minutes N     write/refresh a durable park, N in (0, 10080] minutes
#   pulse-park.sh clear <job>               remove the park record for <job>
#   pulse-park.sh status <job>              report state; see the four outcomes above
#
# ENV (all optional, for sandboxing / override — mirrors pulse.sh's own):
#   LIFEHACK_ROOT      forces the notes root brain_root.py resolves (see shared/brain_root.py)
#   PULSE_PARK_FILE    forces the park file path directly, bypassing notes-root resolution
#   PULSE_CONFIG       forces the manifest path (default: <repo>/system/pulse-config.md)
# ──────────────────────────────────────────────────────────────────────────────────────────────
set -uo pipefail   # NOT -e: we want to control every exit path explicitly

CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG="${PULSE_CONFIG:-$CODE_ROOT/system/pulse-config.md}"

_ROOT_LINE="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"
NOTES_ROOT="${_ROOT_LINE:-}"
PARK_FILE="${PULSE_PARK_FILE:-${NOTES_ROOT:+$NOTES_ROOT/state/pulse-parked-jobs.json}}"

# Mirrors pulse.sh's PARK_HORIZON_S exactly (7 days) — this is the FIRST place that actually
# enforces it. pulse.sh declares the constant but never checks anything against it; this refusal
# is that enforcement, landed at the one place that writes the value in the first place.
PARK_HORIZON_S=$((7 * 86400))
PARK_HORIZON_MIN=$((PARK_HORIZON_S / 60))

NOW=$(date +%s)

# ── manifest lookup: does <job> have a row in the ```jobs``` block? ─────────────────────────────
# Returns via stdout+rc: "found" rc=0, "absent" rc=1 (job has no row), "no-manifest" rc=2 (the
# manifest file itself is missing/unreadable — a DIFFERENT claim from "row absent").
manifest_lookup() {
  local job="$1"
  [ -f "$CONFIG" ] || { echo "no-manifest"; return 2; }
  python3 -c "
import sys
job = sys.argv[1]
path = sys.argv[2]
try:
    text = open(path, encoding='utf-8').read()
except Exception:
    print('no-manifest'); sys.exit(2)
in_block = False
found = False
for raw in text.splitlines():
    line = raw.rstrip('\r')
    if line.strip() == '\`\`\`jobs':
        in_block = True
        continue
    if in_block and line.strip() == '\`\`\`':
        break
    if not in_block:
        continue
    stripped = line.strip()
    if stripped == '' or stripped.startswith('#'):
        continue
    name = line.split('|', 1)[0].strip()
    if name == job:
        found = True
        break
print('found' if found else 'absent')
sys.exit(0 if found else 1)
" "$job" "$CONFIG"
}

# ── park-file read: prints the raw dict as JSON on stdout. rc: 0 = parsed OK (possibly {} for a
# missing file — absence is legitimately empty, never corrupt), 1 = file exists but failed to parse.
read_park_file() {
  [ -n "$PARK_FILE" ] || { echo "NO-ROOT"; return 2; }
  if [ ! -f "$PARK_FILE" ]; then
    echo "{}"
    return 0
  fi
  python3 -c "
import json, sys
path = sys.argv[1]
try:
    d = json.load(open(path, encoding='utf-8'))
    if not isinstance(d, dict):
        raise ValueError('not an object')
except Exception:
    print('CORRUPT'); sys.exit(1)
print(json.dumps(d))
" "$PARK_FILE"
}

usage() {
  echo "usage: pulse-park.sh set <job> --minutes N | clear <job> | status <job>" >&2
}

VERB="${1:-}"
JOB="${2:-}"
shift $(( $# >= 2 ? 2 : $# )) 2>/dev/null || true

if [ -z "$VERB" ] || [ -z "$JOB" ]; then
  usage
  exit 1
fi

case "$VERB" in
  status)
    lookup_out="$(manifest_lookup "$JOB")"; lookup_rc=$?
    if [ "$lookup_rc" -eq 2 ]; then
      echo "CANNOT DETERMINE — manifest not found or unreadable: $CONFIG"
      exit 3
    fi
    if [ "$lookup_rc" -eq 1 ]; then
      echo "ABSENT SUBJECT — '$JOB' has no row in the pulse-config.md jobs block"
      exit 2
    fi

    if [ -z "$PARK_FILE" ]; then
      echo "CANNOT DETERMINE — no notes root resolved (LIFEHACK_ROOT unset, PULSE_PARK_FILE unset); cannot read a park record"
      exit 3
    fi

    park_json="$(read_park_file)"; park_rc=$?
    if [ "$park_rc" -ne 0 ] || [ "$park_json" = "CORRUPT" ]; then
      echo "CANNOT DETERMINE — park file exists but failed to parse as JSON: $PARK_FILE"
      exit 3
    fi

    retry_at=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
print(int(d.get(sys.argv[2], 0)))
" "$park_json" "$JOB" 2>/dev/null || echo 0)

    if [ "$retry_at" -gt "$NOW" ]; then
      human="$(date -r "$retry_at" '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || date -d "@$retry_at" '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || echo "$retry_at")"
      echo "PAUSED — until $human (epoch $retry_at)"
      exit 0
    else
      echo "NOT PAUSED"
      exit 1
    fi
    ;;

  set)
    minutes=""
    while [ $# -gt 0 ]; do
      case "$1" in
        --minutes) minutes="${2:-}"; shift 2 ;;
        --minutes=*) minutes="${1#--minutes=}"; shift ;;
        *) echo "REFUSED — unrecognized argument: $1" >&2; exit 1 ;;
      esac
    done

    if [ -z "$minutes" ]; then
      echo "REFUSED — set requires --minutes N (no default; a stand-down nobody named a duration for is exactly the defect this tool exists to prevent)" >&2
      exit 1
    fi
    case "$minutes" in
      ''|*[!0-9]*)
        echo "REFUSED — --minutes must be a positive integer, got: '$minutes'" >&2
        exit 1
        ;;
    esac
    if [ "$minutes" -le 0 ]; then
      echo "REFUSED — --minutes must be > 0, got: $minutes" >&2
      exit 1
    fi
    if [ "$minutes" -gt "$PARK_HORIZON_MIN" ]; then
      echo "REFUSED — --minutes ($minutes) exceeds the 7-day park horizon (${PARK_HORIZON_MIN} minutes / PARK_HORIZON_S=${PARK_HORIZON_S}s in pulse.sh). A stand-down nobody remembers to lift is a silently-disabled sync — file a longer, explicit re-park instead." >&2
      exit 1
    fi

    lookup_out="$(manifest_lookup "$JOB")"; lookup_rc=$?
    if [ "$lookup_rc" -eq 2 ]; then
      echo "CANNOT DETERMINE — manifest not found or unreadable: $CONFIG" >&2
      exit 3
    fi
    if [ "$lookup_rc" -eq 1 ]; then
      echo "ABSENT SUBJECT — '$JOB' has no row in the pulse-config.md jobs block; refusing to park a job that does not exist" >&2
      exit 2
    fi

    if [ -z "$PARK_FILE" ]; then
      echo "CANNOT DETERMINE — no notes root resolved (LIFEHACK_ROOT unset, PULSE_PARK_FILE unset); cannot write a durable park record" >&2
      exit 3
    fi

    park_json="$(read_park_file)"; park_rc=$?
    if [ "$park_rc" -ne 0 ] || [ "$park_json" = "CORRUPT" ]; then
      echo "CANNOT DETERMINE — existing park file is corrupt; refusing to blindly overwrite it. Inspect/fix by hand: $PARK_FILE" >&2
      exit 3
    fi

    retry_at=$((NOW + minutes * 60))
    mkdir -p "$(dirname "$PARK_FILE")" 2>/dev/null
    tmp="${PARK_FILE}.pulse-park.tmp.$$"
    python3 -c "
import json, sys
d = json.loads(sys.argv[1])
d[sys.argv[2]] = int(sys.argv[3])
json.dump(d, open(sys.argv[4], 'w', encoding='utf-8'))
" "$park_json" "$JOB" "$retry_at" "$tmp" || { echo "CANNOT DETERMINE — failed to write park file" >&2; rm -f "$tmp"; exit 3; }
    mv "$tmp" "$PARK_FILE"

    human="$(date -r "$retry_at" '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || date -d "@$retry_at" '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || echo "$retry_at")"
    echo "PAUSED — until $human (epoch $retry_at) — $PARK_FILE"
    exit 0
    ;;

  clear)
    if [ -z "$PARK_FILE" ]; then
      echo "NOT PAUSED — no notes root resolved; nothing durable to clear"
      exit 1
    fi
    if [ ! -f "$PARK_FILE" ]; then
      echo "NOT PAUSED — no park file exists ($PARK_FILE); nothing to clear"
      exit 1
    fi
    park_json="$(read_park_file)"; park_rc=$?
    if [ "$park_rc" -ne 0 ] || [ "$park_json" = "CORRUPT" ]; then
      echo "CANNOT DETERMINE — park file is corrupt; refusing to modify it blindly. Inspect/fix by hand: $PARK_FILE" >&2
      exit 3
    fi
    had_key=$(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
print('1' if sys.argv[2] in d else '0')
" "$park_json" "$JOB")
    tmp="${PARK_FILE}.pulse-park.tmp.$$"
    python3 -c "
import json, sys
d = json.loads(sys.argv[1])
d.pop(sys.argv[2], None)
json.dump(d, open(sys.argv[3], 'w', encoding='utf-8'))
" "$park_json" "$JOB" "$tmp" || { echo "CANNOT DETERMINE — failed to write park file" >&2; rm -f "$tmp"; exit 3; }
    mv "$tmp" "$PARK_FILE"
    if [ "$had_key" = "1" ]; then
      echo "CLEARED — '$JOB' is no longer parked"
    else
      echo "NOT PAUSED — '$JOB' was not parked (already clear)"
    fi
    exit 0
    ;;

  *)
    usage
    exit 1
    ;;
esac
