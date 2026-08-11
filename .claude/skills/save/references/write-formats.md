# Write formats — read this at the write step

The exact frontmatter and templates `/save` writes against. Deliberately kept out of `SKILL.md`: these
are pure format, read at the moment of writing. The *rules* about whether to write at all — the canon
gate, `vetted: false`, dedup, journal-first — stay in the skill, at their point of use.

Fill every `{placeholder}`. `{topic}` always comes from **`$DATA/memory/topic-vocab.md`, the person's
own vocabulary** — only slugs already in it, never an invented one. Nothing fits → omit the field and
say so.

## § Dated record

```yaml
---
id: {project-or-root}-{YYYY-MM-DD}-{slug}
title: "{the finding, as a title}"
record_type: {context | decisions | insights | logs | proposals | research}
desk: {slug of the owning project, or root}
topic: [{slug(s) from their vocabulary}]
created_at: {YYYY-MM-DD}
updated_at: {YYYY-MM-DD}
status: active
authority: skill
confidence: {CONFIRMED | INFERRED | HYPOTHESIS}
tier: dated-record
type: {finding | decision | possibility | suggestion | pros-cons | dead-end | open-question}
source_refs:
  - "{REQUIRED — the transcript turn, or the source quoted}"
---

{the question this answers}

{why, and the conclusion — about three sentences. For pros-cons: the FULL weighing, both sides.
For a dead-end: what was tried and WHY it failed.}
```

## § Canon proposal

Always `vetted: false`. The machine proposes; only a person vets.

```yaml
---
id: {project-or-root}-{YYYY-MM-DD}-{slug}-canon-proposal
title: "PROPOSAL: {what it proposes}"
record_type: proposals
desk: {slug, or root}
topic: [{slug(s)}]
created_at: {YYYY-MM-DD}
updated_at: {YYYY-MM-DD}
status: draft
authority: skill
vetted: false
confidence: INFERRED
tier: dated-record
---

Proposed addition to {the target canon path}:

> {the exact line(s) proposed — verbatim, never abbreviated}

Rationale: {one or two sentences}
Conflict scan: {NEW | DUPLICATE | CONFLICT} — {N} canon file(s) read.
```

## § Snapshot

A number with an expiry date. **Never promoted to canon**, at any point.

```yaml
---
id: {project-or-root}-{YYYY-MM-DD}-{slug}-snapshot
title: "{what the number represents} — {YYYY-MM-DD}"
record_type: context
desk: {slug, or root}
topic: [{slug(s)}]
created_at: {YYYY-MM-DD}
updated_at: {YYYY-MM-DD}
status: active
authority: skill
confidence: CONFIRMED
tier: snapshot
shelf-life: {REQUIRED — ISO date. 7–14 days out unless a duration was given}
type: snapshot
---

{what it is}: {the number}

Re-pull after {shelf-life}. Do not promote to canon.
```

## § Journal session entry

Appended to `$DATA/system/journal.md` under a new heading.

```markdown
## SESSION — {YYYY-MM-DD} | {project slug}

**Session:** {what was worked on — one sentence}
**Follows:** {what this picked up from, or the prior state}
**Failed / changed:** {what did not work, what pivoted, and why — honestly}
**Key findings:** {the two to four conclusions that matter}
**End state:** {where it stands at close — what is open, what is done}
**Missteps:** {anything that cost time or should not be repeated}
```

If the debt check was skipped, add this line inside the entry:

```
**Debt-check:** skipped at close — debt from this session may be uncaptured.
```

## § Journal ledger row

One line, appended under the log section:

```
{YYYY-MM-DD} | {desk} | {slug} | {event} | supersedes: {path or —} | → {artifact-path}
```

`{event}` is what changed **and why**, readable with no other context. Not a filename echo.

## § Mid-session record

Filename: `YYYY-MM-DD-{slug}.md`, where the slug is 2–5 kebab-cased words from the title.

```yaml
---
id: {project-or-root}-{YYYY-MM-DD}-{type}-{slug}
title: {title}
record_type: {context | decisions | insights | logs | proposals | research}
desk: {slug, or root}
topic: [{slug(s)}]
created_at: {YYYY-MM-DD}
updated_at: {YYYY-MM-DD}
status: active
authority: user
confidence: {CONFIRMED | INFERRED | HYPOTHESIS | UNKNOWN}
tier: {dated-record | snapshot}
type: {finding | decision | possibility | suggestion | pros-cons | dead-end | open-question | snapshot}
---
```

## § Behavioural rule

Three parts. Never just the statement — a rule with no reason gets followed until it is inconvenient,
then dropped, because nobody knows what it was protecting.

```
{one-sentence rule statement}
**Why:** {the reason — the incident behind it, the constraint, or the stated preference}
**How to apply:** {when and where it kicks in; the edge cases, if any}
```
