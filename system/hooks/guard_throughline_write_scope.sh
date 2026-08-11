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
[ -z "$FILE_PATH" ] && exit 0        # a Write|Edit with no path is not a write we can judge

# ── THE DESTINATION. Resolved from the person's notes folder — never a path baked into this file.
# ⛔ THE DONOR HARDCODED ONE MACHINE'S ABSOLUTE DRIVE PATH HERE, and that is not merely unportable:
# on any other machine the comparison below matches NOTHING, so an armed run would have been blocked
# from writing its own findings file. The guard would have made the skill unable to finish, and the
# only symptom would be a refusal naming a folder that does not exist.
notes_root() {
  _nr="${LIFEHACK_ROOT:-}"
  [ -n "$_nr" ] || _nr="$(cat "$HOME/.config/lifehack/brain-root" 2>/dev/null)"
  while [ "${_nr%/}" != "$_nr" ]; do _nr="${_nr%/}"; done
  case "$_nr" in
    ""|"/"|"$HOME") return 1 ;;
    /*) [ -d "$_nr" ] || return 1 ;;
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
FP_C="$(canon "$FILE_PATH")"

case "$FP_C" in
  "$DEST"/*) exit 0 ;;
esac
deny "this run may not write $FILE_PATH"
