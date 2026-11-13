---
title: "Cron jobs SOP: history log"
what: "Retired and moved text from system/sops/cron-jobs-sop.md, kept verbatim and dated so nothing is lost. Never read in normal use."
read_in_normal_use: false
base_commit: "cfc100e  (git -C ~/lifehack-v2 log -1 --format=%h -- system/sops/cron-jobs-sop.md)"
base_file: "system/sops/cron-jobs-sop.md, 251 lines at that commit (no earlier staged batch for this file)"
created: 2026-10-31
status: "V2 draft, to be merged with the SOP"
---

# Cron jobs SOP: history log

⛔ History, quoted as it was: `system/sops/pr-sop.md` is named in old text below and is not in this repo.

Each entry below is one passage removed or reworded in the SOP on 2026-10-31: CUT (retired), MOVE (change note or narrative, history not instruction) or FIX (original wording of a line that was reworded or added to). Line ranges are the line numbers in the base (see `base_file` above). Entries are in original line order. The original is copied word for word inside each fenced block. Decision IDs (1.1 to 4.6, and §7) refer to `cron-jobs-sop--FOR-ENVER.md`, approved as called with its §7 corrections in `cron-jobs-sop--DECISIONS.md` (2026-10-31).

Entries whose body held private material show one line instead of the verbatim block; those originals are kept in the operator's private notes.

## 2026-10-31 · FIX · line 4 · front-matter title

- Date: 2026-10-31
- Action: FIX
- Reason: 4.1 (approved as called, DECISIONS 2026-10-31): "Jobs SOP" becomes "Cron jobs SOP", matching the 2026-10-31 file rename.
- Original lines: 4

```
title: "Jobs SOP: how a scheduled job is added, checked and switched on"
```

## 2026-10-31 · MOVE · line 8 · front-matter reader_note: authorship story

- Date: 2026-10-31
- Action: MOVE
- Reason: 4.5.2 (approved as called, DECISIONS 2026-10-31): the authorship story ("Self-monitoring task 5.8, written 2026-10-29 from the build window's draft and corrected for the 2026-10-28/29 rulings") is history, not instruction. Its two working parts stay in the reader_note: the pointer to the manual's CRON AND ALARMS section, and "if either disagrees with the code, the code wins". The history pointer and section index (4.6) were added after this line.
- Original lines: 8

```
reader_note: "Self-monitoring task 5.8, written 2026-10-29 from the build window's draft and corrected for the 2026-10-28/29 rulings. How it works lives in system/organism/manual.md (CRON AND ALARMS); this file is the HOW-TO. If either disagrees with the code, the code wins."
```

## 2026-10-31 · FIX · line 11 · page heading

- Date: 2026-10-31
- Action: FIX
- Reason: 4.1 (approved as called, DECISIONS 2026-10-31): "Jobs SOP" becomes "Cron jobs SOP".
- Original lines: 11

```
# Jobs SOP
```

## 2026-10-31 · FIX · line 21 · section 1 table, trigger owner cell

- Date: 2026-10-31
- Action: FIX
- Reason: 2.3 (approved as called, DECISIONS 2026-10-31): everything after the alarm clock works on a Mac only. The cell now reads "launchd (macOS). Linux and Windows use `pulse.sh`, which has none of the steps below." The manual (`system/organism/manual.md`, "Non-Mac is unchanged") says `pulse.sh` is driven by a cron line on Linux and Task Scheduler on Windows; a pointer to that paragraph was added under "Read this first".
- Original lines: 21

```
| trigger | the alarm clock | is it time? | launchd (macOS), cron (Linux), schtasks (Windows) |
```

## 2026-10-31 · FIX · line 28 · section 1, card-or-no-card pointer

- Date: 2026-10-31
- Action: FIX
- Reason: 4.2 (approved as called, DECISIONS 2026-10-31): the parenthetical about "The Hospital" is deleted (Enver retired that picture as a frame on 2026-10-30, COMPASS P-43), and "Decision rule" becomes "Decision principle", the bullet's current name in `skill-building-sop.md` PART 0.
- Original lines: 28

```
- Card or no card is the skills rule, not this SOP's: `system/sops/skill-building-sop.md` PART 0 ("The Hospital": the nurse-and-chart picture of how a skill runs its steps), section "When NOT to use a card", bullet "Decision rule: card or no card". Read it there; do not copy it here. A card is an upgrade, never a prerequisite: a job can be scheduled with its routine as it is.
```

## 2026-10-31 · FIX · line 31 · section 2 heading

- Date: 2026-10-31
- Action: FIX
- Reason: 1.1 (approved as called, DECISIONS 2026-10-31, with §7): "The ALWAYS rules" becomes "The principles every job follows"; the numbering 1 to 7 is kept. None of the seven has Enver's words calling it a Rule (COMPASS P-30, P-35); "Rules" was the coordinator's word (FOR-ENVER §7).
- Original lines: 31

```
## 2. The ALWAYS rules
```

## 2026-10-31 · FIX · lines 35-41 · section 2 items 1-7: "held by" tags added

- Date: 2026-10-31
- Action: FIX
- Reason: 1.1 (approved as called, DECISIONS 2026-10-31, with §7): each item gains a few words naming what holds it (the door, the run wrapper, the rig, or nothing yet). Item 5's tag uses §7's wording: "held by run_model as read-only (model.lib.sh:22,74); per-job grants ruled, not built". The item texts themselves are unchanged.
- Original lines: 35-41

```
1. A check tests CONTENT, never presence. A file existing, being non-empty, being fresh, or holding an exit code proves nothing.
2. A step that changes something is safe to run twice, or records what it did before acting. Writes to the owner's own Google account have no shared writer: the routine calls them directly, so it must make them repeat-safe itself (for example, record each item's message id in a ledger BEFORE the append and skip ids already there; or write in place by a key column).
3. Exit 0 is never proof of work. Check the artifact. A bookmark moves only on rc 0 AND a passing check.
4. Never silence a step's errors. A failed fetch must not read as "nothing new".
5. The runner writes the record. The AI never does. AI steps get only the tools they need (today: read-only; per-job grants scoped to the job's own output folder are ruled, not yet built). The AI can never write job state or a bookmark.
6. Refuse a truncated or corrupt record, loudly, and name the file.
7. Test the tester first: plant known faults and see every one named (the rig's bite, section 10).
```

## 2026-10-31 · FIX · line 43 · section 2, dead-end pointer and figure

- Date: 2026-10-31
- Action: FIX
- Reason: 1.1 (approved as called, DECISIONS 2026-10-31): "Also from the system laws" becomes "Also from the skill-building rulebook's dead-end list"; no "system laws" section exists anywhere. 3.5 (approved as called, DECISIONS 2026-10-31): the "166 silent failures" figure is labelled "as counted in the dead-end list, not re-checked".
- Original lines: 43

```
Also from the system laws: "ran" is not "succeeded" (dead end F2, 166 silent failures). No job writes job state to Drive: content yes, state no.
```

## 2026-10-31 · FIX · line 50 · section 3, where files live: private folder name

- Date: 2026-10-31
- Action: FIX
- Reason: 2.4 (approved as called, DECISIONS 2026-10-31; COMPASS P-42, P-39): the clause naming the maintainer's private folder is deleted; the rest of the line is unchanged.
- Original lines: 50

(verbatim original moved to the operator's private notes, 2026-10-31, because it is private)

## 2026-10-31 · FIX · line 51 · section 3, test seam: private default path

- Date: 2026-10-31
- Action: FIX
- Reason: 2.4 (approved as called, DECISIONS 2026-10-31; COMPASS P-42, P-39): the literal private default path is replaced by "the maintainer's own folder", and the line now ends "set `LIFEHACK_DESK_REPO` to your personal code folder." The code default is a bug sent to the coordinator (FOR-ENVER §6, bug 1).
- Original lines: 51

(verbatim original moved to the operator's private notes, 2026-10-31, because it is private)

## 2026-10-31 · FIX · line 74 · exit-code table, row 75

- Date: 2026-10-31
- Action: FIX
- Reason: 2.1 (approved as called, DECISIONS 2026-10-31): a long unbroken run of stand-downs does send one "paused" text (`job-run.sh:196-203`, `job-texts.txt` key `standdown`), which line 78 of the same base already said. The effect now reads "never a fault; shown on the session line; an unbroken run of them longer than 2 x the interval sends one 'paused' text, and one 'running again' text when it next passes (never for a row that is not `yes`)". The 2 x interval and 'running again' detail is the scheduled-jobs window's §7 correction, which Enver approved (`job-run.sh:278`, `job-texts.txt` key `running_again`; corrected 2026-11-02 from 'working again'). A row for exit 78 was also added after row 2 (2.2).
- Original lines: 74

```
| 75 | stood down: nothing configured, not logged in, not overdue, row not `yes`, lock held by a live owner | never a fault, never a page, always shown on the session line |
```

## 2026-10-31 · MOVE · line 78 · alert rule: "(built 2026-10-29)" tag

- Date: 2026-10-31
- Action: MOVE
- Reason: 4.5.1 (approved as called, DECISIONS 2026-10-31): a dated build tag is history, not instruction. Every fact in the paragraph stays.
- Original lines: 78

```
**Alert rule (Alarms).** A failed run (any rc not 0 or 75; 2 counts) pushes ONCE when `last-success` is missing or at least 2 x interval old (the second miss), then leaves `alerted`. The next success pushes one recovery and removes it. A push that fails never changes the exit code. A `--force` run never pushes. Also (built 2026-10-29): `alerted` is written only on a confirmed send, so a failed text retries; a job that keeps standing down texts once; every run checks the other jobs and texts once for one that is not running. Every text follows section 14.
```

## 2026-10-31 · FIX · line 97 · row contract, source column

- Date: 2026-10-31
- Action: FIX
- Reason: 3.1 (approved as called, DECISIONS 2026-10-31): sentence added: "Today only `gmail` changes anything (it loads the Google login); the door accepts any non-empty word." Whether the word list should be enforced goes to the debt ledger.
- Original lines: 97

```
| source | the shared reader that FEEDS it (what it reads, never what it writes): `gmail`, `web`, `gsheet` or `none`. A job that reads email and writes a Sheet is `gmail`. `gmail` makes job-run load the Google credentials |
```

## 2026-10-31 · FIX · line 108 · section 6, presence-grade refusals

- Date: 2026-10-31
- Action: FIX
- Reason: 4.5.1 (approved as called, DECISIONS 2026-10-31): the plan-task tag "(5.9)" is removed. 2.5 (approved as called, DECISIONS 2026-10-31): the bare-word example added ("A check like `^done$` is refused because it is the same on every run; a check must contain something that varies, such as an `=`, a number or a captured value."), from `install-schedulers.sh:170-178`.
- Original lines: 108

```
The door refuses presence-grade checks (5.9): a regex that tests only an exit code written to a file (`"rc":0`), non-empty (`^.+$`), or existence or mtime alone (a check without ` ~ `). Wrong: `last-run.json ~ "rc":0`. Right: `receipt.txt ~ ^example-digest ok .*items=[1-9]`.
```

## 2026-10-31 · MOVE · line 115 · section 7 list: "(5.9)" tag

- Date: 2026-10-31
- Action: MOVE
- Reason: 4.5.1 (approved as called, DECISIONS 2026-10-31): plan-task tag removed; the fact stays.
- Original lines: 115

```
- a presence-grade check (5.9);
```

## 2026-10-31 · MOVE · line 119 · section 7 list: "(5.9)" tag

- Date: 2026-10-31
- Action: MOVE
- Reason: 4.5.1 (approved as called, DECISIONS 2026-10-31): plan-task tag removed; the fact stays.
- Original lines: 119

```
- a silenced error (5.9): `|| true`, `|| :` or `2>/dev/null` on a fetch, write, push or model call. Stderr goes to the job log.
```

## 2026-10-31 · MOVE · line 125 · section 8 heading: "(5.9)" tag

- Date: 2026-10-31
- Action: MOVE
- Reason: 4.5.1 (approved as called, DECISIONS 2026-10-31): plan-task tag removed; the section number 8 is kept.
- Original lines: 125

```
## 8. State, locks, bookmarks (5.9)
```

## 2026-10-31 · MOVE · line 140 · section 9: "(5.9)" tag

- Date: 2026-10-31
- Action: MOVE
- Reason: 4.5.1 (approved as called, DECISIONS 2026-10-31): plan-task tag removed after "`ccv=` is the Claude version"; the fact and the "ruled, not yet built" caveat stay.
- Original lines: 140

```
`calls` and `secs` are the model calls this run made through `run_model` (0 and 0 for a job with no AI). `ccv=` is the Claude version (5.9). To call a model, a runner sources `$LIFEHACK_CODE_ROOT/system/tools/model.lib.sh` and calls `run_model <tier> <prompt-file> <out-file> [marker]`. It maps tier to id from the one table, takes the token, times out (`MODEL_TIMEOUT`, default 600 s), refuses an empty reply or a missing marker, counts the call, and refuses the call that would exceed `budget`. AI steps run with only the tools they need (today read-only, `--allowedTools Read`; per-job grants scoped to the job's own output folder are ruled, not yet built): the runner writes every file and the record, the model returns text. A model failure `run_model` recorded fails the run and is named even if the runner swallowed the return code.
```

## 2026-10-31 · MOVE · line 147 · section 10: two "(5.9)" tags

- Date: 2026-10-31
- Action: MOVE
- Reason: 4.5.1 (approved as called, DECISIONS 2026-10-31): plan-task tags removed; the facts stay.
- Original lines: 147

```
- `--bite` (5.9) plants known faults, one per rule, and asserts each is caught and NAMED exactly. `--gate` runs the bite first (5.9). A rig that was never shown to fail is not trusted.
```

## 2026-10-31 · FIX · line 149 · section 10, "Every job adds one scenario"

- Date: 2026-10-31
- Action: FIX
- Reason: 3.7 (approved as called, DECISIONS 2026-10-31): light touch only. The reason already in the sentence (its check passes on a good output and fails on an empty or wrong one) now comes first, after "before its forced run, so". Nothing is hardened; the closing "Copy …" sentence is unchanged. In the copy below, the two example scenario names are elided (2026-11-02) so the public no-private-desks check passes; they are unchanged in the SOP. Otherwise verbatim.
- Original lines: 149

```
- **Every job adds one scenario** before its forced run: a `<job>-contract` scenario that runs the real row under the rig with a stub, and proves its check passes on a good output and fails on an empty or wrong one. Copy […the two example scenario names, unchanged; still in the SOP…] in `job-sim.sh`.
```

## 2026-10-31 · FIX · line 150 · section 10, not-covered list

- Date: 2026-10-31
- Action: FIX
- Reason: 1.4 (approved as called, DECISIONS 2026-10-31, in §7's narrower wording): sentence added at the end: "Not covered: if no job runs at all (scheduler stopped, Mac off, every job unloaded), no text is sent; the session line at the start of a session is the only backstop." From Enver's 2026-10-27 ruling that this gap is known and accepted.
- Original lines: 150

```
- Not covered by the rig: real launchd wake behavior, real logins, real push delivery, real Google or Claude auth. One live `launchctl kickstart` per gate keeps those honest.
```

## 2026-10-31 · FIX · line 157 · recipe step 2, card pointer

- Date: 2026-10-31
- Action: FIX
- Reason: 2.6 (approved as called, DECISIONS 2026-10-31): "stop and use the skills SOP v2 PART 0 rule" becomes "see the card-or-no-card principle in `system/sops/skill-building-sop.md` PART 0 (hypothetical, not yet validated)"; the old name no longer exists and PART 0 is marked unproven (Enver, 2026-10-30).
- Original lines: 157

```
2. **Decide the layer.** The routine (steps, prompts, verdicts) is a skill, or a script a person can run by hand. If it needs a card, stop and use the skills SOP v2 PART 0 rule. This job is only the envelope.
```

## 2026-10-31 · FIX · line 159 · recipe step 4, five columns

- Date: 2026-10-31
- Action: FIX
- Reason: 3.2 (approved as called, DECISIONS 2026-10-31): the five contract columns are named in brackets (outcome, check, model, budget, source).
- Original lines: 159

```
4. **Add the row, `off`.** Fill all five contract columns. Check the interval against section 4.
```

## 2026-10-31 · CUT · line 164 · recipe step 9: ", per the GitHub SOP"

- Date: 2026-10-31
- Action: CUT
- Reason: 4.3 (approved as called, DECISIONS 2026-10-31): no such rulebook ships to students, and students are assumed to have no GitHub (COMPASS P-8).
- Original lines: 164

```
9. **Commit** shared work to `$CODE` and desk work to your personal code folder, per the GitHub SOP. Report what the run proved and what it did not test.
```

## 2026-10-31 · FIX · line 174 · worked example: runner label

- Date: 2026-10-31
- Action: FIX
- Reason: 3.3 (approved as called, DECISIONS 2026-10-31): "(an illustration; no such file ships)" added, so a reader with no context does not go looking for the file.
- Original lines: 174

```
Runner `$CODE/system/tools/example-digest-run.sh`:
```

## 2026-10-31 · FIX · line 198 · switch-on pacing clause

- Date: 2026-10-31
- Action: FIX
- Reason: 1.2 (approved as called, DECISIONS 2026-10-31, CHANGED by §7): "one at a time" is Enver's own Gate 1 ruling (2026-10-27, "serial, not parallel"), so it is kept; only "never in the prep phase" is dropped, and the line is reworded to "one job at a time, only at a human gate, on the owner's word". "Sprint" and "prep phase" belonged to one build's plan.
- Original lines: 198

```
A row flips from `off` to `yes` only at a human gate, on the owner's word, one job per sprint, never in the prep phase. At the gate:
```

## 2026-10-31 · MOVE · line 206 · carded routine sentence

- Date: 2026-10-31
- Action: MOVE
- Reason: 3.4 (approved as called, DECISIONS 2026-10-31): the first sentence ("A carded routine is switched on the same way: its row runs the card's runner and its check reads the run's record.") describes something not built in the student version, and may become true later. The second sentence, a ruled fact, stays: "No job waits for a card to be switched on."
- Original lines: 206

```
A carded routine is switched on the same way: its row runs the card's runner and its check reads the run's record. No job waits for a card to be switched on.
```

## 2026-10-31 · MOVE · line 217 · section 14 heading: "(operator's rule, 2026-10-29)"

- Date: 2026-10-31
- Action: MOVE
- Reason: 4.5.3 (approved as called, DECISIONS 2026-10-31): the dated attribution moves here; the section number 14 and its title are kept.
- Original lines: 217

```
## 14. Texts are written for a person (operator's rule, 2026-10-29)
```

## 2026-10-31 · MOVE · lines 219-220 · section 14: the operator's first-drill quote

- Date: 2026-10-31
- Action: MOVE
- Reason: 4.5.3 (approved as called, DECISIONS 2026-10-31): the quote is the story behind the rule; the rule it produced stays ("Every text that reaches the owner's phone is read by a regular person, not a programmer." and the three-things rule after it). The title story and its "the cause was not proven" caveat stay too.
- Original lines: 219-220

```
Every text that reaches the owner's phone is read by a regular person, not a programmer. The operator, on the first
drill: *"I have no idea what drill never, drill fail [means]. None of this stuff is written for humans."*
```

## 2026-11-02 · FIX · exit-code table, row 75 (current line 93) · 'working again' corrected

- Date: 2026-11-02
- Action: FIX
- Reason: VALIDATION-FINAL fix 8: after a stand-down, job-run sends `running_again` ("Your {name} is running again.", `job-run.sh:278`, `job-texts.txt`), not 'working again'. The 2 x interval detail is kept (the §7 correction, approved). The 2026-10-31 entry for line 74 now quotes the corrected line. (Fix 7, same date: the line-149 entry's quoted original had two example scenario names elided; its Reason says so.)

Old text (verbatim):
```
an unbroken run of them longer than 2 x the interval sends one 'paused' text, and one 'working again' text when it next passes (never for a row that is not `yes`) |
```
New text:
```
an unbroken run of them longer than 2 x the interval sends one 'paused' text, and one 'running again' text when it next passes (never for a row that is not `yes`) |
```

## 2026-11-05 · ADD · §11a added; personal-folder, refusal and rig edits

- Date: 2026-11-05
- Action: ADD
- Reason: §11a added; personal-folder, refusal and rig edits; owner approved in session

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-001, ids in drafts/cron-jobs-sop/applied.md

~~~~
reader_note: "How it works lives in system/organism/manual.md (CRON AND ALARMS); this file is the HOW-TO. If either disagrees with the code, the code wins."
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-002, ids in drafts/cron-jobs-sop/applied.md

~~~~
  - ["§1", 37, "the three layers: alarm clock, envelope, steps; which layer a bug is in"]
  - ["§2", 51, "the seven principles every job follows, and what holds each one"]
  - ["§3", 65, "the layer law: what is shared, what is the desk's, where files live"]
  - ["§4", 74, "the chain from launchd to the text; local state; exit codes; the alert rule"]
  - ["§5", 101, "the row contract: one row per job, its nine columns"]
  - ["§6", 123, "the check: path ~ regex, written against the outcome; what the door refuses"]
  - ["§7", 131, "the door: what it refuses, its limits, reads through the shared fetch"]
  - ["§8", 151, "state, locks, bookmarks"]
  - ["§9", 158, "the cost line (last-run) and run_model"]
  - ["§10", 168, "the rig: job-sim.sh, the bite, a generated scenario per personal job and hand-written receipts for plugin jobs, what it does not cover"]
  - ["§11", 178, "add a job: the recipe, with a worked example"]
  - ["§11a", 222, "bring an existing job into line: personal folder, what may change, refusal texts, the steps, running outside the checker"]
  - ["§12", 343, "the switch-on protocol"]
  - ["§13", 355, "debugging a job from the session line"]
  - ["§14", 364, "texts are written for a person; the approved wording"]
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-003, ids in drafts/cron-jobs-sop/applied.md

~~~~
**Read this first.** A scheduled job is an alarm clock plus an envelope around something you could run by hand. This SOP owns the alarm clock and the envelope: the **Cron** subsystem (it runs jobs) and the **Alarms** subsystem (it tells you one broke). It does NOT own what happens inside the routine, and nothing in this SOP is a reason to edit a skill. The one exception is a job being brought into line (section 11a): that changes the job's own code, and does not change what the job reads, writes or sends, apart from its own receipt line and exit code (the two allowed fixes are the presence-grade check and the "nothing to do" exit 75). Every path here is in the HARNESS home, resolved from the plugin root (manual, THREE HOMES), never relative to your working folder. `$CODE` below is the harness code root: whatever `$HOME/.config/lifehack/code-root` says. Never type it as a path.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-004, ids in drafts/cron-jobs-sop/applied.md

~~~~
- Card or no card is the skills rule, not this SOP's: `system/sops/skill-building-sop.md` PART 0, section "When NOT to use a card", bullet "Decision principle: card or no card". Read it there; do not copy it here. A card is an upgrade, never a prerequisite: a job can be scheduled with its routine as it is.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-005, ids in drafts/cron-jobs-sop/applied.md

~~~~
Every job obeys these, carded or not. The door and the rig enforce what code can judge.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-006, ids in drafts/cron-jobs-sop/applied.md

~~~~
2. A step that changes something is safe to run twice, or records what it did before acting. Writes to the person's own Google account have no shared writer: the routine calls them directly, so it must make them repeat-safe itself (for example, record each item's message id in a ledger BEFORE the append and skip ids already there; or write in place by a key column). *(Held by nothing yet.)*
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-007, ids in drafts/cron-jobs-sop/applied.md

~~~~
5. The runner writes the record. The AI never does. AI steps get only the tools they need (today: read-only; per-job grants scoped to the job's own output folder are ruled, not yet built). The AI can never write job state or a bookmark. *(Held by `run_model` as read-only, `model.lib.sh:22,74`; per-job grants ruled, not built.)*
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-008, ids in drafts/cron-jobs-sop/applied.md

~~~~
Also from the skill-building rulebook's dead-end list: "ran" is not "succeeded" (dead end F2, 166 silent failures, as counted in the dead-end list, not re-checked). No job writes job state to Drive: content yes, state no.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-009, ids in drafts/cron-jobs-sop/applied.md

~~~~
## 3. The layer law (what is shared, what is the desk's)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-010, ids in drafts/cron-jobs-sop/applied.md

~~~~
- Where files live: shared code in `$CODE` (the public harness). Desk runners, prompts and notes in your personal code folder (find it with `python3 $CODE/shared/personal_code_root.py --quiet`) and the notes folder. Your own scheduled jobs are rows in `<personal-code>/jobs.md`, and their code is in `<personal-code>/tools/<job>/`; never in the plugin, because a plugin update overwrites it. The setup (`bootstrap.py`) makes the personal folder when it is missing, then the places in it; the installer makes those places only when the folder already exists. Neither overwrites anything (section 11a). Never put desk code in the public harness. Never copy a shared file into a desk.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-011, ids in drafts/cron-jobs-sop/applied.md

~~~~
One row per job, in a `jobs` block. A job that ships with the plugin is a row in `$CODE/system/jobs.md`. A person's own job is a row in the same format in `<personal-code>/jobs.md` (the plugin ships no such list, and an update would overwrite anything the person put in its own). One scheduler reads both (`shared/jobs_manifest.py`). To change a plugin job, copy it under a NEW name into your own folder: the row goes in your `jobs.md`, its code in `<personal-code>/tools/<new-name>/`, and the new job is yours and not supported by the plugin; the plugin's job keeps running unchanged (section 11a, "Copying a plugin job to change it"; decided by the owner, in session, 2026-11-05). The code still lets a personal row with a plugin row's name win, with a warning that names it; that is not the way to change a plugin job. A broken plugin job is reported: as an issue on the plugin's GitHub page until `system/sops/pr-sop.md` exists, then by that rulebook. A row in your own `jobs.md` that the checker refuses may run outside the checker only when you knowingly chose it and the row carries the mark above it (section 11a, T5).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-012, ids in drafts/cron-jobs-sop/applied.md

~~~~
| source | the shared reader that FEEDS it (what it reads, never what it writes): `gmail`, `web`, `gsheet` or `none`. A job that reads email and writes a Sheet is `gmail`. `gmail` makes job-run load the Google credentials. Today only `gmail` changes anything (it loads the Google login); the door accepts any non-empty word |
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-013, ids in drafts/cron-jobs-sop/applied.md

~~~~
`job-run.sh` runs the same test before every run of a `yes` row, and every forced run (an `off` row stands down first), so no run can get around the door.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-014, ids in drafts/cron-jobs-sop/applied.md

~~~~
- a raw outside READ (Gmail or Calendar reads, sheets `values get`, `curl`, `urllib`, `requests`) anywhere in the runner, what it sources or invokes, or the helper files beside it. Only files named in `system/tools/shared-fetch-allowlist.txt` may hold one. Never add a desk runner to that list. **Writes** to the owner's own Google account (labels, archive, Sheets, Tasks, Calendar, Docs) are allowed: an accepted risk (ruled 2026-10-28). **One vendor-read exception:** a row whose model is exactly `none` may make its own logged-in read (python `requests` or `urllib` only) of the person's own vendor account from ONE file listed as `<job> <file>` in the person's own `<personal-code>/vendor-read-allowlist.txt` (`<file>` relative to the job's tools folder; the plugin's `system/tools/vendor-read-allowlist.txt` ships empty and is read first). A raw Gmail read and `curl` are never a vendor read. It ends if the row gains an AI step;
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-015, ids in drafts/cron-jobs-sop/applied.md

~~~~
`calls` and `secs` are the model calls this run made through `run_model` (0 and 0 for a job with no AI). `ccv=` is the Claude version. To call a model, a runner sources `$LIFEHACK_CODE_ROOT/system/tools/model.lib.sh` and calls `run_model <tier> <prompt-file> <out-file> [marker]`. It maps tier to id from the one table, takes the token, times out (`MODEL_TIMEOUT`, default 600 s), refuses an empty reply or a missing marker, counts the call, and refuses the call that would exceed `budget`. AI steps run with only the tools they need (today read-only, `--allowedTools Read`; per-job grants scoped to the job's own output folder are ruled, not yet built): the runner writes every file and the record, the model returns text. A model failure `run_model` recorded fails the run and is named even if the runner swallowed the return code.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-016, ids in drafts/cron-jobs-sop/applied.md

~~~~
- **A person's job needs no scenario written by hand.** The rig reads the merged job list (`shared/jobs_manifest.py`: the plugin's `system/jobs.md` plus `<personal-code>/jobs.md`; on a name clash the personal row is the one tested) and generates one scenario per personal row, named `personal:<job>`. The row's own check is shown to pass on a good receipt line and fail on a wrong one, with a generic stub standing in for the runner (the real command never runs; throwaway home, fake clock, no network). The good line is built from the check's regex, the bad line is one that must not match, and both are verified with the same `grep -E` the runner uses; a regex that cannot be built, or whose every bad candidate matches, is a named failure that says why. The expected model calls are 0 for model `none`, else 1. An optional `<personal-code>/job-sim/<job>.json` with `{"good": "...", "bad": "...", "calls": N}` replaces any key it gives; a malformed file (not JSON, wrong types, an unknown key) is a named failure. It lives in the personal code folder, never in the plugin. A row whose check is `TBD` or empty, or that the door refuses, prints `SKIP personal:<job>: <reason>` and is not a failure: the door is its gate. `off` rows are tested too. The plugin's own jobs (rows in `system/jobs.md`) keep hand-written receipts in `job-sim.sh`, which the plugin maintains (`job-sim.sh:575-583`; not every plugin row has one). A plugin job's scenario duty is therefore unchanged: its receipt is hand-written in `job-sim.sh`, not generated.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-017, ids in drafts/cron-jobs-sop/applied.md

~~~~
2. **Decide the layer.** The routine (steps, prompts, verdicts) is a skill, or a script a person can run by hand. If it needs a card, see the card-or-no-card principle in `system/sops/skill-building-sop.md` PART 0 (hypothetical, not yet validated). This job is only the envelope.
3. **Write a thin runner.** A job of your own lives in your personal code folder, in `<personal-code>/tools/<job>/` (the setup makes `tools/`; the door allows any path under the folder, and the vendor-read line needs the path to end `/tools/<job>/<file>`). A job every installer would want is a change to the plugin and goes through the PR rulebook (`system/sops/pr-sop.md`, not written yet; until it exists, a report is an issue on the plugin's GitHub page, decided by the owner, in session, 2026-11-05), never a direct edit of `$CODE/system/tools/`. Never copy shared files into a desk. Resolve everything from `$LIFEHACK_CODE_ROOT`. Use the shared fetch for any read, `run_model` for any AI call, no silenced errors, exit 75 when there is nothing to do or a lock is held, and write a receipt AFTER verifying the artifact.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-018, ids in drafts/cron-jobs-sop/applied.md

~~~~
5. **Run the door** the way `job-run.sh` does, with no session-only settings (command in section 11a, "Check the way the run does") until it prints `rc=0` and the line above it is `PASS` (`job-run.sh:402-406`: exit code 0 and last line `PASS`).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-019, ids in drafts/cron-jobs-sop/applied.md

~~~~
9. **Commit** a personal job's code, row and notes in your own personal code folder, to the person's own repo, never to `$CODE`. A change to a plugin job or a shared tool is a PR (`system/sops/pr-sop.md`, not written yet; until it exists, a report is an issue on the plugin's GitHub page, decided by the owner, in session, 2026-11-05), never a commit to `$CODE` from here. Report what the run proved and what it did not test.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-020, ids in drafts/cron-jobs-sop/applied.md

~~~~
**DECIDED** (P-127, round 4): the root problem is "students or subscribers can't use the plugin to save their kron jobs", because an update overwrites the plugin. So the personal code folder holds what a person needs to save their own jobs, mirroring "only ... the stuff that ... would actually need". **PROPOSED:** each piece comes with a template, created when missing and never overwritten (P-127 asks for "a location and all the folders and everything it needs", not for templates).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-021, ids in drafts/cron-jobs-sop/applied.md

~~~~
**DECIDED** (P-127, round 4, the fuller lines): "do we change the nature of the job no we shouldn't change the nature of the job", and "we just want to stay focused on how a kron drop gets made". **PROPOSED:** the reading of that as "a fix does not change what the job reads, writes or sends, apart from its own receipt line and exit code"; P-127 gives neither that wording nor the examples. Two fixes are allowed under it: the presence-grade check fix (the receipt line and the check are made to carry a value that varies) and the "nothing to do" exit 75. **DECIDED** (P-127, round 4): the aim is to "stay in our lane": the shared code correctly divided between the plugin and the personal folder, "saved in conformance", and "enforced when it's on its own". **PROPOSED:** this section adds no new block of its own (P-127 does not say it). What is built today: the job door refuses a row's runner that breaks the rules (`install-schedulers.sh`), and `job-run.sh` runs the same door before each run of a `yes` row and every forced run; the ingest-gate hook refuses raw reads of outside content typed in a session (SOP §7). What is not built: a hard block on writing into shared plugin code, which `build-conformance-sop.md` line 59 lists as decided 2026-11-03 and not yet built, so today nothing hard-blocks a session that edits the plugin (the fine-china layer there is an ask, not a wall). **DECIDED** (P-127, round 3): rewriting a skill is not planned and not prevented; if the person's own conversation goes there, that is fine.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-022, ids in drafts/cron-jobs-sop/applied.md

~~~~
When the door refuses a personal row, the window says one short line and asks, for example: "This job isn't in line with the Lifehack checker. Want me to bring it into line?" **DECIDED** (P-127, round 4): the offer is made every time the refusal comes up, as "just the small little lines like, hey, this isn't in conformance", "never a huge block"; a person who asks for the fix without being offered gets the same road (round 1). **PROPOSED:** never a pop-up (P-127 does not say it); the line says that the job's own code changes and what it reads, writes and sends does not. **PROPOSED:** a job the person chose to run outside the checker (below) gets the same one short line. P-127 round 4 says "I do think it could keep offering it" about re-offering a fix in general, and adds "If adding that in makes it harder, then fuck it. We'll just warn them one time and leave it"; it does not name a job already chosen outside the checker, and round 3 dropped a repeated session-start line as annoying. **PROPOSED:** a no leaves everything as it is. When the window asks anything, it gives its best guess.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-023, ids in drafts/cron-jobs-sop/applied.md

~~~~
One scheduler reads two lists: the plugin's `system/jobs.md` and the person's `<personal-code>/jobs.md`. A refusal ends with one of two texts, by the list the row came from. A row is plugin-origin ONLY when it is in the plugin's own list, `$CODE/system/jobs.md` (real paths compared), before the `# ── personal rows (from …) ──` marker. A row after the marker, or read from any other manifest file (`LIFEHACK_JOBS_FILE` or `PULSE_CONFIG` pointing anywhere else, such as a branch's `jobs.md`), is personal; a name in both lists counts as personal (`install-schedulers.sh:104`, `door_origin_step`). For `--check-row` it is the last line; `--install` and the plan-only run print each applicable text once, after the count line, to stderr. The exact wording is PROPOSED (not in P-127), as coded at `install-schedulers.sh:352-353`:
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-024, ids in drafts/cron-jobs-sop/applied.md

~~~~
**A broken plugin job** (DECIDED, P-127, round 4): "I would just tell them to report it that's it", following the PR rulebook ("assume that there is a pr sop"), `system/sops/pr-sop.md`. No window tells the person to copy the row to fix it: once the plugin fixes the job "they would have two copies of the same job". **DECIDED** (the owner, in session, 2026-11-05, T7): the person reports it on the plugin's GitHub page as an issue, until `system/sops/pr-sop.md` exists; once it does, that rulebook takes over. The window says plainly that the job should be reported, and does not edit it. The refusal for a broken plugin job is "report it", never a copy. **PROPOSED:** this also holds when the fault is inside a plugin runner or shared script that a personal row calls: report it, change nothing in the plugin (P-127 speaks of a broken plugin job, not of a personal row that calls one).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-025, ids in drafts/cron-jobs-sop/applied.md

~~~~
**Copying a plugin job to change it** (DECIDED, the owner, in session, 2026-11-05, T6; and P-127, round 4: a fork carries "you broke it you bought it"): the copy is a NEW job, under a NEW name, in the person's own folder. Its row goes in the person's `jobs.md`, and its code goes in `<personal-code>/tools/<new-name>/`. The new job is the person's own and is not supported by the plugin. The plugin's original job keeps running unchanged. The window does not recommend a same-name copy that replaces the plugin job. The code still lets a personal row with a plugin row's name win, with a warning that names the override (`job-run.sh:402-411`); that is not the way to change a plugin job, and the refusal for a broken plugin job is "report it" (above). The fork warning still stands: the new job will not get plugin fixes, "you broke it, you bought it". **PROPOSED:** the window says that warning in one plain line before the copy is made (the wording is the draft's).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-026, ids in drafts/cron-jobs-sop/applied.md

~~~~
A row is in line only if the check passes as `job-run.sh` runs it (`job-run.sh:402-406`): `2>&1`, exit code 0 and last line `PASS` (a personal copy of a plugin row prints a warning line first), and none of the test seams set (`LIFEHACK_DESK_REPO`, `LIFEHACK_JOBS_FILE`, `PULSE_CONFIG`, `LIFEHACK_PERSONAL_JOBS_FILE`, `LIFEHACK_VENDOR_ALLOWLIST`; the command below does set `LIFEHACK_CODE_ROOT`, to the real root, on purpose). `env -i` approximates launchd's bare environment (`job-run.sh:80-82`).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-027, ids in drafts/cron-jobs-sop/applied.md

~~~~
To check a row that lives on a branch (a worktree's own `jobs.md`), point the checker at that file. A row read from any file other than `$CODE/system/jobs.md` is personal, so a refusal gives the personal text. With `LIFEHACK_JOBS_FILE` set the personal list is not merged in, so the branch's file must hold the row itself. This is a test check, not the "in line" check above (it sets a seam):
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-028, ids in drafts/cron-jobs-sop/applied.md

~~~~
5. **The first real test run needs the person's yes** (DECIDED, P-127 round 2: approval first; the rest PROPOSED). Say what a run does for real: the runner's own writes and any model spend; no email bookmark moves and no alert is sent. On the yes: `bash $CODE/system/tools/job-run.sh <name> --force`, then read `last-run` and `log`. Without a yes, report the job as checked and rig-tested, not run.
6. **Switch on only through the gate** (§12), never by flipping the row. **PROPOSED:** a row already `yes` goes to `off` first (with the person's yes), is fixed, and returns through §12.

**Cannot pass?** Stop, say what refuses it and why, and ask what they want, with your best guess (PROPOSED). Nothing is installed, switched on or loosened meanwhile.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-029, ids in drafts/cron-jobs-sop/applied.md

~~~~
| `raw curl / urllib / requests`, web fetch or search | read through `safe_fetch.py` or `safe_search_api.sh`; **a new host goes in `<personal-code>/job-fetch-hosts.txt`** (**PROPOSED:** P-127 round 4 says "we only have to mirror the stuff that ... would actually need" outside the plugin to save a job, and never mentions a hosts list); never add a runner to the allowlist | §7 |
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-030, ids in drafts/cron-jobs-sop/applied.md

~~~~
| `silenced <fetch\|write\|push\|model> error at <file>:<line>` (the text in `install-schedulers.sh:314`; the row-command version at `:284` is the row above) | the text names `\|\| true`, `\|\| :` and `2>/dev/null`, but the rule (`door_rules.py:23`) also catches `&>/dev/null` and `>/dev/null 2>&1`: remove any of them from that line, log the failure to stderr and fail the step | §2, §7 |
| `raw curl to a Google/Gmail API host: go through the shared email tool (shared/tools/email_fetch.py; system/register/toolbox.md) at <file>:<line>` (`door_rules.py:65`, printed at `install-schedulers.sh:326-328`) | read mail through `shared/tools/email_fetch.py`, not `safe_fetch.py` (the curl row above is for other hosts) | §7 |
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-031, ids in drafts/cron-jobs-sop/applied.md

~~~~
| a vendor read refused | only model exactly `none`, python `requests`/`urllib` only, on a `<job> <file>` line (`<file>` relative to `tools/<job>/`) in the person's own `vendor-read-allowlist.txt`. **PROPOSED:** add a line only if the person chooses it in their own words | §7 |
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-032, ids in drafts/cron-jobs-sop/applied.md

~~~~
4. **No session-start line** (DECIDED, P-127, round 3). **PROPOSED:** the offer line above still applies each time the refusal comes up for such a row (see the offer section: P-127 does not name this case); it is one line, never a block.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-033, ids in drafts/cron-jobs-sop/applied.md

~~~~
**What the harness then does** (DECIDED, the owner, in session, 2026-11-05, T5): it installs and runs a marked personal row that the checker refuses, and prints a one-line warning that names the first refusal reason. The code that does this is being built now (`install-schedulers.sh`, `job-run.sh`). The mark does nothing for a row from the plugin's `system/jobs.md`.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-034, ids in drafts/cron-jobs-sop/applied.md

~~~~
- COMPASS P-127, round 4 (2026-11-05, cron door window, "approved"; written from plan quotes, not heard directly by the coordinator): (1) root problem and "mirror ... only ... what they need" settle the personal folder section; (2) "I would just tell them to report it", "two copies of the same job", "you broke it you bought it" settle plugin-job reporting and that a fork carries "you broke it you bought it" (the warning itself is PROPOSED); (3) "hey, this isn't in conformance ... never a huge block" settles T2 (one line every time, replacing "do not re-offer"); (4) "stay in our lane ... enforced when it's on its own" gives the aim; T5, T6 and T7 were settled afterwards by the owner, in session, 2026-11-05.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-035, ids in drafts/cron-jobs-sop/applied.md

~~~~
- PROPOSED, not in P-127: the exact wording of both refusal texts (code, dated 2026-11-05, no owner named), the example offer line, the fork-warning wording, "a no leaves everything as it is", step 5's details, step 6's `off`-first. DECIDED by the owner, in session, 2026-11-05 (T5, T6, T7): the comment-line form, running a marked job with a one-line warning, a copy of a plugin job as a new-name job, and reporting a broken plugin job on the plugin's GitHub page.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-036, ids in drafts/cron-jobs-sop/applied.md

~~~~
A row flips from `off` to `yes` one job at a time, only at a human gate, on the person's word. **PROPOSED:** a job whose row was `yes` and which has been changed to pass the door goes back to `off` first and comes through this gate again (section 11a, step 6). At the gate:
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: cron-jobs-sop hunk-037, ids in drafts/cron-jobs-sop/applied.md

~~~~
**Only something that needs the person right now may wake them at night** (today: a dangerous email the security
~~~~
