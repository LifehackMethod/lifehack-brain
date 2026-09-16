#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: The status-line HUD shows "scratch: on" when a session has an active scratchpad.
#      Anything that opens a scratchpad arms it — `/planning-daily`, or a session told to "start a
#      scratchpad". env-var triggers do not survive across tool calls; a FILE does. Same proven
#      pattern as pm_flag.sh and throughline_flag.sh.
# GUARDS: None — a tiny state writer. Flag is SESSION-scoped + machine-local
#         (keyed by CLAUDE_CODE_SESSION_ID; cwd-hash fallback). status self-expires (30m TTL).
# REDIRECT: Flag ~/.claude/run/scratch/scratch-sess-<id>.flag. Reader: system/statusline.sh.
# SIGNPOST: what the status bar shows is `system/statusline.sh`, which reads this flag. ⛔ The plan
#           and research write-up this was built from are records in the author's own notes and do
#           not ship; the behaviour is here. Shared mechanics (key derivation, TTL expiry,
#           sweep-clear) live in system/hooks/lib/flag.sh — change those there, not here.
# FAIL_POSTURE: degrade-safe — a recorder, never a gate.
# UPDATED: 2026-09-15 (B5.1 — converted to a thin shim over system/hooks/lib/flag.sh; CLI
#          contract, payload keys, and output text unchanged. Was: 2026-08-11, ported; the shasum
#          shim added, per the Git Bash floor)
# ─────────────────────────────────────────────────────────────────────────────
#   scratch_flag.sh arm <scratch_path> <skill>   # a scratchpad became active this session
#   scratch_flag.sh clear                        # scratchpad closed
#   scratch_flag.sh status                       # armed | none
# ─────────────────────────────────────────────────────────────────────────────

set +e

# Condition ⑤ (D6): resolve the shared library relative to THIS shim's own location, quoted — the
# notes root and the plugin cache path both contain spaces, so an unquoted expansion breaks.
_SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
_LIB="$_SELF_DIR/lib/flag.sh"
if [ ! -f "$_LIB" ]; then
  echo "scratch_flag.sh: FATAL — shared library missing at $_LIB (cannot arm/clear/read scratch state)" >&2
  exit 1
fi
# shellcheck source=lib/flag.sh
. "$_LIB" || { echo "scratch_flag.sh: FATAL — shared library at $_LIB failed to load" >&2; exit 1; }
for _fn in flag_init flag_write flag_get flag_ttl_expired flag_clear_sweep; do
  command -v "$_fn" >/dev/null 2>&1 || { echo "scratch_flag.sh: FATAL — shared library at $_LIB is missing $_fn() (corrupt)" >&2; exit 1; }
done

TTL_MIN="${SCRATCH_TTL_MIN:-30}"
flag_init scratch scratch

case "$1" in
  arm)   flag_write "scratch_path=$2" "skill=$3" "armed_at=$NOW" "session=$CLAUDE_CODE_SESSION_ID"
         echo "SCRATCH-ARMED: ${3:-?} -> ${2:-?} (session ${CLAUDE_CODE_SESSION_ID:-none})";;
  clear) flag_clear_sweep scratch >/dev/null
         echo "SCRATCH-CLEARED";;
  status) if [ -f "$FLAG" ]; then
            if flag_ttl_expired $(( TTL_MIN * 60 )); then echo "none"; else echo "armed"; fi
          else echo "none"; fi;;
  *) echo "usage: scratch_flag.sh arm <path> <skill> | clear | status" >&2; exit 2;;
esac
exit 0
