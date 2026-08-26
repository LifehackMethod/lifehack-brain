#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: ClaudeOps is the operator's PRIVATE repo. lifehack-brain (github.com/LifehackMethod/lifehack-brain,
#      checked out locally at ~/lifehack-brain) is the PUBLIC student harness. ClaudeOps currently
#      contains a duplicated copy of most of the harness, and that duplication is actively being
#      removed lane by lane (see migration-notes/). Once a harness file's ClaudeOps copy is deleted,
#      NOTHING must be able to write it back — an agent "helpfully" restoring a file it thinks went
#      missing, or a merge/copy operation reintroducing it, would silently re-create the exact
#      duplication this migration exists to end. Built as TASK N2 (plan task D3), 2026-08-23.
# GUARDS: a Write or Edit inside this ClaudeOps checkout whose target path is TRACKED in the public
#      lifehack-brain repo (i.e. `git ls-files` in ~/lifehack-brain finds it at that same relative
#      path). That is a harness file — block it. A path lifehack-brain does not track is presumed
#      personal/private ClaudeOps material — allow it.
# REDIRECT: harness changes belong in ~/lifehack-brain itself (the public repo), on a branch,
#      offered back as a PR — never written into this private repo. See INSTALL.md and
#      system/organism/elements/where-things-live.md ("For everyone -> this repo [lifehack-brain],
#      on a branch, offered back as a PR").
# SIGNPOST: the duplication-removal effort is tracked in migration-notes/ at this repo's root
#      (phase-1-lane-a.md, f3b-upstream-merge.md). To change WHICH paths this guard treats as
#      harness territory, do not edit a list here — there is none. Change what is tracked in
#      ~/lifehack-brain (or point LIFEHACK_BRAIN_ROOT elsewhere) and this guard follows automatically.
# DERIVATION (the load-bearing property): membership is NEVER a hand-typed list. It is asked of the
#      public repo at run time via `git -C <lifehack-brain> ls-files --error-unmatch -- <relpath>`.
#      Three separate defects this week (CRITICAL_HOOKS, UNSAFE_TO_PROBE, a deny list naming a
#      retired tool) all trace to a hand-maintained enumeration going stale. This guard has no such
#      list to go stale — it asks git, every time, against whatever lifehack-brain's HEAD/index
#      actually contains right now.
# FAIL_POSTURE: closed. Any state this guard cannot cleanly resolve to ALLOW or BLOCK — the public
#      repo missing, not a git repo, `git` unusable, the target path unresolvable — DENIES with a
#      CANNOT-DETERMINE reason on stderr and **exit 2**, never silently folded into exit 0 (allow).
#      ⚠ CORRECTED 2026-08-26: these sites previously used exit 3. `system/hook-contract.md:115-121`
#      defines ONLY 0 / 1 / 2 -- "exit 3" appears ZERO times in it -- and :121 states "a guard that
#      can't parse its input must DENY (exit 2), never exit 0". An unrecognised code is not a block,
#      so every CANNOT-DETERMINE path was FAILING OPEN. Caught by the red-then-green check before
#      this guard was ever registered. "The subject
#      was absent" and "the subject was checked and found clean" are different claims (the ratified
#      ABSENT-SUBJECT rule, system/hooks/tests/verify-pm-guard.sh). A caller that only understands
#      0/2 must treat any non-zero, including 3, as NOT-ALLOW.
# UPDATED: 2026-08-23
# ─────────────────────────────────────────────────────────────────────────────
# guard_harness_writeback.sh — PreToolUse hook (matcher: Write|Edit)
#
# Exit codes (deliberately three, not two):
#   0  ALLOW             — target is outside this repo, or not tracked by lifehack-brain.
#   2  BLOCK             — target IS tracked by lifehack-brain: a harness file. Deny + stderr.
#   3  CANNOT-DETERMINE  — could not reach/resolve the public repo or the target path. Deny-shaped
#                          stderr message, but its OWN exit code so it is never mistaken for a
#                          verified-clean ALLOW or a verified-harness BLOCK.

INPUT=$(cat)

# ── Resolve THIS repo's root (ClaudeOps), the same $0-relative-first pattern as
#    guard_write_paths.sh — CLAUDE_PROJECT_DIR is the session's launch cwd, not necessarily the repo
#    that declares this hook, so $0's own on-disk location is authoritative and CLAUDE_PROJECT_DIR
#    is only the fallback.
_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
_SELF_REPO="${_HOOKDIR%/system/hooks}"
[ -n "$_SELF_REPO" ] && [ -d "$_SELF_REPO/system/hooks" ] || _SELF_REPO="${CLAUDE_PROJECT_DIR:-}"

if [ -z "$_SELF_REPO" ] || [ ! -d "$_SELF_REPO" ]; then
  printf '%s\n' '{"decision":"block","reason":"CANNOT-DETERMINE: guard_harness_writeback could not resolve its own ClaudeOps repo root (neither $0-relative nor CLAUDE_PROJECT_DIR resolved to a real directory). WHY: without a repo root there is no way to compute the relative path lifehack-brain would be asked about, so ALLOW would be a guess, not a verified answer. REDIRECT: retry; if this persists the hook install is broken. RULE: system/hooks/guard_harness_writeback.sh header."}' >&2
  exit 2
fi

# ── Extract the write target, realpath-resolved so a relative path or a `..` segment cannot dodge
#    the comparison below (mirrors guard_write_paths.sh's FILE_PATH parsing).
FILE_PATH=$(printf '%s' "$INPUT" | python3 -c "
import sys, json, os
try:
    data = json.load(sys.stdin)
    ti = data.get('tool_input', {}) or {}
    path = ti.get('file_path') or ti.get('path') or ''
    if not path:
        print('')
    else:
        base = os.environ.get('_SELF_REPO') or os.getcwd()
        if not os.path.isabs(path):
            path = os.path.join(base, path)
        print(os.path.realpath(path))
except Exception:
    print('__PARSE_ERROR__')
" 2>/dev/null)

# Fail-closed: an unparseable payload is a distinct CANNOT-DETERMINE, not a silent allow.
if [ "$FILE_PATH" = "__PARSE_ERROR__" ]; then
  printf '%s\n' '{"decision":"block","reason":"CANNOT-DETERMINE: guard_harness_writeback could not parse the tool input, so it cannot compute a target path to check. WHY: allow-on-parse-error would be a silent, unverified pass. REDIRECT: retry the write; if it persists the payload is malformed. RULE: system/hooks/guard_harness_writeback.sh header."}' >&2
  exit 2
fi

# A genuinely-absent path (valid JSON, no file_path — not the Write|Edit shape) is a real no-op.
if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# ── Not our concern unless the write actually lands inside THIS repo.
case "$FILE_PATH" in
  "$_SELF_REPO"/*) : ;;
  *) exit 0 ;;
esac

REL_PATH="${FILE_PATH#"$_SELF_REPO"/}"
if [ -z "$REL_PATH" ] || [ "$REL_PATH" = "$FILE_PATH" ]; then
  printf '%s\n' "{\"decision\":\"block\",\"reason\":\"CANNOT-DETERMINE: guard_harness_writeback resolved a target under the ClaudeOps repo root but could not compute a relative path to check against lifehack-brain ($FILE_PATH). RULE: system/hooks/guard_harness_writeback.sh header.\"}" >&2
  exit 2
fi

# ── Locate the public repo. LIFEHACK_BRAIN_ROOT lets an operator point this at a relocated
#    checkout; the default matches this machine's actual layout (~/lifehack-brain, confirmed to
#    have origin = github.com/LifehackMethod/lifehack-brain.git this session). Never a hand-typed
#    path list of FILES — this is the one root path the derivation needs to start from.
BRAIN_ROOT="${LIFEHACK_BRAIN_ROOT:-$HOME/lifehack-brain}"

if [ ! -d "$BRAIN_ROOT/.git" ]; then
  printf '%s\n' "{\"decision\":\"block\",\"reason\":\"CANNOT-DETERMINE: the public lifehack-brain repo is not present at $BRAIN_ROOT (no .git there), so guard_harness_writeback cannot ask whether '$REL_PATH' is a harness file. WHY: with no public repo to check against, allowing would be an unverified guess and blocking-as-harness would be an unverified accusation -- neither is honest, so this reports its own outcome instead. REDIRECT: point LIFEHACK_BRAIN_ROOT at a real lifehack-brain checkout, or clone one, then retry. RULE: system/hooks/guard_harness_writeback.sh header (FAIL_POSTURE: closed).\"}" >&2
  exit 2
fi

# ── THE DERIVATION: ask the public repo, do not consult a list. `git ls-files --error-unmatch`
#    exits 0 if REL_PATH is tracked in lifehack-brain's index, 1 if it is a known-clean miss, and
#    anything else (128 = not a repo / git failure, etc.) is treated as CANNOT-DETERMINE rather than
#    silently coerced into either verified outcome.
GIT_OUT=$(git -C "$BRAIN_ROOT" ls-files --error-unmatch -- "$REL_PATH" 2>&1)
GIT_RC=$?

case "$GIT_RC" in
  0)
    printf '%s\n' "{\"decision\":\"block\",\"reason\":\"BLOCKED: '$REL_PATH' is tracked in the PUBLIC lifehack-brain repo ($BRAIN_ROOT) -- this write targets a harness file inside the PRIVATE ClaudeOps repo. WHY: ClaudeOps still carries a duplicated copy of most of the harness that is actively being removed (migration-notes/); writing a harness file back here would silently re-create that duplication. REDIRECT: make this change in $BRAIN_ROOT itself, on a branch, offered back as a PR -- never written into ClaudeOps. RULE: system/organism/elements/where-things-live.md ('for everyone -> this repo, on a branch, offered back as a PR'); membership was DERIVED via git ls-files against $BRAIN_ROOT just now, not read from a list.\"}" >&2
    exit 2
    ;;
  1)
    exit 0
    ;;
  *)
    printf '%s\n' "{\"decision\":\"block\",\"reason\":\"CANNOT-DETERMINE: asking $BRAIN_ROOT whether '$REL_PATH' is a harness file failed in an unexpected way (git exit $GIT_RC: ${GIT_OUT}). WHY: neither a verified ALLOW nor a verified BLOCK can be produced from a failed lookup -- reporting an unverified pass here is exactly the silent-ALLOW-on-error failure this repo's hooks have been burned by before. REDIRECT: check that $BRAIN_ROOT is a healthy git checkout ('git -C $BRAIN_ROOT status') and that git is on PATH, then retry. RULE: system/hooks/guard_harness_writeback.sh header (FAIL_POSTURE: closed).\"}" >&2
    exit 2
    ;;
esac
