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
# GUARDS: any WRITE INTO state/findings/ (bypassing `emit_finding.py`) OR state/recommendations/
#      (bypassing `emit_recommendation.py`) — a shell redirect (> or >>), tee, sed -i, cp/mv/rsync
#      into the store, truncate/shred/rm, dd of=, a python open(...,"a"/"w"), or a Write/Edit tool
#      call targeting a shard. Each store checks its OWN designated writer only — naming
#      `emit_finding.py` on a command never legitimizes a write into state/recommendations/, and
#      naming `emit_recommendation.py` never legitimizes one into state/findings/. READS are NEVER
#      blocked: cat/grep/ls/wc/head/tail are how findings_reader.py, recommendations_reader.py,
#      health_line.py and a human inspect either store, and blocking them would break the
#      consumers this subsystem was built to feed.
# REDIRECT: emit a finding or a recommendation the ONE validated way, per store —
#      FINDINGS: `python3 system/tools/emit_finding.py --producer <name> --status <OK|ERROR|
#      NEEDS_REVIEW|NEEDS_APPROVAL> --scanned-n <REAL count examined> --label job=<x> --label
#      kind=<y> --summary "<what>"` (or, from Python: `from emit_finding import emit_finding`).
#      RECOMMENDATIONS: `python3 system/tools/emit_recommendation.py --producer <name> --altitude
#      <INSTANCE|SUBSYSTEM|ORGANISM|DECISION> --action "<what to do>" --summary "<why>" --evidence
#      <finding-fingerprint> [--evidence <more>] --label <k>=<v>` (or, from Python: `from
#      emit_recommendation import emit_recommendation`). The fingerprint and the file path are
#      computed FOR you in both cases — that is the point.
# SIGNPOST: the rule for state/findings/ lives in system/tools/emit_finding.py's module docstring
#      (why no id=, why scanned_n has no default); the rule for state/recommendations/ lives in
#      system/tools/emit_recommendation.py's module docstring (why no id=/fingerprint=, why
#      evidence has no default). Both resolve their store path through shared/brain_root.py. To
#      change what is protected: edit this guard, get sign-off, then update its settings.json
#      registration — see system/hook-contract.md.
# FAIL_POSTURE: closed — an unparseable payload DENIES.
# UPDATED: 2026-08-14 (ported from claudeops-config's guard_findings_write.sh; scope narrowed to
#      state/findings/ ONLY because neither emit_recommendation.py nor any recommendations/
#      concept existed in this repo at port time — confirmed absent that session). SAME DAY,
#      LATER PASS: that assumption is now STALE. system/tools/emit_recommendation.py exists and
#      is live, with a working chain behind it (recommend.py and seam_reason.py write through it;
#      recommendations_reader.py and recommendation_disposition.py read it) — an independent
#      fire-test had already found this guard PARTIAL for exactly that reason: a fresh install
#      had NO write-guard on the recommendations store. Closed below. Two things differ from the
#      original port, one of them just now:
#        1. SCOPE NOW COVERS BOTH VALIDATED STORES, EACH WITH ITS OWN WRITER CHECK. This EXTENDS
#           the original protection; it does not touch or relax the existing state/findings/
#           behavior in any way — see system/hooks/tests/test_findings_and_delegation.sh, which
#           still asserts every original findings case unchanged, alongside the new
#           state/recommendations/ cases.
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
# Blocks any write into the Hospital findings store (state/findings/) that bypasses
# emit_finding.py, OR the Efficiency recommendations store (state/recommendations/) that
# bypasses emit_recommendation.py. Each store is checked, and each store's writer is
# recognized, independently — see the UPDATED note above.

set -uo pipefail

_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd -P)"
REPO="${CLAUDE_PROJECT_DIR:-${_HOOKDIR%/system/hooks}}"

DENY_FINDINGS='{"decision":"block","reason":"BLOCKED: a direct write into a VALIDATED STORE - state/findings/ (Hospital). WHY: a finding must be CAUSED, never GENERATED. emit_finding.py computes the fingerprint from the label set, derives the machine token, and refuses the dishonest case (scanned_n==0 paired with status=OK). A hand-authored line forges all of it, and a forged record is an opinion wearing a machine authority. REDIRECT - python3 system/tools/emit_finding.py --producer <name> --status <OK|ERROR|NEEDS_REVIEW|NEEDS_APPROVAL> --scanned-n <REAL count EXAMINED> --label job=<x> --summary \"<what>\" (from Python: from emit_finding import emit_finding). READS are not blocked - cat/grep/ls the store freely. RULE: system/tools/emit_finding.py module docstring; to change what is protected, edit system/hooks/guard_findings_write.sh, get sign-off, then re-verify per system/hook-contract.md."}'
DENY_RECS='{"decision":"block","reason":"BLOCKED: a direct write into a VALIDATED STORE - state/recommendations/ (Efficiency). WHY: a recommendation must be CAUSED by cited findings, never GENERATED by hand. emit_recommendation.py computes the fingerprint from the label set, requires --evidence (real finding fingerprints) with no default, and refuses the dishonest case (empty/invalid evidence) while still writing a canary record so the refusal is never silent. A hand-authored line forges all of it, and a forged record is an opinion wearing a machine authority. REDIRECT - python3 system/tools/emit_recommendation.py --producer <name> --altitude <INSTANCE|SUBSYSTEM|ORGANISM|DECISION> --action \"<what to do>\" --summary \"<why>\" --evidence <finding-fingerprint> [--evidence <more>] --label <k>=<v> (from Python: from emit_recommendation import emit_recommendation). READS are not blocked - cat/grep/ls the store freely. RULE: system/tools/emit_recommendation.py module docstring; to change what is protected, edit system/hooks/guard_findings_write.sh, get sign-off, then re-verify per system/hook-contract.md."}'
DENY_NOLIB='{"decision":"block","reason":"BLOCKED: guard_findings_write could not load system/hooks/lib/winpath_fold.py, the path-form normaliser it uses to recognise a write target whatever way the path is spelled. WHY: without it, a Windows-native path into a validated store is not recognised as one and this guard returns OK silently - so it fails CLOSED instead. REDIRECT - confirm system/hooks/lib/winpath_fold.py exists and is readable, then retry; if you are writing a finding, the sanctioned writer is python3 system/tools/emit_finding.py. RULE: system/hooks/lib/winpath_fold.sh header, and system/hook-contract.md."}'
DENY_UNKNOWN='{"decision":"block","reason":"BLOCKED: hook input could not be parsed, so guard_findings_write.sh fails CLOSED (hook-contract.md) rather than guessing which validated store was targeted. A write is denied whenever it cannot be proven safe. If this was a legitimate emit_finding.py or emit_recommendation.py call, re-run it as a normal Bash/Write/Edit tool call with valid JSON tool_input."}'
deny() { printf '%s\n' "$1" >&2; exit 2; }

INPUT=$(cat)

# An EMPTY stdin is a bare manual invocation, not a tool call — nothing to adjudicate.
[ -z "$INPUT" ] && exit 0

export GFW_TOOLS_DIR="$REPO/system/tools"
# The path-form normaliser, loaded by the python below. Same GUARD_LIB convention this hook
# plane already uses for lib/gws_guard.py. Without it every path test here is forward-slash
# only, so a Windows-native target sails through this guard silently -- see lib/winpath_fold.sh.
export GFW_WINFOLD_LIB="$REPO/system/hooks/lib/winpath_fold.py"

EVAL=$(printf '%s' "$INPUT" | python3 -c '
import sys, json, os, re

try:
    d = json.load(sys.stdin)
except Exception:
    print("PARSE_FAIL"); raise SystemExit(0)

ti = d.get("tool_input", {}) or {}

# WINDOWS PATH FOLD. Every pattern in this file is forward-slash only, and a Write/Edit
# file_path arrives BACKSLASH-NATIVE on Windows, so without folding first this guard returns
# OK for a real write into a validated store -- silently, with no output at all. FAIL_POSTURE
# for this hook is CLOSED, so a missing normaliser DENIES rather than degrading to the
# unfolded comparison, which is the exact hole being closed.
_lib = os.environ.get("GFW_WINFOLD_LIB", "")
if not _lib or not os.path.isfile(_lib):
    print("NOLIB"); raise SystemExit(0)
import importlib.util
_spec = importlib.util.spec_from_file_location("winpath_fold", _lib)
_wf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_wf)

# Both validated stores, each matched on the PATH SEGMENT so a lookalike
# ("my-state/findings-notes") does NOT match. Kept as an ordered list (not a single combined
# regex) so each store can carry its OWN name and OWN writer allowance below.
STORES = [
    ("FINDINGS", re.compile(r"(^|/)state/findings/"), "state/findings/"),
    ("RECS",     re.compile(r"(^|/)state/recommendations/"), "state/recommendations/"),
]

def _store_hit(text):
    # Fold here rather than at each call site: this is the one place both the Write/Edit
    # door and the Bash door funnel through, so one fold covers both and cannot drift apart.
    text = _wf.winfold(text)
    for name, pat, _frag in STORES:
        if pat.search(text):
            return name
    return None

# Write / Edit tools: the target is a path, so this is unambiguous.
for key in ("file_path", "notebook_path"):
    p = ti.get(key) or ""
    if p:
        hit = _store_hit(p)
        if hit:
            print("DENY:" + hit); raise SystemExit(0)

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
# Fold the command text as well: the write-verb patterns below embed the store fragment with
# forward slashes, so a Windows-spelled redirect target inside a Bash command would not match
# them either. Folded copies only -- the originals are what the WRITER allowance is read from.
cmd_cmp = _wf.winfold(cmd)
cmd_expanded_cmp = _wf.winfold(cmd_expanded)

def _write_patterns(frag):
    return [
        rf">>?\s*[^|;&\n]*{frag}",
        rf"\btee\b\s+(-a\s+)?[^|;&\n]*{frag}",
        rf"\bsed\b[^|;&\n]*-i[^|;&\n]*{frag}",
        rf"\b(cp|mv|rsync|install)\b[^|;&\n]*{frag}",
        rf"\b(truncate|shred|rm)\b[^|;&\n]*{frag}",
        rf"\bdd\b[^|;&\n]*of=[^|;&\n]*{frag}",
        rf"open\(\s*[\x27\"][^\x27\"]*{frag}[^\x27\"]*[\x27\"]\s*,\s*[\x27\"][aw]",
    ]

# The ONE legitimate writer PER STORE. Deliberately NOT one shared writer regex: a command that
# happens to mention emit_finding.py must never wave a write into state/recommendations/ through
# (and the reverse), so each store checks its own allowance in isolation.
WRITER = {"FINDINGS": r"emit_finding(\.py)?\b", "RECS": r"emit_recommendation(\.py)?\b"}

for name, _pat, frag in STORES:
    for pat in _write_patterns(frag):
        if re.search(pat, cmd_cmp) or re.search(pat, cmd_expanded_cmp):
            if re.search(WRITER[name], cmd):
                print("OK"); raise SystemExit(0)
            print("DENY:" + name); raise SystemExit(0)

print("OK")
')

case "$EVAL" in
  DENY:FINDINGS) deny "$DENY_FINDINGS" ;;
  DENY:RECS)     deny "$DENY_RECS" ;;
  PARSE_FAIL)    deny "$DENY_UNKNOWN" ;;   # fail-CLOSED: unreadable input DENIES (hook-contract.md)
  NOLIB)         deny "$DENY_NOLIB" ;;     # fail-CLOSED: without the path normaliser this guard
                                          # cannot tell a Windows-spelled target from an unrelated one
  *)             exit 0 ;;
esac
