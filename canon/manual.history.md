# History log for manual.md

Text cut or moved out of `canon/manual.md`, copied verbatim first. Append-only. Each entry names its
source lines in the manual as it stood on 2026-11-14 (commit 0037ccb) and why it moved.

Note: entries naming the maintainer's own desks were moved to his private records, 2026-11-14.

## 2026-11-14 - G4-4 - source manual.md L30-33 - reason: Batch 4 item 3 (struck chains to history): the struck count and its 2026-10-30 correction

~~~~
> **★ AUTHORED 2026-07-24 (N5):** the middle "how it all works together" layer is now filled — a ranked
> INDEX of all ~~50~~ *(2026-10-30: the index below lists 51; `elements/` holds 49 files)* live parts + a TYPED INTEROP SEAM entry per non-trivial element (42 entries; 8 dormant
> parts carry an index line only), derived from each element's own INTEROP SEAMS. The map (tip) is a
> regenerated slice of this manual + the element STORES tables (N6).
~~~~

## 2026-11-14 - G4-9 - source manual.md L48-50 - reason: Batch 4 item 3 (struck chains to history)

~~~~
nudge (~~`nudge_flow_drift.sh`~~ *(2026-10-30: does not exist, `elements/hook-plane.md` B1)*, Feature 1.4)
~~~~

## 2026-11-14 - G4-20 · G4-21 - source manual.md L99-100 - reason: Batch 6 item 1: TARGET dropped (intent goes to the debt ledger, R1)

~~~~
- **TARGET** — aspirational: the element, or the enforcement it should have, **does not exist yet**. Named
  so the gap is visible, not hidden.
~~~~

## 2026-11-14 - G4-24 - source manual.md L128 - reason: settled by the coordinator 2026-11-14: Seam chapter whole to the manual's history file (this line points into it)

~~~~
  ⚠ **That sentence — "the running session is the interpreter" — is developed further, and its tension with `skill-building-sop.md` (THE FRAME, the "You are buying FRICTION, not certainty" line; formerly cited as :199) (LAW 1) named, in THE CODE/LLM SEAM below.**
~~~~

## 2026-11-14 - G4-34 - source manual.md L181-416 - reason: settled by the coordinator 2026-11-14 ("Seam chapter whole to the manual's history file, two untraceable figures flagged"). FLAGS carried with it: (1) the figures "37 of 57 failures (65%)" (frozen L277) and "14 of 57 (25%)" (frozen L281) trace to neither evidence file; (2) dead pointers inside: skill-building-sop "THE FRAME ... LAW 1" (frozen L193-194, L246) resolves only in the archived skills SOP, and `skill-system/brief.md:2608` (frozen L252) matches no file anywhere

~~~~
## THE CODE/LLM SEAM — how this system is actually made

> ⚠ **PROVISIONAL. NOT PRESCRIPTIVE. THIS IS BEST-CURRENT-THINKING, NOT DOCTRINE.**
> Written 2026-08-09 from one long session plus a six-reader sweep of two projects. It is filed here so
> the thinking survives the window that produced it — **not because it has been validated.** Everything
> below describes what we have observed so far, offered for testing. **Where it disagrees with a LAW in
> `skill-building-sop.md`, the LAW remains the operative rule until the operator says otherwise.**
> ⛔ **Do not cite this chapter as authority. Do not gate anything on it.** It exists to be argued with.
> **This is a new area and we are early in it.**
>
> **What a reader would otherwise misread:** you will assume the code in this system is the system. It
> isn't — and the manual already says so, one chapter up: *"the running session is the interpreter."*
> This chapter develops that sentence. ⚠ **It also sits in tension with `skill-building-sop.md` (THE FRAME, the "You are buying FRICTION, not certainty" line; formerly cited as :199)
> (LAW 1), which says code owns the perimeter and the model works inside it. Both statements are
> currently live. That tension is real, it is named here on purpose, and resolving it is the operator's call.**
>
> **Evidence:** `state/projects/project-system/records/2026-08-09-code-llm-spiral-candidates.md` ·
> `…/2026-08-09-code-spiral-audit-ledger.md`
> ⛔ `state/projects/project-system/records/2026-08-09-code-llm-spiral-candidates.md` and the audit ledger
> beside it live in the author's own notes, not in this repository — the working evidence behind the chapter,
> kept where the author's writing is kept and never committed here (migration note, 2026-08-15). The chapter
> stands on its own; you cannot open its footnotes.

### ▲ 10,000 ft — a shift being staffed, rather than a machine being built

The session behaves like an employee working a long shift. **Extremely capable** — fast, good judgment,
handles the unfamiliar. **Also forgetful by the hour, and eager to please whoever is standing in front of
them.**

On this reading, code is not the shop. **Code is what you put in the shop to help that employee**, and
there seem to be only four such things:

**Signs on the wall** — prose in a file. Only work if someone looks up.
**A supervisor who taps their shoulder** — the per-turn injector. Happens *to* them rather than waiting.
**A locked door** — the hook. They cannot walk through it whether they remember it or not.
**A timecard** — the artifact. Evidence they were there, after the fact.

#### The spiral, in this frame

**The pattern looks like trying to automate a shop that is actually staffed.**

The employee misses something. A machine gets installed to catch it. **But the machine does not run itself
— the employee has to switch it on.** They forget. So a machine gets installed to check the machines.

Meanwhile, measured across three projects on 2026-08-09: **fifteen machines in the back room nobody
switches on** · **thirteen with a green light wired to nothing** · **nine signs in the storeroom.**
Including one on a shelf a session actually opened — it read the first eighty lines and the sign starts
at eighty-two.

#### Why it has felt correct each time

**When the employee fails, you see it. When a machine fails, it hums and the light stays green.**

**13 of 36 code failures reported success while producing nothing.** `emit_status.py` printed `✓ PASSED`,
exit 0, and wrote no tile — **live since 2026-06-25.** `verify-hooks.sh` sat **red for 16 days.** A guard
printed its denial on the wrong channel: **blocked nothing, scored PASS.**

So each comparison between "unreliable model" and "reliable code" weighs **all** of the model's failures
against **a third** of code's. ⇒ **This looks like a measurement problem rather than a discipline
problem — the evidence in front of you genuinely supports building another machine.**

#### The inversion this suggests

**The session appears to be the host. Code appears to be the guest.**

`skill-building-sop.md` (THE FRAME, the "You are buying FRICTION, not certainty" line; formerly cited as :199) says *"code owns the mechanical perimeter, the LLM owns judgment inside it"* —
the model inside code's wall. **In this system it may be the reverse:** the session is what runs, and code
sits inside it waiting to be picked up.

That rule is sound engineering **from systems where code is the host.** In that world delivery is free — a
function call always arrives — so the only leg worth guarding is the return. **The rule came over; the
reason it worked may not have.** `skill-system/brief.md:2608` had already named this shape: *"when you
reuse a rule, re-derive its justification against the new subject."*

#### Where the metaphor breaks — stated rather than sold

**It makes the employee sound duller than they are.** They are excellent and forgetful, which is a
different problem needing different help.
**And it undersells code in three places where code plainly wins: the till, the lock, and the timecard** —
arithmetic, refusal, and proof. A person should not be doing any of those.

### ▲ 5,000 ft — the landmarks

#### 1. Three tiers, by who has to remember

**Fires on its own** — hooks and per-turn injectors.
**The model must call it** — every tool. Its reliability tracks the model's memory, which is what rots.
**The model must call it *and* type it exactly** — two ways to fail.

**Measured 2026-08-09: 49 hooks registered and firing** (29 PreToolUse · 10 UserPromptSubmit ·
5 PostToolUse · 4 Stop · 1 SessionStart) **against 15 tools with no caller.** So far, everything that
fires by itself works and everything that waits does not. ⇒ **A tool has behaved more like a suggestion
than a control.**

#### 2. Two handoff legs, and only one currently has a rule

**Outbound — code produces, the model must pick it up. 37 of 57 failures (65%).** The open question is
*what makes the model look?* Three answers appear available: **it's on screen every turn · it fires on the
act · the model remembers.** The third is hope, and it accounts for most of the 65%.

**Return — the model hands something back. 14 of 57 (25%).** Closed set, a member meaning *no outcome was
reached*, membership checked on the way in.

⚠ **Every enforceable clause of the current seam rule sits on the leg carrying 25% of failures.** The
outbound leg has no rule at all.

#### 3. Payload and delivery look like different axes

**The payload has been the same thing throughout: plain English, written for a model, landing when it is
needed.** There is no ladder here. A hook's deny message and a sign on the wall are the same substance.

**Only delivery has tiers.** A hook is not better prose — it is the same prose with better timing, and the
only one that can also refuse.

⛔ **The artifact does not sit on that ladder at all.** It is evidence after the fact, on its own axis.

#### 4. Liberal at the door, strict in the record

The pattern that has held: **accept anything that clearly means one of the legal values; store only a
legal value.**

**Measured 2026-08-09:** a verdict interface built that same night rejected **five of six plausible
phrasings** — `can proceed`, `can-proceed`, `CanProceed`, `proceed`, `ok`. Only the exact underscored
string passed. **This was a repeat**: `fork.py` did it first, and the recorded reaction was *"that's dumb
as fuck."*

**Why strictness may be backwards here:** strict code rejects what it does not recognise, and what it does
not recognise tends to be **a degraded session** — the moment the step most needed to land. **It has been
solid when nothing was wrong and unhelpful when something was.**

#### 5. The trade looks like error *shape*, not error *rate*

The operator, 2026-08-09: ***"if the LLM gets off course you can put it back; if the code breaks we're fucked."***

A model's error has been **visible, bounded, and non-breeding.** Code's error on the same question has
been **invisible, unbounded, and compounding** — each patch adding surface. ⇒ The trade appears to be a
higher rate of cheap visible errors against a lower rate of silent multiplying ones.

#### 6. What each side has been good at

**Code:** arithmetic · refusing an irreversible act · membership in a closed set · verifying an artifact
or hash · timing.
**The model:** meaning · anything containing a soft word · normalizing messy input · judging whether a
stranger would be confused — **which code has not been able to do at all.**

#### 7. Patterns that have tended to go wrong

A tool with no named caller · code deciding what a soft word means (*meaningful · stale · right ·
proper*) · **code that checks whether other code ran** · asking the model to self-report compliance · a
strict door stacked on a remembered call · trusting a search that returned nothing without a positive
control.

⭐ **One signal that has marked the shift from hybrid toward application: writing code whose job is to make
sure other code ran.** One layer has stayed manageable. Two layers has meant babysitting the machinery.

### ▲ Ground — dated specifics, both directions

#### What has worked, repeatedly

**A blind second instance — 8+ recorded uses across two projects, never previously named as a pattern.**
Eight sealed agents into the elements: **8/8 arrived, zero fabrications.** **55 sealed agents** settling a
map bake-off by measurement rather than debate. **Eight blind auditors over 795 files** — of 84 deletion
candidates, 67 were one concluded lab experiment, so real dead wood was **2.3%, not 11%** (*"the wrong verb
destroys working machinery"*). An adversarial audit **2-for-4 on day one**, finding a fire-test silently
dead. A skeptic pass killing a claim of **476 broken edges** — none real, a path bug. LAW 3, which two
teams stripped everything else down to and kept.

⭐ **Why it seems to work:** the instrument is **structurally incapable of the failure it is testing for** —
a blind reader cannot fake understanding because it has no context to fake with. Same principle as the
tool-less `ingest-reader`: **the wall is structural, not cognitive.**
⭐ **What made the asking work:** ⛔ **no checklist** (a checklist finds only what its author already
imagined) · **asking it to DO the job rather than evaluate the artifact** · **treating the assumptions it
must state as the measurement.**
**Cost:** haiku, two files, one job — **53,243 tokens / 68s**, beating a 110,226-token sonnet baseline.
⚠ **In the one case measured, a second confirming pass cost 110,354 tokens / ~4.3 min and bought nothing.**

**Derive it rather than hand-keep it.** `buried_command_hint.sh` reads frontmatter — *"stopped flagging
`/autoplan` the instant the flag left, with zero edits."* The capability census regenerates every run and
refuses hand edits: *"a hand-kept index rots and then LIES, which is worse than having none."* A producer
roster read from live `crontab` after a curated dict *"enumerated it as NOTHING, which is WHY an 87%
failure rate was invisible."*

**Grepping the live caller rather than reasoning from lineage** — recorded twice; *"both times the one
reasoning from LINEAGE was wrong."*

**An artifact only the real work could produce.** `pad_archive`'s receipt — three projects, never shown to
lose data. `skill-builder` (closed for renovation 2026-10-31) independently replacing self-declared phase completion with a required
artifact, **explicitly borrowing `save_step_ledger.py`.**

**And three smaller ones:** stating the denominator · **admitting the gap out loud — a gap-admission note
measurably outperformed silence in blind probe testing** · stating the fraction rather than the adjective ·
testing on a scratch copy, *"nothing ships in order to test it, and a failure costs nothing."*

#### What has failed before — the record so far

⚠ **These are dated instances, not prohibitions.** They are recorded so a future session can weigh them,
not so it is forbidden from trying something similar with better reasons.

`emit_status.py` — green light, no tile, **since 2026-06-25** · `verify-hooks.sh` — **red 16 days**,
unread · a guard denying on the wrong channel, **blocking nothing, scoring PASS** · `except: continue`
swallowing **1,300 rows** and reporting `0 examined` · `age_s None` becoming 0 so a silent producer could
never escalate · a DECISION gate comparing sha256 to job names, **vacuous by construction**.

`_derive_reader` inferring *"did real work happen"* from a file timestamp — **five bypasses in six
minutes**, two of them things a careful session does by accident · a second `start` call wiping stamps and
pushing the clock forward · **a strict door rejecting five of six phrasings, twice** · a guard matching a
literal path string that **a shell variable walked straight past** (*"cannot be completed by adding an
eighth regex"*) · a skip-filter matching macOS temp roots · a 40-char truncation turning *"30 active
DANGER"* into *"30 ac"* — **a redaction, not a summary.**

`inject_sop_before_build` keyed on the user's words, **firing at session start hours before the edit** · a
rule persisted in **four files and reaching zero of them** · **reading lines 1–80 of a file whose rule
begins at 82** · a clone-only grep returning **0 hits against 21 real references** · a fabricated **"141
sealed agents"** written into an always-loaded banner · a lane reading an **11-minute-old scratchpad note**
as a human ruling.

### What is NOT settled — read this before leaning on any of the above

**The whether/what boundary.** `pad_archive` checks whether a hash matches. Is that code deciding
*whether*, or code deciding *what*? **It is the one piece never shown to lose data, so any rule that
cannot account for it is wrong.** Unresolved.

**Is the no-outcome member mandatory or advisory?** The operator's own question,
`state/projects/ingest-skill/design/skill-maker-note-the-seam-slot.md:82`. **Unanswered.**
⛔ `state/projects/ingest-skill/design/skill-maker-note-the-seam-slot.md` lives in the author's own notes, not
in this repository, and is never committed here (migration note, 2026-08-15). The question above is quoted in
full; the note itself is not openable from here.

**Is a reminder enough, or is a hook needed?** The per-turn line shipped 2026-08-09 is **live and
untested.** What has been observed is that *blocks* worked at boundaries — three fired that night and each
changed the build. **Reminders for mid-work steps remain an experiment in progress, not a finding.**

**And the honest caution about this whole chapter:** the unifying lens fits **57 of 57** instances, which
is exactly the shape of a theory built on its own evidence. **The useful test is what it forbids, not what
it explains.** It cleanly forbids the 111-line scorecard built that night. Whether it forbids anything else
useful is unknown.
~~~~

## 2026-11-14 - G4-37 · G4-38 · G4-50 - source manual.md L422-446 - reason: settlement 7 + G4-37 best reading: the donor-list banner, its policy and counts (the bullets naming the maintainer's own desks, and the two-machine bullet, are NOT here; see the note at the top)

~~~~
> **⛔ TEN OF THE 51 DID NOT MIGRATE — read this before following a pointer** (migration note, 2026-08-15).
> This index, and the element entries below it, are the donor's list of 51 and are kept whole on purpose: a
> list that quietly drops what was left behind teaches you the system is smaller than it is. **41 of the 51
> ship here** *(counted mechanically 2026-08-15 against `elements/` — the earlier figure of 42 was a
> file-count taken before a second authored-here element existed; see the ADDENDUM below)*. **These ten do
> not, and their `elements/<slug>.md` files are absent by decision, not by accident:**
>
> - `elements/overmyshoulder.md` — ⛔ excluded from the migration: **browser-bound.** It reads a live Chrome
>   tab, and the whole Chrome path was ruled out of this system (see the two corrections further down).
>
> Every other numbered line below resolves. If a pointer in this index or a `## <slug>` entry further down
> names one of the ten, that is this banner's subject — the entry describes a part of the donor system that
> stayed there.
~~~~

## 2026-11-14 - G4-37 · G4-39 - source manual.md L448-463 - reason: Batch 4 item 3 (struck chains to history) + G4-37 best reading: the 'frozen at 51' policy and the 2026-08-15 / 2026-09-01 / 2026-10-30 element-count chain

~~~~
> ⭐ **ADDENDUM — TWO ELEMENTS WERE AUTHORED HERE AND TAKE NO NUMBER.** The numbered list above is the
> **donor's** list of 51 and is frozen at 51 on purpose; a 52nd line would quietly turn a preserved
> artifact into a living one, and then nobody could tell which entries were inherited and which were
> written here. So these two sit outside the numbering rather than extending it. **Both files exist on
> disk and both ship** *(~~43 files in `elements/` = 41 donor + these 2, counted mechanically
> 2026-08-15~~ — see the 2026-09-01 correction directly below: 44 files, decomposition unresolved)*:
>
> ⚠ **CORRECTED 2026-09-01 — the "43 = 41 donor + these 2" figure just above no longer adds up.**
> Re-derived this session: `ls -1 system/organism/elements/` → **44** files (all 44 `.md`, 0 non-`.md`,
> counted by directory listing). The `41 donor + 2 authored here` decomposition accounts for only 43 of
> those 44. The 44th is `elements/where-things-live.md` — confirmed present on disk this session, and
> cited by this very manual (line 143 and its own `## where-things-live` entry further down) — but it
> appears in neither the ranked-51 donor list above nor this two-item list. Whether `where-things-live`
> is a third authored-here element this list never named, or something else, is **not resolved here** —
> left as a finding, not patched with a guessed third bullet. The one number this note stands behind:
> ~~**44 files in `elements/`, mechanically counted 2026-09-01.**~~ *(2026-10-30: re-counted by `ls -1 system/organism/elements/ | wc -l` → **49** files, all `.md`; the 2026-09-01 figure is stale, the decomposition question above is still unresolved.)*
~~~~

## 2026-11-14 - G4-41 - source manual.md L484 - reason: Batch 4 item 3; stale pointer 'THE SCHEDULER' (renamed CRON AND ALARMS 2026-10-29)

~~~~
12. **pulse-cron** *[GLOBAL]* — LIVE·gap → `elements/cron.md`  · ↓ `#pulse-cron`  ⚠ CORRECTED 2026-10-27: on a Mac the scheduler is now launchd → `job-run.sh`, see THE SCHEDULER section above; `pulse.sh` + cron remain for Linux/Windows
~~~~

## 2026-11-14 - G4-49 - source manual.md L511 - reason: Batch 4 item 3; registration is the register row (canon/hook-sop.md); the cache path was pinned at 0.3.13 · names of the maintainer's own desks and dashboard taken out 2026-11-14 (see the note at the top)

~~~~
39. **compute-mechanically-gate** *[SHARED: finance desks]* — ~~DORMANT → `elements/compute-mechanically-gate.md`  *(index only — dormant)*~~ ⚠ CORRECTED 2026-08-25: NOT dormant — `inject_compute_mechanically.sh` is registered on UserPromptSubmit in both `system/hooks/registrations.json` and the live `~/.claude/settings.json` (confirmed this session by grep on both files), and fires on EVERY prompt (confirmed this session: piping a synthetic `{"prompt":"can we afford $500?","cwd":"/tmp"}` payload to the script on stdin printed the live "[NUMBERS CHECK (hard math token)...]" injection text, exit 0). It only prints nothing when no arm condition is met — that is normal honor-hook behavior, not dormancy. ⚠ PARTIALLY SUPERSEDED 2026-08-27 (hook-plane migration): the "live `~/.claude/settings.json`" half of that confirmation no longer holds — verified this session by reading `~/.claude/settings.json` with `json.load`, it now carries 7 hook entries (down from 49) and `inject_compute_mechanically.sh` is not one of them. The script is still live and still fires, but from `~/.claude/plugins/cache/lifehack-brain/lifehack-brain/0.3.13/hooks/hooks.json` (confirmed present there this session), not from `~/.claude/settings.json`. → `elements/compute-mechanically-gate.md` ⛔ `system/hooks/registrations.json` retired (hook registration lives in register.jsonl → hooks/hooks.json); kept as history.
~~~~

## 2026-11-14 - G4-51 - source manual.md L518 - reason: Batch 4 item 3 (the keep-it-visible policy is superseded by the move-to-history ruling)

~~~~
46. **world-model-ingestion** *[GLOBAL]* — ~~DORMANT~~ **LIVE** → `elements/world-model-ingestion.md`  ~~*(index only — dormant)*~~ *(index line only — LIVE)*  ⚠ **CORRECTED 2026-08-15.** The element file carries `maturity_label: LIVE` plus its own note — *"no longer inactive as of 2026-08-06 (the skill is built and running on a live corpus)"* — so this manual line's DORMANT was stale. Both read this session; the element is authoritative on its own maturity. The struck text stays visible because this manual asserted it.
~~~~

## 2026-11-14 - G4-52 · G4-53 - source manual.md L522-523 - reason: Batch 4 item 3; stale pointer 'THE SCHEDULER'

~~~~
50. **hospital** *[GLOBAL]* — PARTIAL·gap [provisional] → `elements/alarms.md`  · ↓ `#hospital`  ⚠ CORRECTED 2026-10-27: detector jobs retired; producers are now `job-run.sh` job state, see THE SCHEDULER section above
~~~~

## 2026-11-14 - G4-52 · G4-53 - source manual.md L522-523 - reason: Batch 5 third pass: Efficiency removed from the live manual completely, no pointer (canon: the words are kept here)

~~~~
51. **efficiency** *[GLOBAL]* — PARTIAL·gap [provisional — not fire-tested] → `elements/efficiency.md`  · ↓ `#efficiency`
~~~~

## 2026-11-14 - G4-70 - source manual.md L684-711 - reason: Batch 4 item 3: the struck recipe steps and the note that kept them 'for the record only'

~~~~
### How to add a job (Mac) — step by step

> **This recipe now lives in one place: `canon/cron-jobs-sop.md`, section 11 "Add a job (the recipe)"** (2026-10-30). Follow that, not the steps below. The steps below were marked OUT OF DATE on 2026-10-27 (self-monitoring 5.1–5.3: the check now lives in the ROW, not in `job-run.sh`; every row needs the five contract fields; the door refuses a non-conforming row; a model is reached through `run_model`, not `ingest-run.lib.sh`) and are kept struck through for the record only.

1. ~~**Write the command.** A stand-alone shell command or runner script (`system/tools/<job>-run.sh`). It must exit 0 only
   on real success, 75 if it is simply not configured, 2 for a transient failure, anything else for a failure. Reach a
   model or Google only through the shared libraries (`ingest-run.lib.sh`), never a bare `claude -p`.~~
2. ~~**Add ONE row** to the ```jobs block of `system/jobs.md`: `my-job | yes | 10800 | bash "$LIFEHACK_CODE_ROOT/system/tools/my-job-run.sh"`.
   Name: lowercase letters, digits and hyphens only. Interval: seconds, and on a Mac a whole number of hours that divides
   86400 (3600, 7200, 10800, 14400, 21600, 28800, 43200, 86400) — anything else makes the installer refuse, touching nothing.
   Use `no`, `parked` or `waiting-on-<thing>` for a declared-off row.~~
3. ~~**Declare what it needs, in `job-run.sh`.** In the `case "$JOB"` block add `my-job) NEEDS="gws"; WATCHDOG=1200 ;;` —
   `NEEDS` is any of `claude` and `gws` (each makes the wrapper run that credential pre-flight and stand down with 75 if
   it is missing), and `WATCHDOG` is the most seconds the command may run (default 3600) before it is killed.~~
4. ~~**Write the output check, in `job-run.sh`: `check_my_job` (hyphens become underscores).** It returns 0 only if the job's
   promised output is present AND newer than `$START_MARK`, and echoes the reason when it fails. Check the output that
   proves the work, not the exit code: an empty result is not a success. **Without this function, or without `NEEDS`
   where the job needs credentials, the job can never succeed** — the wrapper fails it with "no output check declared".~~
5. ~~**Run the rig:** `bash system/tools/tests/job-sim.sh` (and add a scenario if you changed the alarm rules).~~
6. ~~**Run it once by hand through the wrapper** (no `--if-overdue`): `bash system/tools/job-run.sh my-job`. Expect exit 0,
   `~/.config/lifehack/state/jobs/my-job/last-success` present, and the log ending `output check passed`. A failure leaves
   a file in `errors/`.~~
7. ~~**Install the schedule:** `bash system/tools/install-schedulers.sh --install` (without `--install` it only prints the
   plan). It rewrites every `ai.lifehack.*` agent from the whole block, so it is safe to re-run. Confirm with
   `launchctl list | grep ai.lifehack.my-job`.~~
8. ~~**Confirm the chain:** open a new session and read the first line (`jobs: <n> OK`; a brand-new job reads "never ran"
   until its first run), and check `cat ~/.config/lifehack/code-root` names the code you mean. To retire a job, set its
   row to `no` and re-run the installer; leave its state folder.~~
~~~~

## 2026-11-14 - G4-71 - source manual.md L717-721 - reason: factual fix: with the Pulse lines corrected (G4-96, G4-97, G4-112, G4-131) the banner points at nothing; Batch 4 item 3

~~~~
> ⚠ **READ THIS FIRST (2026-10-29).** Any entry below that says a part is run by "Pulse" ("Pulse every 900s", "TRIGGERS-BY
> pulse-cron", "Pulse-dispatched") describes the OLD Mac scheduler. On a Mac today a job runs ONLY if its row in
> `system/jobs.md` is switched to `yes`, through Cron (see CRON AND ALARMS above). Check that file for what is
> actually on; do not infer it from an entry below.
~~~~

## 2026-11-14 - G4-78 · G4-79 · G4-80 - source manual.md L752-755 - reason: Batch 4 item 3: struck layer list and the 2026-08-15 correction chain; the live lines keep the present-tense facts, and (settlement 1) keep Level 1 described as fail-open by design

~~~~
Block every outbound network call to a host not on the allowlist — so a hijacked session cannot exfiltrate data. ~~Three independent hook layers (L1 credential-exfil, L2 domain name-check, L3 raw-tool block) plus an OS-layer LuLu backstop~~; ·gap because dynamic-URL and env-var-credential paths are fail-open.
⚠ **CORRECTED 2026-08-15 — the in-process domain seal was ARMED. It still ships OFF.** There is now a FOURTH mechanism beside the three hook layers: the in-process seal inside `system/tools/safe_fetch.py`. The operator ruled it (`authority: user` — *"APPROVED — ARM IT"*). A persistent switch file `system/safe-fetch-allowlist.md` (same ALLOWLIST-START/END markers as `system/egress-allowlist.md`), a `l2_state()` resolving every read to **three named outcomes and no quiet fourth** — **OFF** (allowed, and it says so on stderr once per process) · **ON** (off-list host refused *before the socket opens*) · **AMBIGUOUS** (**refused**) — with the `SAFE_FETCH_ALLOWLIST` env var as the **per-run** seal outranking the file, which is the **persistent** switch a human sets by hand. `--l2-status` reports the switch position without fetching. `system/tools/test_egress_level2.py` holds 12 tests, passing inside `system/tools/run-all-tests.sh`.
⛔ **DO NOT READ THIS AS "THE EGRESS WALL IS NOW ENFORCED."** It ships `off` with an empty domain block and no caller arms it, so **by default it seals nothing.** The honest claim — do not exceed it — is **armed and switchable, ships OFF, refuses loudly when half-configured.** Never "enforced," never "protected." What changed is that the level you are actually at is now knowable and stated out loud; not that a wall went up.
⚠ **Two things did NOT change.** (1) The Bash-command domain hook still **fails OPEN, deliberately** — it sits in front of *every* Bash command, where a false positive stops ordinary work and somebody unregisters the guard; the in-process seal sits in front of web reads only and is off unless deliberately armed. (2) The OS firewall (LuLu) remains the only HARD wall of the three, and is still not carried here.
~~~~

## 2026-11-14 - G4-84 - source manual.md L767-768 - reason: Batch 4 item 3: CLEANUP-PASS note; the passage is repointed to rebuild/conformance-lab/ · a private repo path generalised 2026-11-14

~~~~
> ⚠ CLEANUP-PASS 2026-10-31: conformance-lab/ moved to ~/lifehack-v2/rebuild/conformance-lab/ (V2 copy) and a private config repo's archive (private copy); this passage is stale — fix in the cleanup pass. Ledger: state/projects/skill-system/records/2026-10-31-cleanup-ledger.md
~~~~

## 2026-11-14 - G4-88 - source manual.md L784-785 - reason: Batch 4 item 3: struck auto_register / nudge_flow_drift lines

~~~~
  ~~FEEDS       skill-system       · auto_register_skill writes ~/.claude/commands/<name>.md stub after a desk SKILL.md write~~ *(2026-10-30: `auto_register_skill.sh` does not exist)*
  ~~FEEDS       organism-map       · nudge_flow_drift reads system/organism/elements/*/generated_from and emits advisory when an edited file is cited there~~ *(2026-10-30: `nudge_flow_drift.sh` does not exist; `elements/hook-plane.md` B1)*
~~~~

## 2026-11-14 - G4-88 - source manual.md L798 - reason: Batch 4 item 3 + Batch 1 item 2: mirror_plans.sh correction ('line 964' lands on an unrelated line)

~~~~
~~~~

## 2026-11-14 - G4-88 · G4-89 - source manual.md L800-802 - reason: Batch 4 item 3 + Batch 1 item 2: the 2026-08-25 / 2026-08-27 settings.json correction chain

~~~~
~~~~

## 2026-11-14 - G4-88 · G4-89 - source manual.md L800-802 - reason: factual fix: sentinel's health checkers retired 2026-10-29

~~~~
  FEEDS       sentinel           · hook scripts + settings.json registration are artifacts sentinel's health checkers read for the Security tile
~~~~

## 2026-11-14 - G4-88 - source manual.md L804 - reason: factual fix: translator_gate.sh is in neither registration file

~~~~
  FEEDS       claude-md-pyramid  [deprecated-in-place] · translator_gate.sh was the voice-compliance grading gate (Stop); the Haiku grader was RETIRED per [TRANSLATOR-GATE-RIP] 2026-07-14; hook remains registered but does not enforce
~~~~

## 2026-11-14 - G4-96 - source manual.md L956-993 - reason: Batch 4 item 3 (the entry called itself history); Batch 1 item 2; stale pointers · names of the maintainer's own desks and dashboard taken out 2026-11-14 (see the note at the top)

~~~~
## pulse-cron (HISTORY) · crontab */5   [Linux/Windows only]   → elements/cron.md (history section)
⚠ **CORRECTED 2026-10-27 (self-monitoring plan): on macOS this is no longer how jobs run.** Each enabled row now has its own launchd agent that runs `job-run.sh` (see THE SCHEDULER, THE JOB WRAPPER AND THE ALARM above); the Pulse/system-health/deadman machinery described below, and the per-tick heartbeat mirrors, apply only to Linux and Windows, and the watcher jobs named in the INTEROP list (system-health, sentinel-health, backlog-health, deadman) were removed. The text below is kept as history.
One crontab line ticks pulse.sh every 5 minutes; it reads the jobs block in jobs.md and fires any job whose interval has elapsed, with machine-local circuit-breaker safety, single-writer machine-gating, and a Drive-mirrored heartbeat feed. The Bash-write bypass gap (guard_write_paths.sh matches Write/Edit only) is accepted.

INTEROP:
  TRIGGERS     system-health        · dispatches system-health-run.sh → reads _pulse-*.json + jobs.md to detect missed runs
  TRIGGERS     archivist            · fires archivist-audit/deepmine-run.sh on their respective intervals
  TRIGGERS     email-service        · fires email-summary-write-run.sh + email-summary-freshness-run.sh
  TRIGGERS     grand-central        · fires tasks-store-sync-run.sh + calendar-store-sync-run.sh
  TRIGGERS     sentinel             · fires sentinel-health-run.sh → reads sentinel-events.jsonl → tile
  TRIGGERS     git-sync             · fires git-autopush + git-autopull
  READS        jobs.md      · reads the ```jobs block every tick for the job schedule manifest
  WRITES->     durable-status-plane · writes state/status/_pulse-{machine}.json + _pulse.json heartbeat mirrors after every cycle
  WRITES->     durable-status-plane · runner jobs write state/status/{desk}.json tiles via emit_status.py
  WRITES->     learnings-store      · Pulse trims system/learnings.md sections older than 90d; /save appends
  WRITES->     observability        · observability-trim job deletes system/observability/*.jsonl older than 30d
  WRITES->     maintenance-log      · hook-doc-lint job is the sole writer of system/logs/maintenance-due.md (honor-system pickup by sessions)
  FEEDS        planning             · planning-vault-weekly-run.sh writes desks/cal/state/weekly-vault/ → planning-weekly-analyze-run.sh consumes (⚠ desks/cal/ is DELIBERATE — code/jobs/tiles renamed to planning, the records directory was NOT)
  FEEDS        email-service        · email-summary-write-run.sh → state/email-summary/threads-v2/ (faithful thread store)
  FEEDS        grand-central        · item-store jobs → state/item-store/tasks/ + state/item-store/calendar/ (sole writers)
  COMPLEMENTS  notify-plane         · pulse.sh calls notify-send.sh directly for circuit-breaker trips + no-lead nag; all *-run.sh runners channel alerts through notify-send.sh
  COMPLEMENTS  health-deadman-check · launchd watcher (BY DESIGN outside Pulse) watches system-health tile mtime; catches a dead Pulse+health chain that no Pulse job could detect
  GUARDED-BY   ~~require_primary~~ · **⚠ CORRECTED 2026-08-24: not a real guard.** `require_primary()` has zero definitions anywhere in this repo and `primary-gate.sh` does not exist on disk (grep/find, verified this session). This system has one machine (`canon/data-layout.md:215`); Drive-writing jobs run with no machine gate. Correctly stated in `elements/backlog-authority.md:203-205` and `elements/archivist.md:71-72`; corrected in full in `elements/cron.md`'s GATES section.
  GUARDED-BY   ingest_acquire_lock  · prevents stacked runs per job; single-instance enforcement in every claude-invoking runner
  GUARDED-BY   circuit breaker (pulse.sh) · auto-disables a job after 3 consecutive non-transient failures; rc=2 never trips it
  GUARDED-BY   ingest_check_paused  · Sentinel danger verdict → human-gated source pause; no auto-resume
  GUARDED-BY   guard_write_paths.sh [hook] · blocks Write/Edit tool calls to status stores from a session (NOT from the pulse subprocess; Bash-write bypass gap accepted 2026-07-14)
  GUARDED-BY   ingest_gate_enforce.sh [hook] · fires inside claude -p sessions launched by runners; blocks raw external reads + gws body reads
~~~~

## 2026-11-14 - G4-100 · G4-101 - source manual.md L1010-1011 - reason: Batch 4 item 3: struck EGRESS-WALL-FAILOPEN clause and its 2026-08-15 correction

~~~~
Every byte of external content — web, email, calendar, tasks, documents, search results — passes through a two-layer filter (L0 deterministic scrub + heuristic injection scan) before the model reads it, and a hook plane blocks every raw-read bypass. ~~Egress allowlist is structurally present but functionally unarmed [EGRESS-WALL-FAILOPEN].~~
⚠ **CORRECTED 2026-08-15.** "Functionally unarmed" is no longer true of the in-process seal in `system/tools/safe_fetch.py` — it was built out and made switchable (the operator, `authority: user`). The honest claim, and do not exceed it: **armed and switchable, ships OFF, refuses loudly when half-configured** — never "enforced," never "protected," because it ships `off` with an empty domain block and no caller arms it. ⚠ *"Level 2 is armed"* means **that in-process seal**, NOT the Bash-command hook this map calls L2 — the two ladders are numbered oppositely; see the collision note under `## egress-allowlist-wall` above. The `[EGRESS-WALL-FAILOPEN]` gap itself is UNCHANGED and still stands: the Bash-command domain hook still fails OPEN, deliberately.
~~~~

## 2026-11-14 - G4-102 - source manual.md L1023-1024 - reason: Batch 4 item 3: struck Chrome fallback and its correction

~~~~
  COMPLEMENTS  websearch               · /websearch skill wraps safe_search_api.sh ~~(primary) + safe_search.sh (Chrome fallback)~~ for interactive sessions
                                        ⚠ **CORRECTED 2026-08-15.** safe_search_api.sh is not "primary" — it is the ONLY search path. There is no Chrome fallback: `safe_search.sh` and the whole dev-browser path were DELETED by ruling (the operator, authority: user — *"Research should never go into Chrome… that's an old leftover thing"*). The file is gone from the tree; verified absent this session. The struck text is left visible because it was true of the donor.
~~~~

## 2026-11-14 - G4-104 - source manual.md L1030 - reason: factual fix: sentinel-health retired 2026-10-29

~~~~
  FEEDS        pulse-cron             · sentinel-events.jsonl is the source for sentinel-health.py (a Pulse job); Pulse polls every ~1800s and rewrites the tile with stale_after_s=86400 — sentinel produces the event record; Pulse produces the tile refresh
~~~~

## 2026-11-14 - G4-84 - source manual.md L1080-1081 - reason: Batch 4 item 3: CLEANUP-PASS note; the passage is repointed · a private repo path generalised 2026-11-14

~~~~
> ⚠ CLEANUP-PASS 2026-10-31: conformance-lab/ moved to ~/lifehack-v2/rebuild/conformance-lab/ (V2 copy) and a private config repo's archive (private copy); this passage is stale — fix in the cleanup pass. Ledger: state/projects/skill-system/records/2026-10-31-cleanup-ledger.md
~~~~

## 2026-11-14 - G4-106 - source manual.md L1082 - reason: Batch 4 item 3: struck auto_register_skill line

~~~~
  ~~TRIGGERS     auto_register_skill.sh · a Write or Edit to desks/{desk}/skills/{name}/SKILL.md automatically triggers stub creation; /save may trigger this if it writes a SKILL.md~~ *(2026-10-30: no such hook exists, see the GUARDED-BY note below)*
~~~~

## 2026-11-14 - G4-106 - source manual.md L1089 - reason: Batch 4 item 3: struck auto_register_skill line

~~~~
  ~~GUARDED-BY   auto_register_skill.sh · PostToolUse Write|Edit — creates desk command stubs automatically; non-blocking (stderr only)~~ *(2026-10-30: `auto_register_skill.sh` does not exist and is not registered; `elements/hook-plane.md` B3)*
~~~~

## 2026-11-14 - G4-107 - source manual.md L1116 - reason: Batch 4 item 3: the 2026-08-27 Stop-registration correction

~~~~
  KEYS-OFF     hook-plane        · ~~Stop-event registration in settings.json is what arms this gate at all~~ ⚠ CORRECTED 2026-08-27 (hook-plane migration): the live Stop-event registration for `scratch_capture_gate.sh` is not in `~/.claude/settings.json` — verified this session, that file's 7 remaining hook entries carry no Stop-event hooks at all. The registration now lives in `~/.claude/plugins/cache/lifehack-brain/lifehack-brain/0.3.13/hooks/hooks.json` (confirmed present there this session). Deregistering it there — not in settings.json — is what would silently disable continuous capture now.
~~~~

## 2026-11-14 - G4-109 - source manual.md L1135-1150 - reason: factual fix: system-health retired 2026-10-29, health_invariants.py has no caller (DORMANT = built, not in use); Batch 4 item 3; Batch 1 item 2 · names of the maintainer's own desks and dashboard taken out 2026-11-14 (see the note at the top)

~~~~
## health-invariants · system-health.py + health_invariants.py   [LIVE·gap [provisional]]   → elements/health-invariants.md
Assert five structural invariants and sweep every Pulse job for missed runs — on any breach, push a phone alert and surface a BROKEN tile on the status dashboard; the out-of-band dead-man's-switch watches the sweeper itself from outside Pulse so silence is never mistaken for health. Gap: Invariant 4 fires BROKEN on legitimate machine-offline (no lead-aware suppression); FRESH_TILES is a residual hand-maintained shadow list.

INTEROP:
  TRIGGERS    pulse-cron         · Pulse dispatches system-health-run.sh every 300s — the sweeper IS a Pulse job, living inside the thing it watches (out-of-band launchd watcher is the escape hatch)
  READS       pulse-cron         · _pulse-*.json heartbeat files — the raw evidence the sweeper assesses for missed-run detection
  WRITES→     ~~(ground-truth log) · state/health.jsonl — append-only invariant record; survives tile lies; not consumed by any UI today~~ ⚠ CORRECTED 2026-09-01 (#61): this write no longer happens. Verified this session: `system/tools/health_invariants.py` calls only `emit_finding()`, no `health.jsonl` reference anywhere in the file. The append was deleted in T15.19 (`fe56626`) — same fact this manual already states correctly at line ~1222; this line was the stale half of that self-contradiction.
  READS       egress-allowlist-wall · guard_egress.sh presence is one of the four CRITICAL_HOOKS asserted by Invariant 1; tampering detected by Invariant 2
  READS       hook-plane         · all guard hook files in system/hooks/guard_*.sh — Invariant 1 checks presence; Invariant 2 checks git-committed (untampered) state
  READS       sentinel           · state/status/sentinel.json tile consumed by sentinel_fold() in the sweeper; Sentinel DANGER escalated to need_attention[]
  READS       security-ingest-gate · desk-registry.yaml reads_external field — Invariant 5 / drift-cop coverage check (when INGEST_COVERAGE_FLAG=on)
  COMPLEMENTS sentinel           · Sentinel detects INBOUND injection; health-invariants detects SUBSTRATE failure — parallel, non-redundant
  CHAINS      archivist          · sweeper spawns archivist-placements.py + archivist-lean.py as side-effects post-sweep (decoupled + graceful; failure never blocks sweep)
  READS       grand-central      · state/primary-machine — lead-machine detection in system-health-run.sh and _current_lead()
  SYNCS       (desk-health producers) · FRESH_TILES and assess_registry() must stay in sync with desk-registry.yaml when new desks are added
~~~~

## 2026-11-14 - G4-84 - source manual.md L1230-1231 - reason: Batch 4 item 3: CLEANUP-PASS note; the passage is repointed · a private repo path generalised 2026-11-14

~~~~
> ⚠ CLEANUP-PASS 2026-10-31: conformance-lab/ moved to ~/lifehack-v2/rebuild/conformance-lab/ (V2 copy) and a private config repo's archive (private copy); this passage is stale — fix in the cleanup pass. Ledger: state/projects/skill-system/records/2026-10-31-cleanup-ledger.md
~~~~

## 2026-11-14 - G4-123 - source manual.md L1238-1240 - reason: Batch 4 item 3: lines on documents retired 2026-10-31

~~~~
  READS       architecture-planning-sop [retired 2026-10-31] · /autoplan prose directives; /build Step 0 ALWAYS doc — scoping front-end that produces the vetted handoff prompt
  READS       ~~build-sop~~ [retired 2026-10-31]
  READS       ~~build-conductor-sop~~ [retired 2026-10-31]
~~~~

## 2026-11-14 - G4-123 - source manual.md L1245 - reason: Batch 4 item 3: retired build-sop + mirror_plans correction

~~~~
  WRITES→     durable memory (/save) · build-sop.md retired 2026-10-31; ⛔ CORRECTED 2026-08-25: plans do NOT mirror to Drive — mirror_plans.sh does not exist, see elements/hook-plane.md §E2
~~~~

## 2026-11-14 - G4-123 - source manual.md L1248 - reason: Batch 4 item 3: retired architecture-planning-sop

~~~~
  COMPLEMENTS advisory-council   · architecture-planning-sop.md [retired 2026-10-31] Stages 1/4/6 invokes /advisory-council for blind review; /build does not invoke it directly
~~~~

## 2026-11-14 - G4-123 - source manual.md L1262 - reason: Batch 4 item 3: struck mirror_plans.sh line

~~~~
  SYNCS       ~~mirror_plans.sh~~      · ⛔ CORRECTED 2026-08-25: neither this hook nor its pull-side counterpart exists in this repo — no plan-sync to keep in lockstep; see `elements/plan-integrity-cluster.md` HOOK 4
~~~~

## 2026-11-14 - G4-124 - source manual.md L1270-1271 - reason: Batch 4 item 3: struck safe_search.sh and its correction

~~~~
  FEEDS        safe-reader-plane    · safe_search_api.sh, ~~safe_search.sh,~~ safe_fetch.py are shared primitives; safe-reader-plane OWNS the security model; research-web-plane USES them as its only network path; a change to safe_input.py or sanitize.py propagates to both
                                     ⚠ **CORRECTED 2026-08-15.** `safe_search.sh` is struck because it no longer exists: it and the whole Chrome/dev-browser path were DELETED by ruling (the operator, authority: user — *"Research should never go into Chrome… that's an old leftover thing"*). Verified absent from the tree this session. The shared primitives are safe_search_api.sh and safe_fetch.py; the struck name is kept visible rather than silently removed.
~~~~

## 2026-11-14 - G4-123 - source manual.md L1323 - reason: Batch 4 item 3: retired architecture-planning-sop

~~~~
  TRIGGERS    architecture-planning-sop [retired 2026-10-31] · SOP calls /advisory-council at Stages 1, 4, and 6 using the same roster cartridge; SOP's own subagents stay sonnet, only the advisors run opus
~~~~

## 2026-11-14 - G4-129 - source manual.md L1336 - reason: Batch 4 item 3: simplify_anchor_inject / translator_gate correction chain

~~~~
  COMPLEMENTS all-response-outputs      · ⛔ simplify_anchor_inject.sh was DELETED 2026-08-05 (failed experiment — fired EVERY turn, not 1-in-10). The per-turn voice re-anchor NO LONGER EXISTS; ~~translator_gate.sh (Stop) still grades finished replies.~~ *(2026-10-30: `translator_gate.sh` is not in `system/hooks/` and is not registered; `system/sops/translator-rubric.md` says NOT PORTED.)* This line claimed a live control for 9 days after it was switched off — §19's founding specimen. Was: fires before EVERY turn across every desk, skill, and agent — the voice contract for the entire system
~~~~

## 2026-11-14 - G4-129 - source manual.md L1339 - reason: Batch 4 item 3: struck output-styles line

~~~~
  ~~SYNCS       output-styles/simplify.md · session-startup voice baseline; simplify_anchor_inject.sh is the per-turn re-anchor; both implement the same rubric criteria — out-of-sync means baseline and injection diverge mid-session~~ *(2026-10-30: `output-styles/simplify.md` is not in this repo (archived 2026-07-28) and `simplify_anchor_inject.sh` was deleted 2026-08-05; `system/sops/translator-rubric.md` is the only live copy)*
~~~~

## 2026-11-14 - G4-123 - source manual.md L1348 - reason: Batch 4 item 3: retired architecture-planning-sop

~~~~
  CHAINS       architecture-planning-sop [retired 2026-10-31] · the SOP uses /advisory-council in pre-mortem mode at Stage 4 rather than /red-team directly; /red-team is the available utility for an ad-hoc pre-mortem outside the SOP formal gate — INFERRED
~~~~

## 2026-11-14 - G4-133 · G4-134 - source manual.md L1450-1474 - reason: Batch 4 item 3 (the entry called itself history); stale pointer 'THE SCHEDULER' · names of the maintainer's own desks and dashboard taken out 2026-11-14 (see the note at the top)

~~~~
## hospital (HISTORY — retired as a subsystem name 2026-10-29) · emit_finding.py + findings_reader.py + fault_proposer.py   → elements/alarms.md (history section)
⚠ **CORRECTED 2026-10-27 (self-monitoring plan): Hospital was rebuilt, not deleted.** The detector jobs below are RETIRED; its producers are now `job-run.sh`'s per-job state under `~/.config/lifehack/state/jobs/`, and its reader is `health_line.py` (one line, first in every session). The incident ledger and fault grader are on hold. See THE SCHEDULER section above. The text below is kept as history.
Every problem the system detects about itself becomes ONE comparable record, so "what is wrong?" can be asked once — at ground, subsystem or whole-system altitude — and answered with a ranked, evidence-cited list instead of a pile of incompatible notes. It DETECTS and RANKS; it never REMEDIATES (council: auto-fix CUT 7/7). Four producers emit through it today; ~8 known failure producers still do not (GAP-1), and nothing guards the store against a hand-authored write (GAP-3).

INTEROP:
  READS        health-invariants   · one of its four converted producers; health_invariants.py emits per-invariant findings through emit_finding (T15.19, `fe56626`) — its old state/health.jsonl append was DELETED in that same commit
  COMPLEMENTS  health-invariants   · Health Authority answers "is the SUBSTRATE intact?" (runtime); Hospital answers "what has any DETECTOR found, and how bad is it?" — and health_invariants is now BOTH a substrate-checker AND a Hospital producer, which is exactly why the two must never be merged
  WRITES→      dashboard           · findings land at state/findings/<producer>.<machine>.jsonl on the Drive spine — machine token in the PATH, never only the payload (an internally-tagged shared file still forked 9 ways and stranded 1,169 rows)
  FEEDS        health-line         · health_line.py at SESSION START is the CONSUMER — chosen because it speaks whether or not anyone chooses to look; "a human sees the dashboard" is the consumer that already failed twice (a forked tile unnoticed; 57 findings unread for 7 days)
  TRIGGERS-BY  pulse-cron          · fault-proposer runs daily (86400s); findings_deadman enumerates producers from pulse-config AND live `crontab -l`, which is what finally makes the crontab-only health-deadman visible at all
  GUARDED-BY   ~~NOTHING, as of this write · no Hospital hook exists or is registered (GAP-3)~~ ⚠ CORRECTED 2026-08-24: guard_findings_write.sh IS registered (confirmed present in `~/.claude/settings.json` PreToolUse Bash|Write|Edit hooks, and fired a live `{"decision":"block"}` on a synthetic `echo >> state/findings/*.jsonl` this session) — GAP-3 is CLOSED, not open. The Efficiency section three lines below already names this same hook correctly; this clause was the stale one. emit_finding's contract is ALSO structural (no id= parameter, scanned_n required, zero-scan-OK refused) — the hook and the contract are two independent layers, not one. ⚠ UPDATE 2026-08-27 (hook-plane migration): `guard_findings_write.sh` is no longer in `~/.claude/settings.json` — verified this session, that file's 7 remaining entries do not include it. GAP-3 stays CLOSED, not because the 2026-08-24 finding-location was wrong, but because the hook moved: it is now registered in `~/.claude/plugins/cache/lifehack-brain/lifehack-brain/0.3.13/hooks/hooks.json` (confirmed present there this session). It was not re-fire-tested from that location in this pass.
~~~~

## 2026-11-14 - G4-133 · G4-134 - source manual.md L1450-1474 - reason: Batch 5 third pass: Efficiency removed from the live manual completely, no pointer (canon: the words are kept here)

~~~~
## efficiency · recommend.py + emit_recommendation.py + fault_proposer.py   [PARTIAL·gap [provisional — not fire-tested]]   → elements/efficiency.md
Efficiency exists so the system gets SHARPER with use instead of duller. Entropy is the default — junk accumulates, parts rot, seams fray. Efficiency is the counter-force: it reads what is wrong, reasons ACROSS findings rather than one at a time, and proposes how the organism should evolve. Where Hospital DETECTS and RANKS one problem at a time, Efficiency reasons across them at three altitudes — the broken part, the broken chain, the wrong architecture. **It SUGGESTS and never APPLIES** (⚖ RULED 2026-08-04 by the operator; auto-fix CUT 7/7 by council), and there is no applier anywhere in it. ⚠ **Only the GROUND altitude is built, and it has never run in production** — `recommend.py` has no caller and `<notes>/state/recommendations/` does not exist on disk (measured 2026-08-05), deliberately, pending one supervised live run. **There is no LLM in this subsystem today** — it is deterministic code end to end, so no code/LLM seam binds it as built.

INTEROP:
  READS        hospital            · consumes the findings union via findings_reader.py — Hospital's contract change is Efficiency's outage; the tightest coupling in the pair
  SHARES-STORE hospital            · ONE hook (guard_findings_write.sh, mode 444, ~~settings.json~~ ⚠ CORRECTED 2026-08-27, hook-plane migration: registered in `~/.claude/plugins/cache/lifehack-brain/lifehack-brain/0.3.13/hooks/hooks.json`, not `~/.claude/settings.json` — verified this session, the script is absent from settings.json's 7 remaining entries) guards BOTH state/findings/ and state/recommendations/ incl. dispositions/ — hardening it helps both, breaking it blinds both
  FEEDS        health-line         · the session-start RECOMMENDATIONS: line is the ONLY surface where Efficiency reaches a human — ranked DECISION > ORGANISM > SUBSYSTEM > INSTANCE, capped at 3, each with an 8-char fingerprint the disposition CLI accepts directly
  TRIGGERS-BY  pulse-cron          · ONLY fault-proposer is scheduled (daily, 86400s); the ground reasoner is NOT — that is GAP-1, not an oversight (CUT-E)
  COMPLEMENTS  backlog             · ⚖ RULED 2026-08-05 by the operator — the debt ledger is Efficiency's INPUT, not its exile; it may DEMOTE and ARCHIVE ledger items on POSITIVE EVIDENCE ONLY (§18.5a carve-out). NOT YET BUILT
  GUARDED-BY   guard_findings_write.sh · blocks any Bash/Write/Edit into the store that bypasses emit_recommendation.py; resolves shell variables before matching (the T15.32 bypass). Watched firing on the PRIMARY machine only — the second machine is dark since 2026-07-04
~~~~

## 2026-11-14 - G4-137 · G4-138 - source manual.md L1505-1506 - reason: Batch 4 item 3: the 2026-08-27 hook-registration correction

~~~~
  READS        hook-plane            · ~~hook registration is the one kind this element found to have NO confirmed personal home — the tracked `.claude/settings.json` is the only documented registration surface, and it travels by wholesale `git pull` replacement like every other tracked file~~ ⚠ CORRECTED 2026-08-27 (hook-plane migration): this is now backwards. Verified this session: the tracked `.claude/settings.json` carries 0 hook registrations (holds a `_hooks_moved` key instead), so it no longer travels hooks by `git pull` at all. Registration instead lives in two personal, non-repo homes — `~/.claude/settings.json` (7 entries) and the plugin cache `~/.claude/plugins/cache/lifehack-brain/lifehack-brain/0.3.13/hooks/hooks.json` (50 entries) — neither git-tracked, both installed/maintained per machine. Hook registration DOES now have a confirmed personal home; it just has two, and they can drift from each other.
~~~~

## 2026-11-22 - reason: canon move 2026-11-22: manual now lives at canon/manual.md; the private repo has desks-manual.md, so the bare-path warning no longer holds (Enver's yes)

~~~~
bare `system/organism/manual.md` then opens the private DESKS manual, not this one.
~~~~
⛔ moved 2026-11-22: the manual now lives at canon/manual.md (this entry quotes the old sentence word for word).

## 2026-11-24 - reason: canon update 2026-11-24, manual reply-drafts narrowing: drafts-are-fine approval narrowed to markdown-only reply drafts

~~~~
approval; drafts are fine (approved by Enver, 2026-11-13). A Sheet the person has named as fine china meets
~~~~

## 2026-11-24 - reason: canon update 2026-11-24, status-folder path to <brain>/status/ (ingest-provenance ledger)

~~~~
  WRITES→    ingest-provenance      · breadcrumb ledger ($DRIVE/state/status/ingest-provenance.jsonl) on every gate call
~~~~

## 2026-11-24 - reason: canon update 2026-11-24, status-folder path to <brain>/status/ (email-fallback-events)

~~~~
  FEEDS       email-fallback-events.jsonl · every store miss that routes to raw fallback appended to state/status/email-fallback-events.jsonl via _log_fallback()
~~~~
