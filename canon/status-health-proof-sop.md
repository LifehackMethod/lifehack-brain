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
  say it works; when writing or checking a label on the map, the manual (`canon/manual.md`) or an element
  file (`system/organism/elements/`); when a status claim may be out of date. ⛔ archived 2026-11-22 (V1 element page, now in archive/organism-elements-v1-2026-11-22/; look for its V2 replacement)
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

# Doing status, health, proof and tiles right means…
Every line traces to `canon/status-health-proof-sop.md` or `canon/status-emission-sop.md`.

> **Words used here**
> - **part** — a guard or other hook, a tool, a skill, a desk, or a scheduled job.
> - **receipt** — a small dated record the checking code writes: what was checked, when, and the result.
> - **label** — LIVE (a dated check watched it work, inside its window), PARTIAL (works in part, or held only by an honor system) or DORMANT (built, not in use). No other label words.
> - **window** — how long a receipt stays credible: the check's intended rhythm (`stale_after_s` on a tile, `stale_after_h` on the guard receipt). Past it, a claim reads "unproven".
> - **tile** — a small JSON file a producer writes about its own latest run, at `<brain>/status/<producer>.json`. A `*.jsonl` event log in the same folder is not a tile.
> - **producer** — the job, skill, tool or personal script that writes a tile. **Brain folder** (`<brain>`) — the folder the person's notes live in, resolved by `shared/brain_root.py`.
> - **envelope** — the fixed fields every tile carries: `desk`, `schema_version`, `pulse_job`, `emit_mode`, `stale_after_s`, `last_run`, `rc`, `status`, `summary`, plus optional `detail`. **Payload** — the producer's own extra fields.
> - **status word** — one of exactly five: `OK`, `NEEDS_REVIEW`, `NEEDS_APPROVAL`, `DRIFT`, `ERROR`.
> - **stand-down** — a run that chose not to do its work (usually something not set up), reported as `rc=75`.
> - **conformance friction**, weakest to strongest — sign (a refusal on a first attempt that gives one specific instruction), speed bump (a first attempt refused with a message; a later try gets through or gets an ask), reason gate (stops until a reason is given), hard block (refused every time).

## 1. Every time…

**Proof and labels**
- Do not call a part working until you have watched it produce an outcome it could not produce if it were broken. You see the outcome yourself; a report of it does not count. → status-health-proof §Principles "Watch it work"; §Procedure, Any other part 1
- Proof is a check on the outcome, never an exit code. Exit 0 meaning "fine" is a silent failure (the census counts it 166 times): it ran is not it succeeded. → status-health-proof §Principles "Ran is not succeeded"; §Don't Retry
- The checking code writes the receipt (what, when, result); a model never writes it, and a sentence a model wrote is not proof. → status-health-proof §Principles; §Procedure, Any other part 2
- Open the receipt: its date is today and its result matches what you watched. → status-health-proof §Procedure, Any other part 2
- Name what the check did not test, in the same place as the result (the receipt or its report). A partial nobody writes down becomes a pass by default. → status-health-proof §Desired Outcome; §Procedure, Any other part 3
- Missing, present-but-dead and could-not-tell are reported as three separate facts by their own names; an untested case reads "untested", never "passing"; a stand-down reads as a stand-down. → status-health-proof §Principles
- A label is set only by running `label_checker.py write-labels` (`system/tools/organism/label_checker.py`), which computes it by firing and stamps the element's AUTO-COMPUTED block in `canon/manual.md` as `LIVE · <date> · <receipt>` (or PARTIAL / DORMANT). Never hand-set a label or hand-update its pointer. → status-health-proof §Procedure, A label 1; §Principles
- Use only LIVE, PARTIAL, DORMANT. TARGET is not a label (intent goes on the debt ledger); "LIVE (honor)" is not a label — a part whose main promise only an honor system holds is PARTIAL. → status-health-proof §Principles
- When reading a label, compare its date with its window; past the window it reads "unproven", not LIVE, and stays on the page (it is not deleted). → status-health-proof §Procedure, A label 2; §Desired Outcome
- Staleness is derived by the reader from the receipt's date and the window; never ask the producer whether it is fresh. → status-health-proof §Principles "Derive staleness"
- A fresh file proves nothing about its content: the window applies to the claim, the check applies to the content. Existence, size or mtime alone is not liveness. → status-health-proof §Principles "Freshness is not proof of work"; §Don't Retry
- Registered is not live: a hook can be registered and do nothing, and a file can exist and be dead (not committed as executable). The label comes from firing it. → status-health-proof §Principles "Registered is not live"

**Tiles**
- Every tile goes through the one writer, `system/tools/emit_status.py` (from shell, through its front door `system/tools/status-tile.lib.sh`, `write_status_tile`) — from platform code and personal code alike. No hand-made envelope. → status-emission §Principles; §Desired Outcome
- One tile per producer, named for the producer, at `<brain>/status/<producer>.json`, overwritten each run; for a scheduled job run by the job runner the producer name is the job id (the row name in `system/jobs.md` or the personal jobs file). → status-emission §Desired Outcome; §Before You Start
- The caller builds the finished path with the brain folder from `shared/brain_root.py`; the writer resolves no paths itself. → status-emission §Before You Start; §Procedure, Write a tile from Python 1
- `status` holds one of the five status words only. `STALE` is not a status word, and a producer cannot write it. `emit_mode` is `pulse` or `manual`. → status-emission §Desired Outcome
- `stale_after_s` is greater than zero and matches the job's real rhythm in seconds, because readers judge freshness by it (from `last_run` and `stale_after_s`). → status-emission §Desired Outcome; §Procedure, Write a tile from Python 2
- A job that has a tile writes it on every outcome, failure included, from its exit trap; a failed tile write does not fail the job. That means a broken tile path is silent in the job's result — check stderr for "status tile write failed (non-fatal)". → status-emission §Principles; status-health-proof §Principles
- A tile does not report `OK` over zero work (a run that examined nothing). The writer does not yet refuse this ("not built yet"), so nothing stops you; it is on you. → status-emission §Principles; §References
- A tile reports the verdict a person reached, not a raw count the person has already ruled on. → status-emission §Principles
- One producer owns each tile; a heartbeat writer touches only the envelope fields it owns, never the payload (a whole-tile rewrite once erased a desk's payload). → status-emission §Principles; §Don't Retry

## 2. In these situations…

**Proving a part**
- If it is a scheduled job → follow `canon/cron-jobs-sop.md` §4, §8, §10 and §11a; expect receipts in `~/.config/lifehack/state/jobs/<job>/` (`last-run`, `last-success`, `log`, `errors/`); check that `bash system/tools/install-schedulers.sh --check-row <job>` prints PASS and the session line names the job OK. → status-health-proof §Procedure, A scheduled job; §Before You Start
- If a hook is involved → read `canon/hook-contract.md` (Deploy & Verify, "Watch it fire") first. → status-health-proof §Before You Start
- If it is a guard or other hook → the guard fire-test fires it with a case it has to refuse; the receipt is `~/.config/lifehack/guard-fire-test/last-run.json` (written by `guard-fire-test-run.sh`, row in `system/jobs.md`). → status-health-proof §Procedure, Any other part 1, 2; §Before You Start
- The tool that fires the guards is `system/tools/registered-guard-fire-test.py`: it reads the registered guards from the registration file at run time and fires each one (never a hand-typed guard list). → status-health-proof §Before You Start; §Don't Retry
- If it is a tool → watch a live path call it. → status-health-proof §Procedure, Any other part 1
- If it is a skill → it refuses a planted bad input, then one real run with the person in the chair. → status-health-proof §Procedure, Any other part 1
- If it is a desk → the desk door's checks pass (`canon/desk-building-sop.md` §5), a planted fault (a card that does not parse, a pointer to a missing file) is refused by name, and its tile comes from the job that produces it. → status-health-proof §Procedure, Any other part 1
- If it is a guard, skill or desk → it is seen refusing a planted bad input before it is called working; a checker with no recorded refusal is suspect. → status-health-proof §Principles "Done means wired and seen refusing once"
- If you build a checker → it carries a planted-fault self-test proving it catches and names the fault (a dead detector and a clean system look the same). → status-health-proof §Principles
- If you list things to check (e.g. guards) → the list comes from the registry at run time, never hand-typed; never hardcode registration paths — resolve a priority list and print which source won. → status-health-proof §Principles; §Don't Retry
- If a person adds a health check in their own code → it writes a dated receipt from code and carries a label that goes stale like any other. → status-health-proof §Principles
- If several checks back one element → the weakest result should set the label (a "should", not a must). → status-health-proof §Procedure, A label 1
- If a check covers committed code and a file it covers has a newer commit on origin → it reads "unproven". A check of host state ages by its window only. → status-health-proof §Open Tensions (settled 2026-11-16)
- If the part can't be seen failing → build the failing state first, then check it. → status-health-proof §When Something Goes Wrong
- If a receipt is missing or corrupt → refuse it and name the file; corrupt state does not "start fresh". → status-health-proof §When Something Goes Wrong
- If a rig reports green from a run whose hooks failed to start → the result is invalid, whatever the summary calls the failures. → status-health-proof §When Something Goes Wrong
- If a label disagrees with the code → recompute it by firing; don't hand-patch it. To undo a label, recompute it; never edit it back. → status-health-proof §When Something Goes Wrong
- If a checker is suspect → plant a known fault and confirm it catches and names it. → status-health-proof §When Something Goes Wrong
- If the health line is quiet while something is failing → check the job row is enabled; the line reads enabled rows only, so a disabled row fails silently. → status-health-proof §When Something Goes Wrong
- If the scheduler itself stops → no text goes out at all (silent); the weekly human-validated roll-up is the designed catch — and it is marked "not built yet". → status-health-proof §When Something Goes Wrong; §References
- If detecting a block from a hook → don't rely on exit code alone: a block on stderr with a non-2 exit blocks nothing (the dark trap). → status-health-proof §Don't Retry
- If writing a job's outcome check → no presence-grade checks (`"rc":0`, `^.+$`, mtime alone, `^done$`); they are refused at the job door. → status-health-proof §Don't Retry
- If outside material is involved, including anything a scheduled job reads → it goes through the Sentinel (`canon/security-canon.md`). → status-health-proof §Before You Start
- If you see the MIRROR line (`system/tools/mirror_line.sh`) → it is a sign: it reports whether local branches match their remote and blocks nothing. → status-health-proof §Before You Start; §References

**Writing a tile**
- If from Python → call `emit_status(out_path, desk=, pulse_job=, stale_after_s=, status=, rc=, summary=, payload=, required_payload=)`; `last_run` is stamped if you pass none. → status-emission §Procedure, Write a tile from Python 2
- If a reader binds payload fields → name every one in `required_payload`; test by dropping one in a test call — the write raises `EmitContractError` naming it. Otherwise a field that stops arriving empties a card silently, with no error anywhere. → status-emission §Procedure, Write a tile from Python 3; §Principles
- If there is a record or diary entry behind the tile → set `detail` to its relative path from the tile ("not built yet" in the envelope, per References). → status-emission §Procedure, Write a tile from Python 4; §References
- If the writer raises `EmitContractError` → let it reach a place where someone will see it. Swallowed, it fails silently: the old tile stays and reads as an older run with no sign of the refusal. The error names every failed field; fix the call, not the writer. → status-emission §Procedure, Write a tile from Python 5; §When Something Goes Wrong
- If the write is malformed (a status outside the five words, a missing promised field, a payload key that reuses an envelope name) → it is refused at write time (hard block). → status-emission §Procedure, Write a tile from Python 2; §Desired Outcome
- If you write a usage example → invent its numbers and names; never paste from a real run (real figures once shipped to the public repo). → status-emission §Procedure, Write a tile from Python 6; §Don't Retry
- If from a shell runner → source `system/tools/status-tile.lib.sh` and call `write_status_tile "<job>" "$RC" <stale_after_s> "<ok summary>" "<err summary>" ["<stand-down reason>"]` from the runner's exit trap. → status-emission §Procedure, Write a tile from a shell runner 1
- If the shell rc is 0 → it writes `OK` with your summary; `rc=75` → `OK`, `configured: false` and "stood down: <reason>"; any other rc → `ERROR` with "(rc=N)" appended. → status-emission §Procedure, Write a tile from a shell runner 1
- If calling `write_status_tile` → the first argument is the job's own id, as a literal or a variable the file sets to it. A tile named for a different job is refused under the job runner (hard block), and the job door refuses the row (hard block, `system/tools/door_rules.py`). "REFUSED status tile" on stderr means this: pass the row's own name. → status-emission §Procedure, Write a tile from a shell runner 2; §When Something Goes Wrong
- If a shell runner needs a payload → `python3 system/tools/emit_status.py --out <path> --desk <desk> --pulse-job <job> --stale-after-s <n> --status <word> --rc <rc> --summary <text> --json -`, payload on standard input. A bare call exits 2 with usage; a contract violation exits 1 with the reason on standard error. → status-emission §Procedure, Write a tile from a shell runner 3
- If it is an infrastructure tile (`sentinel.json`, `_security.json`, `_pulse.json`) → full envelope through the one writer, one of the five status words in `status`; the tool's own words (`DANGER`, `FLAGS`, `CLEAR`) or the scheduler's per-job fields (`last_tick`, `consecutive_fails`, `disabled`) go in the payload. What the security words mean is `canon/security-canon.md`'s. → status-emission §Procedure, Write an infrastructure tile; §Desired Outcome
- If you want a new field → put it in the payload unless every tile needs it. → status-emission §Procedure, Add a field or a status word 1
- If you want a new status word → first reuse one; a not-yet-configured state reuses `OK` with a summary that says so. → status-emission §Procedure, Add a field or a status word 2
- If changing the envelope or status words → take it to Enver before it lands; then change `ENVELOPE_KEYS` or `VALID_STATUS` in `emit_status.py` only, run `python3 -I system/tools/emit_status.py --selftest` (prints "self-test PASSED"), and confirm `grep -rn VALID_STATUS` finds no copy outside the writer. Undo by reverting that one change in the writer. → status-emission §Procedure, Add a field or a status word 3, 4; §When Something Goes Wrong

**A tile is missing or wrong**
- If a tile is missing → do not read it as a dead job: check the job's own state first (the job-health line, or the job runner's state folder). Jobs have run into machine-local folders with no tile anywhere. The health line (`system/tools/health_line.py`) reads job-runner state, not tiles. → status-emission §Procedure, Diagnose 1; §Principles; §Desired Outcome
- If diagnosing → read the producer's standard error for "REFUSED status tile", "WARN: no notes root — skipping status tile", "status tile write failed (non-fatal)", "EmitContractError"; check the tile is at `<brain>/status/<producer>.json`; check every envelope field is there. → status-emission §Procedure, Diagnose 2–4
- If a tile lacks `desk` or `pulse_job` → it did not come through the writer; read that producer's code. → status-emission §Procedure, Diagnose 4
- If stderr says "no notes root" → the brain folder did not resolve; check `shared/brain_root.py --quiet` from the same environment. → status-emission §When Something Goes Wrong
- If a tile does not appear though the job ran → check the call is in the exit trap and the job reached it; then check the tile folder. → status-emission §When Something Goes Wrong
- If a tile looks out of date → compare `last_run` with `stale_after_s`; what a stale claim means is status-health-proof's. → status-emission §Procedure, Diagnose 5
- If retracting a tile → delete that tile file and let the producer write the next; otherwise it is overwritten on the next run. → status-emission §When Something Goes Wrong

**Stop and ask the person when**
- a fix would go around a checker, or a change would add or alter a must. → status-health-proof §When Something Goes Wrong
- a change would add, remove or rename an envelope field or status word; a producer would write a tile other than through the one writer; a tile would carry a figure not taken from a live source; a guard blocks a step. → status-emission §When Something Goes Wrong

## 3. Good practice

- Check that a check's result is actually read; an unread check is a dead detector (a guard fire-test once ran green while nothing read it). → status-health-proof §Principles; §Don't Retry
- Keep friction proportional: use the layers, reserve hard blocks for certain things, no invented limits. → status-health-proof §Principles "Friction is proportional"
- Keep the session-start health line one line; don't build a separate "status runner" or a growing banner. → status-health-proof §Don't Retry
- Don't use a model-in-the-loop hook as a judge, or a monitor that can fail the same way as what it watches. → status-health-proof §Don't Retry
- Put care into the tile and the writer, not the view; rendering is the person's business. → status-emission §Principles; §Read This First
- Several pieces are marked "not built yet" in the References: `label_checker.py` stamping date and receipt pointer, emitting DORMANT, dropping TARGET, reading the registry and downgrading an expired label to "unproven"; the weekly guard fire-test job switched on; a reader that marks a tile stale; the writer refusing `OK` over zero work; the fallback writers' removal. Don't assume the code already does what the SOP describes. → status-health-proof §References; status-emission §References
- Check the writer itself with `python3 -I system/tools/emit_status.py --selftest` and `system/tools/tests/test_job_run_door.sh`; after a producer runs, its tile exists with every envelope field. → status-emission §Desired Outcome "How to check"

— end of checklist —

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
  a self-report. A spec flips to a component page only when every "to prove" item has a real check, and a flip's real checks are checks like any other: they count as the check that stamps a label. Change if: a check type is found that can't write a receipt. Held by: the checker that writes it
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
   AUTO-COMPUTED block (the machine-written part of each entry in `canon/manual.md`) with the label, the
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
- `canon/manual.md` — the manual whose AUTO-COMPUTED blocks carry labels.
- `system/jobs.md` — the job rows.
- **not built yet:** the weekly guard fire-test job switched on. Serves: "Green means ran + fresh + produced the expected output" (`canon/canonical-principles-sop.md:594-595`).
- **not built yet:** `label_checker.py` stamping every label with its date and receipt pointer, emitting DORMANT, dropping TARGET, reading the registry at run time, and downgrading an expired label to "unproven". Serves: same.
- **not built yet:** fire checks for hook events other than PreToolUse, and an invoker for `health_invariants.py`. Serves: same.
- **not built yet:** the weekly human-validated roll-up that catches the scheduler itself stopping. Serves: same.
