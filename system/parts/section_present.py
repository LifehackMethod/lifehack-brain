#!/usr/bin/env python3
"""section_present — a required section (and what it promises to show) must appear.  [Parts · S3.2]

WHEN: a step's output is expected to CONTAIN a specific named section or callout, full
      stop -- not "does A come before B" (that's order_lint's job) and not "does a named
      thing stay absent" (that's forbidden_content's, the mirror image). Just: is the
      thing here at all, and does it actually show what it claims to show.

WHAT: locate a required marker (a heading, a literal term, or a regex) in the artifact.
      If it never appears, MISSING -- the whole promise is absent. If it appears, and the
      rule also declares a list of required sub-elements the section is supposed to
      surface, each of those is checked too -- a section that exists in name only (the
      marker is there, but what it promised to show is not) is INCOMPLETE, a verdict
      distinct from either extreme.

WHY:  the FIRST real routing run (a routing run against a weekly-review skill's phase 2) found
      clause `cw_p2_unit_000246_c01`:
        "1. Rolling scratchpad view (shows Phase 1's additions: the reality-reset,
         confirmed/temporary monthly goal, marked deltas)."
      -- classified enforceable, and NOTHING in the parts library matched it (NO-PART).
      The identical shape recurs, worded almost verbatim, at the top of every such
      phase prompt (`a multi-phase skill's per-phase prompts`): "**Rolling scratchpad
      view first:** show what Phase N wrote (X, Y, Z)." That is a presence obligation on
      a section AND its named contents -- not an ordering claim (order_lint) and not a
      withholding claim (forbidden_content). NO-PART is a build order per this router's
      own law 2; this is that part, sized to the real clause rather than an imagined one.

THE THREE VERDICTS -- collapsing them sends a human to the wrong place (same discipline
as order_lint's BEFORE_MISSING vs OUT_OF_ORDER split):
  PRESENT     the section marker is found, and every declared required sub-element (if
              any) is found too.
  MISSING     the section marker itself never appears anywhere in the checked text.
  INCOMPLETE  the section marker IS present, but at least one declared required
              sub-element is not -- the label is there, the substance isn't.

MATCHING a marker (the section itself, or a required sub-element): exactly one of
  "term":    a LITERAL word or phrase. PREFER THIS. Escaped and word-bounded here, so a
             rule author never hand-rolls the regex -- and a literal is the only form a
             mechanical probe can disguise-and-inject back at the rule (order_lint's same
             reasoning, 2026-07-28).
  "pattern": a regex. Use only when the thing genuinely is a pattern, not a word.

HONEST BOUND -- READ THIS BEFORE TRUSTING IT. `requires` sub-elements are checked
ANYWHERE in the (optionally --section-sliced) text, not in a bounded window right after
the section marker -- the same simplicity order_lint uses for its own before/after
`locate()`. A required element that happens to appear elsewhere in the artifact,
unconnected to the section it was meant to belong to, reads as satisfied. Use `--section`
to slice the artifact to one heading first when that scoping matters; this part does not
attempt paragraph-level proximity on its own.

⚠ SIGNATURE DISCIPLINE (route_to_part.py DISPATCH entry for this part): kept deliberately
narrow, grounded in the recurring "Rolling scratchpad view (shows ... additions: ...)"
language actually found in that skill, plus the "must show/include/contain" family that
names the same obligation without ordering or negation. Generic words like "present" or
"appears" alone are NOT signatures here -- they are common enough in ordinary prose that
a loose match would be wired to the wrong part more often than a miss would show up as
NO-PART. A miss is loud; a loose match is quiet and gets trusted (this file's own header
law, inherited from order_lint and forbidden_content).

⛔ DECLARED UNCHECKABLE -- THE `requires` SUB-ELEMENT CHECK CANNOT PROVE THE CONTENT IS REAL.
      What it DOES prove: the declared term (word-bounded, escaped) or pattern is present as
      text somewhere in the checked slice -- a real, mechanical, non-trivial fact. A section
      that never mentions "reality-reset" at all is caught, every time, with the exact
      missing id named.
      What it CANNOT prove: that the sentence containing the term is the substantive artifact
      the clause meant to require, rather than a bare mention of the same words. Proven live:
      the single line "**Rolling scratchpad view first:** reality-reset, monthly goal, marked
      deltas -- noted." earns PRESENT, exit 0, against this part's own real fixture rule --
      the words are named, the content they name does not exist. The mechanism is
      text-in/text-out: the skill under check authors the artifact, and this same check reads
      that artifact for the words the skill just typed. No trace independent of that artifact
      exists to say the substance is there, only the vocabulary.
      This is a TERMINAL answer, not a TODO. No independent trace exists, and none could
      without redefining what `requires` means -- turning it from a keyword-presence check
      into a content-quality check is a different part, not a fix to this one. Do not burn a
      future session trying to "fix" this.
      ⛔ DO NOT PATCH with a "is the content substantive?" heuristic. That heuristic was
      built, measured, and REVERTED in this project: it scored 10/10 on a fixture its own
      author wrote, then produced 50% false positives on real clauses. It is the exact
      false-positive machine this finding exists to keep out.
      Worth naming plainly, because it is the instructive part: the SIGNATURE DISCIPLINE
      block above shows excellent instincts -- narrow signatures, an explicit refusal to
      match bare words like "present" or "appears," a distinct INCOMPLETE verdict so a hollow
      section cannot read as full. Every one of those instincts is aimed at the ROUTER's
      precision (matching the right clause to the right part). None of them is aimed at the
      ACTOR's incentive (writing text that merely names the required words). Good design
      against the wrong threat model.

USAGE
  section_present.py --rules RULES.json --artifact A.md [--section "Phase 2"] [--json]
  section_present.py --selftest

EXIT CODES (the part contract)
  0  PRESENT        -- every rule's section (and its required contents) is present
  1  REFUSED        -- at least one rule is MISSING or INCOMPLETE
  2  CANNOT EVALUATE -- missing file, bad rules, --section matched nothing. Fail-closed.

RULES FILE — a JSON list:
  [ {"id": "p2-scratchpad-view",
     "section": {"id": "scratchpad-marker", "term": "Rolling scratchpad view"},
     "requires": [ {"id": "reality-reset", "term": "reality-reset"},
                   {"id": "monthly-goal", "term": "monthly goal"},
                   {"id": "marked-deltas", "term": "marked deltas"} ],
     "why": "the donor case, a weekly-review skill's phase-2 prompt: 'Rolling scratchpad view "
            "first: show what Phase 1 wrote (the reality-reset, confirmed/temporary "
            "monthly goal, marked deltas).'"} ]
`requires` is optional -- omit it (or leave it an empty list) for a bare presence check
with no sub-element obligation.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

PRESENT, REFUSED, CANNOT_EVALUATE = 0, 1, 2


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


def slice_section(text, section_rx):
    """Slice to the shallowest heading matching section_rx. Raises LookupError.

    Identical in shape to order_lint's helper of the same name -- duplicated rather than
    imported, per the parts-library rule that a part reaches outside its own file into
    nothing (README §1). Same forty-odd lines, same reasoning.
    """
    lines = text.splitlines()
    rx_head = re.compile(r"^(#{1,6})\s+(.*)$")
    rx = re.compile(section_rx, re.IGNORECASE)
    heads = [(len(m.group(1)), i, m.group(2).strip())
             for i, line in enumerate(lines) if (m := rx_head.match(line))]
    cands = [h for h in heads if rx.search(h[2])]
    if not cands:
        raise LookupError(f"no heading matching /{section_rx}/ found")
    level, start, _ = min(cands, key=lambda h: (h[0], h[1]))
    end = next((i for lv, i, _ in heads if i > start and lv <= level), len(lines))
    return "\n".join(lines[start:end])


def locate(text, spec):
    """Return the character offset of the first match for this marker, or None.

    Only "term" (literal, escaped, word-bounded) or "pattern" (regex) -- unlike
    order_lint's locate(), there is no "sequence" form here: a required section is a
    single marker, not a narrative arc that has to land in order.
    """
    if not isinstance(spec, dict) or not spec.get("id"):
        raise ValueError(f"marker needs an 'id': {spec!r}")
    flags = re.IGNORECASE | re.MULTILINE

    if "term" in spec:
        term = spec["term"]
        if not isinstance(term, str) or not term.strip():
            raise ValueError(f"marker {spec['id']!r} has an empty 'term'")
        m = re.compile(rf"\b{re.escape(term.strip())}\b", flags).search(text)
        return m.start() if m else None

    if "pattern" in spec:
        m = re.search(spec["pattern"], text, flags)
        return m.start() if m else None

    raise ValueError(f"marker {spec['id']!r} needs either 'term' or 'pattern'")


def check(text, rules):
    """Return a list of result dicts. Raises ValueError on a bad rule -> fail closed."""
    results = []
    for rule in rules:
        if not isinstance(rule, dict) or not rule.get("id"):
            raise ValueError(f"rule needs an 'id': {rule!r}")
        if "section" not in rule:
            raise ValueError(f"rule {rule['id']!r} needs a 'section'")
        requires = rule.get("requires") or []
        if not isinstance(requires, list):
            raise ValueError(f"rule {rule['id']!r}: 'requires' must be a list")

        sec_at = locate(text, rule["section"])

        if sec_at is None:
            verdict = "MISSING"
            missing = [r.get("id", r) for r in requires]
        else:
            missing = [r["id"] for r in requires if locate(text, r) is None]
            verdict = "INCOMPLETE" if missing else "PRESENT"

        results.append({
            "id": rule["id"],
            "verdict": verdict,
            "why": rule.get("why", ""),
            "section_id": rule["section"].get("id"),
            "section_at": sec_at,
            "missing": missing,
            "failed": verdict != "PRESENT",
        })
    return results


def render(results):
    out = []
    for r in results:
        out.append(f"  [{r['verdict']}] {r['id']}")
        if r["verdict"] == "MISSING":
            out.append(f"      {r['section_id']!r} never appears -- the section itself "
                       f"is absent, not just incomplete")
        elif r["verdict"] == "INCOMPLETE":
            out.append(f"      {r['section_id']!r} is present, but missing: "
                       f"{', '.join(str(m) for m in r['missing'])}")
        if r["why"] and r["failed"]:
            out.append(f"      why it matters: {r['why']}")
    return "\n".join(out)


# ---------------------------------------------------------------- self-test

# The known-bad/known-good pair mirrors the REAL clause this part was bought to enforce:
# that skill's phase 2 "Rolling scratchpad view (shows Phase 1's additions: the
# reality-reset, confirmed/temporary monthly goal, marked deltas)."
_RULES = [{
    "id": "p2-scratchpad-view",
    "section": {"id": "scratchpad-marker", "term": "Rolling scratchpad view"},
    "requires": [
        {"id": "reality-reset", "term": "reality-reset"},
        {"id": "monthly-goal", "term": "monthly goal"},
        {"id": "marked-deltas", "term": "marked deltas"},
    ],
    "why": "the donor case, a weekly-review skill's phase-2 prompt",
}]

# known-bad #1: the marker itself never shows up at all -- MISSING.
_MISSING = """## Phase 2 - Connect the Dots

Ask the owner about his week and take notes. Move on when done.
"""

# known-bad #2: the marker is there, but the content it promised is not -- INCOMPLETE,
# a DIFFERENT failure than MISSING (the label exists; the substance doesn't).
_INCOMPLETE = """## Phase 2 - Connect the Dots

**Rolling scratchpad view first:** show what Phase 1 wrote. Confirm the pad is live.
"""

# known-good: marker present, all three required sub-elements present.
_GOOD = """## Phase 2 - Connect the Dots

**Rolling scratchpad view first:** show what Phase 1 wrote (the reality-reset ·
confirmed/temporary monthly goal · marked deltas). Confirm the pad is live, then begin.
"""

# benign near-miss: the required WORDS appear, but not the marker itself -- must still be
# MISSING, not PRESENT-by-accident. A required-content check with no marker is not a
# section, it's a coincidence.
_NEAR_MISS_NO_MARKER = """## Phase 2

We covered the reality-reset, the monthly goal, and the marked deltas today, informally.
"""


def selftest():
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("section_present --selftest")

    r = check(_MISSING, _RULES)[0]
    report("catches the known-bad: section marker never appears (MISSING)",
           r["verdict"] == "MISSING" and r["failed"], r["verdict"])

    r = check(_INCOMPLETE, _RULES)[0]
    report("catches the known-bad: marker present but required contents absent "
           "(INCOMPLETE, not MISSING)",
           r["verdict"] == "INCOMPLETE" and r["failed"]
           and set(r["missing"]) == {"reality-reset", "monthly-goal", "marked-deltas"},
           f"{r['verdict']} missing={r['missing']}")

    r = check(_GOOD, _RULES)[0]
    report("passes a hand-built correct artifact (marker + all required contents)",
           r["verdict"] == "PRESENT" and not r["failed"], r["verdict"])

    r = check(_NEAR_MISS_NO_MARKER, _RULES)[0]
    report("benign near-miss: required WORDS present without the marker is still "
           "MISSING, not a pass by accident",
           r["verdict"] == "MISSING", r["verdict"])

    # partial incompleteness: only ONE required element missing must still be flagged,
    # and the others must not be reported as missing.
    partial = ("**Rolling scratchpad view first:** show the reality-reset and the "
               "monthly goal, but nothing about deltas.")
    r = check(partial, _RULES)[0]
    report("INCOMPLETE names exactly the missing sub-element(s), not the whole set",
           r["verdict"] == "INCOMPLETE" and r["missing"] == ["marked-deltas"],
           f"missing={r['missing']}")

    # word-boundary discipline: 'realities' must not satisfy 'reality-reset'
    report("word boundaries hold ('realities' is not 'reality-reset')",
           locate("we discussed several realities today",
                  {"id": "x", "term": "reality-reset"}) is None)

    # a bare presence rule (no 'requires' at all) is satisfied by the marker alone
    bare_rules = [{"id": "bare", "section": {"id": "m", "term": "Rolling scratchpad view"}}]
    r = check(_INCOMPLETE, bare_rules)[0]
    report("a rule with no 'requires' is a bare presence check (marker alone suffices)",
           r["verdict"] == "PRESENT")

    # fail-closed: malformed rules
    try:
        check(_GOOD, [{"id": "x"}])
        report("raises on a rule missing 'section' (fail-closed)", False, "no raise")
    except ValueError:
        report("raises on a rule missing 'section' (fail-closed)", True)
    try:
        locate("x", {"id": "w", "term": "   "})
        report("raises on an empty 'term' (fail-closed)", False, "no raise")
    except ValueError:
        report("raises on an empty 'term' (fail-closed)", True)
    try:
        locate("x", {"id": "w"})
        report("raises on a marker with neither 'term' nor 'pattern' (fail-closed)",
               False, "no raise")
    except ValueError:
        report("raises on a marker with neither 'term' nor 'pattern' (fail-closed)", True)

    # slicing
    two_phase = _GOOD + "\n" + _MISSING.replace("Phase 2", "Phase 5")
    report("--section slices to one phase before checking",
           check(slice_section(two_phase, "Phase 5"), _RULES)[0]["verdict"] == "MISSING")
    try:
        slice_section(_GOOD, "Phase 9")
        report("raises when --section matches nothing (fail-closed)", False, "no raise")
    except LookupError:
        report("raises when --section matches nothing (fail-closed)", True)

    # end-to-end CLI, proving the exit-code contract
    with tempfile.TemporaryDirectory() as td:
        rp = os.path.join(td, "rules.json")
        with open(rp, "w") as fh:
            json.dump(_RULES, fh)
        for label, body, want in (("CLI known-bad (MISSING) -> exit 1", _MISSING, REFUSED),
                                  ("CLI known-bad (INCOMPLETE) -> exit 1", _INCOMPLETE, REFUSED),
                                  ("CLI known-good -> exit 0", _GOOD, PRESENT)):
            ap_ = os.path.join(td, "a.md")
            with open(ap_, "w") as fh:
                fh.write(body)
            rc = subprocess.run([sys.executable, os.path.abspath(__file__),
                                 "--rules", rp, "--artifact", ap_],
                                capture_output=True, text=True).returncode
            report(label, rc == want, f"got exit {rc}")
        rc = subprocess.run([sys.executable, os.path.abspath(__file__), "--rules", rp,
                             "--artifact", os.path.join(td, "nope.md")],
                            capture_output=True, text=True).returncode
        report("CLI missing artifact -> exit 2 (fail-closed)", rc == CANNOT_EVALUATE,
               f"got exit {rc}")

        ap_ = os.path.join(td, "good.md")
        with open(ap_, "w") as fh:
            fh.write(_GOOD)
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "--rules", rp,
                            "--artifact", ap_, "--json"],
                           capture_output=True, text=True)
        try:
            payload = json.loads(p.stdout)
            json_ok = payload.get("verdict") == "PRESENT"
        except json.JSONDecodeError:
            json_ok = False
        report("CLI --json emits a parseable verdict", json_ok, p.stdout[:120])

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description="section_present -- a required section (and its declared contents) must appear")
    ap.add_argument("--rules")
    ap.add_argument("--artifact")
    ap.add_argument("--section", help="regex: check only the section under this heading")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if not args.rules or not args.artifact:
        _die("--rules and --artifact are required")
    for p, what in ((args.rules, "rules file"), (args.artifact, "artifact")):
        if not os.path.isfile(p):
            _die(f"{what} not found: {p!r}")
    try:
        rules = json.loads(open(args.rules, encoding="utf-8").read())
    except json.JSONDecodeError as e:
        _die(f"rules file is not valid JSON: {e}")
    if not isinstance(rules, list):
        _die("rules file must contain a JSON list")

    text = open(args.artifact, encoding="utf-8").read()
    if args.section:
        try:
            text = slice_section(text, args.section)
        except LookupError as e:
            _die(str(e))
    try:
        results = check(text, rules)
    except ValueError as e:
        _die(str(e))

    failed = [r for r in results if r["failed"]]
    if args.json:
        print(json.dumps({"verdict": "REFUSED" if failed else "PRESENT",
                          "results": results}, indent=2))
    else:
        print(f"section_present -- {'REFUSED' if failed else 'PRESENT'} "
              f"({len(failed)} of {len(results)} rule(s) failed)")
        print(render(results))
    sys.exit(REFUSED if failed else PRESENT)


if __name__ == "__main__":
    main()
