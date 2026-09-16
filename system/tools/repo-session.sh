#!/bin/bash
# repo-session.sh — start a repo session with the lifehack-brain PLUGIN disabled.
#
# WHY: a session started inside this repo (or the installed plugin folder) with BOTH the
# repo's own project files (.claude/settings.json, hooks/hooks.json) AND the installed
# plugin enabled double-fires every hook the two files share — SessionStart, UserPromptSubmit,
# every guarded Bash call, all of it. Students never see this (they subscribe to the repo
# WITHOUT the plugin, so they single-fire from the project file alone); it is an admin-only
# problem, and re-splitting the wiring files themselves would risk leaving some session mode
# with zero guards (B2.1's clone-only fail line). Enver's Option G ruling (2026-09-15,
# enforcement-layer Phase 2 build) named the fix as a launcher, not a rewrite: run the admin
# session with the plugin disabled for THAT SESSION ONLY — the project file alone then carries
# every guard, single-fired, exactly like a student's session. Nothing on disk changes, nothing
# is installed or uninstalled, and there is no re-enable step to remember: it ends when the
# session ends. Method proven live: `records`/scratchpad `B2.1-report.md` §3 (the E2 isolation
# check, `--settings '{"enabledPlugins":{"lifehack-brain@lifehack-brain":false}}'`).
#
# RUN IT:
#   bash system/tools/repo-session.sh [any extra `claude` flags/args]
#
# ALIAS IT — one word, works from anywhere, add to your shell rc (~/.zshrc or ~/.bashrc):
#   alias lbs='bash ~/lifehack-brain/system/tools/repo-session.sh'
# (swap ~/lifehack-brain for wherever YOUR checkout of this repo actually lives, if different —
# a worktree, a fork, etc. Whichever checkout's copy of this script the alias points at is the
# one that starts.)
#
# This script always starts `claude` in the repo IT ITSELF LIVES IN — it locates and `cd`s to
# its own repo root before doing anything else, so it works correctly no matter what directory
# you were sitting in when you ran it. Every extra argument you pass is forwarded to `claude`
# verbatim, so e.g. `lbs --model haiku --tools "" -p "ok"` behaves exactly like a raw `claude`
# call, just single-fired.

set -euo pipefail

# system/tools/repo-session.sh -> repo root is two directories up.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if ! command -v claude >/dev/null 2>&1; then
  echo "repo-session.sh: 'claude' is not on PATH — cannot start a session." >&2
  exit 1
fi

cd "$HERE"
exec claude --settings '{"enabledPlugins":{"lifehack-brain@lifehack-brain":false}}' "$@"
