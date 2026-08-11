# PASS 1 — CLEAR THE SURFACES (email · calendar · task inbox)

TRIPWIRE: the overnight draft is a GUESS + a 4:10am snapshot — they may have changed things since. Deliberately incomplete.

Read `references/question-style.md` first. This pass clears **surfaces, not lanes** (lanes are Pass 2). Big-rocks /
"what iceberg are we about to hit." You SURFACE and tidy; you do NOT conclude (see THE LAW).

## Open with the cron TL;DR
**One paragraph:** what the 4am cron saw (counts) + what it thinks matters. Then the questions — nothing more elaborate.

## Build the world model from SOURCE, not the digest
The scratchpad seed is the overnight **digest** (`dominoes-draft.md` + the analysis lenses) — a summary, not the raw
truth. As you sweep, **fold the concrete INBOX FACTS into the scratchpad**: flight/booking confirmations, dates,
times, dollar amounts, confirmation numbers, who/what/when. A fact that lives only in the raw inbox (a flight
confirmation email) but never enters the world model is the exact failure that made a past run *doubt a real flight*
(it "verified" against the calendar, where the flight wasn't, instead of the inbox, where it was). **Corollary:** if
you find yourself re-reading a source mid-session for something that was already there at 4am, the scratchpad failed —
fix the scratchpad, don't paper over it with another read.

## Then interrogate, surface by surface (rounds the person controls)
Sweep **email** (inbox + snoozed), **calendar** (today → week ahead), and the **Google task inbox** (the unfiled list;
for already-prioritized lists read only the top). Per round:
- Ask a batch of **~8–10 questions** (never one at a time — he dictates by voice), **bold lead-in + a real one-clause
  refresher + a best-guess** each (see `question-style.md`). Recon-framed: "recon found X — confirm, or correct?"
- **Tidy as you go:** offer to archive email cruft (gated); **leave scripts / live threads IN the inbox**; flag personal-
  calendar clutter (read-only — the person clears it) but Cal CAN write the Agent Ops calendar; surface + triage the task inbox.
- **free/busy every calendar read.** `declined`/`cancelled` self-eliminate — don't surface them.
- **"Anything new since 4am?" → the LIGHT sweep, never a re-pull.** If they ask whether something popped in since the
  overnight pull, run `python3 system/tools/cal-light-sweep.py` (metadata-only — subjects/senders, no bodies, seconds).
  Fold anything real into the scratchpad. Do NOT re-run `cal-vault-pull.py` (the full verbatim re-ingest) for a quick check.
- **Round up the world model in context** (prune/update/add) before the next round — don't rewrite the scratchpad
  file mid-round; the scribe persists it at the pass boundary.

## Gate — with a suggestion (end every round)
Close each round with the user-turn boundary AND your read: **"Another round, or move on? — I suggest [X] because [Y]"**
(e.g. "I suggest another round, I'm still thin on your calendar" / "I suggest we move on"). Only their word advances.

STOP-CHECK: all three surfaces swept; the person said move on; world model current → **fire the gear-2 scribe (sonnet) to persist the scratchpad (background) at this boundary.**

NEXT: load and follow `prompts/02-lanes.md`.
