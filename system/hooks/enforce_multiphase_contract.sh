#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: A multi-phase skill is only gradeable by the conformance-lab if each phase DRIVER declares its
#      own contract — a `## Output contract` block (what the phase must produce) — so the lab can
#      extract the phase's clauses and grade what a run actually wrote vs. them. A phase driver written
#      WITHOUT that block is invisible to the door-tester: the skill silently drifts, and the "solve it
#      once, born knowing it" loop breaks. This guard makes a contract-less phase driver un-writable.
# GUARDS: a Write of any skills/<skill>/prompts/NN-*.md that LOOKS like a phase driver (a `# Phase N`
#      heading or a `[N/M]` HUD marker) but carries NO `## Output contract` section. Blocks the write so
#      the driver is BORN gradeable. (Edits pass — only a full-content Write is adjudicated.)
# REDIRECT: scaffold it right — `bash <repo>/system/tools/new-skill.sh <name> --multiphase N`
#      stamps each driver with a `## Output contract` + `## do NOT` block + a `✅ phase N complete` marker.
#      Or add a `## Output contract` section (ending with the `✅ phase N complete` boundary marker) by hand.
# SIGNPOST: system/sops/skill-building-sop.md (the enforceability partition + 3-failure-type frame) +
#      system/tools/new-skill.sh (the `--multiphase` scaffold, whose own comments name this guard by
#      name as the enforcement it assumes exists — each scaffolded skill gets its own
#      `scripts/phase_gate.py` that checks a run's artifact against this exact `## Output contract`
#      shape). This repo does not have the donor's shared `conformance-lab/`; per-skill
#      `phase_gate.py` is the equivalent here. To change the rule, edit the SOP + get sign-off, then
#      update this guard.
# UPDATED: 2026-07-24
# ─────────────────────────────────────────────────────────────────────────────
# enforce_multiphase_contract.sh — PreToolUse hook (matcher: Write)
# Born-with-contract: a multi-phase skill's phase driver must carry a `## Output contract` block.

INPUT=$(cat)
export INPUT
python3 <<'PY'
import os, json, sys, re

raw = os.environ.get("INPUT", "")
try:
    data = json.loads(raw)
    ti = data.get("tool_input", {}) or {}
    path = ti.get("file_path", "") or ti.get("path", "")
    content = ti.get("content", None)
except Exception:
    sys.exit(0)

if "/skills/" not in path or "/prompts/" not in path or not path.endswith(".md"):
    sys.exit(0)
if "/skills/_" in path or "/templates/" in path or "/_archive" in path or os.path.basename(path).startswith("_"):
    sys.exit(0)

if content is None:
    sys.exit(0)

is_driver = bool(re.search(r"^#\s+Phase\s+\d", content, re.M | re.I) or
                 re.search(r"\[\s*\d+\s*/\s*\d+\s*\]", content))
if not is_driver:
    sys.exit(0)

if not re.search(r"^##\s+Output\s+contract\b", content, re.M | re.I):
    msg = ("BLOCKED: this phase driver (%s) declares a phase but has no `## Output contract` section."
           " WHY: a multi-phase skill's own per-skill `scripts/phase_gate.py` (scaffolded by"
           " new-skill.sh --multiphase) grades a run by extracting each phase driver's"
           " `## Output contract` clauses and checking what the run actually wrote against them — a driver"
           " without one is invisible to that check and the skill silently drifts."
           " REDIRECT: scaffold with `bash <repo>/system/tools/new-skill.sh <name> --multiphase N`"
           " (stamps a `## Output contract` + `## do NOT` block + a `phase N complete` marker per driver),"
           " or add a `## Output contract` section ending with the boundary marker."
           " RULE: system/sops/skill-building-sop.md — edit there + get sign-off to change, then update this guard."
           % os.path.basename(path))
    sys.stderr.write(msg + "\n")
    sys.exit(2)

sys.exit(0)
PY
exit $?
