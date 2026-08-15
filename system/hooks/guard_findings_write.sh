#!/bin/bash
#
# ══════════════════════════════════════════════════════════════════════════════
# ⚠  SPEED BUMP, NOT A BOUNDARY.  Read this before you trust this file.
#
#  This guard inspects a command as TEXT. A shell has infinite equivalent ways to
#  spell the same command, so a text matcher is always one phrasing behind. Treat
#  what follows as a speed bump that raises the cost of a mistake — never as a wall
#  that makes one impossible.
# ══════════════════════════════════════════════════════════════════════════════
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: Hospital's thesis is that a finding must be CAUSED, never GENERATED. `emit_finding.py`
#      (system/tools/emit_finding.py) enforces its contract STRUCTURALLY: no id=/fingerprint=
#      parameter exists to pass, `scanned_n` is required with no default, and `scanned_n==0`
#      paired with `status=OK` is refused outright. All of that is un-bypassable THROUGH the
#      writer — and completely bypassable AROUND it, by appending a hand-authored line straight
#      into `state/findings/*.jsonl`. A hand-written finding is an opinion wearing a machine's
#      authority — the exact disease this store exists to prevent.
# GUARDS: any WRITE INTO state/findings/ that bypasses `emit_finding.py` — a shell redirect
#      (> or >>), tee, sed -i, cp/mv/rsync into the store, truncate/shred/rm, dd of=, a python
#      open(...,"a"/"w"), or a Write/Edit tool call targeting a shard. READS are NEVER blocked:
#      cat/grep/ls/wc/head/tail are how findings_reader.py, health_line.py and a human inspect
#      the store, and blocking them would break the consumer this subsystem was built to feed.
# REDIRECT: emit a finding the ONE validated way —
#      `python3 system/tools/emit_finding.py --producer <name> --status <OK|ERROR|NEEDS_REVIEW|
#      NEEDS_APPROVAL> --scanned-n <REAL count examined> --label job=<x> --label kind=<y>
#      --summary "<what>"` (or, from Python: `from emit_finding import emit_finding`). The
#      fingerprint and the file path are computed FOR you — that is the point.
# SIGNPOST: the rule lives in system/tools/emit_finding.py's module docstring (why no id=, why
#      scanned_n has no default, why the path is resolved through shared/brain_root.py). To
#      change what is protected: edit this guard, get sign-off, then update its settings.json
#      registration — see system/hook-contract.md.
# FAIL_POSTURE: closed — an unparseable payload DENIES.
# UPDATED: 2026-08-14 (ported from claudeops-config's guard_findings_write.sh). Two changes from
#      the donor, both deliberate:
#        1. SCOPE NARROWED TO state/findings/ ONLY. The donor also guarded state/recommendations/
#           (an "Efficiency" reasoner store paired with emit_recommendation.py). Neither
#           emit_recommendation.py nor any recommendations/ concept exists in this repo — confirmed
#           absent this session (no matches anywhere in the tree). A REDIRECT must point at
#           something that exists here; one that named a writer this repo does not have would be
#           worse than no guard. If recommendations/ lands later, extend this guard's STORE
#           pattern and REDIRECT text together, in the same change.
#        2. THE VARIABLE-PATH RESOLVER IS OPTIONAL HERE, NOT ASSUMED. The donor imports
#           `hook_path_resolve.expand()` from its own sibling `system/tools/` (a path-in-a-shell-
#           variable defeater) via a hardcoded `~/claudeops-config/system/tools` sys.path entry.
#           That module does not exist in this repo yet (out of scope for this porting pass — it
#           lives in system/tools/, not system/hooks/). The sys.path entry below now resolves
#           relative to THIS repo (via ${CLAUDE_PROJECT_DIR}, falling back to this script's own
#           directory) instead of a hardcoded home path, so the import will start working
#           automatically the day someone ports hook_path_resolve.py — no second edit needed. Until
#           then this guard DEGRADES LOUDLY (a stderr line, never a silent gap) to literal-path
#           matching only, which is exactly the donor's own designed fallback behavior, not a new
#           weakness introduced here.
# ─────────────────────────────────────────────────────────────────────────────
# guard_findings_write.sh — PreToolUse hook (matcher: Bash|Write|Edit)
# Blocks any write into the Hospital findings store that bypasses emit_finding.py.

set -uo pipefail

_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd -P)"
REPO="${CLAUDE_PROJECT_DIR:-${_HOOKDIR%/system/hooks}}"

DENY='{"decision":"block","reason":"BLOCKED: a direct write into a VALIDATED STORE - state/findings/ (Hospital). WHY: a finding must be CAUSED, never GENERATED. emit_finding.py computes the fingerprint from the label set, derives the machine token, and refuses the dishonest case (scanned_n==0 paired with status=OK). A hand-authored line forges all of it, and a forged record is an opinion wearing a machine authority. REDIRECT - python3 system/tools/emit_finding.py --producer <name> --status <OK|ERROR|NEEDS_REVIEW|NEEDS_APPROVAL> --scanned-n <REAL count EXAMINED> --label job=<x> --summary \"<what>\" (from Python: from emit_finding import emit_finding). READS are not blocked - cat/grep/ls the store freely. RULE: system/tools/emit_finding.py module docstring; to change what is protected, edit system/hooks/guard_findings_write.sh, get sign-off, then re-verify per system/hook-contract.md."}'
deny() { printf '%s\n' "$DENY" >&2; exit 2; }

INPUT=$(cat)

# An EMPTY stdin is a bare manual invocation, not a tool call — nothing to adjudicate.
[ -z "$INPUT" ] && exit 0

export GFW_TOOLS_DIR="$REPO/system/tools"

EVAL=$(printf '%s' "$INPUT" | python3 -c '
import sys, json, os, re

try:
    d = json.load(sys.stdin)
except Exception:
    print("PARSE_FAIL"); raise SystemExit(0)

ti = d.get("tool_input", {}) or {}

# The store, matched on the PATH SEGMENT so a lookalike ("my-state/findings-notes") does NOT match.
STORE = re.compile(r"(^|/)state/findings/")

# Write / Edit tools: the target is a path, so this is unambiguous.
for key in ("file_path", "notebook_path"):
    p = ti.get(key) or ""
    if p and STORE.search(p):
        print("DENY"); raise SystemExit(0)

cmd = ti.get("command", "") or ""
if not cmd:
    print("OK"); raise SystemExit(0)

# Bash: match the WRITE-TO-TARGET pattern, NEVER the mere mention of the path.
# A guard that greps a command string for a keyword false-positives on a
# `git commit -m "...state/findings..."` or a `cat`/`grep` of the store — every pattern here
# requires an actual WRITE VERB aimed AT the store.
# A path held in a shell VARIABLE can evade a literal-text match entirely — the donor guard this
# was ported from closes that with a shared resolver (hook_path_resolve.expand()). That module is
# not yet in this repo (see UPDATED note above), so this DEGRADES to literal-path matching only,
# and says so on stderr rather than pretending the gap is closed.
_tools_dir = os.environ.get("GFW_TOOLS_DIR", "")
if _tools_dir:
    sys.path.insert(0, _tools_dir)
try:
    from hook_path_resolve import expand as _expand
except Exception:
    sys.stderr.write("guard_findings_write: resolver unavailable, variable-path check DISABLED\n")
    def _expand(t):
        return t
cmd_expanded = _expand(cmd)

WRITES = [
    r">>?\s*[^|;&\n]*state/findings/",
    r"\btee\b\s+(-a\s+)?[^|;&\n]*state/findings/",
    r"\bsed\b[^|;&\n]*-i[^|;&\n]*state/findings/",
    r"\b(cp|mv|rsync|install)\b[^|;&\n]*state/findings/",
    r"\b(truncate|shred|rm)\b[^|;&\n]*state/findings/",
    r"\bdd\b[^|;&\n]*of=[^|;&\n]*state/findings/",
    r"open\(\s*[\x27\"][^\x27\"]*state/findings/[^\x27\"]*[\x27\"]\s*,\s*[\x27\"][aw]",
]
for pat in WRITES:
    if re.search(pat, cmd) or re.search(pat, cmd_expanded):
        # The ONE legitimate writer. If emit_finding is what is running, this IS the caused path.
        if re.search(r"emit_finding(\.py)?\b", cmd):
            print("OK"); raise SystemExit(0)
        print("DENY"); raise SystemExit(0)

print("OK")
')

case "$EVAL" in
  DENY)       deny ;;
  PARSE_FAIL) deny ;;   # fail-CLOSED: a guard that cannot read its input DENIES (hook-contract.md)
  *)          exit 0 ;;
esac
