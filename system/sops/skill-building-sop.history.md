---
title: "Skill-building SOP: history log"
what: "Retired and moved text from system/sops/skill-building-sop.md, kept verbatim and dated so nothing is lost. Never read in normal use."
read_in_normal_use: false
base_commit: "a5e968d  (git -C ~/lifehack-v2 log -1 --format=%h -- system/sops/skill-building-sop.md)"
base_file: "system/sops/skill-building-sop.md, 3065 lines at that commit"
created: 2026-10-30
status: "V2 copy, to be merged into main with the SOP"
sibling_files: "Enver-only material from the same SOP is in skill-building-operator-notes.md (ClaudeOps), not here."
---

# Skill-building SOP: history log

Each entry below is one passage removed from the SOP on 2026-10-30: CUT (retired) or MOVE (history, not instruction). Line ranges are the line numbers in the base commit `a5e968d`. All entries carry the same date, so they are listed in original line order. The text is verbatim.


## 2026-10-30 · MOVE · lines 15-21 · Front-matter `sources:` list

- Date: 2026-10-30
- Action: MOVE
- Reason: Front-matter list of source records (change/provenance note); the SOP keeps its own evidence tags.
- Original lines: 15-21

```
sources:
  - system/sops/skill-building-sop.md@v1 (git history)                 # v1 — every law preserved, re-ranked
  - system/research/2026-07-12-skill-sop-ontrack-convergence.md        # [R]  12-agent blind convergence
  - records/research/2026-07-19-step-prompt-injection-craft.md         # [R2] step-prompt convergence
  - records/research/2026-07-25-code-vs-llm-enforcement-split.md       # [C]  6-agent crowd convergence
  - records/research/2026-07-25-skill-dissection-findings.md           # [C]  6 trusted repos, code-level
  - skill-irl-findings.md (your personal code folder, not shipped)     # [M]  our own measured runs
```

## 2026-10-30 · CUT · lines 70-72 · Struck: 'Compliance is a stack'

- Date: 2026-10-30
- Action: CUT
- Reason: Struck text the SOP itself had already replaced (compliance-is-a-stack paragraph); the live replacement stays.
- Original lines: 70-72

```
> ~~**Compliance is a stack, not a choice** (§II.1a). Each layer catches what the one above misses; a hook is the
> scarce top, never a substitute for the layers beneath it.~~ *(2026-10-30: frame updated, see `canonical-principles-sop.md`, "The layers of friction")*
>
```

## 2026-10-30 · CUT · lines 84-89 · Struck: first 'Right-sized, or it does not enter'

- Date: 2026-10-30
- Action: CUT
- Reason: Struck first wording of the 'right-sized' statement, plus its lead-in; the reworded statement stays directly below.
- Original lines: 84-89

```
> **REFINED 2026-09-06 (Enver's ruling — the heading and the closing clause were prescriptive; the description stays).**
> ~~**Right-sized, or it does not enter** *(Enver, 2026-09-05).* The Lifehack Harness is a minimal harness built on Pareto's
> principle: the most value, compliance and reliability for the least code, rules and structure. The question is never
> "how much can we build" but "how little buys the most." **We are not an enterprise solution.** A remedy that works but
> needs a second system to watch the first is recorded as *likely overbuilt for this harness* — kept, never adopted by
> default.~~
```

## 2026-10-30 · CUT · lines 107 · Leftover DRAFT status note

- Date: 2026-10-30
- Action: CUT
- Reason: Leftover 'Was: STATUS - DRAFT' note in an in-force document (status block at line 105 already says in force).
- Original lines: 107

```
> *(Superseded 2026-10-29 — the strike-plus-note editing method below still applies; "draft / v1 is the authority" no longer does.)* **Was:** STATUS — DRAFT. Built on the assumption that the orchestrator-v2 rig validates. **v1 is the authority until Enver swaps this in.** No v1 text was deleted — changed passages are struck through (~~) and followed by a `> **v2 (orchestrator-v2, 2026-10-28):**` line with a confidence tier. Reordering waits (see PART 0, "What waits").
```

## 2026-10-30 · CUT · lines 129-166 · 'Not in this repository' blocks

- Date: 2026-10-30
- Action: CUT
- Reason: Three 'not in this repository' note blocks and closing warning: wrong about 19 of the 37 files they list, and they point at Enver's private notes. Includes the note about the renamed `cal-weekly` skill.
- Original lines: 129-166

```
> ## NOTE — WHAT THIS PAGE CITES THAT IS NOT IN THIS REPOSITORY
>
> **⛔ Nothing marked ⛔ below is coming** — the lesson's evidence is in the lesson; the path was only ever
> the filing location of the original write-up. These bullets are load-bearing for `system/tools/citation_lint.py`
> (a marker accounts for its paths file-wide): correct a bullet, never delete one. Full original prose → `ARCHIVE-2026-09-05.md` § "NOTE blocks — full original text".
>
> - ⛔ `records/research/2026-07-25-code-vs-llm-enforcement-split.md` · `state/debt-ledger.md` · `state/projects/lifehack-cowork/brief.md` · `state/projects/cowork-bulk-ingestion/brief.md` · `state/projects/huddle/huddle-skill/brief.md` · `state/projects/infrastructure/lifehack-correct-architecture/brief.md` · `state/projects/ingest-skill/brief.md` · `state/projects/project-system/brief.md` · `state/projects/security/security-hardening/brief.md` · `state/projects/security/sentinel-gateway/records/2026-07-03-reader-actor-enforcement-proof.md` · `state/projects/skill-builder/brief.md` · `state/projects/skill-system/brief.md` · `state/projects/translator-voice/brief.md` — records in the author's own notes folder, cited as where a lesson was
>   learned. Not in any repository, and not needed: the evidence is in the rule.

> ## NOTE — THE `[M]` MEASUREMENTS WERE TAKEN UNDER A FORMER SKILL NAME
>
> `[M]` evidence here was measured 2026-07 against the skill then named `cal-weekly` on the `cal` desk; the desk
> was renamed `cal` → `planning` on 2026-08-14/15 and every citation updated to `planning-weekly`. The runs behind
> the numbers are unchanged, nothing was re-measured; the HUD persona `Cal` is a character name, deliberately not renamed. Full text → `ARCHIVE-2026-09-05.md` § "NOTE blocks — full original text".

> ## NOTE — WHAT THIS PAGE POINTS AT THAT IS NOT IN THIS REPOSITORY
>
> - ⛔ **Evidence in the author's own notes** — every lesson here cites the project record where it
>   was learned, and those live under a personal notes folder, not in any repository: `records/2026-07-13-translator-voice-debug-history.md` · `records/decision/2026-06-04-design-lifehack-skill.md` · `records/decision/2026-06-27-numbers-integrity-enforcement.md` · `records/decision/2026-07-02-plans-backup-hole-postmortem.md` · `records/decision/2026-07-13-scratchpad-in-brief.md` · `records/decision/2026-07-13-statusbar-hud-build.md` · `records/decision/2026-07-28-model-efficiency-plan-abandoned.md` · `records/decisions/2026-07-17-claudegate-two-way-overwrite.md` · `records/insight/2026-08-01-agent-name-discards-report.md` · `records/insight/2026-08-05-the-code-llm-seam.md` · `records/log/2026-05-30-datagate-websearch-automation.md` · `records/log/2026-05-31-lifehack-v2-audit.md` · `records/log/2026-06-03-relay-ghost-root-cause-fix.md` · `records/log/2026-06-07-overmyshoulder-dev-browser-root-cause.md` · `records/logs/2026-05-26-cross-machine-sync-infrastructure.md` · `records/reference/2026-07-12-stage2-email-interpret-method.md` · and 13 more of the same kind.
>   The lesson is complete without them; the path was the filing location of the original write-up.
> - ✅ **The shared-primitives library — SIX OF THESE HAVE SINCE LANDED, and this line was corrected
>   rather than left to rot.** `system/parts/` now exists here and holds
>   `forbidden_content.py` · `move_aside.py` · `residue_scrub.py` (with the shipping lane) and
>   `order_lint.py` · `phase_gate.py` · `section_present.py` (with `/skill-builder`). Every citation of
>   those six on this page now resolves, and `system/parts/run_selftests.sh` gates them.
> - ⛔ **The rest of that library is still not here** — `system/parts/README.md` · `system/parts/accrual_gate.py` · `system/parts/bounded_input.py` · `system/parts/capture_gate_selftest.py` · `system/parts/completeness_receipt.py` · `system/parts/fanout_budget.py` · `system/parts/fanout_completeness.py` · `system/parts/fanout_gate.py` · `system/parts/identifier_redaction.py` · `system/parts/map_carry_receipt.py` · `system/parts/precondition_gate.py` · `system/parts/routing_evals.py` · `system/parts/voted_judge.py` · `system/parts/write_ledger.py`
> - ⛔ **Tools from the donor system** — `system/tools/checkin_open.py` · `system/tools/conformance-lab/t5_grade.py` · `system/tools/fanout-lab/` · `system/tools/gauge_check.py` · `system/tools/health_line.py` · `system/tools/ingest_coverage.py` · `system/tools/ingest_setdiff.py` · `system/tools/new-skill.sh` · `system/tools/section_archive.py` · `system/tools/skill_promise_check.py` · `system/tools/skill_promise_sweep.py`
> - ⛔ **Hooks from the donor system** — `system/hooks/guard_agent_return_channel.sh` · `system/hooks/mirror_plans.sh` · `system/hooks/scratch_capture_gate.sh`
> - ✅ **The shipping lane has since landed** — `system/shipping-lane/judge.py` and `system/shipping-lane/scrub.py` are both here now, with `/ship`. 
>   ⛔ Line numbers cited elsewhere on this page against the donor's copies of those two files will
>   not match, because both were rewritten so their rules come from the reader's own identity file
>   rather than the author's name.
> - ⛔ **Other documents** — `.claude/skills/extension/` · `.claude/skills/invocation/` · `shared/tools/intake_reader.py` · `system/factory/emit_gate.py` · `system/factory/extract_clauses.py` · `system/factory/route_to_part.py` · `system/reference/settings.json` · `system/security-canon.md` · `system/sops/skill-irl-findings.md`
>
> ⚠ **A STALE ABSENCE-LIST IS WORSE THAN NONE** — it tells a reader not to bother looking for a file that is right
> there; this block was wrong in ten places the day `/ship` and `/skill-builder` landed. `system/tools/citation_lint.py`
> catches exactly this; re-run it after anything crosses. Why `system/parts/` is the big one → `ARCHIVE-2026-09-05.md` § "NOTE blocks — full original text".

```

## 2026-10-30 · CUT · lines 210 · Leftover DRAFT evidence note

- Date: 2026-10-30
- Action: CUT
- Reason: Leftover italic 'DRAFT, built on the assumption...' note, with a pointer to Enver's private notes.
- Original lines: 210

```
> *DRAFT, built on the assumption that the orchestrator-v2 rig validates. Evidence: `state/projects/orchestrator-v2/brief.md` ⛔ (owner's notes) §2 and §4. Tiers: OBSERVED = seen in the rig with a receipt; CANDIDATE = one skill, awaits the week-long /save test and a second skill on a card (per [P2]).*
```

## 2026-10-30 · CUT · lines 212-221 · Hospital comparison (Part 0)

- Date: 2026-10-30
- Action: CUT
- Reason: The retired hospital comparison ('The frame, in plain language'): Enver retired it for friction; the plain-words idea survives at lines 185-195 and 222-228.
- Original lines: 212-221

```
## The frame, in plain language

The harness is a **hospital for very intelligent Alzheimer's patients** — the patients are fresh agents: brilliant, capable, and with no memory of what happened a minute ago.

- **WALLS = hooks.** One circle of friction: a hook blocks one bad action, so going wrong costs more. ~~They keep the agents in.~~ They cannot make a patient do steps in order.
- **CHART = the card plus the record on disk.** A fresh agent reads where things stand and the one next step. Hand it STATE, not history.
- **NURSE = the runner script.** It hands over one step at a time with its inputs as files, runs the check, and writes the chart. The patient never writes the chart. It is another circle of friction, the strongest one for step order, and it fails for its own reasons.

**Principle: do not try to make the patient obedient; put the rules in the nurse.** That is the strongest circle for step order, not a guarantee. (The ESCALATION LADDER in §II.3 and LAW 3 are the same instinct, one altitude down.)

```

## 2026-10-30 · CUT · lines 260-268 · Hospital MAP table

- Date: 2026-10-30
- Action: CUT
- Reason: The hospital MAP table placing sections on the retired hospital picture.
- Original lines: 260-268

```
## MAP — where the existing sections sit in the hospital

| Role | Existing sections |
|---|---|
| **Walls** (a circle of friction: block one action; cannot order steps) | §II.1 family 3 (WALL); §IV.7 "Simpler skill + structural hook" bullet |
| **Chart** (state on disk, read to resume) | §II.0 floor (c), the state/memory layer; "OUR OWN BET" and §VI.1 (the shared state file); §IV.8 per-run receipt; §IV.9 the HUD |
| **Nurse** (the runner: delivers, checks, writes) | LAW 1 (code owns the mechanical perimeter); LAW 3 (never let the actor grade its own completion); §II.1 families 1-2 (REPLACE / VERIFY); PART V checkers |
| **Shrinks to "a human is talking to the model"** | §IV.1 to §IV.7 (anchoring); the barn-sour material |

```

## 2026-10-30 · CUT · lines 269-294 · 'New rules in this draft' recap

- Date: 2026-10-30
- Action: CUT
- Reason: 'New rules in this draft' recap: a duplicate of rules already placed in the body, wearing the draft framing.
- Original lines: 269-294

```
## New rules in this draft (each also placed in the body)

- Code reads the human's answer and refuses anything but an explicit yes (§II.3, §V.4b). **OBSERVED**
- The record has a distinct `waiting` state, separate from `fail` (§II.3). **OBSERVED**
- A hard kill (SIGKILL) leaves the mkdir lock until stale-steal (1500s); a normal close (SIGHUP) releases it; the live cron runner has the same pattern; the 1500s window is a deliberate trade-off (after [A48]). **OBSERVED**

> **v2 (audit, 2026-10-28):** Stage 3 fix (OBSERVED): the lock now records its owner pid. A dead owner's lock is stolen at once; a live owner still gets rc 75. The 1500s wait described above was the pre-fix behaviour.
- The AI never writes the record; only the runner does (LAW 3, §V.9). **OBSERVED**
- When testing a kill, verify the kill landed before the step you meant to interrupt (§V.4c). **OBSERVED**
- Hand state, not history (§IV.6, §VI.1). **CANDIDATE**
- Card + runner + record is the default shape for any ordered skill (§III.1, §III.4). **CANDIDATE**
- A session-reach step receives its inputs as FILES written by a code step, or it cannot run under a runner (LAW 1b reach table). **CANDIDATE**

- Every check tests CONTENT, never presence; "non-empty" is not a check (LAW 3, §V.4b). **OBSERVED**
- Every side-effect step is safe to run twice (idempotent), or records what it did BEFORE acting so a resume can skip it (LAW 1). **OBSERVED**
- The runner detects a truncated or malformed record before resuming and fails loudly instead of guessing (LAW 1). **OBSERVED**
- An exit code of 0 from the AI step is never by itself proof of work; the next step's check reads the artifact (LAW 3). **OBSERVED** (emily marker finding, on paper)
- Never silence an external command's errors (`2>/dev/null`, `|| true`) in a card step; a failed fetch must not read as "nothing new" (LAW 1). **OBSERVED**
- Always score with the card, or `out_of_order` is false (§V.5). **OBSERVED**
  > **v2 (audit, 2026-10-28):** cause: without the card the scorer orders steps alphabetically and reported false out_of_order (2 on /save, 16 on marc). OBSERVED.
- Test the test rig first: a bite with known faults must name every fault before a big run is trusted; the injector bug was found this way (§V.4c). **OBSERVED**
- The AI→code handoff is a contract: fixed shape, code checks shape and content, loud fail on anything else; judgment goes to a reviewer. OBSERVED.
- The flip: the runner calls the model per step; the model never holds the step list. OBSERVED.

> **Tiering note (audit):** the tags above are per rule, not blanket: each rule carries its own tier (OBSERVED where the rig saw it; CANDIDATE otherwise). The same holds for the "Default shape" section above, which is CANDIDATE as a whole only because the week-long test has not run.

```

## 2026-10-30 · MOVE · lines 295-306 · Audit additions (orchestrator rig)

- Date: 2026-10-30
- Action: MOVE
- Reason: Orchestrator test-rig 'Audit additions' (exit-code numbers, version pinning, paper findings): rig evidence, not procedure. Moved, not cut.
- Original lines: 295-306

```
Audit additions (each with its own tier):

- Exit-code contract: 0 complete · 70 waiting · 75 stood down · 1 step failed · 124 watchdog; the cron runner also uses 3 missing config · 2 transient auth · 137 watchdog kill. A marker advances only on rc 0 AND a passing content check. **OBSERVED** (brief §4; rig README).
- Version pinning: the runner writes `ccv=<claude version>` on each run's first record line; 13 version changes occurred across 300 simulated days. Use JSON output; a past `claude -p` empty-stdout regression (2.1.81 to 2.1.83); `--bare` is slated to become the `-p` default. Pin and re-test on upgrade. **OBSERVED / CANDIDATE** (ccv line and version churn observed; the `--bare` change is from the research record).
- ai steps run read-only (`--allowedTools Read`); only the runner writes outputs and the record. **OBSERVED** (rig README).
- Scorer definition: out_of_order = a pass whose predecessor has no earlier pass / answered / skipped-done line. **OBSERVED** (rig scorer).
- Most steps are plain code: emily 14/20, deryl 13/15, clair 12/14 on paper. **CANDIDATE** (`rig/paper/`).
- The card pins the model per ai step (paper found skill text, runner and plan disagreeing on models). **CANDIDATE** (`rig/paper/*.notes.md`).
- Classify steps copy values verbatim (later steps must not work from a paraphrase); undefined flags (emily's Fit/Confidence) must be defined before carding. **CANDIDATE** (`rig/paper/`).
- When skill, runner and old copies disagree (folder names, which runner is live), the card names the one live path. **CANDIDATE** (`rig/paper/`).
- A stale scratchpad is a second source of truth; the record is the one source. **CANDIDATE** (`rig/paper/`).

```

## 2026-10-30 · MOVE · lines 325-328 · Strike-and-replace edits list

- Date: 2026-10-30
- Action: MOVE
- Reason: List of strike-and-replace edits made in the body (change note).
- Original lines: 325-328

```
## Strike-and-replace edits made in the body (all `> **v2 (orchestrator-v2, 2026-10-28):**`)

§IV.8 engine/state-machine (CANDIDATE) · §IV.8 short-run "add nothing" (CANDIDATE) · §IV.8 receipt emitted (OBSERVED) · §IV.6 "habit, not a solution" (CANDIDATE) · §IV.4 model-written banner (CANDIDATE) · §II.3 "say go" most reliably-held (OBSERVED) · LAW 1b HEADLESS cannot pause (OBSERVED) · LAW 1b nested `claude -p` (OBSERVED, qualified not refuted) · §VI.1 handoff carries FULL context (CANDIDATE).

```

## 2026-10-30 · CUT · lines 329-336 · 'What waits' list

- Date: 2026-10-30
- Action: CUT
- Reason: 'What waits': a waiting list for a plan that was cancelled (includes the hospital reorganisation).
- Original lines: 329-336

```
## What waits

These wait for the **week-long /save-on-a-card test and a second skill on a card** (per [P2]); until both, everything tagged CANDIDATE stays CANDIDATE:

- The full reorganisation of this document under the hospital frame (no section is moved in this draft).
- Promotion of every CANDIDATE item above to doctrine.
- The held lines: the [F11] and §IV.6 prose-step entries' core text; LAW 1b's policy-risk lines; [P4] (the week-long test is a deliberate exception to "force the condition instead of waiting").

```

## 2026-10-30 · CUT · lines 349-459 · ROUTE table of contents

- Date: 2026-10-30
- Action: CUT
- Reason: The 111-line ROUTE table of contents (and its three entry points): replaced by machine-readable `route:` / `start_here:` front matter (COMPASS P-38).
- Original lines: 349-459

```
## 🧭 ROUTE — find your question, not the outline

> **This is the generated map of the file — every heading, in document order.** It replaced a hand-written prose
> index on 2026-09-05: that index was sorted by the question a builder asks, which is the better shape, but it was
> maintained by hand and had begun to drift. It is preserved verbatim at `ARCHIVE-2026-09-05.md` § "🧭 ROUTE — the original
> question-sorted index" — read it for the *questions*; read the map below for *where things are*.
>
> **The three entries worth knowing before anything else:**
> ⭐⭐⭐ *"Has anyone already tried this and had it fail?"* → **`§II.4a` / `§II.4b` — DO NOT BUILD**. Grep them
> before you build anything that smells like a retry; `deadend_check.py` searches them for you. ~35% coverage of
> what is on disk (its own header says so) — absence there is not proof it is safe.
> ⭐⭐ *"The HARNESS did something I didn't expect"* → **`§II.4a` cluster 1, facts about the harness** — measured
> behaviours of Claude Code itself (stdin not `$1`; exit 0 cannot block; only `description:` triggers a skill; a
> NAMED sub-agent's report is discarded).
> ⭐ *"Is there already a tool I can call instead of writing one?"* → **`§II.4`** — but read its archive banner
> first; the per-part caller counts were hand-kept and drifted.


> Generated from the headings below. Levels: `#` part · `##` section · `###`/`####` a named rule.

- Skill-Building Playbook v2
  - 🧭 ROUTE — find your question, not the outline
  - §0 — WHAT A GOOD SKILL IS (the portrait — every rule below hangs off these six traits)
- PART I — WHAT HOLDS IN A STOCHASTIC ENVIRONMENT *(formerly "the laws of physics" — retitled 2026-09-05, REFINED; labels kept for cross-reference)*
  - LAW 1 — The Division of Labor: code owns the mechanical perimeter, the LLM owns judgment inside it
    - ⭐ THE SEAM — what the line between the two halves is actually MADE OF
    - ⭐ THE DIVISION INSIDE A SINGLE TOOL: **FINDING is fuzzy; PRINTING, COUNTING, COMPARING and REFUSING are not**
    - ⭐ LAW 1b — THE SECOND AXIS: **MODEL-REACH**. A closed vocabulary says WHAT crosses the seam. It says nothing about whether the seam is REACHABLE AT ALL.
  - LAW 2 — Intent leaks at four seams; diagnose WHICH one before you fix anything
  - LAW 3 — Never let the actor grade its own completion
  - LAW 4 — Three things an LLM structurally CANNOT do
  - LAW 5 — Prose decays, and the decay is measured
- PART II — THE ENFORCEMENT TOOLBOX
  - §II.0 — The three floors (what you are enforcing ACROSS)
    - THE FLOOR IS THE INSTRUMENT SELECTOR — use the wrong one and you get a confident wrong answer
  - §II.1a — ~~Compliance is a STACK, not a rung to pick~~ Compliance is the center of the Venn diagram, not a rung to pick *(added 2026-09-05, OBSERVED; reworded 2026-10-30)*
  - §II.1 — The four families (in order of preference)
  - §II.2 — WHY prose instructions fail (the five modes gates defeat)
  - §II.3 — The reliability ladder (how hard to gate — the Verify/Wall dial)
    - Three rules that govern the whole toolbox
  - §II.4 — The primitives library (build once, reuse in every skill)
    - ⚠ THE HEADLINE INVERSION — read this before the table `[M, verified 2026-08-07, independently re-verified]`
    - ⛔ THE PER-PART CATALOGUE HAS BEEN ARCHIVED — REGENERATE IT BEFORE YOU TRUST IT *(2026-09-05)*
  - §II.4a — ⭐ DO NOT BUILD — what was tried and failed
    - From the failure census, 2026-09-05 — REPRODUCED (15 blind readers · journal + 38 briefs + ledger + doc-vs-disk · every mode 4–6 months, 11–12 of 12 sources · 1,656 cited instances)
    - 1. Facts about the harness (measured behaviours, not opinions)
    - 2. Prose does not enforce
    - 3. Cheap models and cheap judges cost more than they save
    - 4. Tests that grade their own homework
    - 5. Prescription calcifies
    - Also UNIVERSAL, not sorted into the five named clusters
    - LOCAL — recorded history, binds nothing
  - §II.4b — DO NOT BUILD / DO NOT RETRY — build *process* moves proven not to work *(section opened 2026-09-05 by ruling; grows over time)*
  - §II.5 — Packaging: two lanes, so enforcement travels
  - §II.6 — Run-vs-read: the folder IS the signal
  - §II.7 — ⏸ HELD hypothesis: the demand-class law (NOT yet doctrine)
- PART III — BUILD A SKILL (the birth procedure)
  - III.1 — Classify it FIRST: skill, or command?
  - III.2 — Declare its INTENT (three layers, written before anything else)
  - III.3 — Write the `description:` frontmatter (the #1 failure mode)
  - III.4 — Design the flow (§I refers you here for depth)
  - III.5 — Progressive disclosure + layout
  - III.6 — Scaffold at birth, not after the fact
  - III.7 — The spec-diff gate: catch Law 2's link 1 before you ever run the thing
  - III.8 — Name every rule's evidence surface, at design time
    - ⭐ NOWHERE IS A DECISION POINT, NOT A DEAD END — remove the CAPABILITY instead
  - III.9 — Build process: four rules that survived contact
  - III.10 — Close: the per-rule enforcement decision
    - ⭐ THE HUMAN-IN-THE-LOOP TEST — how to make that call (2026-08-01; this is the ruling, not a heuristic)
- PART IV — HOLD IT AT RUNTIME
  - §IV.1 — Three parties are in the room, and only one of them drifts
  - §IV.2 — The 3-layer injection model
  - §IV.3 — Rich canon loads once; a lean anchor fires every turn
  - §IV.4 — Two every-turn re-injections — and neither one is a gate
  - §IV.5 — Edges, not middle [R2]
  - §IV.6 — One step, one injection — never show the whole arc at once
  - §IV.7 — Anchoring the session, not just the user
  - §IV.8 — Staying on-PROCEDURE (distinct from on-principle)
  - §IV.9 — Draw the Path Beat on the status bar (a skill's own HUD line)
  - §IV.10 — Briefing a PANEL of independent sub-agents [R2]
  - ⏗ OUR OWN BET (not crowd-validated) — the file-spine / fresh-context-per-phase architecture
- PART V — VERIFY THE SKILL
  - §V.1 — One detector per loss-chain link
  - §V.2 — Measure before you enforce
  - §V.3 — A fixture can manufacture a violation the real skill never commits
  - §V.4 — Verify the verifier
  - §V.4a — BLIND THE GRADERS, NEVER THE ACTORS
  - §V.4b — A gate verifies EVIDENCE OF WORK, never the FORM of a claim
  - §V.4c — Probe a gate by DESTRUCTION, not by minimization
  - §V.4d — A CLAIM WRITTEN NEXT TO A THING IS TREATED AS THE THING
  - §V.5 — Component checks say nothing about SEAMS — test the seam as a thing
  - §V.6 — The three failure types (from v1 §3.5, preserved)
  - §V.7 — The enforceability partition (from v1 §3.5, preserved)
  - §V.8 — The real supervised run is the acceptance test
  - §V.9 — Anti-patterns observed in the wild `[C]`
- PART VI — SCALE & SPECIAL SHAPES
  - §VI.1 — Splitting a flow that outgrows one skill (EARN it)
  - §VI.2 — Interaction craft for human-facing skills
  - §VI.3 — Character-with-purpose
  - §VI.4 — Writing it
  - §VI.5 — Quality bar
  - §VI.6 — Model tiering
- EVIDENCE & PROVENANCE
  - §VI.7 — MAKING A SKILL FASTER: subtract before you optimize, and price every layer that isn't work
    - ⭐⭐⭐⭐ LAW A — SUBTRACT FIRST. The loudest phase is not automatically the reachable one.
    - ⭐⭐⭐ LAW B — PRICE EVERY LAYER THAT ISN'T DOING THE WORK. A handoff costs time even when it does nothing.
    - ⭐⭐ LAW C — WALL CLOCK AND HUMAN-WAITING TIME ARE DIFFERENT TARGETS, AND ONLY ONE OF THEM IS THE JOB
  - §VII — LIVING INTAKE: candidates, not doctrine
    - From the `/autoplan` rebuild, 2026-09-04 → 05 — the plan format's first execution against itself
    - From the two blind research runs, 2026-09-05 — outside evidence, tiered; nothing here is doctrine
    - What this run says about THIS file (for the next revision, not applied here)
```

## 2026-10-30 · MOVE · lines 464-470 · 'What changed from v1' note

- Date: 2026-10-30
- Action: MOVE
- Reason: 'What changed from v1' paragraph (change note).
- Original lines: 464-470

```
> **What changed from v1 (2026-07-25).** Same laws, ranked. v1 was ordered by build-chronology, which buried the
> load-bearing physics in the middle of §3. v2 puts the laws first, gathers every enforcement mechanism into one
> toolbox, and adds a VERIFY part that v1 had nowhere to put. Two weeks of conformance-lab measurement, a
> six-agent crowd-convergence study, and a code-level dissection of six trusted public skill repos are folded in.
> Nothing from v1 was dropped as wrong; the stale door-tester framing in v1 §3.5 is corrected in PART V.

---
```

## 2026-10-30 · CUT · lines 728 · Empty placeholder (line 728)

- Date: 2026-10-30
- Action: CUT
- Reason: Empty placeholder 'v2 note: held for the week-long test'.
- Original lines: 728

```
> v2 note: held for the week-long test
```

## 2026-10-30 · MOVE · lines 869 · v2 receipt (line 869)

- Date: 2026-10-30
- Action: MOVE
- Reason: One-line v2 receipt repeating rig result.
- Original lines: 869

```
> v2 receipt (orchestrator-v2): checker-writes-marker held in the rig — 10 terminal + 10 nested runs, 0 fail, 0 out-of-order, every record line written by the runner (brief §2/§4; Claude Code 2.1.312). OBSERVED, one rig.
```

## 2026-10-30 · CUT · lines 1113-1148 · Notes about the archived building-block table

- Date: 2026-10-30
- Action: CUT
- Reason: Two notes about the archived building-block table ('headline inversion', 'catalogue archived'): the table is gone; they also stated a wrong count (19; the real count is 14).
- Original lines: 1113-1148

```
### ⚠ THE HEADLINE INVERSION — read this before the table `[M, verified 2026-08-07, independently re-verified]`

For months this table carried the marker `(exists)` on exactly **one** row (capture gate) and nothing on the
other four. That was read as "only one of these five is actually built" — and a reading that bleak invites a
builder to re-build something that already exists, which is waste in the specific direction this SOP exists to
prevent. **It was backwards.** Checked against the filesystem on disk today: **5 of 5 named primitives
resolve to a real file.** The markers were stale, not the primitives — the rulebook made its own shelf look
emptier than it was. The bigger miss sits below the table: the library holds **19** built primitives in
`system/parts/`, and this section, even now, only profiles the ones with something to say. Verify the count
yourself: `python3 -c "import glob;print(len(glob.glob('system/parts/*.py')))"` → `19`.

**How to read what follows.** For every part: the path, what it does, **how many real callers** (a script or
skill that actually invokes it — a comment or docstring *mentioning* it is not a caller), its CLI interface,
and a "don't use this for X" line. The "don't use for" lines are **my read of the code, not a law** — verify
before leaning on one. Parts are grouped by how alive they are, because that's the fact a builder reaching for
one actually needs.

### ⛔ THE PER-PART CATALOGUE HAS BEEN ARCHIVED — REGENERATE IT BEFORE YOU TRUST IT *(2026-09-05)*

The tier-by-tier profile of ~17 parts (Tier 1 LIVE · Tier 2 factory-only · the capture-gate category error ·
Tier 3 zero-callers · also-live-and-uncatalogued) was **hand-kept, and it drifted**: it profiled
`system/parts/routing_evals.py` in Tier 3 as *"built, exists, but nothing calls it"* while the ⛔ banner at the
top of this same page listed that file as *"still not here"* — and the file does not exist in this repository at
all (`find . -name routing_evals*` → nothing; `.claude/skills/autoplan/fixtures/run_routing_eval.py` says in its
own docstring that no commit has ever touched it). A caller count typed by hand goes stale the day after it is
typed. **Do not read a caller count off this page. Regenerate it by script from the tree, then trust it.**

Full archived text, verbatim, with every ⚠ CORRECTED ruling and every "don't use this for X" line → `ARCHIVE-2026-09-05.md` § "§II.4 — the primitives catalogue (tiers)".
The two facts above the archive line that are still worth acting on: **the library holds 19 built parts** —
verify with `python3 -c "import glob;print(len(glob.glob('system/parts/*.py')))"` — and **a part crosses into a
repo when it has a caller, never because it is good**.

⛔ **Citation carried over with the archive**, because the paragraph that accounted for it moved: `skills/ingest/SPEC.md`
is the donor system's path and is not here — this repo ships that spec as `.claude/skills/ingest/SPEC.md`. Two other
donor-only paths (`agents/archivist.md`, and a parked copy of `order_lint.py`) left this page entirely with the catalogue.

```

## 2026-10-30 · MOVE · lines 1164 · v2 receipt (line 1164)

- Date: 2026-10-30
- Action: MOVE
- Reason: One-line v2 receipt repeating rig result.
- Original lines: 1164

```
> v2 receipt (orchestrator-v2): kill-and-resume skipped the done steps and ran the rest exactly once (every resumed run: s1/s2 `skipped-done`, s3/s4/s5 once). OBSERVED, 5 kill samples (4 clean).
```

## 2026-10-30 · MOVE · lines 1191 · v2 receipt (line 1191)

- Date: 2026-10-30
- Action: MOVE
- Reason: One-line v2 receipt repeating rig result.
- Original lines: 1191

```
> v2 receipt (orchestrator-v2): the checker caught **5/5** deliberate lies (rung 3: bad b01–b05 each failed at s2, no s3 line; good g01–g05 passed 15/15). OBSERVED.
```

## 2026-10-30 · MOVE · lines 1202 · v2 receipt (line 1202)

- Date: 2026-10-30
- Action: MOVE
- Reason: One-line v2 receipt repeating rig result.
- Original lines: 1202

```
> v2 receipt (orchestrator-v2): also for Part V rule zero — the check was watched failing first (`bad=1 good=0`, rung 6) and failing 5/5 on known-bad runs before being trusted passing. OBSERVED.
```

## 2026-10-30 · MOVE · lines 1221 · v2 receipt (line 1221)

- Date: 2026-10-30
- Action: MOVE
- Reason: One-line v2 receipt repeating rig result.
- Original lines: 1221

```
> v2 receipt (orchestrator-v2): the runner, not the helper, runs the check and writes the record; the rig's 3-way code-held fan-out passed 5/5 (`examined=15 pass=15`). OBSERVED.
```

## 2026-10-30 · MOVE · lines 1236 · v2 receipt (line 1236)

- Date: 2026-10-30
- Action: MOVE
- Reason: One-line v2 receipt repeating rig result.
- Original lines: 1236

```
> v2 receipt (orchestrator-v2): prose-step order did not decide any outcome in the rig, where the runner held it (0 out-of-order in 20 + 5 + 5 runs). OBSERVED.
```

## 2026-10-30 · CUT · lines 1238 · Empty placeholder (line 1238)

- Date: 2026-10-30
- Action: CUT
- Reason: Empty placeholder 'v2 note: held for the week-long test'.
- Original lines: 1238

```
> v2 note: held for the week-long test
```

## 2026-10-30 · CUT · lines 1772-1782 · II.5 Cowork packaging lane

- Date: 2026-10-30
- Action: CUT
- Reason: The Cowork lane: packaging for 'CLI vs Cowork' as two environments. COMPASS P-34: the separate-Cowork-product idea was abandoned. (The one general design rule in it is kept in a one-line stub under the same heading.)
- Original lines: 1772-1782

```
## §II.5 — Packaging: two lanes, so enforcement travels

`[C, live experiment 2026-06-29]` **Primitives are skill-local scripts** — they live in the skill's folder and
run unchanged on both the CLI and in Cowork's sandbox (bash + Python both execute there). **Walls are authored
once and registered twice**: `settings.json` on the CLI, a **plugin** on Cowork — where `settings.json` hooks
never fire, but *plugin-delivered* hooks were proven to genuinely block out-of-band (a blind session was blocked
from a benign write containing a trigger word while an identical write without it succeeded).
**Design rule:** never let a primitive depend on a hook, a host path, or `settings.json` — or it stops existing
the moment the skill travels. Carried open items: hook audit-log persistence, and UserPromptSubmit-via-plugin
(unproven — the every-turn anchor in Cowork is a TEST, not an assumption).

```

## 2026-10-30 · CUT · lines 2305-2308 · Struck: 'Is this run long enough to lose its place?'

- Date: 2026-10-30
- Action: CUT
- Reason: Struck/duplicated text already replaced by a live version.
- Original lines: 2305-2308

```
~~1. **Is this run long enough to lose its place?** Short/linear → add **nothing**. Only a long, multi-pass, or
   headless run earns an external **scratchpad** — and there it's mandatory, because it *will* get compacted.
   Never reach for a scratchpad by default.~~

```

## 2026-10-30 · CUT · lines 2317-2319 · Struck: 'Per-run conformance receipt'

- Date: 2026-10-30
- Action: CUT
- Reason: Struck text already replaced by the v2 note beneath.
- Original lines: 2317-2319

```
~~**Per-run conformance receipt.** A multi-step skill emits one machine-checkable pass/fail block at close, so each
gated step is provably done on *that* run — not just claimed at the end.~~

```

## 2026-10-30 · CUT · lines 2323-2327 · Struck: 'Our context'

- Date: 2026-10-30
- Action: CUT
- Reason: Struck text already replaced by the v2 note beneath.
- Original lines: 2323-2327

```
~~**Our context.** Frontier Claude running bash/markdown skills, not a general agent framework: an in-context SOP
beats heavy orchestration, and rigid state machines are brittle for us specifically. **We essentially never need
workflow-engine orchestration.** The heaviest this SOP asks for: a scratchpad for a long headless run, plus one
blocking validator hook for a single genuinely critical gate.~~

```

## 2026-10-30 · MOVE · lines 2406 · v2 receipt (line 2406)

- Date: 2026-10-30
- Action: MOVE
- Reason: One-line v2 receipt repeating rig result.
- Original lines: 2406

```
> v2 receipt (orchestrator-v2): a fresh session resumed from a file and finished the run (kill-and-resume, k01–k05). **OBSERVED, one rig — not REPRODUCED.**
```

## 2026-10-30 · MOVE · lines 2759-2760 · Stray note about plan_retire

- Date: 2026-10-30
- Action: MOVE
- Reason: Stray change note about a plan tool's commit lookup.
- Original lines: 2759-2760

```
> **v2 (audit, 2026-10-28):** plan_retire's commit lookup matched unrelated commits by card number and stamped 8 cards with false evidence; root cause unfixed. OBSERVED.

```

## 2026-10-30 · CUT · lines 2785-2790 · Struck: 'handoff carries FULL context'

- Date: 2026-10-30
- Action: CUT
- Reason: Struck 'handoff carries FULL context' bullet, already replaced by the v2 note beneath.
- Original lines: 2785-2790

```
~~- **The handoff carries FULL context, not a summary** — the receiving stage must find the whole prior-stage
  state in the shared file. A lossy summary at the handoff is the documented failure mode. *(Exception, OBSERVED
  2026-09-04: a DIAGNOSED atomic build card — nav/build SOP's diagnosis gate — deliberately carries LESS; the spec
  is the context, and the card held as a sub-agent brief with zero follow-ups. Full context is for STAGE
  handoffs; a card is a different unit.)*~~

```

## 2026-10-30 · MOVE · lines 2798 · v2 receipt (line 2798)

- Date: 2026-10-30
- Action: MOVE
- Reason: One-line v2 receipt repeating rig result.
- Original lines: 2798

```
> v2 receipt (orchestrator-v2): the same kill-and-resume result (`skipped-done` on s1/s2, rest once). OBSERVED.
```

## 2026-10-30 · MOVE · lines 2960-2965 · Delta log

- Date: 2026-10-30
- Action: MOVE
- Reason: Delta log (change note).
- Original lines: 2960-2965

```
**Delta log.** v2 (2026-07-25) re-ranked v1 — laws first, tools second, procedure third, verification fourth,
edge-cases last. Added the entire VERIFY part (v1 had nowhere to put it). Folded in the crowd-convergence study
and the six-repo code dissection `[C]`. Corrected v1 §3.5's stale single-instrument door-tester framing — the
current design is a three-tier × pipeline-seam architecture (reasoning · enforcement · state), not the single
blind judge v1 described.

```

## 2026-10-30 · MOVE · lines 2976-3024 · Planning-skill rebuild build log

- Date: 2026-10-30
- Action: MOVE
- Reason: belongs with the planning skill's own records: build log of the /autoplan (planning skill) rebuild, 2026-09-04 to 05 (COMPASS P-37). Includes the receipt at old line 2989.
- Original lines: 2976-3024

- Destination note: **belongs with the planning skill's own records** (COMPASS P-37). Kept here until that skill's element page or history exists.

```
### From the `/autoplan` rebuild, 2026-09-04 → 05 — the plan format's first execution against itself

Evidence: `~/lifehack-brain` branch `V2` (19 commits). **This section is the only home for these candidates** — no scratch copy exists elsewhere.
⛔ `plans/standalone-autoplan-rebuild.plan.md` — the plan and its `.done.md` live in the operator's notes folder, never in a repository; cited as where the receipts are, not as something this repo carries.
~~**Status: Phase 6 unbuilt, live run not yet made.**~~ — **CORRECTED 2026-09-05 (nav claudeops-1a): Phase 6 IS built** (cards 6.1–6.15 retired, 34 commits on `V2`, unpushed). **The live run is still not made**, so per canon §5.2 none of these is distilled from a finished run and [P2] still governs promotion.

*(Tiers below in the frame's vocabulary: Tier 1–2 = OBSERVED with receipt · Tier 3 = CANDIDATE · Tier 4 = CANDIDATE, weak.)*

**Tier 1 — mechanisms; a script can enforce each; the author had read the relevant rule and broke it anyway.**
- **A field a script consumes is written in the script's grammar, and the writer is refused, not warned.** 7 of 8 `Verify:` lines read correctly to a human and failed a machine re-run. AUTHORITATIVE · refuted if a constrained format still fails to re-run at a real rate.
- **A checker's "could not determine" never resolves to pass.** A fallback to "shell exited 0" on a `; echo $?` command retired a card whose check printed 2 against a stated 0. ~~AUTHORITATIVE~~ OBSERVED ×2 (one build, two operators, two mechanisms — not REPRODUCED until a different build) · Law 1b's no-outcome member applied to the verifier.
  **Extended 2026-09-05, clause → whole scan:** "found nothing" and "did not finish looking" must never render identically — at clause, card, or scan level. A scan killed mid-run (timeout, recursion, exception) exits non-zero with an explicit INCOMPLETE and never an empty finding list; it states EXAMINED beside FOUND ("0 regressions across 27 cards" is checkable; "0 regressions" is not). Receipt: the regression gate went blind on retirement (commit `3bd635f`; fix `65238c6`); a cold window saw "2 regressions across 29 cards examined" with the self-referential cards printed as EXCLUDED. Canon §1.3.

> v2 receipt (orchestrator-v2): the scorer prints examined beside found on every line (`examined=30 runs=10 pass=30 fail=0 waiting=0 out_of_order=0`). OBSERVED.

- **A verifier is also work, and any checker over "all finished work" will enumerate itself.** CANDIDATE (one build). Mechanical form: exclude its own entry and say so in the output; a self-exemption is honest only when visible. Its own check is the natural way to prove it works, so the recursion is what a well-written card produces, not an accident. *Open question, recorded not dressed up: this passed a destruction probe and a selectivity probe and was still wrong, because the property did not exist until acceptance — no pre-acceptance verification could have caught it.*
- **A parser that silently skips what it does not recognise is a fail-open.** An id regex dropped 5 of 15 cards and reported clean; a command allowlist dropped a clause and the card passed on the rest. Count examined vs present. AUTHORITATIVE, 2 instances · canon §5.6 for tokenizers.
- **Any session-level list beside a plan file is a second tracker.** The harness task queue diverged from the plan's cards inside the build fixing two-tracker failures. AUTHORITATIVE, 1 instance.
- **A verify runs as written, by a stranger, with nothing to substitute.** `<copy>` reached the shell as a redirect and a verify PASSED on it. AUTHORITATIVE.

- **A failure to run must not be able to equal a legal answer.** A check expected exit 2 from a linter; the linter was not found at the path, that failure also exits 2, and the check PASSED by coincidence. OBSERVED · `retired-reverify.md` card 2.3 · canon §5.6 sharpened.
- **A retired check un-passes itself.** Three retired cards failed their own checks after later cards moved the files; nothing re-runs a retired check. OBSERVED · canon §1.3 sharpened; card 6.10 builds the regression gate.
- **An exit code read after a pipe is the pipe's.** `cmd | head; echo $?` reports `head`'s. Two operators hit it in one build. OBSERVED ×2.

**Tier 2 — principles; true and receipted; process, not code.**
- Retiring a finished task preserves the amendment, not only the final form; second-resolution backup names collided (8 → 2 files). AUTHORITATIVE.
- When a checker refuses one item, run it against every item before fixing any — the mechanical form of §5.13. Four rounds of one-at-a-time; six more waiting. AUTHORITATIVE.
- The monitor re-runs the verify and never grades from the actor's report (LAW 3 at the nav/build seam). Three instances in one session. AUTHORITATIVE.
- Cold verification is a gate before the human, not a postmortem after. One cold pass caught a builder-certified false pass. AUTHORITATIVE.
- A size floor set by the party being measured measures nothing during the build (canon §4.1 for budgets). AUTHORITATIVE.
- A guard matching a MENTION blocks the fix for the thing it guards. New instance of a ledgered class. AUTHORITATIVE.

**Tier 3 — investigate; n=1 or awaiting the live run.**
- The control for a defect fixture is the same file with defects repaired, generated not hand-kept — never a different clean file (colliding ids manufactured false positives).
- Build order and verify order differ; a checker says NOT-YET, not FAILED, when the verify-dependency is unmet. WORKING THEORY.
- Blind ANGLE panels are not the PERSONA councils [A13] warns against: 11/11 hit, 0 false positives, canon §4.11 conditions met, [B23] agrees. WORKING THEORY until the live run.
- Code and reviewer lenses catch disjoint defect classes (32 vs 8, no overlap). AUTHORITATIVE-local, n=1.

**Tier 4 — recommendation.**
- Do not write size estimates into task text (3 for 3 wrong by 2–3×, same direction).
- Reading the doctrine does not inoculate — Law 5's knows-but-violates, measured on the author. A confirmation, not a finding.

**AWAITING VALIDATION — added 2026-09-05 by nav claudeops-1a, deliberately NOT promoted.**
*Enver's instruction: these get built and tested first; promote only after the fix is proven. Neither is doctrine and neither may be cited as one.*

- **A `Verify:` that compares against a bare literal freezes a value the system computes.** Write it computed-against-computed instead — `test "$(A)" = "$(B)"` rather than `= "17"`. ⚠ **The rule already existed one altitude up and nobody had applied it here**: §V.4a's *"a number without its instrument recorded beside it is not evidence — and a result that a reader cannot re-derive from the file is not a result."* Grepped 2026-09-05: zero occurrences connecting that rule to a plan card's `Verify:` slot. Receipt: 3 of 27 retired cards (2.4, 4.4, 6.8) fail their own `Verify:` today, all three because a later card moved a count they had frozen; ~57 count-comparisons exist across the retired set, so those three are the visible edge. The grammar ALREADY accepts the invariant form — measured, not assumed: a card whose Verify compares two computed values lints rc 0 and parses and runs under `plan_retire`. **CANDIDATE, NOT YET VALIDATED — the rewrite has not been built or tested.** Refuted if invariant-form Verifies prove vacuous, i.e. they pass while the artefact is genuinely broken; that is the probe that must run before this is promoted.

- **A checker whose own acceptance criterion invokes the checker becomes self-referential the moment its card is retired, and fails SILENT.** Receipt: card 6.10's `Verify:` invoked `plan_retire --regressions`; the scan re-runs every retired card's Verify, so on retirement it began invoking itself, hit the 120s subprocess timeout uncaught, and emitted no findings. Measured: the scan reported zero `REGRESSION` lines while card 2.4's Verify independently returned rc 1; an hour earlier the same scan reported four, with nothing repaired in between. ⚠ The companion claim that it *exited 0* was **asserted and never measured** — struck, see [P3]/A14. Fix built and verified (`65238c6`): self-exclusion stated in the output, `INCOMPLETE` + exit 3 on abnormal termination, and an examined-count beside the found-count. **OBSERVED ×1, one build — per [P2] a different build promotes; this is not that.** ⚠ **The property did not exist until acceptance**: this code passed a real destruction probe AND a selectivity probe and was still wrong. No rule is offered for that; it is recorded as an open question, not dressed up as a finding.

```

## 2026-10-30 · CUT · lines 3058-3065 · Done to-do list

- Date: 2026-10-30
- Action: CUT
- Reason: 'What this run says about THIS file': to-do list for a revision that has since happened.
- Original lines: 3058-3065

```
### What this run says about THIS file (for the next revision, not applied here)
- **[A13]** is written broadly enough to forbid the angle-panel shape that worked; scope it to persona councils and cross-cite [B23].
- **§II.3 rung 2** "required artifact — usually enough": enough for structure, never for a completion claim — a typed marker is rung 1 in rung 2's clothes (§V.4b).
- **§II.4 phase_gate blurb** omits the file's own caveat that `requires` cannot tell real work from words typed to match.
- **LAW 3** wants the clause "nor from the actor's report." **§III.9** wants the companion "fail once → sweep siblings." **§VI.1** wants the diagnosis-gate exception: a BUILD card carries less, by design.
- **§III.5** "<500 lines" and canon §5.1 "~1,000 words" never meet; state which governs.
- **This file's voice**: §VI.4 says avoid ALL-CAPS MUST/NEVER walls; the file is dense with them. Harness facts stay rules; doctrine reads as principle.
- **Two copies of this file exist (private ClaudeOps, public lifehack-brain), they differ, and `separation-manifest.md:287` calls them byte-identical.** One home, or a comparison that runs.
```

## 2026-10-30 · MOVE · to the operator notes (not repeated here)

These passages went verbatim, with the date, to the Enver-only file `skill-building-operator-notes.md`:

- lines 720-727: Policy risk on the headless row
- lines 731-760: Headless-in-cron measurements
- lines 1609-1744: LOCAL recorded failure history
- lines 2724-2730: Test-rig housekeeping tips

## 2026-10-30 · FIX · originals of lines reworded or repaired in place

The SOP's text stays but was corrected (principle/Rule wording, cross-references, friction wording, half-struck repairs, pointers to private notes, front page). The original wording of every such line is kept below, verbatim, so the change can be audited. 224 lines in 176 runs.

### FIX original · lines 4

```
title: "Skill-Building Playbook — the laws first, then the tools, then the procedure — v2 (in force in the V2 sandbox, 2026-10-29)"
```

### FIX original · lines 6

```
v2_status: "IN FORCE in the V2 sandbox (Enver, 2026-10-29); main keeps v1 until V2 ships. Was: DRAFT built on the assumption that the orchestrator-v2 rig validates; v1 the authority until Enver swaps this in. No v1 text was deleted: changed passages are struck through (~~) with a > v2 line beneath."
```

### FIX original · lines 12

```
updated_at: 2026-08-15
```

### FIX original · lines 23

```
  READ ORDER IS THE RANKING. PART I is the physics — five laws you cannot prompt your way around; if you read
```

### FIX original · lines 33-34

```
> # THE FRAME — read before any line below. A near-copy of this text sits atop `records/canon/2026-09-02-canonical-principles.md`.
> *(Enver, 2026-09-05. This block is the one place both documents agree by construction.)*
```

### FIX original · lines 37

```
> guaranteed. **That sentence is the one law in this document.** Everything else is a principle, and its tier
```

### FIX original · lines 67-68

```
> Rules live in code; prose carries principles with their reason. **"LAW" below is kept as a stable label for
> cross-references; read it as PRINCIPLE, tiered per line — none but the sentence above meets the bar for law.**
```

### FIX original · lines 73

```
> **Compliance is the center of the Venn diagram, not a stack** (§II.1a). The layers are overlapping circles of friction, each covering part of the risk; where they overlap, a mistake has to get past several at once. A hook is the scarce, expensive circle, never a substitute for the cheaper circles around it.
```

### FIX original · lines 75

```
> **The operating rule under the one law** *(added 2026-09-05 from the failure census — CANDIDATE as a single
```

### FIX original · lines 110

```
> *(The centering frame. Enver's, sharpened and adopted 2026-09-11. A near-copy leads `records/canon/2026-09-02-canonical-principles.md`; per canon §12.b the two are kept in agreement by a quarterly human audit, not by construction. ⚠ **That audit is a thing someone must REMEMBER — so by canon §0.1's own test it is a PREFERENCE, not a layer, and it will drift.** Chosen knowingly anyway: a sync script is one more thing that breaks silently and then needs its own alarm. **Stated so the weakness is owned rather than discovered.**)*
```

### FIX original · lines 114

```
> **Borrow security's architecture, never its threat model.** Borrow: no perfect control · every layer eventually fails · test the *combination*, since a stack whose layers each pass alone can still fail as a stack · **never claim zero — state what is covered and what remains.** Don't borrow the attacker: nothing is breaking in. What you guard is already inside, holds your tools, forgets between turns, and can reason its way past a rule it understands. *(Exception: anything read from outside can be authored against you — full adversarial posture there.)*
```

### FIX original · lines 116

```
> **⇒ You are buying FRICTION, not certainty.** Every control raises the cost of going wrong without ever making it impossible, **and tools differ enormously in how much friction they buy** — a check that fires before the model is consulted is a wall; a line of prose is a speed bump. **Stacked layers compound friction, but only when they fail differently** — three speed bumps in a row is still one speed bump.
```

### FIX original · lines 119

```
> **⇒ Depth is set by blast radius and reversibility, not importance** — irreversible → stack; **reversible and cheap → one deterministic check, then STOP.** ⚠ And blast radius is knowable at DESIGN time, so **a new irreversible action gets its stack up front**; the brake below governs *adding to* a control set that already exists, never the first build.
```

### FIX original · lines 123-124

```
> ⚠ **TWO WORDS, TWO MEANINGS — do not merge them.** A **LAYER** is a rung in the enforcement stack (prose · a
> gate · a hook), and layers are what this frame counts. A **SEAM** is a link in LAW 2's loss-chain — a place
```

### FIX original · lines 126-127

```
> intent was lost.*** ⇒ **LAW 2 tells you which SEAM leaked. This frame tells you whether your LAYERS were ever
> real.** ⛔ *Evidence: `state/projects/canonical-housecleaning/records/2026-09-11-layered-enforcement-composition.md` (Brain, not this repo).*
```

### FIX original · lines 171

```
# PART 0 — THE HOSPITAL (v2 skill-design picture, 2026-10-28; sits inside the friction frame)
```

### FIX original · lines 173

```
> *2026-10-30: the system-wide frame is **layers of friction**, see `canonical-principles-sop.md`, "The layers of friction". The hospital below is only the picture for designing a skill: its walls and its nurse are circles of friction, none of them perfect control.*
```

### FIX original · lines 177

```
1. The card and runner here are a bash prototype: cards are `id | kind | what | check` lines and the runner is about 150 lines of shell (see `<notes>/state/projects/orchestrator-v2/rig/`). It is not a product.
```

### FIX original · lines 192

```
- This qualifies, and does not refute, the LAW 1b nested-hang warning. Re-check per version.
```

### FIX original · lines 204

```
- `--json-schema` does not guarantee a valid shape (see the ⛔ SCHEMA entry in LAW 1b). So validate every time.
```

### FIX original · lines 222

```
## The default shape for any skill whose step order must hold  *(CANDIDATE)*
```

### FIX original · lines 232-234

```
- **Stage 2 (OBSERVED):** the checker caught **5/5** deliberate lies (rung 3: bad runs all failed at s2, no s3 line; good runs 15/15). Kill-and-resume **skipped the done steps and ran the rest exactly once**. A **3-way code-held fan-out** passed 5/5 (`examined=15 pass=15`), the checker having been watched failing first (`bad=1 good=0`).
- **What the rig found about itself:** the runner never checked a human answer (fixed; p06 "no" stopped, p07 "yes" completed); a hard kill leaves the lock (see the lock rule below); one of the 5 kill samples was not clean.
- **LAW 4.3's limit, stated plainly:** with K=10 runs, 95% detection reaches only failure rates of about **26% or more** (1 - 0.05^(1/10)). These are **pass@N counts, not rates.** Zero failures in 10 does not bound the true rate under ~26%.
```

### FIX original · lines 247

```
- **LAW 4.3 caveat:** fake clock and fake claude; these are **pass@N counts, not rates**, and the fake claude is not the real model. The 38/38 real-sonnet controls are small.
```

### FIX original · lines 249

```
- **Stage 5, on paper only (CANDIDATE):** emily-breakdown fits as 20 steps (14 code, 6 ai). The card cannot branch and cannot run two ai steps in parallel (see "When NOT to use a card" below). The live runners hide errors (see the new rules below).
```

### FIX original · lines 317

```
- **Limit 2, no parallel ai steps (CANDIDATE):** emily-breakdown's script-reader and researcher; planning-weekly's 4 + 9 + 6 = 19 AI calls would run in a row (council on Opus today, plan pins sonnet). Use a **code-held fan-out step** (the Stage 2 3-way fan-out passed 5/5, OBSERVED) and a card for each piece.
```

### FIX original · lines 478

```
   seam. **Human-facing simplicity is a design LAW** — never hand the user five skills where one door will do.
```

### FIX original · lines 487

```
   the other direction in 2026, see Law 3. Amended 2026-07-25: v1 said "never just claims done"; v2 names WHO may
```

### FIX original · lines 498

```
# PART I — WHAT HOLDS IN A STOCHASTIC ENVIRONMENT *(formerly "the laws of physics" — retitled 2026-09-05, REFINED; labels kept for cross-reference)*
```

### FIX original · lines 506

```
## LAW 1 — The Division of Labor: code owns the mechanical perimeter, the LLM owns judgment inside it
```

### FIX original · lines 533

```
> ⚠ *2026-09-05, single-source, NOT promoted:* one project measured 57 enforcement instances and found code failing
```

### FIX original · lines 535

```
> unresolved). It does not overturn this LAW; it says code that INFERS a judgment from a side-signal fails like prose
```

### FIX original · lines 571-573

```
>    a general law is what turned a 5,000-foot question into one skill's code.
> 4. ⚠ **Its own evidence table carried a false enforcement claim** — corrected in place above (the
>    `HUMAN_VERBS` row). That is §II.3's *"a claim of enforcement with no named test is a wish"* and the
```

### FIX original · lines 585

```
*(Not to be confused with **LAW 2's four seams**, which are the places intent leaks between what you designed and
```

### FIX original · lines 597

```
contact.** The split is total, and that is why this is a law and not a preference:
```

### FIX original · lines 603

```
| `HUMAN_VERBS` — MINE / TOSS / SAVE | `system/tools/cowork-ingest/pipeline.py` | held. ⚠ **CORRECTED 2026-08-05 — this row originally read *"`check_screens.py` enforces that no jargon leaks past them."* That was FALSE. `check_screens.py` has ZERO callers** (verified: the only references anywhere are this line, `skills/ingest/SPEC.md:567`, and the file's own docstring — no cron, no Pulse job, no hook, no test). It is §V.9's `Validator-exists-but-nothing-calls-it` — COMMITTED, never ENFORCED. **The author of this row asserted enforcement without checking for a runner, which is exactly the wish §II.3 names and the fourth logged instance of §V.4d.** `health_line.py:67` already records the same disease by name. The vocabulary held; nothing was guarding it. |
```

### FIX original · lines 628

```
LAW 1 divides the WORK between code and the model. This divides **a single tool's own job**, and it is the
```

### FIX original · lines 659

```
MENTIONS"* is the same disease one rung down, and by 2026-08-06 it had **three logged instances** (the
```

### FIX original · lines 667

```
  That is **LAW 4.1** — completeness against a source the model cannot hold — and it is structurally unavailable,
```

### FIX original · lines 680

```
where the bugs are, which is why it needs a law of its own.**
```

### FIX original · lines 689

```
### ⭐ LAW 1b — THE SECOND AXIS: **MODEL-REACH**. A closed vocabulary says WHAT crosses the seam. It says nothing about whether the seam is REACHABLE AT ALL.
```

### FIX original · lines 691

```
> **Added 2026-08-05, from a live failure + four measurements.** LAW 1 is about the *contents* of the
```

### FIX original · lines 707

```
| **HEADLESS** | a script shells `claude -p` | ✅ yes — **with the two fixes below** | ⛔ no |
```

### FIX original · lines 712

```
- **NEW RULE — a session-reach step receives its inputs as FILES written by a code step, or it cannot run under a runner.** A step whose reach is SESSION (e.g. `/save` reading the live conversation or armed flags) has nothing to read once a runner owns the order; a code step must first write what it needs to disk. *(CANDIDATE — awaits the week-long /save test.)*
```

### FIX original · lines 715

```
**⛔ LAW: A SEAM WHOSE ONLY REACH IS `SESSION` DOES NOT EXIST IN CRON.** Write that in the artifact, or a
```

### FIX original · lines 762

```
**⭐⭐ THE LAW THAT MATTERS MOST — AN UNREACHABLE MODEL IS NOT A CLEAN RESULT.**
```

### FIX original · lines 767

```
`NO OUTCOME WAS REACHED` member — NEVER onto the clean member.** This is LAW 1's required member doing its
```

### FIX original · lines 772

```
this is our own law, said better:** *"An instrument that cannot distinguish 'nothing there' from 'I was not
```

### FIX original · lines 788

```
## LAW 2 — Intent leaks at four seams; diagnose WHICH one before you fix anything
```

### FIX original · lines 825

```
the stack did not.
```

### FIX original · lines 827

```
> **STACK** level rather than the **CHECK** level.
```

### FIX original · lines 835

```
window filled) plus one structural impossibility (completeness in prose — Law 4).
```

### FIX original · lines 840

```
## LAW 3 — Never let the actor grade its own completion
```

### FIX original · lines 871

```
- **NEW RULE — the AI never writes the record; only the runner does.** The model produces a step's output file; the runner runs the check and writes the record line. *(OBSERVED — also see §V.9.)*
```

### FIX original · lines 880

```
## LAW 4 — Three things an LLM structurally CANNOT do
```

### FIX original · lines 908

```
   - ⭐ **HOW TO CHOOSE K — added 2026-09-11, because this law mandated sampling and never said how many.**
```

### FIX original · lines 926

```
## LAW 5 — Prose decays, and the decay is measured
```

### FIX original · lines 928

```
This is *why* Laws 1–4 exist. A cold session should know these numbers:
```

### FIX original · lines 948

```
# PART II — THE ENFORCEMENT TOOLBOX
```

### FIX original · lines 950

```
> How to obey the laws. Everything here is small plain scripts and existing harness features — **no framework**.
```

### FIX original · lines 963-964

```
- **(b) Deterministic enforcement layer** — hooks, guards, validators, schema checks; where invariants live
  because code can't be talked out of them. **Dominant failure: over- or under-gated** (§II.3's ladder).
```

### FIX original · lines 980-982

```
| **(a) Reasoning** | a **blind, K-voted LLM judge** (Law 4.3 fold) | The property is prose-shaped — no script can read for intent. But a single sample lies, so the verdict is voted and fail-closed. ⚠ **AMENDED 2026-08-07** (the rulebook was over-prescriptive here, not the swarm; amended in place, the rule survives): K-voting earns its cost **wherever a missed finding is expensive and a false negative would be invisible** — a completeness or security clause nobody will re-check by hand; **a single blind pass is enough** where a miss is cheap to catch downstream or the property is low-stakes. The reason is Law 4.3's own measurement `[M: 2 runs, 4 clauses]`: one clause judged five times on byte-identical input returned `violated · violated · violated · violated · met`. Counter-evidence that a second pass earns its keep, not noise: this skill-builder's own tension swarm, 2026-08-06 — of 42 candidates, 17 surfaced blind on the first pass, +3 more on a second look, 25 rejected, and **those 3 were unreachable on the first pass — 15% of every finding came from re-reading.** ⚠ **"Blind" is a claim you must MEASURE, not assume — see §V.4a.** A judge launched from a neutral cwd is *not* blind; `claude -p` auto-discovers `~/.claude/CLAUDE.md` from anywhere. |
| **(b) Enforcement** | **provoke the guard and assert** — fire the faithful forbidden action, require it BLOCKED; fire the allowed twin, require it passes | A guard that was never provoked is untested. Its mere presence in `settings.json` proves nothing about whether it fires. |
| **(c) State** | a **native-id SET-DIFF vs the source** (Law 4.1) | A model cannot verify completeness against a source it cannot hold — it grades the *claim*. Only a mechanical diff grades the *thing*. |
```

### FIX original · lines 992-994

```
## §II.1a — ~~Compliance is a STACK, not a rung to pick~~ Compliance is the center of the Venn diagram, not a rung to pick *(added 2026-09-05, OBSERVED; heading reworded 2026-10-30)*

> *2026-10-30: read "stack" below as overlapping circles of friction. Frame: `canonical-principles-sop.md`, "The layers of friction". The observed catches are unchanged.*
```

### FIX original · lines 1000-1001

```
> enforcement zero. Local receipts this week: a commit guard blocked a correct commit over a flag named in the
> message; the repo signpost misread the repo under `cd`. The stack still holds; the top of it has a cost side.
```

### FIX original · lines 1003-1004

```
The families below and the ladder in §II.3 read as "choose one." The observed truth is that each layer catches
what the one above misses, and the design is to **stack** them, sized to the stakes. One build, three layers,
```

### FIX original · lines 1009

```
first thing reached for. *(Receipts: `V2` commits 2026-09-04; `<notes>/state/autoplan-rebuild/`.)*
```

### FIX original · lines 1017

```
pipeline (Law 1's fence).
```

### FIX original · lines 1032

```
DECAY (Law 2, link 3)** — no gate can. Free, and nothing for a student to install. *(Our own bet — see PART IV.)*
```

### FIX original · lines 1036-1037

```
Law 5 says prose decays; these are the specific mechanisms, and each one names its own counter. Know them, because
they tell you *which* rung the rule needs.
```

### FIX original · lines 1051

```
  of a long file is functionally absent by the time the action happens (Law 5's edges-not-middle, applied locally).
```

### FIX original · lines 1053

```
## §II.3 — The reliability ladder (how hard to gate — the Verify/Wall dial)
```

### FIX original · lines 1055

```
Use the least rung that **holds**. Rung choice IS the right-sizing decision; don't over-gate a low-stakes style
```

### FIX original · lines 1058

```
1. **Self-reported marker** ("GATE CLEARED") — *fakeable.* Orientation only, **never a guarantee** (Law 4.2).
```

### FIX original · lines 1062

```
   self-attestation — rung 1 wearing rung 2's clothes. §V.4b.)*
```

### FIX original · lines 1071-1074

```
**The ESCALATION LADDER (when a rule keeps losing):** reword ❌ → **binary gate** → **the user-turn boundary**.
~~The user-turn boundary is the only truly unbypassable gate, and the **"say go" HARD-STOP is the most
reliably-held gate type there is `[R]`** — use it at every real pause point, and **spend it sparingly**: each one~~
costs the user a tap, and a skill that stops six times gets skipped entirely.
```

### FIX original · lines 1078-1079

```
- **NEW RULE — code reads the human's answer and refuses anything but an explicit yes.** The runner stores the question, reads the reply, and proceeds only on yes; any other reply fails the step. *(OBSERVED — p06 "no" stopped at s3, p07 "yes" completed.)* Also applies at §V.4b.
- **NEW RULE — the record has a distinct `waiting` state, separate from `fail`.** A run paused for a human is neither passing nor failing; collapsing the two hides either a stuck run or a broken one. *(OBSERVED — rungs 4+5: `waiting=11`, then 13, with `fail` counted apart.)*
```

### FIX original · lines 1083-1084

```
  model — re-run the test when the tier changes. "The least rung that holds" is never permanent.
- **Blast-radius scaling** `[C]`: as stakes and autonomy rise, the enforcement bar rises with them — the
```

### FIX original · lines 1087

```
- **Instantiate the existing enforcement infra** (proof-not-ask, Stop hooks, capture gates) — never author a
```

### FIX original · lines 1092

```
- **Name the mechanism + the test, or it's prose.** A claim of enforcement ("by construction," "the skill
```

### FIX original · lines 1097

```
  upgrade; prose may not. **The LLM is swappable; the enforcement seam holds.** This is the durable "why" behind
```

### FIX original · lines 1102

```
  reasoning and the guard. It is non-deterministic by definition (Law 4.3), so it is **never the primary gate**;
```

### FIX original · lines 1109

```
known-good, or it isn't trusted — Law 4.3 applied to our own tools). The law behind the tax: **a gate that
```

### FIX original · lines 1157

```
  "reviewer persona" in the same window. Law 3, implemented structurally.
```

### FIX original · lines 1174-1175

```
> Method and provenance: `records/research/2026-09-05-failure-mode-census.md` ⛔ (owner's notes). Receipts:
> `state/failure-census-2026-09-05/` ⛔ (owner's notes). Canon §16 carries the same modes as principles;
```

### FIX original · lines 1262-1264

```
  2026-09-07 amendment). Receipt: `state/experiments/coordinator/mode-15-draft.md` ⛔ (records in the owner's
  notes) and `state/experiments/coordinator/defects-2026-09-07.md` ⛔ (records in the owner's notes) rows 10-11
  (fix landed as commit `d6a1afa`). ·
```

### FIX original · lines 1323

```
  says must be DELETED.** Receipt: canon `records/canon/2026-09-02-canonical-principles.md` §16 mode 19, §17.26
```

### FIX original · lines 1335

```
> baselines · a semantic classifier behind every guard (also contradicts LAW 3 — held as dissent) · runtime tracing with dashboards ·
```

### FIX original · lines 1354-1355

```
> the second also collides with LAW 3 — a model may annotate a verdict, never be it, per canon §4.11).
> **RESOLVED 2026-09-06 (Enver, canon §12.f):** verification is layers, ranked by independence from the actor — the same window re-reading its own work is the weakest; a separate window on the same model is a real layer and has caught a great deal here; a separate window on a different model family is stronger; a deterministic code check is strongest for well-formed and cannot tell wrong. None is yes or no; each catches what the one beneath it missed. The one shape the evidence warns against is a second model with a deciding vote — it annotates, and the human or the code decides. LAW 3 only says the actor may not declare its own work done; a different window checking is LAW 3 working, not a collision.
```

### FIX original · lines 1426

```
- **[B7]** Tried: polite prompt instructions as enforcement gates in a skill. Failed: "the AI reasons past
```

### FIX original · lines 1431

```
  prose reminder is what **LAW 3 above already names checkbox theater** (cross-ref, not restated). `2026-06-20`
```

### FIX original · lines 1448

```
  re-read" rule (cross-ref, line ~1182). `2026-06-28` · `records/2026-07-13-translator-voice-debug-history.md`
```

### FIX original · lines 1455-1456

```
  §III.4's "too cheap loses intuition"** (cross-ref, line 954), also cited by name in global CLAUDE.md's
  Subagent Model Selection. `2026-07-11, reverted at commit 779157c` ·
```

### FIX original · lines 1521

```
> **This cluster restates existing doctrine — §II.3's reliability ladder ("use the least rung that holds")
```

### FIX original · lines 1528

```
  told in full in PART I's `⭐ THE SEAM` ERODED table** (line ~164: `corpus_map.py`, commit `b110722`) —
```

### FIX original · lines 1548

```
this stays the complete lookup, not filed under LOCAL where their binding scope would be misrepresented.
```

### FIX original · lines 1567

```
  section already cites by name as one of three logged instances** (cross-ref, line ~213) — not restated.
```

### FIX original · lines 1572

```
  PRINTING, COUNTING, COMPARING and REFUSING are not" section exists to state** (cross-ref, line ~175) — not
```

### FIX original · lines 1581

```
  fragment the guard set" — **§II.3 already says this verbatim** (cross-ref, line ~538), not restated.
```

### FIX original · lines 1753

```
  (2026-09-05) carried three wrong claims — a block "with no analogue" that duplicated LAW 1b · "3× the length"
```

### FIX original · lines 1790

```
## §II.7 — ⏸ HELD hypothesis: the demand-class law (NOT yet doctrine)
```

### FIX original · lines 1794

```
true, the demand-class should drive rung choice at design time — the single most useful thing we could know.
```

### FIX original · lines 1805-1806

```
> Laws in PART I and reaches for the toolbox in PART II; where a step needs enforcement, it names the family
> (Replace/Verify/Wall/Refresh, §II.1) and the rung (§II.2) rather than re-deriving them.
```

### FIX original · lines 1815

```
held to the full skill machinery (three floors, enforcement ladder, receipts, anchoring, state files). It escalates
```

### FIX original · lines 1820

```
- **leading/interrogative** (it must hold its frame against the user, PART I Law 5's "social pull")
```

### FIX original · lines 1825-1826

```
right-sizing trait); a skill wearing command lightness silently drops the anchoring and enforcement it needed and
fails exactly the way PART I Law 5 predicts.
```

### FIX original · lines 1864

```
- **NEW RULE — card + runner + record is the default shape for any skill whose step order must hold.** Classify with this in mind (§III.1): if order matters, the skill gets a card, a runner and a record (see PART 0). *(CANDIDATE.)*
```

### FIX original · lines 1872

```
prevents. This is `intent-doctrine.md`'s system-wide law ("every object declares why it exists") applied to
```

### FIX original · lines 1887

```
  what makes it do the work *well*, §0 trait 6) and HOW it carries the work (how it leads and holds its lane, Law
```

### FIX original · lines 1945

```
  skill) — and re-run them whenever you touch the description. **Fold per Law 4.3: run each case 3+ times.**
```

### FIX original · lines 1952-1953

```
Applies Law 1 (mechanics vs judgment) and Law 5 (decay) to the shape of the skill itself, not just its
enforcement:
```

### FIX original · lines 1959

```
  guardrail-to-handcuff, Law 1) and kill the adaptive follow-up a leading/interrogative skill needs. Minimum-viable
```

### FIX original · lines 1975

```
  (Law 5); collapsing state into ONE fresh call recovers near single-turn quality where mid-thread reminders do
```

### FIX original · lines 1982

```
- **Gate the deterministic steps; leave the judgment steps free. `[R]`** This is Law 1's fence in flow-design
```

### FIX original · lines 1992

```
- **NEW RULE (§III.4) — design the flow as card + runner + record by default** when order must hold: ordered steps of kind code/ai/human, each with a check; one shared runner; an append-only runner-written record. *(CANDIDATE.)*
```

### FIX original · lines 2007

```
  itself is the signal (§II.5): `scripts/` = run it, `references/` = read it into context when needed, `assets/`
```

### FIX original · lines 2030

```
- **The 3-rung tooling ladder for rules themselves** (distinct from the runtime reliability ladder, §II.2): a rule
```

### FIX original · lines 2032

```
  skill is born with it, **(c)** a guard hook that blocks a skill missing it. Use the lowest rung that holds;
```

### FIX original · lines 2038

```
## III.7 — The spec-diff gate: catch Law 2's link 1 before you ever run the thing
```

### FIX original · lines 2044

```
This is the **only** detector for Law 2's link 1 (SPEC → SKILL FILE) — an authoring loss, invisible at runtime by
```

### FIX original · lines 2075

```
cannot trust to report on it (LAW 4.2). No gate can see it and no prose can guarantee it. So we did not gate it:
```

### FIX original · lines 2082

```
injection the regex scan had already cleared (`~/.claude/CLAUDE.md` → Subagent Model Selection §2a). **Upgrading
```

### FIX original · lines 2085-2086

```
⛔ `agents/ingest-reader.md` is the donor's path and is not here. The reader itself DID land — it ships as
`.claude/agents/ingest-reader.md`; only the top-level `agents/` location did not come across (migration note, 2026-08-15).
```

### FIX original · lines 2091

```
> The handoff between the first two is a **closed vocabulary** (LAW 1 → `⭐ THE SEAM`).
```

### FIX original · lines 2099

```
`skills/ingest/SPEC.md` §6 is a live worked backlog of exactly this: **seven** rules already named
```

### FIX original · lines 2103

```
LAW 4.2 wearing a gate's clothes, and a fake gate is worse than no gate, because it stops anyone looking.
```

### FIX original · lines 2112

```
  again, **stop rewording** — the second failure is evidence the rule is at the wrong rung (§II.3) or the flow
```

### FIX original · lines 2114

```
- **Mine transcripts with sonnet subagents.** Reading your own run logs by hand doesn't scale, and the main
```

### FIX original · lines 2119

```
## III.10 — Close: the per-rule enforcement decision
```

### FIX original · lines 2126

```
  it as a §II.3 primitive at the rung §II.2 calls for. This is Law 1's division of labor made concrete: if code can
```

### FIX original · lines 2177

```
> as the turns pile up. Law 5 already gave you the numbers (density, duration, turns, position, social pull,
```

### FIX original · lines 2187

```
says — this is Law 5's social-pull bullet, stated as a design consequence: it gets *worse* the longer the session
```

### FIX original · lines 2227-2229

```
**The Path Beat is orientation, not proof** — ladder rung 1 (Part II §II.2: self-reported marker, fakeable). A
~~plain model-written banner is fine for a simple skill; where a receipts file already exists, *prefer* printing the
banner from it — a design preference, not a per-turn runtime gate.~~
```

### FIX original · lines 2235-2236

```
time (Law 4.2, "knows-but-violates"). Declarative recall is not behavioral adherence. **Never treat a
restatement or a banner as a gate** — real enforcement is Part II's Verify/Wall families, not this layer.
```

### FIX original · lines 2241

```
This is Law 5's position bullet applied to placement: recall of a mid-context instruction collapses to ~55%
```

### FIX original · lines 2271-2272

```
~~> **REFINED 2026-09-05 (solutions audit, `records/research/2026-09-05-durable-solutions-audit.md` ⛔ owner's notes):** the
> per-step prompt is *a habit, not a solution.* Inside `/checkin`, already built per-step, prose-backed steps were skipped~~
```

### FIX original · lines 2276

```
> **Hand state, not history** *(new rule, CANDIDATE)*: what a fresh agent is handed is the current state (where things stand) and its one next step, written by the runner — never the transcript of how it got there.
```

### FIX original · lines 2278-2280

```
> a THIRD time while tool-backed steps ran — delivery held constant, only the exit code varied (J5-144, 2026-08-15). What
> holds is the external check with an exit code. Keep the per-step shape for the reasons above (short context, one
> job per prompt); do not count on it for compliance. Every step that must happen gets a tool with an exit code.
```

### FIX original · lines 2292

```
doing anything else — compaction is exactly the event Law 5's "turns" bullet describes, and it's the single
```

### FIX original · lines 2309

```
> **v2 (orchestrator-v2, 2026-10-28):** Order that must hold is held by a runner, whatever the run's length — a 5-step linear run still gets the card and the runner if its order matters. External state beyond the record is still for long or headless runs. *(CANDIDATE.)*
```

### FIX original · lines 2313

```
2. **Does this particular gate MATTER?** Scale the proof to the stakes using Part II §II.2's reliability ladder
```

### FIX original · lines 2320

```
> **v2 (orchestrator-v2, 2026-10-28):** The runner writes one record line per step as each step finishes (run, step, status, utc, output path, reason); the skill never emits its own receipt, because a receipt the actor emits is the actor grading itself (LAW 3). *(OBSERVED — 10+10 runs, every line runner-written; brief §4 Stage 1.)*
```

### FIX original · lines 2328

```
> **v2 (orchestrator-v2, 2026-10-28):** We do not need an engine. Any multi-step skill whose order must hold gets a **card** (ordered steps, each with a check), a **runner** (one shared script) and a **record** (append-only, runner-written) — a script, not a workflow engine, and "rigid state machine" is the wrong description of it. *(CANDIDATE: one skill; awaits the week-long /save-on-a-card test and a second skill, per [P2]. Rig: Stage 1 and 2 scorer lines, orchestrator-v2 brief §2/§4.)*
```

### FIX original · lines 2352-2354

```
- **CLI-only — does NOT port to Cowork.** Unlike the Part II §II.4 primitives (skill-local scripts, portable by
  design), this mechanism is a CLI status-bar feature with no Cowork equivalent — don't design a Cowork-facing
  skill around it.
```

### FIX original · lines 2373

```
  Law 3's "never let the actor grade its own completion" applied to a fan-out: the spine is the thing that isn't
```

### FIX original · lines 2376

```
- **Hand the panel FILES, not history.** Cross-ref Part II §II.3's artifact-file handoff: briefs, seeds, and
```

### FIX original · lines 2394

```
The rationale is Law 5's own "turns" bullet, taken at face value: multi-turn sessions degrade ~39% measured, and
```

### FIX original · lines 2397

```
(Law 2, link 3 — FIRED → HELD) — no Verify script and no Wall hook can reach decay, because decay isn't a
```

### FIX original · lines 2401

```
**Mark this honestly: it is a bet, not a Law.** It did **not** surface in the 2026-07-25 crowd-convergence or
```

### FIX original · lines 2404

```
it next to Part II §II.6's held hypotheses: consistent with everything we've measured, not yet doctrine.
```

### FIX original · lines 2424

```
Law 2 (PART I) names four seams where intent leaks. Each needs a **different** detector — running the wrong one
```

### FIX original · lines 2430

```
| **2. FILE → FIRED** | a written rule the session breaks anyway | grade a real run against the spec with a **VOTED** judge (K-sample, fail-closed fold — Law 4.3) | 2 confirmed real deltas on planning-weekly, after the instrument itself was fixed twice |
```

### FIX original · lines 2432-2433

```
| **4. HELD → PROVABLE** | a rule obeyed but left no trace | name each rule's evidence surface **before grading**, not after (§II below) | confirmed: purely-conversational rules graded as failures for no reason but the tester's own blind spot |
| **5. DETECTOR → STILL RUNNING** ⭐ | **the instrument itself went dark** — ⛔ **defined in LAW 2, not restated here** | *when did this last produce output, and does it still fire on a deliberate break?* (LAW 2) | ⛔ **UNMEASURED.** Known instances only: a failed hook script reporting only to debug · invalid stdout silently dropped · a matcher aimed at a tool the work no longer uses · hooks not firing on **sub-agent tool calls**. ⚠ **AMENDED 2026-09-12:** *"hooks silent after ~2.5h with zero error"* **STRUCK** — its source (`#16047`) is one Windows-only CLOSED report and does not apply here; see LAW 2. **None of the survivors is time-bounded, so there is no safe session length.** **No liveness answer exists for this harness's own detector fleet.** |
```

### FIX original · lines 2435

```
⚠ **THIS TABLE IS A STATUS VIEW OF LAW 2'S LOSS-CHAIN — LAW 2 DEFINES THE LINKS; THIS SECTION SAYS ONLY WHERE
```

### FIX original · lines 2440

```
⭐ **COMBINATION TESTING — also defined in LAW 2.** Status here: **never run.** Every detector in this system
```

### FIX original · lines 2502

```
can enforce was holding Lifehack' own enforcement doctrine while deciding.** Three attempts to isolate it by
```

### FIX original · lines 2508

```
full hook stack or you are testing a fiction. It was then applied to the **judge**, which sits on the opposite
```

### FIX original · lines 2551-2552

```
`[M: 2026-07-28, first hostile sweep of our own parts library]` This is **Law 3's loophole**, and it is the
single most productive rule we have found. Law 3 forbids the actor from *grading* its own completion. It does
```

### FIX original · lines 2571

```
- **NEW RULE (see §II.3) — code reads the human's answer and refuses anything but an explicit yes.** A gate on a human's reply verifies the evidence (the reply) not the form of the claim that one was asked for. *(OBSERVED.)*
```

### FIX original · lines 2602

```
  Law 4.1's *pin the denominator first* missing from the WRITE path. Second run: it mapped a case-blind rule
```

### FIX original · lines 2609

```
- **NEW RULE — when testing a kill, verify the kill landed before the step you meant to interrupt.** One of 5 kill samples (k01) landed after the runner had already reached s3, so it was not a clean sample (4 clean of 5). Read the record to confirm where the kill fell before counting it. *(OBSERVED.)*
```

### FIX original · lines 2658

```
This is the verification twin of Law 2: a per-component pass proves the component works, not that its output
```

### FIX original · lines 2747-2749

```
  ENFORCED. Exactly the gap Law 3 exists to close.
- **A record the AI writes.** The model-written ledger is the anti-pattern above; the v2 form is that the runner writes the record and the AI never does (LAW 3 NEW RULE). *(OBSERVED.)*
- **An LLM judge sold as a deterministic test.** *(Our inference from Law 4.3 — NOT an observed anti-pattern in
```

### FIX original · lines 2793

```
- **NEW RULE — hand state, not history.** See §IV.6 note and the rule above: the unit of handoff is state plus the one next step. *(CANDIDATE.)*
```

### FIX original · lines 2817

```
  the answer — the content-level twin of Law 5's social-pull decay. Give it the **domain**, never the
```

### FIX original · lines 2847

```
  a gate can't do better — but where prose genuinely is the right rung (a judgment call, not a mechanic), it's
```

### FIX original · lines 2859

```
Sub-agents run **sonnet unless the subagent is specifically designed to run something else** — never the top
```

### FIX original · lines 2886

```
- **The demand-class law.** Rules that demand the model **produce** something appear to hold in prose; rules
```

### FIX original · lines 2888

```
  enforcement-rung choice at design time — potentially the single most useful thing we could know. Currently
```

### FIX original · lines 2901

```
to make this reusable doctrine rather than one project's finding.** Two laws, in rank order. The first is the
```

### FIX original · lines 2904

```
### ⭐⭐⭐⭐ LAW A — SUBTRACT FIRST. The loudest phase is not automatically the reachable one.
```

### FIX original · lines 2926

```
### ⭐⭐⭐ LAW B — PRICE EVERY LAYER THAT ISN'T DOING THE WORK. A handoff costs time even when it does nothing.
```

### FIX original · lines 2943

```
### ⭐⭐ LAW C — WALL CLOCK AND HUMAN-WAITING TIME ARE DIFFERENT TARGETS, AND ONLY ONE OF THEM IS THE JOB
```

### FIX original · lines 2956-2958

```
**Living intake.** `system/sops/skill-irl-findings.md` is where new observations land first, append-only,
chronological, tagged TESTER / SKILL / METHOD. When a finding is seen enough to be durably true, it graduates
here and gets marked. Companion for operational specifics: `skill-building-field-notes.md` *(your personal code folder; not shipped in the plugin)*.
```

### FIX original · lines 2970-2974

```
> The frontmatter names `system/sops/skill-irl-findings.md` as where observations land before they graduate
> into this file. **That file does not exist in either repository (checked 2026-09-05).** Until it does,
> candidates land here, in this section, clearly marked. Nothing below is a rule. Each carries the canon's
> confidence tier, its receipt, and what would refute it. **Per Enver 2026-09-05: write principles with
> their reason; a rule only where it is 100% — a harness fact or a mechanical refusal.**
```

### FIX original · lines 3041

```
  relative, no loss of task success (one benchmark family). RESEARCHED. *This is LAW 1's fence and canon §4.6's
```

### FIX original · lines 3046

```
  RESEARCHED, thin. *This is LAW 3.*
```

### FIX original · lines 3051

```
  HAL; CSET), no rebuttal. *Outside support for THE FRAME's one law and for stacking (§II.1a).*
```



## 2026-10-30 — validation fix

Reason per entry. Verbatim text removed or replaced from the edited SOP.

### validation fix 2026-10-30 · edited line 1078 · private repo name and counts removed (leak)

```
  `origin/V2`; `ClaudeOps`: 21 local, `main` 14 ahead. · **Field remedy (RESEARCHED):** `fetch.prune=true` plus
```

### validation fix 2026-10-30 · edited line 1096 · private repo name removed (leak)

```
  — direct branch-content audit, private `egjokaj/ClaudeOps`, 2026-09-08: 20 `ship/*`/`land/*` branches, 211
```

### validation fix 2026-10-30 · edited line 1400 · private window name removed

```
  re-run by this window~~ receipt named: claudeops-1a's transcript audit, entry A10 — four `rc=` values in one
```

### validation fix 2026-10-30 · edited line 2589 · private window name removed

```
**THE SCOPE FAILURE — added 2026-09-05 by nav claudeops-1a at Enver's instruction. CANDIDATE, NOT VALIDATED.**
```

### validation fix 2026-10-30 · edited line 962 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  → *Research pass 2026-09-05:* **No field remedy** — class-level liveness/reachability sweeps exist for conventional code, none for hooks/skills/tools → experiment (unused-parts-drifting-copies). ⛔ (records in the owner's notes) · Category: **architectural** (canon §16 mode 1, 2026-09-08 retrofit) · **CANDIDATE** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; no field remedy, never held here)
```

### validation fix 2026-10-30 · edited line 966 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  → *Research pass 2026-09-05:* **Field remedy (RESEARCHED):** independent output-shape/baseline verification + heartbeat monitoring — emerging-to-strong (n8n community forum) (lying-signals-text-guards). ⛔ (records in the owner's notes) ✅ ADOPTED (right-size audit 2026-09-05) · Category: **architectural** (canon §16 mode 2, 2026-09-08 retrofit) · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; field remedy also noted)
```

### validation fix 2026-10-30 · edited line 975 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  → *Research pass 2026-09-05:* **No field remedy** — generate-from-source is proven for docs/config, not for arbitrary duplicated facts in a harness repo → experiment (unused-parts-drifting-copies). ⛔ (records in the owner's notes) · Category: **both** (canon §16 mode 3, 2026-09-08 retrofit) · **CANDIDATE** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; no field remedy, never held here)
```

### validation fix 2026-10-30 · edited line 979 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  → *Research pass 2026-09-05 (second pass, the five modes):* **Field remedy (RESEARCHED):** checker independent in author, code path, and data source from what it checks — strong, decades-old cross-industry convergence (verification-not-by-the-actor; Skalse 2022 / ISO segregation-of-duties). ✅ ADOPTED (right-size audit, second pass, 2026-09-05) ⛔ (records in the owner's notes) · Category: **architectural** (canon §16 mode 4, 2026-09-08 retrofit) · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; field remedy also noted)
```

### validation fix 2026-10-30 · edited line 985 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  → *Research pass 2026-09-05 (second pass, the five modes):* **No field remedy** — field's answer (plan-first/spec-gating) is the same prose-ceremony shape that already failed 7x locally; METR's RCT shows added process can cost without payoff → experiment (premises-and-numbers-checked-first). ⛔ (records in the owner's notes) · Category: **operational** (canon §16 mode 5, 2026-09-08 retrofit) · **CANDIDATE** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; no field remedy, never held here)
```

### validation fix 2026-10-30 · edited line 989 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  → *Research pass 2026-09-05:* **No field remedy** — artifact-over-summary is exactly what local already tried at one site and it fails partially applied → experiment (values-that-did-not-travel). ⛔ (records in the owner's notes) ✅ ADOPTED (right-size audit 2026-09-05) — the field's strongest mechanism; PARTIAL here, see canon §12.c · Category: **operational** (canon §16 mode 6, 2026-09-08 retrofit) · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; field remedy also noted)
```

### validation fix 2026-10-30 · edited line 993 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  → *Research pass 2026-09-05:* **Field remedy (RESEARCHED):** layered guard — typed parsing + narrow regex triage + semantic classifier — strong (arXiv:2506.10597, IEEE S&P 2026) (lying-signals-text-guards). ⛔ (records in the owner's notes) ✅ ADOPTED (right-size audit 2026-09-05) · Category: **architectural** (canon §16 mode 7, 2026-09-08 retrofit) · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; field remedy also noted)
```

### validation fix 2026-10-30 · edited line 997 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  → *Research pass 2026-09-05 (second pass, the five modes):* **Field remedy (RESEARCHED):** never trust a worker's self-produced proof — poll a pre-agreed, orchestrator-checked landmark fixed before delegation — strong (verification-not-by-the-actor; hexisteme.github.io postmortem). ✅ ADOPTED (right-size audit, second pass, 2026-09-05) ⛔ (records in the owner's notes) · Category: **operational** (canon §16 mode 8, 2026-09-08 retrofit) · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; field remedy also noted)
```

### validation fix 2026-10-30 · edited line 1003 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  → *Research pass 2026-09-05 (second pass, the five modes):* **No field remedy** — reproducibility science's recompute-from-source norm is off-domain inference only; the STALE benchmark confirms detecting stale facts is unsolved → experiment (premises-and-numbers-checked-first). ⛔ (records in the owner's notes) · Category: **operational** (canon §16 mode 9, 2026-09-08 retrofit) · **CANDIDATE** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; no field remedy, never held here)
```

### validation fix 2026-10-30 · edited line 1007 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  → *Research pass 2026-09-05:* **Field remedy (RESEARCHED):** fail-loud unique-context-anchored search/replace, optionally hash-augmented — strong (wuu73.org cross-tool survey) (wrong-target-edited-or-run). ⛔ (records in the owner's notes) ✅ ADOPTED (right-size audit 2026-09-05) · Category: **both** (canon §16 mode 10, 2026-09-08 retrofit) · **RESEARCHED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; field remedy, never held here)
```

### validation fix 2026-10-30 · edited line 1011 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  → *Research pass 2026-09-05 (second pass, the five modes):* **Field remedy (RESEARCHED):** move must-always rules into deterministic hooks/tool gates, keep prose for judgment calls only — strong, three independent communities converge (rules-with-teeth; Claude Code hooks docs). ✅ ADOPTED — a receipt on hook-plane doctrine and point-of-need injection (2026-09-05) ⛔ (records in the owner's notes) · Category: **architectural** (canon §16 mode 11, 2026-09-08 retrofit) · **RESEARCHED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; field remedy, never held here)
```

### validation fix 2026-10-30 · edited line 1017 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  → *Research pass 2026-09-05:* **No field remedy** — content-addressed/hash verification matches local's own one-pair fix, but no source generalizes it to a harness's full file set → experiment (wrong-target-edited-or-run). ⛔ (records in the owner's notes) · Category: **architectural** (canon §16 mode 12, 2026-09-08 retrofit) · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; no field remedy)
```

### validation fix 2026-10-30 · edited line 1021 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  → *Research pass 2026-09-05:* **No field remedy** — consumer-driven contract testing is mature for microservices, never adapted to LLM output anywhere → experiment (values-that-did-not-travel). ⛔ (records in the owner's notes)
```

### validation fix 2026-10-30 · edited line 1105 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
> **Right-size audit, 2026-09-05** *(Enver's rule is in THE FRAME; record: `records/research/2026-09-05-remedy-right-size-audit.md` ⛔ owner's notes).*
```

### validation fix 2026-10-30 · edited line 1171 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  `state/projects/security/security-hardening/brief.md:44-77` → `exit 2`.
```

### validation fix 2026-10-30 · edited line 1173 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  level** — measured, no effect. `NO-DATE` · `state/projects/skill-system/brief.md:122-136` → abandoned.
```

### validation fix 2026-10-30 · edited line 1176 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  `state/projects/skill-system/brief.md:302-407` → put trigger text in `description:`. *(This SOP's §III.3
```

### validation fix 2026-10-30 · edited line 1181 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  `state/projects/skill-system/brief.md:302-407` → always double-quote `description:`.
```

### validation fix 2026-10-30 · edited line 1184 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  `2026-05-30` · `state/projects/security/security-hardening/brief.md:44-77` → `INPUT=$(cat)`.
```

### validation fix 2026-10-30 · edited line 1187 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  `state/projects/ingest-skill/brief.md:147-172` → spawn as plain background agents. **Fired live again
```

### validation fix 2026-10-30 · edited line 1199 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  prose gates." `NO-DATE` · `state/projects/lifehack-cowork/brief.md:280-298` → external bash
```

### validation fix 2026-10-30 · edited line 1204 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  · `state/projects/infrastructure/lifehack-correct-architecture/brief.md:351-390` → a slim
```

### validation fix 2026-10-30 · edited line 1209 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  `state/projects/translator-voice/brief.md:97-122` → a word/section budget instead of a rule.
```

### validation fix 2026-10-30 · edited line 1233 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  `state/projects/cowork-bulk-ingestion/brief.md:83-87` → sonnet + ≥10k-char slice.
```

### validation fix 2026-10-30 · edited line 1250 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  `state/projects/skill-system/brief.md` (wave B1) → kept four separate lens agents.
```

### validation fix 2026-10-30 · edited line 1253 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  reported output. `2026-08-05` · `state/projects/skill-system/brief.md` (wave S) → abandoned as a speed
```

### validation fix 2026-10-30 · edited line 1256 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  worse** wall-clock. `2026-08-04` · `state/projects/skill-system/brief.md:409-473` → kept the fan-out.
```

### validation fix 2026-10-30 · edited line 1259 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  tokens at roughly 100x the input price. `2026-08-04` · `state/projects/skill-system/brief.md:409-473` →
```

### validation fix 2026-10-30 · edited line 1268 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  deterministic test"). `2026-07-29` · `state/projects/skill-system/brief.md:1349-1351` → killed,
```

### validation fix 2026-10-30 · edited line 1273 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  bed") already state (cross-ref). `NO-DATE` · `state/projects/ingest-skill/brief.md:147-172` → verify
```

### validation fix 2026-10-30 · edited line 1288 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  `2026-08-05` · `state/projects/skill-system/brief.md` (wave B1) → rewrite the dispatch as "you personally
```

### validation fix 2026-10-30 · edited line 1301 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  cross-ref only, not restated. `2026-08-04` · `state/projects/ingest-skill/brief.md:147-172` → converted to
```

### validation fix 2026-10-30 · edited line 1305 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  written to prevent. `2026-08-04` · `state/projects/ingest-skill/brief.md:147-172` → guidance that carries
```

### validation fix 2026-10-30 · edited line 1309 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  · `state/projects/ingest-skill/brief.md:147-172` → plain reflowing text.
```

### validation fix 2026-10-30 · edited line 1312 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  `state/projects/skill-builder/brief.md:100-110` → the grid stays the LLM's own completeness check.
```

### validation fix 2026-10-30 · edited line 1315 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  `state/projects/skill-builder/brief.md:100-110` → ask for the outcome in their own words first.
```

### validation fix 2026-10-30 · edited line 1345 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  restated. `NO-DATE` · `state/projects/project-system/brief.md:91` → LLM-judgment section matching.
```

### validation fix 2026-10-30 · edited line 1347 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  silently, no single source of truth. `NO-DATE (LOG-01)` · `state/projects/lifehack-cowork/brief.md:280-298`
```

### validation fix 2026-10-30 · edited line 1350 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  attackers hide payloads in the exemption. `NO-DATE` · `state/projects/ingest-skill/brief.md:147-172` → the
```

### validation fix 2026-10-30 · edited line 1354 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  `NO-DATE (commit 76c6a80)` · `state/projects/skill-builder/brief.md:100-110` → fold the doctrine into the
```

### validation fix 2026-10-30 · edited line 1359 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  that already had 3 of 4 lanes done." `NO-DATE` · `state/projects/skill-system/brief.md:122-136` → not
```

### validation fix 2026-10-30 · edited line 1363 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  `state/projects/huddle/huddle-skill/brief.md:58-86` → every participant and the chair runs in a background
```

### validation fix 2026-10-30 · edited line 1368 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  `NO-DATE` · `state/projects/translator-voice/brief.md:97-122` → killed outright.
```

### validation fix 2026-10-30 · edited line 1372 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  `state/projects/translator-voice/brief.md:97-122` → kept the concrete prompt.
```

### validation fix 2026-10-30 · edited line 1375 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
  the recurring class was adopted by 3 of 15 tools. `2026-08-08` · `state/projects/project-system/brief.md`
```

### validation fix 2026-10-30 · edited line 1709 · dead private pointer stripped (owner's notes / state/projects citation); date and lesson kept

```
`state/projects/security/sentinel-gateway/records/2026-07-03-reader-actor-enforcement-proof.md`. The same
```

### validation fix 2026-10-30 · edited line 1227 · sentence Enver never approved (new pass/fail wording)

```
  §III.4's "too cheap loses intuition"** (cross-ref, §III.4). The lesson: judgment work such as recognizing what a thing is and where it belongs stays on at least the middle tier; save cost by batching instead.
```

### validation fix 2026-10-30 · edited line 1962 · status-bar fallback directive removed; bullet restored to original wording minus Cowork mention

```
- **Where there is no status bar, print the Path Beat as a plain line** (§IV.4). Unlike the Part II §II.4 primitives (skill-local scripts, portable by
  design), this mechanism depends on the host app offering a status bar; the Path Beat itself does not.
```

### validation fix 2026-10-30 · edited line 1410 · only one Rule label may remain

```
**Design rule:** never let a primitive depend on a hook, a host path, or `settings.json` — or it stops existing the moment the skill travels.
```

### validation fix 2026-10-30 · edited line 1170 · dangling separator left after pointer strip

```
  JSON emits but the write still executes. `2026-06-17` ·
```

### validation fix 2026-10-30 · edited line 1175 · dangling separator left after pointer strip

```
  **only `description:`** — anything else is invisible to auto-trigger. `NO-DATE` ·
```

### validation fix 2026-10-30 · edited line 1180 · dangling separator left after pointer strip

```
  **crashes frontmatter YAML parsing**; the menu silently falls back to the body heading. `NO-DATE` ·
```

### validation fix 2026-10-30 · edited line 1186 · dangling separator left after pointer strip

```
  — they ship JSON via it and the collector receives prose instead. `NO-DATE` ·
```

### validation fix 2026-10-30 · edited line 1208 · dangling separator left after pointer strip

```
  every prior rule addition diluted the one line that actually worked. `2026-07-28` ·
```

### validation fix 2026-10-30 · edited line 1232 · dangling separator left after pointer strip

```
  intuition" — same lesson as A4, a separate incident. `NO-DATE` ·
```

### validation fix 2026-10-30 · edited line 1249 · dangling separator left after pointer strip

```
  findings vs 82** at nearly the same wall-clock — "not faster, it is shallower." `2026-08-05` ·
```

### validation fix 2026-10-30 · edited line 1311 · dangling separator left after pointer strip

```
  types). Failed: "they shouldn't need to know what the process is." `NO-DATE` ·
```

### validation fix 2026-10-30 · edited line 1314 · dangling separator left after pointer strip

```
  actually don't want you to start by showing me the full spec template." `NO-DATE` ·
```

### validation fix 2026-10-30 · edited line 1362 · dangling separator left after pointer strip

```
  burns opus, freezes the window for the whole meeting, dumps the full board into main context. `NO-DATE` ·
```

### validation fix 2026-10-30 · edited line 1371 · dangling separator left after pointer strip

```
  were all rejected — "too simplistic... we went off track somewhere." `2026-07-28` ·
```


## 2026-10-30 — label/pointer fix

Reason: only the stochastic-environment sentence may be labelled a Rule, so other Rule labels become Principle wording (meaning kept); citations of the owner's private notes folder (`records/...`) are dead for students, so each pointer is stripped and the date and lesson kept. Each entry is the ORIGINAL line text, verbatim, before the edit.

### label/pointer fix 2026-10-30 · line 72 (before edit) · rule label to principle wording (only the stochastic-environment sentence stays a Rule)

```
  - ["III.9", 1733, "four build-process rules that survived contact"]
```

### label/pointer fix 2026-10-30 · line 169 (before edit) · rule label to principle wording (only the stochastic-environment sentence stays a Rule)

```
> the same signal whether the thing worked or not. And outside that rule: **look before you build.**
```

### label/pointer fix 2026-10-30 · line 312 (before edit) · rule label to principle wording (only the stochastic-environment sentence stays a Rule)

```
- **Decision rule: card or no card (CANDIDATE, audit 2026-10-28):** use a card when step order must hold AND at least one of: the run is long enough that losing progress costs real time/money, a human pause sits mid-run, it spans sessions, or it has more than one ai step. A short job that can simply rerun from scratch gets per-step checks and loud failure, not a card. Every job, carded or not, follows the ALWAYS rules (content checks, no silenced errors, exit 0 is not proof). This reconciles the "5-step linear run still gets a card" note at §IV.8.
```

### label/pointer fix 2026-10-30 · line 417 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept (line was only a pointer)

```
> Rich version + full evidence: `records/insight/2026-08-05-the-code-llm-seam.md` (Drive).
```

### label/pointer fix 2026-10-30 · line 438 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
> membership half was independently corroborated by `records/research/2026-07-25-code-vs-llm-enforcement-split.md`
```

### label/pointer fix 2026-10-30 · line 530 (before edit) · rule label to principle wording (only the stochastic-environment sentence stays a Rule)

```
**A RULE WORTH KEEPING, SHARPENED** (2026-08-05, from someone who works with these systems daily). The rule as stated: *LLMs are for fuzzy matching
```

### label/pointer fix 2026-10-30 · line 535 (before edit) · rule label to principle wording (only the stochastic-environment sentence stays a Rule)

```
down is exactly the thicket the rule above is warning about. **But note what that rule does not cover: it tells you how to
```

### label/pointer fix 2026-10-30 · line 721 (before edit) · rule label to principle wording (only the stochastic-environment sentence stays a Rule)

```
   - **The fold rule (measured, not obvious):** a plain majority is NOT enough. `violated` and `missed` are not
```

### label/pointer fix 2026-10-30 · line 812 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
> *Outside caveat, 2026-09-05, RESEARCHED — `records/research/2026-09-05-code-llm-interaction-modalities.md`:*
```

### label/pointer fix 2026-10-30 · line 905 (before edit) · rule label to principle wording (only the stochastic-environment sentence stays a Rule)

```
### Three rules that govern the whole toolbox
```

### label/pointer fix 2026-10-30 · line 962 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  → *Research pass 2026-09-05:* **No field remedy** — class-level liveness/reachability sweeps exist for conventional code, none for hooks/skills/tools → experiment (unused-parts-drifting-copies). · Category: **architectural** (canon §16 mode 1, 2026-09-08 retrofit) · **CANDIDATE** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; no field remedy, never held here)
```

### label/pointer fix 2026-10-30 · line 966 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  → *Research pass 2026-09-05:* **Field remedy (RESEARCHED):** independent output-shape/baseline verification + heartbeat monitoring — emerging-to-strong (n8n community forum) (lying-signals-text-guards). ✅ ADOPTED (right-size audit 2026-09-05) · Category: **architectural** (canon §16 mode 2, 2026-09-08 retrofit) · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; field remedy also noted)
```

### label/pointer fix 2026-10-30 · line 975 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  → *Research pass 2026-09-05:* **No field remedy** — generate-from-source is proven for docs/config, not for arbitrary duplicated facts in a harness repo → experiment (unused-parts-drifting-copies). · Category: **both** (canon §16 mode 3, 2026-09-08 retrofit) · **CANDIDATE** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; no field remedy, never held here)
```

### label/pointer fix 2026-10-30 · line 977 (before edit) · rule label to principle wording (only the stochastic-environment sentence stays a Rule)

```
  known-bad input before trusting it passing (§V.4c is now rule zero of PART V).
```

### label/pointer fix 2026-10-30 · line 979 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  → *Research pass 2026-09-05 (second pass, the five modes):* **Field remedy (RESEARCHED):** checker independent in author, code path, and data source from what it checks — strong, decades-old cross-industry convergence (verification-not-by-the-actor; Skalse 2022 / ISO segregation-of-duties). ✅ ADOPTED (right-size audit, second pass, 2026-09-05) · Category: **architectural** (canon §16 mode 4, 2026-09-08 retrofit) · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; field remedy also noted)
```

### label/pointer fix 2026-10-30 · line 985 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  → *Research pass 2026-09-05 (second pass, the five modes):* **No field remedy** — field's answer (plan-first/spec-gating) is the same prose-ceremony shape that already failed 7x locally; METR's RCT shows added process can cost without payoff → experiment (premises-and-numbers-checked-first). · Category: **operational** (canon §16 mode 5, 2026-09-08 retrofit) · **CANDIDATE** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; no field remedy, never held here)
```

### label/pointer fix 2026-10-30 · line 989 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  → *Research pass 2026-09-05:* **No field remedy** — artifact-over-summary is exactly what local already tried at one site and it fails partially applied → experiment (values-that-did-not-travel). ✅ ADOPTED (right-size audit 2026-09-05) — the field's strongest mechanism; PARTIAL here, see canon §12.c · Category: **operational** (canon §16 mode 6, 2026-09-08 retrofit) · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; field remedy also noted)
```

### label/pointer fix 2026-10-30 · line 993 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  → *Research pass 2026-09-05:* **Field remedy (RESEARCHED):** layered guard — typed parsing + narrow regex triage + semantic classifier — strong (arXiv:2506.10597, IEEE S&P 2026) (lying-signals-text-guards). ✅ ADOPTED (right-size audit 2026-09-05) · Category: **architectural** (canon §16 mode 7, 2026-09-08 retrofit) · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; field remedy also noted)
```

### label/pointer fix 2026-10-30 · line 997 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  → *Research pass 2026-09-05 (second pass, the five modes):* **Field remedy (RESEARCHED):** never trust a worker's self-produced proof — poll a pre-agreed, orchestrator-checked landmark fixed before delegation — strong (verification-not-by-the-actor; hexisteme.github.io postmortem). ✅ ADOPTED (right-size audit, second pass, 2026-09-05) · Category: **operational** (canon §16 mode 8, 2026-09-08 retrofit) · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; field remedy also noted)
```

### label/pointer fix 2026-10-30 · line 1003 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  → *Research pass 2026-09-05 (second pass, the five modes):* **No field remedy** — reproducibility science's recompute-from-source norm is off-domain inference only; the STALE benchmark confirms detecting stale facts is unsolved → experiment (premises-and-numbers-checked-first). · Category: **operational** (canon §16 mode 9, 2026-09-08 retrofit) · **CANDIDATE** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; no field remedy, never held here)
```

### label/pointer fix 2026-10-30 · line 1007 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  → *Research pass 2026-09-05:* **Field remedy (RESEARCHED):** fail-loud unique-context-anchored search/replace, optionally hash-augmented — strong (wuu73.org cross-tool survey) (wrong-target-edited-or-run). ✅ ADOPTED (right-size audit 2026-09-05) · Category: **both** (canon §16 mode 10, 2026-09-08 retrofit) · **RESEARCHED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; field remedy, never held here)
```

### label/pointer fix 2026-10-30 · line 1011 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  → *Research pass 2026-09-05 (second pass, the five modes):* **Field remedy (RESEARCHED):** move must-always rules into deterministic hooks/tool gates, keep prose for judgment calls only — strong, three independent communities converge (rules-with-teeth; Claude Code hooks docs). ✅ ADOPTED — a receipt on hook-plane doctrine and point-of-need injection (2026-09-05) · Category: **architectural** (canon §16 mode 11, 2026-09-08 retrofit) · **RESEARCHED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; field remedy, never held here)
```

### label/pointer fix 2026-10-30 · line 1017 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  → *Research pass 2026-09-05:* **No field remedy** — content-addressed/hash verification matches local's own one-pair fix, but no source generalizes it to a harness's full file set → experiment (wrong-target-edited-or-run). · Category: **architectural** (canon §16 mode 12, 2026-09-08 retrofit) · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; no field remedy)
```

### label/pointer fix 2026-10-30 · line 1022 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
 · Category: **architectural** (canon §16 mode 13, 2026-09-08 retrofit) · **OBSERVED** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; held partially here; no field remedy)
```

### label/pointer fix 2026-10-30 · line 1030 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  census; canon §16 mode 14 is the same.* · Category: **operational** (canon §16 mode 14, 2026-09-08 retrofit) · **Field remedy (RESEARCHED):** structural substitution over debiasing — name a concrete low-context reader and test against them directly; minimal, self-contained units, dynamically curated for an LLM reader rather than statically front-loaded (`records/research/2026-09-08-mode-14-reader-holds-no-state.md`). · **CANDIDATE** (derived 2026-09-07 from `records/research/2026-09-05-durable-solutions-audit.md` and the 2026-09-05 research pass; Enver's ruling 2026-09-06; nothing watched)
```

### label/pointer fix 2026-10-30 · line 1039 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  independent instances across four traditions and five decades; explicitly bounded, never complete
```

### label/pointer fix 2026-10-30 · line 1040 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  (`records/research/2026-09-08-mode-15-instrument-refuses-truth.md`). ·
```

### label/pointer fix 2026-10-30 · line 1052 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  source are present remains explicitly unsolved per 2025 research
```

### label/pointer fix 2026-10-30 · line 1053 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  (`records/research/2026-09-08-mode-16-written-word-outranks-live.md`). · **CANDIDATE** (derived
```

### label/pointer fix 2026-10-30 · line 1065 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  predating LLMs; explicitly leaky per its own practitioners ("traceability drift")
```

### label/pointer fix 2026-10-30 · line 1066 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  (`records/research/2026-09-08-mode-17-observation-hardened-into-rule.md`). · **CANDIDATE** (derived
```

### label/pointer fix 2026-10-30 · line 1081 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  convergent 2026 practitioner guidance is to gate mutating git actions outside the model's own reasoning
```

### label/pointer fix 2026-10-30 · line 1082 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  (`records/research/2026-09-08-mode-18-mirror-rot.md`). · **CANDIDATE** (derived 2026-09-07 from canon §16 mode
```

### label/pointer fix 2026-10-30 · line 1101 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  solves it, and one tool's own default takes the opposite view
```

### label/pointer fix 2026-10-30 · line 1102 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  (`records/research/2026-09-08-mode-19-delivery-packaging-as-stranded-work.md`). · **CANDIDATE** (derived 2026-09-08 from canon §16 mode 19;
```

### label/pointer fix 2026-10-30 · line 1138 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
> records/briefs directly.
```

### label/pointer fix 2026-10-30 · line 1155 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  **overwrites it on re-entry** — a named, won't-fix upstream Claude Code bug (#21131). `2026-07-13` ·
```

### label/pointer fix 2026-10-30 · line 1156 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  `records/decision/2026-07-13-scratchpad-in-brief.md` → replaced by a fixed `## Scratchpad` section inside
```

### label/pointer fix 2026-10-30 · line 1160 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  theater nothing ever saw. `2026-05-30` · `records/log/2026-05-30-datagate-websearch-automation.md` →
```

### label/pointer fix 2026-10-30 · line 1164 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  2026-06-01` · `records/log/2026-05-31-lifehack-v2-audit.md` → `deny()` corrected to `exit 2`.
```

### label/pointer fix 2026-10-30 · line 1167 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  **zero real entries captured despite 300+ daily calls.** `found 2026-05-31, fixed 2026-06-01` ·
```

### label/pointer fix 2026-10-30 · line 1168 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  `records/log/2026-05-31-lifehack-v2-audit.md` → read stdin via `$(cat)`.
```

### label/pointer fix 2026-10-30 · line 1195 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  putting a report where reports go." `prescribed pre-2026-07-27, disproven 2026-07-30` ·
```

### label/pointer fix 2026-10-30 · line 1196 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  `records/insight/2026-08-01-agent-name-discards-report.md` → `system/hooks/guard_agent_return_channel.sh` +
```

### label/pointer fix 2026-10-30 · line 1206 (before edit) · rule label to principle wording (only the stochastic-environment sentence stays a Rule)

```
- **[B38]** Tried: adding a new RULE to a voice/style skill to fix reply length. Failed: "a rule says what to
```

### label/pointer fix 2026-10-30 · line 1212 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  every-turn L1 anchor exists** — cross-ref §IV.2/§IV.3). `2026-06-08` ·
```

### label/pointer fix 2026-10-30 · line 1213 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  `records/2026-07-13-translator-voice-debug-history.md` → a firmer rewrite + a dedicated SOP, later per-turn
```

### label/pointer fix 2026-10-30 · line 1217 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  `2026-06-27` · `records/2026-07-13-translator-voice-debug-history.md` → a rotating per-turn anchor hook.
```

### label/pointer fix 2026-10-30 · line 1220 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  re-read" rule (cross-ref). `2026-06-28` · `records/2026-07-13-translator-voice-debug-history.md`
```

### label/pointer fix 2026-10-30 · line 1228 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  `2026-07-11, reverted at commit 779157c` ·
```

### label/pointer fix 2026-10-30 · line 1229 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  `records/reference/2026-07-12-stage2-email-interpret-method.md` → kept sonnet, sought savings via bigger
```

### label/pointer fix 2026-10-30 · line 1236 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  was a verified no-op, and the "untyped spawns" thesis measured zero real unpinned sites. `2026-07-28` ·
```

### label/pointer fix 2026-10-30 · line 1237 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  `records/decision/2026-07-28-model-efficiency-plan-abandoned.md` → killed; 7 model pins kept only as
```

### label/pointer fix 2026-10-30 · line 1242 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  structurally <30%, Jain et al. NeurIPS 2025). `2026-07-12/13` ·
```

### label/pointer fix 2026-10-30 · line 1243 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  `records/2026-07-13-translator-voice-debug-history.md` → a 3-layer plan (output-style + examples, a parked
```

### label/pointer fix 2026-10-30 · line 1246 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  Failed: "barely correlate with perceived difficulty on technical prose." `2026-07-12` ·
```

### label/pointer fix 2026-10-30 · line 1247 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  `records/2026-07-13-translator-voice-debug-history.md` → a holistic test + a planned local classifier.
```

### label/pointer fix 2026-10-30 · line 1278 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  `2026-06-04` · `records/decision/2026-06-04-design-lifehack-skill.md` → one skill, 7 lenses as internal
```

### label/pointer fix 2026-10-30 · line 1284 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  wall-of-text detector. Failed: couldn't distinguish a mild wall from a genuinely good reply. `2026-07-12` ·
```

### label/pointer fix 2026-10-30 · line 1285 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  `records/2026-07-13-translator-voice-debug-history.md` → folded into the 3-layer approach.
```

### label/pointer fix 2026-10-30 · line 1324 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  per-session artifact off file mtime under concurrency.** `2026-07-13` ·
```

### label/pointer fix 2026-10-30 · line 1325 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  `records/decision/2026-07-13-statusbar-hud-build.md` → **not yet fixed**, open debt
```

### label/pointer fix 2026-10-30 · line 1328 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  Failed: all blocked — CAPTCHAs and 403/429s, "an unwinnable arms race with bot detection." `2026-05-30` ·
```

### label/pointer fix 2026-10-30 · line 1329 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  `records/log/2026-05-30-datagate-websearch-automation.md` → dev-browser (real Chrome), later Serper API as
```

### label/pointer fix 2026-10-30 · line 1333 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  sanitize-before-context and tool-plane governance. `2026-06-03` ·
```

### label/pointer fix 2026-10-30 · line 1334 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
  `records/log/2026-06-03-relay-ghost-root-cause-fix.md` → the custom sanitized bridge; MCP mined for
```

### label/pointer fix 2026-10-30 · line 1474 (before edit) · rule label to principle wording (only the stochastic-environment sentence stays a Rule)

```
  **The rule this REPLACES** (kept visible so nobody reinstates it from memory): *"side-effect skills get
```

### label/pointer fix 2026-10-30 · line 1733 (before edit) · rule label to principle wording (only the stochastic-environment sentence stays a Rule)

```
## III.9 — Build process: four rules that survived contact
```

### label/pointer fix 2026-10-30 · line 1884 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept

```
> **What outside research adds (2026-09-05, RESEARCHED — `records/research/2026-09-05-multi-step-execution-enforcement.md`):**
```

### label/pointer fix 2026-10-30 · line 1955 (before edit) · rule label to principle wording (only the stochastic-environment sentence stays a Rule)

```
- **HARD RULE — never clobber the core.** Write ONLY via `skill_hud.sh` (it writes your own per-session HUD
```

### label/pointer fix 2026-10-30 · line 2021 (before edit) · rule label to principle wording (only the stochastic-environment sentence stays a Rule)

```
> **Rule zero, 2026-09-05 (census, REPRODUCED — §II.4a [F1]/[F4], canon §16 and the frame's operating rule):**
```

### label/pointer fix 2026-10-30 · line 2243 (before edit) · rule label to principle wording (only the stochastic-environment sentence stays a Rule)

```
> **THE RULE:** *a claim's PROXIMITY to a thing is not evidence about that thing.* Before you price, plan, or
```

### label/pointer fix 2026-10-30 · line 2477 (before edit) · rule label to principle wording (only the stochastic-environment sentence stays a Rule)

```
> **THE RULE:** *a phase's SHARE tells you where the time IS; the REMAINDER tells you whether moving it can
```

### label/pointer fix 2026-10-30 · line 2564 (before edit) · private notes-folder pointer stripped (dead for students); date and lesson kept (line was only a pointer)

```
Records: `records/research/2026-09-05-code-llm-interaction-modalities.md` · `…-multi-step-execution-enforcement.md`.
```

## 2026-10-30 — citation path fix (FIX, factual)
Reason: these four paths were previously accounted for by the cut "not in this repository" lists; corrected to where the files actually live.

Original line 498:
```
| 1 | `system/tools/section_archive.py` | Shipped a heading-guessing regex whose match decided **what gets archived immediately before a deletion** — judgment in code, at the highest-stakes point. It also could not win: the brief fleet is genuinely non-standard, and the first widening matched `## CURRENT STATE NOTES`, a DIFFERENT section. **The ruling:** *"don't make the tool do fuzzy matching, that should belong to the llm. we've got a lot of briefs and they don't have standardized sections."* ⇒ now `--heading "<exact>"` or `--start/--end`, and **a near-miss is REFUSED, never resolved to something close.** |
```
Original line 499:
```
| 2 | `system/tools/checkin_open.py` | Scanned a whole brief for a marker character to find its three status lines. Returned **`PARTIAL-RUNGS 6`** on its own project's brief, because **three lines of ordinary prose elsewhere in the file merely MENTIONED that character while describing this very tool.** ⭐ **It matched its own description.** Its sibling `gauge_check.py` did NOT have the bug — for one reason: it is scoped to the section and does not go looking. |
```
Original line 1338:
```
  `2026-07-13` · `system/sops/build-sop.md`; `state/debt-ledger.md` `[GUARD-HOOKSOP-FALSE-POSITIVE]` → match
```
Original line 1703:
```
`agents/ingest-reader.md` carries **`tools: Read`** and nothing else — no Bash, no Write/Edit, no network, no
```
