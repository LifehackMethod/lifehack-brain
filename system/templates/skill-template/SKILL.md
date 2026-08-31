---
# ── FRONTMATTER (CF-14) — fill for your shape; delete the lines that don't apply ──
skill: {kebab-slug}              # matches the directory name; for a producer, also the pulse_job
title: {Human Readable Name}
shape: {cron-producer | interactive-workflow | utility}   # or a LIST [cron-producer, interactive-workflow] for a genuinely multi-mode skill
version: 0.1.0                   # OPTIONAL — only for a skill with a real changelog (updated_at already marks change)
status: draft                    # draft | active | deprecated
summary: {one paragraph — the JOB this skill does, caller-visible}
# ── cron-producer ONLY ──
desk: {desk-slug}                # owning desk
# (a cron-producer emits a tile by definition — no `emit_tile` flag needed)
emit_diary: true                 # ONLY if it ALSO writes a dated diary entry (omit otherwise)
# ── interactive-workflow / utility ONLY ──
triggers: [{phrase one}, {phrase two}]      # how the user invokes it (producers have none)
# allowed-tools: [Read, Glob, Grep, Bash]   # optional tool allowlist (utility)
created_at: {YYYY-MM-DD}
updated_at: {YYYY-MM-DD}
---

# {Title}
### {one line — what this skill does}

## Desired outcome
{The JOB in one paragraph. What "done" looks like. — ALL SHAPES}

## Hard rules
- {safety / autonomy invariants — what this skill must NEVER do — ALL SHAPES}

<!-- ═══════════════════════════════════════════════════════════════════════════
     JUDGMENT_SPEC — LLM-BEARING CRON-PRODUCERS ONLY (runner shapes A / C).
     OMIT THIS ENTIRE SECTION for: interactive-workflow · utility ·
     LLM-free shape-B health-emitters (no judgment step → no JUDGMENT_SPEC).
     ═══════════════════════════════════════════════════════════════════════════ -->
## JUDGMENT_SPEC
inputs:
  - name: {binding}
    source: {where it comes from — e.g. a tool-less reader subagent → email_convert.py + scan_for_injection}
    format: {shape}
outputs:
  - name: {field}
    schema: {type / enum / prose}
    example: {one real value}
thin_ai_boundary:
  code_does: |
    {auth · fetch · sanitize · dedup · label-moves · atomic write · buzz · emit_status.py — the plumbing}
  llm_does: |
    {the ONE judgment — classify / score / grade / rank / synthesize}
  swap_seam:
    call_site: {the claude -p {SKILL.md} call, e.g. in ingest_run_claude()}
    input_contract: {exact schema a replacement agent must ACCEPT — mirrors `inputs`}
    output_contract: {exact schema it must EMIT — mirrors `outputs`}

## Procedure
{The numbered steps. — ALL SHAPES
  · cron-producer: ingest (deterministic code) → process (the LLM judgment, per JUDGMENT_SPEC) → emit (validated tile)
  · interactive-workflow: the human-gated steps (every write waits for explicit user confirmation)
  · utility: the helper / routing logic}

<!-- ═══ STORAGE + TILE — CRON-PRODUCERS ONLY. Omit for interactive-workflow / utility. ═══ -->
## Storage
{where durable output lands — file paths, the per-run record dir}

## Tile
{Emit the desk tile via `emit_status.py` (P1) — NEVER hand-roll `json.dump`.
 `system/schemas/desk-status-contract.md` ⛔ never landed (donor spillover, parked at
 system/parked/2026-08-23-donor-spillover/system/schemas/desk-status-contract.md) — the envelope
 (schema_version 2) is defined instead by `emit_status.py` itself, the only thing that writes a tile.
 Set: stale_after_s · work_count · work_noun · items[] · link. The desk-specific payload rides alongside.}

<!-- ═══ NOTIFICATION — only if this skill buzzes the user. ═══ -->
## Notification
{Route through `notify-send.sh` (P10) — never curl ntfy directly.
 Use `--priority critical` ONLY for a DANGER / P0 alert (it bypasses quiet-hours + the cap, CF-15).}

<!-- ═══ DEDUP / IDEMPOTENCY — CRON-PRODUCERS. ═══ -->
## Dedup / idempotency
{the high-water marker / "never re-pull" rule; safe to re-run}

## What this does NOT do
- {scope edges — recommended for cron-producers}

<!-- ═══ AUTHORIZATION — MAIL-INGEST (runner shape A) ONLY. ═══ -->
## Authorization checklist
- {trusted-lane identity; body-read split (orchestrator never reads raw bodies); per-item Sentinel gate}

<!-- ═══ CONFORMANCE — required for cron-producers; optional otherwise. ═══ -->
## Conformance checklist
- [ ] CF-14  `shape:` present (+ matches the runner shape A/B/C)
- [ ] CF-5   LLM-bearing → JUDGMENT_SPEC present; fetch + emit separated by the `claude -p` boundary
- [ ] CF-1/6 tile written via `emit_status.py` (atomic; never hand-rolled); `verify-connections.py` GREEN
- [ ] CF-8   registered in `pulse-config.md`, DISABLED until the supervised test passes

<!-- ─────────────────────────────────────────────────────────────────────────────
HOW TO USE THIS TEMPLATE
1. Copy this directory to `skills/{your-skill}/` (or `desks/{desk}/skills/{your-skill}/`).
2. Fill the frontmatter for your shape; DELETE the shape lines + body sections that don't apply
   (the `<!-- ... ONLY -->` markers tell you what to drop — a clean interactive skill has NO
   JUDGMENT_SPEC, Storage, Tile, Dedup, or Authorization section).
3. Run the Conformance checklist.
See filled exemplars: `SKILL.example-producer.md` (LLM-bearing cron-producer) ·
`SKILL.example-interactive.md` (interactive-workflow). Spec + rationale: `docs/skill-conformance.md`.
(Supersedes the pre-runner-standard `system/templates/ingest-skill-template.md` ⛔ — donor spillover,
parked at system/parked/2026-08-23-donor-spillover/system/templates/ingest-skill-template.md, never
ported here — this template is what actually superseded it.)
───────────────────────────────────────────────────────────────────────────── -->
