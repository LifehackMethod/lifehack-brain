---
title: "Canonical-principles SOP: history log"
what: "Retired and moved text from system/sops/canonical-principles-sop.md, kept verbatim and dated so nothing is lost. Never read in normal use."
read_in_normal_use: false
base_commit: "a5e968d  (git -C ~/lifehack-v2 log -1 --format=%h -- system/sops/canonical-principles-sop.md)"
base_file: "system/sops/canonical-principles-sop.md, 1713 lines at that commit"
created: 2026-10-30
status: "V2 copy, to be merged with the SOP"
---

# Canonical-principles SOP: history log

Each entry below is one passage removed or reworded in the SOP on 2026-10-30: CUT (retired), MOVE (change note, history not instruction) or FIX (original wording of a line that was reworded). Line ranges are the line numbers in the base commit `a5e968d`. Entries are in original line order. The original is copied word for word inside each fenced block.

Entries whose body held private material show one line instead of the verbatim block; those originals are kept in the operator's private notes. A second pass (2026-10-30) is at the end of this log; its line numbers are those of the edited SOP before that pass.

## 2026-10-30 · FIX · lines 1-13 · Old front matter (lines 1-13)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 15: replaced by compact machine-readable front matter (what the guide is for, when to read it, date updated 2026-10-30, and a section index with line numbers). The old fields that tools may read (id, title, record_type, desk, topic, created_at, status, authority, confidence, tier) are carried into the new front matter; updated_at is now 2026-10-30.
- Original lines: 1-13

```
---
id: root-2026-09-02-canonical-principles
title: "Canonical principles — the merged canon"  # v2 — IN FORCE in the V2 sandbox (2026-10-29); main keeps v1
record_type: canon
desk: root
topic: [system-architecture, llm-engineering]
created_at: 2026-09-02
updated_at: 2026-09-02
status: active
authority: user
confidence: CONFIRMED
tier: canon
---
```

## 2026-10-30 · CUT · lines 18-19 · Struck 'STATUS (v2 DRAFT, 2026-10-28)' paragraph and its italic note

- Date: 2026-10-30
- Action: CUT
- Reason: Dead draft status, already struck on 2026-10-29; the live status block (line 17) says the V2 canon is in force. The italic note after it (FIX 16a) only explained the strike and described a strike-plus-note editing method that the history log now replaces.
- Original lines: 18-19

```
>
> ~~**STATUS (v2 DRAFT, 2026-10-28):** draft for the V2 sandbox. v1 in the notes-side canon collection is the authority and the backup until Enver validates and swaps; no v1 text is deleted here — every change is a strike (`~~`) plus a `v2` note beneath it, or a new bullet. Frontmatter title carries the same suffix as a YAML comment (the quoted v1 title is kept intact).~~ *(Struck 2026-10-29: the strike-plus-note editing method still applies; "draft / not yet in force" no longer does.)*
```

## 2026-10-30 · FIX · line 28 · 'Stacked layers' wording

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 2: retired 'stack' picture; meaning (layers compound only when they fail differently) unchanged.
- Original line: 28

```
> **⇒ You are buying FRICTION, not certainty.** Every control raises the cost of going wrong without ever making it impossible, **and tools differ enormously in how much friction they buy** — a check that fires before the model is consulted is a wall; a line of prose is a speed bump. **Stacked layers compound friction, but only when they fail differently** — three speed bumps in a row is still one speed bump.
```

## 2026-10-30 · FIX · line 31 · 'irreversible -> stack' wording

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 2: retired 'stack' picture; meaning unchanged.
- Original line: 31

```
> **⇒ Depth is set by blast radius and reversibility, not importance** — irreversible → stack; **reversible and cheap → one deterministic check, then STOP.** ⚠ And blast radius is knowable at DESIGN time, so **a new irreversible action gets its stack up front**; the brake below governs *adding to* a control set that already exists, never the first build.
```

## 2026-10-30 · FIX · lines 68-69 · Marker cut a sentence in half ('lines [marker] were not ratified')

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 8: the sentence is repaired and the marker kept at the end of the clause; the removed private pointer cannot be restored.
- Original lines: 68-69

(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)

## 2026-10-30 · CUT · lines 100-101 · Struck 'Identical text' and 'agree by construction' claims

- Date: 2026-10-30
- Action: CUT
- Reason: Both claims were false and already replaced (a near-copy, kept in agreement by a quarterly human audit, section 12.b); only the struck words are removed, the live wording stays.
- Original lines: 100-101

```
> # THE FRAME — read before any line below. ~~Identical text~~ A near-copy of this text sits atop `system/sops/skill-building-sop.md`.
> *(Enver, 2026-09-05. ~~This block is the one place both documents agree by construction.~~ The two copies are kept in agreement
```

## 2026-10-30 · CUT · lines 127-129 · Struck 'Compliance is a stack, not a choice' paragraph

- Date: 2026-10-30
- Action: CUT
- Reason: Struck 2026-10-30 and replaced by the Venn / circles-of-friction paragraph directly below it; the dated pointer note only explained the strike.
- Original lines: 127-129

```
> ~~**Compliance is a stack, not a choice.** Each layer catches what the one above misses; a hook is the scarce top,
> never a substitute for the layers beneath it (§5.20).~~ *(2026-10-30: see "The layers of friction" above, Venn, not a stack)*
>
```

## 2026-10-30 · MOVE · line 142 · Change note introducing the 2026-09-06 right-sized rewording

- Date: 2026-10-30
- Action: MOVE
- Reason: Small change note (how a passage was reworded), not guidance; moved to the history log by Enver's approval. It would read as a dangling note once the struck text is cut.
- Original line: 142

```
> **REFINED 2026-09-06 (Enver's ruling — the heading and the closing clause were prescriptive; the description stays).**
```

## 2026-10-30 · CUT · lines 143-147 · Struck first wording of 'Right-sized, or it does not enter'

- Date: 2026-10-30
- Action: CUT
- Reason: Superseded by Enver's own rewording on 2026-09-06 (live wording follows); the one dropped clause was dropped by his instruction.
- Original lines: 143-147

```
> ~~**Right-sized, or it does not enter** *(Enver, 2026-09-05).* The Lifehack Harness is a minimal harness built on Pareto's
> principle: the most value, compliance and reliability for the least code, rules and structure. The question is never
> "how much can we build" but "how little buys the most." **We are not an enterprise solution.** A remedy that works but
> needs a second system to watch the first is recorded as *likely overbuilt for this harness* — kept, never adopted by
> default.~~
```

## 2026-10-30 · FIX · lines 154-157 · What the AI is; the human's share of the work

- Date: 2026-10-30
- Action: FIX
- Reason: ASK 3: Enver's 2026-09-06 sentence is kept verbatim and the stateless sentence and the Alzheimer's picture are added right after it. FIX 13: the human's share is the hedged compass wording instead of 'five percent, at most twenty'.
- Original lines: 154-157

```
> *(Enver, 2026-09-06.)* This is a human-in-the-loop judgment system. The model is a great deal of knowledge with very
> little judgment; the human is a great deal of judgment with far less knowledge; the intelligence is the pairing. The
> human's share of the work should be small — five percent, at most twenty — but never zero. Human-out-of-the-loop
> designs are very rare in this system; the default is human in the loop.
```

## 2026-10-30 · FIX · lines 208-209 · Definition of a LAYER ('a rung in the enforcement stack')

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 2: the compass names this line as stale wording; meaning (count layers by how they fail) unchanged.
- Original lines: 208-209

```
⚠ **THREE ADJACENT WORDS, THREE DIFFERENT THINGS — do not merge them.** A **LAYER** is a rung in the enforcement
stack (prose · a gate · a hook) — **that is the only sense counted here.** §0's *"the deterministic machinery is
```

## 2026-10-30 · FIX · line 211 · LAW -> Principle (skills-SOP cross-reference)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 1: the skill-building SOP renamed its LAWs to Principles on 2026-09-05; numbers unchanged.
- Original line: 211

```
link in the skills-SOP LAW 2 loss-chain: **a place where intent died between design and run.** ⇒ ***Which
```

## 2026-10-30 · FIX · lines 213-214 · 'irreversible -> stack' wording (section 0.1)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 2: as above.
- Original lines: 213-214

```
**DEPTH IS SET BY BLAST RADIUS AND REVERSIBILITY, not importance** — irreversible → stack; reversible and
cheap → one deterministic check, stop.
```

## 2026-10-30 · CUT · lines 225-227 · Label 'DRAFT — not in force.' (section 0.2) and the hospital heading

- Date: 2026-10-30
- Action: CUT
- Reason: CUT 7: the label is false now that the document is in force (Enver, 2026-10-29). The rest of the paragraph stays. The heading is renamed 'THE STEP-RUNNER: one more circle of friction' (FIX 4a).
- Original lines: 225-227

```
## 0.2 — THE HOSPITAL: one more layer (v2, 2026-10-28)
> **DRAFT — not in force.** Nothing in §0.1 or the centering frame is struck or qualified by this section. It sits INSIDE that frame: no perfect control · every layer eventually fails · test the combination · FRICTION, not certainty · a real layer depends on neither memory nor agreement · compliance is the center of the Venn diagram, not a stack. What follows adds ONE candidate circle of friction and says exactly what it does and does not buy.

```

## 2026-10-30 · FIX · lines 228-232 · Hospital frame sentence and the 'walls / chart / nurse' bullets

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 4: the frame sentence moves into the new section 0.3 'A picture that helps: the hospital' (Enver does not want to lose the hospital); the three bullets are rewritten with plain names (hooks, the card and record, the runner) and the same content.
- Original lines: 228-232

```
**The frame (Enver's).** A fresh AI agent is a very intelligent Alzheimer's patient: sharp in the moment, nothing carried between moments. So the hospital does not rely on the patient remembering.
- **HOOKS = walls.** A wall blocks one bad action. It cannot force an ORDER of actions. (Layer already counted in §0.1 and §5.20.)
- **CARD + RECORD = the chart.** Ordered steps, each typed code / ai / human, each with a check. An append-only record on disk. A fresh agent is handed STATE (files), not history.
- **RUNNER = the nurse.** A small script hands over ONE step at a time with its file inputs, runs the step's check, and is the ONLY writer of the record. The agent never writes the record.

```

## 2026-10-30 · FIX · line 233 · 'Where it sits among the circles' paragraph: walls / nurse / 'end of the stack'

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 4a: plain names; every caveat kept.
- Original line: 233

```
**Where it sits among the circles.** Walls stop an action. The nurse is a separate layer BESIDE the walls: a sequencing-and-proof layer (did step N happen, in order, and does its output pass a code check). It acts without consulting the model, so by the §0.1 test it is a layer and not a preference. But it is one more layer, not the end of the stack: it fails for its own reasons (a check can be presence-only, a value can go unvalidated, the record can be truncated, a step can be non-idempotent), it does nothing about content inside an `ai` step, and it does not replace any hook or any other layer. Layers combine; the combination is what gets tested. It buys friction, not certainty.
```

## 2026-10-30 · FIX · lines 243-246 · The hospital map (Walls / Chart / Nurse)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 4b: moved into the new section 0.3 'A picture that helps: the hospital', each hospital word labelled with its plain name; the section references are unchanged.
- Original lines: 243-246

```
**Map (labels verified against this file).**
- **Walls:** §4.6 (hook = remove an ability) · §5.4 (bind the predictable and catastrophic) · §5.9 (a guard that looks like it works) · §5.20 (compliance is the Venn center) · §15.27 (the model gate).
- **Chart:** §4.7 (reliability belongs to the chain, seam not step) · §4.12 (re-anchor at the generation boundary) · §5.15 (skill as reusable unit, three phases) · §15.15 (externalise state, pass a pointer) · §12.c (artifact-then-pointer) · §7.3 (nothing is saved unless something writes it).
- **Nurse:** §4.1 (verify the effect, not the report) · §4.3 (a model checking its own work) · §5.6 (alive means saying so) · §5.7 / §5.7a (break the thing; zero events and rates) · §7.2 (a self-written citation must be checked) · §7.7 (a test that authors both sides) · §15.14 (independent positive proof) · §15.17 (independent checker).
```

## 2026-10-30 · FIX · line 248 · 'lowest rung that works' in the 'when NOT to use a card' list

- Date: 2026-10-30
- Action: FIX
- Reason: ASK 4: ladder wording replaced by 'smallest tool that works'.
- Original line: 248

```
**When NOT to use a card** (grounded in §15.29 and §5.12 — lowest rung that works; the person reading is the real detector; a missed or doubled run must be harmless).
```

## 2026-10-30 · FIX · lines 251-252 · 'it needs no chart' and 'the nurse can only hand over and check files'

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 4a: plain names.
- Original lines: 251-252

```
- Pure code: it needs no chart; plain code on a schedule, per §15.29.
- Reasoning that cannot be written to a file: the nurse can only hand over and check files.
```

## 2026-10-30 · FIX · line 256 · '§2 applies to the nurse too'

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 4a: plain name.
- Original line: 256

```
**§2 applies to the nurse too.** The subtract-don't-add principle governs this layer: it is added machinery, paid on every run, and it must keep earning its place. If a card does not catch something in real use that the other layers missed, §2 says remove it.
```

## 2026-10-30 · FIX · lines 258-260 · 'WAIT list (what this draft does NOT do)' and 'the walls and the scarce top of the stack'

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 4a: retitled 'What this section does not claim'; every item kept; hospital and stack words replaced.
- Original lines: 258-260

```
**WAIT list (what this draft does NOT do).**
- No VALIDATED or "fixed" wording anywhere; the evidence above is OBSERVED/CANDIDATE only.
- No demotion of hooks; they stay the walls and the scarce top of the stack in the §5.20 sense.
```

## 2026-10-30 · FIX · lines 279-280 · 'Hospital' as the name of a real system

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 11: say 'the Hospital findings system' at first use so it is not confused with the retired hospital picture.
- Original lines: 279-280

```
**1.2 Detection was never the gap; being believed was.** Journal 2026-08-05. Hospital was built so
faults couldn't go unseen; Efficiency was built on top and also terminates at an eyeball. **Adding a
```

## 2026-10-30 · FIX · line 300 · LAW -> Principle (skills-SOP cross-reference)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 1: as above.
- Original line: 300

```
"EXCLUDED 6.10 … self-referential" and "2 regressions across 29 cards examined."* Not LAW 2's decay seam (that is
```

## 2026-10-30 · MOVE · lines 312-313 · Retitling note for 'THE LAW' (subtract, don't add)

- Date: 2026-10-30
- Action: MOVE
- Reason: Small change note (retitled 2026-09-05), not guidance; moved to the history log by Enver's approval.
- Original lines: 312-313

```
> ~~THE LAW~~ → retitled 2026-09-05 (REFINED). Its own text marks it WORKING THEORY; a theory titled "the law"
> contradicted the frame above. Content unchanged. It stays the first principle under the one law.
```

## 2026-10-30 · FIX · line 323 · 'This law' -> 'This principle' (subtract, don't add)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 1: the subtract-don't-add principle was retitled from 'the law' on 2026-09-05; 'the one law' (the stochastic-environment sentence) is NOT changed.
- Original line: 323

```
called methodologically fragile and deregulation-motivated by its own peer-reviewed source. This law
```

## 2026-10-30 · FIX · lines 418-421 · Section 4.6 heading: half struck-out; the two surviving tests

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 5: the strike swallowed the end of the heading and the list of three tests. Repaired so a cold reader sees the two surviving tests (remove a tool, block an action) and the third as replaced on 2026-10-28 (check content and value, not existence). The struck words ('Everything else is friction.' and 'check whether the file got written') are kept here word for word.
- Original lines: 418-421

```
**4.6 Code works when it takes away an ability or looks at what actually happened. Everything else is
~~friction.** `[H]` Three tests: **remove a tool · block an action · check whether the file got written.**~~

> **v2 (orchestrator-v2, 2026-10-28):** Third test, replaced: **check content and value, not existence.** A file that exists can hold the wrong thing; presence-only checks produced the silent_wrong cases in orchestrator-v2. OBSERVED. (The struck 'check whether the file got written' is kept above; the other two tests stand.)
```

## 2026-10-30 · FIX · line 423 · 'friction that looks like control' (old sense of friction)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 5: friction is the approved good word since the 2026-10-29 ruling; the line used it in the old sense (fake control). Meaning unchanged.
- Original line: 423

```
Code the model is asked to *cooperate with* is friction that looks like control. Measured: 619
```

## 2026-10-30 · FIX · line 440 · ~79% figure in 4.7

- Date: 2026-10-30
- Action: FIX
- Reason: ASK 2: the '~79%' figure is marked unverified.
- Original line: 440

```
unit.** `[U]` `0.90**10 = 0.349`. But ~79% of multi-agent failures are handoffs. Retries convert a step
```

## 2026-10-30 · FIX · line 461 · LAW -> Principle (skills-SOP cross-reference)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 1: as above.
- Original line: 461

```
SOP's LAW 4.3 K-sampling rule. RESEARCHED.
```

## 2026-10-30 · FIX · lines 518-520 · Section 5.4: the 'escalation ladder' framing

- Date: 2026-10-30
- Action: FIX
- Reason: ASK 4 (Enver, 2026-10-30): replace the ladder with his principle. No fixed order and no hook-versus-script rule is written. Removed with it: 'A hook is the last rung, justified by a real incident or a catastrophic-silent failure' (a hook-versus-script rule).
- Original lines: 518-520

```
judgment*. **This is the rule for when something becomes a rule.** The escalation ladder: prose → a
binary gate inside a skill → the user-turn boundary → a hook. A hook is the *last* rung, justified by a
real incident or a catastrophic-silent failure. Hooking "usually do X" creates wallpaper and degrades
```

## 2026-10-30 · FIX · lines 554-555 · Marker cut a sentence in half ('automation dead but [marker] a human is compensating')

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 8: the sentence is repaired and the marker kept after the clause.
- Original lines: 554-555

(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)

## 2026-10-30 · MOVE · lines 567-568 · 'Moved from the build index' note at the end of 5.6a

- Date: 2026-10-30
- Action: MOVE
- Reason: Small change note, not guidance; moved to the history log. Line 567 is kept in the file minus the note; it is logged whole.
- Original lines: 567-568

```
model compiles a deterministic artifact once and leaves the runtime (§15.3, §15.5). *Moved from the build index,
2026-09-05, by Enver's ruling: "one method, not the only one."*
```

## 2026-10-30 · FIX · line 646 · Section 5.12 heading: 'lowest rung that works'

- Date: 2026-10-30
- Action: FIX
- Reason: ASK 4: ladder wording replaced by 'smallest tool that does the job'; the call / workflow / agent / multi-agent list is unchanged.
- Original line: 646

```
**5.12 Use the lowest rung that works: call → workflow → agent → multi-agent** — two vendors converge on
```

## 2026-10-30 · FIX · lines 653-655 · Section 5.12: 'Pass full context at every handoff, never a summary'

- Date: 2026-10-30
- Action: FIX
- Reason: ASK 2 (Enver, 2026-10-30: 'Can we let the LLM use its intuition? This seems a little prescriptive.'): becomes a principle with judgment; the ~79% figure is marked unverified.
- Original lines: 653-655

```
**Default to one unit and earn the split:** ~79% of multi-agent failures are at handoffs; a single
well-configured agent matched or beat multi-agent on 64% of tasks at ~2× the cost. Pass full context at
every handoff, never a summary. Authorisation belongs at the point of action: credentials held in a
```

## 2026-10-30 · FIX · line 662 · Section 5.12 v2 note: parenthetical about the struck 'pass full context' line

- Date: 2026-10-30
- Action: FIX
- Reason: ASK 2: the struck line is retired and section 5.12's text changed, so the parenthetical was no longer true.
- Original line: 662

```
> **v2 (orchestrator-v2, 2026-10-28):** Handoff, revised: hand the next agent current state as files, not history; full context still applies to merged work (§12.g). CANDIDATE. (The struck 'pass full context' line is under §12.g; this section's text is unchanged.)
```

## 2026-10-30 · FIX · lines 713-718 · Markers cut three sentences in half (section 5.18)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 8: each marker moved from the middle of a sentence to the end of its clause; count of markers unchanged.
- Original lines: 713-718

(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)

## 2026-10-30 · CUT · line 730 · Struck heading words on section 5.20

- Date: 2026-10-30
- Action: CUT
- Reason: Struck 2026-10-30 and replaced by the Venn-diagram heading; removed with the struck text.
- Original line: 730

```
**5.20 ~~Compliance is a stack, not a choice.~~ Compliance is the center of the Venn diagram, not a choice.** *(heading reworded 2026-10-30; frame in "The layers of friction" above. Where this section says "stack", read overlapping circles of friction.)* `[H]` §5.4 gives the escalation ladder — prose → gate → user-turn
```

## 2026-10-30 · FIX · lines 730-738 · Section 5.20 body: stack / ladder / rung wording

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 2 and ASK 4: retired picture (stack, escalation ladder, rungs) replaced by overlapping circles of friction and the smallest-tool principle; the heading note ('where this section says stack, read circles') is retired once the body is fixed. Evidence and receipts unchanged.
- Original lines: 730-738

(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)

## 2026-10-30 · FIX · lines 739-740 · 'a stack you cannot count'

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 2: retired 'stack' wording (section 5.20 pointer line).
- Original lines: 739-740

```
⭐ **HOW TO COUNT ONE IS IN §0.1, NOT HERE** *(added 2026-09-11)*. This section says compliance is the **overlap of several circles**;
**§0.1 says how to count one** — and a stack you cannot count is a number you are guessing. ⛔ **The rule is
```

## 2026-10-30 · FIX · line 747 · v2 note after section 5.20: walls / nurse / 'top of the stack'

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 4a and FIX 2: hospital and stack words replaced by plain names; meaning unchanged.
- Original line: 747

```
> **v2 (orchestrator-v2, 2026-10-28):** **§5.20 / §4.6 'a hook is the scarce top of the stack' stands unchanged.** Walls stop one action but cannot force order. The nurse (§0.2) is a separate layer beside them, not above or instead of them; layers combine, and each still fails. CANDIDATE as a layer.
```

## 2026-10-30 · FIX · line 860 · REFINED bullet depended on a struck sentence

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 14: the refined bullet now names Semantic Kernel so it stands alone; the struck sentence above it is left in place for a later pass.
- Original line: 860

```
  coming back to plan again. The vendor finding is one data point about *interactive* planners, not a direction.
```

## 2026-10-30 · FIX · lines 902-903 · Rulings list: 'private question-register shorthand struck' and the cryptic Cowork line

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 17: the shorthand refers to a private question register and is removed. FIX 12: the Cowork line said in plain words (a paraphrase to confirm). The Cowork sentence is marked '(paraphrase, unconfirmed)' in the SOP.
- Original lines: 902-903

(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)

## 2026-10-30 · FIX · line 905 · Rulings list: ledger counts

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 17: counts marked 'as counted 2026-09-01, not re-checked'.
- Original line: 905

```
ledger's type model is the truth (631 debt · 94 project · 89 decision · 34 blocked · 7 chore) ·
```

## 2026-10-30 · MOVE · lines 936-937 · 'Listed here 2026-09-05' change note on T9.11b

- Date: 2026-10-30
- Action: MOVE
- Reason: Small change note, not guidance; moved to the history log. The pointer 'carried in section 5.6' stays.
- Original lines: 936-937

```
carried in §5.6 and, until 2026-09-05, only in the build index. *(Listed here 2026-09-05 — it was cited everywhere and
recorded nowhere in this section.)*
```

## 2026-10-30 · FIX · line 987 · LAW -> Principle (skills-SOP cross-reference)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 1: as above.
- Original line: 987

```
  hand-off carried three wrong claims (a block "with no analogue" that duplicated SOP LAW 1b · "3× the length"
```

## 2026-10-30 · CUT · line 999 · Struck wrong claim '0 regressions, exit 0'

- Date: 2026-10-30
- Action: CUT
- Reason: False figure already corrected in place (the correction text stays, with its date and audit entry); kept here word for word.
- Original line: 999

```
  120 s timeout, an uncaught exception, and a scan that reported ~~**0 regressions, exit 0**~~ **no REGRESSION
```

## 2026-10-30 · FIX · line 1019 · Section 11, Q19: the GitHub security line

- Date: 2026-10-30
- Action: FIX
- Reason: ASK 5 and MOVE decision 2: a private security detail does not belong in a shipped document; removed from canon and moved to the operator's private notes.
- Original line: 1019

(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)

## 2026-10-30 · FIX · lines 1060-1062 · LAW -> Principle (skills-SOP cross-reference)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 1: as above.
- Original lines: 1060-1062

```
- **12.f A model that annotates vs a model that gates.** The field's "skeptical second model" collides with LAW 3 on its
  face; §4.11 already draws the line — a disconfirming pass annotates, never decides. → proposed: a scoping line under
  LAW 3, no experiment.
```

## 2026-10-30 · FIX · lines 1068-1070 · LAW -> Principle (skills-SOP cross-reference)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 1: as above.
- Original lines: 1068-1070

```
  deciding vote — it annotates, and the human or the code decides. *LAW 3 (SOP) says only that the actor may not declare
  its own work done; a different window checking is LAW 3 working as written, not a collision — 12.f as first drafted
  read LAW 3 as broader than it is.*
```

## 2026-10-30 · FIX · line 1075 · Model names in the tension list

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 10: the compass names tiers, not model names; the dollar figure is marked local and not re-derived.
- Original line: 1075

```
versus the local Sonnet→Haiku switch at ~$268/mo saved · **The distill loop adds by design, and §2 says
```

## 2026-10-30 · FIX · lines 1085-1090 · Section 12.g: sentence half struck-out (FIX 6) and 'pass full context' wording (ASK 2)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 6 and ASK 2: the live sentence now reads whole as the principle (enough to do the job well; full context the safe default); the ~79% figure is marked unverified. The v2 CANDIDATE note that interrupted the sentence is kept verbatim and moved to after the paragraph.
- Original lines: 1085-1090

```
**12.g Pass full context at every handoff (§5.12) versus withhold the expected answer when checking.** `[H]`
~~§5.12 says *"pass full context at every handoff, never a summary"* — ~79% of multi-agent failures are at~~

> **v2 (orchestrator-v2, 2026-10-28):** Replaced: hand the next agent current state as files, not history; full context still applies to merged work (§12.g's own case). CANDIDATE.

handoffs, and context-starved sub-agents make **conflicting implicit decisions invisible to each other**
```

## 2026-10-30 · FIX · line 1100 · Section 12.g: 'Unresolved; Enver rules'

- Date: 2026-10-30
- Action: FIX
- Reason: ASK 2: resolved by Enver 2026-10-30 ('a judgment call').
- Original line: 1100

(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)

## 2026-10-30 · FIX · line 1102 · Stray '--- ·' at the start of the 'Acceptance can create...' paragraph

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 7: formatting glitch from a joined line; it becomes its own numbered tension (12.h). The clause 'no rule is offered for it' is kept.
- Original line: 1102

```
--- · **Acceptance can create the property that invalidates the verification**: a checker passed a real destruction probe AND a selectivity probe, and retiring it is what broke it — its own acceptance criterion invoked itself once it was filed as done (2026-09-05, card 6.10). No pre-acceptance check could have found that, and no rule is offered for it.
```

## 2026-10-30 · CUT · lines 1104-1110 · Section 13: NOT PRINCIPLES - open decisions, Enver's alone

- Date: 2026-10-30
- Action: CUT
- Reason: Approved cut (Enver, 2026-10-30): not canon; anything still open belongs in the v2 brief's open loops.
- Original lines: 1104-1110

```
## 13. NOT PRINCIPLES — open decisions, Enver's alone

The reliability number (per chain, as an absolute count) · the timebox · what he is choosing not to fix ·
the Version B wishlist · a shared API layer across harness and web app · whether hospital becomes an
effect-channel diagnostic layer · whether to flip the five OTEL switches · whether diagnostics are
dev-only.

```

## 2026-10-30 · FIX · lines 1113-1137 · Section 14: pointers into the builder's private notes

- Date: 2026-10-30
- Action: FIX
- Reason: MOVE decision 3: the concept does not depend on a reader going to the evidence; private pointers dropped, one line remains. The heading line is kept in the file.
- Original lines: 1113-1137

(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)

## 2026-10-30 · FIX · line 1147 · '§5.20 stacks these'

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 2: retired 'stack' wording.
- Original line: 1147

```
  (near-zero *syntactic* failure — **shape, not truth**) · prompts. RESEARCHED. *§5.20 stacks these; the field ranks.*
```

## 2026-10-30 · FIX · line 1149 · '§5.20's stack works'

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 2: retired 'stack' wording. 'The one law' on this line is left as is (FIX 3 not applied).
- Original line: 1149

```
  rebuttal found. RESEARCHED. *Outside support for the one law, and for why §5.20's stack works.*
```

## 2026-10-30 · FIX · line 1160 · 'stacked' in 15.7

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 2: retired 'stack' wording.
- Original line: 1160

```
  all else stays with the model, stacked. **New code enters only by compilation — written and proven in one
```

## 2026-10-30 · MOVE · lines 1208-1210 · Provenance note under 15.20 (written 2026-09-05, renumbered)

- Date: 2026-10-30
- Action: MOVE
- Reason: Small change note, not guidance; moved to the history log by Enver's approval.
- Original lines: 1208-1210

(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)

## 2026-10-30 · FIX · line 1267 · LAW -> Principle (skills-SOP cross-reference)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 1: as above.
- Original line: 1267

```
  ⚠ **Distinct from the skills SOP's LAW 1b (MODEL-REACH), which asks whether a seam can reach a model AT ALL
```

## 2026-10-30 · FIX · line 1323 · LAW -> Principle (skills-SOP cross-reference)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 1: as above.
- Original line: 1323

```
   **LAW 5** records **knows-but-violates at 8–99%** — a model restates a rule it is *simultaneously* violating.
```

## 2026-10-30 · FIX · line 1332 · LAW -> Principle (skills-SOP cross-reference)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 1: as above.
- Original line: 1332

```
   via LAW 5; the what-raises-it claim is CANDIDATE.)*
```

## 2026-10-30 · FIX · line 1345 · 'v2 nurse verdict ... DRAFT' heading

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 4a: 'nurse' is a retired word and the document is in force; the evidence tier (OBSERVED, fault-injection harness only) is kept.
- Original line: 1345

```
**v2 nurse verdict (orchestrator-v2, 2026-10-28) — DRAFT, OBSERVED in a fault-injection harness only, not validated by multi-week use.** Does the one-step-at-a-time runner (§0.2) help with each mode? YES / PARTLY / NO:
```

## 2026-10-30 · FIX · line 1411 · LAW -> Principle (skills-SOP cross-reference)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 1: as above.
- Original line: 1411

```
baselines · a semantic classifier behind every guard (*also contradicts §4.3 / LAW 3 — held as dissent*) · runtime tracing
```

## 2026-10-30 · FIX · line 1422 · 'CANDIDATE 14th mode'

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 16b: the census now runs to 19 modes, so '14th' is wrong; the candidate is still awaiting Enver's ruling.
- Original line: 1422

```
is 11 seen from inside a skill. **CANDIDATE 14th mode, awaiting Enver's ruling:** *the cloud drive is not a filesystem* —
```

## 2026-10-30 · FIX · line 1428 · Section 17 heading: 'proposed, not started'

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 9: 19 entries record a dated ground result; the heading contradicted them.
- Original line: 1428

```
## 17. EXPERIMENTS TO RUN — proposed, not started *(section opened 2026-09-05 by Enver's ruling; every test proposed in a session lands here)*
```

## 2026-10-30 · MOVE · line 1429 · v2 note at the head of section 17 ('this section is not moved')

- Date: 2026-10-30
- Action: MOVE
- Reason: Small change note, not guidance; moved to the history log by Enver's approval. It also pointed into the builder's private notes.
- Original line: 1429

(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)

## 2026-10-30 · FIX · line 1433 · Section 17 intro: 'None has run.'

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 9: as above.
- Original line: 1433

```
> None has run. Adding one here costs nothing; running one is a plan card.
```

## 2026-10-30 · FIX · line 1435 · Section 17 intro: 'fourteen modes'

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 9: the failure-mode census has 19 modes.
- Original line: 1435

```
> An experiment earns a fix its tier. Ground — one question, arms, a positive and a negative control, measured by artifact — earns OBSERVED. Persisting the fix and running it through blind sessions that were not trying to make it hold earns VALIDATED. A mode's line moves to fixed only after a fresh session audits the fix against the map, the manual and the elements — in a personal productivity system intended to work this way over years, would this hold? — and Enver rules. A fix is fixed when a session with zero state can pick it up from what is persisted and it holds. One window owns one mode; windows report to the coordinator only; the coordinator re-runs every result before believing it. A fix's PERSISTENCE also sits on a scale, weakest to strongest: prose-asked-nicely (a rule the model must remember and re-apply live, unenforced) → speed-bump / redundant-signal / second-check (a real mechanism that raises the cost of the failure or catches it after the fact, but can still be bypassed or ignored on some path) → structurally-impossible-on-every-path (the failure literally cannot occur, on every path, not merely the one tested). This is a scale, not a works/doesn't-work binary — a fix earns the rung the evidence on disk actually supports, and most fixes in this harness sit partway up it, holding on some paths and not others. Where no perfect structural fix exists — and for most of the fourteen modes, none yet does — layered redundancy at the middle rung is the best available fix and a legitimate, rankable outcome in its own right, not a failure to have found the top one.
```

## 2026-10-30 · FIX · line 1438 · Section 17 index stops at mode 17

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 9: modes 18 and 19 have entries 17.25 and 17.26.
- Original line: 1438

```
> **1**→17.11 · **2**→17.12 · **3**→17.13 · **4**→17.14 · **5**→17.6 *(companion arm: 17.5)* · **6**→17.15 · **7**→17.2 · **8**→17.16 · **9**→17.17 · **10**→17.18 · **11**→17.1 · **12**→17.19 · **13**→17.20 · **14**→17.21 · **15**→17.22 · **16**→17.23 · **17**→17.24 — and 17.3, 17.4, 17.7, 17.8, 17.9, 17.10 belong to no single mode and no window owns them.
```

## 2026-10-30 · FIX · line 1440 · Section 17: 'fourteen' and the coordinator's launch-script name

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 9 and MOVE decision 1 (adapt wording specific to Enver's own system): the launch script is not in the plugin.
- Original line: 1440

```
> **How to read a mode entry.** Each of the fourteen carries seven labelled parts, in this order. **Question** — one variable, nothing else moving. **Arms** — each differs from the control in exactly one thing. **Artifact** — the command whose output decides the verdict; the coordinator's `experiment-window-launch.sh --verify NN` re-executes this exact command and diffs its own output against what the window quoted, so a command that does not run is a defect in the entry, not a task for the window to improvise around. **Controls** — positive (the planted failure), negative (the clean twin), and the prior run already on disk where one exists. **Persistence** — the delivery shape the fix would be persisted through at 5,000 ft. **Moves** — which §16 line and which SOP `[F-n]` line moves, and to which word. **Pre-registered pass/fail** — the verdict rule, written before anything runs, in the closed vocabulary `fires` · `theater` · `error` · `dark` · `unscored`, categorical and never a rate.
```

## 2026-10-30 · FIX · line 1442 · Section 17: pointer to the experiment-window remit SOP

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 9: the file does not exist in V2; the pointer would send a student to nothing. The trailing marker on that line was removed in the second pass (see the end of this log).
- Original line: 1442

```
> **What is deliberately NOT here.** The window's own operating contract — its folder, `status.md` after every step, the self-test that must read `theater` before anything else runs, `result.md`'s six lines, atomic `.tmp`-then-rename writes, every plant on a scratch copy and never the live file, questions held not sent — lives in `system/sops/experiment-window-remit-sop.md` and is not repeated in any entry below. Read that first; these entries assume it. ⛔ owner's notes
```

## 2026-10-30 · FIX · lines 1444-1445 · Section 17: shell-variable preamble

- Date: 2026-10-30
- Action: FIX
- Reason: MOVE decision 1: 'private repo' and 'two of the three paths contain spaces' are specific to Enver's own setup.
- Original lines: 1444-1445

(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)

## 2026-10-30 · FIX · lines 1509-1510 · 'the input list for the research pass'

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 16d: the research pass is done (section 16).
- Original lines: 1509-1510

```
- **17.10 Unsolved modes awaiting research** *(from the 2026-09-05 solutions audit; the input list for the research pass,
  then for new experiments here). PARTIAL modes are listed too — held at one site, not generalised.*
```

## 2026-10-30 · FIX · line 1574 · LAW -> Principle (skills-SOP cross-reference)

- Date: 2026-10-30
- Action: FIX
- Reason: FIX 1: as above.
- Original line: 1574

```
  **Persistence** — set from mode 11's answer. ⚠ The trap specific to this mode is recursive and worth naming: whatever is persisted must not take its own verdict from the thing it checks. §12's recorded tension — a dead-man's switch on every hook versus "no meta-checker" (§4.3 / LAW 3) — is live here and is not this experiment's to resolve.
```

## 2026-10-30 · FIX · line 1591 · Section 17.16: command that calls the coordinator's launch script

- Date: 2026-10-30
- Action: FIX
- Reason: MOVE decision 1: the script is coordinator tooling that is not in the plugin; the result and the caveats are untouched.
- Original line: 1591

(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)

## Second pass, 2026-10-30

Line numbers below are those of the SOP before the second pass.

## 2026-10-30 · FIX · line 545 · Section 5.4: the lesson of the removed 'last rung' line, as a principle

- Date: 2026-10-30
- Action: FIX
- Reason: Restores only the lesson of 'A hook is the last rung, justified by a real incident or a catastrophic-silent failure' (removed in the first pass; see the 5.4 entry above). Written as a principle: no ladder, no fixed order, no hook-versus-script rule.
- Original line: 545

```
conformance; ideally 100% conformance; use the smallest tool that does the job.
```

## 2026-10-30 · FIX · lines 124, 1051, 1138, 1296 · References to the removed section 14 pointers

- Date: 2026-10-30
- Action: FIX
- Reason: Section 14 now holds one line; these mentions promised a pointer list or a record there and were reworded to point at that one line.
- Original lines: 124, 1051, 1138, 1296

```
> compressed and read as complete while being incomplete-to-wrong. Pointers in §14.
**From the right-size audit, 2026-09-05** *(record in §14; each is a source of investigation, not a defect to patch):*
> before it moves into §0–§8. Full evidence and caveats: the §14 modalities record.
## 16. THE FAILURE MODES — the census, 2026-09-05 *(REPRODUCED: 15 blind readers · 4 sources · every mode 4–6 months · 11–12 of 12 sources · 1,656 cited instances; method §14)*
```

## 2026-10-30 · FIX · lines 99, 1286 · Sentences that ended in a private notes path

- Date: 2026-10-30
- Action: FIX
- Reason: The private path was removed from the shipped SOP (the original, with its path, is in the operator's private notes); the preceding line was reworded to read cleanly.
- Original lines: 99, 1286

```
> (2026-05-30 → 2026-08-25), and the 28 altitude-tagged lines at
  (2026-10-24, five blind angles; evidence moderate). Detail:
```

## 2026-10-30 · FIX · lines 101, 581, 741, 743, 1432, 1491, 1516, 1526, 1530, 1535, 1538, 1556, 1567, 1569, 1578, 1581, 1589, 1599, 1601, 1610, 1624, 1635, 1651, 1654, 1672, 1682 · The 'owner's notes' marker removed from the sentence it ended

- Date: 2026-10-30
- Action: FIX
- Reason: Marker removed; the sentence and its lesson are unchanged. Lines where a private path was removed with the marker are in the operator's private notes instead.
- Original lines: 101, 581, 741, 743, 1432, 1491, 1516, 1526, 1530, 1535, 1538, 1556, 1567, 1569, 1578, 1581, 1589, 1599, 1601, 1610, 1624, 1635, 1651, 1654, 1672, 1682

(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)

## Third pass, 2026-10-30

Line numbers below are those of the SOP before the third pass.

## 2026-10-30 · FIX · lines 323, 405, 421, 580, 993, 1016, 1025, 1026, 1157, 1180, 1203, 1207, 1211, 1215, 1220, 1224, 1229, 1301, 1302, 1303, 1304, 1305, 1306, 1307, 1308, 1309, 1310, 1311, 1325, 1326, 1327, 1328, 1329, 1330, 1332, 1334, 1360, 1377, 1396, 1435, 1447, 1452, 1463, 1473, 1474, 1487, 1491, 1492, 1534, 1535, 1544, 1555, 1556, 1567, 1568, 1569, 1572, 1577, 1578, 1581, 1588, 1589, 1592, 1599, 1600, 1601, 1610, 1611, 1624, 1625, 1635, 1636, 1640, 1645, 1651, 1654, 1658, 1667, 1672, 1682, 1693 · Private pointers removed from lines that kept their lesson or result

- Date: 2026-10-30
- Action: FIX
- Reason: A pointer into the owner's private notes (a research, insight, receipt, plan or window-name path) was removed from each line. The lesson, result, date and caveat on the line are unchanged; where a path sat inside a command, a placeholder in angle brackets stands for it.
- Original lines: 323, 405, 421, 580, 993, 1016, 1025, 1026, 1157, 1180, 1203, 1207, 1211, 1215, 1220, 1224, 1229, 1301, 1302, 1303, 1304, 1305, 1306, 1307, 1308, 1309, 1310, 1311, 1325, 1326, 1327, 1328, 1329, 1330, 1332, 1334, 1360, 1377, 1396, 1435, 1447, 1452, 1463, 1473, 1474, 1487, 1491, 1492, 1534, 1535, 1544, 1555, 1556, 1567, 1568, 1569, 1572, 1577, 1578, 1581, 1588, 1589, 1592, 1599, 1600, 1601, 1610, 1611, 1624, 1625, 1635, 1636, 1640, 1645, 1651, 1654, 1658, 1667, 1672, 1682, 1693

(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)

## Fourth pass, 2026-10-30

Line numbers below are those of the SOP before the fourth pass.

## 2026-10-30 · FIX · lines 285, 290 · Hospital picture: 'nurse = the step-runner'

- Date: 2026-10-30
- Action: FIX
- Reason: The step-runner is never called the nurse (compass). The picture's nurse stays as part of the old image and is no longer mapped to the step-runner as a name; walls = hooks and chart = the record stay as picture terms; the section references on the label line are unchanged.
- Original lines: 285, 290

```
**Each hospital word, in its plain name:** walls = hooks · chart = the record (the card and record) · nurse = the step-runner (§0.2).
- **Nurse (the step-runner):** §4.1 (verify the effect, not the report) · §4.3 (a model checking its own work) · §5.6 (alive means saying so) · §5.7 / §5.7a (break the thing; zero events and rates) · §7.2 (a self-written citation must be checked) · §7.7 (a test that authors both sides) · §15.14 (independent positive proof) · §15.17 (independent checker).
```

## 2026-10-30 · FIX · lines 544-545 · Section 5.4: attribution of 'Heavier machinery is justified...'

- Date: 2026-10-30
- Action: FIX
- Reason: Enver approved: the sentence 'Heavier machinery is justified by a real incident, or by a failure that would be both catastrophic and silent.' is kept as plain guidance carried over from the old canon, not as his words. The attribution of the smallest-tool sentence ('Enver's principle (2026-10-30)') stays.
- Original lines: 544, 545

```
judgment*. **This is the rule for when something becomes a rule.** Enver's principle (2026-10-30): the minimum amount of code for the maximum amount of
conformance; ideally 100% conformance; use the smallest tool that does the job. Heavier machinery is justified by a real incident, or by a failure that would be both catastrophic and silent.
```

## 2026-10-30 · FIX · lines 305, 925-926, 1019, 1039, 1121, 1479, 1485, 1654 · Private names removed or neutralised

- Date: 2026-10-30
- Action: FIX
- Reason: The name of a private document (the builder's question register) was removed, and the old window name became 'a session', on each line. On line 926 the Cowork sentence is now marked '(paraphrase, unconfirmed)'. On line 1121 Enver's own words were added beside the ruling, as approved. The lesson on each line is unchanged.
- Original lines: 305, 925, 926, 1019, 1039, 1121, 1479, 1485, 1654

(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)

## 2026-10-30 · FIX · history log, the block for original line 1100 and the Reason of the block for lines 902-903

- Date: 2026-10-30
- Action: FIX
- Reason: The verbatim line for original line 1100 named the old window name and was moved to the operator's private notes; the Reason of the lines 902-903 block now carries the '(paraphrase, unconfirmed)' note. Original Reason line follows.

```
- Reason: FIX 17: the shorthand refers to a private question register and is removed. FIX 12: the Cowork line said in plain words (a paraphrase to confirm).
```

## 2026-10-30 · FIX · canon line 1332 (private repo detail neutralised)
- Reason: nothing private in the Harness (COMPASS P-42); same fix as the skill guide.
(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)

## 2026-10-30 · FIX · line 178 capitalisation (leakage checker false positive)
- Reason: the leakage checker reads a capitalised disease name beside "partner" as a person's name. The only change on line 178 was the first letter of "alzheimer's", from upper to lower case; every other character is identical to the current line.

## 2026-10-30 · FIX · citation markers after the owner's-notes markers were stripped
- Reason: the citation lint needs each path to a file that isn't in the plugin to say so; added a ⛔ "not shipped" note. Originals:

Original line 742:
```
⛔ historical text as it was; `system/sops/skill-irl-findings.md` is not shipped in the plugin.
own frontmatter names `system/sops/skill-irl-findings.md` as its living intake (lines 12, 19); no such file exists in
```
Original line 1516:
```
⛔ historical text as it was; `system/pulse-config.md` is not shipped in the plugin.
  `waiting-on-port` rows in `system/pulse-config.md` to `yes`, and they are watched actually running — output, not a log
```
Original line 1526:
```
⛔ historical text as it was; `system/pulse-config.md` is not shipped in the plugin.
  **Extended 2026-09-07 (card 5.1) into MODE 1's runnable form. Reports stored plus message.** The kill-one-job form above still waits on Enver wiring `system/pulse-config.md`; the form below needs no wiring and no change to any live file, so window 1 runs this one now and the entry keeps both.
```
Original line 1538:
```
⛔ historical text as it was; `system/pulse-config.md` is not shipped in the plugin.
  **Arms** — the same runner, registered the same way in the same sandboxed manifest, differing in exactly one thing, whether it does its work: **(a)** does the work and exits 0; **(b)** skips the work and exits 0; **(c)** skips the work and exits **75**, which `system/pulse-config.md:57` defines as *"the job's OWN preflight decided not to run this tick — skipped, never a fault."* Arm (c) is there to show what the contract *can* express, so arm (b)'s result reads as a gap in the signal rather than a gap in the manifest.
```
Original line 1530:
```
⛔ historical text as it was; `system/organism/generated/capability-census.md` is not shipped in the plugin.
  **Controls** — *positive:* `system/tools/assert_dispatch_fidelity.py`, present (33,168 bytes) and with **0 occurrences in each of `registrations.json`, `~/.claude/settings.json` and `pulse-config.md`, counted 2026-09-07**, plus one freshly planted stub hook in a scratch tree that nothing registers. *Negative:* `system/hooks/guard_canon_write.sh`, registered live on `PreToolUse` matcher `Bash|Write|Edit` — the sweep naming it is a false positive. *Prior run on disk:* `system/organism/generated/capability-census.md`, which already carries **145 `UNCALLED` lines** (counted 2026-09-07). So the question is not whether uncalled artifacts can be listed — that list exists — but whether listing them changes anything.
```

## 2026-10-30 · FIX · line 1299 private receipts pointer
- Reason: nothing private in the Harness (P-42).
(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)
