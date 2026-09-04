#!/usr/bin/env python3
"""
WHY: a lens that stopped firing looks identical to a plan with nothing
wrong — both report zero findings. Planting known defects and checking
whether the owning lens catches them is the only thing that proves it.
WHAT: reads an answer key of planted defects (task_id, defect, owning
lens) and a lens run (JSON); checks whether each row's owning lens
reported a finding on that task_id; optionally checks a control run
(clean plan) for false positives.
VERDICTS: HIT (owner found it) · MISS (owner missed it) · HIT-BY-OTHER
<lens> (a different lens found it — still a MISS for the owner; reported
so the operator sees the roster may need reassigning, not that the lens
is broken).
EXIT CODES: 0 = every row HIT by its owner, zero false positives ·
2 = one or more MISS and/or false positives · 4 = CANNOT-READ (missing or
unparseable file, malformed key row, unknown owning lens) — never 0 on
unreadable input.
"""
import sys, json, argparse

OWNERS = {"github", "tokens", "gating", "value", "postmortem", "steps"}

def fail(msg):
    print(f"CANNOT-READ {msg}")
    sys.exit(4)

def load_json(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except FileNotFoundError:
        fail(f"missing file {path}")
    except json.JSONDecodeError as e:
        fail(f"unparseable JSON in {path}: {e}")

def load_key(path):
    try:
        lines = open(path, encoding="utf-8").readlines()
    except FileNotFoundError:
        fail(f"missing file {path}")
    rows = []
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        f = [p.strip() for p in line.split(" · ")]
        if len(f) != 5:
            fail(f"key row {i} has {len(f)} fields, expected 5: {line!r}")
        if f[3] not in OWNERS:
            fail(f"key row {i} has unknown owning lens {f[3]!r}")
        rows.append({"n": f[0], "task_id": f[1], "owner": f[3]})
    return rows

def findings_by_lens(run):
    if isinstance(run, dict):
        items = run.items()
    elif isinstance(run, list):
        for o in run:
            if not isinstance(o, dict) or "lens" not in o:
                fail("run list item missing 'lens' key")
        items = [(o["lens"], o) for o in run]
    else:
        fail("run JSON must be a dict or a list")
    return {name: {str(f.get("task_id")).strip() for f in (ret or {}).get("findings") or []
                   if isinstance(f, dict) and f.get("task_id") is not None}
            for name, ret in items}

ap = argparse.ArgumentParser()
ap.add_argument("--key", required=True)
ap.add_argument("--run", required=True)
ap.add_argument("--control")
args = ap.parse_args()

key_rows = load_key(args.key)
by_lens = findings_by_lens(load_json(args.run))
control = findings_by_lens(load_json(args.control)) if args.control else {}

hits = misses = fp = 0
for row in key_rows:
    tid, owner = row["task_id"], row["owner"]
    if tid in by_lens.get(owner, set()):
        verdict, hits = "HIT", hits + 1
    else:
        misses += 1
        other = next((ln for ln, ids in by_lens.items() if ln != owner and tid in ids), None)
        verdict = f"HIT-BY-OTHER {other}" if other else "MISS"
    print(f"{row['n']} · {tid} · {owner} · {verdict}")
    if args.control and tid in control.get(owner, set()):
        fp += 1

print(f"{hits}/{len(key_rows)} hit · {misses} missed · {fp} false positives")
sys.exit(2 if (misses or fp) else 0)
