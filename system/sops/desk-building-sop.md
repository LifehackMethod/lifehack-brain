---
topic: [build-process]
id: system-playbook-desk-building-sop
title: Desk-Building SOP — how to stand up a full desk
record_type: playbook
desk: root
created_at: 2026-07-10
updated_at: 2026-08-15
status: active
authority: user
---

# Desk-Building SOP

> PORTED from `claudeops-config`'s `system/sops/desk-building-sop.md` (migration F9.6, "THE DESK
> PLANE"). ⚖ Enver, `authority: user`, verbatim: *"the new system should have a template and a way of
> creating new desks, so that a new desk comes pre-filled with all of the folders that it needs and all
> of the knowledge that it needs… It should be born like a deer or a cow — it comes out of the womb and
> it can already start walking."*
>
> **This page is the ONE canonical statement of the full-desk shape.** No other file in this repo
> re-specifies it — anywhere else the shape is mentioned, it points here rather than restating the
> list, which is the exact drift this port closed: the donor carried FOUR independent statements of
> the desk shape (this SOP's own list, `claudeops-schema-brief.md` §Desk Structure, the archivist's
> conformance checks, and `desk_scaffold.py`'s own folder list) that had quietly gone out of sync with
> each other and with the 9 real desks actually in use. Measured against those 9 real desks on
> 2026-08-15: `projects/` exists in 8 of 9 and was in **none** of the four donor statements — added
> below. `views/` exists in 7 of 9 — real, but not universal, so it stays **optional**, never assumed.

## ⚠ This is the HEAVY shape — a different, later thing from what `/ingest` builds by default

`/ingest` PHASE 4 writes a **knowledge folder** — the light subset `canon/current.md` +
`canon/purpose.md` + `records/`, nothing else — via `folder_scaffold.py`. That is the shipped default
for every subject `/ingest` finds, and it is documented (canonically, for that shape) in
`docs/data-layout.md`. **A full desk, built by THIS SOP via `desk_scaffold.py`, is a strict superset of
a knowledge folder, reached only by a separate, deliberate, later human act** — never automatic, never
run by `/ingest` itself. If you are looking for what a fresh subject gets on day one, that answer lives
in `docs/data-layout.md`, not here. This page is for promoting one of those folders — or standing up a
desk directly — once it has earned the heavier shape.

## When to build a full desk

Warranted only when a subject is a standing life-arena outgrowing the light knowledge-folder shape —
needs its own session identity, its own open-loops tracking, or automation wired to it. A one-off topic
stays a record; a folder that just needs canon + records stays a knowledge folder. Promotion is always
a human call, never a skill's own decision.

## The shape (canonical — nowhere else in this repo restates this list)

```
desks/{desk}/
├── canon/current.md      stable reference, human-instructed writes only
├── canon/purpose.md      what this desk is for
├── state/current.md      where we are, session-significant changes only
├── state/open-loops.md   unresolved items pending action
├── records/{type}/       dated artifacts (insights, logs, decisions, etc.)
├── sources/inbox/        intake landing zone
├── projects/             per-project subfolders (brief.md · canon.md · records/) — ⭐ ADDED 2026-08-15,
│                         measured in 8 of 9 real desks, absent from every prior shape doc
├── views/                OPTIONAL — measured in 7 of 9 real desks, not universal; opt-in only
├── _registry.md           folder registry — known managed files for this desk
├── CLAUDE.md              desk identity, read order, scope, write rules
└── .claude/settings.json  machine-local — NOT scaffolded by the tool, added by hand per machine
```

## Procedure (one-punch, then two hand steps)

1. **Scaffold the folder shape (deterministic):**
   ```
   python3 system/tools/cowork-ingest/desk_scaffold.py \
     --drive-root "$NOTES_ROOT" --desk <slug> --purpose "<one line>" \
     [--reads-external yes|no] [--views yes|no]
   ```
   Creates the full conformant shape + stub files (canon stubs carry `authority: user`, so a
   `guard_canon_write`-class hook accepts them). `views/` is opt-in — pass `--views yes` only if this
   desk actually needs it; do not pass it "just in case." Refuses to clobber an existing desk. Use
   `--dry-run` first to preview the folder/file list without writing anything.
2. **Register in the keystone (BY HAND — it is a code file):** paste the block the scaffolder prints
   into `system/desk-registry.yaml` under `desks:`. Deliberately not auto-edited — the registry is read
   by every organ that needs to enumerate desks (e.g. `backlog_groom.py`'s `load_registry()`), and
   hand-maintenance keeps adding a desk a conscious act.
3. **Wire to automation ONLY if the desk needs it** — a pure knowledge desk (no cron) leaves
   `health_producer` / `pulse_slot` / `status_tile_path` = `null` in the registry block and is done at
   step 2.
4. **Verify conformance:** every file in "The shape" above must exist and be non-empty; `_registry.md`
   must list them.

## Portability note

- **Case A — the subject already has a knowledge folder:** promote it in place — scaffold the missing
  pieces (`state/`, `sources/inbox/`, `projects/`, `_registry.md`, `CLAUDE.md`, optionally `views/`)
  around the existing `canon/` + `records/` rather than starting over. `desk_scaffold.py` refuses to
  clobber, so do this by hand for an existing folder today; a promote-in-place mode is not built.
- **Case B — a subject with no home at all:** run this SOP directly.

**Deferred seam (NOT built):** an automatic promote-in-place mode for an existing knowledge folder.
`desk_scaffold.py` today only stands up a brand-new `desks/{desk}/`. Leave the seam; do the promotion by
hand until it earns automation.
