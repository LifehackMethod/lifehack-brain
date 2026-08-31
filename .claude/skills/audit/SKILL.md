---
topic: [system-architecture]
skill: audit
description: "Three read-only subagents try to REFUTE one claim — map, project story, journals — then synthesize. Use on \"/audit\", \"has this been tried\", \"sanity-check this before I build it\", \"is this really broken\", \"check this against what we know\"."
shape: interactive-workflow
desk: root
status: active
version: 0.1
created_at: 2026-08-20
updated_at: 2026-08-20
---

## Intent (§0.5)

**User outcome.** The user hands over one claim — a plan, a "this is broken," a "we need to build X" — and
gets back whether it survives contact with what the system already knows, **before** it reaches a
builder. Not a second opinion that politely agrees: three independent read-only lanes are explicitly
instructed to try to prove the claim wrong, and the run is only worth having if it sometimes succeeds.
**Bar:** *"I brought a claim I believed, and the run either handed me a correction I could not have found
myself, or told me plainly it survived — and either way I trust the answer more than my own first pass."*

**Role.** A **pre-flight checker**, not a builder and not a court — it convenes three isolated, read-only
subagents (the map, the story, the journals), each trying to defeat the claim from its own source, then
synthesizes their returns into one answer. **Propose-only and read-only throughout**: no lane can write,
and the main session never applies anything — it hands the user a verdict and the evidence behind it.
Human-in-the-loop by construction: the machine does all the reading and cross-checking; the user is reserved
for the one thing only they can supply — deciding what to do with a contradiction once it's surfaced.

**Per-turn anchor:** `/audit · step N/4 · <subject> · next → <next>`

# audit

## Purpose

**One claim goes in. Three independent, read-only subagents run in parallel, each trying to REFUTE it
from a different source, and the main session synthesizes their returns into one answer — including the
answer that the claim survived.**

This is a **front door over three existing memory surfaces**, not a new one: `system/organism/manual.md`
+ `system/organism/elements/` (how the system is SUPPOSED to work), the active project's own brief (what
we already tried and what happened), and the append-only journal/debt-ledger/records/canon (what the
history says the brief may have lost). `/audit` invents none of these stores — it only reads them, three
ways at once, with one mandate: **try to prove the claim wrong.**

## Steps / Flow

### 1 · Take ONE claim — refuse a sweep, never pick for the caller

The user states one claim, plan, or "this is broken" — a single, bounded assertion. If they name several or
states none, **ask for one; do not guess and do not pick which one matters.** Write it verbatim into the
anchor and carry it every turn — the lanes must all be refuting the exact same sentence, not three
paraphrases of it.

### 2 · Resolve the project, once, before dispatch

Lane 2 needs a concrete brief to read, and resolving it three different ways in three different lanes
just invites three different answers to "which project is this." Resolve it **once, here, in the main
session**, and hand the resolved path into Lane 2's prompt:

1. Check the armed brief: `bash system/hooks/pm_flag.sh status`. A path back means a project is armed —
   use it.
2. If none is armed, resolve the claim's subject against `$DRIVE/system/project-registry.md` (the
   `{path}` field if present; else the legacy `desks/{desk}/state/briefs/{slug}.md` fallback the registry
   documents).
3. If neither resolves — **say so and hand Lane 2 "no project resolved"** rather than guessing a folder.
   Lane 2 still runs; it just has nothing project-shaped to read, and must say so honestly rather than
   improvising a nearby brief.

### 3 · Dispatch all three lanes, in ONE message, unnamed

Launch all three subagents together — a single message with three `Agent` tool calls — so they run
concurrently and none can see another's return before the main session synthesizes.

⛔ **SPAWN EVERY LANE UNNAMED.** Do not pass `name:` on any of the three. `system/hooks/guard_agent_return_channel.sh`
blocks a named spawn whose prompt states no delivery contract — measured on this machine, 249 named
spawns returned a payload 0 times, 1,714 unnamed spawns returned one every time. A named lane here is not
a style choice, it is a silently discarded lane.

**Subagent type:** `Explore` for all three — its own tool grant (`All tools except Agent, Artifact,
ExitPlanMode, Edit, Write, NotebookEdit`) has no Write or Edit, so a lane structurally cannot leave a mark
on disk regardless of what it's asked to do. `Agent` is also excluded from its grant, so a lane cannot
itself fan out further and dilute the independence the panel exists for.

**Model:** pin `model: sonnet` on **every** lane. Never opus — opus is reserved for three named sites
(none of them this skill) per the global Subagent Model Selection rule. Never haiku — `§II.4a [A4]` of
`skill-building-sop.md`: haiku "lost the intuition" on exactly this class of judgment work, and refuting
a claim against three memory surfaces is squarely that class.

**The shared frame every lane's prompt carries — write the mandate in, do not soften it:**

> You are one of three independent read-only lanes checking a single claim. **Your job is to try to
> REFUTE it, not confirm it.** A lane told to confirm a claim will confirm it — that is not a finding,
> it is an echo. Read your assigned source and look specifically for: a place the claim's premise is
> already wrong, a place this was already tried and failed, a place it was already ruled out or
> superseded, or a fact your source holds that the claim doesn't account for. Confirming evidence is
> only worth reporting if you looked hard for the opposite and didn't find it.
>
> For every relevant item you find, return one of exactly these four verdicts — nothing else is a legal
> answer:
> - `REFUTES` — you found evidence the claim's premise is WRONG (already tried/failed, already ruled
>   out, contradicted by a fact your source holds). This is the finding that matters most.
> - `CORROBORATES` — you found evidence that genuinely supports the claim, after having tried to refute
>   it and failed to find grounds.
> - `NOTHING-FOUND` — you looked and your source has nothing bearing on this claim either way. This is
>   a real, useful answer — say it plainly, do not manufacture a finding to look useful.
> - `COULD-NOT-READ` — you were unable to read a source you needed (missing file, permission error,
>   path doesn't resolve). This is NOT the same as `NOTHING-FOUND` — one means "I looked and it isn't
>   there," the other means "I was not able to look." Never spell one the way the other is spelled.
>
> Every `REFUTES` or `CORROBORATES` verdict MUST carry evidence: `file:line` + a verbatim quote + a
> date if the source has one. **No quote means the verdict is `NOTHING-FOUND`, full stop** — a verdict
> with no receipt is not a finding, it is a guess wearing a finding's clothes.
>
> Return `NONE FOUND` plainly if that's the honest answer. Padding a thin result with a low-confidence
> `CORROBORATES` is worse than an empty return.

**LANE 1 — THE MAP.** Reads `system/organism/manual.md`, the relevant files in
`system/organism/elements/` (search for ones bearing on the claim's subject — this is the lane's own
judgment call, not a fixed list), the organism map at the top of `~/.claude/CLAUDE.md`, and
`$DRIVE/state/projects/infrastructure/organism-audit/intended-map.md`. Its question: **"How is this
system SUPPOSED to work on this issue, ideally — and does the claim's premise match that?"**

**LANE 2 — THE STORY.** Reads the project brief resolved in Step 2 — its STORY LOG, DEAD ENDS /
DO-NOT-RETRY, OPEN LOOPS, DECISION BOARD — plus any `OPEN-FINDINGS.md` in that project's folder. Its
question: **"Have we hit this before? What did we already try that failed? What is the full storyline
the claim might be missing?"** If Step 2 resolved no project, the lane says so and returns
`NOTHING-FOUND` rather than reading an unrelated brief.

**LANE 3 — THE JOURNALS.** Reads `$DRIVE/system/journal.md`, `$DRIVE/state/debt-ledger.md`,
`$DRIVE/state/open-loops.md`, `$DRIVE/records/**`, and `$DRIVE/records/canon/**` (a canon hit outranks
everything else this lane can return). Its question: **"What does the append-only history say that the
brief may have lost?"** — it exists to fill the gaps the other two lanes structurally can't see, since
neither the map nor a single brief carries the system's full append-only memory.

### 4 · Synthesize — never quietly pick a side

Wait for all three returns before writing anything. Then:

- **Build a small table**, one row per lane: `Lane | Verdict(s) | Evidence | one-line gist`. This is
  what makes agreement (or its absence) visible across independent sources at a glance — the synthesis
  prose should never be the first place a reader learns whether the lanes agreed.
- **A disagreement between lanes IS the finding — surface it, never quietly resolve it.** Root doctrine:
  *"tension is a FINDING, not a defect to patch."* If Lane 1 says the map supports the claim and Lane 3
  found a `REFUTES` in the journal, say exactly that — do not average them into a soft middle verdict.
- **Any of these retires the claim before it reaches a builder:** a `DEAD ENDS` / RULED-OUT hit from
  Lane 2 · a debt-ledger entry marked cleared with a date from Lane 3 · a canon file ruling against it
  from Lane 3. State plainly that the plan is retired and why, with the evidence quoted.
- **Truth ordering, when sources conflict:** live command output (something you or a lane actually ran
  this session) > the brief > a plan file. State which rung the deciding evidence sits on.
- **Membership check.** If any lane returns something outside the four-member vocabulary, surface it as
  a broken return rather than silently coercing it into the nearest legal member.
- **No padding.** If all three lanes came back `NOTHING-FOUND`, say the claim was checked against three
  sources and nothing was found to refute or corroborate it — that is a complete, honest result, not a
  reason to keep digging until something turns up.

## Hard rails (what this skill will NEVER do)

- **PROPOSE-ONLY.** It never fixes, edits, applies, or writes anything — like `/architect`. `grep` for a
  write call anywhere this skill touches; if one appears, that is the defect.
- **All three lanes are READ-ONLY.** `Explore` carries no Write/Edit/Agent grant — a lane cannot leave a
  mark on disk or fan out further, regardless of what it's asked to do.
- **Every lane runs `sonnet`.** Never opus (reserved for three named main-session sites elsewhere in the
  system, none of them this skill), never haiku (loses the intuition this class of judgment needs).
- ⛔ **SPAWN EVERY LANE UNNAMED.** A `name:` on any of these three spawns gets its payload discarded —
  measured on this machine: 249 named spawns returned data 0 times, 1,714 unnamed spawns returned it
  every time. `guard_agent_return_channel.sh` blocks a named spawn with no stated delivery contract; do
  not work around it by adding one — just don't name the spawn.
- ⛔ **BUILD NO INDEX.** Lane 3 greps the journals live, every run. A journal index was tried and lost to
  plain grep "with zero maintenance" (`skill-building-sop.md §II.4a [B3]`); two orphaned journal indexes
  already sit on disk read by nothing. Do not add a third.
- **One subject per run.** If the user names several claims or none, ask which one — never pick, never
  batch them.
- **Launch all three lanes in ONE message**, never sequentially — sequential dispatch lets a later lane
  see context bleed from an earlier one's return and defeats the independence the panel exists for.

## Verification — how you know this works

Per `skill-building-sop.md` PART V. Prove the failure paths, not just the happy one.

1. `/audit` resolves from a cold window — as `/audit` **and** from prose intent ("has this actually been
   tried before").
2. **Watch a `REFUTES` fire on a real claim with a real dead end behind it** — a check never seen to fire
   is not a check.
3. **Watch `NONE FOUND` return plainly** on a claim with nothing bearing on it in any of the three
   sources — confirm the run does not manufacture a finding to look useful.
4. **A lane return with no quote is downgraded to `NOTHING-FOUND`**, never left standing as `REFUTES` or
   `CORROBORATES` — prove this actively fails a synthetic no-evidence return, not just that a good return
   passes.
5. `grep -rn "name:" skills/audit/SKILL.md` shows no lane dispatch carrying a `name:` parameter.
6. `grep` finds no `Write`/`Edit`/apply step anywhere in this skill's own instructions.

## Routing eval

`references/routing-eval.md` — prompts that SHOULD fire this, plus near-misses that should NOT, each run
**3+ times** (`skill-building-sop.md` LAW 4.3: single samples lie). Re-run whenever the `description:`
changes.

## What this deliberately does NOT do

- **No applier, at any rung.** The user acts on the verdict; the system only proposes it.
- **No index of any kind** — Lane 3 greps live, every run, forever.
- **No web lane.** An external-practice question with no ClaudeOps subject is `/research`'s job, not
  this skill's.
- **No second council.** This is a three-lane refutation panel, not the 7-lens architecture council —
  if a genuine two-viable-architectures fork is the real question, that's `/architect` COUNCIL mode.
- **No altitude reasoning.** `/architect` reads one subject at ground/5,000/10,000-ft; `/audit` checks
  one claim against three sources. Different job — do not fold one into the other.
- **No context loading for its own sake.** `/read` rehydrates a session; `/audit` exists specifically to
  try to disprove one claim, and stops once the three lanes have reported.
