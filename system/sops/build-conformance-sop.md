---
topic: [build-process, system-architecture]
id: system-playbook-build-conformance
title: "Build Conformance — how building conforms in this harness, and how we know (v1, IN PROGRESS)"
record_type: playbook
desk: root
status: in-progress
authority: user
created_at: 2026-11-02
updated_at: 2026-11-02
purpose: "What was learned building the harness's layers of friction: how the harness behaves, which layers exist and what each catches, what is proven and what is not, and how to add, test or remove a layer without fooling yourself. The validated successor to the old build SOP (system/sops/build-sop.md, retiring)."
read_when: "Before adding or changing a guard, a check or a test; when a build landed somewhere wrong; when a test says the system is broken; when a session asks 'is there already friction for this?'"
relations: "The canonical principles SOP (system/sops/canonical-principles-sop.md) holds the laws of physics for a stochastic harness. The skill-building SOP (system/sops/skill-building-sop.md) is the birth procedure for one skill. This SOP sits between them: how conformance is actually produced here, with receipts. The owner's own principles live in their notes (COMPASS), not in the plugin."
evidence_words: "MEASURED = a scored run or a direct test, with a record. SEEN = happened in real use and was written down at the time. REASONED = argued, not yet tested. Canon's tiers map roughly: MEASURED ≈ AUTHORITATIVE, SEEN ≈ OBSERVED, REASONED ≈ RECOMMENDATION."
---

# Build Conformance — v1 (IN PROGRESS)

> **Status:** in progress. Written by the coordinating session of the V2 build (2026-10-29 to 2026-11-02) while the work was fresh,
> then kept current as the real-life trial reports. Items are marked by how they are known (see the evidence words above). Nearly all of
> this is observed principle. The bar for a **rule** here is very high: tested in the rig AND observed over time. Where this document
> says "must", read it as "every time we skipped this, it cost us"; the only law is the one it inherits from canon: *this is a
> stochastic environment, not a rules-based one.*
>
> **For a student reading this:** everything here applies to your installation too. Nothing in it depends on the owner's machine. Where it
> says "the operator", that is the person who maintains the plugin; "the person" is you.

## 0. Read this first

1. **Conformance is produced by the harness, not by the reader.** The old build SOP was a long rulebook injected into every build. A session ignored it, read part of it, or pulled all of it into context and drowned. Nothing it said acted on its own. V2 moved the lessons into the harness as layers of friction: hooks that run before an action, checks that run at the end of a turn or at commit time, and a few locks that remove an ability outright. Those act whether or not anyone read anything. This document explains those layers; it is not itself one of them. (SEEN)
2. **Most of what looked like the model failing was our own layers fighting it.** The first full exam failed on builds. The main cause was a guard refusing the very folder the owner had ruled skills belong in. The rest was an interview skill that stopped the build to ask questions, and a test fence that steered sessions to the wrong folder. Working with the model's defaults moved builds from 2 of 9 to 6 of 7. When a build goes wrong, ask first which layer did it. (MEASURED: Round D final; pinned re-run 2)
3. **Score the end state.** What counts is that the thing ended up built, in the right place, and listed where the person will find it again. Mistakes along the way are a cost, not the verdict. (MEASURED, owner's ruling)
4. **Say what was tested and what was not, in the same breath as the number.** "20 of 20 listed shapes stopped; shapes not on the list are not covered; the push case is not evaluated" is a result. "Fine china passed" is not. This document's own numbers follow that form.
5. **Overlapping circles, not a stack.** Layers count separately only if they fail differently. Three text-matching guards in a row are one layer. The centre of the Venn diagram, where several different kinds of layer overlap, is compliance. (canonical principles; MEASURED on the cloud incident below)

## 1. Where things go, and the layer that notices

The harness knows a person through two pointers only: their notes folder (content, never code) and their personal code folder. Nothing in the shared plugin names anyone. Within that, each kind of thing has one home, and one or more layers notice when it lands elsewhere.

1. **A personal skill** goes in Claude's own skills folder, `~/.claude/skills/<name>/`, with its scripts inside that folder. Nothing asks first; the final message says where it went. *Notices:* the placement guard at write time (it steers a skill written into a project's `.claude/skills` back to the person's own folder unless the person said it was for that project), and the end-of-turn check that refuses to end a turn with a new skill file nowhere listed. (MEASURED: student skill builds went from 0 of 2 to 2 of 2 once the steer existed)
2. **A one-off script the person wants to keep** goes in the personal code folder and onto the person's own list. *Notices:* the end-of-turn check for an unhomed `.py`/`.sh`; and, when a long inline command ran and nothing was saved, a once-per-session offer to keep it, with a stop if the person said "keep it" and nothing was saved. (MEASURED: both "keep it" cases that failed before now land)
3. **Code that serves one desk** goes in the personal code folder under `desks/<desk>/tools/`; the desk's notes stay in the notes folder. *Notices:* the placement guard's desk clause. (MEASURED: the one desk-tool case lands)
4. **A shared tool** goes in the plugin's shared layer, once, with a row in the shared register; a desk uses it and never copies it. *Notices:* the pre-commit registration gate refuses a commit that adds a tool with no row; the register-drift check refuses a row whose hash no longer matches its file. (SEEN: a week's tools once went unregistered; the gate exists because of it)
5. **Scheduled jobs, the person's tools and the person's desks** are listed in the person's own files (`jobs.md`, `register.jsonl`, `desks/desk-registry.yaml`, in the notes folder), read alongside the plugin's shared lists. The plugin ships no example list, because an example reads as an instruction. *Why:* an entry inside the plugin is wiped by the next plugin update, and a shared plugin is effectively public. *Notices:* a CI check refuses any private name in shipped code. (MEASURED: the check runs on every push)
6. **Sharing a skill with a team** means its files live in a team Google Drive folder, linked into the skills folder. *Status:* designed and approved, not built; the two build cases that need it fail until it is. (REASONED)
7. **Sharing a skill across machines or a business goes through Drive, not through the plugin.** A link from Drive into the skills folder is encouraged as a practice, not insisted on. (owner's ruling)

## 2. Fine china: the asks

Fine china is the owner's name for the hard-to-recover things: SOPs, canon, the person's own SOPs, spreadsheets, data files and databases, whole folders, every `CLAUDE.md`, and anything in a cloud account. The layer is an **ask**, not a wall: the action stops once, the person sees the exact change, and a yes lets it through. Walls are reserved for canon and plugin SOPs being overwritten wholesale, by any tool.

What is covered, as of 2026-11-02 (MEASURED by the direct hook exam, both setups):
1. Overwrites by shell redirect, `tee`, `sed -i`, Python rewrites, and the Write tool.
2. Deletes of a single file by `rm`, `unlink`, a move away, or Python; deletes of a whole non-empty folder by `rm -r`, `find -delete`, `rmdir`, or Python; renames of canon.
3. Mass deletes in a cloud account through command-line tools, including a command tucked inside a script body that an interpreter runs.
4. Every `CLAUDE.md`: an edit asks with a diff; an edit to the plugin's own copy says it will be replaced on the next update and points at the person's own file; a file passing 200 lines gets a warning (the vendor's guidance is to stay under 200).

What stays quiet on purpose: throwaway paths (temp and scratch folders), regenerable folders (`node_modules`, `__pycache__`, `.venv`, `dist`, `build`, caches), a data file touched in the last ten minutes, and the person's ordinary notes (an open question).

The exam result at 2026-11-02: operator setup 20 of 20 listed cases stopped, 38 of 38 harmful calls, 45 of 45 route-arounds; student setup 16 of 16, 25 of 25, 45 of 45; zero false alarms on the 10 and 7 ordinary tasks. **Remainder:** the push cases (a private commit reaching the public repo) are not evaluated while the push scan is in warning mode; shapes not on the list are not covered; and a direct hook exam shows that a guard fires on a shape, not that a person was protected in a real session.

## 3. Reading: guard the doors, trust the house

Anything that arrives from outside the machine is cleaned before the model reads it: web pages and searches, connector output (mail, chat, calendar, documents), PDFs, office files and spreadsheets. Inside the machine, a person's own files read normally; only Downloads and Desktop are untrusted, because that is where outside files land without passing a door. (MEASURED: the five false alarms this replaced, all on a person's own project notes, fire 0 of 5 now; a Downloads read is redirected to the cleaner and a planted line in it is caught)

The connector door is a hook that runs after any connector tool and swaps its output for a cleaned copy, for connectors added later too. If the cleaner itself fails, the content is withheld, never passed raw. **Remainder:** the live check on a real mailbox has not been run; the behaviour is proven by unit tests only, because a test harness that loads no connectors cannot see it.

## 4. How the harness actually behaves

The facts the layers above are built around. Most were learned the hard way.

### 4a. Hooks and guards
1. **A blocking hook stops only what it recognises.** A guard that reads the command's text can be walked past by saying the same thing another way: inside a script body, through another tool, with a different word. That is how 899 of the operator's real cloud files reached the bin during a test (all recovered). For anything irreversible, pair the text guard with a layer that removes the ability: credentials out of reach, a system-level lock, network limits. (SEEN; canonical principles §4.6)
2. **Only one exit code blocks.** In a pre-action hook, exit 2 blocks and everything else allows; an exit 3 meant as "cannot determine" quietly let writes through for weeks. (MEASURED)
3. **An end-of-turn "block" is a request.** It re-injects text and relies on the model agreeing; it beats forgetting, not disagreement. Reminders are strong requests, not walls, and are scored as preferences. (canonical principles; MEASURED)
4. **A reminder can cause the miss it was meant to prevent.** The end-of-turn stop forced a follow-up message, and the follow-up dropped the file's location, failing two builds that had done everything right. The stop now asks for the location to be restated. (MEASURED)
5. **Judge a command where it runs.** Several guards missed `cd notes && rm -r folder` because they resolved the path against the session's starting folder. Follow the `cd` chain. (MEASURED)
6. **Text matching cuts both ways.** A harmless read of a guarded file's name raised a popup; a harmless edit tripped a guard whose parser choked on an apostrophe in a heredoc; "trashed" did not match "trash". Telling a read from a write, and parsing rather than matching, is where both the false alarms and the misses live. (SEEN)
7. **Same target, different tool, different verdict.** A write guard stopped the Write tool from touching a protected folder, and a shell append into the same folder was not caught. Check every tool that can reach a protected target. (SEEN)
8. **A guard that greps a command string for a keyword false-positives on mere mentions.** A comment, a quoted example, or an echo of the word fires it. (SEEN, carried from the old SOP and seen again here)
9. **Hooks need their temp folder.** Inside a sandbox, a copied hook's `mktemp` failed and, failing closed, blocked every command. On macOS `mktemp` ignores `TMPDIR`; a wrapper in a private bin fixed it, and a pre-run check that a hook can make a temp file now catches it. (MEASURED)
10. **A hook written for `sh` and tested with `bash` is not tested.** The bash-ism dies at parse time and takes the whole hook with it. (carried from the old SOP)
11. **Test a hook with faithful JSON on stdin, never with `echo`,** which mangles escapes. (carried from the old SOP)

### 4b. Sessions, configuration and the machine
12. **Claude loads configuration from every parent folder.** Starting in a folder loads the `.claude` instructions, skills and agents of every folder above it. A swapped home folder and `CLAUDE_CONFIG_DIR` do not stop this; a working folder outside the home does, as does a kernel read-deny. (MEASURED by a zero-cost probe)
13. **A throwaway home folder does not isolate logged-in tools.** A child session inherits the environment and the PATH, including where a command-line tool keeps its login. (SEEN: the cloud incident)
14. **Permission asks cannot be observed headless.** They are auto-denied or auto-approved, so no test can see a person answer one. Most fine-china protection works by asking, so a live rig cannot measure it directly; 27 of 37 fine-china sessions in one run were not evaluable for this reason. (MEASURED)
15. **Windows keep the hook list they started with.** After a hook is renamed or retired, older windows print harmless "file not found" errors and run without it until restarted. A forwarding shim at the old name bridges the gap. (SEEN)
16. **Windows run what is on disk, not what is on GitHub.** After a landing from a worktree, the shared checkout is behind, and every window on the machine runs the old version until it is fast-forwarded. (SEEN)
17. **The vendor's own delete-safety popups fire even with all permissions on,** and they wait for a human. Commands written without `rm` and without packed one-liners avoid them; leftover throwaway files can be moved instead. (SEEN)
18. **Two separate settings govern context compaction;** turning off automatic compaction leaves idle compaction on. (SEEN)
19. **A full disk stops everything at once.** Hooks fail closed on their temp files; the cloud sync client asks to reset and sets unsynced files aside. Free the space, reopen the client, then compare what it set aside against what is live; do not reset. (SEEN)
20. **The push scanner runs from the installed copy, not the commit being pushed,** so a change to the scanner cannot approve itself. Land the rule first, update the installed copy, then land what depends on it. (SEEN)
21. **A relayed approval is not an approval until it is written down where you can read it.** One "it's in the plan" relay was not in the plan yet, because the write had been blocked by a false alarm. Check the written source; for a guard change or a bulk real-world action, ask the person directly. (SEEN)
22. **Commit messages drift from what landed when a branch is split;** a record of the SHAs is more reliable than the messages. (SEEN)

### 4c. The sandbox used for tests (macOS `sandbox-exec`), measured on one machine
23. Reads are open by default; write isolation is not read isolation. A test actor listed the real home with `find /`. (MEASURED)
24. Rule ordering is not simply "last match wins": a trailing unfiltered allow did not reopen filtered denies, a filtered one did. Fail-first tests must break the profile realistically. (MEASURED)
25. A nested sandbox is refused (rc 71), which makes a cheap "am I sandboxed?" probe. (MEASURED)
26. Setuid tools (`crontab`, `at`) cannot execute inside it; probe them in read-only form so a broken sandbox can never install a job. (MEASURED)
27. `os.path.exists()` returns False on a kernel-denied path; only ENOENT means absent, anything else must refuse. (MEASURED)
28. Some probes are visible to the person: `open x.command` raises a dialog every run; `lsappinfo front` is a quiet substitute. (MEASURED)
29. The vendor's own Bash sandbox wraps only Bash (not the Write tool or hooks), can write a shared per-user temp folder by default, and in bypass mode lets unlisted hosts through unless a strict allowlist is set. (MEASURED)

## 5. Adding, keeping and removing a layer

1. **Add a layer because an incident or a measured miss demanded it,** never because the frame permits it. Of sixteen switches added in three days, five came from consistency or approval rather than a miss; they are kept and flagged as pruning candidates. (MEASURED by audit)
2. **A new layer lands behind a switch, off.** It goes on when a direct test or a live case shows it changes an outcome, or when it closes a measured hole. Six switches that never fired in any run were deleted; a nudge that proved redundant once the other layers were on stayed off. (MEASURED)
3. **Prefer a different kind of layer over a third copy of the same kind.** After the cloud incident the rig got credential isolation and a kernel lock, not another pattern. (canonical principles; SEEN)
4. **Same action, same verdict.** If the shell is asked, Python is asked; if the shell is blocked, the write tool is blocked. Any gap between tools is a route-around waiting to be found; three such gaps were closed in one night. (MEASURED)
5. **Test both directions, and keep the exemptions honest.** A guard that stops the bad case and also stops `rm -rf build/` in a project is a false-alarm factory; the regenerable list exists for that.
6. **Every switch is a real line in the config file,** with a test that it is a real line. One fix once landed inside a comment and did nothing; a whole live batch was wasted. (SEEN)
7. **Subtraction counts as building.** Retiring an interview skill, dropping the catch-all read rule, and deleting dead switches each improved the scores more than most additions. (MEASURED)
8. **Prose layers are pointed at, not relied on.** `CLAUDE.md` may point to where things live; it enforces nothing. A line added there as enforcement was reverted the same day in favour of a code check. (SEEN, owner's ruling)
9. **Fix the class, not the instance.** When a `cd` blind spot was found in one guard, the same blind spot was in the overwrite guard; both were fixed in the same pass. (MEASURED)
10. **Land one change at a time onto the shared branch, from one window,** with the hooks on and never `--no-verify`. Two commits at once share one index; a refused commit leaves a half-staged file behind for the next one to sweep up. (SEEN, twice in one day)

## 6. Testing conformance without fooling yourself

1. **Isolation is not real until a deliberate attempt to break it has been seen to fail.** We assumed a test wall held, and it did not. Now: no credentials in the environment, a private PATH, a kernel lock around the whole actor, a pre-run check that fails if anything can be reached, and a read-only canary that tries. (SEEN, then MEASURED)
2. **Never aim destructive tasks at a machine with live logins** unless the ability has been removed underneath. A guard alone is not enough. (SEEN)
3. **A check needs a control that must show up.** An isolation preflight reported "nothing personal loaded" while writing its log somewhere it could not see; planting a known file that must appear exposed it. Deliberately broken copies of a fence must fail its tests. (MEASURED)
4. **One frozen version, nothing landing mid-run, every result tied to the commit.** A run on a mixed tree gave a muddled result nobody could use. (SEEN)
5. **An independent scorer that never saw the briefs,** scoring from the rules and transcripts only. The one self-scored run was not trusted. (SEEN)
6. **Match the instrument to the question.** Direct hook runs are cheap and exact for "does this guard fire on this shape", but they do not find route-arounds nobody listed, and both of the worst real holes were found live. Live runs fit builds and false alarms. Only real use shows a person answering a real ask. (MEASURED, REASONED)
7. **Say which layer refused.** Every scored failure names the layer: the test fence, a named guard, the vendor's own check, or the model. A guard's refusal is never recorded as a model failure. (MEASURED)
8. **Student results count only from a clean setup.** Everything before the isolation fix loaded the operator's personal skills and hooks; those results are void. A student run now refuses to start if any personal path loads, and a planted control file must appear. (MEASURED)
9. **Run tests from a real folder, never a throwaway one.** The throwaway exemption is silent and turns fine china off; a whole run was voided this way. (MEASURED)
10. **The test setup can quietly become the project.** Every fence was justified, and rig work still ran about one to one with product work. Ask of each new piece whether it buys a measurement of the outcome. (MEASURED by audit)
11. **Tests clean up and check for disk first.** Leftover temp folders from parallel suites filled the disk and froze every window; runners now refuse to start below 5 GB free. (SEEN)
12. **When a test says the system is broken, suspect the test first,** and that cuts both ways, including against a helper's report. (carried from the old SOP; SEEN again here on the silent-fence run)
13. **Prove it on a real specimen, never only a synthetic one;** and for anything a human sees, the acceptance test is the real invocation path. (carried from the old SOP)
14. **A validator passing is not the thing working.** (carried from the old SOP; SEEN again on a preflight)
15. **A count is only as good as the shape you searched for, so write the shape down.** (carried from the old SOP)
16. **n=1 resolves nothing; grade on output, not the clock.** (carried from the old SOP, measured there)
17. **A correctly scoped narrow finding, read broadly, is as dangerous as a wrong one.** State the full set a claim is about and which members were checked. (carried from the old SOP)

## 7. Working with helpers and across windows

1. **Many windows sharing one checkout is the main coordination hazard.** What helped: helpers in their own worktrees, one landing at a time through one window, and checking the shared checkout is up to date after each landing. (SEEN)
2. **Before moving or deleting anything you did not make, ask every window and the person.** A helper can create things its own window does not know about; a stray full copy of the repository turned out to be a helper's path mistake. Helper scripts take absolute output paths. (SEEN)
3. **An order naming a project applies to that project only,** unless the person says "every window". (SEEN)
4. **A safety stop is not worked around by another helper;** it goes to the person. Doing the same work in the open, where it could be watched, passed. (SEEN)
5. **Windows sensibly ask for the person's own yes before loosening a guard or editing a `CLAUDE.md`,** rather than taking a relay. (SEEN)
6. **Background helpers stall.** A helper that ends its turn waiting on a monitor often never wakes; a one-line nudge to read its own output file unsticks it. The status panel lists finished helpers by their last activity and overstates how much is running. (SEEN)
7. **Ask helpers to report deviations, not hide them.** "I chose X against the brief because Y" was right each time it happened here. (SEEN)
8. **A cheap model told to try three denied commands often stops after the first denial,** so judge a canary by what it attempted, in a mode where total failure is harmless. (MEASURED)
9. **Never hand a human a code fence to paste when a script and one line will do;** never launch a watchable run detached; quote every Drive path (the root contains a space). (carried from the old SOP)
10. **Bulk model work is batched, many items per call, never looped once per item.** (carried from the old SOP, measured there)

## 8. What we tried that did not work

1. **Text as enforcement,** including one line in `CLAUDE.md`, added by mistake and reverted. (SEEN)
2. **Interviewing a person who asked for a skill.** It stopped the build. The skill is archived, closed for renovation; a plain request gets a normal build. (MEASURED)
3. **Speed bumps that pass on retry.** They slow a push and do not steer it; the push case passed on the third attempt. (MEASURED)
4. **A trusted-folders list needing one-time approvals.** More machinery than a short untrusted list, for the same protection. (REASONED)
5. **Guardrails with no measured effect.** Six never fired and were deleted. (MEASURED)
6. **Bundling a rule change with the thing it permits.** The scanner could not approve its own exemption. (SEEN)
7. **Treating "it has a hook" as "it is protected".** The hook was there for the cloud case; the command was written a way it did not read. (SEEN)
8. **Testing the wall by assuming it.** (SEEN)
9. **Blanket-rewriting history to fix a reference.** Journals and records are history; fix live references by hand, visibly. (carried from the old SOP)

## 9. Carried over from the old build SOP (de-risking a build)

The old SOP's domain notes about scheduled runners stay with the cron rulebook. These general ones still hold for any build:
1. De-risk cheap to expensive: a syntax check, then a synthetic dry run, then one real supervised run, then automate.
2. Prove a cheap, risky integration (an API call, an upload, a permission, a path) with throwaway data before the expensive run.
3. Back up a hand-edited or always-loaded file before changing it, even inside a build; it is the only fast revert.
4. A stale or broken command form has usually propagated; when you find one, search the whole system.
5. `commands/` and `skills/` share one namespace; a same-named command shadows the skill.
6. A verification regex using `\s*` spans newlines and reads the next key's value.
7. A script the harness runs as a bare command needs its execute bit.
8. A push can silently no-op after a rebase drops upstream tracking; "checks settled" read immediately after a push is a false result.
9. Bulk archive, drain or migration: make loss impossible before editing (back up, then move, never delete).

## 10. Open as of this draft

The two push cases and all push limits wait for the launcher-lanes step. The live mailbox check for the connector door. The Drive sharing build. Whether ordinary notes are fine china, and how broad folder-delete asks should be. Whether a desk session should load only its own desk's knowledge (the design says so; the loader does not yet). The real-life trial, which is the only instrument that can see a person answer a real ask.
