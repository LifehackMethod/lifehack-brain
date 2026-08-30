---
element: efficiency
title: "efficiency — element detail (ground/base altitude)"
subsystem: efficiency
altitude: base
record_type: organism-element
maturity_label: LIVE·gap
gap_disposition: defect
gap_disposition_note: "TWO gaps, and they are different in kind. GAP-1 is a DEFECT and is the honest reason this element is PARTIAL: the ground reasoner `recommend.py` has NO CALLER and `state/recommendations/` DOES NOT EXIST ON DISK, so nothing has ever flowed end to end — zero recommendations have been produced in production (measured 2026-08-05 by direct `ls` and by a live read-only `health_line.py` run that printed no RECOMMENDATIONS line). This is deliberate, not an oversight: CUT-E holds the scheduling pending a prove-live-once supervised run the operator said he wants to watch. It is recorded as a defect anyway, because an element that reads as working while its pipeline has never carried a load is precisely the false-green this subsystem exists to kill. GAP-2 is BY DESIGN: Efficiency SUGGESTS and never APPLIES (RULED 2026-08-04 by the operator, plan §18.5), so the absence of any applier is correct and must never be `fixed`."
generated_from:
  - system/tools/emit_recommendation.py
  - system/tools/recommend.py
  - system/tools/fault_proposer.py
  - system/tools/recommendations_reader.py
  - system/tools/recommendation_disposition.py
  - system/tools/fault_ledger.py
  - system/tools/fault-proposer-run.sh
  - system/tools/health_line.py
  - system/tools/findings_reader.py
  - system/hooks/guard_findings_write.sh
  - system/hooks/session_context_loader.sh
  - system/pulse-config.md
created_at: 2026-08-05
updated_at: 2026-08-05
status: draft
authority: agent
---

# efficiency — element detail

> **ALTITUDE.** This is the ENCYCLOPEDIA base. Up one rung is `system/organism/manual.md`
> (`## efficiency`); up two is the always-loaded map tip. Down is the code itself, named in
> `generated_from:` above. **This file was written FROM THAT CODE on 2026-08-05, never from the design.**

> **One-line:** **Efficiency reads ACROSS what is wrong and proposes how the organism should evolve — so
> the system gets sharper with use instead of duller.**

> **⛔ BOUNDARY.** Hospital **DETECTS and RANKS** one problem at a time. Efficiency **REASONS ACROSS**
> problems and **PROPOSES**. **It SUGGESTS. It never APPLIES.** ⚖ RULED 2026-08-04 by the operator (`§18.5`);
> auto-fix was CUT 7/7 by council. There is no applier anywhere in this element, at any altitude, and
> `§18.15` verification step 6 exists solely to `grep` for one and confirm it does not exist.

## AUTHORED   (human-only)

### ⚑ PURPOSE — carried verbatim from the intent declaration

**Efficiency exists so the system gets SHARPER with use instead of duller. Entropy is the default — junk
accumulates, parts rot, seams fray. Efficiency is the counter-force: it reads what is wrong, reasons
ACROSS findings rather than one at a time, and proposes how the organism should evolve.**

The operator, verbatim, 2026-08-04 — the sentence the whole subsystem is built on:

> *"As a lot of these systems exist, they actually start to get duller, not sharper... Really what we
> want is we want the system to sharpen itself, right — we want this to be something like **the more this
> blade gets used, the sharper it gets.**"*

### WHY EFFICIENCY EXISTS (the founding problem)

Hospital answered *"what is broken?"* one item at a time and ranked the answers. That left a question
nothing in the system could ask: **"what do these broken things, taken together, say we should DO?"** A
ranked list of forty faults is still forty decisions for a human. Efficiency is the layer that reads the
list as a whole and returns a smaller number of proposed acts, each carrying the evidence that produced
it — at three altitudes, because a fix to one part, a fix to a seam between parts, and a change to the
architecture are different kinds of answer and must not be collapsed into one.

### ARCHITECTURE OVERVIEW

| Component | File | Role |
|---|---|---|
| The validating writer | `system/tools/emit_recommendation.py` | the ONE way a recommendation enters the store; validates producer/altitude/action/evidence, fingerprints, appends JSONL |
| The ground reasoner | `system/tools/recommend.py` | reads Hospital findings, asks for an altitude verdict, writes through the writer. **NO CALLER — see GAP-1** |
| The altitude grader | `system/tools/fault_proposer.py` | grades INSTANCE / SUBSYSTEM / ORGANISM from recurrence; the DECISION gate; refuses what it cannot cite |
| The union reader | `system/tools/recommendations_reader.py` | reads the store back with shard + degradation accounting |
| The human's answer | `system/tools/recommendation_disposition.py` | records accept/reject against a fingerprint. **BUILT, NEVER RUN — see GAP-3** |
| The review surface | `system/tools/health_line.py` | prints open recommendations at session start, ranked, capped at 3 |
| The store guard | `system/hooks/guard_findings_write.sh` | blocks any write to the store that bypasses the writer |

### ⭐ THERE IS NO MODEL IN THIS SUBSYSTEM

**Efficiency is fully deterministic code, end to end. No LLM runs at any altitude today.** Verified
2026-08-05 by grepping every file in `generated_from:` for `claude` / `CLAUDE_BIN` / `anthropic` /
`subprocess` / headless-invocation patterns. ⚠ **CORRECTED 2026-08-27** (L.B2 audit, re-run live):
the "zero hits" half is false as literally stated — the grep DOES hit the substring "claude" inside
naming like `claudeops-config`/`CLAUDEOPS_DRIVE` (not an invocation) in `fault_proposer.py`,
`recommend.py`, `fault_ledger.py`, plus real `subprocess.run(...)` calls in `health_line.py`
(inspected: both shell out to `pm_flag.sh` and `gauge_check.py`, deterministic local tools, not an
LLM). So the substantive conclusion — **no LLM/Claude invocation exists in this subsystem** —
still holds on inspection; only the "zero hits" grep-count claim itself was wrong.

⇒ **No code/LLM seam exists inside Efficiency**, so LAW 1 (the seam) and LAW 1b (model-reach) do not bind
it as built. ⚠ **This sentence has an expiry date.** The purpose statement above explicitly anticipates
judgment — *"the beauty of LLMs is that when we have somewhere to feed it, it can use some type of
judgment"* — and the two upper altitudes (`T18.10` / `T18.11`) are where a model would first appear. **The
day one is introduced, both laws start binding and this section must be rewritten, not amended.**

### THE WRITE CONTRACT (`emit_recommendation.py`)

One writer, one door. It validates the producer, the altitude against a closed set, the action, the
labels, and — the load-bearing one — **the evidence**. A call with empty evidence is **refused** with a
`RecommendationContractError`.

★ **And the refusal is not silent: a canary is written BEFORE the raise.** This is Hospital's most
expensive lesson carried forward rather than re-learned — **A REFUSAL IS NOT A RECORD.** Blocking a bad
write leaves no trace unless the blocked condition is itself emitted; in Hospital that defect bit twice,
once at the writer and once at the consumer.

### THE STORE

`state/recommendations/<altitude>.<machine>.jsonl` — append-only JSONL, sharded on the axis a human
actually reviews (the altitude), with the machine token **in the PATH**, never only in the payload. That
path shape is the RESIDENCY LAW, and it is not stylistic: a file that tagged itself internally still
forked nine ways across 1,169 rows.

Dispositions live one level down at `state/recommendations/dispositions/dispositions.<machine>.jsonl`,
and the union reader is deliberately non-recursive so it does not swallow them.

**⛔ AS OF 2026-08-05 THIS DIRECTORY DOES NOT EXIST.** It is created on first write; there has never been
a first write. See GAP-1. ⚠ **CORRECTED 2026-08-27** (L.B2 audit, live `ls -la`): the directory
now EXISTS with substantial, current, real content — `ORGANISM.mba.jsonl` (962,097 bytes, last
modified 2026-08-22), `SUBSYSTEM.mba.jsonl` (26,588 bytes, 2026-08-05), and a populated
`dispositions/dispositions.mba.jsonl`. A live run of `health_line.py` against the real ledger path
confirms it: a `RECOMMENDATIONS: 65 recommendation(s)` line, ranked and capped at 3 shown. The
2026-08-05 measurement was accurate THEN; it is stale now. `recommend.py` genuinely still has no
wired `-run.sh` caller (confirmed via `system/pulse-config.md:394-397`, "NOT PORTED"), so
recommendations are most likely reaching the store via `fault_proposer.py` / other direct
`emit_recommendation` callers, not via `recommend.py` — but the store is unambiguously live and
loaded with real data today, the OPPOSITE of "zero recommendations in production."

### THE GRADING LAYER (`fault_proposer.py`) — and its ownership

`choose_altitude()` grades a fault INSTANCE / SUBSYSTEM / ORGANISM from recurrence data in the lifecycle
store, and quotes the evidence that chose the altitude inside the proposal. `propose()` adds two rules
that matter more than the grading:

1. **THE DECISION GATE** — it refuses to propose a fix for a job a human **deliberately parked**. This
   exists because of the `4d5c1af` incident, where an auto-resurrected job processed 43 real consulting
   threads. ⚠ **On 2026-08-05 this gate was found VACUOUS** — a key-shape change had it comparing a
   sha256 against real job names, so it could never match. It had not misfired only because nothing was
   parked. **A vacuous gate's silence is indistinguishable from a working gate's silence.** Fixed.
2. **EVIDENCE OR REFUSE** — it will not propose what it cannot cite.

⚖ **OWNERSHIP: this file is EFFICIENCY'S, not Hospital's. RULED 2026-08-05 by the operator (`T18.8`)**, and the
file's own header records the ruling. ⚠ **Two artifacts have not caught up** — `system/pulse-config.md`
still labels the daily job *"fault-proposer: HOSPITAL's runner"*, and `fault-proposer-run.sh`'s header
still frames the tool in Hospital terms. Both are stale-by-one-day rather than wrong-in-substance;
`elements/hospital.md` already carries the corrected boundary.

### THE SESSION-START REVIEW SURFACE (`health_line.py`)

Efficiency's output reaches a human exactly one way: a `RECOMMENDATIONS:` line at session start, appended
alongside — never replacing — Hospital's `FINDINGS:` line. Open recommendations are ranked
**DECISION > ORGANISM > SUBSYSTEM > INSTANCE**, capped at 3, each shown with an 8-character fingerprint
prefix that `recommendation_disposition.py` accepts directly, so the path from *reading* one to
*answering* it is a single command.

**It is silent when there is nothing to say** — which today is indistinguishable from the store being
empty, because the store IS empty. (One silence IS now distinguished: the session floor rc-checks
`health_line.py` and says so when the tool itself could not run — see `elements/hospital.md`, which
owns the wiring description.)

### GATES AND ENFORCEMENT (the honest map)

**Script-level (a hook or code actually stops you):**
1. `guard_findings_write.sh` — ~~mode `444`~~ **CORRECTED 2026-08-27** (L.B2 audit, live
   `ls -la` + live test): actual file permissions are `-rwxr-xr-x` (755) — no "444" appears
   anywhere in the script or its `registrations.json` entry. The mode-444 detail is wrong; the
   enforcement mechanism itself is real and confirmed live — a synthetic Write into
   `state/recommendations/ground.machine.jsonl` ⛔ (a synthetic test path used only for this live
   probe, not a real store file) was blocked, exit 2, with the exact "VALIDATED
   STORE" reasoning text, registered at `registrations.json:282` (matcher `Bash|Write|Edit`) —
   registered, blocks any Bash/Write/Edit into
   `state/recommendations/` (including `dispositions/`) that does not go through
   `emit_recommendation.py`. It resolves shell variables before matching, closing the variable-path
   bypass found as `T15.32`.
2. `emit_recommendation.py`'s own contract — the evidence check, the closed altitude set, the fingerprint.

**Honor-system (prose only, nothing enforces it):**
3. **PROPOSE-ONLY.** Nothing mechanically prevents a future task from writing an applier. The only
   defence is `§18.15`'s verification step, which greps for one — and a grep runs when someone runs it.
4. **The purpose statement.** Carried verbatim in four places by convention, reconciled by nobody.

### GAPS (documented fail-open conditions)

**GAP-1 · THE PIPELINE HAS NEVER CARRIED A LOAD — the honest reason this element is PARTIAL.**
`recommend.py` has **no caller** (grepped repo-wide, including `pulse-config.md`: every hit is inside the
file itself) — that half stands, re-confirmed 2026-08-27. ~~and `state/recommendations/` **does not
exist**. Zero recommendations in production.~~ **CORRECTED 2026-08-27** (L.B2 audit): the store
now exists and holds 962KB+ of real data and 65 live recommendations — see THE STORE section
above. The gap that remains is narrower than originally scoped: `recommend.py` itself is still
unwired, but the recommendations subsystem overall is NOT dark — something else (most likely
`fault_proposer.py`) is already writing through `emit_recommendation.py`.
⇒ **The judgment is proven; the plumbing is not fully wired, but data IS flowing.** Deliberate (CUT-E),
pending a supervised first run of `recommend.py` specifically.
★ This is the same **writer-with-no-reader** disease that left `fault_proposer.py` dark for eleven days —
recurring inside the subsystem built one rung above it.

**GAP-2 · NO APPLIER, BY DESIGN.** Not a defect. ⚖ RULED 2026-08-04 by the operator. Never "fix" this.

**GAP-3 · NOTHING RECORDS WHETHER THE LOOP CLOSED.** `recommendation_disposition.py` (486 lines) is the
primitive that would record a human's accept/reject. It is wired to the read side and **has no runner and
no evidence of ever having been invoked.** ⇒ Efficiency cannot distinguish *"nobody needed to act"* from
*"nobody looked"* — which is exactly the condition that let a correct ORGANISM verdict go unheeded for
days on 2026-08-05. **Surfaced as a 10,000-ft candidate, not decided here.**

**GAP-4 · THE STORE GUARD IS PROVEN ON ONE MACHINE.** Watched firing on the primary machine only; the
second machine has been dark since 2026-07-04. A hook whose symlink is missing on a machine never fires and never errors.

### INTEROP SEAMS (organism view)

1. **`efficiency` READS `hospital`.** `recommend.py` consumes the findings union via `findings_reader.py`.
   Hospital's contract change is Efficiency's outage — this is the tightest coupling in the pair.
2. **`efficiency` SHARES-STORE-WITH `hospital`.** One guard, `guard_findings_write.sh`, protects both
   `state/findings/` and `state/recommendations/`. One hook, two subsystems: hardening it helps both, and
   breaking it blinds both.
3. **`efficiency` FEEDS `health-line`.** The session-start line is the ONLY surface where Efficiency
   reaches a human. If that line is suppressed, Efficiency is functionally absent.
4. **`efficiency` TRIGGERS-BY `pulse-cron`.** Only `fault-proposer` (daily, 86400s) is scheduled. The
   reasoner is not — see GAP-1.
5. **`efficiency` KEYS-OFF `two-machine-residency`.** Machine token in the path; one writer per path per
   machine.
6. **`efficiency` COMPLEMENTS `backlog`.** ⚖ RULED 2026-08-05 by the operator: the debt ledger is Efficiency's
   **INPUT, not its exile** — *"anything that's broken and needs fixed falls under the purview of
   Efficiency."* Efficiency may DEMOTE and ARCHIVE ledger items under the `§18.5a` carve-out (positive
   evidence only). **NOT YET BUILT** — that is `§18.18`.
7. **`efficiency` GUARDED-BY `guard_findings_write.sh`** — and by nothing else.

### INTENT / CURRENT-VS-TARGET

*Efficiency should read across everything the system knows is wrong and return a small number of
evidence-backed proposals, at the altitude that fits each — so that a human spends judgment on decisions
rather than on triage, and the organism evolves deliberately instead of accreting.*

**Current state → PARTIAL, for three cited reasons:**
1. **Only the GROUND altitude exists.** 5,000 ft (seams) and 10,000 ft (architecture) are unbuilt —
   `§18.10`, deliberately unscoped, needs the operator in the room.
2. **The ground rung has never run in production** — GAP-1.
3. **The loop has no closure signal** — GAP-3.

**TARGET:**
1. `recommend.py` scheduled after one supervised live run (CUT-E).
2. The 5,000-ft seam lane, whose output names **the seam, the fingerprints, and the targets** — never a
   bare altitude label.
3. The 10,000-ft architecture lane, able to propose both an elimination and an addition.
4. The debt ledger wired as an input (`§18.18`).

### HARD PROHIBITIONS (what Efficiency never does)

- **It never APPLIES a fix.** No applier, at any altitude, ever.
- **It never proposes what it cannot cite.** No evidence → refusal + canary.
- **It never "fixes" a deliberately parked job or a BY-DESIGN stop.**
- **It never writes to the store except through `emit_recommendation.py`.**
- **It never deletes a debt-ledger item on absence of evidence** — positive evidence only; *"leave fifty
  stale items rather than remove one real one."*

### EDGE CASES

1. **An empty store is silent, and silence here is ambiguous** — an empty `RECOMMENDATIONS:` line means
   either "nothing to recommend" or "the reasoner never ran." ~~Today it is the second.~~ **CORRECTED
   2026-08-27** (L.B2 audit): the store is no longer empty — see THE STORE / GAP-1 corrections above.
   A live `health_line.py` run today prints a real `RECOMMENDATIONS: 65 recommendation(s)` line.
   The ambiguity this edge case describes is still structurally real for a genuinely-empty store;
   it just no longer describes the store's CURRENT state. Nothing in the surface distinguishes them.
2. **A recommendation whose underlying fault has since closed** — the store is append-only, so a stale
   proposal can outlive its cause. Disposition is the intended answer; GAP-3 says it is not in use.
3. **A cohort that collapses to one fingerprint** renders ORGANISM evidence as raw `fp:<sha>` for ~9 of 45
   historical keys — cosmetic, railed off, recorded as deferred in `§18.17.7`.
4. **Test pollution has no sanctioned cleanup path** — a `selftest-zero` canary sits in the real findings
   store and cannot be removed, because the bypass that would have allowed it was correctly closed. Named
   three times now; still open.

## AUTO-COMPUTED   (machine-only)

- **maturity_label:** LIVE·gap [provisional]
- **why ·gap:** GAP-1 (no caller, empty store) and GAP-3 (no closure signal) are documented fail-opens
  alongside a working store guard.
- **check_detail:** ⚠ **HAND-SET AT AUTHORING, NOT MACHINE-EARNED — and labelled as such deliberately.**
  The BASE value is machine-owned per the label grammar (`manual.md`) and must be computed by
  `python3 system/tools/organism/label_checker.py write-labels`, which has not yet been run against this
  element. `PARTIAL` is the honest floor regardless of what a fire test returns, because the pipeline has
  never carried a load. ⛔ **This value is stated IDENTICALLY in the frontmatter above — deliberately.**
  ~~`elements/hospital.md` currently disagrees with itself (frontmatter `LIVE·gap` vs this section's
  `PARTIAL·gap`), which is a live false-green inside the false-green subsystem~~ — **CORRECTED
  2026-08-27** (L.B2 audit, live `grep -n "maturity_label" system/organism/elements/hospital.md`):
  this premise is false. Both hospital.md's frontmatter (line 7) and its AUTO-COMPUTED body
  section (line 655) say the SAME thing — `LIVE·gap` / `LIVE·gap [provisional]`. There is no
  `LIVE·gap` vs `PARTIAL·gap` split in that file today; that contradiction is NOT
  replicated here (this element's own self-consistency claim below stands).
