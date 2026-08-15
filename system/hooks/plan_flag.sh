#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: The status-line HUD shows the active plan's name so a fresh window (post-/compact)
#      re-orients to which plan is live — the user's most-documented misstep. Registered as a
#      PreToolUse ExitPlanMode hook: it RECORDS the plan at approval-presentation; the status-line
#      reads it. FILE-based because env triggers don't survive tool calls (pm_flag pattern).
# GUARDS: ⛔ PLAN ARMING IS IMMUTABLE FOR THE LIFE OF A WINDOW (2026-08-15) — the PLAN half of
#         the same ruling pm_flag.sh already carries for PROJECTS. The FIRST well-formed arm in a
#         session writes lock-<key>.plan. After that: arming a DIFFERENT plan is REFUSED (nothing
#         written) and `clear` is REFUSED. Re-arming the SAME plan still refreshes normally — that
#         is the ordinary case (plan mode re-fires on every amendment, and /checkin re-arms on
#         every run), and it must never be mistaken for a change.
#         ⭐ EXACTLY TWO THINGS CHANGE IT: a NEW WINDOW, or THE HUMAN'S OWN WORDS in their own
#         prompt. There is NO override flag, argument or env var a session can set for itself — the
#         second path is not a flag. It is the human typing something like "switch the plan to
#         <name>" / "override the plan lock"; pm_persist.sh (UserPromptSubmit) is the only code in
#         this system that ever sees that raw prompt, and it writes override-<key>.grant. This
#         script CONSUMES that grant once and burns it. A model acting alone cannot author a
#         UserPromptSubmit prompt, so it cannot mint the token that unlocks it — which is the whole
#         point: if the model can set the thing that unlocks it, there is no lock.
#         ⭐ ONE GRANT TYPE, NOT TWO. The grant this reads is the SAME FILE pm_flag.sh reads, in the
#         SAME store, minted by the SAME hook against the SAME closed phrase list — which already
#         contains the plan forms ("switch the plan to …", "override the plan lock", "write to this
#         other plan"). That lane made the grant generic on purpose so this one could consume it.
#         A second grant type would be a second thing to keep honest and a second thing to forge.
#         KNOWN LIMITATION: fires when a plan is PRESENTED, so a rejected plan can show briefly until
#         the next real plan overwrites it or the 36h TTL ages it out — accepted (KISS, per the plan).
# REDIRECT: Flag ~/.claude/run/plan/plan-sess-<id>.flag · lock ~/.claude/run/plan/lock-<key>.plan
#         · human-word grant ~/.claude/run/pm/override-<key>.grant (written by pm_persist.sh,
#         single-use, burned here) · refusals ~/.claude/run/plan/plan-denied.log.
#         Reader: system/statusline.sh.
# SIGNPOST: the status bar that reads this flag is system/statusline.sh; the flag format is this file.
#         The ruling, the incident and the grant's design live in system/hooks/pm_flag.sh's header —
#         read that FIRST; this file is the same mechanism applied to plans.
# FAIL_POSTURE: closed for the LOCK (an unreadable or ambiguous lock state refuses the change rather
#         than allowing it); degrade-safe for everything else — a recorder that exits 0.
#         ⚠ ONE DELIBERATE FAIL-OPEN: if `record` cannot work out WHICH plan it was handed (an
#         unreadable payload, no planFilePath, no H1, no glob hit) it writes nothing AND refuses
#         nothing. We cannot say a plan differs from the armed one when we never learned what it
#         is, and refusing on no evidence would wall off plan mode on a payload glitch.
# ⚠ THE HOLE, SAID PLAINLY SO NOBODY OVER-TRUSTS THIS. `guard_pm_flag_store.sh` is a PreToolUse
#   guard over ~/.claude/run/pm/ — ~~it does NOT cover ~/.claude/run/plan/. So a session with a shell
#   can write plan-<key>.flag or delete lock-<key>.plan directly and skip this refusal entirely,~~
#   exactly as an audit proved for the pm store before that guard existed. That is stated, not
#   overlooked: ~~extending the guard is a one-line path-pattern change owned by that guard's lane,~~
#   and this file must not grow its own private copy of it. What stands here meanwhile is the same
#   thing that stands there — NOISE: every override prints a banner naming both plans on the
#   terminal the person is watching, and writes previous_plan + override_phrase into the lock file.
#   ⚠ CORRECTED 2026-08-15 — THE STRUCK TEXT ABOVE IS NO LONGER TRUE, AND IS KEPT AS THE RECORD OF
#   WHAT WAS. `guard_pm_flag_store.sh` was extended the same day and now names ~/.claude/run/plan/
#   alongside ~/.claude/run/pm/ at every one of its match sites: the Write/Edit/NotebookEdit target
#   check, the Bash path-BOUNDARY gate, and both interpreter tiers. Re-verified here by probe:
#   Write/Edit/NotebookEdit into the store, `rm` of lock-<key>.plan, a `>` redirect onto
#   plan-<key>.flag, and python3/node write calls all exit 2 — while a READ of the store, the
#   sibling run/plans-archive, and the sibling run/planner all still correctly exit 0.
#   ⛔ READ THAT AS "COVERED BY THE SAME SPEED BUMP", NEVER AS "PROTECTED". The guard matches TEXT;
#   it is not a wall, its own header says so, and the lane that extended it wrote the line refusing
#   to let the extension read as an upgrade: *every evasion listed in that header works identically
#   against `run/plan`*. Confirmed on the spot — that guard's own STATED LOSS, a destroy whose
#   target is only in a shell variable, still walks straight through to the plan store exactly as it
#   does to the pm store. So the ONLY thing that changed is that the plan store is now no worse off
#   than the project store; the honest posture for BOTH remains NOISE, below. The real fix — an OS
#   boundary with a store the agent cannot write as — is still deliberately deferred, not done.
#   The second half above stands unstruck and is still the rule: this file must NOT grow its own
#   private copy of that guard.
# UPDATED: 2026-08-15 (THE PLAN LOCK + THE HUMAN-WORD OVERRIDE — see GUARDS. The ruling has always
#           had two halves, "this other project OR this other plan"; only the project half was
#           built, so a plan could still be silently re-pointed mid-window. Built on the ONE channel
#           a model cannot write to: the raw UserPromptSubmit prompt, via the grant pm_persist.sh
#           already mints. Refusals and override banners print on stdout AND stderr — a refusal that
#           lands only on stderr is invisible to a caller running `2>/dev/null`, which is a guard
#           that scores PASS and protects nothing.)
# UPDATED: 2026-07-28 (record now uses tool_input.planFilePath - the harness-supplied path -
#           instead of the newest-mtime glob, which cross-wired across parallel windows)
# UPDATED: 2026-07-21 (added 'path': print the armed plan's file path, for /advisory-council auto-context)
# UPDATED: 2026-07-13 (added 'set <path>': RESUME-arm from an explicit path — /checkin & /read call it so a
#           resumed window shows its plan WITHOUT plan mode; explicit path avoids the newest-mtime trap 'record' can hit)
# ─────────────────────────────────────────────────────────────────────────────
#   plan_flag.sh record   # PreToolUse ExitPlanMode hook: read plan from stdin, write the marker
#                         # first arm LOCKS the window to that plan; a DIFFERENT plan is REFUSED
#                         # unless the human's own prompt authorised it this turn (then: once)
#   plan_flag.sh set <path>  # RESUME: arm the flag from an EXPLICIT plan-file path (no plan mode, never mtime)
#                            # same lock, same one legal override
#   plan_flag.sh status   # print active plan name | none
#   plan_flag.sh clear    # REFUSED once locked (new window, or the human's word). Deletes the
#                         # FLAG only — NEVER the lock.
#   plan_flag.sh locked   # print the locked plan, or "none" (read-only; CHECK before you arm)
# exit 0 = ok · 2 = REFUSED on the `record` hook path (2 is the harness's PreToolUse block code, so
#          the refusal actually stops the second plan being fired instead of leaving the session on
#          plan B while every reader still says plan A) · 3 = REFUSED on the CLI verbs `set`/`clear`
#          (3 is this repo's REFUSED-BY-THE-LOCK code, matching pm_flag.sh, whose callers are skills)
#          · 2 also = unknown verb, as before.
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
if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then
  KEY="sess-$CLAUDE_CODE_SESSION_ID"
  LOCKABLE=1
else
  KEY="cwd-$(hash_key "$PWD")"
  LOCKABLE=0   # two windows in one folder share this key — a lock here would refuse a legitimate
               # window. Same call pm_flag.sh made, for the same reason; keep them identical.
fi
FLAG="$FLAGDIR/plan-$KEY.flag"
LOCK="$FLAGDIR/lock-$KEY.plan"        # write-once; rewritten ONLY by a human-word override
DENYLOG="$FLAGDIR/plan-denied.log"    # refusals + authorised overrides, so "did this window ever
                                      # change plan, and who said so?" is answerable months later
NOW="$(date +%s 2>/dev/null)"
# ⭐ THE SAME GRANT FILE pm_flag.sh CONSUMES — one grant type in the system, not two. It is minted
# by pm_persist.sh from the human's raw prompt against a closed phrase list that ALREADY covers the
# plan wording, and it lives in the pm store because that store has a custodian guard. Do not mint a
# parallel plan-only grant: a second issuer is a second thing to keep honest and a second thing to forge.
GRANT="$HOME/.claude/run/pm/override-$KEY.grant"
_PLAN_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
# How long a grant stays consumable, in MINUTES — and it is NOT a second copy of that number.
# The env var is pm_flag.sh's own (PM_OVERRIDE_TTL_MIN), so setting it moves BOTH files at once; the
# default is READ OUT OF pm_flag.sh rather than re-typed here. A second literal is precisely how the
# 12h/36h TTL split sat dead across pm_flag.sh and pm_persist.sh for a month. The 30 below is a
# last-resort fallback for when pm_flag.sh cannot be found or read at all — it exists to fail toward
# the current correct value, not as a copy to remember to update. If the default changes, change it THERE.
_pm_override_ttl(){
  _t="$(sed -n 's/^OVERRIDE_TTL_MIN="\${PM_OVERRIDE_TTL_MIN:-\([0-9][0-9]*\)}".*/\1/p' "$_PLAN_HOOKDIR/pm_flag.sh" 2>/dev/null | head -1)"
  case "$_t" in (*[!0-9]*|'') _t=30 ;; esac
  printf '%s' "$_t"
}
OVERRIDE_TTL_MIN="${PM_OVERRIDE_TTL_MIN:-$(_pm_override_ttl)}"

# ── the lock ────────────────────────────────────────────────────────────────
# Prints "<locked_plan_file>\t<locked_name>" and returns 0 when this window is locked; 1 when free.
# NO logbook retro-fallback (pm_flag.sh has one because its logbook predates its lock file). There
# is no plan event log to fall back to, and inventing one to mirror the shape would be building a
# second mechanism to look symmetrical.
_locked_id(){
  [ "$LOCKABLE" = "1" ] || return 1
  [ -f "$LOCK" ] || return 1
  _lf="$(grep '^lock_plan_file=' "$LOCK" 2>/dev/null | head -1 | cut -d= -f2-)"
  _ln="$(grep '^lock_name=' "$LOCK" 2>/dev/null | head -1 | cut -d= -f2-)"
  [ -n "$_lf" ] || [ -n "$_ln" ] || return 1
  printf '%s\t%s\n' "$_lf" "$_ln"
  return 0
}

# IS THIS THE SAME PLAN? Two string-equality tests and nothing else — membership, never judgement.
# ⛔ It deliberately does NOT decide whether a plan "matches" in any looser sense. Making "the ingest
# plan" equal ingest-skill.plan.md is judgement wearing a regex, and it would refuse correct work.
# EITHER the file path OR the H1 name matching counts as the same plan, and that direction is chosen
# on purpose: plan mode re-fires on every amendment, and an amendment can legitimately move one of
# the two (a retitled H1 keeps the path; a `set` from /checkin may know the path when `record` only
# knew the name). Requiring BOTH would refuse the ordinary case, which is the failure that gets a
# guard routed around. The looseness costs a same-H1 collision across two files; the alternative
# costs every amendment.
_same_plan(){   # $1=locked_file $2=locked_name $3=req_file $4=req_name
  [ -n "$1" ] && [ "$1" = "$3" ] && return 0
  [ -n "$2" ] && [ "$2" = "$4" ] && return 0
  return 1
}

_deny_log(){ printf '%s\t%s\t%s\t%s\t%s\n' "${NOW:-0}" "$1" "$2" "$3" "$CLAUDE_CODE_SESSION_ID" >> "$DENYLOG" 2>/dev/null; }

# ── the human-word override ─────────────────────────────────────────────────
# ⭐ VERBATIM THE SAME CHECK pm_flag.sh RUNS, on the same file, deliberately — artifact (does the
# grant exist?), ownership (did THIS session's human speak it?) and timing (single-use, one turn).
# Nothing else. THE CRUX: the token that unlocks a window must be one a model acting alone CANNOT
# PRODUCE. Every flag, env var, argument or file a session can set fails that test — it would be the
# model authorising itself. Exactly one input to this system is written by the human and by nobody
# else: the text of their own prompt.
# Prints the human's verbatim words and returns 0 when a valid grant exists — and BURNS IT either
# way. SINGLE USE IS NOT A DETAIL: "the hook fires once and then the human can override" means one
# change per act of authorisation, never a session-long open door.
# ⛔ NOTE WHAT IS ABSENT: this does not read WHICH plan they named and does not check the arm against
# it. That comparison needs "the ingest plan" to equal a filename before it can run — judgement, not
# code. The grant is PERMISSION FOR ONE CHANGE; the banner below shouts the destination actually
# taken, on the terminal the person is looking at, which is what makes a wrong one visible.
# FAIL_POSTURE: closed. Anything unreadable, malformed, foreign-session or aged out returns 1, which
# lands on the ordinary refusal.
_consume_grant(){
  [ "$LOCKABLE" = "1" ] || return 1
  [ -f "$GRANT" ] || return 1
  _gs="$(grep '^session=' "$GRANT" 2>/dev/null | head -1 | cut -d= -f2-)"
  _gat="$(grep '^granted_at=' "$GRANT" 2>/dev/null | head -1 | cut -d= -f2-)"
  _gph="$(grep '^phrase=' "$GRANT" 2>/dev/null | head -1 | cut -d= -f2-)"
  # A grant is bound to the session whose prompt produced it. Without this, one window's
  # authorisation would unlock a different window that happened to read the same folder.
  [ -n "$CLAUDE_CODE_SESSION_ID" ] && [ "$_gs" = "$CLAUDE_CODE_SESSION_ID" ] || { rm -f "$GRANT" 2>/dev/null; return 1; }
  case "$_gat" in (*[!0-9]*|'') rm -f "$GRANT" 2>/dev/null; return 1;; esac
  [ -n "$NOW" ] || return 1
  _age=$(( NOW - _gat ))
  if [ "$_age" -lt 0 ] || [ "$_age" -ge $(( OVERRIDE_TTL_MIN * 60 )) ]; then rm -f "$GRANT" 2>/dev/null; return 1; fi
  rm -f "$GRANT" 2>/dev/null
  printf '%s' "${_gph:-(the words were not recorded)}"
  return 0
}

# LOUD, on BOTH channels, naming the old plan, the new one, and the human's exact words.
# ⛔ stdout AS WELL AS stderr, deliberately: a caller running this as `... 2>/dev/null` would
# otherwise see a silent success, and the human watching the terminal would see the armed plan change
# with nothing said about it. The one thing this must never be is quiet.
_announce_override(){   # $1=verb  $2=old  $3=new  $4=phrase
  {
    echo "⭐ PLAN LOCK OVERRIDDEN — BY THE HUMAN'S OWN WORDS, ONCE."
    echo "   was armed to: $2"
    case "$1" in
      plan)  echo "   now armed to: $3" ;;
      clear) echo "   now:          un-armed (the LOCK on '$2' REMAINS — see below)" ;;
    esac
    echo "   authorised by their prompt: \"$4\""
    echo "   The grant is BURNED. A further change needs them to say so again, or a new window."
    echo "   SAY THIS OUT LOUD IN YOUR REPLY: which plan you moved off, and which you moved to."
    echo "   If that is not what they meant, STOP and tell them — this window is now building from"
    echo "   a different plan, which is the exact failure this lock exists to prevent."
  } >&2
  echo "⭐ PLAN LOCK OVERRIDDEN by your words (\"$4\"): $2 -> ${3:-un-armed}. One change only."
}

# The deny message's job is to RE-TEACH the boundary, not merely wall it (hook-sop §4).
_refuse(){   # $1=verb  $2=locked_id  $3=locked_file  $4=requested
  # ⛔ COPY THE ARGUMENTS OUT FIRST — the body is a NESTED function so one text can go to two
  # channels without maintaining it twice, and inside it $1..$4 are ITS OWN arguments, not this
  # one's. Read positionally it prints an empty plan name and skips both `case` bodies: a refusal
  # that names nothing and teaches nothing. (That exact bug was caught in pm_flag.sh on 2026-08-15.)
  _RV="$1"; _ROLD="$2"; _RFILE="$3"; _RREQ="$4"
  _refusal_text(){
    echo "⛔ REFUSED — PLAN ARMING IS IMMUTABLE FOR THE LIFE OF THIS WINDOW."
    echo "   armed to:  $_ROLD"
    [ -n "$_RFILE" ] && [ "$_RFILE" != "$_ROLD" ] && echo "              $_RFILE"
    case "$_RV" in
      plan)  echo "   requested: $_RREQ" ;;
      clear) echo "   requested: clear (un-arm)" ;;
    esac
    echo "   NOTHING was written. This window is still building from: $_ROLD"
    echo
    echo "   WHY: firing a plan in a window FIXES that window to it. A session that re-points its"
    echo "        own plan mid-work leaves every reader — the status bar, /save's handoff,"
    echo "        /advisory-council's context — naming a plan the person never approved here, and"
    echo "        it cannot tell the human's intent from its own reading of the human's intent."
    echo "        So there is NO override flag, argument or env var you can set — by design."
    echo
    echo "   TWO THINGS CHANGE IT, AND YOU CANNOT DO EITHER ON YOUR OWN:"
    case "$_RV" in
      plan)
        echo "     1. A NEW WINDOW:  open one and plan there."
        echo "     2. THE HUMAN'S OWN WORDS, in their own next prompt — e.g."
        echo "          \"switch the plan to $_RREQ\"   or   \"override the plan lock\""
        echo "        Their prompt is the one input you cannot write. Saying it yourself, or"
        echo "        reporting that they said it, does nothing: the hook that reads their prompt"
        echo "        is what issues the grant. ⛔ Do NOT paraphrase this at them as a password to"
        echo "        recite — ASK whether they actually want this window's plan changed."
        echo "        Then re-run this exact command; it will allow ONE change and shout about it."
        ;;
      clear)
        echo "     1. Close the window. A finished plan does not need un-arming."
        echo "     2. The human saying so in their own prompt, e.g. \"override the plan lock\"."
        echo "        Even then the LOCK survives — clearing frees the flag, never the identity."
        ;;
    esac
    echo "   NOTE: READING another plan needs NO arming. Open the file."
  }
  # BOTH CHANNELS, DELIBERATELY. A refusal printed only to stderr is silent to any caller that runs
  # this as `... 2>/dev/null`, and a guard whose refusal lands where nobody reads scores a PASS while
  # protecting nothing. The exit code still carries the machine-readable answer.
  _refusal_text >&2
  _refusal_text
}

# THE GATE. Callers guarantee a non-empty identity before calling — `record` skips the write
# entirely when it learned no name (the deliberate fail-open in FAIL_POSTURE above), and `set`
# refuses an unreadable path before it gets here.
# Returns 0 to proceed (OVERRODE=1 when a grant was spent); otherwise refuses and EXITS.
_gate(){   # $1=verb(plan|clear)  $2=req_file  $3=req_name  $4=refuse_exit_code
  OVERRODE=0; GRANT_PHRASE=""; LOCKED_ID=""; LOCKED_FILE=""; LOCKED_NAME=""
  _lk="$(_locked_id)"
  [ -n "$_lk" ] || return 0
  LOCKED_FILE="${_lk%%$'\t'*}"; LOCKED_NAME="${_lk#*$'\t'}"
  LOCKED_ID="${LOCKED_NAME:-$LOCKED_FILE}"
  if [ "$1" != "clear" ] && _same_plan "$LOCKED_FILE" "$LOCKED_NAME" "$2" "$3"; then return 0; fi
  GRANT_PHRASE="$(_consume_grant)"
  if [ -n "$GRANT_PHRASE" ]; then
    OVERRODE=1
    _announce_override "$1" "$LOCKED_ID" "${3:-$2}" "$GRANT_PHRASE"
    _deny_log "$1-OVERRIDDEN-by-human" "$2" "$3"
    return 0
  fi
  _deny_log "$1-denied" "$2" "$3"
  _refuse "$1" "$LOCKED_ID" "$LOCKED_FILE" "${3:-$2}"
  exit "$4"
}

# ESTABLISH THE LOCK. First well-formed arm wins; an override is the ONE case that rewrites it —
# without that, the lock would still name the old plan while the flag names the new one, and every
# later check would refuse a change the human actually authorised.
_write_lock(){   # $1=plan_file  $2=name
  [ "$LOCKABLE" = "1" ] || return 0
  if [ ! -f "$LOCK" ] || [ "$OVERRODE" = "1" ]; then
    { echo "lock_plan_file=$1"; echo "lock_name=$2"; echo "locked_at=$NOW"
      if [ "$OVERRODE" = "1" ]; then
        echo "origin=human-override"; echo "previous_plan=$LOCKED_ID"; echo "override_phrase=$GRANT_PHRASE"
      else
        echo "origin=first-arm"
      fi
      echo "session=$CLAUDE_CODE_SESSION_ID"; } > "$LOCK" 2>/dev/null
  fi
  find "$FLAGDIR" -name 'lock-*.plan' -type f -mtime +30 -delete 2>/dev/null
}

# Control characters would corrupt the key=value lock and flag files — a newline in a name writes a
# second lock_name= line and poisons the identity. Strip before ANY state is touched.
_scrub(){ printf '%s' "$1" | LC_ALL=C tr -d '\000-\037\177' 2>/dev/null; }

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
    NAME="$(_scrub "${RESULT%%$'\t'*}")"
    PLAN_FILE="$(_scrub "${RESULT#*$'\t'}")"
    # THE FAIL-OPEN, and it is the declared one: no name means we never learned which plan this is,
    # so we can neither record it nor honestly say it differs from the armed one. Write nothing,
    # refuse nothing. Refusing on no evidence would wall off plan mode on a payload glitch.
    if [ -n "$NAME" ]; then
      # Exit 2 = the harness's PreToolUse BLOCK code. Chosen over a quiet non-blocking exit because
      # letting ExitPlanMode succeed while refusing to record it is the worse outcome: the session
      # then builds from plan B while the status bar, /save and /advisory-council all still say
      # plan A, and nothing anywhere reconciles them. Blocking keeps the window honest.
      _gate plan "$PLAN_FILE" "$NAME" 2
      { echo "name=$NAME"; echo "plan_file=$PLAN_FILE"; echo "armed_at=$NOW"; echo "session=$CLAUDE_CODE_SESSION_ID"; } > "$FLAG"
      _write_lock "$PLAN_FILE" "$NAME"
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
    NAME="$(_scrub "$NAME")"; SRC="$(_scrub "$SRC")"
    if [ -n "$NAME" ]; then
      # Exit 3 = this repo's REFUSED-BY-THE-LOCK code, matching pm_flag.sh — `set`'s callers are
      # skills (/checkin, /save), not the harness, so the harness's block code would say nothing to them.
      _gate plan "$SRC" "$NAME" 3
      { echo "name=$NAME"; echo "plan_file=$SRC"; echo "armed_at=$NOW"; echo "session=$CLAUDE_CODE_SESSION_ID"; } > "$FLAG"
      _write_lock "$SRC" "$NAME"
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
  locked)
    # Read-only: what plan is this window locked to? For skills that must CHECK before they arm.
    _lk="$(_locked_id)"
    if [ -n "$_lk" ]; then _n="${_lk#*$'\t'}"; _f="${_lk%%$'\t'*}"; echo "${_n:-$_f}"; else echo "none"; fi;;
  clear)
    _gate clear "" "" 3
    # ⛔ THE LOCK FILE IS NEVER DELETED HERE, AUTHORISED OR NOT, and that is what stops the obvious
    # two-step bypass: clear-then-arm-something-else. Clearing frees the FLAG (what this window is
    # currently building through); the LOCK is the window's identity, and identity does not become
    # negotiable because the work finished. After an authorised clear, arming a different plan still
    # costs a second, separate act of human authorisation.
    rm -f "$FLAG" 2>/dev/null
    if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then
      for f in "$FLAGDIR"/plan-*.flag; do [ -f "$f" ] || continue
        s="$(grep '^session=' "$f" 2>/dev/null | cut -d= -f2-)"
        [ "$s" = "$CLAUDE_CODE_SESSION_ID" ] && rm -f "$f" 2>/dev/null; done; fi
    echo "PLAN-CLEARED";;
  *) echo "usage: plan_flag.sh record | set <path> | status | path | locked | clear" >&2; exit 2;;
esac
exit 0
