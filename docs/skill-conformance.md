# Skill conformance — what a SKILL.md must declare

> **What this is for.** A skill is only useful if the harness can find it and a person can tell what it
> does without opening it. This page is the small set of rules that makes both true. It is a checklist,
> not a framework: if you are writing a skill, everything you need is on this page.

## The one required field: `shape:`

Every `SKILL.md` declares what KIND of thing it is. There are three, and all 31 skills shipped here
already use them:

| `shape:` | what it means | how it starts |
|---|---|---|
| `command` | you type it and it does a bounded thing | you invoke it, e.g. `/websearch` |
| `interactive-workflow` | it works THROUGH something with you, in phases | you invoke it, then it asks you things |
| `utility` | another skill or tool calls it; you usually do not | called, not typed |

A skill that genuinely has two modes may declare a list: `shape: [command, interactive-workflow]`.
Prefer one. If you cannot pick, the skill is probably two skills.

## The frontmatter

```yaml
---
name: the-skill-name          # matches the folder name
description: Use when …       # REQUIRED — this is what makes the skill discoverable
shape: command                # one of the three above
---
```

⚠ **`description:` is not decoration.** The harness auto-triggers a skill by matching intent against
this line — a skill with no readable description is invisible, no matter how good it is. Write it as
*"Use when <the situation>"*, in the words a person would actually use, not the words you named the
file. This is enforced: `system/hooks/enforce_skill_frontmatter.sh` blocks a `SKILL.md` written
without one.

## What a skill file should contain, by shape

**All three:** the frontmatter above · a one-line statement of the outcome it produces · the steps, in
the order they run · what it writes and where, if it writes anything.

**`interactive-workflow` also:** the phases, named · what it asks the person at each one · what
"done" looks like. If it can end without reaching an outcome, say so and say what that looks like —
a workflow with no legal way to say *"nothing was decided"* will invent a decision instead.

**`utility` also:** its inputs and outputs, precisely, because its caller is code or another skill and
cannot ask a clarifying question.

## Checklist

- [ ] `name:` matches the folder
- [ ] `description:` starts *"Use when…"* and reads like a person's problem, not a feature name
- [ ] `shape:` present and one of the three
- [ ] The outcome is stated in the first few lines, not buried
- [ ] Anything it writes is named, with its path
- [ ] If it can fail or stop early, that path is written down

---

## ⛔ WHAT THIS PAGE DELIBERATELY DOES NOT COVER — read before you go looking for it

The system this came from ran skills on a schedule, wrote dashboard tiles, and grouped skills under
"desks". Its conformance rules were built around that: a `cron-producer` shape, a `desk:` field, an
`emit_tile:` field, a mandatory `JUDGMENT_SPEC` block for scheduled skills that call a model, a diary
write-helper contract, and a seventeen-rule matrix (CF-1 … CF-17) describing which sweep or hook
enforces each one.

**None of that infrastructure exists here.** There is no scheduler, no dashboard, no tile format, and
no `desks/` tree in this repo. Those rules were left out on purpose rather than shipped as aspiration —
a conformance page that fails your skill for not declaring a dashboard tile you cannot have is worse
than no page, because it teaches you the tool is broken.

⚠ **This is a KNOWN, TRACKED GAP, not a finished decision.** If a scheduler ever ships here, the
producer half of this contract has to come with it — a scheduled skill that calls a model needs its
judgment boundary written down, and a background job that emits nothing is invisible when it dies.
The outstanding items are recorded in the debt ledger under `[SKILL-CONFORMANCE-PRODUCER-HALF]`.
