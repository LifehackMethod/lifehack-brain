---
title: Circulatory System
status: approved
approved_by: "Enver on 2026-11-16, round four's 'land it'"
last_reviewed: 2026-11-16
purpose: Say how knowledge gets from one session to the next and climbs over time — which skill hands what to which, through which surfaces, and what checks each hand-over — so a session that starts with nothing can carry on the work without losing what was learned.
read_when: Before changing /read, /save, /checkin, /project-manager, /orient, /autoplan or /build, or the hooks between them; when a new session redid finished work, missed a decision, or walked into a known dead end; when deciding how a finding climbs from a session toward canon.
history: "canon/circulatory-system-sop.history.md"
---

## Read This First

- **Purpose:** every session starts with no memory of the last one. What a project learned survives only if it is written to a surface the next session actually opens, in words a stranger can act on. This SOP describes that loop (the circulatory system: the skills that carry a project's knowledge across the session handoff and roll it up over time) so that anyone changing one part keeps the hand-overs between the parts intact. Most slips this system has recorded were reasoning and handoff slips that no hook could catch (a census of 2026-10-29), which is why much of this loop is principle, and why each piece of code that does hold a step is named in References at the end. Nothing here is a must: by Enver's ruling of 2026-11-15, musts live only at the top altitude, as architecture, and at this altitude there is only code and the conformance friction it creates; the steps below are how-to.
- **Scope of the description:** the harness repo on its `V2` branch, read on 2026-11-15.
- **Use it when:** you change any of the carry skills — `/read`, `/save`, `/checkin`, `/project-manager`, `/orient`, `/autoplan`, `/build` — or a hook they lean on; a new session did the wrong work, re-suggested a dead end, or missed a decision; you are deciding how a finding moves from a session toward canon.
- **Don't use it when:** deciding which folder or file a saved thing lands in → `canon/data-layout.md`. Deciding which level a line deserves, or whether it is canon at all → `canon/knowledge-altitude.md`. Handing work between windows that are both open → `canon/coordinating-windows-sop.md`. What a session receives without asking, including the project line → `canon/context-injection-sop.md`. Building any one of these skills → `canon/skill-building-sop.md`.
- **Covers:** the order the carry skills run in, what each hands to the next, the surfaces they share (the brief, the scratchpad, the journal, the plan, the session handoff), the flags that keep a project in view, and the climb from a session's notes to canon. **Doesn't cover:** the paths themselves, the canon admission test, or helper model choice (`canon/helpers-and-model-routing-sop.md`).
- **`/autoplan` carries this banner in its own file, quoted as written:** "UNDER CONSTRUCTION (Enver, 2026-10-31): autoplan is under construction and not working well; don't rely on it." (`.claude/skills/autoplan/SKILL.md:17`).
- **Rebuild ruling (Enver, 2026-10-31):** `/save`, `/checkin`, `/build` and the plan tools are rebuilt together; the board and gauge checks are kept, and the self-stamping start/stamp/report steps of the step ledgers are dropped. The `/build` runner is run once, live, before its fate is decided.
- **How this SOP changes:** only through Enver's ruling; superseded text moves to the archive named in the header.
- **Which situation are you in?**
  - Starting or picking up a project → The Procedure, "Start or pick up a project".
  - Mid-session, something is worth keeping → "Keep something during the session".
  - Ending a session → "Close a session".
  - Ending, pausing or splitting a project → "End, pause or split a project".
  - A finding might deserve a higher shelf → "Move a finding up".
  - Turning a goal into built work → "Plan and build".

## Desired Outcome

A session that opens cold can read one short session handoff (the message `/save` emits at close; passing a live role between windows is a role handoff, `canon/coordinating-windows-sop.md`'s), arm its project, read the brief and, when there is one, the plan, and know where the work stands, what is next, and what not to retry — without the person re-explaining, and without redoing finished work. As built, the loop runs like this:

- **The brief** (the project's one living document, overwritten in place) is the spine. `/project-manager` creates it, confirms its frame with the person, registers the project, and arms the flags (`.claude/skills/project-manager/SKILL.md:102-137`). Its frame (desired outcome, definition of done) belongs to the person. The person rewrites it freely as the work moves; a session about to change it meets a street sign, seen only by the session: "This is the person's goal. Did they ask for this change in their own words? If yes, go ahead." — no block and no popup (see References). `/checkin` flags drift in it (`.claude/skills/checkin/SKILL.md:55-58`).
- **The flags** keep the project in view after the skill text is gone: `system/hooks/pm_flag.sh` (which project) and `system/hooks/plan_flag.sh` (which plan) are armed by `/project-manager` (or the two arm lines a session handoff names) and refreshed by `/checkin`; a hook prints the project line once per arming (what it prints, and when, is `canon/context-injection-sop.md`'s). Once armed, the project and plan are locked for the life of the window; the lock, its refusal and how it changes are `canon/coordinating-windows-sop.md`'s.
- **The scratchpad** (the brief's `## 7. SCRATCHPAD` section, a capture surface) takes notes as the session goes, appended from the main window; two hooks prompt for it, and what they inject is `canon/context-injection-sop.md`'s. This SOP owns the pad's life: capture, then compaction by `pad_archive.py`, which archives the pad beside the brief and proves it landed before it clears anything. **The story log** (the brief's append-only `## 4. STORY LOG` section) holds each decision with its outcome; an overtaken entry is tagged `superseded-by`, not removed (`.claude/skills/checkin/SKILL.md:48-51`).
- **`/save` at session close** first runs `/checkin` (`.claude/skills/save/phases/session-close.md:15-40`), which compacts the pad before it compares, reconciles the desired outcome against the brief and what happened, asks once, writes the approved edits, and then has a blind reader — a read-only helper on the medium tier that has not seen the session — try the fixed brief (`.claude/skills/checkin/phases/3-propose.md:214-242`; the tier is `canon/helpers-and-model-routing-sop.md`'s). `/save` then extracts, tiers and files the session's output, writes the journal before the brief, sweeps debt in and finished items out, and ends with a session handoff of at most 200 words (`.claude/skills/save/phases/standard-steps.md:345-437`).
- **The journal** (the append-only log of what happened and why) is the backstop that makes overwriting the brief safe — the reason is `canon/data-layout.md` § The journal (`canon/data-layout.md:195-197`). `/save`, `/checkin` and `/project-manager` write the journal before the brief (`.claude/skills/save/SKILL.md:61-62`, `.claude/skills/project-manager/SKILL.md:92-96`), and a check holds that order (see References); the journal's append, slice and rotate live in `journal.py`.
- **`/read`** and **`/orient`** bring it back: `/read` loads the armed brief first and leads with ruled-out lines and the story log (`.claude/skills/read/SKILL.md:42-58`); `/orient` restates the three altitudes and the near past, present and future, and says so when a part has nothing behind it (`.claude/skills/orient/SKILL.md:22-26`).
- **The plan** is one file per project, amended by `/autoplan`; a build window's own plan sits under the project's as a sub-plan (`canon/coordinating-windows-sop.md` says how). A plan file is retired by renaming, not removed, and code refuses its deletion (see References). `/build`'s runner — not the model — runs every Verify and writes the record (`.claude/skills/build/SKILL.md:61-74`).
- **A student's notes canon** (the canon files in `canon/data-layout.md`'s path table) is written only on the person's explicit yes: through `/save`'s canon pause (a conflict scan, a framed panel and the yes, `.claude/skills/save/SKILL.md:46-60`), or through `/ingest`'s placement preview (`.claude/skills/ingest/phases/4-place.md:89-95`). The harness's own `canon/` folders enter only after a full canon-files run (Enver, 2026-11-14).

**How to check:** a fresh window given only the last handoff names the next action and the ruled-out paths without asking; `/checkin`'s receipt shows its closed verdicts from tool exit codes; the tests pass — `system/hooks/tests/test_pm_lock_override.sh`, `test_plan_lock_override.sh`, `test_checkin_save_seam.sh`, `test_guard_checkin_needs_project.sh`, `system/tools/test_journal.py`, `system/tools/save/test_pad_archive.py`, `test_save_step_ledger.py`, `system/tools/checkin/test_board_check.py`, `test_gauge_check.py`, `shared/test_registry.py`.

## Before You Start

- `canon/data-layout.md` — where the brief, journal, records, plans and debt ledger live.
- `canon/knowledge-altitude.md` — what canon is, and the level a line belongs at.
- `canon/context-injection-sop.md` — the per-turn and session-start lines this loop leans on.
- `shared/registry.py` resolves a project's slug to its folder; `shared/brain_root.py` resolves where the notes live. Every carry skill starts from both.

## Principles

- **Writing a finding down is storage, not delivery: name the surface the next session reads first.** Why: retrieval is harder than storage — a cold session that does not know to ask will not load a finding however well it is filed (`canon/canonical-principles-sop.md:836-838`); pointers get written and nothing makes the next session read them (`canon/canonical-principles-sop.md:1091-1092`). Change if: a stored-only finding is seen picked up by later sessions that were not pointed at it, across several projects. Evidence: OBSERVED — `canon/canonical-principles-sop.md:1334` (derived 2026-09-07).
- **An injected pointer carries a pickup where a pointer stored in a brief is the heavy path.** Why: it is why a hook prints the project line and why the session handoff names the brief and plan by path; the old-and-new-window dialogue that also held is `canon/coordinating-windows-sop.md`'s. Change if: a stored pointer alone is seen carrying a pickup as well as an injected one. Evidence: OBSERVED — `canon/canonical-principles-sop.md:1094-1095` (routed by Enver, 2026-09-06).
- **Hand the next session current state as files, not history; full context still applies to merged work.** Why: a pickup reads the brief and plan in its first action, so the handoff carries only what they cannot hold (`.claude/skills/save/phases/standard-steps.md:384-397`); canon keeps full context as the safe default for a helper and asks for judgment (`canon/canonical-principles-sop.md:687-688`). Change if: a history-style handoff is measured carrying a pickup better than state files. Evidence: CANDIDATE — `canon/canonical-principles-sop.md:696` (2026-10-28).
- **Write every carried line for a stateless reader: could a session that has not seen this conversation act on it alone?** Why: the next session starts from nothing and the person holds less than the page assumes. Change if: a sealed zero-state reader is shown acting correctly on ordinary handoff text without this question being asked. Evidence: CANDIDATE — `canon/canonical-principles-sop.md:1355` (Enver's ruling 2026-09-06; canon notes only canon's write speed bump asks it).
- **Reasons carry across a handoff; bare facts do not.** Why: a blind session given only a brief and plan handled unwritten situations from the reasons, but missed definitions, qualifiers and brief-versus-plan contradictions that were compressed out. Change if: a blind pickup is shown recovering compressed-out qualifiers from bare facts. Evidence: OBSERVED — a blind pickup test, 2026-11-03.
- **The writer cannot judge their own handoff; a different reader, or the source, is the detector.** Why: two sessions can hold the same wrong belief (`canon/canonical-principles-sop.md:854`); errors were caught by going to the source, not by re-reading one's own output, and a quiz written by the brief's author finds only the gaps it thought to ask about — so `/checkin` has a blind reader try the fixed brief (its "no" has been seen on good input, `canon/canonical-principles-sop.md:1678`, 2026-09-07, so a "no" is a reason to look, not a verdict). Change if: self-review is measured catching handoff gaps a blind reader misses. Evidence: OBSERVED — `canon/canonical-principles-sop.md:854`; a session-close review, 2026-09-15.
- **Dead ends stay one line each in the brief, with a pointer to the story.** Why: what failed is what stops a new session walking into it twice, which is why `/read` leads with the ruled-out lines (`.claude/skills/read/SKILL.md:52-57`) and why a compaction keeps them. Change if: sessions are seen avoiding known dead ends with the ruled-out lines removed. Evidence: OBSERVED — a brief-and-plan audit, 2026-11-14.
- **A plan that only collects ticks grows more confident and less accurate at once; each check-in leaves the record sharper than it found it.** Why: a finding written nowhere and a finding not made look the same three sessions later (`canon/canonical-principles-sop.md:675-677`), which is why `/checkin` exists (`.claude/skills/checkin/SKILL.md:23-28`) and why a task leaves the plan only when code re-runs its Verify (`system/tools/plan_retire.py:2-6`). Change if: a tick-only plan is shown staying accurate over months with no re-check. Evidence: OBSERVED — `canon/canonical-principles-sop.md:675-677`.
- **One surface answers "where are we", a different one answers "what do I do next", and code checks both.** Why: a session did the wrong work right after the status surface was verified clean, because an open-questions board still queued a task the plan had marked done; the next day the status block named work the plan did not hold, and a build improvised (`system/tools/checkin/board_check.py:5-25`). Change if: a brief with one checked surface is shown handing over correctly across several sessions. Evidence: OBSERVED — `system/tools/checkin/board_check.py:5-25` (2026-08-07).
- **Code holds the order of the steps, the shape of a section and the proof between them; the model does the work inside each step.** Why: a step held only by words is the one that gets skipped, and one-step-at-a-time with a code check held in 20 runs of one test harness (zero failures in 20 rules out only rates above about 14%; not yet seen over weeks of real use) (`canon/canonical-principles-sop.md:1352`); competing "where we are" blocks told in prose not to pile up piled up until the gauge check stopped them (`system/tools/checkin/board_check.py:30-33`), and that check accepts only the one legal shape because a list of known-bad shapes would rot (`system/tools/checkin/gauge_check.py:14-18`). Change if: a words-only step or section is shown holding as reliably as a tool-backed one across blind runs. Evidence: OBSERVED — `canon/canonical-principles-sop.md:1352` (2026-10-28); `system/tools/checkin/board_check.py:30-33`.
- **A step's own stamp proves it was reached, not that it was done well; a reopen condition nothing logs is a wish.** Why: a self-written done mark hides a skip — a mandatory `/save` step was once stamped from the session's own summary instead of the transcript it exists to read — and a condition that waits on an event no tool records cannot fire, which is why the step ledger exists at all (`system/tools/save/save_step_ledger.py:5-8`, `system/tools/save/save_step_ledger.py:19-21`). Change if: a stamp is tied to output that a different reader checks. Evidence: OBSERVED — `system/tools/save/save_step_ledger.py:5-8`, `system/tools/save/save_step_ledger.py:19-21`; `canon/canonical-principles-sop.md:1026-1028` (a self-written record found incomplete); a session-close review, 2026-09-15.
- **A marker advances only on positive proof of the work, not on a success exit code alone.** Why: a success exit code has advanced a marker over a failed run; the build runner is written to compare the Verify's content and trust no exit code alone (`.claude/skills/build/scripts/build_run.sh:10-13`). Change if: a marker driven by exit codes alone is shown matching real outcomes across many runs. Evidence: OBSERVED — `canon/canonical-principles-sop.md:591` (2026-10-28).
- **Derive a shared value or build the diff that compares the copies; "remember to update the copy" is not a mechanism.** Why: the project flag's lifetime was raised in one file while a hook kept its own copy at the old value, so the raise did not take effect; the hook now asks the flag script for the number (`system/hooks/pm_flag.sh:53-59`). Change if: hand-kept copies are shown staying in step across releases. Evidence: REPRODUCED — `canon/canonical-principles-sop.md:1040-1042`.
- **A number travels with the command that produced it, and with its counting method.** Why: a figure quoted and not recomputed goes stale in a hand-off, and two counts of one plan minutes apart were both right because they counted different things. Change if: quoted figures without their command are measured staying correct across hand-offs. Evidence: CANDIDATE — `canon/canonical-principles-sop.md:1337`; level kept by Enver's ruling, 2026-09-08 (`canon/canonical-principles-sop.md:1634`).
- **Prefer the live source over a dated claim; between written sources of equal authority, prefer the more recent, with the exceptions canon §7.4 lists.** Why: a claim whose date was dropped in retelling gets acted on beside a live source that contradicts it (`canon/canonical-principles-sop.md:1357`); §7.4's exceptions cover a person's ruling, an undated source and a restatement (`canon/canonical-principles-sop.md:867-869`). Change if: an experiment shows dated claims acted on correctly without re-deriving. Evidence: CANDIDATE — `canon/canonical-principles-sop.md:1357` (canon's own grade, 2026-09-07).
- **Record the test you used, not only the verdict.** Why: a saved verdict cannot referee a later disagreement; the reasoning carries to the next case. Change if: verdict-only records are shown settling later disputes as well. Evidence: OBSERVED — `canon/canonical-principles-sop.md:873-876`.
- **A finding climbs by evidence from different builds: two receipts from one build are not reproduction.** Why: this is the bar between a session's note and a reproduced line, and a session once proposed the jump on one build's receipts. Change if: receipts from one build are shown predicting other builds as reliably as receipts from several builds do. Evidence: OBSERVED — `canon/canonical-principles-sop.md:1051-1053` (2026-09-05).
- **Plan ahead in full, then test and validate at every gate.** Why: a plan that runs unattended needs every phase in detail, and drift is caught at the gate by a check that re-runs. Change if: a gated plan is shown drifting past its gates, or an outline-only plan running unattended as well. Evidence: REFINED — `canon/canonical-principles-sop.md:912-917` (Enver's ruling, 2026-09-05).
- **Read the record before writing a plan or a spec; a claim in a plan is not evidence.** Why: a planner's rebuild spec written from memory left out the project's origin, reopened a rejected option, and skipped a field test on disk; and a plan's sizes collapsed when measured. A passing field test can show the spec was the wrong target. Change if: specs written from memory are measured matching the record. Evidence: OBSERVED — a migration handoff, 2026-08-07, and a spec review, 2026-09-15; related: `canon/canonical-principles-sop.md:1333` (the parent mode, CANDIDATE there).
- **Fix every site, not the first one.** Why: a line corrected in one place and left stale in another gets obeyed in its stale form, and a stale scope line once outranked a correct one a few lines below it. Change if: a single-site fix is shown sufficient where several copies exist. Evidence: OBSERVED — a migration handoff, 2026-08-07.
- **A plan quotes the person's ruling in their words, and the scope does not narrow without their yes.** Why: an invented label once moved work out of a round without the person's ruling, and the round was called done against the plan instead of against what they asked for. A quote copied from another window keeps its fidelity caveat: faithful in substance is not a transcript. Change if: paraphrased rulings are measured carrying scope as faithfully as quoted ones. Evidence: OBSERVED — a round's scope cut, 2026-11-13, and a session-close review, 2026-09-15.
- **The frame and the status block are the person's; a session changes them on the person's own words.** Why: a session wrote a status block directly on top of three contradicting ones, and the person later approved a frame they had not read (`.claude/skills/checkin/SKILL.md:55-80`); the person also rewrites the goal and status often, so the friction is a sign for the session, not a stop for the person. Change if: machine-written frames or status blocks are seen matching what the person meant across several projects without their reading them first. Evidence: OBSERVED — `.claude/skills/checkin/SKILL.md:64-80`.
- **The scratchpad is appended from the main window, append-only.** Why: a delegated pad writer truncated a project brief to zero bytes, one of several such losses, and the spawn was removed on the operator's ruling of 2026-09-04 (`system/hooks/scratch_capture_gate.sh:211-215`). Change if: a delegated append is shown unable to truncate, under a guard that sizes the write. Evidence: OBSERVED — `system/hooks/scratch_capture_gate.sh:211-215` (2026-09-04).
- **One living plan file per project; plan mode is not used to hold it.** Why: plan mode mints a new file per session, and a census found most plan files belonged to no project (`.claude/skills/autoplan/SKILL.md:33-37`). The one exception is a build window's sub-plan under the project's plan, described in `canon/coordinating-windows-sop.md`. Change if: plan mode gains an amend-in-place option. Evidence: OBSERVED — `.claude/skills/autoplan/SKILL.md:33-37` (the census there is undated).
- **Roll-ups stay low-confidence until a person checks them.** Why: the diary's weekly-and-longer roll-ups are machine recaps, written as unverified drafts that a person's check-in stamps; promotion from them is held for a person (`system/tools/planning-diary-rollup.py:4-10`; Enver's ruling). Change if: unreviewed roll-ups are shown carrying facts forward without error across several periods. Evidence: CANDIDATE — `system/tools/planning-diary-rollup.py:4-10`; nothing has been watched holding yet.
- **An edge held only by the model's compliance is a gap, not a guarantee.** Why: `/read` skipping canon already loaded at session start (what loads is `canon/context-injection-sop.md`'s), `/read` and the canon conflict scan walking the same scope, and plan-fork prevention since its guard was retired on 2026-07-15 rest on compliance (`system/organism/manual.md:530`, `system/organism/manual.md:566`, `system/organism/manual.md:846`). Change if: a mechanism is built for one of them, or one is shown holding across blind runs. Evidence: OBSERVED — `system/organism/manual.md:846` (2026-07-15).

## The Procedure

### Start or pick up a project

1. **Do:** for new work, run `/project-manager`; for a cold pickup, run the two arm lines and read what the last session handoff names.
   - **Why:** the session handoff hands the new window its mode instead of letting it guess (`.claude/skills/save/phases/standard-steps.md:398-402`).
   - **Expect:** `/project-manager` confirms the frame with the person before the brief counts as authoritative (`.claude/skills/project-manager/SKILL.md:139-146`); a pickup reads the brief's status block and the plan's current phase, then stops and reports. A project can also be born mid-session through `/save`: its frame is then written as best guesses marked `INFERRED`, the frame marked unconfirmed, and the slots put to the person in one round, not written as settled fact (`.claude/skills/save/phases/standard-steps.md:293-300`).
2. **Do:** arm the project and plan flags.
   - **Check:** `pm_flag.sh status` prints the brief's path. A refused arm, and how the project legitimately changes, are `canon/coordinating-windows-sop.md`'s.
3. **Do:** run `/read` when the pickup needs more than the brief.
   - **Expect:** the brief loads first, ruled-out lines and the story log lead, then on-branch canon and search results with trust labels; a second `/read` loads only what is new; the close line names the paths loaded (`.claude/skills/read/SKILL.md:120-140`, `:327-334`).
4. **Do:** run `/orient` when the person has lost the thread; it changes nothing.

### End, pause or split a project

1. **Do:** set the project's status in its registry row — `active`, `paused`, `complete`, or `split` naming the new slugs — through `shared/registry.py` (`.claude/skills/project-manager/SKILL.md:70-76`).
2. **Do:** clear the project flag when the person says the project is done; a locked window refuses the clear, and closing the window is the ordinary answer (`.claude/skills/project-manager/SKILL.md:123-124`).
3. **Do:** run a session close first, so the brief, journal and session handoff carry the final state.

### Keep something during the session

1. **Do:** put notes worth keeping into the scratchpad of the armed brief.
   - **Expect:** with no project armed, ask the person where it goes; the hook text that says so is `canon/context-injection-sop.md`'s.
2. **Do:** when the end-of-turn gate bounces a turn at a checkpoint, append what is missing from this window.
   - **Check:** the appended lines sit under `## 7. SCRATCHPAD`; nothing was overwritten.
3. **Do:** for one artifact, run a mid-session `/save`; it does not run `/checkin` (`.claude/skills/save/SKILL.md:117`).
   - **Expect:** non-canon items are written at once with a receipt; a canon candidate stops for the person's yes.

### Close a session

1. **Do:** run `/save` bare (session close).
   - **Expect:** `/checkin` runs first; with no project armed it is refused, and `/save` notes that in one line and goes on (`.claude/skills/save/phases/session-close.md:28-33`).
2. **Do:** let `/checkin` compact the pad before it compares.
   - **Why:** a comparison against a brief that does not yet hold the session's notes reports no tensions (`.claude/skills/checkin/phases/1-orient.md:243-251`).
3. **Do:** answer `/checkin`'s one batched round; it drafts every change, including any to the status block, and writes only on a yes.
   - **Expect:** drift in the frame is flagged, not redrafted (`.claude/skills/checkin/SKILL.md:55-58`); a change to the frame meets the street sign described under Desired Outcome.
4. **Do:** let the blind reader run on the fixed brief once the edits land.
   - **Expect:** in a pickup window, or when nothing landed, it does not run and stamps `NOT_OWED`; a reader that could not open the brief is reported as "not run", not as a pass.
5. **Do:** let `/save` extract, tier, pre-fill and write the survivors; journal first; sweep debt into the debt ledger; sync the brief.
   - **Expect:** on a long or compacted session, early dead ends may be outside the window, so `/save` asks the person whether any from earlier still need capturing (`.claude/skills/save/phases/standard-steps.md:309-311`; the question is `/save`'s own text, and no hook prints it).
   - **Check:** `system/tools/journal.py` appended the row; the coverage note is the step ledger's print, not a composed list (`.claude/skills/save/SKILL.md:69-70`) — a print of what was reached, not proof of quality.
6. **Do:** sweep out what this session demonstrably closed: delete it from the debt ledger's open list and move resolved open loops to their resolved section, not ticked in place (`.claude/skills/save/phases/standard-steps.md:273-284`).
   - **Why:** a ticked item left in an active list gets re-read as open and redone.
7. **Do:** emit the session handoff form.
   - **Expect:** at most 200 words, counted by the one-line command beside the form; a short timeline — what just finished, what is happening now, the very next step — plus the live thinking and what waits on the person; the plan line only when there is a plan; anything longer goes in a file with a one-line pointer (`.claude/skills/save/phases/standard-steps.md:376-420`).

### Move a finding up

1. **Do:** let it climb by shelf: the scratchpad, then the journal and the story log, then a record, then — only if it passes both tests — a canon proposal on the proposals shelf.
   - **Expect:** which record type and which canon level → `canon/data-layout.md` and `canon/knowledge-altitude.md`. Lessons about how the system itself performed take their own route: `/save`'s self-learning step appends them to the learnings file (`.claude/skills/save/phases/standard-steps.md:244-257`; path in `canon/data-layout.md:236`). Nothing the machine writes is marked vetted; only a person vets (`.claude/skills/save/SKILL.md:63`), because a marker a file carries about itself is not a gate (`canon/canonical-principles-sop.md:844-846`).
2. **Do:** for a canon candidate, run the conflict scan and show the framed panel.
   - **Expect:** `system/tools/canon_conflict_scan.py` tags it NEW, DUPLICATE or CONFLICT; on a conflict, nothing is written until the person has seen both texts and said yes (`.claude/skills/save/SKILL.md:50-53`).
3. **Do:** write it only on the person's explicit yes.
   - **Expect:** `system/hooks/guard_canon_write.sh` refuses fast-stale or oversized notes canon and asks before a whole-file replace.
4. **Do:** grade it by THE FRAME's tiers in `canon/canonical-principles-sop.md`; one build's receipts stay OBSERVED.
5. **Do:** let the daily diary carry the day: one entry per day, written by the diary job, with weekly and longer roll-ups drafted from it (`canon/data-layout.md:242`).
   - **Expect:** a roll-up is an unverified draft until a person's check-in stamps it.
6. **Do:** for the harness's own `canon/` folders, route the change through a full canon-files run instead of `/save`.
   - **Why:** nothing lands in those folders until it has passed one (Enver, 2026-11-14).

### Plan and build

1. **Do:** amend the project's one plan file; with several candidates, stop and show them.
   - **Why:** check `/autoplan`'s output against the record, because its own banner says it is not working well (`.claude/skills/autoplan/SKILL.md:17`).
   - **Expect:** a plan is retired by renaming (`.claude/skills/autoplan/SKILL.md:55-60`); deleting one is refused.
2. **Do:** run `/build` through its runner, which is run once live before its fate is decided (Read This First).
   - **Expect:** exit 0 done, 1 failed, 70 waiting for the person's answer, 4 unreadable record (`.claude/skills/build/SKILL.md:66-71`).
3. **Do:** write any discovery that changes the plan into the plan file, not only into chat.
4. **Do:** retire finished tasks with `system/tools/plan_retire.py`, which re-runs each Verify.

## When Something Goes Wrong

- **If an arm is refused (Start, step 2):** report it and stop; what happens next is `canon/coordinating-windows-sop.md`'s.
- **If a write would shrink a brief or a plan sharply:** the truncation guards stop it (`system/hooks/guard_brief_truncation.sh`, `system/hooks/guard_plans_truncation_floor.sh`); treat the refusal as a near-wipe, not a nuisance — find what produced the short write before retrying.
- **If the project flag is missing mid-session:** `/save` recovers it with `pm_flag_recover.py`.
- **If `/checkin` is refused:** no project is armed; at session close `/save` continues without it.
- **If a tool returns `CANNOT-READ`:** report the step unevaluated; it is not a clean result (`.claude/skills/checkin/SKILL.md:148-150`).
- **If the blind reader cannot read the brief (Close, step 4):** report the handoff proof as not run, not as passed, and tell the person.
- **If the pad will not clear:** `pad_archive.py` refused because its proof did not match; leave the pad and report.
- **If `/build` exits 70 or 4:** ask the person, or stop; do not answer for them and do not repair the record by hand.
- **If a new session redid finished work:** check the board and the status block with `system/tools/checkin/board_check.py`, the plan's ticks with `plan_retire.py`, and whether the last close swept finished items out of the debt ledger and open loops (Close, step 6).
- **To undo:** a brief section is recovered from the journal and the pad archive beside the brief; a plan is un-retired by renaming; a canon line is changed only by the person, with the old wording archived word for word.
- **Stop and ask the person when:** the frame, the desired outcome or the scope would change; a canon write is proposed; the project or plan would switch; several plan files could be the live one; the slug is unknown; a guard blocks a step.

## Don't Retry

- **Delegating the scratchpad write to a sub-agent** — failed because a delegated writer truncated a brief to zero bytes. Proof: `system/hooks/scratch_capture_gate.sh:188-191`, `:213`.
- **Locating a brief section by an unanchored text search and rewriting from there** — failed because the search matched a story-log entry that quoted the heading, and most of a brief was deleted in one write. Proof: `system/hooks/guard_brief_truncation.sh:6-14`.
- **Writing to a plan file through a command whose own text could run** — failed because a plan was flattened to a few bytes repeatedly in one morning. Proof: `system/hooks/guard_plans_truncation_floor.sh:6-14`.
- **Letting `/checkin` write the status block directly with no yes** — failed because it stacked a fourth block on three contradicting ones, and the person approved a frame they had not read. Proof: `.claude/skills/checkin/SKILL.md:64-80`.
- **A long prose spec asking for a short handoff, or a looser word cap** — failed because each loosening was gamed by a longer handoff. Proof: `.claude/skills/save/phases/standard-steps.md:413-427`.
- **Putting `/checkin` back into the pickup handoff** — it loads a whole end-of-session auditor to open a window. Proof: `.claude/skills/save/phases/standard-steps.md:403-407`.
- **Running the blind reader before the edits land** — answers a question nobody asked, and it launched unasked at session start. Proof: `.claude/skills/checkin/phases/3-propose.md:219-238`.
- **Holding a living plan in plan mode** — it mints a new file each session. Proof: `.claude/skills/autoplan/SKILL.md:33-37`.
- **Finding repos by discovery commands** — they missed the second repo and reported no access that was not true. Proof: `.claude/skills/autoplan/SKILL.md:114`.
- **An `authority: user` line as the canon gate** — a machine can type it, and it refused the canon `/save` writes after approval. Proof: `system/hooks/guard_canon_write.sh:63-80`.
- **The same default kept in two files** — the raise landed in one and did not take effect. Proof: `system/hooks/pm_flag.sh:53-59`.
- **Detecting bad status blocks by a list of known-bad shapes** — the shapes multiply and the list certifies a broken brief. Proof: `system/tools/checkin/gauge_check.py:14-18`.

## Pointers

- **Rulings behind this SOP:** `canon/canonical-principles-sop.md` (THE FRAME's tiers; §5.11; §5.12; §7.2; §7.4; §7.5; the do-not-retry entries; §12.c, where Enver routed the heavy-close and pointer-delivery questions on 2026-09-06; §16 modes 6, 9, 14 and 16); `canon/data-layout.md` (paths, the journal backstop); `canon/knowledge-altitude.md` (what canon is); Enver's rulings stated in plain words in this SOP (2026-10-31 rebuild, 2026-11-14 canon-files entry check, 2026-11-15 on what belongs at which altitude); this SOP's history file.
- **Evidence:** the files listed under References; the tests named under Desired Outcome.
- **Words used here:** **brief** — a project's one living document, overwritten in place. **Frame** — the brief's desired outcome and definition of done, owned by the person. **Scratchpad** (pad) — the brief's capture section. **Journal** — the append-only log of what happened and why. **Story log** — the brief's append-only `## 4. STORY LOG` section: each decision with its outcome, overtaken entries tagged `superseded-by`. **Status block** — the brief's two-level reading of where the work stands (10,000 ft and 5,000 ft; there is no ground rung). **Conformance friction** — code that makes the intended path easy and the other path harder: from weakest to strongest, named by what it does when it fires: a sign (a refusal on a first attempt that gives one specific instruction), a speed bump (a first attempt refused with a message, where a later try gets through or gets an ask), a reason gate (stops until a reason is given), a hard block (refused every time); the full ladder is `canon/build-conformance-sop.md` §5.11. **Arm** — set the flag that tells hooks which project or plan a window is on. **Session handoff** — the short message `/save` emits at close for the next window. **Role handoff** — passing a live role from one window to another, owned by `canon/coordinating-windows-sop.md`. **Sub-plan** — a build window's plan under the project's plan. **Pickup** — a window opening cold on existing work. **Step ledger** — the record of which mandatory steps a run reached.

## History

- 2026-11-15 — first draft, written from code and live state for round four; revised the same day after an independent check, after a cross-read of all six drafts, and finished from Enver's rulings of 2026-11-15 (no rules at this altitude; References added). Older wording: none.

## References (work in progress)

Every real thing this SOP points at, with what it is and does. Paths are relative to the harness repo. Friction strength is named where an entry holds a step. Entries marked **not built yet** are mechanisms Enver has said yes to, or rulings the code does not hold yet; each points up to the principle it serves and across to its line in this SOP's gap list.

**Skills**
- `.claude/skills/project-manager/SKILL.md` — starts a project: the brief, the frame intake with the person, the registry row, the flags; `ANCHOR.md` beside it is the build spine re-shown each turn on a build.
- `.claude/skills/read/SKILL.md` — loads the armed brief first, then on-branch canon and search results with trust labels; changes nothing.
- `.claude/skills/save/SKILL.md` with `phases/standard-steps.md` and `phases/session-close.md` — files a session's output onto its shelves, journal first, and emits the session handoff; stops only for canon.
- `.claude/skills/checkin/SKILL.md` with `phases/1-orient.md`, `2-reconcile.md`, `3-propose.md` — reconciles goal, brief and session; asks once; runs the blind reader on the fixed brief.
- `.claude/skills/orient/SKILL.md` — a prompt that restates the altitudes and the near past, present and future.
- `.claude/skills/autoplan/SKILL.md` — amends the project's one plan file; carries Enver's under-construction banner.
- `.claude/skills/build/SKILL.md` with `scripts/build_run.sh` and `scripts/plan_queue.py` — the build runner: walks open cards, runs each Verify itself, writes the record; hard stop at exit 70 until the person answers.
- `.claude/agents/worker.md` — the read-only helper `/checkin` names as its blind reader.

**Hooks**
- `system/hooks/pm_flag.sh` — arms and reads the project flag and its window lock; refuses a different project (hard block, exit 3).
- `system/hooks/plan_flag.sh` — the same for the plan; records the plan when plan mode presents one.
- `system/hooks/pm_persist.sh` — prints the project line once per arming and issues the one-use grant from the person's own words (owned by `canon/context-injection-sop.md`).
- `system/hooks/guard_pm_flag_store.sh` — speed bump on writes into the flag store.
- `system/hooks/guard_checkin_needs_project.sh` — refuses `/checkin` with no project armed (hard block).
- `system/hooks/save_routing_hint.sh` — sign: routes a bare "save this" to the armed brief's scratchpad, or says to ask.
- `system/hooks/scratch_capture_gate.sh` — reason gate at the end of a turn: at each token checkpoint it bounces once with the pad lines added so far and asks the main window to append the rest.
- `system/hooks/scratch_sweep_nudge.sh` — the token signal the capture gate reuses (owned by `canon/context-injection-sop.md`).
- `system/hooks/guard_brief_truncation.sh` — hard block on a write that would shrink a project brief sharply.
- `system/hooks/guard_plans_truncation_floor.sh` — hard block on a write that would flatten a plan file.
- `system/hooks/guard_canon_write.sh` — hard block on fast-stale or oversized notes canon; asks the person before a whole-file replace of canon.
- `system/hooks/step_receipt.sh` — writes `/checkin`'s receipt that `/save` reads back once to skip re-deriving the project.

**Tools and shared code**
- `shared/brain_root.py` — the one resolver for where the person's notes live.
- `shared/registry.py` — slug to folder, brief, records and canon; refuses a folder whose last segment is not the slug.
- `system/tools/journal.py` — append, slice and rotate for the journal.
- `system/tools/save/pad_archive.py` — archives the pad beside the brief and proves it landed before clearing (refuses on a hash mismatch).
- `system/tools/save/save_step_ledger.py` — the coverage table of which `/save` and `/checkin` steps were reached.
- `system/tools/save/pm_flag_recover.py` — restores a project flag that dropped mid-session.
- `system/tools/canon_conflict_scan.py` — tags a canon candidate NEW, DUPLICATE or CONFLICT against existing canon.
- `system/tools/checkin/checkin_open.py` — prints the status block mechanically at the start of `/checkin`.
- `system/tools/checkin/gauge_check.py` — checks the brief's status section has one legal status surface.
- `system/tools/checkin/board_check.py` — checks the open-questions board and the status block against the plan.
- `system/tools/plan_lint.py` — the plan draft gate; its boot guard checks it still fails a known-bad plan.
- `system/tools/plan_retire.py` — retires a plan task only after re-running its Verify.
- `system/tools/plan_git_check.py` — finds open plan boxes that shipped commits already closed.
- `system/tools/conform.py` — the build's conformance doors after each card and on the whole artifact.
- `system/tools/project-manager/check_slug_folder.py` — audits folder-name and slug drift.
- `system/tools/planning-diary-capture.py`, `system/tools/planning-diary-rollup.py`, `system/tools/planning-diary-run.sh` — the daily diary entry and the periodic roll-up drafts.
- `system/jobs.md` — the scheduled-jobs manifest, where the diary job's row lives.
- `system/organism/manual.md` — the system map that names the honour-system edges above.

**Data** (paths are `canon/data-layout.md`'s)
- The project brief, its scratchpad and story log; the pad archive beside it; the journal and its monthly segments; the project registry; the learnings file; the debt ledger and open loops; records and their proposals shelf; plans; the diary.

**Not built yet**
- **not built yet:** a street sign, seen only by the session, when it is about to change a brief's frame: "This is the person's goal. Did they ask for this change in their own words? If yes, go ahead." No block, no popup; the person's own edits pass (Enver approved, 2026-11-15). Serves: `canon/canonical-principles-sop.md:845-846` (a real gate is interactive or structural).
- **not built yet:** a check that a brief overwrite has a matching journal entry first. Serves: `canon/data-layout.md:195-197` (the journal is the backstop).
- **not built yet:** refusal of a plan file's deletion, pointing to retirement by renaming. Serves: not yet in canon.
- **not built yet:** the status check taught the two-level status block, with no ground rung. Serves: not yet in canon.
- **not built yet:** the project lock living as long as the window, separate from the flag's expiry. Serves: not yet in canon.
- **not built yet:** the session handoff's plan line made optional. Serves: `canon/canonical-principles-sop.md:696` (current state as files).
- **not built yet:** `/checkin`'s blind reader on the medium tier, re-tested to open a brief on a cloud drive. Serves: `canon/helpers-and-model-routing-sop.md` (tier table).
- **not built yet:** a stamp that proves a `/save` step really ran, not that it was reached. Serves: `canon/canonical-principles-sop.md:591` (a marker advances only on proof).
- **not built yet:** the diary job switched on. Serves: `canon/data-layout.md:242`.
- **not built yet:** the skills' data folders moved to canon's map, with no umbrella folder. Serves: `canon/data-layout.md:226-257`.
