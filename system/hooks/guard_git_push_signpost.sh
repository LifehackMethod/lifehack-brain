#!/bin/bash
#
# ══════════════════════════════════════════════════════════════════════════════
# ⚠  SPEED BUMP, NOT A BOUNDARY.  Read this before you trust this file.
#
#  This guard inspects a command as TEXT. A shell has infinite equivalent ways to
#  spell the same command, so a text matcher is always one phrasing behind. Treat
#  what follows as a speed bump that raises the cost of a mistake — never as a wall
#  that makes one impossible. Same posture as guard_gh_pr_merge.sh, whose shape this
#  hook copies: first attempt denies and TEACHES, a second attempt passes once.
# ══════════════════════════════════════════════════════════════════════════════
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: Enver's stated failure mode (design brief, 2026-09-02): "by push time I just
#      approve, because I can't tell what's in it." A `git push` is the moment work
#      leaves the private working tree — for the Lifehack repo it SHIPS to every
#      student the instant it lands on main — and nothing paused to show what is
#      actually going out before that moment.
# GUARDS: DENIES a real `git push` subcommand (never a mere MENTION — tokenized, see
#      MATCHING) on the FIRST attempt of a session, printing which repo (private/
#      public), the branch and its remote target, and the commit/file manifest that
#      would leave the machine. ALLOWS every other git verb untouched: status, diff,
#      log, fetch, pull, add, commit, branch, checkout, stash, show, blame.
# REDIRECT: read the printed manifest, confirm it is what you meant to ship, and if
#      genuinely unsure which repo this belongs in — STOP and ask; never guess harness
#      vs personal. Then re-run the exact same push.
# SIGNPOST: system/sops/github-sop.md §0c — the branch/push decision. To change what
#      is gated here, edit that SOP + get sign-off, then update this guard.
# MATCHING: argv STRUCTURE via shlex, never a keyword grep on the command string — a
#      literal "git push" inside a quoted commit message must not trip it. Segments
#      split on ; && || |; only a token that IS literally `git` (or ends in /git),
#      followed by the literal subcommand `push`, counts. On a shlex failure (heredoc,
#      unbalanced quote) we fall back to a raw-text adjacency scan for `git push` as a
#      shape, same fallback guard_gh_pr_merge.sh uses, and deny only if that shape is
#      present.
# IDENTITY: resolved from the COMMAND, never bare `$PWD` — fixed 2026-09-08 after a
#      real incident: a push from a ClaudeOps cwd targeting `git -C
#      ~/lifehack-brain push origin main` was signposted as "ClaudeOps
#      PRIVATE" — the wrong repo, confidently. This hook is a PreToolUse hook, so it
#      runs BEFORE the command — it can never observe a `cd` that hasn't happened
#      yet, so it tracks one explicitly instead: an explicit `-C <path>` on the
#      matched git invocation, or a `cd <path>` earlier in the same `&&`/`;` chain
#      (dropped, not trusted, across `|`/`||` — a `cd` before a pipe runs in a
#      subshell and never takes effect on what follows; a `cd` before `||` only ran
#      if the left side failed). An explicit `-C` on the push's own invocation wins
#      over an inherited `cd` — confirmed against real git behaviour (`git -C B`, run
#      from a cwd `cd`'d to A, resolves to B), not assumed. Falls back to `$PWD` only
#      when NEITHER is present (no regression on a plain `git push`). If a `-C`/`cd`
#      path WAS given but does not resolve to a real directory, this hook REFUSES
#      rather than silently falling back to `$PWD` — printing a guess is worse than
#      admitting it cannot tell.
# FAIL_POSTURE: closed — an unreadable hook payload denies. A command shlex cannot
#      tokenize falls back to the raw-text adjacency scan above and denies only if
#      that still reads as `git push`. SILENT (exit 0) when there is no command to
#      judge, or the command is a genuinely different git verb.
# UPDATED: 2026-09-08
# RULE: system/sops/github-sop.md §0c — system/hook-contract.md (mechanics)
# ─────────────────────────────────────────────────────────────────────────────
# guard_git_push_signpost.sh — PreToolUse hook (matcher: Bash)

INPUT=$(cat 2>/dev/null)

VERDICT=$(printf '%s' "$INPUT" | python3 -c '
import sys, json, shlex, os

try:
    d = json.load(sys.stdin)
except Exception:
    print("PARSE_ERROR"); raise SystemExit

cmd = ((d.get("tool_input") or {}).get("command") or "")
if not cmd.strip():
    print("NOT_OURS"); raise SystemExit

try:
    toks = shlex.split(cmd, comments=False, posix=True)
except ValueError:
    import re as _re
    _shape = _re.compile(r"(^|[;&|(\s])git\s+(-{1,2}\S+\s+)*push\b")
    if _shape.search(cmd):
        print("DENY\t"); raise SystemExit
    print("NOT_OURS"); raise SystemExit

# (segment, operator-that-PRECEDES-it) pairs. A cd before an AND/semicolon
# reliably takes effect on what follows; a cd before a PIPE runs in a
# pipeline subshell and never touches the rest of the command, and a cd
# before OR only ran if the left side failed — neither is trustworthy, so
# cwd tracking is dropped, not guessed, across those two.
segments, buf, op = [], [], None
for t in toks:
    if t in ("&&", "||", ";", "|"):
        if buf: segments.append((buf, op))
        buf = []
        op = t
    else:
        buf.append(t)
if buf: segments.append((buf, op))

def is_git(tok):
    return os.path.basename(tok) == "git"

cwd = ""
for seg, preceding_op in segments:
    if preceding_op in ("|", "||"):
        cwd = ""

    if seg and seg[0] == "cd":
        target = ""
        for tok in seg[1:]:
            if not tok.startswith("-"):
                target = tok
                break
        if target:
            cwd = target
        continue

    i = 0
    while i < len(seg) and "=" in seg[i] and not seg[i].startswith("-"):
        i += 1
    if i >= len(seg) or not is_git(seg[i]):
        continue
    j = i + 1
    cdir = ""
    while j < len(seg) and seg[j].startswith("-"):
        if seg[j] in ("-C", "-c"):
            if seg[j] == "-C" and j + 1 < len(seg):
                cdir = seg[j + 1]
            j += 2
        else:
            j += 1
    if j < len(seg) and seg[j] == "push":
        # explicit -C wins over an inherited cd — confirmed against real git behaviour
        resolved = cdir if cdir else cwd
        print("DENY\t" + resolved); raise SystemExit

print("OK")
' 2>/dev/null)

case "$VERDICT" in
  PARSE_ERROR)
    printf '%s\n' "BLOCKED (push signpost): the hook payload itself was not readable JSON. WHY: failing OPEN would let an unreadable push slip past unseen. REDIRECT: retry the command. RULE: system/sops/github-sop.md section 0c -- FAIL_POSTURE: closed." >&2
    exit 2
    ;;
  "")
    printf '%s\n' "BLOCKED (push signpost): the hook payload itself was not readable JSON. WHY: failing OPEN would let an unreadable push slip past unseen. REDIRECT: retry the command. RULE: system/sops/github-sop.md section 0c -- FAIL_POSTURE: closed." >&2
    exit 2
    ;;
esac

REQUESTED_DIR="${VERDICT#*$'\t'}"
[ "$REQUESTED_DIR" = "$VERDICT" ] && REQUESTED_DIR=""
VERDICT="${VERDICT%%$'\t'*}"

case "$VERDICT" in
  OK|NOT_OURS)
    exit 0
    ;;
  DENY)
    # a -C/cd target was named but does not resolve — refuse rather than guess
    if [ -n "$REQUESTED_DIR" ] && [ ! -d "$REQUESTED_DIR" ]; then
      printf '📍 PUSH · cannot determine the target repo\n' >&2
      printf '   The command names a path (%s) that does not exist here.\n' "$REQUESTED_DIR" >&2
      printf '   WHY: printing a guess about which repo this pushes to is worse than admitting the guard cannot tell.\n' >&2
      printf '   REDIRECT: verify the path, then re-run.\n' >&2
      printf '   -> system/sops/github-sop.md section 0c\n' >&2
      exit 2
    fi

    REPO_DIR="$PWD"
    if [ -n "$REQUESTED_DIR" ] && [ -d "$REQUESTED_DIR" ]; then REPO_DIR="$REQUESTED_DIR"; fi

    _key="${CLAUDE_CODE_SESSION_ID:-$PWD}"
    _hash=$(printf '%s' "$_key" | shasum 2>/dev/null | cut -c1-12)
    [ -n "$_hash" ] || _hash="default"
    _bump="$HOME/.claude/.push-signpost.$_hash"
    if [ -f "$_bump" ]; then
      rm -f "$_bump"
      exit 0
    fi
    : > "$_bump" 2>/dev/null || true

    _branch=$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null)
    [ -n "$_branch" ] || _branch="UNKNOWN"
    _repo_name=$(basename "$(git -C "$REPO_DIR" rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null)
    [ -n "$_repo_name" ] || _repo_name="UNKNOWN"
    _push_url=$(git -C "$REPO_DIR" remote get-url --push origin 2>/dev/null)
    _remote_name="origin"
    if [ -z "$_push_url" ]; then
      _first_remote=$(git -C "$REPO_DIR" remote 2>/dev/null | head -1)
      if [ -n "$_first_remote" ]; then
        _remote_name="$_first_remote"
        _push_url=$(git -C "$REPO_DIR" remote get-url --push "$_first_remote" 2>/dev/null)
      fi
    fi
    case "$_push_url" in
      *LifehackMethod/lifehack-brain*) _kind="⚠⚠ PUBLIC -- SHIPS TO STUDENTS ⚠⚠" ;;
      *egjokaj/ClaudeOps*)             _kind="PRIVATE — students never see this" ;;
      "")                              _kind="UNKNOWN — no push remote resolved; STOP and verify by hand" ;;
      *)                               _kind="UNKNOWN — unrecognized remote ($_push_url); STOP and verify by hand" ;;
    esac

    # ── manifest: what would actually leave the machine ──────────────────────
    _range=""
    if git -C "$REPO_DIR" rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
      _range='@{u}..HEAD'
    elif [ -n "$_branch" ] && [ "$_branch" != "UNKNOWN" ] && git -C "$REPO_DIR" rev-parse --verify "$_remote_name/$_branch" >/dev/null 2>&1; then
      _range="$_remote_name/$_branch..HEAD"
    fi

    if [ -n "$_range" ]; then
      _commit_count=$(git -C "$REPO_DIR" log --oneline "$_range" 2>/dev/null | wc -l | tr -d ' ')
      _files=$(git -C "$REPO_DIR" diff --name-only "$_range" 2>/dev/null)
      _file_count=$(printf '%s\n' "$_files" | grep -c . )
      _file_list=$(printf '%s\n' "$_files" | head -10 | sed 's/^/     /')
      _extra=$((_file_count - 10))
    else
      _commit_count="UNRESOLVED"
      _file_count="UNRESOLVED"
      _file_list="     (no upstream/matching remote branch found -- likely a brand-new branch; verify manually with git log/diff before pushing)"
      _extra=0
    fi

    {
      printf '📍 PUSH · %s (%s)\n' "$_repo_name" "$_kind"
      printf '   %s -> %s/%s\n' "$_branch" "$_remote_name" "$_branch"
      printf '   %s commit(s), %s file(s) going out:\n' "$_commit_count" "$_file_count"
      printf '%s\n' "$_file_list"
      if [ "$_extra" -gt 0 ] 2>/dev/null; then
        printf '     +%s more\n' "$_extra"
      fi
      printf '   Not sure which repo this belongs in? STOP and ask. Never guess harness vs personal.\n'
      printf '   WHY: "by push time I just approve, because I cant tell whats in it" -- this is the fix. Identity above was read from the real git remote, not guessed.\n'
      printf '   -> system/sops/github-sop.md section 0c\n'
      printf '   (run the same push again to proceed -- this fires once per session)\n'
    } >&2
    exit 2
    ;;
  *)
    printf '%s\n' "BLOCKED (push signpost): the hook payload itself was not readable JSON. WHY: failing OPEN would let an unreadable push slip past unseen. REDIRECT: retry the command. RULE: system/sops/github-sop.md section 0c -- FAIL_POSTURE: closed." >&2
    exit 2
    ;;
esac
