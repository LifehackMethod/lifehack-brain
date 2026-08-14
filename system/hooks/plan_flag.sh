#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: The status-line HUD shows the active plan's name so a fresh window (post-/compact)
#      re-orients to which plan is live — the user's most-documented misstep. Registered as a
#      PreToolUse ExitPlanMode hook: it RECORDS the plan at approval-presentation; the status-line
#      reads it. FILE-based because env triggers don't survive tool calls (pm_flag pattern).
# GUARDS: None — a tiny state writer. NEVER blocks (always exit 0) so it can't stop plan approval.
#         KNOWN LIMITATION: fires when a plan is PRESENTED, so a rejected plan can show briefly until
#         the next real plan overwrites it or the 36h TTL ages it out — accepted (KISS, per the plan).
# REDIRECT: Flag ~/.claude/run/plan/plan-sess-<id>.flag. Reader: system/statusline.sh.
# SIGNPOST: the status bar that reads this flag is system/statusline.sh; the flag format is this file.
# FAIL_POSTURE: degrade-safe — a recorder, never a gate; on any error it exits 0 (never blocks planning).
# UPDATED: 2026-07-28 (record now uses tool_input.planFilePath - the harness-supplied path -
#           instead of the newest-mtime glob, which cross-wired across parallel windows)
# UPDATED: 2026-07-21 (added 'path': print the armed plan's file path, for /advisory-council auto-context)
# UPDATED: 2026-07-13 (added 'set <path>': RESUME-arm from an explicit path — /checkin & /read call it so a
#           resumed window shows its plan WITHOUT plan mode; explicit path avoids the newest-mtime trap 'record' can hit)
# ─────────────────────────────────────────────────────────────────────────────
#   plan_flag.sh record   # PreToolUse ExitPlanMode hook: read plan from stdin, write the marker
#   plan_flag.sh set <path>  # RESUME: arm the flag from an EXPLICIT plan-file path (no plan mode, never mtime)
#   plan_flag.sh status   # print active plan name | none
#   plan_flag.sh clear    # remove this session's plan marker
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
TTL_HOURS="${PLAN_TTL_HOURS:-36}"
FLAGDIR="$HOME/.claude/run/plan"; mkdir -p "$FLAGDIR" 2>/dev/null
if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then KEY="sess-$CLAUDE_CODE_SESSION_ID"
else KEY="cwd-$(hash_key "$PWD")"; fi
FLAG="$FLAGDIR/plan-$KEY.flag"
NOW="$(date +%s 2>/dev/null)"
case "$1" in
  record)
    INPUT=$(cat)
    RESULT=$(printf '%s' "$INPUT" | python3 -c '
import sys, json, re, glob, os
def h1(t):
    for line in (t or "").splitlines():
        m = re.match(r"\s{0,3}#\s+(.+)", line)
        if m: return m.group(1).strip()
    return ""
try: d = json.load(sys.stdin)
except Exception: d = None
# `null`, `[]`, `"str"` and `5` are all VALID JSON that are NOT objects, so json.load returns them
# happily and the except above never fires - then .get() raises AttributeError. The traceback goes
# to /dev/null (see the 2>/dev/null closing this block), RESULT comes back empty, and the flag is
# simply never written. Nothing anywhere says so.
#
# ⚠ The cost is NOT a blocked tool call - the record branch exits 0 regardless, verified. The cost
# is that the crash lands BEFORE the resolution below, so the branch never runs at all.
HAVE_PAYLOAD = isinstance(d, dict)
if not HAVE_PAYLOAD: d = {}
ti = d.get("tool_input") or {}
if not isinstance(ti, dict): ti = {}
name = h1(ti.get("plan", ""))
# PRIMARY: the harness hands us the exact plan file on ExitPlanMode (planFilePath).
# The newest-mtime glob below is a LAST-RESORT fallback only - it cross-wires across
# parallel plan-mode windows (build-sop 2026-07-13). That cross-wire is the bug this fixes.
target = (ti.get("planFilePath") or "").strip()
if target:
    target = os.path.expanduser(target)
# ⛔ HAVE_PAYLOAD gates the glob deliberately. A payload that is not an object told us NOTHING, and
# the glob is the known-hazardous route - it cross-wires parallel plan-mode windows (build-sop
# 2026-07-13), which is why it is last-resort even on a good payload. Reaching for it on a payload we
# could not read would arm a plan the person never pointed at, silently, and a wrong plan marker is
# worse than none: it is indistinguishable from a right one. An object with no planFilePath still
# reaches the glob exactly as before - only unreadable input is refused.
if not target and HAVE_PAYLOAD:
    # CLAUDE_CONFIG_DIR moves the whole harness folder. A bare ~/.claude here finds nothing when it
    # is set, and finding nothing is indistinguishable from having no plans -- so the flag is simply
    # never written and nothing says why. Same pattern as agent_output.py:59-60.
    _cfg = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    files = sorted(glob.glob(os.path.join(_cfg, "plans", "*.md")), key=os.path.getmtime, reverse=True)
    target = files[0] if files else ""
if not name and target:
    try: name = h1(open(target, encoding="utf-8").read())
    except Exception: pass
if not name and target:
    name = os.path.basename(target)[:-3]
print((name or "") + "\t" + target)
' 2>/dev/null)
    NAME="${RESULT%%$'\t'*}"
    PLAN_FILE="${RESULT#*$'\t'}"
    if [ -n "$NAME" ]; then
      { echo "name=$NAME"; echo "plan_file=$PLAN_FILE"; echo "armed_at=$NOW"; echo "session=$CLAUDE_CODE_SESSION_ID"; } > "$FLAG"
    fi
    exit 0;;
  set)
    # RESUME arm: write THIS session's plan marker from an EXPLICIT file path — used by /checkin and
    # /read when they resolve a project's linked plan, so a resumed window shows its plan WITHOUT plan
    # mode. Explicit path => never the newest-mtime mis-fire 'record' can hit across parallel windows.
    SRC="$2"
    if [ -z "$SRC" ] || [ ! -f "$SRC" ]; then echo "set: a readable plan-file path is required" >&2; exit 0; fi
    NAME=$(printf '%s' "$SRC" | python3 -c '
import sys, re, os
p = sys.stdin.read().strip()
name = ""
try:
    for line in open(p, encoding="utf-8"):
        m = re.match(r"\s{0,3}#\s+(.+)", line)
        if m:
            name = m.group(1).strip(); break
except Exception:
    pass
if not name:
    name = os.path.basename(p)[:-3]
print(name)
' 2>/dev/null)
    if [ -n "$NAME" ]; then
      { echo "name=$NAME"; echo "plan_file=$SRC"; echo "armed_at=$NOW"; echo "session=$CLAUDE_CODE_SESSION_ID"; } > "$FLAG"
      echo "PLAN-SET: $NAME -> $SRC"
    else
      echo "set: could not derive a name from $SRC" >&2
    fi
    exit 0;;
  status)
    if [ -f "$FLAG" ]; then
      NM="$(grep '^name=' "$FLAG" 2>/dev/null | cut -d= -f2-)"
      AT="$(grep '^armed_at=' "$FLAG" 2>/dev/null | cut -d= -f2-)"
      if [ -n "$AT" ] && [ -n "$NOW" ] && [ $(( NOW - AT )) -ge $(( TTL_HOURS * 3600 )) ]; then rm -f "$FLAG"; echo "none"
      elif [ -z "$NM" ]; then echo "none"
      else echo "$NM"; fi
    else echo "none"; fi;;
  path)
    # print the armed plan's FILE PATH (status prints the name); same TTL check.
    # Consumed by /advisory-council to READ the active plan as advisory context.
    if [ -f "$FLAG" ]; then
      PF="$(grep '^plan_file=' "$FLAG" 2>/dev/null | cut -d= -f2-)"
      AT="$(grep '^armed_at=' "$FLAG" 2>/dev/null | cut -d= -f2-)"
      if [ -n "$AT" ] && [ -n "$NOW" ] && [ $(( NOW - AT )) -ge $(( TTL_HOURS * 3600 )) ]; then rm -f "$FLAG"; echo "none"
      elif [ -z "$PF" ]; then echo "none"
      else echo "$PF"; fi
    else echo "none"; fi;;
  clear)
    rm -f "$FLAG" 2>/dev/null
    if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then
      for f in "$FLAGDIR"/plan-*.flag; do [ -f "$f" ] || continue
        s="$(grep '^session=' "$f" 2>/dev/null | cut -d= -f2-)"
        [ "$s" = "$CLAUDE_CODE_SESSION_ID" ] && rm -f "$f" 2>/dev/null; done; fi
    echo "PLAN-CLEARED";;
  *) echo "usage: plan_flag.sh record | set <path> | status | path | clear" >&2; exit 2;;
esac
exit 0
