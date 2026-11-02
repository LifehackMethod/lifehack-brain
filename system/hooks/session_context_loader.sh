#!/usr/bin/env bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "session_context_loader.sh" "SessionStart" "" 2>/dev/null || true' EXIT
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: An audit of the system this was ported from found ~50% of its settled, human-blessed facts were
#      invisible to sessions — they existed on disk and were never opened, so 9 of 18 blind-test
#      questions failed to surface something the system already knew. A library nobody opens is not a
#      memory. This SessionStart hook puts the standing-true floor in front of every session without
#      anyone having to think to search for it.
# GUARDS: Nothing — this is a context loader, not a blocker. It never stops a session.
# REDIRECT: N/A (non-blocking). Reads <data root>/canon.md (always) and, for the ONE desk this
# session is in (cwd under <root>/desks/<desk>/ or $LIFEHACK_DESK), that desk's canon/current.md —
#      resolved through shared/brain_root.py. Set the data root with: python3 (or python) shared/brain_root.py --set <path>
#      Also invokes `system/tools/health_line.py <ledger>` (see _findings_banner() below) once ROOT is
#      resolved, to render the Hospital/Efficiency findings banner nothing else was calling.
# SIGNPOST: the data-root contract lives in shared/brain_root.py; the folder shape it reads is what
#      /ingest PHASE 4 builds (.claude/skills/ingest/phases/4-place.md). The findings-banner contract
#      lives in system/tools/health_line.py's own module docstring ("never raises, never exits nonzero").
# FAIL_POSTURE: LOUD for the canon/root path — never silently succeeds, see the note below.
#      _findings_banner() is FAIL-SOFT by design (a broken health_line.py must not break a session)
#      but not SILENT: a nonzero rc from the tool itself prints one short "did not run" line rather
#      than nothing, so this file does not grow a second copy of its own named bug in a new spot.
#      ⚠ EVERY EXIT PATH IN THIS FILE IS `exit 0`, ON PURPOSE, INCLUDING THE REAL FAILURES —
#      this is not the same posture as "exit 0 = silently succeeded." Verified against the real
#      SessionStart contract: this event is structurally non-blocking regardless of exit code
#      (no exit-2-blocks behavior here, unlike PreToolUse), and on a NON-zero exit Claude Code
#      does NOT inject this hook's stdout into the model's context — only stderr renders, as a
#      UI-only notice the model itself never sees. So a real failure exiting non-zero would not
#      "fail safely," it would make its own loud message invisible to the one reader this whole
#      file exists for — the exact bug this header describes, one exit code later. `exit 0` +
#      stdout is the ONLY channel that reaches the model here, so every branch uses it.
# UPDATED: 2026-08-11 (ported; the silent-success bug fixed, and the exit path made real).
#      2026-10-27 (task 2.1): _findings_banner() replaced by _job_health_line() — health_line.py now prints ONE
#      job-health line from local job state, and the hook prints it as THE FIRST LINE, before the header.
#      No exit code changed — every path is still `exit 0`.
#      2026-10-27: writes ~/.config/lifehack/code-root, the pointer every scheduled job's launch
#      line reads to find job-run.sh (self-monitoring plan §B.1). Silent and fail-soft, no exit change.
# 2026-11-02 (COMPASS P-71, decision 2g): the standing floor is now DESK-SCOPED — at most ONE
# desk's canon loads (the desk named by $LIFEHACK_DESK, else the desk the cwd is inside), never
# every desk's. No desk signal and a cwd outside every desk loads no desk canon at all.
# No exit code changed — every path in this file is still `exit 0`.
#      2026-08-14: wired in system/tools/health_line.py (_findings_banner()) — see the note below the
#      "Deliberately NOT ported" paragraph for why this is not a reversal of that exclusion.
#      2026-08-14: two more suppressed reads fixed (an existing-but-unreadable canon.md or subject
#      current.md used to fall through `[ -n "$BODY" ] || continue` silently — indistinguishable
#      from a legitimately empty file). AND the two remaining `exit 1` branches (repo-not-found,
#      remembered-root-vanished) were changed to `exit 0` — they were already fail-CLOSED-ISH in
#      spirit (non-zero on real failure) but that reasoning didn't hold for SessionStart specifically:
#      see FAIL_POSTURE above.
#      2026-08-15: the TELOS / strategic-brief block RESTORED, but GATED on `-s` (exists AND non-empty)
#      so a fresh install pays exactly zero bytes for it. See the struck exclusion note below and the
#      block's own comment. ⛔ No exit code changed — every path in this file is still `exit 0`.
# ─────────────────────────────────────────────────────────────────────────────
#
# ⭐ THE BUG THIS FILE IS BUILT AGAINST — it was in the original, and it is the whole point:
# the version this came from suppressed stderr and ended on an unconditional `exit 0` WHILE PRINTING
# NOTHING. So on a machine where the data was not where it expected, it opened, REPORTED SUCCESS, and
# delivered NO MEMORY — silently, every session, for as long as nobody happened to notice. A system
# that cannot see its own memory looks exactly like a system that has none yet. Every branch below
# therefore SAYS which state it is in, loudly, on stdout — and every branch, including the genuine
# internal failures, exits 0, because for THIS hook exit 0 is what makes that message reach the model
# (see FAIL_POSTURE above). The fix for "reported success while doing nothing" was never the exit
# code — it was printing the truth. The exit code point is a distinct, later-discovered trap: a
# NON-zero exit doesn't make the failure any louder, it makes the message that was going to report it
# disappear.
#
# Deliberately NOT ported from the original: ~~its strategic-brief block,~~ its overnight-jobs brief, and
# its DONOR background-health line (a Pulse-tile reader). ~~All three~~ BOTH read files produced by machinery
# that is not part of this system. A loader that prints headings for things nothing writes teaches a
# shape that does not exist.
#   ✎ CORRECTED 2026-08-15 (T9.7 wiring pass): the strategic-brief exclusion was struck, not deleted, so
#   the reasoning stays readable. It was wrong on its own stated test — the test is "does the producing
#   machinery live in this system," and for the strategic brief it DOES: `.claude/skills/telos/` is the
#   documented sole writer of `<notes>/state/telos.md`. The other two exclusions were and remain correct
#   (nothing here writes an overnight-jobs brief or a Pulse tile). The block is restored below, GATED on
#   `-s` — see its own comment for why the gate is the answer to both halves of the argument.
#
# ⚠ THAT EXCLUSION IS NOT THE SAME THING AS THE _findings_banner() CALL BELOW, and the two must not
# be read as contradicting each other. The donor's background-health line read Pulse-cron tiles this
# product never had. `system/tools/health_line.py` is a DIFFERENT, separately-ported mechanism whose
# producer machinery genuinely IS in this repo — `emit_finding.py`/`findings_reader.py` (Hospital) and
# `fault_ledger.py` (the machine-local fault ledger) all exist and run here. It had a writer, a store,
# and a renderer that worked standalone, but nothing called it from a real session — the same
# "detection works, consumption does not" shape as the bug above, one layer down. Wiring it in is
# closing that gap, not reintroducing the excluded donor block.

CEIL="${SESSION_CONTEXT_CHAR_CEIL:-20000}"

# ── code-root pointer (self-monitoring plan §B.1) ── every scheduled job's launchd line runs
# "$(cat ~/.config/lifehack/code-root)/system/tools/job-run.sh", so no plist ever carries a code path.
# Whatever copy of the harness this session runs from becomes the copy the jobs run. Only a root that
# actually has job-run.sh is written (an older release would point the jobs at nothing). Atomic
# (tmp + mv), silent, fail-soft: a pointer problem must never cost a session its context.
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$CLAUDE_PLUGIN_ROOT/system/tools/job-run.sh" ]; then
  _cr_file="$HOME/.config/lifehack/code-root"
  if [ "$(cat "$_cr_file" 2>/dev/null)" != "$CLAUDE_PLUGIN_ROOT" ]; then
    mkdir -p "$HOME/.config/lifehack" 2>/dev/null \
      && printf '%s\n' "$CLAUDE_PLUGIN_ROOT" > "$_cr_file.tmp.$$" 2>/dev/null \
      && mv -f "$_cr_file.tmp.$$" "$_cr_file" 2>/dev/null
    rm -f "$_cr_file.tmp.$$" 2>/dev/null
  fi
fi

REPO="$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)"
if [ -z "$REPO" ] || [ ! -f "$REPO/shared/brain_root.py" ]; then
  echo "=== Session context ==="
  echo "!! CANNOT START: this hook could not find its own repository from $0."
  echo "!! Expected shared/brain_root.py two directories up. Nothing was loaded."
  echo "=== end session context ==="
  # ⚠ exit 0, DELIBERATELY, even for this real failure — verified against the SessionStart
  # exit-code contract: this event is structurally non-blocking regardless of exit code (there is
  # no exit-2-blocks behavior here, unlike PreToolUse), and on a NON-zero exit, Claude Code does
  # NOT inject this hook's stdout into the model's context at all — only stderr renders, as a
  # UI-only notice the model itself never sees. So `exit 1` here would not make the session
  # "fail safely"; it would silently throw away the very message above, reproducing this file's
  # own named bug one exit code later. exit 0 is the ONLY way this line reaches the model.
  exit 0
fi

# ── PYTHON INTERPRETER — resolved, never hardcoded (Issue #55) ───────────────────────────────────
# ⭐ THE BUG THIS BLOCK FIXES: the official Windows Python installer does NOT create a `python3`
# executable — only `python.exe` + the `py` launcher. A hardcoded `python3` call below therefore
# fails on a stock Windows install with "command not found" (RC 127), which the old code could not
# tell apart from "brain_root.py ran fine and honestly reports NOT-SET" — both look like "RC != 0,
# empty ROOT." The result: a Windows user whose data root WAS set for days got told "nothing was
# loaded, and that is correct, not broken" — the exact false-reassurance this file's header exists
# to prevent, one layer down, in its own interpreter call. Resolving PY explicitly, and treating
# "no interpreter at all" as its own loud, distinct case BEFORE the NOT-SET branch is ever reached,
# is the fix — not a Windows-only patch, since `python3` genuinely does not exist on some machines.
PY="$(command -v python3 2>/dev/null || command -v python 2>/dev/null)"
if [ -z "$PY" ]; then
  echo "=== Session context ==="
  echo "!! CANNOT START: no Python interpreter found on PATH (tried: python3, python)."
  echo "!! Nothing was loaded. This is NOT the same as an empty or fresh system — the loader itself"
  echo "!! could not run, so it has no way to know whether a data root is set or not."
  echo "!! Install Python 3 and make sure it is on PATH (on Windows: the python.org installer adds"
  echo "!! 'python', not 'python3' — either works here), then start a new session."
  echo "=== end session context ==="
  exit 0                      # same reasoning as every other branch in this file: exit 0 is what
                               # gets this message into the model's context; exit 1 would hide it
fi

# ── THE JOB-HEALTH LINE (2.1) — printed FIRST, before any header. One line from local job state
# (system/tools/health_line.py reads ~/.config/lifehack/state/jobs/*). health_line.py never raises and
# never exits nonzero, so a nonzero rc means the TOOL could not start: say so in one line rather than
# go silent. Always returns 0.
_job_health_line() {
  local out rc
  out="$("$PY" "$REPO/system/tools/health_line.py" 2>/dev/null)"
  rc=$?
  if [ "$rc" -ne 0 ] || [ -z "$out" ]; then
    echo "note: health_line.py did not run this session (rc=$rc) — job health unavailable"
    return 0
  fi
  printf '%s\n' "$out"
  return 0
}

_job_health_line   # FIRST line of output, ahead of every "=== Session context" header below

# ── TEAM-SHARED SKILLS CHECK — Drive skill sharing (approved design 2026-11-01, SIMPLE build) ──
# WHY THIS LIVES HERE, NOT A NEW HOOK: same reasoning as the CAP_CHECK block below — this hook
# already fires every session, so ONE call site, no fourth part watching a third part. It sits
# BEFORE the brain-root resolution on purpose: team skill sharing is independent of the notes
# root, and the "no subject folders yet" exit further down must not skip it (the fresh-install
# path is exactly the one a new team member is on). The switch (team_skill_verify in
# roundB.conf, DEFAULT OFF) is read INSIDE team_skills.py --session-check, through lib/roundb.py
# like every other switch, so OFF = exactly today's behaviour: this call runs, prints nothing,
# costs a python startup. SILENCE IS THE HEALTHY STATE: with the switch on, a session prints one
# line per BROKEN/MISSING/changed-for-the-worse shared skill only. FAIL-SOFT, ALWAYS: same
# contract as CAP_CHECK — guarded by -r first and `|| true` besides; no nonzero exit from here
# ever escapes (a session must never fail to start because a shared skill drifted). The check
# never touches the Drive copy; on a failed re-scan it drops the local LINK only.
TEAM_CHECK="$REPO/shared/tools/team_skills.py"
if [ -r "$TEAM_CHECK" ]; then
  TEAM_OUT="$("$PY" "$TEAM_CHECK" --session-check 2>/dev/null || true)"
  [ -n "$TEAM_OUT" ] && { echo ""; printf '%s\n' "$TEAM_OUT"; }
fi

# The one resolver. NOT-SET is a real answer and is reported as one; it is never guessed around.
ROOT="$("$PY" "$REPO/shared/brain_root.py" --quiet 2>/dev/null)"
RC=$?
if [ "$RC" -ne 0 ] || [ -z "$ROOT" ]; then
  # ⭐ NOT-SET has TWO causes and they are not the same problem. "You have not chosen a folder yet" is
  # a fresh install. "You chose one and it is not there any more" is a cloud drive that did not mount,
  # an unplugged disk, or a renamed folder — and telling THAT person to "set it once" invites them to
  # point the system at an empty folder and lose the association with their real notes.
  # The resolver deliberately collapses the two (a remembered path that is not a directory falls
  # through rather than resolving), so ask what was remembered, directly.
  REMEMBERED="$("$PY" - "$REPO" <<'_REMEMBERED_EOF' 2>/dev/null
import sys, os
sys.path.insert(0, os.path.join(sys.argv[1], "shared"))
try:
    import brain_root
    p = brain_root.BRAIN_ROOT_CONFIG
    print(open(p).read().strip() if os.path.isfile(p) else "")
except Exception:
    print("")
_REMEMBERED_EOF
)"
  [ -n "$REMEMBERED" ] || REMEMBERED="${LIFEHACK_ROOT:-}"
  if [ -n "$REMEMBERED" ] && [ ! -d "$REMEMBERED" ]; then
    echo "=== Session context ==="
    echo "!! YOUR NOTES ARE NOT WHERE THIS SYSTEM REMEMBERS THEM: $REMEMBERED"
    echo "!! Nothing was loaded. This is NOT an empty system — it is a system that cannot see its own"
    echo "!! memory. If that folder lives in a cloud drive, it may simply not be mounted yet."
    echo "!! Do NOT start writing, and do NOT point this at a new empty folder — you would lose the"
    echo "!! link to everything already there. Get the folder back, or:"
    echo "    $PY \"$REPO/shared/brain_root.py\" --set \"<where they actually are now>\""
    echo "=== end session context ==="
    exit 0                    # same reasoning as the REPO-not-found branch above: exit 0 is what
                               # gets this message into the model's context; exit 1 would hide it
  fi
  echo "=== Session context ==="
  echo "No data root set yet — nothing was loaded, and that is correct, not broken."
  echo "This is where everything you write will live. Set it once:"
  echo "    $PY \"$REPO/shared/brain_root.py\" --set \"<the folder your notes live in>\" [--create]"
  echo "=== end session context ==="
  exit 0                      # a legitimate state (a fresh install), not a failure
fi

echo "=== Session context (loaded automatically) ==="
echo "Your notes: $ROOT"

TOTAL=0

# ── THE ROOT CANON: the few things true for every conversation, on any subject ───────────────────
# ⭐ THIS BLOCK IS A BUG FIX (2026-08-11), and the bug was a promise nothing kept. This loader read
# the subject folders and stopped there — while FOUR shipped places told the person the opposite:
# `system/tools/bootstrap.py` writes the sentence "a cold session loads this file before it loads
# anything else… carried into every conversation that follows, forever" INTO THE FILE ITSELF, and
# `.claude/skills/ingest/phases/4-place.md` says it three more times, once while making the person
# read every line of it aloud precisely because of that weight. None of it was true. `/read` opens
# the file on demand, which is a different claim entirely — on demand is not every session.
# It is the same shape as the journal bug found on the same day: a path that looks fine, is never
# exercised, and fails in the direction that looks like "you have not written anything yet."
#
# IT GOES FIRST, and it is never the thing the ceiling drops. It is the smallest file here — the
# canon-write guard caps it at 3,200 characters — and it is the one every subject defers up to. A
# session that has the subjects but not the root has the details without the frame.
ROOT_CANON="$ROOT/canon.md"
if [ -s "$ROOT_CANON" ]; then
  # `-s` already proved this file is non-empty. So if the read below still comes back empty, the
  # READ failed (permissions, a race with a delete) — that is NOT the same state as "nothing to
  # show," and silently falling through here was the exact bug this file is built against, one
  # file down from the root-resolution case above. Say so; don't just skip it.
  RC_BODY="$(cat "$ROOT_CANON" 2>/dev/null)"
  if [ -n "$RC_BODY" ]; then
    TOTAL=${#RC_BODY}
    echo ""
    echo "--- true for everything ---"
    printf '%s\n' "$RC_BODY"
  else
    echo ""
    echo "!! COULD NOT READ $ROOT_CANON — it exists and is non-empty, but the read returned nothing (check permissions). Root canon NOT loaded this session."
  fi
fi

# ── TELOS: the year-long strategic brief — ONLY if this person actually has one ──────────────────
# ⭐ THE GATE IS THE WHOLE ARGUMENT, and it is the answer to BOTH sides of a real tension.
# This block was cut when this loader was ported, and the reason was good AT THE TIME: the same week,
# this repo's root canon was reduced 87.7% precisely to shrink what every single session pays for, and
# an UNCONDITIONAL strategic-brief block is exactly the always-on cost that reduction was buying back.
# But the opposite failure is the one this entire file exists against: `.claude/skills/telos/` writes
# `<notes>/state/telos.md` and calls it the standing answer to "what am I optimizing for this year" —
# and a standing answer that nothing ever opens is the library-nobody-opens bug, one more time.
# `-s` settles both without compromise, because the two populations are disjoint:
#   · fresh install / never ran /telos -> no state/telos.md -> ZERO bytes, ZERO lines, nothing printed
#   · someone who wrote one            -> gets their own strategic frame back at every session start
# An EMPTY telos.md (the starter at system/templates/telos-starter.md copied and never filled) is
# treated as ABSENT — which is the truth about it, not a fudge.
# It counts against TOTAL/CEIL like everything else, so the ceiling's accounting stays honest.
# Same LOUD-READ posture as the root canon above: `-s` has already proved the file non-empty, so an
# empty read is a READ FAILURE, not "nothing to say" — it says so instead of silently falling through.
TELOS_FILE="$ROOT/state/telos.md"
if [ -s "$TELOS_FILE" ]; then
  TL_BODY="$(cat "$TELOS_FILE" 2>/dev/null)"
  if [ -n "$TL_BODY" ]; then
    TOTAL=$(( TOTAL + ${#TL_BODY} ))
    echo ""
    echo "--- what you are optimizing for this year (state/telos.md — read-only here; /telos is the one writer) ---"
    printf '%s\n' "$TL_BODY"
  else
    echo ""
    echo "!! COULD NOT READ $TELOS_FILE — it exists and is non-empty, but the read returned nothing (check permissions). TELOS NOT loaded this session."
  fi
fi

# ── The standing floor, DESK-SCOPED (COMPASS P-71, decision 2g — fixed 2026-11-02) ────────────────
# /ingest PHASE 4 builds <root>/desks/<subject>/canon/current.md — "the things that stay true" — and
# that is what belongs in front of a session working in that desk. Dated records are NOT loaded:
# they are retrieved on demand, and loading them all is how a context window fills with last month's
# noise.
# ⭐ P-71 (COMPASS, 2026-11-02): "A desk window loads only that desk's knowledge; that separation is
# the point of the folder schema." Until this block, a glob here loaded EVERY desk's canon into EVERY
# session — the exact opposite of that design, and the thing this fix removes. Now: the shared root
# canon above always loads, and AT MOST ONE desk's canon loads — the desk named by the explicit
# signal $LIFEHACK_DESK (the same self-identity env shared/tools/email_convert.py and
# system/tools/safe_input.py already read), else the desk the cwd is actually inside
# (<root>/desks/<desk>/...). No signal and a cwd outside every desk means NO desk canon — a session
# started in the plugin repo is in nobody's desk, and loading everyone's is the bug, not a fallback.
# A missing desk list cannot crash this block: the cwd case is inferred from the folder schema
# itself, and the desk list (<notes>/desks/desk-registry.yaml, read only via shared/desk_list.py) is
# consulted ONLY to map a $LIFEHACK_DESK desk_id that is not itself a folder name — see below.
# realpath on both sides (in Python, not the shell glob engine) so a symlinked cwd meets the real
# desk path, and Windows backslash-native roots work the same day they did not for a bash glob.
# ✎ 2026-11-02 (verify pass): $LIFEHACK_DESK carries a desk_id, and the desk list (read ONLY through
# shared/desk_list.py) is where a desk_id meets its folder — desk_scaffold.py makes them equal, but
# backlog_groom.py reads open_loops_path "VERBATIM — never derived from desk_id", so they may differ.
# So: a desk_id that is not itself a folder is looked up in the list (purpose_path/open_loops_path
# = desks/<folder>/...). A MISSING list is not an error (no desks listed; folder inference still
# works); an UNREADABLE list is said out loud. "root" is safe_input.py's own no-desk default, so it
# means no desk here too, not DESK NOT FOUND.
DESK="$("$PY" - "$ROOT" "$REPO/shared" <<'_DESK_EOF'
import os, sys
root = os.path.realpath(sys.argv[1])
desk = (os.environ.get("LIFEHACK_DESK") or "").strip()
if desk == "root":
    desk = ""
def bad_name(d):
    return d in (".", "..") or "/" in d or "\\" in d or os.sep in d
def isdesk(d):
    return bool(d) and not bad_name(d) and os.path.isdir(os.path.join(root, "desks", d))
if desk:
    # a desk name must be ONE path component — anything else is a malformed signal, not a desk
    if bad_name(desk):
        print("missing:" + desk)
        sys.exit(0)
    if isdesk(desk):
        print(desk)
        sys.exit(0)
    # not a folder name: ask the desk list of this person (shared/desk_list.py, the ONE reader of it)
    try:
        sys.path.insert(0, sys.argv[2])
        import desk_list
        folder, err = desk_list.desk_folder(desk)   # PyYAML-free; never raises
    except Exception as e:
        folder, err = None, "%s: %s" % (type(e).__name__, e)
    if err:
        print("listerr:" + desk + "|" + " ".join(str(err).split()))
        sys.exit(0)
    print(folder if isdesk(folder or "") else "missing:" + desk)
    sys.exit(0)
# no signal: the desk the cwd is actually inside. normcase so a case-insensitive (Windows) path
# still matches; the folder NAME is read from the un-folded cwd so it keeps its on-disk case.
cwd = os.path.realpath(os.getcwd())
prefix = os.path.join(root, "desks") + os.sep
if os.path.normcase(cwd).startswith(os.path.normcase(prefix)):
    first = cwd[len(prefix):].split(os.sep)[0]
    if isdesk(first):
        print(first)
_DESK_EOF
)"
case "$DESK" in
  missing:*)
    _bad="${DESK#missing:}"
    echo ""
    echo "!! DESK NOT FOUND: \$LIFEHACK_DESK='$_bad' names no folder under $ROOT/desks/ and no desk_id in your desk list — no desk canon loaded this session."
    DESK=""; _DESK_SAID=1
    ;;
  listerr:*)
    _rest="${DESK#listerr:}"
    echo ""
    echo "!! DESK NOT FOUND: \$LIFEHACK_DESK='${_rest%%|*}' is not a folder under $ROOT/desks/, and your desk list could not be read to look it up: ${_rest#*|}"
    echo "!! No desk canon loaded this session."
    DESK=""; _DESK_SAID=1
    ;;
esac

# ── NESTED CANON — make the miss LOUD, never silent (Issue #96-§5), for THIS desk only ────────────
# ⭐ THE GAP: the one-level reach above loads desks/<desk>/canon/current.md, but a desk directory can
# also contain a NESTED subject folder with its OWN canon/current.md (desks/<desk>/<nested>/canon/
# current.md), invisible to this loader. ⛔ The fix is NOT a recursive load (withdrawn — sub-agent
# loading for a nested subject is V2 scope). This block changes nothing about what loads; it prints
# the path of anything that would be silently missed, so the gap stays visible instead of silent.
if [ -n "$DESK" ]; then
  while IFS= read -r _nested; do
    echo "!! NESTED CANON NOT LOADED (one level does not reach it): $_nested"
  done < <(find "$ROOT/desks/$DESK" -mindepth 3 -type f -name current.md -path "*/canon/current.md" 2>/dev/null)
fi

if [ -z "$DESK" ] && [ -n "${_DESK_SAID:-}" ]; then
  :   # the DESK NOT FOUND line above already said why no desk canon loaded; the shared canon still did
elif [ -z "$DESK" ]; then
  echo ""
  echo "No desk this session — the cwd is not inside a desk folder and \$LIFEHACK_DESK names none, so no"
  echo "desk canon was loaded (P-71: a desk window loads only that desk's knowledge). The shared root"
  echo "canon above still loads. Open a session inside <notes>/desks/<desk>/ to load that desk's canon."
elif [ ! -s "$ROOT/desks/$DESK/canon/current.md" ]; then
  echo ""
  echo "Desk '$DESK' has no canon/current.md yet — nothing standing to load for it. Run /ingest or"
  echo "/save in that desk to write one. No other desk's canon was loaded (P-71)."
else
  DESK_CANON="$ROOT/desks/$DESK/canon/current.md"
  # Same reasoning as the root canon above: `-s` already proved non-empty, so an empty read means
  # the file could not be read (permissions), not that it had nothing to say. Say so; don't skip.
  BODY="$(cat "$DESK_CANON" 2>/dev/null)"
  if [ -z "$BODY" ]; then
    echo ""
    echo "!! COULD NOT READ $DESK_CANON ($DESK) — it exists and is non-empty, but the read returned nothing (check permissions). Desk canon NOT loaded this session."
  else
    LEN=${#BODY}
    # ⚠ CEILING, and it announces itself. Measured on the system this came from: an unbounded canon
    # emit reached 62 KB in ONE session start. Silently dropping the tail would be worse than the
    # flood — a session would believe it had the whole floor. So: stop, and say what was left out.
    if [ $(( TOTAL + LEN )) -gt "$CEIL" ]; then
      echo ""
      echo "!! STOPPED HERE — ${CEIL} characters is the ceiling, and the desk canon for '$DESK' was"
      echo "!! NOT loaded. You do NOT have the whole picture this session. Read it directly, or raise"
      echo "!! SESSION_CONTEXT_CHAR_CEIL."
    else
      TOTAL=$(( TOTAL + LEN ))
      echo ""
      echo "--- $DESK (this session's desk) ---"
      printf '%s\n' "$BODY"
    fi
  fi
fi

# ── SKILL CAPABILITY CHECK — T3.7(c) wiring ───────────────────────────────────────────────────
# WHY THIS LIVES HERE, NOT A NEW DETECTOR: system/build-rules-index.md's code-spiral rule says
# put the fact where the session ALREADY looks, not stand up a fourth part to watch a third part
# watching a second part. This hook already fires every session -- that is the call site, on
# purpose: ONE part, ONE call site, and deliberately no separate component watching this one.
# SILENCE IS THE HEALTHY STATE: measured 2026-08-23, 9 skills declare tools via `allowed-tools:`
# in YAML frontmatter; only 1 (first-principles, declaring AskUserQuestion) is bare-denied; the
# other 8 are merely scope-restricted and must print nothing. Quiet here is the expected, common
# outcome, not "it didn't run" -- see skill_capability_check.py's own --self-test for proof its
# negative control (a scope-restricted tool) stays silent while a bare-denied one still fires.
# FAIL-SOFT, ALWAYS: this must never block or fail the hook. A session that cannot start because
# a skill's metadata is wrong is a worse failure than the one this check exists to catch, so the
# call is guarded by `-r` first and `|| true` besides -- no nonzero exit from here ever escapes.
CAP_CHECK="$REPO/system/tools/skill_capability_check.py"
if [ -r "$CAP_CHECK" ]; then
  CAP_OUT="$("$PY" "$CAP_CHECK" 2>/dev/null || true)"
  [ -n "$CAP_OUT" ] && { echo ""; printf '%s\n' "$CAP_OUT"; }
fi

echo ""
echo "=== end session context ==="
exit 0
