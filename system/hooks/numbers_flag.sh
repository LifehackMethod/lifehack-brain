#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: the on/off switch for numbers-mode. `/calculate` ARMS it; `/calculate off` or a 12h TTL
#      CLEARS it. While it is armed, inject_compute_mechanically.sh re-states the compute-with-code
#      rule on every turn, so the rule survives compaction instead of fading with the session.
#      It is a FILE and not an environment variable for the reason pm_flag.sh is: an env var set
#      inside one tool call does not exist in the next one.
# GUARDS: nothing. This is a tiny state writer with no opinion about what you do — it records that
#         you asked for numbers-mode. Session-scoped and machine-local (CLAUDE_CODE_SESSION_ID,
#         with a working-directory hash as the fallback key). `status` self-expires a stale flag;
#         `clear` sweeps every flag belonging to this session, not just the one under this key.
# REDIRECT: n/a — it never blocks. The flag is ~/.claude/run/numbers/numbers-<key>.flag; the hook
#         that reads it is system/hooks/inject_compute_mechanically.sh.
# SIGNPOST: the RULE this arms — that a number a decision rests on is computed by code and never in
#         the model's head — is stated in the `/calculate` skill and re-stated by the injector. To
#         change what gets injected, edit inject_compute_mechanically.sh; to change when it arms,
#         edit this file.
# FAIL_POSTURE: degrade-safe — a recorder, never a gate. Any error exits 0 and the session behaves
#         exactly as if numbers-mode had never been armed.
# UPDATED: 2026-08-11 (ported; the shasum shim added, per the Git Bash floor)
# ─────────────────────────────────────────────────────────────────────────────
#   numbers_flag.sh arm     # arm numbers-mode for this session
#   numbers_flag.sh clear   # disarm (remove this session's flag(s))
#   numbers_flag.sh status  # print "armed" or "none"
# ── hash_key: the fallback session key, and it MUST match everywhere ──────────────────────────────
# When the harness gives us no session id we key on the working directory instead. `shasum` does that
# on macOS and Linux and is ABSENT from Git Bash on Windows, where it produces an EMPTY key — so every
# window on that machine would collide on one flag, silently.
# ⚠ SHA-1 DELIBERATELY, NOT SHA-256: this must equal what `shasum` prints, or a machine that has
# shasum and a machine that does not would key the SAME folder differently. One writer and one reader
# disagreeing about the key is worse than having no key at all.
# ⚠ This snippet is IDENTICAL in every file that needs it (plan_flag, pm_flag, pm_persist, skill_anchor,
# skill_anchor_inject, statusline). Keep it that way — the next platform fix should land in one shape.
# ⚠ DEFINE IT AT THE TOP, never beside its first use: these files branch on whether the harness gave
# us a session id, and a definition placed inside that branch is not defined on the other one.
# TEMPORARY: Git Bash is the documented Windows floor; a real Windows story is still owed.
hash_key() {
  _hk="$(printf '%s' "$1" | shasum 2>/dev/null | cut -c1-12)"
  if [ -z "$_hk" ]; then
    _hk="$(printf '%s' "$1" | python3 -c 'import hashlib,sys; sys.stdout.write(hashlib.sha1(sys.stdin.buffer.read()).hexdigest())' 2>/dev/null | cut -c1-12)"
  fi
  printf '%s' "$_hk"
}

set +e
TTL_HOURS="${NUMBERS_TTL_HOURS:-12}"
FLAGDIR="$HOME/.claude/run/numbers"; mkdir -p "$FLAGDIR" 2>/dev/null
if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then KEY="sess-$CLAUDE_CODE_SESSION_ID"
else KEY="cwd-$(hash_key "$PWD")"; fi
FLAG="$FLAGDIR/numbers-$KEY.flag"
NOW="$(date +%s 2>/dev/null)"
case "$1" in
  arm)
    { echo "armed_at=$NOW"; echo "cwd=$PWD"; echo "session=$CLAUDE_CODE_SESSION_ID"; } > "$FLAG"
    echo "ARMED: numbers-mode (session ${CLAUDE_CODE_SESSION_ID:-none}, cwd $PWD)";;
  clear)
    n=0; [ -f "$FLAG" ] && { rm -f "$FLAG" 2>/dev/null; n=$((n+1)); }
    if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then
      for f in "$FLAGDIR"/numbers-*.flag; do
        [ -f "$f" ] || continue
        s="$(grep '^session=' "$f" 2>/dev/null | cut -d= -f2-)"
        [ "$s" = "$CLAUDE_CODE_SESSION_ID" ] && { rm -f "$f" 2>/dev/null; n=$((n+1)); }
      done
    fi
    echo "CLEARED ($n)";;
  status)
    if [ -f "$FLAG" ]; then
      AT="$(grep '^armed_at=' "$FLAG" 2>/dev/null | cut -d= -f2-)"
      if [ -n "$AT" ] && [ -n "$NOW" ] && [ $(( NOW - AT )) -ge $(( TTL_HOURS * 3600 )) ]; then
        rm -f "$FLAG" 2>/dev/null; echo "none"
      else echo "armed"; fi
    else echo "none"; fi;;
  *) echo "usage: numbers_flag.sh arm | clear | status" >&2; exit 2;;
esac
exit 0
