#!/usr/bin/env bash
# job-sim-claude-down-stub.sh -- TEST-ONLY stand-in for a reader that cannot run (retired model / no token): fails like
# `claude -p` does. Used via CLAUDE_BIN by the rig scenario reader-down.
echo "There's an issue with the selected model (retired-model-stub). It may not exist or you may not have access to it." >&2
exit 1
