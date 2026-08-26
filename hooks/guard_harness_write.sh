#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: this ships in the PUBLIC repo (LifehackMethod/lifehack-brain), not ClaudeOps. A student's
#      install lands the harness in a folder they control, and nothing stops them saving their own
#      work, or a customization, straight into that tree. Two DISTINCT ways that goes wrong, and a
#      student notices NEITHER at the moment it happens:
#        (1) a personal file saved inside the harness tree is destroyed, silently, the next time the
#            harness is updated/reinstalled — the update replaces the tree it lives in.
#        (2) an edit to an EXISTING harness file is silently reverted on the same update, with
#            nothing telling the student why their customization disappeared.
#      The maintainer's own version of this mistake is at least visible to them (they know the repo
#      layout). A student does not, so the deny text below names whichever danger actually applies,
#      by name — a generic "blocked" message fails this job.
# GUARDS: a Write or Edit whose target resolves inside the installed harness tree (computed from
#      THIS SCRIPT's own on-disk location, exactly the way shared/brain_root.py's harness_root()
#      does it — so it is correct wherever INSTALL.md actually put the clone, not a hardcoded guess
#      at a path like ~/.claude/plugins/cache/lifehack-brain/) and is NOT one of the tree's own
#      generated build outputs (__pycache__/, *.pyc, .pytest_cache/, node_modules/, .git/ internals).
# REDIRECT: the student's own AI Brain path, resolved the ONE way this system ever resolves it —
#      `shared/brain_root.py`. If that resolves to NOT-SET, this guard denies with the exact
#      NOT-SET message rather than inventing or guessing a path (brain_root.py's own rule: "never a
#      default, never a fallback, never a guess").
# SIGNPOST: shared/brain_root.py (the one resolver) + INSTALL.md (where the harness actually lands)
#      + system/hook-contract.md (this hook's mechanics). Change the rule there first.
# FAIL_POSTURE: closed — unparseable stdin, an unresolvable path, or any python failure DENIES.
# UPDATED: 2026-08-25 (spec draft — see P.A3-public-pr-draft.md for the dry-run evidence this was
#      built and verified against).
# ─────────────────────────────────────────────────────────────────────────────
# guard_harness_write.sh — PreToolUse hook (matcher: Write|Edit)
#
# ⚠ Ships in hooks/ at the PUBLIC repo root (LifehackMethod/lifehack-brain), NOT under
#   system/hooks/ — that path is ClaudeOps's own tree and this hook is not a ClaudeOps hand-apply.
#   See hooks/hooks.json entry in the deliverable doc for the exact registration.

set -u

deny() {
  # $1 = JSON string already fully assembled
  printf '%s\n' "$1" >&2
  exit 2
}

INPUT=$(cat 2>/dev/null)
if [ -z "$INPUT" ]; then
  deny '{"decision":"block","reason":"BLOCKED: guard_harness_write got no stdin at all, so it cannot tell what is being written or where. Failing closed rather than guessing. RULE: system/hook-contract.md — a guard that cannot parse its input must deny, never allow."}'
fi

# Locate the harness root the SAME way shared/brain_root.py's harness_root() does: derived from
# THIS FILE's own on-disk position (repo root = the folder this hooks/ directory sits directly
# under), never from cwd, never hardcoded. That is what makes this correct wherever INSTALL.md
# actually placed the clone, instead of only on a machine where it landed at one guessed path.
HOOK_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
if [ -z "$HOOK_DIR" ]; then
  deny '{"decision":"block","reason":"BLOCKED: guard_harness_write could not resolve its own directory, so it cannot compute the harness root it is supposed to protect. Failing closed."}'
fi
REPO="$(cd "$HOOK_DIR/.." 2>/dev/null && pwd)"
if [ -z "$REPO" ] || [ ! -f "$REPO/shared/brain_root.py" ]; then
  deny '{"decision":"block","reason":"BLOCKED: guard_harness_write expected shared/brain_root.py one directory above hooks/ and did not find it, so it cannot resolve either the harness root or the AI Brain redirect. Failing closed rather than guessing a path. RULE: shared/brain_root.py, system/hook-contract.md."}'
fi

RESULT=$(REPO="$REPO" printf '%s' "$INPUT" | REPO="$REPO" python3 -c "
import sys, json, os

repo = os.environ['REPO']
sys.path.insert(0, os.path.join(repo, 'shared'))

try:
    d = json.load(sys.stdin)
except Exception:
    print('PARSE_ERROR')
    sys.exit()

tool_name = (d.get('tool_name') or '').strip()
ti = d.get('tool_input') or {}
raw_path = ti.get('file_path') or ti.get('path') or ''
if not raw_path:
    print('PARSE_ERROR')
    sys.exit()

try:
    target = os.path.realpath(os.path.expanduser(raw_path))
except Exception:
    print('PARSE_ERROR')
    sys.exit()

try:
    harness = os.path.realpath(repo)
except Exception:
    print('PARSE_ERROR')
    sys.exit()

inside = (target == harness) or target.startswith(harness + os.sep)
if not inside:
    print('ALLOW_OUTSIDE')
    sys.exit()

# The tree's OWN build outputs -- mechanical, generated, never a student's own material.
# Assembled from path FRAGMENTS, never as a bare keyword the guard's own docstring could trip on.
rel = os.path.relpath(target, harness)
parts = rel.split(os.sep)
build_markers = ('__pycache__', '.pytest_cache', 'node_modules')
is_build = (
    any(p in build_markers for p in parts)
    or rel.endswith('.pyc')
    or parts[0] == '.git'
)
if is_build:
    print('ALLOW_BUILD_OUTPUT|' + rel)
    sys.exit()

exists = os.path.exists(target)
danger = 'DANGER2_EDIT_REVERTED' if exists else 'DANGER1_SILENT_DESTROY'

try:
    import brain_root
    source, broot = brain_root.resolve_brain_root()
except Exception:
    print('BRAIN_ROOT_RESOLVE_ERROR|' + danger + '|' + rel)
    sys.exit()

if broot is None:
    print('BRAIN_ROOT_NOT_SET|' + danger + '|' + rel)
else:
    print('DENY|' + danger + '|' + rel + '|' + broot)
")

case "$RESULT" in
  ALLOW_OUTSIDE|ALLOW_BUILD_OUTPUT*)
    exit 0
    ;;
  PARSE_ERROR)
    deny '{"decision":"block","reason":"BLOCKED: guard_harness_write could not read the tool input or the target path, so it is failing closed. RULE: system/hook-contract.md — an unreadable write and a harmless one must never look the same."}'
    ;;
  BRAIN_ROOT_RESOLVE_ERROR*)
    REL="${RESULT#*|*|}"
    deny "{\"decision\":\"block\",\"reason\":\"BLOCKED: this write targets the installed harness tree (${REL}), and guard_harness_write also failed while trying to resolve your AI Brain redirect. Failing closed rather than guessing where your AI Brain lives. Fix: run \`python3 shared/brain_root.py\` yourself to see what is going wrong, then retry. RULE: shared/brain_root.py.\"}"
    ;;
  BRAIN_ROOT_NOT_SET*)
    _T="${RESULT#BRAIN_ROOT_NOT_SET|}"; DANGER="${_T%%|*}"; REL="${_T#*|}"
    if [ "$DANGER" = "DANGER1_SILENT_DESTROY" ]; then
      WHY="WHY: this looks like your own file, saved inside the installed harness (${REL}). The harness folder is the PROGRAM, not your writing -- the next time it is updated or reinstalled, that folder is replaced, and a file saved inside it is destroyed with no warning at the moment it happens."
    else
      WHY="WHY: this edits a file that is already part of the installed harness (${REL}). A customization made in place is exactly what an update or reinstall silently reverts -- your change disappears, and nothing tells you it happened or why."
    fi
    deny "{\"decision\":\"block\",\"reason\":\"BLOCKED: ${WHY} REDIRECT: this should go in your own AI Brain, not the harness -- but your AI Brain root is NOT SET, so no redirect path can be given. NOT-SET -- no \\\$LIFEHACK_ROOT, no .brain-root pointer in this repo, no persisted ~/.config/lifehack/brain-root, and no legacy Drive folder found. This guard will never guess a folder or fall back to the harness itself. Fix: python3 shared/brain_root.py --set <path> (add --create for a new folder), then retry. RULE: shared/brain_root.py, system/hook-contract.md.\"}"
    ;;
  DENY*)
    _T="${RESULT#DENY|}"; DANGER="${_T%%|*}"; _T2="${_T#*|}"; REL="${_T2%%|*}"; BROOT="${_T2#*|}"
    if [ "$DANGER" = "DANGER1_SILENT_DESTROY" ]; then
      WHY="WHY: this looks like your own file, saved inside the installed harness (${REL}). The harness folder is the PROGRAM, not your writing -- the next time it is updated or reinstalled, that folder is replaced, and a file saved inside it is destroyed with no warning at the moment it happens."
    else
      WHY="WHY: this edits a file that is already part of the installed harness (${REL}). A customization made in place is exactly what an update or reinstall silently reverts -- your change disappears, and nothing tells you it happened or why."
    fi
    deny "{\"decision\":\"block\",\"reason\":\"BLOCKED: ${WHY} REDIRECT: save this in your own AI Brain instead -- ${BROOT} -- which the harness never touches on update. RULE: shared/brain_root.py, system/hook-contract.md.\"}"
    ;;
  *)
    deny '{"decision":"block","reason":"BLOCKED: guard_harness_write ended in a state it does not recognise, so it is failing closed."}'
    ;;
esac
