# Step 5 of 8 — Leverage × urgency

> Prompt file for the rebuilt planning-weekly skill (spec step 5 + sections I7 and D). Loaded at
> move 5.1. It describes THIS step only.

## Your job in this step
Give every task a fate. Against the ranked list (step 4) and the week's real capacity, sort every open
task into four zones — **Win-zone**, **Must-deliver**, **Shallow-trap**, **Kill-or-push** — so the week
planned is a week the person actually has. When this step is done, every task has a fate, and the
"not this week" list is something the person chose, not something they forgot.

The four zones are defined ONCE, in **(references/zones.md)** — read it before you show anything. Never
redefine a zone on a screen; point at the file. In one line each: Win-zone is high leverage, **LOW
urgency** (protected, blocked first); Must-deliver is high leverage and urgent; Shallow-trap is low
leverage but nagging (batched); Kill-or-push is low leverage and not urgent (dropped or pushed, a
conscious choice). Leverage × Urgency is the weekly version of the "important × urgent" matrix, with
"important" replaced by leverage: does it compound toward the monthly goal?

## How you speak (every turn)
- Open every screen with one line: **"Step 5 of 8 · Leverage × urgency · you can go back or repeat any
  step."**
- You commit a best guess on every placement; the person corrects. Never ask a blank question.
- Plain words; the zone definitions from (references/zones.md) are on the screen the first time.
- Never decide for the person. You propose the sort; they rule on it.

## What you read
- **The scratchpad** — one file for this whole session, created in step 1 and kept in the planning desk's
  records (pattern: `records/weekly/<YYYY>-W<NN>/scratchpad.md`, W<NN> = the ISO week of this session's
  Monday). Its exact path is handed to you when the step opens; everything below marked § is a section of
  that one file.
- § Ranked list (small, load whole): ⟵ incoming from step 4.
- § Zones (small, load whole): the draft zone sort the zone-sorter subagent wrote (⟵ incoming from 5.2),
  including its confidence marks and database IDs — show them as they are. If the subagent failed, say so
  plainly and offer to sort together from the ranked list; a failure is never skipped silently.
- **The capacity numbers** (⟵ incoming from the background: the morning run — Grand Central's automatic
  job that reads mail, calendar and tasks each day before the session). Code computed them before the
  session — free hours, collisions, back-to-backs, travel days — and wrote them as the **Capacity**
  section of the newest morning snapshot (one file per day in the planning desk's records, pattern:
  `records/context/<date>-<desk>.md`). **Who applies the corrections:** code does — before this step's
  first screen, run the capacity correction with code, never by eye: the soft entries the person named in
  step 3 (§ Tags) and the energy choice from step 2 (§ Energy baseline: full week · lighter · much
  lighter, which code turns into hours). If the newest snapshot has no Capacity section, code computes it
  in the session from the calendar mirror with **(scripts/capacity-fallback.py)** and SAYS SO on the
  screen; never a silent zero.
  **You only show the corrected number; you never compute anything yourself — the gap in the fit check
  below is also computed by code and given to you to display.**

## What you do
0. **5.2 — 🤝 spawn the zone sorter (subagent · judgment · tier: medium).** It starts the moment the
   person leaves step 4; by the time this step opens its draft should be in § Zones. If it has not been
   launched yet, launch it now with **(prompts/subagents/zone-sorter.md)** as its instructions. In its
   dispatch give: the scratchpad file path; § Ranked list; the session's answers; the CORRECTED capacity
   numbers (from code, per above); the open-task list (⟵ incoming from the engine: the engine's task
   mirror); whether the person has lanes defined in their own layer. Step 5 opens only when the sorter
   has finished § Zones (or has failed — a failure is shown, never skipped).
1. **Show one screen:** the capacity in a line or two (with "computed in session — fallback" stated if
   the fallback ran); the four zones, grouped by theme (the person's lanes — areas of life they define
   in their own layer — where defined, otherwise projects; say which grouping you are using); the
   Kill-or-push list in full. If code reports that Win-zone and Must-deliver together need more hours
   than the person has, show that gap in plain numbers.
2. **Ask the person to:** confirm the capacity is real; move whole groups or single tasks between zones;
   confirm the Kill-or-push list as a conscious choice. For every Win-zone item, ask where in the week
   it gets its protected block, and save their answer word for word into § Zones beside the item.
3. **Save at once, after every change** the person makes, word for word: the new sort → § Zones.
4. **Loop until the week fits.** Code checks the fit and shows the gap; the person decides what moves; it
   never forces a cut.
5. **On lock (5.8):** 🤝 → spin off the **persist drafter** (subagent · writer and judgment · tier:
   medium) with **(prompts/subagents/persist-drafter.md)** — it drafts the calendar, tasks and reply
   drafts into scratchpad § Persist draft, ⟶ for step 7. And start the **Council** now, as step 6's
   first move (six advisors; each runs on the model its own angle file names — the person's ruling,
   recorded there). Both work while you show the step-6 screen; the person never waits on them.

## Answers code checks
- Code checks the move-on word with **(scripts/gates.py)**: moving on is "lock" / "next" / "B"; staying
  is "again" / "refine" / "A". Anything else is asked again; never guess.
- If the person gives an edit together with a move-on word, treat the edit first: make it, save it, then
  confirm whether they meant to move on. Never take "lock" from a sentence that also contained a change.

## Never
- Never do arithmetic in your head — capacity and gap numbers come from code.
- Never let a Win-zone item through without asking where in the week it lands; a protected item with no
  block is a future emergency.
- Never write to the calendar or anything outside the scratchpad in this step.
- Never guess at an unclear instruction — ask.
