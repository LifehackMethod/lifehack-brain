#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: a session once re-pointed its own window from one project to another and then — with the
#      wrong project active — rewrote that brief's hand-authored frame block, the section a person
#      had written the day before precisely so a session could not lose the plot. The re-pointing is
#      now refused outright by `pm_flag.sh`. This covers the other half, which had no alarm at all:
#      writing to a brief that is NOT the one this window is working on.
#      THE RULING THIS IS BUILT ON, and it is the whole design: "I don't mind being able to write
#      into a different brief or plan. What I want is for it not to be changed without me looking or
#      noticing." So this is an ALARM, not a wall — it stops ONCE per file per window, names both
#      projects, and then gets out of the way. Ambient signalling was already proven insufficient:
#      the status bar showed the correct project for an hour and the change was still missed. A
#      PreToolUse stop renders as a block in the transcript, which cannot be skimmed past.
# GUARDS: Write/Edit/NotebookEdit whose target is a PROJECT ARTIFACT belonging to a DIFFERENT project
#      than this window's. Left alone: the active project's own files, every non-project file, and
#      ALL writes when no project is active (there is no contradiction to raise). A file already
#      acknowledged in this window passes silently — one stop, never nagging.
# REDIRECT: if the write is intended, acknowledge it and re-run:
#        bash <repo>/system/hooks/guard_cross_project_write.sh ack "<absolute path>"
#      Acknowledging does not change which project the window is on. That is fixed for the life of
#      the window; it needs a new window and `/checkin <project>`.
# SIGNPOST: the arming rule lives in `system/hooks/pm_flag.sh`'s header; this guard's matrix is
#      `system/hooks/tests/test_write_custody_guards.sh`.
# FAIL_POSTURE: closed — unparseable input denies.
# SCOPE, STATED HONESTLY: this watches Write, Edit AND Bash — all three doors into a file.
# ⚖ CORRECTED 2026-08-13. This comment previously read: *"A determined session could still write one
#      through the shell. That is deliberate and NOT a gap to close with a bigger pattern."* That was
#      wrong, and it is corrected here rather than left for the next reader to re-litigate.
#      ⛔ WHY IT WAS WRONG: it assumed the shell door is only reachable by a session that is EVADING.
#      It is not. An ORDINARY, OBEDIENT session writes through the shell constantly — a heredoc, a
#      `cat >`, a `python3 - <<PY` block are all normal, unremarkable ways to edit a file, and every
#      one of them walked straight past this guard. So the gap was not an evasion hole; it was a hole
#      in the common path, which is exactly the case this guard exists for.
#      ⭐ THE REFRAME THAT SETTLED IT (owner, 2026-08-13): a hook is not a suggestion, it is the one
#      hard thing. There are THREE DOORS into a file — Write, Edit and Bash. Standing at two of them
#      is not a soft wall; it is a solid wall with a door beside it.
#      ⚠ WHAT IS STILL TRUE FROM THE OLD COMMENT, kept because it matters: a session actively evading
#      is a different problem with a different answer (an OS-level boundary), and this does not solve
#      it. The Bash matcher reads TEXT — it does not resolve `$VARS`, follow a `cd`, or expand a glob.
#      See `lib/bash_write_door.sh`'s own stated loss. The goal remains NOTICING, not preventing.
# UPDATED: 2026-08-13 (Bash door closed via lib/bash_write_door.sh; scope comment corrected)
#
# ⚠ ONE THING THE DONOR GUARDED THAT THIS DOES NOT, named rather than quietly dropped: plan files.
#   There, a plan lived at `<slug>.plan.md` and its filename WAS the project slug, so a cross-project
#   plan write was detectable. Here plans live in your own notes folder under names you choose
#   (`<notes>/plans/<name>.md`), and a plan's name has no relationship to a project slug — so there
#   is nothing to compare and any check would be a guess. The `<slug>.plan.md` shape is still
#   recognised if you happen to use it. The active plan is exempt either way, resolved live from
#   plan_flag.sh.
# ─────────────────────────────────────────────────────────────────────────────
# guard_cross_project_write.sh — PreToolUse hook (matcher: Write|Edit)
#   ack <abs_path>   # acknowledge ONE file for this window, then re-run the write

# ── hash_key: the fallback window key, and it MUST match everywhere ───────────────────────────────
# `shasum` exists on macOS and Linux and is ABSENT from Git Bash on Windows, where it returns an
# EMPTY key — so every window on that machine would collide on one acknowledgement. SHA-1
# deliberately, not SHA-256, so a machine with shasum and a machine without key the same folder
# identically. This snippet is IDENTICAL in every file that needs it; keep it that way, so the next
# platform fix lands in one shape. TEMPORARY: Git Bash is the documented Windows floor.
hash_key() {
  _hk="$(printf '%s' "$1" | shasum 2>/dev/null | cut -c1-16)"
  if [ -z "$_hk" ]; then
    _hk="$(printf '%s' "$1" | python3 -c 'import hashlib,sys; sys.stdout.write(hashlib.sha1(sys.stdin.buffer.read()).hexdigest())' 2>/dev/null | cut -c1-16)"
  fi
  printf '%s' "$_hk"
}

ACKDIR="$HOME/.claude/run/pm-ack"; mkdir -p "$ACKDIR" 2>/dev/null
if [ -n "${CLAUDE_CODE_SESSION_ID:-}" ]; then KEY="sess-$CLAUDE_CODE_SESSION_ID"
else KEY="cwd-$(hash_key "$PWD" | cut -c1-12)"; fi
_ackfile(){ printf '%s/%s.%s.ok' "$ACKDIR" "$KEY" "$(hash_key "$1")"; }

# Resolve siblings by THIS FILE's own location, never $HOME — so a test can point a temp HOME at a
# temp store and still exercise the real scripts. A guard that cannot be tested against a fake store
# is one that gets tested against the real one, or not at all.
HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="${HOOKDIR%/system/hooks}"
# See system/hooks/lib/winpath_fold.sh -- sourced once here, ahead of _slug_of below, which folds
# a comparison copy of every path it classifies (tool_input.file_path and Bash-door candidates both
# arrive backslash-native on Windows). Degrade-safe on purpose: if the lib fails to load, _slug_of's
# own fallback just leaves Windows at its pre-fold behaviour -- a missed detection, not a false
# block -- which matches this guard's own stated posture (an ALARM, not a wall).
. "$HOOKDIR/lib/winpath_fold.sh" 2>/dev/null

if [ "${1:-}" = "ack" ]; then
  [ -n "${2:-}" ] || { echo "ack: an absolute file path is required" >&2; exit 1; }
  : > "$(_ackfile "$2")"
  printf '%s\t%s\t%s\n' "$(date +%s)" "$KEY" "$2" >> "$ACKDIR/ack-events.log" 2>/dev/null
  echo "ACKNOWLEDGED for this window: $2"
  echo "Re-run the write; it will go through. Which project this window is on is UNCHANGED."
  exit 0
fi

INPUT=$(cat)
PARSED=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
ti = d.get('tool_input') or {}
print((d.get('tool_name') or '').strip())
print((ti.get('file_path') or '').strip())
print((ti.get('command') or '').replace('\n', ';'))   # a newline IS a separator, never a space
") || { printf '%s\n' '{"decision":"block","reason":"BLOCKED: guard_cross_project_write could not read the hook input, so it is failing closed. Retry the write; if it keeps failing, the guard itself is broken."}' >&2; exit 2; }

TOOL=$(printf '%s' "$PARSED" | sed -n '1p')
FP=$(printf '%s' "$PARSED"   | sed -n '2p')
COMMAND=$(printf '%s' "$PARSED" | sed -n '3p')

# Which project does a path belong to? Prints the slug, or nothing if it is not a project artifact.
# THE SHAPES ARE THIS REPO'S, taken from shared/registry.py (Project.brief / Project.canon):
#   a folder project  -> <notes>/state/projects/[<category>/]<slug>/brief.md
#                        <notes>/state/projects/[<category>/]<slug>/canon/current.md
#   a flat project    -> <notes>/state/briefs/<slug>.md
# The folder's last segment IS the slug — that rule is enforced elsewhere and relied on here.
_slug_of(){
  # FOLD FOR DETECTION ONLY (Windows path fold). $1 arrives backslash-native on Windows (either
  # tool_input.file_path directly, or a Bash-door candidate resolved the same way), so the
  # forward-slash shape patterns below would otherwise never match there. The slug TEXT is always
  # sliced from the ORIGINAL $1, below, using a pattern that accepts either separator -- never from
  # the folded copy, which _winfold lowercases, and this slug is shown back to the person verbatim
  # in the cross-project deny message.
  _s1c="$(_winfold "$1" 2>/dev/null)"; [ -n "$_s1c" ] || _s1c="$1"
  case "$_s1c" in
    */projects/*/canon/current.md|*/projects/*/canon/*.md)
      p="${1%[/\\]canon[/\\]*}"; printf '%s' "${p##*[/\\]}" ;;
    */projects/*/brief.md|*/projects/*/canon.md)
      p="${1%[/\\]*}"; printf '%s' "${p##*[/\\]}" ;;
    */state/briefs/*.md)
      b="${1##*[/\\]}"; printf '%s' "${b%.md}" ;;
    */plans/*.plan.md)
      b="${1##*[/\\]}"; printf '%s' "${b%%.plan*}" ;;
    *) : ;;
  esac
}
# ── THE THREE DOORS ───────────────────────────────────────────────────────────────────────────────
# Write/Edit hand us the path directly. Bash hands us a command, so we ask the shared library which
# paths that command WRITES TO (never merely mentions), then run the same test on each. The library
# owns "is this a write"; this guard owns "is this path a project artifact" — that is `_slug_of`,
# directly above, and it is what filters the library's noise tokens down to real briefs.
case "$TOOL" in
  Write|Edit|NotebookEdit)
    [ -n "$FP" ] || exit 0 ;;
  Bash)
    [ -n "$COMMAND" ] || exit 0
    # shellcheck source=lib/bash_write_door.sh
    . "$HOOKDIR/lib/bash_write_door.sh" 2>/dev/null || {
      printf '%s\n' '{"decision":"block","reason":"BLOCKED: guard_cross_project_write could not load lib/bash_write_door.sh, so it is failing closed. The Bash door into another project'"'"'s brief is unguarded without it. REDIRECT: restore system/hooks/lib/bash_write_door.sh from git."}' >&2; exit 2; }
    _HIT=""
    while IFS= read -r _cand; do
      [ -n "$_cand" ] || continue
      if [ "$_cand" = "__BWD_PARSE_ERROR__" ]; then
        printf '%s\n' '{"decision":"block","reason":"BLOCKED: guard_cross_project_write could not analyse this Bash command, so it is failing closed. An unreadable command and a harmless one must never look the same. REDIRECT: use the Write or Edit tool, which this guard can read reliably."}' >&2; exit 2
      fi
      # only a path that is a PROJECT ARTIFACT is this guard's business; everything else is noise
      [ -n "$(_slug_of "$_cand")" ] && { _HIT="$_cand"; break; }
    done <<EOF
$(bwd_write_targets "$COMMAND")
EOF
    [ -n "$_HIT" ] || exit 0
    FP="$_HIT" ;;
  *) exit 0 ;;
esac

TARGET_SLUG="$(_slug_of "$FP")"
[ -n "$TARGET_SLUG" ] || exit 0            # not a brief or a project canon — not this guard's business

PMF="$HOOKDIR/pm_flag.sh"
ACTIVE_DOC="$(bash "$PMF" status 2>/dev/null)"
# Empty is treated exactly like "none": if we cannot read what is active we have nothing to
# contradict, and inventing a contradiction would block ordinary work.
[ -z "$ACTIVE_DOC" ] || [ "$ACTIVE_DOC" = "none" ] && exit 0
ACTIVE_SLUG="$(bash "$PMF" locked 2>/dev/null)"
[ "$ACTIVE_SLUG" = "none" ] && ACTIVE_SLUG="$(_slug_of "$ACTIVE_DOC")"
[ -n "$ACTIVE_SLUG" ] || exit 0

[ "$FP" = "$ACTIVE_DOC" ] && exit 0
ACTIVE_PLAN="$(bash "$HOOKDIR/plan_flag.sh" path 2>/dev/null)"
[ -n "$ACTIVE_PLAN" ] && [ "$ACTIVE_PLAN" != "none" ] && [ "$FP" = "$ACTIVE_PLAN" ] && exit 0
[ "$TARGET_SLUG" = "$ACTIVE_SLUG" ] && exit 0
[ -f "$(_ackfile "$FP")" ] && exit 0       # already acknowledged in this window — one stop, not nagging

python3 - "$ACTIVE_SLUG" "$ACTIVE_DOC" "$TARGET_SLUG" "$FP" "$REPO" <<'PY' >&2
import json, sys
active_slug, active_doc, target_slug, fp, repo = sys.argv[1:6]
print(json.dumps({"decision": "block", "reason":
  "STOPPED ONCE SO YOU SEE IT — this writes to a DIFFERENT PROJECT than the one this window is on. "
  f"THIS WINDOW: {active_slug} ({active_doc}). WRITING TO: {target_slug} ({fp}). "
  "WHY THIS EXISTS: a session once re-pointed its own window to the wrong project and then rewrote "
  "that brief's hand-authored frame block. The re-pointing is refused outright now; this is the other "
  "half — a cross-project write used to happen with no signal at all, and a status bar showing the "
  "right answer for an hour was not enough to catch it. "
  "THIS IS NOT A BAN. Writing into another project's brief is allowed. It just may not happen quietly. "
  "WHAT TO DO: (1) if this was not asked for, do not do it — say what you were about to change and "
  "why, and let the person decide; (2) if it IS intended, run: "
  f"bash {repo}/system/hooks/guard_cross_project_write.sh ack \"{fp}\"  "
  "then re-run the write — it goes through, and this window will not ask about that file again. "
  "NOTE: acknowledging does NOT change which project this window is on. That is fixed for the life of "
  f"the window; it needs a new window and /checkin {target_slug}. "
  "EXTRA CARE if what you are touching is a FRAME, a DESIRED OUTCOME, or an ALTITUDES block: those are "
  "human-authored and human-only in EVERY brief, including one you are allowed to write to."}))
PY
exit 2
