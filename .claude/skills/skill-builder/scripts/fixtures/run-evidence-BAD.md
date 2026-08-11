# RUN EVIDENCE — fixture: every phase failing in its OWN characteristic way

> ⚠ **FIXTURE.** Each phase below breaks differently on purpose, so a refusal proves the
> gate read THAT phase rather than blanket-failing the file. §V.4c — probe a gate by
> DESTRUCTION: take something that legitimately passes and mutate it.
>
> Phase 1 — the decision was never recorded (forbids fires).
> Phase 2 — provenance blank: a machine draft the human never saw (forbids fires).
> Phase 3 — a phase silently lost its step list: missing=2 (forbids fires).
> Phase 4 — the swarm was skipped and reported clean: 0/4 (forbids fires).
> Phase 5 — no commit at all, and the tester verdict is a hedge (requires + forbids).
> Phase 6 — session B is session A: the two-window split defeated (forbids fires).

## BUILDER PHASE 1 — define the desired outcome
OUTCOME-RECORD: NOT-RECORDED
ARM-EVENT: 1000000000/arm/fixture-skill/0000

## BUILDER PHASE 2 — propose the phases
PROVENANCE: NOT-RECORDED
FORK: 2.6 = B

## BUILDER PHASE 3 — decide the steps
SET-DIFF: missing=2 dupes=0 alien=0
DECLARED: 4 (from BUILDER PHASE 2)
STEP-FIELDS: violations=0

## BUILDER PHASE 4 — the tension swarm
READERS-RETURNED: 0 / 4
RULINGS: adopted=0 rejected=0 decided-differently=0
CARRY-RECEIPT: OK

## BUILDER PHASE 5 — build it
SOP-CITED: yes
TESTER: assumed passing

## BUILDER PHASE 6 — the live run
SESSION-B: SESSION-A
OBSERVATIONS: carried=11 out-of-scope=2
FORK: 6.13 = B
