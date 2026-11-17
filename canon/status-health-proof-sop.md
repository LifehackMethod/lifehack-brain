---
title: "Status, Health and Proof"
status: approved
approved_by: "Enver on 2026-11-16, round four's 'land it'"
last_reviewed: 2026-11-16
purpose: "How the harness proves a part works, records that proof, and labels each part LIVE, PARTIAL or DORMANT."
read_when: "A part was built or changed and someone is about to call it working; a label on the map, manual or an element file is being written or checked; a claim's freshness is in doubt."
history: "canon/status-health-proof-sop.history.md"
---

# Status, Health and Proof

## Read This First

- **Purpose:** a part of the harness counts as working only when a check watched it work and left a dated receipt (a
  small record the checking code writes: what was checked, when, and the result). This SOP says how that proof is
  made, where it is kept, and how a label — LIVE, PARTIAL or DORMANT — points to it and goes stale on its own. A
  future session reading "LIVE" can then trust the word, because a receipt earned it, not a model's sentence.
- **Use it when:** a session built or changed a part (a guard or other hook, a tool, a skill, a desk) and is about to
  say it works; when writing or checking a label on the map, the manual (`system/organism/manual.md`) or an element
  file (`system/organism/elements/`); when a status claim may be out of date.
- **Don't use it when:** you need the detail of how a scheduled job proves itself. That is canon in
  `canon/cron-jobs-sop.md`; this SOP only points there (The Procedure, *A scheduled job*). What a session prints at start, including the one-line job-health line, is `canon/context-injection-sop.md`'s; this SOP covers only what the line proves.
- **Covers / doesn't cover:** covers proof, receipts, the session-start health line, and labels; the tile contract is `canon/status-emission-sop.md`'s. Doesn't
  cover how a screen draws a tile (rendering belongs to whoever builds the view) or build conformance in general
  (`canon/build-conformance-sop.md`).
- **How this SOP changes:** only through Enver's ruling; superseded text moves to the archive named in the header.
- **Which situation are you in?**
  - Proving a scheduled job → The Procedure, *A scheduled job*.
  - Proving a guard, tool, skill or desk → The Procedure, *Any other part*.
  - Writing or checking a label → The Procedure, *A label*.

## Desired Outcome

- Every part carries one label — LIVE (a dated check watched it work, inside its window), PARTIAL (works in part, or
  held only by an honor system), or DORMANT (built, not in use) — with the date of the check behind it and a pointer
  to that check's receipt.
- Every check speaks (the speaking cascade): it writes a dated receipt; session start reads receipts for freshness;
  the person finishes the chain; the weekly human-validated roll-up catches what the chain itself misses.
- A label past its window (how long a receipt stays credible: the check's intended rhythm: `stale_after_s` on a tile, `stale_after_h` on the guard receipt) reads
  "unproven", and stays on the page.
- A proof names what it did not test in the same place as what it proved.
- **How to check:** pick any LIVE label; follow its pointer to a receipt the checking code wrote; the receipt's date is
  inside the window and its result matches the label.

## Before You Start

- Read `canon/cron-jobs-sop.md` §4, §8, §10, §11a if a scheduled job is involved.
- Read `canon/hook-contract.md` (Deploy & Verify, "Watch it fire") if a hook is involved.
- Know the machinery (paths from the plugin root):
  - `system/tools/job-run.sh` — runs a job, checks its artifact, writes its receipts.
  - `system/tools/health_line.py` — the session-start health line.
  - `system/tools/emit_status.py` and `system/tools/status-tile.lib.sh` — write tiles (small status files in `<brain>/status/`, the brain folder's root).
  - `system/tools/registered-guard-fire-test.py` — enumerates registered guards from the registration file and fires
    each one.
  - the guard fire-test job (`guard-fire-test-run.sh`, row in `system/jobs.md`) — writes the guard receipt
    `~/.config/lifehack/guard-fire-test/last-run.json`.
  - `system/tools/organism/label_checker.py` — computes labels by firing and stamps them (`write-labels`).
  - `system/tools/tests/job-sim.sh` — the job test rig.
  - `system/tools/mirror_line.sh` — the session-start MIRROR line: reports whether local branches match their remote,
    a health signal the plugin ships; it reports and blocks nothing. Git details live in the person's GitHub workflow,
    not here.
- Outside material, including anything a scheduled job reads, goes through the Sentinel (`canon/security-canon.md`).

## Principles

Evidence tiers are canon's, as `canon/canonical-principles-sop.md` THE FRAME defines them.

- **Watch it work.** Nothing counts as existing, done or true until you have watched it produce an outcome it could
  not produce if it were broken. Why: most recorded failures gave the same signal whether the thing worked or not.
  Change if: a class of part is shown to fail loudly on its own. Evidence: CANDIDATE as a sentence, with a REPRODUCED
  count behind it (`canon/canonical-principles-sop.md` THE FRAME; the census is §16).
- **Ran is not succeeded.** Proof is a check on the outcome, not an exit code. Why: exit-0-means-fine is a silent failure the failure-mode census counts 166 times. Change if: a counter-example is seen. Evidence: OBSERVED, count REPRODUCED
  (`canon/skill-building-sop.md`, census [F2]).
- **The checking code writes the receipt; a model does not.** Why: an agent's account of its own work is a
  self-report, and a record the AI writes is the AI grading itself. Change if: a model-written record is shown to stay
  accurate across blind sessions. Evidence: OBSERVED (`canon/canonical-principles-sop.md`, the
  step-runner and mode 8).
- **Done means wired and seen refusing once.** A guard, skill or desk is seen refusing a planted bad input before it
  is called working; a checker with no recorded refusal is suspect. Why: a check not yet seen refusing looks the same
  as a dead one. Change if: a part type has no bad input to refuse. Evidence: OBSERVED (`canon/skill-building-sop.md`).
- **Registered is not live.** A hook can be registered and do nothing; a file can exist and be dead (not committed as
  executable). The label comes from firing it. Why: hooks that passed existence checks were dead on a fresh clone.
  Change if: registration starts implying execution. Evidence: OBSERVED (`system/tools/health_invariants.py`, the
  2026-08-23 correction).
- **Missing, present-but-dead and could-not-tell are three facts.** Each is reported by its own name; an untested case
  reads as untested, not as passing; a stand-down reads as a stand-down. Why: folding them hides the failure. Change
  if: a reader needs only two. Evidence: OBSERVED (`registered-guard-fire-test.py` verdicts; `status-tile.lib.sh`).
- **A dead detector and a clean system look the same.** Every checker carries a planted-fault self-test that proves it
  catches and names the fault. Why: a check not yet seen failing can't be trusted, and the checker is often the least
  checked file. Change if: a checker is proven by an independent one. Evidence: REPRODUCED
  (`canon/skill-building-sop.md`; `job-sim.sh --bite`).
- **The list of things to check comes from the registry at run time.** Why: a hand-typed list missed guards,
  including a security guard. Change if: the registry itself is shown incomplete. Evidence: OBSERVED
  (`registered-guard-fire-test.py`, founding measurement).
- **Derive staleness; don't ask the producer.** A reader compares a receipt's date with its window; the producer
  doesn't claim "fresh". Why: you don't ask the fish whether the fish is fresh. Change if: a producer's clock is the
  only one available. Evidence: OBSERVED (`emit_status.py`).
- **Freshness is not proof of work.** A fresh artifact proves nothing about its content; the window applies to the
  claim, the check applies to the content. Why: freshness-as-proof was refused at the job door. Change if: a part's
  only output is its timestamp. Evidence: OBSERVED (`canon/cron-jobs-sop.md` §2 principle 1, §7).
- **A job that has a tile writes it on every outcome, failure included.** It writes the tile from an exit trap, without failing because
  of it; tiles go through the one tile writer (`emit_status.py`; `status-tile.lib.sh` is its shell front door), one producer per tile. Why: a silent night is what a missing tile looks
  like. Change if: a part has no glance to give. Evidence: OBSERVED (`status-tile.lib.sh`).
- **The person reading the output is the real detector.** A check earns its place only if its result is read. Why: an
  unread check is a dead detector. Change if: an automated reader is shown to act on it. Evidence: RESEARCHED
  (`canon/canonical-principles-sop.md` §15).
- **A person's own checks follow the same proof.** Any health check a person adds in their own code (business logic)
  writes a dated receipt from code and carries a label that goes stale like any other. Why: the shared layer sets how
  proof works; personal checks plug into it. Change if: a personal check needs a proof the shared layer can't carry.
  Evidence: CANDIDATE.
- **Friction is proportional.** Use the layers of friction, and reserve hard blocks for certain things; no invented limits. Why: a hard block that misfires stops real work. Change if: a lighter layer is shown to fail where a hard block is reserved, or a hard block is shown to stop real work in a case the person has not named. Evidence: OBSERVED (`canon/build-conformance-sop.md` §5.11).
- **A part is LIVE only if a dated check watched it work.** Why: the label is what a blind session trusts. Change if:
  a part type is found that can't be watched working. Held by: `label_checker.py`'s dated stamp and receipt pointer (References). Evidence:
  CANDIDATE — approved by Enver, 2026-11-14.
- **Proof is a receipt written by the code that ran the check — what, when, result.** Why: a sentence a model wrote is
  a self-report. Change if: a check type is found that can't write a receipt. Held by: the checker that writes it
  (`job-run.sh`; the guard fire-test job). Evidence: CANDIDATE — approved by Enver, 2026-11-14.
- **A label points to its receipt and reads "unproven" once past its window.** Why: a claim about the present expires.
  Change if: a part type is found whose claims don't expire. Held by: whatever reads the label (the session line,
  `label_checker.py`). Evidence: CANDIDATE — approved by Enver, 2026-11-14.
- **The label words are LIVE, PARTIAL and DORMANT.** TARGET is not a label (intent goes on the debt ledger); "LIVE
  (honor)" is not a label — a part whose main promise only an honor system holds is PARTIAL. Why: one vocabulary,
  earned by checks. Change if: a part state is found that none of the three words describes. Held by:
  `label_checker.py`. Evidence: CANDIDATE — approved by Enver, 2026-11-14.

## The Procedure

### A scheduled job

1. **Do:** follow `canon/cron-jobs-sop.md` §4, §8, §10 and §11a.
   - **Why:** the job case is canon already: the runner checks the artifact against the row's outcome check and only
     then moves `last-success`; the session-start line and the break-and-recovery texts are the tracking; a job that has a tile writes it on every outcome (`canon/status-emission-sop.md`).
   - **Expect:** receipts in `~/.config/lifehack/state/jobs/<job>/` (`last-run`, `last-success`, `log`, `errors/`).
   - **Check:** `bash system/tools/install-schedulers.sh --check-row <job>` prints PASS, and the session line names
     the job OK.

### Any other part (a guard or other hook, a tool, a skill, a desk)

1. **Do:** run the check that watches this kind of part work:
   - a guard or other hook — the guard fire-test fires it with a case it has to refuse;
   - a tool — watch a live path call it;
   - a skill — it refuses a planted bad input, then one real run with the person in the chair;
   - a desk — the desk door's checks pass (`canon/desk-building-sop.md` §5), and a planted fault (a card that does not parse, a pointer to a missing file) is refused by name; its tile comes from the job that produces it.
   - **Why:** each is the cheapest outcome the part could not produce if it were broken.
   - **Should / may:** the check should watch the part work (see Principles).
   - **Expect:** the part refuses the bad input and produces the outcome.
   - **Check:** you see the outcome yourself; a report of it doesn't count.
2. **Do:** let the checking code write the receipt: what was checked, when, and the result.
   - **Why:** the receipt is what the label points to.
   - **Expect:** a dated receipt written by the checker (for guards, `~/.config/lifehack/guard-fire-test/last-run.json`).
   - **Check:** open it; the date is today and the result matches what you watched.
3. **Do:** name what the check did not test, in the same place as the result.
   - **Why:** a partial nobody writes down becomes a pass by default.
   - **Check:** the receipt or its report names the untested cases.

### A label

1. **Do:** run `label_checker.py write-labels`; it computes each label by firing and stamps the element's
   AUTO-COMPUTED block (the machine-written part of each entry in `system/organism/manual.md`) with the label, the
   date and the receipt pointer.
   - **Why:** the base label is machine-computed; a hand-set label drifts from the code, and so does a hand-updated
     pointer.
   - **Should:** where several checks back one element, the weakest result sets the label, because the label has to
     stay true for the whole element.
   - **Expect:** `LIVE · <date> · <receipt>` (or PARTIAL / DORMANT) in the block.
   - **Check:** the label matches the receipt, and the receipt is inside its window.
2. **Do:** when reading a label, compare its date with its window.
   - **Why:** past the window the claim reads "unproven" and stays on the page.
   - **Check:** an expired label shows as unproven, not as LIVE.

## When Something Goes Wrong

- **If the part can't be seen failing:** build the failing state first, then check it.
- **If a receipt is missing or corrupt:** refuse it and name the file; corrupt state doesn't "start fresh".
- **If a rig reports green from a run whose hooks failed to start:** the result is invalid, whatever the summary calls
  the failures.
- **If a label disagrees with the code:** recompute it by firing; don't hand-patch the label.
- **If a checker is suspect:** plant a known fault and confirm it catches and names it.
- **If the health line is quiet while something is failing:** check the job row is enabled — the line reads enabled
  rows only.
- **If the scheduler itself stops:** no text goes out, and the weekly human-validated roll-up is the designed catch.
- **To undo:** a label is recomputed, not edited back.
- **Stop and ask the person when:** a fix would go around a checker, or a change would add or alter a must.

## Don't Retry

- **Exit 0 means fine** — a silent failure the failure-mode census counts 166 times. Proof: `canon/skill-building-sop.md`, census [F2].
- **A separate "status runner"** — it duplicates the health line and the alert path. Proof: the round-three job-health research.
- **Hand-typed guard lists** — they missed guards, including a security guard. Proof: `registered-guard-fire-test.py`.
- **Hardcoded registration paths** — they caused a false downgrade; resolve a priority list and print which source
  won. Proof: `registered-guard-fire-test.py` header.
- **Existence or size as liveness** — dead hooks passed. Proof: `health_invariants.py`, the 2026-08-23 correction.
- **Exit-code-only block detection** — a block on stderr with a non-2 exit blocks nothing (the dark trap). Proof:
  `canon/hook-contract.md`.
- **Presence-grade checks** (`"rc":0`, `^.+$`, mtime alone, `^done$`) — refused at the job door. Proof:
  `canon/cron-jobs-sop.md` §4.
- **Hand-rolled shell tile writers** — each drifted from the envelope. Proof: `status-tile.lib.sh` replaces them.
- **A scheduled check nothing reads** — the guard fire-test ran green while nothing read it. Proof: `system/jobs.md`,
  the guard fire-test row.
- **A banner that grows** — rich health reporting at session start became unreadable; the line stays one line.
  Proof: `health_line.py`.
- **A model-in-the-loop hook as a judge** — slow, and flagged nothing real. Proof: `canon/hook-sop.md`.
- **A monitor that can fail the same way as what it watches** — disqualifying. Proof: a self-monitoring project record.
- **A label scheme the wiring can't carry** — the grammar said machine-computed while nothing stamped. Proof: a round-three world-model finding.
- **Clearing a rare failure with a handful of trials, assuming a cap is a price, freezing an instrument** — each
  failed. Proof: `canon/canonical-principles-sop.md`, the do-not-retry list.

## Open Tensions

- **Off-but-failing job rows** and the session line. Side A protects a quiet line; side B surfaces every failure.
  Status: open — surfaced to Enver, not resolved here.
- **A deadman on every hook vs no meta-checker.** Side A catches a silent hook; side B avoids a checker that fails
  like what it checks. Status: open — surfaced to Enver, not resolved here.
- **Acceptance can undo a verification.** Later work moves the files a finished check verified. Side A protects
  finished work staying finished; side B protects receipts staying true. Status: settled by Enver's ruling
  (2026-11-16): a check of committed code reads "unproven" when a file it covers has a newer commit on origin;
  a check of host state ages by its window only.

## Pointers

- **Rulings behind this SOP:** Enver's gate rulings of 2026-11-14, stated in plain words in Principles: a part is
  LIVE only if a dated check watched it work; proof is a receipt the checking code writes; a label points to its
  receipt and reads "unproven" past its window; the label words are LIVE, PARTIAL and DORMANT.
- **Evidence:** `canon/canonical-principles-sop.md` (THE FRAME; tiers and decay), `canon/cron-jobs-sop.md`,
  `canon/hook-contract.md`, `canon/hook-sop.md`, `canon/skill-building-sop.md` (failure census),
  `canon/desk-building-sop.md`.
- **Tiles:** the tile envelope and status words live in `canon/status-emission-sop.md`.
- **Words used here:** terms are defined in this SOP, each in one line where first used.

## History

- 2026-11-14 — DRAFT written from the approved template, on Enver's gate rulings of 2026-11-14; revised the same day
  on review.

## References (work in progress)

Every real thing this SOP points at, one line each. Paths are relative to the harness repo. Entries marked **not built yet** are slots for code the SOP describes that does not exist yet.

- `system/tools/job-run.sh` — runs a job, checks its artifact, writes its receipts.
- `system/tools/health_line.py` — the session-start job-health line.
- `system/tools/emit_status.py` and `system/tools/status-tile.lib.sh` — write tiles (`canon/status-emission-sop.md`).
- `system/tools/registered-guard-fire-test.py` — enumerates registered guards and fires each one.
- `system/tools/guard-fire-test-run.sh` — the guard fire-test job; writes `~/.config/lifehack/guard-fire-test/last-run.json`.
- `system/tools/organism/label_checker.py` — computes labels by firing and stamps them (`write-labels`).
- `system/tools/tests/job-sim.sh` — the job test rig.
- `system/tools/mirror_line.sh` — the session-start MIRROR line; reports, blocks nothing (a sign).
- `system/organism/manual.md` — the manual whose AUTO-COMPUTED blocks carry labels.
- `system/jobs.md` — the job rows.
- **not built yet:** the weekly guard fire-test job switched on. Serves: "Green means ran + fresh + produced the expected output" (`canon/canonical-principles-sop.md:594-595`).
- **not built yet:** `label_checker.py` stamping every label with its date and receipt pointer, emitting DORMANT, dropping TARGET, reading the registry at run time, and downgrading an expired label to "unproven". Serves: same.
- **not built yet:** fire checks for hook events other than PreToolUse, and an invoker for `health_invariants.py`. Serves: same.
- **not built yet:** the weekly human-validated roll-up that catches the scheduler itself stopping. Serves: same.
