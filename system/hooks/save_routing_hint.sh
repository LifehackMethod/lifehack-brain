#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: a session — especially a fresh or a compacted one — does not reliably know that a bare
#      "save this / remember this" goes to the ACTIVE project brief's `## 7. SCRATCHPAD` section.
#      Left to itself it searches the filesystem for something called a scratchpad and stalls.
#      An instruction in CLAUDE.md gets skimmed; this fires on the person's actual words, every
#      session, so the routing cannot be missed.
# GUARDS: nothing. OBSERVE + INJECT only — it never blocks (UserPromptSubmit, stdout, exit 0).
#      It fires ONLY when the prompt matches a save phrase, so it is silent the rest of the time.
#      A project armed -> "append to THIS brief's scratchpad, do not go looking". No project ->
#      "ASK which, do not guess".
#      HANDOFF-SAFE: a pasted handoff ALWAYS names "## SCRATCHPAD" and carries a /checkin line.
#      That pair is the fingerprint of a paste, not of a save request, so it bails silently on
#      them — the bare-noun match used to fire on every handoff reload and derail a fresh session
#      into "where do I save?" instead of running /checkin.
# REDIRECT: none needed; it does not block. The scratchpad IS a section of the brief that
#      `pm_flag.sh status` names — never a file to search for.
# SIGNPOST: the routing rule lives in `.claude/skills/save/SKILL.md`; the brief's section spine is
#      in `.claude/skills/project-manager/references/spine.md`. Change the wording there first.
# FAIL_POSTURE: degrade-safe. Any error or unreadable input -> exit 0, silent. It must never wedge
#      a turn; a missing hint is a small loss, a stuck turn is a large one.
# UPDATED: 2026-08-11 (ported; paths resolved from this script, not from a home directory)
# ─────────────────────────────────────────────────────────────────────────────
set +e
INPUT="$(cat 2>/dev/null)"

PROMPT="$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try: d = json.loads(sys.stdin.read() or "{}")
except Exception: print(""); sys.exit()
print((d.get("prompt") or "").strip())
' 2>/dev/null)"
[ -n "$PROMPT" ] || exit 0

IS_SAVE="$(printf '%s' "$PROMPT" | python3 -c '
import sys, re
t = sys.stdin.read().lower()
# A handoff / reload paste is NOT a save request. Every handoff names the scratchpad section and
# carries a /checkin line; that pair is the fingerprint. Bail silent.
if re.search(r"##\s*\d*\.?\s*scratch ?pad", t) or "/checkin" in t:
    print("0"); sys.exit()
# a save verb + a demonstrative, OR a VERB-GATED scratchpad mention (never the bare noun)
save = re.search(r"\b(save|remember|capture|note|jot|hold|keep)\b.{0,24}\b(this|that|it|these|info|information|down|note)\b", t)
pad  = (re.search(r"\b(save|write|add|put|append|jot|drop|stick|log|record|note|remember|capture|keep|hold)\b.{0,24}\bscratch ?pad\b", t)
        or re.search(r"\bscratch ?pad\b.{0,24}\b(it|this|that|these|note)\b", t))
print("1" if (save or pad) else "0")
' 2>/dev/null)"
[ "$IS_SAVE" = "1" ] || exit 0

# Where pm_flag.sh lives, resolved FROM THIS SCRIPT — never a hardcoded home directory, never $PWD.
# A hook runs with the CALLER's working directory, so a bare `git rev-parse` would answer for
# whatever repo they happen to be in. The trim fallback covers a clone with no git available.
_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
_REPO="$(cd "$_HOOKDIR" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)"
[ -n "$_REPO" ] || _REPO="${_HOOKDIR%/system/hooks}"

BRIEF="$(bash "$_REPO/system/hooks/pm_flag.sh" status 2>/dev/null)"
if [ -n "$BRIEF" ] && [ "$BRIEF" != "none" ]; then
  echo "[save-routing] A bare \"save this\" goes to the \`## 7. SCRATCHPAD\` section of the active project's brief: ${BRIEF}. That section IS the scratchpad — do not search the filesystem for one. Append to it, chronologically; it is never wiped by hand."
else
  echo "[save-routing] They asked to save, and NO project is armed. Do not guess a home — ASK: \"No project's active — save to a standalone note, or which project's brief?\" (Normally it is the \`## 7. SCRATCHPAD\` section of the armed brief.)"
fi
exit 0
