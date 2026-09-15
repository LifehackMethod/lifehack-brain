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
# SIGNPOST: shared mechanics (key derivation, TTL expiry, sweep-clear) live in
#           system/hooks/lib/flag.sh — change those there, not here. This file owns only
#           its own arg validation (slug + anchor-file-must-exist) and its own payload/output shape.
# UPDATED: 2026-09-15 (B5.1 — converted to a thin shim over system/hooks/lib/flag.sh; CLI
#          contract, payload keys, and output text unchanged. Was: 2026-06-17, new — Skill
#          Anchor; mirrors pm_flag.sh)
# ─────────────────────────────────────────────────────────────────────────────
#   skill_anchor.sh arm <skill-slug> <abs_anchor_file>   # turn anchoring ON
#   skill_anchor.sh clear                                # turn it OFF (this session)
#   skill_anchor.sh status                               # print active slug or "none"
# ─────────────────────────────────────────────────────────────────────────────

set +e

# Condition ⑤ (D6): resolve the shared library relative to THIS shim's own location, quoted — the
# notes root and the plugin cache path both contain spaces, so an unquoted expansion breaks.
_SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
_LIB="$_SELF_DIR/lib/flag.sh"
if [ ! -f "$_LIB" ]; then
  echo "skill_anchor.sh: FATAL — shared library missing at $_LIB (cannot arm/clear/read anchor state)" >&2
  exit 1
fi
# shellcheck source=lib/flag.sh
. "$_LIB" || { echo "skill_anchor.sh: FATAL — shared library at $_LIB failed to load" >&2; exit 1; }
for _fn in flag_init flag_write flag_get flag_ttl_expired flag_clear_sweep; do
  command -v "$_fn" >/dev/null 2>&1 || { echo "skill_anchor.sh: FATAL — shared library at $_LIB is missing $_fn() (corrupt)" >&2; exit 1; }
done

TTL_HOURS="${ANCHOR_TTL_HOURS:-12}"
flag_init anchor anchor

case "$1" in
  arm)
    if [ -z "$2" ] || [ -z "$3" ]; then echo "arm: <skill-slug> <abs_anchor_file> required" >&2; exit 1; fi
    if [ ! -f "$3" ]; then echo "arm: anchor file not found: $3" >&2; exit 1; fi
    flag_write "skill=$2" "anchor_file=$3" "armed_at=$NOW" "cwd=$PWD" "session=$CLAUDE_CODE_SESSION_ID"
    echo "ANCHOR ARMED: $2 -> $3 (session ${CLAUDE_CODE_SESSION_ID:-none})";;
  clear)
    n="$(flag_clear_sweep anchor)"
    echo "ANCHOR CLEARED ($n)";;
  status)
    if [ -f "$FLAG" ]; then
      SK="$(flag_get skill)"
      if flag_ttl_expired $(( TTL_HOURS * 3600 )); then
        echo "none"
      elif [ -z "$SK" ]; then echo "none"
      else echo "$SK"; fi
    else echo "none"; fi;;
  *) echo "usage: skill_anchor.sh arm <slug> <anchor_file> | clear | status" >&2; exit 2;;
esac
exit 0
