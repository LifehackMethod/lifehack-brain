#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: the /throughline skill must be strictly read-only — it writes ONE findings file and nothing
#      else. This is the session-scoped on/off switch that guard_throughline_write_scope.sh reads.
#      /throughline ARMS it at the start of a run and CLEARS it at the end. It is a FILE and not an
#      environment variable because an env var set inside one tool call does not exist in the next.
# GUARDS: nothing — a tiny state writer. The flag is session-scoped and machine-local (keyed by
#      CLAUDE_CODE_SESSION_ID, with a working-directory hash as the fallback). `status` self-expires
#      after 30 minutes, so a run that dies before its `clear` does not leave the session walled in.
# REDIRECT: n/a — it never blocks. Flag ~/.claude/run/throughline/tl-<key>.flag. The hook that reads
#      it is system/hooks/guard_throughline_write_scope.sh.
# SIGNPOST: what /throughline may write, and where, is stated in .claude/skills/throughline/SKILL.md
#      under "Write Target". Change it there and in the guard together — a switch and a guard that
#      disagree about the destination is the worst of both.
# FAIL_POSTURE: degrade-safe — never a gate. Any error exits 0 and the guard simply stays off.
# UPDATED: 2026-08-11 (ported; the shasum shim added, and the flag dir renamed from `eval` to
#      `throughline` — the old name matched no skill and was unreadable in a directory listing)
# ─────────────────────────────────────────────────────────────────────────────
#   throughline_flag.sh arm     # start of a /throughline run
#   throughline_flag.sh clear   # end of a /throughline run
#   throughline_flag.sh status  # armed | none
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
TTL_MIN="${THROUGHLINE_TTL_MIN:-30}"
FLAGDIR="$HOME/.claude/run/throughline"; mkdir -p "$FLAGDIR" 2>/dev/null
if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then KEY="sess-$CLAUDE_CODE_SESSION_ID"
else KEY="cwd-$(hash_key "$PWD")"; fi
FLAG="$FLAGDIR/tl-$KEY.flag"
NOW="$(date +%s 2>/dev/null)"
case "$1" in
  arm)   { echo "armed_at=$NOW"; echo "session=$CLAUDE_CODE_SESSION_ID"; } > "$FLAG"
         echo "THROUGHLINE-ARMED (session ${CLAUDE_CODE_SESSION_ID:-none}) — writes are now scoped to the findings folder";;
  clear) rm -f "$FLAG" 2>/dev/null
         if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then
           for f in "$FLAGDIR"/tl-*.flag; do [ -f "$f" ] || continue
             s="$(grep '^session=' "$f" 2>/dev/null | cut -d= -f2-)"
             [ "$s" = "$CLAUDE_CODE_SESSION_ID" ] && rm -f "$f" 2>/dev/null; done; fi
         echo "THROUGHLINE-CLEARED";;
  status) if [ -f "$FLAG" ]; then AT="$(grep '^armed_at=' "$FLAG" 2>/dev/null | cut -d= -f2-)"
            if [ -n "$AT" ] && [ -n "$NOW" ] && [ $(( NOW - AT )) -ge $(( TTL_MIN * 60 )) ]; then rm -f "$FLAG"; echo "none"; else echo "armed"; fi
          else echo "none"; fi;;
  *) echo "usage: throughline_flag.sh arm|clear|status" >&2; exit 2;;
esac
exit 0
