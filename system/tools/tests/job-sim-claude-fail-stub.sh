#!/usr/bin/env bash
# job-sim-claude-fail-stub.sh -- TEST-ONLY stand-in for `claude -p` (via CLAUDE_BIN) that FAILS with a reason on stderr:
# used by the 5.9(d) model-stderr scenario to prove the model's stderr reaches the job log and the failure reason. No model call, no network.
echo "boom: simulated model failure" >&2
exit 1
