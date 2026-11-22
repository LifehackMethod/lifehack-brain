---
title: Context Injection
status: approved
approved_by: "Enver on 2026-11-16, round four's 'land it'"
last_reviewed: 2026-11-16
purpose: Say what a session receives without the person typing it — at session start, on every turn, at tool time and at the end of a turn — where each piece comes from, and how to add, change, trim or diagnose it.
read_when: Before adding, changing or removing anything that puts text into a session unasked; when a session did not know something it was meant to know; when a session's standing context costs too much.
history: "canon/context-injection-sop.history.md"
---

## Read This First

- **Purpose:** a session can only act on what reaches it. Most of what a session knows when it starts, and much of what it is reminded of each turn, arrives without the person seeing it sent. This SOP is the inventory of that invisible layer (context injection: text put into a session by the harness, not typed by the person) and the practice for keeping it true, small and honest about where it came from. It is the pilot of six SOPs written together; the other five point here for anything about what a session receives.
- **Scope:** it describes the harness as built on its `V2` branch.
- **Use it when:** you add, change or remove an injector (anything that puts text into a session unasked); a session "didn't know X" it was meant to know; you are trimming what every session or every turn pays for; you change what loads at session start.
- **Don't use it when:** deciding whether a hook is the right tool at all, or which kind → `canon/hook-sop.md`. How a hook is written, registered and deployed → `canon/hook-contract.md`. What a desk adds on top of the shared stack, and its two loading doors → `canon/desk-building-sop.md` §4. When a skill arms or clears its own anchor → `system/hooks/skill_anchor.sh` and the header of `system/hooks/skill_anchor_inject.sh` (no canon document covers it yet). Which model a helper runs on → `canon/helpers-and-model-routing-sop.md`. Where your own standing instructions go → `docs/LOCAL-INSTRUCTIONS.md`.
- **Covers:** the full shared stack — the files Claude Code loads by itself, the session-start hooks, the per-turn hooks, guard messages at tool time, what reaches the model after a tool runs, end-of-turn messages — and which desk's canon loads. **Doesn't cover:** a skill's body when a person invokes it (that is the person asking), the content of the injected principles themselves (canon owns them), or the mechanics of any one hook.
- **How this SOP changes:** only through Enver's ruling; superseded text moves to the archive named in the header.
- **Which situation are you in?**
  - Adding or changing an injector → The Procedure, "Add or change an injector".
  - Changing what a session sees when it starts → "Change the session-start stack".
  - A session didn't know something → "Diagnose a session that didn't know X".
  - Standing context costs too much → "Trim what sessions pay for".

## Desired Outcome

Every session receives the standing floor it needs (the context loaded at every session start: the harness brief, the person's root canon, their year's aim if they wrote one, and at most one desk's canon), each turn adds only short reminders that fire when they have something to say, nothing arrives twice, and a gap is announced rather than hidden. A session receives these layers (each file is described in References):

- **Loaded by Claude Code itself, no hook:** `CLAUDE.md` from the opened folder, every folder above it, and the user's home Claude folder (`system/hooks/emit_harness_brief.sh:8-10`), along with the `.claude` instructions, skills and agents of every folder above the start folder (`canon/build-conformance-sop.md:95`); the person's untracked `CLAUDE.local.md` beside the repo's `CLAUDE.md` (`docs/LOCAL-INSTRUCTIONS.md:3-6`); and the description line of every installed skill and agent, which is what Claude matches a request against (`canon/skill-building-sop.md:113-115`).
- **Session start:**
  - The harness brief: the plugin's own `CLAUDE.md`, read at run time from the plugin root. A plugin's `CLAUDE.md` is in none of the places Claude Code auto-loads, so this hook is how a plugin user sees the brief (`system/hooks/emit_harness_brief.sh:7-15`). It stays quiet when a byte-identical copy already loads from the working folder or above, and says so when it cannot deliver.
  - The floor, from the session-context loader, in order: one job-health line; a team-skills line only if a shared skill is broken; the root canon (`<brain>/canon/canon.md`, per canon's folder map, `canon/data-layout.md:31-32`), first, and the size ceiling does not drop it; the year's aim only if the person has written one, so a fresh install pays nothing; at most one desk's canon (`desks/<desk>/canon/canon.md`), chosen by `$LIFEHACK_DESK` or else the desk folder the session opened in; a skill-capability line only if a skill declares a tool the system denies. Dated records are not loaded; they are fetched on demand. A size ceiling stops the desk canon from loading and says so. Each state the loader meets — no brain folder yet, notes not where the system remembers them, no desk, desk not found, could not read, stopped at the ceiling, no root canon — is printed as a line.
  - One line about local clones out of step with their remotes, and nothing when there is nothing to report.
  - After compaction or `/clear`, the "already printed" stamp is deleted (`system/hooks/pm_announce_reset.sh`) so the next turn prints the project line once more; the project flag and lock are untouched.
- **Every turn:** the delegation standing line, unconditionally (an operator file can replace its text); and, only when they have something to say, the buried-command hint, the numbers check, the build-SOP pointer, the work-altitude restatement (once per context-size bucket), the scratchpad depth nudge, which is also the hand-over nudge (it advises `/save` and a fresh session; at most once per 100k-token bucket past its switch threshold, and only while a scratchpad is active), the plan-written notice, the project-manager line (once per arming), the save-routing hint, and an armed skill's anchor.
- **When a command expands:** `/checkin` is checked for an active project.
- **At tool time:** a guard's deny text reaches the model (`canon/hook-contract.md:118`); some guards also add advisory context on an allowed call.
- **After a tool runs:** a connector tool's result is replaced with a cleaned copy, or a "content withheld" note, before the model reads it (adding a connector → `canon/connecting-an-outside-service-sop.md`); a file written without its required frontmatter fields gets a reminder.
- **End of turn:** end-of-turn checks and the scratchpad capture gate can bounce the turn with a message the model reads; the session recorder's "/save was not called" note goes to stderr on Stop, which the person sees and the model does not (`system/hooks/session_flight_recorder.sh:170`).

**How to check:** in a fresh window, the session-start output shows the brief once, the loader's header and closing line once, and either the desk's canon or a line saying why none loaded; a turn with nothing to say carries only the delegation line; the loader and brief tests in `system/hooks/tests/` pass.

## Before You Start

- Read `canon/hook-sop.md` §3 (the inject shape, fail posture, the per-turn ceiling) and `canon/hook-contract.md` (mechanics, Deploy & Verify). This SOP names injectors; those two say how one is built.
- Read `canon/desk-building-sop.md` §4, "Two kinds of loading, two doors" — the desk side of loading.
- Three registration layers all fire: the user's own settings, the project's `.claude/settings.json`, and the plugin's `hooks/hooks.json`. How the harness's own registration is produced → `canon/hook-sop.md:71` and `canon/hook-contract.md` Deploy & Verify.

## Principles

- **A session-start or per-turn injector's text reaches the model only through plain output and a clean exit, as `canon/hook-sop.md:42` describes; the `systemMessage` field, and the output of a session-start hook that exits non-zero, are lost without a sound.** Why: a hook can report success while nothing reaches the model, and a session-start hook that exits non-zero loses its own message (`system/hooks/session_context_loader.sh:25-32`). A guard's deny text is a different channel and does reach the model (`canon/hook-contract.md:118`); stderr on Stop does not (`system/hooks/session_flight_recorder.sh:170`). Change if: a Claude Code release makes another channel from these hooks reach the model, shown by a fresh-window test. Evidence: OBSERVED — `canon/hook-sop.md:42`; `system/hooks/session_context_loader.sh:25-32`, dated 2026-08-11.
- **Text that has to count as the person's own request rides in the person's turn, not in a file loaded at session start.** Why: Claude Code compiles an instruction into the system prompt that holds back sub-agents "unless the user requested it"; a `CLAUDE.md` line argues with it from the same plane and loses, while a per-turn injection satisfies its escape clause, which is why the delegation line fires every turn (`system/hooks/inject_delegation_standing.sh:6-21`). Change if: a fresh-window test shows session-start text satisfying the clause, or a Claude Code release drops the instruction. Evidence: OBSERVED — `system/hooks/inject_delegation_standing.sh:6-21` (version-bisected 2026-07-28; sub-agent use collapsed once the instruction landed, measured in the system this hook was ported from).
- **A loader says which state it is in on every branch, including "found nothing".** Why: the version this loader replaced reported success and delivered no memory, silently, every session; the fix was printing the truth (`system/hooks/session_context_loader.sh:56-66`). Change if: a loader whose quiet branches are measured to cost nothing ever goes unnoticed while broken. Evidence: OBSERVED — `system/hooks/session_context_loader.sh:56-66`, fixed 2026-08-11.
- **How often text is injected sets how much it may say: text sent every turn becomes wallpaper, and a once-per-bucket cadence sits between that and text sent once.** Why: repetition dulls attention, so the per-turn ceiling in `canon/hook-sop.md:44` governs per-turn hooks only, and the brief emitter states its exemption (`system/hooks/emit_harness_brief.sh:26-30`). Change if: repeated per-turn text is measured still landing after long sessions. Evidence: OBSERVED — `canon/hook-sop.md:124-135` (dated incidents 2026-06-08 to 2026-06-28); `canon/skill-building-sop.md:82-84`. The ceiling figure is a working ceiling, not a measured optimum.
- **Compaction and `/clear` remove what session start delivered, so re-anchor after them and put a reminder at the point of need.** Why: text loaded once sinks or is summarised away; that is why a hook matches `compact|clear` to re-arm the project line (`hooks/hooks.json:356-360`) and why `canon/hook-sop.md:44` says to re-anchor hardest after compaction. Change if: a test shows session-start text intact and followed after compaction. Evidence: RESEARCHED — `canon/canonical-principles-sop.md:1426` (adopted field remedy; three outside communities converge); `canon/hook-sop.md:44`.
- **Keep the floor thin up high and full on the branch the session is in.** Why: a bloated line at the top pollutes every session, yet canon that is pointed to instead of loaded is silently missed — pointer-only desk canon left about half of the known facts invisible in blind tests until the session-start hook loaded the content (`canon/knowledge-altitude.md:174-178`). Change if: a blind test here shows a pointer-only floor losing no answers, or a fuller floor losing answers to length. Evidence: OBSERVED — `canon/knowledge-altitude.md:174-178` (blind tests here, refinement dated 2026-06-13, with outside research behind it).
- **A desk window loads only that desk's knowledge; that separation is the point of the folder schema.** Why: a session given every desk's canon carries the wrong subject's facts and pays for them; the loader once did exactly that until it was desk-scoped (`system/hooks/session_context_loader.sh:300-306`). Change if: a measured case where one session needs two desks' standing canon to do its job. Evidence: OBSERVED — `system/hooks/session_context_loader.sh:300-306`, dated 2026-11-02; `system/hooks/tests/test_session_context_loader_desk_scope.sh`.
- **One source, no copies: the harness brief is read at run time from the plugin root.** Why: a hand-kept copy has nothing that updates it; the brief once carried several false lines and was rewritten once against source (commit `62b3b08`, 2026-10-30). Change if: a second reader needs a derived document and a check that keeps it matched to source exists. Evidence: OBSERVED — commit `62b3b08`; `system/hooks/emit_harness_brief.sh` SIGNPOST.
- **An injector finds its files through a contract (the plugin root, the data-root resolver, the hook's own folder), not a written-down path.** Why: a private predecessor of the brief hook pointed at a fixed path and went dark the day that path was deleted (`system/hooks/emit_harness_brief.sh:12-15`). Change if: the path contract itself changes shape. Evidence: OBSERVED — `system/hooks/emit_harness_brief.sh:7-15`, measured 2026-09-09.
- **Injected text says it came from the harness, and anything an injector grants checks the person's own words at a fixed position in the turn.** Why: peer messages and helper reports arrive in the same prompt field as the person's words; one once issued a lock-override grant under a banner claiming the human authorised it (commit `8f86e5c`, 2026-11-02). Change if: the harness gains a separate channel that marks who wrote a turn. Evidence: OBSERVED — commit `8f86e5c`; `system/hooks/tests/test_pm_lock_override.sh`.
- **A document an injector tells a session to read first is a finished, approved document in `canon/`; an unfinished one is disconnected until it is validated again.** Why: a session treats what it is handed as true, and trust is read from where a document sits (`canon/canonical-principles-sop.md:812-818`). Change if: a pointed-at draft is shown not to steer the sessions that receive it. Evidence: CANDIDATE — `canon/canonical-principles-sop.md:812-818`.
- **An inject reminds; it does not stop.** Why: it prints and lets the action go ahead, so it cannot stop anything, and a preference forced into a hook becomes wallpaper (`canon/hook-sop.md:31`, `canon/hook-sop.md:39`). Change if: a non-blocking inject is measured holding a hard line as well as a guard does. Evidence: OBSERVED — `canon/hook-sop.md:39`; `canon/canonical-principles-sop.md:1404` (a single census, not a frequency).
- **The per-turn path carries cheap mechanical text only; no model call runs inside it.** Why: a per-turn model classifier added seconds of start-up delay to every turn. Change if: a model call's start-up delay drops near zero, measured. Evidence: OBSERVED — `canon/hook-sop.md:138-142`, dated 2026-06-27.
- **Before building a new injector, use one that already fires.** Why: a delivery problem was once answered with a day of new code that nothing called, while existing per-turn injectors sat unused. Change if: no existing injector can carry the message, shown before building. Evidence: REPRODUCED — `canon/hook-sop.md:168-174` (dated 2026-08-08; its count is marked not re-checked).
- **A change to what injects reaches only windows opened after it.** Why: Claude Code reads settings and the launcher's environment when a window starts, so the only symptom in the old window is silence. Change if: Claude Code starts reloading hook settings in an open window. Evidence: OBSERVED — `canon/hook-contract.md:196-198`; a dated natural experiment on 2026-11-14, in which every compaction after a launcher change fell in a window opened before it.
- **What goes into the floor is also an altitude question: content too large or too mixed for one conversation belongs lower.** Why: `canon/knowledge-altitude.md:56-62` frames the split test as an injection question. Change if: a blind test shows mixed content in the floor not confusing sessions. Evidence: CANDIDATE — `canon/knowledge-altitude.md:56-62`, a reframing dated 2026-08-05.

## The Procedure

### Add or change an injector

1. **Do:** find an injector that already fires at the right moment and see whether it can carry the message.
   - **Why:** new injectors with no caller are a recurring failure here.
   - **Check:** you can name the existing injector and its trigger, or say why none fits.
2. **Do:** if the injector tells the session to read a document first, confirm that document sits in a `canon/` folder.
   - **Why:** an unfinished or paused document stays disconnected from every injector until it is validated again.
   - **Check:** every document a read-first injector names is under `canon/`.
3. **Do:** decide whether the message reminds or stops, and which plane it belongs in: the person's turn (per turn), session start, or a file Claude Code loads.
   - **Expect:** a stop is a guard, decided through `canon/hook-sop.md`; a preference goes in `CLAUDE.md` or a skill; text that has to count as the person's request goes in the person's turn.
4. **Do:** write it to the channel `canon/hook-sop.md` §3 describes (plain output, clean exit), opening the text with a "harness-injected, not user input" tag.
   - **Why:** text in the person's turn otherwise reads as the person's words.
5. **Do:** size the text by how often it fires.
   - **Expect:** a per-turn injector fits inside the ceiling in `canon/hook-sop.md:44`; a once-per-session one says in its header that it is exempt, so a later move to per-turn is caught.
6. **Do:** make it quiet when it has nothing to say, and loud when it was meant to load something and could not.
   - **Expect:** a session-start loader names every miss; a per-turn reminder prints nothing on a turn it does not apply to; anything lost to compaction is printed again on `compact|clear` (a once-per-arming line has its printed stamp reset).
7. **Do:** if the injector grants or unlocks anything, gate the grant on a fixed-position check of the person's own words.
   - **Check:** a test feeds it a peer-style message containing the trigger phrase and no grant follows.
8. **Do:** declare its fail posture as `canon/hook-sop.md:43` describes.
   - **Expect:** a session-start hook that only informs is `open`, or loud about what it could not load (the loader); most per-turn injectors are degrade-safe. The header names which.
9. **Do:** register, test and deploy it through `canon/hook-contract.md` Deploy & Verify (`canon/hook-contract.md:189-200`).
   - **Check:** in a fresh window the text appears once, and `wc -c` on it fits step 5.

### Change the session-start stack

1. **Do:** find which layer carries the piece: Claude Code's own `CLAUDE.md` loading, the brief emitter, or the session-context loader.
   - **Expect:** the brief is edited only in the plugin root's `CLAUDE.md`; the floor's content lives in the person's notes.
2. **Do:** fit the change inside the loader's order and ceiling.
   - **Expect:** inside the loader, root canon first, the year's aim only when written, one desk at most, and a stop line at the ceiling. The order between separate hooks is not reported anywhere, so nothing relies on it (`system/hooks/inject_work_altitude.sh:23`).
3. **Do:** check `/read` does not load the same desk canon a second time.
   - **Expect:** `/read`'s Step 0.6 skips desk canon the loader already printed (`canon/manual.md:594`); this is held by the instruction alone, with no conformance friction behind it (`canon/manual.md:566`).
4. **Do:** print no heading for anything no part of the system writes.
   - **Why:** a heading with no producer teaches a shape that does not exist (`system/hooks/session_context_loader.sh:68-71`).
5. **Do:** reopen every window; a change to the harness reaches sessions once it is installed as a new plugin version, and a change to the notes reaches the next window opened.

### Diagnose a session that didn't know X

1. **Do:** decide where X lives: in the floor (root canon, year's aim, this desk's canon, the brief) or only in records fetched on demand.
   - **Expect:** records are not in the session until something reads them.
2. **Do:** read the loader's own lines in the session-start output.
   - **Expect:** a miss is named — no data root, notes not found, no desk, desk not found, stopped at the ceiling, could not read, no root canon.
3. **Do:** check which desk the session thought it was in (`$LIFEHACK_DESK`, or the folder it opened in).
4. **Do:** check whether the output reached the model whole; long hook output can arrive as a short preview (`canon/skill-building-sop.md:393-394`).
5. **Do:** list the hooks registered at each of the three layers, and check the window was opened after the last change to any of them or to the launcher.
6. **Do:** if a hook seems not to fire, replay it by hand with a sample input; for an injector a guard protects from being run by hand, run its test suite as the guard's message directs (for the project-manager line, `system/hooks/tests/test_pm_lock_override.sh`).
   - **Why:** a quiet fire log is not proof of health, and routing around a guard to replay it defeats the guard.

### Trim what sessions pay for

1. **Do:** measure first: what each piece costs and how often its trigger is right on real prompts.
2. **Do:** sort each piece into keep, only-when-relevant, shrink-to-a-pointer, or retire, and take every cut to Enver before it lands.
   - **Why:** a cut changes what every student's session receives.
3. **Do:** prefer a pointer to a payload in standing text, except for canon a session is actually working in, which loads in full (`canon/knowledge-altitude.md:174-178`).
4. **Do:** when an injector is retired, update every description of it — the organism manual, the harness brief, and this SOP's References — in the same change.
   - **Why:** a deleted injector's manual line went on claiming a live control after it was gone (`canon/manual.history.md:577`).
5. **Do:** run the injector tests after the change; some are slow by design, so give them time before reading a timeout as a failure.

## When Something Goes Wrong

- **If a new injector prints nothing (Add, step 9):** open a fresh window first; then check the registration as `canon/hook-sop.md:71` and `canon/hook-contract.md` Deploy & Verify describe.
- **If session-start output appears twice:** look for the same script registered at more than one layer; fix it at the registration, not in the script.
- **If the floor is missing:** find the loader's line that names the miss; if there is no such line, treat the loader as broken.
- **If the brief is wrong:** fix the plugin root's `CLAUDE.md` once; do not patch a copy anywhere else.
- **If a guard denies every write after a folder or path change:** check the hook resolves its helpers beside itself, not from an environment variable.
- **To undo:** remove or revert the registration as `canon/hook-sop.md:71` and `canon/hook-contract.md` Deploy & Verify describe, update every description of the injector, and open a fresh window; an open window keeps what it loaded.
- **Stop and ask the person when:** a change would remove or shrink the standing floor for every student; a cut would retire an injector that carries a safety reminder; a guard blocks a step here.

## Don't Retry

- **Stating a per-turn behaviour once in a file loaded at session start, or in an output style** — failed because guidance loaded once faded over long and resumed sessions. Proof: `canon/hook-sop.md:124-131`.
- **The same block re-sent every turn** — failed because it became wallpaper. Proof: `canon/hook-sop.md:132-135`.
- **A model classifier inside the per-turn hook** — failed on start-up delay every turn. Proof: `canon/hook-sop.md:138-142`.
- **Keyword-only triggers with no check on meaning** — failed because a replay of the trigger code over real prompts showed most fires were wrong for most of the keyword injectors (buried-command was the exception). Proof: the replay of 2026-10-30.
- **The inject nudge family as the answer to a hard line** — failed because it is non-blocking by construction. Proof: `canon/canonical-principles-sop.md:1404`.
- **Moving a line that has to count as the person's request into a file loaded at session start** — fails because it argues with the system prompt from the same plane. Proof: `system/hooks/inject_delegation_standing.sh:16-21`.
- **Loading every desk's canon into every session** — failed because it removed the separation the desk folders exist for. Proof: `system/hooks/session_context_loader.sh:300-306`; `system/hooks/tests/test_session_context_loader_desk_scope.sh`.
- **A loader that hides its errors and exits 0 having printed nothing** — failed because it reported success and delivered no memory. Proof: `system/hooks/session_context_loader.sh:56-66`.
- **Trusting the prompt field as the person's words when granting anything** — failed because peer messages arrive through it. Proof: commit `8f86e5c`.
- **Hard-coding a path in an injector** — failed because the predecessor went dark when its path was deleted. Proof: `system/hooks/emit_harness_brief.sh:12-15`.

## Pointers

- **Rulings behind this SOP:** `canon/hook-sop.md` (when and which kind; the inject channel, fail posture and per-turn ceiling at §3); `canon/hook-contract.md` (mechanics, Deploy & Verify, restart); `canon/knowledge-altitude.md` (floor shape, the altitude test); `canon/desk-building-sop.md` §4 (desk loading); `canon/data-layout.md` (where the floor's files live); `canon/skill-building-sop.md` (the preview limit); `canon/canonical-principles-sop.md` §7.0 (trust by location).
- **Evidence:** the LLM CONTEXT headers of the hooks named in References; the tests in `system/hooks/tests/`; commits `62b3b08` and `8f86e5c`.
- **Words used here:** **injector** — anything that puts text into a session without the person typing it. **Floor** — the context loaded at every session start. **Harness brief** — the plugin root's `CLAUDE.md`, printed at session start. **Fail posture** — what a hook does on its own failure: `open` (carry on quietly), `degrade-safe` (carry on and say so), `closed` (block). **Wallpaper** — text repeated so often the model stops attending to it. **Plane** — where text sits relative to Claude Code's own instructions: the system prompt or the person's turn. **Brain folder** — the folder the person's notes live in. **Conformance friction** — code that makes a wrong action pause, prompt or stop: a sign (a refusal on a first attempt that gives one specific instruction), a speed bump (stops the action the first time and passes once acknowledged), a reason gate (stops until a reason is given), or a hard block (refused every time, kept for a few particular things; the full ladder, with a door and a pop-up between reason gate and hard block, is `canon/build-conformance-sop.md` §5.11).

## History

- 2026-11-15 — first draft, written from code and live state for round four; revised the same day after an independent check, the pause-2 corrections, and Enver's rulings on rules and the References section. Older wording: none.

## References (work in progress)

This list is where the concepts above meet the code. It is a work in progress: entries are added as the code is read, and a "not built yet" slot marks a mechanism this SOP calls for that does not exist yet.

**Files Claude Code loads by itself**
- `CLAUDE.md` (repo root) — the harness brief; the source the brief emitter prints.
- `CLAUDE.local.md` (repo root, untracked) — the person's own standing instructions, loaded beside `CLAUDE.md`.
- `docs/LOCAL-INSTRUCTIONS.md` — how and why to use `CLAUDE.local.md`.

**Registration**
- `hooks/hooks.json` — the plugin's hook registration; generated, lists every hook by event.
- `.claude/settings.json` — the repo's project-level registration; generated from the same source.
- `system/register/register.jsonl` — the one source of hook rows.
- `system/register/generate.py` — writes `hooks/hooks.json` and `.claude/settings.json` from the rows.

**Session start**
- `system/hooks/emit_harness_brief.sh` — prints the plugin root's `CLAUDE.md` once per session; skips when a byte-identical copy already loads; fail posture `open`.
- `system/hooks/session_context_loader.sh` — prints the floor: job health, team skills, root canon, year's aim, one desk's canon, capability check; announces each miss; character ceiling.
- `system/tools/health_line.py` — the one job-health line printed first.
- `shared/tools/team_skills.py` — the shared-skill check; silent when healthy.
- `system/tools/skill_capability_check.py` — flags a skill that declares a tool the system denies.
- `shared/brain_root.py` — resolves the brain folder the loader reads from.
- `shared/desk_list.py` — maps a `$LIFEHACK_DESK` desk id to its folder.
- `system/tools/mirror_line.sh` — one line on clone drift; silent when clean.
- `system/hooks/pm_announce_reset.sh` — on compaction or `/clear`, re-arms the project-manager line; prints nothing.

**Every turn**
- `system/hooks/inject_delegation_standing.sh` — the delegation standing line, every turn; satisfies Claude Code's "unless the user requested it" clause. A sign.
- `system/hooks/inject_compute_mechanically.sh` — the numbers check, when armed or a math token appears.
- `system/hooks/inject_sop_before_build.sh` — on a build verb near a tracked noun, points at the SOP to read first.
- `system/hooks/inject_work_altitude.sh` — asks the session to restate its three altitudes, once per context bucket.
- `system/hooks/buried_command_hint.sh` — names a slash command (for example `/save`) that appears mid-message, leaving invocation-or-mention to the model.
- `system/hooks/scratch_sweep_nudge.sh` — scratchpad depth nudge, at most once per 100k-token bucket past the switch threshold, only while a scratchpad is active.
- `system/hooks/group_dispatch_pilot-map-ups.sh` — runs four per-turn members in one process, each isolated from the others' failures.
- `system/hooks/announce_plan_write.sh` — group member; notes a newly written plan.
- `system/hooks/pm_persist.sh` — group member; prints the project-manager line once per arming; issues the lock-override grant only on a fixed-position check of the person's words.
- `system/hooks/save_routing_hint.sh` — group member; says where a bare "save this" goes.
- `system/hooks/skill_anchor_inject.sh` — group member; re-sends an armed skill's lean anchor every turn.
- `system/hooks/rating_capture.sh` — logs an explicit rating; prints nothing to the model.
- `system/hooks/lib/ups_triggers.py` — the trigger and machine-prompt checks the per-turn hooks share.
- `LIFEHACK_DELEGATION_OVERRIDE` — environment variable naming an operator file that replaces the delegation line's text.

**Tool time, after a tool, end of turn**
- `system/hooks/guard_checkin_needs_project.sh` — stops `/checkin` when no project is armed. A hard block.
- `system/hooks/guard_pm_flag_store.sh` — blocks a shell command whose text names the project-lock files or the grant-issuing hook, which slows a session trying to manufacture its own permission; it matches text, so anything that can read the hook can step around it (`canon/hook-sop.md:32`). A speed bump.
- `system/hooks/guard_git_push_signpost.sh`, `system/hooks/guard_no_upstream_commit_signpost.sh`, `system/hooks/lib/push_warn.py` — guards that add advisory context on allowed calls. Signs.
- `system/hooks/guard_fine_china_ask.sh` with `system/hooks/lib/fine_china_ask.py` — asks the person before an edit or delete of fine china (protection A); the first attempt on a target in a session may meet a sign instead; unattended, the ask becomes a refusal.
- `system/hooks/guard_canon_write.sh` — adds a loud notice on an allowed canon write (a sign); also refuses fast-stale or oversized notes canon (hard block) and asks the person before a whole-file replace of canon (an ask); the entry is `canon/circulatory-system-sop.md`'s.
- `system/hooks/sanitize_connector_output.sh` — replaces a connector result with a cleaned copy or a withheld note before the model reads it; fail posture `closed`.
- `system/hooks/validate_on_write.sh` — frontmatter reminder after a write.
- `system/hooks/end_of_turn_checks.sh` — end-of-turn checks; can bounce the turn. A speed bump.
- `system/hooks/scratch_capture_gate.sh` — bounces the turn once at each token checkpoint, handing back the pad lines added so far and asking the main window to append the rest. A reason gate.
- `system/hooks/session_flight_recorder.sh` — closes the session log; its "/save was not called" note goes to the person only.

**Data the floor reads** (paths inside the brain folder, per `canon/data-layout.md`)
- `canon/canon.md` — the root canon, true for everything.
- `desks/<desk>/canon/canon.md` — one desk's canon.
- The year's aim, written by `/telos`.
- `SESSION_CONTEXT_CHAR_CEIL`, `LIFEHACK_DESK` — the loader's ceiling and desk signal.

**Tests**
- `system/hooks/tests/test_emit_harness_brief.sh`, `test_session_context_loader.sh`, `test_session_context_loader_desk_scope.sh` — the brief and the floor, including one desk only.
- `system/hooks/tests/test_ups_cuts.sh`, `test_delegation_override.sh`, `test_numbers_mode.sh` — per-turn injectors.
- `system/hooks/tests/test_pm_lock_override.sh` — the grant check.
- `system/hooks/tests/test_sanitize_connector_output.sh` — the connector sanitizer.

**Not built yet**
- **not built yet:** one line saying the harness brief could not be delivered, and why. Serves: `canon/canonical-principles-sop.md` §5.6 (alive means saying so).
- **not built yet:** one line saying the person's root canon file was not found. Serves: `canon/canonical-principles-sop.md` §5.6.
- **not built yet:** the loader reading the root canon from canon's folder map. Serves: `canon/data-layout.md` (The shape, `canon/canon.md`).
- **not built yet:** shared hooks registered once, with the duplicate rows removed from the repo's own settings. Serves: `canon/canonical-principles-sop.md` §9, "One copy, in the shared layer" (2026-10-29).
- **not built yet:** the after-a-write frontmatter reminder printed where the model reads it. Serves: `canon/canonical-principles-sop.md` §5.8 (detection and action are two problems).
- **not built yet:** a size budget across the three `CLAUDE.md` layers. Serves: `canon/canonical-principles-sop.md` §5.19 (place each fact at the broadest scope where it holds).
- **not built yet:** tests for the injectors that have none, and a size census of the skill and agent listing. Serves: `canon/canonical-principles-sop.md` §5.7 (only breaking the thing proves the detector).
- **not built yet:** a fresh-window test of whether text loaded at session start counts as the person's own request. Serves: `canon/canonical-principles-sop.md` §4.1 (verify the effect, not the report).
- **not built yet:** a check that a "read this first" injector points only inside `canon/`. Serves: `canon/canonical-principles-sop.md` §7.0 (trust from where a line sits).
- **not built yet:** the delegation standing hook committed and registered in the plugin's `hooks/hooks.json` (on origin its only copy sits in the archive). Serves: this SOP's principle that text counting as the person's own request rides in the person's turn.
- **not built yet:** a commit-time check that each injected message carries the "harness-injected, not user input" tag. Serves: `canon/canonical-principles-sop.md` §7.0 (written text carries no trust metadata).
