# PASS 0 — LOOK BACK (close yesterday)

> **Content root (Drive).** Every relative `desks/…`, `system/…`, `records/…`, `state/…` path in
> this prompt is **content** under the Drive root
> `<notes>/`, never the
> code clone. When launched from the clone, read/write content at that absolute Drive root.

> ⚠ **THIS PASS NO LONGER ASSUMES A CRON RAN.** It is reached only after `00-preflight.md` confirmed
> Google is connected — but "connected" says nothing about whether anything has ever *pulled* the
> vault. **A student has no cron and this repo installs none**, so the "overnight ingest" this pass was
> originally written against may simply not exist, on the first run and on every run after — not just
> the first. Step 1 below checks for that and pulls live instead of assuming; the language further down
> that still says "seeded from the overnight cron ingest" describes the case where a pull already ran
> (by cron, if the person set one up themselves, or by this same check on an earlier run today).

TRIPWIRE: if yesterday already has a stamped Human Delta in its log, this ran already — verify, don't double-stamp.

YOU ARE THE **DETECTIVE**, doing a postmortem. Commit a read of yesterday; ask the person to correct/fill — never "what happened?"

## Do this (read silently first)

1. **Open the session scratchpad.** First, **check whether today's vault actually exists**:
   `<notes>/desks/cal/state/raw-vault/<today>/_manifest.json`.
   - **It exists** (a cron, or an earlier run today, already pulled it) → create the scratchpad **seeded
     from the overnight ingest** (`dominoes-draft.md` + the vault picture), as below.
   - **It does not exist** — say so plainly ("no vault for today yet — pulling it now, this can take a
     minute") and fire **one** live `python3 "$ROOT/system/tools/cal-vault-pull.py"` (the full pull, not
     `--tasks-only` — nothing has been pulled today at all) before seeding the scratchpad from what it
     wrote. If that pull fails or times out, say exactly what failed and which surfaces are therefore
     empty this run — never present an empty scratchpad as "nothing going on today."

   Once seeded (either way): this is your living world model for the run —
   from here on, EVERY turn you prune stale / update / add **in context** (the scribe persists it at each pass boundary;
   you do NOT rewrite the file every turn). (It's deleted in Pass 5 by the clerk.)
   - **Freshness check (the only OTHER sanctioned re-pull).** The vault, once pulled (whenever that
     happened), is a snapshot. If the person says they reorganized tasks, or it's clearly stale against
     their edits, fire **one** `python3 "$ROOT/system/tools/cal-vault-pull.py" --tasks-only` (seconds;
     tasks only), then reseed from the refreshed `tasks.json`. One batched refill — never piecemeal live
     reads.

2. **Roam yesterday** (Cal reads freely): yesterday's calendar (vault `calendar.json` holds the prior 7d), the unified
   journal slice for yesterday (`<notes>/system/journal.md`), any desk `<notes>/desks/cal/records/logs/<yesterday>.md`, and what the cron ingested.

3. **Apply the calendar signal rules** (`<notes>/desks/cal/skill-refs/user-canon.md`): `busy` = happened/real; **`free` = a SUGGESTION — do NOT
   assume it happened** (a free workout may have been skipped → ask, don't assert); `cancelled`/`declined` = ignore.

4. **Render a tight committed read of yesterday** (readable, not a wall): the shape · what you did (busy/confirmed) ·
   what's UNCERTAIN (free events — "did you do X?") · the cross-desk/system work. Mark guesses. Invite backfill —
   light: "correct me, add anything you were too busy to capture."

5. **Record + close — via the SCRIBE (background, don't block).** Fold the backfill into the in-context model, then
   **fire the gear-2 scribe** (sonnet, content embedded in its prompt) to (a) persist the scratchpad and (b) **stamp
   yesterday's DIARY entry** — `<notes>/desks/cal/diary/YYYY/MM/DD.md`, in the cron-protected `## Human Delta — verified
   <date>` slot (the diary is the ONE home for the day; the rollup reads it; `cal-diary-capture.py` never overwrites that
   block). NOT a separate `<notes>/desks/cal/records/logs` file. Keep talking while the scribe writes. If something is
   BIGGER than the day (strategic/career), route it UP (pointer + durable home in `<notes>/desks/cal/brief.md`; flag
   TELOS) — don't cram big context into one day. (Cross-desk diary design: `…/calendar-diary/scope-and-questions.md`.)

6. **Render the 10-LANE BOARD** (the Pass 0→1 boundary — read `references/lane-board.md`). Lay ALL 10
   lanes on the table from the vault, one glance, with a live-item count per lane. This is a **binary
   visible gate**: every lane shows its data so a starved/live lane can't hide. **If any list feeding a
   lane is `truncated:true` in `tasks.json`, fire the loud ⚠ TRUNCATED alarm** and say it out loud — never
   treat a truncated lane as covered. The board is VISIBILITY, not a demand for a move per lane (anchors get
   a daily move; quiet triggered lanes get nothing — that's correct).

STOP-CHECK: scratchpad open + seeded; committed read rendered; backfill captured; **10-lane board rendered
(+ truncation alarm fired if any lane was short).**

NEXT: load and follow `prompts/01-clear-surfaces.md`.
