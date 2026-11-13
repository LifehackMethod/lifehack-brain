---
topic: [build-process]
id: system-playbook-desk-building-sop
title: Desk-Building SOP — how to stand up a full desk
record_type: playbook
desk: root
created_at: 2026-07-10
updated_at: 2026-11-02
status: archived
authority: user
history: "system/sops/desk-building-sop.history.md (retired and moved text; never read in normal use)"
route_format: "[section, line_in_this_file, purpose]; find a section by grep -n on its heading text; generated last, regenerate after any edit"
route:
  - ["heavy shape", 38, "a full desk vs the light knowledge folder /ingest builds"]
  - ["when", 49, "when a subject warrants a full desk; promotion is a human call"]
  - ["the shape", 56, "the canonical folder list, and where a desk's code goes"]
  - ["procedure", 77, "scaffold, register, wire automation only if needed, verify"]
  - ["portability", 101, "promoting an existing knowledge folder; the deferred seam"]
---

# Desk-Building SOP

> **ARCHIVED 2026-11-13. Do not act on this page.** It is kept whole, word for word, as history, at
> `system/_retired-2026-11-13/desk-building-sop.ARCHIVE-2026-11-13.md`. The in-force desk SOP is
> `system/sops/desk-building-sop.md` (promoted from the 2026-11-06 V2 draft), which holds the desk's shape. Build
> or change a desk from that page, not this one. *(Item 7, 2026-11-11: promote the draft, archive v1 with a banner.)*

> **Shared tools:** `system/organism/elements/shared-layer.md` — common tools exist once in `shared/` (list: `system/register/toolbox.md`); use them, never copy them.

> The operator, verbatim: *"the new system should have a template and a way of
> creating new desks, so that a new desk comes pre-filled with all of the folders that it needs and all
> of the knowledge that it needs… It should be born like a deer or a cow — it comes out of the womb and
> it can already start walking."*
>
> **This page is the ONE canonical statement of the full-desk shape.** Where restated (for example the
> scaffold's own folder list), copies must agree with this page.

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

## The shape (canonical; where restated, for example the scaffold's own folder list, copies must agree with this page)

```
desks/{desk}/
├── canon/current.md      stable reference, human-instructed writes only
├── canon/purpose.md      what this desk is for
├── state/current.md      where we are, session-significant changes only
├── state/open-loops.md   unresolved items pending action
├── records/{type}/       dated artifacts (insights, logs, decisions, etc.)
├── sources/inbox/        intake landing zone
├── projects/             per-project subfolders (brief.md · canon.md · records/)
├── views/                OPTIONAL — not universal; opt-in only
├── _registry.md           folder registry — known managed files for this desk
├── CLAUDE.md              desk identity, read order, scope, write rules
└── .claude/settings.json  machine-local — NOT scaffolded by the tool, added by hand per machine
```

A desk's notes live here, in your notes folder. Code that serves only this desk lives in your personal
code folder under `desks/<desk>/tools/`; other standalone scripts live in the personal code folder itself
(one folder for the whole person); a skill lives in `~/.claude/skills/<name>/`.

## Procedure (one-punch, then two hand steps)

1. **Scaffold the folder shape (deterministic):**
   `$NOTES_ROOT` is your notes folder (the AI Brain): `NOTES_ROOT="$(python3 <plugin>/shared/brain_root.py --quiet)"`.
   ```
   python3 <plugin>/system/tools/cowork-ingest/desk_scaffold.py \
     --drive-root "$NOTES_ROOT" --desk <slug> --purpose "<one line>" \
     [--reads-external yes|no] [--views yes|no]
   ```
   Creates the full conformant shape + stub files (canon stubs carry `authority: user`).
   `views/` is opt-in — pass `--views yes` only if this
   desk actually needs it; do not pass it "just in case." Refuses to clobber an existing desk. Use
   `--dry-run` first to preview the folder/file list without writing anything.
2. **Add it to your desk list (BY HAND):** add the entry the scaffolder prints under `desks:` in your
   own desk list, `<notes>/desks/desk-registry.yaml` (the scaffolder says how to start the file if it does
   not exist yet). The plugin ships no desk list; tools read yours through `shared/desk_list.py`.
   Deliberately not auto-edited — the list is read
   by every organ that needs to enumerate desks (e.g. `backlog_groom.py`), and
   hand-maintenance keeps adding a desk a conscious act.
3. **Wire to automation ONLY if the desk needs it** — a pure knowledge desk (no cron) is done at step 2.
   A desk's scheduled jobs are added as rows per `system/sops/cron-jobs-sop.md`.
4. **Verify conformance:** every file the scaffold wrote must exist and be non-empty (`views/` and
   `.claude/settings.json` only if you added them); `_registry.md` must list them.

## Portability note

- **Case A — the subject already has a knowledge folder:** promote it in place — scaffold the missing
  pieces (`state/`, `sources/inbox/`, `projects/`, `_registry.md`, `CLAUDE.md`, optionally `views/`)
  around the existing `canon/` + `records/` rather than starting over. `desk_scaffold.py` refuses to
  clobber, so do this by hand for an existing folder today; a promote-in-place mode is not built.
- **Case B — a subject with no home at all:** run this SOP directly.

**Deferred seam (NOT built):** an automatic promote-in-place mode for an existing knowledge folder.
`desk_scaffold.py` today only stands up a brand-new `desks/{desk}/`. Leave the seam; do the promotion by
hand until it earns automation.
