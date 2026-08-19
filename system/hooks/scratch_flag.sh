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
#           not ship; the behaviour is here.
# FAIL_POSTURE: degrade-safe — a recorder, never a gate.
# UPDATED: 2026-08-11 (ported; the shasum shim added, per the Git Bash floor)
# ─────────────────────────────────────────────────────────────────────────────
#   scratch_flag.sh arm <scratch_path> <skill>   # a scratchpad became active this session
#   scratch_flag.sh clear                        # scratchpad closed
#   scratch_flag.sh status                       # armed | none
# ── hash_key: the fallback session key, and it MUST match everywhere ──────────────────────────────
# When the harness gives us no session id we key on the working directory instead. `shasum` does that
# on macOS and Linux and is ABSENT from Git Bash on Windows, where it produces an EMPTY key — so every
# window on that machine would collide on one flag, silently.
# ⚠ SHA-1 DELIBERATELY, NOT SHA-256: this must equal what `shasum` prints, or a machine that has
# shasum and a machine that does not would key the SAME folder differently.
hash_key() {
  _hk="$(printf '%s' "$1" | shasum 2>/dev/null | cut -c1-12)"
  if [ -z "$_hk" ]; then
    _hk="$(printf '%s' "$1" | python3 -c 'import hashlib,sys; sys.stdout.write(hashlib.sha1(sys.stdin.buffer.read()).hexdigest())' 2>/dev/null | cut -c1-12)"
  fi
  printf '%s' "$_hk"
}

set +e
TTL_MIN="${SCRATCH_TTL_MIN:-30}"
FLAGDIR="$HOME/.claude/run/scratch"; mkdir -p "$FLAGDIR" 2>/dev/null
if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then KEY="sess-$CLAUDE_CODE_SESSION_ID"
else KEY="cwd-$(hash_key "$PWD")"; fi
FLAG="$FLAGDIR/scratch-$KEY.flag"
NOW="$(date +%s 2>/dev/null)"
case "$1" in
  arm)   { echo "scratch_path=$2"; echo "skill=$3"; echo "armed_at=$NOW"; echo "session=$CLAUDE_CODE_SESSION_ID"; } > "$FLAG"
         echo "SCRATCH-ARMED: ${3:-?} -> ${2:-?} (session ${CLAUDE_CODE_SESSION_ID:-none})";;
  clear) rm -f "$FLAG" 2>/dev/null
         if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then
           for f in "$FLAGDIR"/scratch-*.flag; do [ -f "$f" ] || continue
             s="$(grep '^session=' "$f" 2>/dev/null | cut -d= -f2-)"
             [ "$s" = "$CLAUDE_CODE_SESSION_ID" ] && rm -f "$f" 2>/dev/null; done; fi
         echo "SCRATCH-CLEARED";;
  status) if [ -f "$FLAG" ]; then AT="$(grep '^armed_at=' "$FLAG" 2>/dev/null | cut -d= -f2-)"
            if [ -n "$AT" ] && [ -n "$NOW" ] && [ $(( NOW - AT )) -ge $(( TTL_MIN * 60 )) ]; then rm -f "$FLAG"; echo "none"; else echo "armed"; fi
          else echo "none"; fi;;
  *) echo "usage: scratch_flag.sh arm <path> <skill> | clear | status" >&2; exit 2;;
esac
exit 0
