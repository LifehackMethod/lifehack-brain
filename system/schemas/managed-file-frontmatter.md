---
id: shared-schema-managed-file-frontmatter
title: Managed File Frontmatter Spec (New Model)
record_type: schema
desk: shared
created_at: 2026-03-18
updated_at: 2026-05-20
status: active
authority: archivist
tags: [schema, metadata, stage2-new-model]
---

# this system — Managed File Frontmatter Spec

Required frontmatter for all **new managed files** created after 2026-03-24 (new model).
Legacy files (pre-2026-03-24) are exempt from enforcement.

---

## Required Fields

```yaml
---
id: "{desk}-{YYYY-MM-DD}-{slug}"
title: "Human-readable title"
record_type: <see record-types below>
desk: <the owning project's slug, or root>
created_at: YYYY-MM-DD
updated_at: YYYY-MM-DD
status: active | draft | archived | superseded
authority: skill | user | archivist
---
```

### Field definitions

| Field | Purpose | Example |
|-------|---------|---------|
| `id` | Stable unique key | `widget-2026-03-25-the-joining-question` |
| `title` | Human-readable title | `"Grade: The 99ers"` |
| `record_type` | What kind of record this is | `log` or `decision` or `insight` |
| `desk` | Which project owns this | `widget` |
| `created_at` | Date of creation | `2026-03-25` |
| `updated_at` | Date of last significant update | `2026-03-26` |
| `status` | Lifecycle state | `active` |
| `authority` | What produced this file | `skill` or `user` |

---

## Optional Fields

Use when applicable. Do not invent fields outside this list.

```yaml
source_refs:
  - "the source this was pulled from"
  - "sources/research/2026-03-24-market-snapshot.md"
supersedes: "{id of file this replaces}"
superseded_by: "{id of file that replaced this}"
tags: [tag1, tag2]
notes: "Additional context"
```

> ⚖ **The per-subject field tables are not here (2026-08-11).** The document this came from
> carried a table of extra optional fields per desk, and a worked section per desk, naming one
> person's working areas and the fields their own records use. **Those are that person's data
> model, not this system's** — shipping them would hand every reader somebody else's categories
> and quietly suggest theirs should look the same. The fields above are the whole contract; add
> your own optional ones as you need them, and write them down beside the records that use them.

## Record types — the closed set

All files under `records/<type>/` use one of these six. **`docs/data-layout.md` is where the set is
defined; this table restates it so a writer reading the schema does not have to go and look.** If the
two ever disagree, `docs/data-layout.md` is right and this is stale.

| Type | Directory | What goes there |
|------|-----------|-----------------|
| `context` | `records/context/` | reference material, baselines, "how this thing works" |
| `decisions` | `records/decisions/` | a choice that was made, and why |
| `insights` | `records/insights/` | a pattern noticed; analysis worth keeping |
| `logs` | `records/logs/` | a session, a pass, a phase — what was done |
| `proposals` | `records/proposals/` | something proposed, waiting on a person to rule on it |
| `research` | `records/research/` | what `/research` writes |

**Closed means closed.** A seventh type is a change to `docs/data-layout.md`, not a judgment call at
write time.

> ⚖ **Four types were dropped on the way here (2026-08-11), and it is worth saying which.** The table
> this replaces carried `daily`, plus three that were marked as belonging to a single working area —
> raw ingests, their summaries, and per-client files. **A record type that only one person's work
> produces is not a filing category, it is that person's data model.** `daily` went with them because
> the skill that wrote it is not in this release. Anything they held now lands in `logs` or `context`.

### State-layer record type: `project-doc`

`state/briefs/` holds **project docs** — living single-source-of-truth documents
maintained by the `/project-manager` skill (one per project, continuously updated
in place). They are working state, not `records/` artifacts, so they sit outside
the `records/` canonical list above and use `record_type: project-doc`.

| Type | Location | Description | Authority |
|------|----------|-------------|-----------|
| `project-doc` | `state/briefs/{slug}.md` (or `<your notes>/state/briefs/` for root) | Living project source-of-truth; rehydratable operating state | skill \| user |

`id` for a project doc is a stable singleton key `{desk}-{slug}` (no date — the
doc is continuous, not session-stamped). See `<notes>/state/briefs/README.md`.

---

## Naming Conventions

| Location | Pattern | Example |
|----------|---------|---------|
| `state/projects/{slug}/records/{type}/` | `YYYY-MM-DD-{slug}.md` | `2026-03-25-discovery.md` |
| `state/projects/{slug}/state/` | fixed names | `current.md`, `open-loops.md` |
| `state/projects/{slug}/` | `brief.md` (the project doc) | `<notes>/state/projects/widget/brief.md` |
| `state/projects/{slug}/canon/` | fixed name | `current.md` |
| `state/projects/{slug}/sources/` | subdirs: `inbox/`, `reference/`, `research/` | `2026-03-25-transcript.md` |
| `state/projects/{slug}/_registry.md` | fixed name | — |

---

## Desk-Specific Write Rules

### Cal

Every session:
- `records/daily/{YYYY-MM-DD}.md` — session wrap-up
- `<notes>/state/current.md` — update live posture
- `<notes>/state/open-loops.md` — update domino list
- `records/decisions/{YYYY-MM-DD}-{slug}.md` — only on durable state change

No logs, no insights, no proposals.

## Status Lifecycle

```
draft → active → archived
               ↘ superseded (link via superseded_by field)
```

**active** = current, in-use record
**draft** = work-in-progress, not finalized
**archived** = completed, no longer active, but retain for history
**superseded** = replaced by a newer record (link to superseding record via `superseded_by`)

---

## Authority Values

| Value | Meaning | When to use |
|-------|---------|------------|
| `user` | Human created this directly | Session wraps, decisions, approvals, manual entries |
| `skill` | A skill created this | the output of any skill that writes a record |
| `archivist` | Archivist system produced this | Audit logs, drift proposals, system findings |

---

## Backward Compatibility

Files created before 2026-03-24 (legacy model) are exempt from this spec. The old
model used `artifact_type` instead of `record_type`, lived in paths like `artifacts/`,
`15_INSIGHTS/`, `20_PROPOSALS/`, `30_LOGS/`, `40_DECISIONS/`. Those files are
retained as historical record and do not require migration.

New files must conform to this spec.
