#!/usr/bin/env bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "save_routing_hint.sh" "UserPromptSubmit" "" 2>/dev/null || true' EXIT
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
#      2026-10-30: trigger narrowed to an imperative save intent (see the IS_SAVE comment); logic moved to lib/ups_triggers.py.
# ─────────────────────────────────────────────────────────────────────────────
run() {
set +e
INPUT="$(cat 2>/dev/null)"

PROMPT="$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try: d = json.loads(sys.stdin.read() or "{}")
except Exception: print(""); sys.exit()
print((d.get("prompt") or "").strip())
' 2>/dev/null)"
[ -n "$PROMPT" ] || exit 0

# 2026-10-30 (sop-cleanup Phase 2 ruling 4.4, 12-token-audit U8): the old trigger treated "keep", "note", "hold" and
# "remember" as save verbs, so "keep it simple" / "hold it 10 seconds" / "I can't remember. This ..." fired it (about 90%
# false on 2,253-3,005 real prompts, and in the no-project case it made the model ask a wrong question). The trigger is
# now an IMPERATIVE save intent only, one shared copy in lib/ups_triggers.py (also keeps the handoff-paste bail-out).
# Degrade-safe: a missing or broken helper prints nothing -> "0" -> silent.
_SRH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
IS_SAVE="$(printf '%s' "$PROMPT" | python3 "$_SRH_DIR/lib/ups_triggers.py" save 2>/dev/null)"
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
}

if [ "${BASH_SOURCE[0]:-$0}" = "$0" ]; then
  run
  exit $?
fi
