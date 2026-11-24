# House style: how every skill's screen looks

> How every skill's screen looks. Written once; every step prompt points here and never restates it.
> Pre-filled, not described: it shows the shape and tells you what goes inside each blank.

Not skill folders, so there is no file to find:

> ⛔ `/next` is not a skill folder: a command the shared step runner writes when a run starts.

> ⛔ `/back` is not a skill folder: a command the shared step runner writes when a run starts.

> ⛔ `/receipt-sorter` is not a skill folder: a made-up example skill.

> ⛔ `/receipt-total` is not a skill folder: a made-up example command.

## How to use this page

- Copy everything outside `< >` exactly as written: emoji, bold, `---`, backticks, italics, punctuation.
- Each `<…>` is a blank. Replace it, brackets included, with what the words inside it ask for.
- The bar, the figure and the footer phrase come from code. Copy them; never estimate them yourself. Code handed you
  no figure → leave out the whole bar line (the second line of the status bar).
- Pick the screen:
  - **Screen A** on every reply of a skill, unless the step prompt says LEADER MODE.
  - **Screen A, command form** on every reply of a one-step command.
  - **Screen B** on every reply of a step whose prompt says LEADER MODE.
  - **Block C** (optional) goes inside Screen A's content slot, only where a step prompt asks for a walk-through.

## The question block (every question, on every screen, in every skill and command)

````
<n>. **<the question, bold, as a question or a short label>** <only if needed: one sentence of why it matters.>
   *Recommendation:* <what you would do, one or two sentences> · *Confidence:* <high | medium | low> · *Load-bearing:* <high | medium | low>
````

- **Recommendation:** what you would choose, said plainly, so the person can just say "yes".
- **Confidence:** how sure you are the recommendation is right. high = the evidence points one way; medium = a fair
  guess; low = little to go on.
- **Load-bearing:** how much of the skill rests on the answer. high = it changes how the skill works, or is hard to
  undo later; medium = it changes one part; low = easy to change any time.
- All three are always there. Never leave one out, never replace them with a bare guess.

## Screen A — the normal screen (the person is doing the work)

````
# <the skill's one emoji, the same on every screen> <the skill's name in Title Case, as on the spec's cover sheet>

**You're on step <N> of <total>: <the step's name, lower case>.** <ONE sentence, under 25 words: what is happening right now, and what the person does, if anything.>

<CONTENT SLOT: what this step's prompt says to show on this screen. Short paragraphs. Plain words. Every sentence names who does what ("I…", "you…", "a helper…"). No tables. At most one bold phrase per paragraph. Numbered lists where order matters.>

---

**<the same emoji> <the skill's name in sentence case>** · Step <N> of <total>: <the step's name><only when it helps: " (<where in the step, a few words, e.g. last batch · running>)">
<the bar from code> <the figure from code>% · *<the footer phrase from code>*

1. **<the question>** <only if needed: one sentence of why it matters.>
   *Recommendation:* <what you would do> · *Confidence:* <high | medium | low> · *Load-bearing:* <high | medium | low>
2. **<next question>**
   *Recommendation:* <…> · *Confidence:* <…> · *Load-bearing:* <…>
<at most four, most leveraged first; delete unused numbers; no question this turn → delete the whole numbered list>

Keep discussing this round, or ready to move on? `/next` · `/back`
````

## Screen A, command form (a one-step command)

A command has no steps to move between and no `/next` or `/back`, so it has no step line, no step in the bar, and no
`/next` · `/back` closing line. It ends with its result, or with its one question.

````
# <the command's emoji> <the command's name in Title Case>

<ONE sentence, under 25 words: what is happening right now, and what the person does, if anything.>

<CONTENT SLOT: as in Screen A.>

---

**<the same emoji> <the command's name in sentence case>**
<only when code gives a figure: "<the bar from code> <the figure from code>% · *<the footer phrase from code>*">

<only when a question is really open, in the question block: "1. **<the question>**" then its line "*Recommendation:* <…> · *Confidence:* <…> · *Load-bearing:* <…>"; otherwise delete this line>
````

**The footer phrases** (code hands you one; copy it exactly, italic):
- `*not ready to move on*` — important parts are still undecided; most of it is unfilled.
- `*wouldn't recommend moving on yet*` — mostly filled, with some gaps.
- `*probably okay to move on*` — about 90% and up.

They inform and never insist; nothing waits on them. They say "move on" to match the closing line; the owner's spoken
words were "proceed", and the owner may switch both.

**The question rules** (fixed):
- At most four, most leveraged first. More only where the step prompt names an exception.
- Every question is in the question block, with its recommendation, confidence and load-bearing.
- Never ask what could be looked up, or what the person has already said (their first request included). Never ask
  the person to do your thinking, or to choose between things they don't understand.
- Never a question that is not really open. The questions live in the bar only; never repeat them above it.

**Fixed lines for special moments** (copy, fill the blanks):
- Still finishing when the person types `/next`: "<the helper's job, in plain words> is still finishing in the
  background. Nothing is lost; you'll see the result <where, e.g. at the top of the next screen>."
- Truly gated on a helper: "I'm waiting on <what, in plain words> before I can go on. You don't need to do anything."
- Nothing to report: "<Nothing found, in the step's terms>. I checked <what was checked>."
- Failed: "<What> didn't work: <the reason, in plain words>. Nothing was saved as done. <What happens next>."

## Screen B — LEADER MODE (the person is no longer doing the work)

No numbered question list. The closing line takes its leader form. Use it only where the step prompt says LEADER MODE.

````
# <the skill's emoji> <the skill's name in Title Case>

**You're on step <N> of <total>: <the step's name, lower case>.** <ONE sentence: where they are, e.g. "You've done the hard part. Here's what happens from here.">

**What you've made:** <one or two sentences: what exists now, and plainly what does NOT exist yet.>

**What happens next:**
1. **<who acts, bold: "I…", "The planner…">** <what happens, one sentence.>
2. **<who acts>** <what happens.>
<two to four items, in time order; directionally accurate, never prescriptive>

**What you do now:** <exactly what to type or open, one or two sentences.>

<ONLY when a question is really still open and the step prompt names it: one line, "<the question>?", then its line "*Recommendation:* <…> · *Confidence:* <…> · *Load-bearing:* <…>". Otherwise delete this line.>

---

**<the same emoji> <the skill's name in sentence case>** · Step <N> of <total>: <the step's name>
<the bar from code> <the figure from code>% · *<the footer phrase from code>*

Type `/next` to <what /next does here, a few words, e.g. hand it over>, or `/back` if you want to change something.
````

## Block C (optional) — a walk-through

Use it only where a step prompt asks for one: several items (usually a skill's steps) shown two to a screen, each with
the same labelled sections, so the person sees what will happen before it does. It goes in Screen A's content slot.

**The overview screen, shown ONCE** (never again on returning to the walk-through):

````
<one sentence the step prompt gives, e.g. "From what you told me, it looks like this breaks into <N> steps:">

1. **<item name>** — <one line: what happens in it>
2. **<item name>** — <one line>
<one line per item>

Next, I walk you through them two at a time.
````

**Every walk-through screen**, two items per screen. The key line goes on the first walk-through screen only. Each
emoji is always shown with its label (the Lifehack emoji key, the same marks as the spec's ladder). Every section
shows; when a section has nothing, write the line the step prompt gives for that case (a question to the person, or
"None in this step.").

````
**Key:** 🙋 You · 🤖 This session · ➡️🏃 Sub-agent (a separate AI working on its own) · 🌙 Earlier machinery (anything that exists before the skill runs)

**<Item n>: <item name>**

🤖 **This session:** <prose, three to six sentences: what the AI in this window does, in order. Long enough to give a clear sense of everything that will happen; a one-liner is too short.>

🙋 **Your part:** <prose, two to four sentences: what the person sees, says and decides; end with how they finish it.>

➡️🏃 **Sub-agents:** <prose: what helpers do quietly in the background, and that a separate one checks before anything is shown.>

🌙 **Earlier machinery:** <what already exists before this runs: tools, saved files, earlier skills.>

**<Item n+1>: <item name>**
<the same four sections>
````

Then the bar's questions, each in the question block: as many under each walked item as the step prompt names. The
last walk-through screen ends with the step prompt's closing sentence, if it gives one.

## The filled example (/receipt-sorter, step 2 of 3, after the amount checker has passed the sort)

An illustration only: each real screen is filled from that skill's own step prompt.

````
# 🧾 Receipt Sorter

**You're on step 2 of 3: sort.** I've sorted your nine receipts into categories; you keep or move each one.

Here's the month, every amount exactly as on your receipts:

**Groceries**
1. 3 Nov · Green Market · 42.10
2. 12 Nov · Corner Shop · 12.04
3. 17 Nov · Green Market · 38.75

**Eating out**
4. 14 Nov · Noodle Bar · 31.80
5. 28 Nov · Noodle Bar · 26.40

**Transport**
6. 5 Nov · City Cabs · 18.00
7. 9 Nov · City Cabs · 23.50

**Household**
8. 20 Nov · Hardware Plus · 27.99
9. 22 Nov · Pharmacy · 9.60

Nine receipts sorted; none left over.

---

**🧾 Receipt sorter** · Step 2 of 3: Sort
▰▰▰▰▰▰▰▱▱▱ 70% · *wouldn't recommend moving on yet*

1. **Does the pharmacy receipt belong under household?** It's the only one that could fit two places.
   *Recommendation:* keep it under household, since the receipt shows soap and batteries. · *Confidence:* medium · *Load-bearing:* low
2. **Was the 9 Nov cab for work?** A work trip would come out of this month's personal totals.
   *Recommendation:* leave it under transport until you say otherwise. · *Confidence:* low · *Load-bearing:* medium

Keep discussing this round, or ready to move on? `/next` · `/back`
````
