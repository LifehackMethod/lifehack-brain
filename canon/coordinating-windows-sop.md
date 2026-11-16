---
title: Coordinating Windows
status: approved
approved_by: "Enver on 2026-11-16, round four's 'land it'"
last_reviewed: 2026-11-16
purpose: Say how one person runs several Claude Code windows on one piece of work — one coordinator window they talk to, disposable build windows below it — and how work, approvals and reports pass between live windows without being lost, invented or overwritten.
read_when: Before opening a second window on the same work; before handing a coordinator or build window over to a fresh one; when relaying an approval or a report from one window to another; when two windows seem to be stepping on each other.
history: "canon/coordinating-windows-sop.history.md"
---

## Read This First

- **Purpose:** a window (one Claude Code session) forgets everything when it closes and sees nothing another window does. When one person runs several windows at once, the same few failures repeat: a window takes on the wrong work, acts on an approval nobody gave, acts on a handoff's claims without checking them, overwrites another window's files, or pulls the person into every window. This SOP describes the shape that holds against those failures: one **coordinator** (the window the person talks to), **build windows** below it (disposable windows that each do one piece of work from their own plan), and the **role handoff** (passing a live role from a window that is closing to a fresh one). A role handoff is not the **session handoff** — the short message `/save` writes when one session ends, which `canon/circulatory-system-sop.md` owns; a role handoff adds to it. The person's attention is the scarce thing this shape protects.
- **Use it when:** you open a second window on the same work; a window is filling up and a fresh one should take over its role; a report, a question or an approval has to cross from one window to another; two windows touch the same files.
- **Don't use it when:** a single session is ending and its knowledge has to reach the notes (the session handoff) → `canon/circulatory-system-sop.md`. Which model a helper runs on, and accepting a helper's work → `canon/helpers-and-model-routing-sop.md`. What a window receives at start without asking, including the hand-over nudge and the scratchpad capture gate → `canon/context-injection-sop.md`. Helpers in their own worktrees, one landing at a time, a shared checkout → `canon/build-conformance-sop.md` §7, which this SOP points to and does not repeat. How any hook named here is built → `canon/hook-contract.md`.
- **Covers:** the roles (coordinator, build window, helper), how each window's model is chosen, who talks to whom, role handoffs, carrying approvals and reports across windows, **read-backs** (checking a claim by opening its source instead of trusting the message), and **breadcrumbs** (a build window's short dated progress notes beside its plan, for the person to glance at). **Doesn't cover:** the session handoff, the scratchpad's own lifecycle, the helper model table, git procedure, or any one hook's mechanics.
- **How this SOP changes:** only through Enver's ruling; superseded text moves to the archive named in the header.
- **Which situation are you in?**
  - Opening a window for a piece of work → The Procedure, "Open a build window".
  - Choosing which model a window runs on → "Choose a window's model".
  - A coordinator or build window is handing over → "Hand a role to a fresh window".
  - An approval or a ruling has to reach another window → "Carry an approval between windows".
  - Something needs the person → "Bring something to the person".
  - A report has come up from a window or a helper → "Take in a report".
  - Several windows touch the same files → "Work beside other live windows".

## Desired Outcome

The person talks to one window. Every other window knows what it is for, shows it, and asks the coordinator rather than the person. Every approval a window acts on traces back to the person's own words. A fresh window takes over a role knowing what just finished, what is happening now and the very next step, and checks the record before acting on any of it. No window's work is overwritten or lost when another window lands or closes.

Conformance friction (code that adds friction toward the shape, named by file in References) holds part of this:

- **A window's project and plan are fixed for its life — a hard block.** The first well-formed arm writes a lock; arming a different project or plan, or clearing it, is refused. Only a new window, or the person's own words in their own prompt, changes it (`system/hooks/pm_flag.sh`, `system/hooks/plan_flag.sh`). `/project-manager` arms both; `/checkin` (refused until something is armed) explains the refusal when a different project is asked for. The grant from the person's words is minted only from the raw prompt (`pm_persist.sh`), and a speed bump (`guard_pm_flag_store.sh`; matches command text, so it can be worded around) slows anything else that writes the flag store.
- **A window is stopped before it writes into another project's brief or plan — a speed bump.** Once per file per window it stops a write, edit or shell write into another project's file, names both projects, and passes once acknowledged (`guard_cross_project_write.sh`). Acknowledging does not change which project the window is on.
- **A leading window is reminded every turn that it does not build with its own hands — a sign.** On a build, `/project-manager` arms its anchor, which re-injects "The lead delegates and merges; it does not build with its own hands" each turn. The anchor fits the leading roles — the coordinator, and a build window that works its plan through helpers. It does not fit a window doing back-and-forth design with the person, where that window shapes the work itself in one thread, as the anchor's own first gear describes.
- **A window sees its own arming — a sign.** The status bar shows the armed project and plan file name, coloured by freshness. The plan is recorded from the exact file the harness hands over, not the newest file in the folder.
- **Plans keep their shape and their size — hard blocks.** A plan without phases, tasks and a verify step per task is stopped before approval; a write that would shrink a plan file to near nothing is stopped.
- **A window is nudged to hand over before it frays,** and its scratchpad is captured before a turn ends; both are described in `canon/context-injection-sop.md`.

The rest is held by practice: the coordinator role, the window map, who messages whom, the rolling list of what waits on the person, and which model each window runs on.

**How to check:** each open window's status bar names its project and plan; the person can name the one window they talk to; the coordinator can show its rolling list of what waits on the person; every approval quoted in a role handoff or a plan carries the person's words and where they are recorded; a role handoff message holds a window map checked against the live session list; the lock, plan-shape and plan-floor tests listed in References pass.

## Before You Start

- Read `canon/build-conformance-sop.md` §7, "Working with helpers and across windows" — the shared-checkout, deletion and relay principles this SOP leans on.
- Know the work's brief (what is true and why) and its plan (where it is going next), and where each lives; a build window is armed to them.
- Know which window is the coordinator right now. If you cannot tell, ask the person before doing anything else.

## Principles

- **The person talks to one window, the coordinator; build windows take their questions to the coordinator. The person may still choose to work directly in a build window.** Why: the person's attention is what the whole arrangement protects, and questions that were already settled kept reaching him from build windows when they skipped the coordinator. Change if: a build that lets every window ask the person directly is measured costing the person no more time and producing no more re-asked questions. Evidence: OBSERVED — held across separate coordinator role handoffs and builds, 2026-11-06 to 2026-11-14.
- **When something does go to the person, the window says first whether they are needed, then, where the answer is known, brings a finished solution to approve: the exact steps, and what they should see after each; where the person is still unsure, it brings an honest open question with its best guess.** Why: the person's attention is the scarce thing, and a question that could have been worked out spends it; a build window whose plan answers the question keeps going, and only what the person alone can do (a push, a delete, a click only they can make) goes up. Change if: open questions brought to the person are measured costing them no more time than prepared solutions. Evidence: OBSERVED — the person's own instruction of 2026-11-11 to surface solutions for his approval, and of 2026-11-03 not to solution where still unsure (canon), in use since.
- **The coordinator keeps its own context: it reads little itself and hands heavy reading to helpers.** Why: long answers burned through coordinator windows, and the coordinator's context is the one the person's work runs through. Change if: a coordinator doing its own heavy reading is seen lasting as long as one that delegates. Evidence: OBSERVED — an incident of 2026-11-05 and a delegate-by-default practice from 2026-11-06. Which model a helper runs on is `canon/helpers-and-model-routing-sop.md`'s.
- **The coordinator keeps one rolling list of everything still waiting on the person, and hands it over with the role.** Why: the build window's feed keeps scrolling and questions slide out of sight; the coordinator is the window meant not to lose the thread, so what waits on the person lives in one place. Change if: items waiting on the person are seen surfacing reliably with no such list. Evidence: CANDIDATE — the person's ruling and the role-handoff practice of 2026-11-13 to 2026-11-15; not yet measured.
- **The coordinator does not reopen a settled decision over an operational hiccup or the person's passing mood; it leads from facts it went and checked.** Why: reopening a settled decision spends the person's attention on something already decided, and a mood is not a ruling. Change if: decisions reopened on hiccups are seen producing better outcomes than holding them. Evidence: OBSERVED — an incident of 2026-11-05; the same line reaches a leading window each turn through the project-manager anchor (References).
- **The coordinator does not do a build window's work.** Why: a coordinator that ran a build window's measurement itself, and spawned a helper the person had not approved, dropped to ground level and had to be told to stop and re-read the brief. Change if: coordinators doing build work are seen keeping their top-level picture over a long build. Evidence: OBSERVED — one incident in a recovered coordinator session, 2026-11-14.
- **Windows reach each other through the coordinator, routed by live address; a lead and its own build window may talk directly.** Why: a coordinator that is bypassed loses its picture, and a window reopened from an old conversation keeps its old name but gets a new address, so a name alone can route to the wrong window. Change if: windows messaging each other directly are seen leaving the coordinator's picture complete. Evidence: OBSERVED — one dated source, 2026-11-06.
- **When a window names another window to the person, it uses the window's work, not its number; and it says which thing it means where a word could name two (which repo, which name for a skill).** Why: the person cannot tell what a numbered window is for, and an ambiguous noun sends work to the wrong repo or project. Change if: the person finds numbered windows and unqualified nouns as easy to follow. Evidence: OBSERVED — instructed by Enver, 2026-11-03, and repeated in role handoffs of 2026-11-03, 2026-11-05 and 2026-11-10.
- **Different work means a different window, not a re-armed one.** Why: a window that re-armed itself onto another project sent session handoffs to the wrong project and edited the wrong brief, and it recurred the same evening in a second window; the project lock now refuses a second arm. Change if: a window is seen switching projects mid-session with no wrong-project write, across several sessions. Evidence: OBSERVED — `system/hooks/pm_flag.sh:32-37`, incident dated 2026-08-06.
- **The person sets each window's model as they choose; the coordinator usually runs on the largest model.** Why: the coordinator carries the judgment and the person's decisions, and the choice of model stays the person's. Change if: a coordinator on a smaller model is measured making no more routing or judgment errors over a build. Evidence: CANDIDATE — the person's practice; not measured here.
- **Each role reads its own documents whole, directly, not through a helper: a new coordinator reads the brief and the plan; a build window reads its plan whole and need not read the brief.** Why: a role handoff only works if the new window holds the context itself, and a helper's summary of a brief loses the reasons that carry best; a build window that reads the brief drifts to the coordinator's level. Change if: windows loaded through a helper's summary are seen taking over as cleanly, measured on their first questions. Evidence: OBSERVED — the person's ruling and the role-handoff practice of 2026-11-13 to 2026-11-15.
- **The brief and plan are tested on a fresh blind helper before a role handoff, and handed off only after.** Why: the writer cannot see their own gaps after hours in a window; a blind reader's assumptions show where the writing failed. Change if: handoffs made without a blind read are seen landing as cleanly. Evidence: CANDIDATE — the person's ruling and the current role-handoff practice; no measured comparison yet.
- **A role handoff note carries the trajectory — what just finished, what is happening now, the very next step — and the new window checks the record before acting on any of it.** Why: the new window needs to know where the work is going, and a coordinator was once closed after acting on a note's claim that work was in flight when it was not. Change if: windows that act on a note's in-flight claims unchecked are seen landing in the right state across several handoffs. Evidence: OBSERVED — role handoffs run with this note shape from 2026-11-03 to 2026-11-15, and the 2026-11-05 incident; `canon/canonical-principles-sop.md:1043-1046` records the same failure for hand-off claims in general.
- **The old window stays open and talks with the new one until the new one has taken over.** Why: what held across a handoff was a pointer plus a live dialogue between old and new; a pointer stored in a brief is the heavy path (`canon/canonical-principles-sop.md:1094-1095`). The new window asks its questions in one batch, each with a best guess, and keeps sending the old window updates as it goes. Change if: a handoff by stored note alone is seen holding as well, measured on a fresh window's first questions. Evidence: OBSERVED — coordinator role handoffs run this way from 2026-11-06 to 2026-11-10; `canon/canonical-principles-sop.md:1094-1095` records the first instance (2026-09-06).
- **The window map goes in the role handoff message, not the brief, and is checked against the live session list.** Why: windows come and go, so a map is only true at the moment of handoff, and a coordinator's own map has listed a window whose purpose it did not know. Change if: a map kept in the brief is seen staying accurate across several handoffs. Evidence: OBSERVED — one discipline source and one separate drift incident, 2026-11-06.
- **An approval is the person's explicit yes; "let's discuss" and a question mean change nothing yet.** Why: windows have sent work on "let's discuss" and had to stop it, and the person has had to repeat that nothing changes until they approve. Change if: windows that treat discussion as approval are seen causing no reversals across several builds. Evidence: OBSERVED — incidents on 2026-11-04 and 2026-11-05 in separate windows.
- **A relayed approval is checked at its written source before anyone acts on it, and a ruling is attributed to the person only with its source.** Why: a relayed "approved, it's in the plan" was not in the plan when checked, suggestions have been shown to the person as his own decisions, and a set of test cases once carried a ruling label with no source (`canon/build-conformance-sop.md:104`, `canon/build-conformance-sop.md:201`). Change if: relayed approvals are measured matching their source every time over several builds. Evidence: OBSERVED — `canon/build-conformance-sop.md:104` and `:201` (SEEN) plus incidents of 2026-11-02 and 2026-11-05.
- **Scope is cut only on the person's yes, and done is measured against his ruling, not the plan.** Why: a plan once moved part of the agreed scope out of a round without his ruling, every window followed the plan, and the round was called done without it. Change if: plans are seen staying faithful to the ruled scope without quoting it. Evidence: OBSERVED — one incident, 2026-11-13 to 2026-11-15.
- **A build window messages the coordinator when something landed, a decision sits above its plan, something broke or refused, or a shared folder changed; an acknowledgment needs no reply.** Why: a stream of routine messages is hard for the coordinator to keep up with and buries the ones that matter. Change if: a coordinator receiving every milestone is seen missing nothing and keeping its context. Evidence: OBSERVED — one dated source, 2026-11-06, from the person's own words.
- **A build window's notes reach the project's main scratchpad through the coordinator; build windows do not each run a save.** Why: one place holds everything a project learned, while the build window keeps a lean context and does not read the brief that scratchpad feeds. Change if: build windows that save on their own are seen leaving the project's record as complete. Evidence: CANDIDATE — the person's ruling; not yet measured.
- **A report says what its result means for the level above, and the coordinator re-reads the goal before acting on it.** Why: a build window sees only the ground, its reports describe only the ground, and those reports gradually pull the coordinator's picture down to their level (`canon/canonical-principles-sop.md:1366`). Change if: the test canon names for this fix shows reports written this way leave the coordinator's goal no better held. Evidence: CANDIDATE — canon lists this as an untested candidate fix for low-altitude pull (`canon/canonical-principles-sop.md:1366`); the failure itself is OBSERVED there.
- **Another window's account of its own work, or a handoff's factual claim, is not evidence; the claim is read back from its source.** Why: a hand-off carried several wrong claims, all caught by opening the file (`canon/canonical-principles-sop.md:1043-1046`). A landing is read back from where it was saved (the git host, if the work is in git; otherwise the saved file), not from the window that saved it. Change if: window reports and handoff claims are measured matching their sources over many hand-offs. Evidence: OBSERVED — `canon/canonical-principles-sop.md:1043-1046` (2026-09-05). Accepting a helper's work is `canon/helpers-and-model-routing-sop.md`'s.
- **The coordinator writes each build window's plan: a sub-plan under the project's one plan, with its own altitudes, that agrees with the plan above it.** Why: a manager plan that copied the top plan's goal down instead of stating its own was a real bug, and a window reading the top plan works on the wrong level; the person ruled that the coordinator writes these plans. Change if: windows that write their own plans, or work from the top plan only, are seen staying on their own task. Evidence: OBSERVED — one dated source naming a 2026-11-05 bug, and the person's ruling. One plan per project is `canon/circulatory-system-sop.md`'s; a build window's sub-plan is the exception it points here for.
- **Before windows work in parallel, settle the seam: which window writes which file.** Why: coordination at the seam, not capability, is where multi-agent work fails, and append-only writing does not stop two writers forking a file — one named writer per path does (`canon/canonical-principles-sop.md:926`, `canon/canonical-principles-sop.md:930`). Change if: parallel windows with no agreed writer per file are seen producing no overwrites or conflict copies. Evidence: RESEARCHED — `canon/canonical-principles-sop.md:926`, `:930` (§8 practices, outside evidence).
- **On a shared surface, check its current state just before adding, and commit only the files you made.** Why: two windows gave the same entry number on the same day, and a window's commit can carry another window's uncommitted work. Change if: shared counters and checkouts are seen staying clean with several windows writing and no check. Evidence: OBSERVED — incidents of 2026-11-05.

## The Procedure

### Open a build window

1. **Do:** decide whether the work needs its own window.
   - **Why:** each split adds a handoff to get wrong; canon's default is one unit, and a split has to earn itself (`canon/canonical-principles-sop.md:686`).
   - **Expect:** a new window when the work would overflow one window's context, needs its own plan, or needs a check by a window that did not build it.
2. **Do:** name the window by its work, so it can be named that way to the person.
3. **Do:** arm it to the project and plan in the new window, with `/project-manager`, or with the two arm lines (`pm_flag.sh arm`, `plan_flag.sh set`).
   - **Check:** the status bar shows the project and the plan file name.
4. **Do:** as coordinator, write its plan: a sub-plan under the project's plan, opening with the three altitudes of its own work.
5. **Do:** give it its starting brief: its own plan, the list of what is already settled, which files it writes, and that it asks the coordinator, not the person.
6. **Do:** tell it when to message the coordinator — landed, a decision above its plan, broke or refused, a shared folder changed — and that its notes go to the coordinator for the project's main scratchpad; and have it leave breadcrumbs in `<plan name>.progress.md` beside its plan: newest on top, dated, a few plain sentences on where the plan stands, added when a step finishes or something surprises it, not on a timer.
7. **Do:** have it stand up its task queue at once, then work the plan through helpers.
8. **Do:** add it to the window map the coordinator keeps, and read its breadcrumbs; if they show the build drifting, step in before the person has to.

### Choose a window's model

1. **Do:** ask the person which model each window runs on, or use the one they have set; the coordinator usually runs on the largest.
   - **Why:** the coordinator carries the judgment and the person's decisions, and the choice stays theirs.
2. **Do:** leave the model a window's helpers run on to `canon/helpers-and-model-routing-sop.md`.
   - **Expect:** a model change reaches only windows launched after it; see `canon/context-injection-sop.md`.

### Hand a role to a fresh window

1. **Do:** bring the story log up to date (the log is defined in `canon/circulatory-system-sop.md`); each build window sends the coordinator one line per real move since the last role handoff, and the coordinator writes them in, since a build window does not read the brief.
   - **Why:** a stale log starts the new window in the wrong place.
2. **Do:** test the brief and plan on a fresh blind helper: give it the two files and a short note, without hinting at what changed, and ask what it is assuming and what confused it; fix what it shows, then hand off.
3. **Do:** list every window talked to this session — name (its live address), role, project, relationship, state — and mark open windows you have not contacted as unknown; check the list against the live session list.
4. **Do:** if you are the coordinator, run the session close (`/save`; see `canon/circulatory-system-sop.md`), which writes the session handoff and handles the scratchpad; a build window does not run it: it makes sure its one line per real move has reached the coordinator (step 1) and that its `.progress.md` breadcrumbs are current.
5. **Do:** write the role handoff message: the top-level goal and frame, the plan, what just finished, what is happening now, the very next step, the ground details files cannot hold, where the failures are recorded, the window map, the rolling list of what waits on the person, and a line telling the reader to check the work itself (git, if the work is in git), the window list and the records before relying on any of it.
   - **Expect:** it adds to the session handoff rather than replacing it. The session handoff keeps its own word cap (`.claude/skills/save/phases/standard-steps.md:376`); the role handoff message is separate, and load-bearing detail that does not fit goes in a file the message points to (`.claude/skills/save/phases/standard-steps.md:408`).
6. **Do:** find the fresh window: the newest idle blank window. If there is none, ask the person to open one, and wait.
   - **Should / may:** a window should not open a new window itself, because the person closes windows they do not recognize, as happened on 2026-11-15.
7. **Do:** reach the new window directly; have it arm the project and plan and read its documents whole, by role (a coordinator: brief and plan; a build window: plan only).
   - **Check:** its status bar shows the same project and plan as the old window's.
8. **Do:** let the new window check the note's claims against the record, ask its questions in one batch, each with its best guess, and take answers from the old window until they agree; the new window keeps sending the old one updates as it goes.
9. **Do:** introduce the new coordinator to every window that reports to it; do not contact windows marked unknown.
   - **Why:** otherwise build windows keep sending notes to a window that is about to close.
10. **Do:** before closing the old window, check what it leaves behind: worktrees, commits not yet on the remote, background monitors.
    - **Why:** old build windows have left worktrees holding the only copy of a commit, and monitors running long after their work ended.
    - **Check:** each item is landed, handed to the new window by name, or stopped.
11. **Do:** close the old window only after the new one confirms it has taken over.

### Carry an approval between windows

1. **Do:** quote the person's words and say where they are recorded.
2. **Do:** in the receiving window, open that record before acting; for loosening a guard or editing a `CLAUDE.md`, follow `canon/build-conformance-sop.md` §7.
3. **Do:** if the words were "let's discuss", a question, or an off-hand remark, change nothing — no files, no messages, no actions — until the person says go.
4. **Do:** if the work would cut or change the ruled scope, take it back to the person through the coordinator.

### Bring something to the person

1. **Do:** check whether the plan, canon or the already-settled list answers it; if so, act on that and tell the person after, if at all.
2. **Do:** say first, in one line, whether the person is needed.
3. **Do:** bring a finished solution with a recommendation first, then one or two plain sentences on why; where the person is still unsure, bring an honest open question with a best guess instead.
   - **Expect:** the person answers yes, no or a change, without having to work anything out.
4. **Do:** when the answer is human hands (something the person does on the computer: a click, a password, a setting only they can change), weigh their minute against your hours of workaround; then give one or two steps at a time, each with what they should see afterwards, and wait.
   - **Should / may:** human hands should not stand in for anything a window can do itself; when a guard blocks you, human hands may be the right route, and a workaround is not.
5. **Do:** from a build window, prepare it the same way and send it to the coordinator, which decides whether the person is really needed and puts it on the rolling list; keep working on everything else meanwhile.
6. **Do:** when the person replies, answer exactly that and stop; a reply is not an invitation to raise new items that do not pass step 2.

### Take in a report

1. **Do:** read the report against the goal at the coordinator's level.
   - **Should / may:** the coordinator should re-read the goal before acting on a report, because ground-level reports pull its picture down; canon lists this as an untested candidate fix, not a proven one (`canon/canonical-principles-sop.md:1366`).
2. **Do:** read back every claim you will act on from its source — the file, the test output, the git host (if the work is in git).
3. **Do:** for work that has to be right, have a window that did not build it check it.
   - **Why:** the same window re-reading its own work is the weakest check; a separate window is a real one (`canon/canonical-principles-sop.md:1113-1120`).
4. **Do:** for a helper's report — how to spawn it so the report comes back, and how to accept it — follow `canon/helpers-and-model-routing-sop.md`; for a stalled background helper, `canon/build-conformance-sop.md` §7.

### Work beside other live windows

1. **Do:** before parallel work starts, agree which window writes which file, and record it in each window's starting brief.
2. **Do:** for the shared checkout, deletions, relays and orders that name one project, follow `canon/build-conformance-sop.md` §7.
3. **Do:** read a shared counter or list just before adding to it.
4. **Do:** if the work is in git, commit only the files you made, naming them (`git commit --only <files>`); if not, save only the files you made.

## When Something Goes Wrong

- **If an arm is refused (Open, step 3):** the window is already armed to other work. Open a new window, or have the person say in their own prompt that the project changes. The refusal is the lock working.
- **If the status bar shows a stale arm of the right plan (a resumed window):** refresh it with `plan_flag.sh set <absolute path of the same plan>`, which `/checkin` and `/read` use; the same plan re-arms normally.
- **If the status bar shows the wrong plan:** treat it like a refused arm above. Arming a different plan is refused once the window is locked, and `/checkin` says not to work around that refusal; open a new window, or have the person say in their own prompt that the plan changes.
- **If a launcher or its settings changed:** close and relaunch every open window; a window reads its launcher's settings once, when it starts (see `canon/context-injection-sop.md`).
- **If the coordinator finds itself doing build work:** stop, re-read the brief and its goal, and hand the work back to a build window.
- **If a window acted on something that was not an approval:** stop it, list for the person exactly what changed, and undo only what they ask.
- **If notes were sent to a coordinator that has closed:** the receiving window is gone; resend them to the new coordinator and add the missing introduction (Hand, step 9).
- **If a write into another project's brief or plan is stopped:** acknowledge it with `guard_cross_project_write.sh ack "<absolute path>"` only when the write is intended, and say so to the coordinator; otherwise the window was about to write into the wrong project — stop.
- **If a role handoff note's claims do not match the record:** go by the record, and ask the old window what is actually in flight.
- **If a plan file was flattened:** restore it from the brain folder's backup (Drive version history); if the plan is kept in git, from git.
- **To undo:** a role handoff can be reversed while the old window is still open. Once it is closed, what was only in its context cannot be recovered — so it stays open until takeover.
- **Stop and ask the person when:** an approval cannot be traced to their words; the work would change the ruled scope; a guard blocks a step; a window not on the map turns up; you would move or delete something you did not make; you cannot tell which window is the coordinator.

## Don't Retry

- **A window re-arming itself onto another project on its own judgment** — failed because session handoffs went to the wrong project. Proof: `system/hooks/pm_flag.sh:32-37`.
- **Recording the active plan by the newest file in the plans folder** — failed because it cross-wired parallel windows. Proof: `system/hooks/plan_flag.sh:76-77`.
- **Acting on a hand-off's factual claims without opening the source** — failed on several wrong claims in one hand-off. Proof: `canon/canonical-principles-sop.md:1043-1046`.
- **Crediting the person with a ruling that has no source** — failed and was removed. Proof: `canon/build-conformance-sop.md:201`.

## Pointers

- **Rulings behind this SOP:** `canon/build-conformance-sop.md` §7 and §8 (canon); `canon/canonical-principles-sop.md` (the handoff routing at :1094-1095, verification by independence at :1113-1120, failure modes at :1334 and :1366, the hand-off do-not-retry at :1043-1046, one unit first at :686, the seam and one writer per path at :926 and :930) (canon); this SOP's history file. Accepting a helper's work: `canon/helpers-and-model-routing-sop.md`.
- **Evidence:** the files listed in References, read through their LLM CONTEXT headers, and their tests.
- **Words used here:** **window** — one Claude Code session. **Coordinator** — the one window the person talks to; it routes work and answers build windows' questions. **Build window** — a disposable window doing one piece of work from its own plan. **Helper** — a sub-agent a window spawns. **Arm** — fix a window's project or plan so the status bar shows it. **Role handoff** — passing a live role from a closing window to a fresh one. **Session handoff** — the short message `/save` writes when one session ends (`canon/circulatory-system-sop.md`). **Window map** — the list of windows, their live addresses, roles and states, true at the moment of a role handoff. **Rolling list** — the coordinator's one list of everything waiting on the person. **Story log** — as defined in `canon/circulatory-system-sop.md`. **Read-back** — checking a claim by opening its source. **Breadcrumb** — a build window's short dated progress note in `<plan name>.progress.md`, for the person to glance at. **Human hands** — something the person does physically on the computer. **Conformance friction** — code that adds friction toward the shape, named by what it does when it fires: a sign (a refusal on a first attempt that gives one specific instruction), a speed bump (a first attempt refused with a message, where a later try gets through or gets an ask), a reason gate (stops until a reason is given) or a hard block (refused every time); the full ladder is `canon/build-conformance-sop.md` §5.11.

## History

- 2026-11-15 — first draft, written from code, live state and dated role handoffs for round four; revised the same day after an independent check, the round's cross-read, and Enver's batch-session rulings. Older wording: none.

## References (work in progress)

A glossary of the real things this SOP points at, V2-relative. Where the SOP calls for a mechanism not built yet, a slot says so.

- `system/hooks/pm_flag.sh` — arms a window's project; the first arm locks it for the window's life and a different arm or a clear is refused (hard block).
- `system/hooks/plan_flag.sh` — the same lock for the window's plan; records the plan on plan approval from the exact file the harness hands over; `set` re-arms the same plan for a resumed window.
- `system/hooks/pm_persist.sh` — per-turn project line; the only issuer of the one-time grant minted from the person's own prompt that lets the project or plan change.
- `system/hooks/guard_pm_flag_store.sh` — speed bump on writes to the project and plan flag stores.
- `system/hooks/lib/flag.sh` — shared flag mechanics: session key, expiry, sweep.
- `system/hooks/guard_cross_project_write.sh` — speed bump: stops a write into another project's brief or plan once per file per window; `ack` lets an intended write through.
- `system/hooks/guard_plan_structure.sh` — hard block on approving a plan without phases, tasks and a verify step per task.
- `system/hooks/guard_plans_truncation_floor.sh` — hard block on a write that would shrink a plan file to near nothing.
- `system/sops/plan-template.md` — the plan shape the plan-structure block checks against.
- `system/statusline.sh` — the status bar: shows the armed project and plan file name, coloured by freshness (sign).
- `.claude/skills/project-manager/SKILL.md` — arms project and plan, and on a build arms the anchor below.
- `.claude/skills/project-manager/ANCHOR.md` — per-turn reminder for a leading window: delegate and merge, do not build with your own hands, do not reopen a settled decision over a hiccup (sign).
- `.claude/skills/checkin/SKILL.md` — picks a project back up in a fresh window; explains the arm refusal and says not to work around it.
- `.claude/skills/save/phases/standard-steps.md` — the session close; holds the session handoff and its word cap.
- `hooks/hooks.json` — the plugin's hook registrations (generated; see `canon/hook-contract.md`).
- `system/hooks/tests/test_pm_lock_override.sh`, `test_plan_lock_override.sh`, `test_plan_structure_guard.sh`, `test_plans_truncation_floor_guard.sh` — tests for the project lock, the plan lock, the plan-shape block and the plan floor.
- `<plan name>.progress.md` (beside each build window's plan) — the breadcrumb file: short dated progress notes for the person.
- **not built yet:** detect two windows writing the same scratch or plan file, and say so. Serves: one named writer per path (`canon/canonical-principles-sop.md:926`).
- **not built yet:** carry a build window's notes into the project's main scratchpad through the coordinator. Serves: not yet in canon.
- **not built yet:** link a build window's sub-plan to the project plan above it. Serves: not yet in canon.
- **not built yet:** the project and plan lock headers reworded to say the lock is per session id, with the folder-key fallback kept unlocked on purpose. Serves: not yet in canon.
- **not built yet:** stop the deletion of a plan file and retire it by renaming instead (shared with `canon/circulatory-system-sop.md`). Serves: not yet in canon.
