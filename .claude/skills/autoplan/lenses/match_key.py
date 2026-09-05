#!/usr/bin/env python3
"""
WHY: a lens that stopped firing looks identical to a plan with nothing
wrong — both report zero findings. Planting known defects and checking
whether the owning lens catches them is the only thing that proves it.
WHAT: reads an answer key of planted defects (task_id, defect, owning
lens) and a lens run (JSON); checks whether each row's owning lens
reported a finding on that task_id; optionally checks a control run
(clean plan) for the owning lens re-flagging the same task_id.

CONTROL ARM, HONEST vs DISHONEST (card 6.14): a control hit on task_id N
can mean two opposite things — DISHONEST (the lens re-flagged the SAME
now-repaired defect: it is pattern-matching the task_id, not reading the
plan) or HONEST (the lens found a DIFFERENT, still-real defect that
happens to share a task_id: it is doing its job). Both used to score as
one undifferentiated "false positive," which cannot tell an honest
thorough lens from a dishonest one — the only thing the control exists
to detect. The lens JSON (per lenses/_contract.md) carries a free-text
`claim` per finding; there is no field naming "which specific defect"
a finding addresses, so match_key cannot invent a semantic same/different
verdict from prose it did not write. What it CAN do mechanically: compare
the owning lens's RUN-arm claim(s) for task_id N against its CONTROL-arm
claim(s) for the same task_id, byte-for-byte after whitespace
normalization. A CONTROL claim that exactly repeats a RUN claim is
mechanically provable pattern-matching — the plan changed under the lens
and its stated reason for flagging did not change at all. A CONTROL claim
that differs is NOT thereby proven honest (paraphrase of the same defect
would also differ) — match_key does not claim that inference. It reports
such rows as CONTROL-HIT(unresolved) and does not fold them into the
exit code, rather than printing a "false positives" number that reads as
a verdict on data that cannot support one. Verified against the real
2026-09-05 fixtures: all 9 previously-counted "false positives" are
CONTROL-HIT(unresolved) under this scheme (zero byte-identical RUN vs
CONTROL claims) — matching the hand-check in lens-rerun-2026-09-05.md
that every one is a different, still-present defect, not a survivor.

VERDICTS: HIT (owner found it) · MISS (owner missed it) · HIT-BY-OTHER
<lens> (a different lens found it — still a MISS for the owner; reported
so the operator sees the roster may need reassigning, not that the lens
is broken).
CONTROL, per row (only with --control): none (owner raised nothing on
this task_id in the control run) · CONTROL-DISHONEST (owner repeated a
byte-identical claim from the run arm — mechanically proven
pattern-match) · CONTROL-HIT(unresolved) (owner raised a finding on this
task_id in the control run with a claim that differs from every run-arm
claim — may be a genuinely different live defect, may be a paraphrase of
the same one; match_key cannot tell and does not guess).
EXIT CODES: 0 = every row HIT by its owner, zero CONTROL-DISHONEST rows
(CONTROL-HIT(unresolved) rows do NOT affect exit code — they are not a
verdict) · 2 = one or more MISS and/or CONTROL-DISHONEST rows · 4 =
CANNOT-READ (missing or unparseable file, malformed key row, unknown
owning lens) — never 0 on unreadable input.
"""
import sys, os, json, argparse

def fail(msg):
    print(f"CANNOT-READ {msg}")
    sys.exit(4)

def load_owners():
    # WHY: a hardcoded owner list drifts silently the moment a card adds a
    # lens file or a key row names one that was never real — the OWNERS set
    # must always equal what actually exists on disk in this directory.
    lens_dir = os.path.dirname(os.path.abspath(__file__))
    names = {os.path.splitext(f)[0] for f in os.listdir(lens_dir)
              if f.endswith(".md") and not f.startswith("_")}
    if not names:
        fail(f"no lens files found in {lens_dir}")
    return names

OWNERS = load_owners()

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

def norm_claim(c):
    return " ".join(str(c).split()) if c is not None else None

def findings_by_lens(run):
    """Returns {lens_name: {task_id: [normalized claim, ...]}} — every
    finding is kept (not just its task_id) so the CONTROL arm can compare
    what a lens actually SAID, not just which task_id it touched."""
    if isinstance(run, dict):
        items = run.items()
    elif isinstance(run, list):
        for o in run:
            if not isinstance(o, dict) or "lens" not in o:
                fail("run list item missing 'lens' key")
        items = [(o["lens"], o) for o in run]
    else:
        fail("run JSON must be a dict or a list")
    out = {}
    for name, ret in items:
        by_task = {}
        for f in (ret or {}).get("findings") or []:
            if not isinstance(f, dict) or f.get("task_id") is None:
                continue
            tid = str(f.get("task_id")).strip()
            by_task.setdefault(tid, []).append(norm_claim(f.get("claim")))
        out[name] = by_task
    return out

ap = argparse.ArgumentParser()
ap.add_argument("--key", required=True)
ap.add_argument("--run", required=True)
ap.add_argument("--control")
args = ap.parse_args()

key_rows = load_key(args.key)
by_lens = findings_by_lens(load_json(args.run))
control = findings_by_lens(load_json(args.control)) if args.control else {}

hits = misses = dishonest = unresolved = 0
for row in key_rows:
    tid, owner = row["task_id"], row["owner"]
    if tid in by_lens.get(owner, {}):
        verdict, hits = "HIT", hits + 1
    else:
        misses += 1
        other = next((ln for ln, ids in by_lens.items() if ln != owner and tid in ids), None)
        verdict = f"HIT-BY-OTHER {other}" if other else "MISS"

    control_note = ""
    if args.control:
        control_claims = control.get(owner, {}).get(tid)
        if control_claims is not None:
            run_claims = set(by_lens.get(owner, {}).get(tid, []))
            if run_claims & set(control_claims):
                dishonest += 1
                control_note = " · CONTROL-DISHONEST (byte-identical claim repeated from run arm)"
            else:
                unresolved += 1
                control_note = " · CONTROL-HIT(unresolved) (different claim — not scored, needs a human read)"

    print(f"{row['n']} · {tid} · {owner} · {verdict}{control_note}")

summary = f"{hits}/{len(key_rows)} hit · {misses} missed"
if args.control:
    summary += f" · {dishonest} control-dishonest · {unresolved} control-hit(unresolved, unscored)"
print(summary)
sys.exit(2 if (misses or dishonest) else 0)
