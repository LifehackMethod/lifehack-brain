---
title: "Desk-building SOP: history log"
what: "Retired and moved text from system/sops/desk-building-sop.md, kept verbatim and dated so nothing is lost. Never read in normal use."
read_in_normal_use: false
base_commit: "fbb23e9  (git log -1 --format=%h -- system/sops/desk-building-sop.md, on branch V2)"
base_file: "system/sops/desk-building-sop.md, 101 lines at that commit"
created: 2026-11-02
status: "V2 draft, to be merged with the SOP"
---

# Desk-building SOP: history log

Each entry below is one passage removed or reworded in the SOP on 2026-11-02: CUT (retired), MOVE (change note or narrative, history not instruction) or FIX (original wording of a line that was reworded). Line ranges are the line numbers in the base (see `base_file` above). Entries are in original line order. The original is copied word for word inside each fenced block. Decision IDs (2a to 2f, Group 3 item n, Group 4 item n) refer to `desk-building-sop--DECISIONS.md` and the review report it answers.

Entries whose body held private material show one line instead of the verbatim block; those originals are kept in the operator's private notes.

## 2026-11-02 · FIX · line 8 · front-matter updated_at

- Date: 2026-11-02
- Action: FIX
- Reason: Group 4 item 1 (applied per the operator's auto-apply rule, DECISIONS 2026-11-02): the date had not moved since 2026-08-15 although git shows edits on 2026-10-29 and 2026-10-30; now the date of this cleanup edit.
- Original lines: 8

```
updated_at: 2026-08-15
```

## 2026-11-02 · CUT · line 17 · opening box, 'PORTED from' line naming the private source repository

- Date: 2026-11-02
- Action: CUT
- Reason: Decision 2a (Group 4 item 2, the one cut): the line names a private repository that only the operator can open. Its non-private provenance, "(migration F9.6, "THE DESK" … "PLANE")", is history, not instruction (Group 4 item 3); the line's continuation is in the next entry.
- Original lines: 17

(verbatim original moved to the operator's private notes, 2026-11-02, because it is private)

## 2026-11-02 · FIX · line 18 · opening box, end of the provenance note and the quote's attribution

- Date: 2026-11-02
- Action: FIX
- Reason: Group 4 item 3: the end of the migration note ('PLANE").') and the attribution in its original form, "⚖ The operator, `authority: user`, verbatim:", move here word for word; the page keeps a plain attribution, "The operator, verbatim:"; the quote itself, the only "why" for the whole page, stays in the SOP unchanged.
- Original lines: 18

```
> PLANE"). ⚖ The operator, `authority: user`, verbatim: *"the new system should have a template and a way of
```

## 2026-11-02 · FIX · line 23 · opening box, 'No other file in this repo re-specifies it'

- Date: 2026-11-02
- Action: FIX
- Reason: Group 4 item 4: "No other file in this repo re-specifies it" becomes "where restated (for example the scaffold's own folder list), copies must agree with this page" (it is not true today: `desk_scaffold.py` restates the list). The first sentence, "This page is the ONE canonical statement of the full-desk shape.", stays (Group 4 item 3).
- Original lines: 23

```
> **This page is the ONE canonical statement of the full-desk shape.** No other file in this repo
```

## 2026-11-02 · MOVE · lines 24-25 · opening box, the four-drifting-statements story (start)

- Date: 2026-11-02
- Action: MOVE
- Reason: Group 4 items 3 and 4: the story of how the old system's four shape statements drifted is history, not instruction; "re-specifies it … rather than restating the list" is replaced by the "copies must agree" wording.
- Original lines: 24-25

```
> re-specifies it — anywhere else the shape is mentioned, it points here rather than restating the
> list, which is the exact drift this port closed: the donor carried FOUR independent statements of
```

## 2026-11-02 · CUT · line 26 · opening box, the line naming the private schema brief

- Date: 2026-11-02
- Action: CUT
- Reason: Decision 2a (Group 4 item 2, the one cut): the line names a private file that only the operator can open. The rest of the story is kept word for word in the entries before and after this one (Group 4 item 3).
- Original lines: 26

(verbatim original moved to the operator's private notes, 2026-11-02, because it is private)

## 2026-11-02 · MOVE · lines 27-30 · opening box, the four-drifting-statements story (end) and the 2026-08-15 count

- Date: 2026-11-02
- Action: MOVE
- Reason: Group 4 item 3: the story and its 2026-08-15 measurement are history, not instruction. What the count decided stays in the shape list: `projects/` is in the list, and `views/` stays optional.
- Original lines: 27-30

```
> conformance checks, and `desk_scaffold.py`'s own folder list) that had quietly gone out of sync with
> each other and with the 9 real desks actually in use. Measured against those 9 real desks on
> 2026-08-15: `projects/` exists in 8 of 9 and was in **none** of the four donor statements — added
> below. `views/` exists in 7 of 9 — real, but not universal, so it stays **optional**, never assumed.
```

## 2026-11-02 · FIX · line 50 · 'The shape' heading, 'nowhere else in this repo restates this list'

- Date: 2026-11-02
- Action: FIX
- Reason: Group 4 item 4: "nowhere else in this repo restates this list" becomes "where restated, for example the scaffold's own folder list, copies must agree with this page". The heading still begins "The shape", which `desk_scaffold.py` cites.
- Original lines: 50

```
## The shape (canonical — nowhere else in this repo restates this list)
```

## 2026-11-02 · MOVE · lines 60-62 · shape list, the dated notes on `projects/` and `views/`

- Date: 2026-11-02
- Action: MOVE
- Reason: Group 3 item 1 (approved as called): "per-project subfolders (brief.md · canon.md · records/)" and "OPTIONAL — not universal; opt-in only" stay; the 2026-08-15 date and the counts move here word for word. The same counts also stay in `desk_scaffold.py`'s own header, so the evidence for `views/` being optional is kept in two places. Re-counted 2026-10-31: both still held.
- Original lines: 60-62

```
├── projects/             per-project subfolders (brief.md · canon.md · records/) — ⭐ ADDED 2026-08-15,
│                         measured in 8 of 9 real desks, absent from every prior shape doc
├── views/                OPTIONAL — measured in 7 of 9 real desks, not universal; opt-in only
```

## 2026-11-02 · FIX · line 73 · step 1, scaffold command path

- Date: 2026-11-02
- Action: FIX
- Reason: Decision 2f (item 2.3): the command only worked from inside the plugin folder; it now starts with `<plugin>/`, matching the line above it (base line 71).
- Original lines: 73

```
   python3 system/tools/cowork-ingest/desk_scaffold.py \
```

## 2026-11-02 · FIX · lines 77-78 · step 1, the canon-guard claim

- Date: 2026-11-02
- Action: FIX
- Reason: Decision 2f (item 2.2): ", so a `guard_canon_write`-class hook accepts them" deleted. The guard's own header says the `authority: user` check was deliberately not carried over (anyone can type the label) and that it now checks size only; that removal is marked pending the owner's confirmation in the guard, a separate question. "canon stubs carry `authority: user`" is still true and stays. Line 78's remaining words were re-wrapped onto the next line; none were dropped.
- Original lines: 77-78

```
   Creates the full conformant shape + stub files (canon stubs carry `authority: user`, so a
   `guard_canon_write`-class hook accepts them). `views/` is opt-in — pass `--views yes` only if this
```

## 2026-11-02 · FIX · line 82 · step 2, the paste instruction

- Date: 2026-11-02
- Action: FIX
- Reason: Decision 2f (item 2.1): pasting the printed block under `desks:` without replacing the `[]` the file ships with leaves the list unreadable (tested 2026-10-31: "expected <block end>, but found '<block sequence start>'"). Adds "(replacing the `[]` the file ships with)". Where the desk list lives is on hold (decision 2e); nothing about moving it was written.
- Original lines: 82

```
   into `system/desk-registry.yaml` under `desks:`. Deliberately not auto-edited — the registry is read ⛔ since moved to the person's notes folder (b2e5dc5, 2026-11-02)
```

## 2026-11-02 · FIX · lines 85-87 · step 3, wiring to automation

- Date: 2026-11-02
- Action: FIX
- Reason: Decision 2c (item 1.4), with the pointer: "ONLY if the desk needs it" kept; scheduled jobs are added as rows per `system/sops/cron-jobs-sop.md`; the three settings are left at `null` in the registry block "(no tool reads them today)". "a pure knowledge desk (no cron) … is done at step 2" is kept. A code search on 2026-10-31 found no reader of `health_producer`, `pulse_slot` or `status_tile_path` outside comments and docs; the names come from the old scheduler ("pulse").
- Original lines: 85-87

```
3. **Wire to automation ONLY if the desk needs it** — a pure knowledge desk (no cron) leaves
   `health_producer` / `pulse_slot` / `status_tile_path` = `null` in the registry block and is done at
   step 2.
```

## 2026-11-02 · FIX · lines 88-89 · step 4, the conformance check

- Date: 2026-11-02
- Action: FIX
- Reason: Decision 2d (item 1.3): as written, a desk the script had just made failed the check, because "The shape" includes `views/` (optional) and `.claude/settings.json` (added by hand), and the script leaves three folders empty. Reworded to match what the scaffold writes. The scaffold's desk-index fix (code bug 3) goes to the coordinator, not here.
- Original lines: 88-89

```
4. **Verify conformance:** every file in "The shape" above must exist and be non-empty; `_registry.md`
   must list them.
```

## 2026-11-02 — step 2 and step 3 after the desk list moved (b2e5dc5)

Draft wording replaced (draft text; the base text of step 2 is in the entry for decision 2f above):

```
2. **Register in the keystone (BY HAND — it is a code file):** paste the block the scaffolder prints
   into `system/desk-registry.yaml` under `desks:` (replacing the `[]` the file ships with). ⛔ since moved to the person's notes folder (b2e5dc5, 2026-11-02)
   Deliberately not auto-edited — the registry is read
   by every organ that needs to enumerate desks (e.g. `backlog_groom.py`'s `load_registry()`), and
   hand-maintenance keeps adding a desk a conscious act.
   A desk's scheduled jobs are added as rows per `system/sops/cron-jobs-sop.md`; leave `health_producer`, `pulse_slot` and `status_tile_path` at
   `null` in the registry block (no tool reads them today).
```

- Action: REWORDED.
- Reason: Decision 2e (Enver, 2026-11-02, relayed by the coordinator): the desk list moved out of the plugin into each person's notes, `<notes>/desks/desk-registry.yaml`, read through `shared/desk_list.py`; the plugin ships none (commit b2e5dc5). The same commit removed `health_producer`, `pulse_slot` and `status_tile_path`, so the "leave them at null" clause no longer applies. "BY HAND" and "Deliberately not auto-edited … a conscious act" are kept.
