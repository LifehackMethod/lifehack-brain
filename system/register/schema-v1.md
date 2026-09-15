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
   ⚠ **SUPERSEDED, 2026-09-15 (same day, later — Option G, B2.3's design-contradiction ruling).**
   `launch_mode` was RESTORED, with a narrower, now-answerable meaning. See the "Addendum" section
   near the end of this file — the ruling above stood for only part of the day.
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
| `if` | nullable string | **Not in T2/B1.1's original shape — found and closed live by Feature B2.2 (2026-09-15).** Claude Code's own hook-entry format carries an OPTIONAL narrowing condition (e.g. `Skill(checkin)` on `guard_checkin_needs_project.sh`'s `PreToolUse`/`matcher=Skill` entry) that T2/B1.1/B1.2/B1.3 never harvested, because nothing before B2.2 ever regenerated the REAL `.claude/settings.json`/`hooks/hooks.json` (B1.3 wrote only to a scratch `--out` dir). The first real write silently dropped it — caught by the repo's own `system/hooks/tests/test_guard_checkin_needs_project.sh` going RED, not by the semantic-diff method, which is why that method (`(event, matcher, command, statusMessage)` tuples) is now `(event, matcher, command, statusMessage, if)` everywhere it's used. Null for every other hook row today. |
| `launch_mode` | string, **closed enum (4 values)** | **RESTORED 2026-09-15 (Option G) — see the "Addendum" section below for the full history and derivation.** `project` / `plugin` / `both` / `private` — which of the two real public wiring files (`.claude/settings.json` = "project", `hooks/hooks.json` = "plugin") carries this hook registration, or `private` if neither does (a private-repo hook, carried by `registrations`/`user` instead). Harvested mechanically from the row's own `surfaces` (`harvest.py`'s `derive_launch_mode()`) — 0 hand-typed values, required (not nullable): every hook row resolves to exactly one of the four. |
| `group` | nullable string, **open vocabulary, but legal only on a small non-blocking event allowlist** | **NEW 2026-09-15 (B5.2, "the map pilot") — see the second Addendum below.** Rows sharing one non-null value collapse onto ONE generated wiring entry (`generate.py`'s `collapse_group_rows()`), pointed at a single dispatcher script that runs each member's own body, unmodified, in its own isolated subshell, sequentially. Required-but-nullable, same convention as `if`. HARD-REJECTED by `validate_register.py` (not merely discouraged) on any row whose `event` is outside `schema_v1.GROUPABLE_HOOK_EVENTS` (`UserPromptSubmit`/`SessionStart`/`Notification`) — never a `PreToolUse`/`Stop`/`SubagentStop`/guard row, because collapsing a blocking-capable row into a shared dispatcher would recreate the single-point-of-failure "weakest guard wins" forbids (plan constraint 0.5). |

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
   deferred, not left null (Ruling 2). **Then RESTORED the same day** (Option G) — see the
   "Addendum" section below; this history entry stands as what was asked and answered FIRST, not
   as the field's final state.
3. ~~Strict unknown-key rejection — too strict for v1?~~ **Ruled: STRICT stays**, permanently
   (Ruling 3).
4. ~~JSONL vs YAML — confirm the call.~~ **Ruled: JSONL**, confirmed (Ruling 4).
5. ~~`scheduled.path` is forced to double duty — confirm acceptable?~~ **Ruled: KEPT**, documented
   as intended (Ruling 5).

---

## Addendum, 2026-09-15 (later the same day) — `launch_mode` RESTORED (Option G)

**This supersedes Ruling 2 above for everything except the historical record — that stays as
written, because it is honestly what was asked and ruled first.**

Between the morning rulings (above) and this addendum, Phase B2 ran its live re-measurement
(B2.3) and hit a **design contradiction**: the plan's "non-overlapping, complementary" de-dup
target for the two public wiring files cannot coexist with "no mode loses a guard" — every
duplicated hook row besides `emit_harness_brief.sh` protects something a *single* surface's own
standalone population still needs (external-service guards, general git safety, absolute
Brain-root paths). Reported in `B2.2-report.md` / `B2.3-report.md`; Enver's ruling (**Option G**,
2026-09-15, "third set" in the plan's Discoveries) reframed the target around measured reality
(students never double-fire; only the admin's own repo/plugin-folder sessions do) and named the
fix explicitly: *"The `launch_mode` field is RESTORED to the register (records which file holds
which guards)."*

**The restored field is deliberately NOT the field B1.1 first drafted.** B1.1's version asked
"which SESSION MODE loads this unit" (clone-only vs plugin-enabled vs plugin-folder-as-cwd) — a
question the morning ruling correctly dropped as premature, since D5 (the runner) hadn't been
decided yet and B2 hadn't yet measured which files actually survive its de-dup. Option G's version
asks a narrower, already-mechanically-answerable question instead: **for one hook registration,
which of the two real PUBLIC wiring FILES carries it right now** — `.claude/settings.json`
("project") and/or `hooks/hooks.json` ("plugin"). That is a fact already sitting in every hook
row's own `surfaces` list; nothing new needs to be measured or guessed to answer it.

**Schema (`schema_v1.py`):** a new `TYPE_FIELDS["hook"]["launch_mode"]` field, required
(non-nullable), closed 4-value enum — `LAUNCH_MODES = ("project", "plugin", "both", "private")`.
Derived from what the live register actually contains (a fresh 319-row harvest, 63 hook rows,
2026-09-15), not chosen in the abstract:

| value | meaning | count (2026-09-15 harvest) |
|---|---|---|
| `both` | registered on both `settings` (project) and `plugin` | 50 |
| `plugin` | `hooks/hooks.json` only | 5 (includes the post-B2.2 de-dup'd `emit_harness_brief.sh`) |
| `project` | `.claude/settings.json` only | 1 |
| `private` | neither — a private-repo hook carried by `registrations`/`user` instead; the public project/plugin split does not apply | 7 |

Cache mirrors (`cache-settings`/`cache-plugin`) are deliberately excluded from this axis: every
cache surface observed in the live register accompanies its own real `settings`/`plugin` (or is
absent entirely for private hooks), so folding them in would never change today's answer — a
cache-only row would be a content-divergence finding for the generator's existing
cache-divergence check, not this field's job.

**Harvester (`harvest.py`):** `derive_launch_mode(surfaces)` — reads the same `surfaces` set
`harvest_hooks()` already builds from `hook_surfaces()`'s own surface names; 0 hand-typed values,
same discipline as every T2-proven field. Raises loudly (never silently defaults) on a surface
combination none of the four cases cover — a genuine unmodeled finding, not a case to paper over.

**Generator (`generate.py`):** reports the launch_mode distribution (`LAUNCH_MODE DISTRIBUTION`
section, `report()`) as a pure read of already-validated rows. `build_hooks_doc()` never reads
`launch_mode` — it plays no part in what gets written to any wiring file, so restoring it cannot
change emitted wiring (verified: `--install-root` into a scratch `git archive HEAD` copy still
produces byte-identical `.claude/settings.json` / `hooks/hooks.json`).

## Addendum, 2026-09-15 (same day) — `group` NEW (B5.2, the map pilot)

**Feature B5.2** (`enforcement-layer.phase-2.plan.md` PHASE B5) collapses the pilot skill group's
(read / checkin / save / project-manager) 4 always-firing `UserPromptSubmit` inject hooks
(`announce_plan_write.sh`, `pm_persist.sh`, `save_routing_hint.sh`, `skill_anchor_inject.sh` — all
matcher `""`, all `launch_mode: "both"`) onto ONE generated load path, per the design scout's
approved design (session scratchpad `B5.2-design.md`). This is the FIRST field this schema adds
that was not T2-proven or forced by a live regeneration bug — it is a forward-looking chaining/
grouping primitive, deliberately narrow in scope.

**Schema (`schema_v1.py`):** `TYPE_FIELDS["hook"]["group"]` — nullable string, required key
(present-but-null is the default for a row not in any group), open vocabulary (same reasoning as
`needs`/`returns`: closing it to a fixed enum would force a schema migration for a second pilot
group next quarter). `GROUPABLE_HOOK_EVENTS = ("UserPromptSubmit", "SessionStart", "Notification")`
is the allowlist a non-null `group` may combine with — enforced in `validate_register.py` (a
cross-field check, since a single-field `('enum', ...)` hint cannot express "legal combined with
THIS OTHER field's value"), not in `schema_v1.py` itself.

**Why the allowlist is a HARD REJECT, not a WARN or a convention:** the lead's binding condition
for B5.2 (Discoveries, 2026-09-15) states it plainly — collapsing rows into one dispatcher process
entangles their exit codes into one process's exit code. For an INJECT hook this is harmless (it
never blocks; there is no "decision" to entangle). For a row whose event CAN deny a tool call
(`PreToolUse` and its subclasses, `Stop`/`SubagentStop`, or any guard on any event), it would
recreate exactly the single point of failure plan constraint 0.5 forbids ("weakest guard wins —
one dispatcher on a broad event is a single point of failure"). Closing this at the validator
means the mistake is structurally impossible to introduce by a later hand-edit, rather than
relying on someone remembering a rule that lives only in a comment. Proven with a planted-bad row
(`group` set on a `PreToolUse` guard row): `validate_register.py` rejects it, and `generate.py`
(which runs the identical schema gate before writing anything) refuses the whole run — no file
written, for any target.

**Generator (`generate.py`):** `collapse_group_rows()` — for each distinct non-null `group` value
among rows destined for one wiring surface, sharing the same `(event, matcher, launch_mode, if,
args)`, emits ONE synthetic row in their place, whose `path` is the group's dispatcher script
(`system/hooks/group_dispatch_<group>.sh`, the filename DERIVED from the group string, never
hand-typed in the generator). The dispatcher's own on-disk existence is re-checked by the same
assert-on-write gate every other hook row goes through — a missing dispatcher script REFUSES that
target's write, exactly like a missing member script would. The dispatcher file itself is a
normal, hand-authored, committed hook script (never generated on disk) and deliberately carries NO
register row of its own (that would double-emit its own wiring entry alongside the synthetic one)
— it is named in `system/register/omission-exemptions.txt` instead, with the reason stated there.

**Pilot value, this feature:** `group: "pilot-map-ups"` on the 4 named hook rows above; every other
hook row in the register carries `group: null`. The 3 guards in the pilot's scope
(`guard_checkin_needs_project.sh`, `guard_pm_flag_store.sh`, `guard_brief_truncation.sh`) are
`PreToolUse` rows and therefore structurally ineligible for `group` — untouched by this feature,
by construction, not merely by convention.

