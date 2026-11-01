# skill-tester-rig — the crucible for multi-step skills

A test rig that puts a synthetic multi-step skill through every failure mode it could meet in real use
(a stateless session rehydrated from files, a wandering human, a window that fills up, a hand-off to a
cold session, planted faults) and reports, from code alone, whether the machinery held. Trustability
trumps everything; efficiency comes second. Plan: `<notes-root>/plans/skill-tester-rig.plan.md` (card TR0.1
built this folder).

## Rulings that bind this rig (Enver, 2026-10-31) — copied verbatim from the plan

These fourteen rulings are the contract. Every later card is checked against them; they change only by
asking claudeops-a0 (the skill-system window), who asks Enver.

1. **Trust first.** If a shortcut would make a result less trustworthy, take the slow road. If a faster road is clearly as trustworthy, take it.
2. **Code grades. Never an AI judge.** The model plays the human; it never grades a run. (The Conformance Lab's judges were non-blind and ~20% non-deterministic; every number was quarantined.)
3. **Never one run.** n ≥ 3 per condition; n = 5 when a result sits near the pass line.
4. **The test skill is synthetic and boring.** Nothing to judge, only things to check. No real skill is ever the subject.
5. **The rig never touches real state.** Seam-leak snapshot before and after every run (stolen from the cron rig).
6. **Output never goes to Google Drive.** `~/lifehack-scratch/skill-tester-rig/` only (the October rig choked Drive with 17,832 files).
7. **The actor is a real headless Claude Code session**, one fresh process per step (that fresh process IS the cold hand-off). Sub-agents are not the actor. **Never launch the rig from inside an Agent-tool sub-agent** — the Lab found double-nesting times out; the runner passed 30/30 from a window's Bash tool. A separate Claude Code *window* running it from Bash is fine; that is the "subordinate window."
8. **Never `--dangerously-skip-permissions`.** Hangs are prevented by read-only tools, no stdin, a watchdog, and (for multi-turn) `bypassPermissions` plus a deny list that includes `AskUserQuestion` — the guard-rig pattern.
9. **On demand, never scheduled** (canon §15.29). A human starts it and reads the result.
10. **Efficiency, in this order:** fake Claude wherever the model is not the thing under test (zero tokens, seconds) · cheapest model as the fake human · mid-tier model as the actor, top-tier only for a final 3-run confirmation · fill the window by pasting cached documents, not by generated chatter · run independent runs in parallel · fail fast up the ladder · resume from the rig's own record after a crash.
11. **Answer key before the run.** Every planted fault is listed before the run starts; the grader must name each one exactly (string equality). "Something's wrong" is a fail.
12. **Watch every check fail first.** No check is trusted until it has been seen refusing bad input.
13. **False positives are measured.** Every rung runs clean controls (zero faults planted). Any flag on a clean run is a false positive, counted and reported. A gate that cries wolf 15–40% of the time gets bypassed in real use; the rig must say what rate ours cries at.
14. **Cost and time are recorded on every run** from the session's own `total_cost_usd` and `num_turns` (the October rig forgot this).

## Where things live (provenance)

- **This folder** (`~/lifehack-v2/system/tools/skill-tester-rig/`): rig code only. Local run artefacts
  (`runs/`, `*.tmp`, `__pycache__/`) are ignored by this folder's own `.gitignore`. Run dirs live in scratch at
  `<scratch>/actor-home/<run-id>/.claude/run/skill-tester/<run-id>/` (layout.py, TR2.0b).
- **Scratch output** (`~/lifehack-scratch/skill-tester-rig/`): every run's output, outside any repo and
  never on Google Drive (ruling 6). Override with env `SKILL_TESTER_SCRATCH` (tests only).
- **Status file** (`~/lifehack-scratch/skill-tester-rig/STATUS.md`): written by `status.sh` —
  rung, run-id, step, elapsed, cost-so-far, last-event, updated-at. Elapsed is measured from a per-run
  start stamp (`.start-<run-id>`) created on the first call for that run.
- **Usage:** `status.sh <rung> <run-id> <step> <cost-so-far> <last-event>` · `status.sh selftest`.
- **Run by hand (on-demand entry points).** Ruling 9: the rig is on-demand, so nothing schedules it. A
  person starts each of these from a terminal (always from a window's Bash, never from a sub-agent):
  - `bash system/tools/skill-tester-rig/selftest-all.sh`: every rig selftest, sequentially (last line `SELFTEST-ALL OK <n>/<n>`)
  - `bash system/tools/skill-tester-rig/selftest-all.sh --waits`: TR1.8, the wait scan + fail-first copies + the
    selftests that wait (last line `WAITS handshake-only silent-giveup 0 scan fail-first OK`)
  - `bash system/tools/skill-tester-rig/waits_scan.sh [--selftest]`: refuses a bare `sleep` or a poll loop with no
    `WAIT-TIMEOUT` path; every wait is `wait_until` from `wait.lib.sh` (sourced, never run) or tagged `# pacing: <why>`
  - `bash system/tools/skill-tester-rig/run.sh --selftest`: the runner, fake model only
  - `bash system/tools/skill-tester-rig/bite.sh --selftest`: the fault-injection bite
  - `bash system/tools/skill-tester-rig/receipt.sh --selftest`: the long-gate receipt (`receipt.sh check <gate> "<line>"`
    is a gate card's fast Verify; only `bite.sh --rung N` writes receipts, to `~/lifehack-scratch/skill-tester-rig-receipts/`)
  - `bash system/tools/skill-tester-rig/guard.sh selftest`: the write guard refuses a guarded write into the receipts folder
  - `bash system/tools/skill-tester-rig/probe-hooks.sh --selftest`: TR0.4 hook probe, fake claude (drop `--selftest` for the real probe)
  - `bash system/tools/skill-tester-rig/probe-actor-writes.sh --selftest`: TR2.0b write-list census, fake actor (drop
    `--selftest` for the real census: ONE real cheapest-tier actor, cap $0.25, main window only)
  - `bash system/tools/skill-tester-rig/actor-guard.sh --selftest`: TR2.0b orchestrator, fake actor (drop `--selftest`
    for the real gate: census, then one real canary run under the guard with `--plugin-dir`, then the `actor-guard`
    receipt)
  - `bash system/tools/skill-tester-rig/checks/selftest.sh`: judges the shipped checks against their fixtures
  - `python3 system/tools/skill-tester-rig/checks/fixtures/make_fixtures.py`: regenerates the check fixtures
    when the canary contract changes (then re-run `checks/selftest.sh`)
- **Stolen parts** copied from the October step-runner rig carry a header
  `# from orchestrator-v2/rig/<file> @ 2026-10-28`; the Drive originals stay where they are.
