---
title: "Building and testing a skill — history"
created_at: 2026-11-10
---

# Building and testing a skill — history

Superseded wording of `system/sops/skill-building-sop.md` moves here word for word, dated, under a do-not-act note.
The skills SOP as it stood before 2026-11-10, and its own history file, are archived whole in
`system/_retired-2026-11-10/`.

- 2026-11-10 — the SOP written fresh (Enver, 2026-11-10; COMPASS P-122). Nothing superseded yet.

## 2026-11-10 - reason: approval stamped in the header; /next and /back unquoted so citation_lint does not read them as skill folders; history line names the checklist without its old path; description wording made zero-judgment (claudeops-a9). Exact text before the change:

status: draft
approved_by: "pending — Enver, via the V2 coordinator"
- **The description is the skill, from Claude's point of view.** Why: it is the only thing read when Claude Code chooses whether to
  fire a skill; get it wrong and nothing downstream matters. Change if: Claude Code changes how skills trigger.
8. **Do:** register the move-on commands (`/next`, and `/back` to redo) as real commands, and add a plain-speech
   fallback that matches the whole message ("ok next", "move on"), never a keyword.
   - **Why:** an unregistered `/next` gave "Unknown command" and never reached the hook (rig P3, OBSERVED ONCE), and a
     keyword match moved the run on 6 of 13 ordinary sentences, including "don't move on yet" (rig P3, TESTED).
   - **Expect:** typing `/next` writes a record line before the AI replies.
   - **Check:** type `/next` in a real window; a record line appears and no "Unknown command" message.
    or missing input until the person types `/back` (redo the stage that made it) or `/next` (carry on without it).
- **If `/next` says "Unknown command":** the command is not registered (Build, step 8). No record line was written, so
- 2026-11-10 — written fresh from the skill tester rig's final result, COMPASS, the Vision, the skill conformance
  checklist, and the lessons real use proved, each carried on Enver's yes; the previous skills SOP and
  `docs/skill-conformance.md` archived whole (Enver, 2026-11-10; COMPASS P-122). Older wording: the archive named in
  Pointers.
(⛔ `docs/skill-conformance.md` was archived 2026-11-10 to `system/_retired-2026-11-10/skill-conformance.ARCHIVE-2026-11-10.md`.)
