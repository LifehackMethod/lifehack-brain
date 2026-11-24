---
component: scheduled-jobs
title: "Scheduled jobs"
source: origin/V2
scope:
  - system/tools/install-schedulers.sh  # the installer and the install-time door
  - system/tools/door_rules.py          # the door's rules, called by the installer
  - system/tools/job-run.sh             # the one job wrapper (the envelope)
  - system/tools/ingest-run.lib.sh      # sourced by job-run; Sentinel pause gate, headless auth
  - system/tools/runner-lock.lib.sh     # sourced by job-run; the single-instance lock
  - system/jobs.md                      # the plugin's half of the job list
  - shared/jobs_manifest.py             # the one scheduler that reads both halves
  - shared/tools/personal_jobs_scaffold.py  # makes the person's own job places
  - shared/tools/test_personal_jobs_scaffold.py
  - system/tools/job-texts.txt          # every text's wording, in one place
  - system/job-names.txt                # the plain names a text uses
  - system/tools/tests/job-sim.sh       # the rig
  - system/tools/pulse.sh               # the Linux/Windows dispatcher
  - system/tools/pulse-park.sh          # the Linux/Windows park file helper
  - system/tools/job-fetch-hosts.txt    # the shipped web allowlist for scheduled runs
  - system/tools/tests/test_install_schedulers_intervals.sh
  - system/tools/tests/test_job_run_door.sh
  - system/tools/tests/test_pulse_state_path.sh
  - system/tools/tests/test_scheduled_jobs_check.sh
  - system/tools/organism/checks/scheduled_jobs_check.py
shared:
  - {paths: [system/tools/model.lib.sh], home: false, role_here: friction, file_home: helpers-routing}
  - {paths: [system/tools/gws-auth.lib.sh], home: false, role_here: data, file_home: google}
checks:
  - {id: intervals-test, watches: "an interval is any whole number of seconds of 60 or more (canon/cron-jobs-sop.md:81 is the canon pointer for 'any interval, not only whole hours'; the 60-second floor is the code's: system/tools/install-schedulers.sh:545 and its test system/tools/tests/test_install_schedulers_intervals.sh)"}
  - {id: door-test, watches: "the door refuses a bad row, prints the reason, and job-run.sh runs the same door before every run of a yes row (canon/cron-jobs-sop.md:134,136) — held by system/tools/tests/test_job_run_door.sh"}
  - {id: no-send-verb, watches: "email never sends without human approval; reply drafts are allowed only as markdown files, none in Gmail (COMPASS P-184; canon/canonical-principles-sop.md §15.29) — held by a probe of the door's Gmail write list"}
  - {id: refusal-rulebook-resolves, watches: "every refusal names a rulebook that exists and says where the rule lives (COMPASS P-127) — held by a probe of the door's refusal texts"}
  - {id: state-local-not-drive, watches: "job state is local, never Drive (canon/cron-jobs-sop.md:88) — held by the check's Drive-path probe; system/tools/tests/test_pulse_state_path.sh is a related test the check does not run"}
receipts:
  - <brain>/status/component-scheduled-jobs.json
health: []
---

# Scheduled jobs

<!-- roll-up, generated: <LABEL> · checked <date> · valid until <date> · <receipt> · Health · as-built sha · last reading -->

## Purpose/Responsibility <!-- INTENT · human -->

The scheduler, the one job wrapper, and the door that refuses a bad job: plugin and personal jobs as two halves, the job files, and the chain trigger → job → routine. Governs: canon/cron-jobs-sop.md (the how-to; L38-50 the three layers); canon/canonical-principles-sop.md §15.29, §17.27; COMPASS P-127, P-148, P-184, P-188.

## Interface(s) <!-- INTENT · human -->

- Job rows come in from two halves: the plugin's list (system/jobs.md) and the person's own list, read together by the one scheduler (shared/jobs_manifest.py) — canon/cron-jobs-sop.md:104.
- The install door reads the rows through the rule module (system/tools/door_rules.py) and the run-time door is the same check, called by the wrapper before every run of a yes row (system/tools/job-run.sh:402) — canon/cron-jobs-sop.md:134.
- Runner state flows out to Seeing itself: the session's first line reads the local state these files write — canon/cron-jobs-sop.md:86; page: seeing-itself.
- A model step inside a job goes through the shared model library (system/tools/model.lib.sh; homed on helpers-routing) — canon/cron-jobs-sop.md:167; page: helpers-routing.
- The Google login pre-flight loads credentials through the shared auth library (system/tools/gws-auth.lib.sh; homed on google), in a subshell of the wrapper (system/tools/job-run.sh:486-487) — canon/cron-jobs-sop.md:119,150; page: google.
- A job that reads outside material passes through the Sentinel pause gate (system/tools/ingest-run.lib.sh:120-132) — COMPASS P-148; page: sentinel.
- The launchd trigger reads the code-root pointer written by context injection (session_context_loader.sh, homed on context-injection) — canon/cron-jobs-sop.md:82.

## Quality-/Performance characteristics <!-- STATUS input · human -->

- What "working" means, per check id. The register carries the checks at run time; each input names the canon outcome it watches.
- intervals-test: an interval is a whole number of seconds of 60 or more, on the hour or not — canon/cron-jobs-sop.md:81 is the pointer for "any interval, not only whole hours"; the 60-second floor is the code's (system/tools/install-schedulers.sh:545, tested by system/tools/tests/test_install_schedulers_intervals.sh).
- door-test: a bad row is refused at install and cannot run around the door at run time — canon/cron-jobs-sop.md:134-136.
- no-send-verb: a scheduled job reads or drafts, never sends — canon/canonical-principles-sop.md §15.29; COMPASS P-184.
- refusal-rulebook-resolves: a refusal says where the rule lives, and the rulebook it names exists — COMPASS P-127.
- state-local-not-drive: content may live on Drive, job state never does — canon/cron-jobs-sop.md:88.

## Directory/file location <!-- AS-BUILT · generator -->

Human scope meaning: everything that turns a row in a jobs list into a run that fired, was checked, recorded its state, and told the person when it broke — plus the two dispatchers (launchd installer, pulse) and the rig that tests the chain. The code-root pointer (~/.config/lifehack/code-root) is machine state, not a repo file; it is named here for the chain, not homed.

<!-- AS-BUILT:BEGIN generator=system/tools/organism/component_page.py source=origin/V2@d668dd2 fetched=2026-11-17T01:59:28Z sha256=32667d3c5b8c766d194f952def57ecd073cdba1c8dc7a5541f36ffcc504561ad -->
As built from origin `origin/V2` (@d668dd2):

| kind | path | commit |
| --- | --- | --- |
| file | shared/jobs_manifest.py | 5b42d06 2026-11-01 |
| file | shared/tools/personal_jobs_scaffold.py | 0037ccb 2026-11-14 |
| test | shared/tools/test_personal_jobs_scaffold.py | 8f3626d 2026-11-05 |
| file | system/job-names.txt | 5b42d06 2026-11-01 |
| file | system/jobs.md | 2fcbbab 2026-11-14 |
| file | system/tools/door_rules.py | a38e39d 2026-11-01 |
| file | system/tools/ingest-run.lib.sh | 0037ccb 2026-11-14 |
| file | system/tools/install-schedulers.sh | 0c03262 2026-11-16 |
| file | system/tools/job-fetch-hosts.txt | 063dcb8 2026-10-27 |
| file | system/tools/job-run.sh | 1fed78d 2026-11-05 |
| file | system/tools/job-texts.txt | cfc100e 2026-10-31 |
| file | system/tools/organism/checks/scheduled_jobs_check.py | d7c5c8e 2026-11-16 |
| file | system/tools/pulse-park.sh | 5b42d06 2026-11-01 |
| file | system/tools/pulse.sh | 0037ccb 2026-11-14 |
| file | system/tools/runner-lock.lib.sh | 7c254d0 2026-10-28 |
| test | system/tools/tests/job-sim.sh | 8f3626d 2026-11-05 |
| test | system/tools/tests/test_install_schedulers_intervals.sh | 0c03262 2026-11-16 |
| test | system/tools/tests/test_job_run_door.sh | 0037ccb 2026-11-14 |
| test | system/tools/tests/test_pulse_state_path.sh | 80be844 2026-11-01 |
| test | system/tools/tests/test_scheduled_jobs_check.sh | d7c5c8e 2026-11-16 |

Hook wiring (from origin `hooks/hooks.json`):

(none)

Register rows in scope (from origin `system/register/register.jsonl`):

| id | path | type | sha |
| --- | --- | --- | --- |
| scheduled:archivist-audit | /system/jobs.md | scheduled | c0779535 |
| scheduled:archivist-deepmine | /system/jobs.md | scheduled | c0779535 |
| scheduled:calendar-store-sync | /system/jobs.md | scheduled | c0779535 |
| scheduled:email-summary-write | /system/jobs.md | scheduled | c0779535 |
| scheduled:guard-fire-test | /system/jobs.md | scheduled | c0779535 |
| scheduled:mirror-fetch | /system/jobs.md | scheduled | c0779535 |
| scheduled:obsidian-reindex | /system/jobs.md | scheduled | c0779535 |
| scheduled:planning-diary | /system/jobs.md | scheduled | c0779535 |
| scheduled:planning-weekly-prime | /system/jobs.md | scheduled | c0779535 |
| scheduled:tasks-store-sync | /system/jobs.md | scheduled | c0779535 |
| tool:public:/shared/jobs_manifest.py | /shared/jobs_manifest.py | tool | a9daf7cd |
| tool:public:/shared/tools/personal_jobs_scaffold.py | /shared/tools/personal_jobs_scaffold.py | tool | f86b1764 |
| tool:public:/system/tools/door_rules.py | /system/tools/door_rules.py | tool | 98f4853b |
| tool:public:/system/tools/ingest-run.lib.sh | /system/tools/ingest-run.lib.sh | tool | 4b465288 |
| tool:public:/system/tools/install-schedulers.sh | /system/tools/install-schedulers.sh | tool | 3c911a70 |
| tool:public:/system/tools/job-run.sh | /system/tools/job-run.sh | tool | d849ea41 |
| tool:public:/system/tools/organism/checks/scheduled_jobs_check.py | /system/tools/organism/checks/scheduled_jobs_check.py | tool | 5a95e87c |
| tool:public:/system/tools/pulse-park.sh | /system/tools/pulse-park.sh | tool | c91d78db |
| tool:public:/system/tools/pulse.sh | /system/tools/pulse.sh | tool | 5ff68c22 |
| tool:public:/system/tools/runner-lock.lib.sh | /system/tools/runner-lock.lib.sh | tool | 5f09f232 |

Jobs (from origin `system/jobs.md`):

| name | enabled | interval | contract |
| --- | --- | --- | --- |
| calendar-store-sync | off | 86400 | TBD |
| tasks-store-sync | off | 86400 | TBD |
| email-summary-write | off | 10800 | filled |
| planning-diary | off | 86400 | TBD |
| archivist-audit | off | 604800 | TBD |
| archivist-deepmine | off | 345600 | TBD |
| planning-weekly-prime | off | 86400 | TBD |
| guard-fire-test | off | 604800 | filled |
| obsidian-reindex | off | 21600 | filled |
| mirror-fetch | off | 3600 | filled |

Pointers:

named but missing: `system/sops/pr-sop.md` ⛔ not on origin

not on origin: 0

pointed at by: none
<!-- AS-BUILT:END -->

## Fulfilled requirements <!-- INTENT · human -->

- One row per job, in a jobs block; one scheduler reads the plugin's list and the person's own — canon/cron-jobs-sop.md:104.
- The nine-column row contract — canon/cron-jobs-sop.md:107.
- A check tests content, never presence; a pass stamps last-success and nothing else does — canon/cron-jobs-sop.md:56,85,126-130.
- The door at install and at run time; the raw-read rule and the write list — canon/cron-jobs-sop.md:134,136,142.
- Any interval of 60 seconds or more, on the hour or not — canon/cron-jobs-sop.md:81.
- State is local, never Drive — canon/cron-jobs-sop.md:88.
- The exit-code table, the alert rule, the stand-down texts — canon/cron-jobs-sop.md:90-100.
- The rig replays days in seconds and shows itself failing first — canon/cron-jobs-sop.md:171-176.
- The personal scaffold makes the places a person's own jobs need — canon/cron-jobs-sop.md:229-242.
- Refusal texts by list origin (personal vs plugin) — canon/cron-jobs-sop.md:256-263.
- The switch-on protocol, one job at a time at a human gate — canon/cron-jobs-sop.md:350-360.
- Texts written for a person, wording in one place — canon/cron-jobs-sop.md:389-403.
- Not built yet, held as intent: the PR rulebook the plugin refusal names (canon/cron-jobs-sop.md:186); the PROPOSED lines waiting for rulings (canon/cron-jobs-sop.md:408-426).

## Open issues/problems/risks <!-- DELTA -->

### Known (human: pointers only)

Still a gap, as triaged 2026-11-16:

- debt ledger L115 — repeat-safe writes are told to the routine by canon but nothing checks them.
- debt ledger L116, L117, L341 — per-job AI tool grants are ruled but every step still runs read-only (system/tools/model.lib.sh:22,74).
- debt ledger L123 — the door accepts any non-empty source word (system/tools/install-schedulers.sh:163); gap or design, the owner's call.
- debt ledger L313 — personal finance hosts ship to students in the web allowlist (system/tools/job-fetch-hosts.txt:6-10).
- debt ledger L336 — a model called directly outside run_model (intake_reader.py:167; the door names archivist-run.lib.sh:70).
- debt ledger L337 — the "Pulse runners" header wording (archivist-run.lib.sh:3).
- debt ledger L345 — credentials exported into runners: the runners call the loader themselves (system/tools/gws-auth.lib.sh:190-192); the wrapper itself does not (system/tools/job-run.sh:486-487).
- debt ledger L346 — an email row reads outside the one shared path (system/jobs.md:194; row off).
- debt ledger L360 — the door's Gmail write list still holds send and has no drafts verb (system/tools/install-schedulers.sh:264,269).
- debt ledger L456 — deferred cron ideas, waiting for a ruling.
- debt ledger L743 — an off row's Drive tile (goes with L346).
- debt ledger L745, L750 — the door cannot see Python imports (canon admits the limit, canon/cron-jobs-sop.md:148) or list-form calls.
- debt ledger L949 — a job reads the plugin's skill copy by fixed path (archivist-audit-run.sh:36).

Sharpened:

- debt ledger L118-122 — the plugin refusal names a rulebook file that does not exist (system/tools/install-schedulers.sh:358); the file is not written yet, and canon/cron-jobs-sop.md:186 wants the refusal pointing at the plugin's GitHub page instead.
- debt ledger L340 — archivist rows are TBD and the door now names the exact fixes.
- debt ledger L369 — the toolbox and register rows drift from the jobs list.
- debt ledger L694 — the pulse park file sits on the notes root (system/tools/pulse-park.sh:42; system/tools/pulse.sh:133) against canon/cron-jobs-sop.md:88.
- debt ledger L756 — six old port rows: the paths are fixed; the TBD contracts are filled per desk at its rebuild.
- debt ledger L758 — personal refusals are solved (system/tools/install-schedulers.sh:357); plugin refusals wait on L118-122; the plain crontab and direct-runner half is untouched.
- debt ledger L762 — the whole switch-on order: only one step is live; the rest wait on the TBD contracts.

Appeals (upward candidates; canon is not edited here):

1. A wording candidate only in canon/cron-jobs-sop.md:119 — "loads" could read "checks"; the wrapper loads the login in a subshell to read the exit code and nothing is exported into the runner (system/tools/job-run.sh:486-487).
2. A scope question: on Linux and Windows the trigger starts the dispatcher, which has none of the door, check or alarm steps (canon/cron-jobs-sop.md:34,42) — whether "Non-Mac is unchanged" still stands for a product that ships to students.
3. A down-copy: one line in canon/cron-jobs-sop.md:142 pointing at COMPASS P-184, whose ruling is already canon; and the door needs a drafts verb so "drafts stay allowed" holds once send leaves the list.

### Delta reading (AI, dated)

Read 2026-11-16 by Opus 5.5 (claude-opus-5-5) · as-built at 50c09ab · stamp 2026-11-17T01:42:21Z

- **NOT HOLDING** — no-send-verb: the door's Gmail write list still lets a scheduled job send mail, and it has no drafts verb, so "drafts stay allowed" has nothing to hold it once send is taken off — evidence system/tools/install-schedulers.sh:269 — canon canon/cron-jobs-sop.md:142; canon/canonical-principles-sop.md:1331-1335 (§15.29); COMPASS P-184 — goes to: build order (take send off, add drafts); debt ledger L360.
- **NOT HOLDING** — the code comment above that list says sending was part of the 2026-10-28 write ruling; a code comment is not intent, and canon says sending is not one of those writes — evidence system/tools/install-schedulers.sh:263-264 — canon canon/cron-jobs-sop.md:142 — goes to: build order (with the item above).
- **NOT HOLDING** — refusal-rulebook-resolves: the plugin-row refusal names a rulebook file that is not on origin — evidence system/tools/install-schedulers.sh:358; system/sops/pr-sop.md absent at 50c09ab — canon COMPASS P-127; canon/cron-jobs-sop.md:104,260-261 — goes to: build order; debt ledger L118-122.
- **NOT HOLDING** — state-local-not-drive: the Linux/Windows park file is written under the notes root, not the local state folder; the related test system/tools/tests/test_pulse_state_path.sh is on origin but the check does not run it — evidence system/tools/pulse.sh:133; system/tools/pulse-park.sh:42 — canon canon/cron-jobs-sop.md:88 — goes to: build order; debt ledger L694.
- **BROKEN POINTER** (tension inside canon, no winner picked) — where a broken plugin job is reported: one place names system/sops/pr-sop.md as the rulebook ("assume that there is a pr sop"), another says that file is not written yet and a report is an issue on the plugin's GitHub page until it exists; the refusal text follows the first — evidence system/tools/install-schedulers.sh:358 — canon canon/cron-jobs-sop.md:104,186,260-263 — goes to: upward candidate through the canon-files run.
- **UNPROVEN** — the whole Status block comes from code the host has not got: the checker, its planted-fault test and the stamper are all absent at 50c09ab (as-built "not on origin: 2"; system/tools/organism/component_page.py is also absent, and so is this page) — evidence system/tools/organism/checks/scheduled_jobs_check.py, system/tools/tests/test_scheduled_jobs_check.sh, system/tools/organism/component_page.py, none in the tree at 50c09ab — canon canon/status-health-proof-sop.md:35-37,89-91 (proof is a receipt the checking code writes; every checker carries a planted-fault self-test) — goes to: build order.
- **BROKEN POINTER** — the page's footer names a template that is not on origin (as-built "named but missing") — evidence system/templates/component-page-template.md absent at 50c09ab — canon pointer: none (the page's own footer) — goes to: build order.
- **MISSING** — canon says that off the Mac the installer installs plain-code rows only and refuses a row with an AI step; at origin the Linux/Windows install path just installs the dispatcher, and the dispatcher reads the model column and ignores it — evidence system/tools/install-schedulers.sh:700-760 (install_mac_linux), 805 (install_windows); system/tools/pulse.sh:356 — canon canon/cron-jobs-sop.md:34,42 — goes to: build order; upward candidate for the scope question in Appeal 2.
- **UNPROVEN** — the rig was not run by any check, so no green run and no planted-fault (--bite) run is on record for this stamp; canon says a rig never shown failing is not trusted — evidence system/tools/tests/job-sim.sh (8f3626d); Status "not tested" line — canon canon/cron-jobs-sop.md:173-174; canon/status-health-proof-sop.md:89-91 — goes to: build order (a rig receipt the check reads).
- **UNPROVEN** — the Linux/Windows path end to end has no check at all (named as untested in Status) — evidence system/tools/pulse.sh, system/tools/pulse-park.sh — canon canon/cron-jobs-sop.md:34; canon/status-health-proof-sop.md:86-88 (untested reads as untested) — goes to: build order.
- **UNPROVEN** — no plugin job has run under the chain: all ten shipped rows are off, so the live part of the chain (launchd firing, last-success, the texts) has nothing at origin to watch; the label vocabulary has DORMANT for built-not-in-use (label not changed here) — evidence system/jobs.md:182,187,194,210,219,220,229,236,242,250 — canon canon/cron-jobs-sop.md:352-358; canon/status-health-proof-sop.md:35-37 — goes to: debt ledger L762.
- **MISSING** — six of the ten shipped rows have TBD in every contract column, so the door refuses them and they cannot be switched on — evidence system/jobs.md:182,187,210,219,220,229 — canon canon/cron-jobs-sop.md:122 — goes to: debt ledger L340, L756.
- **UNOWNED** — the 60-second interval floor has no canon pointer: canon says any interval, and the code's message cites that canon line for a floor the line does not state — evidence system/tools/install-schedulers.sh:545-546 — canon canon/cron-jobs-sop.md:81,114 — goes to: upward candidate through the canon-files run.
- **UNOWNED** — the shipped web allowlist carries hosts for one person's market-data fetchers, which no shipped row reads; canon says hosts go in a person's own list, never the plugin's — evidence system/tools/job-fetch-hosts.txt:4-11 — canon canon/cron-jobs-sop.md:150 — goes to: debt ledger L313.
- **UNPROVEN** — credentials reach runners: the shared auth library exports them and a runner sources it itself; canon says never export them into a runner. No check holds this; the code as read goes against canon — evidence system/tools/gws-auth.lib.sh:190-192; system/tools/email-summary-write-run.sh:40 — canon canon/cron-jobs-sop.md:150 — goes to: debt ledger L345 (file homed on the google page).
- **MISSING** — per-job AI tool grants: canon allows read-only or a grant scoped to the job's own output folder; every model call still starts read-only and there is no grant path — evidence system/tools/model.lib.sh:22,74 — canon canon/cron-jobs-sop.md:167 — goes to: debt ledger L116, L117, L341 (file homed on the helpers-routing page).
- **UNPROVEN** — a literal model id and a direct model call sit outside the one model library; canon has the door refuse both, and nothing checks the files they live in — evidence system/tools/archivist-run.lib.sh:70; shared/tools/intake_reader.py:167 — canon canon/cron-jobs-sop.md:143,167 — goes to: debt ledger L336.
- **UNOWNED** — the door accepts any non-empty source word; canon states this itself, so it is canon's design as written, and whether it should stand is the owner's call — evidence system/tools/install-schedulers.sh:163 — canon canon/cron-jobs-sop.md:119 — goes to: upward candidate through the canon-files run; debt ledger L123.
- **BROKEN POINTER** (wording) — canon says a gmail row "loads the Google login"; the wrapper only runs the loader in a subshell to read its exit code and exports nothing — evidence system/tools/job-run.sh:486-487 — canon canon/cron-jobs-sop.md:119 — goes to: upward candidate through the canon-files run (Appeal 1).

Refreshed 2026-11-16 at d668dd2 (after the push), by the build window, mechanically; no new reading: the two items "the whole Status block comes from code the host has not got" and "the page's footer names a template that is not on origin" are resolved (as-built: not on origin: 0; the check re-ran on the clean d668dd2 checkout). Every other item stands as read.

## Inside (whitebox) <!-- human -->

Motivation: the split is canon's three layers — the trigger stays dumb, the wrapper is the only place a run earns exit 0, and the routine is the skill's business (canon/cron-jobs-sop.md:38-50). Everything two desks would want different lives in the desk; everything a person would be upset to see differ lives here once (canon/cron-jobs-sop.md:66-71). The plugin/personal split exists because a plugin update overwrites the plugin's own files, so a person's job needs its own home (canon/cron-jobs-sop.md:229).

Overview:

```
launchd (Mac) or pulse.sh (Linux/Windows)
   → code-root pointer → job-run.sh (the door, the lock, the watchdog)
       → the row's command (the routine, in the desk or personal code)
       → the row's check → last-success → session line / one text on break, one on recovery
install-schedulers.sh + door_rules.py refuse a bad row before any of it runs
```

Contained building blocks:

- The installer and the install-time door (system/tools/install-schedulers.sh, system/tools/door_rules.py): one launchd job per yes row, any interval of 60 s or more; refuses a bad row with reasons and a next-step text by list origin; carries the outside-the-checker mark (system/tools/install-schedulers.sh:375-402,515-520).
- The run wrapper (system/tools/job-run.sh): the run-time door (system/tools/job-run.sh:398-409), the watchdog, the lock, the content check, last-success, the alert rule, the cost line.
- The ingest run library (system/tools/ingest-run.lib.sh): the Sentinel pause gate (system/tools/ingest-run.lib.sh:120-132), headless auth pre-flights; a port note records the dropped two-machine gate (system/tools/ingest-run.lib.sh:14-17).
- The lock library (system/tools/runner-lock.lib.sh): owner pid, dead owner taken at once, live owner stands down.
- The two job lists and the one scheduler (system/jobs.md, shared/jobs_manifest.py): the plugin half and the personal half, merged, personal wins on a name clash with a warning.
- The personal scaffold (shared/tools/personal_jobs_scaffold.py, shared/tools/test_personal_jobs_scaffold.py): creates the person's own job places, never overwrites.
- Texts and plain names (system/tools/job-texts.txt, system/job-names.txt): every wording in one place, read by the wrapper (system/tools/job-run.sh:156-158).
- The rig (system/tools/tests/job-sim.sh): replays days in seconds; a generated scenario per personal row; shows itself failing first (canon/cron-jobs-sop.md:171-176).
- The non-Mac dispatcher (system/tools/pulse.sh, system/tools/pulse-park.sh): cron and schtasks entry; no door, check or alarm steps (canon/cron-jobs-sop.md:34); the park file sits on the notes root (system/tools/pulse.sh:133).
- The shipped web allowlist (system/tools/job-fetch-hosts.txt): seals a scheduled run's web reads to named hosts.
- The code-root pointer (machine state, not in the repo): one line, rewritten each session; a plist never holds a code path (canon/cron-jobs-sop.md:82).

## Status <!-- STATUS · checker → stamper -->

Suffix (human-owned): ·gap

<!-- STATUS:BEGIN stamper=system/tools/organism/component_page.py stamped=2026-11-17T01:59:29Z sha256=963f5b86edfb9dc4fd9ae3f744560cbaaa53795f3cdab7b9ce71e5c57a838561 -->
Status: PARTIAL · checked 2026-11-16 · valid until 2026-11-23 · <brain>/status/component-scheduled-jobs.json
Past "valid until", read this as unproven, whatever the word says.
Health: no tile declared

| check | watches | result | date | at sha | clean | window | receipt | untested | reading |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| intervals-test | an interval is any whole number of seconds of 60 or more (canon/cron-jobs-sop.md:81 is the canon pointer for 'any interval, not only whole hours'; the 60-second floor is the code's: system/tools/install-schedulers.sh:545 and its test system/tools/tests/test_install_schedulers_intervals.sh) | PASS | 2026-11-16 | d668dd2 | yes | 604800 | <brain>/status/component-scheduled-jobs.json | job-sim.sh rig (not run: long); live installed jobs and their last-success ages (personal, not shipped); the Linux/Windows pulse path end to end | LIVE |
| door-test | the door refuses a bad row, prints the reason, and job-run.sh runs the same door before every run of a yes row (canon/cron-jobs-sop.md:134,136) — held by system/tools/tests/test_job_run_door.sh | PASS | 2026-11-16 | d668dd2 | yes | 604800 | <brain>/status/component-scheduled-jobs.json | job-sim.sh rig (not run: long); live installed jobs and their last-success ages (personal, not shipped); the Linux/Windows pulse path end to end | LIVE |
| no-send-verb | email never sends without human approval; drafts stay allowed (COMPASS P-184; canon/canonical-principles-sop.md §15.29) — held by a probe of the door's Gmail write list | FAIL | 2026-11-16 | d668dd2 | yes | 604800 | <brain>/status/component-scheduled-jobs.json | job-sim.sh rig (not run: long); live installed jobs and their last-success ages (personal, not shipped); the Linux/Windows pulse path end to end | PARTIAL |
| refusal-rulebook-resolves | every refusal names a rulebook that exists and says where the rule lives (COMPASS P-127) — held by a probe of the door's refusal texts | FAIL | 2026-11-16 | d668dd2 | yes | 604800 | <brain>/status/component-scheduled-jobs.json | job-sim.sh rig (not run: long); live installed jobs and their last-success ages (personal, not shipped); the Linux/Windows pulse path end to end | PARTIAL |
| state-local-not-drive | job state is local, never Drive (canon/cron-jobs-sop.md:88) — held by the check's Drive-path probe; system/tools/tests/test_pulse_state_path.sh is a related test the check does not run | FAIL | 2026-11-16 | d668dd2 | yes | 604800 | <brain>/status/component-scheduled-jobs.json | job-sim.sh rig (not run: long); live installed jobs and their last-success ages (personal, not shipped); the Linux/Windows pulse path end to end | PARTIAL |
not tested by these checks: job-sim.sh rig (not run: long); live installed jobs and their last-success ages (personal, not shipped); the Linux/Windows pulse path end to end
<!-- STATUS:END -->

## Shared ownership <!-- human; generator verifies -->

Two files on this page's list are homed elsewhere; they are named here, not homed here, so no file has two homes:

- The model library (system/tools/model.lib.sh) is a friction surface here — the door refuses a literal model id outside it (canon/cron-jobs-sop.md:143) — but its home is helpers-routing: the tier table and the one way to call a model are that component's as-built. Its check result is stamped there; this page carries the pointer only.
- The Google auth library (system/tools/gws-auth.lib.sh) is data here — the credentials its exports carry reach the runners through their own calls (system/tools/gws-auth.lib.sh:190-192) — but its home is google. Its check result is stamped there.

## Pointed at by <!-- generator -->

(generated in the as-built block)

---

Structure adapted from arc42 (CC BY-SA 4.0); see `system/templates/component-page-template.md`.
