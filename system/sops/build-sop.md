---
topic: [build-process]
id: system-playbook-build-sop
title: Build SOP — hard-won build doctrine (loaded by /build)
record_type: playbook
desk: root
created_at: 2026-06-10
updated_at: 2026-06-10
status: active
authority: user
---

# Build SOP

> ## NOTE — WHAT THIS PAGE CITES THAT IS NOT IN THIS REPOSITORY
>
> This page earns its length by naming the exact record where each lesson was learned. Those records
> live in the author's own notes folder, not in any repository, and they are named here rather than
> discovered one dead link at a time.
>
> **⛔ None of it is coming**, and none of it is needed: where a rule cites one, the evidence is IN
> the rule. The path was only ever the filing location of the original write-up.
>
> - ⛔ `records/2026-07-13-translator-voice-debug-history.md` · `records/decision/2026-06-04-design-lifehack-skill.md` · `records/decision/2026-07-13-statusbar-hud-build.md` · `records/decision/2026-07-28-model-efficiency-plan-abandoned.md` · `records/log/2026-08-07-project-arming-lock-adversarial-audit.md` · `records/reference/2026-07-12-stage2-email-interpret-method.md` · `state/projects/lifehack-cowork/brief.md` · `state/projects/huddle/huddle-skill/brief.md` · `state/projects/ingest-skill/brief.md` · `state/projects/project-system/brief.md` · `state/projects/skill-builder/records/2026-08-07-dead-end-harvest.md` · `state/projects/skill-system/brief.md` · `state/projects/translator-voice/brief.md`

> Loaded on-demand by the `/build` skill — NOT always-on. Apply the **General** do's to ANY build;
> read a **domain** section only when it applies. Append lessons here as builds teach them — this is
> how `/build` gets smarter over time. ⛔ The map that registered its home in the system this came
> from does not ship — it was an index of one person's folders. This file's home is this path.

## General — applies to every build
- **Prove the cheap, risky integration with a synthetic input BEFORE the expensive run.** When a build has a
  step you're unsure of that's *cheap* to test (an API call, an upload, a permission, a path) and a *costly*
  step after it (a long run, a big fan-out), test the cheap one with throwaway data first. *(2026-06-10: a
  synthetic Drive-upload test caught a cwd-sandbox rejection AND a lock-cleanup bug in seconds — before a
  15-min headless run would have.)*
- **Prove it live ONCE, by hand, before automating it.** Don't put a thing on a schedule/cron until a real
  end-to-end run has succeeded supervised. Automation amplifies a broken runner.
- **De-risk in the cheap-to-expensive order:** syntax-check → synthetic/dry integration test → one real
  supervised run → then enable/schedule.
- **Back up a crown-jewel file BEFORE editing it, even in `/build`.** The memory-system skills (`/save`, `/read`,
  `project-manager`) + always-loaded `CLAUDE.md` files aren't unit-tested, so a `*.pre-<change>.bak` next to the
  original is the only fast revert. (2026-06-13: backed up `skills/save/SKILL.md` before the P13 rewrite.)
- **Renaming a folder/file referenced in past records — do NOT blanket-sed those refs.** Journal, diary, records,
  old briefs are history, not canon — **only `canon/` folders are immutable** (see `CLAUDE.md`; a genuinely wrong
  reference in one of them CAN be fixed), so the caution here is narrower than it used to be: a mechanical sed
  across the whole tree is a SILENT mass-edit, and silent is the part that's still wrong — a correction has to be
  visible (strike-through or a dated note beside the original), not a blind find-replace. Either DEFER the rename,
  or rename + leave a compatibility symlink/redirect at the old path and update only the LIVE operational refs
  (skills, READMEs, the active plan / canon-map); fix an individual wrong ref by hand, visibly, rather than sed the
  tree. (2026-06-13: the `insight-inbox`→`inbox` rename touched 75 files incl. journal/diary/records — deferred
  rather than blanket-rewrite.)
- **Renaming a skill/module — repoint its OWN internal self-references too, not just external pointers.** After a
  rename, a file's "this is NOT the `<old-name>` skill" line can end up pointing at *itself*. Grep the renamed file
  for its old name as part of the rename, not only the rest of the tree. (2026-06-12: renaming a skill left a
  self-disambiguation line aimed at the renamed file.)
- **Building a SKILL the model actually obeys?** ⏳ The full skill SOP lands later in phase 3 with
  `skill-builder`; `system/sops/skill-building-sop-extract.md` carries the one law the core skills
  cite. What follows here is the structural
  gates (compliance) + cast identity (quality). Provisional (validating in our harness via `cal-checkin`), but it's
  the home for "why instructions fail + how to gate them."
- **Never full-rewrite a file the human hand-edits.** A shared staging/draft file the human edits directly is authoritative — append or make surgical single-line edits; a full rewrite silently clobbers their changes. (Routed from the inbox 2026-06-16.)
- **Resolve a project via the registry `{path}` before editing its files.** A project may have migrated to the v2 folder model — legacy `records/`/`state/briefs/` paths can be stale or deleted, and an "edit succeeded" message doesn't prove you hit the live file. Grep `$DRIVE/system/project-registry.md` first (it's Drive-canonical now).
- **Split ingestion from analysis: a mechanical pull, then LLM slices.** A dumb verbatim pull dumps the raw source to files (an LLM at pull-time condenses/skips/gets lazy — a script can't); THEN the LLM reads slices of those files. Keeps ingestion accurate + analysis token-light, with the complete source underneath for any deep read.
- **For multi-pass analysis of ONE dataset, a blind panel tends to beat sequential passes.** Isolated one-lens agents (fresh context, blind to each other) + a synthesizer give true independence; one LLM running the passes in sequence anchors on the first salient thing and re-covers ground. The trade is more agents/tokens for genuine per-lens coverage — worth it when the lenses would otherwise crowd each other out.
- **Observe-then-codify for judgment-heavy / human-facing skills.** Rather than fully programming such a skill cold, build it and iterate it across real reps while a living SOP (written after the first real rep, sharpened over months) feeds it — the skill iterates, the SOP is the living doc, a scratchpad is the raw capture. Fits any skill whose quality is learned from real reps, not specifiable up front.
- **Shared harness + per-desk policy for ingestion/automation.** One shared harness can own the invariant plumbing (fetch · sanitize · dispatch · notify · emit) while per-desk variation lives only in the desk's own skill/policy, not as `if desk==X` branches in the engine — but extract that shared harness from 2–3 proven instances (Rule of Three), not up front; a premature shared abstraction is itself a blast radius.
- **Test a hook with FAITHFUL JSON, never `echo`.** Piping `echo '{"...":"a\nb"}'` to a hook mangles `\n` into a REAL newline → invalid JSON (control char in a string) → the hook's `json.load` throws → it fail-opens/returns empty, so the test "passes" for the wrong reason and hides the bug. Generate payloads the way Claude Code delivers them: `python3 -c "import json,sys; sys.stdout.write(json.dumps({'tool_input':{'plan':sys.argv[1]}}))" "$BODY" | bash hook.sh`. (2026-06-19, building `guard_plan_structure.sh`: an echo'd `\n` made the first well-formed test pass via fail-open, not via validation — caught only on a re-test with json.dumps.)
- **A stale/broken command form has usually PROPAGATED — grep the whole system when you find one.** A wrong gws-sheets syntax (`values_get` / `--range`+`--spreadsheet-id`) lived in THREE places (a hook's redirect, the `google-sheet` skill's audit flow, the RUNBOOK binary line); fixing only the instance you tripped on leaves the rest to mislead the next session. When one canonical command form is wrong, `grep -rn` the known-bad fragment system-wide and fix every hit. (2026-06-20, Google Sheets standard build.)

- **Bulk archive / drain / migration — make loss IMPOSSIBLE before editing.** Three moves, in order: (1) back up the full target file **BYTE-IDENTICAL** to a timestamped archive (`state/archive/YYYY-MM-DD-<op>/`) and `diff -q` to prove it; (2) have an adversarial **sonnet** agent read the target + the authoritative sources and propose a **per-item disposition** (it PROPOSES; you + the human lock the rule before any delete — "discover → present all → lock → execute"); (3) **PRESERVE-uncertain-not-delete** — fold anything you can't confidently call done into the typed model (as `state:monitoring`/verify), NEVER guess-delete. Also: when "pushing back" items to another home, CHECK that home first — it often already has them (dupes). The operator's #1 fear on a drain is losing real items; backup + propose + preserve makes a mistake recoverable and a guess impossible. (2026-06-20, organism W4: 1091-line `open-loops.md` swamp → 32-line stub, zero loss.)

- **No silent demotion carries into execution — the close must be honest.** The plan's No-Silent-Demotion guard (`architecture-planning-sop.md`) stops in-scope work being hidden at plan-time; the executor must not re-open the leak at run-time. Two rules: (1) **never quietly skip/defer an in-scope task** — that's a checkpoint, not a silent drop; default is build-it-now, deferral needs a reason AND the user's OK; (2) **never report a build "done" while any in-scope `Phase ▸ Feature ▸ Task` is unbuilt** — reconcile every task ✅/✗, name every ✗ LOUD with its reason at the TOP of the report, treat a partial as ✗, and file it to OPEN LOOPS. A task you didn't mention is assumed built; silence-as-completion is the exact months-later failure. (Full mechanism: `/build` SKILL → "No illusion of completion.")

- **When a ruling is overturned, the ⛔ RULED-OUT / DON'T-RETRY board is a MANDATORY search target — not just the document that demoted it.** A ruling that survives on that board outranks the doc it was demoted in: it will kill the same idea on sight, forever, until the board itself is corrected. `system/schemas/project-doc-schema.md` defines that bucket in EVERY Lifehack brief, so **the hole is system-wide, not one brief's quirk** — any demotion/overturn pass must grep the RULED-OUT bucket itself, not just the section being edited. **Measured: a demotion pass found a THIRD surviving copy at `brief.md:995` that the session had missed.**

- **Never put backticks in a `git commit -m` message under zsh — they command-substitute.** zsh runs
  `` `word` `` as a command, so the quoted identifiers are silently dropped from the message (and you get
  "command not found: word" noise). The commit still lands; the MESSAGE just loses those words. Use a
  quoted heredoc (`-F -` / `git commit -F file`) or plain prose without backticks. (2026-07-10, P6 F6.3
  passes-model commit: `` `subject` ``/`` `summary` `` etc. dropped from the message.)

- **★ NEVER HAND A HUMAN A MARKDOWN CODE FENCE TO PASTE — ship a SCRIPT and give them one line.** The
  backtick rule above is not just about commit messages: a ```` ``` ```` fence in an instruction file gets
  copied *with* the block, and zsh reads the backticks as command substitution — the paste is swallowed, the
  shell hangs on a `>` continuation prompt, and the user lands in a bare `sh-3.2$` subshell having run
  **nothing**. They cannot tell a broken paste from a failed check, so the whole verification is worthless.
  **How to apply:** anything a human will paste goes in a **file in the repo** — the verify scripts
  under `system/hooks/tests/` are the worked examples here —
  and the instruction is a single fence-free line — `cd <this repo> && git pull && bash
  system/tools/<script>.sh`. Indent the line in the doc rather than fencing it. The script also prints its own
  PASS/FAIL verdict, so the human reports an outcome instead of raw output they have to interpret.
  (2026-08-01, Phase 9's two-machine check: the pasted block died on its fence; `verify-agent-guard.sh` replaced it.)

- **★ VERIFY WHICH MACHINE YOU ARE ON BEFORE WRITING TWO-MACHINE INSTRUCTIONS — `scutil --get ComputerName`.**
  A whole build was completed, verified, and written up as "done on the second machine, now go check the
  primary" — while actually running **on the primary machine**. The session never checked, and nothing in the
  environment volunteers it (`hostname` is useless here: on that machine it was literally `Mac`, a default that
  identifies nothing). The result was an instruction file telling the
  user to go and re-verify the one machine that was already proven, and to skip the one that was not. **How to
  apply:** the moment a task becomes machine-specific — a hook deploy, a symlink check, a cron gate, any
  "do this on the other one" — run `scutil --get ComputerName` and put the answer *in the artifact*. Same
  family as Confidence-Requires-a-Source: an unverified premise underneath a correct build still ships wrong
  instructions. (2026-08-01, Phase 9.)

- **Bulk LLM work: BATCH many items per `claude -p` call — NEVER loop it once-per-item.** Each `claude -p`
  invocation cold-starts the ENTIRE Claude CLI (~36s even idle — the startup, not the thinking, dominates). So
  one-call-per-item over hundreds of records, run in parallel, starves the calls past their timeout → nearly
  every one fail-safes → thrash. (2026-07-12 intake backfill: ~5 of ~200 records in 15 min this way.) **FIX:**
  bundle ~10–15 items into ONE prompt/call — amortizes the cold-start (~29s for a bundle of 12 vs ~7 min
  one-at-a-time, a ~15× win). Verdict-only batching + a precise second pass for the rare hit keeps it simple.
  If an `ANTHROPIC_API_KEY` exists, prefer the direct API (no cold-start at all) — but Lifehack runs on a
  **subscription, so usually there is NO API key** (checked env, `~/.config/lifehack/secrets/`, keychain). Also:
  a **SUBAGENT shelling `claude -p` double-nests and times out worse** — run bulk `claude -p` from the MAIN
  session, not a spawned agent. **This is the textbook case for the "prove the cheap risky integration on a
  synthetic input FIRST" rule above:** ONE timed batch would have exposed the cold-start cost in 30 seconds
  instead of after a 15-minute grind. When a loop over an LLM is slow, the question is almost never "add more
  parallelism" — it's "why am I paying the fixed cost N times instead of once."

- **A guard hook that greps a command STRING for a keyword false-positives on mere MENTIONS.** A PreToolUse
  Bash guard matching `settings.json` + `statusLine` blocked a `git commit` whose *message* merely mentioned
  both words — and would equally block a `grep`/`cat` that names them. A guard must match the **write-to-target
  pattern** (a redirect / `sed -i` / `tee` *into* the file), never the keyword alone — and you must **test it
  against benign commands that mention the tokens**, not only against the attack. (2026-07-13, the status-bar
  pointer guard blocked its own build's commit.)

- **Mapping a session → "its file" by NEWEST-mtime is unreliable across concurrent windows.** The status-bar
  plan-marker guessed the plan file as the newest `~/.claude/plans/*.md`; the user runs many plan-mode windows
  at once, so "newest" is whichever window saved LAST → markers cross-wire and a window shows the WRONG plan.
  When the user runs parallel windows (they usually do), key a per-session artifact off a **session-specific
  signal** (match by content, or an explicit id passed in), NEVER file mtime. (2026-07-13, statusline plan field.)

- **A script the harness runs as a BARE COMMAND (not `bash script.sh`) needs its EXECUTE bit — `chmod 444` silently BLANKS it.** `statusline.sh` is invoked as `~/.claude/statusline.sh` (no `bash` prefix), so it must stay **755**; a `chmod 644/444` (the hook-file convention) strips the execute bit → the harness gets *permission-denied* → the status bar renders BLANK on every session. Hooks are safe at 444 because `settings.json` invokes them via `bash "..."`; direct-exec scripts are NOT. **Verify a direct-exec script the way the HARNESS runs it (bare path / `./script`), NEVER via `bash script` — a `bash` test passes without the execute bit and masks the exact failure.** (2026-07-14: a chmod dance while building the flywheel stripped statusline.sh's +x and blanked the bar across sessions; `bash`-based verification hid it for three tries.)

- **★ A `#!/bin/sh` HOOK TESTED WITH `bash` IS NOT TESTED — the bash-ism dies at PARSE time and takes the
  WHOLE hook down, not just your block.** `system/githooks/pre-commit` gained a fourth check containing
  `diff <(...) <(...)`. Process substitution is a **bash-ism**; the file's shebang is `/bin/sh` and git
  invokes it as such. Every test passed — because they were run as `bash system/githooks/pre-commit`. The
  real `git commit` died with `syntax error near unexpected token '('` **before running gitleaks, the
  residency backstop, or the jig check** — a parse error is not a failed check, it is *no checks at all*.
  It was caught only because it blocked its own commit; had the block been added below an `exit 0`, or the
  shell been more forgiving, it would have silently disarmed three working gates. **How to apply:** run
  `sh -n <file>` (or `sh <file>`) on anything with a `sh` shebang, and exercise a git hook through a real
  `git commit`, never a hand-invocation. This is the same family as the direct-exec/`chmod` rule above and
  `hook-sop.md` §4's *"exercise a hook through its REGISTERED entry point, never its logic sibling"* — the
  new surface is **git hooks**, where the interpreter is decided by the shebang, not by how you typed it.
  (2026-08-05, the SEAM-RULE drift gate.)

- **A batch edit over shared Drive files must regenerate + re-verify ATOMICALLY per file — a stale prep can clobber a concurrent edit from another window.** When you prep proposals for N files in one pass and WRITE them in a later step, a parallel session — and people do run several at once — may edit one of those files in between — and your stale proposal then silently overwrites their change. The ONLY thing that catches it is a per-file content-preservation CHECK run against the *current* file at write-time (not against the version you prepped from): back up → write → re-run the byte/content check against the backup; on drift it ABORTs and you restore. Treat any active/hot file as unsafe to bulk-touch — defer it to self-heal rather than fight a live window. (2026-07-19, FB.4 brief backfill: a parallel window appended a block to `organism-audit`'s brief between prep and write; the byte-check `brief_backfill_check.py` caught the stale clobber → restored from `.pre-compact.bak` → deferred the file. The whole staged/backup/re-check discipline existed for exactly this.) *(That script + its normalizer were one-time FB.4 tooling and were DELETED 2026-07-28 in the S2.4 retirement sweep — archived at `state/archive/2026-07-28-s24-retirement-sweep/`. **The DISCIPLINE is the lesson, not the script**; don't go looking for the tool.)*

- **A mechanism that automates RECOVERY must be able to tell a FAULT from a DECISION — and state carrying no provenance defaults to "fault", which then OVERRIDES a human.** Never apply new semantics retroactively to pre-existing state whose meaning they cannot know. (2026-07-28, organism-audit T2.6: a new cron circuit-breaker read a missing `retry_at` as `0` — i.e. "backoff already expired" — so every job disabled *without* a backoff timer half-opened on the first tick. That included a job the operator had **deliberately parked**; it woke up and processed 43 items before it was killed. The breaker could not distinguish "this job tripped and is waiting to retry" from "a human switched this off on purpose," because the parked state predated the field that would have said so.) **How to apply:** when you add a field that changes how existing state is interpreted, ask what that field's ABSENCE means for rows written before it existed — and make absence mean the SAFE thing (stay off / stay blocked / do nothing), never the active thing. Where the distinction matters, write the provenance explicitly (`disabled_by: human` vs `disabled_by: breaker`) rather than inferring intent from a null. Same family as the fail-closed rule: an unknown must never be read as permission.

- **A checker that validates CITED references cannot detect an OMITTED one — green means "nothing rotted," never "nothing is missing."** (2026-07-28, organism-audit S2.0: `generated_from_check.py` verifies every path an element cites still exists on disk. Thirteen new files entered the skill-system subsystem uncited; the drift gauge read `0 dead + 0 behind-code` throughout, and the gap was caught by a peer window, not the tool.) **How to apply:** for any completeness claim, the denominator must be computed from the TERRITORY (glob the directory, enumerate the registry), not from the document's own list — otherwise the document grades its own homework. State plainly in the tool's output which of the two it measures.


- **`commands/` and `skills/` share ONE `/<name>` namespace — a same-named command SHADOWS the skill.** Promoting a command to a skill and leaving a "thin delegator" behind at `commands/<name>.md` does not hand off; the command wins the name, and if its body says "invoke the `<name>` skill" you get a self-reference loop. The skill registry surfaces it immediately (it lists the skill with the COMMAND's first line as its description) — read that listing after any command→skill promotion. **Fix: delete the command, don't delegate.** And remember the symlink is machine-local: the OTHER machine needs `rm ~/.claude/commands/<name>.md` + `ln -s <clone>/skills/<name>/ ~/.claude/skills/<name>` after it pulls, or `/<name>` there points at a deleted file. (2026-07-28, `/autoplan` v2 promotion.)

- **A verification regex using `\s*` SPANS NEWLINES — it will read the NEXT key's value and report a pass.** Checking a YAML/frontmatter field with `^key:\s*(.+)$` matches an EMPTY `key:` line, lets `\s*` swallow the newline, and captures the following line's content — so a blank field reports as populated, confidently. Use `^key:[ \t]*(.*)$` (a class that cannot cross a line) whenever you assert on a field's value. **Caught only because the reported value looked wrong**; a plausible-looking wrong value would have shipped as a green check. Cross-ref skill-building-sop PART V: "a fix is not verified until you re-derive its output from real data," and treat your own checker with the same suspicion as the thing it grades. (2026-07-28, the brief `plan:` backfill verification.)

- **★ WHEN A TEST SAYS THE SYSTEM IS BROKEN, SUSPECT THE TEST FIRST — earned FIVE times in one day.** On 2026-07-28 every single RED result was a bad payload and the system was fine every single time: (1) an anonymous `git ls-remote` reported a PRIVATE repo as PUBLIC — the macOS keychain helper had silently supplied cached credentials, and only an unauthenticated API call (HTTP 404) exposed it; (2) a restore check diffed against `HEAD~2`, which no longer contained the deleted files, so it compared against *nothing* and reported two false MISMATCHes; (3) a sloppy `find … -o -name` matched the wrong file and produced two more false failures; (4) a growth scan flagged a file as `+916 lines` when it had merely MOVED to that path; (5) four faults showing zero alerts looked like a dead alerting path but the escalation threshold is 24h and they were 5h old. **How to apply:** on a RED, before touching the system, ask *"could my payload, my comparison point, or my threshold be wrong?"* and prove the test can go GREEN on a case you KNOW is good. **The compounding version of this — and the most dangerous — is (1): a connectivity / credential / permission test run ON A WORKING MACHINE proves nothing about a fresh one, because the working machine carries the very thing whose absence you are testing.** Pair with the existing "a check that has never been SEEN to fail is not a check": that rule makes you prove the failure path, this one makes you distrust it when it fires.

- **PROVE IT ON A REAL SPECIMEN, NEVER A SYNTHETIC ONE — a fabricated case cannot carry human intent, which is exactly what you need to test against.** (2026-07-28, Step 3's fault proposer.) A new layer that reads failures and proposes fixes passed 5/5 synthetic tests — every altitude derived correctly, the boundary held, the refusal fired. Pointed at the REAL faults open on the machine, its first output proposed fixing two jobs — **both deliberately switched off by a human.** So its first act was to recommend undoing two of the operator's own decisions: the same FAULT-vs-DECISION failure as `4d5c1af`, reappearing *inside the layer built to reason about failure*, minutes after that layer existed. **No synthetic suite could have caught it, because fabricated faults have no human intent behind them.** **How to apply:** when a component's job is to interpret real-world state, its acceptance test is a real specimen, not a fixture — and specifically a specimen that carries a HUMAN DECISION, because that is the class of input a synthetic generator will never produce.

- **★ FOR ANYTHING A HUMAN SEES, THE ACCEPTANCE TEST IS THE REAL INVOCATION PATH — NEVER THE COMPOSER IN
  ISOLATION.** `/ingest`'s reflection screen (`compose_reflection`) was built, unit-tested, and rendered from
  fixtures at a design checkpoint on 2026-07-13 — and **no skill file ever called it.** It sat dead for three
  weeks while the project's own success criterion ("the reflection loop is the reward") read as delivered;
  `grep -rn reflect skills/ingest/` returned only prose about how important it was. Then, wiring it on
  2026-08-04, the very first run through the actual phase commands **crashed** (`AttributeError`) because the
  new upstream step handed it a list of bare strings where it reads `c.get("suggested_category")` — a fixture
  harness passed the same code cleanly, twice. **How to apply:** (1) a feature is not shipped when its function
  is tested, it is shipped when something CALLS it — after adding any composer/renderer/validator, grep for its
  caller before marking the task done (same disease as the writer-with-no-reader rule above, and as
  skill-building-sop §V.9's *"validator-exists-but-nothing-calls-it"*); (2) verify it by running the **exact
  command string the skill file tells the model to run**, with real upstream output, not a hand-built fixture —
  the two differ precisely at the seam where the shapes disagree, and that seam is invisible from either side.
  Corollary caught in the same pass: the phase's own `BRAIN_BEFORE=$(… | head -1)` line would have fed a JSON
  blob to an `int` argument. Nothing but running it would have shown that either.

- **★ VERIFY-FROM-SOURCE APPLIES TO STANDARDS, NOT ONLY TO THIS REPO'S OWN FILES — one socket call beats
  a confident citation.** (2026-08-05, T18.17.3a/f.) A security fix stopped writing an event to the live
  Sentinel ledger for any host under a "reserved" TLD, justified in its own docstring as *"guaranteed-
  unresolvable BY STANDARD… cannot be a real destination."* That claim was **an RFC recalled from memory
  and never executed.** It is correct for `.example` / `.test` / `.invalid` (RFC 2606, RFC 6761 §6.4/§6.5)
  and **FALSE for `localhost`, which RFC 6761 §6.3 REQUIRES to always resolve, to loopback.** Measured
  live in one line: `socket.gethostbyname("localhost")` → `127.0.0.1`, and so does *any* `*.localhost`;
  the other three raise `gaierror`. ⇒ the fix had silently stopped logging the **one** host class that is
  genuinely reachable — anything already listening on loopback (an SSH `-R` forward, a planted proxy, a
  dev tunnel) makes an outbound call at it a working exfil path. **The BLOCK never moved; the RECORD is
  what was lost**, which is that ledger's whole purpose. **How to apply:** when a rule keys on an external
  standard — an RFC, a spec, a vendor guarantee, an HTTP status, a filesystem promise — **run the
  one-liner that demonstrates it on THIS machine before you rely on it.** A standard is a claim about the
  world; "everyone knows" is not a source. Caught by an adversarial auditor charged to REFUTE, not
  confirm — see `/build`'s honest-close and the pairing rule below.

- **★ "FIXING THIS WOULD BREACH THE RAIL" DESERVES ONE GREP BEFORE IT BECOMES A DEFERRAL.** (2026-08-05,
  T18.8b.) A session found a real defect, reasoned that repairing it would require touching a deliberately
  railed-off component, and deferred it in writing with a plausible justification. **It was wrong.** The
  capability needed had been built a week earlier for exactly that call site — `recurrence_by_fingerprint()`
  / `age_s_by_fingerprint()`, whose own docstring said callers *"treat the returned dict identically either
  way"* — and **nothing had ever called them.** The fix was pure wiring; the railed-off function was
  byte-unchanged. **How to apply:** a deferral whose stated reason is "this would require changing X"
  costs one `grep` to test. Search for the capability before you write the deferral — the most expensive
  deferrals are the reasoned, plausible ones, because nobody re-examines them.

- **★ AN INDEPENDENT AUDITOR CHARGED TO *REFUTE* EARNS ITS COST ON THE FIRST RUN — AND ITS SECOND-BEST
  FIND IS USUALLY THE BUILDER'S ARITHMETIC.** (2026-08-05, instituted after it happened twice: *"make sure at the
  end of whatever fix you've got that you have some type of audit that goes back and kind of adversarially
  meets it up."*) The charge matters more than the checklist: *"Prove this is WRONG. Default to REFUTED if
  the evidence is thin."* An audit that sets out to agree is theatre, and the builder cannot run it —
  `build-conductor-sop.md`'s **writer ≠ verifier** applies to fixes, not just features. Two findings on the
  first outing: the security hole above, **and** a cited statistic (`944/4317 = 21.9%`) that re-derived to
  `942/4322 = 21.80%` because the builder had quoted a numerator captured **before** its own verification
  rows landed, against the **later** denominator. **How to apply:** every non-trivial fix gets an
  independent pass whose FOUR questions are (1) does the original symptom actually stop, re-measured from
  source; (2) **does the control still fire on a REAL case** — the one a builder skips, because every fix
  quiets something; (3) what did it break downstream, run the consumers; (4) **re-derive the cited numbers
  from scratch, never re-read the builder's summary.** `INCONCLUSIVE` is a legitimate verdict and must not
  be rounded up to `CONFIRMED`.
  **★ SECOND, STRONGER INSTANCE — 2026-08-07, the project-arming lock, and the numbers are the argument.**
  The builder's own stress harness returned **18 of 18 GREEN** — races, TSV forgery, weaponized env vars,
  corrupted lock state, a 200-attempt switch storm, and a replay of the real incident. An independent agent
  charged *"prove this is bypassable; default to BYPASSABLE if the evidence is thin"* returned **five working
  bypasses in about six minutes**, including the one that mattered most: **the enforcer and the CONSUMER read
  different files** — the lock lived in one script while the thing that actually reported state to the model
  every turn read another and never consulted it, so one direct write re-armed a window with no refusal and
  no trace. A second pass against the fix found **9 of 12 probes disagreeing with intent**, the simplest
  needing **four `cd` commands and a bare relative redirect.** ⭐ **The suite was not weak — it was blind in
  exactly the direction the builder was blind, which is the only direction that matters and the one a builder
  structurally cannot test.** **How to apply:** on any guard, gate, or lock, the acceptance test is not your
  own passing suite — it is an independent pass charged to REFUTE, and **you re-verify its claims yourself
  before accepting them** (all six were reproduced here before a line was changed). Budget the auditor into
  the build, not after it. Full measurements:
  `records/log/2026-08-07-project-arming-lock-adversarial-audit.md`.

- **Sub-agent `usage.output_tokens` is BROKEN — do not trust it.** Measured: it reported **52 tokens
  for a 19,089-byte return.** Use the CLI's `total_cost_usd`, deduplicated by **`request_id`** — ⚠
  note the underscore; it is NOT `requestId`, and using the wrong key silently returns nothing.

- **Never launch a watchable run detached.** `nohup … &` makes the run invisible in the operator's
  window. Use `python3 -u` or the Agent tool so progress is observable.

- **Quote every Drive path.** The Lifehack Drive root contains a space (`"My Drive"`). An unquoted
  path dies mid-argument — and it fails in a way that looks like a different bug entirely.

- **⛔ "CHECKS SETTLED" READ IN THE POST-PUSH GAP IS A FALSE RESULT.** Immediately after pushing to a
  PR branch there is a window where the OLD check run has finished and the NEW one has not queued yet.
  Polling "does every check have a conclusion?" in that window returns TRUE and reports the PREVIOUS
  run's verdict. Measured: it reported FAILURE on PR #119 for a version bump that was in fact correct
  (`0.2.5 > 0.2.4`). **Fix: pin the poll to the pushed HEAD SHA and require every check to carry a
  non-empty conclusion.** ⭐ It produced a false RED here, which is the safe direction — but the
  identical bug produces a false GREEN just as easily. (2026-08-25.)

- **⛔ A PUSH CAN SILENTLY NO-OP AFTER A REBASE.** `git rebase` can drop the branch's upstream tracking
  ref; a bare `git push` then prints `push.default` configuration help to stdout and exits without
  pushing. The remote stays on the old SHA. Measured: PR #124 sat on a stale commit with the old version
  while the local branch was correct, and it was caught ONLY by checking odd-looking output instead of
  accepting it. **Fix: push with an explicit refspec — `git push origin HEAD:<branch>` — and verify the
  remote SHA afterward, never trust the command's own output.** (2026-08-25.)

- **⭐ "SUSPECT THE TEST FIRST" CUTS BOTH WAYS — INCLUDING AGAINST A SUB-AGENT'S REPORT.** The existing
  rule above covers suspecting a failing test. Measured three times in one night that the same
  discipline applies to a LANE'S RETURN: a lane reported the `ship` skill was never fixed — it had
  searched `skills/ship/` while the repo path is `.claude/skills/ship/`. The lead's own verification
  (commit touches the file, commit is an ancestor of the installed SHA, fix present in the installed
  cache) refuted it in three commands. **Rule: when a lane's finding contradicts something you measured
  yourself, re-derive before accepting either. A lane is a witness, not an oracle.** (2026-08-25.)

- **⛔⛔ A CORRECTLY-SCOPED NARROW FINDING, READ BROADLY, IS AS DANGEROUS AS A WRONG ONE.** A lane
  established that plugin-served skills are LISTED to the model only under a namespaced `plugin:skill`
  name — true, well-evidenced, and it honestly flagged that it could not trace the INVOCATION path. The
  lead read that as "bare names do not work" and recommended abandoning a correct fix. A later
  demonstration proved bare-name invocation works fine. **Listing and invocation were different claims
  and only one had been measured.** ⭐ **Rule: when a lane names its own unproven boundary, that boundary
  is part of the finding. Do not round it off. The lane was right and the reader was wrong.**
  (2026-08-25.)

- **⛔ A VALIDATOR PASSING IS NOT THE THING WORKING.** `claude plugin validate` returned "passed with
  warnings" against a plugin that was serving ZERO of its 34 skills. It checks component
  well-formedness, never whether components sit somewhere the loader actually scans. **Rule: a
  validator answers "is this well-formed?", never "does this do anything?" Require a behavioural
  measurement — the count moving, the guard denying, the output appearing — and never accept a
  validator's green as proof of function.** (2026-08-25.)

- **⚠ CONCURRENT WRITES TO ONE LARGE FILE FROM TWO WINDOWS.** Two windows independently persisted the
  same finding into the same ~897KB plan file at the same time. It came out clean — verified no
  duplicate section headers, no adjacent-duplicate lines — but that was luck, not design. **Rule: when
  two windows need to persist the same finding, ONE owns the file and the other relays. Verify
  afterward by checking for duplicated section headers, not by trusting that the writes landed.**
  (2026-08-25. Different failure shape from the stale-prep-clobber rule above — that one is a prep
  going stale between read and write; this one is two live writers landing at once.)

- **⭐ THE SAFE ROUTE FOR PLUGIN EXPERIMENTS (a positive pattern, record it as such).**
  `claude -p "<command>" --plugin-dir <path>` loads a plugin for a SINGLE PROCESS and touches no
  persisted config. ⚠ Also record the inert route so nobody repeats it: copying a plugin cache to
  scratch and repointing `installed_plugins.json` is **INERT** — `claude plugin details` ignores it
  entirely, output unchanged. It is not the real read path. Patching the installed cache in place works
  but requires a byte-for-byte, hash-verified restore. (2026-08-25.)

## Measurement — sizing, grading, and pricing an experiment
- **n=1 resolves nothing.** `EXPRESSION: pooled CV = 22.25%` → `MDE at n=1 = 62.9%`, `n=3 = 36.3%`. A
  null result at n=1 is **`CANNOT RESOLVE`, never "no effect."** State that distinction plainly —
  reporting a null as "no effect" is the failure.
- **Grade on output volume, not the clock.** `EXPRESSION: wall CV 20.4% vs bytes CV 2.3% = 8.9×
  quieter`. The quietest axis that can see the hypothesis is the right one: volume-shaped effects
  resolve on bytes at n=1 where the clock needs n=10. Time-shaped effects (a dead request, fan-out
  width) still need the clock, and still cost repeats.
- **Fan-out is genuinely concurrent but it is NOT free.** `EXPRESSION: n4/n1 = 73.87/52.53 = 1.41×`
  against `4×` if it were serial — so parallelism is real, but there is a **~30–41% spawn-and-collect
  toll** that must be priced into any fan-out estimate.
- **A count is only as good as the shape you searched for — and nobody writes the shape down.** Three
  correct searches on 2026-08-27, each measuring a population that wasn't the one in question: a
  "runner missing" count that searched the repo when the runners live in the AI Brain (true answer:
  ZERO of 23 missing); a row reported absent by its label (`token-burn-mine`) when the file existed
  under its filename (`token_burn_mine.py`) — label ≠ filename, hyphen ≠ underscore; a PII sweep that
  matched email-shaped strings and home paths and so missed seven more tracked files carrying the same
  identifier as a bare username — precise about the wrong shape. In all three the search **ran
  correctly and returned a true fact about the population it actually searched**; nothing errored, so
  the miscount was invisible from the output. Same family as: a registration count of 71 reached by
  grepping for a helper's *absence* (real number, by reading all 47 by hand: 12); `timeout` not
  existing on macOS (exit 127, no output, reads clean); a lint invoked `--files $VAR` under zsh that
  checked zero files and exited 0. **Before trusting any count, write down the shape you searched
  for — tree, string/label, regex class — and ask whether that shape is the population in question.**
  A negative result is only as good as the name, the tree, and the pattern behind it.

## Domain — background / scheduled runners

> ⚠ **THE SCHEDULER AND DASHBOARD NAMED BELOW ARE NOT PART OF THIS REPO.** These entries were learned
> on one particular interval scheduler and one particular status page, neither of which ships here.
> They are kept, and kept specific, because **every one of them is about a property of scheduled work
> rather than about that scheduler** — what a runner's exit code should mean, why a job that only
> fires on Wednesdays looks broken six days a week, why a launchd job cannot see the things your
> terminal can. The first person here to write a cron entry will meet all of them. Read the shape,
> ignore the product names.
- **Reuse the engine, don't re-derive.** Model new runners on the shared-lib pattern: machine-gate → headless
  auth → lock + watchdog → do the work → emit a status record. ⛔ The reference runners this line named
  are part of the personal system it came from and do not ship here; the six-step shape is the point.
- **Eager-expand cleanup paths INTO the EXIT trap.** A `local` var referenced by an `EXIT` trap is out of
  scope when the trap fires and dies under `set -u`, so cleanup silently never runs (→ stale lock → next run
  skips). Write `trap "rm -rf '$lockdir' …" EXIT`, NOT `trap 'rm -rf "$lockdir" …' EXIT`.
- **gws `--upload` sandboxes to the cwd** — it rejects a path outside the working dir. `cd` to the dir that
  contains the file before uploading (the archivist runner `cd`s to `$DRIVE`; its queue lives under `$DRIVE`).
- **Exit 0 on a found-RESULT; non-zero ONLY when the tool itself broke.** the scheduler's circuit breaker disables a
  job after 3 consecutive non-zero exits, so "found drift / found work" MUST be a success exit.
- **Seed the scheduler's last-run = now when enabling a just-proven job**, in whatever state file it keeps, so it
  doesn't immediately re-fire on the next 5-min tick.
- **Machine-gate on `scutil --get ComputerName`, never `hostname`** (on macOS a machine's `hostname` can be a
  default that identifies nothing — one of ours was literally "Mac"; on other platforms use that OS's
  equivalent stable machine-name lookup).
- **Don't run the same Drive-stateful cron on two machines at once** — no cross-machine lock; gate to one.
- **An INTERVAL scheduler cannot pin a job to a clock or calendar time.** It fires when `now − last_run ≥
  interval_seconds`, nothing more. A job that must hit a wall-clock moment (4am daily · Friday-EOB · 1st-of-month ·
  Jan-1) needs a DEDICATED CRONTAB LINE, not an interval entry. (2026-06-10, building a daily-digest cron.)
- **A cadence/day-windowed cron job cannot be monitored by exit code and staleness alone.** "Correctly skipped"
  and "never fired" are both exit 0 plus silence, and time-based staleness reads CORRECT silence as BROKEN —
  a Wednesday-only runner flags STALE roughly 3 days in 7 with zero missed runs. **A windowed job must emit
  three distinct states: skipped-on-purpose · never-fired · ran** — collapse them into a bare exit code plus a
  staleness clock and the monitor cannot tell a designed silence from a dead job.
- **In a cron-run script, call `/usr/sbin` + `/sbin` binaries by ABSOLUTE PATH.** Cron ships a minimal PATH
  (`/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin`) with NO `/usr/sbin` — a bare `scutil`/`system_profiler` isn't
  found, `$(…)` returns empty, and any gate built on it silently takes the wrong branch with no error. Worst case: a
  machine-gate that exits 0 on its "skip" branch reports success, the breaker never trips, and the emit silently
  freezes (a GREEN ILLUSION). Use `/usr/sbin/scutil`, and verify gates under the real cron PATH (`env -i PATH=… bash
  script.sh`), not an interactive shell. (2026-06-12: three scutil-gated runners were
  emitting only on manual in-session runs; the system-health dead-man's-switch was itself frozen by this.)

- **A cron-runner pre-flight check should RETRY before declaring failure.** A single auth/health probe
  (gws `getProfile`, an API ping) can fail on a TRANSIENT blip — an access-token mid-refresh, a momentary
  API hiccup. At a 5-min cadence, three such blips in 15 min trip the scheduler's circuit breaker on a runner whose
  auth is actually fine, and it then sits disabled until a human resets it. Wrap the pre-flight in a small
  retry (e.g. 3 attempts × 4s) so a transient blip becomes a brief wait, not a hard non-zero exit + breaker
  strike. (2026-06-13: a runner auto-disabled for ten minutes on 3 transient pre-flight failures; the
  identical getProfile was healthy minutes later. Reset the breaker + added the retry.)

- **A gate function that `exit`s the runner must be called INLINE, never via `$(...)`.** `exit` inside a
  command-substitution exits only the SUBSHELL, so the parent script sails on. If the gate also needs to
  RETURN a value, set a GLOBAL var (not stdout) so the caller invokes it inline and the `exit` actually
  fires. (2026-06-13: `ingest-run.lib.sh`'s new-mail gate was called as `CUTOFF=$(ingest_new_mail_gate ...)`;
  its cheap-exit only killed the subshell → empty cutoff → the runner processed 10 backlog emails instead
  of exiting. Fixed: gate sets `$INGEST_CUTOFF`, caller invokes it inline.)

- **A status record's own "how did this get here" field is LOAD-BEARING for how it renders — a live
  scheduled job must not be labelled as hand-run.** The dashboard it was built for collapsed any
  hand-run record with no metrics into a one-line stub, so that label on a LIVE job hid all of its real
  data and the job read as empty. (2026-06-14: one record left with its setup-time label → all 9 real
  systems were hidden behind a placeholder.) ⛔ That dashboard is not part of this repo. The lesson
  that is: **a metadata field the renderer branches on is functional, not descriptive** — verify a
  record actually renders before calling it wired.
  **Verify generated data (a tile, fixture, or mock) against the EXACT fields the consumer READS — not a coarse
  "the block exists" proxy: a payload can pass a presence/structure check yet render blank on a key-name mismatch
  (`net` vs `net_mo`, `label` vs `name`, a `"2025-07"` string vs numeric `year`/`month`). (2026-07-06: a dashboard demo
  fixture had every top-level block present but the cards rendered empty until a field-level audit against the
  renderer's actual keys fixed the mismatches.)**
- **Validate every status record through ONE write-time validator** ⛔ (the one this was learned on,
  `emit_status.py`, belongs to a dashboard that does not ship). The rule is the shape: envelope
  + declared `required_payload` contract fields, atomic write, fail-loud at the source). Don't hand-roll `json.dump`
  for a tile — a malformed tile must scream at the emitter, never silently go empty at the dashboard.

- **⚠ SECOND OCCURRENCE 2026-07-28 (S2.4) — the rule below protects OTHER windows from you; NOTHING protects you from THEM. Here is the victim-side procedure.** Staging narrowly is necessary and was done: 16 files staged by explicit path, `git status` confirmed clean of other windows' work. A parallel window still committed everything dirty ~seconds later, so our `git commit -F -` returned **"nothing to commit, working tree clean"** — the alarming-looking outcome that actually means *your work is already committed under someone else's message*, not that it vanished. **DO NOT re-stage, re-apply, or panic-rebuild — you will double-apply.** Procedure, in order: **(1) VERIFY THE WORK SURVIVED before anything else** — `git cat-file -e HEAD:<path>` for each expected deletion (absent = deleted, as intended) and `git show HEAD:<file> | grep <your marker>` for each expected edit; nothing is lost if these pass. **(2) Check whether the sweeping commit is PUSHED** (`git branch -r --contains <sha>`). **(3) If pushed → NEVER rewrite history**; record the attribution split in the NEXT commit message and in the plan, so the record is self-documenting rather than silently wrong. **(4) If not yet pushed, still prefer recording over rewriting** — a rebase across ~7 live windows costs more than a confusing log line. **The deeper lesson: "nothing to commit, working tree clean" is AMBIGUOUS in a multi-window clone** — it means either "I already committed this" or "someone else did." Disambiguate by checking the CONTENT at HEAD, never by re-running the commit.
- **A CONCURRENT window's broad `git add`/`commit -a` will sweep up YOUR in-progress files — under ITS commit message.**
  While F2.2 was mid-build, another session (working on `skill-building-sop.md`) committed everything dirty in the
  clone: `fd16e34 docs(sop): promote the floor→instrument mapping [SKILL-SYSTEM]` silently carried a 388-line
  `organism-health.py` + an 11-line `system-health.py` change that belonged to a different feature — and pushed it.
  Nothing was lost or clobbered, but the history now attributes half a feature to an unrelated docs commit, and
  `git status` showed my own new file as already-tracked-and-clean, which reads like the edit never happened.
  **Rules:** (1) with ~7 parallel windows, `git status` is NOT a reliable record of what YOU changed — diff against
  the specific commit you expect, not against HEAD; (2) stage NARROWLY (`git add <explicit paths>`), never `-A`/`-a`,
  precisely so you don't do this to another window; (3) when it happens and the sweeping commit is already PUSHED,
  do NOT rewrite history — record the split in the later commit message + the plan so the attribution is
  self-documenting. (2026-07-27, F2.2.)

- **`/usr/bin/python3` on macOS is 3.9 — a `X | None` annotation is a RUNTIME crash, not a lint nit.** Cron and
  those runners invoke the system python, so a 3.10+ union annotation in a tool's signature raises
  `TypeError: unsupported operand type(s) for |` at IMPORT time and the job dies before doing anything. Add
  `from __future__ import annotations` (3.7+) or use `Optional[...]`. Verify a new tool with the same interpreter the
  harness will use, not a newer homebrew one. (2026-07-27, F2.2's producer crashed on its first run.)

- **A stat-cell/list CSS class may reflow an ORDERED sequence into meaninglessness — check the class's grid rule
  before reusing it.** a dashboard's shared `.sy-chk` class is a global `grid-template-columns:1fr 1fr`, which turned a 4-row
  enforcement FUNNEL (stated → hook-backed → fire-proven) into a 2×2 block read left-to-right, destroying the
  narrative; and an emitted `tone:g-b` on a `.sy-q-n` stat number had NO css rule, so a tile "going amber" rendered
  in default ink. **Reusing a design-system class is not free: confirm it renders your SEMANTICS (order, emphasis,
  tone), and look at the actual render — neither of these was visible from reading the code.** Fix was a one-column
  modifier + the two missing tone rules, no new colours. (2026-07-27, F2.2.)

- **★ PASSING `name:` TO THE `Agent` TOOL SILENTLY DESTROYS THE HELPER'S REPORT — the fix is to DROP THE NAME,
  not to instruct the agent to deliver.** `name:` is not a label; it is an undocumented **mode switch**. Unnamed →
  a sub-agent, and its final text comes back as the tool result. **Named → an addressable teammate with a mailbox,
  and its final response text is DISCARDED on exit** — the tool result is only `Spawned successfully… will receive
  instructions via mailbox`. The sole surviving channel is whatever the agent chose to put inside a `SendMessage`
  call, which is a judgment it was never told it was making.
  **Measured 2026-08-01 across every spawn in this machine's transcripts:** named **249 spawns → 0 returned a
  payload (0%)**; unnamed **1,714 → 1,714 (100%)**. Not a tendency — a wall.
  **`run_in_background: false` does NOT help — `name` overrides it.** Proven by live A/B (identical haiku workers,
  same prompt, both synchronous): the unnamed one returned its text, the named one returned spawn metadata while
  its text sat in its own transcript on disk. *This is why the bug survived three separate investigations: the one
  lever that looks like the fix isn't.*
  **Rules:** (1) **Do not name a fan-out helper.** Names are only for agents that must genuinely address each
  other (an agent-team wave); (2) if you must name one, the prompt has to instruct it to return its FULL text via
  `SendMessage(to:"main")` — **but treat that as the weak fallback it is**, see the disproof below; (3) an idle
  notification means FINISHED, not DELIVERED; (4) do **NOT** reach for `TaskOutput` — for agent tasks its output
  file is a symlink to the ENTIRE subagent transcript and will overflow the window. **To recover work already
  stranded, use `system/tools/cowork-ingest/agent_output.py --raw`,** which pulls a prose report out of the
  transcript's SendMessage payloads (the default JSON-only mode silently drops prose).
  **Enforcement:** ⛔ the hook that enforced this (`guard_agent_return_channel.sh`, PreToolUse on the
  `Agent` matcher) does not ship here — nothing in this repo spawns named agents yet. It blocked a named spawn
  whose prompt states no delivery contract; fire-proven as `agent-return-channel-guard` in `label_manifest.yaml`.
  **(2026-07-27 → 2026-08-01. Two incidents:** six council advisors, five reports lost; then five research agents
  on 2026-07-30 stranding **90,280 characters** *and* filing a false root-cause to disk — that session concluded
  *"the return channel is unreliable, ~60% failure"* when the truth was 100% and deterministic. **The earlier
  version of this very bullet prescribed the wrong fix** — *"the spawn prompt must state the delivery mechanism"* —
  and the 2026-07-30 round is its disproof: **all five prompts carried that instruction and all five still lost
  work**, because an instruction cannot stop a model from putting a report where reports go. A doc rule failed, a
  skill-scoped rule failed to generalize, the prompt itself failed; that is what promoted this to a hook. Same
  disease as the 2026-07-27 cluster — something reporting success while producing nothing observable — alongside a
  dashboard tile "going amber" in black ink, a token table that read 0.0%, an 11-day-dead watchdog, and a git
  commit that swept up another window's work.)**

- **Run a "dead" cron job by hand under the REAL cron PATH before believing it is broken.** Two jobs flagged dead
  for 11 and 28 days both exited **rc=0 clean** on a manual `env -i PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin`
  run. Neither was ever broken: transient blips tripped the 3-strike circuit breaker, which then held them disabled
  indefinitely — "disabled until a human resets it" means "off forever" in a single-operator system with no on-call.
  **Diagnose before re-arming** (else you re-enable a genuinely broken job and it re-trips), and treat a breaker with
  no auto-retry and no loud state as a design defect, not bad luck. (2026-07-28.)

- **A doc routed behind a CONDITION is unreachable when the condition is the very thing that doc decides.**
  `build-rules-index.md` routed `build-conductor-sop.md` — the file that says "delegate to sub-agents by
  default" — only for *"an orchestrated / parallel build."* You could only read the rule that tells you to
  delegate once you had already decided to delegate. `/build` Step 0 classifies by **artifact** ("hook? skill?
  cron?"), never by shape, so an ordinary build never matched the row and the doc was never opened. Measured:
  across four `/build` sessions on 2026-07-28 that spawned **zero** sub-agents, the other three binding docs
  were read every time and this one never was (`Agent` calls fell from 273/2372 = 11.5% on Jul 9–12 to 6/1079
  = 0.6% on Jul 28, counted from the raw session transcripts). **Rule: when a doc's job is to make a DECISION,
  it cannot be gated on the outcome of that decision — route it ALWAYS.** The general test for any routing
  table: for each row, ask "could a build that NEEDS this doc fail to match this condition?" If the condition
  restates the doc's own conclusion, it's circular. (2026-07-28, the subagent-delegation repair.)

- **A tag one file writes and no file reads is dead plumbing — check the consumer exists.** `/autoplan` had
  been faithfully gear-tagging every task, and `architecture-planning-sop.md` promised *"`/build` re-decides
  the gear per task."* `/build` had no gear logic at all — the word appeared once, inside a cost note. The
  producer was correct, the contract was documented, and the consumer was never built. **When you add a field,
  tag, or annotation to an artifact, grep for the thing that READS it before calling the feature done** — a
  writer with no reader passes every check it has, because it has none. Same disease as the seam-testing rule
  in `skill-building-sop.md` PART V §V.5: both ends worked, the wire between them didn't exist.
  (2026-07-28, same build.)

- **When a string is demonstrably IN the running system but absent from EVERY config file, the remaining
  place is the BINARY — `strings -a <bin> | grep`, then VERSION-BISECT across installed versions to date
  it.** Three separate investigations hunted the source of a session instruction ("Do not call the
  AgentTool unless the user requested it"), searched only config, and each reported *"source unknown"* —
  two of those were mine, and one mis-attributed it to *"your harness config"* as an unverified claim
  stated confidently. It was compiled into the Claude Code binary. The bisect that dated it took one loop:
  `for v in ~/.local/share/claude/versions/*; do echo "$(basename $v) → $(strings -a "$v" | grep -c '<str>')"; done`
  → `2.1.195` 0 · `2.1.218` (Jul 24 12:37) 0 · `2.1.219` (Jul 24 15:44) 3. Two versions the same day,
  three hours apart, and only the later one carries it — which pinned the change to a date and let it be
  correlated with a measured behaviour collapse. **Practical rule: "not in any config" is a HALF-answer.
  The binary, the harness, and the model's own system prompt are all upstream of config, and the binary is
  the one you can actually grep.** (2026-07-28.)

- **`grep -rl --include=*.json …` SILENTLY NO-OPS under zsh when the glob doesn't match in cwd — and its
  empty output reads exactly like "not found."** Two "clean" searches in the investigation above never
  actually ran; their emptiness was recorded as evidence of absence and cost a full round each. Same
  family as the standing rule *"when a test says the system is broken, suspect the test first"* — an
  unrun search and a search that found nothing are indistinguishable from the output alone. **Fix: pass
  explicit paths rather than relying on a glob, or `set -o nullglob`/quote the pattern, and sanity-check
  the search by grepping for something you KNOW is present before trusting a negative.** (2026-07-28.)

- **A NUMBER WITHOUT A UNIT IS THE DRIFT — the arithmetic is usually fine.** A plan's CONTEXT said "63 plan
  files" while its Phase 6 said "76." Both were **correct about different units** — 63 *files* on one date vs
  76 *plan-flag entries* — and neither stated which, so they read as a contradiction and invited a "fix" that
  would have destroyed a true figure. **How to apply:** every count you write states its **date** and its
  **unit** (`63 files, 2026-07-28`), and when two figures disagree, ask *"are these even measuring the same
  thing?"* before assuming one is stale. Correct a stale figure by **dating it in place**, never by
  overwriting — the old number is evidence about when the world changed. (2026-08-01, project-system Phase 7.)

- **★ AN EVENT THAT CORRECTS A STALE NUMBER DOES NOT CLOSE THE WORK — paid for twice in one week.**
  "Nine promote blocks" was corrected to "three" — the three were still unapplied. "86 uncommitted
  files" was corrected to "73" — the files were still uncommitted. Both times the corrected label got
  read as a finished job. **The mechanism:** a correction FEELS like a resolution — striking a wrong
  figure produces the same satisfaction as completing the task, so the label now looks *handled* and
  nobody re-opens it. A struck-through item reads as done; an unstruck one at least reads as open —
  which makes this class worse than plain staleness. **How to apply:** when correcting a count, state
  the WORK STATUS separately and explicitly in the same edit — *"nine → three, and all three remain
  unapplied"* is a status; *"nine → three"* alone is just a number. Never let the first stand in for
  the second. Same family as the "NUMBER WITHOUT A UNIT" rule above and as the recorded case of a
  correction that announced four stale locations and struck four while eight existed — a correction
  that misses its own instances leaves the error live while looking resolved. (2026-08, two measured
  instances.)

- **VERSION ON THE WAY OUT, NEVER ON THE WAY IN — a version slot at creation is a fork button.** Asked to
  "make space in the filename for versioning, just in case," the tempting answer is `<name>.v2.ext`. That
  re-opens *"which one is live?"* — the exact question a one-file-per-thing rule exists to close. The safe
  shape: the live file has ONE predictable name forever, and **renaming is permitted only at retirement**
  (`<name>.<YYYY-MM-DD>-retired.ext`). Retirement is a one-way door; creation-time versioning is an
  always-available fork. Prefer a **date** to a version number — it sorts itself, explains itself, and needs
  no knowledge of the sequence. (2026-08-01, the plan-filename scheme.)

- **WHEN A DELIBERATE CHOICE AND AN ACCIDENT PRODUCE THE SAME ARTIFACT, THE PREFIX IS THE WHOLE SAFETY
  PROPERTY.** Allowing "a plan with no project" risked re-creating the 47 orphaned plan files that a prior
  phase had just cured — because a deliberate standalone and an accidental orphan are *the same file*. Two
  things made it safe, and both are structural, not procedural: (1) it is **CHOSEN, never defaulted-into** —
  the prompt still ASKS and offers it as one named answer, so it can never happen by falling through; (2) a
  **`standalone-` filename prefix** so any future sweep can tell deliberate from accidental at a glance.
  **How to apply:** before legitimising a shape that already exists as a known failure, ask *"how will a
  future sweep tell the good one from the bad one?"* — if the answer is "by reading it," you need a marker.
  (2026-08-01.) Same family as the fault-vs-decision rule above: an artifact carrying no provenance gets
  read as the failure case.

- **A SECTION YOU ARE RETIRING MAY BE THE ONLY HOME OF A RULE'S REASONING — check before you fold it.**
  Folding five ⛔ dead-end bullets out of a retired section and into a Story Log looked like pure relocation.
  **Two of the five had no `why` anywhere else** — their reasoning existed only inside a human-only FRAME
  block that must never be edited, and a doctrine section that stated the rule but not its origin. The fold
  wrote that reasoning down for the first time. **How to apply:** when consolidating or retiring a section,
  grep each item's *justification* (not its statement) elsewhere first; where it doesn't exist, WRITE IT
  rather than assuming the destination already has it. A rule that survives without its why is the one that
  gets re-litigated. (2026-08-01.)

- **ONLY NAME A SUB-AGENT WHEN IT MUST BE ADDRESSABLE — a named spawn's final report is DISCARDED.**
  Measured on this machine: **249 NAMED spawns returned a payload 0 times; 1,714 UNNAMED spawns returned one
  every time.** A `name:` turns the agent into an addressable teammate with a mailbox, and its final response
  text goes nowhere; `run_in_background: false` does NOT rescue it, because `name` overrides it. **How to
  apply:** omit `name:` and the full report arrives as the tool result. If you genuinely need it addressable
  for coordination, put *"return your FULL text via SendMessage to main"* **in the birth prompt** — a gate
  sent to an already-running agent arrives too late. (2026-08-01; `guard_agent_return_channel.sh` caught this
  on a build lead who named two helpers out of habit.)

## DO NOT BUILD — what was tried and failed

> **DUPLICATED BY DESIGN.** This section is deliberately repeated, near-verbatim, in `build-sop.md`,
> `hook-sop.md`, and `skill-building-sop.md`. Ruled 2026-08-07, after a retired rule got
> re-installed TWICE in one day because no SOP could tell a session "this was already tried and
> killed": *"I would rather have duplication than miss something."* **Do not "helpfully" de-duplicate
> this across the three files** — that is the exact failure this section exists to prevent. Source:
> `state/projects/skill-builder/records/2026-08-07-dead-end-harvest.md` (80 entries, this file carries
> the ones relevant to BUILDING, ORCHESTRATION, SUB-AGENTS, MODEL CHOICE, and TEST VALIDITY).
>
> **The pattern underneath every entry below:** something reported success while producing nothing
> observable. A logger that captured zero entries under 300+ daily calls. A guard whose deny path
> exited 0. A judge that flagged nothing across 40 turns. A test that passed because it wrote its own
> exam. That is the shape to look for before you re-try any of these.
>
> Tags: `UNIVERSAL` = ruled 2026-08-07 to bind any build, anywhere. `LOCAL` = failed for us, in
> our circumstances — may not generalize, but don't re-run it here without a reason. Where this SOP
> **already states a lesson in full** (found by a duplication check before writing this section), the
> entry below is a one-line cross-reference instead of a restatement — go read the original.

### 1. Cheap models and cheap judges cost more than they save

- **A4 — downgraded `/ingest` SCAN from sonnet to haiku for ~8x cost saving.** FAILED: haiku "lost the
  intuition that recognizes a chat's project + senses a mis-file"; reverted at commit `779157c`.
  `2026-07-11` · `records/reference/2026-07-12-stage2-email-interpret-method.md`. REPLACED-BY: kept
  sonnet, sought savings via bigger batches instead. `UNIVERSAL` — *"savings from bigger batches are
  durable; savings from a weaker judgment model are not."*
- **A5 — "Plan v6," moved spawned helpers to haiku, projected ~$267.79/mo recovery.** FAILED: realized
  $0 — the convertible bucket measured zero, the spawn-floor guard was vetoed 7/7, a template fix was a
  verified no-op, and the "untyped spawns" thesis measured zero real unpinned sites. `2026-07-28` ·
  `records/decision/2026-07-28-model-efficiency-plan-abandoned.md`. REPLACED-BY: plan killed outright;
  the 7 existing model pins kept only as escalation-prevention. `LOCAL`
- **A33 (recurred B37) — a Stop-hook LLM "bounce judge" that regenerates a reply failing a quality
  check.** FAILED three ways: self-critique degrades output; latency measured 6s → 47–61s per call
  (CLI cold-start, not inference); and across ~30–40 live turns the grader flagged **zero** real
  violations — a rubber stamp (cheap-judge true-negative rate is structurally <30% per Jain et al.,
  NeurIPS 2025). `2026-07-12/13` · `records/2026-07-13-translator-voice-debug-history.md`;
  `state/projects/translator-voice/brief.md:97-122`. REPLACED-BY: killed outright; a 3-layer plan
  (output-style + examples, a parked grader, a planned local classifier). `UNIVERSAL`
- **A34 — readability formulas (Flesch-Kincaid, Gunning Fog, SMOG) as a proxy for reply density.**
  FAILED: "barely correlate with perceived difficulty on technical prose." `2026-07-12` ·
  `records/2026-07-13-translator-voice-debug-history.md`. REPLACED-BY: a holistic test + a planned local
  classifier. `UNIVERSAL`
- **B23 — collapsed four map-agent lenses into ONE agent to save time.** FAILED: measured **35 findings
  vs 82** at nearly the same wall-clock — "not faster, it is shallower." `2026-08-05` ·
  `state/projects/skill-system/brief.md` (wave B1). REPLACED-BY: kept four separate lens agents.
  `UNIVERSAL`
- **B25 — an item budget ("do only N of these") as a way to make an agent run faster.** FAILED:
  compliance near-perfect but the clock **rose 1.35x** — the agent still read everything; the budget
  only trimmed the reported output. `2026-08-05` · `state/projects/skill-system/brief.md` (wave S).
  REPLACED-BY: abandoned as a speed lever. `UNIVERSAL`
- **B26 — collapsed a proven multi-agent fan-out into one inline prompt.** FAILED: measured **2.06x
  worse wall-clock**. `2026-08-04` · `state/projects/skill-system/brief.md:409-473`. REPLACED-BY: kept
  the fan-out. `UNIVERSAL`
- **B27 — stripped a dispatch/spawn prompt to save input tokens ("lean-brief").** FAILED: pointed
  backwards — the LONGER prompt ran on the faster day; under-specification is paid back in output
  tokens at roughly **100x** the input price. `2026-08-04` · `state/projects/skill-system/brief.md:409-473`.
  REPLACED-BY: kept fully-specified prompts. `UNIVERSAL`

### 2. Tests that grade their own homework

- **B30 — an "arrow-sequence" regex signature to detect a clause pattern.** FAILED: **50% false
  positives on real data** — it passed 10/10 only on a fixture written from the same mental model as
  the regex ("grading its own homework"). `2026-07-29` · `state/projects/skill-system/brief.md:1349-1351`.
  REPLACED-BY: killed, do-not-re-add (commit `36ddc93`). `UNIVERSAL`
- **B16 — verified a human-facing screen with a test FIXTURE instead of the real invocation path.**
  FAILED: a fixture passed a DEAD reflection screen TWICE; only the real path caught it. `NO-DATE` ·
  `state/projects/ingest-skill/brief.md:147-172`. → **already stated in full in General** ("★ FOR
  ANYTHING A HUMAN SEES, THE ACCEPTANCE TEST IS THE REAL INVOCATION PATH" — the `compose_reflection`
  / `AttributeError` case) — go read that bullet, not restated here.
- **A13 — a multi-agent "council" of same-model design-critique personas.** FAILED: "same-model
  personas don't reproduce independent reviewers" (cites Park 2024) — error amplification. `2026-06-04`
  · `records/decision/2026-06-04-design-lifehack-skill.md`. REPLACED-BY: one skill, 7 lenses as
  internal sections. `UNIVERSAL`
- **A35 — a mechanical section-counter (>=5 bold headers = "reads like a report") as the sole
  wall-of-text detector.** FAILED: couldn't distinguish a mild wall from a genuinely good reply.
  `2026-07-12` · `records/2026-07-13-translator-voice-debug-history.md`. REPLACED-BY: folded into the
  3-layer approach. `LOCAL`

### 3. Sub-agent orchestration

- **A40 — a doc-level rule prescribing "the spawn prompt must state the delivery mechanism" as the fix
  for lost sub-agent reports.** FAILED — **disproven**, not just abandoned: five research agents
  carried that exact instruction and all five still stranded their reports (90,280 characters lost) —
  "an instruction cannot stop a model from putting a report where reports go." `prescribed
  pre-2026-07-27, disproven 2026-07-30` · `records/insight/2026-08-01-agent-name-discards-report.md`.
  → **already stated in full in General**, twice — "★ PASSING `name:` TO THE `Agent` TOOL SILENTLY
  DESTROYS THE HELPER'S REPORT" and its restatement near the end of this file (249 named spawns → 0
  payloads; 1,714 unnamed → 100%). Not restated here; this entry is the record that the doc-rule fix
  was tried FIRST and failed on its own terms before the hook was built.
- **B11 — spawned ingest readers as NAMED teammates.** FAILED: "they get SendMessage, ship JSON via
  it, collector gets prose" — nothing usable arrives. `NO-DATE` · `state/projects/ingest-skill/brief.md:147-172`.
  REPLACED-BY: spawn as plain background agents. `UNIVERSAL` — same family as the named-spawn bullet
  above; **fired live again during the harvest work that produced this very section.**
- **B24 — tested "one agent, four lenses" by handing one agent the four per-lens dispatch briefs.**
  FAILED: the agent **re-delegated** — spawned its own four sub-agents — voiding the measurement.
  `2026-08-05` · `state/projects/skill-system/brief.md` (wave B1). REPLACED-BY: rewrote the dispatch as
  "you personally perform these four analyses." `UNIVERSAL`
- **B33 — ran huddle seats + the coordinator inside the MAIN (opus) session loop.** FAILED: burns opus,
  freezes the window for the whole meeting, dumps the full board into main context. `NO-DATE` ·
  `state/projects/huddle/huddle-skill/brief.md:58-86`. REPLACED-BY: every participant + the chair runs
  in a background sonnet sub-agent. `UNIVERSAL`
- **B34 — a background watch loop for huddle "breadcrumbs."** FAILED: writes to a file the human can't
  see — "KILLS the live feed." `NO-DATE` · `state/projects/huddle/huddle-skill/brief.md:58-86`.
  REPLACED-BY: `coord-wait` — foreground streaming with early exit. `LOCAL`
- **B35 — writing detailed implementation plans inside the live huddle.** FAILED: "makes sessions go
  solo/silent/slow -> they time out + watch-loop." `NO-DATE` · `state/projects/huddle/huddle-skill/brief.md:58-86`.
  REPLACED-BY: huddle aligns scope only; plans written after, solo. `LOCAL`
- **B36 — letting participants self-declare "done" as the huddle exit signal.** FAILED: sessions kept
  bumping out prematurely. `NO-DATE` · `state/projects/huddle/huddle-skill/brief.md:58-86`. REPLACED-BY:
  "done" is a revocable alignment vote; only the coordinator closes the room. `LOCAL`
- **B21 — `set -e` inside a retry loop over N model/subprocess calls.** FAILED: "it destroyed a run that
  already had 3 of 4 lanes done." `NO-DATE` · `state/projects/skill-system/brief.md:122-136`.
  REPLACED-BY: not stated in source — but the shape is clear: don't let one lane's transient failure
  kill lanes that already succeeded. `UNIVERSAL`
- **B22 — `MAX_THINKING_TOKENS` as a repair/speed lever.** FAILED: "INERT, ignored even at the top
  level" — measured, no effect. `NO-DATE` · `state/projects/skill-system/brief.md:122-136`. REPLACED-BY:
  abandoned. `UNIVERSAL`
- **B7 — polite prompt instructions as enforcement gates in a skill.** FAILED: "the AI reasons past
  prose gates." `NO-DATE (LOG-04)` · `state/projects/lifehack-cowork/brief.md:280-298`. REPLACED-BY:
  an external bash gate (`test -f GATE.ok || exit 1`), never skill prose. `UNIVERSAL` — same family as
  the "prose reminder is fakeable checkbox theater" finding in General's build-router bullet.

### 4. Concurrency and provenance

- **A12 — mapped a session to "its" plan file by newest-mtime in `~/.claude/plans/`.** FAILED:
  cross-wired across parallel windows — a session's status bar showed ANOTHER window's plan. `2026-07-13`
  · `records/decision/2026-07-13-statusbar-hud-build.md`. → **already stated in full in General**
  ("Mapping a session → 'its file' by NEWEST-mtime is unreliable across concurrent windows") — go read
  that bullet. This harvest entry adds only: still **NOT YET FIXED**, tracked as open debt
  `[STATUSLINE-PLAN-CROSSWIRE]`. `UNIVERSAL` — never key a per-session artifact off file mtime under
  concurrency.
- **Tried:** answering a DELIVERY problem by building DETECTORS. **Failed:** 863 lines shipped in one day,
  **ZERO with a caller**, while 10 existing per-turn injectors sat unused; the shared module built to end
  the recurring class was adopted by 3 of 15 tools. `2026-08-08` · `state/projects/project-system/brief.md`
  → replaced by one line in an injection that already fires. **8th recorded instance of build-with-no-caller
  in this system** (prior: `compose_reflection` · `judge.py`/`push_gate.py` — *"I built the lock and never
  built the key"* · `check_screens.py` · 4 unused shared primitives). See **THE CODE SPIRAL**,
  `system/build-rules-index.md`. **UNIVERSAL**

## How to extend this SOP
A build taught you something durable + reusable? Append it under the right section — **General** if it applies
to any build, a **domain** section otherwise. This is the one file `/build` reads: keep it tight, prune dupes.


## Sub-agent orchestration (added 2026-07-25, from the skill-system consolidation session)
- **Gates go in the BIRTH PROMPT, not the mailbox.** A constraint sent to an already-running agent arrives late
  or never — we watched a trust-gate amendment land after the agent had finished cloning. Any rule that must
  hold goes in the spawn prompt itself; a mid-flight message is a hope, not a control.
- **Rate-storm survival:** when a session is huge and the API is throttling — (1) bank every intermediate
  finding to DISK the moment it exists (records/, the pad) so nothing depends on the session surviving;
  (2) do the big single-shot write from a FRESH near-zero-context session reading only the banked files —
  never from the bloated window; (3) if you must write big in-session, split across parallel sonnet writers
  each owning a SEPARATE output file, so one connection death costs one section, not the artifact.

- **A status-string guard must test a POSITIVE marker, never a substring — the negative state often CONTAINS the
  positive token.** The FC tenant-billing script gated its tenant send with
  `nrGet_('billing_ready').indexOf('READY') === -1`. The not-ready value is the literal `"🔴 NOT READY"`, which
  **contains** `"READY"` — so the abort never fired and green and red both sent. The gate was **decorative from the
  day it shipped** (2026-05-11) until 2026-06-09, and the sheet's own `billing_ready` formula had been correctly
  showing 🔴 the whole time; the script just never asked it properly. Cost: a tenant statement went out with a
  blank submeter reading, overbilling by $50. The old test was ALSO case-sensitive, so it would have wrongly
  BLOCKED a legitimately green light — broken in both directions. **FIX PATTERN:** test a positive marker AND
  require the negative token absent (two independent signals, so neither changing alone silently opens the gate),
  and **fail CLOSED** on anything unexpected — blank, error, renamed label. Applies to ANY status guard anywhere
  (sheet cells, JSON status fields, CLI output parsing), not just Apps Script. (2026-06-09, FC tenant billing —
  property/tenant/figures in this example are invented for anonymity, not the real incident; do not "restore" them.)

- **A check that has never been SEEN to fail is not a check — prove it by making it fail on purpose.** After adding
  a validation, don't stop at "it says PASS." Point the same formula/predicate at known-bad input in a scratch
  location, confirm it emits the failure, then clear the scratch. The FC completeness check was proven by aiming
  row 24's formula at a period whose reading was genuinely blank (→ `✗ FAIL`), not by observing it pass on good
  data. A PASS on good data proves nothing about the failure path — which is the only path that matters.
  (2026-06-09; pairs with the fail-loud principle in `google-sheet-sop.md` Principle #2.)

- **Verify a deploy by pulling the remote copy BACK and diffing it — never by trusting the push message.**
  `clasp push` printing "Pushed 2 files" is the tool reporting its own intent, not the deployed state. Pull the
  remote into a scratch dir and `diff` against the clone. (Caveat found doing it: `clasp pull` may rename the
  extension — `Code.gs` came back as `Code.js` — so glob `Code.*` rather than assuming the filename.)
  Generalises to any deploy/upload where a read-back is cheap. (2026-07-26.)

- **A duplicated machine/environment gate is how a migration silently misses a file.** Ten runners were moved onto
  ⛔ a shared gate script that does not ship, on 2026-05-28; one runner kept its own hard-coded
  `case ComputerName in *<that one machine's name>*)` and was skipped. When that machine powered off it stopped feeding the tenant
  statement — and because the skip branch `exit 0`s (a SUCCESS code), no circuit breaker tripped and nothing
  alerted. **Rule: a gate/guard used by more than one runner lives in ONE sourced helper; a private copy is debt,
  not independence.** When you find one inline copy, grep for the others in the same pass. (2026-06-09; same bug
  class as `[ARCHIVIST-AUDIT-DEAD]`.)
