---
element: google-sheet
maturity_label: DORMANT
record_type: organism-element
altitude: index-line
---

An interactive-workflow skill (`.claude/skills/google-sheet/SKILL.md`, v1.1, updated 2026-04-13) that provides a "Google Sheet Architect" role — design, audit, or consulting on spreadsheets to high standards. Triggers on "build me a sheet", "audit my sheet", "design a spreadsheet", or mid-build sheet questions. Distinct from the delicate-data guard (which protects existing database sheets from destructive writes); this skill is the creative/design surface for building new sheets or reviewing structure.
> ~~**⚠ CORRECTED 2026-08-27, lb2-controls.md claim 69 — ⛔ `skills/google-sheet/SKILL.md` does not exist at
> that path in this clone** (`test -f` found nothing). The skill is live today as the plugin skill
> `lifehack-brain:google-sheet` (confirmed present in this session's available-skills listing) — it moved
> to the plugin plane rather than shipping as a repo-tracked `skills/` directory. The role/trigger
> description above is otherwise still accurate to how that skill behaves.~~
> ⚠ **STRUCK (BUG window, 2026-09-07): this 2026-08-27 correction is itself wrong, not the sentence it
> corrected.** Direct check this session: `.claude/skills/google-sheet/SKILL.md` exists, is tracked and
> unmodified, 376 lines, `version: 1.1`, `updated_at: 2026-04-13` — its `description:` matches this
> file's own opening sentence verbatim. Checked at HEAD `db242a783cd8a9bec22f2c182568e6d45c987bf8` — the
> SAME commit the 2026-08-27 audit itself cites, so nothing moved between the two checks; the 2026-08-27
> `test -f` claim was simply run against the wrong path. Most likely explanation: the checker tested the
> bare, un-prefixed `skills/google-sheet/SKILL.md` (the same missing-`.claude/`-prefix defect present in
> 18 other files in this same cluster) — that literal path indeed does not exist, which is consistent
> with `test -f` finding nothing — and concluded from that the skill had moved, when really only the
> CITATION was broken, not the skill. It never moved to a plugin-only plane; it remains a repo-tracked
> skill at `.claude/skills/google-sheet/SKILL.md` today.

### INTENT: bring spreadsheet-architecture judgment to any new-sheet build or structural audit, so a sheet is designed well before it becomes a database other tools depend on.

> INDEX-LINE ONLY — dormant per the 2026-07-24 usage cross-ref; expand to a full entry only if it proves load-bearing.

generated_from: .claude/skills/google-sheet/SKILL.md
