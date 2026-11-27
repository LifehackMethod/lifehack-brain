---
title: "The Lifehack harness SOP template — how we write canon"
status: approved
approved_by: "Enver on 2026-11-16, round four's 'land it'"
last_reviewed: 2026-11-16
purpose: "The one shape every harness SOP is written in, and the principles for writing canon."
read_when: "Before writing, rewriting or reviewing an SOP."
history: "canon/sop-template.history.md"
---

# The Lifehack harness SOP template — how we write canon

Required sections apply to every SOP; the sections marked [optional] apply only when the SOP has that kind of content (Musts only in a high-altitude document, Open Tensions only for a real conflict of meaning), and one that doesn't apply gets one line, "doesn't apply, because…", never a filled-in section.

## Why this shape

- **The reader.** Every SOP is read by a future AI session with zero context, often opened mid-task. So the sections
  are the same names in the same order in every SOP, and every line must make sense on its own.
- **Industry standard outside, case law inside** — the same hybrid Enver chose for the harness's architecture
  (2026-11-08):
  - The shared core of every procedure standard (EPA QA/G-6, the FDA SOP template, ISPE, SRE runbooks, Diátaxis
    how-to guides): purpose, scope, prerequisites, numbered steps, how to check, what to do when it fails, references,
    revision history.
  - The step format of AI-agent SOPs (AWS Strands Agent SOP): each step carries its own must / should / may lines.
  - What an SOP holds: a desired outcome, principles, and how-to; only a high-altitude document also holds musts.
  - Enver's doctrines: every significant choice carries its why and its change condition; an SOP does not create a must
    on its own (every must traces to his approval); no outranking (tensions stay visible); point, don't paste;
    superseded text goes to an archive; no unexplained shorthand.
- **Family names shared across canon:** Read This First, Pointers, History.
- **Different from an architecture document on purpose:** an SOP is applied practice — action first, steps with
  checks. It has no Stakeholders, Target Architecture or Views sections.

## How to use this template

- Copy everything below the line into the new SOP and fill it in.
- Keep every heading name exactly as written, in this order. (Section IDs are deferred; stable headings let a script
  add them later in one pass, and let canon-files compare SOPs section by section.)
- A section marked *[optional]* that has nothing to say gets one line, "doesn't apply, because…" — never left empty and never filled in.
- Lean: a procedure is "action and only action." Every why, change condition and pointer is one line.
- No banners, no ⭐ or ⛔ markers, no struck-through text, no copied rulings, no inline counts (point to them).
- Numbered lists for steps; short bullets elsewhere.
- should / may appear only inside a step's should / may line; must appears only in a high-altitude document's Musts section; each follows "How we write canon" below.

## How we write canon

Every line here is a principle with its reason, except the three marked **must**, which Enver approved.

**What a document is and where its authority comes from**
- **Location makes canon.** A document in a repo's `canon/` folder is approved; being there is the proof. Inside
  canon a reader leans toward trust, outside it toward doubt. Why: a stateless reader treats every sentence as equally
  true unless told where trust lives.
- **Present tense, as the finished system — must** (approved by Enver, 2026-11-13). Every gap between the text and
  today's code goes on the root debt ledger (`<notes>/debt-ledger.md`), not into the wording. Why: a document
  written as a to-do list goes stale the day the work lands.
- **Open Tensions holds only an unresolved conflict of meaning** waiting for Enver's ruling (approved by Enver,
  2026-11-15). A code gap is not a tension: it goes to the debt ledger. Why: a tension section full of code gaps
  hides the few real questions of meaning.
- **Shipped documents don't point at the maintainer's private documents — must** (approved by Enver,
  2026-11-13). A student who installs the plugin cannot open them.
- **When a ruling changes, rewrite clean and archive the old wording word for word, dated.** No strike-through. Why:
  nothing is lost, and superseded text stops steering a reader.

**The three words: must, should, may** (as RFC 2119 defines them)
- **must** — absolute. It enters only on Enver's direct approval, carries its reason, and (outside `canon/`) carries
  "approved by Enver, <date>". Inside `canon/` the folder is the approval and the history file holds the date.
- **should** — strong intent. It names the reason someone might depart from it.
- **may** — a free choice.
- **Most lines carry none of the three.** They are plain principles with their reasons. Why: the bar for a must is
  extremely high, and a principle worded as a must stops being true.
- **A must enters only on Enver's direct approval — must** (approved by Enver, 2026-11-12). The writer stops and asks
  before writing one; a writer's own idea doesn't become a must.
- **A Musts section belongs only in a high-altitude document** (approved by Enver, 2026-11-15). A working SOP holds
  no musts. Where something must hold, it explains the conformance friction that holds it (the hook or code, by file,
  and how strongly: sign, speed bump, reason gate or hard block, as defined by what the guard does when it fires in `canon/build-conformance-sop.md` §5.11), or, where none is built yet, it lists what should be
  built as a debt-ledger entry. Why: in a stochastic system a line with no code behind it is only a suggestion; in his words, "there can be no rules at the low level ... by the time it gets to the actual implementation, it has been transformed from a rule into code that creates friction" (2026-11-15; the one-line form, "rules exist only as architecture; implementation has no rules, only code", is the approved summary of that ruling).
- **"Law", "never", "always", "rule" and "enforcement" stay out of canon wording,** except inside direct quotes and
  history notes. Why: in a stochastic system there is friction, not enforcement, and those words fool a reader into
  thinking a thing is guaranteed or already done.
- **A check keeps this consistent:** every must outside `canon/` without an approval date, and every should without
  a reason, can be listed by a scan.

**Evidence**
- **Evidence accumulates; nothing outranks.** Enver's approval, outside research, seeing a thing work in our system,
  and a passing test rig are each points toward confidence. A principle's Evidence line names its tier, using
  canon's tiers exactly as `canon/canonical-principles-sop.md` THE FRAME defines them (REPRODUCED · RESEARCHED ·
  OBSERVED · CANDIDATE · REFINED; VALIDATED at the top for a fix). A tier without a dated receipt decays one step.
- **Evidence alone doesn't make a must.** However much a line collects, only Enver's approval turns it into one.
- **No self-written "validated" or "fixed".** A writer's own confidence is a self-report; a claim of proof points to
  the check that proved it.

**Words**
- **Three altitudes in naming:** the plain or metaphor word first, the technical term beside it in brackets, and in an
  SOP the real harness file as the third part. Why: the person learns the real term; the reader finds the real file.
- **Keep the hedge words.** "Intended to be", "usually", a scope, a unit — dropping one turns a true principle into a
  false claim.
- **State the intent; don't prohibit.** No invented limits, no fake precision ("90%", "100%"), no line-count targets.
  Why: limits nobody chose become musts nobody approved.
- **Concise means high value, not short:** the most information in the fewest characters, readable straight through.
- **Write for someone new to the project.** Every term is defined or pointed to.

**Writing for a model reader** (applies to an SOP's steps, a checklist, a skill, any text a model will act on)
- **Give the reason with each line of guidance.** Why: a reader that knows why can handle the case nobody wrote down,
  and a later editor can tell whether the line still earns its place. A line whose reason is lost tends to stay
  forever because nobody dares remove it.
- **Prefer plain, conditional wording to an absolute.** "Ask before deleting a file you did not create" beats "never
  delete files". Name what needs no approval as well as what does. Why: a model takes an absolute literally, applies it
  well past its intent, or argues its way around it. A condition with its exception tells it where the edge is.
- **Keep a binding line for the rare real bright line,** one that code already holds or that the owner has approved
  (the "must" above). Everything else is a principle with its reason. Why: a binding word on a line nothing holds is only a
  suggestion that sounds firmer than it is, and it teaches the reader to discount the lines that do bind.
- **Keep the list short, and prune it when the model changes.** Date each line so it can be reviewed. Why: attention
  thins as instructions pile up, and a caution written for an older model keeps being followed rigidly after the
  problem it guarded against has gone.
- **Check whether the point is already covered before adding it.** Repeating a point from a genuinely new angle is
  fine; restating it in the same words is not. Why: two phrasings of one point can drift apart, and a reader then has to
  guess which one wins.
- **Back what matters with code, not wording.** Where a failure is costly, point to the check or guard that holds it.
  Why: written principles are applied unevenly even by capable models, so a line that has to hold is better held
  by friction in code than by phrasing.

*(Approved by the owner, 2026-11-27; evidence: RESEARCHED, 2026-11-25.)*

## Before you hand it in

Run this on your own draft before anyone reviews it. Each line is a slip that review kept catching in the first SOP written from this template (2026-11-14), or a check added at step 7b (2026-11-15; items 9-11), so catching it here saves a review round.

1. **Banned words:** "law", "never", "always", "rule" and "enforcement" appear only inside direct quotes or history notes.
2. **Nothing private:** no pointer to the maintainer's private documents or notes, and no names of his own desks or
   projects. Shipped documents reach every student.
3. **Musts counted:** each must has Enver's approval, its reason, and, outside `canon/`, "approved by Enver, <date>".
   Anything without his approval is a principle.
4. **Evidence tiers copied from canon:** each Evidence line uses a tier exactly as `canon/canonical-principles-sop.md`
   THE FRAME defines it, with its pointer. Don't invent tiers.
5. **Change if names real evidence:** each "Change if" says what would show the line is wrong, not "Enver rules otherwise".
6. **No inline counts:** keep the claim and its pointer; drop the number.
7. **Problems found in canon go to the debt ledger,** `<notes>/debt-ledger.md`, not into this SOP.
8. **Already decided?** A standing step in the build process checks his past answers before any question reaches him; nothing more to check here.
9. **No Musts at working altitude:** a working SOP has no Musts section. Each thing that must hold is described by the
   friction that holds it (file and strength), or listed as debt to build.
10. **Written as working:** no gap between the text and today's code sits in the wording; each is on the debt ledger.
    Open Tensions, if present, holds only conflicts of meaning.
11. **References (work in progress) is the last section:** every real file, hook, script, tool and data folder the SOP
    points at is listed, and every mechanism the SOP calls for that isn't built yet has a "not built yet" slot.

---

```markdown
---
title: "<SOP name>"
status: draft | approved
approved_by: "<who> on <YYYY-MM-DD>, <where the ruling is recorded>"
last_reviewed: <YYYY-MM-DD>
purpose: "<one line: what this SOP is for>"
read_when: "<one line: the situation that should send a session here>"
history: "<path to this SOP's history/archive file>"
---

# <SOP name>

## Read This First   [required]

- **Purpose:** <one or two plain sentences: what this SOP exists to achieve, and why it matters. Written for an AI
  reading with zero context — this line comes first, before anything else.>
- **Use it when:** <the situations>.
- **Don't use it when:** <the situations that belong somewhere else — point to where>.
- **Covers / doesn't cover:** <scope edges>.
- **How this SOP changes:** only through Enver's ruling; superseded text moves to the archive named in the header.
- **Which situation are you in?** <only if the SOP covers more than one: one line per situation, pointing to its part
  of The Procedure>.

## A complete <thing> has… / Doing <job> right means…   [required]

A suggested order, like a highly recommended order of operations; it adds no musts. Written for a reader with zero context. Each line is one checkable thing and ends with the section that explains it.

> **Words used here**
> - **<term>** — <one-line meaning>.
> - **<term>** — <one-line meaning>.

### 1. Every time…

- <one checkable thing>. → <section>

### 2. In these situations…

- If <situation> → <one checkable thing>. → <section>

### 3. Good practice

- <one checkable thing>. → <section>

— end of checklist —

## Desired Outcome   [required]

- <What "done right" looks like when this is finished.>
- **How to check:** <the concrete check that proves it — a file exists, a test passes, a person confirmed>.

## Before You Start   [optional]

- <Inputs needed, access, tools, anything to read first — each as a pointer.>

## Principles   [optional]

- **<Principle, one line>.** Why: <one line>. Change if: <one line>. Evidence: <tier from canon's
  frame, with a pointer to its receipt>.

## Musts   [optional; high-altitude documents only — a working SOP leaves this section out]

- **<must, one line>.** Why: <one line>. Change if: <one line>. Approved by Enver, <YYYY-MM-DD> (outside
  `canon/`). Held by: <the code check or guard that adds friction, or "prose only">. The ruling's source is recorded
  in this SOP's history file.

## The Procedure   [required]

<If several situations: one sub-heading per situation, `### <Situation name>`, each self-contained.>

1. **Do:** <the action, imperative>.
   - **Why:** <one line>.
   - **Should / may:** <only where the step needs one, per "How we write canon">.
   - **Expect:** <what should happen>.
   - **Check:** <how to confirm it did>.
2. **Do:** ...

## When Something Goes Wrong   [required]

- **If <step N> fails:** <what to do>.
- **To undo:** <how to roll back, or "cannot be undone — stop and ask first">.
- **Stop and ask the person when:** <the conditions>.

## Don't Retry   [optional]

- **<Approach already tried>** — failed because <one line>. Proof: <pointer>.

## Open Tensions   [optional]

- **<Tension, one line: a conflict of meaning, not a code gap>.** Side A protects <...>; side B protects <...>.
  Status: open — surfaced to Enver, not resolved here.

## Pointers   [required]

- **Rulings behind this SOP:** <pointers to shipped rulings or this SOP's history file — not the maintainer's private
  documents>.
- **Evidence:** <pointers to records, test results, receipts>.
- **Words used here:** terms are defined in this SOP, each in one line where first used.

## History   [required]

- <YYYY-MM-DD> — <what changed, one line>. Older wording: <archive pointer>.

## References (work in progress)   [required]

- `<V2-relative path>` — <what it is and does, a few plain words; for conformance friction, its strength>.
- **not built yet:** <what it would do, one line>. Serves: <the high-altitude principle it serves, or "not yet in
  canon">. (The debt-ledger entry points at this line; the shipped SOP carries no ledger number.)
```
