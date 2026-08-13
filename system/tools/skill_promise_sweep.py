#!/usr/bin/env python3
"""skill_promise_sweep.py — the CALLER for skill_promise_check.py's per-file verdict.

WHY THIS FILE EXISTS: skill_promise_check.py (built 2026-07-31) checks exactly ONE
      SKILL.md per invocation and was verified by hand against the corpus — but nothing
      called it on a schedule. Per skill-building-sop.md: "a writer with no reader passes
      every check it has, because it has none" and "COMMITTED != ENFORCED — a helper
      nothing calls is not enforcement." This script is that reader: it walks every real
      skill in the repo, calls the checker's own `check_file()` (never reimplements its
      logic), and renders one table + a summary a human or archivist-audit can act on.

WHAT IT DOES NOT DO: it does not change skill_promise_check.py's vocabulary, matching, or
      verdicts in any way — it only iterates and reports. If you need a new promise
      recognized, edit CLAIM_TABLE in skill_promise_check.py, not this file.

THE CANNOT_EVALUATE HONESTY RULE (read before wiring this into anything else): a skill
      returning CANNOT_EVALUATE made none of the promises this tool's curated vocabulary
      recognizes. That is an honest "no signal," not a pass and not a problem — most
      skills in this repo are not read-only/propose-only/no-Sheet/no-delete skills, so
      most legitimately have nothing to check. This sweep reports CANNOT_EVALUATE as its
      OWN column, separate from PASS, and the summary line never folds it into either
      "clean" or "failing." Only REFUSED (a real, quoted contradiction) is a finding.

USAGE
  skill_promise_sweep.py [--root <clone>] [--json]

EXIT CODES
  0  no REFUSED verdicts found (CANNOT_EVALUATE skills may still be present — that's fine)
  1  at least one skill REFUSED — a real self-contradiction exists; see the printed quotes
"""
import argparse
import glob
import importlib.util
import json
import os
import sys

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
CHECK_MODULE_PATH = os.path.join(TOOLS_DIR, "skill_promise_check.py")

# system/tools/ -> repo root, the same relative-to-this-file convention shared/paths.py
# and every other ported tool uses (never a hardcoded install path). Overridable via
# --root / $CLAUDEOPS_ROOT for a session working against a different checkout.
REPO_ROOT = os.path.normpath(os.path.join(TOOLS_DIR, "..", ".."))

# This repo's skills live under .claude/skills/ (a real dir of per-item symlinks into the
# clone), not a top-level skills/ — see shared/paths.py's own note on the same layout.
SKILLS_GLOB = os.path.join(".claude", "skills", "*", "SKILL.md")


def _load_checker():
    spec = importlib.util.spec_from_file_location("skill_promise_check", CHECK_MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sweep(root):
    checker = _load_checker()
    skill_files = sorted(glob.glob(os.path.join(root, SKILLS_GLOB)))
    reports = []
    for path in skill_files:
        rel = os.path.relpath(path, root)
        report = checker.check_file(path)
        report["skill"] = os.path.basename(os.path.dirname(path))
        report["rel_path"] = rel
        reports.append(report)
    return reports


def render_table(reports):
    lines = []
    lines.append("skill_promise_check sweep (system/tools/skill_promise_check.py, called per-skill)\n")
    lines.append(f"{'skill':32} {'verdict':16} {'claims':7} {'contradictions'}")
    lines.append("-" * 78)
    for r in reports:
        n_claims = len(r.get("checked_claims", []))
        n_contra = len(r.get("contradictions", []))
        lines.append(f"{r['skill']:32} {r['verdict']:16} {n_claims:7} {n_contra}")
    lines.append("-" * 78)

    passed = sum(1 for r in reports if r["verdict"] == "PASS")
    refused = sum(1 for r in reports if r["verdict"] == "REFUSED")
    cannot = sum(1 for r in reports if r["verdict"] == "CANNOT_EVALUATE")
    lines.append(
        f"{len(reports)} skills scanned · {passed} PASS (promise upheld) · "
        f"{refused} REFUSED (self-contradiction found) · "
        f"{cannot} CANNOT_EVALUATE (no recognized promise in this file — not a pass, not a problem)"
    )

    if refused:
        lines.append("\nREFUSED — real, quoted contradictions (fix the skill, not this sweep):")
        for r in reports:
            if r["verdict"] != "REFUSED":
                continue
            lines.append(f"\n  {r['rel_path']}:")
            for x in r["contradictions"]:
                lines.append(
                    f"    [{x['id']}] promise at line {x['claim_line']} (\"{x['claim_quote']}\") "
                    f"contradicted by instructed command at line {x['command_line']} "
                    f"(\"{x['command_quote']}\")"
                )

    lines.append(
        "\nCANNOT_EVALUATE is expected for most skills — it means this file makes none of "
        "the read-only/propose-only/no-Sheet/no-delete promises this tool's curated "
        "vocabulary recognizes (see skill_promise_check.py KNOWN BOUNDS). It carries no "
        "verdict about skill quality."
    )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=os.environ.get("CLAUDEOPS_ROOT", REPO_ROOT))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    reports = sweep(args.root)
    refused = sum(1 for r in reports if r["verdict"] == "REFUSED")

    if args.json:
        print(json.dumps(reports, indent=2))
    else:
        print(render_table(reports))

    sys.exit(1 if refused else 0)


if __name__ == "__main__":
    main()
