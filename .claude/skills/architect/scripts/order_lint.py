#!/usr/bin/env python3
"""order_lint — required section A must physically precede section B.  [Parts · Tier A · A3]

WHEN: output sequence carries meaning.
WHAT: a positional check on required content -- A must appear, and appear BEFORE B.
WHY:  Law 1 -- ordering has a definite shape, so it is code's job, not a request.
      cal-weekly's Report 1 presented the Win with no year->quarter->month->week arc
      before it -- confirmed by three unanimous judges on real data [M].  The spec is
      explicit: "The arc first ... Then the Win."  Order is exactly the demand-class
      prose does not hold (SOP §II.7).

THE FOUR VERDICTS -- an ordering rule fails in two genuinely different ways, and
collapsing them hides which one you have:
  ORDERED         A appears before B.  Fine.
  OUT_OF_ORDER    both appear, but B comes first.  A sequencing bug.
  BEFORE_MISSING  B appears and A never does.  The antecedent was skipped entirely --
                  this is cal-weekly's real defect, and it is NOT a sequencing bug.
                  Reporting it as "out of order" would send the fix at the wrong seam
                  (Law 2: fixing the wrong seam is the biggest waste in skill work).
  NOT_APPLICABLE  B never appears, so there is nothing to order.  A vacuous pass,
                  reported by name so a silent no-op is never mistaken for a check
                  that ran.

MATCHING a section: exactly one of
  "term":     a LITERAL word or phrase.  PREFER THIS.  It is word-bounded and escaped
              for you, so it cannot be got subtly wrong, and -- the reason it was added
              2026-07-28 -- a literal is the only form a mechanical probe can DISGUISE
              and inject back at the rule.  A rule declared as a hand-rolled regex is
              un-probeable: `mutate.py` has nothing to inject, reports CANNOT EVALUATE,
              and the rule is never mechanically exercised at all.  Same hazard class as
              a `forbidden_content` rule that omits `flags:["i"]`: the gate looks armed
              and no one ever learns otherwise.
  "pattern":  a regex.  Use only when the thing genuinely is a pattern, not a word.
  "sequence": ["year", "quarter", "month", "week"] -- each must appear, in this order.
              A narrative arc is a sequence, not a keyword; this is what makes the
              real defect detectable at all.

USAGE
  order_lint.py --rules RULES.json --artifact A.md [--section "Phase 3"] [--json]
  order_lint.py --selftest

EXIT CODES (the part contract)
  0  ORDERED        -- every rule ordered or not-applicable
  1  REFUSED        -- at least one OUT_OF_ORDER or BEFORE_MISSING
  2  CANNOT EVALUATE -- missing file, bad rules, --section matched nothing. Fail-closed.

RULES FILE — a JSON list:
  [ {"id": "arc-before-win",
     "before": {"id": "arc", "sequence": ["year", "quarter", "month", "week"]},
     "after":  {"id": "win", "pattern": "\\bWin\\b"},
     "why": "spec L303: 'The arc first ... Then the Win.'"} ]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

ORDERED, REFUSED, CANNOT_EVALUATE = 0, 1, 2


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


def slice_section(text, section_rx):
    """Slice to the shallowest heading matching section_rx. Raises LookupError."""
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
    """Return the character offset where this section is satisfied, or None.

    For a sequence, the offset is where the LAST element lands -- the arc is only
    'present' once it has actually run to completion, so a half-written arc cannot
    satisfy an ordering rule by virtue of its first word.
    """
    if not isinstance(spec, dict) or not spec.get("id"):
        raise ValueError(f"section spec needs an 'id': {spec!r}")
    flags = re.IGNORECASE | re.MULTILINE

    # A literal term is escaped and word-bounded here, so the rule author never hand-rolls
    # the regex -- and a literal is the only form a mechanical probe can disguise-and-inject.
    if "term" in spec:
        term = spec["term"]
        if not isinstance(term, str) or not term.strip():
            raise ValueError(f"section {spec['id']!r} has an empty 'term'")
        m = re.compile(rf"\b{re.escape(term.strip())}\b", flags).search(text)
        return m.start() if m else None

    if "pattern" in spec:
        m = re.search(spec["pattern"], text, flags)
        return m.start() if m else None

    seq = spec.get("sequence")
    if not seq:
        raise ValueError(f"section {spec['id']!r} needs 'term', 'pattern' or 'sequence'")
    pos = 0
    last = None
    for token in seq:
        m = re.compile(rf"\b{re.escape(token)}\b", flags).search(text, pos)
        if not m:
            return None
        last, pos = m.start(), m.end()
    return last


def check(text, rules):
    """Return a list of result dicts. Raises ValueError on a bad rule -> fail closed."""
    results = []
    for rule in rules:
        if not isinstance(rule, dict) or not rule.get("id"):
            raise ValueError(f"rule needs an 'id': {rule!r}")
        if "before" not in rule or "after" not in rule:
            raise ValueError(f"rule {rule['id']!r} needs both 'before' and 'after'")
        a = locate(text, rule["before"])
        b = locate(text, rule["after"])

        if b is None:
            verdict = "NOT_APPLICABLE"
        elif a is None:
            verdict = "BEFORE_MISSING"
        elif a < b:
            verdict = "ORDERED"
        else:
            verdict = "OUT_OF_ORDER"

        results.append({
            "id": rule["id"],
            "verdict": verdict,
            "why": rule.get("why", ""),
            "before_id": rule["before"].get("id"),
            "after_id": rule["after"].get("id"),
            "before_at": a,
            "after_at": b,
            "failed": verdict in ("BEFORE_MISSING", "OUT_OF_ORDER"),
        })
    return results


def render(results):
    out = []
    for r in results:
        out.append(f"  [{r['verdict']}] {r['id']}")
        if r["verdict"] == "BEFORE_MISSING":
            out.append(f"      {r['after_id']!r} is present but {r['before_id']!r} never "
                       f"appears -- the antecedent was skipped, not mis-ordered")
        elif r["verdict"] == "OUT_OF_ORDER":
            out.append(f"      {r['after_id']!r} (char {r['after_at']}) comes before "
                       f"{r['before_id']!r} (char {r['before_at']})")
        elif r["verdict"] == "NOT_APPLICABLE":
            out.append(f"      {r['after_id']!r} never appears -- nothing to order "
                       f"(vacuous pass, not a check that ran)")
        if r["why"] and r["failed"]:
            out.append(f"      why it matters: {r['why']}")
    return "\n".join(out)


# ---------------------------------------------------------------- self-test

# The known-BAD is the REAL shape of cal-weekly's W30 Phase 3: a ranked Win with no
# arc in front of it.  The known-GOOD is the spec-correct artifact, hand-built.
_BAD = """## Phase 3 - Prioritization

### Ranked Win (owner-confirmed, no corrections)
1. Confirm delivery terms with the vendor - before Monday Day 1.
2. Confirm paperwork returned - before Monday Day 1.

### Calendar plan-of-intent
- Week 2 (~Aug 4): standby/hold week
"""

_GOOD = """## Phase 3 - Prioritization

### Report 1 - Radical Clarity
This year you said: build the second lane into the compounding spine.
This quarter: revenue in the door.
This month: the second lane as the move-proof one.
Which puts you HERE this week: the launch is the container.

### Ranked Win (owner-confirmed)
1. Confirm delivery terms with the vendor - before Monday Day 1.
"""

# both present, but reversed -- proves OUT_OF_ORDER is distinguished from BEFORE_MISSING
_REVERSED = """## Phase 3
### Ranked Win
1. Confirm delivery terms.
### Report 1
This year X, this quarter Y, this month Z, this week W.
"""

_RULES = [{
    "id": "arc-before-win",
    "before": {"id": "arc", "sequence": ["year", "quarter", "month", "week"]},
    "after": {"id": "win", "pattern": r"\bWin\b"},
    "why": "spec L303: 'The arc first ... Then the Win.'",
}]


def selftest():
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("order_lint --selftest")

    r = check(_BAD, _RULES)[0]
    report("catches the known-bad (Win with no arc before it)",
           r["verdict"] == "BEFORE_MISSING" and r["failed"], r["verdict"])

    r = check(_GOOD, _RULES)[0]
    report("passes a hand-built correct artifact (arc, then Win)",
           r["verdict"] == "ORDERED" and not r["failed"], r["verdict"])

    r = check(_REVERSED, _RULES)[0]
    report("distinguishes OUT_OF_ORDER from BEFORE_MISSING",
           r["verdict"] == "OUT_OF_ORDER" and r["failed"], r["verdict"])

    r = check("nothing relevant here at all", _RULES)[0]
    report("reports NOT_APPLICABLE by name rather than a silent pass",
           r["verdict"] == "NOT_APPLICABLE" and not r["failed"], r["verdict"])

    # a partial arc must NOT satisfy the rule
    partial = "This year you said X.\n### Ranked Win\n1. thing"
    report("a PARTIAL arc does not count as the arc",
           check(partial, _RULES)[0]["verdict"] == "BEFORE_MISSING")

    # sequence order is enforced, not mere presence
    scrambled = "week month quarter year\n### Ranked Win\n1. thing"
    report("sequence enforces ORDER, not just presence",
           check(scrambled, _RULES)[0]["verdict"] == "BEFORE_MISSING")

    # word-boundary discipline: 'weekend' must not satisfy 'week'
    report("word boundaries hold ('weekend' is not 'week')",
           locate("year quarter month weekend", {"id": "a", "sequence":
                                                 ["year", "quarter", "month", "week"]}) is None)

    # --- "term": the literal form, two-sided (added 2026-07-28, plan S0.7 order_lint item)
    # It must behave IDENTICALLY to the hand-rolled `\bWin\b` regex it replaces -- that
    # equivalence is the whole claim, since the fixture is being switched over to it.
    term_rules = [{
        "id": "arc-before-win",
        "before": {"id": "arc", "sequence": ["year", "quarter", "month", "week"]},
        "after": {"id": "win", "term": "Win"},
        "why": "spec L303: 'The arc first ... Then the Win.'",
    }]
    report("'term' catches the known-bad (Win with no arc before it)",
           check(_BAD, term_rules)[0]["verdict"] == "BEFORE_MISSING")
    report("'term' passes the known-good (arc, then Win)",
           check(_GOOD, term_rules)[0]["verdict"] == "ORDERED")
    report("'term' agrees with the equivalent regex on all three fixtures",
           all(check(t, term_rules)[0]["verdict"] == check(t, _RULES)[0]["verdict"]
               for t in (_BAD, _GOOD, _REVERSED)))
    report("'term' is word-bounded ('Winner' is not 'Win')",
           locate("the Winner takes it", {"id": "w", "term": "Win"}) is None)
    report("'term' is escaped, not evaluated as a regex",
           locate("a b c", {"id": "w", "term": "a.c"}) is None
           and locate("say a.c here", {"id": "w", "term": "a.c"}) is not None)
    try:
        locate("x", {"id": "w", "term": "   "})
        report("raises on an empty 'term' (fail-closed)", False, "no raise")
    except ValueError:
        report("raises on an empty 'term' (fail-closed)", True)

    # slicing
    two_phase = _GOOD + "\n" + _BAD.replace("Phase 3", "Phase 4")
    report("--section slices to one phase",
           check(slice_section(two_phase, "Phase 4"), _RULES)[0]["verdict"] == "BEFORE_MISSING")
    try:
        slice_section(_GOOD, "Phase 9")
        report("raises when --section matches nothing (fail-closed)", False, "no raise")
    except LookupError:
        report("raises when --section matches nothing (fail-closed)", True)
    try:
        check(_BAD, [{"id": "x", "before": {"id": "a"}, "after": {"id": "b", "pattern": "b"}}])
        report("raises on a rule with no pattern/sequence (fail-closed)", False, "no raise")
    except ValueError:
        report("raises on a rule with no pattern/sequence (fail-closed)", True)

    # end-to-end CLI, proving the exit-code contract
    with tempfile.TemporaryDirectory() as td:
        rp = os.path.join(td, "rules.json")
        with open(rp, "w", encoding="utf-8") as fh:
            json.dump(_RULES, fh)
        for label, body, want in (("CLI known-bad -> exit 1", _BAD, REFUSED),
                                  ("CLI known-good -> exit 0", _GOOD, ORDERED)):
            ap_ = os.path.join(td, "a.md")
            with open(ap_, "w", encoding="utf-8") as fh:
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

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="order_lint -- section A must precede section B")
    ap.add_argument("--rules")
    ap.add_argument("--artifact")
    ap.add_argument("--section", help="regex: lint only the section under this heading")
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
        print(json.dumps({"verdict": "REFUSED" if failed else "ORDERED",
                          "results": results}, indent=2))
    else:
        print(f"order_lint -- {'REFUSED' if failed else 'ORDERED'} "
              f"({len(failed)} of {len(results)} rule(s) failed)")
        print(render(results))
    sys.exit(REFUSED if failed else ORDERED)


if __name__ == "__main__":
    main()
