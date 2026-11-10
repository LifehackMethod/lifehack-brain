---
title: "Building and testing a skill"
status: approved
approved_by: "Enver on 2026-11-10, via the V2 coordinator (<notes>/system/journal.md, RULED · Enver, 2026-11-10)"
last_reviewed: 2026-11-10
purpose: "Build a skill that keeps doing its job in a real, filling window, by letting code hold what must hold and showing the person every failure."
read_when: "You are building, rebuilding or testing a skill, or a skill keeps skipping steps, stalling, or failing where nobody can see it."
history: "system/sops/skill-building-sop.history.md"
---

# Building and testing a skill

## Read This First

- **Purpose:** a skill must do its job in the person's real window as that window fills up, not only in a short
  demo. Prose instructions fade as a session grows, so code holds the parts that must hold (the order of the stages,
  the inputs each stage needs, where the run is) and the AI does the work inside them, classifying within the choices code offers; judgment stays with the person. Every failure must be
  visible to the person, because the worst failure is the one nobody can see breaking.
- **Use it when:** building a new skill or command; rebuilding or repairing one; testing whether a skill holds in a
  full window.
- **Don't use it when:** building a scheduled job (`cron-jobs-sop.md`), a hook or guard (`hook-sop.md`), or checking
  where a build's files go (`build-conformance-sop.md`).
- **Covers / doesn't cover:** covers every skill's file and frontmatter, skills with more than one stage, and how to
  test them. It does not cover the content of any particular skill.
- **How this SOP changes:** only through Enver's ruling; superseded text moves to the archive named in the header.
  This SOP was written fresh after the skill tester rig finished, and older skills are assumed not to meet it
  (COMPASS P-122).
- **Which situation are you in?**
  - Not sure whether it is a skill or a command → The Procedure, "Build a skill", step 1.
  - Building or rebuilding a skill → The Procedure, "Build a skill".
  - Testing a skill, or reading a test result → The Procedure, "Test a skill".

## Desired Outcome

- The skill can be found and understood from its first lines; it runs its stages in order in a real, filling window;
  a stage moves on only when code has checked it; a bad or empty input stops the stage on screen until the person
  decides; a new window picks the run up where it was; and the person can always see where the run is.
- **How to check:** the test part of The Procedure passes with valid evidence, including the skill seen stopping on
  (pausing or refusing) a planted bad input at least once (COMPASS P-5); then one real run with the person in the chair,
  watching it work and saying it is right. That real run is the acceptance test; a test's final passing result is what
  counts, and earlier runs are context (COMPASS P-121, P-137).

## Before You Start

- Build on the scaffold: the skill template `system/templates/skill-template/` and the spec sheet
  `system/templates/producer-spec-template.md` (Vision, The products of the harness). Its conformance check is not
  wired; run the checklist in Build, step 2 yourself.
- Use the shared layer first: common tools live once in `shared/`, listed in `system/register/toolbox.md` (Vision,
  The Platform).
- Know which stages talk with the person and which run alone; the design differs (Build, steps 8 and 12).
- Three bodies of evidence stand behind this SOP, each at its own level of confidence (COMPASS P-134):
  - **The skill tester rig's final result, 2026-11-05,** cited as "rig P1" to "rig P11" with the rig's own label
    (TESTED, OBSERVED ONCE, SUGGESTED). Its limits travel with every line that cites it (COMPASS P-41): one made-up
    six-stage skill, an AI stand-in for the person, Sonnet in windows copied from real sessions at about 80% full, one
    machine and one set of launch flags, and the strongest level of code only (all four levels at once — see "levels
    of code" in Pointers).
  - **The failure census, 2026-09-05,** cited as "census [F1]" and so on: failures seen again and again in real use
    across months, counted by blind readers. Counts are floors. Its full text is in the archived SOP.
  - **Other real-use lessons and outside practice** carried over from the archived SOP on Enver's yes (journal, RULED · Enver, 2026-11-10), each
    with its own label.

## Principles

### How a skill holds

- **Code holds what must hold; the AI does the work; the person judges.** Why: prose fades as a window fills; code does not. Change
  if: a skill held by prose alone survives full windows in real use. Evidence: rig P4, TESTED — code held the stage
  order in 10 of 10 tries at about 80% fill, and all 6 stages in order in each of 2 fresh-window runs (one made-up
  skill, strongest level only; it shows code can hold, not how often weaker designs fail). Enver's ruling: a skill carries as much machinery as the rig's test
  dictates (COMPASS P-119).
- **Carry only the machinery that earns its place, lightest first.** Why: every layer costs the person time and
  attention; a guard that never changes an outcome is dropped. Change if: Enver rules otherwise. Evidence: ruling
  (COMPASS P-27, P-55, P-123; Vision View 2 friction ladder).
- **The hook on the person's message acts before the AI does.** Why: a UserPromptSubmit hook can record, refuse or
  hand over text before the AI has a turn. Change if: Claude Code changes hook
  order. Evidence: rig P2, TESTED.
- **Where the run is lives in files that code writes, not in the session.** Why: a new window can only pick up what it
  is shown. Change if: a near-full pickup fails with this design. Evidence: rig P9, TESTED in fresh windows and once at
  about 39% fill; near-full pickup and pickup after auto-compaction UNTESTED.
- **A rule loaded once fades, and the same block every turn becomes wallpaper.** Why: re-inject small, vary it, and
  have the model restate it. Change if: a reproduced counter-case appears. Evidence: REPRODUCED — three dated real
  incidents, 2026-06-08 to 06-28 (archived SOP, §II.4a).
- **Where code meets the AI, code offers a fixed set of outcomes, including "no outcome", and the AI sorts into one of them.** Why: a legal answer is not
  a true answer; a workflow with no legal way to say "nothing was decided" invents a decision. Change if: Enver rules
  otherwise. Evidence: ruling (Vision View 1, the seam rule).
- **A number at a seam drifts; turn it into a named set, or write down that it is a number.** Why: code thresholds a
  number wrongly and prose lets it drift. Change if: a reproduced counter-case appears. Evidence: REPRODUCED — four
  scalars eroded in one real ingest skill while five named sets held (archived SOP, Principle 1).

### Making failure visible

- **Make every failure visible to the person.** Why: Enver, 2026-11-05: "the big problem in general is opaque failure
  the human can't see breaking." Change if: Enver rules otherwise. Evidence: rig P5, TESTED — a code-printed inputs
  line with a pause took silent bad work from 2 of 4 planted inputs to 0 of 5 (stand-in person, one fill level).
- **An error must never look like success.** Why: a script that exits 0 on a skip, a missing input or a swallowed error
  reads as "done". Change if: a reproduced counter-case appears. Evidence: REPRODUCED (census [F2], 166×).
- **A check shapes what the AI does, so it must reward honest work.** Why: an AI dropped true entries to pass a check
  that punished honesty. Change if: a reproduced counter-case appears. Evidence: CANDIDATE (rig P6, OBSERVED ONCE).
- **A dead detector and a clean system look the same.** Why: every detector needs a way to show it is alive. Change if:
  a reproduced counter-case appears. Evidence: REPRODUCED — several real instances (archived SOP, Principle 2, link 5).
- **A helper's account of its own work is never evidence.** Why: re-run the check, stricter than the helper did.
  Change if: a reproduced counter-case appears. Evidence: REPRODUCED (census [F8], 70×).
- **Writing a finding down is not delivering it.** Why: the next session never looks there; name the place it must
  reach. Change if: a reproduced counter-case appears. Evidence: REPRODUCED (census [F6], 88×).

### Building and fixing

- **Decide first whether it is a skill or a command.** Why: a command wearing skill machinery is over-built; a skill
  wearing command lightness drops the holds it needed and fails silently. Change if: Enver rules otherwise. Evidence:
  carried from the archived SOP (§III.1) on Enver's yes (journal, RULED · Enver, 2026-11-10).
- **The description is the skill, from Claude's point of view.** Why: it is the only text Claude Code matches a request against before a
  skill fires; get it wrong and nothing downstream matters. Change if: Claude Code changes how skills trigger.
  Evidence: outside practice, carried from the archived SOP (§III.3) on Enver's yes (journal, RULED · Enver, 2026-11-10).
- **Search before designing; measure before planning.** Why: a build from a premise nobody checked spins. Change if:
  a reproduced counter-case appears. Evidence: REPRODUCED (census [F5], 155×).
- **Find which seam is failing before fixing anything.** Why: fixing the wrong seam is the biggest waste in skill work;
  one real skill's files were about 95% right and the failure was elsewhere. Change if: a reproduced counter-case
  appears. Evidence: REPRODUCED (archived SOP, Principle 2).
- **When one bug is found, sweep its siblings before the second fix.** Why: one-at-a-time fixing costs rounds. Change
  if: a reproduced counter-case appears. Evidence: REPRODUCED — four rounds lost in real work (archived SOP, §III.9).
- **A tool does not exist until a live path calls it.** Why: passing tests is not shipping. Change if: a reproduced
  counter-case appears. Evidence: REPRODUCED (census [F1], 194×).
- **Watch a value travel the whole seam.** Why: a producer and a consumer written apart render empty, with no error.
  Change if: a reproduced counter-case appears. Evidence: REPRODUCED (census [F13], 35×).
- **After a cutover, check which file actually loads.** Why: two copies resolve and the runtime picks the other one.
  Change if: a reproduced counter-case appears. Evidence: REPRODUCED (census [F12], 40×).
- **The person may direct the run.** Why: working ahead because the person asked is fine (Enver, 2026-11-05, rig plan).
  Code keeps the stage where it is; the AI may still write what the person asked for. Change if: Enver rules
  otherwise. Evidence: rig P7, TESTED — 5 of 5 pushes to skip got the early output asked for while code held the stage;
  unprompted working ahead 0 of 10, on thin evidence (one stand-in, one push per try).
- **A skill that travels should not depend on a hook, a host path or `settings.json`.** Why: it stops working the
  moment it moves to a machine without them. Change if: Enver rules on whether a shared skill must work without the
  plugin. Evidence: UNSURE — carried from the archived SOP (§II.5) on Enver's yes (journal, RULED · Enver, 2026-11-10); it pulls against "use
  the shared layer, never copy it" (Open Tensions).

### Testing

- **A test counts only in the real setup, with proof it ran.** Why: a rig whose hooks never started produced
  confident, worthless results, and was retired. Change if: a reproduced counter-case appears. Evidence: rig P1,
  TESTED (that machine and those flags); ruling (COMPASS P-5).
- **Test a checker on known-good input before trusting its "no".** Why: a wrong measuring command taxes honest work
  while the real target goes unmeasured. Change if: a reproduced counter-case appears. Evidence: REPRODUCED — 7
  instances in one day, 2026-09-07 (archived SOP, §II.4a).
- **One real run with the person in the chair beats any number of test runs.** Why: tests sharpen the person's judgment about what
  "right" looks like; they do not replace the person watching it work. Change if: Enver rules otherwise. Evidence:
  carried from the archived SOP (§V.8) on Enver's yes (journal, RULED · Enver, 2026-11-10).

## Rules

- **A skill MUST do arithmetic with code, never in the model's head.** Ruled: COMPASS P-22. Enforced by: not enforced
  in code.
- **A skill MUST NOT be deleted while it is outside git; archive it whole instead.** Ruled: COMPASS P-136. Enforced
  by: hard block (ruled; build deferred to the backlog).
- **A skill shipped in the Harness MUST NOT contain private names, window names or personal paths.** Ruled: COMPASS
  P-42, P-65. Enforced by: not enforced in code here.
- **A skill MUST NOT connect to an outside system unless the person has set that connection up; without enough
  information it says so.** Ruled: COMPASS P-94. Enforced by: not enforced in code.

## The Procedure

### Build a skill

1. **Do:** decide whether you are building a command or a skill. If it could be pasted as one prompt, it is a
   command. It is a skill the moment it is any of: several steps in an order that must hold; stateful across turns;
   leading or questioning the person; carrying something that must reliably happen.
   - **Why:** a command passes on a light bar — a sharp description and clean, right-sized prose — and does not need
     the card, runner and hooks below (archived SOP §III.1, carried on Enver's yes (journal, RULED · Enver, 2026-11-10)).
   - **Expect:** a command stops after step 3; a skill continues through step 15.
   - **Check:** write down which of the four signs, if any, applies.
2. **Do:** create the skill from the scaffold in `~/.claude/skills/<name>/`, and fill the frontmatter: `skill:`
   (matching the folder), `description:`, and `shape:`, the kind of skill it is:
   - `interactive-workflow` — works through something with the person, in named phases (for example a weekly planning
     skill); it says what it asks at each phase and what "done" looks like.
   - `command` — the person types it, it does one bounded job and ends (for example a web search).
   - `utility` — another skill or tool calls it; the person usually never types it; its inputs and outputs are stated
     precisely, because its caller cannot ask a question.
   - `cron-producer` — a schedule runs it unattended and it writes a status tile; its schedule follows `cron-jobs-sop.md`.
   A skill with two real modes may list two, as `shape: [command, interactive-workflow]`; prefer one, and if you
   cannot pick, it is probably two skills.
   - **Why:** the shape tells the system and any reader how the skill is used.
   - **Must / should / may:** a personal skill SHOULD be built in `~/.claude/skills/<name>/` by default, without
     asking, with its scripts inside its own folder (COMPASS P-50). `shape:` SHOULD be one of the four above (journal, RULED · Enver,
     2026-11-10).
   - **Expect:** the description hook accepts the file (`system/hooks/enforce_skill_frontmatter.sh` blocks a
     `SKILL.md` with no description). Nothing in code checks `skill:` or `shape:`; the scaffolder stamps them at birth.
   - **Check:** `skill:` matches the folder; `shape:` is present; the outcome is stated in the first few lines;
     everything it writes is named with its path; if it can stop early or end with no outcome, that path is written
     down.
3. **Do:** write the `description:` in the third person, starting "Use when…", leading with the situation and the
   literal words a person would say, with the keywords in the first 250 characters. Keep a small routing-eval file
   beside the skill — prompts that should fire it and near-misses that should not — and run each case three or more
   times whenever the description changes.
   - **Why:** only about the first 250 characters are read, and auto-triggering is unreliable even with a good
     description; a slightly pushy description under-triggers less than a modest one. Anything that must fire needs
     an explicit invocation or a hook (archived SOP §III.3, carried on Enver's yes (journal, RULED · Enver, 2026-11-10)).
   - **Expect:** the should-fire prompts fire it and the near-misses do not, on repeated runs.
   - **Check:** the routing-eval results, each case run at least three times.
4. **Do:** lay out the skill's folder by Anthropic's convention: `scripts/` for files to run, `references/` for files
   to read into context when needed, `assets/` for files used in output.
   - **Why:** the folder tells Claude whether to run or read a file, with no tag inside it (archived SOP §II.6,
     carried on Enver's yes (journal, RULED · Enver, 2026-11-10)).
   - **Check:** no file sits where Claude could mistake running for reading.
5. **Do:** write the skill's stage card: each stage's name, whether it talks with the person or runs alone, the
   inputs it reads, the output it must produce, and the check on that output.
   - **Why:** code can only hold what is written down for it; a skill carries the machinery the rig's test dictates
     (COMPASS P-119; rig P4).
   - **Expect:** one card file the runner reads; the skill's prose describes the work inside each stage, not the order.
   - **Check:** every stage names its inputs and a check that reads content, not only that a file exists.
6. **Do:** give the skill a runner that alone writes the run's record (current stage, what passed, when), as an
   append-only file where each line carries a hash of the line before it, so a hand edit breaks the chain and the
   runner refuses to go on.
   - **Why:** a record the AI writes is the AI grading itself, and without the chain nothing can detect a write that
     did not come from the runner. This is the rig's design, not a measured result.
   - **Expect:** the record changes only when the runner runs.
   - **Check:** edit one line by hand in a copy; the runner reports the record damaged and stops.
7. **Do:** keep every fact the skill uses in one place, and derive any other copy from it.
   - **Why:** a fact kept in several files with "remember to update" drifts (census [F3], 177×).
   - **Check:** count every copy, the template included.
8. **Do:** register the move-on commands (/next, and /back to redo) as real commands, and add a plain-speech
   fallback that matches the whole message ("ok next", "move on"), never a keyword.
   - **Why:** an unregistered /next gave "Unknown command" and never reached the hook (rig P3, OBSERVED ONCE), and a
     keyword match moved the run on 6 of 13 ordinary sentences, including "don't move on yet" (rig P3, TESTED).
   - **Expect:** typing /next writes a record line before the AI replies.
   - **Check:** type /next in a real window; a record line appears and no "Unknown command" message.
9. **Do:** add an every-turn hook on the person's message that delivers only the current stage's instructions and runs
   the handover check when the person moves on.
   - **Why:** the hook acts before the AI (rig P2); a push such as "skip the rest" did not move a stage in 10 of 10
     full-window tries at about 80% fill, and once more after a pickup at about 39% (rig P4 for the 10 of 10; rig-findings §3 for the pickup;
     strongest level, one made-up skill — it shows code can hold, not that a push can never win).
   - **Expect:** a push to skip produces at most the work the person asked for; the stage does not move.
   - **Check:** the record shows every advance came through the move-on command.
10. **Do:** have code print an inputs line at the start of each stage, on screen and to the AI — for example
    `INPUTS: 02-evidence.md · 0 lines · EMPTY ✗ (stage paused, tell the person)` — and pause the stage on any empty
    or missing input until the person types /back (redo the stage that made it) or /next (carry on without it).
    - **Why:** without it, 2 of 4 planted bad inputs passed silently; with it, 0 of 5 did (rig P5, TESTED; stand-in
      person, one fill level).
    - **Must / should / may:** a stage SHOULD NOT start on a bad input without the person deciding (RULED · Enver,
      2026-11-05: "code-printed inputs line with pause on empty", `<notes>/system/journal.md`, entry "2026-11-05 | RULED · Enver | skill-system"; skill tester rig plan, Phase 3.0).
    - **Expect:** the stage pauses — that is code's guarantee (5 of 5). The AI also told the person in its own words
      in 3 of 5; "told" was detected by keywords, which missed at least once. An AI that only shows the line is not a
      failed build.
    - **Check:** empty one input on purpose; the stage pauses and the line shows on screen.
11. **Do:** write each stage's content check so it rewards honest work and fails padding — for example, allow a listed
    source outside the expected folder if it is marked, and fail a listed source that no tool call touched. Where a
    check matches text, make it deny by default and watch it refuse a real case first.
    - **Why:** a check that punishes honesty teaches the AI to drop true entries (rig P6, OBSERVED ONCE); a keyword
      match fails open on every spelling not listed (census [F7], 80×).
    - **Expect:** honest output passes; invented or padded output fails with a reason.
    - **Check:** feed the check one known-good input, one honest edge case and one padded case.
12. **Do:** make every script the skill runs fail loudly: a skip, a missing input or a caught error exits non-zero and
    says why.
    - **Why:** an error that looks like success is built on (census [F2], 166×).
    - **Check:** force each failure once and read the exit code.
13. **Do:** for a stage that runs alone, hand over at the end of the turn with a Stop hook whose reason is one short
    line pointing to a handover file that exists only until the next hook call.
    - **Why:** Claude Code shows a Stop hook's reason on screen, so a stage prompt in it puts private instructions and
      code words in front of the person (rig P8, TESTED). The short-reason fix was checked live once.
    - **Expect:** the AI tells the person the stage is finished and which comes next.
    - **Check:** watch one handover live; no prompt text or code word appears on screen.
14. **Do:** add a start-up hook that, in a new window, says where the run is (stage, what is still missing, the inputs
    line) and then waits for the person.
    - **Why:** a new window otherwise starts blank and searches the filesystem (rig P9, TESTED in fresh windows and
      once at about 39% fill; near-full pickup and pickup after auto-compaction UNTESTED).
    - **Expect:** asked "where are we?", the AI answers from the run's files without searching.
    - **Check:** kill a window mid-stage, open a new one in the same folder, ask "where are we?".
15. **Do:** if the skill warns about a filling window, read the fill Claude Code itself reports, never a fixed window
    size or a session's last usage line. Claude Code gives `context_window.used_percentage` only to the status-line
    command, so wrap the status line to write that figure to a file in the run folder, have the warning read the file,
    and stay silent when no figure has arrived — never guess. Show the run's position on the same status line (for
    example `RIG 3/6 options (talk)`).
    - **Why:** measuring against a default window size gave a "196% full" warning in a larger window, and a warning
      that is always on gets ignored (rig-findings §3). The fixed warning was checked on canned input only, never in a
      live full window.
    - **Check:** the warning's figure matches the status line's context percentage; the stage shown changes when the
      stage changes.

### Test a skill

1. **Do:** before any live window, test the runner and its checks with no AI at all: for each check, break a copy on
   purpose and see the check fail.
   - **Why:** a live full-window try costs millions of cached tokens (rig-findings §7); a free test finds broken checks
     first. In the rig, 143 of 144 checks were seen failing, and one could never fail (rig-findings §8).
   - **Must / should / may:** a check that has never been seen failing SHOULD NOT be trusted (COMPASS P-5).
   - **Expect:** every check fails on its broken copy and passes on a known-good one.
   - **Check:** a list of checks, each with the broken copy that made it fail; fix or remove any check that cannot fail.
2. **Do:** launch every test window with the same flags as the person's real launcher, never plain `claude -p`.
   - **Why:** on the rig's machine, plain `claude -p` loaded an older installed plugin instead of the one under test,
     and a write the real guard blocks went through (rig P1, TESTED on that machine and those flags).
   - **Check:** the window's hooks are the ones under test (next step).
3. **Do:** prove the hooks fired: plant a control token a hook must write, and count failures to start from the raw
   log.
   - **Why:** a summary that called failures "startup noise" hid a rig whose hooks never started (rig P1).
   - **Must / should / may:** a result SHOULD NOT be reported without this proof; nothing is done until seen working
     in a way it could not if broken (COMPASS P-5).
   - **Expect:** the token is present and failures to start are zero.
   - **Check:** read the raw hook log, not a summary of it.
4. **Do:** to test a full window, copy one of the person's real sessions with
   `claude -p --resume <id> --fork-session --session-id <new>` plus the step-2 launch flags, inside containment: Claude
   Code's Bash sandbox (`sandbox.enabled`, `allowUnsandboxedCommands: false`, `filesystem.allowWrite` set to the test
   folder) plus a PreToolUse hook that denies Write, Edit and NotebookEdit outside it. Record the original's hash,
   size and modified time before the first try and after the last.
   - **Why:** a copy carries real context honestly, and far more cheaply than filling a window by hand (rig P10,
     TESTED); hooks still fire under the sandbox (rig P1). The first copy of a cold session still writes about 800k
     tokens to cache, so run copies one at a time.
   - **Expect:** the copy answers from context only the original had; the original is unchanged.
   - **Check:** read the settings after launch, not before — a launcher that rewrote the settings file once dropped
     containment silently (skill tester rig plan, 3.0.4); the hash matches before and after.
5. **Do:** measure the copy's real fill from its first call: cache read plus cache write plus uncached input, divided
   by the model's window, worked out in code (COMPASS P-22).
   - **Why:** a session picked as "94% full" loaded only about 39%, because it had been compacted (rig-findings §3).
   - **Check:** the figure comes from the copy's first call, not the original's last usage line.
6. **Do:** plant bad input in the live run, hidden from the AI (the plant's record kept in a private file outside the
   run), and count each plant as refused, told or silent.
   - **Why:** a check tested on its own says nothing about the live run (rig P5, TESTED); a plant the AI can read is
     not hidden (rig P11, OBSERVED ONCE).
   - **Expect:** none silent.
   - **Check:** read each "told" case by hand; keyword detection missed one (rig P5).
7. **Do:** when an AI stand-in plays the person, build it from the person's real messages, leaving out personal
   content (family, health, money, credentials), and label every result as stand-in.
   - **Why:** the stand-in's choices are not the person's (rig P5 limits), and private text must not end up in test
     prompts and transcripts.
8. **Do:** check every helper's report yourself before relying on it.
   - **Why:** a helper's account of its own work is not evidence (census [F8], 70×).
   - **Check:** re-run one claimed check with a stricter filter than the helper used.
9. **Do:** take cost and usage from the transcript's usage figures, not the status line; when starting a window from
   inside a session, set `CLAUDE_CODE_FORCE_SESSION_PERSISTENCE=1`.
   - **Why:** the status line showed $0.00 during real AI turns (rig P11, TESTED); windows started from inside a
     session do not save transcripts otherwise (rig P11, TESTED).
   - **Check:** the new session's transcript file exists.
10. **Do:** report each result with its evidence label and limits, then hand the skill to the person for one real,
    supervised run.
    - **Why:** one made-up skill with a stand-in shows that code can hold, not how often a real skill fails (rig P4
      limits); the real run is the acceptance test (Desired Outcome).
    - **Must / should / may:** a result MUST keep its caveats wherever it is retold (COMPASS P-41).

## When Something Goes Wrong

- **If /next says "Unknown command":** the command is not registered (Build, step 8). No record line was written, so
  nothing moved.
- **If a push makes the stage move:** the advance did not go through code; check the record and the hook (Build,
  step 9).
- **If the record is damaged:** the runner stops the run and tells the person; do not continue the stage by hand.
- **If a fix did not work:** find which seam is failing before the next fix, and sweep the bug's siblings (Principles,
  Building and fixing).
- **If a test has no proof the hooks fired:** the test is invalid; fix the launch (Test, steps 2-3) and rerun. Do not
  report its numbers.
- **If a fill warning looks wrong:** check its source (Build, step 15).
- **If the original session's hash changed:** stop all tries and tell the person.
- **To undo:** a skill's runner, hooks and card are files; revert them through git, or archive them whole (Rules).
  A test on a copy changes nothing outside its folder.
- **Stop and ask the person when:** a test would touch real data or a real session file; a result would change a
  ruling; a change would add a new rule or a new hard block (Vision, the amendment clause); where a change goes is
  unclear.

## Don't Retry

- **Trusting a test whose hooks were never shown to fire** — the old skill tester rig ran with every hook failing to
  start, and its results were retired. Proof: rig-findings §5.
- **Matching by keyword, in a guard or a move-on command** — it fails open on every spelling not listed, fails closed on
  a mere mention, and moved a run on "don't move on yet". Deny by default, and watch it refuse a real case first.
  Proof: census [F7], 80×; rig P3.
- **Keeping one fact in several files with a "remember to update" rule** — a fix leaves the other copies live. Proof:
  census [F3], 177×.
- **Editing by heading text, first match or line number** — it deletes silently. Address by identity. Proof: census
  [F10], 50×.
- **Moving a classifying step to a cheaper model to save money** — the recognition goes with it; check values, not only
  format. Proof: two real ingest incidents (archived SOP, §II.4a).
- **Putting the next stage's prompt in a Stop hook's reason** — it shows on the person's screen. Proof: rig P8.
- **Sizing a window from a session's last usage line, or a default window size** — compaction and larger windows make
  it wrong. Proof: rig-findings §3.
- **Hiding the destination from the AI to stop it working ahead** — it cannot work when the person names the
  destination. Proof: rig P7; rig-findings §4.

## Open Tensions

- **Full strength versus lightest first.** Side A protects reliability: the rig ran only at full strength, on Enver's
  ruling, and a skill carries the machinery the rig's test dictates (COMPASS P-119). Side B protects the person's time:
  friction goes lightest first and a layer that never changes an outcome is dropped (COMPASS P-27, P-123). The rig
  never measured weaker levels, so it cannot say which layers a skill can drop. Status: open — surfaced to Enver, not
  resolved here.
- **A travelling skill versus the shared layer.** Side A: a skill shared with someone without the plugin must carry
  its own parts. Side B: shared tools live once and are never copied (Vision, The Platform). Status: open — UNSURE since
  2026-10-31 (archived SOP §II.5).
- **The Stop hook's red "Stop hook error" label.** Side A: handing over through a Stop hook keeps alone stages moving.
  Side B: the label looks broken to a person. Status: open (rig P8).
- **The Harness brief reaches each window only as a short preview.** Side A: Claude Code caps hook output. Side B: a
  skill may rely on rules the window never saw. Status: open — the platform's to fix (rig-findings §1).
- **Once-per-session guard warnings.** Side A: fewer interruptions. Side B: helpers that come after the first warning
  get no guidance. Status: open (rig P11).
- **Harness end-of-turn reminders inside a skill.** Side A: they catch real problems. Side B: one made the AI repeat a
  long answer mid-skill. Status: open (rig P11).
- **Not yet tested:** weaker levels of code, a real person, a real skill, pickup from a near-full window or after
  auto-compaction. Each stays open until real use or a new test answers it (rig-findings §3, §4).

## Pointers

- **Rulings behind this SOP:** COMPASS P-5, P-22, P-27, P-41, P-42, P-50, P-55, P-65, P-94, P-112, P-119, P-121,
  P-122, P-123, P-134, P-136, P-137; Enver's rig rulings of 2026-11-05 (the skill tester rig plan and the skill-system
  journal); Enver's rulings of 2026-11-10 on the proven lessons, the five carried items and the four shapes (`<notes>/system/journal.md`, entry
  "2026-11-10 | RULED · Enver | skill-system").
- **Vision sections it serves:** The products of the harness (the scaffold); The Platform; View 1 Division of Labor
  and the seam rule; View 2 friction ladder; Document hygiene; the amendment clause and the no-precedence rule.
- **Evidence:** the skill tester rig's findings record, 2026-11-05 (`rig-findings-2026-11`, kept in the project's
  notes, not shipped): rig P1-P11 and §1-§8. That record's own status is a draft awaiting a canon-files run; Enver
  ruled on 2026-11-10 that this SOP is a write-up from it, with no canon-files run (V2 plan, step 7). The failure census
  of 2026-09-05 and the other real-use lessons cited here: the archived SOP,
  `system/_retired-2026-11-10/skill-building-sop.ARCHIVE-2026-11-10.md` (with the old SOP's own history file beside it). This SOP's own history starts fresh at `system/sops/skill-building-sop.history.md` (the header's `history:`).
- **Words used here:** the Vision's Ubiquitous Language (skill, scaffold, seam), plus:
  - **command** — one prompt behind a slash command: one shot, no steps that must hold, no state across turns.
  - **shape** — the frontmatter field naming how a skill is used (Build, step 2).
  - **stage** — one step of a skill, with its own inputs, output and check.
  - **card** — the file listing a skill's stages, which the runner reads.
  - **runner** — the code that alone writes the run's record and moves stages.
  - **record** — the hash-chained file saying where a run is and what passed.
  - **talk stage / alone stage** — a stage that works with the person / one that runs without them.
  - **code word** — a fresh one-time word each stage's handover gives the AI, which the AI must give back so code knows
    the handover reached it; kept on disk only as a hash so the AI cannot copy it from disk and fake the handover.
    SUGGESTED, untested (rig P11; the rig's one check on it could never fail).
  - **levels of code** — how much the rig's code held, each level adding to the one before: order checks (stages in
    order); content checks (each output checked); an every-turn hook; and "signs" (a specific instruction at the moment
    of a block). "The strongest level" means all four together.
  - **plant** — a deliberately bad input placed in a test run, hidden from the AI.
  - **stand-in** — an AI helper playing the person in a test.
  - **routing-eval file** — a small list of prompts that should and should not fire a skill, re-run when its
    description changes.
  - **rig P1-P11** — the numbered findings of the skill tester rig; not COMPASS entries.
  - **census [F1]…** — the numbered failure modes of the 2026-09-05 failure census.

## History

- 2026-11-10 — written fresh from the skill tester rig's final result, COMPASS, the Vision, the skill conformance
  checklist, and the lessons real use proved, each carried on Enver's yes; the previous skills SOP and
  the old skill conformance checklist archived whole (Enver, 2026-11-10; COMPASS P-122). Older wording: the archive named in
  Pointers.
