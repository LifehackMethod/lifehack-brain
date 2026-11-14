---
# ── FRONTMATTER — fill for your shape; delete the lines that don't apply ──
skill: {kebab-slug}              # matches the directory name; for a cron-producer, also its jobs.md row name
title: {Human Readable Name}
shape: {interactive-workflow | command | utility | cron-producer}   # or a list of two, e.g. [command, interactive-workflow]; prefer one
version: 0.1.0                   # OPTIONAL — only for a skill with a real changelog (updated_at already marks change)
status: draft                    # draft | active | deprecated
description: {third person, starting "Use when…", leading with the situation}
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

## Musts
- {safety / autonomy invariants — what this skill must not do (each must carries who approved it and when) — ALL SHAPES}

<!-- ═══════════════════════════════════════════════════════════════════════════
     JUDGMENT_SPEC — LLM-BEARING CRON-PRODUCERS ONLY (runner shapes A / C).
     OMIT THIS ENTIRE SECTION for: interactive-workflow · utility ·
     LLM-free shape-B health-emitters (no judgment step → no JUDGMENT_SPEC).
     ═══════════════════════════════════════════════════════════════════════════ -->
## JUDGMENT_SPEC
inputs:
  - name: {binding}
    source: {where it comes from — e.g. the Read-only reader agent (`ingest-reader`, smallest tier) → email_convert.py + scan_for_injection}
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
    call_site: {the `run_model` call (system/tools/model.lib.sh) that hands the judgment to the model}
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
 Use `--priority critical` ONLY for a DANGER / P0 alert (it bypasses quiet-hours + the cap).}

<!-- ═══ DEDUP / IDEMPOTENCY — CRON-PRODUCERS. ═══ -->
## Dedup / idempotency
{the high-water marker / "never re-pull" rule; safe to re-run}

## What this does NOT do
- {scope edges — recommended for cron-producers}

<!-- ═══ AUTHORIZATION — MAIL-INGEST (runner shape A) ONLY. ═══ -->
## Authorization checklist
- {trusted-lane identity; body-read split (orchestrator never reads raw bodies); per-item Sentinel gate}

<!-- ═══ CONFORMANCE — required for cron-producers; optional otherwise. ═══ -->
## Check before use
- {run the check in the skills SOP, Build step 2 (`canon/skill-building-sop.md`): `skill:` matches the folder; `shape:` present; the outcome in the first few lines; everything it writes named with its path; an early-stop path written down.}

<!-- ─────────────────────────────────────────────────────────────────────────────
HOW TO USE THIS TEMPLATE
1. Copy this directory to `~/.claude/skills/{your-skill}/` (canon; skills SOP Build step 2). A desk's skills live there too.
2. Fill the frontmatter for your shape; DELETE the shape lines + body sections that don't apply
   (the `<!-- ... ONLY -->` markers tell you what to drop — a clean interactive skill has NO
   JUDGMENT_SPEC, Storage, Tile, Dedup, or Authorization section).
3. Run the checks in Check before use.
Spec + rationale: `canon/skill-building-sop.md (Build, step 2)`.
(Supersedes the pre-runner-standard `system/templates/ingest-skill-template.md` ⛔ — donor spillover,
parked at system/parked/2026-08-23-donor-spillover/system/templates/ingest-skill-template.md, never
ported here — this template is what actually superseded it.)
───────────────────────────────────────────────────────────────────────────── -->
