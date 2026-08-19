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
#      person typed. Key derivation mirrors pm_flag.sh — keep them identical.
# UPDATED: 2026-08-11 (ported; the shasum shim added, per the Git Bash floor)
# FAIL_POSTURE: degrade-safe (any error -> exit 0; a missing flag simply means "no hand-set rung")
# ─────────────────────────────────────────────────────────────────────────────
#   altitude_flag.sh set --10k "<text>" [--5k "<text>"]   # set either or both rungs
#   altitude_flag.sh status                                # print the armed rungs, or "none"
#   altitude_flag.sh clear                                 # remove this session's rungs
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

DIR="$HOME/.claude/run/altitude"; mkdir -p "$DIR" 2>/dev/null
if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then KEY="sess-$CLAUDE_CODE_SESSION_ID"
else KEY="cwd-$(hash_key "$PWD")"; fi
FLAG="$DIR/alt-$KEY.flag"
NOW="$(date +%s 2>/dev/null)"

flatten() { printf '%s' "$1" | tr '\n\r' '  ' | sed 's/[[:space:]]\{2,\}/ /g; s/^ //; s/ $//'; }
getf()    { grep "^$1=" "$FLAG" 2>/dev/null | cut -d= -f2-; }

case "$1" in
  set)
    shift
    TEN="$(getf ten_k)"; FIVE="$(getf five_k)"
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
    { echo "ten_k=$TEN"; echo "five_k=$FIVE"; echo "armed_at=$NOW"; echo "cwd=$PWD"; echo "session=$CLAUDE_CODE_SESSION_ID"; } > "$FLAG" 2>/dev/null
    echo "altitude rungs armed for this session:"
    [ -n "$TEN" ]  && echo "  10,000 — $TEN"
    [ -n "$FIVE" ] && echo "   5,000 — $FIVE"
    ;;
  status)
    if [ ! -f "$FLAG" ]; then echo "none"; exit 0; fi
    ASESS="$(getf session)"
    if [ -n "$CLAUDE_CODE_SESSION_ID" ] && [ -n "$ASESS" ] && [ "$ASESS" != "$CLAUDE_CODE_SESSION_ID" ]; then
      echo "none"; exit 0
    fi
    TEN="$(getf ten_k)"; FIVE="$(getf five_k)"
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
