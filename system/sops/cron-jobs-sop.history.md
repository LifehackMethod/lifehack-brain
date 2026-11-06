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
