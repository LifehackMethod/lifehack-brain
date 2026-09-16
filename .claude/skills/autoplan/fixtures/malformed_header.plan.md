# Plan: Synthetic malformed-header fixture (card 0R.15)

**Desired outcome:** prove `plan_lint.py` HARD-FAILS (CANNOT-READ, rc=4) on an unparseable
`- [ ] **` card header, instead of folding it into the ordinary per-card `defects` list where
it would read as just one warning among however many others. This file is not real project
work — it exists only so the CLI (and the `UnparseableHeaderHardFail` cases in
`system/tools/test_plan_lint.py`) has something to run against. See `plan_lint.py`'s own module
docstring, card 0R.15.

> **Review:** SKIPPED 2026-09-16 synthetic fixture, no six-lens needed.

## Phase 1 — one good card, one broken header

- [ ] **1.1 A perfectly ordinary card.** `Owner: BUILD`
  `Where: /tmp/fixture/does-not-need-to-exist.py`
  `Do:` nothing real — this card exists only to prove the GOOD card is not what fails.
  `Repo: none`
  `Verify: SHAPE` — `grep -c "x" system/tools/pulse_alert.py` → before `0`, after `1`.
  `Done: Verify passes (re-run by plan_retire.py) → retire`

- [ ] **BROKEN-ID This header's id is not a real id at all.** `Owner: BUILD`
  `Where: /tmp/fixture/does-not-need-to-exist.py`
  `Do:` this card must never parse — its id is letters only, no digit, so the ID pattern
  cannot match it and the whole read must HARD-FAIL rather than silently drop this card.
  `Repo: none`
  `Verify: SHAPE` — `grep -c "x" system/tools/pulse_alert.py` → before `0`, after `1`.
  `Done: Verify passes (re-run by plan_retire.py) → retire`
