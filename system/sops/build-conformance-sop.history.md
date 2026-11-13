# Build Conformance SOP: history log

Passages replaced, word for word. Reason for all, unless marked: corrected or extended 2026-11-03 from the final exam and sign tests.

## 2026-11-03

- updated_at: 2026-11-02

- > **Status:** in progress. Written by the coordinating session of the V2 build (2026-10-29 to 2026-11-02) while the work was fresh,
  > then kept current as the real-life trial reports.

- and listed where the person will find it again. Mistakes along the way are a cost, not the verdict. (MEASURED, owner's ruling)

- and the end-of-turn check that refuses to end a turn with a new skill file nowhere listed. (MEASURED:

- *Notices:* the placement guard's desk clause. (MEASURED: the one desk-tool case lands)

- *Status:* designed and approved, not built; the two build cases that need it fail until it is. (REASONED)

- The layer is an **ask**, not a wall: the action stops once, the person sees the exact change, and a yes lets it through. Walls are reserved for canon and plugin SOPs being overwritten wholesale, by any tool.

- The exam result at 2026-11-02: operator setup 20 of 20 listed cases stopped, 38 of 38 harmful calls, 45 of 45 route-arounds; student setup 16 of 16, 25 of 25, 45 of 45; zero false alarms on the 10 and 7 ordinary tasks.

- Most fine-china protection works by asking, so a live rig cannot measure it directly; 27 of 37 fine-china sessions in one run were not evaluable for this reason. (MEASURED)

- A run on a mixed tree gave a muddled result nobody could use. (SEEN)

- Ask of each new piece whether it buys a measurement of the outcome. (MEASURED by audit)

- 10. **Bulk model work is batched, many items per call, never looped once per item.** (carried from the old SOP, measured there)

- 3. **Speed bumps that pass on retry.** They slow a push and do not steer it; the push case passed on the third attempt. (MEASURED)

- The two push cases and all push limits wait for the launcher-lanes step. The live mailbox check for the connector door. The Drive sharing build. Whether ordinary notes are fine china, and how broad folder-delete asks should be. Whether a desk session should load only its own desk's knowledge (the design says so; the loader does not yet). The real-life trial, which is the only instrument that can see a person answer a real ask.


- ## 8. What we tried that did not work (heading unchanged in the end; listed because a draft changed it)

- Also changed from the old text: §0.2's evidence label named two internal exam names; §0.4's sentence said "stopped" where it now says "got a hook response".

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-001, see drafts/build-conformance-sop/applied.md

~~~~
title: "Build Conformance — how building conforms in this harness, and how we know (v1, IN PROGRESS)"
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-002, see drafts/build-conformance-sop/applied.md

~~~~
supersedes: "Every earlier build SOP, including system/sops/build-sop.md, which is retired. Where they differ, this document wins."
sections: "0 read this first · 1 where things go · 2 fine china · 3 reading · 4 how the harness behaves · 5 adding and removing a layer · 6 testing · 6a where the proof stands · 7 helpers and windows · 8 what didn't work · 9 from the old build SOP · 10 open · 11 tensions · 12 rule candidates"
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-003, see drafts/build-conformance-sop/applied.md

~~~~
relations: "The canonical principles SOP (system/sops/canonical-principles-sop.md) holds the laws of physics for a stochastic harness. The skill-building SOP (system/sops/skill-building-sop.md) is the birth procedure for one skill. This SOP sits between them: how conformance is actually produced here, with receipts. The owner's own principles live in their notes (COMPASS), not in the plugin."
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-004, see drafts/build-conformance-sop/applied.md

~~~~
# Build Conformance — v1 (IN PROGRESS)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-005, see drafts/build-conformance-sop/applied.md

~~~~
> **Status:** in progress. Written by the coordinating session of the V2 build (2026-10-29 to 2026-11-03) while the work was fresh.
> The harness is being reorganized around a three-tier architecture, so parts of this will change; what's proposed for that isn't here until it's proven, apart from one decision noted in §2.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-006, see drafts/build-conformance-sop/applied.md

~~~~
> **Words used here.** The *owner*: the person who maintains the plugin, and the operator. The *rig*: the test setup, where real AI sessions run sealed in a sandbox. The *final exam*: one set of those sessions on one locked version, scored by independent graders. A *fence*: a test-only guard that keeps those sessions away from real accounts. *Bypass*: running with permission prompts switched off. A *speed bump*: a first attempt refused with a message, where a later try gets through or gets an ask. *Launcher lanes*: a later step, for someone who pushes to several repositories, where each desktop shortcut locks a window to one push destination. A *keep question*: a line asking whether to save a command the person ran as a script. Items are marked by how they are known (see the evidence words above). Nearly all of
> this is observed principle. The bar for a **rule** here is very high: it has to be true in theory, seen to be true, and true durably in practice over time, and true in the way it's prescriptively worded (§12). Where this document
> says "must", read it as "every time we skipped this, it cost us"; the only law is the one it inherits from canon: *this is a
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-007, see drafts/build-conformance-sop/applied.md

~~~~
The harness knows a person through two pointers only: their notes folder (content, never code) and their personal code folder. Nothing in the shared plugin names anyone. Within that, each kind of thing has one home, and one or more layers notice when it lands elsewhere.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-008, see drafts/build-conformance-sop/applied.md

~~~~
2. **A one-off script the person wants to keep** goes in the personal code folder and onto the person's own list. *Notices:* the end-of-turn check for an unhomed `.py`/`.sh`; and, when a long inline command ran and nothing was saved, a once-per-session offer to keep it, with a stop if the person said "keep it" and nothing was saved. (MEASURED: both "keep it" cases that failed before now land)
3. **Code that serves one desk** goes in the personal code folder under `desks/<desk>/tools/`; the desk's notes stay in the notes folder. *Notices:* the placement guard's desk clause, and a sign added for loose tools (§0.6). (MEASURED: the one desk-tool case landed 2 of 3 runs at each of the last two commits. A miss leaves a working, listed tool in the wrong folder, and the session says where it is. The added sign fired in none of the three re-runs, so it shows no measured benefit.)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-009, see drafts/build-conformance-sop/applied.md

~~~~
5. **Scheduled jobs, the person's tools and the person's desks** are listed in the person's own files, read alongside the plugin's shared lists: `jobs.md` and `register.jsonl` in the personal code folder, `desks/desk-registry.yaml` in the notes folder, beside the desks it names. The plugin ships no example list, because an example reads as an instruction. *Why:* an entry inside the plugin is wiped by the next plugin update, and a shared plugin is effectively public. *Notices:* a CI check refuses any private name in shipped code. (MEASURED: the check runs on every push)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-010, see drafts/build-conformance-sop/applied.md

~~~~
8. **A student who never finished setup** meets none of these stops, because the personal code folder they steer to doesn't exist. Three sessions built a working tool with no home, and nothing told them. (MEASURED: one small check)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-011, see drafts/build-conformance-sop/applied.md

~~~~
Fine china is the owner's name for the hard-to-recover things: SOPs, canon, the person's own SOPs, spreadsheets, data files and databases, whole folders, every `CLAUDE.md`, and anything in a cloud account. The layer is an **ask**, not a wall: the action stops once, and a yes lets it through. Don't count on the person seeing it: in the owner's working assumption everyone runs in bypass, where a plain-shell ask ran with no prompt in the cases tested, and whether one shows varies by action. Most asks now carry a sign (§0.6), and the sign is what steers the session. Walls are reserved for canon and plugin SOPs being overwritten wholesale, by any tool. Decided 2026-11-03, not yet built: writing into shared plugin code gets a hard block with a sign, with administrators as the one exception.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-012, see drafts/build-conformance-sop/applied.md

~~~~
What stays quiet on purpose: throwaway paths (temp and scratch folders), regenerable folders (`node_modules`, `__pycache__`, `.venv`, `dist`, `build`, caches), a data file touched in the last ten minutes, and the person's ordinary notes (an open question).
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-013, see drafts/build-conformance-sop/applied.md

~~~~
Anything that arrives from outside the machine is cleaned before the model reads it: web pages and searches, connector output (mail, chat, calendar, documents), PDFs, office files and spreadsheets. Inside the machine, a person's own files read normally; only Downloads and Desktop are untrusted, because that is where outside files land without passing a door. The exception today: `.csv`, `.pdf`, `.docx` and `.xlsx` are refused wherever they sit, which stopped reads of a person's own data file in 8 of 12 sessions that used one. Each refusal redirects to a cleaner. The `.csv` refusal is the likely false alarm, and the only one measured; it's logged, not fixed. (MEASURED: the five false alarms this replaced, all on a person's own project notes, fire 0 of 5 now; a Downloads read is redirected to the cleaner and a planted line in it is caught)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-014, see drafts/build-conformance-sop/applied.md

~~~~
24. Rule ordering is not simply "last match wins": a trailing unfiltered allow did not reopen filtered denies, a filtered one did. Fail-first tests must break the profile realistically. (MEASURED)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-015, see drafts/build-conformance-sop/applied.md

~~~~
27. `os.path.exists()` returns False on a kernel-denied path; only ENOENT means absent, anything else must refuse. (MEASURED)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-016, see drafts/build-conformance-sop/applied.md

~~~~
8. **Prose layers are pointed at, not relied on.** `CLAUDE.md` may point to where things live; it enforces nothing. A line added there as enforcement was reverted the same day in favour of a code check. (SEEN, owner's ruling)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-017, see drafts/build-conformance-sop/applied.md

~~~~
11. **Layers go lightest first:** a sign, then a reason gate (the session can proceed only by stating why), then a hard block (refused every time, kept for a few particular things), then a popup (a box the person must answer, used sparingly because it can hang an unattended session for hours). Add the next only where the lighter one fails. (owner's ruling; the sign MEASURED, the reason gate and popup not)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-018, see drafts/build-conformance-sop/applied.md

~~~~
3. **A check needs a control that must show up.** An isolation preflight reported "nothing personal loaded" while writing its log somewhere it could not see; planting a known file that must appear exposed it. Deliberately broken copies of a fence must fail its tests. (MEASURED)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-019, see drafts/build-conformance-sop/applied.md

~~~~
8. **Student results count only from a clean setup.** Everything before the isolation fix loaded the operator's personal skills and hooks; those results are void. A student run now refuses to start if any personal path loads, and a planted control file must appear. (MEASURED)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-020, see drafts/build-conformance-sop/applied.md

~~~~
Not one score: these come from different commits. Today's numbers describe today's harness and won't carry over to a restructured one; the method does.
1. **Final exam, one locked commit, 40 live sessions, one fresh independent grader each:** builds operator 8 of 9 cases, student 8 of 8; false alarms 0 of 10 and 0 of 7. The one miss is the desk-tool case, 1 run of 3. It met the pass mark, on a thin margin: one explained miss per setup is allowed, and 6 passes of the team-skill case rest on a stated reading, that a full Drive plan plus one question about what the skill does passes, with no skill built. Zero false alarms rests on a reading: three sessions in two cases had a one-line keep question that a literal "any ask" rule would fail, and the owner's allowance for one informational line names only one of those cases. No case reads a data file, so this doesn't clear the §3 refusal.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-021, see drafts/build-conformance-sop/applied.md

~~~~
1. **Text as enforcement,** including one line in `CLAUDE.md`, added by mistake and reverted. (SEEN)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-022, see drafts/build-conformance-sop/applied.md

~~~~
13. **Changing every ask to a hard block.** Withdrawn: lighter layers first (§5.11). (owner's ruling)
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-023, see drafts/build-conformance-sop/applied.md

~~~~
## 10. Open as of this draft
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-024, see drafts/build-conformance-sop/applied.md

~~~~
The two push cases and all push limits wait for the launcher-lanes step. A student's push today is a hard stop rather than warning mode, which seems to conflict with "all repos stay open". The live mailbox check for the connector door. Whether ordinary notes are fine china, and how broad folder-delete asks should be. A session in a desk folder now loads only that desk's knowledge; loading across desks is deferred. Only real use can show a person answering a real ask: the planned real-life trial was dropped, and that cost was accepted.
~~~~

## 2026-11-13 - reason: rulebooks run 2026-11-13, approved screen: build-conformance-sop edit-pass hunk hunk-025, see drafts/build-conformance-sop/applied.md

~~~~
1. **Text doesn't enforce anything.** True in theory: a stochastic model can ignore what it reads. Seen: the old build rulebook, and a line added to `CLAUDE.md` as enforcement (§0.1, §5.8). It's the strongest candidate, and it's already the owner's ruling for `CLAUDE.md`.
~~~~
