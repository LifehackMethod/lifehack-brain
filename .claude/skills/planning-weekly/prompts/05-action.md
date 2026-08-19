# Phase 5 — Action  ·  HUD `[5/6] ACTION`

**Paint the HUD on entry:** `bash "$ROOT/system/tools/skill_hud.sh" set '🧭 Cal · Weekly   [5/6] ACTION · calendarize → report → act · next → done'`

**Desired outcome:** turn the ranked, pressure-tested plan into a written, calendarized week — a calendar you'd
stand up and clap for. Three steps, each its own sub-driver (one-step-one-injection): **Calendarize → Report →
Act.** HITL is high for steps 1–2 (he corrects, he confirms), zero for step 3 (machine-only clerk).

**Rolling scratchpad view first:** show Phase 3's ranked Win(s) + Phase 4's folded tensions + the calendar
plan-of-intent.

## ★ Scope guard (the critical rail this phase)
Phase 5 is a major reorientation — planning the intentional week at ALTITUDE. It must NOT drift into actual
inbox-zero or per-item task triage. If you or the person start dropping into item-by-item processing, **note the item
and defer it to Phase 6** rather than derailing. The only live writes allowed are the bounded bulk actions below.

## The confirmation gate (ONE, at the end of Report)
Even if the person says "just skip to the end and write everything," you STOP and confirm before any write. There are
NO unauthorized writes. There is exactly ONE gate: at the end of `05-report.md` you present the full WRITE-LEDGER
and wait for the person's explicit "go"; only then does `05-act-clerk.md` run. *(Instruction-grade stop, not a structural
lock — the un-bypassable version is logged to tech-debt.)* That "go" is the last human act.

## The bounded write-reach (clerk only, step 3)
- **Calendar:** the Agent Ops calendar ONLY, **via `gws` Bash** (never `primary`, never an MCP calendar tool) — the `gws`+Agent-Ops-id path is what makes the `guard_calendar_writes.sh` guard fire.
- **Records:** the Life Map (the Win) via `planning-lifemap-write.py --section weekly --body-file` (section-REPLACE → FULL body + `--check` dry-run FIRST) + the weekly review file (`$DATA/desks/cal/records/weekly-reviews/<YYYY-Www>.md`, a plain append).
- **Tasks:** GOOGLE TASKS, bulk actions only (reschedule lo/lo · mark implied-complete · add shadow tasks) — never one-by-one.
- **Email:** DRAFTS only, and only to support the bulk actions ("I'm pushing this to you") — never auto-sent, never inbox-zero.
Every surface = one read-back-gated row in the WRITE-LEDGER (which MUST cover ALL these surfaces, not calendar-only), each gated on his prior confirmation. Full mechanics + on-disk row-checkpoint: `05-act-clerk.md`.

## Steps (load each at its own entry — do not read ahead)
1. `05-calendarize.md` — body-first best-guess fill → correction rounds → the WRITE-LEDGER.
2. `05-report.md` — the Radical Clarity Report → skeptic pass → confirm → Olsen's closing voice.
3. `05-act-clerk.md` — the machine-only clerk drains the ledger, read-back-gated, deletes the scratchpad last.

## do NOT
- do NOT write anything live outside the step-3 clerk, and never without the confirmation gate.
- do NOT drift into inbox-zero / per-item triage (scope guard) — defer to Phase 6.
- do NOT exceed the bounded write-reach above.

**NEXT:** read `05-calendarize.md`.
