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

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-001, see drafts/skill-building-sop/applied.md

~~~~
approved_by: "Enver on 2026-11-10, via the V2 coordinator (<notes>/system/journal.md, RULED · Enver, 2026-11-10)"
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-002, see drafts/skill-building-sop/applied.md

~~~~
purpose: "Build a skill that keeps doing its job in a real, filling window, by letting code hold what must hold and showing the person every failure."
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-003, see drafts/skill-building-sop/applied.md

~~~~
- **Purpose:** a skill must do its job in the person's real window as that window fills up, not only in a short
  demo. Prose instructions fade as a session grows, so code holds the parts that must hold (the order of the stages,
  the inputs each stage needs, where the run is) and the AI does the work inside them, classifying within the choices code offers; judgment stays with the person. Every failure must be
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-004, see drafts/skill-building-sop/applied.md

~~~~
  (pausing or refusing) a planted bad input at least once (COMPASS P-5); then one real run with the person in the chair,
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-005, see drafts/skill-building-sop/applied.md

~~~~
  counts, and earlier runs are context (COMPASS P-121, P-137).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-006, see drafts/skill-building-sop/applied.md

~~~~
  `system/templates/producer-spec-template.md` (Vision, The products of the harness). Its conformance check is not
  wired; run the checklist in Build, step 2 yourself.
- Use the shared layer first: common tools live once in `shared/`, listed in `system/register/toolbox.md` (Vision,
  The Platform).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-007, see drafts/skill-building-sop/applied.md

~~~~
- Three bodies of evidence stand behind this SOP, each at its own level of confidence (COMPASS P-134):
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-008, see drafts/skill-building-sop/applied.md

~~~~
    (TESTED, OBSERVED ONCE, SUGGESTED). Its limits travel with every line that cites it (COMPASS P-41): one made-up
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-009, see drafts/skill-building-sop/applied.md

~~~~
  - **Other real-use lessons and outside practice** carried over from the archived SOP on Enver's yes (journal, RULED · Enver, 2026-11-10), each
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-010, see drafts/skill-building-sop/applied.md

~~~~
- **Code holds what must hold; the AI does the work; the person judges.** Why: prose fades as a window fills; code does not. Change
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-011, see drafts/skill-building-sop/applied.md

~~~~
  dictates (COMPASS P-119).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-012, see drafts/skill-building-sop/applied.md

~~~~
  (COMPASS P-27, P-55, P-123; Vision View 2 friction ladder).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-013, see drafts/skill-building-sop/applied.md

~~~~
  otherwise. Evidence: ruling (Vision View 1, the seam rule).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-014, see drafts/skill-building-sop/applied.md

~~~~
- **An error must never look like success.** Why: a script that exits 0 on a skip, a missing input or a swallowed error
  reads as "done". Change if: a reproduced counter-case appears. Evidence: REPRODUCED (census [F2], 166×).
- **A check shapes what the AI does, so it must reward honest work.** Why: an AI dropped true entries to pass a check
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-015, see drafts/skill-building-sop/applied.md

~~~~
  Change if: a reproduced counter-case appears. Evidence: REPRODUCED (census [F8], 70×).
- **Writing a finding down is not delivering it.** Why: the next session never looks there; name the place it must
  reach. Change if: a reproduced counter-case appears. Evidence: REPRODUCED (census [F6], 88×).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-016, see drafts/skill-building-sop/applied.md

~~~~
  carried from the archived SOP (§III.1) on Enver's yes (journal, RULED · Enver, 2026-11-10).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-017, see drafts/skill-building-sop/applied.md

~~~~
  Evidence: outside practice, carried from the archived SOP (§III.3) on Enver's yes (journal, RULED · Enver, 2026-11-10).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-018, see drafts/skill-building-sop/applied.md

~~~~
  a reproduced counter-case appears. Evidence: REPRODUCED (census [F5], 155×).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-019, see drafts/skill-building-sop/applied.md

~~~~
  counter-case appears. Evidence: REPRODUCED (census [F1], 194×).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-020, see drafts/skill-building-sop/applied.md

~~~~
  Change if: a reproduced counter-case appears. Evidence: REPRODUCED (census [F13], 35×).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-021, see drafts/skill-building-sop/applied.md

~~~~
  Change if: a reproduced counter-case appears. Evidence: REPRODUCED (census [F12], 40×).
- **The person may direct the run.** Why: working ahead because the person asked is fine (Enver, 2026-11-05, rig plan).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-022, see drafts/skill-building-sop/applied.md

~~~~
  moment it moves to a machine without them. Change if: Enver rules on whether a shared skill must work without the
  plugin. Evidence: UNSURE — carried from the archived SOP (§II.5) on Enver's yes (journal, RULED · Enver, 2026-11-10); it pulls against "use
  the shared layer, never copy it" (Open Tensions).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-023, see drafts/skill-building-sop/applied.md

~~~~
  TESTED (that machine and those flags); ruling (COMPASS P-5).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-024, see drafts/skill-building-sop/applied.md

~~~~
  carried from the archived SOP (§V.8) on Enver's yes (journal, RULED · Enver, 2026-11-10).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-025, see drafts/skill-building-sop/applied.md

~~~~
- **A skill MUST do arithmetic with code, never in the model's head.** Ruled: COMPASS P-22. Enforced by: not enforced
  in code.
- **A skill MUST NOT be deleted while it is outside git; archive it whole instead.** Ruled: COMPASS P-136. Enforced
  by: hard block (ruled; build deferred to the backlog).
- **A skill shipped in the Harness MUST NOT contain private names, window names or personal paths.** Ruled: COMPASS
  P-42, P-65. Enforced by: not enforced in code here.
- **A skill MUST NOT connect to an outside system unless the person has set that connection up; without enough
  information it says so.** Ruled: COMPASS P-94. Enforced by: not enforced in code.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-026, see drafts/skill-building-sop/applied.md

~~~~
1. **Do:** decide whether you are building a command or a skill. If it could be pasted as one prompt, it is a
   command. It is a skill the moment it is any of: several steps in an order that must hold; stateful across turns;
   leading or questioning the person; carrying something that must reliably happen.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-027, see drafts/skill-building-sop/applied.md

~~~~
     the card, runner and hooks below (archived SOP §III.1, carried on Enver's yes (journal, RULED · Enver, 2026-11-10)).
   - **Expect:** a command stops after step 3; a skill continues through step 15.
   - **Check:** write down which of the four signs, if any, applies.
2. **Do:** create the skill from the scaffold in `~/.claude/skills/<name>/`, and fill the frontmatter: `skill:`
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-028, see drafts/skill-building-sop/applied.md

~~~~
   - `command` — the person types it, it does one bounded job and ends (for example a web search).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-030, see drafts/skill-building-sop/applied.md

~~~~
     asking, with its scripts inside its own folder (COMPASS P-50). `shape:` SHOULD be one of the four above (journal, RULED · Enver,
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-031, see drafts/skill-building-sop/applied.md

~~~~
     `SKILL.md` with no description). Nothing in code checks `skill:` or `shape:`; the scaffolder stamps them at birth.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-032, see drafts/skill-building-sop/applied.md

~~~~
     description; a slightly pushy description under-triggers less than a modest one. Anything that must fire needs
     an explicit invocation or a hook (archived SOP §III.3, carried on Enver's yes (journal, RULED · Enver, 2026-11-10)).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-033, see drafts/skill-building-sop/applied.md

~~~~
     carried on Enver's yes (journal, RULED · Enver, 2026-11-10)).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-034, see drafts/skill-building-sop/applied.md

~~~~
   inputs it reads, the output it must produce, and the check on that output.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-035, see drafts/skill-building-sop/applied.md

~~~~
     (COMPASS P-119; rig P4).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-036, see drafts/skill-building-sop/applied.md

~~~~
   - **Why:** a fact kept in several files with "remember to update" drifts (census [F3], 177×).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-037, see drafts/skill-building-sop/applied.md

~~~~
      2026-11-05: "code-printed inputs line with pause on empty", `<notes>/system/journal.md`, entry "2026-11-05 | RULED · Enver | skill-system"; skill tester rig plan, Phase 3.0).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-038, see drafts/skill-building-sop/applied.md

~~~~
      match fails open on every spelling not listed (census [F7], 80×).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-039, see drafts/skill-building-sop/applied.md

~~~~
    - **Why:** an error that looks like success is built on (census [F2], 166×).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-040, see drafts/skill-building-sop/applied.md

~~~~
   - **Must / should / may:** a check that has never been seen failing SHOULD NOT be trusted (COMPASS P-5).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-041, see drafts/skill-building-sop/applied.md

~~~~
3. **Do:** prove the hooks fired: plant a control token a hook must write, and count failures to start from the raw
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-042, see drafts/skill-building-sop/applied.md

~~~~
     in a way it could not if broken (COMPASS P-5).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-043, see drafts/skill-building-sop/applied.md

~~~~
     containment silently (skill tester rig plan, 3.0.4); the hash matches before and after.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-044, see drafts/skill-building-sop/applied.md

~~~~
   by the model's window, worked out in code (COMPASS P-22).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-045, see drafts/skill-building-sop/applied.md

~~~~
   - **Why:** the stand-in's choices are not the person's (rig P5 limits), and private text must not end up in test
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-046, see drafts/skill-building-sop/applied.md

~~~~
   - **Why:** a helper's account of its own work is not evidence (census [F8], 70×).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-047, see drafts/skill-building-sop/applied.md

~~~~
    - **Must / should / may:** a result MUST keep its caveats wherever it is retold (COMPASS P-41).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-048, see drafts/skill-building-sop/applied.md

~~~~
- **To undo:** a skill's runner, hooks and card are files; revert them through git, or archive them whole (Rules).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-049, see drafts/skill-building-sop/applied.md

~~~~
  ruling; a change would add a new rule or a new hard block (Vision, the amendment clause); where a change goes is
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-050, see drafts/skill-building-sop/applied.md

~~~~
  Proof: census [F7], 80×; rig P3.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-051, see drafts/skill-building-sop/applied.md

~~~~
  census [F3], 177×.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-052, see drafts/skill-building-sop/applied.md

~~~~
  [F10], 50×.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-053, see drafts/skill-building-sop/applied.md

~~~~
  ruling, and a skill carries the machinery the rig's test dictates (COMPASS P-119). Side B protects the person's time:
  friction goes lightest first and a layer that never changes an outcome is dropped (COMPASS P-27, P-123). The rig
  never measured weaker levels, so it cannot say which layers a skill can drop. Status: open — surfaced to Enver, not
  resolved here.
- **A travelling skill versus the shared layer.** Side A: a skill shared with someone without the plugin must carry
  its own parts. Side B: shared tools live once and are never copied (Vision, The Platform). Status: open — UNSURE since
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-054, see drafts/skill-building-sop/applied.md

~~~~
- **Rulings behind this SOP:** COMPASS P-5, P-22, P-27, P-41, P-42, P-50, P-55, P-65, P-94, P-112, P-119, P-121,
  P-122, P-123, P-134, P-136, P-137; Enver's rig rulings of 2026-11-05 (the skill tester rig plan and the skill-system
  journal); Enver's rulings of 2026-11-10 on the proven lessons, the five carried items and the four shapes (`<notes>/system/journal.md`, entry
  "2026-11-10 | RULED · Enver | skill-system").
- **Vision sections it serves:** The products of the harness (the scaffold); The Platform; View 1 Division of Labor
  and the seam rule; View 2 friction ladder; Document hygiene; the amendment clause and the no-precedence rule.
- **Evidence:** the skill tester rig's findings record, 2026-11-05 (`rig-findings-2026-11`, kept in the project's
  notes, not shipped): rig P1-P11 and §1-§8. That record's own status is a draft awaiting a canon-files run; Enver
  ruled on 2026-11-10 that this SOP is a write-up from it, with no canon-files run (V2 plan, step 7). The failure census
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-055, see drafts/skill-building-sop/applied.md

~~~~
- **Words used here:** the Vision's Ubiquitous Language (skill, scaffold, seam), plus:
  - **command** — one prompt behind a slash command: one shot, no steps that must hold, no state across turns.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-056, see drafts/skill-building-sop/applied.md

~~~~
  - **code word** — a fresh one-time word each stage's handover gives the AI, which the AI must give back so code knows
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-057, see drafts/skill-building-sop/applied.md

~~~~
  - **rig P1-P11** — the numbered findings of the skill tester rig; not COMPASS entries.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-058, see drafts/skill-building-sop/applied.md

~~~~
- 2026-11-10 — written fresh from the skill tester rig's final result, COMPASS, the Vision, the skill conformance
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: skill-building-sop edit-pass hunk hunk-059, see drafts/skill-building-sop/applied.md

~~~~
  the old skill conformance checklist archived whole (Enver, 2026-11-10; COMPASS P-122). Older wording: the archive named in
~~~~
