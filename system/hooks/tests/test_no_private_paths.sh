#!/bin/bash
# No private paths or names in the skill-builder files that ship (observe tool, runner, spec files, prompts).
cd "$(dirname "$0")/../../.." || exit 1
PAT='envergjokaj|GoogleDrive|_ClaudeOps|16-skill-builder-packet|build-rebuild|packet-component-builder|ClaudeOps|Enver'
FILES=".claude/skills/skill-builder system/tools/observe_flag.sh system/tools/observe_review.sh system/parts/stage_runner.py system/hooks/lib/sb_start.py system/hooks/lib/sb_spec.py system/hooks/lib/spec_write.sh system/hooks/end_of_turn_checks.sh system/hooks/run_step_hook.sh system/templates/skill-spec-form"
HITS="$(grep -rnE "$PAT" --exclude-dir=__pycache__ $FILES 2>/dev/null)"
if [ -z "$HITS" ]; then echo "PASS no private path or name in the shipped skill-builder files"; exit 0; fi
echo "FAIL private paths or names found:"; printf '%s\n' "$HITS"; exit 1
