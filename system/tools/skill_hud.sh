#!/usr/bin/env bash
# skill_hud.sh — let a skill draw a custom HUD line ABOVE the Lifehack status bar.
#
# A running skill calls `set` at each stage boundary; system/statusline.sh renders that
# line above the normal `model · ctx · cost · desk` bar every turn; `clear` removes it
# when the skill finishes. Because the HARNESS redraws it each turn (not the model), the
# HUD can't be forgotten and it survives a context compaction.
#
# SESSION-SCOPED: the file is keyed by $CLAUDE_CODE_SESSION_ID, so parallel windows never
# clobber each other's HUD. statusline.sh reads the same per-session path (session_id from
# its stdin JSON). A 6h freshness guard in statusline.sh drops a HUD a crashed skill left.
#
# Usage (from a skill, via Bash):
#   bash system/tools/skill_hud.sh set '🧭 Ingest · Screen a pile   ◉○○○○   2/4 SCAN · …'
#   bash system/tools/skill_hud.sh clear
set -uo pipefail

HUD_DIR="$HOME/.claude/hud"
SID="${CLAUDE_CODE_SESSION_ID:-default}"
HUD_FILE="$HUD_DIR/$SID.txt"

case "${1:-}" in
  set)
    mkdir -p "$HUD_DIR" 2>/dev/null || true
    printf '%s\n' "${2:-}" > "$HUD_FILE"
    ;;
  clear)
    rm -f "$HUD_FILE"
    ;;
  *)
    echo "usage: skill_hud.sh set '<hud line>' | clear" >&2
    exit 2
    ;;
esac
