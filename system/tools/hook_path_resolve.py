"""Resolve shell variables in a command string so a path-matching guard sees the REAL path.

WHY THIS FILE EXISTS AT ALL (T15.32, 2026-08-04, ported from claudeops-config 2026-08-16)
------------------------------------------------------------------------------------------
`system/hooks/guard_findings_write.sh` blocks hand-authored writes into the Hospital findings
store. Its write patterns each end in the LITERAL store path, so they only fire when that literal
sits in the command next to the write verb. Put the path in a shell variable and every pattern
misses it:

    P="state/findings/forged.jsonl"
    echo ... >> "$P"                      # <- was ALLOWED

Observed live (in the donor repo, not theorised): a variable-path `mv "$src" "$ARCH/"` moved
shards OUT of the store uncontested, minutes after an identical literal-path `mv` was correctly
blocked. This repo's own guard carried the identical gap from the day it was ported (2026-08-14)
until this file landed — see the guard's own header for the standing "resolver unavailable,
DEGRADES to literal-path matching only" note, which this file resolves.

WHY EXPANSION IS SUFFICIENT
---------------------------
The harness runs every Bash tool call in a FRESH shell -- environment variables and functions do
NOT persist between calls. So a variable holding the store path must be ASSIGNED IN THE SAME
command string it is used in, which means the literal is always present somewhere in that string
and expansion always recovers it.

WHY NOT AN EIGHTH REGEX
-----------------------
The defect was never a missing pattern. It was that the match ran against UNRESOLVED text. Adding
patterns to a string matcher repeats the disease. Compare the 2026-07-26 `indexOf("READY")` gate:
a status check must test the RESOLVED value, and must fail CLOSED on anything it cannot resolve.

WHY THIS IS A SEPARATE MODULE AND NOT INLINE IN THE HOOK
----------------------------------------------------------
The guard carries its logic inside a single-quoted `python3 -c` block. On the first attempt at
this fix (in the donor repo) the inserted comments contained apostrophes, which terminated that
quoting early and left the hook syntactically invalid -- and a broken PreToolUse hook blocks EVERY
Bash, Write and Edit call, including the one that would repair it. Keeping this code in its own
importable file means the hook only ever gains an import line, never a body of new text threaded
through that quoting.

Deliberately dependency-free and side-effect-free so the guard stays fast and cannot be broken by
importing it. No repo-specific assumptions -- pure string manipulation, stdlib `re` only -- so it
ported unchanged from claudeops-config other than this docstring's provenance note.
"""

from __future__ import annotations   # target python3 here may be <3.10; keep this for safety

import re

# NAME=value at the start of a line, optionally `export`-prefixed. Single- and double-quoted forms
# and bare words. `\x27` rather than a literal apostrophe purely so this file stays safe to embed
# or echo through a single-quoted shell context.
_ASSIGN = re.compile(
    r"(?m)^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)="
    r"(\"[^\"]*\"|\x27[^\x27]*\x27|[^\s;&|]*)"
)

_MAX_PASSES = 5


def expand(text):
    """Substitute in-command variable assignments and return the expanded command string.

    Iterates so a two-hop chain resolves -- DRIVE=... then SRC="$DRIVE/..." -- and is bounded at
    _MAX_PASSES so a self-referential assignment cannot loop forever. Returns the input unchanged
    when there is nothing to expand.
    """
    if not text:
        return text
    env = {}
    for m in _ASSIGN.finditer(text):
        val = m.group(2)
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"\x27":
            val = val[1:-1]
        env[m.group(1)] = val
    if not env:
        return text
    for _ in range(_MAX_PASSES):
        prev = text
        for k, v in env.items():
            text = text.replace("${%s}" % k, v).replace("$%s" % k, v)
        if text == prev:
            break
    return text
