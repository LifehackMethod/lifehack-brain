# Information Ingestion & Interpretation — history

> **History file — archived text, not live guidance.** Created 2026-11-14 (fine-china edit pass, round three
> 'lowerbooks'). Each passage below was moved word for word out of `system/information-ingestion-interpretation.md` (Batch 4 item 3: retired and
> struck text goes to history, never deleted). Line numbers are those of the frozen copy
> `freeze-2026-11-14/information-ingestion-interpretation.2026-11-14.md`. Read the live file for what is true today.

## G2-48 · moved 2026-11-14 · frozen L53-65

Reason: the 2026-08-15 correction chain, restated in present tense in the live file (K12; Batch 4 item 3). Line 53's opening words (the tasks/calendar writers ship) stay live.

````
  — both ship here and are real, runnable janitors (`--sync`, `--dry-run`, `--self-test`). ⚠
  **CORRECTED 2026-08-15 (T9.7d stale-claim sweep) — the two sentences this replaces were wrong
  in two separate, compounding ways.** First: **the email-side writer DOES ship in this repo** —
  `shared/tools/email_summary_sync.py` is the janitor `shared/tools/email_service_read.py` (the
  READ adapter) reads from; see `system/schemas/email-summary-schema.md` for the full store
  contract. Second: **this repo does have a scheduler** — `system/tools/pulse.sh` (the heartbeat
  daemon) and `system/tools/install-schedulers.sh` (the OS-scheduler installer) both ship, and
  `system/jobs.md` carries a real `email-summary-write` row (10800s) that calls the
  janitor. On a fresh install, before `install-schedulers.sh` has been run on a machine, or
  before a Google account is connected, every email read still returns `MISS-NEW` ("no record
  for this thread") — that remains the correct, by-design state of an unpopulated store, never a
  broken adapter; it is just no longer because "nothing populates it," it is because nothing has
  populated it YET on that particular install.
````

## G2-53 · moved 2026-11-14 · frozen L126-131

Reason: Batch 2 item 1, 2026-11-13: no web exception — web fetch and search pass the whole Sentinel pipeline. The original reason (research cost, egress) is kept here, not lost (canon). Line 126's opening words (the .txt/.md and Doc-export gating) stay live.

````
  (the trusted-zone allowlist plus the `.txt`/`.md` and `drive files export` arms). **Web fetch/search is a
  NAMED, ACCEPTED exception** — it is scrubbed (L0) + injection-scanned (`system/tools/safe_input.py`) +
  egress-capped (`system/hooks/enforce_egress_allowlist.sh`), but not `/tmp/rdr` reader-isolated. By the
  adopted security posture (structural least-privilege + human-gated actions + EGRESS filtering beat heavy
  input-side isolation — a finding inherited from the system this doc was ported from), that is sufficient,
  NOT a gap to close.
````
