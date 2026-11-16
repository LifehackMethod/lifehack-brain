---
title: Status Emission
status: approved
approved_by: "Enver on 2026-11-16, round four's 'land it'"
last_reviewed: 2026-11-16
purpose: Say what a status tile is, which fields and status words every tile carries, and how a job, skill or tool writes one through the one writer so any reader can see its state.
read_when: Before building anything that should report its own state; before writing, changing or debugging a tile; when a tile is missing, refused or reads wrong.
history: "canon/status-emission-sop.history.md"
---

## Read This First

- **Purpose:** a status tile (a small JSON file a producer writes about its own latest run) lets any reader — a dashboard, a planning skill, a person with a text editor — see the state of a job, skill or tool without running it. This SOP is the tile contract: the envelope (the fixed fields every tile carries), the status words (the closed list of values its `status` field may hold), the one writer every tile goes through, and how to write a tile. The contract is the part worth the care, because renderers come and go while the tiles they read stay readable.
- **Three altitudes:** the platform (the shared code every install runs) holds the contract and the one writer; the person's own code and the custom tools they build on top call that same writer; the person owns what their tiles say. Nothing extra is built for personal use: the open-ended tool is the writer itself.
- **Use it when:** you build a producer (anything that writes a tile: a scheduled job, a skill, a tool, your own script) that should report its state; you change how a tile is written; a tile is missing, refused or says something wrong; you want a new field or status word.
- **Don't use it when:** you are proving a part works, writing a LIVE / PARTIAL / DORMANT label, keeping a receipt, or deciding what a reader does with a stale claim → `canon/status-health-proof-sop.md`. You are adding a scheduled job, its check or its door → `canon/cron-jobs-sop.md` (§6 the check, §7 the door). You want to know what a session sees at start, including the one-line job-health line → `canon/context-injection-sop.md`. You want what a security word means → `canon/security-canon.md`.
- **Covers:** the envelope, the status words, the freshness field (`stale_after_s`), the pointer field (`detail`), the one writer and its shell front door, tile naming, and how infrastructure tiles fit the envelope. **Doesn't cover:** where the tile folder sits in the notes (`canon/data-layout.md`, the tile row), or how anything looks. Rendering is delegated and unowned: looking is free, and how state is displayed is the person's business (canon, `canon/desk-building-sop.md:97-98`). The platform's one exception is its plain reference renderer, which demonstrates the contract and sets a floor anyone may replace.
- **How this SOP changes:** only through Enver's ruling; superseded text moves to the archive named in the header.
- **Which situation are you in?**
  - Writing a tile from Python, including your own code → The Procedure, "Write a tile from Python".
  - Writing a tile from a shell runner → "Write a tile from a shell runner".
  - Writing a security or scheduler tile → "Write an infrastructure tile".
  - Wanting a new field or status word → "Add a field or a status word".
  - A tile is missing or wrong → "Diagnose a missing or wrong tile".

## Desired Outcome

Every producer leaves one tile, named for the producer, at `<brain>/status/<producer>.json` (`<brain>` is the brain folder, resolved by `shared/brain_root.py`; the folder is canon's, `canon/data-layout.md:39`, `:243`), overwritten on each run. A job that has a tile writes it on every outcome, failure included. Every tile goes through one writer, carries one envelope with a status word from the closed list, is written whole or not at all, and a malformed tile is refused at write time with the failed field named. A tile is a `*.json` file; `*.jsonl` event logs in the same folder are not tiles.

- **The envelope** (`system/tools/emit_status.py:52-53`): `desk`, `schema_version`, `pulse_job`, `emit_mode`, `stale_after_s`, `last_run`, `rc`, `status`, `summary`, plus an optional `detail` — a relative path from the tile to the record or diary entry behind it, the handshake desk-building canon describes (canon, `canon/desk-building-sop.md:221-224`). Anything else is payload (free fields per producer); a payload key may not reuse an envelope name (`emit_status.py:92-94`).
- **The status words** (`emit_status.py:54`): `OK`, `NEEDS_REVIEW`, `NEEDS_APPROVAL`, `DRIFT`, `ERROR`. `STALE` is not a status word, so a producer cannot write it. `emit_mode` is `pulse` or `manual` (`emit_status.py:55`).
- **The freshness field:** `stale_after_s`, the producer's intended rhythm in seconds, greater than zero (`emit_status.py:88`). Readers age a tile from `last_run` and `stale_after_s` and mark it stale past that window; what a stale claim then means is `canon/status-health-proof-sop.md`'s.
- **The one writer:** `system/tools/emit_status.py` (Python function and command line): it validates, then writes atomically — temp file then rename (`emit_status.py:100-105`). `system/tools/status-tile.lib.sh` (`write_status_tile`) is its front door for shell runners: it maps the runner's exit code to a status word and hands the tile to the writer.
- **Infrastructure tiles** — Sentinel's `sentinel.json`, the security check's `_security.json` and the scheduler's `_pulse.json` — carry the same envelope through the one writer. The security tiles' own words (`DANGER`, `FLAGS`, `CLEAR`) ride in the payload, and their meaning belongs to `canon/security-canon.md`; the scheduler's per-job fields (`last_tick`, `consecutive_fails`, `disabled`) ride in the payload of `_pulse.json`.
- **Readers:** `system/tools/planning-diary-capture.py` reads every tile as a desk snapshot "as of last_run" (`planning-diary-capture.py:11`); `shared/tools/email_service_read.py` reads the email-summary tile to tell a real miss from sync lag; `system/tools/security-health.py` reads `sentinel.json`. The session-start job-health line (`system/tools/health_line.py`) reads job-runner state, not tiles. `system/tools/skill_hud.sh` (a skill's line above the status bar) is not a tile and sits outside this contract.

**How to check:** `python3 -I system/tools/emit_status.py --selftest` prints "self-test PASSED" (one valid write, four refusals, temp folder only); `system/tools/tests/test_job_run_door.sh` passes (a wrong tile name is refused at the door and at run time); after a producer runs, its tile exists in the tile folder with every envelope field.

## Before You Start

- Know your producer's name; for a scheduled job run by the job runner, that is the job id (the row name in `system/jobs.md` or the personal jobs file).
- Know how the brain folder is found: `shared/brain_root.py`. The writer does not resolve paths; the caller hands it the finished path (`emit_status.py:9-12`).
- For a scheduled job, read `canon/cron-jobs-sop.md` first: the tile is one output of a job, and the door checks the tile call.

## Principles

- **Every tile goes through the one writer, from platform code and personal code alike.** Why: one implementation of the contract cannot drift from itself, while hand-made copies of the envelope drift from it (`system/tools/emit_status.py:13-19` describes the copies it replaced). Change if: a second writer is shown staying identical to the first over time without a shared check. Evidence: OBSERVED — `system/tools/emit_status.py:4-7`, `:13-19` (port note 2026-08-15); the single writer is also desk-building canon's (`canon/desk-building-sop.md:198-199`).
- **A malformed tile fails loudly where it is written, not quietly where it is read.** Why: a renderer that meets a bad tile shows an empty card and nobody learns why; refusing at write time names the field so the producer fixes it in one pass (`system/tools/emit_status.py:82-96`). Change if: a refused write is shown losing more information than a bad tile reaching a reader would. Evidence: OBSERVED — `system/tools/emit_status.py:4-7` (ported 2026-08-15); the false-green fix at `:135-143`.
- **A tile carries its freshness as fields — `last_run` and `stale_after_s` — and `STALE` is not a status word.** Why: the fields give any reader what it needs to age the tile; why the reader, not the producer, decides is `canon/status-health-proof-sop.md`'s doctrine. Change if: a reader is shown needing freshness information the two fields cannot give. Evidence: OBSERVED — `system/tools/emit_status.py:54`, `system/tools/emit_status.py:88`, dated by the port note 2026-08-15.
- **A job that has a tile writes it on every outcome, from its exit trap, and a failed tile write does not fail the job.** Why: a job that dies mid-run still leaves a tile saying so, and a broken tile path does not turn a good run into a failed one (`system/tools/status-tile.lib.sh:19-22`). Change if: a job is shown with a failure mode that leaves no tile even from an exit trap. Evidence: OBSERVED — `system/tools/status-tile.lib.sh:5-11`, written after the 2026-08-27 incident in which three store writers failed every run for a night and no tile said so.
- **A tile does not report `OK` over zero work.** Why: a run that examined nothing and says "fine" looks exactly like a run that checked everything; a count of what was found cannot prove anything was looked at (canon, `canon/canonical-principles-sop.md:581-583`). Change if: a producer is shown whose `OK` carries meaning with nothing examined. Evidence: OBSERVED — the retired findings writer refused this pairing in code (`system/tools/emit_finding.py:343-356`).
- **One producer owns each tile; a heartbeat writer touches only the envelope fields it owns, not the payload.** Why: a heartbeat that rewrote a whole tile once erased a desk's rich payload. Change if: tiles gain a merge step that keeps other writers' fields, shown in a test. Evidence: OBSERVED — the clobbered-payload incident, written up 2026-11-06.
- **A producer lists the payload fields its reader binds, and the write is refused if one is missing.** Why: a field that silently stops arriving empties a card with no error anywhere; `required_payload` turns that into a refusal at the source (`emit_status.py:46-48`, `emit_status.py:89-91`). Change if: a producer is shown whose readers bind no payload field at all. Evidence: OBSERVED — `system/tools/emit_status.py:46-48`.
- **The contract is a short list of envelope keys checked on every write, not a separate schema file.** Why: for a system this size a documented envelope and a small required-field check carry most of the value at a fraction of the cost (`emit_status.py:21-23`). Change if: a reader not written in Python, or a second developer, needs a machine-readable schema. Evidence: OBSERVED — `system/tools/emit_status.py:21-23`.
- **The data outlives the code: care goes into the tile and the writer, not the view.** Why: renderer generations built on these tiles have been retired while the tiles they read stayed readable. Change if: a renderer change is shown forcing a change to tiles that still validate. Evidence: OBSERVED — renderers retired between 2026-06 and 2026-07, written up 2026-11-06.
- **A tile reports the verdict a person reached, not a raw count the person has already ruled on.** Why: acknowledged false alarms stay in the history counts; a tile driven by the raw count stays red forever and stops being read (`system/tools/security-health.py:183-186`). Change if: readers are shown needing the raw count as the headline. Evidence: OBSERVED — `system/tools/security-health.py:183-186`.
- **A missing tile does not mean a job is not running.** Why: jobs have been found running and writing to machine-local folders with no tile anywhere (`canon/canonical-principles-sop.md:1075`). Change if: every producer is shown writing a tile on every run, so absence carries meaning. Evidence: OBSERVED — `canon/canonical-principles-sop.md:1075` (three jobs confirmed running with no tile); canon retracted the opposite claim at `canon/canonical-principles-sop.md:1016`.

## The Procedure

### Write a tile from Python

1. **Do:** build the path `<brain>/status/<producer>.json`, with the brain folder from `shared/brain_root.py`.
   - **Why:** the writer takes a finished path and resolves nothing itself (`system/tools/emit_status.py:9-12`).
2. **Do:** call `emit_status(out_path, desk=, pulse_job=, stale_after_s=, status=, rc=, summary=, payload=, required_payload=)`.
   - **Expect:** the tile holds the envelope plus your payload; `last_run` is stamped if you pass none (`emit_status.py:69-80`). `stale_after_s` matches the job's real rhythm, because a reader judges the tile's freshness by it. A status outside the five words, a missing promised field or a payload key that reuses an envelope name is refused (conformance friction: a hard block on the write, `emit_status.py:82-96`).
3. **Do:** name in `required_payload` every payload field a reader binds.
   - **Check:** drop one of those fields in a test call; the write raises `EmitContractError` naming it.
4. **Do:** set `detail` to the relative path of the record or diary entry behind the tile, when there is one.
5. **Do:** let `EmitContractError` reach a place where someone will see it.
   - **Why:** a swallowed refusal leaves the old tile in place, which then reads as an older run with no sign of the refusal.
6. **Do:** if you write a usage example, invent its numbers and names.
   - **Why:** an example pasted from a real run once shipped real figures into the public repo (`emit_status.py:34-44`).

### Write a tile from a shell runner

1. **Do:** source `system/tools/status-tile.lib.sh` and call `write_status_tile "<job>" "$RC" <stale_after_s> "<ok summary>" "<err summary>" ["<stand-down reason>"]` from the runner's exit trap.
   - **Expect:** `rc` 0 writes `OK` with your summary; `rc=75` (stood down: the job chose not to run, usually because something is not set up) writes `OK`, `configured: false` and "stood down: <reason>", so a stand-down is named rather than shown as a clean pass; any other `rc` writes `ERROR` with "(rc=N)" appended (`status-tile.lib.sh:13-18`). The front door hands the tile to the one writer.
2. **Do:** pass the job's own id as the first argument, as a literal or a variable the file sets to it.
   - **Expect:** conformance friction at two points, both hard blocks: under the job runner a tile named for a different job is refused (`status-tile.lib.sh:32-36`), and the job door refuses the row (`system/tools/door_rules.py:101-103`; `canon/cron-jobs-sop.md:141`, fix at `:324`).
3. **Do:** when the runner needs a payload, call the writer's command line: `python3 system/tools/emit_status.py --out <path> --desk <desk> --pulse-job <job> --stale-after-s <n> --status <word> --rc <rc> --summary <text> --json -`, payload on standard input.
   - **Expect:** a bare call exits 2 with usage; a contract violation exits 1 with the reason on standard error (`emit_status.py:192-236`). Working callers: `system/tools/archivist-run.lib.sh:82-83`, `system/tools/planning-weekly-prime-run.sh:118-119`.

### Write an infrastructure tile

1. **Do:** write it through the one writer like any other tile, with the full envelope.
2. **Do:** put the tool's own words or fields in the payload — `DANGER`, `FLAGS` or `CLEAR` for a security tile, the per-job fields for the scheduler's tile — and one of the five status words in `status`.
   - **Why:** the own words carry meaning the five cannot, and the envelope lets any reader age the tile when it stops updating. What each security word means is `canon/security-canon.md`'s.

### Add a field or a status word

1. **Do:** put a new field in the payload unless every tile needs it.
   - **Why:** the envelope is the part every reader relies on; the payload is free per producer.
2. **Do:** before inventing a status word, reuse one: a not-yet-configured state reuses `OK` with a summary that says so (`shared/tools/item_store_read.py:465-470`).
3. **Do:** take a change to the envelope or the status words to Enver before it lands.
   - **Why:** every reader and every producer depends on the list.
4. **Do:** change `ENVELOPE_KEYS` or `VALID_STATUS` (`emit_status.py:52-54`) in the one writer, then run the self-test.
   - **Check:** `python3 -I system/tools/emit_status.py --selftest` passes and `grep -rn VALID_STATUS` finds no copy outside the writer.

### Diagnose a missing or wrong tile

1. **Do:** before reading a missing tile as a dead job, check the job's own state: the job-health line, or the job runner's state folder.
   - **Why:** a missing tile and a stopped job are different facts.
2. **Do:** read the producer's standard error for the writer's own lines: "REFUSED status tile", "WARN: no notes root — skipping status tile", "status tile write failed (non-fatal)", "EmitContractError".
3. **Do:** check the tile is at `<brain>/status/<producer>.json`.
4. **Do:** check the tile has every envelope field; a tile without `desk` or `pulse_job` did not come through the writer, so read that producer's code.
5. **Do:** if the tile looks out of date, compare `last_run` with `stale_after_s`; what a stale claim means is in `canon/status-health-proof-sop.md`.

## When Something Goes Wrong

- **If the Python write raises (Write from Python, step 2):** read the error; it names every failed field. Fix the call, not the writer.
- **If the shell front door prints "REFUSED status tile" (shell, step 2):** the first argument is not the job id; pass the row's own name.
- **If it prints "no notes root":** the brain folder did not resolve; check `shared/brain_root.py --quiet` from the same environment.
- **If a tile does not appear though the job ran:** check the call is in the exit trap and that the job reached it; then check the tile folder.
- **To undo:** a tile is overwritten on the next run; to retract one, delete that tile file and let the producer write the next. A change to the envelope or status words is undone by reverting that one change in the writer.
- **Stop and ask the person when:** a change would add, remove or rename an envelope field or status word; a producer would write a tile other than through the one writer; a tile would carry a figure not taken from a live source; a guard blocks a step here.

## Don't Retry

- **A writer whose bare call runs its self-test** — failed because a caller saw "PASSED" while no tile was written. Proof: `system/tools/emit_status.py:135-143`.
- **Tile writing left optional per runner, outside the exit trap** — failed because three store writers died every run for a night and no tile said so. Proof: `system/tools/status-tile.lib.sh:5-11`.
- **A hand-written fallback behind the writer's import** — failed because, while the writer was missing, a fallback sometimes wrote nothing and the run still reported success. Proof: `system/tools/emit_status.py:9`, `:18-19` (the 2026-08-15 port made the writer the preferred path; the fallbacks remain until removed).
- **A central log of individual check findings** — retired on 2026-10-29 because nothing read it; a real problem reaches the person through a job's own check failing. Proof: `system/organism/manual.md:367-368`.
- **An example pasted from a real run** — failed because it carried real figures into the public repo. Proof: `system/tools/emit_status.py:34-44`.
- **Reading a missing tile as a job that is not running** — failed because the jobs were running into machine-local folders. Proof: `canon/canonical-principles-sop.md:1016`, `:1075`.
- **A heartbeat that rewrites the whole tile** — failed because it erased the producer's payload (written up 2026-11-06).

## Pointers

- **Rulings behind this SOP:** `canon/desk-building-sop.md` (the desk side of the seam: the single writer, tiles registering by existence, the freshness horizon, the `detail` handshake, rendering delegated); `canon/data-layout.md` (the tile folder); `canon/cron-jobs-sop.md` (the tile-name check at the door, §7); `canon/status-health-proof-sop.md` (proof, receipts, labels, staleness); `canon/security-canon.md` (what the security words mean); this SOP's history file.
- **Evidence:** see References below.
- **Words used here:** **tile** — a small JSON file a producer writes about its own latest run. **Producer** — the job, skill, tool or personal script that writes a tile. **Envelope** — the fixed fields every tile carries. **Payload** — the producer's own extra fields. **Status word** — one value from the closed list the `status` field may hold. **Stand-down** — a run that chose not to do its work, reported as `rc=75`. **Brain folder** — the folder the person's notes live in. **Renderer** — anything that reads tiles and shows them. **OK over zero work** — a run reporting `OK` after examining nothing. **Conformance friction** — code that makes the wrong move harder, by strength and named by what it does when it fires: sign (a refusal on a first attempt that gives one specific instruction), speed bump (a first attempt refused with a message, where a later try gets through or gets an ask), reason gate (stops until a reason is given), hard block (refused every time); the full ladder is `canon/build-conformance-sop.md` §5.11.

## History

- 2026-11-15 — first draft, written from code and live state for round four; revised the same day after an independent check, the pause-2 corrections and Enver's batch rulings (one writer, one envelope, tiles in canon's `status/`, the findings store retired). Older wording: none.

## References (work in progress)

Every real thing this SOP points at, one line each. Paths are relative to the harness repo. Entries marked **not built yet** are slots for code the SOP describes that does not exist yet.

- `system/tools/emit_status.py` — the one tile writer and validator; Python function and command line; `--selftest`. Conformance friction: hard block on a malformed tile; a bare call exits 2.
- `system/tools/status-tile.lib.sh` — `write_status_tile`, the shell front door; maps exit codes to status words, writes from the runner's exit trap, refuses a tile named for another job (hard block, run time).
- `system/tools/calendar-store-sync-run.sh`, `system/tools/tasks-store-sync-run.sh`, `system/tools/email-summary-write-run.sh` — the calendar, tasks and email-summary store runners; they call the shell front door from their exit traps.
- `shared/gate/ingest_gate.py` — the ingest gate; appends `ingest-provenance.jsonl` to the tile folder (`ingest_gate.py:68`), an event log, not a tile.
- `system/tools/door_rules.py` — the job door's checks; `TILE_CALL` refuses a runner whose tile call names a different job (hard block, door time).
- `system/tools/tests/test_job_run_door.sh` — tests the tile-name refusal at the door and at run time.
- `system/tools/rig/build_meal_cases.py` — builds the test-rig case for a wrong tile name.
- `shared/brain_root.py` — resolves the brain folder every tile path starts from.
- `<brain>/status/` — the tile folder, one `<producer>.json` per producer (`canon/data-layout.md`).
- `system/jobs.md` — the job rows and the exit-code table (`75` = stood down) the front door follows.
- `system/tools/planning-diary-capture.py` — reads every tile as a desk snapshot for the diary.
- `shared/tools/email_service_read.py` — reads the email-summary tile to tell a real miss from sync lag.
- `shared/tools/item_store_read.py`, `shared/tools/email_summary_sync.py` — producers of the item-store and email-summary tiles.
- `system/tools/archivist-run.lib.sh`, `system/tools/planning-weekly-prime-run.sh` — runners that call the writer's command line with a payload.
- `system/tools/security-health.py` — writes `_security.json` and reads `sentinel.json`.
- `shared/gate/sentinel_response.py` — writes `sentinel.json`, Sentinel's tile (the inbound security gate's rollup).
- `system/tools/pulse.sh` — the scheduler; writes `_pulse.json`.
- `system/tools/health_line.py` — the session-start job-health line; reads job-runner state, not tiles.
- `system/tools/skill_hud.sh` — a skill's status-bar line; not a tile.
- `system/tools/emit_finding.py`, `system/tools/findings_reader.py`, `system/hooks/guard_findings_write.sh` — leftovers of the retired findings store, still in the tree.
- **not built yet:** the tile folder at `<brain>/status/` in every writer and reader. Serves: not yet in canon.
- **not built yet:** the shell front door handing every tile to `emit_status.py` instead of writing its own. Serves: not yet in canon.
- **not built yet:** the hand-written job scripts writing through the one writer. Serves: not yet in canon.
- **not built yet:** the optional `detail` pointer field in the envelope. Serves: not yet in canon.
- **not built yet:** a reader that marks a tile stale from `last_run` and `stale_after_s`. Serves: "Green means ran + fresh + produced the expected output" (`canon/canonical-principles-sop.md:578-579`).
- **not built yet:** the security and sentinel tiles on the shared envelope, own words in the payload. Serves: not yet in canon.
- **not built yet:** `pulse.sh` writing `_pulse.json` through the one writer, on the shared envelope. Serves: not yet in canon.
- **not built yet:** removal of the fallback writers behind the writer's import. Serves: not yet in canon.
- **not built yet:** every job that has a tile writing it from its exit trap through the front door. Serves: "An error must never produce the same signal as success" (`canon/canonical-principles-sop.md:1330`).
- **not built yet:** the writer refusing `OK` over zero work. Serves: "A count of what you FOUND cannot prove you LOOKED" (`canon/canonical-principles-sop.md:581`).
- **not built yet:** the email tile reader using `last_run` and `stale_after_s`. Serves: not yet in canon.
- **not built yet:** the platform's plain reference renderer, a plain view that demonstrates the contract. Serves: not yet in canon.
