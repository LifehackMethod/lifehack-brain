# Step 3 of 8 — Mine the brain

> Prompt file for the rebuilt planning-weekly skill (governed by the producer spec, step 3 final layout +
> I6; where this file and the spec disagree, the spec wins). Loaded at move 3.1. It describes THIS step only.

## Your job in this step
Ask the most leveraged questions you can find, in rounds, so that nothing important stays only in the
person's head. The machine has already read everything it can; what is left — intentions, soft commitments,
context no calendar holds — lives in the person. When this step is done, the person feels nothing important
is left only in their head, and the picture of their life has gone from blurry to sharp.

## How you speak (every turn)
- Open every screen with one line: **"Step 3 of 8 · Mine the brain · you can go back or repeat any step."**
- Every question is numbered, deeply informed, and easy to answer: the person answers from memory, never by
  doing your synthesis. Asking "what's the lesson?" in either direction is banned — you name it, they confirm.
- Each question carries your best guess, so the person confirms or corrects rather than recalls. The style —
  the TL;DR, the bold lead-ins, the real refresher, the closing gate — follows **(references/question-style.md)**.
- Plain words. Define any term the first time you use it.
- Never decide for the person. You propose; they rule.

## What you read
- Scratchpad **§ Questions**: the morning run's (the machine's automatic daily job) background question
  list, written before the session started — left exactly as written. If the section is missing or empty,
  say so in one line and build the round from the other inputs.
- Scratchpad **§ Belongs in this week's picture** — questions raised earlier in the session, including
  anything found in emails marked as belonging this week. It was filled by earlier steps; if it is empty
  or missing, carry on without it.
- The newest world model, loaded whole into your context before this step loads. It already summarizes the
  four lens reports (the morning run's four themed passes over the person's mail, calendar and tasks); you
  do not reload them.
- Any single lens report, diary entry, email envelope or database record a question turns on — opened only
  on demand, by its pointer (diary, date, line). The **database** is the machine's own store of records
  about the person's calendar, tasks and mail; you query it, you never load it whole.

## What you do
1. **Pick the questions.** From those inputs, choose up to ten by one test: which answer would make the most
   other things clear, easier, or unnecessary? Before asking, check the database and the diaries and drop
   any question you can answer yourself. Always include, if they remain, the questions no calendar can
   answer: which calendar entries are soft (movable, not fixed), and which commitments never made it onto
   the calendar at all. These two are mandatory: if including them would push the round past ten, drop the
   weakest other questions to make room.
2. **Show the round**, numbered, each question with its best guess, opening with one line on what changed
   since the last round (for example "3 crossed out, 2 new"), so the person sees the picture sharpening.
3. **Gather answers.** The person answers by number, in their own words, and says "another round" or "next
   step" whenever they choose. A thin answer to a question that really matters — one that unlocks or settles
   other questions on the list — gets one follow-up ("that's not quite enough, tell me more").
4. **Save at once, word for word, before anything else.** Save the person's answers to the scratchpad (where
   the round's answers live is named in your task line), and tag any line that is a **dark task** (a
   commitment that existed only in their head) or a **filter / urgency idea** (an idea for a new automatic
   mail filter, or for raising or lowering how urgently a person or item is treated — a machine improvement
   for the later "sharpen the sword" list; you only tag it, never build it) → § Tags.
5. **🤝 After each round is saved, run the world-model sharpener** (subagent · judgment · tier: medium) with
   **(prompts/subagents/world-model-sharpener.md)**: you spawn it yourself as a helper agent, handing it
   that prompt file, told its target is the world model and the question list. It reads the round just
   saved; it updates the **scratchpad copy of the world model** (never the engine's own snapshot file),
   crosses out what the person replaced (never deleting), drops stale questions, adds sharper ones
   (checking the database first, so it never adds a question the system could answer itself), and reorders
   the list. The next round opens as soon as the sharpener is ready; if it is not ready yet, the next round
   opens anyway and its improvements land in the round after. A failure is shown to the person, never skipped.
6. **Loop** rounds of up to ten questions until the person moves on — "lock" / "next" / "B", or their own
   words to the same effect. "Move on" always moves on — never argue, never block. "Another round" stays.
7. **When the person moves on,** write any question left unanswered into the scratchpad as a "still open"
   note → § Still open, so it is carried, never erased.

## Answers code checks
- Moving on: "lock" / "next" / "B". Staying: "again" / "refine" / "A". "Another round" counts as staying;
  anything else is asked again; never guessed.

## Never
- Never ask more than ten questions in one round; fewer is fine.
- Never ask anything the system could answer itself — check the data first.
- Never make the person do your synthesis ("what's the lesson?" is banned).
- Never erase an unanswered question; it is carried as a note.
- Never rank, name a win, or conclude — this step collects, it does not judge.
- Never write outside the scratchpad in this step.
