# planning-weekly — pre-shakeout stress test + fix record (2026-07-20 → 07-21)

Dry stress test of the rough-built 7-phase skill BEFORE its first live run, then the fix pass (Phase B.5).
Method: a mechanical harness + 3 blind read-only auditors (2026-07-20), then a 4-advisor `/advisory-council`
critique + argue round (2026-07-21), then fixes applied + re-verified. All findings were verified against the
real files.

## Verdict (pre-fix): would NOT survive a first live run — all breaks shallow rough-build wiring, not design flaws.

## CRITICAL / HIGH findings → resolution
| # | Finding | Fix (Phase B.5) | Status |
|---|---------|-----------------|--------|
| 1 | **Calendar rail FAIL-OPEN on the MCP path** — `guard_calendar_writes.sh` only matches `gws` Bash; clerk write-method unpinned + MCP calendar tools bypass the guard (council #1; a watching human can't see the target calendar). | F0: pin clerk calendar writes to `gws` + Agent Ops id; corrected "hook-enforced" wording; **guard-deny test watched: gws-primary DENIED, gws-AgentOps PASSED, MCP passes-through (why the pin).** | ✅ |
| 2 | Literal `<PAD>`/`<Mon>`/`<Sun>` placeholders never resolved → break at launch/Phase 0. | F1.2: SKILL FIRST-ACTION computes WEEK/PAD/dates; arms with resolved values. | ✅ |
| 3 | Relative tool paths fail from a desk cwd. | F1.1: all driver tool-calls → absolute `$ROOT/...`. | ✅ |
| 4 | `planning-lifemap-write.py --append` doesn't exist (real: `--file/--section/--body-file`, section-REPLACE → destructive). | F2/T2.1: correct flags + FULL body + `--check` dry-run guard. | ✅ |
| 5 | ANCHOR.md 2376 chars > injector's 1200 ceiling → Rails line silently cut every turn. | F3: trimmed to 1112 chars (dropped the 7-phase arc enumeration); Rails now survive the ceiling. | ✅ |
| 6 | HUD frozen at `[1/6]` — no driver repaints. | F4/T4.1: every driver paints its own `[N/6]` HUD on entry. | ✅ |
| 7 | `06-triage.md` offered but unbuilt → dead-link read. | F6/T6.1: graceful offer (schedule a separate session; never read the missing file). | ✅ |
| 8 | No real crash-recovery — clerk marks ✅/❌ only in its return; crash loses state; bulk writes double-fire. | F4/T4.4: clerk stamps each row's state INTO the scratchpad on disk (cheap floor). Full dedup/idempotency → tech-debt (v2). | ✅ (floor) |
| 9 | WRITE-LEDGER only calendar-populated; clerk drains an incomplete ledger. | F2/T2.3: ONE clerk-input contract line "ledger covers ALL surfaces" + a trace (not 3-file ETL). | ✅ |
| 10 | Confirmation gate ambiguous + fakeable; sub-agent fences absent. | F5: ONE instruction-grade gate at end of Report (honestly labeled); READ-ONLY/DATA fences on council + leverage + clerk (structural versions → tech-debt). | ✅ |
| 11 | map-agent briefs told a blind sub-agent to "go read" a file. | F1.3: briefs now say content is EMBEDDED at dispatch. | ✅ |
| 12 | Phase-2 "game continues until gaps filled" — no exit / infinite-loop risk. | F6/T6.2: bounded exit backstop (round cap + "move on" carries gaps forward). | ✅ |
| — | Weekly-review-file path undefined; Olsen persona not loaded; capture-gate 30m TTL dormant mid-run. | F2/T2.2 literal path · F6/T6.3 olsen.md load + SCRATCH_TTL_MIN=180. | ✅ |

## Deferred (named, with homes) — see the plan
- To live shakeout: Phase-4 loop-back exit · "no final verdict" wording · Phase-1→2 size/confidence hand-off + flywheel skip.
- To `state/tech-debt.md`: full write idempotency/dedup keys · structural PreToolUse gate + tool-revoking fences · MCP-matcher calendar hook · email auto-send hook · expiry-clock alignment · council opus-vs-sonnet (a decision, kept on opus). ⛔ that `state/tech-debt.md` is the AUTHOR's own engineering burndown in the donor system (`claudeops-config`) — these are build/implementation follow-ups on the skill's own code, not the student-facing `<notes>/state/tech-debt.md` durable-records destination this skill writes to (see `.claude/skills/planning-daily/prompts/05-act.md` / `.claude/skills/planning-daily/prompts/04.5-consolidate.md`). Never shipped here; this is a build record, not a promise.

## Re-verify (post-fix, 2026-07-21)
Mechanical harness: `--append` gone · no literal placeholders · ANCHOR 1112 chars · blind chain intact.
Independent sonnet re-audit: all 12 findings CLOSED, no new mechanical breaks. Guard-deny test watched blocking.
**Ready for Phase C shakeout.**
