#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: An audit of the system this was ported from found ~50% of its settled, human-blessed facts were
#      invisible to sessions — they existed on disk and were never opened, so 9 of 18 blind-test
#      questions failed to surface something the system already knew. A library nobody opens is not a
#      memory. This SessionStart hook puts the standing-true floor in front of every session without
#      anyone having to think to search for it.
# GUARDS: Nothing — this is a context loader, not a blocker. It never stops a session.
# REDIRECT: N/A (non-blocking). Reads <data root>/canon.md and <data root>/desks/*/canon/current.md,
#      resolved through shared/brain_root.py. Set the data root with: python3 shared/brain_root.py --set <path>
# SIGNPOST: the data-root contract lives in shared/brain_root.py; the folder shape it reads is what
#      /ingest PHASE 4 builds (.claude/skills/ingest/phases/4-place.md).
# FAIL_POSTURE: LOUD. Never silently succeeds — see the note below.
# UPDATED: 2026-08-11 (ported; the silent-success bug fixed, and the exit path made real)
# ─────────────────────────────────────────────────────────────────────────────
#
# ⭐ THE BUG THIS FILE IS BUILT AGAINST — it was in the original, and it is the whole point:
# the version this came from suppressed stderr and ended on an unconditional `exit 0`. So on a machine
# where the data was not where it expected, it opened, REPORTED SUCCESS, and delivered NO MEMORY —
# silently, every session, for as long as nobody happened to notice. A system that cannot see its own
# memory looks exactly like a system that has none yet. Every branch below therefore SAYS which one it
# is, and a genuine internal failure exits NON-ZERO instead of pretending.
#
# Deliberately NOT ported from the original: its strategic-brief block, its overnight-jobs brief, and
# its background-health line. All three read files produced by machinery that is not part of this
# system. A loader that prints headings for things nothing writes teaches a shape that does not exist.

CEIL="${SESSION_CONTEXT_CHAR_CEIL:-20000}"

REPO="$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)"
if [ -z "$REPO" ] || [ ! -f "$REPO/shared/brain_root.py" ]; then
  echo "=== Session context ==="
  echo "!! CANNOT START: this hook could not find its own repository from $0."
  echo "!! Expected shared/brain_root.py two directories up. Nothing was loaded."
  echo "=== end session context ==="
  exit 1                      # a real failure exits non-zero — it does not pretend to have worked
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
  # through rather than resolving), so ask what was remembered, directly.
  REMEMBERED="$(python3 - "$REPO" <<'_REMEMBERED_EOF' 2>/dev/null
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
    echo "    python3 \"$REPO/shared/brain_root.py\" --set \"<where they actually are now>\""
    echo "=== end session context ==="
    exit 1
  fi
  echo "=== Session context ==="
  echo "No data root set yet — nothing was loaded, and that is correct, not broken."
  echo "This is where everything you write will live. Set it once:"
  echo "    python3 \"$REPO/shared/brain_root.py\" --set \"<the folder your notes live in>\" [--create]"
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
  RC_BODY="$(cat "$ROOT_CANON" 2>/dev/null)"
  if [ -n "$RC_BODY" ]; then
    TOTAL=${#RC_BODY}
    echo ""
    echo "--- true for everything ---"
    printf '%s\n' "$RC_BODY"
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
  echo "=== end session context ==="
  exit 0
fi

echo ""
echo "Standing notes from ${#CANON[@]} subject folder(s):"
SHOWN=0
for f in "${CANON[@]}"; do
  SUBJECT="$(basename "$(dirname "$(dirname "$f")")")"
  BODY="$(cat "$f" 2>/dev/null)"
  [ -n "$BODY" ] || continue
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

echo ""
echo "=== end session context ==="
exit 0
