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
#         edit this file. Shared mechanics (key derivation, TTL expiry, sweep-clear) live in
#         system/hooks/lib/flag.sh — change those there, not here.
# FAIL_POSTURE: degrade-safe — a recorder, never a gate. Any error exits 0 and the session behaves
#         exactly as if numbers-mode had never been armed.
# UPDATED: 2026-09-15 (B5.1 — converted to a thin shim over system/hooks/lib/flag.sh; CLI
#          contract, payload keys, and output text unchanged. Was: 2026-08-11, ported; the shasum
#          shim added, per the Git Bash floor)
# ─────────────────────────────────────────────────────────────────────────────
#   numbers_flag.sh arm     # arm numbers-mode for this session
#   numbers_flag.sh clear   # disarm (remove this session's flag(s))
#   numbers_flag.sh status  # print "armed" or "none"
# ─────────────────────────────────────────────────────────────────────────────

set +e

# Condition ⑤ (D6): resolve the shared library relative to THIS shim's own location, quoted — the
# notes root and the plugin cache path both contain spaces, so an unquoted expansion breaks.
_SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
_LIB="$_SELF_DIR/lib/flag.sh"
if [ ! -f "$_LIB" ]; then
  echo "numbers_flag.sh: FATAL — shared library missing at $_LIB (cannot arm/clear/read numbers state)" >&2
  exit 1
fi
# shellcheck source=lib/flag.sh
. "$_LIB" || { echo "numbers_flag.sh: FATAL — shared library at $_LIB failed to load" >&2; exit 1; }
for _fn in flag_init flag_write flag_get flag_ttl_expired flag_clear_sweep; do
  command -v "$_fn" >/dev/null 2>&1 || { echo "numbers_flag.sh: FATAL — shared library at $_LIB is missing $_fn() (corrupt)" >&2; exit 1; }
done

TTL_HOURS="${NUMBERS_TTL_HOURS:-12}"
flag_init numbers numbers

case "$1" in
  arm)
    flag_write "armed_at=$NOW" "cwd=$PWD" "session=$CLAUDE_CODE_SESSION_ID"
    echo "ARMED: numbers-mode (session ${CLAUDE_CODE_SESSION_ID:-none}, cwd $PWD)";;
  clear)
    n="$(flag_clear_sweep numbers)"
    echo "CLEARED ($n)";;
  status)
    if [ -f "$FLAG" ]; then
      if flag_ttl_expired $(( TTL_HOURS * 3600 )); then echo "none"; else echo "armed"; fi
    else echo "none"; fi;;
  *) echo "usage: numbers_flag.sh arm | clear | status" >&2; exit 2;;
esac
exit 0
