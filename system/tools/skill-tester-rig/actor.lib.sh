#!/bin/bash
# actor.lib.sh — card TR2.0b of the skill-tester-rig: the ONE headless-actor launch shape. Source it; never run it.
#
# The rig launches a headless `claude -p` from two places: run.sh (every ai step, real or fake) and
# probe-actor-writes.sh (the write-list census). Both build the actor's argv HERE, so the census measures exactly
# the process run.sh starts. The shape is the one probe-hooks.sh proved on 2026-10-31 (TR0.4, `HOOKS: FIRE`):
#
#   env -u <seed vars> -u <harness/env leaks> [-u ANTHROPIC_API_KEY]          (BSD env: every -u BEFORE any NAME=VALUE)
#       HOME=<throwaway home>                     no user settings/hooks, no installed plugin copy, no notes root, no
#                                                 auto-memory carried between steps; the ONLY hooks are --plugin-dir's
#       LHB_JOURNAL_PATH=<home>/.claude/run/fire-journal.jsonl
#                                                 the fire journal stays inside the throwaway HOME (journal.sh's default
#                                                 under that HOME too); the real ~/.claude/run/fire-journal.jsonl is
#                                                 outside every allow rule of the write guard, so a write there is denied
#       DISABLE_AUTOUPDATER=1                     no self-update at startup
#     <bin> -p <prompt> --output-format json --model <id> --allowedTools Read
#           --permission-mode bypassPermissions --settings <rendered lab settings> --plugin-dir <harness tree>
#
# Auth is NOT set here: the caller exports CLAUDE_CODE_OAUTH_TOKEN (read from the REAL home before the switch).
# When it is set, ANTHROPIC_API_KEY is unset so the token is the only credential (probe-hooks.sh does the same).
# Never --dangerously-skip-permissions (ruling 8). stdin </dev/null and the watchdog (budget.sh call) are the
# caller's job, as before.
#
# NOTE on the lab settings: with HOME switched, a `Read(~/...)` deny rule expands to the THROWAWAY home, so only the
# rendered absolute `Read(//<path>/**)` forms bind (lab-settings.template.json carries both; run_selftest checks them).
#
#   actor_argv_build <home> <bin> <prompt> <model-id> <settings> <plugin-dir>
#       sets the array ACTOR (one argv element each). Returns 1 (ACTOR empty) if any argument is empty.
actor_argv_build() {
  local home="$1" bin="$2" prompt="$3" model="$4" settings="$5" plugin="$6" u
  ACTOR=()
  [ -n "$home" ] && [ -n "$bin" ] && [ -n "$prompt" ] && [ -n "$model" ] && [ -n "$settings" ] && [ -n "$plugin" ] || return 1
  u=( -u CANARY_SEED -u SKILL_TESTER_SEED -u CLAUDE_CONFIG_DIR -u LIFEHACK_ROOT -u LHB_JOURNAL_DISABLE
      -u LIFEHACK_WATCH -u CLAUDE_PLUGIN_ROOT -u CLAUDE_CODE_SESSION_ID )
  [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] && u=( "${u[@]}" -u ANTHROPIC_API_KEY )
  ACTOR=( env "${u[@]}"
          HOME="$home" LHB_JOURNAL_PATH="$home/.claude/run/fire-journal.jsonl" DISABLE_AUTOUPDATER=1
          "$bin" -p "$prompt" --output-format json --model "$model" --allowedTools Read
          --permission-mode bypassPermissions --settings "$settings" --plugin-dir "$plugin" )
  return 0
}
