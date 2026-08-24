#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: As context fills, reasoning frays (past ~65% of window) — the user should jump to
#      a FRESH session before it does. This UserPromptSubmit INJECT warns to switch.
#      (F5.4, 2026-07-15: the old "sweep the scratchpad" CAPTURE nudge was RETIRED from
#      here — it was ignorable + invisible. Capture is now ENFORCED by the Stop-event
#      scratch_capture_gate.sh, which bounces the turn until the pad is written. This hook
#      keeps ONLY the switch-session warning, which the gate does not cover.)
# GUARDS: Read-only observer — NEVER blocks a prompt. Silent NO-OP unless a scratchpad is
#         active this session (scratch_flag.sh status = armed). Fires at most once per new
#         100k-token bucket past the switch threshold (anti-wallpaper).
# REDIRECT: N/A (non-blocking). State ~/.claude/run/sweep/sweep-<key>.state.
#           Off-switch: scratch_flag.sh clear (no active scratchpad -> silent).
# SIGNPOST: Rule + design = project-system plan (~/.claude/plans/composed-wiggling-treasure.md
#           PHASE 5, F5.4) + brief. Capture enforcement moved to scratch_capture_gate.sh.
#           Context signal = ABSOLUTE token count from the LAST assistant `usage` block in
#           transcript_path (input + cache_creation + cache_read). Change SWITCH_AT if the model window changes.
# FAIL_POSTURE: degrade-safe — any error / unreadable transcript -> exit 0 silent.
# UPDATED: 2026-07-15 (F5.4 switch-warning only; F1.5.2 — also fires off the project brief, not just scratch_flag)
# PORTED: 2026-08-13 from claudeops-config — the scratch_flag.sh / pm_flag.sh calls below were
#      literal `~/claudeops-config/...` paths; they now resolve from this hook's own location.
# ─────────────────────────────────────────────────────────────────────────────
set +e
INPUT="$(cat 2>/dev/null)"

BUCKET_EVERY=100000  # fire at most once per +100k tokens (anti-wallpaper)
SWITCH_AT=600000     # switch-session warning at ~600k tokens (~60% of 1M; reasoning frays past ~65%)

# shasum is NOT guaranteed on PATH (Git Bash on Windows ships without it). Called bare (with
# 2>/dev/null swallowing the error) it silently produces an empty key, collapsing every window's
# state file onto one path. python3 fallback matches hash_key() in guard_cross_project_write.sh.
_hashcwd() {
  if command -v shasum >/dev/null 2>&1; then
    printf '%s' "$PWD" | shasum | cut -c1-12
  else
    printf '%s' "$PWD" | python3 -c 'import hashlib,sys; sys.stdout.write(hashlib.sha1(sys.stdin.buffer.read()).hexdigest())' 2>/dev/null | cut -c1-12
  fi
}

if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then KEY="sess-$CLAUDE_CODE_SESSION_ID"
elif [ -n "$PWD" ]; then KEY="cwd-$(_hashcwd)"
else exit 0; fi

# Resolve THIS repo's root from the hook's own location — never a hardcoded home directory.
_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
_REPO="$(cd "$_HOOKDIR" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)"
[ -n "$_REPO" ] || _REPO="${_HOOKDIR%/system/hooks}"

# active if an explicit scratch_flag is armed OR a project brief is armed (F1.5.2 precedence)
STATUS="$(bash "$_REPO/system/hooks/scratch_flag.sh" status 2>/dev/null)"
if [ "$STATUS" != "armed" ]; then
  PM="$(bash "$_REPO/system/hooks/pm_flag.sh" status 2>/dev/null)"
  [ "$PM" = "none" ] && exit 0   # no scratch_flag AND no project -> dormant
fi

TOK="$(printf '%s' "$INPUT" | python3 -c '
import sys,json,os
try: d=json.load(sys.stdin)
except: print(""); sys.exit()
tp=d.get("transcript_path","")
if not tp or not os.path.exists(tp): print(""); sys.exit()
last=None
try:
    with open(tp) as f:
        for line in f:
            try: o=json.loads(line)
            except: continue
            m=o.get("message",o); u=m.get("usage")
            if m.get("role")=="assistant" and isinstance(u,dict): last=u
except: print(""); sys.exit()
if not last: print(""); sys.exit()
print((last.get("input_tokens",0) or 0)+(last.get("cache_creation_input_tokens",0) or 0)+(last.get("cache_read_input_tokens",0) or 0))
' 2>/dev/null)"
case "$TOK" in ''|*[!0-9]*) exit 0;; esac

# switch-session warning only, once per 100k-bucket past the threshold
[ "$TOK" -ge "$SWITCH_AT" ] || exit 0
STATEDIR="$HOME/.claude/run/sweep"; mkdir -p "$STATEDIR" 2>/dev/null
SFILE="$STATEDIR/sweep-$KEY.state"
LAST="$(cat "$SFILE" 2>/dev/null)"; [ -n "$LAST" ] || LAST=0
CUR=$(( TOK / BUCKET_EVERY )); K=$(( TOK / 1000 ))
if [ "$CUR" -gt "$LAST" ]; then
  echo "$CUR" > "$SFILE" 2>/dev/null
  echo "[scratchpad] Context ~${K}k tokens deep — good point to /save and jump to a FRESH session (paste the /checkin <project> <plan> handoff it gives you). Reasoning frays as context fills; don't wait for auto-compact."
fi
exit 0
