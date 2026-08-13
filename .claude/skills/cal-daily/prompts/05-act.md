# PASS 5 — ACT (the clerk drains the CONSOLIDATED ledger, then closes)

> **Content root (Drive).** Every relative `desks/…`, `records/…`, `state/…` path in this prompt is
> **content** under the Drive root
> `<notes>/`, never the
> code clone. When launched from the clone, write content (incl. the diary log) to that Drive root.

TRIPWIRE: drain the **consolidated WRITE-LEDGER from Pass 4.5** (the whole-scratchpad harvest the person confirmed) — NOT
just today's dominoes. Unsure a row was confirmed? Ask — don't write on assumption.

The writing is **gear-2 work**: the person confirmed the expanded ledger in Pass 4.5, so there's no human left in this loop —
draining it is mechanical. **You (main session) do NOT run the `gws` writes inline** (that's the round-trip wait we
killed). You hand the confirmed ledger to ONE background **clerk** sub-agent, and relay its receipt.

## Do this
1. **Take the CONSOLIDATED WRITE-LEDGER from Pass 4.5 (binary gate).** It already holds every durable item across four
   buckets — CALENDAR · TASKS · DURABLE RECORDS · DAILY WIN — each row ❌, dedup applied. Do NOT rebuild it from the
   dominoes; that consolidation is the whole point (it's what stops flights/plans/findings from being lost).
2. **Fire the CLERK (gear-2, sonnet, fire-and-collect).** Spawn ONE sub-agent — **model: sonnet** set explicitly — and
   **embed the ENTIRE ledger in its prompt** (it cannot see this chat — embed, never "go read it"). The clerk is **THE
   FORENSIC CLERK: never moves in silence; every write declared, every skip named; a silent write or a claimed-but-
   unmade write is the cardinal sin.** Its instructions, by bucket:
   - **CALENDAR → Agent Ops calendar ONLY** (id in `<notes>/desks/cal/skill-refs/user-canon.md`), **never `primary`**
     (`system/hooks/guard_calendar_writes.sh` fires inside the sub-agent and denies a write to any calendar
     but the one you configured). Today's AND
     future-dated: `gws calendar events insert --params '{"calendarId":"<AGENT_OPS_ID>"}' --json '{"summary":...,"start":...,"end":...}'`.
   - **TASKS → topical Google Tasks list:** `gws tasks tasks insert --params '{"tasklist":"<LIST_ID>"}' --json '{"title":"..."}'`
     (resolve the list via `gws tasks tasklists list --params '{}'`). New durable to-dos only (dedup already applied).
   - **DAILY WIN → subtasks under the Life Map Daily Win parent.** Each confirmed domino becomes a child of the
     `✅ Daily Win:` task: `gws tasks tasks insert --params '{"tasklist":"$(python3 "$ROOT/shared/cal_config.py" --get goals_tasklist)","parent":"$(python3 "$ROOT/shared/cal_config.py" --get daily_parent_task)"}' --json '{"title":"<TAG — move>"}'`.
     This is the ONE allowed Life Map write — `guard_tasks_writes.sh` passes it BECAUSE it references the Daily Win
     parent. **Never** insert a non-Daily-Win Life Map task, touch the Weekly/Monthly/Yearly Win tasks, or delete anything.
   - **DURABLE RECORDS → files, not Google.** Findings / decisions / system-debt with no calendar/task home → write to
     `<notes>/desks/cal/records/`, `<notes>/desks/cal/state/`, or root `<notes>/state/tech-debt.md`. These are the items
     that vanished before — they MUST be filed.
     **DEFERRED TODAY block:** if the ledger contains a DEFERRED TODAY row, it goes in the diary stamp (`<notes>/desks/cal/diary/YYYY/MM/DD.md`) as a `### Deferred Today` sub-section — NOT to Tasks, NOT to the Life Map. Paste the block verbatim.
   - **READ-BACK GATE (un-fakeable):** after each write, **read it back** (`gws tasks tasks list` for the list/parent ·
     `gws calendar events list` for the window · re-read the file) and confirm it's really there **before flipping the
     row ❌→✅**. A write whose read-back fails stays **❌ with the stated reason** — never assume success from exit 0.
   - **Then close:** Cal's session detail → `<notes>/desks/cal/records/logs/<today>.md`; **stamp the diary**
     `<notes>/desks/cal/diary/YYYY/MM/DD.md` (a `## Cal Session` block or pointer, so the rollup sees it); update
     `<notes>/desks/cal/state/current.md` if standing state changed; **delete the session scratchpad**
     `<notes>/desks/cal/state/raw-vault/<today>/session-scratchpad.md` — **LAST, only after every row is ✅ or ❌-with-reason.**
   - **Return the filled WRITE-LEDGER** — every row ✅ (read-back-confirmed) or ❌-with-reason.
3. **Relay the receipt.** Present the clerk's returned ledger verbatim: every row ✅ or ❌-with-reason, grouped by bucket
   (incl. the Daily-Win subtasks now living under the Win). If any ❌, say so plainly and offer to retry that row.

STOP-CHECK: clerk fired with the full consolidated ledger embedded; every row ✅ (read-back-confirmed) or ❌-with-a-
stated-reason; Daily-Win subtasks written under the parent; durable records filed; scratchpad deleted **last**; receipt
relayed. No silent writes, no phantom successes, nothing durable lost.

(End of chain — no NEXT.)
