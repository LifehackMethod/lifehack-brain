#!/bin/bash
# Validation run N of the rebuilt morning read (plan 4P.3R step 1a), on COPIES of live data. Every write is redirected.
# Runs morning.py hand-run directly, never the gcjobs wrapper (which pulls from Google). The live files a morning run
# could write are fingerprinted (content hashes) before and after; the run says LIVE UNCHANGED or stops you.
#
# Usage: validation_run.sh N [DAY]          (DAY defaults to today)
# Every person-specific path comes from the environment; nothing of the person's is written here:
#   GC_LIVE_DATA   the live data folder (holds rig.db and front-room/)                      required
#   GC_NOTES       the person's notes root                                                   required
#   GC_SETUP_DIR   the person's Grand Central setup folder                                   required
#   GC_DESKS       space-separated desk folder names whose diaries a run may write           required
#   GC_PLANNING    the planning desk's folder name (one of GC_DESKS)                         required
#   GC_RUN_ROOT    a LOCAL owner-only folder for the copies (refused if under a synced folder) required
#   GC_OUT         where the draft is handed (a file path that must not exist yet)           required
#   GC_DROP_SRC    the mailroom drop folder                                                  required
#   GC_CHILD_SETTING_SOURCES, GC_CHILD_SETTINGS   optional: the window flags for the model children (claude_child.py reads
#                  them from the environment; this script only inherits them, it clears nothing)
#   GC_LIFE_MAP    the statement of direction      (default $GC_NOTES/desks/$GC_PLANNING/life-map.md)
#   GC_CODE_DIR    the plugin tree to run          (default: the tree this script is in)
set -euo pipefail
N="${1:?run number}"; DAY="${2:-$(date +%F)}"
: "${GC_LIVE_DATA:?}" "${GC_NOTES:?}" "${GC_SETUP_DIR:?}" "${GC_DESKS:?}" "${GC_PLANNING:?}" "${GC_RUN_ROOT:?}" "${GC_OUT:?}" "${GC_DROP_SRC:?}"
HERE="$(cd "$(dirname "$0")" && pwd)"
WT="${GC_CODE_DIR:-$(cd "$HERE/../../.." && pwd)}"
DROP_SRC="$GC_DROP_SRC"
LIFE_MAP="${GC_LIFE_MAP:-$GC_NOTES/desks/$GC_PLANNING/life-map.md}"
LIVE="$GC_LIVE_DATA"; NOTES="$GC_NOTES"; PD="$GC_PLANNING"; OUT="$GC_OUT"
SCR="$GC_RUN_ROOT/run-$N"
case " $GC_DESKS " in *" $PD "*) ;; *) echo "REFUSED: GC_PLANNING ($PD) is not in GC_DESKS" >&2; exit 2 ;; esac
for m in CloudStorage "Mobile Documents" "Google Drive" Dropbox; do
  case "$GC_RUN_ROOT" in *"$m"*) echo "REFUSED: GC_RUN_ROOT is under a synced folder ($m)" >&2; exit 2 ;; esac
done

# 0. Refuse if a Grand Central job is running, or the output or the run folder already exists.
if pgrep -f 'grand_central/(gcjobs|morning|pull|daily)\.py' >/dev/null; then echo "REFUSED: a Grand Central job is running" >&2; exit 3; fi
[ -e "$OUT" ] && { echo "REFUSED: $OUT exists" >&2; exit 3; }
[ -e "$SCR" ] && { echo "REFUSED: $SCR exists" >&2; exit 3; }

fingerprint() {  # every live file a morning run could write
  {
    shasum "$LIVE/front-room/catalogue/used-in-draft.jsonl" "$LIVE/front-room/catalogue/held-shown.jsonl" 2>/dev/null || true
    # CONTENT hashes, never `ls -la`: reading a Drive file adds com.apple.lastuseddate (the "@" in ls), which is not a write.
    find "$NOTES/desks/$PD/records/context" -maxdepth 1 -name "${DAY}-${PD}*" -type f -exec shasum {} + 2>/dev/null | sort || true
    for d in $GC_DESKS; do f="$NOTES/desks/$d/diary/${DAY:0:4}/${DAY:5:2}/${DAY:8:2}.md"; [ -f "$f" ] && shasum "$f"; done
    find "$LIVE/state/morning" -type f -exec shasum {} + 2>/dev/null | sort || true
  } | shasum
}
BEFORE="$(fingerprint)"

# 1. Copies (owner-only, local, never under a synced folder).
mkdir -p "$GC_RUN_ROOT"; chmod 700 "$GC_RUN_ROOT"; mkdir -p "$SCR"; chmod 700 "$SCR"
python3 -I - "$LIVE/rig.db" "$SCR/rig.db" <<'PY'
import sqlite3, sys
src = sqlite3.connect("file:%s?mode=ro" % sys.argv[1], uri=True); dst = sqlite3.connect(sys.argv[2])
src.backup(dst); dst.close(); src.close()
PY
cp -a "$LIVE/front-room" "$SCR/front-room"
mkdir -p "$SCR/drop"; cp -a "$DROP_SRC/facts" "$SCR/drop/facts"; mkdir -p "$SCR/drop/deliveries"
for d in $GC_DESKS; do
  mkdir -p "$SCR/notes/desks/$d"
  [ -d "$NOTES/desks/$d/diary" ] && cp -a "$NOTES/desks/$d/diary" "$SCR/notes/desks/$d/diary"
done
mkdir -p "$SCR/notes/desks/$PD/records"; cp -a "$NOTES/desks/$PD/records/context" "$SCR/notes/desks/$PD/records/context"
cp "$LIFE_MAP" "$SCR/notes/desks/$PD/life-map.md"
mkdir -p "$SCR/gc-data" "$SCR/state" "$SCR/debug"

# 2. Make DAY's mail new again IN THE COPY ONLY: drop DAY's used-in-draft marks and DAY's staged records and diary pages
#    (the live morning may already have run), so the rebuilt read sees what the live one saw.
python3 -I - "$SCR/front-room/catalogue/used-in-draft.jsonl" "$DAY" <<'PY'
import json, sys
p, day = sys.argv[1], sys.argv[2]
try: rows = open(p, encoding="utf-8").read().splitlines()
except FileNotFoundError: rows = []
keep = [r for r in rows if r.strip() and json.loads(r).get("day", "") != day]
open(p, "w", encoding="utf-8").write("".join(r + "\n" for r in keep))
print("used-in-draft marks kept: %d of %d (dropped day == %s)" % (len(keep), len([r for r in rows if r.strip()]), day))
PY
python3 -I - "$SCR/front-room/catalogue/held-shown.jsonl" "$DAY" <<'PY3'
import json, sys
p, day = sys.argv[1], sys.argv[2]
try: rows = open(p, encoding="utf-8").read().splitlines()
except FileNotFoundError: rows = []
keep = [r for r in rows if r.strip() and json.loads(r).get("day", "") != day]
open(p, "w", encoding="utf-8").write("".join(r + "\n" for r in keep))
print("held-shown marks kept: %d of %d (dropped day == %s)" % (len(keep), len([r for r in rows if r.strip()]), day))
PY3
python3 -I - "$SCR/notes" "$DAY" "$PD" $GC_DESKS <<'PY2'
import os, re, sys
root, day, pd, desks = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
ctx = os.path.join(root, "desks", pd, "records", "context")
for n in os.listdir(ctx):
    m = re.match(r"(\d{4}-\d{2}-\d{2})-" + re.escape(pd), n)
    if m and m.group(1) >= day: os.remove(os.path.join(ctx, n)); print("copy: removed staged", n)
for d in desks:
    base = os.path.join(root, "desks", d, "diary")
    for dp, _, fs in os.walk(base):
        for f in fs:
            m = re.match(r"(\d{2})\.md$", f); rel = os.path.relpath(dp, base).split(os.sep)
            if m and len(rel) == 2 and "%s-%s-%s" % (rel[0], rel[1], m.group(1)) >= day: os.remove(os.path.join(dp, f))
PY2

# 3. The run (the same claude command every morning uses; nothing new reaches the network).
export AGE_FRONT_ROOM="$SCR/front-room" GC_DATA_ROOT="$SCR/gc-data" GC_STATE_ROOT="$SCR/state" \
       AGE_NOTES_ROOT="$SCR/notes" GC_DROP="$SCR/drop" GC_SETUP_DIR GC_MORNING_DEBUG_DIR="$SCR/debug"
START=$(date +%s)
set +e
python3 "$WT/shared/grand_central/morning.py" hand-run --i-know-this-calls-the-real-model --desk "$PD" --day "$DAY" \
  --notes-root "$SCR/notes" --db "$SCR/rig.db" --drop "$SCR/drop" --life-map "$SCR/notes/desks/$PD/life-map.md" \
  > "$SCR/run.out" 2> "$SCR/run.err"
RC=$?
set -e
echo "rc=$RC seconds=$(( $(date +%s) - START ))" | tee "$SCR/run.rc"

# 4. Live untouched?
AFTER="$(fingerprint)"
[ "$BEFORE" = "$AFTER" ] && echo "LIVE UNCHANGED (fingerprint)" || echo "!! LIVE FINGERPRINT CHANGED: look before anything else"

# 5. Hand the draft (the staged snapshot from the copy).
STAGED="$(ls "$SCR/notes/desks/$PD/records/context/${DAY}-${PD}"*.md 2>/dev/null | head -1 || true)"
if [ -n "$STAGED" ]; then cp "$STAGED" "$OUT"; echo "draft: $OUT"; else echo "NO DRAFT STAGED (see $SCR/run.err)"; fi
grep -E 'proof|handed|verified|lenses' "$SCR/run.out" | tail -3 || true
