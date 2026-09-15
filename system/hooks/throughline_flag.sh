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
#      disagree about the destination is the worst of both. Shared mechanics (key derivation, TTL
#      expiry, sweep-clear) live in system/hooks/lib/flag.sh — change those there, not here.
# FAIL_POSTURE: degrade-safe — never a gate. Any error exits 0 and the guard simply stays off.
# UPDATED: 2026-09-15 (B5.1 — converted to a thin shim over system/hooks/lib/flag.sh; CLI
#      contract, payload keys, and output text unchanged. Was: 2026-08-11, ported; the shasum shim
#      added, and the flag dir renamed from `eval` to `throughline`)
# ─────────────────────────────────────────────────────────────────────────────
#   throughline_flag.sh arm     # start of a /throughline run
#   throughline_flag.sh clear   # end of a /throughline run
#   throughline_flag.sh status  # armed | none
# ─────────────────────────────────────────────────────────────────────────────

set +e

# Condition ⑤ (D6): resolve the shared library relative to THIS shim's own location, quoted — the
# notes root and the plugin cache path both contain spaces, so an unquoted expansion breaks.
_SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
_LIB="$_SELF_DIR/lib/flag.sh"
if [ ! -f "$_LIB" ]; then
  echo "throughline_flag.sh: FATAL — shared library missing at $_LIB (cannot arm/clear/read throughline state)" >&2
  exit 1
fi
# shellcheck source=lib/flag.sh
. "$_LIB" || { echo "throughline_flag.sh: FATAL — shared library at $_LIB failed to load" >&2; exit 1; }
for _fn in flag_init flag_write flag_get flag_ttl_expired flag_clear_sweep; do
  command -v "$_fn" >/dev/null 2>&1 || { echo "throughline_flag.sh: FATAL — shared library at $_LIB is missing $_fn() (corrupt)" >&2; exit 1; }
done

TTL_MIN="${THROUGHLINE_TTL_MIN:-30}"
flag_init throughline tl

case "$1" in
  arm)   flag_write "armed_at=$NOW" "session=$CLAUDE_CODE_SESSION_ID"
         echo "THROUGHLINE-ARMED (session ${CLAUDE_CODE_SESSION_ID:-none}) — writes are now scoped to the findings folder";;
  clear) flag_clear_sweep tl >/dev/null
         echo "THROUGHLINE-CLEARED";;
  status) if [ -f "$FLAG" ]; then
            if flag_ttl_expired $(( TTL_MIN * 60 )); then echo "none"; else echo "armed"; fi
          else echo "none"; fi;;
  *) echo "usage: throughline_flag.sh arm|clear|status" >&2; exit 2;;
esac
exit 0
