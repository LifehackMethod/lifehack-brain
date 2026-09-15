---
topic: [system-architecture, enforcement-layer]
title: "The register — schema v1"
record_type: system-doc
status: ruled (Enver, 2026-09-15) — schema v1 locked, see "Rulings" section below
created_at: 2026-09-15
---

# The register — schema v1

**Feature B1.1** of `enforcement-layer.phase-2.plan.md`. This is the file format for the LEDGER —
the single register that Phase B1 builds a harvester (B1.2) and generator (B1.3) around. It starts
from the T2-proven entry shape (`t2-register.json`, 114 entries, 0 semantic-diff rows, 0
hand-annotations — see `records/2026-09-13-phase-1/t2-result.md`) and extends it per B1.1's four
Execute bullets. Enver ruled on the five open questions this doc originally raised (2026-09-15,
below) — v1 is now locked to that ruling.

## Rulings (Enver, 2026-09-15)

1. **`hook.event` is a CLOSED enum** — the fixed Claude Code hook-event set. See `HOOK_EVENTS` in
   `schema_v1.py` and the `type: hook` table below for the full 33-value list and citation.
2. **`launch_mode` is DROPPED from v1 entirely** — removed from the schema, the validator, this
   doc, and both fixture generators. Not deferred-null; not present at all.
3. **STRICT unknown-key rejection** — any field not in the schema fails the row, and the
   validator's error message names the offending key (`validate_register.py`,
   `STRICT_UNKNOWN_KEYS`).
4. **Format is JSONL** — confirmed, not YAML.
5. **`scheduled` rows sharing the manifest path is KEPT** — every `scheduled` row's `path`
   resolves to `/system/pulse-config.md` rather than a unique per-row file; documented as
   intended, not a gap to close later.

**Format: JSONL** (one JSON object per line), not YAML. One line per unit means `git diff` shows
exactly which units changed, sorting is trivial (`sort file.jsonl`), and a line-oriented validator
never has to parse the whole file to isolate one bad row (open question #5 below — this is the
one Enver most likely wants to weigh in on).

**Validator:** `validate_register.py`, reading rules from `schema_v1.py` (a plain Python dict of
field definitions — no `jsonschema`/`PyYAML` dependency exists in this repo yet, and pulling one in
for four field-checks would be the opposite of "files a human can open and fix by hand").

---

## The four unit classes (B1.1 (a))

Every register row has a `type`: `hook` (system/hooks/, both repos — T2's original set) · `tool`
(system/tools/, both repos) · `skill` (`.claude/skills/**/SKILL.md`) · `scheduled` (one row of
`system/pulse-config.md`'s `jobs` block). This is deliberately not the full T1 caller-ontology
(that is Feature B1.5's lint, layered on top later) — it is only "what kind of thing is this," the
question every other field branches on.

## Fields, and why each one is here

### Common envelope — every unit type carries these

| field | type | rationale |
|---|---|---|
| `id` | string | A stable handle so the harvester (B1.2), generator (B1.3) and journal (B4) can all name the same unit without re-deriving identity from scratch each time. |
| `type` | enum (4 values above) | Everything else in this table branches on it; the one field that must never be ambiguous. |
| `repo` | enum `public`/`private` | T2-proven. The checkout that OWNS this unit's source. Not the same axis as `surfaces` below — constraint 0.5 is explicit that the plugin cache is a derived surface, never a repo of record, so `cache` is never a legal value here. |
| `path` | string, repo-relative, leading `/` | T2-proven. The on-disk address both the harvester and generator key on. |
| `exists` | bool | T2-proven mechanical disk check. Feeds B1.3's assert-on-write refusal (the 50-broken-path class) directly. |
| `sha` | nullable string | T2-proven mode-12 drift detector (short sha256). Null iff `exists` is false — enforced as a cross-field rule, not left to convention. |
| `needs` | list of strings, default `[]` | B1.1 (c)'s chaining seed. An empty list is the honest mechanical default until a unit actually declares a dependency — never a hand-annotation, never closed to a fixed vocabulary (closing it would foreclose composition, which constraint 0.5 forbids outright). |
| `returns` | list of strings, default `[]` | Same reasoning, the output half. |
| `cost_bytes` | nullable number | B1.1 (d). Left empty until Phase B4 (the fire-journal) measures it for real — never zero-filled, never estimated. |
| `cost_ms` | nullable number | Same, latency partner metric (T3's `guard-timing.md` precedent for the pairing). |

### `type: hook` — carries T2's original fields verbatim

| field | type | rationale |
|---|---|---|
| `event` | string, **closed enum (33 values)** | The hook event name. Ruled CLOSED by Enver, 2026-09-15 (see "Rulings" above). The enum is the union of two sources — (1) this repo's own wiring, grepped 2026-09-15 from `.claude/settings.json` and `hooks/hooks.json`: 6 events actually fire here today (`PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `UserPromptExpansion`, `SessionStart`, `Stop`); (2) the documented set, Claude Code's "Hooks reference" at `https://code.claude.com/docs/en/hooks` (cross-linked from `https://code.claude.com/docs/en/hooks-guide`), fetched 2026-09-15 — the full 33-event set Claude Code supports across its handler-support tiers (`PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`, `PermissionRequest`, `PermissionDenied`, `Stop`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `TeammateIdle`, `UserPromptSubmit`, `UserPromptExpansion`, `Notification`, `MessageDisplay`, `SubagentStart`, `StopFailure`, `PreCompact`, `PostCompact`, `PreModelSwitch`, `PostModelSwitch`, `Elicitation`, `ElicitationResult`, `ConfigChange`, `CwdChanged`, `DirectoryAdded`, `FileChanged`, `InstructionsLoaded`, `WorktreeCreate`, `WorktreeRemove`, `SessionEnd`, `SessionStart`, `Setup`). The 6 wired-today events are already inside the documented 33, so the union equals the documented set — see `HOOK_EVENTS` in `schema_v1.py`, the single source of truth. |
| `matcher` | string, may be `""` | T2-proven. |
| `args` | string, may be `""` | T2-proven. |
| `status` | string, may be `""` | T2-proven — the `statusMessage` shown to the user. |
| `surfaces` | non-empty list, closed enum (6 live files) | T2-proven. Which of today's live registration files currently carry this entry — B2's de-duplication target. Required non-empty: a hook entry with zero surfaces isn't a registered hook. |
| `status_conflicts` | list of strings, default `[]` | T2-proven — same key, disagreeing status messages across surfaces. |

### `type: tool` — system/tools/ units

| field | type | rationale |
|---|---|---|
| `language` | enum `py`/`sh`/`other` | Derived mechanically from the file extension. Lets the generator/lint pick an invocation shape without re-deriving it from the path suffix on every read. |

### `type: skill` — `.claude/skills/**/SKILL.md` units

| field | type | rationale |
|---|---|---|
| `name` | string | Read straight from the SKILL.md frontmatter's `skill:` field — the skill's declared identity, independent of its folder name. |
| `description` | string, may be `""` | Read straight from the frontmatter's `description:` field — this is what the model itself reads as an instruction surface (T1's `skill-referenced` caller class already treats these documents that way); the register should carry what's actually there, not a re-summary of it. |

### `type: scheduled` — one row of `system/pulse-config.md`'s `jobs` block

| field | type | rationale |
|---|---|---|
| `schedule_name` | string | The row's `name` column — pulse-config.md's own identifier for the job. |
| `enabled` | string, open vocabulary | pulse-config.md's own convention: `yes` to run, anything else is a DECLARED disposition (`no`, `parked`, `waiting-on-<thing>`), not just "off." Closing this to an enum would freeze vocabulary a human still writes by hand today — left open on purpose. |
| `interval_seconds` | nullable int | The row's `interval` column, parsed as-is. |
| `command` | string | The row's `command` column — the shell command Pulse actually fires. |

`scheduled` still carries the common `path` field (every type does, see below) — it resolves to
the shared manifest file (`/system/pulse-config.md`), since a scheduled row's identity is really
`schedule_name` plus that one file, not a unique file of its own. **Ruled KEPT by Enver,
2026-09-15** (Ruling 5, above) — this is documented as intended, not a gap `path` nullability
would later need to close.

---

## Validator design

`validate_register.py` checks, per row: every schema field for the row's `type` is present with
the right shape (required fields must be present even when nullable — a missing key is always a
reject, a present-but-null value is only a reject when the field isn't nullable) · enum/closed-list
fields only take listed values · the `exists`/`sha` cross-field rule · **no unknown fields, ever**
— a stray key is either dead weight or an un-ruled extension, and constraint 0.5 ("encode only
what has already converged") says neither belongs in silently, so the row is rejected and the
error names the exact key. Ruled STRICT, permanently, by Enver, 2026-09-15 (Ruling 3, above).

---

## Design questions Enver ruled on, 2026-09-15 (history — see "Rulings" above for the verdicts)

These were the five open questions this doc originally raised at the B1.1 checkpoint. Kept here,
struck through, as the record of what was actually asked — the "Rulings" section above is the
verdict each one got; nothing here still applies.

1. ~~`hook.event` — closed enum or open string?~~ **Ruled: CLOSED**, to the documented 33-event
   Claude Code set (Ruling 1).
2. ~~`launch_mode` — what closes it, and when?~~ **Ruled: DROPPED from v1 entirely** — not
   deferred, not left null (Ruling 2).
3. ~~Strict unknown-key rejection — too strict for v1?~~ **Ruled: STRICT stays**, permanently
   (Ruling 3).
4. ~~JSONL vs YAML — confirm the call.~~ **Ruled: JSONL**, confirmed (Ruling 4).
5. ~~`scheduled.path` is forced to double duty — confirm acceptable?~~ **Ruled: KEPT**, documented
   as intended (Ruling 5).
