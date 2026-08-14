#!/bin/bash
# new-skill.sh — scaffold a CONFORMANT Lifehack skill (enforce-at-birth, Phase 7)
#
# WHY THIS EXISTS: the 46-skill remediation (2026-07) proved skills drift out of conformance one at a
# time — a missing `description:` (the ONLY field the harness reads to trigger), an unquoted colon-space
# that crashes YAML, no `## Intent (§0.5)` block. Rather than re-audit forever, a skill is now BORN
# conformant: this jig stamps the frontmatter + intent block the SOP requires, and the companion hook
# `enforce_skill_frontmatter.sh` blocks any SKILL.md written without them. Solve it once.
#
# RULE / SIGNPOST: the skill shape is codified in system/sops/skill-building-sop.md (§0 six traits, §0.5
# the 3-layer intent model). Change the template there-and-here together.
#
# Usage:  bash system/tools/new-skill.sh <skill-name> --description "<one line>" [--desk <desk>] [--shape <shape>] [--force]
#   <skill-name>   kebab-case, e.g. cal-monthly  (becomes skills/<skill-name>/SKILL.md)
#   --description  REQUIRED — the real one-line description (what it does + when it fires + the literal
#                  trigger words). The ONLY field the harness reads to auto-trigger; no placeholder allowed.
#   --desk         owning desk (default: root)
#   --shape        interactive-workflow | utility | autonomous-cron  (default: interactive-workflow)
#   --force        overwrite an existing SKILL.md (default: refuse)
set -euo pipefail

# Resolve the clone root from THIS script's own location (system/tools/new-skill.sh → root is ../..),
# not a hardcoded absolute path to the repo. This keeps the jig portable — a git worktree's copy writes
# into that worktree, which is what makes the conformance-lab bake-off's isolation actually work.
CODE="$(cd "$(dirname "$0")/../.." && pwd)"
DESK="root"
SHAPE="interactive-workflow"
FORCE=0
NAME=""
DESCRIPTION=""
MULTIPHASE=0   # >0 → also scaffold N per-phase drivers, each BORN with a gradeable contract block

while [ $# -gt 0 ]; do
  case "$1" in
    --desk)  DESK="${2:?--desk needs a value}"; shift 2 ;;
    --shape) SHAPE="${2:?--shape needs a value}"; shift 2 ;;
    --description) DESCRIPTION="${2:?--description needs a value}"; shift 2 ;;
    --multiphase) MULTIPHASE="${2:?--multiphase needs a phase COUNT}"; shift 2 ;;
    --force) FORCE=1; shift ;;
    -h|--help) grep -E '^#( |$)' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "unknown flag: $1" >&2; exit 1 ;;
    *) NAME="$1"; shift ;;
  esac
done

[ -n "$NAME" ] || { echo "ERROR: skill-name required. Usage: new-skill.sh <skill-name> [--desk <desk>] [--shape <shape>]" >&2; exit 1; }
if ! printf '%s' "$NAME" | grep -qE '^[a-z0-9]+(-[a-z0-9]+)*$'; then
  echo "ERROR: skill-name must be kebab-case (a-z, 0-9, hyphens): got '$NAME'" >&2; exit 1
fi

# ── ENFORCE-AT-BIRTH: a real description is REQUIRED (SOP-§0.5-layer1-in-description) ──────────
# The description is the ONLY field the harness reads to auto-trigger, and the ONE rule pushed all
# the way down to tooling is the one that never broke. A skill can no longer be BORN with a
# placeholder description: the jig refuses to scaffold without a real one. (Conformance lab flipped
# this rule dark→fires by adding this gate, 2026-07-23.)
DESCRIPTION="$(printf '%s' "$DESCRIPTION" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
if [ -z "$DESCRIPTION" ]; then
  echo "ERROR: --description is REQUIRED. A skill must be born with a real description — the ONLY" >&2
  echo "       field the harness reads to auto-trigger. Write one line: what it does + when it fires," >&2
  echo "       ending with the literal trigger words, e.g.:" >&2
  echo "       --description 'Cal — weekly review that ranks every lane. Use on \"cal weekly\", \"run my week\".'" >&2
  exit 1
fi
case "$DESCRIPTION" in
  REPLACE*|replace*|Replace*)
    echo "ERROR: --description is still a REPLACE placeholder. Write a real one." >&2; exit 1 ;;
esac
if [ "${#DESCRIPTION}" -lt 20 ]; then
  echo "ERROR: --description too short (${#DESCRIPTION} chars). Write a real one-line description" >&2
  echo "       (what it does + when it fires + the literal 'Use on \"trigger\"' words)." >&2
  exit 1
fi
# YAML-safety: escape backslashes then double-quotes so the stamped value can't break frontmatter.
DESC_ESC="$(printf '%s' "$DESCRIPTION" | sed 's/\\/\\\\/g; s/"/\\"/g')"

DIR="$CODE/skills/$NAME"
FILE="$DIR/SKILL.md"
if [ -e "$FILE" ] && [ "$FORCE" -ne 1 ]; then
  echo "ERROR: $FILE already exists. Use --force to overwrite." >&2; exit 1
fi

TODAY="$(date +%F)"
mkdir -p "$DIR"

# NOTE: description is double-quoted (the YAML colon-space trap: an unquoted value containing ': '
# crashes frontmatter parsing and the harness falls back to the body heading). Keep it quoted.
cat > "$FILE" <<EOF
---
topic: [REPLACE-with-a-slug-from-system/topic-vocab.md]
skill: $NAME
description: "$DESC_ESC"
shape: $SHAPE
desk: $DESK
status: active
version: 0.1
created_at: $TODAY
updated_at: $TODAY
---

## Intent (§0.5)
<!-- The 3-layer intent model (system/sops/skill-building-sop.md §0.5). Write as prose, not a form.
     A skill with no declared user-outcome + role is ambiguous — the session guesses. Fill all layers.
     Layer 3 (per-turn anchor) applies to MULTI-TURN skills only; a one-shot/cron skill omits it. -->
**User outcome:** REPLACE — the human's win in their own terms (what changes for the user, why they asked). End with a **Bar:** in their voice ("it's done when…").
**Role:** REPLACE — what the skill IS and where it sits on the autonomy spectrum (fully-autonomous ↔ human-in-the-loop): what it automates vs. what it reserves for the human, and why that split.
**Per-turn anchor:** REPLACE (multi-turn only) — the one line re-injected every turn so a long/compacted run never loses the thread; e.g. \`Step N/M · {phase} · next → {next}\`. Delete this line for a one-shot or cron skill.

# $NAME

<!-- §0 SIX TRAITS (category-weighted — a lean utility isn't penalized for lacking a persona/anchor):
       1. one-front-door   — a single obvious way in; no guessing which mode/trigger.
       2. leads-not-follows — commits a read and asks to be corrected; never a blank "what do you want?".
       3. trusts-a-file    — durable state in a file (scratchpad/brief), not in fragile chat memory.
       4. proves-work      — Execute → Verify → then claim done; never assert success unverified.
       5. right-sizes      — earn every step/pass; start simplest-that-works, add only on a proven need.
       6. soul+fence       — a clear voice + hard rails (what it will NEVER do).
     Delete these comments as you fill the body. Keep the whole file under 500 lines. -->

## Purpose

REPLACE — one short paragraph: what this skill does, in one pass.

## Steps / Flow

REPLACE — the actual logic. Right-size it; don't over-build.

## Rails (what this skill will NEVER do)

- REPLACE — the hard boundaries (writes it won't make, data it won't touch, instructions it won't obey).
EOF

# ── BORN-WITH-A-GATE (S6.1): assemble from the parts library, not hand-wire later ──────────────
# Every scaffolded skill gets at least one WORKING gate from system/parts/, wired and runnable the
# moment scaffolding finishes -- zero hand-editing required. This is skill-building-sop.md §III.6's
# flywheel taken literally: a mechanical rule the template itself guarantees (Purpose is stamped
# before Rails, always) is enforced by a §II.1 REPLACE-family part, not left as a convention the
# author might silently drop. Parts are DEPLOYED AS COPIES into the skill's own scripts/ folder
# (system/parts/README.md rule 2: "this library is the master copy; skills get copies") so the gate
# travels with the skill and has no dependency on the clone layout surviving.
PARTS_SRC="$CODE/system/parts"

deploy_part() {
  local part="$1"
  local src="$PARTS_SRC/$part.py"
  if [ ! -f "$src" ]; then
    echo "ERROR: parts-library part not found: $src -- system/parts/$part.py is missing or moved." >&2
    exit 1
  fi
  cp "$src" "$DIR/scripts/$part.py"
  chmod +x "$DIR/scripts/$part.py"
}

mkdir -p "$DIR/scripts"
deploy_part order_lint

cat > "$DIR/scripts/order-rules.json" <<'RULES'
[
  {
    "id": "purpose-before-rails",
    "before": {"id": "purpose", "pattern": "^## Purpose\\b"},
    "after": {"id": "rails", "pattern": "^## Rails\\b"},
    "why": "skill-building-sop.md III.5: a skill states what it IS (Purpose) before it states what it will NEVER do (Rails) -- the boundary can't be read before the thing it bounds is named. Stamped by new-skill.sh, checked by order_lint.py from birth (Law 1: ordering has a definite shape). Anchored to the real headings (not a bare word) because the template's own §0-traits comment says '...a clear voice + hard rails...' before the Rails heading ever appears -- a bare 'term' match on 'Rails' false-positives on that mention (caught live scaffolding zz-verify-throwaway, S6.1)."
  }
]
RULES

set +e
GATE_OUT="$(python3 "$DIR/scripts/order_lint.py" --rules "$DIR/scripts/order-rules.json" --artifact "$FILE" 2>&1)"
GATE_RC=$?
set -e
if [ "$GATE_RC" -eq 0 ]; then
  echo "✅ Wired gate: scripts/order_lint.py (purpose-before-rails) -- PASSED at birth (verified against $FILE)"
else
  # A birth-time failure here means the template itself drifted out of the shape the gate
  # expects -- that is a bug in this jig, not in the skill being scaffolded. Report it loudly
  # rather than silently shipping a gate proven to fail on the skill it was just wired into.
  echo "⚠️  scripts/order_lint.py did NOT pass against the freshly-scaffolded SKILL.md (exit $GATE_RC) -- the template drifted out of the shape this gate expects. Fix new-skill.sh's own template." >&2
  echo "$GATE_OUT" >&2
fi

# ── BORN-WITH-CONTRACT (F5.1): scaffold N per-phase drivers, each carrying a GRADEABLE contract ──
# A multi-phase skill is graded by the conformance-lab against its own driver contract: each phase
# driver declares a `## Output contract` + a `## do NOT` block, and stamps a `✅ phase N complete`
# boundary marker the lab slices on. Born this way, conformance.py grades the skill with ZERO new
# code (extract_clauses + slice_phases already read exactly this shape). The birth-guard hook
# (enforce_multiphase_contract.sh) blocks a multi-phase driver written WITHOUT these blocks.
if [ "$MULTIPHASE" -gt 0 ] 2>/dev/null && [ "$MULTIPHASE" -ge 1 ]; then
  PROMPTS="$DIR/prompts"
  mkdir -p "$PROMPTS"
  i=1
  while [ "$i" -le "$MULTIPHASE" ]; do
    nn="$(printf '%02d' "$i")"
    nxt=$((i + 1))
    if [ "$i" -lt "$MULTIPHASE" ]; then
      nextline="**NEXT:** read \`$(printf '%02d' "$nxt")-*.md\`."
    else
      nextline="**NEXT:** final phase — hand off / close per the skill's Rails."
    fi
    cat > "$PROMPTS/${nn}-phase${i}.md" <<DRV
# Phase $i — REPLACE-phase-name  ·  HUD \`[$i/$MULTIPHASE] REPLACE\`

**Desired outcome:** REPLACE — what this phase must leave true by the time it completes.

## Run
REPLACE — the actual logic for this phase (one distinct step; do not prompt the whole arc at once).

## do NOT
- do NOT REPLACE — a hard rail for THIS phase (a thing it must never do / conclude / write).
- do NOT REPLACE — a second rail if the phase has one.

## Output contract
Scratchpad = REPLACE — the concrete artifact/state this phase must have produced (what a grader can
check on disk). Stamp the boundary marker when done: \`✅ phase $i complete\`.

$nextline
DRV
    i=$((i + 1))
  done
  echo "✅ Created $MULTIPHASE phase drivers in $PROMPTS/ (each born with a gradeable ## Output contract + ## do NOT + '✅ phase N complete' marker)"

  # ── BORN-WITH-A-GATE, multiphase half: phase_gate.py IS the checker the contract block
  # above was shaped for -- it slices each driver to its own "Phase N" heading, requires the
  # Desired-outcome + Output-contract shape just stamped, and is the ONLY thing allowed to
  # write the `✅ phase N complete` marker (Law 3: the actor must never grade its own
  # completion). forbidden_content.py is deployed alongside it as the REQUIRED sibling
  # (system/parts/README.md rule 1) so a future `forbids` rule the author adds has somewhere
  # to run without a second deploy step.
  deploy_part phase_gate
  deploy_part forbidden_content

  python3 - "$NAME" "$MULTIPHASE" > "$DIR/scripts/phase-contract.json" <<'PY'
import json, sys
name, n = sys.argv[1], int(sys.argv[2])
phases = {}
for i in range(1, n + 1):
    phases[str(i)] = {
        "name": f"phase {i} (REPLACE when the phase is authored)",
        "requires": [
            {"id": "desired-outcome", "pattern": "Desired outcome",
             "why": "every phase driver must state what it leaves true when done (new-skill.sh --multiphase stamp)"},
            {"id": "output-contract", "pattern": "Output contract",
             "why": "the gradeable artifact contract new-skill.sh stamps at birth"},
        ],
        # "forbids": [] -- add rules here once the phase's real do-NOT content is written;
        # forbidden_content.py is already deployed at scripts/forbidden_content.py to run them.
    }
contract = {
    "_comment": f"generated at birth by new-skill.sh for {name} -- fill in real 'forbids' "
                 "rules per phase as the spec is written; phase_gate.py grades this against "
                 "each prompts/NN-phaseN.md driver.",
    "skill": name,
    "marker": "✅ phase {n} complete",
    "phases": phases,
}
print(json.dumps(contract, indent=2, ensure_ascii=False))
PY

  i=1
  GATE_ALL_OK=1
  while [ "$i" -le "$MULTIPHASE" ]; do
    nn="$(printf '%02d' "$i")"
    set +e
    GATE_OUT="$(python3 "$DIR/scripts/phase_gate.py" --contract "$DIR/scripts/phase-contract.json" --artifact "$PROMPTS/${nn}-phase${i}.md" --phase "$i" 2>&1)"
    GATE_RC=$?
    set -e
    if [ "$GATE_RC" -eq 0 ]; then
      echo "✅ Wired gate: scripts/phase_gate.py --phase $i -- PASSED at birth (verified against prompts/${nn}-phase${i}.md)"
    else
      GATE_ALL_OK=0
      echo "⚠️  scripts/phase_gate.py --phase $i did NOT pass at birth (exit $GATE_RC) -- the multiphase template drifted out of its own contract shape." >&2
      echo "$GATE_OUT" >&2
    fi
    i=$((i + 1))
  done
  [ "$GATE_ALL_OK" -eq 1 ] && echo "   scripts/phase-contract.json wired for all $MULTIPHASE phase(s); re-run any single phase with: python3 scripts/phase_gate.py --contract scripts/phase-contract.json --artifact prompts/NN-phaseN.md --phase N"
fi

echo "✅ Created $FILE"
echo "   Next:"
echo "   1. Fill every REPLACE in the body (description is already stamped) + delete the guide comments."
if [ "$MULTIPHASE" -gt 0 ] 2>/dev/null; then
  echo "   1b. Fill each prompts/NN-phaseN.md driver's contract (keep the '✅ phase N complete' marker) — it's how the conformance-lab grades this skill."
  echo "   1c. Add real 'forbids' rules to scripts/phase-contract.json as the spec is written — scripts/phase_gate.py + scripts/forbidden_content.py are already wired and passing."
fi
echo "   2. Register it on the menu:  bash system/tools/bootstrap-machine.sh"
echo "   3. Read the doctrine as you build:  system/sops/skill-building-sop.md"
echo "   Gates already wired from the parts library (system/parts/):"
echo "     - scripts/order_lint.py    -- Purpose precedes Rails. Re-check: python3 scripts/order_lint.py --rules scripts/order-rules.json --artifact SKILL.md"
if [ "$MULTIPHASE" -gt 0 ] 2>/dev/null; then
  echo "     - scripts/phase_gate.py    -- each phase's Output contract. Re-check: python3 scripts/phase_gate.py --contract scripts/phase-contract.json --artifact prompts/NN-phaseN.md --phase N"
fi
