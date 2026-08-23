#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: An audit of the system this was ported from found ~50% of its settled, human-blessed facts were
#      invisible to sessions — they existed on disk and were never opened, so 9 of 18 blind-test
#      questions failed to surface something the system already knew. A library nobody opens is not a
#      memory. This SessionStart hook puts the standing-true floor in front of every session without
#      anyone having to think to search for it.
# GUARDS: Nothing — this is a context loader, not a blocker. It never stops a session.
# REDIRECT: N/A (non-blocking). Reads <data root>/doctrine.md (if present), <data root>/canon.md and <data root>/desks/*/canon/current.md,
#      resolved through shared/brain_root.py. Set the data root with: python3 shared/brain_root.py --set <path>
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
#      2026-08-22: the NOT-SET branch now asks the repo's own `.brain-root` pointer what was
#      remembered, before ~/.config — a stale pointer used to print "No data root set yet", the
#      exact fresh-install misreport that branch warns against. The two not-set tests moved onto a
#      sandbox copy of the repo, because a real `.brain-root` is read from brain_root.py's file
#      position and no HOME/env sandbox can hide it. ⛔ No exit code changed.
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

# ⚠ THE REAL CEILING IS NOT OURS TO SET. Claude Code caps every hook's stdout at 10,000 characters;
# above that the model receives a ~2KB preview and a file path — the canon, the doctrine, and this
# file's own STOPPED HERE line all vanish into a file nothing opens (found 2026-08-22: with the ceiling
# at 30,000 every session start since the previous evening had been persisted, 35–47KB emitted, 2KB
# seen). So the default sits UNDER that cap, with room for the section headers and the findings banner
# this counter does not tally. Raising SESSION_CONTEXT_CHAR_CEIL past ~9,500 does not load more — it
# loads NOTHING.
CEIL="${SESSION_CONTEXT_CHAR_CEIL:-9500}"
# Clamp, don't trust: a per-machine settings.local.json that still says 20000 or 30000 (both were
# shipped defaults/advice before 2026-08-22) would silently reproduce the blank-session bug on that
# machine. Lower is always honoured (the self-test uses 500); higher is capped.
case "$CEIL" in ''|*[!0-9]*) CEIL=9500 ;; esac
[ "$CEIL" -gt 9500 ] && CEIL=9500

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

# The one resolver. NOT-SET is a real answer and is reported as one; it is never guessed around.
ROOT="$(python3 "$REPO/shared/brain_root.py" --quiet 2>/dev/null)"
RC=$?
if [ "$RC" -ne 0 ] || [ -z "$ROOT" ]; then
  # ⭐ NOT-SET has TWO causes and they are not the same problem. "You have not chosen a folder yet" is
  # a fresh install. "You chose one and it is not there any more" is a cloud drive that did not mount,
  # an unplugged disk, or a renamed folder — and telling THAT person to "set it once" invites them to
  # point the system at an empty folder and lose the association with their real notes.
  # The resolver deliberately collapses the two (a remembered path that is not a directory falls
  # through rather than resolving), so ask what was remembered, directly — the repo's own
  # `.brain-root` pointer FIRST (2026-08-22: it is the primary way a root is set now; a stale one
  # used to fall through to "No data root set yet", the exact misreport the lines below warn about),
  # then the persisted ~/.config file, then $LIFEHACK_ROOT.
  REMEMBERED="$(python3 - "$REPO" <<'_REMEMBERED_EOF' 2>/dev/null
import sys, os
sys.path.insert(0, os.path.join(sys.argv[1], "shared"))
try:
    import brain_root
    remembered = brain_root.read_repo_pointer() or ""
    if not remembered:
        p = brain_root.BRAIN_ROOT_CONFIG
        remembered = open(p).read().strip() if os.path.isfile(p) else ""
    print(remembered)
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
    echo "    python3 \"$REPO/shared/brain_root.py\" --set \"<where they actually are now>\""
    echo "=== end session context ==="
    exit 0                    # same reasoning as the REPO-not-found branch above: exit 0 is what
                               # gets this message into the model's context; exit 1 would hide it
  fi
  echo "=== Session context ==="
  echo "No data root set yet — nothing was loaded, and that is correct, not broken."
  echo "This is where everything you write will live. Set it once:"
  echo "    python3 \"$REPO/shared/brain_root.py\" --set \"<the folder your notes live in>\" [--create]"
  echo "=== end session context ==="
  exit 0                      # a legitimate state (a fresh install), not a failure
fi

# Every line this file prints counts against the ceiling — headers, the banner, the stop notice —
# because the 10,000-character harness cap (see CEIL above) counts them too. `hdr` prints and tallies.
TOTAL=0
hdr() { printf '%s\n' "$1"; TOTAL=$(( TOTAL + ${#1} + 1 )); }
hdr "=== Session context (loaded automatically) ==="
hdr "Your notes: $ROOT"

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
  out="$(python3 "$REPO/system/tools/health_line.py" "$ledger" 2>/dev/null)"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    echo ""
    echo "note: health_line.py did not run this session (rc=$rc) — findings/health banner unavailable"
    return 0
  fi
  [ -n "$out" ] && { echo ""; printf '%s\n' "$out"; }
}

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
    TOTAL=$(( TOTAL + ${#RC_BODY} ))
    hdr ""
    hdr "--- true for everything ---"
    printf '%s\n' "$RC_BODY"
  else
    echo ""
    echo "!! COULD NOT READ $ROOT_CANON — it exists and is non-empty, but the read returned nothing (check permissions). Root canon NOT loaded this session."
  fi
fi

# ── DOCTRINE: the person's standing operating rules — ONLY if they wrote them ─────────────────
# `<root>/doctrine.md` is how this person wants to be worked with (their hard rules, defaults, rulings).
# It used to reach sessions as a `@` import from CLAUDE.local.md. That import never loaded in the
# desktop app: an import that resolves OUTSIDE the repo is dropped until a one-time approval dialog
# is accepted, and the desktop app runs non-interactively and never shows it — so the file was
# silently absent from every session while INSTALL.md said it was carried (found 2026-08-22 by a
# restart probe). Loading it HERE needs no dialog on any machine and is the same mechanism the root
# canon already uses. It sits right after the root canon — frame first, then the rules for working
# inside it. Same `-s` gate and LOUD-READ posture as the root canon and TELOS: no file, nothing
# printed; a non-empty file that reads back empty is a READ FAILURE and says so.
DOCTRINE_FILE="$ROOT/doctrine.md"
if [ -s "$DOCTRINE_FILE" ]; then
  DC_BODY="$(cat "$DOCTRINE_FILE" 2>/dev/null)"
  if [ -n "$DC_BODY" ]; then
    TOTAL=$(( TOTAL + ${#DC_BODY} ))
    hdr ""
    hdr "--- how to work with me (doctrine.md — standing rules; edit the file, not this line) ---"
    printf '%s\n' "$DC_BODY"
  else
    echo ""
    echo "!! COULD NOT READ $DOCTRINE_FILE — it exists and is non-empty, but the read returned nothing (check permissions). DOCTRINE NOT loaded this session."
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
    hdr ""
    hdr "--- what you are optimizing for this year (state/telos.md — read-only here; /telos is the one writer) ---"
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

FB="$(_findings_banner)"
TOTAL=$(( TOTAL + ${#FB} ))
hdr ""
hdr "Standing notes from ${#CANON[@]} subject folder(s):"
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
  if [ $(( TOTAL + LEN + 220 )) -gt "$CEIL" ]; then     # 220 ≈ the stop notice itself
    REMAINING=$(( ${#CANON[@]} - SHOWN ))
    NAMES=""
    for g in "${CANON[@]:$SHOWN}"; do NAMES="$NAMES $(basename "$(dirname "$(dirname "$g")")")"; done
    echo ""
    echo "!! STOPPED HERE — ceiling ${CEIL} chars; $REMAINING subject floor(s) NOT loaded:${NAMES}. You do NOT have the whole picture — /read <subject>, or open desks/<subject>/canon/current.md under the root above."
    break
  fi
  TOTAL=$(( TOTAL + LEN ))
  SHOWN=$(( SHOWN + 1 ))
  hdr ""
  hdr "--- $SUBJECT ---"
  printf '%s\n' "$BODY"
done

# Second net: the banner is the least load-bearing thing here. If the always-on floor (canon +
# doctrine + telos) already fills the ceiling on its own, printing the banner would tip the WHOLE
# output over the harness cap and lose everything — so withhold it and say so in one line.
if [ -n "$FB" ]; then
  if [ "$TOTAL" -gt "$CEIL" ]; then
    echo ""
    echo "note: findings banner withheld (${#FB} chars) — the always-on floor fills the ceiling; run: python3 system/tools/health_line.py ~/.config/lifehack/faults.json"
  else
    printf '%s\n' "$FB"
  fi
fi

echo ""
echo "=== end session context ==="
exit 0
