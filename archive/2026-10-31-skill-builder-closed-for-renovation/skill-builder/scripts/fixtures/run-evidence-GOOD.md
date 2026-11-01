# RUN EVIDENCE — fixture: a chain pass that left every required trace

> ⚠ **FIXTURE, not a real run.** Its only job is to prove `phase_gate.py` PASSES a complete
> artifact, so that the BAD fixture's refusal means something. No real run has happened yet —
> that is F4.1.
>
> ⛔ **EVERY VALUE BELOW IS SYNTHETIC AND MUST STAY SYNTHETIC.** The first draft of this file
> used REAL session ids copied out of `~/.claude/run/pm/arm-events.log` and a real commit hash,
> and the pre-commit guard blocked it — correctly. That is the documented leak class (2026-08-05:
> *"this is exactly how 241 real ids landed in conformance-lab/fixtures"*). Session ids here are
> deliberately all-zeros/`ffff` shapes that no real run can produce. **If you update this fixture,
> do not paste live values into it.**

## BUILDER PHASE 1 — define the desired outcome
OUTCOME-RECORD: ARMED-BRIEF
ARM-EVENT: 1000000000/arm/fixture-skill/00000000-0000-4000-8000-000000000001

## BUILDER PHASE 2 — propose the phases
PROVENANCE: HUMAN-AUTHORED
FORK: 2.6 = B

## BUILDER PHASE 3 — decide the steps
SET-DIFF: missing=0 dupes=0 alien=0
DECLARED: 4 (from BUILDER PHASE 2)
STEP-FIELDS: violations=0

## BUILDER PHASE 4 — the tension swarm
READERS-RETURNED: 4 / 4
RULINGS: adopted=6 rejected=3 decided-differently=1
CARRY-RECEIPT: OK

## BUILDER PHASE 5 — build it
COMMIT: deadbeefdeadbeef
SOP-CITED: yes
TESTER: NO-TESTER-RAN

## BUILDER PHASE 6 — the live run
SESSION-B: ffffffff-ffff-4fff-8fff-ffffffffffff
OBSERVATIONS: carried=11 out-of-scope=2
FORK: 6.13 = B
