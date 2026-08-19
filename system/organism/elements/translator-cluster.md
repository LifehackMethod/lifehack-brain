---
element: translator-cluster
title: "translator-cluster — element detail (ground/base altitude)"
subsystem: voice
altitude: base
record_type: organism-element
maturity_label: PARTIAL [provisional]
generated_from:
  - skills/simplify/SKILL.md (v2.1)
  - skills/explain/SKILL.md (v4.4)
  - skills/summarize/SKILL.md (v1.0)
  - system/hooks/simplify_anchor_inject.sh ⛔ DELETED 2026-08-05 — see the banner below
  - system/hooks/translator_gate.sh (v7.1; updated 2026-07-13)
  - system/translator-rubric.md (updated 2026-07-15)
  - output-styles/simplify.md
  - system/reference/settings.json (hook registration lines 367-375, 438-446)
  - state/debt-ledger.md (TRANSLATOR-GATE-RIP, TRANSLATOR-OUTPUTSTYLE-SECOND-MACHINE)
created_at: 2026-07-24
updated_at: 2026-07-24
status: draft
authority: user
---

# translator-cluster — element detail

> **Altitude = BASE (ground / street view).** The in-the-weeds detail of how the translator
> cluster actually works — every skill's mandate, the span rule, the re-anchor hooks and their
> real enforcement, the translator-rubric as the shared voice contract, and every interop seam.
> The MIDDLE index (`system/organism/manual.md`) carries only a one-line pointer here; the TIP
> (`CLAUDE.md` schematic) shows only the box + arrows; the **live skills and hooks** are the
> fourth level — the executable runtime ground truth. This entry is the UNDERSTANDING layer.
>
> **LADDER: ELEMENT (full mechanics). up → manual#translator-cluster ; ground truth → the live
> artifacts (generated_from list above)**
>
> **One-line:** a three-skill cluster + two hooks that continuously re-assert a shared voice
> contract, keeping every reply readable on first pass for a low-recall reader juggling windows.

> ⛔⛔ **PORT BANNER — WHAT THIS ELEMENT NAMES THAT IS NOT IN THIS REPOSITORY.** The description below
> is faithful to the donor system and is left exactly as written. These four lines record what happened
> to each named file AT THIS DESTINATION, and each one holds for every mention of that file anywhere
> below — the description is not edited to match the destination, the destination's answer is added beside it.
>
> - ⛔ `system/translator-rubric.md` — the donor path is not coming. The rubric itself DID land here, under a different path: `system/sops/translator-rubric.md`. It ships deliberately dark, carrying a debt note that its enforcement mechanism was killed 2026-07-14 and never rebuilt. Every reference to the donor path below means that file.
> - ⛔ `system/hooks/translator_gate.sh` — excluded from the migration by ruling; not coming, ever. The operator, `authority: user`: *"That old thing that was grading… that's dead. That is definitely dead. Do not migrate that."* Distinct from the rubric above, which does ship — the doc lives, the grader does not. Every sentence below about the gate is donor HISTORY, including the "STILL LIVE in this cluster" line in the next banner.
> - ⛔ `system/hooks/simplify_anchor_inject.sh` — nothing to port: deleted in the DONOR itself on 2026-08-05 as a failed experiment, as the banner immediately below records. There is no per-turn voice re-injection here, and there is no plan for one.
> - ⛔ `/distill` — never ships. It was deprecated in the donor on 2026-06-07 and retired to a tombstone there; it exists in neither tree. `/summarize`'s routing target below therefore has no destination here — the multi-turn distillation path is simply absent.

---

## AUTHORED   (human-only)

### WHAT IT IS AND WHY IT EXISTS

The translator cluster is an always-on voice system — not a formatting rule, not a style guide,
but a live enforcement stack. It exists because response voice decays over long sessions: the
model pattern-matches back to heavy structured-report output as the context grows. The operator re-ran
`/simplify` or `/explain` on roughly every reply (~10×/session or more) before this cluster was
built — a "~2x hand tax" (translator_gate.sh header). The cluster was built to eliminate that
tax by maintaining voice mechanically: one per-turn injection hook re-anchors the register
before every response; one Stop hook grades finished replies.

> ⛔⛔ **BANNER — READ BEFORE TRUSTING ANYTHING BELOW ABOUT `simplify_anchor_inject.sh`.**
> **THAT HOOK WAS DELETED 2026-08-05 (the operator: *"that was a failed experiment"*). It no longer exists.**
> It was unregistered on 2026-07-28 (`1d2ddee`) because **it fired EVERY turn instead of the intended
> 1-in-10**, and it sat unregistered-but-present for nine days.
> ⚠ **WHY THIS BANNER EXISTS AND IS NOT JUST A DELETION:** on 2026-08-05 the `§19` quiet-breakage survey
> found this element (plus `manual.md` and `translator-rubric.md`) still asserting in **five separate
> places** that the hook *"fires before EVERY turn,"* *"fires unconditionally,"* and is *"the voice
> contract for the entire system"* — while it had been switched off for nine days. **Nothing detected
> that, because every detector in this system watches CODE and the false claim lived in the DOCS.** It
> is `§19`'s founding specimen. **The body below is HISTORY from here on: every sentence about
> `simplify_anchor_inject.sh` describes a hook that is gone.**
> ✅ **STILL LIVE in this cluster:** `translator_gate.sh` (Stop, 1 registration) and
> `skill_anchor_inject.sh` (1 registration) — verified from `settings.json` at deletion time. **The
> cluster is not dead; one of its two enforcement hooks is.**
> ⏭ **OWED:** a real rewrite of this element against the post-deletion reality (~20 references below
> still read as live). Filed to the debt ledger as `[TRANSLATOR-ELEMENT-REWRITE]` — banner first so the
> file stops lying tonight, rewrite when it is the actual job.

The **shared voice contract** lives in `system/translator-rubric.md` — the single source of
truth. The three skills (`/simplify`, `/explain`, `/summarize`) each implement one re-render
mode against that contract. The two hooks (`simplify_anchor_inject.sh` and
`translator_gate.sh`) enforce or reinforce the contract mechanically. The
`output-styles/simplify.md` file shapes the baseline voice at session start. ALL of these point
back to the rubric; the rubric says "edit criteria HERE first, then propagate."

---

### THE SHARED VOICE CONTRACT (`system/translator-rubric.md`)

**File:** `system/translator-rubric.md` — updated 2026-07-15, authority: user.

The rubric defines 12 positive criteria and a negative rubric of 5 sins, plus the grader's
unifying single-question test. Every translator-cluster component keys off this file; it is
the element's single load-bearing specification.

**12 positive criteria (from rubric §"The criteria"):**

1. Lead with the answer — TL;DR in first 2–8 lines.
2. Re-anchor every named file/tool/command on first mention — a few words on what-it-is/why.
3. College-freshman altitude — never cryptic, never condescending.
4. Keep the load-bearing tech — translate, don't strip; words simpler, not the meaning.
5. Surface the invisible work — anything off-screen (subagent/code/background run) explained
   in plain words; never name-dropped as if the reader watched.
6. Bold = main points only — skimming bold alone gives the gist.
7. Size to substance — length earned by content; no padding, no crushing.
8. End with a numbered "what needs you" (priority order) + "My call" — on decision-bearing
   turns; never on routine FYI turns.
9. Ask-gate (HARD) — keep only what's genuinely new AND blocking-or-materially-helpful;
   drop settled re-asks and bare permission; every kept question self-contained + carries a
   recommendation; label ask-vs-permission plainly.
10. Plain sentences over heavy scaffolding — full human sentences with bold lead-ins +
    bullets to scan; never a wall of prose or dense nested bullets.
11. Rank thoughts (nucleus/nested), map then unpack — adaptive: TL;DR maps territory; numbered
    body leads each point with its bold nucleus; short/exploratory replies aren't over-structured.
12. Surface the delta — where it was → where it is now; only when the prior state is known,
    never manufactured.

**5 sins (the negative rubric — the grader fails on these):**

1. Reads like a report — stacked labeled section-headers + nested bullets instead of plain
   sentences leading with the answer.
2. Buries the point — answer/verdict not in the first few lines.
3. Unanchored jargon — file/tool/term named with no gloss.
4. Parenthetical clutter — asides piled onto many lines, breaking the read.
5. Scattered coordinates — file paths/line numbers sprinkled through the body. Fix: gather
   into a Reference section at the end; keep the body plain.

**Grader's unifying test (v6, 2026-07-12):** "You are an intelligent college freshman who has
NOT been paying close attention. Reading this once, would you get the point and what's asked
immediately — or be even slightly confused / have to re-read / hit a term you lack context
for? Fail if you'd have to work at all."

Structural sins (reads-like-a-report, scattered-coordinates) → cheap **mechanical count** in
`translator_gate.sh` (section-headers ≥5, coordinate-tokens ≥6). Everything else → the single
holistic model question.

---

### THE THREE SKILLS

#### `/simplify` (skills/simplify/SKILL.md — v2.1, updated 2026-07-14)

**Mandate:** CONDENSE. Re-render everything since the user's last message shorter, plainer,
conversational — keeping every fact a decision rests on. Does NOT unpack or expand.

**Span rule (shared by all three):** re-renders everything since the **user's last message** —
not just the last response, not the whole thread. That span can be several assistant turns
(including background/cron turns) since they last spoke.

**Mandate distinction:**
- `/simplify` = CONDENSER. Shortens. Keeps decision-bearing facts. Translates jargon. Drops
  what isn't load-bearing.
- `/explain` = UNPACKER. Keeps ALL technical detail; drops nothing. Reorders freely.
- `/summarize` = GIST-REPORTER. Last response only. ≤3 sentences. Thinnest of the three.

**Key behaviors:**
- Surface the invisible work (anything off-screen → one plain line of what it did).
- Surface the delta (where it was → where it is now; only with prior state).
- Re-anchor every named file/tool in a few words.
- Lead — give the read and a recommendation; never just set the data down and go quiet.
- Close label rule (shared with `/explain`): gate the question (drop settled re-asks, bare
  permission, manufactured questions); label plainly: NEED / PERMISSION ONLY / NOTHING.

**Shape:** utility. Trigger: `/simplify`. Fully autonomous one-shot.

---

#### `/explain` (skills/explain/SKILL.md — v4.4, updated 2026-07-17)

**Mandate:** UNPACK + TRANSLATE. Re-render everything since the user's last message as the
clearest human translation — ALL technical detail kept, none dropped, reordered freely for
readability. Invoking `/explain` is itself proof the last output was too technical or moved
too fast.

**Span rule:** same as `/simplify` — since the user's last message.

**Mandate distinction from `/simplify`:** `/explain` keeps EVERY technical element; dropping
detail is `/simplify`'s job, never `/explain`'s. Reorders freely (the original order isn't
sacred). Adds the missing context, makes reasoning visible — a hint of context, never a flood.

**Key behaviors (beyond shared rubric):**
- RANK, THEN MAP-THEN-UNPACK — sort into nucleus + nested thoughts; lead with a TL;DR that
  maps the territory; numbered body where each point leads with its bold nucleus.
- Size to the comprehension gap: a bit more than the original gave, then STOP. Over-unpacking
  into a wall is its own failure.
- Lead with the answer, not with the method.
- Close label rule: same ask-gate as `/simplify` — gate, self-contain, label.

**Note:** the Step 8 handoff of `/save` specifies the two-pass voice-seed DRAFT → re-render
uses `/explain` voice (not `/simplify`), because a handoff's whole job is completeness and
`/simplify` condenses. This is the cluster's most-cited typed interop seam. (See INTEROP.)

**Shape:** utility. Triggers: `/explain`, "explain that", "what did that mean". Autonomous
one-shot.

---

#### `/summarize` (skills/summarize/SKILL.md — v1.0, updated 2026-05-25)

**Mandate:** GIST. Briefest of the three. Last response only — not the full thread, not the
span. ≤3 sentences, plain prose, no bullets, no headers. One sentence per main point of the
last response; lead with the single most important takeaway.

**Span rule (different from the other two):** last response only. For full-thread or
multi-turn distillations, route to `/distill` instead.

**Format (R-6):** ≤3 sentences, plain prose, no bullet lists, no headers.

**Shape:** utility. Trigger: `/summarize`. Autonomous one-shot.

---

### THE TWO HOOKS

#### `simplify_anchor_inject.sh` — UserPromptSubmit inject

**File:** `system/hooks/simplify_anchor_inject.sh` (v2; 41 lines; updated 2026-07-23)
**Registration:** settings.json line 372 — UserPromptSubmit event, empty matcher (fires EVERY
turn). `[hook]` inject.
**Status message:** "Re-anchoring response register..."

**What it does:** re-asserts the translator register EVERY turn by printing one of 10 rotating
variant lines to stdout before the user's message is processed. The rotation prevents the
injection from becoming "wallpaper" — a static re-inject that the model pattern-matches away
(hook-sop §3.3 doctrine: "rotating among variants + active-recall to re-anchor instead of fade").

**10 variants (from SKILL.md comment block):**
- Variant 0: active-recall — "name to yourself the register you're about to write in"
- Variant 1: translator voice description + close format
- Variant 2: drift-detection check — "are you drifting into a structured wall?"
- Variant 3: active-recall — "restate your frame in one line: translator, not solver"
- Variant 4: lead-with-the-answer + re-anchor reminder
- Variant 5: ask-gate rule — drop settled re-asks and bare permission
- Variant 6: rank-then-map-then-unpack (nucleus/nested + TL;DR)
- Variant 7: billionaire-attention framing
- Variant 8: surface-the-delta rule (`[added 2026-07-23]`)
- Variant 9: chief-of-staff framing (`[added 2026-07-23]`)

Selection: `$RANDOM % 10` — no counter/state, no side effects. Load-bearing invariants present
in EVERY variant: lead-with-the-answer · numbered "what needs you" + "My call" · label
ask-vs-permission.

**Cost:** ~<150 tokens per turn (header comment in SKILL.md).

**Enforcement class:** `[inject]` (pre-turn context injection). NEVER blocks. Degrade-safe:
any error → exit 0 silently. Always-on (no flag, no arm). No side-channel log.

**Source of truth signpost (in script header):** "Edit criteria in `system/translator-rubric.md`
FIRST, then propagate here + `output-styles/simplify.md`."

---

#### `translator_gate.sh` — Stop grade-and-bounce

**File:** `system/hooks/translator_gate.sh` (v7.1; 113 lines; updated 2026-07-13)
**Registration:** settings.json line 443 — Stop event, empty matcher (fires on EVERY stop).
`[hook]` — potentially blocking (decision:block in enforce mode).
**Status message:** "Grading reply voice (translator gate)..."

**What it does:** grades each finished reply against the translator rubric and, in enforce mode,
bounces bad ones for a rewrite (decision:block). Experiment vs. hook-sop §1 "don't hook
style/tone" — justified in the header by the 2x-cost economics of re-running `/simplify`
manually.

**DORMANT BY DEFAULT.** The gate does NOTHING unless armed:
- Per-session arm: `/tmp/translator-gate/<sid>.arm` (contains mode: `observe` or `enforce`)
- Global observe-all: `/tmp/translator-gate/OBSERVE-ALL` (forces observe mode on all sessions)
- Disarm: `rm` the arm flag (per-session) or the OBSERVE-ALL flag.
- If neither flag exists: `exit 0` immediately. The gate is SILENT when dormant.

**Two-layer grading pipeline:**

Layer 1 — Mechanical structural pre-check (instant; no model call):
- Bold-opening-line / status-marker count (any line whose stripped content opens with `**...**`): if ≥5 → `[mech]` fail, reason emitted as "[mech] Reads like a report: bold section-headers / status markers."
- Coordinate-token count (file-path/line-number tokens in the top 75% of the body): if ≥6 →
  `[mech]` fail, reason emitted as "scattered coordinates."
- If either fires → skip Haiku grader entirely.

Layer 2 — Haiku holistic grader (fires only when mechanical pre-check passes):
- Model: `claude-haiku-4-5-20251001`
- Prompt: terse demanding-editor prompt (v7.1; CoT + list-flaws-first + 1-5 anchored scale
  + 1 good/1 bad exemplar). One-line worst-flaw, then score 1-5. JSON verdict on last line:
  `{"ok": true|false, "reason": "..."}`. ok=false if score ≤3.
- Timeout: 70s. On timeout → degrade-safe pass (exit 0 — latency is the known cost of
  Layer 2; the header notes "latency is why Layer-3 local model is the real fix").

**Loop-safe:** exits 0 on `stop_hook_active=True` (CC caps blocks at 8).
**Minimum message size:** messages under 200 chars are unconditionally passed.
**Degrade-safe (HARD):** any grader error/timeout → allow stop (exit 0). No false blocks.

**Verdict log:** always appended to `$ARMDIR/${SID}.log` (tab-delimited:
`timestamp | verdict | mode | chars | sec | coord | reason`).

**In enforce mode on fail:** emits decision:block with a bounce reason string pointing back to
`system/translator-rubric.md`.

**⚠ KNOWN ISSUE — TRANSLATOR-GATE-RIP (debt-ledger line 94):** the Haiku holistic grader
is **parked/dormant by default (no arm flag), NOT removed — the code is fully present and
operational when the gate is armed**. It was parked 2026-07-14 (rubber-stamps + ~60s/turn;
the ask-gate now lives in the prompt layer). The gate is STILL REGISTERED as a dormant Stop
hook in settings.json (line 443) + script at `system/hooks/translator_gate.sh`. **Currently
dormant (OBSERVE mode only unless explicitly armed).** The debt item `TRANSLATOR-GATE-RIP`
(state:parked) calls for unregistering and deleting it when the operator gives the go — the
decision is: rip it, or replace its holistic grader with a better model. Until then: the gate
fires on every Stop but exits 0 immediately unless armed — zero runtime cost in steady state.

---

### THE OUTPUT STYLE (`output-styles/simplify.md`)

**File:** `output-styles/simplify.md` (machine-local; NOT git-tracked; NOT symlinked)
**Where Claude Code reads it:** `~/.claude/output-styles/simplify.md` (a real machine-local
dir — does NOT travel via git).

This file shapes the baseline voice at session start as a Claude Code output style. It extends
and instantiates the translator rubric criteria into default-voice prose — "write like the
AFTER" guidance, with the billionaire-framing, the re-anchor rule, the delta rule, and the
ask-gate rule in unified narrative form.

**⚠ KNOWN ISSUE — TRANSLATOR-OUTPUTSTYLE-SECOND-MACHINE (debt-ledger line 93):** the output style
was built on the primary machine. The file was MISSING from `~/.claude/output-styles/` on
the primary machine (the dir didn't exist) → likely a silent no-op before the fix. Fixed on the primary machine with
a **real file copy** (not a symlink — the operator's call for a small stable file). The second machine
has the same gap: `mkdir -p ~/.claude/output-styles && cp ~/lifehack-brain/output-styles/simplify.md ~/.claude/output-styles/simplify.md` — not yet verified as done (debt state:
waiting-external). The `translator_gate.sh` Stop-hook registration does NOT need manual second-machine
setup — `~/.claude/settings.json` is clone-symlinked so it travels via `git pull` (verified
on the primary machine).

**Source truth propagation rule (from `translator-rubric.md` header):** edit criteria in
`system/translator-rubric.md` FIRST, then propagate to `simplify_anchor_inject.sh` +
`output-styles/simplify.md`. These three must stay in sync — the rubric is the single truth.

---

### TRIGGERS — what causes the cluster to fire

1. **`/simplify`** — explicit skill invocation. Re-renders since user's last message,
   condensed.
2. **`/explain`**, `"explain that"`, `"what did that mean"` — explicit skill invocation.
   Re-renders since user's last message, full-detail unpacked.
3. **`/summarize`** — explicit skill invocation. Gists the last response only.
4. **`simplify_anchor_inject.sh` (UserPromptSubmit)** — fires before EVERY user message.
   Silently injects a rotating register-reminder line to pre-anchor voice; no user-visible
   output.
5. **`translator_gate.sh` (Stop)** — fires after EVERY stop. When dormant (no arm flag):
   exits 0 immediately. When armed in observe mode: grades and logs, never blocks. When armed
   in enforce mode: grades and may bounce for a rewrite.

**Usage frequency (ALWAYS-ON):** `/simplify` runs ~10× per session (UNVERIFIED — sourced from
task description as an estimate; no telemetry logged). `/explain` and `/summarize` invoked
on demand. `simplify_anchor_inject.sh` fires on literally every turn — the highest-frequency
component in the cluster.

---

### STORES TOUCHED

| Store | Component | Access |
|---|---|---|
| `/tmp/translator-gate/<sid>.arm` | translator_gate.sh | READ (arm flag; gate dormant without it) |
| `/tmp/translator-gate/OBSERVE-ALL` | translator_gate.sh | READ (global observe flag) |
| `/tmp/translator-gate/<sid>.log` | translator_gate.sh | WRITE (verdict log; always appended) |
| `~/.claude/output-styles/simplify.md` | output style | READ (session start; machine-local, not git-synced) |
| `stdout` (pre-turn context) | simplify_anchor_inject.sh | WRITE (inject variant; invisible to user) |

No Drive writes. No git writes. The cluster is a pure VOICE layer — it touches NO durable
memory stores; it does not write records, canon, journal, or briefs.

---

### GATES AND ENFORCEMENT (the honest map)

The translator cluster is honest-PARTIAL. The per-turn re-injection is live and always-on;
the Stop-grade layer is dormant-unless-armed and carries a known RETIRED-grader debt item.

**What is hook-enforced (`[hook]`):**
- `simplify_anchor_inject.sh` UserPromptSubmit `[hook inject]` — fires unconditionally,
  every turn. Degrade-safe (never blocks). Rotates among 10 variants. This is the primary
  continuous enforcement mechanism.
- `translator_gate.sh` Stop `[hook — dormant by default]` — registered and fires on every
  stop, but immediately exits 0 unless an arm flag exists. In observe mode: grades and logs,
  never blocks. In enforce mode: can emit decision:block. **Currently parked (DORMANT) due
  to TRANSLATOR-GATE-RIP — the Haiku grader is parked/dormant (code fully present and
  operational when armed, but not the default; parked 2026-07-14).**

**What is honor-system (`[honor]`):**
- The three skills' actual re-render quality — no hook verifies that `/simplify` actually
  condensed, `/explain` actually kept all detail, or `/summarize` actually stayed to ≤3
  sentences.
- Voice contract compliance in EVERY non-skill response — `simplify_anchor_inject.sh` injects
  the reminder; whether the model actually writes to the rubric criteria is behavioral
  (honor). The gate grades after the fact but is dormant in steady state.
- The rubric-propagation rule (edit rubric FIRST, propagate to hook + output-style) — no
  hook verifies that all three are in sync after a rubric edit.

**The `(honor)` tip-tag applies:** the PRIMARY behavioral contract of this cluster (voice
compliance on every response) is skill-prose + a per-turn prompt injection — no blocking hook
enforces compliance in steady state. The gate is `[hook]` but dormant.

**Maturity:** `PARTIAL [provisional]` — the injection is live and functional; the grading
layer is parked with a known debt item; the behavioral contract depends on prompt engineering.

---

### GAPS (documented fail-open conditions)

1. **`translator_gate.sh` grader DORMANT (TRANSLATOR-GATE-RIP):** the Haiku holistic grader
   component of the grade-and-bounce layer is parked/dormant by default — code fully present
   and operational when the gate is armed, but NOT the default (parked 2026-07-14 due to
   rubber-stamps + ~60s/turn latency). The gate script remains registered as a Stop hook and
   fires on every stop, but exits 0 immediately unless explicitly armed. Effectively: the only
   active voice enforcement in steady state is the `simplify_anchor_inject.sh` injection (a
   prompt nudge, not a grade). A session with voice drift won't be blocked — it will only get
   the per-turn reminder. The debt item is `state:parked` (waiting for the operator's go to rip it).
   **Blast radius:** every session is ungraded unless manually armed.

2. **`output-styles/simplify.md` machine-local gap (TRANSLATOR-OUTPUTSTYLE-SECOND-MACHINE):** the
   output style file is a real machine-local copy that does NOT travel via git. The second machine
   may not have it yet — if missing, sessions on the second machine run without the baseline output
   style (UNVERIFIED). The per-turn injection still fires; the output style is additive.

3. **Span-since-last-message is honor-only:** the "re-render since the user's last message"
   rule is prose instruction in each skill. No mechanical scope detection enforces it — a
   model could re-render a shorter or longer span without triggering any hook.

**`·gap` verdict:** YES — a session reading only the map gloss and taking "PARTIAL" at face
value might assume a grader actively bounces bad replies. The grader is retired/dormant.
A tip-only reader would misjudge enforcement posture. `·gap` label is warranted.

---

### INTENT / CURRENT-VS-TARGET

**BY DESIGN:**
- `/simplify`, `/explain`, and `/summarize` are explicit on-demand re-render skills — always
  available regardless of the hook state. This is correct and intentional: the human can
  always request a re-render.
- `simplify_anchor_inject.sh` being always-on (no arm flag needed) is by design — the
  re-anchor must fire every turn to counteract voice drift.
- The rubric being the single source of truth with the three-component propagation rule is
  by design — one truth beats three drifting copies (the operator, 2026-07-12).

**Current-vs-target:**
- The `translator_gate.sh` Haiku grader was the target mechanism for automated bouncing.
  It was retired 2026-07-14 as rubber-stamping. The `state:parked` debt item is the tracked
  fork: rip the gate, or replace its holistic grader with a better model / local model
  (header note: "Layer-3 local model is the real fix").
- The `VOICE v2 — DRIFT COUNTER` design (debt-ledger line 215, state:monitoring) would
  add a PostToolUse-on-Skill hook counting `/simplify`+`/explain` invocations per session and
  escalating the re-injection as the count climbs. Deferred 2026-07-12 (Pareto: 60% surface
  for 20% value; prove v1 nudges first).
- The output-style second-machine gap is a known open item (state:waiting-external).

---

### HARD PROHIBITIONS

What the cluster never does:

- No blocking in `simplify_anchor_inject.sh` — ever. It is a pure inject; degrade-safe.
- No `/simplify` voice in Step 8 of `/save` — the handoff uses `/explain` (completeness
  mandate; `/simplify` condenses and would cut load-bearing items).
- No manufacturing a delta that isn't observable from the prior state.
- No manufacturing a question to fill the close — the ask-gate rule is HARD in all three
  skills.
- No re-rendering the whole thread — span is since the user's last message only (not the
  whole thread, not just the last response).
- No treating `translator_gate.sh` as an active bouncer in steady state — it is dormant
  unless armed.

---

### INTEROP SEAMS (shared-state edges to other elements — the organism view)

**1. COMPLEMENTS all response outputs — the widest seam.**
`simplify_anchor_inject.sh` fires before EVERY turn across every desk, every skill, every
agent. The translator cluster is not a desk-specific element — it is the voice contract for
the entire system. Every other element in the organism produces outputs that the cluster's
injection shapes.

**2. CHAINS → `/save` Step 8 handoff (explicit typed-verb seam).**
The `/save` element's Step 8 continuation handoff specifies a two-pass DRAFT → `/explain`
re-render as its voice-seed. This is the only place in the system that calls a translator
skill as a REQUIRED intermediate step in another skill's flow. The rubric contract's quality
directly affects the handoff's readability — a voice drift in the cluster degrades `/save`'s
most critical output.
Referenced in: `skills/save/SKILL.md` Step 8; `system/organism/elements/save.md` line 758
(check_detail, Step 8 two-pass voice-seed `[honor]`).

**3. KEYS-OFF `system/translator-rubric.md` — the shared contract hub.**
All five cluster components (3 skills + 2 hooks) key off this file as the authority on what
"translator voice" means. A rubric edit must propagate to: `simplify_anchor_inject.sh` (all
10 variants), `output-styles/simplify.md` (baseline voice), and the three skills' SKILL.md
files. The propagation chain is honor-system (no hook verifies sync).

**4. SYNCS with `output-styles/simplify.md` (baseline voice at session start).**
The output style is the session-startup voice baseline; `simplify_anchor_inject.sh` is the
per-turn re-anchor. They both implement the same rubric criteria — changes to the rubric must
land in both. Out-of-sync = the baseline says one thing at start and the injection says
another mid-session.

**5. COMPLEMENTS `/distill` (parallel non-redundant).**
`/summarize` explicitly routes full-thread or multi-turn distillations to `/distill`. `/distill`
is the deep-synthesis path; `/summarize` is the last-response gist. These are complementary
non-redundant tools for different scopes.

**6. READS `$RANDOM` (state-free rotation).**
`simplify_anchor_inject.sh` uses `$RANDOM % 10` for variant selection — no file state, no
counter, no log. Variant distribution is uniform; the rotation is the mechanism that prevents
a single variant from becoming wallpaper. No side-channel observable from outside the hook.

**7. GUARDED-BY no external guard.**
The cluster has no PreToolUse guard protecting it. It IS the enforcement surface for other
elements' voice. No other hook guards the cluster's own execution.

---

## AUTO-COMPUTED   (machine-only — hand-set at authoring; the F1.5 checker will own this once built)

- **maturity_label:** PARTIAL [provisional]
- **check_detail:** `simplify_anchor_inject.sh` (UserPromptSubmit, always-on, settings.json
  line 372) — LIVE, firing every turn, 10-variant rotation. `translator_gate.sh` (Stop,
  settings.json line 443) — REGISTERED but DORMANT: exits 0 immediately unless `/tmp/
  translator-gate/<sid>.arm` or `OBSERVE-ALL` exists. Haiku grader is parked/dormant by
  default (code fully present, operational when armed; parked 2026-07-14 — not removed)
  (TRANSLATOR-GATE-RIP, debt-ledger line 94, state:parked). `output-styles/simplify.md` —
  present on the primary machine (`~/.claude/output-styles/simplify.md`); second machine status UNVERIFIED
  (TRANSLATOR-OUTPUTSTYLE-SECOND-MACHINE, debt-ledger line 93, state:waiting-external). Three skills
  (`/simplify` v2.1, `/explain` v4.4, `/summarize` v1.0) — all active, skill-prose only,
  no hook verifies re-render quality. Voice contract compliance on non-skill responses is
  honor-system (prompt injection, not blocking). Mixed: one always-on inject hook LIVE +
  dormant grader + honor-system skill quality → PARTIAL. `[provisional]` because the
  cluster's maturity assessment may sharpen once the TRANSLATOR-GATE-RIP decision resolves.
