#!/usr/bin/env bash
# LLM-CONTEXT ------------------------------------------------------------------
# emit_harness_brief.sh — SessionStart. Delivers the Harness standing brief to
# sessions that would not otherwise receive it.
#
# WHY THIS EXISTS: the brief lives in this repo's CLAUDE.md, and the harness loads
# a CLAUDE.md only when the session's folder is that repo. A plugin-root CLAUDE.md
# is NEVER loaded — Anthropic's plugins reference states it outright: "A CLAUDE.md
# file at the plugin root is not loaded as project context. Plugins contribute
# context through skills, agents, and hooks rather than CLAUDE.md."
#
# So anyone running the Harness AS A PLUGIN, rather than working inside a clone of
# this repo, never saw the brief at all. This hook is the documented fix. Anthropic
# ships their own learning-output-style plugin the same way: "The plugin uses a
# SessionStart hook to inject additional context into every session... roughly
# equivalent to CLAUDE.md, but more flexible and allows for distribution through
# plugins." It also re-fires on compaction, which a CLAUDE.md does not.
#
# ⭐ THE ANTI-DUPLICATION RULE: if this session is already inside a checkout whose
# own CLAUDE.md carries this brief, emit NOTHING — otherwise the brief arrives
# twice, which is the exact problem this hook was built to end. Detected by
# walking up from the working directory and comparing first headings, so it holds
# whatever a given person named their folder.
#
# FAIL_POSTURE: degrade-safe — any error exits 0 silently. A missing brief is a
# degraded session; a blocked one is a dead session.
# ------------------------------------------------------------------------------
set +e
cat >/dev/null 2>&1   # drain stdin per the hook contract

SRC="${CLAUDE_PLUGIN_ROOT:-}/CLAUDE.md"
[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -r "$SRC" ] || exit 0

MARK="$(head -1 "$SRC" 2>/dev/null)"
[ -n "$MARK" ] || exit 0

# Walk up from cwd to $HOME; if a CLAUDE.md there already carries this brief, stay quiet.
d="$(pwd -P 2>/dev/null)" || exit 0
while [ -n "$d" ] && [ "$d" != "/" ]; do
  if [ -r "$d/CLAUDE.md" ] && [ "$(head -1 "$d/CLAUDE.md" 2>/dev/null)" = "$MARK" ]; then
    exit 0
  fi
  [ "$d" = "$HOME" ] && break
  d="$(dirname "$d")"
done

printf '=== Lifehack Harness — standing brief (delivered by the plugin; this session is outside the repo) ===\n\n'
cat "$SRC"
exit 0
