# PASS L1 — CLOSE (write the diary + the open loops, then stop)

TRIPWIRE: everything confirmed in Pass L1-plan gets written here, and nothing before this pass writes
anything. **These are local file writes only — no Google I/O, so they run inline, in the main session,
right now.** The full flow hands writes to a background "clerk" sub-agent specifically to hide a slow
Google round-trip; there is no round-trip here, so doing the same thing would add a moving part for no
benefit. Write directly.

## Do this

1. **If the person gave real backfill about yesterday** (Pass L1-lookback), and yesterday's diary does
   not already carry a `## Human Delta` block for today's date (check first — don't double-stamp):
   - If yesterday's diary file doesn't exist yet, create its scaffold first:
     `python3 "$ROOT/system/tools/cal-diary-capture.py" --date {yesterday, YYYY-MM-DD}`. This is
     mechanical and fail-soft — in Layer 1 every source section will read `source-unavailable`, which
     is correct and honest, not a bug.
   - Append, at the end of the file:
     ```markdown
     ## Human Delta — verified {today, YYYY-MM-DD}
     {the backfill, in the person's own words as far as possible — what actually happened, corrections
     to anything the machine section got wrong or missed}
     ```
   - If there was no real backfill (first day, or nothing to add), skip this step entirely — do not
     stamp an empty Human Delta just to have stamped one.

2. **Write today's diary scaffold:**
   `python3 "$ROOT/system/tools/cal-diary-capture.py" --date {today, YYYY-MM-DD}`. Same fail-soft
   behaviour — the machine sections read `source-unavailable`, honestly, because Layer 1 has no
   calendar/task/journal source to pull from. Do not treat that as an error to work around.

3. **Append today's plan to today's diary file**, after the machine section:
   ```markdown
   ## Today's Plan — set {today, YYYY-MM-DD}
   {the confirmed ranked list from Pass L1-plan, in order}

   ### Not Today
   {the not-today list, one line each, or "— none" if nothing was held back}
   ```
   This is a distinct section from `## Human Delta` — a Human Delta verifies a day already lived; this
   is the plan for a day not yet lived. Don't conflate the two headings.

4. **Update the open loops file**, `<notes>/state/open-loops.md`. If it doesn't exist yet, create it
   with this shape:
   ```markdown
   # Open Loops

   started, not finished.

   ## Open

   ## Resolved
   ```
   Then:
   - **New or still-open items** (the "Not Today" list, and anything from lookback still unresolved) →
     one line each under `## Open`: `- {YYYY-MM-DD} [cal] {description}`. Check first — never add a
     line that duplicates one already there in substance.
   - **Anything the backfill confirmed as done** → move its line from `## Open` to `## Resolved`,
     appending when it closed: `- {YYYY-MM-DD} (opened {original date}) [cal] {description}`.
   - **Deletion-only discipline on `## Open`**, matching how the rest of this system treats a running
     ledger: closing an item means moving its line out, never annotating it "✅" in place. A line left
     in `## Open` marked done gets re-asked-about tomorrow, which is the exact waste this avoids.

5. **Confirm what was written, plainly, in one short paragraph** — which files changed, and what's now
   in each (today's plan, yesterday's Human Delta if any, the open-loops delta). This is the whole
   receipt; there is no ledger drain to relay because there was no ledger — the writes above are all of
   it.

STOP-CHECK: today's diary carries the confirmed plan · yesterday's diary carries the Human Delta if and
only if there was real backfill · open-loops.md reflects both the new not-today items and anything
resolved · the person was told plainly what got written.

(End of the Layer 1 chain — no NEXT. The next time this skill runs, Pass 0 (`00-preflight.md`) decides
the layer again from scratch.)
