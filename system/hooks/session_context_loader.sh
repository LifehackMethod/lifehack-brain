#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: An audit of the system this was ported from found ~50% of its settled, human-blessed facts were
#      invisible to sessions — they existed on disk and were never opened, so 9 of 18 blind-test
#      questions failed to surface something the system already knew. A library nobody opens is not a
#      memory. This SessionStart hook puts the standing-true floor in front of every session without
#      anyone having to think to search for it.
# GUARDS: Nothing — this is a context loader, not a blocker. It never stops a session.
# REDIRECT: N/A (non-blocking). Reads <data root>/canon.md and <data root>/desks/*/canon/current.md,
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
#      2026-08-16 (Issue #55): `python3` was hardcoded, and the official Windows Python installer does
#      not create that name — only `python`/`python.exe`. On such a machine every `python3` call below
#      failed (command not found), which the old code could not distinguish from brain_root.py honestly
#      reporting NOT-SET — a Windows user with a data root set for days was told "nothing was loaded,
#      and that is correct, not broken," the exact false-reassurance this file exists to prevent, one
#      layer down in its own interpreter call. Fixed by resolving `PY` once (`python3`, falling back to
#      `python`) right after the REPO check, and treating "no interpreter on PATH at all" as its own
#      loud, distinct branch — reported before the NOT-SET branch can ever be reached, still `exit 0`.
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

# ── THE FINDINGS/HEALTH BANNER — the other half of a promise this file already fixed once. ────
# Detection was never the missing piece: emit_finding.py -> findings_reader.py -> health_line.py
# already form a complete chain, and health_line.py renders real content when run directly
# (confirmed: a guard-fire-test ERROR row renders correctly standalone). But nothing called
# health_line.py from a real session — the exact "detection works, consumption does not"
# failure this system keeps re-finding, and the fix is almost always this small: one call from a
# surface that ALREADY fires every session, not new machinery. This is that call.
# FAIL-SOFT, ON PURPOSE: health_line.py's own contract is "never raises, never exits nonzero" —
# so a nonzero rc here means the TOOL ITSELF could not even start (missing file, broken
# interpreter), a different failure than "nothing to report." That case gets ONE short line
# saying so, rather than being swallowed — silence there would grow a second copy of the exact
# bug this file's own header describes fixing for the canon path above. A working health_line.py
# that finds nothing still prints nothing, same as always; this loader adds no new command.
_findings_banner() {
  local ledger out rc
  ledger="$HOME/.config/lifehack/faults.json"     # fault_ledger.py's own LEDGER path — read-only
  out="$("$PY" "$REPO/system/tools/health_line.py" "$ledger" 2>/dev/null)"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    echo ""
    echo "note: health_line.py did not run this session (rc=$rc) — findings/health banner unavailable"
    return 0
  fi
  [ -n "$out" ] && { echo ""; printf '%s\n' "$out"; }
}

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

# ── The standing floor: one canon file per subject folder ────────────────────────────────────────
# /ingest PHASE 4 builds <root>/desks/<subject>/canon/current.md — "the things that stay true" — and
# that is what belongs in front of every session. Dated records are NOT loaded: they are retrieved on
# demand, and loading them all is how a context window fills with last month's noise.
shopt -s nullglob 2>/dev/null
CANON=("$ROOT"/desks/*/canon/current.md)
shopt -u nullglob 2>/dev/null

if [ "${#CANON[@]}" -eq 0 ]; then
  echo ""
  echo "No subject folders yet — nothing standing to load beyond the above. Run /ingest to build them,"
  echo "or just start working and /save will make them as it goes."
  _findings_banner
  echo "=== end session context ==="
  exit 0
fi

echo ""
echo "Standing notes from ${#CANON[@]} subject folder(s):"
SHOWN=0
for f in "${CANON[@]}"; do
  SUBJECT="$(basename "$(dirname "$(dirname "$f")")")"
  if [ ! -s "$f" ]; then
    continue   # genuinely empty — a legitimate, quiet state, not an error
  fi
  # Same reasoning as the root canon above: `-s` already proved non-empty, so an empty read here
  # means the file could not be read (permissions), not that it had nothing to say. One unreadable
  # subject must not silently drop out of a list that still names the OTHER subjects it loaded —
  # say which one failed and keep going.
  BODY="$(cat "$f" 2>/dev/null)"
  if [ -z "$BODY" ]; then
    echo ""
    echo "!! COULD NOT READ $f ($SUBJECT) — it exists and is non-empty, but the read returned nothing (check permissions). Skipped."
    continue
  fi
  LEN=${#BODY}
  # ⚠ CEILING, and it announces itself. Measured on the system this came from: an unbounded canon
  # emit reached 62 KB in ONE session start. Silently dropping the tail would be worse than the
  # flood — a session would believe it had the whole floor. So: stop, and say what was left out.
  if [ $(( TOTAL + LEN )) -gt "$CEIL" ]; then
    REMAINING=$(( ${#CANON[@]} - SHOWN ))
    echo ""
    echo "!! STOPPED HERE — ${CEIL} characters is the ceiling and $REMAINING more subject folder(s) were"
    echo "!! NOT loaded. You do NOT have the whole picture this session. Read them directly, or raise"
    echo "!! SESSION_CONTEXT_CHAR_CEIL. Not loaded:"
    for g in "${CANON[@]:$SHOWN}"; do
      echo "!!   $(basename "$(dirname "$(dirname "$g")")")  ($g)"
    done
    break
  fi
  TOTAL=$(( TOTAL + LEN ))
  SHOWN=$(( SHOWN + 1 ))
  echo ""
  echo "--- $SUBJECT ---"
  printf '%s\n' "$BODY"
done

_findings_banner

echo ""
echo "=== end session context ==="
exit 0
