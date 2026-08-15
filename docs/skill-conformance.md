# Skill conformance — what a SKILL.md must declare

> **What this is for.** A skill is only useful if the harness can find it and a person can tell what it
> does without opening it. This page is the small set of rules that makes both true. It is a checklist,
> not a framework: if you are writing a skill, everything you need is on this page.

## The one required field: `shape:`

Every `SKILL.md` declares what KIND of thing it is. There are three, and all 33 skills shipped here
already use them (counted 2026-08-14; `ls .claude/skills/ | wc -l` is the live source, since this
number moves — it was 32 earlier the same day this page was checked):

| `shape:` | what it means | how it starts |
|---|---|---|
| `command` | you type it and it does a bounded thing | you invoke it, e.g. `/websearch` |
| `interactive-workflow` | it works THROUGH something with you, in phases | you invoke it, then it asks you things |
| `utility` | another skill or tool calls it; you usually do not | called, not typed |

A skill that genuinely has two modes may declare a list: `shape: [command, interactive-workflow]`.
Prefer one. If you cannot pick, the skill is probably two skills.

## The frontmatter

```yaml
---
name: the-skill-name          # matches the folder name
description: Use when …       # REQUIRED — this is what makes the skill discoverable
shape: command                # one of the three above
---
```

⚠ **`description:` is not decoration.** The harness auto-triggers a skill by matching intent against
this line — a skill with no readable description is invisible, no matter how good it is. Write it as
*"Use when <the situation>"*, in the words a person would actually use, not the words you named the
file. This is enforced: `system/hooks/enforce_skill_frontmatter.sh` blocks a `SKILL.md` written
without one.

## What a skill file should contain, by shape

**All three:** the frontmatter above · a one-line statement of the outcome it produces · the steps, in
the order they run · what it writes and where, if it writes anything.

**`interactive-workflow` also:** the phases, named · what it asks the person at each one · what
"done" looks like. If it can end without reaching an outcome, say so and say what that looks like —
a workflow with no legal way to say *"nothing was decided"* will invent a decision instead.

**`utility` also:** its inputs and outputs, precisely, because its caller is code or another skill and
cannot ask a clarifying question.

## Checklist

- [ ] `name:` matches the folder
- [ ] `description:` starts *"Use when…"* and reads like a person's problem, not a feature name
- [ ] `shape:` present and one of the three
- [ ] The outcome is stated in the first few lines, not buried
- [ ] Anything it writes is named, with its path
- [ ] If it can fail or stop early, that path is written down

---

## ⛔ WHAT THIS PAGE DELIBERATELY DOES NOT COVER — read before you go looking for it

The donor system this `shape:` taxonomy came from ran skills on a schedule, wrote dashboard tiles, and
grouped skills under "desks". Its conformance rules were built around that: a `cron-producer` shape, a
`desk:` field, an `emit_tile:` field, a mandatory `JUDGMENT_SPEC` block for scheduled skills that call
a model, a diary write-helper contract (`emit_diary`), and a seventeen-rule matrix (CF-1 … CF-17)
describing which sweep or hook enforces each one.

**None of that was adopted as a skill-authoring requirement here.** No `SKILL.md` in this repo
declares `shape: cron-producer`, none carries `desk:`/`emit_tile:` in the donor's producer-ownership
sense, and no skill's frontmatter is graded against CF-1..17. Writing a skill here was never on the
hook for any of it — a conformance page that fails your skill for not declaring a dashboard tile you
cannot have is worse than no page, because it teaches you the tool is broken.

⚠ **That is a narrower claim than "none of this infrastructure exists," and it used to be true here —
it no longer is, checked live.** `system/tools/pulse.sh` + `system/pulse-config.md` (a real, git-
shipped job scheduler and its registry) landed in this repo the same day this page did. Several of the
CF rules' underlying mechanisms genuinely exist now; they are just not wired to skill-authoring the
way the donor wired them. The table below was checked against the live tree rather than repeated from
memory — **the one fact that still holds, and is the only one that binds a skill author:** nothing
here declares `shape: cron-producer`, and `system/pulse-config.md` says outright that no registered
job invokes a model yet, so `JUDGMENT_SPEC` has no live case to attach to.

### The frontmatter/schema pieces that did not travel

| Donor field/block | Live in any shipped `SKILL.md` here? | Evidence |
|---|---|---|
| `shape: cron-producer` | No | All 33 skills declare `command`, `interactive-workflow`, or `utility` (the table above) — `grep -rhn '^shape:' .claude/skills/*/SKILL.md` returns no other value |
| `desk:` (producer-ownership sense) | No | `desk:` DOES appear in 2 unrelated files — `.claude/skills/skill-builder/SKILL.md` (`desk: root`) and `.claude/skills/research/SKILL.md`'s output template (`desk: {project slug, or root}`) — but as a *project-or-root scope tag on a generated doc*, a coincidental reuse of the word, not the donor's producer-ownership field. Don't conflate the two if you go grepping. |
| `emit_tile:` | No | Zero hits anywhere in this repo outside this page |
| `JUDGMENT_SPEC` | No live block, but the concept is understood correctly | `.claude/skills/design-lifehack/SKILL.md` states inline: *"No JUDGMENT_SPEC: interactive-workflow, not a thin-AI cron-producer."* A skill author already knew to skip it and said why. |
| `emit_diary` (shared, multi-caller write-helper contract) | No shared helper was extracted | `system/tools/cal-diary-capture.py` implements the identical Human-Delta-preservation behavior (`HUMAN_DELTA_MARKER`, extract-before-rebuild, byte-identical re-attach) directly, inline — because it is still the only caller. The BEHAVIOR ported; the *shared-contract-for-N-callers* framing didn't, because nothing here needs one yet. |

### The CF-1 … CF-17 matrix, checked against the live tree

Not something a skill author has to satisfy. This exists so that if you ever read the donor project's
history and hit a `CF-` number, you have somewhere to look instead of guessing.

| CF | Rule (donor short form) | Dependency exists here? | Disposition |
|---|---|---|---|
| CF-1 | tile writes all go through one shared validator, `emit_status.py` | No — `emit_status.py` doesn't exist anywhere in this repo | Not applicable. Tiles themselves DO exist (`<notes>/state/status/*.json`, written by e.g. `system/tools/system-health.py`); there's just no shared write-time validator guarding them. |
| CF-2 | envelope completeness swept by `verify-connections.py` | No such script anywhere here | Not applicable |
| CF-3 | exactly one "obsidian-brain" call site | No — the term doesn't appear anywhere in this repo, and isn't defined anywhere in the donor beyond this one matrix row either | Meaningless here — there's no component by this name to have one call site or many |
| CF-4 | a canon-routing rule, documented and reviewed via the donor's `archivist-review` skill | Partially — `canon/` is a real, live concept here (resolved under the reader's own gitignored `data/` root, same as `<notes>/state/debt-ledger.md` — legitimately absent from a fresh checkout, not missing), and `.claude/skills/archivist-route/SKILL.md` does exactly this job: *"ranks the right canon home (1–3, with why) — never a silent pick, and catches non-canon misfiling."* | **Enforceable here**, under a different skill name — `archivist-route` ships; the donor's `archivist-review` does not ship here |
| CF-5 | no cron runner mixes a fetch call and a tile-emit without an intervening `claude -p` judgment boundary | No — nothing declares `shape: cron-producer`, and `system/pulse-config.md` states outright that no registered job invokes a model | Not applicable — nothing exists yet for this rule to police |
| CF-6 | every cron-producer emits a tile | No, in the `SKILL.md`-producer sense — nothing declares that shape | Not applicable to skill-authoring. Adjacent but distinct: `system/tools/system-health.py` genuinely does watch every job registered in `system/pulse-config.md` for a live heartbeat/tile — real and live, just not scoped to skills. |
| CF-7 | no cron job runs outside the registry | Yes — `system/pulse-config.md` is a real job registry; `system-health.py` + `health_invariants.py` watch it | **Enforceable here**, at the job-scheduling level (not skill-authoring) |
| CF-8 | a freshness/liveness signal per job | Yes — `system-health.py`'s UP/LATE/DOWN/PAUSED read against the Pulse heartbeat | **Enforceable here** |
| CF-9 | no dual scheduler running at once | Not tracked by any tool found here | This was a one-time decommission checklist tied to a specific past donor migration event, not a standing rule. This repo is single-machine by design (`docs/data-layout.md`: *"there is one machine. The two-machine plane is not part of this system"*), so the scenario mostly doesn't arise — but nothing here specifically detects "you ran `install-schedulers.sh` twice." Marked UNKNOWN rather than guessed enforceable. |
| CF-10 | every hook opens with an LLM-CONTEXT block that educates + redirects, checked against a canonical hook contract | Yes — `system/hook-contract.md` exists and defines this exact mandatory block; checked live: all 44 files in `system/hooks/*.sh` carry it (`grep -l "LLM CONTEXT" system/hooks/*.sh` = 44 of 44) | **Enforceable here** — currently 100% compliant. Enforcement today is convention + human/Archivist review; no automated per-hook checker was found. |
| CF-11 | flip `validate_on_write.sh` from advisory to blocking once its violations clear | The hook exists and runs (`system/hooks/validate_on_write.sh`) | The rule as written doesn't apply: this repo's own copy of the hook documents a deliberate, **permanent** decision to stay advisory-only — *"hard blocking is reserved for guards that stop irreversible acts... frontmatter completeness is hygiene, not safety"* (its own LLM-CONTEXT block). Not an oversight waiting to be flipped; a ruled-out design choice. |
| CF-12 | a display-only dashboard (`app.js`) never computes, only renders | No — no dashboard, no `app.js`, no `helm/` anywhere in this repo | Not applicable — nothing to check |
| CF-13 | one contract serves every caller | Deferred even in the donor system (status: "deferred," recorded there as known debt too) | Not applicable — the underlying serving layer this rule was about doesn't exist here either |
| CF-14 | every `SKILL.md` carries `shape:` | Yes | **Enforceable here** — already this page's own live, first-class requirement (see "The one required field" above), write-time-blocked by `system/hooks/enforce_skill_frontmatter.sh`. The one CF rule that fully survived the port, just not under the `CF-14` name. |
| CF-15 | a DANGER/critical alert is never silently swallowed by quiet hours or dedup | Yes — `shared/notify/notify-governor.py` carries the same critical-bypasses-quiet-hours + short-critical-dedup-floor logic the donor built this rule around, and `system/tools/system-health.py` actually calls it with `--priority critical` (line 418) on a DOWN verdict | **Enforceable here**, for anything a script sends at `--priority critical`. The donor's upstream classifier that DECIDES something is DANGER in the first place (email-content triage) has no equivalent here yet — a separate, larger gap, not this rule's. |
| CF-16 | no MCP tool can write to the vault (deny-listed in `settings.json`) | No MCP surface exists at all — no `.mcp.json`, no MCP entries anywhere in `.claude/settings.json`'s `deny` list (checked: that list is 18 filesystem-path entries only) | Not applicable — there is nothing to protect, because there is no MCP write path in the first place |
| CF-17 | a diary writer preserves a human-authored `## Human Delta` section byte-for-byte, through a shared `emit_diary` helper | Partially — `system/tools/cal-diary-capture.py` implements the exact preservation behavior (`HUMAN_DELTA_MARKER`, extract-before-rebuild, re-attach byte-for-byte) | The BEHAVIOR is real and live; the "shared helper for N callers" framing doesn't apply because there is exactly one caller here, not several desks each needing the same contract. |

⚠ **This is a KNOWN, TRACKED GAP, not a finished decision.** The day a skill in this repo is meant to
run on a schedule AND call a model for judgment, it needs its own `JUDGMENT_SPEC` — a scheduled job
that silently mis-scopes what the model decides is a real, previously-measured failure mode, not a
theoretical one. Logged as `[SKILL-CONFORMANCE-PRODUCER-HALF]` in the reader's own
`<notes>/state/debt-ledger.md` — the same place every other deliberately-deferred item in this repo is
tracked (`docs/data-layout.md`). It won't show up in a fresh checkout of this repo because, like
`canon/`, it lives under the reader's own gitignored `data/` root, not in version control.
