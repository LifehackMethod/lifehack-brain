> This component-page template is adapted from the arc42 architecture documentation template (https://arc42.org) by
> Gernot Starke and Peter Hruschka, licensed under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/).
> Changes: it reuses the section-5 building-block (blackbox) fields as a standalone per-component page, with added
> intent, generated as-built, and stamped status sections. This adapted template is itself licensed under CC BY-SA
> 4.0, provided as is without warranty. The arc42 authors do not endorse this adaptation.

# Spec-component template (rebuilt 2026-11-21 from both originals, nothing dropped)

Which sections apply depends on the kind of thing: friction per act only if the system guards actions, boundaries only if it holds anything sensitive, first principles only when the subject has them, and the person's workflow always (one line if the person never touches it); a section that doesn't apply gets one line, "doesn't apply, because…", never a filled-in section.

> **One document, two states.** It starts as a SPEC, while something new is designed, and FLIPS to a COMPONENT page once
> it is built and hooked into the system (the last step of every plan). A spec is a component page that hasn't been
> born yet. It follows the C4 pyramid (round five, 2026-11-16): the map, then the manual, then one component page per
> part, then the code.
>
> **What this is.** A template for writing a specification document: the step upstream of the plan. It merges the
> earlier spec template (2026-11-21) with the component page template (approved 2026-11-16), nothing dropped.
>
> **Principles, not rules.** Every heading below earns its place in most specs; leave out what a subject doesn't need, and
> say so in one line. A section is never padded to fill the shape.
>
> This template is a highly recommended starting point, not a form: a page may add sections, depart from this layout, and run as long as it needs to — there is no length limit. What stays firm is the mechanism: intent as pointers to canon, the generated as-built block, the stamped status block, and the shared-ownership pointer pattern.

---

## Part A — how a spec gets made (the process around the document)

1. **First principles first, when the subject has them** (encouraged). Example: a desk's spec can hang from its own
   first-principles document and cite it section by section.
2. **Research, then a diagnosis** (the `/architect` skill): what is actually broken, and is there one root cause.
3. **Solve the right problem.** State the problem in the person's words, and say what it is NOT. (GitHub one door was first built
   for secrecy; the person's problem was seeing where work goes: "we're not the CIA.")
4. **Write the spec in the present tense, about the working future.** It never treats today's system as the truth or
   compares itself to past builds: "Don't make the mistake of assuming that what we built before was ever working."
5. **Check it against canon:** one reader per important rulebook, with the reading proven by code.
6. **The person's rulings,** on the clashes only. Nothing is folded in before they rule. Check their past answers first.
7. **Rewrite by the person's method:** write the new draft in a temp file → compare line by line with the current one → restore
   anything lost → merge. The old draft is kept beside it (`spec-DRAFT-vN-<date>.md`).
8. **A blind fresh-eyes read,** plus, where the spec guards against something, a blind attack on the person's #1 priority. The blind
   reader is always asked: "Could you build this from the Ground section alone? List everything you would have to guess."
   Every guess is a gap to fill before the plan.
9. **Then the plan,** worked backwards from the spec. The spec's "to prove" items become the plan's first phase.
10. **The flip** (the last step of every plan): the state line changes from `spec` to `component` only when every "to prove"
    item has a real check and the file list generates cleanly. Code can verify it, so it can't be faked. Plugin parts then
    live in `canon/components/`.
11. **Changing a part that already has a component page:** a change spec uses this same template, and at the flip it merges
    into the existing page rather than replacing it.

---

## Part B — the document

**Fill in every section; the HTML comment on each says who writes it. The fenced blocks are written by the generator and the stamper — leave them empty and untouched; a hand edit inside a fence is overwritten and reported.**
**While a spec:** sections marked *(born)* hold one line, "fills when built", and are **filled by code, never typed**.

```markdown
---
component: <slug>            # the triage slug (§8 of the definition)
title: "<the approved name, exactly>"
# while a spec, the title may read: title: "<Name> — Specification"
state: spec | component        # spec while designed; component after the flip
id: <slug>-spec-<date>
record_type: design-spec
desk: <desk or root>
created_at: <date>
status: DRAFT <n> — <what is ruled / nothing ruled>
parent: <first-principles document, if any>
also_follows: <canon this applies, e.g. the V2 Architecture Vision, View 1 "The Division of Labor">
source: origin/V2            # where as-built is read (for a private part: the repo it lives in)
scope:                       # human: what belongs here; the generator expands it
  - <repo path or glob>      # one entry per file the component is
shared:                      # §6 of the definition; only if a file is homed elsewhere
  - {paths: [<path>], home: false, role_here: friction|check|data, file_home: <other slug>}
checks:                      # what "working" means, per check id; the register carries the checks at run time
  - {id: <register id>, watches: "<the canon outcome, in one clause>"}
receipts:
  - <brain>/status/component-<slug>.json
health: []
---
# <Title>
<!-- roll-up, generated: <LABEL> · checked <date> · valid until <date> · <receipt> · Health · as-built sha · last reading -->
```
*(The `scope`, `shared`, `checks`, `receipts` and `health` keys may stay empty while a spec; the roll-up line is born.)*

## How to read this
- Present tense, written from the future: it describes the finished system as if it were running.
- **The three altitudes, as the person defines them (2026-11-21):**
  - **10,000 ft:** "what is it meant to do, how is it meant to work within our system."
  - **5,000 ft:** "detailing the actual pieces, tools, subsystems that work together along with the human in the loop
    and what the human is expected to do."
  - **Ground:** "a very specific detailing of all the technical information. In massive detail."
  - And through all three: "the code, the LLM, and the human are always interplaying so it's not leaving out what the
    human is meant to do in the system."
- **Marks on every Ground item:** **BUILT** exists at this path today · **CHANGES** exists, and this spec changes it ·
  **NEW** doesn't exist yet; the name and path are proposed. **Marks on every mechanism claim:** **[tested]** (with the
  record) or **[to prove]**. In a spec, a BUILT item is one that exists today and is reused as is; it is kept so nothing the
  plan needs is lost (approved 2026-11-21, from converting a finance desk's spec).
- **Conventions:** the roots (`<code>`, `<notes>`, `<harness>`, …) and how each is found; an everyday name first, then the
  industry term in brackets, then the exact file, table or command.
- **Numbers that are the person's to set** are named as theirs and never invented here: no thresholds, odds or targets of the
  spec's own.
- **Written so a blind window with no memory can rehydrate from it.** Wherever this uses a metaphor or everyday words, the
  exact technical thing goes beside it: the real file, table, tool or term.

## Words used
Every term a stranger wouldn't know, one line each. (a finance desk's "driver lights", GitHub's "the check inside git".)

## ▲ 10,000 ft — what it is meant to do, and how it works within our system
### Purpose/Responsibility <!-- human: one plain sentence (the approved purpose) + pointers up to canon; no restatement, no rule -->
*While a spec: items 1–9 below are the purpose, in full. As a component: one plain sentence of purpose plus pointers up to canon, with items 1–9 kept beneath it.*
1. **Desired outcome:** what the person gets, in one or two sentences, in their words where possible.
2. **The problem it solves, in the person's words, and what it is not.**
3. **What matters most, in order** (when there's a trade-off). GitHub: right repo first, right branch second, tidiness
   after. A finance desk: the two dangers side by side, neither outranking the other.
4. **Where it sits in our system:** what it reads from and feeds, which desks or windows use it, what stays outside it.
5. **The three intelligences, at a glance:** what code does, what the AI does, what the person does, in one line each.
6. **How it runs without the person:** what happens unattended, what "couldn't tell" or "no outcome" means, what is safe when
   the person is away.
7. **How the person works with it:** each way, in rising cost of their attention (a glance → an alert → a sitting → a review →
   their hands). **What only the person does, and what they never do.**
8. **Principles it holds** (if it has its own), each with its reason.
9. **How it generalizes:** why any person, or any desk they could think of, would want it; what changes from person to
   person (their data, their choices) and what stays the same (the shared code).

## ▲ 5,000 ft — the pieces, how they work together, and what the human does
1. **The combinations used** (the Vision's View 1): code only · Code+ (code with one sealed AI step that picks from a
   closed menu, always including "couldn't tell") · all three (a session) · human + code · human alone. A short table:
   where this system uses each.
2. **The seams.** In practice code handing to the AI works very well, and the AI handing to code works less well; name
   each place the AI hands something back to code, and keep it small (a menu pick, an id, a quote code can re-find).
3. **The chain:** one diagram of how things flow, each stage tagged with its combination.
4. **The parts:** a table — part · what it is · why it exists · who is in the room · what it connects to.
5. **The three seats:** a table — code / AI / the person · does · never does.
6. **When the person is called:** a table — what arrives · what it asks of them · how much of their time.
7. **One thing walked start to finish** (a decision, a save, a morning), through every seat.
8. **Friction per act,** if the system guards actions: each act and its level on the build conformance SOP §5.11 ladder
   (sign, speed bump, reason gate, door, human hands, hard block), lightest first.
9. **Boundaries,** if it holds anything sensitive: what crosses each one, and what never does.
10. **How it fails:** what each part does when it breaks, and that a failure is shown (grey, "couldn't tell"), never
    shown as fine.

### The person's workflow <!-- human: required in every spec, even when the answer is "none" -->
*There are always three elements: the code, the AI and the person. This section is the person's side, from their point of
view: what they are expected to do, step by step, and how they find their way around this new piece of machinery (where
they see it, what they say or click, what they get back). Code and the AI may do a great deal in the background without
them, in any combination; this section says where the person comes in. If this part never touches the person, say so in
one line and why (the person, 2026-11-21: "it always leaves out the human part … we need to understand … what the human is
expected to do in this system and how the human is meant to navigate this new piece of machinery").*

### Interface(s) <!-- human: each seam to another component — what crosses, which way, the carrying file, the other page -->
*While a spec: each seam being designed to another part (items 3 and 4 name them). As a component: each seam, what crosses, which way, the carrying file, the other page.*
### Inside (whitebox) <!-- human -->
<!-- overview diagram (text or Mermaid) · motivation for the decomposition · each part as a mini-blackbox: responsibility + scope -->
*While a spec: the chain (item 3) and the parts table (item 4) are the whitebox. As a component: the overview diagram, why it splits this way, and each part's responsibility and scope.*
### Quality-/Performance characteristics <!-- human: what "working" means per check id, each pointed at canon's desired outcome -->
*While a spec: what "working" will mean (item 10 and the "to prove" list). As a component: one line per check id, each pointed at canon's desired outcome.*

## ▲ Ground — the full specification, in massive detail
**What this section is (the person, 2026-11-21):** the complete map of the working future system: every file, every function,
every format, and every interaction between them, by real path. Nothing technical lives anywhere else. A builder with no
memory could build the whole thing from this section alone.
- **G0 Roots, conventions and the shared tools it uses** (used from the shared layer, never copied; check
  `system/register/toolbox.md`).
- **G1 … Gn: one section per part, in the 5,000 ft table's order.** Each holds:
  - every file, function, table, job, hook and setting by its real path, with its mark (BUILT / CHANGES / NEW), checked
    against disk on a stated date;
  - the exact formats (fields, columns, menus, file layouts);
  - **who does what, attended and unattended** (code only / Code+ / all three / the person's hands);
  - **fragile seams** named where they are, with the guard that holds them;
  - repo, branch and who pushes, for anything in a repo.
- **What exists today that this reuses:** what is reused, from where. (Not a comparison with past builds; see the open
  question at the end.)
- **Invariants:** the statements that must always be true, numbered, each checkable.
- **Tests:** each finish test shown failing first on a planted case; attacks run by someone who didn't build it; tests on
  synthetic data or scratch copies, never live data.

**Ground completeness check** (tick each before the spec is called done; anything unticked is a gap, not a style choice):
- [ ] every part in the 5,000 ft parts table has its own Ground section;
- [ ] every interface listed under Interface(s) shows its exact call: which file calls which, with what, and what comes back;
- [ ] every command a person or a session runs is named, with its arguments;
- [ ] every file the system reads or writes has its format spelled out (fields, headings, line shapes);
- [ ] every NEW or CHANGES item has a real path;
- [ ] nothing says "to be decided", "TBD" or "later" without a pointer to where it is decided.

### Directory/file location <!-- human: one line of scope meaning; the generator writes the block -->
*(born)* fills when built.
<!-- AS-BUILT:BEGIN generator=<path> source=origin/<branch>@<sha> fetched=<time> sha256=<hash of body> -->
<!-- AS-BUILT:END -->

## What is tested and what is still to prove
Numbered. Each "to prove" item becomes a step in the plan's first phase. At the flip, each "to prove" item becomes a status
check below.

### Status <!-- checker → stamper; the suffix line is human-owned, outside the fence -->
*(born)* fills when built: the status label is stamped by a real check, never typed.
Suffix (human-owned): ·gap
<!-- STATUS:BEGIN stamper=<path> stamped=<time> sha256=<hash> -->
<!-- STATUS:END -->

## Decisions (the person's)
Numbered, each with their words and the date. Nothing is credited to them without their quoted words.

### Fulfilled requirements <!-- human: canon lines this component fulfils, including the SOP's "not built yet" slots -->
*While a spec: the person's decisions above are the requirements. As a component: the canon lines this part fulfils, from those decisions.*

## Open decisions
Each with the best guess the draft is written to, and the other way.

### Open issues/problems/risks <!-- DELTA -->
#### Known <!-- human: pointers only — debt-ledger lines, canon Open Tensions, the appeals; no restatement -->
#### Delta reading (AI, dated) <!-- an AI reader with judgment; names its inputs; never edits the blocks or canon -->
*While a spec: the open decisions above are the open issues. As a component: Known pointers, plus the dated AI reading of the drift.*

## Out of scope
Each item with who ruled it out, and when.

## Rulebook updates this creates
They go to the debt ledger §10 list, never into canon directly.

## Shared ownership <!-- human, in words; the generator verifies the files -->
*While a spec: name any file another part owns. As a component: pointer entries, verified by the generator.*

## Pointed at by <!-- generator: SOPs whose References name this page -->
*(born)* fills when built.

---

## Open question for the person (from the GitHub one door window)

A finance desk's spec ends with "Kept, changed and dropped from the old specs, and why". For GitHub one door the person ruled the opposite:
nothing built before is assumed to have worked, so that spec carries a "what exists today that this reuses" list
instead. This draft follows the GitHub ruling in general, and keeps the "why it changed" story in the rewrite's change
report beside the spec (as Grand Central's rewrite did), not inside the spec.
*(Settled in practice 2026-11-21: the finance desk's conversion kept its old-spec story in a change note beside the spec.)*

---
Structure adapted from arc42 (CC BY-SA 4.0); see `system/templates/component-page-template.md`.
