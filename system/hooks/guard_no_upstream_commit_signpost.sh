#!/bin/bash
#
# ══════════════════════════════════════════════════════════════════════════════
# ⚠  SPEED BUMP, NOT A BOUNDARY.  Read this before you trust this file.
#
#  This guard inspects a command as TEXT. A shell has infinite equivalent ways to
#  spell the same command, so a text matcher is always one phrasing behind. Treat
#  what follows as a speed bump that raises the cost of a mistake — never as a wall
#  that makes one impossible. Same posture as guard_git_commit_signpost.sh (private
#  repo), whose shape this hook copies: first attempt denies and TEACHES, a rerun
#  on the same session/repo/branch passes silently from then on.
# ══════════════════════════════════════════════════════════════════════════════
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: Enver, 2026-09-08: "whenever it goes to commit it should have a reminder
#      not to be committing to some random branch." A local branch with no
#      remote counterpart drifts silently — MIRROR ROT — and the commit moment
#      is when work is about to be stranded there. (O3, re-ruled from an earlier
#      branch-birth design to fire on commit instead.)
# GUARDS: DENIES a real `git commit` subcommand (never a mere MENTION — tokenized,
#      see MATCHING) the FIRST time it runs on the current (session, repo, branch)
#      triple, when the current branch has NO upstream configured OR an upstream
#      whose remote counterpart is gone. SILENT on any branch with a live
#      upstream (main, V2, and any tracked feature branch alike) and on every
#      other git verb.
# REDIRECT: read the printed line, decide whether this branch should have a
#      remote counterpart, then re-run the exact same commit — it proceeds.
# SIGNPOST: the map line this points at is O2's home in the Harness CLAUDE.md
#      (placeholder until that lands: "CLAUDE.md map: no-upstream").
# MATCHING: argv STRUCTURE via shlex, never a keyword grep on the command string
#      — a literal "git commit" inside a quoted commit message must not trip it.
#      Segments split on ; && || |; only a token that IS literally `git` (or
#      ends in /git), followed by the literal subcommand `commit`, counts.
#      On a shlex failure (heredoc, unbalanced quote) this hook stands DOWN
#      silently — see FAIL_POSTURE — never a raw-text fallback for a SPEED BUMP
#      this soft.
# IDENTITY: resolved from the COMMAND, never `$PWD` — the push guard's own
#      2026-09-08 defect (a `cd`/`-C` in the inspected command was invisible to
#      it, so it reported the wrong repo). This hook tracks an explicit `-C` on
#      the matched git invocation, and a `cd <path>` earlier in the same
#      `&&`/`;` chain (dropped, not trusted, across `|`/`||` — a `cd` before a
#      pipe runs in a subshell and never takes effect on what follows; a `cd`
#      before `||` only runs if the left side failed). An explicit `-C` on the
#      commit's own invocation wins over an inherited `cd` — confirmed against
#      real git behaviour, not assumed. Falls back to `$PWD` when neither is
#      present or the resolved path is not a real directory.
# FAIL_POSTURE: degrade-safe — any error (unreadable payload, shlex failure,
#      git error mid-check) exits 0 SILENT. This is a SPEED BUMP on ordinary
#      work, not a security boundary; a hook that can throw and block a commit
#      no one can diagnose is worse than one that occasionally stays quiet.
# UPDATED: 2026-09-08
# RULE: O3 (lifehack-migration.plan.md) — O2's CLAUDE.md map line (mechanics)
# ─────────────────────────────────────────────────────────────────────────────
# guard_no_upstream_commit_signpost.sh — PreToolUse hook (matcher: Bash)

INPUT=$(cat 2>/dev/null)

VERDICT=$(printf '%s' "$INPUT" | python3 -c '
import sys, json, shlex, os

try:
    d = json.load(sys.stdin)
except Exception:
    print("NOT_OURS"); raise SystemExit

cmd = ((d.get("tool_input") or {}).get("command") or "")
if not cmd.strip():
    print("NOT_OURS"); raise SystemExit

try:
    toks = shlex.split(cmd, comments=False, posix=True)
except ValueError:
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
    if j < len(seg) and seg[j] == "commit":
        resolved = cdir if cdir else cwd
        print("DENY\t" + resolved); raise SystemExit

print("OK")
' 2>/dev/null)

case "$VERDICT" in
  ""|PARSE_ERROR)
    exit 0
    ;;
esac

CDIR="${VERDICT#*$'\t'}"
[ "$CDIR" = "$VERDICT" ] && CDIR=""
VERDICT="${VERDICT%%$'\t'*}"
REPO_DIR="$PWD"
if [ -n "$CDIR" ] && [ -d "$CDIR" ]; then REPO_DIR="$CDIR"; fi

case "$VERDICT" in
  OK|NOT_OURS)
    exit 0
    ;;
  DENY)
    BRANCH=$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null)
    [ -n "$BRANCH" ] || exit 0

    TRACKLINE=$(git -C "$REPO_DIR" for-each-ref --format='%(upstream:short)|%(upstream:track)' "refs/heads/$BRANCH" 2>/dev/null)
    [ -n "$TRACKLINE" ] || exit 0
    UPSTREAM="${TRACKLINE%%|*}"
    TRACK="${TRACKLINE#*|}"

    FIRE=0
    if [ -z "$UPSTREAM" ]; then
      FIRE=1
    else
      case "$TRACK" in
        *gone*) FIRE=1 ;;
      esac
    fi
    [ "$FIRE" -eq 1 ] || exit 0

    TOPLEVEL=$(git -C "$REPO_DIR" rev-parse --show-toplevel 2>/dev/null)
    [ -n "$TOPLEVEL" ] || exit 0

    KEY="${CLAUDE_CODE_SESSION_ID:-nosession}|$TOPLEVEL|$BRANCH"
    HASH=$(printf '%s' "$KEY" | shasum 2>/dev/null | cut -c1-12)
    [ -n "$HASH" ] || exit 0
    BUMP="$HOME/.claude/.no-upstream-commit-signpost.$HASH"

    if [ -f "$BUMP" ]; then
      exit 0
    fi
    : > "$BUMP" 2>/dev/null || true

    printf '⚠ %s has no upstream (or its upstream is gone) — a local branch mirrors the remote by default. -> CLAUDE.md map: no-upstream\n' "$BRANCH" >&2
    exit 2
    ;;
  *)
    exit 0
    ;;
esac
