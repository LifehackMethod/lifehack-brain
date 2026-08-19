#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: notes kept getting saved with missing frontmatter (record_type / desk / created_at /
#      status). Nothing breaks loudly when that happens — the file saves fine. What breaks is
#      everything that looks for it later: the record does not show up where you expect it,
#      and you find out months on, when you go looking for something you are sure you wrote.
#      The checker for this already shipped in this repo and NOTHING CALLED IT at write time.
#      It was named in one skill's prose as a step to remember, which is the same as not having
#      it: a validator with no caller passes every check it has, because it has none.
# GUARDS: nothing. This is deliberately a NON-BLOCKING ADVISORY nudge and it always exits 0.
#      Frontmatter completeness is hygiene, not safety, and hard blocking is reserved for the
#      guards that stop irreversible acts. It names the missing field and gets out of the way.
# REDIRECT: add the field(s) named in the reminder. The required set and the check both live in
#      system/tools/validate_frontmatter.py.
# SIGNPOST: system/tools/validate_frontmatter.py holds REQUIRED_FIELDS — change what is required
#      THERE, not by weakening this hook to route around a schema you disagree with.
# FAIL_POSTURE: degrade-safe — a PostToolUse hook cannot block and must never try. Missing
#      validator, unreadable payload, validator crash: all exit 0 silently. The write already
#      happened; the only thing at stake is whether a reminder is printed.
# UPDATED: 2026-08-14 (ported; the donor's absolute path to the author's own clone became
#      ${CLAUDE_PROJECT_DIR}, resolved the way every other hook here resolves it)
# ─────────────────────────────────────────────────────────────────────────────
# PostToolUse hook (matcher: Write|Edit). Advisory only — always exits 0.
#
# ⚠ IT IS SCOPED BY THE VALIDATOR, NOT BY THIS FILE, and that is why it is not noise. The
# validator skips anything that is not a .md, anything unmanaged, backups and fixtures, anything
# quarantined or archived, and — the one that matters most — any file with no frontmatter at all.
# So an ordinary note gets nothing. You hear from this only on a file that already declared itself
# a managed record and then left a required field out.
#
# NOTE: no `set -e`. A non-zero exit from the validator is its VERDICT, not a failure of this
# hook, and must not abort it.

ARGS="${1:-$(cat)}"
[ -z "$ARGS" ] && exit 0

_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd -P)"
REPO="${CLAUDE_PROJECT_DIR:-${_HOOKDIR%/system/hooks}}"

FILE_PATH=$(printf '%s' "$ARGS" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', d) if isinstance(d, dict) else {}
    print(ti.get('file_path') or ti.get('path') or '')
except Exception:
    print('')
" 2>/dev/null)

# Fallback for a payload shape the parser did not expect. A PostToolUse hook that gives up
# quietly is correct; one that errors on the way out is noise attached to a write that already
# succeeded.
if [ -z "$FILE_PATH" ]; then
  FILE_PATH=$(printf '%s' "$ARGS" | grep -o '"file_path":"[^"]*"' | cut -d'"' -f4 | head -1)
fi
[ -z "$FILE_PATH" ] && exit 0

VALIDATOR="$REPO/system/tools/validate_frontmatter.py"
[ -f "$VALIDATOR" ] || exit 0

# The reminder goes to STDERR, which is the channel a PostToolUse hook is actually read on. The
# donor's version of this file sent it to stdout and swallowed the verdict with `|| true`, so it
# ran on every write for weeks and said nothing — inert, while looking installed. That is the same
# failure this hook exists to catch, one level up.
# ⛔ ONLY exit 1 IS A REJECT. The validator has three answers, not two: 0 valid-or-skipped,
# 1 a real missing field, 2 "cannot evaluate" (not markdown, file gone). Treating any non-zero as
# something to say — which is how the donor's version is written — turns every single .py write
# into "cannot evaluate: not markdown -> add the missing field(s)", which is both constant and
# nonsense advice. Measured here before this hook was registered. Noise is not a harmless default:
# it is how a real reminder gets skimmed past, which is the whole failure this hook exists to stop.
MSG=$(python3 "$VALIDATOR" "$FILE_PATH" 2>&1)
if [ "$?" = "1" ]; then
  printf 'FRONTMATTER REMINDER (non-blocking): %s\n    -> add the missing field(s); the schema is system/tools/validate_frontmatter.py\n' "$MSG" >&2
fi
exit 0
