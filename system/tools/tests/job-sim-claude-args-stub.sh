#!/usr/bin/env bash
# job-sim-claude-args-stub.sh -- TEST-ONLY stand-in for `claude` (via CLAUDE_BIN) for the 5.9(g) model-readonly scenario.
#   --version  -> "9.9.9 (Claude Code)"
#   otherwise  -> records its argv (one line) to $JOB_SIM_DIR/claude-args, drains stdin, prints a reply holding the marker MARK.
# No model call, no network.
if [ "${1:-}" = "--version" ]; then echo "9.9.9 (Claude Code)"; exit 0; fi
printf '%s\n' "$*" > "${JOB_SIM_DIR:?JOB_SIM_DIR not set}/claude-args"
cat > /dev/null
echo "reply MARK"
