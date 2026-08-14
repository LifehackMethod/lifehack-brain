#!/usr/bin/env python3
"""fanout_gate — captured == {count, type}, else INCONCLUSIVE.  [Parts · Tier B · B3]

WHEN: acting on what a set of sub-agents returned.
WHAT: compares what was CAPTURED at a fan-out boundary against what the spec EXPECTS --
      how many, of what type -- and refuses to let "we saw nothing" mean "nothing ran."
WHY:  measured [M].  A grader held 19 captured sub-agent transcripts (4 map + 9 leverage
      + 6 council, hashed to provenance) while its reasoning layer, reading only the
      scratchpad, reported "no evidence of nine leverage agents."  Both tiers passed
      their own checks; the WIRING between them was dead.  SOP §V.5: test the seam as a
      thing, not just the floors either side of it.

THE ONE RULE THAT MATTERS -- ABSENCE OF EVIDENCE IS NOT EVIDENCE OF ABSENCE.
      Zero captured records is INCONCLUSIVE, never "no agents ran," because those two
      states are indistinguishable from inside and only one of them is a skill defect.
      Calling it a clean "none" turns a broken capture pipeline into a silent pass --
      the exact false-green this part exists to prevent.  A verdict of MISMATCH (a real
      count/type disagreement) IS a finding; INCONCLUSIVE is a instruction to go fix
      the instrument before grading anything.

WHAT IT CHECKS
  count      captured n vs expected n
  type       every captured agentType is in the expected set (contagion check: a
             fan-out that quietly used the wrong agent type is a real defect)
  integrity  a captured record with no returned text is TORN, not a valid empty result
  quiescence the caller must confirm capture had actually settled; an un-quiesced
             snapshot can only ever be INCONCLUSIVE, since a low count may just mean
             "still running"

USAGE
  fanout_gate.py --captured C.json --expect-count 9 [--expect-types Task,Agent] \\
                 [--quiesced] [--json]
  fanout_gate.py --selftest

EXIT CODES (the part contract)
  0  MATCH        -- captured agrees with expectation
  1  MISMATCH     -- a real disagreement: a genuine finding
  2  INCONCLUSIVE -- nothing captured, or capture not quiesced. Fail-closed: fix the
                    instrument before you grade the skill.

CAPTURED FILE: [{"agent_id": "...", "agentType": "...", "description": "...",
                 "final_text": "..."}, ...]   (or {"records": [...]})

PROVENANCE: extracted from the frozen lab's fan-out seam handling. Extraction, not
reinvention -- self-contained so it travels with a skill.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

MATCH, MISMATCH, INCONCLUSIVE = 0, 1, 2


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(INCONCLUSIVE)


def check(records, expect_count=None, expect_types=None, quiesced=True):
    """Grade a fan-out capture. Returns a verdict dict; never raises for bad data.

    ⛔ THE HOLE THIS CLOSES (found 2026-07-28 by `system/factory/defeater.py`, first
    hostile sweep of the parts library). This gate was defeated by:

        [{"final_text":"x"},{"final_text":"x"},{"final_text":"x"}]

    Three records with NO `agent_id` and NO `agentType` — nothing identifying an agent at
    all — satisfied a gate whose entire contract is "captured == {count, type}". It
    counted `len(records)`. **A fan-out that never happened could be fabricated**, which
    is the precise failure this part exists to make impossible.

    The governing rail (plan, 2026-07-28): A GATE MUST VERIFY EVIDENCE OF WORK, NEVER THE
    FORM OF A CLAIM. An array of the right LENGTH is the form; an identified agent that
    returned text is the evidence. So:
      · a record with no `agent_id` or no `agentType` is UNIDENTIFIED — it is not a
        record OF an agent, and its presence means the CAPTURE is broken, which is
        INCONCLUSIVE (fix the instrument) and never a finding about the skill;
      · the count is DISTINCT `agent_id`s, so duplicates cannot inflate it.
    """
    unidentified = [f"#{i}" for i, r in enumerate(records, 1)
                    if not str(r.get("agent_id") or "").strip()
                    or not str(r.get("agentType") or "").strip()]
    ids = [str(r.get("agent_id")).strip() for r in records
           if str(r.get("agent_id") or "").strip()]
    dupe_ids = sorted({i for i in ids if ids.count(i) > 1})
    # DISTINCT identified agents -- never the array length
    n = len(set(ids))
    torn = [r.get("agent_id", f"#{i}") for i, r in enumerate(records, 1)
            if not (r.get("final_text") or "").strip()]
    types = sorted({(r.get("agentType") or "?") for r in records})
    alien_types = (sorted(set(types) - set(expect_types)) if expect_types else [])

    reasons = []
    if not quiesced:
        verdict = "INCONCLUSIVE"
        reasons.append("capture was not confirmed quiesced -- a low count here may only "
                       "mean 'still running', which is not a finding")
    elif unidentified:
        verdict = "INCONCLUSIVE"
        reasons.append(f"{len(unidentified)} captured record(s) carry no agent_id and/or "
                       f"no agentType: {unidentified[:5]} -- an unidentified record is not "
                       f"evidence that an agent ran, so this capture cannot support ANY "
                       f"verdict about the skill. FIX THE INSTRUMENT first.")
    elif len(records) > 1 and len({(r.get("final_text") or "").strip()
                                   for r in records}) == 1:
        # ⭐ IDENTICAL RETURNS ARE AN INSTRUMENT FAILURE, NOT A RESULT (2026-07-28,
        # third sweep). The cheat that got here was three properly-identified agents of
        # the right type all returning "x". Judging whether returned text is GOOD is
        # judgment and must never be hard-gated (§V.7) -- but "every agent returned the
        # BYTE-IDENTICAL string" is mechanical, threshold-free, and cannot happen when a
        # real fan-out ran distinct angles. This is P1.6's shrug-detector, one phase
        # early: a shrug is detectable even though a judgment is not.
        verdict = "INCONCLUSIVE"
        reasons.append(f"all {len(records)} captured records returned BYTE-IDENTICAL text "
                       f"-- a real fan-out runs distinct angles, so this is a broken or "
                       f"stubbed capture, not {len(records)} agents' work. FIX THE "
                       f"INSTRUMENT before grading the skill.")
    elif dupe_ids:
        verdict = "INCONCLUSIVE"
        reasons.append(f"duplicate agent_id(s) {dupe_ids} -- the same agent counted twice "
                       f"inflates the capture; accounting must be per distinct agent")
    elif n == 0:
        verdict = "INCONCLUSIVE"
        reasons.append("ZERO records captured -- this cannot distinguish 'no sub-agents "
                       "ran' from 'capture is broken', and only one of those is a skill "
                       "defect. Absence of evidence is not evidence of absence.")
    else:
        problems = []
        if expect_count is not None and n != expect_count:
            problems.append(f"expected {expect_count} sub-agents, captured {n}")
        if alien_types:
            problems.append(f"unexpected agentType(s): {alien_types} "
                            f"(expected only {sorted(expect_types)})")
        if torn:
            problems.append(f"{len(torn)} captured record(s) returned no text -- TORN, "
                            f"not a valid empty result: {torn[:5]}")
        verdict = "MISMATCH" if problems else "MATCH"
        reasons = problems or ["captured count and types agree with the expectation"]

    return {"verdict": verdict,
            "captured": n,
            "records_seen": len(records),
            "unidentified": unidentified,
            "duplicate_ids": dupe_ids,
            "expected": expect_count,
            "types": types,
            "alien_types": alien_types,
            "torn": torn,
            "quiesced": quiesced,
            "reasons": reasons,
            "exit": {"MATCH": MATCH, "MISMATCH": MISMATCH,
                     "INCONCLUSIVE": INCONCLUSIVE}[verdict]}


def load_records(path):
    raw = json.loads(open(path, encoding="utf-8").read())
    return raw.get("records", []) if isinstance(raw, dict) else list(raw)


def render(v):
    out = [f"fanout_gate -- {v['verdict']} "
           f"(captured {v['captured']}"
           + (f" of {v['expected']} expected" if v["expected"] is not None else "")
           + f"; types {v['types'] or '—'})"]
    for r in v["reasons"]:
        out.append(f"  - {r}")
    if v["verdict"] == "INCONCLUSIVE":
        out.append("  FIX THE INSTRUMENT before grading the skill — an inconclusive seam "
                   "cannot support any verdict about what the skill did.")
    return "\n".join(out)


# ---------------------------------------------------------------- self-test

def _rec(i, atype="Task", text=None):
    # per-agent text by default: a real fan-out runs DISTINCT angles, and a fixture whose
    # agents all return the same string models a stubbed capture, not a healthy one
    return {"agent_id": f"agent-{i}", "agentType": atype,
            "description": f"Leverage angle {i}",
            "final_text": text if text is not None else f"returned something real about angle {i}"}


def selftest():
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("fanout_gate --selftest")

    nine = [_rec(i) for i in range(1, 10)]

    # ⭐ THE EXACT ARTIFACT THAT DEFEATED THIS PART (2026-07-28) ----------------
    cheat = [{"final_text": "x"}, {"final_text": "x"}, {"final_text": "x"}]
    v0 = check(cheat, expect_count=3, expect_types=["Task"])
    report("the defeater's cheat (3 stubs, no agent_id/agentType) is INCONCLUSIVE, not MATCH",
           v0["verdict"] == "INCONCLUSIVE", f"got {v0['verdict']}")
    report("the count is DISTINCT identified agents, never array length",
           v0["captured"] == 0 and v0["records_seen"] == 3)
    report("every unidentified record is named, not just counted",
           len(v0["unidentified"]) == 3)
    # duplicates cannot inflate a real capture either
    dupes = [_rec(1), _rec(1), _rec(2)]
    v1 = check(dupes, expect_count=3, expect_types=["Task"])
    report("a duplicated agent_id cannot inflate the capture",
           v1["verdict"] == "INCONCLUSIVE" and v1["duplicate_ids"] == ["agent-1"])
    # ...and an honest capture is untouched by any of it
    v2 = check(nine, expect_count=9, expect_types=["Task"])
    report("an honest 9-agent capture still MATCHes (no false positive)",
           v2["verdict"] == "MATCH" and v2["captured"] == 9 and not v2["unidentified"])

    v = check(nine, expect_count=9, expect_types=["Task"])
    report("known-good: 9 of 9 captured, right type -> MATCH",
           v["verdict"] == "MATCH" and v["exit"] == MATCH)

    v = check(nine[:5], expect_count=9, expect_types=["Task"])
    report("known-bad: 5 captured where 9 expected -> MISMATCH",
           v["verdict"] == "MISMATCH" and v["exit"] == MISMATCH, v["reasons"][0])

    # THE measured failure: zero captured must never read as a clean 'none'
    v = check([], expect_count=9, expect_types=["Task"])
    report("ZERO captured -> INCONCLUSIVE, never 'no agents ran'",
           v["verdict"] == "INCONCLUSIVE" and v["exit"] == INCONCLUSIVE)
    report("and it says so in words a human can act on",
           "not evidence of absence" in " ".join(v["reasons"]))

    # zero expected AND zero captured is still inconclusive, not a pass
    v = check([], expect_count=0)
    report("zero captured is inconclusive even when zero was expected",
           v["verdict"] == "INCONCLUSIVE")

    # contagion
    v = check(nine[:8] + [_rec(9, atype="WrongType")], expect_count=9,
              expect_types=["Task"])
    report("catches an unexpected agentType (contagion)",
           v["verdict"] == "MISMATCH" and v["alien_types"] == ["WrongType"])

    # torn record
    v = check(nine[:8] + [_rec(9, text="   ")], expect_count=9, expect_types=["Task"])
    report("a captured record with no text is TORN, not a valid empty result",
           v["verdict"] == "MISMATCH" and len(v["torn"]) == 1)

    # quiescence
    v = check(nine[:3], expect_count=9, expect_types=["Task"], quiesced=False)
    report("an un-quiesced capture can only be INCONCLUSIVE, never a finding",
           v["verdict"] == "INCONCLUSIVE")
    report("a full capture that is not quiesced is ALSO inconclusive (no lucky pass)",
           check(nine, expect_count=9, quiesced=False)["verdict"] == "INCONCLUSIVE")

    # no expectation supplied -> count cannot be judged, but types/torn still can
    v = check(nine)
    report("with no expected count, a healthy capture still MATCHes",
           v["verdict"] == "MATCH")

    # CLI exit-code contract
    me = os.path.abspath(__file__)
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "cap.json")
        with open(p, "w") as fh:
            json.dump(nine, fh)
        rc = subprocess.run([sys.executable, me, "--captured", p, "--expect-count", "9",
                             "--expect-types", "Task", "--quiesced"],
                            capture_output=True, text=True).returncode
        report("CLI known-good -> exit 0", rc == MATCH, f"got exit {rc}")
        rc = subprocess.run([sys.executable, me, "--captured", p, "--expect-count", "4",
                             "--quiesced"], capture_output=True, text=True).returncode
        report("CLI mismatch -> exit 1", rc == MISMATCH, f"got exit {rc}")
        with open(p, "w") as fh:
            json.dump([], fh)
        rc = subprocess.run([sys.executable, me, "--captured", p, "--expect-count", "9",
                             "--quiesced"], capture_output=True, text=True).returncode
        report("CLI zero captured -> exit 2 (inconclusive)", rc == INCONCLUSIVE,
               f"got exit {rc}")
        rc = subprocess.run([sys.executable, me, "--captured", os.path.join(td, "nope.json")],
                            capture_output=True, text=True).returncode
        report("CLI missing file -> exit 2 (fail-closed)", rc == INCONCLUSIVE, f"got exit {rc}")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="fanout_gate -- captured == {count, type} else INCONCLUSIVE")
    ap.add_argument("--captured")
    ap.add_argument("--expect-count", type=int, default=None)
    ap.add_argument("--expect-types", default=None, help="comma-separated allowed agentTypes")
    ap.add_argument("--quiesced", action="store_true",
                    help="assert capture had settled; without this the verdict is INCONCLUSIVE")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if not args.captured:
        _die("--captured is required")
    if not os.path.isfile(args.captured):
        _die(f"captured file not found: {args.captured!r}")
    try:
        records = load_records(args.captured)
    except (json.JSONDecodeError, TypeError) as e:
        _die(f"captured file is not valid JSON: {e}")

    types = [t.strip() for t in args.expect_types.split(",")] if args.expect_types else None
    v = check(records, expect_count=args.expect_count, expect_types=types,
              quiesced=args.quiesced)
    print(json.dumps(v, indent=2) if args.json else render(v))
    sys.exit(v["exit"])


if __name__ == "__main__":
    main()
