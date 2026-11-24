# The skill spec form, v2

> The form every skill spec is written on. Pre-filled, not described: every section shows the shape,
> tells inside each blank, and gives one filled line. It holds only what any runtime skill needs; a skill
> builder's own interview machinery (its packet, its question style, its review step) lives in that
> builder's own spec, never here.

**What this form is:** the one spec every skill and every command fills (one form; the step count is a switch inside
it). It describes how the skill RUNS: its steps, its role, its screens, its proofs, its status note.
**Who fills it in:** an AI designing the skill with its person (usually /skill-builder). The person never fills it in
or reads it as a form; whoever designs with them may read it back in plain words (a readout) before it is handed on.
**How to fill it:** top to bottom. Text outside `< >` is fixed: copy it. Each `<…>` is a blank with its instruction
inside: replace it, brackets included. A block marked **(pre-filled)** is the same for every skill: leave it as is.
Each blank starts with its LINE KIND (legend). A path written `‹at filing: …›` is a plugin home not yet settled while
this form is a draft: copy it as written; the form's owner sets it when the form is filed.
**Attached templates** (one home each; this form points to them, never copies them), all in
`‹at filing: this form's folder›`: `house-style.md` (every screen), `step-prompt-template.md` (one per step),
`subagent-brief-template.md` (one per helper).
**The examples:** lines marked *Example:* follow one made-up skill, `/receipt-sorter` (three steps: read the receipts,
sort them into categories, total each category), plus a one-step command, `/receipt-total`, where a command differs.
They are illustrations only: never copy an example's answers into the skill being designed.

Not skill folders, so there is no file to find:

> ⛔ `/next` is not a skill folder: a command the shared step runner writes when a run starts.

> ⛔ `/back` is not a skill folder: a command the shared step runner writes when a run starts.

> ⛔ `/receipt-sorter` is not a skill folder: a made-up example skill.

> ⛔ `/receipt-total` is not a skill folder: a made-up example command.

## LEGEND (pre-filled)

**Blanks and line kinds**

| mark | meaning |
|---|---|
| `<…>` | a blank; the words inside say what goes there |
| `[ask]` | settled only by the person: their own words (their first request included), or their "yes, that's it" to a play-back. Until then the line holds your recommendation and ends `[inferred]` (confidence medium or high) or `[hypothesis]` (confidence low) |
| `[builder]` | the designer decides. The line ends `[builder's choice]`; the person may veto all of these in one batch before hand-off |
| `[after build]` | only the build can know it. Written as one line in FOR THE PLANNER AND THE BUILD, never here |
| no end mark | confirmed by the person. Write the source at the end in brackets: `(D<n>)`, the line in DECISIONS that records it |
| `(optional)` | after an input: its absence never makes a sub-step wait |

**Every spec starts blank (pre-filled).** A new skill's spec starts empty. Its DECISIONS start at D1, then D2, D3…,
in the order made, with no gaps. It never cites or copies another skill's spec, rulings or decisions.

**Where questions live, and where answers go (pre-filled).**
- A question is asked on the person's SCREEN, in the house style's question block, carrying your recommendation, how
  confident you are, and how load-bearing the decision is. The question is never written into this spec.
- Until the person answers, the blank holds your recommendation with its end mark (`[inferred]` or `[hypothesis]`).
  Still unanswered when the spec is handed on → it is also one item in §8.
- The person's own words already answer a blank (their first request included) → write their words as the answer,
  with no end mark and a D-line, and never ask that blank again.
- An answer is recorded in two places only: on its own line here (end mark removed, `(D<n>)` added) and as one
  numbered line in DECISIONS. If the designer keeps a separate design record (verbatim words, numbered rulings), the
  D-line names that ruling too; the cover sheet says where the record is.

**The ladder (§4)**

| mark | meaning |
|---|---|
| 🤖 / ➡️🏃 / 🙋 | this session (the AI in the person's window) does it / a sub-agent (a separate AI working on its own) does it / the person does it |
| 💾 / ⚙️ / 🖥 / 🤝 | stored information / computes or decides / shows something / waits on the person |
| TALK / ALONE | right after the number: TALK shows the person something; ALONE never does |
| 🔁 | a loop line: sends the run back to repeat earlier sub-steps; no TALK or ALONE |
| ⑂ | a fork: a question whose answer sends the run to a named place |
| `→ CODE (<a>\|<b>\|none-of-these)` | the answer must be one of a fixed set, always ending in `none-of-these` |
| `→ LLM (open)` | the answer is free text, read by the AI |
| `⟵ incoming from <N.M>: "<section>"` / `⟶ for <N.M>: "<section>"` | receiver end / sender end of a handoff, naming an exact §5 section |
| `⟵ from the person: "<section>"` | what the person typed or pasted; the TALK sub-step that receives it writes it to that §5 section |
| `⟵ from the trigger: <what>` | the first sub-step's input when the run is started by its trigger (§3) |
| `⟶ outside: <where>` | an output that leaves the skill (a sent email, a file in the person's notes, another skill); it is listed in §9 |
| `⟵ incoming from last run` / `⟶ for next run` | something one run leaves for the next; it lives in a file listed in §9 |
| `screen:` | under a TALK sub-step: what the content slot shows, in order |
| `├` `│` `└` | a sub-step / a line belonging to it / the last line |
| ✅ | "Done when": the felt result; the only definitive line |
| §N / N.M / L<n> / D<n> | section N of this form / sub-step M of step N / row n of §2 / line n of DECISIONS |

**Model tiers** (pre-filled): `small`, `medium` or `large`, never a model name (§6, the helper routing SOP). Helpers
default to `medium`; `small` only for mechanical lookups; anything that judges or classifies is `medium` or above.

## COVER SHEET

**Cover sheet.** Building: <[ask] the skill's name>, registered as `/<name>`, a <[builder] "command (one step)" |
"skill (<N> steps)", from the step count in §4> that <[ask] one line: what it does>. Status: <[builder] on a first
fill: "First fill: drafted from the person's request; nothing confirmed yet." Later: "Designed through step <N>; <what
the person has confirmed>; <what no reviewer has checked yet>." Always end: "Nothing is built.">. Who uses it and who
it's for: see §1. Project: <[builder] the project and plan, or "none">. Goes next to: <[builder] where this spec goes
when approved, usually "/autoplan", and what travels with it, e.g. "with the design record">. Design record:
<[builder] where the person's verbatim words and any numbered rulings are kept, or "none: this spec is the record">.
Checklists pointed to: the skills checklist (§6). Form: skill spec form v2.

*Example:* Building: the receipt sorter, registered as `/receipt-sorter`, a skill (3 steps) that turns a month of
pasted receipts into one list sorted by category, with a total for each. Status: First fill: drafted from the person's
request; nothing confirmed yet. Nothing is built.

**Words** (pre-filled). Step = a point where the run stops and waits (for the person, a time or a hand-over).
Sub-step = a move inside a step, numbered N.M; everything done in one go without stopping is sub-steps of one step. In
code a step is a "stage". One step = a command; two or more = a skill. The step count decides whether the step-runner
parts apply; the SHAPE (§9) says how it is started and used. The two are separate.

**Which sections each kind fills** (pre-filled). A skill: everything. A command: the cover sheet, §1 (the chain is one
line), §2, §3, §4 (its one step), §5 (may be only `status`), §6 (its own rows), §7, §9, §10, §11 (one row), DECISIONS,
FOR THE PLANNER. A section a kind does not fill keeps one line: "Not applicable: command."

## 1. WHAT THIS SKILL IS FOR

- **Desired outcome:** <[ask] the problem it solves and the result, in the person's terms; write the confirmed
  play-back, quoting the person's own words where they say it best>
- **How the person will know it worked:** <[ask] one or two sentences>
- **The chain:** <[ask] one numbered line per step: its name in caps, then what happens; §4 holds the detail>
- **A run, from the person's chair** (optional): <[builder] three or four sentences: what they type, see and decide in
  one ordinary run>
- **What it is NOT:** <[ask] the nearest things it looks like but isn't, one clause each>
- **Who uses it, and who it's for** (one question, asked once; nowhere else in this form asks it). Pre-filled default
  for who uses it: someone who may be new to this skill and to Lifehack, may be a bit anxious about what is going on,
  and wants none of their time spent on busy work. <[ask] keep the default, or write who it really is; then where it
  is filed: "just for me" (the usual recommendation) → `~/.claude/skills/<name>/` | "for everyone" → inside the
  Lifehack plugin repo, on a branch, offered back as a PR (where-things-live, §6). Repo, branch and push follow the
  routing rule in §6, never this skill. If the person's request already says it, their words are the answer>
- **This skill's role:** <[builder] the stance the AI takes while running this skill: a short role name, then one
  sentence on how it behaves, e.g. "a careful stock-taker: reads back before building on anything". Every step prompt
  opens with it>
- **Over days, weeks, months and years** (optional, one question): <[ask] what changes as it is used; skip if the
  person calls it irrelevant, and write "skipped by the person">
- **What it saves:** <[ask] time, money or stress; say which>
- **What would make the person stop trusting it** (optional): <[ask] their answer; it is also copied into §10>
- **What it must never do:** see §2.

*Example:* Who uses it, and who it's for: the default, and "just for me", in the person's request →
`~/.claude/skills/receipt-sorter/` (D2). This skill's role: a careful bookkeeper: reads every receipt back before
sorting it, and never writes an amount it can't point to [builder's choice].

## 2. THE LOCKED LIST

`L<n> — <what is locked> · <HARD | MOSTLY LOCKED> · <who may change it> · <D-numbers>`

**How to fill it** (pre-filled):
- One row per thing this skill must never do or never lose. Take them from: §1 "What it is NOT" and "stop trusting
  it"; anything the person said with "never" or "always"; anything that touches money, other people, sending,
  deleting or the person's files.
- HARD: only the person changes it, by a new decision. MOSTLY LOCKED: changes with a dated decision. Use HARD for
  anything sent outside, spent, deleted or shown to other people; MOSTLY LOCKED for how the skill works inside. When
  unsure, HARD.
- The last column cites the DECISIONS line(s) that record it. Not yet confirmed: end the row `[inferred]` and cite
  nothing.
- A new statement that contradicts a row: ask which stands; never overwrite.
- **Inherited by every skill, never restated here (pre-filled):** the house style (screens, questions, closing
  line), §4's standard block, and the brief template's fixed blocks (data never instructions, never invent, checked by
  a different model).

<[ask] one row per thing this skill must never do or never lose, beyond the inherited rules>

*Example:* `L1 — Never changes, rounds or invents an amount; every amount shown is one on the confirmed receipt list,
exactly as written · HARD · the person only · D1`

## 3. HOW IT GETS TRIGGERED · THE DOORS

- **What starts it:** <[ask] each trigger and the sub-step it starts, e.g. "the slash command → 1.1", "a hand-over
  from <skill> → <N.M>". A trigger may be a command, a person's request, or a schedule; which one, and how that run
  behaves, is decided when this skill is designed. A hand-over between this skill's own steps is not a trigger>
- **Words that start it:** <[ask] the slash command plus two or three phrases a person would actually say; then one
  near-miss phrase that belongs to another skill, with that skill's name, or "near-miss: none yet (no nearby skill)">
- **Which window** (optional): <[builder] "any window" | "a fresh window, because <why>">
- **A run that outlasts a window** (pre-filled; skills only): picks up through the harness's shared run pickup.
- **Which door:** <[ask] "Door One, a new skill from nothing" | "Door Two, an existing skill rebuilt", then one line
  per thing KEPT from the old skill and one per thing GONE, each written out here as this spec's own line>

*Example:* Words that start it: "/receipt-sorter", "sort my receipts", "where did my money go this month"; near-miss:
"make me a budget" goes to /budget-planner, not here.

## 4. THE STEPS (the ladder)

**Step count:** <[ask] N>. One step → a command: fill one step; §9's step-runner items close. Two or more → a skill.

**The standard block (pre-filled; every sub-step inherits it; never restate it in the ladder)**
- **Moving (skills only).** Only the person typing `/next` or `/back` moves a step; `/back` moves exactly one. No
  plain-speech "next". A step marked OPTIONAL is skipped only by the person's own `/next`, recorded "skipped by the
  person"; if the runner has no optional field, that step opens with one line, "You can skip this: type `/next`." A
  command has no `/next` or `/back`: it runs to its end, and its screen shows no `/next` · `/back` line.
- **Every question** (in every skill and command): asked in the house style's question block, and always carrying
  three things: `*Recommendation:* <what you'd do>` · `*Confidence:* <high | medium | low>` · `*Load-bearing:* <high |
  medium | low>`. Confidence is how sure you are the recommendation is right; load-bearing is how much of the skill
  rests on the answer.
- **Every TALK sub-step:** an edit the person sends with `/next` is made first, then the step moves; an empty or failed
  result is said on screen, never a quiet success; the screen follows the house style. A three-way ⑂ means: more =
  keep discussing, redesign = the person types `/back`, move on = the person types `/next`.
- **Every `→ CODE` set** ends in `none-of-these`, which never moves the run: stay put, ask again `→ LLM (open)`, offer
  the set again.
- **Waiting and stopped.** A missing required input that someone can still supply = waiting: the sub-step does not
  run, launches no helper, writes `waiting: <what> from <where>` to `status`. Something went wrong (a helper ends
  `failed`, an answer is still unreadable after one re-ask) = stopped: nothing after it runs on a guess; it writes
  `stopped: <reason>` to `status`. An ALONE sub-step shows nothing; the next TALK sub-step shows each `status` line in
  one plain sentence.
- **Never stalled on a helper.** On `/next` while a helper runs, the screen moves on at once and says what is still
  finishing (house style). While helpers run, the AI keeps working; it says "wait" only when truly gated.
- **Helpers.** Split one out only when it must be independent of what it checks, reads outside material, or can work
  from one message. Each gets a brief made from `subagent-brief-template.md`. Anything a helper produces that the
  person will see is checked first by a checker: its own ALONE sub-step, right after the work, a different model.
- **Hand-overs.** A hand-over to another skill or window lists every file it relies on, by path. A hand-over that
  proves incomplete: ask up the chain first, saying what is known and not known; ask the person only what the chain
  cannot answer.

**How to fill the ladder** (pre-filled):
1. **Find the steps.** Walk one ordinary run from the trigger to the end. Every place the run must stop for the
   person, for a time, or for a hand-over is the end of a step. No stop at all → one step: a command.
2. **List the sub-steps of each step, in run order.** A sub-step is one move with one purpose: take something in,
   work something out, check it, show it. Write each as one sentence, "<what happens>, so that <why>".
3. **Mark each one.** Does the person see it? → TALK, with a `screen:` line. Otherwise ALONE. Who does it: 🤖 this
   session, ➡️🏃 a sub-agent (add a `helper:` line), or 🙋 the person. Then 💾 / ⚙️ / 🖥 / 🤝.
4. **Wire it.** Every input gets a `⟵` line (from a sub-step, from the person, from the trigger, from last run) and its
   missing case (waits, or stops on a failure). Every output gets a `⟶` line (for a sub-step, outside, for next run).
   Every section named goes in §5.
5. **Check what helpers produce.** Every helper whose work the person will see is followed by a checker sub-step.
   Work done by code that can simply be re-run needs no checker; say so in §7.
6. **Fixed values** (a rate, a time, a limit, a fixed list) are written in the sub-step that uses them. Used in more
   than one place → a row in §6, home "this spec, <N.M>".
7. **Close each step** with ✅ Done when: the felt result, from the person's side.

**The ladder shape** (one header line per step, then its sub-steps):

```
**Step <N> — <NAME IN CAPS>** · step prompt: prompts/step-<N>-<slug>.md (from step-prompt-template.md)<" · LEADER MODE" when the person no longer does the work><" · OPTIONAL" when the person may skip it with /next>
├ <🤖 | ➡️🏃> <💾 | ⚙️> **<N.M>** ALONE — <[builder] one sentence: what happens, so that <purpose>>
│         <⟵ incoming from <N.M>: "<§5 section>"<" (optional)"> | ⟵ from the trigger: <what> | ⟵ incoming from last run: "<section>">
│         <the missing-input case> → waits ("waiting: <what> from <N.M>"); failed → "stopped: <reason>"
│         helper: <name> → brief prompts/subagents/<file>.md (from subagent-brief-template.md) · tier <small|medium|large> · checked by <N.M, or "— (this is the check)">
│         <⟶ for <N.M>: "<§5 section>" | ⟶ outside: <where> (§9) | ⟶ for next run: "<section>">
├ 🙋 🖥 🤝 **<N.M>** TALK — <[ask] one sentence: what the person sees and does, so that <purpose>>
│         screen: <[builder] what the content slot shows, in order; fixed text quoted with its home>
│         <⟵ from the person: "<§5 section>" when they type or paste something here>
│         ⑂ <the question> `→ CODE (<a>|<b>|none-of-these)` · <a> → <N.M> · <b> → <N.M>
├ 🔁 **<N.M>** <what repeats>, so that <purpose>, until <what ends it>
└ ✅ **Done when** <[ask] the felt result>
```

*Example (a skill, step 2 of 3: a TALK line carrying its screen, a sub-agent checker):*
```
**Step 2 — SORT** · step prompt: prompts/step-2-sort.md (from step-prompt-template.md)
├ 🤖 ⚙️ **2.1** ALONE — puts each receipt under one category (groceries · eating out · transport · household · other), copying its amount exactly, so every receipt has one home
│         ⟵ incoming from 1.3: "receipt-list"; no receipt-list → waits ("waiting: receipt list from 1.3"); failed → "stopped: sort failed: <reason>"
│         ⟶ for 2.2: "sort-draft"
├ ➡️🏃 ⚙️ **2.2** ALONE — a separate checker traces every amount in the draft to the receipt list and checks each receipt appears exactly once, so no amount is changed, lost or invented (L1)
│         ⟵ incoming from 2.1: "sort-draft"; ⟵ incoming from 1.3: "receipt-list"; no sort-draft → waits; failed → "stopped: amount check failed: <reason>", the sort withheld
│         helper: amount-checker → brief prompts/subagents/amount-checker.md (from subagent-brief-template.md) · tier medium [builder's choice] · checked by — (this is the check)
│         ⟶ for 2.3: "sort-checked"
├ 🙋 🖥 🤝 **2.3** TALK — the person sees the checked receipts by category and keeps or moves each, so the sort is theirs
│         screen: one block per category, "**<Category>**", then one line per receipt, "<date> · <shop> · <amount>"; then one line, "<N> receipts sorted; none left over."; then the bar's questions
│         ⟵ incoming from 2.2: "sort-checked"; none → shows the status lines, or "waiting: checked sort from 2.2"
│         ⑂ any receipt to move? `→ CODE (move|keep-all|none-of-these)` · move → 2.1 (that receipt only) · keep-all → the person types `/next`
│         ⟶ for 3.1: "sort-final"
└ ✅ **Done when** the person looks at the sorted month and every receipt is where they'd put it
```

*Example (a command's minimal shape, `/receipt-total`):*
```
**Step 1 — ADD UP** · step prompt: the body of SKILL.md (from step-prompt-template.md)
├ 🙋 🖥 🤝 **1.1** TALK — the person pastes the amounts, so there is something to add
│         screen: one line, "Paste the amounts you want added, one per line."
│         ⟵ from the person: "pasted-amounts"; an empty paste → said on screen, asked again
├ 🤖 ⚙️ **1.2** ALONE — code adds the amounts and counts them, so no total is estimated
│         ⟵ incoming from 1.1: "pasted-amounts"; failed → "stopped: sum failed: <reason>"
│         ⟶ for 1.3: "the-total"
├ 🙋 🖥 **1.3** TALK — the person sees the total, so they have their answer
│         screen: "**<total>** from <N> amounts"; then each pasted line that was not an amount, quoted, or nothing
└ ✅ **Done when** the person has one total for the amounts they pasted
```

<[ask]/[builder] the ladder: every step header and every sub-step, in run order, following "How to fill the ladder">

## 5. HANDOFFS AND THE SCRATCHPAD

ONE table for the whole skill. A section not in the table does not exist.

**How to fill it** (pre-filled):
- A section is one named piece of information one sub-step hands to another during a run: what the person typed, a
  draft, a checked result. Name it in two or three lower-case words joined by hyphens.
- What the person types or pastes is a section too, written by the TALK sub-step that receives it.
- Where sections live: for a skill, where the shared step runner keeps a run's working files (§6); for a command, the
  run itself, or the scratch folder (§6, data layout) when something is large. They last one run.
- Anything that must outlast the run (a saved list, something for next run) is not scratchpad: it is a file in §9
  "Files it writes", read back with `⟵ incoming from last run`. Anything sent away is `⟶ outside` and listed in §9.
- A command whose sub-steps hand nothing over keeps only the `status` row.

| section | who writes | who reads |
|---|---|---|
| status | <every ALONE sub-step that can wait or stop> | <every TALK sub-step that shows it> |
| <[builder] one row per section named in §4> | <sub-steps; "the person, at <N.M>" for typed input> | <sub-steps> |

*Example:* `| receipt-paste | the person, at 1.1 | 1.2 |`

**Check both ways before finishing (pre-filled):** every section a sub-step names is in the table with that sub-step;
every row is used by exactly the sub-steps it names.

## 6. ONE HOME PER FACT

Each definition lives in one file; this spec points to it and never repeats it. **When the spec is filed in the
plugin** (pre-filled): no private names, window names or personal paths; every pointer into private notes is replaced
by a plugin-side home.

| definition | one home |
|---|---|
| The house style (every screen, every question) (pre-filled) | `‹at filing: this form's folder›/house-style.md` |
| The step prompt and sub-agent brief templates (pre-filled) | `‹at filing: this form's folder›/step-prompt-template.md`, `…/subagent-brief-template.md` |
| The skills checklist (pre-filled) | plugin `canon/skill-building-sop.md`, its checklist (Build, step 2) |
| The shared step runner, `/next` and `/back` (pre-filled) | plugin `system/parts/stage_runner.py` |
| The skill scaffold (pre-filled) | plugin `system/templates/skill-template/` |
| Model tiers and helper routing (pre-filled) | plugin `canon/helpers-and-model-routing-sop.md` |
| Where durable files go in the brain folder; the scratch folder (pre-filled) | plugin `canon/data-layout.md` |
| Status notes: envelope, location (pre-filled) | plugin `canon/status-emission-sop.md` |
| Checker proof, "wired and seen refusing once" (pre-filled) | plugin `canon/status-health-proof-sop.md` |
| Where a skill is filed, "for me" or "for everyone" (pre-filled) | plugin `canon/manual.md`, "where-things-live" |
| Repo, branch and push routing (pre-filled) | `‹at filing: the plugin's repo and branch routing rule›` (never the skill) |
| This skill's role, who uses it and who it's for (pre-filled) | this spec, §1 |
| <[builder] any other definition used in more than one place, including fixed values> | <its file, or "this spec, <N.M>"> |

## 7. PROOF — HOW WE KNOW IT WORKS

Designed here, RUN in the build. FOR THE PLANNER AND THE BUILD already carries one pre-filled line, "§7's proofs run";
add no more lines for them.

- **A fresh-window run** (pre-filled): one real run in a fresh window not told it is watched; a watcher reads that
  session's records afterwards and checks: <[builder] three to five things the run must visibly do, taken from §1 "how
  the person will know it worked", the HARD rows in §2, and each step's ✅ Done when>.
- **Nothing grades its own work:** <[builder] each checker sub-step and what it checks, "N.M checks N.M"; or "no
  checker: <why>", e.g. "every output is computed by code and re-runnable" or "no helper's work reaches the person">.
- **Planted bad inputs,** each failing first, then passing: <[builder] one per checker (the plant, and the sub-step
  that must catch it); one per §2 row the skill could actually break (the plant, and what must refuse it). A row the
  skill has no way to break gets "L<n>: no plant, no path to break it (<why>)">.
- **The real test** (pre-filled): the skill is built, used by the person in the chair, and they say it is right.

*Example:* Planted: a sort draft that shows the Corner Shop receipt as 12.40 when the receipt list says 12.04 (2.2 must
catch it).

## 8. OPEN — NOT YET DECIDED

`<n>. **<the question>?** Recommendation: <what to do, and when> · Confidence: <high | medium | low> · Load-bearing:
<high | medium | low>.` Never a bare question. A blank from anywhere above that cannot be settled now, or was asked and
not yet answered at hand-off, lands here. **Hygiene (pre-filled):** an item settled leaves this section the same turn
and goes to DECISIONS; a need for a platform or plumbing change goes to ROUTED NOTES as "needs platform change", not
here.

## 9. HOW IT PLUGS INTO LIFEHACK

Every checklist item has exactly one of three homes: always true (below), asked now (below), or FOR THE PLANNER AND
THE BUILD.

**Always true** (pre-filled, by pointer to the skills checklist; never copied):
- One step = a command: the light bar (a sharp description, clean prose); no card, runner or hooks; its step prompt
  is the body of its SKILL.md. Two or more = a skill: a card, the shared runner, `/next` and `/back`, one step prompt
  per step handed over at the START of that step only (never every turn), the inputs line and pause, the start-up
  pickup, the position on the status line.
- Every step prompt opens with who uses it and the role (§1), and describes its own step only. Where a prompt file and
  this spec disagree, the spec wins and the file is fixed.
- Every screen follows the house style.
- Arithmetic by code, never in the model's head (pointer: the skills checklist; not copied here).
- No error that looks like success (pointer: §4, "Every TALK sub-step", the empty-or-failed-result rule).
- No private names when shipped in the plugin.

**Asked now:**
- **Words that start it:** see §3.
- **Where it is filed:** see §1, "Who uses it, and who it's for".
- **Files it writes:** <[ask] every file that outlasts a run, with its path, and who reads it; durable files go where
  the data layout says (§6); or "none: it shows its result and saves nothing">
- **What it sends outside:** <[ask] every `⟶ outside` from §4: where it goes and to whom; or "nothing">
- **Outside connections:** <[ask] "none" | each one (a database, a mail service) and whether it only reads; the skill
  never switches one on itself>
- **Shape:** <[builder] the steps, each one talk or alone (§4), plus the trigger: `command` (the person types it) |
  `schedule` (a schedule starts it). Independent of the step count>
- **Early stop:** <[builder] what happens if the person stops partway: what is saved, what is not sent>

*Example:* Files it writes: one sorted month per file, `<brain>/<the folder the data layout gives>/<year>-<month>.md`,
read by the person [inferred].

## 10. HOW WE KNOW IT KEEPS WORKING

- **The status note** (pre-filled): written by shared code at the end of each run, never by the skill; envelope and
  location by pointer (§6). The payload, below, is the skill's own.
- **What "it worked" means:** <[ask] what a good run leaves behind that code can see (a file written, a send logged,
  a checker receipt); plus the person's §1 answer to "what would make you stop trusting it">
- **The bar's figure while it runs** (skills with a status bar): <[builder] what the figure measures in this skill's
  run, computed by code, e.g. "the share of this step's required answers in place"; or "no figure: the bar line is
  left out">
- **Rhythm:** <[ask] "on demand, no stale timer" | "after <how long> without a run it counts as stale". This line is
  only about when silence means trouble>
- **Checkers inside it** (pre-filled): each writes its own receipt and counts only once seen refusing a planted fault
  (§6, checker proof).

## 11. STEP PROMPTS AND SUB-AGENT BRIEFS

**One home** (pre-filled). The wording lives in the files; this section lists them. A step prompt goes to the AI in
the person's window at the start of a step: one per step, from `step-prompt-template.md` (a command has one, the body
of its SKILL.md). A sub-agent brief goes to a helper that cannot see the conversation: one per helper, from
`subagent-brief-template.md`. The two are never mixed.

**The list** (build it, never write it freehand: copy every step header's `step prompt:` and every `helper:` line from
§4, one row each; a helper used by several sub-steps is one row). The last two columns are what its brief and test
card are filled from:

| file | made from | sub-steps | tier | returns (shape, one example line) | test: one realistic situation · known traps |
|---|---|---|---|---|---|
| `prompts/step-<N>-<slug>.md` | step-prompt-template.md | <N.1–N.x> | (this window) | — | <[builder] a realistic run of this step · two or three ways it goes wrong> |
| `prompts/subagents/<name>.md` | subagent-brief-template.md | <N.M, …> | <[builder] small \| medium \| large> | <[builder] the exact shape, then one example line> | <[builder] a concrete input set · two to four traps, each with the right behaviour> |

*Example:* `prompts/subagents/amount-checker.md` · subagent-brief-template.md · 2.2 · medium [builder's choice] ·
"one line per receipt: `<date> · <shop> · <amount> — traced | NOT TRACED: <why>`" · a receipt list of nine and a draft
that shows one amount as 12.40 where the list says 12.04 and leaves one receipt out · passing an amount that is only
rounded; fixing the amount instead of reporting it.

**How they are made** (pre-filled): each file is drafted from this spec once its step header or helper line is
settled; where a file and this spec disagree, the spec wins and the file is fixed; the build turns them into the
skill's `prompts/` files.

**How they are tested** (pre-filled): each is tested by a fresh, siloed AI given only that file (a brief above its
TEST CARD line) and the realistic situation from the list above; it also lists every place it had to guess; a
different AI grades it against the desired result and the known traps; three tries each; failures are fixed and
retested; step prompts first, then briefs; in small batches, never all at once.

## RESEARCH FOLDED IN

`- **<topic>** (<source file, date, how it was read>): <the finding in two or three sentences>. Consequence for this
spec: <one sentence>.` Depth stays in the design record (cover sheet). Nothing researched → "None."

## DECISIONS

`D<n> · <date> · <the decision, one line> · <source: "the person's words (their request)" | "the person's words" |
"the person's yes" | "builder's choice, not vetoed" | the design record's ruling number>` — every confirmed decision of
THIS skill, one line each, from D1, in the order made, no gaps; "superseded by D<n>" where a later one replaced it,
never deleted. Lines above cite these numbers.

*Example:* `D1 · 2026-11-24 · Every amount shown is one on the confirmed receipt list, exactly as written · the
person's words (their request)`

## ROUTED NOTES

`<n>. <the note> · <where it should go> · <who sends it>` — anything this skill's design surfaced that belongs
elsewhere (another skill, canon, the debt ledger). A need for a platform or plumbing change is marked **needs
platform change** and goes to the coordinator; it never counts against this skill.

## FOR THE PLANNER AND THE BUILD

Build and test items, not design. They do NOT count against the completion figure.

**THE GATE** (pre-filled). Every item below must be closed, or deferred by the person with a reason, as part of the
build's DONE MEANS and as phases of the plan. The skill's component page gets no stamped status until this section is
empty. The technical hand-off note says so, and so does any on-screen readout.

Each line: `- [ ] <the item> · <§ it belongs to> · Drafted: <where a draft answer already exists, or "none">`

**From the skills checklist** (pre-filled; a command keeps the first three, then the last two):
- [ ] Scaffold the skill's folders from the skill scaffold (`prompts/` and `prompts/subagents/` only when it has
  step prompts or helpers beyond its SKILL.md). · §9
- [ ] The frontmatter lines (`skill:`, `shape:`, `description:` quoted, `triggers:`). · §9
- [ ] The routing-eval file beside the skill, each case run three or more times. · §3
- [ ] The card; one prompt file per step, made from §11's list; the inputs-line code and pause for each step. · §11
- [ ] Output checks, each tested on a good, an edge and a padded case, each first seen failing. · §7
- [ ] Scripts fail loudly; every script and helper has a time limit. · §4
- [ ] Stop-hook handover for any ALONE step on the card, or "not applicable: no alone stage" with the reason. · §4
- [ ] Shared parts consumed in place, or pinned by hash with a drift check if the skill travels. · §6
- [ ] Every brief and step prompt tested per §11. · §11
- [ ] All testing rules from the skills checklist. · §7

**From this spec** (pre-filled first three; then the skill's own):
- [ ] §7's proofs run. · §7
- [ ] The bar's figure code, if §10 names one, and the footer phrases' band edges. · §10
- [ ] **The finish-after-build pass:** the plan's FINAL step sharpens and finalizes this spec with everything the build
  discovered (code, JSON, checkers, telemetry), makes it official, and files the skill and its spec per "who it's for"
  (§1). There is no extra stage after the build. · §1
- [ ] <[after build] each item only the build can settle, one line each, in the line shape above>

*Example:* `- [ ] The receipt-reading code's result on a smudged, a two-currency and a duplicate receipt, each first
seen failing · §4 · Drafted: none`

## READY FOR THE PLANNER?

Pre-filled; it informs and never blocks. The final check reports each line as passes / does not, with why.
- **How complete this spec is:** computed by code, never the AI: the share of this form's blanks that are filled AND
  confirmed (`[ask]` lines with no `[inferred]` or `[hypothesis]`, `[builder]` lines filled), each open §8 item counted
  unfilled, FOR THE PLANNER items not counted. A first fill full of `[inferred]` lines is a whole draft with a low
  figure: report it as "drafted, not yet confirmed", not as empty.
- Every blank filled, or listed in §8 with a recommendation; every `[builder's choice]` shown to the person in one
  batch.
- Every "never" is in §2, and every confirmed line cites its D-number.
- Every handoff arrow has both ends, and §5 matches the arrows both ways; every `⟶ outside` is in §9.
- Every step header names its step prompt and every helper line its brief; §11's list matches §4.
- Every section pointer resolves; every `‹at filing›` home is still marked as such.
- Nothing in this form belongs in the design record (no verbatim transcripts, no rework logs, no draft history).
