#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: the guards in this folder are the only things standing between an agent and your calendar,
#      your goals list, your spreadsheets and the network. Every one of them is a plain text file
#      sitting in a repo the agent can edit. Nothing stopped it doing so: measured 2026-08-14, an
#      Edit aimed at `system/hooks/guard_calendar_writes.sh` was waved through by all five of this
#      repo's Write/Edit-matched hooks, rc 0 across the board. Worse, `guard_statusline_lock.sh`
#      stated in its own header — twice, lines 6 and 18 — that this exact case was "already
#      backstopped at the Write/Edit layer" by a file that had never been ported here. A guard that
#      can quietly delete its own siblings is not an enforcement layer, it is a suggestion, and a
#      false claim of protection is worse than an admitted gap.
# GUARDS: Write/Edit aimed at (a) any script under `system/hooks/`, (b) `.claude/settings.json` or
#      `.claude/settings.local.json` — the file that decides which hooks run at all, so editing it
#      disables guards without touching one, and (c) `.git/` internals. Paths are resolved to their
#      real location first, so `a/../b` and a symlink cannot walk around the comparison.
#      (b) covers BOTH the repo-local settings AND the GLOBAL ~/.claude/settings.json /
#      ~/.claude/settings.local.json — a project-clone install (every student's install shape)
#      routes hook registration through the GLOBAL file, not the repo-local copy, so guarding only
#      the repo-local one leaves the file that actually matters unprotected.
# REDIRECT: hooks and settings are edited through Bash, deliberately and visibly — `chmod 644` the
#      file, edit it, `chmod 755` it back (755, not 444: a hook in this repo must stay executable,
#      and stripping that bit is how three guards were silently disarmed on 2026-08-14). This hook
#      matches Write|Edit only, so that path stays open.
# SIGNPOST: system/hook-contract.md — the mechanics and the permission model. Change what is
#      protected THERE, with sign-off, and then update this guard; never widen this file to fit a
#      command you happen to be running.
# FAIL_POSTURE: closed — an unparseable payload denies. This hook sees only Write/Edit, never every
#      Bash command, so denying on a malformed message costs one retry and cannot wall off the shell.
# UPDATED: 2026-08-14 (ported from the donor system, deliberately NOT wholesale — see the scope
#      note below, which is the most important thing on this page)
# ─────────────────────────────────────────────────────────────────────────────
# PreToolUse hook (matcher: Write|Edit).
#
# ⛔⛔ SCOPE — THIS IS A DELIBERATE SUBSET OF THE GUARD IT CAME FROM. READ BEFORE EXTENDING.
# The donor's version of this file is a general write-CONTAINMENT wall: it denies every write that
# does not land in one of four approved zones, and its last line refuses everything else outright.
# That behaviour is NOT ported here, and its absence is a decision, not an oversight.
#
# On the machine it came from, those zones are a synced Drive spine and a code clone, and the wall
# keeps the two from contaminating each other. On YOUR machine there is no such split — there is
# this repo and there is wherever you keep your notes — so the same wall would mean an agent could
# not write a file to your Desktop, a scratch folder, or anywhere else you asked it to. Whether a
# student's install should refuse that is a product decision about how this system feels to use,
# and it belongs to the person who owns the product, not to the session that noticed the gap.
#
# So this file ports only the half that needs no such decision: the guards protecting themselves.
# Nobody legitimately edits a hook with the Edit tool — the documented path has always been Bash —
# so this costs nothing and closes a hole that was live and publicly claimed to be closed.
#
# ⇒ IF YOU ARE HERE TO ADD GENERAL WRITE CONTAINMENT, that is the decision above. Get it made
#   first. Do not grow this file into the wall by accident, one path at a time.

_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd -P)"
# PRECEDENCE INVERTED 2026-08-23 -- $0-RELATIVE FIRST, CLAUDE_PROJECT_DIR ONLY AS FALLBACK.
# MEASURED, not theorised: CLAUDE_PROJECT_DIR is the SESSION'S LAUNCH CWD, not the repo that
# declares this hook. With the old precedence this guard returned exit 0 -- FAILING OPEN -- for
# any session launched outside this repo, i.e. a wrong CLAUDE_PROJECT_DIR switched OFF the guard
# whose whole job is stopping an agent editing the guards. Same payload, only the env differing:
#     CLAUDE_PROJECT_DIR=<this repo> -> exit 2 (blocked)
#     CLAUDE_PROJECT_DIR=/tmp        -> exit 0 (DISARMED)   <-- the bug
#     CLAUDE_PROJECT_DIR unset       -> exit 2 (blocked)    <-- the fallback was always right
# $0 is where the SCRIPT lives, which is the only thing that actually identifies its repo.
_SELF_REPO="${_HOOKDIR%/system/hooks}"
[ -n "$_SELF_REPO" ] && [ -d "$_SELF_REPO/system/hooks" ] || _SELF_REPO="${CLAUDE_PROJECT_DIR:-}"
REPO="$_SELF_REPO"
# See system/hooks/lib/winpath_fold.sh: on Windows, `pwd -P` and Python's os.path.realpath spell
# the same directory two different ways, so REPO_REAL and FILE_PATH below (built through one or
# the other) would never compare equal without this. Sourced here (not deny()'d yet -- deny() is
# defined below this point) so a missing lib is caught the first time it is actually needed.

deny() {
  printf 'BLOCKED (write-paths guard): %s\n' "$1" >&2
  printf '%s\n' "WHY: this file is part of the enforcement layer. If an agent can edit a guard, or edit the settings file that decides which guards run, then every other protection in this repo holds only for as long as nothing chooses to remove it. Measured 2026-08-14: before this hook existed, an Edit aimed at a guard was allowed by every hook here." >&2
  printf '%s\n' "$2" >&2
  printf '%s\n' "RULE: system/hook-contract.md (mechanics + the permission model). Change what is protected there, with sign-off, then update this guard. Do not widen this file to fit the command you are running." >&2
  exit 2
}

INPUT=$(cat 2>/dev/null)

# ⚠ EXPORTED BEFORE the reader runs, not after. The first draft set this on the line BELOW the
# python that reads it, so a relative path resolved against the session's cwd instead of the repo —
# and a relative path is exactly the spelling this block exists to catch. It only failed for
# relative inputs, which is the kind of bug a suite full of absolute paths never sees.
export _GUARD_REPO="$REPO"

# Resolve the target to its REAL path before comparing. A relative path, a `..` segment or a
# symlink would otherwise each be a way to name a protected file that the string test does not
# recognise — the same "the matcher is one spelling behind" failure the Bash guards are built around.
FILE_PATH=$(printf '%s' "$INPUT" | python3 -c "
import sys, json, os
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {}) or {}
    p = ti.get('file_path') or ti.get('path') or ''
    if not p:
        print('')                      # a Write/Edit with no path is not ours to judge
    else:
        base = os.environ.get('_GUARD_REPO') or os.getcwd()
        if not os.path.isabs(p):
            p = os.path.join(base, p)
        print(os.path.realpath(p))
except Exception:
    print('__PARSE_ERROR__')
" 2>/dev/null)

if [ "$FILE_PATH" = "__PARSE_ERROR__" ]; then
  deny "this write could not be read, so there is no way to tell what it targets." \
"REDIRECT: retry the write. If it keeps failing the payload is malformed, and an unreadable write to an unknown path is exactly the case this guard refuses to guess about."
fi
[ -n "$FILE_PATH" ] || exit 0

# Resolve the repo too, so the two sides of every comparison are in the same form.
REPO_REAL=$(python3 -c "
import os,sys
try: print(os.path.realpath(sys.argv[1]))
except Exception: print('')" "$REPO" 2>/dev/null)
[ -n "$REPO_REAL" ] || exit 0     # cannot locate the repo; this guard has nothing to say
. "$_HOOKDIR/lib/winpath_fold.sh" 2>/dev/null || \
  deny "the path-form normaliser (lib/winpath_fold.sh) could not be loaded, so REPO_REAL and FILE_PATH cannot be safely compared." \
"REDIRECT: confirm system/hooks/lib/winpath_fold.sh exists and is readable, then retry."
REPO_REAL="$(_winfold "$REPO_REAL")"
FILE_PATH="$(_winfold "$FILE_PATH")"

# Resolve $HOME the same way, so a symlinked home directory (or a differently-spelled mount)
# cannot walk around the global-settings match below the way an unresolved string would. Unlike
# REPO_REAL, a failure to resolve HOME does not disable the guard -- it falls back to the raw
# $HOME env var, which is what this comparison used before this block existed.
HOME_REAL=$(python3 -c "
import os,sys
try: print(os.path.realpath(sys.argv[1]))
except Exception: print('')" "$HOME" 2>/dev/null)
[ -n "$HOME_REAL" ] || HOME_REAL="$HOME"
HOME_REAL="$(_winfold "$HOME_REAL")"

case "$FILE_PATH" in
  # Tests are NOT enforcement. A guard's test suite proves the guard works; it does not do the
  # work, and weakening one cannot disable a control — the guard beside it still refuses. Blocking
  # these would mean nobody can add a guard test with the ordinary tools, which is friction bought
  # for no protection. Deliberately listed FIRST so it wins over the hooks pattern below.
  "$REPO_REAL"/system/hooks/tests/*)
    exit 0
    ;;
  "$REPO_REAL"/system/hooks/*)
    deny "a Write or Edit aimed at a hook script: ${FILE_PATH#$REPO_REAL/}" \
"REDIRECT: edit hooks through Bash, so the change is deliberate and visible:
    chmod 644 ${FILE_PATH#$REPO_REAL/}
    ...make the edit...
    chmod 755 ${FILE_PATH#$REPO_REAL/}
⚠ 755, not 444 — a hook here must stay executable. Stripping that bit is how three guards went
silently dark on 2026-08-14; they were present, registered, and could not run."
    ;;
  "$REPO_REAL"/.claude/settings.json|"$REPO_REAL"/.claude/settings.local.json|"$HOME_REAL"/.claude/settings.json|"$HOME_REAL"/.claude/settings.local.json)
    deny "a Write or Edit aimed at ${FILE_PATH#$REPO_REAL/}" \
"REDIRECT: this file decides which hooks run at all, so editing it can disable every guard here without touching one of them. Change it through Bash if you mean to, and re-read it afterwards to confirm it still parses — a settings file that no longer parses takes the whole hook set down with it. NOTE: for a project-clone install, hook registrations route through the GLOBAL ~/.claude/settings.json, not only the repo-local copy — both are protected here."
    ;;
  "$REPO_REAL"/.git/*)
    deny "a Write or Edit aimed at git's own internal files." \
"REDIRECT: use git through Bash — git add, git commit, git checkout. A hand edit under .git corrupts history, and for this repo that breaks the only path a student has to receive an update."
    ;;
esac

# Everything else is allowed. That is deliberate — see the SCOPE note at the top of this file.
exit 0
