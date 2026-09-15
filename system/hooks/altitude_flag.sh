#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: inject_work_altitude.sh reads the 10,000-ft rung from the armed BRIEF and the 5,000-ft
#      rung from the armed PLAN. Plenty of real work has neither. The case that produced this
#      file, on 2026-08-05: someone designing the altitude hook itself, with no project and no
#      plan armed, while the true 10,000-ft view ("a machine that builds better skills") was
#      perfectly well known. Without a hand-set path the hook would keep reporting "no brief"
#      for work that genuinely HAS a frame, which trains the reader to ignore it.
# GUARDS: None — a tiny per-session state writer, never a gate. Always exits 0 so it can never
#      wedge a turn. Session-scoped: the flag records `session=` and the reading hook ignores a
#      flag stamped with a different session, so one window's rungs cannot leak into another.
#      Values are flattened to a single line (newlines/CRs stripped) because the store is
#      line-oriented key=value, same shape as pm_flag.sh:30.
# REDIRECT: Flag file ~/.claude/run/altitude/alt-<KEY>.flag. Reader: inject_work_altitude.sh.
#      User-facing entry point: the /altitude command. Off-switch: altitude_flag.sh clear.
# SIGNPOST: The RULE (what the three rungs ARE, and why NO-FRAME is a correct answer) lives in
#      system/work-altitude-doctrine.md. Change the rule THERE; this file only stores what a
#      person typed. Key derivation mirrors pm_flag.sh — keep them identical. Shared mechanics
#      (key derivation, flag init) live in system/hooks/lib/flag.sh — change those there, not
#      here. NOTE: unlike the other four flags, `clear` here removes only THIS session's own file
#      and deliberately does not sweep — that divergence predates B5.1 and is preserved as-is, not
#      folded into the library's flag_clear_sweep.
# UPDATED: 2026-09-15 (B5.1 — converted to a thin shim over system/hooks/lib/flag.sh; CLI
#      contract, payload keys, and output text unchanged. Was: 2026-08-11, ported; the shasum shim
#      added, per the Git Bash floor)
# FAIL_POSTURE: degrade-safe (any error -> exit 0; a missing flag simply means "no hand-set rung")
# ─────────────────────────────────────────────────────────────────────────────
#   altitude_flag.sh set --10k "<text>" [--5k "<text>"]   # set either or both rungs
#   altitude_flag.sh status                                # print the armed rungs, or "none"
#   altitude_flag.sh clear                                 # remove this session's rungs
# ─────────────────────────────────────────────────────────────────────────────

set +e

# Condition ⑤ (D6): resolve the shared library relative to THIS shim's own location, quoted — the
# notes root and the plugin cache path both contain spaces, so an unquoted expansion breaks.
_SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
_LIB="$_SELF_DIR/lib/flag.sh"
if [ ! -f "$_LIB" ]; then
  echo "altitude_flag.sh: FATAL — shared library missing at $_LIB (cannot set/clear/read altitude state)" >&2
  exit 1
fi
# shellcheck source=lib/flag.sh
. "$_LIB" || { echo "altitude_flag.sh: FATAL — shared library at $_LIB failed to load" >&2; exit 1; }
for _fn in flag_init flag_write flag_get; do
  command -v "$_fn" >/dev/null 2>&1 || { echo "altitude_flag.sh: FATAL — shared library at $_LIB is missing $_fn() (corrupt)" >&2; exit 1; }
done

flag_init altitude alt

flatten() { printf '%s' "$1" | tr '\n\r' '  ' | sed 's/[[:space:]]\{2,\}/ /g; s/^ //; s/ $//'; }

case "$1" in
  set)
    shift
    TEN="$(flag_get ten_k)"; FIVE="$(flag_get five_k)"
    while [ $# -gt 0 ]; do
      case "$1" in
        --10k|--10000) TEN="$(flatten "$2")"; shift 2;;
        --5k|--5000)   FIVE="$(flatten "$2")"; shift 2;;
        *) shift;;
      esac
    done
    if [ -z "$TEN" ] && [ -z "$FIVE" ]; then
      echo "altitude_flag: nothing set — pass --10k \"<text>\" and/or --5k \"<text>\"" >&2
      exit 0
    fi
    flag_write "ten_k=$TEN" "five_k=$FIVE" "armed_at=$NOW" "cwd=$PWD" "session=$CLAUDE_CODE_SESSION_ID"
    echo "altitude rungs armed for this session:"
    [ -n "$TEN" ]  && echo "  10,000 — $TEN"
    [ -n "$FIVE" ] && echo "   5,000 — $FIVE"
    ;;
  status)
    if [ ! -f "$FLAG" ]; then echo "none"; exit 0; fi
    ASESS="$(flag_get session)"
    if [ -n "$CLAUDE_CODE_SESSION_ID" ] && [ -n "$ASESS" ] && [ "$ASESS" != "$CLAUDE_CODE_SESSION_ID" ]; then
      echo "none"; exit 0
    fi
    TEN="$(flag_get ten_k)"; FIVE="$(flag_get five_k)"
    [ -z "$TEN" ] && [ -z "$FIVE" ] && { echo "none"; exit 0; }
    [ -n "$TEN" ]  && echo "10k=$TEN"
    [ -n "$FIVE" ] && echo "5k=$FIVE"
    ;;
  clear)
    rm -f "$FLAG" 2>/dev/null; echo "altitude rungs cleared"
    ;;
  *)
    echo "usage: altitude_flag.sh set --10k \"<text>\" [--5k \"<text>\"] | status | clear" >&2
    ;;
esac
exit 0
