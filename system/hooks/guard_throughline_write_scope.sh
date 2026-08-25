#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: /throughline reads a project's whole history and says where it has drifted from what it set
#      out to do. To be worth anything it has to be strictly read-only — an investigator that can
#      edit the evidence is not an investigator. The skill says so in prose; this makes it true.
#      It fires ONLY during an armed /throughline run and is a pure no-op in every other session.
# GUARDS: matcher Write|Edit. While a run is armed for THIS session, any write outside
#      <notes>/records/insights/throughline/ is blocked. Fail-CLOSED while armed: unparseable input,
#      or a notes folder that will not resolve, both DENY rather than allow.
# REDIRECT: /throughline writes exactly one file, at
#      <notes>/records/insights/throughline/{target-slug}-{YYYY-MM-DD}.md. To write anything else,
#      finish the run first: `bash system/hooks/throughline_flag.sh clear`.
# SIGNPOST: the write contract is .claude/skills/throughline/SKILL.md -> "Write Target"; the notes
#      folder is resolved the way shared/brain_root.py resolves it, and the layout is
#      docs/data-layout.md. Change the destination in all three or in none.
# FAIL_POSTURE: CLOSED while armed, open otherwise. Un-armed sessions are never affected at all.
# UPDATED: 2026-08-23 (GitHub #95: notes_root() now also tries the repo's own .brain-root pointer
#      and, when this checkout is a linked git worktree with no pointer of its own, the MAIN
#      worktree's pointer, before falling back to the machine-global brain-root. Ported from
#      system/hooks/ingest_gate_enforce.sh's notes_root()/main_worktree_pointer_file(); this file
#      applies no Windows path fold, so there was no fold-ordering concern to resolve.)
# UPDATED: 2026-08-11 (ported; the destination stopped being one machine's absolute Drive path, the
#      comparison is now made on resolved paths, and the deny moved to the house channel)
# ─────────────────────────────────────────────────────────────────────────────
INPUT=$(cat)

# ── hash_key: the fallback session key, and it MUST match everywhere ──────────────────────────────
# Identical to throughline_flag.sh's. A guard and a switch that key differently is a guard that is
# armed for a session nobody is in.
hash_key() {
  _hk="$(printf '%s' "$1" | shasum 2>/dev/null | cut -c1-12)"
  if [ -z "$_hk" ]; then
    _hk="$(printf '%s' "$1" | python3 -c 'import hashlib,sys; sys.stdout.write(hashlib.sha1(sys.stdin.buffer.read()).hexdigest())' 2>/dev/null | cut -c1-12)"
  fi
  printf '%s' "$_hk"
}

# One parse of the payload for everything read out of it.
PARSED=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    print('__PARSE_ERROR__'); raise SystemExit
ti = d.get('tool_input', {}) or {}
print('\t'.join([
    d.get('session_id','') or '',
    d.get('cwd','') or '',
    (ti.get('file_path','') or ti.get('path','') or '').replace('\t',' '),
    (d.get('tool_name','') or '').strip(),
    (ti.get('command','') or '').replace('\t',' ').replace('\n',';'),
]))" 2>/dev/null)

deny() {
  printf 'BLOCKED (throughline write-scope): %s\n' "$1" >&2
  printf '%s\n' "WHY: /throughline is read-only by contract — it reads a project's whole history and says where it drifted, and an investigator that can edit the evidence is not one. This guard fires only inside an armed run." >&2
  printf '%s\n' "REDIRECT: the one file it may write is <notes>/records/insights/throughline/{target-slug}-{YYYY-MM-DD}.md. To write anything else, end the run first: bash system/hooks/throughline_flag.sh clear" >&2
  printf '%s\n' "RULE: .claude/skills/throughline/SKILL.md -> 'Write Target', and docs/data-layout.md for where that folder lives." >&2
  exit 2
}

# ── session key — env first, then the payload's session_id, then a cwd hash.
if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then
  KEY="sess-$CLAUDE_CODE_SESSION_ID"
elif [ "$PARSED" = "__PARSE_ERROR__" ]; then
  # Nothing readable AND no session id: we cannot tell whether a run is armed. There is no flag to
  # check, so this cannot be a false block on an armed run — and blocking every write in every
  # session on a parse failure would be far worse than the thing being guarded. Stay out of the way.
  exit 0
else
  SID="$(printf '%s' "$PARSED" | cut -f1)"
  CWD="$(printf '%s' "$PARSED" | cut -f2)"
  if [ -n "$SID" ]; then KEY="sess-$SID"; else KEY="cwd-$(hash_key "$CWD")"; fi
fi

FLAG="$HOME/.claude/run/throughline/tl-$KEY.flag"
# Not in a /throughline run -> pure no-op. Ordinary sessions are NEVER affected.
[ -f "$FLAG" ] || exit 0

# ── From here down the run IS armed, and every exit is fail-CLOSED.
[ "$PARSED" = "__PARSE_ERROR__" ] && deny "the tool input could not be read during an armed run, so there is no way to tell what this write is aiming at"

FILE_PATH="$(printf '%s' "$PARSED" | cut -f3)"
TOOL_NAME="$(printf '%s' "$PARSED" | cut -f4)"
COMMAND="$(printf '%s' "$PARSED"   | cut -f5)"

# A Bash command carries no file_path, so the emptiness test below must not swallow it.
[ -z "$FILE_PATH" ] && [ "$TOOL_NAME" != "Bash" ] && exit 0

# ── THE DESTINATION. Resolved from the person's notes folder — never a path baked into this file.
# ⛔ THE DONOR HARDCODED ONE MACHINE'S ABSOLUTE DRIVE PATH HERE, and that is not merely unportable:
# on any other machine the comparison below matches NOTHING, so an armed run would have been blocked
# from writing its own findings file. The guard would have made the skill unable to finish, and the
# only symptom would be a refusal naming a folder that does not exist.
# ── THIS REPO, resolved from this script's own location — never $PWD or $HOME. Needed only so
# main_worktree_pointer_file() below has something to test: is THIS checkout a linked worktree of
# some other, main, checkout?
_HOOKDIR_TL="$(cd "$(dirname "$0")" 2>/dev/null && pwd -P)"
REPO="${_HOOKDIR_TL%/system/hooks}"
[ "$REPO" = "$_HOOKDIR_TL" ] && REPO="$(cd "$_HOOKDIR_TL" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)"
: "${REPO:=/dev/null/no-repo-resolved}"

# See system/hooks/lib/winpath_fold.sh -- FILE_PATH (below) and every Bash-door candidate arrive
# backslash-native on Windows (tool_input.file_path), and canon()'s dirname/basename/cd all need
# forward slashes just to split the string at all, let alone resolve it. Sourced once, here, ahead
# of every fold this file does. This run is ARMED once we reach here in spirit (the FLAG check is
# further down) -- but a missing lib means every write's destination becomes unverifiable, so this
# fails CLOSED like the rest of the armed path, not silently open.
. "$_HOOKDIR_TL/lib/winpath_fold.sh" 2>/dev/null \
  || deny "the path-form normaliser (lib/winpath_fold.sh) could not be loaded, so a Windows-native write target cannot be safely checked against this run's one allowed destination"

# ── THE WORKTREE ROUTE (ported from system/hooks/ingest_gate_enforce.sh, GitHub #95). `git
# worktree add` materialises only TRACKED files, and .brain-root is deliberately gitignored -- so a
# LINKED WORKTREE never has a pointer of its own and git will never give it one. Without this, a
# session running inside a linked worktree would silently fall through to the machine-global
# ~/.config/lifehack/brain-root, which belongs to no repo in particular and can be stale -- the
# IDENTICAL blind spot #95 found in ingest_gate_enforce.sh, here in the guard that resolves the one
# folder /throughline is allowed to write into.
# A linked worktree is a second checkout of ONE repo, so the brain it belongs to is the MAIN
# worktree's brain; borrowing that pointer is the repo's own declaration, not a guess. Detection
# reads GIT'S OWN FILES -- a `.git` FILE holding `gitdir:`, then `commondir` inside that git dir --
# and never `git rev-parse`, for the same reasons as the donor: no PATH dependency, no subprocess
# on every tool call. A SUBMODULE also has a `.git` file and is excluded here (no `commondir`).
# Anything unexpected returns 1 and the next route is tried -- this function never improvises.
main_worktree_pointer_file() {
  [ -f "$REPO/.git" ] || return 1          # an ordinary clone has a .git DIRECTORY, not a file
  _mw_line="$(head -n 1 "$REPO/.git" 2>/dev/null)"
  case "$_mw_line" in gitdir:*) ;; *) return 1 ;; esac
  _mw_gd="$(printf '%s' "${_mw_line#gitdir:}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  [ -n "$_mw_gd" ] || return 1
  case "$_mw_gd" in /*) ;; *) _mw_gd="$REPO/$_mw_gd" ;; esac
  [ -f "$_mw_gd/commondir" ] || return 1   # no commondir => a submodule, not a linked worktree
  _mw_cd="$(head -n 1 "$_mw_gd/commondir" 2>/dev/null)"
  [ -n "$_mw_cd" ] || return 1
  case "$_mw_cd" in /*) ;; *) _mw_cd="$_mw_gd/$_mw_cd" ;; esac
  _mw_cdp="$(cd "$_mw_cd" 2>/dev/null && pwd -P)"
  [ -n "$_mw_cdp" ] || return 1
  # ONLY the ordinary `<main worktree>/.git` layout. A bare repo, or one made with
  # --separate-git-dir, has no main worktree at the parent of the common dir, and inventing one
  # there is exactly the guess a security boundary must not make.
  case "$_mw_cdp" in */.git) ;; *) return 1 ;; esac
  _mw_root="${_mw_cdp%/.git}"
  [ -d "$_mw_root" ] || return 1
  printf '%s' "$_mw_root/.brain-root"
}

notes_root() {
  _nr="${LIFEHACK_ROOT:-}"
  if [ -z "$_nr" ] && [ -f "$REPO/.brain-root" ]; then
    _nr="$(cat "$REPO/.brain-root" 2>/dev/null)"
  fi
  # Only when this repo has no pointer of its own -- which in practice means a linked worktree,
  # since git cannot put one there. A repo that HAS declared, however badly, keeps its declaration.
  if [ -z "$_nr" ] && [ ! -f "$REPO/.brain-root" ]; then
    _mwp="$(main_worktree_pointer_file || true)"
    if [ -n "$_mwp" ] && [ -f "$_mwp" ]; then
      _nr="$(cat "$_mwp" 2>/dev/null)"
    fi
  fi
  [ -n "$_nr" ] || _nr="$(cat "$HOME/.config/lifehack/brain-root" 2>/dev/null)"
  while [ "${_nr%/}" != "$_nr" ]; do _nr="${_nr%/}"; done
  case "$_nr" in
    ""|"/"|"$HOME") return 1 ;;
    # WINDOWS PATH FOLD: `/*` alone is POSIX-only -- a Windows absolute path (`D:\Notes\Brain` or
    # `D:/Notes/Brain`) does not start with `/`, so it fell through this case with no match and no
    # validation at all (a bare `case` has no default arm). `[A-Za-z]:*` catches both spellings.
    /*|[A-Za-z]:*) [ -d "$_nr" ] || return 1 ;;
    *) return 1 ;;
  esac
  # PHYSICAL path — symlinks resolved. See the comparison note below.
  _nrp="$(cd "$_nr" 2>/dev/null && pwd -P)"
  printf '%s' "${_nrp:-$_nr}"
}
NOTES_ROOT="$(notes_root)" || deny "your notes folder is not set, so there is nowhere this run is allowed to write. Set it with: python3 shared/brain_root.py --set \"<the folder your notes live in>\""
DEST="$NOTES_ROOT/records/insights/throughline"

# ⛔ COMPARE RESOLVED PATHS ON BOTH SIDES. The tool hands this hook the path with symlinks already
# followed and doubled slashes collapsed, while the destination above is built from a configured
# string. On macOS that difference alone is fatal — /tmp and /var ARE symlinks, so a notes folder
# under either arrives as /private/... and matches nothing. This is the same failure the egress
# wall's own gate hit on 2026-08-11, reached through string formatting rather than through symlinks;
# it is cheaper to fix it here than to find it twice.
#
# ⚠ IT WALKS UP TO THE DEEPEST ANCESTOR THAT EXISTS, rather than assuming the parent does. The
# first version resolved only `dirname`, and that is wrong on the single most important write there
# is: the FIRST one, when <notes>/records/insights/throughline/ has never been created. `cd` into a
# folder that is not there yet fails, the path falls back to its unresolved form, the unresolved
# form does not match the resolved destination — and the guard refuses the skill's own output on
# run one and every run until somebody makes the folder by hand. Caught by the suite; it would not
# have been caught by any test that only wrote into a folder the test had already made.
canon() {
  _p="$1"
  _d="$(dirname "$_p")"
  _rest="$(basename "$_p")"
  while [ ! -d "$_d" ] && [ "$_d" != "/" ] && [ "$_d" != "." ] && [ -n "$_d" ]; do
    _rest="$(basename "$_d")/$_rest"
    _d="$(dirname "$_d")"
  done
  _dp="$(cd "$_d" 2>/dev/null && pwd -P)"
  if [ -n "$_dp" ]; then printf '%s/%s' "$_dp" "$_rest"; else printf '%s' "$_p"; fi
}
# ── THE THIRD DOOR — placed HERE, below `canon()` and `DEST`, because it needs both.
# An armed run that cannot use Write or Edit can still `cat >` its way out, and that is not an evader:
# a heredoc is an ordinary way to write a file. A read-only contract with a shell door beside it is
# not read-only. The shared library answers "which paths does this command WRITE to"; the DEST test
# below is unchanged and does the judging.
# ⚠ Reads stay untouched, which is the whole point — /throughline READS a project's entire history,
# so a guard that denied reading would break the skill it exists to protect.
if [ "$TOOL_NAME" = "Bash" ]; then
  [ -z "$COMMAND" ] && exit 0
  HOOKDIR_TL="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
  # shellcheck source=lib/bash_write_door.sh
  . "$HOOKDIR_TL/lib/bash_write_door.sh" 2>/dev/null \
    || deny "lib/bash_write_door.sh could not be loaded during an armed run, so the shell door cannot be checked at all"
  _TL_HIT=""
  while IFS= read -r _c; do
    [ -n "$_c" ] || continue
    [ "$_c" = "__BWD_PARSE_ERROR__" ] && deny "this Bash command could not be analysed during an armed run, so there is no way to tell what it writes"
    case "$(canon "$_c")" in
      "$DEST"/*) : ;;                 # the one sanctioned destination — allowed
      *) _TL_HIT="$_c"; break ;;
    esac
  done <<EOF
$(bwd_write_targets "$COMMAND")
EOF
  [ -n "$_TL_HIT" ] || exit 0
  deny "this run may not write $_TL_HIT (reached through a Bash command rather than the Write tool)"
fi

FP_C="$(canon "$FILE_PATH")"

case "$FP_C" in
  "$DEST"/*) exit 0 ;;
esac
deny "this run may not write $FILE_PATH"
