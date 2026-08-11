# Project Doc Quality Standard

A project doc is successful if it preserves the **operating state** of a long-running project with enough fidelity for future continuation.

## Minimum quality bar

A project doc must be:

1. **Portable**
   - It must make sense without the original chat.
   - It must define the user's goal, current state, key context, and next actions.

2. **Comprehensive**
   - It must include all material facts, decisions, tests, results, hypotheses, constraints, and open questions.
   - Comprehensive does not mean verbose. It means nothing important is missing.

3. **High-density**
   - Prefer dense bullets, tables, compact labels, and structured notes.
   - Remove narrative filler.
   - Preserve nuance that affects future reasoning.

4. **Operational**
   - A future AI should know what to do next.
   - The document should drive action, not just describe history.

5. **Current-state-forward**
   - The latest working model and active work should be easy to find.
   - Old history should not bury the current state.

6. **Confidence-labeled**
   - Facts, assumptions, hypotheses, user theories, conflicts, and unknowns must be distinguishable.

7. **Maintained**
   - Do not append forever.
   - Periodically consolidate, compress, reorganize, and update navigation.

8. **Organic**
   - Structure should match the work.
   - Do not force a troubleshooting template onto a writing project or a book template onto a systems problem.

## Rehydration test

A future AI should be able to answer:

- What is the user trying to accomplish?
- What is the current state?
- What happened before?
- What has been tried?
- What did we learn?
- What is known, inferred, and unknown?
- What is the current best model?
- What should happen next?
- What should not be assumed?

If the answer is incomplete, the project doc is not yet good enough.

## Compression standard

The project doc should be as short as possible **without losing operational fidelity**.

Bad compression:
- deletes why a decision was made
- removes failed tests
- blurs facts and theories
- loses constraints
- leaves a future AI unable to continue

Good compression:
- merges duplicates
- removes prose padding
- replaces paragraphs with structured bullets
- keeps exact values and decisions
- records why state changed
- keeps live next actions visible

## Confidence label standard

Use these labels when useful:

- `CONFIRMED`: directly observed, decided, sourced, or stated by the user.
- `INFERRED`: likely from evidence, not directly proven.
- `HYPOTHESIS`: plausible theory or possible explanation.
- `USER HYPOTHESIS`: user-originated theory preserved without over-validation.
- `UNKNOWN`: important unresolved point.
- `CONFLICT`: apparent contradiction.
- `DEPRECATED`: superseded or falsified belief.
- `ACTIVE`: currently being worked/tested.
- `TODO`: future action.

## Red flags

The project doc needs maintenance if:
- it reads like a transcript
- multiple sections repeat the same point
- current state is hard to find
- old theories are not marked deprecated
- future plan is missing or stale
- tests are recorded without results
- results are recorded without interpretation
- user preferences or constraints are missing
- a new AI would need the original chat to understand it
