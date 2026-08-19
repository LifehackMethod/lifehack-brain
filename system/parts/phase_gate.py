#!/usr/bin/env python3
"""phase_gate — the completion stamp only code can write.  [Parts Library · Tier A · A1]

WHEN: any skill with ordered phases -- always.
WHAT: the `✅ phase N complete` marker is written ONLY by this checker, after it verifies
      the phase's required artifacts exist and its forbidden content is absent.
WHY:  Law 3 -- the thing that did the work must never be the thing that declares the work
      done.  "Hallucinated success" / checkbox theater is the most-regretted failure in
      production LLM systems [C]; >14% of measured multi-agent failures are premature
      termination plus skipped verification [R].  a weekly-review skill stamped `✅ phase 2 complete`
      on a phase that had violated its own spec [M] -- the model grading its own homework.

WHAT IT DOES
  1. Slices the artifact down to phase N's own section (never grades the cumulative pad).
  2. REQUIRES  -- every declared required pattern must be present in that slice.
  3. FORBIDS   -- delegates to the sibling part `forbidden_content.py` (A2), which draws
                  the declaration-vs-mention distinction.  Required, not optional: if a
                  phase declares `forbids` and the sibling is missing, this exits 2.
                  One code path, no inline fallback -- a fallback is a second thing to
                  test and the place a gate quietly starts failing open.
  4. UNEARNED STAMP -- if the marker is ALREADY in the slice while the check refuses,
                  that is a model-written completion claim on unfinished work.  Reported
                  loudly and by name, because it is the exact failure Law 3 describes.
  5. --stamp   -- on PASS only, appends the marker with a receipt.  Never on a refusal.

⛔ DECLARED UNCHECKABLE -- THE `requires` CHECK CANNOT PROVE THE MATCHED TEXT IS REAL WORK.
      What it DOES prove: the declared regex pattern is present as text somewhere in the
      phase's own slice (never the cumulative pad, thanks to `slice_phase`) -- a real,
      non-trivial fact. A phase that never mentions its required pattern anywhere in its own
      section is refused, every time, with the pattern named.
      What it CANNOT prove: that the matched text is the phase's actual deliverable, rather
      than prose typed into the phase output for the purpose of satisfying the pattern. The
      mechanism is text-in/text-out: the skill being graded writes the phase's artifact, and
      this same check reads that artifact for the pattern the skill just wrote. No trace
      independent of the artifact exists to distinguish "did the work" from "wrote words that
      match."
      THE BOUND IS ON `requires` ONLY. `forbids` (delegated whole to the sibling part
      `forbidden_content.py`, which draws a genuine declaration-vs-mention distinction) is not
      covered by this finding and stays sound as built.
      This is a TERMINAL answer, not a TODO. No independent trace exists, and none could
      without redefining what `requires` means -- turning it from a pattern-presence check
      into a content-quality check is a different part, not a fix to this one. Do not burn a
      future session trying to "fix" this.
      ⛔ DO NOT PATCH with a "is the content substantive?" heuristic. That heuristic was
      built, measured, and REVERTED in this project: it scored 10/10 on a fixture its own
      author wrote, then produced 50% false positives on real clauses. It is the exact
      false-positive machine this finding exists to keep out.

USAGE
  phase_gate.py --contract C.json --artifact A.md --phase 2            # check
  phase_gate.py --contract C.json --artifact A.md --phase 2 --stamp    # check, then stamp
  phase_gate.py --contract C.json --artifact A.md --phase 2 --json
  phase_gate.py --selftest

EXIT CODES (the part contract)
  0  PASSED    -- phase verified (and stamped if --stamp was given)
  1  REFUSED   -- a requirement is missing and/or forbidden content is present
  2  CANNOT EVALUATE -- missing file, bad contract, phase section not found, sibling part
                        absent.  Fail-closed: an un-evaluable phase is NEVER a pass.

CONTRACT FILE
  {
    "skill": "weekly-review",
    "marker": "✅ phase {n} complete",
    "phases": {
      "2": {
        "name": "Connect the Dots",
        "requires": [{"id": "human-delta", "pattern": "Human Delta",
                      "why": "the phase's own deliverable"}],
        "forbids":  [{"id": "win-named-early", "term": "Win", "mode": "declaration",
                      "why": "spec: the Win is named in Phase 3, never before"}]
      }
    }
  }
  `requires` patterns are regexes, searched case-insensitively over the slice.
  `forbids` entries are passed through verbatim to forbidden_content.py.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime

PASSED, REFUSED, CANNOT_EVALUATE = 0, 1, 2
SIBLING = "forbidden_content.py"


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


# ---------------------------------------------------------------- slicing

def slice_phase(text, phase):
    """Return (slice_text, start_line, heading) for phase N, or raise LookupError.

    Picks the SHALLOWEST heading that names the phase -- a scratchpad often carries a
    deeper '### ✅ Phase 2 complete' summary inside the '## Phase 2' section, and slicing
    on the deeper one would grade a fragment and miss the violation above it.
    """
    lines = text.splitlines()
    rx_head = re.compile(r"^(#{1,6})\s+(.*)$")
    rx_phase = re.compile(rf"\bphase\s*0*{int(phase)}\b", re.IGNORECASE)

    heads = []  # (level, idx, title)
    for i, line in enumerate(lines):
        m = rx_head.match(line)
        if m:
            heads.append((len(m.group(1)), i, m.group(2).strip()))

    cands = [h for h in heads if rx_phase.search(h[2])]
    if not cands:
        raise LookupError(f"no heading naming phase {phase} found in the artifact")

    level, start, title = min(cands, key=lambda h: (h[0], h[1]))

    end = len(lines)
    for lv, idx, _ in heads:
        if idx > start and lv <= level:
            end = idx
            break
    return "\n".join(lines[start:end]), start + 1, title


# ---------------------------------------------------------------- checks

def check_requires(slice_text, requires):
    missing = []
    for req in requires:
        if not isinstance(req, dict) or not req.get("pattern") or not req.get("id"):
            raise ValueError(f"bad 'requires' entry (needs id + pattern): {req!r}")
        if not re.search(req["pattern"], slice_text, re.IGNORECASE | re.MULTILINE):
            missing.append(req)
    return missing


def check_forbids(slice_text, forbids, here):
    """Delegate to the sibling part. Raises RuntimeError if it is missing or misbehaves."""
    sib = os.path.join(here, SIBLING)
    if not os.path.isfile(sib):
        raise RuntimeError(
            f"this phase declares 'forbids' but the required sibling part {SIBLING} is not "
            f"beside phase_gate.py ({here}). Deploy A1 and A2 together.")
    with tempfile.TemporaryDirectory() as td:
        rp = os.path.join(td, "rules.json")
        with open(rp, "w", encoding="utf-8") as fh:
            json.dump(forbids, fh)
        proc = subprocess.run(
            [sys.executable, sib, "--rules", rp, "--stdin", "--json"],
            input=slice_text, capture_output=True, text=True)
    if proc.returncode == CANNOT_EVALUATE:
        raise RuntimeError(f"{SIBLING} could not evaluate: {proc.stderr.strip()}")
    try:
        return json.loads(proc.stdout)["hits"]
    except (json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"{SIBLING} returned unparseable output ({e}): {proc.stdout[:200]!r}")


def marker_for(contract, phase):
    return contract.get("marker", "✅ phase {n} complete").replace("{n}", str(phase))


def evaluate(text, contract, phase, here):
    """Return a verdict dict. Raises LookupError/ValueError/RuntimeError -> fail closed."""
    phases = contract.get("phases")
    if not isinstance(phases, dict):
        raise ValueError("contract has no 'phases' object")
    spec = phases.get(str(phase))
    if spec is None:
        raise ValueError(f"contract declares no phase {phase} "
                         f"(has: {', '.join(sorted(phases)) or 'none'})")

    slice_text, start_line, title = slice_phase(text, phase)
    missing = check_requires(slice_text, spec.get("requires", []))
    forbids = spec.get("forbids", [])
    hits = check_forbids(slice_text, forbids, here) if forbids else []

    marker = marker_for(contract, phase)
    stamped = marker.lower() in slice_text.lower()
    passed = not missing and not hits

    return {
        "phase": phase,
        "name": spec.get("name", ""),
        "heading": title,
        "heading_line": start_line,
        "slice_lines": len(slice_text.splitlines()),
        "verdict": "PASSED" if passed else "REFUSED",
        "missing_requirements": missing,
        "forbidden_present": hits,
        "marker": marker,
        "marker_already_present": stamped,
        "unearned_stamp": bool(stamped and not passed),
    }


def stamp(path, text, contract, phase, verdict):
    """Append the marker at the end of the phase's section. PASS only."""
    marker = verdict["marker"]
    if verdict["marker_already_present"]:
        return False, "marker already present -- not double-stamping"
    _, start_line, _ = slice_phase(text, phase)
    lines = text.splitlines()
    end = start_line - 1 + verdict["slice_lines"]
    receipt = (f"\n{marker}  <!-- written by phase_gate.py at "
               f"{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}; requirements verified, "
               f"forbidden content absent. The model does not write this line. -->")
    lines.insert(end, receipt)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return True, f"stamped {marker!r} after line {end}"


def render(v):
    out = [f"phase {v['phase']}"
           + (f" ({v['name']})" if v["name"] else "")
           + f" -- {v['verdict']}",
           f"  section: {v['heading']!r} @ line {v['heading_line']} ({v['slice_lines']} lines)"]
    for m in v["missing_requirements"]:
        out.append(f"  MISSING REQUIREMENT [{m['id']}]: /{m['pattern']}/ not found in the slice")
        if m.get("why"):
            out.append(f"      why it matters: {m['why']}")
    for h in v["forbidden_present"]:
        out.append(f"  FORBIDDEN CONTENT [{h['id']}] at slice line {h['line']}: {h['evidence']}")
        if h.get("why"):
            out.append(f"      why it matters: {h['why']}")
    if v["unearned_stamp"]:
        out.append(f"  *** UNEARNED STAMP: {v['marker']!r} is ALREADY in this section while the")
        out.append("      phase does not pass its own contract. A completion marker was written")
        out.append("      by something that did not verify it -- the Law 3 failure, on real data.")
    return "\n".join(out)


# ---------------------------------------------------------------- self-test

_ARTIFACT = """# Session Scratchpad -- selftest fixture

## Phase 2 -- Connect the Dots ✅ phase 2 complete

### Human Delta -- confirmed this turn
- some real delta content here

### Connected picture
- Win (the owner-authored): Fully Day-1 ready - paperwork confirmed
- Bonus aim: heat-pump fix

## Phase 1 -- Orientation ✅ phase 1 complete

**Monthly goal: CONFIRMED AS-IS** -- the film is the plan.
- carried forward: two operational deltas, which land inside the Win as actions later
"""

_CONTRACT = {
    "skill": "selftest",
    "marker": "✅ phase {n} complete",
    "phases": {
        "1": {"name": "Orientation",
              "requires": [{"id": "monthly-goal", "pattern": "Monthly goal",
                            "why": "the phase's own deliverable"}],
              "forbids": [{"id": "win-named-early", "term": "Win", "mode": "declaration",
                           "why": "spec: the Win is named in Phase 3"}]},
        "2": {"name": "Connect the Dots",
              "requires": [{"id": "human-delta", "pattern": "Human Delta",
                            "why": "the phase's own deliverable"}],
              "forbids": [{"id": "win-named-early", "term": "Win", "mode": "declaration",
                           "why": "spec: the Win is named in Phase 3"}]},
        "3": {"name": "Missing-from-artifact",
              "requires": [{"id": "x", "pattern": "x", "why": "n/a"}]},
    },
}


def selftest():
    here = os.path.dirname(os.path.abspath(__file__))
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("phase_gate --selftest")

    # --- the two sides, on the same artifact -------------------------------
    v2 = evaluate(_ARTIFACT, _CONTRACT, 2, here)
    report("BLOCKS a phase that declares the forbidden thing (known-bad)",
           v2["verdict"] == "REFUSED" and len(v2["forbidden_present"]) == 1,
           f"{v2['verdict']}, {len(v2['forbidden_present'])} forbidden hit(s)")
    report("names the UNEARNED STAMP on that same phase",
           v2["unearned_stamp"] is True)

    v1 = evaluate(_ARTIFACT, _CONTRACT, 1, here)
    report("PASSES a phase that only mentions it (known-good)",
           v1["verdict"] == "PASSED", f"{v1['verdict']} {v1['forbidden_present']}")

    # --- slicing --------------------------------------------------------
    report("slices to the phase's OWN section, not the whole pad",
           v1["slice_lines"] < len(_ARTIFACT.splitlines()) and "Phase 2" not in
           slice_phase(_ARTIFACT, 1)[0])
    deep = _ARTIFACT.replace("### Connected picture", "### ✅ Phase 2 complete -- summary")
    report("prefers the SHALLOWEST heading when a deeper one names the same phase",
           slice_phase(deep, 2)[1] == 3, f"heading line {slice_phase(deep, 2)[1]}")

    # --- fail-closed paths ------------------------------------------------
    try:
        evaluate(_ARTIFACT, _CONTRACT, 3, here)
        report("raises when the phase section is absent (fail-closed)", False, "no raise")
    except LookupError:
        report("raises when the phase section is absent (fail-closed)", True)
    try:
        evaluate(_ARTIFACT, {"phases": {}}, 2, here)
        report("raises when the contract lacks the phase (fail-closed)", False, "no raise")
    except ValueError:
        report("raises when the contract lacks the phase (fail-closed)", True)
    try:
        check_forbids("text", [{"id": "x", "term": "y"}], tempfile.gettempdir())
        report("raises when the sibling part is missing (fail-closed)", False, "no raise")
    except RuntimeError:
        report("raises when the sibling part is missing (fail-closed)", True)

    # --- stamping ---------------------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        # a passing phase with no marker yet -> gets stamped, and only once
        body = "## Phase 1 -- Orientation\n\n**Monthly goal: CONFIRMED AS-IS**\n"
        p = os.path.join(td, "a.md")
        with open(p, "w") as fh:
            fh.write(body)
        v = evaluate(body, _CONTRACT, 1, here)
        did, _ = stamp(p, body, _CONTRACT, 1, v)
        after = open(p).read()
        report("stamps a PASSING phase that had no marker", did and "✅ phase 1 complete" in after)
        v = evaluate(after, _CONTRACT, 1, here)
        did2, _ = stamp(p, after, _CONTRACT, 1, v)
        report("refuses to double-stamp", did2 is False)

        # CLI: refusal must NOT stamp
        cp = os.path.join(td, "c.json")
        with open(cp, "w") as fh:
            json.dump(_CONTRACT, fh)
        ap_ = os.path.join(td, "b.md")
        bad = _ARTIFACT.replace("## Phase 2 -- Connect the Dots ✅ phase 2 complete",
                                "## Phase 2 -- Connect the Dots")
        with open(ap_, "w") as fh:
            fh.write(bad)
        rc = subprocess.run([sys.executable, os.path.abspath(__file__), "--contract", cp,
                             "--artifact", ap_, "--phase", "2", "--stamp"],
                            capture_output=True, text=True).returncode
        report("CLI known-bad -> exit 1", rc == REFUSED, f"got exit {rc}")
        report("a REFUSED phase is never stamped",
               "✅ phase 2 complete" not in open(ap_).read())

        rc = subprocess.run([sys.executable, os.path.abspath(__file__), "--contract", cp,
                             "--artifact", ap_, "--phase", "1"],
                            capture_output=True, text=True).returncode
        report("CLI known-good -> exit 0", rc == PASSED, f"got exit {rc}")
        rc = subprocess.run([sys.executable, os.path.abspath(__file__), "--contract", cp,
                             "--artifact", os.path.join(td, "nope.md"), "--phase", "1"],
                            capture_output=True, text=True).returncode
        report("CLI missing artifact -> exit 2 (fail-closed)", rc == CANNOT_EVALUATE,
               f"got exit {rc}")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="phase_gate -- the completion stamp only code can write")
    ap.add_argument("--contract")
    ap.add_argument("--artifact")
    ap.add_argument("--phase")
    ap.add_argument("--stamp", action="store_true", help="on PASS only, write the marker")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    for name, val in (("--contract", args.contract), ("--artifact", args.artifact),
                      ("--phase", args.phase)):
        if not val:
            _die(f"{name} is required")

    here = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isfile(args.contract):
        _die(f"contract not found: {args.contract!r}")
    if not os.path.isfile(args.artifact):
        _die(f"artifact not found: {args.artifact!r}")
    try:
        contract = json.loads(open(args.contract, encoding="utf-8").read())
    except json.JSONDecodeError as e:
        _die(f"contract is not valid JSON: {e}")
    text = open(args.artifact, encoding="utf-8").read()

    try:
        verdict = evaluate(text, contract, args.phase, here)
    except (LookupError, ValueError, RuntimeError) as e:
        _die(str(e))

    stamped = None
    if args.stamp and verdict["verdict"] == "PASSED":
        did, note = stamp(args.artifact, text, contract, args.phase, verdict)
        stamped = note
    elif args.stamp:
        stamped = "NOT stamped -- the phase did not pass its contract"

    if args.json:
        verdict["stamp_action"] = stamped
        print(json.dumps(verdict, indent=2, ensure_ascii=False))
    else:
        print(render(verdict))
        if stamped:
            print(f"  stamp: {stamped}")

    sys.exit(PASSED if verdict["verdict"] == "PASSED" else REFUSED)


if __name__ == "__main__":
    main()
