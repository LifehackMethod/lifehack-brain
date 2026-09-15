#!/usr/bin/env bash
# Installs the status-bar STUB at a fixed user path. Run once, by hand: `bash system/statusline-bootstrap.sh`.
#
# WHY THIS EXISTS: Claude Code's `statusLine` setting needs a real path, and a plugin's own
# settings.json cannot register `statusLine` at all (only `agent`/`subagentStatusLine` — see
# plugins-reference.md). The plugin cache is also version-numbered with no stable "current"
# pointer. So the STUB below holds NO Harness logic — only enough to find wherever the plugin
# currently lives and hand off to its real system/statusline.sh — which means the stub never
# goes stale across an update, even though it lives outside the plugin.
#
# This script does NOT touch ~/.claude/settings.json — wiring a statusLine into someone's own
# settings is their act, per this project's standing rule. It prints the one line to paste.

set -euo pipefail
STUB="$HOME/.claude/statusline.sh"
mkdir -p "$(dirname "$STUB")"

# ⛔ NEVER CLOBBER SOMETHING ALREADY THERE. That path is a plausible place for a person's own
# status line, and on the machine where this was written it was exactly that — a personal,
# guard-protected file that a blind `cat >` would have destroyed with no warning and no copy.
# If anything is there that is not our own stub, keep it: back it up, name the backup, and let
# the person decide. Losing someone's own work to an install script is not a recoverable mistake.
if [ -L "$STUB" ] && [ ! -e "$STUB" ]; then
  # A DEAD symlink: there is no content to preserve, so there is nothing to back up.
  # Say where it pointed — that is the only information it carried — and replace it.
  echo "⚠ $STUB was a symlink to $(readlink "$STUB"), which no longer exists. Replacing it."
elif { [ -e "$STUB" ] || [ -L "$STUB" ]; } && ! grep -q 'lifehack-brain@lifehack-brain' "$STUB" 2>/dev/null; then
  BAK="$STUB.before-lifehack-$(date +%Y%m%dT%H%M%S)"
  cp -p "$STUB" "$BAK"
  echo "⚠ $STUB already exists and is NOT this stub — it looks like your own."
  echo "  A copy is saved at: $BAK"
  echo "  Overwriting now. If that was deliberate work of yours, restore it from that copy."
fi

# ⛔ REMOVE FIRST. `cat >` FOLLOWS a symlink: if $STUB is a symlink to a path that no longer
# exists, the redirect tries to create the file at the DEAD TARGET and fails with a bare
# "No such file or directory" — the install silently does nothing. Found on a real machine
# 2026-09-09, where this path was a symlink into a folder deleted long ago. A sandbox test
# with an ordinary file cannot reproduce it.
rm -f "$STUB"
cat > "$STUB" <<'STUBEOF'
#!/usr/bin/env bash
# Fixed-path stub (see system/statusline-bootstrap.sh, public Harness). NO Harness logic here
# on purpose: it only finds the plugin's CURRENT install and execs its real statusline, so it
# never goes stale across a plugin update. Never errors — a status bar must never block a session.
REG="$HOME/.claude/plugins/installed_plugins.json"
P="$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1]));print(d["plugins"]["lifehack-brain@lifehack-brain"][0]["installPath"])' "$REG" 2>/dev/null)"
[ -n "$P" ] && [ -f "$P/system/statusline.sh" ] || \
  P="$(ls -d "$HOME"/.claude/plugins/cache/lifehack-brain/lifehack-brain/*/ 2>/dev/null | sort -V | tail -1 | sed 's:/$::')"
[ -n "${P:-}" ] && [ -f "$P/system/statusline.sh" ] && exec bash "$P/system/statusline.sh"
exit 0
STUBEOF
chmod +x "$STUB"

echo "Installed the status-bar stub: $STUB"
echo
echo "One thing left, and it's yours to do: add this to ~/.claude/settings.json"
echo '  "statusLine": { "type": "command", "command": "bash ~/.claude/statusline.sh" }'
echo
echo "(If settings.json already has other top-level keys, add statusLine as a sibling — don't replace the file.)"
