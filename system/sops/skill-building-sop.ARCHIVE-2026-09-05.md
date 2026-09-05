# ARCHIVE — skill-building-sop.md, material moved out on 2026-09-05

> Nothing here was deleted; all of it was **moved**, verbatim, out of
> `system/sops/skill-building-sop.md` and into this file, so the live page could stay dense without
> losing anything hard-won. Each section below is named by the pointer that replaced it in the
> compacted page. `verify.py` in this folder proves that COMPACT + ARCHIVE together still contain
> every non-blank line of the original.

---

## NOTE blocks — full original text

> Moved from the top of the page. The ⛔/✅ **path bullets stayed in the live page** because
> `system/tools/citation_lint.py` reads them: a marker accounts for its backticked paths everywhere in the
> file, so deleting a bullet would break the lint on citations further down. Only the surrounding prose
> moved here.

> ## NOTE — WHAT THIS PAGE CITES THAT IS NOT IN THIS REPOSITORY
>
> Named here rather than discovered one dead link at a time.
>

> ## NOTE — THE `[M]` MEASUREMENTS WERE TAKEN UNDER A FORMER SKILL NAME
>
> Nearly all `[M]` evidence on this page was measured against the skill this repo now ships as
> **`planning-weekly`**. At measurement time (2026-07) that skill was named **`cal-weekly`**, on the
> `cal` desk. The desk was renamed `cal` → `planning` on 2026-08-14/15, and every citation below was
> updated to the current name so the paths resolve — the *runs behind the numbers* are unchanged, and
> nothing was re-measured. Read `planning-weekly` wherever an older copy of this page said
> `cal-weekly`. **The persona in the HUD examples is still `Cal`** — that is a character name, and it
> was deliberately not renamed.

> ## NOTE — WHAT THIS PAGE POINTS AT THAT IS NOT IN THIS REPOSITORY
>
> This is 2,300 lines of hard-won skill-building doctrine, and it earns its length by citing the
> exact file where each lesson was learned. Most of those files belong to the system it came from and
> **do not ship here.** They are named below rather than discovered one dead link at a time.
>
> **⛔ Nothing in this block is coming.** Where a lesson cites one of them, the lesson's evidence is in
> the lesson — the path was only ever the filing location of the original write-up. Read the rule; it
> is complete without the citation.

> ⚠ **`system/parts/` is the big one, and it is worth knowing why.** That library is where the donor
> system kept its small reusable gates — a fan-out budget, a write ledger, a completeness receipt.
> This page cites them constantly as worked examples of *"build the gate once, source it everywhere."*
> **The principle is the transferable part**, and six of the parts have now crossed because a shipped
> skill actually needed them — which is the rule this page teaches, applied to itself: a part crosses
> when it has a caller, never because it is good. Two more crossed earlier under different names
> (`shared/bounded_input.py`, `shared/emit/verdicts.py`). The remainder are inventory, not assets.
>
> ⚠ **THIS BLOCK GOES STALE EVERY TIME SOMETHING LANDS, AND A STALE ONE IS WORSE THAN NONE** — it
> tells a reader not to bother looking for a file that is right there. It was wrong in ten places the
> day `/ship` and `/skill-builder` landed. `system/tools/citation_lint.py` catches exactly this and is
> what caught it; re-run it after anything crosses.

---

## 🧭 ROUTE — the original question-sorted index

> Moved 2026-09-05, replaced in the live page by a generated table of contents. This index is sorted by
> the QUESTION a builder arrives with rather than by document order, which is the more useful shape — it
> was archived only because it was hand-maintained and had started to drift from the headings it names
> (its `routing_evals.py` line is the proven instance). Read it for the questions.

## 🧭 ROUTE — find your question, not the outline

> This file is 2,000+ lines. **You did not arrive with an outline — you arrived with a question.** The
> entries below are sorted by the question a builder actually asks, not by document order; each one names
> the section(s) that answer it. If your question isn't close to any of these, the six-trait portrait at
> §0 and the reader_note in the frontmatter (READ ORDER = PART I → II → III → IV → V → VI) are the fallback.

⭐⭐⭐ **"Has anyone already tried this and had it fail?"** → **`§II.4a — DO NOT BUILD`**, 80 dated dead
ends, grouped by failure shape (harness facts, prose-doesn't-enforce, cheap-models/cheap-judges,
self-grading tests, prescription-calcifies). **Grep this section BEFORE you build anything that smells like
a retry** — it is the single most-needed, least-guessed-at section in the file. Only ~35% coverage of what's
actually on disk (stated in its own header) — absence here is not proof it's safe.

**"Is there already a tool I can just call instead of writing a new one?"** → **`§II.4 — the primitives
library`**: 19 built parts in `system/parts/`, sorted by how alive they are (Tier 1 = called by a shipped
skill today, Tier 2 = live only through the dev factory, Tier 3 = built with zero callers anywhere — the
`validator-exists-but-nothing-calls-it` anti-pattern §V.9 names). Each entry states its real caller count and
a "don't use this for X" line. Read `⚠ THE HEADLINE INVERSION` first — the table's stale-looking markers
undercounted what's actually built.

⭐ **"The HARNESS did something I didn't expect — my agent came back empty, my hook logged nothing, my
skill didn't fire."** → **`§II.4a` cluster 1, *facts about the harness*.** Measured behaviours of Claude
Code itself, not opinions: hook payload arrives on **stdin, never `$1`** · a hook that **exits 0 cannot
block and the model never sees it** · **only `description:` triggers a skill** (`summary:`/`note:`/`title:`
are invisible) · an unquoted `description:` containing a colon-space **breaks the menu silently** · a
**NAMED sub-agent's report is DISCARDED** (249 named spawns returned a payload 0 times; 1,714 unnamed
returned one every time) · `MAX_THINKING_TOKENS` is **inert** · plan mode **overwrites its own file** on
re-entry. *(Added 2026-08-07 after an independent cold routing eval: a reader asked "my helper agent came
back with nothing, where do I look?" and this index sent it confidently to the wrong section. The facts
were in the file; nothing routed to them. That confident-wrong-answer is the exact failure the
instrument-selector entry below warns about, and the index had it too.)*

**Before you write a line of SKILL.md:**
- "Should this even be a skill, or just a slash-command?" → `III.1`
- "How do I write down what this is FOR before I build anything?" → `III.2 — declare its INTENT`
- "Is my skill going to fire when I want it to, and stay silent when it shouldn't?" → `III.3 — the
  description: frontmatter`, the #1 failure mode. *(Near miss: the tool that TESTS firing behavior,
  `routing_evals.py`, lives in `§II.4` Tier 3 — it exists but nothing calls it yet.)*
- "How do I design the actual step-by-step shape of the flow?" → `III.4`
- "How do I lay out files so the skill doesn't load bloated every turn?" → `III.5 — progressive disclosure`
- "Should I hand-build the skeleton or generate it?" → `III.6 — new-skill.sh`
- "How do I catch a spec-vs-implementation mismatch before the first live run?" → `III.7 — the spec-diff gate`
- "For each rule I care about, how will I ever prove it happened?" → `III.8`, plus `⭐ NOWHERE IS A DECISION
  POINT` if a rule turns out to be unprovable
- "A rule keeps breaking no matter how I reword it" → `III.9 — FAIL TWICE → the architecture is the bug`
- "Does this rule need an actual human checkpoint, or can code check it alone?" → `III.10`'s `⭐ THE
  HUMAN-IN-THE-LOOP TEST`

**Deciding who owns what — code, the model, or a human:**
- "Should this be code or should I trust the model to do it?" → `LAW 1 — the Division of Labor`, plus `⭐ THE
  SEAM` (what actually crosses the code/model line) and `⭐ LAW 1b` (is the seam even REACHABLE, separate
  question from what crosses it)
- "My intent got lost somewhere between design and the actual run — where do I even look?" → `LAW 2 — intent
  leaks at four seams`
- "Can the skill just report itself as done?" → `LAW 3 — never let the actor grade its own completion`
- "What can an LLM just structurally never do, no matter how I prompt it?" → `LAW 4`
- "Why did a rule that worked last week stop landing?" → `LAW 5 — prose decays`, the numbers behind Parts II–VI

**Deciding HOW HARD to enforce a rule once you have one:**
- "What are my actual options for enforcing something?" → `§II.1 — the four families` (Replace / Verify /
  Wall / Refresh)
- "My rule keeps getting negotiated away or argued with by the model" → `§II.2 — why prose instructions fail`
- "How strict does this specific rule's enforcement need to be?" → `§II.3 — the reliability ladder`
- "What are the three layers I'm even enforcing ACROSS?" → `§II.0` (reasoning / state / wall), plus `⭐ THE
  FLOOR IS THE INSTRUMENT SELECTOR` — the wrong instrument on the right floor gives a confident wrong answer
- "I'm bundling extra files with the skill — how does it know whether to run one or read one?" → `§II.6 —
  run-vs-read: the folder IS the signal`
- "The same guard needs to work identically on the CLI and inside Cowork's sandbox" → `§II.5 — packaging:
  two lanes`
- "Does telling the model to WITHHOLD, ORDER, or COUNT something actually hold in prose?" → `§II.7 — ⏸ HELD
  hypothesis`, not yet doctrine, flagged as such

**Keeping a long interactive session on the rails (PART IV):**
- "My skill starts strong and drifts off its own instructions as turns pile up" → `§IV.1 — three parties are
  in the room` and `§IV.2 — the 3-layer injection model`
- "How does a principle/canon actually persist instead of being said once and going stale?" → `§IV.3`
- "Where in the prompt should a reminder go so the model actually sees it?" → `§IV.5 — edges, not middle`
- "How do I stop the model from silently skipping a step in a multi-step flow?" → `§IV.8 — staying
  on-PROCEDURE`
- "Should I show the whole multi-step arc in one prompt, or dole it out?" → `§IV.6 — one step, one injection`
- "Is correcting the user's own words back to them just being pedantic?" → `§IV.7 — anchoring the session`
- "Can the skill show its own progress on the status bar?" → `§IV.9 — draw the Path Beat`
- "I'm fanning work out to several sub-agents — how do I keep them from just agreeing with each other?" →
  `§IV.10 — briefing a PANEL`, same-base-model homogeneity floor

**Proving the skill actually works (PART V):**
- "How do I verify a skill does what it claims, not just that it SAYS it did?" → `PART V` overview, and Law
  3's loophole at `§V.4b — evidence of work, never the FORM of a claim`
- "Before I add a gate, how do I know a real problem even exists?" → `§V.2 — measure before you enforce`
- "My tester might be lying to me too — how do I check the checker?" → `§V.4 — verify the verifier`, `§V.4a —
  BLIND THE GRADERS, NEVER THE ACTORS`, `§V.4c — probe by DESTRUCTION, not minimization`
- "A claim sits right next to a receipt — is that proof?" → `§V.4d — a claim written next to a thing is
  treated as the thing`
- "My test fixture caught a bug the real skill doesn't actually have" → `§V.3 — a fixture can manufacture a
  violation`. *(Related but distinct from `§II.4a` cluster 4, "tests that grade their own homework" — §V.3 is
  a fixture inventing a false positive, cluster 4 is a test built from the same mental model as what it
  checks. Both are self-grading failures; check both.)*
- "Which link in the chain am I even testing?" → `§V.1 — one detector per loss-chain link`
- "Every component passed its own check but the whole thing still doesn't work" → `§V.5 — component checks
  say nothing about SEAMS`
- "A run diverged from spec — how do I classify what kind of failure it was?" → `§V.6 — the three failure
  types`
- "Which of my spec's rules can even be graded by machine, and which can't?" → `§V.7 — the enforceability
  partition`
- "Do I need the full lab, or does a real supervised run cover it?" → `§V.8`
- "What bad patterns do other public skill repos fall into, so I don't copy them?" → `§V.9 — anti-patterns
  observed in the wild`

**Scale, character, and speed (PART VI):**
- "My skill has outgrown one file — split it?" → `§VI.1`, EARN it first — ~79% of multi-agent failures are
  handoffs
- "How do I make a human-facing skill feel like a conversation, not a form?" → `§VI.2 — interaction craft`
- "What makes a skill's identity more than just gate-compliance?" → `§VI.3 — character-with-purpose`
- "What craft rules apply once I'm actually drafting the prose?" → `§VI.4 — writing it`
- "What's the quality bar for content a skill produces?" → `§VI.5`
- "What model tier should a sub-agent run?" → `§VI.6 — model tiering`
- "My skill is too slow — where do I actually cut time?" → `§VI.7`: `LAW A — subtract first` (is the phase
  you'd attack even the bottleneck), `LAW B — price every layer that isn't work` (handoffs cost time even
  doing nothing), `LAW C — wall clock vs. human-waiting time` (different targets)

**"Where does a claim in this doc actually come from?"** → `EVIDENCE & PROVENANCE`, the `[R]`/`[R2]`/`[C]`/`[M]`
tag legend; `⏗ OUR OWN BET` (after §IV.10) is flagged separately as not crowd-validated.

---

## §II.4 — the primitives catalogue (tiers)

> Moved 2026-09-05. A hand-kept inventory of ~17 parts with hand-typed caller counts. **Verified drift:**
> `system/parts/routing_evals.py` is profiled below in Tier 3 as built-but-uncalled, while the ⛔ banner at
> the top of the same page lists it as "still not here" — and the file exists nowhere in the repository.
> Two other entries below already carry ⚠ CORRECTED rulings against the same failure. **Regenerate from the
> tree by script before trusting any count here.** The ⚠ THE HEADLINE INVERSION block that preceded these
> tiers is a measurement and stayed in the live page.

### Tier 1 — LIVE: called by a real shipped skill or a production lane today

- **`system/parts/phase_gate.py`** — writes `✅ phase N complete` ONLY after verifying the phase's required
  artifacts against a JSON contract (`requires`/`forbids`); also flags an UNEARNED stamp already present on a
  refused phase. CALLERS: 1 — `system/tools/new-skill.sh:228`, unconditional for any multiphase skill scaffold.
  INTERFACE: `phase_gate.py --contract C.json --artifact A.md --phase N [--stamp] [--json] [--selftest]`.
  Don't use for: checking whether one section precedes another inside a phase — that's order_lint's job;
  phase_gate answers "is this phase's contract satisfied," never "is X before Y." ⚠ Its own docstring bounds it:
  `requires` is text-in/text-out and cannot tell real work from words typed to match — presence only.
- **`system/parts/order_lint.py`** — positional check with four verdicts (ORDERED / OUT_OF_ORDER /
  BEFORE_MISSING / NOT_APPLICABLE), deliberately separating "B came first" from "A never appeared." CALLERS: 1
  unconditional — `system/tools/new-skill.sh:154`, every scaffolded skill; a deployed copy sits in
  `skills/architect/scripts/order_lint.py` (resolves to `.claude/skills/architect/scripts/order_lint.py`).
  ⛔ **CORRECTED 2026-09-01** — ~~deployed copies also sit in `skills/skill-builder/scripts/order_lint.py`~~:
  checked this session against the repo, `.claude/skills/skill-builder/`, and the installed plugin cache
  (`~/.claude/plugins/cache/lifehack-brain/.../skill-builder/scripts/`) — no `order_lint.py` exists in any
  of them. The only copy anywhere is a stale one archived at
  `system/parked/2026-08-23-ruled-out-resurrections/.claude/skills/skill-builder/scripts/order_lint.py`.
  This claim was stale; skill-builder does not currently carry a deployed `order_lint.py`. The strongest of
  the whole library on caller count. INTERFACE: `order_lint.py --rules RULES.json --artifact A.md [--section
  "..."] [--json] [--selftest]`. Don't use for: proving something exists at all when there's no "before" — a
  BEFORE_MISSING antecedent that never runs at all is precondition_gate's or section_present's question, not
  a position question.
- **`system/parts/forbidden_content.py`** — the "do NOT yet" checker: scans a block of text for a forbidden
  artifact (e.g. a Win named before its arc), nonzero refuses. CALLERS: many — the live `/ship` lane
  (`system/shipping-lane/scrub.py`, `judge.py`, `push_gate.py`, `verify_rules.py`, all invoking it as a
  subprocess verdict engine) and `system/tools/new-skill.sh:229` (deployed as phase_gate's required sibling
  on every multiphase skill). INTERFACE: `forbidden_content.py --rules R.json (--text-file F | --stdin) [--json]
  [--selftest]`. Don't use for: proving a REQUIRED thing is present — it only proves an absence; section_present
  is its mirror image for presence.
- **`system/parts/move_aside.py`** — destructive-op safety net: keeps `.prev` generations, never `rm`s.
  CALLERS: 3 in the live `/ship` lane — ⛔ `system/shipping-lane/scrub.py:110,368` (donor line
  numbers; both files are here but were rewritten, so the numbers no longer match), `judge.py:223`,
  `push_gate.py:219`. **Absent from every prior version of this table despite being live in production — a
  bigger miss than any missing marker.** INTERFACE: `move_aside.py --target PATH [--keep N] [--dry-run]
  [--json] [--selftest]`. Don't use for: a correctness or completeness check — it says nothing about whether
  the new content is right, only that the old content wasn't destroyed.
- **`system/parts/bounded_input.py`** — proves a run touched ONLY what it was handed (the over-processing ⛔ ARCHIVED 2026-09-05 — catalogue entry moved out of the live SOP; the path was hand-kept and had drifted (see the pointer in §II.4); regenerate by script before trusting
  guard: set-diffs processed-ids against handed-ids). CALLERS: 1 — one ingest runner in the donor system, a
  production ingest runner. Also absent from every prior version of this table. INTERFACE:
  `bounded_input.py --handed H.json --processed P.json [--json] [--selftest]`. Don't use for: proving nothing
  was MISSED — that's the opposite direction (completeness_receipt / `ingest_setdiff.py`'s job).
- **`system/parts/precondition_gate.py`** — a consequent marker (e.g. a locked Win) may not stand until its ⛔ ARCHIVED 2026-09-05 — catalogue entry moved out of the live SOP; the path was hand-kept and had drifted (see the pointer in §II.4); regenerate by script before trusting
  antecedent artifact, with declared substance, already exists in the same document. ⚠ **CORRECTED
  2026-08-07** — the brief this section was drafted from labelled this part "BUILT-BUT-UNCALLED." That is
  wrong, verified directly: **`.claude/skills/planning-weekly/prompts/01a-lookback.md:161` invokes it as a real gate step**
  (`python3 .../precondition_gate.py --rules .../lookback-before-win.json --artifact
  .../session-scratchpad.md`) inside a shipped, running skill. CALLERS: 1 real shipped-skill caller
  (planning-weekly), plus factory-only reachability via `emit_gate.py`'s clause-routing dispatch. INTERFACE:
  `precondition_gate.py --rules R.json --artifact A.md [--json] [--selftest]`. Don't use for: proving
  sequence — its own docstring states the honest bound: it proves CO-PRESENCE only ("if X is present, Y must
  be too"), never which one came first; that's order_lint's question.
- **`system/parts/fanout_completeness.py`** — native-id coverage set-diffed **at the fan-out return
  boundary**, never at phase exit; combines completeness_receipt's set-diff with fanout_gate's capture check.
  CALLERS: 1 real shipped-skill caller — `.claude/skills/planning-weekly/prompts/00-system-layer.md:135`, invoked directly
  as a subprocess. INTERFACE: `fanout_completeness.py --captured C.json --source-ids IDS.json [--declared N]
  [--quiesced] [--require-substance] [--ledger-scope] [--json] [--selftest]`. Don't use for: checking
  coverage at any moment other than the fan-out's own return — its docstring says "never at phase exit"
  because the two moments prove different things.
- **`system/parts/map_carry_receipt.py`** — proves every finding written into a Map either reached the ⛔ ARCHIVED 2026-09-05 — catalogue entry moved out of the live SOP; the path was hand-kept and had drifted (see the pointer in §II.4); regenerate by script before trusting
  scratchpad or was explicitly declared dropped. CALLERS: 1 real shipped-skill caller —
  `.claude/skills/planning-weekly/prompts/00-system-layer.md:174`, invoked directly. INTERFACE: `map_carry_receipt.py --map
  M.md --scratchpad S.md [--json] [--selftest]`. Don't use for: proving a carried finding was acted on
  correctly — only that it wasn't silently lost in the hand-off.
- **`system/parts/residue_scrub.py`** — L0 sanitization + an explicit DATA fence + a hard size cap whose
  over-cap behavior is REFUSE or CHUNK, never silent truncation. CALLERS: 1 — `system/shipping-lane/judge.py`,
  invoked as a required sibling subprocess before any judged content reaches an LLM reader. INTERFACE:
  `residue_scrub.py --in FILE [--cap N] [--mode refuse|chunk|truncate] [--fence] [--label "..."] [--json]
  [--selftest]`. Don't use for: a security boundary against a determined attacker — it's deterministic
  sanitization + a size cap, not a content-safety judgment; that's `voted_judge.py`'s or an isolated
  tool-less reader's job.

### Tier 2 — LIVE, but reachable ONLY through the dev factory pipeline — no shipped skill calls these directly

- **`system/parts/completeness_receipt.py`** — pins a source-id denominator, set-diffs the artifact's cited
  ids against it, writes the receipt into the artifact. CALLERS: 1 — `system/factory/extract_clauses.py:379-406`,
  a dev pipeline, **not** a shipped skill. Its own docstring credits the older, production-proven
  `system/tools/ingest_setdiff.py` as the mechanism this generalizes from. INTERFACE:
  `completeness_receipt.py --artifact MAP.md --source-ids IDS.json [--declared N] [--write-receipt]
  [--require-substance] [--json] [--selftest]`. Don't use for: verifying quality or content — its own
  docstring states the bound plainly: it proves CITATION, not WORK; an artifact of bare cited ids with no
  content passes clean.
- **`system/parts/write_ledger.py`** — queue → write → read back → mark; a row cannot be declared drained
  while unproven. CALLERS: **not** "zero of any kind" — no shipped skill calls it, but
  `system/factory/emit_gate.py:334-339` carries a live dispatch entry that invokes it (`--ledger F --verify`), ⛔ ARCHIVED 2026-09-05 — catalogue entry moved out of the live SOP; the path was hand-kept and had drifted (see the pointer in §II.4); regenerate by script before trusting
  and `system/factory/route_to_part.py:202` routes clauses to it. Precisely: no shipped-skill caller; ⛔ ARCHIVED 2026-09-05 — catalogue entry moved out of the live SOP; the path was hand-kept and had drifted (see the pointer in §II.4); regenerate by script before trusting
  reachable only through the factory's own routing/dispatch table. INTERFACE: `write_ledger.py --ledger L.json
  (--verify | --status) [--json] [--selftest]`. Don't use for: checking write CONTENT is correct — it proves a
  row was read back, never that what landed there is right.
- **`system/parts/identifier_redaction.py`** — scans one or more artifacts for RAW sensitive-identifier ⛔ ARCHIVED 2026-09-05 — catalogue entry moved out of the live SOP; the path was hand-kept and had drifted (see the pointer in §II.4); regenerate by script before trusting
  PATTERN CLASSES (credit-card-, SSN/tax-ID-, bank-routing-, long-account-number-shaped) before anything gets
  written out. CALLERS: none shipped; reachable only via `emit_gate.py`'s dispatch table
  (`PART_TRACES["identifier_redaction"]`) and `route_to_part.py`'s classifier. INTERFACE:
  `identifier_redaction.py --artifact A.md [--artifact A2.md ...] [--rules R.json] [--json] [--selftest]`.
  Don't use for: general PII detection — it's a fixed pattern-class net (card/SSN/routing/account shapes
  only), not a classifier for every kind of sensitive identifier.
- **`system/parts/fanout_gate.py`** — compares what was CAPTURED at a fan-out boundary against what the spec
  EXPECTS (count, type); refuses to let "we saw nothing" silently mean "nothing ran." CALLERS: none shipped;
  reachable only via `emit_gate.py`'s dispatch table (`PART_TRACES["fanout_gate"]`) and `route_to_part.py`'s
  classifier — planning-weekly's own prompt mentions its captured-record *shape* but the literal subprocess calls
  in that skill run `fanout_completeness.py` and `map_carry_receipt.py` instead. INTERFACE:
  `fanout_gate.py --captured C.json [--expect-count N] [--expect-types "a,b"] [--quiesced] [--json]
  [--selftest]`. Don't use for: judging whether each sub-agent did GOOD work — its own docstring is explicit
  that it proves returns were collected, never that the work was good.
- **`system/parts/section_present.py`** — a required section, heading, or callout must literally appear (and
  show what it promises); the mirror image of forbidden_content. ⚠ **CORRECTED 2026-08-07** — also mislabelled
  "no caller found anywhere" in the source brief; more precisely it has the **same profile as write_ledger
  above**: no shipped-skill caller, but a live dispatch entry in `emit_gate.py`
  (`PART_TRACES["section_present"]`, exercised in the factory's own tests against two real routed planning-weekly
  clauses). INTERFACE: `section_present.py --rules R.json --artifact A.md [--section "..."] [--json]
  [--selftest]`. Don't use for: proving the content under a present section is correct — presence only.

### Category error, not a missing build — the "capture gate" row

`system/parts/capture_gate_selftest.py` is **not** the primitive itself — it is the primitive's self-test.
The primitive is `system/hooks/scratch_capture_gate.sh`, a registered **Stop hook**
(`system/reference/settings.json:533`), structurally a hook, not a skill-local script, which is why it never ⛔ ARCHIVED 2026-09-05 — catalogue entry moved out of the live SOP; the path was hand-kept and had drifted (see the pointer in §II.4); regenerate by script before trusting
belonged in the same table row-format as the other four. It is also the **one part in the library that
deliberately FAILS OPEN** — a wedged turn was judged worse than a missed checkpoint — so a clean exit here
proves less than a clean exit anywhere else in this section: don't read "gate passed" as "state was captured
on every possible path."

### Tier 3 — BUILT, ZERO CALLERS ANYWHERE, not even the factory's own dispatch table

The real anti-pattern §V.9 names as `validator-exists-but-nothing-calls-it`. Unlike Tier 2, nothing — no
shipped skill, no factory dispatch entry — currently runs these:

- **`system/parts/routing_evals.py`** — tests whether a skill's `description:` fires on SHOULD-FIRE prompts
  and stays silent on BOUNDARY prompts. `route_to_part.py:322` classifies clauses toward it, but no
  `emit_gate.py` dispatch entry exists, so a routed clause dead-ends unresourced. INTERFACE:
  `routing_evals.py --cases CASES.json (--description "..." | --description-file F) [--k N] [--model sonnet]
  [--json] [--selftest]`. Don't use for: proving a skill routes correctly on prompts outside its own
  should-fire/boundary set — it only checks the cases you hand it.
- **`system/parts/accrual_gate.py`** — refuses a compounding-saving counter (cache-hits, notes-served, ...) ⛔ ARCHIVED 2026-09-05 — catalogue entry moved out of the live SOP; the path was hand-kept and had drifted (see the pointer in §II.4); regenerate by script before trusting
  that a skill advertises as compounding but that never actually leaves zero. No dispatch entry, no shipped
  caller — only a catalog mention in `system/parts/README.md` and a `route_to_part.py` classification entry. ⛔ ARCHIVED 2026-09-05 — catalogue entry moved out of the live SOP; the path was hand-kept and had drifted (see the pointer in §II.4); regenerate by script before trusting
  INTERFACE: `accrual_gate.py --history H.json [--counter-name NAME] [--json] [--selftest]`. Don't use for:
  verifying the counter's arithmetic — only that it isn't stuck at zero.
- **`system/parts/fanout_budget.py`** — actual vs DECLARED cost budget (turns, tokens, wall-clock) per agent, ⛔ ARCHIVED 2026-09-05 — catalogue entry moved out of the live SOP; the path was hand-kept and had drifted (see the pointer in §II.4); regenerate by script before trusting
  else CANNOT EVALUATE. Referenced only as a "captured-record shape" by the experimental
  `system/tools/fanout-lab/` tooling (a lab, not a shipped skill or the factory pipeline) and classified by ⛔ ARCHIVED 2026-09-05 — catalogue entry moved out of the live SOP; the path was hand-kept and had drifted (see the pointer in §II.4); regenerate by script before trusting
  `route_to_part.py`; no dispatch entry, no live caller. INTERFACE: `fanout_budget.py --captured C.json
  --budget B.json [--quiesced] [--json] [--selftest]`. Don't use for: judging whether a fan-out's OUTPUT was
  worth its cost — only whether the cost stayed inside the declared number.
- **`system/parts/voted_judge.py`** — runs an LLM judgment K times on identical input and folds the votes by a
  non-majority rule (Law 4.3: an LLM can't reliably judge the same evidence twice). No dispatch entry in
  `emit_gate.py` (only a string constant, never invoked); `system/tools/conformance-lab/t5_grade.py` calls a ⛔ ARCHIVED 2026-09-05 — catalogue entry moved out of the live SOP; the path was hand-kept and had drifted (see the pointer in §II.4); regenerate by script before trusting
  same-named but *different* local function in `conformance.py`, not this file. INTERFACE: `voted_judge.py
  --clause C --evidence-file E [--k N] [--selftest] [--mode] [--probe] [--controls] [--live-canary]`. Don't
  use for: a deterministic gate substitute — it stays non-deterministic by definition, just less so than one
  sample.

### Also live, and absent from the `system/parts/` catalogue entirely

These aren't in the 19-count (they live in `system/tools/`), but they're production mechanisms a builder
reaching for a primitive should know exist before writing a new one:

- **`system/tools/ingest_setdiff.py`** — the older, production-proven completeness mechanism
  `completeness_receipt.py`'s own docstring credits as its origin. CALLERS: `system/tools/ingest_coverage.py`,
  `system/tools/conformance-lab/{state_seam.py,canary.py,_experiment_wired_drop.py}`,
  `skills/ingest/SPEC.md`.
- **`system/tools/gauge_check.py`** — the mechanical referee for a brief's `## CURRENT STATE` section: counts, ⛔ ARCHIVED 2026-09-05 — catalogue entry moved out of the live SOP; the path was hand-kept and had drifted (see the pointer in §II.4); regenerate by script before trusting
  measures, and compares dates; makes zero judgment calls. CALLERS: `system/tools/checkin_open.py`, ⛔ ARCHIVED 2026-09-05 — catalogue entry moved out of the live SOP; the path was hand-kept and had drifted (see the pointer in §II.4); regenerate by script before trusting
  `system/tools/health_line.py`, `skills/checkin/SKILL.md`.
- **`system/tools/skill_promise_check.py`** — cross-checks a SKILL.md's own stated promises against its own
  instructed commands, catching a file that contradicts itself. CALLERS: `system/tools/skill_promise_sweep.py`,
  `agents/archivist.md`, `skills/archivist-audit/SKILL.md`.
  ⛔ `agents/archivist.md` is the donor's path and is not here. The charter itself DID land — it ships as
  `.claude/agents/archivist.md`; only the top-level `agents/` location did not come across (migration note, 2026-08-15).

