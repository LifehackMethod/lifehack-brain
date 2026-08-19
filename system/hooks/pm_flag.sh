#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: Shared on/off switch for project-manager persistence. /project-manager
#      ARMS it; /read re-arms on rehydrate. The pm_persist.sh UserPromptSubmit
#      hook reads the flag this writes.
# GUARDS: ⛔ PROJECT ARMING IS IMMUTABLE FOR THE LIFE OF A WINDOW (2026-08-06).
#         The FIRST well-formed `arm` in a session writes lock-<key>.project. After
#         that: `arm` with a DIFFERENT slug is REFUSED (exit 3, nothing written) and
#         `clear` is REFUSED (exit 3). Same-slug `arm` still refreshes normally (TTL
#         refresh + /save's recovery path both depend on it).
#         ⭐ EXACTLY TWO THINGS CHANGE IT (2026-08-15): a NEW WINDOW, or THE HUMAN'S
#         OWN WORDS in their own prompt. There is still NO override flag a session can
#         set for itself — the second path is not a flag. It is the human typing, in
#         their prompt, something like "switch the project to <slug>" / "override the
#         project lock"; pm_persist.sh (UserPromptSubmit) is the only code here that
#         ever sees that raw prompt, and it writes override-<key>.grant. This script
#         CONSUMES that grant once and burns it. A model acting alone cannot author a
#         UserPromptSubmit prompt, so it cannot mint the token that unlocks it — which
#         is the whole point: if the model can set the thing that unlocks it, there is
#         no lock.
#         Flag remains SESSION-scoped + machine-local (CLAUDE_CODE_SESSION_ID; cwd-hash
#         fallback). The cwd-hash fallback is deliberately NOT lockable — two windows in
#         one folder share that key, and a lock there would refuse a legitimate window.
#         arm still requires a doc_path; status self-expires stale flags.
# REDIRECT: Flag ~/.claude/run/pm/pm-<key>.flag · lock ~/.claude/run/pm/lock-<key>.project
#           · human-word grant ~/.claude/run/pm/override-<key>.grant (written by pm_persist.sh,
#           single-use, burned here) · audit ~/.claude/run/pm/arm-events.log · refusals
#           ~/.claude/run/pm/arm-denied.log.
#           Hook: pm_persist.sh. Recovery tool: system/tools/pm_flag_recover.py.
# FAIL_POSTURE: closed for the LOCK (an unreadable/ambiguous lock state refuses the
#           change rather than allowing it); degrade-safe for everything else.
# WHY THE LOCK EXISTS: on 2026-08-06 a session re-armed its own window from
#   `ingest-skill` to `skill-builder` on its own judgment, mid-conversation, while
#   following /checkin Step 0's instruction to "arm the flag once the project is
#   resolved." Two /save handoffs were emitted pointing at the wrong project and the
#   wrong brief's human-authored FRAME block was edited. It recurred the same evening
#   in a second window. Prose could not stop it; this can.
# UPDATED: 2026-08-15 (THE HUMAN-WORD OVERRIDE. The 2026-08-06 note below says "there is NO
#           override flag and there never will be" — that stands, and this is not one. The ruling
#           it was built to (the owner, authority: user) has TWO legal ways to change an armed
#           project: a new window, OR the human saying so explicitly in the moment. Only the first
#           was built, so a human who said "write to this other project" was told to open a new
#           window — the lock was one half of the ruling, not the whole of it. Built the second
#           half on the ONE channel a model cannot write to: the raw UserPromptSubmit prompt.
#           pm_persist.sh reads it, and only it, and issues override-<key>.grant; this file burns
#           the grant on first use and shouts what it did on stdout AND stderr. Refusals now print
#           on both channels too — a refusal that lands only on stderr is invisible to a caller
#           that redirects it, which is a guard that scores PASS and protects nothing.)
# UPDATED: 2026-08-06 (THE LOCK: immutable project arming per window; refusals logged
#           to arm-denied.log, deliberately NOT arm-events.log — pm_flag_recover.py reads
#           the LAST event there and would otherwise report a DENIED project as recoverable)
# UPDATED: 2026-07-11 (TTL 12h->36h; arm-events.log breadcrumb on arm/clear; prune-on-write caps it at PM_EVENTLOG_MAX=500)
# UPDATED: 2026-08-14 (added the read-only `ttl` verb below. FOUND: the 2026-07-11 bump above
#           only ever landed HERE — pm_persist.sh's UserPromptSubmit hook carried its own
#           independent copy of the same default, still at 12h, and its every-turn expiry
#           check runs far more often than anything that would have read this file's value, so
#           it always won: the 36h extension had never once taken effect. Fix: pm_persist.sh no
#           longer carries its own literal — it calls this verb for the default, so this file's
#           TTL_HOURS is the ONLY place that number is defined.)
# ─────────────────────────────────────────────────────────────────────────────
#   pm_flag.sh arm  <abs_doc_path> <slug> <desk>   # first arm LOCKS the window to <slug>
#                                                  # a DIFFERENT slug is REFUSED unless the human's
#                                                  # own prompt authorised it this turn (then: once)
#   pm_flag.sh clear                               # REFUSED once locked (new window, or the human's
#                                                  # word). Deletes the FLAG only — NEVER the lock.
#   pm_flag.sh status                              # print active doc or "none"
#   pm_flag.sh locked                              # print the locked slug, or "none"
#   pm_flag.sh ttl                                 # print TTL_HOURS (read-only; the single
#                                                   # source pm_persist.sh reads its default from)
# exit 0 = ok · 1 = usage/arg error · 2 = unknown verb · 3 = REFUSED BY THE LOCK
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
TTL_HOURS="${PM_TTL_HOURS:-36}"
FLAGDIR="$HOME/.claude/run/pm"; mkdir -p "$FLAGDIR" 2>/dev/null
if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then
  KEY="sess-$CLAUDE_CODE_SESSION_ID"
  LOCKABLE=1
else
  KEY="cwd-$(hash_key "$PWD")"
  LOCKABLE=0   # two windows in one folder share this key — a lock here would misfire
fi
FLAG="$FLAGDIR/pm-$KEY.flag"
LOCK="$FLAGDIR/lock-$KEY.project"     # write-once, rewritten ONLY by a human-word override — the window's identity
EVENTLOG="$FLAGDIR/arm-events.log"    # durable append-only breadcrumb (survives flag TTL); read by pm_flag_recover.py
DENYLOG="$FLAGDIR/arm-denied.log"     # refusals ONLY — kept out of EVENTLOG so recovery can't read a denial as an arm
GRANT="$FLAGDIR/override-$KEY.grant"  # the human's word, written by pm_persist.sh from the raw prompt; single-use
NOW="$(date +%s 2>/dev/null)"
# How long a human-word grant stays consumable, in MINUTES. THE TIGHT BOUND IS NOT THIS ONE:
# pm_persist.sh deletes the grant on the very next human prompt that does not re-authorise, so in
# practice it lives for exactly one turn. This is only the backstop for a window that goes idle
# mid-turn (the human authorises, the session stalls, someone returns hours later). Defined HERE
# and nowhere else — the 12h/36h TTL split that sat dead in these two files for a month is the
# reason a second copy of any number in this pair is a bug, not a convenience.
OVERRIDE_TTL_MIN="${PM_OVERRIDE_TTL_MIN:-30}"

# ── the lock ────────────────────────────────────────────────────────────────
# Prints "<locked_id>\t<locked_doc>\t<origin>" and returns 0 when this window is
# locked; returns 1 when it is free. locked_id is the SLUG (paths legitimately move
# under a v2 folder migration; the slug is the identity), falling back to the doc_path
# when a slug was never recorded.
_locked_id(){
  [ "$LOCKABLE" = "1" ] || return 1
  local ls ld lid line lsl ldc
  if [ -f "$LOCK" ]; then
    ls="$(grep '^lock_slug=' "$LOCK" 2>/dev/null | cut -d= -f2-)"
    ld="$(grep '^lock_doc=' "$LOCK" 2>/dev/null | cut -d= -f2-)"
    lid="${ls:-$ld}"
    if [ -n "$lid" ]; then printf '%s\t%s\t%s\n' "$lid" "$ld" "lockfile"; return 0; fi
  fi
  # RETRO-FALLBACK: the FIRST arm this session ever logged. The logbook predates the
  # lock file, so this is what protects windows that were ALREADY OPEN when the lock
  # shipped — they get locked to whatever they armed first, with no re-arm needed.
  if [ -f "$EVENTLOG" ]; then
    # Same WELL-FORMEDNESS filter as the lock file below ($4 = slug non-empty, $3 = doc_path
    # absolute). Without it the fallback re-introduces exactly what the lock file avoids: a
    # malformed arm (the arg-order slip, or a relative path) would lock the window to a broken
    # identity that the corrective arm can then never match, bricking the window for its life.
    # Caught by pm_hooks_test.sh T4 + L16 on 2026-08-06.
    line="$(awk -F'\t' -v s="$CLAUDE_CODE_SESSION_ID" '$2=="arm" && $6==s && $4!="" && $3 ~ /^\// {print $4 "\t" $3; exit}' "$EVENTLOG" 2>/dev/null)"
    if [ -n "$line" ]; then
      lsl="${line%%$'\t'*}"; ldc="${line#*$'\t'}"; lid="${lsl:-$ldc}"
      if [ -n "$lid" ]; then printf '%s\t%s\t%s\n' "$lid" "$ldc" "logbook"; return 0; fi
    fi
  fi
  return 1
}

_deny_log(){ printf '%s\t%s\t%s\t%s\t%s\n' "${NOW:-0}" "$1" "$2" "$3" "$CLAUDE_CODE_SESSION_ID" >> "$DENYLOG" 2>/dev/null; }

# ── the human-word override ─────────────────────────────────────────────────
# THE CRUX OF THE WHOLE DESIGN: the token that unlocks a window must be one a model acting
# alone CANNOT PRODUCE. Every flag, env var, argument or file a session can set fails that
# test — it would be the model authorising itself, which is not a human gate (that is what
# the 2026-08-06 note means by "there is NO override flag"). Exactly one input to this system
# is written by the human and by nobody else: the text of their own prompt. pm_persist.sh runs
# on UserPromptSubmit, is handed that raw text, matches it against a narrow closed list of
# explicit phrases, and writes override-<key>.grant. Nothing else writes that file.
#
# Prints the human's verbatim words and returns 0 when a valid grant exists — and BURNS IT
# either way. SINGLE USE IS NOT A DETAIL: "the hook fires once and then the human can override"
# means one change per act of authorisation, never a session-long open door.
# FAIL_POSTURE: closed. Anything unreadable, malformed, foreign-session or aged out returns 1,
# which lands on the ordinary refusal.
_consume_grant(){
  [ "$LOCKABLE" = "1" ] || return 1
  [ -f "$GRANT" ] || return 1
  local gs gat gph age
  gs="$(grep '^session=' "$GRANT" 2>/dev/null | head -1 | cut -d= -f2-)"
  gat="$(grep '^granted_at=' "$GRANT" 2>/dev/null | head -1 | cut -d= -f2-)"
  gph="$(grep '^phrase=' "$GRANT" 2>/dev/null | head -1 | cut -d= -f2-)"
  # A grant is bound to the session whose prompt produced it. Without this, one window's
  # authorisation would unlock a different window that happened to read the same folder.
  [ -n "$CLAUDE_CODE_SESSION_ID" ] && [ "$gs" = "$CLAUDE_CODE_SESSION_ID" ] || { rm -f "$GRANT" 2>/dev/null; return 1; }
  case "$gat" in (*[!0-9]*|'') rm -f "$GRANT" 2>/dev/null; return 1;; esac
  [ -n "$NOW" ] || return 1
  age=$(( NOW - gat ))
  if [ "$age" -lt 0 ] || [ "$age" -ge $(( OVERRIDE_TTL_MIN * 60 )) ]; then rm -f "$GRANT" 2>/dev/null; return 1; fi
  rm -f "$GRANT" 2>/dev/null
  printf '%s' "${gph:-(the words were not recorded)}"
  return 0
}

# LOUD, on BOTH channels, naming the old project, the new one, and the human's exact words.
# ⛔ stdout AS WELL AS stderr, deliberately: a caller that runs this as `... 2>/dev/null` would
# otherwise see a silent success, and the human watching the terminal would see a project change
# with nothing said about it. The one thing this must never be is quiet.
_announce_override(){   # $1=verb  $2=old_id  $3=new_id  $4=phrase
  {
    echo "⭐ PROJECT LOCK OVERRIDDEN — BY THE HUMAN'S OWN WORDS, ONCE."
    echo "   was armed to: $2"
    case "$1" in
      arm)   echo "   now armed to: $3" ;;
      clear) echo "   now:          un-armed (the LOCK on '$2' REMAINS — see below)" ;;
    esac
    echo "   authorised by their prompt: \"$4\""
    echo "   The grant is BURNED. A further change needs them to say so again, or a new window."
    echo "   SAY THIS OUT LOUD IN YOUR REPLY: which project you moved off, and which you moved to."
    echo "   If that is not what they meant, STOP and tell them — you have just written to a"
    echo "   different project's brief, which is the exact failure this lock exists to prevent."
  } >&2
  {
    echo "⭐ PROJECT LOCK OVERRIDDEN by your words (\"$4\"): $2 -> ${3:-un-armed}. One change only."
  }
}

# The deny message's job is to RE-TEACH the boundary, not merely wall it (hook-sop §4).
_refuse(){   # $1=verb  $2=locked_id  $3=locked_doc  $4=requested_id
  # ⛔ COPY THE ARGUMENTS OUT FIRST. The body below is a NESTED function so the same text can be
  # sent to two channels without maintaining it twice — and inside it, $1..$4 are ITS OWN
  # arguments, not this one's. Read positionally, the message printed an empty project name, an
  # empty requested name, and skipped both `case` bodies entirely — a refusal that named nothing
  # and taught nothing, which is the failure mode this file exists to avoid. Caught by
  # test_pm_lock_override.sh on the first run, 2026-08-15.
  _RV="$1"; _ROLD="$2"; _RDOC="$3"; _RREQ="$4"
  _refusal_text(){
    echo "⛔ REFUSED — PROJECT ARMING IS IMMUTABLE FOR THE LIFE OF THIS WINDOW."
    echo "   armed to:  $_ROLD"
    # Show the LIVE doc_path when the flag is readable; the lock file records the doc as
    # it was at FIRST arm and a v2 folder migration legitimately moves it. A deny message
    # that names a stale path misroutes the reader (hook-sop §4: a wrong redirect is worse
    # than no redirect).
    _livedoc="$(grep '^doc_path=' "$FLAG" 2>/dev/null | cut -d= -f2-)"
    _showdoc="${_livedoc:-$_RDOC}"
    [ -n "$_showdoc" ] && echo "              $_showdoc"
    case "$_RV" in
      arm)   echo "   requested: $_RREQ" ;;
      clear) echo "   requested: clear (un-arm)" ;;
    esac
    echo "   NOTHING was written. The flag still points at: $_ROLD"
    [ -n "$_MALFORMED_NOTE" ] && echo "$_MALFORMED_NOTE"
    echo
    echo "   WHY: on 2026-08-06 a session re-armed its own window on its own judgment and"
    echo "        emitted two /save handoffs pointing at the wrong project. A session cannot"
    echo "        tell the human's intent from its own reading of the human's intent, so"
    echo "        there is NO override flag, argument or env var you can set — by design."
    echo
    echo "   TWO THINGS CHANGE IT, AND YOU CANNOT DO EITHER ON YOUR OWN:"
    case "$_RV" in
      arm)
        echo "     1. A NEW WINDOW:  open one and run  /checkin $_RREQ"
        echo "     2. THE HUMAN'S OWN WORDS, in their own next prompt — e.g."
        echo "          \"switch the project to $_RREQ\"   or   \"override the project lock\""
        echo "        Their prompt is the one input you cannot write. Saying it yourself, or"
        echo "        reporting that they said it, does nothing: the hook that reads their"
        echo "        prompt is what issues the grant. ⛔ Do NOT paraphrase this at them as a"
        echo "        password to recite — ASK whether they actually want the project changed."
        echo "        Then re-run this exact command; it will allow ONE change and shout about it."
        ;;
      clear)
        echo "     1. Close the window. A finished project does not need un-arming."
        echo "     2. The human saying so in their own prompt, e.g. \"override the project lock\"."
        echo "        Even then the LOCK survives — clearing frees the flag, never the identity."
        ;;
    esac
    echo "   NOTE: READING another project's brief or plan needs NO arming. Open the file."
  }
  # BOTH CHANNELS, DELIBERATELY. A refusal printed only to stderr is silent to any caller that
  # runs this as `... 2>/dev/null`, and a guard whose refusal lands where nobody reads scores a
  # PASS while protecting nothing. Exit 3 still carries the machine-readable answer.
  _refusal_text >&2
  _refusal_text
}

case "$1" in
  arm)
    if [ -z "$2" ]; then echo "arm: doc_path required (absolute path)" >&2; exit 1; fi
    # Control characters (newline / tab / CR) would corrupt the TSV logbook AND the key=value
    # lock file — a newline in the slug writes a second lock_slug= line and poisons the identity.
    # Reject before ANY state is touched. (Audit finding #5, 2026-08-06.)
    # NB: use ANSI-C quoting. `$(printf '\n')` is WRONG here — command substitution strips the
    # trailing newline, so the pattern collapses to *""* and matches EVERY input. That mistake
    # made this check reject all arms and was caught only by re-running the repros.
    case "$2$3$4" in
      *$'\n'*|*$'\t'*|*$'\r'*)
        echo "arm: doc_path/slug/desk may not contain newlines, tabs or carriage returns" >&2; exit 1;;
    esac
    REQ_ID="${3:-$2}"

    # ATOMIC MUTEX around check-then-write. Without it, two concurrent arms with DIFFERENT slugs
    # on a not-yet-locked window BOTH succeed and split-brain: the flag ends up on one project
    # and the lock on the other, so the visible context and every future lock check disagree.
    # `mkdir` is the atomic POSIX primitive. Bounded wait, then proceed rather than deadlock —
    # a stuck mutex must never make arming impossible. (Audit finding #4, 2026-08-06.)
    MUTEX="$FLAGDIR/.arm-mutex.d"
    _held=0
    for _i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
      if mkdir "$MUTEX" 2>/dev/null; then _held=1; break; fi
      # reap a mutex orphaned by a killed process (older than 30s)
      if [ -n "$(find "$MUTEX" -maxdepth 0 -type d -mmin +0.5 2>/dev/null)" ]; then rmdir "$MUTEX" 2>/dev/null; fi
      sleep 0.05
    done
    [ "$_held" = "1" ] && trap 'rmdir "$MUTEX" 2>/dev/null' EXIT
    LOCKED_ID=""; LOCKED_DOC=""; OVERRODE=0; GRANT_PHRASE=""; _MALFORMED_NOTE=""
    LK="$(_locked_id)"
    if [ -n "$LK" ]; then
      LOCKED_ID="${LK%%$'\t'*}"; _rest="${LK#*$'\t'}"; LOCKED_DOC="${_rest%%$'\t'*}"
      if [ "$REQ_ID" != "$LOCKED_ID" ]; then
        # WELL-FORMEDNESS IS CHECKED BEFORE THE GRANT IS TOUCHED, and that order is the point.
        # An override rewrites the lock; a malformed arm (the known arg-order slip — a bare slug
        # in the doc_path slot) would rewrite it to a broken identity, and the human's one
        # authorisation would be spent on it. Refusing here leaves the grant unburned, so the
        # corrected command still works inside the same turn. Same well-formedness test the
        # first-arm lock uses below — deliberately, so the two can never disagree.
        if [ -z "$3" ] || [ "${2#/}" = "$2" ]; then
          _MALFORMED_NOTE="   ⚠ AND THIS COMMAND IS MALFORMED: arm needs <ABSOLUTE doc_path> <slug> <desk>.
      Even with the human's word this would be refused — an override may not install a
      broken identity. Fix the arguments first. (No authorisation was spent.)"
        else
          GRANT_PHRASE="$(_consume_grant)"
        fi
        if [ -n "$GRANT_PHRASE" ]; then
          OVERRODE=1
          _announce_override arm "$LOCKED_ID" "$REQ_ID" "$GRANT_PHRASE"
          # The override goes in the DENY log as well as the event log. That log is what someone
          # reads when asking "did this window ever change project, and who said so?" — and the
          # answer must not live only in the log that records ordinary arms.
          _deny_log "arm-OVERRIDDEN-by-human" "$2" "$REQ_ID"
        else
          _deny_log "arm-denied" "$2" "$REQ_ID"
          _refuse arm "$LOCKED_ID" "$LOCKED_DOC" "$REQ_ID"
          exit 3
        fi
      fi
    fi
    # PAD FINGERPRINT AT ARM (W11.1c, 2026-08-08) -- the mechanical answer to "did THIS window do the
    # work?", replacing a self-assessed PICKUP/CLOSE mode. Compaction may graduate pad content into an
    # APPEND-ONLY Story Log, and a window that did not write the notes cannot correctly sort them
    # (ruled 2026-08-06). Later: sha(pad now) == pad_sha_at_arm => this window wrote NOTHING => DO NOT
    # COMPACT. Differs => this window wrote => compaction is safe.
    # FAIL_POSTURE: closed-by-absence. Any failure here writes NO line, and a MISSING pad_sha_at_arm
    # means "do not compact" -- never an error, never a licence. An un-armed or legacy window is exactly
    # the blind case this exists to stop, so the safe answer and the failure answer are the same answer.
    # MUST reuse pad_archive.py's OWN extract_scratchpad()+sha(): the later comparison is computed there,
    # and two different definitions of "the pad" would never match.
    # FIRST ARM WINS -- NEVER RE-STAMP ON A RE-ARM (2026-08-08, found on the FIRST live run of
    # Step 1.8, in a second window). /checkin Step 0 instructs an arm/refresh on EVERY run. If that
    # re-stamped the fingerprint, the baseline would move to the pad's CURRENT contents -- erasing
    # the evidence that this window wrote earlier -- and Gate 2 would then read "this window wrote
    # nothing" and REFUSE to compact a session that legitimately should. The gate would defeat
    # itself on any window that ran /checkin twice.
    # Same shape as the project lock directly above: the FIRST well-formed value is the identity,
    # and a re-arm refreshes everything EXCEPT it. A baseline you can re-take on demand is not a
    # baseline.
    # ⭐ EXCEPT ON AN OVERRIDE (2026-08-15). "First arm wins" is scoped to ONE project's pad. A
    # human-word override points this window at a DIFFERENT brief, so the carried-over sha is the
    # fingerprint of a pad that is no longer the armed one — the later comparison would read
    # "differs" every time and hand out a licence to compact notes this window never wrote, which
    # is precisely the blindness the fingerprint exists to stop. A new project gets a new baseline.
    if [ "$OVERRODE" = "1" ]; then _EXISTING_PAD_SHA=""; else
    _EXISTING_PAD_SHA="$(grep '^pad_sha_at_arm=' "$FLAG" 2>/dev/null | cut -d= -f2-)"; fi
    # Where pad_archive.py lives, resolved FROM THIS SCRIPT -- never a hardcoded home dir, never $PWD.
    # A hook runs with the CALLER's working directory, which is the person's project folder, so a bare
    # `git rev-parse` would answer for THAT repo, not this one. Anchoring it at the hook's own path is
    # what makes it repo-relative. The trim fallback covers a clone with no git available (a downloaded
    # ZIP, or git off PATH). Plain $0, not BASH_SOURCE: this file has to parse under dash too.
    _PM_HOOKDIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
    _PM_REPO="$(cd "$_PM_HOOKDIR" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)"
    [ -n "$_PM_REPO" ] || _PM_REPO="${_PM_HOOKDIR%/system/hooks}"
    # Silent-degrade on ANY failure is DELIBERATE: no pad module, or a brief with no scratchpad,
    # means no fingerprint line, which the writer below already treats as "armed without one".
    # (pad_archive.py landed at system/tools/save/ in T1.2, merged with section_archive.py.)
    PAD_SHA="$(python3 - "$2" "$_PM_REPO/system/tools/save" 2>/dev/null <<'_PADSHA_EOF'
import sys, os
sys.path.insert(0, sys.argv[2])
try:
    import pad_archive as pa
    pad = pa.extract_scratchpad(open(sys.argv[1], encoding="utf-8").read())
    if pad is not None:
        sys.stdout.write(pa.sha(pad))
except Exception:
    pass
_PADSHA_EOF
)"
    { echo "doc_path=$2"; echo "slug=$3"; echo "desk=$4"; echo "armed_at=$NOW"; echo "cwd=$PWD"; echo "session=$CLAUDE_CODE_SESSION_ID"; \
      if [ ${#_EXISTING_PAD_SHA} -eq 64 ]; then echo "pad_sha_at_arm=$_EXISTING_PAD_SHA";
      elif [ ${#PAD_SHA} -eq 64 ]; then case "$PAD_SHA" in *[!0-9a-f]*) ;; *) echo "pad_sha_at_arm=$PAD_SHA" ;; esac; fi; } > "$FLAG" 2>/dev/null
    # Never print ARMED on a write that did not happen. A session id containing "/" (or an
    # unwritable flag dir) made every write fail while the script still reported success and
    # exit 0 — a green illusion, and inconsistent with the declared FAIL_POSTURE.
    # (Audit finding #6, 2026-08-06.)
    if [ ! -s "$FLAG" ]; then
      echo "arm: FAILED to write the flag at $FLAG — nothing is armed" >&2; exit 1
    fi
    printf '%s\tarm\t%s\t%s\t%s\t%s\n' "${NOW:-0}" "$2" "$3" "$4" "$CLAUDE_CODE_SESSION_ID" >> "$EVENTLOG" 2>/dev/null
    # THE ARTIFACT. A second, differently-verbed line so the question "did a human ever move this
    # window off its first project, and what did they say?" is answerable from the logbook alone,
    # months later. Verb is `arm-override`, NOT `arm`: _locked_id's retro-fallback matches $2=="arm"
    # and takes the FIRST such line, and an override line answering to that filter would let a
    # pruned-away lock file resurrect the wrong identity.
    [ "$OVERRODE" = "1" ] && printf '%s\tarm-override\t%s\t%s\t%s\t%s\t%s\n' "${NOW:-0}" "$2" "$3" "$LOCKED_ID" "$CLAUDE_CODE_SESSION_ID" "$GRANT_PHRASE" >> "$EVENTLOG" 2>/dev/null
    # ESTABLISH THE LOCK. A malformed arm (the known arg-order slip: a bare slug in the
    # doc_path slot) must NOT lock the window to a broken identity — it would leave the
    # window unable to re-arm correctly. So only an ABSOLUTE doc_path + a non-empty slug
    # establishes a lock; anything else writes the flag as before and leaves the window
    # free to be armed properly. A lock inherited from the logbook is materialised here
    # so it survives log pruning.
    # An override is the ONE case that rewrites an existing lock. It must: without it the lock
    # would still name the old project while the flag names the new one, and pm_persist.sh's
    # cross-check would then scream TAMPER on every turn for the rest of a change the human
    # actually authorised — teaching the session to ignore the alarm that matters.
    if [ "$LOCKABLE" = "1" ] && { [ ! -f "$LOCK" ] || [ "$OVERRODE" = "1" ]; }; then
      if [ "$OVERRODE" = "1" ]; then
        { echo "lock_slug=$3"; echo "lock_doc=$2"; echo "lock_desk=$4"; echo "locked_at=$NOW"; echo "origin=human-override"; echo "previous_slug=$LOCKED_ID"; echo "override_phrase=$GRANT_PHRASE"; echo "session=$CLAUDE_CODE_SESSION_ID"; } > "$LOCK"
      elif [ -n "$LOCKED_ID" ]; then
        { echo "lock_slug=$LOCKED_ID"; echo "lock_doc=$LOCKED_DOC"; echo "lock_desk=$4"; echo "locked_at=$NOW"; echo "origin=logbook"; echo "session=$CLAUDE_CODE_SESSION_ID"; } > "$LOCK"
      elif [ -n "$3" ] && [ "${2#/}" != "$2" ]; then
        { echo "lock_slug=$3"; echo "lock_doc=$2"; echo "lock_desk=$4"; echo "locked_at=$NOW"; echo "origin=first-arm"; echo "session=$CLAUDE_CODE_SESSION_ID"; } > "$LOCK"
      fi
    fi
    # prune-on-write: cap the append-only logbook (keeps the MOST RECENT lines, so the just-appended
    # event is always retained; env PM_EVENTLOG_MAX overrides the default cap). The lock FILE is what
    # makes pruning safe — it is why losing the first arm line can no longer unlock a window.
    # PM_EVENTLOG_MAX is FLOORED at 50 and must be a plain integer. Unfloored, `PM_EVENTLOG_MAX=0`
    # turns the prune into `tail -n 0`, which EMPTIES the logbook — and it fires during a
    # same-slug refresh, which is never refused. That is a sanctioned call silently destroying
    # the retro-fallback. (Found by the adversarial audit, 2026-08-06, finding #3.)
    _cap="${PM_EVENTLOG_MAX:-500}"
    case "$_cap" in (*[!0-9]*|'') _cap=500;; esac
    [ "$_cap" -lt 50 ] 2>/dev/null && _cap=50
    if [ "$(wc -l < "$EVENTLOG" 2>/dev/null || echo 0)" -gt "$_cap" ]; then
      tail -n "$_cap" "$EVENTLOG" > "$EVENTLOG.tmp" 2>/dev/null && mv "$EVENTLOG.tmp" "$EVENTLOG" 2>/dev/null
    fi
    find "$FLAGDIR" -name 'lock-*.project' -type f -mtime +30 -delete 2>/dev/null
    echo "ARMED: $3 -> $2 (session ${CLAUDE_CODE_SESSION_ID:-none}, cwd $PWD)";;
  clear)
    _MALFORMED_NOTE=""
    LK="$(_locked_id)"
    if [ -n "$LK" ]; then
      LOCKED_ID="${LK%%$'\t'*}"; _rest="${LK#*$'\t'}"; LOCKED_DOC="${_rest%%$'\t'*}"
      GRANT_PHRASE="$(_consume_grant)"
      if [ -n "$GRANT_PHRASE" ]; then
        _announce_override clear "$LOCKED_ID" "" "$GRANT_PHRASE"
        _deny_log "clear-OVERRIDDEN-by-human" "" "$LOCKED_ID"
        # FALL THROUGH to the delete below — which touches pm-*.flag ONLY.
      else
        _deny_log "clear-denied" "" "$LOCKED_ID"
        _refuse clear "$LOCKED_ID" "$LOCKED_DOC" ""
        exit 3
      fi
    fi
    # ⛔ THE LOCK FILE IS NEVER DELETED HERE, AUTHORISED OR NOT, and that is what stops the
    # obvious two-step bypass: clear-then-arm-something-else. Clearing frees the FLAG (what the
    # window is currently working through); the LOCK is the window's identity, and identity does
    # not become negotiable because the work finished. After an authorised clear, arming a
    # different project still costs a second, separate act of human authorisation.
    n=0
    [ -f "$FLAG" ] && { rm -f "$FLAG" 2>/dev/null; n=$((n+1)); }
    if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then
      for f in "$FLAGDIR"/pm-*.flag; do
        [ -f "$f" ] || continue
        s="$(grep '^session=' "$f" 2>/dev/null | cut -d= -f2-)"
        [ "$s" = "$CLAUDE_CODE_SESSION_ID" ] && { rm -f "$f" 2>/dev/null; n=$((n+1)); }
      done
    fi
    printf '%s\tclear\t\t\t\t%s\n' "${NOW:-0}" "$CLAUDE_CODE_SESSION_ID" >> "$EVENTLOG" 2>/dev/null
    echo "CLEARED ($n)";;
  locked)
    # Read-only: what is this window locked to? For skills that must CHECK before they arm.
    LK="$(_locked_id)"
    if [ -n "$LK" ]; then echo "${LK%%$'\t'*}"; else echo "none"; fi;;
  ttl)
    # Read-only: the TTL (hours) this file resolved above (env PM_TTL_HOURS if set, else the
    # default literal a few lines up). pm_persist.sh calls this instead of carrying its own
    # copy of the default — see the 2026-08-14 UPDATED note at the top of this file for why.
    echo "$TTL_HOURS";;
  status)
    if [ -f "$FLAG" ]; then
      DP="$(grep '^doc_path=' "$FLAG" 2>/dev/null | cut -d= -f2-)"
      AT="$(grep '^armed_at=' "$FLAG" 2>/dev/null | cut -d= -f2-)"
      if [ -n "$AT" ] && [ -n "$NOW" ] && [ $(( NOW - AT )) -ge $(( TTL_HOURS * 3600 )) ]; then
        rm -f "$FLAG" 2>/dev/null; echo "none"
      elif [ -z "$DP" ]; then echo "none"
      else echo "$DP"; fi
    else echo "none"; fi;;
  *) echo "usage: pm_flag.sh arm <doc> <slug> <desk> | clear | status | locked | ttl" >&2; exit 2;;
esac
exit 0
