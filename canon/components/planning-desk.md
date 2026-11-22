---
component: planning-desk
title: "Planning desk"
source: origin/V2
scope:
  - system/tools/planning-diary-run.sh # the diary job's runner (built; the row is off by canon)
  - system/tools/planning-diary-capture.py # the daily diary capture
  - system/tools/planning-diary-rollup.py # the periodic diary roll-ups
  - system/tools/planning-weekly-prime-run.sh # LEGACY plumbing, replaced by the engine
  - system/tools/organism/checks/planning_door_rows_check.py # check (i)
  - system/tools/organism/checks/planning_guard_tests_check.py # check (ii)
  - system/tools/organism/checks/planning_data_path_check.py # check (iii)
  - system/tools/organism/checks/planning_weekly_receipt_check.py # check (iv)
  - system/tools/tests/test_planning_desk_checks.sh # the four checks' test
shared:
  - {paths: [system/tools/gws-auth.lib.sh], home: false, role_here: friction, file_home: google}
checks:
  - {id: planning-desk-door-rows, watches: "each job row the desk relies on passes the job door; the canon-off rows read DORMANT and never run (canon/cron-jobs-sop.md §5, §7; canon/data-layout.md:242)"}
  - {id: planning-desk-guard-tests, watches: "the guards the desk's sessions rely on hold — the desk's glasses, its scope boundary, No Private Desks, the one tile home, the compute-mechanically gate"}
  - {id: planning-desk-data-path, watches: "the person's desks sit where canon/data-layout.md says, read through the ONE desk list reader (shared/desk_list.py) — never a literal desk name"}
  - {id: planning-desk-weekly-receipt, watches: "the weekly run's receipt CONTENT — the staged validated picture plus the engine's snapshot-check result — read through ONE command Grand Central names (canon/status-health-proof-sop.md: freshness is not proof of work)"}
  - {id: planning-desk-weekly-prime-row, watches: "the planning-weekly-prime job row: LEGACY, replaced by Grand Central's engine; built, deliberately not in use; deleting it is the owner's separate yes", dormant: true}
  - {id: planning-desk-diary-row, watches: "the planning-diary job row: stays OFF by canon (canon/data-layout.md:242; canon/circulatory-system-sop.md:251); built, deliberately not in use", dormant: true}
  - {id: planning-desk-job-sim-rig, watches: "the job-sim rig that proves the job door bites", not_run: "the rig is benched on this machine this stage; it rewrote real state (2026-11-17)"}
receipts:
  - <brain>/status/component-planning-desk-door-rows.json
  - <brain>/status/component-planning-desk-guard-tests.json
  - <brain>/status/component-planning-desk-data-path.json
  - <brain>/status/component-planning-desk-weekly-receipt.json
health: []
---

# Planning desk

<!-- roll-up, generated: <LABEL> · checked <date> · valid until <date> · <receipt> · Health · as-built sha · last reading -->

## Purpose/Responsibility <!-- INTENT · human -->

The first desk brought online on V2: one folder of the person's own knowledge, a card, and a weekly planning run — the proof that the canonical documents build a real desk. Governs: canon/desk-building-sop.md (§5 the desk door's checks; §6 the diary economy, Planning-Diary); canon/data-layout.md (the desk's shape, :242 the planning-diary row off by canon); canon/status-health-proof-sop.md (how the label below is earned); the plan this desk is being built from is the build window's plan, `plans/planning-desk.plan.md` — ⛔ not a file of this repo: it lives on the notes side of the build (a plan, not canon), so this citation names it only to point at the governing document, never as a repo path.

## Interface(s) <!-- INTENT · human -->

- The desk's sessions load through the context-injection loader (session_context_loader.sh), which reads the desk's card and chain-loads its canon — canon/desk-building-sop.md §6 "launch sequence"; page: context-injection.
- The desk's diary is written by the diary tools through the shared tile writer (emit_status.py, homed in the Circulatory system's page); the plugin's planning-diary row stays off by canon — canon/data-layout.md:242; page: circulatory-system.
- The weekly run's picture is staged by Grand Central's engine; V2 never parses the engine's files — the receipt is read through ONE command Grand Central names (not named yet; see check (iv)); page: grand-central.
- Every job row the desk relies on passes the job door (install-schedulers.sh --check-row) — canon/cron-jobs-sop.md §7; page: scheduled-jobs.
- Google-facing pre-flights go through the shared auth library (gws-auth.lib.sh; homed on google) — canon/cron-jobs-sop.md §7; page: google.

## Quality-/Performance characteristics <!-- STATUS input · human -->

What "working" means, per check id:

- planning-desk-door-rows: each row the desk relies on passes the job door; the LEGACY row (planning-weekly-prime) and the canon-off row (planning-diary) read DORMANT — built, deliberately not in use — and a DORMANT row that runs is a fault.
- planning-desk-guard-tests: the desk's glasses load, a desk window loads only that desk's knowledge (P-71), No Private Desks holds, planning tiles land at the one tile home, and the compute-mechanically gate fires on planning prompts with numbers.
- planning-desk-data-path: the desk folders match canon/data-layout.md's shape, found through the desk list, never a literal name.
- planning-desk-weekly-receipt: the weekly receipt holds a validated staged picture AND the engine's snapshot-check result — content, never a date.

## Directory/file location <!-- AS-BUILT · generator -->

Human scope meaning: the desk's runners as they sit in the plugin today (the diary chain and the LEGACY weekly prime), plus this page's four named checks and their test. The desk's own material (card, canon, records, diary) lives in the person's notes folder under `<notes>/desks/`, found through the desk list — data, not code, and never in this repo. The engine's files are Grand Central's; they are not on the shipped origin and appear nowhere in this block.

<!-- AS-BUILT:BEGIN generator=system/tools/organism/component_page.py source=origin/V2@<sha> fetched=<time> sha256=<hash of body> -->
Hand-prepared in the generator's format; the generator itself has not run yet — this page and its
checks are new and not on the fetched origin, so a generated block today would read "not on origin"
for every row. The FIRST `component_page.py asbuilt` run overwrites this block wholesale (a hand
edit inside the fence is overwritten and reported, by design). What will be generated, stated honestly:

| kind | path | status |
| --- | --- | --- |
| file | system/tools/planning-diary-run.sh | on origin (ported; row off by canon) |
| file | system/tools/planning-diary-capture.py | on origin |
| file | system/tools/planning-diary-rollup.py | on origin |
| file | system/tools/planning-weekly-prime-run.sh | on origin (LEGACY) |
| check | system/tools/organism/checks/planning_door_rows_check.py | NEW — not on origin yet |
| check | system/tools/organism/checks/planning_guard_tests_check.py | NEW — not on origin yet |
| check | system/tools/organism/checks/planning_data_path_check.py | NEW — not on origin yet |
| check | system/tools/organism/checks/planning_weekly_receipt_check.py | NEW — not on origin yet |
| test | system/tools/tests/test_planning_desk_checks.sh | NEW — not on origin yet |

Not on origin (in-scope paths that differ from the fetched origin): the five rows above marked NEW.
<!-- AS-BUILT:END -->

## Fulfilled requirements <!-- INTENT · human -->

- The desk door's checks as code, refusing a planted fault by name — canon/desk-building-sop.md §5; canon/status-health-proof-sop.md:142. Held by the four checks; each carries a planted-fault self-test.
- One row per job; the door at install and at run time; TBD contracts can never succeed — canon/cron-jobs-sop.md §5, §7. Held by planning-desk-door-rows.
- The planning-diary row stays off — canon/data-layout.md:242; canon/circulatory-system-sop.md:251. Held by planning-desk-door-rows (DORMANT handling: an enabled DORMANT row is a fault).
- A desk's folder shape — canon/data-layout.md ("The shape", "Types of record"). Held by planning-desk-data-path.
- Freshness is not proof of work — canon/status-health-proof-sop.md:99-101. Held by planning-desk-weekly-receipt (content only).
- Not built yet, held as intent: the weekly receipt's ONE command (Grand Central has not named it — check (iv) fails closed until then); the first generator run of the as-built block; the final stamp (after his real week, the plan's step 7, his decision 6).

## Open issues/problems/risks <!-- DELTA -->

### Known (human: pointers only)

- Ledger lines carried by the plan's stage (planning-desk.plan.md part (E), each on its own step): L304, L320(c), L322(a)(b) (the label machinery), L888 / §9 #28 (the generator's missing parts), L893.
- The receipt command for check (iv) is a placeholder (`LIFEHACK_PLANNING_WEEKLY_RECEIPT_CMD`); Grand Central names the real one — until then the check ERRORs, fail-closed, by design.
- The job-sim rig is barred from this machine (it rewrote real state on this machine, 2026-11-17); the rig row below reads "not run here".

### Delta reading (AI, dated)

Read 2026-11-17 by the step-6(c) build helper · basis: the checks' real runs recorded in the build report (worktree cr9-s6-page), not stamped receipts — this page reads "no run on record" until the stamper's first stamp.

- **NOT HOLDING** — planning-desk-door-rows: the door refuses `calendar-store-sync` today (raw gws calendar read calls in its runner chain: system/tools/calendar-store-sync-run.sh:108, shared/tools/calendar_store_sync.py:391,395) — evidence: a real `--check-row` run recorded in report-s6-page.md — canon: canon/cron-jobs-sop.md §7 — goes to: build order (the door's finding, reported to the window; not fixed in this step).
- **NOT HOLDING** — planning-desk-data-path: two of the person's desks lack `canon/purpose.md` — evidence: the check's real run (report-s6-page.md) — canon: canon/data-layout.md ("what /ingest builds for each subject it finds") — goes to: debt ledger (the person's own folders; the check reports, it never repairs).
- **MISSING** — the weekly receipt command Grand Central is to name — evidence: check (iv) unset → ERROR by design — canon: the plan's step 6 — goes to: build order (Grand Central's window).
- **UNPROVEN** — the whole Status side: no check has written a receipt into `<brain>/status/` yet, so no label is earned and the page reads "no run on record" honestly — canon: canon/status-health-proof-sop.md:86-88 — goes to: the final stamp after step 7.

## Inside (whitebox) <!-- human -->

Motivation: the desk is knowledge plus a short card, never machinery (canon/desk-building-sop.md §5) — everything that runs a desk lives once in the platform; what this page scopes is the desk's runners as they sit in the plugin today and the four checks that earn the page's label.

Overview:

```
the person's notes folder, desks/<folder>/ (data; found through the desk list, never a literal name)
   | session start: the card -> the canon chain (context-injection)
weekly run: Grand Central's engine stages the picture -> the receipt -> ONE named command -> check (iv)
job rows: launchd -> job-run.sh -> the door -> stores, diary (off by canon), legacy prime (off)
```

Contained building blocks:

- The diary chain (planning-diary-run.sh, planning-diary-capture.py, planning-diary-rollup.py): one writer per day plus periodic roll-ups; the row is off by canon; owned by the Circulatory system component (see Shared ownership).
- The LEGACY weekly prime (planning-weekly-prime-run.sh): the old map-warming plumbing, replaced by the engine; stays off; deletion is the owner's separate yes (his Fable answer 6).
- The four checks (planning_door_rows_check.py, planning_guard_tests_check.py, planning_data_path_check.py, planning_weekly_receipt_check.py) and their test (test_planning_desk_checks.sh): each a named check with a planted-fault self-test that fails by name; each writes its receipt through the shared single tile writer.

## Status <!-- STATUS · checker → stamper -->

Suffix (human-owned): ·gap

**No run on record (untested).** No check on this page has written a receipt into `<brain>/status/` yet — the checks exist and their planted-fault self-tests pass (system/tools/tests/test_planning_desk_checks.sh, ALL PASS), but canon says a label is earned by a dated check that watched the part work, and nothing has earned one here yet. The page gets its first stamp after his real week and any fixes (the plan's step 7; his decision 6).

- The planning-weekly-prime row (LEGACY) and the planning-diary row (OFF by canon) are declared in the frontmatter as `dormant: true` checks: the stamper reads them DORMANT, counted beside the roll-up, never inside it; check (i) keeps verifying they never run.
- job-sim rig (declared `not_run:` in the frontmatter): **not run here** — the rig is barred from this machine (it rewrote real state on this machine, 2026-11-17); a rig never shown failing is not trusted (canon/cron-jobs-sop.md §10), so this row stays "not run" and is recorded as such, by design.

<!-- STATUS:BEGIN stamper=system/tools/organism/component_page.py stamped=<time> sha256=<hash> -->
<!-- STATUS:END -->

## Shared ownership <!-- human, in words; the generator verifies the files -->

In words, with the cross-page pointers written out. **These pointers were checked by hand, and are recorded as such** — the generator's cross-page UNOWNED and return-pointer checks are deferred (the plan's step 6(b); the set is small enough to check by hand and record, per the approved definition's fallback):

- **The diary tools** (planning-diary-run.sh, planning-diary-capture.py, planning-diary-rollup.py) belong to the **Circulatory system** component — the diary economy is its machinery; this page uses them, and its diary depends on them: → canon/components/circulatory-system.md (the page's own diary rows live under its scope). Return pointer: circulatory-system's page points back here for the planning desk's use of them.
- **The guards** the desk's sessions rely on (the context-injection loader's desk scoping, the egress and write guards, the Google auth pre-flight system/tools/gws-auth.lib.sh) belong to their own components — the loaders to **context-injection**, the Google credential pre-flight to **Google**: → canon/components/context-injection.md and canon/components/google.md. Return pointers: each of those pages names the planning desk among the sessions its machinery serves.
- **The engine** — the thing that stages the weekly picture and runs the snapshot check — belongs to **Grand Central**: → canon/components/grand-central.md. It is not on the shipped origin; outside the harness until Grand Central's Phase 6. Return pointer: grand-central's page names the planning desk as the first desk its engine serves.
- The job rows the desk relies on are homed on **scheduled-jobs** (the job machinery, the door, the wrapper): → canon/components/scheduled-jobs.md. Return pointer: scheduled-jobs' page lists the rows each desk relies on.

## Pointed at by <!-- generator -->

none yet (the generator's References grep has not run; the desk-building SOP's References section is written at the canon-files run — canon edits are barred from this build).

---
Structure adapted from arc42 (CC BY-SA 4.0); see `system/templates/component-page-template.md`.
