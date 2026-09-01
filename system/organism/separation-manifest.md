# Separation manifest — Y.C1 consolidated

One row per tracked file (593 total), each with the verdict from the six Y.C1 sort shards
(sort-system, sort-claude-shared-github, sort-docs-root, sort-sys-rest-1/2/3) plus the two
hand-sorted files (`memory/README.md`, `agents/sentinel.md`). Reconciled against `git ls-files`:
every one of the 593 tracked files appears exactly once below, no duplicates, no gaps.

## Reconciliation notes
- **Duplicate found and resolved**: `.claude/agents/sentinel.md` (analyzed in shard 2:
  HARNESS-UNSHIPPED-FIX, 41-line addition) is a DIFFERENT file from the hand-sorted
  `agents/sentinel.md` (top-level, no `.claude/` prefix — a second, separate tracked file).
  Both exist in `git ls-files`; both now have their own row. Not a real conflict, just two
  distinct paths that look alike.
- **Verdict totals differ from the brief's rough count** (294/52/117/118, sum 581) because: (a)
  several shard files had small arithmetic typos in their own section headers vs the bullets
  actually listed (e.g. shard 1's HARNESS-DIVERGED header said "(15)" but listed 16 bullets;
  its HARNESS-UNSHIPPED-FIX header said "(6)" but listed 5) — this manifest uses the actual
  bullets, verified against `git ls-files`, not the headers; (b) shard 2 additionally carried
  a third category, "HARNESS (stale/orphan/retired, no unique content)" (12 files: the orphaned
  `shared/tools/sentinel_response.py` + the 11 `cal-daily-retired-2026-08-20/` files), which
  doesn't map to the brief's four-verdict taxonomy — folded into HARNESS-IDENTICAL here since
  both are "delete-safe, no unique content to preserve."
- ~~**Final verdict counts (593 total)**: HARNESS-IDENTICAL 296 · HARNESS-DIVERGED 54 ·
  HARNESS-UNSHIPPED-FIX 116 · PERSONAL 127.~~
  **CORRECTED 2026-08-31, authoritative — verified byte-for-byte against `git ls-files` (601/601 exact match, 0 missing, 0 extra):** HARNESS-IDENTICAL **297** · HARNESS-DIVERGED **51** · HARNESS-UNSHIPPED-FIX **122** · PERSONAL **131**. Total **601** (was 593 — the gap was 11 files that had never been classified at all, now added; plus 5 rows whose verdicts the table never updated to match corrections already stated in this file's own prose).

## ⚠ CORRECTION 2026-08-28 (later session) — re-verified live against `upstream/main` @ 7895bbb

The verdicts above were sorted against the tree as it stood. Every bucket was then re-measured
file-by-file against `upstream/main` by comparing blob SHAs. **Three rows were wrong. The row text
above is left standing (no silent overwrite); this block is the correction.**

- **`system/tools/backlog_groom.py` and `system/tools/smoke-check.sh` were `HARNESS-IDENTICAL`
  and are NOT.** Both carried *uncommitted* 2026-08-28 python3 PATH-drift fixes at sort time, so
  they measured identical to upstream. Committed in `d44e093`, they now differ.
  ⛔ **They were one step from being deleted as "byte-identical to upstream" while carrying a fix
  that exists nowhere else.** → reclassified **HARNESS-UNSHIPPED-FIX**, and they must SHIP.
- **`system/hooks/lib/tasks_guard.py` was `HARNESS-DIVERGED` and is byte-identical today**
  → reclassified **HARNESS-IDENTICAL**, delete-safe, nothing to ship.

~~**Corrected counts (still 593):** HARNESS-IDENTICAL **295** · HARNESS-DIVERGED **53** ·
HARNESS-UNSHIPPED-FIX **118** · PERSONAL **127**. Deletion population 295+53+118 = **466**;
ClaudeOps after deletion = **127**. Ship population is **118, not 116**.~~
**SUPERSEDED 2026-08-31 — see the authoritative figures at line ~23-24 above.**

**Precision on the 295 `HARNESS-IDENTICAL`:** only **282 are byte-identical to upstream**. The
other **13 do not exist upstream at all** and are delete-safe on *retired/orphan* grounds, which is
a different and weaker justification than byte-identity: the 11 `cal-daily-retired-2026-08-20/`
files, `shared/tools/sentinel_response.py` (orphaned), and `agents/sentinel.md` (hand-sorted,
"plugin-served"). ⚠ Before deleting those 13, confirm the content genuinely exists elsewhere —
for `agents/sentinel.md` that means confirming the plugin actually serves it. "Absent upstream"
is not by itself evidence that anything preserves it.

### ⛔ SECOND CORRECTION — one of those 13 is NOT delete-safe (checked 2026-08-28)

The 13 were checked rather than assumed. Two groups cleared, one did not:

- **`cal-daily-retired-2026-08-20/` (11 files) — SAFE.** The retirement banner names `planning-daily`,
  which is live in the active plugin install (v0.3.13) with matching prompt/reference files.
- **`shared/tools/sentinel_response.py` — SAFE.** Every live caller (`ingest_gate.py`, `safe_input.py`,
  `sentinel_ack.py`, `sentinel-health.py`) hardcodes `shared/gate/`, never `shared/tools/`. Measured by
  grepping every `.py/.md/.json/.sh` in the repo; a dynamically-built path would not show up, and none
  was found.
- ⛔ **`agents/sentinel.md` — NOT SAFE. The "plugin-served" justification is false for this exact path.**
  Verified directly: the active install is v0.3.13, and v0.3.13 ships `.claude/agents/sentinel.md` but has
  **no top-level `agents/sentinel.md` at all**. That path survives only in stale cache versions (0.1.0,
  0.2.3, 0.3.0, 0140d8d179a5) which a prune or reinstall would remove. It is also absent upstream. It is a
  distinct blob from `.claude/agents/sentinel.md` (`629fb11` vs `84ca138`), so the sibling does not
  preserve it either.
  ⇒ **Deleting it would put its content durably nowhere. Do not delete it in the D4 sweep** — keep it, or
  ship/preserve it deliberately first. This is exactly the case §⑤'s order exists to catch.

**Two clean results worth stating:** all 118 UNSHIPPED-FIX files genuinely differ from or are
absent upstream (0 would ship a no-op), and 126 of 127 PERSONAL files are absent upstream. The one
exception, `.claude/settings.json`, exists upstream with different content — his own guard
registrations against the harness's. Correctly classified PERSONAL; no leak.

### ⛔ THIRD CORRECTION — the two UNPROVEN files are NOT delete-safe (checked 2026-08-30)

The Y.C2 delete list left exactly two files UNPROVEN rather than guessing. Both were resolved, and
**both turned out to hold content that exists nowhere else.** This is precisely what the standing order
— *nothing is deleted until its content exists somewhere permanent* — exists to catch.

- ⛔ **`system/egress-allowlist.md` — MOVED FROM DELETE TO KEEP.** It carries an allowlist line for
  `fred.stlouisfed.org`, absent from `upstream/main` AND from the delivery branch. The tool that needs it,
  `marc-data-fetch.py`, **is still live**: present in the AI Brain with a compiled `__pycache__` (evidence
  of recent execution), it calls that host directly, it is chained by `marc-health-run.sh`, and
  `system/pulse-config.md` still lists `marc-health` as a job. `system/requirements.txt` pins `yfinance`
  for it specifically. ⇒ Deleting this file would strip the egress wall's ONLY permission record for a
  host a live tool calls. It is personal infrastructure config and belongs in the KEEP set.
- ⚠ **`INSTALL.md` — CONDITIONAL, port before deleting.** Its Cowork paragraph (private lines 34-42,
  opening *"⚠ If the answer is Cowork, that is its own case…"*) is confirmed absent from both
  `upstream/main:INSTALL.md` and the `ship/ALL-combined` delivery copy. It is generic, non-identifying
  install-robustness guidance — worth keeping. ⇒ Port it into the delivery branch first; only then is
  deleting the private copy safe.

~~**Corrected counts (still 593):** deletion population **464** (was 465); keep set **129** (was 128).
464 + 129 = 593 ✓~~
**SUPERSEDED 2026-08-31:** using the authoritative bucket counts above, deletion population (HARNESS-IDENTICAL+HARNESS-DIVERGED+HARNESS-UNSHIPPED-FIX) = 297+51+122 = **470**; keep population (PERSONAL) = **131**. 470+131 = **601** ✓.

## Hazard scan of the HARNESS-UNSHIPPED-FIX bucket (116 files)
Grepped every file for name-hazard tokens (case-insensitive). File:line counts only, no content
printed, no absolute paths:
- `system/parked/2026-08-23-ruled-out-resurrections/.claude/skills/skill-builder/scripts/forbidden_content.py` — 4 lines (10, 165, 166, 201). Previously known as "3 lines"; rescan found a 4th. ⛔ FLAGGED, excluded from all PR batches below, must never ship.
- 8 other files hit the same grep (architect SKILL.md/order_lint.py, guard_gh_account_switch.sh, pulse-config.md, recovery-runbook.md, test_section_archive.py.retired-2026-08-24, loop_probe.sh, check_no_internal_leakage.py) — 34 combined line hits, all in narrative/comment context (dated-fix prose, leak-detector pattern definitions, or commit-log-style annotations), not baked-into-shipped-data like the flagged file. Worth a second look before shipping but not the same hazard class; full file:line list in `work/hazard_scan.txt` alongside this manifest's source materials.

| Path | Verdict | Reason |
|---|---|---|
| `.claude/README.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `.claude/agents/ingest-conclusions.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `.claude/agents/ingest-reader.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `.claude/agents/ingest-tagger.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `.claude/agents/web-searcher.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `.claude/skills/cal-daily-retired-2026-08-20/SKILL.md` | HARNESS-IDENTICAL | retired harness machinery superseded by planning-daily, delete-safe |
| `.claude/skills/cal-daily-retired-2026-08-20/prompts/00-lookback.md` | HARNESS-IDENTICAL | retired harness machinery superseded by planning-daily, delete-safe |
| `.claude/skills/cal-daily-retired-2026-08-20/prompts/01-clear-surfaces.md` | HARNESS-IDENTICAL | retired harness machinery superseded by planning-daily, delete-safe |
| `.claude/skills/cal-daily-retired-2026-08-20/prompts/02-lanes.md` | HARNESS-IDENTICAL | retired harness machinery superseded by planning-daily, delete-safe |
| `.claude/skills/cal-daily-retired-2026-08-20/prompts/03-logistics.md` | HARNESS-IDENTICAL | retired harness machinery superseded by planning-daily, delete-safe |
| `.claude/skills/cal-daily-retired-2026-08-20/prompts/04-rank.md` | HARNESS-IDENTICAL | retired harness machinery superseded by planning-daily, delete-safe |
| `.claude/skills/cal-daily-retired-2026-08-20/prompts/04.5-consolidate.md` | HARNESS-IDENTICAL | retired harness machinery superseded by planning-daily, delete-safe |
| `.claude/skills/cal-daily-retired-2026-08-20/prompts/05-act.md` | HARNESS-IDENTICAL | retired harness machinery superseded by planning-daily, delete-safe |
| `.claude/skills/cal-daily-retired-2026-08-20/references/lane-board.md` | HARNESS-IDENTICAL | retired harness machinery superseded by planning-daily, delete-safe |
| `.claude/skills/cal-daily-retired-2026-08-20/references/purpose.md` | HARNESS-IDENTICAL | retired harness machinery superseded by planning-daily, delete-safe |
| `.claude/skills/cal-daily-retired-2026-08-20/references/question-style.md` | HARNESS-IDENTICAL | retired harness machinery superseded by planning-daily, delete-safe |
| `PUSH-FORWARD.md` | HARNESS-IDENTICAL | byte-identical to upstream |
| `README.md` | HARNESS-IDENTICAL | byte-identical to upstream |
| `REPAIR.md` | HARNESS-IDENTICAL | byte-identical to upstream |
| `TARGET-STATE.md` | HARNESS-IDENTICAL | byte-identical to upstream |
| `UPDATE.md` | HARNESS-IDENTICAL | byte-identical to upstream |
| `agents/sentinel.md` | HARNESS-IDENTICAL | hand-sorted: harness, plugin-served, deletes safely |
| `docs/LOCAL-INSTRUCTIONS.md` | HARNESS-IDENTICAL | byte-identical to upstream |
| `docs/OUTSIDE-SERVICES.md` | HARNESS-IDENTICAL | byte-identical to upstream |
| `docs/REPORT-A-BUG.md` | HARNESS-IDENTICAL | byte-identical to upstream |
| `docs/skill-conformance.md` | HARNESS-IDENTICAL | byte-identical to upstream |
| `memory/README.md` | HARNESS-IDENTICAL | hand-sorted by prior session |
| `shared/bounded_input.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/brain_root.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/cal_config.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/emit/verdicts.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/gate/ingest_gate.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/gate/sentinel_ack.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/gate/sentinel_quarantine.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/gate/sentinel_response.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/gate/test_ingest_gate.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/gate/test_sentinel_response.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/notify/notify-governor.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/notify/notify-send.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/notify/test_notify.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/paths.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/registry.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/test_bounded_input.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/test_brain_root.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/test_paths.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/test_registry.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/tools/calendar_store_sync.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/tools/email_convert.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/tools/email_service_contract.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/tools/email_service_read.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/tools/email_summary_run.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/tools/email_summary_sync.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/tools/email_thread_schema.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/tools/hitl_note_store.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/tools/intake_backfill.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/tools/intake_backfill_batch.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/tools/intake_reader.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/tools/item_schema.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/tools/item_store_read.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/tools/item_store_window.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/tools/sentinel_response.py` | HARNESS-IDENTICAL | stale orphan superseded by gate/sentinel_response.py, no unique content |
| `shared/tools/store_date_index.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `shared/tools/tasks_store_sync.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/build-rules-index.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/confidence-model.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/desk-registry.yaml` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/factory/classify_clause.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/factory/defeater.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/factory/extract_clauses.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/factory/spec_units.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/google-capability-registry.yaml` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/google-policy.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/gws-contract.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/altitude_flag.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/announce_plan_write.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/enforce_egress_allowlist.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/enforce_egress_allowlist.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/enforce_multiphase_contract.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/enforce_skill_frontmatter.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_agent_return_channel.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_canon_write.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_checkin_needs_project.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_cross_project_write.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_egress.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_findings_write.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_gmail_destructive.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_gmail_send.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_gws_logout.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_ledger_discipline.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_no_repoint_into_claudeops.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_no_repoint_into_claudeops.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_organism_map.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_plan_structure.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_pm_flag_store.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_sheet_formula_writes.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_sheet_writes.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_statusline_lock.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/guard_throughline_write_scope.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/ingest_gate_enforce.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/inject_compute_mechanically.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/inject_delegation_standing.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/inject_sop_before_build.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/inject_work_altitude.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/lib/bash_write_door.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/lib/gws_guard.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/numbers_flag.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/observability_logger.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/plan_flag.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/rating_capture.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/save_routing_hint.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/scratch_capture_gate.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/scratch_flag.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/scratch_sweep_nudge.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/session_context_loader.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/session_flight_recorder.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/skill_anchor.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/skill_anchor_inject.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/tests/test_bash_write_door.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/tests/test_calendar_guard.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/tests/test_egress_wall.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/tests/test_findings_and_delegation.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/tests/test_gmail_send_guard.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/tests/test_numbers_mode.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/tests/test_organism_map_guard.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/tests/test_plan_lock_override.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/tests/test_ported_batch_guards.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/tests/test_ported_batch_observers.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/tests/test_session_context_loader.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/tests/test_sheet_guards.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/tests/test_tasks_guard.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/tests/test_throughline_scope.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/tests/test_write_custody_guards.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/tests/verify-pm-guard.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/throughline_flag.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/hooks/validate_on_write.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/information-ingestion-interpretation.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/ingestion-reader-contract.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/intent-doctrine.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/knowledge-altitude.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/memory-system.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/organism-manual-extract.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/organism/elements/brain.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/organism/elements/calculate.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/organism/elements/email-service.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/organism/elements/ingest-gate.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/organism/elements/red-team.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/organism/elements/research-web-plane.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/organism/elements/topic-vocab-lint.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/organism/map-format-specs.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/parts/fanout_gate.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/parts/forbidden_content.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/parts/move_aside.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/parts/order_lint.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/parts/phase_gate.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/parts/residue_scrub.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/parts/section_present.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/parts/voted_judge.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/parts/write_ledger.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/safe-fetch-allowlist.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/schemas/backlog-entry-schema.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/schemas/email-summary-schema.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/schemas/ingest-gate-signature.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/schemas/managed-file-frontmatter.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/security-canon.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/shipping-lane/fixtures/clean-fixture.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/shipping-lane/fixtures/identity-fixture.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/shipping-lane/fixtures/refuse-fixture.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/shipping-lane/fixtures/semantic-fixture.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/shipping-lane/judge.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/shipping-lane/run_selftests.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/shipping-lane/verify_rules.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/sops/architecture-planning-sop.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/sops/deck-design-system.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/sops/design-process-sop.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/sops/desk-building-sop.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/sops/google-sheet-sop.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/sops/plan-sharpening-sop.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/sops/skill-building-sop-extract.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/sops/skill-building-sop.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/statusline.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/templates/telos-starter.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/archivist-audit-run.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/archivist-deepmine-run.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/assert_dispatch_fidelity.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/audit_compaction.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/backlog-health.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/backlog_groom.py` | HARNESS-UNSHIPPED-FIX | byte-identical to upstream/main. CORRECTED 2026-08-31: carries an uncommitted 2026-08-28 python3 PATH-drift fix (committed in d44e093) that now differs from upstream; must ship, not delete-safe. |
| `system/tools/canon_conflict_scan.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/check-my-notes.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/checkin/board_check.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/checkin/checkin_open.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/checkin/gauge_check.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/checkin/test_board_check.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/checkin/test_checkin_open.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/checkin/test_gauge_check.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/claude-auth.lib.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/conformance-lab/driver.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/conformance-lab/probes/__init__.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/conformance-lab/rule-registry.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/agent_output.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/basket_review.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/conclusions_review.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/corpus-map-schema.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/desk_scaffold.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/filer_review.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/flatten.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/folder_scaffold.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/intake.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/pipeline.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/tag.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/test_folder_branch.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/test_pad_init.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/test_scan_evidence.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/test_sort_to_baskets.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/test_split_orphans_empty_basket.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/test_topic_check.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/test_world_map.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/cowork-ingest/wmb_commit.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/deadend_check.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/emit_finding.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/emit_recommendation.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/emit_status.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/encoding_audit.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/fault-proposer-run.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/fault_proposer.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/findings_deadman.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/findings_reader.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/guard_fire_test_record.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/gws-auth.lib.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/health_invariants.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/health_line.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/hook_path_resolve.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/identity_secret_drift_check.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/ingest_coverage.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/ingest_setdiff.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/map_integrity_check.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/new-skill.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/plan_git_check.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/planning-analysis/big-rocks.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/planning-analysis/cracks.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/planning-analysis/logistics.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/planning-analysis/synthesize.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/planning-diary-capture.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/planning-diary-rollup.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/planning-diary-run.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/planning-health.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/planning-lifemap-write.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/planning-light-sweep.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/planning-vault-pull.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/planning-vault-run.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/planning-window-to-vault.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/project-manager/check_slug_folder.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/project-manager/test_check_slug_folder.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/recommend.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/recommendation_disposition.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/recommendations_reader.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/render_shot.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/safe_csv.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/safe_docx.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/safe_fetch.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/safe_input.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/safe_pdf.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/safe_read.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/safe_search_api.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/safe_xlsx.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/sanitize.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/save/pad_archive.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/save/pm_flag_recover.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/save/save_step_ledger.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/save/test_pad_archive.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/save/test_save_step_ledger.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/seam_reason.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/security-health.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/sentinel-health-run.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/sentinel-health.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/skill_hud.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/skill_promise_check.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/skill_promise_sweep.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/smoke-check.sh` | HARNESS-UNSHIPPED-FIX | byte-identical to upstream/main. CORRECTED 2026-08-31: same PATH-drift fix situation as backlog_groom.py; must ship. |
| `system/tools/statusline-truth-test.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/system-health-run.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/system-health.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/test_agent_pins.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/test_canon_conflict_scan.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/test_egress_level2.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/test_planning_diary_capture.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/test_safe_readers.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/test_sanitize.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/test_utf8_stdio.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/tests/test_pulse_state_path.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/untrack-my-stuff.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/utf8_stdio.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/validate_frontmatter.py` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/verify-hooks.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/tools/verify-ship-skill.sh` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `system/work-altitude-doctrine.md` | HARNESS-IDENTICAL | byte-identical to upstream/main |
| `.gitattributes` | HARNESS-DIVERGED | local carries extra explanatory block, documentation-only divergence |
| `.github/workflows/exercise-loop.yml` | HARNESS-DIVERGED | ClaudeOps missing upstream's later fork-guard/secret-scoping fixes; stale not ahead, safe to delete |
| `.github/workflows/no-internal-leakage-baseline.yml` | HARNESS-DIVERGED | ClaudeOps missing upstream's later fork-guard/secret-scoping fixes; stale not ahead, safe to delete |
| `.github/workflows/no-internal-leakage.yml` | HARNESS-DIVERGED | ClaudeOps missing upstream's later fork-guard/secret-scoping fixes; stale not ahead, safe to delete |
| `CLAUDE.md` | HARNESS-DIVERGED | local edits track ClaudeOps in-progress separation state, not vetted upstream-ready fixes |
| `INSTALL.md` | PERSONAL | large divergence both directions; local stale on install-path section, possible unshipped Cowork paragraph needs review. CORRECTED 2026-08-31: conditional keep — its Cowork paragraph (private lines 34-42) is absent from both upstream/main and the ship/ALL-combined delivery copy; must be ported into the delivery branch before this private copy can be deleted. |
| `docs/LIVE-CLASS-CRIB.md` | HARNESS-DIVERGED | title changed + ClaudeOps-separation-status annotations added, not a portable fix |
| `docs/data-layout.md` | HARNESS-DIVERGED | one line maintainer-specific framing vs upstream, not a portable fix |
| `system/council-framings.md` | HARNESS-DIVERGED | ClaudeOps NEWER (has /architect "here now" status; upstream still says lands later phase 3) |
| `system/egress-allowlist.md` | PERSONAL | ClaudeOps has one extra line (fred.stlouisfed.org, personal marc-data-fetch.py dependency), not present upstream. CORRECTED 2026-08-31: moved off the delete population — carries the only allowlist record for fred.stlouisfed.org, needed by the still-live marc-data-fetch.py tool; must not be deleted. |
| `system/hooks/buried_command_hint.sh` | HARNESS-DIVERGED | ClaudeOps OLDER (missing upstream's 2026-08-23 correction block) + "Enver" -> "the operator" genericization |
| `system/hooks/guard_brief_truncation.sh` | HARNESS-DIVERGED | cosmetic only (stat -c/-f fallback order swapped, both sides work) |
| `system/hooks/guard_calendar_writes.sh` | HARNESS-DIVERGED | ClaudeOps OLDER (missing upstream's fail-open-on-unreadable-payload fix) |
| `system/hooks/guard_disable_model_invocation.sh` | HARNESS-DIVERGED | cosmetic only ("Enver" -> "the operator") |
| `system/hooks/guard_harness_writeback.sh` | HARNESS-DIVERGED | cosmetic only ("Enver" -> "the operator") |
| `system/hooks/guard_hook_sop_read.sh` | HARNESS-DIVERGED | cosmetic only (stat -c/-f order swapped) |
| `system/hooks/guard_tasks_writes.sh` | HARNESS-DIVERGED | ClaudeOps OLDER (missing upstream's fail-open-on-unreadable-payload fix, same class as guard_calendar_writes.sh) |
| `system/hooks/lib/tasks_guard.py` | HARNESS-IDENTICAL | content byte-identical; only the executable bit differs (755 vs 644). CORRECTED 2026-08-31: re-verified byte-identical to upstream; delete-safe. |
| `system/hooks/lib/winpath_fold.sh` | HARNESS-DIVERGED | cosmetic only ($USER vs literal "name" in a comment example) |
| `system/hooks/pm_flag.sh` | HARNESS-DIVERGED | ClaudeOps OLDER (missing upstream's 2026-08-28 Windows-absolute-path fix — worth backporting, but ClaudeOps deletion loses nothing since ups |
| `system/hooks/pm_persist.sh` | HARNESS-DIVERGED | ClaudeOps OLDER (missing the same 2026-08-28 absolute-path fix + a stat-mount-point GNU/BSD fix; upstream already has both) |
| `system/hooks/tests/test_guard_checkin_needs_project.sh` | HARNESS-DIVERGED | structural divergence, tied to ClaudeOps-only registrations.json (see PERSONAL) vs upstream's settings.json-only test |
| `system/hooks/tests/test_ingest_gate_enforce.sh` | HARNESS-DIVERGED | cosmetic wording only (same fixture-case fix, ClaudeOps has older "PORTED-FIXTURE" phrasing, upstream reworded for public + more detail) |
| `system/hooks/tests/test_pm_lock_override.sh` | HARNESS-DIVERGED | ClaudeOps OLDER (missing upstream's new "section 14" Windows-abs-path test, matches the pm_flag.sh gap) |
| `system/hooks/tests/test_winpath_fold.sh` | HARNESS-DIVERGED | ClaudeOps swapped the generic `/opt/repo` test fixture paths for home-folder-style absolute ones; test data only, no behavior change. ⚠ HAZARD: a fixture carrying a real account name must never ship — rewrite the fixture generic before this file is reconciled. |
| `system/organism/elements/backlog-authority.md` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/organism/elements/compute-mechanically-gate.md` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/organism/elements/egress-allowlist-wall.md` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/organism/elements/grand-central.md` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/organism/elements/hook-plane.md` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/organism/elements/ingest-run-lib.md` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/organism/elements/label-checker.md` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/organism/elements/planning.md` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/organism/elements/pulse-cron.md` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/organism/elements/scratch-capture-gate.md` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/organism/elements/skill-system.md` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/organism/elements/world-model-ingestion.md` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/schemas/project-doc-schema.md` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/sops/build-sop.md` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/sops/hook-sop.md` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/sops/translator-rubric.md` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/tools/conformance-lab/probes/guard.py` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/tools/cowork-ingest/corpus_map.py` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/tools/cowork-ingest/gate_and_pack.py` | HARNESS-DIVERGED | ~~ClaudeOps is BEHIND: missing upstream's newer "explore" slice mode / explore_char_slice, added for step 2.9 EXPLORE re-read~~ ⚠ CORRECTED 2026-09-01 (stale claim re-entered the tree this morning, still wrong after the fix): commit `e91b942` (2026-08-27) wired `explore_char_slice` into this file — verified live at `gate_and_pack.py:150` (`clean = explore_char_slice(clean)`, reached via the `elif args.slice == "explore":` branch at line 149); no longer behind. |
| `system/tools/cowork-ingest/scan_collect.py` | HARNESS-DIVERGED | ~~ClaudeOps is BEHIND: missing upstream's newer --store-cap CLI option for the EXPLORE re-read's longer gist~~ ⚠ CORRECTED 2026-09-01 (stale claim re-entered the tree this morning, still wrong after the fix): commit `e91b942` (2026-08-27) parameterised `store_cap` with a `--store-cap` CLI flag — verified live at `scan_collect.py:143` (`ap.add_argument("--store-cap", type=int, default=STORE_CAP, ...)`) feeding `collect(..., store_cap=a.store_cap)` at line 149; no longer behind. |
| `system/tools/cowork-ingest/scan_review.py` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/tools/encoding_lint.py` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/tools/fault_ledger.py` | HARNESS-DIVERGED | ClaudeOps still calls force_utf8_stdio() at import; upstream refactored this away — ClaudeOps is stale, not carrying a unique fix |
| `system/tools/hook-doc-lint.sh` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/tools/install-schedulers.sh` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/tools/read_sop.sh` | HARNESS-DIVERGED | comment-wording only — both sides have the identical shasum-fallback code; ClaudeOps' comment cites GitHub #82, upstream's doesn't; no functional delt |
| `system/tools/run-all-tests.sh` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `system/tools/skill_capability_check.py` | HARNESS-DIVERGED | same force_utf8_stdio() staleness as fault_ledger.py, plus upstream added the executable bit |
| `system/tools/test_encoding_lint.py` | HARNESS-DIVERGED | diverged, no destructive-if-deleted local-only fix found |
| `.claude/agents/archivist.md` | HARNESS-UNSHIPPED-FIX | local rewrite adds Authority Boundary section, new checks; unshipped audit-logic |
| `.claude/agents/sentinel.md` | HARNESS-UNSHIPPED-FIX | 41-line addition: dated rationale block for tools: line, citing advisory-council veto |
| `.claude/agents/worker.md` | HARNESS-UNSHIPPED-FIX | 5-line addition: new ingest-gate trusted-zone refusal rule |
| `.claude/skills/architect/SKILL.md` | HARNESS-UNSHIPPED-FIX | desk:root harness skill, absent from upstream and plugin cache, not yet shipped |
| `.claude/skills/architect/references/routing-eval.md` | HARNESS-UNSHIPPED-FIX | desk:root harness skill, absent from upstream and plugin cache, not yet shipped |
| `.claude/skills/architect/scripts/order-rules.json` | HARNESS-UNSHIPPED-FIX | desk:root harness skill, absent from upstream and plugin cache, not yet shipped |
| `.claude/skills/architect/scripts/order_lint.py` | HARNESS-UNSHIPPED-FIX | desk:root harness skill, absent from upstream and plugin cache, not yet shipped |
| `.claude/skills/audit/SKILL.md` | HARNESS-UNSHIPPED-FIX | desk:root harness skill, absent from upstream and plugin cache, not yet shipped |
| `.claude/skills/audit/references/routing-eval.md` | HARNESS-UNSHIPPED-FIX | desk:root harness skill, absent from upstream and plugin cache, not yet shipped |
| `.github/PULL_REQUEST_TEMPLATE.md` | HARNESS-UNSHIPPED-FIX | absent from upstream/main and plugin cache; in-progress PR-body citation gate feature |
| `.github/scripts/check_fix_needs_pr_body_citation.py` | HARNESS-UNSHIPPED-FIX | absent from upstream/main and plugin cache; in-progress PR-body citation gate feature |
| `.github/scripts/check_no_internal_leakage.py` | HARNESS-UNSHIPPED-FIX | 157 ins/81 del vs upstream; active load-bearing leak-scan security work |
| `.github/scripts/demo_fixture.diff` | HARNESS-UNSHIPPED-FIX | absent from upstream/main and plugin cache; in-progress PR-body citation gate feature |
| `.github/scripts/demo_fixture_false_positive.diff` | HARNESS-UNSHIPPED-FIX | absent from upstream/main and plugin cache; in-progress PR-body citation gate feature |
| `.github/scripts/demo_fixture_ordinary.diff` | HARNESS-UNSHIPPED-FIX | absent from upstream/main and plugin cache; in-progress PR-body citation gate feature |
| `.github/scripts/demo_pr_body_missing.txt` | HARNESS-UNSHIPPED-FIX | absent from upstream/main and plugin cache; in-progress PR-body citation gate feature |
| `.github/scripts/demo_pr_body_present.txt` | HARNESS-UNSHIPPED-FIX | absent from upstream/main and plugin cache; in-progress PR-body citation gate feature |
| `.github/scripts/test_check_no_internal_leakage.py` | HARNESS-UNSHIPPED-FIX | paired test for check_no_internal_leakage.py fix |
| `.github/scripts/test_line_boundary_bypass.py` | HARNESS-UNSHIPPED-FIX | absent from upstream/main and plugin cache; in-progress PR-body citation gate feature |
| `.github/workflows/fix-citation-required.yml` | HARNESS-UNSHIPPED-FIX | absent from upstream/main and plugin cache; in-progress PR-body citation gate feature |
| `.gitignore` | HARNESS-UNSHIPPED-FIX | adds *.bak-* and system/organism/generated/ ignore-gap fixes; also a donor-spillover comment line, flag before shipping |
| `system/githooks/pre-commit` | HARNESS-UNSHIPPED-FIX | carries the internal-leakage/operator-identity scan block entirely absent from upstream (upstream doesn't need it — no personal identity in  |
| `system/hook-contract.md` | HARNESS-UNSHIPPED-FIX | carries 2026-08-24 CORRECTED note fixing wrong symlink claim; upstream still has old wrong checklist line |
| `system/hooks/guard_gh_account_switch.sh` | HARNESS-UNSHIPPED-FIX | carries a 2026-08-28 "FAIL-OPEN, found" fix (adds CLAUDE_PROJECT_DIR as a zone-root candidate so the plugin-distributed copy doesn't silentl |
| `system/hooks/guard_git_add_class.sh` | HARNESS-UNSHIPPED-FIX | carries a 2026-08-28 fix removing a quote-blanking regex that falsely flagged quoted pathspecs with spaces (Windows) as "no pathspec"; upstr |
| `system/hooks/guard_write_paths.sh` | HARNESS-UNSHIPPED-FIX | large diff (145 ins / 390 del); ClaudeOps carries multiple 2026-08-28-dated "ZONE-ESCAPE FIX (found + evidenced ..., b3-tests)" blocks entir |
| `system/hooks/tests/test_winpath_fold_extra_shapes.sh` | HARNESS-UNSHIPPED-FIX | Windows winpath-fold test, absent from upstream/main and plugin cache 0.3.13; generic hook-test infra not yet shipped |
| `system/hooks/tests/test_write_paths_guard.sh` | HARNESS-UNSHIPPED-FIX | adds 2 test blocks absent upstream: global ~/.claude/settings.json protection coverage, and a 2026-07-13-incident regression test ("mentioning a prote |
| `system/hooks/tests/test_youtube_url_route.sh` | HARNESS-UNSHIPPED-FIX | part of YouTube transcript pipeline (commit "Land the YouTube transcript pipeline that was running untracked"), generic, unshipped |
| `system/machine-readiness-checklist.md` | HARNESS-UNSHIPPED-FIX | generic build-process reference doc, desk:root, no Enver-only content, unshipped |
| `system/organism/elements/archivist.md` | HARNESS-UNSHIPPED-FIX | carries multiple "CORRECTED 2026-08-27" (L.B2 audit) live-behavior corrections not in upstream |
| `system/organism/elements/build-plan-plane.md` | HARNESS-UNSHIPPED-FIX | carries a "CORRECTED 2026-08-27" note flagging the autoplan-plan-mode section below as describing a superseded mechanism |
| `system/organism/elements/canon.md` | HARNESS-UNSHIPPED-FIX | ClaudeOps has 2026-08-27 factual corrections (session_context_loader.sh mechanism, guard_write_paths.sh gap) that upstream lacks |
| `system/organism/elements/claude-md-pyramid.md` | HARNESS-UNSHIPPED-FIX | multiple 2026-08-27 audit corrections not in upstream |
| `system/organism/elements/council-engine.md` | HARNESS-UNSHIPPED-FIX | ClaudeOps has clarified/merged citation prose upstream lacks (cosmetic-adjacent but content differs, not just backticks) |
| `system/organism/elements/efficiency.md` | HARNESS-UNSHIPPED-FIX | multiple 2026-08-27 audit corrections not in upstream |
| `system/organism/elements/google-sheet.md` | HARNESS-UNSHIPPED-FIX | CORRECTED note: the google-sheet skill moved to the plugin plane, not a repo-tracked skills/ dir; absent upstream |
| `system/organism/elements/gws-plane.md` | HARNESS-UNSHIPPED-FIX | ClaudeOps has 2026-08-27 live-verification corrections (permissions.ask key absent; MCP calendar guard via permissions.deny) upstream lacks |
| `system/organism/elements/health-invariants.md` | HARNESS-UNSHIPPED-FIX | 3 live-behavior corrections (CRITICAL_HOOKS superseded, HEARTBEAT_STALE_S rename, deadman actually runs via cron not launchd on this machine) absent u |
| `system/organism/elements/hospital.md` | HARNESS-UNSHIPPED-FIX | ClaudeOps has merged/clarified exclusion citations + VALID_STATUS set correction (adds DRIFT) upstream lacks |
| `system/organism/elements/item-store.md` | HARNESS-UNSHIPPED-FIX | ClaudeOps has 2026-08-27 correction of sync cadence (86400s not 21600s) and primary-machine-gated claim upstream lacks |
| `system/organism/elements/journal.md` | HARNESS-UNSHIPPED-FIX | corrects guard_write_paths.sh line number AND a live-tested finding that the clone-copy write is NOT actually blocked, contradicting the plain claim u |
| `system/organism/elements/notify-plane.md` | HARNESS-UNSHIPPED-FIX | ClaudeOps has 2026-08-27 corrections (notify-send.sh path moved to shared/notify/, DAILY_CAP=3 enforced not 0) upstream lacks |
| `system/organism/elements/plan-integrity-cluster.md` | HARNESS-UNSHIPPED-FIX | 2 corrections: plan_flag.sh record DOES block on re-arm mismatch (not "never blocks"), and the mtime cross-wire bug is demoted to a rare fallback path |
| `system/organism/elements/pm-flag.md` | HARNESS-UNSHIPPED-FIX | ClaudeOps has 2026-08-27 live-test corrections (test_pm_lock_override.sh PASS=75 not 61; plan store now covered by guard_pm_flag_store.sh) upstream la |
| `system/organism/elements/project-manager.md` | HARNESS-UNSHIPPED-FIX | 14 correction annotations, absent upstream |
| `system/organism/elements/read.md` | HARNESS-UNSHIPPED-FIX | ClaudeOps has 2026-08-27/28 corrections (pulse-brief.md not loaded by session_context_loader.sh; guard_canon_write.sh authority rail dropped 2026-08-1 |
| `system/organism/elements/safe-reader-plane.md` | HARNESS-UNSHIPPED-FIX | ClaudeOps has 2026-08-27 corrections (_audit_email_read param name 'reader' not 'lane'; log path; six matchers not four) upstream lacks |
| `system/organism/elements/save.md` | HARNESS-UNSHIPPED-FIX | 8 correction annotations, absent upstream |
| `system/organism/elements/security-ingest-gate.md` | HARNESS-UNSHIPPED-FIX | ClaudeOps has 2026-08-27 correction (manifest grew to 16 violation/6 allow cases, not 6/3) upstream lacks |
| `system/organism/elements/sentinel.md` | HARNESS-UNSHIPPED-FIX | corrects pulse-config.md line number, AND flags that Gmail quarantine is a total no-op by default (SENTINEL_QUARANTINE_TOOL unset nowhere in repo) wit |
| `system/organism/elements/statusline-hud.md` | HARNESS-UNSHIPPED-FIX | ClaudeOps has 2026-08-27 correction (plan_flag.sh record branch uses tool_input.planFilePath, not primarily newest-mtime glob) upstream lacks |
| `system/organism/elements/strategic-navigation-cluster.md` | HARNESS-UNSHIPPED-FIX | corrects $EVAL_TTL_MIN → actual THROUGHLINE_TTL_MIN, and the real scratchpad DEST path in code vs docs |
| `system/organism/elements/translator-cluster.md` | HARNESS-UNSHIPPED-FIX | ClaudeOps documents /simplify->/condense rename and skill-location verification upstream lacks |
| `system/organism/elements/where-things-live.md` | HARNESS-UNSHIPPED-FIX | multiple 2026-08-27 audit corrections absent upstream |
| `system/organism/manual.md` | HARNESS-UNSHIPPED-FIX | ClaudeOps has multiple 2026-08-24/25/27 live-verification corrections (two-machine ruling reversed 2026-08-22; compute-mechanically-gate not dormant;  |
| `system/parked/2026-08-23-ruled-out-resurrections/.claude/skills/skill-builder/scripts/forbidden_content.py` | HARNESS-UNSHIPPED-FIX | ⛔ TRAP: absent from upstream/main AND absent by this exact path from plugin cache, BUT it is the SAME file as cache's system/parts/forbidden_content.p |
| `system/parts/capture_gate_selftest.py` | HARNESS-UNSHIPPED-FIX | ClaudeOps fixes the selftest's expected receipt string ('Scratchpad: N lines captured, verified' vs stale 'SCRATCHPAD CAPTURED') upstream lacks |
| `system/parts/completeness_receipt.py` | HARNESS-UNSHIPPED-FIX | replaces upstream's plain report() call with an explanatory comment block on why the lab-fixture check is intentionally [SKIP] not a gate-blocking FAI |
| `system/parts/fanout_completeness.py` | HARNESS-UNSHIPPED-FIX | generic reusable "Parts Library" component (A4+B3), unshipped |
| `system/parts/run_selftests.sh` | HARNESS-UNSHIPPED-FIX | ClaudeOps adds SKIP-tracking (a skipped check no longer silently counts as a pass) upstream lacks |
| `system/pulse-config.md` | HARNESS-UNSHIPPED-FIX | 39 correction annotations, by far the largest audit-correction file; absent upstream |
| `system/requirements.txt` | HARNESS-UNSHIPPED-FIX | commit msg explicitly: "make venue-probe checks + requirements.txt machine-portable, not Enver-only" — generic infra, unshipped |
| `system/security-posture-baseline.md` | HARNESS-UNSHIPPED-FIX | generic security reference doc, desk:root, unshipped |
| `system/shipping-lane/canon.py` | HARNESS-UNSHIPPED-FIX | ClaudeOps fixes DEFECT (found 2026-08-28): armed-ness of the personal-tier now read off the rules themselves, not the call site -- closes a near-leak  |
| `system/shipping-lane/identity_rules.py` | HARNESS-UNSHIPPED-FIX | THE TRAP: local-only FLEX_WS/LINE_BOUNDARY_CHARS fix (2026-08-28) closing a scrub-bypass on hard-wrapped multi-word identity terms; absent u |
| `system/shipping-lane/public-remotes.json` | HARNESS-UNSHIPPED-FIX | the actual push-gate wall config (matches LifehackMethod/ remote pattern); core shipping-lane security infra, unshipped |
| `system/shipping-lane/push_gate.py` | HARNESS-UNSHIPPED-FIX | ClaudeOps companion fix to canon.py: receipt schema v4 pins personal_tier_terms count to prove the tier was armed at CLEAN time; upstream still on v3, |
| `system/shipping-lane/refuse-rules.json` | HARNESS-UNSHIPPED-FIX | carries an extra "path-unc-share" leak-scan rule (Windows UNC path detection) AND a placeholder-name exclusion lookahead on path-home-windows, both ab |
| `system/shipping-lane/rewrite-rules.json` | HARNESS-UNSHIPPED-FIX | brand-rewrite rules (ClaudeOps->Lifehack) used by the publish pipeline itself; generic infra, unshipped |
| `system/shipping-lane/scrub.py` | HARNESS-UNSHIPPED-FIX | carries "DEFECT 1" fix (2026-08-28): refuses a CLEAN verdict when --refuse-rules points at a file with zero personal-tier entries (was silently report |
| `system/shipping-lane/test_line_boundary_bypass_scrub.py` | HARNESS-UNSHIPPED-FIX | adversarial test pairing identity_rules.py's line-boundary-scar fix (see that file); same unshipped fix family |
| `system/sops/agentic-security-sop.md` | HARNESS-UNSHIPPED-FIX | generic security SOP, unshipped |
| `system/sops/build-conductor-sop.md` | HARNESS-UNSHIPPED-FIX | carries 2 clarifying asides pinning the "~3 teammates" ceiling to human-review-bandwidth, not dispatch-parallelism, to prevent a future sweep striking |
| `system/sops/recovery-runbook.md` | HARNESS-UNSHIPPED-FIX | generic cold-restore playbook, desk:root, unshipped |
| `system/templates/skill-template/SKILL.md` | HARNESS-UNSHIPPED-FIX | generic skill-authoring template (CF-14 frontmatter spec), unshipped |
| `system/tools/architecture_reason.py` | HARNESS-UNSHIPPED-FIX | local-only self-poisoning-detection fix (T-session 2026-08-24), absent upstream |
| `system/tools/archivist-run.lib.sh` | HARNESS-UNSHIPPED-FIX | local-only cross-platform (BSD/GNU stat) lock-staleness fix, absent upstream |
| `system/tools/bootstrap.py` | HARNESS-UNSHIPPED-FIX | local-only branch "THIS BRANCH EXISTS BECAUSE ITS ABSENCE WAS THE BUG" (2026-08-23) PYTHONUTF8 fix, absent upstream |
| `system/tools/calendar-store-sync-run.sh` | HARNESS-UNSHIPPED-FIX | local-only cross-platform stat lock-staleness fix, absent upstream (same family as archivist-run.lib.sh) |
| `system/tools/citation_lint.py` | HARNESS-UNSHIPPED-FIX | local-only "SHADOW FIX" (2026-08-24) for same-physical-line key detection, absent upstream |
| `system/tools/conformance-lab/_verify_guards_manual.py` | HARNESS-UNSHIPPED-FIX | SECURITY FIX: removes a comment describing a real operator Google Tasks list id that "shipped public before anyone caught it" as a hardcoded fixture,  |
| `system/tools/conformance-lab/capture.py` | HARNESS-UNSHIPPED-FIX | generic conformance-lab tooling, unshipped |
| `system/tools/email-summary-freshness-run.sh` | HARNESS-UNSHIPPED-FIX | local-only notify dedup fix (T10.A3 OL-N1, --identity stabilized), absent upstream |
| `system/tools/email-summary-write-run.sh` | HARNESS-UNSHIPPED-FIX | ClaudeOps fixes lockdir naming (claudeops- vs upstream's lifehack-) and adds portable/robust stat mtime parsing upstream lacks |
| `system/tools/frontmatter_triage.py` | HARNESS-UNSHIPPED-FIX | generic tooling, unshipped |
| `system/tools/guard-fire-test-run.sh` | HARNESS-UNSHIPPED-FIX | same lockdir-naming + stat portability fix as above, upstream lacks |
| `system/tools/gws-audit.sh` | HARNESS-UNSHIPPED-FIX | generic Google-Workspace credential-plane health tool, unshipped |
| `system/tools/health-deadman-check.sh` | HARNESS-UNSHIPPED-FIX | local-only _deadman_gate() alert-storm fix (46 sends/46h -> edge+24h escalation via fault_ledger), absent upstream |
| `system/tools/ingest-run.lib.sh` | HARNESS-UNSHIPPED-FIX | local-only cross-platform stat lock-staleness fix, absent upstream (same family) |
| `system/tools/item-store-freshness-run.sh` | HARNESS-UNSHIPPED-FIX | local-only cross-platform stat lock-staleness fix, absent upstream (same family) |
| `system/tools/journal.py` | HARNESS-UNSHIPPED-FIX | ClaudeOps adds legacy pre-pipe-format row parsing (LEGACY_RE) so old rows are read, not silently dropped; upstream lacks |
| `system/tools/loop_probe.sh` | HARNESS-UNSHIPPED-FIX | generic tooling, unshipped |
| `system/tools/organism/label_checker.py` | HARNESS-UNSHIPPED-FIX | local-only "HISTORICAL BUG (found 2026-08-23, fixed same day)" hardcoded-constant fix, absent upstream |
| `system/tools/organism/label_manifest.yaml` | HARNESS-UNSHIPPED-FIX | ClaudeOps corrects tasks-guard label_claim from PARTIAL to LIVE with a re-verified investigation trail; upstream lacks |
| `system/tools/planning-analyze-run.sh` | HARNESS-UNSHIPPED-FIX | GNU/BSD stat portability fix (numeric-guard on _lock_mtime) upstream lacks; also personalizes LOCKDIR to /tmp/claudeops-* vs upstream's /tmp/lifehack- |
| `system/tools/planning-health-run.sh` | HARNESS-UNSHIPPED-FIX | generic tooling, unshipped |
| `system/tools/planning-vault-weekly-run.sh` | HARNESS-UNSHIPPED-FIX | local-only cross-platform stat lock-staleness fix, absent upstream (same family) |
| `system/tools/planning-weekly-analyze-run.sh` | HARNESS-UNSHIPPED-FIX | same lockdir-naming + stat portability fix as email-summary-write-run.sh, upstream lacks |
| `system/tools/planning-weekly-prime-run.sh` | HARNESS-UNSHIPPED-FIX | carries the documented GitHub #127 B2 GNU/BSD `date` parsing fix (upstream's bare fallback silently returns TODAY's weekday, ignoring $DATE) AND the s |
| `system/tools/pulse-park.sh` | HARNESS-UNSHIPPED-FIX | generic tooling, unshipped |
| `system/tools/pulse.sh` | HARNESS-UNSHIPPED-FIX | ClaudeOps adds per-job time budget/timeout (closes the 'one hung job stalls the rest of the roster' exposure); upstream lacks |
| `system/tools/registered-guard-fire-test.py` | HARNESS-UNSHIPPED-FIX | generic guard fire-test (commit "K.D3: the Windows root causes"), unshipped; NOTE also has uncommitted local edits in working tree |
| `system/tools/safe_calendar.py` | HARNESS-UNSHIPPED-FIX | ClaudeOps forces UTF-8 stdio (force_utf8_stdio import) upstream lacks |
| `system/tools/safe_tasks.py` | HARNESS-UNSHIPPED-FIX | local-only force_utf8_stdio() Windows console-encoding fix, absent upstream |
| `system/tools/skill_command_check.py` | HARNESS-UNSHIPPED-FIX | generic tooling, unshipped |
| `system/tools/tasks-store-sync-run.sh` | HARNESS-UNSHIPPED-FIX | same GNU/BSD lock stat-portability fix + claudeops- lockdir personalization as the two files above, absent upstream |
| `system/tools/test_bootstrap.py` | HARNESS-UNSHIPPED-FIX | carries Windows-Store-execution-alias-stub and "undetermined"-status test coverage for functionality that still exists in bootstrap.py on BOTH sides,  |
| `system/tools/test_citation_lint.py` | HARNESS-UNSHIPPED-FIX | ClaudeOps adds/keeps a robustness test for a repo with no plugin manifest (os.path.isfile guard); upstream's version differs / lacks this coverage |
| `system/tools/test_journal.py` | HARNESS-UNSHIPPED-FIX | carries 6 additional test cases for legacy (pre-canonical-format) journal row parsing/slug-filtering that do not exist upstream |
| `system/tools/test_section_archive.py.retired-2026-08-24` | HARNESS-UNSHIPPED-FIX | THE TRAP, explicit in-file: retired test for section_archive.py that "carries a real local fix, dated 2026-08-23, for section_archive.py's C |
| `system/tools/test_skill_command_check.py` | HARNESS-UNSHIPPED-FIX | generic tooling test, unshipped |
| `system/tools/tests/test_transcript_index.py` | HARNESS-UNSHIPPED-FIX | YouTube transcript pipeline test, unshipped |
| `system/tools/tests/test_transcript_save.py` | HARNESS-UNSHIPPED-FIX | YouTube transcript pipeline test, unshipped |
| `system/tools/transcript_outline.py` | HARNESS-UNSHIPPED-FIX | YouTube transcript pipeline tool, unshipped |
| `system/tools/venue-probe/checks/d06_posttooluse_hook.sh` | HARNESS-UNSHIPPED-FIX | commit msg: "machine-portable, not Enver-only" — generic infra, unshipped |
| `.claude/settings.json` | PERSONAL | diverged intentionally: hooks: block removed (plugin-served), local-only deny rules added |
| `.claude/skills/clair-ingest/SKILL.md` | PERSONAL | Clair desk skill |
| `.claude/skills/clair-session-close/SKILL.md` | PERSONAL | Clair desk skill |
| `.claude/skills/deryl-ingest/SKILL.md` | PERSONAL | Deryl desk skill |
| `.claude/skills/deryl-rocketmoney/SKILL.md` | PERSONAL | Deryl desk skill |
| `.claude/skills/dobby-scan/SKILL.md` | PERSONAL | Dobby desk skill |
| `.claude/skills/emily-1-ingest/SKILL.md` | PERSONAL | Emily desk skill |
| `.claude/skills/emily-2-interrogate/SKILL.md` | PERSONAL | Emily desk skill |
| `.claude/skills/emily-breakdown/SKILL.md` | PERSONAL | Emily desk skill |
| `.claude/skills/emily-breakdown/alexis-audition.md` | PERSONAL | Emily desk skill |
| `.claude/skills/emily-breakdown/reader-rubric.md` | PERSONAL | Emily desk skill |
| `.claude/skills/emily-ledger-write/SKILL.md` | PERSONAL | Emily desk skill |
| `.claude/skills/reconcile/SKILL.md` | PERSONAL | Deryl desk tax/bookkeeping skill |
| `CONTRIBUTING.md` | PERSONAL | path absent from upstream entirely |
| `docs/design.md` | PERSONAL | path absent from upstream entirely |
| `migration-notes/citation-repair.md` | PERSONAL | migration-log prose about this repo's own history, not in upstream |
| `migration-notes/desk-plane-spec.md` | PERSONAL | migration-log prose about this repo's own history, not in upstream |
| `migration-notes/f1-f2-write-guard-verify.md` | PERSONAL | migration-log prose about this repo's own history, not in upstream |
| `migration-notes/f3-upstream-merge.md` | PERSONAL | migration-log prose about this repo's own history, not in upstream |
| `migration-notes/f3b-upstream-merge.md` | PERSONAL | migration-log prose about this repo's own history, not in upstream |
| `migration-notes/f8-f10-f11-f15-residue.md` | PERSONAL | migration-log prose about this repo's own history, not in upstream |
| `migration-notes/guard-set-reconciliation.md` | PERSONAL | migration-log prose about this repo's own history, not in upstream |
| `migration-notes/p-b2-plane-attribution-procedure.md` | PERSONAL | migration-log prose about this repo's own history, not in upstream |
| `migration-notes/phase-1-lane-a.md` | PERSONAL | migration-log prose about this repo's own history, not in upstream |
| `migration-notes/phase-2-ports.md` | PERSONAL | migration-log prose about this repo's own history, not in upstream |
| `migration-notes/phase-3-ports.md` | PERSONAL | migration-log prose about this repo's own history, not in upstream |
| `skills/marc-transcribe/SKILL.md` | PERSONAL | Enver's own desk skill, active WIP |
| `system/desktop-launchers/Cal.command` | PERSONAL | personal Terminal launcher |
| `system/desktop-launchers/Cal.command.pb3.bak.20260826T140232Z` | PERSONAL | backup of personal launcher |
| `system/desktop-launchers/Clair.command` | PERSONAL | personal Terminal launcher |
| `system/desktop-launchers/Clair.command.pb3.bak.20260826T140232Z` | PERSONAL | backup of personal launcher |
| `system/desktop-launchers/ClaudeOps.command` | PERSONAL | personal Terminal launcher |
| `system/desktop-launchers/ClaudeOps.command.pb3.bak.20260826T140232Z` | PERSONAL | backup of personal launcher |
| `system/desktop-launchers/Deryl.command` | PERSONAL | personal Terminal launcher |
| `system/desktop-launchers/Deryl.command.pb3.bak.20260826T140232Z` | PERSONAL | backup of personal launcher |
| `system/desktop-launchers/Dobby.command` | PERSONAL | personal Terminal launcher |
| `system/desktop-launchers/Dobby.command.pb3.bak.20260826T140232Z` | PERSONAL | backup of personal launcher |
| `system/desktop-launchers/Emily.command` | PERSONAL | personal Terminal launcher |
| `system/desktop-launchers/Emily.command.pb3.bak.20260826T140232Z` | PERSONAL | backup of personal launcher |
| `system/desktop-launchers/Marc.command` | PERSONAL | personal Terminal launcher |
| `system/desktop-launchers/Marc.command.pb3.bak.20260826T140232Z` | PERSONAL | backup of personal launcher |
| `system/desktop-launchers/link-to-desktop.sh` | PERSONAL | Desktop symlink installer |
| `system/egress-allowlist.hosts` | PERSONAL | generated local LuLu firewall allow-list |
| `system/email-service-store-first.md` | PERSONAL | own desk-architecture doc |
| `system/githooks/pre-push` | PERSONAL | own public-shaped-remote push gate |
| `system/hooks/guard_gh_pr_merge.sh` | PERSONAL | own operator-merges-PR guard |
| `system/hooks/guard_mcp_connector_shape.sh` | PERSONAL | own MCP-connector guard |
| `system/hooks/registrations.json` | PERSONAL | legacy repo-level hook-registration manifest |
| `system/hooks/tests/cross_project_write_test.sh` | PERSONAL | test suite for personal-only guards |
| `system/hooks/tests/firetest-sheet-sep.sh` | PERSONAL | test suite for personal-only guards |
| `system/hooks/tests/guard_pm_flag_store_test.py` | PERSONAL | test suite for personal-only guards |
| `system/hooks/tests/pm_hooks_test.sh` | PERSONAL | test suite for personal-only guards |
| `system/hooks/tests/pm_lock_stress.sh` | PERSONAL | test suite for personal-only guards |
| `system/hooks/tests/test_git_add_class.sh` | PERSONAL | test suite for personal-only guards |
| `system/hooks/tests/test_guard_brief_truncation.sh` | PERSONAL | test suite for personal-only guards |
| `system/hooks/tests/test_guard_hook_sop_hash_parity.sh` | PERSONAL | test suite for personal-only guards |
| `system/hooks/tests/test_guard_hook_sop_read.sh` | PERSONAL | test suite for personal-only guards |
| `system/hooks/tests/test_guard_mcp_connector_shape.sh` | PERSONAL | test suite for personal-only guards |
| `system/hooks/tests/test_scratch_lock_indirection.sh` | PERSONAL | test suite for personal-only guards |
| `system/hooks/tests/verify-bootstrap-standdown.sh` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/hooks/tests/verify-harness-writeback-guard.sh` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/hooks/tests/verify_checkin_matcher_resolves.sh` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/hooks/youtube_url_route.sh` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/marc-lenses.md` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/organism/.plan-retirement-state.json` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/organism/plan-retirement-enver-queue.md` | PERSONAL | explicitly "Phase Z — Enver's queue"; his own ranked decision list for this migration project |
| `system/organism/plan-retirement-verdicts.md` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/parked/2026-08-23-ruled-out-resurrections/.claude-plugin/plugin.json` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/parked/2026-08-23-ruled-out-resurrections/.claude/skills/overmyshoulder/SKILL.md` | PERSONAL | Enver's own 2026-08-14 ruling record: skill deliberately removed (needs undistributable browser relay); house-rule archival "retire never re |
| `system/parked/2026-08-23-ruled-out-resurrections/.claude/skills/skill-builder/scripts/order_lint.py` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/parked/2026-08-23-ruled-out-resurrections/.claude/skills/skill-builder/scripts/phase_gate.py` | PERSONAL | personalized/renamed variant (cal-weekly, "Enver-authored") of upstream-equivalent system/parts/phase_gate.py, sitting in Enver's ruled-out- |
| `system/parked/2026-08-23-ruled-out-resurrections/README.md` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/parked/2026-08-23-ruled-out-resurrections/system/tools/oms_format.py` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/parked/2026-08-23-ruled-out-resurrections/system/tools/over_my_shoulder.sh` | PERSONAL | same ruled-out record as the SKILL.md above, companion CLI script |
| `system/schemas/runner-standard.md` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/shipping-lane/path_gate.py` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/skills-manifest.md` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/sops/dev-browser-debug-sop.md` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/sops/port-lane-sop.md` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/templates/producer-spec-template.md` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/_parked/README.md` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/_parked/test_transcript_query.py` | PERSONAL | retired/superseded unit test for the now-parked transcript_query.py tool (superseded by transcript_outline.py pipeline); kept as archival re |
| `system/tools/_parked/transcript_query.py` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/architecture-reachability-run.sh` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/bootstrap-machine.sh` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/brokenlist-run.sh` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/brokenlist.py` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/cowork-ingest/test_chain_e2e.sh` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/cowork-ingest/test_pipeline.py` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/cowork-ingest/test_scratch_hook.sh` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/d4_hook_dedup.py` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/gws-reauth.sh` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/ingest_method_audit.py` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/install-guard-registrations.py` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/install-machine-settings.py` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/issue-staleness-sweep-run.sh` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/issue_staleness_sweep.py` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/lint_settings_permissions.sh` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/loop_watch.sh` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/obsidian-prune-archive.mjs` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/obsidian-reindex.sh` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/plan_retirement_verdicts.py` | PERSONAL | "Phase Z.A1/A2 instrument" built specifically to manage THIS separation project's own migration plan file, not a public-harness feature |
| `system/tools/plugin-presence-probe.sh` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/pulse-park-health-run.sh` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/pulse-park-health.py` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/resolution-census.sh` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/security-posture-scan.sh` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/silence-check-run.sh` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/test_architecture_reachability_run.py` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/test_issue_staleness_sweep.py` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/test_security_posture_scan.py` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/test_silence_check_run.py` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/tests/test_bsd_gnu_flag_fallbacks.sh` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/tests/test_plan_retirement_verdicts.py` | PERSONAL | test for the Phase-Z migration-plan instrument above; same personal-project family |
| `system/tools/tests/test_pulse_crlf_manifest.sh` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/tests/test_transcript_outline.py` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/tests/test_transcript_pipeline.sh` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/tests/test_youtube_transcribe.py` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/transcript_index.py` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/transcript_pipeline.sh` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/venue-probe/checks/d02_pretooluse_hook.sh` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/venue-probe/checks/d13_network_egress.sh` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/verify-guard-plane-live.sh` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/verify-identity-secret-drift.sh` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/verify-pm-guard.sh` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `system/tools/youtube_transcribe.py` | PERSONAL | ClaudeOps-specific desk/runner infrastructure, absent upstream and plugin cache |
| `system/tools/youtube_transcript_save.py` | PERSONAL | ClaudeOps-specific, absent upstream and plugin cache |
| `SECURITY.md` | HARNESS-IDENTICAL | Newly classified 2026-08-31: added after the manifest's own commit; matches upstream. |
| `system/organism/plan-retirement-accepted-deltas.md` | PERSONAL | Newly classified 2026-08-31: operator's own working notes, not harness machinery. |
| `system/organism/separation-manifest.md` | PERSONAL | Newly classified 2026-08-31: this file never classified itself; it is the operator's own working document, not shipped harness content. |
| `system/tools/test_identity_tier_covers_bare_terms.py` | HARNESS-UNSHIPPED-FIX | Newly classified 2026-08-31: test for harness identity-scrub machinery, not yet in the shipped tree. |
| `system/githooks/tests/test_pre_push.sh` | HARNESS-UNSHIPPED-FIX | Newly classified 2026-08-31: test for harness pre-push hook machinery, not yet shipped. |
| `system/githooks/tests/test_pre_push_registry_missing.sh` | HARNESS-UNSHIPPED-FIX | Newly classified 2026-08-31: same as above, companion test. |
| `system/shipping-lane/exemptions.json` | HARNESS-UNSHIPPED-FIX | Newly classified 2026-08-31: shipping-lane machinery data file, not yet shipped. |
| `system/shipping-lane/exemptions.py` | HARNESS-IDENTICAL | Newly classified 2026-08-31: matches upstream. |

## Y.C1 -> PR batch plan for the 116 HARNESS-UNSHIPPED-FIX files (10 batches, 10-25 files each)

Excludes 1 file — see FLAG below, never batch it.

| # | Batch | Files | Security-sensitive | Rationale |
|---|---|---|---|---|
| 1 | Publish-gate / shipping-lane security core | 11 | YES | canon.py/push_gate.py/scrub.py/identity_rules.py/refuse-rules.json/rewrite-rules.json/public-remotes.json + pre-commit + .gitignore + guard-verify script — the push-time leak wall itself |
| 2 | GitHub leak-scan + PR-citation-gate infra | 11 | YES | check_no_internal_leakage.py + its test + the whole in-progress PR-body-citation-gate feature (workflow, script, fixtures, template) |
| 3 | Guards + hooks fixes | 7 | YES | hook-contract.md + 3 guard scripts with dated 2026-08-28 fixes (fail-open, quote-blanking, zone-escape) + 3 hook tests |
| 4 | Agent + skill-spec additions | 9 | NO | .claude/agents/{archivist,sentinel,worker}.md additions + the unshipped architect/audit desk:root skills (4+2 files) |
| 5A | Organism element corrections, half 1 | 13 | NO | 2026-08-27 live-behavior/factual correction annotations to element docs |
| 5B | Organism element corrections, half 2 + manual.md + pulse-config.md | 14 | NO | same correction pattern; manual.md and pulse-config.md carry the most annotations (14 and 39 respectively) |
| 6 | Cross-platform portability fixes | 14 | NO | GNU/BSD stat lock-staleness + UTF-8 stdio fixes across *-run.sh scripts and safe_calendar/safe_tasks/bootstrap.py |
| 7 | Tooling correctness fixes + parts library | 17 | NO | assorted local-only bug fixes (citation_lint SHADOW FIX, journal.py legacy-row parsing, label_checker constant fix, pulse.sh per-job timeout, etc.) + their tests |
| 8 | Generic unshipped infra/docs, portable as-is | 15 | LOW (2 files touch security topics: agentic-security-sop.md, security-posture-baseline.md — docs only, worth a second look, not blocking) | never-Enver-only tooling/docs never yet ported (requirements.txt, SOPs, skill-template, conformance-lab, gws-audit.sh, etc.) |
| 9 | YouTube transcript pipeline (unshipped feature) | 3 | NO | test_transcript_index.py, test_transcript_save.py, transcript_outline.py |
| 10 | venue-probe posttooluse hook test | 1 | NO | single machine-portability test, no natural home in the above |

⛔ FLAG — do not include in any batch, must never ship:
`system/parked/2026-08-23-ruled-out-resurrections/.claude/skills/skill-builder/scripts/forbidden_content.py`
carries a real name at 4 lines (10, 165, 166, 201) — one more line than the previously known count of 3.
