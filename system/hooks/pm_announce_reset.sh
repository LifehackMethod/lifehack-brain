#!/usr/bin/env bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }  # allow-silence: fire-journal is observe-only and must never alter this hook
trap 'lhb_journal_fire "$?" "pm_announce_reset.sh" "SessionStart" "compact|clear" 2>/dev/null || true' EXIT
# -- LLM CONTEXT ------------------------------------------------------------------------------
# WHY: the "[project-manager ACTIVE]" line is now printed ONCE per arming instead of on every message
#      (sop-cleanup Phase 2 ruling 4.1). A compaction or /clear wipes it from the model's context, so
#      this SessionStart hook (matcher "compact|clear") deletes the "already announced" stamp; the
#      next message's project-manager UserPromptSubmit hook then prints the line again.
# GUARDS: prints nothing, deletes one stamp file, always exit 0. It cannot block anything.
# REDIRECT: N/A (non-blocking). The stamp is ~/.claude/run/pm/announced-<key>, written by the
#      project-manager UserPromptSubmit hook.
# SIGNPOST: the rule is in that hook, search "ONCE PER ARMING". Key derivation MUST match pm_flag.sh
#      and that hook (session id from the environment, else a hash of the cwd).
# FAIL_POSTURE: degrade-safe. Any error -> exit 0; the worst case is the line is not repeated until
#      the next arming.
# UPDATED: 2026-10-30 (new, sop-cleanup Phase 2).
# ---------------------------------------------------------------------------------------------
set +e
INPUT="$(cat 2>/dev/null)"

hash_key() {
  _hk="$(printf '%s' "$1" | shasum 2>/dev/null | cut -c1-12)"
  if [ -z "$_hk" ]; then
    _hk="$(printf '%s' "$1" | python3 -c 'import hashlib,sys; sys.stdout.write(hashlib.sha1(sys.stdin.buffer.read()).hexdigest())' 2>/dev/null | cut -c1-12)"
  fi
  printf '%s' "$_hk"
}

CWD="$PWD"
if [ -z "$CWD" ] || [ "$CWD" = "/" ]; then
  CWD="$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("cwd",""))
except: print("")' 2>/dev/null)"
fi
if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then KEY="sess-$CLAUDE_CODE_SESSION_ID"
elif [ -n "$CWD" ]; then KEY="cwd-$(hash_key "$CWD")"
else KEY=""; fi

ANN="$HOME/.claude/run/pm/announced-$KEY"
[ -n "$KEY" ] && rm -f "$ANN" 2>/dev/null
exit 0
