#!/usr/bin/env bash
# test_no_hardcoded_model_ids.sh -- static rule: no literal model id outside the ONE table (self-monitoring 5.4).
# Scans shared/ and system/tools/ for (1) claude-(haiku|sonnet|opus|fable)-<n> and (2) any literal passed as a model
# flag/assignment (--model X, "--model","X", model="X", MODEL=X; a $variable / model_id(tier) / run_model tier is fine).
# Allowed anywhere: model.lib.sh, model_ids.py (and tests/, which quote ids as fixtures).
# KNOWN = files that still hold one because their job is not migrated yet. Printed, NOT failed. Each entry is
# REMOVED from this list the day its job migrates to a tier; a file not on the list that holds one FAILS the suite.
cd "$(dirname "${BASH_SOURCE[0]}")/../../.." || exit 2
python3 - <<'PY'
import os, re, sys
KNOWN = {
    "shared/tools/email_service_contract.py",
    "system/tools/archivist-run.lib.sh",
    "system/tools/planning-analyze-run.sh",
    "system/tools/planning-weekly-analyze-run.sh",
    "system/tools/planning-weekly-prime-run.sh",
}
ID = re.compile(r"claude-(?:haiku|sonnet|opus|fable)-[0-9]")
LIT = [re.compile(p) for p in (
    r"""--model(?:=|[ \t]+)["']?([A-Za-z0-9][\w.\-]*)""",
    r"""["']--model["']\s*,\s*["']([\w.\-]+)["']""",
    r"""\b[Mm][Oo][Dd][Ee][Ll]\s*=\s*["']([\w.\-]+)["']""",
    r"""^\s*(?:export\s+)?MODEL\s*=\s*([A-Za-z0-9][\w.\-]*)\s*(?:#.*)?$""")]
EXEMPT = {"system/tools/model.lib.sh", "shared/tools/model_ids.py"}
hits = []
for top in ("shared", "system/tools"):
    for dp, dn, fn in os.walk(top):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".git", "tests", "fixtures")]
        for f in fn:
            p = os.path.join(dp, f)
            if p in EXEMPT: continue
            try: lines = open(p, encoding="utf-8").read().splitlines()
            except (UnicodeDecodeError, OSError): continue
            for i, ln in enumerate(lines, 1):
                code = not ln.lstrip().startswith("#")
                if ID.search(ln) or (code and any(r.search(ln) for r in LIT)):
                    hits.append((p, i, ln.strip()[:100]))
known = [h for h in hits if h[0] in KNOWN]; new = [h for h in hits if h[0] not in KNOWN]
print("KNOWN hard-coded ids (job not migrated yet; remove each entry as its job migrates):")
for p, i, l in known: print(f"  KNOWN {p}:{i}: {l}")
for p, i, l in new: print(f"  NEW   {p}:{i}: {l}")
if new:
    print(f"FAIL: {len(new)} NEW hard-coded model id(s) -- name a tier; ids live only in system/tools/model.lib.sh"); sys.exit(1)
print(f"PASS: no new hard-coded model ids ({len(known)} known lines, unmigrated)")
PY
