# Plan: Quiet the pulse-cron alert

**Desired outcome:** the pulse-cron health check stops paging on a single missed heartbeat, and the suppressed-alert count is visible on the status tile.

> **Review:** six-lens 2026-09-04 · reviewed, two owner notes appended below.

## CONTEXT

The pulse-cron health-invariants check pages on every missed heartbeat, including a single
transient one. Three pages in one week resolved themselves before anyone looked. The fix adds
a debounce window and a visible suppressed-count so a real outage still pages, but a lone blip
does not.

## FRAME

- Owner: BUILD carries every task below; no other lane touches this plan.
- Repo: all work lands in the public tree, `V2` branch, commit local per the map.
- Success criteria:
  - the debounce window swallows a single missed heartbeat and lets a second consecutive
    miss through, proven by the regression test in 1.6.
  - the suppressed-count is visible on the end-of-run status tile.
  - the pulse alert pipeline is noticeably leaner and quieter than before.

## Phase 1 — Quiet the false alarm and prove it

- [ ] **1.1 Silence the false-positive latency alert.** `Owner: BUILD` · gear-1
  `Where: ~/lifehack-brain/system/health/health_invariants.py`
  `Do:` widen the latency threshold check to ignore a single missed heartbeat.
  `Repo: public · V2 · commit local, never push`
  `Commit: 1.1: widen latency threshold tolerance`
  `Done: Verify passes (re-run by plan_retire.py) → retire`

- [ ] **1.2 Add a debounce window to the alert emitter.** `Owner: BUILD` · gear-1
  `Where: ~/lifehack-brain/system/tools/pulse_alert.py`
  `Do:` add a 90-second debounce before the emitter fires a second alert.
  `Repo: public · V2 · commit local, never push`
  `Verify:` — `grep -c "debounce" system/tools/pulse_alert.py` → before `0`, after `1`.
  `Commit: 1.2: add alert debounce window`
  `Done: Verify passes (re-run by plan_retire.py) → retire`

- [ ] **1.3 Log the suppressed-alert count.** `Owner: BUILD` · gear-1
  `Where: ~/lifehack-brain/system/tools/pulse_alert.py`
  `Do:` increment a suppressed-count counter each time debounce swallows an alert.
  `Verify: SHAPE` — `grep -c "suppressed_count" system/tools/pulse_alert.py` → before `0`, after `1`.
  `Commit: 1.3: log suppressed-alert count`
  `Done: Verify passes (re-run by plan_retire.py) → retire`

- [ ] **1.4 Surface the suppressed count on the status tile.** · gear-1
  `Where: ~/lifehack-brain/system/tools/pulse_status.py`
  `Do:` append the suppressed-count value to the end-of-run status tile.
  `Repo: public · V2 · commit local, never push`
  `Verify: SHAPE` — `grep -c "suppressed_count" system/tools/pulse_status.py` → before `0`, after `1`.
  `Commit: 1.4: surface suppressed count on status tile`
  `Done: Verify passes (re-run by plan_retire.py) → retire`

- [ ] **1.5 Rewrite the alert-classification heuristic.** `Owner: BUILD` · gear-2
  `Where: ~/lifehack-brain/system/tools/pulse_alert.py`
  `Do:` replace the fixed threshold with a rolling-median comparison.
  `Repo: public · V2 · commit local, never push`
  `Verify: SHAPE` — `grep -c "rolling_median" system/tools/pulse_alert.py` → before `0`, after `1`.
  `Commit: 1.5: rolling-median alert classification`
  `Done: Verify passes (re-run by plan_retire.py) → retire`

- [ ] **1.6 Backfill a regression test for the debounce window.** `Owner: BUILD` · gear-1
  `Where: ~/lifehack-brain/system/tools/tests/test_pulse_alert.py`
  `Do:` add a test asserting a second alert within 90 seconds is swallowed.
  PARALLEL-LANES: gated on 1.2
  `Repo: public · V2 · commit local, never push`
  `Verify: SHAPE` — `grep -c "test_debounce_swallows" system/tools/tests/test_pulse_alert.py` → before `0`, after `1`.
  `Commit: 1.6: add debounce regression test`
  `Done: Verify passes (re-run by plan_retire.py) → retire`

## Phase 2 — Close the loop and confirm

- [ ] **2.1 Retire the old alert-dedup shim.** `Owner: BUILD` · gear-1
  `Where: ~/lifehack-brain/system/tools/pulse_alert.py`
  `Do:` close #127 and #131 by deleting the deprecated dedup shim they tracked.
  `Repo: public · V2 · commit local, never push`
  `Verify: SHAPE` — `grep -c "dedup_shim" system/tools/pulse_alert.py` → before `1`, after `0`.
  `Commit: 2.1: remove deprecated dedup shim`
  `Done: Verify passes (re-run by plan_retire.py) → retire`

- [ ] **2.2 Move the alert log out of the public tree.** `Owner: BUILD` · gear-1
  `Where: ~/lifehack-brain/system/tools/pulse_alert.py`
  `Do:` point the alert logger at the brain-root log path instead of a repo-local file.
  `Repo: private · commit local, never push`
  `Verify: SHAPE` — `grep -c "brain_root" system/tools/pulse_alert.py` → before `0`, after `1`.
  `Commit: 2.2: log alerts to brain root, not the repo`
  `Done: Verify passes (re-run by plan_retire.py) → retire`

- [ ] **2.3 Sanity-check the debounce window end to end.** `Owner: BUILD` · gear-1
  `Where: ~/lifehack-brain/system/tools/pulse_alert.py`
  `Do:` run the alert emitter twice within 90 seconds and confirm only one alert fires.
  `Repo: public · V2 · commit local, never push`
  `Verify: SHAPE` — re-read the file and confirm it looks right → before `no`, after `yes`.
  `Commit: 2.3: confirm debounce behaves end to end`
  `Done: Verify passes (re-run by plan_retire.py) → retire`

- [ ] **2.4 Confirm the debounce constant is documented.** `Owner: BUILD` · gear-1
  `Where: ~/lifehack-brain/system/tools/pulse_alert.py`
  `Do:` confirm the module docstring already names the debounce constant.
  `Repo: public · V2 · commit local, never push`
  `Verify: SHAPE` — `grep -c "DEBOUNCE_SECONDS" system/tools/pulse_alert.py` → before `1`, after `1`.
  `Commit: 2.4: confirm debounce constant documented`
  `Done: Verify passes (re-run by plan_retire.py) → retire`
