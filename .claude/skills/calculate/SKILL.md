---
skill: calculate
description: "Arm numbers-mode so every calculation this session runs through code, not the model's head. Use on \"/calculate\", or before any math/money work; \"/calculate off\" disarms."
shape: command
summary: |
  Arms "numbers-mode" for this session: a UserPromptSubmit hook then re-states the
  compute-with-code rule every turn until you clear it or 12 hours pass. Use it when you
  sit down to do money or maths. Compute mechanically — a spreadsheet formula, a Python
  snippet, some code — never in the model's head; and never bend a number to fit.
  Triggered by: /calculate, "numbers mode on", "we're doing math", "calculate carefully".
  Turn off: /calculate off, "stop numbers mode".
---

## Intent (§0.5)
**User outcome:** For any session with maths or money in it, one word makes every calculation run through code — a spreadsheet formula or a Python line — never the model's head, so no number can be quietly wrong. **Bar:** "I said /calculate and I know every number this session was actually computed — I never wonder if it was eyeballed."
**Role:** a session-mode switch — a one-shot arm that flags the session so `system/hooks/inject_compute_mechanically.sh` re-states the rule every turn (12h TTL); "/calculate off" disarms. No multi-turn flow — arm, confirm, and the hook holds the rule from there.

# /calculate — arm numbers-mode

When invoked **without "off"**: arm numbers-mode for this session, then confirm.

```bash
bash "$(git rev-parse --show-toplevel)/system/hooks/numbers_flag.sh" arm
```

Then tell them, in one line: *numbers-mode armed — every turn this session will re-state the
compute-with-code rule until you say "/calculate off" or 12 hours pass.*

State the rule once now, so it is in context immediately:
> Any calculation this session is computed by code — a spreadsheet formula, a Python snippet via
> Bash, something that actually runs — never in my head or in prose. I show the expression next to
> the result. I never bend, round, or work backwards from an input to land on a number I was
> hoping for; I run it forwards and say so if the answer disagrees.

When invoked **with "off"** (or "stop numbers mode"): disarm and confirm.

```bash
bash "$(git rev-parse --show-toplevel)/system/hooks/numbers_flag.sh" clear
```

## Making a subject arm itself

If one of your subject folders is always about money, you can have it arm without being asked.
Put its folder name — one per line — in `<notes>/config/numbers-auto-arm`:

```
freelance-invoicing
household-budget
```

Any window opened inside `<notes>/desks/freelance-invoicing/` then arms itself. No file means no
folder arms itself, which is the default; `/calculate` still works everywhere, and the hook's own
backstop still catches an obvious currency figure or percentage in any session.

## What this skill needs outside its own folder

| what | where | status |
|---|---|---|
| the arm/disarm switch | `system/hooks/numbers_flag.sh` | ✅ here |
| the hook that re-states the rule each turn | `system/hooks/inject_compute_mechanically.sh` | ✅ here |
| your auto-arm list | `<notes>/config/numbers-auto-arm` | ⛔ never ships — it is yours, and it is optional |
