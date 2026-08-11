---
id: root-schema-backlog-entry
title: "BacklogEntry Schema v1.0 — the typed backlog model"
record_type: schema
created_at: 2026-06-19
updated_at: 2026-06-19
status: active
authority: user
owners: [backlog-authority, save-skill]
note: >
  The frozen entry schema that the Backlog groomer (Window 4) and /save's write-time stamp
  (Window 2) build against. Changes require bumping schema_version AND reconciling with the
  groomer before they land. Frozen by Window 1 (interface freeze).
---

# BacklogEntry Schema (v1.0)

> **Frozen by Window 1 (interface freeze, 2026-06-19).** The drain + groomer (Window 4) and
> `/save`'s write-time stamp (Window 2) MUST build against this exact field set and these enums.
> Any change requires bumping `schema_version` here AND reconciling with the groomer. No silent
> field additions.

**schema_version: "1.0"**

---

## Why a schema (the two-axis model)

`state/debt-ledger.md` already encodes **type** structurally — an item's section IS its type
(`## Open` = debt, `## Projects` = project, …). What's missing is a **state** (lifecycle) axis:
without it, the groomer can't tell a `blocked` item (externally waiting — zero staleness defect)
from an `actionable` item (should be moving). The two axes — **`type` + `state`** — are what make
"zero" honest: **zero actionable debt**, not zero items. (A living system never has zero items:
monitoring, externally-blocked, and parked items never reach zero, and that's correct.)

---

## Representation: inline tags (Option A)

New and groomer-touched entries stay prose bullets, with backtick tags appended after the text:

```
- **[AREA-TAG] description** `type:debt` `state:actionable`
- **[AREA-TAG] description** `type:blocked` `state:waiting-external` `unblock:Air gws-cron isolation done`
- **[AREA-TAG] description** `type:project` `state:parked` `done_when:organism build ships`
```

**Untagged legacy entries are valid.** The groomer classifies them best-effort during the Window-4
drain: section membership ⇒ `type`; absence of a state tag ⇒ `state:actionable` for debt/decision,
`state:parked` for items already in the `## Parked`/`## Blocked` sections. Nothing is deleted on a
first pass.

*(Why inline tags over a per-entry YAML block: it needs no migration of existing entries before the
groomer can run, it's human-readable in the raw `.md`, and it deletes with the line. The lighter move.)*

---

## Fields

**Required** (on any new or groomer-touched entry): `type`, `state`.

**Optional** (stamp when known):
| Field | Type | Notes |
|---|---|---|
| `unblock` | str | The condition that unlocks the item. **Required** when `state` is `waiting-external` or `waiting-date`. |
| `owner` | str | desk_id or `user` — who drives it. Omit if obvious. |
| `last_touched` | YYYY-MM-DD | Last actively worked. The groomer's staleness signal (queue desks only). |
| `done_when` | str | Observable completion condition → enables **deterministic** done-detection (no LLM re-classification). |

---

## `type` enum  (mirrors the existing debt-ledger sections)

| value | Section / home | Meaning |
|---|---|---|
| `debt` | `## Open` | Genuinely broken / stale / half-finished system thing. Fix these. |
| `project` | `## Projects` | Future build; tracked, not owed. |
| `decision` | `## Decisions` | Needs an the operator call before it can move. |
| `blocked` | `## Blocked` | Waiting on a condition (external action, date, another item). |
| `chore` | desk `open-loops.md` | Routine desk work. Lives in the desk's open-loops, NOT the root ledger. |
| `idea` | desk `open-loops.md` | Captured idea; desk-local. NOT the root ledger. |

**`parked` is NOT a type — it is a `state`.** Items in the ledger's `## Parked` section are
`type:project` or `type:decision` (or `type:idea`) with `state:parked`.

---

## `state` enum  (the new lifecycle axis)

| value | Meaning |
|---|---|
| `actionable` | Ready to work; no blocker. |
| `waiting-external` | Waiting on something outside this system (a third party). Requires `unblock`. |
| `waiting-date` | Waiting for a date/event. Requires `unblock` (the date/condition). |
| `monitoring` | Watching something; no action until a signal fires. |
| `parked` | Intentionally deferred; someday-maybe. |
| `done` | Completed. **Transient only** — used by the groomer's done-detection pass, then the line is DELETED (ledger discipline). Never leave `done` live in an active section. |

**The headline "what's actually broken" number = `type:debt` AND `state:actionable`.** That single
query is what a flat list could never answer and is the antidote to the "95/243 scare."

---

## Groomer invariants (Window 4 reads these)

- **One home per item.** If the same item appears in both the root ledger AND a desk open-loops,
  that's a duplicate — the root ledger wins; the desk copy is deleted on the next pass.
- **Register-mode subjects** (a subject whose backlog is a register rather than a list): items in
  `waiting-external` / `waiting-date` are **NOT** flagged stale. Queue desks: same states flagged if
  `last_touched` exceeds a threshold.
- **Done-detection is deterministic** via `done_when` — the groomer evaluates the condition
  mechanically; no LLM re-classification on items that carry one.
- **New items** (written by `/save`, Window 2) arrive pre-stamped with `type`+`state`, so the groomer
  is ~0-LLM in steady state and only best-effort-classifies legacy untagged items.

---

## Compatibility with `guard_ledger_discipline.sh`

The guard blocks ADDING a `✅ / RESOLVED / CLEARED / FIXED` annotation to the `## Open` section
(close an item by DELETING its line, not annotating). It operates on those keywords + the section
boundary — it does **not** parse inline tags. Adding `` `type:debt` `` to a bullet is new content on
an existing line, which the guard passes. (Its forbidden pattern is `✅|\b(RESOLVED|CLEARED|FIXED)\b`,
which does not match backtick-tag syntax.)
