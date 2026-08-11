# PASS 2 — THE LANES (coverage check)

TRIPWIRE: this is a COVERAGE check against the ALREADY-VISIBLE board, not a re-interrogation. Don't re-ask what the surfaces settled.

The **10-lane board is already on the table** (rendered at the Pass 0→1 boundary, maintained through Pass 1 —
`references/lane-board.md`). Pass 2 is where you **verify coverage against that visible board**: every lane's
data is showing, so you're no longer walking lanes blind — you're checking that what's live on the board got
addressed, and catching the shadow stuff a lane would have but no surface showed. Still interrogative — surfacing
gaps, not concluding.

## Do this
1. **Re-render the board (refreshed)** with everything Pass 1 added, so the person sees all 10 lanes current in one
   glance. **Any lane still flagged ⚠ truncated is an OPEN data hole — surface it loudly, never call it covered.**
2. For each lane: covered by what we surfaced, or a GAP? An ANCHOR lane with no move yet is a gap to close; a
   quiet 🟡 TRIGGERED lane with nothing live is **correct — leave it** (do NOT invent a move; that deep-mine is
   the weekly skill's job).
3. **Ask only the GAPS** — never one-question-per-lane (that's the mechanical failure mode; the board is the
   silent filter, not the question structure). A well-covered lane gets nothing. Bold lead-in + refresher +
   best-guess, same style as Pass 1.
4. **Round up into the scratchpad** (prune/update/add in context; the scribe persists at the boundary).

## Gate — with a suggestion
**"Another round, or move on to logistics? — I suggest [X] because [Y]."** Only their word advances.

STOP-CHECK: refreshed board shown; every lane covered or its gap asked; no ⚠ truncated lane left unflagged; world model current → **fire the gear-2 scribe (sonnet) to persist the scratchpad (background).**

NEXT: load and follow `prompts/03-logistics.md`.
