#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: Lead-don't-follow specialist skills drift into FOLLOWING the user as a long
#      session buries their SOP in the low-attention middle of context ("lost in
#      the middle" / context rot — research 2026-06-17 skill-anchoring-hooks). This
#      is the on/off switch a skill ARMS to re-anchor itself every turn.
# GUARDS: None — a tiny state writer. Flag is SESSION-scoped + machine-local
#         (CLAUDE_CODE_SESSION_ID; cwd-hash fallback). arm requires a slug + an
#         existing anchor file; status self-expires stale flags; clear sweeps this
#         session's flags.
# REDIRECT: Flag ~/.claude/run/anchor/anchor-sess-<id>.flag (or -cwd-<hash>).
#           Injector: skill_anchor_inject.sh (UserPromptSubmit). Off: clear or TTL.
# UPDATED: 2026-06-17 (new — Skill Anchor; mirrors pm_flag.sh)
# ─────────────────────────────────────────────────────────────────────────────
#   skill_anchor.sh arm <skill-slug> <abs_anchor_file>   # turn anchoring ON
#   skill_anchor.sh clear                                # turn it OFF (this session)
#   skill_anchor.sh status                               # print active slug or "none"
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
TTL_HOURS="${ANCHOR_TTL_HOURS:-12}"
FLAGDIR="$HOME/.claude/run/anchor"; mkdir -p "$FLAGDIR" 2>/dev/null
if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then
  KEY="sess-$CLAUDE_CODE_SESSION_ID"
else
  KEY="cwd-$(hash_key "$PWD")"
fi
FLAG="$FLAGDIR/anchor-$KEY.flag"
NOW="$(date +%s 2>/dev/null)"
case "$1" in
  arm)
    if [ -z "$2" ] || [ -z "$3" ]; then echo "arm: <skill-slug> <abs_anchor_file> required" >&2; exit 1; fi
    if [ ! -f "$3" ]; then echo "arm: anchor file not found: $3" >&2; exit 1; fi
    { echo "skill=$2"; echo "anchor_file=$3"; echo "armed_at=$NOW"; echo "cwd=$PWD"; echo "session=$CLAUDE_CODE_SESSION_ID"; } > "$FLAG"
    echo "ANCHOR ARMED: $2 -> $3 (session ${CLAUDE_CODE_SESSION_ID:-none})";;
  clear)
    n=0
    [ -f "$FLAG" ] && { rm -f "$FLAG" 2>/dev/null; n=$((n+1)); }
    if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then
      for f in "$FLAGDIR"/anchor-*.flag; do
        [ -f "$f" ] || continue
        s="$(grep '^session=' "$f" 2>/dev/null | cut -d= -f2-)"
        [ "$s" = "$CLAUDE_CODE_SESSION_ID" ] && { rm -f "$f" 2>/dev/null; n=$((n+1)); }
      done
    fi
    echo "ANCHOR CLEARED ($n)";;
  status)
    if [ -f "$FLAG" ]; then
      SK="$(grep '^skill=' "$FLAG" 2>/dev/null | cut -d= -f2-)"
      AT="$(grep '^armed_at=' "$FLAG" 2>/dev/null | cut -d= -f2-)"
      if [ -n "$AT" ] && [ -n "$NOW" ] && [ $(( NOW - AT )) -ge $(( TTL_HOURS * 3600 )) ]; then
        rm -f "$FLAG" 2>/dev/null; echo "none"
      elif [ -z "$SK" ]; then echo "none"
      else echo "$SK"; fi
    else echo "none"; fi;;
  *) echo "usage: skill_anchor.sh arm <slug> <anchor_file> | clear | status" >&2; exit 2;;
esac
exit 0
