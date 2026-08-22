#!/usr/bin/env bash
# install-doctrine-check.sh — put the doctrine-sync CHECK side on a Mac that does NOT run the pulse.
#
# Renders system/launchd/com.lifehack.doctrine-check.plist (filling __REPO__ and __HOME__) into
# ~/Library/LaunchAgents/, loads it with launchctl, kick-starts one run, and then PROVES it ran by
# reading the log and the findings shard — never by the registration alone (install-schedulers.sh's
# own A38 lesson: a registered job that never fires looks identical to a healthy one if all you
# check is that the entry exists).
#
# DOCTRINE THIS ENFORCES (2026-08-22): pulse on the machine that runs the pulse; a check-only
# LaunchAgent on any other. If this machine's crontab already carries pulse.sh, `check` already
# rides its 5-minute system-health sweep and a second runner would only double-write the same
# shard — so this script REFUSES there. Read the plist's own header for why the pulse itself must
# never be duplicated across machines.
#
#   bash system/launchd/install-doctrine-check.sh            install + prove
#   bash system/launchd/install-doctrine-check.sh --render   print the rendered plist, touch nothing
#   bash system/launchd/install-doctrine-check.sh --uninstall
#
# Exit: 0 installed and proven · 3 refused (pulse machine, or not a Mac) · 1 install ran but the
# proof did not land (the log and shard are named so you can look).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd -P)"
REPO="$(cd "$HERE/../.." && pwd -P)"
LABEL="com.lifehack.doctrine-check"
TEMPLATE="$HERE/$LABEL.plist"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOGDIR="$HOME/.local/state/lifehack"
LOG="$LOGDIR/doctrine-check.log"
MODE="${1:-install}"

render() { sed -e "s|__REPO__|$REPO|g" -e "s|__HOME__|$HOME|g" "$TEMPLATE"; }

if [ "$MODE" = "--render" ]; then render; exit 0; fi

[ "$(uname -s)" = "Darwin" ] || { echo "refused: launchd is macOS-only; on Linux/Windows the check rides the pulse (install-schedulers.sh)" >&2; exit 3; }

if [ "$MODE" = "--uninstall" ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  if [ -f "$DEST" ]; then
    STAMP="$(date +%Y-%m-%dT%H%M%S)"
    ARCH="$LOGDIR/archive/plist-$STAMP"   # never deleted: archived
    mkdir -p "$ARCH" && mv "$DEST" "$ARCH/" && echo "unloaded; plist archived to $ARCH/ (never deleted)"
  else
    echo "nothing installed at $DEST"
  fi
  exit 0
fi

# ── the refusal: this machine runs the pulse → the check already rides it ──
if crontab -l 2>/dev/null | grep -q 'pulse\.sh'; then
  echo "refused: this machine's crontab runs pulse.sh, so doctrine_sync.py check already rides the" >&2
  echo "         system-health sweep every 5 min. A LaunchAgent here would double-write the same shard." >&2
  echo "         Doctrine: pulse on the machine that runs the pulse; a check-only LaunchAgent on any other." >&2
  exit 3
fi
if [ -f "$DEST" ] && ! grep -q "$REPO/system/tools/doctrine_sync.py" "$DEST"; then
  echo "note: $DEST exists but points at a different repo path; re-rendering over it" >&2
fi

python3 "$REPO/shared/brain_root.py" >/dev/null 2>&1 || echo "warning: .brain-root not set — check will stand down (exit 75) until it is" >&2

mkdir -p "$HOME/Library/LaunchAgents" "$LOGDIR"
render > "$DEST"
plutil -lint "$DEST" >/dev/null
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$DEST"
launchctl kickstart -k "gui/$(id -u)/$LABEL"

# ── the proof: a shard row with a timestamp AFTER the kick-start, not just a registered label ──
MARK="$(date +%s)"
sleep 4
MACHINE="$(python3 "$REPO/system/tools/doctrine_sync.py" status 2>/dev/null | sed -n 's/^machine: \([^ ]*\).*/\1/p')"
BRAIN="$(python3 "$REPO/shared/brain_root.py" 2>/dev/null || true)"
SHARD="$BRAIN/state/findings/doctrine-sync-$MACHINE.local.jsonl"
if [ -n "$BRAIN" ] && [ -f "$SHARD" ] && [ "$(stat -f %m "$SHARD")" -ge "$((MARK - 5))" ]; then
  echo "installed: $DEST"
  echo "proven:    $SHARD gained a row after kick-start ($(tail -n1 "$SHARD" | python3 -c 'import sys,json;d=json.loads(sys.stdin.read());print(d["summary"], d["ts"])'))"
  echo "log:       $LOG"
  echo "next tick: every 300 s while awake. Remove with: bash $0 --uninstall"
  exit 0
fi
echo "installed but NOT proven: no fresh row in $SHARD within 4 s. Look at $LOG and at: launchctl print gui/$(id -u)/$LABEL" >&2
exit 1
