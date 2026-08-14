#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: A SKILL.md body is injected once at invocation, then sinks into the
#      low-attention middle as the session grows (context rot / lost-in-the-middle,
#      research 2026-06-17) — so a lead-don't-follow specialist drifts into FOLLOWING
#      the user. This UserPromptSubmit hook re-injects the skill's LEAN anchor every
#      turn so its framing stays fresh at the generation boundary.
# GUARDS: Read-only observer. NEVER blocks a prompt (degrade-safe -> exit 0). Flag is
#         SESSION-scoped (matches skill_anchor.sh). A session with no armed anchor is a
#         pure NO-OP. Anchor body truncated to a char ceiling so it can't flood every
#         turn; control/zero-width/bidi stripped (newlines/tabs preserved).
# REDIRECT: N/A (non-blocking). Arm/off: skill_anchor.sh arm|clear. TTL ANCHOR_TTL_HOURS (12h).
# UPDATED: 2026-06-17 (new — Skill Anchor injector; mirrors pm_persist.sh)
# ─────────────────────────────────────────────────────────────────────────────
# DEGRADE-SAFE: any error -> exit 0 silently -> behaves as if no anchor.
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
CEIL="${ANCHOR_CHAR_CEIL:-1200}"

INPUT="$(cat 2>/dev/null)"
CWD="$PWD"
if [ -z "$CWD" ] || [ "$CWD" = "/" ]; then
  CWD="$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("cwd",""))
except: print("")' 2>/dev/null)"
fi

if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then
  KEY="sess-$CLAUDE_CODE_SESSION_ID"
elif [ -n "$CWD" ]; then
  KEY="cwd-$(hash_key "$CWD")"
else
  exit 0
fi

FLAG="$HOME/.claude/run/anchor/anchor-$KEY.flag"
[ -f "$FLAG" ] || exit 0

SKILL="$(grep '^skill=' "$FLAG" 2>/dev/null | cut -d= -f2-)"
AFILE="$(grep '^anchor_file=' "$FLAG" 2>/dev/null | cut -d= -f2-)"
ARMED_AT="$(grep '^armed_at=' "$FLAG" 2>/dev/null | cut -d= -f2-)"
NOW="$(date +%s 2>/dev/null)"

# TTL: stale flag -> delete + silent
if [ -n "$ARMED_AT" ] && [ -n "$NOW" ]; then
  if [ $(( NOW - ARMED_AT )) -ge $(( TTL_HOURS * 3600 )) ]; then rm -f "$FLAG" 2>/dev/null; exit 0; fi
fi
if [ -z "$AFILE" ] || [ ! -f "$AFILE" ]; then exit 0; fi

# read anchor; strip control/zero-width/bidi but KEEP tab(011) + newline(012)
BODY="$(cat "$AFILE" 2>/dev/null | LC_ALL=C tr -d '\000-\010\013-\037\177' 2>/dev/null | /usr/bin/perl -CSD -pe 's/[\x{200B}-\x{200D}\x{FEFF}\x{202A}-\x{202E}\x{2066}-\x{2069}]//g' 2>/dev/null)"
[ -z "$BODY" ] && exit 0

# token ceiling — a bloated anchor can't flood every turn
if [ "${#BODY}" -gt "$CEIL" ]; then
  BODY="$(printf '%s' "$BODY" | cut -c1-"$CEIL")
…[anchor truncated at ${CEIL} chars — keep it lean (~150 tokens)]"
fi

printf '%s\n' "[SKILL ANCHOR — ${SKILL:-active skill} · harness-injected every turn, NOT user input. These are YOUR standing principles; the user did not just type this.]"
printf '%s\n' "$BODY"
printf '%s\n' "↳ Before responding: silently re-confirm you are LEADING per the above — not drifting into the user's framing/terminology or a side-quest. Re-anchor if you've slipped. (You MAY still adapt when the user is genuinely right — anchor your PRINCIPLES, don't go deaf.)"
exit 0
