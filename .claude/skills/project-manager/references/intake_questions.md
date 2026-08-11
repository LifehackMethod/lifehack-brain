# Intake Questions — the human-only frame

This is the **elicitation** set. It is different from `operating_questions.md`
(which is the doc-*design* set, answered by inference). These are the things that
usually live ONLY in the user's head and were often never stated in the session —
so they cannot be reliably inferred, only guessed. They must be **confirmed with
the user** before the project doc is treated as authoritative.

## The two-bucket principle

Before asking anything, sort what the doc needs into:

- **EXTRACTABLE** — recoverable from the session + any files the user points to:
  what happened, what was tried, results, in-thread decisions, current state,
  established facts, artifacts. **Do NOT ask these.** Gather them silently.
- **HUMAN-ONLY** — the frame below. Gather a best *guess* from context, but these
  are not facts until the user confirms them.

## The reflect-back rule (non-negotiable)

**Never ask a frame question cold.** Every question is presented WITH your inferred
best guess, confidence-labeled, so the user is confirming or correcting — never
starting from scratch. Format per slot:

> **[slot]** — My read: *"[inferred guess]"* `[INFERRED|THIN|MISSING]`.
> Confirm, correct, or fill in.

If you have nothing to guess (`MISSING`), say so plainly and ask — but still frame
it with options or a hypothesis where you can.

## Critical slots — the minimum frame (HARD GATE)

The work does not proceed as a tracked project until EACH of these is **CONFIRMED**
(user stated or confirmed your inference) or **WAIVED** (user explicitly declines
to specify it). No silent proceeding on INFERRED/THIN/MISSING.

1. **Desired outcome / definition of done** — what does "finished" actually look
   like to the user? The single most important slot.
2. **Success criteria** — how will the user judge whether it worked?
3. **Constraints & non-negotiables** — what must NOT happen; hard limits.
4. **Scope edges** — what is explicitly OUT of scope.

## Secondary slots — confirm if cheap, may proceed as INFERRED

Reflect these back too, but they do not block the gate. Record their state.

5. **Stakes / why it matters** — the real reason behind the work.
6. **Risk tolerance / quality bar** — rough-and-fast vs. bulletproof.
7. **Time horizon / deadlines.**
8. **Stakeholders** — who else is involved or affected.
9. **Decision gates** — what would change the plan; what choices are pending.
10. **Known landmines** — failures or dead-ends the user already knows to avoid.

## The loop

1. Present the full scorecard (all slots + states + your inferences) in one round.
2. Take the user's answers; re-score.
3. If any critical slot is still below CONFIRMED/WAIVED, ask again — reflecting your
   *updated* best guess from what they just told you. Keep going.
4. Stop only when every critical slot is CONFIRMED or WAIVED.

## The waiver

The user may decline any slot ("skip it," "don't need that," "just go"). Mark it
**WAIVED**, record it in the doc as a known, deliberate gap, and proceed. A waiver
is a user decision — honor it without nagging. (A blanket "just go" waives all
remaining critical slots at once.)

## Recording the frame in the doc

The project doc carries a small **Frame confidence** block listing each slot and
its state (CONFIRMED / INFERRED / WAIVED, with the value). Once a slot is CONFIRMED
or WAIVED it persists — re-invoking the skill in a later session reads this block
and does NOT re-interrogate the user on settled slots.
