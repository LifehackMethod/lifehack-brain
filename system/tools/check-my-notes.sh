#!/bin/bash
# check-my-notes.sh — did the August 11 bugs touch your notes?
#
# READ-ONLY. This looks at your files and tells you what it sees. It changes NOTHING,
# moves NOTHING, deletes NOTHING. Run it as often as you like.
#
# Run it:   bash system/tools/check-my-notes.sh
#
# Why this is a script and not a list of commands in a README: a block of commands copied
# out of a markdown file brings its backticks with it, and the shell reads those as
# something to run. The paste dies, you get a confusing prompt, and you cannot tell a
# broken paste from a real problem. One line, one script, one verdict.

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FOUND_SOMETHING=0

echo ""
echo "Checking your notes for the two bugs fixed on August 11."
echo "This reads. It never writes."
echo ""

# ── where do your notes live? ───────────────────────────────────────────────────────
NOTES="$(python3 "$HERE/system/tools/cowork-ingest/pipeline.py" brain-root --quiet 2>/dev/null)"
if [ -z "$NOTES" ] || [ ! -d "$NOTES" ]; then
  echo "I could not work out where your notes live, so I stopped rather than guess."
  echo ""
  echo "  Fix: python3 system/tools/cowork-ingest/pipeline.py brain-root --set <your folder>"
  echo ""
  echo "Nothing was checked. Run this again afterwards."
  exit 1
fi
echo "Your notes: $NOTES"
echo ""

# ── 1 · notes filed under the wrong name ────────────────────────────────────────────
# A pad belongs at memory/<your corpus>/<pile>/scratchpad.md. The bug wrote <your corpus>
# as the name of the TAG FILE instead. Your corpus names are the folders under
# state/projects/ — anything in memory/ that is not one of those is stranded.
echo "1. Are any notes filed under the wrong name?"
if [ ! -d "$NOTES/memory" ]; then
  echo "   No memory/ folder yet — nothing to check. You are fine."
else
  KNOWN=""
  if [ -d "$NOTES/state/projects" ]; then
    for p in "$NOTES/state/projects"/*/; do
      [ -d "$p" ] && KNOWN="$KNOWN $(basename "$p")"
    done
  fi
  STRANDED=""
  for m in "$NOTES/memory"/*/; do
    [ -d "$m" ] || continue
    name="$(basename "$m")"
    case " $KNOWN " in
      *" $name "*) : ;;
      *) STRANDED="$STRANDED $name" ;;
    esac
  done
  if [ -z "$STRANDED" ]; then
    echo "   No. Every folder in memory/ matches a corpus you actually started."
  else
    FOUND_SOMETHING=1
    echo "   YES — these folders in memory/ do not match any corpus you started:"
    for s in $STRANDED; do
      n="$(find "$NOTES/memory/$s" -name scratchpad.md 2>/dev/null | wc -l | tr -d ' ')"
      echo "      $s   ($n notes file(s) inside)"
    done
    echo ""
    echo "   Your notes are in there and are perfectly readable. Nothing was deleted."
    echo "   To bring them across, COPY (do not move) into the right folder, look, then"
    echo "   delete the old one later if you want to:"
    echo ""
    echo "      cp -R \"$NOTES/memory/<wrong-name>/\"* \"$NOTES/memory/<your-corpus>/\""
  fi
fi
echo ""

# ── 2 · notes that were dropped and cannot come back ────────────────────────────────
# A pad with no dated "### YYYY-MM-DD" block has never had an entry written into it.
# On a pile you actually worked, that means your rulings were dropped on the way to disk.
echo "2. Were any notes dropped entirely?"
EMPTY=""
while IFS= read -r f; do
  [ -n "$f" ] || continue
  grep -q '^### 2' "$f" 2>/dev/null || EMPTY="$EMPTY$f"$'\n'
done < <(find "$NOTES/memory" -name scratchpad.md 2>/dev/null)
if [ -z "$EMPTY" ]; then
  echo "   No. Every notes file has at least one dated entry in it."
else
  FOUND_SOMETHING=1
  COUNT="$(printf '%s' "$EMPTY" | grep -c . )"
  echo "   MAYBE — $COUNT notes file(s) have no dated entry at all:"
  printf '%s' "$EMPTY" | sed 's|^|      |'
  echo ""
  echo "   If you never worked those piles, this is correct and expected — ignore it."
  echo ""
  echo "   If you DID work them, those rulings were dropped before they reached disk."
  echo "   They were never written anywhere, so nothing can recover them — not this"
  echo "   script, not a better one, not later. Re-screening those piles is the only"
  echo "   way back. Sorry. Knowing which ones beats not knowing anything went missing."
fi
echo ""

# ── 3 · things you approved that never got filed ────────────────────────────────────
echo "3. Did anything you approved get parked instead of filed?"
PROPS="$(find "$NOTES/desks" -path "*records/proposals/*" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')"
if [ "$PROPS" = "0" ]; then
  echo "   No. Nothing is sitting in a proposals folder."
else
  FOUND_SOMETHING=1
  echo "   YES — $PROPS file(s) are sitting in records/proposals/."
  echo ""
  echo "   These are things you already said yes to. The yes is recorded inside each file."
  echo "   The old design parked them waiting for a second step that was never built."
  echo "   They are not lost. Read IF-YOU-RAN-THIS-BEFORE-AUG-11.md for what to do —"
  echo "   short version: move the ones still true in two years into the canon file of"
  echo "   the folder they belong to, and leave the rest as records."
  echo ""
  echo "   Do NOT move all of them into one file. Canon loads into every conversation"
  echo "   you have, so a file full of things that expire is worse than an empty one."
fi
echo ""

# ── 4 · the top-level canon file ────────────────────────────────────────────────────
echo "4. Do you have a canon file at the top?"
if [ -f "$NOTES/canon.md" ]; then
  echo "   Yes."
else
  FOUND_SOMETHING=1
  echo "   No. Make it with:  python3 system/tools/bootstrap.py"
  echo "   It never overwrites anything and is safe to run whenever."
fi
echo ""

# ── verdict ─────────────────────────────────────────────────────────────────────────
echo "──────────────────────────────────────────────────────────────"
if [ "$FOUND_SOMETHING" = "0" ]; then
  echo "Nothing to do. Your notes are where they should be."
else
  echo "Some things above need you. Nothing is urgent and nothing is lost"
  echo "except where it says so plainly."
fi
echo ""
echo "Full explanation: IF-YOU-RAN-THIS-BEFORE-AUG-11.md"
echo "This script changed nothing."
echo ""
