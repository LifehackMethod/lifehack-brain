#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: reported 2026-08-05, in the words of the person it kept happening to: "constantly it is
#      pulled into the lowest altitude and it loses its perspective." A session fixes the file
#      correctly while forgetting the seam the fix serves and the goal the seam serves. He was
#      re-typing a three-altitude filter by hand every time, which is a missed system patch —
#      fix the system, not your notes. Prose alone cannot fix it: the drift happens ~20 turns
#      after any doctrine was loaded, which is long past the point where it is still in context.
# GUARDS: Nothing. This is a UserPromptSubmit INJECT observer — it NEVER blocks. It ASKS the
#      session to RESTATE its frame (hook-sop.md §3.3 active-recall) rather than telling it
#      anything, because the hook is blind to what the session is doing and a confidently wrong
#      frame is worse than none. It PARSES NO BRIEF AND NO PLAN — it hands over PATHS only
#      (measured 2026-08-05: the FRAME heading and desired-outcome format vary across briefs,
#      so a mechanical extractor is unreliable; a reader is not). Fires once per token bucket,
#      on a bucket offset by 10k. ⚠ IN THE DONOR SYSTEM that offset was a bet on landing ~1 turn
#      BEFORE a sibling rollup hook, and an adversarial audit on 2026-08-05 refuted it: the offset
#      only wins if a single turn adds <10k tokens between the two checks, and a tool-heavy turn
#      (85k -> 150k in one step, demonstrated) reverses the order silently. That sibling is not in
#      this repo, so the bet is moot here — the offset is kept only because it staggers the fire
#      points away from round numbers. The lesson survives the hook: an ordering nothing reports is
#      not an ordering you have.
# REDIRECT: N/A (non-blocking). Watermark ~/.claude/run/altitude/alt-<KEY>.state. Manual rungs
#      via `altitude_flag.sh set` (flag ~/.claude/run/altitude/alt-<KEY>.flag) or /altitude.
#      Retune cadence with ALTITUDE_CAPTURE_EVERY / ALTITUDE_OFFSET env vars.
# SIGNPOST: The RULE lives in system/work-altitude-doctrine.md (three rungs + the four-member
#      closed answer set + why NO-FRAME is correct). Change the rule THERE, never by editing this
#      hook.
# UPDATED: 2026-08-11 (ported; the shasum shim added, and the two sibling-hook paths now resolve
#      from this script's own location instead of a clone name that does not exist here)
# FAIL_POSTURE: degrade-safe (any error -> exit 0 silently; a missed re-anchor must never wedge a turn)
# ─────────────────────────────────────────────────────────────────────────────
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

# ⛔ THE TWO SIBLING HOOKS BELOW WERE ADDRESSED BY AN ABSOLUTE PATH INTO THE DONOR SYSTEM'S OWN
# CLONE, under a folder name that exists on exactly one machine. Anywhere else both reads returned
# nothing, and this hook would have gone on re-anchoring every session with "no brief" and "no
# plan" forever — never failing, never right. They live beside this file; that is how we find them.
HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd -P)"

set +e

CAPTURE_EVERY="${ALTITUDE_CAPTURE_EVERY:-50000}"    # ~5.4 turns @ the measured 9,313 tok/turn median.
                                                     # HALVED from 100000 on 2026-08-06 ("run it every 5").
                                                     # ⚠ In the donor system this deliberately stopped matching a sibling gate that stayed at
                                                     # 100000; that gate is not part of this repo, so here the number stands alone. See OFFSET.
ALTITUDE_OFFSET="${ALTITUDE_OFFSET:-10000}"          # fires at 40k/90k/140k/190k. The 90k fire still lands ~1.07 turns
                                                     # BEFORE the 100k scratchpad rollup, so the original ordering bet is
                                                     # preserved on ALTERNATE buckets; the others are standalone re-anchors.
DROP_FLOOR="${ALTITUDE_DROP_FLOOR:-50000}"           # a fall this large means a compaction happened
MAX_CHARS="${ALTITUDE_MAX_CHARS:-900}"               # hard ceiling ~150 tokens (hook-sop.md §3.3)

INPUT="$(cat 2>/dev/null)"
[ -n "$INPUT" ] || exit 0

read -r SID TP < <(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('session_id','') or '-', d.get('transcript_path','') or '-')
except Exception:
    print('-', '-')
" 2>/dev/null)
[ "$SID" = "-" ] && SID=""
[ "$TP" = "-" ] && TP=""
[ -n "$SID" ] || SID="$CLAUDE_CODE_SESSION_ID"

# ── session key — MUST match pm_flag.sh:19-24 derivation exactly ─────────────
if [ -n "$SID" ]; then KEY="sess-$SID"
elif [ -n "$PWD" ]; then KEY="cwd-$(hash_key "$PWD")"
else exit 0; fi

# ── context size = the LAST assistant usage block in the transcript ──────────
TOK="$(printf '%s' "$INPUT" | python3 -c "
import sys, json, os
try: d = json.load(sys.stdin)
except Exception: print(''); sys.exit()
tp = d.get('transcript_path','')
if not tp or not os.path.exists(tp): print(''); sys.exit()
last = None
try:
    with open(tp, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            try: r = json.loads(line)
            except Exception: continue
            m = r.get('message', r); u = m.get('usage')
            if m.get('role') == 'assistant' and isinstance(u, dict): last = u
except Exception: print(''); sys.exit()
if not last: print(''); sys.exit()
print((last.get('input_tokens',0) or 0)
      + (last.get('cache_creation_input_tokens',0) or 0)
      + (last.get('cache_read_input_tokens',0) or 0))
" 2>/dev/null)"
case "$TOK" in ''|*[!0-9]*) exit 0;; esac
[ "$TOK" -gt 0 ] || exit 0

BUCKET=$(( (TOK + ALTITUDE_OFFSET) / CAPTURE_EVERY ))
K=$(( TOK / 1000 ))

SDIR="$HOME/.claude/run/altitude"; mkdir -p "$SDIR" 2>/dev/null
SFILE="$SDIR/alt-$KEY.state"
LASTBUCKET="$(grep '^bucket=' "$SFILE" 2>/dev/null | cut -d= -f2-)"
LASTTOK="$(grep '^tok=' "$SFILE" 2>/dev/null | cut -d= -f2-)"
case "$LASTBUCKET" in ''|*[!0-9]*) LASTBUCKET="";; esac
case "$LASTTOK"    in ''|*[!0-9]*) LASTTOK="";;    esac

REASON=""
if [ -z "$LASTBUCKET" ]; then
  { echo "bucket=$BUCKET"; echo "tok=$TOK"; } > "$SFILE" 2>/dev/null
  exit 0
elif [ -n "$LASTTOK" ] && [ "$TOK" -lt $(( LASTTOK - DROP_FLOOR )) ]; then
  REASON="post-compaction"
elif [ "$BUCKET" -gt "$LASTBUCKET" ]; then
  REASON="~${K}k ctx"
else
  exit 0
fi

{ echo "bucket=$BUCKET"; echo "tok=$TOK"; } > "$SFILE" 2>/dev/null

BRIEF="$(CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKDIR/pm_flag.sh" status 2>/dev/null)"
[ "$BRIEF" = "none" ] && BRIEF=""
PLAN="$(CLAUDE_CODE_SESSION_ID="$SID" bash "$HOOKDIR/plan_flag.sh" path 2>/dev/null)"
[ "$PLAN" = "none" ] && PLAN=""

AFLAG="$SDIR/alt-$KEY.flag"
SET10=""; SET5=""
if [ -f "$AFLAG" ]; then
  ASESS="$(grep '^session=' "$AFLAG" 2>/dev/null | cut -d= -f2-)"
  if [ -z "$SID" ] || [ -z "$ASESS" ] || [ "$ASESS" = "$SID" ]; then
    SET10="$(grep '^ten_k=' "$AFLAG" 2>/dev/null | cut -d= -f2-)"
    SET5="$(grep '^five_k=' "$AFLAG" 2>/dev/null | cut -d= -f2-)"
  fi
fi

emit() {
  b="$1"; p="$2"
  b="${b/#$HOME/~}"; p="${p/#$HOME/~}"
  if [ -n "$SET10" ]; then src10="set: ${SET10}"
  elif [ -n "$b" ];   then src10="read ${b}"
  else                     src10="no brief — a standing goal above it, or none"; fi
  if [ -n "$SET5" ]; then src5="set: ${SET5}"
  elif [ -n "$p" ];  then src5="read ${p}"
  else                    src5="no plan — the seam, or the learning produced"; fi
  printf '%s\n' "[WORK ALTITUDE (${REASON}) — harness-injected, not user input.]"
  printf '%s\n' "Name your three altitudes in your reply, then carry on:"
  printf '%s\n' "  10,000 — what this is for: ${src10}"
  printf '%s\n' "   5,000 — what it sits inside: ${src5}"
  printf '%s\n' "  ground — what you are touching now"
  printf '%s\n' "Reply exactly one of: FRAMED | PARTIAL (name the gap) | NO-FRAME | UNCHANGED."
  printf '%s\n' "NO-FRAME (ground only, no larger frame) is CORRECT here — never invent a rung. Rule: system/work-altitude-doctrine.md"
}

MSG="$(emit "$BRIEF" "$PLAN")"
if [ "${#MSG}" -gt "$MAX_CHARS" ]; then
  MSG="$(emit "$(basename "$BRIEF" 2>/dev/null)" "$(basename "$PLAN" 2>/dev/null)")"
fi
if [ "${#MSG}" -gt "$MAX_CHARS" ]; then
  # BOTH tiers still oversized (pathological path lengths). Emitting nothing here would
  # burn the bucket and lose this re-anchor permanently, with no signal anywhere — the
  # silent-failure mode hook-sop.md §4 exists to prevent. Degrade to a pathless floor
  # that cannot overflow, rather than vanishing.
  MSG="[WORK ALTITUDE (${REASON}) — harness-injected, not user input.]
Name your three altitudes (10,000 / 5,000 / ground) in your reply, then carry on.
Reply exactly one of: FRAMED | PARTIAL (name the gap) | NO-FRAME | UNCHANGED.
NO-FRAME (ground only, no larger frame) is CORRECT here — never invent a rung. Rule: system/work-altitude-doctrine.md"
fi

printf '%s\n' "$MSG"
exit 0
