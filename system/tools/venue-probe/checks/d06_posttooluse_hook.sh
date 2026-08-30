#!/bin/bash
# D6 — PostToolUse hooks (5 registered).
#
# CAUSED-EVIDENCE DESIGN: writes a REAL file to /tmp with deliberately
# missing frontmatter, then runs the actual registered advisory hook
# (system/hooks/validate_on_write.sh, matcher Write|Edit) against it with
# the real JSON payload shape, and captures its real stderr text. This is
# not the model reporting "the advisory appeared" -- it is the hook's own
# process output, captured mechanically.
#
# WHY THE PATH LOOKS ODD: validate_frontmatter.py only validates paths
# containing "desks/", "system/", or "_ClaudeOps" (see
# system/tools/validate_frontmatter.py, scope-narrowing block). To trip a
# REAL advisory while staying entirely inside /tmp (hard safety rule), the
# scratch file is created at $SCRATCH_DIR/system/<name>.md -- the substring
# "system/" satisfies the validator's scope check without the file living
# anywhere near the real system/ tree. Confirmed by direct run 2026-08-04.
#
# validate_on_write.sh is advisory-only by design (never blocks, always
# exits 0) -- so PASS here means "the advisory text appeared," not "the
# write was blocked." That is the correct read for this hook.

set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "$DIR/../lib/common.sh"

HOOK_SCRIPT="$DIR/../../../hooks/validate_on_write.sh"
if [ "${VENUE_PROBE_BREAK:-0}" = "1" ]; then
    HOOK_SCRIPT="$SCRATCH_DIR/no-such-advisory-hook-$$.sh"
fi

TARGET_DIR="$SCRATCH_DIR/system"
mkdir -p "$TARGET_DIR" 2>/dev/null
TARGET="$TARGET_DIR/d6-bad-frontmatter-$$.md"
CMD="printf '{tool_input JSON}' | bash $HOOK_SCRIPT"

if [ ! -f "$HOOK_SCRIPT" ]; then
    emit_json "D6" "INCONCLUSIVE" "stdout" \
        "advisory hook not found at $HOOK_SCRIPT -- cannot obtain caused evidence of a PostToolUse advisory" \
        "$CMD" "$VENUE"
    exit 0
fi

if [ -z "$PYTHON3" ]; then
    emit_json "D6" "INCONCLUSIVE" "stdout" "python3 unavailable -- cannot build the synthetic tool_input payload" "$CMD" "$VENUE"
    exit 0
fi

printf -- '---\ntitle: venue-probe D6 canary (deliberately missing required fields)\n---\n\nbody text.\n' > "$TARGET"

if [ ! -f "$TARGET" ]; then
    emit_json "D6" "INCONCLUSIVE" "stdout" "could not create the /tmp canary file at $TARGET -- no substrate to test the advisory against" "$CMD" "$VENUE"
    exit 0
fi

PAYLOAD=$("$PYTHON3" -c "
import json
print(json.dumps({'tool_name': 'Write', 'tool_input': {'file_path': '$TARGET'}}))
")

ADVISORY=$(printf '%s' "$PAYLOAD" | bash "$HOOK_SCRIPT" 2>&1 >/dev/null)
HOOK_EXIT=$?

if printf '%s' "$ADVISORY" | grep -q "FRONTMATTER REMINDER"; then
    emit_json "D6" "PASS" "deny_text" "advisory hook exited $HOOK_EXIT (advisory-only, non-blocking by design) and emitted: $ADVISORY" "$CMD" "$VENUE"
elif [ -z "$ADVISORY" ]; then
    emit_json "D6" "FAIL" "stdout" "advisory hook ran (exit $HOOK_EXIT) but emitted no reminder text for a file missing all four required frontmatter fields" "$CMD" "$VENUE"
else
    emit_json "D6" "INCONCLUSIVE" "stdout" "advisory hook produced unexpected output (exit $HOOK_EXIT): $ADVISORY" "$CMD" "$VENUE"
fi

rm -f "$TARGET" 2>/dev/null
exit 0
