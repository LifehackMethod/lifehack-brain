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
