#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: Enver's standing rule — every plan must be hierarchical (Phase → Feature →
#      Task) with each task gated Execute → Verify & test → mark ✅ (not "done" until
#      its verify passes). It lived only as prose in a SOP, so it kept getting missed;
#      nothing enforced it. There is NO EnterPlanMode hook (verified vs Claude Code
#      docs 2026-06-19), so ExitPlanMode is the only enforcement point.
# GUARDS: an ExitPlanMode submission whose plan text lacks the required structure
#      (Phase + Task + Verify markers) — blocks it so the plan is rewritten in shape
#      BEFORE the user sees the approval dialog. Features optional for small plans;
#      Phase + Task + Verify are the non-negotiables.
# REDIRECT: rewrite the plan as Phase → Feature → Task, each task Execute → Verify &
#      test → mark ✅. Spec: system/sops/architecture-planning-sop.md (★★ ALWAYS)
#      + the "Planning Output" rule in CLAUDE.md.
# UPDATED: 2026-06-19 (ported 2026-08-13 from claudeops-config — verbatim; no hardcoded paths
#      or identifiers, no machine-gate)
# ─────────────────────────────────────────────────────────────────────────────
# guard_plan_structure.sh — PreToolUse hook (matcher: ExitPlanMode)
# NOTE: deliberately fails OPEN (allow) on empty/unparseable plan text. This is a
# QUALITY gate, not a security control — a parse miss must never brick plan mode.
# Worst case of fail-open = one unchecked plan slips (CLAUDE.md rule still nudges).

INPUT=$(cat)
PLAN=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('tool_input', {}).get('plan', ''))
except:
    print('')
")

# Fail-OPEN: no plan text -> do not block (see NOTE above).
if [ -z "$PLAN" ]; then
  exit 0
fi

# Structural check — case-insensitive presence of the three non-negotiable markers.
miss=""
echo "$PLAN" | grep -qi 'phase'  || miss="${miss}Phase "
echo "$PLAN" | grep -qi 'task'   || miss="${miss}Task "
echo "$PLAN" | grep -qi 'verif'  || miss="${miss}Verify "

if [ -n "$miss" ]; then
  printf '%s\n' '{"decision":"block","reason":"BLOCKED: plan is missing required structure ('"$miss"'). WHY: ClaudeOps plans must be Phase -> Feature -> Task, each task Execute -> Verify & test -> mark done (a task is NOT done until its verify passes), per the Planning Output rule in CLAUDE.md. REDIRECT: rewrite the plan in that hierarchy (Features optional for small plans; Phase + Task + Verify are required) before calling ExitPlanMode. Spec: system/sops/architecture-planning-sop.md (star-star ALWAYS)."}' >&2
  exit 2
fi
exit 0
