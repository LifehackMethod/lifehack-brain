#!/usr/bin/env python3
"""precondition_gate — a consequent marker may not stand without its antecedent.  [Parts Library]

WHEN: a skill's own output declares something ("shipped", "confirmed", "done") that is only
      true if some OTHER, earlier-declared fact already exists in the same document -- e.g. a
      "PR merged" line may not stand unless a "tests green" line, with real substance, is
      also there.

WHAT: for each rule, if the CONSEQUENT pattern is found anywhere in the artifact, the
      ANTECEDENT pattern must also be found in the SAME document, and (if the rule declares
      `min_chars`) the matched antecedent region must carry that much real content -- not
      just the bare pattern with nothing behind it. If the consequent never appears, the
      rule does not apply (NOT_APPLICABLE) and passes: this gate has nothing to say about a
      document that never makes the claim in the first place.

⛔ CO-PRESENCE ONLY, NEVER ORDER. This part proves the antecedent EXISTS somewhere in the
      artifact when the consequent does. It does NOT prove the antecedent appears BEFORE the
      consequent, or that one caused the other -- an artifact where the consequent is on
      line 1 and the antecedent is on line 400 passes this check cleanly. Sequencing is a
      DIFFERENT claim, checked by the sibling part `order_lint.py`. Wiring only this part
      behind a clause that says "X only after Y" is a documented gap, not a bug: use
      order_lint for the ordering half and this part for the presence half, together, if a
      clause requires both.

⛔ DECLARED UNCHECKABLE -- `min_chars` PROVES LENGTH, NOT TRUTH. A region with 40 characters
      of plausible-looking filler passes exactly as well as 40 characters of real content.
      This is the same bound every other part in this library states for itself (see
      phase_gate.py, section_present.py): text-in/text-out, no independent trace of whether
      the matched text is the actual deliverable. Do not "fix" this with a substance
      heuristic -- that heuristic was built, measured, and reverted elsewhere in this
      project (see phase_gate.py's DECLARED UNCHECKABLE note) after it produced 50% false
      positives on real clauses.

USAGE
  precondition_gate.py --rules R.json --artifact A.md [--json]
  precondition_gate.py --selftest

EXIT CODES (the part contract)
  0  PASSED    -- every applicable rule's antecedent is co-present (with declared substance)
  1  VIOLATED  -- at least one applicable rule's antecedent is missing or under-substance
  2  CANNOT EVALUATE -- missing/unreadable/unparsable artifact or rules file, or a malformed
                        rule. This is the ABSENT-SUBJECT outcome: never folded into PASSED
                        or VIOLATED, always its own named refusal.

RULES FILE -- a JSON list:
  [ {"id": "pr-needs-green-tests",
     "consequent": {"pattern": "PR merged"},
     "antecedent": {"pattern": "tests?:?\\s*(green|passing).*", "min_chars": 15},
     "why": "a merge claim with no test evidence in the same doc is unearned"} ]
  `consequent.pattern` and `antecedent.pattern` are regexes, searched case-insensitively
  over the whole artifact (MULTILINE|IGNORECASE) -- this checks the WHOLE document, not a
  phase slice; callers who need a bounded region should pre-slice the artifact themselves.
  `antecedent.min_chars` is optional. When the antecedent pattern has exactly one capturing
  group, that group's stripped text is what gets measured against `min_chars` (so a rule
  author can wrap just the substantive part); with no group, the whole match is measured.

PER-RULE VERDICTS: OK / VIOLATED / NOT_APPLICABLE (consequent absent -- the rule has
nothing to say about this document, and NOT_APPLICABLE always counts toward PASSED).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

PASSED, VIOLATED, CANNOT_EVALUATE = 0, 1, 2


def _die(msg):
    print(f"CANNOT EVALUATE: {msg}", file=sys.stderr)
    sys.exit(CANNOT_EVALUATE)


# ---------------------------------------------------------------- matching

def _search(pattern, text):
    """Return the first re.Match for pattern in text, or None. Raises re.error on a bad regex."""
    return re.search(pattern, text, re.IGNORECASE | re.MULTILINE)


def _substance_text(match):
    """The text `min_chars` is measured against: the sole capturing group if there is
    exactly one, else the whole match. Always stripped of surrounding whitespace."""
    try:
        groups = match.groups()
    except (AttributeError, IndexError):
        groups = ()
    if len(groups) == 1 and groups[0] is not None:
        return groups[0].strip()
    return match.group(0).strip()


def _validate_rule(rule):
    if not isinstance(rule, dict) or not rule.get("id"):
        raise ValueError(f"rule needs an 'id': {rule!r}")
    for key in ("consequent", "antecedent"):
        spec = rule.get(key)
        if not isinstance(spec, dict) or not spec.get("pattern"):
            raise ValueError(f"rule {rule['id']!r} needs a {key!r} object with a 'pattern'")
    min_chars = rule["antecedent"].get("min_chars")
    if min_chars is not None and (not isinstance(min_chars, int) or min_chars < 0):
        raise ValueError(f"rule {rule['id']!r}: antecedent.min_chars must be a non-negative int")


# ---------------------------------------------------------------- the check

def evaluate(text, rules):
    """Return a list of per-rule verdict dicts. Raises ValueError/re.error -> fail closed."""
    results = []
    for rule in rules:
        _validate_rule(rule)
        rid = rule["id"]
        cons = rule["consequent"]
        ante = rule["antecedent"]
        why = rule.get("why", "")

        cons_match = _search(cons["pattern"], text)
        if cons_match is None:
            results.append({
                "id": rid, "verdict": "NOT_APPLICABLE", "why": why,
                "detail": "consequent pattern never appears -- this rule has nothing to "
                          "say about this document",
                "failed": False,
            })
            continue

        ante_match = _search(ante["pattern"], text)
        if ante_match is None:
            results.append({
                "id": rid, "verdict": "VIOLATED", "why": why,
                "detail": f"consequent /{cons['pattern']}/ is present but the required "
                          f"antecedent /{ante['pattern']}/ is absent from this artifact",
                "failed": True,
            })
            continue

        min_chars = ante.get("min_chars")
        if min_chars is not None:
            substance = _substance_text(ante_match)
            if len(substance) < min_chars:
                results.append({
                    "id": rid, "verdict": "VIOLATED", "why": why,
                    "detail": f"antecedent /{ante['pattern']}/ matched, but the matched "
                              f"region carries only {len(substance)} char(s) of substance "
                              f"(< {min_chars} required): {substance[:80]!r}",
                    "failed": True,
                })
                continue

        results.append({
            "id": rid, "verdict": "OK", "why": why,
            "detail": "antecedent co-present with the required substance",
            "failed": False,
        })
    return results


def render(results):
    out = []
    for r in results:
        out.append(f"  [{r['verdict']}] {r['id']}")
        out.append(f"      {r['detail']}")
        if r["why"] and r["failed"]:
            out.append(f"      why it matters: {r['why']}")
    return "\n".join(out)


# ---------------------------------------------------------------- self-test

_RULES = [
    {
        "id": "pr-needs-green-tests",
        "consequent": {"pattern": r"PR merged"},
        "antecedent": {"pattern": r"tests?:?\s*(green|passing)([^\n]*)", "min_chars": 15},
        "why": "a merge claim with no real test evidence in the same doc is unearned",
    },
    {
        "id": "deploy-needs-rollback-plan",
        "consequent": {"pattern": r"deployed to prod"},
        "antecedent": {"pattern": r"rollback plan:\s*(.+)", "min_chars": 20},
        "why": "a prod deploy claim needs a real rollback plan on record",
    },
]

# known-bad #1: consequent present, antecedent entirely absent -> VIOLATED
_BAD_MISSING = """# Ship log

Status: PR merged this afternoon, closes #482.
"""

# known-bad #2: consequent present, antecedent pattern matches but has almost no
# substance behind it (a bare stamp, no real content) -> VIOLATED
_BAD_THIN = """# Ship log

Status: PR merged this afternoon, closes #482.
Tests: green.
"""

# known-good: consequent present, antecedent present with real substance -> OK
_GOOD = """# Ship log

Status: PR merged this afternoon, closes #482.
Tests: green -- 214 passed, 0 failed, full suite, CI run #9931, 2026-08-30T14:02Z.
"""

# consequent never appears at all -> NOT_APPLICABLE, and NOT_APPLICABLE must count as
# a pass (this gate has nothing to say about a doc that never makes the claim)
_NEVER_CLAIMED = """# Ship log

Still working the branch, nothing merged yet.
"""


def selftest():
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("precondition_gate --selftest")

    r = evaluate(_BAD_MISSING, _RULES)
    v = next(x for x in r if x["id"] == "pr-needs-green-tests")
    report("known-bad: consequent present, antecedent wholly absent -> VIOLATED",
           v["verdict"] == "VIOLATED" and v["failed"], v["verdict"])

    r = evaluate(_BAD_THIN, _RULES)
    v = next(x for x in r if x["id"] == "pr-needs-green-tests")
    report("known-bad: antecedent pattern matches but has too little substance -> VIOLATED",
           v["verdict"] == "VIOLATED" and v["failed"], v["detail"])

    r = evaluate(_GOOD, _RULES)
    v = next(x for x in r if x["id"] == "pr-needs-green-tests")
    report("known-good: antecedent present WITH real substance -> OK",
           v["verdict"] == "OK" and not v["failed"], v["verdict"])
    v2 = next(x for x in r if x["id"] == "deploy-needs-rollback-plan")
    report("a rule whose consequent never fires is NOT_APPLICABLE (and passes)",
           v2["verdict"] == "NOT_APPLICABLE" and not v2["failed"], v2["verdict"])

    r = evaluate(_NEVER_CLAIMED, _RULES)
    report("NOT_APPLICABLE for every rule when no consequent is ever made",
           all(x["verdict"] == "NOT_APPLICABLE" and not x["failed"] for x in r))

    # co-presence only, never order: antecedent AFTER consequent still counts as present
    reordered = "PR merged.\n\nirrelevant filler line one\nirrelevant filler line two\n" \
                "Tests: green -- full suite, 214 passed, CI run #9931, verified end to end.\n"
    r = evaluate(reordered, [_RULES[0]])
    report("proves CO-PRESENCE only: an antecedent written AFTER the consequent still "
           "counts (ordering is order_lint's job, not this part's)",
           r[0]["verdict"] == "OK")

    # capturing-group substance measurement: only the group's text is measured
    group_rule = [{"id": "g", "consequent": {"pattern": "shipped"},
                   "antecedent": {"pattern": r"note: \[(.*?)\]", "min_chars": 10},
                   "why": "n/a"}]
    thin_group = "shipped. note: [ok]"
    thick_group = "shipped. note: [full regression suite run, all green, verified by hand]"
    report("min_chars measures the CAPTURING GROUP alone when the pattern has one",
           evaluate(thin_group, group_rule)[0]["verdict"] == "VIOLATED"
           and evaluate(thick_group, group_rule)[0]["verdict"] == "OK")

    # fail-closed on malformed rules
    for label, bad_rules in (
        ("rule missing 'id'", [{"consequent": {"pattern": "x"}, "antecedent": {"pattern": "y"}}]),
        ("rule missing 'consequent'", [{"id": "x", "antecedent": {"pattern": "y"}}]),
        ("rule missing 'antecedent'", [{"id": "x", "consequent": {"pattern": "y"}}]),
        ("rule with negative min_chars", [{"id": "x", "consequent": {"pattern": "y"},
                                           "antecedent": {"pattern": "z", "min_chars": -1}}]),
    ):
        try:
            evaluate("y z", bad_rules)
            report(f"raises on {label} (fail-closed)", False, "no raise")
        except ValueError:
            report(f"raises on {label} (fail-closed)", True)

    # CLI end-to-end, proving the exit-code contract
    me = os.path.abspath(__file__)
    with tempfile.TemporaryDirectory() as td:
        rp = os.path.join(td, "rules.json")
        with open(rp, "w", encoding="utf-8") as fh:
            json.dump(_RULES, fh)

        bad_p = os.path.join(td, "bad.md")
        with open(bad_p, "w", encoding="utf-8") as fh:
            fh.write(_BAD_MISSING)
        rc = subprocess.run([sys.executable, me, "--rules", rp, "--artifact", bad_p],
                            capture_output=True, text=True).returncode
        report("CLI known-bad -> exit 1", rc == VIOLATED, f"got exit {rc}")

        good_p = os.path.join(td, "good.md")
        with open(good_p, "w", encoding="utf-8") as fh:
            fh.write(_GOOD)
        rc = subprocess.run([sys.executable, me, "--rules", rp, "--artifact", good_p],
                            capture_output=True, text=True).returncode
        report("CLI known-good -> exit 0", rc == PASSED, f"got exit {rc}")

        rc = subprocess.run([sys.executable, me, "--rules", rp,
                             "--artifact", os.path.join(td, "nope.md")],
                            capture_output=True, text=True).returncode
        report("CLI missing artifact -> exit 2 (fail-closed, ABSENT-SUBJECT)",
               rc == CANNOT_EVALUATE, f"got exit {rc}")

        rc = subprocess.run([sys.executable, me, "--rules", os.path.join(td, "norules.json"),
                             "--artifact", good_p],
                            capture_output=True, text=True).returncode
        report("CLI missing rules file -> exit 2 (fail-closed, ABSENT-SUBJECT)",
               rc == CANNOT_EVALUATE, f"got exit {rc}")

        junk_p = os.path.join(td, "junk.json")
        with open(junk_p, "w", encoding="utf-8") as fh:
            fh.write("{not valid json")
        rc = subprocess.run([sys.executable, me, "--rules", junk_p, "--artifact", good_p],
                            capture_output=True, text=True).returncode
        report("CLI unparsable rules JSON -> exit 2 (fail-closed, ABSENT-SUBJECT)",
               rc == CANNOT_EVALUATE, f"got exit {rc}")

        p = subprocess.run([sys.executable, me, "--rules", rp, "--artifact", good_p, "--json"],
                           capture_output=True, text=True)
        try:
            payload = json.loads(p.stdout)
            json_ok = isinstance(payload, dict) and payload.get("verdict") == "PASSED"
        except json.JSONDecodeError:
            json_ok = False
        report("CLI --json emits a parseable verdict", json_ok, p.stdout[:150])

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description="precondition_gate -- a consequent marker may not stand without its "
                     "co-present antecedent (proves co-presence only, never order)")
    ap.add_argument("--rules")
    ap.add_argument("--artifact")
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
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        _die(f"rules file is not valid JSON: {e}")
    if not isinstance(rules, list):
        _die("rules file must contain a JSON list")

    try:
        text = open(args.artifact, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError) as e:
        _die(f"artifact could not be read: {e}")

    try:
        results = evaluate(text, rules)
    except (ValueError, re.error) as e:
        _die(str(e))

    failed = [r for r in results if r["failed"]]
    verdict = "VIOLATED" if failed else "PASSED"

    if args.json:
        print(json.dumps({"verdict": verdict, "results": results}, indent=2, ensure_ascii=False))
    else:
        print(f"precondition_gate -- {verdict} "
              f"({len(failed)} of {len(results)} rule(s) violated)")
        print(render(results))

    sys.exit(VIOLATED if failed else PASSED)


if __name__ == "__main__":
    main()
