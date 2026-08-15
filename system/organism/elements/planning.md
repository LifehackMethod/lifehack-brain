---
element: planning
title: "planning — element detail (ground/base altitude)"
subsystem: planning-cadence
altitude: base
record_type: organism-element
maturity_label: PARTIAL·gap [provisional] (honor)
generated_from:
  - .claude/skills/planning-daily/SKILL.md (the daily cadence — read whole, 2026-08-15)
  - .claude/skills/planning-weekly/SKILL.md (the weekly cadence — read whole, 2026-08-15)
  - .claude/skills/planning-weekly/prompts/00-system-layer.md (Phase 0, the priming contract)
  - system/tools/planning-weekly-prime-run.sh (the one scheduled leg that carries the new name)
  - system/tools/cal-vault-run.sh · system/tools/cal-vault-pull.py (the overnight pull, unscheduled)
  - system/tools/cal-diary-run.sh · system/tools/cal-diary-capture.py (the diary, scheduled)
  - system/hooks/guard_calendar_writes.sh · system/hooks/guard_tasks_writes.sh · system/hooks/lib/tasks_guard.py
  - shared/cal_config.py (the four identifiers, and why none of them has a default)
  - system/pulse-config.md (the scheduler manifest — the jobs block read row by row)
  - system/tools/organism/label_manifest.yaml (the two guards' fire-test fixtures)
  - .claude/settings.json (hook registrations — grep-verified, 2026-08-15)
created_at: 2026-08-15
updated_at: 2026-08-15
status: draft
authority: agent
---

# planning — element detail

> **LADDER: ELEMENT (full mechanics). up → manual (no `## planning` entry yet — see GAPS) ; ground truth → the live artifacts (generated_from)**
>
> **Altitude = BASE (ground / street view).** The in-the-weeds detail of PLANNING — the cadence
> layer that answers *"what do I do today"* and *"what does this week look like."*
>
> **One-line:** two interrogative planning skills — a **daily** trust-fall and a **weekly**
> helmsman — that mine the reader for the judgment a machine cannot pull from data, batch every
> write to the end, and put it behind a gate they confirm by hand.
>
> **Step grammar:** `actor → port/tool → store → gate`
> Enforcement tags: `[hook]` (a real guard fires) · `[skill]` (skill logic / mandatory script) ·
> `[honor]` (prose instruction only, no mechanical enforcement) · `[human]` (deliberate HITL pause).

> ⛔ **CITATION BANNER — two names below are deliberately not files in this repository.**
> `system/organism/elements/cal-pipeline.md` — ⛔ excluded from the migration: **personal.** It is
> the donor's own calendar desk element, and this file is its generic replacement, not its copy.
> `state/status/planning-weekly-prime.json` — ⛔ runtime-generated, created on first run, never
> committed. Both are named here so a reader is redirected rather than sent hunting.

---

## AUTHORED   (human-only)

### ⭐ WHY THIS ELEMENT EXISTS AT ALL — read this before comparing it to anything

This element has **no donor counterpart.** The donor system described its planning capability in
`elements/cal-pipeline.md`, which was correctly left behind: that file describes **one person's own
calendar desk** — their lanes, their calendar, their week — and the exclusion list rules the six
desk elements out as personal.

**But the capability itself ships.** The two skills are here, the tools are here, one scheduled row
is here, and two hook guards fire on the write path. Leaving the corpus with no planning file at all
would have taught the next reader that this system cannot plan a day — which is false. So this is a
**freshly-written generic description of what is actually on disk**, in the same move that produced
`system/organism/elements/brain.md`.

⛔ **Do not reconcile this file against `cal-pipeline` at the donor.** They describe different
things: that one describes a person's desk, this one describes a capability a reader receives.

⚠ **What you receive is a MECHANISM, not a week.** Every specific thing the donor's file named —
the lanes, the calendar ids, the voice, the goals list — is **the reader's own**, held in their
notes folder and in `<notes>/config/cal.md`, never in this repository. The skills ask for those on
first run rather than inventing a set (`.claude/skills/planning-daily/references/lane-board.md` does
this explicitly).

---

### WHAT ACTUALLY SHIPS — verified on disk, 2026-08-15

| Piece | Where | State |
|---|---|---|
| the daily cadence | `.claude/skills/planning-daily/SKILL.md` (+ 11 prompt beats + 3 references) | ships · Layer 1 verified end to end · Layer 2 unproven here |
| the weekly cadence | `.claude/skills/planning-weekly/SKILL.md` (+ ANCHOR + 17 prompt beats + 4 map-agents + 9 leverage angles + 6 council members) | ships · **UNDER CONSTRUCTION, never run end to end here** |
| the mid-week map priming cron | `system/tools/planning-weekly-prime-run.sh` + its row in `system/pulse-config.md` | ships · scheduled · never LIVE-fired end to end |
| the diary (capture + rollups) | `system/tools/cal-diary-capture.py` · `system/tools/cal-diary-rollup.py` · `system/tools/cal-diary-run.sh` | ships · scheduled (one row drives five cadences) |
| the read-only calendar health check | `system/tools/cal-health.py` | ships · scheduled · no `*-run.sh` wrapper (no lock, no buzz) |
| the overnight raw-vault pull | `system/tools/cal-vault-run.sh` → `system/tools/cal-vault-pull.py` | ships · **NO scheduler row** — see GAPS |
| the weekly deep pull + its analysis | `system/tools/cal-vault-weekly-run.sh` → `system/tools/cal-window-to-vault.py` → `system/tools/cal-weekly-analyze-run.sh` | ships · **NO scheduler row** — see GAPS |
| the overnight analysis panel | `system/tools/cal-analyze-run.sh` | ships · **NO scheduler row** — see GAPS |
| the light metadata sweep | `system/tools/cal-light-sweep.py` | ships · called on demand by the daily |
| the goals-list writer | `system/tools/cal-lifemap-write.py` | ships · called by the weekly's clerk |
| the identifier reader | `shared/cal_config.py` | ships · **nothing here has a default** |
| the two write walls | `system/hooks/guard_calendar_writes.sh` · `system/hooks/guard_tasks_writes.sh` (+ `system/hooks/lib/tasks_guard.py`) | ships · registered · **fire-tested LIVE this session** |

⚠ **THE FILENAMES STILL SAY `cal`, AND THAT IS DELIBERATE.** The skills were renamed
`cal-daily` → `planning-daily` and `cal-weekly` → `planning-weekly`; the **tools and the data paths
were not.** `.claude/skills/planning-daily/SKILL.md` states why at length: the tools construct
`<notes>/desks/cal/...` directly and `shared/cal_config.py` hardcodes `<notes>/config/cal.md`, so
renaming the references inside the skills alone would point them at a folder nothing writes to.
**This is a half-finished rename left visible on purpose — not a missed one.**

⛔ **THERE IS NO `desks/planning/` TREE IN THIS REPOSITORY, AND THERE IS NOT MEANT TO BE.**
`system/desk-registry.yaml` ships **empty** (`desks: []`) by design — a fresh install has no desks,
and a full desk is promoted by hand through `system/sops/desk-building-sop.md`. All planning
**content** lives under the reader's own notes root, resolved through `shared/brain_root.py`, and is
never committed. Verified by directory listing this session: no `desks/` at the repository root.

---

### THE DAILY — `planning-daily`, two layers decided fresh every run

**Trigger:** the reader types `planning daily` / `what's my day` / `morning check-in` / `trust fall`
(the skill's own `triggers`). It runs **interactively in the main session**, never as a subagent —
every gate is a human turn.

**The two-layer split is the most important thing about it.**

- **Layer 1 needs no account, ever.** A diary lookback, an interrogative planning conversation, and
  open-loop tracking. It works the first time the skill is ever opened, on a machine with no Google
  anywhere near it. Its own SKILL.md makes the claim this layer exists to answer: it is *"the
  product's only answer to 'what do I open tomorrow'"* — every other skill in this repository is
  retrospective, grown from material that already exists, and **nobody's day is a subject an ingest
  could discover.** So Layer 1 asks. `[skill]`
- **Layer 2 sits on top when Google is connected** — calendar and task surfaces, the life-lane gap
  check, the logistics pass, the ranking, the gated write.

**Nothing chooses between them by hand.** `.claude/skills/planning-daily/prompts/00-preflight.md`
checks **every run** — `gws` on PATH, authenticated, and all four identifiers present via
`shared/cal_config.py` — and announces which layer is live before the first question. It is never
carried over from a prior session and never assumed from whether it worked last time. `[skill]`

**Two gears, and the doctrine note that keeps them apart.** The interrogation, the gates and every
approval run in the main session (gear 1). Already-confirmed I/O is fanned out to two named sonnet
subagents (gear 2): a **scribe** that persists the scratchpad at each pass boundary, and a **clerk**
that at Pass 5 drains the whole confirmed write-ledger and **reads each write back** before marking
it done. The skill argues its own case for this: *"human-in-the-loop execution stays in the main
session"* governs the interrogation and the gates, **not** the flush of writes the reader already
confirmed — already-decided I/O has no human left in its loop. `[skill]`

**The one-dataset rail.** The heavy verbatim re-ingest (a full `system/tools/cal-vault-pull.py`
rebuild) is banned mid-session — that is the freeze the skill exists to kill. A **light,
metadata-only sweep** (`system/tools/cal-light-sweep.py`) is explicitly allowed and encouraged. The
distinction is diagnostic: re-reading for something that was already there means the morning capture
**failed**, and papering over it with a re-read hides the real defect. `[honor]`

⛔ **ONE SURFACE OF THREE DOES NOT WORK, EVEN IN LAYER 2 — the email slice.** Calendar and tasks
work fully; email does not. `shared/tools/email_convert.py` is present here as of 2026-08-14 but has
**never been run against a real mailbox**, and the skill's own table says so. The pull says this out
loud rather than returning an empty result, on the reasoning that *a morning briefing that reports a
clear inbox every single day is worse than one that admits it never opened the door.*

---

### THE WEEKLY — `planning-weekly`, seven phases, under construction

**Trigger:** `planning weekly` / `weekly review` / `run my week` / `set my week` / `week ahead`.
Also main-session-only, also human-in-the-loop.

⛔⛔ **IT SHIPS MARKED UNDER CONSTRUCTION AND HAS NEVER BEEN RUN END TO END HERE.** Its own
frontmatter says it, and names the reason: *shipped whole per the migration law ("broken is fine,
migrate it") rather than held back or trimmed to what's proven.* Treat every phase description below
as **a description of the code, not a report of a working run.**

**The seven phases, blind-chained** — each driver is fetched one at a time, and the run may not read
ahead. The stated reason is behavioural, not stylistic: shown the finish line, an interrogative skill
goes *barn sour* — it rushes the ending and pre-writes the conclusion it was supposed to mine out.

| # | Phase | Driver |
|---|---|---|
| P0 | System Layer — builds the week's Map (machine-only, no human turn) | `.claude/skills/planning-weekly/prompts/00-system-layer.md` + the briefs in `prompts/map-agents/` |
| P1a | **LOOK BACK** — confirm the week that was; fires unprompted | `prompts/01a-lookback.md` |
| P1b | Orientation | `prompts/01-orientation.md` |
| P2 | Connect the Dots | `prompts/02-connect-the-dots.md` |
| P3 | Prioritization — 3 reports + a 9-angle leverage engine | `prompts/03-prioritization.md` + `prompts/leverage-angles/` |
| P4 | The Council — six members | `prompts/04-council.md` + `prompts/council/` |
| P5 | Action — calendarize, report, then the clerk writes | `prompts/05-action.md` + `.claude/skills/planning-weekly/prompts/05-act-clerk.md` |
| P6 | Triage — optional inbox-zero | `prompts/06-triage.md` + five sweep sub-drivers |

**Phase 4 IS the council engine.** It dispatches six member briefs as an advisor roster running
blind-diverge → argue → converge — the same engine described in
`system/organism/elements/council-engine.md`. Those six members are the **one place in this element
that runs opus**; every other subagent here is sonnet.

**The three-layer injection model** keeps the skill leading across a long session:
`.claude/skills/planning-weekly/ANCHOR.md` re-injected every turn via
`system/hooks/skill_anchor.sh` (L1) · a one-line phase HUD repainted every turn via
`system/tools/skill_hud.sh` (L2) · the phase driver loaded once at phase entry (L3).
⛔ **The skill states its own ceiling and it must not be overstated:** a hook cannot author the
model's output tokens, so L1/L2 make a behaviour *far more likely* and can never *guarantee* it.
**Rendering is not enforcement.**

**Priming, and the rule that survived a reversal.** An earlier ruling forbade any scheduled pass at
all; it was superseded 2026-08-06 (`authority: user`) by a narrower one, quoted in
`prompts/00-system-layer.md`: **a scheduled pass MAY prime the Map; no phase may EVER assume it.**
Every phase must still run correctly with no priming, behind a bounded `{WARM, PARTIAL(n of m),
COLD}` state where `COLD` is never spellable the same way as `WARM`. ⭐ **What was always forbidden
is the ASSUMPTION, never the SCHEDULE.** The superseded text is struck in place, not deleted.

---

### THE SCHEDULED LEG — one row carries the new name, three runners carry none

`system/tools/planning-weekly-prime-run.sh` has a row in `system/pulse-config.md`'s jobs block and is
dispatched by `system/tools/pulse.sh`. It ticks **daily** even though its work is weekly, because its
own cadence guard (a Thursday window with Friday/Saturday catch-up, ISO-week-idempotent on the mere
existence of `map.md`) needs a daily check to catch the window at all.

**What it actually does, and the honest limit on it.** It cannot invoke Phase 0's real fan-out — that
is `MODEL-REACH: SESSION`, uses the Agent tool inside a live interactive session, and a scheduled
path *"would silently skip the model step entirely."* What it ships instead is the CLI-level shape:
separate headless `claude -p` processes, one per lens, reading **the same four lens briefs Phase 0
itself reads** and the same output contract, over the same corpus window Phase 0 pulls
(`shared/tools/item_store_window.py --last-days 7 --mode bundle`). A small inline assembler writes a
partial-but-honest `map.md` when fewer than four lanes land.

**Its contract with the skill is a two-way refusal:** priming writes `map.md` and **never**
`session-scratchpad.md`, so the skill can still tell *primed-but-not-yet-reviewed* from
*already-reviewed*; and the runner refuses to prime a week whose scratchpad already exists, so a
review already under way is never clobbered.

**Every branch emits a status tile,** including the skip branches — a windowed job that silently
exits clean on a skip ages into a false STALE that is indistinguishable from broken. Unconfigured
installs stand down at **rc=75** (*"this job's own preflight declined to run this tick"*) rather than
failing, so a machine that has simply never run `claude setup-token` does not trip the three-strike
breaker. Credentials come from the two shared preflights, `system/tools/claude-auth.lib.sh`
(required) and `system/tools/gws-auth.lib.sh` (optional here — the lenses read local files, so no
Google means a still-useful result, not a failure).

⚠ **The other three runners have no row at all** — `system/tools/cal-vault-run.sh` (the overnight
pull the daily's Layer 2 is written around), `system/tools/cal-vault-weekly-run.sh`, and
`system/tools/cal-analyze-run.sh`. `cal-vault-run.sh` says so in its own header. **The daily
compensates:** its lookback beat now pulls live if no vault exists for today, *rather than assuming a
cron ran* — because a fresh reader has no cron. So the absence degrades the experience without
breaking it. See GAPS.

---

### THE CONFIG SEAM — four identifiers, and why none of them has a default

`shared/cal_config.py` is the **only** thing that reads a calendar or task-list identifier. The
donor's fifteen tools each carried the same four values as module constants; shipping that would have
been worse than shipping nothing, because **an agent that writes to a calendar id baked into a tool
writes to somebody else's calendar, and the failure is silent to the person running it** — their
events simply never appear.

⛔ **NOTHING HERE HAS A DEFAULT. A default calendar id is a wrong calendar id.** Every accessor
either returns what the reader wrote in `<notes>/config/cal.md` or raises `CalConfigMissing`, whose
message names the exact missing key. The four keys: `personal_calendar` · `agent_calendar` ·
`goals_tasklist` · `daily_parent_task`.

⚠ **The consequence, and it surprises people:** because both guards are **fail-closed**, an install
with no `<notes>/config/cal.md` has its entire Layer 2 write path **walled shut**. That is correct
behaviour, not breakage — but a reader who has not done the one-time setup will see every calendar
and task write refused, with a redirect naming the file to fill in.

---

### STORES + PATHS

| Store | Path | Access | By |
|---|---|---|---|
| the reader's identifiers | `<notes>/config/cal.md` | READ only, via `shared/cal_config.py` | both skills; both guards, at fire time |
| the daily raw vault | `<notes>/desks/cal/state/raw-vault/<today>/` | WRITE by the pull · READ by the daily | `system/tools/cal-vault-pull.py`; the daily |
| the daily scratchpad | `<notes>/desks/cal/state/raw-vault/<today>/session-scratchpad.md` | living world model — pruned/updated every turn, persisted at pass boundaries, **deleted in Pass 5** | the scribe; the clerk |
| the weekly scratch dir | `<notes>/desks/cal/state/checkin-scratch/weekly-<YYYY-Www>/` | `map.md` written by priming or P0 · `window.json` the corpus · `session-scratchpad.md` the run | `system/tools/planning-weekly-prime-run.sh`; the weekly |
| the diary | `<notes>/desks/cal/diary/{YYYY}/{MM}/{DD}.md` | WRITE (mechanical, fail-soft, zero credentials) | `system/tools/cal-diary-capture.py` |
| the weekly review record | `<notes>/desks/cal/records/weekly-reviews/<YYYY-Www>.md` | plain append | the P5 clerk |
| the goals list / life map | Google Tasks + `<notes>/desks/cal/life-map.md` | READ-ONLY with **one** sanctioned write | `system/tools/cal-lifemap-write.py`; the clerk |
| the reader's lanes, rails, voice | `<notes>/desks/cal/skill-refs/user-canon.md` | READ | both skills |
| the corpus window | the item store, via `shared/tools/item_store_window.py` | READ | P0; the priming cron |
| the status tile | `state/status/planning-weekly-prime.json` | WRITE on every branch | the priming cron, via `system/tools/emit_status.py` |

⚠ **`<notes>/desks/cal/skill-refs/user-canon.md` never ships, and the reason is stated in the skill
rather than left to inference:** those are the reader's own life lanes, *"and ten of someone else's
would be worse than none."*

---

### GATES AND ENFORCEMENT (the honest map)

**Two real hooks. Everything else on this page is prose.**

- **`system/hooks/guard_calendar_writes.sh`** `[hook]` — every calendar write must target the
  configured `agent_calendar`; `primary` is refused. Registered `PreToolUse`/`Bash` in
  `.claude/settings.json` (grep-verified this session, line 211). **DEFAULT DENY**: the file carries
  an explicit instruction not to add an `|| exit 0` after its final test, because that exact
  fail-open is the bug an earlier inversion fixed — `gws calendar events insert --calendar primary`
  blocked correctly while `gws calendar +insert --calendar primary` **walked straight through**.
- **`system/hooks/guard_tasks_writes.sh` + `system/hooks/lib/tasks_guard.py`** `[hook]` — refuses any
  `gws tasks` write touching the configured `goals_tasklist`, with exactly one carve-out (the day's
  plan as subtasks under `daily_parent_task`); `delete` and `clear` never pass there, carve-out or
  not, because **Google Tasks keeps no version history and a deleted task is simply gone.**
  Registered `PreToolUse`/`Bash` (line 216). ⭐ **The decision was moved OUT of the shell wrapper into
  a real parser** after three independent auditors, each charged to refute it, found **seventeen
  working bypasses across three passes** — a semicolon, a newline, two adjacent quotes, `xargs`, a
  duplicate JSON key, `@default`. The patch for round two also **broke the legitimate path**,
  refusing a plan titled *"Q3 R&D review"* because a text matcher cannot tell an `&` inside a quoted
  string from a shell operator. Simultaneously too weak and too strict is the signature of the wrong
  instrument, not a bad rule.
- **Both are fail-closed on an unresolvable target.** An unknown is never read as permission: a write
  with no goals list on file, a target hidden behind a variable, `@default`, or an omitted list are
  all refused with a redirect. Reads always pass, on any list.
- ⭐ **FIRE-TESTED, THIS SESSION.** `python3 system/tools/organism/label_checker.py check` returned
  exit 0 and *"every claimed label verified against live behavior"*, with
  `calendar-primary-write-guard` and `tasks-readonly-list-guard` both **LIVE** — *git-tracked +
  registered + blocks every violation + passes every allow*. Their fixtures live in
  `system/tools/organism/label_manifest.yaml`, and `system/tools/guard-fire-test-run.sh` re-runs the
  whole set weekly.
- **The Pass-5 / Phase-5 confirmation gate** `[human]` — every write is batched to a ledger and
  flushed only after the reader confirms, with each row read back before it is marked done.
  ⚠ **It is not redundant with the guards** — the guards read a command as text, and a shell has
  endless ways to spell the same thing. The guard's own header says so at length.
- **Everything else is `[honor]`** — the interrogative law, the blind chain, the one-dataset rail,
  the mark-inference rule, the never-write-synchronously rule, the rolling roundup, the
  money-is-computed rule. None of them is backed by a hook. Their evidence surface is the
  **transcript**, which is why the skill states that any later grading of them returns
  **INCONCLUSIVE, never FAILED** — an evidence gap is not a behaviour gap, and nobody downstream
  should read it as one.

---

### EDGE CASES

1. **No Google account, ever.** Layer 1 runs alone and says plainly what is missing rather than
   erroring or quietly doing less than it claims. This is the design centre, not a degraded mode.
2. **No `<notes>/config/cal.md`.** Both guards refuse every write with a redirect naming the file. A
   reader can still run the whole daily conversation; only the write path is shut.
3. **No vault for today.** The daily's lookback pulls live rather than assuming a cron ran. Slower,
   correct, and the only behaviour that works for a reader with no scheduler installed.
4. **The weekly's Phase 0 finds no Map.** It runs Phase 0 in the moment and does not address the
   reader until the Map exists. A COLD start is a supported state, never an error.
5. **The priming cron and a live review collide.** The cron refuses the week outright if
   `session-scratchpad.md` exists. The artifact *is* the done-state; there is no separate marker file.
6. **Fewer than four priming lanes land.** `map.md` is written partial, labelled partial. Zero lanes
   landing writes nothing at all and leaves the Friday/Saturday catch-up available.
7. **A compacted or resumed run.** Both skills re-anchor rather than restart: re-read the scratchpad,
   find the last completed-phase marker, re-arm the anchor and HUD, continue from the first
   unfinished phase. Never re-stamp a confirmed answer.
8. **An abandoned run.** The anchor, the HUD and `system/hooks/scratch_flag.sh` are all cleared with
   absolute paths at the end — and only if every write row succeeded. A TTL backstops a forgotten
   clear; on a failed row the session is deliberately left hot for recovery.
9. **A long turn degrading.** Observed twice in a real run at the donor: duplicated headers,
   duplicated lines, skipped numbers in a question list. The rule is to re-render the block rather
   than ship it — `[honor]`, and worth knowing it has actually happened.

---

### INTEROP SEAMS

```
CHAINS       council-engine        · planning-weekly Phase 4 IS the advisory-council engine — six member
                                     briefs dispatched as the advisor roster, blind-diverge → argue →
                                     converge; the members are this element's ONLY opus subagents [skill]

FEEDS        item-store            · both skills read the faithful de-duplicated library through
                                     shared/tools/item_store_window.py (--mode bundle); metadata-only and
                                     index-only reads are REJECTED — you cannot tell what matters from
                                     subjects. The store is the query layer, not Google [skill]

KEYS-OFF     gws-plane             · every calendar and task read/write goes out through the gws CLI; the
                                     four identifiers come from the reader's own config via
                                     shared/cal_config.py, never from a constant in a tool [skill]

GUARDED-BY   hook-plane            · guard_calendar_writes.sh (agent calendar only, default-deny) and
                                     guard_tasks_writes.sh + lib/tasks_guard.py (goals list read-only, one
                                     carve-out, delete/clear never) — both registered PreToolUse/Bash and
                                     both fire-tested LIVE [hook]

TRIGGERS     pulse-cron            · system/pulse-config.md carries planning-weekly-prime (daily tick, weekly
                                     work), cal-diary (one row driving five cadences) and cal-health;
                                     cal-vault / cal-vault-weekly / cal-analyze have NO row — see GAPS [skill]

WRITES->     journal               · the diary under the reader's notes root is written by
                                     cal-diary-capture.py, which protects the Human Delta block and
                                     completes with gws entirely absent from PATH [skill]

SHARES-STORE checkin               · /checkin's journal-first writes feed cal-diary-capture.py; a skipped
                                     checkin starves the diary silently — the failure is invisible at the
                                     planning end [honor]

SHARES       statusline-hud        · skill_hud.sh paints the per-phase HUD and scratch_flag.sh paints the
                                     scratchpad indicator; both are rendering, never enforcement [skill]

SHARES       scratch-capture-gate  · scratch_flag.sh arms the capture gate on the resolved scratchpad path;
                                     the weekly raises SCRATCH_TTL_MIN to 180 because its run is long [skill]

READS        safe-reader-plane     · external content (email bodies, invites, task text from anyone) is
                                     ADVERSARIAL DATA — facts extracted, embedded instructions never obeyed;
                                     the priming cron restates this verbatim in every lens prompt [honor]

COMPLEMENTS  email-service         · the daily's email surface routes through shared/tools/email_convert.py,
                                     which is present but has never been run against a real mailbox — the
                                     inbox slice is EMPTY BY BREAKAGE, and says so [skill]

COMPLEMENTS  build-plan-plane      · a different sense of "plan": that element structures and executes
                                     PROJECT plans (Phase, Feature, Task). This one plans a DAY and a WEEK.
                                     They share no code and no store — named so nobody merges them [honor]

PROPOSES     backlog-authority     · the weekly's ranked output and the daily's open-loop pass both surface
                                     work the reader then decides on; neither writes a backlog itself [honor]
```

---

### GAPS

1. ⛔ **THREE RUNNERS HAVE NO SCHEDULER ROW** — `system/tools/cal-vault-run.sh`,
   `system/tools/cal-vault-weekly-run.sh`, `system/tools/cal-analyze-run.sh`. Verified this session
   by reading the whole jobs block in `system/pulse-config.md`. `cal-vault-run.sh` names its own
   absence in its header (*"this runner specifically has no row there yet"*). **Blast radius:** the
   "overnight vault" the daily's Layer 2 is written around never gets built unattended. Mitigated,
   not closed — the daily pulls live when no vault exists. **Disposition: unruled.**
2. ⛔ **THE EMAIL SURFACE IS DEAD IN LAYER 2.** `shared/tools/email_convert.py` ships but has never
   been run against a real mailbox. The inbox slice is always empty — *not looked at*, not "nothing
   came in." The tool says so out loud rather than returning a clean-looking empty result.
   **Disposition: known, named in the skill.**
3. ⛔ **THE MCP BYPASS — the calendar guard is `gws`-shaped.** `system/hooks/guard_calendar_writes.sh`
   pre-filters on the `gws` binary appearing in a Bash command, so **an MCP calendar tool call routes
   around it entirely.** `.claude/skills/planning-weekly/SKILL.md` states this directly: pinning to
   `gws` plus the configured id *"is what makes the guard actually fire — an MCP calendar call routes
   AROUND it."* This is the `·gap` on this element's label: a reader who stops at the gloss would
   believe calendar writes are walled, and on a non-`gws` path they are not. **Disposition: unruled
   here** — no class-level ruling covers this element.
4. ⛔ **NEITHER SKILL HAS BEEN RUN END TO END IN THIS REPOSITORY.** The weekly is marked UNDER
   CONSTRUCTION and has never completed a run; the daily's Layer 1 is verified end to end but Layer 2
   is wired-not-run. The priming cron is scheduled but, like the other four rows added the same day,
   was verified by exercising its skip branches rather than by a real fire.
5. ⚠ **A TENSION, RECORDED NOT RESOLVED — where the calendar id lives.**
   `.claude/skills/planning-daily/SKILL.md` and both guards read the id from `<notes>/config/cal.md`
   via `shared/cal_config.py`. `.claude/skills/planning-weekly/SKILL.md` still tells its run the id is
   in `<notes>/desks/cal/skill-refs/user-canon.md`. Both files ship; they disagree. This is a
   **finding** — do not quietly edit one to match the other, and do not stack a new rule on top of it.
6. ⚠ **THIS ELEMENT HAS NO `## planning` ENTRY IN `system/organism/manual.md`.** The manual's ranked
   index is deliberately frozen as the donor's list of 51, with a banner naming the ten that did not
   migrate; a newly-authored element with no donor counterpart has no number to take, which is why
   `system/organism/elements/brain.md` is not in it either. The middle-altitude entry is therefore
   **owed**, not present. Naming it beats leaving a reader to discover the silence.
7. ⚠ **NO DOOR ON THE MAP.** The always-loaded map block in `CLAUDE.md` mentions planning only as one
   word inside the scheduled-jobs line; there is no goal-phrased routing line pointing at this file. A
   reader whose only source is the map cannot find the planning capability at all.

---

### INTENT / CURRENT-VS-TARGET

**Purpose.** Every other durable skill in this system is **retrospective** — it reasons over material
that already exists. A day does not exist yet. So this element is the one place the system **asks**,
and its whole design follows from that: it commits a read and invites correction rather than opening
a blank page; it does everything a machine can do first, so the only thing left to spend a human turn
on is judgment, taste and private context; and it writes nothing until the reader says so.

**BY DESIGN — interrogative, never conclusory.** The stated law in both skills is that the run
**surfaces and interrogates** and does not solve, conclude or decide. *"When you feel the urge to
wrap up with a recommendation, ask another question instead."* The ranked outcome is a suggestion the
reader confirms, never a verdict handed over. A run that produces a tidy recommendation quickly has
failed at the thing it exists for.

**BY DESIGN — human-in-the-loop is the product, not a gap.** Classify it correctly: the pauses here
are **BY DESIGN**, not DEGRADED and not BROKEN. The data is only dots; the picture — the threads, the
shadow context — lives only in the reader's head, and mining it is the job.

**BY DESIGN — Layer 1 owes nothing to any account.** The split exists so the capability is real on
day one, with no Google, no cron and no configuration. Everything above that is additive.

**Current state → PARTIAL·gap, for precise reasons.** What is REAL and verified on disk: both skills
ship whole with every prompt beat; twelve tools ship; three scheduler rows are wired; and **two hook
guards fire, fire-tested LIVE this session.** What holds it below LIVE: the weekly has never
completed a run here, the daily's Layer 2 is unproven, one of its three surfaces is dead, and three
runners have no scheduler row. `·gap` for the MCP bypass in GAPS #3. `(honor)` because the element's
**main** promise — the interrogative discipline itself — is prose with no hook behind it.
`[provisional]` because this file is newly authored and has not been independently reviewed.

**TARGET, in the order that buys the most.**
1. **Wire the three missing rows** into `system/pulse-config.md`. It is the smallest change with the
   largest effect: it converts the daily's Layer 2 from *pull it live and wait* to *it was ready
   before you woke up*, which is the experience the skill is written around.
2. **Run the weekly once, end to end, and record what breaks.** It has a stress-test artifact from
   the donor (`.claude/skills/planning-weekly/audit/2026-07-20-stress-test.md`) and an open build
   checklist (`.claude/skills/planning-weekly/BUILD-CHECKLIST.md`); neither substitutes for a real run.
3. **Prove the email surface** against a real mailbox, or say plainly that the surface is two of
   three and stop describing a third.
4. **Resolve the rename honestly** — either finish `cal` to `planning` across the tools and the data
   paths in one move, or write down the decision that they stay. A half-rename left visible is correct
   today and rots into confusion if nobody rules on it.
5. **Owe the manual its entry and the map its door** (GAPS #6, #7).

---

## AUTO-COMPUTED   (machine-only — hand-set at authoring; the label checker owns the guard half already, not the element label)

- **maturity_label:** PARTIAL·gap [provisional] (honor)
- **last_checked:** 2026-08-15 — guards, by fire test; the element label itself hand-set and never
  fire-tested.
- **check_detail:** The guard half of this element **was** fire-tested this session:
  `python3 system/tools/organism/label_checker.py check` returned exit 0 and *"every claimed label
  verified against live behavior"*, with `calendar-primary-write-guard` **LIVE** and
  `tasks-readonly-list-guard` **LIVE** (git-tracked + registered + blocks every violation + passes
  every allow). That is the strongest claim on this page and it is machine-backed. Everything else is
  hand-set: the element label is not an entry in `system/tools/organism/label_manifest.yaml`, and no
  fixture exists for a skill's conversational discipline. What is REAL, verified by reading the
  artifacts this session: both skill trees ship whole; twelve tools ship under `system/tools/`; three
  rows exist in `system/pulse-config.md` (`planning-weekly-prime`, `cal-diary`, `cal-health`);
  `system/desk-registry.yaml` ships empty by design. What is HONOR-ONLY: the interrogative law, the
  blind chain, the one-dataset rail, the rolling roundup, mark-inference, and
  never-write-synchronously. What is UNPROVEN: any end-to-end run of either skill in this repository.
  Real walls on the write path plus a shipped, unproven conversational layer ⇒ **PARTIAL**; `·gap`
  from GAPS #3 (a non-`gws` path routes around the calendar guard); `(honor)` because the main promise
  is prose; `[provisional]` because this file is newly authored and not independently reviewed.

